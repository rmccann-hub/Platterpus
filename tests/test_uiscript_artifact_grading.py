"""The acceptance script's graders, against the rip reports we actually have.

Every "passes" case below is a COMMITTED round-29 Full-run report
(`docs/handshake/artifactsround29/`), because `CLAUDE.md` says a test should read
the artifact when one can settle the question: a fixture shaped like a report is
our belief about a report. The "fails" cases are those same reports with one
field changed, so each failure is the only difference from a real pass.
"""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from platterpus import rip_audit
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.uiscript import artifact_grading as g

_ROUND29 = Path(__file__).resolve().parent.parent / "docs/handshake/artifactsround29"


def _report(name: str) -> dict[str, Any]:
    loaded = json.loads((_ROUND29 / f"round29full{name}report.json").read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _album(tmp_path: Path, report: dict[str, Any], *, with_audio: bool = True) -> Path:
    """An album folder holding `report`, and a stand-in file per ripped track.

    The stand-ins are NOT audio: filler bytes past the audit's size floor, named
    as the report names the tracks, so the audio-file check can count them. Real
    audio never enters the repository or a test (Critical rule #8).
    """
    folder = tmp_path / "album"
    folder.mkdir()
    path = folder / "rip.platterpus.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    if with_audio:
        for track in report.get("tracks") or []:
            name = Path(str(track.get("filename") or "")).name
            if name:
                (folder / name).write_bytes(
                    b"\0" * (rip_audit.MIN_PLAUSIBLE_TRACK_BYTES + 1)
                )
    return path


# --- settle_state ---------------------------------------------------------------


def test_the_settle_states_are_read_from_the_report_itself() -> None:
    assert g.settle_state(None) == g.SETTLE_ABSENT
    assert g.settle_state(_report("wholedisc")) == g.SETTLE_SETTLED
    assert g.settle_state(_report("cancelme")) == g.SETTLE_UNFINISHED
    in_progress = _report("wholedisc")
    in_progress["outcome"]["status"] = "in_progress"  # rip_worker's incremental write
    assert g.settle_state(in_progress) == g.SETTLE_PENDING
    dropped = _report("wholedisc")
    dropped["issues"].append(
        {"code": "verification_result_missing", "severity": "warning"}
    )
    assert g.settle_state(dropped) == g.SETTLE_PENDING


# --- expect-album-audit ---------------------------------------------------------


@pytest.mark.parametrize(
    "name", ["wholedisc", "overwrite", "derivedwav", "securereread"]
)
def test_every_finished_round29_rip_passes_the_whole_audit(
    tmp_path: Path, name: str
) -> None:
    """The floor, measured: every check ran and reached ok on every finished rip."""
    grade = g.grade_album_audit(_album(tmp_path, _report(name)))
    assert grade.passed, grade.detail
    assert f"all {len(rip_audit.CHECKS)} audit check(s)" in grade.detail


def test_a_missing_audio_file_fails_the_audit(tmp_path: Path) -> None:
    grade = g.grade_album_audit(
        _album(tmp_path, _report("overwrite"), with_audio=False)
    )
    assert not grade.passed and "audio_files" in grade.detail


def test_a_cancelled_rip_fails_the_whole_audit_but_passes_the_log_check(
    tmp_path: Path,
) -> None:
    """§I's question after a cancel is only whether cyanrip signed off its log."""
    path = _album(tmp_path, _report("cancelme"))
    whole = g.grade_album_audit(path)
    assert not whole.passed and "completion warned" in whole.detail
    assert g.grade_album_audit(path, ["ripper_log_integrity"]).passed


def test_a_rejected_ripper_log_fails(tmp_path: Path) -> None:
    report = _report("overwrite")
    report["ripper_log_verification"]["verdict"] = "failed"
    grade = g.grade_album_audit(_album(tmp_path, report), ["ripper_log_integrity"])
    assert not grade.passed and "ripper_log_integrity warned" in grade.detail


def test_a_check_that_reached_only_not_determined_verified_nothing(
    tmp_path: Path,
) -> None:
    """No EAC log written: the checksum check notes, and a note is not a pass."""
    report = _report("overwrite")
    del report["artifacts"]["eac_log"]
    grade = g.grade_album_audit(_album(tmp_path, report), ["our_log_integrity"])
    assert not grade.passed and "verified nothing" in grade.detail


def test_an_unknown_check_name_is_refused_not_ignored(tmp_path: Path) -> None:
    grade = g.grade_album_audit(
        _album(tmp_path, _report("overwrite")), ["cue_integrty"]
    )
    assert not grade.passed and "no audit check is called cue_integrty" in grade.detail


# --- the audit's new check: the EAC-style log agrees with the ripper's ---------


def test_the_eac_log_agrees_with_the_ripper_log_on_a_real_rip() -> None:
    album = rip_audit.AlbumAudit(folder=Path("."))
    rip_audit._audit_eac_log_agreement(_report("wholedisc"), album)
    assert [(f.level, f.text) for f in album.findings] == [
        (
            "ok",
            "the EAC-style log's copy CRCs match the ripper's log on all 14 track(s)",
        )
    ]


def test_an_auto_fixed_rip_agrees_once_its_addendum_is_applied() -> None:
    """THE REGRESSION, from a committed report. Round 27's whole-disc rip re-read
    track 3; cyanrip's log keeps the discarded read's CRC, the addendum the kept
    one, and the EAC-style log was rendered from the kept one. Compared without
    the addendum, track 3 disagrees."""
    loaded = json.loads(
        (
            _ROUND29.parent / "artifactsround27/round27fullwholediscreport.json"
        ).read_text("utf-8")
    )
    assert loaded["artifacts"]["addendum"]["text"], "the fixture lost its addendum"
    album = rip_audit.AlbumAudit(folder=Path("."))
    rip_audit._audit_eac_log_agreement(loaded, album)
    assert [f.level for f in album.findings] == ["ok"], album.findings


def test_an_eac_log_with_a_changed_crc_is_a_warning() -> None:
    report = _report("wholedisc")
    eac = report["artifacts"]["eac_log"]
    assert "Copy CRC B0D122E7" in eac["text"]  # track 1's, as the ripper computed it
    eac["text"] = eac["text"].replace("Copy CRC B0D122E7", "Copy CRC 00000000")
    album = rip_audit.AlbumAudit(folder=Path("."))
    rip_audit._audit_eac_log_agreement(report, album)
    assert (
        album.findings[0].level == "warn" and "on track(s) 1" in album.findings[0].text
    )


# --- expect-accuraterip ---------------------------------------------------------


def _log(report: dict[str, Any]) -> object:
    return parse_cyanrip_log(report["artifacts"]["rip_log"]["text"])


def test_accuraterip_passes_a_real_rip_and_names_the_one_frame_tracks() -> None:
    report = _report("wholedisc")
    grade = g.grade_accuraterip(_log(report), report)
    assert grade.passed, grade.detail
    assert "offset-variant: 3, 5" in grade.detail  # the rig disc's two marginal tracks


def test_accuraterip_fails_when_the_report_disagrees_with_the_log() -> None:
    report = _report("wholedisc")
    report["tracks"][0]["accuraterip_verified"] = False
    grade = g.grade_accuraterip(_log(report), report)
    assert not grade.passed and "disagree about whether track(s) 1" in grade.detail


def test_accuraterip_fails_when_no_lookup_happened() -> None:
    report = _report("overwrite")
    text = report["artifacts"]["rip_log"]["text"]
    lines = [line for line in text.splitlines() if "Accurip" not in line]
    grade = g.grade_accuraterip(parse_cyanrip_log("\n".join(lines) + "\n"), report)
    assert not grade.passed and "gave no answer" in grade.detail


# --- expect-ctdb ----------------------------------------------------------------


def test_ctdb_whole_passes_a_whole_disc_and_partial_passes_a_partial() -> None:
    assert g.grade_ctdb(_report("wholedisc"), "whole").passed
    assert g.grade_ctdb(_report("overwrite"), "partial").passed


def test_ctdb_fails_the_wrong_scope_either_way() -> None:
    """A partial rip looked up is the 2026-09-28 defect; a whole disc declined is a skip."""
    assert not g.grade_ctdb(_report("wholedisc"), "partial").passed
    assert not g.grade_ctdb(_report("overwrite"), "whole").passed


def test_ctdb_fails_a_lookup_error_and_a_missing_block() -> None:
    report = _report("wholedisc")
    broken = copy.deepcopy(report)
    broken["ctdb"]["verdict"] = "lookup_error"
    assert not g.grade_ctdb(broken, "whole").passed
    broken["ctdb"] = None
    assert "holds no CTDB result" in g.grade_ctdb(broken, "whole").detail
    assert not g.grade_ctdb(report, "some").passed


def test_the_real_reports_are_where_the_tests_say(tmp_path: Path) -> None:
    """Floor for this file: the committed artifacts exist and are what we read."""
    names = sorted(p.name for p in _ROUND29.glob("round29full*report.json"))
    assert "round29fullwholediscreport.json" in names and len(names) >= 8
    shutil.copy(
        _ROUND29 / "round29fullwholediscreport.json", tmp_path / "x.platterpus.json"
    )
    assert g.report_path(tmp_path) == tmp_path / "x.platterpus.json"
