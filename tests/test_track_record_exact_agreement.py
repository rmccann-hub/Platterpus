"""A converged ``-Z`` track's record counts its agreeing reads exactly where the log can.

**The defect (TASKS R140, our round 39 lap 2 S16).** In round 39's five-rip run
(2026-11-11, 0.7.122 with the fork's ``.31``) track 3's record read ``re-read, at
least 2 agreeing of 3`` in rips 1, 2 and 5, where the securing pass printed
``Done; (2 out of 2 matches for current checksum 59D352DD)`` and no ``Other read:``
line, so all three reads agreed. True, and weaker than the log.

**The rule.** ``.30`` and ``.31`` print an ``Other read:`` line for every value
their ``-Z`` reads gave that was not kept, with how many reads gave it (read in
their source, and stated by the fork's round 39 lap 5 S7; ``track_record_sources.OTHER_READS_COMPLETE_BUILDS``
cites it), so on those builds a converged track with none had every read agree:
``3 agreeing of 3``. Any other build, and a track whose lines were elided past the
bound, keeps the floor, which is true and only weaker.

The log text is synthesized in the five-rip run's shape (``round 39 repeat rip 1``'s
securing pass, track 3, lines 75 to 124); no bundle file is committed, and no
audio is involved (Critical rule 8).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from platterpus.eac_log_export import render_eac_style_log
from platterpus.other_reads import OtherRead
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import TrackResult
from platterpus.track_record import RECORD_REREAD, track_record
from platterpus.track_record_sources import (
    OTHER_READS_COMPLETE_BUILDS,
    fork_build_number,
    prints_every_other_read,
)
from platterpus.uiscript.track_record_grading import eac_log_blocks

_BANNER_31 = "cyanrip 0.9.4-rc3+platterpus.31 (platterpus-fork-ge531a33)"
_BANNER_30 = "cyanrip 0.9.4-rc3+platterpus.30 (platterpus-fork-g5cc1c6b)"
_ARTIFACTS = Path(__file__).resolve().parent.parent / "docs/handshake/inbound/artifacts"

#: Each fork build's filed provider contract, by build number, for the P2 row.
_CONTRACTS: dict[int, str] = {
    26: "round-36-lap-04-provider-contract-ge2b52b1.md",
    27: "round-36-lap-10-provider-contract-g580c46c.md",
    28: "round-37-lap-04-provider-contract-gef413b1.md",
    29: "round-38-lap-05-provider-contract-g2a06e064.md",
    30: "round-38-lap-12-provider-contract-g0c276fc.md",
    31: "round-39-lap-01-provider-contract-g6eacb8b.md",
}


def _securing_pass(banner: str, other_read: str = "") -> str:
    """The five-rip run's securing pass for track 3, in its own lines, trimmed to the rows
    the record reads: three reads, every one ``59D352DD``, verified by AccurateRip."""
    return (
        f"{banner}\n"
        "Disc tracks:    14\n"
        "AccurateRip:    found\n"
        "\n"
        "Tracks:\n"
        "\n"
        "Repeating ripping (0 out of 2 matches for current checksum 59D352DD)\n"
        "\n"
        "Repeating ripping (1 out of 2 matches for current checksum 59D352DD)\n"
        "\n"
        "Done; (2 out of 2 matches for current checksum 59D352DD)\n"
        "Track 3 read with no error reported.\n"
        "  EAC CRC32:     59D352DD (after 3 rips)\n"
        "  Secure re-read:  converged after 3 reads\n"
        f"{other_read}"
        "  Accurip:       disc found in database (max confidence: 200)\n"
        "    Accurip v1:  3C8BDDD2 (accurately ripped, confidence 128)\n"
        "    Accurip v2:  96DF8C22 (accurately ripped, confidence 200)\n"
        "  File(s):\n"
        "    Artist/Album/03 - Message in a Bottle.flac\n"
        "Ripping errors: 0\n"
    )


def _track3(text: str) -> TrackResult:
    log = parse_cyanrip_log(text)
    (track,) = [t for t in log.tracks if t.number == 3]
    return track


# --- the five-rip run's track 3 ------------------------------------------------------------


def test_the_five_rip_runs_track_3_on_31_reads_three_agreeing_of_three() -> None:
    """The defect itself: the five-rip run's text, on the build that printed it."""
    text = _securing_pass(_BANNER_31)
    track = _track3(text)
    # The parse is what the record stands on; assert it rather than assume it.
    assert track.rip_count == 3 and track.secure_rerip_converged is True
    assert track.other_reads == () and track.other_reads_not_kept == 0
    record = track_record(track, ripper_version=parse_cyanrip_log(text).log_creator)
    assert record.kind == RECORD_REREAD
    assert record.line.startswith("re-read, 3 agreeing of 3; verified by AccurateRip")
    assert "at least" not in record.line
    assert record.reads_disagree is False


def test_the_eac_layout_logs_record_row_says_it_too() -> None:
    """Through the renderer, which hands the record the log's own banner: the row
    a reader of the EAC-layout log sees (repeat rip 1's line 102 said the floor)."""
    log = parse_cyanrip_log(_securing_pass(_BANNER_31))
    block = eac_log_blocks(render_eac_style_log(log))[3]
    (row,) = [line.strip() for line in block if "Record:" in line]
    assert row.startswith("Record: re-read, 3 agreeing of 3; verified by AccurateRip")


def test_30_counts_exactly_as_well() -> None:
    track = _track3(_securing_pass(_BANNER_30))
    assert track_record(track, ripper_version=_BANNER_30).line.startswith(
        "re-read, 3 agreeing of 3;"
    )


# --- where the floor stays --------------------------------------------------------


@pytest.mark.parametrize(
    "banner",
    [
        "cyanrip 0.9.4-rc3+platterpus.29 (platterpus-fork-g2a06e064)",  # before the line
        "cyanrip 0.9.4-rc3+platterpus.32 (platterpus-fork-g0000000)",  # not yet read
        "cyanrip 0.9.3 (release)",  # stock: no Other read line at all
        "",  # no banner: nothing known
    ],
)
def test_a_build_not_known_to_print_every_other_read_keeps_the_floor(
    banner: str,
) -> None:
    track = _track3(_securing_pass(_BANNER_31))
    line = track_record(track, ripper_version=banner).line
    assert line.startswith("re-read, at least 2 agreeing of 3;"), line


def test_lines_elided_past_the_bound_keep_the_floor() -> None:
    """``other_reads_not_kept`` counts lines the parser dropped from the middle:
    the log printed reads we did not keep, so 'none printed' is not what it said."""
    track = replace(_track3(_securing_pass(_BANNER_31)), other_reads_not_kept=1)
    line = track_record(track, ripper_version=_BANNER_31).line
    assert line.startswith("re-read, at least 2 agreeing of 3;"), line


def test_a_printed_other_read_still_counts_from_its_lines() -> None:
    """The existing exact path, unchanged: one other read, read once, of four."""
    track = _track3(_securing_pass(_BANNER_31).replace("after 3 rips", "after 4 rips"))
    other = OtherRead(state="read", text="", crc="3D8FCF0C", count=1, where="not_known")
    track = replace(track, other_reads=(other,))
    line = track_record(track, ripper_version=_BANNER_31).line
    assert line.startswith("re-read, 3 agreeing of 4;"), line


def test_one_line_for_a_value_read_twice_counts_both_reads() -> None:
    """The line is one per VALUE, not one per read (the fork's round 39 lap 5 S7,
    ``cyanrip@e531a33:src/cyanrip_log.c:874-897``): ``read 2 times`` is two reads
    not kept, so five reads with one such line are three agreeing, not four."""
    track = _track3(_securing_pass(_BANNER_31).replace("after 3 rips", "after 5 rips"))
    other = OtherRead(state="read", text="", crc="3D8FCF0C", count=2, where="not_known")
    track = replace(track, other_reads=(other,))
    line = track_record(track, ripper_version=_BANNER_31).line
    assert line.startswith("re-read, 3 agreeing of 5;"), line


# --- the gate, checked against the artifacts ----------------------------------------


def test_the_listed_builds_are_exactly_those_whose_contract_prints_the_line() -> None:
    """Each listed build's own filed contract carries P2's ``Other read:`` row, and
    each earlier build's does not, so the set cannot list a build that never
    printed the line. (That the line is printed for EVERY read not kept is read in
    their source; ``OTHER_READS_COMPLETE_BUILDS``'s comment cites the lines.)"""
    printed = {
        build
        for build, name in _CONTRACTS.items()
        if "`Other read:      %08X, read %i time%s, %s%s%s`"
        in (_ARTIFACTS / name).read_text(encoding="utf-8")
    }
    assert len(_CONTRACTS) >= 6, "floor: the contracts compared"
    assert printed == OTHER_READS_COMPLETE_BUILDS == frozenset({30, 31})


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        (_BANNER_30, True),
        (_BANNER_31, True),
        ("cyanrip 0.9.4-rc3+platterpus.29 (platterpus-fork-g2a06e064)", False),
        ("cyanrip 0.9.4-rc3+platterpus.32 (platterpus-fork-g0000000)", False),
        ("cyanrip 0.9.3 (release)", False),
        ("", False),
    ],
)
def test_prints_every_other_read(version: str, expected: bool) -> None:
    assert prints_every_other_read(version) is expected
    assert (fork_build_number(version) in OTHER_READS_COMPLETE_BUILDS) is expected
