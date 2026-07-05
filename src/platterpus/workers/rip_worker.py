"""RipWorker — drives a RipBackend rip off the GUI thread.

The main thread constructs a RipWorker, moves it to a QThread, and
connects QThread.started to RipWorker.start_rip. The worker streams the
backend's stdout (cyanrip — the sole backend, KDD-18) via Qt signals so
the GUI can update without blocking.

Signals:
  log_line(str)               — one line of rip output
  progress(int, float)        — (track_number, percent_complete) when
                                parseable from the output stream
  finished(bool, str)         — (success, log_file_path); log path is
                                "" when no .log file was located
  error(str)                  — short human-readable error message

Cancel:
  Call cancel() from the GUI thread. It sets a flag and forwards to
  RipHandle.cancel(), which SIGTERMs (then SIGKILLs) the subprocess.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from platterpus.adapters.rip_backend import (
    RipBackend,
    RipError,
    RipHandle,
    RipMetadata,
)
from platterpus.read_speed_ladder import (
    MAX_ATTEMPTS,
    MAX_SECURE_REREP,
    SpeedAttempt,
    disc_in_accuraterip,
    next_step,
    read_errors_present,
    tracks_failing_accuraterip,
    unstable_tracks,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RipParameters:
    """Everything the worker needs to start a rip.

    Keep this typed and frozen so the caller's intent is locked in
    before crossing thread boundaries — a `dict[str, Any]` would let
    typos slip through silently.
    """

    drive: str
    release_id: str
    output_dir: Path
    track_template: str
    disc_template: str
    unknown: bool = False
    # EAC bit-perfect parity gap (KDD-13). cover_art "" = don't fetch art;
    # otherwise the front cover is embedded after the rip.
    cover_art: str = ""
    max_retries: int = 5
    # cyanrip's `-Z N` (rip until N reads' checksums match) for marginal
    # discs. 0 = off.
    secure_rerip_matches: int = 0
    # Dynamic secure-rerip (0.4.9): when True (and secure_rerip_matches > 0),
    # DON'T apply `-Z` to every track. Rip once fast (no `-Z`), then secure-re-rip
    # only the tracks that didn't match AccurateRip (a DB match on the first read
    # is already proof of bit-perfection). False = today's behaviour (`-Z` on
    # every track). Default False here so a bare worker keeps the simple path.
    secure_rerip_dynamic: bool = False
    # Adaptive read-speed ladder (0.4.6). `read_speed_mode` is "auto_ladder"
    # (start fast, re-rip slower on read errors) or "fixed"; `read_speed` is the
    # fixed/starting `-S` value (0 = drive max). Defaults are conservative here
    # ("fixed" / 0 == today's behaviour) so a worker constructed without them —
    # e.g. in a unit test — never enters the escalation loop; the GUI passes the
    # user's config values (auto_ladder by default) explicitly.
    read_speed_mode: str = "fixed"
    read_speed: int = 0
    # When set, applied as the read offset for the rip (cyanrip's `-s`).
    read_offset_override: int | None = None
    # The GUI's already-fetched album/track tags (track table content),
    # fed to cyanrip via -a/-t so the rip needs no in-container network.
    metadata: RipMetadata | None = None


# Human-readable phase descriptions for the status line. Without these
# the GUI sat on "Starting rip…" for the whole pre-track disc scan
# (which can run a minute or more) and looked frozen — T32 feedback.
# The current backend is cyanrip (KDD-18) — its progress lines are matched by
# the _CYANRIP_* patterns further down. The patterns just below match the
# WHIPPER log format and are kept only as an inert whipper-format seam (harmless
# if a whipper-era log is ever re-fed); whipper's progress lines looked like:
#   "Reading TOC  50 %"
#   "Reading table  50 %"
#   "Reading track 3 of 16 (1 of 9) ...  42 %"
#   "Verifying track 3 of 16 (3 of 9) ... 42 %"
#   "Encoding track to FLAC (5 of 9) ...   0 %"
#   "Getting length of audio track (1 of 16) ... 100 %"
_DISC_SCAN_PATTERN = re.compile(r"Reading (?P<what>TOC|table)\s+(?P<pct>\d+)\s*%")
_TRACK_PHASE_PATTERN = re.compile(
    r"(?P<verb>Reading|Verifying) track (?P<track>\d+) of (?P<total>\d+)"
    r".*?(?P<pct>\d+)\s*%"
)
_LENGTH_PHASE_PATTERN = re.compile(
    r"Getting length of audio track \((?P<track>\d+) of (?P<total>\d+)\)"
)
# Per-track sub-phases that carry no track number on their own line.
_NAMED_PHASES: dict[str, str] = {
    "Encoding track to FLAC": "Encoding to FLAC…",
    "Calculating peak level": "Calculating peak level…",
    "Writing tags to FLAC": "Writing tags…",
    "Embed picture to FLAC": "Finalizing track…",
}

# --- cyanrip progress lines (KDD-18) ---------------------------------------
# cyanrip redraws ONE progress line with `\r` (cyanrip_main.c):
#   "Ripping track 5, progress - 42.37%, ETA - 3m, errors - 0"
#   "Ripping and encoding track 5, progress - 42.37%"
# Popen(text=True) reads in universal-newlines mode, which translates every
# bare `\r` to `\n` — so each redraw reaches log_lines() as its own line and
# these regexes see them one at a time, no extra plumbing.
_CYANRIP_TRACK_PROGRESS = re.compile(
    r"Ripping(?P<encoding> and encoding)? track (?P<track>\d+), progress - "
    r"(?P<pct>\d+(?:\.\d+)?)%(?:, ETA - (?P<eta>[^,]+))?"
)
# Per-track completion ("Track 5 ripped and encoded successfully!" / "with
# errors.") — pegs that track's slice of the overall bar.
_CYANRIP_TRACK_DONE = re.compile(
    r"^Track (?P<track>\d+) ripped and encoded (?P<how>successfully|with errors)"
)
# The start report carries the track total ("Disc tracks:    16") — cyanrip's
# progress lines don't repeat it, so we capture it here for the overall bar.
_CYANRIP_DISC_TRACKS = re.compile(r"^Disc tracks:\s+(?P<total>\d+)\s*$")

# A ripper can abort when it can't fetch online metadata (e.g. the container
# has no network) and wasn't told the disc is "unknown". We detect that so the
# GUI can auto-retry as an unknown-album rip — which needs no network — and tag
# locally afterward from the metadata it already has. These are whipper's abort
# strings; cyanrip is always run with `-N` and fed the GUI's tags (Critical
# Rule #5), so it never does an online lookup and never hits this — the heal
# path is currently inert, kept as the seam for any future networked backend.
_NO_METADATA_MARKERS: tuple[str, ...] = (
    "--unknown argument not passed",
    "unable to retrieve disc metadata",
)

# A ripper can exhaust its retries on a track it can't read consistently (a
# scratched/dirty disc). We turn that into an actionable message instead of a
# bare "Rip failed". This matches whipper's "giving up on track N" wording;
# cyanrip instead rips the track "with errors" and keeps going, so it doesn't
# trip this — the hint stays for the whipper-format seam and is harmless inert.
_TRACK_GIVEUP_RE = re.compile(r"giving up on track (?P<track>\d+)")

# Minimum wall-clock gap between forwarding consecutive *progress redraw* lines
# to the GUI. cyanrip redraws its progress many times a second (each `\r` becomes
# its own line — see above), and forwarding every one floods the GUI's event loop
# with queued signals: the window can't service paint events and goes black when
# another window is dragged over it (real-user report, 2026-06-27). Coalescing to
# ~10 updates/second keeps the bar and ETA feeling live while leaving the event
# loop plenty of room to repaint. Only progress lines are throttled — phase
# changes, errors, and end-of-rip markers always go through immediately.
_PROGRESS_MIN_INTERVAL_S: float = 0.1

# Slack subtracted from a pass's start time when deciding whether a .log is
# "this pass's" (see _find_log_path). Absorbs coarse filesystem mtime resolution
# and minor clock jitter; a real just-written log is many seconds newer than the
# pass start, so this only ever needs to be generous, never precise.
_LOG_MTIME_SLACK_S: float = 2.0

# Don't show an album ETA until at least this much wall-clock has elapsed —
# before that, elapsed÷fraction projects wild/"0s" values off almost no data.
_MIN_ELAPSED_FOR_ETA_S: float = 8.0

# EMA weight for the new raw ETA sample each tick (0<α≤1). Small = heavy
# smoothing. 0.15 damps the encode-phase sawtooth while still tracking real
# slowdowns within a few seconds.
_ETA_SMOOTHING_ALPHA: float = 0.15

# Trailing window (seconds) for the ETA's *rate* estimate. The remaining time is
# projected from the read rate over the last this-many seconds, NOT from the
# cumulative average since the pass began. Why: the disc-scan phase (the first
# ~5%) and the disc's inner tracks read far faster than the bulk, so averaging
# from zero let that fast start dominate and the early ETA came out absurdly low
# (real hardware: at 5% done / 14s in it said "~4m left" with 58m to go). A
# trailing window tracks the CURRENT rate and self-corrects as the rip proceeds.
_ETA_RATE_WINDOW_S: float = 90.0

# The "for posterity" ETA trace: sample at most this often (seconds) and cap the
# number of samples, so a long rip yields a compact comparable curve, not a
# per-tick flood. ~10s over even a 5-hour rip stays well under the cap.
_ETA_SAMPLE_INTERVAL_S: float = 10.0
_ETA_TRACE_MAX: int = 2000

# Stall detection for the ETA (real-hardware lesson: the Roots track-18 read that
# hung for HOURS while the on-screen ETA still counted down "~4h left"). When the
# album fraction hasn't advanced by a MEANINGFUL step for this long, the drive is
# stuck on a hard-to-read spot (a scratch/smudge); the plain projection would just
# show a misleading — and eventually absurd — countdown, so we say "stalled"
# instead. Keyed on meaningful progress, not zero movement, so a barely-crawling
# read (the disc showed 72.00→72.02% over minutes) is still caught.
#   * MIN_PROGRESS is what a HEALTHY read clears in a second or two (a track is a
#     several-percent slice of the album), so a normal rip never trips this; a
#     stuck/crawling read takes many minutes to clear it.
#   * THRESHOLD is deliberately generous (3 min) so a merely-slow-but-advancing
#     drive is never mislabelled — only a genuine hang crosses it.
_ETA_STALL_MIN_PROGRESS: float = 0.005  # 0.5% of the whole album
_ETA_STALL_THRESHOLD_S: float = 180.0

# cyanrip appends its OWN per-op ETA to each progress redraw
# ("…, progress - 42%, ETA - 3m"). We distrust it (it printed "822h" at 0.01%)
# and show our own smoothed album ETA instead — so strip cyanrip's trailing
# ETA clause from the lines we forward to the log view, or the two would
# contradict each other on screen (real-user report). It's always the last
# field, so match to end of line.
_CYANRIP_ETA_CLAUSE = re.compile(r",\s*ETA\s*-.*$")


def _coarsen_eta_seconds(seconds: float) -> int:
    """Round an ETA to a bucket sized to its magnitude, so the displayed number
    is steady instead of ticking every second (a 1-hour ETA doesn't need
    5-second precision). Bigger ETA → bigger bucket."""
    if seconds >= 3600:  # ≥ 1 h → nearest 5 min
        step = 300
    elif seconds >= 600:  # ≥ 10 min → nearest 1 min
        step = 60
    elif seconds >= 120:  # ≥ 2 min → nearest 30 s
        step = 30
    else:  # < 2 min → nearest 10 s
        step = 10
    return int(round(seconds / step) * step)


class RipWorker(QObject):
    """QObject worker that owns a rip subprocess for its lifetime.

    Construct on the GUI thread, then move to a QThread:

        worker = RipWorker(backend, params)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.start_rip)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()
    """

    log_line = Signal(str)
    # Two-tier progress so the GUI can show an overall bar (whole rip) and
    # a task bar (current operation). Overall is monotonic; task resets per
    # operation (read → verify → encode each sweep 0-100%).
    progress = Signal(float, float)  # overall_percent, task_percent
    status = Signal(str)  # human-readable current phase
    # Emitted with the 1-based track number whenever the ripper starts working
    # on a new track, so the GUI can follow along by highlighting that row.
    current_track = Signal(int)
    finished = Signal(bool, str)  # success, log_path
    error = Signal(str)

    def __init__(
        self,
        backend: RipBackend,
        params: RipParameters,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend: RipBackend = backend
        self._params: RipParameters = params
        self._handle: RipHandle | None = None
        # Last status text emitted, so we don't re-emit identical phases
        # on every progress tick (cyanrip redraws its progress many times a sec).
        self._last_status: str = ""
        # Progress state. `_overall` only ever moves forward (see
        # _bump_overall); `_total_tracks`/`_current_track` are learned from
        # the ripper's per-track progress lines (cyanrip's "Ripping track N";
        # the whipper "track N of M" form is still matched as an inert seam).
        self._overall: float = 0.0
        self._total_tracks: int = 0
        self._current_track: int = 0
        # Per-track MusicBrainz durations (ms), for weighting the overall bar by
        # each track's real length so the ETA tracks wall-clock instead of
        # oscillating (a 5-minute track is a bigger slice than a 3-minute one).
        # Built ONLY when the metadata gives a positive length for every track,
        # numbered 1..N contiguously; otherwise stays empty and the bar falls back
        # to today's equal-per-track slices (unknown discs, partial metadata). See
        # _overall_from_track. `_track_ms_prefix[n]` = ms before track n starts.
        self._track_ms: dict[int, int] = {}
        self._track_ms_total: int = 0
        self._track_ms_prefix: dict[int, int] = {}
        meta = getattr(params, "metadata", None)
        meta_tracks = list(getattr(meta, "tracks", ()) or ()) if meta else []
        if meta_tracks:
            lengths: dict[int, int] = {}
            usable = True
            for t in meta_tracks:
                n = getattr(t, "number", None)
                length = getattr(t, "length_ms", None)
                if not isinstance(n, int) or not isinstance(length, int) or length <= 0:
                    usable = False
                    break
                lengths[n] = length
            # Require a contiguous 1..N with no gaps/dupes — anything else and we
            # can't trust the weighting, so we don't use it.
            if usable and lengths and set(lengths) == set(range(1, len(lengths) + 1)):
                self._track_ms = lengths
                self._track_ms_total = sum(lengths.values())
                running = 0
                for n in range(1, len(lengths) + 1):
                    self._track_ms_prefix[n] = running
                    running += lengths[n]
        # Last track number we emitted `current_track` for, so we signal
        # once per track instead of on every per-percent progress line.
        self._emitted_track: int = 0
        # Monotonic timestamp of the last progress redraw we forwarded to the
        # GUI, for rate-limiting the flood (see _PROGRESS_MIN_INTERVAL_S). 0.0
        # means "none yet" → the first progress line always goes through.
        self._last_progress_emit: float = 0.0
        # Flag is a plain Python bool — assignment is atomic under the
        # GIL, so reading it from the worker thread while the GUI thread
        # sets it is safe without locks.
        self._cancelled: bool = False
        # Set true if the ripper aborts for lack of online metadata, so the GUI
        # can heal by retrying as an unknown-album rip. An inert whipper-era seam:
        # cyanrip runs with -N and is fed the GUI's tags, so it never hits this.
        # Only meaningful when this rip wasn't already unknown.
        self._needs_unknown_retry: bool = False
        # A user-facing explanation set when a known fatal pattern is seen
        # (e.g. the ripper giving up on an unreadable track). "" if none.
        self._failure_hint: str = ""
        # Wall-clock start of the rip, stamped when the stream loop begins. Used
        # to compute our OWN album-level ETA (elapsed × (1-frac)/frac) — stable
        # and self-correcting, unlike cyanrip's per-operation ETA which resets
        # every phase and is wildly wrong early (it printed "822h" at 0.01% on a
        # real disc). None until the loop starts.
        self._started_monotonic: float | None = None
        # Epoch wall-clock start of this rip (0.0 = unset → log discovery is
        # unfiltered). Set in start_rip; used to ignore a previous album's log.
        self._rip_started_at: float = 0.0
        # Smoothed album-ETA state (an exponential moving average of the raw
        # elapsed÷fraction projection). The raw projection sawtooths — it creeps
        # UP during a track's encode pass (overall bar frozen while time passes)
        # then drops when the next read advances the bar — so we damp it here and
        # round coarsely for display, per real-user feedback ("smooth it out").
        self._smoothed_remaining_s: float | None = None
        # ETA baseline for the CURRENT pass. The album-ETA divides elapsed by the
        # `overall` fraction — but `overall` resets to 0 at the start of every
        # pass, so using the whole-rip start as the baseline on pass 2+ divided a
        # large elapsed by a tiny fresh fraction and projected a wildly inflated
        # remaining time (#21). Reset per pass (in _reset_pass_progress) so each
        # pass estimates its own remaining time; falls back to the rip start.
        self._eta_pass_started: float | None = None
        # Trailing (elapsed_s, fraction) samples for the windowed rate estimate
        # (see _album_eta_text / _ETA_RATE_WINDOW_S). Pruned to the window and
        # cleared per pass so each pass's rate is measured on its own progress.
        self._eta_rate_window: list[tuple[float, float]] = []
        # Stall detection (see _album_eta_text / _ETA_STALL_THRESHOLD_S): the album
        # fraction at the last MEANINGFUL forward step, and the monotonic time it
        # was reached. When the fraction hasn't cleared another step for the
        # threshold, the read is stalled on a hard-to-read spot and we say so
        # instead of a misleading countdown. Reset per pass.
        self._eta_stall_frac: float | None = None
        self._eta_stall_since: float | None = None
        # True once we've LOGGED that this pass is stalled, so the warning is
        # written to the record (log.txt + the report's embedded debug log) exactly
        # once per stall — on entry — not on every progress tick while it's stuck.
        # Flipped back off (with a recovery line) when real progress resumes.
        self._eta_stalled: bool = False
        # ETA trace kept "for posterity" (maintainer's ask): a throttled series of
        # samples, each pairing the PC wall-clock time with BOTH estimates —
        # cyanrip's own per-op ETA and our smoothed album ETA — so the report can
        # be compared against reality (the real elapsed/finish live in `timing`).
        # `_last_cyanrip_eta` is the most recent cyanrip reading (updated as its
        # progress lines stream); the trace is sampled in `_album_eta_text`.
        self._last_cyanrip_eta: str | None = None
        self._eta_trace: list[dict] = []
        self._last_eta_sample_monotonic: float = 0.0
        # The read speed (`-S`) in effect for the current pass (0 = drive max),
        # stamped into each ETA sample so the recorded curve is correlated with
        # speed — the raw material for a better ETA model later (maintainer's ask).
        self._current_read_speed: int = 0
        # The adaptive read-speed ladder's history: one SpeedAttempt per rip pass
        # (speed + -Z + whether it read clean). The GUI reads this at finish and
        # folds it into the report, so a disc that needed a slow re-read — or that
        # never read clean even at the floor — is recorded honestly, not hidden.
        self._speed_attempts: list[SpeedAttempt] = []
        # Track numbers whose secure re-read (-Z) never converged on the FINAL
        # pass — read instability we FLAG but (per policy) do not auto-re-rip. The
        # GUI reads this at finish for the report + results-pane caveat. Empty on
        # a clean disc.
        self._last_unstable_tracks: list[int] = []
        # Set true once a pass's log reveals the drive can't change read speed
        # (cyanrip aborts on `-S` for such a drive). Once locked, the ladder
        # escalates via `-Z` only and never sends `-S` again this rip.
        self._speed_locked: bool = False
        # Per-track auto-fix history: one dict per unstable track we re-ripped
        # alone with a harder -Z ({track, reripped_z, converged, replaced}). The
        # GUI folds this into the report and results pane. Empty when nothing was
        # re-ripped.
        self._retried_tracks: list[dict] = []
        # Why the dynamic secure re-rip did or didn't run (report's
        # read_speed.secure_rerip), so "why wasn't my shaky track re-ripped?" is
        # answerable from the JSON. `mode` is dynamic / uniform / off; `engaged`
        # is whether a secure re-rip actually happened (dynamic: a targeted
        # re-rip ran; uniform: -Z was applied to every track); `disc_in_ar` is
        # whether the disc was in AccurateRip (dynamic only); `skipped_reason`
        # explains a dynamic skip (e.g. the disc isn't in AccurateRip so a
        # targeted re-rip can't converge on a consensus). Set in start_rip.
        self._secure_rerip_mode: str = "off"
        self._secure_rerip_engaged: bool = False
        self._disc_in_accuraterip: bool | None = None
        self._secure_rerip_skipped_reason: str | None = None

    def _album_eta_text(self, overall_pct: float) -> str:
        """A smoothed, self-correcting album ETA suffix (" · about 25m left").

        Computed from actual elapsed and the album fraction done — so it absorbs
        secure re-read slowdowns instead of jumping like cyanrip's per-operation
        ETA. The raw projection is then **smoothed** (an EMA) and **coarsely
        rounded** (bigger buckets for bigger ETAs) so it reads as a steady
        estimate rather than a second-by-second jitter (real-user feedback). It's
        also the ONLY ETA the user sees — cyanrip's per-op "ETA - …" is stripped
        from the forwarded log lines (see the stream loop), so nothing contradicts
        this number. Returns "" during the ≤5% disc scan, before a few seconds
        have elapsed (any projection is noise then), and once effectively done.
        Never raises.
        """
        from platterpus.rip_timing import format_duration

        # Use the CURRENT pass's baseline (see _reset_pass_progress / #21): the
        # `overall` fraction resets each pass, so elapsed must be measured from
        # this pass's start, not the whole rip's. Fall back to the rip start.
        started = self._eta_pass_started or self._started_monotonic
        if started is None:
            return ""
        frac = overall_pct / 100.0
        # Skip the disc-scan band (0-5%) and the very end; both give noise.
        if frac <= 0.05 or frac >= 0.999:
            return ""
        now = time.monotonic()
        elapsed = now - started
        if elapsed < _MIN_ELAPSED_FOR_ETA_S:
            return ""
        # Stall detection FIRST — before any projection. Track when the album
        # fraction last cleared a meaningful forward step; if it hasn't for the
        # threshold, the drive is stuck on a hard-to-read spot (real hardware: a
        # track that hung for hours while the projection still counted down "~4h
        # left"). Say so plainly instead — honest and far more useful than a
        # misleading, ever-growing number. A tiny per-tick crawl doesn't reset the
        # timer (the step is what a healthy read clears in a second or two), so a
        # barely-moving read is caught, while a merely-slow-but-advancing one is
        # not. Note `frac > 0.05` already here (scan band skipped above).
        if (
            self._eta_stall_frac is None
            or frac >= self._eta_stall_frac + _ETA_STALL_MIN_PROGRESS
        ):
            # Real forward progress. If we were stalled, note the recovery in the
            # record (the transient status line can't be a durable record).
            if self._eta_stalled:
                log.info(
                    "rip recovered from stall at %.1f%% (track %s)",
                    overall_pct,
                    self._current_track,
                )
                self._eta_stalled = False
            self._eta_stall_frac = frac
            self._eta_stall_since = now
        elif (
            self._eta_stall_since is not None
            and now - self._eta_stall_since >= _ETA_STALL_THRESHOLD_S
        ):
            stalled_for = now - self._eta_stall_since
            # Record the stall ONCE (on entry) at WARNING, so it lands in both
            # log.txt (INFO+) and the report's embedded debug log regardless of the
            # Debug-logging setting — the status line alone is not a durable record
            # (maintainer's ask: "show up in either the log or json file").
            if not self._eta_stalled:
                self._eta_stalled = True
                log.warning(
                    "rip stalled: no forward progress for %s at %.1f%% (track %s) "
                    "— the drive is stuck on a hard-to-read spot",
                    format_duration(stalled_for),
                    overall_pct,
                    self._current_track,
                )
            return (
                f" · stalled {format_duration(stalled_for)} — the drive is stuck "
                "on a hard-to-read spot (a scratch or smudge)"
            )
        # Project the remaining time from the RECENT read rate (a trailing
        # window), not the cumulative average since the pass began. The fast
        # disc-scan phase and the disc's inner tracks read much faster than the
        # bulk, so a from-zero average let that fast start dominate and the early
        # ETA came out absurdly low. Collect (elapsed, frac) points — only past
        # the scan band, so the scan never enters the window — prune to the
        # window, and measure the rate over it.
        self._eta_rate_window.append((elapsed, frac))
        cutoff = elapsed - _ETA_RATE_WINDOW_S
        self._eta_rate_window = [p for p in self._eta_rate_window if p[0] >= cutoff]
        base_elapsed, base_frac = self._eta_rate_window[0]
        window_dt = elapsed - base_elapsed
        window_dfrac = frac - base_frac
        if window_dt > 0 and window_dfrac > 0:
            # remaining = remaining_fraction ÷ recent_rate (frac per second).
            raw_remaining = (1.0 - frac) * window_dt / window_dfrac
        else:
            # Only one distinct point so far (first post-scan tick) or a paused
            # bar (encode phase, no forward progress): fall back to the
            # cumulative projection until the window has real movement.
            raw_remaining = elapsed * (1.0 - frac) / frac
        if not raw_remaining >= 1:  # guards NaN/inf and sub-second "0s left"
            return ""
        # EMA-smooth so a per-tick swing doesn't yank the number around.
        if self._smoothed_remaining_s is None:
            self._smoothed_remaining_s = raw_remaining
        else:
            self._smoothed_remaining_s = (
                _ETA_SMOOTHING_ALPHA * raw_remaining
                + (1.0 - _ETA_SMOOTHING_ALPHA) * self._smoothed_remaining_s
            )
        display = _coarsen_eta_seconds(self._smoothed_remaining_s)
        if display < 1:
            return ""
        # Record a throttled trace sample (PC clock + both estimates) for the
        # report — this is the point where both are freshest. Best-effort.
        self._record_eta_sample(overall_pct, elapsed, display)
        return f" · about {format_duration(display)} left"

    def _record_cyanrip_eta(self, eta: str | None) -> None:
        """Remember cyanrip's most recent per-op ETA reading (raw string), for the
        posterity trace. A no-op when cyanrip's line carried no ETA."""
        if eta:
            self._last_cyanrip_eta = eta.strip()

    def _record_eta_sample(
        self, overall_pct: float, elapsed_s: float, our_eta_s: int
    ) -> None:
        """Append a throttled ETA-trace sample: PC wall-clock time + both
        estimates + progress, for the report's ``eta_trace``. Never raises."""
        try:
            now = time.monotonic()
            if self._eta_trace and (
                now - self._last_eta_sample_monotonic < _ETA_SAMPLE_INTERVAL_S
            ):
                return
            if len(self._eta_trace) >= _ETA_TRACE_MAX:
                return
            from datetime import datetime

            self._last_eta_sample_monotonic = now
            self._eta_trace.append(
                {
                    # The actual PC clock time of this sample (maintainer's ask).
                    "at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "elapsed_seconds": round(elapsed_s),
                    "overall_percent": round(overall_pct, 2),
                    # The read speed (`-S`) in effect (0 = drive max) — recorded
                    # so a future ETA model can correlate rate with speed.
                    "read_speed": self._current_read_speed,
                    # Our smoothed album estimate (seconds remaining).
                    "our_eta_seconds": our_eta_s,
                    # cyanrip's own per-op ETA at this moment (its raw string), or
                    # None if it hasn't printed one yet.
                    "cyanrip_eta": self._last_cyanrip_eta,
                    # The EVENT context, so a jump in the estimate can be tied to
                    # its cause (maintainer's ask): the track being worked on and
                    # the current phase text (e.g. "Reading track 2… 40%" vs
                    # "Encoding track 1…" vs a re-rip). This is why the estimate
                    # rose — e.g. finishing a fast track 1 and hitting a slow,
                    # re-read-heavy track 2.
                    "track": self._current_track or None,
                    "activity": self._last_status or None,
                }
            )
        except Exception:  # noqa: BLE001 — a diagnostic trace must never crash a rip
            log.exception("ETA-trace sample failed; skipping")

    @property
    def needs_unknown_retry(self) -> bool:
        """True if the rip failed because the ripper couldn't fetch online
        metadata (and this wasn't already an unknown-album rip). Inert with
        cyanrip, which never does its own lookup — kept for a networked backend."""
        return self._needs_unknown_retry

    @property
    def failure_hint(self) -> str:
        """An actionable failure explanation, or "" if the failure was generic.
        Set when the ripper gives up on an unreadable track."""
        return self._failure_hint

    @property
    def speed_attempts(self) -> list[SpeedAttempt]:
        """The adaptive read-speed ladder's per-pass history (empty on a normal
        single-pass rip). The GUI reads this at finish for the report."""
        return list(self._speed_attempts)

    @property
    def unstable_tracks(self) -> list[int]:
        """Track numbers still unstable after any auto-fix (their secure re-read
        never converged, and a per-track re-rip didn't fix them either). Flagged
        in the report + results pane. The GUI reads this at finish. Empty when the
        disc read clean or every unstable track was auto-fixed."""
        return list(self._last_unstable_tracks)

    @property
    def retried_tracks(self) -> list[dict]:
        """Per-track auto-fix history: which unstable tracks were re-ripped alone
        with a harder -Z, whether they then converged, and whether the improved
        FLAC replaced the original. The GUI folds this into the report + results
        pane. Empty when no track was re-ripped."""
        return list(self._retried_tracks)

    @property
    def eta_trace(self) -> list[dict]:
        """The "for posterity" ETA trace: throttled samples pairing the PC clock
        time with cyanrip's ETA and our smoothed album ETA. The GUI reads this at
        finish for the report. NOT the estimate shown live (that's the status)."""
        return list(self._eta_trace)

    @property
    def secure_rerip_report(self) -> dict | None:
        """Why the dynamic secure re-rip did/didn't run — the report's
        ``read_speed.secure_rerip``. None in plain ``off`` mode (nothing to
        explain); otherwise ``{mode, engaged, disc_in_accuraterip,
        skipped_reason}``. The GUI reads this at finish."""
        if self._secure_rerip_mode == "off":
            return None
        return {
            "mode": self._secure_rerip_mode,
            "engaged": self._secure_rerip_engaged,
            "disc_in_accuraterip": self._disc_in_accuraterip,
            "skipped_reason": self._secure_rerip_skipped_reason,
        }

    # --- Slots ---

    @Slot()
    def start_rip(self) -> None:
        """Begin the rip (QThread.started slot).

        BUG-2 belt: delegates to ``_run_rip`` inside a last-resort try/except so
        ANY unexpected error still emits ``finished(False, "")``. ``_run_rip``
        already emits ``finished`` on all of its own paths; this only fires if an
        exception escapes it (e.g. a filesystem race in log discovery). Without
        it, an un-emitted ``finished`` leaves the GUI's rip lock on forever —
        the drive keeps spinning and the UI is dead until an app restart.
        """
        try:
            self._run_rip()
        except Exception as exc:  # noqa: BLE001 — never leave the rip hung
            log.exception("rip aborted by an unexpected error")
            try:
                self.error.emit(f"rip aborted unexpectedly: {exc}")
            except Exception:  # noqa: BLE001 — even the error signal is best-effort
                log.exception("error signal emit failed during abort")
            self.finished.emit(False, "")

    def _run_rip(self) -> None:
        """The rip's main body: run the adaptive read-speed ladder — rip once,
        and — in ``auto_ladder`` mode — if the pass completed with unrecoverable
        read errors, re-rip the disc a rung slower (and, at the floor, with a
        higher ``-Z``), until it reads clean or the ladder is exhausted (then the
        disc is FLAGGED via the recorded attempts). A clean disc, or ``fixed``
        mode, is a single pass exactly as before — no regression. Each pass's
        speed/``-Z``/outcome is recorded in ``_speed_attempts`` for honest
        reporting. Emits ``finished`` on every normal path; ``start_rip`` wraps
        this so an unexpected escape still emits it (BUG-2).
        """
        # Stamp the wall-clock start once (album-ETA baseline spans all passes).
        self._started_monotonic = time.monotonic()
        # Real (epoch) start, used to scope log discovery to THIS rip: the output
        # dir is the shared music root, so a rip that fails before writing its own
        # log must not adopt a *previous album's* log sitting in a sibling folder
        # (#20). Every log this rip writes is newer than this instant.
        self._rip_started_at = time.time()

        auto_ladder = self._params.read_speed_mode == "auto_ladder"
        # Dynamic secure-rerip: rip the FIRST pass fast (no `-Z`) and secure only
        # the tracks that don't match AccurateRip afterwards (below). Only active
        # when the user both enabled it AND set a `-Z` level to use for the
        # targeted re-rip.
        dynamic_secure = (
            self._params.secure_rerip_dynamic and self._params.secure_rerip_matches > 0
        )
        # Record the secure-re-rip mode up front for the report (see
        # secure_rerip_report). Uniform mode applies `-Z` to every track on every
        # pass, so it's "engaged" the moment it starts; dynamic mode's engagement
        # is decided later (only if some track needs the targeted re-rip).
        if dynamic_secure:
            self._secure_rerip_mode = "dynamic"
        elif self._params.secure_rerip_matches > 0:
            self._secure_rerip_mode = "uniform"
            self._secure_rerip_engaged = True
        else:
            self._secure_rerip_mode = "off"
        # Starting rung: the ladder starts at the drive's max (0); a fixed mode
        # uses the configured speed for its single pass.
        speed = 0 if auto_ladder else self._params.read_speed
        # Pass 1's `-Z`: none in dynamic mode (fast single read — securing is done
        # selectively afterwards); otherwise the configured value on every track.
        secure_rerip = 0 if dynamic_secure else self._params.secure_rerip_matches

        success = False
        log_path_str = ""
        parsed_log: object | None = None
        attempt = 0
        while True:
            attempt += 1
            self._reset_pass_progress()
            # Remember this pass's speed so ETA samples are tagged with it.
            self._current_read_speed = speed
            outcome = self._rip_once(
                read_speed=speed, secure_rerip_matches=secure_rerip
            )
            if outcome is None:
                # A hard start/stream error already emitted `error`; stop here.
                self.finished.emit(False, "")
                return
            success, log_path_str = outcome
            if self._cancelled:
                break
            parsed_log = self._parse_log(log_path_str)
            # Whether this pass's log shows unrecoverable read errors — the ONLY
            # signal that triggers a step-down (below).
            had_read_errors = read_errors_present(parsed_log)
            # Read instability: tracks whose secure re-read (-Z) never converged.
            # These do NOT trigger the whole-disc step-down (escalation below keys
            # ONLY on `had_read_errors` — cyanrip's whole-disc error count stays 0
            # here). Instead they're handled AFTER the loop by the per-track
            # auto-fix (re-rip the track alone with a harder -Z; see
            # `_auto_fix_unstable_tracks`), and whatever it can't rescue is flagged
            # via the report's `unstable_tracks`.
            self._last_unstable_tracks = unstable_tracks(parsed_log)
            # Learn from this pass's log whether the drive can change read speed.
            # If it CAN'T, cyanrip aborts the whole rip when handed `-S`, so the
            # ladder must never send it — we lock the speed and escalate via `-Z`
            # only (real-hardware finding, 2026-07-01). Pass 1 always runs at max
            # (no `-S`), so an unchangeable drive is detected before any `-S` is
            # ever sent — the abort can't happen.
            info = getattr(parsed_log, "ripping_info", None)
            if getattr(info, "speed_changeable", None) is False:
                self._speed_locked = True
            # "Clean" means the pass completed (exit 0) and read without
            # unrecoverable errors. It deliberately does NOT fold in read
            # instability: an unstable track is handled separately (auto-fix, then
            # flagged via the report's `unstable_tracks`), so `unresolved` is
            # computed from the POST-auto-fix unstable set — otherwise a track the
            # auto-fix rescued would still read as unresolved. A hard failure
            # (non-zero exit) is NOT clean even if its log shows no read-error line
            # (review-confirmed bug).
            clean = success and not had_read_errors
            self._speed_attempts.append(
                SpeedAttempt(attempt, speed, secure_rerip, clean=clean)
            )
            # Escalate only in auto_ladder mode, only on a pass that COMPLETED
            # with unrecoverable read errors (not a hard crash — re-ripping a
            # broken drive/disc just burns time; not mere instability — see
            # above), and only while the ladder + hard cap allow.
            if (
                not (auto_ladder and success and had_read_errors)
                or attempt >= MAX_ATTEMPTS
            ):
                break
            step = next_step(
                current_speed=speed,
                current_secure_rerip=secure_rerip,
                speed_locked=self._speed_locked,
                # The user's -Z is the ceiling when they set one — the ladder never
                # escalates beyond the number they picked. When they left it at the
                # default 0 (no secure re-rip requested), the read-error recovery
                # still needs SOME -Z to try, so fall back to the small internal
                # recovery bound (MAX_SECURE_REREP — the "like 10" cap the user
                # explicitly allowed). `0 or MAX_SECURE_REREP` == MAX_SECURE_REREP.
                max_secure_rerip=self._params.secure_rerip_matches or MAX_SECURE_REREP,
            )
            if step is None:
                # Floor + -Z exhausted — stop and leave the disc FLAGGED
                # (unresolved in the report). Quality never went DOWN.
                log.warning("read-speed ladder exhausted; disc still has read errors")
                break
            speed, secure_rerip = step.speed, step.secure_rerip_matches
            self.status.emit(f"Read errors — {step.reason}…")
            self.log_line.emit(f"[read-speed ladder] {step.reason}")

        # Post-rip targeted secure re-rip: re-rip just the track(s) that need it
        # (via cyanrip's -l, into a temp dir — the album's whole-disc log/cue stay
        # intact, only an improved FLAC is copied in), keeping a re-read only if it
        # now converges. Two triggers, decided by mode (they never overlap):
        #   • dynamic mode → the fast first pass had no -Z, so secure the tracks
        #     that didn't match AccurateRip, at the CONFIGURED -Z level;
        #   • else auto_ladder → a -Z pass left an unstable track (never converged),
        #     so re-read it HARDER (escalate to the -Z ceiling).
        # Neither can make a track worse; skipped entirely in plain fixed mode.
        if success and not self._cancelled:
            if dynamic_secure:
                # Dynamic mode: secure the AccurateRip-failing tracks at the user's
                # configured -Z. The `dynamic_secure` gate already guarantees
                # secure_rerip_matches > 0, so this is always a real -Z. Their
                # number is the max — we never invent a harder value.
                #
                # BUT only when the disc is actually in the AccurateRip DB: for a
                # disc that's NOT in the DB (a CD-R, an obscure pressing — every
                # track "fails" AR because there's nothing to match), there's no
                # consensus to converge toward, so a targeted re-rip can't produce
                # a match — it would just re-rip and swap EVERY track, a full
                # wasted second pass (the "20min → 1h" slowdown dynamic mode
                # exists to avoid). Skip it; the fast first pass stands, flagged
                # as not-verified. (An in-DB disc where a *few* tracks failed is
                # the real dynamic case and still re-rips just those.)
                self._disc_in_accuraterip = disc_in_accuraterip(parsed_log)
                if self._disc_in_accuraterip:
                    to_fix = tracks_failing_accuraterip(parsed_log)
                else:
                    to_fix = []
                    self._secure_rerip_skipped_reason = "disc_not_in_accuraterip"
                    self.log_line.emit(
                        "[secure re-rip] disc is not in AccurateRip — keeping the "
                        "fast read (a re-rip can't verify against a DB that has no "
                        "entry for this disc)."
                    )
                    log.info("dynamic secure re-rip skipped: disc not in AccurateRip")
                # Engaged only when there's actually a track to secure (every
                # track matching AccurateRip on the fast read is already proven).
                self._secure_rerip_engaged = bool(to_fix)
                trigger = "accuraterip"
                rerip_z = self._params.secure_rerip_matches
            elif auto_ladder:
                # Recovery: an unstable track (a -Z pass that never converged) is
                # re-read alone HARDER. It NEEDS a -Z to converge, so use the user's
                # configured ceiling when they set one, else the internal recovery
                # bound (they may have left -Z at 0 while still wanting a shaky
                # track rescued — that's what auto_ladder mode is for).
                to_fix = list(self._last_unstable_tracks)
                trigger = "instability"
                rerip_z = self._params.secure_rerip_matches or MAX_SECURE_REREP
            else:
                to_fix = []
                trigger = ""
                rerip_z = 0
            if to_fix:
                self._auto_fix_tracks(
                    to_fix, rerip_z, trigger, album_log_path=log_path_str
                )

        if success:
            # Peg both bars at 100% so a finished rip never leaves the
            # overall bar short of full (the post-rip AccurateRip phase
            # has no reliable percentage of its own).
            self.progress.emit(100.0, 100.0)
        self.finished.emit(success, log_path_str)

    def _rip_once(
        self,
        *,
        read_speed: int,
        secure_rerip_matches: int,
        output_dir: Path | None = None,
        only_tracks: tuple[int, ...] = (),
    ) -> tuple[bool, str] | None:
        """Run ONE rip pass at the given speed/``-Z``; stream its output.

        Returns ``(success, log_path_str)`` for a completed pass, or None on a
        hard start/stream error (having already emitted ``error``) so the caller
        stops the whole rip. Emits log/progress/status/current_track exactly as
        the single-pass rip always did.

        ``output_dir`` overrides where the rip writes (defaults to the params'
        dir); ``only_tracks`` re-rips just those tracks (cyanrip ``-l``). Both are
        used by the per-track auto-fix, which re-rips an unstable track into a
        temp dir so the album's whole-disc log/cue are left intact.
        """
        out_dir = output_dir or self._params.output_dir
        # Only the MAIN rip passes snapshot an incremental report — never the
        # throwaway auto-fix temp rip (output_dir set). See _write_incremental_report.
        incremental = output_dir is None
        try:
            self._handle = self._backend.rip(
                drive=self._params.drive,
                release_id=self._params.release_id,
                output_dir=out_dir,
                track_template=self._params.track_template,
                disc_template=self._params.disc_template,
                unknown=self._params.unknown,
                cover_art=self._params.cover_art,
                max_retries=self._params.max_retries,
                secure_rerip_matches=secure_rerip_matches,
                read_offset_override=self._params.read_offset_override,
                metadata=self._params.metadata,
                read_speed=read_speed,
                only_tracks=only_tracks,
            )
        except RipError as exc:
            log.exception("rip failed to start")
            self.error.emit(str(exc))
            return None
        except Exception as exc:  # noqa: BLE001 — last-resort guard
            log.exception("unexpected error starting rip")
            self.error.emit(f"unexpected error: {exc}")
            return None

        # Close the startup-window cancel race: if cancel() arrived while
        # backend.rip() was still spawning the subprocess — before _handle was
        # assigned — it could only flip the flag (it found _handle is None).
        # Now that we hold the handle, honour the pending cancel by stopping the
        # subprocess; otherwise the loop below would break on the flag but
        # self._handle.wait() would block on a still-running rip ("Cancel did
        # nothing" until the 5s force-stop backstop fired).
        if self._cancelled:
            try:
                self._handle.terminate()
            except Exception:  # noqa: BLE001 — cancel is best-effort
                log.exception("startup-window terminate() raised; ignored")

        # Stream output. Iteration ends when the ripper closes its stdout
        # (i.e. exits) or when cancel() flips the flag.
        try:
            for line in self._handle.log_lines():
                if self._cancelled:
                    break
                # `_progress_for` both classifies the line (a numeric progress
                # redraw → not None) AND updates `_current_track` as a side
                # effect, so call it once up front.
                prog = self._progress_for(line)
                is_progress = prog is not None
                # Forward the line to the GUI's log pane — but RATE-LIMIT the
                # high-frequency progress redraws. Appending to the log widget
                # (text layout + repaint) is the expensive per-tick work; at
                # cyanrip's redraw rate it floods the event loop and starves
                # repaints, so the window goes black when overlapped (real-user
                # report, 2026-06-27). The bar/status/track signals below are
                # cheap and stay unthrottled, so the progress bar still moves
                # smoothly even when the log pane updates only ~10×/second.
                now = time.monotonic()
                if is_progress:
                    if now - self._last_progress_emit >= _PROGRESS_MIN_INTERVAL_S:
                        self._last_progress_emit = now
                        # Strip cyanrip's own trailing "ETA - …" so the log pane
                        # never shows an ETA that contradicts our smoothed album
                        # ETA in the status line (real-user report). Detection
                        # below still uses the raw `line`.
                        self.log_line.emit(_CYANRIP_ETA_CLAUSE.sub("", line))
                else:
                    self.log_line.emit(line)
                # Watch for the "no online metadata" abort so the GUI can heal
                # by re-ripping as unknown (only worth it if this rip wasn't
                # already unknown). Inert whipper-era seam — cyanrip runs -N and
                # never emits these markers. Detection runs on EVERY line.
                if not self._params.unknown and any(
                    m in line for m in _NO_METADATA_MARKERS
                ):
                    self._needs_unknown_retry = True
                giveup = _TRACK_GIVEUP_RE.search(line)
                if giveup:
                    track = giveup.group("track")
                    self._failure_hint = (
                        f"Track {track} couldn't be read after repeated tries. "
                        "The disc may be scratched or dirty — clean it and try "
                        "again."
                    )
                # Status text first (covers the pre-track disc scan and
                # the encode/tag sub-phases), then the numeric progress
                # that drives the bar.
                desc = _describe_activity(line)
                # Append our own smoothed album ETA to a progress phase (never
                # cyanrip's per-op ETA — see _album_eta_text / _describe_activity).
                if desc is not None and prog is not None:
                    desc += self._album_eta_text(prog[0])
                if desc is not None and desc != self._last_status:
                    self._last_status = desc
                    self.status.emit(desc)
                if prog is not None:
                    self.progress.emit(prog[0], prog[1])
                # _progress_for updates _current_track as a side effect when
                # it sees a per-track progress line. Emit once per new track so
                # the GUI can highlight the row the ripper is on.
                if self._current_track and self._current_track != self._emitted_track:
                    self._emitted_track = self._current_track
                    self.current_track.emit(self._current_track)
                # Incremental report snapshot: each time cyanrip finishes a track
                # it appends that track's summary to its .log; re-parse it and
                # re-write a PARTIAL .platterpus.json beside it. This closes the
                # last durability gap — a HARD stop (power loss, SIGKILL, an OS
                # crash) that never reaches the GUI's finish handler still leaves
                # the tracks completed so far on disk. A clean cancel/finish is
                # still written by the GUI afterward, superseding these partials.
                if incremental and _CYANRIP_TRACK_DONE.search(line):
                    self._write_incremental_report(out_dir)
        except Exception as exc:  # noqa: BLE001
            log.exception("error reading ripper stdout")
            # The subprocess is still running (we broke out of the read loop
            # abnormally, before wait()). Stop it so it doesn't keep holding the
            # drive and contend with a retry — best-effort, non-blocking.
            try:
                self._handle.terminate()
            except Exception:  # noqa: BLE001 — cleanup is best-effort
                log.exception("terminate() after stream error raised; ignored")
            self.error.emit(f"rip stream error: {exc}")
            return None

        exit_code = self._handle.wait()
        success = (exit_code == 0) and not self._cancelled
        log_path = self._find_log_path(out_dir, since=self._rip_started_at)
        return success, str(log_path) if log_path else ""

    def _write_incremental_report(self, out_dir: Path) -> None:
        """Snapshot a PARTIAL ``.platterpus.json`` after a track completes.

        The FULL report is written by the GUI at finish (success or cancel). This
        fills the one remaining durability gap — a hard stop that never reaches
        that handler (power loss, SIGKILL, an OS crash) — by re-writing the report
        beside the growing cyanrip ``.log`` as each track lands, so whatever
        completed is always on disk. Its ``outcome.status`` is ``"in_progress"``;
        the GUI overwrites it with the real status when the rip actually ends.

        Runs on the WORKER thread (never the GUI thread — it does file I/O), is
        atomic (temp + ``os.replace``, inside ``write_report``), and is
        best-effort: a diagnostic snapshot must never crash the rip. No-op until
        cyanrip has written its log (nothing to snapshot yet).
        """
        from datetime import datetime

        from platterpus.rip_report import build_outcome, build_timing, write_report

        try:
            log_path = self._find_log_path(out_dir, since=self._rip_started_at)
            if log_path is None:
                return  # cyanrip hasn't written its .log yet — nothing to snapshot
            parsed = self._parse_log(str(log_path))
            if parsed is None:
                return
            elapsed = (
                time.monotonic() - self._started_monotonic
                if self._started_monotonic is not None
                else None
            )
            started_iso = (
                datetime.fromtimestamp(self._rip_started_at)
                .astimezone()
                .isoformat(timespec="seconds")
                if self._rip_started_at
                else ""
            )
            write_report(
                parsed,
                log_path,
                outcome=build_outcome(status="in_progress"),
                timing=build_timing(elapsed, started_at=started_iso),
                eta_trace=self.eta_trace,
                secure_rerip=self.secure_rerip_report,
                generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            )
        except Exception:  # noqa: BLE001 — a partial snapshot must never crash a rip
            log.exception("incremental report snapshot failed; continuing rip")

    def _reset_pass_progress(self) -> None:
        """Reset the per-pass progress state before a (re-)rip pass, so a re-rip's
        bar sweeps fresh from 0 instead of inheriting the previous pass's value."""
        self._overall = 0.0
        self._current_track = 0
        self._emitted_track = 0
        self._last_status = ""
        self._last_progress_emit = 0.0
        # Re-baseline the ETA to THIS pass and drop the previous pass's smoothed
        # value: `overall` just reset to 0, so an ETA built from the whole-rip
        # elapsed would project a wildly inflated remaining time on pass 2+ (#21).
        self._eta_pass_started = time.monotonic()
        self._smoothed_remaining_s = None
        self._eta_rate_window = []
        self._eta_stall_frac = None
        self._eta_stall_since = None
        self._eta_stalled = False

    def _auto_fix_tracks(
        self,
        tracks: list[int],
        rerip_z: int,
        trigger: str,
        album_log_path: str = "",
    ) -> None:
        """Re-rip the given track(s) ALONE with ``-Z rerip_z``, keeping a re-read
        only if it now reads consistently (converges).

        ``trigger`` records WHY each track was re-ripped, for the report:
        ``"instability"`` (a -Z pass never converged) or ``"accuraterip"`` (dynamic
        mode — the fast first pass didn't match the AccurateRip database).

        ``album_log_path`` is the whole-disc log from the first pass. When a
        re-rip is swapped in, that log's recorded CRC for the track is now the
        *old* bytes' — so we append a truthful swap addendum with the shipped
        file's CRC, keeping the committed "durable proof" text consistent with
        the audio actually on disk (#19). The original log content is preserved
        verbatim; we only append.

        Cheap (cyanrip's ``-l`` rips just the listed tracks), needs no speed change
        (so it works on a speed-locked drive), and **can never make a track worse**
        — a track is only ever replaced by a *converged* re-read; on any failure or
        uncertainty the original is left untouched. The re-rip runs in a throwaway
        temp dir so the album's whole-disc ``.log`` / ``.cue`` stay intact; only an
        improved FLAC is copied into the album. Whatever couldn't be made to
        converge is left as ``unstable_tracks`` (flagged, never papered over).

        **HARDWARE-GATED:** the re-rip-and-swap path has not been exercised on a
        real drive yet. It's safe by construction (no swap unless the re-read
        converges and the file copies cleanly), but flag it for validation on the
        Bazzite + BDR-209D rig. Best-effort: never raises (would abort the rip).
        """
        import shutil
        import tempfile

        tracks = list(tracks)
        if not tracks or rerip_z <= 0:
            return
        listed = ", ".join(str(n) for n in tracks)
        why = (
            "didn't match AccurateRip"
            if trigger == "accuraterip"
            else "didn't read consistently"
        )
        self._reset_pass_progress()
        self.status.emit(f"Re-ripping track(s) {listed} ({why}) to secure them…")
        self.log_line.emit(
            f"[auto-fix] re-ripping track(s) {listed} at -Z {rerip_z} — they "
            f"{why} (the rest of the album is kept as-is)"
        )
        tmp_root: Path | None = None
        try:
            tmp_root = Path(tempfile.mkdtemp(prefix="platterpus-refix-"))
            # Never send -S: the speed lever is unreliable / aborts on some drives,
            # and -Z at max speed is the mechanism that actually helps here.
            self._current_read_speed = 0
            outcome = self._rip_once(
                read_speed=0,
                secure_rerip_matches=rerip_z,
                output_dir=tmp_root,
                only_tracks=tuple(tracks),
            )
            if outcome is None:
                return  # re-rip failed to start/stream — originals untouched
            success, rerip_log_path = outcome
            if not success or not rerip_log_path:
                return
            rerip_log = self._parse_log(rerip_log_path)
            fixed: list[int] = []
            # (track number, filename, new CRC) for each track actually swapped —
            # used to append the log addendum so the album .log's CRCs stay honest.
            swapped: list[tuple[int, str, str]] = []
            for track in getattr(rerip_log, "tracks", ()) or ():
                number = getattr(track, "number", None)
                if number not in tracks:
                    continue
                converged = getattr(track, "secure_rerip_converged", None) is True
                replaced = False
                if converged:
                    replaced = self._swap_in_reripped_track(track, tmp_root)
                    if replaced:
                        fixed.append(number)
                        new_crc = getattr(track, "copy_crc", "") or getattr(
                            track, "test_crc", ""
                        )
                        swapped.append(
                            (number, getattr(track, "filename", "") or "", new_crc)
                        )
                self._retried_tracks.append(
                    {
                        "track": number,
                        "trigger": trigger,
                        "reripped_z": rerip_z,
                        "converged": converged,
                        "replaced": replaced,
                    }
                )
            # Whatever we couldn't get to converge stays flagged as unstable
            # (a genuinely unreadable-consistently track — dynamic mode adds these,
            # the -Z path narrows its set). A converged read — even one that still
            # doesn't match the DB (a rare pressing) — is the best possible and is
            # NOT called unstable.
            self._last_unstable_tracks = [t for t in tracks if t not in fixed]
            if fixed:
                names = ", ".join(str(n) for n in fixed)
                self.log_line.emit(
                    f"[auto-fix] track(s) {names} now read consistently — kept the "
                    "re-rip."
                )
                self.status.emit(f"Auto-fixed track(s) {names}.")
                # Keep the durable-proof log honest: the swapped-in files no longer
                # match the CRCs the first-pass log recorded for them.
                self._append_swap_addendum(album_log_path, trigger, swapped)
        except Exception:  # noqa: BLE001 — auto-fix must never crash the rip
            log.exception("auto-fix re-rip failed; originals kept")
        finally:
            if tmp_root is not None:
                shutil.rmtree(tmp_root, ignore_errors=True)

    def _append_swap_addendum(
        self,
        album_log_path: str,
        trigger: str,
        swapped: list[tuple[int, str, str]],
    ) -> None:
        """Append a truthful swap addendum to the whole-disc album ``.log``.

        After the auto-fix replaces a track's FLAC with a converged re-read, the
        first-pass log's CRC for that track describes the *discarded* bytes, not
        the file now on disk — so the committed proof text would misrepresent the
        shipped audio (#19). We append a clearly-delimited block that names each
        swapped track and the shipped file's CRC, superseding the value above.
        The original log is preserved verbatim (append-only). Best-effort: a
        write failure is logged and swallowed — it must never abort the rip, and
        the ``.platterpus.json`` report's ``retried_tracks`` is the structured
        record regardless.
        """
        if not album_log_path or not swapped:
            return
        why = (
            "didn't match AccurateRip on the first pass"
            if trigger == "accuraterip"
            else "didn't read consistently on the first pass"
        )
        lines = [
            "",
            "=" * 72,
            "[Platterpus auto-fix addendum]",
            "The whole-disc log above records the FIRST read pass. The track(s)",
            f"below {why} and were re-ripped to secure them; the improved read was",
            "swapped in. Each CRC below is the SHIPPED file's and supersedes the",
            "value recorded for that track above.",
        ]
        for number, filename, crc in swapped:
            shown = filename or f"track {number}"
            lines.append(f"  Track {number} ({shown}): CRC {crc or 'n/a'}")
        lines.append("=" * 72)
        try:
            with Path(album_log_path).open("a", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + "\n")
        except OSError:
            log.exception("could not append auto-fix addendum to %s", album_log_path)

    def _swap_in_reripped_track(self, track: object, tmp_root: Path) -> bool:
        """Atomically replace the album's original FLAC with a converged re-rip.

        The re-rip used the SAME naming templates + metadata, so its per-track
        filename (relative, from the re-rip log) maps to the same relative path
        under the album's output dir. The copy goes to a sibling temp file which
        is then ``os.replace``d into place — an ATOMIC swap, so a crash or
        disk-full mid-copy can never leave a truncated (corrupt) archival master
        where a good one was. Returns True on success; False (no change, temp
        cleaned up) if the source is missing or the copy fails — never raises.
        """
        import os
        import shutil

        filename = getattr(track, "filename", "") or ""
        if not filename:
            return False
        src = tmp_root / filename
        dst = self._params.output_dir / filename
        if not src.exists():
            return False
        tmp = dst.with_name(dst.name + ".platterpus-refix.tmp")
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tmp)
            os.replace(tmp, dst)  # atomic: dst is never a partial file
            return True
        except OSError:
            log.exception("auto-fix: could not swap in re-ripped %s", filename)
            # Best-effort cleanup of a partial temp so a failed swap leaves
            # nothing behind (the original master is untouched either way).
            try:
                tmp.unlink()
            except OSError:
                pass
            return False

    def _parse_log(self, log_path_str: str) -> object | None:
        """Parse a rip log for the escalation decision. Never raises (parsers
        don't, and a missing/unreadable file just yields None → 'no errors')."""
        if not log_path_str:
            return None
        from platterpus.parsers.cyanrip_log import (
            looks_like_cyanrip_log,
            parse_cyanrip_log,
        )
        from platterpus.parsers.rip_log import parse_rip_log

        try:
            text = Path(log_path_str).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        return (
            parse_cyanrip_log(text)
            if looks_like_cyanrip_log(text)
            else parse_rip_log(text)
        )

    @Slot()
    def cancel(self) -> None:
        """Cancel an in-progress rip — NON-BLOCKING (safe from the GUI thread).

        Sets the cancel flag (read by the worker's iteration loop) and sends a
        non-blocking SIGTERM via ``terminate()`` — it never waits, so a wedged
        drive can't freeze the caller. The worker's own ``wait()`` (on the worker
        thread) reaps the terminated process; if the ripper ignores SIGTERM, the
        GUI's force-stop timer escalates to a SIGKILL off the GUI thread. Both the
        flag write and ``terminate()`` are thread-safe (atomic bool; subprocess
        signalling is), so this is safe to call from the GUI thread.
        """
        self._cancelled = True
        if self._handle is not None:
            try:
                self._handle.terminate()
            except Exception:  # noqa: BLE001
                log.exception("terminate() raised; ignored")

    # --- Internals ---

    def _progress_for(self, line: str) -> tuple[float, float] | None:
        """Map a ripper stdout line to (overall, task) percentages.

        Handles cyanrip's progress lines (the live backend) and, as an inert
        seam, the whipper log format.

        The rip is split into three overall bands so the overall bar
        advances smoothly start-to-finish instead of resetting per track:
          * disc scan (Reading TOC/table)        → 0–5%
          * per-track read/verify (N of M)       → 5–95%
          * post-rip length/AccurateRip checks   → 95–100%
        The task percentage is the current operation's own 0–100%.
        Returns None for lines with no usable percentage (e.g. the
        encode/tag sub-phases) — the status label covers those, and the
        task bar simply holds its last value.
        """
        match = _DISC_SCAN_PATTERN.search(line)
        if match:
            task = float(match.group("pct"))
            return self._bump_overall(task * 0.05), task

        match = _TRACK_PHASE_PATTERN.search(line)
        if match:
            self._current_track = int(match.group("track"))
            self._total_tracks = int(match.group("total"))
            task = float(match.group("pct"))
            return self._bump_overall(
                self._overall_from_track(self._current_track, task)
            ), task

        match = _LENGTH_PHASE_PATTERN.search(line)
        if match:
            done = int(match.group("track"))
            total = int(match.group("total"))
            frac = done / total if total else 1.0
            return self._bump_overall(95.0 + frac * 5.0), 100.0

        # --- cyanrip lines (mutually exclusive with whipper's formats) ---

        match = _CYANRIP_DISC_TRACKS.search(line)
        if match:
            # Total learned from the start report; no bar movement yet.
            self._total_tracks = int(match.group("total"))
            return None

        match = _CYANRIP_TRACK_PROGRESS.search(line)
        if match:
            self._current_track = int(match.group("track"))
            self._record_cyanrip_eta(match.group("eta"))
            task = float(match.group("pct"))
            return self._bump_overall(
                self._overall_from_track(self._current_track, task)
            ), task

        match = _CYANRIP_TRACK_DONE.search(line)
        if match:
            done = int(match.group("track"))
            # task=100 → the end of this track's slice (its full length consumed).
            return self._bump_overall(self._overall_from_track(done, 100.0)), 100.0

        return None

    def _overall_from_track(self, current_track: int, task_pct: float) -> float:
        """Map (track, within-track %) to an overall 0-100 bar value in the 5-95%
        read band.

        When per-track MusicBrainz durations are known for the whole disc
        (``self._track_ms``), each track's slice of the band is proportional to
        its real length, so the bar advances with *audio position* — which, at a
        steady read speed, is ~linear with wall-clock, so the elapsed÷fraction ETA
        stops oscillating between long and short tracks. Without usable durations
        (unknown disc, partial metadata), falls back to today's equal-per-track
        slices. Pure; never raises (guards a zero total)."""
        total = self._total_tracks
        weighted_ok = (
            self._track_ms_total > 0
            and total > 0
            and len(self._track_ms) == total
            and 1 <= current_track <= total
        )
        if weighted_ok:
            before = self._track_ms_prefix[current_track]
            cur = self._track_ms[current_track]
            frac = (before + (task_pct / 100.0) * cur) / self._track_ms_total
        elif total:
            frac = ((current_track - 1) + task_pct / 100.0) / total
        else:
            frac = 0.0
        return 5.0 + frac * 90.0

    def _bump_overall(self, value: float) -> float:
        """Clamp `value` to [0, 100] and never let the overall bar regress."""
        self._overall = max(self._overall, min(value, 100.0))
        return self._overall

    def _find_log_path(
        self, output_dir: Path | None = None, since: float | None = None
    ) -> Path | None:
        """Locate the .log the ripper just wrote under `output_dir`.

        The ripper drops the rip log next to the FLACs. We search the given root
        (defaults to the params' output dir; the auto-fix re-rip passes its temp
        dir) recursively for the most recent .log. Returns None if nothing was
        written (e.g. rip failed before any output).

        `since` (a wall-clock time from just before the pass started) scopes the
        search to logs this pass could have written: the params' output dir is
        the *shared* music root, so a rip that fails before writing its own log
        would otherwise pick up a **previous album's** log sitting in a sibling
        folder and parse it as this rip's (#20). We keep only logs modified at or
        after `since` (minus a small slack for coarse mtime resolution); a
        genuine just-written log is always many seconds newer, an older album's
        log is filtered out. Without `since`, behaviour is unchanged.
        """
        output_dir = output_dir or self._params.output_dir
        if not output_dir.exists():
            return None

        # BUG-2: stat EACH candidate exactly once, guarded — a `.log` can vanish
        # between the rglob and the read (a concurrent cleanup, a temp-dir sweep).
        # Both the `since` filter AND the recency sort need the mtime; doing the
        # stat once in a guarded pass means a file that disappears mid-scan is
        # simply skipped, never a `FileNotFoundError` escaping into start_rip's
        # loop (which would leave `finished` un-emitted and the rip lock stuck).
        cutoff = None if since is None else since - _LOG_MTIME_SLACK_S
        scored: list[tuple[float, Path]] = []
        for path in output_dir.rglob("*.log"):
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue  # vanished / unreadable mid-scan — skip it
            if cutoff is not None and mtime < cutoff:
                continue
            scored.append((mtime, path))
        if not scored:
            return None
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[0][1]


def _describe_activity(line: str) -> str | None:
    """Return a short human status for a ripper progress line, or None.

    Matches cyanrip's progress lines (and the inert whipper-format seam). Used
    to keep the status label live across every phase — especially the pre-track
    disc scan, which otherwise left the GUI on "Starting rip…" for a minute-plus
    and looked hung.
    """
    match = _DISC_SCAN_PATTERN.search(line)
    if match:
        what = "disc TOC" if match.group("what") == "TOC" else "disc table"
        return f"Reading {what}… {match.group('pct')}%"

    match = _TRACK_PHASE_PATTERN.search(line)
    if match:
        return (
            f"{match.group('verb')} track {match.group('track')} "
            f"of {match.group('total')}… {match.group('pct')}%"
        )

    match = _LENGTH_PHASE_PATTERN.search(line)
    if match:
        return f"Checking track {match.group('track')} of {match.group('total')}…"

    match = _CYANRIP_TRACK_PROGRESS.search(line)
    if match:
        pct = float(match.group("pct"))
        # Always "Ripping" — cyanrip's own verb, and the app's. cyanrip reads AND
        # encodes a track in ONE pass ("Ripping and encoding track N"), so calling
        # that "Encoding" was actively misleading: encoding FLAC is near-instant,
        # the minutes are the disc READ, yet a real user watched "Encoding
        # track 1… 7%" crawl for a whole ~1× secure read and reasonably wondered
        # why encoding was so slow (real-hardware finding — the Police rip's trace
        # showed "Encoding track N" for all 59 minutes). Using one honest verb for
        # BOTH progress forms also stops the label flickering between
        # "Reading"/"Encoding" as cyanrip interleaves the read and read+encode
        # lines. cyanrip's own per-op ETA is still dropped here (it resets every
        # phase and is wildly wrong early — it once printed "822h"); the run loop
        # appends our own smoothed album ETA instead.
        return f"Ripping track {match.group('track')}… {pct:.0f}%"

    match = _CYANRIP_TRACK_DONE.search(line)
    if match:
        outcome = "✓" if match.group("how") == "successfully" else "with errors"
        return f"Track {match.group('track')} done {outcome}"

    for phrase, friendly in _NAMED_PHASES.items():
        if phrase in line:
            return friendly
    return None
