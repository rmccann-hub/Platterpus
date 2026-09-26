"""The amendments' checks that span a round: what a `GO` must wait for.

A1, A2 and A7 cannot be checked inside one lap. A close condition set in lap 1
is met in lap 4; a pre-commit in lap 3 falls due in lap 5; a blocking question
from one side is answered by the other. So these read every held LSL lap of the
round up to the one under check, in order, and decide from the whole sequence.

A held lap that is not in LSL contributes nothing here: it has no statements to
read, and a check that guessed from its prose would be a second parser of prose.
"""

from __future__ import annotations

from dataclasses import dataclass

from .context import Context
from .model import Lap, Side, Statement, other
from .refs import first_token, parse_statement


@dataclass(frozen=True)
class Placed:
    """A statement and where it sits in the round: (lap number, statement number)."""

    lap: Lap
    statement: Statement

    @property
    def order(self) -> tuple[int, int]:
        return (self.lap.lap or 0, self.statement.n)

    @property
    def key(self) -> tuple[Side | None, int | None, int]:
        return (self.lap.author, self.lap.lap, self.statement.n)


def check_round_rules(ctx: Context) -> None:
    """A1, A2 and A7, whichever are switched on."""
    on = ctx.tables.amendments
    if "A2" in on:
        _check_promise_kept(ctx)
    if ctx.lap.verdict != "GO":
        return
    if "A1" in on:
        _check_go_over_terms(ctx)
    if "A7" in on:
        _check_go_over_questions(ctx)


def _round_statements(ctx: Context) -> list[Placed]:
    """Every statement of an LSL lap of this round up to and including this one."""
    placed: list[Placed] = []
    if ctx.lap.round is not None and ctx.lap.lap is not None:
        for held in ctx.record.round_laps(ctx.lap.round):
            if held.lsl and held.lap is not None and held.lap < ctx.lap.lap:
                placed.extend(Placed(held, s) for s in held.statements)
    placed.extend(Placed(ctx.lap, s) for s in ctx.lap.statements)
    return sorted(placed, key=lambda p: p.order)


def _absolute(relative: str, author: Side | None) -> Side | None:
    if author is None:
        return None
    return author if relative == "us" else other(author) if relative == "them" else None


def _check_go_over_terms(ctx: Context) -> None:
    placed = _round_statements(ctx)
    status: dict[tuple[Side | None, int | None, int], Placed] = {}
    conditions: list[Placed] = []
    for item in placed:
        s = item.statement
        if s.kind != "TERM":
            continue
        if s.grade == "set":
            conditions.append(item)
            continue
        target = _term_target(ctx, item)
        if target is not None:
            status[target] = item
    go_line = verdict_line(ctx.lap)
    for condition in conditions:
        latest = status.get(condition.key)
        name = _name(ctx, condition)
        if latest is None:
            ctx.refuse(go_line, "A1", f"GO while close condition {name} has no status")
            continue
        grade = latest.statement.grade
        if grade == "unmet":
            ctx.refuse(go_line, "A1", f"GO while close condition {name} is unmet")
        elif grade == "pending":
            on_value = (
                first_token(latest.statement.values("on")[0].value)
                if latest.statement.has("on")
                else ""
            )
            if _absolute(on_value, latest.lap.author) == ctx.lap.author:
                ctx.refuse(
                    go_line,
                    "A1",
                    f"GO over our own pending half of close condition {name}; a side may say GO over the other side's pending half, never its own",
                )


def _term_target(
    ctx: Context, item: Placed
) -> tuple[Side | None, int | None, int] | None:
    """The key of the TERM set a status statement names, without reporting."""
    for fld in item.statement.values("term"):
        ref = parse_statement(first_token(fld.value))
        if ref is None or ref.is_section or ref.number is None:
            return None
        if ref.side is None:
            return (item.lap.author, item.lap.lap, ref.number)
        return (ref.side, ref.lap, ref.number)
    return None


def _check_promise_kept(ctx: Context) -> None:
    """The author's previous lap in the round pre-committed a verdict: is it kept?"""
    lap = ctx.lap
    if lap.round is None or lap.lap is None or lap.author is None:
        return
    previous = [
        h
        for h in ctx.record.round_laps(lap.round)
        if h.lsl and h.author == lap.author and h.lap is not None and h.lap < lap.lap
    ]
    if not previous:
        return
    prior = previous[-1]
    triggered = set()
    for s in lap.statements:
        for fld in s.values("triggers"):
            ref = parse_statement(first_token(fld.value))
            if ref is not None and ref.number is not None and ref.lap == prior.lap:
                triggered.add(ref.number)
    for will in prior.statements:
        if will.kind != "WILL" or not will.has("verdict"):
            continue
        promised = will.values("verdict")[0].value
        if lap.verdict != promised and will.n not in triggered:
            ctx.refuse(
                verdict_line(lap),
                "A2",
                f"lap {prior.lap} promised {promised} unless a named condition came true (S{will.n}); this lap declares {lap.verdict} and no statement triggers: that promise",
            )


def _check_go_over_questions(ctx: Context) -> None:
    author = ctx.lap.author
    if author is None:
        return
    placed = _round_statements(ctx)
    answered: set[tuple[Side | None, int | None, int]] = set()
    for item in placed:
        if item.lap.author != author:
            continue
        for fld in item.statement.values("answers"):
            ref = parse_statement(first_token(fld.value))
            if ref is not None and ref.number is not None and ref.side is not None:
                answered.add((ref.side, ref.lap, ref.number))
    for item in placed:
        s = item.statement
        if item.lap.author == author or s.kind != "ASK":
            continue
        if [f.value for f in s.values("target")] != ["BLOCKING"]:
            continue
        if item.key not in answered:
            ctx.refuse(
                verdict_line(ctx.lap),
                "A7",
                f"GO while a blocking question is unanswered: {_name(ctx, item)}; S-14",
            )


def verdict_line(lap: Lap) -> int:
    for s in lap.statements:
        if s.kind == "VERDICT":
            return s.line
    return 1


def _name(ctx: Context, item: Placed) -> str:
    if item.lap is ctx.lap:
        return f"S{item.statement.n}"
    return f"{item.lap.author}:R{item.lap.round}.L{item.lap.lap}.S{item.statement.n}"
