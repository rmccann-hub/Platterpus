"""The rules between the laps of one round, and whose turn it is."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .header import check_next_lap
from .kinds import ANSWERS_FOR, reference_slots, slot_refuses
from .model import Lap, Problem, Statement
from .values import REF

# ---------------------------------------------------------------------------
# A round: the rules between laps, and whose turn it is.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Turn:
    """Whose move it is, read from the newest released lap. Tri-state honest:
    `party` is None when the files do not say (a v6 lap, or `none`)."""

    party: str | None
    lap: int | None
    source: str
    detail: str


@dataclass(frozen=True)
class Ledger:
    open_questions: tuple[tuple[str, Statement], ...]
    promises: tuple[tuple[str, Statement], ...]
    terms: tuple[tuple[str, Statement, str, Statement | None], ...]
    findings_next_round: tuple[tuple[str, Statement], ...]


def key(lap: Lap, s: Statement) -> str:
    return f"r{lap.round}l{lap.lap}#{s.sid}"


def _resolve(ref: str, here: Lap, laps: dict[int, Lap]) -> tuple[Lap, Statement] | str:
    """A reference, resolved within one round's laps (by lap number)."""
    m = REF.fullmatch(ref)
    if m is None:
        return f"{ref} is not a reference"
    owner = here
    if m.group("round") is not None:
        if here.round is not None and int(m.group("round")) != here.round:
            return "outside"  # a reference into another round is not checked here
        held = laps.get(int(m.group("lap")))
        if held is None:
            return f"{ref} names a lap this record does not hold"
        if not held.uses_language:
            return (
                f"{ref} names a lap that is not in the lap language; cite it by anchor"
            )
        owner = held
    target = owner.statement(m.group("sid"))
    if target is None:
        return f"{ref} names a statement that lap does not contain"
    return owner, target


def check_round(laps: Iterable[Lap]) -> list[tuple[Lap, Problem]]:
    """The rules between laps of one round. Only language-1 laps are judged."""
    by_number: dict[int, Lap] = {}
    problems: list[tuple[Lap, Problem]] = []
    for lap in laps:
        if lap.lap is None:
            continue
        if lap.lap in by_number:
            problems.append((lap, Problem("R1", 1, f"two laps declare lap {lap.lap}")))
            continue
        by_number[lap.lap] = lap

    for number in sorted(by_number):
        lap = by_number[number]
        if not lap.uses_language:
            continue
        for s in lap.statements:
            for slot, ref, line in reference_slots(s):
                m = REF.fullmatch(ref)
                if m is None or m.group("round") is None:
                    continue
                got = _resolve(ref, lap, by_number)
                if isinstance(got, str):
                    if got != "outside":
                        problems.append((lap, Problem("R2", line, f"{s.sid}: {got}")))
                    continue
                if int(m.group("lap")) >= number:
                    problems.append(
                        (
                            lap,
                            Problem(
                                "R3", line, f"{s.sid}: {ref} is not an earlier lap"
                            ),
                        )
                    )
                    continue
                why = slot_refuses(slot, got[1])
                if why is not None:
                    problems.append(
                        (
                            lap,
                            Problem(
                                "R10",
                                line,
                                f"{s.sid} {slot} must be {why}; {ref} is {got[1].kind} {got[1].qualifier}",
                            ),
                        )
                    )
            if s.kind == "ANSWER":
                problems.extend((lap, p) for p in _check_answer(s, lap, by_number))
        if lap.field("HANDSHAKE-VERDICT") == "GO":
            problems.extend((lap, p) for p in _check_go(lap, by_number))
        problems.extend((lap, p) for p in _check_promises_due(lap, by_number))
    return problems


def _check_answer(s: Statement, lap: Lap, laps: dict[int, Lap]) -> list[Problem]:
    target_text = s.value("answers") or ""
    if target_text.startswith("§"):
        return []  # answers a section of a lap written before the language
    got = _resolve(target_text, lap, laps)
    if isinstance(got, str):
        return [] if got == "outside" else [Problem("R2", s.line, f"{s.sid}: {got}")]
    owner, target = got
    if target.kind != "QUESTION":
        return [
            Problem(
                "R4",
                s.line,
                f"{s.sid} answers {target.kind} {target.sid}; an ANSWER answers a QUESTION",
            )
        ]
    own = owner.author == lap.author
    if own and s.qualifier != "withdrawn":
        return [
            Problem(
                "R5",
                s.line,
                f"{s.sid} answers its own side's question; the only own answer is `withdrawn`",
            )
        ]
    if not own and s.qualifier == "withdrawn":
        return [
            Problem(
                "R5",
                s.line,
                f"{s.sid}: only the side that asked can withdraw a question",
            )
        ]
    wants = target.value("wants") or ""
    if not own and s.qualifier not in ANSWERS_FOR.get(wants, frozenset()):
        legal = ", ".join(sorted(ANSWERS_FOR.get(wants, frozenset())))
        return [
            Problem(
                "R6",
                s.line,
                f"{s.sid}: a question wanting {wants} takes {legal}; not {s.qualifier}",
            )
        ]
    return []


def _statements_through(
    laps: dict[int, Lap], number: int
) -> list[tuple[Lap, Statement]]:
    return [
        (lap, s)
        for n in sorted(laps)
        if n <= number and laps[n].uses_language
        for lap in (laps[n],)
        for s in lap.statements
    ]


def _answered(laps: dict[int, Lap], number: int) -> set[str]:
    done: set[str] = set()
    for lap, s in _statements_through(laps, number):
        if s.kind != "ANSWER":
            continue
        got = _resolve(s.value("answers") or "", lap, laps)
        if not isinstance(got, str):
            done.add(key(*got))
    return done


def _check_go(lap: Lap, laps: dict[int, Lap]) -> list[Problem]:
    number = lap.lap or 0
    problems: list[Problem] = []
    answered = _answered(laps, number)
    for owner, s in _statements_through(laps, number):
        if (
            s.kind == "QUESTION"
            and s.qualifier == "blocking"
            and key(owner, s) not in answered
        ):
            problems.append(
                Problem(
                    "R7",
                    1,
                    f"GO with a blocking question unanswered: {key(owner, s)} (S-14)",
                )
            )
    for ref, _term, state, status in _term_states(laps, number):
        if state in {"met", "waived"}:
            continue
        if (
            state == "pending"
            and status is not None
            and status.value("on") != lap.author
        ):
            continue  # the other side's half remains, which a GO may stand over
        owed = " on this side" if state == "pending" else ""
        problems.append(
            Problem("R8", 1, f"GO with close condition {ref} {state}{owed}")
        )
    return problems


def _term_states(
    laps: dict[int, Lap], number: int
) -> list[tuple[str, Statement, str, Statement | None]]:
    """Every TERM set in the round, with its latest state as of lap `number`.

    Each entry is (reference, the `set` statement, the state, the statement that
    reported that state or None). The state is `unreported` until a lap says one.
    """
    states: dict[str, tuple[Statement, str, Statement | None]] = {}
    for owner, s in _statements_through(laps, number):
        if s.kind != "TERM":
            continue
        if s.qualifier == "set":
            states.setdefault(key(owner, s), (s, "unreported", None))
            continue
        got = _resolve(s.value("term") or "", owner, laps)
        if not isinstance(got, str) and key(*got) in states:
            states[key(*got)] = (states[key(*got)][0], s.qualifier, s)
    return [(ref, s, state, status) for ref, (s, state, status) in states.items()]


def _check_promises_due(lap: Lap, laps: dict[int, Lap]) -> list[Problem]:
    """A lap that falls due under an earlier PROMISE keeps it, or says why not."""
    problems: list[Problem] = []
    number = lap.lap or 0
    for owner, p in _statements_through(laps, number - 1):
        if (
            p.kind != "PROMISE"
            or p.qualifier != "verdict"
            or owner.author != lap.author
        ):
            continue
        due = p.value("due") or ""
        if due != f"lap {number}":
            continue
        promised = p.value("verdict")
        triggered = any(
            s.kind == "CLAIM" and s.value("triggers") == key(owner, p)
            for s in lap.statements
        )
        if lap.field("HANDSHAKE-VERDICT") != promised and not triggered:
            problems.append(
                Problem(
                    "R9",
                    1,
                    f"{key(owner, p)} promised {promised} in this lap; it declares "
                    f"{lap.field('HANDSHAKE-VERDICT')} and no CLAIM `triggers` the promise",
                )
            )
    return problems


def turn(laps: Iterable[Lap]) -> Turn:
    """Whose move it is, from the newest released lap of the round."""
    released = sorted(
        (lap for lap in laps if lap.lap is not None and lap.released),
        key=lambda lap: lap.lap or 0,
    )
    if not released:
        return Turn(None, None, "no released lap", "the opener has not sent lap 1")
    newest = released[-1]
    value = newest.field("HANDSHAKE-NEXT-LAP")
    source = f"{newest.name} (lap {newest.lap}, {newest.author})"
    if not newest.uses_language:
        return Turn(
            None,
            None,
            source,
            f"not determined: that lap is not in the lap language; it says {value!r}",
        )
    if value is None or check_next_lap(value) is not None:
        return Turn(
            None,
            None,
            source,
            "not determined: HANDSHAKE-NEXT-LAP is missing or malformed",
        )
    if value == "none":
        return Turn(
            None,
            None,
            source,
            "no further lap in this round; the next round opens with the provider's "
            "lap 1 (§1a: cyanrip-fork)",
        )
    lap_text, party = value.split(" ")
    return Turn(party, int(lap_text), source, f"lap {lap_text} is {party}'s")


def ledger(laps: Iterable[Lap]) -> Ledger:
    by_number = {lap.lap: lap for lap in laps if lap.lap is not None}
    newest = max(by_number, default=0)
    answered = _answered(by_number, newest)
    items = _statements_through(by_number, newest)
    return Ledger(
        open_questions=tuple(
            (key(o, s), s)
            for o, s in items
            if s.kind == "QUESTION" and key(o, s) not in answered
        ),
        promises=tuple((key(o, s), s) for o, s in items if s.kind == "PROMISE"),
        terms=tuple(_term_states(by_number, newest)),
        findings_next_round=tuple(
            (key(o, s), s)
            for o, s in items
            if s.kind == "FINDING" and s.value("target") == "next-round"
        ),
    )
