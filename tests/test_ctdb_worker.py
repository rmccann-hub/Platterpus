# SPDX-License-Identifier: GPL-3.0-only
"""Tests for whipper_gui.workers.ctdb_worker.verify_rip_dir.

verify_rip_dir is a plain off-thread function (MainWindow runs it on a daemon
thread). Tests call it directly with an injected fake CTDB client + fake
decoder/probe, so nothing touches the network or shells out to flac/metaflac.
"""

from __future__ import annotations

import threading
import zlib
from pathlib import Path

from whipper_gui.adapters.ctdb_client import (
    CTDBClient,
    CtdbEntry,
    CtdbLookupResult,
)
from whipper_gui.ctdb.toc import DiscToc
from whipper_gui.ctdb.verify import Verdict
from whipper_gui.workers.ctdb_worker import verify_rip_dir


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
    _make_flacs(tmp_path, 2)
    pcm = b"\x01\x02\x03\x04"
    whole_disc_crc = zlib.crc32(pcm * 2) & 0xFFFFFFFF  # two tracks concatenated
    client = _FakeClient(
        CtdbLookupResult(entries=(CtdbEntry(crc=whole_disc_crc, confidence=42),))
    )
    result = verify_rip_dir(
        client, tmp_path, samples_probe=lambda _p: 1000, decoder=lambda _p: pcm
    )

    assert result.verdict is Verdict.MATCH
    assert result.confidence == 42
    assert result.our_crc == whole_disc_crc


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
            samples_probe=lambda _p: 1000,
            decoder=decoder,
            wait_for=pr,
        ),
        daemon=True,
    )
    run_thread.start()
    release.set()
    run_thread.join(5)

    assert order == ["post_rip_done", "decode"]  # never decode mid-rewrite
