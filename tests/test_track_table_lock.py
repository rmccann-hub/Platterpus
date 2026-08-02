"""The track list must stay scrollable while a rip is running.

`_set_rip_lock` used `setEnabled(False)` to stop the user editing the track
list mid-rip. A disabled `QTableView` also ignores the wheel and the arrow
keys, so the list could not be scrolled for the whole rip — and that list is
what carries the live per-track status, i.e. the most interesting widget on
screen at exactly that moment (user report, 2026-08-02).

Read-only achieves the actual goal. These tests pin both halves: still
reachable, still not editable.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QApplication

from platterpus.adapters.musicbrainz_client import TrackSummary
from platterpus.ui.track_table import TrackTable, TrackTableModel


def _model(count: int = 14) -> TrackTableModel:
    model = TrackTableModel()
    model.set_tracks(
        [
            TrackSummary(number=n, title=f"Track {n}", artist_credit="A")
            for n in range(1, count + 1)
        ]
    )
    return model


def _table(qapp: QApplication) -> TrackTable:
    return TrackTable()


def test_a_locked_table_is_still_enabled_so_it_still_scrolls(qapp) -> None:
    """The bug, directly: a disabled view cannot be scrolled by wheel or key."""
    table = _table(qapp)
    table.set_locked(True)
    assert table.isEnabled(), "disabling the widget is what broke scrolling"
    assert table._view.isEnabled()
    assert table._view.verticalScrollBar().isEnabled()


def test_a_locked_table_refuses_edits() -> None:
    """The goal the disabling was reaching for, kept."""
    from platterpus.ui.track_table import _COL_TITLE

    model = _model(1)
    editable = model.flags(model.index(0, _COL_TITLE))
    assert editable & Qt.ItemFlag.ItemIsEditable

    model.set_locked(True)
    locked = model.flags(model.index(0, _COL_TITLE))
    assert not (locked & Qt.ItemFlag.ItemIsEditable)


def test_a_locked_table_refuses_the_rip_checkbox() -> None:
    """Un-ticking a track mid-rip would silently disagree with the running
    cyanrip `-l`, so the checkbox has to go read-only too."""
    from platterpus.ui.track_table import _COL_RIP

    model = _model(1)
    assert model.flags(model.index(0, _COL_RIP)) & Qt.ItemFlag.ItemIsUserCheckable

    model.set_locked(True)
    assert not (model.flags(model.index(0, _COL_RIP)) & Qt.ItemFlag.ItemIsUserCheckable)


def test_a_locked_row_is_still_selectable_and_readable(qapp) -> None:
    """Read-only is not invisible: the user must still be able to click a row
    and read every cell while the rip runs."""
    from platterpus.ui.track_table import _COL_TITLE

    model = TrackTableModel()
    model.set_tracks([TrackSummary(number=1, title="Roxanne", artist_credit="A")])
    model.set_locked(True)
    index = model.index(0, _COL_TITLE)
    assert model.flags(index) & Qt.ItemFlag.ItemIsEnabled
    assert model.flags(index) & Qt.ItemFlag.ItemIsSelectable
    assert model.data(index, Qt.ItemDataRole.DisplayRole) == "Roxanne"


def test_unlocking_restores_editing(qapp) -> None:
    """The lock has to lift, or the table is dead after the first rip."""
    table = _table(qapp)
    table.set_locked(True)
    table.set_locked(False)
    assert table._view.editTriggers() != QAbstractItemView.EditTrigger.NoEditTriggers
