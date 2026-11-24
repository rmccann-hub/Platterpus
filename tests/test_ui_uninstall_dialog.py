"""Tests for the in-app Uninstaller dialog (TASKS R190).

The scan and removal slots are driven directly with fake observations and
reports (no thread, nothing removed); the run flow is tested with a fake engine
factory and a monkeypatched confirmation.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from platterpus.deps.install_footprint import FootprintItem, Group, Kind
from platterpus.deps.step_engine import StepResult, StepStatus
from platterpus.deps.uninstall_plan import (
    Choices,
    Observation,
    Plan,
    UninstallReport,
)
from platterpus.paths import LOG_PATH
from platterpus.ui import message_boxes
from platterpus.ui.uninstall_dialog import UninstallDialog


def _item(
    item_id: str, group: Group = Group.APP, kind: Kind = Kind.TREE
) -> FootprintItem:
    return FootprintItem(item_id, f"title of {item_id}", kind, group, path=Path("/x"))


def _observations() -> tuple[Observation, ...]:
    return (
        Observation(_item("cache"), present=("/home/u/.cache/platterpus",)),
        Observation(
            _item("settings", Group.SETTINGS), present=("/home/u/.config/platterpus",)
        ),
        Observation(
            _item("logs", Group.LOGS), present=("/home/u/.local/share/platterpus",)
        ),
        Observation(
            _item("picard", Group.PICARD, Kind.FLATPAK_APP),
            present=("org.musicbrainz.Picard",),
        ),
        Observation(_item("rips", Group.RIPS), present=("/home/u/Music/rips",)),
    )


def _dialog(
    qapp: QApplication,
    build=None,
    rips: tuple[Path | None, str] = (Path("/home/u/Music/rips"), ""),
) -> UninstallDialog:
    return UninstallDialog(
        build_engine=build or (lambda _rips: (None, None)),
        rips=rips,
        scan_on_open=False,
    )


def _report(**kwargs: object) -> UninstallReport:
    defaults: dict[str, object] = {"plan": Plan(), "results": (), "leftovers": ()}
    defaults.update(kwargs)
    return UninstallReport(**defaults)  # type: ignore[arg-type]  # test kwargs


def test_defaults_remove_everything_but_rips_and_packages(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    assert dialog.choices() == Choices()
    assert not dialog._remove_rips.isChecked()
    assert dialog._remove_packages.isVisibleTo(dialog) is False


def test_the_preview_lists_what_goes_and_what_stays(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    dialog._on_scanned(_observations())
    text = dialog._details.toPlainText()
    assert text.startswith("Will remove:")
    assert "/home/u/.config/platterpus" in text.split("Will keep:")[0]
    assert "Music/rips (you chose to keep your rips)" in text
    assert dialog._uninstall_button.isEnabled()

    dialog._keep_settings.setChecked(True)  # the preview follows the boxes
    kept = dialog._details.toPlainText().split("Will keep:")[1]
    assert "/home/u/.config/platterpus" in kept


def test_the_rips_box_names_the_configured_folder_or_why_not(
    qapp: QApplication,
) -> None:
    named = _dialog(qapp, rips=(Path("/srv/flac"), ""))
    assert "/srv/flac" in named._remove_rips.text() and named._remove_rips.isEnabled()
    refused = _dialog(
        qapp, rips=(None, "the rips folder is the root of the filesystem")
    )
    assert "root of the filesystem" in refused._remove_rips.text()
    assert not refused._remove_rips.isEnabled()
    refused._remove_rips.setChecked(True)
    assert refused.choices().remove_rips is False


def test_the_packages_box_appears_only_when_the_note_names_them(
    qapp: QApplication,
) -> None:
    dialog = _dialog(qapp)
    dialog._on_scanned(_observations())
    assert not dialog._remove_packages.isVisibleTo(dialog)
    package = Observation(
        _item("package:podman", Group.SYSTEM_PACKAGES, Kind.SYSTEM_PACKAGE),
        present=("podman",),
    )
    dialog._on_scanned((*_observations(), package))
    assert dialog._remove_packages.isVisibleTo(dialog)
    dialog._remove_packages.setChecked(True)
    assert dialog.choices().remove_system_packages


def test_confirm_cancel_runs_nothing(qapp: QApplication, monkeypatch) -> None:
    built: list[object] = []
    dialog = _dialog(qapp, build=lambda rips: built.append(rips))
    dialog._on_scanned(_observations())
    monkeypatch.setattr(
        message_boxes, "warning", lambda *a, **k: QMessageBox.StandardButton.Cancel
    )
    dialog._on_uninstall_clicked()
    assert built == []
    assert dialog._thread is None


def test_confirm_yes_runs_the_engine_with_the_boxes(
    qapp: QApplication, monkeypatch
) -> None:
    seen: list[Choices] = []
    asked: list[str] = []

    class _Engine:
        def run(self, choices, progress=None, cancelled=None):
            seen.append(choices)
            return _report()

    class _Runner:
        def cancel(self) -> None:
            pass

    dialog = _dialog(qapp, build=lambda _rips: (_Engine(), _Runner()))
    dialog._on_scanned(_observations())
    dialog._keep_logs.setChecked(True)
    dialog._remove_rips.setChecked(True)
    monkeypatch.setattr(
        message_boxes,
        "warning",
        lambda _p, _t, text, *a, **k: (
            asked.append(text) or QMessageBox.StandardButton.Yes
        ),
    )
    dialog._on_uninstall_clicked()
    dialog._stop()  # joins the worker without pumping global events

    assert seen == [Choices(keep_logs=True, remove_rips=True)]
    assert "/home/u/Music/rips will be DELETED" in asked[0]


def test_success_says_what_the_rescan_found_and_signals(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    seen: list[bool] = []
    dialog.uninstall_finished.connect(seen.append)
    dialog._on_finished(
        _report(results=(StepResult("cache", "cache", StepStatus.RAN),))
    )
    assert dialog._status_label.text().startswith(
        "✓ Uninstalled, and a check afterwards"
    )
    assert dialog._uninstall_button.isEnabled() is False
    assert seen == [True]


def test_leftovers_and_failures_are_reported(
    qapp: QApplication, caplog: pytest.LogCaptureFixture
) -> None:
    dialog = _dialog(qapp)
    seen: list[bool] = []
    dialog.uninstall_finished.connect(seen.append)
    failed = StepResult(
        "container", "the 'ripping' container", StepStatus.FAILED, "in use"
    )
    with caplog.at_level(logging.ERROR):
        dialog._on_finished(
            _report(results=(failed,), leftovers=("menu icon: /home/u/icon.png",))
        )
    status = dialog._status_label.text()
    assert "Could not remove: the 'ripping' container" in status
    assert "1 item(s) are still on this computer" in status
    assert str(LOG_PATH) in status
    assert "menu icon: /home/u/icon.png" in dialog._details.toPlainText()
    assert "in use" in caplog.text
    assert dialog._uninstall_button.isEnabled()
    assert seen == [False]


def test_a_missing_report_is_not_called_success(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    seen: list[bool] = []
    dialog.uninstall_finished.connect(seen.append)
    dialog._on_finished(None)
    assert dialog._status_label.text().startswith("⚠")
    assert seen == [False]


def test_steps_go_to_the_status_line_and_the_details(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    dialog._on_step(StepResult("cache", "the cache", StepStatus.RUNNING))
    assert "the cache" in dialog._status_label.text()
    assert "the cache" not in dialog._details.toPlainText()
    dialog._on_step(StepResult("cache", "the cache", StepStatus.RAN, "removed /x"))
    assert "✓ the cache — removed /x" in dialog._details.toPlainText()


def test_a_click_while_running_is_ignored(qapp: QApplication, monkeypatch) -> None:
    built: list[object] = []
    dialog = _dialog(qapp, build=lambda rips: built.append(rips))
    dialog._worker = object()  # type: ignore[assignment]  # a job is running
    monkeypatch.setattr(
        message_boxes, "warning", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    dialog._on_uninstall_clicked()
    assert built == []
    dialog._worker = None


def test_nothing_updates_while_closing(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    dialog._closing = True
    seen: list[bool] = []
    dialog.uninstall_finished.connect(seen.append)
    dialog._on_step(StepResult("x", "x", StepStatus.RAN, "x"))
    dialog._on_finished(_report())
    dialog._on_scanned(_observations())
    assert seen == []
    assert dialog._observations == ()


def test_close_and_reject_stop_the_worker(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    dialog.reject()
    assert dialog._closing and dialog._thread is None
    other = _dialog(qapp)
    other.close()
    assert other._closing and other._thread is None


def test_progress_and_outcome_are_announced(qapp: QApplication, monkeypatch) -> None:
    heard: list[str] = []
    monkeypatch.setattr(
        "platterpus.ui.uninstall_dialog.announce",
        lambda _source, message: heard.append(message) or True,
    )
    dialog = _dialog(qapp)
    dialog._on_step(StepResult("cache", "the cache", StepStatus.RUNNING))
    dialog._on_finished(_report())
    assert any("the cache" in m for m in heard)
    assert heard[-1] == dialog._status_label.text()


def test_the_scan_runs_on_a_worker_thread(qapp: QApplication, process_until) -> None:
    """The real engine shape, through the real worker: scanned, then finished."""
    import threading

    threads: list[str] = []

    class _Engine:
        def scan(self):
            threads.append(threading.current_thread().name)
            return _observations()

    class _Runner:
        def cancel(self) -> None:
            pass

    dialog = UninstallDialog(
        build_engine=lambda _rips: (_Engine(), _Runner()),
        rips=(None, "not configured"),
        scan_on_open=True,
    )
    assert dialog._thread is not None
    assert process_until(lambda: dialog._worker is None)
    assert threads and threads[0] != threading.main_thread().name
    assert dialog._details.toPlainText().startswith("Will remove:")
    dialog.reject()


def test_a_finished_scan_keeps_its_thread_until_the_dialog_stops_it(
    qapp: QApplication, process_until, monkeypatch
) -> None:
    """A finished job's thread may still be quitting, so the dialog keeps it and
    stops it on close. Dropping it at the worker's `finished` let a close destroy
    the thread while it ran: SIGABRT, main's CI of 2026-11-24 (py3.12, this
    file's worker-thread test)."""
    from platterpus.ui import uninstall_dialog as module

    class _Engine:
        def scan(self):
            return _observations()

    class _Runner:
        def cancel(self) -> None:
            pass

    dialog = UninstallDialog(
        build_engine=lambda _rips: (_Engine(), _Runner()),
        rips=(None, "not configured"),
        scan_on_open=True,
    )
    scan_thread = dialog._thread
    assert scan_thread is not None
    assert process_until(lambda: dialog._worker is None)
    assert dialog._thread is scan_thread, "the finished scan's thread was dropped"
    stopped: list[object] = []
    real_stop = module.stop_thread
    monkeypatch.setattr(
        module,
        "stop_thread",
        lambda thread, *a, **k: (stopped.append(thread), real_stop(thread, *a, **k)),
    )
    dialog.reject()
    assert stopped == [scan_thread], "closing did not stop the scan's thread"
    assert dialog._thread is None
