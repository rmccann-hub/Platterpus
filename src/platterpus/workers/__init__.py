"""Background workers that drive the adapters off the GUI thread.

Each worker is a `QObject` instance the main thread constructs and
then moves to a `QThread` via `moveToThread()`. Signals carry results
back to the GUI thread automatically as queued connections.

The workers are deliberately small — they're glue, not logic. All
parsing and subprocess handling lives in `adapters/` and `parsers/`.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterable

from PySide6.QtCore import QObject, QThread, SignalInstance

log = logging.getLogger(__name__)

# How long a single stop attempt waits before abandoning the thread.
#
# 2000 ms was the old value and it could not cover a **cold** distrobox/podman
# exec, measured at 3.45 s in the v0.5.8 crash — so a worker that was about to
# finish got abandoned anyway. 4 s clears that measurement with margin.
DEFAULT_STOP_WAIT_MS: int = 4_000

# The total budget for stopping EVERY worker on one shutdown.
#
# This is the constant that matters, and it is why the crash brief's advice —
# "raise the per-worker timeout to 10 s" — is not what we did. `closeEvent` makes
# six `stop_thread` calls; a 10 s wait on each is up to a **60 s frozen window**
# on close, and a GUI that stops responding is the failure this project guards
# hardest against (CLAUDE.md, "Never block the GUI thread"). So the budget is
# shared: the *whole* teardown gets 10 s, and each worker gets whatever is left.
# The pathological case degrades to "the last workers are abandoned immediately",
# which is exactly right — abandoning is safe now that exit bypasses teardown.
WORKER_SHUTDOWN_BUDGET_MS: int = 10_000


class ShutdownDeadline:
    """A shared wall-clock budget for stopping several workers in sequence.

    Hand the same instance to every ``stop_thread`` call on one shutdown path and
    the total wait is bounded by the budget rather than by (number of workers ×
    per-worker timeout). Uses a monotonic clock so a system clock adjustment
    mid-shutdown cannot extend or collapse the budget.
    """

    def __init__(self, budget_ms: int = WORKER_SHUTDOWN_BUDGET_MS) -> None:
        self._budget_ms: int = budget_ms
        self._started: float = time.monotonic()

    def remaining_ms(self) -> int:
        """Milliseconds left in the budget; never negative.

        Zero means "don't wait at all" — ``QThread.wait(0)`` still reports
        truthfully whether the thread has already finished, so a worker that
        stopped on its own is still detected rather than needlessly abandoned.
        """
        spent_ms = (time.monotonic() - self._started) * 1000.0
        return max(0, int(self._budget_ms - spent_ms))


# Threads we abandoned because they wouldn't stop promptly on close.
#
# **This list keeps them alive for the rest of the process; it does NOT make
# exiting safe.** It stops the *garbage collector* destroying a running QThread
# mid-session (which Qt treats as fatal), and each entry reaps itself via its own
# finished→quit→deleteLater once its blocked step finally returns. But it is a
# **module global**, and CPython clears module globals during interpreter
# shutdown — so if the process exits while an entry is still running, the last
# reference drops there, `~QThread()` runs on a running thread, and Qt calls
# qFatal() → SIGABRT.
#
# That is the v0.5.8 crash, reproduced: a child process that abandons a running
# QThread and then returns from main() exits **134 (SIGABRT)** with
# `QThread: Destroyed while thread 'DiscInfoWorker' is still running`. The
# retention was already here when it crashed; retention alone was never the fix.
#
# So `abandoned_thread_count()` exists, and every exit path that can run while an
# entry is live MUST hard-exit instead of unwinding — see
# `platterpus.hard_exit.exit_without_teardown`. Never "just drop the reference",
# and never assume this list protects process exit.
# (Module-scoped on purpose: it must outlive the widget that owned the thread.)
_abandoned_threads: list[QThread] = []


def abandoned_thread_count() -> int:
    """How many worker threads were abandoned still-running.

    Non-zero means **interpreter shutdown is unsafe**: see the note on
    `_abandoned_threads`. Exit paths use this to decide whether they must bypass
    teardown rather than unwind through it.
    """
    return len(_abandoned_threads)


def stop_thread(
    thread: QThread | None,
    worker: object | None = None,
    *,
    wait_ms: int | None = None,
    deadline: ShutdownDeadline | None = None,
) -> None:
    """Stop a one-shot worker thread on close WITHOUT a GUI-thread freeze or a
    destroyed-while-running abort.

    The trap this avoids: a widget's ``closeEvent``/``reject`` used to call
    ``thread.wait(N)`` on the GUI thread with N up to 120s. ``quit()`` cannot
    interrupt a ``run()`` blocked inside a subprocess/HTTP call, so that wait
    froze the window for the whole step; and if it timed out, destroying the
    (widget-parented) QThread while it was still running aborted the app.

    So: cancel the worker (if it exposes ``cancel()``), ask the thread to quit,
    and wait only briefly. If it's still running after ``wait_ms`` (a step is in
    flight), **abandon** it — reparent to ``None`` and keep a reference in
    ``_abandoned_threads`` — rather than block longer or let the caller's
    destruction take it down. The abandoned thread finishes its current step and
    reaps itself. Best-effort; never raises. Safe when ``thread`` is ``None`` or
    already stopped.

    **"Abandon", never "detach".** Qt has no detach operation: there is no API
    that severs Python ownership from C++ lifetime, and the word invited exactly
    the mistake of dropping the reference. We keep the reference.

    **Abandoning does not make process exit safe** — see the note on
    ``_abandoned_threads``. A caller that abandons a thread and then lets the
    interpreter shut down will abort. Exit paths must consult
    ``abandoned_thread_count()`` and hard-exit; that is not this function's job,
    because it is also called mid-session (dialog close), where unwinding is
    fine.

    ``wait_ms`` overrides the per-call wait; ``deadline`` shares one budget across
    a whole shutdown (pass the *same* ``ShutdownDeadline`` to every call on that
    path). Give at most one — a deadline wins if both are supplied, because the
    shared budget is the stronger guarantee. With neither, the wait is
    ``DEFAULT_STOP_WAIT_MS``.
    """
    if thread is None:
        return
    # Resolve the wait once, so the log line below reports the number actually
    # used rather than the caller's request.
    if deadline is not None:
        effective_wait_ms = deadline.remaining_ms()
    elif wait_ms is not None:
        effective_wait_ms = wait_ms
    else:
        effective_wait_ms = DEFAULT_STOP_WAIT_MS
    if worker is not None:
        cancel = getattr(worker, "cancel", None)
        if callable(cancel):
            try:
                cancel()
            except Exception:  # noqa: BLE001 — cancel is best-effort
                log.exception("worker cancel() during stop_thread raised; ignored")
    try:
        if not thread.isRunning():
            return
        thread.quit()
        if thread.wait(effective_wait_ms):
            return
        # Still running — a step can't be interrupted by quit(). Abandon it so we
        # neither block the GUI thread longer nor destroy a live QThread.
        log.warning(
            "worker thread %s did not stop within %dms — abandoning it "
            "(reference retained; process exit must now bypass teardown)",
            thread.objectName() or type(thread).__name__,
            effective_wait_ms,
        )
        thread.setParent(None)
        _abandoned_threads.append(thread)
    except Exception:  # noqa: BLE001 — teardown must never crash close
        log.exception("stop_thread failed; ignored")


def start_worker_thread(
    worker: QObject,
    thread: QThread,
    on_started: Callable[[], None],
    *,
    also_quit_on: Iterable[SignalInstance] = (),
) -> None:
    """Move `worker` onto `thread` and wire the standard one-shot lifecycle.

    Every off-thread worker here tore down the same way by hand: the worker's
    `finished` signal quits the thread, the thread's `finished` schedules its own
    `deleteLater`, and the work begins via `on_started` when the thread spins up.
    This wires exactly that and starts the thread, so the lifecycle contract
    lives in one place instead of being copied at every call site.

    Callers create `worker` and `thread` themselves — so a test that patches the
    module's `QThread` (or the worker class) still intercepts — and connect their
    own result/progress/status slots BEFORE calling this. Those handlers are
    connected first, so they run before the thread quits. `also_quit_on` lists
    any *extra* worker signals that should also stop the thread (e.g. a separate
    `failed` signal on workers that report success and failure distinctly).

    This intentionally does NOT cover the persistent MusicBrainz worker (which
    lives for the window's lifetime and is never torn down per-call).
    """
    # Name the worker + thread after the worker class, so log lines and any
    # crash backtrace identify *which* background job is running (a freeze or a
    # "QThread destroyed while running" abort is far easier to diagnose when the
    # thread isn't anonymous). Observability-only and strictly best-effort: it
    # must never break the lifecycle, so a minimal test fake without
    # setObjectName (or anything else odd) is tolerated.
    name = type(worker).__name__
    for obj in (worker, thread):
        setter = getattr(obj, "setObjectName", None)
        if callable(setter):
            try:
                setter(name)
            except Exception:  # noqa: BLE001 — naming is cosmetic, never fatal
                pass
    log.debug("starting worker thread: %s", name)

    worker.moveToThread(thread)
    worker.finished.connect(thread.quit)  # type: ignore[attr-defined]
    for signal in also_quit_on:
        signal.connect(thread.quit)
    thread.finished.connect(thread.deleteLater)
    thread.started.connect(on_started)
    thread.start()
