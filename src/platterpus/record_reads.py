# SPDX-License-Identifier: GPL-3.0-only
"""Every distinct ``-Z`` read of a track, from the fork's ``cyanrip-diagnostics/13``.

**Why this exists.** The log's ``Other read:`` lines (:mod:`platterpus.other_reads`)
say which reads were not kept and where they differ; the ``-j`` record keeps all
of them, the kept one too, with each read's own per-second CRCs, which is what
rebuilding a disputed second needs (our ``docs/eac-parity.md`` Part G.5; the
fork's round 38 lap 8 S16, which moved the record to ``/13``).

**What a ``track_state`` row says, from their source**
(``cyanrip@40dc64d7:src/diagnostics.c:553-590``), under the key ``reads``:

* a list, in the order each read was first read, one object per distinct read:
  ``eac_crc`` and ``accurip_v1`` / ``accurip_v2`` as ``"%08X"``; ``count``, how
  many whole-track reads gave it; ``last_read``, the newest of them counting from
  1; ``kept``, whether it is the read the files carry; ``block_crcs``, its own
  per-second CRCs written as the track's are (:mod:`platterpus.record_block_crcs`),
  ``null`` when memory for them could not be had; ``file``, the path
  ``--keep-every-read`` saved it to, the folder as given less any trailing slash
  then ``/NN-CRC.wav`` (``cyanrip@40dc64d7:src/cyanrip_main.c:1439-1465``, their
  round 38 lap 10 S5 and S6), ``null`` when none was saved;
* ``null`` for a track read without ``-Z``, and for one never read.

Their own test pins the shape, a null ``block_crcs`` and ``file`` included
(``cyanrip@40dc64d7:tests/diagrecord.c:360-402``). **No read is kept** when the
source's kept index is unset (``r->kept = i == kept``,
``cyanrip@40dc64d7:src/cyanrip_main.c:1416``), so zero kept is a state the
record can state, and :meth:`DistinctReads.kept` then answers None.

**States**, in :mod:`platterpus.record_block_crcs`'s words: ``not_present`` (no
key: ``/12`` and earlier), ``not_stated`` (``null``), ``unrecognised`` (not a
list), ``read``. An entry that is not an object is skipped and counted; a field
missing or mistyped is None and the entry is marked not ``complete``, never
filled with a default. Bounded: the first :data:`KEEP_HEAD` and the last
:data:`KEEP_TAIL` entries kept, the middle counted. Read once with the rest of
the row, by :func:`platterpus.isrc_provenance.parse_isrcs`. Pure, never raises.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from platterpus import diagnostics, inbound_text
from platterpus.record_block_crcs import NOT_STATED as BLOCK_CRCS_NOT_STATED
from platterpus.record_block_crcs import READ as BLOCK_CRCS_READ
from platterpus.record_block_crcs import BlockCrcs, differing_seconds, parse_block_crcs
from platterpus.report_types import DistinctReadEntry

#: The record's key, spelled once.
READS_KEY: Final[str] = "reads"

READ: Final[str] = "read"
NOT_PRESENT: Final[str] = "not_present"
NOT_STATED: Final[str] = "not_stated"
UNRECOGNISED: Final[str] = "unrecognised"
STATES: Final[frozenset[str]] = frozenset({READ, NOT_PRESENT, NOT_STATED, UNRECOGNISED})

#: Entries kept from each end. A track has at most as many distinct reads as
#: ``-r`` allows; a list longer than this is not one cyanrip wrote for a CD track.
KEEP_HEAD: Final[int] = 32
KEEP_TAIL: Final[int] = 32

#: A path longer than Linux's 4,096 bytes is kept as its head and tail, counted.
_MAX_FILE_CHARS: Final[int] = 4096
_FILE_TAIL: Final[int] = 512
_HEX_CRC: Final[re.Pattern[str]] = re.compile(r"[0-9A-Fa-f]{8}")


@dataclass(frozen=True)
class RecordRead:
    """One entry of ``reads``. ``None`` is a field missing, mistyped or null."""

    eac_crc: str | None
    count: int | None
    last_read: int | None
    kept: bool | None
    accurip_v1: str | None
    accurip_v2: str | None
    block_crcs: BlockCrcs
    file: str | None
    #: False when any field was missing or of the wrong type; ``file`` and
    #: ``block_crcs`` may be ``null`` and still be complete.
    complete: bool


@dataclass(frozen=True)
class DistinctReads:
    """One row's ``reads``, as the record states it."""

    state: str = NOT_PRESENT
    reads: tuple[RecordRead, ...] = ()
    #: Entries cut from the middle past the bound.
    not_kept: int = 0
    #: Entries that were not objects, skipped.
    not_read: int = 0

    def kept(self) -> RecordRead | None:
        """The one read marked kept, or None when none or more than one is."""
        marked = [read for read in self.reads if read.kept is True]
        return marked[0] if len(marked) == 1 else None


def _crc(value: object) -> str | None:
    if isinstance(value, str) and _HEX_CRC.fullmatch(value):
        return value.upper()
    return None


def _positive(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 1:
        return value
    return None


def _file(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    bounded = diagnostics.bounded_chars(
        value, head=_MAX_FILE_CHARS - _FILE_TAIL, tail=_FILE_TAIL
    )
    return inbound_text.screen_line(bounded).text


def _entry(value: Mapping[str, object]) -> RecordRead:
    crc = _crc(value.get("eac_crc"))
    count = _positive(value.get("count"))
    last_read = _positive(value.get("last_read"))
    kept = value.get("kept")
    v1 = _crc(value.get("accurip_v1"))
    v2 = _crc(value.get("accurip_v2"))
    raw_file = value.get("file")
    file = _file(raw_file)
    blocks = parse_block_crcs(value)
    complete = (
        None not in (crc, count, last_read, v1, v2)
        and isinstance(kept, bool)
        and "file" in value
        and (raw_file is None or file is not None)
        and blocks.state in (BLOCK_CRCS_READ, BLOCK_CRCS_NOT_STATED)
    )
    return RecordRead(
        eac_crc=crc,
        count=count,
        last_read=last_read,
        kept=kept if isinstance(kept, bool) else None,
        accurip_v1=v1,
        accurip_v2=v2,
        block_crcs=blocks,
        file=file,
        complete=complete,
    )


def parse_distinct_reads(row: Mapping[str, object]) -> DistinctReads:
    """The ``reads`` key of one ``track_state`` row. Pure; never raises."""
    try:
        if READS_KEY not in row:
            return DistinctReads()
        value = row.get(READS_KEY)
        if value is None:
            return DistinctReads(state=NOT_STATED)
        if not isinstance(value, list):
            return DistinctReads(state=UNRECOGNISED)
        if len(value) > KEEP_HEAD + KEEP_TAIL:
            candidates = value[:KEEP_HEAD] + value[-KEEP_TAIL:]
            not_kept = len(value) - len(candidates)
        else:
            candidates, not_kept = value, 0
        reads = tuple(_entry(item) for item in candidates if isinstance(item, Mapping))
        return DistinctReads(
            state=READ,
            reads=reads,
            not_kept=not_kept,
            not_read=len(candidates) - len(reads),
        )
    except (AttributeError, TypeError):
        return DistinctReads(state=UNRECOGNISED)


def report_entries(reads: DistinctReads) -> list[DistinctReadEntry] | None:
    """The report's ``distinct_reads``, or None unless the key read. Never raises.

    Each read not kept carries the seconds its per-second CRCs differ from the
    kept read's in, derived here from the two lists, not taken from the log;
    None for the kept read, or where either list cannot be compared.
    """
    if reads.state != READ:
        return None
    kept = reads.kept()
    rows: list[DistinctReadEntry] = []
    for read in reads.reads:
        differs = (
            differing_seconds(read.block_crcs, kept.block_crcs)
            if kept is not None and read is not kept
            else None
        )
        rows.append(
            {
                "eac_crc": read.eac_crc,
                "count": read.count,
                "last_read": read.last_read,
                "kept": read.kept,
                "accurip_v1": read.accurip_v1,
                "accurip_v2": read.accurip_v2,
                "block_crcs": (
                    list(read.block_crcs.crcs)
                    if read.block_crcs.state == BLOCK_CRCS_READ
                    else None
                ),
                "block_crcs_state": read.block_crcs.state,
                "file": read.file,
                "complete": read.complete,
                "differs_from_kept_in_seconds": (
                    list(differs) if differs is not None else None
                ),
            }
        )
    return rows
