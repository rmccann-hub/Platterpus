"""A question nobody is waiting on waits for the main window (TASKS R96).

The owner's report of 2026-10-29: on 0.7.114 the album picker opened by itself
over Tools → Setup & Updates…, while they were using it. Their rule: *"if they
need to pop up, sure, but if they can hold, then hold them."* The picker can hold,
so it waits until the main window is the one in use, then opens, if it is still
wanted (`ui/hold_for_user.py`, `ui/main_window_picker.py`).

These drive the real window and the real Setup & Updates window, which is
modeless, as the owner's was: a check for a modal dialog alone would not have
held the picker they saw.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from conftest import stop_window_threads
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QDialog, QWidget
from test_ui_main_window import _make_window

from platterpus.adapters.musicbrainz_client import ReleaseSummary
from platterpus.ui import hold_for_user
from platterpus.ui.release_picker import ReleasePickerDialog

_DISC = "pNtImOkdBm9RMBIalzx0w9cfsYY-"

_RELEASES = [
    ReleaseSummary(
        mbid=f"aaaaaaaa-0000-0000-0000-00000000000{n}",
        title=f"Candidate {n}",
        artist_credit="The Police",
        date="2003",
        country="GB",
        track_count=14,
    )
    for n in (1, 2)
]


@pytest.fixture()
def make_window(qapp: QApplication) -> Iterator[Callable[..., Any]]:
    """A real MainWindow, its threads stopped afterwards (as `teardown_threads`)."""
    created: list[Any] = []

    def factory(**kwargs: Any) -> Any:
        window = _make_window(qapp, **kwargs)
        created.append(window)
        return window

    yield factory
    for window in created:
        for child in window.findChildren(QDialog):
            child.close()
        stop_window_threads(window)
        window.deleteLater()


@pytest.fixture()
def pickers(monkeypatch: pytest.MonkeyPatch) -> list[ReleasePickerDialog]:
    """Every release picker that opened; each is cancelled at once."""
    opened: list[ReleasePickerDialog] = []

    def _fake_exec(self: ReleasePickerDialog) -> int:
        opened.append(self)
        return int(QDialog.DialogCode.Rejected)

    monkeypatch.setattr(ReleasePickerDialog, "exec", _fake_exec)
    return opened


def _activate(widget: QWidget) -> None:
    """Make ``widget`` the active window, as a click on it would."""
    widget.show()
    widget.raise_()
    widget.activateWindow()
    deadline = time.monotonic() + 5.0
    while QApplication.activeWindow() is not widget and time.monotonic() < deadline:
        QCoreApplication.processEvents()
    assert QApplication.activeWindow() is widget, "the window never became active"


def _wait(seconds: float) -> None:
    """Let the event loop run, retry timers included, for ``seconds``."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)


def test_the_picker_waits_while_setup_and_updates_is_in_use(
    make_window: Callable[..., Any],
    pickers: list[ReleasePickerDialog],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The owner's case: Setup & Updates is open and in use when the lookup lands.

    The picker does not open over it; it opens once the owner is back on the main
    window. The control is the main window in use: the picker opens at once."""
    window = make_window()
    window._current_disc_id = _DISC
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    assert not setup.isModal(), "Setup & Updates is modeless; the test needs that"

    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        window._on_mb_releases(_DISC, _RELEASES)
        _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert pickers == [], "the picker opened over Setup & Updates"
    assert "held until the main window is in use" in caplog.text, caplog.text
    assert window._mb_picker_held_for == _DISC

    setup.close()
    _activate(window)
    _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert len(pickers) == 1, "the held picker never opened"
    assert window._mb_picker_held_for == ""


def test_the_picker_opens_at_once_when_the_main_window_is_in_use(
    make_window: Callable[..., Any], pickers: list[ReleasePickerDialog]
) -> None:
    """The control for the test above: nothing else of ours in use, no wait."""
    window = make_window()
    window._current_disc_id = _DISC
    _activate(window)
    window._on_mb_releases(_DISC, _RELEASES)
    assert len(pickers) == 1


def test_the_script_console_does_not_hold_the_picker(
    make_window: Callable[..., Any], pickers: list[ReleasePickerDialog]
) -> None:
    """An acceptance run keeps the script console active by design, and its
    `pick-release` answers the picker: holding it there would stall the run."""
    window = make_window()
    window._current_disc_id = _DISC
    console = window.open_script_console()
    _activate(console)
    window._on_mb_releases(_DISC, _RELEASES)
    assert len(pickers) == 1


def test_a_modal_dialog_holds_the_picker(qapp: QApplication) -> None:
    """A modal dialog of ours is busy even when no window is active."""
    main = QWidget()
    modal = QDialog()
    modal.setWindowTitle("Some question")
    modal.setModal(True)
    modal.show()
    try:
        QCoreApplication.processEvents()
        assert "a dialog is open ('Some question')" == hold_for_user.busy_reason(main)
    finally:
        modal.close()
        QCoreApplication.processEvents()
    assert QApplication.activeModalWidget() is not modal


def test_a_held_picker_for_a_disc_that_left_is_dropped(
    make_window: Callable[..., Any],
    pickers: list[ReleasePickerDialog],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Checked when it would open, not when it was held: a different disc in the
    drive by then means the picker is not shown, and the hold is forgotten so the
    disc's next lookup can ask."""
    window = make_window()
    window._current_disc_id = _DISC
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    window._on_mb_releases(_DISC, _RELEASES)
    assert window._mb_picker_held_for == _DISC

    window._current_disc_id = "another-disc-id"
    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert "no longer wanted, not opened" in caplog.text, caplog.text
    assert window._mb_picker_held_for == ""
    setup.close()
    _activate(window)
    _wait(3 * hold_for_user.RETRY_MS / 1000)
    assert pickers == []


def test_one_held_picker_per_disc(
    make_window: Callable[..., Any],
    pickers: list[ReleasePickerDialog],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A second lookup for a disc whose picker is waiting is declined, as it is
    while the picker is open: two would ask the same question twice."""
    window = make_window()
    window._current_disc_id = _DISC
    _activate(window)
    setup = window.open_setup_center()
    _activate(setup)
    window._on_mb_releases(_DISC, _RELEASES)
    with caplog.at_level(logging.INFO, logger="platterpus.ui"):
        window._on_mb_releases(_DISC, _RELEASES)
    assert "not holding a second one" in caplog.text, caplog.text

    setup.close()
    _activate(window)
    _wait(4 * hold_for_user.RETRY_MS / 1000)
    assert len(pickers) == 1
