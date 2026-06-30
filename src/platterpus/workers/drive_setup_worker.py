"""DriveSetupWorker — runs drive calibration off the GUI thread.

Offset detection (cyanrip's `offset find`) spins the disc and can take a
minute or more, so it must not run on the GUI thread. This worker drives the
backend's calibration commands and reports a single result object; the GUI
then persists the detected offset as Platterpus's `--offset` override (the
backend does not write any config file itself).

Signals:
  status(str)        — human-readable phase ("Analyzing drive cache…")
  finished(object)   — a DriveSetupResult (always emitted, even on partial
                       failure, so the dialog can show what worked)

Usage mirrors RipWorker: construct on the GUI thread, move to a QThread,
connect QThread.started → run.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from platterpus.adapters.rip_backend import RipBackend, RipError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DriveSetupResult:
    """Outcome of a drive-calibration run.

    Each step is independent: a failed `offset find` (e.g. the disc isn't
    in AccurateRip) still leaves the cache verdict intact, so we report
    both halves rather than aborting on the first error. `offset` /
    `can_defeat_cache` are None when their step didn't yield a value;
    the matching `*_error` carries a user-facing reason instead.
    """

    offset: int | None = None
    can_defeat_cache: bool | None = None
    offset_error: str | None = None
    analyze_error: str | None = None
    backup_path: Path | None = None

    @property
    def ok(self) -> bool:
        """True when we got a usable read offset (the key archival value)."""
        return self.offset is not None


class DriveSetupWorker(QObject):
    """QObject worker that calibrates one drive via whipper's commands."""

    status = Signal(str)
    finished = Signal(object)  # DriveSetupResult

    def __init__(
        self,
        backend: RipBackend,
        device: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend: RipBackend = backend
        self._device: str = device
        # Set from the GUI thread when the user closes the dialog. Plain
        # bool assignment is atomic under the GIL.
        self._cancelled: bool = False

    @Slot()
    def cancel(self) -> None:
        """Request cancellation and terminate the running whipper process.

        Thread-safe: called from the GUI thread. Terminating the subprocess
        unblocks `run()` (which is waiting on it) so the QThread can finish
        and be torn down cleanly — without this the dialog's QThread is
        destroyed mid-run and Qt aborts the whole app, and the orphaned
        whipper keeps the optical drive spinning.
        """
        self._cancelled = True
        try:
            self._backend.cancel_setup()
        except Exception:  # noqa: BLE001 — cancel must never raise
            log.exception("cancel_setup() raised; ignored")

    @Slot()
    def run(self) -> None:
        """Run cache analysis + offset find in turn, then report the result."""
        if self._cancelled:
            self.finished.emit(DriveSetupResult())
            return

        # Cache analysis first — it's the quicker of the two and confirms a
        # disc is actually present before the longer offset search.
        self.status.emit("Analyzing drive cache…")
        can_defeat: bool | None = None
        analyze_error: str | None = None
        try:
            can_defeat = self._backend.analyze_drive(self._device)
        except RipError as exc:
            log.warning("drive analyze failed: %s", exc)
            analyze_error = str(exc)
        except NotImplementedError:
            analyze_error = "This backend can't analyze the drive cache."

        self.status.emit(
            "Detecting read offset… this can take a minute (needs a CD "
            "that's in the AccurateRip database)."
        )
        offset: int | None = None
        offset_error: str | None = None
        if self._cancelled:
            # Don't kick off the long offset search if we're already closing.
            self.finished.emit(
                DriveSetupResult(
                    can_defeat_cache=can_defeat,
                    analyze_error=analyze_error,
                )
            )
            return
        try:
            offset = self._backend.find_offset(self._device)
        except RipError as exc:
            log.warning("offset find failed: %s", exc)
            offset_error = str(exc)
        except NotImplementedError:
            offset_error = "This backend can't auto-detect the read offset."

        self.finished.emit(
            DriveSetupResult(
                offset=offset,
                can_defeat_cache=can_defeat,
                offset_error=offset_error,
                analyze_error=analyze_error,
            )
        )
