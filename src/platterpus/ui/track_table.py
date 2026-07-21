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
    Qt,
)
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QHeaderView,
    QLineEdit,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionProgressBar,
    QStyleOptionViewItem,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from platterpus.adapters.musicbrainz_client import ReleaseDetail, TrackSummary

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


# Column layout. Defined once so the model + view + tests share it. Status is
# LAST so the existing column indices (and every test/consumer that uses them)
# stay put.
_COLUMNS: list[str] = ["#", "Title", "Artist", "Length", "Status"]
_COL_NUMBER: int = 0
_COL_TITLE: int = 1
_COL_ARTIST: int = 2
_COL_LENGTH: int = 3
_COL_STATUS: int = 4
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

# Custom model role carrying the ripping row's live percent (int 0–100, or None
# when the row has no live progress). The Status-column delegate reads it to
# draw a real progress bar; DisplayRole keeps the plain "⟳ Ripping" text so
# assistive technology and tests still see status as text (never colour/paint
# alone — docs/ux-design-principles.md #10).
PROGRESS_ROLE: int = int(Qt.ItemDataRole.UserRole) + 1


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

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tracks: list[TrackSummary] = []
        # Live per-track rip status keyed by 1-based track number; absent = pending.
        self._status: dict[int, str] = {}
        # Live percent for the track currently being ripped (1-based number →
        # 0–100). Only the RIPPING row ever holds one; done/reset clears it so a
        # finished row shows "✓ Done", never a stale frozen bar.
        self._progress: dict[int, int] = {}
        # The track the worker's task-percent stream currently applies to (the
        # last one marked RIPPING). The progress signal carries no track number
        # — the worker's current_track signal set this just before.
        self._ripping_track: int | None = None

    # --- Public surface ---

    def set_tracks(self, tracks: Sequence[TrackSummary]) -> None:
        """Replace the current track list. Resets the view (and rip status)."""
        self.beginResetModel()
        self._tracks = list(tracks)
        self._status = {}
        self._progress = {}
        self._ripping_track = None
        self.endResetModel()

    def set_track_status(self, track_number: int, status: str) -> None:
        """Set the live rip status for a 1-based `track_number` and refresh its
        Status cell. Out-of-range numbers are ignored (never raises)."""
        row = track_number - 1
        if row < 0 or row >= len(self._tracks):
            return
        self._status[track_number] = status
        # Keep the live-progress bookkeeping in step with the status: a row
        # entering RIPPING becomes the target of the worker's task-percent
        # stream; a row leaving RIPPING (done) drops its bar so it can never
        # freeze mid-way on a finished track.
        if status == STATUS_RIPPING:
            self._ripping_track = track_number
        else:
            self._progress.pop(track_number, None)
            if self._ripping_track == track_number:
                self._ripping_track = None
        cell = self.index(row, _COL_STATUS)
        self.dataChanged.emit(cell, cell, [Qt.ItemDataRole.DisplayRole, PROGRESS_ROLE])

    def set_current_progress(self, task_percent: float) -> None:
        """Update the live percent shown on the currently-ripping row.

        The worker's ``progress`` signal carries no track number (the task bar
        is per-operation), so the percent applies to whichever track was last
        marked RIPPING via ``set_track_status``. No-op when no track is ripping
        (e.g. during the pre-track disc scan). Never raises.
        """
        track = self._ripping_track
        if track is None:
            return
        percent = max(0, min(100, int(task_percent)))
        if self._progress.get(track) == percent:
            return  # same value — skip the repaint (the stream is ~10/s)
        self._progress[track] = percent
        cell = self.index(track - 1, _COL_STATUS)
        self.dataChanged.emit(cell, cell, [PROGRESS_ROLE])

    def reset_statuses(self) -> None:
        """Clear every track's rip status back to pending (called at rip start)."""
        if not self._status and not self._progress:
            return
        self._status = {}
        self._progress = {}
        self._ripping_track = None
        if self._tracks:
            top = self.index(0, _COL_STATUS)
            bottom = self.index(len(self._tracks) - 1, _COL_STATUS)
            self.dataChanged.emit(
                top, bottom, [Qt.ItemDataRole.DisplayRole, PROGRESS_ROLE]
            )

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
        # Live percent for the Status column's progress-bar delegate: an int
        # 0–100 while the row is ripping and a percent has arrived, else None
        # (the delegate then paints plain text).
        if role == PROGRESS_ROLE:
            if index.column() != _COL_STATUS:
                return None
            track = self._tracks[index.row()]
            return self._progress.get(track.number)
        if role not in (
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.EditRole,
        ):
            return None
        track = self._tracks[index.row()]
        col = index.column()
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
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        col = index.column()
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
        if index.column() in _EDITABLE_COLS:
            return base | Qt.ItemFlag.ItemIsEditable
        return base


class TrackStatusDelegate(QStyledItemDelegate):
    """Paints a live progress bar in the Status cell of the ripping row.

    Reads :data:`PROGRESS_ROLE`: an int percent means "this row is ripping —
    draw a real bar" (with the percent as the bar's own text, so the number is
    visible without hovering); None falls back to the default text painting
    ("✓ Done", "⟳ Ripping" before the first percent arrives, or blank for
    pending). The DisplayRole text is untouched either way, so assistive
    technology and tests keep reading the status as text.
    """

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: _Index,
    ) -> None:
        percent = index.data(PROGRESS_ROLE)
        if not isinstance(percent, int):
            super().paint(painter, option, index)
            return
        bar = QStyleOptionProgressBar()
        bar.rect = option.rect.adjusted(2, 2, -2, -2)  # breathing room in the cell
        bar.minimum = 0
        bar.maximum = 100
        bar.progress = percent
        bar.text = f"{percent}%"
        bar.textVisible = True
        style = option.widget.style() if option.widget is not None else None
        if style is None:  # pragma: no cover — option.widget is always the view
            super().paint(painter, option, index)
            return
        style.drawControl(
            QStyle.ControlElement.CE_ProgressBar, bar, painter, option.widget
        )


class TrackTable(QWidget):
    """Composite widget: album-level fields + track table."""

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
        # The Status column paints a live progress bar on the ripping row
        # (per-track progress, feature backlog 2026-07-21); other rows/roles
        # fall through to the default text painting.
        self._status_delegate: TrackStatusDelegate = TrackStatusDelegate(self._view)
        self._view.setItemDelegateForColumn(_COL_STATUS, self._status_delegate)
        # Title + Artist columns stretch; # + Length are content-sized.
        header = self._view.horizontalHeader()
        for col in range(len(_COLUMNS)):
            mode = (
                QHeaderView.ResizeMode.Stretch
                if col in _EDITABLE_COLS
                else QHeaderView.ResizeMode.ResizeToContents
            )
            header.setSectionResizeMode(col, mode)
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

    def on_rip_progress(self, overall: float, task: float) -> None:
        """Drive the ripping row's live progress bar from the worker's
        ``progress(overall, task)`` signal. The task percent is the current
        operation's own 0–100 — exactly what the row's bar should show; the
        overall percent belongs to the rip-progress pane, not a single row.
        No-op when no track is marked ripping (e.g. the pre-track disc scan).
        """
        del overall
        self._model.set_current_progress(task)

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

    def validate(self) -> tuple[bool, str]:
        """Validate that nothing required is blank.

        Returns (True, "") when everything's filled in; (False, message)
        with the first failure when not. The main window uses this
        before kicking off a rip.
        """
        if not self._album_artist_edit.text().strip():
            return False, "Album artist is required."
        if not self._album_title_edit.text().strip():
            return False, "Album title is required."
        tracks = self._model.tracks()
        if not tracks:
            return False, "No tracks loaded."
        for track in tracks:
            if not track.title.strip():
                return False, f"Track {track.number} is missing a title."
        return True, ""
