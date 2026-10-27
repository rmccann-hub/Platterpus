"""The flags that make a hashed install hashed, held one by one.

`tests/test_dependency_locks.py` holds that the jobs which publish, attest or gate
install `--require-hashes -r <lock>`. The second follow-up review of 2026-10-27
(item 3) found reverts that test cannot see, each of which reopens an unhashed
path into a privileged job. One test per revert:

- **`--no-isolation` dropped from a build.** An isolated `python -m build` makes
  its own environment and fetches `setuptools>=77` and `wheel` into it by range,
  with no hashes, inside the job that holds `id-token: write`.
- **`--only-binary=:all:` dropped.** A hash pins the file, but a source
  distribution runs its own build code at install time; wheels only.
- **Another installer in a privileged workflow** (`pipx`, `uv`, `uvx`), which the
  `pip install` check does not read.
- **The AppImage build's refusal without its lock**, run, not read: the block that
  checks `requirements.lock` is executed against a recipe folder with the lock
  missing, and against one made for another Python.

The fifth revert the review named, a package deleted from a lock, is caught by
the lock currency check, which regenerates each lock and compares it.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Final

import pytest

REPO: Final[Path] = Path(__file__).resolve().parent.parent
WORKFLOWS: Final[Path] = REPO / ".github" / "workflows"
BUILD_SCRIPT: Final[Path] = REPO / "build" / "build_appimage.sh"

#: The workflows whose jobs publish, attest or upload a build.
PRIVILEGED: Final[tuple[str, ...]] = ("release.yml", "publish-pypi.yml", "appimage.yml")


def _commands(text: str) -> list[str]:
    """Executable lines, comments dropped and backslash continuations joined."""
    joined = re.sub(r"\\\s*\n\s*", " ", text)
    return [
        line.strip()
        for line in joined.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _sources() -> dict[str, list[str]]:
    """Every workflow and the AppImage build script, as command lines."""
    found = {
        p.name: _commands(p.read_text(encoding="utf-8"))
        for p in WORKFLOWS.glob("*.yml")
    }
    found[BUILD_SCRIPT.name] = _commands(BUILD_SCRIPT.read_text(encoding="utf-8"))
    return found


_BUILD: Final[re.Pattern[str]] = re.compile(r"\bpython3?\s+-m\s+build\b")


def test_every_build_runs_without_isolation() -> None:
    """`python -m build` with no `--no-isolation` fetches setuptools by range."""
    builds = [
        (name, line)
        for name, lines in _sources().items()
        for line in lines
        if _BUILD.search(line) and "echo" not in line.split()[:1]
    ]
    # publish-pypi.yml's build and the AppImage build script's wheel, at least.
    assert len(builds) >= 2, builds
    isolated = [
        f"{name}: {line}" for name, line in builds if "--no-isolation" not in line
    ]
    assert not isolated, f"builds that fetch their build tools unhashed: {isolated}"


def test_every_hashed_install_takes_wheels_only() -> None:
    hashed = [
        (name, line)
        for name, lines in _sources().items()
        for line in lines
        if "--require-hashes" in line
        and re.search(r"\bpip\s+(install|download)\b", line)
    ]
    # Five workflow installs and the build script's download on 2026-10-27.
    assert len(hashed) >= 5, hashed
    sdists = [
        f"{name}: {line}" for name, line in hashed if "--only-binary=:all:" not in line
    ]
    assert not sdists, f"hashed installs that would run a source build: {sdists}"


_OTHER_INSTALLER: Final[re.Pattern[str]] = re.compile(
    r"\b(pipx\s+(install|run|inject)|uvx\b|uv\s+(pip|tool|add|sync|run)\b|easy_install)"
)


def test_no_privileged_workflow_installs_any_other_way() -> None:
    offenders = [
        f"{name}: {line}"
        for name in PRIVILEGED
        for line in _commands((WORKFLOWS / name).read_text(encoding="utf-8"))
        if _OTHER_INSTALLER.search(line)
    ]
    assert not offenders, f"installs the hashed-lock check cannot read: {offenders}"


def test_the_installer_check_sees_what_it_refuses() -> None:
    for line in (
        "pipx install twine",
        "uvx zizmor",
        "uv pip install build",
        "uv tool install x",
    ):
        assert _OTHER_INSTALLER.search(line), line
    assert not _OTHER_INSTALLER.search(
        "python -m pip install --require-hashes -r a.lock"
    )


def _lock_check_block() -> str:
    """The build script's requirements.lock refusals, from its first line to the download."""
    text = BUILD_SCRIPT.read_text(encoding="utf-8")
    start = text.index('WHEELHOUSE="$RECIPE_DIR/.wheelhouse"')
    end = text.index(
        'echo "Verifying the AppImage\'s dependencies against requirements.lock"'
    )
    return text[start:end]


def _run_block(
    recipe: Path, python_version: str = "3.12"
) -> subprocess.CompletedProcess[str]:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not installed")
    script = f'set -euo pipefail\nRECIPE_DIR="{recipe}"\nPLATTERPUS_PYTHON_VERSION="{python_version}"\n'
    return subprocess.run(
        [bash, "-c", script + _lock_check_block() + '\necho "LOCK ACCEPTED"\n'],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )


def test_the_build_refuses_to_run_without_its_lock(tmp_path: Path) -> None:
    result = _run_block(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "requirements.lock is missing" in result.stderr
    assert "LOCK ACCEPTED" not in result.stdout


def test_the_build_refuses_a_lock_for_another_python(tmp_path: Path) -> None:
    (tmp_path / "requirements.lock").write_text(
        "# target-python: 3.11\n# target-platform: manylinux_2_34_x86_64\n",
        encoding="utf-8",
    )
    result = _run_block(tmp_path, python_version="3.12")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "resolved for CPython 3.11" in result.stderr


def test_the_build_accepts_the_committed_lock(tmp_path: Path) -> None:
    """The floor for the two above: the real lock passes the same block."""
    shutil.copy(REPO / "build" / "python-appimage" / "requirements.lock", tmp_path)
    result = _run_block(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "LOCK ACCEPTED" in result.stdout
