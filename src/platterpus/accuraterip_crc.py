# SPDX-License-Identifier: GPL-3.0-only
"""AccurateRip v1 and v2 checksums of one track's PCM, computed by us.

**Why we compute them at all.** Every AccurateRip number Platterpus showed until
2026-11-04 was the ripper's: cyanrip prints ``Accurip v1:``/``v2:`` and the
parser reads them. A CTDB repair (``ctdb/repair.py``) rewrites a track AFTER the
rip, so the ripper's numbers describe the bytes it replaced. The repair needs the
repaired file's checksums, from the repaired file, to set beside AccurateRip's
database: the one witness independent of CTDB, whose parity drove the repair.

**The algorithm** (public, and the same in every implementation: AccurateRip's
own description, the hydrogenaudio thread Leo Bogert's ``accuraterip-checksum.c``
cites, and cyanrip). Read each stereo frame as ONE little-endian 32-bit word
(left sample low, right sample high). Number the frames from 1 (the
"multiplier"). For each frame inside the checked range, form the 64-bit product
``word * multiplier``:

* **v1** is the sum of the products' low 32 bits, modulo 2**32;
* **v2** is v1 plus the sum of the products' high 32 bits, modulo 2**32.

The checked range is every frame, except that the disc's FIRST track skips its
first ``5 * 588 - 1`` frames (the multiplier must reach 2940) and the LAST track
skips its last 2940 (the multiplier may not pass ``frames - 2940``): the guard
AccurateRip keeps for drive offsets. A one-track disc does both.

**Checked against an independent witness**, not against a second copy of this
description: ``tests/test_accuraterip_crc.py`` pins values computed by Leo Bogert
and Andreas Oberritter's C ``compute_checksums`` (GPLv3), compiled
outside the repository and fed the same seeded PCM. Two programs agreeing on the
definition they were both written from would prove nothing (CLAUDE.md, *two
implementations agreeing is not either one being correct*).

numpy, in bounded blocks: a five-minute track is 13 million frames, and one
uint64 array of it is 106 MB. Imported only by callers that the dependency
registry has said numpy is installed for (the repair, like the localisation).
Pure; never raises: input that is not whole frames, or a track number outside
the disc, returns ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

#: Frames AccurateRip leaves out at each end of the disc: five sectors.
AR_GUARD_FRAMES: int = 5 * 588

#: Bytes per stereo 16-bit frame.
_FRAME_BYTES: int = 4

#: Frames per numpy block: 1 Mi frames is 8 MB per uint64 array.
_BLOCK_FRAMES: int = 1 << 20

_LOW32: np.uint64 = np.uint64(0xFFFFFFFF)
_SHIFT32: np.uint64 = np.uint64(32)


@dataclass(frozen=True)
class AccurateRipCrcs:
    """One track's two checksums, as the ripper prints them (``%08X``)."""

    v1: int
    v2: int

    @property
    def v1_hex(self) -> str:
        return f"{self.v1:08X}"

    @property
    def v2_hex(self) -> str:
        return f"{self.v2:08X}"


def checked_range(frames: int, track: int, total_tracks: int) -> tuple[int, int]:
    """The multipliers counted, ``(first, last)`` inclusive, 1-based.

    Empty (``first > last``) for a track shorter than its guard band.
    """
    first = AR_GUARD_FRAMES if track == 1 else 1
    last = frames - AR_GUARD_FRAMES if track == total_tracks else frames
    return first, last


def accuraterip_crcs(
    pcm: bytes, track: int, total_tracks: int
) -> AccurateRipCrcs | None:
    """AccurateRip v1 and v2 of one track's whole PCM; ``None`` for input that is not one.

    ``pcm`` is the track's little-endian 16-bit stereo audio, every frame of the
    file (the guard band is applied here, from ``track`` and ``total_tracks``).
    """
    if (
        not isinstance(pcm, bytes | bytearray | memoryview)
        or not 1 <= track <= total_tracks
        or len(pcm) % _FRAME_BYTES
    ):
        return None
    frames = len(pcm) // _FRAME_BYTES
    if frames == 0:
        return None
    first, last = checked_range(frames, track, total_tracks)
    words = np.frombuffer(pcm, dtype="<u4")
    low_sum = 0
    high_sum = 0
    # Multiplier m covers word m - 1, so the counted words are [first-1, last).
    start = max(first, 1) - 1
    stop = min(last, frames)
    for block in range(start, stop, _BLOCK_FRAMES):
        end = min(block + _BLOCK_FRAMES, stop)
        multipliers = np.arange(block + 1, end + 1, dtype=np.uint64)
        products = words[block:end].astype(np.uint64) * multipliers
        # Each low/high half is below 2**32 and a block holds 2**20 of them, so a
        # uint64 sum cannot overflow; the Python ints carry it across blocks.
        low_sum += int(np.sum(products & _LOW32, dtype=np.uint64))
        high_sum += int(np.sum(products >> _SHIFT32, dtype=np.uint64))
    v1 = low_sum & 0xFFFFFFFF
    return AccurateRipCrcs(v1=v1, v2=(v1 + high_sum) & 0xFFFFFFFF)
