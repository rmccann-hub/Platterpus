# SPDX-License-Identifier: GPL-3.0-only
"""Tests for the CTDB-CRC calibration sweep (pure; no disc needed).

The algorithm lives in ``ctdb.crc``; calibration sweeps the ±2939-sample offset
guard band to find which offset reproduces a database CRC. We synthesise PCM,
compute the CRC at a known offset ourselves, and assert the (fast, combine-based)
sweep recovers exactly that offset — and that the fast sweep matches the naive
per-offset CRC.
"""

from __future__ import annotations

import zlib

from platterpus.ctdb.calibrate import (
    OffsetMatch,
    calibrate,
    crc32_combine,
    crc_at_offset,
    ctdb_crc_offsets,
)
from platterpus.ctdb.crc import BYTES_PER_SAMPLE_FRAME, ctdb_crc, ctdb_trims

# A deterministic PCM blob big enough to hold the guard band (front 5880 + back
# ~8232 frames) with audio left over at every offset in the ±2939 window.
_FRAMES = 20_000
_PCM = bytes((i * 7 + 13) & 0xFF for i in range(_FRAMES * BYTES_PER_SAMPLE_FRAME))


def test_crc32_combine_matches_zlib_on_concatenation() -> None:
    # The GF(2) "append |b| zero bytes" operator must equal a real concatenation.
    a = b"hello world" * 7
    b = b"the quick brown fox" * 11
    assert crc32_combine(zlib.crc32(a), zlib.crc32(b), len(b)) == zlib.crc32(a + b)
    # A zero-length tail is a no-op.
    assert crc32_combine(zlib.crc32(a), zlib.crc32(b""), 0) == zlib.crc32(a)


def test_ctdb_crc_offsets_matches_naive_per_offset() -> None:
    # The fast combine-based sweep is bit-identical to calling ctdb_crc per offset.
    sweep = ctdb_crc_offsets(_PCM, range(-7, 8))
    for oi in range(-7, 8):
        assert sweep[oi] == ctdb_crc(_PCM, oi)


def test_ctdb_trims_here_leave_audio() -> None:
    # Guard against a too-short fixture: the window must be non-empty at offset 0.
    front, back = ctdb_trims(_FRAMES)
    assert (front + back) < _FRAMES


def test_calibrate_finds_the_offset_that_matches() -> None:
    # Plant an expected CRC = the disc's CRC at a known offset; the sweep finds it.
    target = 3
    expected = ctdb_crc(_PCM, target)
    assert expected is not None
    assert OffsetMatch(offset=target, crc=expected) in calibrate(_PCM, {expected})


def test_calibrate_finds_offset_zero() -> None:
    # The common case: a correctly-offset rip matches at offset 0.
    expected = ctdb_crc(_PCM, 0)
    assert expected is not None
    assert any(m.offset == 0 and m.crc == expected for m in calibrate(_PCM, {expected}))


def test_calibrate_empty_when_nothing_matches() -> None:
    # A CRC no offset can produce → honest negative.
    assert calibrate(_PCM, {0xDEADBEEF}) == []


def test_calibrate_empty_expected_is_empty() -> None:
    assert calibrate(_PCM, set()) == []


def test_crc_at_offset_wrapper() -> None:
    assert crc_at_offset(_PCM, 2) == ctdb_crc(_PCM, 2)
    # An absurd offset pushes the window outside the audio → None (skipped).
    assert crc_at_offset(_PCM, 10**9) is None
