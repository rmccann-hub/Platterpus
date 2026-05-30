"""DriveSetupWorker — runs drive calibration off the GUI thread.

`whipper drive analyze` (cache profile) and `whipper offset find` (read
offset) both spin the disc and can take a minute or more, so they must
not run on the GUI thread. This worker drives whipper's OWN commands —
which persist their results to `whipper.conf` themselves (KDD-15) — after
backing the config up first, then reports a single result object.

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

from whipper_gui.adapters.whipper_backend import (
    WhipperBackend,
    WhipperError,
    back_up_whipper_config,
)

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
        backend: WhipperBackend,
        device: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend: WhipperBackend = backend
        self._device: str = device

    @Slot()
    def run(self) -> None:
        """Back up whipper.conf, then run analyze + offset find in turn."""
        backup_path = back_up_whipper_config()

        # Cache analysis first — it's the quicker of the two and confirms a
        # disc is actually present before the longer offset search.
        self.status.emit("Analyzing drive cache…")
        can_defeat: bool | None = None
        analyze_error: str | None = None
        try:
            can_defeat = self._backend.analyze_drive(self._device)
        except WhipperError as exc:
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
        try:
            offset = self._backend.find_offset(self._device)
        except WhipperError as exc:
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
                backup_path=backup_path,
            )
        )
