"""Settings, each in its one home: the window's side of saving them.

**Why a mixin of its own.** Since 2026-09-24 every user setting has exactly one
control (:mod:`platterpus.ui.setting_homes`). Most live in Settings, which is
modal and saves on OK or Apply. The rest live beside what they steer — the read
offset's Apply tick-box in the drive wizard, the update channels in Setup &
Updates, the startup test script in the script console — and those save as they
are changed, because their windows have no OK button to wait for.

So there are two ways a setting is written, and this file holds both, so neither
grows a private copy of "validate, apply, push to the rip controls, save":

* :meth:`_on_open_settings` / :meth:`_apply_settings_from` — the Settings
  dialog's OK and Apply, which write only what the user changed there;
* :meth:`_save_user_setting` — one field from one control, validated by the same
  predicate the ``set`` script verb uses (`settings_validation.field_error`).

Nothing here blocks: validation is pure and ``_save_config`` writes a small TOML
file.
"""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QDialog, QMessageBox

from platterpus import settings_validation
from platterpus.ui.main_window_shared import MainWindowShared
from platterpus.ui.settings_dialog import SettingsDialog
from platterpus.user_settings import SettingWrite, user_setting_names, with_values

log = logging.getLogger(__name__)


class SettingsMixin(MainWindowShared):
    """Writing settings from their one home, and the Settings dialog's save."""

    # --- Tools → Settings… -------------------------------------------------

    def _on_open_settings(self) -> None:
        dialog = SettingsDialog(self._config, self)
        # Apply saves through the same method as OK, then re-baselines the
        # dialog, so Cancel after Apply keeps what was applied.
        dialog.apply_requested.connect(lambda: self._apply_settings_from(dialog))
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        if accepted:
            self._apply_settings_from(dialog)
        # Freed once read — see the release picker's `deleteLater` for why.
        dialog.deleteLater()

    def _apply_settings_from(self, dialog: SettingsDialog) -> None:
        """Save what the user changed in Settings. OK and Apply both land here.

        Only what the user changed — never the whole form read back. The config
        may have been written while the dialog was open, and the form still shows
        the values it opened with (`apply_user_edits`).
        """
        self._config = dialog.user_edits_applied_to(self._config)
        # Push the new config into the rip controls so the next rip reflects the
        # edits (output dir, templates, cover art, …).
        self._rip_controls.set_config(self._config)
        # Apply the debug-logging toggle immediately so the change takes effect
        # for this session, not just the next launch.
        from platterpus.logging_setup import set_debug_logging

        set_debug_logging(self._config.debug_logging)
        try:
            self._save_config(self._config)
        except OSError as exc:
            QMessageBox.warning(self, "Couldn't save settings", f"{exc}")
        dialog.mark_applied()
        self._refresh_setting_views()

    # --- One setting, from its one control ---------------------------------

    def _save_user_setting(self, field: str, value: object) -> SettingWrite:
        """Validate, apply and save one setting changed by the control that owns it.

        Refuses a field that is not a user setting at all (a wiring mistake,
        logged loudly) and any value the validator calls an error, in which case
        nothing changes and the validator's own sentence comes back to show.
        """
        if field not in user_setting_names():
            log.error("refusing to save %r: it is not a user setting", field)
            return SettingWrite(False, f"{field} is not a setting")
        candidate = with_values(self._config, {field: value})
        problem = settings_validation.field_error(candidate, field)
        if problem:
            log.warning("setting %s refused: %s", field, problem)
            return SettingWrite(False, problem)
        self._config = candidate
        self._rip_controls.set_config(self._config)
        log.info("setting %s = %r (saved from its own control)", field, value)
        try:
            self._save_config(self._config)
        except OSError as exc:
            log.warning("setting %s applied but not saved: %s", field, exc)
            return SettingWrite(
                True, f"In effect for this session, but not saved to disk: {exc}"
            )
        self._refresh_setting_views()
        return SettingWrite(True)

    def _refresh_setting_views(self) -> None:
        """Re-render the open windows that SHOW a setting another window edits.

        Setup & Updates shows the read offset beside Set up drive…, and its
        channel boxes must follow a change made by a script's ``set``. Cheap:
        text from values already in memory, no probe.
        """
        center = self._setup_center
        if center is not None:
            center.refresh_settings(self._config)

    def _on_offset_applied_changed(self, applied: bool) -> None:
        """The drive wizard's "Apply this read offset to every rip" tick-box."""
        self._save_user_setting("override_read_offset", applied)
        self._refresh_drive_profile_display()
