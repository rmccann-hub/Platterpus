# SPDX-License-Identifier: GPL-3.0-only
"""The per-second CRCs the fork's ``-j`` record proposes at ``cyanrip-diagnostics/12``.

**Why it exists.** Two rips of one track that disagree say only THAT they
disagree: the whole-track CRC cannot say where. The 2026-11-03 run needed to
place track 3's wrong reads and had nothing finer than the track (the fork's
round 38 lap 1 S10). So the fork proposes, for each kept read, ``block_crcs``: a
CRC32 per 75 frames, one second of audio, so two rips can be compared region by
region without the audio. Adding a key moves the record to ``/12`` (each
addition has moved it, ``cyanrip@3f288fb:src/diagnostics.c:631-650``).

**Not built yet, and its shape is not settled by the lap.** It names the key and
what each entry covers, not how an entry is spelled. So this reader takes the
two shapes the record already uses for a CRC: an eight-digit hex string, as
``eac_crc`` is written (``"%08X"``, ``cyanrip@3f288fb:src/diagnostics.c:393-394``),
or a JSON number from 0 to 2**32 - 1. Each is kept as eight upper-case hex digits.

**Positions are the point, so they are never shifted.** Entry ``i`` covers
seconds ``i`` to ``i + 1`` of the track; dropping an unreadable entry would move
every later one to the wrong second and make two rips look different where they
are not. An entry we cannot read is kept as ``None`` in its place and counted;
past :data:`MAX_BLOCKS` the list is cut at the end, never in the middle, and the
cut is counted (CLAUDE.md's diagnostic-completeness rule).

**How ``/12`` is accepted.** Every reader recognises the record by its schema
PREFIX (``ripper_ending.RECORD_SCHEMA_PREFIX``), never by its number, so a
``/12`` record was never refused; a ``/11`` record lacks the key and reads
``not_present``. Read once with the rest of the row:
:func:`platterpus.isrc_provenance.parse_isrcs` hands each ``track_state`` row
here. Pure, Qt-free, never raises.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

#: The record's key, spelled once.
BLOCK_CRCS_KEY: Final[str] = "block_crcs"

#: Frames per block, as the lap states it: 75 frames, one second.
FRAMES_PER_BLOCK: Final[int] = 75

#: The longest track a CD can hold is under 100 minutes, 6,000 one-second blocks;
#: more than this is not a list of one track's seconds, and is cut at the end.
MAX_BLOCKS: Final[int] = 6000

#: One CRC32 as the record writes ``eac_crc``: eight hex digits.
_HEX_CRC: Final[re.Pattern[str]] = re.compile(r"[0-9A-Fa-f]{8}")
_CRC_MAX: Final[int] = 0xFFFFFFFF

#: The states of the key, in :mod:`platterpus.record_track_v11`'s words.
READ: Final[str] = "read"
NOT_PRESENT: Final[str] = "not_present"
NOT_STATED: Final[str] = "not_stated"
UNRECOGNISED: Final[str] = "unrecognised"
STATES: Final[frozenset[str]] = frozenset({READ, NOT_PRESENT, NOT_STATED, UNRECOGNISED})


@dataclass(frozen=True)
class BlockCrcs:
    """One ``track_state`` row's ``block_crcs``, as the record states it.

    ``crcs`` is position-aligned: entry ``i`` is second ``i`` of the track, as
    eight upper-case hex digits, or ``None`` where the record's entry could not
    be read. ``not_read`` counts those; ``not_kept`` counts entries past
    :data:`MAX_BLOCKS`, cut from the end.
    """

    state: str = NOT_PRESENT
    crcs: tuple[str | None, ...] = ()
    not_read: int = 0
    not_kept: int = 0


def _crc(entry: object) -> str | None:
    """One entry as eight upper-case hex digits, or None. Never raises."""
    if isinstance(entry, bool):
        return None
    if isinstance(entry, int):
        return f"{entry:08X}" if 0 <= entry <= _CRC_MAX else None
    if isinstance(entry, str) and _HEX_CRC.fullmatch(entry):
        return entry.upper()
    return None


def parse_block_crcs(row: Mapping[str, object]) -> BlockCrcs:
    """The ``block_crcs`` key of one ``track_state`` row. Pure; never raises."""
    try:
        if BLOCK_CRCS_KEY not in row:
            return BlockCrcs()
        value = row.get(BLOCK_CRCS_KEY)
        if value is None:
            return BlockCrcs(state=NOT_STATED)
        if not isinstance(value, list):
            return BlockCrcs(state=UNRECOGNISED)
        kept = [_crc(entry) for entry in value[:MAX_BLOCKS]]
        return BlockCrcs(
            state=READ,
            crcs=tuple(kept),
            not_read=sum(1 for crc in kept if crc is None),
            not_kept=max(0, len(value) - MAX_BLOCKS),
        )
    except (AttributeError, TypeError):
        return BlockCrcs(state=UNRECOGNISED)


def differing_seconds(first: BlockCrcs, second: BlockCrcs) -> tuple[int, ...] | None:
    """The seconds at which two reads of one track differ, or None.

    None when either list is not read, or they differ in length (two reads of one
    track that cover different spans cannot be compared second by second). A
    second either side could not read is not counted as differing. Never raises.
    """
    if first.state != READ or second.state != READ:
        return None
    if len(first.crcs) != len(second.crcs) or first.not_kept or second.not_kept:
        return None
    return tuple(
        index
        for index, (a, b) in enumerate(zip(first.crcs, second.crcs, strict=True))
        if a is not None and b is not None and a != b
    )
