"""Old commit IDs from before a history rewrite, and the IDs that replaced them.

**Why this exists (2026-10-12).** The owner removed personal information from
this repository's commit metadata with `git filter-repo`. A rewrite gives every
commit a new ID even when, as here, no file changes: a commit's ID is a hash of
its author and committer lines as well as its tree, and every later commit names
the one before it. So all of this repository's commit IDs changed in one go.

Our laps, TASKS rows, session log and the cyanrip fork's laps cite those commits
by their OLD IDs, and a sent lap is never edited (its bytes are hash-pinned and
mirrored in the fork's tree). So the citations stay as written, and each one is
resolved through the map that `git filter-repo` wrote: one line per rewritten
commit, `<old 40-hex ID> <new 40-hex ID>`, committed at
`docs/handshake/commit-map-<YYYY-MM-DD>.txt`. The handshake amendment that
agreed this with the fork is in `docs/cyanrip-handshake.md`.

**Who calls this.** Everything that asks "does this commit ID name one of our
commits?" about a citation: `tests/test_cited_commits_are_reachable.py`, the
`HANDSHAKE-OUR-PIN` check in `tests/test_handshake_tooling.py`, and the lap
checker (`laplang.refs`, `laplang.scratch`). One function, many callers, so they
cannot disagree about what an old ID means.

**This file has no imports from the rest of `laplang`,** so a test can load it
on its own by path.

**Never raises on a malformed map.** It returns the problems as sentences, and
each caller decides what a problem costs (the tests fail on any). A map that
cannot be read must not crash a checker into reporting nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

#: Where the maps live, relative to a repository's root.
MAP_DIR: Final[str] = "docs/handshake"

#: A map's file name. The date is the day of the rewrite, so a second rewrite
#: years later adds a second file rather than editing the first.
MAP_NAME_RE: Final[re.Pattern[str]] = re.compile(
    r"^commit-map-(?P<date>\d{4}-\d{2}-\d{2})\.txt$"
)

#: The first line `git filter-repo` writes to `.git/filter-repo/commit-map`.
HEADER: Final[str] = "old new"

#: One rewritten commit: its old full ID, one space, its new full ID.
LINE_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<old>[0-9a-f]{40}) (?P<new>[0-9a-f]{40})$"
)

#: A citation's shape: 7 to 40 lowercase hex characters.
TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{7,40}$")

#: Shortest prefix a citation can use, and the length the lookup index keys on.
_INDEX_LEN: Final[int] = 7

#: A chain longer than this is a cycle, not a history: no repository is
#: rewritten this many times.
_MAX_HOPS: Final[int] = 16


@dataclass
class CommitMap:
    """Every old ID this repository's maps know, and what replaced it."""

    pairs: dict[str, str] = field(default_factory=dict)
    #: The files the pairs were read from, by name, oldest first.
    sources: list[str] = field(default_factory=list)
    _index: dict[str, list[str]] = field(default_factory=dict, repr=False)

    def _add(self, old: str, new: str) -> None:
        self.pairs[old] = new
        self._index.setdefault(old[:_INDEX_LEN], []).append(old)

    def old_id(self, token: str) -> str | None:
        """The one old full ID `token` abbreviates, or None.

        None when no old ID starts with `token`, and also when more than one
        does: an ambiguous abbreviation names no commit, exactly as git treats
        it.
        """
        if TOKEN_RE.match(token) is None:
            return None
        hits = [
            o for o in self._index.get(token[:_INDEX_LEN], ()) if o.startswith(token)
        ]
        return hits[0] if len(hits) == 1 else None

    def current(self, token: str) -> str | None:
        """The present-day full ID of the commit `token` named before a rewrite.

        Follows the maps in order, so an ID rewritten twice reaches today's ID.
        None when `token` is not an old ID at all; the caller then resolves it
        as it always did.
        """
        old = self.old_id(token)
        if old is None:
            return None
        sha = self.pairs[old]
        for _ in range(_MAX_HOPS):
            nxt = self.pairs.get(sha)
            if nxt is None:
                return sha
            sha = nxt
        return None  # a cycle; `parse_map`'s checks report how it got there


def parse_map(text: str, source: str) -> tuple[list[tuple[str, str]], list[str]]:
    """The pairs in one map file, and every problem with it, as sentences.

    Checked: the header, every line's shape, an old ID listed twice, a commit
    mapped to itself, and an ID that is both old and new in the same file
    (which would make a lookup depend on the order it was asked in).
    """
    problems: list[str] = []
    pairs: list[tuple[str, str]] = []
    lines = text.splitlines()
    if not lines or lines[0].split() != HEADER.split():
        problems.append(f"{source}: the first line must be {HEADER!r}")
        return pairs, problems
    seen: set[str] = set()
    for number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        match = LINE_RE.match(line)
        if match is None:
            problems.append(
                f"{source}:{number}: not '<old 40-hex> <new 40-hex>': {line[:100]!r}"
            )
            continue
        old, new = match["old"], match["new"]
        if old == new:
            problems.append(f"{source}:{number}: {old[:12]} is mapped to itself")
            continue
        if old in seen:
            problems.append(f"{source}:{number}: {old[:12]} is listed twice")
            continue
        seen.add(old)
        pairs.append((old, new))
    both = seen & {new for _, new in pairs}
    for sha in sorted(both):
        problems.append(f"{source}: {sha[:12]} is both an old and a new ID")
    return pairs, problems


def load(root: Path) -> tuple[CommitMap, list[str]]:
    """Every map under `root`'s `docs/handshake`, oldest first, and their problems.

    A repository that was never rewritten has no map, and gets an empty one:
    every lookup then answers None and callers behave exactly as before.
    """
    found = CommitMap()
    problems: list[str] = []
    directory = root / MAP_DIR
    try:
        candidates = sorted(p for p in directory.glob("commit-map*") if p.is_file())
    except OSError as exc:
        return found, [f"{directory}: could not be listed ({exc})"]
    for path in candidates:
        if MAP_NAME_RE.match(path.name) is None:
            problems.append(
                f"{path.name}: a map must be named commit-map-YYYY-MM-DD.txt"
            )
            continue
        try:
            text = path.read_text(encoding="ascii")
        except (OSError, UnicodeDecodeError) as exc:
            problems.append(f"{path.name}: could not be read as ASCII ({exc})")
            continue
        pairs, said = parse_map(text, path.name)
        problems.extend(said)
        for old, new in pairs:
            if old in found.pairs:
                problems.append(
                    f"{path.name}: {old[:12]} is already mapped by an earlier file"
                )
                continue
            found._add(old, new)
        found.sources.append(path.name)
    return found, problems
