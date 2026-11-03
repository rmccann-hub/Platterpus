# SPDX-License-Identifier: GPL-3.0-only
"""Where a rip's counted ripping errors were, and whether the reads it KEEPS had any.

**Why this exists** (run C of the four 0.7.112 Full runs, 2026-10-22; TASKS R59,
R70). cyanrip's ``Ripping errors:`` tally counts the album pass. On *Roots Music*
disc 3 it counted 2, both paranoia skips in track 16 (its ``-j`` record), and the
verified-read chase then replaced track 16 with a single read AccurateRip
verified (v1 confidence 11, v2 24), one that printed no skip and no read error.
Every surface kept describing the album pass: the completion audit warned
"completed with 2 ripping errors", the report's ``health_status`` read "2 ripping
errors", and the EAC-layout log printed "2 ripping errors" under "All tracks
accurately ripped". Each was the ripper's number, and none was about the files.

**One placement, three callers.** :func:`place_counted_errors` decides where the
counted errors were and whether the reads the album keeps had any. The audit asks
it of a written report (:func:`errors_in_replaced_reads`); the report builder,
the window's status line and the EAC-layout log ask it of the parsed log and the
worker's record (:func:`errors_in_replaced_reads_of`). Both adapters only gather
the same three inputs, so the four surfaces cannot place one error two ways.

**Clean only when every input closes** (:attr:`ErrorsInReplacedReads.reads_kept_are_clean`):

* the per-track counts (``disc.error_positions``: ``read_errors`` + ``skips``
  over every read of the album pass) are complete, agree with their counters,
  and sum to exactly the tally, so every counted error has a track;
* every error is in a first read the album replaced, and a first read counts as
  replaced only when ``retried_tracks`` keeps another read on AccurateRip's word
  AND that track's row says AccurateRip verified it (the pair, not the label);
* each replacing read printed its own paranoia counters, with no ``READERR`` and
  no ``SKIP``. cyanrip prints only the counters that are not zero, so an absent
  key is zero; a read that printed no counters at all is not known to be clean,
  and then neither is the album.

Anything short of that, and the callers keep the ripper's own sentence: an error
we cannot place stays in the warning, which keeps a clean word off a read nobody
checked.

Pure, Qt-free, and never raises.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from platterpus.parsers.rip_log import track_accuraterip_verified
from platterpus.verdict import REREAD_KEPT_FOR_ACCURATERIP
from platterpus.verified_read_chase import (
    KEPT_SECURING_PASS,
    KEPT_VERIFIED_REREAD,
    kept_read,
)

#: The parser's health sentence for a non-zero ``Ripping errors:`` count
#: (``parsers/cyanrip_log.py``). Anchored and bounded: the count is 1-9 digits.
#: Singular for one from 2026-11-03 (TASKS R113); a report written before reads
#: "1 ripping errors", so both are read.
_COUNTED_ERRORS: Final[re.Pattern[str]] = re.compile(
    r"^(?P<count>\d{1,9}) ripping errors?$"
)
#: ``retried_tracks[].kept_read`` values naming a read that replaced the first.
_REPLACING_READS: Final[frozenset[str]] = frozenset(
    {KEPT_SECURING_PASS, KEPT_VERIFIED_REREAD}
)
#: The paranoia counters that are errors: a read that failed, and a read
#: paranoia gave up verifying. The same two ``disc.error_positions`` sums.
_ERROR_COUNTERS: Final[tuple[str, ...]] = ("READERR", "SKIP")


@dataclass(frozen=True)
class ErrorsInReplacedReads:
    """Where the album pass's counted ripping errors were.

    ``counted`` is the ``Ripping errors:`` total; ``in_replaced`` how many were in
    first reads the album replaced with a read AccurateRip verified, ``tracks``
    those tracks, and ``kept_tracks`` the tracks whose kept read holds the rest.
    ``kept_read_errors`` is ``READERR`` + ``SKIP`` in the replacing reads' own
    counters, or ``None`` when one of them printed no counters.
    """

    counted: int
    in_replaced: int
    tracks: tuple[int, ...]
    kept_tracks: tuple[int, ...] = ()
    kept_read_errors: int | None = None

    @property
    def in_kept_reads(self) -> int:
        """The counted errors in reads the album keeps."""
        return self.counted - self.in_replaced

    @property
    def reads_kept_are_clean(self) -> bool:
        """Every counted error was in a replaced read, and the replacements had none."""
        return (
            self.in_replaced > 0
            and self.in_kept_reads == 0
            and self.kept_read_errors == 0
        )


def _int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _read_errors(counts: object) -> int | None:
    """``READERR`` + ``SKIP`` in one read's printed counters, or None if it printed none."""
    if not isinstance(counts, Mapping) or not counts:
        return None
    total = 0
    for key in _ERROR_COUNTERS:
        number = _int(counts.get(key, 0))
        if number is None or number < 0:
            return None
        total += number
    return total


def place_counted_errors(
    tally: object, error_positions: object, replacing: Mapping[int, object]
) -> ErrorsInReplacedReads | None:
    """Place the tally's errors on tracks, or None when the population is not closed.

    ``tally`` is the parser's health sentence for the album pass ("2 ripping
    errors"); ``error_positions`` is the report's ``disc.error_positions`` block;
    ``replacing`` maps each track whose first read a read AccurateRip verified
    replaced to that read's own paranoia counters. Never raises.
    """
    try:
        match = _COUNTED_ERRORS.match(str(tally or ""))
        if match is None or not isinstance(error_positions, Mapping):
            return None
        if error_positions.get("state") != "read":
            return None
        rows = error_positions.get("tracks")
        if not isinstance(rows, Sequence) or isinstance(rows, str):
            return None
        total = in_replaced = 0
        tracks: list[int] = []
        kept: list[int] = []
        for row in rows:
            if not isinstance(row, Mapping) or row.get("state") != "read":
                continue
            if row.get("complete") is not True:
                return None
            if row.get("count_agrees_with_counters") is not True:
                return None
            errors, skips = _int(row.get("read_errors")), _int(row.get("skips"))
            if errors is None or skips is None:
                return None
            total += errors + skips
            number = row.get("number")
            if not errors + skips or not isinstance(number, int):
                continue
            if number in replacing:
                in_replaced += errors + skips
                tracks.append(number)
            else:
                kept.append(number)
        if total != int(match.group("count")):
            return None
        found = [_read_errors(counts) for counts in replacing.values()]
        kept_read_errors = None if None in found else sum(n or 0 for n in found)
        return ErrorsInReplacedReads(
            total, in_replaced, tuple(tracks), tuple(kept), kept_read_errors
        )
    except (AttributeError, TypeError, ValueError):
        return None


def _replaced_on_accuraterip(entry: object) -> int | None:
    """The track a retried-track entry replaced on AccurateRip's word, or None."""
    if not isinstance(entry, Mapping):
        return None
    if entry.get("replaced_because") != REREAD_KEPT_FOR_ACCURATERIP:
        return None
    if kept_read(entry) not in _REPLACING_READS:  # type: ignore[arg-type]  # a Mapping read with .get, as kept_read does
        return None
    return _int(entry.get("track"))


def errors_in_replaced_reads(
    report: Mapping[str, object],
) -> ErrorsInReplacedReads | None:
    """:func:`place_counted_errors` over a written report. Never raises.

    The tally is ``ripper_health_status`` (schema 42), the ripper's own sentence;
    a report older than that carried it in ``health_status``, which from schema
    42 describes the reads kept and so is never read for the tally when the
    newer field is present.
    """
    try:
        tally = (
            report.get("ripper_health_status")
            if "ripper_health_status" in report
            else report.get("health_status")
        )
        disc = report.get("disc")
        block = disc.get("error_positions") if isinstance(disc, Mapping) else None
        rows = report.get("tracks")
        verified: dict[int, object] = {}
        for row in rows if isinstance(rows, Sequence) else ():
            if isinstance(row, Mapping) and row.get("accuraterip_verified") is True:
                number = _int(row.get("number"))
                if number is not None:
                    verified[number] = row.get("paranoia_counts")
        speed = report.get("read_speed")
        retried = speed.get("retried_tracks") if isinstance(speed, Mapping) else None
        replacing: dict[int, object] = {}
        for entry in retried if isinstance(retried, Sequence) else ():
            number = _replaced_on_accuraterip(entry)
            if number is not None and number in verified:
                replacing[number] = verified[number]
        return place_counted_errors(tally, block, replacing)
    except (AttributeError, TypeError, ValueError):
        return None


def errors_in_replaced_reads_of(
    rip_log: object, error_positions: object, retried_tracks: object
) -> ErrorsInReplacedReads | None:
    """:func:`place_counted_errors` over a parsed log and the worker's record.

    ``rip_log`` must be the log AFTER the auto-fix merge, so each replaced
    track's AccurateRip result and paranoia counters are the shipped read's own
    (TASKS R61). ``error_positions`` is ``disc.error_positions`` as the report
    records it, and ``retried_tracks`` the worker's per-track auto-fix record.
    Never raises.
    """
    try:
        by_number: dict[int, object] = {}
        for track in getattr(rip_log, "tracks", ()) or ():
            number = _int(getattr(track, "number", None))
            if number is not None and track_accuraterip_verified(track):
                by_number[number] = getattr(track, "paranoia_counts", None)
        replacing: dict[int, object] = {}
        entries = retried_tracks if isinstance(retried_tracks, Sequence) else ()
        for entry in entries:
            number = _replaced_on_accuraterip(entry)
            if number is not None and number in by_number:
                replacing[number] = by_number[number]
        tally = getattr(rip_log, "health_status", "")
        return place_counted_errors(tally, error_positions, replacing)
    except (AttributeError, TypeError, ValueError):
        return None


def _listed(numbers: Sequence[int]) -> str:
    return ", ".join(str(n) for n in numbers)


def kept_reads_health(placed: ErrorsInReplacedReads) -> str:
    """The health sentence for an album whose counted errors were all replaced.

    Says the reads kept had none, then what the replaced read had, so the
    ripper's number is never hidden: the report's ``health_status`` and the
    window's status line.
    """
    return (
        f"No errors occurred in the reads kept; the ripper's {placed.counted} "
        f"ripping error(s) were all in the first read of track(s) "
        f"{_listed(placed.tracks)}, replaced by a read AccurateRip verified"
    )


def applies_to(rip_log: object, placed: ErrorsInReplacedReads | None) -> bool:
    """Every error the ripper counted in THIS log was in a read the album replaced.

    The placement read the parser's sentence; the parser's number must agree with
    it, so a sentence and a count that disagree are never cleaned.
    """
    count = _int(getattr(rip_log, "ripping_errors", None))
    return (
        placed is not None and placed.reads_kept_are_clean and count == placed.counted
    )


def count_line(
    rip_log: object, placed: ErrorsInReplacedReads | None, contradicted: str = ""
) -> str:
    """The EAC-layout log's line of ours under its health sentence, or ``""``.

    In the shape agreed in round 36 (our lap 3 S11) for a count AccurateRip
    contradicts: ``Ripper's own count  : Ripping errors: 2 — all in the first
    read of track(s) 16, replaced by a read AccurateRip verified``, with
    ``; not counted: track(s) 3, which AccurateRip contradicts`` when
    ``contradicted`` lists any. ``""`` unless :func:`applies_to`.
    """
    if placed is None or not applies_to(rip_log, placed):
        return ""
    line = (
        f"Ripper's own count  : Ripping errors: {placed.counted} — all in the "
        f"first read of track(s) {_listed(placed.tracks)}, replaced by a read "
        "AccurateRip verified"
    )
    if contradicted:
        line += f"; not counted: track(s) {contradicted}, which AccurateRip contradicts"
    return line
