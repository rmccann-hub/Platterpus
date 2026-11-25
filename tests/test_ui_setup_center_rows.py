"""Setup & Updates as rows: status on the left, a normal-size button on the right.

UX review of 0.7.127, finding L2 (TASKS R183): eight full-width, 44 px buttons
stacked under their status lines, so nothing read as primary and the body needed
814 px — the window opened at 560 × 736 on an 800 px screen and still scrolled
67 px. These tests hold the redesign to what it promised:

* every button sits to the RIGHT of its section's status, in its own column, at
  its own width — not across the window;
* the window opens without scrolling on the 800 × 800 screen the test platform
  gives, and keeps not scrolling when a long dependency report lands after it
  opened (the window grows instead, `SetupCenterDialog._grow_to_fit`);
* the one button that commits (Add app shortcut) keeps the 44 px commit size,
  and every other button keeps the 24 px floor;
* every action is still there, by key, and still runs its own action.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from conftest import stop_window_threads
from PySide6.QtWidgets import QApplication, QGridLayout, QLabel, QPushButton
from test_ui_main_window import _make_window
from test_ui_message_box_conformance import _dependency_report_with_every_section

from platterpus.ui.dialogs.centering import CenteredDialog

#: Every action Setup & Updates offers, by its key. A row redesign that dropped
#: one would be a feature lost to a layout change.
_KEYS: frozenset[str] = frozenset(
    {
        "app_update",
        "ripper_update",
        "ripper_pick",
        "dep_check",
        "drive_setup",
        "drive_diagnose",
        "host_setup",
        "shortcut",
    }
)


@pytest.fixture()
def center(qapp: QApplication) -> Iterator[Any]:
    """Setup & Updates opened the way the menu opens it, closed afterwards."""
    window = _make_window(qapp)
    dialog = window.open_setup_center()
    for _ in range(5):
        qapp.processEvents()
    yield dialog
    dialog.close()
    dialog.deleteLater()
    window._setup_center = None
    stop_window_threads(window)
    window.deleteLater()


def _grid(dialog: Any) -> QGridLayout:
    grids = dialog._body_scroll.widget().findChildren(QGridLayout)
    assert len(grids) == 1, grids
    return grids[0]


def test_every_button_sits_right_of_its_status_at_its_own_width(center: Any) -> None:
    grid = _grid(center)
    assert set(center._buttons) == _KEYS
    for key, button in center._buttons.items():
        index = grid.indexOf(button)
        row, column, _rows, columns = grid.getItemPosition(index)
        assert (column, columns) == (1, 1), f"{key} spans {columns} from {column}"
        # The status beside it: the label in column 0 whose rows cover this one.
        beside = [
            grid.itemAt(i).widget()
            for i in range(grid.count())
            if isinstance(grid.itemAt(i).widget(), QLabel)
            and grid.getItemPosition(i)[1] == 0
            and grid.getItemPosition(i)[0]
            <= row
            < grid.getItemPosition(i)[0] + grid.getItemPosition(i)[2]
        ]
        assert len(beside) == 1, f"{key}: no single status beside it: {beside}"
        assert beside[0].geometry().right() < button.geometry().left(), key
        # Its own width, not the window's: the wall was eight window-wide buttons.
        assert button.width() < center.width() / 2, (key, button.width())


def test_it_opens_without_scrolling_and_stays_so_when_a_long_report_lands(
    center: Any, qapp: QApplication
) -> None:
    bar = center._body_scroll.verticalScrollBar()
    cap = center.screen().availableGeometry().height() - CenteredDialog.SCREEN_MARGIN_PX
    opened = center.height()
    # Floor: the window was NOT simply capped at the screen, where scrolling is
    # allowed, so "no scroll" below is a statement about the layout.
    assert opened < cap, (opened, cap)
    assert bar.maximum() == 0, f"scrolls {bar.maximum()} px at {center.size()}"

    center.show_dependency_check_finished(_dependency_report_with_every_section())
    for _ in range(5):
        qapp.processEvents()
    assert len(center._dependency_label.text()) > 200, "the long report did not land"
    assert center.height() > opened, "the window did not grow for the longer text"
    assert bar.maximum() == 0, f"scrolls {bar.maximum()} px at {center.size()}"


def test_only_the_committing_button_takes_the_commit_size(center: Any) -> None:
    heights = {key: b.height() for key, b in center._buttons.items()}
    assert heights["shortcut"] >= 44, heights
    assert all(h >= 24 for h in heights.values()), heights
    others = [h for key, h in heights.items() if key != "shortcut"]
    # Floor: the others are not all secretly 44 px, which would rebuild the wall.
    assert max(others) < 44, heights


def test_every_button_still_runs_its_own_action(qapp: QApplication) -> None:
    from platterpus.config import Config
    from platterpus.ui.dialogs.setup_center import SetupCenterDialog
    from platterpus.user_settings import SettingWrite

    ran: list[str] = []

    def record(key: str) -> Callable[[], object]:
        return lambda: ran.append(key)

    dialog = SetupCenterDialog(
        None,
        app_version="0.0.0",
        ripper_pin="0000000",
        ripper_version="0.0.0",
        approved_by_round=0,
        dependency_report=None,
        actions={key: record(key) for key in _KEYS},
        config=Config(),
        save_setting=lambda _f, _v: SettingWrite(True),
    )
    try:
        for key, button in dialog._buttons.items():
            assert isinstance(button, QPushButton)
            assert "&" in dialog._button_labels[key], f"{key} lost its mnemonic"
            button.click()
        assert sorted(ran) == sorted(_KEYS)
    finally:
        dialog.deleteLater()


def test_a_report_landing_as_the_window_opens_does_not_scroll(
    qapp: QApplication,
) -> None:
    """The conformance matrix's order: opened, and the report lands before Qt
    has had an event-loop turn. The body's layout still answers with the old
    text's height then, unless `_grow_to_fit` activates it first."""
    window = _make_window(qapp)
    dialog = window.open_setup_center()
    try:
        dialog.show_dependency_check_finished(_dependency_report_with_every_section())
        for _ in range(5):
            qapp.processEvents()
        bar = dialog._body_scroll.verticalScrollBar()
        cap = (
            dialog.screen().availableGeometry().height()
            - CenteredDialog.SCREEN_MARGIN_PX
        )
        assert dialog.height() < cap, "capped at the screen, so scrolling is allowed"
        assert bar.maximum() == 0, f"scrolls {bar.maximum()} px at {dialog.size()}"
    finally:
        dialog.close()
        dialog.deleteLater()
        window._setup_center = None
        stop_window_threads(window)
        window.deleteLater()


def test_the_drive_and_setup_rows_say_whether_anything_is_left_to_do(
    center: Any,
) -> None:
    """TASKS R248 (the owner, 2026-11-25, after reinstalling): the rows say,
    checked now, whether drive setup and setup have anything left to do, instead
    of leaving the user to rerun both to find out."""
    from platterpus import install_health

    window = center.parent()
    expected_drive = install_health.drive_setup_line(
        window._selected_drive_setup_facts()
    )
    assert center._offset_label.text().splitlines()[0] == expected_drive
    assert "Read offset:" in center._offset_label.text()
    assert center._setup_label.text()[:1] in {"✓", "⚠", "ⓘ"}
    assert "Installs the ripping tools" not in center._setup_label.text()

    # The Setup line moves with each dependency check that lands.
    center._setup_standing = lambda report: f"standing for {report!r}"
    center.refresh_dependencies("a report")
    assert center._setup_label.text() == "standing for 'a report'"
