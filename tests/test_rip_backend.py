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


def test_rip_handle_cancel_gives_up_instead_of_waiting_forever_after_sigkill(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Regression: `cancel()` used to end with a bare, unbounded `wait()`.

    SIGKILL is unblockable *unless* the target is in uninterruptible sleep — which
    is exactly where a reader wedged in a drive ioctl sits, and this project has met
    wedged drives on real hardware more than once. In that state the old final
    `self._process.wait()` blocks forever, on the rip worker's thread, which then
    never finishes and gets abandoned at shutdown.

    So the post-SIGKILL wait is bounded too, and an unreapable process returns
    `None` — a value the caller can log and route around.
    """
    sent: list[int] = []
    monkeypatch.setattr(rip_backend.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(rip_backend.os, "killpg", lambda pgid, sig: sent.append(sig))

    class _UnreapableFakePopen(_FakePopen):
        """Never reaped, no matter what is sent — a `D`-state process."""

        def wait(self, timeout: float | None = None) -> int:
            assert timeout is not None, (
                "cancel() waited with NO timeout after SIGKILL — that is the hang. "
                "A D-state process is never reaped and this blocks forever."
            )
            raise subprocess.TimeoutExpired(cmd="cyanrip", timeout=timeout)

    handle = RipHandle(process=_UnreapableFakePopen(argv=[]))  # type: ignore[arg-type]

    with caplog.at_level("ERROR"):
        code = handle.cancel(term_timeout=0.01, kill_timeout=0.01)

    # It escalated all the way, then gave up rather than blocking.
    assert sent == [signal.SIGTERM, signal.SIGKILL]
    assert code is None, (
        "an unreapable process must report None, not a fake exit code — a caller "
        "comparing to 0 would otherwise call this a successful rip."
    )
    assert any("survived SIGKILL" in r.message for r in caplog.records), (
        "gave up silently; a leaked ripper still holding the drive must be in the log"
    )


def test_rip_handle_cancel_is_actually_called_from_the_product() -> None:
    """`cancel()` was fully implemented, documented — and called from nowhere.

    A method like this is worse than a missing one: `RipWorker.cancel`'s docstring
    described the SIGTERM→SIGKILL escalation as the thing that would stop a ripper
    ignoring SIGTERM, so the gap read as covered in review. It was dead code for as
    long as it existed (found by audit, 2026-07-29).

    This is `docs/testing.md` §5.x — test the wiring at the call site — applied to a
    method rather than a signal. Deliberately a source-level check: the deadlock it
    resolves only reproduces with a real full pipe, so behaviour tests use a fake
    handle and cannot prove the *real* `RipHandle.cancel` is reachable.

    **It checks reachability, not merely presence.** The first version asserted only
    that a `<handle>.cancel(...)` call existed somewhere in `src/`, and it passed
    against a deliberately reverted tree — because the call still sat there inside a
    helper that nothing called any more. A call site in dead code is dead code; that
    is the same "mentioning is not stopping" trap `test_harness_fidelity.py` was
    written for, hit a second time. So the enclosing function must itself be called.
    """
    import ast
    from pathlib import Path

    src = Path(rip_backend.__file__).resolve().parents[1]
    # name -> where a `<...handle...>.cancel(...)` call sits inside it
    call_sites: dict[str, str] = {}
    # Every function name invoked anywhere in src/, so we can ask whether the
    # function holding the call site is itself reachable.
    invoked: set[str] = set()

    for path in src.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        # Record the enclosing function of every rip-handle `.cancel(...)` call.
        for func in ast.walk(tree):
            if not isinstance(func, ast.FunctionDef):
                continue
            for node in ast.walk(func):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "cancel"
                    # Narrow to the rip handle specifically — plenty of unrelated
                    # objects have a `cancel`, and counting those would let this
                    # pass on the strength of something else entirely.
                    and "handle" in ast.unparse(node.func.value).lower()
                    # Not the definition's own file: `RipHandle.cancel` calling
                    # itself recursively would not make it reachable.
                    and path.name != "rip_backend.py"
                ):
                    call_sites[func.name] = f"{path.relative_to(src)}:{node.lineno}"
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                target = node.func
                name = (
                    target.id
                    if isinstance(target, ast.Name)
                    else getattr(target, "attr", "")
                )
                if name:
                    invoked.add(name)

    assert call_sites, (
        "no code in src/ calls <rip handle>.cancel(). The SIGTERM→SIGKILL "
        "escalation is implemented and documented but unreachable, so a ripper "
        "that ignores SIGTERM is never killed and the drive keeps spinning. Wire "
        "it in (RipWorker._reap_ripper) or delete the method — do not leave a "
        "documented promise that no code keeps."
    )
    reachable = {name: where for name, where in call_sites.items() if name in invoked}
    assert reachable, (
        "<rip handle>.cancel() is called only from function(s) that nothing else "
        f"calls: {call_sites}. The escalation is unreachable in practice, which is "
        "the original bug wearing a helper's clothes."
    )


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
        rip_backend.INFO_PROBE,
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

    # `run_capture` no longer calls `subprocess.run`: it goes through the shared
    # `KillableCommand` so the child can be signalled (docs/testing.md §8 — move the
    # patch target to where the code now lives). The seam is the command's `run`.
    monkeypatch.setattr(rip_backend.INFO_PROBE, "run", _boom)
    with pytest.raises(RipError) as info:
        run_capture("cyanrip", "/x/cyanrip", ["-V"], timeout=5)
    assert "binary not found" in str(info.value)


def test_run_capture_timeout_raises_riperror(monkeypatch: pytest.MonkeyPatch) -> None:
    def _timeout(*a: Any, **k: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd="cyanrip", timeout=5)

    monkeypatch.setattr(rip_backend.INFO_PROBE, "run", _timeout)
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
