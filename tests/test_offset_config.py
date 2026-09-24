"""Tests for platterpus.offset_config.

Since 2026-09-24 the module reads no file at all: the read offset lives in
Platterpus's own config and nowhere else. The leftover config folder of the
ripper older versions drove is still REMOVED by the uninstaller, and the sweep at
the bottom holds everything else to not reading it.
"""

from __future__ import annotations

import ast
from pathlib import Path

from platterpus.offset_config import describe_applied_offset, is_offset_configured

_SRC = Path(__file__).resolve().parents[1] / "src" / "platterpus"


def test_is_configured_follows_the_override_alone() -> None:
    # Regression: a leftover offset in another program's config must NOT satisfy
    # the gate — it never reaches cyanrip's -s, so counting it as "configured"
    # made the rip preflight skip auto-apply + the wizard and rip at offset 0.
    # Only the GUI override (which is what cyanrip actually gets) configures it.
    assert is_offset_configured(True) is True
    assert is_offset_configured(False) is False


def test_describe_applied_offset_says_what_the_next_rip_does() -> None:
    assert describe_applied_offset(667, True) == "+667 samples, applied to every rip"
    assert describe_applied_offset(-6, True) == "-6 samples, applied to every rip"
    off = describe_applied_offset(667, False)
    assert "not applied" in off and "+667" not in off


def test_the_module_does_no_io() -> None:
    """It used to read a file; nothing here may open one again."""
    tree = ast.parse((_SRC / "offset_config.py").read_text(encoding="utf-8"))
    names = {
        node.attr if isinstance(node, ast.Attribute) else node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute | ast.Name)
    }
    assert not names & {"open", "read_text", "read_bytes", "Path"}, names


def test_only_the_uninstaller_refers_to_the_leftover_config_folder() -> None:
    """Nothing reads the old ripper's config folder; the uninstaller removes it.

    Derived from the tree, so a new reader anywhere in the package fails here by
    name. `paths.py` defines the constant; `deps/host_teardown.py` removes it.
    """
    users = sorted(
        str(path.relative_to(_SRC))
        for path in _SRC.rglob("*.py")
        if "LEGACY_RIPPER_CONFIG_DIR" in path.read_text(encoding="utf-8")
    )
    assert users == ["deps/host_teardown.py", "paths.py"], users
