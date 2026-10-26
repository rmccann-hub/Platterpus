"""Row 9 of the owner's EAC-parity plan of record (2026-10-26): one line per track
naming which proof its copy has.

EAC's log has one kind of proof, a Test and Copy CRC pair that agree. Ours varies
by track: AccurateRip at a confidence, a single re-read AccurateRip verifies (the
verified-read chase), CTDB per track, reads that agreed with no database behind
them, or none. The plan grades this row "Better once shown"; these tests hold
that it is shown, in the EAC-layout log and the report, from one function
(`track_proof.track_proof`), and that each kind is reachable.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from platterpus.ctdb.matching import CtdbTrackResult, TrackVerdict
from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
from platterpus.eac_log_export import render_eac_style_log
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import AccurateRipResult, RipLog, TrackResult
from platterpus.rip_report import build_report
from platterpus.track_proof import (
    PROOF_ACCURATERIP,
    PROOF_CTDB,
    PROOF_KINDS,
    PROOF_NONE,
    PROOF_READS_AGREE,
    PROOF_VERIFIED_REREAD,
    track_proof,
)

_REFERENCE = (
    Path(__file__).resolve().parent.parent
    / "output_reference"
    / "cyanrip_flac"
    / "cyanrip_flac_police_classics.log"
)

#: A track AccurateRip has no entry for: the lookup ran and found no disc.
_ABSENT = "not found in database"


def _reference() -> RipLog:
    return parse_cyanrip_log(_REFERENCE.read_text(encoding="utf-8", errors="replace"))


def _unknown_track(**fields: object) -> TrackResult:
    """A track on a disc AccurateRip does not hold."""
    base = TrackResult(
        number=4,
        copy_crc="0BADF00D",
        accuraterip_v1=AccurateRipResult(version=1, result="x", local_crc="AA"),
        accuraterip_lookup=_ABSENT,
    )
    return replace(base, **fields)  # type: ignore[arg-type]  # test-only field overrides


def _ctdb_row(verdict: TrackVerdict, confidence: int, strongest: int = 0) -> object:
    return CtdbTrackResult(
        track=4,
        verdict=verdict,
        confidence=confidence,
        strongest_disagreeing=strongest,
    )


def _proof_rows(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("     Proof: ")]


# --- every kind, from the one function ---------------------------------------


@pytest.mark.skipif(not _REFERENCE.exists(), reason="reference rip not present")
def test_an_accuraterip_match_names_both_versions_and_their_confidence() -> None:
    track1 = next(t for t in _reference().tracks if t.number == 1)
    proof = track_proof(track1)
    assert proof.kind == PROOF_ACCURATERIP
    assert proof.line == "AccurateRip v1 at confidence 129 and v2 at confidence 200"


@pytest.mark.skipif(not _REFERENCE.exists(), reason="reference rip not present")
def test_a_chase_read_is_named_as_a_single_verified_re_read() -> None:
    track1 = next(t for t in _reference().tracks if t.number == 1)
    proof = track_proof(track1, verified_reread=True)
    assert proof.kind == PROOF_VERIFIED_REREAD
    assert proof.line.startswith("a single re-read that AccurateRip verifies (v1 at")


def test_ctdb_per_track_is_the_proof_when_accuraterip_has_no_entry() -> None:
    proof = track_proof(_unknown_track(), ctdb_track=_ctdb_row(TrackVerdict.MATCH, 53))
    assert proof.kind == PROOF_CTDB
    assert proof.line == (
        "CTDB per track at confidence 53; AccurateRip has no entry for this track"
    )


def test_an_outvoted_ctdb_match_is_not_proof() -> None:
    """A minority entry corroborates nothing (TASKS R34)."""
    proof = track_proof(
        _unknown_track(), ctdb_track=_ctdb_row(TrackVerdict.MATCH, 2, strongest=1516)
    )
    assert proof.kind == PROOF_NONE
    assert "CTDB agrees only with a minority entry (confidence 2)" in proof.line


def test_reads_that_agreed_are_named_and_not_called_right() -> None:
    proof = track_proof(_unknown_track(secure_rerip_converged=True, rip_count=3))
    assert proof.kind == PROOF_READS_AGREE
    assert proof.line == (
        "the secure re-reads agreed (converged after 3 reads), and AccurateRip has "
        "no entry for this track, so this shows the drive read it the same way each "
        "time, not that the audio is right"
    )


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        (
            {},
            "none — AccurateRip has no entry for this track, and no second read "
            "confirms it",
        ),
        (
            {"secure_rerip_converged": False, "rip_count": 5},
            "none — AccurateRip has no entry for this track, and its re-reads did not "
            "converge",
        ),
        (
            {"accuraterip_lookup": "disabled"},
            "none — AccurateRip was not checked, and no second read confirms it",
        ),
    ],
    ids=["one-read", "did-not-converge", "not-checked"],
)
def test_no_proof_says_why(fields: dict[str, object], expected: str) -> None:
    proof = track_proof(_unknown_track(**fields))
    assert proof.kind == PROOF_NONE
    assert proof.line == expected


@pytest.mark.skipif(not _REFERENCE.exists(), reason="reference rip not present")
def test_a_contradicted_track_has_no_proof_whatever_ctdb_says() -> None:
    track3 = next(t for t in _reference().tracks if t.number == 3)
    proof = track_proof(track3, ctdb_track=_ctdb_row(TrackVerdict.MATCH, 53))
    assert proof.kind == PROOF_NONE
    assert proof.line.startswith("none — WRONG: frame 450 matches")
    assert proof.line.endswith("; CTDB's per-track entry agrees (confidence 53)")


def test_every_kind_is_reachable() -> None:
    """Non-triviality: the kinds the module declares are the kinds it returns."""
    seen = {
        track_proof(
            TrackResult(
                number=1,
                accuraterip_v2=AccurateRipResult(version=2, confidence=9),
            )
        ).kind,
        track_proof(
            TrackResult(
                number=1, accuraterip_v2=AccurateRipResult(version=2, confidence=9)
            ),
            verified_reread=True,
        ).kind,
        track_proof(_unknown_track(), ctdb_track=_ctdb_row(TrackVerdict.MATCH, 5)).kind,
        track_proof(_unknown_track(secure_rerip_converged=True)).kind,
        track_proof(_unknown_track()).kind,
    }
    assert seen == PROOF_KINDS


def test_it_never_raises_on_a_wrong_shape() -> None:
    assert track_proof(object()).kind == PROOF_NONE
    assert track_proof(None, ctdb_track=object()).kind == PROOF_NONE


# --- the surfaces --------------------------------------------------------------


@pytest.mark.skipif(not _REFERENCE.exists(), reason="reference rip not present")
def test_the_eac_layout_log_has_one_proof_row_per_track() -> None:
    rip_log = _reference()
    rows = _proof_rows(render_eac_style_log(rip_log, disc_track_total=14))
    assert len(rows) == len(rip_log.tracks) == 14
    assert rows[0] == (
        "     Proof: AccurateRip v1 at confidence 129 and v2 at confidence 200"
    )
    assert rows[2].startswith("     Proof: none — WRONG:")


@pytest.mark.skipif(not _REFERENCE.exists(), reason="reference rip not present")
def test_the_eac_layout_log_names_a_chase_read() -> None:
    text = render_eac_style_log(
        _reference(), disc_track_total=14, secure_rerip={"verified_rereads": [1]}
    )
    assert _proof_rows(text)[0].startswith(
        "     Proof: a single re-read that AccurateRip verifies"
    )


@pytest.mark.skipif(not _REFERENCE.exists(), reason="reference rip not present")
def test_the_report_and_the_log_print_the_same_line() -> None:
    """One function, two callers: the relation, not either side alone."""
    rip_log = _reference()
    rows = _proof_rows(render_eac_style_log(rip_log, disc_track_total=14))
    report = build_report(rip_log)
    lines = [f"     Proof: {t['proof']['line']}" for t in report["tracks"]]
    assert lines == rows
    assert {t["proof"]["kind"] for t in report["tracks"]} == {
        PROOF_ACCURATERIP,
        PROOF_NONE,
    }


@pytest.mark.skipif(not _REFERENCE.exists(), reason="reference rip not present")
def test_the_report_carries_ctdb_and_the_chase_the_log_cannot() -> None:
    rip_log = _reference()
    # Track 4 made unknown to AccurateRip, so CTDB is its strongest proof.
    rip_log = replace(
        rip_log,
        tracks=tuple(
            replace(
                t,
                accuraterip_v1=AccurateRipResult(version=1, result="x", local_crc="A"),
                accuraterip_v2=None,
                accuraterip_offset=None,
                accuraterip_lookup=_ABSENT,
            )
            if t.number == 4
            else t
            for t in rip_log.tracks
        ),
    )
    ctdb = CtdbVerifyResult(
        verdict=Verdict.MATCH,
        tracks=(CtdbTrackResult(track=4, verdict=TrackVerdict.MATCH, confidence=53),),
    )
    report = build_report(
        rip_log, ctdb_result=ctdb, secure_rerip={"verified_rereads": [1]}
    )
    by_number = {t["number"]: t["proof"] for t in report["tracks"]}
    assert by_number[4]["kind"] == PROOF_CTDB
    assert by_number[1]["kind"] == PROOF_VERIFIED_REREAD
    assert by_number[2]["kind"] == PROOF_ACCURATERIP
