"""The single, pure AccurateRip "is this rip trustworthy?" verdict.

This lives in its own Qt-free module because **more than one surface needs the
same answer**: the results-pane verdict banner (`ui/rip_progress`), the
machine-readable rip report (`rip_report`), and any future consumer. Keeping it
here (not in a UI module) is the "one definition of verified" rule from
docs/ux-design-principles.md — duplicating it is exactly the bug that made the
disc-info panel disagree with the banner.

It builds on the per-track predicate in `parsers/rip_log`
(`track_accuraterip_verified`, confidence ≥ 1), so the whole-disc verdict and
the per-track checkmarks can never diverge.
"""

from __future__ import annotations

from collections.abc import Sequence

from platterpus.parsers.rip_log import accuraterip_is_match, track_accuraterip_verified


def _audio_tracks(rip_log: object) -> list[object]:
    """Tracks AccurateRip has *anything* to say about (a Copy CRC or any result).

    Split out because the verdict needs both this list and the log's full track
    list: a track that failed outright produces neither a CRC nor an AR line, so
    it is invisible here — and comparing the two is what stops a dead track from
    being silently dropped from the denominator (audit finding, 2026-07-28).
    """
    tracks = getattr(rip_log, "tracks", ()) or ()
    return [
        t
        for t in tracks
        if getattr(t, "copy_crc", "")
        or getattr(t, "accuraterip_v1", None) is not None
        or getattr(t, "accuraterip_v2", None) is not None
        or getattr(t, "accuraterip_offset", None) is not None
    ]


def track_accuraterip_partial(track: object) -> bool:
    """True when a track matched ONLY the +450-frame offset-variant pressing.

    The single definition, because three surfaces used to compute it three ways.
    An ``accuraterip_offset`` *attribute* is set whenever cyanrip printed an
    "Accurip 450:" line at all — **including** ``(not found, either a new
    pressing, or bad rip)``. Counting the line's presence therefore reported a
    partial match for a track that matched nothing, so the banner said "matched
    an offset-variant pressing" while the table beside it said "—" (audit
    finding, 2026-07-28). A partial is a *match* (confidence ≥ 1) at the variant
    offset and no exact match. Reads via ``getattr``; never raises.
    """
    if track_accuraterip_verified(track):
        return False
    return accuraterip_is_match(getattr(track, "accuraterip_offset", None))


def accuraterip_counts(rip_log: object) -> tuple[int, int, int]:
    """Return ``(total_audio, verified, partial)`` for a rip log.

    ``total_audio`` counts tracks AccurateRip has anything to say about (a Copy
    CRC or any AR result), ``verified`` those that matched exactly (confidence
    ≥ 1), and ``partial`` those that matched only the offset-variant pressing
    ("Accurip 450") without an exact match. The single source both
    :func:`accuraterip_verdict` and :func:`reconcile_ar_ctdb` read, so the
    banner, the JSON, and the reconciliation line can never disagree on the
    tally. Pure; reads via ``getattr`` and never raises.

    Note the denominator: ``total_audio`` can be **smaller** than the log's track
    count when a track failed outright. Callers that render a "clean sweep"
    headline must compare it against ``len(rip_log.tracks)`` themselves — or use
    :func:`accuraterip_verdict`, which already does.
    """
    audio = _audio_tracks(rip_log)
    total = len(audio)
    verified = sum(1 for t in audio if track_accuraterip_verified(t))
    partial = sum(1 for t in audio if track_accuraterip_partial(t))
    return total, verified, partial


# --- The one AccurateRip state classification --------------------------------
#
# Lifted here from `ui/rip_progress` (2026-07-30). Two surfaces render this fact
# — the EAC-compatible log's per-track line and the results table's v1/v2 cells —
# and they had *different state sets*: the log grew a fourth state ("cannot be
# verified as accurate") in 2026-07-28 on the grounds that saying "not present in
# the database" about a track the database DOES have is a false claim, and the
# table never got it. So the screen made the exact claim the log fix removed.
#
# A cross-surface test now guards their agreement, but a test that watches two
# copies is weaker than one definition. This is that definition: both renderers
# ask it *which state* a track is in and only decide how to word it. The states
# themselves therefore cannot diverge, and the test's job becomes exhaustiveness —
# every state must be rendered distinctly by every surface — which is a stronger
# property than agreement by coincidence.
#
# Plain strings rather than an Enum: they are only ever compared against these
# constants, and a string keeps log and debugger output readable.
AR_STATE_VERIFIED: str = "verified"  # exact checksum match, confidence >= 1
AR_STATE_OFFSET_VARIANT: str = "offset-variant"  # matched the +450 pressing only
AR_STATE_NO_MATCH: str = "no-match"  # in the database, our read matched nothing
AR_STATE_ABSENT: str = "absent"  # nothing in the database to compare against
AR_STATE_NO_DATA: str = "no-data"  # this AR version reported nothing at all
# No lookup happened, so the database has said NOTHING about this track either
# way. Distinct from `absent` ("looked, the disc is not there") and from
# `no-match` ("looked, the disc is there, our read is not one of the copies").
AR_STATE_NOT_CHECKED: str = "not-checked"

# Every state the classifier can return. A renderer that handles a subset of
# these is a renderer with a silent hole, which is precisely what happened — so
# the set is exported for the consistency test to enumerate rather than being
# rediscovered by reading if-chains.
AR_STATES: frozenset[str] = frozenset(
    {
        AR_STATE_VERIFIED,
        AR_STATE_OFFSET_VARIANT,
        AR_STATE_NO_MATCH,
        AR_STATE_ABSENT,
        AR_STATE_NO_DATA,
        AR_STATE_NOT_CHECKED,
    }
)


# The `Accurip:` status texts that mean NO comparison took place. Matched as
# substrings, casefolded, so a reworded variant still lands — and negatives are
# listed rather than positives because a *positive* list would have to be complete
# to be safe, while a negative list only has to be right about what it names.
_LOOKUP_DID_NOT_HAPPEN: tuple[str, ...] = ("disabled", "error", "not attempted")
# ...and the ones that mean the lookup ran and the disc simply is not there.
_LOOKUP_FOUND_NOTHING: tuple[str, ...] = ("not found", "not present", "not in database")


def accuraterip_lookup_happened(lookup: str | None) -> bool | None:
    """Did a database lookup take place? True / False / None for "not stated".

    Pure, and never raises. ``lookup`` is the verbatim text of cyanrip's per-track
    ``Accurip:`` row.
    """
    if not lookup:
        return None
    text = lookup.casefold()
    if any(token in text for token in _LOOKUP_DID_NOT_HAPPEN):
        return False
    if any(token in text for token in _LOOKUP_FOUND_NOTHING):
        # The lookup ran; the disc was not there. That IS a comparison attempt, so
        # it is "happened" — the classifier separates it from a match below.
        return True
    return True


def accuraterip_compared(result: object, lookup: str | None = None) -> bool:
    """True when this AR result proves a database comparison actually happened.

    ``lookup`` is cyanrip's per-track ``Accurip:`` status text and is consulted
    FIRST, because it is the only thing in the log that states this directly.

    The fallback evidence is ``local_crc`` — the checksum *we* computed for the
    track. That used to be the whole test, on the stated reasoning that cyanrip
    only prints a per-track ``Accurip v1/v2:`` row when the disc was found. **That
    reasoning was false.** cyanrip prints those rows in every state, `disabled`
    included, so the predicate was effectively unconditional: it made
    :data:`AR_STATE_ABSENT` unreachable for a cyanrip log, and a disc nobody had
    ever looked up rendered as "in DB, no match" — a claim both that the disc is
    in the database and that our read disagreed with it (audit, 2026-07-31).

    The CRC fallback is kept for logs that carry no status row at all — whipper's,
    where a local CRC really does evidence a comparison — so this change cannot
    reclassify an existing whipper rip.

    Reads via ``getattr`` so it never raises on an unexpected shape.
    """
    stated = accuraterip_lookup_happened(lookup)
    if stated is not None:
        return stated
    return bool(getattr(result, "local_crc", None))


def accuraterip_state(
    result: object, offset_result: object, lookup: str | None = None
) -> str:
    """Classify one AR column (v1 or v2) into exactly one of :data:`AR_STATES`.

    ``result`` is the track's v1 or v2 result; ``offset_result`` is its +450
    offset-variant result (cyanrip's "Accurip 450:"), shared by both columns
    because it describes the same track. ``lookup`` is the track's ``Accurip:``
    status text — defaulted so a caller without it degrades to the previous
    behaviour rather than failing. Pure and never raises.
    """
    # An exact match outranks everything — a real match is never downgraded.
    if accuraterip_is_match(result):
        return AR_STATE_VERIFIED
    # Partially accurate: the standard checksum missed, the offset variant hit.
    if accuraterip_is_match(offset_result):
        return AR_STATE_OFFSET_VARIANT
    # Nothing matched. Did we have anything to match *against*? Either result
    # carrying our computed checksum means the disc was in the database and this
    # read simply is not one of the stored copies.
    # Nothing matched. Before deciding *why*, ask whether anyone looked: a
    # comparison that never happened cannot have failed, and saying it did is the
    # sharpest way this screen can mislead.
    if accuraterip_lookup_happened(lookup) is False:
        return AR_STATE_NOT_CHECKED
    if lookup and any(token in lookup.casefold() for token in _LOOKUP_FOUND_NOTHING):
        # Looked, and the disc is not in the database. Says nothing about the rip.
        return AR_STATE_ABSENT
    if accuraterip_compared(result, lookup) or accuraterip_compared(
        offset_result, lookup
    ):
        return AR_STATE_NO_MATCH
    if result is None:
        return AR_STATE_NO_DATA
    return AR_STATE_ABSENT


def expected_track_total(
    disc_track_total: int | None, only_tracks: Sequence[int] | None
) -> int | None:
    """How many tracks this rip was **asked** to produce. The missing concept.

    This tiny function exists because the same bug has now shipped four times
    (v0.5.9, twice in v0.5.12, and again in this cycle), and every fix corrected
    one surface instead of naming the thing they disagreed about. There are three
    defensible meanings of "how many tracks should there be", and code that says
    `total` picks one by accident:

    * **the disc's** track count — right for "did we get the whole disc?";
    * **the logged** track count — what a parsed log happens to contain, which
      shrinks when a rip stops early (that is the bug fixed a few hours ago);
    * **the requested** count — the disc's, unless the user deselected tracks in
      the Rip? column, in which case it is what they asked for.

    The last one is what a completeness verdict actually needs, and getting it
    wrong is visible in *both* directions. Using the logged count let a cancelled
    2-of-14 rip call itself "Bit-perfect: all 2 tracks". Then using the disc count
    made a **deliberate** 2-of-14 rip — the Rip? column exists precisely so that is
    possible — warn that "12 tracks were never ripped", which is not a fault, it is
    the user's own choice reported as a failure. Both readings are wrong; neither is
    fixed by patching one renderer.

    ``only_tracks`` is ``RipParameters.only_tracks``: empty means "all of them".
    Returns ``None`` when the disc total is unknown, which callers already treat as
    "fall back to whatever the log contains".
    """
    if only_tracks:
        # A deliberate subset. The user asked for these, so these are all there
        # should be — a complete rip of a selection is COMPLETE.
        return len(only_tracks)
    if disc_track_total and disc_track_total > 0:
        return disc_track_total
    return None


def _shortfall_phrase(never_ripped: int, no_result: int, outcome_status: str) -> str:
    """Name *why* the verdict's numerator falls short of the disc's track count.

    Kept separate and pure so the wording is testable on its own. The two causes
    read very differently to a user — "never extracted" is something they did (or
    a failure that stopped the rip), while "produced no result" means the track is
    on disk but AccurateRip had nothing to say about it — so they are never
    collapsed into one number. When the rip's own outcome explains the first
    cause, it is named: "the rip was cancelled" is the sentence that turns a
    confusing shortfall into an obvious one.
    """
    status = (outcome_status or "").strip().casefold()
    parts: list[str] = []
    if never_ripped:
        noun = "track was" if never_ripped == 1 else "tracks were"
        reason = (
            f"the rip was {status} so " if status in {"cancelled", "failed"} else ""
        )
        parts.append(f"{reason}{never_ripped} {noun} never ripped")
    if no_result:
        noun = "track" if no_result == 1 else "tracks"
        # Wording preserved verbatim from the 2026-07-28 fix — its regression test
        # asserts this exact phrase, and the phrase is right.
        parts.append(f"{no_result} {noun} produced no result at all")
    return "; ".join(parts) if parts else "the rip did not cover the whole disc"


def accuraterip_verdict(
    rip_log: object,
    *,
    disc_track_total: int | None = None,
    outcome_status: str = "",
) -> tuple[str, str]:
    """At-a-glance AccurateRip verdict: ``(message, level)``.

    ``level`` is "ok" (all audio tracks verified — bit-perfect against the
    shared AccurateRip database), "warn" (some but not all matched), or
    "neutral" (none matched — typically a disc nobody has submitted, e.g. a
    CD-R). An empty ``message`` means "show nothing" (no audio tracks parsed).

    ``disc_track_total`` is the number of audio tracks **on the disc**, and it is
    what makes the word "all" mean anything. Without it the denominator can only
    be the number of tracks *in the log*, which is not the same number the moment
    a rip stops early — see below. ``outcome_status`` is the rip's own outcome
    ("success" / "cancelled" / "failed"), used only to explain a shortfall in
    words the reader will recognise. Both are keyword-only and defaulted, so a
    caller that cannot supply them keeps the old behaviour rather than breaking.

    Pure and never-raises (reads via ``getattr``) so it accepts both the
    whipper and cyanrip ``RipLog`` shapes and any partially-parsed log. The
    wording never claims more than AccurateRip returned — this is the trust
    headline, so it must be honest above all.
    """
    total, verified, partial = accuraterip_counts(rip_log)
    if total == 0:
        return "", "neutral"
    audio = _audio_tracks(rip_log)
    # Two different ways a track can be absent from `total`, and the earlier fix
    # only closed one of them:
    #
    #   • It was ripped and failed — present in the log, no CRC, no AccurateRip
    #     line. Caught since 2026-07-28 by comparing against the log's own track
    #     count.
    #   • **It was never ripped at all** — so it is absent from the log entirely,
    #     and the log's track count shrinks with it. Both sides of that comparison
    #     moved together, `missing` stayed 0, and the headline went GREEN.
    #
    # A cancelled rip is exactly the second case, and it shipped: cancelling
    # after two tracks of fourteen produced "✓ Bit-perfect: all 2 tracks verified
    # against AccurateRip (confidence 129+)" — green, on 14% of the disc — while
    # the EAC log beside it correctly said "covers 2 of 14 disc tracks" (found on
    # the rig, 2026-07-30). The exporter was right because it is *given* the disc
    # total; this function had to be given it too. Only the disc's own count can
    # be the denominator, because it is the one number a stopped rip cannot move.
    logged = len(getattr(rip_log, "tracks", ()) or ())
    expected = disc_track_total if disc_track_total and disc_track_total > 0 else logged
    never_ripped = max(0, expected - logged)
    no_result = max(0, logged - total)
    missing = never_ripped + no_result
    if verified == total and missing:
        return (
            f"⚠ {verified} of {expected} tracks verified against AccurateRip — "
            f"{_shortfall_phrase(never_ripped, no_result, outcome_status)} "
            "(see the table)",
            "warn",
        )
    if verified == total:
        # Only count confidences of ACTUAL matches (>= 1, same as
        # accuraterip_is_match). A track can be verified on its v2 while its v1
        # is "present, no match" with confidence 0 — including that 0 would
        # render a misleading "confidence 0+" floor.
        confidences = [
            conf
            for t in audio
            for conf in (
                getattr(getattr(t, "accuraterip_v1", None), "confidence", None),
                getattr(getattr(t, "accuraterip_v2", None), "confidence", None),
            )
            if conf is not None and conf >= 1
        ]
        tail = f" (confidence {min(confidences)}+)" if confidences else ""
        return (
            f"✓ Bit-perfect: all {total} tracks verified against AccurateRip{tail}",
            "ok",
        )
    if verified > 0:
        if partial and verified + partial == total:
            # Every track is accounted for in AccurateRip: some exact, the rest
            # offset-variant. Say so instead of implying the partials "didn't
            # match" — but stay amber, since partial ≠ proven bit-perfect.
            return (
                f"⚠ {verified} of {total} tracks verified exactly against "
                f"AccurateRip; the other {partial} matched an offset-variant "
                "pressing (partially accurate — see the table)",
                "warn",
            )
        tail = (
            f"; {partial} matched an offset-variant pressing (partially accurate)"
            if partial
            else ""
        )
        return (
            f"⚠ {verified} of {total} tracks verified against AccurateRip — "
            f"the rest aren't in the database or didn't match{tail} (see the table)",
            "warn",
        )
    # None verified exactly, but some matched an offset-variant pressing — still
    # better news than "nobody submitted this disc," so say it (amber, not grey).
    if partial:
        return (
            f"⚠ {partial} of {total} tracks matched an offset-variant pressing "
            "(partially accurate); none verified exactly — see the table",
            "warn",
        )
    # The leading "ⓘ" (like ✓/⚠ above) means the status is conveyed by symbol +
    # text, never colour alone — colour-blind and screen-reader users get the
    # same signal as the green/amber/grey tint (ux-design-principles.md #10).
    return (
        "ⓘ AccurateRip: none of these tracks matched the database. That can mean "
        "the disc isn't in AccurateRip (e.g. a burned CD-R or an obscure "
        "pressing), AccurateRip couldn't be reached, or the read offset is wrong "
        "— so the audio is NOT independently verified. The per-track Copy CRCs "
        "below only show the FLAC losslessly encodes what was read; they don't "
        "prove the read itself was correct.",
        "neutral",
    )


def reconcile_ar_ctdb(rip_log: object, ctdb_result: object) -> str | None:
    """Explain an AccurateRip-vs-CTDB result that *looks* contradictory.

    The two checks read as if they disagree to a non-expert: AccurateRip can say
    "12/14 accurate" while CTDB says "no match". They don't actually disagree —
    CTDB folds the WHOLE disc into one CRC, so if even a couple of tracks differ
    from the common pressing (an offset-variant, or a genuinely different read),
    the whole-disc CRC won't be in CTDB. That's the *same* finding AccurateRip
    already reported, seen from a different angle — not a second problem.

    Returns a one-line reconciliation to show under the CTDB verdict, or None
    when there's nothing to reconcile (CTDB matched, isn't a validated no-match,
    or there was no AccurateRip signal to compare against). Pure; reads via
    ``getattr`` and never raises — it backs a results-pane label populated from a
    best-effort parse.

    This only speaks when the CTDB CRC is *hardware-validated* (KDD-16,
    ``crc_validated`` True); before that a no-match is expected noise and
    :func:`platterpus.ui.rip_progress.ctdb_verdict_line` already says so, so
    adding a reconciliation would over-explain a placeholder.
    """
    try:
        verdict = getattr(getattr(ctdb_result, "verdict", None), "value", None)
        if verdict != "no_match":
            return None
        if not getattr(ctdb_result, "crc_validated", False):
            return None
        total, verified, partial = accuraterip_counts(rip_log)
        if total == 0 or (verified == 0 and partial == 0):
            # No AccurateRip signal at all → the two aren't in apparent conflict;
            # the standalone CTDB line already stands alone. (An all-offset-
            # variant disc — verified 0 but partial > 0 — DOES look contradictory
            # next to a CTDB no-match, so it falls through to the partial branch.)
            return None
        if partial > 0:
            return (
                f"Why this and AccurateRip seem to disagree: {partial} track(s) "
                "matched only an offset-variant pressing, so the whole-disc CTDB "
                "CRC won't match the database's common-pressing entries — this is "
                "the SAME finding as AccurateRip above, not a separate problem."
            )
        if verified == total:
            return (
                "AccurateRip verified every track, but CTDB has no matching "
                "whole-disc entry — most likely this exact pressing just hasn't "
                "been submitted to CTDB. AccurateRip is the authority here."
            )
        # verified > 0 and the rest are NOT in AccurateRip at all (not
        # offset-variants). AccurateRip made no finding about those tracks, so
        # this is NOT "the same finding" — a CTDB no-match here is unsurprising
        # and doesn't mean the rip is wrong. Say exactly that, and don't claim a
        # mismatch AccurateRip never reported.
        return (
            "Some of these tracks aren't in AccurateRip at all, so the whole-disc "
            "CTDB CRC has nothing in the database to match against — this doesn't "
            "mean your rip is wrong; AccurateRip is the per-track authority."
        )
    except Exception:  # noqa: BLE001 — a results-pane footnote must never crash
        return None
