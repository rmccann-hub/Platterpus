"""The parser: script text in, a list of steps out, and it never raises.

A script is **external input** — pasted by a human, or copied out of a chat
window with whatever quoting survived the trip. ``CLAUDE.md``'s rule applies
literally: *validate every input, visibly, and to the log*. So a malformed line
does not raise and does not get silently skipped; it becomes a :class:`Step` that
carries its own error, keeps its line number, and renders in the transcript as a
reported failure at the line the user can see. A parser that throws on line 12 of
a 60-line batch destroys the other 59 results, which for an unattended run is the
whole session.

**Quoting.** Values routinely contain spaces and em dashes
(``FLAC — Lossless Archival Master [Recommended]``), so double quotes group a
value. Everything else is whitespace-split. An unterminated quote is reported
against its line rather than swallowing the rest of the file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from platterpus.uiscript.verbs import VERBS, Verb

#: Longest script we will parse, in lines. A pasted script is human-written; a
#: hundred thousand lines is a paste accident or a stress attempt, and either way
#: the honest response is to say so rather than to spend a minute parsing it.
MAX_LINES: int = 2000

#: Longest single line. Same reasoning; also bounds the tokeniser's work.
MAX_LINE_CHARS: int = 4000

#: Matches a double-quoted run (allowing an escaped quote) or a bare word.
#: Bounded quantifiers per the project's regex rule — an unbounded `[^"]*` inside
#: an alternation is the classic backtracking shape, and this file parses
#: attacker-shaped input by construction.
_TOKEN = re.compile(r'"((?:[^"\\]|\\.){0,4000})"|(\S{1,4000})')


@dataclass(frozen=True)
class Step:
    """One parsed line, valid or not.

    An invalid step is still a step: it holds its ``line_no`` and its ``error``
    so the transcript can point at the line the user typed. ``verb`` is empty
    when the line could not be resolved to one.
    """

    line_no: int
    source: str
    verb: str = ""
    args: tuple[str, ...] = field(default_factory=tuple)
    error: str = ""

    @property
    def ok(self) -> bool:
        """True when this step can be executed."""
        return not self.error and bool(self.verb)

    @property
    def spec(self) -> Verb | None:
        """The vocabulary entry, or ``None`` for an unparsed line."""
        return VERBS.get(self.verb)

    @property
    def unsafe(self) -> bool:
        """True when this step needs the escape-hatch opt-in."""
        spec = self.spec
        return spec is not None and spec.unsafe

    def joined(self, start: int = 0) -> str:
        """Arguments from ``start`` re-joined with single spaces.

        For the free-text tails (``log``, ``eval``, ``album``) where the split
        into tokens was only ever a parsing detail.
        """
        return " ".join(self.args[start:])


def _tokenise(text: str) -> tuple[list[str], str]:
    """Split one line into tokens. Returns ``(tokens, error)``.

    Never raises. An unterminated quote is an error string, not an exception,
    because it must be attributed to its own line.
    """
    if text.count('"') % 2:
        return [], "unterminated quote"
    tokens: list[str] = []
    for match in _TOKEN.finditer(text):
        quoted, bare = match.group(1), match.group(2)
        if quoted is not None:
            tokens.append(quoted.replace('\\"', '"').replace("\\\\", "\\"))
        elif bare is not None:
            tokens.append(bare)
    return tokens, ""


def _strip_comment(line: str) -> str:
    """Remove a trailing ``#`` comment, respecting quotes.

    A naive ``line.split("#")`` would cut a value containing a hash — and album
    titles do (``"Greatest Hits #2"``), which is exactly the sort of value this
    language is used to set.
    """
    in_quote = False
    for index, char in enumerate(line):
        if char == '"':
            in_quote = not in_quote
        elif char == "#" and not in_quote:
            return line[:index]
    return line


def parse(text: str) -> list[Step]:
    """Parse a whole script. Never raises.

    Blank lines and comment-only lines produce no step — they are formatting, and
    a transcript full of "line 4: blank, OK" helps nobody. Everything else
    produces exactly one step, valid or not, so the transcript's step count
    matches the user's mental model of "commands I wrote".
    """
    steps: list[Step] = []
    lines = text.splitlines()
    truncated = len(lines) > MAX_LINES
    for number, raw in enumerate(lines[:MAX_LINES], start=1):
        if len(raw) > MAX_LINE_CHARS:
            steps.append(
                Step(
                    number,
                    raw[:120] + "…",
                    error=f"line is {len(raw)} characters; the limit is "
                    f"{MAX_LINE_CHARS}",
                )
            )
            continue
        body = _strip_comment(raw).strip()
        if not body:
            continue
        tokens, error = _tokenise(body)
        if error:
            steps.append(Step(number, body, error=error))
            continue
        if not tokens:
            continue
        name = tokens[0].lower()
        spec = VERBS.get(name)
        if spec is None:
            steps.append(
                Step(
                    number,
                    body,
                    error=f"unknown command '{tokens[0]}' — see the reference below",
                )
            )
            continue
        args = tuple(tokens[1:])
        arity = spec.arity_problem(len(args))
        if arity:
            steps.append(Step(number, body, verb=name, args=args, error=arity))
            continue
        steps.append(Step(number, body, verb=name, args=args))
    if truncated:
        steps.append(
            Step(
                MAX_LINES + 1,
                "(rest of script)",
                error=f"script is longer than {MAX_LINES} lines; the rest was "
                "not parsed",
            )
        )
    return steps


def uses_unsafe(steps: list[Step]) -> bool:
    """True when any step needs the escape hatch.

    Asked *before* a run starts, so the console can refuse the whole batch with
    one clear message instead of failing at line 40 of 60 — an unattended run
    that dies two-thirds through is worse than one that never started.
    """
    return any(step.unsafe for step in steps)
