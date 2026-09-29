"""A probe Platterpus stops itself is recorded as stopped, never as the tool failing.

The round-29 Full run's bundle (2026-09-28, `docs/handshake/artifactsround29/`) is
the case. At 18:13:00 the operator pressed Rescan; the rescan superseded the
`cyanrip -I` disc probe in flight, and `KillableCommand.cancel()` sent it SIGKILL
(`round29fullplatterpusapplog1.txt:23`). The next line recorded
`deps.command_failed: cyanrip exited -9` as a warning, and every rip report of
that app session carried it in its diagnostics, as did the diagnostics the
operator pasted. The -9 was ours.

So a run is marked as ended by our cancel only when both hold: a cancel covered
that run, and the child died of SIGKILL. The tests below pin both halves and
every caller that reports a probe's exit: the disc-info probe (`run_capture`),
the version probe (`deps.checks`) and the cache probe.
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time

import pytest

from platterpus import diagnostics
from platterpus.adapters import cache_probe, rip_backend
from platterpus.deps import checks
from platterpus.killable import CancelledRun, KillableCommand, was_cancelled


def _run_then_cancel(cmd: KillableCommand) -> object:
    """Run ``sleep 30`` on a thread, cancel it once it is running, return the outcome."""
    outcome: list[object] = []

    def _run() -> None:
        try:
            outcome.append(cmd.run(["sh", "-c", "sleep 30"], timeout=30))
        except BaseException as exc:  # noqa: BLE001 — record whatever happened
            outcome.append(exc)

    worker = threading.Thread(target=_run)
    worker.start()
    deadline = time.monotonic() + 10
    while not cmd.is_running() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert cmd.is_running(), "the child never started"
    cmd.cancel()
    worker.join(15)
    assert not worker.is_alive(), "the run never returned after cancel"
    assert len(outcome) == 1
    return outcome[0]


def test_a_run_our_cancel_ended_says_so() -> None:
    result = _run_then_cancel(KillableCommand("test ours"))
    assert isinstance(result, subprocess.CompletedProcess), result
    assert result.returncode == -9
    assert was_cancelled(result)


def test_a_sigkill_nobody_here_sent_is_the_tools_exit() -> None:
    """The counter-case: the same -9 with no cancel is the tool's exit (an OOM kill)."""
    result = KillableCommand("test theirs").run(["sh", "-c", "kill -9 $$"], timeout=30)
    assert result.returncode == -9, "the floor: this case must reach the same -9"
    assert not was_cancelled(result)


def test_a_cancel_does_not_mark_a_run_that_starts_after_it() -> None:
    cmd = KillableCommand("test scoping")
    cmd.cancel()  # nothing running: it covers no run issued afterwards
    result = cmd.run(["sh", "-c", "kill -9 $$"], timeout=30)
    assert result.returncode == -9
    assert not was_cancelled(result)


def test_the_rescan_case_records_the_kill_as_ours(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The bundle's sequence, with a real child: a probe in flight, then our cancel."""
    monkeypatch.setattr(rip_backend, "INFO_PROBE", KillableCommand("rescan case"))
    diagnostics.clear()
    raised: list[BaseException] = []

    def _probe() -> None:
        try:
            rip_backend.run_capture("cyanrip", "sh", ["-c", "sleep 30"], timeout=30)
        except BaseException as exc:  # noqa: BLE001 — the assertion is on the type
            raised.append(exc)

    worker = threading.Thread(target=_probe)
    worker.start()
    deadline = time.monotonic() + 10
    while not rip_backend.INFO_PROBE.is_running() and time.monotonic() < deadline:
        time.sleep(0.01)
    rip_backend.cancel_info_probe()
    worker.join(15)
    try:
        assert raised and isinstance(raised[0], rip_backend.ProbeCancelled), raised
        # Still a RipError, so the disc-info worker's handling is unchanged.
        assert isinstance(raised[0], rip_backend.RipError)
        assert "stopped by Platterpus" in str(raised[0])
        codes = {(d.code, d.severity) for d in diagnostics.default_log().items()}
        assert ("deps.command_cancelled", diagnostics.INFO) in codes, codes
        assert not any(code == "deps.command_failed" for code, _ in codes), codes
    finally:
        diagnostics.clear()


def test_a_nonzero_exit_we_did_not_cause_is_still_a_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The fix must not quieten the real case: a -9 with no cancel is recorded."""
    monkeypatch.setattr(rip_backend, "INFO_PROBE", KillableCommand("theirs"))
    diagnostics.clear()
    try:
        rc, _ = rip_backend.run_capture(
            "cyanrip", "sh", ["-c", "kill -9 $$"], timeout=30
        )
        assert rc == -9
        items = diagnostics.default_log().items()
        assert [(d.code, d.severity) for d in items] == [
            ("deps.command_failed", diagnostics.WARNING)
        ]
    finally:
        diagnostics.clear()


def test_a_cancelled_version_probe_is_not_called_unavailable(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def _cancelled(argv: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        return CancelledRun(argv, -9, "", "")

    monkeypatch.setattr(checks.VERSION_PROBE, "run", _cancelled)
    with caplog.at_level(logging.DEBUG, logger="platterpus.deps.checks"):
        ok, _output, _where = checks._run_version_command(["cyanrip", "-V"])
    assert ok is False, "a probe with no answer still answers nothing"
    text = caplog.text
    assert "stopped by Platterpus" in text, text
    assert "unavailable" not in text, text


def test_a_cancelled_cache_probe_is_no_measurement_and_no_failure() -> None:
    diagnostics.clear()
    try:
        result = cache_probe.probe_cache_defeat(
            "/dev/sr0",
            runner=lambda argv: CancelledRun(argv, -9, "Backseek flushes the", ""),
        )
        assert result.defeat is None and not result.analyzed
        assert result.error.startswith("stopped by Platterpus"), result.error
        assert result.exit_code == -9
        assert diagnostics.default_log().count() == 0
    finally:
        diagnostics.clear()


def test_a_child_that_exited_before_the_cancel_keeps_its_own_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cancel that lands after the child exited covers the run and kills nothing.

    Constructed, not raced: the cancel is issued from inside ``communicate`` once the
    child has exited, so the watermark covers the run and its status is still ``3``.
    """
    cmd = KillableCommand("test exited first")

    class _CancelAfterExit(subprocess.Popen[str]):
        def communicate(self, *args: object, **kwargs: object) -> tuple[str, str]:
            out = super().communicate(*args, **kwargs)  # type: ignore[arg-type]  # passthrough
            cmd.cancel()
            return out

    monkeypatch.setattr(subprocess, "Popen", _CancelAfterExit)
    result = cmd.run(["sh", "-c", "exit 3"], timeout=30)
    with cmd._lock:
        assert cmd._cancel_through >= 1, "the floor: the cancel must cover this run"
    assert result.returncode == 3
    assert not was_cancelled(result)
