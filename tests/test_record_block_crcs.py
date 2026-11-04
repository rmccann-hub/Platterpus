"""`cyanrip-diagnostics/12`'s proposed `block_crcs`, read before the build exists.

The fork's round 38 lap 1 S10 (``cyanrip@f1bcb683:docs/handshake/round-38-lap-01.md``)
proposes a CRC32 per 75 frames for each kept read, moving the ``-j`` record to
``/12``. The record below is **HAND-MADE**: the committed ``/10`` fixture with its
schema set to ``/12`` and a ``block_crcs`` list added to a row, because no ``/12``
record exists yet and the lap does not say how an entry is spelled.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus import record_block_crcs as blocks
from platterpus.error_positions import report_block
from platterpus.isrc_provenance import parse_isrcs
from platterpus.ripper_ending import STATE_READ, parse_ending

_FIXTURE: Final[Path] = (
    Path(__file__).parent / "fixtures" / "cyanrip_fork_diagnostics10_interrupted.json"
)


def _record(schema: str, crcs: object | None = None, *, key: bool = True) -> str:
    data: dict[str, Any] = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    data["schema"] = schema
    if key:
        data["rip"]["track_state"][0][blocks.BLOCK_CRCS_KEY] = crcs
    return json.dumps(data)


def test_a_v12_record_is_read_and_its_block_crcs_reach_the_report() -> None:
    text = _record("cyanrip-diagnostics/12", ["0a1b2c3d", 4294967295, "zzzz", 0])
    assert parse_ending(text).state == STATE_READ
    reading = parse_isrcs(text)
    assert reading.state == STATE_READ
    row = report_block(reading)["tracks"][0]
    assert row["block_crcs_state"] == blocks.READ
    # Position-aligned: the unreadable third entry stays in its place, as null.
    assert row["block_crcs"] == ["0A1B2C3D", "FFFFFFFF", None, "00000000"]
    assert row["block_crcs_not_read"] == 1
    assert row["block_crcs_not_kept"] == 0


def test_a_v11_record_still_reads_and_says_not_present() -> None:
    text = _record("cyanrip-diagnostics/11", key=False)
    reading = parse_isrcs(text)
    assert reading.state == STATE_READ
    row = report_block(reading)["tracks"][0]
    assert row["block_crcs_state"] == blocks.NOT_PRESENT
    assert row["block_crcs"] is None


def test_null_and_wrong_types_are_their_own_states() -> None:
    assert blocks.parse_block_crcs({"block_crcs": None}).state == blocks.NOT_STATED
    assert blocks.parse_block_crcs({"block_crcs": "AB"}).state == blocks.UNRECOGNISED
    odd = blocks.parse_block_crcs({"block_crcs": [True, -1, 2**32, "ABCDEF0"]})
    assert odd.crcs == (None, None, None, None) and odd.not_read == 4


def test_a_list_past_the_bound_is_cut_at_the_end_and_counted() -> None:
    parsed = blocks.parse_block_crcs({"block_crcs": [1] * (blocks.MAX_BLOCKS + 7)})
    assert len(parsed.crcs) == blocks.MAX_BLOCKS
    assert parsed.not_kept == 7


def test_two_reads_are_compared_second_by_second() -> None:
    first = blocks.parse_block_crcs({"block_crcs": [1, 2, 3, "zz"]})
    second = blocks.parse_block_crcs({"block_crcs": [1, 9, 3, 4]})
    assert blocks.differing_seconds(first, second) == (1,)
    shorter = blocks.parse_block_crcs({"block_crcs": [1, 2]})
    assert blocks.differing_seconds(first, shorter) is None


@settings(max_examples=300, deadline=None)
@given(
    st.one_of(
        st.none(),
        st.text(max_size=20),
        st.lists(
            st.one_of(st.integers(), st.text(max_size=10), st.none(), st.booleans()),
            max_size=30,
        ),
        st.dictionaries(st.text(max_size=5), st.integers(), max_size=3),
    )
)
def test_the_reader_never_raises(value: object) -> None:
    parsed = blocks.parse_block_crcs({"block_crcs": value})
    assert parsed.state in blocks.STATES
    blocks.differing_seconds(parsed, parsed)


# --- Derived, not accepted: the fork's own `.29` record (round 38 lap 3 S6) -----
#
# Their lap 3 S6 says each entry is zlib's CRC-32 over 176,400 bytes of the same
# bytes `eac_crc` covers. If that is so, the blocks COMBINE to `eac_crc`, which
# we can check without the audio: zlib's `crc32_combine` needs only each block's
# length. The values are copied from their regenerated golden record,
# `cyanrip@838fb437:docs/golden-reference.diagnostics.json` (tracks of 225, 150
# and 75 frames, so every block is a whole 75 frames).

_GOLDEN_29: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("D36D9296", ("6457F1AA", "214ABF76", "A7F68480")),
    ("07B89F6F", ("3E9C7536", "CE785ED8")),
    ("CC206A3D", ("CC206A3D",)),
)
_BLOCK_BYTES: Final[int] = 176_400


def _gf2_times(mat: list[int], vec: int) -> int:
    total, index = 0, 0
    while vec:
        if vec & 1:
            total ^= mat[index]
        vec >>= 1
        index += 1
    return total


def _crc32_combine(first: int, second: int, second_length: int) -> int:
    """zlib's ``crc32_combine``, by its GF(2) matrix method."""
    odd = [0xEDB88320] + [1 << n for n in range(31)]
    even = [_gf2_times(odd, odd[n]) for n in range(32)]
    odd = [_gf2_times(even, even[n]) for n in range(32)]
    while True:
        even = [_gf2_times(odd, odd[n]) for n in range(32)]
        if second_length & 1:
            first = _gf2_times(even, first)
        second_length >>= 1
        if not second_length:
            break
        odd = [_gf2_times(even, even[n]) for n in range(32)]
        if second_length & 1:
            first = _gf2_times(odd, first)
        second_length >>= 1
        if not second_length:
            break
    return first ^ second


def test_the_combine_is_zlib_s() -> None:
    import zlib

    one, two = b"\x01" * _BLOCK_BYTES, b"\x7f" * _BLOCK_BYTES
    combined = _crc32_combine(zlib.crc32(one), zlib.crc32(two), _BLOCK_BYTES)
    assert combined == zlib.crc32(one + two)


def test_the_fork_s_blocks_combine_to_its_eac_crc() -> None:
    assert len(_GOLDEN_29) == 3  # floor: three tracks compared, one multi-block
    for eac_crc, entries in _GOLDEN_29:
        read = blocks.parse_block_crcs({"block_crcs": list(entries)})
        assert read.state == blocks.READ and read.not_read == 0
        crcs = [int(crc, 16) for crc in read.crcs if crc is not None]
        total = crcs[0]
        for crc in crcs[1:]:
            total = _crc32_combine(total, crc, _BLOCK_BYTES)
        assert f"{total:08X}" == eac_crc
