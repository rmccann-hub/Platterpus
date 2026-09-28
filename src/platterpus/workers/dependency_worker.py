"""DependencyCheckWorker — runs the launch-time dependency probe off-thread.

`DependencyManager.check_all()` shells out to each dependency's probe — and
the cyanrip probe runs `~/.local/bin/cyanrip --version`, which *enters the
Distrobox container*. On a cold container that can take several seconds, so
running it on the GUI thread at launch would freeze the just-shown window
("never block the GUI thread"). This worker runs the pure *probe* phase off
the GUI thread; the result (a `DependencyReport`) is applied back on the GUI
thread, where the resolver dialogs must live.

Same minimal worker pattern as UpdateCheckWorker.

The whole check is bounded by `deps.manager.CHECK_DEADLINE_S`; a check that runs
out of time still emits, with the tools it did not reach listed in
`report.unchecked`.

Signals:
  finished(object) — a `DependencyReport`, or None if the probe crashed
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

from platterpus import diagnostics
from platterpus.deps import manager as dep_manager
from platterpus.deps.checks import cancel_version_probes

if TYPE_CHECKING:
    from platterpus.deps.manager import DependencyManager

log = logging.getLogger(__name__)


class DependencyCheckWorker(QObject):
    """QObject worker: probe every dependency (no installs), emit the report.

    Takes a fully-built `DependencyManager`; only calls its `check_all()`
    (pure probing — touches no widgets), so it's safe off the GUI thread. The
    manager's resolvers are used later, on the GUI thread, by the caller.
    """

    finished = Signal(object)  # DependencyReport | None

    def __init__(
        self, manager: DependencyManager, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._manager = manager
        # Set from the GUI thread. Plain bool assignment is atomic under the GIL.
        self._cancelled: bool = False

    @Slot()
    def cancel(self) -> None:
        """Stop the dependency check. Thread-safe, non-blocking.

        Two halves, both needed. The flag stops `check_all` starting the next spec;
        killing the running version probe interrupts the one already in flight —
        and that is the part that matters, because the **first** probe of a session
        starts the Distrobox container and can block for tens of seconds where
        `QThread.quit()` cannot reach it. A flag alone would be the false promise
        CLAUDE.md rule 9 forbids; a kill alone would let the loop march on to the
        next dependency.
        """
        self._cancelled = True
        cancel_version_probes()

    @Slot()
    def run(self) -> None:
        try:
            # The overall deadline is read HERE, at run time, rather than bound at
            # import: it is the one number that decides how long a user waits for
            # any answer at all, and a test must be able to shorten it. The check
            # itself enforces it where the waiting happens (see `check_all`).
            report = self._manager.check_all(
                cancelled=lambda: self._cancelled,
                deadline_s=dep_manager.CHECK_DEADLINE_S,
            )
        except Exception as exc:  # noqa: BLE001 — a worker must always finish
            log.exception("dependency check crashed")
            # RECORD IT, not merely log it. The GUI half returns immediately on a
            # None report, so a user who clicked Tools → Check dependencies saw
            # *nothing at all* — indistinguishable from a dead menu item — and the
            # only trace was a traceback in a file that is INFO-only by default.
            # This puts it in the enumerated diagnostics too, so a later rip report
            # explains why the dependency block is empty.
            diagnostics.exception(
                "deps.command_failed",
                "the dependency check crashed before it could produce a report",
                exc,
                where="workers.dependency_worker.DependencyWorker.run",
            )
            report = None
        # A CANCELLED check is not announced: the window cancels only while it is
        # closing, so there is nobody left to show it to. A check stopped by its
        # DEADLINE is announced — the user is waiting for exactly that answer — and
        # is safe to announce, because `check_all` marks everything it did not
        # reach as `unchecked` rather than leaving it out and calling the rest the
        # whole picture.
        if self._cancelled:
            log.info("dependency check cancelled; not emitting a partial report")
            return
        self.finished.emit(report)
