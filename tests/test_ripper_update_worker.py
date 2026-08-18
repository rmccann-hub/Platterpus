"""The ripper update check off the GUI thread, and the window methods around it.

`test_ripper_manifest.py` covers the parsing and the decision. This covers the
parts that touch Qt: the worker, its cancel, and the four window methods that
read the setting, read the installed build, and render the verdict.

Those were the untested half, and the worker in particular is where "cancel is a
real interrupt" has to hold — a flag the blocked read never checks is a false
promise (`CLAUDE.md` rule 9), and the no-cancel ratchet in
`tests/test_qthread_ownership.py` only shrinks.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from platterpus.deps import fork_source
from platterpus.deps.ripper_manifest import CancellableFetcher
from platterpus.deps.ripper_offer import (
    OFFER_AVAILABLE,
    OFFER_NOT_DETERMINED,
    OFFER_UP_TO_DATE,
)

pytest.importorskip("PySide6.QtWidgets")

MANIFEST: dict[str, Any] = {
    "schema": 1,
    "project": "cyanrip-fork",
    "default_channel": "stable",
    "channels": {
        "stable": {
            "version": "0.9.4-rc1+platterpus.5",
            "commit": "ddf7ac3",
            "release_seq": 11,
            "handshake_round": 7,
            "round_closed": True,
            "install": "https://github.com/rmccann-hub/cyanrip/archive/ddf7ac3.tar.gz",
        }
    },
}


def _serve(
    monkeypatch, body: str | None = None, error: Exception | None = None
) -> None:
    """Make the REAL fetcher return `body` (or raise `error`).

    Patched at `urlopen` rather than at `_default_fetch`, because the worker does
    not use `_default_fetch`: it passes its own `CancellableFetcher.fetch` so the
    read stays interruptible. Patching the convenience function would have left
    the worker talking to the real network — a test that appears to control its
    input and does not.
    """
    import platterpus.deps.ripper_manifest as rm

    class _Response:
        def read(self, _size: int) -> bytes:
            if error is not None:
                raise error
            return (body or "").encode()

        def close(self) -> None:
            pass

    def _open(*_a: object, **_k: object) -> _Response:
        if error is not None:
            raise error
        return _Response()

    monkeypatch.setattr(rm.urllib.request, "urlopen", _open)


# --- The worker --------------------------------------------------------------


def test_the_worker_emits_an_offer_never_none(qapp, process_until, monkeypatch) -> None:
    """ "Couldn't determine" is a verdict this subsystem carries explicitly.

    Emitting `None` for it would push the distinction onto every caller, and the
    caller that forgets is the one that renders "unknown" as reassurance.
    """
    from platterpus.workers.ripper_update_worker import RipperUpdateWorker

    _serve(monkeypatch, json.dumps(MANIFEST))

    seen: list[object] = []
    worker = RipperUpdateWorker(channel="stable", installed_commit="ddf7ac3")
    worker.finished.connect(seen.append)
    worker.run()

    assert len(seen) == 1
    assert seen[0] is not None
    assert getattr(seen[0], "verdict", "") == OFFER_UP_TO_DATE


def test_the_worker_reports_not_determined_when_the_fetch_fails(qapp, monkeypatch):
    """An unreachable manifest is "not determined", never "you're up to date".

    ``installed_commit`` is pinned to a build we DO recognise so the manifest is the
    only variable. Without that this test was measuring two failures at once — no
    network *and* no cyanrip on the test machine — and after the 2026-08-18 redesign
    the second one answers first (see the offline-mismatch test below). Two causes,
    one assertion, is how a test starts passing for a reason nobody intended.
    """
    from platterpus.workers.ripper_update_worker import RipperUpdateWorker

    _serve(monkeypatch, error=OSError("network unreachable"))

    seen: list[object] = []
    worker = RipperUpdateWorker(installed_commit=fork_source.FORK_PIN)
    worker.finished.connect(seen.append)
    worker.run()

    assert len(seen) == 1
    assert getattr(seen[0], "verdict", "") == OFFER_NOT_DETERMINED


def test_a_wrong_installed_build_is_reported_even_with_no_network(qapp, monkeypatch):
    """The mismatch is a LOCAL fact, so it must survive an unreachable manifest.

    This is the case the redesign exists for, and answering it needs no network at
    all: two constants in this repository (the pin, and what the binary said it is).
    The old order asked the manifest first and therefore had nothing to say when it
    was unreachable — a dead end reached by the one user who had it.
    """
    from platterpus.deps.ripper_offer import OFFER_MISMATCHED
    from platterpus.workers.ripper_update_worker import RipperUpdateWorker

    _serve(monkeypatch, error=OSError("network unreachable"))

    # `deadbee` is unknown to `FORK_RELEASE_SEQ_BY_PIN`, deliberately. `c4d1a00`
    # would NOT do: it is the fork's published release 16 and we record its
    # sequence, so it is recognised and takes the up-to-date path instead.
    seen: list[Any] = []
    worker = RipperUpdateWorker(installed_commit="deadbee")
    worker.finished.connect(seen.append)
    worker.run()

    assert seen[0].verdict == OFFER_MISMATCHED
    assert seen[0].install_commit == fork_source.FORK_PIN
    assert seen[0].auto_installable is True


def test_a_cancelled_check_produces_no_offer_to_act_on(qapp, monkeypatch):
    """Cancel means the window is closing. It must not hand back an install prompt.

    Before the one-click install existed, a cancelled check's verdict was harmless
    text. Now an offer can drive a modal, so a late `finished` from an abandoned
    check is a dialog appearing out of a window the user just closed.
    """
    from platterpus.workers.ripper_update_worker import RipperUpdateWorker

    _serve(monkeypatch, error=OSError("cancelled mid-read"))

    seen: list[Any] = []
    # A commit that WOULD produce an actionable mismatch offer, so the assertion
    # below is about the cancel and not about there being nothing to offer.
    worker = RipperUpdateWorker(installed_commit="deadbee")
    worker.finished.connect(seen.append)
    worker.cancel()
    worker.run()

    assert len(seen) == 1, "a cancelled worker must still finish, or it is never joined"
    assert seen[0].verdict == OFFER_NOT_DETERMINED
    assert seen[0].install_commit == "", "a cancelled check must offer no action"
    assert seen[0].auto_installable is False


def test_the_worker_still_finishes_when_evaluation_itself_explodes(qapp, monkeypatch):
    """A worker must ALWAYS finish. A thread that never emits is a thread that
    never gets joined, and `stop_thread` then waits out the shutdown budget."""
    import platterpus.deps.ripper_offer as offer_mod
    from platterpus.workers import ripper_update_worker as mod

    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("evaluation exploded")

    # The handler re-imports evaluate_offer inside run(), so patch the module.
    monkeypatch.setattr(offer_mod, "evaluate_offer", boom)

    seen: list[object] = []
    worker = mod.RipperUpdateWorker()
    worker.finished.connect(seen.append)
    # The except branch calls evaluate_offer again to build the "not determined"
    # answer; if that also raises, run() must still not propagate.
    try:
        worker.run()
    except RuntimeError:
        pytest.fail("run() propagated an exception — a worker must always finish")
    assert len(seen) <= 1, "at most one finished emission"


def test_the_worker_offers_the_newer_build_with_its_consequence(qapp, monkeypatch):
    from platterpus.workers.ripper_update_worker import RipperUpdateWorker

    ahead = json.loads(json.dumps(MANIFEST))
    ahead["channels"]["stable"].update(
        {"release_seq": 20, "commit": "beefcaf", "handshake_round": 9}
    )
    _serve(monkeypatch, json.dumps(ahead))

    seen: list[Any] = []
    worker = RipperUpdateWorker(channel="stable", installed_commit="ddf7ac3")
    worker.finished.connect(seen.append)
    worker.run()

    assert seen[0].verdict == OFFER_AVAILABLE
    assert seen[0].would_be_unapproved is True
    assert "unapproved" in seen[0].detail


def test_the_worker_cancel_is_wired_to_the_fetcher(qapp) -> None:
    """`cancel()` must reach the thing that can actually break a blocked read.

    Structural, deliberately: the runtime behaviour (a closed socket makes the
    read raise) needs a real network to demonstrate, but *that the worker's cancel
    reaches the fetcher at all* is what makes it more than a flag — and it is what
    would silently regress if someone replaced the fetcher with a plain function.
    """
    from platterpus.workers.ripper_update_worker import RipperUpdateWorker

    worker = RipperUpdateWorker()
    assert isinstance(worker._fetcher, CancellableFetcher)
    worker.cancel()
    assert worker._fetcher._cancelled is True
    # Idempotent, because teardown can call it twice.
    worker.cancel()


def test_a_cancelled_worker_refuses_to_fetch(qapp, monkeypatch) -> None:
    """The cancel must take effect even if it lands before run() starts.

    The gap between constructing a worker and its thread actually running is real;
    a cancel landing there must not be ignored, or the window tears down while a
    network read it already abandoned is still starting.
    """
    from platterpus.workers.ripper_update_worker import RipperUpdateWorker

    worker = RipperUpdateWorker(installed_commit=fork_source.FORK_PIN)
    worker.cancel()

    seen: list[Any] = []
    worker.finished.connect(seen.append)
    worker.run()
    assert seen[0].verdict == OFFER_NOT_DETERMINED


# --- The fetcher's own bounds ------------------------------------------------


def test_the_fetcher_refuses_an_over_cap_body(monkeypatch) -> None:
    """An unbounded read has no upside; the cap is the half that matters."""
    import platterpus.deps.ripper_manifest as rm

    class _Response:
        def read(self, size: int) -> bytes:
            return b"x" * size  # always one byte past the cap

        def close(self) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_exc: object) -> None:
            pass

    monkeypatch.setattr(rm.urllib.request, "urlopen", lambda *_a, **_k: _Response())
    with pytest.raises(ValueError, match="exceeded"):
        CancellableFetcher().fetch("https://example.invalid/m.json")


def test_the_fetcher_returns_the_body_it_read(monkeypatch) -> None:
    """Non-triviality floor: the refusal tests above must be refusing something
    that otherwise works."""
    import platterpus.deps.ripper_manifest as rm

    payload = json.dumps(MANIFEST).encode()

    class _Response:
        def read(self, _size: int) -> bytes:
            return payload

        def close(self) -> None:
            pass

    monkeypatch.setattr(rm.urllib.request, "urlopen", lambda *_a, **_k: _Response())
    assert CancellableFetcher().fetch("https://example.invalid/m.json") == (
        payload.decode()
    )


def test_a_cancel_during_the_read_discards_the_result(monkeypatch) -> None:
    """A body that arrived after the user closed the window is not an answer."""
    import platterpus.deps.ripper_manifest as rm

    fetcher = CancellableFetcher()

    class _Response:
        def read(self, _size: int) -> bytes:
            fetcher.cancel()  # the GUI thread closes us mid-read
            return b"{}"

        def close(self) -> None:
            pass

    monkeypatch.setattr(rm.urllib.request, "urlopen", lambda *_a, **_k: _Response())
    with pytest.raises(ValueError, match="cancelled"):
        fetcher.fetch("https://example.invalid/m.json")


# --- The window methods ------------------------------------------------------


def _stub_window(config: object) -> Any:
    """Just enough window for the mixin methods, which take only `self`.

    A real `QWidget`, not a bare object: `_on_ripper_update_result` builds a
    `QMessageBox(self)`, and Qt refuses a non-widget parent. A plain stub passed
    that check only because the first version of these tests never reached the
    dialog — the stub was quietly narrower than the thing it stood in for.

    **Every attribute here is one `MainWindow.__init__` really sets**, and the mixin
    reads them as plain `self._x` rather than through `getattr(..., default)`. That
    is the point: a missing one raises here, loudly, in the test — which is exactly
    how the `_ripper_check_is_automatic` slot got added to this stub. A defaulted
    read would have passed silently in both the harness and the product, which is
    the `_observed_ripper_banner` defect this file's own subject matter is about.
    """
    from PySide6.QtWidgets import QWidget

    from platterpus.ui.main_window_update import UpdateMixin

    # **A QWidget that really carries the mixin**, not a bare one. Calling
    # `UpdateMixin._method(stub)` unbound reaches a sibling method the moment one
    # branch delegates to another (`_on_ripper_update_result` →
    # `_offer_ripper_install`), and a bare QWidget answers that with
    # AttributeError — a stand-in narrower than the product, which is the failure
    # this file's own docstring is about. `MainWindowShared` is `object` at
    # runtime, so this adds no Qt base beyond QWidget.
    class _StubWindow(QWidget, UpdateMixin):
        pass

    win = _StubWindow()
    win._config = config
    win._ripper_update_worker = None
    win._ripper_update_thread = None
    win._ripper_check_is_automatic = False
    win._ripper_offer_box = None
    win._ripper_offer = None
    win._ripper_offer_commit = ""
    win._rip_thread = None
    return win


def test_the_channel_is_read_live_and_falls_back_to_stable(qapp) -> None:
    """A value the validator would reject must not widen what a user is offered."""
    import dataclasses

    from platterpus.config import Config
    from platterpus.ui.main_window_update import UpdateMixin

    good = _stub_window(dataclasses.replace(Config(), ripper_channel="beta"))
    assert UpdateMixin._ripper_channel(good) == "beta"

    bad = _stub_window(dataclasses.replace(Config(), ripper_channel="nightly"))
    assert UpdateMixin._ripper_channel(bad) == "stable"

    missing = _stub_window(object())
    assert UpdateMixin._ripper_channel(missing) == "stable"


@pytest.mark.parametrize(
    ("banner", "expected"),
    [
        ("cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)", "ddf7ac3"),
        ("cyanrip 0.9.4 (platterpus-fork-gddf7ac3-dirty)", "ddf7ac3-dirty"),
        ("cyanrip 0.9.3", None),  # no parenthetical at all
        ("cyanrip 0.9.3 (some-other-tag)", None),  # not a fork tag
        ("cyanrip 0.9.3 (platterpus-fork-g)", None),  # tag present, sha empty
        ("", None),
    ],
)
def test_the_installed_commit_is_read_off_the_banner(banner, expected) -> None:
    """Best-effort and never raising: every failure mode is already "not determined".

    **Repointed 2026-08-17, and the move is the fix.** This used to call
    ``UpdateMixin._installed_ripper_commit(window)``, whose only input was a cached
    ``window._observed_ripper_banner`` — an attribute assigned **nowhere in src/**,
    and assigned *here*, by ``_stub_window``. That is precisely what made the dead
    code look wired: the test supplied the producer the product lacked, so the
    parsing was exercised while the path that fed it in production returned ``None``
    on every call. The window then reported the build-time constant ``FORK_PIN`` as
    "what you have", forever, including right after a successful install.

    The parsing now lives in :func:`platterpus.ripper_identity.fork_commit_from_banner`
    and the worker probes the binary for the banner itself, so there is no cache to
    populate and nothing for a stub to stand in for. The cases below are unchanged —
    they were always the right cases, asked of the wrong object.
    """
    from platterpus.ripper_identity import fork_commit_from_banner

    assert fork_commit_from_banner(banner) == expected


def test_the_verdict_dialog_renders_plain_text_never_html(qapp, monkeypatch) -> None:
    """**The inbound-seam rule, at the widget that shows dependency output.**

    Qt's default `AutoText` auto-detects HTML. This paragraph carries a version
    string and a commit read out of a *network document*, and album titles reaching
    other panes come from MusicBrainz — so a value containing `<` would be swallowed
    as an unknown tag and the user would never learn text went missing. Asserted on
    the constructed box rather than trusted to review.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox

    from platterpus.deps.ripper_offer import RipperOffer
    from platterpus.ui.main_window_update import UpdateMixin

    built: list[QMessageBox] = []
    real_exec = QMessageBox.exec

    def _capture(self: QMessageBox) -> int:
        built.append(self)
        return 0

    monkeypatch.setattr(QMessageBox, "exec", _capture)
    try:
        window = _stub_window(object())
        offer = RipperOffer(
            verdict=OFFER_AVAILABLE,
            channel="stable",
            release=None,
            detail="a <newer> build exists",
        )
        UpdateMixin._on_ripper_update_result(window, offer)
    finally:
        monkeypatch.setattr(QMessageBox, "exec", real_exec)

    assert len(built) == 1, "the verdict must be shown, not swallowed"
    box = built[0]
    assert box.textFormat() == Qt.TextFormat.PlainText, (
        "dependency output must render as PlainText; AutoText would interpret "
        "'<newer>' as markup and silently drop it"
    )
    assert "<newer>" in box.text(), "the literal text must survive to the widget"
    # And the in-flight slots are cleared, so a second check is possible.
    assert window._ripper_update_worker is None
    assert window._ripper_update_thread is None


def test_a_verdict_with_no_detail_still_says_something(qapp, monkeypatch) -> None:
    """A dialog with an empty body is the 'accurate and useless' failure."""
    from PySide6.QtWidgets import QMessageBox

    from platterpus.ui.main_window_update import UpdateMixin

    # Capture the TEXT at exec time, not the widget. The box is parented to the
    # window, so holding the widget past the test means reading a C++ object Qt
    # has already deleted — `libshiboken: Internal C++ object already deleted`.
    shown: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "exec", lambda self: shown.append(self.text()) or 0
    )

    window = _stub_window(object())
    UpdateMixin._on_ripper_update_result(window, object())
    assert shown and shown[0].strip(), "an empty verdict dialog tells nobody anything"


def test_a_second_check_is_refused_while_one_is_in_flight(qapp) -> None:
    """One at a time, so a slow check cannot spawn a thread per click."""
    from platterpus.ui.main_window_update import UpdateMixin

    window = _stub_window(object())
    window._ripper_update_thread = object()  # pretend one is running
    UpdateMixin._on_check_ripper_updates(window)
    # No worker was constructed, so nothing to join — the guard returned early.
    assert window._ripper_update_worker is None


# --- The automatic check must not interrupt anyone ----------------------------


def test_constructing_a_window_does_not_arm_the_automatic_check() -> None:
    """**A regression test for a hang this change itself caused**, found and fixed
    the same hour (2026-08-18).

    The automatic check was first armed by a `QTimer.singleShot` in
    `MainWindow.__init__`. The suite builds `MainWindow` directly in dozens of
    tests, and several then spin a nested event loop for longer than the delay — so
    the timer fired, the check found no fork ripper on the test machine, produced a
    one-click install offer, and `exec()`d a `QMessageBox` **with nobody to click
    it**. The run stopped at 56% and stayed there.

    **The fix is structural, not a harness flag**, and this asserts the structure:
    "a window exists" and "the application started" are different events, and only
    the second licenses interrupting somebody. Arming it from `app.py` is the same
    reason `refresh_drives()` is called from there. A test-mode branch in the
    product would have hidden a real hazard — a dialog that can appear at a moment
    nobody chose — behind a green suite.
    """
    import ast
    import inspect

    from platterpus.ui import main_window

    source = inspect.getsource(main_window)
    tree = ast.parse(source)
    window = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "MainWindow"
    )
    init = next(
        node
        for node in window.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    scheduled = [
        node.args[1].attr
        for node in ast.walk(init)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "singleShot"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Attribute)
    ]
    assert "_maybe_check_ripper_updates" not in scheduled, (
        "MainWindow.__init__ arms the automatic cyanrip check again. It must be "
        "armed from app.py's launch path — see "
        "MainWindow.schedule_ripper_update_check. Constructing a window must never "
        "schedule something that can open a modal."
    )
    # The floor: this must be looking at a real `__init__` that really does schedule
    # things, or it passes by finding nothing.
    assert scheduled, (
        "no `QTimer.singleShot(..., self.<method>)` found in MainWindow.__init__ at "
        "all — the detector is not seeing the population it polices, so the "
        "assertion above is vacuous"
    )


def test_the_launch_path_does_arm_it() -> None:
    """The converse. Without this, deleting the call entirely passes the test above.

    Asserted on `app.py`'s source rather than by launching the app: the call sits
    inside the `QApplication` branch, and reaching it for real means a window and an
    event loop, which is the very thing this pair is about not doing in a test.
    """
    from pathlib import Path

    app_source = (
        Path(__file__).resolve().parents[1] / "src" / "platterpus" / "app.py"
    ).read_text(encoding="utf-8")
    assert "window.schedule_ripper_update_check()" in app_source, (
        "app.py no longer arms the automatic cyanrip check, so nothing does — the "
        "'do not arm it in __init__' test above would still pass"
    )


def test_a_scripted_run_never_arms_the_automatic_check() -> None:
    """**A modal must never appear in an unattended run.**

    A script drives the real GUI for 30-50 minutes on the rig with nobody watching.
    An offer raised eight seconds in would stand there blocking the batch until
    somebody happened to look — and answering it *yes* would swap the ripper
    **mid-session**, invalidating the very evidence the session exists to produce.

    Found by the suite on 2026-08-18, which drives this same path: two `cyanrip
    update` dialogs were left standing over the script console, and an unrelated
    `_active_dialog()` assertion three files later was what reported it. The
    harness found a product bug, which is the right way round.

    Asserted on the source because the alternative is launching a real app with a
    real event loop — the exact thing that made this expensive to find.
    """
    import re
    from pathlib import Path

    app_source = (
        Path(__file__).resolve().parents[1] / "src" / "platterpus" / "app.py"
    ).read_text(encoding="utf-8")
    guard = re.search(
        r"if not _autorun:\s*\n\s*try:\s*\n\s*window\.schedule_ripper_update_check\(\)",
        app_source,
    )
    assert guard is not None, (
        "app.py arms the automatic cyanrip check without checking `_autorun`. A "
        "scripted run is a harness run: interrupting it with a modal blocks the "
        "batch, and taking the offer swaps the ripper mid-session."
    )


def test_the_automatic_check_stands_down_during_a_rip(qapp) -> None:
    """A rip can start inside the delay — the user came to rip a disc.

    The offer ends in a modal, and the install it offers replaces the binary doing
    the ripping. So the automatic check skips entirely; the menu item is unaffected.
    """
    from platterpus.ui.main_window_update import UpdateMixin

    window = _stub_window(object())
    # SHOWN, deliberately. The check also stands down for a window that is not on
    # screen, so an unshown stub would make this pass for the wrong reason — it
    # would still pass with the rip guard deleted.
    window.show()
    qapp.processEvents()
    assert window.isVisible(), "the fixture must clear the visibility guard first"
    window._rip_thread = object()  # pretend a rip is running
    UpdateMixin._maybe_check_ripper_updates(window)
    assert window._ripper_update_worker is None, (
        "the automatic check started a worker while a rip was running"
    )
    assert window._ripper_update_thread is None


def test_the_install_offer_is_never_shown_with_exec() -> None:
    """**A structural guard, because the failure mode is a hang and not a crash.**

    `_offer_ripper_install` is reached from a *queued signal* — the update worker
    finishing — and on the automatic path that worker was started by a timer.
    `exec()` spins a **nested event loop** inside whatever the GUI thread was doing.
    Measured 2026-08-18: the suite reached that line from an unrelated test's
    `qapp.processEvents()` and stopped there, forever, with nobody to click the
    button. A user meets the same shape as a frozen window.

    Asserted on the source rather than by observing behaviour, for the reason this
    project keeps rediscovering: the safe version and the broken version *look*
    identical at every surface except the one line, and a behavioural test for "did
    it not hang" is a test that hangs when it fails.

    `exec()` elsewhere in this mixin is fine and deliberately still allowed — a
    menu action is user-initiated and synchronous. Only the dialog that a timer can
    raise is held to `open()`.
    """
    import ast
    import inspect

    from platterpus.ui import main_window_update

    tree = ast.parse(inspect.getsource(main_window_update))
    offer = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_offer_ripper_install"
    )
    calls = [
        node.func.attr
        for node in ast.walk(offer)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert "exec" not in calls, (
        "_offer_ripper_install calls exec(). It is raised from a queued signal, so "
        "that nests an event loop inside whatever the GUI thread was doing — the "
        "hang measured on 2026-08-18. Use open() and handle buttonClicked."
    )
    assert "open" in calls, (
        "_offer_ripper_install no longer shows the dialog at all — the assertion "
        "above would pass for a method that does nothing"
    )
    # And the answer must actually be wired, or `open()` shows a dialog that
    # decides nothing.
    assert "connect" in calls, "buttonClicked is not connected; the answer is lost"


def test_the_exec_detector_would_catch_the_shipped_shape() -> None:
    """Non-triviality: the detector must match the code that actually hung."""
    import ast

    shipped = ast.parse("def _offer_ripper_install(self):\n    box.exec()\n")
    calls = [
        node.func.attr
        for node in ast.walk(shipped)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert "exec" in calls, "the detector misses a bare `box.exec()`"


def test_the_automatic_check_never_offers_a_step_backwards(qapp, monkeypatch) -> None:
    """Being AHEAD of the pin is a deliberate state; do not nag about it at launch.

    A user on a newer *published* release installed it on purpose — during a joint
    hardware session, say. Their rips do report `unapproved`, the menu says so, and
    a one-click way back is offered there. Raising it unprompted every launch would
    be the app asking someone to undo a decision they made, which is the opposite of
    *"it shouldnt need to be explicity callled out … unless very impartant."*

    Measured against the real situation: round 11's own record has `FORK_PIN`
    staying at `ddf7ac3` while the fork's published stable moved to `c4d1a00`
    (byte-identical in `src/` to the `c455683` that round reviewed and approved), so
    this is the state the maintainer's own rig is in — not a hypothetical.
    """
    from PySide6.QtWidgets import QMessageBox

    from platterpus.deps.ripper_offer import OFFER_UP_TO_DATE, RipperOffer
    from platterpus.ui.main_window_update import UpdateMixin

    shown: list[str] = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: shown.append("exec") or 0)
    monkeypatch.setattr(QMessageBox, "open", lambda self: shown.append("open"))

    ahead = RipperOffer(
        verdict=OFFER_UP_TO_DATE,
        channel="stable",
        release=None,
        detail="newest published, but not the approved pin",
        install_commit=fork_source.FORK_PIN,
        auto_installable=True,
    )

    window = _stub_window(object())
    window._ripper_check_is_automatic = True
    UpdateMixin._on_ripper_update_result(window, ahead)
    assert not shown, (
        f"the automatic check interrupted with {shown} to offer a downgrade"
    )

    # The converse, so this cannot pass by the automatic path being dead: asked
    # directly (the menu), the very same offer DOES surface, with its button.
    window = _stub_window(object())
    window._ripper_check_is_automatic = False
    UpdateMixin._on_ripper_update_result(window, ahead)
    assert shown == ["open"], (
        f"the menu path must still offer the way back; got {shown}"
    )


def test_the_automatic_check_stands_down_when_the_window_is_not_shown(qapp) -> None:
    """The timer fires seconds after launch; by then the window may be gone.

    `test_app_smoke` starts the real app and closes the window — and the timer
    still fired on it, leaving an install dialog standing over the rest of the
    suite (2026-08-18). A user meets the same shape as a dialog appearing after
    they quit. `isVisible()` is the third of the three conditions an interruption
    is subject to: a person is here, they are not busy, and it is worth asking.
    """
    from platterpus.ui.main_window_update import UpdateMixin

    window = _stub_window(object())  # never shown
    assert not window.isVisible()
    UpdateMixin._maybe_check_ripper_updates(window)
    assert window._ripper_update_worker is None, (
        "the automatic check ran against a window nobody is looking at"
    )


def test_dismissing_the_offer_clears_its_slots_and_installs_nothing(qapp) -> None:
    """Both ways out, because the dialog is non-blocking and holds state on `self`.

    `open()` means the answer arrives later, so the offer and the commit live on the
    window until it does. A dialog closed with **Esc or the window's close box**
    clicks no button — without a `finished` handler those slots stayed set, pointing
    at a dialog nobody can answer, and PySide6 turns the next access into "Internal
    C++ object already deleted" once Qt reaps it.

    Also asserts the decline button installs nothing, which is the half a reader
    would assume and the half worth pinning: `_begin_ripper_install` shells out.
    """
    from PySide6.QtWidgets import QMessageBox

    from platterpus.ui.main_window_update import UpdateMixin

    installs: list[str] = []
    window = _stub_window(object())
    window._begin_ripper_install = lambda offer, commit: installs.append(commit)  # type: ignore[method-assign]

    # 1. Esc / reject — no button is clicked at all.
    UpdateMixin._offer_ripper_install(window, object(), "detail", "ddf7ac3")
    assert window._ripper_offer_box is not None, "the offer was never shown"
    assert window._ripper_offer_commit == "ddf7ac3"
    window._ripper_offer_box.reject()
    qapp.processEvents()
    assert window._ripper_offer_box is None, "dismissing left the offer slots set"
    assert window._ripper_offer_commit == ""
    assert not installs, "a dismissed offer installed something"

    # 2. The decline button — a real click, a real role.
    UpdateMixin._offer_ripper_install(window, object(), "detail", "ddf7ac3")
    box = window._ripper_offer_box
    assert box is not None
    decline = next(
        b
        for b in box.buttons()
        if box.buttonRole(b) == QMessageBox.ButtonRole.RejectRole
    )
    decline.click()
    qapp.processEvents()
    assert window._ripper_offer_box is None
    assert not installs, "declining installed the build anyway"
