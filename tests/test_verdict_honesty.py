"""The owner's known-fixes list of 2026-10-21, items 3 and 12: verdict honesty.

**Item 3.** "No errors occurred" sat over a track paranoia could not read cleanly,
and over an error line the ripper printed above its own ``Ripping errors: 0``.
The report now carries an ``issues`` code for each, its ``health_status`` and the
window's status line (one function, ``rip_health.effective_health_status``) no
longer read clean over an error line, and the EAC-layout log's read-stability
line names skipped tracks. The EAC-layout log's disc-level health sentence stays
verbatim: the fork diffs it, so its wording goes through the handshake.

**Item 12.** For a disc AccurateRip holds, the headline said the failing tracks
"aren't in the database or didn't match". It now names each as differing from
AccurateRip's entry, with the database's confidence for it, on every surface
that shows the headline (all through ``verdict.accuraterip_verdict``).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from evidence_paths import evidence
from PySide6.QtWidgets import QApplication

from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
from platterpus.eac_log_export import render_eac_style_log
from platterpus.parsers.cyanrip_log import is_ripper_error_line, parse_cyanrip_log
from platterpus.parsers.rip_log import AccurateRipResult, RipLog, TrackResult
from platterpus.rip_health import (
    ISSUE_ERROR_LINES_UNDER_ZERO_SUMMARY,
    ISSUE_UNVERIFIED_PARANOIA_SKIPS,
    effective_health_status,
    error_lines_contradicting_summary,
)
from platterpus.rip_report import build_report
from platterpus.ui.main_window_helpers import fidelity_summary
from platterpus.ui.rip_progress import RipProgress
from platterpus.verdict import accuraterip_verdict, reconcile_ar_ctdb

_FIXTURES = Path(__file__).parent / "fixtures"
#: A real fork log (round 35's golden reference): `Ripping errors: 0`, 3 tracks.
_R35_GOLDEN = _FIXTURES / "cyanrip_fork_golden_reference_r35.log"
#: The 2026-10-04 rig run: track 18 has 2,586 paranoia skips under
#: `Ripping errors: 0` and only one frame matched AccurateRip.
_ROUND30_OCT04_FULL_LOG = "docs/handshake/artifactsround30/round30oct04full.log"
_TRAILER_ERROR = "Error writing trailer: File too large!"


def _with_error_line_above_summary(text: str) -> str:
    """The fork's round-20 shape: an error line six lines above the zero summary."""
    assert "\nRipping errors: 0\n" in text, "floor: the subject has a zero summary"
    lines = text.split("\n")
    at = lines.index("Ripping errors: 0")
    return "\n".join([*lines[: at - 6], _TRAILER_ERROR, *lines[at - 6 :]])


# --- Item 3 (b): an error line under a zero summary -------------------------


def test_the_parser_keeps_the_error_line_and_health_stops_reading_clean() -> None:
    text = _with_error_line_above_summary(_R35_GOLDEN.read_text(encoding="utf-8"))
    rip_log = parse_cyanrip_log(text)
    # The ripper's own summary is untouched: it really did print 0.
    assert rip_log.ripping_errors == 0
    assert rip_log.health_status == "No errors occurred"
    assert rip_log.ripper_error_lines == (_TRAILER_ERROR,)
    assert rip_log.ripper_error_lines_total == 1
    assert error_lines_contradicting_summary(rip_log) == (_TRAILER_ERROR,)
    health = effective_health_status(rip_log)
    assert health != "No errors occurred"
    assert "1 error line" in health and "Ripping errors: 0" in health


def test_the_report_flags_the_disagreement_and_does_not_read_clean() -> None:
    text = _with_error_line_above_summary(_R35_GOLDEN.read_text(encoding="utf-8"))
    report = build_report(parse_cyanrip_log(text))
    assert report["health_status"] != "No errors occurred"
    found = [
        issue
        for issue in report["issues"]
        if issue["code"] == ISSUE_ERROR_LINES_UNDER_ZERO_SUMMARY
    ]
    assert len(found) == 1, report["issues"]
    assert found[0]["severity"] == "warning"
    assert _TRAILER_ERROR in found[0]["message"]


def test_the_status_line_does_not_say_ripped_cleanly_over_the_error_line() -> None:
    text = _with_error_line_above_summary(_R35_GOLDEN.read_text(encoding="utf-8"))
    summary = fidelity_summary(parse_cyanrip_log(text), expected_track_total=3)
    assert "ripped cleanly, no read errors" not in summary
    assert _TRAILER_ERROR in summary


def test_the_eac_layout_disc_sentence_stays_verbatim_until_the_handshake() -> None:
    """Deliberate: the fork diffs this line; the new wording is a round 36 proposal."""
    text = _with_error_line_above_summary(_R35_GOLDEN.read_text(encoding="utf-8"))
    eac = render_eac_style_log(parse_cyanrip_log(text))
    assert "\nNo errors occurred\n" in eac


def test_a_clean_log_has_no_error_lines_and_stays_clean() -> None:
    """The other side: a real clean log is not flagged, so the check can fail."""
    rip_log = parse_cyanrip_log(_R35_GOLDEN.read_text(encoding="utf-8"))
    assert rip_log.tracks, "floor: the log parsed"
    assert rip_log.ripper_error_lines == ()
    assert effective_health_status(rip_log) == "No errors occurred"
    codes = {issue["code"] for issue in build_report(rip_log)["issues"]}
    assert ISSUE_ERROR_LINES_UNDER_ZERO_SUMMARY not in codes


def test_no_committed_clean_fork_log_trips_the_check() -> None:
    """Every committed fork log with a zero summary: none has an error line."""
    examined = 0
    for path in sorted(_FIXTURES.glob("cyanrip_fork_golden_reference*.log")):
        rip_log = parse_cyanrip_log(path.read_text(encoding="utf-8"))
        assert rip_log.ripping_errors == 0, path
        assert error_lines_contradicting_summary(rip_log) == (), path
        examined += 1
    assert examined >= 3, examined


def test_a_secure_reread_verdict_is_not_an_error_line() -> None:
    """The matcher matches the repeat-limit verdict; the shared predicate does not."""
    assert not is_ripper_error_line(
        "Done; (no matches found, but hit repeat limit of 3)"
    )
    assert is_ripper_error_line(_TRAILER_ERROR)


def test_a_non_zero_summary_is_not_a_contradiction() -> None:
    rip_log = RipLog(
        log_creator="cyanrip 0.9.4",
        ripping_errors=1,
        health_status="1 ripping errors",
        ripper_error_lines=("Stopping, ripping incomplete!",),
        ripper_error_lines_total=1,
    )
    assert error_lines_contradicting_summary(rip_log) == ()
    assert effective_health_status(rip_log) == "1 ripping errors"


# --- Item 3 (a) and (c): a track paranoia skipped on --------------------------


def test_the_report_names_round_30s_skipped_track_18() -> None:
    rip_log = parse_cyanrip_log(
        evidence(_ROUND30_OCT04_FULL_LOG).read_text(encoding="utf-8")
    )
    assert rip_log.tracks[17].paranoia_counts.get("SKIP") == 2586, "floor"
    found = [
        issue
        for issue in build_report(rip_log, disc_track_total=18)["issues"]
        if issue["code"] == ISSUE_UNVERIFIED_PARANOIA_SKIPS
    ]
    assert len(found) == 1
    assert found[0]["severity"] == "warning"
    assert found[0]["message"].startswith("track(s) 18:"), found[0]["message"]


def test_the_read_stability_line_names_the_skipped_track() -> None:
    rip_log = parse_cyanrip_log(
        evidence(_ROUND30_OCT04_FULL_LOG).read_text(encoding="utf-8")
    )
    eac = render_eac_style_log(rip_log, disc_track_total=18)
    assert (
        "Read stability      : track(s) 18 had reads paranoia could not verify "
        "(skips) and AccurateRip did not confirm the audio — not confirmed"
    ) in eac


def test_a_skipped_track_accuraterip_confirmed_raises_nothing() -> None:
    track = TrackResult(
        number=1,
        copy_crc="0AC0374D",
        status="ripped successfully",
        paranoia_counts={"SKIP": 12},
        accuraterip_v2=AccurateRipResult(version=2, confidence=200),
    )
    rip_log = RipLog(log_creator="cyanrip 0.9.4", tracks=(track,))
    codes = {issue["code"] for issue in build_report(rip_log)["issues"]}
    assert ISSUE_UNVERIFIED_PARANOIA_SKIPS not in codes
    assert "Read stability" not in render_eac_style_log(rip_log)
    # And the same track unconfirmed does raise it: the check can fail.
    unconfirmed = replace(rip_log, tracks=(replace(track, accuraterip_v2=None),))
    codes = {issue["code"] for issue in build_report(unconfirmed)["issues"]}
    assert ISSUE_UNVERIFIED_PARANOIA_SKIPS in codes


# --- Item 12: a disc AccurateRip holds -----------------------------------------

_FOUND = "disc found in database (max confidence: 200)"


def _matched(number: int) -> TrackResult:
    return TrackResult(
        number=number,
        copy_crc=f"{number:08X}",
        accuraterip_lookup=_FOUND,
        accuraterip_v1=AccurateRipResult(
            version=1, result="accurately ripped", confidence=128, local_crc="AAAA"
        ),
        accuraterip_v2=AccurateRipResult(
            version=2, result="accurately ripped", confidence=200, local_crc="BBBB"
        ),
    )


def _differs(number: int, lookup: str = _FOUND) -> TrackResult:
    """cyanrip's shape for a track of a found disc that matched nothing."""
    miss = "not found, either a new pressing, or bad rip"
    return TrackResult(
        number=number,
        copy_crc=f"{number:08X}",
        accuraterip_lookup=lookup,
        accuraterip_v1=AccurateRipResult(version=1, result=miss, local_crc="CCCC"),
        accuraterip_v2=AccurateRipResult(version=2, result=miss, local_crc="DDDD"),
    )


def _twelve_of_fourteen() -> RipLog:
    tracks = tuple(_differs(n) if n in (5, 9) else _matched(n) for n in range(1, 15))
    return RipLog(
        log_creator="cyanrip 0.9.4", tracks=tracks, accuraterip_disc_status="found"
    )


def test_a_disc_in_accuraterip_names_the_tracks_that_differ() -> None:
    text, level = accuraterip_verdict(_twelve_of_fourteen(), disc_track_total=14)
    assert level == "warn"
    assert "12 of 14 tracks verified against AccurateRip" in text
    assert (
        "tracks 5 (confidence 200) and 9 (confidence 200) differ from "
        "AccurateRip's entry: most likely misreads"
    ) in text, text
    assert "aren't in the database" not in text, text


def test_one_differing_track_reads_as_the_owner_worded_it() -> None:
    tracks = tuple(_differs(n) if n == 5 else _matched(n) for n in range(1, 15))
    rip_log = RipLog(tracks=tracks, accuraterip_disc_status="found")
    text, _level = accuraterip_verdict(rip_log, disc_track_total=14)
    assert (
        "track 5 differs from AccurateRip's entry (confidence 200): most likely a "
        "misread"
    ) in text, text


def test_a_track_with_no_comparison_keeps_the_old_wording() -> None:
    """Standing not established for that track: nothing on record to differ from."""
    tracks = (
        *(_matched(n) for n in range(1, 14)),
        TrackResult(number=14, copy_crc="E"),
    )
    text, _level = accuraterip_verdict(RipLog(tracks=tracks), disc_track_total=14)
    assert "aren't in the database or didn't match" in text, text
    assert "differs from AccurateRip's entry" not in text


def test_the_report_and_the_window_show_the_same_headline(qapp: QApplication) -> None:
    rip_log = _twelve_of_fourteen()
    expected, _level = accuraterip_verdict(rip_log, disc_track_total=14)
    assert "differ from AccurateRip's entry" in expected, "floor: the new wording"
    report = build_report(rip_log, disc_track_total=14)
    assert report["verdict"]["message"] == expected
    widget = RipProgress()
    widget.set_rip_log(rip_log, disc_track_total=14)
    assert widget._verdict_banner.text() == expected


def test_nothing_matched_a_disc_accuraterip_holds_is_amber_not_unknown() -> None:
    tracks = tuple(_differs(n) for n in range(1, 4))
    rip_log = RipLog(tracks=tracks, accuraterip_disc_status="found")
    text, level = accuraterip_verdict(rip_log, disc_track_total=3)
    assert level == "warn", text
    assert "AccurateRip has an entry for this disc" in text
    assert "isn't in AccurateRip" not in text
    # Not in the database: the grey wording, which says so, is the right one.
    absent = tuple(_differs(n, lookup="not found") for n in range(1, 4))
    text, level = accuraterip_verdict(
        RipLog(tracks=absent, accuraterip_disc_status="not found"), disc_track_total=3
    )
    assert level == "neutral" and "isn't in AccurateRip" in text, text


def test_the_ctdb_reconciliation_names_the_same_tracks() -> None:
    ctdb = CtdbVerifyResult(verdict=Verdict.NO_MATCH, confidence=0, crc_validated=True)
    line = reconcile_ar_ctdb(_twelve_of_fourteen(), ctdb)
    assert line is not None
    assert "differ from AccurateRip's entry" in line and "SAME finding" in line
    assert "aren't in AccurateRip at all" not in line
