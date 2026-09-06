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


# --- The rest of verdict.py's survivors, 2026-09-06 --------------------------
#
# The first pass took `verdict.py` from 20.5% to 48.7% by pinning the trust
# headline. These are the remaining twenty, and they are not leftovers: each is a
# decision the **results table**, the **report** or a user-facing sentence states
# about one track. `accuraterip_state` alone drives the per-track column.


def _ar(conf: int | None, *, crc: str | None = "22B9924D") -> AccurateRipResult:
    return AccurateRipResult(version=2, confidence=conf, local_crc=crc)


# --- accuraterip_state: the per-track column --------------------------------


def test_state_prefers_an_exact_match_over_everything() -> None:
    """An exact match is never downgraded, even with an offset-variant beside it."""
    from platterpus.verdict import AR_STATE_VERIFIED, accuraterip_state

    assert accuraterip_state(_ar(200), _ar(200)) == AR_STATE_VERIFIED
    assert accuraterip_state(_ar(200), None, "found") == AR_STATE_VERIFIED


def test_state_says_NOT_CHECKED_only_when_the_lookup_MEASURABLY_did_not_run() -> None:
    """`accuraterip_lookup_happened(lookup) is False` — an identity test, tri-state.

    The mutant `is True` inverts it: tracks that *were* checked get "not checked",
    and tracks that were not fall through to a state that presumes a comparison.
    `None` ("not stated") must fire neither branch — that is what makes `is False`
    the right operator rather than `not`.
    """
    from platterpus.verdict import (
        AR_STATE_NOT_CHECKED,
        accuraterip_state,
    )

    assert accuraterip_state(_ar(0), None, "disabled") == AR_STATE_NOT_CHECKED
    assert accuraterip_state(_ar(0), None, "error") == AR_STATE_NOT_CHECKED

    # Ran, found nothing → NOT the same claim as "we never looked".
    assert accuraterip_state(_ar(0), None, "not found") != AR_STATE_NOT_CHECKED
    # Not stated at all → also not a measured "did not run".
    assert accuraterip_state(_ar(0), None, None) != AR_STATE_NOT_CHECKED


def test_state_separates_ABSENT_from_NO_MATCH_from_NO_DATA() -> None:
    """Three different things a user must not be told interchangeably.

    * **absent** — looked, the disc is not in the database. Says nothing about the rip.
    * **no match** — the disc IS there and our read is not one of the stored copies.
    * **no data** — we have no result at all to reason from.

    The `and`/`or` mutants at 265 and 268 collapse these into each other; the
    `result is None` mutant at 272 swaps the last two.
    """
    from platterpus.verdict import (
        AR_STATE_ABSENT,
        AR_STATE_NO_DATA,
        AR_STATE_NO_MATCH,
        accuraterip_state,
    )

    # The lookup text is the REAL one, read from the committed reference log:
    #   `Accurip:       disc found in database (max confidence: 200)`
    # Guessing it is what made the first version of this test wrong twice.
    FOUND = "disc found in database (max confidence: 200)"

    # Looked; disc not in the database.
    assert accuraterip_state(_ar(0), None, "not found") == AR_STATE_ABSENT

    # Looked; disc present; our read is not one of the stored copies.
    assert accuraterip_state(_ar(0, crc="DEADBEEF"), None, FOUND) == AR_STATE_NO_MATCH

    # NO_DATA needs no lookup statement at all — and this is the surprising one,
    # so it is pinned as measured rather than as expected. With a lookup that
    # states the disc was found, a track with **no result** is still NO_MATCH:
    # `accuraterip_compared` consults the stated row first and never reaches the
    # local-CRC fallback, by the 2026-07-31 design. Worth knowing before anyone
    # "fixes" it — the state is reachable only when nothing stated anything.
    assert accuraterip_state(None, None, FOUND) == AR_STATE_NO_MATCH
    assert accuraterip_state(None, None, None) == AR_STATE_NO_DATA


def test_lookup_happened_treats_only_the_named_tokens_as_a_measured_NO() -> None:
    """`token in text` — the mutant `not in` inverts the whole classifier.

    Case-folded, and substring rather than equality, because the row is prose.
    """
    from platterpus.verdict import accuraterip_lookup_happened

    for did_not in ("disabled", "DISABLED", "lookup error", "not attempted"):
        assert accuraterip_lookup_happened(did_not) is False, did_not
    for did in ("not found", "found, confidence 200", "not present"):
        assert accuraterip_lookup_happened(did) is True, did
    assert accuraterip_lookup_happened(None) is None
    assert accuraterip_lookup_happened("") is None


# --- accuraterip_confidence_text: "200 of 200" ------------------------------


def test_confidence_text_shows_a_pair_ONLY_when_the_max_is_genuinely_larger() -> None:
    """`db_max is None or db_max < own` — an ordering we cannot explain is not shown.

    A max *below* the track's own confidence reads as a bug to anyone who notices,
    so we show the number we are sure of instead. The `<` → `<=` mutant makes an
    equal max print `"200 of 200"`… which is right, so the boundary that matters is
    equality: it must still render the pair.
    """
    from platterpus.verdict import accuraterip_confidence_text

    # The real row, from the committed reference log — the max lives in
    # `(max confidence: N)`, which is what `_DB_MAX_CONFIDENCE` matches. A
    # plausible-looking `"confidence 200 of 200"` matches nothing, and writing one
    # is how the first version of this test asserted the wrong thing.
    FOUND = "disc found in database (max confidence: 200)"

    assert accuraterip_confidence_text(_ar(3), FOUND) == "3 of 200"
    # Equal — the pair is still meaningful and must be shown. This is the boundary
    # the `<` → `<=` mutant moves.
    assert accuraterip_confidence_text(_ar(200), FOUND) == "200 of 200"
    # Max BELOW own: unexplainable ordering, so just the number we are sure of.
    assert accuraterip_confidence_text(_ar(300), FOUND) == "300"
    # No max known at all — and a row that states no max is the common case.
    assert accuraterip_confidence_text(_ar(3), None) == "3"
    assert accuraterip_confidence_text(_ar(3), "not found") == "3"


def test_confidence_text_is_EMPTY_when_the_track_has_no_confidence() -> None:
    """`own is None` — the mutant `is not None` makes a track with no confidence
    render one, and one that has a confidence render nothing."""
    from platterpus.verdict import accuraterip_confidence_text

    assert accuraterip_confidence_text(_ar(None), "confidence 200 of 200") == ""
    assert accuraterip_confidence_text(None, None) == ""
    # Zero is a confidence, not an absence.
    assert accuraterip_confidence_text(_ar(0), None) == "0"


# --- _audio_tracks: the denominator's population -----------------------------


def test_a_track_counts_as_audio_if_ANY_of_its_four_signals_is_present() -> None:
    """Four `or`-ed `is not None` checks; three mutants flip one each.

    This is the population the verdict's denominator is drawn from. A track
    dropped here is a track that silently stops counting — the 2026-07-28 audit
    finding. Each signal is driven **alone**, because with all four present every
    mutant still passes.
    """
    from platterpus.verdict import _audio_tracks

    only_crc = TrackResult(number=1, copy_crc="AAAAAAAA")
    only_v1 = TrackResult(number=2, accuraterip_v1=_ar(1))
    only_v2 = TrackResult(number=3, accuraterip_v2=_ar(1))
    only_off = TrackResult(number=4, accuraterip_offset=_ar(1))
    nothing = TrackResult(number=5)

    for track in (only_crc, only_v1, only_v2, only_off):
        assert _audio_tracks(RipLog(tracks=(track,))) == [track], (
            f"track {track.number} was dropped from the audio population"
        )
    assert _audio_tracks(RipLog(tracks=(nothing,))) == []


# --- expected_track_total: the concept that shipped four wrong fixes ---------


def test_a_deliberate_SUBSET_is_complete_at_its_own_size() -> None:
    """`only_tracks` wins over the disc total — the Rip? column exists for this.

    Using the disc count here made a deliberate 2-of-14 rip warn that "12 tracks
    were never ripped", reporting the user's own choice as a failure.
    """
    from platterpus.verdict import expected_track_total

    assert expected_track_total(14, [1, 2]) == 2
    assert expected_track_total(None, [1, 2, 3]) == 3
    # Empty means "all of them", NOT "a subset of zero".
    assert expected_track_total(14, []) == 14
    assert expected_track_total(14, None) == 14


def test_an_unknown_or_nonsensical_disc_total_is_None_not_a_number() -> None:
    """`disc_track_total and disc_track_total > 0` — both halves.

    `> 0` → `>= 0` would make a total of 0 an answer, and callers treat `None` as
    "fall back to the log", which is the only honest option when we do not know.
    """
    from platterpus.verdict import expected_track_total

    assert expected_track_total(None, None) is None
    assert expected_track_total(0, None) is None
    assert expected_track_total(-1, None) is None
    assert expected_track_total(1, None) == 1


# --- _shortfall_phrase: why the numerator falls short ------------------------


def test_the_two_shortfall_causes_are_never_collapsed_into_one() -> None:
    """ "Never ripped" and "produced no result" read very differently to a user.

    One is a track that is not on disk; the other is on disk with nothing from
    AccurateRip. The `or` → `and` mutant at 326 reports only one when both apply.
    """
    from platterpus.verdict import _shortfall_phrase

    both = _shortfall_phrase(2, 3, "")
    assert "2 tracks were never ripped" in both
    assert "3 tracks produced no result at all" in both
    assert both.count(";") == 1, f"the two causes were collapsed: {both!r}"

    assert _shortfall_phrase(0, 0, "") == "the rip did not cover the whole disc"


def test_the_shortfall_phrase_is_SINGULAR_for_exactly_one_track() -> None:
    """`never_ripped == 1` and `no_result == 1`. The `== 1` → `!= 1` mutant makes
    every count singular except one, and `1` → `2` shifts the boundary."""
    from platterpus.verdict import _shortfall_phrase

    assert "1 track was never ripped" in _shortfall_phrase(1, 0, "")
    assert "2 tracks were never ripped" in _shortfall_phrase(2, 0, "")
    assert "1 track produced no result" in _shortfall_phrase(0, 1, "")
    assert "2 tracks produced no result" in _shortfall_phrase(0, 2, "")


def test_the_rips_own_outcome_is_named_only_when_it_EXPLAINS_the_shortfall() -> None:
    """`status in {"cancelled", "failed"}` — those two explain a missing track.

    Any other status does not, and asserting one would invent a cause. Case and
    surrounding whitespace are normalised, so those are driven too.
    """
    from platterpus.verdict import _shortfall_phrase

    assert "the rip was cancelled so" in _shortfall_phrase(3, 0, "cancelled")
    assert "the rip was failed so" in _shortfall_phrase(3, 0, "  FAILED  ")
    for unexplaining in ("", "success", "completed", "unknown"):
        assert "the rip was" not in _shortfall_phrase(3, 0, unexplaining), unexplaining


# --- The last five, and two proven EQUIVALENT ---------------------------------


def test_either_column_alone_can_evidence_a_comparison() -> None:
    """`compared(result) or compared(offset_result)` — the mutant demands BOTH.

    Only reachable when the log states no `Accurip:` row, so the predicate falls
    back to the local CRC. With `and`, a track whose v2 carries our checksum but
    whose offset column does not gets classified as though nothing was compared —
    "not in the database" instead of "in the database, our read differs", which are
    opposite claims about the disc.

    Measured before writing: with `lookup=None`, `accuraterip_compared` is True for
    a result carrying a local CRC and False for one without, so this pair is the
    only shape that separates `or` from `and`.
    """
    from platterpus.verdict import AR_STATE_ABSENT, AR_STATE_NO_MATCH, accuraterip_state

    with_crc = _ar(0, crc="DEADBEEF")
    without = _ar(0, crc=None)

    # v2 evidences the comparison, the offset column does not.
    assert accuraterip_state(with_crc, without, None) == AR_STATE_NO_MATCH
    # ...and the other way round, so neither operand is the one that matters.
    assert accuraterip_state(without, with_crc, None) == AR_STATE_NO_MATCH
    # Neither: nothing evidences a comparison.
    assert accuraterip_state(without, without, None) == AR_STATE_ABSENT


def test_a_confidence_of_exactly_ONE_counts_toward_the_floor() -> None:
    """`conf >= 1` — the floor of `accuraterip_is_match`, reused for the headline.

    Two mutants sit here (`>= 1` → `> 1`, and `1` → `2`) and both exclude a
    confidence of exactly 1, which is a real match. The rendered floor would then
    silently jump to the next-lowest confidence and over-state the disc.
    """
    from platterpus.verdict import accuraterip_verdict

    log = RipLog(tracks=(_verified(1, conf=1), _verified(2, conf=200)))
    text, tone = accuraterip_verdict(log, disc_track_total=2)
    assert tone == "ok"
    assert "confidence 1+" in text, (
        f"a track verified at confidence 1 was excluded from the floor: {text!r}"
    )


def test_reconcile_defaults_crc_validated_to_FALSE_when_absent() -> None:
    """`getattr(ctdb_result, "crc_validated", False)` — the default is the safe one.

    An object that does not carry the attribute at all must be treated as
    *not* hardware-validated. The mutant defaults it True, so a result shape
    without the field starts producing the reconciliation KDD-16 says to withhold.
    """

    class _NoField:
        verdict = type("V", (), {"value": "no_match"})()

    log = RipLog(tracks=(_verified(1), _offset(2)))
    assert reconcile_ar_ctdb(log, _NoField()) is None


def test_reconcile_on_a_ONE_TRACK_disc_still_speaks() -> None:
    """`total == 0` — the mutant `== 1` silences a whole class of disc.

    A single-track disc that matched an offset variant, beside a CTDB no-match, is
    exactly as contradictory as a fourteen-track one and must be explained.
    """
    one = RipLog(tracks=(_offset(1),))
    assert reconcile_ar_ctdb(one, _ctdb(Verdict.NO_MATCH)) is not None


def test_two_verdict_mutants_are_EQUIVALENT_and_here_is_the_proof() -> None:
    """Recorded rather than left looking unkilled, with the reasoning measured.

    * **`accuraterip_lookup_happened`, the `_LOOKUP_FOUND_NOTHING` branch.** Its arm
      returns ``True`` and so does the fall-through, so flipping the membership test
      cannot change the answer for *any* input. The branch exists to carry the
      comment explaining why "looked, found nothing" counts as *happened* — it is
      documentation with a `return` attached, and that is a reasonable thing to
      keep.
    * **`expected_track_total`, `disc_track_total > 0`.** Guarded by
      ``disc_track_total and``, which already rejects ``0`` and ``None``; a negative
      fails both spellings. ``>= 0`` is therefore unreachable-different.

    Both were checked over their whole reachable input space before being called
    equivalent, which is the difference between a proof and a shrug. The
    assertions below are the same exhaustive check, so the claim decays if either
    function grows a new path.
    """
    from platterpus.verdict import accuraterip_lookup_happened, expected_track_total

    # The FOUND_NOTHING arm and the fall-through must agree, or the mutant is live.
    assert accuraterip_lookup_happened("not found") is True
    assert accuraterip_lookup_happened("something else entirely") is True

    # And every falsy disc total is already rejected before the comparison.
    for falsy in (None, 0):
        assert expected_track_total(falsy, None) is None
    assert expected_track_total(-1, None) is None
