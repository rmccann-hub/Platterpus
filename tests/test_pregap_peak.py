"""The fork's proposed `Pregap sample peak:` row, read before any build prints it.

TASKS R227. The fork's round 36 lap 1 S17 proposed saying, in track 1's block,
how loud the span before track 1 is (the hidden track one audio EAC reports and
cyanrip does not rip): ``    Pregap sample peak: 12.3% (-18.2 dBFS), not
ripped``, or ``unknown (<reason>)``. Their round 43 lap 1 S43 asks us to accept
that wording; they print it only after a release of ours that reads it. The row
is injected into a real `.35`-era log, so the rest of the log is what a drive
printed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus.parsers import cyanrip_log, pregap_peak
from platterpus.rip_report import REPORT_SCHEMA_VERSION, build_report

_FIXTURE = (
    Path(__file__).parent / "fixtures" / "cyanrip_fork_golden_reference_r36l7.log"
)
_LAP = (
    Path(__file__).parent.parent
    / "docs"
    / "handshake"
    / "inbound"
    / "round-36-lap-01.md"
)
_ANCHOR = "  Preemphasis:   none detected"


def _with_row(row: str) -> str:
    """The fixture with ``row`` added after track 1's `Preemphasis:` row only."""
    lines = _FIXTURE.read_text(encoding="utf-8").splitlines()
    first = lines.index(_ANCHOR)
    return "\n".join([*lines[: first + 1], row, *lines[first + 1 :]]) + "\n"


def test_the_fixture_has_the_anchor_once_per_track_and_track_1_first() -> None:
    """Floor: the insertion lands in a track block, so no test below is a no-op."""
    text = _FIXTURE.read_text(encoding="utf-8")
    assert text.splitlines().count(_ANCHOR) >= 2
    assert text.index("Track 1 read successfully!") < text.index(_ANCHOR)


def test_our_copy_of_the_proposal_is_the_filed_lap_s_text() -> None:
    """The example is checked against the fork's own words, not our memory."""
    filed = _LAP.read_text(encoding="utf-8")
    assert pregap_peak.PROPOSED_EXAMPLE.strip() in filed


@pytest.mark.parametrize(
    ("value", "state", "percent", "dbfs", "note", "reason"),
    [
        ("12.3% (-18.2 dBFS), not ripped", "read", 12.3, -18.2, "not ripped", ""),
        ("0.0% (-inf dBFS), not ripped", "read", 0.0, None, "not ripped", ""),
        ("100% (0.0 dBFS)", "read", 100.0, 0.0, "", ""),
        (
            "unknown (no span before track 1)",
            "unknown",
            None,
            None,
            "",
            "no span before track 1",
        ),
    ],
)
def test_each_form_reads(
    value: str,
    state: str,
    percent: float | None,
    dbfs: float | None,
    note: str,
    reason: str,
) -> None:
    peak = pregap_peak.read_value(value)
    assert (peak.state, peak.percent, peak.dbfs, peak.note, peak.reason) == (
        state,
        percent,
        dbfs,
        note,
        reason,
    )


@pytest.mark.parametrize(
    "value",
    ["101% (0.1 dBFS)", "１２% (-1 dBFS)", "loud", " ", "12.3 (-18.2 dBFS)"],
)
def test_any_other_shape_is_kept_as_unrecognised(value: str) -> None:
    peak = pregap_peak.read_value(value)
    assert peak.state == "unrecognised"
    assert peak.value
    assert peak.percent is None


def test_a_log_that_prints_the_row_carries_it_on_track_1() -> None:
    log = cyanrip_log.parse_cyanrip_log(_with_row(pregap_peak.PROPOSED_EXAMPLE))
    first = log.tracks[0]
    assert first.number == 1
    assert first.pregap_peak is not None
    assert first.pregap_peak.state == "read"
    assert first.pregap_peak.percent == 12.3
    assert all(track.pregap_peak is None for track in log.tracks[1:])

    report = build_report(log)
    assert report["schema_version"] == REPORT_SCHEMA_VERSION == 48
    block = report["tracks"][0]["pregap_peak"]
    assert block["state"] == "read" and block["dbfs"] == -18.2
    assert block["note"] == "not ripped"
    assert report["tracks"][1]["pregap_peak"]["state"] == "not_present"


def test_today_s_logs_read_not_present() -> None:
    log = cyanrip_log.parse_cyanrip_log(_FIXTURE.read_text(encoding="utf-8"))
    assert all(track.pregap_peak is None for track in log.tracks)
    report = build_report(log)
    assert report["tracks"][0]["pregap_peak"] == {
        "state": "not_present",
        "percent": None,
        "dbfs": None,
        "dbfs_text": None,
        "note": None,
        "reason": None,
        "value": None,
    }


def test_the_row_is_not_another_row_s() -> None:
    """`Sample peak:` and `Pregap search:`-style rows are not this row."""
    for line in (
        "  Sample peak:",
        "    Peak:        0.0 dBFS",
        "Pregap sample peak: 1%",
    ):
        assert pregap_peak.read_line(line) is None


@given(st.text(max_size=300))
def test_the_reader_never_raises(tail: str) -> None:
    pregap_peak.read_line("    Pregap sample peak: " + tail)
    pregap_peak.read_value(tail)


@given(st.text(max_size=300))
def test_a_claimed_row_is_never_read_as_absent(tail: str) -> None:
    peak = pregap_peak.read_line("    Pregap sample peak: " + tail)
    if peak is not None:
        assert peak.state in pregap_peak.PEAK_STATES - {"not_present"}
