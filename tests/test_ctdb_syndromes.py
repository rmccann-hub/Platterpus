"""Our CTDB syndromes over a disc's PCM, against an independent reference (TASKS R43).

No copyrighted audio (CLAUDE.md rule 8): every disc here is random PCM generated
in the test. The reference encoder computes each syndrome by its DEFINITION, a
direct power sum ``sum_r word(r, c) * alpha**(i * (rows - 1 - r))`` over the
window the CTDB CRC covers, rather than by the module's Horner recurrence, its
row-shift algebra or its lookup table. The tests then hold the streamed
accumulator, the shift to any alignment and the column-0 sweep to it.

One more check ties the definition to the form CUETools STORES internally, a
systematic Reed-Solomon parity remainder, through the conversion its published
``Parity2Syndrome`` performs, so the definition is not merely self-consistent.
"""

from __future__ import annotations

import random

import numpy as np
import pytest

from platterpus.ctdb import gf16, syndromes
from platterpus.ctdb.rs_decode import chien_powers
from platterpus.ctdb.syndromes import (
    STRIDE,
    SyndromeAccumulator,
    chien_powers_fast,
    column0_by_offset,
    layout,
    record_syndromes,
    syndromes_at,
)

_EXP = np.array(gf16.EXP, dtype=np.int64)
_LOG = np.array(gf16.LOG, dtype=np.int64)

#: A synthetic disc of 6 rows: (6 + 2) rows' worth of words plus a ragged tail,
#: so the back guard band is longer than a row, as on a real disc.
ROWS = 6
TOTAL_FRAMES = ((ROWS + 2) * STRIDE + 2 * 123) // 2


def _pcm(seed: int, frames: int = TOTAL_FRAMES) -> bytes:
    return random.Random(seed).randbytes(4 * frames)


def reference(pcm: bytes, offset: int, npar: int) -> np.ndarray:
    """The definition, by direct power sums, at alignment ``offset`` frames."""
    words = np.frombuffer(pcm, dtype="<u2").astype(np.int64)
    rows = len(words) // STRIDE - 2
    start = STRIDE + 2 * offset
    block = words[start : start + rows * STRIDE].reshape(rows, STRIDE)
    out = np.zeros((npar, STRIDE), dtype=np.int64)
    for i in range(npar):
        for r in range(rows):
            power = i * (rows - 1 - r)
            row = block[r]
            term = np.where(row == 0, 0, _EXP[(_LOG[row] + power) % gf16.ORDER])
            out[i] ^= term
    return out.astype(np.uint16)


def _accumulate(pcm: bytes, chunk_sizes: list[int]) -> syndromes.OurSyndromes:
    columns = layout(len(pcm) // 4)
    assert columns is not None
    acc = SyndromeAccumulator(columns, deadline=float("inf"))
    position = 0
    sizes = iter(chunk_sizes)
    while position < len(pcm):
        size = next(sizes, len(pcm))
        assert acc.feed(pcm[position : position + size])
        position += size
    ours = acc.finish()
    assert ours is not None
    return ours


def test_the_layout_ends_where_the_crc_window_ends() -> None:
    columns = layout(TOTAL_FRAMES)
    assert columns is not None and columns.rows == ROWS
    # rows * STRIDE words = the CTDB CRC window: total less front 5880 frames and
    # the length-dependent back trim (crc.ctdb_trims).
    from platterpus.ctdb.crc import ctdb_trims

    front, back = ctdb_trims(TOTAL_FRAMES)
    assert columns.rows * STRIDE == 2 * (TOTAL_FRAMES - front - back)
    assert layout(STRIDE) is None  # too short for one row and its guard bands


@pytest.mark.parametrize(
    "chunks",
    [[], [1, 3, 11760 * 2 + 1, 7], [4 * 588] * 50, [99_999]],
    ids=["whole", "odd-bytes", "sectors", "big"],
)
def test_the_streamed_syndromes_equal_the_definition(chunks: list[int]) -> None:
    pcm = _pcm(1)
    ours = _accumulate(pcm, chunks)
    assert np.array_equal(ours.syn, reference(pcm, 0, 16))
    assert ours.rows == ROWS


@pytest.mark.parametrize("offset", [-5879, -2939, -1, 1, 2, 667, 5879])
def test_every_alignment_equals_the_definition_without_another_pass(
    offset: int,
) -> None:
    pcm = _pcm(2)
    ours = _accumulate(pcm, [])
    shifted = syndromes_at(ours, offset, 16)
    assert shifted is not None
    assert np.array_equal(shifted, reference(pcm, offset, 16))


def test_column0_at_every_offset_is_the_shifted_column0() -> None:
    pcm = _pcm(3)
    ours = _accumulate(pcm, [])
    reach = 40
    table = column0_by_offset(ours, 8, reach)
    for offset in range(-reach, reach + 1, 7):
        shifted = syndromes_at(ours, offset, 8)
        assert shifted is not None
        assert np.array_equal(table[offset + reach], shifted[:, 0])
    full = column0_by_offset(ours, 16, 5879)
    assert np.array_equal(full[0], reference(pcm, -5879, 16)[:, 0])
    assert np.array_equal(full[-1], reference(pcm, 5879, 16)[:, 0])


def test_an_alignment_outside_ctdbs_range_is_refused() -> None:
    ours = _accumulate(_pcm(4), [])
    assert syndromes_at(ours, 5880, 16) is None
    assert syndromes_at(ours, 0, 17) is None


def test_audio_that_stops_short_has_no_syndromes() -> None:
    pcm = _pcm(5)
    columns = layout(TOTAL_FRAMES)
    assert columns is not None
    acc = SyndromeAccumulator(columns, deadline=float("inf"))
    acc.feed(pcm[: len(pcm) - 4 * 600])
    assert acc.finish() is None


def test_a_passed_deadline_stops_the_pass() -> None:
    pcm = _pcm(6, frames=((64 + 3) * STRIDE) // 2)
    columns = layout(len(pcm) // 4)
    assert columns is not None
    acc = SyndromeAccumulator(columns, deadline=0.0)
    assert acc.feed(pcm) is False
    assert acc.stopped and acc.finish() is None
    assert acc.feed(b"\0\0\0\0") is False


def test_a_record_must_be_exactly_rows_by_stride() -> None:
    assert record_syndromes(bytes(4 * STRIDE * 2), 4) is not None
    assert record_syndromes(bytes(4 * STRIDE * 2 - 2), 4) is None
    assert record_syndromes(b"", 0) is None


def test_the_fast_root_search_agrees_with_the_reference() -> None:
    rng = random.Random(9)
    for _ in range(30):
        powers = rng.sample(range(3000), rng.randint(1, 8))
        locator = [1]
        for p in powers:  # multiply by (1 + alpha**p x)
            x = gf16.alpha_pow(p)
            locator = [
                (locator[k] if k < len(locator) else 0)
                ^ (gf16.mul(locator[k - 1], x) if k >= 1 else 0)
                for k in range(len(locator) + 1)
            ]
        assert (
            chien_powers_fast(locator, 3000)
            == chien_powers(locator, 3000)
            == sorted(powers)
        )


def test_the_definition_is_what_cuetools_systematic_parity_converts_to() -> None:
    """Their stored form is a parity remainder; their published conversion gives ours.

    CUETools encodes each column systematically: parity ``P(x) = D(x) * x**16 mod
    g(x)`` with ``g(x) = prod_{k<16} (x + alpha**k)`` (``Galois.makeEncodeGx``),
    and ``Parity2Syndrome`` turns the 16 parity words into syndromes as ``S_x =
    sum_k par[k] * alpha**(-(1 + k) * x)``, ``par[0]`` being the highest-degree
    coefficient. Done here by long division with the table-free multiply.
    """
    rng = random.Random(13)
    data = [rng.randrange(65536) for _ in range(40)]  # one column, first row first
    generator = [1]  # lowest degree first
    for k in range(16):
        root = gf16.alpha_pow(k)
        generator = [
            (generator[j - 1] if j >= 1 else 0)
            ^ (gf16.mul_slow(generator[j], root) if j < len(generator) else 0)
            for j in range(len(generator) + 1)
        ]
    # D(x) * x**16, highest degree first, then reduce by the monic generator.
    dividend = data + [0] * 16
    for i in range(len(data)):
        coefficient = dividend[i]
        if coefficient:
            for j in range(17):
                dividend[i + j] ^= gf16.mul_slow(coefficient, generator[16 - j])
    parity = dividend[-16:]  # par[0] is the x**15 coefficient
    converted = []
    for x in range(16):
        acc = 0
        for k, word in enumerate(parity):
            acc ^= gf16.mul_slow(word, gf16.alpha_pow(-(1 + k) * x))
        converted.append(acc)
    rows = len(data)
    by_definition = []
    for i in range(16):
        acc = 0
        for r, word in enumerate(data):
            acc ^= gf16.mul_slow(word, gf16.alpha_pow(i * (rows - 1 - r)))
        by_definition.append(acc)
    assert converted == by_definition
