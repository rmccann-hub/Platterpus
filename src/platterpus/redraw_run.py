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
