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
