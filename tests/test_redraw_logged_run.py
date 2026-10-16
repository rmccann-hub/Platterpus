"""Tests for `redraw_run.LoggedRun`: the app log's copy of a run of redraws (R14).

Measured 2026-10-14: 231 MB of the 240 MB of filed app logs were cyanrip's
progress redraw at ten a second, and the redraws between those ten were dropped
with no count. The collapse keeps first, a checkpoint every 10 s, and last, and
counts every other redraw in a marker, so nothing is dropped unsaid.
"""

from __future__ import annotations

import re

from hypothesis import given
from hypothesis import strategies as st

from platterpus.redraw_run import (
    CHECKPOINT_SECONDS,
    REDRAW_ELISION_PHRASE,
    LoggedRun,
)

_MARKER = re.compile(
    r"\[platterpus\] … (\d+) " + re.escape(REDRAW_ELISION_PHRASE) + " …"
)


def _drive(lines: list[str], times: list[float]) -> list[str]:
    run = LoggedRun()
    written: list[str] = []
    for line, now in zip(lines, times, strict=True):
        written += run.note(line, now)
    return written + run.close()


def _accounted(written: list[str]) -> int:
    """Redraws written plus redraws counted by a marker."""
    total = 0
    for line in written:
        marker = _MARKER.fullmatch(line)
        total += int(marker.group(1)) if marker else 1
    return total


def test_a_fast_run_writes_first_a_counted_marker_and_last() -> None:
    lines = [f"track 3, progress - {i}%" for i in range(1000)]
    written = _drive(lines, [0.0] * 1000)

    assert written == [
        lines[0],
        f"[platterpus] … 998 {REDRAW_ELISION_PHRASE} …",
        lines[-1],
    ]


def test_a_long_run_writes_a_checkpoint_every_interval() -> None:
    """A freeze or a force-kill must still leave where the read had got to."""
    times = [i * 0.1 for i in range(301)]  # thirty seconds at ten a second
    lines = [f"p {i}" for i in range(301)]
    run = LoggedRun()
    checkpoints = [
        i
        for i, (ln, t) in enumerate(zip(lines, times, strict=True))
        if ln in run.note(ln, t)
    ]

    assert checkpoints[0] == 0
    assert len(checkpoints) >= 3  # 0 s, ~10 s, ~20 s, ~30 s
    gaps = [
        times[b] - times[a] for a, b in zip(checkpoints, checkpoints[1:], strict=False)
    ]
    assert all(gap >= CHECKPOINT_SECONDS for gap in gaps), gaps


def test_short_runs_lose_nothing_and_claim_no_elision() -> None:
    assert _drive([], []) == []
    assert _drive(["a"], [0.0]) == ["a"]
    assert _drive(["a", "b"], [0.0, 0.0]) == ["a", "b"]  # no zero-count marker
    assert _drive(["a", "b", "c"], [0.0, 0.0, 0.0]) == [
        "a",
        f"[platterpus] … 1 {REDRAW_ELISION_PHRASE} …",
        "c",
    ]


def test_a_closed_run_reopens_cleanly() -> None:
    run = LoggedRun()
    run.note("a", 0.0)
    run.note("b", 0.0)
    assert run.close() == ["b"]
    assert run.close() == []
    assert run.note("c", 1.0) == ["c"]


@given(st.lists(st.floats(min_value=0, max_value=0.5), max_size=300))
def test_every_redraw_is_written_or_counted_exactly_once(steps: list[float]) -> None:
    times: list[float] = []
    now = 0.0
    for step in steps:
        now += step
        times.append(now)
    lines = [f"p {i}" for i in range(len(times))]
    written = _drive(lines, times)

    assert _accounted(written) == len(lines)
    if lines:  # the first and the last are always written as themselves
        assert written[0] == lines[0] and written[-1] == lines[-1]
