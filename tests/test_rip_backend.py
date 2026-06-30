"""Tests for the backend-neutral pieces in platterpus.adapters.rip_backend.

The concrete backend (cyanrip) has its own suite in test_cyanrip_backend.py;
this file covers the shared plumbing every backend depends on: the RipHandle
process wrapper (log streaming + group-signalling cancel), the RipError /
run_capture subprocess helper, and the ABC's abstract-method discipline.
"""

from __future__ import annotations

import signal
import subprocess
from typing import Any

import pytest

from platterpus.adapters import rip_backend
from platterpus.adapters.rip_backend import (
    RipBackend,
    RipError,
    RipHandle,
    run_capture,
)


class _FakePopen:
    """Stand-in for subprocess.Popen suitable for unit testing."""

    def __init__(self, argv: list[str], *args: Any, **kwargs: Any) -> None:
        self.argv: list[str] = argv
        self.stdout = iter(())  # type: ignore[assignment]
        self.returncode: int | None = None
        self.pid: int = 424242  # cancel paths address the process GROUP
        _FakePopen.last = self  # type: ignore[attr-defined]

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


# --- RipHandle -------------------------------------------------------------


def test_rip_handle_yields_log_lines() -> None:
    fake = _FakePopen(argv=[])
    fake.stdout = iter(["one\n", "two\n", "three\n"])  # type: ignore[assignment]
    handle = RipHandle(process=fake)  # type: ignore[arg-type]

    assert list(handle.log_lines()) == ["one", "two", "three"]


def test_rip_handle_cancel_signals_group_terminate_then_kill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancel must SIGTERM then (on timeout) SIGKILL the process GROUP, so the
    in-tree reader — not just the parent — dies and the drive stops."""
    sent: list[int] = []
    monkeypatch.setattr(rip_backend.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(rip_backend.os, "killpg", lambda pgid, sig: sent.append(sig))

    class _SlowFakePopen(_FakePopen):
        def wait(self, timeout: float | None = None) -> int:
            if signal.SIGKILL not in sent:  # SIGTERM didn't take → time out
                raise subprocess.TimeoutExpired(cmd="cyanrip", timeout=5)
            self.returncode = -9
            return -9

    fake = _SlowFakePopen(argv=[])
    handle = RipHandle(process=fake)  # type: ignore[arg-type]

    code = handle.cancel(term_timeout=0.01)

    assert sent == [signal.SIGTERM, signal.SIGKILL]
    assert code == -9


def test_rip_handle_cancel_on_already_exited_process_is_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    killed: list[int] = []
    monkeypatch.setattr(rip_backend.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(rip_backend.os, "killpg", lambda pgid, sig: killed.append(sig))
    fake = _FakePopen(argv=[])
    fake.returncode = 0
    handle = RipHandle(process=fake)  # type: ignore[arg-type]

    assert handle.cancel() == 0
    assert killed == []  # nothing signalled — it had already exited


def test_rip_handle_returncode_passthrough() -> None:
    fake = _FakePopen(argv=[])
    fake.returncode = 7
    handle = RipHandle(process=fake)  # type: ignore[arg-type]
    assert handle.returncode == 7


# --- run_capture -----------------------------------------------------------


def test_run_capture_returns_rc_and_combined_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    monkeypatch.setattr(
        rip_backend.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout="out\n", stderr="err\n"),
    )
    rc, combined = run_capture("cyanrip", "/x/cyanrip", ["-V"], timeout=5)
    assert rc == 0
    assert combined == "out\nerr\n"


def test_run_capture_missing_binary_raises_riperror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*a: Any, **k: Any) -> Any:
        raise FileNotFoundError("nope")

    monkeypatch.setattr(rip_backend.subprocess, "run", _boom)
    with pytest.raises(RipError) as info:
        run_capture("cyanrip", "/x/cyanrip", ["-V"], timeout=5)
    assert "binary not found" in str(info.value)


def test_run_capture_timeout_raises_riperror(monkeypatch: pytest.MonkeyPatch) -> None:
    def _timeout(*a: Any, **k: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd="cyanrip", timeout=5)

    monkeypatch.setattr(rip_backend.subprocess, "run", _timeout)
    with pytest.raises(RipError) as info:
        run_capture("cyanrip", "/x/cyanrip", ["-V"], timeout=5)
    assert "timed out" in str(info.value)


# --- ABC discipline --------------------------------------------------------


def test_abstract_methods_block_instantiation() -> None:
    """RipBackend itself must not be instantiable."""
    with pytest.raises(TypeError):
        RipBackend()  # type: ignore[abstract]


def test_optional_capability_defaults() -> None:
    """A minimal concrete backend inherits the safe capability defaults."""

    class _Minimal(RipBackend):
        def list_drives(self):  # type: ignore[no-untyped-def]
            return []

        def disc_info(self, drive: str):  # type: ignore[no-untyped-def]
            raise NotImplementedError

        def rip(self, *a: Any, **k: Any) -> Any:
            raise NotImplementedError

        def version(self) -> str:
            return "x"

    backend = _Minimal()
    assert backend.self_verifies_encode() is False
    assert backend.produces_max_compression_flac() is False
    assert backend.native_output_formats() == frozenset({"flac"})
    # Calibration hooks default to "not supported".
    with pytest.raises(NotImplementedError):
        backend.analyze_drive("/dev/sr0")
    with pytest.raises(NotImplementedError):
        backend.find_offset("/dev/sr0")
    backend.cancel_setup()  # no-op, must not raise
