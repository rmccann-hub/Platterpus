"""The first-run setup answer is the decision for that launch (UX review of 0.7.127).

**F1, the defect.** On a fresh install the first launch asks whether to install
the ripping tools. The launch dependency check is still running, or held, while
that question is open (`_defer_if_floor_is_busy`), and when the question closed
it was delivered and `_resolve_missing_unified` opened the setup wizard anyway.
So **No** was followed, within ten seconds, by the wizard, a "Dependency check
complete" box listing *"Install failures: cyanrip: still missing after setup"*
for a setup that never ran, and a *"cyanrip update"* box (F2). The reviewer's
log read "delivering the held dependency report now → dialog presented:
HostSetupDialog".

These tests drive the real window through that sequence: the report lands while
the question is open, is held, and is delivered once it is answered. They stub
only what cannot run here: the question's answer, the wizard's own run, and the
file lookup that says whether a ripper is installed.

**F2** is the update offer: not shown while no ripper is installed, and, where
it is shown, one plain question with the record under Show Details. **F4** is
the question's title and the wizard's empty log box.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from conftest import stop_window_threads
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from test_ui_main_window import _make_window

from platterpus.config import Config
from platterpus.deps.checks import ProbeResult
from platterpus.deps.manager import DependencyReport
from platterpus.deps.registry import DependencySpec, Tier
from platterpus.deps.resolvers import MissingItem
from platterpus.ui import main_window_deps, message_boxes

_ABSENT = ProbeResult(present=False, version=None, location=None)


@pytest.fixture()
def make_window(qapp: QApplication) -> Iterator[Callable[..., Any]]:
    """A real MainWindow, hidden and its threads stopped afterwards."""
    created: list[Any] = []

    def factory(**kwargs: Any) -> Any:
        window = _make_window(qapp, **kwargs)
        created.append(window)
        return window

    yield factory
    for window in created:
        for child in window.findChildren(QDialog):
            child.close()
        window.hide()
        stop_window_threads(window)
        window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


class _StubSignal:
    def connect(self, *_a: object, **_k: object) -> None:
        return None


@pytest.fixture()
def wizards(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """Every setup wizard the window built, recorded instead of run.

    Its `exec()` returns at once without running setup: the user closed it, or
    (for the Yes test) the run did not make the ripper usable. Either way the
    ripper is still missing afterwards, which is the state the held report meets.
    """
    import platterpus.ui.host_setup_dialog as hsd

    built: list[object] = []

    class FakeWizard:
        def __init__(self, *_a: object, **_k: object) -> None:
            built.append(self)
            self.setup_finished = _StubSignal()

        def exec(self) -> int:
            return 0

        def raise_(self) -> None:
            return None

        def activateWindow(self) -> None:  # Qt API
            return None

    monkeypatch.setattr(hsd, "HostSetupDialog", FakeWizard)
    return built


@pytest.fixture()
def boxes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every information/warning box and every `open()`ed message box, by title."""
    shown: list[str] = []
    monkeypatch.setattr(
        message_boxes, "information", lambda _p, title, *_a, **_k: shown.append(title)
    )
    monkeypatch.setattr(
        message_boxes, "warning", lambda _p, title, *_a, **_k: shown.append(title)
    )
    monkeypatch.setattr(
        QMessageBox, "open", lambda box: shown.append(box.windowTitle())
    )
    return shown


@pytest.fixture()
def no_ripper(monkeypatch: pytest.MonkeyPatch) -> None:
    """No ripper on this computer: the fresh install the review ran."""
    monkeypatch.setattr("platterpus.deps.host_setup.cyanrip_on_host", lambda: False)
    # Fast retries, so a held report is delivered within the test's wait.
    monkeypatch.setattr(main_window_deps, "_DEP_RESOLVE_RETRY_MS", 5)


def _cyanrip_missing() -> DependencyReport:
    """The launch report of a fresh install: cyanrip, a setup-wizard tool, absent."""
    spec = DependencySpec(
        dep_id="cyanrip",
        display_name="cyanrip",
        probe=lambda: _ABSENT,
        min_version=(0, 0, 0),
        tier=Tier.MANUAL,
        install_command=None,
        search_string="install cyanrip",
        from_setup_wizard=True,
    )
    return DependencyReport(missing=[MissingItem(spec=spec, probe=_ABSENT)])


def _wait(seconds: float) -> None:
    """Let the event loop run, retry timers included, for ``seconds``."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)


def _answer_with_the_report_landing_meanwhile(
    window: Any, monkeypatch: pytest.MonkeyPatch, answer: QMessageBox.StandardButton
) -> DependencyReport:
    """Ask the first-run question; the launch report lands while it is open.

    That is the order on a fresh install: the question opens at once, and the
    probe, entering a cold container, finishes inside its nested event loop. The
    question being open is what `_modal_floor_blocker` sees, so it is modelled
    there; the report is then held, and delivered by its own retry timer after
    the answer, exactly as in the field.
    """
    report = _cyanrip_missing()
    asking = [False]
    monkeypatch.setattr(
        window,
        "_modal_floor_blocker",
        lambda: "a dialog already has the floor (QMessageBox)" if asking[0] else "",
    )

    def question(*_a: object, **_k: object) -> QMessageBox.StandardButton:
        asking[0] = True
        window._dep_check_generation += 1  # the launch check, started at launch
        window._apply_dependency_report(
            window._dependency_manager, report, show_summary=False, launch=True
        )
        assert window._dep_resolve_deferrals == 1, "the report was not held"
        asking[0] = False
        return answer

    monkeypatch.setattr(message_boxes, "question", question)
    window._maybe_offer_host_setup()
    _wait(0.3)
    return report


def test_no_means_no_wizard_no_summary_and_a_notice_with_set_up(
    make_window: Callable[..., Any],
    wizards: list[object],
    boxes: list[str],
    no_ripper: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F1: after No, the held report opens nothing; the window says what is missing."""
    window = make_window(config=Config(host_setup_prompted=False))

    _answer_with_the_report_landing_meanwhile(
        window, monkeypatch, QMessageBox.StandardButton.No
    )

    assert window._dep_resolve_deferrals == 0, "the held report was never delivered"
    assert wizards == [], "answering No still opened the setup wizard"
    assert boxes == [], f"answering No was followed by {boxes}"
    notice = window._setup_needed_notice
    assert notice is not None and not notice.isHidden(), (
        "the user was not told the ripping tools are missing"
    )
    assert "not installed yet" in notice.text()
    assert notice.set_up_button().text() == "Set up…"

    # And the one way in still works: the strip's own button opens the wizard.
    notice.set_up_button().click()
    assert len(wizards) == 1, "Set up… did not open the setup wizard"


def test_yes_opens_exactly_one_wizard_even_after_the_held_report(
    make_window: Callable[..., Any],
    wizards: list[object],
    boxes: list[str],
    no_ripper: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After Yes the wizard has been shown; the held report must not open another.

    The wizard here closes without making the ripper usable, the case where the
    report still says cyanrip is missing when it is delivered. The window then
    says so in its strip rather than with a second wizard or a failure list.
    """
    window = make_window(config=Config(host_setup_prompted=False))

    _answer_with_the_report_landing_meanwhile(
        window, monkeypatch, QMessageBox.StandardButton.Yes
    )

    assert window._dep_resolve_deferrals == 0, "the held report was never delivered"
    assert len(wizards) == 1, f"{len(wizards)} setup wizards opened for one Yes"
    assert boxes == [], f"the held report was followed by {boxes}"
    notice = window._setup_needed_notice
    assert notice is not None and not notice.isHidden()


def test_the_notice_does_not_make_the_page_scroll_in_a_tall_window(
    make_window: Callable[..., Any],
    qapp: QApplication,
) -> None:
    """The strip must fit the page, not hold it at its tallest.

    Its first version word-wrapped its label, which asks for "height for
    width"; the scroll area obeyed that, kept the page at 888 px in an 840 px
    view and squeezed both track lists to their floors, caught by
    `test_the_taller_default_is_what_buys_the_extra_rows`. The label must also
    keep room for its second line in a narrow window.
    """
    window = make_window(config=Config(host_setup_prompted=True))
    window.show()
    window._show_setup_needed_notice()
    page = window._page_scroll.widget()
    viewport = window._page_scroll.viewport()

    window.resize(1000, 860)
    _wait(0.1)
    assert page.height() == viewport.height(), (
        f"the page is {page.height()} px in a {viewport.height()} px view: the "
        "notice made it scroll in a window tall enough for everything"
    )

    window.resize(640, 600)
    _wait(0.1)
    label = window._setup_needed_notice._label
    assert label.height() >= label.heightForWidth(label.width()), (
        "the notice's wrapped sentence is clipped in a narrow window"
    )


def test_a_check_the_user_starts_after_no_still_resolves(
    make_window: Callable[..., Any],
    no_ripper: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The answer covers the launch check, not a check the user asks for later."""
    window = make_window(config=Config(host_setup_prompted=False))
    monkeypatch.setattr(
        message_boxes, "question", lambda *_a, **_k: QMessageBox.StandardButton.No
    )
    window._maybe_offer_host_setup()
    resolved: list[object] = []
    monkeypatch.setattr(window, "_resolve_missing_unified", resolved.append)
    monkeypatch.setattr(window, "_show_dep_summary", lambda *_a, **_k: None)

    # A newer check (Setup & Updates → Check dependencies), and one that is silent
    # (Help → About → Check again): both started after the answer.
    for show_summary in (True, False):
        window._dep_check_generation += 1
        report = _cyanrip_missing()
        window._apply_dependency_report(
            window._dependency_manager, report, show_summary=show_summary
        )
        assert resolved and resolved[-1] is report, (
            f"a check started after the answer (show_summary={show_summary}) did "
            "not offer setup"
        )


def test_the_automatic_cyanrip_offer_is_not_shown_while_no_ripper_is_installed(
    make_window: Callable[..., Any],
    boxes: list[str],
    no_ripper: None,
) -> None:
    """F2: on a fresh install the launch-time update check raised "cyanrip update".

    The offer it raised is the real one `evaluate_offer` gives a machine with no
    fork build (`installed_commit=None`): auto-installable, and allowed to
    surface unprompted. The window is shown and free, so before the fix it
    opened at once.
    """
    from platterpus.deps.ripper_offer import evaluate_offer

    window = make_window(config=Config(host_setup_prompted=True))
    window.show()
    offer = evaluate_offer(None, installed_commit=None)
    assert offer.may_surface_unprompted and offer.auto_installable, (
        "the premise: this is an offer the automatic check would raise"
    )

    window._ripper_check_is_automatic = True
    window._on_ripper_update_result(offer)
    _wait(0.2)

    assert boxes == [], f"an unasked update offer opened with no ripper: {boxes}"
    assert window._ripper_offer_box is None
    assert window._held_ripper_offer is None, "the offer is waiting to be shown"


def test_a_setup_run_drops_an_automatic_offer_worked_out_before_it(
    make_window: Callable[..., Any],
    wizards: list[object],
) -> None:
    """F2: an offer held while the wizard was open describes the machine before setup.

    Setup installs the tested build, so showing that offer once the wizard closes
    would offer to install what was just installed. It is dropped; the next
    check asks again.
    """
    window = make_window(config=Config(host_setup_prompted=True))
    window._held_ripper_offer = object()  # waiting for the main window

    window.open_host_setup_dialog()

    assert len(wizards) == 1
    assert window._held_ripper_offer is None, "a pre-setup offer survived setup"


def test_the_install_offer_asks_in_plain_words_and_keeps_the_record_in_details(
    make_window: Callable[..., Any],
    boxes: list[str],
) -> None:
    """F2: the box asks one plain question; the handshake paragraph is under Details."""
    from platterpus import __version__
    from platterpus.deps.ripper_offer import evaluate_offer
    from platterpus.handshake_approval import (
        APPROVED_BY_ROUND,
        APPROVED_FOR_PLATTERPUS_VERSION,
    )

    window = make_window(config=Config(host_setup_prompted=True))
    offer = evaluate_offer(None, installed_commit=None)

    for consent, button in ((False, "Install it now"), (True, "Install it anyway")):
        window._offer_ripper_install(
            offer, offer.detail, offer.install_commit, needs_consent=consent
        )
        box = window._ripper_offer_box
        assert box is not None
        text = box.text()
        for jargon in ("handshake", "unapproved", "commit", "round", __version__):
            assert jargon not in text, f"{jargon!r} in the question: {text!r}"
        assert "?" in text, text
        assert box.detailedText() == offer.detail, "the record is not under Details"
        assert button in [b.text() for b in box.buttons()], "the README names it"
        window._ripper_offer_box = None

    # The record names the version the round TESTED WITH, and says so, so it
    # cannot be read as the app calling itself an older version.
    assert (
        f"round {APPROVED_BY_ROUND} approved, testing it with Platterpus "
        f"{APPROVED_FOR_PLATTERPUS_VERSION}" in offer.detail
    ), offer.detail


def test_a_wizard_closed_unused_is_reported_as_not_installed_yet(
    make_window: Callable[..., Any],
    wizards: list[object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F1: nothing was attempted, so nothing is called an install failure."""
    window = make_window(config=Config(host_setup_prompted=True))
    shown: list[str] = []
    monkeypatch.setattr(
        message_boxes, "information", lambda _p, _t, text, *_a, **_k: shown.append(text)
    )
    monkeypatch.setattr(
        message_boxes, "warning", lambda _p, _t, text, *_a, **_k: shown.append(text)
    )
    report = _cyanrip_missing()

    window._resolve_missing_unified(report)
    window._show_dep_summary(report)

    assert len(wizards) == 1
    assert shown, "no summary was shown"
    summary = shown[-1]
    assert "Not installed yet: cyanrip" in summary, summary
    assert "Install failures" not in summary, summary
    assert "still missing after setup" not in summary, summary


def test_the_question_and_the_wizard_have_different_titles(
    make_window: Callable[..., Any],
    monkeypatch: pytest.MonkeyPatch,
    no_ripper: None,
) -> None:
    """F4: two windows called "Set up Platterpus", and "Run setup…." ended a line."""
    from platterpus.ui.host_setup_dialog import SetupCopy

    window = make_window(config=Config(host_setup_prompted=False))
    asked: list[tuple[str, str]] = []

    def question(_p: object, title: str, text: str, *_a: object) -> object:
        asked.append((title, text))
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(message_boxes, "question", question)
    window._maybe_offer_host_setup()

    title, text = asked[0]
    assert title == "Install the ripping tools?"
    assert title != SetupCopy().title
    assert "…." not in text, text


def test_the_setup_wizard_hides_its_empty_log_until_a_step_reports(
    qapp: QApplication,
) -> None:
    """F4: the wizard opened on an empty box filling half of it."""
    from platterpus.deps.step_engine import StepResult, StepStatus
    from platterpus.ui.host_setup_dialog import HostSetupDialog

    class _NeverReady:
        def is_ready(self) -> bool:
            return False

    dialog = HostSetupDialog(None, host_setup=_NeverReady())  # type: ignore[arg-type]  # a stand-in HostSetup
    try:
        assert dialog._results.isHidden(), "the empty log box is shown"
        dialog._on_step(StepResult("distrobox", "Distrobox", StepStatus.DONE, "ok"))
        assert not dialog._results.isHidden(), "a step's line went into a hidden box"
        assert "Distrobox" in dialog._results.toPlainText()
    finally:
        dialog.deleteLater()
