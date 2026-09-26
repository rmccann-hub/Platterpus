"""One lap under check, and resolving the references it makes.

Both the LSL 1 checks (`check`) and the amendments (`amend`, `round_rules`) ask
the same questions of a reference: does this statement exist, in a lap we hold,
and does this artifact resolve in its tree. This module answers them once, so
the two sets of checks cannot resolve one reference two ways.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .model import Lap, Side, Statement
from .record import Record
from .refs import (
    Resolution,
    StatementRef,
    Trees,
    parse_artifact,
    parse_statement,
)
from .tables import Tables


@dataclass(frozen=True)
class Found:
    """A statement a reference resolved to, and the lap that holds it."""

    lap: Lap
    statement: Statement


class Context:
    """One lap under check, with what its references resolve against."""

    def __init__(self, lap: Lap, record: Record, trees: Trees, tables: Tables) -> None:
        self.lap = lap
        self.record = record
        self.trees = trees
        self.tables = tables

    @property
    def me(self) -> tuple[Side | None, int | None, int | None]:
        return (self.lap.author, self.lap.round, self.lap.lap)

    def refuse(self, line: int, rule: str, message: str) -> None:
        self.lap.add(line, "REFUSED", rule, message)

    def warn(self, line: int, rule: str, message: str) -> None:
        self.lap.add(line, "WARN", rule, message)

    def report(self, line: int, rule: str, resolution: Resolution) -> None:
        if resolution.outcome == "refused":
            self.refuse(line, rule, resolution.message)
        elif resolution.outcome == "unchecked":
            self.warn(line, "LSL.unchecked", resolution.message)
        elif resolution.outcome == "offrecord":
            self.warn(line, "LSL.offrecord", resolution.message)

    def statement(self, token: str, line: int, rule: str) -> Found | None | bool:
        """Resolve a statement or section reference.

        Returns the statement it names, None when it names a section of a prose
        lap (which has no statements), or False when it does not resolve. Every
        failure is reported under `rule`.
        """
        ref = parse_statement(token)
        if ref is None:
            self.refuse(line, rule, f"{token!r} is not a statement reference")
            return False
        if ref.side is None or (ref.side, ref.round, ref.lap) == self.me:
            return self._local(ref, token, line, rule)
        assert (
            ref.round is not None and ref.lap is not None
        )  # the regex binds all three
        held = self.record.lap(ref.side, ref.round, ref.lap)
        if held is None:
            self.refuse(
                line,
                rule,
                f"{token}: we do not hold {ref.side}'s round {ref.round} lap {ref.lap}; "
                "a cited document must be one we hold",
            )
            return False
        if ref.is_section:
            if not _has_section(held.text, ref.target[1:]):
                self.warn(
                    line, rule, f"{token}: no heading for {ref.target} in that lap"
                )
            return None
        if not held.lsl:
            self.refuse(
                line,
                rule,
                f"{token}: that is a prose lap with no statement numbers; cite a section",
            )
            return False
        number = ref.number
        stmt = held.statement(number) if number is not None else None
        if stmt is None:
            self.refuse(line, rule, f"{token}: that lap has no statement {ref.target}")
            return False
        return Found(held, stmt)

    def _local(
        self, ref: StatementRef, token: str, line: int, rule: str
    ) -> Found | bool:
        if ref.is_section:
            self.refuse(
                line, rule, f"{token}: this lap is LSL; cite a statement, not a section"
            )
            return False
        number = ref.number
        stmt = self.lap.statement(number) if number is not None else None
        if stmt is None:
            self.refuse(line, rule, f"{token}: no such statement in this lap")
            return False
        return Found(self.lap, stmt)

    def artifact(self, token: str, line: int, rule: str) -> bool:
        """Resolve an artifact reference; False when it does not parse."""
        ref = parse_artifact(token)
        if ref is None:
            return False
        self.report(line, rule, self.trees.artifact(ref, self.lap.author))
        return True

    def lookup(self, token: str) -> Found | None:
        """Resolve a statement reference without reporting anything.

        For checks that run after LSL 1's, which has already reported a reference
        that does not resolve. None for a section, a prose lap or a miss.
        """
        ref = parse_statement(token)
        if ref is None or ref.number is None:
            return None
        if ref.side is None or (ref.side, ref.round, ref.lap) == self.me:
            stmt = self.lap.statement(ref.number)
            return Found(self.lap, stmt) if stmt is not None else None
        if ref.round is None or ref.lap is None:
            return None
        held = self.record.lap(ref.side, ref.round, ref.lap)
        if held is None or not held.lsl:
            return None
        stmt = held.statement(ref.number)
        return Found(held, stmt) if stmt is not None else None


def _has_section(text: str, section: str) -> bool:
    escaped = re.escape(section)
    return bool(
        re.search(rf"^#+\s*(?:§\s*)?{escaped}[.\s:—-]", text, re.M)
        or f"§{section}" in text
        or re.search(rf"^\*\*{escaped}[.\s:]", text, re.M)
    )
