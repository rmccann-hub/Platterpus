"""RipWorker — drives a WhipperBackend rip off the GUI thread.

The main thread constructs a RipWorker, moves it to a QThread, and
connects QThread.started to RipWorker.start_rip. The worker streams
whipper's stdout via Qt signals so the GUI can update without blocking.

Signals:
  log_line(str)               — one line of whipper output
  progress(int, float)        — (track_number, percent_complete) when
                                parseable from the output stream
  finished(bool, str)         — (success, log_file_path); log path is
                                "" when no .log file was located
  error(str)                  — short human-readable error message

Cancel:
  Call cancel() from the GUI thread. It sets a flag and forwards to
  RipHandle.cancel(), which SIGTERMs (then SIGKILLs) the subprocess.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from whipper_gui.adapters.whipper_backend import (
    RipHandle,
    WhipperBackend,
    WhipperError,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RipParameters:
    """Everything the worker needs to start a rip.

    Keep this typed and frozen so the caller's intent is locked in
    before crossing thread boundaries — a `dict[str, Any]` would let
    typos slip through silently.
    """

    drive: str
    release_id: str
    output_dir: Path
    track_template: str
    disc_template: str
    unknown: bool = False
    cdr: bool = False


# Defensive progress matcher. Whipper's output during a rip is line-based
# and includes progress indicators; the exact format may drift between
# versions. We match a "Track N ... NN%" shape with named groups, and if
# the line doesn't match we just don't emit a progress signal for it —
# the log_line signal still carries the raw text. T32's smoke test will
# tell us whether this pattern needs tweaking for the user's version.
_PROGRESS_PATTERN = re.compile(
    r"[Tt]rack\s+(?P<track>\d+).*?(?P<pct>\d+(?:\.\d+)?)\s*%"
)


class RipWorker(QObject):
    """QObject worker that owns a rip subprocess for its lifetime.

    Construct on the GUI thread, then move to a QThread:

        worker = RipWorker(backend, params)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.start_rip)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()
    """

    log_line = Signal(str)
    progress = Signal(int, float)         # track_number, percent
    finished = Signal(bool, str)           # success, log_path
    error = Signal(str)

    def __init__(
        self,
        backend: WhipperBackend,
        params: RipParameters,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend: WhipperBackend = backend
        self._params: RipParameters = params
        self._handle: RipHandle | None = None
        # Flag is a plain Python bool — assignment is atomic under the
        # GIL, so reading it from the worker thread while the GUI thread
        # sets it is safe without locks.
        self._cancelled: bool = False

    # --- Slots ---

    @Slot()
    def start_rip(self) -> None:
        """Begin the rip. Invoked via QThread.started."""
        try:
            self._handle = self._backend.rip(
                drive=self._params.drive,
                release_id=self._params.release_id,
                output_dir=self._params.output_dir,
                track_template=self._params.track_template,
                disc_template=self._params.disc_template,
                unknown=self._params.unknown,
                cdr=self._params.cdr,
            )
        except WhipperError as exc:
            log.exception("rip failed to start")
            self.error.emit(str(exc))
            self.finished.emit(False, "")
            return
        except Exception as exc:  # noqa: BLE001 — last-resort guard
            log.exception("unexpected error starting rip")
            self.error.emit(f"unexpected error: {exc}")
            self.finished.emit(False, "")
            return

        # Stream output. Iteration ends when whipper closes its stdout
        # (i.e. exits) or when cancel() flips the flag.
        try:
            for line in self._handle.log_lines():
                if self._cancelled:
                    break
                self.log_line.emit(line)
                emit = _parse_progress(line)
                if emit is not None:
                    track, pct = emit
                    self.progress.emit(track, pct)
        except Exception as exc:  # noqa: BLE001
            log.exception("error reading whipper stdout")
            self.error.emit(f"rip stream error: {exc}")
            self.finished.emit(False, "")
            return

        exit_code = self._handle.wait()
        success = (exit_code == 0) and not self._cancelled
        log_path = self._find_log_path()
        self.finished.emit(success, str(log_path) if log_path else "")

    @Slot()
    def cancel(self) -> None:
        """Cancel an in-progress rip.

        Thread-safe: sets a flag (read by the worker's iteration loop),
        then forwards to the handle's cancel() which is itself thread-safe
        because subprocess methods are.
        """
        self._cancelled = True
        if self._handle is not None:
            try:
                self._handle.cancel()
            except Exception:  # noqa: BLE001
                log.exception("cancel() raised; ignored")

    # --- Internals ---

    def _find_log_path(self) -> Path | None:
        """Locate the .log whipper just wrote.

        Whipper drops the rip log next to the FLACs. The output_dir from
        params is the root; we search recursively for the most recent
        .log file. Returns None if nothing was written (e.g. rip failed
        before any output).
        """
        output_dir = self._params.output_dir
        if not output_dir.exists():
            return None

        candidates = list(output_dir.rglob("*.log"))
        if not candidates:
            return None
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]


def _parse_progress(line: str) -> tuple[int, float] | None:
    """Try to extract (track_number, percent) from a whipper stdout line.

    Returns None when the line doesn't match — the worker just won't
    emit a progress signal for that line. Robust to format drift per
    CLAUDE.md "named-group regexes, not column-index splits".
    """
    match = _PROGRESS_PATTERN.search(line)
    if not match:
        return None
    track = int(match.group("track"))
    percent = float(match.group("pct"))
    return track, percent
