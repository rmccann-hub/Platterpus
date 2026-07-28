"""Shared pytest fixtures for platterpus's test suite.

Only one QApplication instance can exist per process. The `qapp`
session-scoped fixture guarantees that — tests that need a Qt event
loop, widgets, or the clipboard depend on it; tests that don't, ignore
it.

We force the Qt platform plugin to `offscreen` BEFORE importing any
Qt module, so the suite runs on CI / headless containers without a
real display.
"""

from __future__ import annotations

import os

# Set before any Qt import. Subsequent imports of QtGui/QtWidgets
# inherit this platform choice; widgets are created in-memory and
# never draw to a real display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

# --- Defuse the PySide interpreter-shutdown abort -------------------------
#
# With many QThread-using tests, PySide6 intermittently SIGABRTs during
# interpreter shutdown of the (offscreen) QApplication — a Qt-internal teardown
# race that fires *after* every test has passed and after pytest-cov has written
# coverage. It only flips the exit code, turning a green run red (CI flake). The
# accepted fix: capture pytest's real exit status at session finish, then in
# `pytest_unconfigure` (which runs after results AND coverage are finalized)
# exit the process hard with that status — skipping the crash-prone Qt global
# teardown. This does NOT mask real failures (the captured status is whatever
# pytest computed, including the coverage gate) and does NOT mask a *mid-run*
# abort (that kills the process before sessionfinish, so this never fires —
# which is why the per-test QThread-join backstop below is still essential).


@pytest.hookimpl(hookwrapper=True)
def pytest_sessionfinish(session, exitstatus):  # noqa: ANN001, ANN201
    # Defuse the intermittent PySide interpreter-shutdown SIGABRT (a Qt-internal
    # global-teardown race with offscreen + many QThread tests). We exit the
    # process HARD with the real status at the END of session finish — as a
    # hookwrapper post-`yield`, so this runs AFTER pytest-cov's wrapper has saved
    # the .coverage data file and applied `--cov-fail-under` to
    # `session.exitstatus`. Exiting *here* (the earliest point after results are
    # final) rather than in `pytest_unconfigure` matters: the crash otherwise
    # fires in the gap between session-finish and unconfigure, during pytest's
    # own end-of-session cleanup. Trade-off: pytest-cov's *printed* terminal
    # report is skipped (it prints after this) — but the gate is enforced by the
    # exit code and the .coverage file is written, so `coverage report` shows the
    # numbers anytime. Does NOT mask failures (status is whatever pytest
    # computed: an impossible gate / a failing test still exits non-zero) and
    # does NOT mask a *mid-run* abort (that kills the process before this fires,
    # which is why the per-test QThread-join backstop above stays essential).
    yield
    import os
    import sys

    status = int(session.exitstatus)
    # Print the terminal summary OURSELVES before the hard exit. Without this the
    # `os._exit` below skipped it entirely — a red CI run produced only progress
    # dots, with no failing test names and no tracebacks, and `--durations` was
    # silently useless. Diagnosability is the whole point of a test run
    # (audit finding, 2026-07-28), and the summary is cheap to emit here.
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        try:
            reporter.write_line("")
            reporter.summary_failures()
            reporter.summary_errors()
            reporter.short_test_summary()
            reporter.summary_stats()
        except Exception:  # noqa: BLE001 — reporting must never change the status
            log_ = __import__("logging").getLogger(__name__)
            log_.exception("could not print the pytest summary")
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(status)


def stop_window_threads(window: object) -> None:
    """Join every QThread a MainWindow owns, before it is destroyed.

    **Destroying a QWidget while a QThread it owns is still running aborts the
    process** — a mid-run SIGSEGV during a later test's garbage collection, with
    a traceback pointing at whatever innocent test happened to trigger the GC.
    That is exactly what happened on 2026-07-28: a new test file grew its own
    window fixture that called `deleteLater()` without joining anything, every
    window it made left `_mb_thread` running, and CI segfaulted inside
    `test_ui_auto_center.py` — a file that had nothing to do with it.

    So the joins live here, in one place, and every window fixture calls this.
    A second copy of this logic is a second chance to forget a thread.

    `quit()` is delivered to each thread's own event loop directly (not via a
    queued `finished` → `quit`), so it works even when the test never pumped the
    GUI event loop. Read via `getattr` so a window that never created a given
    thread — or a future one that renames it — degrades to "nothing to join"
    rather than raising during teardown.

    **The daemon threads are joined too, and that is the important half.** An
    earlier version of this helper said they could be left alone because they
    "die with the process and guard their emits". That was wrong in the way that
    mattered: a daemon `threading.Thread` still running when the cyclic garbage
    collector fires *on that thread* — mid-`rglob` in `checksums.py`, in the
    observed case — walks Qt wrappers whose C++ objects the GUI thread is busy
    destroying. The crash lands wherever the collection happened to start, which
    is why it looked like a bug in whichever innocent test triggered it. Guarding
    the *emit* is not enough; the thread must not still be alive.

    Both loops read via `getattr`, so a window that never created a given thread
    — or a future one that renames it — degrades to "nothing to join" rather than
    raising during teardown. Waits are bounded: a wedged worker should slow a
    test down, not hang the suite.
    """
    # Qt worker threads. `quit()` is delivered to each thread's own event loop
    # directly (not via a queued `finished` → `quit`), so it works even when the
    # test never pumped the GUI event loop. ALL SEVEN slots that
    # `main_window_shared.MainWindowShared` declares — the first version of this
    # helper listed four and its docstring already claimed to be the one place a
    # thread could not be forgotten. Three were forgotten on day one.
    for name in (
        "_mb_thread",
        "_dep_check_thread",
        "_disc_info_thread",
        "_drive_list_thread",
        "_rip_thread",
        "_update_thread",
        "_install_thread",
    ):
        thread = getattr(window, name, None)
        # Duck-typed on purpose: many tests put a stand-in (a SimpleNamespace, a
        # `_FakeThread`, a bare object) in these slots, and teardown must not
        # care. Anything without the QThread interface has nothing to join.
        if thread is None or not callable(getattr(thread, "isRunning", None)):
            continue
        try:
            if thread.isRunning():
                thread.quit()
                thread.wait(2000)
        except RuntimeError:
            continue  # the C++ QThread is already gone — nothing to join

    # Plain daemon threads. These have no event loop to quit, so all we can do is
    # wait for them; every one of them is a bounded piece of post-rip work
    # (hashing, verifying, transcoding, moving) that finishes on its own.
    for name in (
        "_post_rip_thread",
        "_ctdb_thread",
        "_flac_verify_thread",
        "_derived_verify_thread",
        "_checksums_thread",
        "_comparison_thread",
        "_library_move_thread",
        "_eject_thread",
        "_force_stop_thread",
    ):
        worker = getattr(window, name, None)
        if worker is None or not callable(getattr(worker, "is_alive", None)):
            continue  # a stand-in, or never started
        try:
            if worker.is_alive():
                worker.join(5.0)
        except RuntimeError:
            continue


# Hold the QApplication in a module global so it is NEVER garbage-collected —
# if Python GCs it at session end, its Qt teardown can SIGABRT (see the
# session-finish hard-exit above). Pinned here, it survives until os._exit.
_HELD_APP: object | None = None


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Return the single QApplication instance for the test session.

    (The interpreter-shutdown SIGABRT this app can trigger during global Qt
    teardown is defused by pinning it in `_HELD_APP` + the `pytest_unconfigure`
    hard-exit above, not by tearing it down here.)
    """
    global _HELD_APP
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    _HELD_APP = app  # pin: never let it be collected
    return app  # type: ignore[return-value]


@pytest.fixture
def process_until(qapp: QApplication):
    """Canonical bounded event-loop pump for worker-thread / queued-signal flows.

    We don't use pytest-qt, so this is how a test drives a flow that does work on
    a worker thread (a dialog's install loop, a window's rip/probe) and reports
    back via queued signals: pump the GUI event loop until a predicate holds (or
    a timeout), delivering those queued slots on the GUI thread. It is always
    BOUNDED — never a bare ``while True``.

    Returns ``pump(predicate, timeout=5.0, step=0.005) -> bool`` (the predicate's
    final value). Use it instead of ``QThread.wait()`` on the GUI thread: a bare
    ``wait()`` blocks the loop, so a queued ``finished``/``quit`` can never be
    delivered — a deadlock (see docs/testing.md and architecture.md §3.2).

    While pumping, the cyclic garbage collector is paused (see below). This is
    the window where a worker thread is churning Qt objects concurrently with the
    GUI thread; a cyclic-GC pass that fires on *any* thread here can finalize a
    QObject off the Qt thread and SIGSEGV the interpreter mid-run under the
    headless ``offscreen`` platform (a real, intermittent CI abort, exit 139 —
    seen in both the e2e rip test and the pending-installs dialog test, hopping
    between Python cells run to run). The ``os._exit`` shutdown hook can't help (a
    mid-run crash never reaches session finish). Pausing only for the pump keeps
    it surgical: refcount freeing still runs throughout, and cyclic collection
    resumes the moment the pump returns, so memory stays bounded. Reentrant/
    nesting-safe: it only re-enables GC if it was enabled on entry.
    """
    import gc
    import time

    def pump(predicate, timeout: float = 5.0, step: float = 0.005) -> bool:
        gc_was_enabled = gc.isenabled()
        gc.disable()
        try:
            deadline = time.monotonic() + timeout
            while not predicate() and time.monotonic() < deadline:
                qapp.processEvents()
                qapp.sendPostedEvents()  # flush queued cross-thread signals too
                time.sleep(step)
            return predicate()
        finally:
            if gc_was_enabled:
                gc.enable()

    return pump


@pytest.fixture(autouse=True)
def _cyclic_gc_paused_during_each_test():
    """Run each test with the cyclic collector off; collect between tests.

    **This is the fix for the suite's long-standing intermittent SIGSEGV**, and
    it generalises a guard the codebase had already reached for twice locally —
    `process_until` pauses the collector around its pump, and the end-to-end rip
    fixture pauses it for a whole test. Both did so for the same reason, written
    in `process_until`'s own docstring: a cyclic-GC pass that fires *on a worker
    thread* while that worker is churning Qt objects, under the headless
    `offscreen` platform, is an observed hard crash.

    The trouble with doing it locally is that the hazard is not local. Platterpus
    runs its post-rip work — hashing, verification, transcoding, the library move
    — on daemon threads, and a collection can begin on *any* thread that trips
    the allocation threshold, at *any* moment. Whichever thread happens to be
    inside the collector when the GUI thread destroys a widget is the one that
    dies, which is why the crash always surfaced in an unrelated file (a
    `gc.collect()` in a dialog test; a `pathlib.rglob` in a checksums worker).

    So: reference counting still runs normally and still frees the overwhelming
    majority of objects the instant they go out of scope. Only *cycle* detection
    is deferred, to a single deterministic point per test — on the main thread,
    **after** the two join fixtures below have stopped every worker, which is the
    one moment when no other thread can be inside the collector.

    Declared FIRST on purpose. Autouse fixtures tear down in reverse setup order,
    so being first here makes this teardown run LAST — after
    `_join_leaked_qthreads` and `_join_leaked_worker_threads` have done their
    work. Move it and the collect happens while workers are still alive, which is
    the bug.

    `tests/test_qt_teardown_fitness.py` is the detector that proves this holds:
    it forces a full collection and asserts no worker survived. Baseline before
    this fixture: 3 crashes in 3 runs. After: 10 clean randomized runs.
    """
    import gc

    was_enabled = gc.isenabled()
    gc.disable()
    try:
        yield
    finally:
        if was_enabled:
            gc.enable()
        # A full `gc.collect()` here would be correct but costs more than it is
        # worth: at ~2,000 tests it more than doubled the suite's runtime.
        # Generation 0 is the cheap one — it reclaims the short-lived cycles a
        # single test creates, which is nearly all of them — and it runs HERE, on
        # the main thread, after the join fixtures below have stopped every
        # worker. The full, all-generations sweep happens once, in
        # `tests/test_qt_teardown_fitness.py`, which is also the detector.
        gc.collect(0)


@pytest.fixture(autouse=True)
def _isolate_drive_profiles(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the drive-profile ledger out of the real user config dir.

    `DriveProfileStore` resolves its path live from `platterpus.paths`, so
    redirecting that constant to a per-test temp file means any window code that
    records a drive fact (the recorder calls `save()`) writes to the sandbox,
    never `~/.config/platterpus/drive_profiles.json`. Mirrors how the suite
    injects `save_config` to avoid touching the real config.toml.
    """
    monkeypatch.setattr(
        "platterpus.paths.DRIVE_PROFILES_PATH", tmp_path / "drive_profiles.json"
    )


@pytest.fixture(autouse=True)
def _join_leaked_qthreads(monkeypatch: pytest.MonkeyPatch):
    """Join any `QThread` a test started but didn't drive to completion.

    Destroying a running `QThread` aborts the whole process (Qt). A test that
    triggers a worker (a dialog's install loop, a window's rip/probe) but returns
    before the thread finishes leaves it running; when the test's widgets are
    GC'd, the child thread is destroyed mid-run → a hard `SIGABRT` that takes
    down the *whole suite*, not just that test. This bit the dependency-install
    work: a stub that returned before the worker finished crashed the run.

    We track every `QThread.start()` during the test, then at teardown — which
    runs BEFORE the test's locals (and their threads) are GC'd — quit + bounded-
    wait any that are still running, pumping the loop so a queued `finished` can
    fire first. Leaking isn't failed (it's a latent abort risk, not a behaviour
    bug, and some daemon-style flows are legitimately in flight) but it's warned
    so a chronically-leaking test gets noticed. The real fix in the test is to
    drive the worker to completion (see `docs/testing.md` — bounded
    `processEvents` pump); this is the backstop that keeps a slip from aborting
    everyone else's tests.
    """
    import warnings

    from PySide6.QtCore import QThread

    started: list[QThread] = []
    original_start = QThread.start

    def tracking_start(self: QThread, *args: object, **kwargs: object) -> None:
        started.append(self)
        return original_start(self, *args, **kwargs)

    monkeypatch.setattr(QThread, "start", tracking_start)
    yield

    leaked = 0
    for thread in started:
        try:
            if not thread.isRunning():
                continue
        except RuntimeError:
            continue  # underlying C++ QThread already deleted — nothing to do
        leaked += 1
        try:
            # quit() acts on the WORKER thread's own event loop, so it doesn't
            # need the GUI thread to pump — and we deliberately do NOT pump
            # processEvents() here: doing so can fire a stale QTimer.singleShot
            # left by a half-destroyed window and segfault (the very hazard the
            # message-box fixture guards). requestInterruption() nudges any
            # cooperative loop; wait() is bounded.
            thread.requestInterruption()
            thread.quit()
            thread.wait(3000)
        except RuntimeError:
            pass
    if leaked:
        warnings.warn(
            f"{leaked} QThread(s) were still running at test teardown and were "
            "joined to avoid a destroyed-while-running abort. Drive workers to "
            "completion in the test (bounded processEvents pump) — see "
            "docs/testing.md.",
            stacklevel=2,
        )


@pytest.fixture(autouse=True)
def _join_leaked_worker_threads():
    """Join any plain `threading.Thread` a test started but didn't wait for.

    The sibling fixture above does this for `QThread`. This one covers the other
    half, and it is the half that was actually crashing the suite.

    Platterpus runs its post-rip work — hashing, FLAC verification, transcoding,
    CTDB lookup, the library move — on **daemon** `threading.Thread`s. Daemon
    means "don't hold up interpreter exit", not "safe to abandon": a daemon
    thread that is still running when the cyclic garbage collector fires *on it*
    will walk the object graph from inside itself, and the objects it walks
    include Qt wrappers the GUI thread may be tearing down. The observed crash
    was exactly that shape — a segfault inside `pathlib._scandir`, on a
    `checksums.py` worker, during a collection.

    Only threads started **during the test** are tracked, and only ones that are
    still alive at teardown are waited on, so the normal case costs nothing. The
    wait is bounded and a timeout warns rather than fails: a wedged worker should
    make itself known without turning one slow test into a red suite.

    Note the deliberate absence of `processEvents()` here — same reason the
    QThread backstop avoids it. Pumping can fire a stale `QTimer.singleShot` left
    by a half-destroyed window, which is its own crash.
    """
    import threading
    import warnings

    started: list[threading.Thread] = []
    original_start = threading.Thread.start

    def tracking_start(self: threading.Thread) -> None:
        started.append(self)
        return original_start(self)

    threading.Thread.start = tracking_start  # type: ignore[method-assign]
    try:
        yield
    finally:
        threading.Thread.start = original_start  # type: ignore[method-assign]

    current = threading.current_thread()
    stubborn: list[str] = []
    for worker in started:
        if worker is current or not worker.is_alive():
            continue
        worker.join(5.0)
        if worker.is_alive():
            stubborn.append(worker.name)
    if stubborn:
        warnings.warn(
            f"{len(stubborn)} worker thread(s) were still running 5s after the "
            f"test ended and could not be joined: {', '.join(stubborn)}. A live "
            "thread during a later garbage collection can abort the process — "
            "drive the worker to completion in the test (see docs/testing.md).",
            stacklevel=2,
        )


@pytest.fixture(autouse=True)
def _non_blocking_message_boxes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give `QMessageBox`'s static helpers safe, non-blocking defaults.

    A modal `QMessageBox.question/.information/...` calls `.exec()`, which
    **blocks forever** under the headless `offscreen` platform (no user to
    click). That's a real hazard whenever a test pumps the event loop
    (`processEvents()`): a *stale* `QTimer.singleShot` left by an earlier
    test's window — e.g. the first-run `_maybe_offer_host_setup` offer — can
    fire and hang the whole suite (a hard abort).

    So we default them to a harmless answer for every test: `question` →
    `No` (decline), the notice boxes → `Ok`. Tests that assert specific
    dialog behaviour monkeypatch the relevant method themselves; that
    per-test patch is applied after this autouse one and wins.
    """
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No
    )
    for method in ("information", "warning", "critical"):
        monkeypatch.setattr(
            QMessageBox, method, lambda *a, **k: QMessageBox.StandardButton.Ok
        )
