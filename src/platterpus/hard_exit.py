"""Exit the process without running interpreter teardown.

Why this module exists — the v0.5.8 SIGABRT, stated precisely:

1. A worker thread blocked in a subprocess call cannot observe ``QThread.quit()``
   (``quit()`` posts to a thread's event loop; a thread inside
   ``communicate()`` never returns to its loop). ``workers.stop_thread``
   therefore gives up after a short wait and **abandons** the thread, keeping a
   reference in a module-level list so the garbage collector can't destroy a
   running ``QThread`` — which Qt treats as fatal.
2. That retention is real but only lasts as long as the module does. **CPython
   clears module globals during interpreter shutdown.** So the moment the process
   exits normally, the last reference to a still-running ``QThread`` drops,
   ``~QThread()`` runs, and Qt calls ``qFatal()`` → ``abort()`` → ``SIGABRT``.
3. Reproduced: a child process that abandons a running ``QThread`` and then
   returns from ``main()`` exits **134 (SIGABRT)**, logging
   ``QThread: Destroyed while thread 'DiscInfoWorker' is still running`` — the
   exact line from the crash report.

The only reliable answer is not to unwind at all. ``os._exit`` skips garbage
collection, C++ destructors and ``atexit`` handlers, so no ``~QThread()`` runs
and no abort is possible. The cost — nothing is cleaned up — is precisely what we
want here: the OS reclaims everything, and any thread still grinding away in a
container exec is killed with the process.

The trade-off is that ``os._exit`` also skips **flushing**, which would silently
truncate the log file that a bug report depends on. So flushing is this module's
other job, and it is done explicitly before exiting.

Used by both exit paths that can run with a live abandoned thread: the
update-relaunch (which is replacing the process anyway) and normal application
exit (``app.main``). Deliberately Qt-free so it can be unit-tested without a
``QApplication``.
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable

log = logging.getLogger(__name__)

# Injection seam so the tests can observe the flush-then-exit ordering without
# actually killing the test runner. Module-level rather than parameters because
# callers should not have to know this is testable.
#
# **A seam nobody uses is not a safety feature.** This existed, and was documented
# as the way to test the exit, and no test ever patched it — so the real
# ``os._exit`` was live in the whole suite. A test that drove the update-relaunch
# path called it, pytest vanished at 76% with status 0, and CI read that as green
# (2026-07-29). The suite now patches this from an *autouse* fixture
# (``tests/conftest.py``, ``hard_exit_calls``) so no test has to know it exists,
# and the stand-in **raises** rather than returning — see below.
_exit_fn: Callable[[int], None] = os._exit


def flush_logs() -> None:
    """Flush stdout, stderr and every logging handler.

    ``os._exit`` does not run ``atexit`` handlers and does not flush buffers, so
    without this the tail of the log — the part that says *why* we exited — is
    lost exactly when someone needs it. Best-effort: a handler that refuses to
    flush must not stop the exit.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (OSError, ValueError):  # closed or detached stream
            pass
    # Walk the root logger's handlers plus every configured logger's, since the
    # file handler that matters may be attached to the package logger rather than
    # the root.
    handlers: list[logging.Handler] = list(logging.getLogger().handlers)
    manager_dict = logging.Logger.manager.loggerDict
    for logger in manager_dict.values():
        if isinstance(logger, logging.Logger):
            handlers.extend(logger.handlers)
    for handler in handlers:
        try:
            handler.flush()
        except (OSError, ValueError):
            pass


def exit_without_teardown(code: int, reason: str) -> None:
    """Flush, then leave the process immediately. Never returns.

    Call this instead of returning from ``main()`` or letting Qt unwind whenever a
    worker thread may still be running — see the module docstring. ``reason`` is
    logged first so the log says why the process stopped short rather than
    looking like it vanished.
    """
    log.info("exiting without teardown (%s); exit code %d", reason, code)
    flush_logs()
    _exit_fn(code)
    # Unreachable with the real ``os._exit``, which never returns. The test
    # stand-in therefore never returns either — it raises — because a stub that
    # falls through would let callers run code that production can never reach, and
    # the caller here is the update-relaunch path whose whole point is that nothing
    # after it happens. (An earlier version of this comment said falling through
    # was "correct"; it is a fidelity gap, not a convenience.)


def exit_now_if_threads_abandoned(code: int) -> None:
    """Hard-exit if any worker thread was abandoned still-running; else return.

    The check is what keeps this from being a blunt instrument: a clean shutdown
    (every worker stopped) unwinds normally, runs ``atexit``, and flushes the way
    Python intends. Only the unsafe case — a live ``QThread`` that interpreter
    shutdown would destroy — skips teardown.
    """
    from platterpus.workers import abandoned_thread_count

    count = abandoned_thread_count()
    if count == 0:
        return
    exit_without_teardown(
        code,
        f"{count} worker thread(s) abandoned still-running; interpreter shutdown "
        "would destroy a live QThread and abort",
    )
