# SPDX-License-Identifier: GPL-3.0-only
"""Turn a CTDB localisation into a repair plan, or say exactly why not (TASKS R43).

The localisation (:mod:`platterpus.ctdb.localise`) names each 16-bit word where
our audio differs from an entry, and the XOR the entry holds there. A REPAIR
applies those XORs to the files on disk, which is the first thing Platterpus
does that rewrites the archival master after a rip. So this step's job is to
refuse, and to say why, every case where the corrections cannot be placed
exactly or should not be applied at all. Pure and numpy-free; never raises
(``tests/test_ctdb_repair_plan.py`` holds it with a property test).

**What it refuses**, each with its own sentence:

* **not the strongest entry.** Only the entry with the most submissions is a
  repair target, and only when no other entry ties it. A located minority entry
  is never used: repairing toward it would make our rip agree with fewer
  people, not more (CUETools' own repair picks the most confident; ``cdverify``
  does the same, ``src/repair.rs``). And a rip that already MATCHES the strongest
  entry is that version of the disc: nothing is rewritten.
* **AccurateRip contradicts it.** A track AccurateRip verified as accurately
  ripped is never rewritten, whatever CTDB says: two witnesses disagree, and the
  disagreement is the finding, not something to settle by editing audio.
* **the guard bands.** The entry's parity and CRC cover only its window: our
  words ``[stride + 2*offset, stride + 2*offset + rows*stride)``. A word in the
  first stride or the last ``laststride`` (CUETools' names; ``crc.ctdb_trims``)
  is one neither the parity nor the CRC vouches for.
* **outside the audio, or in no track.** A word before the disc's first or past
  its last sample, or one the track layout cannot place.
* **a layout it cannot account for.** Audio before track 1 (a hidden track or a
  pregap the files hold, ``pregap_frames``) shifts every word, and a track that
  is not a whole number of CD sectors breaks the TOC the windows were cut from.
  The CTDB verify assumes neither (``toc.disc_toc_from_files``), so the repair
  does not either.
* **more corrections in one parity column than the parity can carry.** An entry
  with ``npar`` parity words per column locates at most ``npar // 2`` errors in
  it: 8 for npar 16, 4 for npar 8 (the reference disc's lookup holds both).
* **anything malformed.** Values outside 1..65535, a word listed twice, words
  and values of different lengths, an offset outside CTDB's ±5879 frames, or a
  localisation that did not measure every track's audio (without that, a file
  changed since cannot be detected; :mod:`platterpus.ctdb.repair_apply`).

**Offsets.** Ours: an entry at offset ``o`` holds, at its frame ``f``, what our
audio holds at frame ``f + o`` (``verify_parity``). CUETools' ``actualOffset``
is the opposite sign (``CDRepair.cs:212-213``: ``erroffi = stride + pos +
pregap*2 - actualOffset*2``, where ours is ``stride + 2*o + pos``).
"""

from __future__ import annotations

import bisect
from collections import Counter
from collections.abc import Mapping, Sequence

from platterpus.adapters.ctdb_client import CtdbEntry
from platterpus.ctdb.crc import CTDB_OFFSET_RANGE, CTDB_STRIDE_WORDS, ctdb_trims
from platterpus.ctdb.differences import (
    CtdbLocalisation,
    EntryLocalisation,
    LocalisationStatus,
)
from platterpus.ctdb.matching import match_disc
from platterpus.ctdb.repair_types import PlanRefusal, RepairPlan, SampleFix

#: Frames per CD sector.
SECTOR_FRAMES: int = 588

#: The most parity words per column CTDB serves (``adapters/ctdb_parity.MAX_NPAR``).
MAX_NPAR: int = 16


def _strongest(entries: Sequence[CtdbEntry]) -> tuple[int, CtdbEntry] | str:
    """The single entry with the most submissions, or why there is none."""
    if not entries:
        return "CTDB holds no entry for this disc"
    best = max(entry.confidence for entry in entries)
    top = [i for i, entry in enumerate(entries) if entry.confidence == best]
    if len(top) != 1:
        return (
            f"{len(top)} CTDB entries tie as the strongest ({best:,} submissions "
            "each), so there is no single version of the disc to repair toward"
        )
    return top[0], entries[top[0]]


def _layout(
    track_frames: Sequence[int], pregap_frames: int
) -> tuple[list[int], int] | str:
    """``(track starts, total frames)``, or why the layout cannot be trusted."""
    if pregap_frames != 0:
        return (
            f"the rip holds {pregap_frames:,} frames before track 1 (a hidden track "
            "or a pregap), which the CTDB check does not place; nothing is repaired"
        )
    if not track_frames:
        return "the rip has no tracks"
    starts: list[int] = []
    cursor = 0
    for number, frames in enumerate(track_frames, start=1):
        if not isinstance(frames, int) or frames <= 0 or frames % SECTOR_FRAMES:
            return (
                f"track {number} is not a whole number of CD sectors ({frames!r} "
                "frames), so its words cannot be placed against the disc's TOC"
            )
        starts.append(cursor)
        cursor += frames
    return starts, cursor


def _check_row(row: EntryLocalisation, npar: int) -> str | None:
    """The row's own consistency: why it cannot drive a repair, or ``None``."""
    if row.offset is None or abs(row.offset) > CTDB_OFFSET_RANGE:
        return f"the located offset {row.offset!r} is outside CTDB's ±5,879 frames"
    if not row.words:
        return "the localisation located no differing samples"
    if len(row.words) != len(row.values):
        return "the localisation kept a value for some corrections and not others"
    if any(not 0 < v <= 0xFFFF for v in row.values):
        return "a correction's value is not a non-zero 16-bit number"
    if any(b <= a for a, b in zip(row.words, row.words[1:], strict=False)):
        return "the corrected samples are not distinct and in order"
    window_start = CTDB_STRIDE_WORDS + 2 * row.offset
    per_column = Counter((w - window_start) % CTDB_STRIDE_WORDS for w in row.words)
    column, count = per_column.most_common(1)[0]
    if count > npar // 2:
        return (
            f"{count} corrections in one parity column (column {column}), more than "
            f"the {npar // 2} an entry with {npar} parity words can locate"
        )
    return None


def _place(
    row: EntryLocalisation, offset: int, starts: Sequence[int], total_frames: int
) -> tuple[SampleFix, ...] | str:
    """Each word as (track, frame, channel), or why one cannot be placed."""
    total_words = 2 * total_frames
    front, back = ctdb_trims(total_frames)
    window = (2 * (front + offset), total_words - 2 * (back - offset))
    fixes: list[SampleFix] = []
    for word, value in zip(row.words, row.values, strict=True):
        if not 0 <= word < total_words:
            return f"sample word {word:,} is outside the disc's audio"
        if word < window[0]:
            return (
                f"sample word {word:,} is in the first stride, the guard band the "
                "entry's parity and CRC do not cover"
            )
        if word >= window[1]:
            return (
                f"sample word {word:,} is in the last stride, the guard band the "
                "entry's parity and CRC do not cover"
            )
        frame = word // 2
        index = bisect.bisect_right(starts, frame) - 1
        if index < 0:
            return f"sample word {word:,} lies before track 1"
        fixes.append(SampleFix(index + 1, frame - starts[index], word % 2, word, value))
    return tuple(fixes)


def plan_repair(
    localisation: CtdbLocalisation | None,
    entries: Sequence[CtdbEntry],
    disc_crcs: Mapping[int, int],
    track_frames: Sequence[int],
    *,
    pregap_frames: int = 0,
    accuraterip_verified: Mapping[int, bool | None] | None = None,
) -> RepairPlan | PlanRefusal:
    """The repair toward the strongest CTDB entry, or why there is none. Never raises.

    ``disc_crcs`` is the verify's ``{offset: whole-disc CRC}`` (to see whether we
    already match); ``track_frames`` each track's frame count from its file;
    ``accuraterip_verified`` per track number: True where AccurateRip verified the
    track as ripped, False where it compared and did not, None or absent where
    it did not say.
    """
    try:
        return _plan(
            localisation,
            entries,
            disc_crcs,
            track_frames,
            pregap_frames,
            accuraterip_verified or {},
        )
    except (TypeError, ValueError, AttributeError, OverflowError) as exc:
        # A pure function over data from outside (a lookup, a decoder): malformed
        # input becomes a refusal with the reason, never an exception.
        return PlanRefusal(f"the repair could not be planned ({exc})")


def _plan(
    localisation: CtdbLocalisation | None,
    entries: Sequence[CtdbEntry],
    disc_crcs: Mapping[int, int],
    track_frames: Sequence[int],
    pregap_frames: int,
    verified: Mapping[int, bool | None],
) -> RepairPlan | PlanRefusal:
    strongest = _strongest(entries)
    if isinstance(strongest, str):
        return PlanRefusal(strongest)
    index, entry = strongest
    if index in match_disc(entries, disc_crcs):
        return PlanRefusal(
            "this rip already matches the strongest CTDB entry; nothing to repair"
        )
    if localisation is None or localisation.status is not LocalisationStatus.LOCATED:
        return PlanRefusal("the CTDB check located no difference to repair")
    row = next(
        (
            r
            for r in localisation.entries
            if r.entry_id == entry.entry_id and r.status is LocalisationStatus.LOCATED
        ),
        None,
    )
    if row is None:
        return PlanRefusal(
            f"the strongest CTDB entry ({entry.confidence:,} submissions) was not "
            "located; a repair toward a weaker entry is never made"
        )
    layout = _layout(track_frames, pregap_frames)
    if isinstance(layout, str):
        return PlanRefusal(layout)
    starts, total_frames = layout
    if entry.crc is None or len(entry.track_crcs) != len(starts):
        return PlanRefusal(
            "the strongest entry lacks the whole-disc or per-track CRCs the repair "
            "must reproduce"
        )
    if len(localisation.track_crc32s) != len(starts):
        return PlanRefusal(
            "the localisation did not measure every track's audio, so a file "
            "changed since could not be detected"
        )
    npar = min(entry.npar, MAX_NPAR)
    if npar < 2:
        return PlanRefusal(f"the entry's parity is too short (npar {entry.npar})")
    problem = _check_row(row, npar)
    if problem or row.offset is None:
        return PlanRefusal(problem or "the localisation has no offset")
    placed = _place(row, row.offset, starts, total_frames)
    if isinstance(placed, str):
        return PlanRefusal(placed)
    for track in sorted({fix.track for fix in placed}):
        if verified.get(track) is True:
            return PlanRefusal(
                f"AccurateRip verified track {track} as accurately ripped, and CTDB's "
                "strongest entry differs there; the two disagree, so nothing is "
                "rewritten"
            )
    return RepairPlan(
        entry_id=entry.entry_id,
        confidence=entry.confidence,
        offset=row.offset,
        npar=npar,
        expected_disc_crc=entry.crc,
        expected_track_crcs=tuple(entry.track_crcs),
        fixes=placed,
        track_starts=tuple(starts),
        track_frames=tuple(track_frames),
        track_crc32s=tuple(localisation.track_crc32s),
    )
