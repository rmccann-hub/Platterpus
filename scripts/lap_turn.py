#!/usr/bin/env python3
"""Who released the last lap, and who holds the next one: the first question.

**Why this exists (the owner, 2026-11-12):** *"the first question on both repos
should be, who released the last lap, and who is holding the next. this should
cover most situations"*. Twice in round 39 the owner had to ask it ("is lap 2 the
next lap? did fork already release lap 1?", "so who is next to release a lap?"),
and both times the answer was already in the laps' own headers: every lap names
the next one in ``HANDSHAKE-NEXT-LAP`` (``"5 (yours): …"``), and says whether it
is released in ``HANDSHAKE-READY-TO-READ``. This reads them and says so, so the
answer comes from the record, never from a session's memory.

**Where it reads.** Each side's lap as that side publishes it, never a working
tree: ours from ``origin/main`` (our ref of record, CLAUDE.md rule 12, *Laps
travel by git*), theirs from the fork's ``origin/platterpus-fork`` in a clone of
their tree when one is given (``--peer``), and from the laps we filed under
``docs/handshake/inbound/`` otherwise. ``--fetch`` refreshes both refs first,
bounded, and says when it could not; without it the answer is as of the last
fetch, and it says that too.

    python3 scripts/lap_turn.py [--peer /home/user/cyanrip] [--fetch]

It never writes, never pushes, and exits 0 unless it found no lap at all (2), so
the session-start hook can run it without ever failing a session.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
OUR_REF: Final[str] = "origin/main"
THEIR_REF: Final[str] = "origin/platterpus-fork"
#: How long a ``--fetch`` may take per repository before the answer goes ahead
#: as of the last fetch: a stalled network must not hold a session's start.
FETCH_SECONDS: Final[int] = 20

#: ``round-39-lap-04.md``: the committed lap name both sides use.
_LAP_NAME: Final[re.Pattern[str]] = re.compile(r"^round-(\d{2})-lap-(\d{2})\.md$")
#: ``HANDSHAKE-NEXT-LAP: 5 (yours): …`` — the number and whose it is, said from
#: the AUTHOR's side: ``yours`` is the reader's, ``ours`` the author's.
_NEXT: Final[re.Pattern[str]] = re.compile(
    r"^(?P<lap>\d+)\s*\((?P<whose>yours|ours|theirs|mine)\)", re.IGNORECASE
)

SIDES: Final[tuple[str, str]] = ("platterpus", "cyanrip-fork")


@dataclass(frozen=True)
class Lap:
    """One lap as its author published it."""

    round: int
    lap: int
    author: str  # HANDSHAKE-FROM
    released: bool  # HANDSHAKE-READY-TO-READ starts with "yes"
    next_lap: str  # HANDSHAKE-NEXT-LAP, verbatim
    where: str  # "<repo> <ref>", for the report


@dataclass(frozen=True)
class Turn:
    """The answer: the last released lap, and who holds the next."""

    last: Lap | None
    next_holder: str | None  # a side, or None when the lap does not say
    next_number: int | None
    next_text: str
    held: tuple[Lap, ...]  # laps written but not yet released, either side


#: Every ``HANDSHAKE-<NAME>: value`` line, at column 0: a literal the regex sweep
#: can time (`tests/test_regex_bounded_time.py`), rather than one built per name.
_HEADER: Final[re.Pattern[str]] = re.compile(
    r"^HANDSHAKE-(?P<name>[A-Z][A-Z-]{0,40}):[ \t]*(?P<value>[^\n]*)$", re.MULTILINE
)


def _header(text: str, name: str) -> str:
    """The first ``HANDSHAKE-<name>`` header's value, or "" when there is none."""
    for match in _HEADER.finditer(text):
        if match.group("name") == name:
            return match.group("value").strip()
    return ""


def parse_lap(name: str, text: str, where: str) -> Lap | None:
    """A lap from its file name and text, or None when either is not a lap's."""
    named = _LAP_NAME.match(name)
    author = _header(text, "FROM")
    if named is None or author not in SIDES:
        return None
    return Lap(
        round=int(named.group(1)),
        lap=int(named.group(2)),
        author=author,
        released=_header(text, "READY-TO-READ").lower().startswith("yes"),
        next_lap=_header(text, "NEXT-LAP"),
        where=where,
    )


def _other(side: str) -> str:
    return SIDES[1] if side == SIDES[0] else SIDES[0]


def decide(laps: Iterable[Lap]) -> Turn:
    """Pure: who released the last lap, and who holds the next one.

    The last lap is the newest RELEASED one by ``(round, lap)``; a lap written
    and held does not move the turn, because the other side cannot read it, but
    it is listed so a held lap is never forgotten. The next holder is read from
    that lap's ``NEXT-LAP``, which the author writes from its own side.
    """
    by_key: dict[tuple[int, int], Lap] = {}
    for lap in laps:
        key = (lap.round, lap.lap)
        # The same lap seen twice (ours on main and filed by them): a released
        # copy outranks a held one, so a release is never hidden by a stale copy.
        if key not in by_key or (lap.released and not by_key[key].released):
            by_key[key] = lap
    released = [lap for lap in by_key.values() if lap.released]
    last = max(released, key=lambda x: (x.round, x.lap)) if released else None
    # Only a held lap NEWER than the last released one matters: an older one is
    # history (laps before round 19 carry no READY-TO-READ header at all, so
    # they read as held forever and would bury the answer).
    floor = (last.round, last.lap) if last is not None else (-1, -1)
    held = tuple(
        sorted(
            (x for x in by_key.values() if not x.released and (x.round, x.lap) > floor),
            key=lambda x: (x.round, x.lap),
        )
    )
    if last is None:
        return Turn(None, None, None, "", held)
    match = _NEXT.match(last.next_lap)
    if match is None:
        return Turn(last, None, None, last.next_lap, held)
    whose = match.group("whose").lower()
    holder = _other(last.author) if whose == "yours" else last.author
    return Turn(last, holder, int(match.group("lap")), last.next_lap, held)


#: Where each side publishes its laps, for the turn line: the repository and
#: the branch the other side reads (CLAUDE.md rule 12, *Laps travel by git*).
REPOS: Final[dict[str, str]] = {
    "platterpus": "rmccann-hub/Platterpus main",
    "cyanrip-fork": "rmccann-hub/cyanrip platterpus-fork",
}


def turn_line(turn: Turn, me: str = "platterpus") -> str:
    """The HANDOFF block's first line: whose turn it is, said from ``me``'s side.

    **Why this exists (the owner, 2026-11-13):** *"round x lap y goes to repo z,
    expecting round a lap b back. 'its my turn to send' or its 'my turn to wait'
    should be clear on first line of handshake text"*. Computed from the laps'
    own headers, never typed from memory, so the line cannot say a turn the
    record does not. A lap of ours written and held is still ours to send: the
    other side cannot read it until it is released.
    """
    them = _other(me)
    held_mine = [lap for lap in turn.held if lap.author == me]
    if held_mine:
        lap = held_mine[-1]
        return (
            f"MY TURN TO SEND: round {lap.round} lap {lap.lap} is written and held; "
            f"it goes to {REPOS[them]} once released, expecting round {lap.round} "
            f"lap {lap.lap + 1} back."
        )
    last = turn.last
    if last is None or turn.next_holder is None or turn.next_number is None:
        where = (
            f"round {last.round} lap {last.lap} by {last.author}"
            if last is not None
            else "no released lap"
        )
        return f"NEITHER SIDE'S TURN IS NAMED: {where}; its NEXT-LAP says {turn.next_text!r}."
    if turn.next_holder == me:
        return (
            f"MY TURN TO SEND: round {last.round} lap {turn.next_number} goes to "
            f"{REPOS[them]}, expecting round {last.round} lap {turn.next_number + 1} back."
        )
    return (
        f"MY TURN TO WAIT: round {last.round} lap {last.lap} went to {REPOS[them]}, "
        f"expecting round {last.round} lap {turn.next_number} back."
        if last.author == me
        else f"MY TURN TO WAIT: expecting round {last.round} lap {turn.next_number} "
        f"from {REPOS[them]}."
    )


def render(turn: Turn, fetched: str) -> str:
    """The turn line, the answer in two lines, then anything held."""
    if turn.last is None:
        return "No released lap found on either side's published ref. " + fetched
    last = turn.last
    lines = [
        turn_line(turn),
        f"Last released: round {last.round} lap {last.lap}, by {last.author}"
        f" ({last.where}).",
    ]
    if turn.next_holder is None:
        lines.append(f"Next: its NEXT-LAP says {turn.next_text!r}; read it.")
    else:
        lines.append(
            f"Next: round {last.round} lap {turn.next_number}, held by "
            f"{turn.next_holder}. NEXT-LAP: {turn.next_text}"
        )
    for lap in turn.held:
        lines.append(
            f"Written and held, not released: round {lap.round} lap {lap.lap} "
            f"by {lap.author} ({lap.where})."
        )
    lines.append(fetched)
    return "\n".join(lines)


def _git(repo: Path, *args: str, timeout: int | None = None) -> str | None:
    try:
        done = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def laps_at(repo: Path, ref: str, folders: Sequence[str], label: str) -> list[Lap]:
    """Every lap under ``folders`` at ``ref`` in ``repo``, as published there."""
    found: list[Lap] = []
    for folder in folders:
        listing = _git(repo, "ls-tree", "--name-only", f"{ref}:{folder}")
        for name in (listing or "").splitlines():
            if not _LAP_NAME.match(name):
                continue
            text = _git(repo, "show", f"{ref}:{folder}/{name}")
            lap = parse_lap(name, text or "", f"{label} {ref}")
            if lap is not None:
                found.append(lap)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--peer", type=Path, help="a clone of the fork's tree")
    parser.add_argument(
        "--fetch", action="store_true", help="fetch both published refs first"
    )
    args = parser.parse_args(argv)
    notes: list[str] = []
    if args.fetch:
        if (
            _git(REPO_ROOT, "fetch", "-q", "origin", "main", timeout=FETCH_SECONDS)
            is None
        ):
            notes.append("could not fetch our main")
        if (
            args.peer
            and _git(
                args.peer,
                "fetch",
                "-q",
                "origin",
                "platterpus-fork",
                timeout=FETCH_SECONDS,
            )
            is None
        ):
            notes.append("could not fetch the fork's platterpus-fork")
    fetched = (
        "As of a fetch just now."
        if args.fetch and not notes
        else "As of the last fetch"
        + (f" ({'; '.join(notes)})" if notes else "")
        + ": fetch both before acting on it."
    )
    laps = laps_at(
        REPO_ROOT,
        OUR_REF,
        ("docs/handshake/outbound", "docs/handshake/inbound"),
        "Platterpus",
    )
    if args.peer:
        laps += laps_at(args.peer, THEIR_REF, ("docs/handshake",), "cyanrip")
    turn = decide(laps)
    print(render(turn, fetched))
    return 0 if turn.last is not None else 2


if __name__ == "__main__":
    sys.exit(main())
