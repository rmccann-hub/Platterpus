# SPDX-License-Identifier: GPL-3.0-only
"""The CTDB audio CRC.

⚠️⚠️ HARDWARE-VALIDATION GATE (PLANNING.md KDD-16) ⚠️⚠️
This is the one part of the CTDB feature that CANNOT be confirmed correct in a
cloud environment. CTDB's per-disc CRC is computed by `CUETools.AccurateRip`'s
`CTDBCRC(offset)` over the decoded audio, tolerant of a pressing/drive offset
of ±(5·588−1) = ±2939 samples. The *bit-exact* polynomial, initial value,
reflection, and the efficient per-offset sliding computation must be read from
the **LGPL** `CUETools.AccurateRip`/`CUETools.Parity` source and validated
against a real CD that is in CTDB — see `docs/test-plan.md`.

Until then this module implements a **documented best-effort** standard CRC-32
(IEEE / zlib) over the whole-disc PCM at offset 0. Consequences:
  * The transformation is deterministic and unit-tested (it does what we say).
  * If CTDB uses a different CRC variant or offset, this will report
    NO MATCH for a genuinely-good disc — i.e. it fails *safe* (it never
    fabricates a "verified" result). Correcting it is the hardware task.

Keep this function the single seam to change when the algorithm is confirmed.
"""

from __future__ import annotations

import zlib
from collections.abc import Iterable

# CTDB's offset tolerance: 5 CD frames of 588 samples, minus one.
CTDB_OFFSET_RANGE: int = 5 * 588 - 1  # = 2939

# Bytes per stereo 16-bit sample frame (used to convert a sample offset to a
# byte offset when/if the offset sweep is implemented).
BYTES_PER_SAMPLE_FRAME: int = 4

# Set True only once the algorithm has been confirmed bit-exact on hardware.
CRC_VALIDATED: bool = False


def ctdb_crc_offset0(pcm: bytes) -> int:
    """Best-effort CTDB CRC of the whole-disc PCM at offset 0.

    `pcm` is the concatenation of every track decoded to little-endian signed
    16-bit stereo (see `decode.decode_flac_to_pcm`). Returns a 32-bit int.

    ⚠️ UNVERIFIED variant — see the module docstring. This is a standard
    zlib CRC-32; the real CTDB variant is confirmed on hardware (KDD-16).
    """
    return zlib.crc32(pcm) & 0xFFFFFFFF


def ctdb_crc_offset0_streaming(chunks: Iterable[bytes]) -> int:
    """Whole-disc offset-0 CRC folded over `chunks` one at a time.

    Identical result to ``ctdb_crc_offset0(b"".join(chunks))`` — zlib CRC-32 is
    linear, so ``crc32(a + b) == crc32(b, crc32(a))`` — but it never holds more
    than one chunk in memory. The caller passes a generator that decodes one
    track at a time, so a whole album (~750 MB of PCM) is CRC'd with a single
    track's footprint instead of buffering the disc AND the ``b"".join`` copy
    (which spiked ~1.5 GB on the verify thread, #39).

    ⚠️ Streaming is valid ONLY for this offset-0 zlib variant. The real,
    hardware-validated CTDB CRC sweeps a ±2939-sample offset window (module
    docstring / KDD-16) and needs the whole-disc PCM; when that lands it must
    change THIS seam and revisit whether a streaming form is still possible.
    """
    crc = 0
    for chunk in chunks:
        crc = zlib.crc32(chunk, crc)
    return crc & 0xFFFFFFFF
