#!/usr/bin/env python3
"""Check the evidence manifest, the `evidence` branch, and a move (HR-2 §3-§5, §8a).

**Why this exists (HR-2, agreed 2026-10-14).** Run evidence moves off the default
branch onto an orphan branch named `evidence`, and `docs/evidence-manifest.tsv`
on the default branch says, one row per file, where each one went and what it
hashes to. Laps cite those files by commit and SHA-256, so the manifest is a
promise every later lap leans on. These checks are what keep it one:

* ``format``   -- the manifest is HR-2 §4's shape; with ``--base REF``, also
  append-only against REF: every row REF held is still here, unchanged.
* ``rows``     -- every row (or, with ``--since REF``, every row added since REF)
  is checked against its file at its commit: the bytes and the SHA-256 match,
  and the commit is on `evidence` (§8a). The commit is fetched by hash when this
  clone does not hold it, into a temporary repository, never into this one.
* ``branch``   -- `evidence` is HR-2 §3's shape: one root, each later commit has
  the previous tip as its only parent, and adds files without changing or
  removing any.
* ``tags``     -- no tag points at or reaches an evidence commit (§8a).
* ``laps``     -- every lap citing a file with a manifest row passes the lap
  checker; run with ``HR2_EVIDENCE_STRICT=1`` in CI, so an evidence citation that
  cannot be fetched fails instead of going unchecked (§6b).
* ``unchanged`` -- HR-2.1 b, before the removal merges: every moved folder the
  default branch still holds has the same tree there as at its evidence commit.
* ``move``     -- HR-2 §5d, after a move: for every moved folder, its tree at the
  last default commit is the tree at the evidence commit, and every path the
  removal commit deletes has exactly one manifest row.

``unchanged`` and ``move`` compare trees across the move and live in
``evidence_trees.py``; they are run from here so there is one command line.

Every check refuses rather than passes on nothing: a ``rows`` run with rows to
check and none examined, or a ``move`` naming no folders, fails.

    python3 scripts/evidence_manifest.py format --base origin/main
    python3 scripts/evidence_manifest.py rows --since origin/main
    python3 scripts/evidence_manifest.py branch
    python3 scripts/evidence_manifest.py tags
    python3 scripts/evidence_manifest.py unchanged --ref origin/main
    python3 scripts/evidence_manifest.py move --removal <commit> <folder>...

Exit 0 when every check held, 1 when one did not, 2 when it could not be run.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))
from laplang.evidence import (  # needs the path line above
    EVIDENCE_BRANCH,
    MANIFEST_PATH,
    Fetcher,
    Row,
    parse_manifest,
)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]

#: What HR-2's first move takes off the default branch, as an ENUMERATED list
#: (§5b: never a pattern, because `git ls-tree` reads `docs/rig-*` literally,
#: prints nothing and exits 0). Whole run folders: the evidence commit holds each
#: one entire, and the default branch keeps only the files `stays_on_default`
#: names (HR-2 §5a and HR-2.1 a). `outbound/artifacts` is one of them since
#: HR-2.1 a: its six round-15 logs move, and `lsl-amendments-1.md`, a
#: specification the lap checker implements, stays on both branches.
MOVING_FOLDERS: Final[tuple[str, ...]] = (
    "docs/handshake/artifacts-round-07",
    "docs/handshake/artifacts-round-07-lap-29",
    "docs/handshake/artifactsround08",
    "docs/handshake/artifactsround26",
    "docs/handshake/artifactsround27",
    "docs/handshake/artifactsround28",
    "docs/handshake/artifactsround29",
    "docs/handshake/artifactsround30",
    "docs/handshake/artifactsround31",
    "docs/handshake/artifactsround32",
    "docs/handshake/outbound/artifacts",
)
#: Files in a moving folder that the default branch keeps, besides every README
#: (HR-2.1 a: "a specification like outbound/artifacts/lsl-amendments-1.md").
STAYS: Final[frozenset[str]] = frozenset(
    {"docs/handshake/outbound/artifacts/lsl-amendments-1.md"}
)


def stays_on_default(path: str) -> bool:
    """Does `path`, inside a moving folder, stay on the default branch too?
    A folder's README is its index (HR-2 §5a); `STAYS` holds the rest."""
    return path.rsplit("/", 1)[-1] == "README.md" or path in STAYS


#: Rows of one commit at which `rows` downloads the whole commit once rather
#: than each file's blob lazily, one round trip apiece.
PREFETCH_AT: Final[int] = 20
#: Generous: a blobless fetch of one commit over the network.
GIT_TIMEOUT_S: Final[int] = 300


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git in `root`, bounded, never raising on a non-zero exit."""
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_S,
        check=False,
    )


def manifest_text(root: Path, ref: str | None) -> str | None:
    """The manifest at `ref`, or in the working tree when `ref` is None."""
    if ref is None:
        path = root / MANIFEST_PATH
        return path.read_text(encoding="utf-8") if path.is_file() else None
    shown = git(root, "show", f"{ref}:{MANIFEST_PATH}")
    return shown.stdout if shown.returncode == 0 else None


def evidence_ref(root: Path) -> str | None:
    """The `evidence` branch this clone holds: local, else origin's."""
    for ref in (
        f"refs/heads/{EVIDENCE_BRANCH}",
        f"refs/remotes/origin/{EVIDENCE_BRANCH}",
    ):
        if git(root, "rev-parse", "--verify", "--quiet", ref).returncode == 0:
            return ref
    return None


def check_format(root: Path, base: str | None) -> list[str]:
    text = manifest_text(root, None)
    if text is None:
        return [] if base is None else _base_rows_kept(root, base, {})
    rows, problems = parse_manifest(text)
    if base is not None:
        problems += _base_rows_kept(root, base, rows)
    return problems


def _base_rows_kept(root: Path, base: str, rows: dict[str, Row]) -> list[str]:
    """Append-only (§4): every row `base` held is here, byte for byte."""
    before = manifest_text(root, base)
    if before is None:
        return []
    old, _ = parse_manifest(before)
    problems: list[str] = []
    for path, row in old.items():
        if path not in rows:
            problems.append(f"{path}: its row at {base} has been removed")
        elif rows[path] != row:
            problems.append(f"{path}: its row at {base} has been changed")
    return problems


def check_rows(root: Path, since: str | None) -> tuple[list[str], int]:
    """Every row (added since `since`) against its file; (problems, examined)."""
    text = manifest_text(root, None)
    if text is None:
        return [], 0
    rows, problems = parse_manifest(text)
    if problems:
        return [f"the manifest is malformed: {p}" for p in problems], 0
    old: dict[str, Row] = {}
    if since is not None:
        before = manifest_text(root, since)
        old = parse_manifest(before)[0] if before is not None else {}
    fetcher = Fetcher()
    examined = 0
    added = [row for path, row in rows.items() if old.get(path) != row]
    by_commit: dict[str, int] = {}
    for row in added:
        by_commit[row.evidence_commit] = by_commit.get(row.evidence_commit, 0) + 1
    for commit, count in by_commit.items():
        if count >= PREFETCH_AT:
            why = fetcher.prefetch(root, commit)
            if why is not None:
                problems.append(why)
    for row in added:
        path = row.path
        examined += 1
        data = fetcher.read(root, row.evidence_commit, path)
        if isinstance(data, str):
            problems.append(f"{path}: {data}")
            continue
        if len(data) != row.size:
            problems.append(f"{path}: {len(data)} bytes, its row says {row.size}")
        got = hashlib.sha256(data).hexdigest()
        if got != row.sha256:
            problems.append(f"{path}: hashes {got}, its row says {row.sha256}")
        on = fetcher.reachable_from_evidence(root, row.evidence_commit)
        if on is not True:
            why = on if isinstance(on, str) else f"not on {EVIDENCE_BRANCH}"
            problems.append(f"{path}: {row.evidence_commit[:12]} is {why}")
    return problems, examined


def check_branch(root: Path) -> tuple[list[str], int]:
    """HR-2 §3 over the whole branch; (problems, commits examined)."""
    ref = evidence_ref(root)
    if ref is None:
        return [], 0
    listed = git(root, "rev-list", "--parents", "--reverse", ref)
    if listed.returncode != 0:
        return [f"git could not list {ref}: {listed.stderr.strip()}"], 0
    problems: list[str] = []
    previous: str | None = None
    lines = [line.split() for line in listed.stdout.splitlines() if line.strip()]
    for commit, *parents in lines:
        expected = [] if previous is None else [previous]
        if parents != expected:
            problems.append(
                f"{commit[:12]}: parents {parents or 'none'}, expected "
                f"{expected or 'none (the root)'}"
            )
        if previous is not None:
            changed = git(
                root,
                "diff-tree",
                "--no-commit-id",
                "-r",
                "--name-status",
                "--diff-filter=MDRTC",
                previous,
                commit,
            )
            for line in changed.stdout.splitlines():
                problems.append(f"{commit[:12]} changes or removes a file: {line}")
        previous = commit
    return problems, len(lines)


def check_tags(root: Path) -> list[str]:
    """No tag points at or reaches an evidence commit (§3, §8a)."""
    ref = evidence_ref(root)
    if ref is None:
        return []
    roots = git(root, "rev-list", "--max-parents=0", ref).stdout.split()
    problems: list[str] = []
    for first in roots:
        tagged = git(
            root,
            "for-each-ref",
            "--format=%(refname)",
            "--contains",
            first,
            "refs/tags",
        )
        problems += [
            f"{tag} points at or reaches the evidence branch"
            for tag in tagged.stdout.split()
        ]
    return problems


#: The lap-language rule that resolves an artifact citation (`laplang.check`).
CITATION_RULE: Final[str] = "LSL.4"

#: An evidence citation as a lap writes it: `platterpus@<commit>:<path>`.
_CITATION: Final[re.Pattern[str]] = re.compile(
    r"\bplatterpus@(?P<sha>[0-9a-f]{7,40}):(?P<path>[A-Za-z0-9._/-]+)"
)


def citing_laps(root: Path) -> list[Path]:
    """Every lap, in any direction, that cites a file with a manifest row."""
    text = manifest_text(root, None)
    if text is None:
        return []
    rows, _ = parse_manifest(text)
    found: list[Path] = []
    for lap in sorted((root / "docs" / "handshake").glob("*/round-*.md")):
        body = lap.read_text(encoding="utf-8", errors="replace")
        if any(m.group("path") in rows for m in _CITATION.finditer(body)):
            found.append(lap)
    return found


def check_laps(root: Path) -> tuple[list[str], int]:
    """Re-check every lap that cites our evidence (§8a: "runs every check that
    reads evidence"). Under ``HR2_EVIDENCE_STRICT=1`` a citation that cannot be
    fetched is refused here rather than left unchecked."""
    from laplang.cli import check_path

    problems: list[str] = []
    laps = citing_laps(root)
    for lap in laps:
        checked = check_path(lap, root=root)
        for p in checked.problems:
            # Citation resolution only. A lap's other findings are its own
            # round's business, judged when it was sent; re-trying old laps on
            # every rule here would fail this job for something it is not about.
            if p.rule == CITATION_RULE and p.severity in ("REFUSED", "CANNOT"):
                problems.append(f"{lap.name}:{p.line} [{p.rule}] {p.message}")
    return problems, len(laps)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    sub = parser.add_subparsers(dest="mode", required=True)
    fmt = sub.add_parser("format")
    fmt.add_argument("--base")
    rows = sub.add_parser("rows")
    rows.add_argument("--since")
    sub.add_parser("branch")
    sub.add_parser("tags")
    sub.add_parser("laps")
    unchanged = sub.add_parser("unchanged")
    unchanged.add_argument("--ref", default="origin/main")
    move = sub.add_parser("move")
    move.add_argument("--removal", required=True)
    move.add_argument("folders", nargs="*")
    args = parser.parse_args(argv)
    # The two tree checks live in their own module, which builds on this one's
    # plumbing; importing it here rather than at the top keeps that one-way.
    import evidence_trees

    root: Path = args.root
    examined: int | None = None
    if args.mode == "format":
        problems = check_format(root, args.base)
    elif args.mode == "rows":
        problems, examined = check_rows(root, args.since)
    elif args.mode == "branch":
        problems, examined = check_branch(root)
    elif args.mode == "tags":
        problems = check_tags(root)
    elif args.mode == "laps":
        problems, examined = check_laps(root)
    elif args.mode == "unchanged":
        problems, examined = evidence_trees.check_unchanged(root, args.ref)
    else:
        problems = evidence_trees.check_move(root, args.removal, args.folders)
    for problem in problems:
        print(f"FAIL {problem}")
    tail = f", {examined} examined" if examined is not None else ""
    print(f"evidence {args.mode}: {len(problems)} problem(s){tail}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
