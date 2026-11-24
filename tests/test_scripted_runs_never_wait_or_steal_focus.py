"""A scripted run never waits on a dialog nobody answers, and never steals focus.

The owner's Full acceptance run of 2026-11-23 (0.7.129) sat 3m29s on a
*"Dependency check complete"* box until they clicked OK, and its dialogs took
focus from whatever they were doing (their word, 2026-11-24: *"they should run
on their own, not need acceptance by a user, and also not interrupt a user with
bringing windows and things to the front"*). The guard, the quiet presentation
and the `open dependencies` wait are `uiscript/unanswered_dialog_guard.py`,
`ui/dialogs/quiet_presentation.py` and `uiscript/dependency_verbs.py`.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Final

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QWidget

from platterpus.ui.dialogs import quiet_presentation as centering
from platterpus.ui.dialogs.auto_center import DialogCenterFilter
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner
from platterpus.uiscript.script import parse
from platterpus.uiscript.unanswered_dialog_guard import UNANSWERED_DIALOG_TIMEOUT_S

_SRC: Final[Path] = Path(__file__).resolve().parents[1] / "src" / "platterpus"


@pytest.fixture(autouse=True)
def _loud_presentation_after(qapp: object) -> Generator[None, None, None]:
    """Every test here leaves windows presenting normally, as it found them."""
    yield
    centering.present_quietly(False)


class _Window(QWidget):
    """A bare window for the runner to drive: the guard reads nothing of it."""


def _runner() -> tuple[ScriptRunner, _Window]:
    window = _Window()
    runner = ScriptRunner(window)
    runner._steps = parse("log one\nlog two")
    runner._index = 1
    runner._report.steps.clear()
    return runner, window


def _box(parent: QWidget, title: str, text: str) -> QMessageBox:
    """An OK-only box, shown modal without blocking, like the one in the run.

    OK-only on purpose: such a box refuses `close()` (no escape button), and the
    guard must still be able to put it away.
    """
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.setWindowModality(Qt.WindowModality.ApplicationModal)
    box.show()
    QApplication.processEvents()
    return box


# --- The guard ---------------------------------------------------------------


def test_a_dialog_nobody_answers_is_cancelled_and_recorded_as_a_fail() -> None:
    runner, window = _runner()
    box = _box(window, "Dependency check complete", "8 installed, 0 need attention.")
    try:
        runner._close_dialog_nobody_answered(now=1000.0)  # starts its clock
        assert box.isVisible()
        runner._close_dialog_nobody_answered(now=1000.0 + UNANSWERED_DIALOG_TIMEOUT_S)
        QApplication.processEvents()
        assert not box.isVisible(), "the run would still be waiting for a person"
        assert box.result() == QDialog.DialogCode.Rejected, (
            "answered with anything but Cancel"
        )
        record = runner._report.steps[-1]
        assert record.outcome is Outcome.FAIL, record
        assert "'Dependency check complete'" in record.detail
        assert "closed it with Cancel" in record.detail
        assert "8 installed, 0 need attention." in record.detail
    finally:
        box.done(0)
        window.deleteLater()


def test_a_dialog_is_given_the_whole_timeout_first() -> None:
    runner, window = _runner()
    box = _box(window, "Album already ripped", "Replace it?")
    try:
        runner._close_dialog_nobody_answered(now=0.0)
        runner._close_dialog_nobody_answered(now=UNANSWERED_DIALOG_TIMEOUT_S - 0.5)
        assert box.isVisible(), "closed before a step had its chance to answer"
        assert not runner._report.steps
    finally:
        box.done(0)
        window.deleteLater()


def test_each_new_dialog_gets_its_own_clock() -> None:
    """A second dialog is not charged the time the first one was up."""
    runner, window = _runner()
    first = _box(window, "First", "one")
    runner._close_dialog_nobody_answered(now=0.0)
    first.done(0)
    QApplication.processEvents()
    second = _box(window, "Second", "two")
    try:
        runner._close_dialog_nobody_answered(now=UNANSWERED_DIALOG_TIMEOUT_S - 1)
        runner._close_dialog_nobody_answered(now=UNANSWERED_DIALOG_TIMEOUT_S + 1)
        assert second.isVisible(), "the second dialog inherited the first's clock"
    finally:
        second.done(0)
        window.deleteLater()


def test_the_guard_runs_on_every_tick_whatever_step_is_waiting() -> None:
    """Called at the top of `_tick`, before any pending wait returns early: in
    the run that made this, a step was waiting the whole time."""
    source = (_SRC / "uiscript" / "runner.py").read_text(encoding="utf-8")
    tick = source[source.index("    def _tick(self) -> None:") :]
    tick = tick[: tick.index("    def _service_deadline")]
    guard_at = tick.index("self._close_dialog_nobody_answered()")
    for early in ("_service_cyanrip()", "_service_deadline()"):
        assert guard_at < tick.index(early), f"the guard runs after {early}"


# --- Quiet presentation ---------------------------------------------------------


class _Raisable:
    def __init__(self) -> None:
        self.raised = 0
        self.activated = 0

    def raise_(self) -> None:
        self.raised += 1

    def activateWindow(self) -> None:
        self.activated += 1


def test_bring_to_front_does_nothing_while_quiet_and_works_otherwise() -> None:
    widget = _Raisable()
    centering.present_quietly(True)
    centering.bring_to_front(widget)  # type: ignore[arg-type]  # a stand-in
    assert (widget.raised, widget.activated) == (0, 0)
    centering.present_quietly(False)
    centering.bring_to_front(widget)  # type: ignore[arg-type]  # a stand-in
    assert (widget.raised, widget.activated) == (1, 1)


@pytest.mark.parametrize("quiet", [True, False])
def test_a_shown_window_is_marked_not_to_take_focus_only_while_quiet(
    quiet: bool,
) -> None:
    centering.present_quietly(quiet)
    app = QApplication.instance()
    assert app is not None
    flt = DialogCenterFilter()
    app.installEventFilter(flt)
    main = QWidget()
    dialog = QDialog(main)
    try:
        main.show()
        dialog.show()
        QApplication.processEvents()
        for window in (main, dialog):
            assert (
                window.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
                is quiet
            ), window
            handle = window.windowHandle()
            assert handle is not None
            assert (
                bool(handle.property(centering.SHOW_WITHOUT_ACTIVATING_PROPERTY))
                is quiet
            ), window
    finally:
        app.removeEventFilter(flt)
        dialog.done(0)
        main.hide()
        main.deleteLater()


def test_a_run_is_quiet_while_it_runs_and_puts_back_what_it_found() -> None:
    runner, window = _runner()
    try:
        assert not centering.presenting_quietly()
        runner.start(parse("log only"))
        assert centering.presenting_quietly(), "a run let its windows take focus"
        while runner.running:
            runner._tick()
        assert not centering.presenting_quietly(), "the run left the app quiet"
        # A `--run-script` launch is quiet before the run, and stays so after.
        centering.present_quietly(True)
        runner.start(parse("log again"))
        runner.stop("ended by the test")
        assert centering.presenting_quietly()
    finally:
        window.deleteLater()


def test_a_scripted_launch_is_quiet_before_its_first_window_shows() -> None:
    source = (_SRC / "app.py").read_text(encoding="utf-8")
    code_show = source.index("\n        window.show()\n")
    assert "present_quietly(" in source
    assert source.index("present_quietly(") < code_show


def test_the_app_asks_for_the_front_in_one_place() -> None:
    """Every raise-and-focus goes through `bring_to_front`, so quiet mode is
    one switch, not one per caller."""
    offenders = []
    for path in (_SRC / "ui").rglob("*.py"):
        if path.name == "quiet_presentation.py":
            continue
        text = path.read_text(encoding="utf-8")
        if ".activateWindow()" in text:
            offenders.append(path.name)
    assert not offenders, f"raise and focus outside bring_to_front: {offenders}"
