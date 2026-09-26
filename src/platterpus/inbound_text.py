"""Screen text a dependency sends us before we store it or show it.

**The rule this implements.** Critical rule #12, the inbound half: the ripper's
output is external input. Control characters and NULs are flagged, absurdly long
lines are bounded, everything else is kept verbatim, and anything elided is
counted and marked. A silent drop reads as completeness. Until 2026-09-25 the rule
said this and no code did it (found by the TASKS audit that day). The only bound
on ripper output was a count of lines, in ``workers/rip_worker.py``.

**Why each part matters here.**

* **Control characters.** A NUL, an escape sequence or a stray backspace from
  the ripper (or from a disc's CD-TEXT it echoes) is invisible in the log pane
  and in the report, so text looks intact when it is not. Each one becomes a
  visible ``\\xNN`` escape, so a reader sees that it was there and what it was.
  Tab is kept: it is ordinary layout.
* **Line length.** One multi-megabyte line freezes the GUI thread that lays it
  out. A line longer than :data:`MAX_LINE_CHARS` keeps its head and its tail,
  because a tool's last words are where its error is, and says how much of the
  middle was dropped.
* **Undecodable bytes.** Readers open the pipe with ``errors="replace"``, so a
  byte that is not UTF-8 arrives as U+FFFD instead of raising and ending the
  read. They are counted here, so the substitution is reported rather than
  silent.

**Display and storage only.** Parsers read the raw line, so what they match is
exactly what the ripper wrote. This module decides what a person sees, not what
the program concludes. Pure, and never raises.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

#: The longest line kept whole. The longest line in any ripper log committed here
#: is 1,601 characters (an ``Invoked as:`` line, 2026-09-25). A 99-track disc's
#: would be about ten thousand. This bound is far above both and far below the
#: multi-megabyte line that freezes a text widget.
MAX_LINE_CHARS: Final[int] = 65_536

#: Stands in for the middle of an over-long line. Styled like the rip worker's
#: line-count elision marker, so both read as ours.
ELISION_MARK: Final[str] = (
    "[platterpus] … {count} characters of this line elided here …"
)

#: Characters shown as escapes: C0 controls except tab, DEL, C1 controls, and the
#: two Unicode line and paragraph separators, which a text widget treats as a
#: line break the text never had. ``\n`` and ``\r`` cannot reach here in a line:
#: text-mode pipes split on both.
_FLAGGED: Final[re.Pattern[str]] = re.compile(
    "[\x00-\x08\x0a-\x1f\x7f-\x9f\u2028\u2029]"
)

_REPLACEMENT: Final[str] = "\ufffd"


def _escape(match: re.Match[str]) -> str:
    code = ord(match.group(0))
    return f"\\x{code:02x}" if code <= 0xFF else f"\\u{code:04x}"


@dataclass(frozen=True)
class Screened:
    """One screened line or text, and what screening changed in it."""

    text: str
    control_chars: int = 0
    undecodable: int = 0
    elided_chars: int = 0

    @property
    def flagged(self) -> bool:
        """Whether screening changed or had to report anything."""
        return bool(self.control_chars or self.undecodable or self.elided_chars)


def screen_line(line: str) -> Screened:
    """Screen one line of dependency output. Never raises.

    Bounds the length first, so a line made of control characters cannot be
    expanded fourfold by escaping before it is bounded.
    """
    elided = 0
    if len(line) > MAX_LINE_CHARS:
        keep = MAX_LINE_CHARS // 2
        elided = len(line) - 2 * keep
        line = line[:keep] + ELISION_MARK.format(count=elided) + line[-keep:]
    text, controls = _FLAGGED.subn(_escape, line)
    return Screened(
        text=text,
        control_chars=controls,
        undecodable=text.count(_REPLACEMENT),
        elided_chars=elided,
    )


def screen_text(text: str) -> Screened:
    """Screen a block of output line by line, keeping its line structure."""
    screened = [screen_line(line) for line in text.split("\n")]
    return Screened(
        text="\n".join(s.text for s in screened),
        control_chars=sum(s.control_chars for s in screened),
        undecodable=sum(s.undecodable for s in screened),
        elided_chars=sum(s.elided_chars for s in screened),
    )


@dataclass
class Tally:
    """Running totals over a stream of screened lines, e.g. one rip."""

    control_chars: int = 0
    undecodable: int = 0
    elided_chars: int = 0
    lines_flagged: int = 0

    def add(self, screened: Screened) -> None:
        self.control_chars += screened.control_chars
        self.undecodable += screened.undecodable
        self.elided_chars += screened.elided_chars
        self.lines_flagged += 1 if screened.flagged else 0

    def note(self) -> str:
        """One line saying what screening changed, or ``""`` if it changed nothing.

        Appended to a captured stream so its reader knows the text was screened
        and how, instead of mistaking an escape for something the tool printed.
        """
        if not self.lines_flagged:
            return ""
        parts = []
        if self.control_chars:
            parts.append(
                f"{self.control_chars} control character(s) shown as \\x escapes"
            )
        if self.undecodable:
            parts.append(
                f"{self.undecodable} byte(s) that were not UTF-8 shown as \ufffd"
            )
        if self.elided_chars:
            parts.append(
                f"{self.elided_chars} character(s) elided from over-long line(s)"
            )
        return (
            f"[platterpus] {self.lines_flagged} line(s) of this output were screened: "
            + "; ".join(parts)
        )
