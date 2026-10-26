# SPDX-License-Identifier: GPL-3.0-only
"""Where cdparanoia reported a hard read error or a skip, per track (TASKS R44).

**Why this exists.** EAC's log says *where* a track was doubtful (its
``Suspicious position`` lines); the cyanrip builds before ``.25`` printed only
how many errors and skips each track had. From ``.25`` (round 35, release 36,
``cyanrip-diagnostics/10``) the fork's ``-j`` record carries, per track, every
position paranoia's status callback reported, and the paranoia counters summed
over every read of the track. Until this module nothing of ours read them, so a
rip with read errors said how many and never where.

**What the record says, per ``rip.track_state[]`` row** (read in the fork's own
source, not from a description of it):

* ``error_positions``: a list of ``{"lsn": <int>, "kind": "read_error" |
  "skip"}`` (``cyanrip@5f1d036:src/diagnostics.c:302-307``). ``lsn`` is a
  logical sector number on the disc, an absolute position, not one counted from
  the track's start: paranoia's callback passes a position in 16-bit words and
  the fork divides it by ``CD_FRAMEWORDS``, as cd-paranoia itself does
  (``cyanrip@5f1d036:src/cyanrip_main.c:635-646``). A ``read_error`` names the
  first sector of the read that failed, and a ``skip`` the end of what paranoia
  had verified, or 0 when it had verified nothing
  (``cyanrip@5f1d036:src/diagnostics.c:458-463``). Each is the position
  paranoia passed, not a sector the fork located. A ``-Z`` re-read that
  disagreed has no position, so it is never here.
* ``error_positions_dropped``: how many the fork did not keep. It keeps the
  first 500 and a ring of the last 500, and counts the middle
  (``cyanrip@5f1d036:src/diagnostics.c:269-293``, ``CRIP_ERROR_POS_HALF`` at
  ``src/cyanrip_main.h:229``), the amendment our round 35 lap 8 S8 asked for.
* ``paranoia_all_reads``: the sixteen counters (``READ``, ``VERIFY``, ...,
  ``READERR``, ``SKIP``, ...) summed over EVERY read, ``-Z`` re-reads included
  (``cyanrip@5f1d036:src/diagnostics.c:312-329`` for the key table,
  ``:469-473`` for the object, ``:474-486`` for the list).
* All three are ``null`` for a track whose read never ran, a different claim from
  a read that counted nothing (``cyanrip@5f1d036:src/diagnostics.c:464-467``).

So an unamended list is as long as ``READERR`` plus ``SKIP`` (the fork's comment,
``:456-458``). :func:`parse_reads` checks that: a list whose length, with both
drop counts, disagrees with the counters is said, not reconciled.

**What an empty list does not mean.** The fork measured it on round 35's Full run
(their lap 17 S8): ``error_positions`` was empty on every track, *even on reads
AccurateRip shows were wrong*. Paranoia reporting nothing is not the audio being
verified; AccurateRip and CTDB are what verify it. The report block says so.

**Tri-state throughout.** A key absent from the row (every build before ``.25``)
is ``not_present``; ``null`` is ``track_not_read``; a value of the wrong type is
``not_determined``. Never a negative for something we could not read.

**Bounded, and every drop counted.** The fork already bounds the list at 1,000;
we bound it again at the same size, because a record is external input, and keep
the head and the tail as the fork does. An entry we cannot read (not an object,
no integer ``lsn``, an ``lsn`` outside a CD's address range) is skipped and
counted, never silently lost: CLAUDE.md's diagnostic-completeness rule.

**Read once, with the record's other per-track fields.** This module does not
open the record: :func:`platterpus.isrc_provenance.parse_isrcs` is the one
reader of ``rip.track_state`` and hands each row here, so the file is read,
size-bounded and parsed in one place. Pure, Qt-free, and never raises.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from platterpus import inbound_text
from platterpus.report_types import (
    ErrorPositionEntry,
    ErrorPositionsBlock,
    TrackErrorPositionsBlock,
)
from platterpus.ripper_ending import DESCRIBES, STATE_NOT_READ

if TYPE_CHECKING:  # the reader imports this module, so only its type is needed
    from platterpus.isrc_provenance import IsrcReading, TrackIsrc

#: The record's keys, spelled once.
POSITIONS_KEY: Final[str] = "error_positions"
DROPPED_KEY: Final[str] = "error_positions_dropped"
COUNTERS_KEY: Final[str] = "paranoia_all_reads"

#: The two kinds the fork writes (``cyanrip@5f1d036:src/diagnostics.c:306``).
KIND_READ_ERROR: Final[str] = "read_error"
KIND_SKIP: Final[str] = "skip"

#: The two counters an unamended list's length equals the sum of.
_READERR: Final[str] = "READERR"
_SKIP: Final[str] = "SKIP"

#: How many positions we keep from each end of a list. The fork keeps 500 of each
#: (``CRIP_ERROR_POS_HALF``); the same number here means a record from a build
#: that keeps its promise is never cut by us, and one that does not is.
KEEP_HEAD: Final[int] = 500
KEEP_TAIL: Final[int] = 500

#: A CD's address range in logical sectors: MSF 00:00:00 is LSN -150, and the
#: Red Book's last address, 99:59:74, is 449,849. A position outside it is not a
#: sector of any CD, so the entry is counted as unreadable rather than reported.
LSN_MIN: Final[int] = -150
LSN_MAX: Final[int] = 99 * 60 * 75 + 59 * 75 + 74 - 150

#: A counter name is upper case and short (the fork's longest is 13). Longer or
#: other text is not a counter, and at most this many are read from one object.
_COUNTER_NAME: Final[re.Pattern[str]] = re.compile(r"[A-Z_]{1,32}")
MAX_COUNTERS: Final[int] = 32

#: An unrecognised kind is kept as the record says it, screened and cut to this.
MAX_KIND_CHARS: Final[int] = 32

#: One track's state for each of the two fields.
READ: Final[str] = "read"
TRACK_NOT_READ: Final[str] = "track_not_read"
NOT_PRESENT: Final[str] = "not_present"
NOT_DETERMINED: Final[str] = "not_determined"

#: The issue codes :func:`findings` raises.
ISSUE_REPORTED: Final[str] = "error_positions_reported"
ISSUE_COUNT_DISAGREES: Final[str] = "error_positions_count_disagrees"

#: Said in every block, because an empty list reads as a clean track otherwise.
NOTE: Final[str] = (
    "positions where cdparanoia reported a hard read error or a skip, as disc "
    "sectors (LSN); an empty list means it reported none, not that the audio "
    "was verified: AccurateRip and CTDB say that"
)

#: How many LSNs a finding's sentence names before it says "and N more".
_SENTENCE_LSNS: Final[int] = 5


@dataclass(frozen=True)
class ErrorPosition:
    """One position paranoia reported: a disc sector and what happened there."""

    lsn: int
    #: ``read_error`` or ``skip``; anything else is kept as the record says it.
    kind: str


@dataclass(frozen=True)
class TrackReads:
    """One track's error positions and all-reads counters, as the record states them."""

    #: :data:`READ`, :data:`TRACK_NOT_READ`, :data:`NOT_PRESENT` or
    #: :data:`NOT_DETERMINED`, for ``error_positions``.
    state: str = NOT_PRESENT
    positions: tuple[ErrorPosition, ...] = ()
    #: ``error_positions_dropped`` as the record states it: the fork's own count
    #: of positions it did not keep. ``None`` when absent, null or mistyped.
    dropped_by_ripper: int | None = None
    #: Entries WE did not keep: past our head-and-tail bound, or unreadable.
    not_kept: int = 0
    #: The same four states, for ``paranoia_all_reads``.
    counters_state: str = NOT_PRESENT
    #: The counters, in the record's order, as ``(name, count)``; empty unless read.
    counters: tuple[tuple[str, int], ...] = ()
    #: Counter entries skipped: a name or a value that was not a counter.
    counters_not_read: int = 0

    def count(self, kind: str) -> int:
        """How many kept positions are of ``kind``."""
        return sum(1 for position in self.positions if position.kind == kind)

    def complete(self) -> bool | None:
        """Whether the list holds every position paranoia reported.

        ``None`` when that cannot be said: no list, or no readable drop count.
        """
        if self.state != READ or self.dropped_by_ripper is None:
            return None
        return self.dropped_by_ripper == 0 and self.not_kept == 0

    def agrees_with_counters(self) -> bool | None:
        """Whether every position reported, kept or dropped, equals READERR + SKIP.

        The fork's own invariant (``cyanrip@5f1d036:src/diagnostics.c:456-458``).
        ``None`` without a list, a drop count, or both counters to compare.
        """
        counters = dict(self.counters)
        if (
            self.state != READ
            or self.dropped_by_ripper is None
            or self.counters_state != READ
            or _READERR not in counters
            or _SKIP not in counters
        ):
            return None
        reported = len(self.positions) + self.not_kept + self.dropped_by_ripper
        return reported == counters[_READERR] + counters[_SKIP]


def parse_reads(row: Mapping[str, object]) -> TrackReads:
    """The three ``/10`` fields of one ``track_state`` row. Pure; never raises."""
    state, positions, not_kept = _positions(row)
    counters_state, counters, counters_not_read = _counters(row)
    return TrackReads(
        state=state,
        positions=positions,
        dropped_by_ripper=_count(row.get(DROPPED_KEY)),
        not_kept=not_kept,
        counters_state=counters_state,
        counters=counters,
        counters_not_read=counters_not_read,
    )


def report_block(reading: IsrcReading | None) -> ErrorPositionsBlock:
    """The report's ``disc.error_positions`` block (schema v39). Pure.

    ``reading`` is the record as :mod:`platterpus.isrc_provenance` read it, the
    worker's ``isrc_reading``; ``None`` is a report written with no reading.
    """
    tracks: Sequence[TrackIsrc]
    if reading is None:
        state, detail, tracks, rows_not_read = STATE_NOT_READ, "", (), 0
    else:
        state, detail = reading.state, reading.detail
        tracks, rows_not_read = reading.tracks, reading.dropped
    rows: list[TrackErrorPositionsBlock] = []
    for track in tracks:
        reads = track.reads
        # Null, never `[]` or 0, for a list we do not have: an empty list is the
        # claim "paranoia reported nothing", which a track never read cannot make.
        listed = reads.state == READ
        rows.append(
            {
                "number": track.number,
                "audio_ripped": track.ripped,
                "state": reads.state,
                "positions": (
                    [
                        ErrorPositionEntry(lsn=position.lsn, kind=position.kind)
                        for position in reads.positions
                    ]
                    if listed
                    else None
                ),
                "read_errors": reads.count(KIND_READ_ERROR) if listed else None,
                "skips": reads.count(KIND_SKIP) if listed else None,
                # Beside the list, always, so an elided list never reads as whole.
                "error_positions_dropped": reads.dropped_by_ripper,
                "error_positions_not_kept": reads.not_kept,
                "complete": reads.complete(),
                "count_agrees_with_counters": reads.agrees_with_counters(),
                "paranoia_all_reads_state": reads.counters_state,
                "paranoia_all_reads": (
                    dict(reads.counters) if reads.counters_state == READ else None
                ),
                "paranoia_all_reads_not_read": reads.counters_not_read,
                # v40 (`/11`): when the read the files carry began, as the
                # record states it (`record_track_v11`), beside the log's copy.
                "kept_read_began": track.record.kept_read_began,
                "kept_read_began_state": track.record.kept_read_began_state,
            }
        )
    return {
        "describes": DESCRIBES,
        "state": state,
        "detail": detail or None,
        "note": NOTE,
        "tracks": rows,
        "rows_not_read": rows_not_read,
    }


def findings(block: object) -> list[tuple[str, str]]:
    """The report's ``(issue code, sentence)`` pairs for a block. Pure; never raises.

    A track with any position, kept or dropped, is named with its counts, and its
    first and last sectors. A list that disagrees with its own counters is named
    too, because it is the record contradicting itself.
    """
    if not isinstance(block, Mapping):
        return []
    rows = block.get("tracks")
    found: list[tuple[str, str]] = []
    for row in rows if isinstance(rows, list) else ():
        if not isinstance(row, Mapping):
            continue
        number = row.get("number")
        positions = row.get("positions")
        kept = positions if isinstance(positions, list) else []
        dropped = _count(row.get("error_positions_dropped")) or 0
        not_kept = _count(row.get("error_positions_not_kept")) or 0
        if kept or dropped or not_kept:
            found.append(
                (ISSUE_REPORTED, _reported_sentence(row, kept, dropped, not_kept))
            )
        if row.get("count_agrees_with_counters") is False:
            counters = row.get("paranoia_all_reads")
            said = counters if isinstance(counters, Mapping) else {}
            found.append(
                (
                    ISSUE_COUNT_DISAGREES,
                    f"track {number}: cyanrip's record lists {len(kept) + dropped + not_kept} "
                    f"error position(s), counting those not listed, but its counters "
                    f"say {said.get(_READERR)} read error(s) and {said.get(_SKIP)} "
                    "skip(s); the two should be equal",
                )
            )
    return found


def _reported_sentence(
    row: Mapping[str, object], kept: Sequence[object], dropped: int, not_kept: int
) -> str:
    """One track's ``error_positions_reported`` sentence: counts, then where."""
    lsns = [
        entry["lsn"]
        for entry in kept
        if isinstance(entry, Mapping) and isinstance(entry.get("lsn"), int)
    ]
    where = ", ".join(str(lsn) for lsn in lsns[:_SENTENCE_LSNS])
    if len(lsns) > _SENTENCE_LSNS:
        where += f" and {len(lsns) - _SENTENCE_LSNS} more"
    sentence = (
        f"track {row.get('number')}: cdparanoia reported {row.get('read_errors')} "
        f"hard read error(s) and {row.get('skips')} skip(s)"
    )
    if where:
        sentence += f" at disc sector(s) {where}"
    if dropped:
        sentence += f"; cyanrip did not list {dropped} more"
    if not_kept:
        sentence += f"; Platterpus did not keep {not_kept} more"
    return sentence + " (AccurateRip and CTDB say whether the audio is right)"


def _positions(row: Mapping[str, object]) -> tuple[str, tuple[ErrorPosition, ...], int]:
    """``error_positions`` as ``(state, kept positions, entries not kept)``."""
    if POSITIONS_KEY not in row:
        return NOT_PRESENT, (), 0
    value = row.get(POSITIONS_KEY)
    if value is None:
        return TRACK_NOT_READ, (), 0
    if not isinstance(value, list):
        return NOT_DETERMINED, (), 0
    # Head and tail, as the fork keeps them: a run of errors at a track's end is
    # what a damaged disc's last track looks like, and a head-only cap loses it.
    if len(value) > KEEP_HEAD + KEEP_TAIL:
        candidates = value[:KEEP_HEAD] + value[-KEEP_TAIL:]
        not_kept = len(value) - len(candidates)
    else:
        candidates, not_kept = value, 0
    kept: list[ErrorPosition] = []
    for entry in candidates:
        position = _position(entry)
        if position is None:
            not_kept += 1
        else:
            kept.append(position)
    return READ, tuple(kept), not_kept


def _position(entry: object) -> ErrorPosition | None:
    """One ``{"lsn", "kind"}`` entry, or ``None`` when it is not one."""
    if not isinstance(entry, Mapping):
        return None
    lsn = entry.get("lsn")
    kind = entry.get("kind")
    if not isinstance(lsn, int) or isinstance(lsn, bool):
        return None
    if not LSN_MIN <= lsn <= LSN_MAX or not isinstance(kind, str):
        return None
    if kind not in (KIND_READ_ERROR, KIND_SKIP):
        kind = inbound_text.screen_line(kind).text[:MAX_KIND_CHARS]
    return ErrorPosition(lsn, kind)


def _counters(
    row: Mapping[str, object],
) -> tuple[str, tuple[tuple[str, int], ...], int]:
    """``paranoia_all_reads`` as ``(state, counters, entries not read)``."""
    if COUNTERS_KEY not in row:
        return NOT_PRESENT, (), 0
    value = row.get(COUNTERS_KEY)
    if value is None:
        return TRACK_NOT_READ, (), 0
    if not isinstance(value, Mapping):
        return NOT_DETERMINED, (), 0
    counters: list[tuple[str, int]] = []
    skipped = 0
    for name, count in value.items():
        number = _count(count)
        if (
            len(counters) >= MAX_COUNTERS
            or not isinstance(name, str)
            or _COUNTER_NAME.fullmatch(name) is None
            or number is None
        ):
            skipped += 1
            continue
        counters.append((name, number))
    return READ, tuple(counters), skipped


def _count(value: object) -> int | None:
    """A non-negative integer from the record, or ``None`` when it is not one."""
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None
