"""cyanrip's `C2 errors:` line, read as a DECLARATION, in every wording (round 39 lap 3 S14).

The fork's lap 3 S14: their header line `C2 errors:      unsupported by drive`
repeats the drive's capabilities page (MODE SENSE 2Ah) as a fact about the drive,
and their C2 probe of 2026-11-11 (S11, filed at `cyanrip@74b6f0a`) found the
BDR-209D returns C2 pointers its page does not declare. They propose, for a later
build, `not declared by drive (capabilities page, not measured)` and `declared
supported by drive (capabilities page), not used`, the failed-query form
unchanged. Our reader takes both now, before any build prints them, and reads the
old and new spelling of each branch into ONE state about the page
(`c2_declaration.py`).

**Where the lines come from.** Each case is the fork's golden reference
(`tests/fixtures/cyanrip_fork_golden_reference_r36.log`, `cyanrip@cef0f629:docs/
golden-reference.log` byte for byte) with the `C2 errors:` VALUE replaced by the
string the source prints, cited beside each case: the fork's
`cyanrip@54d66666:src/drive_caps.c:117-122`, upstream's
`cyanrip@648b1ddd:src/cyanrip_log.c:275-276`, and the proposal's text from
`docs/handshake/inbound/round-39-lap-03.md` (S14), copied, not built from our table.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus import c2_declaration
from platterpus.c2_declaration import (
    C2_DECLARED_STATES,
    c2_declaration_state,
    c2_used,
)
from platterpus.eac_log_export import render_eac_style_log
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import (
    DRIVE_FACT_NOT_PRESENT,
    DRIVE_FACT_UNRECOGNISED,
    RipLog,
)
from platterpus.rip_report import build_report

_R36_LOG = Path(__file__).parent / "fixtures" / "cyanrip_fork_golden_reference_r36.log"
# cyanrip@cef0f629:docs/golden-reference.log:12, as the fork prints it.
_C2_LINE = "C2 errors:      unsupported by drive\n"
# The fork's format string, `cyanrip@54d66666:src/cyanrip_log.c:1268`.
_C2_FORMAT = "C2 errors:      %s\n"
_LAP3 = Path(__file__).parents[1] / "docs/handshake/inbound/round-39-lap-03.md"

# The two proposed wordings, verbatim from the fork's lap 3 S14.
_PROPOSED_NOT_DECLARED = "not declared by drive (capabilities page, not measured)"
_PROPOSED_DECLARED = "declared supported by drive (capabilities page), not used"


def _with_c2(value: str) -> str:
    """The golden reference with its `C2 errors:` value replaced."""
    text = _R36_LOG.read_text(encoding="utf-8")
    assert text.count(_C2_LINE) == 1  # floor: the anchor is there, once
    return text.replace(_C2_LINE, _C2_FORMAT % value, 1)


def _c2_row(value: str) -> str:
    """The EAC-layout log's `Make use of C2 pointers` row for that value."""
    rows = [
        line
        for line in render_eac_style_log(
            parse_cyanrip_log(_with_c2(value))
        ).splitlines()
        if line.startswith("Make use of C2 pointers")
    ]
    assert len(rows) == 1, rows
    return rows[0]


def test_the_proposed_wordings_are_the_ones_the_fork_sent() -> None:
    """Our copies of S14's two wordings are in the lap as filed, so the reader is
    checked against their text and not against our memory of it."""
    lap = _LAP3.read_text(encoding="utf-8")
    s14 = next(line for line in lap.splitlines() if line.startswith("S14 ASK:"))
    assert f"`C2 errors:      {_PROPOSED_NOT_DECLARED}`" in s14
    assert f"`C2 errors:      {_PROPOSED_DECLARED}`" in s14


@pytest.mark.parametrize(
    ("value", "state", "reason", "used"),
    [
        # upstream, cyanrip@648b1ddd:src/cyanrip_log.c:275-276
        ("supported by drive", "declared_supported", "", None),
        # upstream and the fork today, cyanrip@54d66666:src/drive_caps.c:121
        ("unsupported by drive", "not_declared", "", False),
        # the fork today, drive_caps.c:121
        ("supported by drive, not used", "declared_supported", "", False),
        # the fork today and unchanged by the proposal, drive_caps.c:120
        (
            "unknown (capabilities query failed)",
            "unknown",
            "capabilities query failed",
            None,
        ),
        # PROPOSED, round 39 lap 3 S14 (not built)
        (
            _PROPOSED_NOT_DECLARED,
            "not_declared",
            "capabilities page, not measured",
            False,
        ),
        # PROPOSED, round 39 lap 3 S14 (not built)
        (_PROPOSED_DECLARED, "declared_supported", "capabilities page", False),
    ],
)
def test_each_c2_wording_is_read(
    value: str, state: str, reason: str, used: bool | None
) -> None:
    info = parse_cyanrip_log(_with_c2(value)).ripping_info
    assert (info.c2_declared, info.c2_declared_reason, info.c2_pointers) == (
        state,
        reason,
        used,
    )


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("unsupported by drive", _PROPOSED_NOT_DECLARED),
        ("supported by drive, not used", _PROPOSED_DECLARED),
    ],
)
def test_a_relabelling_does_not_change_the_answer(old: str, new: str) -> None:
    """The proposal rewords a branch; it does not change what the branch is. So
    the state, EAC's answer and the rendered row are the same for both spellings,
    a relation no test of either spelling alone can state."""
    a = parse_cyanrip_log(_with_c2(old)).ripping_info
    b = parse_cyanrip_log(_with_c2(new)).ripping_info
    assert a.c2_declared == b.c2_declared
    assert a.c2_pointers == b.c2_pointers is False
    assert _c2_row(old) == _c2_row(new) == "Make use of C2 pointers : No"


@pytest.mark.parametrize(
    "value",
    [
        "supported by drive",
        "unsupported by drive",
        "supported by drive, not used",
        "unknown (capabilities query failed)",
        _PROPOSED_NOT_DECLARED,
        _PROPOSED_DECLARED,
    ],
)
def test_the_eac_row_never_says_the_drive_cannot_or_that_c2_was_used(
    value: str,
) -> None:
    """EAC's row asks whether the rip USED C2. Ours answers No or not reported,
    and never carries the ripper's capability word into it."""
    row = _c2_row(value)
    assert row in {
        "Make use of C2 pointers : No",
        "Make use of C2 pointers : (not reported by the ripper)",
    }
    assert "Yes" not in row and "unsupported" not in row and "cannot" not in row


def test_an_unrecognised_wording_is_kept_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A reword claims its line but is not squeezed into a state: `measured
    unsupported` is not `not_declared`, whatever it resembles."""
    with caplog.at_level("WARNING", logger="platterpus.c2_declaration"):
        info = parse_cyanrip_log(_with_c2("measured absent by drive")).ripping_info
    assert info.c2_declared == DRIVE_FACT_UNRECOGNISED
    assert info.c2_declared_reason == "measured absent by drive"
    assert info.c2_pointers is None
    assert any("C2 errors:" in r.getMessage() for r in caplog.records)


def test_an_unrecognised_wording_keeps_the_old_negative_reading() -> None:
    """A reword never turns an earned "No" into a guess: the substring reading
    the parser had before this module still answers for a wording we do not know."""
    assert c2_declaration_state("C2 disabled")[0] == DRIVE_FACT_UNRECOGNISED
    assert c2_used("C2 disabled") is False
    assert c2_used("not supported") is False
    assert c2_used("something else entirely") is None


def test_no_line_is_not_present_and_says_nothing_about_the_drive() -> None:
    text = _R36_LOG.read_text(encoding="utf-8").replace(_C2_LINE, "", 1)
    info = parse_cyanrip_log(text).ripping_info
    assert (info.c2_declared, info.c2_declared_reason, info.c2_pointers) == (
        DRIVE_FACT_NOT_PRESENT,
        "",
        None,
    )
    assert RipLog().ripping_info.c2_declared == DRIVE_FACT_NOT_PRESENT


def test_the_states_are_spelled_as_the_other_drive_facts() -> None:
    """One word means one thing in the report's `rip` block."""
    assert c2_declaration.C2_NOT_PRESENT == DRIVE_FACT_NOT_PRESENT
    assert c2_declaration.C2_UNRECOGNISED == DRIVE_FACT_UNRECOGNISED


def test_the_report_carries_the_declaration() -> None:
    rip = build_report(parse_cyanrip_log(_with_c2(_PROPOSED_NOT_DECLARED)))["rip"]
    assert rip["c2_declared"] == "not_declared"
    assert rip["c2_declared_reason"] == "capabilities page, not measured"
    assert rip["c2_pointers"] is False
    plain = build_report(parse_cyanrip_log(_with_c2("unsupported by drive")))["rip"]
    assert (plain["c2_declared"], plain["c2_declared_reason"]) == ("not_declared", None)
    absent = build_report(RipLog())["rip"]
    assert absent["c2_declared"] == DRIVE_FACT_NOT_PRESENT


@given(st.text(max_size=400))
def test_the_c2_readers_never_raise(value: str) -> None:
    """Parsers of external output never raise (Code conventions), and neither
    ever answers EAC's "Yes"."""
    state, reason = c2_declaration_state(value)
    assert state in C2_DECLARED_STATES and state != DRIVE_FACT_NOT_PRESENT
    assert isinstance(reason, str) and len(reason) < 400
    assert c2_used(value) in (False, None)
