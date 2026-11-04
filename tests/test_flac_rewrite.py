"""The repair's FLAC writer: binary runs, the block parser, and the real tools where present.

The real ``flac`` and ``metaflac`` tests run only where both are on PATH, and
skip with that reason otherwise (CI images may not carry them). They were run on
2026-11-04 against FLAC 1.4.3, outside the repository. No audio is committed
(rule 8): every file is made here from ``random.Random`` PCM and deleted with
``tmp_path``.
"""

from __future__ import annotations

import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.adapters.flac_rewrite import (
    STRUCTURAL_BLOCKS,
    BytesRun,
    FlacRewriter,
    parse_blocks,
    run_bytes,
)
from platterpus.adapters.tool_run import ToolRun


def _block(kind: int, body: bytes, last: bool = False) -> bytes:
    return bytes([kind | (0x80 if last else 0)]) + len(body).to_bytes(3, "big") + body


# --- the block parser ------------------------------------------------------------


def test_blocks_parse_and_the_last_bit_is_ignored() -> None:
    dump = _block(4, b"tags") + _block(6, b"\x00" * 300, last=True)
    assert parse_blocks(dump) == ((4, b"tags"), (6, b"\x00" * 300))
    assert parse_blocks(_block(4, b"tags", last=True)) == parse_blocks(
        _block(4, b"tags")
    )
    assert parse_blocks(b"") == ()
    assert parse_blocks(dump[:-1]) is None
    assert parse_blocks(b"\x04\x00") is None


@settings(max_examples=200, deadline=None)
@given(st.binary(max_size=600))
def test_parse_blocks_never_raises(data: bytes) -> None:
    got = parse_blocks(data)
    assert got is None or sum(4 + len(b) for _k, b in got) == len(data)


# --- binary runs -------------------------------------------------------------------


def test_run_bytes_passes_bytes_both_ways() -> None:
    echo = "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read()[::-1])"
    got = run_bytes(
        [sys.executable, "-c", echo], b"\x00\xff\x01", timeout_s=30, tool="py", code="t"
    )
    assert got.run.ok and got.stdout == b"\x01\xff\x00"
    assert got.run.argv[0] == sys.executable


def test_run_bytes_captures_a_failure_whole() -> None:
    fail = "import sys; sys.stderr.write('bad block\\n'); sys.exit(3)"
    got = run_bytes(
        [sys.executable, "-c", fail], None, timeout_s=30, tool="py", code="t"
    )
    assert got.run.exit_code == 3 and "bad block" in got.run.output
    missing = run_bytes(["/nonexistent/flac"], None, timeout_s=5, tool="flac", code="t")
    assert not missing.run.started and missing.run.exit_code is None
    slow = "import time; time.sleep(5)"
    late = run_bytes(
        [sys.executable, "-c", slow], None, timeout_s=0.2, tool="py", code="t"
    )
    assert late.run.exit_code is None and "timed out" in late.run.error


# --- the rewriter with a fake runner -------------------------------------------------


class _Runner:
    """Plays metaflac: remembers each call, answers dumps from ``dumps`` by path."""

    def __init__(self, dumps: dict[str, bytes], fail: str = "") -> None:
        self.dumps = dumps
        self.fail = fail
        self.calls: list[tuple[list[str], bytes | None]] = []

    def __call__(self, argv: list[str], stdin: bytes | None) -> BytesRun:
        self.calls.append((argv, stdin))
        if self.fail and self.fail in argv:
            return BytesRun(ToolRun.of(1, "metaflac: error"))
        if "--append" in argv and stdin is not None:
            self.dumps[argv[-1]] = stdin
        if "--list" in argv:
            return BytesRun(ToolRun.of(0), self.dumps.get(argv[-1], b""))
        if "--show-sample-rate" in argv:
            return BytesRun(ToolRun.of(0), b"44100\n16\n2\n")
        return BytesRun(ToolRun.of(0))


def test_copy_metadata_dumps_empties_appends_and_compares(tmp_path: Path) -> None:
    src, dest = tmp_path / "a.flac", tmp_path / "b.flac"
    blocks = _block(4, b"vendor+tags") + _block(6, b"picture")
    runner = _Runner({str(src): blocks})
    writer = FlacRewriter(runner, flac="flac", metaflac="metaflac")
    assert writer.copy_metadata(src, dest) is None
    argvs = [argv for argv, _stdin in runner.calls]
    assert argvs[0][1:4] == [
        "--list",
        "--data-format=binary",
        f"--except-block-type={STRUCTURAL_BLOCKS}",
    ]
    assert argvs[1][1:4] == [
        "--remove",
        "--block-type=VORBIS_COMMENT",
        "--dont-use-padding",
    ]
    assert argvs[2][1:3] == ["--append", "--block-number=0"]
    assert runner.calls[2][1] == blocks
    assert writer.stream_shape(src) == (44100, 16, 2)


def test_a_copy_that_does_not_round_trip_is_refused(tmp_path: Path) -> None:
    src, dest = tmp_path / "a.flac", tmp_path / "b.flac"

    class _Lossy(_Runner):
        def __call__(self, argv: list[str], stdin: bytes | None) -> BytesRun:
            if "--append" in argv and stdin is not None:
                # Exit 0, yet only the first block lands: the silent loss the
                # round-trip comparison exists to catch.
                self.dumps[argv[-1]] = _block(4, b"vendor+tags")
                return BytesRun(ToolRun.of(0))
            return super().__call__(argv, stdin)

    runner = _Lossy({str(src): _block(4, b"vendor+tags") + _block(6, b"pic")})
    writer = FlacRewriter(runner, flac="flac", metaflac="metaflac")
    reason = writer.copy_metadata(src, dest)
    assert reason is not None and "differ from the original's" in reason
    failing = FlacRewriter(
        _Runner({str(src): _block(4, b"t")}, fail="--append"), flac="f", metaflac="m"
    )
    assert "could not copy" in (failing.copy_metadata(src, dest) or "")


def test_missing_tools_are_named() -> None:
    writer = FlacRewriter(_Runner({}), flac="", metaflac="")
    writer.flac = None
    writer.metaflac = None
    assert writer.missing() == "flac and metaflac not found on the host"
    assert writer.encode(b"", Path("x")) == "flac not found on the host"


# --- the real tools, where installed ---------------------------------------------

_REAL = shutil.which("flac") is not None and shutil.which("metaflac") is not None
_needs_flac = pytest.mark.skipif(not _REAL, reason="flac and metaflac are not on PATH")


def _png() -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    pixels = zlib.compress(b"\x00\xff\x00\x00")
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", pixels)
        + chunk(b"IEND", b"")
    )


@_needs_flac
def test_a_real_rewrite_keeps_every_block_and_the_audio(tmp_path: Path) -> None:
    import random

    pcm = random.Random(3).randbytes(4 * 588 * 30)
    original, new = tmp_path / "01.flac", tmp_path / ".01.flac.ctdb-repair.flac"
    writer = FlacRewriter()
    assert writer.encode(pcm, original) is None
    picture = tmp_path / "c.png"
    picture.write_bytes(_png())
    subprocess.run(
        [
            "metaflac",
            "--set-tag=TITLE=Repaired",
            "--set-tag=COMMENT=two\nlines",
            f"--import-picture-from={picture}",
            str(original),
        ],
        check=True,
    )
    changed = pcm[:100] + bytes([pcm[100] ^ 0x5A]) + pcm[101:]
    assert writer.encode(changed, new) is None
    assert writer.copy_metadata(original, new) is None
    from platterpus.ctdb.decode import decode_flac_to_pcm

    assert decode_flac_to_pcm(new) == changed
    tags = subprocess.run(
        ["metaflac", "--export-tags-to=-", str(new)], capture_output=True, check=True
    ).stdout
    assert b"TITLE=Repaired" in tags and b"two\nlines" in tags
    assert writer.stream_shape(new) == (44100, 16, 2)
