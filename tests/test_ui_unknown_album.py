"""Tests for platterpus.ui.unknown_album."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication, QDialogButtonBox

from platterpus.adapters.metaflac import MetaflacAdapter, MetaflacError
from platterpus.adapters.musicbrainz_client import TrackSummary
from platterpus.ui import unknown_album as unknown_module
from platterpus.ui.track_table import AlbumMetadata
from platterpus.ui.unknown_album import (
    UnknownAlbumDialog,
    apply_placeholder_tags,
    apply_track_tags,
    launch_picard_for,
)

# --- UnknownAlbumDialog --------------------------------------------------


def test_dialog_title_and_modality(qapp: QApplication) -> None:
    dialog = UnknownAlbumDialog()
    assert "unknown" in dialog.windowTitle().lower()
    assert dialog.isModal() is True


def test_dialog_initial_picard_state_from_default(
    qapp: QApplication,
) -> None:
    off = UnknownAlbumDialog(auto_launch_picard_default=False)
    on = UnknownAlbumDialog(auto_launch_picard_default=True)
    assert off.auto_launch_picard() is False
    assert on.auto_launch_picard() is True


def test_dialog_picard_toggle_round_trips(qapp: QApplication) -> None:
    dialog = UnknownAlbumDialog(auto_launch_picard_default=False)
    dialog._picard_check.setChecked(True)
    assert dialog.auto_launch_picard() is True


def test_dialog_ok_accepts(qapp: QApplication) -> None:
    dialog = UnknownAlbumDialog()
    button_box = dialog.findChild(QDialogButtonBox)
    button_box.button(QDialogButtonBox.StandardButton.Ok).click()
    assert dialog.result() == int(dialog.DialogCode.Accepted)


def test_dialog_cancel_rejects(qapp: QApplication) -> None:
    dialog = UnknownAlbumDialog()
    button_box = dialog.findChild(QDialogButtonBox)
    button_box.button(QDialogButtonBox.StandardButton.Cancel).click()
    assert dialog.result() == int(dialog.DialogCode.Rejected)


# --- apply_placeholder_tags ----------------------------------------------


class _FakeMetaflac(MetaflacAdapter):
    """Captures write_tags calls."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[Path, dict[str, str]]] = []
        self._fail_for: set[Path] = set()

    def fail_for(self, path: Path) -> None:
        self._fail_for.add(path)

    def write_tags(self, flac_path: Path, tags: dict[str, str]) -> None:
        if flac_path in self._fail_for:
            raise MetaflacError(f"intentional failure for {flac_path}")
        self.calls.append((flac_path, dict(tags)))


def test_apply_placeholder_tags_writes_track_nn(tmp_path: Path) -> None:
    """Realistic filenames on purpose: `NN - Title.flac`, as cyanrip writes them.

    This fixture used to be `track1.flac`, `track2.flac`, … — names no rip ever
    produces. That made the list position and the track number agree by
    construction, which is exactly why the positional-mapping bug looked correct
    here for as long as it existed (docs/testing.md §5.t: a stand-in must not be
    tidier than the real thing).
    """
    metaflac = _FakeMetaflac()
    files = [tmp_path / f"{i:02d} - Track {i:02d}.flac" for i in range(1, 4)]

    apply_placeholder_tags(metaflac, files)

    assert len(metaflac.calls) == 3
    for i, (path, tags) in enumerate(metaflac.calls, start=1):
        number = f"{i:02d}"
        assert path == files[i - 1]
        assert tags == {
            "TITLE": f"Track {number}",
            "ARTIST": "Unknown Artist",
            "ALBUM": "Unknown Album",
            "TRACKNUMBER": number,
        }


def test_apply_placeholder_tags_returns_successes(tmp_path: Path) -> None:
    metaflac = _FakeMetaflac()
    files = [
        tmp_path / "01 - Track 01.flac",
        tmp_path / "02 - Track 02.flac",
        tmp_path / "03 - Track 03.flac",
    ]
    metaflac.fail_for(files[1])  # track 02 will fail

    succeeded = apply_placeholder_tags(metaflac, files)

    assert succeeded == [files[0], files[2]]


def test_apply_placeholder_tags_handles_empty_list() -> None:
    metaflac = _FakeMetaflac()
    succeeded = apply_placeholder_tags(metaflac, [])
    assert succeeded == []
    assert metaflac.calls == []


# --- apply_track_tags (edit-aware) ---------------------------------------


def test_apply_track_tags_writes_edited_values(tmp_path: Path) -> None:
    metaflac = _FakeMetaflac()
    files = [tmp_path / "01.flac", tmp_path / "02.flac"]
    album = AlbumMetadata(artist="Pink Floyd", title="The Wall", year="1979")
    tracks = [
        TrackSummary(number=1, title="In the Flesh?", artist_credit="Pink Floyd"),
        TrackSummary(number=2, title="The Thin Ice", artist_credit=""),
    ]

    apply_track_tags(metaflac, files, album, tracks)

    assert metaflac.calls[0][1] == {
        "TITLE": "In the Flesh?",
        "ARTIST": "Pink Floyd",
        "ALBUM": "The Wall",
        "ALBUMARTIST": "Pink Floyd",
        "TRACKNUMBER": "01",
        "DATE": "1979",
    }
    # Track 2 left its artist blank → falls back to the album artist.
    assert metaflac.calls[1][1]["TITLE"] == "The Thin Ice"
    assert metaflac.calls[1][1]["ARTIST"] == "Pink Floyd"


def test_apply_track_tags_falls_back_to_placeholders(tmp_path: Path) -> None:
    metaflac = _FakeMetaflac()
    files = [tmp_path / "01.flac"]
    # Nothing edited: blank album, no track rows.
    apply_track_tags(metaflac, files, AlbumMetadata(), [])

    assert metaflac.calls[0][1] == {
        "TITLE": "Track 01",
        "ARTIST": "Unknown Artist",
        "ALBUM": "Unknown Album",
        "ALBUMARTIST": "Unknown Artist",
        "TRACKNUMBER": "01",
    }
    # No year typed → no DATE tag at all (rather than an empty one).
    assert "DATE" not in metaflac.calls[0][1]


# --- launch_picard_for ---------------------------------------------------


def test_launch_picard_invokes_flatpak_with_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: list[list[str]] = []

    class _FakePopen:
        def __init__(self, argv: list[str], *a: Any, **kw: Any) -> None:
            captured.append(argv)

    monkeypatch.setattr(unknown_module.subprocess, "Popen", _FakePopen)

    ok = launch_picard_for(tmp_path)

    assert ok is True
    assert captured == [
        [
            "flatpak",
            "run",
            "org.musicbrainz.Picard",
            str(tmp_path),
        ]
    ]


def test_launch_picard_returns_false_when_flatpak_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def boom(*a: Any, **kw: Any) -> Any:
        raise FileNotFoundError("flatpak")

    monkeypatch.setattr(unknown_module.subprocess, "Popen", boom)

    assert launch_picard_for(tmp_path) is False


def test_launch_picard_returns_false_on_other_oserror(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def boom(*a: Any, **kw: Any) -> Any:
        raise PermissionError("no exec")

    monkeypatch.setattr(unknown_module.subprocess, "Popen", boom)

    assert launch_picard_for(tmp_path) is False


def test_launch_picard_detaches_into_a_new_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """BUG-7: Picard is launched detached (start_new_session=True) — consistent
    with the other fire-and-forget launch — so quitting Platterpus doesn't kill
    it and a signal aimed at our process group can't catch it."""
    captured: dict[str, Any] = {}

    class _FakePopen:
        def __init__(self, argv: list[str], **kwargs: Any) -> None:
            captured["argv"] = argv
            captured["kwargs"] = kwargs

    monkeypatch.setattr(unknown_module.subprocess, "Popen", _FakePopen)
    assert launch_picard_for(tmp_path) is True
    assert captured["kwargs"].get("start_new_session") is True


# --- Track-number mapping (audit, 2026-07-29) --------------------------------


def test_tags_follow_the_track_number_not_the_file_position(tmp_path: Path) -> None:
    """Regression: deselecting a track shifted every tag by one.

    The Rip? column lets the user untick tracks, so the files on disk are NOT
    necessarily `01, 02, 03…`. The old code used `enumerate(flac_files, start=1)` as
    the track number, so with track 1 deselected the file `02 - …` was written
    track 1's title and `TRACKNUMBER=01`, `03 - …` got track 2's, and so on —
    **every tag on the archival master silently wrong**, while the UI reported
    success and the log said nothing.

    A wrong TRACKNUMBER is worse than a missing one: nothing downstream can tell it
    from a correct one.
    """
    metaflac = _FakeMetaflac()
    # Track 1 was deselected, so the rip starts at 02.
    files = [tmp_path / "02 - Track 02.flac", tmp_path / "03 - Track 03.flac"]
    album = AlbumMetadata(artist="Some Artist", title="Some Album", year="")
    tracks = [
        TrackSummary(number=1, title="First", artist_credit=""),
        TrackSummary(number=2, title="Second", artist_credit=""),
        TrackSummary(number=3, title="Third", artist_credit=""),
    ]

    apply_track_tags(metaflac, files, album, tracks)

    written = {path.name: tags for path, tags in metaflac.calls}
    assert written["02 - Track 02.flac"]["TRACKNUMBER"] == "02"
    assert written["02 - Track 02.flac"]["TITLE"] == "Second", (
        "the file for track 2 was tagged with another track's title — the "
        "positional mapping is back."
    )
    assert written["03 - Track 03.flac"]["TRACKNUMBER"] == "03"
    assert written["03 - Track 03.flac"]["TITLE"] == "Third"


def test_placeholder_tags_follow_the_track_number_too(tmp_path: Path) -> None:
    """The same bug lived in the no-edits path; fixing one and not the other would
    leave it reachable for every user who never touches the track table."""
    metaflac = _FakeMetaflac()
    files = [tmp_path / "05 - Track 05.flac", tmp_path / "06 - Track 06.flac"]

    apply_placeholder_tags(metaflac, files)

    written = {path.name: tags for path, tags in metaflac.calls}
    assert written["05 - Track 05.flac"]["TRACKNUMBER"] == "05"
    assert written["05 - Track 05.flac"]["TITLE"] == "Track 05"
    assert written["06 - Track 06.flac"]["TRACKNUMBER"] == "06"


def test_a_file_with_no_track_number_is_skipped_and_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Skipping beats guessing.

    If the name carries no number there is nothing to key on, and inventing one
    would write a confidently wrong TRACKNUMBER. The file is left untagged and the
    reason goes to the log, so the outcome is visible rather than silently wrong.
    """
    metaflac = _FakeMetaflac()
    files = [tmp_path / "bonus material.flac", tmp_path / "01 - Track 01.flac"]

    with caplog.at_level("WARNING"):
        succeeded = apply_placeholder_tags(metaflac, files)

    assert [p.name for p in succeeded] == ["01 - Track 01.flac"]
    assert len(metaflac.calls) == 1, "the un-numbered file was tagged anyway"
    assert "does not start with a track number" in " ".join(
        r.getMessage() for r in caplog.records
    ), "skipped silently — the user has an untagged file and no explanation"
