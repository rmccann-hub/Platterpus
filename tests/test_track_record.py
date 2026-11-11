"""Round 39's gate G3, "the record": every track says how it was verified.

The owner-approved plan of 2026-11-11: each track's line, in the EAC-layout log
and the report, names one of first read; re-read, n agreeing of m; kept at the -Z
limit for AccurateRip; the fork's ``.31`` rule (a seam); chase attempt k;
repaired from CTDB (entry, then AccurateRip v1 and v2); or not verified. And two
wordings never appear: ``Accurately ripped`` on a repaired track, and ``OK`` over
reads that disagree (EAC's own fault, ``docs/eac-parity.md`` Part F row 8).

The repaired case is the owner's Full run of 2026-11-10 (secure re-read): track 5
rewritten toward CTDB entry 32115, ``E0036697`` to ``C96464AB``, with AccurateRip
v1 ``134C0B9D`` and v2 ``BCF4E815`` after (the values pre-registered for it in
``docs/session-log.md``, 2026-11-04). No audio is involved (Critical rule 8): the
facts are dataclasses and text.
"""

from __future__ import annotations

import itertools
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from platterpus.ctdb.repair_types import RepairedTrack, RepairRecord, RepairStatus
from platterpus.ctdb.repair_wording import ACCURATERIP_AFTER_REPAIR_WHY
from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
from platterpus.eac_log_export import render_eac_style_log
from platterpus.eac_track_verdict import (
    DISAGREED_VERDICT,
    DISAGREED_VERIFIED_VERDICT,
    REPAIRED_READ_MATCHED,
    REPAIRED_VERDICT,
    status_line,
)
from platterpus.other_reads import OtherRead
from platterpus.parsers.rip_log import (
    AccurateRipResult,
    LimitKeptRead,
    RereadAgreement,
    RipLog,
    TrackResult,
)
from platterpus.rip_report import build_report
from platterpus.track_record import (
    RECORD_CHASE,
    RECORD_FIRST_READ,
    RECORD_KEPT_AT_LIMIT,
    RECORD_KINDS,
    RECORD_NOT_VERIFIED,
    RECORD_REPAIRED,
    RECORD_REREAD,
    track_record,
)
from platterpus.track_record_reads import reads_disagree
from platterpus.track_record_sources import (
    AR_GUIDED_CONVERGENCE_BUILDS,
    ar_guided_convergence,
    chase_attempts_by_track,
    fork_build_number,
    repaired_tracks_by_number,
)
from platterpus.uiscript.track_record_grading import (
    eac_log_blocks,
    grade_track_records,
)

_LOOKUP = "disc found in database (max confidence: 200)"


def _verified(number: int, **fields: Any) -> TrackResult:
    """A track AccurateRip verifies (v1 at 128, v2 at 200), read once."""
    return TrackResult(
        number=number,
        filename=f"{number:02d}.flac",
        copy_crc="1A2B3C4D",
        status="ripped successfully",
        accuraterip_v1=AccurateRipResult(1, "accurately ripped", 128, "11111111"),
        accuraterip_v2=AccurateRipResult(2, "accurately ripped", 200, "22222222"),
        accuraterip_lookup=_LOOKUP,
        **fields,
    )


def _track5() -> TrackResult:
    """Track 5 of the 2026-11-10 secure re-read, as the read left it."""
    return TrackResult(
        number=5,
        filename="05 - Don't Stand So Close to Me.flac",
        copy_crc="E0036697",
        status="ripped successfully",
        rip_count=3,
        secure_rerip_converged=False,
        secure_rerip_agreement=RereadAgreement(most_reads_agreed=2, exact=True),
        accuraterip_v1=AccurateRipResult(
            1, "not found, either a new pressing, or bad rip", None, "9D8E7F60"
        ),
        accuraterip_v2=AccurateRipResult(
            2, "not found, either a new pressing, or bad rip", None, "6902BCF0"
        ),
        accuraterip_lookup=_LOOKUP,
    )


def _repaired_result() -> CtdbVerifyResult:
    """CTDB's answer with the repair of track 5 landed and verified again."""
    row = RepairedTrack(
        track=5,
        path="/music/05.flac",
        original_kept_as="/music/05.flac.before-ctdb-repair",
        samples_corrected=6,
        pcm_crc32_before=0xE0036697,
        pcm_crc32_after=0xC96464AB,
        ctdb_crc_expected=0x1CB564CC,
        ctdb_crc_after=0x1CB564CC,
        accuraterip_v1_after=0x134C0B9D,
        accuraterip_v2_after=0xBCF4E815,
    )
    record = RepairRecord(
        RepairStatus.REPAIRED, entry_id="32115", confidence=1416, tracks=(row,)
    )
    after = CtdbVerifyResult(
        verdict=Verdict.MATCH, confidence=1416, best_confidence=1416
    )
    return CtdbVerifyResult(
        verdict=Verdict.NO_MATCH,
        best_confidence=1416,
        repair=record,
        after_repair=after,
    )


def _log(
    *tracks: TrackResult, creator: str = "cyanrip 0.9.4-rc3+platterpus.30"
) -> RipLog:
    return RipLog(log_creator=creator, tracks=tracks)


def _block(text: str, number: int) -> list[str]:
    return eac_log_blocks(text)[number]


def _last(block: list[str]) -> str:
    """A track block's status line: its last line with text."""
    return next(line.strip() for line in reversed(block) if line.strip())


# --- the repaired track: the owner's 2026-11-10 run ------------------------------


def test_the_repaired_track_says_so_in_the_eac_layout_log() -> None:
    """Track 5's block keeps the read's rows and names the repair beside them."""
    text = render_eac_style_log(
        _log(_verified(4), _track5()), ctdb_result=_repaired_result()
    )
    block = "\n".join(_block(text, 5))
    record = next(line.strip() for line in block.splitlines() if "Record:" in line)
    assert record.startswith(
        "Record: repaired from CTDB entry 32115 (confidence 1,416)"
    )
    assert "Copy CRC E0036697 before, C96464AB after, 6 samples corrected" in record
    assert (
        "a fresh CTDB check of the repaired files agrees (1,416 submissions)" in record
    )
    assert (
        "AccurateRip v1 134C0B9D: not determined; v2 BCF4E815: not determined" in record
    )
    assert ACCURATERIP_AFTER_REPAIR_WHY in record
    # The read's own rows are untouched: the Copy CRC is still the read's.
    assert "Copy CRC E0036697" in block and "Copy CRC C96464AB" not in block
    assert "accurately ripped" not in block.lower()
    assert _last(_block(text, 5)) == REPAIRED_VERDICT
    assert "OK" not in REPAIRED_VERDICT.split()


def test_before_the_repair_lands_the_same_track_is_not_verified() -> None:
    """The first write, and the CTDB answer's write, describe the read alone."""
    text = render_eac_style_log(_log(_track5()))
    record = next(line for line in _block(text, 5) if "Record:" in line)
    assert "Record: not verified — re-read, at most 2 agreeing of 3" in record
    assert "repaired" not in record


def test_the_report_records_the_repair_per_track() -> None:
    report = build_report(_log(_verified(4), _track5()), ctdb_result=_repaired_result())
    by_number = {t["number"]: t for t in report["tracks"]}
    record = by_number[5]["record"]
    assert record["kind"] == RECORD_REPAIRED and record["repaired"] is True
    assert record["reads_disagree"] is True
    assert "entry 32115" in record["line"] and "C96464AB after" in record["line"]
    assert by_number[4]["record"]["kind"] == RECORD_FIRST_READ
    assert by_number[4]["record"]["repaired"] is False


def test_the_log_and_the_report_print_one_line_per_track() -> None:
    """Two surfaces, one key: the report's line is the log's Record row."""
    rip_log = _log(_verified(4), _track5())
    ctdb = _repaired_result()
    text = render_eac_style_log(rip_log, ctdb_result=ctdb)
    report = build_report(rip_log, ctdb_result=ctdb)
    for track in report["tracks"]:
        row = next(x for x in _block(text, track["number"]) if "Record:" in x)
        assert row.strip() == f"Record: {track['record']['line']}"


def test_a_refused_repair_changes_no_record() -> None:
    refused = replace(
        _repaired_result(),
        repair=RepairRecord(RepairStatus.REFUSED, reason="a guard said no"),
        after_repair=None,
    )
    assert repaired_tracks_by_number(refused) == {}
    text = render_eac_style_log(_log(_track5()), ctdb_result=refused)
    assert "repaired from CTDB" not in text


def test_accurately_ripped_never_reaches_a_repaired_track_row() -> None:
    """The guard holds by construction, not only by the plan's refusal.

    The repair refuses a track AccurateRip verified, so this input is one the
    product should never build; the row must still not vouch for the file.
    """
    matched = replace(_verified(5), copy_crc="E0036697")
    text = render_eac_style_log(_log(matched), ctdb_result=_repaired_result())
    block = "\n".join(_block(text, 5))
    assert "accurately ripped" not in block.lower()
    assert REPAIRED_READ_MATCHED + " (confidence 200)" in block


# --- OK over reads that disagree --------------------------------------------------


def test_reads_that_disagree_never_read_ok_even_when_they_converged() -> None:
    """`.30`'s Other read lines prove a read the album did not keep differed."""
    other = OtherRead(state="read", text="", crc="4065BECC", count=1, where="not_known")
    converged = replace(
        _verified(3), rip_count=4, secure_rerip_converged=True, other_reads=(other,)
    )
    text = render_eac_style_log(_log(converged))
    block = _block(text, 3)
    assert _last(block) == DISAGREED_VERIFIED_VERDICT
    record = next(x for x in block if "Record:" in x)
    assert "re-read, 3 agreeing of 4" in record  # exact: 4 reads, one other


def test_a_test_crc_unlike_the_copy_crc_is_never_copy_ok() -> None:
    """EAC's own fault, in a legacy dual-read log: Test != Copy, Copy OK."""
    legacy = TrackResult(
        number=1, test_crc="AAAAAAAA", copy_crc="BBBBBBBB", status="Copy OK"
    )
    text = render_eac_style_log(_log(legacy, creator="legacyripper 0.10.0"))
    assert _last(_block(text, 1)) == DISAGREED_VERDICT


def test_a_chase_read_names_its_attempt_and_is_not_ok() -> None:
    chased = _verified(5)
    retried = [{"track": 5, "verified_read_chase": {"kept_attempt": 3}}]
    secure = {
        "mode": "dynamic",
        "engaged": True,
        "disc_in_accuraterip": True,
        "skipped_reason": None,
        "interrupted": False,
        "accuraterip_standing": None,
        "verified_rereads": [5],
    }
    text = render_eac_style_log(
        _log(chased),
        secure_rerip=secure,
        retried_tracks=retried,  # type: ignore[arg-type]  # a hand-built block
    )
    block = _block(text, 5)
    record = next(x for x in block if "Record:" in x)
    assert "Record: chase attempt 3 (TASKS R7)" in record
    assert (
        "verified by AccurateRip v1 at confidence 128 and v2 at confidence 200"
        in record
    )
    assert _last(block) == DISAGREED_VERIFIED_VERDICT
    assert chase_attempts_by_track(retried) == {5: 3}


def test_no_status_line_says_ok_over_a_repair_or_disagreeing_reads() -> None:
    """Every combination of the verdict's inputs: OK only when neither holds."""
    flags = [True, False]
    for (
        skips,
        reproducible,
        contradicted,
        timed,
        repaired,
        disagree,
        verified,
    ) in itertools.product(
        flags, [True, False, None], flags, flags, flags, [True, False, None], flags
    ):
        line = status_line(
            "ripped successfully",
            reproducible=reproducible,
            unverified_skips=skips,
            contradicted=contradicted,
            stopped_by_time_limit=timed,
            repaired=repaired,
            reads_disagree=disagree,
            accuraterip_verified=verified,
        )
        if repaired or disagree is True:
            assert "OK" not in line.split(), (line, repaired, disagree)


def test_a_clean_single_read_still_reads_copy_ok() -> None:
    """The mirror: a track nothing contradicts keeps EAC's own clean line."""
    text = render_eac_style_log(_log(_verified(1)))
    assert _last(_block(text, 1)) == "Copy OK"


# --- each kind's line ---------------------------------------------------------------


#: One case per kind a track's own fields can reach, with the words it opens with.
#: A literal list, not a parametrize over it: a computed population that came out
#: empty would generate no case at all (`tests/test_dynamic_sweeps_declare_a_floor.py`).
_KIND_CASES: list[tuple[TrackResult, str, str]] = [
    (_verified(1), RECORD_FIRST_READ, "first read; verified by AccurateRip v1 at"),
    (
        replace(_verified(1), rip_count=2, secure_rerip_converged=True),
        RECORD_REREAD,
        "re-read, 2 agreeing of 2; verified by AccurateRip",
    ),
    (
        replace(_verified(1), rip_count=5, secure_rerip_converged=True),
        RECORD_REREAD,
        "re-read, at least 2 agreeing of 5;",
    ),
    (
        replace(
            _verified(1),
            rip_count=3,
            secure_rerip_converged=False,
            secure_rerip_kept_read=LimitKeptRead("c96464ab", 1, 200),
        ),
        RECORD_KEPT_AT_LIMIT,
        "kept at the -Z limit for AccurateRip's match (the ripper's "
        "--prefer-accuraterip-match): C96464AB, read 1 time, AccurateRip "
        "confidence 200",
    ),
    (
        TrackResult(number=2, copy_crc="12345678", status="ripped successfully"),
        RECORD_NOT_VERIFIED,
        "not verified — first read;",
    ),
]


def test_each_kind_has_its_words() -> None:
    assert len(_KIND_CASES) >= 5  # a floor: the loop below cannot pass on nothing
    for track, kind, starts in _KIND_CASES:
        record = track_record(track)
        assert record.kind == kind and record.kind in RECORD_KINDS, record
        assert record.line.startswith(starts), record.line


def test_a_track_whose_reads_agreed_is_not_called_disagreeing() -> None:
    assert (
        reads_disagree(replace(_verified(1), rip_count=2, secure_rerip_converged=True))
        is False
    )
    assert reads_disagree(_verified(1)) is None  # one read: nothing to compare
    assert track_record(_verified(1), chased=True).kind == RECORD_CHASE


# --- the .31 seam ---------------------------------------------------------------


def test_the_31_seam_is_named_and_never_guessed() -> None:
    """`.31`'s log text is read (2026-11-11, its contract filed), so a `.31` re-read
    the rule did not end says so plainly; a re-read from a LATER build we have not
    read says whether it applied is not determined. `.31`'s own lines are held in
    `tests/test_cyanrip_dot31_reread_until_accuraterip.py`."""
    assert AR_GUIDED_CONVERGENCE_BUILDS == frozenset({31})
    assert fork_build_number("cyanrip 0.9.4-rc3+platterpus.31") == 31
    assert fork_build_number("cyanrip 0.9.3") is None
    reread = replace(_verified(1), rip_count=3, secure_rerip_converged=True)
    assert ar_guided_convergence(reread, "cyanrip 0.9.4-rc3+platterpus.30") is False
    assert ar_guided_convergence(reread, "cyanrip 0.9.4-rc3+platterpus.31") is False
    assert ar_guided_convergence(reread, "cyanrip 0.9.4-rc3+platterpus.32") is None
    later = track_record(reread, ripper_version="cyanrip 0.9.4-rc3+platterpus.32")
    assert later.kind == RECORD_REREAD
    assert (
        "whether the fork's .31 AccurateRip-guided -Z rule chose this read is not determined"
        in later.line
    )
    for read_build in ("30", "31"):
        record = track_record(reread, ripper_version=f"x+platterpus.{read_build}")
        assert "not determined" not in record.line, read_build
    # A first read cannot have been chosen by a -Z rule, so it carries no caveat.
    assert (
        ".31" not in track_record(_verified(1), ripper_version="x+platterpus.32").line
    )


def test_track_record_never_raises_on_junk() -> None:
    class Junk:
        number = "five"
        rip_count = "many"
        secure_rerip_converged = "maybe"
        other_reads = 7
        test_crc = 3

    record = track_record(Junk())
    assert record.kind in RECORD_KINDS


# --- expect-track-records: the grader ------------------------------------------------


def _album(
    tmp_path: Path, rip_log: RipLog, ctdb: object | None
) -> tuple[dict[str, Any], Path]:
    report = json.loads(
        json.dumps(build_report(rip_log, ctdb_result=ctdb), default=str)
    )
    (tmp_path / "rip (EAC-compatible).log").write_text(
        render_eac_style_log(rip_log, ctdb_result=ctdb), "utf-8"
    )
    return report, tmp_path


def _repaired_and_asked() -> CtdbVerifyResult:
    """:func:`_repaired_result` once AccurateRip was asked (G2, TASKS R138).

    The grader also grades G2, which a repair nobody asked AccurateRip about can
    only block (``tests/test_repair_accuraterip.py``); the G3 cases here give it
    the reference disc's synthesised answer, in which v2 matches.
    """
    from test_accuraterip_db import DISC, TRACKS, reference_dbar

    from platterpus.adapters.accuraterip_db import AccurateRipHttpImpl
    from platterpus.ctdb.repair_accuraterip import with_accuraterip

    result = _repaired_result()
    lookup = AccurateRipHttpImpl(fetcher=lambda _u: reference_dbar()).lookup(
        DISC, TRACKS
    )
    assert result.repair is not None
    return replace(result, repair=with_accuraterip(result.repair, lookup))


def test_the_grader_passes_the_owners_repaired_album(tmp_path: Path) -> None:
    report, folder = _album(
        tmp_path, _log(_verified(4), _track5()), _repaired_and_asked()
    )
    grade = grade_track_records(report, folder)
    assert grade.passed and not grade.blocked, grade.detail
    assert (
        "repaired from CTDB: [5]" in grade.detail and "2 track records" in grade.detail
    )


def test_the_grader_fails_accurately_ripped_on_a_repaired_track(tmp_path: Path) -> None:
    """The subject is ctdb.repair, not the Record row: a log written before the
    repair landed (no Record saying so) and edited to vouch for track 5 fails."""
    report, folder = _album(tmp_path, _log(_verified(4), _track5()), _repaired_result())
    log = folder / "rip (EAC-compatible).log"
    text = render_eac_style_log(_log(_verified(4), _track5()))  # before the repair
    log.write_text(
        text.replace(
            "Cannot be verified as accurate", "Accurately ripped (confidence 200)"
        ),
        "utf-8",
    )
    grade = grade_track_records(report, folder)
    assert not grade.passed and not grade.blocked
    assert (
        "track 5 was repaired from CTDB and its EAC-layout block says Accurately ripped"
        in grade.detail
    )
    assert "its Record: row does not say so" in grade.detail


def test_the_grader_fails_ok_over_reads_that_disagree(tmp_path: Path) -> None:
    other = OtherRead(state="read", text="", crc="4065BECC", count=1, where="not_known")
    track = replace(
        _verified(3), rip_count=4, secure_rerip_converged=True, other_reads=(other,)
    )
    report, folder = _album(tmp_path, _log(track), None)
    log = folder / "rip (EAC-compatible).log"
    log.write_text(
        log.read_text("utf-8").replace(DISAGREED_VERIFIED_VERDICT, "Copy OK"), "utf-8"
    )
    grade = grade_track_records(report, folder)
    assert not grade.passed
    assert (
        "track 3 had reads that disagree and its status line says 'Copy OK'"
        in grade.detail
    )


def test_the_grader_reads_the_report_alone_when_there_is_no_eac_log(
    tmp_path: Path,
) -> None:
    report = json.loads(
        json.dumps(
            build_report(_log(_track5()), ctdb_result=_repaired_and_asked()),
            default=str,
        )
    )
    grade = grade_track_records(report, tmp_path)
    assert grade.passed, grade.detail
    assert "no EAC-layout log in the folder" in grade.detail


def test_the_grader_never_passes_a_report_without_records(tmp_path: Path) -> None:
    report = json.loads(json.dumps(build_report(_log(_verified(1))), default=str))
    for track in report["tracks"]:
        del track["record"]
    assert grade_track_records(report, tmp_path).blocked
    assert grade_track_records({"tracks": []}, tmp_path).blocked


def test_the_grader_fails_a_report_record_that_hides_the_repair(tmp_path: Path) -> None:
    report = json.loads(
        json.dumps(
            build_report(_log(_track5()), ctdb_result=_repaired_result()), default=str
        )
    )
    report["tracks"][0]["record"].update(kind=RECORD_NOT_VERIFIED, repaired=False)
    grade = grade_track_records(report, tmp_path)
    assert not grade.passed
    assert (
        "track 5 was repaired from CTDB and its report record reads 'not_verified'"
        in grade.detail
    )


# --- expect-track-records: through the real runner --------------------------------


def test_expect_track_records_runs_through_the_runner(
    qapp: Any, process_until: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The verb is registered, handled and graded from the rip's own folder:
    BLOCKED on a report before schema 45, PASS once each track has a record, and
    FAIL when ctdb.repair names a track whose record hides the repair."""
    pytest.importorskip("PySide6.QtWidgets")
    from test_uiscript_artifact_verbs import _load, _rip, _run

    from platterpus.uiscript import artifact_verbs
    from platterpus.uiscript.report import Outcome

    monkeypatch.setattr(artifact_verbs, "ARTIFACT_WAIT_S", 0.5)
    verb = "expect-track-records"
    old = _run(_rip(tmp_path / "a", _load("overwrite")), qapp, process_until, verb)
    assert old.outcome is Outcome.BLOCKED, old.detail

    report = _load("overwrite")
    for track in report["tracks"]:
        track["record"] = {
            "kind": RECORD_FIRST_READ,
            "line": "first read; verified by AccurateRip v2 at confidence 200",
            "reads_disagree": None,
            "repaired": False,
        }
    ok = _run(_rip(tmp_path / "b", report), qapp, process_until, verb)
    assert ok.outcome is Outcome.PASS, ok.detail

    report["ctdb"] = {"repair": {"status": "repaired", "tracks": [{"track": 1}]}}
    bad = _run(_rip(tmp_path / "c", report), qapp, process_until, verb)
    assert bad.outcome is Outcome.FAIL, bad.detail
    assert "track 1 was repaired from CTDB" in bad.detail


def test_expect_track_records_reads_the_eac_layout_log_in_the_rips_folder(
    qapp: Any, process_until: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The regression of round 39's test burn (2026-11-11): through the real
    runner, the step graded the report alone and said "no EAC-layout log in the
    folder" on all five rips, while each folder held one. The runner hands the
    grader the REPORT FILE's path and the grader searched it as a folder. Here
    the report is clean and only the EAC-layout log says `Copy OK` over reads
    that disagree, so only a step that reads the log can fail it."""
    pytest.importorskip("PySide6.QtWidgets")
    from test_uiscript_artifact_verbs import _load, _rip, _run

    from platterpus.uiscript import artifact_verbs
    from platterpus.uiscript.report import Outcome
    from platterpus.uiscript.track_record_grading import EAC_LOG_SUFFIX

    monkeypatch.setattr(artifact_verbs, "ARTIFACT_WAIT_S", 0.5)
    report = _load("overwrite")
    for track in report["tracks"]:
        track["record"] = {
            "kind": RECORD_FIRST_READ,
            "line": "first read; verified by AccurateRip v2 at confidence 200",
            "reads_disagree": None,
            "repaired": False,
        }
    report["tracks"][0]["record"]["reads_disagree"] = True
    numbers = [t["number"] for t in report["tracks"]]
    win = _rip(tmp_path / "eac", report)
    folder = tmp_path / "eac" / "album"
    blocks = []
    for n in numbers:
        status = "Copy OK" if n == numbers[0] else "Copy finished"
        blocks.append(f"Track {n:2d}\n\n     Record: first read\n\n     {status}\n")
    (folder / f"album{EAC_LOG_SUFFIX}").write_text("\n".join(blocks), "utf-8")

    step = _run(win, qapp, process_until, "expect-track-records")
    assert step.outcome is Outcome.FAIL, step.detail
    assert "status line says 'Copy OK'" in step.detail, step.detail
    assert "no EAC-layout log in the folder" not in step.detail, step.detail
