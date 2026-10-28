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
- **The AppImage build's refusal without its lock**, run, not read: the WHOLE
  build script runs in a copy of the tree with a stub `python3` that records each
  call, without the lock and with one made for another Python.

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


#: A stand-in `python3` that records every call and does the least each needs:
#: `-c` succeeds (the prerequisite imports), `-m build` drops a placeholder wheel
#: where it was told to, and `-` swallows its heredoc. Everything else, the pip
#: and python_appimage calls above all, succeeds without doing anything, so the
#: record shows exactly what the real script would have run.
_STUB_PYTHON: Final[str] = """#!/bin/sh
printf '%s\\n' "$*" >> "$CALL_LOG"
if [ "$1" = "-m" ] && [ "$2" = "build" ]; then
    out=""
    while [ $# -gt 0 ]; do
        if [ "$1" = "--outdir" ]; then out="$2"; fi
        shift
    done
    : > "$out/platterpus-0.0.0-py3-none-any.whl"
fi
if [ "$1" = "-" ]; then cat > /dev/null; fi
exit 0
"""


def _run_whole_build(
    tmp_path: Path, lock: str | None, python_version: str = "3.12"
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    """Run the WHOLE build_appimage.sh in a copy of the tree, with a stub python3.

    The third follow-up review of 2026-10-27 (item 3) wrapped the refusal in
    `if [ -f lock ]` with an online fallback and the old test, which ran only the
    refusal block, still passed. Run end to end, the fallback's install is a
    recorded call, and the exit code is the script's own. ``lock`` is the
    requirements.lock to place, or None for none.
    """
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not installed")
    tree = tmp_path / "tree"
    shutil.copytree(
        REPO / "build" / "python-appimage", tree / "build" / "python-appimage"
    )
    shutil.copy(BUILD_SCRIPT, tree / "build" / BUILD_SCRIPT.name)
    (tree / "src" / "platterpus").mkdir(parents=True)
    placed = tree / "build" / "python-appimage" / "requirements.lock"
    placed.unlink(missing_ok=True)
    if lock is not None:
        placed.write_text(lock, encoding="utf-8")
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    stub = stubs / "python3"
    stub.write_text(_STUB_PYTHON, encoding="utf-8")
    stub.chmod(0o755)
    log = tmp_path / "calls.log"
    log.touch()
    result = subprocess.run(
        [bash, str(tree / "build" / BUILD_SCRIPT.name)],
        cwd=tree,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
        env={
            "PATH": f"{stubs}:/usr/bin:/bin",
            "HOME": str(tmp_path),
            "CALL_LOG": str(log),
            "PLATTERPUS_PYTHON_VERSION": python_version,
            "SOURCE_DATE_EPOCH": "315532800",
        },
    )
    return result, log.read_text(encoding="utf-8").splitlines()


def _fetches(calls: list[str]) -> list[str]:
    """Calls that would reach an index or build the AppImage."""
    return [c for c in calls if re.search(r"-m pip\b|-m python_appimage\b", c)]


def test_the_whole_build_refuses_to_run_without_its_lock(tmp_path: Path) -> None:
    result, calls = _run_whole_build(tmp_path, lock=None)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "requirements.lock is missing" in result.stderr
    # Non-triviality: the script really ran up to the check (it built the wheel).
    assert any(c.startswith("-m build") for c in calls), calls
    assert not _fetches(calls), (
        f"the build fetched or packaged without its lock: {calls}"
    )


def test_the_whole_build_refuses_a_lock_for_another_python(tmp_path: Path) -> None:
    lock = "# target-python: 3.11\n# target-platform: manylinux_2_34_x86_64\n"
    result, calls = _run_whole_build(tmp_path, lock=lock, python_version="3.12")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "resolved for CPython 3.11" in result.stderr
    assert not _fetches(calls), calls


def test_the_whole_build_downloads_from_the_committed_lock(tmp_path: Path) -> None:
    """The floor for the two above: with the real lock, the first fetch is the
    hash-checked download, wheels only, and nothing installs from an index."""
    lock = (REPO / "build" / "python-appimage" / "requirements.lock").read_text(
        encoding="utf-8"
    )
    _, calls = _run_whole_build(tmp_path, lock=lock)
    fetches = _fetches(calls)
    assert fetches, calls
    first = fetches[0]
    assert first.startswith("-m pip download"), fetches
    assert "--require-hashes" in first and "--only-binary=:all:" in first, first
    assert not any(c.startswith("-m pip install") for c in fetches), fetches
