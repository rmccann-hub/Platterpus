"""Tests for whipper_gui.workers.rip_worker.

We drive the worker synchronously (no QThread, no event loop) — Qt
signals are callable regardless of whether an event loop is running.
Connected slots receive emissions immediately because we use direct
connections by default. This keeps the tests fast and deterministic.

The WhipperBackend is replaced with a fake so we don't need a real
whipper binary.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pytest
from PySide6.QtWidgets import QApplication

from whipper_gui.adapters.whipper_backend import (
    RipHandle,
    WhipperBackend,
    WhipperError,
)
from whipper_gui.workers.rip_worker import (
    RipParameters,
    RipWorker,
    _parse_progress,
)


# The `qapp` fixture comes from tests/conftest.py. Worker tests don't
# strictly need a QApplication (QCoreApplication would be enough), but
# the UI tests in the same suite do — so we standardize on the wider
# fixture to avoid "QCoreApplication created, can't upgrade" crashes.


# --- Fakes ----------------------------------------------------------------


class _FakeHandle:
    """Implements the RipHandle interface for the worker to consume."""

    def __init__(
        self,
        lines: Iterable[str] = (),
        exit_code: int = 0,
    ) -> None:
        self._lines: list[str] = list(lines)
        self._exit_code: int = exit_code
        self.cancel_calls: int = 0

    def log_lines(self) -> Iterable[str]:
        for line in self._lines:
            yield line

    def wait(self, timeout: float | None = None) -> int:
        return self._exit_code

    def cancel(self, term_timeout: float = 5.0) -> int:
        self.cancel_calls += 1
        return -15


class _FakeBackend(WhipperBackend):
    """Backend whose `rip()` returns a pre-baked _FakeHandle."""

    def __init__(self, handle: _FakeHandle | None = None) -> None:
        self._handle: _FakeHandle | None = handle
        self._raise_on_rip: Exception | None = None
        self.rip_calls: list[dict[str, object]] = []

    def set_handle(self, handle: _FakeHandle) -> None:
        self._handle = handle

    def raise_on_rip(self, exc: Exception) -> None:
        self._raise_on_rip = exc

    # ABC plumbing — not used by the worker tests but required to be a
    # non-abstract subclass.
    def list_drives(self) -> list:  # type: ignore[type-arg]
        return []

    def disc_info(self, drive: str):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    def rip(
        self,
        drive: str,
        release_id: str,
        output_dir: Path,
        track_template: str,
        disc_template: str,
        unknown: bool = False,
    ) -> RipHandle:
        self.rip_calls.append({
            "drive": drive, "release_id": release_id,
            "output_dir": output_dir, "unknown": unknown,
        })
        if self._raise_on_rip:
            raise self._raise_on_rip
        assert self._handle is not None
        return self._handle  # type: ignore[return-value]

    def version(self) -> str:
        return "fake 0.0.0"


def _params(tmp_path: Path, unknown: bool = False) -> RipParameters:
    return RipParameters(
        drive="/dev/sr0",
        release_id="mbid-abc",
        output_dir=tmp_path,
        track_template="t",
        disc_template="d",
        unknown=unknown,
    )


# --- Signal-collector helper ----------------------------------------------


class _Signals:
    """Accumulates signal emissions for assertion."""

    def __init__(self) -> None:
        self.log_lines: list[str] = []
        self.progress: list[tuple[int, float]] = []
        self.errors: list[str] = []
        self.finished: list[tuple[bool, str]] = []

    def attach(self, worker: RipWorker) -> None:
        worker.log_line.connect(self.log_lines.append)
        worker.progress.connect(
            lambda t, p: self.progress.append((t, p))
        )
        worker.error.connect(self.errors.append)
        worker.finished.connect(
            lambda ok, path: self.finished.append((ok, path))
        )


# --- Happy-path tests -----------------------------------------------------


def test_emits_log_lines_in_order(
    qapp: QApplication, tmp_path: Path
) -> None:
    handle = _FakeHandle(lines=["one", "two", "three"], exit_code=0)
    backend = _FakeBackend(handle=handle)
    worker = RipWorker(backend, _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    assert sigs.log_lines == ["one", "two", "three"]
    assert sigs.finished == [(True, "")]
    assert sigs.errors == []


def test_finished_reports_success_on_zero_exit(
    qapp: QApplication, tmp_path: Path
) -> None:
    handle = _FakeHandle(lines=[], exit_code=0)
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    assert sigs.finished[0][0] is True


def test_finished_reports_failure_on_nonzero_exit(
    qapp: QApplication, tmp_path: Path
) -> None:
    handle = _FakeHandle(lines=[], exit_code=1)
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    assert sigs.finished[0][0] is False


# --- Progress parsing -----------------------------------------------------


def test_progress_signal_fires_on_parseable_lines(
    qapp: QApplication, tmp_path: Path
) -> None:
    handle = _FakeHandle(
        lines=[
            "Reading TOC...",
            "Track 1 [###       ] 30%",
            "Track 1 [##########] 100% copy OK",
            "Track 2 [#         ] 5%",
        ],
        exit_code=0,
    )
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    assert sigs.progress == [(1, 30.0), (1, 100.0), (2, 5.0)]
    # log_line still emits for every line including the non-progress one.
    assert sigs.log_lines[0] == "Reading TOC..."


def test_progress_helper_returns_none_for_non_matching_lines() -> None:
    assert _parse_progress("Reading TOC...") is None
    assert _parse_progress("") is None


def test_progress_helper_extracts_fractional_percent() -> None:
    out = _parse_progress("Track 5 ... 42.5%")
    assert out == (5, 42.5)


# --- Error paths ----------------------------------------------------------


def test_whipper_error_on_start_emits_error_and_finished_false(
    qapp: QApplication, tmp_path: Path
) -> None:
    backend = _FakeBackend()
    backend.raise_on_rip(WhipperError("device busy"))
    worker = RipWorker(backend, _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    assert sigs.errors == ["device busy"]
    assert sigs.finished == [(False, "")]


def test_unexpected_exception_on_start_emits_error(
    qapp: QApplication, tmp_path: Path
) -> None:
    backend = _FakeBackend()
    backend.raise_on_rip(RuntimeError("kaboom"))
    worker = RipWorker(backend, _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    assert len(sigs.errors) == 1
    assert "kaboom" in sigs.errors[0]
    assert sigs.finished == [(False, "")]


# --- Cancellation ---------------------------------------------------------


def test_cancel_sets_flag_and_calls_handle_cancel(
    qapp: QApplication, tmp_path: Path
) -> None:
    handle = _FakeHandle(lines=["one", "two"], exit_code=-15)
    backend = _FakeBackend(handle=handle)
    worker = RipWorker(backend, _params(tmp_path))

    # Cancel must be safe before start.
    worker.cancel()
    # cancel() before start() — handle isn't yet set, so handle.cancel
    # is NOT called. The flag is set, though.
    assert handle.cancel_calls == 0

    worker.start_rip()  # but iteration sees the flag set, exits early

    # After start_rip, the handle exists; calling cancel again should
    # forward to it.
    worker.cancel()
    assert handle.cancel_calls == 1


def test_cancellation_makes_finished_report_false(
    qapp: QApplication, tmp_path: Path
) -> None:
    """When the cancel flag is set during iteration, success must be
    False even if the subprocess exits with 0."""
    handle = _FakeHandle(lines=["x"], exit_code=0)
    backend = _FakeBackend(handle=handle)
    worker = RipWorker(backend, _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    # Pre-cancel so the loop's first iteration sees the flag.
    worker.cancel()
    worker.start_rip()

    assert sigs.finished[0][0] is False


# --- Log path discovery ---------------------------------------------------


def test_finished_includes_log_path_when_log_present(
    qapp: QApplication, tmp_path: Path
) -> None:
    rip_log = tmp_path / "Artist" / "Album" / "rip.log"
    rip_log.parent.mkdir(parents=True)
    rip_log.write_text("dummy log content")

    handle = _FakeHandle(lines=[], exit_code=0)
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    success, path = sigs.finished[0]
    assert success is True
    assert path == str(rip_log)


def test_finished_log_path_empty_when_no_log_file(
    qapp: QApplication, tmp_path: Path
) -> None:
    handle = _FakeHandle(lines=[], exit_code=0)
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    _, path = sigs.finished[0]
    assert path == ""
