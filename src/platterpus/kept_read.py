# SPDX-License-Identifier: GPL-3.0-only
"""When the read a track's files carry began: the fork's ``Kept read began:``.

**Why this exists.** cyanrip's ``Elapsed:`` says how long a track took, never
when. Under ``-Z`` the read whose samples a track's files carry can be any of its
passes, so a log that supersedes a track (our securing pass, the verified-read
chase) had no read time to stand on. The fork's ``.27`` adds one line per audio
track, directly below ``Elapsed:``, in UTC, in ISO 8601
(``cyanrip@709337a:src/cyanrip_log.c:670-679``; the formatter is
``crip_iso8601_utc``, ``cyanrip@709337a:src/utils.h:278-284``, which writes
``strftime("%Y-%m-%dT%H:%M:%SZ")``)::

    Kept read began:    2026-10-21T09:23:27Z

Their round 36 lap 4 S13 proposed it, our round 36 lap 3 S6 accepted it as given,
and their lap 7 S5 says it is built (``5062bd5``). Without ``-Z`` it is the one
read; under ``-Z`` the newest read of the spool kept. **A data track prints none,
and neither does a track whose time could not be converted** (their source prints
no line rather than one nobody agreed), so an absent line is never "no read".

The same instant joins the ``--diagnostics`` record as ``kept_read_began`` at
schema ``cyanrip-diagnostics/11`` (their lap 7 S15), read by
:mod:`platterpus.record_track_v11`. Its spelling there is not built yet, so the
record's reader also takes an explicit UTC offset: the record's other instants,
``started_at`` and ``finished_at``, are local time written with a ``±HH:MM``
offset (``crip_iso8601_now``, ``cyanrip@709337a:src/utils.h:255-270``). The log's
reader takes exactly the form the source prints.

**One reader of the instant, two callers** (the log parser and the record
reader), so the two cannot disagree about what a well-formed value is.
Pure, Qt-free, never raises.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Final

#: The value cyanrip's log prints, and nothing looser: four-digit year, two-digit
#: fields, ``T``, a trailing ``Z``. Bounded, so it is linear on any input.
LOG_INSTANT: Final[re.Pattern[str]] = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})T(?P<time>\d{2}:\d{2}:\d{2})Z"
)

#: The record's form: the log's, or the same instant with a ``±HH:MM`` offset,
#: which the record's other two instants carry. Seconds only, as both write.
RECORD_INSTANT: Final[re.Pattern[str]] = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})T(?P<time>\d{2}:\d{2}:\d{2})"
    r"(?P<zone>Z|[+-]\d{2}:\d{2})"
)

#: The states a track's kept-read time can be in, in the report and the parse.
#: ``read``: a well-formed instant, normalised to UTC.
READ: Final[str] = "read"
#: No line (an older build, a data track, a time the ripper could not convert)
#: or no key in the record (``/10`` and earlier). Never "no read".
NOT_PRESENT: Final[str] = "not_present"
#: A line or a key that IS there, holding a value we cannot read as an instant.
#: The value is not reported as a time; the parser logs it.
UNRECOGNISED: Final[str] = "unrecognised"

#: Every state :func:`instant_state` and the parser can produce.
STATES: Final[frozenset[str]] = frozenset({READ, NOT_PRESENT, UNRECOGNISED})

#: A value longer than this is not an instant whatever it holds, and is refused
#: before any parsing (the record is external input).
_MAX_VALUE_CHARS: Final[int] = 40


def began_instant(value: str, *, offset_allowed: bool = False) -> str | None:
    """``value`` as a UTC instant, ``YYYY-MM-DDTHH:MM:SSZ``, or ``None``. Pure.

    ``offset_allowed`` is the record's reader: a ``±HH:MM`` zone is converted to
    UTC. The log's reader leaves it False, so a line in any other form than the
    one cyanrip prints reads as unrecognised rather than as a time we guessed.

    The fields are checked as a calendar date and a clock time, not only as digits:
    ``2026-13-45T25:61:00Z`` has the shape and is not an instant. Never raises.
    """
    if not isinstance(value, str) or len(value) > _MAX_VALUE_CHARS:
        return None
    pattern = RECORD_INSTANT if offset_allowed else LOG_INSTANT
    match = pattern.fullmatch(value.strip())
    if match is None:
        return None
    zone = match.groupdict().get("zone") or "Z"
    # `fromisoformat` takes `Z` from Python 3.11, which is the floor
    # (`pyproject.toml`), and refuses an impossible date or time with ValueError.
    text = f"{match.group('date')}T{match.group('time')}{zone}"
    try:
        when = datetime.fromisoformat(text)
    except ValueError:
        return None
    if when.tzinfo is None:  # unreachable with the patterns above; kept honest
        return None
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def instant_state(value: object, *, offset_allowed: bool = False) -> tuple[str, str]:
    """``(state, instant)`` for one value; ``instant`` is ``""`` unless ``read``.

    A value that is not a string, or does not read as an instant, is
    :data:`UNRECOGNISED`: something was said, and we could not read it. Absence is
    the caller's to decide, since only it knows whether the line or key was there.
    """
    if not isinstance(value, str):
        return UNRECOGNISED, ""
    instant = began_instant(value, offset_allowed=offset_allowed)
    return (READ, instant) if instant is not None else (UNRECOGNISED, "")
