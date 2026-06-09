"""Tests for the `cyanrip -I` info parser (parsers/cyanrip_info.py).

Sample shapes are reconstructed from cyanrip master's format strings
(`cyanrip_log.c::cyanrip_log_start_report`, `cyanrip_main.c`); the labels
are exact. Cases follow the five-tier taxonomy from docs/testing.md.
"""

from __future__ import annotations

from whipper_gui.parsers.cd_info import DiscInfo
from whipper_gui.parsers.cyanrip_info import parse_cyanrip_info

# A realistic full `-I` report (known disc, MusicBrainz enabled).
_FULL_REPORT = """\
cyanrip 0.9.3.1 (master)
Drive used:     PIONEER BD-RW   BDR-209D (revision 1.10)
System device:  /dev/sr0
Offset:         +667 samples
Paranoia level: full
Frame retries:  10
HDCD decoding:  disabled
Album Art:      none
Outputs:        flac
Disc tracks:    16
Tracks to rip:  all
DiscID:         xA2hjkk0Jl0gKKtIdYuTje4JTXY-
Release ID:     1e477f68-c407-4eae-ad01-518528cedc2c
CDDB ID:        c50a780f
Disc MCN:       0000000000000
Album:          Greatest Hits
Album artist:   The Police
AccurateRip:    disabled
Total time:     58:06:33
MusicBrainz URL:
https://musicbrainz.org/cdtoc/attach?toc=1+16+260075&tracks=16&id=xA2hjkk0Jl0gKKtIdYuTje4JTXY-
"""


# --- Easy: the full, well-formed report ------------------------------------


def test_full_report_parses_all_fields() -> None:
    info = parse_cyanrip_info(_FULL_REPORT)
    assert info.musicbrainz_disc_id == "xA2hjkk0Jl0gKKtIdYuTje4JTXY-"
    assert info.cddb_disc_id == "c50a780f"
    assert info.num_tracks == 16
    assert info.musicbrainz_submit_url.startswith(
        "https://musicbrainz.org/cdtoc/attach?"
    )


# --- Medium: `-N` output (no Release ID / Album lines — CLOG skips unknowns)


def test_offline_report_still_has_ids() -> None:
    """With -N, cyanrip still computes DiscID + CDDB ID locally from the
    TOC (discid.c) — exactly what the adapter relies on."""
    report = (
        "cyanrip 0.9.3.1 (master)\n"
        "System device:  /dev/sr0\n"
        "Disc tracks:    12\n"
        "DiscID:         lwHl8fUzJyLzMyJzKy.MyM3hbW0-\n"
        "CDDB ID:        940a6a0b\n"
        "Total time:     42:17:00\n"
    )
    info = parse_cyanrip_info(report)
    assert info.musicbrainz_disc_id == "lwHl8fUzJyLzMyJzKy.MyM3hbW0-"
    assert info.cddb_disc_id == "940a6a0b"
    assert info.num_tracks == 12
    assert info.musicbrainz_submit_url == ""


# --- Hard: URL-label edge shapes -------------------------------------------


def test_url_after_blank_line_is_still_captured() -> None:
    report = "MusicBrainz URL:\n\nhttps://musicbrainz.org/cdtoc/attach?id=x\n"
    info = parse_cyanrip_info(report)
    assert info.musicbrainz_submit_url == "https://musicbrainz.org/cdtoc/attach?id=x"


def test_url_label_followed_by_non_url_is_ignored() -> None:
    """printf of a NULL url prints "(null)" — must not be taken as a URL,
    and the line after that must not be either (the window is one line)."""
    report = (
        "MusicBrainz URL:\n"
        "(null)\n"
        "https://example.com/not-the-submit-url\n"
        "Disc tracks:    5\n"
    )
    info = parse_cyanrip_info(report)
    assert info.musicbrainz_submit_url == ""
    assert info.num_tracks == 5  # parsing continues normally afterwards


def test_url_label_at_end_of_output() -> None:
    assert parse_cyanrip_info("MusicBrainz URL:\n") == DiscInfo()


# --- Edge: empty / whitespace / label-only ----------------------------------


def test_empty_and_whitespace_inputs() -> None:
    assert parse_cyanrip_info("") == DiscInfo()
    assert parse_cyanrip_info("\n\n\t \n") == DiscInfo()


def test_label_without_value_is_ignored() -> None:
    # A bare label (no value) must not match — \s+ requires separation,
    # \S+ requires content.
    assert parse_cyanrip_info("DiscID:\nCDDB ID:\nDisc tracks:\n") == DiscInfo()


# --- Unexpected: error output instead of a report ---------------------------


def test_error_output_degrades_to_empty() -> None:
    report = (
        "cyanrip 0.9.3.1 (master)\n"
        "Couldn't open drive: /dev/sr0\n"
        "Unable to read disc TOC!\n"
    )
    assert parse_cyanrip_info(report) == DiscInfo()


def test_similar_but_wrong_labels_do_not_match() -> None:
    # Near-misses (different label text, indented, prefixed) stay ignored.
    report = (
        "  DiscID:         indented-should-not-match\n"
        "MusicBrainz DiscID: wrong-label\n"
        "CDDB disc id: whipper-style-label\n"
        "Total tracks:   9\n"
    )
    assert parse_cyanrip_info(report) == DiscInfo()
