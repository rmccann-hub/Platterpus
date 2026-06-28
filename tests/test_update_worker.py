"""Tests for platterpus.workers.update_worker.

Both workers are QObjects driven synchronously (no real QThread/event
loop) — same approach as test_mb_worker. The network/install layer is
monkeypatched, so nothing here touches GitHub or the filesystem install.
"""

from __future__ import annotations

from typing import Any

import pytest
from PySide6.QtWidgets import QApplication

from platterpus import update_install as install_module
from platterpus.workers import update_worker
from platterpus.workers.update_worker import UpdateCheckWorker, UpdateInstallWorker

# `qapp` fixture comes from tests/conftest.py (workers need a QApplication
# for their signals), same as the other worker tests.


# --- UpdateCheckWorker ----------------------------------------------------


def test_check_worker_emits_release_info(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    sentinel = object()  # stands in for a ReleaseInfo
    monkeypatch.setattr(update_worker, "latest_release", lambda: sentinel)
    worker = UpdateCheckWorker()
    got: list[object] = []
    worker.finished.connect(got.append)

    worker.run()

    assert got == [sentinel]


def test_check_worker_emits_none_on_crash(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A worker must always finish — a lookup that raises becomes None,
    not an unhandled exception that strands the thread."""

    def boom() -> object:
        raise RuntimeError("network exploded")

    monkeypatch.setattr(update_worker, "latest_release", boom)
    worker = UpdateCheckWorker()
    got: list[object] = []
    worker.finished.connect(got.append)

    worker.run()

    assert got == [None]


# --- UpdateInstallWorker --------------------------------------------------


class _InstallSignals:
    def __init__(self) -> None:
        self.progress: list[float] = []
        self.status: list[str] = []
        self.finished: list[tuple[bool, str]] = []

    def attach(self, worker: UpdateInstallWorker) -> None:
        worker.progress.connect(self.progress.append)
        worker.status.connect(self.status.append)
        worker.finished.connect(lambda ok, payload: self.finished.append((ok, payload)))


def test_install_worker_forwards_progress_status_and_success(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The worker must wire the download's progress/status callbacks to its
    own signals and report the installed path on success."""

    def fake_install(version: str, **kwargs: Any) -> str:
        # Exercise the callbacks the worker passes in.
        kwargs["progress"](50.0)
        kwargs["status"]("Verifying the download…")
        kwargs["progress"](100.0)
        assert kwargs["cancelled"]() is False  # not cancelled
        return f"/home/u/Applications/platterpus-{version}.AppImage"

    monkeypatch.setattr(install_module, "download_and_install", fake_install)
    worker = UpdateInstallWorker("0.2.6")
    sigs = _InstallSignals()
    sigs.attach(worker)

    worker.run()

    assert sigs.progress == [50.0, 100.0]
    assert sigs.status == ["Verifying the download…"]
    assert sigs.finished == [(True, "/home/u/Applications/platterpus-0.2.6.AppImage")]


def test_install_worker_reports_install_error_as_failure(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_install(version: str, **kwargs: Any) -> str:
        raise install_module.UpdateInstallError("checksum mismatch")

    monkeypatch.setattr(install_module, "download_and_install", fake_install)
    worker = UpdateInstallWorker("0.2.6")
    sigs = _InstallSignals()
    sigs.attach(worker)

    worker.run()

    assert sigs.finished == [(False, "checksum mismatch")]


def test_install_worker_wraps_unexpected_error(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-UpdateInstallError must still finish cleanly (False, message)
    rather than crash the worker thread."""

    def fake_install(version: str, **kwargs: Any) -> str:
        raise ValueError("something weird")

    monkeypatch.setattr(install_module, "download_and_install", fake_install)
    worker = UpdateInstallWorker("0.2.6")
    sigs = _InstallSignals()
    sigs.attach(worker)

    worker.run()

    assert len(sigs.finished) == 1
    ok, message = sigs.finished[0]
    assert ok is False
    assert "unexpected error" in message
    assert "something weird" in message


def test_install_worker_cancel_flag_is_observed(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cancel() must flip the flag the download polls between chunks."""
    observed: list[bool] = []

    def fake_install(version: str, **kwargs: Any) -> str:
        observed.append(kwargs["cancelled"]())
        return "/x/platterpus.AppImage"

    monkeypatch.setattr(install_module, "download_and_install", fake_install)
    worker = UpdateInstallWorker("0.2.6")
    worker.cancel()  # user hit Cancel before the worker ran
    worker.finished.connect(lambda *_: None)

    worker.run()

    assert observed == [True]
