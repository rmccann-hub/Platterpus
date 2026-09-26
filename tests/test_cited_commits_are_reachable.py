"""Every commit this repository cites must be reachable from `HEAD`.

**Why this exists.** Laps, TASKS rows and session-log entries cite our own
commits by SHA, and the cyanrip fork's laps cite them too. A citation is only
worth something if a fresh clone can resolve it. For years this repository
squash-merged every pull request, and a squash puts one *new* commit on `main`
and none of the branch's. So each citation of a branch commit lasted exactly as
long as the branch did. Measured 2026-09-26: **47 cited commits were on no
branch at all**. Only GitHub's `refs/pull/N/head` still held them, and a plain
`git clone` does not fetch those refs. One of the 47, `926dcb3`, is cited in the
fork's round 19 lap 1.

They were brought back with `git merge -s ours` (which keeps history and leaves
the tree alone), and session-branch pull requests now merge with a merge
commit (CLAUDE.md, *Commit & PR hygiene*). This test is what holds that in place.

**Where it can fail, and where it cannot.** On a pull request, CI checks out the
merge of the branch into `main`, so every branch commit is an ancestor and this
passes. On `main` after a squash merge, the branch's commits are not ancestors,
so it fails there. That is the same asymmetry `docs/testing.md` §5.bv records,
used on purpose this time: a red `main` is the signal that a squash stranded a
citation. The merge convention is what prevents it; this test detects it.

**What it cannot see.** A short hex token that resolves to no commit here might
be a fork commit, a digest prefix, or one of our commits that is gone for good.
Only the `platterpus@<sha>` form says whose commit it is, so only that form is
required to resolve. Bare tokens are checked for reachability when they resolve
and ignored when they do not.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]

#: A commit-shaped token: 7 to 40 lowercase hex characters standing alone. A
#: 64-character digest has no word boundary inside it, so it never matches.
HEX_RE: Final[re.Pattern[str]] = re.compile(r"\b[0-9a-f]{7,40}\b")

#: The form that names *our* tree, as LSL and the handshake laps write it.
PREFIXED_RE: Final[re.Pattern[str]] = re.compile(r"\bplatterpus@([0-9a-f]{7,40})\b")

#: Placeholders used as examples of the citation form, not citations. Each one is
#: listed with the file that uses it so the list cannot quietly absorb a real SHA.
EXAMPLE_SHAS: Final[dict[str, str]] = {
    "abc1234": "tests/test_handshake_conformance.py",
    "def5678": "tests/test_handshake_conformance.py",
}

#: How many cited commits the scan must find. Measured 159 on 2026-09-26. A scan
#: that finds none reports "nothing unreachable" too, so it needs a floor.
MIN_CITED_COMMITS: Final[int] = 150

GIT_TIMEOUT_S: Final[float] = 60.0


def _git(root: Path, *args: str, stdin: str | None = None) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_S,
        check=True,
    ).stdout


def _tracked_text(root: Path) -> dict[str, str]:
    """Every tracked text file, by path. Binary files are skipped, as grep does."""
    texts: dict[str, str] = {}
    for name in _git(root, "ls-files", "-z").split("\0"):
        if not name:
            continue
        try:
            data = (root / name).read_bytes()
        except OSError:
            continue  # listed but absent from the working tree (e.g. a deleted file)
        if b"\0" in data[:8192]:
            continue
        texts[name] = data.decode("utf-8", errors="replace")
    return texts


def _resolve(root: Path, tokens: list[str]) -> dict[str, str | None]:
    """Each token's full commit SHA, or None if it names no commit here."""
    if not tokens:
        return {}
    out = _git(
        root,
        "cat-file",
        "--batch-check=%(objectname) %(objecttype)",
        stdin="".join(f"{t}\n" for t in tokens),
    )
    resolved: dict[str, str | None] = {}
    for token, line in zip(tokens, out.splitlines(), strict=True):
        name, _, kind = line.partition(" ")
        resolved[token] = name if kind == "commit" else None
    return resolved


def cited_commits(root: Path) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Scan the tree. Returns (commit SHA -> citing files, unresolved
    `platterpus@` token -> citing files)."""
    where: dict[str, set[str]] = {}
    prefixed: dict[str, set[str]] = {}
    for path, text in _tracked_text(root).items():
        for token in set(HEX_RE.findall(text)):
            where.setdefault(token, set()).add(path)
        for token in set(PREFIXED_RE.findall(text)):
            prefixed.setdefault(token, set()).add(path)
    resolved = _resolve(root, sorted(where.keys() | prefixed.keys()))
    commits: dict[str, set[str]] = {}
    for token, files in where.items():
        sha = resolved.get(token)
        if sha is not None:
            commits.setdefault(sha, set()).update(files)
    missing = {t: f for t, f in prefixed.items() if resolved.get(t) is None}
    return commits, missing


def unreachable(root: Path, commits: dict[str, set[str]]) -> dict[str, set[str]]:
    """The cited commits that `HEAD` does not reach."""
    reachable = set(_git(root, "rev-list", "HEAD").split())
    return {sha: files for sha, files in commits.items() if sha not in reachable}


def _require_full_history(root: Path) -> None:
    if _git(root, "rev-parse", "--is-shallow-repository").strip() != "false":
        pytest.skip(
            "shallow clone: a commit missing from it proves nothing (CI fetches the "
            "full history, so this runs there)"
        )


@pytest.fixture(scope="module")
def scan() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    _require_full_history(REPO_ROOT)
    return cited_commits(REPO_ROOT)


def _describe(found: dict[str, set[str]]) -> str:
    return "\n".join(
        f"  {sha[:12]}  cited in {', '.join(sorted(files)[:3])}"
        for sha, files in sorted(found.items())
    )


def test_the_scan_finds_the_citations(
    scan: tuple[dict[str, set[str]], dict[str, set[str]]],
) -> None:
    commits, _ = scan
    assert len(commits) >= MIN_CITED_COMMITS, (
        f"found only {len(commits)} cited commits (floor {MIN_CITED_COMMITS}); a scan "
        "that finds nothing also finds nothing unreachable"
    )


def test_every_cited_commit_is_reachable_from_head(
    scan: tuple[dict[str, set[str]], dict[str, set[str]]],
) -> None:
    commits, _ = scan
    stranded = unreachable(REPO_ROOT, commits)
    assert not stranded, (
        f"{len(stranded)} cited commit(s) are not reachable from HEAD. On main this "
        "usually means a pull request was squash-merged; bring the branch's history "
        "in with `git merge -s ours <tip>` (the tree does not change):\n"
        + _describe(stranded)
    )


def test_every_platterpus_citation_resolves(
    scan: tuple[dict[str, set[str]], dict[str, set[str]]],
) -> None:
    _, missing = scan
    real = {t: f for t, f in missing.items() if EXAMPLE_SHAS.get(t) not in f}
    assert not real, (
        "a `platterpus@<sha>` citation names a commit this clone does not have. If "
        "GitHub still holds it (`git fetch origin <full sha>` works for a pull "
        "request's commits), merge it in with `git merge -s ours`:\n" + _describe(real)
    )


def test_the_examples_are_still_only_examples(
    scan: tuple[dict[str, set[str]], dict[str, set[str]]],
) -> None:
    """An allowlist entry whose file no longer uses it is stale, and a stale entry
    is how a real SHA would slip through later."""
    _, missing = scan
    for token, path in EXAMPLE_SHAS.items():
        assert path in missing.get(token, set()), (
            f"{token} is allowlisted for {path}, which no longer cites it"
        )


def _commit(root: Path, name: str) -> str:
    (root / name).write_text(name, encoding="utf-8")
    _git(root, "add", name)
    _git(root, "commit", "-q", "-m", name)
    return _git(root, "rev-parse", "HEAD").strip()


def test_a_squash_merge_that_strands_a_citation_is_caught(tmp_path: Path) -> None:
    """The failure this file exists for, built in a throwaway repository: a
    branch commit is cited, the branch is squash-merged, and `main` no longer
    reaches the commit."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    _commit(root, "base")
    _git(root, "switch", "-q", "-c", "topic")
    stranded = _commit(root, "work")
    _git(root, "switch", "-q", "main")
    _git(root, "merge", "-q", "--squash", "topic")
    (root / "lap.md").write_text(f"see platterpus@{stranded[:9]}\n", encoding="utf-8")
    _git(root, "add", "lap.md")
    _git(root, "commit", "-q", "-m", "squash of topic")

    commits, missing = cited_commits(root)
    assert set(unreachable(root, commits)) == {stranded}
    assert missing == {}

    # The repair this repository used: history in, tree unchanged.
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    _git(root, "merge", "-q", "-s", "ours", "--no-ff", "-m", "keep topic", "topic")
    assert _git(root, "rev-parse", "HEAD^{tree}") == tree
    assert unreachable(root, commits) == {}
