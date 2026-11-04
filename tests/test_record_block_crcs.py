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
