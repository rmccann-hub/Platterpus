"""Tests for the Help menu's About and User Guide dialogs."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from whipper_gui import __version__, help_content
from whipper_gui.ui.help_dialogs import AboutDialog, HelpDialog


def test_user_guide_content_is_substantive() -> None:
    guide = help_content.USER_GUIDE
    assert guide.strip().startswith("#")  # Markdown heading
    # Covers the key tasks the user needs.
    for topic in ("Start rip", "Force stop", "Unknown Album", "Settings"):
        assert topic in guide
    assert help_content.REPO_URL.startswith("https://")


def test_about_dialog_shows_version_and_paths(qapp: QApplication) -> None:
    dialog = AboutDialog(whipper_path="/home/me/.local/bin/whipper")
    assert dialog.windowTitle() == "About Whipper GUI"
    md = AboutDialog._build_markdown("/home/me/.local/bin/whipper")
    assert __version__ in md
    assert "/home/me/.local/bin/whipper" in md
    assert help_content.REPO_URL in md
    assert "Python:" in md and "Qt:" in md


def test_about_dialog_constructs_without_whipper_path(qapp: QApplication) -> None:
    # Falls back to the default whipper path; must not raise.
    dialog = AboutDialog()
    assert dialog.windowTitle() == "About Whipper GUI"


def test_help_dialog_constructs(qapp: QApplication) -> None:
    dialog = HelpDialog()
    assert "User Guide" in dialog.windowTitle()
