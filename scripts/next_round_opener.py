"""§1a in a lap of ours: the NEXT round is the provider's to open, not ours or "either".

`docs/handshake-protocol.md` §1a: **the provider opens every round**, and between
cyanrip and Platterpus the provider is cyanrip, because only the side that
produces the artifact under review can mint the commit a round is about. The one
exception is E3: the operator hands us the opening *in writing*, as three
column-0 fields:

    HANDSHAKE-OVERRIDE: 1a — Platterpus opens round N
    HANDSHAKE-OVERRIDE-BY: operator (name), <date>
    HANDSHAKE-OVERRIDE-WHY: <a reason a later reader can weigh>

WHY THIS EXISTS (TASKS R171, 2026-11-16). Our round 40 lap 4 closed the round
with ``HANDSHAKE-NEXT-LAP: none in round 40: … Round 41 opens with whichever side
writes its lap 1.`` That sentence contradicts §1a, and ``handshake.py --check``
passed it with no warning, because row C46 (``next_lap_problems``) grades only
the value's OPENING (``<n> (ours):``, ``<n> (yours):`` or ``none``) and reads
none of the prose after it. Round 29 lap 4 had said the same thing (*"Round 30
opens with a lap 1 from either side"*) and nothing caught that either.

HOW NARROW, AND WHY. The value is prose for a person, so this does not try to
understand it. It refuses one shape only: a clause (a stretch of the value
between full stops or semicolons) that

1. names the NEXT round, as ``round <N+1>`` or ``next round``;
2. talks about opening it (``open``, ``opens``, ``opener``, ``lap 1``); and
3. gives the opening to us or to no one in particular: ``either``,
   ``whichever``, ``any side``, ``ours``, ``our lap 1``, ``we open``,
   ``Platterpus opens``.

All three in the SAME clause. So the correct sentences we have actually sent —
*"round 41 is yours to open"*, *"round 32 opens with your lap 1"*, *"Round 36 is
yours to open under §1a"* — pass, and so does a lap number like ``3 (yours): …``
or ``7 (ours): …``, which is about the current round and names no round at all.
A "not ours" or "never either" is left alone too, because negating the wrong
opener is the right statement.

Every function here reports and never raises, like every other check the gate
runs: a checker that crashed on an odd lap would be a checker nobody runs.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Final

#: The header field whose prose is read. Same name as ``handshake.NEXT_LAP_FIELD``;
#: restated rather than imported so this module has no import of the gate it is a
#: part of (the gate imports it, and a cycle would need a function-local import).
NEXT_LAP_FIELD: Final[str] = "HANDSHAKE-NEXT-LAP"

#: §6a-ter's override fields, as §1a's E3 spells them.
OVERRIDE_FIELD: Final[str] = "HANDSHAKE-OVERRIDE"
OVERRIDE_BY_FIELD: Final[str] = "HANDSHAKE-OVERRIDE-BY"
OVERRIDE_WHY_FIELD: Final[str] = "HANDSHAKE-OVERRIDE-WHY"

#: A clause ends at a full stop or semicolon FOLLOWED BY WHITESPACE (or the end),
#: so a version like ``0.6.63`` or a sha with dots stays inside its clause.
_CLAUSE_END: Final[re.Pattern[str]] = re.compile(r"[.;](?:\s+|$)")

#: Condition 2: the clause is about opening a round. ``lap 1`` counts because
#: "round 30's lap 1 is ours" says who opens without the verb.
_OPENING: Final[re.Pattern[str]] = re.compile(
    r"\bopen(?:s|ed|er|ing)?\b|\blap\s{0,3}0{0,3}1\b", re.IGNORECASE
)

#: Condition 3: the opening given to us, or to whoever gets there first. The
#: look-behinds leave a NEGATED wrong opener alone ("yours to open, not ours").
#: ``\bours\b`` does not match inside "yours": there is no word boundary there.
_WRONG_OPENER: Final[re.Pattern[str]] = re.compile(
    r"(?<!not )(?<!never )"
    r"(?:\beither\b|\bwhichever\b|\bany\s{1,3}side\b|\bours\b|\bour\s{1,3}lap\s{0,3}0{0,3}1\b"
    r"|\bwe(?:\s{1,3}will|\s{1,3}shall|'ll)?\s{1,3}open\b|\bplatterpus\s{1,3}opens\b)",
    re.IGNORECASE,
)

#: E3's rule id at the head of an override value: ``1a`` or ``§1a``.
_E3_RULE: Final[re.Pattern[str]] = re.compile(r"^§?1a\b", re.IGNORECASE)


#: Condition 1's raw material: every ``round <n>`` and every ``next round``. A
#: literal rather than a pattern built per lap from N, so the regex timing sweep
#: (`tests/test_regex_bounded_time.py`) can time it; :func:`_names_round` compares
#: the number afterwards.
_ROUND_REF: Final[re.Pattern[str]] = re.compile(
    r"\bround\s{1,3}0{0,3}(?P<n>\d{1,4})\b|\bnext\s{1,3}round\b", re.IGNORECASE
)


def _names_round(text: str, wanted: int, *, next_round_counts: bool) -> bool:
    """Whether ``text`` names round ``wanted`` (or, if allowed, "next round")."""
    for match in _ROUND_REF.finditer(text):
        number = match.group("n")
        if number is None:
            if next_round_counts:
                return True
        elif int(number) == wanted:
            return True
    return False


def wrong_opener_clauses(next_lap: str, round_no: int) -> list[str]:
    """Every clause of a ``HANDSHAKE-NEXT-LAP`` value that gives round N+1 away.

    Empty for a value that says nothing about the next round's opener, or says
    the right thing. Each returned clause is stripped, for quoting in a refusal.
    """
    found: list[str] = []
    for clause in _CLAUSE_END.split(next_lap):
        if (
            _names_round(clause, round_no + 1, next_round_counts=True)
            and _OPENING.search(clause)
            and _WRONG_OPENER.search(clause)
        ):
            found.append(clause.strip())
    return found


def e3_override_for(declared: Sequence[tuple[str, str]], round_no: int) -> bool:
    """Whether the lap records a complete E3 override handing us round N+1.

    All three fields, as §6a-ter requires (*"Rule id, who, and why. All
    three."*), and the rule line must name the round it hands over, so an
    override recorded for one round cannot be carried into the next.
    """
    rules = [v for k, v in declared if k == OVERRIDE_FIELD]
    has_by = any(k == OVERRIDE_BY_FIELD and v.strip() for k, v in declared)
    has_why = any(k == OVERRIDE_WHY_FIELD and v.strip() for k, v in declared)
    hands_over = any(
        _E3_RULE.match(v.strip())
        and _names_round(v, round_no + 1, next_round_counts=False)
        for v in rules
    )
    return hands_over and has_by and has_why


def opener_problems(declared: Sequence[tuple[str, str]], where: str) -> list[str]:
    """§1a's refusal for one outbound lap, given its column-0 declarations in order.

    ``declared`` is every ``KEY: value`` the gate read outside fenced examples,
    duplicates kept (two override lines are legitimate; a dict would lose one).
    Empty when the round number cannot be read: that is ``check_wire_header``'s
    to report, and guessing N here would refuse against the wrong round.
    """
    rounds = [v for k, v in declared if k == "HANDSHAKE-ROUND"]
    try:
        round_no = int(rounds[0].split()[0])
    except (IndexError, ValueError):
        return []
    problems: list[str] = []
    for key, value in declared:
        if key != NEXT_LAP_FIELD:
            continue
        for clause in wrong_opener_clauses(value, round_no):
            if e3_override_for(declared, round_no):
                continue
            problems.append(
                f"{where}: {NEXT_LAP_FIELD} gives round {round_no + 1}'s opening to "
                f"us or to either side: {clause[:120]!r}. Protocol §1a: the "
                "provider, cyanrip, opens every round. Write it as 'round "
                f"{round_no + 1} is yours to open', or record the operator's E3 "
                f"override (`{OVERRIDE_FIELD}: 1a — Platterpus opens round "
                f"{round_no + 1}` with its -BY and -WHY lines)."
            )
    return problems
