"""Tests for platterpus.adapters.cache_probe (the cd-paranoia -A cache probe).

The adapter must be (1) honest — a verdict only when the output clearly says so,
never a fabricated "Yes"; (2) robust — its parser never raises on any input
(parser-grade, per CLAUDE.md), so a cd-paranoia output-format change can't crash
a caller; and (3) correctly routed — the argv targets the host-exported binary
and the requested device.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from platterpus.adapters import cache_probe
from platterpus.adapters.cache_probe import (
    CacheProbeResult,
    build_argv,
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
