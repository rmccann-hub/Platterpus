"""Tests for whipper_gui.parsers.cd_info."""

from __future__ import annotations

from pathlib import Path

from whipper_gui.parsers.cd_info import DiscInfo, parse_cd_info

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_parse_full_output() -> None:
    info = parse_cd_info(_read("cd_info_pink_floyd.txt"))

    assert info.cddb_disc_id == "940A6A0B"
    assert info.musicbrainz_disc_id == "wzr8h2ssXg4F2.x8L3KqB9PHevc-"
    assert info.musicbrainz_submit_url.startswith(
        "https://musicbrainz.org/cdtoc/attach?id="
    )


def test_parse_tolerates_surrounding_noise() -> None:
    """Whipper occasionally emits log lines around the actual info output."""
    info = parse_cd_info(_read("cd_info_with_noise.txt"))

    assert info.cddb_disc_id == "12345678"
    assert info.musicbrainz_disc_id == "abc-123-def-456"
    assert info.musicbrainz_submit_url.endswith("id=abc-123")


def test_parse_empty_input_returns_empty_fields() -> None:
    info = parse_cd_info("")

    assert info == DiscInfo(
        cddb_disc_id="", musicbrainz_disc_id="", musicbrainz_submit_url=""
    )


def test_parse_partial_input() -> None:
    """If whipper only printed the MB disc id (e.g., CDDB lookup failed),
    we still extract what's there."""
    info = parse_cd_info("MusicBrainz disc id partial-id-only\n")

    assert info.cddb_disc_id == ""
    assert info.musicbrainz_disc_id == "partial-id-only"
    assert info.musicbrainz_submit_url == ""
