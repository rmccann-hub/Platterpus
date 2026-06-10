"""Tests for the in-app Uninstaller dialog.

Render slots are driven directly with fake results (no QThread, nothing
removed); the run flow is tested with a fake teardown factory and a
monkeypatched confirm prompt.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMessageBox

from whipper_gui.deps.host_setup import StepResult, StepStatus
from whipper_gui.ui.uninstall_dialog import UninstallDialog


def _dialog(qapp: QApplication, build=None) -> UninstallDialog:
    return UninstallDialog(build_teardown=build or (lambda *a: None))


def test_checkboxes_default_to_remove_everything(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    assert dialog._container_check.isChecked() is True
    assert dialog._whipper_conf_check.isChecked() is True


def test_confirm_cancel_runs_nothing(qapp: QApplication, monkeypatch) -> None:
    built: list = []
    dialog = _dialog(qapp, build=lambda *a: built.append(a))
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.Cancel
    )
    dialog._on_uninstall_clicked()
    assert built == []  # declined → no teardown was even constructed
    assert dialog._thread is None


def test_confirm_yes_builds_teardown_from_checkboxes(
    qapp: QApplication, monkeypatch
) -> None:
    """The ticked boxes flow into the engine; the worker thread starts."""

    class _InstantEngine:
        def __init__(self, args):
            self.args = args

        def run(self, progress=None, dry_run=False, cancelled=None):
            return [StepResult("shortcuts", "Shortcuts", StepStatus.DONE)]

    built: list = []

    def build(remove_container: bool, remove_whipper_config: bool):
        built.append((remove_container, remove_whipper_config))
        return _InstantEngine(built[-1])

    dialog = _dialog(qapp, build=build)
    dialog._whipper_conf_check.setChecked(False)
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.Yes
    )

    dialog._on_uninstall_clicked()
    # `built` is appended synchronously before the thread starts; join the
    # worker via the dialog's own teardown (no event pumping — processing
    # global events here would fire stale deferred events from other tests).
    dialog._stop()

    assert built == [(True, False)]


def test_on_finished_success_locks_ui_and_signals(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    dialog._uninstall_button.setEnabled(False)  # as the run flow leaves it
    seen: list[bool] = []
    dialog.uninstall_finished.connect(seen.append)

    dialog._on_finished(
        [
            StepResult("shortcuts", "Shortcuts", StepStatus.RAN, "removed …"),
            StepResult("app_data", "Settings + logs", StepStatus.RAN),
        ]
    )

    assert "✓" in dialog._status_label.text()
    assert "Close this app" in dialog._status_label.text()
    # No "try again" affordance after success — the app should be closed.
    assert dialog._uninstall_button.isEnabled() is False
    assert seen == [True]


def test_on_finished_failure_reenables_and_reports(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    dialog._uninstall_button.setEnabled(False)
    seen: list[bool] = []
    dialog.uninstall_finished.connect(seen.append)

    dialog._on_finished(
        [
            StepResult("shortcuts", "Shortcuts", StepStatus.RAN),
            StepResult(
                "container",
                "'ripping' container",
                StepStatus.FAILED,
                "container is in use",
            ),
            StepResult("app_data", "Settings + logs", StepStatus.CANCELLED),
        ]
    )

    assert "container is in use" in dialog._status_label.text()
    assert dialog._uninstall_button.isEnabled() is True  # retry possible
    assert seen == [False]


def test_on_step_appends_result_lines(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    dialog._on_step(StepResult("exports", "Exports", StepStatus.RAN, "removed whipper"))
    assert "removed whipper" in dialog._results.toPlainText()
    # RUNNING goes to the status line, not the log.
    dialog._on_step(StepResult("container", "Container", StepStatus.RUNNING))
    assert "Container" in dialog._status_label.text()
    assert "Container" not in dialog._results.toPlainText()
