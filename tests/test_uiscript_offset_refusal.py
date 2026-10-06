"""`expect-offset-refusal`: the offset-override-off path (TASKS C4 (a), KDD-41).

With the override off, Start applies the AccurateRip list's offset on a listed
drive and refuses any other drive with *"Set up your drive first"*. The verb
records `UNREACHABLE` on a listed drive, touching nothing, and grades the
refusal on any other, putting the override back on every path.

**The refusal under test is the REAL one.** The stand-in window's Start calls the
real `RipMixin._on_rip_requested`, with the real `DriveMixin.
_auto_apply_known_offset` bound to it, and `message_boxes.warning` is given its
real, blocking body (`_run_modal`) for these tests. So the verb has to find and
answer a genuine modal inside its nested event loop, which is the case that
matters on the rig. A safety timer closes any box left open, so a broken verb
fails a test instead of hanging the suite.

**What the stand-in does that the product does not** (`CLAUDE.md`): it has no
rip pipeline after the gate. Where a test needs a rip to start (the defect the
verb exists to catch), Start sets `_rip_worker` itself.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from test_uiscript_rip_verbs import _step_outcome, _window

from platterpus.config import Config
from platterpus.parsers.drive_list import DriveDescriptor
from platterpus.ui import message_boxes
from platterpus.ui.main_window_drive import DriveMixin
from platterpus.ui.main_window_rip import RipMixin
from platterpus.uiscript import offset_verbs
from platterpus.uiscript.offset_grading import (
    OFFSET_REFUSAL_TITLE,
    start_blocker,
    unreachable_detail,
)
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner
from platterpus.uiscript.script import parse
from platterpus.user_settings import SettingWrite

pytest.importorskip("PySide6.QtWidgets")

_REPO = Path(__file__).resolve().parent.parent
_SRC = _REPO / "src" / "platterpus"
_ACCEPTANCE = _SRC / "rig_scripts" / "fullacceptance.txt"

#: The rig's drive, and the offset the bundled AccurateRip list holds for it.
_LISTED = DriveDescriptor("/dev/sr0", "PIONEER", "BD-RW BDR-209D", "1.10", None, None)
#: A drive no list carries.
_UNLISTED = DriveDescriptor("/dev/sr0", "NOBODY", "UNKNOWN DRIVE 9", "1.00", None, None)


class _Picker:
    def __init__(self, drive: DriveDescriptor | None) -> None:
        self._drive = drive

    def current_drive(self) -> DriveDescriptor | None:
        return self._drive

    def current_device(self) -> str:
        return self._drive.device if self._drive else ""


class _OffsetDb:
    """The two drives above, as `OffsetDatabase.lookup` answers for them."""

    def lookup(self, vendor: str, model: str) -> int | None:
        return 667 if vendor == "PIONEER" else None


class _Controls:
    """Start, wired the way `MainWindow` wires it: straight into the real gate."""

    def __init__(self, win: Any, *, startable: bool = True) -> None:
        self._win = win
        self._startable = startable
        self.pressed = 0
        self.config_pushed: Config | None = None

    def can_start(self) -> bool:
        return self._startable

    def set_config(self, config: Config) -> None:
        self.config_pushed = config

    def _on_start(self) -> None:
        self.pressed += 1
        # The real slot, on the stand-in: the params are unread before the gate
        # returns on this path, which is the only path these tests drive.
        RipMixin._on_rip_requested(self._win, None)  # type: ignore[arg-type]  # a stand-in window


def _offset_window(drive: DriveDescriptor | None, **overrides: Any) -> Any:
    """A stand-in window with the attributes the verb and the real gate read."""
    win = _window(config=Config(read_offset=667, override_read_offset=True))
    win._drive_picker = _Picker(drive)
    win._offset_db = _OffsetDb()
    win._rip_controls = _Controls(win, startable=overrides.get("startable", True))
    win.setup_opened = 0
    win.writes = []

    def save_user_setting(field: str, value: object) -> SettingWrite:
        win.writes.append((field, value))
        win._config = dataclasses.replace(win._config, **{field: value})
        return SettingWrite(True)

    def set_read_offset_override(value: int) -> bool:
        win.writes.append(("override", value))
        win._config = dataclasses.replace(
            win._config, read_offset=value, override_read_offset=True
        )
        return True

    win._save_user_setting = save_user_setting
    win._set_read_offset_override = set_read_offset_override
    win._auto_apply_known_offset = lambda: DriveMixin._auto_apply_known_offset(win)
    win._on_drive_setup = lambda: setattr(win, "setup_opened", win.setup_opened + 1)
    win._record_drive_fact = lambda *a, **k: None
    return win


@pytest.fixture
def real_warning(monkeypatch: pytest.MonkeyPatch, qapp: QApplication) -> list[str]:
    """`message_boxes.warning` with its real, blocking body; returns titles shown.

    conftest answers every box at once so no test can hang on one. These tests
    need the real modal, so it is restored here, with a 10 s safety timer that
    closes anything still open: a verb that fails to answer then fails its test.
    """
    shown: list[str] = []

    def warning(
        parent: Any, title: str, text: str, buttons: Any = None, default: Any = None
    ) -> Any:
        shown.append(title)
        box = message_boxes.build(
            QMessageBox.Icon.Warning,
            parent,
            title,
            text,
            buttons or QMessageBox.StandardButton.Ok,
            default or QMessageBox.StandardButton.NoButton,
        )
        QTimer.singleShot(10_000, box.reject)
        return message_boxes._run_modal(box)

    monkeypatch.setattr(message_boxes, "warning", warning)
    return shown


def _run(win: Any, qapp: Any, process_until: Any, source: str) -> Any:
    return _step_outcome(ScriptRunner(win), qapp, process_until, source)


# --- The pure half ------------------------------------------------------------


def test_the_unreachable_record_says_why_and_that_nothing_changed() -> None:
    detail = unreachable_detail("PIONEER BD-RW BDR-209D", 667)
    for needed in (
        "PIONEER BD-RW BDR-209D",
        "+667",
        "Nothing was changed",
        "not a pass",
    ):
        assert needed in detail, (needed, detail)


def test_start_blocker_names_each_refusal_rip_makes(qapp: Any) -> None:
    win = _offset_window(_UNLISTED)
    assert start_blocker(win, "") == ""
    assert "Album already ripped" in start_blocker(win, "Album already ripped")
    win._rip_worker = object()
    assert start_blocker(win, "") == "a rip is already running"
    disabled = _offset_window(_UNLISTED, startable=False)
    assert "identify the disc first" in start_blocker(disabled, "")


def test_the_title_the_verb_waits_for_is_the_one_the_gate_raises() -> None:
    """The verb keeps its own copy of the title; this ties the copy to the gate.

    Read from the real method's source, together with the two facts the verb
    rests on: the gate asks `_auto_apply_known_offset` first, and its box has a
    No button (`DECLINE_LABEL`) to decline the wizard with.
    """
    source = inspect.getsource(RipMixin._on_rip_requested)
    gate = source.split("Self-heal a stale", 1)[0]
    assert f'"{OFFSET_REFUSAL_TITLE}"' in gate, "the refusal's title moved"
    assert "_auto_apply_known_offset()" in gate
    assert "QMessageBox.StandardButton.No" in gate


# --- The verb against the real gate ------------------------------------------


def test_on_a_listed_drive_it_records_unreachable_and_touches_nothing(
    qapp: Any, process_until: Any, real_warning: list[str]
) -> None:
    win = _offset_window(_LISTED)
    step = _run(win, qapp, process_until, "expect-offset-refusal")
    assert step.outcome is Outcome.UNREACHABLE, step.detail
    assert "+667" in step.detail and "not a pass" in step.detail
    assert win.writes == [] and win._rip_controls.pressed == 0
    assert real_warning == [], "Start was pressed on a listed drive"
    assert win._config.override_read_offset and win._config.read_offset == 667


def test_on_an_unlisted_drive_the_real_refusal_is_answered_and_the_override_restored(
    qapp: Any, process_until: Any, real_warning: list[str]
) -> None:
    win = _offset_window(_UNLISTED)
    step = _run(win, qapp, process_until, "expect-offset-refusal")
    assert step.outcome is Outcome.PASS, step.detail
    assert real_warning == [OFFSET_REFUSAL_TITLE], "the real gate never refused"
    assert win._rip_controls.pressed == 1
    assert win.setup_opened == 0, "the wizard opened in an unattended run"
    # Off, then back on at the same offset: both halves, in that order.
    assert win.writes == [("override_read_offset", False), ("override", 667)]
    assert win._config.override_read_offset and win._config.read_offset == 667
    assert "put back on at +667" in step.detail


def test_a_rip_that_starts_with_the_override_off_fails_and_is_cancelled(
    qapp: Any, process_until: Any, real_warning: list[str]
) -> None:
    """The defect the verb exists for: no refusal, and a rip at no offset."""
    win = _offset_window(_UNLISTED)

    def start_a_rip() -> None:
        win._rip_controls.pressed += 1
        win._rip_worker = object()

    win._rip_controls._on_start = start_a_rip
    step = _run(win, qapp, process_until, "expect-offset-refusal")
    assert step.outcome is Outcome.FAIL, step.detail
    assert "STARTED" in step.detail
    assert win.cancelled, "the rip the step caused was left running"
    assert win._config.override_read_offset and win._config.read_offset == 667


def test_no_refusal_at_all_fails_when_the_wait_runs_out_and_still_restores(
    qapp: Any, process_until: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(offset_verbs, "OFFSET_REFUSAL_WAIT_S", 0.3)
    win = _offset_window(_UNLISTED)
    win._rip_controls._on_start = lambda: None  # Start does nothing at all
    step = _run(win, qapp, process_until, "expect-offset-refusal")
    assert step.outcome is Outcome.FAIL, step.detail
    assert "no rip started either" in step.detail
    assert win._config.override_read_offset, "the timeout left the override off"


def test_a_run_stopped_mid_wait_puts_the_override_back(
    qapp: Any, process_until: Any
) -> None:
    win = _offset_window(_UNLISTED)
    win._rip_controls._on_start = lambda: None
    runner = ScriptRunner(win)
    runner.start(parse("expect-offset-refusal"))
    assert process_until(lambda: runner._deadline_step is not None)
    assert not win._config.override_read_offset, "the step never turned it off"
    runner.stop("stopped from the console")
    assert win._config.override_read_offset, "a stop left the override off"


def test_a_start_that_cannot_be_pressed_asks_nothing_and_changes_nothing(
    qapp: Any, process_until: Any, real_warning: list[str]
) -> None:
    win = _offset_window(_UNLISTED, startable=False)
    step = _run(win, qapp, process_until, "expect-offset-refusal")
    assert step.outcome is Outcome.FAIL and "identify the disc first" in step.detail
    assert win.writes == [] and real_warning == []


def test_no_drive_selected_is_a_failure_not_a_skip(
    qapp: Any, process_until: Any
) -> None:
    step = _run(_offset_window(None), qapp, process_until, "expect-offset-refusal")
    assert step.outcome is Outcome.FAIL and "no drive is selected" in step.detail


# --- Who may say UNREACHABLE --------------------------------------------------

#: Every module allowed to emit `Outcome.UNREACHABLE`. **A ratchet**: `ok`
#: forgives the outcome, so a new producer is a new way for a run to be ok
#: without checking something, and it has to be argued for here, by name.
_UNREACHABLE_PRODUCERS: frozenset[str] = frozenset({"uiscript/offset_verbs.py"})

#: Modules that only read the outcome (the report defines and renders it).
_UNREACHABLE_READERS: frozenset[str] = frozenset({"uiscript/report.py"})


def test_only_the_named_verbs_may_record_a_step_as_unreachable() -> None:
    found: set[str] = set()
    for path in sorted(_SRC.rglob("*.py")):
        rel = path.relative_to(_SRC).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "UNREACHABLE"
                and isinstance(node.value, ast.Name)
                and node.value.id == "Outcome"
            ):
                found.add(rel)
    producers = found - _UNREACHABLE_READERS
    assert producers, "no producer found: the sweep is reading nothing"
    assert producers == _UNREACHABLE_PRODUCERS, (
        f"modules emitting UNREACHABLE: {sorted(producers)}; allowed: "
        f"{sorted(_UNREACHABLE_PRODUCERS)}. `RunReport.ok` forgives it, so a new "
        "producer must be argued for in this allowlist."
    )


# --- The shipped script -------------------------------------------------------


def test_the_acceptance_script_runs_it_after_the_disc_is_identified() -> None:
    """E2: after E's abort (Start needs an identified disc) and before F's rip,
    followed by the two lines that prove the override came back."""
    lines = [ln.strip() for ln in _ACCEPTANCE.read_text(encoding="utf-8").splitlines()]
    at = lines.index("expect-offset-refusal")
    e_abort = max(
        i
        for i, ln in enumerate(lines[:at])
        if ln.startswith("abort-if-failed the disc")
    )
    first_rip = lines.index("rip")
    assert e_abort < at < first_rip
    following = [ln for ln in lines[at + 1 :] if ln and not ln.startswith("#")][:2]
    assert following == ["expect-drive-offset", "expect override_read_offset on"]
