"""Regression tests for the v0.5.8 QThread-teardown SIGABRT.

The crash, stated precisely (reproduced before any of it was fixed):

1. A worker blocked in a subprocess call cannot observe ``QThread.quit()`` —
   ``quit()`` posts to a thread's event loop, and a thread inside
   ``communicate()`` never returns to its loop. ``workers.stop_thread`` gives up
   after a short wait and **abandons** the thread, retaining a reference in a
   module-level list so the garbage collector can't destroy a running
   ``QThread`` (which Qt treats as fatal).
2. That retention is real but only lasts as long as the module. **CPython clears
   module globals during interpreter shutdown**, so a normal exit drops the last
   reference to a still-running ``QThread``, ``~QThread()`` runs, and Qt calls
   ``qFatal()`` → ``abort()`` → ``SIGABRT``.

**These have to run in a child process.** The failure mode is the interpreter
aborting, which would take the test runner with it — an in-process test cannot
observe "did this exit cleanly?" because a failure means there is nothing left to
report. So each test spawns a child, lets it exit, and asserts on its status.

Verified before/after: against the pre-fix code, the abort test child exits
**-6 / 134 (SIGABRT)** and prints ``QThread: Destroyed while thread
'DiscInfoWorker' is still running``. With ``hard_exit`` wired into the exit paths
it exits **0**.
"""

from __future__ import annotations

import signal
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[1]

# A thread that ignores quit(), standing in for one blocked in a container exec.
# Sleeping inside run() never returns to the event loop, which is exactly why
# quit() cannot reach it.
_CHILD_PREAMBLE: str = """
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

class Uninterruptible(QThread):
    def run(self):
        QThread.msleep(30_000)

app = QApplication(sys.argv)
thread = Uninterruptible()
thread.setObjectName("DiscInfoWorker")
thread.start()
QThread.msleep(200)          # let it get properly into run()
app.processEvents()

from platterpus.workers import stop_thread, abandoned_thread_count
stop_thread(thread, None, wait_ms=200)
assert thread.isRunning(), "the stand-in thread stopped; the test proves nothing"
assert abandoned_thread_count() == 1, "stop_thread did not abandon the thread"
del thread                    # the module global is now the only reference
"""


def _run_child(body: str, timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
    """Run a child interpreter with the repo importable, and return its result."""
    script = textwrap.dedent(_CHILD_PREAMBLE) + textwrap.dedent(body)
    return subprocess.run(  # noqa: S603 — our own generated script
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=REPO_ROOT,
        check=False,
    )


def _describe(result: subprocess.CompletedProcess[str]) -> str:
    code = result.returncode
    signal_name = ""
    if code < 0:
        try:
            signal_name = f" ({signal.Signals(-code).name})"
        except ValueError:  # pragma: no cover — unknown signal number
            signal_name = " (unknown signal)"
    return (
        f"exit={code}{signal_name}\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )


def _aborted(result: subprocess.CompletedProcess[str]) -> bool:
    """True when the child died of SIGABRT.

    Reported as a negative return code on POSIX; 134 when a shell layer
    translates it. Accept both so the test is not sensitive to that detail.
    """
    return result.returncode in (-signal.SIGABRT, 134)


def test_exiting_with_an_abandoned_thread_does_not_abort() -> None:
    """The crash itself: process exit must not destroy a live QThread.

    This is the test that fails against the pre-fix code. `exit_now_if_threads_
    abandoned` is what makes it pass — it leaves the process before interpreter
    shutdown can clear the retention list.
    """
    result = _run_child("""
        from platterpus import hard_exit
        # Exactly what app.main() now does after app.exec() returns.
        hard_exit.exit_now_if_threads_abandoned(0)
        # Only reached if the guard decided teardown was safe, which it must not
        # have here — fail loudly rather than exiting 0 for the wrong reason.
        sys.exit("guard did not fire despite an abandoned running thread")
    """)
    assert not _aborted(result), (
        "exiting with an abandoned running QThread aborted the process — the "
        "v0.5.8 crash. Interpreter shutdown cleared workers._abandoned_threads, "
        "dropping the last reference to a running QThread.\n" + _describe(result)
    )
    assert result.returncode == 0, _describe(result)
    assert "Destroyed while thread" not in result.stderr, _describe(result)


def test_the_abort_is_real_without_the_guard() -> None:
    """Prove the detector isn't vacuous: without the guard, the child DOES abort.

    Without this, `test_exiting_with_an_abandoned_thread_does_not_abort` could
    pass because the scenario never actually reproduces the crash — the same
    vacuity trap that has bitten this suite before. If Qt ever stops treating
    this as fatal, this test fails and tells us the other one has stopped
    proving anything.
    """
    result = _run_child("""
        # No guard: just return from the script, letting the interpreter shut
        # down with a running QThread retained only by the module global.
        pass
    """)
    assert _aborted(result) or "Destroyed while thread" in result.stderr, (
        "expected the unguarded child to abort (or at least warn) — if it now "
        "exits cleanly, the guarded test above no longer proves anything and "
        "this scenario needs rebuilding.\n" + _describe(result)
    )


def test_hard_exit_flushes_the_log_before_leaving() -> None:
    """os._exit skips flushing, which would truncate the log that explains why.

    Asserted through a real file handler in a child process, because the point is
    what survives an `os._exit` — something an in-process test cannot observe.
    """
    result = _run_child("""
        import logging, tempfile, pathlib
        log_path = pathlib.Path(tempfile.gettempdir()) / "platterpus-flush-probe.log"
        log_path.unlink(missing_ok=True)
        handler = logging.FileHandler(log_path)
        # A big buffer would normally hold this until interpreter shutdown, which
        # os._exit never reaches.
        logging.getLogger("platterpus").addHandler(handler)
        logging.getLogger("platterpus").setLevel(logging.INFO)
        logging.getLogger("platterpus").info("MARKER-BEFORE-EXIT")
        print(log_path)
        from platterpus import hard_exit
        hard_exit.exit_now_if_threads_abandoned(0)
    """)
    assert result.returncode == 0, _describe(result)
    log_path = Path(result.stdout.strip().splitlines()[-1])
    assert log_path.is_file(), _describe(result)
    contents = log_path.read_text(encoding="utf-8", errors="replace")
    log_path.unlink(missing_ok=True)
    assert "MARKER-BEFORE-EXIT" in contents, (
        "the log was not flushed before os._exit, so the tail of the log — the "
        f"part saying why we exited — was lost. Log held: {contents!r}"
    )


def test_the_word_detach_is_gone_from_thread_handling() -> None:
    """ "Detach" describes an operation Qt does not have.

    There is no API that severs Python ownership from C++ lifetime, and the word
    is what invited dropping the reference in the first place. The thread-handling
    module must say "abandon".

    Checks **code and log messages**, not prose: the module legitimately explains
    *why* the word is banned, and a naive line scan flags that explanation — the
    test would then be asserting against its own documentation. Comments and
    docstrings are therefore tokenised out first, and the log-message text is
    checked separately, since that is user-visible and was the misleading part.
    """
    import io
    import tokenize

    path = REPO_ROOT / "src" / "platterpus" / "workers" / "__init__.py"
    source = path.read_text(encoding="utf-8")

    # Everything that is not a comment or a string literal — i.e. identifiers,
    # keywords and operators. A helper named `_detach_thread` would show up here.
    code_tokens: list[str] = []
    message_strings: list[str] = []
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    for token in tokens:
        if token.type == tokenize.COMMENT:
            continue
        if token.type == tokenize.STRING:
            # Docstrings are prose; a string passed to log.* is user-visible text.
            # Keep the short ones (log messages) and drop the long ones (docs).
            if len(token.string) < 400:
                message_strings.append(token.string)
            continue
        code_tokens.append(token.string)

    in_code = [t for t in code_tokens if "detach" in t.lower()]
    in_messages = [s for s in message_strings if "detach" in s.lower()]
    assert not in_code, (
        "thread handling still uses 'detach' as an identifier, an operation Qt "
        f"does not have: {in_code}"
    )
    assert not in_messages, (
        "a log message still says 'detach' — that wording is what made the code "
        f"look like it was doing something safe: {in_messages}"
    )


# --- Findings from the 2026-07-29 threading audit ------------------------------


def test_close_event_stops_the_rip_thread() -> None:
    """`closeEvent` must stop `_rip_thread`, not only cancel the rip worker.

    The audit's critical finding, reproduced to exit 134 before the fix: the rip
    QThread is parented to the window, so leaving it running means `~QMainWindow`
    destroys a live QThread. The usual net does not catch it either —
    `worker.finished → thread.quit` is a *queued* connection to the GUI thread, so
    once `app.exec()` has returned that `quit()` is never delivered and even a
    cleanly-finished worker leaves its thread spinning.

    Asserted against the **source of closeEvent**, deliberately. The obvious
    behavioural test would build a window and close it — but `tests/conftest.py`'s
    window fixture stops `_rip_thread` itself, which is exactly why the real gap
    went unnoticed for so long. A test that inherits that helper cannot see this.
    """
    import inspect

    from platterpus.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow.closeEvent)
    assert "_rip_thread" in source, (
        "closeEvent does not stop _rip_thread. Closing the window mid-rip will "
        "destroy a running QThread and abort. Note the test-suite's "
        "stop_window_threads helper stops it for tests, so no window fixture "
        "will reveal this — that is why this test reads the source."
    )


def test_the_uninstall_path_checks_before_returning() -> None:
    """`--uninstall` must not return into interpreter shutdown unguarded.

    Its worker shells out to podman/dnf with an 1800 s step timeout and a cancel
    flag that is only polled *between* steps, so closing mid-teardown reliably
    abandons a running thread — the v0.5.8 mechanism on a path the first fix did
    not cover.
    """
    import inspect

    from platterpus import app as app_module

    source = inspect.getsource(app_module.main)
    uninstall_block = source.split("if args.uninstall:", 1)
    assert len(uninstall_block) == 2, "the --uninstall branch moved; update this test"
    # Only look at the branch itself, up to the next top-level statement.
    branch = uninstall_block[1].split("\n    # Bringing up the adapters", 1)[0]
    assert "exit_now_if_threads_abandoned" in branch, (
        "the --uninstall branch returns from main() without the abandoned-thread "
        "check, so a mid-teardown close will abort at interpreter shutdown"
    )


def test_a_finished_abandoned_thread_stops_forcing_a_hard_exit() -> None:
    """The retention list must not latch, or os._exit becomes the normal exit.

    One call site abandons unconditionally (a rescan superseding an in-flight disc
    probe waits 0 ms), and the list was append-only — so a single mid-probe rescan
    made every later quit skip teardown for the rest of the session, and `atexit`
    never ran. Pruning finished entries restores "skip teardown only when it is
    genuinely unsafe".
    """
    from platterpus import workers

    class _FinishedThread:
        """Stands in for an abandoned thread whose blocked step has returned."""

        def isRunning(self) -> bool:
            return False

    class _RunningThread:
        def isRunning(self) -> bool:
            return True

    original = list(workers._abandoned_threads)
    try:
        workers._abandoned_threads[:] = [_FinishedThread()]  # type: ignore[list-item]  # minimal stand-in, not a real QThread
        assert workers.abandoned_thread_count() == 0, (
            "a finished abandoned thread still counts, so the hard exit fires on "
            "every quit for the rest of the session"
        )

        workers._abandoned_threads[:] = [_FinishedThread(), _RunningThread()]  # type: ignore[list-item]  # as above
        assert workers.abandoned_thread_count() == 1, (
            "pruning dropped a thread that is still RUNNING — that reference is "
            "the only thing stopping Qt destroying it"
        )
    finally:
        workers._abandoned_threads[:] = original


# --- Rip-path audit findings, 2026-07-29 --------------------------------------


def test_quitting_just_after_cancel_still_stops_the_container_reader() -> None:
    """Cancel then Quit within 5 s must not leave the drive reading.

    On Cancel the host wrapper dies at once (podman does not forward the signal
    into the container), so the pipe EOFs, `_on_rip_finished` clears
    `_rip_thread`, and the only thing left that would kill the in-container reader
    is the five-second force-stop rescue. `closeEvent` used to disarm that timer
    *before* `_stop_rip_on_shutdown` ran, and that method returned early when
    `_rip_thread is None` — so quitting inside the window left the reader ripping
    with no in-app recovery, and the physical eject button is ignored while a read
    holds the device.

    Two properties, both read from the source because the behaviour needs a live
    drive to exercise: the shutdown stop must consider a *pending* force-stop, and
    `closeEvent` must disarm the timer only after consulting it.
    """
    import inspect

    from platterpus.ui.main_window import MainWindow
    from platterpus.ui.main_window_rip import RipMixin

    shutdown = inspect.getsource(RipMixin._stop_rip_on_shutdown)
    assert "_force_stop_timer.isActive()" in shutdown, (
        "_stop_rip_on_shutdown only checks _rip_thread, so a cancelled rip whose "
        "container reader is still alive is skipped entirely"
    )

    close = inspect.getsource(MainWindow.closeEvent)
    stop_call = close.index("_stop_rip_on_shutdown")
    disarm = close.index("_force_stop_timer.stop()")
    assert disarm > stop_call, (
        "closeEvent disarms the force-stop timer BEFORE _stop_rip_on_shutdown "
        "reads it, so the one signal that the drive may still be reading is "
        "destroyed before it can be acted on"
    )


def test_force_stop_is_recorded_as_a_cancellation_not_a_failure() -> None:
    """Force stop is the user's own choice; the record must not call it a failure.

    Only `_on_rip_cancel` set `_rip_cancelled`, so pressing Force stop on its own
    — the button is enabled for the whole rip — produced "Rip failed.", an
    `outcome.status` of "failed" in the JSON report, an
    `*** INCOMPLETE RIP (failed) ***` banner in the checksum-signed log, and a
    failure notification.
    """
    import inspect

    from platterpus.ui.main_window_rip import RipMixin

    source = inspect.getsource(RipMixin._do_force_stop)
    assert "_rip_cancelled = True" in source, (
        "_do_force_stop does not mark the rip cancelled, so a deliberate user "
        "stop is permanently recorded as a rip failure in the report and the log"
    )
