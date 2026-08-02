"""Parse cyanrip's rip log into the shared RipLog record.

cyanrip writes a per-album ``Album name.log`` next to the FLACs (one per
output format). Its content mirrors what cyanrip prints to stdout — the
start report, one block per track, and a finish report. Exact format
strings verified against cyanreg/cyanrip master ``src/cyanrip_log.c``:

    cyanrip 0.9.3.1 (...)
    Drive used:     PIONEER BD-RW   BDR-209D (revision 1.10)
    Offset:         +667 samples
    ...
    Track 5 ripped and encoded successfully!
      Preemphasis:   none detected
        Duration:    03:51.44
      EAC CRC32:     A1B2C3D4 (after 2 rips)
      Accurip:       found in database (max confidence: 3)
        Accurip v1:  12345678 (accurately ripped, confidence 3)
        Accurip v2:  9ABCDEF0 (not found, either a new pressing, or bad rip)
    ...
    Tracks ripped accurately: 15/16
    Ripping errors: 0
    Ripping finished at 2026-06-09 12:34:56

We reuse the whipper parser's dataclasses (`RipLog`, `TrackResult`,
`AccurateRipResult`) so the GUI's results table, disc panel, and fidelity
summary work identically on both backends. Mapping notes:

* cyanrip computes ONE EAC CRC32 per track (no whipper-style test+copy
  dual read) — it lands in ``copy_crc`` and ``test_crc`` stays empty, so
  the fidelity summary can tell the two verification models apart.
* `health_status` is normalized to whipper's "No errors occurred"
  phrasing when cyanrip reports 0 ripping errors, so downstream string
  checks behave the same.

Like every parser of external output, this must never raise on arbitrary
text — it degrades to empty fields (institutional rule, docs/testing.md).

**How to read the code below.** The disc-level rows ("Label: value", one line,
no surrounding state) are matched by ORDERED TABLES of (pattern → handler)
entries, so the set of lines we understand is *data* rather than the shape of an
if-chain — see the long comment above ``_RULES_BEFORE_GAPS`` for why that matters
here specifically, and ``_IGNORED_DISC_LINES`` for the rows we skip on purpose.
The section-scoped parsing (the ``Gaps:`` two-liner, ``Paranoia status counts:``,
``Album Loudness Summary:``, the per-track block) stays as explicit control flow,
because those blocks change what the FOLLOWING lines mean.

**Forward compatibility with the maintainer's cyanrip fork (2026-07-31).** Some
lines below exist only in a *future* cyanrip — the ones
``docs/cyanrip-improvements-wanted.md`` asks upstream for (a per-track sample
peak, a per-track elapsed/speed, the ``-Z`` convergence verdict written into the
log file, and a C2 line that states *use* rather than *capability*). They are
parsed here **before** they exist, on purpose and under one hard rule:

    *absent means absent.* A field no ripper reported stays ``None``, and every
    surface then renders exactly what it renders today.

That rule is not tidiness — AppImage users run the **deployed cyanrip 0.9.3**,
which will never print these lines, so one build has to be correct against both.
Each fork-only pattern is marked ``FORK-ONLY`` with the shape it expects, and
every one of them has a test proving today's real logs are unchanged. The one
line in this group that cyanrip 0.9.3 *does* already print is
``Appended:  N frames of silence``, which we simply discarded until now.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace

from platterpus.parsers.rip_log import (
    AccurateRipResult,
    RipLog,
    RippingInfo,
    TrackResult,
)

# THE shared "int() that cannot raise" guard. This module used to carry a private
# copy (`_int_or_none`) — it was the module the hole was found in, and the fix was
# applied here and then centralised in `safe_int` for every other parser. Keeping
# a second implementation alive meant the one place the rule was learned was the
# one place that did not follow it, and its warnings could not name the field.
# See safe_int.py's docstring for why the guard exists at all (CPython refuses a
# digit run longer than 4300 characters, and a `\d+` group is unbounded).
from platterpus.safe_int import int_or_none

log = logging.getLogger(__name__)

# First meaningful line of any cyanrip log/output: "cyanrip 0.9.3.1 (tag)".
# The trailing parenthetical is cyanrip's build tag — "(release)", "(fork)", a
# `git describe` string. Captured into its own field rather than folded into
# `log_creator`, which would change both committed reference logs' value. It is
# the ONLY thing that distinguishes a rip by an unreviewed local build from one
# by official 0.9.3.1, and two such logs of the same disc can carry materially
# different pre-gap metadata and peak values (audit, 2026-07-31).
_HEADER = re.compile(r"^cyanrip\s+(?P<version>\S+)(?:\s+\((?P<build>[^)]*)\))?")
# cyanrip 0.9.3 prints "Device model:   PIONEER …"; older/whipper-style logs use
# "Drive used:". Accept both so the archival "which drive" field is never lost
# (real-log bug: 0.9.3's "Device model:" didn't match, so `drive` came out null).
_DRIVE = re.compile(r"^(?:Drive used|Device model):\s+(?P<drive>.+?)\s*$")
# "Offset:         +667 samples" (sign printed explicitly by cyanrip).
_OFFSET = re.compile(r"^Offset:\s+(?P<sign>[+-])(?P<value>\d+)\s+samples")
# "Overread mode:  read in lead-in/lead-out"              → cyanrip `-O` ON  → EAC "Yes"
# "Overread mode:  fill with silence in lead-in/lead-out" → default (no -O)  → EAC "No"
#
# THIS line — not the neighbouring "Overread:  +2 frames" — is the one that says
# whether the drive actually read the disc's outermost samples. The frame COUNT is
# derived from the read offset and is printed IDENTICALLY in both modes: verified
# against two real logs (the committed overread-OFF reference in
# `output_reference/cyanrip_flac/` says "+2 frames / fill with silence…" while the
# 2026-07-26 overread-ON hardware rip says "+2 frames / read in lead-in/lead-out").
# Keying on the count would therefore report Yes for every rip — worse than the
# "(unknown)" this replaces, which is why the mode line is the only discriminator.
#
# **"Under"read, not just "Over"read.** cyanrip switches the label to
# "Underread mode:" whenever the frame count is negative — and the sign comes
# straight from the read offset (`cyanrip_log.c` picks the label on
# `over_under_read_frames < 0`; `cyanrip_main.c` sets that to
# `sign(offset) * ceil(|offset| / 588)`). So a drive with a NEGATIVE read offset
# prints "Underread mode:" and an `^Overread mode:`-only pattern silently misses
# it — the field would fall back to "(unknown)" for exactly those drives. The
# *value* strings are identical in both cases (cyanrip keys them only on whether
# it reads the lead-in/lead-out), so one pattern with both labels is enough.
_OVERREAD_MODE = re.compile(r"^(?:Over|Under)read mode:\s+(?P<mode>.+?)\s*$")
# "DiscID:         pNtImOkdBm9RMBIalzx0w9cfsYY-" (MusicBrainz Disc ID) and
# "CDDB ID:        E20DFE0E" (freedb/CDDB Disc ID). Both are TOC-derived, so
# they identify the SAME physical disc across re-rips — the key the re-rip
# comparison uses. Values are opaque tokens (no spaces), so \S+ is exact.
# EAC prints the disc as "Artist / Album" under its date line; cyanrip reports
# the same two facts as separate start-report rows.
_ALBUM = re.compile(r"^Album:\s+(?P<value>.+?)\s*$")
_ALBUM_ARTIST = re.compile(r"^Album artist:\s+(?P<value>.+?)\s*$")
# "C2 errors:      unsupported by drive" (BDR-209D) / "... enabled" etc. EAC's
# "Make use of C2 pointers" row. Only an explicit positive counts as Yes — an
# unsupported or unrecognised value is No/unknown, never an invented Yes.
_C2 = re.compile(r"^C2 errors:\s+(?P<text>.+?)\s*$")
# "Paranoia level: max" → EAC's "Read mode" (Secure vs Burst).
_PARANOIA_LEVEL = re.compile(r"^Paranoia level:\s+(?P<text>.+?)\s*$")
# cyanrip's "Gaps:" section, whose single indented line answers EAC's
# "Gap handling" row ("None signalled" on the reference disc). The row was
# rendering "(not reported)" although the ripper does report it (review
# finding, 2026-07-28).
_GAPS_HEADER = re.compile(r"^Gaps:\s*$")
_GAPS_VALUE = re.compile(r"^\s+(?P<value>\S.*?)\s*$")
# Platterpus's own swap addendum, appended after cyanrip's output when the
# per-track auto-fix replaced a track's file. Its text states that these CRCs
# are the SHIPPED file's and supersede the values above — so a re-parse must
# honour it, or anything reading the saved log back (parity.track_copy_crcs,
# the --compare path, a third-party tool) gets CRCs describing bytes that are
# not on disk (review finding, 2026-07-28). The GUI never hit this because it
# patches from live worker state; a re-parse from disk did.
_ADDENDUM_CRC = re.compile(
    r"^\s+Track (?P<number>\d+) \(.*\): CRC (?P<crc>[0-9A-Fa-f]{8})\s*$"
)
_OUTPUTS = re.compile(r"^Outputs:\s+(?P<value>.+?)\s*$")
_DISC_ID = re.compile(r"^DiscID:\s+(?P<value>\S+)")
_CDDB_ID = re.compile(r"^CDDB ID:\s+(?P<value>\S+)")
# "Speed:          default (unchangeable)" / "default (changeable)" / "8x".
# cyanrip's drive banner reports whether the drive can change read speed. When
# it can't, cyanrip ABORTS on `-S` — so the read-speed ladder must read this and
# skip the speed rungs (see RippingInfo.speed_changeable).
_SPEED_CAP = re.compile(r"^Speed:\s+(?P<text>.+?)\s*$")
# A track block opens with its outcome line.
_TRACK_START = re.compile(
    r"^Track (?P<number>\d+) "
    r"(?P<what>ripped and encoded successfully!|ripped and encoded with errors\.|is data:)"
)
# cyanrip's secure re-read (-Z N) verdict for a track, printed on the line JUST
# BEFORE that track's "Track N ripped…" line. Either the reads converged —
#   "Done; (2 out of 2 matches for current checksum ABCD1234)"
# — or it gave up without any two reads agreeing —
#   "Done; (no matches found, but hit repeat limit of 5)".
# The latter is the reliable per-track read-instability signal (see
# TrackResult.secure_rerip_converged). Absent entirely when -Z is off.
#
# **`\s*`, not `^`, and that leading whitespace is the whole point.** These lines
# are emitted from inside `cyanrip_rip_track()`'s repeat loop, which runs BEFORE
# the "Track N ripped…" opener — so wherever they sit on the line, they describe
# the track that is about to open, and they are buffered for it. The maintainer's
# fork indented them (our own ask, and a mistaken one: see the note at
# `_TRACK_SECURE_VERDICT`), which under an `^`-anchored pattern silently handed
# each verdict to the PREVIOUS track instead. Anchoring on POSITION rather than
# on indentation is what makes one build read stock, master and the fork
# identically (audit, 2026-07-31).
#
# The match form requires at least ONE agreeing read. "0 out of 5 matches" is
# not convergence, and cyanrip demonstrably has that wording in its vocabulary —
# its `Repeating ripping (0 out of 1 matches …)` progress line uses it — so a
# bare `\d+` here would read a total failure as a clean verdict.
_SECURE_DONE_MATCH = re.compile(
    r"^\s*Done;\s+\((?P<agreed>\d{1,6})\s+out of\s+(?P<total>\d{1,6})\s+matches\b"
)
_SECURE_DONE_FAIL = re.compile(r"^\s*Done;\s+\(no matches found\b")
# "Total time:     00:59:42.354" — the disc's AUDIO duration (start report).
_TOTAL_TIME = re.compile(r"^Total time:\s+(?P<time>\d{1,2}:\d{2}:\d{2}(?:\.\d+)?)")
_PREEMPHASIS = re.compile(r"^\s+Preemphasis:\s+(?P<text>.+?)\s*$")
# Absolute disc geometry, from each track's "Properties:" block. EAC's TOC table
# is derived from exactly these (its Start and Length columns reproduce
# bit-for-bit — verified against a real EAC log of the same disc). The
# "(with offset: N)" suffix is deliberately IGNORED: EAC's TOC reports the disc's
# own geometry, not the offset-shifted read window.
_START_LSN = re.compile(r"^\s+Start LSN:\s+(?P<value>\d+)")
_END_LSN = re.compile(r"^\s+End LSN:\s+(?P<value>\d+)")
# Anchored like its two siblings — NOT to end-of-line. cyanrip prints a
# "(with offset: N)" suffix on some geometry rows, and a `$` here would drop a
# real pre-gap value the moment it gained one (review finding, 2026-07-28).
# `unknown` is a THIRD answer, not a missing one. The fork prints
# `unknown (sub-channel unreadable)` / `unknown (sub-channel CRC mismatches)`
# when it tried a Q-subchannel scan and could not tell. The old
# `(\d+|none)` matched neither, so the row fell through entirely and the track
# came out identical to a measured "none" — see TrackResult.pregap_state.
_PREGAP_LSN = re.compile(
    r"^\s{1,8}Pregap LSN:\s+(?P<value>\d{1,9}|none|unknown)"
    r"(?:\s+\((?P<reason>[^)]{0,64})\))?"
)
# Fork-only, and authoritative when present: the only field that can express
# track 1 (lead-in + any declared gap). Bounded per the never-unbounded rule.
_PREGAP_LENGTH = re.compile(r"^\s{1,8}Pregap length:\s+(?P<frames>\d{1,9})\s+frames?\b")
# Fork-only provenance. `sub-channel` is the PR #115 payoff — a gap the TOC does
# not declare. Left as free text after the keyword so a future source name is
# recorded rather than dropped.
_PREGAP_SOURCE = re.compile(r"^\s{1,8}Pregap source:\s+(?P<source>\S.{0,63}?)\s*$")


# "  EAC CRC32:     A1B2C3D4" with an optional "(after N rips)" suffix — the
# rip-pass count for the track (1 if absent; higher means -Z secure re-reads).
_EAC_CRC = re.compile(
    r"^\s+EAC CRC32:\s+(?P<crc>[0-9A-Fa-f]{8})"
    r"(?:\s+\(after\s+(?P<rips>\d+)\s+rips?\))?"
)
# "    Accurip v1:  12345678 (accurately ripped, confidence 3)" — the
# parenthetical varies ("not found, either a new pressing, or bad rip").
_ACCURIP_TRACK = re.compile(
    r"^\s+Accurip v(?P<version>[12]):\s+(?P<crc>[0-9A-Fa-f]{8})"
    r"(?:\s+\((?P<result>[^)]*)\))?"
)
# "    Accurip 450: BF62B1DA (matches Accurip DB, confidence 200, track is
# partially accurately ripped)" — the +450-frame offset-pressing variant.
_ACCURIP_OFFSET = re.compile(
    r"^\s+Accurip 450:\s+(?P<crc>[0-9A-Fa-f]{8})"
    r"(?:\s+\((?P<result>[^)]*)\))?"
)
_ACCURIP_CONFIDENCE = re.compile(r"confidence\s+(?P<value>\d+)")
# "  Accurip:       disc found in database (max confidence: 200)" — the per-track
# line that says WHETHER a database lookup happened at all. Also seen: "disabled"
# (AccurateRip off), "error" (lookup failed), "disc not found in database".
#
# It was on the ignore list, with the written reason that the per-track
# `Accurip vN:` rows only print when the disc was found — so a row's presence was
# taken as proof a comparison occurred. **That is false**: cyanrip prints the
# per-track CRC rows in every state, including `disabled`. The consequence was
# that a disc nobody ever looked up rendered as "in DB, no match", which asserts
# both that the disc is in the database and that our read disagreed with it
# (audit, 2026-07-31).
_TRACK_ACCURIP_STATUS = re.compile(r"^\s+Accurip:\s+(?P<status>\S.*?)\s*$")
# Finish report.
_ACCURATE_TOTAL = re.compile(
    r"^Tracks ripped accurately:\s+(?P<hit>\d+)/(?P<total>\d+)"
)
# "Tracks ripped partially accurately: 2/2" — offset-variant matches.
_PARTIAL_TOTAL = re.compile(
    r"^Tracks ripped partially accurately:\s+(?P<hit>\d+)/(?P<total>\d+)"
)
_RIP_ERRORS = re.compile(r"^Ripping errors:\s+(?P<count>\d+)")
_FINISHED_AT = re.compile(r"^Ripping finished at\s+(?P<when>.+?)\s*$")
# The "Paranoia status counts:" block header, then indented "KEY:  N" lines.
_PARANOIA_HEADER = re.compile(r"^Paranoia status counts:\s*$")
_PARANOIA_LINE = re.compile(r"^\s+(?P<key>[A-Z][A-Z_]*):\s+(?P<count>\d+)\s*$")
# Per-track "File(s):" header; the filename is the next indented line.
_FILES_HEADER = re.compile(r"^\s+File\(s\):\s*$")
# ReplayGain / R128 tags cyanrip writes into the FLAC (in the Metadata block):
#   "    REPLAYGAIN_TRACK_GAIN:         -4.10 dB" / "    R128_TRACK_GAIN:  229"
_REPLAYGAIN = re.compile(
    r"^\s+(?P<key>REPLAYGAIN_[A-Z_]+|R128_TRACK_GAIN):\s+(?P<val>.+?)\s*$"
)
# "Album Loudness Summary:" block header (comes after the last track), then
# indented loudness lines shared with the per-track summaries.
_ALBUM_LOUDNESS_HEADER = re.compile(r"^Album Loudness Summary:\s*$")
_LOUDNESS_I = re.compile(r"^\s+I:\s+(?P<v>-?\d+(?:\.\d+)?)\s+LUFS")
_LOUDNESS_LRA = re.compile(r"^\s+LRA:\s+(?P<v>-?\d+(?:\.\d+)?)\s+LU")
# Bounded like every pattern in the fork block: this one feeds the SAMPLE-peak
# sub-header path, and `float()` has no 4300-digit ceiling — it returns `-inf`,
# which slipped past the "> 0.0" refusal and computed a concrete peak of exactly
# 0.0, i.e. digital silence, from unparseable input (audit, 2026-07-31).
_LOUDNESS_PEAK = re.compile(r"^\s+Peak:\s+(?P<v>-?\d{1,6}(?:\.\d{1,6})?)\s+dBFS")
# cyanrip's own log signature, the last line: "Log FUN512: <base64>".
_LOG_CHECKSUM = re.compile(r"^Log FUN512:\s+(?P<sig>\S+)")

# ---------------------------------------------------------------------------
# Lines a FORK of cyanrip will print, parsed before they exist
# ---------------------------------------------------------------------------
# Read the "Forward compatibility" paragraph in this module's docstring first.
# Every pattern in this block is bounded (`\d{1,N}`, never `\d+`): an unbounded
# group is both a ReDoS shape (tests/test_regex_bounded_time.py) and the way an
# over-4300-digit run reaches a conversion at all.
#
# --- 1. the per-track SAMPLE peak (docs/cyanrip-improvements-wanted.md §2.1) ---
#
# THE TRAP THIS BLOCK EXISTS TO AVOID. EAC's per-track `Peak level` row is the
# **sample** peak as a percentage of full scale, and it *cannot exceed 100 %*.
# cyanrip already prints a **true** (4x-oversampled) peak — `True peak:` /
# `Peak: 0.3 dBFS` — which is a DIFFERENT quantity that legitimately goes over
# full scale: all fourteen tracks of the committed reference disc do
# (`REPLAYGAIN_TRACK_PEAK` 1.008499–1.097464, i.e. 100.8 %–109.7 %). So the true
# peak must NEVER reach `TrackResult.peak_level`; rendering it would print a wrong
# number into EAC's row where today we honestly print "(not reported by the
# ripper)". Only a line that says **sample** peak is accepted, and even then a
# value above full scale is refused (see `_sample_peak_fraction`).
#
# FORK-ONLY. Two shapes are accepted because cyanrip's own log has both styles and
# the upstream print site is UNREAD (the doc says so explicitly):
#   inline —   "  Sample peak:  -0.5 dBFS"     (the shape §2.1 proposes)
#   header —   "  Sample peak:" / "    Peak:  -0.5 dBFS"  (how `True peak:`
#              is already printed, so arguably the likelier of the two)
# The unit is REQUIRED. A bare "Sample peak: 0.942" is refused rather than guessed
# at, because dBFS and a linear fraction are indistinguishable in that range and an
# archival peak read in the wrong unit is worse than a labelled gap.
_SAMPLE_PEAK = re.compile(
    r"^\s+(?:Sample peak|Peak level):\s+"
    r"(?P<value>-?\d{1,6}(?:\.\d{1,6})?)\s*(?P<unit>dBFS|%)"
)
# The sub-header form of both peaks. Captured together so the ONE piece of state
# it arms ("which peak does the next `Peak:` line report?") cannot get out of sync:
# a `True peak:` header must actively DISARM sample-peak capture, or the existing
# true peak would silently land in EAC's sample-peak row — the exact bug above.
_PEAK_KIND_HEADER = re.compile(r"^\s+(?P<kind>True|Sample) peak:\s*$")

# --- 2. the per-track extraction speed / elapsed (§2.3) ----------------------
#
# FORK-ONLY. EAC prints a per-track `Extraction speed` as a multiple of 1x read
# speed ("1.6 X"); cyanrip prints no per-track timing at all today, which is 14
# labelled cells on a 14-track disc. §2.3's upstream change is "stamp a monotonic
# clock per track and print the elapsed, optionally with the derived speed", so
# BOTH halves are read: the speed multiple fills EAC's row directly, the elapsed
# is recorded on its own field.
#
# `^\s+` matters: cyanrip's *disc* banner already has a column-0 "Speed:" row
# (the drive's speed-changeability), and `_SPEED_CAP` claims that one. These two
# cannot collide because this pattern requires indentation and that one forbids it.
_TRACK_SPEED = re.compile(
    r"^\s+(?:Extraction speed|Rip speed|Read speed|Speed):\s+"
    # `[xX]\b` so "1.6x" and "1.6 X" both match while "1.6xyz" does not.
    r"(?P<value>\d{1,6}(?:\.\d{1,3})?)\s?[xX]\b"
)
# The elapsed wall-clock. cyanrip's own duration style is a clock ("00:03:13.180"
# in the committed logs, "03:51.44" in older output), so both an optional-hours
# clock and a plain seconds form are accepted. NOT routed through
# `rip_timing.parse_hms_to_seconds`: that helper requires exactly HH:MM:SS and
# would silently drop the MM:SS form cyanrip also prints.
_TRACK_ELAPSED_CLOCK = re.compile(
    r"^\s+(?:Elapsed(?: time)?|Rip time|Extraction time|Time taken):\s+"
    r"(?:(?P<h>\d{1,3}):)?(?P<m>\d{1,3}):(?P<s>\d{1,2}(?:\.\d{1,6})?)\s*$"
)
_TRACK_ELAPSED_SECONDS = re.compile(
    r"^\s+(?:Elapsed(?: time)?|Rip time|Extraction time|Time taken):\s+"
    r"(?P<s>\d{1,7}(?:\.\d{1,6})?)\s*(?:s|sec|secs|seconds)\b"
)

# --- 3. the -Z convergence verdict as a LABELLED per-track row (§2.4) --------
#
# FORK-ONLY. A purpose-written row inside the track block, which is unambiguous
# about which track it describes and can state all three outcomes by name.
#
# **POSITION is the discriminator, never indentation.** This was got wrong once
# and it cost a whole class of bug, so the reasoning is recorded here rather than
# in a commit message nobody will read again:
#
#   * §2.4 assumed the `Done; (…)` verdict was stdout-only and absent from
#     cyanrip's log file. **That was false at 0.9.3 and at master** —
#     `cyanrip_log()` writes the logfile before stdout, so the line was always in
#     the log; it was merely un-indented. The fork answered the question by
#     reading the source (their §4).
#   * On that false premise we asked for indentation as the signal, and defined
#     "indented ⇒ belongs to the open track". The fork duly indented the string
#     *in place* — still inside the pre-opener repeat loop. Indentation and
#     position now disagreed, and every verdict shifted one track: a converged
#     track inherited the next track's failure and vice versa, producing a false
#     "not confirmed reproducible" AND a false "verified" in the same log.
#
# So `_SECURE_DONE_*` above match at any indentation and always buffer for the
# NEXT track, because that is where cyanrip emits them from. This labelled row is
# the only in-block source, and it wins over a buffered value for the same track
# (it is applied after the block opens) because a row inside the block is the one
# form whose ownership is not in question.
_TRACK_SECURE_VERDICT = re.compile(r"^\s+Secure re-?read(?:s)?:\s+(?P<text>\S.*?)\s*$")

# --- 4. "Appended: N frames of silence" — ALREADY PRINTED by cyanrip 0.9.3 ---
#
# Not fork-only: this is in both committed reference logs (track 14 of each), and
# the parser's own enumerable check flagged it as the best line we still discarded.
# It names the track whose FINAL FRAMES ARE FABRICATED SILENCE rather than disc
# audio — a direct archival-fidelity statement, and the per-track consequence of
# overread being off (the disc's outermost samples were padded, not read).
_APPENDED_SILENCE = re.compile(
    r"^\s+Appended:\s+(?P<frames>\d{1,9})\s+frames? of silence"
)


def _parse_overread_mode(mode: str) -> bool | None:
    """Map cyanrip's "Overread mode:" text to EAC's Yes/No, or None if unrecognised.

    EAC's archival field is *"Overread into Lead-In and Lead-Out"* — i.e. did the
    drive actually read the disc's outermost samples? cyanrip states this directly:

      * ``read in lead-in/lead-out``              → it read them        → **True**
      * ``fill with silence in lead-in/lead-out`` → padded, didn't read → **False**

    Both phrasings are confirmed against real logs (see ``_OVERREAD_MODE``). Anything
    else returns ``None`` so the field renders "(unknown)" rather than a guess — a
    wrong "No" would misreport an archival fact just as badly as a wrong "Yes".
    """
    text = mode.strip().casefold()
    if "silence" in text:
        # Padded rather than read: cyanrip's conservative default (no `-O`).
        return False
    if "read in" in text:
        return True
    return None


def _float_or_none(raw: str) -> float | None:
    """``float(raw)`` or None — never raises.

    The float sibling of :func:`platterpus.safe_int.int_or_none`, kept local
    because it has exactly one caller family (the peak / speed / elapsed values
    below) and `safe_int` is the *integer* guard the whole codebase routes
    through. Same contract: unusable text becomes "unknown" and says so in the
    log, rather than raising out of a parser that promises it never will. Only
    ``ValueError`` is possible from the bounded regexes that feed it, but
    ``TypeError`` is caught too so the function is total for any caller.
    """
    try:
        return float(raw)
    except (TypeError, ValueError):
        log.warning(
            "cyanrip log: unusable number %r; recording as unknown", str(raw)[:32]
        )
        return None


def _sample_peak_fraction(value: str, unit: str) -> float | None:
    """A reported sample peak as a linear fraction of full scale, or None.

    ``TrackResult.peak_level`` is a linear fraction (0.0–1.0) because that is what
    ``eac_log_export._track_block`` renders as ``peak_level * 100:.1f %`` — EAC's
    own unit for the row.

    **The refusal is the point.** EAC's ``Peak level`` is a percentage of full
    scale, so it cannot exceed 100 %. A value above full scale therefore is not a
    sample peak — overwhelmingly likely cyanrip's *true* peak, which exceeds it on
    every track of the reference disc — and putting it in EAC's row would print a
    wrong number where today we print an honest "(not reported by the ripper)".
    So an over-scale value is dropped to None *and logged*, which keeps the
    labelled cell rather than inventing a plausible-looking one.

    A note for whoever lands the upstream patch: 0 dBFS is exactly 100 %, and
    docs/cyanrip-improvements-wanted.md §2.1 warns that cyanrip's currently-dead
    ``ebu_sample_peak`` field probably reads a zero-initialised ``0.0`` — which
    would render as a *plausible* 100.0 %. This function cannot tell that apart
    from a genuinely clipped track, so the filter edit and the print MUST land
    together upstream. Parsing cannot save us from a ripper that prints a zero.
    """
    number = _float_or_none(value)
    if number is None:
        return None
    if unit == "%":
        fraction = number / 100.0
    else:
        # dBFS. Checked BEFORE the exponentiation, which both keeps the refusal
        # exact (> 0 dBFS is > full scale) and avoids an OverflowError on an
        # absurd positive exponent.
        if number > 0.0:
            log.warning(
                "cyanrip log: sample peak %s dBFS is above full scale, so it is "
                "not a sample peak (EAC's Peak level cannot exceed 100%%); "
                "recording as unreported",
                value,
            )
            return None
        fraction = 10.0 ** (number / 20.0)
    if not 0.0 <= fraction <= 1.0:
        log.warning(
            "cyanrip log: sample peak %s %s is outside 0–100%% of full scale; "
            "recording as unreported",
            value,
            unit,
        )
        return None
    return fraction


# Phrases that decide a secure-re-read verdict, in the order they MUST be tested.
# Order is load-bearing: every negative phrasing contains a positive substring
# ("did NOT converge" contains "converge"; "no matches found" contains "matches"),
# so a positive-first check would read every failure as a success — the one
# direction this project must never get wrong (it would render an EAC-style
# Test/Copy CRC pair for a track whose reads disagreed).
_SECURE_NOT_ATTEMPTED: tuple[str, ...] = (
    "not attempted",
    "not requested",
    "not enabled",
    "not run",
    "disabled",
    "n/a",
)
_SECURE_DID_NOT_CONVERGE: tuple[str, ...] = (
    "no match",
    "not converge",
    "did not",
    "never agreed",
    "repeat limit",
    "gave up",
    "failed",
)
_SECURE_CONVERGED: tuple[str, ...] = (
    "converged",
    "out of",
    "matches",
    "agreed",
    "identical",
)


def _parse_secure_verdict(text: str) -> bool | None:
    """Map a secure-re-read verdict line to True / False / None.

    THREE states, not two, and the middle one is why this exists:

    * **converged** → ``True``. Two or more reads produced the same checksum, which
      is EAC's "Test CRC == Copy CRC" guarantee by a cheaper mechanism.
    * **did NOT converge** → ``False``. The re-read limit was reached with no two
      reads agreeing. cyanrip's own health line still says "No errors occurred"
      here, so without this the log cannot tell a non-converging track from a clean
      one (real-hardware finding, 2026-07-01).
    * **not attempted / unrecognised** → ``None``, i.e. no verdict. The caller
      leaves the field alone, so an unfamiliar future wording can never *erase* a
      verdict we already measured, and never invents one.

    Free text on purpose: the upstream wording is unread (§2.4), so the sense is
    matched rather than an exact string — the same approach ``_parse_overread_mode``
    takes for a line whose phrasing has already changed once.
    """
    lowered = text.strip().casefold()
    if not lowered:
        return None
    if any(phrase in lowered for phrase in _SECURE_NOT_ATTEMPTED):
        return None
    if any(phrase in lowered for phrase in _SECURE_DID_NOT_CONVERGE):
        return False
    if any(phrase in lowered for phrase in _SECURE_CONVERGED):
        return True
    log.debug("cyanrip log: unrecognised secure re-read verdict %r", text[:80])
    return None


# ---------------------------------------------------------------------------
# The recognised-line table
# ---------------------------------------------------------------------------
# WHY a table at all. Every bug this file has ever shipped was the same shape:
# *cyanrip prints a line and the parser silently ignores it* — the overread mode
# (twice), the gap section, the "Accurip 450" offset variant, the per-track rip
# count. An if/elif chain hides that failure mode, because "we don't handle this
# line" and "there is no such line" look identical in the source. So the
# disc-level rows — the ones that are a plain "Label: value", one line, no
# section state — live in ORDERED TABLES of (pattern → handler) below.
#
# What that buys, concretely:
#   * a reader can list every row we understand without reading the loop;
#   * a TEST can too — `tests/test_parsers_cyanrip_log.py` walks the committed
#     real logs and fails if a top-level line matches neither the tables nor the
#     explicit `_IGNORED_DISC_LINES` allow-list, so a row a future cyanrip adds
#     cannot slip past unnoticed the way the ones above did;
#   * the parser itself logs (at debug) any top-level line it did not claim, so a
#     user's log file carries the evidence when upstream changes its output.
#
# What deliberately stays as control flow (a table would OBSCURE it): the
# section-scoped blocks — the `Gaps:` two-liner, `Paranoia status counts:`,
# `Album Loudness Summary:`, the per-track block and its "File(s):" lookahead.
# Those aren't "match a line, set a field"; they change what SUBSEQUENT lines
# mean, and the flag that carries that state is the point of them.


@dataclass
class _Disc:
    """Everything the parse learns about the disc as a whole.

    One mutable accumulator instead of ~20 loop locals, so a table handler can
    write its field without the loop having to hand every variable around. It is
    NOT the return type — `parse_cyanrip_log` copies these into the frozen
    `RipLog`/`RippingInfo` at the end, which keeps the public contract unchanged.
    Every field starts at the same empty/None value the old locals did, because
    "cyanrip didn't say" must stay distinguishable from "cyanrip said zero".
    """

    log_creator: str = ""
    ripper_build: str = ""
    creation_date: str = ""
    drive: str = ""
    read_offset: int | None = None
    overread_lead_out: bool | None = None
    overread_mode: str = ""
    speed_changeable: bool | None = None
    album: str = ""
    album_artist: str = ""
    c2_pointers: bool | None = None
    paranoia_level: str = ""
    gap_detection: str = ""
    output_formats: str = ""
    disc_id: str = ""
    cddb_id: str = ""
    accuraterip_summary: str = ""
    partially_accurate_summary: str = ""
    disc_duration: str = ""
    health_status: str = ""
    log_checksum: str = ""
    # Track number → CRC of the file that actually shipped, from Platterpus's own
    # swap addendum. Applied over the finished track list at the very end.
    shipped_crcs: dict[int, str] = field(default_factory=dict)
    paranoia_counts: dict[str, int] = field(default_factory=dict)
    album_loudness: dict[str, str] = field(default_factory=dict)
    tracks: list[TrackResult] = field(default_factory=list)


@dataclass
class _TrackAcc:
    """The track block being read right now, before it becomes a `TrackResult`.

    A track's facts arrive across a dozen lines, so they have to be collected
    somewhere mutable and then frozen. This used to be a bare `dict`, which meant
    a typo in a key ("copy_crc2") was a silent no-op that no type check could see
    — on the very fields that carry the bit-perfection claim. A dataclass makes
    every field a checked name and lists them in one place.

    The field names match `TrackResult`'s so `flush()` is a plain copy; the two
    stay separate because `TrackResult` is frozen and shared with the whipper
    parser, and only completed tracks belong in it.
    """

    number: int
    status: str
    # cyanrip prints a track's secure re-read verdict on the line BEFORE the
    # track opens, so the loop buffers it and hands it in at construction.
    secure_rerip_converged: bool | None
    filename: str = ""
    pre_emphasis: bool | None = None
    copy_crc: str = ""
    accuraterip_v1: AccurateRipResult | None = None
    accuraterip_v2: AccurateRipResult | None = None
    accuraterip_offset: AccurateRipResult | None = None
    # The verbatim text of this track's "Accurip:" status row — the only thing in
    # the log that says whether a lookup happened. None = the ripper said nothing.
    accuraterip_lookup: str | None = None
    rip_count: int | None = None
    start_sector: int | None = None
    end_sector: int | None = None
    pregap_sectors: int | None = None
    # The RAW value off cyanrip's "Pregap LSN:" row — an ABSOLUTE disc position,
    # not a length. Kept separate from `pregap_sectors` (the derived length)
    # because conflating the two is precisely the bug this field exists to end:
    # see the derivation in `flush()`.
    pregap_start_lsn: int | None = None
    # See TrackResult for what each of these means; `unknown` is not `none`.
    pregap_state: str = ""
    pregap_unknown_reason: str = ""
    pregap_length_frames: int | None = None
    pregap_source: str = ""
    replaygain: dict[str, str] = field(default_factory=dict)
    # The three new per-track facts. All default to None — "the ripper did not say"
    # — which is what the deployed cyanrip 0.9.3 leaves them at for the first two.
    peak_level: float | None = None
    extraction_speed: float | None = None
    extraction_elapsed_seconds: float | None = None
    appended_silence_frames: int | None = None


# A handler takes the accumulator and the successful match, records the fact, and
# returns whether it CLAIMED the line. Returning False means "this row isn't mine
# after all" and the line keeps travelling down the chain exactly as it did when
# the chain was `if match and <guard>:` — the version banner uses that (a second
# banner must not overwrite the first, and must not be swallowed either).
_LineHandler = Callable[[_Disc, re.Match[str]], bool]


@dataclass(frozen=True)
class _LineRule:
    """One recognised disc-level log line: how to spot it, what to do with it.

    `name` exists so failures and debug output can say WHICH row was involved
    ("overread_mode"), rather than printing a regex at the maintainer.
    """

    name: str
    pattern: re.Pattern[str]
    handle: _LineHandler
    # True for rows that only mean something in the disc-level report. cyanrip
    # prints "Album:" both in the start report and inside each track's Metadata
    # block, and the per-track copy must not overwrite the disc's — the old chain
    # spelled this `if match and current is None`.
    disc_level_only: bool = False


def _take_version(disc: _Disc, match: re.Match[str]) -> bool:
    """First banner wins; a later one is not ours (see `_LineHandler`)."""
    if disc.log_creator:
        return False
    disc.log_creator = f"cyanrip {match.group('version')}"
    # Additive: `log_creator` is byte-identical to before, so both committed
    # reference logs and every assertion over them are untouched.
    disc.ripper_build = (match.group("build") or "").strip()
    return True


def _take_drive(disc: _Disc, match: re.Match[str]) -> bool:
    disc.drive = match.group("drive").strip()
    return True


def _take_offset(disc: _Disc, match: re.Match[str]) -> bool:
    """Signed read offset in samples — cyanrip prints the sign separately."""
    value = int_or_none(match.group("value"), field="cyanrip read offset") or 0
    disc.read_offset = -value if match.group("sign") == "-" else value
    return True


def _take_overread_mode(disc: _Disc, match: re.Match[str]) -> bool:
    """Both the EAC yes/no verdict and cyanrip's own wording (kept verbatim)."""
    disc.overread_lead_out = _parse_overread_mode(match.group("mode"))
    disc.overread_mode = match.group("mode").strip()
    return True


def _take_album(disc: _Disc, match: re.Match[str]) -> bool:
    # `.strip()`: a padded, value-less row backtracks into capturing a single
    # space, which would render the disc line as " / ".
    disc.album = match.group("value").strip()
    return True


def _take_album_artist(disc: _Disc, match: re.Match[str]) -> bool:
    disc.album_artist = match.group("value").strip()
    return True


def _take_c2(disc: _Disc, match: re.Match[str]) -> bool:
    """C2 error pointers — a DRIVE CAPABILITY line, never a claim about the rip.

    cyanrip's format string is "C2 errors:      %s by drive". So "unsupported"
    proves C2 was not used (the drive cannot), while "supported" says only that it
    was available — EAC's row asks whether C2 was *used*, which cyanrip never
    states. Claiming Yes from a capability line would be exactly the invented rip
    fact the export forbids, so an affirmative capability leaves the answer
    unknown rather than becoming a Yes. That distinction is the whole reason the
    row is honest, and `tests/test_eac_layout_parity.py` pins it.

    **FORK-ONLY addition (§2.5).** The upstream ask is one printf: say whether C2
    was *used*, not only whether the drive supports it — "supported by drive, not
    used". That wording answers EAC's actual question, so it maps to a truthful
    ``False``. The bare "supported by drive" mapping is deliberately UNCHANGED
    (still ``None``).

    Note there is no affirmative branch, on purpose. libcdio-paranoia never
    consumes C2 pointers, so a "used" line would contradict the engine, and
    "not used" contains the substring "used" — a positive check would have to be
    ordered after every negative one and would earn us nothing but a way to
    fabricate EAC's "Yes".
    """
    text = match.group("text").casefold()
    if "unsupported" in text or "not supported" in text:
        disc.c2_pointers = False
    elif "disabled" in text or "off" in text:
        disc.c2_pointers = False
    elif "not used" in text or "unused" in text or "never used" in text:
        # A statement about the RIP, not the drive: C2 was available and the
        # reader did not use it, which is exactly EAC's "No".
        disc.c2_pointers = False
    else:
        disc.c2_pointers = None
    return True


def _take_paranoia_level(disc: _Disc, match: re.Match[str]) -> bool:
    disc.paranoia_level = match.group("text").strip()
    return True


def _take_addendum_crc(disc: _Disc, match: re.Match[str]) -> bool:
    """A shipped-file CRC from Platterpus's swap addendum (supersedes the block)."""
    number = int_or_none(
        match.group("number"), field="cyanrip swap-addendum track number"
    )
    if number is not None:
        disc.shipped_crcs[number] = match.group("crc").upper()
    return True


def _take_outputs(disc: _Disc, match: re.Match[str]) -> bool:
    disc.output_formats = match.group("value").strip()
    return True


def _take_disc_id(disc: _Disc, match: re.Match[str]) -> bool:
    disc.disc_id = match.group("value")
    return True


def _take_cddb_id(disc: _Disc, match: re.Match[str]) -> bool:
    disc.cddb_id = match.group("value")
    return True


def _take_speed_cap(disc: _Disc, match: re.Match[str]) -> bool:
    """Whether the drive lets us change read speed (cyanrip ABORTS on `-S` if not)."""
    text = match.group("text").lower()
    # "unchangeable" contains "changeable", so test the negative first.
    if "unchangeable" in text:
        disc.speed_changeable = False
    elif "changeable" in text or (text and text[0].isdigit()):
        disc.speed_changeable = True
    return True


def _take_total_time(disc: _Disc, match: re.Match[str]) -> bool:
    disc.disc_duration = match.group("time")
    return True


def _take_log_checksum(disc: _Disc, match: re.Match[str]) -> bool:
    disc.log_checksum = match.group("sig")
    return True


def _take_accurate_total(disc: _Disc, match: re.Match[str]) -> bool:
    disc.accuraterip_summary = (
        f"{match.group('hit')}/{match.group('total')} tracks "
        "ripped accurately (AccurateRip)"
    )
    return True


def _take_partial_total(disc: _Disc, match: re.Match[str]) -> bool:
    disc.partially_accurate_summary = (
        f"{match.group('hit')}/{match.group('total')} tracks "
        "ripped partially accurately (offset-variant match)"
    )
    return True


def _take_rip_errors(disc: _Disc, match: re.Match[str]) -> bool:
    count = int_or_none(match.group("count"), field="cyanrip ripping-error count") or 0
    # Same phrasing as whipper's healthy verdict so downstream string checks
    # treat both backends alike.
    disc.health_status = (
        "No errors occurred" if count == 0 else f"{count} ripping errors"
    )
    return True


def _take_finished_at(disc: _Disc, match: re.Match[str]) -> bool:
    disc.creation_date = match.group("when").strip()
    return True


# --- the tables, and why there are four of them ----------------------------
# Each table is dispatched at the exact point in the loop where the old if-chain
# tested those same lines, and the split points are the section-state blocks.
# That ORDER IS LOAD-BEARING and the tables are not merged for tidiness: the
# section flags are cleared by "a line reached this block", so moving a row from
# after a block to before it changes whether that block's flag survives the line.
# (Concretely: with `Gaps:` armed, a `Total time:` row that the chain claims
# *before* the gaps block leaves the flag armed for the next line, and one
# claimed *after* it does not.) It costs four one-line dispatch calls to keep the
# behaviour provably identical, which is the right trade for the file that turns
# a ripper's text into a bit-perfection claim.
_RULES_BEFORE_GAPS: tuple[_LineRule, ...] = (
    _LineRule("version_banner", _HEADER, _take_version),
    _LineRule("drive", _DRIVE, _take_drive),
    _LineRule("read_offset", _OFFSET, _take_offset),
    _LineRule("overread_mode", _OVERREAD_MODE, _take_overread_mode),
    _LineRule("album", _ALBUM, _take_album, disc_level_only=True),
    _LineRule("album_artist", _ALBUM_ARTIST, _take_album_artist, disc_level_only=True),
    _LineRule("c2_errors", _C2, _take_c2),
    _LineRule("paranoia_level", _PARANOIA_LEVEL, _take_paranoia_level),
)

_RULES_AFTER_GAPS: tuple[_LineRule, ...] = (
    _LineRule("swap_addendum_crc", _ADDENDUM_CRC, _take_addendum_crc),
    _LineRule("outputs", _OUTPUTS, _take_outputs, disc_level_only=True),
    _LineRule("disc_id", _DISC_ID, _take_disc_id),
    _LineRule("cddb_id", _CDDB_ID, _take_cddb_id),
    _LineRule("speed_capability", _SPEED_CAP, _take_speed_cap),
    _LineRule("total_time", _TOTAL_TIME, _take_total_time),
)

_RULES_BEFORE_TRACKS: tuple[_LineRule, ...] = (
    _LineRule("log_signature", _LOG_CHECKSUM, _take_log_checksum),
)

_RULES_AFTER_TRACKS: tuple[_LineRule, ...] = (
    _LineRule("accuraterip_total", _ACCURATE_TOTAL, _take_accurate_total),
    _LineRule("accuraterip_partial_total", _PARTIAL_TOTAL, _take_partial_total),
    _LineRule("ripping_errors", _RIP_ERRORS, _take_rip_errors),
    _LineRule("finished_at", _FINISHED_AT, _take_finished_at),
)

# The complete set of disc-level rows we understand, in dispatch order. This is
# the enumerable surface the tests read; nothing else should be added to a table
# without appearing here automatically.
_ALL_LINE_RULES: tuple[_LineRule, ...] = (
    _RULES_BEFORE_GAPS + _RULES_AFTER_GAPS + _RULES_BEFORE_TRACKS + _RULES_AFTER_TRACKS
)

# The section headers the stateful control flow reacts to. They are NOT in the
# tables (matching one changes the parser's mode rather than setting a field),
# but they ARE part of "lines we recognise", so they are listed here for the same
# reason the tables exist: the enumeration must be complete or the test that
# reads it would flag them as unhandled.
_SECTION_LINE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("gaps_section", _GAPS_HEADER),
    ("paranoia_counts_section", _PARANOIA_HEADER),
    ("album_loudness_section", _ALBUM_LOUDNESS_HEADER),
    ("track_block_start", _TRACK_START),
    ("secure_rerip_converged", _SECURE_DONE_MATCH),
    ("secure_rerip_no_match", _SECURE_DONE_FAIL),
)

# The INDENTED rows the loop reads inside a section or a track block, listed for
# the same enumeration reason. These are not dispatched from here — the loop
# applies them in the order its section state requires — and the tests assert
# that no line pattern in this module is missing from one of these three groups,
# so the listing cannot silently drift away from the code.
_INDENTED_LINE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("gaps_value", _GAPS_VALUE),
    ("paranoia_count", _PARANOIA_LINE),
    ("loudness_integrated", _LOUDNESS_I),
    ("loudness_range", _LOUDNESS_LRA),
    ("loudness_true_peak", _LOUDNESS_PEAK),
    ("track_files_header", _FILES_HEADER),
    ("track_replaygain", _REPLAYGAIN),
    ("track_start_lsn", _START_LSN),
    ("track_end_lsn", _END_LSN),
    ("track_pregap_lsn", _PREGAP_LSN),
    ("track_pregap_length", _PREGAP_LENGTH),
    ("track_pregap_source", _PREGAP_SOURCE),
    ("track_preemphasis", _PREEMPHASIS),
    ("track_eac_crc", _EAC_CRC),
    ("track_accurip", _ACCURIP_TRACK),
    ("track_accurip_offset", _ACCURIP_OFFSET),
    # Already printed by cyanrip 0.9.3 and parsed since 2026-07-31 — it moved out
    # of the "skimmed" residue this listing exists to expose, so the test that
    # walks the real logs now requires it to be recognised.
    ("track_appended_silence", _APPENDED_SILENCE),
    # FORK-ONLY (see the pattern block). Listed so the enumeration stays complete;
    # they match nothing in the committed 0.9.3 logs, which is exactly the point.
    ("track_peak_kind_header", _PEAK_KIND_HEADER),
    ("track_sample_peak", _SAMPLE_PEAK),
    ("track_extraction_speed", _TRACK_SPEED),
    ("track_elapsed_clock", _TRACK_ELAPSED_CLOCK),
    ("track_elapsed_seconds", _TRACK_ELAPSED_SECONDS),
    ("track_secure_verdict", _TRACK_SECURE_VERDICT),
    ("track_accurip_status", _TRACK_ACCURIP_STATUS),
)

# Lines cyanrip prints at the top level that we KNOWINGLY do not parse. This is
# an allow-list, not a shrug: each entry is a decision with a reason, and the
# test that walks the real logs treats "matches nothing and isn't listed here" as
# a failure. So a row upstream adds shows up as a red test, and silencing it
# requires writing down why — which is exactly the step that never happened for
# the overread mode, the gap section, or "Accurip 450".
#
# CANDIDATES flagged 2026-07-31: several of these are archival facts we arguably
# SHOULD record (they would need new `RippingInfo` fields, so they are a separate
# change, not a silent one): `HDCD decoding:` (an enabled HDCD decode alters
# samples, so it bears directly on "is this a bit-perfect copy"), `Tracks to rip:`
# (anything but "all" means the album on disk is incomplete), `Frame retries:`
# (a rip-effort setting EAC reports as part of its read mode) and `Album Art:`
# (the north star includes cover art).
#
# NOTE for whoever graduates one of those: the sibling candidate flagged in the
# same pass, per-track `Appended:  N frames of silence`, has now BEEN graduated
# (2026-07-31) — but it never appeared in this list, because it is *indented*.
# Indented rows are not allow-listed here; they live in the "skimmed" residue that
# `test_indented_lines_report_what_the_parser_reads_and_what_it_skims` prints, and
# graduating one means adding it to `_INDENTED_LINE_PATTERNS` and to that test's
# `must_read` set. Two different enumerations, one habit: write the decision down.
_IGNORED_DISC_LINES: tuple[tuple[re.Pattern[str], str], ...] = (
    # The device node we ripped from. The GUI already knows which device it
    # asked for, and EAC has no equivalent field.
    (re.compile(r"^System device:\s"), "device node; GUI already knows it"),
    # The overread FRAME COUNT, which is derived from the read offset and is
    # printed identically whether or not the drive read the lead-in/lead-out.
    # `_OVERREAD_MODE` is the only line that answers EAC's question — see the
    # long comment on that pattern before ever wiring this one up.
    # Both labels, for the same reason `_OVERREAD_MODE` accepts both: cyanrip
    # switches to "Underread:" when the read offset is negative.
    (re.compile(r"^(?:Over|Under)read:\s"), "derived from offset; not a verdict"),
    # Rip-effort / feature rows: real facts, no field to put them in yet.
    (re.compile(r"^Frame retries:\s"), "candidate: rip-effort setting"),
    (re.compile(r"^HDCD decoding:\s"), "candidate: alters samples when enabled"),
    (re.compile(r"^Album Art:\s"), "candidate: cover-art presence"),
    (re.compile(r"^Disc tracks:\s"), "candidate: total tracks on the disc"),
    (re.compile(r"^Tracks to rip:\s"), "candidate: partial-rip marker"),
    # Whether the DISC was found in AccurateRip at all ("AccurateRip:    found").
    # Skipped because the INDENTED per-track `Accurip:` row carries the same fact
    # at finer granularity and is what the classifier reads (see
    # `_TRACK_ACCURIP_STATUS`). NOT skipped because "the per-track CRC rows only
    # print when the disc was found" — that was the old reason here and it is
    # false: cyanrip prints those rows in every state, including `disabled`, which
    # is how a disc nobody looked up came to render as "in DB, no match".
    #
    # Unverified, and it is the reason to keep this line in mind: whether cyanrip
    # prints per-track `Accurip:` rows at all for a disc that is NOT in the
    # database. If it does not, this disc-level row is the only signal and will
    # need parsing. No committed log covers it — it needs a CD-R or an unlisted
    # pressing on the rig.
    (re.compile(r"^AccurateRip:\s"), "the indented per-track Accurip: row is read"),
    # Pure structure: a section marker with no value of its own.
    (re.compile(r"^Tracks:\s*$"), "section marker, no payload"),
    (re.compile(r"^Summary:\s*$"), "section marker, no payload"),
)

# How many unclaimed top-level lines to keep as evidence for the debug log. A
# corrupt or enormous input must not turn diagnostics into unbounded memory use.
_UNCLAIMED_SAMPLE_LIMIT = 10


def _apply_line_rules(
    rules: tuple[_LineRule, ...],
    line: str,
    disc: _Disc,
    *,
    in_track: bool,
) -> bool:
    """Try each rule in order; return True if one claimed the line.

    Deliberately mirrors the old if-chain exactly, including the fall-through:
    a rule whose pattern matches but whose guard or handler declines keeps the
    line moving to the NEXT rule (and, when no rule takes it, to the rest of the
    loop), because that is what `if match and <guard>: … continue` did.
    """
    for rule in rules:
        if rule.disc_level_only and in_track:
            continue
        match = rule.pattern.match(line)
        if match is None:
            continue
        if rule.handle(disc, match):
            return True
    return False


def _is_ignored_disc_line(line: str) -> bool:
    """True for a top-level line we knowingly skip (`_IGNORED_DISC_LINES`)."""
    return any(pattern.match(line) for pattern, _reason in _IGNORED_DISC_LINES)


def looks_like_cyanrip_log(text: str) -> bool:
    """True if `text` is cyanrip output (vs whipper's YAML-ish log).

    The first non-blank line of a cyanrip log is its version banner;
    whipper logs start with "Log created by: whipper ...".
    """
    for line in text.splitlines():
        if line.strip():
            return bool(_HEADER.match(line))
    return False


def _detect_truncation(text: str, tracks: list[TrackResult]) -> tuple[bool, bool]:
    """Was this log cut off mid-write? Returns ``(truncated, last_incomplete)``.

    **Why this is not "did the rip finish".** A cancelled rip and a truncated
    log look identical from the parse alone — both give fewer tracks and no
    finish report — and conflating them is what let a *verified* track vanish
    in silence. On the rig (2026-08-01) cyanrip's logfile was killed at exactly
    4096 bytes, one unflushed stdio block, ending mid-token at
    ``REPLAYGAIN_TRACK_GA``. Track 3 had completed and matched AccurateRip at
    confidence 200. Every artifact Platterpus wrote said 2 tracks, and the
    verdict blamed the user's cancel for 12 tracks that "were never ripped" —
    when the true figure was 11 and the log simply stopped talking.

    Two signals, both specific to *the writer was interrupted*, neither of which
    a cleanly-stopped rip can trip:

    1. **The text does not end in a newline.** Every line cyanrip writes ends
       with one, so a final partial line means the process died mid-write. This
       is the strong signal and it is what the rig artifact shows.
    2. **The last track claims success but never got its filename.** ``File(s):``
       is the last row of a track block, so a track that says "ripped
       successfully" with no filename had its block cut. Scoped to *successful
       audio* tracks deliberately: a data track and an errored track both
       legitimately carry an empty filename, so keying on the empty string alone
       would false-positive on any disc with a data track.

    Deliberately does NOT use "no finish report" as a signal. That is absent
    from every cancelled rip, truncated or not, so it would flag the honest case
    as often as the broken one — a detector that fires on everything says
    nothing. Pure and never raises; the parse itself must not depend on it.
    """
    if not text:
        return False, False
    mid_write = not text.endswith("\n")
    last_incomplete = False
    if tracks:
        last = tracks[-1]
        last_incomplete = getattr(
            last, "status", ""
        ) == "ripped successfully" and not getattr(last, "filename", "")
    return (mid_write or last_incomplete), last_incomplete


def parse_cyanrip_log(text: str) -> RipLog:
    """Parse a cyanrip log into the backend-neutral RipLog.

    Missing pieces degrade to empty/None — including a log truncated by a
    crash mid-rip. Never raises on arbitrary input.

    Shape of the loop below: the plain "Label: value" rows are recognised by the
    ordered tables (`_RULES_BEFORE_GAPS` and friends), while the SECTION-scoped
    parsing stays as explicit control flow — those blocks change what the
    FOLLOWING lines mean, and a table would hide that. The four table dispatch
    points sit exactly where those rows sat in the original if-chain, which is
    deliberate: see the comment above `_RULES_BEFORE_GAPS`.
    """
    disc = _Disc()
    # Section / lookahead state. Every one of these means "the next line(s) are
    # inside this block", which is precisely why they can't become table rows.
    expect_gaps = False
    # Every indented line of the `Gaps:` block, in order.
    gap_lines: list[str] = []
    in_paranoia = False
    in_album_loudness = False
    expect_filename = False
    # cyanrip prints a track's secure re-read verdict ("Done; (…)") on the line
    # just BEFORE that track's "Track N ripped…" opener, so we buffer it here and
    # attach it when the track block opens. None = no verdict seen (no -Z).
    pending_converged: bool | None = None
    # Which peak the NEXT indented "Peak:  N dBFS" line reports: "true", "sample",
    # or "" for no header seen. cyanrip prints its peaks as a sub-header plus a
    # value line, and a FORK adding the sample peak is likely to do the same — so
    # this one flag is what stops the existing TRUE peak (which legitimately
    # exceeds full scale) from landing in EAC's sample-peak row. See
    # `_PEAK_KIND_HEADER` and `_sample_peak_fraction`.
    pending_peak_kind = ""
    # Set when a track gave us its peak as a direct percentage, so the dBFS
    # sub-header cannot overwrite a more precise value with a rounded one.
    peak_from_percentage = False
    # Evidence for the debug line at the end: top-level rows nothing claimed.
    # A bounded sample plus a full count, so a corrupt or enormous input cannot
    # turn diagnostics into unbounded memory use.
    unclaimed_sample: list[str] = []
    unclaimed_total = 0

    # The track block currently being read; flushed into `disc.tracks` when the
    # next block (or the end of input) is reached.
    current: _TrackAcc | None = None

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        # Derive the pre-gap LENGTH from the two absolute positions cyanrip prints,
        # exactly the way cyanrip itself derives the duration it displays:
        #
        #     cyanrip_frames_to_duration(t->start_lsn_sig - t->pregap_lsn, ...)
        #     cyanrip_log(ctx, 0, "    Pregap LSN:  %i (duration: %s)\n",
        #                 t->pregap_lsn, pregap_duration);
        #
        # The number on the row is `pregap_lsn` — where INDEX 00 *begins* — while
        # `Start LSN:` is `start_lsn_sig`, the very variable cyanrip subtracts
        # from. Storing the row's number as a length was an 89x over-claim on a
        # real disc: track 2 of the reference pressing has INDEX 00 at LSN 14327
        # and starts at 14487, a 160-sector (2.13 s) gap, which was archived as
        # 3 m 11 s (audit, 2026-07-31).
        #
        # Subtraction rather than the `(duration: …)` suffix on purpose: that
        # suffix's fractional field is CD frames in some cyanrip formatters and
        # hundredths in others, and we have no reference log that pins which —
        # so parsing it would trade a known-correct computation for a guess.
        #
        # Both operands are required. A log that prints a pregap LSN without a
        # Start LSN leaves the length None ("not reported"), never 0 ("measured
        # none") — absent must stay absent.
        #
        # A ripper that STATES the length outright wins over our subtraction.
        # `Pregap length: N frames` (fork-only) is the only field that can
        # express track 1, whose gap is the 150-frame lead-in PLUS any declared
        # gap: the fork's reference disc reads `Pregap LSN: 0` / `Start LSN: 150`
        # / `Pregap length: 300`, and its `Gaps:` block confirms a 150-frame TOC
        # pre-gap — 150 + 150. Subtracting gets 150 there, and is simply wrong.
        # Deriving remains the path for stock cyanrip, which states nothing.
        if current.pregap_length_frames is not None:
            current.pregap_sectors = current.pregap_length_frames
        elif current.pregap_start_lsn is not None:
            if current.start_sector is None:
                current.pregap_sectors = None
            else:
                length = current.start_sector - current.pregap_start_lsn
                # A non-positive result cannot be a gap. It happens for real on
                # track 1, where cyanrip reports `Pregap LSN: 0` against
                # `Start LSN: 0`: the Red Book lead-in physically occupies LSN
                # -150..-1, so LSN 0 cannot express it and the ripper has told us
                # nothing machine-readable about the length. We record "not
                # reported" rather than inventing the 150-sector constant — the
                # log is a record of what the ripper measured (audit, 2026-07-31).
                current.pregap_sectors = length if length > 0 else None
        disc.tracks.append(
            TrackResult(
                number=current.number,
                pregap_state=current.pregap_state,
                pregap_unknown_reason=current.pregap_unknown_reason,
                pregap_length_frames=current.pregap_length_frames,
                pregap_source=current.pregap_source,
                filename=current.filename,
                pre_emphasis=current.pre_emphasis,
                copy_crc=current.copy_crc,
                status=current.status,
                accuraterip_v1=current.accuraterip_v1,
                accuraterip_v2=current.accuraterip_v2,
                accuraterip_offset=current.accuraterip_offset,
                accuraterip_lookup=current.accuraterip_lookup,
                rip_count=current.rip_count,
                secure_rerip_converged=current.secure_rerip_converged,
                start_sector=current.start_sector,
                end_sector=current.end_sector,
                pregap_sectors=current.pregap_sectors,
                pregap_start_lsn=current.pregap_start_lsn,
                replaygain=dict(current.replaygain),
                # None for every track of a cyanrip 0.9.3 log except
                # `appended_silence_frames` on a track that ends in padding.
                peak_level=current.peak_level,
                extraction_speed=current.extraction_speed,
                extraction_elapsed_seconds=current.extraction_elapsed_seconds,
                appended_silence_frames=current.appended_silence_frames,
            )
        )
        current = None

    for line in text.splitlines():
        # Are we inside a track block? Read once per line, for the rows that only
        # count in the disc-level report. Nothing between here and the last table
        # dispatch can change it without also skipping to the next line, so a
        # single snapshot is honest.
        in_track = current is not None

        # Disc-level rows the old if-chain tested BEFORE the "Gaps:" block.
        if _apply_line_rules(_RULES_BEFORE_GAPS, line, disc, in_track=in_track):
            continue

        # cyanrip's "Gaps:" section is a header plus one or MORE indented lines.
        # Stock 0.9.3 prints exactly one ("None signalled"); the maintainer's fork
        # enumerates a line per track ("0 frame pregap in track 1, unmerged"), and
        # a one-line lookahead silently kept only the first of those — discarding
        # the gap report for every track but one (audit, 2026-07-31). Collected
        # until the first blank or non-indented line, the same shape as the
        # "Paranoia status counts:" block.
        if expect_gaps:
            if current is None and _GAPS_VALUE.match(line):
                match = _GAPS_VALUE.match(line)
                assert match is not None  # just tested
                gap_lines.append(match.group("value"))
                continue
            # Anything not an indented value ends the block; fall through so the
            # line is still offered to every rule below it.
            expect_gaps = False
            # Joined for the single-string field every consumer already reads. A
            # one-line 0.9.3 block therefore still yields exactly "None signalled".
            disc.gap_detection = "; ".join(gap_lines)

        if _GAPS_HEADER.match(line) and current is None:
            expect_gaps = True
            gap_lines = []
            continue

        # Disc-level rows the old if-chain tested AFTER the "Gaps:" block.
        if _apply_line_rules(_RULES_AFTER_GAPS, line, disc, in_track=in_track):
            continue

        # The Paranoia status counts block: a header then indented "KEY: N"
        # lines. Stay in the block only while lines keep matching, so a later
        # finish line (e.g. "Ripping errors:") cleanly ends it.
        if _PARANOIA_HEADER.match(line):
            in_paranoia = True
            continue
        if in_paranoia:
            match = _PARANOIA_LINE.match(line)
            if match:
                disc.paranoia_counts[match.group("key")] = (
                    int_or_none(
                        match.group("count"),
                        field=f"cyanrip paranoia count {match.group('key')}",
                    )
                    or 0
                )
                continue
            in_paranoia = False  # block ended; fall through to other handlers

        # The album-loudness summary comes after the last track. Flush it so its
        # I:/LRA:/Peak: lines are captured album-wide, not misattributed to the
        # final track (whose own summary looks identical).
        if _ALBUM_LOUDNESS_HEADER.match(line):
            flush()
            in_album_loudness = True
            # Defensive: a track whose "Sample peak:" header had no value line must
            # not let the ALBUM's true peak be recorded as a sample peak.
            pending_peak_kind = ""
            continue
        if in_album_loudness:
            # The block has sub-headers ("Integrated loudness:", "Loudness
            # range:", "True peak:") and blank lines between the value lines, so
            # we DON'T end the block on a non-match — we just capture the I:/LRA:/
            # Peak: values wherever they appear. Nothing after this block carries
            # those lines, so leaving the flag on is safe; the finish handlers
            # below (Tracks ripped…, Paranoia, Log FUN512) still run normally.
            m_i = _LOUDNESS_I.match(line)
            if m_i:
                disc.album_loudness["integrated_lufs"] = m_i.group("v")
                continue
            m_lra = _LOUDNESS_LRA.match(line)
            if m_lra:
                disc.album_loudness["lra_lu"] = m_lra.group("v")
                continue
            m_pk = _LOUDNESS_PEAK.match(line)
            if m_pk:
                # cyanrip 0.9.3 prints only the TRUE peak here, so the key is
                # unchanged unless a fork's "Sample peak:" header armed the flag —
                # in which case recording it as `true_peak_dbfs` would quietly
                # replace one loudness quantity with a different one.
                key = (
                    "sample_peak_dbfs"
                    if pending_peak_kind == "sample"
                    else "true_peak_dbfs"
                )
                disc.album_loudness[key] = m_pk.group("v")
                pending_peak_kind = ""
                continue

        # Which peak the next "Peak:" value line reports (FORK-ONLY for "Sample";
        # "True" is cyanrip 0.9.3's own sub-header and its only job here is to
        # DISARM sample capture). Handled once, outside both the album block and
        # the per-track block, because the state is the same state for both.
        peak_kind = _PEAK_KIND_HEADER.match(line)
        if peak_kind:
            pending_peak_kind = peak_kind.group("kind").casefold()
            continue

        # cyanrip's own log signature — the last line of a complete log.
        if _apply_line_rules(_RULES_BEFORE_TRACKS, line, disc, in_track=in_track):
            continue

        # Secure re-read verdict for the NEXT track — buffer it (see above).
        # Checked at ANY indentation, because cyanrip emits these from the repeat
        # loop that runs before the track opener regardless of how the string is
        # formatted. The fork indents them; stock does not; both mean the same
        # thing about the same track.
        match = _SECURE_DONE_MATCH.match(line)
        if match:
            # "N out of M matches" is convergence only when N >= 1. A zero
            # numerator is a total failure to reproduce, and reading it as
            # "verified" is the worst direction for this field to be wrong in.
            agreed = int_or_none(match.group("agreed"), field="cyanrip -Z agreements")
            pending_converged = agreed is not None and agreed >= 1
            continue
        if _SECURE_DONE_FAIL.match(line):
            pending_converged = False
            continue

        match = _TRACK_START.match(line)
        if match:
            flush()
            what = match.group("what")
            if what == "is data:":
                status = "data track (skipped)"
            elif what.endswith("successfully!"):
                status = "ripped successfully"
            else:
                status = "ripped with errors"
            current = _TrackAcc(
                number=int_or_none(match.group("number"), field="cyanrip track number")
                or 0,
                status=status,
                # The verdict buffered from this track's "Done; (…)" line above;
                # consumed so the next track starts fresh (None if -Z was off).
                secure_rerip_converged=pending_converged,
            )
            pending_converged = None
            expect_filename = False
            # A new track's peaks are its own: a dangling header from the previous
            # block must not decide what this track's first "Peak:" line means, and
            # a percentage on the PREVIOUS track must not suppress this track's
            # dBFS reading.
            pending_peak_kind = ""
            peak_from_percentage = False
            continue

        if current is not None:
            # The filename follows the "File(s):" header on the next indented
            # line — capture it so the per-track `filename` isn't null.
            if expect_filename:
                if line.strip():
                    current.filename = line.strip()
                    expect_filename = False
                continue
            if _FILES_HEADER.match(line):
                expect_filename = True
                continue

            match = _REPLAYGAIN.match(line)
            if match:
                current.replaygain[match.group("key")] = match.group("val")
                continue

            match = _START_LSN.match(line)
            if match:
                current.start_sector = int_or_none(
                    match.group("value"), field="cyanrip Start LSN"
                )
                continue

            match = _END_LSN.match(line)
            if match:
                current.end_sector = int_or_none(
                    match.group("value"), field="cyanrip End LSN"
                )
                continue

            match = _PREGAP_LSN.match(line)
            if match:
                raw = match.group("value")
                if raw == "none":
                    # "none" is a real answer (no pre-gap), recorded as a measured
                    # 0 length rather than None so "measured: none" stays
                    # distinguishable from "not reported".
                    current.pregap_sectors = 0
                    current.pregap_state = "none"
                elif raw == "unknown":
                    # The ripper TRIED and could not tell. Deliberately leaves
                    # `pregap_sectors` as None rather than 0: a 0 here would be
                    # read downstream as "measured, no gap", which is the false
                    # claim this branch exists to prevent.
                    current.pregap_state = "unknown"
                    current.pregap_unknown_reason = match.group("reason") or ""
                else:
                    current.pregap_state = "known"
                    # An ABSOLUTE LSN, never a length. It is stored raw and the
                    # length is derived in `flush()`, once `Start LSN:` (printed
                    # two rows later) is also known.
                    current.pregap_start_lsn = int_or_none(
                        raw, field="cyanrip Pregap LSN"
                    )
                continue

            match = _PREGAP_LENGTH.match(line)
            if match:
                current.pregap_length_frames = int_or_none(
                    match.group("frames"), field="cyanrip Pregap length"
                )
                continue

            match = _PREGAP_SOURCE.match(line)
            if match:
                current.pregap_source = match.group("source")
                continue

            # "Appended:    2 frames of silence" — cyanrip 0.9.3 DOES print this,
            # in the same Properties block as the LSNs above, on a track whose
            # final frames were padded instead of read. Parsed since 2026-07-31;
            # surfaced by eac_log_export's status report, because it is a statement
            # about the archived audio's fidelity, not a rip *setting*.
            match = _APPENDED_SILENCE.match(line)
            if match:
                current.appended_silence_frames = int_or_none(
                    match.group("frames"), field="cyanrip appended silence frames"
                )
                continue

            # --- the FORK-ONLY per-track rows ------------------------------------
            # Not one of these patterns matches a line in a cyanrip 0.9.3 log
            # (proved against the committed real logs), so every `if` below is dead
            # code today and every field stays None. That is the
            # forward-compatibility contract, not an oversight.

            # The SAMPLE peak, inline form — either label:
            #   "Sample peak:  -0.5 dBFS"   (the shape §2.1 proposed)
            #   "Peak level:   99.7%"       (what the fork actually prints)
            #
            # The fork's own `Peak level:` row is PREFERRED over the dBFS
            # sub-header below, and a flag records that so the sub-header cannot
            # overwrite it. Three reasons, all about accuracy rather than taste:
            # it is already EAC's unit and precision so nothing is re-derived; it
            # is pre-rounding, whereas converting a 1-decimal dBFS print fabricates
            # "exactly 100.0 %" for anything peaking 99.43–100 %; and the fork gates
            # it behind `t->computed_crcs`, so unlike the FFmpeg-printed sub-header
            # it cannot appear when no audio was decoded (their `-I` bug).
            match = _SAMPLE_PEAK.match(line)
            if match:
                current.peak_level = _sample_peak_fraction(
                    match.group("value"), match.group("unit")
                )
                if match.group("unit") == "%":
                    peak_from_percentage = True
                continue

            # The SAMPLE peak, header form: a "Peak:" value line, but ONLY when a
            # "Sample peak:" header armed it. Without that guard this would capture
            # cyanrip's existing TRUE peak — a different quantity that exceeds full
            # scale on all fourteen reference tracks — and print it as EAC's
            # percentage-of-full-scale `Peak level`.
            match = _LOUDNESS_PEAK.match(line)
            if match and pending_peak_kind == "sample":
                if peak_from_percentage:
                    # A direct percentage already gave us the value at EAC's own
                    # precision. Log rather than silently prefer one, because two
                    # peak statements per track that disagree is a contract problem
                    # worth seeing (validate-dependency-output rule).
                    derived = _sample_peak_fraction(match.group("v"), "dBFS")
                    if (
                        derived is not None
                        and current.peak_level is not None
                        and (abs(derived - current.peak_level) > 0.005)
                    ):
                        log.warning(
                            "track %s reports two different sample peaks: %.4f from "
                            "the percentage row and %.4f from the dBFS sub-header — "
                            "keeping the percentage",
                            current.number,
                            current.peak_level,
                            derived,
                        )
                else:
                    current.peak_level = _sample_peak_fraction(match.group("v"), "dBFS")
                pending_peak_kind = ""
                continue

            # The per-track read speed, as a multiple of 1x — EAC's own unit.
            match = _TRACK_SPEED.match(line)
            if match:
                current.extraction_speed = _float_or_none(match.group("value"))
                continue

            # The per-track elapsed wall-clock, in either shape cyanrip writes
            # durations. Recorded as seconds; deliberately NOT converted into a
            # speed multiple (see eac_log_export._track_block for why deriving one
            # would be a guess about what the interval includes).
            match = _TRACK_ELAPSED_CLOCK.match(line)
            if match:
                hours = int_or_none(match.group("h") or "0", field="cyanrip elapsed h")
                minutes = int_or_none(match.group("m"), field="cyanrip elapsed m")
                seconds = _float_or_none(match.group("s"))
                if hours is not None and minutes is not None and seconds is not None:
                    current.extraction_elapsed_seconds = (
                        hours * 3600 + minutes * 60 + seconds
                    )
                continue
            match = _TRACK_ELAPSED_SECONDS.match(line)
            if match:
                current.extraction_elapsed_seconds = _float_or_none(match.group("s"))
                continue

            # The -Z convergence verdict as a durable, LABELLED per-track row —
            # the only in-block form. A `Done; (…)` line is never read here, at any
            # indentation: cyanrip emits it from the pre-opener repeat loop, so it
            # is buffered for the NEXT track further up. An in-block arm for it
            # used to exist and was reachable ONLY as the misattribution, because
            # no cyanrip has ever written a `Done;` inside a track block.
            match = _TRACK_SECURE_VERDICT.match(line)
            if match:
                verdict = _parse_secure_verdict(match.group("text"))
                # Only a recognised verdict is recorded. "not attempted" and an
                # unfamiliar wording both mean "no verdict here", and neither may
                # ERASE one already measured — including the GUI's own auto-fix
                # verdict, which overrides this field afterwards
                # (`ui/main_window_rip._merge_shipped_track`) and must stay the
                # last word.
                if verdict is not None:
                    current.secure_rerip_converged = verdict
                continue

            match = _PREEMPHASIS.match(line)
            if match:
                current.pre_emphasis = not match.group("text").startswith("none")
                continue

            match = _EAC_CRC.match(line)
            if match:
                current.copy_crc = match.group("crc").upper()
                rips = match.group("rips")
                if rips is not None:
                    current.rip_count = int_or_none(rips, field="cyanrip rip count")
                continue

            match = _ACCURIP_TRACK.match(line)
            if match:
                result_text = match.group("result") or ""
                conf_match = _ACCURIP_CONFIDENCE.search(result_text)
                version = (
                    int_or_none(match.group("version"), field="cyanrip Accurip version")
                    or 0
                )
                ar = AccurateRipResult(
                    version=version,
                    result=result_text,
                    confidence=int_or_none(
                        conf_match.group("value"),
                        field="cyanrip Accurip confidence",
                    )
                    if conf_match
                    else None,
                    local_crc=match.group("crc").upper(),
                )
                # The pattern only accepts v1/v2, so these two arms are the whole
                # space — spelled out rather than computed so the field names stay
                # greppable and type-checked.
                if version == 2:
                    current.accuraterip_v2 = ar
                else:
                    current.accuraterip_v1 = ar
                continue

            match = _TRACK_ACCURIP_STATUS.match(line)
            if match:
                current.accuraterip_lookup = match.group("status")
                continue

            match = _ACCURIP_OFFSET.match(line)
            if match:
                result_text = match.group("result") or ""
                conf_match = _ACCURIP_CONFIDENCE.search(result_text)
                # version=450 is a sentinel for "the +450-frame offset variant"
                # — it isn't a real AccurateRip protocol version, just how
                # cyanrip labels this pressing-offset match.
                current.accuraterip_offset = AccurateRipResult(
                    version=450,
                    result=result_text,
                    confidence=int_or_none(
                        conf_match.group("value"),
                        field="cyanrip Accurip 450 confidence",
                    )
                    if conf_match
                    else None,
                    local_crc=match.group("crc").upper(),
                )
                continue

        # Disc-level rows the old if-chain tested AFTER the per-track block:
        # cyanrip's finish report.
        if _apply_line_rules(_RULES_AFTER_TRACKS, line, disc, in_track=in_track):
            continue

        # Nothing claimed this line. Indented lines are per-track detail we
        # deliberately skim (metadata, timings, sub-headers), but a line starting
        # in COLUMN 0 is one of cyanrip's structural rows — so an unlisted one
        # means upstream changed its output and we are quietly dropping a fact.
        # That is the exact failure mode every bug in this file had, so it goes
        # to the log where a bug report will carry it. Debug level, not warning:
        # it is diagnostics, and a stray line is not a rip failure.
        if line and not line[0].isspace() and not _is_ignored_disc_line(line):
            unclaimed_total += 1
            if len(unclaimed_sample) < _UNCLAIMED_SAMPLE_LIMIT:
                unclaimed_sample.append(line[:120])

    if expect_gaps and gap_lines:
        # EOF inside the block — a truncated log must not lose what it did say.
        disc.gap_detection = "; ".join(gap_lines)
    flush()
    truncated, last_incomplete = _detect_truncation(text, disc.tracks)
    if unclaimed_total:
        log.debug(
            "cyanrip log: %d unrecognised top-level line(s); first %d: %r",
            unclaimed_total,
            len(unclaimed_sample),
            unclaimed_sample,
        )
    # Apply the swap addendum last, over the finished track list: it is the only
    # statement in the file about which bytes actually shipped.
    tracks = disc.tracks
    if disc.shipped_crcs:
        tracks = [
            replace(tr, copy_crc=disc.shipped_crcs.get(tr.number, tr.copy_crc))
            for tr in tracks
        ]
    return RipLog(
        log_creator=disc.log_creator,
        ripper_build=disc.ripper_build,
        creation_date=disc.creation_date,
        ripping_info=RippingInfo(
            drive=disc.drive,
            extraction_engine=disc.log_creator,
            read_offset_correction=disc.read_offset,
            overread_lead_out=disc.overread_lead_out,
            speed_changeable=disc.speed_changeable,
            album=disc.album,
            album_artist=disc.album_artist,
            c2_pointers=disc.c2_pointers,
            paranoia_level=disc.paranoia_level,
            overread_mode=disc.overread_mode,
            gap_detection=disc.gap_detection,
            output_formats=disc.output_formats,
        ),
        tracks=tuple(tracks),
        accuraterip_summary=disc.accuraterip_summary,
        health_status=disc.health_status,
        partially_accurate_summary=disc.partially_accurate_summary,
        disc_duration=disc.disc_duration,
        paranoia_counts=disc.paranoia_counts,
        album_loudness=disc.album_loudness,
        log_checksum=disc.log_checksum,
        disc_id=disc.disc_id,
        cddb_id=disc.cddb_id,
        log_truncated=truncated,
        last_track_incomplete=last_incomplete,
    )
