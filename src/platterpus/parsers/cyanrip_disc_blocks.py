"""Two disc-level blocks the fork's `.28` adds to the log, read without a lazy regex.

Round 37 lap 1 of the cyanrip fork (`docs/handshake/inbound/round-37-lap-01.md`)
proposed both before building them, so our reader takes them before `.28` ships:

* **`Pregap searches:`** (their S5, built at `cyanrip@14f9298:src/cyanrip_main.c:2409-2443`).
  After `Gaps:` and its blank line, one line per track a sub-channel search ran
  on, ripped or not: ``    track N: <that track's Pregap search: record>``. It
  exists because round 36's Full run listed track 9's pregap as ``unknown`` in 21
  logs that did not rip track 9, with no line saying why (their round 36 lap 16
  S10).
* **`Names shortened:`** (their S7). One line per path component a tag value made
  longer than 255 bytes, which the fork shortened to fit, as our round 36 lap 13
  S4 asked: ``    <what>: <name as written> (<N> bytes as rendered)``, where
  ``<what>`` is ``folder``, ``track N, <format>``, ``cue sheet`` or ``log``.

Each block is a header at column 0, indented lines, then a blank line. The loop
in `cyanrip_log` recognises the header and hands each indented line here. The
values are read with string operations, as `cyanrip_preemphasis` reads its row:
a name may itself contain ``": "`` and parentheses, and the record is free text,
so a split from the right on the fixed suffix is both exact and linear. The
patterns below only RECOGNISE a line, for the tables that publish our consumer
contract and classify real-log lines; they capture nothing open-ended.

Never raises: a line that does not fit returns None and the block ends there, so
the line is still offered to every other rule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

#: The `Pregap searches:` header, column 0.
PREGAP_SEARCHES_HEADER: Final[re.Pattern[str]] = re.compile(r"^Pregap searches:\s*$")

#: One line of that block: four spaces, ``track N:``, a space, the record.
PREGAP_SEARCHES_LINE: Final[re.Pattern[str]] = re.compile(r"^ {4}track \d{1,3}: \S")

#: The `Names shortened:` header, column 0.
NAMES_SHORTENED_HEADER: Final[re.Pattern[str]] = re.compile(r"^Names shortened:\s*$")

#: One line of that block, recognised by its four kinds of ``<what>``. A track's
#: format is a word as `Outputs:` names it (``flac``, ``mp3``, ``wavpack``...).
NAMES_SHORTENED_LINE: Final[re.Pattern[str]] = re.compile(
    r"^ {4}(?:folder|track \d{1,3}, [a-z0-9_]{1,16}|cue sheet|log): \S"
)

#: The fixed tail of a `Names shortened:` line, after the name.
_RENDERED_SUFFIX: Final[str] = " bytes as rendered)"

#: A rendered length is at most a few kilobytes; more digits than this is not a
#: length we believe, so the line is "not recognised" rather than a huge number.
_MAX_BYTES_DIGITS: Final[int] = 6


@dataclass(frozen=True)
class ShortenedName:
    """One path component the ripper shortened to 255 bytes.

    ``what`` is the ripper's own label (``folder``, ``track 3, flac``,
    ``cue sheet``, ``log``), ``name`` the component as written to the disc, and
    ``rendered_bytes`` the length it would have had.
    """

    what: str
    name: str
    rendered_bytes: int


def parse_pregap_search_line(line: str) -> tuple[int, str] | None:
    """``(track, record)`` from one `Pregap searches:` line, or None."""
    if not PREGAP_SEARCHES_LINE.match(line):
        return None
    head, _, record = line[4:].partition(": ")
    record = record.strip()
    try:
        track = int(head.removeprefix("track "))
    except ValueError:
        return None
    return (track, record) if record else None


def parse_shortened_name_line(line: str) -> ShortenedName | None:
    """One `Names shortened:` line as a :class:`ShortenedName`, or None.

    Split from the right: the line ends ``(<N> bytes as rendered)``, and the
    name before it may contain anything, ``": "`` and parentheses included.
    """
    if not NAMES_SHORTENED_LINE.match(line):
        return None
    body = line[4:].rstrip()
    if not body.endswith(_RENDERED_SUFFIX):
        return None
    rest, _, count = body[: -len(_RENDERED_SUFFIX)].rpartition(" (")
    # ASCII digits only: `str.isdigit` also passes `²`, which `int` refuses.
    if not rest or not (count.isascii() and count.isdigit()):
        return None
    if len(count) > _MAX_BYTES_DIGITS:
        return None
    # The label never contains ": ", so the first one ends it.
    what, _, name = rest.partition(": ")
    if not name:
        return None
    return ShortenedName(what=what, name=name, rendered_bytes=int(count))
