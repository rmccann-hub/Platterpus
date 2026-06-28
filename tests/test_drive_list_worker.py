"""Tests for platterpus.workers.drive_list_worker.

Driven synchronously (call `run()` directly), with a fake backend standing in
for the real `list_drives()` (which would shell into the container).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QApplication

from platterpus.adapters.whipper_backend import (
    RipHandle,
    WhipperBackend,
    WhipperError,
)
from platterpus.parsers.drive_list import DriveDescriptor
from platterpus.workers.drive_list_worker import DriveListWorker

# `qapp` fixture from tests/conftest.py — the worker's signals need a QApplication.


class _Backend(WhipperBackend):
    def __init__(
        self,
        drives: list[DriveDescriptor] | None = None,
        exc: Exception | None = None,
    ) -> None:
        self._drives = drives if drives is not None else []
        self._exc = exc

    def list_drives(self) -> list[DriveDescriptor]:
        if self._exc is not None:
            raise self._exc
        return self._drives

    def disc_info(self, drive: str) -> Any:  # pragma: no cover
        raise NotImplementedError

    def rip(self, **kwargs: Any) -> RipHandle:  # pragma: no cover
        raise NotImplementedError

    def version(self) -> str:
        return "fake 0.0.0"


def _drive() -> DriveDescriptor:
    return DriveDescriptor(device="/dev/sr0", vendor="ACME", model="CD", release="1")


def test_worker_emits_the_drive_list(qapp: QApplication) -> None:
    drives = [_drive()]
    worker = DriveListWorker(_Backend(drives=drives))
    got: list[object] = []
    worker.finished.connect(got.append)

    worker.run()

    assert got == [drives]


def test_worker_routes_whipper_error_to_failed(qapp: QApplication) -> None:
    worker = DriveListWorker(_Backend(exc=WhipperError("no whipper")))
    failed: list[str] = []
    worker.failed.connect(failed.append)

    worker.run()

    assert failed == ["no whipper"]


def test_worker_wraps_unexpected_error(qapp: QApplication) -> None:
    worker = DriveListWorker(_Backend(exc=ValueError("weird parse")))
    failed: list[str] = []
    worker.failed.connect(failed.append)

    worker.run()

    assert len(failed) == 1 and "weird parse" in failed[0]
