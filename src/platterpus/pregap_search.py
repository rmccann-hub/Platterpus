# SPDX-License-Identifier: GPL-3.0-only
"""What the ripper's sub-channel pre-gap search saw: the fork's ``Pregap search:``.

**Why this exists.** cyanrip finds a pre-gap the TOC does not declare by reading
the disc's Q sub-channel, sector by sector, until the frame that says "index 1"
and the one before it meet. When they never meet, the log says
``Pregap LSN:  unknown (sub-channel CRC mismatches)`` — and that reason was
printed whatever stopped the search, including frames that PASSED their CRC and
answered for another sector. On the fork's round 36 Full runs the reference
disc's track 9 read 95 frames in three ``.26`` logs and ``unknown`` in five,
where ``.25`` and EAC read 94, and nothing in the log could say which cause it was
(their round 36 lap 8 S5). From ``.27`` the track block carries one more line,
below ``Pregap source:`` (or below ``Pregap LSN:`` when no source was printed),
for every track a sub-channel search ran on, found or not
(``cyanrip@b2ffd42:src/cyanrip_log.c:476-489``; their P2 row
``cyanrip@b2ffd42:PROVIDER-CONTRACT.md:300``; their lap 8 S21)::

    Pregap search: 37 sectors asked; 2 reads failed the CRC; 0 sectors gave no
    frame passing it; 3 frames were another sector's; 0 had no address; frames
    answer +0 sectors off

(one line in the log), with ``; 200-retry pass ran`` when the search's harder
pass ran, and ``; LSN A to B undecided`` when it ended without an answer.

**What this module does with it.** :func:`read_search` turns the line's value into
a :class:`PregapSearch`; :func:`describe` writes the sentence a person reads where
a pre-gap is ``unknown`` (the rip audit, the ``expect-pregaps-agree`` grader), so
a drive run can tell CRC failures from misplaced frames without opening the log;
:func:`report_block` is the report's per-track ``pregap_search``.

**A wording we do not know is kept, never dropped.** The whole value, bounded
(head and tail, the cut counted) and screened (:mod:`platterpus.inbound_text`),
goes into :attr:`PregapSearch.unrecognised`, and no count is invented for it.
**Absence is not "no search"**: an older build, an image rip, and a pre-gap the
TOC or the lead-in gave all print no line, so the parse holds ``None``.

One reader, every caller. Pure, Qt-free, never raises. Imports nothing from the
parser, so the parser and :mod:`platterpus.parsers.rip_log` can take the
dataclass from here without a cycle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, TypedDict

from platterpus import diagnostics, inbound_text
from platterpus.safe_int import int_or_none

#: The line's value exactly as the fork's source prints it
#: (``cyanrip@b2ffd42:src/cyanrip_log.c:483-487``): five ``%i`` counts, a ``%+i``
#: shift, then the two optional clauses in the order the source appends them.
#: Every number is bounded to nine digits, so the pattern is linear on any input,
#: and a count with a sign is not a count (``%i`` of a non-negative tally prints
#: none). Applied with ``fullmatch`` to a value already capped in length.
_VALUE: Final[re.Pattern[str]] = re.compile(
    r"(?P<asked>\d{1,9}) sectors asked; "
    r"(?P<crc_failed>\d{1,9}) reads failed the CRC; "
    r"(?P<no_frame>\d{1,9}) sectors gave no frame passing it; "
    r"(?P<elsewhere>\d{1,9}) frames were another sector's; "
    r"(?P<no_address>\d{1,9}) had no address; "
    r"frames answer (?P<shift>[+-]\d{1,9}) sectors off"
    r"(?P<harder>; 200-retry pass ran)?"
    r"(?:; LSN (?P<undecided_from>-?\d{1,9}) to (?P<undecided_to>-?\d{1,9}) "
    r"undecided)?"
)

#: A value longer than this is not the line above whatever it holds (the longest
#: the source can print, every number at nine digits, is under 250 characters),
#: so it is kept as unrecognised without being matched.
MAX_VALUE_CHARS: Final[int] = 400

#: How much of an unrecognised value is kept: its head and its tail, the middle
#: cut and counted (``diagnostics.bounded_chars``), because a reworded line's
#: change can be at either end.
_KEEP_HEAD: Final[int] = 200
_KEEP_TAIL: Final[int] = 100

#: The two states a search line can be read into. No line is ``None`` on the
#: track, never a third state here: only the parser knows whether a line was there.
READ: Final[str] = "read"
UNRECOGNISED: Final[str] = "unrecognised"


@dataclass(frozen=True)
class PregapSearch:
    """One track's ``Pregap search:`` line, read.

    When :attr:`unrecognised` is ``""`` the line was read and every count is an
    int; otherwise it holds the line's value (bounded, screened) and every count
    is ``None``, because a count we did not read is not a zero.

    ``elsewhere`` is the count the line exists for: frames that passed their CRC
    and named another sector. ``shift`` is how far, in sectors, the frames the
    search settled on answer from the sector asked for. ``undecided_from`` and
    ``undecided_to`` are the stretch the search could not decide, printed only
    when it ended without an answer (both ``None`` otherwise).
    """

    asked: int | None = None
    crc_failed: int | None = None
    no_frame: int | None = None
    elsewhere: int | None = None
    no_address: int | None = None
    shift: int | None = None
    harder_pass_ran: bool | None = None
    undecided_from: int | None = None
    undecided_to: int | None = None
    unrecognised: str = ""

    @property
    def state(self) -> str:
        """:data:`READ` or :data:`UNRECOGNISED`."""
        return UNRECOGNISED if self.unrecognised else READ


class PregapSearchBlock(TypedDict):
    """The report's per-track ``pregap_search`` (schema 40; ``report_types``).

    The counts are ``None`` when ``state`` is ``unrecognised``; ``unrecognised``
    then holds the line's value, bounded and screened. ``summary`` is
    :func:`describe`'s sentence.
    """

    state: str
    asked: int | None
    crc_failed: int | None
    no_frame: int | None
    elsewhere: int | None
    no_address: int | None
    shift: int | None
    harder_pass_ran: bool | None
    undecided_from: int | None
    undecided_to: int | None
    unrecognised: str | None
    summary: str


def _kept(value: str) -> str:
    """``value`` bounded and screened, for a wording we do not recognise."""
    bounded = diagnostics.bounded_chars(value, head=_KEEP_HEAD, tail=_KEEP_TAIL)
    return inbound_text.screen_line(bounded).text or "(an empty value)"


def read_search(value: object) -> PregapSearch:
    """The ``Pregap search:`` line's value as a :class:`PregapSearch`. Never raises.

    ``value`` is everything after the label. Anything but the source's own
    wording, a non-string included, is :data:`UNRECOGNISED`, kept rather than
    dropped; the parser logs it.
    """
    if not isinstance(value, str):
        return PregapSearch(unrecognised=_kept(repr(value)))
    text = value.strip()
    if len(text) > MAX_VALUE_CHARS:
        return PregapSearch(unrecognised=_kept(text))
    match = _VALUE.fullmatch(text)
    if match is None:
        return PregapSearch(unrecognised=_kept(text))
    numbers: dict[str, int] = {}
    for name in ("asked", "crc_failed", "no_frame", "elsewhere", "no_address", "shift"):
        number = int_or_none(match.group(name), field=f"Pregap search {name}")
        if number is None:  # unreachable with the bounded pattern; kept honest
            return PregapSearch(unrecognised=_kept(text))
        numbers[name] = number
    undecided_from = int_or_none(
        match.group("undecided_from"), field="Pregap search undecided from"
    )
    undecided_to = int_or_none(
        match.group("undecided_to"), field="Pregap search undecided to"
    )
    return PregapSearch(
        asked=numbers["asked"],
        crc_failed=numbers["crc_failed"],
        no_frame=numbers["no_frame"],
        elsewhere=numbers["elsewhere"],
        no_address=numbers["no_address"],
        shift=numbers["shift"],
        harder_pass_ran=match.group("harder") is not None,
        undecided_from=undecided_from,
        undecided_to=undecided_to,
    )


def _count(number: int, one: str, many: str) -> str:
    return f"{number} {one if number == 1 else many}"


def describe(search: PregapSearch | None) -> str:
    """The search's counts as a person reads them, or ``""`` for no line.

    Always names the two counts that tell the causes of an ``unknown`` apart
    (reads that failed the CRC, frames that answered for another sector), even at
    zero, since a zero is what rules a cause out. The other counts are named only
    when they are not zero. Never raises.
    """
    if search is None:
        return ""
    if search.unrecognised:
        return f"the search's line, in a wording this version does not read: {search.unrecognised}"
    if (
        search.asked is None
        or search.crc_failed is None
        or search.elsewhere is None
        or search.no_frame is None
        or search.no_address is None
        or search.shift is None
    ):
        return ""
    parts = [
        _count(search.asked, "sector asked", "sectors asked"),
        _count(search.crc_failed, "read failed the CRC", "reads failed the CRC"),
        _count(
            search.elsewhere,
            "frame answered for another sector",
            "frames answered for another sector",
        ),
    ]
    if search.no_frame:
        parts.append(
            _count(
                search.no_frame,
                "sector gave no frame passing the CRC",
                "sectors gave no frame passing the CRC",
            )
        )
    if search.no_address:
        parts.append(
            _count(search.no_address, "frame had no address", "frames had no address")
        )
    if search.shift:
        parts.append(f"frames answered {search.shift:+d} sectors off")
    if search.harder_pass_ran:
        parts.append("the 200-retry pass ran")
    if search.undecided_from is not None and search.undecided_to is not None:
        parts.append(f"LSN {search.undecided_from} to {search.undecided_to} undecided")
    return "; ".join(parts)


def report_block(search: object) -> PregapSearchBlock | None:
    """The report's ``pregap_search`` for one track, or ``None`` for no line.

    Takes ``object`` because the report reads the track with ``getattr``: anything
    that is not a :class:`PregapSearch` is written as "not stated" rather than as
    something that looks like a measurement. Never raises.
    """
    if not isinstance(search, PregapSearch):
        return None
    return PregapSearchBlock(
        state=search.state,
        asked=search.asked,
        crc_failed=search.crc_failed,
        no_frame=search.no_frame,
        elsewhere=search.elsewhere,
        no_address=search.no_address,
        shift=search.shift,
        harder_pass_ran=search.harder_pass_ran,
        undecided_from=search.undecided_from,
        undecided_to=search.undecided_to,
        unrecognised=search.unrecognised or None,
        summary=describe(search),
    )
