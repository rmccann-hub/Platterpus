"""Drive setup wizard — one-click calibration of the optical drive.

Replaces the manual hand-edit of `whipper.conf` (the worst first-run
step) with a guided flow: the user inserts a popular CD and clicks
Detect; we run `whipper drive analyze` + `whipper offset find` (off the
GUI thread, via DriveSetupWorker), which persist the cache verdict and
read offset to `whipper.conf` themselves. We back the file up first so
the user can always revert. See PLANNING.md KDD-15.

The dialog owns the worker thread; `_on_finished` is a plain slot so
tests can exercise the result rendering without a live event loop.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from whipper_gui.adapters.whipper_backend import WhipperBackend
from whipper_gui.workers.drive_setup_worker import (
    DriveSetupResult,
    DriveSetupWorker,
)

log = logging.getLogger(__name__)


class DriveSetupDialog(QDialog):
    """Modal-ish dialog that calibrates one drive via whipper's commands."""

    def __init__(
        self,
        backend: WhipperBackend,
        device: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend: WhipperBackend = backend
        self._device: str = device
        self._thread: QThread | None = None
        self._worker: DriveSetupWorker | None = None

        self.setWindowTitle("Set up drive")

        root = QVBoxLayout(self)

        intro = QLabel(
            "This calibrates your drive for bit-perfect rips. It detects the "
            "drive's read offset and audio-cache behaviour and saves them to "
            "whipper.conf (your existing config is backed up first).\n\n"
            "Insert a popular commercial CD — one likely to be in the "
            "AccurateRip database — then click Detect. This can take a minute.",
            self,
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        self._device_label: QLabel = QLabel(
            f"Drive: {device or '(auto-detected)'}", self
        )
        root.addWidget(self._device_label)

        self._detect_button: QPushButton = QPushButton("Detect", self)
        self._detect_button.clicked.connect(self._on_detect_clicked)
        root.addWidget(self._detect_button)

        # Indeterminate (busy) bar — min==max==0 animates with no percentage,
        # which is honest here since neither whipper command reports progress.
        self._progress: QProgressBar = QProgressBar(self)
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        self._status_label: QLabel = QLabel("", self)
        self._status_label.setWordWrap(True)
        root.addWidget(self._status_label)

        self._results_label: QLabel = QLabel("", self)
        self._results_label.setWordWrap(True)
        root.addWidget(self._results_label)

        # Close only — there's no "apply" step because whipper writes the
        # config itself the moment detection succeeds.
        self._button_box: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, self
        )
        self._button_box.rejected.connect(self.reject)
        self._button_box.accepted.connect(self.accept)
        root.addWidget(self._button_box)

    # --- Detection flow -----------------------------------------------------

    def _on_detect_clicked(self) -> None:
        """Kick off calibration on a worker thread."""
        if self._thread is not None:  # already running
            return
        self._detect_button.setEnabled(False)
        self._results_label.clear()
        self._progress.setVisible(True)
        self._status_label.setText("Starting…")

        self._worker = DriveSetupWorker(self._backend, self._device)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._worker.status.connect(self._status_label.setText)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.started.connect(self._worker.run)
        self._thread.start()

    def _on_finished(self, result: DriveSetupResult) -> None:
        """Render the calibration outcome. Safe to call directly in tests."""
        self._progress.setVisible(False)
        self._status_label.setText(
            "Done." if result.ok else "Finished with issues."
        )
        self._results_label.setText(_format_result(result))
        self._detect_button.setEnabled(True)
        self._detect_button.setText("Re-detect")
        self._worker = None
        self._thread = None

    # --- Lifecycle ----------------------------------------------------------

    def closeEvent(self, event: object) -> None:  # noqa: N802 — Qt API
        """Stop the worker thread cleanly if detection is still running."""
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)
        super().closeEvent(event)  # type: ignore[arg-type]


def _format_result(result: DriveSetupResult) -> str:
    """Build the human-readable summary block for the dialog."""
    lines: list[str] = []

    if result.offset is not None:
        lines.append(
            f"✓ Read offset: {result.offset:+d} samples — saved to whipper.conf."
        )
    else:
        lines.append(f"✗ Read offset: {result.offset_error or 'not detected'}")

    if result.can_defeat_cache is True:
        lines.append("✓ Audio cache: will be defeated for secure rips (saved).")
    elif result.can_defeat_cache is False:
        lines.append(
            "• Audio cache: this drive doesn't need cache-defeating (saved)."
        )
    else:
        lines.append(
            f"• Audio cache: {result.analyze_error or 'could not be determined'}"
        )

    if result.backup_path is not None:
        lines.append(f"Previous whipper.conf backed up to {result.backup_path.name}.")

    return "\n".join(lines)
