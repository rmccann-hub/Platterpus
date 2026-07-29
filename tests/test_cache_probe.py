"""Tests for platterpus.adapters.cache_probe (the cd-paranoia -A cache probe).

The adapter must be (1) honest — a verdict only when the output clearly says so,
never a fabricated "Yes"; (2) robust — its parser never raises on any input
(parser-grade, per CLAUDE.md), so a cd-paranoia output-format change can't crash
a caller; and (3) correctly routed — the argv targets the host-exported binary
and the requested device.
"""

from __future__ import annotations

import signal
import subprocess
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from platterpus.adapters import cache_probe
from platterpus.adapters.cache_probe import (
    CacheProbeResult,
    build_argv,
    describe,
    parse_cache_analysis,
    probe_cache_defeat,
)

# --- argv construction ------------------------------------------------------


def test_argv_targets_the_device_and_analyze_flag() -> None:
    argv = build_argv("/dev/sr0", binary=Path("/home/u/.local/bin/cd-paranoia"))
    assert argv == ["/home/u/.local/bin/cd-paranoia", "-A", "-d", "/dev/sr0"]


def test_argv_omits_device_when_blank() -> None:
    argv = build_argv("", binary=Path("cd-paranoia"))
    assert argv == ["cd-paranoia", "-A"]  # no dangling -d


# --- parser: verdict mapping ------------------------------------------------


def test_parses_defeat_yes_and_cache_size() -> None:
    out = "Drive cache management engaged. Drive cache holds 1200 sectors."
    result = parse_cache_analysis(out)
    assert result.defeat is True
    assert result.cache_sectors == 1200
    assert result.analyzed is True


def test_parses_no_cache_as_defeated() -> None:
    # No cache to defeat → re-reads reach the disc, so the verdict is True.
    assert parse_cache_analysis("This drive does not cache audio reads.").defeat is True


def test_explicit_unbeatable_wins_over_a_generic_positive() -> None:
    # A drive that caches AND cannot be defeated is the dangerous case; an
    # explicit negative must not be overridden by an incidental positive phrase.
    out = "cache management attempted, but the cache cannot be defeated on this unit"
    assert parse_cache_analysis(out).defeat is False


def test_ambiguous_output_is_unknown_never_guessed() -> None:
    # The honesty gate: no clear signal → None (rendered "(unknown)"), never a
    # fabricated Yes.
    result = parse_cache_analysis("Analyzing... some unrelated timing chatter.")
    assert result.defeat is None
    assert result.analyzed is True  # it DID run, just inconclusive


def test_empty_output_is_unanalyzed_and_unknown() -> None:
    result = parse_cache_analysis("")
    assert result.defeat is None
    assert result.analyzed is False


# --- parser: never raises (property) ----------------------------------------


@given(st.text())
def test_parser_never_raises_on_arbitrary_text(text: str) -> None:
    result = parse_cache_analysis(text)
    assert isinstance(result, CacheProbeResult)
    assert result.defeat in (True, False, None)


@given(st.binary().map(lambda b: b.decode("latin-1")))
def test_parser_never_raises_on_binary_ish_text(text: str) -> None:
    # cd-paranoia can emit odd bytes on a flaky drive; the parser must cope.
    assert isinstance(parse_cache_analysis(text), CacheProbeResult)


# --- probe(): subprocess handling (injected runner) -------------------------


def _proc(stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["cd-paranoia"], 0, stdout=stdout, stderr=stderr)


def test_probe_reads_stdout_and_stderr() -> None:
    def runner(argv: list[str]):
        return _proc(stdout="drive tests ok", stderr="cache holds 999 sectors")

    result = probe_cache_defeat("/dev/sr0", runner=runner)
    assert result.defeat is True
    assert result.cache_sectors == 999


def test_probe_missing_binary_is_unknown_not_a_crash() -> None:
    def runner(argv: list[str]):
        raise FileNotFoundError(argv[0])

    result = probe_cache_defeat("/dev/sr0", runner=runner)
    assert result.defeat is None
    assert result.analyzed is False
    assert "not installed" in result.error


def test_probe_timeout_is_unknown() -> None:
    def runner(argv: list[str]):
        raise subprocess.TimeoutExpired(argv, 90.0)

    result = probe_cache_defeat("/dev/sr0", runner=runner)
    assert result.defeat is None
    assert "timed out" in result.error


def test_probe_os_error_is_unknown() -> None:
    def runner(argv: list[str]):
        raise OSError("device busy")

    result = probe_cache_defeat("/dev/sr0", runner=runner)
    assert result.defeat is None
    assert result.error


def test_probe_default_binary_is_the_host_export() -> None:
    # Sanity: the default routes through the host-exported wrapper (Rule #3).
    assert cache_probe.CDPARANOIA_BINARY_DEFAULT.name == "cd-paranoia"
    assert ".local/bin" in str(cache_probe.CDPARANOIA_BINARY_DEFAULT)


# --- Real hardware output (BDR-209D, 2026-07-26) -----------------------------

_REAL_A_OUTPUT = (
    Path(__file__).resolve().parent / "fixtures" / "cdparanoia_A_bdr209d.txt"
)


def test_parses_the_real_bdr209d_output() -> None:
    """The authoritative case: cd-paranoia 10.2's actual `-A` report on the
    project's reference drive. This is the capture KDD-29 said the parser had to
    be tuned against — pinning it means a future signal-table edit can't silently
    stop recognising the one drive we've measured."""
    result = parse_cache_analysis(_REAL_A_OUTPUT.read_text(encoding="utf-8"))
    assert result.defeat is True, "the real report states the cache IS defeated"
    assert result.cache_sectors == 140  # "Approximate random access cache size"
    assert result.analyzed is True


def test_backseek_flush_line_is_the_authoritative_signal() -> None:
    """cd-paranoia's specific cache-defeat statement, on its own, is enough —
    we must not depend on the generic "Drive tests OK" summary also being there."""
    assert (
        parse_cache_analysis("        Backseek flushes the cache as expected").defeat
        is True
    )


def test_explicit_backseek_failure_is_a_negative() -> None:
    for text in (
        "Backseek does not flush the cache",
        "backseek doesn't flush the cache",
    ):
        assert parse_cache_analysis(text).defeat is False, text


def test_zero_sector_cache_counts_as_defeated() -> None:
    """A measured cache of zero sectors means there's nothing to defeat, so a
    re-read necessarily reaches the medium. Data-driven, not a phrase guess."""
    result = parse_cache_analysis("Approximate random access cache size: 0 sector(s)")
    assert result.cache_sectors == 0
    assert result.defeat is True


def test_frame_count_alone_never_implies_a_verdict() -> None:
    # Guard the honesty rule: timing/size chatter with no verdict stays unknown.
    text = "Seek/read timing:\n [59:29.27]: 97ms seek, 1.50ms/sec read [8.9x]\n"
    assert parse_cache_analysis(text).defeat is None


def test_probe_timeout_budget_covers_a_real_analysis() -> None:
    """REGRESSION (real hardware, 2026-07-26): the timeout was 90 s and `-A`
    exceeded it on the BDR-209D — the app reported "could not be determined" for a
    drive whose analysis actually succeeds (app log: probe started 14:05:31,
    "timed out" 14:07:01 = 90.009 s). `-A` does a seven-point seek/read timing
    sweep plus a full cache-behaviour analysis, so the budget must be minutes."""
    assert cache_probe._PROBE_TIMEOUT_S >= 300.0


# --- describe(): the unknown verdict must name its cause ---------------------


def test_describe_is_empty_when_a_verdict_was_determined() -> None:
    assert describe(CacheProbeResult(defeat=True)) == ""
    assert describe(CacheProbeResult(defeat=False)) == ""


def test_describe_distinguishes_the_three_unknown_causes() -> None:
    """REGRESSION (real hardware, 2026-07-26): all three reached the user as the
    same undiagnosable "could not be determined", so nothing could be acted on."""
    missing = describe(CacheProbeResult(error="cd-paranoia not installed"))
    timed_out = describe(CacheProbeResult(error="timed out", analyzed=True))
    inconclusive = describe(CacheProbeResult(analyzed=True, raw_output="odd report"))

    assert "Set up Platterpus" in missing  # tells them how to fix it
    assert "too long" in timed_out or "timed out" in timed_out
    assert "log" in inconclusive  # points at the captured output
    # The whole point: three different problems read differently.
    assert len({missing, timed_out, inconclusive}) == 3
    assert all(s.strip() for s in (missing, timed_out, inconclusive))


@given(st.text())
def test_describe_never_raises(text: str) -> None:
    assert isinstance(describe(CacheProbeResult(error=text, raw_output=text)), str)


# --- Cancellation ------------------------------------------------------------
#
# Regression set for the false-promise cancel (audit, 2026-07-29). Closing the
# drive-setup dialog was supposed to stop `cd-paranoia -A`; it called
# `RipBackend.cancel_setup`, a concrete no-op the cyanrip backend never overrode,
# so the disc kept spinning for up to the 600 s ceiling with the physical eject
# button ignored (a read holds the device).


def test_the_probe_runs_the_child_in_its_own_process_group() -> None:
    """`start_new_session=True` is load-bearing, not cosmetic.

    Cancellation signals the process GROUP, because the host wrapper spawns podman
    which spawns the actual reader — signalling only the parent leaves the disc
    spinning. If the child is *not* a group leader it shares OUR group, and the
    `killpg` in `cancel_active_probe` would signal the GUI itself. So this asserts
    the flag rather than trusting it.
    """
    import inspect

    source = inspect.getsource(cache_probe._default_runner)
    assert "start_new_session=True" in source, (
        "the cache probe's child is not started in a new session, so it shares the "
        "GUI's process group — cancelling it would killpg our own process."
    )


def test_cancel_kills_the_live_probe_process_group(monkeypatch, caplog) -> None:
    """The real thing: a cancel while a probe is running kills its group.

    Drives the actual `_default_runner` against a child that would otherwise
    outlive the test, and cancels it from another thread the way the GUI does.
    """
    import threading

    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(cache_probe.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(
        cache_probe.os, "killpg", lambda pgid, sig: killed.append((pgid, sig))
    )

    started = threading.Event()
    release = threading.Event()

    class _FakePopen:
        """A child that stays 'running' until the test lets it finish."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            self.pid = 4242
            self.returncode: int | None = None
            self.kwargs = kwargs

        def poll(self) -> int | None:
            return self.returncode

        def communicate(self, timeout: float | None = None) -> tuple[str, str]:
            started.set()
            release.wait(10)
            self.returncode = -9
            return ("", "")

        def kill(self) -> None:  # pragma: no cover — group kill succeeds here
            self.returncode = -9

    monkeypatch.setattr(cache_probe.subprocess, "Popen", _FakePopen)

    result: list[subprocess.CompletedProcess[str]] = []

    def _run() -> None:
        result.append(cache_probe._default_runner(["cd-paranoia", "-A"]))

    worker = threading.Thread(target=_run)
    worker.start()
    assert started.wait(10), "the probe never started"

    with caplog.at_level("INFO"):
        cache_probe.cancel_active_probe()  # what the GUI thread calls

    release.set()
    worker.join(10)
    assert not worker.is_alive()

    assert killed == [(4242, signal.SIGKILL)], (
        f"cancel did not SIGKILL the probe's process group; sent {killed}. A flag "
        "the blocked call never checks is not cancellation."
    )
    assert any("cancelling cd-paranoia" in r.message for r in caplog.records)
    # And the registry is clean, so the next probe isn't pre-cancelled.
    assert cache_probe._active_proc is None
    assert cache_probe._cancel_requested is False


def test_a_cancel_during_startup_is_not_lost(monkeypatch) -> None:
    """The registration race: cancel between `Popen` and registration.

    Without the sticky flag the cancel finds `_active_proc is None`, returns
    quietly, and the probe runs to completion — a cancel the user pressed that did
    nothing. The runner re-checks the flag right after registering.
    """
    killed: list[int] = []
    monkeypatch.setattr(cache_probe.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(cache_probe.os, "killpg", lambda pgid, sig: killed.append(sig))

    class _FakePopen:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.pid = 99
            self.returncode: int | None = None
            # Cancel lands here — after the process exists, before it is registered.
            cache_probe.cancel_active_probe()

        def poll(self) -> int | None:
            return self.returncode

        def communicate(self, timeout: float | None = None) -> tuple[str, str]:
            self.returncode = -9
            return ("", "")

        def kill(self) -> None:  # pragma: no cover
            self.returncode = -9

    monkeypatch.setattr(cache_probe.subprocess, "Popen", _FakePopen)
    cache_probe._default_runner(["cd-paranoia", "-A"])

    assert killed == [signal.SIGKILL], (
        "a cancel that arrived during process startup was dropped — the sticky "
        f"_cancel_requested flag is not being honoured. Sent: {killed}"
    )
    assert cache_probe._cancel_requested is False  # reset for the next probe


def test_a_timed_out_probe_is_killed_rather_than_left_spinning(monkeypatch) -> None:
    """`subprocess.run` killed the child on timeout; `Popen` does not for free.

    Swapping to `Popen` for cancellability would otherwise have LOST that
    behaviour — a timed-out probe left running, disc spinning, which is exactly the
    bug being fixed. The new state a fix creates needs its own test.
    """
    killed: list[int] = []
    monkeypatch.setattr(cache_probe.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(cache_probe.os, "killpg", lambda pgid, sig: killed.append(sig))

    class _TimingOutPopen:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.pid = 7
            self.returncode: int | None = None
            self._calls = 0

        def poll(self) -> int | None:
            return self.returncode

        def communicate(self, timeout: float | None = None) -> tuple[str, str]:
            self._calls += 1
            if self._calls == 1:
                raise subprocess.TimeoutExpired(cmd="cd-paranoia", timeout=timeout)
            self.returncode = -9  # reaped after the kill
            return ("", "")

        def kill(self) -> None:  # pragma: no cover
            self.returncode = -9

    monkeypatch.setattr(cache_probe.subprocess, "Popen", _TimingOutPopen)

    # probe_cache_defeat turns this into an honest "timed out" unknown verdict.
    result = probe_cache_defeat("/dev/sr0")

    assert killed == [signal.SIGKILL], (
        f"a timed-out probe was not killed; sent {killed}. It keeps the disc "
        "spinning and holds the device against the eject button."
    )
    assert result.defeat is None and result.error == "timed out"
