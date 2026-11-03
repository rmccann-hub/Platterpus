"""The graders that read a verdict the rip's report already computed.

Review of the owner's 2026-11-03 Full run (0.7.117 with cyanrip `.28`), items A3,
C1 and C3: three steps passed without checking their subject, and each time the
answer was in the report. Each "fails" case is one field of a passing shape
changed, so the failure is the only difference from a pass. The CTDB block is the
shape `rip_report._ctdb` writes (schema v38 on), with the 2026-11-03 numbers.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from platterpus.ctdb.verify import minority_match_sentence
from platterpus.read_offset_check import (
    AR_CONFIRMED,
    AR_NOT_CONFIRMED,
    OFFSET_DIFFERS,
    OFFSET_DRIVE_NOT_LISTED,
    OFFSET_MATCHES,
    OFFSET_NOT_DETERMINED,
)
from platterpus.uiscript import record_grading as rg
from platterpus.verification_gates import GATE_RAN_FAILED, GATE_RAN_PASSED

# --- A3: a CTDB match its own database outvotes ---------------------------------


def _ctdb_report(**ctdb: Any) -> dict[str, Any]:
    block: dict[str, Any] = {
        "verdict": "match",
        "confidence": 1525,
        "trustworthy": True,
        "best_confidence": 1525,
        "total_confidence": 1526,
        "outvoted": False,
        "crc_validated": True,
        "entry_count": 102,
        "message": "matched 1,525 of 1,526 CTDB submissions",
    }
    block.update(ctdb)
    return {"ctdb": block}


def _outvoted_report() -> dict[str, Any]:
    """The 2026-11-03 rip: confidence 1 against 1,524 disagreeing submissions."""
    return _ctdb_report(
        confidence=1,
        best_confidence=1524,
        total_confidence=1525,
        outvoted=True,
        trustworthy=False,
        message=minority_match_sentence(1, 1525),
    )


def test_a_plurality_match_passes_whole() -> None:
    grade = rg.grade_ctdb(_ctdb_report(), "whole")
    assert grade.passed, grade.detail
    assert "1525" in grade.detail


def test_a_match_its_own_database_outvotes_fails_whole() -> None:
    """A3: it passed, while the report said the match does not corroborate the rip."""
    grade = rg.grade_ctdb(_outvoted_report(), "whole")
    assert not grade.passed and not grade.blocked
    assert "does not corroborate the rip" in grade.detail
    assert "outvotes" in grade.detail


def test_the_outvote_is_read_from_the_confidences_when_the_flag_is_absent() -> None:
    report = _outvoted_report()
    del report["ctdb"]["outvoted"]
    report["ctdb"]["trustworthy"] = True  # only the weights say it now
    assert not rg.grade_ctdb(report, "whole").passed


def test_an_untrustworthy_match_fails_and_a_weightless_one_is_not_determined() -> None:
    untrusted = _ctdb_report(trustworthy=False)
    assert not rg.grade_ctdb(untrusted, "whole").passed
    # A report from before schema v38 carries no weight: not determined.
    old = _ctdb_report()
    for key in ("outvoted", "best_confidence", "total_confidence"):
        del old["ctdb"][key]
    grade = rg.grade_ctdb(old, "whole")
    assert not grade.passed and grade.blocked
    assert "not determined" in grade.detail


def test_a_no_match_is_still_a_determined_answer() -> None:
    """Narrowing written down: only a MATCH is weighed; a no-match is an answer."""
    report = _ctdb_report(verdict="no_match", outvoted=False)
    assert rg.grade_ctdb(report, "whole").passed


# --- C1: a gate that ran and failed ---------------------------------------------


def _gates(**gates: str) -> dict[str, Any]:
    base = {"ctdb": "ran", "flac_integrity": GATE_RAN_PASSED, "derived": "flac-only"}
    base.update(gates)
    return {"outcome": {"status": "success"}, "verification": {"gates": base}}


def test_every_gate_passed_is_no_refusal() -> None:
    assert rg.verification_refusal(_gates()) is None
    assert rg.verification_refusal(_gates(derived=GATE_RAN_PASSED)) is None


@pytest.mark.parametrize("gate", ["flac_integrity", "derived", "a_gate_added_later"])
def test_any_gate_that_ran_and_failed_is_refused(gate: str) -> None:
    report = _gates(**{gate: GATE_RAN_FAILED})
    report["verification"][gate] = {"failures": ["/x/03 - Three.flac"]}
    refused = rg.verification_refusal(report)
    assert refused is not None and "FAILED" in refused
    if gate != "derived":
        assert gate in refused and "03 - Three.flac" in refused


def test_the_refusal_never_raises_on_a_malformed_report() -> None:
    for broken in (None, {}, {"verification": 3}, {"verification": {"gates": [1]}}):
        assert rg.verification_refusal(broken) is None


# --- C3: the read offset a rip used ---------------------------------------------


def _offset_report(
    state: str = OFFSET_MATCHES,
    applied: int | None = 667,
    reconfirms: str = AR_CONFIRMED,
    sent: str | None = "667",
) -> dict[str, Any]:
    argv = ["cyanrip", "-d", "/dev/sr0"] + (["-s", sent] if sent is not None else [])
    return {
        "outcome": {"ripper_argv": argv + ["-o", "flac"]},
        "rip": {
            "read_offset_check": {
                "state": state,
                "applied": applied,
                "listed": 667,
                "detail": f"{applied}, against the drive list's +667",
                "accuraterip_reconfirms": reconfirms,
                "accuraterip_detail": "AccurateRip matched 13 of 14 tracks",
            }
        },
    }


def test_a_listed_offset_passes() -> None:
    assert rg.grade_read_offset(_offset_report()).passed


def test_a_differing_offset_fails() -> None:
    grade = rg.grade_read_offset(_offset_report(state=OFFSET_DIFFERS, applied=6))
    assert not grade.passed and not grade.blocked


def test_a_sent_offset_the_log_did_not_apply_fails() -> None:
    """A changed `-s` must not hide behind a log that reads the list's value."""
    grade = rg.grade_read_offset(_offset_report(sent="6"))
    assert not grade.passed and not grade.blocked
    assert "-s +6" in grade.detail


@pytest.mark.parametrize("state", [OFFSET_DRIVE_NOT_LISTED, OFFSET_NOT_DETERMINED])
def test_an_unlisted_drive_passes_only_when_accuraterip_confirmed_it(
    state: str,
) -> None:
    assert rg.grade_read_offset(_offset_report(state=state)).passed
    grade = rg.grade_read_offset(
        _offset_report(state=state, reconfirms=AR_NOT_CONFIRMED)
    )
    assert not grade.passed and grade.blocked  # tri-state: never a pass


def test_a_report_without_the_check_is_not_determined() -> None:
    report = _offset_report()
    del report["rip"]["read_offset_check"]
    grade = rg.grade_read_offset(report)
    assert not grade.passed and grade.blocked
    broken = copy.deepcopy(report)
    broken["rip"] = "nonsense"
    assert rg.grade_read_offset(broken).blocked


def test_sent_read_offset_reads_the_argv_as_spawned() -> None:
    assert rg.sent_read_offset(["-s", "-30"]) == -30
    assert rg.sent_read_offset(["-s"]) is None
    assert rg.sent_read_offset(["-s", "x"]) is None
    assert rg.sent_read_offset([]) is None
