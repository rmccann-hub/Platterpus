"""Tests for platterpus.rip_pass_exit — which pass an exit status describes."""

from __future__ import annotations

from platterpus.rip_pass_exit import (
    SECURING_EXIT_KEY,
    SECURING_STARTED_KEY,
    PassExits,
    exit_text,
    securing_fact,
)
from platterpus.rip_report import build_outcome


def test_null_is_never_shown_as_zero() -> None:
    assert exit_text(None) == "not reaped (null)"
    assert exit_text(0) == "0"
    assert securing_fact(False, None) == "did not run"
    assert securing_fact(True, None) == "not reaped (null)"
    assert securing_fact(True, 1) == "1"


def test_a_report_says_which_pass_each_code_is() -> None:
    both = PassExits.from_outcome(
        build_outcome(
            status="failed",
            ripper_exit_code=1,
            securing_pass_started=True,
            securing_pass_exit_code=0,
        )
    )
    assert both.phrase() == "album pass exit 1; securing pass exit 0"
    album_only = PassExits.from_outcome(
        build_outcome(status="failed", ripper_exit_code=1)
    )
    assert album_only.phrase() == "album pass exit 1"
    unreaped = PassExits.from_outcome(
        build_outcome(status="cancelled", securing_pass_started=True)
    )
    assert unreaped.phrase() == (
        "album pass exit not reaped (null); securing pass exit not reaped (null)"
    )


def test_an_older_report_keeps_its_old_wording() -> None:
    """Before schema v31 the code was the LAST pass's, so no pass is named."""
    old = PassExits.from_outcome({"status": "failed", "ripper_exit_code": 137})
    assert old.pass_recorded is False
    assert old.phrase() == "ripper exit 137"


def test_the_writer_and_the_reader_use_the_same_keys() -> None:
    """The relation: what `build_outcome` writes is what `PassExits` reads."""
    outcome = build_outcome(
        status="success",
        ripper_exit_code=0,
        securing_pass_started=True,
        securing_pass_exit_code=1,
    )
    assert outcome[SECURING_STARTED_KEY] is True
    assert outcome[SECURING_EXIT_KEY] == 1
    assert PassExits.from_outcome(outcome) == PassExits(
        album=0, securing_started=True, securing=1
    )


def test_a_malformed_outcome_is_not_determined_never_a_crash() -> None:
    assert PassExits.from_outcome(None).phrase() == "ripper exit not reaped (null)"
    odd = PassExits.from_outcome(
        {"ripper_exit_code": True, SECURING_STARTED_KEY: "yes", SECURING_EXIT_KEY: "1"}
    )
    # A bool is not an exit code, and a string is not a boolean.
    assert odd == PassExits(album=None, securing_started=None, securing=None)
