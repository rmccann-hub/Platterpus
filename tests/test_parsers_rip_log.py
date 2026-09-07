"""Tests for platterpus.parsers.rip_log.

Primary fixture (`rip_log_real_whipper_0_7.log`) is whipper-team/whipper's
own test fixture from master — i.e., a real log produced by whipper,
not hand-authored. Source:
https://github.com/whipper-team/whipper/blob/master/whipper/test/test_result_logger.log
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from platterpus.parsers.rip_log import (
    AccurateRipResult,
    RipLog,
    RippingInfo,
    TrackResult,
    accuraterip_is_match,
    parse_rip_log,
    track_accuraterip_verified,
)

FIXTURES = Path(__file__).parent / "fixtures"
REAL_LOG = "rip_log_real_whipper_0_7.log"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text()


# --- Top-level metadata ---------------------------------------------------


def test_parse_log_creator_and_creation_date() -> None:
    log = parse_rip_log(_read(REAL_LOG))
    assert log.log_creator.startswith("whipper 0.7.4")
    assert log.creation_date == "2019-10-26T14:25:02Z"


def test_parse_sha256_hash() -> None:
    log = parse_rip_log(_read(REAL_LOG))
    assert log.sha256_hash.startswith("2B176D8C")
    assert len(log.sha256_hash) == 64  # SHA-256 = 64 hex chars


# --- Ripping info (the EAC-equivalent archival block) --------------------


def test_parse_ripping_info_drive() -> None:
    info = parse_rip_log(_read(REAL_LOG)).ripping_info
    assert "HL-DT-ST" in info.drive
    assert "WH14NS40" in info.drive
    assert "revision 1.03" in info.drive


def test_parse_ripping_info_extraction_engine() -> None:
    info = parse_rip_log(_read(REAL_LOG)).ripping_info
    assert "cdparanoia" in info.extraction_engine


def test_parse_ripping_info_cache_and_offset() -> None:
    info = parse_rip_log(_read(REAL_LOG)).ripping_info
    assert info.defeat_audio_cache is True
    assert info.read_offset_correction == 6


def test_parse_ripping_info_overread_and_gap() -> None:
    info = parse_rip_log(_read(REAL_LOG)).ripping_info
    assert info.overread_lead_out is False
    assert "cdrdao" in info.gap_detection
    assert info.cd_r_detected is False


# --- Tracks ---------------------------------------------------------------


def test_parse_track_count() -> None:
    log = parse_rip_log(_read(REAL_LOG))
    assert len(log.tracks) == 2


def test_parse_track_one_basic_fields() -> None:
    track = parse_rip_log(_read(REAL_LOG)).tracks[0]
    assert track.number == 1
    assert "Three Little Birds.flac" in track.filename
    assert track.peak_level is not None
    assert abs(track.peak_level - 0.90036) < 1e-6
    # Pre-emphasis is empty in this fixture -> None (we can't claim
    # either way).
    assert track.pre_emphasis is None
    assert track.extraction_speed == 7.0
    assert track.extraction_quality == 100.0
    assert track.test_crc == "0025D726"
    assert track.copy_crc == "0025D726"
    assert track.status == "Copy OK"


def test_parse_track_one_accuraterip_v1() -> None:
    ar = parse_rip_log(_read(REAL_LOG)).tracks[0].accuraterip_v1
    assert ar is not None
    assert ar.version == 1
    assert ar.result == "Found, exact match"
    assert ar.confidence == 14
    assert ar.local_crc == "95E6A189"
    assert ar.remote_crc == "95E6A189"


def test_parse_track_one_accuraterip_v2() -> None:
    ar = parse_rip_log(_read(REAL_LOG)).tracks[0].accuraterip_v2
    assert ar is not None
    assert ar.version == 2
    assert ar.confidence == 11
    assert ar.local_crc == "113FA733"


def test_parse_track_two_distinct_from_track_one() -> None:
    """Track 2 must not bleed track 1's data — header transitions correctly."""
    tracks = parse_rip_log(_read(REAL_LOG)).tracks
    assert tracks[1].number == 2
    assert tracks[1].test_crc == "F77C14CB"  # different from track 1
    assert tracks[1].extraction_speed == 7.7  # different from track 1


# --- Status section -------------------------------------------------------


def test_parse_status_summary_and_health() -> None:
    log = parse_rip_log(_read(REAL_LOG))
    assert log.accuraterip_summary == "All tracks accurately ripped"
    assert log.health_status == "No errors occurred"


# --- Defensive edge cases -------------------------------------------------


def test_parse_empty_input_returns_empty_log() -> None:
    log = parse_rip_log("")
    assert log.tracks == ()
    assert log.log_creator == ""
    assert log.sha256_hash == ""
    assert log.ripping_info == RippingInfo()


def test_parse_truncated_log_without_status_section() -> None:
    """A rip killed mid-write should still parse partial output."""
    text = (
        "Log created by: whipper 0.10.0\n"
        "\n"
        "Tracks:\n"
        "  1:\n"
        "    Filename: track01.flac\n"
        "    Peak level: 0.5\n"
        "    Test CRC: AAAABBBB\n"
        "    Copy CRC: AAAABBBB\n"
        "    Status: Copy OK\n"
    )
    log = parse_rip_log(text)
    assert len(log.tracks) == 1
    assert log.tracks[0].number == 1
    assert log.tracks[0].test_crc == "AAAABBBB"
    assert log.accuraterip_summary == ""


def test_parse_handles_ar_missing_from_database() -> None:
    """When a track isn't in AccurateRip, the Result line says so and
    the CRC fields are typically blank. We should report this state
    correctly rather than crashing."""
    text = (
        "Tracks:\n"
        "  1:\n"
        "    Filename: track01.flac\n"
        "    Test CRC: AAAABBBB\n"
        "    Copy CRC: AAAABBBB\n"
        "    AccurateRip v2:\n"
        "      Result: Track not present in AccurateRip database\n"
        "      Confidence: 0\n"
        "      Local CRC:\n"
        "      Remote CRC:\n"
        "    Status: Copy OK\n"
    )
    log = parse_rip_log(text)
    ar = log.tracks[0].accuraterip_v2
    assert ar is not None
    assert ar.result.startswith("Track not present")
    assert ar.confidence == 0
    assert ar.local_crc is None
    assert ar.remote_crc is None


def test_track_result_is_frozen() -> None:
    t = TrackResult(number=1)
    with pytest.raises(FrozenInstanceError):
        t.number = 2  # type: ignore[misc]


def test_ripping_info_is_frozen() -> None:
    info = RippingInfo()
    with pytest.raises(FrozenInstanceError):
        info.drive = "x"  # type: ignore[misc]


def test_accuraterip_result_is_frozen() -> None:
    ar = AccurateRipResult(version=1)
    with pytest.raises(FrozenInstanceError):
        ar.confidence = 5  # type: ignore[misc]


# --- The shared "is verified?" rule (one source of truth for every surface) --


def test_accuraterip_is_match_requires_confidence_at_least_one() -> None:
    # A real match (confidence >= 1) — whichever wording the backend used.
    assert accuraterip_is_match(
        AccurateRipResult(version=1, result="Found, exact match", confidence=12)
    )
    assert accuraterip_is_match(
        AccurateRipResult(
            version=2, result="accurately ripped, confidence 3", confidence=3
        )
    )
    # Not a match: None, 0, or absent — these can never read as verified.
    assert not accuraterip_is_match(None)
    assert not accuraterip_is_match(AccurateRipResult(version=1, confidence=None))
    assert not accuraterip_is_match(
        AccurateRipResult(version=1, result="Found, exact match", confidence=0)
    )


def test_track_accuraterip_verified_uses_either_version() -> None:
    # Verified if EITHER v1 or v2 is a match…
    v2_only = TrackResult(
        number=1, accuraterip_v2=AccurateRipResult(version=2, confidence=5)
    )
    assert track_accuraterip_verified(v2_only)
    # …and not verified when neither is.
    neither = TrackResult(
        number=2,
        copy_crc="ABCD1234",
        accuraterip_v1=AccurateRipResult(version=1, confidence=0),
    )
    assert not track_accuraterip_verified(neither)


# --- rip_log.py's mutation survivors, 2026-09-06 -----------------------------
#
# 72.5% under the sweep. The survivors cluster in the three places this module
# actually decides something: whether a track counts as VERIFIED (the definition
# every surface reuses), whether it needed unusual read effort, and what the
# parsed record's defaults claim before anything has been parsed at all.


def test_the_parsed_record_is_FROZEN() -> None:
    """`@dataclass(frozen=True)` on `RipLog`, and the mutant unfreezes it.

    The parsed log is passed to the report writer, the EAC exporter, the verdict
    helpers and the UI. A mutable one lets any of them quietly edit the record the
    others are about to read — and the archival artifacts are generated from it, so
    the edit would reach the disc. `AccurateRipResult` already has this test; the
    container that holds them did not.
    """
    log = RipLog()
    with pytest.raises(FrozenInstanceError):
        log.log_truncated = True  # type: ignore[misc]

    track = TrackResult(number=1)
    with pytest.raises(FrozenInstanceError):
        track.copy_crc = "DEADBEEF"  # type: ignore[misc]


def test_a_freshly_parsed_log_claims_NEITHER_truncation_NOR_incompleteness() -> None:
    """Both flags default `False`, and both mutants default them `True`.

    These are claims *against* a log: "this was cut off mid-write" and "the last
    track's record is incomplete". Defaulting either to True means every ordinary
    rip carries the caveat, which is the crying-wolf direction — and the truncation
    flag is the one that turns "12 tracks were never ripped" into "we cannot say",
    so inverting it silences a real finding on real discs.
    """
    fresh = RipLog()
    assert fresh.log_truncated is False
    assert fresh.last_track_incomplete is False

    # And a real, complete log parses to the same answer — the defaults are not
    # merely declared, they survive a parse.
    parsed = parse_rip_log(_read(REAL_LOG))
    assert parsed.log_truncated is False
    assert parsed.last_track_incomplete is False
    assert parsed.tracks, "the real fixture parsed no tracks, so this proves nothing"


def test_an_all_zero_local_crc_is_NOT_a_match_but_an_empty_one_is_no_evidence() -> None:
    """`local_crc.strip("0Xx") == ""` — the three mutants each break one half.

    An all-zero CRC means the checksum was never computed, so a confidence beside
    it is not a verification. An **empty** CRC is different: a whipper log can
    carry a real match without one, and treating empty as zero silently discards
    genuine verifications — under-claiming, which this module's comment calls as
    much a bug as the over-claim.
    """
    # All zeros, any width, with or without the 0x prefix → never verified.
    for zero in ("00000000", "0", "0x00000000", "0X0000"):
        assert not accuraterip_is_match(
            AccurateRipResult(version=2, confidence=200, local_crc=zero)
        ), zero

    # Empty or absent → not evidence of anything, so the confidence decides.
    for empty in ("", None):
        assert accuraterip_is_match(
            AccurateRipResult(version=2, confidence=200, local_crc=empty)
        ), repr(empty)

    # A real CRC with a real confidence is the ordinary verified case.
    assert accuraterip_is_match(
        AccurateRipResult(version=2, confidence=1, local_crc="22B9924D")
    )


def test_confidence_of_exactly_one_is_the_verification_floor() -> None:
    """`confidence >= 1`, and the mutants move the floor to 2.

    One other person's disc agreeing with yours is the smallest real corroboration
    AccurateRip offers, and it is what every surface in this program means by
    "verified". Raising the floor silently downgrades those tracks everywhere at
    once.
    """
    assert accuraterip_is_match(AccurateRipResult(version=2, confidence=1))
    assert not accuraterip_is_match(AccurateRipResult(version=2, confidence=0))


def test_read_effort_is_flagged_by_a_MEASURED_non_convergence_or_the_pass_count() -> (
    None
):
    """`secure_rerip_converged is False` — identity, tri-state — or `>= THRESHOLD`.

    `None` means the track was never re-read, which is not a warning sign; only a
    measured `False` is. And the pass-count arm is `>=`, so a track at exactly the
    threshold is flagged — the `>` mutant lets the worst permitted case through.
    """
    from platterpus.parsers.rip_log import (
        HEAVY_REREAD_THRESHOLD,
        track_read_effort_flag,
    )

    # A measured non-convergence, on its own.
    assert track_read_effort_flag(TrackResult(number=1, secure_rerip_converged=False))
    # Not measured → not a warning.
    assert not track_read_effort_flag(
        TrackResult(number=2, secure_rerip_converged=None)
    )
    assert not track_read_effort_flag(
        TrackResult(number=3, secure_rerip_converged=True)
    )

    # Exactly the threshold is flagged; one below is not.
    assert track_read_effort_flag(
        TrackResult(number=4, rip_count=HEAVY_REREAD_THRESHOLD)
    )
    assert not track_read_effort_flag(
        TrackResult(number=5, rip_count=HEAVY_REREAD_THRESHOLD - 1)
    )
    # A non-int pass count must not raise or flag.
    assert not track_read_effort_flag(TrackResult(number=6, rip_count=None))


def test_the_heavy_reread_list_needs_a_flag_AND_a_usable_track_number() -> None:
    """`isinstance(number, int)` guards the list's contents.

    The mutant at the flag/number pair lets a flagged track with no number into a
    `list[int]`, which the results footnote and the report's `read_effort` issue
    both render — so a `None` reaches a user-facing sentence.
    """
    from platterpus.parsers.rip_log import tracks_needing_heavy_reread

    log = RipLog(
        tracks=(
            TrackResult(number=1, secure_rerip_converged=False),
            TrackResult(number=None, secure_rerip_converged=False),
            TrackResult(number=3, secure_rerip_converged=True),
        )
    )
    flagged = tracks_needing_heavy_reread(log)
    assert flagged == [1], f"expected only track 1, got {flagged!r}"
    assert all(isinstance(n, int) for n in flagged)


def test_the_scoped_secure_rerip_count_counts_TRACKS_not_discs() -> None:
    """`sum(1 for ...)` — the `1` → `2` mutant doubles every count.

    The docstring is explicit that a count is returned rather than a bool because
    "1 of 14" and "14 of 14" are different facts. A doubled count is a third,
    false, fact — and it is the number the acceptance run's secure-re-read section
    asserts on.
    """
    from platterpus.parsers.rip_log import secure_rerip_tracks_scoped

    log = RipLog(
        tracks=(
            TrackResult(number=1, paranoia_scope="2 of 2 matches"),
            TrackResult(number=2, paranoia_scope="2 of 2 matches"),
            TrackResult(number=3),
        )
    )
    assert secure_rerip_tracks_scoped(log) == 2
    assert secure_rerip_tracks_scoped(RipLog()) == 0


def test_a_SECOND_tracks_header_cannot_rewrite_the_track_before_it() -> None:
    r"""Leaving the ``Tracks`` section closes the in-flight track — always.

    The flush is guarded by ``section == "tracks"``, and the mutation sweep's last
    surviving mutant here flips it to ``!=``. It is *nearly* equivalent: with the
    comparison inverted the flush simply happens one header later, and since
    nothing outside the tracks section touches the in-flight track, the parsed
    result is identical for every well-formed log — which is why 39 of 40 mutants
    died and this one did not.

    **It separates on two consecutive ``Tracks:`` headers**, which is what a
    concatenated log looks like (two rips pasted into one file — an ordinary thing
    for a user to do when reporting a problem). Then the inverted guard keeps the
    first section's track open across the boundary and the second section's fields
    are written *into it*:

        Tracks:            1: Filename: a.flac
        Tracks:               Filename: STRAY.flac   -> track 1 becomes STRAY.flac

    A silently rewritten filename in an archival parser is the failure this project
    calls worst: nothing raises, nothing is logged, and the record is wrong. So the
    boundary is pinned rather than left to the near-equivalence.
    """
    log = (
        "Log created by: whipper 0.10.0\n"
        "Tracks:\n"
        "  1:\n"
        "    Filename: a.flac\n"
        "    Copy CRC: DEADBEEF\n"
        "Tracks:\n"
        "    Filename: STRAY.flac\n"
        "    Copy CRC: 00000000\n"
    )
    parsed = parse_rip_log(log)
    assert [t.number for t in parsed.tracks] == [1]
    assert parsed.tracks[0].filename == "a.flac", (
        "a second Tracks: header wrote its fields into the previous section's "
        f"track: {parsed.tracks[0].filename!r}"
    )
    assert parsed.tracks[0].copy_crc == "DEADBEEF"


def test_the_boundary_flush_still_runs_for_an_ORDINARY_log() -> None:
    """The companion: closing at the boundary must not *lose* the last track.

    Pinning the guard one way invites fixing it by removing the flush, so this
    holds the other side — a track that is in flight when a real section follows
    is still in the result, exactly once.
    """
    log = (
        "Log created by: whipper 0.10.0\n"
        "Tracks:\n"
        "  1:\n"
        "    Filename: a.flac\n"
        "Conclusive status report:\n"
        "  Status: Success\n"
    )
    parsed = parse_rip_log(log)
    assert [t.number for t in parsed.tracks] == [1]
    assert parsed.tracks[0].filename == "a.flac"
