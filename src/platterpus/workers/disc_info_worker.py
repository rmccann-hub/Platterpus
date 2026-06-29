"""DiscInfoWorker — reads the inserted disc's TOC/MB-id off the GUI thread.

`RipBackend.disc_info()` shells out (whipper `cd info` / cyanrip `-I`),
which **enters the Distrobox container** and reads the disc — several seconds,
especially on a cold container or a slow drive. Running it on the GUI thread
(as the drive-change handler used to) froze the window on every drive
selection and at launch. This worker runs that probe off the GUI thread; the
result is applied back on the GUI thread, which then drives the disc-info
panel + the (already off-thread) MusicBrainz lookup.

Same minimal worker pattern as MusicBrainzWorker / DependencyCheckWorker. The
`device` is echoed back in both signals so a stale result (the user switched
drives while a probe was in flight) is easy to recognise.

Signals:
  finished(str, object) — (device, DiscInfo)
  failed(str, str)      — (device, human-readable error message)
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Slot

from platterpus.adapters.whipper_backend import RipBackend, WhipperError

log = logging.getLogger(__name__)


class DiscInfoWorker(QObject):
    """QObject worker: read `disc_info(device)`, emit the DiscInfo or an error."""

    finished = Signal(str, object)  # (device, DiscInfo)
    failed = Signal(str, str)  # (device, message)

    def __init__(
        self, backend: RipBackend, device: str, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._device = device

    @Slot()
    def run(self) -> None:
        try:
            info = self._backend.disc_info(self._device)
        except WhipperError as exc:
            log.warning("disc_info failed: %s", exc)
            self.failed.emit(self._device, str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — a worker must always finish
            log.exception("disc_info crashed")
            self.failed.emit(self._device, f"unexpected error: {exc}")
            return
        self.finished.emit(self._device, info)
