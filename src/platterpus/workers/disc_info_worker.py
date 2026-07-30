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

from platterpus.adapters.rip_backend import RipBackend, RipError, cancel_info_probe

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
        # Set from the GUI thread. Plain bool assignment is atomic under the GIL.
        self._cancelled: bool = False

    @Slot()
    def cancel(self) -> None:
        """Kill the in-flight disc-info probe. Thread-safe, non-blocking.

        This worker blocks inside a container exec (`cyanrip -I`) for up to 120 s on
        a cold container, and `QThread.quit()` cannot reach a thread that is not in
        its event loop. So a flag alone would be a false promise (CLAUDE.md rule 9):
        the kill is the part that makes closing the window prompt instead of waiting
        out the shutdown budget and abandoning this thread.

        The flag is still worth setting — it suppresses the `failed` signal for a
        probe the user deliberately stopped, so cancelling a rescan does not raise a
        spurious "disc_info failed" in the UI.
        """
        self._cancelled = True
        cancel_info_probe()

    @Slot()
    def run(self) -> None:
        try:
            info = self._backend.disc_info(self._device)
        except RipError as exc:
            if self._cancelled:
                # We killed it. Not a failure worth telling the user about.
                log.info("disc_info cancelled for %s", self._device)
                return
            log.warning("disc_info failed: %s", exc)
            self.failed.emit(self._device, str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — a worker must always finish
            log.exception("disc_info crashed")
            self.failed.emit(self._device, f"unexpected error: {exc}")
            return
        self.finished.emit(self._device, info)
