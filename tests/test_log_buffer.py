"""Tests for platterpus.log_buffer (the in-memory session log for the report)."""

from __future__ import annotations

import logging
import re

from platterpus.log_buffer import SessionLogBuffer


def _record(message: str, created: float) -> logging.LogRecord:
    r = logging.LogRecord("t", logging.INFO, __file__, 0, message, None, None)
    r.created = created
    return r


def _buffer() -> SessionLogBuffer:
    b = SessionLogBuffer()
    b.setFormatter(logging.Formatter("%(message)s"))
    return b


def test_captures_formatted_lines_in_order() -> None:
    b = _buffer()
    for i, msg in enumerate(["a", "b", "c"]):
        b.emit(_record(msg, float(i)))
    assert b.lines_excluding([]) == ["a", "b", "c"]
    assert b.truncated is False


def test_lines_excluding_drops_other_rip_windows() -> None:
    b = _buffer()
    b.emit(_record("setup before any rip", 100.0))
    b.emit(_record("other album rip line", 150.0))
    b.emit(_record("inter-rip activity", 200.0))
    b.emit(_record("my rip line", 250.0))
    # Exclude the other album's rip window [140,160]; keep everything else,
    # including general session lines on either side and this rip's own line.
    kept = b.lines_excluding([(140.0, 160.0)])
    assert kept == ["setup before any rip", "inter-rip activity", "my rip line"]


def test_window_bounds_are_inclusive() -> None:
    b = _buffer()
    b.emit(_record("on start edge", 10.0))
    b.emit(_record("on end edge", 20.0))
    assert b.lines_excluding([(10.0, 20.0)]) == []


def test_multiple_windows_excluded() -> None:
    b = _buffer()
    for i in range(6):
        b.emit(_record(f"line{i}", float(i)))
    # Drop lines at t=1 and t=4.
    kept = b.lines_excluding([(1.0, 1.0), (4.0, 4.0)])
    assert kept == ["line0", "line2", "line3", "line5"]


def test_emit_never_raises_on_bad_format(monkeypatch) -> None:
    # A formatting blow-up must be swallowed (handlers can't crash the app).
    b = _buffer()
    monkeypatch.setattr(logging, "raiseExceptions", False)

    def boom(_record: logging.LogRecord) -> str:
        raise ValueError("bad format")

    b.format = boom  # type: ignore[method-assign]
    b.emit(_record("x", 1.0))  # must not raise
    assert b.lines_excluding([]) == []


# --- Head and tail, the gap counted (2026-09-28, the round-28 Full run) --------
#
# `round28fullsecurerereadreport.json` (on the session branch): `debug.truncated`
# was true, its first line was 01:17:49 for a rip that began at 23:52:41, nothing
# said how many lines were missing, and its scope said "this session since
# launch". The buffer evicted its oldest lines silently, so the launch context
# went first and the report could not say what it had lost.

_MARKER = re.compile(r"^… \[(?P<n>\d+) line\(s\) of this session, logged between ")


def _small(head: int, tail: int) -> SessionLogBuffer:
    b = SessionLogBuffer(head=head, tail=tail)
    b.setFormatter(logging.Formatter("%(message)s"))
    return b


def test_a_full_buffer_keeps_its_head_and_tail_and_counts_the_gap() -> None:
    b = _small(head=3, tail=5)
    for i in range(20):
        b.emit(_record(f"line{i}", float(i)))
    snap = b.snapshot_excluding([])
    # The counts add up: everything received is either kept or counted as dropped.
    assert snap.received == 20
    assert snap.dropped == 12
    assert 3 + 5 + snap.dropped == snap.received
    # Both ends survive, in order, with exactly one marker between them.
    assert snap.lines[:3] == ["line0", "line1", "line2"]
    assert snap.lines[-5:] == [f"line{i}" for i in range(15, 20)]
    assert len(snap.lines) == 3 + 1 + 5
    marker = _MARKER.match(snap.lines[3])
    assert marker is not None, snap.lines[3]
    assert int(marker.group("n")) == snap.dropped
    # And it says WHEN: the first and last dropped records are line3 and line14.
    from platterpus.log_buffer import _when

    assert snap.dropped_between == f"{_when(3.0)} and {_when(14.0)}"
    assert snap.dropped_between in snap.lines[3]
    assert b.truncated is True
    # The list-only view carries the same marker.
    assert b.lines_excluding([]) == snap.lines


def test_a_buffer_that_never_filled_has_no_marker_and_says_it_dropped_nothing() -> None:
    b = _small(head=3, tail=5)
    for i in range(8):  # exactly head + tail: full, nothing evicted
        b.emit(_record(f"line{i}", float(i)))
    snap = b.snapshot_excluding([])
    assert snap.dropped == 0 and snap.dropped_between == ""
    assert snap.lines == [f"line{i}" for i in range(8)]
    assert b.truncated is False


def test_the_marker_survives_the_other_rips_windows_and_their_lines_do_not() -> None:
    b = _small(head=3, tail=5)
    for i in range(20):
        b.emit(_record(f"line{i}", float(i)))
    # Another album's rip spanned t=1..2 (in the head) and t=16..17 (in the tail).
    lines = b.lines_excluding([(1.0, 2.0), (16.0, 17.0)])
    assert lines[0] == "line0"
    assert _MARKER.match(lines[1]), lines
    assert lines[2:] == ["line15", "line18", "line19"]


def test_the_default_buffer_keeps_the_launch_through_a_marathon_session() -> None:
    """The round-28 shape at the real sizes: a session past the cap keeps its
    first line — the launch — and says how much of the middle it let go."""
    from platterpus.log_buffer import _HEAD_RECORDS, _MAX_RECORDS, _TAIL_RECORDS

    b = _buffer()
    total = _MAX_RECORDS + 10_000
    b.emit(_record("platterpus 0.6.61 (build 59f4c00) starting", 0.0))
    for i in range(1, total):
        b.emit(_record(f"cyanrip │ progress {i}", float(i)))
    snap = b.snapshot_excluding([])
    assert snap.lines[0] == "platterpus 0.6.61 (build 59f4c00) starting"
    assert snap.lines[-1] == f"cyanrip │ progress {total - 1}"
    assert snap.dropped == total - _HEAD_RECORDS - _TAIL_RECORDS == 10_000
    markers = [line for line in snap.lines if _MARKER.match(line)]
    assert len(markers) == 1 and markers[0].startswith("… [10000 line(s)")
    assert len(snap.lines) == _HEAD_RECORDS + 1 + _TAIL_RECORDS


def test_a_snapshot_taken_while_another_thread_logs_is_consistent() -> None:
    """The rip worker logs from its own thread while the GUI thread builds a
    report, so the snapshot reads the lines and the counts under the handler's
    lock — otherwise the count can describe a later moment than the lines.

    Made deterministic rather than hoped for: the tail below pauses right AFTER it
    has been copied, which is exactly the gap an unlocked read would leave open. A
    writer that gets in during the pause evicts the oldest kept line, so the count
    says it was dropped while the copied lines still hold it — and the first tail
    line stops being the one right after the last dropped line. Under the lock the
    writer waits the pause out, and the two stay the same moment.
    """
    import threading
    import time
    from collections import deque
    from collections.abc import Iterator

    b = _small(head=10, tail=200)
    for i in range(300):  # full, and already dropping
        b.emit(_record(f"line{i}", float(i)))

    class _PauseAfterCopy(deque[tuple[float, str]]):
        """A tail that sleeps once it has been fully iterated (copied)."""

        def __iter__(self) -> Iterator[tuple[float, str]]:
            yield from list(super().__iter__())
            time.sleep(0.02)

    # The one stand-in difference, and the reason for it: it widens a real window
    # (between copying the tail and reading the counters) that the interpreter
    # would otherwise open too rarely for a test to rely on.
    b._tail = _PauseAfterCopy(b._tail, maxlen=b._tail.maxlen)
    stop = threading.Event()
    written = [300]

    def writer() -> None:
        while not stop.is_set():
            b.handle(_record(f"line{written[0]}", float(written[0])))
            written[0] += 1

    thread = threading.Thread(target=writer, daemon=True)
    thread.start()
    try:
        before = written[0]
        # At least ten snapshots, and then more until the writer has been seen to
        # advance, bounded. **The bound replaced a fixed ten on 2026-09-28**, when
        # the floor below failed once under the full parallel suite (`387 > 387`)
        # and passed six of six alone: each snapshot holds the lock for its pause,
        # the main thread re-took the GIL straight after releasing it, and ten
        # snapshots went by with the writer never scheduled. That is a starved
        # writer, not an inconsistent snapshot, so the fix gives it a turn between
        # snapshots rather than weakening either assertion.
        taken = 0
        deadline = time.monotonic() + 10.0
        while taken < 10 or (written[0] == before and time.monotonic() < deadline):
            snap = b.snapshot_excluding([])
            taken += 1
            marker = _MARKER.match(snap.lines[10])
            assert marker is not None and int(marker.group("n")) == snap.dropped
            assert 10 + 200 + snap.dropped == snap.received
            # The first kept tail line follows the last dropped one — the check
            # an unlocked read fails.
            assert snap.lines[11] == f"line{10 + snap.dropped}", (
                snap.lines[11],
                snap.dropped,
            )
            time.sleep(0.001)  # a turn for the writer, outside the lock
        # Floor: the writer really ran alongside the snapshots, so the pauses
        # were raced rather than merely slept through.
        assert written[0] > before, f"the writer never ran across {taken} snapshots"
    finally:
        stop.set()
        thread.join(timeout=5)
