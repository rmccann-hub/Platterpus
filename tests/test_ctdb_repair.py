"""CTDB repair, end to end on synthetic discs: restored byte for byte, or refused.

No copyrighted audio (CLAUDE.md rule 8): every disc is ``random.Random`` PCM made
here. The entry's parity record comes from the TEST-ONLY reference encoder in
``tests/test_ctdb_localise.py`` (a direct power sum per column, written from the
definition, not the module's Horner recurrence). Damage is XORed into our copy
at known samples, the real verify locates it, and the repair must give back the
clean audio exactly, at offsets 0, +667 and -1500.

**What the stand-in does that the real thing does not** (CLAUDE.md): the files
here are raw PCM with a ``.flac`` name, the "decoder" reads them back and the
"encoder" writes the PCM it is given, so FLAC's own codec is not exercised in
this file. ``tests/test_flac_rewrite.py`` runs the real ``flac`` and
``metaflac`` where they are installed, and says so when they are not. The
commit (links, renames, rollback) is real: it runs on ``tmp_path``.
"""

from __future__ import annotations

import dataclasses
import os
import random
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from test_ctdb_localise import _Client, _encode, _inject, _shifted

from platterpus.accuraterip_crc import accuraterip_crcs
from platterpus.adapters.ctdb_client import CtdbEntry
from platterpus.adapters.flac_rewrite import CD_SHAPE, FlacRewriter
from platterpus.ctdb import crc as crc_mod
from platterpus.ctdb.repair_commit import backup_path, candidate_path
from platterpus.ctdb.repair_run import repair_verified_rip
from platterpus.ctdb.repair_types import RepairRecord, RepairStatus
from platterpus.ctdb.sweep import sweep
from platterpus.ctdb.verify import CtdbVerifyResult, Verdict, verify_rip
from platterpus.rip_report import REPORT_SCHEMA_VERSION, _ctdb

_SECTORS = (40, 40, 40)
_FRAMES = sum(_SECTORS) * 588
_STARTS = [0, 40 * 588, 80 * 588]


class _FakeRewriter(FlacRewriter):
    """Writes the PCM it is given; ``mangle`` lets a test make the encoder lie."""

    def __init__(self, mangle: Callable[[bytes], bytes] | None = None) -> None:
        super().__init__(flac="/fake/flac", metaflac="/fake/metaflac")
        self.mangle = mangle
        self.copy_problem: str | None = None

    def stream_shape(self, path: Path) -> tuple[int, int, int] | str:
        return CD_SHAPE

    def encode(self, pcm: bytes, dest: Path) -> str | None:
        assert not dest.exists()
        self.encoder_argv = ("flac", "-8", "-o", str(dest), "-")
        dest.write_bytes(self.mangle(pcm) if self.mangle else pcm)
        return None

    def copy_metadata(self, source: Path, dest: Path) -> str | None:
        return self.copy_problem


def _errors() -> dict[int, int]:
    """A few lone samples in tracks 1 and 2, and a 40-word burst near one second.

    All inside the entry's window at every offset tested: at +667 the window
    starts at frame 6,547, and a sample before it is in a guard band neither the
    parity nor the CRC covers (``test_damage_in_a_guard_band_is_beyond_ctdb``).
    """
    rng = random.Random(42)
    words = {2 * 7000: 0x0101, 2 * 20000 + 1: 0x8000, 2 * 30000: 0x00FF}
    for k in range(40):
        words[2 * 44100 + k] = rng.randint(1, 0xFFFF)
    return words


def _track_crcs(pcm: bytes) -> tuple[int, ...]:
    """The entry's per-track CTDB CRCs, measured over its own audio at offset 0."""
    measured = sweep([pcm], _STARTS, _FRAMES, disc_range=0, track_range=0)
    return tuple(t[0] for t in measured.tracks)


def _entry(theirs: bytes, npar: int = 16, confidence: int = 1416) -> CtdbEntry:
    record = _encode(theirs, npar)
    column0 = tuple(
        int.from_bytes(record[i * 23520 : i * 23520 + 2], "little") for i in range(npar)
    )
    return CtdbEntry(
        crc=crc_mod.ctdb_crc(theirs, 0),
        confidence=confidence,
        track_crcs=_track_crcs(theirs),
        npar=npar,
        has_parity=True,
        entry_id="32115",
        parity_url="http://p.cuetools.net/32115",
        syndrome=column0,
        stride=5880,
    )


class _Disc:
    """A rip on disk (tmp_path), its clean audio, and the verify of it."""

    def __init__(
        self,
        tmp: Path,
        seed: int,
        errors: dict[int, int],
        offset: int = 0,
        npar: int = 16,
    ) -> None:
        self.clean = random.Random(seed).randbytes(4 * _FRAMES)
        ours = _inject(self.clean, errors)
        theirs = _shifted(self.clean, offset)
        strong = _entry(theirs, npar)
        weak = CtdbEntry(crc=crc_mod.ctdb_crc(ours, 0), confidence=1, entry_id="weak")
        self.client = _Client((strong, weak), {"32115": _encode(theirs, npar)})
        self.paths = [tmp / f"{n:02d}.flac" for n in (1, 2, 3)]
        edges = [*_STARTS, _FRAMES]
        for i, path in enumerate(self.paths):
            path.write_bytes(ours[4 * edges[i] : 4 * edges[i + 1]])
        self.result = verify_rip(
            self.paths,
            self.client,
            decoder=lambda p: Path(p).read_bytes(),
            samples_probe=lambda p: Path(p).stat().st_size // 4,
        )

    def clean_track(self, number: int) -> bytes:
        edges = [*_STARTS, _FRAMES]
        return self.clean[4 * edges[number - 1] : 4 * edges[number]]

    def repair(
        self,
        result: CtdbVerifyResult | None = None,
        rewriter: FlacRewriter | None = None,
        **kwargs: object,
    ) -> RepairRecord:
        repaired = repair_verified_rip(
            self.paths,
            result or self.result,
            samples_probe=lambda p: Path(p).stat().st_size // 4,
            decoder=lambda p: Path(p).read_bytes(),
            rewriter=rewriter or _FakeRewriter(),
            **kwargs,
        )
        assert repaired.repair is not None
        return repaired.repair

    def snapshot(self) -> dict[str, bytes]:
        folder = self.paths[0].parent
        return {p.name: p.read_bytes() for p in sorted(folder.iterdir())}


# --- restored byte for byte -------------------------------------------------------


@pytest.mark.parametrize("offset", [0, 667, -1500])
def test_a_damaged_rip_is_restored_byte_for_byte(tmp_path: Path, offset: int) -> None:
    errors = _errors()
    disc = _Disc(tmp_path, 1, errors, offset)
    damaged = {p.name: p.read_bytes() for p in disc.paths}
    record = disc.repair()
    assert record.status is RepairStatus.REPAIRED, record.reason
    assert record.offset == offset and record.cuetools_offset == -offset
    assert sorted(w.disc_word for w in record.words) == sorted(errors)
    for number, path in enumerate(disc.paths, start=1):
        assert path.read_bytes() == disc.clean_track(number)
    assert [t.track for t in record.tracks] == [1, 2]  # track 3 was never damaged
    for row in record.tracks:
        kept = Path(row.original_kept_as)
        assert kept == backup_path(Path(row.path))
        assert kept.read_bytes() == damaged[Path(row.path).name]
        assert row.ctdb_crc_after == row.ctdb_crc_expected
        witness = accuraterip_crcs(disc.clean_track(row.track), row.track, 3)
        assert witness is not None
        assert (row.accuraterip_v1_after, row.accuraterip_v2_after) == (
            witness.v1,
            witness.v2,
        )
        assert row.accuraterip_v2_before != row.accuraterip_v2_after
    assert record.disc_crc_after == record.disc_crc_expected
    assert record.disc_crc_before is not None
    assert record.disc_crc_before != record.disc_crc_after
    assert not any(candidate_path(p).exists() for p in disc.paths)
    assert not backup_path(disc.paths[2]).exists()


def test_an_npar_8_entry_repairs_four_errors_in_one_column(tmp_path: Path) -> None:
    column = 2 * 5880 + 321
    four = {column + r * 11760: 0x0F0F + r for r in range(4)}
    disc = _Disc(tmp_path, 2, four, npar=8)
    record = disc.repair()
    assert record.status is RepairStatus.REPAIRED, record.reason
    assert [p.read_bytes() for p in disc.paths] == [
        disc.clean_track(n) for n in (1, 2, 3)
    ]


# --- refused, and nothing on disk changed ----------------------------------------


def test_a_file_changed_since_the_localisation_is_refused(tmp_path: Path) -> None:
    disc = _Disc(tmp_path, 3, _errors())
    data = bytearray(disc.paths[0].read_bytes())
    data[400] ^= 1  # not one of the corrections: a different edit
    disc.paths[0].write_bytes(bytes(data))
    before = disc.snapshot()
    record = disc.repair()
    assert record.status is RepairStatus.REFUSED
    assert "has changed since" in record.reason
    assert disc.snapshot() == before


def test_an_untouched_track_changed_since_is_caught_by_the_proof(
    tmp_path: Path,
) -> None:
    disc = _Disc(tmp_path, 4, _errors())
    data = bytearray(disc.paths[2].read_bytes())
    data[4000] ^= 1
    disc.paths[2].write_bytes(bytes(data))
    before = disc.snapshot()
    record = disc.repair()
    assert record.status is RepairStatus.REFUSED and "track 3" in record.reason
    assert disc.snapshot() == before


def _with_strong(result: CtdbVerifyResult, **changes: object) -> CtdbVerifyResult:
    entries = tuple(
        dataclasses.replace(e, **changes) if e.entry_id == "32115" else e
        for e in result.entries
    )
    return dataclasses.replace(result, entries=entries)


def test_a_crc_that_does_not_close_replaces_nothing(tmp_path: Path) -> None:
    disc = _Disc(tmp_path, 5, _errors())
    before = disc.snapshot()
    strong = next(e for e in disc.result.entries if e.entry_id == "32115")
    wrong_track = (strong.track_crcs[0], strong.track_crcs[1] ^ 1, strong.track_crcs[2])
    record = disc.repair(_with_strong(disc.result, track_crcs=wrong_track))
    assert record.status is RepairStatus.REFUSED
    assert "repaired track 2's CTDB CRC" in record.reason
    assert disc.snapshot() == before
    assert strong.crc is not None
    record = disc.repair(_with_strong(disc.result, crc=strong.crc ^ 1))
    assert record.status is RepairStatus.REFUSED
    assert "repaired disc's CTDB CRC" in record.reason
    assert disc.snapshot() == before


def test_a_minority_entry_is_never_repaired_toward(tmp_path: Path) -> None:
    disc = _Disc(tmp_path, 6, _errors())
    stronger = CtdbEntry(crc=0x0BADF00D, confidence=5000, entry_id="no-parity")
    result = dataclasses.replace(disc.result, entries=(*disc.result.entries, stronger))
    before = disc.snapshot()
    record = disc.repair(result)
    assert record.status is RepairStatus.REFUSED
    assert "weaker entry is never made" in record.reason
    assert disc.snapshot() == before


def test_accuraterip_verifying_a_track_stops_the_repair(tmp_path: Path) -> None:
    disc = _Disc(tmp_path, 7, _errors())
    before = disc.snapshot()
    record = disc.repair(accuraterip_verified={1: None, 2: True})
    assert record.status is RepairStatus.REFUSED
    assert "AccurateRip verified track 2" in record.reason
    assert disc.snapshot() == before


def test_an_encoder_that_lies_is_caught_before_the_commit(tmp_path: Path) -> None:
    disc = _Disc(tmp_path, 8, _errors())
    before = disc.snapshot()

    def flip_last(pcm: bytes) -> bytes:
        return pcm[:-1] + bytes([pcm[-1] ^ 1])

    record = disc.repair(rewriter=_FakeRewriter(mangle=flip_last))
    assert record.status is RepairStatus.FAILED
    assert "does not decode to the corrected audio" in record.reason
    assert disc.snapshot() == before  # the candidate was removed too


def test_a_metadata_copy_failure_replaces_nothing(tmp_path: Path) -> None:
    disc = _Disc(tmp_path, 9, _errors())
    before = disc.snapshot()
    writer = _FakeRewriter()
    writer.copy_problem = "metaflac could not copy the metadata: exit 1"
    record = disc.repair(rewriter=writer)
    assert record.status is RepairStatus.FAILED and "metaflac" in record.reason
    assert disc.snapshot() == before


def test_an_earlier_repairs_original_is_never_overwritten(tmp_path: Path) -> None:
    disc = _Disc(tmp_path, 10, _errors())
    backup_path(disc.paths[1]).write_bytes(b"an earlier original")
    before = disc.snapshot()
    record = disc.repair()
    assert record.status is RepairStatus.REFUSED
    assert "already there from an earlier repair" in record.reason
    assert disc.snapshot() == before


def test_a_disk_error_is_a_failure_never_an_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disc = _Disc(tmp_path, 17, _errors())
    before = disc.snapshot()

    class _ReadOnly(_FakeRewriter):
        def encode(self, pcm: bytes, dest: Path) -> str | None:
            raise PermissionError(13, "Permission denied", str(dest))

    record = disc.repair(rewriter=_ReadOnly())
    assert record.status is RepairStatus.FAILED and "Permission denied" in record.reason
    assert disc.snapshot() == before


def test_without_hard_links_the_original_is_copied_and_compared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disc = _Disc(tmp_path, 11, _errors())
    damaged = disc.paths[0].read_bytes()

    def no_links(src: object, dst: object) -> None:
        raise OSError("Operation not permitted (exFAT)")

    monkeypatch.setattr(os, "link", no_links)
    record = disc.repair()
    assert record.status is RepairStatus.REPAIRED, record.reason
    assert backup_path(disc.paths[0]).read_bytes() == damaged
    assert disc.paths[0].read_bytes() == disc.clean_track(1)


def test_a_rename_that_fails_part_way_puts_everything_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disc = _Disc(tmp_path, 12, _errors())
    real_replace = os.replace
    calls: list[str] = []

    def second_fails(src: str | Path, dst: str | Path) -> None:
        calls.append(str(dst))
        if len(calls) == 2:
            raise OSError("No space left on device")
        real_replace(src, dst)

    before = disc.snapshot()
    monkeypatch.setattr(os, "replace", second_fails)
    record = disc.repair()
    assert record.status is RepairStatus.FAILED and "No space left" in record.reason
    assert disc.snapshot() == before


def test_damage_in_a_guard_band_is_beyond_ctdb(tmp_path: Path) -> None:
    """Frame 6,000 sits before the window at +667: CTDB cannot see it, so the
    repair fixes what the parity covers and leaves that sample as it was, and the
    record says the guard bands are outside what a repair checks."""
    errors = {2 * 6000: 0x0101, 2 * 30000: 0x00FF}
    disc = _Disc(tmp_path, 15, errors, 667)
    record = disc.repair()
    assert record.status is RepairStatus.REPAIRED, record.reason
    assert [w.disc_word for w in record.words] == [60000]
    assert disc.paths[1].read_bytes() == disc.clean_track(2)
    assert disc.paths[0].read_bytes() != disc.clean_track(1)
    assert any("guard band" in u for u in record.untouched)


def test_a_rip_that_needs_no_repair_says_so(tmp_path: Path) -> None:
    disc = _Disc(tmp_path, 13, {})
    record = disc.repair()
    assert record.status is RepairStatus.REFUSED
    assert "already matches the strongest" in record.reason


# --- the report carries it ---------------------------------------------------------


def test_the_report_carries_the_repair(tmp_path: Path) -> None:
    disc = _Disc(tmp_path, 14, _errors())
    repaired = repair_verified_rip(
        disc.paths,
        disc.result,
        samples_probe=lambda p: Path(p).stat().st_size // 4,
        decoder=lambda p: Path(p).read_bytes(),
        rewriter=_FakeRewriter(),
    )
    assert REPORT_SCHEMA_VERSION == 46
    block = _ctdb(repaired)
    assert block is not None
    repair = block["repair"]
    assert repair["status"] == "repaired" and repair["reason"] is None
    assert repair["entry_id"] == "32115" and repair["confidence"] == 1416
    assert repair["offset"] == 0 and repair["cuetools_offset"] == 0
    assert repair["disc_crc_after"] == repair["disc_crc_expected"]
    assert repair["words_elided"] == 0 and len(repair["words"]) == 43
    first = repair["words"][0]
    assert first == {
        "track": 1,
        "frame": 7000,
        "channel": 0,
        "disc_word": 14000,
        "value": "0101",
    }
    rows = repair["tracks"]
    assert [r["track"] for r in rows] == [1, 2]
    assert rows[0]["original_kept_as"].endswith("01.flac.before-ctdb-repair")
    assert rows[0]["ctdb_crc_after"] == rows[0]["ctdb_crc_expected"]
    # The thin caller passes each track's CTDB CRC at offset 0 from the verify
    # (TASKS R133), so at an offset-0 entry the record names it: the track's own
    # CRC as the verify measured it, before the repair, which is not the entry's.
    measured = disc.result.tracks[0].our_crc
    assert isinstance(measured, int)
    assert rows[0]["ctdb_crc_before"] == f"{measured:08X}"
    assert rows[0]["ctdb_crc_before"] != rows[0]["ctdb_crc_expected"]
    assert len(rows[0]["accuraterip_v2_after"]) == 8
    assert repair["encoder_argv"][0] == "flac"
    assert any("KDD-24" in u for u in repair["untouched"])
    assert _ctdb(disc.result)["repair"] is None


def test_the_report_counts_words_it_does_not_list() -> None:
    from platterpus.ctdb.repair_types import SampleFix

    many = tuple(SampleFix(1, k, 0, 2 * k, 1) for k in range(1005))
    result = CtdbVerifyResult(
        Verdict.NO_MATCH, repair=RepairRecord(RepairStatus.REFUSED, "x", words=many)
    )
    block = _ctdb(result)
    assert block is not None
    assert len(block["repair"]["words"]) == 1000
    assert block["repair"]["words_elided"] == 5


# --- the real codec, where installed ----------------------------------------------

_REAL = shutil.which("flac") is not None and shutil.which("metaflac") is not None


@pytest.mark.skipif(not _REAL, reason="flac and metaflac are not on PATH")
def test_a_real_flac_rip_is_repaired_with_its_tags_kept(tmp_path: Path) -> None:
    """The whole chain with the real tools: encode the damaged tracks as FLAC,
    verify with metaflac's lengths and flac's decode, repair, decode again."""
    from platterpus.ctdb import decode

    disc = _Disc(tmp_path, 16, _errors(), -1500)
    writer = FlacRewriter()
    for path in disc.paths:
        raw = path.read_bytes()
        path.unlink()
        assert writer.encode(raw, path) is None
        subprocess.run(
            ["metaflac", f"--set-tag=TITLE={path.stem}", str(path)], check=True
        )
    result = verify_rip(disc.paths, disc.client)
    repaired = repair_verified_rip(disc.paths, result)
    record = repaired.repair
    assert record is not None and record.status is RepairStatus.REPAIRED, record
    for number, path in enumerate(disc.paths, start=1):
        assert decode.decode_flac_to_pcm(path) == disc.clean_track(number)
        tags = subprocess.run(
            ["metaflac", "--export-tags-to=-", str(path)],
            capture_output=True,
            check=True,
        ).stdout
        assert f"TITLE={path.stem}".encode() in tags
    again = verify_rip(disc.paths, disc.client)
    assert again.verdict is Verdict.MATCH and again.confidence == 1416
