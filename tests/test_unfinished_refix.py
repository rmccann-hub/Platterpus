"""What a stopped securing pass may still give the album (`unfinished_refix.py`).

Run B of the 0.7.112 Full runs (2026-10-21): the securing pass was stopped during
track 18, and track 11's finished re-read, which matched AccurateRip at
confidence 29 where the album pass's read matched nothing, was thrown away with
the pass. These pin the per-track decision and the file-whole check it rests on.
"""

from __future__ import annotations

from pathlib import Path

from platterpus.checksums import flac_total_samples, flac_unencoded_md5
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.unfinished_refix import (
    NOT_REPLACED_BLOCK_INCOMPLETE,
    NOT_REPLACED_FILE_NOT_WHOLE,
    NOT_REPLACED_NOT_VERIFIED,
    expected_samples,
    file_written_whole,
    salvage_decision,
)
from platterpus.verdict import REREAD_KEPT_FOR_ACCURATERIP

#: Run B's track 11: Start LSN 135147, End LSN 149259, `Samples: 8298444`.
_RUN_B_TRACK_11_SAMPLES = 8298444


def _flac(total_samples: int, md5: bytes | None = None) -> bytes:
    """A FLAC header; ``md5`` None means the all-zero "never closed" value."""
    packed = (44100 << 44) | (1 << 41) | (15 << 36) | total_samples
    payload = bytes(10) + packed.to_bytes(8, "big") + (md5 or bytes(16))
    return b"fLaC" + bytes([0x80, 0, 0, 34]) + payload


def _track(accurip: str) -> object:
    """Track 11 of run B's securing-pass log, with the AccurateRip rows given."""
    text = (
        "cyanrip 0.9.4-rc3+platterpus.26 (platterpus-fork-gca0f097)\n"
        "Disc tracks:    18\n"
        "Done; (repeat limit of 5 reads reached; at most 1 read agreed)\n"
        "Track 11 read with errors.\n"
        "    Start LSN:   135147 (with offset: 135148)\n"
        "    End LSN:     149259 (with offset: 149261)\n"
        "  EAC CRC32:     10248071 (after 5 rips)\n"
        f"{accurip}"
        "  File(s):\n"
        "    Artist/Album/11 - A.flac\n"
    )
    return next(t for t in parse_cyanrip_log(text).tracks if t.number == 11)


_VERIFIED = (
    "    Accurip v1:  9FCC4FB0 (accurately ripped, confidence 12)\n"
    "    Accurip v2:  F90C8B07 (accurately ripped, confidence 29)\n"
)
_NOT_FOUND = (
    "    Accurip v1:  D2A1E64C (not found, either a new pressing, or bad rip)\n"
    "    Accurip v2:  5FD4DDDF (not found, either a new pressing, or bad rip)\n"
)


def test_the_sample_count_is_read_from_streaminfo(tmp_path: Path) -> None:
    path = tmp_path / "a.flac"
    path.write_bytes(_flac(_RUN_B_TRACK_11_SAMPLES, bytes(range(16))))
    assert flac_total_samples(path) == _RUN_B_TRACK_11_SAMPLES
    # The refactor kept the MD5 reader reading the same 16 bytes.
    assert flac_unencoded_md5(path) == bytes(range(16)).hex()


def test_a_header_never_closed_has_no_sample_count(tmp_path: Path) -> None:
    path = tmp_path / "a.flac"
    path.write_bytes(_flac(0))
    assert flac_total_samples(path) is None
    assert flac_unencoded_md5(path) is None
    (tmp_path / "b.flac").write_bytes(b"fLaC\x80\x00")
    assert flac_total_samples(tmp_path / "b.flac") is None
    assert flac_total_samples(tmp_path / "missing.flac") is None


def test_expected_samples_is_the_logs_sector_range() -> None:
    assert expected_samples(_track(_VERIFIED)) == _RUN_B_TRACK_11_SAMPLES
    assert expected_samples(object()) is None


def test_run_b_track_11_is_swapped_in(tmp_path: Path) -> None:
    """The case itself: verified, block complete, file closed and complete."""
    path = tmp_path / "11.flac"
    path.write_bytes(_flac(_RUN_B_TRACK_11_SAMPLES, bytes(range(1, 17))))
    decision = salvage_decision(_track(_NOT_FOUND), _track(_VERIFIED), path)
    assert decision.swap is True
    assert decision.replaced_because == REREAD_KEPT_FOR_ACCURATERIP
    assert decision.not_replaced_because is None


def test_a_re_read_accuraterip_did_not_verify_keeps_the_first_read(
    tmp_path: Path,
) -> None:
    """Run B's tracks 12 to 17: one frame matched, the tracks did not."""
    path = tmp_path / "12.flac"
    path.write_bytes(_flac(_RUN_B_TRACK_11_SAMPLES, bytes(range(1, 17))))
    decision = salvage_decision(_track(_NOT_FOUND), _track(_NOT_FOUND), path)
    assert (decision.swap, decision.not_replaced_because) == (
        False,
        NOT_REPLACED_NOT_VERIFIED,
    )
    # A first read AccurateRip verified is never replaced, whatever the re-read.
    decision = salvage_decision(_track(_VERIFIED), _track(_VERIFIED), path)
    assert decision.swap is False


def test_a_file_that_is_not_whole_keeps_the_first_read(tmp_path: Path) -> None:
    short = tmp_path / "short.flac"
    short.write_bytes(_flac(_RUN_B_TRACK_11_SAMPLES - 588, bytes(range(1, 17))))
    unclosed = tmp_path / "unclosed.flac"
    unclosed.write_bytes(_flac(0))
    no_md5 = tmp_path / "nomd5.flac"
    no_md5.write_bytes(_flac(_RUN_B_TRACK_11_SAMPLES))
    for path in (short, unclosed, no_md5, tmp_path / "missing.flac"):
        decision = salvage_decision(_track(_NOT_FOUND), _track(_VERIFIED), path)
        assert decision.not_replaced_because == NOT_REPLACED_FILE_NOT_WHOLE, path
        assert decision.swap is False
        assert file_written_whole(path, _track(_VERIFIED))[0] is False


def test_a_block_with_no_file_row_keeps_the_first_read() -> None:
    decision = salvage_decision(_track(_NOT_FOUND), _track(_VERIFIED), None)
    assert decision.not_replaced_because == NOT_REPLACED_BLOCK_INCOMPLETE
