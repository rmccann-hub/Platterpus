"""Tests for the off-thread derived-file verify worker.

Uses real files on disk (so the rglob pairing is exercised) but an injected PCM
hasher so no ffmpeg is invoked.
"""

from __future__ import annotations

import threading
from pathlib import Path

from platterpus.adapters.derived_verify import DerivedVerifyResult
from platterpus.workers.derived_verify_worker import verify_rip_dir


def _make_album(tmp_path: Path, exts: dict[str, list[str]]) -> Path:
    """Create <album>/NN.flac masters and their derived siblings.

    ``exts`` maps a derived extension (e.g. "mp3") to the list of stems that
    should get that sibling. Every stem always gets a .flac master.
    """
    album = tmp_path / "Artist" / "Album"
    album.mkdir(parents=True)
    stems = {s for names in exts.values() for s in names} | {"01", "02"}
    for stem in sorted(stems):
        (album / f"{stem}.flac").write_bytes(b"flac")
    for ext, names in exts.items():
        for stem in names:
            (album / f"{stem}.{ext}").write_bytes(b"derived")
    return album


def test_worker_pairs_derived_with_masters_and_verifies(tmp_path: Path) -> None:
    album = _make_album(tmp_path, {"wv": ["01", "02"]})

    # Fake hasher: derived .wv and its .flac master hash identically → bit-perfect.
    def hasher(path: Path) -> str:
        return "SAME"  # every file "decodes" to the same PCM

    result = verify_rip_dir(album, "wavpack", hasher=hasher)
    assert isinstance(result, DerivedVerifyResult)
    assert result.ok is True
    assert result.checked == 2 and result.expected == 2
    assert result.lossless is True


def test_worker_flags_incomplete_transcode(tmp_path: Path) -> None:
    # Two masters but only one .mp3 was produced → incomplete.
    album = _make_album(tmp_path, {"mp3": ["01"]})

    result = verify_rip_dir(album, "mp3", hasher=lambda p: "pcm")
    assert result.checked == 1 and result.expected == 2
    assert result.complete is False
    assert result.ok is False


def test_worker_no_derived_files_is_error(tmp_path: Path) -> None:
    album = _make_album(tmp_path, {})  # masters only, no derived
    result = verify_rip_dir(album, "mp3", hasher=lambda p: "pcm")
    assert result.ran is False
    assert "no mp3 files" in result.error


def test_worker_unsupported_format_is_error(tmp_path: Path) -> None:
    album = _make_album(tmp_path, {})
    result = verify_rip_dir(album, "flac", hasher=lambda p: "pcm")
    assert result.ran is False
    assert "flac" in result.error


def test_worker_joins_wait_for_before_reading(tmp_path: Path) -> None:
    """The verify must join the transcode thread first so it never reads a
    derived file mid-write."""
    album = _make_album(tmp_path, {"mp3": ["01", "02"]})
    joined = threading.Event()

    def slow_transcode() -> None:
        joined.set()

    t = threading.Thread(target=slow_transcode)
    t.start()
    result = verify_rip_dir(album, "mp3", wait_for=t, hasher=lambda p: "pcm")
    assert joined.is_set()  # the wait_for thread ran to completion first
    assert result.checked == 2


def test_worker_never_raises_on_hasher_crash(tmp_path: Path) -> None:
    album = _make_album(tmp_path, {"wav": ["01", "02"]})

    def boom(path: Path) -> str:
        raise RuntimeError("ffmpeg died")

    result = verify_rip_dir(album, "wav", hasher=boom)
    assert isinstance(result, DerivedVerifyResult)
    assert result.ok is False


def test_worker_wraps_unexpected_verify_crash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Belt-and-braces: if the pure verifier itself somehow raised, the worker
    catches it and returns an error result (never lets it reach the GUI)."""
    import platterpus.workers.derived_verify_worker as mod

    album = _make_album(tmp_path, {"mp3": ["01", "02"]})

    def boom(*a, **k):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(mod, "verify_derived_files", boom)
    result = verify_rip_dir(album, "mp3", hasher=lambda p: "x")
    assert result.ran is False
    assert "unexpected error" in result.error
