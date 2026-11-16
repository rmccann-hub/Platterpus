"""A track's record describes the read its file holds, not the reads around it.

Two defects the cyanrip fork found reading the owner's Full run of 2026-11-14
(their round 40 lap 3 S13 and S14; our lap 4 S8 and S9; TASKS R155 and R156).

**R155, ``kept_read_began``.** The field says when the read the files carry
began. It was read from the album pass's log and nothing replaced it when a
later read was kept, so in all seven whole-disc rips track 3 gave the album
read's time beside a later read's CRC: rip 1, ``05:02:54Z`` (a read of
``2E36401F``) beside the securing pass's ``59D352DD``, begun ``05:21:02Z``; rip 2,
``05:53:04Z`` beside the chase's ninth read, begun ``06:36:53Z``.

**R156, the repair's parenthetical.** Rip 1's track 5 kept its album read,
``6902BCF0``, a single read; the securing pass's five reads agreed on
``E0036697`` and were not kept; CTDB then repaired the file. The record said
``after the read (re-read, at most 5 agreeing): Copy CRC 6902BCF0 before``,
naming the securing pass's reads beside the album read's CRC.

The run's own files are the input, filed on ``evidence`` at ``7faf1b9f`` and
reached only through ``evidence_paths`` (copies of the logs, slim extracts of the
reports): each rip's album log, its securing pass's log, rip 2's chase log, and
each report's ``read_speed.retried_tracks`` (the worker's record of what it
re-read and kept) and ``ctdb.repair``. The merge is driven as the window drives
it, through ``RipMixin._apply_auto_fix_results``. No audio (Critical rule 8).
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest
from evidence_paths import evidence

from platterpus.ctdb.repair_types import RepairedTrack, RepairRecord, RepairStatus
from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
from platterpus.eac_log_export import render_eac_style_log
from platterpus.first_pass_reread import FirstPassReread
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import RereadAgreement, RipLog, TrackResult
from platterpus.rip_report import build_report
from platterpus.track_record import RECORD_REPAIRED, track_record
from platterpus.track_record_reads import album_pass_read_path, read_path
from platterpus.track_record_sources import repaired_tracks_by_number
from platterpus.ui.main_window_rip import RipMixin
from platterpus.verified_read_chase import (
    KEPT_FIRST_READ,
    KEPT_SECURING_PASS,
    KEPT_VERIFIED_REREAD,
)

_RUN = "docs/handshake/artifactsround40/round40fullrepeatrip"

#: One chase attempt's section of the chase log: its header, then that read's
#: own cyanrip log (``verified_read_chase.py`` writes the header).
_CHASE_HEADER = re.compile(
    r"^=== Platterpus verified-read chase: track (?P<track>\d+), "
    r"attempt (?P<attempt>\d+) ===$",
    re.MULTILINE,
)


def _text(name: str) -> str:
    return evidence(f"{_RUN}{name}").read_text(encoding="utf-8")


def _report(rip: int) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(_text(f"{rip}report.json"))
    return loaded


def _track(log: RipLog, number: int) -> TrackResult:
    return next(t for t in log.tracks if t.number == number)


def _report_track(report: dict[str, Any], number: int) -> dict[str, Any]:
    found: dict[str, Any] = next(t for t in report["tracks"] if t["number"] == number)
    return found


def _chase_read(rip: int, track: int, attempt: int) -> TrackResult:
    """The parsed record of one chase attempt, as the worker parses its log."""
    text = _text(f"{rip}verifiedread.txt")
    heads = list(_CHASE_HEADER.finditer(text))
    for index, head in enumerate(heads):
        if int(head["track"]) == track and int(head["attempt"]) == attempt:
            end = heads[index + 1].start() if index + 1 < len(heads) else len(text)
            return _track(parse_cyanrip_log(text[head.end() : end]), track)
    raise AssertionError(f"rip {rip} has no chase attempt {attempt} of track {track}")


def _merged(rip: int, shipped: dict[int, TrackResult]) -> RipLog:
    """The album pass with the run's later reads merged in, as the window does.

    The agreements are the securing pass's own, from its log, as the worker
    records them (``reread_agreements``) for every track it re-read.
    """
    securing = parse_cyanrip_log(_text(f"{rip}securingpass.txt"))
    window = SimpleNamespace(
        _last_retried_tracks=_report(rip)["read_speed"]["retried_tracks"],
        _last_swapped_tracks=shipped,
        _last_reread_agreements={
            t.number: t.secure_rerip_agreement
            for t in securing.tracks
            if t.secure_rerip_agreement is not None
        },
    )
    out = RipMixin._apply_auto_fix_results(
        window, parse_cyanrip_log(_text(f"{rip}.log"))
    )
    assert isinstance(out, RipLog)
    return out


@pytest.fixture(scope="module")
def rip1() -> RipLog:
    """Rip 1: the securing pass's track 3 shipped; track 5's album read stayed."""
    securing = parse_cyanrip_log(_text("1securingpass.txt"))
    return _merged(1, {3: _track(securing, 3)})


@pytest.fixture(scope="module")
def rip2() -> RipLog:
    """Rip 2: the chase's ninth read of track 3 shipped (its report says so)."""
    return _merged(2, {3: _chase_read(2, 3, 9)})


def _ctdb_repair_of_rip1() -> CtdbVerifyResult:
    """Rip 1's CTDB repair of track 5, from its report's ``ctdb.repair``."""
    block = _report(1)["ctdb"]["repair"]
    row = block["tracks"][0]
    repaired = RepairedTrack(
        track=row["track"],
        path=row["path"],
        original_kept_as=row["original_kept_as"],
        samples_corrected=row["samples_corrected"],
        pcm_crc32_before=int(row["pcm_crc32_before"], 16),
        pcm_crc32_after=int(row["pcm_crc32_after"], 16),
        ctdb_crc_expected=int(row["ctdb_crc_expected"], 16),
        ctdb_crc_after=int(row["ctdb_crc_after"], 16),
    )
    record = RepairRecord(
        RepairStatus.REPAIRED,
        entry_id=block["entry_id"],
        confidence=block["confidence"],
        tracks=(repaired,),
    )
    after = CtdbVerifyResult(
        verdict=Verdict.MATCH,
        confidence=block["confidence"],
        best_confidence=block["confidence"],
    )
    return CtdbVerifyResult(
        verdict=Verdict.NO_MATCH,
        best_confidence=block["confidence"],
        repair=record,
        after_repair=after,
    )


# --- non-triviality: the run's files say what the finding says --------------------


def test_the_shipped_reports_carry_both_defects() -> None:
    """The reports the run wrote: the album read's time, the securing pass's reads."""
    one, two = _report(1), _report(2)
    assert _report_track(one, 3)["copy_crc"] == "59D352DD"
    assert _report_track(one, 3)["kept_read_began"] == "2026-11-14T05:02:54Z"
    assert _report_track(two, 3)["kept_read_began"] == "2026-11-14T05:53:04Z"
    line = _report_track(one, 5)["record"]["line"]
    assert "after the read (re-read, at most 5 agreeing): Copy CRC 6902BCF0 before" in (
        line
    )


def test_each_read_has_its_own_start_in_its_own_log() -> None:
    """Two reads, two instants, so a test can tell which one the record took."""
    album = parse_cyanrip_log(_text("1.log"))
    securing = parse_cyanrip_log(_text("1securingpass.txt"))
    assert _track(album, 3).kept_read_began == "2026-11-14T05:02:54Z"
    assert _track(securing, 3).kept_read_began == "2026-11-14T05:21:02Z"
    assert _track(securing, 3).copy_crc == "59D352DD"
    chase = _chase_read(2, 3, 9)
    assert (chase.copy_crc, chase.kept_read_began) == (
        "59D352DD",
        "2026-11-14T06:36:53Z",
    )
    assert _track(parse_cyanrip_log(_text("2.log")), 3).kept_read_began == (
        "2026-11-14T05:53:04Z"
    )


# --- R155: kept_read_began follows the read the file holds ------------------------


def test_the_securing_pass_read_brings_its_own_start(rip1: RipLog) -> None:
    track = _track(rip1, 3)
    assert track.copy_crc == "59D352DD"
    assert track.kept_read_began == "2026-11-14T05:21:02Z"
    assert track.kept_read_began_state == "read"
    assert track.kept_read_pass == KEPT_SECURING_PASS


def test_a_chase_read_brings_its_own_start(rip2: RipLog) -> None:
    track = _track(rip2, 3)
    assert track.copy_crc == "59D352DD"
    assert track.kept_read_began == "2026-11-14T06:36:53Z"
    assert track.kept_read_pass == KEPT_VERIFIED_REREAD


def test_an_album_read_that_stayed_keeps_its_own_start(rip1: RipLog) -> None:
    """Track 5's file is the album read, so the album read's time is the right one."""
    track = _track(rip1, 5)
    assert track.copy_crc == "6902BCF0"
    assert track.kept_read_began == "2026-11-14T05:06:12Z"
    assert track.kept_read_pass == KEPT_FIRST_READ


def test_the_report_states_the_kept_reads_start(rip1: RipLog, rip2: RipLog) -> None:
    for log, expected in (
        (rip1, "2026-11-14T05:21:02Z"),
        (rip2, "2026-11-14T06:36:53Z"),
    ):
        row = _report_track(build_report(log), 3)
        assert (row["kept_read_began"], row["kept_read_began_state"]) == (
            expected,
            "read",
        )


def test_a_shipped_read_with_no_line_is_unknown_never_the_album_reads_time() -> None:
    """An older build prints no ``Kept read began:``: not stated, not the album's."""
    securing = parse_cyanrip_log(_text("1securingpass.txt"))
    silent = replace(_track(securing, 3), kept_read_began="", kept_read_began_state="")
    row = _report_track(build_report(_merged(1, {3: silent})), 3)
    assert row["kept_read_began"] is None
    assert row["kept_read_began_state"] == "not_present"


# --- R156: the repair names the read it started from ------------------------------


def test_the_repair_names_the_album_read_it_started_from(rip1: RipLog) -> None:
    """Both surfaces: the report's record and the EAC-layout log's ``Record:`` row."""
    ctdb = _ctdb_repair_of_rip1()
    report_line = _report_track(build_report(rip1, ctdb_result=ctdb), 5)["record"]
    assert report_line["kind"] == RECORD_REPAIRED
    text = render_eac_style_log(rip1, ctdb_result=ctdb)
    log_line = next(
        line.strip()
        for line in text.splitlines()
        if "Record: repaired from CTDB entry 32115" in line
    )
    for line in (report_line["line"], log_line):
        assert "after the read (first read): Copy CRC 6902BCF0 before" in line
        assert "at most 5 agreeing" not in line


def test_the_securing_pass_verdict_still_describes_the_track(rip1: RipLog) -> None:
    """The fix moves the parenthetical only: the drive's measured non-agreement on
    track 5 stays on the track, as the merge intends."""
    track = _track(rip1, 5)
    assert track.secure_rerip_converged is False
    assert track.secure_rerip_agreement == RereadAgreement(5, exact=True)
    assert read_path(track) == "re-read, at most 5 agreeing"


def test_a_repair_of_a_securing_pass_read_names_that_read(rip1: RipLog) -> None:
    """A file the securing pass replaced: its own reads are the ones to name."""
    track = _track(rip1, 3)
    facts = next(iter(repaired_tracks_by_number(_ctdb_repair_of_rip1()).values()))
    facts = replace(facts, crc_before="59D352DD")
    line = track_record(track, repair=facts).line
    assert f"after the read ({read_path(track)}): Copy CRC 59D352DD before" in line


def test_a_repair_of_a_chase_read_names_the_attempt(rip2: RipLog) -> None:
    track = _track(rip2, 3)
    facts = next(iter(repaired_tracks_by_number(_ctdb_repair_of_rip1()).values()))
    facts = replace(facts, crc_before="59D352DD")
    line = track_record(track, chased=True, chase_attempt=9, repair=facts).line
    assert "after the read (chase attempt 9, a single read): Copy CRC" in line


def test_a_repair_whose_start_is_not_the_records_read_names_none(
    rip1: RipLog,
) -> None:
    """Two CRCs, two reads: the line refuses to pick one."""
    facts = next(iter(repaired_tracks_by_number(_ctdb_repair_of_rip1()).values()))
    line = track_record(_track(rip1, 3), repair=facts).line
    assert (
        "after the read (which read is not determined: the record's Copy CRC is "
        "59D352DD): Copy CRC 6902BCF0 before"
    ) in line


def test_an_album_pass_read_with_its_own_reread_is_named_by_it() -> None:
    """A ``-Z`` album pass: its own verdict, kept by the merge, names the read."""
    track = TrackResult(
        number=5,
        filename="05.flac",
        copy_crc="6902BCF0",
        # The album pass's count stays on a track no later read replaced; its
        # verdict and agreement were overwritten by the securing pass's (5).
        rip_count=4,
        secure_rerip_converged=False,
        secure_rerip_agreement=RereadAgreement(5, exact=True),
        first_pass_reread=FirstPassReread(
            rip_count=4,
            converged=False,
            agreement=RereadAgreement(2, exact=True),
        ),
        kept_read_pass=KEPT_FIRST_READ,
    )
    assert album_pass_read_path(track) == "re-read, at most 2 agreeing of 4"
