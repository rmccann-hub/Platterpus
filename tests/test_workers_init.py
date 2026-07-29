"""Tests for platterpus.workers.start_worker_thread (the shared lifecycle)."""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QApplication

from platterpus import workers
from platterpus.workers import start_worker_thread, stop_thread


class _Worker(QObject):
    finished = Signal()


class _FakeThread:
    """Duck-typed QThread for stop_thread unit tests (no real thread needed)."""

    def __init__(self, *, running: bool, stops: bool) -> None:
        self._running = running
        self._stops = stops  # does wait() succeed (thread stopped) in time?
        self.quit_calls = 0
        self.wait_calls: list[int] = []
        self.parent_cleared = False

    def isRunning(self) -> bool:  # noqa: N802 — Qt API name
        return self._running

    def quit(self) -> None:
        self.quit_calls += 1

    def wait(self, ms: int) -> bool:
        self.wait_calls.append(ms)
        return self._stops

    def objectName(self) -> str:  # noqa: N802 — Qt API name
        return "FakeThread"

    def setParent(self, parent: object) -> None:  # noqa: N802 — Qt API name
        self.parent_cleared = parent is None


def test_stop_thread_none_is_a_noop() -> None:
    stop_thread(None)  # must not raise


def test_stop_thread_cancels_worker_and_returns_when_thread_stops() -> None:
    """A thread that stops within the wait is joined, not abandoned; the worker's
    cancel() is called first."""
    cancelled: list[bool] = []
    worker = type("W", (), {"cancel": lambda self: cancelled.append(True)})()
    thread = _FakeThread(running=True, stops=True)

    stop_thread(thread, worker, wait_ms=10)

    assert cancelled == [True]
    assert thread.quit_calls == 1
    assert thread.wait_calls == [10]
    assert not thread.parent_cleared  # stopped cleanly → not abandoned


def test_stop_thread_abandons_a_stuck_thread_instead_of_blocking() -> None:
    """Regression: a thread still running after the brief wait (a step in flight
    quit() can't interrupt) is DETACHED — never blocked-on longer, never
    destroyed while running."""
    thread = _FakeThread(running=True, stops=False)
    before = len(workers._abandoned_threads)

    stop_thread(thread, wait_ms=5)

    assert thread.parent_cleared  # reparented to None
    assert thread in workers._abandoned_threads  # held so the GC can't kill it
    assert len(workers._abandoned_threads) == before + 1


def test_stop_thread_skips_wait_for_an_already_stopped_thread() -> None:
    thread = _FakeThread(running=False, stops=True)
    stop_thread(thread)
    assert thread.quit_calls == 0
    assert thread.wait_calls == []


def test_names_the_thread_after_the_worker_class(
    qapp: QApplication, process_until
) -> None:
    """The thread is named after the worker class so logs / crash backtraces
    identify which background job is running (observability)."""
    worker = _Worker()
    thread = QThread()

    def on_started() -> None:
        worker.finished.emit()  # finish immediately → clean teardown

    start_worker_thread(worker, thread, on_started)
    # Naming is set synchronously, before the thread starts.
    assert thread.objectName() == "_Worker"

    # And the standard lifecycle still tears the thread down.
    assert process_until(lambda: not thread.isRunning())


def test_extra_quit_signal_also_stops_the_thread(
    qapp: QApplication, process_until
) -> None:
    """`also_quit_on` lets a worker that reports failure on a separate signal
    still stop its thread."""

    class _FailingWorker(QObject):
        finished = Signal()
        failed = Signal()

    worker = _FailingWorker()
    thread = QThread()

    def on_started() -> None:
        worker.failed.emit()  # only the failure signal fires

    start_worker_thread(worker, thread, on_started, also_quit_on=[worker.failed])

    assert process_until(lambda: not thread.isRunning())


# --- Shared shutdown budget ---------------------------------------------------
# The crash brief advised raising the per-worker stop timeout to 10 s. That would
# be wrong here: `MainWindow.closeEvent` makes six `stop_thread` calls, so a 10 s
# wait each is up to a 60 s frozen window on close — the failure this project
# guards hardest against. The budget is shared instead, and these pin that.


def test_the_shutdown_budget_is_shared_not_per_worker() -> None:
    """A deadline hands out the REMAINING time, so N workers can't cost N × T."""
    from platterpus.workers import ShutdownDeadline

    deadline = ShutdownDeadline(budget_ms=500)
    first = deadline.remaining_ms()
    assert 0 < first <= 500

    # Spend some of it, as a slow worker would.
    time.sleep(0.2)
    second = deadline.remaining_ms()
    assert second < first, (
        f"the deadline did not shrink ({first} → {second}); every worker would "
        "get the full budget and close could freeze for the sum of them"
    )
    assert second <= 300


def test_an_exhausted_budget_reports_zero_not_a_negative_wait() -> None:
    """QThread.wait() must never be handed a negative number.

    Qt treats a negative wait as "wait forever", so an overrun budget that
    returned -1 would freeze the window indefinitely — the exact opposite of the
    intent. Zero is correct: wait(0) still truthfully reports whether the thread
    already finished.
    """
    from platterpus.workers import ShutdownDeadline

    deadline = ShutdownDeadline(budget_ms=0)
    time.sleep(0.01)
    assert deadline.remaining_ms() == 0


def test_stop_thread_prefers_the_shared_deadline_over_a_per_call_wait() -> None:
    """When both are given the deadline wins — it is the stronger guarantee."""
    from platterpus.workers import ShutdownDeadline, stop_thread

    waits: list[int] = []

    class _RecordingThread:
        def isRunning(self) -> bool:
            return True

        def quit(self) -> None:
            pass

        def wait(self, ms: int) -> bool:
            waits.append(ms)
            return True  # "stopped", so nothing is abandoned

        def objectName(self) -> str:
            return "recorder"

    deadline = ShutdownDeadline(budget_ms=250)
    stop_thread(_RecordingThread(), None, wait_ms=99_999, deadline=deadline)  # type: ignore[arg-type]  # a minimal stand-in, not a real QThread
    assert waits and waits[0] <= 250, (
        f"stop_thread waited {waits} — it used the per-call wait_ms instead of "
        "the shared budget, so a long-running close could still freeze"
    )
