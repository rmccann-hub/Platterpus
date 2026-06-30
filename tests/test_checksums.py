"""Tests for platterpus.checksums — the SHA256 integrity manifest."""

from __future__ import annotations

import hashlib
from pathlib import Path

from platterpus import checksums


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_manifest_lists_audio_in_sha256sum_format(tmp_path: Path) -> None:
    _write(tmp_path / "01 - A.flac", b"flac-audio")
    _write(tmp_path / "01 - A.mp3", b"mp3-audio")
    # A non-audio sibling (the log) must NOT be hashed.
    _write(tmp_path / "album.log", b"log text")

    result = checksums.write_manifest(tmp_path)

    assert result.error == ""
    assert result.hashed == 2
    assert result.failed == 0
    assert result.path == tmp_path / "checksums.sha256"

    text = result.path.read_text()
    # Exact `sha256sum -c` line format: "<hex>  <relpath>".
    expected = hashlib.sha256(b"flac-audio").hexdigest()
    assert f"{expected}  01 - A.flac" in text
    assert "album.log" not in text  # non-audio excluded


def test_manifest_uses_relative_posix_paths(tmp_path: Path) -> None:
    _write(tmp_path / "The Police" / "Album" / "01 - Roxanne.flac", b"x")
    result = checksums.write_manifest(tmp_path)
    text = result.path.read_text()
    assert "The Police/Album/01 - Roxanne.flac" in text  # relative, forward slash


def test_manifest_verifies_with_sha256sum_semantics(tmp_path: Path) -> None:
    # The hash we write must equal a straight SHA256 of the bytes, so an external
    # `sha256sum -c` would pass.
    data = b"some audio bytes" * 1000
    _write(tmp_path / "track.flac", data)
    checksums.write_manifest(tmp_path)
    line = (tmp_path / "checksums.sha256").read_text().strip()
    digest, _, name = line.partition("  ")
    assert digest == hashlib.sha256(data).hexdigest()
    assert name == "track.flac"


def test_empty_dir_writes_empty_manifest(tmp_path: Path) -> None:
    result = checksums.write_manifest(tmp_path)
    assert result.error == ""
    assert result.hashed == 0
    assert result.path is not None and result.path.exists()


def test_missing_directory_returns_error_not_raise(tmp_path: Path) -> None:
    result = checksums.write_manifest(tmp_path / "does-not-exist")
    # rglob on a missing dir yields nothing → empty manifest write fails because
    # the parent dir doesn't exist → error set, never raised.
    assert result.error != ""


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    data = b"hello world"
    p = tmp_path / "f.flac"
    p.write_bytes(data)
    assert checksums.sha256_file(p) == hashlib.sha256(data).hexdigest()
