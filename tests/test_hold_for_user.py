"""A question nobody is waiting on waits for the main window (TASKS R96).

The owner's report of 2026-10-29: on 0.7.114 the album picker opened by itself
over Tools → Setup & Updates…, while they were using it. Their rule: *"if they
need to pop up, sure, but if they can hold, then hold them."* The picker can hold,
so it waits until the main window is the one in use, then opens, if it is still
wanted (`ui/hold_for_user.py`, `ui/main_window_picker.py`).

These drive the real window and the real Setup & Updates window, which is
modeless, as the owner's was: a check for a modal dialog alone would not have
held the picker they saw.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from conftest import stop_window_threads
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QDialog, QWidget
from test_ui_main_window import _make_window

from platterpus.adapters.musicbrainz_client import ReleaseSummary
from platterpus.ui import hold_for_user
from platterpus.ui.release_picker import ReleasePickerDialog
from platterpus.ui.unknown_album import UnknownAlbumDialog

_DISC = "pNtImOkdBm9RMBIalzx0w9cfsYY-"

_RELEASES = [
    ReleaseSummary(
        mbid=f"aaaaaaaa-0000-0000-0000-00000000000{n}",
        title=f"Candidate {n}",
        artist_credit="The Police",
        date="2003",
        country="GB",
        track_count=14,
    )
    for n in (1, 2)
]


@pytest.fixture()
def make_window(qapp: QApplication) -> Iterator[Callable[..., Any]]:
    """A real MainWindow, its threads stopped afterwards (as `teardown_threads`)."""
    created: list[Any] = []

    def factory(**kwargs: Any) -> Any:
        window = _make_window(qapp, **kwargs)
        created.append(window)
        return window

    yield factory
    for window in created:
        for child in window.findChildren(QDialog):
            child.close()
        # Hidden, and its deferred delete run below: these tests show the real
        # window, and a shown window outlives `deleteLater` until a loop runs, so
        # a later test on the same worker that read every visible label read this
        # one's ("2 matches found — pick one") and failed `main`'s CI after #420.
        # Either step alone puts it away (`scripts/revert_probe.py`); with
        # neither, conftest's leftover check fails the test that leaked it.
        window.hide()
        stop_window_threads(window)
        window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture()
def pickers(monkeypatch: pytest.MonkeyPatch) -> list[ReleasePickerDialog]:
    """Every release picker that opened; each is cancelled at once."""
    opened: list[ReleasePickerDialog] = []

    def _fake_exec(self: ReleasePickerDialog) -> int:
        opened.append(self)
        return int(QDialog.DialogCode.Rejected)

    monkeypatch.setattr(ReleasePickerDialog, "exec", _fake_exec)
    return opened


def _activate(widget: QWidget) -> None:
    """Make ``widget`` the active window, as a click on it would."""
    widget.show()
    widget.raise_()
    widget.activateWindow()
    deadline = time.monotonic() + 5.0
    while QApplication.activeWindow() is not widget and time.monotonic() < deadline:
        QCoreApplication.processEvents()
    assert QApplication.activeWindow() is widget, "the window never became active"


def _wait(seconds: float) -> None:
    """Let the event loop run, retry timers included, for ``seconds``."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)


def test_the_picker_waits_while_setup_and_updates_is_in_use(
    make_window: Callable[..., Any],
    pickers: list[ReleasePickerDialog],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The owner's case: Setup & Updates is open and in use when the lookup lands.

    The picker does not open over it; it opens once the owner is back on the main
    window. The control is the main window in use: the picker opens at once."""
    window = make_window()
    window._current_disc_id = _DISC
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    assert not setup.isModal(), "Setup & Updates is modeless; the test needs that"

    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        window._on_mb_releases(_DISC, _RELEASES)
        _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert pickers == [], "the picker opened over Setup & Updates"
    assert "held until the main window is in use" in caplog.text, caplog.text
    assert window._mb_picker_held_for == _DISC

    setup.close()
    _activate(window)
    _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert len(pickers) == 1, "the held picker never opened"
    assert window._mb_picker_held_for == ""


def test_the_picker_opens_at_once_when_the_main_window_is_in_use(
    make_window: Callable[..., Any], pickers: list[ReleasePickerDialog]
) -> None:
    """The control for the test above: nothing else of ours in use, no wait."""
    window = make_window()
    window._current_disc_id = _DISC
    _activate(window)
    window._on_mb_releases(_DISC, _RELEASES)
    assert len(pickers) == 1


def test_the_script_console_does_not_hold_the_picker(
    make_window: Callable[..., Any], pickers: list[ReleasePickerDialog]
) -> None:
    """An acceptance run keeps the script console active by design, and its
    `pick-release` answers the picker: holding it there would stall the run."""
    window = make_window()
    window._current_disc_id = _DISC
    console = window.open_script_console()
    _activate(console)
    window._on_mb_releases(_DISC, _RELEASES)
    assert len(pickers) == 1


def test_a_modal_dialog_holds_the_picker(qapp: QApplication) -> None:
    """A modal dialog of ours is busy even when no window is active."""
    main = QWidget()
    modal = QDialog()
    modal.setWindowTitle("Some question")
    modal.setModal(True)
    modal.show()
    try:
        QCoreApplication.processEvents()
        assert "a dialog is open ('Some question')" == hold_for_user.busy_reason(main)
    finally:
        modal.close()
        QCoreApplication.processEvents()
    assert QApplication.activeModalWidget() is not modal


def test_a_held_picker_for_a_disc_that_left_is_dropped(
    make_window: Callable[..., Any],
    pickers: list[ReleasePickerDialog],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Checked when it would open, not when it was held: a different disc in the
    drive by then means the picker is not shown, and the hold is forgotten so the
    disc's next lookup can ask."""
    window = make_window()
    window._current_disc_id = _DISC
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    window._on_mb_releases(_DISC, _RELEASES)
    assert window._mb_picker_held_for == _DISC

    window._current_disc_id = "another-disc-id"
    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert "no longer wanted, not opened" in caplog.text, caplog.text
    assert window._mb_picker_held_for == ""
    setup.close()
    _activate(window)
    _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert pickers == []


def test_one_held_picker_per_disc(
    make_window: Callable[..., Any],
    pickers: list[ReleasePickerDialog],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A second lookup for a disc whose picker is waiting is declined, as it is
    while the picker is open: two would ask the same question twice."""
    window = make_window()
    window._current_disc_id = _DISC
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    window._on_mb_releases(_DISC, _RELEASES)
    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        window._on_mb_releases(_DISC, _RELEASES)
    assert "not holding a second one" in caplog.text, caplog.text

    setup.close()
    _activate(window)
    _wait(4 * hold_for_user.RETRY_MS / 1000)
    assert len(pickers) == 1


# --- The unknown-album offer (`_hold_unknown_album_offer`) -------------------
#
# The picker's sibling: a lookup that finds NO release offers to rip the disc
# as an unknown album. Nothing waits on that answer either, so it holds the same
# way, keyed on the disc SCAN (`_disc_retries.request`) because a disc with no
# MusicBrainz ID at all comes here too.


@pytest.fixture()
def unknown_offers(monkeypatch: pytest.MonkeyPatch) -> list[UnknownAlbumDialog]:
    """Every unknown-album offer that opened; each is declined at once, so the
    window stays out of unknown mode and a second offer would not be refused
    for that reason."""
    opened: list[UnknownAlbumDialog] = []

    def _fake_exec(self: UnknownAlbumDialog) -> int:
        opened.append(self)
        return int(QDialog.DialogCode.Rejected)

    monkeypatch.setattr(UnknownAlbumDialog, "exec", _fake_exec)
    return opened


def test_the_unknown_album_offer_waits_while_setup_and_updates_is_in_use(
    make_window: Callable[..., Any],
    unknown_offers: list[UnknownAlbumDialog],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A disc MusicBrainz does not know, read while Setup & Updates is in use:
    the offer does not open over it, and opens once the main window is back."""
    window = make_window()
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)

    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        window._handle_no_mb_match()
        _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert unknown_offers == [], "the unknown-album offer opened over Setup"
    assert "held until the main window is in use" in caplog.text, caplog.text
    assert window._unknown_offer_held_for == window._disc_retries.request

    setup.close()
    _activate(window)
    _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert len(unknown_offers) == 1, "the held offer never opened"
    assert window._unknown_offer_held_for is None


def test_the_unknown_album_offer_opens_at_once_when_the_main_window_is_in_use(
    make_window: Callable[..., Any], unknown_offers: list[UnknownAlbumDialog]
) -> None:
    """The control for the test above: nothing else of ours in use, no wait."""
    window = make_window()
    _activate(window)
    window._handle_no_mb_match()
    assert len(unknown_offers) == 1


def test_a_newer_disc_scan_drops_a_held_unknown_album_offer(
    make_window: Callable[..., Any],
    unknown_offers: list[UnknownAlbumDialog],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Checked when it would open, not when it was held: a scan asked for since
    (a Rescan, another disc) makes the held offer stale. It is dropped, and the
    hold forgotten so the new scan's own result can ask."""
    window = make_window()
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    window._handle_no_mb_match()
    held = window._disc_retries.request
    assert window._unknown_offer_held_for == held

    window._begin_disc_request()  # what a Rescan or a new disc does first
    assert window._disc_retries.request == held + 1
    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert "no longer wanted, not opened" in caplog.text, caplog.text
    assert window._unknown_offer_held_for is None

    setup.close()
    _activate(window)
    _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert unknown_offers == [], "a stale scan's offer opened"


def test_one_held_unknown_album_offer_per_scan(
    make_window: Callable[..., Any],
    unknown_offers: list[UnknownAlbumDialog],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Two no-match results for one scan (the disc-ID path and a duplicate
    lookup) hold ONE offer: two would ask the same question twice in a row."""
    window = make_window()
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    window._handle_no_mb_match()
    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        window._handle_no_mb_match()
    assert "not holding a second one" in caplog.text, caplog.text

    setup.close()
    _activate(window)
    _wait(4 * hold_for_user.RETRY_MS / 1000)
    assert len(unknown_offers) == 1


def test_a_duplicate_no_match_while_the_offer_is_open_does_not_ask_again(
    make_window: Callable[..., Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The offer is modal; a duplicate result for the same scan that lands while
    it is open would be held behind it and asked again the moment the user
    declined. The key stays set until the dialog closes, so it is not."""
    window = make_window()
    _activate(window)
    opened: list[UnknownAlbumDialog] = []

    def _exec_with_a_duplicate_arriving(self: UnknownAlbumDialog) -> int:
        opened.append(self)
        if len(opened) == 1:
            window._handle_no_mb_match()  # lands during the nested loop
        return int(QDialog.DialogCode.Rejected)

    monkeypatch.setattr(UnknownAlbumDialog, "exec", _exec_with_a_duplicate_arriving)
    window._handle_no_mb_match()
    _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert len(opened) == 1, "the same scan's offer was asked twice"
    assert window._unknown_offer_held_for is None


# --- The first-run offers (`_maybe_offer_first_run_setup`) ------------------
#
# The config-reset notice, the AppImage menu offer, the host setup offer and the
# drive setup offer open by themselves at launch, one after another. Nothing is
# stopped on their answers, so the group holds as one: each is its own modal
# and closes before the next opens, so the main window is free between them.


def _record_first_run_offers(window: Any, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace each first-run offer with a recorder; the host stack is ready,
    so the sequence runs to the drive offer.

    The window's constructor queued the REAL launch call
    (`QTimer.singleShot(0, ...)`), which would otherwise fire inside the first
    event pump of the test and record a launch the test did not drive. It is
    delivered here while the window counts as unattended, so it makes no offer
    and holds nothing, and each test then makes its own call.
    """
    window._unattended = True
    QCoreApplication.processEvents()
    window._unattended = False
    fired: list[str] = []
    monkeypatch.setattr(
        window, "_show_config_reset_notice", lambda: fired.append("notice")
    )
    monkeypatch.setattr(
        window, "_maybe_offer_appimage_integration", lambda: fired.append("appimage")
    )
    monkeypatch.setattr(window, "_host_stack_ready", lambda: True)
    monkeypatch.setattr(
        window, "_maybe_offer_drive_setup", lambda: fired.append("drive")
    )
    return fired


def test_the_first_run_offers_wait_while_setup_and_updates_is_in_use(
    make_window: Callable[..., Any],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    window = make_window()
    fired = _record_first_run_offers(window, monkeypatch)
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)

    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        window._maybe_offer_first_run_setup()
        _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert fired == [], f"first-run offers opened over Setup & Updates: {fired}"
    assert "first-run offers: held until the main window is in use" in caplog.text

    setup.close()
    _activate(window)
    _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert fired == ["notice", "appimage", "drive"], fired


def test_the_first_run_offers_open_at_once_when_the_main_window_is_in_use(
    make_window: Callable[..., Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: nothing else of ours in use, the offers run in the call."""
    window = make_window()
    fired = _record_first_run_offers(window, monkeypatch)
    _activate(window)
    window._maybe_offer_first_run_setup()
    assert fired == ["notice", "appimage", "drive"], fired


def test_held_first_run_offers_are_dropped_if_the_launch_turns_unattended(
    make_window: Callable[..., Any],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The unattended rule (rig, 2026-08-18) is asked where they OPEN, not only
    where they were held: a script that started meanwhile has nobody to answer."""
    window = make_window()
    fired = _record_first_run_offers(window, monkeypatch)
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    window._maybe_offer_first_run_setup()

    window._unattended = True
    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert "first-run offers: no longer wanted" in caplog.text, caplog.text
    setup.close()
    _activate(window)
    _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert fired == [], fired


# --- The automatic cyanrip update offer (`_hold_automatic_ripper_offer`) -----
#
# The launch-time check's one-click install offer. Nobody asked for it, so it
# can hold: it used to be DROPPED by anything open when the answer landed, and
# saw only a modal dialog, so it opened over Setup & Updates. A check the user
# starts from Setup & Updates is the other case and is answered at once.


def _an_automatic_offer() -> Any:
    """An answer the automatic check surfaces: a one-click, approved build."""
    from types import SimpleNamespace

    from platterpus.deps.ripper_offer import OFFER_AVAILABLE

    return SimpleNamespace(
        verdict=OFFER_AVAILABLE,
        detail="a newer cyanrip build is available",
        install_commit="abc1234",
        auto_installable=True,
    )


@pytest.fixture()
def ripper_offers(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """Every install offer that opened, recorded instead of shown."""
    from platterpus.ui.main_window import MainWindow

    opened: list[object] = []
    monkeypatch.setattr(
        MainWindow,
        "_offer_ripper_install",
        lambda self, offer, detail, commit, **_: opened.append(offer),
    )
    return opened


def _land(window: Any, offer: object, *, automatic: bool) -> None:
    """Deliver a ripper check's answer, as the worker's queued signal does."""
    window._ripper_check_is_automatic = automatic
    window._on_ripper_update_result(offer)


def test_the_automatic_ripper_offer_waits_while_setup_and_updates_is_in_use(
    make_window: Callable[..., Any],
    ripper_offers: list[object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    window = make_window()
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    offer = _an_automatic_offer()

    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        _land(window, offer, automatic=True)
        _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert ripper_offers == [], "the automatic offer opened over Setup & Updates"
    assert "automatic cyanrip update offer: held" in caplog.text, caplog.text
    assert window._held_ripper_offer is offer

    setup.close()
    _activate(window)
    _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert ripper_offers == [offer], "the held offer never opened"
    assert window._held_ripper_offer is None


def test_the_automatic_ripper_offer_waits_out_a_rip_instead_of_being_dropped(
    make_window: Callable[..., Any], ripper_offers: list[object]
) -> None:
    """Never over a running rip (the install would replace the binary ripping),
    and no longer lost because of one: it opens when the rip has ended."""
    window = make_window()
    _activate(window)
    window._rip_thread = object()  # a rip is running when the answer lands
    try:
        _land(window, _an_automatic_offer(), automatic=True)
        _wait(3 * hold_for_user.RETRY_MS / 1000)
        assert ripper_offers == [], "an install offer opened over a running rip"
    finally:
        window._rip_thread = None
    _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert len(ripper_offers) == 1, "the offer was lost to the rip"


def test_a_check_the_user_starts_from_setup_and_updates_is_answered_at_once(
    make_window: Callable[..., Any], ripper_offers: list[object]
) -> None:
    """The caveat R96 names: the user's own check is asked FROM Setup & Updates,
    which is then the active window. Holding it until they left that window
    would answer nobody."""
    window = make_window()
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    offer = _an_automatic_offer()
    _land(window, offer, automatic=False)
    assert ripper_offers == [offer], "the user's own check was held"
    assert window._held_ripper_offer is None


def test_a_newer_check_drops_a_held_automatic_offer(
    make_window: Callable[..., Any],
    ripper_offers: list[object],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The user checks again from Setup & Updates while the launch's offer
    waits: that newer answer is the one that counts, so the held one is dropped
    and does not open as a stale second offer when they come back."""
    import platterpus.workers as workers

    window = make_window()
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    _land(window, _an_automatic_offer(), automatic=True)
    assert window._held_ripper_offer is not None

    # The check is started, not run: no network, no container.
    monkeypatch.setattr(workers, "start_worker_thread", lambda *a, **k: None)
    window._on_check_ripper_updates()
    assert window._held_ripper_offer is None
    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert "automatic cyanrip update offer: no longer wanted" in caplog.text
    setup.close()
    _activate(window)
    _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert ripper_offers == [], "a superseded offer opened"
    window._ripper_update_worker = None
    window._ripper_update_thread = None


def test_a_held_automatic_offer_is_dropped_when_the_window_is_hidden(
    make_window: Callable[..., Any],
    ripper_offers: list[object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Waiting does not turn a closed window into a person: drop, and say why."""
    window = make_window()
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    _land(window, _an_automatic_offer(), automatic=True)
    window.hide()
    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert "offer dropped — the window is not shown" in caplog.text, caplog.text
    assert window._held_ripper_offer is None
    setup.close()
    _wait(2 * hold_for_user.RETRY_MS / 1000)
    assert ripper_offers == []


def test_an_open_dialog_no_longer_skips_the_automatic_check(
    make_window: Callable[..., Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The launch's check used to be SKIPPED when a dialog was open as it was
    armed (the first-run setup question, at launch). Its answer now waits for
    the main window, so the check itself runs; a rip or a hidden window still
    skips it (`test_ripper_update_worker.py`)."""
    import platterpus.workers as workers

    started: list[object] = []
    monkeypatch.setattr(
        workers, "start_worker_thread", lambda *a, **k: started.append(a)
    )
    window = make_window()
    _activate(window)
    modal = QDialog(window)
    modal.setWindowTitle("Set up Platterpus?")
    modal.setModal(True)
    modal.show()
    try:
        QCoreApplication.processEvents()
        assert QApplication.activeModalWidget() is modal, "floor: no modal is up"
        window._maybe_check_ripper_updates()
    finally:
        modal.hide()
        modal.deleteLater()
    assert started, "the automatic check was skipped because a dialog was open"
    window._ripper_update_worker = None
    window._ripper_update_thread = None


# --- The launch dependency report (`_defer_if_floor_is_busy`, launch=True) ---
#
# The launch check's report opens the resolver when a REQUIRED tool is missing.
# Nobody asked for it, so it waits for the main window too; a check the user
# starts (Check dependencies, About's Check again, the re-check after host setup)
# is answered at once. A missing required tool is never given up on the old 30 s
# clock: only a newer check drops the held report.


def _missing_required_report() -> Any:
    """A real report with one required tool missing."""
    from test_ui_main_window import _dep_spec

    from platterpus.deps.checks import ProbeResult
    from platterpus.deps.manager import DependencyReport
    from platterpus.deps.resolvers import MissingItem

    absent = ProbeResult(present=False, version=None, location=None)
    spec = _dep_spec("cyanrip", lambda: absent)
    return DependencyReport(missing=[MissingItem(spec=spec, probe=absent)])


@pytest.fixture()
def resolutions(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """Every report whose missing tools the window set out to resolve."""
    from platterpus.ui import main_window_deps
    from platterpus.ui.main_window import MainWindow

    resolved: list[object] = []
    monkeypatch.setattr(
        MainWindow, "_resolve_missing_unified", lambda self, r: resolved.append(r)
    )
    monkeypatch.setattr(MainWindow, "_show_dep_summary", lambda self, *a, **k: None)
    # Fast retries, so a test can outlast the old 40-attempt budget in a second.
    monkeypatch.setattr(main_window_deps, "_DEP_RESOLVE_RETRY_MS", 5)
    return resolved


def _land_check(window: Any, report: object, *, launch: bool) -> None:
    """Deliver a silent check's report, as the worker's queued signal does."""
    window._dep_check_manager = window._dependency_manager
    window._dep_check_show_summary = False
    window._dep_check_is_launch = launch
    window._on_dependency_check_done(report)


def test_the_launch_dependency_report_waits_while_setup_and_updates_is_in_use(
    make_window: Callable[..., Any],
    resolutions: list[object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Setup & Updates is in use when the launch check lands with cyanrip
    missing: the resolver does not open over it, the hold outlasts the old 30 s
    budget (attempts, not seconds, are what it counted), and it opens once the
    main window is back."""
    from platterpus.ui import main_window_deps

    window = make_window()
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    report = _missing_required_report()
    budget = main_window_deps._DEP_RESOLVE_MAX_DEFERRALS

    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        _land_check(window, report, launch=True)
        deadline = time.monotonic() + 5.0
        while window._dep_resolve_deferrals <= budget and time.monotonic() < deadline:
            _wait(0.05)
    assert window._dep_resolve_deferrals > budget, "the hold ended at the old budget"
    assert resolutions == [], "the launch report opened over Setup & Updates"
    assert "another window is in use" in caplog.text, caplog.text
    assert "gave up" not in caplog.text, "a missing required tool was given up on"

    setup.close()
    _activate(window)
    _wait(0.3)
    assert resolutions == [report], "the held launch report never opened"
    assert window._dep_resolve_deferrals == 0


def test_the_launch_dependency_report_opens_at_once_when_the_main_window_is_in_use(
    make_window: Callable[..., Any], resolutions: list[object]
) -> None:
    """The control for the test above: nothing else of ours in use, no wait."""
    window = make_window()
    _activate(window)
    report = _missing_required_report()
    _land_check(window, report, launch=True)
    assert resolutions == [report]


def test_a_check_the_user_started_is_answered_at_once_over_setup_and_updates(
    make_window: Callable[..., Any], resolutions: list[object]
) -> None:
    """About's Check again and the re-check after host setup are silent too
    (`show_summary=False`), so silence cannot be the launch marker: started
    from the window the user is in, their answer is not held behind it."""
    window = make_window()
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    report = _missing_required_report()
    _land_check(window, report, launch=False)
    assert resolutions == [report], "a check the user started was held"


def test_asking_during_the_launch_check_makes_it_the_users(
    make_window: Callable[..., Any],
    resolutions: list[object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Check again while the launch check is still probing: the one running
    check answers both (never a second probe), so it stops being the launch
    check, and its result is answered at once."""
    import platterpus.workers as workers

    monkeypatch.setattr(workers, "start_worker_thread", lambda *a, **k: None)
    window = make_window()
    _activate(window)
    window.run_dependency_check_async(launch=True)
    assert window._dep_check_is_launch, "floor: the launch check is not marked"
    setup = window.open_setup_center()
    _activate(setup)
    window._recheck_dependencies_for(lambda: None)
    assert not window._dep_check_is_launch, "the user's request left it held"

    report = _missing_required_report()
    window._on_dependency_check_done(report)  # the running check lands
    assert resolutions == [report]


def test_a_newer_check_drops_a_held_launch_report(
    make_window: Callable[..., Any],
    resolutions: list[object],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The one way a held report of a missing tool is dropped: a newer check
    has started, and its own report takes the held one's place, so the stale
    one does not open as a second resolver when the user comes back."""
    import platterpus.workers as workers

    window = make_window()
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    _land_check(window, _missing_required_report(), launch=True)
    _wait(0.05)
    assert window._dep_resolve_deferrals > 0, "floor: the report was not held"

    # The newer check is started, not run: no container.
    monkeypatch.setattr(workers, "start_worker_thread", lambda *a, **k: None)
    window.run_dependency_check_async(show_summary=True)
    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        _wait(0.2)
    assert "dropped a held dependency report" in caplog.text, caplog.text
    setup.close()
    _activate(window)
    _wait(0.2)
    assert resolutions == [], "a superseded report opened"
    window._dep_check_worker = None
    window._dep_check_thread = None


def test_only_the_launch_passes_the_launch_marker() -> None:
    """Read from the source, because the launch call runs in `app.main`, which
    a test cannot start without starting the app. Every other caller (Check
    dependencies, About's Check again, the re-check after host setup) is
    started by the user and must be answered at once, so none may pass it."""
    import ast
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src" / "platterpus"
    calls: list[tuple[str, object]] = []
    for path in sorted(src.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "run_dependency_check_async"
            ):
                launch = next(
                    (k.value for k in node.keywords if k.arg == "launch"), None
                )
                value = launch.value if isinstance(launch, ast.Constant) else launch
                calls.append((path.relative_to(src).as_posix(), value))
    assert len(calls) >= 3, f"floor: only {calls} found, the scan broke"
    marked = [where for where, value in calls if value is not None]
    assert marked == ["app.py"], calls
    assert ("app.py", True) in calls, calls
