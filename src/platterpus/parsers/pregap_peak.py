"""Reading cyanrip's proposed ``Pregap sample peak:`` row (TASKS R227).

**Why this exists.** A span before track 1 (the hidden track one audio, HTOA,
EAC's "range before track 1") can hold music. EAC reports it; cyanrip does not
rip it. The fork proposed, in its round 36 lap 1 S17, to say how loud that span
is, so a user can tell silence from a hidden track without ripping it, in track
1's block::

        Pregap sample peak: 12.3% (-18.2 dBFS), not ripped

or ``unknown (<reason>)`` when it was not measured. Our round 41 lap 2 S14 said
we still want it; their round 43 lap 1 S43 asks us to accept the wording, and
the fork prints it only from a build after a release of ours that reads it. So
this reader is built first, for a line no build prints yet.

**States.** ``read`` (a percentage and, where it is a number, the dBFS beside
it, with the clause after it such as ``not ripped`` kept in ``note``);
``unknown`` (the ripper's word, its parenthetical in ``reason``);
``unrecognised`` (any other shape, the value kept, bounded and screened);
``not_present`` (no line, which is every build released so far).

A percentage is read as ASCII digits only (``re.ASCII``), and bounded to 0 to
100; a dBFS of ``-inf`` (digital silence) is kept as text with ``dbfs`` null,
since JSON has no infinity. Pure, Qt-free, never raises: a parser of external
output (``tests/test_pregap_peak.py`` holds the property test).
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from typing import Final, TypedDict

from platterpus import diagnostics, inbound_text

log = logging.getLogger(__name__)

#: The span was measured: ``percent`` holds the peak.
PEAK_READ: Final[str] = "read"
#: ``unknown (<reason>)``: the span was not measured, for the ripper's reason.
PEAK_UNKNOWN: Final[str] = "unknown"
#: The line is there in a shape this build does not know; the value is kept.
PEAK_UNRECOGNISED: Final[str] = "unrecognised"
#: No ``Pregap sample peak:`` line: every build released so far.
PEAK_NOT_PRESENT: Final[str] = "not_present"
#: Every state :attr:`PregapPeak.state` can hold.
PEAK_STATES: Final[frozenset[str]] = frozenset(
    {PEAK_READ, PEAK_UNKNOWN, PEAK_UNRECOGNISED, PEAK_NOT_PRESENT}
)

#: The fork's proposed example, word for word from its round 36 lap 1 S17, so a
#: test can check our reading of it against the filed lap's text.
PROPOSED_EXAMPLE: Final[str] = "    Pregap sample peak: 12.3% (-18.2 dBFS), not ripped"

#: The row, indented as a track block's rows are (the proposal: four spaces),
#: its value everything after the label's padding. A value of only blanks still
#: matches, so it is read as ``unrecognised`` rather than left unclaimed.
LINE: Final[re.Pattern[str]] = re.compile(
    r"^[ \t]{1,16}Pregap sample peak:\s+(?P<value>\S(?:.*\S)?|[^\S\n])\s*$"
)

# The value's shapes, bounded everywhere so each is linear on any input
# (`tests/test_regex_bounded_time.py`).
_MEASURED: Final[re.Pattern[str]] = re.compile(
    r"^(?P<percent>[0-9]{1,3}(?:\.[0-9]{1,6})?)%"
    r"(?:\s{1,4}\((?P<dbfs>-?(?:inf|[0-9]{1,4}(?:\.[0-9]{1,6})?)) dBFS\))?"
    r"(?:,\s{1,4}(?P<note>[^\n]{1,120}))?$",
    re.ASCII,
)
_UNKNOWN: Final[re.Pattern[str]] = re.compile(
    r"^unknown \((?P<reason>[^()\n]{1,160})\)$"
)

#: How much of an unrecognised value is kept: head and tail, the gap counted.
_KEEP_HEAD: Final[int] = 80
_KEEP_TAIL: Final[int] = 40


@dataclass(frozen=True)
class PregapPeak:
    """What the ``Pregap sample peak:`` row said, as one of :data:`PEAK_STATES`.

    ``percent`` (0 to 100) and ``dbfs`` are set for ``read`` (``dbfs`` stays
    None for ``-inf`` or when the row gives none, and ``dbfs_text`` keeps what it
    said); ``note`` is the clause after the value (``not ripped``); ``reason``
    is the ripper's parenthetical for ``unknown``; ``value`` is the kept text
    for ``unrecognised``. The default is the line's absence.
    """

    state: str = PEAK_NOT_PRESENT
    percent: float | None = None
    dbfs: float | None = None
    dbfs_text: str = ""
    note: str = ""
    reason: str = ""
    value: str = ""


class PregapPeakBlock(TypedDict):
    """The rip report's ``pregap_peak`` object on a track (schema 48)."""

    state: str
    percent: float | None
    dbfs: float | None
    dbfs_text: str | None
    note: str | None
    reason: str | None
    value: str | None


def _kept(text: object) -> str:
    """``text`` bounded and screened, so a control character shows as an escape."""
    bounded = diagnostics.bounded_chars(text, head=_KEEP_HEAD, tail=_KEEP_TAIL)
    return inbound_text.screen_line(bounded).text or "(an empty value)"


def _unrecognised(value: object) -> PregapPeak:
    kept = _kept(value)
    log.warning(
        "cyanrip's Pregap sample peak: row reads %r, a shape no build we know "
        "prints (the fork's round 36 lap 1 S17); kept as given",
        kept,
    )
    return PregapPeak(state=PEAK_UNRECOGNISED, value=kept)


def read_value(value: object) -> PregapPeak:
    """Read a ``Pregap sample peak:`` value (everything after the label).

    See the module docstring for each state. Never raises.
    """
    if not isinstance(value, str):
        return _unrecognised(value)
    text = value.strip()
    measured = _MEASURED.match(text)
    if measured is not None:
        percent = float(measured.group("percent"))
        if not 0.0 <= percent <= 100.0:
            return _unrecognised(value)
        dbfs_text = measured.group("dbfs") or ""
        dbfs: float | None = None
        if dbfs_text and "inf" not in dbfs_text:
            parsed = float(dbfs_text)
            dbfs = parsed if math.isfinite(parsed) else None
        note = measured.group("note") or ""
        return PregapPeak(
            state=PEAK_READ,
            percent=percent,
            dbfs=dbfs,
            dbfs_text=dbfs_text,
            note=inbound_text.screen_line(note).text if note else "",
        )
    unknown = _UNKNOWN.match(text)
    if unknown is not None:
        return PregapPeak(
            state=PEAK_UNKNOWN,
            reason=inbound_text.screen_line(unknown.group("reason")).text,
        )
    return _unrecognised(value)


def read_line(line: str) -> PregapPeak | None:
    """The row's reading, or None when ``line`` is not the row. Never raises."""
    match = LINE.match(line) if isinstance(line, str) else None
    if match is None:
        return None
    return read_value(match.group("value"))


def report_block(peak: object) -> PregapPeakBlock:
    """The report's object for one track; ``not_present`` for anything else."""
    if not isinstance(peak, PregapPeak):
        peak = PregapPeak()
    return {
        "state": peak.state,
        "percent": peak.percent,
        "dbfs": peak.dbfs,
        "dbfs_text": peak.dbfs_text or None,
        "note": peak.note or None,
        "reason": peak.reason or None,
        "value": peak.value or None,
    }
