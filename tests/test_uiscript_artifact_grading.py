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
from platterpus.uiscript import expected_warnings

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


def _without_the_retired_recompress_keys(report: dict[str, Any]) -> dict[str, Any]:
    """`report` as schema v33 writes it: the four re-compress keys gone."""
    stripped = copy.deepcopy(report)
    del stripped["settings"]["recompress_flac_after_rip"]
    stripped["settings"].get("every_setting", {}).pop("recompress_flac_after_rip", None)
    del stripped["verification"]["gates"]["recompress"]
    del stripped["verification"]["recompress"]
    return stripped


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("wholedisc", g.SETTLE_SETTLED),
        # The Archival rip: its gate read "backend already maxes compression",
        # the one value a reader that matched on gate strings could trip over.
        ("securereread", g.SETTLE_SETTLED),
        ("cancelme", g.SETTLE_UNFINISHED),
    ],
)
def test_settle_state_reads_a_report_the_same_with_or_without_the_recompress_keys(
    name: str, expected: str
) -> None:
    """Schema v33 removed the re-compress keys (2026-10-07). Every report filed
    before that — these committed round-29 ones among them — still carries them,
    and the reports written from now on do not. The one predicate every artifact
    verb asks "is this record final?" must give the same answer for both shapes.
    """
    old = _report(name)
    # Floor: the committed report really is the old shape, or this would compare
    # a report with itself.
    assert "recompress" in old["verification"]["gates"]
    assert "recompress" in old["verification"]
    assert "recompress_flac_after_rip" in old["settings"]
    new = _without_the_retired_recompress_keys(old)
    assert "recompress" not in new["verification"]["gates"]
    assert g.settle_state(old) == expected
    assert g.settle_state(new) == expected


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


# --- the open-round warning on the build under review (2026-10-06) -------------

_ROUND30 = _ROUND29.parent / "artifactsround30"

#: The finished rips of round 30's closing run. Each failed `expect-album-audit`
#: on the handshake check's open-round warning alone (transcript lines 441 to
#: 1083), so each is the real case the narrowing is for.
_CLOSING_RUN_RIPS = (
    "wholedisc",
    "overwrite",
    "derivedwav",
    "derivedmp3",
    "derivedwavpack",
    "securereread",
    "permutations",
    "aftercancel",
)


def _closing_report(name: str) -> dict[str, Any]:
    loaded = json.loads(
        (_ROUND30 / f"round30oct06full{name}report.json").read_text("utf-8")
    )
    assert isinstance(loaded, dict)
    return loaded


@pytest.fixture
def reviewing_5704062(monkeypatch: pytest.MonkeyPatch) -> None:
    """The handshake state the closing run was graded in: round 30 reviewing
    `5704062` while `51cc789` is the approved pin. Pinned here so these tests
    describe that run, and do not change meaning when round 30 closes."""
    from platterpus.deps import fork_source

    monkeypatch.setattr(fork_source, "PIN_UNDER_REVIEW", "5704062")
    monkeypatch.setattr(fork_source, "PIN_UNDER_REVIEW_ROUND", 30)
    monkeypatch.setattr(fork_source, "FORK_PIN", "51cc789")


@pytest.mark.usefixtures("reviewing_5704062")
@pytest.mark.parametrize("name", _CLOSING_RUN_RIPS)
def test_the_closing_runs_rips_fail_without_the_report_and_pass_with_it(
    tmp_path: Path, name: str
) -> None:
    """Regression (round 30's closing run): the warning failed every rip by
    construction. With the report, the grader can see the binary is the build
    under review, and the passing sentence says why the warning was expected."""
    report = _closing_report(name)
    path = _album(tmp_path, report)
    without = g.grade_album_audit(path)
    assert not without.passed
    assert without.detail.startswith("handshake_note warned:"), without.detail
    assert ";" not in without.detail  # that warning, and nothing else
    graded = g.grade_album_audit(path, (), report)
    assert graded.passed, graded.detail
    assert "expected on the build under review" in graded.detail
    assert "platterpus-fork-g5704062" in graded.detail


@pytest.mark.usefixtures("reviewing_5704062")
def test_the_product_audit_still_warns_on_the_build_under_review(
    tmp_path: Path,
) -> None:
    """Only the acceptance grader expects the warning. A user ripping with an
    unreleased build is still told, by the product's own audit."""
    album = rip_audit.audit_album(_album(tmp_path, _closing_report("wholedisc")))
    warned = [
        f.text
        for f in album.by_check["handshake_note"]
        if f.level == rip_audit.LEVEL_WARN
    ]
    assert len(warned) == 1 and warned[0].startswith(rip_audit.OPEN_ROUND_WARNING)


@pytest.mark.usefixtures("reviewing_5704062")
@pytest.mark.parametrize(
    ("field", "value", "why"),
    [
        ("ripper_build", "platterpus-fork-g174a134", "another build"),
        ("ripper_build", "platterpus-fork-g5704062-dirty", "a dirty build"),
        ("ripper_build", "someone-else-g5704062", "another fork's id"),
        ("ripper_handshake_approval", "approved", "our verdict disagrees"),
        ("ripper_handshake_approval", "not_determined", "no verdict"),
        (
            "ripper_handshake_note",
            "round 29 lap 3 OPEN, verdict OPEN -- NOT a released build",
            "a different round",
        ),
    ],
)
def test_the_warning_is_a_failure_unless_every_condition_holds(
    tmp_path: Path, field: str, value: str, why: str
) -> None:
    """Each condition, broken alone, leaves the warning a failure: a label is
    never enough without the binary it describes."""
    report = _closing_report("wholedisc")
    report["rip"][field] = value
    assert expected_warnings.expected_open_round_warning(report) == "", why
    grade = g.grade_album_audit(_album(tmp_path, report), (), report)
    assert not grade.passed, why
    assert "handshake_note warned" in grade.detail


def test_the_warning_is_a_failure_once_no_round_is_reviewing_the_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After round 30 closes, `5704062` is the approved pin, not a build under
    review, and a binary still calling itself unreleased is a real finding."""
    from platterpus.deps import fork_source

    monkeypatch.setattr(fork_source, "PIN_UNDER_REVIEW", "5704062")
    monkeypatch.setattr(fork_source, "PIN_UNDER_REVIEW_ROUND", 30)
    monkeypatch.setattr(fork_source, "FORK_PIN", "5704062")
    report = _closing_report("wholedisc")
    assert expected_warnings.expected_open_round_warning(report) == ""
    assert not g.grade_album_audit(_album(tmp_path, report), (), report).passed


@pytest.mark.usefixtures("reviewing_5704062")
def test_the_expectation_never_raises_on_a_malformed_report() -> None:
    for bad in (None, {}, {"rip": None}, {"rip": {"ripper_build": 7}}, {"rip": []}):
        assert expected_warnings.expected_open_round_warning(bad) == ""  # type: ignore[arg-type]  # malformed on purpose


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
