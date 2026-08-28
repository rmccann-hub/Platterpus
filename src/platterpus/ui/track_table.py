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

import logging
from collections.abc import Callable, Iterable, Sequence
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

log = logging.getLogger(__name__)


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

# --- Column widths: measured once per disc, never during a rip -------------------
#
# WHY THIS IS NOT `ResizeToContents`, which is what it used to be. That mode
# re-measures whenever the data changes, and the Status column's data changes on
# EVERY track transition — so the whole table re-laid-out mid-rip. Measured on the
# 14-track reference disc at a 900 px window (2026-08-05, after the maintainer
# reported the columns "eating the width"):
#
#     pending   Rip?=33  #=26  Title=370  Artist=369  Length=52  Status=48
#     ripping   Rip?=33  #=26  Title=360  Artist=360  Length=52  Status=67
#     done      Rip?=33  #=26  Title=367  Artist=367  Length=52  Status=53
#
# Status swings 48 -> 67 -> 53 as one track advances, and the two stretch columns
# give and take to absorb it — so the Title text the user is reading shifts sideways
# roughly **twice per track**, 28 times over a disc. Nothing is broken; it just
# never sits still, which reads as the layout being unstable rather than as a bar
# advancing.
#
# So: every column except Title gets a width computed from the widest string it can
# ever hold, and only Title stretches. The widths are derived from the SAME tables
# the cells render from (`_STATUS_DISPLAY.values()`, `_COLUMNS`), so a new status
# string widens the column automatically — a hand-maintained list of specimen
# strings would be a second copy to keep in sync, and it would go stale silently.
#
# Padding for the cell's own margins plus the frame; measured empirically rather
# than derived, because the exact figure is style-dependent and only needs to be
# generous enough that no text is clipped.
_COL_PAD_PX: int = 16
# The widest track number a Red Book CD can carry is 99, so sizing to "99" makes a
# 9-track disc and a 14-track disc render identically — otherwise the `#` column
# changes width between discs for no reason the user can see.
_WIDEST_TRACK_NUMBER: str = "99"
# The widest length string: a CD tops out near 80 minutes, so two digits of minutes
# is the ceiling. "00:00" is wider than "9:99" in any proportional font.
_WIDEST_LENGTH: str = "00:00"
# Artist starts sized to its content but never takes more than this share of the
# table, so a compilation with long artist credits cannot squeeze Title out. The
# user can still drag it — Artist is Interactive, not Fixed.
_ARTIST_MAX_FRACTION: float = 0.32


def status_column_width(measure: Callable[[str], int], pad: int = _COL_PAD_PX) -> int:
    """Width the Status column needs to hold ANY status it can ever show.

    ``measure`` is a text-width function (in practice ``QFontMetrics
    .horizontalAdvance``); injected so this is a pure, directly testable function
    rather than something only observable through a laid-out widget.

    Derived from ``_STATUS_DISPLAY`` itself, so adding a status string cannot leave
    this width behind. Pure; never raises.
    """
    candidates = [_COLUMNS[_COL_STATUS], *_STATUS_DISPLAY.values()]
    return max(measure(text) for text in candidates) + pad


def fixed_column_widths(
    measure: Callable[[str], int], pad: int = _COL_PAD_PX
) -> dict[int, int]:
    """Width for every column that must NOT resize itself, keyed by column index.

    Excludes Title (which stretches) and Artist (whose width depends on the disc's
    own data — see `artist_column_width`). Pure; never raises.
    """
    return {
        _COL_RIP: measure(_COLUMNS[_COL_RIP]) + pad,
        _COL_NUMBER: max(measure(_COLUMNS[_COL_NUMBER]), measure(_WIDEST_TRACK_NUMBER))
        + pad,
        _COL_LENGTH: max(measure(_COLUMNS[_COL_LENGTH]), measure(_WIDEST_LENGTH)) + pad,
        _COL_STATUS: status_column_width(measure, pad),
    }


def artist_column_width(
    measure: Callable[[str], int],
    artists: Iterable[str],
    available_px: int,
    pad: int = _COL_PAD_PX,
) -> int:
    """Initial width for the Artist column: what its content needs, capped.

    An album where every row reads "The Police" needs ~70 px and used to be handed
    half the table, because two `Stretch` columns split the remainder evenly and
    Title is the column with the varied, long text. Sized to content instead, with
    a ceiling of `_ARTIST_MAX_FRACTION` of the table so a compilation's long artist
    credits still cannot crowd Title out.

    `available_px` <= 0 (a widget not laid out yet) means "no ceiling known", so the
    content width stands. Pure; never raises.
    """
    needed = max(
        [measure(_COLUMNS[_COL_ARTIST]), *(measure(a) for a in artists if a)] or [0]
    )
    needed += pad
    if available_px > 0:
        return min(needed, int(available_px * _ARTIST_MAX_FRACTION))
    return needed


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

    def artist_credits(self) -> list[str]:
        """Every row's Artist text, for sizing that column to its real content.

        Reads the model rather than the ReleaseDetail so it reflects the user's
        edits and any album-artist propagation, not just what MusicBrainz sent.
        """
        return [t.artist_credit for t in self._tracks]

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

    def rowCount(self, parent: _Index = QModelIndex()) -> int:  # noqa: N802 — Qt override
        return 0 if parent.isValid() else len(self._tracks)

    def columnCount(self, parent: _Index = QModelIndex()) -> int:  # noqa: N802 — Qt override
        return 0 if parent.isValid() else len(_COLUMNS)

    def headerData(  # noqa: N802 — QAbstractTableModel override
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

    def setData(  # noqa: N802 — QAbstractTableModel override
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
        # ONLY Title stretches. Everything else is Interactive at a width computed
        # from the widest string it can hold — see the `_COL_PAD_PX` block above for
        # the measurements that motivated this. `Interactive`, not `Fixed`, so the
        # user can still drag any boundary; what they cannot get is the table
        # re-laying itself out under them while a rip advances.
        header = self._view.horizontalHeader()
        for col in range(len(_COLUMNS)):
            mode = (
                QHeaderView.ResizeMode.Stretch
                if col == _COL_TITLE
                else QHeaderView.ResizeMode.Interactive
            )
            header.setSectionResizeMode(col, mode)
        self._apply_column_widths()
        # Right-click a row (or several highlighted rows) for quick rip-selection
        # actions — the second half of the "checkbox column + right-click" model.
        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._show_track_menu)
        # Surface the model's selection changes as our own signal so the main
        # window can watch one object (the widget), not the inner model.
        self._model.selection_changed.connect(self.selection_changed)
        root.addWidget(self._view, stretch=1)

    def _apply_column_widths(self) -> None:
        """Size every non-stretching column from the widest text it can hold.

        Called when the DISC changes (a new release, placeholder rows, an
        album-artist propagation) — deliberately NOT when a track's status changes,
        which is what `ResizeToContents` used to do and is what made the table shift
        under the user roughly twice per track. Best-effort: a geometry helper must
        never take a rip down, so a Qt failure is logged and swallowed.
        """
        try:
            from PySide6.QtGui import QFontMetrics

            header = self._view.horizontalHeader()
            measure = QFontMetrics(self._view.font()).horizontalAdvance
            widths = fixed_column_widths(measure)
            for col, width in widths.items():
                header.resizeSection(col, width)
            # Artist last: its ceiling is a share of what is left after the fixed
            # columns, not of the whole table, or a narrow window would let it take
            # a third of the space Title needs.
            viewport = self._view.viewport().width()
            remaining = max(0, viewport - sum(widths.values()))
            header.resizeSection(
                _COL_ARTIST,
                artist_column_width(measure, self._model.artist_credits(), remaining),
            )
        except Exception:  # noqa: BLE001 — layout polish must never break a rip
            log.exception("column-width sizing failed; leaving Qt's defaults")

    # --- Public surface -----------------------------------------------------

    def set_release(self, detail: ReleaseDetail) -> None:
        """Populate from a MusicBrainz ReleaseDetail."""
        self._album_artist_edit.setText(detail.summary.artist_credit)
        self._album_title_edit.setText(detail.summary.title)
        self._album_year_edit.setText(detail.summary.date)
        self._model.set_tracks(detail.tracks)
        self._apply_column_widths()

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
            self._apply_column_widths()
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
        self._apply_column_widths()

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
        self._apply_column_widths()

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

    def set_all_selected(self, selected: bool) -> None:
        """Tick or untick every track's Rip? box.

        A delegation, like :meth:`tracks` and :meth:`selected_track_numbers` above.
        Added 2026-08-07 because the widget exposed every *read* of the selection
        and none of the *writes*: the right-click menu reached
        ``self._model.set_all_selected`` directly, so nothing outside the widget
        could change the selection at all. The ``select-tracks`` script verb was
        written against the widget — the obvious surface — and would have raised
        ``AttributeError`` on the first real disc, recorded as ERROR by the
        runner's fault guard. Caught before it shipped by
        ``tests/test_uiscript_rip_verbs.py``'s floor, which checks every name a
        verb calls against the real class rather than against its own stub.
        """
        self._model.set_all_selected(selected)

    def set_only_selected(self, track_numbers: Sequence[int]) -> None:
        """Tick exactly ``track_numbers`` and untick everything else.

        The write behind "Rip only these" — and behind ``select-tracks 1,3,5-7``,
        which is what reaches cyanrip's ``-l``. See :meth:`set_all_selected` for
        why these two delegations did not exist until now.
        """
        self._model.set_only_selected(track_numbers)

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
