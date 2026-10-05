"""Release picker dialog — substitutes for the ripper's interactive TTY prompt.

Critical Rule #5: when MusicBrainz returns multiple matches for the
inserted disc, the GUI presents them in this dialog and obtains the
chosen MBID — the backend is then invoked with the chosen release id and
never opens a prompt.

The dialog is a pure picker: it doesn't do MB lookups itself. The
caller passes in a list[ReleaseSummary] (typically from the
MusicBrainzWorker) and reads back the chosen MBID via
`selected_mbid()` after the dialog accepts.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from platterpus.adapters.musicbrainz_client import ReleaseSummary
from platterpus.ui.dialogs.centering import CenteredDialog

# Column layout for the candidates table. Defined once so the test can
# assert on positions without magic numbers.
_COLUMNS: list[tuple[str, str]] = [
    # (header label, attribute on ReleaseSummary)
    ("Title", "title"),
    ("Artist", "artist_credit"),
    ("Year", "date"),
    ("Country", "country"),
    ("Label", "label"),
    ("Catalog #", "catalog_number"),
    ("Tracks", "track_count"),
    ("Format", "medium_format"),
    ("Notes", "disambiguation"),
]

#: The columns whose text has no natural length limit: they share the table's
#: width and wrap. The rest (a date, a country code, a catalog number, a count,
#: a format) are short by nature and are sized to their content.
_PROSE_ATTRIBUTES: frozenset[str] = frozenset(
    {"title", "artist_credit", "label", "disambiguation"}
)

#: The widest the picker opens, whatever its text would like: about the width of
#: Settings on a large screen. Wider, a row is harder to follow across.
_WIDEST_OPENING_PX: int = 1200


class ReleasePickerDialog(CenteredDialog):
    """Modal picker shown when MusicBrainz returns >1 release candidate."""

    def __init__(
        self,
        releases: Sequence[ReleaseSummary],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._releases: list[ReleaseSummary] = list(releases)

        self.setWindowTitle("Pick a MusicBrainz release")
        self.setModal(True)
        # Generous default size; users frequently have long album titles.
        self.resize(900, 380)

        root = QVBoxLayout(self)

        intro = QLabel(
            f"MusicBrainz returned {len(self._releases)} matches. "
            "Pick the release that matches the disc in the drive."
        )
        # PlainText, stated rather than left to Qt's AutoText, which reads text
        # as HTML when its first line happens to hold a known tag (CLAUDE.md
        # Critical rule #12). Only a count reaches this label; the releases'
        # own titles and artists go into the table's cells below, and a table
        # cell shows its text as written.
        intro.setTextFormat(Qt.TextFormat.PlainText)
        intro.setWordWrap(True)
        root.addWidget(intro)

        self._table: QTableWidget = QTableWidget(
            len(self._releases), len(_COLUMNS), self
        )
        # Screen readers announce a table by its accessible name; without one
        # this reads as an anonymous grid (ux-design-principles.md #10).
        self._table.setAccessibleName("MusicBrainz release candidates")
        self._table.setHorizontalHeaderLabels([header for header, _ in _COLUMNS])
        # Select whole rows, one at a time — the user is picking a
        # release, not editing cells.
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # **Every column whose text can run long shares the width and wraps;
        # only the short codes fit their content.** Title and Artist used to be
        # the only stretching columns, with Label and Notes sized to their whole
        # text — so with real releases (a two-label credit, a disambiguation like
        # "Japanese reissue, remastered, with obi") those two took the width and
        # squeezed Title and Artist, the columns a user reads to choose, to three
        # characters: "Lift Y…", "G… Y…" (audit, 2026-10-05; the test stand-ins,
        # "Album" and "Artist" with no label or notes, never showed it). Now the
        # prose columns divide what the short ones leave, in proportion to what
        # each needs, never narrower than its longest word (a word cannot wrap);
        # rows grow to the wrapped text, and if even the words do not fit — 150 %
        # text on a small screen — the table scrolls sideways rather than cutting
        # one off. Recomputed whenever the table changes size.
        header = self._table.horizontalHeader()
        for i, (_, attr) in enumerate(_COLUMNS):
            mode = (
                QHeaderView.ResizeMode.Interactive
                if attr in _PROSE_ATTRIBUTES
                else QHeaderView.ResizeMode.ResizeToContents
            )
            header.setSectionResizeMode(i, mode)
        self._table.setWordWrap(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)

        self._populate_rows()
        self._table.installEventFilter(self)
        root.addWidget(self._table, stretch=1)
        # Open as wide as the text would like, up to a width past which a row is
        # harder to scan than a wrapped cell is to read; `CenteredDialog` caps it
        # at the screen, where wrapping takes over.
        natural = min(self._natural_width(), _WIDEST_OPENING_PX)
        self.resize(max(self.width(), natural), self.height())

        # Double-click on a row accepts the dialog (matches OS pattern
        # for "pick from list" dialogs).
        self._table.itemDoubleClicked.connect(lambda _: self.accept())

        # Button box. Pick is the primary; we default to row 0 so the
        # user can just press Enter to accept the top result.
        self._button_box: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Pick this release"
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        root.addWidget(self._button_box)

        # Default selection: row 0 if any rows exist.
        if self._releases:
            self._table.selectRow(0)

    # --- Public surface -----------------------------------------------------

    def selected_mbid(self) -> str | None:
        """Return the MBID of the selected row, or None if nothing selected."""
        row = self._table.currentRow()
        if row < 0 or row >= len(self._releases):
            return None
        return self._releases[row].mbid

    def selected_release(self) -> ReleaseSummary | None:
        """Return the full ReleaseSummary of the selected row, or None."""
        row = self._table.currentRow()
        if row < 0 or row >= len(self._releases):
            return None
        return self._releases[row]

    # --- Internals ---------------------------------------------------------

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 — Qt API
        """Share the width out again whenever the table changes size."""
        if watched is self._table and event.type() == QEvent.Type.Resize:
            self._share_prose_width()
        return super().eventFilter(watched, event)

    def _share_prose_width(self) -> None:
        """Divide the table's free width among the prose columns; see `__init__`."""
        header = self._table.horizontalHeader()
        prose = [i for i, (_, a) in enumerate(_COLUMNS) if a in _PROSE_ATTRIBUTES]
        short = sum(
            header.sectionSize(i) for i in range(len(_COLUMNS)) if i not in prose
        )
        # The vertical bar's width is ALWAYS set aside, so the bar appearing or
        # going as the rows reflow cannot change the answer and trigger another.
        room = (
            self._table.width()
            - 2 * self._table.frameWidth()
            - self._table.verticalScrollBar().sizeHint().width()
            - short
        )
        need = {
            i: max(self._table.sizeHintForColumn(i), header.sectionSizeHint(i))
            for i in prose
        }
        total = sum(need.values()) or 1
        for i in prose:
            header.resizeSection(
                i, max(self._longest_word_width(i), room * need[i] // total)
            )
        self._table.resizeRowsToContents()

    def _longest_word_width(self, column: int) -> int:
        """The width column ``column``'s widest single word needs, heading included."""
        attr = _COLUMNS[column][1]
        cells = [str(getattr(release, attr, "") or "") for release in self._releases]
        margin = (
            self._table.style().pixelMetric(QStyle.PixelMetric.PM_FocusFrameHMargin) + 1
        )
        widest_cell = max(
            (
                self._table.fontMetrics().horizontalAdvance(word)
                for text in cells
                for word in text.split()
            ),
            default=0,
        )
        heading = self._table.horizontalHeader().fontMetrics()
        widest_heading = max(
            (heading.horizontalAdvance(w) for w in _COLUMNS[column][0].split()),
            default=0,
        )
        # A few pixels of slack: the header pads its text more than a cell does.
        return max(widest_cell, widest_heading) + 2 * margin + 4

    def _natural_width(self) -> int:
        """The dialog width at which no cell would need to wrap."""
        columns = sum(
            max(
                self._table.sizeHintForColumn(i),
                self._table.horizontalHeader().sectionSizeHint(i),
            )
            for i in range(len(_COLUMNS))
        )
        bar = self._table.verticalScrollBar().sizeHint().width()
        frame = 2 * self._table.frameWidth()
        layout = self.layout()
        margins = layout.contentsMargins() if layout is not None else None
        sides = margins.left() + margins.right() if margins is not None else 0
        return columns + bar + frame + sides

    def _populate_rows(self) -> None:
        for row, release in enumerate(self._releases):
            for col, (_, attr) in enumerate(_COLUMNS):
                value = getattr(release, attr, "")
                if value is None:
                    text = ""
                else:
                    text = str(value)
                item = QTableWidgetItem(text)
                # Cells aren't editable but should support copy via
                # selection (per the disc_info_panel precedent).
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(row, col, item)
