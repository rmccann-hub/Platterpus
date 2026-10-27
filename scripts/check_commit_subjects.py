#!/usr/bin/env python3
"""Check that every new commit's subject follows this repository's grammar.

**Why this exists (the 2026-10-27 external review, item 2.9).** `CLAUDE.md`
→ *Commit & PR hygiene* records the grammar, and records it as a deliberate
divergence from the generic SOP: a lowercase conventional subject,
`type(scope): summary` or `type: summary`. Nothing checked it, so it held only
as long as every author remembered. The laps, `TASKS.md` and the session log
cite commits by subject as well as by SHA, and a grammar that drifts makes them
harder to read and to grep.

**What it accepts**, and why each:

* ``type(scope): summary`` / ``type: summary``, with ``type`` one of ``feat fix
  docs test refactor style chore release`` (the list `CLAUDE.md` names) and
  ``ci build``. Those two are not in `CLAUDE.md`'s list, but they are standard
  Conventional Commits types and the history uses them on purpose (5 ``ci`` and
  1 ``build`` in the 400 subjects before 27755380, and every Dependabot bump is
  ``build(deps): …``), so refusing them would fail real practice rather than
  enforce a rule. An optional ``!`` marks a breaking change, as the spec allows.
* The summary starts with something other than a capitalised plain word
  (``Add``, ``Fix``): `CLAUDE.md` says lowercase after the colon. A first word
  that is an acronym or identifier (``README``, ``FORK_PIN``, ``PySide6``) is
  allowed, because lower-casing it would make it wrong. No trailing period.
* On a MERGE commit (two or more parents), any subject that starts ``Merge ``:
  GitHub's ``Merge pull request #N from …``, git's ``Merge branch '…' into …``,
  and the prose an author gives ``git merge -m`` (``Merge the taken-over EAC
  audit branch …``; several in the 400). Every pull request lands with a merge
  commit, so these are on `main` by design. A merge commit may carry a
  conventional subject instead. On an ORDINARY commit a ``Merge …`` subject is
  refused: none appears in the 400, and one would be a squash title or a typo.
* git's ``Revert "…"`` subject, and Dependabot's unprefixed ``Bump X from A to
  B`` form, which no author writes by hand.

It is NOT a required status check. Making it one is the owner's call, in the
default-branch ruleset (`PLANNING.md` KDD-43); until then a red run here is a
signal, not a block.

Exit status: 0 when every subject passes, 1 when any fails, and 1 when the
commits cannot be listed or the range holds none: a check that read nothing has
checked nothing.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence
from typing import Final

#: The types `CLAUDE.md` lists, plus `ci` and `build` (see the module docstring).
TYPES: Final[tuple[str, ...]] = (
    "feat",
    "fix",
    "docs",
    "test",
    "refactor",
    "style",
    "chore",
    "release",
    "ci",
    "build",
)

#: `type(scope)!: summary`. Scopes in use are lowercase words joined by `-`, and
#: one history entry joins two with a comma (`docs,ui`).
_CONVENTIONAL: Final[re.Pattern[str]] = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[a-z0-9][a-z0-9._/,-]*)\))?!?: (?P<summary>\S.*)$"
)

#: A capitalised plain word: the sentence-case first word the rule forbids.
_SENTENCE_CASE: Final[re.Pattern[str]] = re.compile(r"^[A-Z][a-z]+\b(?![-_./0-9A-Z])")

#: A merge commit's subject: GitHub's, git's, or an author's `git merge -m`.
_MERGE: Final[re.Pattern[str]] = re.compile(r"^Merge \S")

#: Subjects git or Dependabot write on an ordinary commit.
_MACHINE: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r'^Revert ".+"$'),
    # Dependabot without a commit-message prefix.
    re.compile(r"^Bump \S+ from \S+ to \S+(?: in /\S*)?$"),
    re.compile(
        r"^Bump the \S+ group(?: across \d+ director(?:y|ies))? with \d+ updates?$"
    ),
)


def check_subject(subject: str, *, is_merge: bool = False) -> str | None:
    """None when `subject` follows the grammar; otherwise the reason it does not.

    `is_merge` says the commit has two or more parents, which admits the
    ``Merge …`` subjects. Pure and total: never raises, whatever the input.
    """
    if is_merge and _MERGE.match(subject):
        return None
    if any(pattern.match(subject) for pattern in _MACHINE):
        return None
    match = _CONVENTIONAL.match(subject)
    if match is None:
        return (
            "not `type(scope): summary` or `type: summary` (lowercase type, a "
            "colon and one space)"
        )
    kind = match.group("type")
    if kind not in TYPES:
        return f"type `{kind}` is not one of: {' '.join(TYPES)}"
    summary = match.group("summary")
    if _SENTENCE_CASE.match(summary):
        return "the summary starts with a capitalised word; write it lowercase"
    if summary.endswith("."):
        return "the summary ends with a period"
    return None


def _subjects_in_range(revision_range: str) -> list[tuple[str, str, bool]] | None:
    """(sha, subject, is_merge) for every commit in the range; None on error."""
    try:
        result = subprocess.run(  # fixed argv, no shell
            ["git", "log", "--format=%H %P%x00%s%x00", revision_range],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"::error::could not run git log: {exc}")
        return None
    if result.returncode != 0:
        print(
            f"::error::git log {revision_range} exited {result.returncode}: "
            f"{result.stderr.strip()}"
        )
        return None
    fields = result.stdout.split("\x00")
    commits: list[tuple[str, str, bool]] = []
    for index in range(0, len(fields) - 1, 2):
        # "<sha> <parent> <parent>…": two or more parents make a merge commit.
        hashes = fields[index].split()
        if hashes:
            commits.append((hashes[0], fields[index + 1], len(hashes) > 2))
    return commits


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--range", help="a git revision range, e.g. BASE..HEAD")
    source.add_argument(
        "--subject", action="append", help="check this subject (repeatable)"
    )
    args = parser.parse_args(argv)

    if args.range is not None:
        found = _subjects_in_range(args.range)
        if found is None:
            print("Refusing: the commits could not be listed, so none was checked.")
            return 1
        commits = found
    else:
        commits = [("(given)", subject, False) for subject in args.subject]
    if not commits:
        print(
            "::error::the range holds no commits, so this check read nothing. "
            "Refusing rather than passing."
        )
        return 1

    failures = 0
    for sha, subject, is_merge in commits:
        reason = check_subject(subject, is_merge=is_merge)
        if reason is not None:
            failures += 1
            print(f"::error::{sha[:12]} {subject!r}: {reason}")
    print(f"commit subjects examined: {len(commits)}; failing: {failures}")
    if failures:
        print(
            "The grammar is CLAUDE.md → Commit & PR hygiene: lowercase "
            "`type(scope): summary`, types " + " ".join(TYPES) + "."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
