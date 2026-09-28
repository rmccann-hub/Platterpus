"""The command line: `python3 scripts/lap_language.py check <lap>`.

Exit codes follow the fork's checker, because they are the part of the output
another program reads: **0** the lap is well formed (warnings may be printed),
**1** at least one refusal, **2** the file could not be checked (unreadable, not
an LSL lap, or an LSL version this checker does not implement). *Refused* and
*could not check* are different claims, so they are different codes.

`--rerun` is LSL 3's B1: a `run:` whose command can depend on nothing but the
commit it names is re-run in a scratch worktree of the author's clone, and a
quoted result it did not print is a refusal. It executes the author's committed
code, so it is off unless asked for, and the report always says how many `run:`
results there were and what became of each (`render_runs`).
"""

from __future__ import annotations

import argparse
import shlex
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from .amend import check_amendments
from .check import check_lap
from .context import Context
from .grammar import read_lap
from .model import Lap, RunCoverage, Side
from .record import Record
from .refs import Trees, default_at
from .scratch import REMOVE_WORKTREE
from .tables import AMENDMENTS, LSL_VERSIONS, tables_for

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]

#: Each side's ref of record, tried in order. `main` is ours (CLAUDE.md rule #12:
#: "`main` is the ref of record"); `platterpus-fork` is the fork's. A commit on
#: another branch only is reported `offrecord`, not refused (`refs.Trees`).
PUBLISHING_REFS: Final[dict[Side, tuple[str, ...]]] = {
    "platterpus": ("origin/main", "main", "HEAD"),
    "cyanrip": ("origin/platterpus-fork", "platterpus-fork", "HEAD"),
}


#: What each amendment's count in `Lap.go_checked_against` counts, for `render`.
_WAITED_ON: Final[dict[str, str]] = {
    "A1": "close condition(s) written as TERM set in this round's held laps",
    "A7": "blocking question(s) the other side asked in this round's held laps",
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
    rerun: bool = False,
) -> Lap:
    """Parse and check one lap file. The problems come back on the lap.

    `rerun` is `--rerun`: in an `LSL: 3` lap, B1 re-runs the `run:` commands it
    may, which EXECUTES the author's committed code. Off unless asked for.
    """
    lap = read_lap(path)
    if not lap.lsl:
        if not lap.problems:
            lap.add(0, "CANNOT", "LSL.version", "not an LSL lap: no 'LSL: N' line")
        return lap
    # `LSL: 2` means LSL 1 with A1-A8 on, and `LSL: 3` A1-A8 and B1-B3, whatever
    # `--amend` asked for; `--amend` can add amendments to a lap, never take away
    # what its version declares.
    amendments = amendments | LSL_VERSIONS[lap.lsl_version]
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
        lap,
        Record(root, checking),
        Trees(roots, refs),
        tables_for(amendments),
        rerun=rerun,
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
    for amendment, count in sorted(lap.go_checked_against.items()):
        waited = _WAITED_ON[amendment]
        lines.append(
            f"{amendment}: this GO was checked against {count} {waited}"
            + ("; none is, so it had nothing to wait for" if count == 0 else "")
        )
    if lap.runs is not None:
        lines.extend(render_runs(lap.runs))
    refused = lap.refused()
    warnings = [p for p in lap.problems if p.severity == "WARN"]
    if refused:
        lines.append(f"{len(refused)} refusal(s): not a well-formed LSL lap")
        return "\n".join(lines), 1
    lines.append(f"well formed, {len(warnings)} warning(s)")
    return "\n".join(lines), 0


def render_runs(runs: RunCoverage) -> list[str]:
    """What B1 covered, in the proposal's four numbers: the `run:` results, how
    many were re-run and matched, how many were not matched, and how many could
    not be re-run. Without `--rerun` it says that nothing was executed, so a B1
    that looked at nothing cannot read as one that passed."""
    lines: list[str] = []
    if runs.total == 0:
        lines.append("B1: 0 run: result(s) in this lap, so there was nothing to re-run")
    elif not runs.rerun:
        lines.append(
            f"B1: {runs.total} run: result(s); none re-run, because --rerun was not "
            "given, so nothing was executed"
        )
    else:
        # A match whose command failed is still a match by B1's text, and is
        # never folded silently into one: the count says so on this line.
        failed = (
            f" ({runs.matched_nonzero} of them exited non-zero, which B1 does not "
            "compare: each an UNCHECKED exit: above)"
            if runs.matched_nonzero
            else ""
        )
        lines.append(
            f"B1: {runs.total} run: result(s): {runs.matched} re-run and matched"
            f"{failed}, {runs.mismatched} re-run and not matched, {runs.not_rerun} "
            "could not be re-run (each an UNCHECKED run: above, with its reason)"
        )
    for left in runs.leftovers:
        if left.checkout:
            # The command `Scratch.close` itself tried, so the advice is one git
            # takes: a single --force is refused for a worktree still locked
            # "initializing" by a `worktree add` that timed out (review finding
            # Q8), which is how a checkout is most likely to be left.
            # Quoted as a shell would need it, should TMPDIR hold a space.
            remove = shlex.join(("git", *REMOVE_WORKTREE, left.path))
            lines.append(
                f"B1: could not remove the scratch checkout {left.path}; remove it "
                f"with `{remove}` in the author's clone"
            )
        else:
            lines.append(
                f"B1: could not remove the scratch directory {left.path}, which is "
                "not a checkout; once any checkout named above is removed, remove "
                "what is left in it by hand"
            )
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check a lap written in LSL 1, LSL 2 or LSL 3."
    )
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
    check.add_argument(
        "--rerun",
        action="store_true",
        help="LSL 3's B1: re-run each run: whose command can depend on nothing but "
        "its commit, in a scratch worktree of the author's clone, and refuse one "
        "whose quoted result is not in the output. This EXECUTES the author's "
        "committed code, the fork's when checking their lap",
    )
    check.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    lap = check_path(
        args.lap,
        root=args.root,
        peer=args.peer,
        amendments=args.amend,
        at=args.at,
        rerun=args.rerun,
    )
    text, code = render(lap)
    print(text)
    if args.rerun and lap.lsl and lap.runs is None:
        # Said, not silent: a --rerun that re-ran nothing must not read as a pass.
        print(
            f"--rerun: this lap declares LSL {lap.lsl_version}, and B1 is LSL 3's, "
            "so nothing was re-run"
        )
    return code
