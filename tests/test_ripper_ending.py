"""Tests for platterpus.ripper_ending — cyanrip's own record of how a rip ended (W6).

Read against the fork's own committed records, not a fixture we wrote: a reader
pinned to our belief about the record's shape would pass on a shape the fork
never emits (`CLAUDE.md`: *assert against the source artifact*).
"""

from __future__ import annotations

import json
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.rip_report import build_outcome, build_report
from platterpus.ripper_ending import (
    MAX_LABEL_CHARS,
    MAX_RECORD_BYTES,
    STATE_ABSENT,
    STATE_NOT_READ,
    STATE_NOT_REQUESTED,
    STATE_READ,
    STATE_UNREADABLE,
    STATE_UNRECOGNISED,
    RipperEnding,
    describe,
    disagreements,
    parse_ending,
    read_ending,
    status_suffix,
)

_INBOUND = Path(__file__).resolve().parents[1] / "docs/handshake/inbound/artifacts"
#: The fork's own records: a completed rip, and one stopped by SIGTERM.
_GOLDEN = _INBOUND / "round-12-lap-03-golden-reference-diagnostics-g6a23662.json"
_INTERRUPTED = _INBOUND / "round-12-lap-03-sample-interrupted-diagnostics-g6a23662.json"


def _record(**fields: object) -> str:
    """A minimal record: the fork's golden reference with fields replaced."""
    data = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    for key, value in fields.items():
        if key.startswith("rip."):
            data["rip"][key[4:]] = value
        else:
            data[key] = value
    return json.dumps(data)


# --- Reading ------------------------------------------------------------------


def test_the_forks_completed_record_reads_as_not_interrupted() -> None:
    ending = parse_ending(_GOLDEN.read_text(encoding="utf-8"))
    assert ending == RipperEnding(
        STATE_READ, exit_code=0, interrupted=False, interrupted_by=None
    )


def test_the_forks_interrupted_record_reads_who_stopped_it() -> None:
    ending = parse_ending(_INTERRUPTED.read_text(encoding="utf-8"))
    assert ending == RipperEnding(
        STATE_READ, exit_code=1, interrupted=True, interrupted_by="SIGTERM"
    )


def test_the_schema_is_recognised_by_its_prefix_never_its_number() -> None:
    """§P8a: the number after the slash is an identity, not a version to compare."""
    assert parse_ending(_record(schema="cyanrip-diagnostics/99")).state == STATE_READ
    assert parse_ending(_record(schema="other-tool/7")).state == STATE_UNRECOGNISED
    assert parse_ending(_record(schema=None)).state == STATE_UNRECOGNISED
    assert parse_ending("[1, 2]").state == STATE_UNRECOGNISED


def test_null_and_wrong_types_are_not_determined_never_false_or_zero() -> None:
    """§P8c: `exit_code` null is not 0. A field of the wrong type is not a value."""
    assert parse_ending(_record(exit_code=None)).exit_code is None
    assert parse_ending(_record(exit_code=True)).exit_code is None
    assert parse_ending(_record(exit_code="0")).exit_code is None
    assert parse_ending(_record(rip=None)).interrupted is None
    assert parse_ending(_record(**{"rip.interrupted": "no"})).interrupted is None
    missing = json.loads(_record())
    del missing["rip"]["interrupted"]
    assert parse_ending(json.dumps(missing)).interrupted is None


def test_the_label_is_screened_and_any_cut_is_counted() -> None:
    odd = parse_ending(_record(**{"rip.interrupted_by": "SIG\x1bTERM"}))
    assert odd.interrupted_by == "SIG\\x1bTERM"
    long = parse_ending(_record(**{"rip.interrupted_by": "X" * (MAX_LABEL_CHARS + 30)}))
    assert long.interrupted_by is not None
    assert long.interrupted_by.endswith("… [30 more characters]")


def test_reading_the_file_says_why_when_it_cannot(tmp_path: Path) -> None:
    assert read_ending(None).state == STATE_NOT_REQUESTED
    assert read_ending(tmp_path / "missing.json").state == STATE_ABSENT
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert read_ending(bad).state == STATE_UNREADABLE
    huge = tmp_path / "huge.json"
    huge.write_bytes(b" " * (MAX_RECORD_BYTES + 1))
    unreadable = read_ending(huge)
    assert unreadable.state == STATE_UNREADABLE and "bound" in unreadable.detail
    good = tmp_path / "good.json"
    good.write_text(_INTERRUPTED.read_text(encoding="utf-8"), encoding="utf-8")
    assert read_ending(good).interrupted_by == "SIGTERM"


@settings(max_examples=300, deadline=None)
@given(st.text())
def test_parsing_never_raises_on_any_text(text: str) -> None:
    """A parser of external output never raises (`CLAUDE.md`)."""
    assert isinstance(parse_ending(text), RipperEnding)


_JSON = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats() | st.text(),
    lambda inner: st.lists(inner) | st.dictionaries(st.text(), inner),
    max_leaves=20,
)


@settings(max_examples=300, deadline=None)
@given(exit_code=_JSON, rip=_JSON)
def test_parsing_never_raises_on_any_field_values(
    exit_code: object, rip: object
) -> None:
    text = json.dumps(
        {"schema": "cyanrip-diagnostics/7", "exit_code": exit_code, "rip": rip}
    )
    ending = parse_ending(text)
    assert ending.state == STATE_READ
    assert ending.exit_code is None or type(ending.exit_code) is int
    assert ending.interrupted in (None, True, False)


# --- Comparing with our own reading ----------------------------------------------


def _read(**kw: object) -> RipperEnding:
    return RipperEnding(STATE_READ, **kw)  # type: ignore[arg-type]  # test kwargs


def _disagree(
    ending: RipperEnding, status: str, ours: int | None, securing: bool = False
) -> list[str]:
    return disagreements(
        ending, status=status, our_exit_code=ours, securing_pass_started=securing
    )


def test_a_finished_rip_the_record_says_was_interrupted_is_said() -> None:
    found = _disagree(
        _read(exit_code=1, interrupted=True, interrupted_by="SIGTERM"), "success", 1
    )
    assert len(found) == 1
    assert "recorded the rip as finished" in found[0] and "by SIGTERM" in found[0]


def test_a_cancel_the_record_says_ran_to_the_end_is_said_unless_a_securing_pass_ran() -> (
    None
):
    """A cancel during the securing pass leaves the album record truthfully
    uninterrupted (the 2026-08-05 shape), so it is not a disagreement there."""
    ending = _read(exit_code=0, interrupted=False)
    assert len(_disagree(ending, "cancelled", -15)) == 1
    assert _disagree(ending, "cancelled", -15, securing=True) == []


def test_a_different_exit_code_is_said_except_on_a_cancel() -> None:
    """On a cancel we signalled the wrapper, so its signal death beside cyanrip's
    own exit is expected; anywhere else, both codes are named."""
    ending = _read(exit_code=1, interrupted=True, interrupted_by="SIGTERM")
    killed = _disagree(ending, "failed", 137)
    assert len(killed) == 1 and "137 (SIGKILL)" in killed[0] and "exited 1" in killed[0]
    assert _disagree(ending, "cancelled", -15) == []
    assert _disagree(_read(exit_code=1, interrupted=False), "failed", 1) == []


def test_a_record_that_was_not_read_never_disagrees() -> None:
    """Tri-state: "not determined" is not evidence against us."""
    for state in (STATE_ABSENT, STATE_UNREADABLE, STATE_NOT_REQUESTED, STATE_NOT_READ):
        assert _disagree(RipperEnding(state), "success", 0) == []
    # And the floor: the same comparison on a READ record does find one.
    assert _disagree(_read(exit_code=1, interrupted=True), "success", 0)


def test_each_reading_has_its_own_sentence() -> None:
    sentences = {
        describe(_read(exit_code=1, interrupted=True, interrupted_by="SIGTERM")),
        describe(_read(exit_code=0, interrupted=False)),
        describe(_read(exit_code=None, interrupted=None)),
        describe(RipperEnding(STATE_ABSENT)),
    }
    assert len(sentences) == 4
    assert "interrupted by SIGTERM (exit 1)" in describe(
        _read(exit_code=1, interrupted=True, interrupted_by="SIGTERM")
    )
    assert "not determined" in describe(RipperEnding(STATE_ABSENT))
    assert "exit status not recorded" in describe(_read(interrupted=False))


# --- In the report, and on the status line ------------------------------------


def test_the_report_carries_the_record_and_raises_each_disagreement() -> None:
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    outcome = build_outcome(
        status="success",
        ripper_exit_code=0,
        ripper_record=parse_ending(_INTERRUPTED.read_text(encoding="utf-8")),
    )
    block = outcome["ripper_record"]
    assert block["describes"] == "album pass"
    assert (block["state"], block["exit_code"], block["interrupted"]) == (
        STATE_READ,
        1,
        True,
    )
    assert block["interrupted_by"] == "SIGTERM"
    assert len(block["disagreements"]) == 2  # finished vs interrupted; 0 vs 1
    report = build_report(
        parse_cyanrip_log("cyanrip 0.9.3 (release)\n"), outcome=outcome
    )
    raised = [i for i in report["issues"] if i["code"] == "ripper_record_disagrees"]
    assert [i["message"] for i in raised] == block["disagreements"]
    assert {i["severity"] for i in raised} == {"warning"}


def test_a_report_given_no_reading_says_so() -> None:
    block = build_outcome(status="in_progress")["ripper_record"]
    assert block["state"] == STATE_NOT_READ
    assert block["exit_code"] is None and block["interrupted"] is None
    assert block["disagreements"] == []


def test_the_status_line_says_what_the_record_says() -> None:
    interrupted = parse_ending(_INTERRUPTED.read_text(encoding="utf-8"))
    failed = build_outcome(
        status="failed", ripper_exit_code=1, ripper_record=interrupted
    )
    assert (
        status_suffix(failed)
        == " cyanrip's own record: interrupted by SIGTERM (exit 1)."
    )
    # A success whose record agrees adds nothing; one that disagrees is marked.
    golden = parse_ending(_GOLDEN.read_text(encoding="utf-8"))
    agreeing = build_outcome(status="success", ripper_exit_code=0, ripper_record=golden)
    assert status_suffix(agreeing) == ""
    disagreeing = build_outcome(
        status="success", ripper_exit_code=1, ripper_record=interrupted
    )
    assert status_suffix(disagreeing).startswith(
        " ⚠ Platterpus recorded the rip as finished"
    )
    # Not determined is said, never left to read as "not interrupted".
    absent = build_outcome(status="failed", ripper_record=RipperEnding(STATE_ABSENT))
    assert "not determined" in status_suffix(absent)
    assert status_suffix(None) == "" and status_suffix({"status": "failed"}) == ""
