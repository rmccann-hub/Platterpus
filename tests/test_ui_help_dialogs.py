"""Tests for the Help menu's About and User Guide dialogs."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from platterpus import __version__, help_content
from platterpus.ui.help_dialogs import AboutDialog, HelpDialog


def test_user_guide_content_is_substantive() -> None:
    guide = help_content.USER_GUIDE
    assert guide.strip().startswith("#")  # Markdown heading
    # Covers the key tasks the user needs.
    for topic in ("Start rip", "Force stop", "Unknown Album", "Settings"):
        assert topic in guide
    assert help_content.REPO_URL.startswith("https://")


def test_about_dialog_shows_version_and_paths(qapp: QApplication) -> None:
    dialog = AboutDialog()
    assert dialog.windowTitle() == "About Platterpus"
    md = AboutDialog._build_markdown()
    assert __version__ in md
    assert "cyanrip binary:" in md
    assert help_content.REPO_URL in md
    assert "Python:" in md and "Qt:" in md


def test_help_dialog_constructs(qapp: QApplication) -> None:
    dialog = HelpDialog()
    assert "User Guide" in dialog.windowTitle()
