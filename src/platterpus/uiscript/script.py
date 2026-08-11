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


def sanitise_cyanrip_args(args: list[str]) -> str | None:
    """Refuse a scripted cyanrip argv that would be unsafe or unattended-hostile.

    Returns a human-readable reason, or ``None`` when the argv may run.

    **Why this exists at all.** The application's own rip argv passes through
    :func:`platterpus.adapters.cyanrip_backend.assert_metadata_lookup_disabled` —
    one chokepoint, which refuses any argv lacking ``-N``. A scripted
    ``cyanrip …`` verb is a **straight passthrough that bypasses it**, so the
    protection has to be re-established here or the script surface is a hole in a
    rule the rest of the codebase enforces. (Found by the maintainer asking the
    right architectural question: *"does all pass through platterpus to cyanrip
    (filtered), or do any do a straight pass to cyanrip bypassing platterpus?"*
    The answer was the second one, and the verb as first written was a bug.)

    Three checks, each for a named failure:

    1. **A rip invocation must carry ``-N``**, delegating the judgement to the
       real chokepoint rather than restating its rule — a second copy of a
       safety check is a second thing to drift. Probe invocations
       (:data:`~platterpus.uiscript.verbs.PROBE_FLAGS`) are exempt because they
       never reach the metadata path.
    2. **No argument may contain a newline or a NUL.** We never use a shell, so
       this is not injection — it is *log forgery*: cyanrip writes its argv into
       an archival log, and a newline could fabricate a second line in a document
       whose whole purpose is being trustworthy evidence.
    3. **Bounded count and length**, so a paste accident cannot build a
       multi-megabyte command line.
    """
    # `RipError` comes from `rip_backend` (the ABC that defines it), not from
    # `cyanrip_backend` which merely re-exports it. Importing it from the
    # re-exporter is what mypy's no-implicit-reexport flags, and it is right to:
    # the chokepoint is a cyanrip concern, the exception type is the backend
    # contract, and taking each from its own home keeps that distinction visible.
    from platterpus.adapters.cyanrip_backend import assert_metadata_lookup_disabled
    from platterpus.adapters.rip_backend import RipError
    from platterpus.uiscript.verbs import PROBE_FLAGS

    if len(args) > 64:
        return f"{len(args)} arguments is not a command line; the limit is 64"
    for arg in args:
        if len(arg) > 4000:
            return f"an argument is {len(arg)} characters; the limit is 4000"
        if "\n" in arg or "\r" in arg or "\x00" in arg:
            return (
                f"refusing an argument containing a newline or NUL: {arg!r} — "
                "cyanrip writes its argv into an archival log, and a newline "
                "could forge a second line in it"
            )

    # ALL, not ANY. `any` made one probe flag anywhere exempt the WHOLE command
    # line, so `cyanrip -v -d /dev/sr0 -o flac` was waved through as "a probe" —
    # a full rip of the inserted disc with MusicBrainz lookup enabled, which is
    # the unattended interactive-prompt hang this function exists to prevent.
    # A probe is a property of the entire argv: every argument must be one.
    if args and all(arg in PROBE_FLAGS for arg in args):
        return None  # a probe: prints and exits, never looks up metadata

    try:
        assert_metadata_lookup_disabled(["cyanrip", *args])
    except RipError as exc:
        return str(exc)
    return None
