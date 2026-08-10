"""The offset-variant sentence must count the FINAL tracks, not the first pass.

**Measured on real hardware, 2026-08-07** — the Police re-rip, the first disc ever
to take the auto-fix path on a released build. Tracks 3 and 5 both missed
AccurateRip on the whole-disc pass and were re-ripped. Track 3's re-read matched
exactly; track 5's still matched only the +450 offset-variant pressing.

So the truth afterwards is **one** partially-accurate track. The verdict banner
said so. The footnote beneath it said "2 of 14", because it was a string rendered
while parsing the whole-disc log and never recomputed once the addendum superseded
those two tracks' AccurateRip results.

Both numbers went into the same `.platterpus.json` and onto the same results pane:

    verdict:                    "…the other 1 matched an offset-variant pressing"
    partially_accurate_summary: "2 of 14 tracks matched only an offset-variant…"

`accuraterip_counts` documents itself as the single source "so the banner, the
JSON, and the reconciliation line can never disagree on the tally". This field was
the one that bypassed it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from platterpus.rip_report import _final_partial_summary
from platterpus.verdict import accuraterip_counts


@dataclass
class _AR:
    """An AccurateRip result, in the shape `accuraterip_is_match` reads."""

    result: str = ""
    confidence: int | None = None
    local_crc: str = ""


@dataclass
class _Track:
    number: int
    copy_crc: str = "AAAABBBB"
    accuraterip_v1: _AR | None = None
    accuraterip_v2: _AR | None = None
    accuraterip_offset: _AR | None = None


@dataclass
class _RipLog:
    tracks: list[_Track] = field(default_factory=list)
    partially_accurate_reported: str = ""
    partially_accurate_summary: str = ""


def _verified(number: int) -> _Track:
    """A track AccurateRip matched exactly."""
    return _Track(
        number=number,
        accuraterip_v1=_AR("accurately ripped, confidence 128", 128, "AAAA1111"),
        accuraterip_v2=_AR("accurately ripped, confidence 200", 200, "BBBB2222"),
    )


def _offset_variant(number: int) -> _Track:
    """A track that matched ONLY the +450 offset-variant pressing."""
    return _Track(
        number=number,
        accuraterip_v1=_AR("not found, either a new pressing, or bad rip", None, "C1"),
        accuraterip_v2=_AR("not found, either a new pressing, or bad rip", None, "C2"),
        accuraterip_offset=_AR(
            "matches Accurip DB, confidence 200, track is partially accurately ripped",
            200,
            "4CCBCF89",
        ),
    )


def _police_disc_after_autofix() -> _RipLog:
    """The measured case: 14 tracks, track 5 offset-variant, everything else exact.

    ``partially_accurate_reported`` is the ripper's own whole-disc-pass fraction —
    ``2/14`` — kept verbatim, because that IS what the ripper said and the field
    exists to preserve it. The rendered sentence must not repeat it.
    """
    tracks = [_verified(n) for n in range(1, 15)]
    tracks[4] = _offset_variant(5)  # track 5, 0-indexed
    return _RipLog(tracks=tracks, partially_accurate_reported="2/14")


def test_the_counts_see_one_partial_not_two() -> None:
    """The floor: the fixture must actually model the measured disc."""
    total, verified, partial = accuraterip_counts(_police_disc_after_autofix())
    assert total == 14
    assert verified == 13
    assert partial == 1


def test_the_sentence_counts_the_final_tracks_not_the_ripper_s_fraction() -> None:
    """**The regression.** Before the fix this rendered the ripper's ``2``."""
    summary = _final_partial_summary(_police_disc_after_autofix()) or ""
    assert summary, "a disc with a partial track must say so"
    assert "1 of 14" in summary, (
        f"expected the FINAL count of offset-variant tracks (1), got: {summary!r}. "
        f"Rendering the ripper's whole-disc-pass fraction (2/14) contradicts the "
        f"verdict banner on the same screen."
    )
    assert "2 of 14" not in summary


def test_the_stale_parse_time_string_is_not_used_even_when_present() -> None:
    """Prove the fix reads the tracks, not the attribute sitting right there.

    Without this the implementation could keep returning
    ``rip_log.partially_accurate_summary`` and pass the test above whenever the
    parser happened to be right — the two agree on most discs, which is exactly
    why this went unnoticed until a disc where they differed.
    """
    rip_log = _police_disc_after_autofix()
    rip_log.partially_accurate_summary = "2 of 14 tracks matched only an offset-variant"
    summary = _final_partial_summary(rip_log) or ""
    assert "1 of 14" in summary, (
        f"the stale attribute won over the counted tracks: {summary!r}"
    )


def test_a_clean_disc_counts_zero_rather_than_inheriting_a_stale_number() -> None:
    """Zero partials must render **zero**, whatever the ripper's fraction said.

    This is the same regression from the other side, and it is the one that would
    bite hardest: if every partial track were rescued by the auto-fix, the stale
    sentence would announce offset-variant tracks on a disc that now has none.

    Note what this does NOT assert. The renderer still emits a sentence for zero
    ("0 of 14 tracks matched only…"), which is pre-existing behaviour and unchanged
    here — the ripper printed the line, so we describe it. Whether a perfect rip
    should carry that footnote at all is a separate question about wording, not
    about correctness, and folding it into a correctness fix would make the fix
    harder to review and the behaviour change harder to find later.
    """
    clean = _RipLog(
        tracks=[_verified(n) for n in range(1, 15)],
        # The ripper's whole-disc pass found two; the auto-fix rescued both.
        partially_accurate_reported="2/14",
    )
    summary = _final_partial_summary(clean) or ""
    assert "0 of 14" in summary, (
        f"every partial track was rescued, so the count is zero; got {summary!r}"
    )
    assert "2 of 14" not in summary


def test_no_reported_fraction_falls_back_rather_than_going_silent() -> None:
    """Without the ripper's fraction there is nothing to recompute against.

    **The fix's own regression, caught by the existing UI tests.** The first
    version returned ``None`` here, which did not merely decline to correct the
    sentence — it *deleted* the footnote for every log shape that never carried a
    ``Tracks ripped partially accurately:`` line (whipper-era logs, and any
    partial parse). Suppressing a right answer is not an improvement over
    correcting a wrong one.
    """
    parsed = "1/3 tracks partial"
    no_fraction = _RipLog(
        tracks=[_verified(1)],
        partially_accurate_reported="",
        partially_accurate_summary=parsed,
    )
    assert _final_partial_summary(no_fraction) == parsed

    # And with nothing to fall back to either, silence is correct.
    empty = _RipLog(tracks=[_verified(1)], partially_accurate_reported="")
    assert _final_partial_summary(empty) is None


def test_it_never_raises_on_a_malformed_rip_log() -> None:
    """A summary line must never be the thing that stops a report being written."""

    class _Hostile:
        @property
        def tracks(self) -> list[object]:
            raise RuntimeError("tracks exploded")

        partially_accurate_reported = "1/14"

    _final_partial_summary(_Hostile())  # must not raise


def test_the_verdict_and_the_footnote_now_agree() -> None:
    """The property that was violated, asserted directly.

    Two surfaces, one fact. Compare the number each renders rather than trusting
    that they share a code path — sharing one today does not keep them sharing it.
    """
    import re

    from platterpus.verdict import accuraterip_verdict

    rip_log = _police_disc_after_autofix()
    message, _level = accuraterip_verdict(rip_log, disc_track_total=14)
    footnote = _final_partial_summary(rip_log) or ""

    banner_partial = re.search(r"the other (\d+) matched an offset-variant", message)
    footnote_partial = re.search(r"(\d+) of \d+ tracks matched only", footnote)
    assert banner_partial, f"banner did not state a partial count: {message!r}"
    assert footnote_partial, f"footnote did not state a partial count: {footnote!r}"
    assert banner_partial.group(1) == footnote_partial.group(1), (
        f"banner says {banner_partial.group(1)} partial track(s), footnote says "
        f"{footnote_partial.group(1)} — same fact, same screen, two numbers"
    )


def test_the_REPORT_carries_the_final_count_not_the_parse_time_string() -> None:
    """**The wiring, through the real `build_report`.**

    The tests above exercise the helper. That is not the same as exercising the
    change: the first version of this file passed unaltered against a revert of
    the report assembly, because it called the helper directly and the helper was
    never what broke. A test that cannot fail when the fix is removed is not a
    regression test — so this one goes through the actual builder and reads the
    field a consumer reads.
    """
    rip_log = _police_disc_after_autofix()
    # The stale string the parser would have produced, present exactly as it is on
    # the real artifact, so the assembly has something wrong to prefer.
    rip_log.partially_accurate_summary = (
        "2 of 14 tracks matched only an offset-variant pressing (partially accurate)"
    )

    from platterpus.rip_report import build_report

    report = build_report(
        rip_log, disc_track_total=14, generated_at="2026-08-07T00:00:00"
    )

    summary = report.get("partially_accurate_summary") or ""
    assert "1 of 14" in summary, (
        f"the report carried {summary!r} — the parse-time sentence, not the count "
        f"of the tracks it actually shipped"
    )
    # And the ripper's own fraction is still preserved verbatim beside it, because
    # that field's entire job is being what the ripper said.
    assert report.get("partially_accurate_reported") == "2/14"

    # The property that was violated: the two statements in one report agree.
    message = (report.get("verdict") or {}).get("message") or ""
    assert "the other 1 matched an offset-variant" in message, message
