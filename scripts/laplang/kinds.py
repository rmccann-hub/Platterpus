"""The eight statement kinds, the attributes each qualifier takes, and the
rules a single statement is held to.
"""

from __future__ import annotations

from typing import Final

from .model import Problem, Statement
from .values import (
    REF,
    Check,
    check_anchor,
    check_answer_target,
    check_cite,
    check_cite_line,
    check_date,
    check_due,
    check_examined,
    check_location,
    check_operator,
    check_party,
    check_ref,
    check_refs,
    check_restates,
    check_text,
    check_verdict,
    check_yes_no,
    words,
)

#: The longest text a statement may carry, in words. A statement is one point;
#: a longer one is two points sharing an ID, and the second can't be answered.
MAX_STATEMENT_WORDS: Final[int] = 120

# ---------------------------------------------------------------------------
# Statement kinds. For each kind: the ID letter, and for each qualifier the
# attributes it takes: key -> (type, required, repeatable).
# ---------------------------------------------------------------------------

Spec = tuple[Check, bool, bool]
REQUIRED: Final[bool] = True
OPTIONAL: Final[bool] = False
ONCE: Final[bool] = False
MANY: Final[bool] = True


def enum(*allowed: str) -> Check:
    def check(value: str) -> str | None:
        return None if value in allowed else " or ".join(f"`{a}`" for a in allowed)

    return check


_CLAIM_COMMON: Final[dict[str, Spec]] = {
    "holds-for": (check_text, REQUIRED, ONCE),
    "triggers": (check_ref, OPTIONAL, ONCE),
}

KINDS: Final[dict[str, tuple[str, dict[str, dict[str, Spec]]]]] = {
    # A fact. The qualifier is where the fact came from, because "am I answering
    # from the artifact, or from my memory of it?" is the question a reader
    # most needs answered and prose never does.
    "CLAIM": (
        "C",
        {
            "measured": {
                **_CLAIM_COMMON,
                "method": (check_text, REQUIRED, ONCE),
                "tool": (check_text, REQUIRED, ONCE),
                "result": (check_text, REQUIRED, ONCE),
                "examined": (check_examined, REQUIRED, ONCE),
                "missing": (check_text, OPTIONAL, ONCE),
            },
            "derived": {**_CLAIM_COMMON, "from": (check_cite_line, REQUIRED, MANY)},
            "cited": {**_CLAIM_COMMON, "anchor": (check_anchor, REQUIRED, MANY)},
            "operator": {
                **_CLAIM_COMMON,
                "by": (check_operator, REQUIRED, ONCE),
                "on": (check_date, REQUIRED, ONCE),
                "said": (check_text, REQUIRED, ONCE),
            },
            "asserted": {
                **_CLAIM_COMMON,
                "unverified-because": (check_text, REQUIRED, ONCE),
            },
        },
    ),
    # Anything that wants a reply. S-16: every question carries a target, and a
    # blocking one names what it breaks in the artifact under review (S-14).
    "QUESTION": (
        "Q",
        {
            "blocking": {
                "to": (check_party, REQUIRED, ONCE),
                "wants": (enum("answer", "change", "acceptance"), REQUIRED, ONCE),
                "breaks": (check_text, REQUIRED, ONCE),
            },
            "next-round": {
                "to": (check_party, REQUIRED, ONCE),
                "wants": (enum("answer", "change", "acceptance"), REQUIRED, ONCE),
            },
        },
    ),
    # A reply to exactly one QUESTION. `done` must say where it landed, because
    # "it was requested" and "it happened" are different claims.
    "ANSWER": (
        "A",
        {
            "yes": {
                "answers": (check_answer_target, REQUIRED, ONCE),
                "because": (check_refs, OPTIONAL, ONCE),
            },
            "no": {
                "answers": (check_answer_target, REQUIRED, ONCE),
                "because": (check_refs, OPTIONAL, ONCE),
            },
            "value": {
                "answers": (check_answer_target, REQUIRED, ONCE),
                "value": (check_text, REQUIRED, ONCE),
            },
            "accept": {"answers": (check_answer_target, REQUIRED, ONCE)},
            "amend": {
                "answers": (check_answer_target, REQUIRED, ONCE),
                "amended": (check_text, REQUIRED, ONCE),
            },
            "refuse": {
                "answers": (check_answer_target, REQUIRED, ONCE),
                "because": (check_refs, REQUIRED, ONCE),
            },
            "done": {
                "answers": (check_answer_target, REQUIRED, ONCE),
                "landed": (check_cite, REQUIRED, ONCE),
            },
            "queued": {
                "answers": (check_answer_target, REQUIRED, ONCE),
                "target": (check_text, REQUIRED, ONCE),
            },
            "cannot": {
                "answers": (check_answer_target, REQUIRED, ONCE),
                "because": (check_refs, REQUIRED, ONCE),
            },
            "withdrawn": {
                "answers": (check_answer_target, REQUIRED, ONCE),
                "because": (check_refs, OPTIONAL, ONCE),
            },
        },
    ),
    # A defect. The qualifier is its ORIGIN, settled before anything else,
    # because a defect put on the wrong side produces the wrong fix.
    "FINDING": (
        "F",
        {
            origin: {
                "in": (check_location, REQUIRED, ONCE),
                "shape": (check_text, REQUIRED, ONCE),
                "target": (enum("next-round", "blocking", "fixed"), REQUIRED, ONCE),
                "landed": (check_cite, OPTIONAL, ONCE),
                "witness": (check_ref, REQUIRED, ONCE),
                "breaks": (check_text, OPTIONAL, ONCE),
                "portable": (check_yes_no, OPTIONAL, ONCE),
            }
            for origin in ("ours", "yours", "upstream", "unknown")
        },
    ),
    # A change to a surface the other side reads: a log line, a flag, a field,
    # a shared file. `semantic` is a change of meaning with no change of text.
    "NOTICE": (
        "N",
        {
            q: {
                "surface": (check_text, REQUIRED, ONCE),
                "before": (check_text, REQUIRED, ONCE),
                "after": (check_text, REQUIRED, ONCE),
                "in": (check_text, REQUIRED, ONCE),
            }
            for q in ("breaking", "compatible", "semantic")
        },
    ),
    # A binding pre-commitment: "our next lap is GO unless X". The one mechanism
    # that has actually ended rounds, so it is checked when the lap is due.
    "PROMISE": (
        "P",
        {
            "verdict": {
                "due": (check_due, REQUIRED, ONCE),
                "verdict": (check_verdict, REQUIRED, ONCE),
                "unless": (check_text, REQUIRED, MANY),
            },
            "action": {
                "due": (check_due, REQUIRED, ONCE),
                "does": (check_text, REQUIRED, ONCE),
                "unless": (check_text, OPTIONAL, MANY),
            },
        },
    ),
    # A correction of a statement already sent. It needs the same witness a
    # claim does: a correction, or an apology, gets no less scrutiny.
    "ERRATUM": (
        "E",
        {
            q: {
                "corrects": (check_ref, REQUIRED, ONCE),
                "was": (check_text, REQUIRED, ONCE),
                "now": (check_text, REQUIRED, ONCE),
                "witness": (check_ref, REQUIRED, ONCE),
            }
            for q in ("ours", "yours")
        },
    ),
    # A close condition. Set in lap 1 and fixed there (S-13). Later laps only
    # report its state, and a GO needs every one met or waived.
    "TERM": (
        "T",
        {
            "set": {
                "requires": (check_text, REQUIRED, ONCE),
                "regression": (check_text, OPTIONAL, ONCE),
                "restates": (check_restates, OPTIONAL, ONCE),
            },
            "met": {
                "term": (check_ref, REQUIRED, ONCE),
                "witness": (check_refs, REQUIRED, ONCE),
            },
            "unmet": {
                "term": (check_ref, REQUIRED, ONCE),
                "because": (check_text, REQUIRED, ONCE),
            },
            "waived": {
                "term": (check_ref, REQUIRED, ONCE),
                "override": (check_text, REQUIRED, ONCE),
            },
            # "Our half is done; yours remains." A side may declare GO over a
            # term pending on the OTHER side, never over one pending on itself.
            # Round 27 lap 5 needed exactly this: our GO came one lap before
            # the fork's closing lap could name `.17`, which §0.3 required.
            "pending": {
                "term": (check_ref, REQUIRED, ONCE),
                "on": (check_party, REQUIRED, ONCE),
                "remains": (check_text, REQUIRED, ONCE),
            },
        },
    ),
}

#: Attributes every statement may carry: `re:` threads it to what it responds to.
COMMON_ATTRIBUTES: Final[dict[str, Spec]] = {"re": (check_refs, OPTIONAL, ONCE)}

#: Which ANSWER qualifiers can reply to which kind of QUESTION.
ANSWERS_FOR: Final[dict[str, frozenset[str]]] = {
    "answer": frozenset({"yes", "no", "value", "cannot"}),
    "change": frozenset({"done", "queued", "refuse", "cannot"}),
    "acceptance": frozenset({"accept", "amend", "refuse"}),
}

#: Evidence that can hold a verdict, a finding or a correction up. An asserted
#: claim is allowed to exist; it is not allowed to carry weight.
WEIGHT_BEARING: Final[frozenset[str]] = frozenset(
    {"measured", "derived", "cited", "operator"}
)

#: Every attribute that holds references, what it may point at, and whether it
#: holds one reference or a list. `CLAIM*` means a weight-bearing CLAIM.
#: ``None`` means any statement. TERM `unmet` has a `because` too, but there it is
#: text (the reason), so it is not a slot.
REF_SLOTS: Final[dict[str, tuple[str | None, bool]]] = {
    "answers": ("QUESTION", False),
    "corrects": (None, False),
    "term": ("TERM set", False),
    "triggers": ("PROMISE", False),
    "witness": ("CLAIM*", True),
    "because": ("CLAIM*", True),
    "re": (None, True),
}


def reference_slots(s: Statement) -> list[tuple[str, str, int]]:
    """Every (attribute, reference, line) a statement carries."""
    found: list[tuple[str, str, int]] = []
    for a in s.attributes:
        slot = REF_SLOTS.get(a.key)
        if slot is None or (a.key == "because" and s.kind == "TERM"):
            continue
        refs = a.value.split(", ") if slot[1] else [a.value]
        found.extend((a.key, ref, a.line) for ref in refs if REF.fullmatch(ref))
    return found


def slot_refuses(slot: str, target: Statement) -> str | None:
    """Why `target` cannot sit in `slot`, or None when it can."""
    want = REF_SLOTS[slot][0]
    if want is None:
        return None
    if want == "CLAIM*":
        if target.kind == "CLAIM" and target.qualifier in WEIGHT_BEARING:
            return None
        return "a measured, derived, cited or operator CLAIM"
    kind, _, qualifier = want.partition(" ")
    if target.kind == kind and (not qualifier or target.qualifier == qualifier):
        return None
    return f"a {want}"


def check_statement(s: Statement) -> list[Problem]:
    problems: list[Problem] = []
    entry = KINDS.get(s.kind)
    if entry is None:
        return [Problem("L21", s.line, f"{s.kind} is not a kind ({', '.join(KINDS)})")]
    letter, qualifiers = entry
    if not s.sid.startswith(letter):
        problems.append(
            Problem("L22", s.line, f"a {s.kind} is numbered {letter}<n>, not {s.sid}")
        )
    schema = qualifiers.get(s.qualifier)
    if schema is None:
        return problems + [
            Problem(
                "L23",
                s.line,
                f"{s.kind} takes {', '.join(qualifiers)}; not {s.qualifier}",
            )
        ]
    if not s.text:
        problems.append(
            Problem("L24", s.line, f"{s.sid} says nothing: a statement has text")
        )
    elif words(s.text) > MAX_STATEMENT_WORDS:
        problems.append(
            Problem(
                "L25",
                s.line,
                f"{s.sid} is {words(s.text)} words; at most {MAX_STATEMENT_WORDS} (split the point)",
            )
        )
    allowed = {**COMMON_ATTRIBUTES, **schema}
    counts: dict[str, int] = {}
    for a in s.attributes:
        spec = allowed.get(a.key)
        if spec is None:
            problems.append(
                Problem(
                    "L26", a.line, f"{s.sid}: {s.kind} {s.qualifier} takes no `{a.key}`"
                )
            )
            continue
        counts[a.key] = counts.get(a.key, 0) + 1
        check, _required, repeatable = spec
        if counts[a.key] > 1 and not repeatable:
            problems.append(Problem("L27", a.line, f"{s.sid}: `{a.key}` given twice"))
        why = check(a.value)
        if why is not None:
            problems.append(Problem("L28", a.line, f"{s.sid}: `{a.key}` must be {why}"))
    for key, (_check, required, _many) in schema.items():
        if required and key not in counts:
            problems.append(
                Problem("L29", s.line, f"{s.sid}: {s.kind} {s.qualifier} needs `{key}`")
            )
    # Requirements that depend on another attribute's value.
    if s.kind == "FINDING":
        if s.value("target") == "blocking" and s.value("breaks") is None:
            problems.append(
                Problem(
                    "L30",
                    s.line,
                    f"{s.sid}: a blocking finding names what it breaks (S-14)",
                )
            )
        if s.value("target") == "fixed" and s.value("landed") is None:
            problems.append(
                Problem(
                    "L33",
                    s.line,
                    f"{s.sid}: a fixed finding names the commit it `landed` in",
                )
            )
        if s.qualifier == "ours" and s.value("portable") is None:
            problems.append(
                Problem(
                    "L31",
                    s.line,
                    f"{s.sid}: a finding in our own code says whether its shape is portable "
                    "(rule #12: a fix that could help them is sent)",
                )
            )
    if s.kind == "CLAIM" and s.qualifier == "measured":
        examined = s.value("examined") or ""
        if examined.endswith(", open") and s.value("missing") is None:
            problems.append(
                Problem(
                    "L32",
                    s.line,
                    f"{s.sid}: an open population names what is `missing`",
                )
            )
    return problems
