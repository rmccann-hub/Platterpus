"""Tests for platterpus.workers.disc_info_worker.

Driven synchronously (call `run()` directly) like the other worker tests; a
fake backend stands in for the real `disc_info()` (which would shell into the
container).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QApplication

from platterpus.adapters.rip_backend import (
    DiscInfo,
    RipBackend,
    RipError,
    RipHandle,
)
from platterpus.parsers.drive_list import DriveDescriptor
from platterpus.workers.disc_info_worker import DiscInfoWorker

# `qapp` fixture comes from tests/conftest.py (the worker's signals need a
# QApplication), as in the other worker tests.


class _Backend(RipBackend):
    """Minimal backend whose disc_info returns a fixed DiscInfo or raises."""

    def __init__(
        self, info: DiscInfo | None = None, exc: Exception | None = None
    ) -> None:
        self._info = info if info is not None else DiscInfo()
        self._exc = exc

    def list_drives(self) -> list[DriveDescriptor]:
        return []

    def disc_info(self, drive: str) -> DiscInfo:
        if self._exc is not None:
            raise self._exc
        return self._info

    def rip(self, **kwargs: Any) -> RipHandle:  # pragma: no cover
        raise NotImplementedError

    def version(self) -> str:
        return "fake 0.0.0"


def test_worker_emits_finished_with_disc_info(qapp: QApplication) -> None:
    info = DiscInfo(num_tracks=5, musicbrainz_disc_id="mb-id")
    worker = DiscInfoWorker(_Backend(info=info), "/dev/sr0")
    got: list[tuple[str, object]] = []
    worker.finished.connect(lambda device, di: got.append((device, di)))

    worker.run()

    assert got == [("/dev/sr0", info)]


def test_worker_routes_whipper_error_to_failed(qapp: QApplication) -> None:
    worker = DiscInfoWorker(_Backend(exc=RipError("no disc")), "/dev/sr0")
    failed: list[tuple[str, str]] = []
    worker.failed.connect(lambda device, msg: failed.append((device, msg)))

    worker.run()

    assert failed == [("/dev/sr0", "no disc")]


def test_worker_wraps_unexpected_error(qapp: QApplication) -> None:
    """A non-RipError must still finish via `failed`, not crash the thread."""
    worker = DiscInfoWorker(_Backend(exc=ValueError("weird")), "/dev/sr0")
    failed: list[tuple[str, str]] = []
    worker.failed.connect(lambda device, msg: failed.append((device, msg)))

    worker.run()

    assert len(failed) == 1
    device, message = failed[0]
    assert device == "/dev/sr0"
    assert "weird" in message
