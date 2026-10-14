#!/usr/bin/env python3
"""The two checks that compare a moved folder's tree with its evidence commit.

**Why these are their own module.** ``evidence_manifest.py`` checks the manifest
and the `evidence` branch; these two check the MOVE itself, from either side of
the removal pull request, and are the only checks that read a folder's tree on
the default branch and on `evidence` and compare them:

* ``check_unchanged`` -- HR-2.1 b, BEFORE the removal merges: every moved folder
  the default branch still holds has the same tree there as at its evidence
  commit. A file changed after the build means the removal waits.
* ``check_move``      -- HR-2 §5d, AFTER the removal commit: each moved folder's
  tree at the last default commit is its tree at the evidence commit, and every
  path the removal deletes has a manifest row and is not one that stays.

They are run through ``evidence_manifest.py unchanged`` and ``... move``, so the
command line CI and the move procedure use is one script; this module builds on
that one's plumbing (`git`, `manifest_text`, `MOVING_FOLDERS`,
`stays_on_default`), so what moves and what stays is decided in one place.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_manifest import (  # noqa: E402 - needs the path line above
    MOVING_FOLDERS,
    git,
    manifest_text,
    stays_on_default,
)
from laplang.evidence import (  # noqa: E402 - needs the path line above
    MANIFEST_PATH,
    Fetcher,
    parse_manifest,
)


def check_move(root: Path, removal: str, folders: Sequence[str]) -> list[str]:
    """HR-2 §5d, after the move commit `removal` on the default branch."""
    if not folders:
        return ["no folders named: a move check of nothing is not a check"]
    text = manifest_text(root, removal)
    if text is None:
        return [f"{removal} has no {MANIFEST_PATH}"]
    rows, problems = parse_manifest(text)
    parent = git(root, "rev-parse", f"{removal}^").stdout.strip()
    fetcher = Fetcher()
    for folder in folders:
        item = folder.rstrip("/")
        in_folder = [
            r for p, r in rows.items() if p == item or p.startswith(item + "/")
        ]
        commits = {r.evidence_commit for r in in_folder}
        lasts = {r.last_default_commit for r in in_folder}
        if len(commits) != 1 or len(lasts) != 1:
            problems.append(
                f"{folder}: its rows name {len(commits)} evidence commit(s) and "
                f"{len(lasts)} last default commit(s), not one of each"
            )
            continue
        (evidence,), (last,) = commits, lasts
        if last != parent:
            problems.append(
                f"{folder}: last_default_commit {last[:12]} is not {removal}^"
            )
        a = fetcher.object_id(root, last, item) or ""
        b = fetcher.object_id(root, evidence, item) or ""
        if not a or a != b:
            problems.append(
                f"{folder}: tree {a or '(none)'} at {last[:12]}, "
                f"{b or '(none)'} at {evidence[:12]}"
            )
    deleted = git(
        root,
        "diff-tree",
        "--no-commit-id",
        "-r",
        "--name-only",
        "--diff-filter=D",
        removal,
    ).stdout.split("\n")
    for path in filter(None, deleted):
        if path not in rows:
            problems.append(f"{path}: deleted by {removal[:12]} with no manifest row")
        if stays_on_default(path):
            problems.append(
                f"{path}: deleted by {removal[:12]}, but it stays on the default "
                "branch (HR-2 §5a, HR-2.1 a)"
            )
    return problems


def moved_folder_of(path: str) -> str:
    """The moving folder `path` was moved with, else its own folder."""
    for folder in MOVING_FOLDERS:
        if path.startswith(folder + "/"):
            return folder
    return path.rsplit("/", 1)[0]


def check_unchanged(root: Path, ref: str) -> tuple[list[str], int]:
    """HR-2.1 b, before the removal merges: each moved folder that `ref` (the
    current default branch) still holds has the same tree there as at its
    evidence commit. A difference means a file changed after the build, and the
    removal waits until that is resolved. A folder `ref` no longer holds, or
    holds only what stays on the default branch (its README), has been removed
    already and is not this check's business. (problems, examined)"""
    text = manifest_text(root, None)
    if text is None:
        return [], 0
    rows, problems = parse_manifest(text)
    if problems:
        return [f"the manifest is malformed: {p}" for p in problems], 0
    folders: dict[str, set[str]] = {}
    for row in rows.values():
        if row.last_default_commit:  # moved from the default branch, not filed
            folders.setdefault(moved_folder_of(row.path), set()).add(
                row.evidence_commit
            )
    fetcher = Fetcher()
    examined = 0
    for folder, commits in sorted(folders.items()):
        held = git(root, "rev-parse", "--verify", "--quiet", f"{ref}:{folder}")
        if held.returncode != 0:
            continue
        files = git(root, "ls-tree", "-r", "--name-only", ref, "--", folder)
        if all(stays_on_default(f) for f in files.stdout.split("\n") if f):
            continue  # removed already: only what stays on the default branch is left
        examined += 1
        if len(commits) != 1:
            problems.append(f"{folder}: its rows name {len(commits)} evidence commits")
            continue
        (evidence,) = commits
        theirs = fetcher.object_id(root, evidence, folder)
        if held.stdout.strip() != theirs:
            problems.append(
                f"{folder}: its tree on {ref} is {held.stdout.strip()[:12]}, at the "
                f"evidence commit {evidence[:12]} it is {(theirs or '(none)')[:12]}: "
                "a file changed after the build, so the removal waits (HR-2.1 b)"
            )
    return problems, examined
