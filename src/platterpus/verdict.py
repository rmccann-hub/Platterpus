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

from platterpus.parsers.rip_log import track_accuraterip_verified


def accuraterip_counts(rip_log: object) -> tuple[int, int, int]:
    """Return ``(total_audio, verified, partial)`` for a rip log.

    ``total_audio`` counts tracks AccurateRip has anything to say about (a Copy
    CRC or any AR result), ``verified`` those that matched exactly (confidence
    ≥ 1), and ``partial`` those that matched only the offset-variant pressing
    ("Accurip 450") without an exact match. The single source both
    :func:`accuraterip_verdict` and :func:`reconcile_ar_ctdb` read, so the
    banner, the JSON, and the reconciliation line can never disagree on the
    tally. Pure; reads via ``getattr`` and never raises.
    """
    tracks = getattr(rip_log, "tracks", ()) or ()
    audio = [
        t
        for t in tracks
        if getattr(t, "copy_crc", "")
        or getattr(t, "accuraterip_v1", None) is not None
        or getattr(t, "accuraterip_v2", None) is not None
        or getattr(t, "accuraterip_offset", None) is not None
    ]
    total = len(audio)
    verified = sum(1 for t in audio if track_accuraterip_verified(t))
    partial = sum(
        1
        for t in audio
        if not track_accuraterip_verified(t)
        and getattr(t, "accuraterip_offset", None) is not None
    )
    return total, verified, partial


def accuraterip_verdict(rip_log: object) -> tuple[str, str]:
    """At-a-glance AccurateRip verdict: ``(message, level)``.

    ``level`` is "ok" (all audio tracks verified — bit-perfect against the
    shared AccurateRip database), "warn" (some but not all matched), or
    "neutral" (none matched — typically a disc nobody has submitted, e.g. a
    CD-R). An empty ``message`` means "show nothing" (no audio tracks parsed).

    Pure and never-raises (reads via ``getattr``) so it accepts both the
    whipper and cyanrip ``RipLog`` shapes and any partially-parsed log. The
    wording never claims more than AccurateRip returned — this is the trust
    headline, so it must be honest above all.
    """
    total, verified, partial = accuraterip_counts(rip_log)
    if total == 0:
        return "", "neutral"
    tracks = getattr(rip_log, "tracks", ()) or ()
    audio = [
        t
        for t in tracks
        if getattr(t, "copy_crc", "")
        or getattr(t, "accuraterip_v1", None) is not None
        or getattr(t, "accuraterip_v2", None) is not None
        or getattr(t, "accuraterip_offset", None) is not None
    ]
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
