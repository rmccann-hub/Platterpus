"""Measured drive cache-defeat probe (``cd-paranoia -A``) — KDD-25/KDD-29.

Why this exists
---------------
EAC's archival log carries a ``Defeat audio cache: Yes/No`` fact, measured by
EAC during drive setup. cyanrip prints no such line, and its engine
(libcdio-paranoia) only *attempts* cache defeat best-effort — so Platterpus has
had to render the field as ``(unknown)`` rather than forge a ``Yes`` (KDD-25).

This adapter closes that honestly. ``cd-paranoia`` is libcdio's own copy of the
cdparanoia tool — **the same read engine cyanrip uses** — and its ``-A``
(analyze-drive) mode runs the drive's cache/timing self-test. Because it is the
same engine, what ``-A`` finds about this drive's cache is a valid statement
about the reads the actual rip performs. We run it, parse the result, and record
a *measured* Yes/No/(unknown) per drive.

This is the equal-or-stronger, honestly-labelled analogue of EAC's cache field
(the same "match EAC's rigor, stay up front that we are not EAC" principle as the
log checksum, KDD-28): both are empirical drive probes; ours is attributed to
Platterpus + cd-paranoia and never claims to be EAC's own measurement.

Boundaries
----------
* **Thin adapter (Critical Rule #1)** over an external CLI — the only place that
  knows ``cd-paranoia``'s argv and output shape, so a future replacement is a
  one-file change.
* **Distrobox-routed (Critical Rule #3).** ``cd-paranoia`` touches the drive, so
  it is the host-exported wrapper (``~/.local/bin/cd-paranoia``) that runs inside
  the ``ripping`` container against the mapped device — exactly how cyanrip runs.
  We never open the raw device ourselves.
* **Pure parser, never raises** (parser-grade, per CLAUDE.md): a malformed/partial
  ``-A`` output degrades to a best-effort result, never an exception. The verdict
  defaults to *unknown* and only becomes ``True``/``False`` on a clear signal — we
  never fabricate a ``Yes`` we didn't measure.
* **Runs off the GUI thread.** The probe reads the disc and can take seconds
  (and, on a wedged drive, hit its timeout); the caller invokes it from a worker.
  The ``runner`` is injectable so tests never touch a real drive.

Hardware note (KDD-29): the exact wording ``cd-paranoia -A`` prints for the cache
verdict is confirmed against the first real capture on the BDR-209D and any
divergent build; until a phrase is seen on hardware the parser stays conservative
(``unknown``) rather than guess a ``Yes``. The signal tables below are the single
place to adjust when a new real capture arrives — add the phrase, add a fixture
line to the regression test.
"""

from __future__ import annotations

import logging
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from platterpus.paths import CDPARANOIA_BINARY_DEFAULT

log = logging.getLogger(__name__)

# A runner takes an argv list and returns a CompletedProcess (captured text).
# Injectable so tests never shell out to a real cd-paranoia / real drive.
Runner = Callable[[list[str]], "subprocess.CompletedProcess[str]"]

# The probe reads the disc, so it is slower than a version check but must still
# be bounded — a wedged drive must not hang the worker forever. If it does hang,
# the force-stop path already lists ``cd-paranoia`` in its reader names, so a
# Cancel/force-stop reaches it.
_PROBE_TIMEOUT_S: float = 90.0

# --- Cache-verdict signal tables (KDD-29: hardware-tuned) -------------------
#
# The mapping logic (parse_cache_analysis) is what the unit tests pin; the exact
# PHRASES are what a real ``cd-paranoia -A`` capture pins. Keep them here, one
# place, so a hardware-tuning pass is an edit to these tuples + a fixture line —
# never a change to the logic. All matched case-insensitively.
#
# "Defeat is in effect" — the drive's cache is being managed (cdparanoia flushes
# it with overlapping reads) OR there is no cache to defeat. Either way a re-read
# hits the medium, which is the whole point. cyanrip's engine does the same, so a
# positive here speaks for the rip.
_DEFEAT_SIGNALS: tuple[str, ...] = (
    r"cache management",  # cdparanoia announces it will manage the cache
    r"cache[- ]defeat",  # "cache-defeat capable", "cache defeat enabled"
    r"drive is caching[^.]*\bwill\b",  # "…caching; cdparanoia will compensate"
    r"does not cache",  # no cache to defeat
    r"no\b[^.\n]*\bcache",  # "no read cache", "no audio cache"
    r"drive tests? ok",  # analysis passed cleanly with paranoia
)

# "Caches and cannot be defeated" — the dangerous case EAC's field warns about.
# Only an explicit negative sets False; anything unclear stays unknown.
_CACHE_UNBEATABLE_SIGNALS: tuple[str, ...] = (
    r"cannot\b[^.\n]*\bcache",  # "cannot defeat cache"
    r"cache\b[^.\n]*cannot be (defeated|managed|flushed)",
    r"unable to (defeat|manage|flush)[^.\n]*cache",
)

# A reported cache size (sectors), recorded as measured evidence when present.
_CACHE_SECTORS_RE: re.Pattern[str] = re.compile(
    r"cache[^.\n]*?(?P<sectors>\d{1,7})\s*sector", re.IGNORECASE
)


@dataclass(frozen=True)
class CacheProbeResult:
    """Outcome of a ``cd-paranoia -A`` cache analysis. Never carries a guess.

    - ``defeat``: ``True`` if the drive's audio cache is defeated (managed, or
      absent) so re-reads hit the medium; ``False`` if it explicitly cannot be;
      ``None`` if we couldn't determine it (the honest default — rendered
      "(unknown)", never forged "Yes").
    - ``cache_sectors``: the drive's measured cache size in sectors, if reported.
    - ``analyzed``: ``True`` if cd-paranoia ran and produced output to parse
      (distinguishes "ran, inconclusive" from "never ran").
    - ``raw_output``: captured stdout+stderr (trimmed) — the diagnostic evidence
      kept in the report/log so a verdict is auditable.
    - ``error``: a short reason the probe couldn't run (missing binary, timeout),
      "" when it ran.
    """

    defeat: bool | None = None
    cache_sectors: int | None = None
    analyzed: bool = False
    raw_output: str = ""
    error: str = ""


def build_argv(device: str, binary: Path = CDPARANOIA_BINARY_DEFAULT) -> list[str]:
    """The ``cd-paranoia -A`` argv for analyzing ``device``'s cache behavior.

    ``-A`` = analyze-drive (test + report, extract nothing). ``-d <device>``
    targets the specific drive so the probe can never analyze the wrong one on a
    multi-drive rig. Routes through the host-exported wrapper (Critical Rule #3);
    a bare ``device`` (no path) omits ``-d`` and lets cd-paranoia pick its default.
    """
    argv = [str(binary), "-A"]
    if device:
        argv += ["-d", device]
    return argv


def parse_cache_analysis(output: str) -> CacheProbeResult:
    """Parse ``cd-paranoia -A`` output into a cache verdict. NEVER raises.

    Conservative by design: returns ``defeat=None`` unless a clear signal is
    present, so an unrecognized/partial report is honestly "unknown", never a
    fabricated "Yes". The size, when reported, is always recorded as evidence.
    """
    try:
        text = output or ""
        analyzed = bool(text.strip())

        sectors: int | None = None
        size_match = _CACHE_SECTORS_RE.search(text)
        if size_match:
            try:
                sectors = int(size_match.group("sectors"))
            except (TypeError, ValueError):
                sectors = None

        # Order matters: an explicit "cannot defeat" wins over a generic positive
        # so we never call a known-bad drive "defeated".
        if _any_match(_CACHE_UNBEATABLE_SIGNALS, text):
            defeat: bool | None = False
        elif _any_match(_DEFEAT_SIGNALS, text):
            defeat = True
        else:
            defeat = None

        return CacheProbeResult(
            defeat=defeat,
            cache_sectors=sectors,
            analyzed=analyzed,
            raw_output=text.strip()[:2000],
        )
    except Exception:  # noqa: BLE001 — a parser must never crash a caller
        log.exception("cd-paranoia -A parse failed; treating as unknown")
        return CacheProbeResult()


def _any_match(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _default_runner(argv: list[str]) -> subprocess.CompletedProcess[str]:
    """Run cd-paranoia, capturing text output; no stdin (can't block on a TTY),
    bounded by a timeout so a wedged drive can't hang the worker forever."""
    return subprocess.run(
        argv,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=_PROBE_TIMEOUT_S,
        check=False,
    )


def probe_cache_defeat(
    device: str,
    *,
    binary: Path = CDPARANOIA_BINARY_DEFAULT,
    runner: Runner | None = None,
) -> CacheProbeResult:
    """Measure whether ``device`` defeats its audio cache. NEVER raises.

    Runs ``cd-paranoia -A -d <device>`` (off the GUI thread — the caller supplies
    a worker) and parses the result. A missing binary, a timeout, or any OS error
    yields an ``analyzed=False`` result with ``error`` set and ``defeat=None`` —
    the caller records "(unknown)", never a forged verdict.
    """
    run = runner or _default_runner
    argv = build_argv(device, binary)
    try:
        proc = run(argv)
    except FileNotFoundError:
        log.info("cache probe: %s not present; verdict stays unknown", binary)
        return CacheProbeResult(error="cd-paranoia not installed")
    except subprocess.TimeoutExpired:
        log.warning(
            "cache probe: cd-paranoia -A timed out on %s", device or "(default)"
        )
        return CacheProbeResult(error="timed out", analyzed=True)
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("cache probe: cd-paranoia -A failed: %s", exc)
        return CacheProbeResult(error=str(exc))

    combined = (getattr(proc, "stdout", "") or "") + (getattr(proc, "stderr", "") or "")
    result = parse_cache_analysis(combined)
    log.info(
        "cache probe on %s: defeat=%s cache_sectors=%s",
        device or "(default)",
        result.defeat,
        result.cache_sectors,
    )
    return result
