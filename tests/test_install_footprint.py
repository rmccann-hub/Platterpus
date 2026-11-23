"""The ONE list of what Platterpus creates (deps/install_footprint.py) is complete.

TASKS R190: the uninstaller missed the fork's build cache, the container image,
the rig folders, Picard's data and interrupted downloads, because nothing held
its list to the code that writes. These tests do, three ways:

1. **Run the writers we can run** (AppImage integration, ``install-appimage.sh``)
   into a fake home, and require the scan to find every file they made.
2. **Compare the constants** the other writers use (the fork's source folder, the
   updater's partial download, the rig folder, the exports, Picard) with the list.
3. **A sweep of every module that names the home folder**, each declared with the
   footprint items that cover what it writes, or why it only reads. A new module
   that reaches into ``$HOME`` fails here until someone answers that question.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
from pathlib import Path

import pytest

from platterpus import appimage_integration, update_install
from platterpus.deps import fork_source, host_setup, registry
from platterpus.deps.host_teardown import HostTeardown
from platterpus.deps.install_footprint import (
    EXPORTED_BINARIES,
    LEGACY_APP_SLUG,
    PARTIAL_DOWNLOADS,
    PICARD_APP_ID,
    Group,
    Kind,
    footprint,
)
from platterpus.deps.user_locations import (
    Locations,
    desktop_folder_from_user_dirs,
    dev_checkout_venv,
    rips_setting,
    safe_rips_folder,
)
from platterpus.paths import DEFAULT_OUTPUT_DIR, LEGACY_RIPPER_CONFIG_DIR
from platterpus.test_session import RIG_PARENT_NAME

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src" / "platterpus"


class _NoCommands:
    def which(self, name: str) -> bool:
        return False

    def run(self, argv: list[str], timeout: float = 60.0) -> tuple[int, str]:
        raise AssertionError(f"no command expected: {argv}")


def _loc(home: Path) -> Locations:
    return Locations(
        home, home / ".config", home / ".local" / "share", home / "Desktop"
    )


def _found(home: Path) -> set[str]:
    engine = HostTeardown(runner=_NoCommands(), locations=_loc(home))
    return {thing for obs in engine.scan() if obs.removable for thing in obs.present}


def _files_under(home: Path) -> set[str]:
    return {str(p) for p in home.rglob("*") if p.is_file() or p.is_symlink()}


def _covered(path: str, found: set[str]) -> bool:
    return any(path == f or path.startswith(f"{f}/") for f in found)


# --- 1. Run the writers ----------------------------------------------------------


def test_everything_appimage_integration_writes_is_found(tmp_path: Path) -> None:
    home = tmp_path / "home"
    loc = _loc(home)
    loc.desktop_folder.mkdir(parents=True)
    app_dir = tmp_path / "appdir"
    (app_dir / "usr/share/icons/hicolor/256x256/apps").mkdir(parents=True)
    icon = app_dir / f"{appimage_integration.DESKTOP_ID}.png"
    icon.write_bytes(b"png")
    appimage = home / "Applications" / appimage_integration.CANONICAL_APPIMAGE_NAME
    appimage.parent.mkdir(parents=True)
    appimage.write_text("#!/bin/sh\n")
    before = _files_under(home)

    appimage_integration.integrate(
        appimage,
        app_dir=app_dir,
        desktop_dir=loc.data_home / "applications",
        icon_dir=loc.data_home / "icons",
        desktop_folder=loc.desktop_folder,
        refresh=lambda: None,
    )

    written = _files_under(home) - before
    assert len(written) >= 3, written  # menu entry, uninstall entry, shortcut
    found = _found(home)
    missed = sorted(p for p in written | {str(appimage)} if not _covered(p, found))
    assert not missed, f"integration writes what the uninstaller cannot find: {missed}"


def test_everything_install_appimage_sh_writes_is_found(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    appimage = tmp_path / appimage_integration.CANONICAL_APPIMAGE_NAME
    appimage.write_text("#!/bin/sh\necho fake\n")
    appimage.chmod(0o755)
    env = {**os.environ, "HOME": str(home), "XDG_DATA_HOME": str(home / ".local/share")}
    result = subprocess.run(
        ["bash", str(REPO / "install-appimage.sh"), str(appimage)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    written = _files_under(home)
    assert len(written) >= 3, written
    found = _found(home)
    missed = sorted(p for p in written if not _covered(p, found))
    assert not missed, (
        f"install-appimage.sh writes what the uninstaller misses: {missed}"
    )


# --- 2. The constants other writers use ------------------------------------------


def _items(home: Path, **kwargs: object) -> dict[str, object]:
    return {i.item_id: i for i in footprint(_loc(home), **kwargs)}  # type: ignore[arg-type]


def test_the_fork_build_cache_is_listed(tmp_path: Path) -> None:
    cache = _items(tmp_path)["cache"]
    source = tmp_path / fork_source.FORK_SOURCE_SUBPATH
    assert source.is_relative_to(cache.path)  # type: ignore[attr-defined]


def test_both_partial_downloads_are_listed() -> None:
    updater = Path(update_install.__file__).read_text(encoding="utf-8")
    installer = (REPO / "install.sh").read_text(encoding="utf-8")
    assert f'"{PARTIAL_DOWNLOADS[0]}"' in updater
    assert f"/{PARTIAL_DOWNLOADS[1]}" in installer


def test_the_rig_folder_and_older_session_folders_are_listed(tmp_path: Path) -> None:
    items = _items(tmp_path)
    assert items["rig"].pattern == f"{RIG_PARENT_NAME}*"  # type: ignore[attr-defined]
    assert items["rig"].group is Group.LOGS  # type: ignore[attr-defined]


def test_every_binary_setup_exports_is_listed() -> None:
    source = Path(host_setup.__file__).read_text(encoding="utf-8")
    exported = set(re.findall(r'"/usr/bin/([a-z-]+)"', source))
    assert {"cyanrip", "flac", "metaflac", "cd-paranoia"} <= exported
    assert exported <= set(EXPORTED_BINARIES), exported - set(EXPORTED_BINARIES)


def test_picard_and_the_image_are_the_ones_setup_installs(tmp_path: Path) -> None:
    items = _items(tmp_path)
    picard_spec = next(s for s in registry.SPECS if s.dep_id == "picard")
    assert any(PICARD_APP_ID in word for word in picard_spec.install_command)
    assert items["image"].name == host_setup.DEFAULT_IMAGE  # type: ignore[attr-defined]


def test_older_version_names_are_derived_not_spelled() -> None:
    assert LEGACY_APP_SLUG == f"{LEGACY_RIPPER_CONFIG_DIR.name}-gui"
    text = (SRC / "deps" / "install_footprint.py").read_text(encoding="utf-8")
    assert ("whip" + "per") not in text.lower()


def test_removal_order_and_the_last_items(tmp_path: Path) -> None:
    ids = [i.item_id for i in footprint(_loc(tmp_path), venv=tmp_path / ".venv")]
    assert len(ids) == len(set(ids)), "item ids must be unique"
    order = {item_id: n for n, item_id in enumerate(ids)}
    assert order["container"] < order["image"]
    assert order["picard"] < order["picard:runtime"] < order["picard:remote"]
    assert order["cli_link"] < order["venv"]
    assert ids[-2:] == ["settings", "logs"]
    logs = footprint(_loc(tmp_path))[-1]
    assert logs.keep_on_failure and logs.kind is Kind.TREE


def test_rips_and_packages_only_appear_when_given(tmp_path: Path) -> None:
    plain = _items(tmp_path)
    assert "rips" not in plain
    assert not any(k.startswith("package:") for k in plain)
    given = _items(tmp_path, rips=tmp_path / "rips", system_packages=("podman",))
    assert given["rips"].group is Group.RIPS  # type: ignore[attr-defined]
    assert given["package:podman"].group is Group.SYSTEM_PACKAGES  # type: ignore[attr-defined]


# --- 3. Every module that names the home folder ---------------------------------

#: Module -> what it writes under $HOME and the footprint items that cover it, or
#: why it only reads. Measured 2026-11-23 (TASKS R190). A NEW module reaching
#: into $HOME fails the sweep until it is added here with its answer.
_HOME_REFERENCES: dict[str, str] = {
    "paths.py": "defines settings, logs, exports and the default rips folder: settings, logs, export:*, rips",
    "appimage_integration.py": "menu entry, icon, desktop shortcut, ~/Applications: menu:*, icon:*, desktop:*, appimages",
    "tool_paths.py": "reads: where the exported tools are found",
    "rip_compare.py": "reads: proposes ~/Music as a folder to open",
    "ui/main_window_provision.py": "rig session folders under ~/platterpus-rig: rig",
    "ui/dialogs/run_tests_dialog.py": "reads: a file dialog's starting folder (it writes only under settings: the scripts folder)",
    "ui/dialogs/script_console.py": "reads: a file dialog's starting folder",
    "app.py": "--rig-session's default folder under ~/platterpus-rig: rig",
    "ui/uninstall_dialog.py": "reads: the uninstaller itself",
    "deps/user_locations.py": "reads: the uninstaller's own locations",
    "deps/ripper_wrapper_probe.py": "reads: times the exported cyanrip wrapper",
    "export_redaction.py": "reads: replaces the home path with ~ in shared text",
}


def _modules_naming_home() -> set[str]:
    found: set[str] = set()
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names_home = (
                isinstance(node, ast.Attribute)
                and node.attr == "home"
                and isinstance(node.value, ast.Name)
                and node.value.id == "Path"
            ) or (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value.startswith(
                    ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME")
                )
            )
            if names_home:
                found.add(str(path.relative_to(SRC)))
                break
    return found


def test_every_module_naming_the_home_folder_is_answered_for() -> None:
    found = _modules_naming_home()
    assert len(found) >= 8, f"the sweep is blind: {sorted(found)}"
    new = sorted(found - set(_HOME_REFERENCES))
    assert not new, (
        f"these modules reach into $HOME and are not in _HOME_REFERENCES: {new}. "
        "If they write there, add the paths to deps/install_footprint.py so the "
        "uninstaller removes them; either way, record the answer here."
    )
    stale = sorted(set(_HOME_REFERENCES) - found)
    assert not stale, f"no longer naming $HOME; remove them: {stale}"


def test_every_item_named_in_the_ledger_exists(tmp_path: Path) -> None:
    ids = set(_items(tmp_path, rips=tmp_path / "r"))
    named = {
        word.strip(" ,.")
        for answer in _HOME_REFERENCES.values()
        if ":" in answer and not answer.startswith("reads:")
        for word in answer.split(":", 1)[1].split(",")
    }
    for name in named:
        prefix = name.removesuffix("*")
        assert any(i == prefix or i.startswith(prefix) for i in ids), name


# --- Locations and the rips folder ----------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('XDG_DESKTOP_DIR="$HOME/Schreibtisch"\n', "Schreibtisch"),
        ('# comment\nXDG_DESKTOP_DIR="$HOME/Desktop"\n', "Desktop"),
        ("", "Desktop"),
        ('XDG_DESKTOP_DIR="$HOME/"\n', "Desktop"),
    ],
)
def test_the_localized_desktop_folder_is_read(
    tmp_path: Path, text: str, expected: str
) -> None:
    assert desktop_folder_from_user_dirs(text, tmp_path) == tmp_path / expected


def test_locations_read_user_dirs_and_xdg(tmp_path: Path) -> None:
    config = tmp_path / "cfg"
    config.mkdir()
    (config / "user-dirs.dirs").write_text('XDG_DESKTOP_DIR="$HOME/Bureau"\n')
    loc = Locations.from_environment({"XDG_CONFIG_HOME": str(config)}, home=tmp_path)
    assert loc.desktop_folder == tmp_path / "Bureau"
    assert loc.data_home == tmp_path / ".local" / "share"
    items = footprint(loc)
    assert any(
        i.path == tmp_path / "Bureau" / f"{appimage_integration.DESKTOP_ID}.desktop"
        for i in items
    )


@pytest.mark.parametrize(
    ("raw", "ok"),
    [
        ("", False),
        ("Music/rips", False),
        ("/", False),
        ("HOME", False),
        ("HOME/..", False),
        ("HOME/.config", False),
        ("HOME/.local/share/rips", False),
        ("HOME/Music/rips", True),
        ("HOME/Music/../Music/rips", True),
        ("/mnt/library/rips", True),
    ],
)
def test_the_rips_folder_is_refused_when_unsafe(
    tmp_path: Path, raw: str, ok: bool
) -> None:
    home = tmp_path / "home"
    folder, why = safe_rips_folder(raw.replace("HOME", str(home)), home)
    assert (folder is not None) is ok, why
    assert bool(why) is not ok


def test_the_rips_folder_comes_from_the_settings(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    assert rips_setting(config) == str(DEFAULT_OUTPUT_DIR)
    config.write_text('output_dir = "/srv/music/flac"\n')
    assert rips_setting(config) == "/srv/music/flac"
    config.write_text("not = [valid toml")
    assert rips_setting(config) == str(DEFAULT_OUTPUT_DIR)


def test_only_a_checkout_venv_counts(tmp_path: Path) -> None:
    venv = tmp_path / ".venv"
    venv.mkdir()
    assert dev_checkout_venv(venv) is None
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "src" / "platterpus").mkdir(parents=True)
    assert dev_checkout_venv(venv) == venv
    assert dev_checkout_venv(tmp_path / "pipx-venv") is None
