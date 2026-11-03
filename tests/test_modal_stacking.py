"""A question is stacked above the window it blocks (TASKS R96).

The owner's report of 2026-10-28: *"a dialog or yes/no question can end up
behind a window that cannot be closed until the question is answered, which
locks the app."* An application-modal question blocks every other window of
ours, but Qt makes it the transient of its PARENT, and the transient is what a
desktop stacks by. Parented to the main window while the user was in another
window, it could sit under the window it had locked (`ui/dialogs/stacking.py`).

These read the transient parent off Qt's own window handle, which is what the
desktop is told. The offscreen platform has no window manager, so what a real
desktop then does with it is for the owner's machine to confirm.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QMessageBox, QWidget

from platterpus.ui import message_boxes
from platterpus.ui.dialogs.auto_center import DialogCenterFilter
from platterpus.ui.dialogs.centering import CenteredDialog


@pytest.fixture()
def centring_filter(qapp: QApplication) -> Iterator[DialogCenterFilter]:
    """The app-wide filter `app.main` installs, which places every dialog that
    is not a `CenteredDialog` (every `QMessageBox`)."""
    installed = DialogCenterFilter(qapp)
    qapp.installEventFilter(installed)
    yield installed
    qapp.removeEventFilter(installed)
    installed.deleteLater()


@pytest.fixture()
def main_window(qapp: QApplication) -> Iterator[QMainWindow]:
    """A shown, active main window; it and every dialog under it put away after."""
    window = QMainWindow()
    window.setWindowTitle("Platterpus")
    _activate(window)
    yield window
    for child in window.findChildren(QDialog):
        child.hide()
        child.deleteLater()
    window.hide()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def _activate(widget: QWidget) -> None:
    """Make ``widget`` the active window, as a click on it would."""
    widget.show()
    widget.raise_()
    widget.activateWindow()
    deadline = time.monotonic() + 5.0
    while QApplication.activeWindow() is not widget and time.monotonic() < deadline:
        QCoreApplication.processEvents()
    assert QApplication.activeWindow() is widget, "the window never became active"


def _settle() -> None:
    for _ in range(5):
        QCoreApplication.processEvents()


def _open_modal(parent: QWidget, title: str) -> QDialog:
    """An application-modal dialog over ``parent``, as the setup wizard is."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    dialog.show()
    _settle()
    assert QApplication.activeModalWidget() is dialog, "floor: no modal is up"
    return dialog


def _question(parent: QWidget) -> QMessageBox:
    """The box `message_boxes.question` builds, shown as its `exec()` shows it."""
    box = message_boxes.build(
        QMessageBox.Icon.Question, parent, "Replace the files?", "Yes or no?"
    )
    box.setWindowModality(Qt.WindowModality.ApplicationModal)
    return box


def _transient(widget: QWidget) -> object:
    handle = widget.windowHandle()
    assert handle is not None, "the dialog has no window"
    return handle.transientParent()


def test_a_question_over_a_modal_dialog_is_stacked_above_that_dialog(
    main_window: QMainWindow,
    centring_filter: DialogCenterFilter,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The owner's lock: a modal dialog is up, a question parented to the main
    window opens. It must be the transient of the dialog it blocks."""
    wizard = _open_modal(main_window, "Set up Platterpus")
    box = _question(main_window)
    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        box.show()
        _settle()
    assert QApplication.activeModalWidget() is box, "the question is not on top"
    assert _transient(box) is wizard.windowHandle(), (
        "the question is stacked by the main window, under the dialog it locks"
    )
    assert box.parentWidget() is main_window, "the owner must not change"
    assert "stacked above 'Set up Platterpus'" in caplog.text, caplog.text


def test_a_question_over_a_modeless_window_in_use_is_stacked_above_it(
    main_window: QMainWindow, centring_filter: DialogCenterFilter
) -> None:
    """Setup & Updates is modeless and was the window in use (the 2026-10-29
    report): the question that blocks it goes above it."""
    setup = QDialog(main_window)
    setup.setWindowTitle("Setup & Updates")
    _activate(setup)
    assert not setup.isModal()
    box = _question(main_window)
    box.show()
    _settle()
    assert _transient(box) is setup.windowHandle()


def test_with_its_own_window_in_use_a_question_keeps_its_transient(
    main_window: QMainWindow, centring_filter: DialogCenterFilter
) -> None:
    """The control: the main window is the window in use, so nothing moves."""
    box = _question(main_window)
    box.show()
    _settle()
    assert _transient(box) is main_window.windowHandle()


def test_a_window_modal_dialog_is_left_with_its_parent(
    main_window: QMainWindow, centring_filter: DialogCenterFilter
) -> None:
    """`open()` blocks the transient parent's chain only, so moving it would
    change WHICH windows it blocks; and the window above it still answers, so
    it cannot lock the app. It keeps its parent."""
    _open_modal(main_window, "Something else")
    box = message_boxes.build(QMessageBox.Icon.Information, main_window, "t", "x")
    box.open()
    _settle()
    assert box.windowModality() == Qt.WindowModality.WindowModal
    assert _transient(box) is main_window.windowHandle()


def test_the_question_is_stacked_again_on_every_show(
    main_window: QMainWindow, centring_filter: DialogCenterFilter
) -> None:
    """Qt puts the parent back as the transient on each show, and the window
    in use may be another one the second time."""
    first = _open_modal(main_window, "First")
    box = _question(main_window)
    box.show()
    _settle()
    assert _transient(box) is first.windowHandle()
    box.hide()
    first.hide()
    second = _open_modal(main_window, "Second")
    box.show()
    _settle()
    assert _transient(box) is second.windowHandle()


def test_a_centered_dialog_is_stacked_without_the_app_filter(
    main_window: QMainWindow,
) -> None:
    """`CenteredDialog` stacks itself, so it holds where the filter is not
    installed (and the filter skips placing it)."""
    wizard = _open_modal(main_window, "Set up Platterpus")
    picker = CenteredDialog(main_window)
    picker.setWindowTitle("Choose a release")
    picker.setWindowModality(Qt.WindowModality.ApplicationModal)
    picker.show()
    _settle()
    assert _transient(picker) is wizard.windowHandle()


#: Window flags that ask the desktop to keep a window above windows it does not
#: belong to, or to stack it outside the desktop's rules altogether.
_ABOVE_EVERYTHING: tuple[str, ...] = (
    "WindowStaysOnTopHint",
    "X11BypassWindowManagerHint",
    "BypassWindowManagerHint",
)


def test_no_window_of_ours_asks_to_stay_above_unrelated_windows() -> None:
    """R96 (2): a dialog that is not a question should not stay above windows
    it has nothing to do with. Ours stay above their own parent only, which is
    what a transient is; a flag like these would put one above everything."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src" / "platterpus"
    files = sorted(src.rglob("*.py"))
    assert len(files) >= 100, f"floor: only {len(files)} modules read"
    found = [
        f"{path.relative_to(src).as_posix()}:{number}: {flag}"
        for path in files
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        for flag in _ABOVE_EVERYTHING
        if flag in line and not line.lstrip().startswith("#")
    ]
    assert found == [], found
