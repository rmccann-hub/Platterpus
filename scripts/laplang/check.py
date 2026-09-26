"""The checks LSL 1 makes of one lap, by the spec's numbered refusals.

The spec (§"What the checker refuses") numbers six refusals. Each problem here
carries the number it is about:

* `LSL.1` a kind or grade not in the table;
* `LSL.2` a required field missing;
* `LSL.3` a gap or a repeat in the numbering;
* `LSL.4` a reference that does not parse, or one in the author's tree that does
  not resolve;
* `LSL.5` not exactly one VERDICT, one that disagrees with `HANDSHAKE-VERDICT`, or
  a `basis:` naming a statement that does not exist or carries no claim;
* `LSL.6` an `ASK BLOCKING` with no `breaks:`.

Three more rules are stated elsewhere in the spec and have their own ids:
`LSL.syntax` (any other line, `grammar`), `LSL.field` (a field outside the kinds
table) and `LSL.value` (a value outside the shape the table gives it, such as an
`owner:` that is not us, them or operator). `LSL.header` covers the three wire
headers the body's references depend on: who wrote the lap, its round, its lap.
"""

from __future__ import annotations

import re
from typing import Final

from .context import Context
from .model import Side, Statement
from .refs import first_token, is_run, parse_artifact, parse_statement, tokens

DATE_RE: Final[re.Pattern[str]] = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
VERDICTS: Final[frozenset[str]] = frozenset({"GO", "HOLD", "OPEN"})
#: Statements that carry no claim, so a verdict cannot rest on them (the spec
#: names NOTE and ASK; a VERDICT resting on itself is the same mistake).
NO_CLAIM: Final[frozenset[str]] = frozenset({"NOTE", "ASK", "VERDICT"})


def check_lap(ctx: Context) -> None:
    """Every LSL 1 check of `ctx.lap`. Amendment checks are `amend.py`'s."""
    lap = ctx.lap
    _check_headers(ctx)
    if not lap.statements:
        ctx.refuse(1, "LSL.5", "an LSL lap with no statements, so no VERDICT")
    _check_numbering(ctx)
    verdicts = [s for s in lap.statements if s.kind == "VERDICT"]
    if lap.statements and len(verdicts) != 1:
        ctx.refuse(
            1, "LSL.5", f"{len(verdicts)} VERDICT statements; exactly one is required"
        )
    for stmt in lap.statements:
        if not _check_kind(ctx, stmt):
            continue
        _check_fields(ctx, stmt)
        if stmt.kind == "VERDICT":
            _check_verdict(ctx, stmt)


def _check_headers(ctx: Context) -> None:
    lap = ctx.lap
    if lap.author is None:
        ctx.refuse(
            1, "LSL.header", "HANDSHAKE-FROM names neither cyanrip-fork nor platterpus"
        )
    if lap.round is None or lap.lap is None:
        ctx.refuse(
            1, "LSL.header", "HANDSHAKE-ROUND and HANDSHAKE-LAP must each be a number"
        )


def _check_numbering(ctx: Context) -> None:
    seen: set[int] = set()
    gap_reported = False
    for expected, stmt in enumerate(ctx.lap.statements, start=1):
        if stmt.n in seen:
            ctx.refuse(stmt.line, "LSL.3", f"S{stmt.n} is numbered twice")
        elif stmt.n != expected and not gap_reported:
            ctx.refuse(
                stmt.line,
                "LSL.3",
                f"S{stmt.n} where S{expected} was expected; numbers run from S1 with no gaps",
            )
            gap_reported = True
        seen.add(stmt.n)


def _check_kind(ctx: Context, stmt: Statement) -> bool:
    grades = ctx.tables.grades.get(stmt.kind)
    if grades is None:
        ctx.refuse(stmt.line, "LSL.1", f"{stmt.tag}: {stmt.kind} is not a kind")
        return False
    if grades and stmt.grade not in grades:
        ctx.refuse(
            stmt.line,
            "LSL.1",
            f"{stmt.tag}: a {stmt.kind} takes one grade of {sorted(grades)}",
        )
        return False
    if not grades and stmt.grade is not None:
        ctx.refuse(stmt.line, "LSL.1", f"{stmt.tag}: a {stmt.kind} takes no grade")
        return False
    return True


def _check_fields(ctx: Context, stmt: Statement) -> None:
    for fld in stmt.fields:
        if fld.name not in ctx.tables.fields:
            ctx.refuse(fld.line, "LSL.field", f"{stmt.tag}: {fld.name}: is not a field")
    for name in ctx.tables.requires(stmt.kind, stmt.grade):
        if not stmt.has(name):
            rule = ctx.tables.source(stmt.kind, stmt.grade, name)
            ctx.refuse(stmt.line, rule, f"{stmt.tag}: needs a {name}: field")
    _check_evidence(ctx, stmt)
    for fld in stmt.values("re"):
        token = first_token(fld.value)
        if parse_statement(token) is not None:
            ctx.statement(token, fld.line, "LSL.4")
        elif not ctx.artifact(token, fld.line, "LSL.4"):
            ctx.refuse(
                fld.line,
                "LSL.4",
                f"{stmt.tag}: re: {token!r} is neither a statement nor an artifact",
            )
    for fld in stmt.values("because"):
        for token in tokens(fld.value):
            ctx.statement(token, fld.line, "LSL.4")
    for fld in stmt.values("commit"):
        sha = first_token(fld.value)
        if not re.fullmatch(r"[0-9a-f]{7,40}", sha):
            ctx.refuse(
                fld.line, "LSL.4", f"{stmt.tag}: commit: {sha!r} is not a commit SHA"
            )
        elif ctx.lap.author is not None:
            ctx.report(fld.line, "LSL.4", ctx.trees.commit(ctx.lap.author, sha))
    for fld in stmt.values("owner"):
        if fld.value not in ("us", "them", "operator"):
            ctx.refuse(
                fld.line,
                "LSL.value",
                f"{stmt.tag}: owner: is us, them or operator, not {fld.value!r}",
            )
    for fld in stmt.values("when"):
        if DATE_RE.search(fld.value):
            ctx.refuse(
                fld.line, "LSL.value", f"{stmt.tag}: when: is a condition, never a date"
            )
    for fld in stmt.values("target"):
        _check_target(ctx, stmt, fld.value, fld.line)
    if stmt.kind == "FACT" and stmt.grade == "relayed":
        ctx.warn(
            stmt.line, "LSL.relayed", f"{stmt.tag}: a relay is in neither repository"
        )


def _check_target(ctx: Context, stmt: Statement, value: str, line: int) -> None:
    """`target:` on an ASK. A FINDING's `target:` has its own values (A3)."""
    if stmt.kind != "ASK":
        return
    if value not in ("BLOCKING", "NEXT-ROUND"):
        ctx.refuse(line, "LSL.value", f"{stmt.tag}: target: is BLOCKING or NEXT-ROUND")
    elif value == "BLOCKING" and not stmt.has("breaks"):
        ctx.refuse(
            line,
            "LSL.6",
            f"{stmt.tag}: a BLOCKING question names what it breaks (breaks:)",
        )


def _check_evidence(ctx: Context, stmt: Statement) -> None:
    runs = 0
    artifacts: list[Side] = []
    for fld in stmt.values("evidence"):
        if is_run(fld.value):
            if " => " not in fld.value:
                ctx.refuse(
                    fld.line,
                    "LSL.4",
                    f"{stmt.tag}: a run: names its command and its result, as 'run: CMD => RESULT'",
                )
            runs += 1
            continue
        token = first_token(fld.value)
        ref = parse_artifact(token)
        if ref is None:
            ctx.refuse(
                fld.line,
                "LSL.4",
                f"{stmt.tag}: evidence {token!r} is neither 'run: CMD => RESULT' nor side@commit:path[:line[-line]]",
            )
            continue
        artifacts.append(ref.side)
        ctx.report(fld.line, "LSL.4", ctx.trees.artifact(ref, ctx.lap.author))
    if not stmt.values("evidence"):
        return
    if stmt.kind == "FACT" and stmt.grade == "measured":
        if runs == 0 and ctx.lap.author not in artifacts:
            ctx.refuse(
                stmt.line,
                "LSL.2",
                f"{stmt.tag}: measured needs a run: or an artifact the author produced",
            )
    if stmt.kind == "FACT" and stmt.grade == "read" and not artifacts:
        ctx.refuse(stmt.line, "LSL.2", f"{stmt.tag}: read needs an artifact reference")


def _check_verdict(ctx: Context, stmt: Statement) -> None:
    said = stmt.sentence.rstrip(".")
    if said not in VERDICTS:
        ctx.refuse(stmt.line, "LSL.5", f"{stmt.tag}: the verdict is GO, HOLD or OPEN")
    elif ctx.lap.verdict != said:
        ctx.refuse(
            stmt.line,
            "LSL.5",
            f"{stmt.tag}: says {said} and HANDSHAKE-VERDICT says {ctx.lap.verdict or 'nothing'}",
        )
    for fld in stmt.values("basis"):
        for token in tokens(fld.value):
            if not re.fullmatch(r"S\d+", token):
                ctx.refuse(
                    fld.line,
                    "LSL.5",
                    f"{stmt.tag}: basis: {token!r} is not a statement of this lap",
                )
                continue
            target = ctx.lap.statement(int(token[1:]))
            if target is None:
                ctx.refuse(
                    fld.line, "LSL.5", f"{stmt.tag}: basis: {token} does not exist"
                )
            elif target.kind in NO_CLAIM:
                ctx.refuse(
                    fld.line,
                    "LSL.5",
                    f"{stmt.tag}: basis: {token} is a {target.kind}, which carries no claim",
                )
