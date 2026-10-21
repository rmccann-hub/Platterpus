"""The applied read offset, checked against the AccurateRip drive list.

TASKS P2 #6 (the owner's known-fixes list of 2026-10-21, item 11): the report
used to record only the offset APPLIED, never whether it was the AccurateRip
list's value for the drive. Each state is pinned here, on the real
``OffsetDatabase`` class (a stand-in Protocol fake would not exercise the
matching rule the app applies offsets with), plus the report's ``issues`` entry,
the results-pane line, and a "never raises" property over arbitrary input,
because the drive banner is external text.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from hypothesis import given
from hypothesis import strategies as st

from platterpus import read_offset_check as roc
from platterpus.adapters.accuraterip_offsets import OffsetDatabase
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import AccurateRipResult, TrackResult
from platterpus.rip_report import build_report

_REFERENCE = (
    Path(__file__).resolve().parents[1]
    / "output_reference"
    / "cyanrip_flac"
    / "cyanrip_flac_police_classics.log"
)

#: The two banner shapes cyanrip prints, verbatim from the reference logs.
_DEVICE_MODEL = "PIONEER  BD-RW   BDR-209D 1.51 SCSI CD-ROM"
_DRIVE_USED = "PIONEER  BD-RW   BDR-209D (revision 1.51)"

_DB = OffsetDatabase({"PIONEER BD-RW BDR-209D": 667, "PIONEER DVD-RW DVR-220L": 48})


def _track(number: int, *, matched: bool) -> TrackResult:
    ar = AccurateRipResult(
        version=2,
        result="Found, exact match" if matched else "Not found",
        confidence=5 if matched else None,
        local_crc="1A2B3C4D",
    )
    return TrackResult(number=number, accuraterip_v2=ar)


def _check(
    banner: object = _DEVICE_MODEL,
    applied: object = 667,
    lookup: OffsetDatabase | None = _DB,
    tracks: list[TrackResult] | None = None,
) -> roc.ReadOffsetCheckBlock:
    return roc.check_read_offset(
        drive_banner=banner, applied=applied, lookup=lookup, tracks=tracks
    )


def test_matches_names_the_database_entry() -> None:
    block = _check()
    assert block["state"] == roc.OFFSET_MATCHES
    assert block["listed"] == 667
    assert block["listed_entry"] == "PIONEER BD-RW BDR-209D"
    assert block["detail"] == (
        "+667, matches the AccurateRip drive database for PIONEER BD-RW BDR-209D"
    )
    assert roc.issue_for(block) is None
    assert roc.results_line(block).startswith("✓ Read offset +667, matches")


def test_the_forks_drive_used_banner_matches_too() -> None:
    assert roc.drive_name_candidates(_DRIVE_USED) == ("PIONEER BD-RW BDR-209D",)
    assert _check(banner=_DRIVE_USED)["state"] == roc.OFFSET_MATCHES


def test_differs_names_both_values_and_raises_a_warning() -> None:
    block = _check(applied=48)
    assert block["state"] == roc.OFFSET_DIFFERS
    assert (block["applied"], block["listed"]) == (48, 667)
    assert "+48 applied" in block["detail"] and "+667" in block["detail"]
    issue = roc.issue_for(block)
    assert issue is not None
    severity, code, message = issue
    assert (severity, code) == ("warning", roc.ISSUE_DIFFERS)
    assert "+48" in message and "+667" in message
    assert "PIONEER BD-RW BDR-209D" in message
    assert roc.results_line(block).startswith("⚠ ")


def test_drive_not_in_the_list_says_so() -> None:
    block = _check(banner="ACME     SUPERDRIVE 9000 1.00 SCSI CD-ROM")
    assert block["state"] == roc.OFFSET_DRIVE_NOT_LISTED
    assert block["listed"] is None
    assert "ACME SUPERDRIVE 9000" in block["detail"]
    assert "is not in the AccurateRip drive database" in block["detail"]
    issue = roc.issue_for(block)
    assert issue is not None and issue[:2] == ("info", roc.ISSUE_NOT_LISTED)
    assert roc.results_line(block).startswith("ⓘ ")


def test_not_determined_without_a_drive_model() -> None:
    for banner in ("", "   ", None, 42, "error retrieving drive info", "X" * 500):
        block = _check(banner=banner)
        assert block["state"] == roc.OFFSET_NOT_DETERMINED, banner
        assert roc.issue_for(block) is None


def test_not_determined_without_a_list() -> None:
    for lookup in (None, OffsetDatabase({})):
        block = _check(lookup=lookup)
        assert block["state"] == roc.OFFSET_NOT_DETERMINED
        assert "not available" in block["detail"]
        assert roc.issue_for(block) is None


def test_not_determined_when_the_log_states_no_offset() -> None:
    # A bool is an int in Python; True is not an offset of +1.
    for applied in (None, True, "667"):
        block = _check(applied=applied)
        assert block["state"] == roc.OFFSET_NOT_DETERMINED, applied
        assert block["applied"] is None
        assert block["listed"] == 667  # the list's answer is still recorded


def test_accuraterip_reconfirmation_is_tri_state() -> None:
    confirmed = _check(tracks=[_track(1, matched=True), _track(2, matched=False)])
    assert confirmed["accuraterip_reconfirms"] == roc.AR_CONFIRMED
    assert (
        confirmed["accuraterip_tracks_matched"],
        confirmed["accuraterip_tracks_read"],
    ) == (1, 2)
    assert "matched 1 of 2 tracks" in roc.results_line(confirmed)
    unconfirmed = _check(tracks=[_track(1, matched=False)])
    assert unconfirmed["accuraterip_reconfirms"] == roc.AR_NOT_CONFIRMED
    assert "neither confirms nor refutes" in unconfirmed["accuraterip_detail"]
    nothing = _check(tracks=[])
    assert nothing["accuraterip_reconfirms"] == roc.AR_NOT_DETERMINED
    assert nothing["accuraterip_tracks_read"] is None


def test_lookup_is_a_view_of_lookup_entry() -> None:
    """One matching rule: what the app applies and what the report checks."""
    assert _DB.lookup("PIONEER", "BD-RW  BDR-209D") == 667
    assert _DB.lookup_entry("PIONEER", "BD-RW  BDR-209D") == (
        "PIONEER BD-RW BDR-209D",
        667,
    )
    # The vendorless tail fallback names the row it matched.
    assert _DB.lookup_entry("", "DVD-RW DVR-220L") == ("PIONEER DVD-RW DVR-220L", 48)
    assert _DB.lookup_entry("", "") is None


def test_report_records_the_check_and_raises_the_issue() -> None:
    rip_log = parse_cyanrip_log(_REFERENCE.read_text(encoding="utf-8"))
    report = build_report(rip_log, offset_lookup=_DB)
    block = report["rip"]["read_offset_check"]
    assert block["state"] == roc.OFFSET_MATCHES
    assert block["accuraterip_reconfirms"] == roc.AR_CONFIRMED
    codes = {issue["code"] for issue in report["issues"]}
    assert roc.ISSUE_DIFFERS not in codes

    wrong = OffsetDatabase({"PIONEER BD-RW BDR-209D": 6})
    report = build_report(rip_log, offset_lookup=wrong)
    assert report["rip"]["read_offset_check"]["state"] == roc.OFFSET_DIFFERS
    issues = [i for i in report["issues"] if i["code"] == roc.ISSUE_DIFFERS]
    assert len(issues) == 1 and issues[0]["severity"] == "warning"

    # No list handed to the writer: recorded as not determined, never a pass.
    report = build_report(rip_log)
    assert report["rip"]["read_offset_check"]["state"] == roc.OFFSET_NOT_DETERMINED


def test_window_says_what_the_report_says() -> None:
    from platterpus.ui.main_window_rip import RipMixin

    lines: list[str] = []
    window = SimpleNamespace(
        _offset_db=_DB,
        _rip_progress=SimpleNamespace(append_log_line=lines.append),
    )
    rip_log = parse_cyanrip_log(_REFERENCE.read_text(encoding="utf-8"))
    RipMixin._announce_read_offset_check(window, rip_log)  # type: ignore[arg-type]  # a stub holding only the two attributes the method reads
    assert lines == [
        roc.results_line(
            build_report(rip_log, offset_lookup=_DB)["rip"]["read_offset_check"]
        )
    ]
    assert lines[0].startswith("✓ Read offset +667, matches")


_ANY: st.SearchStrategy[object] = st.one_of(
    st.none(), st.booleans(), st.integers(), st.text(), st.floats()
)


@given(
    banner=st.one_of(st.text(), _ANY),
    applied=_ANY,
    matched=st.lists(st.booleans(), max_size=4),
)
def test_never_raises(banner: object, applied: object, matched: list[bool]) -> None:
    roc.drive_name_candidates(banner)
    tracks = [_track(n, matched=m) for n, m in enumerate(matched, start=1)]
    block = _check(banner=banner, applied=applied, tracks=tracks)
    assert block["state"] in {
        roc.OFFSET_MATCHES,
        roc.OFFSET_DIFFERS,
        roc.OFFSET_DRIVE_NOT_LISTED,
        roc.OFFSET_NOT_DETERMINED,
    }
    roc.issue_for(block)
    roc.results_line(block)
    roc.issue_for(banner)
    roc.results_line(banner)
