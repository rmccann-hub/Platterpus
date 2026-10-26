# SPDX-License-Identifier: GPL-3.0-only
"""Where a rip differs from a CTDB entry, as data and as words (TASKS R43).

:mod:`platterpus.ctdb.localise` finds the differing samples; this module holds
what it found and turns it into what every surface shows, per track, in the shape
EAC's CTDB plugin prints it: ``differs in 16 samples @04:04:68,04:05:17,04:11:32``.
Pure and numpy-free, so the report, the results pane and ``--ctdb-calibrate`` can
read a localisation without importing the arithmetic that made it.

**The positions, the way CUETools writes them** (LGPL ``CDRepair.cs``,
``GetAffectedSectors``; written from its behaviour, not its code): each position
is the SECTOR (588 frames, 1/75 s) the sample sits in, counted from the start of
its track, as ``mm:ss:ff``; differing samples within five sectors of each other
are one place, written ``a-b`` when it spans more than one sector. A "sample" is
one channel's 16-bit value, which is what CUETools counts, so the number is
comparable with an EAC log's.
"""

from __future__ import annotations

import bisect
import enum
from collections.abc import Sequence
from dataclasses import dataclass

#: Frames per CD sector, and sectors per second.
_FRAMES_PER_SECTOR: int = 588
_SECTORS_PER_SECOND: int = 75

#: Differing samples closer than this many 16-bit words are one place: CUETools'
#: default ``coalesce`` of five sectors.
COALESCE_WORDS: int = 2 * _FRAMES_PER_SECTOR * 5

#: The most places one line names; the rest are counted, never dropped silently.
MAX_PLACES_SHOWN: int = 12


class LocalisationStatus(enum.Enum):
    """Whether the differing samples were located. Tri-state, as every CTDB answer."""

    LOCATED = "located"  # the parity named the samples and the CRC confirmed them
    NOT_DETERMINED = "not_determined"  # tried, and could not say (reason given)
    NOT_NEEDED = "not_needed"  # no entry outweighing ours differs, or no parity


@dataclass(frozen=True)
class EntryLocalisation:
    """One entry's answer: where our audio differs from it, or why that is unknown.

    ``words`` are the differing 16-bit words, counted from the start of the disc's
    audio (word ``2f`` is frame ``f``'s left channel), sorted. ``offset`` is the
    alignment it was found at, in frames.
    """

    entry_id: str
    confidence: int
    status: LocalisationStatus
    offset: int | None = None
    words: tuple[int, ...] = ()
    reason: str = ""


@dataclass(frozen=True)
class CtdbLocalisation:
    """The disc-level answer: one row per entry tried, and the reason when none was."""

    status: LocalisationStatus
    reason: str = ""
    entries: tuple[EntryLocalisation, ...] = ()


@dataclass(frozen=True)
class TrackDifference:
    """Where one track differs from one entry: the per-track line's content."""

    entry_id: str
    confidence: int
    samples: int
    places: tuple[str, ...]
    elided: int = 0

    @property
    def text(self) -> str:
        """``differs in 16 samples @04:04:68,04:05:17,04:11:32`` (EAC's layout)."""
        noun = "sample" if self.samples == 1 else "samples"
        shown = ",".join(self.places)
        more = f" and {self.elided:,} more places" if self.elided else ""
        return f"differs in {self.samples:,} {noun} @{shown}{more}"


def msf(sectors: int) -> str:
    """``mm:ss:ff`` for a sector count, as CUETools' ``TimeToString``."""
    frames = sectors % _SECTORS_PER_SECOND
    seconds = (sectors // _SECTORS_PER_SECOND) % 60
    minutes = sectors // (_SECTORS_PER_SECOND * 60)
    return f"{minutes:02d}:{seconds:02d}:{frames:02d}"


def _places(words: Sequence[int], track_start_frame: int) -> list[str]:
    """Coalesce sorted words into places, each ``mm:ss:ff`` or ``mm:ss:ff-mm:ss:ff``."""
    places: list[str] = []
    index = 0
    while index < len(words):
        end = index
        while end + 1 < len(words) and words[end + 1] - words[end] < COALESCE_WORDS:
            end += 1
        first = (words[index] // 2 - track_start_frame) // _FRAMES_PER_SECTOR
        last = (words[end] // 2 - track_start_frame) // _FRAMES_PER_SECTOR
        places.append(msf(first) if first == last else f"{msf(first)}-{msf(last)}")
        index = end + 1
    return places


def track_differences(
    localisation: CtdbLocalisation | None,
    track_starts: Sequence[int],
    total_frames: int,
) -> dict[int, tuple[TrackDifference, ...]]:
    """``{track number: differences}`` for every track a located entry differs in.

    ``track_starts`` are frame positions from the start of the disc's audio (track
    1 at 0). Entries come strongest first, so the first difference of a track is
    the one against the strongest entry. Pure; never raises.
    """
    found: dict[int, list[TrackDifference]] = {}
    if localisation is None or not track_starts:
        return {}
    starts = list(track_starts)
    for entry in localisation.entries:
        if entry.status is not LocalisationStatus.LOCATED:
            continue
        by_track: dict[int, list[int]] = {}
        for word in entry.words:
            frame = word // 2
            if not 0 <= frame < total_frames:
                continue
            position = bisect.bisect_right(starts, frame) - 1
            if position >= 0:
                by_track.setdefault(position, []).append(word)
        for position, words in sorted(by_track.items()):
            places = _places(sorted(words), starts[position])
            found.setdefault(position + 1, []).append(
                TrackDifference(
                    entry_id=entry.entry_id,
                    confidence=entry.confidence,
                    samples=len(words),
                    places=tuple(places[:MAX_PLACES_SHOWN]),
                    elided=max(0, len(places) - MAX_PLACES_SHOWN),
                )
            )
    return {number: tuple(rows) for number, rows in found.items()}
