"""The checks our proposed amendments add to LSL 1, one id each.

The spec for every amendment is `docs/handshake/outbound/artifacts/
lsl-amendments-1.md`, and each check here reports under that amendment's id:

* `A1` close conditions are statements (`TERM`), and a `GO` waits for them;
* `A2` a pre-commit binds: a `WILL` with `verdict:` is checked when it falls due;
* `A3` a defect is a `FINDING`, its origin is stated first, and ours says
  whether its shape could hold on the other side;
* `A4` a fact names the builds or commits it holds for (`holds:`);
* `A5` a measurement names its population, and whether it is closed (`examined:`);
* `A6` only a checkable claim can carry weight in `basis:` or `because:`;
* `A7` an answer names its question (`answers:`), and a `GO` waits for every
  blocking question the other side has asked;
* `A8` a correction carries evidence, like any claim.

A4, A5 and A8 only add required fields, so `tables.py` enforces them and they
need nothing here beyond A4's and A5's value shapes.

"us" and "them" in `owner:` and `on:` are relative to the lap's author, the same
as LSL 1's `owner:`. Checks that span laps turn them into the absolute side.
"""

from __future__ import annotations

import re
from typing import Final

from .context import Context, Found
from .model import Statement
from .refs import first_token, parse_artifact, parse_statement, tokens
from .round_rules import check_round_rules

EXAMINED_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<count>\d+) (?P<unit>\S.*?), (?P<state>closed|open)$"
)
#: A build or a commit: a hex SHA, or a dotted version number.
HOLDS_RE: Final[re.Pattern[str]] = re.compile(r"\b[0-9a-f]{7,40}\b|\b\d+\.\d+")
FINDING_TARGETS: Final[frozenset[str]] = frozenset({"NEXT-ROUND", "BLOCKING", "FIXED"})
#: What cannot carry weight (A6): it makes no claim, or no claim either side can check.
NO_WEIGHT_KINDS: Final[frozenset[str]] = frozenset(
    {"NOTE", "ASK", "VERDICT", "WILL", "UNKNOWN"}
)


def check_amendments(ctx: Context) -> None:
    """Every switched-on amendment's check of `ctx.lap`."""
    on = ctx.tables.amendments
    for stmt in ctx.lap.statements:
        if "A1" in on and stmt.kind == "TERM":
            _check_term(ctx, stmt)
        if "A2" in on:
            _check_promise_fields(ctx, stmt)
        if "A3" in on and stmt.kind == "FINDING":
            _check_finding(ctx, stmt)
        if "A4" in on:
            for fld in stmt.values("holds"):
                if not HOLDS_RE.search(fld.value):
                    ctx.refuse(
                        fld.line, "A4", f"{stmt.tag}: holds: names no build or commit"
                    )
        if "A5" in on:
            _check_examined(ctx, stmt)
        if "A6" in on:
            _check_weight(ctx, stmt)
        if "A7" in on:
            _check_answers(ctx, stmt)
    check_round_rules(ctx)


def _resolve(ctx: Context, stmt: Statement, name: str, rule: str) -> Found | None:
    """The statement a single-reference field names, reporting failures under `rule`."""
    for fld in stmt.values(name):
        got = ctx.statement(first_token(fld.value), fld.line, rule)
        return got if isinstance(got, Found) else None
    return None


def _check_term(ctx: Context, stmt: Statement) -> None:
    if stmt.grade == "set":
        if ctx.lap.lap != 1 and not (stmt.has("restates") or stmt.has("regression")):
            ctx.refuse(
                stmt.line,
                "A1",
                f"{stmt.tag}: a close condition set after lap 1 must restate lap 1's (restates:) or be a regression (regression:); S-13",
            )
        for fld in stmt.values("restates"):
            ctx.statement(first_token(fld.value), fld.line, "A1")
        return
    found = _resolve(ctx, stmt, "term", "A1")
    if found is not None and not (
        found.statement.kind == "TERM" and found.statement.grade == "set"
    ):
        ctx.refuse(
            stmt.line,
            "A1",
            f"{stmt.tag}: term: names a {found.statement.tag}, not a TERM set",
        )
    for fld in stmt.values("on"):
        if fld.value not in ("us", "them"):
            ctx.refuse(
                fld.line, "A1", f"{stmt.tag}: on: is us or them, not {fld.value!r}"
            )


def _check_promise_fields(ctx: Context, stmt: Statement) -> None:
    if stmt.kind == "WILL" and stmt.has("verdict"):
        for fld in stmt.values("verdict"):
            if fld.value not in ("GO", "HOLD"):
                ctx.refuse(fld.line, "A2", f"{stmt.tag}: verdict: is GO or HOLD")
        if [f.value for f in stmt.values("owner")] != ["us"]:
            ctx.refuse(
                stmt.line,
                "A2",
                f"{stmt.tag}: only the author can pre-commit its own verdict (owner: us)",
            )
    elif stmt.has("unless") or stmt.has("verdict"):
        ctx.refuse(
            stmt.line, "A2", f"{stmt.tag}: verdict: and unless: belong to a WILL"
        )
    for fld in stmt.values("triggers"):
        got = ctx.statement(first_token(fld.value), fld.line, "A2")
        if isinstance(got, Found) and not (
            got.statement.kind == "WILL" and got.statement.has("verdict")
        ):
            ctx.refuse(
                fld.line,
                "A2",
                f"{stmt.tag}: triggers: names a {got.statement.tag}, not a pre-committed verdict",
            )


def _check_finding(ctx: Context, stmt: Statement) -> None:
    author = ctx.lap.author
    for fld in stmt.values("in"):
        ref = parse_artifact(first_token(fld.value))
        if ref is None:
            ctx.refuse(
                fld.line,
                "A3",
                f"{stmt.tag}: in: is an artifact reference, side@commit:path",
            )
            continue
        ctx.report(fld.line, "A3", ctx.trees.artifact(ref, author))
        if stmt.grade == "ours" and ref.side != author:
            ctx.refuse(
                fld.line,
                "A3",
                f"{stmt.tag}: a finding of ours is in our tree, not {ref.side}'s",
            )
        if stmt.grade == "yours" and author is not None and ref.side == author:
            ctx.refuse(
                fld.line,
                "A3",
                f"{stmt.tag}: a finding of yours cannot be in our own tree; say whose it is first",
            )
    for fld in stmt.values("target"):
        if fld.value not in FINDING_TARGETS:
            ctx.refuse(
                fld.line, "A3", f"{stmt.tag}: target: is NEXT-ROUND, BLOCKING or FIXED"
            )
        elif fld.value == "BLOCKING" and not stmt.has("breaks"):
            ctx.refuse(
                fld.line,
                "A3",
                f"{stmt.tag}: a blocking finding names what it breaks (breaks:); S-14",
            )
        elif fld.value == "FIXED" and not stmt.has("landed"):
            ctx.refuse(
                fld.line,
                "A3",
                f"{stmt.tag}: a fixed finding names where the fix landed (landed:)",
            )
    for fld in stmt.values("landed"):
        if not ctx.artifact(first_token(fld.value), fld.line, "A3"):
            ctx.refuse(fld.line, "A3", f"{stmt.tag}: landed: is an artifact reference")
    for fld in stmt.values("portable"):
        if fld.value not in ("yes", "no"):
            ctx.refuse(fld.line, "A3", f"{stmt.tag}: portable: is yes or no")


def _check_examined(ctx: Context, stmt: Statement) -> None:
    for fld in stmt.values("examined"):
        match = EXAMINED_RE.match(fld.value)
        if match is None:
            ctx.refuse(
                fld.line,
                "A5",
                f"{stmt.tag}: examined: is '<count> <unit>, closed' or '…, open'",
            )
        elif int(match["count"]) < 1:
            ctx.refuse(
                fld.line,
                "A5",
                f"{stmt.tag}: examined: counts at least one; a measurement of nothing is not a measurement",
            )
        elif match["state"] == "open" and not stmt.has("missing"):
            ctx.refuse(
                fld.line,
                "A5",
                f"{stmt.tag}: an open population says what the count leaves out (missing:)",
            )


def _check_weight(ctx: Context, stmt: Statement) -> None:
    for name in ("basis", "because"):
        for fld in stmt.values(name):
            for token in tokens(fld.value):
                ref = parse_statement(token)
                if ref is None or ref.is_section:
                    continue
                found = ctx.lookup(token)
                if found is None:
                    continue
                target = found.statement
                if name == "basis" and target.kind in ("NOTE", "ASK", "VERDICT"):
                    continue  # LSL.5 already refuses these in basis:
                if target.kind in NO_WEIGHT_KINDS or (
                    target.kind == "FACT" and target.grade == "relayed"
                ):
                    ctx.refuse(
                        fld.line,
                        "A6",
                        f"{stmt.tag}: {name}: {token} is a {target.tag}, which cannot carry weight",
                    )


def _check_answers(ctx: Context, stmt: Statement) -> None:
    for fld in stmt.values("answers"):
        token = first_token(fld.value)
        got = ctx.statement(token, fld.line, "A7")
        if not isinstance(got, Found):
            continue
        if got.lap is ctx.lap:
            ctx.refuse(fld.line, "A7", f"{stmt.tag}: answers a question in its own lap")
        elif got.statement.kind != "ASK":
            ctx.refuse(
                fld.line,
                "A7",
                f"{stmt.tag}: answers: names a {got.statement.tag}, not an ASK",
            )
        elif got.lap.author == ctx.lap.author:
            ctx.refuse(
                fld.line,
                "A7",
                f"{stmt.tag}: answers our own question; only the other side answers it",
            )
