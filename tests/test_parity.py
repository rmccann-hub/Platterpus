"""Tests for platterpus.parity and the scripts/eac_parity.py CLI.

Covers the cross-format Copy-CRC dispatch (EAC / cyanrip / the legacy log
format), the
baseline-vs-candidate comparison (match, mismatch, missing, extra), and a
smoke test of the CLI against the committed EAC baseline.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from platterpus.parity import compare_logs, decode_log_bytes, track_copy_crcs

_REPO_ROOT = Path(__file__).resolve().parents[1]
_EAC_BASELINE = (
    _REPO_ROOT / "output_reference" / "EAC_flac" / "eac_baseline_police_classics.log"
)
_CYANRIP_REFERENCE = (
    _REPO_ROOT
    / "output_reference"
    / "cyanrip_flac"
    / "cyanrip_flac_police_classics.log"
)


# --- Synthetic log builders (one per format) ------------------------------


def _eac(crcs: dict[int, str]) -> str:
    body = "Exact Audio Copy V1.8 from 15. July 2024\n\n"
    for n, crc in crcs.items():
        body += f"Track  {n}\n\n     Copy CRC {crc}\n\n"
    return body


def _legacy(crcs: dict[int, str]) -> str:
    # The legacy log format's real header line: the parser dispatches on it, so
    # it names the tool that wrote the format rather than a neutral stand-in.
    body = "Log created by: whipper 0.10.0\n\nTracks:\n"
    for n, crc in crcs.items():
        body += f"  {n}:\n    Copy CRC: {crc}\n"
    return body


def _cyanrip(crcs: dict[int, str]) -> str:
    body = "cyanrip 0.9.3.1 (test)\n"
    for n, crc in crcs.items():
        body += f"Track {n} ripped and encoded successfully!\n  EAC CRC32:     {crc}\n"
    return body


# --- track_copy_crcs: format dispatch -------------------------------------


def test_dispatch_reads_eac() -> None:
    assert track_copy_crcs(_eac({1: "AAAA1111", 2: "BBBB2222"})) == {
        1: "AAAA1111",
        2: "BBBB2222",
    }


def test_dispatch_reads_the_legacy_format() -> None:
    assert track_copy_crcs(_legacy({1: "aaaa1111"})) == {1: "AAAA1111"}  # upper-cased


def test_dispatch_reads_cyanrip() -> None:
    assert track_copy_crcs(_cyanrip({1: "AAAA1111", 2: "BBBB2222"})) == {
        1: "AAAA1111",
        2: "BBBB2222",
    }


def test_dispatch_on_the_committed_eac_baseline() -> None:
    crcs = track_copy_crcs(decode_log_bytes(_EAC_BASELINE.read_bytes()))
    assert len(crcs) == 14
    assert crcs[1] == "B0D122E7"
    assert crcs[14] == "787BA2D6"


def test_unknown_text_yields_empty() -> None:
    assert track_copy_crcs("nonsense\n:::\n") == {}


# --- Committed reference-data regression guard ----------------------------
#
# "Make parity measurable and routine" (docs/eac-parity.md P1):
# run the two committed REAL-disc logs through the real comparison so a silent
# parser/parity regression — or an accidental re-encode/corruption of the
# committed artifacts — fails loudly, with no hardware needed. The numbers
# below are the documented ground truth for The Police — *Every Breath You
# Take: The Classics* (cyanrip 0.9.3, BDR-209D, +667): the cyanrip rip is
# byte-identical to the EAC baseline on 12 of 14 tracks; T3 is the
# offset-450 near-miss and T5 is the disc's defective spot (EAC fails it too).
# If this count or the offending tracks change, something moved — investigate.


def test_committed_cyanrip_reference_matches_eac_baseline_12_of_14() -> None:
    eac = decode_log_bytes(_EAC_BASELINE.read_bytes())
    cyanrip = decode_log_bytes(_CYANRIP_REFERENCE.read_bytes())
    report = compare_logs(eac, cyanrip)
    assert report.total == 14
    assert report.matched == 12
    assert report.ok is False  # not 14/14 — T3 + T5 differ, as documented
    differing = {t.number for t in report.tracks if not t.ok}
    assert differing == {3, 5}


def test_committed_eac_baseline_full_crc_vector() -> None:
    """Pin all 14 Copy CRCs of the committed EAC baseline so a corrupted or
    re-encoded artifact (e.g. a botched UTF-16 round-trip) fails loudly."""
    crcs = track_copy_crcs(decode_log_bytes(_EAC_BASELINE.read_bytes()))
    assert crcs == {
        1: "B0D122E7",
        2: "985AAE32",
        3: "59D352DD",
        4: "60D796AE",
        5: "E0036697",
        6: "B32769D6",
        7: "CCBFF669",
        8: "D723C1B0",
        9: "6F6E4A5F",
        10: "3A33519F",
        11: "56BFC63D",
        12: "D78CEAEF",
        13: "DA6A4DAF",
        14: "787BA2D6",
    }


# --- compare_logs ----------------------------------------------------------


def test_identical_is_parity() -> None:
    base = _eac({1: "AAAA1111", 2: "BBBB2222"})
    report = compare_logs(base, base)
    assert report.ok is True
    assert report.matched == report.total == 2


def test_cross_format_same_crcs_is_parity() -> None:
    # The whole point: EAC baseline vs a legacy-format rip with identical Copy CRCs.
    crcs = {1: "AAAA1111", 2: "BBBB2222"}
    report = compare_logs(_eac(crcs), _legacy(crcs))
    assert report.ok is True
    assert report.matched == 2


def test_one_wrong_crc_fails_and_is_identified() -> None:
    report = compare_logs(
        _eac({1: "AAAA1111", 2: "BBBB2222"}),
        _cyanrip({1: "AAAA1111", 2: "DEADBEEF"}),
    )
    assert report.ok is False
    assert report.matched == 1
    failing = [t.number for t in report.tracks if not t.ok]
    assert failing == [2]


def test_missing_track_in_candidate_fails() -> None:
    report = compare_logs(
        _eac({1: "AAAA1111", 2: "BBBB2222"}), _legacy({1: "AAAA1111"})
    )
    assert report.ok is False
    track2 = next(t for t in report.tracks if t.number == 2)
    assert track2.candidate_crc == ""  # missing
    assert track2.ok is False


def test_extra_track_in_candidate_fails() -> None:
    report = compare_logs(
        _eac({1: "AAAA1111"}), _legacy({1: "AAAA1111", 2: "BBBB2222"})
    )
    assert report.ok is False  # candidate has a track the baseline doesn't
    assert report.extra == (2,)


def test_empty_baseline_is_never_parity() -> None:
    report = compare_logs("nonsense", _legacy({1: "AAAA1111"}))
    assert report.ok is False
    assert report.total == 0


# --- Output-format semantics: WAV and MP3 share the extraction-CRC path -----
#
# The per-track Copy CRC is computed on the EXTRACTED PCM, before (and
# independent of) the output encoder, so ONE parity check covers FLAC, WAV and
# MP3:
#   * WAV is lossless → a WAV rip's Copy CRCs equal the FLAC baseline's, so the
#     committed EAC *FLAC* baseline IS the WAV target — no separate WAV baseline
#     is needed (TASKS.md "WAV (lossless → same Copy CRCs as FLAC)").
#   * MP3 is lossy → the audio is NOT bit-comparable, but the extraction CRC
#     still proves the disc read was bit-perfect; "MP3 parity" = that CRC matches
#     PLUS correct encoder/tag behaviour (the latter verified elsewhere, not here).
# These two tests pin those invariants against the real committed baseline so a
# future regression in the format-dispatch is caught.


def test_wav_rip_parities_against_the_committed_flac_baseline() -> None:
    base = decode_log_bytes(_EAC_BASELINE.read_bytes())
    flac_crcs = track_copy_crcs(base)
    # A WAV rip of the same disc yields the SAME per-track Copy CRCs (lossless),
    # so a WAV-rip log compares clean against the FLAC baseline.
    wav_rip_log = _legacy(flac_crcs)
    report = compare_logs(base, wav_rip_log)
    assert report.ok is True
    assert report.matched == report.total == 14


def test_mp3_rip_parities_on_extraction_crc() -> None:
    base = decode_log_bytes(_EAC_BASELINE.read_bytes())
    flac_crcs = track_copy_crcs(base)
    # A cyanrip MP3 rip still logs the per-track EAC CRC32 of the *decoded PCM*;
    # that extraction CRC matches the baseline even though the MP3 audio is lossy.
    mp3_rip_log = _cyanrip(flac_crcs)
    report = compare_logs(base, mp3_rip_log)
    assert report.ok is True
    assert report.matched == 14


# --- decode_log_bytes: EAC writes UTF-16 (regression) ----------------------
#
# Real EAC logs are UTF-16-with-BOM. Reading them as UTF-8 turned every char
# into a replacement char → the parser found zero CRCs → the parity check
# silently reported "NOT parity (0/N)" on a perfectly good rip. Found 2026-06-25
# when a real EAC MP3 log was run through scripts/eac_parity.py.


def test_decode_utf16le_bom() -> None:
    text = "Exact Audio Copy\n     Copy CRC B0D122E7\n"
    raw = b"\xff\xfe" + text.encode("utf-16-le")
    assert decode_log_bytes(raw) == text


def test_decode_utf16be_bom() -> None:
    text = "Exact Audio Copy\n     Copy CRC B0D122E7\n"
    raw = b"\xfe\xff" + text.encode("utf-16-be")
    assert decode_log_bytes(raw) == text


def test_decode_utf8_bom() -> None:
    text = "Log created by: whipper 0.10.0\n"  # the legacy format's real header
    assert decode_log_bytes(b"\xef\xbb\xbf" + text.encode("utf-8")) == text


def test_decode_plain_utf8() -> None:
    text = "cyanrip 0.9.3.1\n  EAC CRC32:     AAAA1111\n"
    assert decode_log_bytes(text.encode("utf-8")) == text


def test_decode_bomless_utf16le_heuristic() -> None:
    # No BOM, but NUL-heavy → guessed as UTF-16-LE.
    text = "Exact Audio Copy\n     Copy CRC AAAA1111\n"
    assert decode_log_bytes(text.encode("utf-16-le")) == text


def test_decode_never_raises_on_garbage() -> None:
    # Arbitrary bytes must not blow up (errors="replace").
    assert isinstance(decode_log_bytes(b"\xff\xfe\x00\x01\x80\x81"), str)
    assert isinstance(decode_log_bytes(b"\x80\x81\x82"), str)


def test_utf16_eac_log_parities_after_decode() -> None:
    """The actual bug: an EAC log encoded as UTF-16 must compare clean once
    decoded, instead of every track reading as 'missing'."""
    crcs = {1: "AAAA1111", 2: "BBBB2222"}
    baseline = _eac(crcs)
    eac_utf16_bytes = b"\xff\xfe" + _eac(crcs).encode("utf-16-le")
    candidate = decode_log_bytes(eac_utf16_bytes)
    report = compare_logs(baseline, candidate)
    assert report.ok is True
    assert report.matched == 2
    # And the pre-fix failure mode (decode as UTF-8) would have found nothing:
    assert track_copy_crcs(eac_utf16_bytes.decode("utf-8", errors="replace")) == {}


# --- CLI smoke (scripts/eac_parity.py) ------------------------------------


def _load_cli():
    spec = importlib.util.spec_from_file_location(
        "eac_parity_cli", _REPO_ROOT / "scripts" / "eac_parity.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_cli_exit_zero_when_candidate_matches_baseline(capsys) -> None:
    cli = _load_cli()
    # Baseline compared against itself → every CRC matches → exit 0.
    rc = cli.main([str(_EAC_BASELINE), str(_EAC_BASELINE)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PARITY" in out
    assert "Track  1: PASS" in out


def test_cli_exit_one_on_mismatch(tmp_path: Path, capsys) -> None:
    cli = _load_cli()
    bad = tmp_path / "bad.log"
    bad.write_text(_legacy({1: "DEADBEEF"}), encoding="utf-8")  # wrong CRCs
    rc = cli.main([str(_EAC_BASELINE), str(bad)])
    assert rc == 1
    assert "NOT parity" in capsys.readouterr().out


def test_cli_unreadable_baseline_returns_2(tmp_path: Path) -> None:
    cli = _load_cli()
    rc = cli.main([str(tmp_path / "missing.log"), str(_EAC_BASELINE)])
    assert rc == 2


# --- Properties: the decoder and the extractor over every input shape -----------
#
# Every test above pins one encoding of one short text. The decoder takes ARBITRARY
# bytes from disk and the extractor turns them into the per-track checksums a parity
# verdict is built on, so both are stated here once over the whole input space.

_NO_SURROGATES = st.characters(blacklist_categories=["Cs"])
_BOMS: dict[str, tuple[bytes, str]] = {
    "utf-16-le BOM": (b"\xff\xfe", "utf-16-le"),
    "utf-16-be BOM": (b"\xfe\xff", "utf-16-be"),
    "utf-8 BOM": (b"\xef\xbb\xbf", "utf-8"),
}


@given(st.text(_NO_SURROGATES, max_size=80), st.sampled_from(sorted(_BOMS)))
def test_a_bom_decides_the_encoding_and_the_text_survives_whole(
    text: str, which: str
) -> None:
    """With a BOM the text comes back exactly — including a text that itself
    starts with U+FEFF, which a decoder stripping every BOM would eat."""
    bom, codec = _BOMS[which]
    assert decode_log_bytes(bom + text.encode(codec)) == text


@given(st.text(_NO_SURROGATES, max_size=80))
def test_plain_utf8_survives_whole_unless_it_looks_like_utf16(text: str) -> None:
    """The default path. The only UTF-8 texts it may misread are the two the
    sniffing rules name: a leading U+FEFF (which IS a UTF-8 BOM) and a head more
    than a quarter NUL (which reads as BOM-less UTF-16)."""
    raw = text.encode("utf-8")
    head = raw[:256]
    looks_utf16 = bool(head) and head.count(0) > len(head) // 4
    if text.startswith("﻿") or looks_utf16:
        return
    assert decode_log_bytes(raw) == text


@given(
    st.text(st.characters(min_codepoint=1, max_codepoint=255), min_size=1, max_size=80),
    st.sampled_from(["utf-16-le", "utf-16-be"]),
)
def test_bomless_utf16_of_ascii_ish_text_is_recognised_either_way_round(
    text: str, codec: str
) -> None:
    """The heuristic's own claim: an ASCII-ish UTF-16 file is half NUL bytes, and
    where the NULs fall says which byte order it is."""
    assert decode_log_bytes(text.encode(codec)) == text


@given(st.binary(max_size=600))
def test_any_bytes_decode_to_text_and_extract_without_raising(raw: bytes) -> None:
    """Whatever is on disk, text comes back and extraction yields a map. (Random
    bytes almost never form a log, so the CRC-shape rule is asserted below, over
    logs that do.)"""
    text = decode_log_bytes(raw)
    assert isinstance(text, str)
    assert isinstance(track_copy_crcs(text), dict)


def test_two_logs_with_the_same_garbled_crc_are_not_a_parity_match() -> None:
    """REGRESSION, found by the property below on its first run (2026-09-25).

    The legacy-format parser keeps its `Copy CRC:` field verbatim, and the extractor
    upper-cased whatever it held — so `n/a` became the "CRC" `N/A`, and a baseline
    and a candidate both carrying it compared as a bit-perfect match: a parity
    claim made about two checksums neither log contains.
    """
    garbled = _legacy({1: "n/a", 2: "AAAA1111"})
    assert track_copy_crcs(garbled) == {2: "AAAA1111"}
    report = compare_logs(garbled, garbled)
    assert [t.number for t in report.tracks] == [2], "track 1 has no CRC to compare"


_BUILDERS = {"eac": _eac, "cyanrip": _cyanrip, "legacy": _legacy}
_HEX8 = st.text("0123456789abcdefABCDEF", min_size=8, max_size=8)
#: A value that is not a checksum at all. Drawn with no hex digit in it, so no
#: prefix of it could be one either — the property is about garbage, not about
#: where a checksum ends.
_NOT_A_CRC = st.text(
    st.characters(
        blacklist_characters="0123456789abcdefABCDEF\n\r\x0b\x0c\x1c\x1d\x1e\x85  ",
        blacklist_categories=["Cs"],
    ),
    max_size=12,
)


@given(
    values=st.dictionaries(
        st.integers(0, 99), st.one_of(_HEX8, _NOT_A_CRC), min_size=1, max_size=12
    ),
    backend=st.sampled_from(sorted(_BUILDERS)),
)
def test_a_malformed_crc_costs_that_track_and_never_becomes_one(
    values: dict[int, str], backend: str
) -> None:
    """Each backend's log with some checksum values replaced by garbage: every
    track with a real CRC keeps it, and every garbled one is ABSENT — never reported
    as a "Copy CRC", where two logs carrying the same garbage would compare as a
    bit-perfect match."""
    got = track_copy_crcs(_BUILDERS[backend](values))
    for crc in got.values():
        assert re.fullmatch(r"[0-9A-F]{8}", crc), f"{backend} reported {crc!r} as a CRC"
    real = {
        n: v.upper() for n, v in values.items() if re.fullmatch(r"[0-9A-Fa-f]{8}", v)
    }
    assert got == real


_ENCODINGS: dict[str, tuple[bytes, str]] = {
    **_BOMS,
    "utf-8": (b"", "utf-8"),
    "bomless utf-16-le": (b"", "utf-16-le"),
    "bomless utf-16-be": (b"", "utf-16-be"),
}


@given(
    crcs=st.dictionaries(
        st.integers(0, 99),
        st.text("0123456789abcdefABCDEF", min_size=8, max_size=8),
        min_size=1,
        max_size=20,
    ),
    backend=st.sampled_from(sorted(_BUILDERS)),
    encoding=st.sampled_from(sorted(_ENCODINGS)),
    crlf=st.booleans(),
)
def test_every_backend_s_crcs_survive_every_encoding_it_can_arrive_in(
    crcs: dict[int, str], backend: str, encoding: str, crlf: bool
) -> None:
    """The cross-backend extractor, end to end from bytes: whichever ripper wrote
    the log and however it was encoded (EAC writes UTF-16 with CRLF), the same
    per-track CRCs come out — so a parity verdict never depends on the encoding."""
    text = _BUILDERS[backend](crcs)
    if crlf:
        text = text.replace("\n", "\r\n")
    prefix, codec = _ENCODINGS[encoding]
    raw = prefix + text.encode(codec)
    assert track_copy_crcs(decode_log_bytes(raw)) == {
        n: crc.upper() for n, crc in crcs.items()
    }
