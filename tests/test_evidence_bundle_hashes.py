"""S8: a SHA-256 for every member of an evidence bundle, from the sender.

The cyanrip fork's round 32 lap 9 S8 (their data register's X7): the bundle's
``MANIFEST.txt`` gave each member's size and no hash, so a filing could be checked
only against the archive as it reached them — a member changed by an exporter,
or in transit before the archive was hashed, was invisible. These tests hold the
new block to the bytes a receiver actually extracts, and to the format of the tool
they will check it with (``sha256sum``), run for real.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

from platterpus import evidence_bundle
from platterpus.bundle_integrity import SHA256_HEADING, sha256sum_line
from platterpus.evidence_bundle import BundleResult, build_bundle, sha256_of


def _read_from(archive: Path, name: str) -> str:
    with tarfile.open(archive, "r:gz") as tar:
        handle = tar.extractfile(name)
        assert handle is not None, f"{name} is in the listing but has no content"
        return handle.read().decode("utf-8", errors="replace")


def _hash_rows(manifest: str) -> dict[str, str]:
    """``name -> hex`` for every plain ``sha256sum``-format line in the manifest."""
    rows: dict[str, str] = {}
    for line in manifest.splitlines():
        match = re.match(r"^([0-9a-f]{64})  (.+)$", line)
        if match:
            rows[match.group(2)] = match.group(1)
    return rows


def _hashing_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BundleResult:
    """A bundle with an ordinary member, a BOUNDED one and an in-app one.

    The three routes a member can arrive by, because a hash computed on one route
    and forgotten on another is the shape this guards against. The cap is shrunk
    so the bounded case costs kilobytes rather than 16 MiB.
    """
    monkeypatch.setattr(evidence_bundle, "MAX_FILE_BYTES", 1_000)
    monkeypatch.setattr(evidence_bundle, "_KEEP_HEAD_BYTES", 300)
    monkeypatch.setattr(evidence_bundle, "_KEEP_TAIL_BYTES", 300)
    album = tmp_path / "album"
    album.mkdir()
    (album / "rip.log").write_text("ripper log\n")
    (album / "big.log").write_text("x" * 5_000 + "\nthe fatal line\n")
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "log.txt").write_text("app log line\n")
    return build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20261014T000000Z",
        app_version="0.7.104",
        outcome="success",
        album_dir=album,
        log_dir=logs,
        extra_text={"DIAGNOSTICS.txt": "generated in memory\n"},
    )


def test_every_included_member_has_a_hash_of_the_bytes_a_receiver_extracts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each hash is recomputed from the EXTRACTED member and must agree.

    Compared against the archive, not against ``BundleEntry.sha256``: two values
    computed by the same code agreeing says nothing (``CLAUDE.md``: two
    implementations agreeing is not either one being correct). The bounded file is
    the case that separates "hash of what was written" from "hash of the file on
    disk", so it is required to be present, not merely tolerated.
    """
    result = _hashing_bundle(tmp_path, monkeypatch)
    assert result.path is not None, result.error
    rows = _hash_rows(_read_from(result.path, "MANIFEST.txt"))
    included = {e.name for e in result.included}
    # FLOOR: three routes, so "every row agreed" cannot be satisfied by no rows.
    assert {"album/rip.log", "album/big.log", "DIAGNOSTICS.txt"} <= included
    assert set(rows) == included, (
        f"hash rows {sorted(rows)} do not cover the included members "
        f"{sorted(included)} one-for-one"
    )
    assert "MANIFEST.txt" not in rows, "a file cannot carry its own hash"
    with tarfile.open(result.path, "r:gz") as tar:
        for name, digest in rows.items():
            handle = tar.extractfile(name)
            assert handle is not None
            assert hashlib.sha256(handle.read()).hexdigest() == digest, name
    # The bounded member's hash is NOT the source file's: the archive holds the
    # head, a marker and the tail, and that is what was hashed.
    assert rows["album/big.log"] != sha256_of(tmp_path / "album" / "big.log")


def test_the_hash_block_checks_with_the_real_sha256sum(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The promise in the manifest's own words: extract, then ``sha256sum -c``.

    Run with the real tool, because a format "compatible with sha256sum" that was
    never fed to sha256sum is a description of the behaviour, not the behaviour.
    The grep is the one the manifest prints, read out of the manifest.
    """
    tool = shutil.which("sha256sum")
    grep = shutil.which("grep")
    if tool is None or grep is None:
        pytest.skip("sha256sum/grep not installed; the Python check above still ran")
    result = _hashing_bundle(tmp_path, monkeypatch)
    assert result.path is not None, result.error
    out = tmp_path / "extracted"
    with tarfile.open(result.path, "r:gz") as tar:
        tar.extractall(out, filter="data")
    manifest = (out / "MANIFEST.txt").read_text(encoding="utf-8")
    # The pattern the manifest tells a receiver to use, taken from the manifest.
    printed = re.search(r"grep -E '([^']+)' MANIFEST\.txt", manifest)
    assert printed is not None, "the manifest no longer says how to check it"
    selected = subprocess.run(
        [grep, "-E", printed.group(1), "MANIFEST.txt"],
        cwd=out,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout
    checked = subprocess.run(
        [tool, "-c", "--strict", "-"],
        input=selected,
        cwd=out,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr
    # FLOOR: it checked every member, not an empty list.
    assert checked.stdout.count(": OK") == len(result.included), checked.stdout


def test_a_name_is_written_exactly_as_sha256sum_writes_it(tmp_path: Path) -> None:
    """A backslash or newline in a name: our line equals the tool's own line.

    Expected values are the coreutils escape rule written out, so this half runs
    on any machine; the tool's own output is compared too where it is installed.
    """
    digest = "0" * 64
    expected = {
        "back\\slash.log": f"\\{digest}  back\\\\slash.log",
        "new\nline.log": f"\\{digest}  new\\nline.log",
        "plain name.log": f"{digest}  plain name.log",
    }
    for name, line in expected.items():
        assert sha256sum_line(digest, name) == line, name
    tool = shutil.which("sha256sum")
    if tool is None:
        return  # the written-out rule above still ran
    compared = 0
    for name in expected:
        (tmp_path / name).write_bytes(b"content\n")
        theirs = subprocess.run(
            [tool, name],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout.rstrip("\n")
        assert sha256sum_line(sha256_of(tmp_path / name), name) == theirs, name
        compared += 1
    assert compared == len(expected)


def test_the_old_rows_keep_their_shape_so_an_older_reader_still_reads_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The hash block is NEW; the INCLUDED rows above it did not change.

    Backward compatibility stated as a check: an INCLUDED row is still
    ``  <name> <size> B`` with nothing appended, and the hash block comes after
    the NOT INCLUDED block, so a reader that stops at the old blocks reads the old
    manifest.
    """
    result = _hashing_bundle(tmp_path, monkeypatch)
    assert result.path is not None, result.error
    manifest = _read_from(result.path, "MANIFEST.txt")
    row = next(
        line for line in manifest.splitlines() if line.startswith("  album/rip.log")
    )
    assert re.fullmatch(r"  album/rip\.log\s+\d+ B", row), row
    assert manifest.index("NOT INCLUDED") < manifest.index(SHA256_HEADING)
