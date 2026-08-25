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
import math
import re
import subprocess
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from platterpus import diagnostics
from platterpus.adapters.rip_backend import (
    RipBackend,
    RipError,
    RipHandle,
    RipMetadata,
)
from platterpus.adapters.ripper_log_verify import FAILED as RIPPER_LOG_FAILED
from platterpus.adapters.ripper_log_verify import LogVerification
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
from platterpus.rip_addendum import (
    SupersededTrack,
    read_log_with_addendum,
    write_addendum,
)
from platterpus.rip_plan import describe_rip_plan
from platterpus.ripper_message_inventory import ALL_FORMATS
from platterpus.ripper_messages import build_matcher
from platterpus.safe_int import int_or_none

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
    # cyanrip's `-O`: read into the disc's lead-in/lead-out instead of
    # zero-padding the offset-shifted edge samples. Opt-in and
    # drive-dependent (upstream: "may freeze if unsupported by drive").
    force_overread: bool = False
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
    # How many tracks the DISC's TOC reports. Handed to the backend so it can
    # refuse to pass cyanrip a `-t` for a track that does not exist: cyanrip
    # rejects the entire rip on an out-of-range track number, which cost a real
    # rip on the rig (2026-08-02). None means "unknown", and the guard then
    # stays out of the way rather than guessing a ceiling.
    disc_track_total: int | None = None
    # The GUI's already-fetched album/track tags (track table content),
    # fed to cyanrip via -a/-t so the rip needs no in-container network.
    metadata: RipMetadata | None = None
    # User-chosen subset of 1-based track numbers to rip (the track table's
    # "Rip?" checkboxes). Empty = rip the whole disc (the common case); a
    # non-empty tuple becomes cyanrip's `-l` so only those tracks are read.
    only_tracks: tuple[int, ...] = ()
    # Opt-in (Settings): in dynamic secure-rerip mode, also re-read tracks that
    # only got an offset-variant ("partially accurate") AccurateRip match, until
    # `-Z` reads agree — so an offset-variant track with an unstable read
    # converges on a reproducible one. Off by default (an offset-variant match is
    # accepted on the fast read, as before). Real-hardware finding, 2026-07-23.
    rerip_offset_variant: bool = False


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
_DISC_SCAN_PATTERN = re.compile(r"Reading (?P<what>TOC|table)\s+(?P<pct>\d{1,3})\s*%")
_TRACK_PHASE_PATTERN = re.compile(
    r"(?P<verb>Reading|Verifying) track (?P<track>\d{1,4}) of (?P<total>\d{1,4})"
    r".*?(?P<pct>\d{1,3})\s*%"
)
_LENGTH_PHASE_PATTERN = re.compile(
    r"Getting length of audio track \((?P<track>\d{1,4}) of (?P<total>\d{1,4})\)"
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
    r"Ripping(?P<encoding> and encoding)? track (?P<track>\d{1,4}), progress - "
    r"(?P<pct>\d{1,3}(?:\.\d{1,4})?)%(?:, ETA - (?P<eta>[^,]+))?"
)
# Per-track completion ("Track 5 ripped and encoded successfully!" / "with
# errors.") — pegs that track's slice of the overall bar.
_CYANRIP_TRACK_DONE = re.compile(
    r"^Track (?P<track>\d{1,4}) ripped and encoded (?P<how>successfully|with errors)"
)
# The start report carries the track total ("Disc tracks:    16") — cyanrip's
# progress lines don't repeat it, so we capture it here for the overall bar.
_CYANRIP_DISC_TRACKS = re.compile(r"^Disc tracks:\s+(?P<total>\d{1,4})\s*$")

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
# cyanrip's own fatal-argument / fatal-setup errors, which it prints and then
# exits on. Deliberately narrow: these are the shapes that end a rip before any
# audio is read, so surfacing one verbatim is strictly better than "Rip failed."
# Bounded quantifiers per the never-unbounded rule.
#
# WIDENED 2026-08-02. The fork session enumerated cyanrip's fatal `cyanrip_log`
# call sites and measured that the six prefixes above matched **24 of 45** of
# them. The other 21 printed a precise diagnosis that the user never saw: the
# report's `failure_hint` was null and the window said "Rip failed."
#
# "Deliberately narrow" was the wrong instinct here, and worth naming because it
# is a tempting one. The cost of a MISS is a user staring at "Rip failed" with
# the answer sitting in a buffer we captured and did not read. The cost of a
# FALSE POSITIVE is one extra sentence of the ripper's own words in a hint —
# which is, at worst, mildly confusing, and is shown only on a rip that already
# failed. Those costs are not close, so the pattern is now broad on purpose.
#
# Anchored at line start with a trailing space or end-of-line after each prefix,
# so `Error reading` matches but `No errors` does not, and a track title that
# happens to begin with one of these words cannot match (titles never appear at
# column 0 in cyanrip's output — they are indented inside a Metadata block).
_RIPPER_ERROR_PREFIXES: tuple[str, ...] = (
    "Invalid",
    "Unable to",
    "Missing",
    "No device",
    "No disc",
    "No cover art",
    "No tracks",
    "Error",
    "Errors",
    "Failed",
    "Couldn't",
    "Could not",
    "Cannot",
    # The contraction, and the omission was measurable rather than theoretical.
    # `Cannot`, `Could not` and `Couldn't` were all here; `Can't` was not, and
    # the ripper's P2 table carries `Can't init %s handler!` — a signal-handler
    # setup failure, published since round 7 lap 25 and matched by NOTHING in
    # this file until now. Measured against round 12's contract before adding it:
    # of 296 P2 rows, exactly one has a `Can't`/`Cannot` shape (that one), and
    # widening to `Can't` fires on zero additional P2 lines. It is a *prefix*
    # rather than an inventory row on purpose — the prefixes are the forward
    # tolerance member of the union, and the string is not in P5, which is the
    # provider's authority on failure-path reachability. Inventing a P5 row for
    # it would be us guessing again, which is the mistake this whole subsystem
    # was rebuilt to stop.
    "Can't",
    "Unsupported",
    "Unknown option",
    "Unrecognized",
    "Stopping,",
    "Stopping",
    "Aborting",
    "Drive media",
    "Insufficient",
    "Out of memory",
    "Fatal",
    # Begins with a hyphen, so no word prefix reaches it. The fork's generated
    # inventory (handshake round 4, Appendix 2) has exactly one string our 23
    # prefixes missed, and this is it — independently re-measured on our side
    # at 87/88 before adding this, rather than taken on their word.
    #
    # No trailing space: the boundary below supplies it. With `"-J "` the
    # boundary then has to match the `(` of `-J (only generate...` and does
    # not — which the fixture caught immediately, and reading the prefix list
    # would not have.
    "-J",
    # Two more, found on our side while implementing `-c disc/totaldiscs` by
    # reading the fork's `src/cyanrip_main.c` at the pin instead of reading its
    # generated inventory. Both are fatal (`return 1`), both are argument
    # validation and therefore stdout-only (their Q5), and both are ABSENT from
    # the fork's 88-string round-4 inventory:
    #
    #   cyanrip_main.c:1439  "discnumber %i is larger than totaldiscs %i"
    #   cyanrip_main.c:1554  "Cover art already specified for track idx %i!"
    #
    # The reason they are missing is a systematic blind spot, not two typos: in
    # both calls the format string sits on a CONTINUATION LINE, so a generator
    # scanning for a literal on the same line as `cyanrip_log(` cannot see it.
    # A sweep of the fork's whole `src/` for that shape finds exactly these two,
    # which is why the number goes 88 → 90 and not further. Reported as §1 of
    # handshake round 5, with the class rather than only the instances.
    #
    # The first matters immediately: it is the fatal we would hit if the range
    # check on `-c` ever let a bad disc position through, so shipping the flag
    # without surfacing its refusal would be capture-without-surfacing again.
    "discnumber",
    "Cover art already specified",
)

# THE MATCHER IS DERIVED FROM THE RIPPER'S PUBLISHED INVENTORY, not from the
# prefix guesses above — full reasoning in `platterpus.ripper_messages`.
#
# Short version: the prefix list was a *second* guess at "what does a diagnostic
# look like", layered on the fork's own 21-word allowlist, and both shared a blind
# spot. Their control-flow re-derivation took the inventory from 88 strings to
# 104, and our pattern missed **all 13** matchable strings the allowlist had
# hidden — including `Offset is unset! To continue with an offset of 0, run with
# -s 0!` and `Device does not support changing speeds!`, which are ordinary
# hardware failures, not exotica. Every one rendered as a bare "Rip failed."
#
# Our 90/90 standing test stayed green throughout, because the fixture it
# asserted against had inherited their filter's blind spot: it measured their
# allowlist, not the ripper's behaviour. That is CLAUDE.md's
# verify-the-behaviour-not-the-description rule biting one level below where it
# was written. See docs/testing.md §5.ab.
#
# The prefixes are KEPT, as union members and nothing more. The inventory
# describes one pin; a newer build will say things it does not list, and the
# prefixes catch the common shapes of those. Inventory for completeness, prefixes
# for forward tolerance — neither alone was enough, which is the whole lesson.
#
# AND THE INVENTORY GOING STALE IS THE SAME BUG A THIRD TIME (2026-08-21). It sat
# at round 6's 115 strings while rounds 7-11 published 117, 120 and then 130; the
# 10 `genopt.h` diagnostics round 9 added include two that matched NOTHING here —
# `Programming error, incorrect type for: %s` and
# `Too many values for argument "%s" (at most %i)` — so either one was a bare
# "Rip failed." The forward-tolerance prefixes carried the other eight, which is
# exactly why nobody noticed: a fallback that half-works hides the gap it is
# filling. Now round 12's 128, and
# `tests/test_ripper_error_surfacing.py::test_the_inventory_is_not_behind_the_newest_published_contract`
# fails when the newest inbound contract publishes a string we do not carry.
_RIPPER_ERROR_RE, _UNMATCHABLE_RIPPER_FORMATS = build_matcher(
    list(ALL_FORMATS), extra_prefixes=_RIPPER_ERROR_PREFIXES
)

# Formats too generic to pattern — a bare `%s` would match every line of output,
# turning every progress redraw into a fatal-error report. Named and counted
# rather than dropped, because "we cannot pattern this" and "this does not exist"
# are different facts and only the second one hides bugs.
if _UNMATCHABLE_RIPPER_FORMATS:
    log.debug(
        "ripper diagnostics: %d of %d published formats carry too little literal "
        "text to pattern, and are covered only by the prefix fallback: %s",
        len(_UNMATCHABLE_RIPPER_FORMATS),
        len(ALL_FORMATS),
        _UNMATCHABLE_RIPPER_FORMATS,
    )

_TRACK_GIVEUP_RE = re.compile(r"giving up on track (?P<track>\d+)")

# Minimum wall-clock gap between forwarding consecutive *progress redraw* lines
# to the GUI. cyanrip redraws its progress many times a second (each `\r` becomes
# its own line — see above), and forwarding every one floods the GUI's event loop
# with queued signals: the window can't service paint events and goes black when
# another window is dragged over it (real-user report, 2026-06-27). Coalescing to
# ~10 updates/second keeps the bar and ETA feeling live while leaving the event
# loop plenty of room to repaint. Only progress lines are throttled — phase
# changes, errors, and end-of-rip markers always go through immediately.
# Cap on retained non-progress ripper output (see RipWorker._stdout_lines).
# A 14-track album is a few hundred such lines, so this is ~30x headroom while
# still bounding a pathological ripper.
#
# HEAD **AND TAIL**, not head-only. This was a plain stop at the cap, reasoned as
# "the head holds the header and the earliest tracks, which is what a report
# needs". That is true of a *successful* rip and exactly wrong for a failing one:
# a ripper's fatal message is the LAST thing it prints, so the one capture a
# 20000-line runaway most needs to keep was the one guaranteed to be dropped —
# and dropped silently, since nothing recorded that a drop had happened. The
# retained text is now the first `_MAX_STDOUT_LINES` lines plus the last
# `_STDOUT_TAIL_LINES`, with an explicit elision marker in between naming how
# many lines were discarded (audit prompted by the maintainer, 2026-08-02:
# "is there any output or error the log file does not capture?").
_MAX_STDOUT_LINES: int = 20000

# How much of the END of a runaway ripper's output to keep. Small relative to the
# head cap because the diagnostic value is concentrated in the last handful of
# lines (the error, and the few lines of context before it), while the head is
# where the header, argv echo and per-track results live.
_STDOUT_TAIL_LINES: int = 2000

# How many lines the cancel path may pull off the pipe *after* the cancel flag is
# seen, to recover the ripper's own account of why it is stopping. Small on
# purpose: this is a bound on a read that `_retain_last_words` argues cannot
# block, not a drain budget. Two is the shape cyanrip actually produces (a
# progress-redraw terminator, then the message); the rest is headroom.
_CANCEL_LAST_WORDS_LINES: int = 4

# Marker written into the captured stdout in place of the discarded middle. It is
# a line the *ripper* could not have produced, so a reader (or a parser) can tell
# an elision from real output — an unmarked gap would read as a rip that simply
# went quiet.
_STDOUT_ELISION = "[platterpus] … {count} lines of ripper output elided here …"

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

# MINIMUM progress across the window before its rate is believed, as a FRACTION
# (0.002 = 0.2 percentage points).
#
# **THIS IS THE 62-HOUR BUG.** The rate projection divides by the progress made
# across the window, and the guard used to be nothing but `window_dfrac > 0`. A
# movement of 0.01 percentage points is greater than zero, so it passed — and
# dividing an hour of remaining work by a rounding-level delta produced, measured
# on real hardware from this rip's own `eta_trace`: 51 → 59 → 70 → 85 → 115 → 175
# → 335 → **3715 minutes**, eight consecutive samples, then a snap back to 11
# minutes when the delta finally reached exactly zero and the fallback branch took
# over. The maintainer saw it as *"track 5 went from hours to minutes"*.
#
# A floor, not a cap, is the right fix here: below this much movement we have no
# rate measurement at all, so the honest answer is to keep the previous estimate
# rather than to invent a number from noise. `_ETA_MAX_REMAINING_S` is the belt to
# this braces, because a floor cannot catch every way a model can be wrong.
#
# WHERE THIS FLOOR BITES, measured rather than assumed. Progress across a 90 s
# window is `90 / total_rip_seconds`, so the floor is reached when a rip's total
# length passes roughly **12.5 hours**:
#
#     1 h rip -> 2.500 pp per window     8 h  -> 0.312 pp     believed
#     4 h rip -> 0.625 pp per window    12 h  -> 0.208 pp     believed
#                                       16 h  -> 0.156 pp     HELD
#                                       24 h  -> 0.104 pp     HELD
#
# Past that the estimate is held rather than refreshed. That is the safe direction
# (a stale plausible number beats a fresh implausible one) and a 12-hour CD rip is
# already pathological — genuine wedges are the stall detector's job, and it reports
# "stalled" instead of a countdown. Documented because an undocumented boundary is
# the kind of thing that gets rediscovered as a bug.
_ETA_MIN_WINDOW_DFRAC: float = 0.002

# A drop in progress this large (fraction) means the bar RESTARTED rather than
# regressed by rounding — a second cyanrip invocation for an auto-fix re-rip,
# which reports its own progress from 0 and resets the elapsed baseline.
#
# Measured: 0.9479 → 0.2935 in one sample when track 5's re-rip began. Blending
# that into an album-scale rate estimate is meaningless, so the estimator is reset
# and the phase is recorded; a sub-pass gets its own clean measurement instead of
# corrupting the album's.
_ETA_PROGRESS_RESET_DROP: float = 0.05

# Hard sanity ceiling on the estimate (seconds). Above this the model has failed
# and we show NOTHING, because "about 62 hours left" is worse than no estimate —
# the user cannot tell a bug from a genuinely slow disc.
#
# WHY AN ABSOLUTE BOUND AND NOT A DISC-RELATIVE ONE. The first draft scaled this to
# the disc's own audio length, which reads better — but the worker does not know
# that length (cyanrip prints `Total time:` in its start report; nothing plumbs it
# here), and inventing plumbing so a *safety net* can be more elegant is backwards:
# a net that depends on a field being populated fails open exactly when the field
# is missing. Red Book caps an audio CD near 80 minutes, so 24 hours is ~18x the
# whole disc — generous enough that it can never fire on a real rip, including a
# damaged disc grinding at 0.5x with heavy re-reads. Genuine wedges are the stall
# detector's job (`_ETA_STALL_THRESHOLD_S`), which reports "stalled" instead of a
# countdown, so this does not have to model them.
_ETA_MAX_REMAINING_S: float = 24 * 60 * 60

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
#   * The album fraction is NOT the only liveness signal, and on its own it is
#     wrong: see `_TASK_LIVENESS_MIN_PCT` below. A secure re-read replays a track
#     the album bar has already counted, so the album fraction freezes for the
#     whole re-read while the drive reads perfectly — measured twice in one rip
#     (2026-08-05 b8): "no forward progress for 3m 2s at 21.7% (track 3)" while
#     cyanrip's own line climbed 52% -> 55% at a steady 1x. We told the user their
#     disc was scratched while nothing was wrong with it.
_ETA_STALL_MIN_PROGRESS: float = 0.005  # 0.5% of the whole album
_ETA_STALL_THRESHOLD_S: float = 180.0

# A meaningful forward step in the CURRENT OPERATION's own percentage (0-100), used
# as a second, independent liveness signal for the stall detector.
#
# WHY A SECOND SIGNAL. The album fraction is a lossy projection: `_overall_from_track`
# maps (track, task%) into the album's 5-95% band and `_bump_overall` refuses to let
# it regress, so ANY work that revisits ground the bar has already covered leaves it
# frozen. The secure re-read (`-Z`) is exactly that — cyanrip re-reads the same track
# from 0% again — so a healthy, converging re-read looks identical to a wedged drive
# if you only watch the album bar. cyanrip's per-operation percentage does not have
# that blind spot: it advances whenever the drive is actually reading, on a re-read
# as much as a first read. So the drive is "stalled" only when NEITHER signal has
# moved for the threshold, which makes the detector strictly more sensitive (a truly
# stuck drive freezes both) and stops it crying scratch on ordinary verification.
_TASK_LIVENESS_MIN_PCT: float = 1.0

# A drop this large (percentage points) in the CURRENT OPERATION's percentage, while
# the track number is unchanged, means that track's read RESTARTED — a secure re-read
# pass (`-Z`), not a regression.
#
# Measured (2026-08-05, b8, track 3): "Ripping track 3, progress - 100%" then
# "…progress - 5%", twice, as it re-read to convergence. 20pp is far above cyanrip's
# redraw granularity (~0.05pp per line) and far below a real restart's ~100pp drop,
# so it cannot be tripped by jitter and cannot miss a restart.
_REREAD_TASK_DROP_PCT: float = 20.0

# --- WHAT KIND of cyanrip invocation a pass is ------------------------------
#
# A rip can spawn cyanrip more than once, and the invocations are NOT the same
# kind of thing. Which kind we are in is decided STRUCTURALLY — from the
# arguments this app itself chose when it launched the pass (see
# ``RipWorker._rip_once``, the single writer) — never by watching the numbers
# and guessing. A "did the progress bar go backwards?" heuristic would read our
# own output as its input, which is exactly the trap CLAUDE.md names as *"what
# pins my input?"*; it also cannot tell the two cases below apart, because both
# of them make the bar stop advancing.
#
#   * ALBUM — a whole-disc pass, or a read-speed-ladder retry of one. The album
#     progress bar and the album ETA mean what they say: N tracks to read, this
#     fraction of them done.
#   * REFIX — the post-rip auto-fix ("securing") pass. It is a SECOND cyanrip
#     run, started AFTER every track has already been ripped, re-reading a
#     SUBSET of tracks (cyanrip ``-l 5``) into a throwaway temp dir so the
#     album's own log/cue stay intact. Here the album model is a *category
#     error*: there is no "track 5 of 14" left to do, there is one track being
#     re-verified, and the album's remaining read work is zero.
#
# MEASURED COST of not distinguishing them — 2026-08-05 rig rip (Police, "Every
# Breath You Take: The Classics", 14 tracks, app v0.6.4b11), read straight off
# that rip's own `eta_trace`: during track 5's auto-fix re-rip the app showed,
# for 47 consecutive samples, a FROZEN "about 43m 0s left" while the true
# remaining time was FOUR SECONDS; the album bar REGRESSED 94.77% -> 35.45% and
# relabelled itself "Ripping track 5 of 14…" after all 14 tracks were already on
# disk; and one sentence carried two contradictory percentages (a 99% track-local
# figure beside a 35.45% album bar). cyanrip's own per-op ETA read "3s" — and it
# was right.
_PASS_ALBUM: str = "album"
_PASS_REFIX: str = "refix"

# Where the overall bar's reserved post-rip band begins (see `_progress_for`'s
# docstring: 0-5% disc scan, 5-95% per-track read, 95-100% post-rip work). The
# securing pass is post-rip work by definition, so this is the floor the bar is
# lifted to when that pass starts — a step FORWARD, never a rewind.
_POST_RIP_BAND_START: float = 95.0

# --- The securing pass's own estimate model ---------------------------------
#
# WHAT CAN HONESTLY BE ESTIMATED HERE, and what deliberately is not.
#
# A `-Z N` re-rip reads one track over and over until N reads agree. **How many
# more reads that will take is unknowable** — that is the whole point of the
# b8 lesson (`_album_eta_text`): "the extra time the re-read costs is unknowable
# until it converges". So we do NOT invent a total for the securing pass.
#
# What IS measurable, every second, is the time left in the read that is running
# right now: cyanrip's per-operation percentage climbs steadily from 0 to 100
# for each read, and we can measure its rate ourselves. So the securing phase
# estimates *this read* and says so in words ("about 20s left in re-read 3").
# That number genuinely counts down instead of freezing, and it never implies
# knowledge of how many reads remain.
#
# The windows are much shorter than the album model's because the thing being
# measured is much shorter: a single track read is seconds to minutes, where an
# album pass is an hour. A 90-second window and an alpha-0.15 filter would still
# be catching up when the read ended.
_REFIX_MIN_ELAPSED_FOR_ETA_S: float = 3.0
_REFIX_ETA_WINDOW_S: float = 20.0
# Minimum movement (percentage points of the CURRENT READ) across that window
# before its rate is believed. Same shape, and the same reason, as
# `_ETA_MIN_WINDOW_DFRAC`: below this we have no rate measurement at all, and
# dividing by a rounding-level delta is how the 62-hour bug happened.
_REFIX_ETA_MIN_WINDOW_DPCT: float = 0.5
_REFIX_ETA_SMOOTHING_ALPHA: float = 0.4
# Sanity ceiling for a SINGLE read of a SINGLE track. Red Book caps one track at
# ~80 minutes of audio, so even a 0.25x crawl finishes inside ~5.5 hours; 6 hours
# can therefore never fire on a real read, while still refusing the kind of
# nonsense cyanrip's own estimator has been seen to print (it said "822h" at
# 0.01%). Above it we show nothing rather than a number the user cannot tell
# from a bug.
_REFIX_ETA_MAX_S: float = 6 * 60 * 60

# cyanrip's own per-operation ETA, as a value we can compare against ours.
#
# The three shapes come from the FORK'S PUBLISHED PROVIDER CONTRACT, not from
# guesswork — `docs/handshake/inbound/artifacts/round-07-lap-25-provider-contract-g9048082.md`
# §P2a, `cyanrip_main.c:868`, lists the ETA segment as exactly one of
# `, ETA - %ih %im` / `, ETA - %im` / `, ETA - %llds`. Deriving the parser from
# the dependency's own format strings rather than from a hand-kept list of
# examples is the same discipline `ripper_messages.py` follows.
#
# Bounded quantifiers throughout (never-unbounded rule), and every group is
# optional so a shape we have not seen degrades to "unparseable" rather than to
# a wrong number.
_CYANRIP_ETA_VALUE = re.compile(
    r"^(?:(?P<h>\d{1,4})\s*h)?\s*(?:(?P<m>\d{1,4})\s*m)?\s*(?:(?P<s>\d{1,7})\s*s)?$"
)

# cyanrip appends its OWN per-op ETA to each progress redraw
# ("…, progress - 42%, ETA - 3m"). We distrust it (it printed "822h" at 0.01%)
# and show our own smoothed album ETA instead — so strip cyanrip's trailing
# ETA clause from the lines we forward to the log view, or the two would
# contradict each other on screen (real-user report). It's always the last
# field, so match to end of line.
_CYANRIP_ETA_CLAUSE = re.compile(r",\s*ETA\s*-.*$")

# How long to wait for the ripper to exit on its own once we have stopped reading
# its output, before escalating to the SIGTERM→SIGKILL group kill.
#
# Generous on purpose: a *normal* finish reaches this having already closed stdout,
# so it returns instantly; the wait only elapses on the abnormal paths (cancel, a
# stream error), where the alternative was hanging forever. cyanrip's own shutdown
# after a SIGTERM includes flushing and closing the current FLAC, which on a slow
# target filesystem is seconds, not milliseconds.
_RIPPER_EXIT_GRACE_S: float = 15.0
# Handed to RipHandle.cancel() for the escalation itself: SIGTERM, wait, SIGKILL,
# wait. Bounded at both steps so a wedged drive cannot make the reap unbounded.
_RIPPER_TERM_GRACE_S: float = 5.0
_RIPPER_KILL_GRACE_S: float = 5.0


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
    # `seconds` is already a float we computed, not external text — but this file
    # is on the never-raises roster and `int()` on a non-finite float raises, so
    # the guard is the cheap way to keep that promise unconditional.
    rounded = int_or_none(round(seconds / step) * step, field="rounded ETA seconds")
    return rounded if rounded is not None else 0


def _cyanrip_eta_seconds(raw: str | None) -> int | None:
    """cyanrip's own per-operation ETA string as whole seconds, or ``None``.

    Parses the three shapes the fork's provider contract publishes — ``"1h 5m"``,
    ``"3m"``, ``"3s"`` — and returns ``None`` for anything else, including the
    empty string. **Never raises**: this is external text, and the read loop that
    ultimately reaches it terminates the rip on an exception.

    WHY WE PARSE A NUMBER WE DO NOT TRUST. cyanrip's estimate is *not* promoted
    to the primary source anywhere — it resets every phase and has printed "822h"
    at 0.01% done, which is why the app strips it from the forwarded log lines and
    shows its own instead. But during the securing pass it is a **second,
    independent witness of exactly the quantity we are estimating** (the current
    read), and on the 2026-08-05 rig rip it read "3s" while our album model read
    43 minutes. CLAUDE.md's lesson is *"the fix for a signal going quiet is a
    second signal, not an exemption"*, so it is used in the one place our own
    measurement genuinely does not exist yet — the first seconds after a read
    restarts, before a rate window has formed — and never to override a
    measurement we do have. Every sample that came from it is labelled as such in
    the trace (``state="securing_from_ripper"``), so a borrowed number can never
    be mistaken for one we measured.
    """
    if not raw:
        return None
    match = _CYANRIP_ETA_VALUE.match(raw.strip())
    if match is None:
        return None
    hours, minutes, seconds = match.group("h"), match.group("m"), match.group("s")
    # All three groups are optional, so the pattern also matches the empty string
    # and any run of whitespace. Requiring at least one unit is what stops that
    # from being reported as a confident "0 seconds remaining".
    if hours is None and minutes is None and seconds is None:
        return None
    total = 0
    for value, scale in ((hours, 3600), (minutes, 60), (seconds, 1)):
        if value is None:
            continue
        parsed = int_or_none(value, field="cyanrip ETA field")
        if parsed is None:  # pragma: no cover — the pattern already bounds these
            return None
        total += parsed * scale
    return total


def _percent_or_none(raw: str) -> float | None:
    """A percentage from external text as a finite float, or ``None``. Never raises.

    `float()` is the trap here and it is a quieter one than `int()`: on a long run
    of digits it does **not** raise, it silently returns `inf`. That `inf` then
    travels through the progress signal into `RipProgress.set_progress`, where
    `int(inf)` raises `OverflowError` — on the GUI thread, inside a queued slot,
    for a progress bar. (`nan` does the same with `ValueError`.)

    So the conversion is done once, here, and anything not finite is refused. The
    producing patterns are bounded now too; this is the second layer, because a
    pattern is one edit away from being unbounded again and the read loop that
    calls this terminates the rip on an exception (audit, 2026-07-31).
    """
    try:
        value = float(raw)
    except (TypeError, ValueError):
        log.warning("unusable percentage in ripper output: %r", raw[:32])
        return None
    if not math.isfinite(value):
        log.warning("non-finite percentage in ripper output: %r", raw[:32])
        return None
    return value


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
    # Emitted with the 1-based track number each time the ripper finishes a track
    # (from cyanrip's "Track N ripped…" line), so the GUI can mark that row done
    # in the live per-track Status column.
    track_completed = Signal(int)
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
        #: The ripper's verdict on its own log. None until the verification step
        #: runs — a third state, not a failure (see `ripper_log_verification`).
        self._ripper_log_verification: LogVerification | None = None
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
        # WHICH handle we have already sent a stop signal to — not a bool. "Have
        # we signalled?" is a fact about a *subprocess*, and this worker spawns one
        # per pass (the read-speed ladder and the per-track auto-fix each start a
        # fresh ripper). A bool would need resetting somewhere, and every place to
        # put that reset has a window in which a cancel either double-signals the
        # old process or fails to signal the new one. Comparing identity has no
        # such window: a new handle is a different object and is therefore
        # un-signalled, automatically.
        #
        # The lock makes the compare-and-set atomic across this worker's two
        # callers — `cancel()` on the GUI thread and `_reap_ripper()` on the
        # worker's. It is held only across a `killpg` syscall (microseconds), so it
        # does not engage the never-block-the-GUI rule.
        self._sigterm_sent_for: RipHandle | None = None
        self._sigterm_lock: threading.Lock = threading.Lock()
        # Every NON-progress line the ripper printed, kept verbatim.
        #
        # This is the one artifact that survives a kill. cyanrip's logfile is
        # block-buffered, so killing it loses the tail of a 4 KiB block — twice
        # on the rig now (2026-08-01: a 4096-byte cut that lost a track verified
        # at AccurateRip confidence 200, and a 20480-byte cut that lost a
        # track's filename). Its stdout is a pipe we are already draining, so
        # whatever it *said* is ours the moment it says it, regardless of what
        # reaches disk.
        #
        # Progress redraws are excluded, not truncated: they are ~98% of the
        # stream (900+ lines of "progress - 41.65%" for one album) and carry
        # nothing a report needs. What is left is every Summary block, header
        # and error — a few hundred lines, small enough to embed in the JSON.
        self._stdout_lines: list[str] = []
        # The rolling tail kept once `_stdout_lines` hits its cap, so a runaway
        # ripper's FINAL lines — where its fatal message is — survive. See
        # `_MAX_STDOUT_LINES`.
        self._stdout_tail: list[str] = []
        # How many lines fell out of that rolling window. Reported in the
        # captured text rather than leaving an unexplained gap.
        self._stdout_elided: int = 0
        # The ripper's exit status, and the exact argv we invoked it with. Both
        # were computed (or built) and then discarded, so the report could say a
        # rip failed but not *how*: exit 1 (the ripper refused an argument),
        # exit 0 with cancel (the user stopped it), and -9 (we SIGKILLed a wedged
        # child) are three different failures that all rendered identically. The
        # argv is the other half — the `-t 17=` defect that killed a whole rip
        # was diagnosed from the maintainer's uploaded files because our own
        # report did not carry the command line (2026-08-02).
        self._ripper_exit_code: int | None = None
        self._ripper_argv: tuple[str, ...] = ()
        # The FIRST pass's argv, kept separately because only the first pass
        # writes the whole-disc log whose `Invoked as:` line we cross-check
        # against (see the assignment site for the false alarm this fixes).
        self._ripper_argv_first_pass: tuple[str, ...] = ()
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
        # The previous album fraction, so a RESTART (a second cyanrip invocation
        # for an auto-fix re-rip, which reports progress from zero) can be told
        # from ordinary forward movement and reset the rate estimate instead of
        # blending two different scales. See _ETA_PROGRESS_RESET_DROP.
        self._eta_last_frac: float | None = None
        # Stall detection (see _album_eta_text / _ETA_STALL_THRESHOLD_S): the album
        # fraction at the last MEANINGFUL forward step, and the monotonic time it
        # was reached. When the fraction hasn't cleared another step for the
        # threshold, the read is stalled on a hard-to-read spot and we say so
        # instead of a misleading countdown. Reset per pass.
        self._eta_stall_frac: float | None = None
        self._eta_stall_since: float | None = None
        # SECOND liveness signal, independent of the album bar: the current
        # operation's own percentage at its last meaningful forward step, and when
        # that happened. See _TASK_LIVENESS_MIN_PCT — during a secure re-read the
        # album fraction is frozen by construction, so watching it alone reported a
        # perfectly healthy drive as stuck on a scratch. Maintained in
        # _note_task_progress, consumed by the stall check in _album_eta_text.
        self._task_forward_pct: float | None = None
        self._task_forward_at: float | None = None
        # Secure-re-read tracking (see _REREAD_TASK_DROP_PCT). `_reread_track` is the
        # track whose task percentage we're following; `_reread_pass` counts how many
        # times its read has RESTARTED (0 = still the first read). While it is >0 the
        # album fraction cannot advance, so the ETA holds and says what's happening
        # rather than dividing a huge remaining fraction by a frozen window.
        self._reread_track: int | None = None
        self._reread_pass: int = 0
        self._task_pct_seen: float | None = None
        # WHICH KIND OF PASS is running, and which tracks it was asked for. See
        # `_PASS_ALBUM` / `_PASS_REFIX` for what turns on this and why it is
        # declared rather than inferred. `_rip_once` is the ONLY writer — it sets
        # both from its own arguments on every invocation, so the pair can never
        # be stale for the pass that is actually running.
        self._pass_kind: str = _PASS_ALBUM
        self._pass_tracks: tuple[int, ...] = ()
        # The securing pass's own rate window and smoothed estimate, measured on
        # the CURRENT READ's percentage rather than on the album fraction. Kept
        # separate from `_eta_rate_window` / `_smoothed_remaining_s` on purpose:
        # the two are measurements of different things on different scales, and
        # mixing them is the defect this state exists to prevent. Emptied whenever
        # a read restarts (`_note_task_progress`) so no window ever spans two
        # different reads.
        self._refix_rate_window: list[tuple[float, float]] = []
        self._refix_smoothed_s: float | None = None
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
        # The PARSED per-track record of every re-rip we actually swapped into the
        # album, keyed by track number. This is the shipped file's own read — its
        # CRC and AccurateRip results — which the whole-disc first-pass log cannot
        # know (real-hardware bug, 2026-07-26: the log kept describing the
        # DISCARDED bytes). The GUI folds these over the parsed log before any
        # rendering, so every surface describes the audio actually on disk.
        self._swapped_track_records: dict[int, object] = {}
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
        # Set the moment the securing pass actually starts, and cleared when it
        # finishes recording its per-track results. If it is still True at the
        # end, the pass was cut short (app shutdown, cancel, a re-rip that never
        # produced a log) — real-hardware finding 2026-07-28, where closing the
        # window mid-securing produced `engaged: true` with an EMPTY
        # `retried_tracks` and no other trace. The audio is unaffected (the
        # re-rip works in a temp dir and only swaps on success), but the record
        # must not imply a securing pass that did not complete.
        self._secure_rerip_interrupted: bool = False
        self._disc_in_accuraterip: bool | None = None
        self._secure_rerip_skipped_reason: str | None = None

    def _album_eta_text(self, overall_pct: float, task_pct: float | None = None) -> str:
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

        ``task_pct`` is the CURRENT OPERATION's own percentage from the same
        progress line (``_progress_for``'s second return value). It is only used
        by the securing pass, whose estimate is scoped to the read that is running
        rather than to the album; passing it explicitly keeps that input pinned to
        the tick it belongs to instead of to whatever bookkeeping happens to hold
        last. Falls back to the bookkeeping (``_task_pct_seen``) when a caller
        does not supply it.
        """
        from platterpus.rip_timing import format_duration

        # Use the CURRENT pass's baseline (see _reset_pass_progress / #21): the
        # `overall` fraction resets each pass, so elapsed must be measured from
        # this pass's start, not the whole rip's. Fall back to the rip start.
        started = self._eta_pass_started or self._started_monotonic
        if started is None:
            return ""
        frac = overall_pct / 100.0
        # WHICH KIND OF PASS is this? Declared by `_rip_once`, never inferred —
        # see `_PASS_ALBUM` / `_PASS_REFIX`. Everything below that reads the ALBUM
        # fraction is meaningless during a securing pass, because the album's read
        # work is already finished.
        securing = self._pass_kind == _PASS_REFIX
        # Skip the disc-scan band (0-5%) and the very end; both give noise. These
        # are guards on the ALBUM fraction, so they do not apply to the securing
        # pass — there the album bar is deliberately parked at the top of its
        # range (`_POST_RIP_BAND_START`), which would trip the "effectively done"
        # test on every single tick and silence the phase's own estimate.
        if not securing and (frac <= 0.05 or frac >= 0.999):
            return ""
        now = time.monotonic()
        elapsed = now - started
        # A securing pass warms up faster because it is measuring a much shorter
        # thing: 8 seconds of silence out of a 30-second re-read is most of it.
        min_elapsed = (
            _REFIX_MIN_ELAPSED_FOR_ETA_S if securing else _MIN_ELAPSED_FOR_ETA_S
        )
        if elapsed < min_elapsed:
            return ""
        # Stall detection FIRST — before any projection. Track when the drive last
        # proved itself alive; if it hasn't for the threshold, it's stuck on a
        # hard-to-read spot (real hardware: a track that hung for hours while the
        # projection still counted down "~4h left"). Say so plainly instead — honest
        # and far more useful than a misleading, ever-growing number. A tiny per-tick
        # crawl doesn't reset the timer (the step is what a healthy read clears in a
        # second or two), so a barely-moving read is caught, while a
        # merely-slow-but-advancing one is not. Note `frac > 0.05` already here (scan
        # band skipped above).
        #
        # TWO signals, not one, and the second is not optional — a secure re-read
        # pins the album fraction by construction, and watching only that told a
        # maintainer twice in one rip that a perfectly good disc was scratched.
        album_moved = (
            self._eta_stall_frac is None
            or frac >= self._eta_stall_frac + _ETA_STALL_MIN_PROGRESS
        )
        if album_moved:
            self._eta_stall_frac = frac
            self._eta_stall_since = now
        # SECOND SIGNAL. The album fraction freezes for the whole of a secure
        # re-read, so it cannot be the only witness — see _TASK_LIVENESS_MIN_PCT.
        # "Stalled" requires that NEITHER signal has moved for the threshold, so
        # take the more recent of the two as the last time the drive proved itself
        # alive. This makes the detector stricter, not laxer: a wedged drive stops
        # printing progress lines at all, so both signals go quiet together.
        last_alive = self._eta_stall_since
        if self._task_forward_at is not None and (
            last_alive is None or self._task_forward_at > last_alive
        ):
            last_alive = self._task_forward_at
        if last_alive is None or now - last_alive < _ETA_STALL_THRESHOLD_S:
            # The drive proved itself alive recently enough. If we were stalled, note
            # the recovery in the record (the transient status line can't be one).
            if self._eta_stalled:
                log.info(
                    "rip recovered from stall at %.1f%% (track %s)",
                    overall_pct,
                    self._current_track,
                )
                self._eta_stalled = False
        else:
            stalled_for = now - last_alive
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
            self._record_eta_sample(overall_pct, elapsed, None, state="stalled")
            return (
                f" · stalled {format_duration(stalled_for)} — the drive is stuck "
                "on a hard-to-read spot (a scratch or smudge)"
            )
        # THE SECURING PASS GETS ITS OWN MODEL, because the album model has nothing
        # left to describe: every track is already on disk, so "remaining album
        # work" is zero and the album fraction is a constant. Note this branch is
        # AFTER the stall check on purpose — a drive that wedges during a re-rip is
        # still a wedged drive, and the two-signal stall detector is the only thing
        # that reports it. See `_securing_eta_text`.
        if securing:
            return self._securing_eta_text(now, elapsed, overall_pct, task_pct)
        # A SECURE RE-READ IS RUNNING, so the album fraction is pinned and there is
        # nothing here to project from: `_overall_from_track` maps this track's
        # progress into a span of the album the bar has already covered, and
        # `_bump_overall` refuses to regress. Any rate computed below would be
        # (1 - a big constant) ÷ (whatever noise is left in the window) — measured
        # climbing 54m -> 1h5m -> 2h15m -> 5h40m in 70 seconds (2026-08-05, b8,
        # track 3), which is the SAME divide-by-a-frozen-bar shape as the 62-hour
        # bug arriving through a door the floor below does not cover: the window
        # still held real pre-freeze movement, so the floor was legitimately met.
        #
        # So hold the estimate and SAY WHY. "About 54m left · verifying track 3" is
        # the truth: the remaining album work hasn't changed, and the extra time the
        # re-read costs is unknowable until it converges (this one took two more
        # passes; the next disc may take five). A number that stops moving with a
        # reason beside it is honest; a number that triples in a minute is not.
        if self._reread_pass > 0:
            self._record_eta_sample(
                overall_pct,
                elapsed,
                _coarsen_eta_seconds(self._smoothed_remaining_s)
                if self._smoothed_remaining_s is not None
                else None,
                state="rereading",
            )
            verifying = (
                f" · verifying track {self._current_track} "
                f"(re-read {self._reread_pass + 1})"
                if self._current_track
                else " · verifying this track by re-reading it"
            )
            return f"{self._eta_hold_text()}{verifying}"
        # Project the remaining time from the RECENT read rate (a trailing
        # window), not the cumulative average since the pass began. The fast
        # disc-scan phase and the disc's inner tracks read much faster than the
        # bulk, so a from-zero average let that fast start dominate and the early
        # ETA came out absurdly low. Collect (elapsed, frac) points — only past
        # the scan band, so the scan never enters the window — prune to the
        # window, and measure the rate over it.
        # A RESTART, not a regression: the auto-fix re-rip is a SECOND cyanrip
        # invocation that reports its own progress from zero and resets the elapsed
        # baseline. Measured: 94.79% → 29.35% in one sample. Carrying the album's
        # rate window across that boundary mixes two different scales, so throw the
        # window away and measure the new phase on its own terms.
        if (
            self._eta_last_frac is not None
            and frac < self._eta_last_frac - _ETA_PROGRESS_RESET_DROP
        ):
            log.info(
                "ETA: progress restarted (%.1f%% -> %.1f%%) — a new pass is running, "
                "resetting the rate estimate rather than blending two scales",
                self._eta_last_frac * 100.0,
                frac * 100.0,
            )
            self._eta_rate_window = []
            self._smoothed_remaining_s = None
        self._eta_last_frac = frac
        self._eta_rate_window.append((elapsed, frac))
        cutoff = elapsed - _ETA_RATE_WINDOW_S
        self._eta_rate_window = [p for p in self._eta_rate_window if p[0] >= cutoff]
        base_elapsed, base_frac = self._eta_rate_window[0]
        window_dt = elapsed - base_elapsed
        window_dfrac = frac - base_frac
        if window_dt > 0 and window_dfrac >= _ETA_MIN_WINDOW_DFRAC:
            # remaining = remaining_fraction ÷ recent_rate (frac per second).
            raw_remaining = (1.0 - frac) * window_dt / window_dfrac
        elif self._smoothed_remaining_s is not None:
            # THE WINDOW HAS NO USABLE RATE — and we already have an estimate, so
            # KEEP IT rather than divide by noise. This is the 62-hour bug's fix:
            # the old code's only guard was `> 0`, so a 0.01pp rounding wobble
            # became the divisor and the estimate ran to 3715 minutes across eight
            # consecutive samples. A frozen progress bar means "we cannot measure
            # the rate right now", and the honest response is to hold the last
            # measurement, not to invent one.
            self._record_eta_sample(
                overall_pct,
                elapsed,
                _coarsen_eta_seconds(self._smoothed_remaining_s),
                state="held_no_rate",
            )
            return self._eta_hold_text()
        else:
            # No usable rate AND no previous estimate (first post-scan tick):
            # the cumulative projection is all we have. Bounded below by the same
            # sanity check as every other branch.
            raw_remaining = elapsed * (1.0 - frac) / frac
        if not raw_remaining >= 1:  # guards NaN/inf and sub-second "0s left"
            return ""
        # PHYSICAL SANITY BOUND. A floor on the divisor stops the failure we
        # measured; this stops the ones we have not. Scaled to the disc's own audio
        # length rather than a magic hour count, so a 25-minute EP and a 74-minute
        # disc get proportionate ceilings. Beyond it the model has failed, and the
        # right output is NO estimate — "about 62 hours left" is worse than silence
        # because the user cannot tell it is a bug.
        if raw_remaining > _ETA_MAX_REMAINING_S:
            log.warning(
                "ETA: computed %s remaining, past the %s sanity ceiling — the model "
                "has failed, so no estimate is shown (progress %.2f%%, "
                "window dt=%.1fs dfrac=%.5f, elapsed %.0fs)",
                format_duration(raw_remaining),
                format_duration(_ETA_MAX_REMAINING_S),
                frac * 100.0,
                window_dt,
                window_dfrac,
                elapsed,
            )
            self._record_eta_sample(
                overall_pct,
                elapsed,
                _coarsen_eta_seconds(self._smoothed_remaining_s)
                if self._smoothed_remaining_s is not None
                else None,
                state="held_over_ceiling",
            )
            return self._eta_hold_text()
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

    def _securing_label(self) -> str:
        """The " · re-read 3" / "" tail that names which read is running.

        Kept separate so every return path of :meth:`_securing_eta_text` — the one
        with an estimate and the several without — carries the same phase wording.
        A phase that names itself only when it also has a number is a phase the
        user cannot recognise on the ticks where the number is missing.
        """
        if self._reread_pass > 0:
            # +1 because `_reread_pass` counts RESTARTS: the first restart is the
            # second read of that track.
            return f" · re-read {self._reread_pass + 1}"
        return ""

    def _securing_eta_text(
        self,
        now: float,
        elapsed: float,
        overall_pct: float,
        task_pct: float | None,
    ) -> str:
        """The status-line suffix during a securing (auto-fix) re-rip. Never raises.

        **What this estimates, and what it refuses to.** It estimates the time left
        in the read that is running right now, measured from that read's own
        percentage over a short trailing window. It does NOT estimate the securing
        pass as a whole, because a ``-Z N`` re-rip runs until N reads agree and the
        number of reads that will take is genuinely unknowable — inventing a total
        for it is the same class of mistake as the album estimate this replaces,
        just with a smaller denominator. So the wording is scoped too: "about 20s
        left in re-read 3", never "about 20s left".

        **Why not simply hold the album estimate here (the b8 behaviour)?** Because
        the two cases the hold conflates are different. Holding is honest for a
        secure re-read *inside* the whole-disc pass: the album's remaining work
        really has not changed, so the last album estimate is still the best answer.
        It is dishonest here: the album has no remaining work at all, and the number
        being held is a projection of album-scale work that no longer exists. On the
        rig it held "43m" with four seconds to go.

        Falls back to cyanrip's own per-op ETA only where we have no measurement
        yet, and labels those samples so the trace never passes a dependency's
        claim off as ours — see :func:`_cyanrip_eta_seconds` for that reasoning.
        """
        from platterpus.rip_timing import format_duration

        label = self._securing_label()
        pct = task_pct if task_pct is not None else self._task_pct_seen
        if pct is None:
            # No per-operation percentage has arrived yet (e.g. cyanrip is still
            # printing its start report). Say what is happening; claim no number.
            self._record_eta_sample(overall_pct, elapsed, None, state="securing_held")
            return label

        # Measure THIS read's rate over a short trailing window. The window is
        # emptied whenever a read restarts (`_note_task_progress`), so it can never
        # span two reads — the same rule the album window learned the hard way.
        self._refix_rate_window.append((now, pct))
        cutoff = now - _REFIX_ETA_WINDOW_S
        self._refix_rate_window = [p for p in self._refix_rate_window if p[0] >= cutoff]
        base_at, base_pct = self._refix_rate_window[0]
        window_dt = now - base_at
        window_dpct = pct - base_pct

        raw_remaining: float | None = None
        state = "securing"
        if window_dt > 0 and window_dpct >= _REFIX_ETA_MIN_WINDOW_DPCT:
            # remaining = percentage left ÷ recent rate (percentage points/second).
            raw_remaining = (100.0 - pct) * window_dt / window_dpct
        else:
            # No rate of our own yet. This is the one hole a second signal is for
            # (CLAUDE.md: "the fix for a signal going quiet is a second signal, not
            # an exemption"), and cyanrip's per-op ETA measures exactly the thing we
            # are missing. Borrowed, bounded, and LABELLED — never promoted.
            borrowed = _cyanrip_eta_seconds(self._last_cyanrip_eta)
            if borrowed is not None:
                raw_remaining = float(borrowed)
                state = "securing_from_ripper"

        if (
            raw_remaining is None
            or not math.isfinite(raw_remaining)
            or raw_remaining < 0.0
            or raw_remaining > _REFIX_ETA_MAX_S
        ):
            # Nothing believable to show. Unlike the album path there is no held
            # value worth re-showing: a stale per-read estimate describes a read
            # that may already have finished and restarted. Name the phase and stop.
            if raw_remaining is not None:
                log.warning(
                    "securing pass: computed %.0fs remaining for the current read, "
                    "outside the 0-%.0fs sanity range — showing no estimate rather "
                    "than a number the user cannot tell from a bug (read at %.2f%%, "
                    "window dt=%.1fs dpct=%.2f)",
                    raw_remaining,
                    _REFIX_ETA_MAX_S,
                    pct,
                    window_dt,
                    window_dpct,
                )
            self._record_eta_sample(overall_pct, elapsed, None, state="securing_held")
            return label

        # Light EMA. Lighter than the album's alpha (0.15) because a read lasts
        # seconds to minutes: a heavy filter would still be catching up when the
        # read ended, which would make the number look frozen — the exact symptom
        # this whole change exists to remove. A borrowed value replaces the state
        # outright rather than being blended, because it is a different kind of
        # measurement and averaging the two would produce a third thing that is
        # neither.
        if self._refix_smoothed_s is None or state == "securing_from_ripper":
            self._refix_smoothed_s = raw_remaining
        else:
            self._refix_smoothed_s = (
                _REFIX_ETA_SMOOTHING_ALPHA * raw_remaining
                + (1.0 - _REFIX_ETA_SMOOTHING_ALPHA) * self._refix_smoothed_s
            )
        display = _coarsen_eta_seconds(self._refix_smoothed_s)
        self._record_eta_sample(overall_pct, elapsed, display, state=state)
        if display < 1:
            # Under the display floor: the read is about to finish. The phase label
            # still goes out so the line does not silently lose its context.
            return label
        where = (
            f"re-read {self._reread_pass + 1}" if self._reread_pass > 0 else "this read"
        )
        return f" · about {format_duration(display)} left in {where}"

    def _eta_hold_text(self) -> str:
        """The last believed estimate, re-rendered — or nothing if there is none.

        Used when the rate is unmeasurable (a frozen progress bar) or when the
        computed value failed the sanity ceiling. **Holding a stale-but-plausible
        number beats printing a fresh implausible one**: the 62-hour reading came
        from recomputing on noise, and a user reads every number we print as a
        claim. Deliberately does NOT record a trace sample — the trace exists to
        show what we *computed*, and holding is the absence of a computation.
        """
        from platterpus.rip_timing import format_duration

        if self._smoothed_remaining_s is None:
            return ""
        display = _coarsen_eta_seconds(self._smoothed_remaining_s)
        if display < 1:
            return ""
        return f" · about {format_duration(display)} left"

    def _record_cyanrip_eta(self, eta: str | None) -> None:
        """Remember cyanrip's most recent per-op ETA reading (raw string), for the
        posterity trace. A no-op when cyanrip's line carried no ETA."""
        if eta:
            self._last_cyanrip_eta = eta.strip()

    def _record_eta_sample(
        self,
        overall_pct: float,
        elapsed_s: float,
        our_eta_s: int | None,
        state: str = "computed",
    ) -> None:
        """Append a throttled ETA-trace sample: PC wall-clock time + both
        estimates + progress + WHICH BRANCH produced it, for the report's
        ``eta_trace``. Never raises.

        ``state`` names the path: ``computed`` (a fresh rate measurement),
        ``held_no_rate`` / ``held_over_ceiling`` (the previous estimate re-shown
        because the window had no usable rate, or the computed value failed the
        sanity ceiling), ``rereading`` (a secure re-read has the album bar pinned),
        ``stalled`` (neither liveness signal moved), and — during the post-rip
        securing pass, which estimates the CURRENT READ rather than the album —
        ``securing`` (measured by us), ``securing_from_ripper`` (borrowed from
        cyanrip's own per-op ETA because we had no measurement yet) and
        ``securing_held`` (nothing believable to show). ``our_eta_seconds`` is None
        where there was no estimate to show.

        ``pass_kind`` records WHICH KIND of cyanrip invocation the sample came
        from (``album`` / ``refix``). Its absence is why the 2026-08-05 trace could
        not be read at a glance: 47 samples labelled "Ripping track 5 of 14" with a
        frozen 43-minute estimate were, in fact, a separate one-track re-rip that
        ran after the album finished, and nothing in the record said so.

        **EVERY branch records.** The first version recorded only ``computed``,
        with a comment arguing that "holding is the absence of a computation" — and
        that argument cost the analysis of this very bug: the 2026-08-05 b8 trace
        has a 541-second hole and a 400-second hole, both landing exactly on the
        minutes the model was misbehaving, because the hold and stall paths returned
        without sampling. A trace that goes quiet during the interesting part is not
        a trace, and the maintainer's standing instruction is to capture more than
        we think we need. `state` is what keeps the samples honest instead: a held
        value is labelled as held rather than passed off as a measurement.
        """
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
                    # Our smoothed album estimate (seconds remaining), or None when
                    # there was nothing to show. `state` says how it was arrived at
                    # — read the two together or a held value reads as a fresh one.
                    "our_eta_seconds": our_eta_s,
                    "state": state,
                    # Which KIND of cyanrip invocation produced this sample:
                    # "album" (a whole-disc pass or a ladder retry) or "refix"
                    # (the post-rip securing re-rip of a track subset). Two
                    # samples with the same `overall_percent` mean entirely
                    # different things depending on this field.
                    "pass_kind": self._pass_kind,
                    # How many times the current track's read has restarted (0 =
                    # first read). Non-zero means the album bar is pinned by a
                    # secure re-read, which is why `state` is "rereading".
                    "reread_pass": self._reread_pass,
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
    def swapped_track_records(self) -> dict[int, object]:
        """Parsed per-track records of the re-rips actually swapped into the album.

        Keyed by track number; each value is the ``TrackResult`` from the *re-rip's*
        own log, i.e. the read that produced the file now on disk. The whole-disc
        log records only the first pass, so without this the report and the
        EAC-layout log describe the discarded bytes — a CRC that doesn't match the
        file it names (real-hardware bug, 2026-07-26). Empty when nothing was
        swapped."""
        return dict(self._swapped_track_records)

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
            "interrupted": self._secure_rerip_interrupted,
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
        # BEFORE anything spawns: say what this rip is about to do. The app builds
        # the ripper's argv, so which flags a rip carries is our decision — and
        # until now the only way to learn it was to read the finished artifact
        # (`Invoked as:` in cyanrip's log, `ripper_argv` in our JSON). Both are
        # post-mortem, which is the wrong end of a 70-minute rip to discover that
        # `-Z` ran in dynamic mode when you wanted it on every track. Pure
        # function, no I/O, so it cannot fail the rip; see `rip_plan`.
        for planned in describe_rip_plan(
            secure_rerip_matches=self._params.secure_rerip_matches,
            secure_rerip_dynamic=self._params.secure_rerip_dynamic,
            rerip_offset_variant=self._params.rerip_offset_variant,
            max_retries=self._params.max_retries,
            read_speed_mode=self._params.read_speed_mode,
            read_speed=self._params.read_speed,
            force_overread=self._params.force_overread,
            read_offset_override=self._params.read_offset_override,
            only_tracks=self._params.only_tracks,
            disc_track_total=self._params.disc_track_total,
            cover_art=self._params.cover_art,
        ):
            # Both surfaces: the app's log file (so a returned bug report carries
            # it) and the on-screen live log (so the person at the drive can read
            # it while the disc is still spinning up).
            log.info("%s", planned)
            self.log_line.emit(planned)

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
            # Remember this pass's speed so ETA samples are tagged with it.
            # (`_rip_once` resets the per-pass progress state itself — it is the
            # single writer of the pass phase; see its docstring.)
            self._current_read_speed = speed
            outcome = self._rip_once(
                read_speed=speed,
                secure_rerip_matches=secure_rerip,
                only_tracks=self._params.only_tracks,
                pass_kind=_PASS_ALBUM,
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
                    # With rerip_offset_variant on, an offset-variant ("partially
                    # accurate") match is NOT treated as proven and is re-read too,
                    # so a track that offset-variant-matches with an unstable read
                    # converges on a reproducible one (real-hardware finding,
                    # 2026-07-23). Off by default → today's behaviour (offset-variant
                    # accepted on the fast read).
                    to_fix = tracks_failing_accuraterip(
                        parsed_log,
                        include_offset_variant=self._params.rerip_offset_variant,
                    )
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
                # The FIRST pass's CRC per track, captured before any swap, so the
                # addendum can say whether a re-read confirmed the original audio
                # or replaced it. Without this it could only assert "the improved
                # read was swapped in" — which on the J1 rip was false: track 5
                # came back with the CRC the album log already held (round 7).
                first_pass_crcs = {
                    number: crc
                    for track in getattr(parsed_log, "tracks", ()) or ()
                    if (number := getattr(track, "number", None)) is not None
                    and (
                        crc := str(
                            getattr(track, "copy_crc", "")
                            or getattr(track, "test_crc", "")
                            or ""
                        )
                    )
                }
                self._auto_fix_tracks(
                    to_fix,
                    rerip_z,
                    trigger,
                    album_log_path=log_path_str,
                    first_pass_crcs=first_pass_crcs,
                )

        # Ask the RIPPER whether the log it wrote still matches its own checksum.
        # Deliberately the LAST thing before finishing: every step that could touch
        # that file (the speed ladder, the auto-fix and its addendum) has run, so a
        # pass here is a statement about the artifact the user keeps.
        #
        # An INDEPENDENT witness — not our file, not our checksum, not our checking
        # code — which is the whole point (round 7 lap 10, J3). Our own footer check
        # reported "the log matches its own SHA-256 footer" on a rip that shipped a
        # cyanrip log cyanrip itself would reject.
        #
        # Runs HERE, on the worker thread, because it spawns a container exec. The
        # report's audit check reads the recorded verdict instead of probing, so no
        # subprocess ever lands in a GUI slot.
        self._verify_ripper_log(log_path_str)

        if success:
            # Peg both bars at 100% so a finished rip never leaves the
            # overall bar short of full (the post-rip AccurateRip phase
            # has no reliable percentage of its own).
            self.progress.emit(100.0, 100.0)
        self.finished.emit(success, log_path_str)

    def _verify_ripper_log(self, log_path_str: str) -> None:
        """Record the ripper's verdict on its own log. Best-effort; never raises."""
        if not log_path_str:
            return
        try:
            verification = self._backend.verify_log(log_path_str)
        except Exception as exc:  # noqa: BLE001 — a probe must not cost a finished rip
            log.exception("ripper log verification raised")
            diagnostics.exception(
                "ripper.log_verify_failed",
                "could not ask the ripper to verify its own log; the rip itself is "
                "unaffected, but this rip carries no independent check of that log",
                exc,
            )
            return
        self._ripper_log_verification = verification
        if verification.is_verified:
            self.log_line.emit(f"[verify] {verification.detail}")
            return
        # Both remaining states are surfaced, not just the negative: a
        # `not_determined` that says nothing is the "capture without surfacing"
        # bug, and it is the state a user on a stock build will actually hit.
        self.log_line.emit(f"[verify] {verification.detail}")
        if verification.verdict == RIPPER_LOG_FAILED:
            diagnostics.error(
                "ripper.log_verify_failed",
                verification.detail,
                argv=verification.argv,
                exit_code=verification.exit_code,
                detail=verification.output,
            )
        else:
            log.info("ripper log not verified: %s", verification.detail)

    @property
    def ripper_log_verification(self) -> LogVerification | None:
        """The ripper's verdict on its own log, or ``None`` if never attempted.

        ``None`` is a third state and is reported as such: a rip that never reached
        the verification step (cancelled before a log existed) is not a rip whose
        log failed.
        """
        return self._ripper_log_verification

    def _rip_once(
        self,
        *,
        read_speed: int,
        secure_rerip_matches: int,
        output_dir: Path | None = None,
        only_tracks: tuple[int, ...] = (),
        pass_kind: str = _PASS_ALBUM,
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

        ``pass_kind`` is the caller DECLARING what this invocation is —
        ``_PASS_ALBUM`` for a whole-disc pass (or a ladder retry of one),
        ``_PASS_REFIX`` for the post-rip securing re-rip. The progress bar, the
        status wording and the ETA model all key off it, and it is a parameter
        rather than something inferred from the numbers for the reason spelled out
        at ``_PASS_ALBUM``: every heuristic that could tell the two apart is
        downstream of the very display we are trying to fix.

        **This method is the single writer of the pass-phase state.** It resets the
        per-pass progress bookkeeping itself (callers used to do it just before
        calling in), so a new call site cannot start a pass that never declared
        what kind it is — it would simply inherit the previous pass's model, which
        is precisely the bug.
        """
        self._reset_pass_progress(kind=pass_kind, tracks=tuple(only_tracks))
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
                force_overread=self._params.force_overread,
                read_offset_override=self._params.read_offset_override,
                metadata=self._params.metadata,
                disc_track_total=self._params.disc_track_total,
                read_speed=read_speed,
                only_tracks=only_tracks,
            )
            # Snapshot the command line as soon as we have a handle, BEFORE the
            # read loop — so a rip that dies in its first second still carries
            # the argv that caused it. `getattr` because a backend stand-in may
            # not expose it; an absent argv stays empty rather than raising here,
            # since failing to record diagnostics must never fail the rip.
            self._ripper_argv = tuple(getattr(self._handle, "argv", ()) or ())
            # Keep the FIRST pass's argv as well as the latest.
            #
            # A rip can spawn the ripper more than once — a speed-ladder retry, or
            # (dynamic secure-rerip) a whole-disc pass followed by a targeted
            # `-Z N -l <tracks>` pass over just the tracks AccurateRip did not
            # verify. Only the first pass writes the whole-disc log, so its
            # `Invoked as:` line is the only one the argv-agreement check can
            # compare against. Overwriting this on every pass is what made that
            # check report the auto-fix pass's `-Z`/`-l` as arguments something
            # had injected in transit (real-hardware false alarm, 2026-08-03).
            if not self._ripper_argv_first_pass:
                self._ripper_argv_first_pass = self._ripper_argv
        except RipError as exc:
            log.exception("rip failed to start")
            # RECORD IT with the argv. A rip that never started produces no ripper
            # log and no stdout, so this exception is the *entire* evidence — and it
            # went only to a traceback in a file that is INFO-only by default plus a
            # one-line signal. It now lands in the enumerated diagnostics too, which
            # the report carries whether or not anyone reads the text log.
            diagnostics.exception(
                "ripper.nonzero_exit",
                f"the ripper could not be started: {exc}",
                exc,
                tool="cyanrip",
                argv=self._ripper_argv,
                where="workers.rip_worker.RipWorker._run_rip",
            )
            self.error.emit(str(exc))
            return None
        except Exception as exc:  # noqa: BLE001 — last-resort guard
            log.exception("unexpected error starting rip")
            diagnostics.exception(
                "internal.unexpected_exception",
                f"an unexpected error stopped the rip before it started: {exc}",
                exc,
                tool="cyanrip",
                argv=self._ripper_argv,
                where="workers.rip_worker.RipWorker._run_rip",
            )
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
            self._signal_stop("cancel arrived during the startup window")

        # Stream output. Iteration ends when the ripper closes its stdout
        # (i.e. exits) or when cancel() flips the flag.
        try:
            # Held as an explicit iterator, not just a `for` target, so the cancel
            # branch below can pull the ripper's last words off the pipe.
            lines = iter(self._handle.log_lines())
            for line in lines:
                if self._cancelled:
                    # KEEP THIS LINE, THEN LEAVE. It was already read off the pipe
                    # by the iterator above, and it is the ripper's FIRST output
                    # after our signal — i.e. its answer to being cancelled. The
                    # old `break` discarded it, silently, every single time: the
                    # one line most worth having was the one line guaranteed to be
                    # dropped. Measured, not reasoned — a stand-in ripper's
                    # "Trying to quit" was handed to this loop and was absent from
                    # `captured_stdout` (`docs/testing.md` §5.ay), which is how a
                    # handshake round came to conclude the ripper's signal handler
                    # had never run.
                    #
                    # Retained WITHOUT the progress filter the rest of the loop
                    # applies, deliberately: at a cancel, even a bare progress
                    # redraw is the diagnostic — it says how far the rip had got
                    # when the user stopped it. One line, and the buffer is
                    # head+tail bounded anyway.
                    self._retain_stdout_line(line)
                    self._retain_last_words(lines, line)
                    break
                # `_progress_for` both classifies the line (a numeric progress
                # redraw → not None) AND updates `_current_track` as a side
                # effect, so call it once up front.
                prog = self._progress_for(line)
                is_progress = prog is not None
                # Retain the substantive stream (see `_stdout_lines`). Bounded so
                # a runaway ripper cannot grow this without limit; the cap is far
                # above a real album's few hundred non-progress lines, and it is
                # a *stop*, not a ring buffer, because the head is where the
                # header and the early tracks are.
                if not is_progress:
                    self._retain_stdout_line(line)
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
                        forwarded = _CYANRIP_ETA_CLAUSE.sub("", line)
                        self.log_line.emit(forwarded)
                        # Persist the forwarded stream to log.txt in real time
                        # (DEBUG-gated, so it only lands when Debug logging is on
                        # — the bug-report setting). The in-window log pane is
                        # ephemeral; this survives a freeze/force-kill on disk, so
                        # a bug report shows exactly where the drive stopped. Only
                        # the throttled set is logged (not every redraw), keeping
                        # the volume bounded.
                        log.debug("cyanrip │ %s", forwarded)
                else:
                    self.log_line.emit(line)
                    log.debug("cyanrip │ %s", line)
                # Watch for the "no online metadata" abort so the GUI can heal
                # by re-ripping as unknown (only worth it if this rip wasn't
                # already unknown). Inert whipper-era seam — cyanrip runs -N and
                # never emits these markers. Detection runs on EVERY line.
                if not self._params.unknown and any(
                    m in line for m in _NO_METADATA_MARKERS
                ):
                    self._needs_unknown_retry = True
                # The ripper's OWN error text, kept as the hint when we have
                # nothing better. cyanrip said "Invalid track number 17, list
                # has 16 tracks!" and the user was shown "Rip failed." — the
                # tool had already diagnosed it and we threw the diagnosis away
                # (rig, 2026-08-02). CLAUDE.md requires capturing a dependency's
                # error output rather than swallowing it; this is that, on the
                # path the user actually reads.
                #
                # `if not self._failure_hint` so the specific, actionable hints
                # below always outrank a raw line: first error wins, and a
                # tailored message beats a verbatim one.
                if _RIPPER_ERROR_RE.match(line):
                    if not self._failure_hint:
                        self._failure_hint = line.strip()
                    # EVERY matched fatal is recorded, not only the first. The hint is
                    # deliberately "first error wins" because a status label holds one
                    # sentence — but the *report* should carry all of them: a rip that
                    # printed four diagnostics and showed one is three facts short, and
                    # the later ones are often the consequence that explains the first.
                    diagnostics.error(
                        "ripper.fatal_message",
                        line.strip(),
                        tool="cyanrip",
                        where="workers.rip_worker.RipWorker._run_rip",
                    )
                giveup = _TRACK_GIVEUP_RE.search(line)
                if giveup:
                    track = giveup.group("track")
                    tailored = (
                        f"Track {track} couldn't be read after repeated tries. "
                        "The disc may be scratched or dirty — clean it and try "
                        "again."
                    )
                    # KEEP THE RIPPER'S OWN SENTENCE when we already have one. This
                    # assigned unconditionally, so a verbatim fatal matched *one line
                    # earlier* — by the branch directly above, whose comment says
                    # "first error wins" — was overwritten by this canned advice. The
                    # comment described a rule the code did not implement for this
                    # branch. When both exist the tool's words lead and the advice
                    # follows, so nothing is lost either way.
                    if self._failure_hint:
                        self._failure_hint = f"{self._failure_hint} — {tailored}"
                    else:
                        self._failure_hint = tailored
                # Status text first (covers the pre-track disc scan and
                # the encode/tag sub-phases), then the numeric progress
                # that drives the bar.
                # Prefer the metadata track count (known from __init__, so the
                # label is right from the very first progress line) and fall back
                # to the count parsed from cyanrip's disc banner.
                desc = _describe_activity(
                    line,
                    len(self._track_ms) or self._total_tracks,
                    # The pass DECLARED its kind when it started (`_rip_once`), so
                    # the label follows from the invocation rather than from a
                    # guess about what the numbers mean.
                    securing=self._pass_kind == _PASS_REFIX,
                )
                # Append our own estimate to a progress phase (never cyanrip's
                # per-op ETA as the headline figure — see _album_eta_text /
                # _describe_activity). `prog[1]` is the CURRENT OPERATION's own
                # percentage, which is what the securing pass estimates from;
                # handing it over explicitly keeps that input pinned to this tick.
                if desc is not None and prog is not None:
                    desc += self._album_eta_text(prog[0], prog[1])
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
                # Each time cyanrip finishes a track it emits a "Track N ripped…"
                # line: tell the GUI so it can mark that row done in the live
                # Status column, AND (incremental report snapshot) re-parse the
                # .log into a PARTIAL .platterpus.json beside it. The snapshot
                # closes the last durability gap — a HARD stop (power loss,
                # SIGKILL, an OS crash) that never reaches the GUI's finish handler
                # still leaves the tracks completed so far on disk. A clean
                # cancel/finish is still written by the GUI afterward, superseding
                # these partials.
                done_match = _CYANRIP_TRACK_DONE.search(line)
                if done_match:
                    self.track_completed.emit(int(done_match.group("track")))
                    if incremental:
                        self._write_incremental_report(out_dir)
        except Exception as exc:  # noqa: BLE001
            log.exception("error reading ripper stdout")
            # The stdout we DID capture before the break is the only account of how
            # far the rip got; hand it over rather than letting the traceback stand
            # alone. (`captured_stdout` is already head+elision+tail bounded.)
            diagnostics.exception(
                "internal.unexpected_exception",
                f"reading the ripper's output failed mid-rip: {exc}",
                exc,
                tool="cyanrip",
                argv=self._ripper_argv,
                detail=self.captured_stdout,
                where="workers.rip_worker.RipWorker._run_rip",
            )
            # The subprocess is still running (we broke out of the read loop
            # abnormally, before wait()). Stop it so it doesn't keep holding the
            # drive and contend with a retry — best-effort, non-blocking.
            self._signal_stop("stdout stream error")
            self.error.emit(f"rip stream error: {exc}")
            return None

        exit_code = self._reap_ripper()
        self._ripper_exit_code = exit_code
        success = (exit_code == 0) and not self._cancelled
        if exit_code not in (0, None) and not self._cancelled:
            # The ripper's OWN verdict on the rip, with its argv and everything it
            # said. Recorded here rather than left to the GUI: this is the one place
            # that holds all three at once, and the report used to carry the exit code
            # in `outcome` with nothing enumerating it as a problem.
            diagnostics.record_command_failure(
                "ripper.nonzero_exit",
                "cyanrip",
                self._ripper_argv,
                exit_code,
                self.captured_stdout,
                message=(
                    f"the ripper exited {exit_code}"
                    + (f" — {self._failure_hint}" if self._failure_hint else "")
                ),
                where="workers.rip_worker.RipWorker._run_rip",
            )
        log_path = self._find_log_path(out_dir, since=self._rip_started_at)
        return success, str(log_path) if log_path else ""

    def _retain_last_words(self, lines: Iterator[str], first: str) -> None:
        """Pull the ripper's cancel message off the pipe, if it is already there.

        **Why this is not just "read one more line".** cyanrip's signal handler
        emits ``"\\r\\nTrying to quit\\n"`` in a *single* ``write(2)``. The leading
        ``\\r\\n`` terminates whatever progress redraw was mid-line, so the first
        line we read after our signal is that **terminator — blank** — and the
        message we actually want is the one after it. Retaining "one more line"
        therefore keeps a bare ``\\r`` and still loses the sentence.

        **Why it cannot block.** We read on only while the line we just took is
        blank. A blank line is itself proof the ripper just completed a write, and
        that write was atomic — 17 bytes, far below ``PIPE_BUF`` (4096), so a pipe
        write of that size is indivisible — which means the remainder of it is
        **already sitting in the pipe buffer** and the next read is satisfied
        without waiting on the ripper. A silent ripper produces no blank line and
        so gets no extra read at all: the cancel stays fast, which is the property
        the original `break` was protecting.

        Bounded anyway (``_CANCEL_LAST_WORDS_LINES``), because "cannot block"
        should not be the only thing standing between a cancel and a wedged GUI.
        """
        line = first
        for _ in range(_CANCEL_LAST_WORDS_LINES):
            if line.strip():
                # Not a redraw terminator — we already have real text, stop.
                return
            nxt = next(lines, None)
            if nxt is None:  # the ripper exited; nothing more to take
                return
            self._retain_stdout_line(nxt)
            line = nxt

    def _retain_stdout_line(self, line: str) -> None:
        """Keep one line of the ripper's output in the diagnostic record.

        Bounded head + rolling tail, because the head is where the header and the
        early tracks are and the tail is where a dying message is — a head-only
        cap drops precisely the line that explains a failure. Whatever falls out
        of the middle is *counted* into ``_stdout_elided`` and reported by
        ``captured_stdout``, never silently dropped: a silent truncation reads as
        completeness.

        One method rather than two call sites doing it inline, so the cancel path
        (which has its own reason to retain a line) cannot drift from the main
        loop's bookkeeping.
        """
        if len(self._stdout_lines) < _MAX_STDOUT_LINES:
            self._stdout_lines.append(line)
            return
        self._stdout_tail.append(line)
        if len(self._stdout_tail) > _STDOUT_TAIL_LINES:
            self._stdout_tail.pop(0)
            self._stdout_elided += 1

    def _reap_ripper(self) -> int | None:
        """Reap the ripper process, bounded. Returns its exit code, or ``None``.

        **This replaced a bare ``self._handle.wait()``, which was a textbook
        pipe deadlock.** The read loop above does not always run to EOF: on cancel
        it `break`s, and on a stream error it bails out. Either way the ripper's
        stdout pipe stops being drained while the ripper may still be writing to it.
        A pipe holds ~64 KiB; once it is full the child blocks in ``write()``, so it
        never exits, so an unbounded ``wait()`` never returns — and it is waiting on
        the rip worker's own thread, which then never finishes, which then gets
        abandoned at shutdown. Python's own docs warn about exactly this shape
        (``Popen.wait`` + a live ``PIPE``); we had it.

        The escalation is ``RipHandle.cancel()``, which sends SIGTERM then SIGKILL
        to the process *group*. That method already existed, fully implemented and
        documented — and was **called from nowhere in the codebase**, so the
        escalation the cancel path's docstring promised did not exist. It does now,
        and this is the only correct place for it: it blocks, so it must run off the
        GUI thread, and this method always does.

        SIGKILL ends the writer, which is what unblocks the pipe — so the deadlock
        is broken by the escalation, not merely timed out of. ``None`` comes back
        only when even SIGKILL could not reap it (a reader wedged in an
        uninterruptible drive ioctl), and the caller treats that as "not a clean
        exit" rather than hanging.
        """
        handle = self._handle
        if handle is None:  # pragma: no cover — callers hold a handle
            return None
        # Make sure the ripper has been told to stop before we wait on it. This
        # used to call `handle.terminate()` directly on the reasoning that "asking
        # again is free and idempotent" — true of `Popen`, FALSE of cyanrip, whose
        # second signal is `_exit(1)` with no log footer and no checksum. It goes
        # through `_signal_stop`, which sends at most one per rip; on a cancel the
        # signal has already gone and this is a no-op.
        if self._cancelled:
            self._signal_stop("before reaping a cancelled rip")
        try:
            return handle.wait(timeout=_RIPPER_EXIT_GRACE_S)
        except subprocess.TimeoutExpired:
            log.warning(
                "ripper still running %.1fs after we stopped reading its output — "
                "escalating to SIGTERM/SIGKILL on the process group. Its stdout "
                "pipe is no longer drained, so it may be blocked writing to a full "
                "pipe rather than doing work.",
                _RIPPER_EXIT_GRACE_S,
            )
        exit_code = handle.cancel(
            term_timeout=_RIPPER_TERM_GRACE_S, kill_timeout=_RIPPER_KILL_GRACE_S
        )
        if exit_code is None:
            log.error(
                "could not reap the ripper even after SIGKILL; treating the rip as "
                "not cleanly finished. The drive may still be held — a force stop "
                "or a drive reset is the remaining recovery."
            )
            # Tri-state, made explicit in the report: `null` here means the child was
            # never reaped, which is a different and more serious fact than exit 0,
            # and the report must never let the two look the same.
            diagnostics.error(
                "ripper.unreapable_child",
                "the ripper could not be reaped even after SIGKILL — it is probably "
                "stuck in an uninterruptible drive ioctl, so the drive may still be "
                "held. This rip has NO exit status; success or failure rests on the "
                "log alone.",
                tool="cyanrip",
                argv=self._ripper_argv,
                exit_code=None,
                where="workers.rip_worker.RipWorker._reap_ripper",
            )
        return exit_code

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

    def _reset_pass_progress(
        self, *, kind: str = _PASS_ALBUM, tracks: tuple[int, ...] = ()
    ) -> None:
        """Reset the per-pass progress state before a (re-)rip pass, so a re-rip's
        bar sweeps fresh from 0 instead of inheriting the previous pass's value.

        ``kind`` / ``tracks`` declare what the pass about to run *is* — see
        ``_PASS_ALBUM`` / ``_PASS_REFIX``. Called only by :meth:`_rip_once`, which
        passes its own arguments straight through; the default keeps a direct call
        (tests) behaving as it always did.
        """
        self._pass_kind = kind
        self._pass_tracks = tracks
        # THE OVERALL BAR IS NOT REWOUND FOR A SECURING PASS. A whole-disc pass
        # legitimately sweeps from zero again — it is re-reading the whole disc. A
        # securing pass is not: every track is already ripped, so zeroing the album
        # bar would be claiming the album got un-ripped. On the rig it did exactly
        # that, 94.77% -> 35.45%, and a progress bar that goes backwards is read as
        # "something went wrong" by every user who has ever seen one.
        if kind != _PASS_REFIX:
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
        # Also clear the restart detector's memory: the fraction is about to drop to
        # 0 legitimately, and that is not the anomaly the detector exists to catch.
        self._eta_last_frac = None
        self._eta_stall_frac = None
        self._eta_stall_since = None
        self._eta_stalled = False
        # And the task-level liveness / re-read state: a new pass re-reads tracks
        # this rip has already read, so carrying the previous pass's percentage in
        # would look like a restart-within-a-track and mislabel the first line of
        # the new pass as a secure re-read.
        self._task_forward_pct = None
        self._task_forward_at = None
        self._reread_track = None
        self._reread_pass = 0
        self._task_pct_seen = None
        # The securing pass's per-read estimate state. Cleared unconditionally:
        # it is scoped to one read of one track, and nothing about it survives a
        # pass boundary in either direction.
        self._refix_rate_window = []
        self._refix_smoothed_s = None

    def _auto_fix_tracks(
        self,
        tracks: list[int],
        rerip_z: int,
        trigger: str,
        album_log_path: str = "",
        first_pass_crcs: dict[int, str] | None = None,
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
        self.status.emit(f"Re-ripping track(s) {listed} ({why}) to secure them…")
        self.log_line.emit(
            f"[auto-fix] re-ripping track(s) {listed} at -Z {rerip_z} — they "
            f"{why} (the rest of the album is kept as-is)"
        )
        tmp_root: Path | None = None
        self._secure_rerip_interrupted = True
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
                # THE DECLARATION. This is the one call site that runs after the
                # album is already on disk, and saying so here is what stops the
                # album progress model — bar, label and ETA — from being applied
                # to a one-track re-read. See `_PASS_REFIX`.
                pass_kind=_PASS_REFIX,
            )
            if outcome is None:
                return  # re-rip failed to start/stream — originals untouched
            success, rerip_log_path = outcome
            if not success or not rerip_log_path:
                return
            rerip_log = self._parse_log(rerip_log_path)
            fixed: list[int] = []
            # One record per track actually swapped — used to write the addendum
            # sidecar, so the folder's text still describes the audio on disk.
            swapped: list[SupersededTrack] = []
            # A re-rip we asked for ONE track must come back describing exactly
            # that track. This is defence against a verdict-attribution bug, not
            # against cyanrip: the -Z verdict has already been mis-attributed once
            # by a whole track (the fork indented its `Done;` line and every
            # verdict shifted, 2026-07-31), and the consequence *here* is the worst
            # one in the program — copying a read that never reproduced over audio
            # that was fine, and recording the wrong verdict as the last word.
            #
            # So the swap requires positive attribution, and a surprise degrades to
            # "don't swap" rather than to a coin flip. Hardware-gated code the
            # suite cannot reach is exactly where a cheap guard earns its keep.
            rerip_numbers = {
                getattr(t, "number", None)
                for t in getattr(rerip_log, "tracks", ()) or ()
            }
            unexpected = rerip_numbers - set(tracks)
            if unexpected:
                log.warning(
                    "re-rip of track(s) %s returned a log describing track(s) %s — "
                    "refusing to swap any file, because the verdict cannot be "
                    "attributed with confidence",
                    sorted(tracks),
                    sorted(n for n in unexpected if n is not None),
                )
                # Bare return: the enclosing `try` has a `finally` that removes
                # `tmp_root`, and every other early exit here leaves the same way.
                return
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
                        # The WHOLE per-track record, not just the CRC. Round 7
                        # lap 10 H5: the CRC-only addendum left the archived
                        # AccurateRip v1/v2 and the "not attempted" re-read verdict
                        # describing bytes we had deleted.
                        swapped.append(
                            self._superseded_record(
                                track, (first_pass_crcs or {}).get(number, "")
                            )
                        )
                        # Keep the re-rip's parsed record: it is the SHIPPED file's
                        # read, so it — not the first pass — is what the report and
                        # the EAC-layout log must describe.
                        self._swapped_track_records[number] = track
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
            # Every requested track now has a recorded outcome, so the pass ran
            # to completion — whatever its verdicts were.
            self._secure_rerip_interrupted = False
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
        swapped: list[SupersededTrack],
    ) -> None:
        """Write the swap addendum to a **sidecar** beside the album ``.log``.

        After the auto-fix replaces a track's FLAC with a converged re-read, the
        first-pass log's record for that track describes the *discarded* bytes,
        not the file now on disk — so the folder's proof text would misrepresent
        the shipped audio (#19). The addendum says which rows are superseded.

        **It used to be appended to the ripper's log, and that was a real defect**
        (round 7 lap 10, H1): cyanrip's log ends with its own ``Log FUN512:``
        self-checksum and ``cyanrip --verify-log`` rejects trailing content, so
        every auto-fixed disc shipped a log the ripper called modified. The
        ripper's log is now left byte-exact; see :mod:`platterpus.rip_addendum`
        for the reasoning and for the read path that keeps the supersede visible.

        The method name is kept (tests and the call site above reference it) even
        though it no longer appends; the docstring is the honest description.
        Best-effort: a write failure is recorded to diagnostics and swallowed —
        it must never abort a rip whose audio is already correct, and the
        ``.platterpus.json`` report's ``retried_tracks`` is the structured record
        regardless.
        """
        if not album_log_path or not swapped:
            return
        # THE SIDECAR STAYS, and the reason is an ORDERING one that a file count
        # does not outweigh. `main_window_rip`'s post-rip finish handler re-parses
        # this log through `read_log_with_addendum` BEFORE `write_report` has run,
        # so at that moment the `.platterpus.json` does not exist yet. Retiring the
        # file made that re-parse read the DISCARDED pass's CRC — reintroducing the
        # exact defect the addendum was created to prevent (#19), and the trap this
        # module's docstring names: fixing one problem by making the supersede
        # invisible.
        #
        # `rip_addendum.addendum_text` now ALSO rebuilds the block from the report
        # when no sidecar is present, which covers a folder written by an older
        # build and any offline re-parse of a folder whose sidecar was lost. That is
        # added robustness, not a replacement.
        #
        # Still never appended to the ripper's own log: it ends with cyanrip's
        # `Log FUN512:` checksum and `--verify-log` rejects trailing content by
        # design (round 7 lap 10).
        written = write_addendum(album_log_path, trigger, swapped)
        if written is not None:
            self.log_line.emit(
                f"[auto-fix] wrote the supersede record to {written.name} — the "
                "ripper's own log is left unmodified so it still verifies."
            )

    @staticmethod
    def _superseded_record(track: object, previous_crc: str = "") -> SupersededTrack:
        """Build the sidecar's row for one swapped track, from the re-rip's log.

        Every value comes from the **re-rip's** parsed record, which is the read
        that shipped. Reaching for the first pass here is the H5 bug: the archived
        block's AccurateRip v1/v2 and its ``not attempted`` re-read verdict belong
        to bytes we deleted.

        ``previous_crc`` is the one deliberate exception, and it is a *comparison*
        rather than a description: it is the first pass's CRC, carried so the
        addendum can state whether the re-read **confirmed** that read or
        **replaced** it. Empty means not determined, which is a real answer and is
        rendered as one.
        """

        def _ar(name: str) -> str:
            result = getattr(track, name, None)
            if result is None:
                return ""
            verdict = str(getattr(result, "result", "") or "")
            crc = str(getattr(result, "local_crc", "") or "")
            confidence = getattr(result, "confidence", None)
            parts = [p for p in (crc, verdict) if p]
            if isinstance(confidence, int):
                parts.append(f"confidence {confidence}")
            return " — ".join(parts)

        converged = getattr(track, "secure_rerip_converged", None)
        reads = getattr(track, "rip_count", None)
        if converged is True:
            reread = (
                f"converged after {reads} reads"
                if isinstance(reads, int) and reads > 0
                else "converged"
            )
        elif converged is False:
            reread = "did not converge (kept anyway only if it read cleanly)"
        else:
            reread = ""
        return SupersededTrack(
            # int_or_none, not int(): the never-raises contract covers this module,
            # and a track number reaches us from parsed external text.
            number=int_or_none(getattr(track, "number", None)) or 0,
            filename=str(getattr(track, "filename", "") or ""),
            crc=str(
                getattr(track, "copy_crc", "") or getattr(track, "test_crc", "") or ""
            ),
            accuraterip_v1=_ar("accuraterip_v1"),
            accuraterip_v2=_ar("accuraterip_v2"),
            accuraterip_offset=_ar("accuraterip_offset"),
            secure_reread=reread,
            previous_crc=previous_crc,
        )

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

        # read_log_with_addendum, not read_text: a re-parse that reads the ripper's
        # log alone gets the checksums of bytes the auto-fix deleted. The addendum
        # lives in a sidecar (round 7 lap 10 H1) precisely so the ripper's log stays
        # verifiable, which means the reader is now the only thing keeping the
        # supersede visible.
        text = read_log_with_addendum(log_path_str)
        if not text:
            return None
        return (
            parse_cyanrip_log(text)
            if looks_like_cyanrip_log(text)
            else parse_rip_log(text)
        )

    @property
    def captured_stdout(self) -> str:
        """Everything substantive the ripper printed, as one text blob.

        The recovery source when the logfile is truncated, and the artifact the
        cyanrip project cannot produce for itself (it has no physical drive).
        Empty until the rip starts. Safe to read from the GUI thread after
        ``finished`` — the worker no longer touches the lists by then.

        On a rip that overran the retention cap this is the head, an explicit
        elision marker naming the number of discarded lines, and the tail. The
        marker matters as much as the tail does: an unmarked jump would read as
        a ripper that fell silent, which is a different (and alarming) fact.
        """
        if not self._stdout_tail:
            return "\n".join(self._stdout_lines)
        middle = (
            [_STDOUT_ELISION.format(count=self._stdout_elided)]
            if self._stdout_elided
            else []
        )
        return "\n".join([*self._stdout_lines, *middle, *self._stdout_tail])

    @property
    def ripper_exit_code(self) -> int | None:
        """The ripper's exit status, or ``None`` if it was never reaped.

        ``None`` is a real outcome, not a placeholder: a child wedged in a drive
        ioctl is in uninterruptible sleep where even SIGKILL does not land, and
        :meth:`_reap_ripper` bounds its wait rather than blocking forever. A
        negative value is a signal number (``-9`` = we SIGKILLed the group).
        """
        return self._ripper_exit_code

    @property
    def ripper_argv(self) -> tuple[str, ...]:
        """The exact command line handed to the ripper, for the report.

        Empty until the rip starts. This is the single most useful thing for
        reproducing a failure by hand, and it is recorded verbatim — including
        the metadata arguments, since an out-of-range ``-t`` is precisely the
        kind of defect that reads as an unexplained "Rip failed."
        """
        return self._ripper_argv

    @property
    def ripper_argv_first_pass(self) -> tuple[str, ...]:
        """The argv of the FIRST pass, when the rip ran the ripper more than once.

        Equal to :attr:`ripper_argv` on a single-pass rip. It differs when a
        speed-ladder retry or a dynamic secure-rerip spawns the ripper again —
        and only the first pass writes the whole-disc log, so this is the one
        that can be compared against that log's ``Invoked as:`` line. Comparing
        the *last* pass instead reported the auto-fix pass's ``-Z``/``-l`` as
        arguments injected in transit.
        """
        return self._ripper_argv_first_pass

    @Slot()
    def cancel(self) -> None:
        """Cancel an in-progress rip — NON-BLOCKING (safe from the GUI thread).

        Sets the cancel flag (read by the worker's iteration loop) and sends a
        non-blocking SIGTERM via ``terminate()`` — it never waits, so a wedged
        drive can't freeze the caller. Both the flag write and ``terminate()`` are
        thread-safe (atomic bool; subprocess signalling is), so this is safe to call
        from the GUI thread.

        Reaping happens on the worker thread in :meth:`_reap_ripper`, which is
        bounded and escalates to SIGKILL on the process group. An earlier version of
        this docstring said the *GUI's force-stop timer* provided that escalation.
        It does not: ``drive_control`` kills whatever holds the **device**, which is
        a different and coarser thing, and the process-group escalation it described
        (``RipHandle.cancel``) was called from nowhere. Fixed 2026-07-29 — the claim
        is now true, but it was documentation describing an intention.
        """
        self._cancelled = True
        self._signal_stop("user cancel")

    def _signal_stop(self, why: str) -> None:
        """SIGTERM the ripper's process group — **at most once per rip**.

        The single chokepoint for every stop signal this worker sends. It exists
        because **a second signal is not a free repeat of the first.**

        ``Popen.terminate()`` is idempotent, and three call sites here reasoned
        from that: cancel, the startup-window race, and ``_reap_ripper``'s
        pre-reap "asking again is free" nudge. It is idempotent *for us*. It is
        not idempotent for **cyanrip**, whose handler is::

            if (quit_now) { SIG_WRITE_LIT("Force quitting\\n"); _exit(1); }

        — an escape hatch for a user hammering Ctrl-C. ``_exit(1)`` runs no
        ``atexit``, so the ripper writes **no completion footer and no FUN512
        checksum**, and the log it leaves behind is an unverifiable fragment.

        We were sending two, and not 50 ms apart as a human would: measured at
        **0.445 ms** on this code path (`docs/testing.md` §5.ay). That destroyed
        the cancelled rip's log on the 2026-08-24 rig run — exit 1, no footer, no
        checksum — and we spent a handshake round attributing it to the ripper.

        Suppressing the repeat costs nothing, because the guarantee the pre-reap
        nudge was there to provide ("the process has been told to stop before we
        wait on it") is already satisfied by the signal that was actually sent —
        and the real escalation is untouched: ``_reap_ripper`` still bounds its
        wait and still escalates to SIGTERM→SIGKILL on the process *group*.
        """
        with self._sigterm_lock:
            handle = self._handle
            if handle is None:
                # A cancel during the startup window, before the subprocess exists.
                # Nothing to signal and nothing recorded, so the startup-window
                # re-check in `_rip_once` still delivers the first signal.
                return
            if self._sigterm_sent_for is handle:
                log.debug(
                    "ripper stop already signalled — NOT sending a second SIGTERM "
                    "(%s). A second signal makes cyanrip _exit(1) without writing "
                    "its log's completion footer or checksum.",
                    why,
                )
                return
            self._sigterm_sent_for = handle
            log.info("signalling the ripper to stop (SIGTERM, %s)", why)
            try:
                handle.terminate()
            except Exception:  # noqa: BLE001 — best-effort, must not mask caller
                log.exception("terminate() raised; ignored (%s)", why)

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
            task = _percent_or_none(match.group("pct"))
            if task is None:
                return None
            return self._bump_overall(task * 0.05), task

        match = _TRACK_PHASE_PATTERN.search(line)
        if match:
            track = int_or_none(match.group("track"), field="progress track number")
            total = int_or_none(match.group("total"), field="progress track total")
            if track is None or total is None:
                return None
            self._current_track = track
            self._total_tracks = total
            task = _percent_or_none(match.group("pct"))
            if task is None:
                return None
            self._note_task_progress(self._current_track, task)
            return self._overall_for_pass(self._current_track, task), task

        match = _LENGTH_PHASE_PATTERN.search(line)
        if match:
            done = int_or_none(match.group("track"), field="length-phase track")
            total = int_or_none(match.group("total"), field="length-phase total")
            if done is None or total is None:
                return None
            frac = done / total if total else 1.0
            return self._bump_overall(95.0 + frac * 5.0), 100.0

        # --- cyanrip lines (mutually exclusive with whipper's formats) ---

        match = _CYANRIP_DISC_TRACKS.search(line)
        if match:
            # Total learned from the start report; no bar movement yet.
            total = int_or_none(match.group("total"), field="disc track total")
            if total is not None:
                self._total_tracks = total
            return None

        match = _CYANRIP_TRACK_PROGRESS.search(line)
        if match:
            track = int_or_none(match.group("track"), field="cyanrip track number")
            if track is None:
                return None
            self._current_track = track
            self._record_cyanrip_eta(match.group("eta"))
            task = _percent_or_none(match.group("pct"))
            if task is None:
                return None
            self._note_task_progress(self._current_track, task)
            return self._overall_for_pass(self._current_track, task), task

        match = _CYANRIP_TRACK_DONE.search(line)
        if match:
            done = int_or_none(match.group("track"), field="completed track number")
            if done is None:
                return None
            # task=100 → the end of this track's slice (its full length consumed).
            return self._overall_for_pass(done, 100.0), 100.0

        return None

    def _overall_for_pass(self, current_track: int, task_pct: float) -> float:
        """The overall bar's value for this progress line, for the pass we are in.

        ALBUM pass → the usual "(track, within-track %) mapped into the 5-95% read
        band" model, monotonic via :meth:`_bump_overall`.

        SECURING pass → **the bar does not move.** It is lifted once to the floor of
        the reserved post-rip band (``_POST_RIP_BAND_START``) — a step forward that
        marks "the reading you asked for is finished, this is the checking phase" —
        and then holds there for the whole pass. Three alternatives were considered
        and rejected, and the reasoning is recorded because a frozen bar looks like
        an oversight to the next reader:

        * **Recomputing the album position from the re-ripped track** is what shipped
          and is the bug: track 5 of 14 maps to ~35%, so the bar rewound 94.77% ->
          35.45% and told the user the album had un-ripped itself.
        * **Advancing it to 100%** would claim the rip is finished while a file may
          still be swapped in — and the last thing this phase can do is decide the
          original was better and change nothing.
        * **Sweeping it through the 95-100% band with the securing pass's own
          progress** was the tempting one. It fails on the common case: the pass
          usually re-rips ONE track, so its first read alone fills the whole band,
          the bar sits at ~100% for every subsequent re-read, and the `>= 99.9%`
          "effectively done" guard silences the estimate. A bar that reaches the end
          and then waits is a worse lie than one that visibly holds.

        The phase's real motion lives where it is measurable and honest instead: the
        **task** bar (the current read's own 0-100%, still returned unchanged beside
        this value) and the **status line**, which names the track, the re-read
        number, and a countdown scoped to the read that is running. A dedicated
        third bar would be the nicest answer and is a GUI change, not a worker one —
        recorded here as the extension point rather than half-built.
        """
        if self._pass_kind == _PASS_REFIX:
            return self._bump_overall(_POST_RIP_BAND_START)
        return self._bump_overall(self._overall_from_track(current_track, task_pct))

    def _note_task_progress(self, track: int, task_pct: float) -> None:
        """Follow the CURRENT OPERATION's own percentage, to tell a secure re-read
        apart from a stalled drive.

        Called for every per-track progress line, before the album bar is computed.
        Maintains two things the album bar cannot express:

        * **Liveness.** ``_task_forward_at`` is stamped whenever this percentage
          makes a real forward step (or restarts). The album bar freezes during a
          re-read; this does not, so the stall detector gets a signal that means
          "the drive is reading" rather than "the bar moved".
        * **Re-read passes.** A big drop with the track number unchanged is cyanrip
          starting that track's read over (``-Z``). We count the passes, because
          while one is running the album fraction is pinned and any ETA computed
          from it is arithmetic on a constant — measured climbing 54m -> 5h40m in
          70 seconds (2026-08-05, b8, track 3).

        Pure bookkeeping; never raises, emits nothing, touches no widgets.
        """
        now = time.monotonic()
        if track != self._reread_track:
            # A different track: a genuinely new operation. Record how many extra
            # passes the one we're leaving needed — that is the honest measure of how
            # hard the disc was to read there, and it is nowhere else in the record.
            #
            # No window reset is needed HERE even though the fraction is about to
            # jump forward to catch up on everything the freeze hid: the window was
            # emptied when the re-read STARTED (below), and the hold path
            # `_album_eta_text` takes during a re-read returns before appending, so
            # by now it holds nothing that predates the freeze. Stated rather than
            # re-cleared defensively, because a guard no test can distinguish from
            # its absence is a claim of protection, not protection.
            if self._reread_pass:
                log.info(
                    "secure re-read of track %s finished after %d extra pass(es); "
                    "resuming the album ETA on a fresh rate window",
                    self._reread_track,
                    self._reread_pass,
                )
            self._reread_track = track
            self._reread_pass = 0
            self._task_pct_seen = task_pct
            self._task_forward_pct = task_pct
            self._task_forward_at = now
            # A different track is a different read, so the securing pass's
            # per-read estimate starts over. Keeping the old window would measure
            # the new track's rate against the previous track's percentages.
            self._refix_rate_window = []
            self._refix_smoothed_s = None
            return
        previous = self._task_pct_seen
        if previous is not None and task_pct < previous - _REREAD_TASK_DROP_PCT:
            # Same track, percentage restarted: another secure re-read pass.
            self._reread_pass += 1
            log.info(
                "track %s is being re-read to verify it (pass %d) — its progress "
                "restarted at %.0f%%; the album bar cannot advance during a "
                "re-read, so the ETA holds instead of projecting from a frozen "
                "fraction",
                track,
                self._reread_pass + 1,
                task_pct,
            )
            # The window's older points are from BEFORE the freeze. Left in place
            # they keep the divisor alive just long enough to inflate the estimate
            # (measured: 0.22pp of pre-freeze movement still in a 90 s window,
            # yielding 498 minutes). Drop them; the hold path takes over.
            self._eta_rate_window = []
            # Same rule for the securing pass's per-read window, for the same
            # reason one level down: its points describe the read that just ended,
            # and a window spanning the restart measures a rate no drive achieved.
            # The smoothed value goes too — a read that has just restarted has ALL
            # of its time ahead of it, and an EMA seeded with "nearly finished"
            # would spend the next several seconds insisting so.
            self._refix_rate_window = []
            self._refix_smoothed_s = None
            self._task_forward_pct = task_pct
            self._task_forward_at = now
        elif (
            self._task_forward_pct is None
            or task_pct >= self._task_forward_pct + _TASK_LIVENESS_MIN_PCT
        ):
            self._task_forward_pct = task_pct
            self._task_forward_at = now
        self._task_pct_seen = task_pct

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


def _describe_activity(
    line: str, total_tracks: int = 0, *, securing: bool = False
) -> str | None:
    """Return a short human status for a ripper progress line, or None.

    Matches cyanrip's progress lines (and the inert whipper-format seam). Used
    to keep the status label live across every phase — especially the pre-track
    disc scan, which otherwise left the GUI on "Starting rip…" for a minute-plus
    and looked hung.

    `total_tracks` is the disc's track count when the caller knows it (the worker
    learns it from cyanrip's "Disc tracks: N" banner and independently from the
    MusicBrainz metadata). When it's > 0 the cyanrip progress line reads
    "Ripping track N of M…" so the user can see position at a glance; when it's
    still unknown (0) we omit "of M" rather than show a wrong total.

    `securing` says this line came from the POST-RIP auto-fix pass — a second
    cyanrip run re-reading a couple of tracks after the album is already on disk
    (see `_PASS_REFIX`). There, "of M" is not merely unhelpful but false: the disc
    has 14 tracks and this pass is not working through them, so "Ripping track 5
    of 14…" told a user with a finished album that ten tracks were still to come.
    The securing wording names what is actually happening instead.
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
        if securing:
            # No "of M": this pass is re-reading a track, not working through the
            # disc. The verb says WHY the drive is still spinning after the album
            # finished, which is the question a user actually has at that moment.
            return f"Re-ripping track {match.group('track')} to secure it… {pct:.0f}%"
        # "of M" appears once we know the disc's track count (see the docstring);
        # it turns "Ripping track 12…" into "Ripping track 12 of 17…".
        of_total = f" of {total_tracks}" if total_tracks > 0 else ""
        return f"Ripping track {match.group('track')}{of_total}… {pct:.0f}%"

    match = _CYANRIP_TRACK_DONE.search(line)
    if match:
        outcome = "✓" if match.group("how") == "successfully" else "with errors"
        if securing:
            return f"Track {match.group('track')} re-ripped {outcome}"
        return f"Track {match.group('track')} done {outcome}"

    for phrase, friendly in _NAMED_PHASES.items():
        if phrase in line:
            return friendly
    return None
