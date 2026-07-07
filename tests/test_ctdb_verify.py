# SPDX-License-Identifier: GPL-3.0-only
"""Tests for platterpus.ctdb.verify + crc — the verdict logic (fakes only)."""

from __future__ import annotations

import zlib
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from platterpus.adapters.ctdb_client import (
    CTDBClient,
    CtdbEntry,
    CtdbLookupError,
    CtdbLookupResult,
)
from platterpus.ctdb import crc as crc_mod
from platterpus.ctdb.toc import SAMPLES_PER_SECTOR, DiscToc
from platterpus.ctdb.verify import CtdbVerifyResult, Verdict, verify_rip

# --- crc -------------------------------------------------------------------


def _big_pcm(frames: int) -> bytes:
    """Deterministic pseudo-PCM of `frames` stereo frames (4 bytes each)."""
    return bytes((i * 7 + 3) & 0xFF for i in range(frames * 4))


def test_ctdb_trims_front_fixed_back_length_dependent() -> None:
    # front = stride/2 = 5880 frames (10 sectors), fixed for every disc.
    assert crc_mod.ctdb_trims(20_000)[0] == 10 * 588
    # back = laststride/2, laststride = 11760 + (2*frames mod 11760).
    frames = 20_000
    laststride = crc_mod.CTDB_STRIDE_WORDS + ((2 * frames) % crc_mod.CTDB_STRIDE_WORDS)
    assert crc_mod.ctdb_trims(frames)[1] == laststride // 2


def test_ctdb_crc_offset0_is_zlib_crc32_of_the_trimmed_range() -> None:
    # The CRC IS zlib.crc32; only the TRIM (front stride/2, back laststride/2)
    # makes it the CTDB value — that trim was the bug the placeholder got wrong.
    pcm = _big_pcm(20_000)
    front, back = crc_mod.ctdb_trims(20_000)
    expected = zlib.crc32(pcm[front * 4 : len(pcm) - back * 4]) & 0xFFFFFFFF
    assert crc_mod.ctdb_crc_offset0(pcm) == expected


def test_ctdb_crc_none_when_disc_too_short_for_guard_band() -> None:
    # A handful of frames can't hold the ~14k-frame guard band → no CTDB CRC.
    assert crc_mod.ctdb_crc_offset0(b"\x00\x01\x02\x03" * 10) is None


def test_streaming_crc_equals_whole_buffer_crc() -> None:
    """Regression (#39): the whole-disc CRC is folded track-by-track to avoid
    buffering the entire album (+ its b''.join copy) — ~1.5 GB — in memory. The
    streamed offset-0 result must be byte-for-byte identical to CRC'ing the
    concatenation, so it's purely a memory optimization."""
    pcm = _big_pcm(20_000)
    chunks = [pcm[:1234], pcm[1234:50_000], b"", pcm[50_000:]]
    assert crc_mod.ctdb_crc_offset0_streaming(chunks, 20_000) == (
        crc_mod.ctdb_crc_offset0(pcm)
    )
    # A too-short disc has no CRC in either form.
    assert crc_mod.ctdb_crc_offset0_streaming([b"abc"], 10) is None


def test_offset_range_constant() -> None:
    # CTDB sweeps ±(stride/2 − 1) = ±5879 frames — WIDER than AccurateRip's
    # ±2939. Using the AR range was the KDD-16 calibration bug; pin the correct
    # CTDB value so it can't regress back.
    assert crc_mod.CTDB_OFFSET_RANGE == 5879
    assert crc_mod.CTDB_OFFSET_RANGE == crc_mod.CTDB_STRIDE_WORDS // 2 - 1


@given(st.binary(max_size=400))
def test_ctdb_crc_never_raises_on_arbitrary_bytes(data: bytes) -> None:
    # The CRC consumes decoded PCM (external-derived), so — like the parsers —
    # it must never raise: only ever an int or None, for any input length.
    total = len(data) // crc_mod.BYTES_PER_SAMPLE_FRAME
    for value in (
        crc_mod.ctdb_crc(data, 0),
        crc_mod.ctdb_crc(data, 100),
        crc_mod.ctdb_crc_offset0(data),
        crc_mod.ctdb_crc_offset0_streaming([data], total),
    ):
        assert value is None or isinstance(value, int)


# --- fakes -----------------------------------------------------------------


class _FakeClient(CTDBClient):
    def __init__(self, result: CtdbLookupResult | Exception) -> None:
        self._result = result

    def lookup(self, toc: DiscToc) -> CtdbLookupResult:
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


_FLACS = [Path("01.flac"), Path("02.flac")]
# Each "file" decodes to 17 WHOLE sectors (9996 frames), so (a) the disc is long
# enough to hold the CTDB guard band (front 5880 + back ~8232 frames — a shorter
# disc has no CRC) and (b) sample count is sector-aligned, so the TOC-derived
# total_frames equals the decoded frame count (as it is for a real CD rip).
_FRAMES_PER_FILE = 17 * SAMPLES_PER_SECTOR  # 9996
_PCM = {
    p: bytes((i * 5 + 1) & 0xFF for i in range(_FRAMES_PER_FILE * 4)) for p in _FLACS
}


def _probe(_: Path) -> int:
    return _FRAMES_PER_FILE


def _decoder(path: Path) -> bytes:
    return _PCM[path]


def _whole_disc_crc() -> int:
    # The CORRECT offset-0 CTDB CRC of the concatenated disc (not a plain crc32).
    return crc_mod.ctdb_crc_offset0(b"".join(_PCM[p] for p in _FLACS))


# --- verdicts --------------------------------------------------------------


def test_not_in_database() -> None:
    client = _FakeClient(CtdbLookupResult(entries=()))
    res = verify_rip(_FLACS, client, decoder=_decoder, samples_probe=_probe)
    assert res.verdict is Verdict.NOT_IN_DATABASE


def test_match_when_crc_equals_entry() -> None:
    entry = CtdbEntry(crc=_whole_disc_crc(), confidence=42)
    client = _FakeClient(CtdbLookupResult(entries=(entry,)))
    res = verify_rip(_FLACS, client, decoder=_decoder, samples_probe=_probe)
    assert res.verdict is Verdict.MATCH
    assert res.confidence == 42
    assert res.our_crc == _whole_disc_crc()


def test_match_is_flagged_experimental_until_validated() -> None:
    entry = CtdbEntry(crc=_whole_disc_crc(), confidence=1)
    client = _FakeClient(CtdbLookupResult(entries=(entry,)))
    res = verify_rip(_FLACS, client, decoder=_decoder, samples_probe=_probe)
    # CRC_VALIDATED is False until hardware confirms it (KDD-16).
    assert res.crc_validated is False
    assert res.trustworthy is False
    assert "experimental" in res.message.lower()


def test_no_match_when_crc_differs() -> None:
    entry = CtdbEntry(crc=0xDEADBEEF, confidence=5)
    client = _FakeClient(CtdbLookupResult(entries=(entry,)))
    res = verify_rip(_FLACS, client, decoder=_decoder, samples_probe=_probe)
    assert res.verdict is Verdict.NO_MATCH
    assert res.confidence == 5  # best confidence still surfaced
    # The DB's CRC(s) are carried on the result so a report / --ctdb-calibrate
    # can diagnose our_crc vs the expected value(s) without a second lookup.
    assert res.db_crcs == (0xDEADBEEF,)
    assert res.our_crc == _whole_disc_crc()


def test_no_match_message_does_not_blame_the_rip_while_unvalidated() -> None:
    # Regression (real-disc Police report): a NO_MATCH message must not lead with
    # "the rip differs" while CRC_VALIDATED is False (KDD-16) — our CRC is a
    # placeholder EXPECTED to disagree, so it says nothing about the rip.
    entry = CtdbEntry(crc=0xDEADBEEF, confidence=1347)
    client = _FakeClient(CtdbLookupResult(entries=(entry,)))
    res = verify_rip(_FLACS, client, decoder=_decoder, samples_probe=_probe)
    assert res.crc_validated is False
    assert "not yet hardware-validated" in res.message
    assert "KDD-16" in res.message
    # It must NOT flatly assert the rip differs (that's the false alarm).
    assert "this rip differs" not in res.message


def test_lookup_error_is_a_verdict_not_a_raise() -> None:
    client = _FakeClient(CtdbLookupError("network down"))
    res = verify_rip(_FLACS, client, decoder=_decoder, samples_probe=_probe)
    assert res.verdict is Verdict.LOOKUP_ERROR


def test_decoder_unavailable_after_db_hit() -> None:
    from platterpus.ctdb.decode import DecoderUnavailable

    entry = CtdbEntry(crc=123, confidence=3)
    client = _FakeClient(CtdbLookupResult(entries=(entry,)))

    def no_decoder(path: Path) -> bytes:
        raise DecoderUnavailable("no flac")

    res = verify_rip(_FLACS, client, decoder=no_decoder, samples_probe=_probe)
    assert res.verdict is Verdict.DECODER_UNAVAILABLE
    assert res.confidence == 3  # DB hit still reported


def test_trustworthy_true_for_non_match_verdicts() -> None:
    res = CtdbVerifyResult(Verdict.NOT_IN_DATABASE)
    assert res.trustworthy is True


def test_toc_build_timeout_is_lookup_error_not_a_raise() -> None:
    # BUG-4: a wedged flac/metaflac raises subprocess.TimeoutExpired, which is
    # NOT an OSError/RuntimeError/ValueError — so it used to bypass the never-raise
    # classification and escape uncaught. It must become a LOOKUP_ERROR verdict.
    import subprocess

    def timing_out_probe(_p: Path) -> int:
        raise subprocess.TimeoutExpired(cmd="metaflac", timeout=5)

    client = _FakeClient(CtdbLookupResult(entries=()))
    res = verify_rip(_FLACS, client, decoder=_decoder, samples_probe=timing_out_probe)
    assert res.verdict is Verdict.LOOKUP_ERROR


def test_decode_timeout_after_db_hit_is_lookup_error() -> None:
    # BUG-4: same for a decoder that wedges during the CRC pass (after a DB hit).
    import subprocess

    entry = CtdbEntry(crc=123, confidence=3)
    client = _FakeClient(CtdbLookupResult(entries=(entry,)))

    def timing_out_decoder(_p: Path) -> bytes:
        raise subprocess.TimeoutExpired(cmd="flac", timeout=5)

    res = verify_rip(_FLACS, client, decoder=timing_out_decoder, samples_probe=_probe)
    assert res.verdict is Verdict.LOOKUP_ERROR


def test_toc_build_error_is_lookup_error() -> None:
    # A probe failure while building the TOC (before any lookup) → LOOKUP_ERROR.
    def bad_probe(_p: Path) -> int:
        raise RuntimeError("metaflac exploded")

    client = _FakeClient(CtdbLookupResult(entries=()))
    res = verify_rip(_FLACS, client, decoder=_decoder, samples_probe=bad_probe)
    assert res.verdict is Verdict.LOOKUP_ERROR
    assert "TOC error" in res.message


def test_decode_oserror_after_db_hit_is_lookup_error() -> None:
    # DB hit, then the decode raises a non-DecoderUnavailable error.
    entry = CtdbEntry(crc=123, confidence=4)
    client = _FakeClient(CtdbLookupResult(entries=(entry,)))

    def bad_decoder(_p: Path) -> bytes:
        raise OSError("disk vanished mid-read")

    res = verify_rip(_FLACS, client, decoder=bad_decoder, samples_probe=_probe)
    assert res.verdict is Verdict.LOOKUP_ERROR
    assert res.confidence == 4  # DB hit still surfaced
