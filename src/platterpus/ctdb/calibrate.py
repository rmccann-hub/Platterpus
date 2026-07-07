# SPDX-License-Identifier: GPL-3.0-only
"""Pin the CTDB audio-CRC algorithm against a real, in-database disc (KDD-16).

The algorithm itself now lives in :mod:`platterpus.ctdb.crc` (reconstructed from
the CueTools LGPL source): ``CTDBCRC(offset)`` is a standard zlib CRC-32 over the
whole-disc PCM with a fixed front trim and a length-dependent back trim, and an
``offset`` slides that window across the ±5879-frame guard band. The one thing
only a real disc can settle is *which* offset (ideally 0, if the rip's read
offset matches the pressing) reproduces a database CRC — so this module sweeps
the whole guard band and reports every offset whose CTDB CRC matches a DB entry.

A naive sweep (re-CRC the ~600 MB disc at each of ~11 759 offsets in the ±5879
band) would take tens of minutes. Instead we compute a couple of big base CRCs
once and derive every offset's CRC with the standard zlib ``crc32_combine``
operator (the same GF(2) "append N zero bytes" trick CueTools' ``Crc32.Combine``
uses). The GF(2) matrix work depends only on byte-*lengths*, not on the disc, and
those lengths are arithmetic across the sweep — so we build each operator ONCE
and apply a cheap matrix-multiply per offset (a full sweep is ~0.3 s, vs ~40 s if
each offset rebuilt the operators — a difference that used to look like a CI hang
under coverage and made the real ``--ctdb-calibrate`` wait).

Everything here is pure (PCM in, matches out) so it's unit-tested without a disc
(the algebra is checked against the naive per-offset CRC); the disc only supplies
the PCM + the expected CRCs when run for real (``scripts/ctdb_verify.py
--calibrate`` / ``platterpus --ctdb-calibrate``). No audio is ever committed
(Rule #8).
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass

from platterpus.ctdb.crc import (
    BYTES_PER_SAMPLE_FRAME,
    CTDB_OFFSET_RANGE,
    ctdb_crc,
    ctdb_trims,
)

_GF2_DIM: int = 32  # CRC-32 register width


@dataclass(frozen=True)
class OffsetMatch:
    """One pressing offset (in samples) whose CTDB CRC matched a DB entry."""

    offset: int
    crc: int


# --- zlib crc32_combine (GF(2) "append |b| zero bytes" operator) ------------


def _gf2_matrix_times(mat: list[int], vec: int) -> int:
    total = 0
    i = 0
    while vec:
        if vec & 1:
            total ^= mat[i]
        vec >>= 1
        i += 1
    return total


def _gf2_matrix_square(square: list[int], mat: list[int]) -> None:
    for n in range(_GF2_DIM):
        square[n] = _gf2_matrix_times(mat, mat[n])


def _gf2_matrix_compose(a: list[int], b: list[int]) -> list[int]:
    """The matrix for "apply ``b`` then ``a``": ``(a∘b)[n] = a(b[n])``, so
    ``_gf2_matrix_times(a∘b, v) == _gf2_matrix_times(a, _gf2_matrix_times(b, v))``.
    """
    return [_gf2_matrix_times(a, b[n]) for n in range(_GF2_DIM)]


def _gf2_combine_operator(len2: int) -> list[int]:
    """The single GF(2) operator matrix equivalent to ``crc32_combine(·, 0, len2)``.

    ``crc32_combine`` applies a sequence of even/odd square matrices to the input
    register; that whole sequence composes into one 32×32 matrix that depends
    ONLY on ``len2``. Building it once (``O(log len2)`` matrix squarings) and then
    applying it with a single :func:`_gf2_matrix_times` is what lets a sweep that
    combines the *same* ``len2`` thousands of times (the offset scan) pay the
    log-cost once instead of per offset. For ``len2 <= 0`` this is the identity.
    """
    op = [1 << n for n in range(_GF2_DIM)]  # identity: matrix_times(op, v) == v
    if len2 <= 0:
        return op
    even = [0] * _GF2_DIM
    odd = [0] * _GF2_DIM
    odd[0] = 0xEDB88320  # the CRC-32 polynomial (reflected)
    row = 1
    for n in range(1, _GF2_DIM):
        odd[n] = row
        row <<= 1
    _gf2_matrix_square(even, odd)
    _gf2_matrix_square(odd, even)
    while True:
        _gf2_matrix_square(even, odd)
        if len2 & 1:
            op = _gf2_matrix_compose(even, op)
        len2 >>= 1
        if len2 == 0:
            break
        _gf2_matrix_square(odd, even)
        if len2 & 1:
            op = _gf2_matrix_compose(odd, op)
        len2 >>= 1
        if len2 == 0:
            break
    return op


def crc32_combine(crc1: int, crc2: int, len2: int) -> int:
    """Standard zlib ``crc32_combine``: the CRC of ``A ‖ B`` given ``crc1`` =
    CRC(A), ``crc2`` = CRC(B), and ``len2`` = len(B) in bytes. Bit-identical to
    CueTools' ``Crc32.Combine`` and to zlib's C implementation."""
    if len2 <= 0:
        return crc1
    return _gf2_matrix_times(_gf2_combine_operator(len2), crc1) ^ crc2


def _shift_crc(crc: int, nbytes: int) -> int:
    """CRC of ``data ‖ (nbytes zero bytes)`` given CRC(data) — the zeros operator."""
    return crc32_combine(crc, 0, nbytes)


def ctdb_crc_offsets(pcm: bytes, offsets: range | None = None) -> dict[int, int]:
    """Map each `offset` in the guard band to its ``CTDBCRC(offset)``.

    Computes one big base CRC and splices per-offset front/back extensions with
    ``crc32_combine`` — C-speed, and bit-identical to calling
    :func:`~platterpus.ctdb.crc.ctdb_crc` per offset (asserted in tests). Offsets
    whose window falls outside the audio are skipped. Pure; never raises.
    """
    if offsets is None:
        offsets = range(-CTDB_OFFSET_RANGE, CTDB_OFFSET_RANGE + 1)
    total_frames = len(pcm) // BYTES_PER_SAMPLE_FRAME
    front, back = ctdb_trims(total_frames)
    fpb = BYTES_PER_SAMPLE_FRAME
    n = len(pcm)

    starts: dict[int, int] = {}
    ends: dict[int, int] = {}
    for oi in offsets:
        a = (front + oi) * fpb
        b = n - (back - oi) * fpb
        if a < 0 or b > n or b <= a:
            continue
        starts[oi] = a
        ends[oi] = b
    if not starts:
        return {}

    b_min = min(ends.values())
    base = zlib.crc32(pcm[:b_min])  # one big pass over the common prefix

    # The per-offset prefix lengths (the ``a`` values, and the ``b`` values) are
    # ARITHMETIC — consecutive offsets differ by exactly one sample-frame
    # (``fpb`` bytes) — so ``_shift_crc(0xFFFFFFFF, L)`` for each length is just the
    # previous one shifted by one more frame. Build the one-frame shift operator
    # ONCE and walk the lengths in order, applying a single cheap matrix-multiply
    # per step, instead of a full ``O(log L)`` combine per length. A non-``fpb``
    # gap (only at the range extremes) falls back to a full shift. Without this
    # the ~2 × 11 759 full combines dominate (tens of seconds — a coverage-time
    # "hang", and a real ``--ctdb-calibrate`` that made the user wait).
    fpb_op = _gf2_combine_operator(fpb)

    def _shift_ff_map(lengths: list[int]) -> dict[int, int]:
        """``{L: _shift_crc(0xFFFFFFFF, L)}`` computed incrementally over sorted L."""
        result: dict[int, int] = {}
        prev_len: int | None = None
        prev_val = 0
        for length in lengths:
            if prev_len is not None and length == prev_len + fpb:
                val = _gf2_matrix_times(fpb_op, prev_val)
            else:
                val = _shift_crc(0xFFFFFFFF, length)
            result[length] = val
            prev_len, prev_val = length, val
        return result

    a_lengths = sorted(set(starts.values()))
    b_lengths = sorted(set(ends.values()))
    shift_a = _shift_ff_map(a_lengths)
    shift_b = _shift_ff_map(b_lengths)
    raw_a = {
        a: (0xFFFFFFFF ^ zlib.crc32(pcm[:a]) ^ shift_a[a]) & 0xFFFFFFFF
        for a in a_lengths
    }
    raw_b = {
        b: (0xFFFFFFFF ^ zlib.crc32(pcm[b_min:b], base) ^ shift_b[b]) & 0xFFFFFFFF
        for b in b_lengths
    }

    # The window length ``b - a`` is CONSTANT across offsets (``a`` and ``b`` both
    # shift by ``+oi``, so their difference is offset-independent), so the GF(2)
    # combine operator is identical for every offset — build it ONCE and apply a
    # single cheap matrix-multiply per offset instead of a full ``crc32_combine``.
    # Keyed by length for safety, but in practice there is a single entry.
    op_cache: dict[int, list[int]] = {}
    out: dict[int, int] = {}
    for oi, a in starts.items():
        b = ends[oi]
        len2 = b - a
        op = op_cache.get(len2)
        if op is None:
            op = _gf2_combine_operator(len2)
            op_cache[len2] = op
        out[oi] = 0xFFFFFFFF ^ (_gf2_matrix_times(op, 0xFFFFFFFF ^ raw_a[a]) ^ raw_b[b])
    return out


def calibrate(pcm: bytes, expected_crcs: set[int]) -> list[OffsetMatch]:
    """Return every guard-band offset whose CTDB CRC reproduces an expected CRC.

    `expected_crcs` are the CTDB lookup's entry CRCs for this disc. A non-empty
    result pins the algorithm on a real, in-database disc: a match at ``offset 0``
    means the rip's read offset aligns with that pressing; a match at ``±k`` means
    the rip differs from the pressing by ``k`` samples (still a valid verify).
    Empty means no offset matched. Pure and total; never raises.
    """
    if not expected_crcs:
        return []
    matches = [
        OffsetMatch(offset=oi, crc=crc)
        for oi, crc in sorted(ctdb_crc_offsets(pcm).items())
        if crc in expected_crcs
    ]
    return matches


def crc_at_offset(pcm: bytes, offset: int) -> int | None:
    """Convenience: the CTDB CRC at a single `offset` (``None`` if out of range).

    Thin wrapper over :func:`~platterpus.ctdb.crc.ctdb_crc`, kept here so the
    diagnostics/report can quote the no-offset (offset-0) value alongside the
    swept matches without importing two modules."""
    return ctdb_crc(pcm, offset)
