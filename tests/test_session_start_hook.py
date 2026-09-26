"""The session-start hook switches the audio guard on in a cloud session.

`.githooks/pre-commit` refuses a commit that stages a music file (CLAUDE.md
Critical rule #8), but git runs it only once `core.hooksPath` is `.githooks`,
and only `dev-setup.sh` set that. A Claude Code session on the web starts from a
fresh clone that never ran it, so the guard was off there. Found 2026-09-26, and
switched on by hand in that session. The hook makes that automatic.

These run the real script against a scratch repository, because the claim is
about git's configuration afterwards, not about the script's text.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / ".claude" / "hooks" / "session-start.sh"

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def _scratch_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "clone"
    (repo / ".githooks").mkdir(parents=True)
    shutil.copy2(
        REPO_ROOT / ".githooks" / "pre-commit", repo / ".githooks" / "pre-commit"
    )
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    return repo


def _run(repo: Path, *, remote: bool) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_REMOTE"}
    env["CLAUDE_PROJECT_DIR"] = str(repo)
    if remote:
        env["CLAUDE_CODE_REMOTE"] = "true"
    return subprocess.run(
        ["bash", str(HOOK)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _hooks_path(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "config", "--get", "core.hooksPath"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def test_in_a_cloud_session_the_guard_is_switched_on(tmp_path: Path) -> None:
    repo = _scratch_repo(tmp_path)
    assert _hooks_path(repo) == "", "a fresh clone must start with the guard off"
    result = _run(repo, remote=True)
    assert result.returncode == 0, result.stderr
    assert _hooks_path(repo) == ".githooks"


def test_running_it_twice_changes_nothing_and_still_succeeds(tmp_path: Path) -> None:
    repo = _scratch_repo(tmp_path)
    _run(repo, remote=True)
    again = _run(repo, remote=True)
    assert again.returncode == 0 and again.stderr == ""
    assert _hooks_path(repo) == ".githooks"


def test_outside_a_cloud_session_it_leaves_git_alone(tmp_path: Path) -> None:
    """Locally, `dev-setup.sh` sets it, and a developer's git config is theirs."""
    repo = _scratch_repo(tmp_path)
    assert _run(repo, remote=False).returncode == 0
    assert _hooks_path(repo) == ""


def test_a_missing_guard_is_reported_and_never_fails_the_session(
    tmp_path: Path,
) -> None:
    repo = _scratch_repo(tmp_path)
    (repo / ".githooks" / "pre-commit").unlink()
    result = _run(repo, remote=True)
    assert result.returncode == 0
    assert "audio guard not set" in result.stderr
    assert _hooks_path(repo) == ""


def test_the_hook_is_registered_and_executable() -> None:
    settings = json.loads(
        (REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    commands = [
        hook["command"]
        for entry in settings["hooks"]["SessionStart"]
        for hook in entry["hooks"]
    ]
    assert any(
        command.endswith("/.claude/hooks/session-start.sh") for command in commands
    )
    assert os.access(HOOK, os.X_OK), "git keeps the executable bit; the hook needs it"
