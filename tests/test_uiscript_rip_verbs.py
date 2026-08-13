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
import json
from pathlib import Path
from typing import Any

import pytest

from platterpus.config import Config
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner
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
    """Never a silent clamp: the transcript says the wait was refused."""
    from platterpus.uiscript.runner import MAX_RIP_WAIT_S

    win = _window()
    record, _ = _run_one(win, f"wait-for-rip {int(MAX_RIP_WAIT_S) + 1000}")
    assert record.outcome is Outcome.FAIL
    assert "cap" in record.detail


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
    def __init__(self) -> None:
        self.current = -1

    def setCurrentRow(self, row: int) -> None:  # noqa: N802 — Qt spelling
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
