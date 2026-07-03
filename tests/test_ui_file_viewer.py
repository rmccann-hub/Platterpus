"""Tests for the in-app read-only file viewer (IMP-1)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication

from platterpus.ui.dialogs.file_viewer import (
    _MAX_VIEW_BYTES,
    FileViewerDialog,
    read_text_bounded,
)


def test_read_text_bounded_truncates_and_notes(tmp_path: Path) -> None:
    big = tmp_path / "big.log"
    big.write_bytes(b"x" * (_MAX_VIEW_BYTES + 100))
    text = read_text_bounded(big)
    assert "truncated" in text.lower()
    assert len(text) <= _MAX_VIEW_BYTES + 200  # capped, not the whole file


def test_read_text_bounded_never_raises_on_missing(tmp_path: Path) -> None:
    text = read_text_bounded(tmp_path / "nope.log")
    assert "could not open" in text


def test_read_text_bounded_replaces_bad_bytes(tmp_path: Path) -> None:
    f = tmp_path / "x.log"
    f.write_bytes(b"cyanrip \xff\x80 log")  # invalid UTF-8
    # Must not raise; the bad bytes become the replacement char.
    assert "cyanrip" in read_text_bounded(f)


def test_viewer_shows_contents_read_only(qapp: QApplication, tmp_path: Path) -> None:
    f = tmp_path / "Album.log"
    f.write_text("cyanrip log\nTrack 1 ripped successfully!\n", encoding="utf-8")
    dialog = FileViewerDialog(f)
    assert "Track 1 ripped successfully" in dialog._view.toPlainText()
    assert dialog._view.isReadOnly()
    assert dialog.windowTitle() == "Album.log"


def test_viewer_reader_is_injectable(qapp: QApplication, tmp_path: Path) -> None:
    f = tmp_path / "x.log"
    f.write_text("on disk", encoding="utf-8")
    dialog = FileViewerDialog(f, reader=lambda _p: "injected content")
    assert dialog._view.toPlainText() == "injected content"


def test_viewer_open_externally_defers_to_open_url(
    qapp: QApplication, tmp_path: Path
) -> None:
    f = tmp_path / "x.log"
    f.write_text("hi", encoding="utf-8")
    calls: list[QUrl] = []
    dialog = FileViewerDialog(
        f, open_url=lambda url: (calls.append(url), True)[1], reader=lambda _p: ""
    )
    dialog._open_external_button.click()
    assert len(calls) == 1
    assert calls[0].toLocalFile() == str(f)
