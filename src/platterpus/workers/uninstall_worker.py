"""UninstallWorker — scans for, and removes, Platterpus's footprint off the GUI thread.

Both halves can take minutes: the scan asks ``distrobox``, ``podman`` and
``flatpak`` (a cold container store answers slowly), and the removal deletes a
container, an image and a Flatpak runtime. Neither may run on the Qt main
thread (CLAUDE.md, *Never block the GUI thread*).

``cancel()`` kills the command in flight: the engine's runner is a
``deps/uninstall_runner.UninstallRunner``, whose ``cancel()`` SIGKILLs the child's
process group and refuses every later command. So closing the dialog during a
40-second ``podman rmi`` ends it, rather than setting a flag the blocked call
never reads (CLAUDE.md rule 9).

Signals:
  scanned(object)   — tuple[Observation, ...], when :meth:`scan` finishes
  step(object)      — a StepResult, as each removal starts and ends
  finished(object)  — an UninstallReport from :meth:`remove`, or None from a scan
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Slot

from platterpus.deps.host_teardown import HostTeardown
from platterpus.deps.uninstall_plan import Choices
from platterpus.deps.uninstall_runner import CommandKiller

log = logging.getLogger(__name__)


class UninstallWorker(QObject):
    """Runs one scan or one removal on a worker thread."""

    scanned = Signal(object)  # tuple[Observation, ...]
    step = Signal(object)  # StepResult
    finished = Signal(object)  # UninstallReport | None

    def __init__(
        self,
        engine: HostTeardown,
        commands: CommandKiller,
        choices: Choices | None = None,
        parent: QObject | None = None,
    ) -> None:
        """``commands`` is the engine's runner, whose ``cancel`` kills its child."""
        super().__init__(parent)
        self._engine: HostTeardown = engine
        self._commands: CommandKiller = commands
        self._choices: Choices = choices or Choices()
        self._cancelled: bool = False

    @Slot()
    def cancel(self) -> None:
        """Kill the command in flight and stop before the next item."""
        self._cancelled = True
        self._commands.cancel()

    @Slot()
    def scan(self) -> None:
        """Scan the footprint; emit ``scanned``, then ``finished(None)``."""
        try:
            observations = self._engine.scan()
        except Exception:  # noqa: BLE001 — a worker must always finish
            log.exception("uninstall scan crashed")
            observations = ()
        self.scanned.emit(observations)
        self.finished.emit(None)

    @Slot()
    def remove(self) -> None:
        """Remove what the choices say; emit each step, then the report."""
        try:
            report = self._engine.run(
                self._choices,
                progress=self.step.emit,
                cancelled=lambda: self._cancelled,
            )
        except Exception:  # noqa: BLE001 — a worker must always finish
            log.exception("uninstall crashed")
            report = None
        self.finished.emit(report)
