"""HostSetupWorker — runs the host-stack bootstrap off the GUI thread.

The bootstrap (`deps.host_setup.HostSetup`) installs Distrobox + a container
backend, creates the `ripping` container, installs whipper into it, and
exports it — operations that can take minutes (image pulls, dnf installs), so
they must not run on the GUI thread.

Signals:
  step(object)      — a StepResult, emitted as each step completes (live log)
  finished(object)  — the full list[StepResult] when the run ends

Usage mirrors DriveSetupWorker: construct on the GUI thread, move to a
QThread, connect QThread.started → run.

Cancellation note: `cancel()` is honoured *between* steps (the orchestrator
polls it), so a long in-progress command — e.g. a `dnf install` — finishes
before the run stops. That's an accepted limitation; the alternative (killing
a half-done package install) is worse.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Slot

from platterpus.deps.step_engine import StepEngine

log = logging.getLogger(__name__)


class HostSetupWorker(QObject):
    """QObject worker that runs a step engine and reports per-step."""

    step = Signal(object)  # StepResult
    finished = Signal(object)  # list[StepResult]

    def __init__(self, host_setup: StepEngine, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._host: StepEngine = host_setup
        # Plain bool assignment is atomic under the GIL; set from the GUI
        # thread when the dialog closes.
        self._cancelled: bool = False

    @Slot()
    def cancel(self) -> None:
        """Request cancellation; takes effect at the next step boundary."""
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        """Run the bootstrap, emitting a step signal per step."""
        try:
            results = self._host.run(
                progress=self.step.emit,
                cancelled=lambda: self._cancelled,
            )
        except Exception:  # noqa: BLE001 — a worker must always finish
            log.exception("host setup crashed")
            results = []
        self.finished.emit(results)
