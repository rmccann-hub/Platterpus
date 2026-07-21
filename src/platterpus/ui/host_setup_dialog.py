"""Host-setup wizard — one-click bootstrap of the host stack from the GUI.

Replaces having to run ``setup-host.sh`` in a terminal (KDD-17, the zero-CLI
goal). The user clicks "Set up"; we run the bootstrap (`deps.host_setup`) off
the GUI thread via :class:`HostSetupWorker`, showing live per-step progress.
Installing *system* packages needs root, so on non-atomic distros a single
graphical polkit prompt appears (via ``pkexec``); on Bazzite/Silverblue the
runtime is preinstalled, so those steps are skipped and nothing is prompted.

The dialog owns the worker thread and tears it down cleanly on close, the same
way DriveSetupDialog does.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from platterpus.deps.host_setup import HostSetup
from platterpus.deps.step_engine import StepResult, StepStatus
from platterpus.ui.accessibility import announce
from platterpus.ui.dialogs.centering import CenteredDialog
from platterpus.workers import start_worker_thread
from platterpus.workers.host_setup_worker import HostSetupWorker

log = logging.getLogger(__name__)

_STATUS_GLYPH: dict[StepStatus, str] = {
    StepStatus.DONE: "✓",
    StepStatus.RAN: "✓",
    StepStatus.WOULD_RUN: "•",
    StepStatus.FAILED: "✗",
    StepStatus.CANCELLED: "•",
}


class HostSetupDialog(CenteredDialog):
    """Modal-ish wizard that bootstraps the host stack (Distrobox + cyanrip)."""

    # Emitted once the run finishes; True if the stack is ready to rip. The
    # main window uses this to re-check dependencies / refresh the drive list.
    setup_finished = Signal(bool)

    def __init__(
        self,
        parent: QWidget | None = None,
        host_setup: HostSetup | None = None,
    ) -> None:
        """`host_setup` is injectable for tests; production builds the real
        one (a SubprocessRunner-backed bootstrap)."""
        super().__init__(parent)
        if host_setup is None:
            from platterpus.deps.step_engine import SubprocessRunner

            host_setup = HostSetup(runner=SubprocessRunner())
        self._host: HostSetup = host_setup
        self._thread: QThread | None = None
        self._worker: HostSetupWorker | None = None
        self._closing: bool = False

        self.setWindowTitle("Set up Platterpus")
        self.resize(580, 460)
        self.setMinimumSize(480, 360)

        root = QVBoxLayout(self)

        self._intro: QLabel = QLabel(
            "Platterpus rips through the <b>cyanrip</b> tool, which runs in a "
            "small Linux container so it never touches your system. This sets "
            "that up for you — no terminal needed:\n\n"
            "• installs Distrobox + a container runtime (if missing)\n"
            "• creates the 'ripping' container and installs cyanrip + flac into it\n"
            "• makes the ripping tools available to this app\n\n"
            "Installing system packages may pop up your system password prompt "
            "once. On Bazzite/Silverblue everything's already there, so this is "
            "usually instant. It's safe to re-run.",
            self,
        )
        self._intro.setWordWrap(True)
        root.addWidget(self._intro)

        self._setup_button: QPushButton = QPushButton("&Set up", self)
        self._setup_button.clicked.connect(self._on_setup_clicked)
        root.addWidget(self._setup_button)

        # Indeterminate bar — neither distrobox nor dnf reports real progress.
        self._progress: QProgressBar = QProgressBar(self)
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        self._status_label: QLabel = QLabel("", self)
        self._status_label.setWordWrap(True)
        self._status_label.setAccessibleName("Setup status")
        root.addWidget(self._status_label)

        self._results: QPlainTextEdit = QPlainTextEdit("", self)
        self._results.setReadOnly(True)
        self._results.setAccessibleName("Setup step results")
        root.addWidget(self._results, stretch=1)

        self._button_box: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, self
        )
        self._button_box.rejected.connect(self.reject)
        self._button_box.accepted.connect(self.accept)
        root.addWidget(self._button_box)

    # --- Run flow -----------------------------------------------------------

    def _on_setup_clicked(self) -> None:
        if self._thread is not None:  # already running
            return
        self._setup_button.setEnabled(False)
        self._results.clear()
        self._progress.setVisible(True)
        self._status_label.setText("Setting up… this can take a few minutes.")

        self._worker = HostSetupWorker(self._host)
        self._thread = QThread(self)
        self._worker.step.connect(self._on_step)
        self._worker.finished.connect(self._on_finished)
        start_worker_thread(self._worker, self._thread, self._worker.run)

    def _on_step(self, result: StepResult) -> None:
        """Update progress as steps run/complete. Safe to call in tests.

        A RUNNING ping shows what's happening *now* in the status line (so a
        slow step never looks frozen); terminal results append a ✓/✗ line to
        the log so the user sees what's been done.
        """
        if self._closing:
            return
        if result.status is StepStatus.RUNNING:
            hint = f" — {result.detail}" if result.detail else ""
            step_text = f"⏳ {result.title}{hint}"
            self._status_label.setText(step_text)
            # Steps run for minutes with focus elsewhere — announce each new
            # step start focus-safely (low-frequency, one per step; gap #4).
            announce(self._status_label, step_text)
            return
        glyph = _STATUS_GLYPH.get(result.status, "•")
        line = f"{glyph} {result.title}"
        if result.detail:
            line += f" — {result.detail}"
        self._results.appendPlainText(line)

    def _on_finished(self, results: list[StepResult]) -> None:
        """Render the final summary. Safe to call directly in tests."""
        if self._closing:
            return
        self._progress.setVisible(False)
        self._setup_button.setEnabled(True)
        self._setup_button.setText("Re-run setup")
        ready = self._host.is_ready()
        # Distinguish "nothing to do" (everything was already present — common
        # on Bazzite, and otherwise looks like the wizard did nothing) from a
        # setup that actually installed things.
        all_already = bool(results) and all(
            r.status is StepStatus.DONE for r in results
        )
        if ready and all_already:
            self._status_label.setText(
                "✓ Everything was already set up — you're ready to rip."
            )
        elif ready:
            self._status_label.setText(
                "✓ Setup complete — the ripping tools are installed. You can rip now."
            )
        else:
            failed = next((r for r in results if r.status is StepStatus.FAILED), None)
            if failed is not None:
                self._status_label.setText(
                    f"Setup stopped at “{failed.title}”: {failed.detail}"
                )
            else:
                self._status_label.setText("Setup did not complete.")
        # Announce the final outcome — the run may have taken minutes (gap #4).
        announce(self._status_label, self._status_label.text())
        self._worker = None
        self._thread = None
        self.setup_finished.emit(ready)

    # --- Lifecycle ----------------------------------------------------------

    def _stop(self) -> None:
        """Cancel the run and stop the thread WITHOUT freezing the window.

        A step in flight (dnf, an image pull) can't be interrupted by quit(), so
        we never block the GUI thread waiting for it: stop_thread cancels, waits
        briefly, and detaches a still-running thread (which finishes its step and
        reaps itself) rather than blocking or destroying it (real-user report:
        closing mid-dnf froze the app, then risked a destroyed-while-running
        abort)."""
        from platterpus.workers import stop_thread

        stop_thread(self._thread, self._worker)
        self._worker = None
        self._thread = None

    def reject(self) -> None:  # noqa: D102 — Qt override (Close / Esc)
        self._closing = True
        self._stop()
        super().reject()

    def closeEvent(self, event: object) -> None:  # noqa: N802 — Qt API
        self._closing = True
        self._stop()
        super().closeEvent(event)  # type: ignore[arg-type]
