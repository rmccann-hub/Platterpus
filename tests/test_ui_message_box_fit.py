"""`ui/dialogs/message_box_fit.py`, unit by unit, in-process.

The conformance matrix (`tests/test_ui_conformance.py`) is the gate that every
real box fits every screen. This file pins the mechanism's pieces, each against
the failure it exists for, including the one the matrix cannot reach: Qt
rebuilding a box's layout AFTER it has been fitted — which the unattended crash
dialog does once a second as its countdown changes.

Each test passes ``avail`` explicitly, smaller than the test screen, so the
box's real screen does not have to be the one being fitted to.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QSize, Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
)

from platterpus.ui import message_boxes
from platterpus.ui.dialogs import message_box_fit as fit
from platterpus.ui.dialogs.auto_center import DialogCenterFilter, fit_plain_dialog

#: The vertical margin every dialog keeps clear (`CenteredDialog.SCREEN_MARGIN_PX`).
MARGIN = 64

#: About 1,300 characters of prose: too tall for a 400-px screen at Qt's own
#: 400-px width, short enough to fit once the box is widened.
PROSE = (
    "A newer cyanrip build is published on the beta channel, and taking it "
    "changes what your rips can claim: until a handshake round approves it, "
    "every rip records its ripper as unapproved in the report, the log and the "
    "EAC-compatible export. "
) * 6

#: Far more than any width can show on a 400-px screen.
TOO_LONG = "Commands, one per line, each with what it does and when to use it. " * 120


def _settle(qapp: QApplication) -> None:
    """Let the event loop run as a real one would — deferred deletions included.

    `processEvents()` called from outside any event loop never delivers a
    `deleteLater()`; a running application always does. Without the flush, a
    fit that deleted something it still needed passed here and broke in use (a
    revert probe found exactly that, 2026-10-05).
    """
    for _ in range(8):
        qapp.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture
def shown(qapp: QApplication) -> Iterator[list[QMessageBox]]:
    """Boxes a test showed, closed and handed back to Qt afterwards."""
    boxes: list[QMessageBox] = []
    yield boxes
    for box in boxes:
        box.close()
        box.deleteLater()
    _settle(qapp)


def _box(text: str, qapp: QApplication, shown: list[QMessageBox]) -> QMessageBox:
    box = message_boxes.build(QMessageBox.Icon.Warning, None, "Fit test", text)
    box.show()
    _settle(qapp)
    shown.append(box)
    return box


def _text_label(box: QMessageBox) -> QLabel:
    label = box.findChild(QLabel, fit.QT_TEXT_LABEL_NAME)
    assert label is not None, "Qt's message label was not found by its name"
    return label


def _handle_works(widget: QLabel) -> bool:
    """Whether a Python handle still reaches its widget.

    PySide raises RuntimeError ("Internal C++ object already deleted") through
    a handle it has invalidated. Asked of the handle, not of shiboken6, which is
    not a declared dependency.
    """
    try:
        widget.objectName()
    except RuntimeError:
        return False
    return True


def _areas(box: QMessageBox) -> list[QScrollArea]:
    return [
        area
        for area in box.findChildren(QScrollArea, fit.SCROLL_AREA_NAME)
        if area.isVisible()
    ]


def test_qts_width_ceiling_is_the_rule_qt_applies() -> None:
    assert fit.qt_width_ceiling(800) == 800
    assert fit.qt_width_ceiling(1024) == 1024
    assert fit.qt_width_ceiling(1366) == 886
    assert fit.qt_width_ceiling(1920) == 1000
    assert fit.qt_width_ceiling(3840) == 1000


def test_a_short_box_is_left_exactly_as_qt_sized_it(qapp, shown) -> None:
    box = _box("Select a drive first.", qapp, shown)
    before = box.size()
    fit.fit_message_box(box, QSize(800, 400), MARGIN)
    assert box.size() == before
    assert _text_label(box).minimumWidth() == 0
    assert _areas(box) == []


def test_a_tall_box_is_widened_to_the_narrowest_width_that_fits(qapp, shown) -> None:
    avail = QSize(800, 400)
    box = _box(PROSE, qapp, shown)
    label = _text_label(box)
    assert box.height() > avail.height() - MARGIN, "premise: Qt's box is too tall"

    fit.fit_message_box(box, avail, MARGIN)

    assert box.height() <= avail.height() - MARGIN
    assert box.width() <= avail.width() - 2 * fit.SIDE_MARGIN_PX
    assert _areas(box) == [], "widening sufficed; nothing should scroll"
    assert label.height() >= label.heightForWidth(label.width()), "text clipped"
    # Narrowest: a step narrower than the search's precision would not fit.
    label.setMinimumWidth(label.minimumWidth() - 2 * fit._WIDTH_SEARCH_PRECISION_PX)
    fit._let_qt_size(box)
    assert box.height() > avail.height() - MARGIN


def test_text_no_width_can_fit_scrolls_and_keeps_the_buttons(qapp, shown) -> None:
    avail = QSize(800, 400)
    box = _box(TOO_LONG, qapp, shown)
    label = _text_label(box)

    fit.fit_message_box(box, avail, MARGIN)
    _settle(qapp)

    areas = _areas(box)
    assert len(areas) == 1 and areas[0].widget() is label
    assert box.height() <= avail.height() - MARGIN
    assert box.width() <= avail.width() - 2 * fit.SIDE_MARGIN_PX
    assert label.wordWrap(), "an unwrapped label in the area would cut every line"
    assert label.height() >= label.heightForWidth(label.width()), "text clipped"
    bar = areas[0].verticalScrollBar()
    assert bar.maximum() > bar.minimum(), "the text is long enough to scroll"
    for button in box.findChildren(QPushButton):
        if button.isVisible():
            assert box.rect().contains(button.geometry()), button.text()
    assert areas[0].accessibleName(), "a screen reader needs a name for the area"


def test_the_scrolling_text_survives_qt_rebuilding_the_layout(qapp, shown) -> None:
    """Qt rebuilds a box's layout when its informative text changes and puts the
    label straight back into the grid. The unattended crash dialog changes it
    every second. Each rebuild must end with the text scrolling in ONE area, not
    an empty area left floating over a box taller than the screen.

    And a handle on the label taken before the rebuilds must still work after
    them: replacing the area instead of reusing it made PySide declare the
    (living) label deleted, which any code holding it would have crashed on.
    """
    avail = QSize(800, 400)
    box = _box(TOO_LONG, qapp, shown)
    box.setInformativeText("This closes by itself in 30 s.")
    _settle(qapp)
    fit.fit_message_box(box, avail, MARGIN)
    _settle(qapp)
    label = _text_label(box)
    assert len(_areas(box)) == 1
    the_area = _areas(box)[0]
    destroyed: list[str] = []
    the_area.destroyed.connect(lambda *_a: destroyed.append("area"))

    for seconds in (29, 28, 27):
        box.setInformativeText(f"This closes by itself in {seconds} s.")
        _settle(qapp)
        assert not destroyed, "the box's text area was deleted in a rebuild"
        areas = _areas(box)
        assert len(areas) == 1, f"{len(areas)} visible text areas after a rebuild"
        assert areas[0] is the_area, "a rebuild replaced the box's text area"
        assert _handle_works(label), "a live label's Python handle was invalidated"
        assert label is _text_label(box)
        assert label.parentWidget() is areas[0].viewport(), "the text left its area"
        assert label.isVisible()
        assert box.layout().indexOf(areas[0]) >= 0, "the area is not in the layout"
        assert box.height() <= avail.height() - MARGIN, box.size()
        assert label.height() >= label.heightForWidth(label.width()), "text clipped"
    assert len(box.findChildren(QScrollArea, fit.SCROLL_AREA_NAME)) == 1, (
        "a rebuild made a new area instead of reusing the box's own"
    )


def test_the_filter_sizes_a_box_before_it_places_it(qapp, shown) -> None:
    """The order that put a beta prompt's buttons below the screen.

    Without fitting first, the filter centred the box at Qt's 640-wide
    placeholder size (about 70 px tall) and the box then grew downward by its
    real height — so any box taller than half the screen ran off the bottom.
    """
    screen = qapp.primaryScreen()
    assert screen is not None
    avail = screen.availableGeometry()
    centring = DialogCenterFilter()
    qapp.installEventFilter(centring)
    try:
        box = message_boxes.build(
            QMessageBox.Icon.Question,
            None,
            "Update available",
            "Version 0.7.100b12 is available.\n\n" + PROSE,
        )
        box.show()
        _settle(qapp)
        shown.append(box)
    finally:
        qapp.removeEventFilter(centring)
    # The premise, measured rather than assumed (a first version of this test
    # used a box too short to overrun and passed with the fix reverted): taller
    # than half the screen plus the placeholder's half-height, so centring the
    # placeholder would have put its bottom past the screen's.
    assert box.height() > avail.height() // 2 + 40, (box.size(), avail)
    assert avail.contains(box.geometry()), (
        f"{box.geometry()} is not within the screen {avail}"
    )


def test_a_plain_dialog_is_only_ever_made_smaller(qapp) -> None:
    from PySide6.QtWidgets import QProgressDialog

    dialog = QProgressDialog("Downloading Platterpus 0.7.100b12…", "Cancel", 0, 100)
    try:
        dialog.resize(300, 80)
        fit_plain_dialog(dialog, QSize(800, 600), MARGIN)
        assert dialog.size() == QSize(300, 80)
        dialog.resize(1200, 900)
        fit_plain_dialog(dialog, QSize(800, 600), MARGIN)
        assert dialog.width() <= 800 - 2 * fit.SIDE_MARGIN_PX
        assert dialog.height() <= 600 - MARGIN
    finally:
        dialog.deleteLater()


def test_a_box_sized_for_a_long_title_keeps_a_side_margin(qapp, shown) -> None:
    """Qt widens a box to fit its title, up to the whole screen on one up to
    1024 px wide, so a box titled with a long path touched both edges of every
    small screen (KDD-41). Its title bar shows the title shortened instead; the
    whole title stays the box's accessible name, and a fit on a wider screen
    starts from the whole title again.
    """
    title = "Open " + "/home/maximilian-schwarzenegger-lindqvist/Music" * 4
    box = message_boxes.build(QMessageBox.Icon.Information, None, title, "Short.")
    box.show()
    _settle(qapp)
    shown.append(box)
    screen = box.screen().availableGeometry().size()
    assert screen.width() <= 1024, "premise: Qt's ceiling is the whole screen here"
    assert box.width() > screen.width() - 2 * fit.SIDE_MARGIN_PX, (
        "premise: Qt sized the box for its title, to the screen's edges"
    )

    fit.fit_message_box(box, screen, MARGIN)

    assert box.width() <= screen.width() - 2 * fit.SIDE_MARGIN_PX
    assert box.windowTitle() != title and "…" in box.windowTitle()
    assert box.windowTitle().startswith("Open /home/")
    assert box.accessibleName() == title
    # Qt sizes the box again on every Show and layout change; the shortened
    # title is an input to that, so the margin survives it.
    fit._let_qt_size(box)
    assert box.width() <= screen.width() - 2 * fit.SIDE_MARGIN_PX

    # A later fit for a screen with room for the whole title gives it back.
    fit.fit_message_box(box, QSize(4000, screen.height()), MARGIN)
    assert box.windowTitle() == title


def test_a_box_without_qts_label_is_left_alone(qapp, shown, caplog) -> None:
    """If Qt ever renames its label, the fit does nothing rather than something
    wrong, and says so in the log; the matrix then goes red on the real boxes."""
    box = _box(PROSE, qapp, shown)
    _text_label(box).setObjectName("renamed_by_a_future_qt")
    before = box.size()
    fit.fit_message_box(box, QSize(800, 400), MARGIN)
    assert box.size() == before
    assert "is left at Qt's own size" in caplog.text


def test_plaintext_survives_the_move_into_the_scroll_area(qapp, shown) -> None:
    """The label that moves is Qt's own, with the format `build` pinned."""
    box = _box("<b>not bold</b> " + TOO_LONG, qapp, shown)
    fit.fit_message_box(box, QSize(800, 400), MARGIN)
    label = _text_label(box)
    assert label.textFormat() == Qt.TextFormat.PlainText
    assert label.text().startswith("<b>not bold</b>")
