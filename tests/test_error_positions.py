"""Tests for platterpus.error_positions — where paranoia reported read errors (R44).

**Where the shapes come from.** One real record: the fork's interrupted sample
for ``.25`` (``cyanrip-diagnostics/10``), copied byte for byte from
``cyanrip@5f1d036:docs/sample-interrupted.diagnostics.json`` into
``tests/fixtures/cyanrip_fork_diagnostics10_interrupted.json`` (the README says
why it is a copy). It holds the two states a real run gives: track 1 read with
an empty list, tracks 2 and 3 never read, all three fields null.

No record in either tree carries a position: round 35's Full run had none on any
track (the fork's lap 17 S8). The rows that do are built from the shape the
fork's source writes, ``{"lsn": <int>, "kind": "read_error" | "skip"}``
(``cyanrip@5f1d036:src/diagnostics.c:302-307``), the head-and-tail cap of 500
each (``:269-293``) and the sixteen counter keys (``:312-329``).
"""

from __future__ import annotations

import json
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from platterpus import error_positions as ep
from platterpus import isrc_provenance as ip
from platterpus.rip_report import build_report
from platterpus.ripper_ending import STATE_NOT_READ, STATE_READ

_FIXTURE = (
    Path(__file__).parent / "fixtures" / "cyanrip_fork_diagnostics10_interrupted.json"
)

#: The fork's counter keys, in its order (``cyanrip@5f1d036:src/diagnostics.c:312-329``).
_KEYS = (
    "READ VERIFY FIXUP_EDGE FIXUP_ATOM SCRATCH REPAIR SKIP DRIFT BACKOFF "
    "OVERLAP FIXUP_DROPPED FIXUP_DUPED READERR CACHEERR WROTE FINISHED"
).split()


def _counters(**counts: int) -> dict[str, int]:
    return {key: counts.get(key, 0) for key in _KEYS}


def _row(number: int, **fields: object) -> dict[str, object]:
    """A `/10` track_state row with no positions, read once."""
    row: dict[str, object] = {
        "number": number,
        "cd_track": number,
        "audio_ripped": True,
        "isrc_written": None,
        "isrc_disc": None,
        "isrc_disc_reason": "libcdio returned none",
        "paranoia_all_reads": _counters(READ=45),
        "error_positions": [],
        "error_positions_dropped": 0,
    }
    row.update(fields)
    return row


def _record(*rows: dict[str, object], schema: str = "cyanrip-diagnostics/10") -> str:
    return json.dumps({"schema": schema, "rip": {"track_state": list(rows)}})


def _block(text: str) -> ep.ErrorPositionsBlock:
    return ep.report_block(ip.parse_isrcs(text))


# --- the real record ---------------------------------------------------------------


def test_the_forks_interrupted_sample_reads_a_clean_track_and_two_never_read() -> None:
    """Track 1 read and reported nothing, which is a claim (`[]`, complete, the
    count agreeing with READERR + SKIP); tracks 2 and 3 were never read, which is
    no claim at all (null everywhere, never `[]` or 0)."""
    block = _block(_FIXTURE.read_text(encoding="utf-8"))

    assert block["state"] == STATE_READ
    first, second, third = block["tracks"]
    assert first["state"] == ep.READ
    assert first["positions"] == []
    assert (first["read_errors"], first["skips"]) == (0, 0)
    assert first["error_positions_dropped"] == 0
    assert first["complete"] is True
    assert first["count_agrees_with_counters"] is True
    assert first["paranoia_all_reads"] is not None
    assert first["paranoia_all_reads"]["READ"] == 91
    assert list(first["paranoia_all_reads"]) == _KEYS
    for row in (second, third):
        assert row["state"] == ep.TRACK_NOT_READ
        assert row["positions"] is None
        assert row["read_errors"] is None
        assert row["error_positions_dropped"] is None
        assert row["complete"] is None
        assert row["paranoia_all_reads_state"] == ep.TRACK_NOT_READ
        assert row["paranoia_all_reads"] is None
    assert ep.findings(block) == []


# --- positions -------------------------------------------------------------------


def test_positions_reach_the_report_with_a_warning_naming_the_track_and_count() -> None:
    text = _record(
        _row(1),
        _row(
            2,
            paranoia_all_reads=_counters(READ=60, READERR=2, SKIP=1),
            error_positions=[
                {"lsn": 20480, "kind": "read_error"},
                {"lsn": 20496, "kind": "read_error"},
                {"lsn": 20511, "kind": "skip"},
            ],
        ),
    )
    report = build_report(None, disc={"error_positions": _block(text)})

    row = report["disc"]["error_positions"]["tracks"][1]
    assert row["positions"] == [
        {"lsn": 20480, "kind": "read_error"},
        {"lsn": 20496, "kind": "read_error"},
        {"lsn": 20511, "kind": "skip"},
    ]
    assert (row["read_errors"], row["skips"]) == (2, 1)
    assert row["complete"] is True
    assert row["count_agrees_with_counters"] is True
    issues = [i for i in report["issues"] if i["code"].startswith("error_positions")]
    assert issues == [
        {
            "severity": "warning",
            "code": "error_positions_reported",
            "message": "track 2: cdparanoia reported 2 hard read error(s) and 1 "
            "skip(s) at disc sector(s) 20480, 20496, 20511 (AccurateRip and CTDB "
            "say whether the audio is right)",
        }
    ]


def test_the_rippers_dropped_count_sits_beside_the_list_and_in_the_sentence() -> None:
    """An elided list never reads as complete: the fork's count of the middle it
    did not keep is in the row, makes `complete` false, and is in the sentence."""
    text = _record(
        _row(
            5,
            paranoia_all_reads=_counters(READERR=9),
            error_positions=[{"lsn": 100, "kind": "read_error"}],
            error_positions_dropped=8,
        )
    )
    block = _block(text)

    row = block["tracks"][0]
    assert row["error_positions_dropped"] == 8
    assert row["complete"] is False
    assert row["count_agrees_with_counters"] is True
    ((code, sentence),) = ep.findings(block)
    assert code == ep.ISSUE_REPORTED
    assert "cyanrip did not list 8 more" in sentence


def test_dropped_positions_alone_still_raise_the_finding() -> None:
    """A list the fork emptied (a failed allocation counts every position as
    dropped, `cyanrip@5f1d036:src/diagnostics.c:271-276`) is not a clean track."""
    text = _record(
        _row(
            3,
            paranoia_all_reads=_counters(READERR=4),
            error_positions=[],
            error_positions_dropped=4,
        )
    )

    assert [code for code, _ in ep.findings(_block(text))] == [ep.ISSUE_REPORTED]


def test_an_over_long_list_keeps_its_head_and_tail_and_counts_the_middle() -> None:
    entries = [{"lsn": n, "kind": "skip"} for n in range(1200)]
    reads = ep.parse_reads(_row(1, error_positions=entries))

    assert len(reads.positions) == ep.KEEP_HEAD + ep.KEEP_TAIL
    assert reads.positions[0].lsn == 0
    assert reads.positions[ep.KEEP_HEAD - 1].lsn == ep.KEEP_HEAD - 1
    # The run at the track's end survives: that is what a head-only cap loses.
    assert reads.positions[ep.KEEP_HEAD].lsn == 1200 - ep.KEEP_TAIL
    assert reads.positions[-1].lsn == 1199
    assert reads.not_kept == 200
    assert reads.complete() is False


def test_entries_that_are_not_positions_are_counted_never_silently_lost() -> None:
    reads = ep.parse_reads(
        _row(
            1,
            error_positions=[
                {"lsn": 10, "kind": "read_error"},
                "not an object",
                {"lsn": True, "kind": "skip"},  # a bool is not a sector
                {"lsn": ep.LSN_MAX + 1, "kind": "skip"},  # past any CD
                {"lsn": ep.LSN_MIN - 1, "kind": "skip"},
                {"lsn": 11},  # no kind
                {"lsn": 12, "kind": "wobble\x1b[2J"},  # kept, as said, screened
            ],
        )
    )

    assert [(p.lsn, p.kind) for p in reads.positions] == [
        (10, "read_error"),
        (12, "wobble\\x1b[2J"),
    ]
    assert reads.not_kept == 5
    assert reads.complete() is False


def test_a_list_that_disagrees_with_its_counters_is_said() -> None:
    text = _record(
        _row(
            7,
            paranoia_all_reads=_counters(READERR=3, SKIP=0),
            error_positions=[{"lsn": 500, "kind": "read_error"}],
        )
    )
    block = _block(text)

    assert block["tracks"][0]["count_agrees_with_counters"] is False
    codes = [code for code, _ in ep.findings(block)]
    assert codes == [ep.ISSUE_REPORTED, ep.ISSUE_COUNT_DISAGREES]
    report = build_report(None, disc={"error_positions": block})
    severities = {
        i["code"]: i["severity"]
        for i in report["issues"]
        if i["code"].startswith("error_positions")
    }
    assert severities == {
        "error_positions_reported": "warning",
        "error_positions_count_disagrees": "info",
    }


# --- tri-state ---------------------------------------------------------------------


def test_a_record_from_before_the_fields_existed_is_not_present() -> None:
    """`cyanrip-diagnostics/9` (`.23`, `.24`) has none of the three keys: not
    present, and no list, never an empty one that would read as clean."""
    text = _record(
        {"number": 1, "audio_ripped": True, "isrc_written": None, "isrc_disc": None},
        schema="cyanrip-diagnostics/9",
    )
    row = _block(text)["tracks"][0]

    assert row["state"] == ep.NOT_PRESENT
    assert row["positions"] is None
    assert row["error_positions_dropped"] is None
    assert row["complete"] is None
    assert row["count_agrees_with_counters"] is None
    assert row["paranoia_all_reads_state"] == ep.NOT_PRESENT


def test_fields_of_the_wrong_type_are_not_determined() -> None:
    reads = ep.parse_reads(
        _row(
            1,
            error_positions="none",
            error_positions_dropped=-1,
            paranoia_all_reads=[1, 2],
        )
    )

    assert reads.state == ep.NOT_DETERMINED
    assert reads.dropped_by_ripper is None
    assert reads.counters_state == ep.NOT_DETERMINED
    assert reads.complete() is None


def test_counter_entries_that_are_not_counters_are_counted() -> None:
    reads = ep.parse_reads(
        _row(1, paranoia_all_reads={"READ": 4, "lower": 1, "SKIP": "x", "READERR": -2})
    )

    assert reads.counters == (("READ", 4),)
    assert reads.counters_not_read == 3
    # SKIP and READERR were unreadable, so the invariant cannot be checked.
    assert reads.agrees_with_counters() is None


def test_no_reading_at_all_is_not_read() -> None:
    block = ep.report_block(None)

    assert block["state"] == STATE_NOT_READ
    assert block["tracks"] == []
    assert block["note"] == ep.NOTE


# --- never raises ------------------------------------------------------------------

_JSON = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(max_size=20),
    lambda children: (
        st.lists(children, max_size=4)
        | st.dictionaries(st.text(max_size=12), children, max_size=4)
    ),
    max_leaves=20,
)

_KEY = st.sampled_from([ep.POSITIONS_KEY, ep.DROPPED_KEY, ep.COUNTERS_KEY, "number"])


@given(st.dictionaries(_KEY, _JSON, max_size=4))
def test_parse_reads_never_raises_on_any_row(row: dict[str, object]) -> None:
    reads = ep.parse_reads(row)
    reads.complete()
    reads.agrees_with_counters()


@given(st.lists(st.dictionaries(_KEY, _JSON, max_size=4), max_size=4))
def test_the_block_and_its_findings_never_raise_on_any_rows(
    rows: list[dict[str, object]],
) -> None:
    for number, row in enumerate(rows, start=1):
        row["number"] = number
    block = _block(_record(*rows))
    ep.findings(block)
    json.dumps(block)


@given(_JSON)
def test_findings_never_raise_on_any_json(value: object) -> None:
    ep.findings(value)
    ep.findings({"tracks": value})
