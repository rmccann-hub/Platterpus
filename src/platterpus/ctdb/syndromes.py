# SPDX-License-Identifier: GPL-3.0-only
"""OUR Reed-Solomon syndromes of a disc's audio, as CTDB's parity defines them (TASKS R43).

**The only module that imports numpy** (added on the owner's word of 2026-10-26;
DEPENDENCIES.md). :mod:`platterpus.ctdb.localise` imports it only after the
dependency registry says numpy is installed, so a dev install without numpy reads
"not determined" instead of failing.

**What a syndrome is here** (clean-room, KDD-16: from the published format, read
in the LGPL ``CUETools.AccurateRip/AccurateRip.cs`` and ``CDRepair.cs``, no code
copied). Lay the disc's little-endian 16-bit samples out as one stream of words,
left and right interleaved. Skip the first ``stride`` words (11,760, i.e. 5,880
frames: the same front guard band the CTDB CRC skips, ``crc.ctdb_trims``) and cut
the rest into rows of ``stride`` words; there are ``rows = total_words // stride
- 2`` of them, which ends exactly where the CRC's back guard band starts. Column
``c`` is word ``c`` of every row, 11,760 columns in all, each one a sequence of
``rows`` field elements (:mod:`platterpus.ctdb.gf16`). For each column and each
``i`` in ``0..15``::

    S_i(c) = sum over rows r of  word(r, c) * alpha**(i * (rows - 1 - r))

CTDB stores the entry's ``S_i`` for every column (``adapters/ctdb_parity.py``);
we compute ours over our audio. Where the two agree the audio agrees; XOR them
and :mod:`platterpus.ctdb.rs_decode` says which rows of a column differ. CUETools
keeps a systematic parity remainder internally and converts it to these values
(``Parity2Syndrome.cs``); ``tests/test_ctdb_syndromes.py`` checks that the two
definitions agree, from the algebra rather than from their code.

**How, in seconds rather than hours.** Horner's rule down the rows:
``S <- S * alpha**i XOR row``, for all 16 ``i`` and all 11,760 columns at once.
Multiplying by the constant ``alpha**i`` is one lookup in a 65,536-entry table,
so each row is one ``numpy.take`` over 188,160 values and one XOR. Measured on the
2026-10-26 session box (numpy 2.4.6, 4 cores): 0.64 ms a row, 17 s for the
reference disc's 26,866 rows.

**Other alignments without another pass.** A pressing ``o`` frames from ours
moves the window ``2o`` words. A column then either is another column of ours
(same rows) or is one shifted by a whole row, which :func:`syndromes_at` gets by
multiplying by ``alpha**+-i`` and swapping one word at each end. Those edge words
are why :class:`SyndromeAccumulator` keeps the two rows either side of the window.

Memory: the 16 x 11,760 syndromes (376 KB), the edge rows (94 KB), the lookup
table (2 MB) and one row index (752 KB), plus whatever chunk the caller is
feeding: one track at a time, as the rest of the CTDB verify does (#39).
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from platterpus.ctdb.crc import CTDB_STRIDE_WORDS
from platterpus.ctdb.gf16 import EXP, LOG, ORDER

#: Words per row and columns per disc: CUETools' ``10 * 588 * 2``.
STRIDE: int = CTDB_STRIDE_WORDS

#: How many syndromes we compute: CUETools' ``maxNpar``. An entry with more uses
#: its first 16; one with fewer uses its own count.
MAX_NPAR: int = 16

#: Check the deadline after this many rows (about 40 ms of work).
_ROWS_PER_CHECK: int = 64

Words = NDArray[np.uint16]

_EXP: NDArray[np.uint16] = np.array(EXP, dtype=np.uint16)
_LOG: NDArray[np.int64] = np.array(LOG, dtype=np.int64)


def _horner_table() -> NDArray[np.uint16]:
    """One flat table: entry ``i * 65536 + v`` is ``v * alpha**i``, for i < 16."""
    values = np.arange(1, 65536, dtype=np.int64)
    table = np.zeros((MAX_NPAR, 65536), dtype=np.uint16)
    for i in range(MAX_NPAR):
        table[i, 1:] = _EXP[(_LOG[values] + i) % ORDER]
    return table.reshape(-1)


_TABLE: NDArray[np.uint16] = _horner_table()
_TABLE_BASE: NDArray[np.int32] = (np.arange(MAX_NPAR, dtype=np.int32) * 65536)[:, None]
_POWERS: NDArray[np.int64] = np.arange(MAX_NPAR, dtype=np.int64)[:, None]


def _mul_alpha(values: Words, power: NDArray[np.int64] | int) -> Words:
    """``values * alpha**power`` element-wise (``power`` broadcasts)."""
    product: Words = _EXP[(_LOG[values] + power) % ORDER]
    return np.where(values == 0, np.uint16(0), product).astype(np.uint16)


@dataclass(frozen=True)
class ColumnLayout:
    """How a disc of ``total_frames`` frames is cut into rows and columns."""

    total_words: int
    rows: int

    @property
    def leadout_start(self) -> int:
        """First word of the two rows kept after the window: row ``rows - 1``'s start."""
        return self.rows * STRIDE


def layout(total_frames: int) -> ColumnLayout | None:
    """The layout, or ``None`` for a disc too short to hold one row and its edges."""
    total_words = 2 * total_frames
    rows = total_words // STRIDE - 2
    if rows < 1:
        return None
    return ColumnLayout(total_words=total_words, rows=rows)


@dataclass(frozen=True)
class OurSyndromes:
    """Our 16 syndromes per column at alignment 0, and the edge rows for shifting.

    ``leadin`` is words ``[0, 2*STRIDE)``: the row before the window and its first
    row. ``leadout`` is words ``[rows*STRIDE, (rows+2)*STRIDE)``: its last row and
    the row after it.
    """

    syn: Words
    leadin: Words
    leadout: Words
    rows: int


class SyndromeAccumulator:
    """Streams a disc's PCM, one chunk at a time, into :class:`OurSyndromes`.

    ``feed`` returns False once the deadline (a ``time.monotonic`` value) has
    passed, and every later call does nothing: the caller stops decoding and
    records the localisation as not determined, bounded out.
    """

    def __init__(self, columns: ColumnLayout, deadline: float) -> None:
        self._layout = columns
        self._deadline = deadline
        self._syn: Words = np.zeros((MAX_NPAR, STRIDE), dtype=np.uint16)
        self._index: NDArray[np.int32] = np.empty((MAX_NPAR, STRIDE), dtype=np.int32)
        self._leadin: Words = np.zeros(2 * STRIDE, dtype=np.uint16)
        self._leadout: Words = np.zeros(2 * STRIDE, dtype=np.uint16)
        self._pending: Words = np.zeros(0, dtype=np.uint16)
        self._pending_start = 0  # word index of _pending[0]
        self._seen = 0  # words received so far
        self._next_row = 0
        self._odd_byte = b""
        self.stopped = False

    def _capture(self, words: Words, start: int) -> None:
        """Copy whatever part of ``words`` falls in the two edge regions."""
        for target, first in (
            (self._leadin, 0),
            (self._leadout, self._layout.leadout_start),
        ):
            lo = max(start, first)
            hi = min(start + len(words), first + 2 * STRIDE)
            if hi > lo:
                target[lo - first : hi - first] = words[lo - start : hi - start]

    def feed(self, chunk: bytes) -> bool:
        """Fold ``chunk`` (the next bytes of the disc's PCM) into the syndromes."""
        if self.stopped:
            return False
        data = self._odd_byte + chunk if self._odd_byte else chunk
        even = len(data) - len(data) % 2
        self._odd_byte = bytes(data[even:])
        words: Words = np.frombuffer(data, dtype="<u2", count=even // 2).astype(
            np.uint16, copy=False
        )
        start = self._seen
        self._seen += len(words)
        self._capture(words, start)
        if len(self._pending):
            buffer: Words = np.concatenate((self._pending, words))
            buffer_start = self._pending_start
        else:
            buffer, buffer_start = words, start
        rows = self._layout.rows
        while self._next_row < rows:
            row_start = STRIDE * (self._next_row + 1) - buffer_start
            if row_start < 0 or row_start + STRIDE > len(buffer):
                break
            np.add(self._syn, _TABLE_BASE, out=self._index)
            np.take(_TABLE, self._index, out=self._syn)
            np.bitwise_xor(
                self._syn, buffer[row_start : row_start + STRIDE], out=self._syn
            )
            self._next_row += 1
            if (
                self._next_row % _ROWS_PER_CHECK == 0
                and time.monotonic() > self._deadline
            ):
                self.stopped = True
                return False
        keep_from = max(0, STRIDE * (self._next_row + 1) - buffer_start)
        if self._next_row >= rows or keep_from >= len(buffer):
            self._pending = np.zeros(0, dtype=np.uint16)
            self._pending_start = buffer_start + len(buffer)
        else:
            self._pending = buffer[keep_from:].copy()
            self._pending_start = buffer_start + keep_from
        return True

    def finish(self) -> OurSyndromes | None:
        """The result, or ``None`` when the audio stopped short of the window's edges."""
        if self.stopped or self._next_row < self._layout.rows:
            return None
        if self._seen < self._layout.leadout_start + 2 * STRIDE:
            return None
        return OurSyndromes(
            syn=self._syn.copy(),
            leadin=self._leadin.copy(),
            leadout=self._leadout.copy(),
            rows=self._layout.rows,
        )


def syndromes_at(ours: OurSyndromes, offset: int, npar: int) -> Words | None:
    """Our first ``npar`` syndromes for a pressing ``offset`` frames from ours.

    ``None`` outside ``|2 * offset| < STRIDE`` (CTDB's own ±5879 range). A column
    the shift carries past either end of a row is the neighbouring row's column:
    multiply by ``alpha**i`` (one row later) or ``alpha**-i`` (one earlier) and
    swap the word that left the window for the one that entered it.
    """
    shift = 2 * offset
    if not -STRIDE < shift < STRIDE or not 1 <= npar <= MAX_NPAR:
        return None
    syn = ours.syn[:npar]
    powers = _POWERS[:npar]
    last_power = powers * (ours.rows - 1)
    out: Words = np.empty_like(syn)
    if shift >= 0:
        out[:, : STRIDE - shift] = syn[:, shift:]
        if shift:
            first_row = ours.leadin[STRIDE : STRIDE + shift][None, :]
            next_row = ours.leadout[STRIDE : STRIDE + shift][None, :]
            dropped = syn[:, :shift] ^ _mul_alpha(first_row, last_power)
            out[:, STRIDE - shift :] = _mul_alpha(dropped, powers) ^ next_row
    else:
        back = -shift
        out[:, back:] = syn[:, : STRIDE - back]
        last_row = ours.leadout[STRIDE - back : STRIDE][None, :]
        before_row = ours.leadin[STRIDE - back : STRIDE][None, :]
        without_last = syn[:, STRIDE - back :] ^ last_row
        out[:, :back] = _mul_alpha(without_last, -powers) ^ _mul_alpha(
            before_row, last_power
        )
    return out


def column0_by_offset(ours: OurSyndromes, npar: int, reach: int) -> Words:
    """Our column-0 syndromes at every offset in ``-reach..reach`` (one row each).

    What CUETools' ``FindOffset`` compares an entry's ``syndrome`` attribute with.
    Row ``k`` is offset ``k - reach``; ``reach`` must be below ``STRIDE // 2``.
    """
    offsets = np.arange(-reach, reach + 1)
    syn = ours.syn[:npar]
    powers = _POWERS[:npar]
    out: Words = np.empty((npar, len(offsets)), dtype=np.uint16)
    ahead = offsets >= 0
    out[:, ahead] = syn[:, 2 * offsets[ahead]]
    columns = STRIDE + 2 * offsets[~ahead]
    without_last = syn[:, columns] ^ ours.leadout[columns][None, :]
    out[:, ~ahead] = _mul_alpha(without_last, -powers) ^ _mul_alpha(
        ours.leadin[columns][None, :], powers * (ours.rows - 1)
    )
    return out.T.copy()


def record_syndromes(data: bytes, rows: int) -> Words | None:
    """A fetched parity record as ``rows x STRIDE`` words; ``None`` if it is not that size."""
    if rows < 1 or len(data) != rows * STRIDE * 2:
        return None
    record: Words = (
        np.frombuffer(data, dtype="<u2").astype(np.uint16).reshape(rows, STRIDE)
    )
    return record


def chien_powers_fast(locator: Sequence[int], length: int) -> list[int]:
    """:func:`rs_decode.chien_powers`, evaluated at every power at once."""
    if not locator or length <= 0:
        return []
    powers = np.arange(min(length, ORDER), dtype=np.int64)
    total: Words = np.full(len(powers), locator[0] & 0xFFFF, dtype=np.uint16)
    for degree, coefficient in enumerate(list(locator)[1:], start=1):
        if 0 < coefficient <= 0xFFFF:
            total ^= _EXP[(LOG[coefficient] - powers * degree) % ORDER]
    return [int(p) for p in np.flatnonzero(total == 0)]
