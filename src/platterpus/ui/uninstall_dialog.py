"""In-app Uninstaller — removes everything Platterpus created, with choices to keep some.

The owner's requirement (2026-11-18, TASKS R190): a full removal by default,
so a reinstall is truly fresh, with boxes to keep (a) settings and measured
drive data, (b) logs, test runs and support bundles, and (c) MusicBrainz
Picard. Two more boxes are OFF unless ticked: (d) delete the rips in the folder
the settings name, and (e) remove Distrobox and podman, shown ONLY when the
install note says Platterpus installed them.

The flow: on open, a worker scans the computer (``deps/host_teardown``) and
the dialog shows a preview of exactly what will go and what will stay, updated
as boxes change. "Uninstall…" asks once, then a second worker removes, with
live progress, and the result names anything still on disk after a re-scan —
so the last line says what happened, not what was asked.

Both the scan and the removal run on worker threads (they ask ``podman`` and
``flatpak``, which can take a minute); closing the dialog cancels the worker,
which kills the command in flight (CLAUDE.md rule 9).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from platterpus.deps.host_teardown import HostTeardown
from platterpus.deps.install_footprint import Group
from platterpus.deps.step_engine import StepResult, StepStatus
from platterpus.deps.uninstall_plan import (
    Choices,
    Observation,
    UninstallReport,
    build_plan,
    preview_lines,
    summary,
)
from platterpus.deps.uninstall_runner import CommandKiller
from platterpus.ui import message_boxes
from platterpus.ui.accessibility import announce
from platterpus.ui.dialogs.centering import CenteredDialog
from platterpus.ui.failure_text import LOG_POINTER
from platterpus.ui.scroll_guards import append_keeping_position
from platterpus.workers import start_worker_thread, stop_thread
from platterpus.workers.uninstall_worker import UninstallWorker

log = logging.getLogger(__name__)

_STATUS_GLYPH: dict[StepStatus, str] = {
    StepStatus.DONE: "ⓘ",
    StepStatus.RAN: "✓",
    StepStatus.FAILED: "⚠",
    StepStatus.CANCELLED: "•",
}


#: Builds one engine and the runner that can kill its commands. One per run.
EngineFactory = Callable[[Path | None], tuple[HostTeardown, CommandKiller]]


class UninstallDialog(CenteredDialog):
    """Modal uninstaller: keep boxes, a preview, a confirmation, live progress."""

    # True when everything planned was removed and nothing is left; the main
    # window then offers to close the app.
    uninstall_finished = Signal(bool)

    def __init__(
        self,
        parent: QWidget | None = None,
        build_engine: EngineFactory | None = None,
        rips: tuple[Path | None, str] | None = None,
        scan_on_open: bool = True,
    ) -> None:
        """``build_engine`` and ``rips`` (folder, refusal reason) are injectable
        for tests; ``scan_on_open=False`` leaves the scan to the test."""
        super().__init__(parent)
        self._build_engine: EngineFactory = build_engine or _default_build_engine
        self._rips_folder, rips_refusal = (
            rips if rips is not None else _rips_from_settings()
        )
        self._observations: tuple[Observation, ...] = ()
        self._thread: QThread | None = None
        self._worker: UninstallWorker | None = None
        self._closing: bool = False

        self.setWindowTitle("Uninstall Platterpus")
        self.resize(640, 620)
        self.setMinimumSize(520, 480)
        root = QVBoxLayout(self)

        intro = QLabel(
            "This removes everything Platterpus put on this computer, so a "
            "reinstall starts fresh: the app, its shortcuts, the 'ripping' "
            "container and its image, the cyanrip build cache, Picard, settings "
            "and logs. Tick what you want to keep.",
            self,
        )
        intro.setTextFormat(Qt.TextFormat.PlainText)
        intro.setWordWrap(True)
        root.addWidget(intro)

        keep_box = QGroupBox("Keep", self)
        keep_layout = QVBoxLayout(keep_box)
        self._keep_settings: QCheckBox = QCheckBox(
            "My settings and measured drive data", keep_box
        )
        self._keep_logs: QCheckBox = QCheckBox(
            "Logs, test runs and support bundles", keep_box
        )
        self._keep_picard: QCheckBox = QCheckBox("MusicBrainz Picard", keep_box)
        for box in (self._keep_settings, self._keep_logs, self._keep_picard):
            keep_layout.addWidget(box)
        root.addWidget(keep_box)

        also_box = QGroupBox("Also remove (only if ticked)", self)
        also_layout = QVBoxLayout(also_box)
        if self._rips_folder is not None:
            rips_text = f"Delete my rips in {self._rips_folder}"
        else:
            rips_text = f"Delete my rips (not offered: {rips_refusal})"
        self._remove_rips: QCheckBox = QCheckBox(rips_text, also_box)
        self._remove_rips.setEnabled(self._rips_folder is not None)
        self._remove_packages: QCheckBox = QCheckBox(
            "Distrobox and podman (Platterpus installed them)", also_box
        )
        # Shown only when the scan finds packages the install note names.
        self._remove_packages.setVisible(False)
        also_layout.addWidget(self._remove_rips)
        also_layout.addWidget(self._remove_packages)
        root.addWidget(also_box)
        for box in self._choice_boxes():
            box.toggled.connect(self._refresh_preview)

        self._details: QPlainTextEdit = QPlainTextEdit(
            "Checking what is on this computer…", self
        )
        self._details.setReadOnly(True)
        self._details.setAccessibleName("Uninstall preview and results")
        root.addWidget(self._details, stretch=1)

        self._progress: QProgressBar = QProgressBar(self)
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        self._status_label: QLabel = QLabel("", self)
        # PlainText: a failed step's detail quotes a tool's output.
        self._status_label.setTextFormat(Qt.TextFormat.PlainText)
        self._status_label.setWordWrap(True)
        self._status_label.setAccessibleName("Uninstall status")
        root.addWidget(self._status_label)

        self._uninstall_button: QPushButton = QPushButton("&Uninstall…", self)
        self._uninstall_button.setEnabled(False)
        self._uninstall_button.clicked.connect(self._on_uninstall_clicked)
        self._button_box: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, self
        )
        self._button_box.addButton(
            self._uninstall_button, QDialogButtonBox.ButtonRole.DestructiveRole
        )
        self._button_box.rejected.connect(self.reject)
        root.addWidget(self._button_box)

        if scan_on_open:
            self._start(scan=True)

    # --- Choices and preview -------------------------------------------------

    def _choice_boxes(self) -> tuple[QCheckBox, ...]:
        return (
            self._keep_settings,
            self._keep_logs,
            self._keep_picard,
            self._remove_rips,
            self._remove_packages,
        )

    def choices(self) -> Choices:
        """The boxes, as the engine reads them."""
        return Choices(
            keep_settings=self._keep_settings.isChecked(),
            keep_logs=self._keep_logs.isChecked(),
            keep_picard=self._keep_picard.isChecked(),
            remove_rips=self._remove_rips.isChecked() and self._rips_folder is not None,
            remove_system_packages=(
                self._remove_packages.isChecked()
                and self._remove_packages.isVisibleTo(self)
            ),
        )

    def _on_scanned(self, observations: tuple[Observation, ...]) -> None:
        if self._closing:
            return
        self._observations = observations
        packages = [
            o
            for o in observations
            if o.item.group is Group.SYSTEM_PACKAGES and o.present
        ]
        self._remove_packages.setVisible(bool(packages))
        self._uninstall_button.setEnabled(bool(observations))
        if not observations:
            self._status_label.setText(
                f"⚠ Could not check this computer. {LOG_POINTER}"
            )
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        if not self._observations or self._worker is not None:
            return
        plan = build_plan(self._observations, self.choices())
        self._details.setPlainText("\n".join(preview_lines(plan)))
        self._uninstall_button.setEnabled(not plan.nothing_to_do)

    # --- Run flow ------------------------------------------------------------

    def _on_uninstall_clicked(self) -> None:
        if self._worker is not None:  # a job is running
            return
        choices = self.choices()
        text = (
            "Remove everything listed under “Will remove”?\n\n"
            "This can't be undone (you can always reinstall)."
        )
        if choices.remove_rips:
            text += f"\n\nYour rips in {self._rips_folder} will be DELETED."
        choice = message_boxes.warning(
            self,
            "Uninstall Platterpus?",
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return
        for box in self._choice_boxes():
            box.setEnabled(False)
        self._uninstall_button.setEnabled(False)
        self._details.clear()
        self._status_label.setText("Uninstalling…")
        self._start(scan=False, choices=choices)

    def _start(self, scan: bool, choices: Choices | None = None) -> None:
        engine, runner = self._build_engine(self._rips_folder)
        worker = UninstallWorker(engine, runner, choices)
        self._worker = worker
        stop_thread(self._thread)  # the last job's, ended: see `_stop`
        self._thread = QThread(self)
        self._progress.setVisible(True)
        if scan:
            worker.scanned.connect(self._on_scanned)
            worker.finished.connect(self._on_scan_finished)
            start_worker_thread(worker, self._thread, worker.scan)
        else:
            worker.step.connect(self._on_step)
            worker.finished.connect(self._on_finished)
            start_worker_thread(worker, self._thread, worker.remove)

    def _on_scan_finished(self, _report: object) -> None:
        if self._closing:
            return
        self._progress.setVisible(False)
        self._worker = None
        self._refresh_preview()

    def _on_step(self, result: StepResult) -> None:
        if self._closing:
            return
        if result.status is StepStatus.RUNNING:
            text = f"⏳ Removing {result.title}…"
            self._status_label.setText(text)
            announce(self._status_label, text)
            return
        line = f"{_STATUS_GLYPH.get(result.status, '•')} {result.title}"
        if result.detail:
            line += f" — {result.detail}"
        append_keeping_position(self._details, line)

    def _on_finished(self, report: UninstallReport | None) -> None:
        if self._closing:
            return
        self._progress.setVisible(False)
        self._worker = None
        complete = report is not None and report.complete
        if report is None:
            log.error("uninstall finished without a report")
            self._status_label.setText(
                f"⚠ The uninstall stopped unexpectedly. {LOG_POINTER}"
            )
        elif complete:
            self._status_label.setText(
                f"{summary(report)} Close this app now. "
                "(Reinstall any time from the project page.)"
            )
        else:
            self._report_problems(report)
        if not complete:
            for box in self._choice_boxes():
                box.setEnabled(
                    box is not self._remove_rips or self._rips_folder is not None
                )
            self._uninstall_button.setEnabled(True)
        announce(self._status_label, self._status_label.text())
        self.uninstall_finished.emit(complete)

    def _report_problems(self, report: UninstallReport) -> None:
        if report.leftovers:
            append_keeping_position(self._details, "Still on this computer:")
            for line in report.leftovers:
                append_keeping_position(self._details, f"  ⚠ {line}")
        for r in report.failed:
            log.error("uninstall failed at %s: %s", r.step_id, r.detail)
        self._status_label.setText(f"{summary(report)}\n{LOG_POINTER}")

    # --- Lifecycle -----------------------------------------------------------

    def _stop(self) -> None:
        # Cancel kills the command in flight; a thread that still does not stop
        # in time is ABANDONED with its reference kept (rule 9), never waited on.
        # A finished job keeps `_thread` to here: dropped sooner, SIGABRT (R196).
        stop_thread(self._thread, self._worker)
        self._worker = None
        self._thread = None

    def reject(self) -> None:  # Qt override (Close / Esc)
        self._closing = True
        self._stop()
        super().reject()

    def closeEvent(self, event: object) -> None:  # noqa: N802 — Qt API
        self._closing = True
        self._stop()
        super().closeEvent(event)  # type: ignore[arg-type]


def _rips_from_settings() -> tuple[Path | None, str]:
    """The rips folder the settings name, if deleting it is safe; else the reason."""
    from platterpus.deps.user_locations import rips_setting, safe_rips_folder
    from platterpus.paths import CONFIG_PATH

    return safe_rips_folder(rips_setting(CONFIG_PATH), Path.home())


def _default_build_engine(rips: Path | None) -> tuple[HostTeardown, CommandKiller]:
    """Production engine: the killable runner, the real folders, this process's AppImage."""
    import sys

    from platterpus.appimage_integration import appimage_path
    from platterpus.deps.uninstall_runner import UninstallRunner
    from platterpus.deps.user_locations import Locations, dev_checkout_venv

    runner = UninstallRunner()
    engine = HostTeardown(
        runner=runner,
        locations=Locations.from_environment(),
        appimage=appimage_path(),
        venv=dev_checkout_venv(Path(sys.prefix)),
        rips=rips,
    )
    return engine, runner
