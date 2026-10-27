"""`release.yml`'s steps that use git, run for real against throwaway repositories.

**Why this exists (the 2026-10-27 review).** Item 1.5: the CI gate checked that a
commit's checks were green, and a commit on any branch has green checks once its
pull request ran, so a release could be cut from a branch that never reached
`main`. The *branch gate* now refuses that. Item 2.8: `gh release create
--target` made every tag lightweight (no tagger, no date, no message). The *tag
step* now makes an annotated tag on the release commit, and the publish step uses
`--verify-tag`.

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
TAG_STEP: Final[str] = "Tag the release commit (annotated)"
PUBLISH_STEP: Final[str] = "Publish to GitHub Release"
TAG: Final[str] = "v0.7.999"
BOT: Final[str] = "github-actions[bot]"


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


# --- the annotated tag (item 2.8) --------------------------------------------


def _tag_env(sha: str) -> dict[str, str]:
    return {"TAG": TAG, "SHA": sha, "GH_TOKEN": "not-a-real-token"}


def _remote_tag(origin: _Origin) -> tuple[str, str, str]:
    """(object type, commit it points to, tagger name) of `TAG` in the bare origin."""
    kind = _git(origin.bare, "cat-file", "-t", f"refs/tags/{TAG}")
    commit = _git(origin.bare, "rev-parse", f"refs/tags/{TAG}^{{commit}}")
    tagger = _git(
        origin.bare, "for-each-ref", "--format=%(taggername)", f"refs/tags/{TAG}"
    )
    return kind, commit, tagger


def test_a_new_release_gets_an_annotated_tag_on_its_commit(
    origin: _Origin, tmp_path: Path
) -> None:
    clone = origin.shallow_clone(tmp_path, "main")
    code, out = _run_step(TAG_STEP, clone, **_tag_env(origin.d))
    assert code == 0, out
    assert _remote_tag(origin) == ("tag", origin.d, BOT)
    assert f"created annotated {TAG}" in out


def test_a_re_run_on_the_same_commit_uses_the_tag_and_moves_nothing(
    origin: _Origin, tmp_path: Path
) -> None:
    first = origin.shallow_clone(tmp_path, "main")
    assert _run_step(TAG_STEP, first, **_tag_env(origin.d))[0] == 0
    before = _git(origin.bare, "rev-parse", f"refs/tags/{TAG}")
    again = tmp_path / "again"
    _git(tmp_path, "clone", "-q", "--depth", "1", origin.url, str(again))
    code, out = _run_step(TAG_STEP, again, **_tag_env(origin.d))
    assert code == 0, out
    assert "already exists" in out
    assert _git(origin.bare, "rev-parse", f"refs/tags/{TAG}") == before


def test_a_tag_on_another_commit_is_refused(origin: _Origin, tmp_path: Path) -> None:
    """A tag here cannot move (the `v*` ruleset), so the fix is a new version."""
    first = origin.shallow_clone(tmp_path, "rel")
    assert _run_step(TAG_STEP, first, **_tag_env(origin.b))[0] == 0
    later = origin.shallow_clone(tmp_path, "main")
    code, out = _run_step(TAG_STEP, later, **_tag_env(origin.d))
    assert code == 1, out
    assert f"already exists on {origin.b}, not on {origin.d}" in out
    assert _remote_tag(origin)[1] == origin.b


def test_a_lightweight_tag_someone_pushed_is_used_with_a_warning(
    origin: _Origin, tmp_path: Path
) -> None:
    """A hand-pushed tag (the `push: tags` trigger) is not replaced, only flagged."""
    seed = tmp_path / "seed"
    _git(seed, "tag", TAG, origin.d)
    _git(seed, "push", "-q", "origin", f"refs/tags/{TAG}")
    clone = origin.shallow_clone(tmp_path, "main")
    code, out = _run_step(TAG_STEP, clone, **_tag_env(origin.d))
    assert code == 0, out
    assert "::warning::" in out and "LIGHTWEIGHT" in out
    assert _remote_tag(origin)[0] == "commit"


def test_an_unreadable_remote_is_a_refusal(origin: _Origin, tmp_path: Path) -> None:
    clone = origin.shallow_clone(tmp_path, "main")
    _git(clone, "remote", "set-url", "origin", f"file://{tmp_path / 'gone.git'}")
    code, out = _run_step(TAG_STEP, clone, **_tag_env(origin.d))
    assert code == 1, out
    assert f"Could not read tag {TAG}" in out


def test_the_publish_step_verifies_the_tag_instead_of_making_one() -> None:
    """`--target` would let GitHub make a lightweight tag if ours were missing."""
    publish = _step_script(PUBLISH_STEP)
    assert "--verify-tag" in publish
    assert "--target" not in publish
    text = RELEASE_YML.read_text(encoding="utf-8")
    # After every gate (the attestation check is the last), before the publish.
    assert (
        text.index("- name: Check the attestation as the updater will")
        < text.index(f"- name: {TAG_STEP}")
        < text.index(f"- name: {PUBLISH_STEP}")
    )
