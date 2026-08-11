"""Write the rip report off the GUI thread, newest-wins, at most one at a time.

**Why this exists.** `rip_report.write_report` was called directly from the GUI
thread and its own docstring said that was fine because *"writing a small JSON
file is cheap"*. It is not a small JSON file. The `debug` block alone is budgeted
8 MiB (`rip_report._MAX_EMBEDDED_LOG_BYTES`) and real reports on the maintainer's
machine measure **5.2 MB / 46,594 lines**, of which 4.78 MB is the embedded
session log. Serialising that is ~46 ms and the atomic write (write + `fsync` the
file + `fsync` the parent directory) is another 15-40 ms — measured on fast local
SSD. It happens **six to eight times per rip**, once per post-rip check that
finishes, plus once more on window close.

The `fsync` is the term that does not stay small. The output folder is explicitly
allowed to be a removable disk or a network share — `settings_validation` tells
the user to mount it before ripping — and an `fsync` into a directory that has
just received ~400 MB of FLAC writeback measured **206 ms**. That is a window
that stops repainting in bursts exactly as the verdict is being filled in, which
is when the user is looking at it.

**The design, and why each part.**

* **One worker, not a pool.** Two threads writing one file is a torn report, and
  the whole point of the atomic write is that the artifact is never torn.
* **Newest-wins with a single pending slot.** Every write carries *all*
  accumulated results (see `_write_rip_report`), so a superseded job contains
  strictly less than the one replacing it — dropping it loses nothing. This is
  the same reasoning the 750 ms debounce already relies on, applied one layer
  down where it also bounds memory: at most two report payloads are alive.
* **Ordering is guaranteed by construction.** A single consumer and a
  latest-only slot mean a stale write can never land after a fresher one. With a
  queue or a pool it could, and the file would silently regress to an earlier
  state — the kind of defect that survives because the artifact still parses.
* **A plain daemon thread, not a `QThread`.** Nothing here needs a Qt event
  loop, and `CLAUDE.md`'s threading rules make a daemon thread the lighter of
  the two permitted options: no ownership obligations, and abandoning one at
  exit is safe (`tests/test_qthread_ownership.py` governs the other kind).
* **`flush()` is bounded and real.** Window close must not drop a pending
  report, but it also must not hang on a wedged network mount. It waits for a
  deadline and reports whether the write actually landed, rather than returning
  silently either way.

**What this does NOT do:** it does not make the report smaller, and it does not
change a single byte of what is written. It moves *when* the bytes are written
relative to the event loop. The report's content is assembled by the caller on
the GUI thread — cheap attribute reads — and handed over as a finished payload.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger(__name__)

#: How long `flush()` waits for an in-flight write before giving up. Generous
#: enough for the measured worst case (206 ms into a directory with 400 MB of
#: dirty writeback, plus a superseded job ahead of it) and short enough that a
#: wedged network share cannot hold the window open. Bounded, always: an
#: unbounded wait here is the "Not Responding" this module exists to remove,
#: relocated to the one moment the user is trying to leave.
FLUSH_TIMEOUT_S: float = 5.0


class ReportWriter:
    """Serialises rip-report writes onto one background thread.

    Not a general-purpose executor: the newest-wins slot is only correct because
    every job is a *complete* report, and that is a property of the caller. Do
    not reuse this for work where jobs are increments.
    """

    def __init__(self, name: str = "platterpus-report-writer") -> None:
        self._name: str = name
        #: The one pending job. Replaced, never appended to — see the module
        #: docstring on why dropping the superseded one is lossless.
        self._pending: Callable[[], Path | None] | None = None
        #: Guards `_pending` and `_busy`. Held only for slot swaps, never across
        #: the write itself, so submitting never blocks on a slow disk.
        self._lock: threading.Lock = threading.Lock()
        #: Set whenever a job is waiting OR one is in flight. `flush()` waits on
        #: its *clearing*, so it cannot return while a write is still running.
        self._idle: threading.Event = threading.Event()
        self._idle.set()
        self._wake: threading.Event = threading.Event()
        self._stopping: bool = False
        self._thread: threading.Thread | None = None
        #: Last path written, for tests and for the caller's logging. Written by
        #: the worker, read by the GUI thread only after `flush()` returns.
        self.last_written: Path | None = None

    # --- Public API ---------------------------------------------------------

    def submit(self, job: Callable[[], Path | None]) -> None:
        """Queue ``job``, replacing any job not yet started.

        ``job`` must be a zero-argument callable that performs the whole write
        and returns the path (or None). It runs on the worker thread, so it must
        not touch Qt, a widget, or anything the GUI thread mutates — the caller
        assembles the payload first and closes over the finished values.
        """
        with self._lock:
            # A submit after stop() RESTARTS the writer rather than refusing.
            #
            # The first version latched `_stopping` permanently and logged a
            # warning instead of writing. That is the wrong trade: dropping a
            # report is strictly worse than writing one late, and this is a
            # process-wide singleton, so one close would have disarmed it for
            # everything afterwards — including a late queued signal arriving
            # during teardown, which is exactly when the report matters most.
            # `stop()` ends the *thread*; it does not end the *writer*.
            self._stopping = False
            superseded = self._pending is not None
            self._pending = job
            self._idle.clear()
        if superseded:
            log.debug("report write superseded by a newer one before it started")
        self._ensure_thread()
        self._wake.set()

    def flush(self, timeout: float = FLUSH_TIMEOUT_S) -> bool:
        """Wait for the pending and in-flight writes to finish.

        Returns True when the writer went idle within ``timeout``. False means a
        write was still running — the caller should say so rather than implying
        the report is complete on disk.
        """
        if self._thread is None:
            return True
        deadline = max(0.0, timeout)
        finished = self._idle.wait(deadline)
        if not finished:
            log.warning(
                "rip report still being written after %.1fs; the file on disk may "
                "be one revision behind",
                deadline,
            )
        return finished

    def stop(self, timeout: float = FLUSH_TIMEOUT_S) -> bool:
        """Finish what is pending, then end the worker thread. Bounded.

        Called from `closeEvent`. The thread is a daemon, so an over-running
        write is abandoned rather than holding the process open — and because
        the write is atomic, an abandoned one leaves either the previous
        complete report or the new complete report, never a torn file.

        **Not terminal.** A later :meth:`submit` starts a fresh thread; see the
        note there for why refusing would be the worse failure.
        """
        landed = self.flush(timeout)
        with self._lock:
            self._stopping = True
        self._wake.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=0.5)
        return landed

    # --- The worker ---------------------------------------------------------

    def _ensure_thread(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name=self._name, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while True:
            self._wake.wait(timeout=0.25)
            self._wake.clear()
            with self._lock:
                job = self._pending
                self._pending = None
                stopping = self._stopping
            if job is None:
                # Nothing to do. Publish idle only now — after the slot is
                # confirmed empty — so `flush()` cannot observe idle while a job
                # is sitting in the slot unstarted.
                self._idle.set()
                if stopping:
                    return
                continue
            try:
                self.last_written = job()
            except Exception:  # noqa: BLE001 — a report must never kill its writer
                # `write_report` already swallows OSError and returns None; this
                # catches anything past it. The worker MUST survive, because the
                # next post-rip check will submit again and a dead writer would
                # silently stop producing the one artifact a user uploads.
                log.exception("rip report write failed on the writer thread")


#: The process-wide writer. One file, one writer — a second instance would
#: reintroduce exactly the two-writers-one-file race the single worker removes.
_WRITER: ReportWriter | None = None


def writer() -> ReportWriter:
    """The shared :class:`ReportWriter`, created on first use."""
    global _WRITER
    if _WRITER is None:
        _WRITER = ReportWriter()
    return _WRITER
