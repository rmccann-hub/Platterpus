"""Who cancelled a rip (TASKS R62; the plan of record, Appendix H §3).

On 2026-10-21 disc 1's rip was cancelled by the acceptance runner when its
six-hour `wait-for-rip` ran out. The app log said "rip cancel requested by the
user" and the EAC-layout log "INTERRUPTED (you cancelled the rip)"
(`round36full1021bwholedisceac.log:325`, evidence `08de9851`). Every route to
the window's Cancel now names itself, and the app log, the report and the
EAC-layout log say who.
"""

from __future__ import annotations

import pytest

from platterpus import cancel_cause as cc
from platterpus.parsers.rip_log import RipLog
from platterpus.rip_report import build_outcome, build_report

_LIMIT = cc.CancelCause(cc.BY_TIME_LIMIT, "`wait-for-rip 21600` (L325) ran out")


def test_each_cause_has_its_own_words_and_only_the_user_is_you() -> None:
    said = {by: cc.sentence(cc.CancelCause(by)) for by in cc.CAUSES}
    assert len(set(said.values())) == len(cc.CAUSES), said
    assert said[cc.BY_USER] == "you cancelled the rip"
    assert [by for by, text in said.items() if "you " in text] == [cc.BY_USER]


@pytest.mark.parametrize("cause", [None, "user", cc.CancelCause("someone")])
def test_an_unnamed_or_unknown_cause_is_not_recorded_never_the_user(
    cause: object,
) -> None:
    assert cc.who(cause) == "a caller that did not say who it was"
    block = cc.outcome_block(cause, status="cancelled")
    assert block is not None and block["by"] == cc.NOT_RECORDED
    assert "you" not in block["sentence"]


def test_the_block_is_written_only_for_a_cancelled_rip() -> None:
    assert cc.outcome_block(cc.USER, status="success") is None
    assert cc.outcome_block(cc.USER, status="failed") is None
    block = cc.outcome_block(_LIMIT, status="cancelled")
    assert block == {
        "by": cc.BY_TIME_LIMIT,
        "detail": "`wait-for-rip 21600` (L325) ran out",
        "sentence": "the test run, whose time limit for the rip ran out "
        "(`wait-for-rip 21600` (L325) ran out) cancelled the rip",
    }


def test_a_long_detail_is_bounded_and_the_cut_is_counted() -> None:
    who = cc.who(cc.CancelCause(cc.BY_RUN_ENDED, "x" * 1000))
    assert "… [760 more]" in who and len(who) < 400


def test_the_report_says_who_in_the_outcome_and_the_issue() -> None:
    outcome = build_outcome(status="cancelled", cancelled_by=_LIMIT)
    assert outcome["cancelled_by"]["by"] == cc.BY_TIME_LIMIT
    report = build_report(RipLog(), outcome=outcome)
    issue = next(i for i in report["issues"] if i["code"] == "rip_cancelled")
    assert "time limit for the rip ran out" in issue["message"], issue
    assert build_outcome(status="success", cancelled_by=cc.USER)["cancelled_by"] is None
