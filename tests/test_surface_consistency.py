"""Fitness test: every surface must tell the same story about one rip.

Platterpus reports a rip through four independent renderings of a single parsed
``RipLog`` — the **EAC-compatible log** (the durable text artifact), the
**JSON report** (the machine record), the **verdict banner** (the trust
headline), and the **status line**. They are written in different modules by
different code, and nothing structural stops one from drifting.

Four shipped defects in a single week were all exactly that drift:

* the EAC log called offset-variant tracks "not present in AccurateRip" while
  cyanrip's log and our own verdict banner said they matched (v0.5.8);
* an interrupted rip rendered as a clean, complete one because the renderer was
  never told the outcome (v0.5.8);
* a re-read track's Test & Copy proof reached the report but not the log, and a
  track whose re-reads *disagreed* was flagged on screen but not in the log
  (v0.5.9);
* a swapped-in re-rip's CRC was right in cyanrip's addendum and wrong in both
  our log and our report (v0.5.10).

Individually those are four bugs. Together they are one: **a fact reaches some
surfaces and not others.** Unit tests didn't catch them because each surface
was correct *by its own lights* — the disagreement only exists between them.

So this file asserts the agreements, not the outputs. It is a fitness function
in the shape of ``test_gui_thread_discipline.py``: cheap, Qt-free, and aimed at
a class of bug rather than a single behaviour. Scenarios are modelled on the
real Police-disc runs, because that disc produced every one of the defects
above.

When you add a surface, add it here. When you add a fact a surface can report,
add the agreement it owes the others.

**What this file cannot catch, by construction.** It compares surfaces against
each other, so it is blind to a fact that is wrong *before* any of them render
it — every surface then agrees, and agrees wrongly. That is precisely the
v0.5.10 CRC defect: the parsed ``RipLog`` itself carried the discarded read's
CRC, so log, report, and table were perfectly consistent about the wrong bytes.
Guarding the *input* is a different job, done where the input is built —
``test_auto_fix_convergence.py`` for the post-rip enrichers, the parser tests
for what comes out of cyanrip. Both halves are needed; neither substitutes for
the other.

Each assertion here was mutation-checked against the defect it exists for:
deleting the offset-variant branch, the read-stability line, the incomplete-rip
banner, or the Test/Copy pair each turns exactly one test red, and rendering a
CRC the report doesn't have turns three red.
"""

from __future__ import annotations

import re

from platterpus.eac_log_export import render_eac_style_log
from platterpus.parsers.rip_log import (
    AccurateRipResult,
    RipLog,
    RippingInfo,
    TrackResult,
    track_accuraterip_verified,
)
from platterpus.rip_report import build_report
from platterpus.verdict import accuraterip_counts, accuraterip_verdict

# --- scenario builders (modelled on the real hardware runs) ------------------


def _verified(crc: str, confidence: int = 200) -> AccurateRipResult:
    return AccurateRipResult(
        version=2,
        result="accurately ripped",
        confidence=confidence,
        local_crc=crc,
    )


def _offset_variant(crc: str) -> AccurateRipResult:
    """A +450 offset-variant match: in the database, but not an exact match."""
    return AccurateRipResult(
        version=2,
        result="matches Accurip DB, track is partially accurately ripped",
        confidence=200,
        local_crc=crc,
    )


def _clean_disc() -> RipLog:
    """Every track exactly verified — the boring case that must stay boring."""
    return RipLog(
        log_creator="cyanrip 0.9.3",
        ripping_info=RippingInfo(drive="PIONEER BDR-209D", read_offset_correction=667),
        tracks=tuple(
            TrackResult(
                number=n,
                filename=f"{n:02d}.flac",
                copy_crc=f"AAAA000{n}",
                status="ripped successfully",
                accuraterip_v2=_verified(f"BBBB000{n}"),
            )
            for n in range(1, 5)
        ),
        accuraterip_summary="4/4 tracks ripped accurately (AccurateRip)",
        health_status="No errors occurred",
    )


def _police_disc() -> RipLog:
    """The real shape: mostly exact, two offset-variant, one never converged.

    Track 3 is the one that has never read the same way twice on real hardware;
    track 5 converged on a re-read and was swapped in.
    """
    tracks = [
        TrackResult(
            number=n,
            filename=f"{n:02d}.flac",
            copy_crc=f"CCCC000{n}",
            status="ripped successfully",
            accuraterip_v2=_verified(f"DDDD000{n}"),
        )
        for n in (1, 2, 4)
    ]
    tracks.append(
        TrackResult(
            number=3,
            filename="03.flac",
            copy_crc="3D8FCF0C",
            status="ripped successfully",
            accuraterip_offset=_offset_variant("BF62B1DA"),
            secure_rerip_converged=False,  # re-read, reads disagreed
        )
    )
    tracks.append(
        TrackResult(
            number=5,
            filename="05.flac",
            copy_crc="E0036697",
            status="ripped successfully",
            accuraterip_offset=_offset_variant("4CCBCF89"),
            secure_rerip_converged=True,  # re-read, reads agreed, swapped in
        )
    )
    return RipLog(
        log_creator="cyanrip 0.9.3",
        ripping_info=RippingInfo(drive="PIONEER BDR-209D", read_offset_correction=667),
        tracks=tuple(sorted(tracks, key=lambda t: t.number)),
        accuraterip_summary="3/5 tracks ripped accurately (AccurateRip)",
        partially_accurate_summary="2/2 tracks ripped partially accurately",
        health_status="No errors occurred",
    )


def _unknown_disc() -> RipLog:
    """A disc nobody has submitted (a CD-R): no AR data at all, and that's fine."""
    return RipLog(
        log_creator="cyanrip 0.9.3",
        tracks=tuple(
            TrackResult(number=n, filename=f"{n:02d}.flac", copy_crc=f"EEEE000{n}")
            for n in range(1, 4)
        ),
        health_status="No errors occurred",
    )


SCENARIOS = {
    "clean": _clean_disc,
    "police": _police_disc,
    "unknown": _unknown_disc,
}


def _surfaces(rip_log: RipLog, **render_kwargs: object) -> tuple[str, dict, str, str]:
    """Render one RipLog through every surface. Returns (log_text, report, msg, level)."""
    text = render_eac_style_log(rip_log, **render_kwargs)  # type: ignore[arg-type]
    report = build_report(rip_log)
    message, level = accuraterip_verdict(rip_log)
    return text, report, message, level


# --- the agreements ----------------------------------------------------------


def test_every_track_crc_is_identical_in_the_log_and_the_report() -> None:
    """A CRC identifies specific bytes; two surfaces naming different ones is a lie.

    This is the v0.5.10 defect in general form: the log rendered the discarded
    read's CRC while the file on disk (and cyanrip's own addendum) had another.
    """
    for name, build in SCENARIOS.items():
        rip_log = build()
        text, report, _, _ = _surfaces(rip_log)
        for track, entry in zip(rip_log.tracks, report["tracks"], strict=True):
            assert entry["copy_crc"] == track.copy_crc, (
                f"{name}: report CRC disagrees with the parsed log for track "
                f"{track.number}"
            )
            assert f"Copy CRC {track.copy_crc}" in text, (
                f"{name}: track {track.number}'s CRC {track.copy_crc} is in the "
                "report but not in the EAC-compatible log"
            )


def test_no_crc_appears_in_the_log_that_no_track_actually_has() -> None:
    """The inverse direction: the log may not invent or retain a stale CRC."""
    for name, build in SCENARIOS.items():
        rip_log = build()
        text, _, _, _ = _surfaces(rip_log)
        known = {t.copy_crc for t in rip_log.tracks}
        rendered = set(re.findall(r"(?:Copy|Test) CRC ([0-9A-F]{8})", text))
        assert rendered <= known, (
            f"{name}: the log shows CRC(s) {rendered - known} that belong to no "
            "track — a stale or invented value"
        )


def test_verified_track_counts_agree_across_all_three_surfaces() -> None:
    """ "How many tracks are proven?" must have exactly one answer."""
    for name, build in SCENARIOS.items():
        rip_log = build()
        text, report, message, _ = _surfaces(rip_log)
        expected = sum(1 for t in rip_log.tracks if track_accuraterip_verified(t))

        in_report = sum(1 for t in report["tracks"] if t["accuraterip_verified"])
        in_log = text.count("Accurately ripped (confidence")
        assert in_report == expected, f"{name}: report verified-count disagrees"
        assert in_log == expected, f"{name}: EAC log verified-count disagrees"

        # The verdict headline quotes the count in prose; when it does, it must be
        # the same number. (An all-verified or nothing-verified disc words it
        # without a count, which is fine — there is nothing to disagree with.)
        quoted = re.search(r"(\d+) of (\d+) tracks", message)
        if quoted:
            assert int(quoted.group(1)) == expected, (
                f"{name}: the verdict banner claims {quoted.group(1)} verified "
                f"tracks but {expected} are"
            )


def test_an_offset_variant_track_is_never_called_absent_or_exact() -> None:
    """The v0.5.8 defect: three surfaces disagreeing about the same two tracks.

    An offset-variant match is *in* the database (so "not present" is false) but
    is not an exact match (so counting it as verified over-claims). Every surface
    has to land in that middle.
    """
    rip_log = _police_disc()
    text, report, message, level = _surfaces(rip_log)
    variants = [t for t in rip_log.tracks if t.accuraterip_offset is not None]
    assert variants, "scenario must contain offset-variant tracks"

    assert "not present in AccurateRip" not in text
    assert text.count("offset-variant") == len(variants)
    for track in variants:
        entry = next(t for t in report["tracks"] if t["number"] == track.number)
        assert entry["accuraterip_verified"] is False, (
            f"track {track.number} matched only an offset-variant pressing; the "
            "report must not call it verified"
        )
    assert level == "warn", "a partially-accurate disc is not a clean pass"
    _, _, partial = accuraterip_counts(rip_log)
    assert partial == len(variants)


def test_a_track_whose_rereads_disagreed_is_flagged_everywhere() -> None:
    """The v0.5.9 defect: the app warned on screen, the durable log did not."""
    rip_log = _police_disc()
    text, report, _, _ = _surfaces(rip_log)
    unstable = [t for t in rip_log.tracks if t.secure_rerip_converged is False]
    assert unstable, "scenario must contain a non-converged track"

    for track in unstable:
        entry = next(t for t in report["tracks"] if t["number"] == track.number)
        assert entry["secure_rerip_converged"] is False, (
            f"track {track.number}'s measured non-convergence is missing from the "
            "machine record"
        )
        assert f"track(s) {track.number}" in text, (
            f"track {track.number} did not read reproducibly, but the "
            "EAC-compatible log's summary never says so"
        )
    assert "not confirmed reproducible" in text


def test_a_converged_track_earns_the_test_and_copy_pair_in_the_log() -> None:
    """Convergence is EAC's Test & Copy proof; having it and not saying it is a loss."""
    rip_log = _police_disc()
    text, report, _, _ = _surfaces(rip_log)
    converged = [t for t in rip_log.tracks if t.secure_rerip_converged is True]
    assert converged, "scenario must contain a converged track"

    for track in converged:
        assert f"Test CRC {track.copy_crc}" in text
        entry = next(t for t in report["tracks"] if t["number"] == track.number)
        assert entry["secure_rerip_converged"] is True


def test_a_single_read_track_claims_no_second_read_anywhere() -> None:
    """The mirror rule: never render proof of a read that didn't happen."""
    rip_log = _clean_disc()
    text, report, _, _ = _surfaces(rip_log)
    assert "Test CRC" not in text
    assert "Read stability" not in text
    assert all(t["secure_rerip_converged"] is None for t in report["tracks"])


def test_an_interrupted_rip_is_declared_in_the_durable_log() -> None:
    """The v0.5.8 HIGH defect: a cancelled rip that read as a clean complete one."""
    rip_log = _clean_disc()  # 4 tracks written…
    text = render_eac_style_log(
        rip_log,
        outcome_status="cancelled",
        disc_track_total=14,  # …of a 14-track disc
    )
    assert "INCOMPLETE RIP (cancelled)" in text
    assert "4" in text and "14" in text
    # And the notice sits ABOVE the checksum, so it cannot be stripped silently.
    assert text.index("INCOMPLETE RIP") < text.index("Platterpus log checksum")


def test_a_complete_rip_carries_no_incomplete_banner() -> None:
    """The same fact in the other direction — no crying wolf on a good rip."""
    text, _, _, _ = _surfaces(_clean_disc(), outcome_status="success")
    assert "INCOMPLETE RIP" not in text


def test_a_disc_absent_from_accuraterip_over_claims_nowhere() -> None:
    """No AR data is not a failure and not a pass — every surface must stay neutral."""
    rip_log = _unknown_disc()
    text, report, _, level = _surfaces(rip_log)
    assert level == "neutral"
    assert "Accurately ripped (confidence" not in text
    assert "offset-variant" not in text
    assert all(t["accuraterip_verified"] is False for t in report["tracks"])
