"""The CHANGELOG gate's Dependabot exemption holds under merge commits.

**Why this exists (2026-10-12).** The owner turned squash merging off: every pull
request now merges with a merge commit. The `changelog` job in `ci.yml` exempted a
Dependabot bump on a push to `main` by the HEAD COMMIT's author, which a squash
kept as `dependabot[bot]`. A merge commit's author is whoever pressed merge, so
under the new setting that key would have failed `main`'s CI on every Dependabot
merge, and `release.yml` refuses to release from a `main` whose CI is red.

The exemption now reads the commits the push brings in: it applies when every
non-merge commit in the range is Dependabot's. On a pull request it reads the PR's
author or its `dependabot/*` branch, never `github.actor`, which is whoever last
re-ran the job.

These tests run the step's OWN script, extracted from `ci.yml`, against a real
temporary repository, so they test the gate as CI runs it, not a copy of its rule.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
CI_YML: Final[Path] = REPO_ROOT / ".github" / "workflows" / "ci.yml"
STEP_NAME: Final[str] = "Require a CHANGELOG entry (or an explicit opt-out)"
DEPENDABOT: Final[str] = "dependabot[bot]"


def _step_script() -> str:
    """The `run: |` block of the changelog step, dedented, read from `ci.yml`.

    Extracted by indentation rather than a YAML parser, because PyYAML is not one
    of this project's dependencies. The block ends at the first line indented
    less than its own first line.
    """
    lines = CI_YML.read_text(encoding="utf-8").splitlines()
    start = next(
        i for i, ln in enumerate(lines) if ln.strip() == f"- name: {STEP_NAME}"
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
    script = "\n".join(body)
    # Floor: an extraction that found nothing would make every case below pass
    # or fail for a reason that has nothing to do with the exemption.
    assert "dependabot" in script and "CHANGELOG.md" in script, script[:400]
    return script


def _git(repo: Path, *args: str, author: str = "Maintainer") -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": author,
        "GIT_AUTHOR_EMAIL": f"{author}@example.invalid",
        "GIT_COMMITTER_NAME": "Maintainer",
        "GIT_COMMITTER_EMAIL": "maintainer@example.invalid",
    }
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    ).stdout.strip()


def _commit(repo: Path, name: str, author: str, *, changelog: bool = False) -> str:
    (repo / name).write_text(f"{name}\n", encoding="utf-8")
    _git(repo, "add", name)
    if changelog:
        with (repo / "CHANGELOG.md").open("a", encoding="utf-8") as fh:
            fh.write(f"- {name}\n")
        _git(repo, "add", "CHANGELOG.md")
    _git(repo, "commit", "-q", "-m", f"change {name}", author=author)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    _git(tmp_path, "add", "CHANGELOG.md")
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def _merge(repo: Path, branch_commits: list[tuple[str, str]]) -> tuple[str, str]:
    """Branch off main, add commits, merge back with a merge commit.

    Returns (base, merge) — the push range CI would see.
    """
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "switch", "-q", "-c", "topic")
    for name, author in branch_commits:
        _commit(repo, name, author)
    _git(repo, "switch", "-q", "main")
    _git(repo, "merge", "-q", "--no-ff", "-m", "Merge pull request", "topic")
    return base, _git(repo, "rev-parse", "HEAD")


def _run(repo: Path, **env: str) -> subprocess.CompletedProcess[str]:
    full = {
        **os.environ,
        "EVENT": "push",
        "PUSH_BEFORE": "",
        "PR_BASE": "",
        "PR_HEAD": "",
        "PR_TITLE": "",
        "PR_AUTHOR": "",
        "HEAD_REF": "",
        "GITHUB_SHA": "",
        **env,
    }
    return subprocess.run(
        ["bash", "-c", _step_script()],
        cwd=repo,
        capture_output=True,
        text=True,
        env=full,
        timeout=60,
    )


def test_a_dependabot_pr_merged_with_a_merge_commit_is_exempt(repo: Path) -> None:
    base, merge = _merge(repo, [("bump.txt", DEPENDABOT)])
    assert _git(repo, "log", "-1", "--format=%an", merge) == "Maintainer"
    done = _run(repo, PUSH_BEFORE=base, GITHUB_SHA=merge)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "Dependency bump" in done.stdout


def test_a_squashed_dependabot_commit_is_still_exempt(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "bump.txt", DEPENDABOT)
    done = _run(repo, PUSH_BEFORE=base, GITHUB_SHA=head)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "Dependency bump" in done.stdout


def test_a_human_merge_without_a_changelog_entry_fails(repo: Path) -> None:
    base, merge = _merge(repo, [("feature.txt", "Someone")])
    done = _run(repo, PUSH_BEFORE=base, GITHUB_SHA=merge)
    assert done.returncode == 1, done.stdout + done.stderr
    assert "No CHANGELOG.md entry" in done.stdout


def test_a_dependabot_range_with_one_human_commit_is_not_exempt(repo: Path) -> None:
    """The exemption needs EVERY non-merge commit to be Dependabot's."""
    base, merge = _merge(repo, [("bump.txt", DEPENDABOT), ("extra.txt", "Someone")])
    done = _run(repo, PUSH_BEFORE=base, GITHUB_SHA=merge)
    assert done.returncode == 1, done.stdout + done.stderr


def test_a_human_merge_with_a_changelog_entry_passes(repo: Path) -> None:
    """Positive control: the gate itself still passes a real entry."""
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "switch", "-q", "-c", "topic")
    _commit(repo, "feature.txt", "Someone", changelog=True)
    _git(repo, "switch", "-q", "main")
    _git(repo, "merge", "-q", "--no-ff", "-m", "Merge pull request", "topic")
    merge = _git(repo, "rev-parse", "HEAD")
    done = _run(repo, PUSH_BEFORE=base, GITHUB_SHA=merge)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "gained" in done.stdout


def test_a_pull_request_opened_by_dependabot_is_exempt(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "bump.txt", DEPENDABOT)
    done = _run(
        repo,
        EVENT="pull_request",
        PR_BASE=base,
        PR_HEAD=head,
        PR_AUTHOR=DEPENDABOT,
        HEAD_REF="renamed-branch",
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "Dependency bump" in done.stdout


def test_a_human_pull_request_is_not_exempt_whoever_reruns_it(repo: Path) -> None:
    """`github.actor` is not read: a re-run by anyone does not exempt a PR."""
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "feature.txt", "Someone")
    done = _run(
        repo,
        EVENT="pull_request",
        PR_BASE=base,
        PR_HEAD=head,
        PR_AUTHOR="someone",
        HEAD_REF="claude/session-x",
        ACTOR=DEPENDABOT,
    )
    assert done.returncode == 1, done.stdout + done.stderr
