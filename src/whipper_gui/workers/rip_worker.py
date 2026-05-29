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

# Human-readable phase descriptions for the status line. Without these
# the GUI sat on "Starting rip…" for the whole pre-track disc scan
# (which can run a minute or more) and looked frozen — T32 feedback.
# Whipper's progress lines look like:
#   "Reading TOC  50 %"
#   "Reading table  50 %"
#   "Reading track 3 of 16 (1 of 9) ...  42 %"
#   "Verifying track 3 of 16 (3 of 9) ... 42 %"
#   "Encoding track to FLAC (5 of 9) ...   0 %"
#   "Getting length of audio track (1 of 16) ... 100 %"
_DISC_SCAN_PATTERN = re.compile(
    r"Reading (?P<what>TOC|table)\s+(?P<pct>\d+)\s*%"
)
_TRACK_PHASE_PATTERN = re.compile(
    r"(?P<verb>Reading|Verifying) track (?P<track>\d+) of (?P<total>\d+)"
    r".*?(?P<pct>\d+)\s*%"
)
_LENGTH_PHASE_PATTERN = re.compile(
    r"Getting length of audio track \((?P<track>\d+) of (?P<total>\d+)\)"
)
# Per-track sub-phases that carry no track number on their own line.
_NAMED_PHASES: dict[str, str] = {
    "Encoding track to FLAC": "Encoding to FLAC…",
    "Calculating peak level": "Calculating peak level…",
    "Writing tags to FLAC": "Writing tags…",
    "Embed picture to FLAC": "Finalizing track…",
}


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
    status = Signal(str)                   # human-readable current phase
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
        # Last status text emitted, so we don't re-emit identical phases
        # on every progress tick (whipper prints one line per percent).
        self._last_status: str = ""
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
                # Status text first (covers the pre-track disc scan and
                # the encode/tag sub-phases), then the numeric progress
                # that drives the bar.
                desc = _describe_activity(line)
                if desc is not None and desc != self._last_status:
                    self._last_status = desc
                    self.status.emit(desc)
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


def _describe_activity(line: str) -> str | None:
    """Return a short human status for a whipper progress line, or None.

    Used to keep the status label live across every phase — especially
    the pre-track disc scan, which otherwise left the GUI on
    "Starting rip…" for a minute-plus and looked hung.
    """
    match = _DISC_SCAN_PATTERN.search(line)
    if match:
        what = "disc TOC" if match.group("what") == "TOC" else "disc table"
        return f"Reading {what}… {match.group('pct')}%"

    match = _TRACK_PHASE_PATTERN.search(line)
    if match:
        return (
            f"{match.group('verb')} track {match.group('track')} "
            f"of {match.group('total')}… {match.group('pct')}%"
        )

    match = _LENGTH_PHASE_PATTERN.search(line)
    if match:
        return (
            f"Checking track {match.group('track')} "
            f"of {match.group('total')}…"
        )

    for phrase, friendly in _NAMED_PHASES.items():
        if phrase in line:
            return friendly
    return None
