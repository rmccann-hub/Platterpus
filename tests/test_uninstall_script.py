"""Tests for uninstall.sh and the command-line uninstaller it launches (TASKS R190).

``uninstall.sh`` is a thin launcher for ``platterpus.deps.uninstall_cli``, which
reads the same footprint and engine as the in-app dialog. The launcher is run
only with ``--help`` and ``--dry-run`` here (a real run from a checkout would
also remove that checkout's ``.venv``); real removals run the CLI module
directly, in a fake home, with stand-ins for distrobox, podman and flatpak.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
UNINSTALL = REPO_ROOT / "uninstall.sh"


def _env(home: Path, shims: Path | None = None) -> dict[str, str]:
    env = {
        **os.environ,
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
    }
    if shims is not None:
        env["PATH"] = f"{shims}:{os.environ.get('PATH', '')}"
    return env


def _launcher(
    args: list[str], env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(UNINSTALL), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _cli(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "platterpus.deps.uninstall_cli", *args],
        capture_output=True,
        text=True,
        check=False,
        env={**env, "PYTHONPATH": str(REPO_ROOT / "src")},
        stdin=subprocess.DEVNULL,
    )


def _shims(tmp_path: Path, mode: str = "ok") -> Path:
    """distrobox, podman and flatpak stand-ins that log each call.

    ``ok``: a container named ``ripping-old`` (NOT ours), no image, no Picard.
    ``fail``: every listing fails, as a broken podman socket would make it.
    """
    folder = tmp_path / f"shims-{mode}"
    folder.mkdir()
    calls = tmp_path / "calls.log"
    bodies = {
        "distrobox": 'echo "ID | NAME | STATUS"; echo "1 | ripping-old | Up"',
        "podman": 'echo "Error: image not known" >&2; exit 125',
        "flatpak": "exit 0",
    }
    for tool, body in bodies.items():
        if mode == "fail":
            body = 'echo "simulated listing failure" >&2; exit 1'
        shim = folder / tool
        shim.write_text(
            f'#!/bin/bash\necho "{tool} $*" >> "{calls}"\n{body}\n', encoding="utf-8"
        )
        shim.chmod(0o755)
    return folder


def _home(tmp_path: Path, output_dir: str | None = None) -> Path:
    home = tmp_path / "home"
    files = [
        ".config/platterpus/config.toml",
        ".local/share/platterpus/log.txt",
        ".cache/platterpus/cyanrip-fork/meson.build",
        "platterpus-rig/rigsession1/log.txt",
        "Applications/platterpus-x86_64.AppImage",
        "Applications/.platterpus-install.part",
        "Music/rips/Album/01.txt",
    ]
    for rel in files:
        (home / rel).parent.mkdir(parents=True, exist_ok=True)
        (home / rel).write_text("x", encoding="utf-8")
    if output_dir is not None:
        (home / ".config/platterpus/config.toml").write_text(
            f'output_dir = "{output_dir}"\n', encoding="utf-8"
        )
    return home


def test_script_exists_and_is_executable() -> None:
    assert UNINSTALL.is_file()
    assert os.access(UNINSTALL, os.X_OK), "uninstall.sh is not executable"


def test_help_exits_zero_and_shows_usage() -> None:
    result = _launcher(["--help"])
    assert result.returncode == 0, result.stderr
    for flag in (
        "Uninstall Platterpus",
        "--full",
        "--dry-run",
        "--remove-rips",
        "--keep-settings",
    ):
        assert flag in result.stdout, flag


def test_unknown_flag_exits_non_zero() -> None:
    result = _launcher(["--bogus-flag"])
    assert result.returncode != 0
    assert "unrecognized arguments" in result.stderr


def test_the_launcher_dry_run_lists_and_touches_nothing(tmp_path: Path) -> None:
    home = _home(tmp_path)
    before = sorted(home.rglob("*"))
    result = _launcher(["--dry-run", "--yes"], env=_env(home, _shims(tmp_path)))
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "DRY RUN" in out
    assert "Will remove:" in out
    for expected in (".cache/platterpus", "platterpus-rig", ".platterpus-install.part"):
        assert expected in out, expected
    assert sorted(home.rglob("*")) == before
    assert f"the clone at {REPO_ROOT}" in out
    assert "Music/rips" not in out.split("Will keep:")[0], "rips planned unasked"


def test_the_cli_removes_everything_but_rips_and_the_clone(tmp_path: Path) -> None:
    home = _home(tmp_path)
    result = _cli(["--yes"], _env(home, _shims(tmp_path)))
    assert result.returncode == 0, result.stdout + result.stderr
    left = sorted(str(p.relative_to(home)) for p in home.rglob("*") if p.is_file())
    assert left == ["Music/rips/Album/01.txt"], left
    assert "✓ Uninstalled, and a check afterwards found nothing" in result.stdout


def test_a_container_that_only_contains_the_name_is_not_removed(tmp_path: Path) -> None:
    home = _home(tmp_path)
    _cli(["--yes"], _env(home, _shims(tmp_path)))
    calls = (tmp_path / "calls.log").read_text(encoding="utf-8")
    assert "distrobox list" in calls
    assert "distrobox rm" not in calls, "ripping-old is not the 'ripping' container"


def test_remove_rips_uses_the_configured_folder(tmp_path: Path) -> None:
    library = tmp_path / "library"
    (library / "Album").mkdir(parents=True)
    (library / "Album" / "01.txt").write_text("x")
    home = _home(tmp_path, output_dir=str(library))
    result = _cli(["--yes", "--remove-rips"], _env(home, _shims(tmp_path)))
    assert result.returncode == 0, result.stdout + result.stderr
    assert not library.exists()
    assert (home / "Music/rips/Album/01.txt").exists(), (
        "the default folder was not named"
    )


@pytest.mark.parametrize("unsafe", ["/", "HOME", "Music/rips"])
def test_remove_rips_refuses_an_unsafe_folder(tmp_path: Path, unsafe: str) -> None:
    home = _home(tmp_path, output_dir=unsafe.replace("HOME", str(tmp_path / "home")))
    result = _cli(["--yes", "--remove-rips"], _env(home, _shims(tmp_path)))
    assert "--remove-rips refused" in result.stdout
    assert (home / "Music/rips/Album/01.txt").exists()


def test_keep_flags_keep_their_groups(tmp_path: Path) -> None:
    home = _home(tmp_path)
    _cli(["--yes", "--keep-settings", "--keep-logs"], _env(home, _shims(tmp_path)))
    assert (home / ".config/platterpus/config.toml").exists()
    assert (home / ".local/share/platterpus/log.txt").exists()
    assert (home / "platterpus-rig/rigsession1/log.txt").exists()
    assert not (home / ".cache/platterpus").exists()


def test_a_probe_that_cannot_tell_is_never_reported_as_not_present(
    tmp_path: Path,
) -> None:
    """Regression (2026-10-12): a failed listing read as "not installed".

    With a failing ``distrobox list`` or ``flatpak list``, the old script said
    the container and Picard were "not present" and left them installed. Now the
    plan says it could not check, quotes the tool, and leaves them in place.
    """
    home = _home(tmp_path)
    result = _cli(["--dry-run"], _env(home, _shims(tmp_path, "fail")))
    out = result.stdout
    assert result.returncode == 0, result.stderr
    assert "Could not check (left in place):" in out
    assert "simulated listing failure" in out, "the tool's own words were dropped"
    unchecked = out.split("Could not check (left in place):")[1]
    assert "'ripping' container" in unchecked and "Picard" in unchecked
