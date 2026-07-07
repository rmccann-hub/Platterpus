# SPDX-License-Identifier: GPL-3.0-only
"""The CTDB audio CRC.

⚠️⚠️ HARDWARE-VALIDATION GATE (PLANNING.md KDD-16) ⚠️⚠️
The *algorithm* below is now reconstructed bit-for-bit from the LGPL
`CUETools.AccurateRip` / `CUETools.Codecs` source (see
`docs/ctdb-crc-algorithm.md`), but ``CRC_VALIDATED`` stays **False** until a
real, in-database disc confirms it end-to-end on hardware (the maintainer's
`--ctdb-calibrate` run) — only then does a ``MATCH`` become trustworthy.

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

# CTDB's offset tolerance: 5 CD frames of 588 samples, minus one.
CTDB_OFFSET_RANGE: int = 5 * 588 - 1  # = 2939

# Bytes per stereo 16-bit sample frame.
BYTES_PER_SAMPLE_FRAME: int = 4

# CUETools' CTDB parity stride, in 16-bit words: `CUEToolsDB.Init` constructs
# `new CDRepairEncode(ar, 10 * 588 * 2)`. Frame trims are half of a word count
# (2 words = 1 stereo frame), so `stride/2` and `laststride/2` are FRAME counts.
CTDB_STRIDE_WORDS: int = 10 * 588 * 2  # = 11760

# Set True only once the algorithm has been confirmed bit-exact on hardware.
CRC_VALIDATED: bool = False


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
