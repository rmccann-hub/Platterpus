"""Tests for platterpus.isrc_provenance — the files' ISRC beside the disc's (R20).

The record shape is the fork's ``.23`` (``cyanrip-diagnostics/9``), as every
``-j`` record of the 2026-10-16 Full run states it: on a whole-disc pass each
track has ``audio_ripped: true``, ``isrc_written`` the MusicBrainz code we
passed (``GBAAM0201086`` for track 1), ``isrc_disc: null`` and
``isrc_disc_reason: "libcdio returned none"``; on a pass limited with ``-l`` the
tracks not ripped say ``audio_ripped: false``, ``isrc_written: null`` and
``"not read"``. Those runs' records travel in the bundle, not the tree, so the
rows below copy their shape rather than read them.
"""

from __future__ import annotations

import json
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from platterpus import isrc_provenance as ip
from platterpus.rip_report import build_report
from platterpus.ripper_ending import (
    STATE_ABSENT,
    STATE_NOT_READ,
    STATE_NOT_REQUESTED,
    STATE_READ,
    STATE_UNREADABLE,
    STATE_UNRECOGNISED,
)


def _row(number: int, **fields: object) -> dict[str, object]:
    row: dict[str, object] = {
        "number": number,
        "cd_track": number,
        "audio_ripped": True,
        "isrc_written": None,
        "isrc_disc": None,
        "isrc_disc_reason": "libcdio returned none",
    }
    row.update(fields)
    return row


def _record(*rows: dict[str, object], schema: str = "cyanrip-diagnostics/9") -> str:
    return json.dumps({"schema": schema, "rip": {"track_state": list(rows)}})


def _agreements(text: str) -> list[str]:
    return [row["agreement"] for row in ip.report_block(ip.parse_isrcs(text))["tracks"]]  # type: ignore[index, union-attr]  # report_block's rows are dicts


# --- the run's own shapes --------------------------------------------------------


def test_the_whole_disc_pass_of_the_2026_10_16_run_reads_as_written_only() -> None:
    """MusicBrainz gave a code, the disc gave none: said as `written_only`, with
    the fork's reason kept beside it, and no issue raised."""
    text = _record(
        _row(1, isrc_written="GBAAM0201086"), _row(2, isrc_written="GBAAM0201089")
    )
    block = ip.report_block(ip.parse_isrcs(text))

    assert block["state"] == STATE_READ
    assert block["tracks"] == [
        {
            "number": 1,
            "audio_ripped": True,
            "written": "GBAAM0201086",
            "disc": None,
            "disc_reason": "libcdio returned none",
            "disc_well_formed": None,
            "agreement": ip.WRITTEN_ONLY,
        },
        {
            "number": 2,
            "audio_ripped": True,
            "written": "GBAAM0201089",
            "disc": None,
            "disc_reason": "libcdio returned none",
            "disc_well_formed": None,
            "agreement": ip.WRITTEN_ONLY,
        },
    ]
    assert ip.findings(block) == []


def test_a_track_a_limited_pass_did_not_rip_is_not_ripped_never_neither() -> None:
    """The securing pass and `-l` runs list every track. A track with no files
    has no written code for a different reason from a track MusicBrainz gave
    none, and the two are kept apart."""
    text = _record(
        _row(1, isrc_written="GBAAM0201086"),
        _row(2, audio_ripped=False, isrc_disc_reason="not read"),
        _row(3, isrc_written=None),
    )

    assert _agreements(text) == [ip.WRITTEN_ONLY, ip.NOT_RIPPED, ip.NEITHER]


# --- the comparison ----------------------------------------------------------------


def test_the_two_codes_agree_after_hyphens_and_case_are_set_aside() -> None:
    text = _record(_row(1, isrc_written="gb-aam-02-01086", isrc_disc="GBAAM0201086"))

    assert _agreements(text) == [ip.AGREE]


def test_a_disc_code_that_differs_is_information_naming_both_values() -> None:
    text = _record(
        _row(
            4,
            isrc_written="GBAAM0201086",
            isrc_disc="USABC1234567",
            isrc_disc_reason=None,
        )
    )
    report = build_report(
        None, disc={"isrc_provenance": ip.report_block(ip.parse_isrcs(text))}
    )

    issues = [i for i in report["issues"] if i["code"].startswith("isrc_")]
    assert issues == [
        {
            "severity": "info",
            "code": "isrc_disc_differs",
            "message": "track 4: the disc's own ISRC is USABC1234567, the files "
            "carry GBAAM0201086 (from MusicBrainz)",
        }
    ]


def test_a_disc_only_code_is_said_and_a_malformed_one_is_flagged() -> None:
    text = _record(
        _row(1, isrc_disc="GBAAM0201086", isrc_disc_reason=None),
        _row(2, isrc_disc="NOT-AN-ISRC", isrc_disc_reason=None),
    )
    block = ip.report_block(ip.parse_isrcs(text))

    assert [r["agreement"] for r in block["tracks"]] == [ip.DISC_ONLY, ip.DISC_ONLY]  # type: ignore[index, union-attr]  # rows are dicts
    assert [r["disc_well_formed"] for r in block["tracks"]] == [True, False]  # type: ignore[index, union-attr]  # rows are dicts
    assert [code for code, _ in ip.findings(block)] == ["isrc_disc_malformed"]


def test_well_formed_follows_iso_3901() -> None:
    assert ip.well_formed("GBAAM0201086") is True
    assert ip.well_formed("GB-AAM-02-01086") is True
    assert ip.well_formed("GBAAM020108") is False  # eleven characters
    assert ip.well_formed("12AAM0201086") is False  # country must be letters
    assert ip.well_formed("GBAAMXX01086") is False  # year must be digits
    assert ip.well_formed(None) is None


# --- tri-state: what is not determined is never a pass ----------------------------


def test_a_record_from_before_the_fields_existed_is_not_determined() -> None:
    """`cyanrip-diagnostics/7` (the 2026-10-06 records) has no ISRC fields. Its
    tracks compare as `not_determined`, never as `neither`."""
    text = _record(
        {"number": 1, "cd_track": 1, "audio_ripped": True},
        schema="cyanrip-diagnostics/7",
    )

    assert _agreements(text) == [ip.NOT_DETERMINED]


def test_a_field_of_the_wrong_type_is_not_determined() -> None:
    text = _record(_row(1, isrc_written=12345, isrc_disc="GBAAM0201086"))

    assert _agreements(text) == [ip.NOT_DETERMINED]


def test_records_that_are_not_cyanrips_say_why() -> None:
    assert ip.parse_isrcs("{").state == STATE_UNREADABLE
    assert ip.parse_isrcs("[]").state == STATE_UNRECOGNISED
    assert ip.parse_isrcs('{"schema": "other/1"}').state == STATE_UNRECOGNISED


def test_a_run_refused_before_it_ripped_is_read_with_no_tracks() -> None:
    reading = ip.parse_isrcs('{"schema": "cyanrip-diagnostics/9", "rip": null}')

    assert reading.state == STATE_READ
    assert reading.tracks == ()
    assert reading.detail == "the record lists no tracks"


def test_no_reading_at_all_is_not_read() -> None:
    assert ip.report_block(None)["state"] == STATE_NOT_READ


def test_rows_past_the_bound_or_not_tracks_are_counted() -> None:
    rows = [_row(n) for n in range(1, ip.MAX_TRACKS + 3)] + ["junk", {"number": True}]  # type: ignore[list-item]  # junk rows on purpose
    reading = ip.parse_isrcs(_record(*rows))  # type: ignore[arg-type]  # junk rows on purpose

    assert len(reading.tracks) == ip.MAX_TRACKS
    assert reading.dropped == 4
    assert ip.report_block(reading)["rows_not_read"] == 4


def test_values_from_the_record_are_screened_and_bounded() -> None:
    text = _record(
        _row(1, isrc_disc="GB\x1b[31mAAM" + "9" * 200, isrc_disc_reason=None)
    )
    disc = ip.parse_isrcs(text).tracks[0].disc

    assert disc is not None
    assert "\x1b" not in disc
    assert "more characters]" in disc


# --- the file reader ---------------------------------------------------------------


def test_the_reader_states_each_way_a_file_can_be_missing(tmp_path: Path) -> None:
    assert ip.read_isrcs(None).state == STATE_NOT_REQUESTED
    assert ip.read_isrcs(tmp_path / "absent.json").state == STATE_ABSENT

    big = tmp_path / "big.json"
    big.write_bytes(b" " * (ip.MAX_RECORD_BYTES + 1))
    assert ip.read_isrcs(big).state == STATE_UNREADABLE

    good = tmp_path / "good.json"
    good.write_text(_record(_row(1, isrc_written="GBAAM0201086")), encoding="utf-8")
    assert ip.read_isrcs(good).tracks[0].written == "GBAAM0201086"


# --- never raises --------------------------------------------------------------------

_JSON = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(max_size=20),
    lambda children: (
        st.lists(children, max_size=4)
        | st.dictionaries(st.text(max_size=12), children, max_size=4)
    ),
    max_leaves=20,
)


@given(st.text(max_size=200))
def test_parse_never_raises_on_any_text(text: str) -> None:
    ip.report_block(ip.parse_isrcs(text))


@given(_JSON)
def test_parse_and_findings_never_raise_on_any_json(value: object) -> None:
    wrapped = {"schema": "cyanrip-diagnostics/9", "rip": {"track_state": value}}
    block = ip.report_block(ip.parse_isrcs(json.dumps(wrapped)))
    ip.findings(block)
    ip.findings(value)
