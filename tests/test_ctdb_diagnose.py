# SPDX-License-Identifier: GPL-3.0-only
"""Tests for platterpus.ctdb.diagnose — the shared CTDB verify/calibrate engine
behind `scripts/ctdb_verify.py` and `platterpus --ctdb-calibrate` (fakes only)."""

from __future__ import annotations

from pathlib import Path

import pytest

from platterpus.adapters.ctdb_client import (
    CTDBClient,
    CtdbEntry,
    CtdbLookupResult,
)
from platterpus.ctdb import decode as decode_mod
from platterpus.ctdb import diagnose
from platterpus.ctdb.toc import SAMPLES_PER_SECTOR, DiscToc


class _FakeClient(CTDBClient):
    def __init__(self, result: CtdbLookupResult) -> None:
        self._result = result

    def lookup(self, toc: DiscToc) -> CtdbLookupResult:
        return self._result


# 17 whole sectors per file: sector-aligned (TOC total_frames == decoded frames)
# and long enough for the CTDB guard band (front 5880 + back ~8232 frames).
_FRAMES_PER_FILE = 17 * SAMPLES_PER_SECTOR  # 9996


def _probe(_: Path) -> int:
    return _FRAMES_PER_FILE


def _make_flacs(tmp_path: Path, n: int = 2) -> tuple[list[Path], bytes]:
    """Create `n` empty .flac files; return them + the per-file PCM they map to
    (17 sectors of deterministic pseudo-audio each)."""
    flacs = []
    for i in range(1, n + 1):
        p = tmp_path / f"{i:02d}.flac"
        p.write_bytes(b"")
        flacs.append(p)
    pcm = bytes((i * 5 + 1) & 0xFF for i in range(_FRAMES_PER_FILE * 4))  # per file
    return flacs, pcm


def _decoder_for(pcm: bytes):
    return lambda _path: pcm


def _capture() -> tuple[list[str], diagnose.Out]:
    lines: list[str] = []
    return lines, lines.append


def test_no_flacs_returns_2(tmp_path: Path) -> None:
    lines, out = _capture()
    rc = diagnose.run_diagnostics(
        tmp_path, out=out, client=_FakeClient(CtdbLookupResult())
    )
    assert rc == 2
    assert any("No .flac files" in ln for ln in lines)


def test_verify_no_match_reports_db_crcs(tmp_path: Path) -> None:
    flacs, pcm = _make_flacs(tmp_path)
    client = _FakeClient(
        CtdbLookupResult(entries=(CtdbEntry(crc=0xDEADBEEF, confidence=9),))
    )
    lines, out = _capture()
    rc = diagnose.run_diagnostics(
        tmp_path,
        out=out,
        client=client,
        decoder=_decoder_for(pcm),
        samples_probe=_probe,
    )
    assert rc == 0
    text = "\n".join(lines)
    assert "no_match" in text
    assert "deadbeef" in text  # the DB CRC is surfaced for diagnosis


def test_calibrate_finds_the_offset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Build a whole-disc PCM and use its CORRECT offset-0 CTDB CRC as the
    # "expected" DB CRC, so the sweep must find a match at offset 0 — proving the
    # calibrate wiring end to end.
    from platterpus.ctdb import crc as crc_mod

    flacs, pcm = _make_flacs(tmp_path, n=2)
    whole = pcm * 2  # two files, concatenated as the decoder yields them
    expected_crc = crc_mod.ctdb_crc_offset0(whole)
    assert expected_crc is not None
    client = _FakeClient(
        CtdbLookupResult(entries=(CtdbEntry(crc=expected_crc, confidence=1347),))
    )
    # calibrate() guards on a real flac decoder being present.
    monkeypatch.setattr(decode_mod, "flac_available", lambda: True)
    lines, out = _capture()
    rc = diagnose.run_diagnostics(
        tmp_path,
        calibrate_crc=True,
        out=out,
        client=client,
        decoder=_decoder_for(pcm),
        samples_probe=_probe,
    )
    assert rc == 0
    text = "\n".join(lines)
    assert "MATCH — the CTDB-CRC algorithm is confirmed" in text
    assert "offset=+0" in text
    assert "confidence 1347" in text


def test_calibrate_bails_when_not_in_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    flacs, pcm = _make_flacs(tmp_path)
    monkeypatch.setattr(decode_mod, "flac_available", lambda: True)
    lines, out = _capture()
    rc = diagnose.run_diagnostics(
        tmp_path,
        calibrate_crc=True,
        out=out,
        client=_FakeClient(CtdbLookupResult()),  # empty → not in DB
        decoder=_decoder_for(pcm),
        samples_probe=_probe,
    )
    assert rc == 0
    assert any("isn't in CTDB" in ln for ln in lines)


def test_toc_build_without_decoder_returns_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No metaflac/flac to read sample counts → can't build the TOC. It must
    # report clearly and exit 3, never crash (real-hardware failure mode).
    flacs, _pcm = _make_flacs(tmp_path)

    def _boom(_p: Path) -> int:
        raise decode_mod.DecoderUnavailable("no metaflac")

    lines, out = _capture()
    rc = diagnose.run_diagnostics(
        tmp_path,
        out=out,
        client=_FakeClient(CtdbLookupResult()),
        decoder=_decoder_for(b""),
        samples_probe=_boom,
    )
    assert rc == 3
    assert any("Cannot build TOC" in ln for ln in lines)


def test_calibrate_bails_without_flac_decoder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The disc verify can still run (TOC via metaflac), but calibration needs the
    # `flac` decoder to produce PCM — it must say so, not crash.
    flacs, pcm = _make_flacs(tmp_path)
    monkeypatch.setattr(decode_mod, "flac_available", lambda: False)
    lines, out = _capture()
    rc = diagnose.run_diagnostics(
        tmp_path,
        calibrate_crc=True,
        out=out,
        client=_FakeClient(CtdbLookupResult(entries=(CtdbEntry(crc=1, confidence=1),))),
        decoder=_decoder_for(pcm),
        samples_probe=_probe,
    )
    assert rc == 0
    assert any("flac` decoder isn't available" in ln for ln in lines)
