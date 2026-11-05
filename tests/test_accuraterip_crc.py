"""Our AccurateRip v1/v2 checksums against an independent witness (the CTDB repair).

The pinned values were computed on 2026-11-04 by the C ``compute_checksums``
of Leo Bogert and Andreas Oberritter's ``accuraterip-checksum.c`` (GPLv3),
copied verbatim into a scratch program outside the repository, compiled with
gcc and fed the same seeded PCM this file generates. That is a second program
written by other people, not a second copy of our reading of the algorithm, so
agreeing with it is evidence (CLAUDE.md: two implementations sharing an ancestor
share its bugs). No audio is committed (rule 8): the PCM is ``random.Random``.
"""

from __future__ import annotations

import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.accuraterip_crc import (
    AR_GUARD_FRAMES,
    accuraterip_crcs,
    checked_range,
)

#: 20 sectors of seeded PCM, the witness's input.
_PCM: bytes = random.Random(20261104).randbytes(4 * 588 * 20)
#: 12 sectors of 0xFF bytes: every product overflows 32 bits, so v2 != v1.
_FF: bytes = b"\xff" * (4 * 588 * 12)

#: (pcm, track, total tracks) -> (v1, v2) as that C code printed them.
_WITNESS: list[tuple[bytes, int, int, str, str]] = [
    (_PCM, 1, 1, "4850522F", "4957618B"),
    (_PCM, 1, 3, "034E67FE", "0542DC18"),
    (_PCM, 2, 3, "D8BFB213", "DAD4AEF4"),
    (_PCM, 3, 3, "1DC19C44", "1EE93467"),
    (_FF, 1, 1, "FFC0A378", "FFFFFB67"),
    (_FF, 2, 3, "FE8419B8", "FFFFE470"),
]


@pytest.mark.parametrize(
    ("pcm", "track", "total", "v1", "v2"),
    _WITNESS,
    ids=[
        f"{'ff' if p is _FF else 'random'}-track{t}of{n}"
        for p, t, n, _a, _b in _WITNESS
    ],
)
def test_our_checksums_equal_the_c_witness(
    pcm: bytes, track: int, total: int, v1: str, v2: str
) -> None:
    got = accuraterip_crcs(pcm, track, total)
    assert got is not None
    assert (got.v1_hex, got.v2_hex) == (v1, v2)


def test_the_witness_cases_differ_from_each_other() -> None:
    """Non-triviality: the guard bands and the high halves each change the answer."""
    answers = {(v1, v2) for _p, _t, _n, v1, v2 in _WITNESS}
    assert len(answers) == len(_WITNESS)
    assert all(v1 != v2 for _p, _t, _n, v1, v2 in _WITNESS)


def test_the_guard_band_is_the_first_and_last_2940_frames() -> None:
    assert AR_GUARD_FRAMES == 2940
    assert checked_range(10_000, 1, 3) == (2940, 10_000)
    assert checked_range(10_000, 2, 3) == (1, 10_000)
    assert checked_range(10_000, 3, 3) == (1, 7060)
    assert checked_range(10_000, 1, 1) == (2940, 7060)


def test_one_changed_sample_changes_both_checksums() -> None:
    changed = bytearray(_PCM)
    changed[4 * 5000] ^= 1
    before = accuraterip_crcs(_PCM, 2, 3)
    after = accuraterip_crcs(bytes(changed), 2, 3)
    assert before is not None and after is not None
    assert before.v1 != after.v1 and before.v2 != after.v2


@pytest.mark.parametrize(
    ("pcm", "track", "total"),
    [(b"", 1, 1), (b"\x00" * 6, 1, 1), (_PCM, 0, 3), (_PCM, 4, 3)],
)
def test_input_that_is_not_one_track_returns_none(
    pcm: bytes, track: int, total: int
) -> None:
    assert accuraterip_crcs(pcm, track, total) is None


@settings(max_examples=60, deadline=None)
@given(st.binary(max_size=4096), st.integers(-3, 120), st.integers(-3, 120))
def test_never_raises(pcm: bytes, track: int, total: int) -> None:
    got = accuraterip_crcs(pcm, track, total)
    assert got is None or (0 <= got.v1 <= 0xFFFFFFFF and 0 <= got.v2 <= 0xFFFFFFFF)
