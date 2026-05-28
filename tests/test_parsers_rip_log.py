"""Tests for whipper_gui.parsers.rip_log.

Fixture is hand-authored to match the format documented in
whipper-team/whipper master (result/logger.py). The smoke test in T32
will validate the parser against a real .log produced by ripping a CD.
"""

from __future__ import annotations

from pathlib import Path

from whipper_gui.parsers.rip_log import (
    AccurateRipResult,
    RipLog,
    TrackResult,
    parse_rip_log,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text()


# --- High-level parsing ---------------------------------------------------


def test_parse_complete_log() -> None:
    log = parse_rip_log(_read("rip_log_two_tracks.log"))

    assert log.log_creator.startswith("whipper 0.10.0")
    assert log.creation_date == "2024-03-15T20:30:45Z"
    assert log.accuraterip_summary == "All tracks accurately ripped (v1)"
    assert log.health_status == "No errors occurred"
    assert log.sha256_hash.startswith("7d8e9f0a")
    assert len(log.tracks) == 2


def test_track_one_fields() -> None:
    log = parse_rip_log(_read("rip_log_two_tracks.log"))
    track = log.tracks[0]

    assert track.number == 1
    assert track.filename.endswith("01. Speak to Me.flac")
    assert track.peak_level is not None
    assert abs(track.peak_level - 0.348297) < 1e-6
    assert track.pre_emphasis is False
    assert track.extraction_speed == 8.5
    assert track.extraction_quality == 100.0
    assert track.test_crc == "1A2B3C4D"
    assert track.copy_crc == "1A2B3C4D"
    assert track.status == "Copy OK"


def test_track_one_accuraterip_v1_match() -> None:
    log = parse_rip_log(_read("rip_log_two_tracks.log"))
    ar = log.tracks[0].accuraterip_v1
    assert ar is not None
    assert ar.version == 1
    assert ar.result == "Found, exact match"
    assert ar.confidence == 12
    assert ar.local_crc == "1A2B3C4D"
    assert ar.remote_crc == "1A2B3C4D"


def test_track_one_accuraterip_v2_match() -> None:
    log = parse_rip_log(_read("rip_log_two_tracks.log"))
    ar = log.tracks[0].accuraterip_v2
    assert ar is not None
    assert ar.version == 2
    assert ar.confidence == 8
    assert ar.local_crc == "9E8F7A6B"


def test_track_two_accuraterip_v2_missing_from_database() -> None:
    """Track 2 in the fixture is "Track not present in AccurateRip
    database" with empty CRC fields. The parser should report this
    correctly rather than crashing on the blanks."""
    log = parse_rip_log(_read("rip_log_two_tracks.log"))
    ar = log.tracks[1].accuraterip_v2
    assert ar is not None
    assert ar.version == 2
    assert ar.result.startswith("Track not present")
    assert ar.confidence == 0
    assert ar.local_crc is None
    assert ar.remote_crc is None


# --- Defensive edge cases -------------------------------------------------


def test_parse_empty_input_returns_empty_log() -> None:
    log = parse_rip_log("")
    assert log == RipLog()


def test_parse_log_without_status_section() -> None:
    """A truncated log (rip killed mid-write) should still parse what's
    there without raising."""
    text = (
        "Log created by: whipper 0.10.0\n"
        "Tracks:\n"
        "  1. (filename: track01.flac)\n"
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


def test_track_result_is_frozen() -> None:
    t = TrackResult(number=1)
    try:
        t.number = 2  # type: ignore[misc]
        assert False, "expected FrozenInstanceError"
    except Exception:
        pass


def test_accuraterip_result_is_frozen() -> None:
    ar = AccurateRipResult(version=1)
    try:
        ar.confidence = 5  # type: ignore[misc]
        assert False, "expected FrozenInstanceError"
    except Exception:
        pass
