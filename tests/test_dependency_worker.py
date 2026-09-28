"""Tests for platterpus.workers.dependency_worker.

Driven synchronously (call `run()` directly) — same approach as the other
worker tests. The DependencyManager is a fake; nothing shells out.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from platterpus.workers.dependency_worker import DependencyCheckWorker

# `qapp` fixture comes from tests/conftest.py (the worker's signals need a
# QApplication), as in the other worker tests.


class _FakeManager:
    """Stands in for DependencyManager — only `check_all()` is exercised."""

    def __init__(self, report: object = None, raises: Exception | None = None) -> None:
        self._report = report
        self._raises = raises

    def check_all(self, cancelled: object = None, deadline_s: object = None) -> object:
        """Mirrors the real signature, INCLUDING `cancelled` and `deadline_s`.

        A fake whose signature has drifted from the real one is the §5.t hazard in
        its smallest form: it does not make the product look safer, it makes the
        test fail for a reason unrelated to the product. Accepting and ignoring the
        kwarg is right here — the cancel behaviour has its own tests against the
        real manager, and this fake exists only to hand back a canned report.
        """
        self.cancelled_callback = cancelled
        self.deadline_s = deadline_s
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


def test_worker_bounds_the_whole_check_with_the_deadline_read_at_run_time(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The worker hands `check_all` the overall deadline, read when it RUNS.

    Read at run time rather than bound at import, because it is the number that
    decides how long a user waits for any answer at all — and a binding taken at
    import would make the monkeypatched value in every other deadline test a lie.
    """
    from platterpus.deps import manager as dep_manager

    monkeypatch.setattr(dep_manager, "CHECK_DEADLINE_S", 7.5)
    fake = _FakeManager(report=object())
    DependencyCheckWorker(fake).run()
    assert fake.deadline_s == 7.5


def test_worker_emits_a_report_its_deadline_stopped(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deadline-stopped check is ANNOUNCED, unlike a shutdown cancel.

    The user is waiting for exactly this answer. Suppressing it — the way a
    cancelled check is suppressed — would be the "nothing happens" report
    reproduced by the fix meant to end it. Real manager, real sleeping child.
    """
    from platterpus.deps import manager as dep_manager
    from platterpus.deps.checks import check_cyanrip
    from platterpus.deps.manager import DependencyManager, DependencyReport
    from platterpus.deps.registry import DependencySpec, Tier

    tool = tmp_path / "cyanrip"
    tool.write_text("#!/bin/sh\nexec sleep 20\n", encoding="utf-8")
    tool.chmod(0o755)
    spec = DependencySpec(
        dep_id="cyanrip",
        display_name="cyanrip",
        probe=lambda: check_cyanrip(tool),
        min_version=(0, 0, 0),
        tier=Tier.MANUAL,
        install_command=None,
        search_string="x",
    )
    monkeypatch.setattr(dep_manager, "CHECK_DEADLINE_S", 0.4)
    worker = DependencyCheckWorker(DependencyManager(specs=[spec]))
    got: list[object] = []
    worker.finished.connect(got.append)

    started = time.monotonic()
    worker.run()

    assert time.monotonic() - started < 8.0, "the deadline did not stop the probe"
    assert len(got) == 1, "a deadline-stopped check was not announced"
    report = got[0]
    assert isinstance(report, DependencyReport)
    assert [s.dep_id for s in report.unchecked] == ["cyanrip"]
    assert report.missing == [], "a probe the deadline killed was called missing"
