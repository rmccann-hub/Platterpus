"""`tool_paths` is the ONE tool-search order, and each caller names only its directories.

TASKS row "Three copies of one tool-search order": the loop *PATH, then these
directories* existed in `tool_paths.resolve_tool`, `ctdb/decode._which` and
`drive_control._resolve`, in a module whose docstring says it exists so there
would be one; and `MetaflacAdapter` ran its binary bare, with no `~/.local/bin`
fallback at all. These tests hold the single implementation, the one directory
split that is deliberate (host force-stop tools never search `~/.local/bin`), and
the composition root's resolution of metaflac.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from platterpus import composition, drive_control, tool_paths
from platterpus.config import Config

_SRC = Path(__file__).resolve().parents[1] / "src" / "platterpus"


def _no_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """A desktop-launch PATH: nothing resolves through `shutil.which`."""
    monkeypatch.setattr(tool_paths.shutil, "which", lambda name: None)


def test_find_tool_searches_the_named_directories_in_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _no_path(monkeypatch)
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()
    (second / "flac").write_text("", encoding="utf-8")
    assert tool_paths.find_tool("flac", (str(first), str(second))) == str(
        second / "flac"
    )
    (first / "flac").write_text("", encoding="utf-8")
    assert tool_paths.find_tool("flac", (str(first), str(second))) == str(
        first / "flac"
    )
    # A directory, not a file, is not a tool.
    (first / "metaflac").mkdir()
    assert tool_paths.find_tool("metaflac", (str(first),)) is None


def test_absent_is_none_for_find_and_the_bare_name_for_resolve(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _no_path(monkeypatch)
    monkeypatch.setattr(tool_paths, "_FALLBACK_DIRS", (str(tmp_path),))
    assert tool_paths.find_tool("flac") is None
    assert tool_paths.resolve_tool("flac") == "flac"


def test_the_default_directories_are_read_at_call_time(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A default bound at definition time would ignore a replaced `_FALLBACK_DIRS`,
    and every test that relies on replacing it would then test the machine."""
    _no_path(monkeypatch)
    (tmp_path / "ffmpeg").write_text("", encoding="utf-8")
    monkeypatch.setattr(tool_paths, "_FALLBACK_DIRS", (str(tmp_path),))
    assert tool_paths.resolve_tool("ffmpeg") == str(tmp_path / "ffmpeg")


def test_there_is_one_search_loop() -> None:
    """The two former copies delegate: neither calls `shutil.which` any more.

    Scoped to the two modules the row named, which held copies of the SEARCH. The
    other `shutil.which` calls in `src/` ask "is it installed?", and those belong to
    the dependency subsystem (Critical rule #6), not to this module.
    """
    for relative in ("drive_control.py", "ctdb/decode.py"):
        tree = ast.parse((_SRC / relative).read_text(encoding="utf-8"))
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and node.attr == "which"
            and isinstance(node.value, ast.Name)
            and node.value.id == "shutil"
        ]
        assert not calls, f"{relative} searches for tools itself again"


def test_the_host_force_stop_tools_never_search_the_exported_tool_directory() -> None:
    """Critical rule #3's one exception kills the reader device-scoped on the HOST
    first. `~/.local/bin` is where distrobox-export puts CONTAINER tools, so a pkill,
    fuser or eject found there would not be the host's."""
    exported = str(Path.home() / ".local" / "bin")
    for dirs in (
        drive_control._HOST_TOOL_DIRS_PKILL,
        drive_control._HOST_TOOL_DIRS_FUSER,
        drive_control._HOST_TOOL_DIRS_EJECT,
    ):
        assert exported not in dirs and dirs, dirs
    # NON-TRIVIALITY: the one host tool that does live there when installed per user
    # still searches it, so the check above is a split and not a blanket omission.
    assert exported in drive_control._DISTROBOX_DIRS


def test_the_composition_root_resolves_metaflac_like_every_other_tool(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`MetaflacAdapter` ran its name bare, the one tool with no `~/.local/bin`
    fallback. The composition root resolves it; an absolute path is kept."""
    _no_path(monkeypatch)
    (tmp_path / "metaflac").write_text("", encoding="utf-8")
    monkeypatch.setattr(tool_paths, "_FALLBACK_DIRS", (str(tmp_path),))
    adapter = composition.build_metaflac(Config())
    assert adapter._binary == str(tmp_path / "metaflac")
    pinned = Config()
    pinned.metaflac_path = "/opt/custom/metaflac"
    assert composition.build_metaflac(pinned)._binary == "/opt/custom/metaflac"
