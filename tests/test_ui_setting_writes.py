"""The controls that save one setting as they change, and the window behind them.

Companion to ``tests/test_setting_homes.py``, which checks WHERE each setting is
edited. This checks that editing it there does the right thing:

* the drive wizard's **Apply this read offset to every rip** tick-box, which
  moved there from Settings;
* the two update-channel tick-boxes in **Setup & Updates**;
* the three test-script settings in the **script console**;
* ``MainWindow._save_user_setting``, the one writer all of them go through, and
  Settings' **Apply**, which goes through the other one;
* the rip lock reaching a Setup & Updates window that was already open — a gap
  found while moving *Diagnose drive access…* into it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from conftest import stop_window_threads
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QWidget
from test_ui_drive_setup_dialog import _StubBackend
from test_ui_main_window import _make_window

from platterpus.config import Config
from platterpus.ui.dialogs.script_console import STARTER_SCRIPT, ScriptConsoleDialog
from platterpus.ui.dialogs.setup_center import SetupCenterDialog
from platterpus.ui.drive_setup_dialog import DriveSetupDialog
from platterpus.update_check import CHANNEL_BETA, CHANNEL_STABLE
from platterpus.user_settings import SettingWrite


@pytest.fixture()
def make_window(qapp: QApplication):
    """A real MainWindow, its threads stopped afterwards (as `teardown_threads`)."""
    created: list[Any] = []

    def factory(**kwargs: Any) -> Any:
        window = _make_window(qapp, **kwargs)
        created.append(window)
        return window

    yield factory
    for window in created:
        stop_window_threads(window)
        window.deleteLater()


def _center(
    config: Config,
    save: Any,
    actions: dict[str, Any] | None = None,
) -> SetupCenterDialog:
    return SetupCenterDialog(
        None,
        app_version="0.0.0",
        ripper_pin="0000000",
        ripper_version="0.0.0",
        approved_by_round=0,
        dependency_report=None,
        actions=actions or {},
        config=config,
        save_setting=save,
    )


# --- The drive wizard's Apply tick-box --------------------------------------


def test_the_apply_box_starts_from_the_config_and_reports_each_click(
    qapp: QApplication,
) -> None:
    dialog = DriveSetupDialog(_StubBackend(), "/dev/sr0", offset_applied=False)
    heard: list[bool] = []
    dialog.offset_applied_changed.connect(heard.append)
    assert dialog._apply_offset_check.isChecked() is False
    dialog._apply_offset_check.setChecked(True)
    dialog._apply_offset_check.setChecked(False)
    assert heard == [True, False]
    assert "not apply any read offset" in dialog._status_label.text()


def test_saving_an_offset_ticks_the_box_without_a_second_change(
    qapp: QApplication,
) -> None:
    """Save means "use this offset", so the box follows — quietly."""
    dialog = DriveSetupDialog(_StubBackend(), "/dev/sr0", offset_applied=False)
    saved: list[int] = []
    applied: list[bool] = []
    dialog.manual_offset_saved.connect(saved.append)
    dialog.offset_applied_changed.connect(applied.append)
    dialog._offset_spin.setValue(667)
    dialog._save_offset_button.click()
    assert saved == [667]
    assert dialog._apply_offset_check.isChecked() is True
    assert applied == [], "Save emitted a redundant apply change"


def test_the_legacy_whipper_line_is_shown_only_when_there_is_one(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """It moved with the offset, and stopped printing "none set" to everyone."""
    from platterpus import offset_config
    from platterpus.offset_config import WhipperConfOffset

    monkeypatch.setattr(offset_config, "read_drive_offsets", lambda *a: [])
    dialog = DriveSetupDialog(_StubBackend(), "/dev/sr0")
    assert dialog._legacy_offset_label.isHidden() is True

    found = [WhipperConfOffset(drive="PIONEER:BDR-209D:1.10", offset=667)]
    monkeypatch.setattr(offset_config, "read_drive_offsets", lambda *a: found)
    monkeypatch.setattr(
        offset_config, "describe_conf_offsets", lambda *a: "PIONEER:BDR-209D → +667"
    )
    shown = DriveSetupDialog(_StubBackend(), "/dev/sr0")
    assert shown._legacy_offset_label.isHidden() is False
    assert "whipper.conf" in shown._legacy_offset_label.text()
    assert "+667" in shown._legacy_offset_label.text()
    assert shown._legacy_offset_label.textFormat() == Qt.TextFormat.PlainText


def test_the_window_writes_the_apply_box_and_saves(make_window: Any) -> None:
    saved: list[bool] = []
    window = make_window(
        config=Config(read_offset=667, override_read_offset=True),
        save_cfg=lambda cfg: saved.append(cfg.override_read_offset),
    )
    window._on_offset_applied_changed(False)
    assert window._config.override_read_offset is False
    assert window._config.read_offset == 667, "the offset itself was touched"
    assert saved == [False]


# --- The window's single-setting writer -------------------------------------


def test_save_user_setting_applies_saves_and_reports(make_window: Any) -> None:
    saved: list[str] = []
    window = make_window(save_cfg=lambda cfg: saved.append(cfg.update_channel))
    result = window._save_user_setting("update_channel", CHANNEL_BETA)
    assert result == SettingWrite(True)
    assert window._config.update_channel == CHANNEL_BETA
    assert saved == [CHANNEL_BETA]


def test_save_user_setting_refuses_what_the_validator_refuses(
    make_window: Any, tmp_path: Path
) -> None:
    """Nothing changes and nothing is saved; the validator's sentence comes back."""
    saved: list[object] = []
    window = make_window(save_cfg=saved.append)
    result = window._save_user_setting(
        "test_script_path", str(tmp_path / "no-such-script.txt")
    )
    assert result.applied is False
    assert "No file at" in result.message
    assert window._config.test_script_path == ""
    assert saved == []


def test_save_user_setting_refuses_a_name_that_is_not_a_setting(
    make_window: Any,
) -> None:
    """A wiring typo must be loud, and app state is not the user's to set."""
    window = make_window()
    for name in ("no_such_field", "host_setup_prompted"):
        assert window._save_user_setting(name, True).applied is False, name


def test_save_user_setting_says_so_when_the_disk_write_fails(
    make_window: Any,
) -> None:
    def refuse(_cfg: Config) -> None:
        raise OSError("disk full")

    window = make_window(save_cfg=refuse)
    result = window._save_user_setting("ripper_channel", CHANNEL_BETA)
    assert result.applied is True
    assert "not saved to disk" in result.message and "disk full" in result.message


def test_settings_apply_saves_and_cancel_then_keeps_it(
    make_window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KDE's meaning of Cancel-after-Apply, through the real window."""
    from platterpus.ui import settings_dialog

    saved: list[int] = []
    window = make_window(save_cfg=lambda cfg: saved.append(cfg.max_retries))

    def apply_then_cancel(self: settings_dialog.SettingsDialog) -> int:
        self._max_retries_spin.setValue(3)
        self._on_apply_clicked()
        assert self.has_unapplied_edits() is False, "Apply did not re-baseline"
        self._max_retries_spin.setValue(9)  # changed after Apply, then cancelled
        return int(QDialog.DialogCode.Rejected)

    monkeypatch.setattr(settings_dialog.SettingsDialog, "exec", apply_then_cancel)
    window._on_open_settings()
    assert window._config.max_retries == 3
    assert saved == [3]


# --- Setup & Updates --------------------------------------------------------


def test_a_channel_click_saves_the_channel_string(qapp: QApplication) -> None:
    calls: list[tuple[str, object]] = []

    def save(field: str, value: object) -> SettingWrite:
        calls.append((field, value))
        return SettingWrite(True)

    center = _center(Config(), save)
    assert center._app_beta_check.isChecked() is False
    center._app_beta_check.setChecked(True)
    center._ripper_beta_check.setChecked(True)
    center._app_beta_check.setChecked(False)
    assert calls == [
        ("update_channel", CHANNEL_BETA),
        ("ripper_channel", CHANNEL_BETA),
        ("update_channel", CHANNEL_STABLE),
    ]
    assert "only stable Platterpus releases" in center._settings_status.text()


def test_a_refused_channel_click_puts_the_box_back(qapp: QApplication) -> None:
    center = _center(Config(), lambda _f, _v: SettingWrite(False, "nope"))
    center._ripper_beta_check.setChecked(True)
    assert center._ripper_beta_check.isChecked() is False
    assert "Not changed: nope" in center._settings_status.text()


def test_refresh_shows_the_config_and_saves_nothing(qapp: QApplication) -> None:
    calls: list[object] = []
    center = _center(Config(), lambda f, v: calls.append((f, v)) or SettingWrite(True))
    center.refresh_settings(
        Config(update_channel=CHANNEL_BETA, read_offset=6, override_read_offset=True)
    )
    assert center._app_beta_check.isChecked() is True
    assert "+6 samples, applied to every rip" in center._offset_label.text()
    assert calls == [], "re-rendering looked like a click"


def test_diagnose_drive_access_lives_in_setup_and_updates(make_window: Any) -> None:
    window = make_window()
    tools = [
        action.text()
        for action in window.menuBar().actions()
        if action.menu() is not None
        for action in action.menu().actions()
    ]
    assert not any("Diagnose" in text for text in tools), tools
    center = window.open_setup_center()
    try:
        assert center._actions["drive_diagnose"] == window._show_drive_access_diagnosis
        assert "drive_diagnose" in center._buttons
    finally:
        center.close()


def test_a_rip_locks_a_setup_and_updates_window_that_was_already_open(
    make_window: Any,
) -> None:
    """The regression: greying the menu item only stopped it being OPENED.

    Before this, a Setup & Updates window left open when a rip started kept every
    button live — Set up drive… → Analyse cache would spin the drive under the
    rip. Every action is locked for the rip and unlocked after it.
    """
    window = make_window()
    center = window.open_setup_center()
    try:
        assert all(button.isEnabled() for button in center._buttons.values())
        window._set_rip_lock(True)
        assert center._buttons, "no buttons to lock"
        assert not any(button.isEnabled() for button in center._buttons.values())
        assert "Locked while a rip runs" in center._settings_status.text()
        # The channel boxes only decide what a later check offers; they stay live.
        assert center._app_beta_check.isEnabled()
        window._set_rip_lock(False)
        assert all(button.isEnabled() for button in center._buttons.values())
        assert center._settings_status.text() == ""
    finally:
        center.close()


def test_a_script_set_reaches_an_open_setup_and_updates(make_window: Any) -> None:
    """A change made elsewhere must not leave the box showing the old channel."""
    window = make_window()
    center = window.open_setup_center()
    try:
        window._save_user_setting("update_channel", CHANNEL_BETA)
        assert center._app_beta_check.isChecked() is True
    finally:
        center.close()


# --- The script console -----------------------------------------------------


def _console(save: Any = None, **kwargs: Any) -> ScriptConsoleDialog:
    return ScriptConsoleDialog(QWidget(), save_setting=save, **kwargs)


def test_the_console_carries_one_unsafe_box_and_it_is_the_setting(
    qapp: QApplication,
) -> None:
    calls: list[tuple[str, object]] = []
    console = _console(
        lambda f, v: calls.append((f, v)) or SettingWrite(True), allow_unsafe=False
    )
    from PySide6.QtWidgets import QCheckBox

    unsafe = [box for box in console.findChildren(QCheckBox) if "unsafe" in box.text()]
    assert unsafe == [console._unsafe_check], "a second unsafe-verbs box is back"
    console._unsafe_check.setChecked(True)
    console._autorun_check.setChecked(True)
    assert calls == [
        ("test_script_allow_unsafe", True),
        ("test_script_autorun", True),
    ]


def test_choosing_a_startup_script_saves_and_loads_it(
    qapp: QApplication, tmp_path: Path
) -> None:
    script = tmp_path / "mine.txt"
    script.write_text("log hello\n", encoding="utf-8")
    calls: list[tuple[str, object]] = []
    console = _console(lambda f, v: calls.append((f, v)) or SettingWrite(True))
    assert console._script_settings.set_startup_script(str(script)) is True
    assert calls == [("test_script_path", str(script))]
    assert console._startup_script_edit.text() == str(script)
    assert console.script_text() == "log hello\n"


def test_a_new_startup_script_never_replaces_a_typed_batch(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The user's typed work outranks a setting change."""
    script = tmp_path / "mine.txt"
    script.write_text("log hello\n", encoding="utf-8")
    console = _console(lambda _f, _v: SettingWrite(True))
    console.set_script_text("log my own batch\n")
    console._script_settings.set_startup_script(str(script))
    assert console.script_text() == "log my own batch\n"
    assert "loads when this console next opens" in (
        console._script_settings.status_text()
    )


def test_a_refused_startup_script_leaves_everything_as_it_was(
    qapp: QApplication,
) -> None:
    console = _console(lambda _f, _v: SettingWrite(False, "No file at: /x"))
    assert console._script_settings.set_startup_script("/x") is False
    assert console._startup_script_edit.text() == ""
    assert console.script_text() == STARTER_SCRIPT
    assert "Not changed: No file at: /x" in console._script_settings.status_text()


def test_use_built_in_sets_a_script_that_exists(qapp: QApplication) -> None:
    """The whole point: no download, no path typed by hand (moved from Settings)."""
    calls: list[tuple[str, object]] = []
    console = _console(lambda f, v: calls.append((f, v)) or SettingWrite(True))
    console._script_settings.use_builtin_acceptance_script()
    chosen = Path(console._startup_script_edit.text())
    assert chosen.is_file(), f"the button set a path that does not exist: {chosen}"
    assert chosen.name == "fullacceptance.txt"
    assert len(chosen.read_text(encoding="utf-8").splitlines()) > 100
    assert calls == [("test_script_path", str(chosen))]


def test_use_built_in_says_why_when_the_script_is_missing(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing branch surfaces a sentence, in PlainText, and sets nothing."""
    import platterpus.ui.dialogs.script_settings_box as module

    monkeypatch.setattr(
        module,
        "builtin_acceptance_script",
        lambda: (None, "missing: /tmp/<odd>/fullacceptance.txt"),
    )
    shown: list[tuple[str, Qt.TextFormat]] = []
    monkeypatch.setattr(
        QMessageBox, "exec", lambda self: shown.append((self.text(), self.textFormat()))
    )
    calls: list[object] = []
    console = _console(lambda f, v: calls.append((f, v)) or SettingWrite(True))
    console._script_settings.use_builtin_acceptance_script()
    assert shown == [
        ("missing: /tmp/<odd>/fullacceptance.txt", Qt.TextFormat.PlainText)
    ]
    assert calls == [] and console._startup_script_edit.text() == ""


def test_the_window_hands_the_console_its_writer(make_window: Any) -> None:
    window = make_window(config=Config(test_script_autorun=False))
    console = window.open_script_console()
    try:
        console._autorun_check.setChecked(True)
        assert window._config.test_script_autorun is True
    finally:
        console.close()
