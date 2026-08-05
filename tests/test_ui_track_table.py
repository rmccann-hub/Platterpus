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
    _COL_ARTIST,
    _COL_LENGTH,
    _COL_NUMBER,
    _COL_RIP,
    _COL_STATUS,
    _COL_TITLE,
    STATUS_DONE,
    STATUS_RIPPING,
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
    assert model.columnCount() == 6  # Rip?, #, Title, Artist, Length, Status


def test_model_set_tracks_populates_rows(qapp: QApplication) -> None:
    model = TrackTableModel()
    model.set_tracks([_track(1), _track(2)])
    assert model.rowCount() == 2


def test_model_data_displays_track_fields(qapp: QApplication) -> None:
    model = TrackTableModel()
    model.set_tracks([_track(1, "Speak to Me", "Pink Floyd", 67_000)])

    assert model.data(model.index(0, _COL_NUMBER)) == "1"
    assert model.data(model.index(0, _COL_TITLE)) == "Speak to Me"
    assert model.data(model.index(0, _COL_ARTIST)) == "Pink Floyd"
    assert model.data(model.index(0, _COL_LENGTH)) == "1:07"


def test_model_title_and_artist_are_editable(qapp: QApplication) -> None:
    model = TrackTableModel()
    model.set_tracks([_track()])

    title_flags = model.flags(model.index(0, _COL_TITLE))
    artist_flags = model.flags(model.index(0, _COL_ARTIST))
    number_flags = model.flags(model.index(0, _COL_NUMBER))
    length_flags = model.flags(model.index(0, _COL_LENGTH))

    assert title_flags & Qt.ItemFlag.ItemIsEditable
    assert artist_flags & Qt.ItemFlag.ItemIsEditable
    assert not (number_flags & Qt.ItemFlag.ItemIsEditable)
    assert not (length_flags & Qt.ItemFlag.ItemIsEditable)


def test_model_setData_updates_title(qapp: QApplication) -> None:
    model = TrackTableModel()
    model.set_tracks([_track(title="Old")])

    ok = model.setData(model.index(0, _COL_TITLE), "New")

    assert ok is True
    assert model.tracks()[0].title == "New"


def test_model_setData_updates_artist(qapp: QApplication) -> None:
    model = TrackTableModel()
    model.set_tracks([_track(artist="Old")])

    ok = model.setData(model.index(0, _COL_ARTIST), "New")

    assert ok is True
    assert model.tracks()[0].artist_credit == "New"


def test_model_setData_refuses_to_edit_number_or_length(
    qapp: QApplication,
) -> None:
    model = TrackTableModel()
    model.set_tracks([_track(number=1)])

    assert model.setData(model.index(0, _COL_NUMBER), "99") is False
    assert model.setData(model.index(0, _COL_LENGTH), "9:99") is False
    # Underlying data unchanged.
    assert model.tracks()[0].number == 1


def test_model_headers(qapp: QApplication) -> None:
    model = TrackTableModel()
    expected = ["Rip?", "#", "Title", "Artist", "Length", "Status"]
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
    widget._model.setData(widget._model.index(0, _COL_TITLE), "Edited Title")

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
    widget._model.setData(widget._model.index(0, _COL_TITLE), "")
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


# --- Per-track Rip? selection (checkbox column + right-click, 2026-07-23) -----


def _checkstate(model: TrackTableModel, row: int) -> Qt.CheckState:
    return model.data(model.index(row, _COL_RIP), Qt.ItemDataRole.CheckStateRole)


def test_all_tracks_selected_by_default(qapp: QApplication) -> None:
    """Every track ticked on load → the whole-disc case."""
    widget = TrackTable()
    widget.set_release(_detail())
    assert widget.selected_track_numbers() == [1, 2]
    assert widget.all_tracks_selected() is True
    assert _checkstate(widget._model, 0) == Qt.CheckState.Checked
    assert _checkstate(widget._model, 1) == Qt.CheckState.Checked


def test_rip_column_is_user_checkable(qapp: QApplication) -> None:
    model = TrackTableModel()
    model.set_tracks([_track(1)])
    flags = model.flags(model.index(0, _COL_RIP))
    assert flags & Qt.ItemFlag.ItemIsUserCheckable
    # The checkbox cell shows no text beside the box.
    assert model.data(model.index(0, _COL_RIP)) is None


def test_untick_via_setdata_drops_track_from_selection(qapp: QApplication) -> None:
    widget = TrackTable()
    widget.set_release(_detail())
    ok = widget._model.setData(
        widget._model.index(0, _COL_RIP),
        Qt.CheckState.Unchecked,
        Qt.ItemDataRole.CheckStateRole,
    )
    assert ok is True
    assert widget.selected_track_numbers() == [2]
    assert widget.all_tracks_selected() is False
    assert _checkstate(widget._model, 0) == Qt.CheckState.Unchecked


def test_set_only_selected_ticks_just_those(qapp: QApplication) -> None:
    widget = TrackTable()
    widget.set_release(_detail())
    widget._model.set_only_selected([2])
    assert widget.selected_track_numbers() == [2]


def test_set_all_selected_false_then_validate_fails(qapp: QApplication) -> None:
    """Zero tracks ticked → validate() blocks the rip with a clear message."""
    widget = TrackTable()
    widget.set_release(_detail())
    widget._model.set_all_selected(False)
    assert widget.selected_track_numbers() == []
    ok, message = widget.validate()
    assert ok is False
    assert "select" in message.lower() or "rip?" in message.lower()


def test_selection_changed_signal_fires(qapp: QApplication) -> None:
    widget = TrackTable()
    seen: list[tuple[int, int]] = []
    widget.selection_changed.connect(lambda sel, total: seen.append((sel, total)))
    widget.set_release(_detail())  # emits (2, 2)
    widget._model.set_all_selected(False)  # emits (0, 2)
    assert seen[-1] == (0, 2)
    assert (2, 2) in seen


# --- Metadata that becomes a path segment (audit, 2026-07-31) ----------------
#
# The album artist / album title / track title / track artist are not just tags:
# cyanrip substitutes them into the `-D`/`-F` naming schemes, so each becomes one
# folder or file name. "." and ".." are the two segments POSIX reserves for *this*
# and *the parent* directory, and nothing in cyanrip's sanitiser maps them — so an
# album titled ".." wrote the rip ABOVE the output directory. The unknown-album
# path already refused them (`main_window_helpers.safe_path_segment`); the ordinary
# known-disc path, which reaches cyanrip verbatim, did not. This is the visible,
# specific error at the point of entry; the rule itself is asserted against the
# pure `settings_validation.path_segment_issue` in tests/test_settings_validation.


def test_validate_rejects_a_path_reference_album_title(qapp: QApplication) -> None:
    widget = TrackTable()
    widget.set_release(_detail())
    widget._album_title_edit.setText("..")
    ok, message = widget.validate()
    assert ok is False
    assert "Album title" in message
    assert "outside your output directory" in message  # says WHY, not "invalid"


def test_validate_rejects_a_path_reference_album_artist(qapp: QApplication) -> None:
    widget = TrackTable()
    widget.set_release(_detail())
    widget._album_artist_edit.setText(".")
    ok, message = widget.validate()
    assert ok is False
    assert "Album artist" in message


def test_validate_rejects_a_path_reference_track_title(qapp: QApplication) -> None:
    widget = TrackTable()
    widget.set_release(_detail())
    widget._model.setData(widget._model.index(1, _COL_TITLE), "..")
    ok, message = widget.validate()
    assert ok is False
    assert "Track 2" in message


def test_validate_rejects_a_path_reference_track_artist(qapp: QApplication) -> None:
    widget = TrackTable()
    widget.set_release(_detail())
    widget._model.setData(widget._model.index(0, _COL_ARTIST), "..")
    ok, message = widget.validate()
    assert ok is False
    assert "Track 1" in message


def test_validate_rejects_a_control_char_in_a_title(qapp: QApplication) -> None:
    """A NUL would make `subprocess` raise mid-rip; the rest of the C0 range has
    no business in a filename."""
    widget = TrackTable()
    widget.set_release(_detail())
    widget._model.setData(widget._model.index(0, _COL_TITLE), "Speak\x00to Me")
    ok, message = widget.validate()
    assert ok is False
    assert "illegal character" in message


def test_validate_still_accepts_ordinary_dotted_titles(qapp: QApplication) -> None:
    """The guard stays narrow — "..." and a trailing dot are ordinary names on
    the Linux target, and cyanrip owns naming (Critical rule #3)."""
    widget = TrackTable()
    widget.set_release(_detail())
    widget._album_title_edit.setText("...")
    widget._model.setData(widget._model.index(0, _COL_TITLE), "..and Justice for All")
    ok, message = widget.validate()
    assert ok is True, message


def test_validate_accepts_a_blank_track_artist(qapp: QApplication) -> None:
    """An empty artist is legal (the required-field checks own blankness for the
    album fields only) — the path guard must not turn it into an error."""
    widget = TrackTable()
    widget.set_release(_detail())
    widget._model.setData(widget._model.index(0, _COL_ARTIST), "")
    ok, message = widget.validate()
    assert ok is True, message


# --- column widths: stable during a rip, and Title gets the room ------------------
#
# MEASURED, then fixed (2026-08-05, after the maintainer sent two screenshots and
# said "make sure to keep formatting in mind too"). At a 900 px window on the
# 14-track reference disc, with every column but Title/Artist on `ResizeToContents`:
#
#     pending   Rip?=33  #=26  Title=370  Artist=369  Length=52  Status=48
#     ripping   Rip?=33  #=26  Title=360  Artist=360  Length=52  Status=67
#     done      Rip?=33  #=26  Title=367  Artist=367  Length=52  Status=53
#
# Two separate defects in one table:
#
#   * Status is re-measured whenever its data changes, and its data changes on every
#     track transition — so the whole table re-laid-out roughly TWICE PER TRACK, 28
#     times over a disc, sliding the Title text the user is reading.
#   * Title and Artist were both `Stretch`, which splits the remainder evenly, so a
#     column holding "The Police" on every row (~70 px) was handed 369 px while the
#     column holding the long, varied titles got the same.


def _release(tracks: list[TrackSummary]) -> ReleaseDetail:
    return ReleaseDetail(
        summary=ReleaseSummary(
            mbid="mbid-1",
            title="Every Breath You Take: The Classics",
            artist_credit="The Police",
            date="1995",
        ),
        tracks=tuple(tracks),
    )


_POLICE_TRACKS: list[TrackSummary] = [
    TrackSummary(
        number=1, title="Roxanne", artist_credit="The Police", length_ms=193000
    ),
    TrackSummary(
        number=2,
        title="Every Little Thing She Does Is Magic",
        artist_credit="The Police",
        length_ms=261000,
    ),
    TrackSummary(
        number=14,
        title="Message in a Bottle (new classic rock mix)",
        artist_credit="The Police",
        length_ms=295000,
    ),
]


def _widths(table: TrackTable) -> list[int]:
    header = table._view.horizontalHeader()
    return [header.sectionSize(c) for c in range(6)]


def _laid_out(table: TrackTable, width: int, app: QApplication) -> None:
    table.show()
    table.resize(width, 320)
    app.processEvents()


# --- the pure width functions (no Qt geometry involved) --------------------------


def test_status_width_is_derived_from_the_status_table_not_a_copy_of_it() -> None:
    """Add a status string and the column widens on its own.

    The anti-drift property, and the reason `measure` is injected: a hand-written
    list of specimen strings beside `_STATUS_DISPLAY` would be a second copy, and it
    would go stale the first time a status was added — silently, because a too-narrow
    column elides rather than errors.
    """
    from platterpus.ui import track_table as tt

    measure = len  # 1 unit per character: enough to compare, and deterministic
    before = tt.status_column_width(measure, pad=0)
    longest = max(len(s) for s in tt._STATUS_DISPLAY.values())
    assert before >= longest, "the width does not even cover today's widest status"
    with_extra = dict(tt._STATUS_DISPLAY)
    with_extra["invented"] = "x" * (longest + 25)
    original = tt._STATUS_DISPLAY
    try:
        tt._STATUS_DISPLAY = with_extra
        after = tt.status_column_width(measure, pad=0)
    finally:
        tt._STATUS_DISPLAY = original
    assert after == longest + 25, (
        f"a new status string did not widen the column ({before} -> {after}); the "
        "width is not derived from the table the cells render from"
    )


def test_the_number_column_is_sized_for_any_disc_not_this_one() -> None:
    """A 9-track disc and a 14-track disc must render identically.

    Sizing `#` to the disc's own highest track number would change the column width
    between discs for no reason the user can see — the same class of "it never sits
    still" complaint as the Status swing, arriving between rips instead of during one.
    """
    from platterpus.ui import track_table as tt

    widths = tt.fixed_column_widths(len, pad=0)
    assert widths[tt._COL_NUMBER] >= len("99")
    assert widths[tt._COL_LENGTH] >= len("00:00"), (
        "the Length column cannot hold a two-digit-minute track, so a >=10:00 track "
        "would widen it mid-list"
    )


def test_artist_width_is_capped_so_a_compilation_cannot_crowd_title_out() -> None:
    from platterpus.ui import track_table as tt

    long_credits = ["Emerson, Lake & Palmer featuring The London Philharmonic"] * 3
    capped = tt.artist_column_width(len, long_credits, available_px=100, pad=0)
    assert capped <= 100 * tt._ARTIST_MAX_FRACTION + 1, (
        f"the Artist column took {capped} of 100 available px"
    )
    # FLOOR: the cap must not be the only thing being tested — without a ceiling the
    # content width has to be what comes back, or the cap above proves nothing.
    uncapped = tt.artist_column_width(len, long_credits, available_px=0, pad=0)
    assert uncapped == len(long_credits[0]), (
        "with no ceiling known the content width should stand"
    )
    assert uncapped > capped, "the cap did not actually reduce anything"


# --- the widget, at a real size -------------------------------------------------


def test_column_widths_do_not_move_while_a_rip_advances(qapp: QApplication) -> None:
    """THE REGRESSION. Every status transition used to re-lay-out the table."""
    table = TrackTable()
    table.set_release(_release(_POLICE_TRACKS))
    _laid_out(table, 900, qapp)
    before = _widths(table)
    assert sum(before) > 0, "the table was never laid out; this proves nothing"
    for number, status in (
        (1, STATUS_RIPPING),
        (1, STATUS_DONE),
        (2, STATUS_RIPPING),
        (2, STATUS_DONE),
        (14, STATUS_RIPPING),
        (14, STATUS_DONE),
    ):
        table._model.set_track_status(number, status)
        qapp.processEvents()
    assert _widths(table) == before, (
        f"the columns moved during the rip: {before} -> {_widths(table)}. The Title "
        "text slides sideways on every track transition."
    )


def test_title_gets_the_room_not_the_repeated_album_artist(qapp: QApplication) -> None:
    """The reported symptom: Artist held "The Police" on every row and was handed
    the same width as the column with the long, varied titles."""
    table = TrackTable()
    table.set_release(_release(_POLICE_TRACKS))
    _laid_out(table, 900, qapp)
    widths = _widths(table)
    title, artist = widths[_COL_TITLE], widths[_COL_ARTIST]
    assert title > artist * 3, (
        f"Title={title} vs Artist={artist} — a column repeating one short string is "
        "still taking room from the one that needs it"
    )


def test_extra_window_width_goes_to_title(qapp: QApplication) -> None:
    """Only Title stretches, so growing the window must widen Title and nothing
    else. Guards the converse of the fix: pinning every column would have passed the
    stability test above and left the table unable to use a wider window."""
    table = TrackTable()
    table.set_release(_release(_POLICE_TRACKS))
    _laid_out(table, 900, qapp)
    narrow = _widths(table)
    table.resize(1400, 320)
    qapp.processEvents()
    wide = _widths(table)
    assert wide[_COL_TITLE] > narrow[_COL_TITLE] + 400, (
        f"Title did not absorb the extra 500 px: {narrow[_COL_TITLE]} -> "
        f"{wide[_COL_TITLE]}"
    )
    for col in (_COL_RIP, _COL_NUMBER, _COL_ARTIST, _COL_LENGTH, _COL_STATUS):
        assert wide[col] == narrow[col], (
            f"column {col} changed width when the window grew: {narrow} -> {wide}"
        )
