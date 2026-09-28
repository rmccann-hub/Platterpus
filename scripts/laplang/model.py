"""What a parsed LSL lap is made of, and the problems a check can find in it.

These are plain data holders with no behaviour beyond small lookups, so every
other module can share them without importing each other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Literal

#: The two parties, spelled the way LSL references spell them
#: (`cyanrip@<sha>:…`, `platterpus:R27.L5.S4`).
Side = Literal["cyanrip", "platterpus"]
SIDES: Final[tuple[Side, Side]] = ("cyanrip", "platterpus")

#: `HANDSHAKE-FROM` values, mapped to the side they name. The fork writes
#: `cyanrip-fork`, so both spellings are the same party.
FROM_SIDE: Final[dict[str, Side]] = {
    "cyanrip-fork": "cyanrip",
    "cyanrip": "cyanrip",
    "platterpus": "platterpus",
}

#: How bad a problem is. `REFUSED` means the lap is not well formed. `WARN` is
#: printed and does not fail the lap. `CANNOT` means the file could not be checked
#: at all, which is a different claim from "refused" (exit 2, not 1).
Severity = Literal["REFUSED", "WARN", "CANNOT"]


def other(side: Side) -> Side:
    """The party that is not `side`."""
    return "platterpus" if side == "cyanrip" else "cyanrip"


@dataclass
class Field:
    """One `  name: value` line of a statement, with its continuation lines joined."""

    name: str
    value: str
    line: int


@dataclass
class Statement:
    """One `S<n> KIND[ grade]: sentence` head and the fields under it."""

    n: int
    kind: str
    grade: str | None
    sentence: str
    line: int
    fields: list[Field] = field(default_factory=list)

    def values(self, name: str) -> list[Field]:
        """Every field called `name`, in order. A field may repeat."""
        return [f for f in self.fields if f.name == name]

    def has(self, name: str) -> bool:
        return any(f.name == name for f in self.fields)

    @property
    def tag(self) -> str:
        """`S7 CORRECT` or `S2 FACT measured`: how a message names the statement."""
        return f"S{self.n} {self.kind}" + (f" {self.grade}" if self.grade else "")


@dataclass(frozen=True)
class Problem:
    """One thing a check found.

    `rule` names what was broken: `LSL.1`–`LSL.6` for the six refusals the spec
    numbers, `LSL.<word>` for rules the spec states elsewhere, `A1`–`A8` for the
    amendments LSL 2 adopted, and `B1`–`B3` for what LSL 3 adds. A disagreement
    between two checkers can then name the rule it is about.
    """

    line: int
    severity: Severity
    rule: str
    message: str


@dataclass
class RunCoverage:
    """What B1 covered in one lap: its `run:` results, and what became of each.

    Printed, because a B1 that re-ran nothing passes by finding nothing, and a
    reader can see that only if the counts are on the page (the proposal: "The
    checker prints what B1 covered"). `matched + mismatched + not_rerun == total`
    whenever `rerun` is True; without `--rerun` nothing is executed and all
    three stay 0.
    """

    #: Every `run:` in an `evidence:` field of the lap.
    total: int = 0
    #: True when `--rerun` was given, so the counts below mean something.
    rerun: bool = False
    matched: int = 0
    mismatched: int = 0
    #: Reported `UNCHECKED run:` with a reason: not a command B1 re-runs, a
    #: result that quotes nothing, or a re-run that could not be done.
    not_rerun: int = 0
    #: Scratch worktrees that `git worktree remove` would not remove, by path,
    #: so a person can remove them; never removed by force of `rm`.
    leftovers: list[str] = field(default_factory=list)


@dataclass
class Lap:
    """A lap file, parsed. `lsl` is False for a prose lap or an unreadable one."""

    path: Path
    text: str
    headers: dict[str, list[str]] = field(default_factory=dict)
    statements: list[Statement] = field(default_factory=list)
    problems: list[Problem] = field(default_factory=list)
    lsl: bool = False
    #: The N of the lap's `LSL: N` line; 0 when it has none.
    lsl_version: int = 0
    #: How many things a `GO` waited on, by the amendment that counted them:
    #: `A1` close conditions, `A7` the other side's blocking questions. Printed,
    #: because a GO checked against nothing passes by finding nothing, and a
    #: reader can see that only if the count is on the page (the fork's round 28
    #: lap 3 S19-S21, which holds for this checker too).
    go_checked_against: dict[str, int] = field(default_factory=dict)
    #: What B1 covered; None unless B1 is on (an `LSL: 3` lap).
    runs: RunCoverage | None = None

    def add(self, line: int, severity: Severity, rule: str, message: str) -> None:
        self.problems.append(Problem(line, severity, rule, message))

    def header(self, name: str) -> str | None:
        """The first value of `HANDSHAKE-<name>`, or None when it is absent."""
        values = self.headers.get(name)
        return values[0].strip() if values else None

    @property
    def author(self) -> Side | None:
        """Who wrote the lap, from `HANDSHAKE-FROM`. LSL's "us" means this side."""
        value = self.header("FROM")
        return FROM_SIDE.get(value) if value is not None else None

    @property
    def round(self) -> int | None:
        return _as_int(self.header("ROUND"))

    @property
    def lap(self) -> int | None:
        return _as_int(self.header("LAP"))

    @property
    def verdict(self) -> str | None:
        """The first word of `HANDSHAKE-VERDICT`: `GO`, `HOLD`, `OPEN`, …"""
        value = self.header("VERDICT")
        return value.split()[0] if value and value.split() else None

    def statement(self, n: int) -> Statement | None:
        for stmt in self.statements:
            if stmt.n == n:
                return stmt
        return None

    def refused(self) -> list[Problem]:
        return [p for p in self.problems if p.severity == "REFUSED"]


def _as_int(value: str | None) -> int | None:
    if value is None or not value.isdigit():
        return None
    return int(value)
