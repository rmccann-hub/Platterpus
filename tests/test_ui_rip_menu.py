"""The Rip menu and its Ctrl+R shortcut (UX review of 0.7.127, A2; TASKS R183).

Before this, only Alt+S (the Start button's mnemonic) started a rip, and the menu
bar had no Rip menu: File held "Rip as Unknown Album…" and Quit. These tests hold
the three properties the change is made of:

* **one predicate** — the menu's Start rip is enabled exactly when the button is,
  in every state the button has, because both are set from one value in
  ``RipControls._refresh_button_state``;
* **one handler** — triggering the action presses the button, so a disabled
  action, a click and Ctrl+R cannot start a rip three different ways;
* **a modified key nobody else holds** — Ctrl+R, never a bare character (WCAG
  2.1.4), and no other action in the window answers to it.

Plus the trap the shortcut opens: a menu shortcut moves no focus, so a title
still being typed into the track list would not be committed before the rip
read the table. Alt+S moves focus to the button, which commits it; the action
does the same.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from conftest import stop_window_threads
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QMainWindow, QMenu
from test_ui_main_window import _make_window

from platterpus.ui.rip_controls import START_RIP_SHORTCUT
from platterpus.workers.rip_worker import RipParameters


@pytest.fixture()
def teardown_threads(qapp: QApplication) -> Iterator[Callable[..., Any]]:
    """A real MainWindow, its threads stopped afterwards (as in
    `test_ui_main_window`, whose fixture is not shared through conftest)."""
    created: list[Any] = []

    def factory(**kwargs: Any) -> Any:
        window = _make_window(qapp, **kwargs)
        created.append(window)
        return window

    yield factory
    for window in created:
        stop_window_threads(window)
        window.deleteLater()


def _menu(window: QMainWindow, title: str) -> QMenu:
    """The menu-bar menu whose title is ``title`` (mnemonic included)."""
    for action in window.menuBar().actions():
        if action.text() == title:
            menu = action.menu()
            assert isinstance(menu, QMenu), f"{title!r} is not a menu"
            return menu
    raise AssertionError(
        f"no {title!r} menu; the bar has {[a.text() for a in window.menuBar().actions()]}"
    )


def _item(menu: QMenu, text: str) -> QAction:
    """The action labelled ``text`` in ``menu``."""
    for action in menu.actions():
        if action.text() == text:
            return action
    raise AssertionError(
        f"no {text!r} in the menu: {[a.text() for a in menu.actions()]}"
    )


def test_the_rip_menu_sits_between_file_and_tools_and_holds_both_rip_actions(
    teardown_threads: Callable[..., Any],
) -> None:
    window = teardown_threads()
    titles = [a.text() for a in window.menuBar().actions()]
    assert titles[:3] == ["&File", "R&ip", "&Tools"], titles
    rip_menu = _menu(window, "R&ip")
    start = _item(rip_menu, "&Start rip")
    unknown = _item(rip_menu, "Rip as &Unknown Album…")
    # The SAME QAction as File's: one slot and one rip-lock state, never two
    # kept in step by hand (the README still sends people to File for it).
    assert unknown is _item(_menu(window, "&File"), "Rip as &Unknown Album…")
    assert unknown in window._rip_locked_actions
    assert start.shortcut().matches(QKeySequence("Ctrl+R")) == (
        QKeySequence.SequenceMatch.ExactMatch
    )


def test_start_rip_is_enabled_exactly_when_the_button_is(
    teardown_threads: Callable[..., Any],
) -> None:
    """Every state the button has, the menu item has too — read off both."""
    window = teardown_threads()
    controls = window._rip_controls
    start = _item(_menu(window, "R&ip"), "&Start rip")
    states: list[bool] = []

    def check(why: str) -> None:
        assert start.isEnabled() == controls._start_button.isEnabled(), why
        assert start.toolTip() == controls._start_button.toolTip(), why
        states.append(start.isEnabled())

    check("no drive")
    controls.set_drive("/dev/sr0")
    check("a drive, no release")
    controls.set_release_id("mbid")
    check("a drive and a release")
    controls.set_scan_active(True)
    check("a disc scan holds the drive")
    controls.set_scan_active(False)
    controls.set_rip_active(True)
    check("a rip is running")
    controls.set_rip_active(False)
    check("the rip ended")
    # Floor: the walk saw both answers, so the equality was tested both ways.
    assert True in states and False in states, states


def test_start_rip_presses_the_button_and_a_disabled_one_does_nothing(
    teardown_threads: Callable[..., Any],
) -> None:
    window = teardown_threads()
    controls = window._rip_controls
    start = _item(_menu(window, "R&ip"), "&Start rip")
    emitted: list[RipParameters] = []
    controls.rip_requested.connect(emitted.append)

    start.trigger()  # no drive: disabled, so Qt does not even deliver it
    assert emitted == []
    # Straight to the handler too: the button it presses is disabled, so the
    # second guard holds even if something delivered the trigger anyway.
    controls._on_start_action()
    assert emitted == []

    controls.set_drive("/dev/sr0")
    controls.set_unknown_mode(True)
    start.trigger()
    assert len(emitted) == 1
    assert emitted[0].drive == "/dev/sr0" and emitted[0].unknown is True


def test_the_ready_tooltip_names_the_shortcut(
    teardown_threads: Callable[..., Any],
) -> None:
    window = teardown_threads()
    controls = window._rip_controls
    controls.set_drive("/dev/sr0")
    controls.set_unknown_mode(True)
    assert START_RIP_SHORTCUT in controls._start_button.toolTip()


def test_no_other_action_in_the_window_answers_to_the_start_shortcut(
    teardown_threads: Callable[..., Any],
) -> None:
    """Two actions on one key make Qt fire neither ("ambiguous shortcut")."""
    from conftest import window_menus

    window = teardown_threads()
    menus = window_menus(window)
    owners: set[str] = set()
    examined = 0

    def claims(action: QAction) -> bool:
        return any(
            sequence.matches(QKeySequence(START_RIP_SHORTCUT))
            == QKeySequence.SequenceMatch.ExactMatch
            for sequence in action.shortcuts()
        )

    try:
        for _where, menu in menus:
            for action in menu.actions():  # type: ignore[attr-defined]  # a QMenu
                examined += len(action.shortcuts())
                if claims(action):
                    owners.add(action.text())
    finally:
        for where, menu in menus:
            if where.startswith("album menu"):
                menu.deleteLater()  # type: ignore[attr-defined]  # built for us
    # Actions owned by widgets rather than menus are bindings too.
    owners |= {a.text() for a in window.findChildren(QAction) if claims(a)}
    # Floor: Quit, Settings, the User Guide and Start rip each carry one.
    assert examined >= 4, examined
    assert owners == {"&Start rip"}, owners


def test_ctrl_r_commits_a_track_title_still_being_typed(
    teardown_threads: Callable[..., Any], qapp: QApplication
) -> None:
    """The edit in the open cell is in the table when the rip reads it.

    Alt+S moves focus to the Start button, and leaving the cell commits it. A
    menu shortcut moves no focus, so without `_on_start_action`'s ``setFocus``
    the rip would read the title from before the edit.
    """
    window = teardown_threads()
    window.show()
    window.activateWindow()
    try:
        assert QTest.qWaitForWindowActive(window, 2000), "the window never activated"
        controls = window._rip_controls
        # Shown, so `showEvent` wired Start to a real rip: take that out and
        # listen instead, so nothing is ripped.
        controls.rip_requested.disconnect()
        emitted: list[RipParameters] = []
        controls.rip_requested.connect(emitted.append)
        controls.set_drive("/dev/sr0")
        controls.set_unknown_mode(True)
        window._track_table.set_placeholder_tracks(2)

        view = window._track_table._view
        title_cell = window._track_table._model.index(0, 2)
        view.setFocus()
        view.setCurrentIndex(title_cell)
        view.edit(title_cell)
        qapp.processEvents()
        editor = QApplication.focusWidget()
        assert isinstance(editor, QLineEdit), f"no cell editor open: {editor!r}"
        assert editor.text() == "Track 01"
        editor.setText("Typed, not yet committed")

        _item(_menu(window, "R&ip"), "&Start rip").trigger()
        qapp.processEvents()

        assert len(emitted) == 1
        assert window._track_table.tracks()[0].title == "Typed, not yet committed"
        assert QApplication.focusWidget() is controls._start_button
    finally:
        window.hide()
