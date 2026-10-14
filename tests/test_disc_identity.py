"""TASKS P1 #1: is the disc that was ripped the disc whose tags were looked up?

Every state of the tri-state is tested here, on every surface that reports it —
the pure comparison, the JSON report (block, issue and verdict), the album audit,
the window's banner — and on the real filed run of 2026-10-13, where the disc ID
the MusicBrainz lookup was made with and the disc ID each cyanrip log reports
must MATCH. The real data is the floor: if it cannot be examined, the test fails
rather than passing on nothing.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from evidence_paths import evidence_dir
from hypothesis import given
from hypothesis import strategies as st

from platterpus.disc_identity import (
    IDENTITY_MATCH,
    IDENTITY_MISMATCH,
    IDENTITY_NOT_DETERMINED,
    MB_DISC_ID,
    check_disc_identity,
)
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.rip_audit import (
    LEVEL_NOTE,
    LEVEL_OK,
    LEVEL_WARN,
    AlbumAudit,
    _audit_disc_identity,
)
from platterpus.rip_report import build_report
from platterpus.verdict import accuraterip_verdict, apply_downgrades

#: The 2026-10-13 run, through its fixtures (HR-2 moved `artifactsround32` off
#: `main`): the cyanrip logs byte for byte, the reports as slim extracts without
#: `debug.lines`, and the app logs as slim extracts without cyanrip's progress lines,
#: which keep every MusicBrainz lookup line this file reads. `evidence_dir` refuses
#: an empty folder, so the floors below still guard the population.
_FILED = evidence_dir("docs/handshake/artifactsround32")
#: The reference disc's ID, as cyanrip printed it on the rig.
_REAL = "pNtImOkdBm9RMBIalzx0w9cfsYY-"
#: Another well-formed disc ID (a different disc of the rig's history).
_OTHER = "oMp2k.ixH0QqrdaZzsARoRS.p6c-"


def _real_log() -> Any:
    """The 2026-10-13 run's whole-disc rip, parsed by the real parser."""
    return parse_cyanrip_log(
        (_FILED / "round32fullwholedisc.log").read_text(encoding="utf-8")
    )


# --- the comparison -------------------------------------------------------------


def test_the_same_id_matches() -> None:
    check = check_disc_identity(_REAL, _REAL)
    assert check.status == IDENTITY_MATCH
    assert check.downgrade_reason == ""


def test_a_different_id_is_a_mismatch_with_both_ids_named() -> None:
    check = check_disc_identity(_OTHER, _REAL)
    assert check.status == IDENTITY_MISMATCH
    assert _OTHER in check.detail and _REAL in check.detail
    assert _OTHER in check.downgrade_reason and _REAL in check.downgrade_reason


@pytest.mark.parametrize(
    ("expected", "ripped", "says"),
    [
        (None, _REAL, "looked up for is absent"),
        ("", _REAL, "looked up for is absent"),
        ("   ", _REAL, "looked up for is absent"),
        (_REAL, None, "rip's log is absent"),
        (_REAL, "", "rip's log is absent"),
        (None, None, "absent"),
        ("not-a-disc-id", _REAL, "not shaped like a MusicBrainz disc ID"),
        (_REAL, "xxxx", "not shaped like a MusicBrainz disc ID"),
        (_REAL, 12345, "not text"),
        # One character short, and the right length with the wrong last character:
        # malformed is NEVER a mismatch, however close it is.
        (_REAL[:-1], _REAL, "not shaped"),
        (_REAL[:-1] + "A", _REAL, "not shaped"),
    ],
)
def test_an_absent_or_malformed_id_is_not_determined_never_a_verdict(
    expected: object, ripped: object, says: str
) -> None:
    check = check_disc_identity(expected, ripped)
    assert check.status == IDENTITY_NOT_DETERMINED, check
    assert says in check.detail, check.detail
    assert "not a pass" in check.detail
    assert check.downgrade_reason == ""


def test_a_quoted_malformed_value_is_bounded() -> None:
    """Inbound text is bounded before it reaches a sentence (Critical rule #12)."""
    check = check_disc_identity("x" * 5000, _REAL)
    assert len(check.detail) < 400, len(check.detail)


@given(st.one_of(st.none(), st.text(max_size=60), st.integers()), st.text(max_size=60))
def test_the_comparison_never_raises_and_only_two_good_ids_can_disagree(
    expected: object, ripped: str
) -> None:
    check = check_disc_identity(expected, ripped)
    assert check.status in {IDENTITY_MATCH, IDENTITY_MISMATCH, IDENTITY_NOT_DETERMINED}
    if check.status != IDENTITY_NOT_DETERMINED:
        assert isinstance(expected, str) and MB_DISC_ID.match(expected.strip())
        assert MB_DISC_ID.match(ripped.strip())


# --- the report -----------------------------------------------------------------


def test_the_report_records_a_match_and_leaves_the_verdict_alone() -> None:
    log = _real_log()
    report = build_report(log, disc={"unknown": False, "lookup_disc_id": _REAL})
    block = report["disc"]["identity_check"]
    assert block == {
        "status": IDENTITY_MATCH,
        "expected": _REAL,
        "ripped": _REAL,
        "detail": block["detail"],
    }
    codes = {issue["code"] for issue in report["issues"]}
    assert not {"disc_identity_mismatch", "disc_identity_not_determined"} & codes
    message, level = accuraterip_verdict(log)
    assert report["verdict"] == {"level": level, "message": message or None}


def test_a_mismatch_downgrades_the_verdict_and_raises_an_error() -> None:
    """An ARCHIVAL defect: the record must not read as clean anywhere."""
    log = _real_log()
    report = build_report(log, disc={"unknown": False, "lookup_disc_id": _OTHER})
    assert report["disc"]["identity_check"]["status"] == IDENTITY_MISMATCH
    issues = {issue["code"]: issue for issue in report["issues"]}
    assert issues["disc_identity_mismatch"]["severity"] == "error"
    assert report["verdict"]["level"] == "warn"
    assert "NOT the disc these tags were looked up for" in report["verdict"]["message"]
    assert not report["verdict"]["message"].startswith("✓")
    # The audio claim is not rewritten into a false one: a wrong disc is not
    # "not bit-perfect", so that issue is raised only if AccurateRip said so.
    _, ar_level = accuraterip_verdict(log)
    if ar_level == "ok":
        assert "not_bit_perfect" not in issues


def test_a_scan_id_with_no_log_id_is_said_in_issues() -> None:
    from platterpus.parsers.rip_log import RipLog

    report = build_report(RipLog(), disc={"unknown": False, "lookup_disc_id": _REAL})
    assert report["disc"]["identity_check"]["status"] == IDENTITY_NOT_DETERMINED
    issues = {issue["code"]: issue for issue in report["issues"]}
    assert issues["disc_identity_not_determined"]["severity"] == "info"


# --- the audit ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("lookup", "level"),
    [(_REAL, LEVEL_OK), (_OTHER, LEVEL_WARN), (None, LEVEL_NOTE), ("junk", LEVEL_NOTE)],
)
def test_the_audit_levels_each_state(lookup: str | None, level: str) -> None:
    album = AlbumAudit(folder=Path("/music/a"))
    report: dict[str, Any] = {
        "rip": {"musicbrainz_disc_id": _REAL, "cddb_id": "E20DFE0E"},
        "disc": {"lookup_disc_id": lookup},
    }
    _audit_disc_identity(report, album)
    identity = [f for f in album.findings if "looked up for" in f.text]
    assert len(identity) == 1, album.findings
    assert identity[0].level == level, identity


# --- one sentence on two surfaces -----------------------------------------------


def test_the_banner_and_the_report_word_a_mismatch_identically(qapp: Any) -> None:
    """The window downgrades its banner; the report downgrades its verdict.

    One assembly (`apply_downgrades`) and one reason (`downgrade_reason`), so the
    two must be the same sentence. Compared as a relation: no test of either side
    alone can catch them drifting apart.
    """
    del qapp
    from platterpus.ui.rip_progress import RipProgress

    log = _real_log()
    pane = RipProgress()
    pane.set_rip_log(log)
    pane.downgrade_verdict(check_disc_identity(_OTHER, _REAL).downgrade_reason)
    report = build_report(log, disc={"unknown": False, "lookup_disc_id": _OTHER})
    assert pane._verdict_banner.text() == report["verdict"]["message"]
    assert pane._verdict_banner.text().startswith("⚠")


def test_apply_downgrades_with_no_reason_changes_nothing() -> None:
    assert apply_downgrades("✓ fine", "ok", []) == ("✓ fine", "ok")
    assert apply_downgrades("✓ fine", "ok", [""]) == ("✓ fine", "ok")
    assert apply_downgrades("✓ fine", "ok", ["x"]) == ("⚠ fine — x", "warn")


# --- the real filed run: the IDs must MATCH ---------------------------------------

#: The app log's own record of which disc each MusicBrainz lookup was for.
_LOOKUP_LINE = re.compile(r"MusicBrainz returned \d+ candidates? for disc '([^']+)'")


def test_on_the_real_run_the_looked_up_disc_is_the_ripped_disc() -> None:
    """2026-10-13, our own filing: every log's disc ID against every lookup's.

    Floors: at least the eleven cyanrip logs and one lookup line, and at least
    nine reports carrying the log's ID, so "every comparison matched" cannot be
    satisfied by comparing nothing.
    """
    looked_up: set[str] = set()
    for applog in sorted(_FILED.glob("round32fullplatterpusapplog*.txt")):
        looked_up |= set(
            _LOOKUP_LINE.findall(applog.read_text(encoding="utf-8", errors="replace"))
        )
    assert looked_up, "no MusicBrainz lookup line in the filed app logs"
    compared = 0
    for path in sorted(_FILED.glob("round32full*.log")):
        if path.name.endswith("eac.log"):
            continue
        ripped = parse_cyanrip_log(path.read_text(encoding="utf-8")).disc_id
        for expected in looked_up:
            check = check_disc_identity(expected, ripped)
            assert check.status == IDENTITY_MATCH, (path.name, check.detail)
        compared += 1
    assert compared >= 11, compared
    reports = 0
    for path in sorted(_FILED.glob("round32full*report.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        ripped = (data.get("rip") or {}).get("musicbrainz_disc_id")
        if ripped is None:
            continue
        for expected in looked_up:
            assert check_disc_identity(expected, ripped).status == IDENTITY_MATCH
        reports += 1
    assert reports >= 9, reports
