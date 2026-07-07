# SPDX-License-Identifier: GPL-3.0-only
"""Pin the CTDB audio-CRC algorithm against a real, in-database disc (KDD-16).

The algorithm itself now lives in :mod:`platterpus.ctdb.crc` (reconstructed from
the CueTools LGPL source): ``CTDBCRC(offset)`` is a standard zlib CRC-32 over the
whole-disc PCM with a fixed front trim and a length-dependent back trim, and an
``offset`` slides that window across the ±2939-sample guard band. The one thing
only a real disc can settle is *which* offset (ideally 0, if the rip's read
offset matches the pressing) reproduces a database CRC — so this module sweeps
the whole guard band and reports every offset whose CTDB CRC matches a DB entry.

A naive sweep (re-CRC the ~600 MB disc at each of 5 879 offsets) would take tens
of minutes. Instead we compute the offset-0 CRC once and derive every other
offset's CRC in microseconds with the standard zlib ``crc32_combine`` operator
(the same GF(2) "append N zero bytes" trick CueTools' ``Crc32.Combine`` uses) —
so the full sweep is a handful of big CRC passes plus cheap algebra.

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


def crc32_combine(crc1: int, crc2: int, len2: int) -> int:
    """Standard zlib ``crc32_combine``: the CRC of ``A ‖ B`` given ``crc1`` =
    CRC(A), ``crc2`` = CRC(B), and ``len2`` = len(B) in bytes. Bit-identical to
    CueTools' ``Crc32.Combine`` and to zlib's C implementation."""
    if len2 <= 0:
        return crc1
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
            crc1 = _gf2_matrix_times(even, crc1)
        len2 >>= 1
        if len2 == 0:
            break
        _gf2_matrix_square(odd, even)
        if len2 & 1:
            crc1 = _gf2_matrix_times(odd, crc1)
        len2 >>= 1
        if len2 == 0:
            break
    return crc1 ^ crc2


def _shift_crc(crc: int, nbytes: int) -> int:
    """CRC of ``data ‖ (nbytes zero bytes)`` given CRC(data) — the zeros operator."""
    return crc32_combine(crc, 0, nbytes)


def _raw_prefix(std_crc: int, nbytes: int) -> int:
    """The init-0 / no-xorout running CRC register for a `nbytes`-long prefix,
    given its standard ``zlib.crc32`` value. Lets us splice prefixes/suffixes the
    way CUETools' ``CTDBCRC`` does with its per-track running registers."""
    return (0xFFFFFFFF ^ std_crc ^ _shift_crc(0xFFFFFFFF, nbytes)) & 0xFFFFFFFF


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
    raw_a = {a: _raw_prefix(zlib.crc32(pcm[:a]), a) for a in set(starts.values())}
    raw_b = {
        b: _raw_prefix(zlib.crc32(pcm[b_min:b], base), b)
        for b in sorted(set(ends.values()))
    }
    out: dict[int, int] = {}
    for oi, a in starts.items():
        b = ends[oi]
        out[oi] = 0xFFFFFFFF ^ crc32_combine(0xFFFFFFFF ^ raw_a[a], raw_b[b], b - a)
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
