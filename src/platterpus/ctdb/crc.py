# SPDX-License-Identifier: GPL-3.0-only
"""The CTDB audio CRC.

✅ HARDWARE-VALIDATION GATE PASSED (PLANNING.md KDD-16) ✅
The *algorithm* below is reconstructed bit-for-bit from the LGPL
`CUETools.AccurateRip` / `CUETools.Codecs` source (see
`docs/ctdb-crc-algorithm.md`) AND confirmed end-to-end on real hardware: a
`platterpus --ctdb-calibrate` run on a known in-database disc reproduced a
stored CTDB CRC at aligned **offset 0** (see ``CONFIRMED_VECTOR`` below), so
``CRC_VALIDATED`` is now **True** and a ``MATCH`` is trustworthy (2026-07-07).

What we established from the CueTools source (and reproduced in Python):
  * the checksum IS the **standard IEEE/zlib CRC-32** (poly ``0x04c11db7``,
    reflected, init/xor ``0xffffffff``) — exactly :func:`zlib.crc32`; and
  * ``CTDBCRC(offset)`` is that CRC over the whole-disc little-endian 16-bit
    stereo PCM with a **fixed front trim of ``stride/2`` frames** and a
    **length-dependent back trim of ``laststride/2`` frames**, where
    ``stride = 10·588·2`` 16-bit words and
    ``laststride = stride + (2·total_frames mod stride)`` — an offset guard band
    so the value survives a small pressing/drive offset. An ``offset`` slides
    that constant-length window (``front += offset``; ``back -= offset``).

The earlier placeholder was a plain offset-0 CRC with **no trim**, which is why
a genuinely-good, in-database disc reported NO MATCH — the trim, not the CRC
polynomial, was wrong. This module is the single seam; :mod:`platterpus.ctdb.
calibrate` sweeps the ``offset`` axis to confirm the algorithm on a real disc.
"""

from __future__ import annotations

import zlib
from collections.abc import Iterable

# Bytes per stereo 16-bit sample frame.
BYTES_PER_SAMPLE_FRAME: int = 4

# CUETools' CTDB parity stride, in 16-bit words: `CUEToolsDB.Init` constructs
# `new CDRepairEncode(ar, 10 * 588 * 2)`. Frame trims are half of a word count
# (2 words = 1 stereo frame), so `stride/2` and `laststride/2` are FRAME counts.
CTDB_STRIDE_WORDS: int = 10 * 588 * 2  # = 11760

# CTDB's offset search range — the window CueTools' `CDRepair.FindOffset` sweeps:
# `for (offset = 1 - stride/2; offset < stride/2; offset++)` (CDRepair.cs). In
# stereo frames that is ±(stride/2 − 1) = ±5879, DELIBERATELY WIDER than
# AccurateRip's ±2939 (`5*588 − 1`), because real pressing offsets routinely
# exceed the AR window. Using the narrower AR range here was the bug behind two
# failed hardware calibrations (KDD-16): a pressing aligned at an offset in
# (2939, 5879] was never reached — the CRC/trim/combine were already correct
# (verified bit-for-bit against the CueTools C# source). The fixed stride/2-frame
# front trim exists precisely to give this range room.
CTDB_OFFSET_RANGE: int = CTDB_STRIDE_WORDS // 2 - 1  # = 5879 frames

# Hardware-confirmed CTDB-CRC vector (KDD-16) — the evidence that flipped
# CRC_VALIDATED to True. Reproduce any time with `platterpus --ctdb-calibrate`
# on the same disc; the test suite pins the trim (`ctdb_trims`) against it so a
# future refactor of the trim/offset math can't silently regress.
#   Disc:  The Police — Every Breath You Take: The Classics (14 tracks)
#   Drive: PIONEER BD-RW BDR-209D (read offset +667); Platterpus build f50258c
#   Whole-disc PCM: 631_998_864 bytes = 157_999_716 stereo frames
#   ctdb_trims(157_999_716) == (front 5880, back 9996)
#   offset 0 → CTDB CRC 0x5DA89FCD, matched an in-database entry (confidence 1)
# Tuple layout: (total_frames, front_trim, back_trim, offset, crc).
CONFIRMED_VECTOR: tuple[int, int, int, int, int] = (
    157_999_716,
    5880,
    9996,
    0,
    0x5DA89FCD,
)

# True: the algorithm has been confirmed bit-exact on real hardware (see the
# CONFIRMED_VECTOR above and docs/ctdb-crc-algorithm.md "Confirming on hardware").
CRC_VALIDATED: bool = True


def ctdb_trims(total_frames: int) -> tuple[int, int]:
    """Return the ``(front, back)`` frame trims for a whole disc's CTDB CRC.

    ``front`` is fixed at ``stride/2`` (5880 frames = 10 sectors) for every disc;
    ``back`` is ``laststride/2`` where ``laststride = stride + (2·total_frames
    mod stride)`` (from ``CDRepair.cs``). Pure; never raises (a tiny/zero disc
    just yields trims that :func:`ctdb_crc` will reject as out-of-range).
    """
    n_words = total_frames * 2
    laststride = CTDB_STRIDE_WORDS + (n_words % CTDB_STRIDE_WORDS)
    return CTDB_STRIDE_WORDS // 2, laststride // 2


def ctdb_crc(pcm: bytes, offset: int = 0) -> int | None:
    """Bit-exact CUETools ``CTDBCRC(offset)`` of whole-disc LE-16 stereo PCM.

    ``offset`` slides a constant-length window over the guard band: ``front +=
    offset``, ``back -= offset``. ``offset=0`` is the value stored in the
    database and the value a rip with the correct read offset must reproduce.
    Returns a 32-bit int, or ``None`` when the offset pushes the window outside
    the audio (the caller — a sweep — simply skips it). Never raises.
    """
    total_frames = len(pcm) // BYTES_PER_SAMPLE_FRAME
    front, back = ctdb_trims(total_frames)
    start = (front + offset) * BYTES_PER_SAMPLE_FRAME
    end = len(pcm) - (back - offset) * BYTES_PER_SAMPLE_FRAME
    if start < 0 or end > len(pcm) or end <= start:
        return None
    return zlib.crc32(pcm[start:end]) & 0xFFFFFFFF


def ctdb_crc_offset0(pcm: bytes) -> int | None:
    """The offset-0 CTDB CRC of the whole-disc PCM (``ctdb_crc(pcm, 0)``).

    The value a correctly-offset rip must match in the database. ``None`` only
    for a degenerate disc too short to hold the guard band.
    """
    return ctdb_crc(pcm, 0)


def ctdb_crc_offset0_streaming(
    chunks: Iterable[bytes], total_frames: int
) -> int | None:
    """Offset-0 CTDB CRC folded over `chunks` one track at a time.

    Identical result to ``ctdb_crc(b"".join(chunks), 0)`` for a whole disc whose
    frame count is `total_frames`, but it never holds more than one track's PCM
    resident (the caller passes a generator that decodes one FLAC at a time), so
    a whole album is CRC'd with a single track's memory footprint instead of
    buffering the disc plus a ``b"".join`` copy (which spiked ~1.5 GB on the
    verify thread, #39).

    `total_frames` is required up front (from the disc TOC) because the back trim
    depends on the whole-disc length — a streamed offset-0 CRC skips the front
    ``stride/2`` frames and stops ``laststride/2`` frames before the end, folding
    only the in-window slice of each chunk. Returns ``None`` for a degenerate
    (too-short) disc. Never raises.
    """
    front, back = ctdb_trims(total_frames)
    start = front * BYTES_PER_SAMPLE_FRAME
    end = total_frames * BYTES_PER_SAMPLE_FRAME - back * BYTES_PER_SAMPLE_FRAME
    if end <= start:
        return None
    crc = 0
    pos = 0
    for chunk in chunks:
        chunk_start = pos
        chunk_end = pos + len(chunk)
        pos = chunk_end
        lo = max(chunk_start, start)
        hi = min(chunk_end, end)
        if hi > lo:
            crc = zlib.crc32(chunk[lo - chunk_start : hi - chunk_start], crc)
    return crc & 0xFFFFFFFF
