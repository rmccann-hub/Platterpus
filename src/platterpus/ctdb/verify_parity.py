# SPDX-License-Identifier: GPL-3.0-only
"""Locate our differences from ONE CTDB entry: CUETools' ``VerifyParity``, clean-room.

Steps 2 to 5 of :mod:`platterpus.ctdb.localise` (read its docstring first), for
one entry, once our syndromes are computed. Imports numpy through
:mod:`platterpus.ctdb.syndromes`, so ``localise`` imports this module only after
the dependency registry says numpy is installed.

Written from CUETools' published behaviour (LGPL ``CDRepair.cs``: ``FindOffset``,
``VerifyParity``; ``CUEToolsDB.cs``: ``FetchDB``), not its code (KDD-16).
"""

from __future__ import annotations

import time
import zlib
from collections.abc import Mapping, Sequence

import numpy as np

from platterpus.adapters.ctdb_client import CTDBClient, CtdbEntry
from platterpus.adapters.ctdb_parity import MAX_NPAR
from platterpus.ctdb.calibrate import crc32_combine
from platterpus.ctdb.differences import EntryLocalisation, LocalisationStatus
from platterpus.ctdb.rs_decode import decode_column, row_of_power
from platterpus.ctdb.syndromes import (
    STRIDE,
    OurSyndromes,
    Words,
    chien_powers_fast,
    column0_by_offset,
    record_syndromes,
    syndromes_at,
)

#: CTDB's own alignment range in frames (CUETools' ``FindOffset`` loop).
REACH: int = STRIDE // 2 - 1


def corrected_crc(
    our_crc: int,
    words: Sequence[int],
    values: Sequence[int],
    window: int,
    deadline: float = float("inf"),
) -> int | None:
    """Our CRC with each word XORed by its value: what the entry's audio CRCs to.

    CRC-32 is affine over GF(2), so flipping bits changes it by the CRC of the flip
    pattern alone: for a 2-byte change at byte ``b`` of an ``n``-byte window, the
    zero-initialised CRC of those two bytes carried through ``n - b - 2`` zero
    bytes (zlib's ``crc32_combine``). ``words`` count from the window's start and
    ``window`` is its length in bytes. About 5 ms a word (measured 2026-10-26), so
    a few hundred differing samples cost a second or two; ``None`` once the
    ``deadline`` passes, which only the thousands-of-samples case reaches.
    """
    zero_pair = zlib.crc32(b"\0\0")
    crc = our_crc
    for count, (word, value) in enumerate(zip(words, values, strict=True)):
        if count % 64 == 63 and time.monotonic() > deadline:
            return None
        flip = zlib.crc32(value.to_bytes(2, "little")) ^ zero_pair
        crc ^= crc32_combine(flip, 0, window - 2 * word - 2)
    return crc & 0xFFFFFFFF


def find_offset(ours: OurSyndromes, column0: Sequence[int]) -> int | None:
    """Where our column-0 syndromes equal the entry's, nearest alignment first.

    CUETools' ``FindOffset`` exact test. 16 words of 16 bits agreeing by chance is
    a 1-in-2^256 event, so an equality here is the alignment; the CRC check in
    :func:`verify_at` confirms it anyway.
    """
    npar = len(column0)
    if not 1 <= npar <= MAX_NPAR:
        return None
    ours0 = column0_by_offset(ours, npar, REACH)
    hits = np.flatnonzero((ours0 == np.array(column0, dtype=np.uint16)).all(axis=1))
    if not len(hits):
        return None
    return min((int(k) - REACH for k in hits), key=lambda o: (abs(o), o))


def verify_at(
    entry: CtdbEntry,
    offset: int,
    ours: OurSyndromes,
    theirs: Words,
    our_crc: int,
    deadline: float,
) -> EntryLocalisation | None:
    """CUETools' ``VerifyParity`` at one alignment: located, or ``None`` to try another.

    ``None`` when a column carries more differences than the parity can locate,
    when time runs out, or when the corrections do not reproduce the entry's CRC.
    """
    shifted = syndromes_at(ours, offset, len(theirs))
    if shifted is None or entry.crc is None:
        return None
    diff = shifted ^ theirs
    words: list[int] = []
    values: list[int] = []
    for column in np.flatnonzero(diff.any(axis=0)):
        if time.monotonic() > deadline:
            return None
        found = decode_column(
            [int(v) for v in diff[:, column]], ours.rows, roots=chien_powers_fast
        )
        if found is None:
            return None
        for power, value in zip(found.powers, found.values, strict=True):
            words.append(row_of_power(power, ours.rows) * STRIDE + int(column))
            values.append(value)
    window = ours.rows * STRIDE * 2
    if corrected_crc(our_crc, words, values, window, deadline) != entry.crc:
        return None  # a stray decode, or the time bound (the caller tells which)
    start = STRIDE + 2 * offset  # the window's first word in our audio
    return EntryLocalisation(
        entry.entry_id,
        entry.confidence,
        LocalisationStatus.LOCATED,
        offset,
        words=tuple(sorted(start + w for w in words)),
    )


def locate_entry(
    entry: CtdbEntry,
    placed: int | None,
    ours: OurSyndromes,
    disc_crcs: Mapping[int, int],
    client: CTDBClient,
    deadline: float,
) -> EntryLocalisation:
    """Fetch the entry's record, check it, align it, and locate. Never raises.

    Alignments are tried in order: where the syndromes say (exact), where the
    entry's per-track CRCs placed it (``placed``), then 0. The first that passes
    :func:`verify_at` wins.
    """

    def failed(reason: str, offset: int | None = None) -> EntryLocalisation:
        return EntryLocalisation(
            entry.entry_id,
            entry.confidence,
            LocalisationStatus.NOT_DETERMINED,
            offset,
            reason=reason,
        )

    npar = min(entry.npar, MAX_NPAR)
    if npar < 2 or entry.stride * 2 != STRIDE:
        return failed(
            f"parity shape not supported (npar {entry.npar}, stride {entry.stride})"
        )
    fetched = client.fetch_parity(entry, npar)
    if fetched.error:
        return failed(fetched.error)
    theirs = record_syndromes(fetched.data, npar)
    if theirs is None:
        return failed("the parity record has the wrong size")
    column0 = tuple(int(v) for v in theirs[:, 0])
    if entry.syndrome and column0 != tuple(entry.syndrome[:npar]):
        return failed("the parity record does not match the entry's own syndrome")

    exact = find_offset(ours, column0)
    tried: list[int] = []
    for offset in (exact, placed, 0):
        if offset is None or offset in tried or abs(offset) > REACH:
            continue
        tried.append(offset)
        our_crc = disc_crcs.get(offset)
        if our_crc is None:
            continue  # no CRC of ours here, so nothing to close the loop with
        if time.monotonic() > deadline:
            return failed("stopped at the time bound", offset)
        located = verify_at(entry, offset, ours, theirs, our_crc, deadline)
        if located is not None:
            return located
        if time.monotonic() > deadline:
            return failed("stopped at the time bound", offset)
    shown = ", ".join(f"{o:+d}" for o in tried) or "none"
    return failed(
        "the parity does not locate a difference that reproduces the entry's CRC "
        f"(alignments tried: {shown})"
    )
