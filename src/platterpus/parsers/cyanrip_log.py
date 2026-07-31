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

log = logging.getLogger(__name__)

# First meaningful line of any cyanrip log/output: "cyanrip 0.9.3.1 (tag)".
_HEADER = re.compile(r"^cyanrip\s+(?P<version>\S+)")
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
_SECURE_DONE_MATCH = re.compile(r"^Done;\s+\(\d+\s+out of\s+\d+\s+matches\b")
_SECURE_DONE_FAIL = re.compile(r"^Done;\s+\(no matches found\b")
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
_PREGAP_LSN = re.compile(r"^\s+Pregap LSN:\s+(?P<value>\d+|none)\b")


def _int_or_none(raw: str) -> int | None:
    """``int(raw)`` or None — never raises.

    CPython 3.11+ refuses to convert a string of more than 4300 digits, so a
    corrupt log with a long digit run would otherwise raise ValueError straight
    out of the parser, which must never happen (parsers return a best-effort
    dataclass on ANY input). Non-numeric text can't reach here through the
    regexes, but the guard is cheap and the rule is absolute.
    """
    try:
        return int(raw)
    except ValueError:
        log.warning("cyanrip log: unusable integer %r; recording as unknown", raw[:32])
        return None


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
_LOUDNESS_PEAK = re.compile(r"^\s+Peak:\s+(?P<v>-?\d+(?:\.\d+)?)\s+dBFS")
# cyanrip's own log signature, the last line: "Log FUN512: <base64>".
_LOG_CHECKSUM = re.compile(r"^Log FUN512:\s+(?P<sig>\S+)")


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

    The field names match `TrackResult`'s so `_flush` is a plain copy; the two
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
    rip_count: int | None = None
    start_sector: int | None = None
    end_sector: int | None = None
    pregap_sectors: int | None = None
    replaygain: dict[str, str] = field(default_factory=dict)


# A handler takes the accumulator and the successful match, records the fact, and
# returns whether it CLAIMED the line. Returning False means "this row isn't mine
# after all" and the line keeps travelling down the chain exactly as it did when
# the chain was `if match and <guard>:` — the version banner uses that (a second
# banner must not overwrite the first, and must not be swallowed either).
_LineHandler = Callable[[_Disc, "re.Match[str]"], bool]


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
    return True


def _take_drive(disc: _Disc, match: re.Match[str]) -> bool:
    disc.drive = match.group("drive").strip()
    return True


def _take_offset(disc: _Disc, match: re.Match[str]) -> bool:
    """Signed read offset in samples — cyanrip prints the sign separately."""
    value = _int_or_none(match.group("value")) or 0
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
    unknown rather than becoming a Yes.
    """
    text = match.group("text").casefold()
    if "unsupported" in text or "not supported" in text:
        disc.c2_pointers = False
    elif "disabled" in text or "off" in text:
        disc.c2_pointers = False
    else:
        disc.c2_pointers = None
    return True


def _take_paranoia_level(disc: _Disc, match: re.Match[str]) -> bool:
    disc.paranoia_level = match.group("text").strip()
    return True


def _take_addendum_crc(disc: _Disc, match: re.Match[str]) -> bool:
    """A shipped-file CRC from Platterpus's swap addendum (supersedes the block)."""
    number = _int_or_none(match.group("number"))
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
    count = _int_or_none(match.group("count")) or 0
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
    ("track_preemphasis", _PREEMPHASIS),
    ("track_eac_crc", _EAC_CRC),
    ("track_accurip", _ACCURIP_TRACK),
    ("track_accurip_offset", _ACCURIP_OFFSET),
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
    # Whether the DISC was found in AccurateRip at all. The per-track
    # "Accurip v1/v2:" lines carry the verdict that actually matters, and the
    # finish report's "Tracks ripped accurately: N/M" summarises it.
    (re.compile(r"^AccurateRip:\s"), "per-track Accurip lines carry the verdict"),
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
    in_paranoia = False
    in_album_loudness = False
    expect_filename = False
    # cyanrip prints a track's secure re-read verdict ("Done; (…)") on the line
    # just BEFORE that track's "Track N ripped…" opener, so we buffer it here and
    # attach it when the track block opens. None = no verdict seen (no -Z).
    pending_converged: bool | None = None
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
        disc.tracks.append(
            TrackResult(
                number=current.number,
                filename=current.filename,
                pre_emphasis=current.pre_emphasis,
                copy_crc=current.copy_crc,
                status=current.status,
                accuraterip_v1=current.accuraterip_v1,
                accuraterip_v2=current.accuraterip_v2,
                accuraterip_offset=current.accuraterip_offset,
                rip_count=current.rip_count,
                secure_rerip_converged=current.secure_rerip_converged,
                start_sector=current.start_sector,
                end_sector=current.end_sector,
                pregap_sectors=current.pregap_sectors,
                replaygain=dict(current.replaygain),
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

        # cyanrip's "Gaps:" section is a header plus ONE indented value line, so
        # it needs a one-line lookahead rather than a table row.
        if expect_gaps:
            expect_gaps = False
            match = _GAPS_VALUE.match(line)
            if match and current is None:
                disc.gap_detection = match.group("value")
                continue

        if _GAPS_HEADER.match(line) and current is None:
            expect_gaps = True
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
                    _int_or_none(match.group("count")) or 0
                )
                continue
            in_paranoia = False  # block ended; fall through to other handlers

        # The album-loudness summary comes after the last track. Flush it so its
        # I:/LRA:/Peak: lines are captured album-wide, not misattributed to the
        # final track (whose own summary looks identical).
        if _ALBUM_LOUDNESS_HEADER.match(line):
            flush()
            in_album_loudness = True
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
                disc.album_loudness["true_peak_dbfs"] = m_pk.group("v")
                continue

        # cyanrip's own log signature — the last line of a complete log.
        if _apply_line_rules(_RULES_BEFORE_TRACKS, line, disc, in_track=in_track):
            continue

        # Secure re-read verdict for the NEXT track — buffer it (see above).
        if _SECURE_DONE_MATCH.match(line):
            pending_converged = True
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
                number=_int_or_none(match.group("number")) or 0,
                status=status,
                # The verdict buffered from this track's "Done; (…)" line above;
                # consumed so the next track starts fresh (None if -Z was off).
                secure_rerip_converged=pending_converged,
            )
            pending_converged = None
            expect_filename = False
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
                current.start_sector = _int_or_none(match.group("value"))
                continue

            match = _END_LSN.match(line)
            if match:
                current.end_sector = _int_or_none(match.group("value"))
                continue

            match = _PREGAP_LSN.match(line)
            if match:
                raw = match.group("value")
                # "none" is a real answer (no pre-gap), recorded as 0 rather than
                # None so "measured: none" is distinguishable from "not reported".
                current.pregap_sectors = 0 if raw == "none" else _int_or_none(raw)
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
                    current.rip_count = _int_or_none(rips)
                continue

            match = _ACCURIP_TRACK.match(line)
            if match:
                result_text = match.group("result") or ""
                conf_match = _ACCURIP_CONFIDENCE.search(result_text)
                version = _int_or_none(match.group("version")) or 0
                ar = AccurateRipResult(
                    version=version,
                    result=result_text,
                    confidence=_int_or_none(conf_match.group("value"))
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
                    confidence=_int_or_none(conf_match.group("value"))
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

    flush()
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
    )
