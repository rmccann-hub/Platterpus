"""Drive calibration, read-offset, and access diagnostics for the main window.

Extracted from ``main_window`` (2026-06-13 modularization, KDD-19) as a
mixin so the "is the drive ready to rip bit-perfectly?" concern lives in one
focused file while its methods stay reachable as ``window._x`` (tests + Qt
signal wiring rely on that). ``MainWindow`` inherits this; methods run with
``self`` being the window.

The read offset is what makes a rip bit-perfect, so this group is load-bearing:
it resolves the offset from the bundled AccurateRip list by drive model
(`_auto_apply_known_offset`, the disc-free primary path), runs the wizard for
the unknown-drive case (`_on_drive_setup` → `DriveSetupDialog`), records a
hand-entered value as the GUI's `--offset` override (`_set_read_offset_override`
— the single place that marks "offset configured", so `whipper.conf` is never
hand-authored, KDD-15), and diagnoses the no-drive case (permission vs. no
device).

Contract this mixin expects from the host window (set in
``MainWindow.__init__``): ``self._config``, ``self._save_config``,
``self._backend``, ``self._offset_db``, ``self._drive_picker``,
``self._rip_controls``, ``self._drive_access_nudged``; ``self`` is a
``QWidget`` (dialog parent).
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from whipper_gui.drive_access import (
    SEVERITY_NO_DEVICE,
    SEVERITY_OK,
    DriveAccessDiagnosis,
    diagnose_drive_access,
)
from whipper_gui.offset_config import is_offset_configured
from whipper_gui.ui.drive_setup_dialog import DriveSetupDialog

log = logging.getLogger(__name__)


class DriveMixin:
    """Drive setup wizard, read-offset auto-apply/override, access diagnostics."""

    def _on_drive_setup(self) -> None:
        """Tools → Set up drive: launch the calibration wizard.

        Targets the currently-selected drive (whipper auto-detects a single
        drive anyway, but passing the device is correct for multi-drive).
        """
        device = self._drive_picker.current_device()
        if not device:
            QMessageBox.warning(self, "Set up drive", "Select a drive first.")
            return
        # Primary path: resolve the offset by drive model from the AccurateRip
        # list, so the wizard can pre-fill the right value with no disc and no
        # dependence on whipper's unreliable `offset find`.
        drive = self._drive_picker.current_drive()
        known_offset: int | None = None
        drive_label = ""
        if drive is not None:
            known_offset = self._offset_db.lookup(drive.vendor, drive.model)
            drive_label = f"{drive.vendor.strip()} {drive.model.strip()}".strip()
            if known_offset is not None:
                log.info(
                    "known AccurateRip offset for %s: %+d",
                    drive_label,
                    known_offset,
                )
        dialog = DriveSetupDialog(
            self._backend,
            device,
            self,
            current_offset=self._config.read_offset,
            known_offset=known_offset,
            drive_label=drive_label,
        )
        dialog.manual_offset_saved.connect(self._on_manual_offset_saved)
        dialog.exec()

    def _should_offer_drive_setup(self) -> bool:
        """True when we should auto-offer calibration on first run.

        Only when (a) we haven't offered before and (b) no read offset is
        configured (neither whipper.conf nor our --offset override). whipper
        can't rip without one, so a fresh user is otherwise stuck.
        """
        if self._config.drive_setup_prompted:
            return False
        return not is_offset_configured(self._config.override_read_offset)

    def _maybe_offer_drive_setup(self) -> None:
        """Show the one-time, dismissible first-run calibration offer."""
        if not self._should_offer_drive_setup():
            return
        # Record the offer first so a decline (or any path out) never re-nags;
        # afterwards calibration lives on Tools → Set up drive….
        self._config.drive_setup_prompted = True
        self._save_config(self._config)
        choice = QMessageBox.question(
            self,
            "Set up your drive",
            "Your drive's read offset isn't configured yet — whipper needs it "
            "to rip. Set it up now?\n\n"
            "You can auto-detect it (insert a popular commercial CD) or enter "
            "it by hand. You can also do this later from Tools → Set up drive….",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if choice == QMessageBox.StandardButton.Yes:
            self._on_drive_setup()

    def _on_manual_offset_saved(self, value: int) -> None:
        """Store a hand-entered read offset as the GUI's --offset override."""
        self._set_read_offset_override(value)
        log.info("manual read offset saved: %+d", value)

    def _set_read_offset_override(self, value: int) -> None:
        """Persist `value` as the GUI's `--offset` override and push it into the
        rip controls. This is the single place that records "the offset is now
        configured" (so whipper.conf is never hand-authored, KDD-15)."""
        self._config.read_offset = value
        self._config.override_read_offset = True
        self._rip_controls.set_config(self._config)
        self._save_config(self._config)

    def _auto_apply_known_offset(self) -> bool:
        """If the selected drive's offset is known (AccurateRip list), apply it
        and return True so the rip can proceed — no wizard, asked at most once.

        Returns False when there's no selected drive or its offset is unknown,
        so the caller falls back to the set-up-your-drive prompt.
        """
        drive = self._drive_picker.current_drive()
        if drive is None:
            return False
        known = self._offset_db.lookup(drive.vendor, drive.model)
        if known is None:
            return False
        label = f"{drive.vendor.strip()} {drive.model.strip()}".strip()
        self._set_read_offset_override(known)
        log.info("auto-applied known read offset %+d for %s", known, label)
        # Tell the user once where the value came from (and that it's editable).
        QMessageBox.information(
            self,
            "Read offset set automatically",
            f"Using read offset {known:+d} for {label}, from the AccurateRip "
            "drive list — no setup needed. You can change it any time in "
            "Settings or Tools → Set up drive….",
        )
        return True

    # --- Slots: drive-access diagnostics -----------------------------------

    def _on_drives_unavailable(self) -> None:
        """A refresh found no drives — proactively offer a fix, once.

        Only auto-interrupts when the diagnosis is *actionable* (a
        permission fix). "No device connected" stays quiet (there's no
        command to run); the Tools → Diagnose entry is there for that.
        """
        if self._drive_access_nudged:
            return
        diagnosis = diagnose_drive_access()
        if diagnosis.actionable:
            self._drive_access_nudged = True
            self._present_drive_diagnosis(diagnosis)

    def _show_drive_access_diagnosis(self) -> None:
        """Tools → Diagnose drive access: always show, any severity."""
        self._present_drive_diagnosis(diagnose_drive_access())

    def _present_drive_diagnosis(self, diagnosis: DriveAccessDiagnosis) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Drive access")
        box.setIcon(
            QMessageBox.Icon.Information
            if diagnosis.severity in (SEVERITY_OK, SEVERITY_NO_DEVICE)
            else QMessageBox.Icon.Warning
        )
        box.setText(diagnosis.summary)
        info = diagnosis.detail
        if diagnosis.fix_command:
            info += (
                f"\n\nRun this, then log out and back in:\n    {diagnosis.fix_command}"
            )
        box.setInformativeText(info)
        # Let the user select/copy the fix command out of the dialog.
        box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        box.exec()
