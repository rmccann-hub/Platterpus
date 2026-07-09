"""Tests for the pure verdict helpers (verdict.py).

Focus: the shared AccurateRip counter and the AR↔CTDB reconciliation added
2026-07-09. The banner wording itself is exercised via test_ui_rip_progress.
"""

from __future__ import annotations

from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
from platterpus.parsers.rip_log import AccurateRipResult, RipLog, TrackResult
from platterpus.verdict import accuraterip_counts, reconcile_ar_ctdb


def _verified(number: int, conf: int = 200) -> TrackResult:
    return TrackResult(
        number=number,
        copy_crc=f"{number:08X}",
        accuraterip_v2=AccurateRipResult(version=2, confidence=conf),
    )


def _offset(number: int, conf: int = 200) -> TrackResult:
    return TrackResult(
        number=number,
        copy_crc=f"{number:08X}",
        accuraterip_offset=AccurateRipResult(version=450, confidence=conf),
    )


def _not_in_db(number: int) -> TrackResult:
    return TrackResult(number=number, copy_crc=f"{number:08X}")


# --- accuraterip_counts -----------------------------------------------------


def test_counts_mixed_disc() -> None:
    log = RipLog(tracks=(_verified(1), _verified(2), _offset(3), _not_in_db(4)))
    total, verified, partial = accuraterip_counts(log)
    assert (total, verified, partial) == (4, 2, 1)


def test_counts_empty() -> None:
    assert accuraterip_counts(RipLog()) == (0, 0, 0)


# --- reconcile_ar_ctdb ------------------------------------------------------


def _ctdb(verdict: Verdict, *, crc_validated: bool = True) -> CtdbVerifyResult:
    return CtdbVerifyResult(
        verdict=verdict, confidence=100, crc_validated=crc_validated
    )


def test_reconcile_explains_no_match_with_partials() -> None:
    # The real Police case: 12 verified + 2 offset-variant, CTDB no_match.
    log = RipLog(tracks=(_verified(1), _verified(2), _offset(3), _offset(4)))
    line = reconcile_ar_ctdb(log, _ctdb(Verdict.NO_MATCH))
    assert line is not None
    assert "offset-variant" in line
    assert "SAME finding" in line


def test_reconcile_all_verified_no_ctdb_entry() -> None:
    log = RipLog(tracks=(_verified(1), _verified(2)))
    line = reconcile_ar_ctdb(log, _ctdb(Verdict.NO_MATCH))
    assert line is not None
    assert "hasn't been submitted" in line or "AccurateRip is the authority" in line


def test_reconcile_silent_on_match() -> None:
    log = RipLog(tracks=(_verified(1),))
    assert reconcile_ar_ctdb(log, _ctdb(Verdict.MATCH)) is None


def test_reconcile_silent_when_crc_unvalidated() -> None:
    log = RipLog(tracks=(_verified(1), _offset(2)))
    assert reconcile_ar_ctdb(log, _ctdb(Verdict.NO_MATCH, crc_validated=False)) is None


def test_reconcile_silent_when_nothing_verified() -> None:
    log = RipLog(tracks=(_not_in_db(1),))
    assert reconcile_ar_ctdb(log, _ctdb(Verdict.NO_MATCH)) is None


def test_reconcile_never_raises_on_garbage() -> None:
    assert reconcile_ar_ctdb(object(), object()) is None
    assert reconcile_ar_ctdb(None, None) is None


# --- Review-driven reconcile edge cases (2026-07-09) ------------------------


def test_reconcile_not_in_db_branch_does_not_claim_mismatch() -> None:
    # verified>0, the rest NOT in AccurateRip (not offset-variants): must NOT
    # claim those tracks "didn't match the common pressing" — AR has no data.
    log = RipLog(tracks=(_verified(1), _not_in_db(2)))
    line = reconcile_ar_ctdb(log, _ctdb(Verdict.NO_MATCH))
    assert line is not None
    assert "aren't in AccurateRip" in line
    assert "didn't match the common pressing" not in line


def test_reconcile_all_offset_variant_is_explained() -> None:
    # verified==0 but partial>0 (every track offset-variant) beside a CTDB
    # no-match still looks contradictory → must be reconciled, not silent.
    log = RipLog(tracks=(_offset(1), _offset(2)))
    line = reconcile_ar_ctdb(log, _ctdb(Verdict.NO_MATCH))
    assert line is not None
    assert "offset-variant" in line
