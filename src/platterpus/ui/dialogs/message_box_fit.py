"""Fitting a ``QMessageBox`` to the screen it opens on.

**Why this exists (audit, 2026-10-05).** `CenteredDialog` fits itself to the
screen (`fit_scroll_area.fit_dialog_to_screen`). A `QMessageBox` is sized by Qt,
privately, whenever its layout changes (``QMessageBoxPrivate::updateSize``): the
WIDTH capped at half the screen (500 px at most), the HEIGHT whatever the text
needs, with no ceiling, then fixed so nobody can resize it. Nothing checked the
result. Measured with the real texts (offscreen, Fusion, DejaVu Sans): the
*Script commands* reference 480 × 1820 on a 960 × 540 screen (500 × 1764 even on
1920 × 1080); the cyanrip offer for an unapproved beta build 500 × 903 at 150 %
text on a 1366 × 768 laptop; the dependency summary after a failed install
480 × 1260 at 150 % on 960 × 540 — each with its buttons below the screen. A
second defect shared the root, and `auto_center.fit_before_centring` carries it:
boxes were centred before Qt had sized them.

**What the fit does,** once, on first show, from `DialogCenterFilter`, before
the box is centred:

1. asks Qt to size the box now (:func:`_let_qt_size`);
2. if a long TITLE made Qt size it wider than the screen less
   `SIDE_MARGIN_PX` on each side, shortens the title its title bar shows
   (:func:`_shorten_a_title_too_wide`; KDD-41, 2026-10-05);
3. if it is taller than the screen allows, WIDENS it, to the narrowest width at
   which it fits, by setting a minimum width on Qt's text label — the one input
   Qt's own sizing reads — and never past Qt's own width ceiling
   (:func:`qt_width_ceiling`), beyond which Qt would squeeze the label, nor
   into the side margin;
4. if no width is enough (long text, a small screen, a large font), the message
   text SCROLLS inside the box and the buttons stay on screen
   (:func:`_scroll_the_text`).

**Leaning on two Qt internals, named rather than hidden.** Qt's text label has
the object name ``qt_msgbox_label`` (true since Qt 4, and what
`tests/test_message_boxes_are_plaintext.py` already reads), and the box re-sizes
itself on a ``LayoutRequest`` event. If either stops being true the fit does
nothing rather than something wrong, and `tests/test_ui_conformance.py` — which
measures every message box in every screen condition — goes red, which is the
point of measuring rather than trusting.
"""

from __future__ import annotations

import logging
from typing import Final

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QSize, Qt, QTimer
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
)

# Re-exported: one side margin for every fitted window, a message box included.
from platterpus.ui.dialogs.fit_scroll_area import SIDE_MARGIN_PX

log = logging.getLogger(__name__)

#: Qt's object name for a message box's main text label.
QT_TEXT_LABEL_NAME: Final[str] = "qt_msgbox_label"

#: Our object name for the scroll area the text moves into when it cannot fit.
#: A test, and anyone reading a widget dump, can find it by this.
SCROLL_AREA_NAME: Final[str] = "platterpus_message_text_scroll"

#: Qt widens a box to its title's width PLUS this, in its own sizing pass
#: (``QMessageBoxPrivate::updateSize``: ``horizontalAdvance(title) + 50``), to
#: leave room for the title bar's buttons. Mirrored here so a shortened title
#: makes Qt choose the width we need, no more.
_QT_TITLE_ALLOWANCE_PX: Final[int] = 50

#: The font Qt measures a message box's title in (the same ``updateSize``).
_QT_TITLE_FONT_CLASS: Final[str] = "QMdiSubWindowTitleBar"

#: A Qt dynamic property holding a box's full title while its title bar shows a
#: shortened one (:func:`_shorten_a_title_too_wide`), so a later fit — the box
#: shown again, perhaps on a wider screen — starts from the whole title. Stored on
#: the box for the reason `auto_center.CENTERED_PROPERTY` gives: it lives and
#: dies with the box.
FULL_TITLE_PROPERTY: Final[str] = "_platterpus_full_title"

#: The shortest a scrolling text area may be: three lines of default text, so a
#: box on an absurdly short screen still shows something to scroll.
_MIN_SCROLL_HEIGHT_PX: Final[int] = 60

#: Stop the width search when the bracket is this narrow; a few pixels of width
#: is not worth another layout pass.
_WIDTH_SEARCH_PRECISION_PX: Final[int] = 8


def qt_width_ceiling(screen_width: int) -> int:
    """The widest Qt will make a message box on a screen this wide.

    Qt's rule (``QMessageBoxPrivate::updateSize``, Qt 5 and 6): the whole screen
    width on a screen up to 1024 px wide, otherwise ``min(width - 480, 1000)``.
    Asking for more than this does not widen the box: Qt fixes it at the ceiling
    and squeezes the label narrower than its minimum, cutting its text off at the
    right edge — so the widening below never asks for more.
    """
    if screen_width <= 1024:
        return screen_width
    return min(screen_width - 480, 1000)


def _let_qt_size(box: QMessageBox) -> None:
    """Make Qt run its own sizing pass on ``box`` now, instead of on its next turn.

    Qt re-sizes a message box when the box receives a ``LayoutRequest`` and is
    visible — which it already is when the app-wide filter sees its Show event.
    Delivered synchronously, so the size read straight after is the final one.
    """
    QCoreApplication.sendEvent(box, QEvent(QEvent.Type.LayoutRequest))


def fit_message_box(box: QMessageBox, avail: QSize, margin: int) -> None:
    """Size ``box`` so all of it — text and buttons — fits in ``avail``.

    ``margin`` is kept clear vertically, for the taskbar and the title bar: the
    same `CenteredDialog.SCREEN_MARGIN_PX` every other dialog is held to.
    Sideways, `SIDE_MARGIN_PX` is kept clear on each side, as for every fitted
    window.
    """
    label = box.findChild(QLabel, QT_TEXT_LABEL_NAME)
    if label is None:
        log.warning(
            "message box %r has no %r label; it is left at Qt's own size",
            box.windowTitle(),
            QT_TEXT_LABEL_NAME,
        )
        return
    _restore_the_full_title(box)
    _let_qt_size(box)
    if _shorten_a_title_too_wide(box, avail.width() - 2 * SIDE_MARGIN_PX):
        _let_qt_size(box)
    max_h = max(avail.height() - margin, 120)
    if box.height() <= max_h:
        return  # the common case: a short message, untouched
    max_w = min(avail.width() - 2 * SIDE_MARGIN_PX, qt_width_ceiling(avail.width()))
    # What the box needs beside the label — icon, spacing, margins. Read from the
    # box as Qt laid it out, not assumed.
    qt_width = label.width()  # read now: every probe below changes it
    beside = box.width() - qt_width
    widest = max_w - beside
    if widest > qt_width and _fits_at(box, label, widest, max_h):
        _narrowest_fit(box, label, qt_width, widest, max_h)
        log.info(
            "message box %r widened to %dx%d to fit a %dx%d screen",
            box.windowTitle(),
            box.width(),
            box.height(),
            avail.width(),
            avail.height(),
        )
        return
    _scroll_the_text(box, label, max(widest, qt_width), avail, margin)


def _shorten_a_title_too_wide(box: QMessageBox, widest: int) -> bool:
    """Shorten a title so wide that Qt would make the box wider than ``widest``.

    Returns whether the title changed. **Why the title, and not the box.** Qt
    widens a box to fit its title (its width plus :data:`_QT_TITLE_ALLOWANCE_PX`,
    up to :func:`qt_width_ceiling` — the WHOLE screen on one up to 1024 px wide),
    and it applies that rule last, every time it sizes the box, including on the
    box's own Show, which runs AFTER this fit. A width we set is therefore
    undone (measured: a box resized from inside the Show filter came back at
    Qt's width), and the one input the rule reads is the title. A box sized
    for a long title (the matrix measures ``Open <a long path>``) touched both
    edges of every small screen.

    The title is shortened in the middle, which keeps a path's start and its
    last folder, to what the title bar of a box ``widest`` px wide can show; the
    window manager would cut it in that box anyway. Nothing is lost: the whole
    title stays the box's accessible name, which is what a screen reader reads
    for a window, and :data:`FULL_TITLE_PROPERTY` keeps it for a later fit.
    """
    title = box.windowTitle()
    # PySide6 6.11's stub types the class name as bytes, but only a str is
    # accepted at runtime (measured: bytes raises ValueError).
    font = QApplication.font(_QT_TITLE_FONT_CLASS)  # type: ignore[call-overload]  # stub says bytes; runtime takes str
    metrics = QFontMetrics(font)
    room = widest - _QT_TITLE_ALLOWANCE_PX
    if metrics.horizontalAdvance(title) <= room:
        return False
    box.setProperty(FULL_TITLE_PROPERTY, title)
    if not box.accessibleName():
        box.setAccessibleName(title)
    box.setWindowTitle(metrics.elidedText(title, Qt.TextElideMode.ElideMiddle, room))
    log.info(
        "message box title %r is wider than a %dpx box can show; its title bar "
        "shows it shortened",
        title,
        widest,
    )
    return True


def _restore_the_full_title(box: QMessageBox) -> None:
    """Undo :func:`_shorten_a_title_too_wide` before a fit measures the box again."""
    full = box.property(FULL_TITLE_PROPERTY)
    if isinstance(full, str) and full:
        box.setWindowTitle(full)
        box.setProperty(FULL_TITLE_PROPERTY, None)


def _fits_at(box: QMessageBox, label: QLabel, width: int, max_h: int) -> bool:
    """Give the label ``width`` and report whether the box is then short enough."""
    label.setMinimumWidth(width)
    _let_qt_size(box)
    return box.height() <= max_h


def _narrowest_fit(
    box: QMessageBox, label: QLabel, too_narrow: int, fits: int, max_h: int
) -> None:
    """Binary-search the narrowest label width in ``(too_narrow, fits]`` that fits.

    Narrowest, not widest: the box stays as close to the shape Qt would have given
    it as the screen allows, and a line of prose much wider than this is harder to
    read, not easier. Leaves the label at the width found.
    """
    while fits - too_narrow > _WIDTH_SEARCH_PRECISION_PX:
        middle = (too_narrow + fits) // 2
        if _fits_at(box, label, middle, max_h):
            fits = middle
        else:
            too_narrow = middle
    _fits_at(box, label, fits, max_h)


def _scroll_the_text(
    box: QMessageBox, label: QLabel, width: int, avail: QSize, margin: int
) -> None:
    """The last resort: the text scrolls inside the box; the buttons stay put.

    Qt's label is moved into a scroll area that takes the label's place in the
    box's grid, as wide as the screen allows and only as tall as leaves room for
    everything else. The area takes keyboard focus (Qt's default for a scroll
    area), so the arrow and Page keys scroll it.

    **Qt can take the label back.** Qt rebuilds the box's layout whenever its
    icon, informative text or check box changes — the unattended crash dialog
    changes its informative text every second — and the rebuild puts the label
    straight back into the grid. :class:`_RefitWhenQtTakesTheLabelBack` hides the
    emptied area and fits again, and the refit puts the label back into the SAME
    area. One area for the life of the box, never a new one per rebuild: deleting
    the old one would make PySide invalidate every Python handle on the label
    (it records the area as the label's owner when ``setWidget`` is called, and
    cannot see Qt moving the label away) — measured, a handle held across one
    rebuild raised "Internal C++ object already deleted" on a label that was alive.
    """
    grid = box.layout()
    if not isinstance(grid, QGridLayout):
        log.warning("message box %r has no grid layout; left as Qt sized it", box)
        return
    cell = _grid_cell(grid, grid.indexOf(label))
    if cell is None:
        log.warning("message box %r: text label not in its layout", box.windowTitle())
        return
    row, column, row_span, column_span = cell
    # What the box needs below and around the text at this width, read off the box.
    _fits_at(box, label, width, 0)
    around = box.height() - label.height()
    height = max(avail.height() - margin - around, _MIN_SCROLL_HEIGHT_PX)

    grid.removeWidget(label)
    label.setMinimumWidth(0)
    area = box.findChild(QScrollArea, SCROLL_AREA_NAME)
    if area is None:
        area = QScrollArea(box)
        area.setObjectName(SCROLL_AREA_NAME)
        area.setAccessibleName("Message text")
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setWidget(label)
    else:
        # The box's own area, emptied by Qt's last rebuild: the label goes back.
        label.setParent(area.viewport())
    # The area, not the label, now carries the width Qt reads; the text wraps in
    # what is left of it beside the scroll bar.
    area.setMinimumWidth(width)
    area.setFixedHeight(height)
    grid.addWidget(area, row, column, row_span, column_span)
    area.show()
    label.show()  # reparenting hides a widget
    # Also what makes the area lay the label out afresh after a rebuild, which
    # left it at the size and place Qt's grid had given it.
    area.setWidgetResizable(True)
    label.installEventFilter(_RefitWhenQtTakesTheLabelBack(box, area, avail, margin))
    _let_qt_size(box)
    # Qt switches word wrap off and on again inside its sizing pass; for text
    # this long it always ends on, but a label left unwrapped in a scroll area
    # with no horizontal bar would cut every line off, so make sure.
    if not label.wordWrap():
        label.setWordWrap(True)
    log.info(
        "message box %r is too long for a %dx%d screen even at full width; its "
        "text scrolls in a %dpx area",
        box.windowTitle(),
        avail.width(),
        avail.height(),
        height,
    )


def _grid_cell(grid: QGridLayout, index: int) -> tuple[int, int, int, int] | None:
    """``(row, column, row_span, column_span)`` of layout item ``index``, or ``None``.

    PySide6 types `getItemPosition`'s return as ``object``; at runtime it is that
    4-tuple of ints. Checked rather than assumed, so a binding change degrades to
    "leave the box as Qt sized it" instead of an exception inside an event filter.
    """
    if index < 0:
        return None
    position = grid.getItemPosition(index)
    if not (
        isinstance(position, tuple)
        and len(position) == 4
        and all(isinstance(part, int) for part in position)
    ):
        return None
    row, column, row_span, column_span = (int(part) for part in position)
    return row, column, row_span, column_span


class _RefitWhenQtTakesTheLabelBack(QObject):
    """Watches Qt's text label after it has been moved into a scroll area.

    Parented to the box, so it lives exactly as long as the box does. When Qt's
    layout rebuild reparents the label back into the box, the scroll area is
    empty and no longer in any layout: it is hidden at once (kept, for the refit
    to reuse — see :func:`_scroll_the_text`), and the whole fit runs again on the
    next turn of the event loop — after Qt has finished rebuilding, which is the
    only moment the new layout can be measured.
    """

    def __init__(
        self, box: QMessageBox, area: QScrollArea, avail: QSize, margin: int
    ) -> None:
        super().__init__(box)
        self._box: QMessageBox = box
        self._area: QScrollArea = area
        self._avail: QSize = QSize(avail)
        self._margin: int = margin

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802 — Qt API
        if (
            event.type() == QEvent.Type.ParentChange
            and isinstance(obj, QLabel)
            and obj.parentWidget() is not self._area.viewport()
        ):
            obj.removeEventFilter(self)
            self._area.hide()
            # The box as context: if it is destroyed first, the refit is dropped.
            QTimer.singleShot(0, self._box, self._refit)
        return False

    def _refit(self) -> None:
        # Moving a widget to a new parent HIDES it, and Qt shows the label again
        # only from a queued call of its own. Until then the layout leaves the
        # hidden label out, the box measures short, and the fit would wrongly
        # decide there is nothing to do (measured: it returned, and the label then
        # reappeared in an 812-px box on a 540-px screen). Show it now, as Qt is
        # about to, so the fit measures the box the user will see.
        label = self._box.findChild(QLabel, QT_TEXT_LABEL_NAME)
        if label is not None and label.isHidden():
            label.show()
        fit_message_box(self._box, self._avail, self._margin)
        self.deleteLater()
