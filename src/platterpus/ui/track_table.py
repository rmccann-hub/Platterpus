"""Editable track table for pre-rip metadata.

Composite widget — album-level fields above a QTableView of per-track
data, backed by a custom QAbstractTableModel. The main window populates
the table from a ReleaseDetail and reads back the user-edited metadata
before kicking off a rip.

Layout:
  Album artist:  [_____________]
  Album title:   [_____________]
  Year:          [____]

  ┌─#─┬─Title──────────────┬─Artist──────────┬─Length─┐
  │ 1 │ Speak to Me        │ Pink Floyd      │  1:07  │
  │ 2 │ Breathe            │ Pink Floyd      │  2:45  │
  ...

Editable columns: Title, Artist. Track number and length are read-only.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import TypeAlias

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
    QPoint,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QHeaderView,
    QLineEdit,
    QMenu,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from platterpus.adapters.musicbrainz_client import ReleaseDetail, TrackSummary
from platterpus.settings_validation import path_segment_issue

# Qt's model/view API types every index/parent argument as this union, so our
# QAbstractTableModel overrides must annotate it the same way or mypy flags an
# LSP (Liskov) violation. Both member types expose the .isValid()/.row()/
# .column() we actually call, so widening the annotation is a pure signature
# match — no behaviour change (Qt still passes a plain QModelIndex at runtime).
# The explicit TypeAlias marker is load-bearing: mypy 2.3 stopped inferring a
# bare ``X | Y`` assignment of these Qt wrapper types as a type alias and
# started rejecting it wherever it was used as an annotation.
_Index: TypeAlias = QModelIndex | QPersistentModelIndex


@dataclass(frozen=True)
class AlbumMetadata:
    """Album-level fields edited above the track table."""

    artist: str = ""
    title: str = ""
    year: str = ""


# Column layout. Defined once so the model + view + tests share it. The leading
# "Rip?" column is a per-track checkbox (which tracks to rip → cyanrip `-l`);
# Status stays LAST.
_COLUMNS: list[str] = ["Rip?", "#", "Title", "Artist", "Length", "Status"]
_COL_RIP: int = 0
_COL_NUMBER: int = 1
_COL_TITLE: int = 2
_COL_ARTIST: int = 3
_COL_LENGTH: int = 4
_COL_STATUS: int = 5
_EDITABLE_COLS: set[int] = {_COL_TITLE, _COL_ARTIST}

# Per-track live rip status, shown in the Status column as it advances. Symbol
# AND text (not colour alone) per docs/ux-design-principles.md #10; pending shows
# nothing so a not-yet-ripping list stays uncluttered.
STATUS_PENDING: str = "pending"
STATUS_RIPPING: str = "ripping"
STATUS_DONE: str = "done"
_STATUS_DISPLAY: dict[str, str] = {
    STATUS_RIPPING: "⟳ Ripping",
    STATUS_DONE: "✓ Done",
}


def _format_length(ms: int | None) -> str:
    """Render a track length in milliseconds as MM:SS."""
    if ms is None or ms < 0:
        return ""
    total_seconds = round(ms / 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:d}:{seconds:02d}"


class TrackTableModel(QAbstractTableModel):
    """QAbstractTableModel backing the track table.

    Holds a list of TrackSummary; allows editing of Title and Artist.
    TrackSummary is frozen, so edits go through dataclasses.replace.
    """

    # Emitted whenever the "Rip?" checkbox selection changes: (selected, total).
    # The main window uses it to reflect "Rip N of M" and block a zero-selection
    # start. Defined at class scope so it's a real Qt signal on the model.
    selection_changed = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tracks: list[TrackSummary] = []
        # Read-only lock, set while a rip is in flight. Blocks editing and the
        # Rip? checkbox WITHOUT disabling the widget — see `flags`.
        self._locked: bool = False
        # Live per-track rip status keyed by 1-based track number; absent = pending.
        self._status: dict[int, str] = {}
        # Which tracks the user wants ripped, keyed by 1-based track number.
        # Every track starts ticked (the common "rip the whole disc" case);
        # unticking a row drops it from the rip (cyanrip `-l`). A number absent
        # from this map is treated as selected (so a freshly-set list is all-on).
        self._selected: dict[int, bool] = {}

    # --- Public surface ---

    def set_tracks(self, tracks: Sequence[TrackSummary]) -> None:
        """Replace the current track list. Resets the view, rip status, and
        selection (every track ticked)."""
        self.beginResetModel()
        self._tracks = list(tracks)
        self._status = {}
        self._selected = {t.number: True for t in self._tracks}
        self.endResetModel()
        self.selection_changed.emit(self.selected_count(), len(self._tracks))

    # --- Rip selection ("Rip?" checkboxes) ---

    def _is_selected(self, track_number: int) -> bool:
        """True if `track_number` is ticked (absent = ticked by default)."""
        return self._selected.get(track_number, True)

    def selected_track_numbers(self) -> list[int]:
        """The 1-based track numbers currently ticked, in track order."""
        return [t.number for t in self._tracks if self._is_selected(t.number)]

    def selected_count(self) -> int:
        """How many tracks are ticked."""
        return sum(1 for t in self._tracks if self._is_selected(t.number))

    def set_all_selected(self, selected: bool) -> None:
        """Tick (or untick) every track at once."""
        if not self._tracks:
            return
        self._selected = {t.number: selected for t in self._tracks}
        self._emit_selection_column_changed()

    def set_only_selected(self, track_numbers: Sequence[int]) -> None:
        """Tick exactly `track_numbers` (a set) and untick the rest.

        Backs the right-click "Rip only these" action: the highlighted rows
        become the whole rip selection.
        """
        if not self._tracks:
            return
        wanted = set(track_numbers)
        self._selected = {t.number: (t.number in wanted) for t in self._tracks}
        self._emit_selection_column_changed()

    def set_selected(self, track_numbers: Sequence[int], selected: bool) -> None:
        """Tick or untick a specific set of tracks, leaving the others as-is."""
        if not self._tracks:
            return
        for n in track_numbers:
            self._selected[n] = selected
        self._emit_selection_column_changed()

    def _emit_selection_column_changed(self) -> None:
        """Repaint the whole Rip? column and announce the new count."""
        if self._tracks:
            top = self.index(0, _COL_RIP)
            bottom = self.index(len(self._tracks) - 1, _COL_RIP)
            self.dataChanged.emit(top, bottom, [Qt.ItemDataRole.CheckStateRole])
        self.selection_changed.emit(self.selected_count(), len(self._tracks))

    def set_track_status(self, track_number: int, status: str) -> None:
        """Set the live rip status for a 1-based `track_number` and refresh its
        Status cell. Out-of-range numbers are ignored (never raises)."""
        row = track_number - 1
        if row < 0 or row >= len(self._tracks):
            return
        self._status[track_number] = status
        cell = self.index(row, _COL_STATUS)
        self.dataChanged.emit(cell, cell, [Qt.ItemDataRole.DisplayRole])

    def reset_statuses(self) -> None:
        """Clear every track's rip status back to pending (called at rip start)."""
        if not self._status:
            return
        self._status = {}
        if self._tracks:
            top = self.index(0, _COL_STATUS)
            bottom = self.index(len(self._tracks) - 1, _COL_STATUS)
            self.dataChanged.emit(top, bottom, [Qt.ItemDataRole.DisplayRole])

    def tracks(self) -> list[TrackSummary]:
        """Return the current track list (with any user edits applied)."""
        return list(self._tracks)

    def set_all_artists(self, artist: str) -> None:
        """Set every track's artist to `artist` (album-artist propagation).

        Overwrites per-track artists in place and refreshes the Artist
        column. Callers invoke this when the album-artist field changes;
        the user can then still edit individual rows afterward.
        """
        if not self._tracks:
            return
        self._tracks = [replace(track, artist_credit=artist) for track in self._tracks]
        top = self.index(0, _COL_ARTIST)
        bottom = self.index(len(self._tracks) - 1, _COL_ARTIST)
        self.dataChanged.emit(top, bottom, [Qt.ItemDataRole.DisplayRole])

    # --- QAbstractTableModel overrides ---

    def rowCount(self, parent: _Index = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._tracks)

    def columnCount(self, parent: _Index = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(_COLUMNS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            return _COLUMNS[section]
        return None

    def data(
        self,
        index: _Index,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if not index.isValid():
            return None
        col = index.column()
        # The Rip? column is a checkbox — its state lives in CheckStateRole, and
        # it shows no text (DisplayRole falls through to None below).
        if col == _COL_RIP and role == Qt.ItemDataRole.CheckStateRole:
            track = self._tracks[index.row()]
            return (
                Qt.CheckState.Checked
                if self._is_selected(track.number)
                else Qt.CheckState.Unchecked
            )
        if role not in (
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.EditRole,
        ):
            return None
        track = self._tracks[index.row()]
        if col == _COL_RIP:
            return None  # checkbox only — no text beside it
        if col == _COL_NUMBER:
            return str(track.number)
        if col == _COL_TITLE:
            return track.title
        if col == _COL_ARTIST:
            return track.artist_credit
        if col == _COL_LENGTH:
            return _format_length(track.length_ms)
        if col == _COL_STATUS:
            return _STATUS_DISPLAY.get(
                self._status.get(track.number, STATUS_PENDING), ""
            )
        return None

    def setData(
        self,
        index: _Index,
        value: object,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if not index.isValid():
            return False
        col = index.column()
        # Toggling the Rip? checkbox (Qt sends CheckStateRole with a CheckState).
        if col == _COL_RIP and role == Qt.ItemDataRole.CheckStateRole:
            track = self._tracks[index.row()]
            self._selected[track.number] = Qt.CheckState(value) == Qt.CheckState.Checked
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            self.selection_changed.emit(self.selected_count(), len(self._tracks))
            return True
        if role != Qt.ItemDataRole.EditRole:
            return False
        if col not in _EDITABLE_COLS:
            return False
        text = str(value) if value is not None else ""
        row = index.row()
        existing = self._tracks[row]
        if col == _COL_TITLE:
            self._tracks[row] = replace(existing, title=text)
        elif col == _COL_ARTIST:
            self._tracks[row] = replace(existing, artist_credit=text)
        self.dataChanged.emit(index, index, [role])
        return True

    def flags(self, index: _Index) -> Qt.ItemFlag:
        base = super().flags(index)
        # A locked model grants no editing and no checkbox — but stays ENABLED
        # and selectable, so the view still scrolls and the user can still read
        # and select rows. Disabling the widget instead is what made the track
        # list unscrollable during a rip, which is precisely when it is the most
        # interesting thing on screen (user report, 2026-08-02).
        if self._locked:
            return base
        col = index.column()
        if col == _COL_RIP:
            # A user-checkable cell — the checkbox toggles the track's rip
            # selection. Still selectable/enabled so keyboard Space toggles it.
            return base | Qt.ItemFlag.ItemIsUserCheckable
        if col in _EDITABLE_COLS:
            return base | Qt.ItemFlag.ItemIsEditable
        return base

    def set_locked(self, locked: bool) -> None:
        """Make every cell read-only (or editable again) without disabling it.

        Emits ``layoutChanged`` so open editors close and the view re-queries
        ``flags``; a plain attribute set would leave a mid-edit cell editable.
        """
        if self._locked == locked:
            return
        self._locked = locked
        self.layoutChanged.emit()


class TrackTable(QWidget):
    """Composite widget: album-level fields + track table."""

    # Re-emitted from the model: (selected, total) whenever the Rip? checkboxes
    # change. The main window connects this to reflect "Rip N of M" on the Start
    # button and to block a start when nothing's ticked.
    selection_changed = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Album-level fields.
        album_form = QFormLayout()
        self._album_artist_edit: QLineEdit = QLineEdit(self)
        self._album_title_edit: QLineEdit = QLineEdit(self)
        self._album_year_edit: QLineEdit = QLineEdit(self)
        # Accessible names so a screen reader announces each field by what it
        # holds — a QFormLayout label is purely visual and is NOT a programmatic
        # buddy, so without these the fields read as anonymous text boxes
        # (ux-design-principles.md #10).
        self._album_artist_edit.setAccessibleName("Album artist")
        self._album_title_edit.setAccessibleName("Album title")
        self._album_year_edit.setAccessibleName("Album year")
        # Explain the album-artist field's dual role: it's the album-level
        # artist AND it fills every track's Artist column (the common
        # single-artist case), but each row stays editable for compilations
        # and featured guests. Without this the "global field that also
        # overwrites a column" behaviour looks inconsistent.
        self._album_artist_edit.setToolTip(
            "Sets the album artist and fills every track's Artist below. "
            "Edit a row to override it (e.g. a compilation or a featured guest)."
        )
        album_form.addRow("Album artist:", self._album_artist_edit)
        album_form.addRow("Album title:", self._album_title_edit)
        album_form.addRow("Year:", self._album_year_edit)
        root.addLayout(album_form)

        # Typing an album artist fills the per-track Artist column with it
        # (then individual rows can still be overridden). editingFinished —
        # not textChanged — so it fires once on focus-out/Enter, not on
        # every keystroke, and programmatic setText() (set_release /
        # set_placeholder_tracks) does NOT trigger it.
        self._album_artist_edit.editingFinished.connect(self._propagate_album_artist)

        # Track table.
        self._model: TrackTableModel = TrackTableModel(self)
        self._view: QTableView = QTableView(self)
        # A small minimum so the vertical splitter in the main window can shrink
        # the track list to give room to other panes (it scrolls). Without it
        # the stacked panels' minimums fill the whole window and the splitter
        # has no slack to redistribute at the default size (0.4.4 resize fix).
        self._view.setMinimumHeight(64)
        self._view.setAccessibleName("Track list")
        self._view.setModel(self._model)
        self._view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._view.verticalHeader().setVisible(False)
        self._view.setAlternatingRowColors(True)
        # The Status column shows plain text ("⟳ Ripping" / "✓ Done"). It used
        # to also paint a per-track progress bar, but that duplicated the current-
        # task bar in the progress pane below — same percent, two places — so it
        # was removed (real-user feedback, 2026-07-22). Live progress lives in the
        # one two-tier bar (overall + current task); the grid just says which
        # track is active.
        # Title + Artist columns stretch; # + Length are content-sized.
        header = self._view.horizontalHeader()
        for col in range(len(_COLUMNS)):
            mode = (
                QHeaderView.ResizeMode.Stretch
                if col in _EDITABLE_COLS
                else QHeaderView.ResizeMode.ResizeToContents
            )
            header.setSectionResizeMode(col, mode)
        # Right-click a row (or several highlighted rows) for quick rip-selection
        # actions — the second half of the "checkbox column + right-click" model.
        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._show_track_menu)
        # Surface the model's selection changes as our own signal so the main
        # window can watch one object (the widget), not the inner model.
        self._model.selection_changed.connect(self.selection_changed)
        root.addWidget(self._view, stretch=1)

    # --- Public surface -----------------------------------------------------

    def set_release(self, detail: ReleaseDetail) -> None:
        """Populate from a MusicBrainz ReleaseDetail."""
        self._album_artist_edit.setText(detail.summary.artist_credit)
        self._album_title_edit.setText(detail.summary.title)
        self._album_year_edit.setText(detail.summary.date)
        self._model.set_tracks(detail.tracks)

    def set_placeholder_tracks(self, count: int) -> None:
        """Pre-fill placeholder metadata for a disc MusicBrainz can't ID.

        Album fields become "Unknown Artist" / "Unknown Album"; each of
        the `count` track rows gets a "Track NN" title and an "Unknown
        Artist" credit. This mirrors the placeholder tags the
        unknown-album rip actually writes (see
        `ui.unknown_album.apply_placeholder_tags`), so the table shows
        the user what will land on disk instead of empty rows.

        Editing these rows doesn't feed the rip yet — that's the P2
        follow-up tracked in TASKS.md.
        """
        self._album_artist_edit.setText("Unknown Artist")
        self._album_title_edit.setText("Unknown Album")
        self._album_year_edit.clear()
        if count <= 0:
            self._model.set_tracks([])
            return
        rows = [
            TrackSummary(
                number=n,
                title=f"Track {n:02d}",
                artist_credit="Unknown Artist",
            )
            for n in range(1, count + 1)
        ]
        self._model.set_tracks(rows)

    def set_locked(self, locked: bool) -> None:
        """Lock the table read-only for the duration of a rip.

        Replaces a ``setEnabled(False)`` that also killed scrolling: a disabled
        QTableView ignores the wheel and the arrow keys, so during a rip the
        user could not look at the very list that was updating (report,
        2026-08-02). Read-only keeps every cell legible, selectable and
        scrollable while refusing edits and Rip? toggles.
        """
        self._model.set_locked(locked)
        self._view.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
            if locked
            else QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )

    def highlight_track(self, track_number: int) -> None:
        """Select and scroll to the row for `track_number` (1-based).

        Called as a rip progresses so the table follows whipper track by
        track instead of staying wherever the user last clicked. The track
        rows are laid out 1..N in order, so row index == track_number - 1.
        Out-of-range numbers (e.g. a stray 0 before the first track, or a
        track beyond the loaded rows) are ignored rather than raising.
        """
        row = track_number - 1
        if row < 0 or row >= self._model.rowCount():
            return
        self._view.selectRow(row)
        self._view.scrollTo(
            self._model.index(row, _COL_NUMBER),
            QAbstractItemView.ScrollHint.EnsureVisible,
        )

    def mark_track_ripping(self, track_number: int) -> None:
        """Show `track_number` (1-based) as the one currently being ripped."""
        self._model.set_track_status(track_number, STATUS_RIPPING)

    def mark_track_done(self, track_number: int) -> None:
        """Show `track_number` (1-based) as finished ripping."""
        self._model.set_track_status(track_number, STATUS_DONE)

    def reset_track_status(self) -> None:
        """Clear the live Status column back to pending (called at rip start)."""
        self._model.reset_statuses()

    def clear(self) -> None:
        """Reset to the empty state (no album metadata, no tracks)."""
        self._album_artist_edit.clear()
        self._album_title_edit.clear()
        self._album_year_edit.clear()
        self._model.set_tracks([])

    def _propagate_album_artist(self) -> None:
        """Push the album-artist field into every track row's Artist cell."""
        self._model.set_all_artists(self._album_artist_edit.text())

    def album_metadata(self) -> AlbumMetadata:
        """Return the user's current album-level edits."""
        return AlbumMetadata(
            artist=self._album_artist_edit.text(),
            title=self._album_title_edit.text(),
            year=self._album_year_edit.text(),
        )

    def tracks(self) -> list[TrackSummary]:
        """Return the user's current track edits."""
        return self._model.tracks()

    def selected_track_numbers(self) -> list[int]:
        """The 1-based track numbers the user ticked in the Rip? column.

        The main window passes this to the rip as ``only_tracks``. When every
        track is ticked it returns them all; the caller treats "all ticked" as
        "rip the whole disc" (empty ``-l``).
        """
        return self._model.selected_track_numbers()

    def all_tracks_selected(self) -> bool:
        """True when every track is ticked (the whole-disc case)."""
        return self._model.selected_count() == len(self._model.tracks())

    def _highlighted_track_numbers(self) -> list[int]:
        """1-based track numbers of the rows the user has highlighted (selected
        in the view), for the right-click actions. Row index == number - 1."""
        rows = {idx.row() for idx in self._view.selectionModel().selectedRows()}
        tracks = self._model.tracks()
        return [tracks[r].number for r in sorted(rows) if 0 <= r < len(tracks)]

    def _show_track_menu(self, pos: QPoint) -> None:
        """Right-click menu: quick rip-selection actions on the highlighted rows.

        These just set the Rip? checkboxes (the single source of truth for what
        Start rips) — nothing rips immediately. "Rip only these" is the headline:
        tick just the highlighted rows and untick the rest.
        """
        if not self._model.tracks():
            return
        highlighted = self._highlighted_track_numbers()
        menu = QMenu(self._view)
        if highlighted:
            only = menu.addAction("Rip only these")
            only.triggered.connect(lambda: self._model.set_only_selected(highlighted))
            inc = menu.addAction("Include these in the rip")
            inc.triggered.connect(lambda: self._model.set_selected(highlighted, True))
            exc = menu.addAction("Exclude these from the rip")
            exc.triggered.connect(lambda: self._model.set_selected(highlighted, False))
            menu.addSeparator()
        all_on = menu.addAction("Select all")
        all_on.triggered.connect(lambda: self._model.set_all_selected(True))
        all_off = menu.addAction("Select none")
        all_off.triggered.connect(lambda: self._model.set_all_selected(False))
        menu.exec(self._view.viewport().mapToGlobal(pos))

    def validate(self) -> tuple[bool, str]:
        """Validate that nothing required is blank and at least one track is
        selected.

        Returns (True, "") when everything's filled in; (False, message)
        with the first failure when not. The main window uses this
        before kicking off a rip.

        These fields are not just tags — cyanrip substitutes them into the rip's
        folder and file names (``-D "{album_artist}/{album}"``,
        ``-F "{track} - {title}"``), so they are also *path* input and get the
        path-segment check every other path input gets. The rule already existed
        for the unknown-album path (``main_window_helpers.safe_path_segment``
        refuses ``.``/``..``) but had never been applied to the ordinary
        known-disc path, where the values reach cyanrip verbatim — the same
        one-place-only fix as the ``%Y`` traversal (audit, 2026-07-31). The check
        itself lives in ``settings_validation.path_segment_issue`` so it is
        asserted against a pure function, not through this widget.
        """
        if not self._album_artist_edit.text().strip():
            return False, "Album artist is required."
        if not self._album_title_edit.text().strip():
            return False, "Album title is required."
        problem = path_segment_issue("Album artist", self._album_artist_edit.text())
        if problem:
            return False, problem
        problem = path_segment_issue("Album title", self._album_title_edit.text())
        if problem:
            return False, problem
        tracks = self._model.tracks()
        if not tracks:
            return False, "No tracks loaded."
        for track in tracks:
            if not track.title.strip():
                return False, f"Track {track.number} is missing a title."
            problem = path_segment_issue(f"Track {track.number}’s title", track.title)
            if problem:
                return False, problem
            problem = path_segment_issue(
                f"Track {track.number}’s artist", track.artist_credit
            )
            if problem:
                return False, problem
        # At least one track must be ticked in the Rip? column, or there's
        # nothing to rip.
        if self._model.selected_count() == 0:
            return False, "No tracks selected to rip (tick at least one in Rip?)."
        return True, ""
