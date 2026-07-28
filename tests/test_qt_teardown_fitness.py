"""The detector: a forced full collection the suite must survive.

**Why this file exists, and why it must not be deleted to make CI green.**

For most of this project's life the suite leaked Qt objects and nobody could
see it. `deleteLater()` does not delete anything by itself — it posts a
`DeferredDelete` event and hands ownership of the C++ object to Qt, and Qt
delivers that event only when the event loop that posted it exits, or when
someone asks for it *by type*. This suite runs no event loop, and neither
`processEvents()` nor a bare `sendPostedEvents()` qualifies. So every window a
fixture "deleted" stayed alive, pinned, with an event queued against it, for the
whole process — hundreds of fully built `MainWindow`s, each with its widget
tree, worker threads, timers and signal graph.

That wreckage was invisible right up until something walked it. On 2026-07-28 a
single `gc.collect()` in an unrelated test (`test_ui_auto_center.py`, testing a
`WeakSet`) started taking the process down with SIGSEGV — and the traceback
pointed at that innocent file, because it was merely the first code to traverse
the graph. Measured at the time: **unmodified `main` segfaulted 5 runs out of
5**; the CI 3.11 leg failed three times in a row.

So the fix could not be "stop collecting". A test suite that only stays up
because nothing ever looks at its garbage is not passing, it is not looking.
This file looks, deliberately, every run:

* It forces a **full, all-generations** collection — the thing that detonated
  the old suite.
* It asserts no Qt worker threads are still running, because a QThread alive at
  destruction is what aborts the process.
* It sorts late alphabetically (``test_q…``) so it runs after most of the files
  that build windows, and `pytest-randomly` moves it around anyway — between
  them, it sees a realistic accumulation.

If this file starts crashing, **do not delete it and do not skip it.** It is
reporting a real use-after-free that a user could hit in a long GUI session. The
teardown machinery it guards lives in `tests/conftest.py`
(`stop_window_threads`, `_join_leaked_qthreads`, `_drain_deferred_deletes`);
`docs/testing.md` §5.w records the measurements and the two "obvious" fixes that
made things worse when applied in the wrong order.
"""

from __future__ import annotations

import gc

from PySide6.QtCore import QCoreApplication, QEvent, QThread
from PySide6.QtWidgets import QApplication


def test_a_forced_full_collection_does_not_crash_the_process(
    qapp: QApplication,
) -> None:
    """Walk every object the suite has accumulated so far. Must not segfault.

    Three passes, because collecting one generation can make the next
    collectable, and because the crash this guards was a race that a single
    pass did not always reach.
    """
    for _ in range(3):
        gc.collect()


def test_no_qt_worker_thread_outlives_the_test_that_started_it(
    qapp: QApplication,
) -> None:
    """No QThread from an earlier test may still be running.

    Destroying a QObject that owns a live QThread aborts the process, and the
    abort surfaces later, somewhere unrelated. `_join_leaked_qthreads` in
    `conftest` is what keeps this true; this asserts the outcome rather than
    trusting the mechanism.

    The current thread is excluded — that is the main thread, which is
    obviously running.
    """
    running = [
        thread
        for thread in _live_qthreads()
        if thread is not QThread.currentThread() and thread.isRunning()
    ]
    assert not running, (
        f"{len(running)} QThread(s) from earlier tests are still running; "
        "destroying their owner will abort the process"
    )


def test_the_deferred_delete_queue_is_drained_between_tests(
    qapp: QApplication,
) -> None:
    """A `deleteLater()` from an earlier test must already have been honoured.

    Draining by type is a no-op when the queue is empty, so if the autouse
    drain in `conftest` is working, asking again destroys nothing. This is a
    weak assertion by construction — it cannot count what was already gone —
    so its real value is that it *exercises* the drain path every run, on
    whatever an earlier test left behind, with the collection above as witness.
    """
    for _ in range(3):
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()


def _live_qthreads() -> list[QThread]:
    """Every QThread Python still has a wrapper for.

    Qt has no public "list all threads" API, so this walks the GC's object
    graph. That is exactly the right lens here: a QThread with no Python
    reference cannot be the one a fixture forgot to join.
    """
    threads: list[QThread] = []
    for obj in gc.get_objects():
        try:
            if isinstance(obj, QThread):
                threads.append(obj)
        except (ReferenceError, RuntimeError):
            # A dead wrapper mid-collection — not a live thread by definition.
            continue
    return threads
