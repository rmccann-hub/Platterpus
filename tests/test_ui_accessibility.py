"""Tests for platterpus.ui.accessibility (the announce helper, UX gap #4)
plus the cross-widget keyboard-mnemonic regression checks.

The announce() helper is the one shared path every live status surface uses to
reach a screen reader without stealing focus, so its contract (never raises,
feature-detects, empty-message no-op) is pinned here; the per-surface wiring
(what announces, when, and how it's throttled) is tested beside each widget.
"""

from __future__ import annotations

import re

import pytest
from PySide6 import QtGui
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QWidget

from platterpus.ui.accessibility import announce
from platterpus.ui.drive_picker import DrivePicker
from platterpus.ui.rip_controls import RipControls
from platterpus.ui.rip_progress import RipProgress, status_phase_key

# --- announce() -------------------------------------------------------------


def test_announce_dispatches_for_a_real_widget(qapp: QApplication) -> None:
    """On this Qt (>= 6.8) the announcement event exists and dispatch succeeds
    — a no-op under the offscreen platform, but a real event send."""
    label = QLabel("status")
    assert announce(label, "Ripping track 1 of 14") is True


def test_announce_empty_message_is_a_noop(qapp: QApplication) -> None:
    label = QLabel("status")
    assert announce(label, "") is False


def test_announce_survives_a_qt_without_the_api(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Our PySide6 pin allows Qt < 6.8, where QAccessibleAnnouncementEvent
    doesn't exist — announce() must degrade to False, never raise."""
    monkeypatch.delattr(QtGui, "QAccessibleAnnouncementEvent")
    label = QLabel("status")
    assert announce(label, "hello") is False


# --- status_phase_key() -----------------------------------------------------


def test_status_phase_key_strips_the_numeric_tail() -> None:
    assert status_phase_key("Ripping track 3 of 14… 27%") == "Ripping track 3 of 14"
    assert status_phase_key("Reading disc TOC… 42% — about 3m left") == (
        "Reading disc TOC"
    )


def test_status_phase_key_track_change_is_a_new_key() -> None:
    """A new track must re-announce even though only a digit changed."""
    assert status_phase_key("Ripping track 3 of 14… 99%") != status_phase_key(
        "Ripping track 4 of 14… 0%"
    )


def test_status_phase_key_without_ellipsis_is_the_full_text() -> None:
    text = "Done — all 14 tracks verified, Test/Copy CRCs match"
    assert status_phase_key(text) == text
    assert status_phase_key("") == ""


# --- Main-window mnemonic uniqueness ----------------------------------------


class _FakeBackend:
    """DrivePicker only stores the backend at construction — no calls made."""


def _mnemonic_letters(widget: QWidget) -> list[str]:
    """Collect the Alt+<letter> mnemonics of every button under `widget`."""
    letters: list[str] = []
    for button in widget.findChildren(QPushButton):
        match = re.search(r"&(\w)", button.text())
        if match:
            letters.append(match.group(1).lower())
    return letters


def test_main_window_button_mnemonics_are_unique(qapp: QApplication) -> None:
    """Every prominent main-window button carries a mnemonic, and no two
    collide with each other or with the menu-bar mnemonics (File/Tools/Help
    hold F/T/H) — an ambiguous mnemonic only cycles focus instead of
    activating, which defeats the point (gap #4)."""
    from platterpus.config import Config

    picker = DrivePicker(_FakeBackend())  # type: ignore[arg-type]
    controls = RipControls(Config())
    progress = RipProgress()

    letters = (
        _mnemonic_letters(picker)
        + _mnemonic_letters(controls)
        + _mnemonic_letters(progress)
    )
    # Every one of the nine prominent buttons has a mnemonic…
    assert len(letters) == 9
    # …they are all distinct…
    assert len(set(letters)) == len(letters)
    # …and none shadows a menu-bar mnemonic.
    assert not set(letters) & {"f", "t", "h"}
