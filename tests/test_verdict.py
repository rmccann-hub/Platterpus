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


# --- accuraterip_verdict: the TRUST HEADLINE's branch boundaries -------------
#
# `verdict.py` scored **20.5%** under the mutation sweep on 2026-09-06 — the worst
# of any module measured, in the module that decides the sentence a user reads
# about whether their rip is bit-perfect and that the report records. Eight of the
# 31 survivors were in this one function, and every one of them was a **branch
# boundary**: `verified == total` → `!=`, `verified > 0` → `>=`, `total == 0` → `!=`.
#
# A wrong branch here does not crash and does not look wrong. It prints a
# confident, well-formed, green sentence about a disc that did not earn it — which
# is the shape that shipped on 2026-07-30, when cancelling after two tracks of
# fourteen produced "✓ Bit-perfect: all 2 tracks verified".
#
# Each case below sits ON a boundary, because that is the only place the operator
# and its mutant differ.


def test_no_accuraterip_data_at_all_says_NOTHING(track_count: int = 0) -> None:
    """`total == 0` → empty text, neutral tone. The mutant makes it `!= 0`, which
    sends a disc *with* AccurateRip data down the no-data path and silences the
    headline entirely."""
    from platterpus.verdict import accuraterip_verdict

    text, tone = accuraterip_verdict(RipLog())
    assert (text, tone) == ("", "neutral")

    # The other side: one track with data must NOT take that path.
    text, tone = accuraterip_verdict(RipLog(tracks=(_verified(1),)))
    assert text and tone == "ok", "a disc with AccurateRip data got the empty verdict"


def test_a_complete_verified_disc_is_the_ONLY_green_case() -> None:
    """`verified == total` **and** nothing missing. Both halves, on the boundary.

    The 2026-07-30 defect lived exactly here: `verified == total` was true of a
    cancelled rip's two tracks, and without the `missing` half it went green on 14%
    of the disc.
    """
    from platterpus.verdict import accuraterip_verdict

    whole = RipLog(tracks=(_verified(1), _verified(2), _verified(3)))
    text, tone = accuraterip_verdict(whole, disc_track_total=3)
    assert tone == "ok" and "Bit-perfect" in text

    # ONE track short of the disc — same `verified == total`, and it must not be
    # green. This is the cancelled-rip shape.
    text, tone = accuraterip_verdict(whole, disc_track_total=4)
    assert tone == "warn", "a rip missing a track went green"
    assert "Bit-perfect" not in text
    assert "3 of 4" in text

    # And one track present but with no AccurateRip result is the OTHER way to be
    # short — `verified == total` is false there, so it must not be green either.
    partial_log = RipLog(tracks=(_verified(1), _verified(2), _not_in_db(3)))
    text, tone = accuraterip_verdict(partial_log, disc_track_total=3)
    assert tone == "warn" and "Bit-perfect" not in text


def test_every_track_accounted_for_but_some_offset_variant_stays_AMBER() -> None:
    """`verified + partial == total` — accounted for, not proven bit-perfect.

    The boundary is the equality: with `!=` an all-accounted disc falls through to
    the "aren't in the database or didn't match" wording, which is false about
    tracks that DID match an offset-variant pressing.
    """
    from platterpus.verdict import accuraterip_verdict

    log = RipLog(tracks=(_verified(1), _verified(2), _offset(3)))
    text, tone = accuraterip_verdict(log, disc_track_total=3)
    assert tone == "warn", "offset-variant is not proven bit-perfect"
    assert "offset-variant" in text
    assert "aren't in the database" not in text, (
        "tracks that matched an offset-variant were described as unmatched"
    )

    # NOT all accounted for: one genuinely absent → the other wording is correct.
    log = RipLog(tracks=(_verified(1), _offset(2), _not_in_db(3)))
    text, tone = accuraterip_verdict(log, disc_track_total=3)
    assert tone == "warn" and "aren't in the database" in text


def test_no_exact_matches_but_offset_variants_is_not_the_same_as_nothing() -> None:
    """`verified > 0` is the boundary between "some matched" and "none did".

    With `>=` a disc where **nothing** matched takes the some-matched branch and
    reports verified tracks it does not have.
    """
    from platterpus.verdict import accuraterip_verdict

    only_offset = RipLog(tracks=(_offset(1), _offset(2)))
    text, tone = accuraterip_verdict(only_offset, disc_track_total=2)
    assert tone == "warn" and "offset-variant" in text
    assert "verified against AccurateRip" not in text.split("—")[0], (
        "a disc with no exact matches claimed verified tracks"
    )

    # Exactly one exact match is the other side of `> 0`.
    one = RipLog(tracks=(_verified(1), _not_in_db(2)))
    text, tone = accuraterip_verdict(one, disc_track_total=2)
    assert "1 of 2" in text


def test_the_disc_total_is_the_denominator_a_stopped_rip_cannot_move() -> None:
    """`disc_track_total > 0` chooses between the disc's count and the log's.

    The mutants here (`> 0` → `>= 0`, and the fallback) swap which number is the
    denominator. That is the whole 2026-07-30 fix: only the disc's own count is
    immune to a rip stopping early, because the log's count shrinks with it.
    """
    from platterpus.verdict import accuraterip_verdict

    two_of_ten = RipLog(tracks=(_verified(1), _verified(2)))

    # Disc total known → it is the denominator, and the rip is short.
    text, tone = accuraterip_verdict(two_of_ten, disc_track_total=10)
    assert tone == "warn" and "2 of 10" in text

    # Disc total UNKNOWN (0 or None) → fall back to the log's own count, which is
    # all we have. It must not become "2 of 0".
    for unknown in (0, None):
        text, tone = accuraterip_verdict(two_of_ten, disc_track_total=unknown)
        assert " of 0" not in text, f"disc_track_total={unknown!r} produced 'of 0'"
        assert tone == "ok" and "Bit-perfect" in text


def test_reconcile_stays_silent_until_the_CTDB_CRC_IS_HARDWARE_VALIDATED() -> None:
    """`crc_validated` False → no reconciliation (KDD-16).

    Before validation a CTDB no-match is expected noise, and explaining it would
    over-explain a placeholder. The mutant flips the guard, so the explanation
    appears exactly when it is meaningless and vanishes when it matters.
    """
    log = RipLog(tracks=(_verified(1), _offset(2)))
    assert reconcile_ar_ctdb(log, _ctdb(Verdict.NO_MATCH, crc_validated=False)) is None
    assert reconcile_ar_ctdb(log, _ctdb(Verdict.NO_MATCH)) is not None


def test_reconcile_says_nothing_when_there_is_no_AccurateRip_signal() -> None:
    """`total == 0 or (verified == 0 and partial == 0)` — no apparent conflict.

    Three boundaries in one condition, so all three states are driven: no data at
    all, data but nothing matched, and the all-offset-variant disc that DOES look
    contradictory beside a CTDB no-match and must fall through.
    """
    assert reconcile_ar_ctdb(RipLog(), _ctdb(Verdict.NO_MATCH)) is None

    nothing_matched = RipLog(tracks=(_not_in_db(1), _not_in_db(2)))
    assert reconcile_ar_ctdb(nothing_matched, _ctdb(Verdict.NO_MATCH)) is None

    all_offset = RipLog(tracks=(_offset(1), _offset(2)))
    assert reconcile_ar_ctdb(all_offset, _ctdb(Verdict.NO_MATCH)) is not None, (
        "an all-offset-variant disc beside a CTDB no-match DOES look "
        "contradictory and must be explained"
    )
