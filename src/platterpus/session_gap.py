# SPDX-License-Identifier: GPL-3.0-only
"""cyanrip's ``Session gap:`` track line (``.35``): a CD-Extra cut made by assumption.

**What the line is.** On an Enhanced CD (audio session, then a data session) the
last audio track ends 11,400 frames before the data track starts: the gap between
the sessions. cyanrip takes those frames off the track's end. Until ``.35`` it did
so whether or not the drive answered the last-session query that says a second
session exists, and said nothing. From ``.35`` (the fork's round 42 lap 1 S7, as
our round 41 lap 4 S17 answered), when the cut is made because the query FAILED,
the track block says so under ``End LSN:``::

    Session gap: not determined (the last-session query failed; 11400 frames cut by assumption)

(``cyanrip@1280aa4:src/cyanrip_log.c:624-626``; the flag is set where the cut is
made, ``src/cyanrip_main.c:756``). Every image prints it on such a disc, since no
image driver answers the query; no drive has printed it yet (their lap, citing
their ``docs/OPEN-ITEMS.md`` HW-18).

**Why we keep it.** It says the track's ``End LSN:`` is an assumption, not a
measured session layout. :func:`read_session_gap` keeps the state, the ripper's
reason as printed and the frames it names, on the track
(``parsers.rip_log.TrackResult.session_gap``). Nothing renders it yet (TASKS
R192); keeping it is the first half.

**Tri-state, and never raises.** ``not_determined`` is the one shape ``.35``
prints. Any other value, a non-string among them, is ``unrecognised``, with the
value kept, bounded and screened (``inbound_text``), and no count invented for it.
No line at all is ``None`` on the track: an earlier build, a one-session disc, or a
drive that answered the query.

Pure, Qt-free. Imports nothing from the parser, so the parser and
:mod:`platterpus.parsers.rip_log` take the dataclass from here without a cycle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from platterpus import diagnostics, inbound_text
from platterpus.safe_int import int_or_none

#: The line, indented as the track block's other rows; everything after the label
#: is the value. Linear on any input (``tests/test_regex_bounded_time.py``).
SESSION_GAP_LINE: Final[re.Pattern[str]] = re.compile(
    r"^\s{1,8}Session gap:[ \t]*(?P<value>[^\n]*)$"
)

#: ``not determined (<reason>)``: the cut was made by assumption.
SESSION_GAP_NOT_DETERMINED: Final[str] = "not_determined"
#: A line that is there in a wording we do not read: the value is kept.
#: Spelled as ``ripper_track_notes.UNRECOGNISED``.
SESSION_GAP_UNRECOGNISED: Final[str] = "unrecognised"

_NOT_DETERMINED: Final[re.Pattern[str]] = re.compile(
    r"^not determined \((?P<reason>[^()\n]{1,300})\)$"
)
#: The frames the ripper says it cut, at the end of its reason.
_FRAMES_CUT: Final[re.Pattern[str]] = re.compile(
    r"(?:^|; )(?P<frames>\d{1,9}) frames? cut by assumption$"
)

#: How much of a value is kept: head and tail, the gap counted.
_KEEP_HEAD: Final[int] = 200
_KEEP_TAIL: Final[int] = 100


@dataclass(frozen=True)
class SessionGap:
    """A track's ``Session gap:`` line.

    ``state`` is :data:`SESSION_GAP_NOT_DETERMINED` or
    :data:`SESSION_GAP_UNRECOGNISED`; ``text`` the value as printed, bounded and
    screened; ``reason`` the ripper's parenthetical, screened ("" when
    unrecognised); ``frames_cut`` the frames it names, or None where it names none.
    """

    state: str
    text: str
    reason: str = ""
    frames_cut: int | None = None


def _kept(value: object) -> str:
    """``value`` bounded and screened, so a control character shows as an escape.

    ``diagnostics.bounded_chars`` takes any object and never raises.
    """
    bounded = diagnostics.bounded_chars(value, head=_KEEP_HEAD, tail=_KEEP_TAIL)
    return inbound_text.screen_line(bounded).text or "(an empty value)"


def read_session_gap(value: object) -> SessionGap:
    """The ``Session gap:`` line's value as a :class:`SessionGap`. Never raises.

    Only ``not determined (...)`` is a shape ``.35`` prints; anything else is
    :data:`SESSION_GAP_UNRECOGNISED` with the value kept.
    """
    if not isinstance(value, str):
        return SessionGap(state=SESSION_GAP_UNRECOGNISED, text=_kept(value))
    text = value.strip()
    found = _NOT_DETERMINED.match(text)
    if found is None:
        return SessionGap(state=SESSION_GAP_UNRECOGNISED, text=_kept(text))
    reason = found.group("reason")
    frames = _FRAMES_CUT.search(reason)
    return SessionGap(
        state=SESSION_GAP_NOT_DETERMINED,
        text=_kept(text),
        reason=inbound_text.screen_line(reason).text,
        frames_cut=(
            int_or_none(frames.group("frames"), field="cyanrip session gap")
            if frames
            else None
        ),
    )
