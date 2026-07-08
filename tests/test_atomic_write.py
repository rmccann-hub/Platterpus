"""Tests for platterpus.atomic_write — durable, atomic file writes."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from platterpus import atomic_write


def test_atomic_write_bytes_writes_content_and_leaves_no_temp(tmp_path: Path) -> None:
    target = tmp_path / "f.bin"
    atomic_write.atomic_write_bytes(target, b"hello")
    assert target.read_bytes() == b"hello"
    assert not (tmp_path / "f.bin.tmp").exists()  # temp renamed away, not left


def test_atomic_write_text_overwrites_existing(tmp_path: Path) -> None:
    target = tmp_path / "f.txt"
    target.write_text("old", encoding="utf-8")
    atomic_write.atomic_write_text(target, "new")
    assert target.read_text(encoding="utf-8") == "new"


def test_atomic_write_fsyncs_file_and_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Durability is the whole point (the reason this module exists): the data
    # file AND the parent directory must be fsync'd, or a power loss can lose the
    # data or the rename. Prove both fsyncs happen.
    real_fsync = os.fsync
    seen: list[int] = []

    def spy(fd: int) -> None:
        seen.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", spy)
    atomic_write.atomic_write_text(tmp_path / "f.txt", "data")
    assert len(seen) >= 2  # the temp file fd + the parent-directory fd


def test_fsync_dir_swallows_unsupported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Some filesystems can't fsync a directory fd; that must weaken durability,
    # not crash the write. _fsync_dir must never raise.
    def boom(_fd: int) -> None:
        raise OSError("directory fsync unsupported here")

    monkeypatch.setattr(os, "fsync", boom)
    atomic_write._fsync_dir(tmp_path)  # must not raise
