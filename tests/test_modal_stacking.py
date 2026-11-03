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
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from unittest import mock

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


# --- Every modal path, opened over another window (TASKS R96) ---------------
#
# The row's test: open each modal path over another modal window and check the
# newest is on top and answerable. The population is the UI conformance matrix's,
# derived from the source there, so a new dialog or box is opened here the day it
# lands:
#
# * every `CenteredDialog` subclass (`test_ui_conformance._factories`, held equal
#   to `MEASURED`, which that file holds equal to the source), parented to the main
#   window and opened the way `exec()` opens it;
# * every routed message box (`message_boxes.<kind>(...)`, found by walking the
#   AST), built as the call builds it;
# * every function that builds a box or a Qt dialog itself, driven through the
#   REAL code path by its scenario, with `exec()`/`open()` replaced by the check.
#
# Each is opened twice: over an application-modal dialog (the setup wizard's
# shape) and over a modeless window in use (Setup & Updates'). Not covered, said
# rather than implied: Qt's own file dialog, which the desktop usually draws.


@dataclass(frozen=True)
class _Opened:
    """What one dialog looked like when opened over another window."""

    modality: Qt.WindowModality
    on_top: bool  # the newest modal: Qt delivers its input, so it is answerable
    shown: bool
    stacked_over_modal: bool  # transient of the modal dialog underneath
    stacked_over_window_in_use: bool  # transient of the modeless window in use


def _open_over_others(main: QWidget, widget: QDialog) -> _Opened:
    """Open ``widget`` over a modal dialog, then over a modeless window in use."""
    readings: list[tuple[bool, bool, bool]] = []
    for kind in ("modal", "modeless"):
        under = QDialog(main)
        under.setWindowTitle(f"the {kind} window underneath")
        if kind == "modal":
            under.setWindowModality(Qt.WindowModality.ApplicationModal)
            under.show()
            _settle()
            assert QApplication.activeModalWidget() is under, "floor: no modal is up"
        else:
            _activate(under)
        widget.show()
        _settle()
        handle = widget.windowHandle()
        readings.append(
            (
                QApplication.activeModalWidget() is widget,
                widget.isVisible(),
                handle is not None and handle.transientParent() is under.windowHandle(),
            )
        )
        widget.hide()
        under.hide()
        under.deleteLater()
        _settle()
    (modal_top, modal_shown, over_modal), (_, _, over_in_use) = readings
    return _Opened(
        modality=widget.windowModality(),
        on_top=modal_top,
        shown=modal_shown,
        stacked_over_modal=over_modal,
        stacked_over_window_in_use=over_in_use,
    )


@contextmanager
def _opened_instead_of_waited(
    main: QWidget, results: dict[str, _Opened], current: list[str]
) -> Iterator[None]:
    """`exec()` and `open()` open the dialog over other windows, then return
    as if it were closed; a dialog the code only `show()`s is handed over by the
    scenario itself (`_MEASURE_SHOWN`) and opened with its own modality."""
    import test_ui_message_box_conformance as boxes

    def record(widget: QDialog, modality: Qt.WindowModality | None) -> None:
        if modality is not None:
            widget.setWindowModality(modality)
        key, number = current[0], 2
        while key in results:
            key, number = f"{current[0]}#{number}", number + 1
        results[key] = _open_over_others(main, widget)

    def fake_exec(self: QDialog) -> int:
        # What `exec()` does: application-modal unless the caller chose.
        modal = self.windowModality()
        record(self, None if modal != Qt.WindowModality.NonModal else _APP_MODAL)
        return 0

    def fake_open(self: QDialog) -> None:
        record(self, Qt.WindowModality.WindowModal)  # what `open()` does

    saved = boxes._MEASURE_SHOWN[0]
    boxes._MEASURE_SHOWN[0] = lambda widget: record(widget, None)  # type: ignore[arg-type]  # a QDialog
    try:
        with (
            mock.patch.object(QMessageBox, "exec", fake_exec),
            mock.patch.object(QMessageBox, "open", fake_open),
            mock.patch.object(QDialog, "exec", fake_exec),
            mock.patch.dict(os.environ, {"APPIMAGE": boxes.LONG_APPIMAGE}),
        ):
            yield
    finally:
        boxes._MEASURE_SHOWN[0] = saved


_APP_MODAL: Final[Qt.WindowModality] = Qt.WindowModality.ApplicationModal


def _every_modal_path(main: QWidget, tmp: Path) -> dict[str, _Opened]:
    """Open every dialog in the three populations over other windows."""
    import test_ui_conformance as matrix
    import test_ui_message_box_conformance as boxes

    icons = {
        "warning": QMessageBox.Icon.Warning,
        "information": QMessageBox.Icon.Information,
        "critical": QMessageBox.Icon.Critical,
        "question": QMessageBox.Icon.Question,
    }
    results: dict[str, _Opened] = {}
    factories = matrix._factories()
    assert set(factories) == matrix.MEASURED, "the dialog population drifted"
    for name, make in factories.items():
        dialog = make()  # type: ignore[operator]  # factories are callables
        dialog.setParent(main, dialog.windowFlags())  # as production parents it
        dialog.setWindowModality(_APP_MODAL)  # as `exec()` opens it
        results[f"dialog {name}"] = _open_over_others(main, dialog)
        dialog.deleteLater()
    for box in boxes.routed_boxes():
        built = message_boxes.build(icons[box.kind], main, box.title, box.text)  # type: ignore[arg-type]  # the evaluated text is a str
        built.setWindowModality(_APP_MODAL)  # as `_run_modal`'s `exec()` opens it
        results[f"routed {box.key}"] = _open_over_others(main, built)
        built.deleteLater()
    current = ["?"]
    with _opened_instead_of_waited(main, results, current):
        for name, run in boxes._scenarios(main, tmp).items():
            current[0] = f"scenario {name}"
            run()
            assert current[0] in results, f"scenario {name!r} opened no dialog"
    return results


def _restore_the_real_message_boxes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Undo conftest's non-blocking answers for this test only.

    `conftest._non_blocking_message_boxes` replaces `message_boxes`' four
    functions with a bare answer, so a scenario that reaches one would build no
    box at all and this test would see nothing. The functions put back are the
    module's own, from a fresh load of its source, so the box is built and
    `exec()`ed exactly as production does; `exec()` itself is what the test
    replaces.
    """
    import importlib.util

    spec = importlib.util.find_spec("platterpus.ui.message_boxes")
    assert spec is not None and spec.loader is not None
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    for name in ("information", "warning", "critical", "question"):
        monkeypatch.setattr(message_boxes, name, getattr(fresh, name))


def test_every_modal_path_opens_on_top_of_another_window(
    qapp: QApplication,
    centring_filter: DialogCenterFilter,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each dialog, opened over a modal dialog and over a modeless window in
    use, is the newest modal (answerable) and shown; an application-modal one
    is stacked above whichever window it opened over. A window-modal one keeps
    its parent (`stacking.py` says why), and is still the newest modal."""
    import test_ui_conformance as matrix
    import test_ui_message_box_conformance as boxes
    from conftest import stop_window_threads

    _restore_the_real_message_boxes(monkeypatch)
    main = matrix._main_window()
    assert isinstance(main, QMainWindow)
    _activate(main)
    try:
        results = _every_modal_path(main, tmp_path)
    finally:
        main.hide()
        stop_window_threads(main)
        main.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    # Floors: a population that shrank to nothing would pass every check below.
    dialogs = [k for k in results if k.startswith("dialog ")]
    routed = [k for k in results if k.startswith("routed ")]
    scenarios = [k for k in results if k.startswith("scenario ")]
    assert len(dialogs) == len(matrix.MEASURED) >= 16, dialogs
    assert len(routed) >= boxes.MIN_ROUTED_BOXES, len(routed)
    # Measured 2026-11-03 (PySide6 6.11): 16 dialogs, 40 routed boxes, 53
    # scenarios; 74 application-modal, 33 window-modal (the cyanrip offers,
    # opened with `open()`), 2 modeless (the update's progress window).
    assert len(scenarios) >= 50, len(scenarios)
    app_modal = {k: v for k, v in results.items() if v.modality == _APP_MODAL}
    assert len(app_modal) >= 70, f"only {len(app_modal)} application-modal paths"
    window_modal = {
        k: v for k, v in results.items() if v.modality == Qt.WindowModality.WindowModal
    }
    assert len(window_modal) >= 30, f"only {len(window_modal)} window-modal paths"

    # A modeless dialog (the update's progress window) is in no modal stack, so
    # "the newest modal" is not a question it can answer; it must be shown.
    not_on_top = sorted(
        k
        for k, v in results.items()
        if not v.shown or (v.modality != Qt.WindowModality.NonModal and not v.on_top)
    )
    assert not_on_top == [], f"not the newest window, or not shown: {not_on_top}"
    hidden = sorted(
        k
        for k, v in app_modal.items()
        if not (v.stacked_over_modal and v.stacked_over_window_in_use)
    )
    assert hidden == [], f"stacked under the window they block: {hidden}"
    # Asserted at the section, not inherited: a window-modal dialog blocks its
    # transient parent's chain, so restacking it would change what it blocks.
    moved = sorted(k for k, v in window_modal.items() if v.stacked_over_modal)
    assert moved == [], f"window-modal dialogs restacked: {moved}"
