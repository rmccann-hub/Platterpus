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
``self._backend``, ``self._offset_db``, ``self._drive_profiles`` (a
``DriveProfileStore``), ``self._drive_picker``, ``self._disc_info_panel``,
``self._rip_controls``, ``self._drive_access_nudged``; ``self`` is a
``QWidget`` (dialog parent).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from platterpus.drive_access import (
    SEVERITY_NO_DEVICE,
    SEVERITY_OK,
    DriveAccessDiagnosis,
    diagnose_drive_access,
)
from platterpus.drive_profiles import (
    SEVERITY_WARN,
    DriveProfile,
    OffsetRecord,
    OffsetSource,
    compute_fingerprint,
    conf_offset_for,
    confidence_for,
    describe_source,
    evaluate_drive_state,
    find_fingerprint_collisions,
    read_drive_identity,
    should_replace_offset,
)
from platterpus.offset_config import is_offset_configured, read_drive_offsets
from platterpus.ui.drive_setup_dialog import DriveSetupDialog

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
        # Record a successful auto-detect's provenance (measured on this drive →
        # high confidence). Provenance only — whipper already wrote whipper.conf.
        dialog.detection_recorded.connect(self._on_detection_recorded)
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
        # Record the provenance: a deliberate user entry (MANUAL always wins in
        # the ledger). This does not change the override behaviour above.
        drive = self._drive_picker.current_drive()
        if drive is not None:
            self._record_drive_fact(
                drive, offset_value=value, source=OffsetSource.MANUAL
            )
        # Refresh the trust line for the selected drive so it reflects the save.
        self._refresh_drive_profile_display()

    def _on_detection_recorded(self, result: object) -> None:
        """Persist a wizard auto-detect result and record its provenance.

        `result` is a DriveSetupResult; we read its offset/cache via getattr so
        this never depends on the dialog's concrete type. cyanrip's offset
        finder only *returns* the value (it writes no config file of its own),
        so the GUI persists it here as the `--offset` override — otherwise a
        detected offset wouldn't reach the next rip. Provenance is recorded as
        a measured value (HIGH confidence).
        """
        drive = self._drive_picker.current_drive()
        if drive is None:
            return
        offset = getattr(result, "offset", None)
        cache = getattr(result, "can_defeat_cache", None)
        if isinstance(offset, int):
            # Save it as the offset every rip will use (cyanrip's -s).
            self._set_read_offset_override(offset)
        self._record_drive_fact(
            drive,
            offset_value=offset if isinstance(offset, int) else None,
            source=OffsetSource.OFFSET_FIND,
            cache_defeat=cache if isinstance(cache, bool) else None,
        )
        self._refresh_drive_profile_display()

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
        self._record_drive_fact(
            drive, offset_value=known, source=OffsetSource.ACCURATERIP_LIST
        )
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

    # --- Drive-profile ledger (provenance + trust display, KDD-23) ----------
    #
    # A record/display/guard layer keyed by a stable hardware fingerprint. It
    # NEVER decides which offset a rip uses — whipper.conf and the --offset
    # override above stay authoritative. It records where each learned offset
    # came from + how sure we are, and surfaces collision/drift warnings so a
    # silent wrong-offset rip becomes visible. The single writer is
    # `_record_drive_fact`; no other code touches the store.

    def _now_iso(self) -> str:
        """Current UTC time as an ISO-8601 string (overridable in tests)."""
        return datetime.now(UTC).isoformat()

    def _fingerprint_for(self, drive: object) -> tuple[str, str, str]:
        """Return ``(fingerprint, serial, wwn)`` for a DriveDescriptor.

        Reads serial/WWN from sysfs (sub-ms local read; "" when absent, the
        common optical-drive case). The fingerprint falls back to vendor/model.
        """
        device = getattr(drive, "device", "")
        serial, wwn = read_drive_identity(device) if device else ("", "")
        fingerprint = compute_fingerprint(
            getattr(drive, "vendor", ""),
            getattr(drive, "model", ""),
            serial=serial,
            wwn=wwn,
        )
        return fingerprint, serial, wwn

    def _record_drive_fact(
        self,
        drive: object,
        *,
        offset_value: int | None = None,
        source: OffsetSource | None = None,
        cache_defeat: bool | None = None,
    ) -> None:
        """The single writer of the drive-profile ledger.

        Updates (or creates) the profile for `drive`'s fingerprint, applying the
        upgrade rule so an automatic source never clobbers a higher-confidence
        record (`should_replace_offset`). Stamps last-seen and saves atomically.
        Never changes which offset a rip uses.
        """
        fingerprint, serial, wwn = self._fingerprint_for(drive)
        existing = self._drive_profiles.get(fingerprint)
        now = self._now_iso()

        new_offset = existing.offset if existing else None
        if offset_value is not None and source is not None:
            candidate = OffsetRecord(
                value=offset_value,
                source=source,
                confidence=confidence_for(source),
                detected_at=now,
            )
            if should_replace_offset(new_offset, candidate):
                new_offset = candidate

        new_cache = existing.cache_defeat if existing else None
        new_cache_source = existing.cache_defeat_source if existing else None
        if cache_defeat is not None:
            new_cache = cache_defeat
            new_cache_source = source

        self._drive_profiles.upsert(
            DriveProfile(
                fingerprint=fingerprint,
                vendor=getattr(drive, "vendor", ""),
                model=getattr(drive, "model", ""),
                release=getattr(drive, "release", ""),
                serial=serial,
                wwn=wwn,
                offset=new_offset,
                cache_defeat=new_cache,
                cache_defeat_source=new_cache_source,
                last_seen_device=getattr(drive, "device", ""),
                last_seen_at=now,
            )
        )
        self._drive_profiles.save()

    def _refresh_drive_profile_display(self) -> None:
        """Recompute and push the read-offset trust line for the selected drive.

        Seeds the ledger from whipper.conf the first time we see an offset there
        (so the display isn't empty for a drive whipper already knows), stamps
        last-seen, runs the mismatch guard across all enumerated drives, and
        hands the disc-info panel a ready-to-show provenance/warning string.
        """
        drive = self._drive_picker.current_drive()
        if drive is None:
            return
        fingerprint, _serial, _wwn = self._fingerprint_for(drive)
        conf_offsets = read_drive_offsets()
        existing = self._drive_profiles.get(fingerprint)

        # Seed from whipper.conf only when we have nothing recorded yet — never
        # overwrite a known provenance with the bare conf value (the guard
        # surfaces any disagreement instead).
        if existing is None or existing.offset is None:
            conf_value = conf_offset_for(drive.vendor, drive.model, conf_offsets)
            if conf_value is not None:
                self._record_drive_fact(
                    drive, offset_value=conf_value, source=OffsetSource.WHIPPER_CONF
                )
            else:
                # Still stamp last-seen / persist identity even with no offset.
                self._record_drive_fact(drive)
            existing = self._drive_profiles.get(fingerprint)
        else:
            self._record_drive_fact(drive)
            existing = self._drive_profiles.get(fingerprint)

        all_fingerprints = [
            self._fingerprint_for(d)[0] for d in self._drive_picker.all_drives()
        ]
        warnings = evaluate_drive_state(
            fingerprint=fingerprint,
            vendor=drive.vendor,
            model=drive.model,
            release=getattr(drive, "release", ""),
            stored=existing,
            conf_offsets=conf_offsets,
            collisions=find_fingerprint_collisions(all_fingerprints),
        )
        self._disc_info_panel.set_drive_offset_provenance(
            _format_offset_provenance(existing, warnings)
        )

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


def _format_offset_provenance(
    profile: DriveProfile | None, warnings: list[object]
) -> str:
    """Build the disc-info panel's read-offset trust line.

    Leads with the offset + where it came from + confidence (effect-first), then
    appends any guard warnings as text with a leading symbol — never colour
    alone (accessibility principle #10): ``⚠`` for a warning, ``ⓘ`` for an info
    nudge. Pure; safe to call with no profile.
    """
    if profile is not None and profile.offset is not None:
        record = profile.offset
        head = (
            f"{record.value:+d} — {describe_source(record.source)} "
            f"({record.confidence.value} confidence)"
        )
    else:
        head = "not recorded yet — Set up drive to calibrate"

    lines = [head]
    for warning in warnings:
        severity = getattr(warning, "severity", "")
        message = getattr(warning, "message", "")
        symbol = "⚠" if severity == SEVERITY_WARN else "ⓘ"
        lines.append(f"{symbol} {message}")
    return "\n".join(lines)
