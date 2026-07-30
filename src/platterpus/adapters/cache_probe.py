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

Hardware status (KDD-29): **validated on the BDR-209D, 2026-07-26.** The real
``-A`` output is committed at ``tests/fixtures/cdparanoia_A_bdr209d.txt`` and pinned
by a test; on it this parser returns ``defeat=True, cache_sectors=140``. The signal
tables below remain the single place to adjust when a *different* drive or build
words its report differently — add the phrase, add a fixture line. An unrecognised
report still degrades to ``unknown`` rather than guessing, and now also **logs what
the tool actually said**, so a new wording arrives in the next bug report without
anyone having to run the CLI by hand.
"""

from __future__ import annotations

import logging
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from platterpus.killable import KillableCommand
from platterpus.paths import CDPARANOIA_BINARY_DEFAULT

log = logging.getLogger(__name__)

# A runner takes an argv list and returns a CompletedProcess (captured text).
# Injectable so tests never shell out to a real cd-paranoia / real drive.
Runner = Callable[[list[str]], "subprocess.CompletedProcess[str]"]

# The probe must be bounded — a wedged drive must not hang the worker forever. If
# it does hang, the force-stop path already lists ``cd-paranoia`` in its reader
# names, so a Cancel/force-stop reaches it.
#
# REGRESSION (real hardware, 2026-07-26, BDR-209D): this was 90 s, and ``-A``
# **timed out** — the app reported an honest but useless "could not be determined"
# for a drive whose cache analysis actually succeeds. ``-A`` is inherently slow: it
# runs a seek/read timing sweep at seven points across the disc (one seek alone
# measured 3692 ms on this drive) and *then* a full cache-behaviour analysis
# (readahead, tail rollbehind, granularity, backseek flush). Minutes, not seconds.
# Budget generously — the probe is off the GUI thread, genuinely cancellable (see
# `cancel_active_probe`; it was NOT, despite this comment once saying so — fixed
# 2026-07-29), and only ever runs when the user explicitly asks for it, so a long
# ceiling costs nothing and only ever bites a genuinely wedged drive.
_PROBE_TIMEOUT_S: float = 600.0

# --- Cache-verdict signal tables (KDD-29: hardware-tuned) -------------------
#
# The mapping logic (parse_cache_analysis) is what the unit tests pin; the exact
# PHRASES are what a real ``cd-paranoia -A`` capture pins. Keep them here, one
# place, so a hardware-tuning pass is an edit to these tuples + a fixture line —
# never a change to the logic. All matched case-insensitively.
#
# "Defeat is in effect" — the drive's cache is flushed between reads (so a re-read
# reaches the medium) or there is no cache to defeat. cyanrip's engine is the same
# libcdio-paranoia, so a positive here speaks for the actual rip.
#
# The first two are CONFIRMED against real BDR-209D output
# (``tests/fixtures/cdparanoia_A_bdr209d.txt``, captured 2026-07-26) — the backseek
# line is cdparanoia's *specific* statement that cache defeat works, so it leads;
# "Drive tests OK with Paranoia." is its overall pass. The rest are defensive
# variants for other builds/drives, kept because a drive we haven't seen may word
# it differently — an unmatched report still degrades to "unknown", never a guess.
_DEFEAT_SIGNALS: tuple[str, ...] = (
    r"backseek flushes the cache",  # ← the authoritative positive (confirmed)
    r"drive tests? ok",  # cdparanoia's overall verdict (confirmed)
    r"cache management",  # cdparanoia announces it will manage the cache
    r"cache[- ]defeat(?:s|ed|able)?\b",  # "cache-defeat capable", "defeats cache"
    r"does not cache",  # no cache to defeat
)

# "Caches and cannot be defeated" — the dangerous case EAC's field warns about.
# Only an EXPLICIT negative sets False; anything unclear stays unknown. Note the
# asymmetry is deliberate: a wrong "No" misinforms the user just as badly as a
# forged "Yes", so these stay narrow and literal rather than clever.
_CACHE_UNBEATABLE_SIGNALS: tuple[str, ...] = (
    r"backseek does(?:n't| not) flush the cache",  # the backseek line's negative
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
        elif sectors == 0:
            # A measured cache of zero sectors means there is no audio cache to
            # defeat, so a re-read necessarily reaches the medium. This is a
            # *data-driven* positive (not a phrase guess) and so is safe to trust
            # even on a build whose wording we don't recognise.
            defeat = True
        else:
            defeat = None

        result = CacheProbeResult(
            defeat=defeat,
            cache_sectors=sectors,
            analyzed=analyzed,
            raw_output=text.strip()[:2000],
        )
        if defeat is None and analyzed:
            # DIAGNOSABILITY (real-hardware lesson, 2026-07-26): an inconclusive
            # verdict used to leave no trace of *why*, so the only way to find out
            # was to ask the user to run the CLI by hand. Log what the tool actually
            # said, so the next occurrence is self-diagnosing from the log file
            # alone — and so a new drive's wording can be added to the tables above.
            log.warning(
                "cd-paranoia -A ran but matched no known cache verdict; "
                "recording (unknown). Raw output follows:\n%s",
                result.raw_output,
            )
        return result
    except Exception:  # noqa: BLE001 — a parser must never crash a caller
        log.exception("cd-paranoia -A parse failed; treating as unknown")
        return CacheProbeResult()


def describe(result: CacheProbeResult) -> str:
    """A user-facing reason the verdict is unknown; ``""`` when one was determined.

    Real-hardware lesson (2026-07-26): the dialog showed the same
    "could not be determined" whether cd-paranoia was missing, timed out, or simply
    said something we don't recognise — three different problems with three
    different fixes, and the user could act on none of them. The adapter already
    knows which happened, so it words it here (one place, testable, no Qt).
    """
    if result.defeat is not None:
        return ""
    if result.error:
        low = result.error.casefold()
        if "not installed" in low:
            return (
                "cd-paranoia isn't installed, so the cache couldn't be measured. "
                "Run Tools → Set up Platterpus… to install it, then try again."
            )
        if "timed out" in low:
            return (
                "the cache analysis ran too long and was stopped. It reads the disc "
                "at several points, so it needs a few minutes — make sure a disc is "
                "in the drive and nothing else is using it, then try again."
            )
        return f"the cache analysis couldn't run: {result.error}."
    if result.analyzed:
        return (
            "cd-paranoia ran but didn't report a cache verdict we recognise, so it "
            "was recorded as unknown rather than guessed. Its full output is in the "
            "log file if you want to send it in."
        )
    return "the cache analysis produced no output."


def _any_match(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


# --- Cancellation ------------------------------------------------------------
#
# The probe is the longest disc-spinning operation the GUI can start (600 s
# ceiling), and closing the drive-setup dialog is supposed to stop it. It did not:
# `DriveSetupWorker.cancel()` called `RipBackend.cancel_setup()`, which is a
# **concrete no-op on the ABC that the cyanrip backend never overrode**, so cancel
# set a flag the blocked `subprocess.run` never checked — and the flag is only read
# *between* the two setup steps. Meanwhile the comment above claimed the probe was
# "cancellable" and `drive_setup_dialog` claimed `cancel_setup` "SIGTERM/SIGKILLs
# the subprocess". Three places documenting a capability that did not exist
# (audit, 2026-07-29). CLAUDE.md rule 9: a `cancel()` that only sets a flag the
# blocked call never checks is a false promise — do not ship one.
#
# Making it real needs a handle on the live child, which `subprocess.run` hides.
# That machinery — Popen, a thread-safe registry, `start_new_session` so a killpg
# reaches the podman/in-container tree instead of the GUI, the cancel/startup race,
# and killing on timeout — was first written *here*, then wanted again by the
# disc-info probe. It now lives once in `platterpus.killable`; this module keeps
# only the policy that is specific to the cache probe (which binary, which timeout).
_PROBE: KillableCommand = KillableCommand("cache probe (cd-paranoia -A)")


def cancel_active_probe() -> None:
    """Kill the running ``cd-paranoia -A``, if any. Thread-safe, non-blocking.

    Called from the **GUI thread** when the user closes the drive-setup dialog, so
    it must not wait for anything (CLAUDE.md never-block rule). See
    `platterpus.killable` for why the signal is SIGKILL rather than SIGTERM and why
    it goes to the process group.
    """
    _PROBE.cancel()


def _default_runner(argv: list[str]) -> subprocess.CompletedProcess[str]:
    """Run cd-paranoia, capturing text output; no stdin (can't block on a TTY),
    bounded by a timeout so a wedged drive can't hang the worker forever."""
    return _PROBE.run(argv, timeout=_PROBE_TIMEOUT_S)


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
