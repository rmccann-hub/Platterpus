"""In-app Uninstaller — removes everything this app installed, no terminal.

The GUI counterpart of ``uninstall.sh`` (current-plan item 4; standing user
request): one dialog that removes the app's shortcuts, the host-exported
binaries, the `ripping` container, optionally `whipper.conf` and the AppImage
file, and the GUI's own settings + logs — while **always keeping
Distrobox/podman and all music**.

Structure mirrors ``HostSetupDialog``: the engine
(`deps/host_teardown.HostTeardown`) runs off-thread via the shared
:class:`HostSetupWorker`, with live per-step progress and clean thread
teardown on close. The destructive action is double-gated: a confirm prompt
before anything runs, and per-piece checkboxes for the optional parts.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from platterpus.deps.host_teardown import HostTeardown
from platterpus.deps.step_engine import StepResult, StepStatus
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


class UninstallDialog(CenteredDialog):
    """Modal uninstaller with per-piece checkboxes and live progress."""

    # True when everything selected was removed — the main window then
    # offers to close the app (its config no longer exists on disk).
    uninstall_finished = Signal(bool)

    def __init__(
        self,
        parent: QWidget | None = None,
        build_teardown: Callable[[bool, bool], HostTeardown] | None = None,
    ) -> None:
        """`build_teardown(remove_container, remove_whipper_config) ->
        HostTeardown` is injectable for tests; production builds the real
        engine (SubprocessRunner + the running AppImage path, if any)."""
        super().__init__(parent)
        self._build_teardown = build_teardown or _default_build_teardown
        self._teardown: HostTeardown | None = None
        self._thread: QThread | None = None
        self._worker: HostSetupWorker | None = None
        self._closing: bool = False

        self.setWindowTitle("Uninstall Platterpus")
        self.resize(580, 480)
        self.setMinimumSize(480, 380)

        root = QVBoxLayout(self)

        intro = QLabel(
            "This removes what Platterpus installed on this computer:\n\n"
            "• menu and desktop shortcuts\n"
            "• whipper / metaflac / cyanrip from ~/.local/bin\n"
            "• the app's own settings and logs\n"
            "• the items ticked below\n\n"
            "<b>Never touched:</b> your music, and Distrobox/podman "
            "themselves (other containers keep working).",
            self,
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        self._container_check: QCheckBox = QCheckBox(
            "Remove the 'ripping' container (whipper + cyanrip inside it)", self
        )
        self._container_check.setChecked(True)
        root.addWidget(self._container_check)

        self._whipper_conf_check: QCheckBox = QCheckBox(
            "Remove whipper.conf (your drive calibration)", self
        )
        self._whipper_conf_check.setChecked(True)
        root.addWidget(self._whipper_conf_check)

        self._uninstall_button: QPushButton = QPushButton("Uninstall…", self)
        self._uninstall_button.clicked.connect(self._on_uninstall_clicked)
        root.addWidget(self._uninstall_button)

        self._progress: QProgressBar = QProgressBar(self)
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        self._status_label: QLabel = QLabel("", self)
        self._status_label.setWordWrap(True)
        root.addWidget(self._status_label)

        self._results: QPlainTextEdit = QPlainTextEdit("", self)
        self._results.setReadOnly(True)
        root.addWidget(self._results, stretch=1)

        self._button_box: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, self
        )
        self._button_box.rejected.connect(self.reject)
        root.addWidget(self._button_box)

    # --- Run flow -------------------------------------------------------

    def _on_uninstall_clicked(self) -> None:
        if self._thread is not None:  # already running
            return
        # The one confirmation gate before anything destructive happens.
        choice = QMessageBox.warning(
            self,
            "Uninstall Platterpus?",
            "Remove Platterpus and the ticked items from this computer?\n\n"
            "Your music is not touched. This can't be undone (you can "
            "always reinstall later).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return

        self._teardown = self._build_teardown(
            self._container_check.isChecked(),
            self._whipper_conf_check.isChecked(),
        )
        self._uninstall_button.setEnabled(False)
        self._container_check.setEnabled(False)
        self._whipper_conf_check.setEnabled(False)
        self._results.clear()
        self._progress.setVisible(True)
        self._status_label.setText("Uninstalling…")

        self._worker = HostSetupWorker(self._teardown)
        self._thread = QThread(self)
        self._worker.step.connect(self._on_step)
        self._worker.finished.connect(self._on_finished)
        start_worker_thread(self._worker, self._thread, self._worker.run)

    def _on_step(self, result: StepResult) -> None:
        if self._closing:
            return
        if result.status is StepStatus.RUNNING:
            self._status_label.setText(f"⏳ {result.title}")
            return
        line = f"{_STATUS_GLYPH.get(result.status, '•')} {result.title}"
        if result.detail:
            line += f" — {result.detail}"
        self._results.appendPlainText(line)

    def _on_finished(self, results: list[StepResult]) -> None:
        if self._closing:
            return
        self._progress.setVisible(False)
        complete = bool(results) and all(r.ok for r in results)
        if complete:
            self._status_label.setText(
                "✓ Uninstalled. Close this app — it no longer has settings "
                "on disk. (Reinstall any time from the project page.)"
            )
        else:
            failed = next((r for r in results if r.status is StepStatus.FAILED), None)
            if failed is not None:
                self._status_label.setText(
                    f"Uninstall stopped at “{failed.title}”: {failed.detail}"
                )
            else:
                self._status_label.setText("Uninstall did not complete.")
            self._uninstall_button.setEnabled(True)
            self._container_check.setEnabled(True)
            self._whipper_conf_check.setEnabled(True)
        self._worker = None
        self._thread = None
        self.uninstall_finished.emit(complete)

    # --- Lifecycle --------------------------------------------------------

    def _stop(self) -> None:
        # Don't block the GUI thread joining a step in flight (podman/container
        # teardown can't be interrupted by quit()); stop_thread cancels, waits
        # briefly, and detaches a still-running thread rather than freezing the
        # window or destroying a live QThread.
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


def _default_build_teardown(
    remove_container: bool, remove_whipper_config: bool
) -> HostTeardown:
    """Production teardown: real runner + the running AppImage (if any)."""
    from platterpus.appimage_integration import appimage_path
    from platterpus.deps.step_engine import SubprocessRunner

    return HostTeardown(
        runner=SubprocessRunner(),
        remove_container=remove_container,
        remove_whipper_config=remove_whipper_config,
        appimage=appimage_path(),
    )
