"""Behavioural tests for `.githooks/pre-commit` — the Critical Rule #8 guard.

**Why this file exists.** `CLAUDE.md` calls this hook *"the canonical guard"* for
the one rule in the project with legal consequences: never commit audio or other
copyrighted media to a public repository. It had **no test of any kind**. It was
also invisible to `tests/test_security_no_shell.py::test_shell_scripts_enable_errexit`,
whose scan globs `*.sh` and so never sees an extensionless hook.

And it failed **open**. The original spelling was

    offenders=$(git diff --cached --name-only --diff-filter=ACMR | grep -iE "$pattern" || true)

where `|| true` is needed for grep's no-match exit — the normal case — but sits
outside the pipeline and therefore also absorbs a failure of `git diff` itself.
`set -o pipefail` cannot help, because it is the pipeline's own status being
discarded. A fatal `git diff` yielded an empty `offenders`, and the hook exited 0.
The identical idiom was in `ci.yml`'s media-guard, so the two guards meant to be
*independent* witnesses shared one failure mode — which is the entire point of
having a backstop.

`test_the_hook_refuses_when_it_cannot_list_the_staged_files` is the regression
test for that, and it is the reason this file runs a real `git` shim rather than
asserting on the script's text: the defect was in behaviour under a failing
producer, and no amount of reading the source would have shown it passing.

No real audio is created anywhere here (Rule #8 applies to the tests too). The
fixtures are ordinary text files with audio *extensions*, written under
`tmp_path` and never added to this repository.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
HOOK: Final[Path] = REPO_ROOT / ".githooks" / "pre-commit"

_GIT: Final[str | None] = shutil.which("git")

pytestmark = pytest.mark.skipif(
    _GIT is None or not HOOK.is_file(),
    reason="needs git on PATH and the committed .githooks/pre-commit",
)


def _git(repo: Path, *args: str) -> None:
    """Run git in `repo`, raising with its output if it fails."""
    assert _GIT is not None
    subprocess.run(
        [_GIT, *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A throwaway git repo with the real hook available to run against it."""
    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "-q")
    _git(work, "config", "user.email", "test@example.invalid")
    _git(work, "config", "user.name", "test")
    return work


def _run_hook(
    repo: Path, extra_path: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Invoke the hook exactly as git would: as a program, with cwd in the repo."""
    env = None
    if extra_path is not None:
        import os

        env = dict(os.environ)
        env["PATH"] = f"{extra_path}:{env.get('PATH', '')}"
    return subprocess.run(
        ["bash", str(HOOK)],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


def test_a_staged_audio_file_blocks_the_commit(repo: Path) -> None:
    """The thing the hook is for. Text content, audio extension — no media created."""
    (repo / "track01.flac").write_text("not audio, just a name\n", encoding="utf-8")
    _git(repo, "add", "-f", "track01.flac")

    result = _run_hook(repo)

    assert result.returncode == 1, (
        f"the hook allowed a staged .flac. stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    assert "track01.flac" in result.stderr, (
        "the refusal did not name the offending file, so the operator cannot act "
        f"on it: {result.stderr!r}"
    )


def test_the_extension_match_is_case_insensitive(repo: Path) -> None:
    """`.FLAC` off a Windows-ish tool must not slip past a lowercase pattern."""
    (repo / "TRACK.FLAC").write_text("not audio\n", encoding="utf-8")
    _git(repo, "add", "-f", "TRACK.FLAC")
    assert _run_hook(repo).returncode == 1


def test_an_ordinary_text_commit_is_allowed(repo: Path) -> None:
    """The floor: a guard that blocks everything would pass the tests above.

    Without this, `exit 1` unconditionally would satisfy every other assertion in
    this file — the mirror image of a check satisfied by finding nothing.
    """
    (repo / "notes.md").write_text("# text\n", encoding="utf-8")
    _git(repo, "add", "notes.md")

    result = _run_hook(repo)

    assert result.returncode == 0, (
        f"the hook blocked an ordinary text commit. stderr={result.stderr!r}"
    )


def test_a_log_and_a_crc_file_are_allowed(repo: Path) -> None:
    """The durable proof this project DOES commit must not be blocked.

    Rule #8's own instruction is to commit the text artifacts — the ripper log and
    per-track CRCs — and never the audio. A guard that rejected those would push
    people to `--no-verify`, which disables it entirely.
    """
    (repo / "album.log").write_text("Track 1 | CRC32 A1B2C3D4\n", encoding="utf-8")
    (repo / "crcs.txt").write_text("01 A1B2C3D4\n", encoding="utf-8")
    _git(repo, "add", "album.log", "crcs.txt")
    assert _run_hook(repo).returncode == 0


def test_the_hook_refuses_when_it_cannot_list_the_staged_files(repo: Path) -> None:
    """THE regression test: a failing producer must refuse, not pass.

    With the original `... | grep ... || true`, a fatal `git diff` produced an
    empty offender list and the hook exited **0** — so a commit could proceed
    entirely unchecked. This drives that exact state with a `git` shim that fails
    only for `diff`, leaving every other git call real.

    Asserting on the exit code AND on a diagnostic reaching stderr, because a
    silent refusal would be nearly as bad: the operator needs to know the guard
    declined rather than passed.
    """
    assert _GIT is not None
    shim_dir = repo.parent / "shim"
    shim_dir.mkdir()
    shim = shim_dir / "git"
    shim.write_text(
        "#!/usr/bin/env bash\n"
        "# Fail only for `git diff`, so the hook's producer breaks while\n"
        "# everything else behaves normally.\n"
        'if [ "${1:-}" = "diff" ]; then\n'
        '  echo "fatal: bad object deadbeef" >&2\n'
        "  exit 128\n"
        "fi\n"
        f'exec {_GIT} "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)

    (repo / "notes.md").write_text("# text\n", encoding="utf-8")
    _git(repo, "add", "notes.md")

    result = _run_hook(repo, extra_path=shim_dir)

    assert result.returncode != 0, (
        "the hook exited 0 while `git diff` was failing, so it vouched for a "
        "commit it never inspected — fail-OPEN on Critical Rule #8. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert (
        "could not list" in result.stderr.lower() or "blocked" in result.stderr.lower()
    ), (
        "the hook refused but said nothing useful, so the operator cannot tell a "
        f"refusal from a crash: {result.stderr!r}"
    )


def test_the_shim_itself_is_not_what_causes_the_refusal(repo: Path) -> None:
    """Non-triviality for the test above: the shim must be transparent otherwise.

    If the shim broke *every* git call, the previous test would pass for the wrong
    reason — it would prove only that a wrecked PATH breaks the hook, not that a
    failing producer is now refused. So the same shim, with `diff` allowed
    through, must let an ordinary commit pass.
    """
    assert _GIT is not None
    shim_dir = repo.parent / "shim_ok"
    shim_dir.mkdir()
    shim = shim_dir / "git"
    shim.write_text(f'#!/usr/bin/env bash\nexec {_GIT} "$@"\n', encoding="utf-8")
    shim.chmod(0o755)

    (repo / "notes.md").write_text("# text\n", encoding="utf-8")
    _git(repo, "add", "notes.md")

    result = _run_hook(repo, extra_path=shim_dir)
    assert result.returncode == 0, (
        "a pass-through git shim broke the hook, so the refusal test above proves "
        f"nothing about a failing producer. stderr={result.stderr!r}"
    )


def test_the_hook_and_the_ci_gate_share_one_extension_pattern() -> None:
    """Two guards, one list — so they are compared rather than trusted to match.

    `ci.yml`'s media-guard says "Same audio-extension pattern as
    .githooks/pre-commit". That sentence is not a mechanism. Two lists that must
    be identical and are maintained separately is precisely how `release.yml`'s
    two tag-shape lists diverged invisibly for the whole v0.x line.
    """
    hook_text = HOOK.read_text(encoding="utf-8")
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    def _pattern(text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("pattern=") and "flac" in stripped:
                return stripped.split("=", 1)[1].strip().strip("'\"")
        return ""

    hook_pattern = _pattern(hook_text)
    ci_pattern = _pattern(ci_text)
    assert hook_pattern, "no audio pattern found in the hook — this test is broken"
    assert ci_pattern, "no audio pattern found in ci.yml — this test is broken"
    assert hook_pattern == ci_pattern, (
        "the hook and the CI gate disagree about which extensions are audio, so "
        "one of them lets a format through that the other blocks.\n"
        f"  hook: {hook_pattern}\n  ci:   {ci_pattern}"
    )
