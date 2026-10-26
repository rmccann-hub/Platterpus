# SPDX-License-Identifier: GPL-3.0-only
"""Which limit stopped a ``-Z`` secure re-read: the repeat limit, or our time limit.

**Why this exists.** cyanrip's ``-Z N`` reads a track again and again until N + 1
reads agree. Every build stops trying at the repeat limit (``-r``), and the log
says so: ``Done; (repeat limit of 3 reads reached; at most 2 reads agreed)``, and
in the track block ``Secure re-read:  did NOT converge after 3 reads (repeat
limit hit)``. The cyanrip fork PROPOSES a second limit, ``--reread-time-limit
SECONDS`` (their round 36 lap 10 S11,
``cyanrip@52501ed:docs/handshake/round-36-lap-10.md``; not built, and Platterpus
does not send the option): after each whole-track read of a track that has not
converged, once its reads have taken SECONDS or more, no further read starts. Its
log shapes, verbatim from S11::

    Re-read limit:  600 s a track, checked between whole-track reads
    Done; (time limit of 600 s reached after 4 reads; at most 2 reads agreed)
      Secure re-read:  did NOT converge after 4 reads (time limit of 600 s reached)

The first is a disc header line below ``Retry limit:``, printed only when the
option is given. The second can carry the repeat limit's two clauses as they are
(``; last read %08X, not kept`` and ``; kept %08X, read %i time%s, which
AccurateRip matches at confidence %i``), which the parser already reads.

**The two limits mean different things, and the difference is the point.** A
track stopped at the repeat limit made N reads that did not agree enough: a fact
about how the drive read it. A track stopped at the time limit made as many reads
as WE allowed time for, and can stop after a single read, with nothing to agree
with: a fact about the limit we set, never about the disc. Both are "did not
converge", and the verdict stays exactly that (the parser's ``_SECURE_DONE_FAIL``
reads both as not converged, in the fail-safe direction). What this module adds
is WHICH limit, so the report and the EAC-layout log can say "stopped at our time
limit" instead of describing reads that disagreed.

**What the parser hands here.** Only text it has already claimed: a line its
``_SECURE_DONE_FAIL`` matched, the text of a ``Secure re-read:`` row it read as
not converged, and the value of a ``Re-read limit:`` line. So the patterns here
are FRAGMENT patterns, searched inside a claimed line, and a reworded clause
costs the detail, never the verdict.

Pure, Qt-free, never raises. Imports nothing from the parser, so the parser and
:mod:`platterpus.parsers.rip_log` can take the dataclass from here without a
cycle.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Final

from platterpus import diagnostics
from platterpus.safe_int import int_or_none

log = logging.getLogger(__name__)

#: The repeat limit (``-r``), which every build has.
STOPPED_BY_REPEAT_LIMIT: Final[str] = "repeat_limit"
#: The fork's proposed ``--reread-time-limit`` (round 36 lap 10 S11).
STOPPED_BY_TIME_LIMIT: Final[str] = "time_limit"
STOPPED_BY: Final[frozenset[str]] = frozenset(
    {STOPPED_BY_REPEAT_LIMIT, STOPPED_BY_TIME_LIMIT}
)

#: States of the ``Re-read limit:`` header line. ``read``: the seconds are known.
#: ``unrecognised``: the line is there in a wording this build does not know,
#: its value kept. ``not_present``: no line, which is every rip that did not set
#: the limit and every build before it. The last two are spelled as
#: ``parsers.rip_log``'s drive-fact states, so one word means one thing in the
#: report's ``rip`` block.
TIME_LIMIT_READ: Final[str] = "read"
TIME_LIMIT_UNRECOGNISED: Final[str] = "unrecognised"
TIME_LIMIT_NOT_PRESENT: Final[str] = "not_present"
TIME_LIMIT_STATES: Final[frozenset[str]] = frozenset(
    {TIME_LIMIT_READ, TIME_LIMIT_UNRECOGNISED, TIME_LIMIT_NOT_PRESENT}
)

# `\d{1,7}` seconds is a little over 115 days, far past any limit a person sets;
# the option takes a whole number from 1. Every number is bounded, so each
# pattern is linear on any input (`tests/test_regex_bounded_time.py`).
_TIME_LIMIT: Final[re.Pattern[str]] = re.compile(
    r"\btime limit of (?P<seconds>\d{1,7}) s reached\b"
)
# `repeat limit of 3 reads reached`, the older `hit repeat limit of 5`, and the
# track block's bare `(repeat limit hit)`, which names no count.
_REPEAT_LIMIT: Final[re.Pattern[str]] = re.compile(
    r"\brepeat limit\b(?: of (?P<limit>\d{1,6})\b)?"
)
# How many reads were made, where the line says: `after 4 reads`.
_AFTER_READS: Final[re.Pattern[str]] = re.compile(
    r"\bafter (?P<reads>\d{1,6}) reads?\b"
)
# The `Re-read limit:` value: the seconds first, then whatever the fork says
# about when the limit is checked. Only the start is read, so a reworded trailer
# keeps the seconds.
_TIME_LIMIT_VALUE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<seconds>\d{1,7}) s a track\b"
)

#: An unrecognised ``Re-read limit:`` value is kept, its head and tail, the cut
#: counted (`diagnostics.bounded_chars`).
_VALUE_HEAD: Final[int] = 80
_VALUE_TAIL: Final[int] = 40


@dataclass(frozen=True)
class RereadLimitStop:
    """WHICH limit stopped a ``-Z`` re-read that did not converge.

    ``kind`` is one of :data:`STOPPED_BY`. ``time_limit_seconds`` is the limit
    the line names, for the time limit only, and ``None`` for a zero the option
    cannot take. ``repeat_limit_reads`` is the ``-r`` count the repeat-limit line
    names, for the repeat limit only, and ``None`` where it names none (the
    block's ``(repeat limit hit)``). ``reads`` is how many reads were made, where
    the line says ``after N reads``.
    """

    kind: str
    time_limit_seconds: int | None = None
    repeat_limit_reads: int | None = None
    reads: int | None = None


def limit_stop(claimed: str) -> RereadLimitStop | None:
    """Which limit a claimed ``-Z`` verdict names, or ``None``.

    ``claimed`` is a line the parser has already read as a not-converged verdict
    (see the module docstring). ``None`` when it names neither limit, or both: a
    contradiction is not resolved in either direction, since picking one would be
    us deciding which limit the ripper meant. Pure; never raises.
    """
    timed = _TIME_LIMIT.search(claimed)
    counted = _REPEAT_LIMIT.search(claimed)
    after = _AFTER_READS.search(claimed)
    reads = (
        int_or_none(after.group("reads"), field="cyanrip -Z reads made")
        if after
        else None
    )
    if timed and counted:
        log.warning(
            "cyanrip log: a -Z verdict names both the time limit and the repeat "
            "limit; recording neither: %r",
            diagnostics.bounded_chars(claimed, head=60, tail=60),
        )
        return None
    if timed:
        seconds = int_or_none(timed.group("seconds"), field="cyanrip -Z time limit")
        return RereadLimitStop(
            kind=STOPPED_BY_TIME_LIMIT,
            time_limit_seconds=seconds if seconds else None,
            reads=reads,
        )
    if counted:
        limit = counted.group("limit")
        return RereadLimitStop(
            kind=STOPPED_BY_REPEAT_LIMIT,
            repeat_limit_reads=(
                int_or_none(limit, field="cyanrip -Z repeat limit") if limit else None
            ),
            reads=reads,
        )
    return None


def combined(buffered: RereadLimitStop | None, row: RereadLimitStop) -> RereadLimitStop:
    """The track block row's limit, with what the ``Done;`` line added to it.

    The row wins, as the parser's verdict does: it is the one form whose track is
    not in question. But the two lines state different halves of one fact (the
    ``Done;`` line names the repeat limit's count, the row only ``(repeat limit
    hit)``), so when both name the SAME limit, a number the row leaves unstated
    is taken from the line. When they name different limits, the row's stands
    alone. Pure.
    """
    if buffered is None or buffered.kind != row.kind:
        return row
    return RereadLimitStop(
        kind=row.kind,
        time_limit_seconds=_first(row.time_limit_seconds, buffered.time_limit_seconds),
        repeat_limit_reads=_first(row.repeat_limit_reads, buffered.repeat_limit_reads),
        reads=_first(row.reads, buffered.reads),
    )


def _first(preferred: int | None, fallback: int | None) -> int | None:
    return preferred if preferred is not None else fallback


def time_limit_state(value: str) -> tuple[str, int | None, str]:
    """Read a ``Re-read limit:`` value as ``(state, seconds, text)``.

    ``600 s a track, checked between whole-track reads`` → ``("read", 600, "")``.
    Any value that does not begin with a whole number of seconds from 1 and ``s a
    track`` → ``("unrecognised", None, <the value, bounded>)``, and a warning in
    the log: the option takes a whole number from 1, so a zero is not a limit we
    can report. ``not_present`` (no line) is the caller's to decide.

    Pure apart from that warning; never raises.
    """
    text = value.strip()
    match = _TIME_LIMIT_VALUE.match(text)
    seconds = (
        int_or_none(match.group("seconds"), field="cyanrip Re-read limit")
        if match
        else None
    )
    if seconds:
        return TIME_LIMIT_READ, seconds, ""
    kept = diagnostics.bounded_chars(text, head=_VALUE_HEAD, tail=_VALUE_TAIL)
    log.warning(
        "cyanrip's Re-read limit: line reads %r, a wording this build does not "
        "recognise; recorded as unrecognised with the value kept",
        kept,
    )
    return TIME_LIMIT_UNRECOGNISED, None, kept


def stopped_by_time_limit(stop: object) -> bool:
    """True when ``stop`` (a track's ``secure_rerip_limit_stop``) is our time limit.

    False for the repeat limit and for ``None``, so every log filed so far, none
    of which names a time limit, reads as before. Never raises.
    """
    return getattr(stop, "kind", None) == STOPPED_BY_TIME_LIMIT
