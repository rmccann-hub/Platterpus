"""Locating where a rip differs from a CTDB entry, end to end (TASKS R43).

No copyrighted audio (CLAUDE.md rule 8): each disc is random PCM made here. The
entry's parity record is computed by a TEST-ONLY encoder written from the
definition (a direct power sum per column, not the module's Horner recurrence),
errors are injected into our copy at known samples, and the verify must name
exactly those samples, in EAC's words, on every surface that shows per-track CTDB.

What only hardware can settle is said in TASKS R43 and below: whether EAC's own
wav session of the reference disc reads ``differs in 16 samples
@04:04:68,04:05:17,04:11:32`` here. That needs the owner's audio. What this file
pins instead is that our words for a located difference are EAC's words, read
from EAC's committed log of that session.
"""

from __future__ import annotations

import random
import re
from pathlib import Path

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from platterpus.adapters.ctdb_client import (
    CTDBClient,
    CtdbEntry,
    CtdbLookupResult,
    parse_lookup_response,
)
from platterpus.adapters.ctdb_parity import ParityFetch
from platterpus.ctdb import crc as crc_mod
from platterpus.ctdb import gf16, localise
from platterpus.ctdb.diagnose import run_diagnostics
from platterpus.ctdb.differences import (
    CtdbLocalisation,
    EntryLocalisation,
    LocalisationStatus,
    msf,
    track_differences,
)
from platterpus.ctdb.syndromes import STRIDE, record_syndromes
from platterpus.ctdb.toc import SAMPLES_PER_SECTOR, DiscToc
from platterpus.ctdb.track_wording import per_track_lines
from platterpus.ctdb.verify import CtdbVerifyResult, verify_rip
from platterpus.ctdb.verify_parity import corrected_crc
from platterpus.deps.checks import ProbeResult
from platterpus.rip_report import _ctdb

FIXTURES = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[1]

_SECTORS = (40, 40, 40)  # 70,560 frames: 10 parity rows
_FILES = [Path(f"{n:02d}.flac") for n in range(1, len(_SECTORS) + 1)]
_STARTS = [0, 40 * SAMPLES_PER_SECTOR, 80 * SAMPLES_PER_SECTOR]
_FRAMES = sum(_SECTORS) * SAMPLES_PER_SECTOR
_EXP = np.array(gf16.EXP, dtype=np.int64)
_LOG = np.array(gf16.LOG, dtype=np.int64)


def _encode(pcm: bytes, npar: int = 16) -> bytes:
    """TEST-ONLY encoder: the entry's parity record, by the definition."""
    words = np.frombuffer(pcm, dtype="<u2").astype(np.int64)
    rows = len(words) // STRIDE - 2
    block = words[STRIDE : STRIDE + rows * STRIDE].reshape(rows, STRIDE)
    record = np.zeros((npar, STRIDE), dtype=np.int64)
    for i in range(npar):
        for r in range(rows):
            row = block[r]
            power = i * (rows - 1 - r)
            record[i] ^= np.where(row == 0, 0, _EXP[(_LOG[row] + power) % gf16.ORDER])
    return record.astype("<u2").tobytes()


def _split(pcm: bytes) -> dict[Path, bytes]:
    out: dict[Path, bytes] = {}
    edges = [*_STARTS, _FRAMES]
    for index, path in enumerate(_FILES):
        out[path] = pcm[4 * edges[index] : 4 * edges[index + 1]]
    return out


def _inject(pcm: bytes, words: dict[int, int]) -> bytes:
    data = bytearray(pcm)
    for word, flip in words.items():
        value = int.from_bytes(data[2 * word : 2 * word + 2], "little") ^ flip
        data[2 * word : 2 * word + 2] = value.to_bytes(2, "little")
    return bytes(data)


def _shifted(pcm: bytes, offset: int) -> bytes:
    """The entry's pressing ``offset`` frames from ours: its frame f is our f + offset."""
    if offset >= 0:
        return pcm[4 * offset :] + bytes(4 * offset)
    return bytes(-4 * offset) + pcm[: 4 * offset]


class _Client(CTDBClient):
    def __init__(
        self, entries: tuple[CtdbEntry, ...], records: dict[str, bytes]
    ) -> None:
        self._entries = entries
        self._records = records
        self.fetched: list[tuple[str, int]] = []

    def lookup(self, toc: DiscToc) -> CtdbLookupResult:
        return CtdbLookupResult(entries=self._entries)

    def fetch_parity(self, entry: CtdbEntry, rows: int) -> ParityFetch:
        self.fetched.append((entry.entry_id, rows))
        record = self._records.get(entry.entry_id)
        if record is None:
            return ParityFetch(error="no such record")
        return ParityFetch(data=record[: rows * STRIDE * 2], rows=rows)


def _entry(pcm: bytes, record: bytes, confidence: int, entry_id: str) -> CtdbEntry:
    crc = crc_mod.ctdb_crc(pcm, 0)
    assert crc is not None
    column0 = tuple(
        int.from_bytes(record[i * STRIDE * 2 : i * STRIDE * 2 + 2], "little")
        for i in range(16)
    )
    return CtdbEntry(
        crc=crc,
        confidence=confidence,
        npar=16,
        has_parity=True,
        entry_id=entry_id,
        parity_url=f"http://p.cuetools.net/{entry_id}",
        syndrome=column0,
        stride=5880,
    )


def _scenario(
    seed: int, errors: dict[int, int], offset: int = 0
) -> tuple[CtdbVerifyResult, _Client, bytes]:
    """Our rip is the entry's audio, ``offset`` frames along, with ``errors`` XORed in.

    A second, weak entry equals our rip exactly, so our disc MATCHES something
    (outvoted), the case the reference disc's rips are in (TASKS R34).
    """
    clean = random.Random(seed).randbytes(4 * _FRAMES)
    ours = _inject(clean, errors)
    theirs = _shifted(clean, offset)
    strong = _entry(theirs, _encode(theirs), 1416, "32115")
    weak = CtdbEntry(crc=crc_mod.ctdb_crc(ours, 0), confidence=1, entry_id="8456102")
    client = _Client((strong, weak), {"32115": _encode(theirs)})
    pieces = _split(ours)
    result = verify_rip(
        _FILES,
        client,
        decoder=lambda p: pieces[p],
        samples_probe=lambda p: len(pieces[p]) // 4,
    )
    return result, client, ours


def _sixteen_errors() -> dict[int, int]:
    """16 differing samples in track 2 in three places, and 3 in track 3."""
    rng = random.Random(5)
    words: dict[int, int] = {}
    for sector, count in ((3, 6), (4, 5), (30, 5)):  # sectors 3 and 4 coalesce
        base = 2 * (_STARTS[1] + sector * SAMPLES_PER_SECTOR)
        for k in range(count):
            words[base + 37 * k + (k % 2)] = rng.randint(1, 0xFFFF)
    base = 2 * (_STARTS[2] + 10 * SAMPLES_PER_SECTOR)
    for k in range(3):
        words[base + 2 * k] = rng.randint(1, 0xFFFF)
    return words


# --- the end-to-end localisation ------------------------------------------------


@pytest.mark.parametrize("offset", [0, 667, -1500])
def test_the_verify_names_exactly_the_injected_samples(offset: int) -> None:
    errors = _sixteen_errors()
    result, client, _ = _scenario(1, errors, offset)
    located = result.localisation
    assert located is not None and located.status is LocalisationStatus.LOCATED
    entry = located.entries[0]
    assert entry.entry_id == "32115" and entry.offset == offset
    assert entry.words == tuple(sorted(errors))
    assert client.fetched == [("32115", 16)]  # only the entry that outweighs ours
    by_track = {t.track: t.differences for t in result.tracks}
    assert by_track[1] == ()
    assert [d.text for d in by_track[2]] == [
        "differs in 16 samples @00:00:03-00:00:04,00:00:30"
    ]
    assert [d.text for d in by_track[3]] == ["differs in 3 samples @00:00:10"]


def test_the_message_the_pane_and_the_report_carry_the_places() -> None:
    result, _, _ = _scenario(2, _sixteen_errors())
    phrase = "differs in 16 samples @00:00:03-00:00:04,00:00:30 from the 1,416-submission entry"
    assert f"track 2 {phrase}" in result.message
    from platterpus.ui.rip_progress import ctdb_verdict_line

    assert phrase in ctdb_verdict_line(result)
    block = _ctdb(result)
    assert block is not None
    assert block["localisation"]["status"] == "located"
    assert block["localisation"]["entries_tried"][0]["samples_located"] == 19
    row = block["tracks"][1]["differences"][0]
    assert row["samples"] == 16 and row["places"] == ["00:00:03-00:00:04", "00:00:30"]
    assert row["confidence"] == 1416 and row["places_elided"] == 0
    lines = per_track_lines(result.tracks, result.total_confidence)
    assert lines[1].endswith(
        "; (1,416/1,417) differs in 16 samples @00:00:03-00:00:04,00:00:30"
    )


def test_eight_errors_in_one_column_are_the_most_it_locates() -> None:
    rng = random.Random(8)
    start = 2 * 5880  # the window's first word at offset 0
    column = 1234
    eight = {start + r * STRIDE + column: rng.randint(1, 0xFFFF) for r in range(8)}
    result, _, _ = _scenario(3, eight)
    assert result.localisation is not None
    assert result.localisation.entries[0].words == tuple(sorted(eight))
    nine = {start + r * STRIDE + column: rng.randint(1, 0xFFFF) for r in range(9)}
    result, _, _ = _scenario(3, nine)
    assert result.localisation is not None
    assert result.localisation.status is LocalisationStatus.NOT_DETERMINED
    assert "reproduces the entry's CRC" in result.localisation.reason


def test_a_disc_that_matches_the_strongest_entry_needs_no_localisation() -> None:
    clean = random.Random(4).randbytes(4 * _FRAMES)
    strong = _entry(clean, _encode(clean), 1416, "32115")
    client = _Client((strong,), {"32115": _encode(clean)})
    pieces = _split(clean)
    result = verify_rip(
        _FILES,
        client,
        decoder=lambda p: pieces[p],
        samples_probe=lambda p: len(pieces[p]) // 4,
    )
    assert result.localisation is not None
    assert result.localisation.status is LocalisationStatus.NOT_NEEDED
    assert client.fetched == []
    assert "where it differs" not in result.message


# --- every way it can fail says why --------------------------------------------


def test_without_numpy_it_reads_not_determined_and_never_crashes(monkeypatch) -> None:
    monkeypatch.setattr(
        localise,
        "probe_dependency",
        lambda dep: ProbeResult(present=False, version=None, location=None),
    )
    result, client, _ = _scenario(6, _sixteen_errors())
    assert result.localisation is not None
    assert result.localisation.status is LocalisationStatus.NOT_DETERMINED
    assert result.localisation.reason == "numpy is not installed"
    assert client.fetched == []
    block = _ctdb(result)
    assert (
        block is not None
        and block["localisation"]["reason"] == "numpy is not installed"
    )


def _direct(
    entries: tuple[CtdbEntry, ...], client: CTDBClient, pcm: bytes, **kwargs: float
) -> CtdbLocalisation:
    return localise.localise_disc(
        entries,
        {0: crc_mod.ctdb_crc(pcm, 0) or 0},
        [],
        [pcm],
        _FRAMES,
        client,
        **kwargs,
    )


def test_each_failure_is_a_reason() -> None:
    clean = random.Random(7).randbytes(4 * _FRAMES)
    ours = _inject(clean, {2 * 9000: 1})
    record = _encode(clean)
    strong = _entry(clean, record, 50, "1")

    cannot = CtdbLookupResult  # a client that cannot fetch parity at all

    class _NoParity(CTDBClient):
        def lookup(self, toc: DiscToc) -> CtdbLookupResult:
            return cannot()

    assert "does not fetch" in _direct((strong,), _NoParity(), ours).reason
    bad = bytearray(record)
    bad[0] ^= 1
    wrong = _direct((strong,), _Client((strong,), {"1": bytes(bad)}), ours)
    assert "does not match the entry's own syndrome" in wrong.reason
    late = _direct((strong,), _Client((strong,), {"1": record}), ours, budget_s=0.0)
    assert "time bound" in late.reason
    short = _direct((strong,), _Client((strong,), {"1": record}), ours[: 4 * 30000])
    assert "did not reach the end" in short.reason

    def broken() -> object:
        yield ours[:1000]
        raise OSError("flac exited 1")

    failed = localise.localise_disc(
        (strong,), {0: 1}, [], broken(), _FRAMES, _Client((strong,), {"1": record})
    )
    assert failed.reason == "decode error (flac exited 1)"


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.binary(min_size=0, max_size=64), st.integers(min_value=1, max_value=16))
def test_random_parity_never_raises(noise: bytes, rows: int) -> None:
    clean = random.Random(9).randbytes(4 * _FRAMES)
    record = (noise * (1 + rows * STRIDE * 2 // max(1, len(noise))))[
        : rows * STRIDE * 2
    ]
    entry = CtdbEntry(
        crc=1,
        confidence=9,
        npar=rows,
        has_parity=True,
        entry_id="x",
        parity_url="http://p.cuetools.net/x",
        stride=5880,
    )
    found = _direct((entry,), _Client((entry,), {"x": record}), clean)
    assert found.status in (
        LocalisationStatus.LOCATED,
        LocalisationStatus.NOT_DETERMINED,
    )
    assert found.status is LocalisationStatus.NOT_DETERMINED or rows >= 2


# --- the CRC loop and the words ------------------------------------------------


def test_the_corrected_crc_is_the_crc_of_the_corrected_audio() -> None:
    clean = random.Random(10).randbytes(4 * _FRAMES)
    errors = {2 * 6000: 0x1234, 2 * 20000 + 1: 0x8001, 2 * 60000: 0xFFFF}
    ours = _inject(clean, errors)
    start = 2 * 5880
    window = 2 * (_FRAMES - 5880 - 5880)
    want = crc_mod.ctdb_crc(clean, 0)
    got = corrected_crc(
        crc_mod.ctdb_crc(ours, 0) or 0,
        [w - start for w in errors],
        list(errors.values()),
        2 * window,
    )
    assert got == want
    # Bounded: past its deadline the loop gives up rather than run on.
    many = list(range(0, 200, 2))
    assert corrected_crc(0, many, [1] * len(many), 2 * window, deadline=0.0) is None


def _eac_status(track: int) -> str:
    """Track ``track``'s CTDB status line in EAC's committed wav-session log."""
    text = (REPO / "output_reference/EAC_wav/eac_wav_police_classics.log").read_text(
        encoding="utf-16"
    )
    line = re.compile(
        rf"^ {{0,2}}{track} {{1,4}}\| (?P<status>[^\r\n]{{1,300}})$", re.MULTILINE
    )
    match = line.search(text)
    assert match is not None
    return match.group("status")


def test_our_words_for_a_located_difference_are_eacs() -> None:
    """EAC's wav session: track 3 ``Differs in 16 samples @04:04:68,04:05:17,04:11:32``.

    Built from the reference disc's TOC (EAC's own sectors) and 16 differing
    samples in those three sectors; our line must be EAC's, word for word. Whether
    OUR decoder finds those samples in EAC's audio is the hardware-gated half.
    """
    track_sectors = [0, 14487, 28067, 49920, 72570]
    starts = [s * SAMPLES_PER_SECTOR for s in track_sectors]
    words: list[int] = []
    for place, count in (("04:04:68", 6), ("04:05:17", 5), ("04:11:32", 5)):
        minutes, seconds, frames = (int(x) for x in place.split(":"))
        sector = (minutes * 60 + seconds) * 75 + frames
        first = 2 * (starts[2] + sector * SAMPLES_PER_SECTOR)
        words.extend(first + 3 * k for k in range(count))
    track5 = 2 * (starts[4] + ((2 * 60 + 24) * 75 + 59) * SAMPLES_PER_SECTOR)
    words.extend([track5, track5 + 1, track5 + 9])
    located = CtdbLocalisation(
        LocalisationStatus.LOCATED,
        entries=(
            EntryLocalisation(
                "32115", 1341, LocalisationStatus.LOCATED, 0, tuple(sorted(words))
            ),
        ),
    )
    found = track_differences(located, starts, 268707 * SAMPLES_PER_SECTOR)
    assert _eac_status(3).lower().endswith(found[3][0].text)
    assert _eac_status(5).endswith(found[5][0].text)
    assert msf(18368) == "04:04:68"


def test_many_places_are_counted_not_dropped() -> None:
    words = tuple(2 * (k * 10 * SAMPLES_PER_SECTOR) for k in range(1, 16))
    located = CtdbLocalisation(
        LocalisationStatus.LOCATED,
        entries=(EntryLocalisation("1", 5, LocalisationStatus.LOCATED, 0, words),),
    )
    (difference,) = track_differences(located, [0], 10**7)[1]
    assert len(difference.places) == 12 and difference.elided == 3
    assert difference.text.endswith(" and 3 more places")


# --- the real reference-disc record ----------------------------------------------


def test_the_real_record_parses_to_the_lookups_syndrome() -> None:
    """The row heads of the real record behind entry 32115, padded to full rows."""
    heads = [
        bytes.fromhex(line.split()[1])
        for line in (FIXTURES / "ctdb_parity_32115_rowheads.txt")
        .read_text()
        .splitlines()
        if line.strip() and not line.startswith("#")
    ]
    data = b"".join(head + bytes(STRIDE * 2 - len(head)) for head in heads)
    record = record_syndromes(data, 16)
    assert record is not None
    lookup = parse_lookup_response(
        (FIXTURES / "ctdb_lookup_police_classics.xml").read_bytes()
    )
    entry = next(e for e in lookup.entries if e.entry_id == "32115")
    assert tuple(int(v) for v in record[:, 0]) == entry.syndrome


def test_run_diagnostics_prints_the_localisation(tmp_path: Path) -> None:
    errors = _sixteen_errors()
    clean = random.Random(11).randbytes(4 * _FRAMES)
    ours = _inject(clean, errors)
    strong = _entry(clean, _encode(clean), 1416, "32115")
    pieces = _split(ours)
    names = {tmp_path / p.name: pieces[p] for p in _FILES}
    for path in names:
        path.write_bytes(b"")
    lines: list[str] = []
    run_diagnostics(
        tmp_path,
        out=lines.append,
        client=_Client((strong,), {"32115": _encode(clean)}),
        decoder=lambda p: names[Path(p)],
        samples_probe=lambda p: len(names[Path(p)]) // 4,
    )
    text = "\n".join(lines)
    assert "Localisation: located" in text
    assert "entry 32115 (confidence 1,416): located at offset +0, 19 samples" in text
    assert "(1,416/1,416) differs in 16 samples @00:00:03-00:00:04,00:00:30" in text
