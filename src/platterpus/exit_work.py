"""Work that must finish before the process exits, after the window has gone.

**What it is for.** Quitting during a rip must stop the ripper, and stop it so
that its log keeps its footer: cyanrip is sent SIGTERM and given a grace to
finish the read in hand and write the end of its log, and only then, if it still
holds the drive, SIGKILL. cyanrip acts on SIGTERM only once that read returns,
and the rig's drive has been measured taking 20 seconds over one read (our
filed round 15 lap 13 log; the fork's round 30 lap 5 S17 found 11), so the grace
is long. Waiting it out on the GUI thread froze
the window for up to half a minute at the moment the user asked it to go away.

So the window closes at once, and the wait moves here: ``closeEvent`` hands the
stop to :func:`start`, which runs it on a helper thread, and ``app.main`` calls
:func:`wait` after ``app.exec()`` returns and before the process exits. The
window is already gone by then, so no slot can fire into it, and the process
lingers without a window only for as long as the reader takes to let go.

**Why the join, and why it is bounded.** The helper is a daemon thread, so an
interpreter exit that did not wait for it would kill it part-way through
stopping the reader, and leave cyanrip holding the drive after the app has gone
(the 2026-07-01 report). The join is what prevents that. It is bounded by each
job's own budget plus a margin, because the job's subprocesses are themselves
bounded and a wait past that would only hide a hang.

Plain ``threading``, not ``QThread``: the work touches no Qt object, and a
Python thread carries none of ``~QThread()``'s hazards (Critical rule #9).
Never raises.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

log = logging.getLogger(__name__)

#: How long :func:`wait` allows past a job's own budget. The budget bounds the
#: job's steps, but a subprocess started just before the budget ran out still
#: runs for its own timeout, so the join allows a few seconds more.
JOIN_MARGIN_S: Final[float] = 5.0


@dataclass
class _Job:
    """One piece of exit work: its thread, its name, and when it must be done."""

    thread: threading.Thread
    name: str
    deadline: float


_LOCK: Final[threading.Lock] = threading.Lock()
_JOBS: list[_Job] = []


def start(
    work: Callable[[], object],
    *,
    name: str,
    budget_s: float,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    """Run ``work`` on a helper thread that :func:`wait` joins before exit.

    ``work`` must be thread-safe: no Qt, no widgets, no dialogs. It is expected
    to bound itself to ``budget_s``; the join allows that plus
    :data:`JOIN_MARGIN_S`. A failure inside it is logged, never raised.
    """

    def run() -> None:
        try:
            work()
        except Exception:  # noqa: BLE001 — exit work must not die silently
            log.exception("exit work %r failed", name)

    thread = threading.Thread(target=run, name=f"exit-{name}", daemon=True)
    with _LOCK:
        _JOBS.append(_Job(thread, name, clock() + budget_s))
    log.info("exit work %r started, budget %.0fs", name, budget_s)
    thread.start()


def pending() -> int:
    """How many exit jobs are still running."""
    with _LOCK:
        return sum(1 for job in _JOBS if job.thread.is_alive())


def wait(
    *,
    margin_s: float = JOIN_MARGIN_S,
    clock: Callable[[], float] = time.monotonic,
) -> bool:
    """Join every exit job, each up to its deadline plus ``margin_s``.

    Returns ``True`` when every job finished, ``False`` when one was still
    running at its deadline. That one is left to die with the process, and the
    log says which, because the work it was doing is then not known to be done.
    """
    with _LOCK:
        jobs = list(_JOBS)
    finished = True
    for job in jobs:
        remaining = job.deadline + margin_s - clock()
        if job.thread.is_alive():
            log.info(
                "waiting up to %.0fs for exit work %r before the process exits",
                max(remaining, 0.0),
                job.name,
            )
        job.thread.join(timeout=max(remaining, 0.0))
        if job.thread.is_alive():
            finished = False
            log.warning(
                "exit work %r did not finish within its budget; the process exits "
                "without it, so what it was doing is not known to be done",
                job.name,
            )
    with _LOCK:
        _JOBS[:] = [job for job in _JOBS if job.thread.is_alive()]
    return finished
