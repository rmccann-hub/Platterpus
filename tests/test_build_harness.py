"""Tests for the AppImage build harness.

The actual AppImage build needs Linux + python-appimage and is the
domain of T32's smoke test. Here we just verify the recipe directory
has the structure python-appimage expects and that the build script
references the right files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = REPO_ROOT / "build"
RECIPE_DIR = BUILD_DIR / "python-appimage"


def test_build_script_exists_and_is_executable() -> None:
    script = BUILD_DIR / "build_appimage.sh"
    assert script.is_file()
    # On POSIX, the executable bit must be set for `bash build/...` to
    # work without an explicit interpreter prefix.
    import os
    assert os.access(script, os.X_OK), (
        f"{script} is not executable; run chmod +x"
    )


def test_recipe_dir_has_required_files() -> None:
    expected = {"requirements.txt", "entrypoint", "whipper-gui.desktop"}
    actual = {p.name for p in RECIPE_DIR.iterdir() if p.is_file()}
    missing = expected - actual
    assert not missing, f"recipe missing: {missing}"


def test_entrypoint_is_executable() -> None:
    entrypoint = RECIPE_DIR / "entrypoint"
    assert entrypoint.is_file()
    import os
    assert os.access(entrypoint, os.X_OK)


def test_entrypoint_invokes_whipper_gui_module() -> None:
    """The entrypoint must run `python -m whipper_gui`."""
    text = (RECIPE_DIR / "entrypoint").read_text()
    assert "whipper_gui" in text
    assert "-m" in text  # invoking as a module


def test_desktop_file_has_correct_app_id() -> None:
    """The .desktop Exec/Icon fields must match the AppImage name."""
    text = (RECIPE_DIR / "whipper-gui.desktop").read_text()
    assert "[Desktop Entry]" in text
    assert "Exec=whipper-gui" in text
    assert "Icon=whipper-gui" in text
    assert "Type=Application" in text


def test_requirements_uses_find_links_for_local_wheel() -> None:
    """Self-install path: --find-links . + bare `whipper-gui` package."""
    lines = (RECIPE_DIR / "requirements.txt").read_text().splitlines()
    non_comment = [line.strip() for line in lines if not line.strip().startswith("#")]
    non_blank = [line for line in non_comment if line]
    assert "--find-links ." in non_blank
    assert "whipper-gui" in non_blank


def test_requirements_pins_match_dependencies_md() -> None:
    """Runtime dep pins in the recipe must match the source-of-truth."""
    text = (RECIPE_DIR / "requirements.txt").read_text()
    # Same constraints as pyproject.toml + DEPENDENCIES.md.
    assert "PySide6>=6.7,<7" in text
    assert "musicbrainzngs==0.7.1" in text
    assert "tomli-w>=1.0,<2" in text
