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


# --- Found by mutation sweep, 2026-09-05 ------------------------------------
#
# `scripts/mutation_sweep.py` mutated `verdict.py` against this file and 16 of 21
# mutants SURVIVED — a 23.8% score on the module that decides what a rip's
# accuracy claim says. Coverage was already high here; coverage proves a line
# RAN, and these prove nothing was ASSERTED about it. The three below are the
# trust-bearing ones.
#
# `accuraterip_lookup_happened` was not imported by this file at all, so every
# one of its returns could be flipped with the suite still green: a rip whose
# AccurateRip lookup was DISABLED would have been reported as having been
# compared. That is a false archival claim, which is the one class this project
# treats as unacceptable.


def test_a_lookup_that_never_RAN_is_not_a_lookup_that_found_nothing() -> None:
    """**Mutant: `return False` -> `return True` at the "did not happen" branch.**

    It survived, so nothing distinguished *"we never asked the database"* from
    *"we asked and the disc is not in it"*. Those are `none` versus
    `unknown (reason)` — the distinction `docs/OWNERSHIP.md` makes absolute — and
    collapsing them turns an absent comparison into a performed one.
    """
    from platterpus.verdict import accuraterip_lookup_happened

    for text in (
        "disabled",
        "AccurateRip disabled",
        "error: timed out",
        "not attempted",
    ):
        assert accuraterip_lookup_happened(text) is False, text


def test_a_lookup_that_ran_and_MISSED_still_happened() -> None:
    """**Mutants: `return True` -> `return False` at both remaining branches.**

    A miss is still a comparison attempt. Reporting it as "no lookup" would hide
    that the disc was checked and genuinely is not in the database.
    """
    from platterpus.verdict import accuraterip_lookup_happened

    for text in ("not found", "not present", "not in database"):
        assert accuraterip_lookup_happened(text) is True, text
    # Anything else that is non-empty also means a lookup occurred.
    assert accuraterip_lookup_happened("2 of 2 matched") is True


def test_an_unstated_lookup_is_NOT_DETERMINED_and_never_a_verdict() -> None:
    """Tri-state, and the third state is the one that must not be inferred."""
    from platterpus.verdict import accuraterip_lookup_happened

    assert accuraterip_lookup_happened(None) is None
    assert accuraterip_lookup_happened("") is None


def test_the_missing_track_clamp_reports_ZERO_on_a_complete_rip() -> None:
    """**Mutant: `max(0, expected - logged)` -> `max(1, ...)`, and it survived.**

    The clamp exists so a rip that logged MORE tracks than the disc claims cannot
    report a negative shortfall. Nothing asserted its floor, so a complete rip
    could have been made to claim one track was never ripped — a shortfall
    invented out of a clamp, in the sentence a user reads as the accuracy
    headline.
    """
    from platterpus.verdict import accuraterip_verdict

    tracks = tuple(
        TrackResult(
            number=n,
            accuraterip_offset=AccurateRipResult(
                version=2, result="Found, exact match"
            ),
        )
        for n in (1, 2, 3)
    )
    log = RipLog(tracks=tracks)
    text, _tone = accuraterip_verdict(log, disc_track_total=3)
    assert "never ripped" not in text.lower(), text
    assert "1 track" not in text, (
        f"a complete 3-of-3 rip reported a shortfall: {text!r} — the clamp's "
        "floor is inventing a missing track"
    )
