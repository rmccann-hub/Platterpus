"""Background workers that drive the adapters off the GUI thread.

Each worker is a `QObject` instance the main thread constructs and
then moves to a `QThread` via `moveToThread()`. Signals carry results
back to the GUI thread automatically as queued connections.

The workers are deliberately small — they're glue, not logic. All
parsing and subprocess handling lives in `adapters/` and `parsers/`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable

from PySide6.QtCore import QObject, QThread, SignalInstance

log = logging.getLogger(__name__)

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
    wait_ms: int = 2000,
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
    """
    if thread is None:
        return
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
        if thread.wait(wait_ms):
            return
        # Still running — a step can't be interrupted by quit(). Abandon it so we
        # neither block the GUI thread longer nor destroy a live QThread.
        log.warning(
            "worker thread %s did not stop within %dms — abandoning it "
            "(reference retained; process exit must now bypass teardown)",
            thread.objectName() or type(thread).__name__,
            wait_ms,
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
