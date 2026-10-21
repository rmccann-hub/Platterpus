# SPDX-License-Identifier: GPL-3.0-only
"""The one-pass CTDB CRC engine (`ctdb/sweep.py`), held against the naive CRC.

Every CRC the engine derives with prefix values and the GF(2) "append zeros"
operator must equal ``zlib.crc32`` of the same slice of PCM, computed the slow,
obvious way. Synthetic PCM only (Critical rule #8): the definition of WHICH slice
is checked against measured data in ``tests/test_ctdb_per_track.py``.
"""

from __future__ import annotations

import random
import zlib

from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.ctdb import crc as crc_mod
from platterpus.ctdb.calibrate import ctdb_crc_offsets
from platterpus.ctdb.sweep import (
    DISC_OFFSET_RANGE,
    disc_window,
    sweep,
    sweep_disc,
    track_windows,
)
from platterpus.ctdb.toc import LEAD_IN_SECTORS, SAMPLES_PER_SECTOR, DiscToc

# Four tracks, long enough that the ±5879-frame disc window and the ±2939-frame
# track windows stay inside the disc at every offset.
_FRAMES = (9_000, 13_000, 7_000, 11_000)
_TOTAL = sum(_FRAMES)
_STARTS = [sum(_FRAMES[:i]) for i in range(len(_FRAMES))]
_PCM = random.Random(20261021).randbytes(_TOTAL * 4)


def _chunks(pcm: bytes = _PCM, frames: tuple[int, ...] = _FRAMES) -> list[bytes]:
    """The PCM cut at the track boundaries, as the verify's decoder yields it."""
    out: list[bytes] = []
    position = 0
    for count in frames:
        out.append(pcm[position : position + count * 4])
        position += count * 4
    return out


def _naive(window: tuple[int, int], offset: int, pcm: bytes = _PCM) -> int:
    start, end = window
    return zlib.crc32(pcm[(start + offset) * 4 : (end + offset) * 4]) & 0xFFFFFFFF


def test_the_track_windows_trim_only_the_disc_s_two_ends() -> None:
    """Track 1 loses the front guard band, the last track the back one, and the
    middle tracks are whole: CUETools' `CTDBCRC(iTrack, oi, stride/2, laststride/2)`."""
    front, back = crc_mod.ctdb_trims(_TOTAL)
    assert track_windows(_STARTS, _TOTAL) == (
        (front, _STARTS[1]),
        (_STARTS[1], _STARTS[2]),
        (_STARTS[2], _STARTS[3]),
        (_STARTS[3], _TOTAL - back),
    )
    # A one-track disc gets the whole-disc window, as CUETools' code gives it.
    assert track_windows([0], _TOTAL) == (disc_window(_TOTAL),)


def test_a_track_the_guard_band_swallows_has_no_window() -> None:
    windows = track_windows([0, 3_000, 30_000], 40_000)
    assert windows[0] is None  # 3,000 frames < the 5,880-frame front trim
    assert windows[1] == (3_000, 30_000)


def test_the_whole_disc_sweep_equals_the_calibration_sweep_at_every_offset() -> None:
    """The calibration sweep is itself pinned to the naive per-offset CRC
    (`test_ctdb_calibrate.py`), and to the hardware vector through the trims."""
    measured = sweep(_chunks(), _STARTS, _TOTAL, disc_range=DISC_OFFSET_RANGE)
    expected = ctdb_crc_offsets(_PCM)
    assert len(expected) == 2 * DISC_OFFSET_RANGE + 1  # non-triviality
    assert dict(measured.disc) == expected


def test_offset_zero_equals_the_hardware_confirmed_streamed_crc() -> None:
    measured = sweep(_chunks(), _STARTS, _TOTAL)
    assert set(measured.disc) == {0}  # the default sweeps the disc at 0 only
    assert measured.disc[0] == crc_mod.ctdb_crc_offset0_streaming(_chunks(), _TOTAL)


def test_every_track_crc_is_the_crc_of_its_window_moved_by_the_offset() -> None:
    measured = sweep(_chunks(), _STARTS, _TOTAL)
    windows = track_windows(_STARTS, _TOTAL)
    checked = 0
    for window, crcs in zip(windows, measured.tracks, strict=True):
        assert window is not None
        assert len(crcs) == 2 * DISC_OFFSET_RANGE + 1
        for offset in (-DISC_OFFSET_RANGE, -1, 0, 1, 777, DISC_OFFSET_RANGE):
            assert crcs[offset] == _naive(window, offset)
            checked += 1
        for offset in range(-DISC_OFFSET_RANGE, DISC_OFFSET_RANGE + 1, 211):
            assert crcs[offset] == _naive(window, offset)
            checked += 1
    assert checked >= 4 * 30  # the floor: this cannot pass by comparing nothing


def test_a_middle_track_at_offset_zero_is_the_plain_crc_of_the_track() -> None:
    """The link to EAC's Copy CRC (null samples counted), which
    `test_ctdb_per_track.py` finds in the real CTDB response for the reference disc."""
    measured = sweep(_chunks(), _STARTS, _TOTAL)
    for index in (1, 2):
        track = _chunks()[index]
        assert measured.tracks[index][0] == zlib.crc32(track) & 0xFFFFFFFF


def test_audio_that_stops_short_leaves_the_windows_past_it_unmeasured() -> None:
    """A decode shorter than the TOC: no CRC of audio that never arrived."""
    short = _chunks()[:3]  # the last track never decodes
    measured = sweep(short, _STARTS, _TOTAL)
    seen = sum(_FRAMES[:3])
    assert measured.bytes_seen == seen * 4
    # Track 4's window, once moved far enough back, lies wholly in audio that DID
    # arrive, so those offsets are measured; none reaching past it is.
    last = track_windows(_STARTS, _TOTAL)[3]
    assert last is not None
    assert 0 not in measured.tracks[3]
    assert measured.tracks[3]  # non-triviality: some offsets were measurable
    for offset, value in measured.tracks[3].items():
        assert last[1] + offset <= seen
        assert value == _naive(last, offset)
    assert 0 not in measured.disc  # the disc window reaches into track 4
    assert measured.tracks[1][0] == zlib.crc32(_chunks()[1]) & 0xFFFFFFFF


def test_sweep_disc_reads_the_windows_off_the_toc() -> None:
    sectors = [count // SAMPLES_PER_SECTOR for count in (9_996, 12_936, 7_056)]
    frames = tuple(s * SAMPLES_PER_SECTOR for s in sectors)
    pcm = random.Random(7).randbytes(sum(frames) * 4)
    offsets = [LEAD_IN_SECTORS + sum(sectors[:i]) for i in range(len(sectors))]
    toc = DiscToc(track_offsets=tuple(offsets), leadout=LEAD_IN_SECTORS + sum(sectors))
    measured = sweep_disc(_chunks(pcm, frames), toc)
    assert measured.disc[0] == crc_mod.ctdb_crc(pcm, 0)
    assert measured.tracks[1][0] == zlib.crc32(_chunks(pcm, frames)[1]) & 0xFFFFFFFF


@settings(max_examples=25, deadline=None)
@given(st.lists(st.integers(min_value=0, max_value=_TOTAL * 4), max_size=6))
def test_how_the_pcm_is_chunked_never_changes_a_crc(cuts: list[int]) -> None:
    """Chunk boundaries anywhere (mid-frame, empty chunks) give identical CRCs."""
    edges = sorted({0, _TOTAL * 4, *cuts})
    chunks = [_PCM[a:b] for a, b in zip(edges, edges[1:], strict=False)]
    chunks.insert(len(chunks) // 2, b"")
    reference = sweep(_chunks(), _STARTS, _TOTAL, track_range=40)
    assert sweep(chunks, _STARTS, _TOTAL, track_range=40) == reference


@settings(max_examples=60, deadline=None)
@given(
    st.binary(max_size=64),
    st.lists(st.integers(min_value=-50, max_value=50_000), max_size=4),
    st.integers(min_value=-10, max_value=50_000),
    st.integers(min_value=-3, max_value=8),
)
def test_sweep_never_raises_on_any_input(
    data: bytes, starts: list[int], total: int, spread: int
) -> None:
    """Decoded PCM and TOC numbers are external-derived, so no input may raise."""
    result = sweep([data], starts, total, disc_range=spread, track_range=spread)
    assert len(result.tracks) == len(starts)
    assert all(0 <= v <= 0xFFFFFFFF for v in result.disc.values())
