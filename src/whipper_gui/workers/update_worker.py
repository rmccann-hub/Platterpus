"""UpdateCheckWorker — runs the release lookup off the GUI thread.

The check is one short HTTPS GET, but the GUI thread must never block on
the network (a slow or absent connection would freeze the window for the
whole timeout). Same minimal worker pattern as HostSetupWorker.

Signals:
  finished(object) — a `ReleaseInfo` or None (couldn't determine)
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Slot

from whipper_gui.update_check import latest_release

log = logging.getLogger(__name__)


class UpdateCheckWorker(QObject):
    """QObject worker: fetch the newest published release, emit it."""

    finished = Signal(object)  # ReleaseInfo | None

    @Slot()
    def run(self) -> None:
        try:
            result = latest_release()
        except Exception:  # noqa: BLE001 — a worker must always finish
            log.exception("update check crashed")
            result = None
        self.finished.emit(result)
