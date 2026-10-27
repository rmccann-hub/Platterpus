#!/usr/bin/env python3
"""Build the evidence commit for HR-2's move, and the manifest rows that go with it.

**Why this exists (HR-2 §5, agreed 2026-10-14).** The first move takes the run
folders off the default branch onto the orphan `evidence` branch. §5 fixes how,
so that either side can rebuild the other's commit and compare IDs:

* **b.** from an ENUMERATED list (`evidence_manifest.MOVING_FOLDERS`), never a
  pattern; each entry must yield at least one file, so
  a misspelt folder fails here instead of moving nothing. It is built in a
  temporary clone made with ``git clone --depth 1 --single-branch``: the files'
  blobs are already on the remote, in the default branch's history, so a push
  sends only trees and one commit.
* **c.** author and committer ``evidence <evidence@invalid>``, both dates the
  instant round 33's lap 1 fixes, set in all six ``GIT_AUTHOR_*`` and
  ``GIT_COMMITTER_*`` variables. The message is derived from the base commit and
  the list, so it is reproducible too.
* **d.** before the push, the commit's file count and bytes are checked against
  the manifest rows built from the same tree; ``evidence_manifest.py move``
  checks the rest after the push.

**This builds; it never pushes.** Pushing to `evidence` is a separate, deliberate
act under the operator's standing permission (adding commits only; never
delete, force-push or tag it), done from the temporary clone this leaves behind:

    python3 scripts/evidence_move.py build --date 2026-10-15T12:00:00Z --out /tmp/ev
    python3 scripts/evidence_move.py removal --base <the build's base>
    git -C /tmp/ev/clone push origin <commit>:refs/heads/evidence

The rows land in ``<out>/manifest-rows.tsv``; the removal pull request merges
them into ``docs/evidence-manifest.tsv`` (sorted, append-only) and deletes the
moved files, keeping each folder's README (§5a).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_manifest  # needs the path line above
from laplang.evidence import HEADER

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
IDENTITY_NAME: Final[str] = "evidence"
IDENTITY_EMAIL: Final[str] = "evidence@invalid"
GIT_TIMEOUT_S: Final[int] = 600


@dataclass(frozen=True)
class Entry:
    """One file of the move: its path, blob id and size at the base commit."""

    path: str
    mode: str
    blob: str
    size: int


def _git(
    root: Path, *args: str, env: dict[str, str] | None = None, stdin: str = ""
) -> str:
    done = subprocess.run(
        ["git", "-C", str(root), *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=GIT_TIMEOUT_S,
        check=False,
        env=env,
    )
    if done.returncode != 0:
        raise SystemExit(f"git {' '.join(args[:3])} failed: {done.stderr.strip()}")
    return done.stdout


def moving_list() -> list[str]:
    return list(evidence_manifest.MOVING_FOLDERS)


def entries_at(root: Path, base: str, listed: Sequence[str]) -> list[Entry]:
    """Every file under each listed path at `base`; refuse an entry that has none."""
    out = _git(root, "ls-tree", "-r", "-l", "-z", "--full-tree", base, "--", *listed)
    entries: list[Entry] = []
    for record in filter(None, out.split("\0")):
        meta, path = record.split("\t", 1)
        mode, kind, blob, size = meta.split()
        if kind != "blob" or mode not in ("100644", "100755"):
            raise SystemExit(f"{path}: a {kind} with mode {mode} cannot be moved")
        if "\t" in path or "\n" in path:
            raise SystemExit(f"{path!r}: a path with a tab or newline isn't filed (§4)")
        entries.append(Entry(path, mode, blob, int(size)))
    for item in listed:
        if not any(e.path == item or e.path.startswith(item + "/") for e in entries):
            raise SystemExit(
                f"{item}: nothing at {base[:12]} (§5b: refuse, never skip)"
            )
    return sorted(entries, key=lambda e: e.path)


def message(base: str, listed: Sequence[str]) -> str:
    return f"evidence: HR-2 move from platterpus@{base}\n\n" + "\n".join(listed) + "\n"


def identity_env(date: str) -> dict[str, str]:
    env = dict(os.environ)
    for who in ("AUTHOR", "COMMITTER"):
        env[f"GIT_{who}_NAME"] = IDENTITY_NAME
        env[f"GIT_{who}_EMAIL"] = IDENTITY_EMAIL
        env[f"GIT_{who}_DATE"] = date
    return env


def build(
    base: str, date: str, clone: Path, parent: str | None
) -> tuple[str, list[Entry]]:
    """The evidence commit, made in `clone`, and the entries it holds."""
    listed = moving_list()
    entries = entries_at(clone, base, listed)
    index = clone / ".git" / "hr2-move-index"
    env = identity_env(date)
    env["GIT_INDEX_FILE"] = str(index)
    if parent is None:
        _git(clone, "read-tree", "--empty", env=env)
    else:
        _git(clone, "read-tree", parent, env=env)
    lines = "".join(f"{e.mode} {e.blob}\t{e.path}\n" for e in entries)
    _git(clone, "update-index", "--add", "--index-info", env=env, stdin=lines)
    tree = _git(clone, "write-tree", env=env).strip()
    args = ["commit-tree", tree, "-m", message(base, listed)]
    if parent is not None:
        args[2:2] = ["-p", parent]
    commit = _git(clone, *args, env=env).strip()
    return commit, entries


def check_built(clone: Path, commit: str, entries: Sequence[Entry]) -> list[str]:
    """§5d before the push: the commit holds exactly these files, these bytes."""
    out = _git(clone, "ls-tree", "-r", "-l", "-z", commit)
    held = {}
    for record in filter(None, out.split("\0")):
        meta, path = record.split("\t", 1)
        held[path] = int(meta.split()[3])
    problems: list[str] = []
    want = {e.path: e.size for e in entries}
    for path, size in want.items():
        if held.get(path) != size:
            problems.append(
                f"{path}: {held.get(path)} bytes in the commit, {size} wanted"
            )
    if sum(want.values()) != sum(held[p] for p in want if p in held):
        problems.append("byte totals differ")
    return problems


def rows(clone: Path, commit: str, base: str, entries: Sequence[Entry]) -> str:
    """The manifest rows (§4), sha256 read from the blobs themselves."""
    import hashlib

    lines = [HEADER]
    for e in entries:
        data = subprocess.run(
            ["git", "-C", str(clone), "cat-file", "blob", e.blob],
            capture_output=True,
            check=True,
            timeout=GIT_TIMEOUT_S,
        ).stdout
        if len(data) != e.size:
            raise SystemExit(f"{e.path}: read {len(data)} bytes, ls-tree said {e.size}")
        digest = hashlib.sha256(data).hexdigest()
        lines.append(f"{e.path}\t{e.size}\t{digest}\t{commit}\t{base}")
    return "\n".join(lines) + "\n"


def removal(root: Path, base: str) -> list[str]:
    """What the removal pull request deletes (HR-2 §5a, HR-2.1 a): every file of
    every moving folder at `base`, except those that stay on the default branch.
    The same enumerated list and the same predicate the builder and the move
    check use, so the three cannot disagree about what moved."""
    entries = entries_at(root, base, moving_list())
    return [e.path for e in entries if not evidence_manifest.stays_on_default(e.path)]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    r = sub.add_parser("removal", help="print the paths the removal deletes")
    r.add_argument("--base", default="HEAD")
    b = sub.add_parser("build")
    b.add_argument("--date", required=True, help="round 33 lap 1's instant (§5c)")
    b.add_argument("--base", default="origin/main")
    b.add_argument("--url", help="the repository to clone (default: origin's URL)")
    b.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    base = _git(REPO_ROOT, "rev-parse", "--verify", f"{args.base}^{{commit}}").strip()
    if args.mode == "removal":
        for path in removal(REPO_ROOT, base):
            print(path)
        return 0
    url = args.url or _git(REPO_ROOT, "remote", "get-url", "origin").strip()
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=False)
    clone = out / "clone"
    remote_evidence = _git(REPO_ROOT, "ls-remote", url, "refs/heads/evidence").split()
    parent = remote_evidence[0] if remote_evidence else None
    branch = "evidence" if parent else "main"
    _git(
        out,
        "clone",
        "--depth",
        "1",
        "--single-branch",
        "--branch",
        branch,
        "--no-checkout",
        url,
        str(clone),
    )
    if parent is None and _git(clone, "rev-parse", "HEAD").strip() != base:
        raise SystemExit(
            f"the clone's main is not {base[:12]}: build from main's tip, or move it"
        )
    commit, entries = build(base, args.date, clone, parent)
    problems = check_built(clone, commit, entries)
    for problem in problems:
        print(f"FAIL {problem}")
    if problems:
        return 1
    (out / "manifest-rows.tsv").write_text(rows(clone, commit, base, entries))
    total = sum(e.size for e in entries)
    print(f"evidence commit {commit}")
    print(
        f"{len(entries)} files, {total} bytes, base {base}, parent {parent or 'none'}"
    )
    print(f"rows: {out / 'manifest-rows.tsv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
