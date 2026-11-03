"""The disc header's guard against rows forged by an echoed value (TASKS R86).

**The problem.** cyanrip prints metadata and CD-TEXT values with a bare
``"%s\\n"`` (``cyanrip@eca33dc:src/cyanrip_log.c:58-62``, ``:770-776``,
``:785-788``), so a value holding a line break puts the text after it at column
0 of a line of its own, shaped exactly like a row cyanrip printed itself. Our own
values cannot carry one (the argv chokepoint, decision D14); the disc's own
CD-TEXT can, whatever we send. Inside a track block the parser already sets
verdict rows found after the echo aside (``cyanrip_log._TRACK_ECHO_HEADER``).
This module is the same idea for the DISC header, where every rule let the last
copy of a row win, so a forged ``Offset: +667 samples`` or ``DiscID: …`` after
cyanrip's own replaced it.

**Two guards, each resting on an order every committed log agrees on** (read
from all of them, with a floor, by ``tests/test_echoed_field_forgery.py``):

* ``ECHO_LATCH_BEFORE_CDTEXT`` holds the rows cyanrip prints ABOVE the disc
  ``CD-TEXT:`` row (drive, offset, overread mode, speed, C2, accurate stream,
  recordable, the argv echo). No value from outside the code is printed above
  that row (the argv echo carries only our own, D14-screened values), so once
  the row, or a track block, has been reached, one of these can only be a
  forgery: counted and not read. cyanrip's own value is kept.
* ``ECHO_LATCH_ONCE`` holds the rows printed BELOW the disc ``CD-TEXT:`` block
  and above ``Album:`` (paranoia level, outputs, tracks to rip, DiscID, CDDB ID).
  A forgery can stand before cyanrip's copy (in the disc CD-TEXT block) or after
  it (on the ``Album:`` line), and no row we can see marks where that block
  ends, so neither copy can be preferred. cyanrip prints each exactly once, so a
  second copy at disc level makes the row NOT DETERMINED (its "cyanrip did not
  say" value), never the forger's value. Inside a track block it is dropped.

Rows below ``Album:`` need neither: every route a forgery has reaches them before
cyanrip's copy, which wins as the last, and track blocks cannot reach them
(``disc_level_only``).

**The disc ``CD-TEXT:`` row itself** stays on the parser's ignored list for its
content (``cyanrip_log._IGNORED_DISC_LINES``); only its POSITION is used here.

**What this does not close**, and only the fork escaping what it echoes can: a
forged block opener (``Track N read successfully!``) or ``Done;`` line, and a
row of the ``ONCE`` group on a build that prints none of its own.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Final

log = logging.getLogger(__name__)

#: The disc-level ``CD-TEXT:`` row, at column 0: where outside text can first
#: appear in the header. A track's own ``CD-TEXT:`` header is indented.
DISC_CDTEXT_ROW: Final[re.Pattern[str]] = re.compile(r"^CD-TEXT:")

#: The two guards a disc rule can be held by; see the module docstring.
ECHO_LATCH_BEFORE_CDTEXT: Final[str] = "before_cdtext"
ECHO_LATCH_ONCE: Final[str] = "once"


@dataclass
class EchoGuard:
    """One parse's guard state. Mutable, owned by the parser's disc accumulator.

    ``past_disc_cdtext``: the disc ``CD-TEXT:`` row, or a track block, has been
    reached. ``once_seen``: ONCE rows read so far. ``ambiguous``: ONCE rows seen
    twice, so not determined. ``set_aside``: forged copies counted and not read.
    """

    past_disc_cdtext: bool = False
    once_seen: set[str] = field(default_factory=set)
    ambiguous: set[str] = field(default_factory=set)
    set_aside: int = 0

    def note_line(self, line: str, *, in_track: bool) -> None:
        """Advance the latch on a line, before any rule reads it. Never raises."""
        if in_track or DISC_CDTEXT_ROW.match(line):
            self.past_disc_cdtext = True

    def claims(self, latch: str, name: str, *, in_track: bool) -> bool:
        """Whether the row ``name``, held by ``latch``, is set aside unread.

        True means a forged copy: counted, and for a second disc-level copy of a
        ONCE row also marked not determined (cleared by the parser after its
        loop, so a third copy cannot bring a value back). False means read it.
        A ``latch`` that names neither guard is never set aside. Never raises.
        """
        if latch == ECHO_LATCH_BEFORE_CDTEXT:
            forged = self.past_disc_cdtext or in_track
        elif latch == ECHO_LATCH_ONCE and in_track:
            forged = True
        elif latch == ECHO_LATCH_ONCE:
            forged = name in self.once_seen
            if forged:
                self.ambiguous.add(name)
            self.once_seen.add(name)
        else:
            return False
        if forged:
            self.set_aside += 1
        return forged

    def report(self) -> None:
        """Log what was set aside, as a warning: each is a value that broke a line."""
        if self.set_aside:
            log.warning(
                "cyanrip log: %d disc header row(s) set aside as echoed copies (a "
                "value cyanrip echoed carried a line break); not determined: %s",
                self.set_aside,
                ", ".join(sorted(self.ambiguous)) or "none",
            )
