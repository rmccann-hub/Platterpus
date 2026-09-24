"""`set-drive-offset`, `expect-drive-offset` and `(offset)`: the drive's offset, not 667.

The acceptance script said `set read_offset 667`: the Pioneer BDR-209D's offset,
and wrong on every other drive. A second machine would have ripped the whole run
at the wrong offset with every AccurateRip check failing for our reason. The verb
keeps the offset this machine is already set to, or takes the AccurateRip drive
list's, and fails naming the fix if neither is known.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from platterpus.config import Config
from platterpus.uiscript.report import Outcome, RunReport, StepRecord
from platterpus.uiscript.runner import ScriptRunner
from platterpus.uiscript.script import (
    args_as_preflight_sees_them,
    expand_offset,
    parse,
)


@dataclass
class _Drive:
    vendor: str = "PIONEER "
    model: str = "BD-RW   BDR-209D"


class _Picker:
    def __init__(self, drive: _Drive | None) -> None:
        self._drive = drive

    def current_drive(self) -> _Drive | None:
        return self._drive


class _OffsetList:
    def __init__(self, known: int | None) -> None:
        self._known = known

    def lookup(self, vendor: str, model: str) -> int | None:
        return self._known


@dataclass
class _Window:
    """What the verbs read: the config, the drive picker, the list, the writer."""

    _config: Config = field(default_factory=Config)
    _drive_picker: _Picker = field(default_factory=lambda: _Picker(_Drive()))
    _offset_db: _OffsetList = field(default_factory=lambda: _OffsetList(667))
    written: list[int] = field(default_factory=list)

    def _set_read_offset_override(self, value: int) -> bool:
        # The app's own writer validates and saves; this stand-in records the call
        # and applies it the same way, so the verbs are seen going through it.
        self.written.append(value)
        self._config.read_offset = value
        self._config.override_read_offset = True
        return True


def _run(script: str, window: _Window) -> list[StepRecord]:
    runner = ScriptRunner(window)  # type: ignore[arg-type]  # a stand-in, by design
    runner._report = RunReport(started_at="t", app_version="test")
    for step in parse(script):
        runner._execute(step)
    return runner._report.steps


def test_a_machine_with_no_offset_takes_the_accuraterip_lists() -> None:
    window = _Window()
    steps = _run("set-drive-offset\nexpect-drive-offset", window)
    assert [s.outcome for s in steps] == [Outcome.PASS, Outcome.PASS]
    assert window.written == [667], "the app's own writer was not used"
    assert "AccurateRip drive list" in steps[0].detail


def test_an_offset_this_machine_is_already_set_to_is_kept() -> None:
    """A drive the list does not carry: the machine's own offset is the only one."""
    window = _Window(
        _config=Config(read_offset=102, override_read_offset=True),
        _offset_db=_OffsetList(None),
    )
    steps = _run("set-drive-offset", window)
    assert steps[0].outcome is Outcome.PASS
    assert window._config.read_offset == 102
    assert "already set to" in steps[0].detail


def test_a_disagreement_with_the_list_is_named_not_hidden() -> None:
    window = _Window(_config=Config(read_offset=102, override_read_offset=True))
    detail = _run("set-drive-offset", window)[0].detail
    assert "+102" in detail and "+667" in detail


def test_no_known_offset_fails_and_names_the_fix() -> None:
    window = _Window(_offset_db=_OffsetList(None))
    steps = _run("set-drive-offset", window)
    assert steps[0].outcome is Outcome.FAIL
    assert "Set up drive" in steps[0].detail
    assert window.written == [], "nothing may be written when nothing is known"


def test_expect_drive_offset_fails_when_the_offset_moved() -> None:
    window = _Window()
    steps = _run("set-drive-offset\nset read_offset 6\nexpect-drive-offset", window)
    assert steps[-1].outcome is Outcome.FAIL
    assert "+667" in steps[-1].detail


def test_expect_drive_offset_needs_a_set_drive_offset_first() -> None:
    steps = _run("expect-drive-offset", _Window())
    assert steps[0].outcome is Outcome.FAIL


def test_the_placeholder_expands_to_the_offset_and_preflight_sees_a_valid_one() -> None:
    args = ["-N", "-s", "(offset)", "-l", "1"]
    assert expand_offset(args, 667) == ["-N", "-s", "667", "-l", "1"]
    assert args_as_preflight_sees_them(args) == ["-N", "-s", "0", "-l", "1"]


def test_a_cyanrip_step_with_the_placeholder_fails_before_any_offset_is_set() -> None:
    """Not run with a literal `(offset)`, and not with a guessed value either."""
    steps = _run("cyanrip -N -s (offset) -l 1", _Window())
    assert steps[0].outcome is Outcome.FAIL
    assert "no set-drive-offset has run" in steps[0].detail
