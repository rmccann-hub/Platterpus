"""DriveListWorker — runs `list_drives()` off the GUI thread.

On the whipper backend, `list_drives()` shells out to `whipper drive list`,
which enters the Distrobox container — a couple of seconds on a cold start.
Running it on the GUI thread at launch froze the just-shown window, so the
launch path (`MainWindow.refresh_drives`) uses this worker; the result is
applied to the `DrivePicker` on the GUI thread via `populate()`/`show_error()`.
(The user-initiated Refresh button stays synchronous — a brief block is fine
when the user explicitly asked for it.)

Same minimal worker pattern as the other workers.

Signals:
  finished(object) — a list[DriveDescriptor]
  failed(str)      — a human-readable error message
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Slot

from platterpus.adapters.whipper_backend import RipBackend, WhipperError

log = logging.getLogger(__name__)


class DriveListWorker(QObject):
    """QObject worker: list the drives, emit the list or an error."""

    finished = Signal(object)  # list[DriveDescriptor]
    failed = Signal(str)

    def __init__(self, backend: RipBackend, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._backend = backend

    @Slot()
    def run(self) -> None:
        try:
            drives = self._backend.list_drives()
        except WhipperError as exc:
            log.warning("list_drives failed: %s", exc)
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — a worker must always finish
            log.exception("list_drives raised an unexpected error")
            self.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        self.finished.emit(drives)
