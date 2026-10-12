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

**After the 2026-10-12 history rewrite every one of our commit IDs changed**, and
the citations kept their old IDs, because a sent lap is never edited. So a token
is first looked up in the commit map `git filter-repo` wrote
(`docs/handshake/commit-map-<date>.txt`, read by `scripts/laplang/commit_map.py`),
and the commit it maps to is the one that must resolve and be reachable. Old
before new: in a clone made before the rewrite, the old ID still resolves to the
old commit, which `HEAD` no longer reaches.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
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

#: How many old IDs the rewrite's map must hold. The rewrite of 2026-10-12
#: changed every commit reachable from `main` and the tags: 1,821 of them. A map
#: that lost most of its lines would still "translate" the few citations it
#: kept, so the size is checked as well as the shape.
MIN_MAPPED_COMMITS: Final[int] = 1800

#: How many citations must reach their commit THROUGH the map. Every citation
#: written before the rewrite does, so a scan where none did has not read the map.
MIN_CITATIONS_THROUGH_MAP: Final[int] = 150

COMMIT_MAP_PY: Final[Path] = REPO_ROOT / "scripts" / "laplang" / "commit_map.py"

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


def commit_map_module() -> ModuleType:
    """`scripts/laplang/commit_map.py`, loaded by path: it imports nothing else
    from `laplang`, so the tests and the lap checker share one reading of a map."""
    name = "platterpus_commit_map"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, COMMIT_MAP_PY)
    assert spec is not None and spec.loader is not None, COMMIT_MAP_PY
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _resolve(root: Path, tokens: list[str]) -> tuple[dict[str, str | None], int]:
    """Each token's full commit SHA, or None if it names no commit here, and how
    many tokens were old IDs answered through the commit map."""
    if not tokens:
        return {}, 0
    cmap, _ = commit_map_module().load(root)
    asked = [cmap.current(t) or t for t in tokens]
    out = _git(
        root,
        "cat-file",
        "--batch-check=%(objectname) %(objecttype)",
        stdin="".join(f"{q}\n" for q in asked),
    )
    resolved: dict[str, str | None] = {}
    for token, line in zip(tokens, out.splitlines(), strict=True):
        name, _, kind = line.partition(" ")
        resolved[token] = name if kind == "commit" else None
    through_map = sum(1 for t, q in zip(tokens, asked, strict=True) if q != t)
    return resolved, through_map


def cited_commits(
    root: Path,
) -> tuple[dict[str, set[str]], dict[str, set[str]], int]:
    """Scan the tree. Returns (commit SHA -> citing files, unresolved
    `platterpus@` token -> citing files, how many tokens the map answered)."""
    where: dict[str, set[str]] = {}
    prefixed: dict[str, set[str]] = {}
    maps = commit_map_module()
    for path, text in _tracked_text(root).items():
        # A commit map is the lookup table, not a citation. Scanned, its 3,600
        # IDs would all "resolve", and its old IDs alone would satisfy the
        # through-the-map floor below with no real citation read at all.
        if path.startswith(maps.MAP_DIR + "/") and maps.MAP_NAME_RE.match(
            path.rsplit("/", 1)[-1]
        ):
            continue
        for token in set(HEX_RE.findall(text)):
            where.setdefault(token, set()).add(path)
        for token in set(PREFIXED_RE.findall(text)):
            prefixed.setdefault(token, set()).add(path)
    resolved, through_map = _resolve(root, sorted(where.keys() | prefixed.keys()))
    commits: dict[str, set[str]] = {}
    for token, files in where.items():
        sha = resolved.get(token)
        if sha is not None:
            commits.setdefault(sha, set()).update(files)
    missing = {t: f for t, f in prefixed.items() if resolved.get(t) is None}
    return commits, missing, through_map


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


Scan = tuple[dict[str, set[str]], dict[str, set[str]], int]


@pytest.fixture(scope="module")
def scan() -> Scan:
    _require_full_history(REPO_ROOT)
    return cited_commits(REPO_ROOT)


def _describe(found: dict[str, set[str]]) -> str:
    return "\n".join(
        f"  {sha[:12]}  cited in {', '.join(sorted(files)[:3])}"
        for sha, files in sorted(found.items())
    )


def test_the_scan_finds_the_citations(
    scan: Scan,
) -> None:
    commits, _, _ = scan
    assert len(commits) >= MIN_CITED_COMMITS, (
        f"found only {len(commits)} cited commits (floor {MIN_CITED_COMMITS}); a scan "
        "that finds nothing also finds nothing unreachable"
    )


def test_every_cited_commit_is_reachable_from_head(
    scan: Scan,
) -> None:
    commits, _, _ = scan
    stranded = unreachable(REPO_ROOT, commits)
    assert not stranded, (
        f"{len(stranded)} cited commit(s) are not reachable from HEAD. On main this "
        "usually means a pull request was squash-merged; bring the branch's history "
        "in with `git merge -s ours <tip>` (the tree does not change):\n"
        + _describe(stranded)
    )


def test_every_platterpus_citation_resolves(
    scan: Scan,
) -> None:
    _, missing, _ = scan
    real = {t: f for t, f in missing.items() if EXAMPLE_SHAS.get(t) not in f}
    assert not real, (
        "a `platterpus@<sha>` citation names a commit this clone does not have. If "
        "GitHub still holds it (`git fetch origin <full sha>` works for a pull "
        "request's commits), merge it in with `git merge -s ours`:\n" + _describe(real)
    )


def test_the_examples_are_still_only_examples(
    scan: Scan,
) -> None:
    """An allowlist entry whose file no longer uses it is stale, and a stale entry
    is how a real SHA would slip through later."""
    _, missing, _ = scan
    for token, path in EXAMPLE_SHAS.items():
        assert path in missing.get(token, set()), (
            f"{token} is allowlisted for {path}, which no longer cites it"
        )


def test_the_commit_map_is_well_formed_and_complete() -> None:
    """The map the 2026-10-12 rewrite left must read cleanly, be the size the
    rewrite was, and name only commits this clone has.

    `scripts/laplang/commit_map.py` reports a malformed map as sentences rather
    than raising, so a checker keeps working; this is where those sentences fail.
    """
    _require_full_history(REPO_ROOT)
    cmap, problems = commit_map_module().load(REPO_ROOT)
    assert not problems, "the commit map has problems:\n  " + "\n  ".join(problems)
    assert len(cmap.pairs) >= MIN_MAPPED_COMMITS, (
        f"the commit maps ({cmap.sources}) hold {len(cmap.pairs)} old IDs; the "
        f"rewrite changed at least {MIN_MAPPED_COMMITS}"
    )
    news = sorted(set(cmap.pairs.values()))
    kinds = _git(
        REPO_ROOT,
        "cat-file",
        "--batch-check=%(objecttype)",
        stdin="".join(f"{n}\n" for n in news),
    ).splitlines()
    absent = [n[:12] for n, k in zip(news, kinds, strict=True) if k != "commit"]
    assert not absent, (
        f"{len(absent)} new ID(s) in the commit map name no commit here, so every "
        f"citation that maps to them is lost: {absent[:10]}"
    )


def test_citations_written_before_the_rewrite_reach_their_commit_through_the_map(
    scan: Scan,
) -> None:
    """Non-triviality for the scan: every citation written before the rewrite
    names an old ID, so if none went through the map the map was not read, and
    the reachability test above passed on whatever was left."""
    _, _, through_map = scan
    assert through_map >= MIN_CITATIONS_THROUGH_MAP, (
        f"only {through_map} citation(s) resolved through the commit map "
        f"(floor {MIN_CITATIONS_THROUGH_MAP})"
    )


def test_an_old_id_resolves_through_the_map_and_not_without_it(tmp_path: Path) -> None:
    """The mechanism, in a throwaway repository: a citation of an ID that no
    longer exists is lost without a map, and reaches its commit with one."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    current = _commit(root, "base")
    gone = "0123456789abcdef0123456789abcdef01234567"
    (root / "lap.md").write_text(f"see platterpus@{gone[:9]}\n", encoding="utf-8")
    _git(root, "add", "lap.md")
    _git(root, "commit", "-q", "-m", "cite")

    commits, missing, through_map = cited_commits(root)
    assert current not in commits and gone[:9] in missing and through_map == 0

    maps = root / "docs" / "handshake"
    maps.mkdir(parents=True)
    (maps / "commit-map-2026-10-12.txt").write_text(
        f"old new\n{gone} {current}\n", encoding="ascii"
    )
    _git(root, "add", "docs")
    _git(root, "commit", "-q", "-m", "map")
    commits, missing, through_map = cited_commits(root)
    assert current in commits and missing == {} and through_map == 1
    assert unreachable(root, commits) == {}


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

    commits, missing, _ = cited_commits(root)
    assert set(unreachable(root, commits)) == {stranded}
    assert missing == {}

    # The repair this repository used: history in, tree unchanged.
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    _git(root, "merge", "-q", "-s", "ours", "--no-ff", "-m", "keep topic", "topic")
    assert _git(root, "rev-parse", "HEAD^{tree}") == tree
    assert unreachable(root, commits) == {}


# --- Laps that name their own commit by SUBJECT --------------------------------
#
# Rounds 8 to 11 wrote provenance as "Committed to `Platterpus` on
# `claude/session-omka9f` at the commit whose subject is **"…"**", because a file
# cannot carry the hash of the tree that contains it. The fork holds byte-identical
# copies of those laps in its own tree, so each subject is a citation of ours that
# the hex scan above cannot see. Found 2026-09-29, when the operator deleted that
# branch: two of the named commits (`d045bd00`, `b8599c24`) were reachable only
# through `refs/pull/154/head`, because PR #154 had been squash-merged. They were
# brought in with `git merge -s ours`.

#: Our provenance sentence. The subject is bolded and quoted, and it may wrap.
BY_SUBJECT_RE: Final[re.Pattern[str]] = re.compile(
    r"`Platterpus`[^.]{0,80}?at\s+the\s+commit\s+whose\s+subject\s+is\s+"
    r"\*\*\"(?P<subject>[^\"]+?)\"\*\*",
    re.DOTALL,
)

#: Subjects a lap paraphrased: no commit anywhere carries these words. The laps
#: themselves are on `main` byte for byte (`docs/handshake/verified/`), which is
#: what a reader holding the fork's copy can resolve. Each entry is checked below to
#: be still cited and still unmatched, so the list cannot hide a real stranding.
PARAPHRASED_SUBJECTS: Final[frozenset[str]] = frozenset(
    {
        "docs(handshake): close round 8 and declare GO on round 9",
        "docs(handshake): round 9 lap 10 — GO, the round closes",
    }
)

#: Measured 2026-09-29: eleven provenance lines, seven subjects, in our tree.
MIN_BY_SUBJECT: Final[int] = 8


def by_subject_citations(root: Path) -> dict[str, set[str]]:
    """Subject → the files whose provenance line names it."""
    found: dict[str, set[str]] = {}
    for path, text in _tracked_text(root).items():
        if not path.startswith("docs/handshake/"):
            continue
        for match in BY_SUBJECT_RE.finditer(text):
            subject = " ".join(match.group("subject").split())
            found.setdefault(subject, set()).add(path)
    return found


def unresolved_subjects(root: Path, rev: str, subjects: set[str]) -> set[str]:
    """The subjects no commit reachable from ``rev`` starts with."""
    reachable = _git(root, "log", rev, "--format=%s").splitlines()
    return {s for s in subjects if not any(line.startswith(s) for line in reachable)}


def test_every_lap_that_names_its_commit_by_subject_resolves_through_head() -> None:
    _require_full_history(REPO_ROOT)
    cited = by_subject_citations(REPO_ROOT)
    lines = sum(len(files) for files in cited.values())
    assert lines >= MIN_BY_SUBJECT, (
        f"found {lines} provenance lines, floor {MIN_BY_SUBJECT}"
    )
    missing = unresolved_subjects(REPO_ROOT, "HEAD", set(cited)) - PARAPHRASED_SUBJECTS
    assert not missing, (
        "a lap names its commit by a subject no commit reachable from HEAD carries. "
        "Find it with `git log --all --format='%h %s' | grep -F '<subject>'` (fetch "
        "`refs/pull/*/head` first) and merge it in with `git merge -s ours`:\n"
        + "\n".join(f"  {s!r} in {sorted(cited[s])}" for s in sorted(missing))
    )


def test_the_paraphrased_subjects_are_still_paraphrases() -> None:
    _require_full_history(REPO_ROOT)
    cited = by_subject_citations(REPO_ROOT)
    for subject in PARAPHRASED_SUBJECTS:
        assert subject in cited, f"{subject!r} is allowlisted and no longer cited"
    assert unresolved_subjects(REPO_ROOT, "HEAD", set(PARAPHRASED_SUBJECTS)) == set(
        PARAPHRASED_SUBJECTS
    ), "an allowlisted subject now matches a commit; take it off the list"
