"""Tests for platterpus.workers.start_worker_thread (the shared lifecycle)."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QApplication

from platterpus.workers import start_worker_thread


class _Worker(QObject):
    finished = Signal()


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
