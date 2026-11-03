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


# --- Progress lines, folded before a capture is stored -------------------------
#
# **Why** (the 2026-11-03 Full run on 0.7.117, section P3). cyanrip redraws its
# progress line in place, ``\r`` then ``Ripping track 1, progress - 12.34%, ETA``
# (``cyanrip@239adda:src/cyanrip_main.c:1199-1212``, ``crip_progress_report``),
# once per frame read. A one-track rip printed about 898 KB of them, and the
# script transcript's head-and-tail bound then kept the banner and the last few
# kilobytes and cut the track block, CRC and loudness, out of the middle. The
# step's result was lost to its own progress bar.
#
# What a terminal would show is the last state of each redraw, so that is what is
# kept: the last update of each run, preceded by a marker that says how many
# earlier updates were folded into it. Nothing is dropped silently.
#
# A text-mode pipe turns every ``\r`` into a line break, so the redraws usually
# arrive as separate lines; a raw ``\r`` inside one line (a binary-mode capture)
# is folded the same way. A run is consecutive progress lines with the same text
# before the number, so track 1's updates never fold into track 2's.

#: One progress update: anything, then ``progress - <number>%``. Named groups, and
#: bounded, because this reads external output (CLAUDE.md: parsers never raise).
_PROGRESS_LINE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<head>.{0,200}?\bprogress - )(?P<pct>\d{1,3}(?:\.\d{1,4})?)%"
)

#: Put before the update a run was folded into. Styled like :data:`ELISION_MARK`.
FOLD_MARK: Final[str] = (
    "[platterpus] … {count} earlier redraw(s) of the line below folded into it …"
)


@dataclass(frozen=True)
class Folded:
    """Output with its progress redraws folded, and how many were folded."""

    text: str
    folded: int = 0


def _progress_key(line: str) -> str | None:
    """The text before a progress line's number, or ``None`` for any other line."""
    match = _PROGRESS_LINE.match(line)
    return match.group("head") if match else None


def fold_progress(text: str) -> Folded:
    """Fold each run of progress redraws to its last update, counted and marked.

    Never raises; text with no progress lines comes back unchanged. Apply it
    BEFORE :func:`screen_text`, which would otherwise show a raw ``\\r`` as an
    escape rather than as the redraw it is.
    """
    out: list[str] = []
    folded = 0
    run_key: str | None = None
    run_count = 0
    run_last = ""

    def close_run() -> None:
        nonlocal run_key, run_count
        if run_key is None:
            return
        if run_count > 1:
            out.append(FOLD_MARK.format(count=run_count - 1))
        out.append(run_last)
        run_key, run_count = None, 0

    for raw in text.split("\n"):
        # A redraw inside one line: what a terminal shows is the last non-empty
        # segment, and each earlier one is a folded update.
        segments = [s for s in raw.split("\r") if s]
        line = segments[-1] if segments else ""
        inline = max(len(segments) - 1, 0)
        key = _progress_key(line)
        if key is not None and key == run_key:
            run_count += 1 + inline
            folded += 1 + inline
            run_last = line
            continue
        close_run()
        if key is not None:
            run_key, run_count, run_last = key, 1 + inline, line
            folded += inline
            continue
        if inline:
            out.append(FOLD_MARK.format(count=inline))
            folded += inline
        out.append(line)
    close_run()
    return Folded(text="\n".join(out), folded=folded)
