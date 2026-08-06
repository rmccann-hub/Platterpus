# SPDX-License-Identifier: GPL-3.0-only
r"""The `cyanrip` script verb, which is the one that runs a real subprocess.

**Why this file exists at all.** The verb was written to call ``run_capture``
inline, on the GUI thread, with a 300-second timeout and a docstring arguing the
block was acceptable *here specifically*. That is the exact shape ``CLAUDE.md``
refuses — a comment where a check belongs — and the cost is concrete: an
unattended batch that runs ``cyanrip -x`` against a wedged drive freezes the
window for five minutes, which is indistinguishable from the hang the whole
feature was built to diagnose. It now runs on a daemon thread and the tick polls
it.

**The revert check.** Every test below fails if the work moves back onto the GUI
thread, because each one asserts something only an *asynchronous* implementation
can satisfy: that the first tick returns while the command is still running, and
that a stop mid-flight kills the child rather than waiting for it. An inline
implementation cannot pass `test_the_first_tick_returns_before_the_command_does`
— it would not return until the fake had slept.

**What the stand-in does that the real thing does not** (``CLAUDE.md``): the
fake ``run_capture`` sleeps on an :class:`threading.Event` instead of spawning a
child, so nothing here proves the *kill* reaches a real process. What it does
prove is the runner's half — that a kill is requested, that the step is recorded
once and only once, and that a never-returning command is reported as an
unreapable child rather than stranding the batch. The kill's effect on a real
child is ``KillableCommand``'s own tested behaviour.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from platterpus.uiscript import runner as runner_mod
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.script import parse


@pytest.fixture
def window(qapp: QApplication) -> QWidget:
    """A bare top-level. The `cyanrip` verb never touches the window."""
    del qapp
    return QWidget()


def _steps(text: str) -> list[Any]:
    parsed = parse(text)
    assert all(step.ok for step in parsed), [s.error for s in parsed]
    return parsed


class _FakeCapture:
    """Stands in for `run_capture`, and can be released on demand.

    Records the argv it was handed so a test can assert the *real* arguments
    crossed the seam, not just that something ran.
    """

    def __init__(self, result: tuple[int, str] | None = None) -> None:
        self.released: threading.Event = threading.Event()
        self.entered: threading.Event = threading.Event()
        self.calls: list[list[str]] = []
        self._result: tuple[int, str] = result or (0, "cyanrip 0.9.4-rc1\n")
        self.raise_riperror: str = ""

    def __call__(
        self,
        tool_name: str,
        binary: str,
        args: list[str],
        *,
        timeout: float,
        stdin_devnull: bool = False,
    ) -> tuple[int, str]:
        del tool_name, timeout, stdin_devnull
        self.calls.append([binary, *args])
        self.entered.set()
        # Bounded so a broken test cannot hang the suite; the assertions below
        # all release it explicitly long before this expires.
        self.released.wait(timeout=30.0)
        if self.raise_riperror:
            from platterpus.adapters.rip_backend import RipError

            raise RipError(self.raise_riperror)
        return self._result


@pytest.fixture
def fake_capture(monkeypatch: pytest.MonkeyPatch) -> _FakeCapture:
    fake = _FakeCapture()
    # The verb imports `run_capture` from the adapter INSIDE the function, so
    # patching the attribute on the module is what the call site actually reads.
    monkeypatch.setattr("platterpus.adapters.rip_backend.run_capture", fake)
    return fake


def _pump(run: runner_mod.ScriptRunner, *, until: float = 5.0) -> None:
    """Tick until the runner stops, bounded. Drives the state machine by hand.

    Calling `_tick` directly rather than spinning the Qt timer keeps the test
    deterministic; the tick is the same method the timer invokes.
    """
    deadline = time.monotonic() + until
    while run.running and time.monotonic() < deadline:
        run._tick()
        time.sleep(0.01)


class TestItDoesNotBlockTheGuiThread:
    def test_the_first_tick_returns_before_the_command_does(
        self, window: QWidget, fake_capture: _FakeCapture
    ) -> None:
        """The whole point. An inline implementation cannot pass this."""
        run = runner_mod.ScriptRunner(window)
        run.start(_steps("cyanrip -N --version"))
        started = time.monotonic()
        # Tick until the helper thread is actually inside the fake — proving the
        # command is in flight — and require that each tick was cheap.
        while not fake_capture.entered.is_set():
            tick_started = time.monotonic()
            run._tick()
            assert time.monotonic() - tick_started < 0.5, (
                "a tick blocked while the command was running — the work is back "
                "on the GUI thread"
            )
            assert time.monotonic() - started < 5.0, "the helper thread never ran"
            time.sleep(0.005)
        # In flight, and nothing recorded yet: the step is still open.
        assert run._pending_cyanrip is not None
        assert not run._report.steps
        fake_capture.released.set()
        _pump(run)
        assert [s.outcome for s in run._report.steps] == [Outcome.PASS]

    def test_the_argv_that_crossed_the_seam_is_the_one_asked_for(
        self, window: QWidget, fake_capture: _FakeCapture
    ) -> None:
        # Not a formality: the async rewrite moved the argv construction and the
        # call into different scopes, which is exactly where an argument gets
        # dropped. `-N` is mandatory (the sanitiser refuses without it).
        run = runner_mod.ScriptRunner(window)
        run.start(_steps("cyanrip -N --version"))
        fake_capture.released.set()
        _pump(run)
        assert len(fake_capture.calls) == 1
        assert fake_capture.calls[0][1:] == ["-N", "--version"]

    def test_the_step_is_recorded_exactly_once(
        self, window: QWidget, fake_capture: _FakeCapture
    ) -> None:
        # A poll loop's classic defect: recording on every tick after completion.
        run = runner_mod.ScriptRunner(window)
        run.start(_steps("cyanrip -N --version\nlog done"))
        fake_capture.released.set()
        _pump(run)
        cyanrip_records = [s for s in run._report.steps if "cyanrip" in s.source]
        assert len(cyanrip_records) == 1

    def test_the_output_and_exit_code_reach_the_transcript(
        self, window: QWidget, fake_capture: _FakeCapture
    ) -> None:
        fake_capture._result = (3, "Ripping errors: 1\n")
        run = runner_mod.ScriptRunner(window)
        run.start(_steps("cyanrip -N --version"))
        fake_capture.released.set()
        _pump(run)
        detail = run._report.steps[0].detail
        assert "exit: 3" in detail
        assert "Ripping errors: 1" in detail
        assert "argv:" in detail


class TestFailurePaths:
    def test_a_riperror_records_a_null_exit_not_a_zero(
        self, window: QWidget, fake_capture: _FakeCapture
    ) -> None:
        """Tri-state: a child that was never reaped has no exit code."""
        fake_capture.raise_riperror = "cyanrip: no such binary"
        run = runner_mod.ScriptRunner(window)
        run.start(_steps("cyanrip -N --version"))
        fake_capture.released.set()
        _pump(run)
        record = run._report.steps[0]
        assert record.outcome is Outcome.ERROR
        assert "exit: null" in record.detail
        assert "no such binary" in record.detail
        assert "exit: 0" not in record.detail

    def test_an_unexpected_exception_in_the_helper_is_reported_not_swallowed(
        self, window: QWidget, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A helper thread that dies silently is a batch that hangs."""

        def boom(*_a: object, **_k: object) -> tuple[int, str]:
            raise ValueError("something the adapter never promised")

        monkeypatch.setattr("platterpus.adapters.rip_backend.run_capture", boom)
        run = runner_mod.ScriptRunner(window)
        run.start(_steps("cyanrip -N --version"))
        _pump(run)
        record = run._report.steps[0]
        assert record.outcome is Outcome.ERROR
        assert "ValueError" in record.detail

    def test_a_command_that_never_returns_is_reported_as_unreapable(
        self,
        window: QWidget,
        fake_capture: _FakeCapture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The grace path: `run_capture`'s own timeout failed to end the child.

        Shrunk to milliseconds rather than the shipped 320 s — the *behaviour*
        under test is what the runner does when the deadline passes, and a test
        that waited the real duration would never be run.
        """
        killed: list[bool] = []
        monkeypatch.setattr(runner_mod, "CYANRIP_VERB_TIMEOUT_S", 0.05)
        monkeypatch.setattr(runner_mod, "CYANRIP_VERB_GRACE_S", 0.05)
        monkeypatch.setattr(
            "platterpus.adapters.rip_backend.cancel_info_probe",
            lambda: killed.append(True),
        )
        run = runner_mod.ScriptRunner(window)
        run.start(_steps("cyanrip -N --version"))
        _pump(run, until=5.0)
        record = run._report.steps[0]
        assert record.outcome is Outcome.ERROR
        assert "unreapable" in record.detail
        assert "exit: null" in record.detail
        assert killed == [True], "the runner gave up without asking for a kill"
        # And the batch is over rather than stranded.
        assert not run.running
        fake_capture.released.set()


class TestStopWhileInFlight:
    def test_stopping_kills_the_child_and_records_the_open_step(
        self,
        window: QWidget,
        fake_capture: _FakeCapture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`stop()` must not silently drop a running command.

        A cancel that only forgets is the false promise ``CLAUDE.md`` names by
        that phrase; and a transcript missing the step that was running when the
        user hit Stop reads as a batch that never reached it.
        """
        killed: list[bool] = []
        monkeypatch.setattr(
            "platterpus.adapters.rip_backend.cancel_info_probe",
            lambda: killed.append(True),
        )
        run = runner_mod.ScriptRunner(window)
        run.start(_steps("cyanrip -N --version\nlog never reached"))
        while not fake_capture.entered.is_set():
            run._tick()
            time.sleep(0.005)
        run.stop("stopped by the user")
        assert killed == [True], "stop() did not kill the in-flight child"
        outcomes = [s.outcome for s in run._report.steps]
        # The open command is an ERROR; the step after it is SKIPPED, not passed.
        assert outcomes == [Outcome.ERROR, Outcome.SKIPPED]
        assert "still running" in run._report.steps[0].detail
        assert run._report.ended_reason
        fake_capture.released.set()

    def test_a_second_run_does_not_inherit_the_first_ones_pending_job(
        self, window: QWidget, fake_capture: _FakeCapture
    ) -> None:
        # New state the fix created: a field that survives between runs. If
        # `start()` forgot to clear it, the next run would service a corpse.
        run = runner_mod.ScriptRunner(window)
        run.start(_steps("cyanrip -N --version"))
        while not fake_capture.entered.is_set():
            run._tick()
            time.sleep(0.005)
        run.stop()
        assert run._pending_cyanrip is None
        fake_capture.released.set()
        run.start(_steps("log second run"))
        assert run._pending_cyanrip is None
        _pump(run)
        assert [s.outcome for s in run._report.steps] == [Outcome.PASS]
