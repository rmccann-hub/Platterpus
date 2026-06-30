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
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(status)


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
    """
    import time

    def pump(predicate, timeout: float = 5.0, step: float = 0.005) -> bool:
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            qapp.processEvents()
            qapp.sendPostedEvents()  # flush queued cross-thread signals too
            time.sleep(step)
        return predicate()

    return pump


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
