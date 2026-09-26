"""Reading a lap, and the rules that hold inside one lap."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

from .header import (
    HEADER_REF_KINDS,
    HEADER_TYPES,
    LANGUAGE_FIELD,
    UNPREFIXED_FIELDS,
    check_header,
)
from .kinds import check_statement, reference_slots, slot_refuses
from .model import Attribute, Lap, Problem, Statement
from .values import REF, check_refs, check_refs_or_none

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_FIELD_LINE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<key>HANDSHAKE-[A-Z0-9-]+|"
    + "|".join(sorted(UNPREFIXED_FIELDS))
    + r"):[ \t]*(?P<value>.*?)[ \t]*$"
)
_HEAD: Final[re.Pattern[str]] = re.compile(
    r"^#### (?P<sid>[A-Z][1-9][0-9]{0,2}) (?P<kind>[A-Z]+) (?P<qual>[a-z][a-z-]*)$"
)
_SECTION: Final[re.Pattern[str]] = re.compile(r"^#{1,3} \S")
_ATTR: Final[re.Pattern[str]] = re.compile(
    r"^- (?P<key>[a-z][a-z-]*): (?P<value>\S.*?)[ \t]*$"
)
_FENCE: Final[re.Pattern[str]] = re.compile(r"^[ \t]*(?P<mark>```|~~~)")


@dataclass
class _Draft:
    sid: str
    kind: str
    qualifier: str
    line: int
    text: list[str] = field(default_factory=list)
    attributes: list[Attribute] = field(default_factory=list)


def parse_lap(text: str, name: str = "<lap>") -> Lap:
    """Parse one lap. Never raises: every defect is a Problem in the result.

    There is deliberately no catch-all here. A broad `except` would turn a bug in
    this module into a quiet "problem" in someone's lap; the guarantee is instead
    `tests/test_lap_language.py`'s property test, which feeds it arbitrary text.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    problems: list[Problem] = []
    header: list[tuple[str, str, int]] = []

    index = 0
    while index < len(lines):
        m = _FIELD_LINE.match(lines[index])
        if m is None:
            break
        header.append((m.group("key"), m.group("value"), index + 1))
        index += 1
    uses_language = any(k == LANGUAGE_FIELD for k, _v, _l in header)
    if not uses_language:
        # Not a language-1 lap. Its header is still returned, so a round can be
        # checked around it, but its body is prose under v6 and is not judged.
        return Lap(name, tuple(header), (), (), False)

    problems.extend(check_header(header))
    if index < len(lines) and lines[index].strip():
        problems.append(Problem("L2", index + 1, "the header ends at a blank line"))

    statements: list[Statement] = []
    current: _Draft | None = None
    fence: str | None = None
    prose_run = False

    def close() -> None:
        nonlocal current
        if current is not None:
            statements.append(
                Statement(
                    current.sid,
                    current.kind,
                    current.qualifier,
                    "\n".join(current.text).strip(),
                    tuple(current.attributes),
                    current.line,
                )
            )
        current = None

    for number, line in enumerate(lines[index:], start=index + 1):
        if fence is not None:
            if line.strip().startswith(fence):
                fence = None
            continue
        opened = _FENCE.match(line)
        if opened:
            fence = opened.group("mark")
            if current is None:
                problems.append(
                    Problem("L3", number, "a fenced block outside a statement")
                )
            elif current.attributes:
                problems.append(
                    Problem("L4", number, "text after a statement's attributes")
                )
            else:
                current.text.append("")  # a quotation is part of the text, not counted
            continue
        if not line.strip():
            prose_run = False
            continue
        if _FIELD_LINE.match(line):
            problems.append(Problem("L1", number, "a header field outside the header"))
            continue
        if line.startswith("#"):
            close()
            prose_run = False
            head = _HEAD.match(line)
            if head:
                current = _Draft(
                    head.group("sid"), head.group("kind"), head.group("qual"), number
                )
            elif line.startswith("#### ") or re.match(r"^#{4,6}(?: |$)", line):
                problems.append(
                    Problem(
                        "L5",
                        number,
                        "a level-4 heading is a statement: `#### <ID> <KIND> <qualifier>`",
                    )
                )
            elif not _SECTION.match(line):
                problems.append(Problem("L6", number, "prose outside a statement"))
            continue
        if current is None:
            if not prose_run:
                problems.append(Problem("L6", number, "prose outside a statement"))
            prose_run = True
            continue
        attr = _ATTR.match(line)
        if attr:
            current.attributes.append(
                Attribute(attr.group("key"), attr.group("value"), number)
            )
        elif line.startswith("- ") or line.startswith("* "):
            problems.append(
                Problem("L7", number, "an attribute is `- key: value`, one per line")
            )
        elif current.attributes:
            problems.append(
                Problem("L4", number, "text after a statement's attributes")
            )
        else:
            current.text.append(line)
    close()
    if fence is not None:
        problems.append(Problem("L3", len(lines), "a fenced block that never closes"))

    lap = Lap(name, tuple(header), tuple(statements), (), True)
    problems.extend(_check_statements(lap))
    return Lap(name, lap.header, lap.statements, tuple(problems), True)


def _check_statements(lap: Lap) -> list[Problem]:
    problems: list[Problem] = []
    by_id: dict[str, Statement] = {}
    for s in lap.statements:
        problems.extend(check_statement(s))
        if s.sid in by_id:
            problems.append(
                Problem("L13", s.line, f"{s.sid} is used twice in this lap")
            )
        by_id.setdefault(s.sid, s)

    def local(ref: str, line: int, *, what: str) -> Statement | None:
        m = REF.fullmatch(ref)
        if m is None or m.group("round") is not None:
            return None
        target = by_id.get(m.group("sid"))
        if target is None:
            problems.append(
                Problem(
                    "L14", line, f"{what} names {ref}, which this lap does not contain"
                )
            )
        return target

    # References from the header resolve inside the lap, and some fields say
    # what kind of statement they must point at.
    for field_name, value, line in lap.header:
        is_refs = HEADER_TYPES.get(field_name) in (check_refs, check_refs_or_none)
        if not is_refs or value == "none" or check_refs(value) is not None:
            continue
        allowed = HEADER_REF_KINDS.get(field_name)
        for ref in value.split(", "):
            if not ref.startswith("#"):
                problems.append(
                    Problem(
                        "L15",
                        line,
                        f"{field_name} references this lap's own statements only",
                    )
                )
                continue
            target = local(ref, line, what=field_name)
            if (
                target is not None
                and allowed is not None
                and not any(
                    target.kind == k and (q is None or target.qualifier == q)
                    for k, q in allowed
                )
            ):
                kinds = ", ".join(
                    f"{k} {q}" if q else k for k, q in sorted(allowed, key=str)
                )
                problems.append(
                    Problem(
                        "L16",
                        line,
                        f"{field_name} must point at {kinds}; {ref} is {target.kind} {target.qualifier}",
                    )
                )

    # References between statements of this lap resolve, and each slot takes
    # only what it is for: a witness is never an asserted claim.
    for s in lap.statements:
        for slot, ref, line in reference_slots(s):
            if not ref.startswith("#"):
                continue  # into another lap: check_round resolves it
            target = local(ref, line, what=f"{s.sid} {slot}")
            if target is None:
                continue
            why = slot_refuses(slot, target)
            if why is not None:
                problems.append(
                    Problem(
                        "L17",
                        line,
                        f"{s.sid} {slot} must be {why}; {ref} is {target.kind} {target.qualifier}",
                    )
                )

    # Rules that need the lap's own header.
    author = lap.author
    number = lap.lap
    verdict = lap.field("HANDSHAKE-VERDICT")
    for s in lap.statements:
        if s.kind == "QUESTION" and author is not None and s.value("to") == author:
            problems.append(
                Problem("L18", s.line, f"{s.sid} is addressed to its own author")
            )
        if (
            s.kind == "TERM"
            and s.qualifier == "set"
            and number not in (None, 1)
            and s.value("regression") is None
            and s.value("restates") is None
        ):
            problems.append(
                Problem(
                    "L19",
                    s.line,
                    f"{s.sid}: close conditions are fixed in lap 1 (S-13); a later one "
                    "either restates a lap-1 condition (`restates`) or names the "
                    "regression in the pin under review (`regression`)",
                )
            )
    if verdict == "GO":
        for key in ("HANDSHAKE-VERDICT-SOURCE", "HANDSHAKE-TESTED"):
            if lap.field(key) is None:
                problems.append(Problem("L20", 1, f"a GO lap declares {key}"))
    return problems
