"""`release.yml`'s steps that use git, run for real against throwaway repositories.

**Why this exists (the 2026-10-27 review).** Item 1.5: the CI gate checked that a
commit's checks were green, and a commit on any branch has green checks once its
pull request ran, so a release could be cut from a branch that never reached
`main`. The *branch gate* now refuses that.

Each test extracts the step's own `run: |` script from `release.yml`, the way
`tests/test_release_uploads_while_draft.py` does, and runs it with bash inside a
clone of a bare repository made in `tmp_path`. Real git, not a fake: the step's
whole job is what git answers, and a fake would answer what the test expects.

**What the stand-in does that the runner does not.** `origin` is a local bare
repository reached by a `file://` URL instead of github.com, and git's global and
system configuration are switched off so a developer's settings (a signing key,
a hook path) cannot change the answer. The shallow clone is made with
`--depth 1`, as `actions/checkout` makes it.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
RELEASE_YML: Final[Path] = REPO_ROOT / ".github" / "workflows" / "release.yml"
BRANCH_GATE: Final[str] = "Branch gate — refuse to release a commit that is not on main"


def _step_script(step_name: str) -> str:
    """The named step's `run: |` block, dedented, read from `release.yml`."""
    lines = RELEASE_YML.read_text(encoding="utf-8").splitlines()
    start = next(
        i for i, ln in enumerate(lines) if ln.strip() == f"- name: {step_name}"
    )
    run_at = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    body: list[str] = []
    indent: int | None = None
    for line in lines[run_at + 1 :]:
        if line.strip() == "":
            body.append("")
            continue
        here = len(line) - len(line.lstrip(" "))
        if indent is None:
            indent = here
        if here < indent:
            break
        body.append(line[indent:])
    return "\n".join(body)


def _git_env() -> dict[str, str]:
    """An environment where only the test's own git settings apply."""
    return {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
        "GIT_TERMINAL_PROMPT": "0",
    }


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=_git_env(),
        timeout=60,
        check=True,
    )
    return done.stdout.strip()


def _commit(work: Path, name: str) -> str:
    (work / f"{name}.txt").write_text(name, encoding="utf-8")
    _git(work, "add", f"{name}.txt")
    _git(work, "commit", "-q", "-m", name)
    return _git(work, "rev-parse", "HEAD")


class _Origin:
    """A bare `origin` whose `main` has moved on past a commit a release names.

    History: ``a - b - d`` on `main`, ``b - c`` on `feature`, and `rel` at ``b``
    (on `main`, but no longer its tip, as when `main` moves after a dispatch).
    """

    def __init__(self, root: Path) -> None:
        self.bare = root / "origin.git"
        _git(root, "init", "-q", "--bare", "-b", "main", str(self.bare))
        seed = root / "seed"
        _git(root, "clone", "-q", str(self.bare), str(seed))
        _git(seed, "switch", "-q", "-c", "main")
        self.a = _commit(seed, "a")
        self.b = _commit(seed, "b")
        _git(seed, "branch", "rel")
        _git(seed, "switch", "-q", "-c", "feature")
        self.c = _commit(seed, "c")
        _git(seed, "switch", "-q", "main")
        self.d = _commit(seed, "d")
        _git(seed, "push", "-q", "origin", "main", "feature", "rel")
        self.url = f"file://{self.bare}"

    def shallow_clone(self, root: Path, branch: str) -> Path:
        """A one-commit clone of ``branch``, the shape `actions/checkout` makes."""
        dest = root / f"clone-{branch}"
        _git(
            root, "clone", "-q", "--depth", "1", "--branch", branch, self.url, str(dest)
        )
        assert _git(dest, "rev-parse", "--is-shallow-repository") == "true"
        return dest


def _run_step(step: str, cwd: Path, **env: str) -> tuple[int, str]:
    done = subprocess.run(
        ["bash", "-e", "-c", _step_script(step)],
        cwd=cwd,
        capture_output=True,
        text=True,
        env={**_git_env(), **env},
        timeout=120,
    )
    return done.returncode, done.stdout + done.stderr


@pytest.fixture
def origin(tmp_path: Path) -> _Origin:
    return _Origin(tmp_path)


# --- the branch gate (item 1.5) ----------------------------------------------


def test_a_commit_on_main_that_is_no_longer_its_tip_passes(
    origin: _Origin, tmp_path: Path
) -> None:
    """The common real case: `main` moved between the dispatch and the run."""
    clone = origin.shallow_clone(tmp_path, "rel")
    code, out = _run_step(BRANCH_GATE, clone, SHA=origin.b)
    assert code == 0, out
    assert "is on main" in out


def test_a_commit_only_on_a_feature_branch_is_refused(
    origin: _Origin, tmp_path: Path
) -> None:
    clone = origin.shallow_clone(tmp_path, "feature")
    code, out = _run_step(BRANCH_GATE, clone, SHA=origin.c)
    assert code == 1, out
    assert f"{origin.c} is not on main" in out


def test_main_s_own_tip_passes_from_a_full_clone(
    origin: _Origin, tmp_path: Path
) -> None:
    """A clone that already has all of `main` passes too (a hand-run, say)."""
    clone = tmp_path / "full"
    _git(tmp_path, "clone", "-q", origin.url, str(clone))
    code, out = _run_step(BRANCH_GATE, clone, SHA=origin.d)
    assert code == 0, out


def test_a_fetch_that_fails_is_a_refusal_not_a_pass(
    origin: _Origin, tmp_path: Path
) -> None:
    """No answer is not a yes: the gate's tri-state half."""
    clone = origin.shallow_clone(tmp_path, "rel")
    _git(clone, "remote", "set-url", "origin", f"file://{tmp_path / 'gone.git'}")
    code, out = _run_step(BRANCH_GATE, clone, SHA=origin.b)
    assert code == 1, out
    assert "Could not fetch main" in out
    # It stopped at the fetch. Going on would still refuse (merge-base has no
    # `main` to read), but by luck rather than by the step's own decision.
    assert "could not compare" not in out, out


def test_the_branch_gate_fetches_main_alone_and_runs_before_the_build() -> None:
    """A plain `git fetch` would pull the `evidence` branch; and a gate after the
    build would spend the build on a commit it then refuses."""
    script = _step_script(BRANCH_GATE)
    assert '"+refs/heads/main:refs/remotes/origin/main"' in script
    assert "--no-tags" in script
    text = RELEASE_YML.read_text(encoding="utf-8")
    assert text.index(f"- name: {BRANCH_GATE}") < text.index(
        "- name: Build the AppImage"
    )
