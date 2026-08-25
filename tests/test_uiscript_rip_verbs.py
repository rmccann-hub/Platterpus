"""The rip-driving verbs, executed against a stand-in window.

`test_uiscript.py` covers the parser, the vocabulary and the report. Nothing
covered the **runner's handlers**, which is why eleven verbs could be added and
the suite stay green — and a verb that fails at run time fails in front of an
unattended batch, at the worst possible moment.

**What this stand-in does that a real MainWindow does not, stated rather than
left implicit** (`CLAUDE.md`: *what does my stand-in do that the real thing does
not?*). It is a plain `QWidget` carrying the same attribute *names* the handlers
reach for — `_track_table`, `_rip_controls`, `_drive_picker`, `_config`,
`_rip_worker`, `_on_drive_changed`, `_on_rip_cancel`, `_save_config`. It does not
rip, does not touch a drive, and does not persist anything.

That is a real difference, so the names themselves are pinned separately: the
sibling test below asserts every attribute this stub fakes actually exists on the
real `MainWindow` / `RipControls` / `TrackTable` / `DrivePicker`. Without that,
the stub would happily satisfy handlers that reach for methods the product does
not have — which is exactly the failure mode a stub invites, and the one that
five wrong `OPENABLE` names were caught by.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from platterpus.config import Config
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner, _CyanripJob
from platterpus.uiscript.script import parse

pytest.importorskip("PySide6.QtWidgets")


class _Track:
    """A track row, as much of one as `tracks()` consumers need."""

    def __init__(self, number: int) -> None:
        self.number: int = number


class _TrackTable:
    def __init__(self, count: int = 14) -> None:
        self._tracks = [_Track(n) for n in range(1, count + 1)]
        self.selected: list[int] | None = None
        self.all_selected: bool | None = None
        from PySide6.QtWidgets import QLineEdit

        self._album_title_edit = QLineEdit()
        self._album_artist_edit = QLineEdit()

    def tracks(self) -> list[_Track]:
        return list(self._tracks)

    def set_all_selected(self, selected: bool) -> None:
        self.all_selected = selected

    def set_only_selected(self, numbers: list[int]) -> None:
        self.selected = list(numbers)


class _RipControls:
    def __init__(self, *, startable: bool = True) -> None:
        self._startable = startable
        self.started = False
        self.config_pushed: Config | None = None

    def can_start(self) -> bool:
        return self._startable

    def _on_start(self) -> None:
        self.started = True

    def set_config(self, config: Config) -> None:
        self.config_pushed = config


class _RipProgress:
    """The rip-progress pane, as much of it as `expect-status` needs.

    Mirrors `RipProgress.current_status()` exactly — the floor test in this file
    checks every faked attribute exists on the real class, which is what stops a
    stub being kinder than the product.
    """

    def __init__(self, status: str = "") -> None:
        self._status = status

    def current_status(self) -> str:
        return self._status


class _DrivePicker:
    def __init__(self, device: str = "/dev/sr0") -> None:
        self._device = device

    def current_device(self) -> str:
        return self._device


def _window(**overrides: Any):
    """A QWidget carrying the attribute names the handlers reach for."""
    from PySide6.QtWidgets import QWidget

    win = QWidget()
    win._track_table = overrides.get("track_table", _TrackTable())
    win._rip_controls = overrides.get("rip_controls", _RipControls())
    win._drive_picker = overrides.get("drive_picker", _DrivePicker())
    win._config = overrides.get("config", Config())
    win._rip_worker = overrides.get("rip_worker", None)
    win._rip_progress = overrides.get("rip_progress", _RipProgress())
    win.rescanned = []
    win.cancelled = False
    win.saved = []
    win._on_drive_changed = win.rescanned.append
    win._on_rip_cancel = lambda: setattr(win, "cancelled", True)
    win._save_config = win.saved.append
    return win


def _run_one(window: Any, line: str) -> Any:
    """Execute a single script line synchronously and return its StepRecord."""
    runner = ScriptRunner(window)
    steps = parse(line)
    assert len(steps) == 1, f"{line!r} did not parse to one step"
    runner._report.steps.clear()
    runner._execute(steps[0])
    # A deadline-arming verb records nothing until its deadline resolves; the
    # caller inspects `runner` in that case.
    return runner._report.steps[-1] if runner._report.steps else None, runner


# --- The stand-in must not be kinder than the product -----------------------


def test_every_attribute_the_stub_fakes_exists_on_the_real_classes() -> None:
    """**The floor for this whole file.**

    A stub answers whatever the handler asks. If a handler reached for a method
    the real window does not have, every test here would still pass and the verb
    would die at run time — which is precisely how five wrong dialog names got
    into `OPENABLE` on the first attempt.

    So the names are checked against the real classes, not against the stub.

    **`hasattr` alone is not enough, and finding that out was the point.** The
    first version of this test failed on `MainWindow._save_config` — not because
    the attribute is missing, but because it is an *injected instance attribute*
    (``self._save_config: Callable[[Config], None] = save_config`` in
    ``__init__``), so it exists on every real window and on no class object. A
    check that only looked at the class would have declared a working verb broken;
    one that only looked at `__init__` would miss the ordinary methods. Both are
    searched, and the failure message says which kind was expected.
    """
    import inspect

    from platterpus.ui.drive_picker import DrivePicker
    from platterpus.ui.main_window import MainWindow
    from platterpus.ui.rip_controls import RipControls
    from platterpus.ui.track_table import TrackTable

    def _provides(owner: type, name: str) -> bool:
        if hasattr(owner, name):
            return True
        # An attribute assigned in __init__ (an injected dependency) is real but
        # invisible on the class. Look for the assignment, on any class in the MRO
        # — a mixin's __init__ counts, and this window is built from mixins.
        for klass in owner.__mro__:
            init = klass.__dict__.get("__init__")
            if init is None:
                continue
            try:
                source = inspect.getsource(init)
            except (OSError, TypeError):  # C-implemented or unavailable
                continue
            if f"self.{name}" in source:
                return True
        return False

    for owner, names in (
        (MainWindow, ("_on_drive_changed", "_on_rip_cancel", "_save_config")),
        (RipControls, ("can_start", "_on_start", "set_config")),
        (TrackTable, ("tracks", "set_all_selected", "set_only_selected")),
        (DrivePicker, ("current_device",)),
    ):
        for name in names:
            assert _provides(owner, name), (
                f"{owner.__name__} provides no {name!r} — neither as a method nor as "
                f"an attribute assigned in __init__ — but a script verb calls it. "
                f"The verb would fail at RUN time in front of an unattended batch."
            )


def test_the_attribute_check_can_actually_fail() -> None:
    """Non-triviality floor: `_provides` must not accept everything.

    Without this, a helper that returned True unconditionally would make the test
    above pass for every name including invented ones — a check satisfiable by the
    wrong thing.
    """
    import inspect

    from platterpus.ui.rip_controls import RipControls

    def _provides(owner: type, name: str) -> bool:
        if hasattr(owner, name):
            return True
        for klass in owner.__mro__:
            init = klass.__dict__.get("__init__")
            if init is None:
                continue
            try:
                source = inspect.getsource(init)
            except (OSError, TypeError):
                continue
            if f"self.{name}" in source:
                return True
        return False

    assert _provides(RipControls, "can_start")
    assert not _provides(RipControls, "definitely_not_a_real_method_name")


def test_the_track_row_really_carries_a_number_attribute() -> None:
    """`select-tracks` reads `t.number` off whatever `tracks()` returns."""
    from platterpus.ui.track_table import TrackSummary

    assert "number" in {f.name for f in dataclasses.fields(TrackSummary)}


# --- rescan -----------------------------------------------------------------


def test_rescan_reaches_the_windows_own_drive_pipeline(qapp, process_until) -> None:
    win = _window()
    record, _ = _run_one(win, "rescan")
    assert record.outcome is Outcome.PASS
    # Deferred via singleShot(0); pump the loop so the deferred call lands.
    assert process_until(lambda: win.rescanned == ["/dev/sr0"]), (
        "the deferred call never landed"
    )


def test_rescan_with_no_drive_fails_rather_than_silently_doing_nothing(
    qapp, process_until
) -> None:
    win = _window(drive_picker=_DrivePicker(device=""))
    record, _ = _run_one(win, "rescan")
    assert record.outcome is Outcome.FAIL
    assert "no drive" in record.detail.lower()


# --- album / album-artist ---------------------------------------------------


def test_album_takes_the_whole_rest_of_the_line(qapp, process_until) -> None:
    """Titles have spaces, brackets and colons; none of that needs quoting."""
    win = _window()
    record, _ = _run_one(win, "album Synchronicity (rig ddf7ac3 pass 1)")
    assert record.outcome is Outcome.PASS
    assert win._track_table._album_title_edit.text() == (
        "Synchronicity (rig ddf7ac3 pass 1)"
    )


def test_album_artist_sets_its_own_field(qapp, process_until) -> None:
    win = _window()
    record, _ = _run_one(win, "album-artist The Police")
    assert record.outcome is Outcome.PASS
    assert win._track_table._album_artist_edit.text() == "The Police"


# --- select-tracks ----------------------------------------------------------


def test_select_tracks_all_and_none(qapp, process_until) -> None:
    win = _window()
    record, _ = _run_one(win, "select-tracks all")
    assert record.outcome is Outcome.PASS
    assert win._track_table.all_selected is True

    record, _ = _run_one(win, "select-tracks none")
    assert record.outcome is Outcome.PASS
    assert win._track_table.all_selected is False


def test_select_tracks_expands_a_range(qapp, process_until) -> None:
    win = _window()
    record, _ = _run_one(win, "select-tracks 3,7,11-13")
    assert record.outcome is Outcome.PASS
    assert win._track_table.selected == [3, 7, 11, 12, 13]


def test_select_tracks_refuses_a_track_the_disc_does_not_have(
    qapp, process_until
) -> None:
    """Silently dropping it would rip a different disc than the script says.

    The disc here has 14 tracks; asking for 15 must FAIL rather than quietly
    selecting the 14 that exist.
    """
    win = _window()
    record, _ = _run_one(win, "select-tracks 13-15")
    assert record.outcome is Outcome.FAIL
    assert "15" in record.detail
    assert win._track_table.selected is None, "nothing may be selected on refusal"


def test_select_tracks_with_no_tracks_loaded_fails(qapp, process_until) -> None:
    win = _window(track_table=_TrackTable(count=0))
    record, _ = _run_one(win, "select-tracks all")
    assert record.outcome is Outcome.FAIL


# --- rip / cancel-rip -------------------------------------------------------


def test_rip_presses_the_real_start_slot(qapp, process_until) -> None:
    win = _window()
    record, _ = _run_one(win, "rip")
    assert record.outcome is Outcome.PASS
    assert process_until(lambda: win._rip_controls.started), (
        "the deferred call never landed"
    )


def test_rip_refuses_when_the_start_button_would_be_disabled(
    qapp, process_until
) -> None:
    """An unstarted rip reporting PASS is the worst outcome available here."""
    win = _window(rip_controls=_RipControls(startable=False))
    record, _ = _run_one(win, "rip")
    assert record.outcome is Outcome.FAIL
    assert not win._rip_controls.started


def test_rip_refuses_while_one_is_already_running(qapp, process_until) -> None:
    win = _window(rip_worker=object())
    record, _ = _run_one(win, "rip")
    assert record.outcome is Outcome.FAIL
    assert "already running" in record.detail


def test_rip_refuses_while_a_dialog_is_waiting_for_an_answer(
    qapp, process_until
) -> None:
    """The 0.6.18 re-entrancy guard, at the state the other two guards cannot see.

    Both pre-existing guards — `_rip_worker is not None` and `can_start()` — say
    "go ahead" while the window is holding its overwrite confirmation up: the
    worker is created *after* that dialog is answered, and the controls behind it
    are still enabled. Qt runs this runner's timer inside the modal's nested event
    loop, so the batch does not pause there; a script with two `rip` steps reaches
    the second one and, when the operator finally clicks through, launches **two
    cyanrip processes against one drive**.

    Asserted on the OUTCOME OF THE PRESS, not only on the record: the thing that
    must not happen is Start being pressed, and a test that checked the FAIL alone
    would pass against a guard that recorded FAIL and pressed Start anyway.
    """
    from PySide6.QtWidgets import QDialog

    win = _window()
    dialog = QDialog(win)
    dialog.setWindowTitle("Album folder already has audio")
    dialog.setModal(True)
    dialog.show()
    try:
        assert process_until(lambda: dialog.isVisible()), "the stand-in never showed"
        record, _ = _run_one(win, "rip")
        assert record.outcome is Outcome.FAIL, record.detail
        assert "Album folder already has audio" in record.detail, (
            "the refusal did not name the dialog that caused it — the whole "
            "point is that the transcript carries the diagnosis"
        )
        # Give the deferred `singleShot(0, start)` every chance to land, then
        # prove it never armed.
        process_until(lambda: win._rip_controls.started, timeout=0.5)
        assert not win._rip_controls.started, (
            "Start was pressed behind an open modal — this is the two-rippers-"
            "on-one-drive defect"
        )
    finally:
        dialog.close()
        dialog.deleteLater()


def test_wait_for_rip_names_the_modal_that_is_blocking_the_rip(
    qapp, process_until
) -> None:
    """ "No rip is running" is true and useless when a modal is why.

    The rip WAS requested; the worker does not exist yet because the app is
    blocked on a confirmation. On the rig that rendered as an unexplained
    failure while the explanation was on screen.
    """
    from PySide6.QtWidgets import QDialog

    win = _window()
    dialog = QDialog(win)
    dialog.setWindowTitle("Album folder already has audio")
    dialog.setModal(True)
    dialog.show()
    try:
        assert process_until(lambda: dialog.isVisible())
        record, _ = _run_one(win, "wait-for-rip 30")
        assert record.outcome is Outcome.FAIL, record.detail
        assert "Album folder already has audio" in record.detail, record.detail
    finally:
        dialog.close()
        dialog.deleteLater()


def test_cancel_rip_needs_a_rip_to_cancel(qapp, process_until) -> None:
    win = _window()
    record, _ = _run_one(win, "cancel-rip")
    assert record.outcome is Outcome.FAIL
    assert not win.cancelled


def test_cancel_rip_reaches_the_windows_cancel_handler(qapp, process_until) -> None:
    win = _window(rip_worker=object())
    record, _ = _run_one(win, "cancel-rip")
    assert record.outcome is Outcome.PASS
    assert process_until(lambda: win.cancelled), "the deferred call never landed"


# --- wait-for-rip -----------------------------------------------------------


def test_wait_for_rip_arms_a_deadline_rather_than_blocking(qapp, process_until) -> None:
    """A `sleep` here would freeze the window for the whole rip.

    Asserted structurally: after the step, the runner holds a pending deadline
    and a predicate, and control has already returned to us.
    """
    win = _window(rip_worker=object())
    runner = ScriptRunner(win)
    steps = parse("wait-for-rip 60")
    runner._execute(steps[0])
    assert runner._deadline is not None
    assert runner._deadline_predicate is not None
    assert runner._deadline_predicate() is False, "a live rip is not finished"

    # And the predicate flips the moment the window clears its worker — the same
    # fact the UI uses to re-enable its controls, not a second notion of doneness.
    win._rip_worker = None
    assert runner._deadline_predicate() is True


def test_wait_for_rip_refuses_a_nonsense_timeout(qapp, process_until) -> None:
    win = _window()
    for line in ("wait-for-rip 0", "wait-for-rip -5", "wait-for-rip soon"):
        record, _ = _run_one(win, line)
        assert record.outcome is Outcome.ERROR, line


def test_wait_for_rip_caps_an_absurd_timeout_loudly(qapp, process_until) -> None:
    """Never a silent clamp — and, since 2026-08-24, never a silent SKIP either.

    **This test used to assert the wait was REFUSED, and that behaviour destroyed
    a night of drive time.** `wait-for-rip 21600` against the 10800 s cap recorded
    FAIL and returned immediately, so the wait was zero. The next step graded a
    rip 0.4 s old, a cache probe opened the same drive 1.2 s later, and the
    unattended-quit helper killed the reader at 1.48% of track 1.

    The transcript must still say the request was clamped — that half was always
    right, and the word "cap" is still asserted. What changed is that the clamp is
    now honoured rather than used as a reason not to wait. With no rip running
    there is nothing to wait *for*, so the outcome here is still FAIL; the
    behaviour under test is that the detail names the clamp.
    """
    from platterpus.uiscript.runner import MAX_RIP_WAIT_S

    win = _window()
    record, _ = _run_one(win, f"wait-for-rip {int(MAX_RIP_WAIT_S) + 1000}")
    assert record.outcome is Outcome.FAIL
    assert "cap" in record.detail
    assert "CLAMPED" in record.detail or "no rip is running" in record.detail, (
        record.detail
    )


# --- expect-tracks ----------------------------------------------------------


def test_expect_tracks_is_a_real_floor(qapp, process_until) -> None:
    win = _window()
    assert _run_one(win, "expect-tracks 14")[0].outcome is Outcome.PASS
    assert _run_one(win, "expect-tracks 13")[0].outcome is Outcome.FAIL
    assert _run_one(win, "expect-tracks nine")[0].outcome is Outcome.ERROR


def test_expect_tracks_fails_when_nothing_is_loaded(qapp, process_until) -> None:
    """The case the floor exists for: a rip that identified nothing."""
    win = _window(track_table=_TrackTable(count=0))
    assert _run_one(win, "expect-tracks 14")[0].outcome is Outcome.FAIL


def test_expect_tracks_at_least_form(qapp, process_until) -> None:
    """`3+` means at least three, which is what a disc-agnostic script wants.

    Added 0.6.18. `rigcancelandoverread.txt` promises at the top that it needs no
    editing and works on any ordinary CD, and then asserted `expect-tracks 3` —
    "this disc has exactly three tracks" — while meaning "at least the three I am
    about to select". It failed twice per run on the 14-track rig disc, in a
    transcript whose purpose was proving the rip worked, and there was no exact
    number that could satisfy both the assertion and the promise.
    """
    win = _window()  # 14 rows
    assert _run_one(win, "expect-tracks 3+")[0].outcome is Outcome.PASS
    assert _run_one(win, "expect-tracks 14+")[0].outcome is Outcome.PASS
    assert _run_one(win, "expect-tracks 15+")[0].outcome is Outcome.FAIL


def test_the_at_least_form_still_catches_a_disc_that_identified_nothing(
    qapp, process_until
) -> None:
    """The counter-test, and the one that matters most.

    A looser assertion is only worth having if it still fails on the case the
    strict one existed for. `1+` against an empty table is the vacuous-pass shape
    the verb's own docstring calls the floor — if the `+` form had been written as
    "pass unless we can prove otherwise" it would report PASS here, and every
    script using it would have a check that cannot fail.
    """
    win = _window(track_table=_TrackTable(count=0))
    assert _run_one(win, "expect-tracks 1+")[0].outcome is Outcome.FAIL
    assert _run_one(win, "expect-tracks 3+")[0].outcome is Outcome.FAIL


def test_a_malformed_at_least_count_is_an_error_not_a_pass(qapp, process_until) -> None:
    """`+` alone, or a word with a `+`, must not read as zero-or-more."""
    win = _window()
    assert _run_one(win, "expect-tracks +")[0].outcome is Outcome.ERROR
    assert _run_one(win, "expect-tracks nine+")[0].outcome is Outcome.ERROR


# --- set / expect / expect-contains -----------------------------------------


def test_set_changes_the_config_and_pushes_it_to_the_rip_controls(
    qapp, process_until
) -> None:
    win = _window()
    record, _ = _run_one(win, "set force_overread off")
    assert record.outcome is Outcome.PASS
    assert win._config.force_overread is False
    assert win._rip_controls.config_pushed is win._config
    assert win.saved and win.saved[-1] is win._config


def test_set_refuses_a_value_the_settings_dialog_would_refuse(
    qapp, process_until
) -> None:
    win = _window()
    before = win._config
    record, _ = _run_one(win, "set output_format mp4")
    assert record.outcome is Outcome.FAIL
    assert win._config is before, "a rejected set must not have been applied"
    assert not win.saved, "a rejected set must not reach the disk"


def test_set_refuses_an_unknown_field(qapp, process_until) -> None:
    win = _window()
    record, _ = _run_one(win, "set not_a_setting 3")
    assert record.outcome is Outcome.ERROR
    assert "not_a_setting" in record.detail


def test_set_refuses_a_malformed_value_for_a_known_field(qapp, process_until) -> None:
    win = _window()
    record, _ = _run_one(win, "set max_retries lots")
    assert record.outcome is Outcome.ERROR


def test_expect_and_expect_contains(qapp, process_until) -> None:
    win = _window(config=dataclasses.replace(Config(), output_format="flac"))
    assert _run_one(win, "expect output_format flac")[0].outcome is Outcome.PASS
    assert _run_one(win, "expect output_format wavpack")[0].outcome is Outcome.FAIL
    assert _run_one(win, "expect-contains output_format fla")[0].outcome is Outcome.PASS
    assert _run_one(win, "expect-contains output_format zzz")[0].outcome is Outcome.FAIL
    assert _run_one(win, "expect nope 1")[0].outcome is Outcome.ERROR


def test_a_saved_config_failure_is_reported_not_swallowed(qapp, process_until) -> None:
    """The set still applies for the session, and the transcript says it did not
    reach disk. Going quiet would leave a run whose settings nobody can reproduce."""
    win = _window()

    def boom(_config: Config) -> None:
        raise OSError("read-only file system")

    win._save_config = boom
    record, _ = _run_one(win, "set force_overread on")
    assert record.outcome is Outcome.PASS
    assert "not saved to disk" in record.detail
    assert win._config.force_overread is True


# --- The run must leave a folder, not a window full of text -----------------


def _finished_report(runner: Any, qapp: Any, process_until: Any) -> Any:
    """Drive `runner` to its natural end and return the emitted RunReport.

    Uses the real `start()` → `_tick()` path rather than poking `_persist`
    directly, because the defect this guards against is not "the writer is
    broken" — it is "the writer exists and nothing calls it", which is the shape
    `CLAUDE.md` records as having shipped three times (a `cancel()` calling an
    ABC no-op, a `RipHandle.cancel` called from nowhere, a flag nobody checks).
    """
    emitted: list[Any] = []
    runner.finished.connect(emitted.append)
    runner.start(parse("log hello\nlog goodbye"), source="log hello\nlog goodbye")
    assert process_until(lambda: bool(emitted)), "the run never finished"
    return emitted[0]


def test_a_finished_run_writes_its_transcript_and_json_to_disk(
    qapp, process_until, tmp_path, monkeypatch
) -> None:
    """The operator's deliverable is a folder, not a text selection.

    Before this, the only route off the rig was the console's *Save transcript…*
    button — a human, after an unattended run. On the 2026-08-12 pass the
    transcript came back pasted into a chat message instead.
    """
    monkeypatch.setattr(
        "platterpus.paths.LOG_PATH", tmp_path / "share" / "log.txt", raising=False
    )
    runner = ScriptRunner(_window())
    report = _finished_report(runner, qapp, process_until)

    assert report.artifact_dir, "the run finished without naming an output folder"
    directory = Path(report.artifact_dir)
    transcript = (directory / "transcript.txt").read_text(encoding="utf-8")
    payload = json.loads((directory / "report.json").read_text(encoding="utf-8"))

    # Non-triviality: an empty file compares equal to an empty file, so assert
    # the run's actual content reached both forms rather than that they exist.
    assert "log hello" in transcript and "log goodbye" in transcript
    assert [step["source"] for step in payload["steps"]] == ["log hello", "log goodbye"]
    # And the transcript must name the folder it is sitting in — that string is
    # the entire answer to "what do I upload".
    assert str(directory) in transcript


def test_the_writer_is_reachable_from_both_ends_of_a_run(
    qapp, process_until, tmp_path, monkeypatch
) -> None:
    """A run stopped early is the case that most needs its evidence kept, and it
    leaves by a different exit than a run that completes. Both call the writer.

    This is the revert-proof: deleting either `_persist()` call site leaves the
    other passing, so each is asserted through the path that reaches it.
    """
    monkeypatch.setattr(
        "platterpus.paths.LOG_PATH", tmp_path / "share" / "log.txt", raising=False
    )
    runner = ScriptRunner(_window())
    emitted: list[Any] = []
    runner.finished.connect(emitted.append)
    runner.start(parse("wait 30\nlog never reached"))
    runner.stop("stopped by the operator")
    assert emitted, "stopping did not finish the run"
    report = emitted[0]

    assert report.artifact_dir, "a stopped run left nothing on disk"
    transcript = (Path(report.artifact_dir) / "transcript.txt").read_text(
        encoding="utf-8"
    )
    assert "stopped by the operator" in transcript
    assert "skip" in transcript, "the unreached step is not recorded as skipped"


def test_a_write_failure_is_logged_and_does_not_lose_the_run(
    qapp, process_until, tmp_path, monkeypatch, caplog
) -> None:
    """A full disk at the end of an hour-long disc pass must not also take the
    transcript still sitting in the window. `_persist` reports and returns."""
    monkeypatch.setattr(
        "platterpus.paths.LOG_PATH", tmp_path / "share" / "log.txt", raising=False
    )

    def boom(self: Any, *args: Any, **kwargs: Any) -> None:
        raise OSError("no space left on device")

    monkeypatch.setattr(Path, "write_text", boom)
    runner = ScriptRunner(_window())
    with caplog.at_level("ERROR"):
        report = _finished_report(runner, qapp, process_until)

    # The run itself is intact and still emitted; only the copy on disk is lost.
    assert [step.source for step in report.steps] == ["log hello", "log goodbye"]
    assert "no space left on device" in caplog.text


# --- pick-release: answering the MusicBrainz picker without a person --------


class _Release:
    """As much of a `ReleaseSummary` as the verb touches."""

    def __init__(self, mbid: str, title: str = "Every Breath You Take") -> None:
        self.mbid = mbid
        self.title = title


class _FakeTable:
    """Stands in for the picker's `QTableWidget`.

    **`setCurrentCell`, not `setCurrentRow`** — and getting that wrong is the
    whole reason this class is now pinned against the real widget below. The
    first version provided `setCurrentRow`, which `QListWidget` has and
    `QTableWidget` does not, so every test here passed while the shipped verb
    raised `AttributeError` on the rig 25 times in a single step. The stub was
    kinder than the product, exactly as `CLAUDE.md` warns.
    """

    def __init__(self) -> None:
        self.current = -1

    def setCurrentCell(self, row: int, column: int) -> None:  # noqa: N802 — Qt
        self.current = row


class ReleasePickerDialog:  # noqa: N801 — the name IS the interface here
    """Stand-in matched by class name, exactly as the runner matches the real one.

    **What it does that the real dialog does not:** it does not lay out widgets,
    does not populate a table, and `accept()` only records a flag instead of
    ending a modal loop. The three things the verb actually touches — `_releases`,
    `_table.setCurrentRow`, `accept()` — are pinned against the real class by
    `test_the_stand_in_matches_the_real_pickers_surface` below, so this cannot
    drift into satisfying a verb the product would not.
    """

    def __init__(self, releases: list[_Release], visible: bool = True) -> None:
        self._releases = releases
        self._table = _FakeTable()
        self._visible = visible
        self.accepted = False

    def isVisible(self) -> bool:  # noqa: N802 — Qt spelling
        return self._visible

    def accept(self) -> None:
        self.accepted = True


def _with_picker(monkeypatch: Any, dialog: Any) -> None:
    """Make `_release_picker()` find `dialog` (or nothing, for None)."""
    import platterpus.uiscript.runner as runner_mod

    monkeypatch.setattr(runner_mod, "_release_picker", lambda: dialog)


def test_the_stand_in_matches_the_real_pickers_surface() -> None:
    """The floor. A stub that answers whatever the verb asks would let the verb
    reach for attributes the real dialog does not have, and every test below
    would still pass while the verb died in front of an unattended batch."""
    from platterpus.ui.release_picker import ReleasePickerDialog as Real

    for name in ("_releases", "_table", "accept", "isVisible"):
        assert hasattr(Real, name) or f"self.{name}" in __import__("inspect").getsource(
            Real.__init__
        ), f"the real ReleasePickerDialog has no {name!r}, but the verb uses it"


def test_it_chooses_the_release_the_script_names(
    qapp, process_until, monkeypatch
) -> None:
    win = _window()
    runner = ScriptRunner(win)
    dialog = ReleasePickerDialog(
        [
            _Release("aaaa1111-0000-0000-0000-000000000000"),
            _Release("d14a7546-815b-43c6-8af6-35cff6cee1d0"),
            _Release("bbbb2222-0000-0000-0000-000000000000"),
        ]
    )
    _with_picker(monkeypatch, dialog)

    runner.start(parse("pick-release d14a7546-815b-43c6-8af6-35cff6cee1d0"))
    assert process_until(lambda: bool(runner._report.steps)), "never resolved"

    record = runner._report.steps[-1]
    assert record.outcome is Outcome.PASS, record.detail
    assert dialog._table.current == 1, "selected the wrong row"
    assert dialog.accepted, "the picker was never accepted"
    assert "d14a7546-815b-43c6-8af6-35cff6cee1d0" in record.detail
    assert "row 2 of 3" in record.detail


def test_the_optional_timeout_is_not_swallowed_into_the_mbid(
    qapp, process_until, monkeypatch
) -> None:
    """Regression: the first version used `joined()`, so `pick-release <mbid> 60`
    searched for "<mbid> 60" and matched nothing — the verb would have timed out
    on the very disc it was written for."""
    win = _window()
    runner = ScriptRunner(win)
    dialog = ReleasePickerDialog([_Release("d14a7546-815b-43c6-8af6-35cff6cee1d0")])
    _with_picker(monkeypatch, dialog)

    runner.start(parse("pick-release d14a7546-815b-43c6-8af6-35cff6cee1d0 60"))
    assert process_until(lambda: bool(runner._report.steps))
    assert runner._report.steps[-1].outcome is Outcome.PASS
    assert dialog.accepted


def test_an_unknown_release_fails_and_leaves_the_picker_alone(
    qapp, process_until, monkeypatch
) -> None:
    """Choosing *something else* would tag the rip from the wrong release — an
    error that survives into an archive. Failing the step is the cheap outcome."""
    win = _window()
    runner = ScriptRunner(win)
    dialog = ReleasePickerDialog([_Release("aaaa1111-0000-0000-0000-000000000000")])
    _with_picker(monkeypatch, dialog)

    runner.start(parse("pick-release ffff9999-0000-0000-0000-000000000000"))
    assert process_until(lambda: bool(runner._report.steps))

    record = runner._report.steps[-1]
    assert record.outcome is Outcome.FAIL
    assert not dialog.accepted, "it accepted a release the script did not name"
    assert dialog._table.current == -1, "it moved the selection anyway"
    assert "aaaa1111-0000-0000-0000-000000000000" in record.detail, (
        "the failure does not say what WAS offered, so it cannot be acted on"
    )


def test_no_picker_plus_loaded_tracks_is_a_pass_that_says_why(
    qapp, process_until, monkeypatch
) -> None:
    """A disc with one candidate opens no picker. That must not fail — but it is
    the 'satisfied by finding nothing' shape, so it is only accepted alongside
    positive evidence that the disc really did identify."""
    win = _window()  # the stub track table carries 14 tracks
    runner = ScriptRunner(win)
    _with_picker(monkeypatch, None)

    runner.start(parse("pick-release d14a7546"))
    assert process_until(lambda: bool(runner._report.steps))

    record = runner._report.steps[-1]
    assert record.outcome is Outcome.PASS
    assert "14 track(s) are loaded" in record.detail
    assert "nothing to pick" in record.detail


def test_no_picker_and_no_tracks_keeps_waiting_then_fails(
    qapp, process_until, monkeypatch
) -> None:
    """The case the pass above must not absorb: the scan simply has not finished.
    Passing here would report success for a disc that was never identified."""
    win = _window(track_table=_TrackTable(count=0))
    runner = ScriptRunner(win)
    _with_picker(monkeypatch, None)

    runner.start(parse("pick-release d14a7546 1"))
    assert process_until(lambda: bool(runner._report.steps), timeout=8.0)

    record = runner._report.steps[-1]
    assert record.outcome is Outcome.FAIL
    assert "no release picker appeared" in record.detail
    assert "no tracks" in record.detail


def test_an_ambiguous_prefix_refuses_rather_than_taking_the_first(
    qapp, process_until, monkeypatch
) -> None:
    win = _window()
    runner = ScriptRunner(win)
    dialog = ReleasePickerDialog(
        [
            _Release("d14a7546-aaaa-0000-0000-000000000000"),
            _Release("d14a7546-bbbb-0000-0000-000000000000"),
        ]
    )
    _with_picker(monkeypatch, dialog)

    runner.start(parse("pick-release d14a7546"))
    assert process_until(lambda: bool(runner._report.steps))
    assert runner._report.steps[-1].outcome is Outcome.FAIL
    assert not dialog.accepted


def test_a_picker_whose_internals_changed_is_reported_not_crashed(
    qapp, process_until, monkeypatch
) -> None:
    """The verb reaches `_table` duck-typed, because importing the real dialog
    here would be circular. That makes a rename an AttributeError inside an
    unattended batch unless it is checked — so it is checked, and it says which
    attribute went missing rather than dying."""

    class _Renamed:
        def __init__(self) -> None:
            self._releases = [_Release("d14a7546-815b-43c6-8af6-35cff6cee1d0")]
            self.accepted = False

        def isVisible(self) -> bool:  # noqa: N802 — Qt spelling
            return True

        def accept(self) -> None:
            self.accepted = True

    win = _window()
    runner = ScriptRunner(win)
    dialog = _Renamed()
    _with_picker(monkeypatch, dialog)

    runner.start(parse("pick-release d14a7546-815b-43c6-8af6-35cff6cee1d0"))
    assert process_until(lambda: bool(runner._report.steps))

    record = runner._report.steps[-1]
    assert record.outcome is Outcome.ERROR
    assert "setCurrentCell" in record.detail
    assert not dialog.accepted, "it accepted without ever moving the selection"


def test_the_fake_table_speaks_the_real_widgets_api() -> None:
    """The floor that was missing, and its absence shipped a broken verb.

    `test_the_stand_in_matches_the_real_pickers_surface` checked that the dialog
    has a `_table`. It did not check what that table *is*, so the fake was free
    to offer `setCurrentRow` — a `QListWidget` method — while the real
    `QTableWidget` has only `setCurrentCell`. Every test passed; the rig raised
    `AttributeError` 25 times in one step.

    So: every method the verb calls on the table is asserted to exist on the
    **real** widget class, and the method the fake does NOT have is asserted
    absent, so the fake cannot drift back into inventing API.
    """
    from PySide6.QtWidgets import QTableWidget

    from platterpus.ui.release_picker import ReleasePickerDialog as Real

    assert "QTableWidget" in inspect.getsource(Real.__init__), (
        "the picker no longer builds a QTableWidget — re-check what the verb calls"
    )
    assert hasattr(QTableWidget, "setCurrentCell"), (
        "the real widget lost setCurrentCell; the verb calls it"
    )
    assert not hasattr(QTableWidget, "setCurrentRow"), (
        "QTableWidget gained setCurrentRow — this test encodes that it has NOT, "
        "which is why the shipped verb was wrong; revisit the fix"
    )
    assert hasattr(_FakeTable, "setCurrentCell")
    assert not hasattr(_FakeTable, "setCurrentRow"), (
        "the fake is offering API the real widget does not have — the exact "
        "shape that let a broken verb ship"
    )


def test_a_faulting_predicate_ends_the_step_once(
    qapp, process_until, monkeypatch
) -> None:
    """One raise must end the step, not be retried every 120 ms forever.

    On the rig a single `AttributeError` produced **25 identical ERROR rows** for
    one script line, and only a human clicking the dialog stopped it. A
    transcript like that buries every other finding in the run.
    """
    import platterpus.uiscript.runner as runner_mod

    def boom() -> bool:
        raise RuntimeError("predicate is broken")

    win = _window()
    runner = ScriptRunner(win)
    monkeypatch.setattr(
        runner_mod,
        "_release_picker",
        lambda: (_ for _ in ()).throw(RuntimeError("predicate is broken")),
    )

    runner.start(parse("pick-release d14a7546 30"))
    assert process_until(lambda: bool(runner._report.steps))
    # Give it several more ticks — a retry loop would pile up more records.
    assert not process_until(lambda: len(runner._report.steps) > 1, timeout=2.0), (
        f"the faulting step was retried: {len(runner._report.steps)} records for "
        "one line — this is the 25-row rig failure"
    )

    record = runner._report.steps[0]
    assert record.outcome is Outcome.ERROR
    assert "faulted and the step was ended rather than retried" in record.detail
    assert "predicate is broken" in record.detail


# --- pick-release phase 2: the tracks have to actually arrive ---------------
#
# The rig failure this section pins (2026-08-18, app 0.6.16). `pick-release`
# returned PASS the instant it called `dialog.accept()`, but the window's
# `_fetch_release_detail` *emits* to the MusicBrainz worker thread rather than
# calling it — so at the moment the verb declared success, no release had been
# fetched, no tags applied and no track rows existed. Measured: picker accepted
# at 20:08:25,436, `expect-tracks 3` failed with "found 0" at 20:08:25,560 —
# 124 ms later. All eight failures in that run descend from this one line.
#
# Note what the pre-existing tests above could not see: `_TrackTable()` starts
# with 14 rows, so the stand-in was already in the post-fetch state before the
# verb ran. The fake was kinder than the product, which is why every one of them
# passed against the broken verb. These tests start EMPTY.


class _LateTrackTable(_TrackTable):
    """A track table that starts empty and is filled by the test, on cue.

    This is the difference between the harness and the rig that mattered: on the
    rig the table is empty when the picker closes and fills a network round-trip
    later. A fixture that is already full cannot express the bug.
    """

    def __init__(self) -> None:
        super().__init__(count=0)

    def arrive(self, count: int = 14) -> None:
        """The MusicBrainz release detail came back and the rows were built."""
        self._tracks = [_Track(n) for n in range(1, count + 1)]


def test_it_does_not_pass_until_the_tracks_actually_load(
    qapp, process_until, monkeypatch
) -> None:
    """The regression. Accepting the dialog is not the end of the work.

    Revert check: with `_try_pick_release` returning True straight after
    `dialog.accept()`, the first `process_until` below succeeds and the assertion
    that no step was recorded fails — which is the rig transcript exactly.
    """
    table = _LateTrackTable()
    win = _window(track_table=table)
    runner = ScriptRunner(win)
    dialog = ReleasePickerDialog([_Release("d14a7546-815b-43c6-8af6-35cff6cee1d0")])
    _with_picker(monkeypatch, dialog)

    runner.start(parse("pick-release d14a7546-815b-43c6-8af6-35cff6cee1d0 30"))

    # The picker is answered promptly...
    assert process_until(lambda: dialog.accepted), "the picker was never accepted"
    # ...and the step is still open, because nothing has loaded yet. This is the
    # window in which the old verb handed control to `expect-tracks`.
    assert not process_until(lambda: bool(runner._report.steps), timeout=1.0), (
        "pick-release reported a result while the track table was still empty — "
        "the rig race is back"
    )

    # The MB detail lands.
    table.arrive(14)
    assert process_until(lambda: bool(runner._report.steps)), "never resolved"

    record = runner._report.steps[-1]
    assert record.outcome is Outcome.PASS, record.detail
    assert "d14a7546-815b-43c6-8af6-35cff6cee1d0" in record.detail
    assert "14 track(s) loaded" in record.detail, (
        f"the transcript must record the positive evidence, got {record.detail!r}"
    )


def test_a_release_whose_tracks_never_arrive_fails_and_says_so(
    qapp, process_until, monkeypatch
) -> None:
    """Timing out after a successful pick must not blame the picker.

    The message armed at the start of the verb says "no release picker appeared".
    Once one has appeared and been answered, that sentence is false, and a report
    that carries it sends the next reader into the wrong subsystem. The failure
    is real either way; only the diagnosis differs, and the diagnosis is the
    whole value of the transcript.
    """
    table = _LateTrackTable()  # nothing ever arrives
    win = _window(track_table=table)
    runner = ScriptRunner(win)
    dialog = ReleasePickerDialog([_Release("d14a7546-815b-43c6-8af6-35cff6cee1d0")])
    _with_picker(monkeypatch, dialog)

    runner.start(parse("pick-release d14a7546-815b-43c6-8af6-35cff6cee1d0 1"))
    assert process_until(lambda: bool(runner._report.steps), timeout=10.0)

    record = runner._report.steps[-1]
    assert record.outcome is Outcome.FAIL, record.detail
    assert "no tracks ever loaded" in record.detail, record.detail
    assert "MusicBrainz" in record.detail, record.detail
    assert "no release picker appeared" not in record.detail, (
        "it blamed the picker, which appeared and was answered: " + record.detail
    )


def test_the_no_picker_and_picker_arms_demand_the_same_evidence(
    qapp, process_until, monkeypatch
) -> None:
    """Both branches of the verb must refuse to pass on an empty track table.

    The asymmetry is what shipped: the "no picker appeared" branch already
    required loaded tracks as positive evidence (a pass that can be satisfied by
    finding nothing is decoration — `CLAUDE.md`), while the "picker appeared"
    branch passed on an empty table. The rule had been applied where it was
    noticed rather than where it held.
    """
    for with_picker in (True, False):
        table = _LateTrackTable()
        win = _window(track_table=table)
        runner = ScriptRunner(win)
        dialog = (
            ReleasePickerDialog([_Release("d14a7546-815b-43c6-8af6-35cff6cee1d0")])
            if with_picker
            else None
        )
        _with_picker(monkeypatch, dialog)

        runner.start(parse("pick-release d14a7546-815b-43c6-8af6-35cff6cee1d0 30"))
        # `r=runner` binds this iteration's runner into the lambda. Without it
        # ruff's B023 fires and, worse, both iterations would poll whichever
        # runner the loop variable last held.
        assert not process_until(lambda r=runner: bool(r._report.steps), timeout=1.0), (
            f"passed on an empty track table (picker present: {with_picker})"
        )
        runner.stop()


# --- `(ripper)` in an album title: the two-pass collision fix ---------------
#
# A two-pass hardware session rips the same disc on two ripper builds. The album
# title decides the output folder, so a fixed title makes pass 2 land on top of
# pass 1 and destroy the evidence. The workaround was two `mv` commands handed to
# the operator between passes — hand-work the software should do (`CLAUDE.md`).


def _run_cyanrip_step(runner: ScriptRunner, output: str, exit_code: int = 0) -> None:
    """Play a completed `cyanrip` verb through the runner's REAL collector.

    Deliberately not `runner._last_cyanrip_output = banner`, which is what this
    helper used to do. That shortcut is the *"what does my stand-in do that the
    real thing does not?"* trap in miniature: it wrote the field the reader read,
    so it would have kept passing against a build where the absorber that
    populates the latch was never called at all — which is precisely the 0.6.18
    defect. Constructing the job and calling `_service_cyanrip` exercises the
    production path from a finished subprocess to the latched tag.
    """
    job = _CyanripJob(
        step=parse("cyanrip --version")[0],
        argv=["cyanrip", "--version"],
        started=time.monotonic(),
        done=threading.Event(),
        result=(exit_code, output),
    )
    job.done.set()
    runner._pending_cyanrip = job
    runner._service_cyanrip()


def _window_with_banner(runner: ScriptRunner, banner: str) -> None:
    """Give the runner a captured `cyanrip --version` banner, as section A does."""
    if banner:
        _run_cyanrip_step(runner, banner)


def test_the_ripper_placeholder_expands_to_the_installed_build_tag(qapp) -> None:
    win = _window()
    runner = ScriptRunner(win)
    _window_with_banner(
        runner, "cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)"
    )

    runner._execute(parse("album cancel me (ripper)")[0])

    record = runner._report.steps[-1]
    assert record.outcome is Outcome.PASS, record.detail
    assert win._track_table._album_title_edit.text() == (
        "cancel me platterpus-fork-gddf7ac3"
    )


def test_two_builds_produce_two_different_album_folders(qapp) -> None:
    """The property the whole fix exists for, asserted as a RELATION.

    Testing one expansion alone would pass against a function that returned a
    constant. What matters is that two different builds give two different
    titles — that is what stops pass 2 overwriting pass 1.
    """
    titles = []
    for banner in (
        "cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)",
        "cyanrip 0.9.4-rc1+platterpus.6 (platterpus-fork-gc4d1a00)",
    ):
        win = _window()
        runner = ScriptRunner(win)
        _window_with_banner(runner, banner)
        runner._execute(parse("album cancel me (ripper)")[0])
        titles.append(win._track_table._album_title_edit.text())

    assert titles[0] != titles[1], (
        f"both builds produced the album folder {titles[0]!r} — pass 2 would "
        "overwrite pass 1's evidence, which is the bug this fixes"
    )
    assert "ddf7ac3" in titles[0] and "c4d1a00" in titles[1], titles


def test_a_later_cyanrip_step_cannot_destroy_the_latched_build_tag(qapp) -> None:
    """The 0.6.18 regression, reproduced from the rig transcript.

    Sequence, exactly as `rigcancelandoverread.txt` runs it: section A captures
    the `--version` banner, section C runs the cache probe, section D expands
    `(ripper)` into the album title. On the real rig section C's probe TIMED OUT
    (`-x` rips the whole disc, so the verb's five-minute ceiling ended it), and
    the timeout path wrote its own error text into the single
    `_last_cyanrip_output` slot the placeholder was reading. Both `album …
    (ripper)` steps then failed with "no build tag has been captured yet" —
    twenty minutes after the tag had been captured and thrown away.

    The rip fell back to the default album title, which is how a cancelled rip's
    two FLACs landed in the real album folder and produced the overwrite prompt
    the maintainer reported as *"that doesn't seem right"*.

    So the assertion is about SURVIVAL, not expansion: the test above already
    proves a fresh banner expands. This one proves a banner survives the traffic
    that follows it.
    """
    win = _window()
    runner = ScriptRunner(win)
    _window_with_banner(
        runner, "cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)"
    )

    # Section C: a `cyanrip` step whose output carries no version banner at all.
    # Both shapes the rig produced, in the order it produced them.
    _run_cyanrip_step(runner, "Cache probe: 32 sectors\nRipping...", exit_code=1)
    runner._last_cyanrip_output = ""  # the timeout path's own invalidation

    runner._execute(parse("album cancel me (ripper)")[0])

    record = runner._report.steps[-1]
    assert record.outcome is Outcome.PASS, record.detail
    assert win._track_table._album_title_edit.text() == (
        "cancel me platterpus-fork-gddf7ac3"
    ), (
        "a later cyanrip step destroyed the build tag — this is the defect that "
        "sent a cancelled rip into the real album folder"
    )


def test_an_unresolvable_ripper_placeholder_fails_loudly(qapp) -> None:
    """Refusing beats writing the literal text.

    A silently unexpanded `(ripper)` gives both passes the SAME folder name — it
    restores the exact collision the placeholder exists to prevent, while looking
    like it worked. The step fails and names the cause instead.
    """
    win = _window()
    runner = ScriptRunner(win)
    _window_with_banner(runner, "")  # no `cyanrip --version` ran yet

    runner._execute(parse("album cancel me (ripper)")[0])

    record = runner._report.steps[-1]
    assert record.outcome is Outcome.FAIL, record.detail
    assert "cyanrip --version" in record.detail
    assert "(ripper)" not in win._track_table._album_title_edit.text(), (
        "the literal placeholder was written into the album title"
    )


def test_a_title_without_the_placeholder_is_untouched(qapp) -> None:
    """Non-triviality: the expansion must not rewrite ordinary titles, and must
    not require a banner for them."""
    win = _window()
    runner = ScriptRunner(win)
    _window_with_banner(runner, "")

    runner._execute(parse("album Every Breath You Take")[0])

    record = runner._report.steps[-1]
    assert record.outcome is Outcome.PASS, record.detail
    assert win._track_table._album_title_edit.text() == "Every Breath You Take"


# --- `answer-dialog`: the verb that had to exist ----------------------------
#
# Added 2026-08-20 after the cancel-path rig run finished pass=58 fail=2 with
# BOTH failures descending from one unanswered "Album already ripped" modal. The
# obvious fix — put `ok` after `rip` — is a race, because `rip` returns as soon
# as the start is *requested* and the confirmation appears a beat later. These
# tests pin the waiting and the refusal-to-answer-the-wrong-thing, because those
# are the two properties a bare `ok` does not have.


def _drive_deadline(runner: Any, process_until: Any, timeout: float = 2.0) -> Any:
    """Pump until the runner's armed deadline resolves; return its record."""
    process_until(lambda: _service_and_check(runner), timeout=timeout)
    return runner._report.steps[-1] if runner._report.steps else None


def _service_and_check(runner: Any) -> bool:
    if runner._deadline is None:
        return True
    runner._service_deadline()
    return runner._deadline is None


def test_answer_dialog_waits_for_a_dialog_that_is_not_up_yet(
    qapp, process_until
) -> None:
    """**The regression test for the race.**

    A bare `ok` fails here with "no dialog is open", which is the whole reason
    this verb exists: on the rig the dialog arrives after the step that provoked
    it has already returned. So the dialog is deliberately created *after* the
    step is executed, which is the ordering a script actually meets.
    """
    from PySide6.QtWidgets import QDialog

    win = _window()
    record, runner = _run_one(win, "answer-dialog ok 30 Album already ripped")
    assert record is None, "the verb should arm a deadline, not resolve instantly"

    dialog = QDialog(win)
    dialog.setWindowTitle("Album already ripped")
    dialog.setModal(True)
    dialog.show()
    try:
        assert process_until(lambda: dialog.isVisible())
        resolved = _drive_deadline(runner, process_until)
        assert resolved is not None, "the deadline never resolved"
        assert resolved.outcome is Outcome.PASS, resolved.detail
        assert "accepted" in resolved.detail, resolved.detail
        assert "Album already ripped" in resolved.detail, (
            "the transcript must name WHICH dialog was answered — an unattended "
            "run has no operator to remember"
        )
    finally:
        dialog.close()
        dialog.deleteLater()


def test_answer_dialog_refuses_to_answer_a_dialog_it_was_not_told_to_expect(
    qapp, process_until
) -> None:
    """The property that makes an unattended accept safe.

    A verb that answered whatever was on top would dismiss a crash report, an
    overwrite prompt, or a "disc has changed" without anyone knowing. This one
    leaves it alone and says what it saw.

    Asserted on the DIALOG'S STATE, not only on the record: a guard that recorded
    FAIL and accepted anyway would pass a record-only check.
    """
    from PySide6.QtWidgets import QDialog

    win = _window()
    dialog = QDialog(win)
    dialog.setWindowTitle("Something nobody predicted")
    dialog.setModal(True)
    dialog.show()
    try:
        assert process_until(lambda: dialog.isVisible())
        _, runner = _run_one(win, "answer-dialog ok 1 Album already ripped")
        resolved = _drive_deadline(runner, process_until, timeout=4.0)
        assert resolved is not None, "the deadline never resolved"
        assert resolved.outcome is Outcome.FAIL, resolved.detail
        assert "Something nobody predicted" in resolved.detail, (
            "the timeout must name the dialog it found instead — 'no dialog "
            "appeared' and 'the wrong one appeared' are different findings"
        )
        assert dialog.isVisible(), (
            "the unexpected dialog was ANSWERED; refusing to touch it is the "
            "entire safety property of this verb"
        )
    finally:
        dialog.close()
        dialog.deleteLater()


def test_answer_dialog_says_no_dialog_opened_at_all_when_none_does(
    qapp, process_until
) -> None:
    """The other half of the timeout, which must not be conflated with the first.

    Nothing opened => the action that should have raised it did not run. A
    different dialog opened => the app did something unexpected. Reporting both
    as one message throws away the distinction that tells you which.
    """
    win = _window()
    _, runner = _run_one(win, "answer-dialog ok 1 Album already ripped")
    resolved = _drive_deadline(runner, process_until, timeout=4.0)
    assert resolved is not None, "the deadline never resolved"
    assert resolved.outcome is Outcome.FAIL, resolved.detail
    assert "no dialog opened at all" in resolved.detail, resolved.detail


def test_answer_dialog_rejects_a_zero_timeout_because_that_is_the_race() -> None:
    """A zero wait is `ok` with extra steps, so it is refused by name."""
    win = _window()
    record, _ = _run_one(win, "answer-dialog ok 0 Album already ripped")
    assert record is not None
    assert record.outcome is Outcome.ERROR, record.detail
    assert "race" in record.detail, record.detail


def test_answer_dialog_rejects_an_unknown_action() -> None:
    win = _window()
    record, _ = _run_one(win, "answer-dialog maybe 30 Album already ripped")
    assert record is not None
    assert record.outcome is Outcome.ERROR, record.detail
    # Asserted token by token rather than on one phrasing, so growing the
    # vocabulary again does not silently stop checking the earlier members.
    for token in ("ok", "cancel", "click="):
        assert token in record.detail, (
            f"the refusal must name {token!r} as an accepted form; a script "
            f"author reads this message instead of the source"
        )


# --- `answer-dialog click=<label>`: two answers were not enough -------------
#
# `ok`/`cancel` call accept()/reject(), which is the entire vocabulary a
# two-button dialog needs. A dialog with three NAMED choices cannot be answered
# that way at all — and it fails at it *silently*, which is why this needed a
# verb rather than a note. Added 2026-08-21, before it shipped, by reading
# `_confirm_known_overwrite`'s fall-through rather than assuming it.


def _three_button_box(parent: Any, title: str) -> Any:
    """A QMessageBox shaped exactly like `_confirm_known_overwrite`'s.

    Built with `addButton` and a `RejectRole` cancel — the shape whose
    `clickedButton()` stays None after `accept()`. The stand-in must not be
    kinder than the product, so the buttons are added the same way and in the
    same order the product adds them.
    """
    from PySide6.QtWidgets import QMessageBox

    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText("This album already has a rip.")
    replace = box.addButton("Replace it", QMessageBox.ButtonRole.DestructiveRole)
    new_folder = box.addButton("Rip to a new folder", QMessageBox.ButtonRole.AcceptRole)
    cancel = box.addButton(QMessageBox.StandardButton.Cancel)
    box.setDefaultButton(cancel)
    box.setModal(True)
    return box, replace, new_folder, cancel


def test_answer_dialog_click_presses_the_named_button(qapp, process_until) -> None:
    """**The reason this form exists.**

    Asserted on `clickedButton()` — the thing the product branches on — not on
    the record. A verb that recorded PASS while leaving `clickedButton()` as
    None is exactly the defect being fixed, and a record-only check would pass
    against it.
    """
    win = _window()
    box, _replace, new_folder, _cancel = _three_button_box(win, "Album already ripped")
    box.show()
    try:
        assert process_until(lambda: box.isVisible())
        _, runner = _run_one(win, "answer-dialog click=new 5 Album already ripped")
        resolved = _drive_deadline(runner, process_until, timeout=6.0)
        assert resolved is not None, "the deadline never resolved"
        assert resolved.outcome is Outcome.PASS, resolved.detail
        assert box.clickedButton() is new_folder, (
            f"the named button was not the one pressed; clickedButton() is "
            f"{box.clickedButton()!r}. This is the assertion the whole form "
            f"exists for — `ok` leaves it None."
        )
        assert "Rip to a new folder" in resolved.detail, (
            "the transcript must name the FULL label that was pressed, not the "
            "substring the script happened to type — an unattended run's "
            "transcript is the only record of which choice was taken"
        )
    finally:
        box.close()
        box.deleteLater()


def test_answer_dialog_ok_does_not_choose_a_button_on_this_dialog_shape(
    qapp, process_until
) -> None:
    """**Pins the Qt behaviour that made `ok` unsafe here, so we learn if it moves.**

    `accept()` on a QMessageBox built with `addButton` closes the dialog and
    leaves `clickedButton()` as **None**. A caller shaped like
    `_confirm_known_overwrite` — `if clicked is replace … if clicked is new …
    return None  # Cancel` — therefore falls through to CANCEL. So
    `answer-dialog ok` on this dialog would have cancelled the rip while the
    transcript said "accepted", and no assertion in this file would have
    noticed.

    This test does not assert a bug in our code; it asserts the Qt fact the
    `click=` form was added because of. If a future PySide6 makes `accept()`
    populate `clickedButton()`, this fails and the reasoning gets re-read
    rather than inherited.
    """
    win = _window()
    box, _replace, _new_folder, _cancel = _three_button_box(win, "Album already ripped")
    box.show()
    try:
        assert process_until(lambda: box.isVisible())
        _, runner = _run_one(win, "answer-dialog ok 5 Album already ripped")
        resolved = _drive_deadline(runner, process_until, timeout=6.0)
        assert resolved is not None, "the deadline never resolved"
        assert resolved.outcome is Outcome.PASS, resolved.detail
        assert "accepted" in resolved.detail, resolved.detail
        assert box.clickedButton() is None, (
            "PySide6 now reports a clicked button after accept() on an "
            "addButton-built QMessageBox. That is the premise `click=` was "
            "added on — re-read the reasoning in `_do_answer_dialog` before "
            "changing this test to match."
        )
    finally:
        box.close()
        box.deleteLater()


def test_answer_dialog_click_names_every_button_when_none_matches(
    qapp, process_until
) -> None:
    """A refusal has to carry the labels, or the author is left guessing.

    The one thing a script author needs at this moment is the text of the
    buttons that were actually there — that is the input to the fix. Also
    asserts nothing was clicked: a guard that reported FAIL and pressed
    something anyway would pass a record-only check.
    """
    win = _window()
    box, _replace, _new_folder, _cancel = _three_button_box(win, "Album already ripped")
    box.show()
    try:
        assert process_until(lambda: box.isVisible())
        _, runner = _run_one(
            win, "answer-dialog click=obliterate 1 Album already ripped"
        )
        resolved = _drive_deadline(runner, process_until, timeout=4.0)
        assert resolved is not None, "the deadline never resolved"
        assert resolved.outcome is Outcome.FAIL, resolved.detail
        assert "Replace it" in resolved.detail, resolved.detail
        assert "Rip to a new folder" in resolved.detail, resolved.detail
        assert box.clickedButton() is None, "a non-matching name pressed something"
        assert box.isVisible(), "the dialog was answered despite no match"
    finally:
        box.close()
        box.deleteLater()


def test_answer_dialog_click_refuses_an_ambiguous_substring(
    qapp, process_until
) -> None:
    """Two matches is a refusal, not a coin flip.

    Same call `uiscript/find_script.py` makes for two files matching one name,
    and for the same reason: guessing here answers a question the wrong way, and
    the transcript would say it answered it correctly. `rip` matches both
    "Rip to a new folder" and "Rip and keep both".
    """
    from PySide6.QtWidgets import QMessageBox

    win = _window()
    box = QMessageBox(win)
    box.setWindowTitle("Album already ripped")
    box.addButton("Rip to a new folder", QMessageBox.ButtonRole.AcceptRole)
    box.addButton("Rip and keep both", QMessageBox.ButtonRole.AcceptRole)
    box.setModal(True)
    box.show()
    try:
        assert process_until(lambda: box.isVisible())
        _, runner = _run_one(win, "answer-dialog click=rip 1 Album already ripped")
        resolved = _drive_deadline(runner, process_until, timeout=4.0)
        assert resolved is not None, "the deadline never resolved"
        assert resolved.outcome is Outcome.FAIL, resolved.detail
        assert "matches 2 buttons" in resolved.detail, resolved.detail
        assert box.clickedButton() is None, (
            "an ambiguous substring picked one anyway — the transcript would "
            "then record a confident answer to the wrong question"
        )
    finally:
        box.close()
        box.deleteLater()


def test_answer_dialog_click_refuses_a_disabled_button(qapp, process_until) -> None:
    """The failure nobody thinks of, and the only silent one left.

    `QAbstractButton.click()` on a disabled button raises nothing and does
    nothing. Without this check the step records PASS, the dialog stays on
    screen, and the NEXT step's failure gets the blame.
    """
    from PySide6.QtWidgets import QMessageBox

    win = _window()
    box = QMessageBox(win)
    box.setWindowTitle("Album already ripped")
    disabled = box.addButton("Rip to a new folder", QMessageBox.ButtonRole.AcceptRole)
    disabled.setEnabled(False)
    box.addButton(QMessageBox.StandardButton.Cancel)
    box.setModal(True)
    box.show()
    try:
        assert process_until(lambda: box.isVisible())
        _, runner = _run_one(win, "answer-dialog click=new 1 Album already ripped")
        resolved = _drive_deadline(runner, process_until, timeout=4.0)
        assert resolved is not None, "the deadline never resolved"
        assert resolved.outcome is Outcome.FAIL, resolved.detail
        assert "DISABLED" in resolved.detail, resolved.detail
        assert box.clickedButton() is None
        assert box.isVisible(), "a disabled button still closed the dialog"
    finally:
        box.close()
        box.deleteLater()


def test_answer_dialog_click_says_so_when_the_dialog_has_no_buttons(
    qapp, process_until
) -> None:
    """A plain QDialog cannot be answered by name, and must say that."""
    from PySide6.QtWidgets import QDialog

    win = _window()
    dialog = QDialog(win)
    dialog.setWindowTitle("Album already ripped")
    dialog.setModal(True)
    dialog.show()
    try:
        assert process_until(lambda: dialog.isVisible())
        _, runner = _run_one(win, "answer-dialog click=new 1 Album already ripped")
        resolved = _drive_deadline(runner, process_until, timeout=4.0)
        assert resolved is not None, "the deadline never resolved"
        assert resolved.outcome is Outcome.FAIL, resolved.detail
        assert "no buttons at all" in resolved.detail, resolved.detail
        assert "'ok' or 'cancel'" in resolved.detail, (
            "the message must name the form that WOULD work here"
        )
    finally:
        dialog.close()
        dialog.deleteLater()


def test_answer_dialog_rejects_an_empty_click_substring() -> None:
    """`click=` with nothing after it would match every button."""
    win = _window()
    record, _ = _run_one(win, "answer-dialog click= 30 Album already ripped")
    assert record is not None
    assert record.outcome is Outcome.ERROR, record.detail
    assert "substring" in record.detail, record.detail


# --- The pure matcher, tested where the refusal branches are reachable ------


def test_button_matching_is_case_insensitive_and_refuses_ambiguity() -> None:
    from platterpus.uiscript.runner import _match_button_label

    labels = ["Replace it", "Rip to a new folder", "Cancel"]
    assert _match_button_label(labels, "NEW") == (1, "")
    assert _match_button_label(labels, "replace")[0] == 0

    index, why = _match_button_label(labels, "r")
    assert index is None, "a one-letter substring matching 3 labels picked one"
    assert "refuses to guess" in why, why

    index, why = _match_button_label(labels, "nope")
    assert index is None
    for label in labels:
        assert repr(label) in why, f"the refusal dropped {label!r}"

    index, why = _match_button_label([], "new")
    assert index is None
    assert "no buttons at all" in why, why


def test_one_sweep_finds_the_same_buttons_qmessagebox_reports_itself(qapp) -> None:
    """**Pins the measurement that deleted a special case.**

    `_dialog_buttons` used to branch on `isinstance(dialog, QMessageBox)` to use
    the box's own `buttons()`, on the stated grounds that a `findChildren` sweep
    would additionally pick up the internal "Show Details…" toggle. Measured on
    PySide6 6.9.1, that is false — `buttons()` reports the toggle too — so the
    branch distinguished nothing and was removed. The revert-proof had already
    said so by failing to fail.

    This test is what stops that from being a claim in a comment. A detailed-text
    box is used deliberately, because the toggle is the only button the two
    accessors could plausibly disagree about. Compared as SETS, since the two
    orders genuinely differ and order is not something we depend on.
    """
    from PySide6.QtWidgets import QAbstractButton, QMessageBox

    from platterpus.uiscript.runner import _dialog_buttons

    box = QMessageBox()
    box.setText("hi")
    box.setDetailedText("the gory details")
    box.addButton("Replace it", QMessageBox.ButtonRole.DestructiveRole)
    box.addButton(QMessageBox.StandardButton.Cancel)
    try:
        own = {b.text() for b in box.buttons()}
        swept = {b.text() for b in box.findChildren(QAbstractButton)}
        assert own == swept, (
            f"QMessageBox.buttons() and a findChildren sweep now DISAGREE — "
            f"buttons()={sorted(own)}, sweep={sorted(swept)}. Re-read the "
            f"docstring of `_dialog_buttons`: the special case was deleted "
            f"because these were measured equal."
        )
        assert len(swept) >= 3, (
            "fewer than three buttons means the fixture stopped building the "
            "shape this test is about, and the comparison above is vacuous"
        )
        assert {b.text() for b in _dialog_buttons(box)} == own, (
            "the production accessor no longer returns what the box reports"
        )
    finally:
        box.deleteLater()


def test_mnemonic_markers_are_stripped_but_a_literal_ampersand_survives() -> None:
    """`&Replace` reads as "Replace"; `Save && Close` reads as "Save & Close".

    The second half is why this is not a bare `.replace("&", "")`: that would
    render the label `Save  Close`, and a script written as `click=&` — or as
    `click=save & close` — would then match nothing while the button sat right
    there.
    """
    from platterpus.uiscript.runner import _plain_label

    assert _plain_label("&Replace it") == "Replace it"
    assert _plain_label("Rip to a &new folder") == "Rip to a new folder"
    assert _plain_label("Save && Close") == "Save & Close"
    assert _plain_label("Cancel") == "Cancel"


def test_wait_for_rip_advises_the_non_racy_verb() -> None:
    """The advice the app prints must not reintroduce the bug.

    Before 0.6.20 this message said to add `ok`, which races the very dialog it
    is complaining about. Guidance that is wrong is worse than none: it is
    followed.
    """
    from PySide6.QtWidgets import QDialog

    win = _window()
    dialog = QDialog(win)
    dialog.setWindowTitle("Album already ripped")
    dialog.setModal(True)
    dialog.show()
    try:
        record, _ = _run_one(win, "wait-for-rip 30")
        assert record is not None
        assert record.outcome is Outcome.FAIL, record.detail
        assert "answer-dialog" in record.detail, record.detail
        assert "NOT a bare `ok`" in record.detail, (
            "the message must say why the obvious fix is wrong, or it will be "
            "applied anyway"
        )
    finally:
        dialog.close()
        dialog.deleteLater()


# --- expect-status: implemented 2026-08-24, and it names its surface ---------


def test_expect_status_matches_the_rip_status_line_case_insensitively(qapp) -> None:
    """The verb the full-acceptance run needed and got an ERROR from.

    It sat in the table `implemented=False` with a written reason — there is no
    single "status line" to assert against, so any implementation would pick one
    surface and *silently* mean only that. The objection was about the silence:
    the fix is to pick the surface and say which, in the help text and in every
    message. It reads `RipProgress.current_status()`, which is also what the
    desktop notification reads, so the two cannot disagree.

    Case-insensitive substring, like `expect-dialog`: the real line carries a
    `HH:MM:SS ·` stamp and a sentence assembled from several sources, so an exact
    match is unusable and case is unpredictable from a script.
    """
    win = _window(
        rip_progress=_RipProgress(
            "Done — all 2 tracks ripped cleanly, no read errors. "
            "AccurateRip: all 2 verified."
        )
    )
    record, _ = _run_one(win, "expect-status all 2 tracks ripped cleanly")
    assert record.outcome is Outcome.PASS, record.detail
    # Case folded in BOTH directions, not just one.
    record, _ = _run_one(win, "expect-status ACCURATERIP: ALL 2 VERIFIED")
    assert record.outcome is Outcome.PASS, record.detail


def test_expect_status_failure_quotes_the_line_it_actually_read(qapp) -> None:
    """A status assertion that says only "no match" makes the reader re-run a
    two-hour rip to discover what it did say."""
    win = _window(rip_progress=_RipProgress("Rip cancelled by user."))
    record, _ = _run_one(win, "expect-status ripped cleanly")
    assert record.outcome is Outcome.FAIL
    assert "Rip cancelled by user." in record.detail, (
        f"the failure did not report the line it read: {record.detail!r}"
    )


def test_expect_status_says_so_when_no_status_has_been_set(qapp) -> None:
    """An empty line is a different fact from a wrong line, and reporting the
    empty string as the "actual" reads like a rendering bug."""
    win = _window(rip_progress=_RipProgress(""))
    record, _ = _run_one(win, "expect-status anything")
    assert record.outcome is Outcome.FAIL
    assert "empty" in record.detail and "no status has been set" in record.detail


def test_expect_status_errors_rather_than_passing_when_the_pane_is_missing(
    qapp,
) -> None:
    """A missing surface must never read as a satisfied assertion — the
    "can this check be satisfied by finding nothing?" question."""
    win = _window()
    del win._rip_progress
    record, _ = _run_one(win, "expect-status anything")
    assert record.outcome is Outcome.ERROR
    assert "status line" in record.detail


def test_the_preflight_names_an_unimplemented_verb_before_step_one_runs() -> None:
    """MEASURED: the full-acceptance run found this at step 179 of 288, 1h 49m in.

    The verb table was honest and the generated reference printed
    `NOT IMPLEMENTED`; the handler lookup simply happens at dispatch, so a batch
    learns about it when it gets there. `_preflight` already did exactly this job
    for `cyanrip` steps — one function wide — and `uses_unsafe`'s docstring
    already states the principle: *"an unattended run that dies two-thirds
    through is worse than one that never started."*

    Uses a verb that is *currently* unimplemented rather than a hardcoded name,
    so the test keeps testing the mechanism as verbs land. It skips if the table
    ever has none left, and asserts the population is non-empty rather than
    passing vacuously on an empty sweep.
    """
    from platterpus.uiscript import verbs as verbs_mod
    from platterpus.uiscript.runner import _preflight

    unimplemented = [n for n, v in verbs_mod.VERBS.items() if not v.implemented]
    if not unimplemented:
        pytest.skip("every verb is implemented — the happy future")
    name = unimplemented[0]
    steps = parse(f"log fine\n{name} something")
    problems = _preflight(steps)
    assert problems, f"preflight said nothing about the unimplemented {name!r}"
    joined = "\n".join(problems)
    assert name in joined and "no handler" in joined, joined
    assert "L2" in joined, f"the notice must name the line: {joined}"
    # And it must not cry wolf over the implemented verb on line 1.
    assert len(problems) == 1, f"preflight flagged an implemented verb too: {problems}"


def test_an_unimplemented_unsafe_verb_blames_the_missing_handler_not_a_checkbox(
    qapp,
) -> None:
    """`eval` and `call` are BOTH unsafe and unimplemented, and the order of the
    two refusals decides whether the message is useful.

    With the unsafe gate first, a script using `eval` was told *"this verb needs
    the 'allow unsafe script verbs' setting, which is off"* — true, and the wrong
    cause. Ticking that box (in Settings, or the console's own checkbox, both of
    which advertised the verbs by name) changes nothing: the very next line
    refuses the same step for having no handler. A true diagnosis of the wrong
    cause is the expensive kind, because it sends somebody into Settings instead
    of telling them the verb does not exist.

    Uses whichever unsafe+unimplemented verbs the table actually has, so it keeps
    testing the property rather than a hardcoded name, and asserts the population
    is non-empty rather than passing on an empty sweep.
    """
    from platterpus.uiscript import verbs as verbs_mod

    candidates = [
        n for n, v in verbs_mod.VERBS.items() if v.unsafe and not v.implemented
    ]
    if not candidates:
        pytest.skip("no verb is both unsafe and unimplemented — the happy future")
    win = _window()
    for name in candidates:
        record, _ = _run_one(win, f"{name} whatever")
        assert record.outcome is Outcome.ERROR, (
            f"{name} is unimplemented, so it must ERROR rather than report as "
            f"merely gated: got {record.outcome} — {record.detail}"
        )
        assert "not implemented" in record.detail, record.detail
        assert "setting" not in record.detail, (
            f"{name} blamed a setting the user could tick, which would not have "
            f"helped: {record.detail!r}"
        )
