# SPDX-License-Identifier: GPL-3.0-only
"""The fork's ``Other read:`` line: each value a track's ``-Z`` reads gave that was not kept.

**Why this exists.** Under ``-Z`` cyanrip reads a track until its reads agree or a
limit stops it, and keeps one read. Until ``.30`` the log named only the kept
read, so a track whose reads disagreed said THAT they disagreed and never what
else the drive had given, nor where. Our ``docs/eac-parity.md`` Part G.5 asked
for it, to rebuild a disputed second; the fork's round 38 lap 8 S16 built it, and
our round 38 lap 9 S10 promised a release of ours reads it before one names
``.30``.

**The line, from their source** (``cyanrip@40dc64d7:src/cyanrip_log.c:856-896``;
the P2 row ``cyanrip@40dc64d7:PROVIDER-CONTRACT.md:375``)::

    "  Other read:      %08X, read %i time%s, %s%s%s\\n"

One line per VALUE not kept, with how many reads gave it (``read %i time%s``;
the fork's round 39 lap 5 S7, ``cyanrip@e531a33:src/cyanrip_log.c:874-897``),
in the order first read, in the track block after
``Secure re-read:`` and before ``Accurip:``, so before ``Metadata:`` and inside
our echo boundary (``parsers/cyanrip_log._TRACK_ECHO_HEADER``). None is printed
when no read was kept or the track had one distinct read. The parts:

* the read's EAC CRC32, eight upper-case hex digits;
* ``read N time`` or ``times``, ``time`` exactly when N is 1;
* where it differs from the kept read, one of three arms (``:874-890``):

  - ``differs from the kept read; which seconds is not known (per-second CRCs
    not kept)`` when either read's per-second CRCs are missing or the two lists
    differ in length;
  - ``differs from the kept read in second 1 (00:01)``: ``second`` when one
    second differs, else ``seconds``; each second counted from 0 with its
    ``%02i:%02i`` (minutes, seconds), the first 8 named, ``, `` between them,
    then ``, and N more`` when more than 8 differ;
  - empty, only when their print buffer could not be completed;

* ``; saved as <path>`` when ``--keep-every-read`` saved the read: the folder as
  given, less any trailing slash, then ``/NN-CRC.wav`` (``cyanrip@40dc64d7:
  src/cyanrip_main.c:1439-1465``; their round 38 lap 10 S5 and S6). Never made
  absolute. Our rips do not send ``--keep-every-read``, so ours carry none.

Their own test builds the second arm word for word
(``cyanrip@40dc64d7:tests/rip_images.py:8970-8972``), and their lap 8 S16 quotes
``  Other read:      2FFECF45, read 1 time, differs from the kept read in second
1 (00:01); saved as reads/01-2FFECF45.wav``.

**Checked, not trusted.** Each named second must carry its own ``mm:ss``, in
order and once; ``and N more`` follows exactly eight; ``second`` is singular
exactly when one differs; ``time`` exactly when read once. A part that breaks one
of these is :data:`UNRECOGNISED`, the value kept, screened and bounded, never a
fact we half read. Pure, Qt-free, never raises; imports nothing from the parser.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from typing import Final, TypedDict

from platterpus import diagnostics, inbound_text
from platterpus.safe_int import int_or_none

#: The line, indented as the track block's other rows. Unbounded on purpose and
#: still linear (nothing before ``.*`` can match what it does), so a line of any
#: length is claimed here rather than falling unread into the skimmed residue;
#: :func:`read_other_read` bounds the value.
OTHER_READ_LINE: Final[re.Pattern[str]] = re.compile(
    r"^\s{1,8}Other read:\s+(?P<value>\S.*)$"
)

#: The value's fixed head: CRC, count and its unit, then whatever follows.
_HEAD: Final[re.Pattern[str]] = re.compile(
    r"(?P<crc>[0-9A-F]{8}), read (?P<count>\d{1,9}) (?P<unit>times?),(?P<rest>.*)"
)

#: The second arm: the named seconds, at most eight, then the count of the rest.
_IN_SECONDS: Final[re.Pattern[str]] = re.compile(
    r"differs from the kept read in (?P<unit>seconds?)"
    r"(?: (?P<named>\d{1,5} \(\d{2,3}:\d{2}\)(?:, \d{1,5} \(\d{2,3}:\d{2}\)){0,7}))?"
    r"(?:, and (?P<more>\d{1,5}) more)?"
)
_ONE_SECOND: Final[re.Pattern[str]] = re.compile(
    r"(?P<index>\d{1,5}) \((?P<minutes>\d{2,3}):(?P<seconds>\d{2})\)"
)

#: The first arm, word for word (``cyanrip@40dc64d7:src/cyanrip_log.c:876``).
NOT_KNOWN_TEXT: Final[str] = (
    "differs from the kept read; which seconds is not known (per-second CRCs not kept)"
)
#: What separates the file from the rest (``cyanrip@40dc64d7:src/cyanrip_log.c:891-894``).
SAVED_AS: Final[str] = "; saved as "
#: How many seconds the line names before it counts the rest (``:882``, ``:888``).
NAMED_MAX: Final[int] = 8

# --- states -------------------------------------------------------------------

#: The CRC and the count read in the source's wording.
READ: Final[str] = "read"
#: A line that is there, in a wording we do not read: kept, bounded and screened.
UNRECOGNISED: Final[str] = "unrecognised"
STATES: Final[frozenset[str]] = frozenset({READ, UNRECOGNISED})

#: Where the read differs from the kept one: the seconds were named.
WHERE_SECONDS: Final[str] = "seconds"
#: The first arm: the per-second CRCs needed to say were not kept.
WHERE_NOT_KNOWN: Final[str] = "not_known"
#: Nothing printed there (their buffer could not be completed).
WHERE_NOT_STATED: Final[str] = "not_stated"
WHERE_STATES: Final[frozenset[str]] = frozenset(
    {WHERE_SECONDS, WHERE_NOT_KNOWN, WHERE_NOT_STATED, UNRECOGNISED}
)

#: A value longer than this is not one the source can print (a path is at most
#: 4,096 bytes on Linux), and is kept as its head and tail only.
MAX_VALUE_CHARS: Final[int] = 4096 + 512
_KEEP_HEAD: Final[int] = 300
_KEEP_TAIL: Final[int] = 300

#: Lines kept per track, from each end; the middle is counted. A ``-Z`` track has
#: at most as many distinct reads as ``-r`` allows, far fewer than this.
KEEP_HEAD: Final[int] = 32
KEEP_TAIL: Final[int] = 32


@dataclass(frozen=True)
class OtherRead:
    """One ``Other read:`` line, as cyanrip printed it.

    ``seconds`` are the seconds the line NAMES, counted from 0, and
    ``seconds_not_named`` the ``and N more``; both mean something only when
    ``where`` is :data:`WHERE_SECONDS`. ``file`` is the path as printed, None when
    the line names none.
    """

    state: str
    text: str
    crc: str | None = None
    count: int | None = None
    where: str = UNRECOGNISED
    seconds: tuple[int, ...] = ()
    seconds_not_named: int | None = None
    file: str | None = None

    @property
    def seconds_differing(self) -> int | None:
        """How many seconds differ, named and counted; None unless stated."""
        if self.where != WHERE_SECONDS or self.seconds_not_named is None:
            return None
        return len(self.seconds) + self.seconds_not_named


class OtherReadEntry(TypedDict):
    """One line in the report's per-track ``other_reads`` (schema 44)."""

    state: str
    crc: str | None
    count: int | None
    #: ``seconds`` / ``not_known`` / ``not_stated`` / ``unrecognised``.
    differs: str
    #: The seconds the line names, from 0; null unless ``differs`` is ``seconds``.
    differing_seconds: list[int] | None
    differing_seconds_not_named: int | None
    differing_seconds_total: int | None
    file: str | None
    #: The value as printed, screened and bounded.
    text: str


class OtherReadsBlock(TypedDict):
    """The report's per-track ``other_reads`` (schema 44); null when no line."""

    reads: list[OtherReadEntry]
    #: Lines past :data:`KEEP_HEAD` + :data:`KEEP_TAIL`, from the middle.
    not_kept: int


def _kept(value: str) -> str:
    bounded = diagnostics.bounded_chars(value, head=_KEEP_HEAD, tail=_KEEP_TAIL)
    return inbound_text.screen_line(bounded).text


def _seconds(where: str) -> tuple[tuple[int, ...], int] | None:
    """The second arm as ``(named seconds, not named)``, or None. Never raises."""
    match = _IN_SECONDS.fullmatch(where)
    if match is None:
        return None
    named: list[int] = []
    for one in _ONE_SECOND.finditer(match.group("named") or ""):
        index = int_or_none(one.group("index"), field="Other read second")
        minutes = int_or_none(one.group("minutes"), field="Other read minutes")
        seconds = int_or_none(one.group("seconds"), field="Other read seconds")
        if index is None or (minutes, seconds) != divmod(index, 60):
            return None  # a second whose mm:ss is not its own
        if named and index <= named[-1]:
            return None  # out of order, or named twice
        named.append(index)
    more = int_or_none(match.group("more") or "0", field="Other read more")
    if more is None or (more and len(named) != NAMED_MAX):
        return None
    if (match.group("unit") == "second") != (len(named) + more == 1):
        return None
    return tuple(named), more


def read_other_read(value: object) -> OtherRead:
    """The ``Other read:`` line's value as an :class:`OtherRead`. Never raises."""
    if not isinstance(value, str):
        return OtherRead(UNRECOGNISED, _kept(repr(value)))
    text = value.strip()
    kept = _kept(text)
    head = _HEAD.fullmatch(text) if len(text) <= MAX_VALUE_CHARS else None
    if head is None:
        return OtherRead(UNRECOGNISED, kept)
    count = int_or_none(head.group("count"), field="Other read count")
    if count is None or count < 1 or (head.group("unit") == "time") != (count == 1):
        return OtherRead(UNRECOGNISED, kept)
    rest = head.group("rest")
    if rest and not rest.startswith(" "):
        return OtherRead(UNRECOGNISED, kept)
    where_text, saved, path = rest[1:].partition(SAVED_AS)
    if saved and not path.strip():
        return OtherRead(UNRECOGNISED, kept)
    where_text = where_text.strip()
    seconds: tuple[int, ...] = ()
    not_named: int | None = None
    if not where_text:
        where = WHERE_NOT_STATED
    elif where_text == NOT_KNOWN_TEXT:
        where = WHERE_NOT_KNOWN
    else:
        parsed = _seconds(where_text)
        where = WHERE_SECONDS if parsed is not None else UNRECOGNISED
        if parsed is not None:
            seconds, not_named = parsed
    return OtherRead(
        READ,
        kept,
        crc=head.group("crc"),
        count=count,
        where=where,
        seconds=seconds,
        seconds_not_named=not_named,
        file=inbound_text.screen_line(path).text if saved else None,
    )


@dataclass
class OtherReadsAcc:
    """One track's lines while its block is read: head and tail kept, middle counted."""

    head: list[OtherRead] = field(default_factory=list)
    tail: deque[OtherRead] = field(default_factory=lambda: deque(maxlen=KEEP_TAIL))
    not_kept: int = 0

    def add(self, read: OtherRead) -> None:
        if len(self.head) < KEEP_HEAD:
            self.head.append(read)
            return
        if len(self.tail) == KEEP_TAIL:
            self.not_kept += 1  # the oldest of the tail leaves it
        self.tail.append(read)

    def result(self) -> tuple[tuple[OtherRead, ...], int]:
        return (*self.head, *self.tail), self.not_kept


def entry(read: OtherRead) -> OtherReadEntry:
    """One line for the report. Never raises."""
    named = read.where == WHERE_SECONDS
    return {
        "state": read.state,
        "crc": read.crc,
        "count": read.count,
        "differs": read.where,
        "differing_seconds": list(read.seconds) if named else None,
        "differing_seconds_not_named": read.seconds_not_named if named else None,
        "differing_seconds_total": read.seconds_differing,
        "file": read.file,
        "text": read.text,
    }


def block(reads: object, not_kept: object = 0) -> OtherReadsBlock | None:
    """The report's per-track ``other_reads``, or None when no line was printed.

    None, never ``[]``: no line is an older build, a track read without ``-Z``, or
    one whose reads all agreed, which the log does not tell apart. Never raises.
    """
    kept = (
        [read for read in reads if isinstance(read, OtherRead)]
        if isinstance(reads, tuple | list)
        else []
    )
    dropped = not_kept if isinstance(not_kept, int) and not_kept > 0 else 0
    if not kept and not dropped:
        return None
    return {"reads": [entry(read) for read in kept], "not_kept": dropped}
