# SPDX-License-Identifier: GPL-3.0-only
"""The whole-disc offset sweep (TASKS R43, step 2).

CTDB places a pressing anywhere in ±5879 samples of ours (``CDRepairEncode.
FindOffset`` searches that range), and until 2026-10-21 the verify compared one
alignment, so a disc whose pressing sat one sample away read "no match" and said
nothing. Now the verify compares every alignment in that range in the same
streamed pass, reports where a match sits, and, when nothing matches anywhere,
says so as a finding scoped to what CTDB holds.

Synthetic PCM only (rule #8). An entry's CRC is made with :func:`crc.ctdb_crc` at
a chosen offset, the function the hardware vector pins (KDD-16), so the sweep has
to find exactly that offset.
"""

from __future__ import annotations

import random
from pathlib import Path

from platterpus.adapters.ctdb_client import CTDBClient, CtdbEntry, CtdbLookupResult
from platterpus.ctdb import crc as crc_mod
from platterpus.ctdb.matching import TrackVerdict
from platterpus.ctdb.toc import SAMPLES_PER_SECTOR, DiscToc
from platterpus.ctdb.verify import CtdbVerifyResult, Verdict, verify_rip
from platterpus.rip_report import _ctdb
from platterpus.ui.rip_progress import ctdb_verdict_line

# 54 sectors: the ±5879-sample window stays inside the disc at every offset.
_SECTORS = (17, 20, 17)
_FILES = [Path(f"{n:02d}.flac") for n in range(1, len(_SECTORS) + 1)]
_PCM = {
    path: random.Random(100 + index).randbytes(sectors * SAMPLES_PER_SECTOR * 4)
    for index, (path, sectors) in enumerate(zip(_FILES, _SECTORS, strict=True))
}
_WHOLE = b"".join(_PCM[p] for p in _FILES)


class _Client(CTDBClient):
    def __init__(self, entries: tuple[CtdbEntry, ...]) -> None:
        self._entries = entries

    def lookup(self, toc: DiscToc) -> CtdbLookupResult:
        return CtdbLookupResult(entries=self._entries)


def _verify(*entries: CtdbEntry) -> CtdbVerifyResult:
    return verify_rip(
        _FILES,
        _Client(entries),
        decoder=lambda p: _PCM[p],
        samples_probe=lambda p: len(_PCM[p]) // 4,
    )


def _crc_at(offset: int) -> int:
    value = crc_mod.ctdb_crc(_WHOLE, offset)
    assert value is not None
    return value


def test_a_pressing_1234_samples_away_is_found_and_named() -> None:
    result = _verify(CtdbEntry(crc=_crc_at(1234), confidence=40))
    assert result.verdict is Verdict.MATCH
    assert result.matched_offset == 1234
    assert result.offset_range == crc_mod.CTDB_OFFSET_RANGE
    assert result.trustworthy is True
    assert "a pressing +1,234 samples from ours" in result.message
    line = ctdb_verdict_line(result)
    assert line.startswith("CTDB: verified ✓ (confidence 40")
    assert "a pressing +1,234 samples from ours" in line
    block = _ctdb(result)
    assert block is not None
    assert block["matched_offset"] == 1234
    assert block["offset_range"] == crc_mod.CTDB_OFFSET_RANGE


def test_the_edges_of_ctdb_s_range_are_reached() -> None:
    for offset in (-crc_mod.CTDB_OFFSET_RANGE, crc_mod.CTDB_OFFSET_RANGE):
        result = _verify(CtdbEntry(crc=_crc_at(offset), confidence=3))
        assert result.matched_offset == offset, offset


def test_an_aligned_match_still_reads_as_it_did() -> None:
    result = _verify(CtdbEntry(crc=_crc_at(0), confidence=12))
    assert result.matched_offset == 0
    assert result.message == "verified against CTDB (confidence 12)"
    assert ctdb_verdict_line(result) == "CTDB: verified ✓ (confidence 12)"


def test_every_matched_entry_counts_and_the_strongest_names_the_offset() -> None:
    """CUETools' `Confidence` sums every error-free entry, whatever its offset."""
    result = _verify(
        CtdbEntry(crc=_crc_at(0), confidence=1),
        CtdbEntry(crc=_crc_at(-200), confidence=50),
        CtdbEntry(crc=0xDEADBEEF, confidence=30),
    )
    assert result.confidence == 51
    assert result.matched_crc == _crc_at(-200)
    assert result.matched_offset == -200
    assert result.best_confidence == 50
    assert result.outvoted is False
    assert result.disagreeing_confidence == 30


def test_a_match_away_from_alignment_vouches_for_every_track_at_that_offset() -> None:
    result = _verify(CtdbEntry(crc=_crc_at(777), confidence=9))
    assert [t.verdict for t in result.tracks] == [TrackVerdict.MATCH] * 3
    assert [t.offset for t in result.tracks] == [777] * 3
    assert [t.confidence for t in result.tracks] == [9] * 3


def test_a_no_match_after_the_sweep_says_what_was_tried() -> None:
    result = _verify(CtdbEntry(crc=0xDEADBEEF, confidence=5))
    assert result.verdict is Verdict.NO_MATCH
    assert result.offset_range == crc_mod.CTDB_OFFSET_RANGE
    assert result.matched_offset is None
    line = ctdb_verdict_line(result)
    assert "differs from every entry CTDB holds for this disc" in line
    assert "within ±5,879 samples" in line
    assert "standard alignment" not in line  # it is no longer the only one tried
    block = _ctdb(result)
    assert block is not None and block["matched_offset"] is None


def test_a_result_without_a_sweep_keeps_the_narrow_wording() -> None:
    """A result built from the aligned CRC alone (offset_range 0) must not claim
    the sweep: it says "standard alignment", as before R43."""
    line = ctdb_verdict_line(CtdbVerifyResult(Verdict.NO_MATCH, crc_validated=True))
    assert "no match at the standard alignment" in line
    assert "differs" not in line


def test_the_report_s_issue_says_the_range_after_a_sweep() -> None:
    from platterpus.rip_report import _issues

    def issue(ctdb: dict[str, object]) -> str:
        found = _issues(
            outcome={"status": "success", "ripper_exit_code": 0},
            verdict_level="ok",
            ctdb=ctdb,
            flac_integrity=None,
            derived=None,
            transcode=None,
            cover_art=None,
            read_speed=None,
        )
        assert [i["code"] for i in found] == ["ctdb_no_match"]
        return str(found[0]["message"])

    swept = issue({"verdict": "no_match", "crc_validated": True, "offset_range": 5879})
    assert "at any alignment within ±5,879 samples" in swept
    assert "ctdb.tracks" in swept
    narrow = issue({"verdict": "no_match", "crc_validated": True, "offset_range": 0})
    assert "standard alignment" in narrow
