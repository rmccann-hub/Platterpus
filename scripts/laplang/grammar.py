"""Read an LSL lap into headers and statements. Syntax only; meaning is `check`'s.

Written from the fork's spec (`PROPOSAL-lap-statement-language.md`, §"Syntax"),
not from their checker, because two checkers written from one spec that agree
are evidence and one checker copied into two trees is not (`CLAUDE.md` rule #12).

The file, as the spec lays it out:

* Everything before a line reading exactly `LSL: 1` is the wire headers and a
  title. `PROTOCOL.md` governs those, and this language does not touch them. The
  `HANDSHAKE-*` lines are collected here only so the checks can read who wrote
  the lap, its round and lap, and its declared verdict.
* After that line come statements. A statement is a head,
  `S<n> <KIND>[ <grade>]: <one sentence>`, followed directly by fields,
  `  <name>: <value>`, each indented two spaces. A value continues on lines
  indented four spaces.
* A blank line or a `## ` heading ends the statement above it, so a field after
  one is refused: it would otherwise attach to whichever statement came last.
* Any other line is refused. Prose goes in a NOTE.

Parsing never raises (`CLAUDE.md`: parsers of external output never raise). The
fork's laps are external input, so anything wrong comes back as a problem.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from .model import Field, Lap, Statement

#: The one line that starts an LSL body. Any other `LSL:` value is a version this
#: checker does not implement, which is "cannot check", not "refused".
LSL_LINE: Final[str] = "LSL: 1"

HEAD_RE: Final[re.Pattern[str]] = re.compile(
    r"^S(?P<n>\d+) (?P<kind>[A-Z]+)(?: (?P<grade>[a-z]+))?: (?P<sentence>\S.*)$"
)
#: Field names are lowercase letters only. The spec says "lowercase"; a hyphen or
#: a digit in a name makes the line fail as a field and fall through to "any
#: other line", which is what the fork's checker does with `holds-for:`
#: (measured 2026-09-26).
FIELD_RE: Final[re.Pattern[str]] = re.compile(r"^  (?P<name>[a-z]+): (?P<value>\S.*)$")
CONTINUATION_RE: Final[re.Pattern[str]] = re.compile(r"^    (?P<text>\S.*)$")
WIRE_RE: Final[re.Pattern[str]] = re.compile(
    r"^HANDSHAKE-(?P<name>[A-Z0-9-]+): ?(?P<value>.*)$"
)


def parse_lap(text: str, path: Path) -> Lap:
    """Parse `text` (the contents of `path`). Never raises."""
    lap = Lap(path=path, text=text)
    lines = text.splitlines()
    start = _read_headers(lap, lines)
    if start is None:
        return lap
    lap.lsl = True
    _read_statements(lap, lines, start)
    return lap


def read_lap(path: Path) -> Lap:
    """Read and parse a lap file. An unreadable file is a lap that cannot be checked."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        lap = Lap(path=path, text="")
        lap.add(0, "CANNOT", "LSL.file", f"cannot read {path.name}: {exc}")
        return lap
    return parse_lap(text, path)


def _read_headers(lap: Lap, lines: list[str]) -> int | None:
    """Collect the wire headers; return the index of the first body line, if LSL.

    Header lines inside a fenced block are quotations, not headers (the protocol
    strips fences before matching for the same reason).
    """
    fenced = False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = WIRE_RE.match(line)
        if match:
            lap.headers.setdefault(match["name"], []).append(match["value"])
            continue
        stripped = line.rstrip()
        if stripped.startswith("LSL:"):
            if stripped != LSL_LINE:
                lap.add(
                    i + 1,
                    "CANNOT",
                    "LSL.version",
                    f"declares {stripped!r}; this checker implements LSL 1 only",
                )
                return None
            return i + 1
    return None


def _read_statements(lap: Lap, lines: list[str], start: int) -> None:
    current: Statement | None = None
    open_field: Field | None = None
    for i in range(start, len(lines)):
        number, line = i + 1, lines[i]
        if not line.strip() or line.startswith("## "):
            current = None
            open_field = None
            continue
        head = HEAD_RE.match(line)
        if head:
            current = Statement(
                n=int(head["n"]),
                kind=head["kind"],
                grade=head["grade"],
                sentence=head["sentence"].strip(),
                line=number,
            )
            lap.statements.append(current)
            open_field = None
            continue
        field_match = FIELD_RE.match(line)
        if field_match:
            if current is None:
                lap.add(
                    number,
                    "REFUSED",
                    "LSL.syntax",
                    "a field after a blank line or a heading belongs to no statement",
                )
                continue
            open_field = Field(
                field_match["name"], field_match["value"].strip(), number
            )
            current.fields.append(open_field)
            continue
        continuation = CONTINUATION_RE.match(line)
        if continuation and open_field is not None:
            open_field.value += " " + continuation["text"].strip()
            continue
        lap.add(
            number,
            "REFUSED",
            "LSL.syntax",
            "not a statement, a field, a continuation or a heading; prose goes in "
            f"a NOTE: {line.strip()[:60]!r}",
        )
