"""The parsed form of a lap: its header, its statements, and what is wrong with it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

#: Rounds before this were hand-carried, so delivery was the release (the same
#: grandfather `scripts/handshake.py` applies to `HANDSHAKE-READY-TO-READ`).
READY_TO_READ_FROM_ROUND: Final[int] = 19

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Problem:
    """One broken rule, named by its id in the spec (`L…` for a lap, `R…` for a round)."""

    rule: str
    line: int
    message: str

    def render(self, where: str) -> str:
        return f"{where}:{self.line}: [{self.rule}] {self.message}"


@dataclass(frozen=True)
class Attribute:
    key: str
    value: str
    line: int


@dataclass(frozen=True)
class Statement:
    """One statement: `#### <sid> <kind> <qualifier>`, its text, its attributes."""

    sid: str
    kind: str
    qualifier: str
    text: str
    attributes: tuple[Attribute, ...]
    line: int

    def values(self, key: str) -> list[str]:
        """Every value given for `key`, in order (repeatable keys give several)."""
        return [a.value for a in self.attributes if a.key == key]

    def value(self, key: str) -> str | None:
        found = self.values(key)
        return found[0] if found else None


@dataclass(frozen=True)
class Lap:
    """A parsed lap. `problems` holds everything wrong with it on its own."""

    name: str
    header: tuple[tuple[str, str, int], ...]
    statements: tuple[Statement, ...]
    problems: tuple[Problem, ...]
    uses_language: bool

    def field(self, name: str) -> str | None:
        for key, value, _line in self.header:
            if key == name:
                return value
        return None

    def int_field(self, name: str) -> int | None:
        value = self.field(name)
        return int(value) if value is not None and value.isdigit() else None

    def statement(self, sid: str) -> Statement | None:
        for s in self.statements:
            if s.sid == sid:
                return s
        return None

    @property
    def round(self) -> int | None:
        return self.int_field("HANDSHAKE-ROUND")

    @property
    def lap(self) -> int | None:
        return self.int_field("HANDSHAKE-LAP")

    @property
    def author(self) -> str | None:
        return self.field("HANDSHAKE-FROM")

    @property
    def released(self) -> bool:
        """Released for reading (§5c), or from a round that predates the field."""
        if self.round is not None and self.round < READY_TO_READ_FROM_ROUND:
            return True
        value = self.field("HANDSHAKE-READY-TO-READ") or ""
        return value.split(" ", 1)[0] == "yes"
