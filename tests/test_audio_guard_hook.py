"""Behavioural tests for `.claude/hooks/audio_guard.py`, the agent-side audio guard.

**What the hook is.** A Claude Code ``PreToolUse`` hook on the Bash tool: before
every Bash call, the harness pipes it a JSON object carrying
``tool_input.command``, and exit 2 blocks the call. It is the agent's early
warning for CLAUDE.md Critical rule #8 (no copyrighted media in this public
repository). The real gate stays ``.githooks/pre-commit``
(``tests/test_media_guard_hook.py``).

**Why this file exists (2026-10-12).** The hook used to be one line in
``.claude/settings.json``, and an outside read found three defects in it:

(a) it failed OPEN: ``git diff ... 2>/dev/null | grep -q ... && block || exit 0``
    allowed the call whenever ``git diff`` itself failed;
(b) it never read the command, so while audio was staged it blocked every Bash
    call, including the ``git restore --staged`` its own message prescribed;
(c) it checked what was staged BEFORE the call, so
    ``git add x.flac && git commit`` in one call got straight past it.

Each test below is one case of the rule. **Every case runs twice**: once with
real git, and once with a ``git`` on ``PATH`` whose ``diff`` fails. A case that
commits or pushes must be BLOCKED in the broken mode, with a message saying the
staged list could not be read. That is defect (a), checked under every command
shape rather than one. A case that neither commits nor pushes must still be
ALLOWED in the broken mode, because the rule says fail closed for commits and
pushes and allow everything else.

The hook is run exactly as Claude Code runs it: as a program, with the JSON on
stdin. No real audio is created anywhere. The fixtures are text files with
audio extensions, written under ``tmp_path`` and never added to this repository.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Final, Literal

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
HOOK: Final[Path] = REPO_ROOT / ".claude" / "hooks" / "audio_guard.py"
SETTINGS: Final[Path] = REPO_ROOT / ".claude" / "settings.json"

_GIT: Final[str | None] = shutil.which("git")

pytestmark = pytest.mark.skipif(
    _GIT is None or not HOOK.is_file(),
    reason="needs git on PATH and the committed .claude/hooks/audio_guard.py",
)

Mode = Literal["real", "diff-fails"]
MODES: Final[tuple[Mode, ...]] = ("real", "diff-fails")


def _git(repo: Path, *args: str) -> None:
    """Run git in `repo`, raising with its output if it fails."""
    assert _GIT is not None
    subprocess.run([_GIT, *args], cwd=repo, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A throwaway repository with one commit, so `git restore --staged` works."""
    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "-q")
    _git(work, "config", "user.email", "test@example.invalid")
    _git(work, "config", "user.name", "test")
    (work / "README").write_text("seed\n", encoding="utf-8")
    _git(work, "add", "README")
    _git(work, "commit", "-q", "-m", "seed")
    return work


def _shim(tmp_path: Path, *, fail: str | None) -> Path:
    """A folder holding a `git` that fails for subcommand `fail` (or for all).

    Every other call goes to the real git. `fail="diff"` breaks only the hook's
    staged-list probe; `fail="*"` breaks every git call. `fail=None` passes
    everything through: the control that proves the shim alone is not what
    makes a test block.
    """
    assert _GIT is not None
    folder = tmp_path / f"shim-{fail or 'none'}".replace("*", "all")
    folder.mkdir(exist_ok=True)
    shim = folder / "git"
    # The hook calls `git -C <dir> <subcommand> ...`, so the subcommand is the
    # third word. Match it anywhere to stay honest if that ever changes.
    if fail == "*":
        body = 'echo "fatal: simulated git failure" >&2\nexit 128\n'
    elif fail is not None:
        body = (
            'for arg in "$@"; do\n'
            f'  if [ "$arg" = "{fail}" ]; then\n'
            '    echo "fatal: bad object deadbeef" >&2\n'
            "    exit 128\n"
            "  fi\n"
            "done\n"
            f'exec {_GIT} "$@"\n'
        )
    else:
        body = f'exec {_GIT} "$@"\n'
    shim.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
    shim.chmod(0o755)
    return folder


@dataclass(frozen=True)
class Outcome:
    code: int
    stderr: str


def _run_hook(
    command: str, cwd: Path, *, shim: Path | None = None, raw: str | None = None
) -> Outcome:
    """Feed the hook one PreToolUse event, the way Claude Code does."""
    env = dict(os.environ)
    if shim is not None:
        env["PATH"] = f"{shim}{os.pathsep}{env.get('PATH', '')}"
    event = {
        "session_id": "test",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command, "description": "test"},
        "cwd": str(cwd),
    }
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input=raw if raw is not None else json.dumps(event),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )
    return Outcome(done.returncode, done.stderr)


def _in_mode(command: str, repo: Path, mode: Mode) -> Outcome:
    shim = _shim(repo.parent, fail="diff") if mode == "diff-fails" else None
    return _run_hook(command, repo, shim=shim)


def _assert_blocked(out: Outcome, why: str) -> None:
    assert out.code == 2, f"{why}: the hook allowed it. stderr={out.stderr!r}"
    assert "Blocked" in out.stderr, f"{why}: blocked without saying why: {out.stderr!r}"


def _assert_fail_closed(out: Outcome) -> None:
    """Blocked because the staged list was unreadable, and saying exactly that."""
    _assert_blocked(out, "a commit or push while `git diff` fails")
    assert "could not read the staged files" in out.stderr, (
        "the refusal did not say the staged list was unreadable, so it cannot be "
        f"told apart from a real audio finding: {out.stderr!r}"
    )
    assert "bad object deadbeef" in out.stderr, (
        f"the refusal dropped git's own words: {out.stderr!r}"
    )


def _assert_allowed(out: Outcome, why: str) -> None:
    assert out.code == 0, f"{why}: the hook blocked it. stderr={out.stderr!r}"


def _stage_audio(repo: Path, name: str = "track01.flac") -> None:
    (repo / name).write_text("not audio, just a name\n", encoding="utf-8")
    _git(repo, "add", "-f", name)


# ----------------------------------------------------- (b) reads the command ---


@pytest.mark.parametrize("mode", MODES)
def test_an_ordinary_command_is_allowed_while_audio_is_staged(
    repo: Path, mode: Mode
) -> None:
    """Defect (b): the old hook blocked EVERY Bash call while audio was staged."""
    _stage_audio(repo)
    _assert_allowed(_in_mode("ls -la", repo, mode), "`ls` while audio is staged")
    _assert_allowed(
        _in_mode("git status", repo, mode), "`git status` while audio is staged"
    )


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "command",
    [
        "git restore --staged track01.flac",
        "git restore --staged -- track01.flac",
        "git reset",
        "git reset HEAD -- track01.flac",
        "git rm --cached track01.flac",
        "git rm -f track01.flac",
    ],
)
def test_removing_audio_is_always_allowed(repo: Path, mode: Mode, command: str) -> None:
    """The way out the hook's own message prescribes must never be blocked."""
    _stage_audio(repo)
    _assert_allowed(_in_mode(command, repo, mode), f"`{command}` while audio is staged")


def test_the_allowed_unstage_actually_works(repo: Path) -> None:
    """Non-triviality for the test above: the allowed command really unstages it."""
    _stage_audio(repo)
    _assert_allowed(_run_hook("git restore --staged track01.flac", repo), "unstage")
    _git(repo, "restore", "--staged", "track01.flac")
    _assert_allowed(_run_hook("git commit -m ok", repo), "a commit after unstaging")


# ---------------------------------------- commits and pushes while staged ---


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "command",
    [
        "git commit -m 'add notes'",
        "git push origin HEAD",
        "git -C . commit -m x",
        "GIT_AUTHOR_NAME=x git commit -m x",
        "cd . && git commit -m x",
        "bash -c 'git commit -m x'",
    ],
)
def test_a_commit_or_push_is_blocked_while_audio_is_staged(
    repo: Path, mode: Mode, command: str
) -> None:
    """The thing the hook is for, through the shapes a command arrives in."""
    _stage_audio(repo)
    out = _in_mode(command, repo, mode)
    if mode == "diff-fails":
        _assert_fail_closed(out)
        return
    _assert_blocked(out, f"`{command}` with audio staged")
    assert "track01.flac" in out.stderr, (
        f"the refusal did not name the file: {out.stderr!r}"
    )
    assert "git restore --staged" in out.stderr, (
        f"the refusal did not say how to unstage: {out.stderr!r}"
    )


def test_a_git_alias_for_commit_is_still_a_commit(repo: Path) -> None:
    _git(repo, "config", "alias.ci", "commit")
    _stage_audio(repo)
    _assert_blocked(_run_hook("git ci -m x", repo), "`git ci` aliased to commit")


# ------------------------------------------- (c) commands that stage audio ---


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "command",
    [
        "git add track01.flac && git commit -m x",
        "git add -f TRACK02.FLAC",
        "git add . && git commit -m x",
        "git add -A; git commit -m x",
        "git commit -m x track01.flac",
        "git mv notes.txt notes.flac",
        "bash -c 'git add track01.flac'",
        "cd sub && git add deep.wav",
        "git -C sub add deep.wav",
    ],
)
def test_a_command_that_stages_audio_is_blocked(
    repo: Path, mode: Mode, command: str
) -> None:
    """Defect (c): staging and committing in ONE call got past a pre-call check.

    Nothing is staged when the hook runs, so only reading the command can catch
    these. They are blocked in both modes: whether a command stages audio is
    read from its own arguments and from `git add --dry-run`, never from
    `git diff`, so a broken `git diff` does not change the answer.
    """
    (repo / "track01.flac").write_text("x\n", encoding="utf-8")
    (repo / "TRACK02.FLAC").write_text("x\n", encoding="utf-8")
    (repo / "notes.txt").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "notes.txt")
    _git(repo, "commit", "-q", "-m", "notes")
    (repo / "sub").mkdir()
    (repo / "sub" / "deep.wav").write_text("x\n", encoding="utf-8")
    out = _in_mode(command, repo, mode)
    _assert_blocked(out, f"`{command}` stages audio")
    assert "would stage audio" in out.stderr, f"wrong reason given: {out.stderr!r}"


@pytest.mark.parametrize("mode", MODES)
def test_a_stage_the_guard_cannot_list_does_not_ride_along_with_a_commit(
    repo: Path, mode: Mode
) -> None:
    """`git add` reading paths from stdin, then a commit: not vouched for."""
    out = _in_mode("git add --pathspec-from-file=- && git commit -m x", repo, mode)
    _assert_blocked(out, "an unlistable stage chained to a commit")


# --------------------------------------------------- the floor: no false alarms ---


@pytest.mark.parametrize("mode", MODES)
def test_an_ordinary_commit_is_allowed_only_when_the_list_is_readable(
    repo: Path, mode: Mode
) -> None:
    """The floor: a guard that blocked every commit would pass every test above."""
    (repo / "notes.md").write_text("# text\n", encoding="utf-8")
    out = _in_mode("git add notes.md && git commit -m notes", repo, mode)
    if mode == "diff-fails":
        _assert_fail_closed(out)
    else:
        _assert_allowed(out, "an ordinary text commit")


def test_an_ignored_audio_file_does_not_block_git_add_all(repo: Path) -> None:
    """`git add .` stages what git would stage, so an ignored .flac is not staged."""
    (repo / ".gitignore").write_text("*.flac\n", encoding="utf-8")
    (repo / "track01.flac").write_text("x\n", encoding="utf-8")
    (repo / "notes.md").write_text("# text\n", encoding="utf-8")
    _assert_allowed(_run_hook("git add . && git commit -m x", repo), "an ignored .flac")


def test_a_commit_message_that_mentions_audio_is_not_a_command(repo: Path) -> None:
    """A heredoc body is data. Its words must not be read as shell commands."""
    command = (
        "git commit --allow-empty -m \"$(cat <<'EOF'\n"
        "it's about git add track01.flac and git push\n"
        "EOF\n"
        ')"'
    )
    _assert_allowed(_run_hook(command, repo), "a message mentioning git add x.flac")


def test_a_log_and_a_crc_file_are_allowed(repo: Path) -> None:
    """The text proof Rule #8 tells us to commit must not be blocked."""
    (repo / "album.log").write_text("Track 1 | CRC32 A1B2C3D4\n", encoding="utf-8")
    _assert_allowed(_run_hook("git add album.log && git commit -m log", repo), "a log")


def test_outside_a_repository_nothing_is_blocked(tmp_path: Path) -> None:
    lonely = tmp_path / "not-a-repo"
    lonely.mkdir()
    _assert_allowed(_run_hook("git commit -m x", lonely), "a commit outside any repo")


# ------------------------------------------------- (a) fails closed, and only there ---


def test_a_git_that_fails_every_call_still_counts_as_a_repository(repo: Path) -> None:
    """If git cannot even answer "is this a repo?", a `.git` folder still says yes.

    Otherwise a fully broken git would make a real repository look like "not a
    repository", which is the answer that allows a commit.
    """
    out = _run_hook("git commit -m x", repo, shim=_shim(repo.parent, fail="*"))
    _assert_blocked(out, "a commit while every git call fails")
    assert "could not read the staged files" in out.stderr


def test_the_shim_itself_is_not_what_causes_a_block(repo: Path) -> None:
    """Non-triviality for every diff-fails case: a pass-through shim allows."""
    out = _run_hook(
        "git commit --allow-empty -m x", repo, shim=_shim(repo.parent, fail=None)
    )
    _assert_allowed(out, "a commit through a pass-through git shim")


@pytest.mark.parametrize(
    "raw",
    ["not json", "{}", '{"tool_input": {}}', '{"tool_input": {"command": 7}}'],
)
def test_input_it_cannot_read_is_blocked(repo: Path, raw: str) -> None:
    """It will not allow a command it could not see."""
    out = _run_hook("", repo, raw=raw)
    _assert_blocked(out, f"unreadable hook input {raw!r}")
    assert "could not read the command" in out.stderr


def _load_hook() -> ModuleType:
    spec = importlib.util.spec_from_file_location("audio_guard", HOOK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered first: its dataclasses look their own module up by name.
    sys.modules["audio_guard"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("command", "expected"), [("git commit -m x", 2), ("ls", 0), ("git push", 2)]
)
def test_a_crash_in_the_guard_blocks_commits_and_allows_the_rest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, command: str, expected: int
) -> None:
    """A bug in the hook must not decide silently, and must not take the shell away."""
    hook = _load_hook()

    def _boom(command: str, cwd: Path) -> tuple[int, str]:
        raise RuntimeError("simulated defect")

    monkeypatch.setattr(hook, "judge", _boom)
    event = json.dumps({"tool_input": {"command": command}, "cwd": str(tmp_path)})
    monkeypatch.setattr(sys, "stdin", io.StringIO(event))
    assert hook.main() == expected


# ---------------------------------------------------------------- wiring ---


def test_settings_run_this_script_and_no_inline_grep() -> None:
    """The registered PreToolUse command is this script, failing closed if it can't run.

    `|| exit 2` turns "python3 could not start the script" into a block instead
    of a non-blocking error. And no `2>/dev/null | grep` may come back.
    """
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    bash_hooks = [
        hook["command"]
        for entry in settings["hooks"]["PreToolUse"]
        if entry.get("matcher") == "Bash"
        for hook in entry["hooks"]
    ]
    assert bash_hooks, "no Bash PreToolUse hook is registered"
    assert any(
        "/.claude/hooks/audio_guard.py" in c and c.rstrip().endswith("|| exit 2")
        for c in bash_hooks
    ), bash_hooks
    assert not any("grep" in c for c in bash_hooks), bash_hooks
    assert os.access(HOOK, os.X_OK), "the hook script lost its executable bit"


def test_the_registered_command_blocks_end_to_end(repo: Path) -> None:
    """Run the settings.json command line itself, with the harness's environment."""
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    command = next(
        hook["command"]
        for entry in settings["hooks"]["PreToolUse"]
        if entry.get("matcher") == "Bash"
        for hook in entry["hooks"]
    )
    _stage_audio(repo)
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(REPO_ROOT))
    event = json.dumps({"tool_input": {"command": "git commit -m x"}, "cwd": str(repo)})
    done = subprocess.run(
        ["bash", "-c", command],
        input=event,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )
    assert done.returncode == 2, done.stderr
    assert "track01.flac" in done.stderr
