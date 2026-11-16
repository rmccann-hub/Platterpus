# SPDX-License-Identifier: GPL-3.0-only
"""cyanrip's ``Disc MCN:`` header line: the disc's catalogue number, or why there is none.

**What the line is.** The MCN (Media Catalog Number) is the disc's 13-digit
UPC/EAN, stored in the sub-channel and read by libcdio's ``cdio_get_mcn``. cyanrip
prints it in the start report, which both a rip and ``-I`` print
(``cyanrip_log_start_report``, called for either at
``cyanrip@13bec0a:src/cyanrip_main.c:4258``), between ``CDDB ID:`` and ``Album:``:

* **today, every build:** ``Disc MCN:       %s``, through ``CLOG``, which prints
  nothing when the value is unset (``cyanrip@13bec0a:src/cyanrip_log.c:1367``, the
  macro at ``:41-43``). The fork sets it only when the drive declares it can read
  an MCN and libcdio returned one that is not all zeroes
  (``cyanrip@13bec0a:src/cyanrip_main.c:819-838``, ``crip_fill_mcn``); upstream
  prints an all-zero code as it came (the shape in
  ``tests/test_parsers_cyanrip_info.py``'s report, ``0000000000000``). So today a
  disc with no MCN, a driver that cannot read one and a failed capabilities query
  all print NO line;
* **the fork's PROPOSAL** (their round 38 lap 3 S17,
  ``docs/handshake/inbound/round-38-lap-03.md:130``, accepted in our round 38
  lap 4 S11, and printed in the first build after a release of ours that reads
  it, their round 41 lap 1 S18): the line ALWAYS, with the reason in
  ``Disc ISRC:``'s shape, ``%s (%s)``:

  - ``none (libcdio returned none)``
  - ``unknown (the driver does not report reading MCN)``
  - ``unknown (capabilities query failed)``

  Read here before any build prints them.

**The states**, one field (:class:`DiscMcn`), tri-state at heart: a value, an
absence with the ripper's reason, or no line at all:

* ``read``: 13 ASCII digits, not all zero. ``value`` holds them;
* ``all_zero``: ``0000000000000``, which upstream prints and the fork treats as
  "none at all" (``cyanrip_main.c:819``). Kept apart from ``read`` so an all-zero
  code is never presented as a catalogue number, and apart from ``none`` so we
  never write a reason the ripper did not give;
* ``none`` / ``unknown``: the ripper's word, its reason verbatim in ``reason``.
  Any reason is taken (bounded, screened): a reworded reason is still the ripper
  saying there is no MCN, or that it does not know. :data:`PROPOSED_REASONS`
  lists the three the lap proposes; another is logged at INFO, not refused;
* ``unrecognised``: anything else (a code of the wrong length, a letter, a
  control character, a value with a parenthetical the proposal has no shape
  for). The value is KEPT, bounded and screened (``inbound_text``), in
  ``value``, and a warning names it in the log file. Never dropped silently;
* ``not_present``: no ``Disc MCN:`` line. On every build today, that is most
  discs; after the proposal ships, it means an older build or a log cut short.

A value is never validated by being a number: ``int("１２３")`` takes full-width
digits and ``str.isdigit`` takes superscripts, so the check is
``[0-9]{13}`` on ASCII only (``re.ASCII``).

Pure, Qt-free, never raises. Both parsers take :data:`LINE` and
:func:`read_value` from here, so a rip log and ``-I`` cannot read one line two
ways (``tests/test_disc_mcn.py``).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Final, TypedDict

from platterpus import diagnostics, inbound_text

log = logging.getLogger(__name__)

#: 13 ASCII digits, not all zero: the disc's catalogue number.
MCN_READ: Final[str] = "read"
#: ``0000000000000``: upstream's print of a disc with no MCN.
MCN_ALL_ZERO: Final[str] = "all_zero"
#: ``none (<reason>)``: libcdio answered, with no MCN (the proposal).
MCN_NONE: Final[str] = "none"
#: ``unknown (<reason>)``: the read was not made, or its answer is not known.
MCN_UNKNOWN: Final[str] = "unknown"
#: The line is there in a shape this build does not know; the value is kept.
#: Spelled as ``parsers.rip_log.DRIVE_FACT_UNRECOGNISED``.
MCN_UNRECOGNISED: Final[str] = "unrecognised"
#: No ``Disc MCN:`` line. Spelled as ``parsers.rip_log.DRIVE_FACT_NOT_PRESENT``.
MCN_NOT_PRESENT: Final[str] = "not_present"
#: Every state :attr:`DiscMcn.state` can hold.
MCN_STATES: Final[frozenset[str]] = frozenset(
    {
        MCN_READ,
        MCN_ALL_ZERO,
        MCN_NONE,
        MCN_UNKNOWN,
        MCN_UNRECOGNISED,
        MCN_NOT_PRESENT,
    }
)

#: The reasons the fork's round 38 lap 3 S17 proposes, word for word, by state.
PROPOSED_REASONS: Final[dict[str, frozenset[str]]] = {
    MCN_NONE: frozenset({"libcdio returned none"}),
    MCN_UNKNOWN: frozenset(
        {"the driver does not report reading MCN", "capabilities query failed"}
    ),
}

#: The line, at column 0, the value everything after the label's padding. The
#: idiom of the other header rows (``Accurate stream:``): a value of only blanks
#: still matches, so it is read as ``unrecognised`` rather than left unclaimed.
LINE: Final[re.Pattern[str]] = re.compile(
    r"^Disc MCN:\s+(?P<value>\S(?:.*\S)?|[^\S\n])\s*$"
)

# The value's shapes. ASCII digits only; bounded everywhere, so each is linear
# on any input (`tests/test_regex_bounded_time.py`).
_CODE: Final[re.Pattern[str]] = re.compile(r"^[0-9]{13}$", re.ASCII)
_ALL_ZERO: Final[str] = "0" * 13
_ABSENT: Final[re.Pattern[str]] = re.compile(
    r"^(?P<state>none|unknown) \((?P<reason>[^()\n]{1,120})\)$"
)

#: How much of an unrecognised value is kept: head and tail, the gap counted.
_KEEP_HEAD: Final[int] = 80
_KEEP_TAIL: Final[int] = 40


@dataclass(frozen=True)
class DiscMcn:
    """What the ``Disc MCN:`` line said, as one of :data:`MCN_STATES`.

    ``value`` is the 13 digits for ``read`` and ``all_zero``, the kept (bounded,
    screened) text for ``unrecognised``, and "" otherwise. ``reason`` is the
    ripper's parenthetical for ``none`` and ``unknown``, screened, and ""
    otherwise. The default is the line's absence.
    """

    state: str = MCN_NOT_PRESENT
    value: str = ""
    reason: str = ""


def _kept(text: object) -> str:
    """``text`` bounded and screened, so a control character shows as an escape.

    ``diagnostics.bounded_chars`` takes any object and never raises, so a
    non-string's text is kept the same way.
    """
    bounded = diagnostics.bounded_chars(text, head=_KEEP_HEAD, tail=_KEEP_TAIL)
    return inbound_text.screen_line(bounded).text or "(an empty value)"


def read_value(value: object) -> DiscMcn:
    """Read a ``Disc MCN:`` value (everything after the label) as a :class:`DiscMcn`.

    See the module docstring for each state. A non-string is ``unrecognised``
    like any other shape we do not know. Pure and never raises (a parser of
    external output); logs a warning for ``unrecognised`` and an INFO line for a
    reason the proposal does not list.
    """
    text = value.strip() if isinstance(value, str) else ""
    if isinstance(value, str) and _CODE.match(text):
        state = MCN_ALL_ZERO if text == _ALL_ZERO else MCN_READ
        return DiscMcn(state=state, value=text)
    absent = _ABSENT.match(text) if isinstance(value, str) else None
    if absent is not None:
        state, reason = absent.group("state"), absent.group("reason")
        screened = inbound_text.screen_line(reason)
        if reason not in PROPOSED_REASONS[state] or screened.flagged:
            log.info(
                "cyanrip's Disc MCN: line gives the reason %r, which the fork's "
                "round 38 lap 3 S17 does not list; kept as the ripper's own",
                screened.text,
            )
        return DiscMcn(state=state, reason=screened.text)
    kept = _kept(text if isinstance(value, str) else value)
    log.warning(
        "cyanrip's Disc MCN: line reads %r, which is not 13 ASCII digits nor a "
        "none/unknown reason; recorded as unrecognised with the value kept",
        kept,
    )
    return DiscMcn(state=MCN_UNRECOGNISED, value=kept)


class DiscMcnBlock(TypedDict):
    """The report's ``rip.disc_mcn`` (schema 47): always present, ``state`` saying
    whether the line was printed; ``value`` and ``reason`` null where empty."""

    state: str
    value: str | None
    reason: str | None


def report_block(mcn: object) -> DiscMcnBlock:
    """``mcn`` (a :class:`DiscMcn`) as the report's block. Never raises.

    Anything that is not a :class:`DiscMcn` (a legacy-format log's object, a
    stand-in) reads as ``not_present``: the report says no line was read, never
    a value it was not given.
    """
    if not isinstance(mcn, DiscMcn) or mcn.state not in MCN_STATES:
        return {"state": MCN_NOT_PRESENT, "value": None, "reason": None}
    return {
        "state": mcn.state,
        "value": mcn.value or None,
        "reason": mcn.reason or None,
    }
