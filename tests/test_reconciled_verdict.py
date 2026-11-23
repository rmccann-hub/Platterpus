"""The one line that says which of AccurateRip and CTDB decides, and why (R181).

UX review of 0.7.127, V2 and A3: CTDB's "verified ✓" and AccurateRip's "WRONG"
sat on one screen, both amber, and nothing said which to believe. The line
``reconciled_verdict.reconcile_verdict`` builds always names the deciding source.

The rip log is REAL: the owner's 2026-11-03 Full run, section F
(``round37full1103awholedisc.log``), whose track 5 matched AccurateRip on frame
450 only, so AccurateRip calls it WRONG. The CTDB answers are built around it.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from evidence_paths import evidence
from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.ctdb.matching import CtdbTrackResult, TrackVerdict
from platterpus.ctdb.repair_types import RepairedTrack, RepairRecord, RepairStatus
from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
from platterpus.ctdb_disagreement import ctdb_note_sentence
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog
from platterpus.reconciled_verdict import (
    DECIDES_ACCURATERIP,
    DECIDES_BOTH,
    DECIDES_CTDB,
    DECIDES_SPLIT,
    LEVEL_NEUTRAL,
    LEVEL_OK,
    LEVEL_WARN,
    reconcile_verdict,
    repaired_tracks,
)

_F1_LOG: str = "docs/handshake/artifactsround37/round37full1103awholedisc.log"


def _f1() -> RipLog:
    return parse_cyanrip_log(evidence(_F1_LOG).read_text(encoding="utf-8"))


def _all_verified(rip_log: RipLog) -> RipLog:
    """F1 with every track carrying track 1's exact AccurateRip match."""
    one = next(t for t in rip_log.tracks if t.number == 1)
    return replace(
        rip_log,
        tracks=tuple(
            replace(
                t,
                accuraterip_v1=one.accuraterip_v1,
                accuraterip_v2=one.accuraterip_v2,
                accuraterip_offset=None,
            )
            for t in rip_log.tracks
        ),
    )


def _rows(
    questioned: dict[int, TrackVerdict], count: int = 14
) -> tuple[CtdbTrackResult, ...]:
    """Per-track CTDB rows: MATCH unless ``questioned`` says otherwise."""
    rows: list[CtdbTrackResult] = []
    for n in range(1, count + 1):
        verdict = questioned.get(n, TrackVerdict.MATCH)
        if verdict is TrackVerdict.DIFFERS:
            rows.append(CtdbTrackResult(n, verdict, disagreeing_confidence=212))
        else:
            rows.append(CtdbTrackResult(n, verdict, confidence=212))
    return tuple(rows)


def _no_match(questioned: dict[int, TrackVerdict]) -> CtdbVerifyResult:
    return CtdbVerifyResult(
        Verdict.NO_MATCH,
        message="no entry matches the whole disc",
        best_confidence=212,
        total_confidence=214,
        offset_range=5879,
        tracks=_rows(questioned),
    )


def _whole_disc_match() -> CtdbVerifyResult:
    return CtdbVerifyResult(
        Verdict.MATCH, confidence=212, best_confidence=212, total_confidence=214
    )


def _repaired(before: CtdbVerifyResult, *, agrees: bool | None) -> CtdbVerifyResult:
    """``before`` after a REPAIRED record for track 5, with or without a fresh check."""
    record = RepairRecord(
        status=RepairStatus.REPAIRED,
        entry_id="1f2e3d4c",
        confidence=212,
        tracks=(
            RepairedTrack(
                track=5,
                path="/m/05.flac",
                original_kept_as="/m/05.flac.before-ctdb-repair",
                samples_corrected=12,
                pcm_crc32_before=1,
                pcm_crc32_after=2,
                ctdb_crc_expected=3,
                ctdb_crc_after=3,
            ),
        ),
    )
    after = None
    if agrees is not None:
        after = (
            _whole_disc_match()
            if agrees
            else CtdbVerifyResult(Verdict.NO_MATCH, message="still differs")
        )
    return replace(before, repair=record, after_repair=after)


# --- No CTDB answer: no line ----------------------------------------------------


def test_no_ctdb_answer_means_no_line() -> None:
    """Absence promotes nobody: without CTDB the banner is the whole verdict."""
    assert reconcile_verdict(_f1(), None) is None
    assert reconcile_verdict(None, _whole_disc_match()) is None


# --- The cases -------------------------------------------------------------------


def test_both_agree_when_accuraterip_verifies_every_track_and_ctdb_matches() -> None:
    verdict = reconcile_verdict(_all_verified(_f1()), _whole_disc_match())
    assert verdict is not None
    assert verdict.level == LEVEL_OK
    assert verdict.decides == DECIDES_BOTH
    assert verdict.text.startswith("✓ AccurateRip and CTDB agree")


def test_accuraterip_decides_a_track_it_calls_wrong_that_ctdb_matches() -> None:
    """THE V2 CASE, with real data: track 5 is AccurateRip-WRONG and CTDB's
    per-track answer matches it. AccurateRip decides, the line says why, and it
    is a warning, never green."""
    verdict = reconcile_verdict(_f1(), _no_match({}))
    assert verdict is not None
    assert verdict.level == LEVEL_WARN
    assert verdict.decides == DECIDES_ACCURATERIP
    assert verdict.text.startswith("⚠ AccurateRip decides track 5:")
    assert "CTDB matches it" in verdict.text
    assert "AccurateRip is the per-track verdict" in verdict.text
    assert "re-rip it" in verdict.text


def test_a_whole_disc_ctdb_match_does_not_clear_an_accuraterip_wrong_track() -> None:
    verdict = reconcile_verdict(_f1(), _whole_disc_match())
    assert verdict is not None
    assert verdict.level == LEVEL_WARN
    assert verdict.decides == DECIDES_ACCURATERIP
    assert "CTDB matches the whole disc" in verdict.text


def test_a_confirmed_repair_makes_ctdb_decide_the_repaired_track() -> None:
    """The file is no longer the read AccurateRip rejected."""
    before = _no_match({5: TrackVerdict.DIFFERS})
    verdict = reconcile_verdict(_f1(), before, _repaired(before, agrees=True))
    assert verdict is not None
    assert verdict.decides == DECIDES_CTDB
    assert verdict.level == LEVEL_OK
    assert verdict.text.startswith("✓ CTDB decides track 5:")
    assert "describes the read the repair replaced" in verdict.text


@pytest.mark.parametrize("agrees", [False, None], ids=["check-disagrees", "no-check"])
def test_an_unconfirmed_repair_settles_nothing(agrees: bool | None) -> None:
    before = _no_match({5: TrackVerdict.DIFFERS})
    verdict = reconcile_verdict(_f1(), before, _repaired(before, agrees=agrees))
    assert verdict is not None
    assert verdict.level == LEVEL_WARN
    assert "nothing settles it yet" in verdict.text
    assert "CTDB decides" not in verdict.text


def test_a_repair_and_a_rejected_track_split_the_decision() -> None:
    """Track 5 repaired (CTDB decides it) beside track 9 AccurateRip rejects."""
    rip_log = _f1()
    five = next(t for t in rip_log.tracks if t.number == 5)
    rip_log = replace(
        rip_log,
        tracks=tuple(
            replace(
                t,
                accuraterip_v1=five.accuraterip_v1,
                accuraterip_v2=five.accuraterip_v2,
                accuraterip_offset=five.accuraterip_offset,
            )
            if t.number == 9
            else t
            for t in rip_log.tracks
        ),
    )
    before = _no_match({5: TrackVerdict.DIFFERS, 9: TrackVerdict.DIFFERS})
    verdict = reconcile_verdict(rip_log, before, _repaired(before, agrees=True))
    assert verdict is not None
    assert verdict.decides == DECIDES_SPLIT
    assert verdict.level == LEVEL_WARN
    assert "CTDB decides track 5" in verdict.text
    assert "AccurateRip decides track 9" in verdict.text


def test_the_ctdb_disagreement_note_reaches_the_line_with_real_data() -> None:
    """R181's check: the 0.7.119 note (``ctdb_disagreement``) is carried word for
    word by the reconciled line, on the real F1 log with every track verified."""
    rip_log = _all_verified(_f1())
    result = _no_match({2: TrackVerdict.DIFFERS})
    verdict = reconcile_verdict(rip_log, result)
    assert verdict is not None
    note = ctdb_note_sentence([(2, "differs")]).removeprefix("ⓘ ")
    assert note == "CTDB disagrees on track 2 (differs); AccurateRip is the verdict"
    assert verdict.text == (
        f"ⓘ {note}, because AccurateRip, the per-track check, found nothing wrong "
        "with this track."
    )
    assert verdict.level == LEVEL_NEUTRAL
    assert verdict.decides == DECIDES_ACCURATERIP
    assert "WRONG" not in verdict.text.upper().replace("NOTHING WRONG", "")


def test_ctdb_decides_a_disc_accuraterip_has_no_entry_for() -> None:
    rip_log = _f1()
    absent = replace(
        rip_log,
        tracks=tuple(
            replace(
                t,
                accuraterip_v1=None,
                accuraterip_v2=None,
                accuraterip_offset=None,
                accuraterip_lookup="not found",
            )
            for t in rip_log.tracks
        ),
    )
    verdict = reconcile_verdict(absent, _whole_disc_match())
    assert verdict is not None
    assert verdict.decides == DECIDES_CTDB
    assert verdict.level == LEVEL_OK


def test_a_ctdb_no_match_beside_a_verified_rip_leaves_accuraterip_deciding() -> None:
    verdict = reconcile_verdict(_all_verified(_f1()), _no_match({}))
    assert verdict is not None
    assert verdict.decides == DECIDES_ACCURATERIP
    assert verdict.level == LEVEL_NEUTRAL
    assert verdict.text.startswith("ⓘ AccurateRip decides:")


def test_every_line_leads_with_its_marker() -> None:
    """Status is never colour alone (WCAG 2.2 AA)."""
    marks = {LEVEL_OK: "✓", LEVEL_WARN: "⚠", LEVEL_NEUTRAL: "ⓘ"}
    before = _no_match({5: TrackVerdict.DIFFERS})
    seen = set()
    for rip_log, ctdb, repair in (
        (_all_verified(_f1()), _whole_disc_match(), None),
        (_f1(), _no_match({}), None),
        (_all_verified(_f1()), _no_match({2: TrackVerdict.DIFFERS}), None),
        (_f1(), before, _repaired(before, agrees=True)),
    ):
        verdict = reconcile_verdict(rip_log, ctdb, repair)
        assert verdict is not None
        assert verdict.text.startswith(marks[verdict.level] + " ")
        seen.add(verdict.level)
    assert seen == set(marks), f"the sweep did not reach every level: {seen}"


def test_repaired_tracks_reads_only_a_repaired_record() -> None:
    before = _no_match({5: TrackVerdict.DIFFERS})
    assert repaired_tracks(_repaired(before, agrees=True)) == {5: True}
    assert repaired_tracks(_repaired(before, agrees=None)) == {5: None}
    refused = replace(before, repair=RepairRecord(status=RepairStatus.REFUSED))
    assert repaired_tracks(refused) == {}
    assert repaired_tracks(None) == {}


@settings(max_examples=60, deadline=None)
@given(
    junk=st.one_of(
        st.none(),
        st.integers(),
        st.text(),
        st.lists(st.integers()),
        st.dictionaries(st.text(), st.integers()),
    )
)
def test_it_never_raises_on_a_shape_it_does_not_know(junk: object) -> None:
    """A results-pane line must never take the pane down."""
    for args in ((junk, junk, junk), (_f1(), junk, junk), (junk, _no_match({}), junk)):
        result = reconcile_verdict(*args)
        assert result is None or isinstance(result.text, str)
