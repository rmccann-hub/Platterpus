"""Plant one fault at a time in a passing rip, and require a grader to FAIL on it.

Review E1 of the owner's 2026-11-03 Full run. That run went green over steps
that passed without checking their subject (A3, C1, C3, C4), and each was found
by reading the evidence, not by a test. This file asks the question the other
way round: take a rip the graders PASS, plant exactly one fault of a kind a
real rip can carry, and assert that the grader the acceptance script runs for
that fault now fails. **Each test first asserts the clean rip passes**, so a
failure after planting is evidence about the fault, never a grader that fails
everything.

The rips are the committed round-29 whole-disc report (through its fixture,
`tests/fixtures/evidence/`, as `test_uiscript_artifact_grading` reads it) and
synthetic derived albums built from each format's layout
(`test_uiscript_derived_grading.derived_album`); no audio (Critical rule #8).

**A planted fault no grader catches is a hole, written down rather than
hidden**: it is an `xfail(strict=True)` below, naming why, so the day a
grader catches it the test turns red and is promoted.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from evidence_paths import evidence_dir
from test_flac_metadata import build_flac
from test_uiscript_derived_grading import EXPECTED, _grade, derived_album

from platterpus import rip_audit
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.uiscript import artifact_grading as ag
from platterpus.uiscript import record_grading as rg
from platterpus.uiscript import tag_grading as tg
from platterpus.verification_gates import GATE_RAN_FAILED, GATE_RAN_PASSED

_ROUND29 = evidence_dir("docs/handshake/artifactsround29")


def _wholedisc() -> dict[str, Any]:
    loaded = json.loads(
        (_ROUND29 / "round29fullwholediscreport.json").read_text("utf-8")
    )
    assert isinstance(loaded, dict)
    return loaded


def _offset_checked(report: dict[str, Any]) -> dict[str, Any]:
    """The report as schema v39 on writes it: the read-offset check present.

    Round 29 predates the block; its values here are the rig's (BDR-209D,
    +667, the list's value), and the `-s 667` is round 29's own argv.
    """
    report = copy.deepcopy(report)
    report["rip"]["read_offset_check"] = {
        "state": "matches",
        "applied": 667,
        "listed": 667,
        "detail": "+667, matches the AccurateRip drive database",
        "accuraterip_reconfirms": "confirmed",
        "accuraterip_detail": "AccurateRip matched 12 of 14 tracks",
    }
    return report


# --- the record: gates, offset, AccurateRip ---------------------------------------


def test_a_failed_gate_fails_expect_verification() -> None:
    clean = _wholedisc()
    clean["verification"]["gates"]["flac_integrity"] = GATE_RAN_PASSED
    assert rg.verification_refusal(clean) is None
    planted = copy.deepcopy(clean)
    planted["verification"]["gates"]["flac_integrity"] = GATE_RAN_FAILED
    planted["verification"]["flac_integrity"]["failures"] = ["/x/05 - Five.flac"]
    refused = rg.verification_refusal(planted)
    assert refused is not None and "05 - Five.flac" in refused


def test_a_changed_s_offset_fails_expect_read_offset() -> None:
    clean = _offset_checked(_wholedisc())
    assert rg.grade_read_offset(clean).passed
    planted = copy.deepcopy(clean)
    argv = planted["outcome"]["ripper_argv"]
    argv[argv.index("-s") + 1] = "6"
    grade = rg.grade_read_offset(planted)
    assert not grade.passed and not grade.blocked, grade.detail


def test_a_wrong_track_shown_as_verified_fails_expect_accuraterip() -> None:
    """Track 5 of round 29's whole disc did not verify; the report says it did."""
    clean = _wholedisc()
    log = parse_cyanrip_log(clean["artifacts"]["rip_log"]["text"])
    assert ag.grade_accuraterip(log, clean).passed
    planted = copy.deepcopy(clean)
    (five,) = [t for t in planted["tracks"] if t["number"] == 5]
    assert five["accuraterip_verified"] is False
    five["accuraterip_verified"] = True
    grade = ag.grade_accuraterip(log, planted)
    assert not grade.passed and "5" in grade.detail


# --- the files: tags and length ---------------------------------------------------


def test_a_stripped_flac_tag_fails_expect_tags(tmp_path: Path) -> None:
    def master(name: str, comments: list[str]) -> list[tuple[int, Path]]:
        return [(1, build_flac(tmp_path / name, comments))]

    whole = [
        f"ALBUM={EXPECTED.album}",
        f"ALBUMARTIST={EXPECTED.album_artist}",
        "TITLE=Roxanne",
        "ARTIST=A",
        "TRACKNUMBER=1",
    ]
    assert tg.grade_tags(master("a.flac", whole), EXPECTED).passed
    stripped = [c for c in whole if not c.startswith("TITLE=")]
    assert not tg.grade_tags(master("b.flac", stripped), EXPECTED).passed


@pytest.mark.parametrize(("fmt", "ext"), [("mp3", "mp3"), ("wavpack", "wv")])
def test_a_stripped_derived_tag_fails_expect_derived_files(
    tmp_path: Path, fmt: str, ext: str
) -> None:
    report = derived_album(tmp_path, fmt)
    assert _grade(report, tmp_path, fmt).passed
    path = tmp_path / f"01 - Track.{ext}"
    data = path.read_bytes()
    path.write_bytes(data.replace(b"Roxanne", b"Roxan\x00e", 1))
    grade = _grade(report, tmp_path, fmt)
    assert not grade.passed and "track 1: TITLE" in grade.detail


@pytest.mark.parametrize(
    ("fmt", "ext"), [("mp3", "mp3"), ("wavpack", "wv"), ("wav", "wav")]
)
def test_a_truncated_duration_fails_expect_derived_files(
    tmp_path: Path, fmt: str, ext: str
) -> None:
    report = derived_album(tmp_path, fmt)
    assert _grade(report, tmp_path, fmt).passed
    path = tmp_path / f"02 - Track.{ext}"
    path.write_bytes(path.read_bytes()[:-2000])
    grade = _grade(report, tmp_path, fmt)
    assert not grade.passed and "track 2" in grade.detail


# --- the holes: planted, and no grader catches them yet -----------------------------


def _audit(tmp_path: Path, report: dict[str, Any]) -> ag.Grade:
    folder = tmp_path / "album"
    folder.mkdir(parents=True)
    path = folder / "rip.platterpus.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    for track in report.get("tracks") or []:
        name = Path(str(track.get("filename") or "")).name
        (folder / name).write_bytes(b"\0" * (rip_audit.MIN_PLAUSIBLE_TRACK_BYTES + 1))
    return ag.grade_album_audit(path, ("cue_integrity",), report)


def test_the_clean_cue_check_passes_so_the_hole_below_is_about_the_fault(
    tmp_path: Path,
) -> None:
    """The xfail below needs its clean half to hold, or it xfails on setup."""
    assert _audit(tmp_path, _wholedisc()).passed


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "HOLE: the cue check (rip_audit._audit_cue_integrity, cue_validate) never "
        "reads FLAGS PRE, so a pre-emphasised track whose cue omits it passes. A "
        "correct rule needs to know whether de-emphasis was applied (section P3's "
        "subject), which neither the report nor the cue states today."
    ),
)
def test_a_missing_flags_pre_fails_the_cue_check(tmp_path: Path) -> None:
    planted = _wholedisc()
    planted["tracks"][0]["pre_emphasis"] = True  # the cue still has no FLAGS PRE
    assert not _audit(tmp_path / "planted", planted).passed
