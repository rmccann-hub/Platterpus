"""The command line: `python3 scripts/lap_language.py check <lap>`.

Exit codes follow the fork's checker, because they are the part of the output
another program reads: **0** the lap is well formed (warnings may be printed),
**1** at least one refusal, **2** the file could not be checked (unreadable, not
an LSL lap, or an LSL version this checker does not implement). *Refused* and
*could not check* are different claims, so they are different codes.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from .amend import check_amendments
from .check import check_lap
from .context import Context
from .grammar import read_lap
from .model import Lap, Side
from .record import Record
from .refs import Trees, default_at
from .tables import AMENDMENTS, tables_for

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]

#: Where each side publishes from, tried in order. `main` is ours (CLAUDE.md
#: rule #12); `platterpus-fork` is the fork's branch of record.
PUBLISHING_REFS: Final[dict[Side, tuple[str, ...]]] = {
    "platterpus": ("HEAD",),
    "cyanrip": ("platterpus-fork", "origin/platterpus-fork", "HEAD"),
}


def parse_amendments(value: str | None) -> frozenset[str]:
    """`all`, `none`, or a comma list such as `A1,A3`. Unknown ids are an error."""
    if value is None or value == "none":
        return frozenset()
    if value == "all":
        return frozenset(AMENDMENTS)
    chosen = frozenset(v.strip() for v in value.split(",") if v.strip())
    unknown = chosen - set(AMENDMENTS)
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown amendment(s) {sorted(unknown)}; known: {', '.join(AMENDMENTS)}"
        )
    return chosen


def check_path(
    path: Path,
    *,
    root: Path = REPO_ROOT,
    peer: Path | None = None,
    amendments: frozenset[str] = frozenset(),
    at: str | None = None,
) -> Lap:
    """Parse and check one lap file. The problems come back on the lap."""
    lap = read_lap(path)
    if not lap.lsl:
        if not lap.problems:
            lap.add(0, "CANNOT", "LSL.version", "not an LSL lap: no 'LSL: 1' line")
        return lap
    checking = None
    if lap.author is not None and lap.round is not None and lap.lap is not None:
        checking = (lap.author, lap.round, lap.lap)
    roots: dict[Side, Path | None] = {"platterpus": root, "cyanrip": peer}
    refs: dict[Side, str] = {
        side: default_at(roots[side], candidates)
        for side, candidates in PUBLISHING_REFS.items()
    }
    if at is not None and lap.author is not None:
        refs[lap.author] = at
    ctx = Context(
        lap, Record(root, checking), Trees(roots, refs), tables_for(amendments)
    )
    check_lap(ctx)
    if amendments:
        check_amendments(ctx)
    return lap


def render(lap: Lap) -> tuple[str, int]:
    """The report a person reads, and the exit code."""
    lines: list[str] = []
    cannot = [p for p in lap.problems if p.severity == "CANNOT"]
    if cannot:
        for p in cannot:
            lines.append(f"CANNOT CHECK  {lap.path.name}:{p.line}  {p.message}")
        return "\n".join(lines), 2
    for p in sorted(lap.problems, key=lambda p: (p.severity != "REFUSED", p.line)):
        lines.append(
            f"{p.severity:<8} {lap.path.name}:{p.line}  [{p.rule}] {p.message}"
        )
    census: dict[str, int] = {}
    for stmt in lap.statements:
        census[stmt.kind] = census.get(stmt.kind, 0) + 1
    listed = ", ".join(f"{n} {kind}" for kind, n in sorted(census.items()))
    lines.append(f"\n{len(lap.statements)} statement(s): {listed or 'none'}")
    refused = lap.refused()
    warnings = [p for p in lap.problems if p.severity == "WARN"]
    if refused:
        lines.append(f"{len(refused)} refusal(s): not a well-formed LSL lap")
        return "\n".join(lines), 1
    lines.append(f"well formed, {len(warnings)} warning(s)")
    return "\n".join(lines), 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a lap written in LSL 1.")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="check one lap")
    check.add_argument("lap", type=Path)
    check.add_argument(
        "--peer",
        type=Path,
        help="a clone of the fork's tree, to resolve references into it",
    )
    check.add_argument(
        "--amend",
        type=parse_amendments,
        default=frozenset(),
        help="amendments to apply: all, none, or e.g. A1,A3",
    )
    check.add_argument(
        "--at", help="the author's commits must be reachable from this ref"
    )
    check.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    lap = check_path(
        args.lap, root=args.root, peer=args.peer, amendments=args.amend, at=args.at
    )
    text, code = render(lap)
    print(text)
    return code
