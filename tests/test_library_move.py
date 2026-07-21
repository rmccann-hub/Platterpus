"""Tests for platterpus.library_move (auto-move finished rips to the library).

The move runs on a best-effort post-rip daemon thread, so the module's contract
is "never raises — always a MoveResult"; every safety rule the docstring
promises is pinned here with real tmp_path folders.
"""

from __future__ import annotations

from pathlib import Path

from platterpus.library_move import MoveResult, free_destination, move_album_folder


def _album(tmp_path: Path, name: str = "Artist - Album") -> Path:
    folder = tmp_path / "out" / name
    folder.mkdir(parents=True)
    (folder / "01 - Track.flac.txt").write_text("not audio — a stand-in file")
    (folder / "Album.log").write_text("log")
    return folder


def test_moves_folder_with_contents_into_library(tmp_path: Path) -> None:
    album = _album(tmp_path)
    library = tmp_path / "library"

    result = move_album_folder(album, library)

    assert result.ok is True
    assert result.destination == library / "Artist - Album"
    assert not album.exists()  # gone from the workspace…
    assert (result.destination / "Album.log").read_text() == "log"  # …intact


def test_collision_lands_in_a_numbered_sibling_never_overwrites(
    tmp_path: Path,
) -> None:
    library = tmp_path / "library"
    occupied = library / "Artist - Album"
    occupied.mkdir(parents=True)
    (occupied / "keep.txt").write_text("the earlier rip")
    album = _album(tmp_path)

    result = move_album_folder(album, library)

    assert result.ok is True
    assert result.destination == library / "Artist - Album (2)"
    # The earlier rip is untouched.
    assert (occupied / "keep.txt").read_text() == "the earlier rip"


def test_already_in_the_library_is_a_clean_noop(tmp_path: Path) -> None:
    library = tmp_path / "library"
    album = library / "Artist - Album"
    album.mkdir(parents=True)

    result = move_album_folder(album, library)

    assert result.ok is True
    assert result.destination == album
    assert album.is_dir()


def test_missing_source_reports_not_ok(tmp_path: Path) -> None:
    result = move_album_folder(tmp_path / "nope", tmp_path / "library")
    assert result == MoveResult(
        False, None, f"rip folder not found: {tmp_path / 'nope'}"
    )


def test_refuses_library_inside_the_rip_folder(tmp_path: Path) -> None:
    album = _album(tmp_path)
    result = move_album_folder(album, album / "library")
    assert result.ok is False
    assert "into itself" in result.message
    assert album.is_dir()  # nothing moved


def test_refuses_source_equal_to_library(tmp_path: Path) -> None:
    album = _album(tmp_path)
    result = move_album_folder(album, album)
    assert result.ok is False
    assert "same" in result.message


def test_free_destination_exhaustion_reports_not_ok(tmp_path: Path) -> None:
    library = tmp_path / "library"
    (library / "A").mkdir(parents=True)
    for n in range(2, 100):
        (library / f"A ({n})").mkdir()
    assert free_destination(library, "A") is None

    album = tmp_path / "out" / "A"
    album.mkdir(parents=True)
    result = move_album_folder(album, library)
    assert result.ok is False
    assert "no free name" in result.message
