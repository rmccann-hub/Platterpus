"""Tests for platterpus.ui.track_table."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from platterpus.adapters.musicbrainz_client import (
    ReleaseDetail,
    ReleaseSummary,
    TrackSummary,
)
from platterpus.ui.track_table import (
    AlbumMetadata,
    TrackTable,
    TrackTableModel,
    _format_length,
)


def _track(
    number: int = 1,
    title: str = "Track",
    artist: str = "Artist",
    length_ms: int | None = 60_000,
) -> TrackSummary:
    return TrackSummary(
        number=number, title=title, artist_credit=artist, length_ms=length_ms
    )


def _detail() -> ReleaseDetail:
    return ReleaseDetail(
        summary=ReleaseSummary(
            mbid="m",
            title="Dark Side",
            artist_credit="Pink Floyd",
            date="1973",
        ),
        tracks=(
            _track(1, "Speak to Me", "Pink Floyd", 67_000),
            _track(2, "Breathe", "Pink Floyd", 165_000),
        ),
    )


# --- _format_length -------------------------------------------------------


def test_format_length_basic() -> None:
    assert _format_length(67_000) == "1:07"
    assert _format_length(165_000) == "2:45"


def test_format_length_zero() -> None:
    assert _format_length(0) == "0:00"


def test_format_length_none() -> None:
    assert _format_length(None) == ""


def test_format_length_negative_is_empty() -> None:
    assert _format_length(-1) == ""


# --- TrackTableModel ------------------------------------------------------


def test_model_starts_empty(qapp: QApplication) -> None:
    model = TrackTableModel()
    assert model.rowCount() == 0
    assert model.columnCount() == 5  # #, Title, Artist, Length, Status


def test_model_set_tracks_populates_rows(qapp: QApplication) -> None:
    model = TrackTableModel()
    model.set_tracks([_track(1), _track(2)])
    assert model.rowCount() == 2


def test_model_data_displays_track_fields(qapp: QApplication) -> None:
    model = TrackTableModel()
    model.set_tracks([_track(1, "Speak to Me", "Pink Floyd", 67_000)])

    assert model.data(model.index(0, 0)) == "1"
    assert model.data(model.index(0, 1)) == "Speak to Me"
    assert model.data(model.index(0, 2)) == "Pink Floyd"
    assert model.data(model.index(0, 3)) == "1:07"


def test_model_title_and_artist_are_editable(qapp: QApplication) -> None:
    model = TrackTableModel()
    model.set_tracks([_track()])

    title_flags = model.flags(model.index(0, 1))
    artist_flags = model.flags(model.index(0, 2))
    number_flags = model.flags(model.index(0, 0))
    length_flags = model.flags(model.index(0, 3))

    assert title_flags & Qt.ItemFlag.ItemIsEditable
    assert artist_flags & Qt.ItemFlag.ItemIsEditable
    assert not (number_flags & Qt.ItemFlag.ItemIsEditable)
    assert not (length_flags & Qt.ItemFlag.ItemIsEditable)


def test_model_setData_updates_title(qapp: QApplication) -> None:
    model = TrackTableModel()
    model.set_tracks([_track(title="Old")])

    ok = model.setData(model.index(0, 1), "New")

    assert ok is True
    assert model.tracks()[0].title == "New"


def test_model_setData_updates_artist(qapp: QApplication) -> None:
    model = TrackTableModel()
    model.set_tracks([_track(artist="Old")])

    ok = model.setData(model.index(0, 2), "New")

    assert ok is True
    assert model.tracks()[0].artist_credit == "New"


def test_model_setData_refuses_to_edit_number_or_length(
    qapp: QApplication,
) -> None:
    model = TrackTableModel()
    model.set_tracks([_track(number=1)])

    assert model.setData(model.index(0, 0), "99") is False
    assert model.setData(model.index(0, 3), "9:99") is False
    # Underlying data unchanged.
    assert model.tracks()[0].number == 1


def test_model_headers(qapp: QApplication) -> None:
    model = TrackTableModel()
    expected = ["#", "Title", "Artist", "Length", "Status"]
    for i, header in enumerate(expected):
        assert model.headerData(i, Qt.Orientation.Horizontal) == header


def test_status_column_starts_blank_and_advances(qapp: QApplication) -> None:
    from platterpus.ui.track_table import _COL_STATUS

    model = TrackTableModel()
    model.set_tracks([_track(1, "A"), _track(2, "B")])
    # Pending → blank (no clutter before/while another track rips).
    assert model.data(model.index(0, _COL_STATUS)) == ""
    # Ripping / done render symbol + text (not colour alone).
    model.set_track_status(1, "ripping")
    assert model.data(model.index(0, _COL_STATUS)) == "⟳ Ripping"
    model.set_track_status(1, "done")
    assert model.data(model.index(0, _COL_STATUS)) == "✓ Done"
    assert model.data(model.index(1, _COL_STATUS)) == ""  # track 2 untouched


def test_reset_statuses_clears_all(qapp: QApplication) -> None:
    from platterpus.ui.track_table import _COL_STATUS

    model = TrackTableModel()
    model.set_tracks([_track(1, "A"), _track(2, "B")])
    model.set_track_status(1, "done")
    model.set_track_status(2, "ripping")
    model.reset_statuses()
    assert model.data(model.index(0, _COL_STATUS)) == ""
    assert model.data(model.index(1, _COL_STATUS)) == ""


def test_set_track_status_ignores_out_of_range(qapp: QApplication) -> None:
    model = TrackTableModel()
    model.set_tracks([_track(1, "A")])
    model.set_track_status(0, "done")  # no such 1-based track
    model.set_track_status(99, "done")  # beyond the loaded rows
    # No raise, and the one real row stays pending.
    from platterpus.ui.track_table import _COL_STATUS

    assert model.data(model.index(0, _COL_STATUS)) == ""


def test_widget_status_helpers_and_reset(qapp: QApplication) -> None:
    from platterpus.ui.track_table import _COL_STATUS

    widget = TrackTable()
    widget.set_release(_detail())
    widget.mark_track_ripping(1)
    widget.mark_track_done(1)
    widget.mark_track_ripping(2)
    model = widget._model
    assert model.data(model.index(0, _COL_STATUS)) == "✓ Done"
    assert model.data(model.index(1, _COL_STATUS)) == "⟳ Ripping"
    widget.reset_track_status()
    assert model.data(model.index(1, _COL_STATUS)) == ""


def test_set_tracks_resets_status(qapp: QApplication) -> None:
    from platterpus.ui.track_table import _COL_STATUS

    model = TrackTableModel()
    model.set_tracks([_track(1, "A")])
    model.set_track_status(1, "done")
    # Loading a new track list clears leftover status.
    model.set_tracks([_track(1, "X"), _track(2, "Y")])
    assert model.data(model.index(0, _COL_STATUS)) == ""


# --- TrackTable widget ----------------------------------------------------


def test_default_state_is_empty(qapp: QApplication) -> None:
    widget = TrackTable()
    assert widget.album_metadata() == AlbumMetadata()
    assert widget.tracks() == []
    # The track view has an accessible name (a11y, principle #10).
    assert widget._view.accessibleName() == "Track list"


def test_album_fields_have_accessible_names(qapp: QApplication) -> None:
    # The QFormLayout labels beside these line edits are cosmetic, not
    # programmatic buddies, so without explicit accessible names a screen
    # reader announces three anonymous text boxes (a11y, principle #10).
    widget = TrackTable()
    assert widget._album_artist_edit.accessibleName() == "Album artist"
    assert widget._album_title_edit.accessibleName() == "Album title"
    assert widget._album_year_edit.accessibleName() == "Album year"


def test_set_release_populates_album_and_tracks(qapp: QApplication) -> None:
    widget = TrackTable()
    widget.set_release(_detail())

    meta = widget.album_metadata()
    assert meta.artist == "Pink Floyd"
    assert meta.title == "Dark Side"
    assert meta.year == "1973"
    assert len(widget.tracks()) == 2
    assert widget.tracks()[0].title == "Speak to Me"


def test_set_placeholder_tracks_creates_numbered_rows(
    qapp: QApplication,
) -> None:
    widget = TrackTable()
    widget.set_placeholder_tracks(16)

    tracks = widget.tracks()
    assert len(tracks) == 16
    assert [t.number for t in tracks] == list(range(1, 17))
    assert tracks[0].title == "Track 01"
    assert tracks[15].title == "Track 16"
    assert all(t.artist_credit == "Unknown Artist" for t in tracks)
    # Album-level fields get the matching placeholders.
    meta = widget.album_metadata()
    assert meta.artist == "Unknown Artist"
    assert meta.title == "Unknown Album"


def test_set_placeholder_tracks_zero_clears_rows_but_sets_album(
    qapp: QApplication,
) -> None:
    widget = TrackTable()
    widget.set_release(_detail())
    widget.set_placeholder_tracks(0)
    assert widget.tracks() == []
    assert widget.album_metadata().artist == "Unknown Artist"


def test_clear_resets_to_empty(qapp: QApplication) -> None:
    widget = TrackTable()
    widget.set_release(_detail())
    widget.clear()

    assert widget.album_metadata() == AlbumMetadata()
    assert widget.tracks() == []


def test_highlight_track_selects_matching_row(qapp: QApplication) -> None:
    widget = TrackTable()
    widget.set_release(_detail())  # 2 tracks

    widget.highlight_track(2)  # 1-based → row index 1

    selected = widget._view.selectionModel().selectedRows()
    assert len(selected) == 1
    assert selected[0].row() == 1


def test_highlight_track_ignores_out_of_range(qapp: QApplication) -> None:
    """A stray 0 (pre-first-track) or a number beyond the loaded rows must
    not raise and must not change the selection."""
    widget = TrackTable()
    widget.set_release(_detail())  # 2 tracks
    widget.highlight_track(1)  # select row 0

    widget.highlight_track(0)  # below range — ignored
    widget.highlight_track(99)  # above range — ignored

    selected = widget._view.selectionModel().selectedRows()
    assert len(selected) == 1
    assert selected[0].row() == 0


def test_user_edit_album_artist_visible_in_metadata(
    qapp: QApplication,
) -> None:
    widget = TrackTable()
    widget.set_release(_detail())
    widget._album_artist_edit.setText("Edited Artist")

    assert widget.album_metadata().artist == "Edited Artist"


def test_user_edit_track_title_visible_in_tracks(qapp: QApplication) -> None:
    widget = TrackTable()
    widget.set_release(_detail())
    widget._model.setData(widget._model.index(0, 1), "Edited Title")

    assert widget.tracks()[0].title == "Edited Title"


# --- validate -------------------------------------------------------------


def test_validate_ok_for_complete_release(qapp: QApplication) -> None:
    widget = TrackTable()
    widget.set_release(_detail())
    ok, message = widget.validate()
    assert ok is True
    assert message == ""


def test_validate_rejects_blank_artist(qapp: QApplication) -> None:
    widget = TrackTable()
    widget.set_release(_detail())
    widget._album_artist_edit.setText("   ")
    ok, message = widget.validate()
    assert ok is False
    assert "artist" in message.lower()


def test_validate_rejects_blank_title(qapp: QApplication) -> None:
    widget = TrackTable()
    widget.set_release(_detail())
    widget._album_title_edit.setText("")
    ok, message = widget.validate()
    assert ok is False
    assert "title" in message.lower()


def test_validate_rejects_no_tracks(qapp: QApplication) -> None:
    widget = TrackTable()
    widget._album_artist_edit.setText("A")
    widget._album_title_edit.setText("T")
    ok, message = widget.validate()
    assert ok is False
    assert "tracks" in message.lower()


def test_validate_rejects_blank_track_title(qapp: QApplication) -> None:
    widget = TrackTable()
    widget.set_release(_detail())
    widget._model.setData(widget._model.index(0, 1), "")
    ok, message = widget.validate()
    assert ok is False
    assert "track 1" in message.lower() or "track" in message.lower()


def test_album_artist_propagates_to_track_rows(qapp) -> None:
    from platterpus.ui.track_table import TrackTable

    table = TrackTable()
    table.set_placeholder_tracks(3)
    # Simulate the user typing an album artist and tabbing away.
    table._album_artist_edit.setText("Pink Floyd")
    table._propagate_album_artist()

    artists = [t.artist_credit for t in table.tracks()]
    assert artists == ["Pink Floyd", "Pink Floyd", "Pink Floyd"]


def test_per_track_artist_edit_holds_after_propagation(qapp) -> None:
    from platterpus.ui.track_table import _COL_ARTIST, TrackTable

    table = TrackTable()
    table.set_placeholder_tracks(2)
    table._album_artist_edit.setText("Various")
    table._propagate_album_artist()
    # Edit track 2's artist individually via the model.
    idx = table._model.index(1, _COL_ARTIST)
    table._model.setData(idx, "Soloist")
    artists = [t.artist_credit for t in table.tracks()]
    assert artists == ["Various", "Soloist"]


# --- Status column is text-only (per-track progress bar removed 2026-07-22) ---


def test_status_column_is_text_only_no_progress_bar(qapp: QApplication) -> None:
    """The Status column shows plain text and carries no per-track progress bar.

    The bar was removed because it duplicated the current-task bar in the
    progress pane (same percent, two places). Guard against it coming back:
    the column has no custom delegate, the removed API is gone, and the status
    stays textual across ripping → done.
    """
    from platterpus.ui import track_table
    from platterpus.ui.track_table import _COL_STATUS, TrackTable

    # The removed progress-bar machinery must not reappear.
    assert not hasattr(track_table, "PROGRESS_ROLE")
    assert not hasattr(track_table, "TrackStatusDelegate")

    widget = TrackTable()
    # No column-specific delegate installed on the Status column (returns None) →
    # the view's default text painting is used, not a progress-bar delegate.
    assert widget._view.itemDelegateForColumn(_COL_STATUS) is None
    assert not hasattr(widget, "on_rip_progress")
    assert not hasattr(widget._model, "set_current_progress")

    widget._model.set_tracks([_track(1, "A"), _track(2, "B")])
    widget.mark_track_ripping(1)
    assert widget._model.data(widget._model.index(0, _COL_STATUS)) == "⟳ Ripping"
    widget.mark_track_done(1)
    assert widget._model.data(widget._model.index(0, _COL_STATUS)) == "✓ Done"
    assert widget._model.data(widget._model.index(1, _COL_STATUS)) == ""
