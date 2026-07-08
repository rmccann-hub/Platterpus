"""Drive setup wizard — one-click calibration of the optical drive.

Replaces the manual hand-edit of a config file (the worst first-run step) with a
guided flow. The read offset (what makes a rip bit-perfect) comes from the
bundled AccurateRip drive-model list — pre-filled and saved in one click when the
drive is recognised — or is entered by hand. The main window persists it as
Platterpus's `--offset` override (the backend writes no config file of its own).

Backends that can genuinely MEASURE an offset from a disc
(``RipBackend.supports_offset_detection()``) additionally get a "Detect" button
that runs off the GUI thread via ``DriveSetupWorker``. **cyanrip cannot** (it has
no offset finder — its ``-f`` is force-overread), so that button is hidden for it
rather than offering a probe that can only fail — honest UI. The
``DriveSetupWorker``/detection seam remains for a future measuring backend.

The dialog owns the worker thread; `_on_finished` is a plain slot so tests can
exercise the result rendering without a live event loop.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from platterpus.adapters.rip_backend import RipBackend
from platterpus.ui.dialogs.centering import CenteredDialog
from platterpus.workers import start_worker_thread
from platterpus.workers.drive_setup_worker import (
    DriveSetupResult,
    DriveSetupWorker,
)

log = logging.getLogger(__name__)


class DriveSetupDialog(CenteredDialog):
    """Modal-ish dialog that calibrates one drive via the backend's commands."""

    # Emitted when the user saves a manually-entered offset (the fallback for
    # when auto-detection can't run — e.g. no AccurateRip disc to hand). The
    # main window persists it as the GUI's `--offset` override; this dialog
    # stays a view and never writes config itself.
    manual_offset_saved = Signal(int)

    # Emitted after a successful auto-detect (only reachable for a backend that
    # can measure — not cyanrip). Carries the DriveSetupResult so the main window
    # can persist the measured offset and record its provenance in the
    # drive-profile ledger. Confidence is earned by AGREEMENT with the AccurateRip
    # list (reconcile_offset), never granted to a lone reading. The dialog stays
    # a view.
    detection_recorded = Signal(object)

    def __init__(
        self,
        backend: RipBackend,
        device: str,
        parent: QWidget | None = None,
        current_offset: int = 0,
        known_offset: int | None = None,
        drive_label: str = "",
    ) -> None:
        """`known_offset`, when provided, is the AccurateRip read offset
        looked up by drive model (the primary, disc-free path). We prefill
        the manual field with it and call it out so the user can save it in
        one click — no disc or ripper probe required. `drive_label` is the
        human drive name shown in that callout.
        """
        super().__init__(parent)
        self._backend: RipBackend = backend
        # Whether this backend can genuinely measure the offset from a disc. When
        # False (cyanrip), we do NOT show a "Detect" button that can only fail —
        # the offset comes from the AccurateRip drive list (pre-filled below) or
        # manual entry. Honest UI: never present a non-working path as working.
        self._can_detect: bool = backend.supports_offset_detection()
        self._device: str = device
        self._known_offset: int | None = known_offset
        self._thread: QThread | None = None
        self._worker: DriveSetupWorker | None = None
        # Set true once the dialog is closing, so a late worker result
        # doesn't poke widgets that are being torn down.
        self._closing: bool = False

        self.setWindowTitle("Set up drive")
        # Open at a readable size (the default was cramped — labels and the
        # detection output were clipped and unscrollable). Resizable.
        self.resize(560, 420)
        self.setMinimumSize(460, 320)

        root = QVBoxLayout(self)

        if self._can_detect:
            intro_text = (
                "This calibrates your drive for bit-perfect rips. It detects the "
                "drive's read offset and audio-cache behaviour and saves the "
                "offset to Platterpus's own settings, which are applied to "
                "cyanrip on every rip.\n\n"
                "Insert a popular commercial CD — one likely to be in the "
                "AccurateRip database — then click Detect. This can take a minute."
            )
        else:
            # cyanrip can't measure the offset from a disc, so we don't pretend
            # to. The read offset — what makes a rip bit-perfect — comes from the
            # AccurateRip drive list (pre-filled below when your drive is known)
            # or is entered by hand. It's saved to Platterpus's settings and
            # applied to cyanrip on every rip.
            intro_text = (
                "The read offset is what makes a rip bit-perfect. Platterpus "
                "applies it to cyanrip on every rip.\n\n"
                "Your drive's offset comes from the AccurateRip drive list "
                "(pre-filled below when your drive is recognised) or you can "
                "enter it by hand. On-disc auto-detection isn't available with "
                "this backend."
            )
        intro = QLabel(intro_text, self)
        intro.setWordWrap(True)
        root.addWidget(intro)

        self._device_label: QLabel = QLabel(
            f"Drive: {device or '(auto-detected)'}", self
        )
        root.addWidget(self._device_label)

        # Primary path: if we already know this drive's offset from the
        # AccurateRip drive list (looked up by model), say so prominently —
        # the user can save it in one click below without inserting a disc.
        # This sidesteps cyanrip's disc-based offset detection entirely.
        if known_offset is not None:
            name = drive_label or "this drive"
            verify_clause = (
                " Auto-detect (Detect) is optional verification."
                if self._can_detect
                else ""
            )
            suggestion = QLabel(
                f"✓ Known read offset for {name}: <b>{known_offset:+d}</b> "
                "(from the AccurateRip drive list). It's pre-filled below — "
                'click "Save offset" to use it. No disc needed.' + verify_clause,
                self,
            )
            suggestion.setWordWrap(True)
            root.addWidget(suggestion)

        # The "Detect" action + its busy bar only exist when the backend can
        # actually measure an offset from a disc. cyanrip can't, so we don't show
        # a button that would only ever report "can't do it" — honest UI (the
        # offset comes from the AccurateRip list / manual entry below instead).
        self._detect_button: QPushButton | None = None
        self._progress: QProgressBar | None = None
        if self._can_detect:
            self._detect_button = QPushButton("Detect", self)
            self._detect_button.clicked.connect(self._on_detect_clicked)
            root.addWidget(self._detect_button)

            # Indeterminate (busy) bar — min==max==0 animates with no percentage,
            # honest here since the detection command reports no progress.
            self._progress = QProgressBar(self)
            self._progress.setRange(0, 0)
            self._progress.setVisible(False)
            root.addWidget(self._progress)

        self._status_label: QLabel = QLabel("", self)
        self._status_label.setWordWrap(True)
        root.addWidget(self._status_label)

        # Read-only, scrollable: detection output can be several lines and
        # the offset-find guidance is long, so a label clipped it.
        self._results_label: QPlainTextEdit = QPlainTextEdit("", self)
        self._results_label.setReadOnly(True)
        root.addWidget(self._results_label, stretch=1)

        # --- Manual fallback ---------------------------------------------------
        # Auto-detection needs a disc that's in AccurateRip; a user with only
        # CD-Rs (or an obscure pressing) can't run it. Let them enter the
        # offset by hand — every drive model's value is published at
        # AccurateRip's list, keyed by the exact drive the GUI already shows.
        manual_intro = QLabel(
            "No AccurateRip disc handy? Look up your drive's offset at "
            '<a href="https://www.accuraterip.com/driveoffsets.htm">'
            "accuraterip.com/driveoffsets.htm</a> and enter it here. It's "
            "saved in Platterpus's own settings and passed to cyanrip at rip "
            "time (cyanrip uses no config file of its own).",
            self,
        )
        manual_intro.setWordWrap(True)
        manual_intro.setOpenExternalLinks(True)
        root.addWidget(manual_intro)

        manual_row = QHBoxLayout()
        manual_row.addWidget(QLabel("Read offset (samples):", self))
        self._offset_spin: QSpinBox = QSpinBox(self)
        # AccurateRip offsets sit well within ±2000 samples in practice.
        self._offset_spin.setRange(-2000, 2000)
        # Prefill with the model-looked-up offset when we have one (the
        # primary path); otherwise fall back to the currently-configured
        # value passed in.
        self._offset_spin.setValue(
            known_offset if known_offset is not None else current_offset
        )
        manual_row.addWidget(self._offset_spin)
        self._save_offset_button: QPushButton = QPushButton("Save offset", self)
        self._save_offset_button.clicked.connect(self._on_save_offset_clicked)
        manual_row.addWidget(self._save_offset_button)
        manual_row.addStretch(1)
        root.addLayout(manual_row)

        # Close only — there's no "apply" step because the offset is saved to
        # Platterpus's own config the moment detection (or a manual save)
        # succeeds, and cyanrip is fed it via -s at rip time.
        self._button_box: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, self
        )
        self._button_box.rejected.connect(self.reject)
        self._button_box.accepted.connect(self.accept)
        root.addWidget(self._button_box)

    # --- Detection flow -----------------------------------------------------

    def _on_detect_clicked(self) -> None:
        """Kick off calibration on a worker thread."""
        # Only reachable when the backend can detect (the button doesn't exist
        # otherwise), but guard defensively.
        if self._detect_button is None or self._thread is not None:
            return
        self._detect_button.setEnabled(False)
        # Lock the manual-offset controls while detection runs: editing or
        # saving an offset mid-detection would race the value the ripper is
        # about to report. They're re-enabled in `_on_finished`.
        self._set_manual_controls_enabled(False)
        self._results_label.clear()
        if self._progress is not None:
            self._progress.setVisible(True)
        self._status_label.setText("Starting…")

        self._worker = DriveSetupWorker(self._backend, self._device)
        self._thread = QThread(self)
        self._worker.status.connect(self._status_label.setText)
        self._worker.finished.connect(self._on_finished)
        start_worker_thread(self._worker, self._thread, self._worker.run)

    def _on_finished(self, result: DriveSetupResult) -> None:
        """Render the calibration outcome. Safe to call directly in tests."""
        # If the dialog is closing, the worker's final (likely cancelled)
        # result is irrelevant and the widgets may be on their way out —
        # don't touch them.
        if self._closing:
            return
        if self._progress is not None:
            self._progress.setVisible(False)
        self._status_label.setText("Done." if result.ok else "Finished with issues.")
        self._results_label.setPlainText(_format_result(result))
        if self._detect_button is not None:
            self._detect_button.setEnabled(True)
            self._detect_button.setText("Re-detect")
        self._set_manual_controls_enabled(True)
        self._worker = None
        self._thread = None
        # Tell the main window to persist this measured offset and record it in
        # the drive profile. Only when we actually got an offset; a failed
        # detect has nothing to record.
        if result.offset is not None:
            self.detection_recorded.emit(result)

    def _set_manual_controls_enabled(self, enabled: bool) -> None:
        """Enable/disable the manual read-offset controls as a unit.

        The QSpinBox covers its own up/down arrows, so disabling it locks the
        whole numeric entry; the Save button is locked alongside it.
        """
        self._offset_spin.setEnabled(enabled)
        self._save_offset_button.setEnabled(enabled)

    def _on_save_offset_clicked(self) -> None:
        """Persist a hand-entered offset via the main window (--offset path)."""
        value = self._offset_spin.value()
        self.manual_offset_saved.emit(value)
        self._status_label.setText(
            f"Saved read offset {value:+d} — it will be used for rips."
        )

    # --- Lifecycle ----------------------------------------------------------

    def _stop_detection(self) -> None:
        """Cancel a running detection and join its thread before teardown.

        Cancelling terminates the ripper subprocess, which unblocks the
        worker's run() so the QThread can quit and be waited on. Without
        this, closing mid-detection destroys a still-running QThread (Qt
        aborts the process) and leaves the ripper spinning the drive.
        """
        # cancel_setup SIGTERM/SIGKILLs the subprocess so run() returns promptly;
        # stop_thread waits briefly for that and detaches if the kill is slow,
        # so closing the dialog never blocks the GUI thread nor destroys a
        # still-running QThread.
        from platterpus.workers import stop_thread

        stop_thread(self._thread, self._worker)
        self._worker = None
        self._thread = None

    def reject(self) -> None:  # noqa: D102 — Qt override (Close button / Esc)
        self._closing = True
        self._stop_detection()
        super().reject()

    def closeEvent(self, event: object) -> None:  # noqa: N802 — Qt API
        """Stop the worker thread cleanly if detection is still running."""
        self._closing = True
        self._stop_detection()
        super().closeEvent(event)  # type: ignore[arg-type]


def _format_result(result: DriveSetupResult) -> str:
    """Build the human-readable summary block for the dialog."""
    lines: list[str] = []

    if result.offset is not None:
        lines.append(
            f"✓ Read offset: {result.offset:+d} samples — saved to Platterpus settings."
        )
    else:
        lines.append(f"✗ Read offset: {result.offset_error or 'not detected'}")

    if result.can_defeat_cache is True:
        lines.append(
            "✓ Audio cache: this drive caches audio, so Platterpus will read "
            "around the cache to keep rips bit-perfect (saved)."
        )
    elif result.can_defeat_cache is False:
        lines.append(
            "• Audio cache: this drive doesn't cache audio, so Platterpus "
            "doesn't need to read around a cache (saved)."
        )
    else:
        lines.append(
            f"• Audio cache: {result.analyze_error or 'could not be determined'}"
        )

    return "\n".join(lines)
