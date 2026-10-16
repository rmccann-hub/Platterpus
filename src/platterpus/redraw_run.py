"""A run of the ripper's progress redraws, thinned for the record.

cyanrip redraws one progress line with ``\\r`` many times a second
(``Ripping track 5, progress - 42.37%, ETA - 3m, errors - 0``), and each redraw
reaches us as its own line. They are ~98% of everything it prints, so the rip
worker's capture of its stdout does not keep them whole. Until 2026-10-05 it kept
none of them, and the question it asked to recognise one also matched every
track's outcome line, ``Track N read successfully!``, so those were lost too (the
cyanrip fork's round 30 lap 9 S29).

What is kept now is the rule for any bounded output (``CLAUDE.md``, *Diagnostic
completeness*: head and tail, with any elision counted and marked), applied to each
run of redraws:

* the run's **first** line, which says where a read started;
* a **marker** counting the lines between, when there are any;
* the run's **last** line, which says how far the read got and with what error
  count, a figure the ripper's log does not carry.

So every redraw the ripper printed is either in the capture or in a marker's count,
and a reader can tell an elision from a ripper that went quiet.

Pure: no Qt, no I/O, never raises. The rip worker owns one run at a time and decides
which lines are redraws (``rip_worker._is_progress_redraw``); the report's label for
the capture quotes :data:`REDRAW_ELISION` so a reader can find the marker.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The words that identify the marker. A line the ripper could not have produced,
#: like every ``[platterpus]`` marker in the capture.
REDRAW_ELISION_PHRASE: str = "progress redraws elided here"

#: The marker written in place of a run's middle; ``{count}`` is how many lines it
#: stands for. Never written with a count of zero: that would claim an elision that
#: did not happen.
REDRAW_ELISION: str = f"[platterpus] … {{count}} {REDRAW_ELISION_PHRASE} …"


@dataclass
class RedrawRun:
    """The run of redraws not yet written to the capture.

    ``count`` is how many redraws the run has had, and 0 means no run is open. Only
    the first and the latest line are held, so the memory a run costs does not grow
    with its length.
    """

    first: str = ""
    last: str = ""
    count: int = 0

    def note(self, line: str) -> None:
        """Add one redraw to the run, opening it if none is open."""
        if self.count == 0:
            self.first = line
        self.last = line
        self.count += 1

    def lines(self) -> list[str]:
        """The run as the capture shows it, leaving it open. Reads only."""
        if self.count == 0:
            return []
        if self.count == 1:
            return [self.first]
        middle = self.count - 2
        elision = [REDRAW_ELISION.format(count=middle)] if middle else []
        return [self.first, *elision, self.last]

    def close(self) -> list[str]:
        """End the run and return its lines, for the caller to write."""
        shown = self.lines()
        self.count = 0
        return shown


#: How often a long run still writes a line to the app log. A freeze or a
#: force-kill then leaves the log saying where the read had got to, which is why
#: the log carried redraws at all ("a bug report shows exactly where the drive
#: stopped"), at a hundredth of the ten a second it used to write.
CHECKPOINT_SECONDS: float = 10.0


@dataclass
class LoggedRun:
    """A run of redraws as the app log writes it (TASKS R14).

    The app log and the report's ``debug.lines`` carried a redraw ten times a
    second, which was 85% of every filed app log (231 MB of 240 MB, measured
    2026-10-14), and the redraws between those ten were dropped without a count.
    Now a run writes its **first** line when it opens, one **checkpoint** line at
    most every :data:`CHECKPOINT_SECONDS`, and its **last** line when it closes,
    with a :data:`REDRAW_ELISION` marker before each written line counting the
    redraws not written since the one before. Every redraw is written or counted,
    exactly once.

    ``now`` is passed in rather than read, so this stays pure and a test can
    drive the clock.
    """

    last: str = ""
    count: int = 0
    skipped: int = 0
    written_at: float = 0.0

    def note(self, line: str, now: float) -> list[str]:
        """Add one redraw; return the lines to write now, in order."""
        if self.count == 0:
            self.count, self.skipped, self.last, self.written_at = 1, 0, line, now
            return [line]
        self.count += 1
        self.last = line
        if now - self.written_at < CHECKPOINT_SECONDS:
            self.skipped += 1
            return []
        shown = self._marker() + [line]
        self.skipped, self.written_at = 0, now
        return shown

    def close(self) -> list[str]:
        """End the run; return its marker and last line if they are unwritten."""
        if self.count == 0:
            return []
        shown: list[str] = []
        if self.skipped:
            # The last redraw is among the skipped; it is written, not counted.
            self.skipped -= 1
            shown = [*self._marker(), self.last]
        self.count = self.skipped = 0
        return shown

    def _marker(self) -> list[str]:
        return [REDRAW_ELISION.format(count=self.skipped)] if self.skipped else []
