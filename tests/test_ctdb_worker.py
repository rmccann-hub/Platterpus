# SPDX-License-Identifier: GPL-3.0-only
"""Tests for platterpus.workers.ctdb_worker.verify_rip_dir.

verify_rip_dir is a plain off-thread function (MainWindow runs it on a daemon
thread). Tests call it directly with an injected fake CTDB client + fake
decoder/probe, so nothing touches the network or shells out to flac/metaflac.
"""

from __future__ import annotations

import threading
from pathlib import Path

from platterpus.adapters.ctdb_client import (
    CTDBClient,
    CtdbEntry,
    CtdbLookupResult,
)
from platterpus.ctdb.toc import DiscToc
from platterpus.ctdb.verify import Verdict
from platterpus.workers.ctdb_worker import verify_rip_dir


class _FakeClient(CTDBClient):
    """Returns a canned lookup result; records the TOC it was queried with."""

    def __init__(self, result: CtdbLookupResult) -> None:
        self._result = result
        self.queried_toc: DiscToc | None = None

    def lookup(self, toc: DiscToc) -> CtdbLookupResult:
        self.queried_toc = toc
        return self._result


def _make_flacs(tmp_path: Path, count: int) -> None:
    for i in range(1, count + 1):
        # content is irrelevant; decoder/probe are injected
        (tmp_path / f"{i:02d} - Track.flac").write_bytes(b"")


def test_not_in_database_returns_not_in_db_verdict(tmp_path: Path) -> None:
    _make_flacs(tmp_path, 2)
    client = _FakeClient(CtdbLookupResult())  # empty → not in DB
    result = verify_rip_dir(
        client, tmp_path, samples_probe=lambda _p: 1000, decoder=lambda _p: b"x"
    )

    assert result.verdict is Verdict.NOT_IN_DATABASE
    assert client.queried_toc is not None  # the lookup happened


def test_matching_crc_returns_match(tmp_path: Path) -> None:
    from platterpus.ctdb import crc as crc_mod

    _make_flacs(tmp_path, 2)
    # 17 whole sectors per file: sector-aligned (TOC total == decoded frames) and
    # long enough for the CTDB guard band (a shorter disc has no CRC).
    frames_per_file = 17 * 588  # 9996
    pcm = bytes((i * 5 + 1) & 0xFF for i in range(frames_per_file * 4))
    whole_disc_crc = crc_mod.ctdb_crc_offset0(pcm * 2)  # correct offset-0 CTDB CRC
    client = _FakeClient(
        CtdbLookupResult(entries=(CtdbEntry(crc=whole_disc_crc, confidence=42),))
    )
    result = verify_rip_dir(
        client,
        tmp_path,
        samples_probe=lambda _p: frames_per_file,
        decoder=lambda _p: pcm,
    )

    assert result.verdict is Verdict.MATCH
    assert result.confidence == 42
    assert result.our_crc == whole_disc_crc


def test_nested_flacs_are_not_pulled_into_the_toc(tmp_path: Path) -> None:
    """Regression (#40): the TOC is exactly this disc's tracks, which sit
    directly in the album folder. A FLAC in a nested subfolder (a bonus disc, a
    leftover, or — if rip_dir ever fell back to the music root — a whole other
    album) must NOT be decoded into the TOC, which would corrupt the CRC and
    yield a spurious not-in-database. Only the direct children are verified."""
    _make_flacs(tmp_path, 2)  # 01, 02 directly in the album folder
    nested = tmp_path / "bonus"
    nested.mkdir()
    (nested / "03 - Extra.flac").write_bytes(b"")  # must be ignored

    probed: list[Path] = []

    def recording_probe(path: Path) -> int:
        # samples_probe runs per FLAC to build the TOC — a faithful count of
        # which files entered the TOC.
        probed.append(path)
        return 1000

    client = _FakeClient(CtdbLookupResult())
    verify_rip_dir(
        client, tmp_path, samples_probe=recording_probe, decoder=lambda _p: b"x"
    )

    # Only the two top-level tracks entered the TOC — not the nested one.
    assert sorted(p.name for p in probed) == ["01 - Track.flac", "02 - Track.flac"]


def test_no_flac_files_returns_lookup_error(tmp_path: Path) -> None:
    client = _FakeClient(CtdbLookupResult())
    result = verify_rip_dir(client, tmp_path)  # empty dir

    assert result.verdict is Verdict.LOOKUP_ERROR
    assert "no flac" in result.message.lower()
    assert client.queried_toc is None  # never reached the lookup


def test_waits_for_post_rip_thread_before_decoding(tmp_path: Path) -> None:
    """When a post-rip thread is supplied, verify_rip_dir joins it before
    decoding (so it never reads a FLAC while metaflac is mid-rewrite)."""
    _make_flacs(tmp_path, 1)
    release = threading.Event()
    order: list[str] = []

    def post_rip() -> None:
        release.wait(5)  # block until the test releases us
        order.append("post_rip_done")

    pr = threading.Thread(target=post_rip, daemon=True)
    pr.start()

    def decoder(_p: Path) -> bytes:
        order.append("decode")
        return b"\x00\x00\x00\x00"

    # An in-DB result so the decoder is actually reached.
    client = _FakeClient(CtdbLookupResult(entries=(CtdbEntry(crc=123, confidence=1),)))

    # Run verify on its own thread so it blocks on the join; release the
    # post-rip thread and confirm the decode happened strictly after it.
    run_thread = threading.Thread(
        target=lambda: verify_rip_dir(
            client,
            tmp_path,
            # Long enough that the CTDB guard-band window is non-empty, so the
            # decoder is actually reached (a too-short disc short-circuits before
            # decoding) — this test is about join-ordering, not the CRC value.
            samples_probe=lambda _p: 30000,
            decoder=decoder,
            wait_for=pr,
        ),
        daemon=True,
    )
    run_thread.start()
    release.set()
    run_thread.join(5)

    assert order == ["post_rip_done", "decode"]  # never decode mid-rewrite


# --- a partial rip is not looked up (the 2026-09-28 Full run) ---------------
#
# The worker is where the disc's track count is decided, so the three witnesses
# are pinned here: the log's own footer, the caller's probe count for a log with
# none, and the footer winning when they disagree.


def _cyanrip_log(names: list[str], footer: str | None) -> str:
    """A minimal real-shaped cyanrip log naming ``names``, optionally with the
    fork's ``Rip completed:`` footer (``None`` = a build that prints none)."""
    lines = ["cyanrip 0.9.4-rc2+platterpus.17 (platterpus-fork-ge0471f4)", ""]
    for number, name in enumerate(names, start=1):
        lines += [
            f"Track {number} read successfully!",
            "  EAC CRC32:     A1B2C3D4",
            "  File(s):",
            f"    The Police/Album/{name}",
            "",
        ]
    if footer is not None:
        lines.append(footer)
    return "\n".join(lines) + "\n"


def _album(tmp_path: Path, count: int, footer: str | None) -> Path:
    names = [f"{i:02d} - Track.flac" for i in range(1, count + 1)]
    for name in names:
        (tmp_path / name).write_bytes(b"")  # decoder/probe are injected
    (tmp_path / "Album.log").write_text(_cyanrip_log(names, footer), encoding="utf-8")
    return tmp_path


def test_a_partial_rip_folder_is_not_looked_up(tmp_path: Path) -> None:
    """Two files whose log says `2 of 14`: no TOC, no lookup, a not-run verdict."""
    album = _album(tmp_path, 2, "Rip completed:  yes (2 of 14 tracks)")
    client = _FakeClient(CtdbLookupResult())  # would answer "not in CTDB"
    result = verify_rip_dir(
        client, album, samples_probe=lambda _p: 1000, decoder=lambda _p: b"x"
    )
    assert client.queried_toc is None
    assert result is not None
    assert result.verdict is Verdict.NOT_WHOLE_DISC
    assert "2 of the disc's 14 tracks" in result.message


def test_a_whole_disc_log_still_looks_up_every_track(tmp_path: Path) -> None:
    album = _album(tmp_path, 3, "Rip completed:  yes (3 of 3 tracks)")
    client = _FakeClient(CtdbLookupResult())
    result = verify_rip_dir(
        client, album, samples_probe=lambda _p: 1000, decoder=lambda _p: b"x"
    )
    assert client.queried_toc is not None
    assert client.queried_toc.num_tracks == 3
    assert result is not None and result.verdict is Verdict.NOT_IN_DATABASE


def test_the_probe_count_covers_a_log_without_a_footer(tmp_path: Path) -> None:
    """An upstream build prints no `Rip completed:`; the GUI's probe count
    (cyanrip's own `Disc tracks:`) is then the witness."""
    album = _album(tmp_path, 2, footer=None)
    client = _FakeClient(CtdbLookupResult())
    result = verify_rip_dir(
        client,
        album,
        disc_tracks_hint=14,
        samples_probe=lambda _p: 1000,
        decoder=lambda _p: b"x",
    )
    assert client.queried_toc is None
    assert result is not None and result.verdict is Verdict.NOT_WHOLE_DISC


def test_the_logs_footer_wins_over_the_probe_count(tmp_path: Path) -> None:
    """The footer was written by the rip being verified; a stale probe count from
    an earlier disc must not suppress a whole-disc lookup."""
    album = _album(tmp_path, 2, "Rip completed:  yes (2 of 2 tracks)")
    client = _FakeClient(CtdbLookupResult())
    result = verify_rip_dir(
        client,
        album,
        disc_tracks_hint=14,
        samples_probe=lambda _p: 1000,
        decoder=lambda _p: b"x",
    )
    assert client.queried_toc is not None
    assert client.queried_toc.num_tracks == 2
    assert result is not None and result.verdict is Verdict.NOT_IN_DATABASE


def test_a_passed_rip_log_is_the_witness_not_a_second_parse(tmp_path: Path) -> None:
    """The finish handler hands over its parsed log. The folder here holds a log
    with no footer, so only the passed one can say the rip is partial."""
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    album = _album(tmp_path, 2, footer=None)
    names = [f"{i:02d} - Track.flac" for i in (1, 2)]
    passed = parse_cyanrip_log(
        _cyanrip_log(names, "Rip completed:  yes (2 of 14 tracks)")
    )
    client = _FakeClient(CtdbLookupResult())
    result = verify_rip_dir(
        client,
        album,
        rip_log=passed,
        samples_probe=lambda _p: 1000,
        decoder=lambda _p: b"x",
    )
    assert client.queried_toc is None
    assert result is not None and result.verdict is Verdict.NOT_WHOLE_DISC
