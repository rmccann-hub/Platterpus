# SPDX-License-Identifier: GPL-3.0-only
"""Apply a repair plan to PCM, and prove the result against the entry (TASKS R43).

Pure: bytes in, bytes or a reason out, never an exception (a property test holds
:func:`apply_fixes`). The file work is ``ctdb/repair.py``'s; this module is the
arithmetic it must not get wrong, kept where a test can reach every branch.

Three steps, in the order the repair calls them:

1. :func:`unchanged_reason` — the track's audio must be the audio the
   localisation measured: same length, same CRC-32
   (``CtdbLocalisation.track_crc32s``). The corrections were located in THOSE
   bytes; a file re-ripped, retagged-and-re-encoded wrongly, or edited since is
   refused rather than "repaired" at positions that no longer mean anything.
2. :func:`apply_fixes` — XOR each word. The words are 16-bit little-endian
   samples, so word ``w`` is bytes ``2w`` and ``2w + 1``.
3. :func:`prove` — over the WHOLE disc as it will be after the repair (the
   rewritten track decoded back from its new file, every other track decoded
   from its own), the entry's whole-disc CRC and each rewritten track's CRC at
   the entry's offset must come out exactly. This is the CRC the localisation
   predicted algebraically, now measured from the artifact.
"""

from __future__ import annotations

import zlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from platterpus.ctdb.repair_types import RepairPlan, SampleFix
from platterpus.ctdb.sweep import sweep


def unchanged_reason(pcm: bytes, track: int, plan: RepairPlan) -> str | None:
    """Why ``pcm`` is not track ``track``'s audio as localised, or ``None`` if it is."""
    if not 1 <= track <= len(plan.track_frames):
        return f"track {track} is not on this disc"
    want_bytes = 4 * plan.track_frames[track - 1]
    if len(pcm) != want_bytes:
        return (
            f"track {track} decodes to {len(pcm):,} bytes where the localisation "
            f"measured {want_bytes:,}; the file has changed since, so nothing is "
            "repaired"
        )
    crc = zlib.crc32(pcm) & 0xFFFFFFFF
    if crc != plan.track_crc32s[track - 1]:
        return (
            f"track {track}'s audio CRC is now {crc:08X} where the localisation "
            f"measured {plan.track_crc32s[track - 1]:08X}; the file has changed "
            "since, so nothing is repaired"
        )
    return None


def apply_fixes(pcm: bytes, fixes: Sequence[SampleFix]) -> bytes | str:
    """``pcm`` with each fix's word XORed by its value, or why it cannot be. Never raises."""
    data = bytearray(pcm) if isinstance(pcm, bytes | bytearray) else None
    if data is None or len(data) % 4:
        return "the track's audio is not whole stereo frames"
    for fix in fixes:
        word = fix.track_word if isinstance(fix, SampleFix) else -1
        value = fix.value if isinstance(fix, SampleFix) else 0
        if not isinstance(word, int) or not 0 <= 2 * word <= len(data) - 2:
            return f"a correction (word {word}) lies outside the track's audio"
        if not isinstance(value, int) or not 0 < value <= 0xFFFF:
            return f"a correction's value {value!r} is not a non-zero 16-bit number"
        current = int.from_bytes(data[2 * word : 2 * word + 2], "little")
        data[2 * word : 2 * word + 2] = (current ^ value).to_bytes(2, "little")
    return bytes(data)


@dataclass(frozen=True)
class Proof:
    """What the whole repaired disc measured at the entry's offset."""

    disc_crc: int
    track_crcs: dict[int, int]  # track number -> its CTDB CRC at the offset


def prove(plan: RepairPlan, chunks: Iterable[bytes]) -> Proof | str:
    """Measure the repaired disc; a :class:`Proof` only if every CRC closes.

    ``chunks`` is every track's PCM after the repair, in disc order, one track
    at a time (a generator decoding on demand keeps one track resident, as the
    verify does). Any decoder error the generator raises reaches the caller.
    """
    spread = abs(plan.offset)
    measured = sweep(
        chunks,
        plan.track_starts,
        plan.total_frames,
        disc_range=spread,
        track_range=spread,
    )
    if measured.bytes_seen != 4 * plan.total_frames:
        return (
            f"the repaired disc decoded to {measured.bytes_seen:,} bytes where it "
            f"holds {4 * plan.total_frames:,}"
        )
    disc = measured.disc.get(plan.offset)
    if disc != plan.expected_disc_crc:
        shown = "none" if disc is None else f"{disc:08X}"
        return (
            f"the repaired disc's CTDB CRC at offset {plan.offset:+d} is {shown}, "
            f"not the entry's {plan.expected_disc_crc:08X}; nothing is replaced"
        )
    tracks: dict[int, int] = {}
    for track in plan.tracks:
        got = measured.tracks[track - 1].get(plan.offset)
        want = plan.expected_track_crcs[track - 1]
        if got != want:
            shown = "none" if got is None else f"{got:08X}"
            return (
                f"repaired track {track}'s CTDB CRC at offset {plan.offset:+d} is "
                f"{shown}, not the entry's {want:08X}; nothing is replaced"
            )
        tracks[track] = got
    return Proof(disc_crc=disc, track_crcs=tracks)
