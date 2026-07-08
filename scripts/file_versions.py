#!/usr/bin/env python3
"""Show the last-updated version of every tracked file — derived from git.

Why this exists
---------------
Docs carry a visible ``*Last updated for Platterpus vX.Y.Z.*`` footer because
they're read *outside* the repo (GitHub, the in-app User Guide) where git
history isn't at hand. Source files deliberately do **not** carry such a stamp:
git already records the last-updated commit per file exactly, and a hand-typed
comment would rot the moment someone edited the file without bumping it — turning
into misinformation, which is worse than nothing.

This script gives the same "last updated" view for **every** tracked file, on
demand, computed from git — so it's always accurate and nothing has to be
embedded or maintained. For each file it reports:

* **version** — ``__version__`` (from ``src/platterpus/__init__.py``) as it stood
  at that file's most recent commit, i.e. the release the file's content was last
  revised for;
* **date** — the commit date (YYYY-MM-DD);
* **commit** — the short SHA.

Usage (run from the repo root)::

    python scripts/file_versions.py                 # aligned plain-text table
    python scripts/file_versions.py --markdown       # a Markdown table (manifest)
    python scripts/file_versions.py --path docs       # only files under docs/
    python scripts/file_versions.py --path docs --path README.md

Never raises for the expected cases: a file with no history, or a commit from
before ``__init__.py`` existed, simply shows ``?`` for the version.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass

# The single source of the version string; we read it *as it was* at each file's
# last commit, so the reported version matches that file's last content change.
_VERSION_FILE = "src/platterpus/__init__.py"


@dataclass(frozen=True)
class FileVersion:
    """One tracked file's last-updated provenance, all git-derived."""

    path: str
    version: str  # __version__ at the file's last commit, or "?"
    date: str  # commit date YYYY-MM-DD, or ""
    commit: str  # short SHA, or ""


def _git(*args: str) -> str:
    """Run a git command from the current directory; return stripped stdout.

    Returns "" on any git failure — callers treat missing data as "unknown"
    rather than crashing, so a half-initialised repo can't blow the tool up.
    """
    try:
        out = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    return out.stdout.strip()


def _tracked_files(prefixes: list[str]) -> list[str]:
    """All tracked files, optionally filtered to the given path prefixes."""
    files = _git("ls-files").splitlines()
    if prefixes:
        files = [f for f in files if any(f.startswith(p) for p in prefixes)]
    return sorted(files)


def _version_at_commit(commit: str, cache: dict[str, str]) -> str:
    """``__version__`` as it stood at ``commit`` (memoised — many files share a
    commit, so we resolve each commit's version string only once)."""
    if not commit:
        return "?"
    if commit in cache:
        return cache[commit]
    blob = _git("show", f"{commit}:{_VERSION_FILE}")
    version = "?"
    for line in blob.splitlines():
        # Match e.g.  __version__: str = "0.4.20"
        if "__version__" in line and '"' in line:
            version = line.split('"')[1]
            break
    cache[commit] = version
    return version


def collect(prefixes: list[str] | None = None) -> list[FileVersion]:
    """Build the last-updated record for every tracked file (git-derived)."""
    prefixes = prefixes or []
    version_cache: dict[str, str] = {}
    rows: list[FileVersion] = []
    for path in _tracked_files(prefixes):
        # "%H<TAB>%cs" → full SHA + committer date (short ISO). One log call per
        # file is the simplest correct way to get *that file's* last commit.
        info = _git("log", "-1", "--format=%H%x09%cs", "--", path)
        commit_full, _, date = info.partition("\t")
        short = commit_full[:9]
        rows.append(
            FileVersion(
                path=path,
                version=_version_at_commit(commit_full, version_cache),
                date=date,
                commit=short,
            )
        )
    return rows


def format_table(rows: list[FileVersion]) -> str:
    """A left-aligned fixed-width table for the terminal."""
    if not rows:
        return "(no tracked files matched)"
    path_w = max(len(r.path) for r in rows)
    ver_w = max(len(r.version) for r in rows + [FileVersion("", "version", "", "")])
    header = f"{'FILE'.ljust(path_w)}  {'VERSION'.ljust(ver_w)}  DATE        COMMIT"
    lines = [header, "-" * len(header)]
    for r in rows:
        lines.append(
            f"{r.path.ljust(path_w)}  v{r.version.ljust(ver_w - 1)}  "
            f"{r.date or '?':<10}  {r.commit}"
        )
    return "\n".join(lines)


def format_markdown(rows: list[FileVersion]) -> str:
    """A Markdown table, suitable for committing as a browsable manifest."""
    lines = [
        "| File | Last updated (version) | Date | Commit |",
        "|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| `{r.path}` | v{r.version} | {r.date or '?'} | `{r.commit}` |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Show each tracked file's last-updated version, from git."
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="emit a Markdown table (a committable manifest) instead of plain text",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        metavar="PREFIX",
        help="only include files under this path prefix (repeatable)",
    )
    args = parser.parse_args(argv)

    if not _git("rev-parse", "--is-inside-work-tree"):
        print(
            "error: not inside a git work tree (run from the repo root)",
            file=sys.stderr,
        )
        return 2

    rows = collect(args.path)
    print(format_markdown(rows) if args.markdown else format_table(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
