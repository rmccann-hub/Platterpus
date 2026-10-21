# SPDX-License-Identifier: GPL-3.0-only
"""Compare what :mod:`platterpus.ctdb.sweep` measured with what CTDB holds.

Two questions, answered the way CUETools answers them (LGPL,
``CUETools.CTDB/CUEToolsDB.cs``, ``GenerateLog`` and ``GetConfidence``), so a
per-track line of ours and a line of EAC's CTDB plugin mean the same thing:

1. **Which entries does the whole disc match, and at what offset?** An entry
   whose whole-disc CRC equals ours at some offset is an error-free match
   (CUETools' ``!entry.hasErrors``), and its confidence counts for EVERY track,
   without looking at its per-track CRCs.
2. **Per track, which other entries agree?** An entry with a per-track CRC list
   (``trackcrcs``) agrees with a track when that track's CRC equals ours at the
   ENTRY'S OFFSET, or at any offset within AccurateRip's ±2939 frames
   (:data:`AR_OFFSET_RANGE`): CUETools tries ``TrackCRC(i, -entry.offset)``,
   then loops ``_arOffsetRange``.

A track's confidence is the SUM of the agreeing entries' confidences, out of all
the submissions for the disc: EAC's ``(1426/1441) Accurately ripped``.

**Where an entry's offset comes from.** CUETools reads it from the entry's parity
syndrome (``CDRepairEncode.FindOffset``), which needs Reed-Solomon arithmetic
over the whole disc that is not built here (TASKS R43 says why). We read it from
the tracks instead (:func:`entry_offsets`): the offset, anywhere in ±5879, at
which the most of that entry's per-track CRCs equal ours, provided at least two
do. Two independent 32-bit CRCs agreeing at the same offset by chance is a
one-in-10^19 event, so a consensus is a measurement, not a guess; an entry with
no such consensus keeps offset 0, as CUETools' does when ``FindOffset`` fails.

What CUETools does that this still does not: for an entry it can REPAIR, it
counts the tracks the repair leaves untouched as agreeing, and it names the
differing samples ("Differs in 16 samples @04:04:68,..."). That needs the parity
data itself (TASKS R43). So a track that differs here is reported as differing,
with no count of samples and no position.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from platterpus.adapters.ctdb_client import CtdbEntry

#: AccurateRip's ±(5·588 − 1) frames: the ``_arOffsetRange`` that
#: ``CUEToolsDB.GenerateLog`` and ``GetConfidence`` loop over when a track's CRC
#: differs at the entry's own offset.
AR_OFFSET_RANGE: int = 5 * 588 - 1  # = 2939

#: How many of an entry's tracks must agree at one offset to place the entry.
CONSENSUS_TRACKS: int = 2


class TrackVerdict(enum.Enum):
    """What CTDB says about one track. Tri-state: unknown is never a pass or a fail."""

    MATCH = "match"  # at least one entry agrees with this track
    DIFFERS = "differs"  # entries carry this track's CRC and none agrees
    NOT_DETERMINED = "not_determined"  # nothing to compare with, or no CRC of ours


@dataclass(frozen=True)
class CtdbTrackResult:
    """One track's CTDB result.

    ``confidence`` is the submissions behind the entries that agree;
    ``disagreeing_confidence`` those behind entries that carry a different CRC
    for this track, and ``strongest_disagreeing`` the largest single such entry.
    ``our_crc`` is this track's CTDB CRC at offset 0. ``offset`` is where the
    strongest agreeing entry agreed (0 is aligned; ``None`` without a match).
    ``reason`` says why a track is not determined, and is empty otherwise.
    """

    track: int
    verdict: TrackVerdict
    confidence: int = 0
    disagreeing_confidence: int = 0
    strongest_disagreeing: int = 0
    our_crc: int | None = None
    offset: int | None = None
    reason: str = ""

    @property
    def outvoted(self) -> bool:
        """A MATCH whose agreeing submissions are fewer than one disagreeing entry's.

        The per-track form of :attr:`CtdbVerifyResult.outvoted` (TASKS R34):
        agreeing with a minority corroborates nothing, because a shared misread
        explains it as well as a correct read does.
        """
        return (
            self.verdict is TrackVerdict.MATCH
            and self.confidence < self.strongest_disagreeing
        )


#: Why a track is not determined, in the words every surface shows.
NO_TRACK_CRCS_REASON: str = "CTDB holds no per-track CRCs for this disc"
NO_LOCAL_CRC_REASON: str = (
    "no aligned CRC of ours for this track (the decoded audio did not reach it)"
)


def _closest_to_zero(offsets: Sequence[int]) -> int:
    """The offset nearest alignment; a tie prefers the negative one, deterministically."""
    return min(offsets, key=lambda o: (abs(o), o))


def _by_crc(crcs: Mapping[int, int]) -> dict[int, list[int]]:
    """Invert ``{offset: crc}`` to ``{crc: [offsets]}`` for one lookup per entry."""
    inverted: dict[int, list[int]] = {}
    for offset, value in crcs.items():
        inverted.setdefault(value, []).append(offset)
    return inverted


def match_disc(
    entries: Sequence[CtdbEntry], disc_crcs: Mapping[int, int]
) -> dict[int, int]:
    """``{entry index: offset}`` for each entry our whole-disc CRC equals.

    The offset is the one nearest alignment when more than one matches. An entry
    without a whole-disc CRC never matches. Pure; never raises.
    """
    inverted = _by_crc(disc_crcs)
    matched: dict[int, int] = {}
    for index, entry in enumerate(entries):
        if entry.crc is None:
            continue
        offsets = inverted.get(entry.crc)
        if offsets:
            matched[index] = _closest_to_zero(offsets)
    return matched


def entry_offsets(
    entries: Sequence[CtdbEntry], track_crcs: Sequence[Mapping[int, int]]
) -> dict[int, int]:
    """``{entry index: offset}`` for each entry its own per-track CRCs place.

    The offset at which the most of the entry's tracks equal ours, when at least
    :data:`CONSENSUS_TRACKS` do (a one-track disc needs its one track). Ties go
    to the offset nearest alignment. Stands in for CUETools' syndrome-based
    ``FindOffset`` (module docstring). Pure; never raises.
    """
    count = len(track_crcs)
    needed = min(CONSENSUS_TRACKS, count)
    inverted = [_by_crc(crcs) for crcs in track_crcs]
    placed: dict[int, int] = {}
    for index, entry in enumerate(entries):
        if needed == 0 or len(entry.track_crcs) != count:
            continue
        votes: dict[int, int] = {}
        for position, value in enumerate(entry.track_crcs):
            for offset in inverted[position].get(value, ()):
                votes[offset] = votes.get(offset, 0) + 1
        if not votes:
            continue
        offset, tally = min(votes.items(), key=lambda v: (-v[1], abs(v[0]), v[0]))
        if tally >= needed:
            placed[index] = offset
    return placed


def _agreeing_offset(
    crcs: Mapping[int, int], inverted: Mapping[int, list[int]], want: int, home: int
) -> int | None:
    """Where this track agrees with an entry's CRC ``want``, or ``None``.

    First at the entry's own offset ``home``, then anywhere in ±2939 (nearest
    alignment first): CUETools' ``TrackCRC(i, -entry.offset)``, then its
    ``_arOffsetRange`` loop.
    """
    if crcs.get(home) == want:
        return home
    near = [o for o in inverted.get(want, ()) if abs(o) <= AR_OFFSET_RANGE]
    return _closest_to_zero(near) if near else None


def match_tracks(
    entries: Sequence[CtdbEntry],
    track_crcs: Sequence[Mapping[int, int]],
    disc_matched: Mapping[int, int],
) -> tuple[CtdbTrackResult, ...]:
    """Each track's result, in disc order. Pure; never raises.

    ``track_crcs`` is :attr:`SweepResult.tracks`; ``disc_matched`` is
    :func:`match_disc`'s answer. An entry whose ``trackcrcs`` list does not have
    one CRC per track is ignored for per-track purposes, as CUETools' ``DBEntry``
    ignores it: a list of the wrong length cannot be lined up with our tracks.
    """
    count = len(track_crcs)
    placed = entry_offsets(entries, track_crcs)
    results: list[CtdbTrackResult] = []
    for position, crcs in enumerate(track_crcs):
        number = position + 1
        if 0 not in crcs:
            # Without our aligned CRC the audio did not all arrive; a match or a
            # difference found only at shifted offsets would be about other audio.
            results.append(
                CtdbTrackResult(
                    number, TrackVerdict.NOT_DETERMINED, reason=NO_LOCAL_CRC_REASON
                )
            )
            continue
        inverted = _by_crc(crcs)
        compared = False  # did any entry say anything about this track?
        agreeing = 0
        # (confidence, offset) of each agreeing entry; the strongest names the
        # track's offset, the one nearest alignment among equals.
        agreements: list[tuple[int, int]] = []
        disagreeing = 0
        strongest_disagreeing = 0
        for index, entry in enumerate(entries):
            weight = max(0, entry.confidence)
            offset: int | None = disc_matched.get(index)
            if offset is None:
                if len(entry.track_crcs) != count:
                    continue  # this entry says nothing usable about tracks
                compared = True
                offset = _agreeing_offset(
                    crcs, inverted, entry.track_crcs[position], placed.get(index, 0)
                )
                if offset is None:
                    disagreeing += weight
                    strongest_disagreeing = max(strongest_disagreeing, weight)
                    continue
            compared = True
            agreeing += weight
            agreements.append((weight, offset))
        best = (
            min(agreements, key=lambda a: (-a[0], abs(a[1]), a[1]))
            if agreements
            else None
        )
        if best is not None:
            verdict = TrackVerdict.MATCH
        elif compared:
            verdict = TrackVerdict.DIFFERS
        else:
            verdict = TrackVerdict.NOT_DETERMINED
        results.append(
            CtdbTrackResult(
                number,
                verdict,
                confidence=agreeing,
                disagreeing_confidence=disagreeing,
                strongest_disagreeing=strongest_disagreeing,
                our_crc=crcs.get(0),
                offset=best[1] if best is not None else None,
                reason=NO_TRACK_CRCS_REASON
                if verdict is TrackVerdict.NOT_DETERMINED
                else "",
            )
        )
    return tuple(results)
