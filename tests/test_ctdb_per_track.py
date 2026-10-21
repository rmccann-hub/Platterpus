# SPDX-License-Identifier: GPL-3.0-only
"""Per-track CTDB results (TASKS R43), held against a REAL CTDB response.

``tests/fixtures/ctdb_lookup_police_classics.xml`` is the live ``lookup2.php``
answer for the reference disc, fetched 2026-10-21 (provenance in
``tests/fixtures/README.md``). Beside it sit EAC's three logs of the same disc
(``output_reference/EAC_*``), whose CTDB plugin printed a per-track table. Two
things are checked against those artifacts rather than against our description of
them:

* **The definition.** A middle track's CTDB per-track CRC is the plain CRC-32 of
  the track, which is EAC's "Copy CRC" with null samples counted (EAC's logs say
  ``Null samples used in CRC calculations : Yes``). If that were wrong, EAC's
  Copy CRCs would not be found among the database's per-track CRCs; they are,
  for 46 or more submissions on every middle track EAC read correctly.
* **The counting.** Fed EAC's own Copy CRCs, our matcher marks a track as
  differing exactly where EAC's plugin printed no "Accurately ripped", and it
  counts the 2 submissions EAC's plugin counted for track 5's minority read.
"""

from __future__ import annotations

import random
import re
import zlib
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus.adapters.ctdb_client import (
    CTDBClient,
    CtdbEntry,
    CtdbLookupResult,
    parse_lookup_response,
    parse_track_crcs,
)
from platterpus.ctdb import crc as crc_mod
from platterpus.ctdb.matching import (
    NO_LOCAL_CRC_REASON,
    NO_TRACK_CRCS_REASON,
    TrackVerdict,
    match_disc,
    match_tracks,
)
from platterpus.ctdb.sweep import sweep
from platterpus.ctdb.toc import SAMPLES_PER_SECTOR, DiscToc
from platterpus.ctdb.track_wording import per_track_lines, per_track_sentence
from platterpus.ctdb.verify import Verdict, verify_rip
from platterpus.parity import decode_log_bytes
from platterpus.parsers.eac_log import parse_eac_copy_crcs
from platterpus.rip_report import _ctdb

_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE = _ROOT / "tests" / "fixtures" / "ctdb_lookup_police_classics.xml"
_EAC = {
    "flac": _ROOT / "output_reference/EAC_flac/eac_baseline_police_classics.log",
    "wav": _ROOT / "output_reference/EAC_wav/eac_wav_police_classics.log",
    "mp3": _ROOT / "output_reference/EAC_mp3/eac_mp3_police_classics.log",
}
_TRACKS = 14
_MIDDLE = range(2, _TRACKS)  # tracks 2..13: no guard band, so a Copy CRC compares
# EAC's plugin row: ` 3   | (1341/1443) Differs in 16 samples @04:04:68,...`.
_EAC_CTDB_ROW = re.compile(r"^\s*(?P<track>\d+)\s+\|\s+(?P<status>\(.*)$")


def _real_lookup() -> CtdbLookupResult:
    return parse_lookup_response(_FIXTURE.read_bytes())


def _eac(session: str) -> tuple[dict[int, int], dict[int, str]]:
    """EAC's Copy CRCs and its CTDB plugin's per-track rows for one session."""
    text = decode_log_bytes(_EAC[session].read_bytes())
    copy = {n: int(c, 16) for n, c in parse_eac_copy_crcs(text).items()}
    table = text.split("Track | CTDB Status", 1)[1]
    rows: dict[int, str] = {}
    for line in table.splitlines():
        match = _EAC_CTDB_ROW.match(line)
        if match:
            rows[int(match["track"])] = match["status"]
    assert len(copy) == _TRACKS and len(rows) == _TRACKS, (session, copy, rows)
    return copy, rows


def _as_measured(copy: dict[int, int]) -> list[dict[int, int]]:
    """EAC's Copy CRCs as our aligned middle-track CRCs; tracks 1 and 14 unknown."""
    return [{0: copy[n]} if n in _MIDDLE else {} for n in range(1, _TRACKS + 1)]


# --- the parser --------------------------------------------------------------


def test_track_crcs_parse_one_value_per_token() -> None:
    assert parse_track_crcs("0011 22ff ABCDEF01") == (0x11, 0x22FF, 0xABCDEF01)
    assert parse_track_crcs(None) == ()
    assert parse_track_crcs("") == ()


def test_one_unreadable_token_drops_the_whole_list() -> None:
    """Skipping it would slide every later CRC onto the wrong track."""
    assert parse_track_crcs("0011 zz 22ff") == ()
    assert parse_track_crcs("0011 123456789") == ()  # wider than 32 bits


@given(st.one_of(st.none(), st.text(max_size=200)))
def test_parse_track_crcs_never_raises(text: str | None) -> None:
    values = parse_track_crcs(text)
    assert all(0 <= v <= 0xFFFFFFFF for v in values)


def test_the_real_response_parses_with_a_crc_per_track_for_every_entry() -> None:
    lookup = _real_lookup()
    assert len(lookup.entries) == 102
    assert {len(e.track_crcs) for e in lookup.entries} == {_TRACKS}
    assert max(e.confidence for e in lookup.entries) == 1416
    assert lookup.entries[0].track_crcs[2] == 0xBA71189B  # the 1,416 entry's track 3


# --- the definition, against measured data ---------------------------------


@pytest.mark.parametrize("session", ["flac", "mp3", "wav"])
def test_eac_copy_crcs_are_the_database_s_middle_track_crcs(session: str) -> None:
    """For every middle track EAC read as the plurality of same-offset rips did,
    its Copy CRC is in the database's per-track list, behind many submissions."""
    copy, rows = _eac(session)
    lookup = _real_lookup()
    found = 0
    for number in _MIDDLE:
        agreeing = sum(
            e.confidence
            for e in lookup.entries
            if e.track_crcs[number - 1] == copy[number]
        )
        # A plain "Accurately ripped" row: EAC's read is the common one. A row
        # with ", or" is a minority read (track 5), counted in the next test.
        if "Accurately ripped" in rows[number] and ", or" not in rows[number]:
            assert agreeing >= 42, (session, number, agreeing)
            found += 1
    assert found >= 9  # the floor: most middle tracks were read correctly


def test_the_first_and_last_track_are_not_the_plain_track_crc() -> None:
    """Tracks 1 and 14 lose the guard band, so no EAC Copy CRC appears there."""
    copy, _ = _eac("flac")
    lookup = _real_lookup()
    for number in (1, _TRACKS):
        assert all(e.track_crcs[number - 1] != copy[number] for e in lookup.entries)


# --- the counting, against EAC's own plugin ---------------------------------


@pytest.mark.parametrize("session", ["wav", "mp3"])
def test_a_track_differs_exactly_where_eac_s_plugin_found_no_agreement(
    session: str,
) -> None:
    """The wav and mp3 sessions came after EAC's 06-11 submission, the database
    state this fixture still holds; the flac session predates it (its own track-5
    read was not yet in the database), so it is not compared here."""
    copy, rows = _eac(session)
    lookup = _real_lookup()
    tracks = match_tracks(lookup.entries, _as_measured(copy), {})
    differs = {t.track for t in tracks if t.verdict is TrackVerdict.DIFFERS}
    eac_differs = {n for n in _MIDDLE if "Accurately ripped" not in rows[n]}
    assert eac_differs  # non-triviality: EAC found a differing track
    assert differs == eac_differs
    # Track 5's minority read: EAC's plugin printed "(  2/1443) Accurately
    # ripped, or (1341/1443) differs", and our count of agreeing submissions is 2.
    assert rows[5].startswith("(  2/1443) Accurately ripped")
    assert tracks[4].verdict is TrackVerdict.MATCH and tracks[4].confidence == 2
    assert tracks[4].outvoted is True
    # Tracks 1 and 14 have no aligned CRC from a Copy CRC: not determined.
    assert tracks[0].verdict is TrackVerdict.NOT_DETERMINED
    assert tracks[0].reason == NO_LOCAL_CRC_REASON


def test_the_wav_session_s_sentence_names_the_differing_track() -> None:
    """Fed only ALIGNED CRCs (a Copy CRC has no other offset), every track reads
    as agreeing with a minority: the 1,416 entry is a pressing at another offset,
    which a real verify measures (its tracks are swept over ±5879) and this input
    cannot show. What the input does settle: track 3 differs from every entry."""
    copy, _ = _eac("wav")
    lookup = _real_lookup()
    total = sum(e.confidence for e in lookup.entries)
    tracks = match_tracks(lookup.entries, _as_measured(copy), {})
    sentence = per_track_sentence(tracks, total)
    assert "track 3 differs from every entry" in sentence
    assert (
        f"track 5 agrees only with a minority (2 of {total:,} submissions)" in sentence
    )
    assert "tracks 1 and 14 not determined" in sentence
    lines = per_track_lines(tracks, total)
    assert (
        lines[2] == f"  3   | differs from every entry ({total:,}/{total:,} disagree)"
    )


def test_the_sentence_counts_agreeing_differing_and_minority_tracks() -> None:
    entries = (
        CtdbEntry(crc=None, confidence=100, track_crcs=(1, 2, 3, 4)),
        CtdbEntry(crc=None, confidence=3, track_crcs=(1, 9, 8, 5)),
    )
    measured = [{0: 1}, {0: 2}, {0: 7}, {0: 5}]
    tracks = match_tracks(entries, measured, {})
    assert per_track_sentence(tracks, 103) == (
        "Per track: 2 of 4 agree with CTDB; track 3 differs from every entry; "
        "track 4 agrees only with a minority (3 of 103 submissions)."
    )


def test_an_entry_is_placed_where_its_tracks_agree_beyond_the_ar_window() -> None:
    """An entry pressed 4,000 samples from ours (outside ±2939) is found by the
    consensus of its tracks, as CUETools finds it from the parity syndrome."""
    entries = (CtdbEntry(crc=None, confidence=50, track_crcs=(0x11, 0x22, 0x33)),)
    measured = [{0: 1, 4000: 0x11}, {0: 2, 4000: 0x22}, {0: 3, 4000: 0x99}]
    tracks = match_tracks(entries, measured, {})
    assert [t.verdict for t in tracks] == [
        TrackVerdict.MATCH,
        TrackVerdict.MATCH,
        TrackVerdict.DIFFERS,
    ]
    assert tracks[0].offset == 4000
    # One track alone at 4,000 is no consensus, and 4,000 is outside ±2939.
    lone = (CtdbEntry(crc=None, confidence=50, track_crcs=(0x11, 0x77, 0x33)),)
    assert match_tracks(lone, measured, {})[0].verdict is TrackVerdict.DIFFERS


# --- the rules, on synthetic entries ----------------------------------------


def test_an_entry_matching_the_whole_disc_vouches_for_every_track() -> None:
    """CUETools counts an error-free entry for every track, per-track list or not."""
    entries = (CtdbEntry(crc=0xAB, confidence=9),)
    measured = [{0: 1}, {0: 2}]
    tracks = match_tracks(entries, measured, match_disc(entries, {0: 0xAB}))
    assert [t.verdict for t in tracks] == [TrackVerdict.MATCH] * 2
    assert [t.confidence for t in tracks] == [9, 9]


def test_a_track_crc_found_at_a_shifted_offset_names_the_offset() -> None:
    entries = (CtdbEntry(crc=None, confidence=4, track_crcs=(0x55, 0x66)),)
    measured = [{0: 1, -12: 0x55}, {0: 0x66}]
    first, second = match_tracks(entries, measured, {})
    assert first.verdict is TrackVerdict.MATCH and first.offset == -12
    assert second.offset == 0 and second.our_crc == 0x66


def test_a_per_track_list_of_the_wrong_length_says_nothing() -> None:
    entries = (CtdbEntry(crc=None, confidence=4, track_crcs=(0x55,)),)
    (track, _) = match_tracks(entries, [{0: 0x55}, {0: 2}], {})
    assert track.verdict is TrackVerdict.NOT_DETERMINED
    assert track.reason == NO_TRACK_CRCS_REASON
    assert (
        per_track_sentence((track,), 4)
        == f"Per track: not determined ({NO_TRACK_CRCS_REASON})."
    )


def test_no_per_track_result_gives_no_sentence() -> None:
    assert per_track_sentence((), 10) == ""


# --- the verify and the report, end to end ----------------------------------

_SECTORS = (17, 20, 17)  # long enough for the guard band at every track offset
_FILES = [Path(f"{n:02d}.flac") for n in range(1, len(_SECTORS) + 1)]
_PCM = {
    path: random.Random(index).randbytes(sectors * SAMPLES_PER_SECTOR * 4)
    for index, (path, sectors) in enumerate(zip(_FILES, _SECTORS, strict=True))
}


class _Client(CTDBClient):
    def __init__(self, entries: tuple[CtdbEntry, ...]) -> None:
        self._entries = entries

    def lookup(self, toc: DiscToc) -> CtdbLookupResult:
        return CtdbLookupResult(entries=self._entries)


def _our_track_crcs() -> list[int]:
    starts = [0, _SECTORS[0], _SECTORS[0] + _SECTORS[1]]
    frames = [s * SAMPLES_PER_SECTOR for s in starts]
    measured = sweep(
        [_PCM[p] for p in _FILES], frames, sum(_SECTORS) * SAMPLES_PER_SECTOR
    )
    return [crcs[0] for crcs in measured.tracks]


def _verify(entries: tuple[CtdbEntry, ...]) -> object:
    return verify_rip(
        _FILES,
        _Client(entries),
        decoder=lambda p: _PCM[p],
        samples_probe=lambda p: len(_PCM[p]) // 4,
    )


def test_a_rip_with_one_bad_track_names_it_in_the_verdict_and_the_report() -> None:
    ours = _our_track_crcs()
    assert ours[1] == zlib.crc32(_PCM[_FILES[1]]) & 0xFFFFFFFF  # a middle track
    damaged = (ours[0], ours[1] ^ 1, ours[2])
    entries = (
        CtdbEntry(crc=0xDEAD, confidence=30, track_crcs=damaged),
        CtdbEntry(crc=0xBEEF, confidence=2, track_crcs=(1, 2, 3)),
    )
    result = _verify(entries)
    assert result.verdict is Verdict.NO_MATCH
    assert [t.verdict for t in result.tracks] == [
        TrackVerdict.MATCH,
        TrackVerdict.DIFFERS,
        TrackVerdict.MATCH,
    ]
    assert result.tracks[0].confidence == 30
    assert result.tracks[1].disagreeing_confidence == 32
    assert "track 2 differs from every entry" in result.message
    block = _ctdb(result)
    assert block is not None and block["tracks"] is not None
    row = block["tracks"][1]
    assert row["verdict"] == "differs"
    assert row["our_crc"] == f"{ours[1]:08X}"
    assert row["strongest_disagreeing"] == 30
    assert block["tracks"][0]["reason"] is None


def test_a_check_that_never_computed_our_crcs_reports_no_tracks() -> None:
    result = _verify(())  # not in the database
    assert result.verdict is Verdict.NOT_IN_DATABASE
    assert result.tracks == ()
    block = _ctdb(result)
    assert block is not None and block["tracks"] is None


def test_the_whole_disc_crc_is_unchanged_by_the_new_pass() -> None:
    whole = b"".join(_PCM[p] for p in _FILES)
    result = _verify((CtdbEntry(crc=crc_mod.ctdb_crc(whole, 0), confidence=5),))
    assert result.verdict is Verdict.MATCH
    assert result.our_crc == crc_mod.ctdb_crc(whole, 0)
    assert all(t.verdict is TrackVerdict.MATCH for t in result.tracks)
