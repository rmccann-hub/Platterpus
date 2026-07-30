"""Tests for platterpus.workers.dependency_worker.

Driven synchronously (call `run()` directly) — same approach as the other
worker tests. The DependencyManager is a fake; nothing shells out.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from platterpus.workers.dependency_worker import DependencyCheckWorker

# `qapp` fixture comes from tests/conftest.py (the worker's signals need a
# QApplication), as in the other worker tests.


class _FakeManager:
    """Stands in for DependencyManager — only `check_all()` is exercised."""

    def __init__(self, report: object = None, raises: Exception | None = None) -> None:
        self._report = report
        self._raises = raises

    def check_all(self, cancelled: object = None) -> object:
        """Mirrors the real signature, INCLUDING the `cancelled` callback.

        A fake whose signature has drifted from the real one is the §5.t hazard in
        its smallest form: it does not make the product look safer, it makes the
        test fail for a reason unrelated to the product. Accepting and ignoring the
        kwarg is right here — the cancel behaviour has its own tests against the
        real manager, and this fake exists only to hand back a canned report.
        """
        self.cancelled_callback = cancelled
        if self._raises is not None:
            raise self._raises
        return self._report


def test_worker_emits_the_probe_report(qapp: QApplication) -> None:
    sentinel = object()  # stands in for a DependencyReport
    worker = DependencyCheckWorker(_FakeManager(report=sentinel))
    got: list[object] = []
    worker.finished.connect(got.append)

    worker.run()

    assert got == [sentinel]


def test_worker_emits_none_when_probe_crashes(qapp: QApplication) -> None:
    """A worker must always finish — a probe that raises becomes None, not an
    unhandled exception that strands the thread."""
    worker = DependencyCheckWorker(_FakeManager(raises=RuntimeError("probe boom")))
    got: list[object] = []
    worker.finished.connect(got.append)

    worker.run()

    assert got == [None]
