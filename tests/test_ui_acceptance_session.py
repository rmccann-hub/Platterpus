"""Tools → Run acceptance test…: the overnight session, done by the program.

**What this covers.** The maintainer's ruling was that the overnight acceptance
run must stop being two bash scripts and a thing to remember in the morning —
*"make the app make the rig folder and anything else, this was supposed to be a
no cli program, not give me commands to use"*. `ProvisioningMixin` is the wiring
that does it, and these tests hold the four properties that wiring can get wrong
in ways nothing else would notice:

* the run starts against the **packaged** script, and refuses — visibly, with a
  reason, having started nothing — when that script is not there;
* a sleep lock that could not be taken **downgrades the run, it does not cancel
  it**, and its own sentence reaches the user (a silent downgrade is how you
  spend a night and learn nothing);
* the archive is built **off the GUI thread** (it gzips a log measured at 4.4 MB);
* the `systemd-inhibit` **child process** is released on every exit path — the
  run finishing, the window closing, and the bundle blowing up — because a leaked
  one holds the machine awake until reboot with nothing on screen to say why.

**Why the message boxes are patched at `exec`.** This feature builds its own
`QMessageBox` (it needs an "Open the folder" button and `PlainText`), so
conftest's `_non_blocking_message_boxes` — which only covers the *static*
helpers — does not reach it. Under the headless `offscreen` platform a real
`exec()` blocks forever, so the autouse fixture below records the box and
returns.
"""

from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import stop_window_threads
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from platterpus.adapters.metaflac import MetaflacAdapter
from platterpus.adapters.musicbrainz_client import MusicBrainzClient
from platterpus.adapters.rip_backend import DiscInfo, RipBackend, RipHandle
from platterpus.config import Config
from platterpus.deps.manager import DependencyManager
from platterpus.evidence_bundle import BundleResult
from platterpus.parsers.drive_list import DriveDescriptor
from platterpus.sleep_inhibit import (
    INHIBIT_WHAT,
    STATE_HELD,
    STATE_NOT_INSTALLED,
    STATE_UNAVAILABLE,
    InhibitOutcome,
)
from platterpus.ui.dialogs.script_console import ScriptConsoleDialog
from platterpus.ui.main_window import MainWindow
from platterpus.uiscript.report import RunReport

# --- Fakes ----------------------------------------------------------------


class _Backend(RipBackend):
    """Enough of the backend to build a window; nothing here is ever called."""

    def list_drives(self) -> list[DriveDescriptor]:
        return []

    def disc_info(self, drive: str) -> DiscInfo:
        return DiscInfo()

    def rip(
        self,
        drive: str,
        release_id: str,
        output_dir: Path,
        track_template: str,
        disc_template: str,
        unknown: bool = False,
        **kwargs: object,
    ) -> RipHandle:
        raise NotImplementedError

    def version(self) -> str:
        return "fake 0.0.0"


class _Mb(MusicBrainzClient):
    """No lookup ever happens here; the window just needs a client to hold."""

    def releases_by_disc_id(self, disc_id: str) -> list:  # type: ignore[type-arg]
        return []

    def releases_by_toc(self, toc: Any) -> list:  # type: ignore[type-arg]
        return []

    def release_by_mbid(
        self,
        mbid: str,
        *,
        disc_id: str = "",
        disc_track_count: int | None = None,
    ) -> Any:
        raise NotImplementedError

    def set_user_agent(self, app: str, version: str, contact: str) -> None:
        pass


class _FakeInhibitor:
    """A `SleepInhibitor` stand-in that never spawns anything.

    Deliberately narrower than the real class — it implements exactly the three
    members the window uses. `CLAUDE.md` asks what a stand-in does that the real
    thing does not; here the difference is that it starts no child, which is the
    whole reason a test may use it, and it cannot hide a defect in the window
    because the window's entire contract with it is `acquire()` once and
    `release()` at least once.
    """

    def __init__(self, outcome: InhibitOutcome, *, why: str = "") -> None:
        self.outcome = outcome
        self.why = why
        self.acquires = 0
        self.releases = 0

    def acquire(self) -> InhibitOutcome:
        self.acquires += 1
        return self.outcome

    def release(self) -> None:
        self.releases += 1


def _held() -> InhibitOutcome:
    return InhibitOutcome(
        state=STATE_HELD,
        detail="Idle, sleep and lid suspend are held off for this run.",
        what=INHIBIT_WHAT,
    )


def _refused() -> InhibitOutcome:
    return InhibitOutcome(
        state=STATE_UNAVAILABLE,
        detail=(
            "`systemd-inhibit` is installed but could not take the lock this run "
            "needs — the probe exited 1. It said: Failed to inhibit: Access denied. "
            "The run will proceed WITHOUT the lock."
        ),
        what=INHIBIT_WHAT,
    )


# --- Fixtures -------------------------------------------------------------


@pytest.fixture(autouse=True)
def shown_boxes(monkeypatch: pytest.MonkeyPatch) -> list[QMessageBox]:
    """Record every `QMessageBox.exec()` instead of blocking on it."""
    boxes: list[QMessageBox] = []

    def fake_exec(self: QMessageBox) -> int:
        boxes.append(self)
        return int(QMessageBox.StandardButton.Close)

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    return boxes


@pytest.fixture()
def window(qapp: QApplication):
    """A real MainWindow, torn down the one canonical way."""
    made: list[MainWindow] = []

    def factory() -> MainWindow:
        win = MainWindow(
            config=Config(),
            backend=_Backend(),
            mb_client=_Mb(),
            metaflac=MetaflacAdapter(),
            dependency_manager=DependencyManager(specs=[]),
            save_config=lambda _cfg: None,
        )
        made.append(win)
        return win

    yield factory

    for win in made:
        # `close()` runs the real closeEvent, which is what releases the sleep
        # lock and stops the console — the product's own teardown, not the
        # harness doing its job for it.
        win.close()
        stop_window_threads(win)
        win.deleteLater()


@pytest.fixture()
def session(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Point the whole session at `tmp_path` and hand back the knobs.

    Returns a `SimpleNamespace` with the packaged-script stand-in, the list the
    fake inhibitors are recorded in, and the list of `run_now()` calls. Every
    path the session touches — `$HOME`, the app log, the config file — is
    redirected, so a run never reads or writes the developer's own files.
    """
    home = tmp_path / "home"
    home.mkdir()
    log_path = tmp_path / "log.txt"
    log_path.write_text("app log line\n", encoding="utf-8")
    config_path = tmp_path / "config.toml"
    config_path.write_text("read_offset = 6\n", encoding="utf-8")

    script = tmp_path / "fullacceptance.txt"
    script.write_text("log a self-check\n", encoding="utf-8")

    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr("platterpus.paths.LOG_PATH", log_path)
    monkeypatch.setattr("platterpus.paths.CONFIG_PATH", config_path)

    state = SimpleNamespace(
        home=home,
        script=script,
        log_path=log_path,
        inhibitors=[],
        outcome=_held(),
        runs=[],
    )

    monkeypatch.setattr(
        "platterpus.test_session.builtin_acceptance_script",
        lambda: (script, f"using the acceptance script shipped in the app: {script}"),
    )

    def make_inhibitor(**kwargs: Any) -> _FakeInhibitor:
        inhibitor = _FakeInhibitor(state.outcome, why=str(kwargs.get("why", "")))
        state.inhibitors.append(inhibitor)
        return inhibitor

    monkeypatch.setattr("platterpus.sleep_inhibit.SleepInhibitor", make_inhibitor)

    # The batch itself is not the subject of this file — `test_uiscript.py` owns
    # that — and letting it drive the real window here would make every test in
    # this module depend on the acceptance script's contents.
    monkeypatch.setattr(
        ScriptConsoleDialog, "run_now", lambda self: state.runs.append(self)
    )
    return state


def _start(window_factory, session, process_until) -> MainWindow:
    """Arm a session and pump until the batch has been started."""
    win = window_factory()
    assert win.run_acceptance_session() is True
    assert process_until(lambda: session.runs), (
        "the batch never started — the sleep-lock signal did not land"
    )
    return win


def _finish(win: MainWindow, process_until, report: object | None = None) -> None:
    """Fire the console's `run_finished` and pump until the bundle has landed."""
    console = win._acceptance_console
    assert console is not None
    console.run_finished.emit(
        report if report is not None else RunReport(started_at="t", app_version="v")
    )
    thread = win._acceptance_bundle_thread
    assert thread is not None, "no bundle daemon was started"
    assert process_until(lambda: not thread.is_alive()), "the bundle daemon wedged"
    process_until(lambda: False, timeout=0.05)  # deliver the queued result


# --- The console's seam ---------------------------------------------------


def test_the_console_re_emits_the_runs_report(qapp: QApplication) -> None:
    """`run_finished` is the seam: the runner is built lazily inside `_on_run`,
    so a caller cannot connect to `runner().finished` before starting a run."""
    holder = QWidget()
    console = ScriptConsoleDialog(holder)
    seen: list[object] = []
    console.run_finished.connect(seen.append)

    report = RunReport(started_at="t", app_version="v")
    console._on_finished(report)

    assert seen == [report]
    console.close()
    holder.close()


def test_the_console_emits_after_the_transcript_is_rendered(
    qapp: QApplication,
) -> None:
    """Ordering matters: a listener's first act is to read `transcript_text()`,
    and emitting before the render would hand it the streaming lines instead."""
    holder = QWidget()
    console = ScriptConsoleDialog(holder)
    seen_text: list[str] = []
    console.run_finished.connect(lambda _r: seen_text.append(console.transcript_text()))

    console._on_finished(RunReport(started_at="2026-08-28", app_version="9.9.9"))

    assert seen_text and "9.9.9" in seen_text[0], (
        f"the transcript was not rendered before the emit: {seen_text!r}"
    )
    console.close()
    holder.close()


def test_the_console_emits_even_for_a_payload_it_cannot_narrow(
    qapp: QApplication,
) -> None:
    """A run that ends with an unreadable payload is still a run that ended —
    and whoever is holding a child process open for its duration must hear."""
    holder = QWidget()
    console = ScriptConsoleDialog(holder)
    seen: list[object] = []
    console.run_finished.connect(seen.append)

    console._on_finished("not a RunReport")

    assert seen == ["not a RunReport"]
    console.close()
    holder.close()


# --- Starting the session -------------------------------------------------


def test_the_action_runs_the_packaged_script_in_the_console(
    window, session, process_until
) -> None:
    win = _start(window, session, process_until)

    console = win._script_console
    assert console is not None, "the script console was never opened"
    assert console.script_text() == session.script.read_text(encoding="utf-8")
    assert session.runs == [console], "the batch was not started on that console"
    # And the session folder really exists — `prepare_session` ran.
    layout = win._acceptance_layout
    assert layout is not None
    assert layout.root.is_dir() and layout.artifacts.is_dir()


def test_the_tools_menu_item_is_wired_to_the_session(
    window, session, process_until
) -> None:
    """The wiring, not the method. A capability nobody can invoke is not a
    capability — the exact lesson the script console itself was built from
    (`docs/testing.md` §5.p), and `triggered` hands its slot a `checked` bool
    that `run_acceptance_session` does not take, so the connection is worth
    proving rather than assuming."""
    win = window()
    actions = [
        action
        for action in win.menuBar().findChildren(QAction)
        if "acceptance" in action.text().lower()
    ]
    assert actions, "Tools has no acceptance-test item"

    actions[0].trigger()

    assert process_until(lambda: bool(session.runs)), (
        "triggering the menu item did not start the acceptance batch"
    )
    assert win._script_console is not None


def test_a_missing_packaged_script_says_why_and_starts_nothing(
    window, session, process_until, shown_boxes, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The refusal names the path it looked for, and nothing is set in motion:
    no console, no sleep lock, no session folder."""
    missing = session.script.parent / "gone" / "fullacceptance.txt"
    monkeypatch.setattr(
        "platterpus.test_session.builtin_acceptance_script",
        lambda: (
            None,
            f"the acceptance script that ships inside Platterpus is not there: "
            f"{missing}. This build did not include it.",
        ),
    )
    win = window()

    assert win.run_acceptance_session() is False

    assert shown_boxes, "nothing was said on screen"
    assert str(missing) in shown_boxes[-1].text()
    assert win._script_console is None
    assert win._acceptance_layout is None
    assert session.inhibitors == [], "a sleep lock was taken for a run that never ran"
    assert session.runs == []


def test_a_script_that_will_not_load_stops_the_session_and_frees_the_lock(
    window, session, process_until, shown_boxes, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The 2026-08-13 rig defect, at this call site: a script that will not load
    must not fall through to whatever the editor happens to hold."""
    monkeypatch.setattr(ScriptConsoleDialog, "load_file", lambda self, path: False)
    win = window()

    assert win.run_acceptance_session() is True
    assert process_until(lambda: bool(shown_boxes)), "no refusal was shown"

    assert session.runs == [], "the batch ran anyway"
    assert win._acceptance_layout is None
    assert session.inhibitors[-1].releases == 1, "the sleep lock was left held"


# --- The sleep lock -------------------------------------------------------


def test_the_run_proceeds_and_says_so_when_the_lock_is_refused(
    window, session, process_until
) -> None:
    """`unavailable` is a downgrade, not a cancellation — and the tool's own
    sentence has to reach the user, or the downgrade is silent."""
    session.outcome = _refused()

    win = _start(window, session, process_until)

    assert session.runs, "an unavailable sleep lock aborted the run"
    note = win._acceptance_inhibit_note
    assert STATE_UNAVAILABLE in note
    assert "Access denied" in note, f"the tool's own words were dropped: {note!r}"
    assert note.startswith("⚠"), "a status level carried by colour alone"
    # On screen, not only in the log: the rip pane's live view is where the
    # operator is already looking, and it is not a dialog that could race the
    # script.
    assert "Access denied" in win._rip_progress._log_view.toPlainText()


def test_a_missing_systemd_inhibit_also_proceeds(
    window, session, process_until
) -> None:
    session.outcome = InhibitOutcome(
        state=STATE_NOT_INSTALLED,
        detail="`systemd-inhibit` is not installed, so sleep could NOT be held off.",
        what=INHIBIT_WHAT,
    )

    win = _start(window, session, process_until)

    assert session.runs, "a missing systemd-inhibit aborted the run"
    assert STATE_NOT_INSTALLED in win._acceptance_inhibit_note
    assert "not installed" in win._rip_progress._log_view.toPlainText()


def test_a_held_lock_is_reported_as_held(window, session, process_until) -> None:
    win = _start(window, session, process_until)

    assert win._acceptance_inhibit_note.startswith("✓")
    assert STATE_HELD in win._acceptance_inhibit_note
    assert session.inhibitors[-1].acquires == 1


def test_an_unreadable_outcome_is_reported_as_not_determined(
    window, session, process_until
) -> None:
    """Tri-state: a payload we cannot narrow is never reported as held."""
    win = window()
    win._acceptance_layout = object()  # type: ignore[assignment]  # armed enough
    win._on_acceptance_inhibitor_ready("not an InhibitOutcome")

    assert "not determined" in win._acceptance_inhibit_note
    assert STATE_HELD not in win._acceptance_inhibit_note


# --- The bundle -----------------------------------------------------------


def test_the_bundle_does_not_run_on_the_gui_thread(
    window, session, process_until, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rule this project has been bitten by three times, at the one place
    this change could reintroduce it: the archive gzips a 4.4 MB log."""
    gui_thread = threading.get_ident()
    ran_on: list[int] = []

    def fake_finish(layout: object, **kwargs: object) -> BundleResult:
        ran_on.append(threading.get_ident())
        return BundleResult(path=Path("/dev/null"))

    monkeypatch.setattr("platterpus.test_session.finish_session", fake_finish)
    win = _start(window, session, process_until)

    _finish(win, process_until)

    assert ran_on, "the bundle was never built"
    assert ran_on[0] != gui_thread, (
        "the session bundle ran on the GUI thread — a stalled filesystem or a "
        "large log would freeze the window"
    )


def test_the_event_loop_keeps_turning_while_the_bundle_is_packed(
    window, session, process_until, qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Heartbeat guard beside the thread-identity one: if the pack ran on the
    GUI thread, a main-thread timer would stop firing for its duration."""
    from PySide6.QtCore import QTimer

    release = threading.Event()
    ticks = {"n": 0}
    heartbeat = QTimer()
    heartbeat.setInterval(5)
    heartbeat.timeout.connect(lambda: ticks.__setitem__("n", ticks["n"] + 1))
    heartbeat.start()

    def slow_finish(layout: object, **kwargs: object) -> BundleResult:
        release.wait(0.3)
        return BundleResult(path=Path("/dev/null"))

    monkeypatch.setattr("platterpus.test_session.finish_session", slow_finish)
    win = _start(window, session, process_until)
    _finish(win, process_until)
    heartbeat.stop()

    assert ticks["n"] >= 5, (
        f"the event loop was starved ({ticks['n']} ticks) — the pack blocked the "
        "GUI thread"
    )


def test_the_success_path_names_a_file_that_exists(
    window, session, process_until, shown_boxes
) -> None:
    """The floor. A 'send this one file' message that names a path which is not
    there is worse than no message: it is acted on."""
    win = _start(window, session, process_until)

    _finish(win, process_until)

    assert shown_boxes, "the operator was never told where the file is"
    text = shown_boxes[-1].text()
    named = [
        Path(word)
        for word in text.split()
        if word.endswith(".tar.gz") and word.startswith("/")
    ]
    assert named, f"no archive path was named in:\n{text}"
    assert named[0].is_file(), f"the named file does not exist: {named[0]}"
    # And the operator gets a way to reach it without retyping the path.
    assert any("Open" in button.text() for button in shown_boxes[-1].buttons())


def test_a_bundle_error_is_surfaced_not_reported_as_success(
    window, session, process_until, shown_boxes, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`BundleResult.error` is a real answer and has to reach the user — with
    the session folder named, because that workspace is still complete."""
    monkeypatch.setattr(
        "platterpus.test_session.finish_session",
        lambda layout, **kwargs: BundleResult(error="OSError: No space left on device"),
    )
    win = _start(window, session, process_until)
    root = win._acceptance_root
    assert root is not None

    _finish(win, process_until)

    assert shown_boxes, "a failed bundle said nothing at all"
    text = shown_boxes[-1].text()
    assert "No space left on device" in text
    assert str(root) in text
    assert ".tar.gz" not in text, "a failed bundle was reported as a written file"


def test_a_bundle_that_raises_is_reported_rather_than_lost(
    window, session, process_until, shown_boxes, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(layout: object, **kwargs: object) -> BundleResult:
        raise RuntimeError("the packer exploded")

    monkeypatch.setattr("platterpus.test_session.finish_session", boom)
    win = _start(window, session, process_until)

    _finish(win, process_until)

    assert shown_boxes
    assert "the packer exploded" in shown_boxes[-1].text()


def test_the_bundle_collects_the_app_log_and_the_transcript(
    window, session, process_until, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The morning script's job, done by the program: the one archive carries
    the app log and the run's transcript, and the sleep verdict is a fact in it."""
    captured: dict[str, object] = {}

    def spy(layout: object, **kwargs: object) -> BundleResult:
        captured["sources"] = kwargs["sources"]
        captured["facts"] = kwargs["facts"]
        return BundleResult(path=Path("/dev/null"))

    monkeypatch.setattr("platterpus.test_session.finish_session", spy)
    win = _start(window, session, process_until)
    layout = win._acceptance_layout
    assert layout is not None
    transcript_path = layout.transcript

    _finish(win, process_until)

    sources = [Path(p) for p in captured["sources"]]  # type: ignore[union-attr]
    assert session.log_path in sources, f"the app log was not collected: {sources}"
    assert transcript_path in sources
    assert transcript_path.is_file(), "the transcript was never written"
    facts = captured["facts"]
    assert isinstance(facts, dict)
    assert STATE_HELD in facts["sleep lock"]


# --- Releasing the lock ---------------------------------------------------


def test_the_lock_is_released_when_the_run_finishes(
    window, session, process_until, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "platterpus.test_session.finish_session",
        lambda layout, **kwargs: BundleResult(path=Path("/dev/null")),
    )
    win = _start(window, session, process_until)
    inhibitor = session.inhibitors[-1]
    assert inhibitor.releases == 0

    _finish(win, process_until)

    assert inhibitor.releases == 1, "the systemd-inhibit child was left holding"


def test_the_lock_is_released_before_the_bundle_is_built(
    window, session, process_until, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ordering, not just eventual release. A bundle that wedges must not be
    able to hold the machine awake, so the release cannot be downstream of it."""
    order: list[str] = []

    def note_finish(layout: object, **kwargs: object) -> BundleResult:
        order.append("bundle")
        return BundleResult(path=Path("/dev/null"))

    monkeypatch.setattr("platterpus.test_session.finish_session", note_finish)
    win = _start(window, session, process_until)
    inhibitor = session.inhibitors[-1]
    original_release = inhibitor.release

    def note_release() -> None:
        order.append("release")
        original_release()

    inhibitor.release = note_release  # type: ignore[method-assign]

    _finish(win, process_until)

    assert order[:2] == ["release", "bundle"], f"wrong order: {order}"


def test_the_lock_is_released_even_when_the_bundle_raises(
    window, session, process_until, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-vacuous against the ordering above: if the release were placed after
    the pack without a guard, an exploding packer would leak the child."""

    def boom(layout: object, **kwargs: object) -> BundleResult:
        raise RuntimeError("the packer exploded")

    monkeypatch.setattr("platterpus.test_session.finish_session", boom)
    win = _start(window, session, process_until)
    inhibitor = session.inhibitors[-1]

    _finish(win, process_until)

    assert inhibitor.releases == 1, (
        "a bundle that raised left the systemd-inhibit child running — it would "
        "keep the machine awake until reboot"
    )


def test_the_lock_is_released_when_the_window_closes(
    window, session, process_until
) -> None:
    win = _start(window, session, process_until)
    inhibitor = session.inhibitors[-1]
    assert inhibitor.releases == 0

    win.close()

    assert inhibitor.releases == 1, "closing the window leaked the sleep lock"
    assert win._acceptance_layout is None


def test_closing_the_window_does_not_start_a_bundle_daemon(
    window, session, process_until
) -> None:
    """Closing the window closes the console, which ends the run — and that must
    not start a pack in the middle of a teardown."""
    win = _start(window, session, process_until)

    win.close()

    assert win._acceptance_bundle_thread is None, (
        "a bundle daemon was started during window teardown"
    )


def test_a_second_session_is_refused_while_one_is_running(
    window, session, process_until, shown_boxes
) -> None:
    win = _start(window, session, process_until)

    assert win.run_acceptance_session() is False
    assert shown_boxes and "already" in shown_boxes[-1].text().lower()
    assert len(session.inhibitors) == 1, "a second sleep lock was taken"


def test_a_run_that_finishes_after_the_session_ended_builds_nothing(
    window, session, process_until
) -> None:
    """The guard that makes the teardown order safe, asserted directly."""
    win = _start(window, session, process_until)
    console = win._acceptance_console
    assert console is not None
    win._end_acceptance_session("test")

    console.run_finished.emit(RunReport(started_at="t", app_version="v"))

    assert win._acceptance_bundle_thread is None
