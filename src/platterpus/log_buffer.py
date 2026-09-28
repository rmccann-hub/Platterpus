"""In-memory capture of this session's log lines, for the rip report.

The `.platterpus.json` rip report is a single self-contained debug record for
one album's rip (maintainer decision, 2026-06-30). Alongside the verdict, CRCs
and timing it embeds the session's log lines — **everything since this launch**
(host setup, dependency probes, the MusicBrainz lookup, the read offset, *this*
rip) — **minus the lines that belong to a different album's rip**. So each
album's report carries the full environmental picture without the noise of other
albums ripped in the same session. In a session long enough to pass the cap it is
the first lines and the most recent ones, with the gap between them marked and
counted in place (``_HEAD_RECORDS``).

This handler is held at **DEBUG always** (see ``logging_setup``), independent of
the "Debug logging" setting — so the embedded report is fully verbose (every
subprocess/probe/parse line) even with default settings. That's cheap: it lives
only in memory and is capped (below). The setting instead governs only how chatty
the on-disk ``log.txt`` is.

The on-disk rolling log (`log.txt`) still records everything at its configured
level, including every rip — it's the catch-all for problems with no rip to
attach to (startup, a dependency install, a crash before any rip ever runs).

This handler is installed once by ``logging_setup.configure_logging`` and reached
by the report builder through the module-level singleton — so no call site has
to thread a buffer reference around.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime

# Cap so a marathon session can't grow the buffer without bound. log.txt on disk
# is the complete record; this in-memory copy only needs to cover a normal
# session.
_MAX_RECORDS: int = 50_000

# **HEAD AND TAIL, not tail-only (2026-09-28, the round-28 Full run).** The cap
# used to evict the oldest lines, silently: the secure re-read rip's report said
# `truncated: true`, began at 01:17:49 for a rip that started at 23:52:41, said
# nothing about how much was missing, and called its scope "this session since
# launch". A tail-only cap drops exactly the launch — the version, the
# environment, the dependency probe, the settings in force — which is the
# context every other line is read against. So the first `_HEAD_RECORDS` lines
# are kept for the whole session, the most recent `_TAIL_RECORDS` slide, and
# every line that falls between them is COUNTED (CLAUDE.md: where output must be
# bounded, keep head and tail and mark any elision with a count). The head is a
# tenth: launch context is a few hundred lines, and the tail is where the rip
# being reported lives.
_HEAD_RECORDS: int = 5_000
_TAIL_RECORDS: int = _MAX_RECORDS - _HEAD_RECORDS


def _when(created: float) -> str:
    """A record's time as the log lines spell it, plus the UTC offset they omit."""
    return (
        datetime.fromtimestamp(created)
        .astimezone()
        .strftime("%Y-%m-%d %H:%M:%S (UTC%z)")
    )


@dataclass(frozen=True)
class BufferedLines:
    """One consistent read of the buffer: the lines, and what they are missing.

    Read under the handler's lock, so ``dropped`` is the count the elision marker
    inside ``lines`` states — a count read a moment later, after more lines had
    been evicted, would disagree with the marker it describes.
    """

    #: The kept lines, in order, other rips' windows removed, with ONE elision
    #: marker at the gap when anything was dropped.
    lines: list[str]
    #: Every record this buffer was handed since launch.
    received: int
    #: Of those, how many it evicted. Always ``received - head - tail``.
    dropped: int
    #: ``"<first> and <last>"`` — when the dropped lines were logged; "" if none.
    dropped_between: str


class SessionLogBuffer(logging.Handler):
    """A logging handler that keeps formatted records in memory for the session.

    Each entry is ``(created_epoch, formatted_line)``. The first ``head`` records
    are kept for the whole session and the most recent ``tail`` slide; what falls
    between is counted in ``dropped`` and its time span remembered, so a reader
    of the report is told exactly what is missing and where to find it.
    """

    def __init__(self, *, head: int = _HEAD_RECORDS, tail: int = _TAIL_RECORDS) -> None:
        super().__init__()
        self._head_limit: int = max(0, head)
        self._head: list[tuple[float, str]] = []
        # `deque(maxlen=…)` evicts its oldest entry on append — the slide.
        self._tail: deque[tuple[float, str]] = deque(maxlen=max(1, tail))
        #: Every record handed to `emit` that formatted, kept or not.
        self.received: int = 0
        #: How many of them were evicted from between the head and the tail.
        self.dropped: int = 0
        self._dropped_first: float | None = None
        self._dropped_last: float | None = None

    @property
    def truncated(self) -> bool:
        """True once anything was dropped. Derived from the count, so the flag and
        the number it summarises cannot disagree."""
        return self.dropped > 0

    def emit(self, record: logging.LogRecord) -> None:
        # A handler must never crash the app at logging time; on a formatting
        # error, defer to handleError (which respects logging.raiseExceptions).
        # `Handler.handle` holds `self.lock` around this call, so the counters and
        # the two containers change together.
        try:
            line = self.format(record)
        except Exception:  # noqa: BLE001 — logging must not raise into callers
            self.handleError(record)
            return
        entry = (record.created, line)
        self.received += 1
        if len(self._head) < self._head_limit:
            self._head.append(entry)
            return
        if len(self._tail) == self._tail.maxlen:
            # The tail is full, so appending evicts its oldest entry: count it,
            # and widen the span the marker will name.
            evicted_at = self._tail[0][0]
            self.dropped += 1
            if self._dropped_first is None:
                self._dropped_first = evicted_at
            self._dropped_last = evicted_at
        self._tail.append(entry)

    def snapshot_excluding(self, windows: list[tuple[float, float]]) -> BufferedLines:
        """The buffer's lines outside ``windows``, with the gap marked and counted.

        ``windows`` are ``(start_epoch, end_epoch)`` spans of *other* rips this
        session; their lines are dropped so an album's report doesn't carry
        another album's rip chatter. Everything else — pre-rip setup, inter-rip
        general activity, and this rip's own lines — is kept, in order.

        The elision marker is OURS, not a record, so no window removes it. Its
        count is the session's: some of the dropped lines may have belonged to
        another album's rip and would have been excluded anyway, and the marker
        says so rather than pretending to a per-album number it cannot know.
        """
        self.acquire()
        try:
            head = list(self._head)
            tail = list(self._tail)
            received = self.received
            dropped = self.dropped
            first, last = self._dropped_first, self._dropped_last
        finally:
            self.release()

        def keep(entries: list[tuple[float, str]]) -> list[str]:
            if not windows:
                return [line for _created, line in entries]
            return [
                line
                for created, line in entries
                if not any(start <= created <= end for start, end in windows)
            ]

        between = ""
        lines = keep(head)
        if dropped and first is not None and last is not None:
            between = f"{_when(first)} and {_when(last)}"
            lines.append(
                f"… [{dropped} line(s) of this session, logged between {between}, "
                "were dropped from Platterpus's in-memory log to bound its size — "
                "some may be other albums' rips, which this report excludes anyway; "
                "log.txt has every one]"
            )
        lines.extend(keep(tail))
        return BufferedLines(
            lines=lines, received=received, dropped=dropped, dropped_between=between
        )

    def lines_excluding(self, windows: list[tuple[float, float]]) -> list[str]:
        """:meth:`snapshot_excluding`'s lines alone — the gap still marked."""
        return self.snapshot_excluding(windows).lines


# Module-level singleton: logging_setup installs exactly one, and the report
# builder reaches it here without it being threaded through every call site.
_BUFFER: SessionLogBuffer | None = None


def get_session_buffer() -> SessionLogBuffer | None:
    """The installed session buffer, or None if logging isn't configured yet."""
    return _BUFFER


def set_session_buffer(buffer: SessionLogBuffer | None) -> None:
    """Record (or clear) the installed buffer. Called by ``logging_setup``."""
    global _BUFFER
    _BUFFER = buffer
