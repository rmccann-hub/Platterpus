"""The command line: `python3 scripts/lap_language.py check|turn`."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from .header import LANGUAGE_FIELD, LANGUAGE_VERSION
from .model import Lap, Problem
from .parse import parse_lap
from .rounds import check_round, ledger, turn

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
HANDSHAKE_DIR: Final[Path] = REPO_ROOT / "docs" / "handshake"

# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def round_files(round_number: int, root: Path = HANDSHAKE_DIR) -> list[Path]:
    name = f"round-{round_number:02d}-lap-*.md"
    return sorted((root / "inbound").glob(name)) + sorted(
        (root / "outbound").glob(name)
    )


def load(path: Path) -> Lap:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return Lap(path.name, (), (), (Problem("L0", 1, f"unreadable: {exc}"),), False)
    return parse_lap(text, name=f"{path.parent.name}/{path.name}")


def _cmd_check(paths: Sequence[Path]) -> int:
    failed = 0
    for path in paths:
        lap = load(path)
        if not lap.uses_language:
            print(
                f"{path}: not a language-{LANGUAGE_VERSION} lap ({LANGUAGE_FIELD} absent); not checked"
            )
            continue
        round_laps = [
            load(p)
            for p in round_files(lap.round or 0)
            if p.resolve() != path.resolve()
        ]
        found = list(lap.problems) + [
            p for owner, p in check_round([*round_laps, lap]) if owner is lap
        ]
        for problem in found:
            print(problem.render(str(path)))
        print(f"{path}: {len(lap.statements)} statement(s), {len(found)} problem(s)")
        failed += bool(found)
    return 1 if failed else 0


def _newest_round(root: Path = HANDSHAKE_DIR) -> int:
    numbers = [
        int(p.name.split("-")[1])
        for side in ("inbound", "outbound")
        for p in (root / side).glob("round-*-lap-*.md")
    ]
    return max(numbers, default=0)


def _cmd_turn(round_number: int | None) -> int:
    number = round_number or _newest_round()
    laps = [load(p) for p in round_files(number)]
    t = turn(laps)
    print(f"round {number}: {t.detail}")
    print(f"  read from {t.source}")
    if t.party is not None:
        owed = ledger(laps)
        for ref, s in owed.open_questions:
            if s.value("to") == t.party:
                print(f"  owed by {t.party}: an answer to {ref} ({s.qualifier})")
        for ref, _s, state, _status in owed.terms:
            if state not in {"met", "waived"}:
                print(f"  close condition {ref}: {state}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check laps written in the lap language."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser(
        "check", help="check lap files, alone and against their round"
    )
    check.add_argument("paths", nargs="+", type=Path)
    whose = sub.add_parser(
        "turn", help="say whose move it is in a round, from the files"
    )
    whose.add_argument("round", nargs="?", type=int)
    args = parser.parse_args(argv)
    if args.command == "check":
        return _cmd_check(args.paths)
    return _cmd_turn(args.round)


if __name__ == "__main__":
    sys.exit(main())
