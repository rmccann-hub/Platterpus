"""Headless smoke test of the REAL app.main() startup path.

Unit tests build MainWindow with fakes; nothing else exercises the actual entry
point — the composition root in app.py, the real adapters, and a turn of the
real event loop. This test does, under offscreen Qt, hermetically (fresh empty
config; the subprocess probe layer + drive listing stubbed, so no real
whipper/flatpak/container/network).

It guards two things unit tests can't:

1. The real app composes and comes up (menus + widgets present, exits cleanly).
2. The launch dependency check applies its result ON THE GUI THREAD. The
   `finished` signal was once connected to a lambda, which Qt delivers as a
   DirectConnection — so the handler (which builds "install this dependency"
   resolver dialogs) ran on the *worker* thread, creating widgets off the GUI
   thread (Qt logged "QObject::setParent: ... in a different thread"). This test
   stubs the probes so whipper + metaflac report missing → the resolver-dialog
   path runs, records the thread it ran on, and fails on any cross-thread Qt
   warning. (Found originally by a manual smoke-run; codified here.)
"""

from __future__ import annotations

import sys
import threading
import time

import pytest
from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtWidgets import QApplication, QDialog, QMenu, QMessageBox


def test_app_main_starts_up_clean_on_the_gui_thread(
    qapp, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    from platterpus import app as app_module
    from platterpus import config as config_module
    from platterpus.ui.main_window import MainWindow
    from platterpus.ui.main_window_deps import DependencyMixin

    # --- Hermetic + non-polluting startup -----------------------------------
    # Fresh config in a temp dir (never touch the real ~/.config).
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.toml")
    # Don't reconfigure global logging (it adds persistent root handlers).
    monkeypatch.setattr(
        "platterpus.logging_setup.configure_logging", lambda *a, **k: None
    )
    # Stub the subprocess probe layer: every version probe "fails", so the
    # required deps (whipper, metaflac) report missing → the manual resolver
    # dialog path runs — exactly where the cross-thread bug lived — with no real
    # subprocess.
    monkeypatch.setattr(
        "platterpus.deps.checks._run_version_command", lambda argv: (False, "", None)
    )
    # The launch drive listing must not shell out to a (possibly installed)
    # cyanrip that would enter the Distrobox container.
    monkeypatch.setattr(
        "platterpus.adapters.cyanrip_backend.CyanripImpl.list_drives",
        lambda self: [],
    )
    # main() installs its own excepthook; snapshot so monkeypatch restores ours.
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)

    # Neuter every modal so first-run offers / resolver dialogs never block.
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No),
    )
    monkeypatch.setattr(
        QMessageBox,
        "information",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok),
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No),
    )
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok),
    )
    monkeypatch.setattr(QDialog, "exec", lambda self: 0)

    # Record which thread the launch dep-check report is applied on.
    apply_threads: list[bool] = []
    orig_apply = DependencyMixin._apply_dependency_report

    def recording_apply(self, *args, **kwargs):
        apply_threads.append(threading.current_thread() is threading.main_thread())
        return orig_apply(self, *args, **kwargs)

    monkeypatch.setattr(DependencyMixin, "_apply_dependency_report", recording_apply)

    # Capture Qt warnings; the cross-thread one is what we're guarding against.
    qt_messages: list[str] = []
    old_handler = qInstallMessageHandler(lambda mode, ctx, msg: qt_messages.append(msg))

    results: dict[str, object] = {}

    def fake_exec(self) -> int:
        # We're now "inside" the running app. Pump the real loop so off-thread
        # probes deliver their queued results (applied on THIS, the GUI thread)
        # and any first-run singleShots fire (neutered), then introspect + close.
        try:
            deadline = time.monotonic() + 5.0
            while not apply_threads and time.monotonic() < deadline:
                self.processEvents()
                time.sleep(0.005)
            self.processEvents()
            wins = [w for w in self.topLevelWidgets() if isinstance(w, MainWindow)]
            results["window_found"] = bool(wins)
            if wins:
                window = wins[0]
                results["menus"] = [
                    m.title() for m in window.menuBar().findChildren(QMenu)
                ]
                results["widgets_ok"] = all(
                    hasattr(window, attr)
                    for attr in (
                        "_drive_picker",
                        "_disc_info_panel",
                        "_track_table",
                        "_rip_controls",
                        "_rip_progress",
                    )
                )
                window.close()  # exercise closeEvent → joins the launch threads
        except Exception as exc:  # noqa: BLE001 — record, never hang the loop
            results["exec_error"] = repr(exc)
        return 0

    monkeypatch.setattr(QApplication, "exec", fake_exec)

    try:
        rc = app_module.main([])
    finally:
        qInstallMessageHandler(old_handler)

    assert results.get("exec_error") is None, results.get("exec_error")
    assert rc == 0  # clean startup, no fatal-error path
    assert results.get("window_found") is True
    menus = results.get("menus") or []
    assert "&File" in menus and "&Tools" in menus and "&Help" in menus
    assert results.get("widgets_ok") is True
    # Regression: the launch dep-check applied on the GUI thread, not the worker.
    assert apply_threads and all(apply_threads), apply_threads
    # No cross-thread Qt warnings during startup.
    cross_thread = [
        m for m in qt_messages if "different thread" in m or "Cannot set parent" in m
    ]
    assert cross_thread == [], (
        f"cross-thread Qt warnings during startup: {cross_thread}"
    )
