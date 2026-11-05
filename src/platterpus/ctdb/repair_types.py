# SPDX-License-Identifier: GPL-3.0-only
"""The data a CTDB repair plans, proves and records (TASKS R43). Pure; no I/O.

Three stages, three shapes:

* :class:`RepairPlan` (or :class:`PlanRefusal`) — what :mod:`platterpus.ctdb.
  repair_plan` decided from the localisation, before any file is opened;
* :class:`RepairedTrack` — one rewritten file, with every CRC measured before
  and after;
* :class:`RepairRecord` — the whole outcome, ``repaired`` or ``refused`` or
  ``failed`` with the reason, which the rip report carries as ``ctdb.repair``
  (schema 44; ``rip_report._ctdb_repair``).

A record is written for a refusal too, because "the repair was refused, and
why" is the answer a user asked for when they asked for a repair.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


@dataclass(frozen=True)
class SampleFix:
    """One 16-bit word to correct, placed in its file.

    ``frame`` counts from the start of the track's FILE (0 = its first frame),
    ``channel`` is 0 for left and 1 for right, and ``value`` is the XOR that
    turns our word into the entry's. ``disc_word`` is the word's index in the
    whole disc's audio, as the localisation located it.
    """

    track: int
    frame: int
    channel: int
    disc_word: int
    value: int

    @property
    def track_word(self) -> int:
        """The word's index in the track's PCM: ``2 * frame + channel``."""
        return 2 * self.frame + self.channel


@dataclass(frozen=True)
class RepairPlan:
    """What a repair will change, and what it must reproduce. Never partial.

    ``offset`` is ours (an entry at ``o`` holds at its frame ``f`` what we hold
    at ``f + o``); ``expected_*`` are the entry's CRCs at that offset;
    ``track_crc32s`` each track's whole-file CRC-32 as the localisation measured
    it, which the files must still have.
    """

    entry_id: str
    confidence: int
    offset: int
    npar: int
    expected_disc_crc: int
    expected_track_crcs: tuple[int, ...]
    fixes: tuple[SampleFix, ...]
    track_starts: tuple[int, ...]
    track_frames: tuple[int, ...]
    track_crc32s: tuple[int, ...]

    @property
    def total_frames(self) -> int:
        return sum(self.track_frames)

    @property
    def tracks(self) -> tuple[int, ...]:
        """The track numbers the plan rewrites, in disc order."""
        return tuple(sorted({fix.track for fix in self.fixes}))

    def fixes_for(self, track: int) -> tuple[SampleFix, ...]:
        return tuple(fix for fix in self.fixes if fix.track == track)


@dataclass(frozen=True)
class PlanRefusal:
    """Why no repair is planned: one sentence a user can read."""

    reason: str


class RepairStatus(enum.Enum):
    """The three outcomes. Only REPAIRED means a file on disk changed."""

    REPAIRED = "repaired"  # written, proved, and committed
    REFUSED = "refused"  # a guard said no before anything was replaced
    FAILED = "failed"  # a tool or the disk failed; nothing was replaced


@dataclass(frozen=True)
class RepairedTrack:
    """One rewritten track: where it is, where the original went, and its numbers.

    ``pcm_crc32_*`` are the CRC-32 of the file's whole decoded audio (EAC's "Copy
    CRC" for the track); ``ctdb_crc_*`` the track's CTDB CRC at the entry's
    offset (``before`` only when the verify measured it); ``accuraterip_*`` our
    own AccurateRip v1/v2 of the file (``platterpus.accuraterip_crc``), the one
    witness independent of CTDB.
    """

    track: int
    path: str
    original_kept_as: str
    samples_corrected: int
    pcm_crc32_before: int
    pcm_crc32_after: int
    ctdb_crc_expected: int
    ctdb_crc_after: int
    ctdb_crc_before: int | None = None
    accuraterip_v1_before: int | None = None
    accuraterip_v2_before: int | None = None
    accuraterip_v1_after: int | None = None
    accuraterip_v2_after: int | None = None


@dataclass(frozen=True)
class RepairRecord:
    """The whole outcome of one repair attempt, as the report records it.

    ``words`` lists every correction (track, frame, channel, value); ``tracks``
    is filled only when REPAIRED. ``disc_crc_*`` are the whole-disc CTDB CRC at
    the entry's offset. ``untouched`` names what the repair deliberately did not
    change (the ripper's logs, derived copies), so nobody reads a stale file as
    repaired.
    """

    status: RepairStatus
    reason: str = ""
    entry_id: str = ""
    confidence: int = 0
    offset: int | None = None
    disc_crc_expected: int | None = None
    disc_crc_before: int | None = None
    disc_crc_after: int | None = None
    words: tuple[SampleFix, ...] = ()
    tracks: tuple[RepairedTrack, ...] = ()
    encoder_argv: tuple[str, ...] = ()
    untouched: tuple[str, ...] = ()

    @property
    def cuetools_offset(self) -> int | None:
        """The offset as CUETools writes it: the opposite sign (``CDRepair.cs:213``)."""
        return None if self.offset is None else -self.offset


def refused(reason: str, plan: RepairPlan | None = None) -> RepairRecord:
    """A REFUSED record, carrying what the plan said when there was one."""
    return _unchanged(RepairStatus.REFUSED, reason, plan)


def failed(reason: str, plan: RepairPlan | None = None) -> RepairRecord:
    """A FAILED record: a tool or the disk failed and nothing was replaced."""
    return _unchanged(RepairStatus.FAILED, reason, plan)


def _unchanged(
    status: RepairStatus, reason: str, plan: RepairPlan | None
) -> RepairRecord:
    if plan is None:
        return RepairRecord(status, reason)
    return RepairRecord(
        status,
        reason,
        entry_id=plan.entry_id,
        confidence=plan.confidence,
        offset=plan.offset,
        disc_crc_expected=plan.expected_disc_crc,
        words=plan.fixes,
    )
