"""`open dependencies` starts the app's own check off the GUI thread, and waits.

Until 2026-09-28 the script verb named `run_dependency_check`, the synchronous
form of the check kept for tests, so a script's `open dependencies` probed every
tool on the GUI thread and the window showed "Not Responding" for as long as the
ripping container took to answer (CLAUDE.md, *Never block the GUI thread*). The
scripts' `open dependencies` → `screenshot` → `cancel` still found the summary
up, because the freeze held every later step back; the wait is now explicit.

The real-window half, with a held probe and a turning event loop, is
`tests/test_ui_main_window.py::test_open_dependencies_in_a_script_probes_off_the_gui_thread`.
These use a stand-in window, which carries only the three names the handler
reads; `test_every_openable_dialog_names_a_real_method` in `tests/test_uiscript.py`
holds the method name against the real class, and the names read here are held by
`test_the_stand_in_reads_only_names_the_real_window_has` below.
"""

from __future__ import annotations

import ast
import time
from pathlib import Path
from typing import Final

import pytest

pytest.importorskip("PySide6.QtWidgets")

from platterpus.uiscript import verbs  # noqa: E402
from platterpus.uiscript.report import Outcome  # noqa: E402
from platterpus.uiscript.runner import ScriptRunner  # noqa: E402
from platterpus.uiscript.script import parse  # noqa: E402

_SRC: Final[Path] = Path(__file__).resolve().parents[1] / "src" / "platterpus"


@pytest.fixture(autouse=True)
def _an_application_exists(qapp: object) -> None:
    """The runner's timer and `_active_dialog` need a Qt application; without one
    a test here depends on which test the worker happened to run first."""


class _Window:
    """The three names `_open_dependency_check` reads, and nothing else."""

    def __init__(self, *, starts: bool = True) -> None:
        self._dep_check_worker: object | None = None
        self._dep_resolve_deferrals: int = 0
        self._starts = starts
        self.started = 0

    def _on_check_dependencies(self) -> None:
        self.started += 1
        if self._starts:
            self._dep_check_worker = object()

    def run_dependency_check(self, show_summary: bool = True) -> None:
        raise AssertionError("the synchronous check was called from a script")


def _open(window: _Window) -> ScriptRunner:
    runner = ScriptRunner(window)  # type: ignore[arg-type]  # a stand-in, by design
    runner._report.steps.clear()
    runner._execute(parse("open dependencies")[0])
    return runner


def test_the_target_is_the_asynchronous_entry_point() -> None:
    assert verbs.OPENABLE["dependencies"] == "_on_check_dependencies"


def test_the_step_waits_for_the_check_it_started_and_passes_when_it_lands() -> None:
    window = _Window()
    runner = _open(window)
    assert window.started == 1
    assert runner._deadline is not None, "the step did not wait"
    assert not runner._report.steps, "the step recorded before its check landed"
    runner._service_deadline()
    assert runner._deadline is not None and not runner._report.steps
    window._dep_check_worker = None  # landed
    runner._service_deadline()
    assert runner._deadline is None
    record = runner._report.steps[-1]
    assert record.outcome is Outcome.PASS, record
    assert "finished with no dialog left on screen" in record.detail, record.detail


def test_a_newer_check_does_not_hold_the_step_open() -> None:
    """Identity, not presence: ours was replaced, so ours has landed."""
    window = _Window()
    runner = _open(window)
    window._dep_check_worker = object()
    runner._service_deadline()
    assert runner._deadline is None
    assert runner._report.steps[-1].outcome is Outcome.PASS


def test_a_result_held_for_another_dialog_says_so() -> None:
    window = _Window()
    runner = _open(window)
    window._dep_check_worker = None
    window._dep_resolve_deferrals = 1
    runner._service_deadline()
    assert "waiting for another dialog to close" in runner._report.steps[-1].detail


def test_a_check_that_does_not_start_is_an_error_not_a_wait() -> None:
    runner = _open(_Window(starts=False))
    assert runner._deadline is None
    record = runner._report.steps[-1]
    assert record.outcome is Outcome.ERROR, record
    assert "did not start" in record.detail


def test_a_check_that_never_lands_fails_at_its_bound() -> None:
    from platterpus.deps import manager as dep_manager

    window = _Window()
    runner = _open(window)
    # The bound is the check's own deadline plus a grace, never shorter.
    assert runner._deadline is not None
    assert runner._deadline - runner._deadline_started >= dep_manager.CHECK_DEADLINE_S
    runner._deadline = time.monotonic() - 1.0  # the bound has passed
    runner._service_deadline()
    record = runner._report.steps[-1]
    assert record.outcome is Outcome.FAIL, record
    assert "had not finished" in record.detail, record.detail
    assert f"{dep_manager.CHECK_DEADLINE_S:.0f}s deadline" in record.detail


def test_a_run_stopped_mid_wait_records_the_waiting_step() -> None:
    """A waiting step has left the queue, so the stop path must name it itself.

    Before this, a run stopped during any wait (`wait-for-rip`, `answer-dialog`,
    this one) ended with no row for the step that was waiting.
    """
    window = _Window()
    runner = ScriptRunner(window)  # type: ignore[arg-type]  # a stand-in, by design
    runner.start(parse("open dependencies\nlog after"))
    until = time.monotonic() + 5.0
    while runner._deadline is None and time.monotonic() < until:
        runner._tick()
    assert runner._deadline is not None
    runner.stop("stopped by the test")
    rows = [(r.source, r.outcome) for r in runner._report.steps]
    assert ("open dependencies", Outcome.BLOCKED) in rows, rows
    waiting = next(r for r in runner._report.steps if r.source == "open dependencies")
    assert "still waiting" in waiting.detail, waiting.detail
    # NON-TRIVIALITY: the unreached step is still recorded as before.
    assert ("log after", Outcome.BLOCKED) in rows, rows
    assert runner._deadline_step is None


def test_the_stand_in_reads_only_names_the_real_window_has() -> None:
    """A method, or an attribute the window's classes declare (set in `__init__`,
    so absent from the class object itself)."""
    import inspect

    from platterpus.ui.main_window import MainWindow

    declared = {
        name for klass in MainWindow.__mro__ for name in inspect.get_annotations(klass)
    }
    for name in (
        "_on_check_dependencies",
        "_dep_check_worker",
        "_dep_resolve_deferrals",
    ):
        assert hasattr(MainWindow, name) or name in declared, name


def _calls_of_the_synchronous_check() -> list[str]:
    """Every place in the product that reaches `run_dependency_check` itself.

    A call by attribute, or the NAME as a string — `OPENABLE` resolves its
    targets with `getattr`, which is how the script verb reached it.
    """
    found: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        relative = path.relative_to(_SRC).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "run_dependency_check":
                found.append(f"{relative}:{node.lineno}")
            elif (
                isinstance(node, ast.Constant) and node.value == "run_dependency_check"
            ):
                found.append(f"{relative}:{node.lineno} (by name)")
    return found


def test_nothing_in_the_product_reaches_the_synchronous_check() -> None:
    """It is kept for tests; every product path uses the worker-thread form."""
    assert _calls_of_the_synchronous_check() == []
    # NON-TRIVIALITY: the method this sweep looks for still exists, so an empty
    # result is not the product of a rename.
    source = (_SRC / "ui" / "main_window_deps.py").read_text(encoding="utf-8")
    assert "def run_dependency_check(" in source


def test_the_sweep_finds_a_call_and_a_name() -> None:
    tree = ast.parse(
        'w.run_dependency_check()\nOPENABLE = {"d": "run_dependency_check"}'
    )
    attrs = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute)]
    names = [n for n in ast.walk(tree) if isinstance(n, ast.Constant)]
    assert [a.attr for a in attrs] == ["run_dependency_check"]
    assert "run_dependency_check" in [n.value for n in names]
