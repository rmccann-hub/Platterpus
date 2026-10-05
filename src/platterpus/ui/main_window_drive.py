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
— the single place that marks "offset configured", KDD-15, so the offset has
one home: the GUI's own config), and diagnoses the no-drive case (permission
vs. no device).

It also gets the disc in the drive READ without the user: the media poll
(`_poll_disc_media`, an insertion or removal) and the bounded automatic retry
of a failed disc read (`_handle_disc_probe_failure`, policy in
`disc_probe_retry`).

Contract this mixin expects from the host window (set in
``MainWindow.__init__``): ``self._config``, ``self._save_config``,
``self._backend``, ``self._offset_db``, ``self._drive_profiles`` (a
``DriveProfileStore``), ``self._drive_picker``, ``self._disc_info_panel``,
``self._rip_controls``, ``self._drive_access_nudged``, and the disc-read retry
state (``self._disc_retries``, ``self._disc_retry_timer``); ``self`` is a
``QWidget`` (dialog parent).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMessageBox

if TYPE_CHECKING:  # the type only; the module is imported where it is used
    from platterpus.rip_estimate import ReadRate

from platterpus import drive_media
from platterpus.disc_probe_retry import (
    AUTO_RETRY_DELAY_MS,
    READ_NOW,
    RETRY_LATER,
    RetryConditions,
    RetryDecision,
)
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
    confidence_for,
    describe_source,
    evaluate_drive_state,
    find_fingerprint_collisions,
    read_drive_identity,
    reconcile_offset,
)
from platterpus.offset_config import is_offset_configured
from platterpus.settings_validation import OFFSET_MAX, OFFSET_MIN
from platterpus.ui import message_boxes
from platterpus.ui.drive_setup_dialog import DriveSetupDialog
from platterpus.ui.main_window_helpers import friendly_disc_scan_error
from platterpus.ui.main_window_shared import MainWindowShared

log = logging.getLogger(__name__)


class DriveMixin(MainWindowShared):
    """Drive setup wizard, read-offset auto-apply/override, access diagnostics."""

    def _on_drive_setup(self) -> None:
        """Tools → Setup & Updates… → Set up drive: launch the calibration wizard.

        Targets the currently-selected drive (the ripper auto-detects a single
        drive anyway, but passing the device is correct for multi-drive).
        """
        device = self._drive_picker.current_device()
        if not device:
            message_boxes.warning(self, "Set up drive", "Select a drive first.")
            return
        # Primary path: resolve the offset by drive model from the AccurateRip
        # list, so the wizard can pre-fill the right value with no disc and no
        # dependence on the ripper's disc-based offset detection.
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
            offset_applied=self._config.override_read_offset,
        )
        dialog.manual_offset_saved.connect(self._on_manual_offset_saved)
        # The Apply tick-box moved here from Settings (2026-09-24): the offset
        # and the switch that makes it count are edited in one window.
        dialog.offset_applied_changed.connect(self._on_offset_applied_changed)
        # Record a successful auto-detect's provenance (measured on this drive →
        # high confidence). Provenance only — the offset itself is saved to
        # Platterpus config by the manual-save path.
        dialog.detection_recorded.connect(self._on_detection_recorded)
        dialog.exec()

    def _should_offer_drive_setup(self) -> bool:
        """True when we should auto-offer calibration on first run.

        Only when (a) we haven't offered before and (b) no read offset is
        configured (our --offset override is off — see offset_config.py).
        A bit-perfect rip needs one, so a fresh user is otherwise stuck.
        """
        if self._config.drive_setup_prompted:
            return False
        return not is_offset_configured(self._config.override_read_offset)

    def _maybe_offer_drive_setup(self) -> None:
        """Show the one-time, dismissible first-run calibration offer."""
        if not self._should_offer_drive_setup():
            return
        # Record the offer first so a decline (or any path out) never re-nags;
        # afterwards calibration lives on Tools → Setup & Updates… → Set up drive….
        self._config.drive_setup_prompted = True
        self._save_config(self._config)
        choice = message_boxes.question(
            self,
            "Set up your drive",
            "Your drive's read offset isn't configured yet — it's needed for "
            "a bit-perfect rip. Set it up now?\n\n"
            "You can auto-detect it (insert a popular commercial CD) or enter "
            "it by hand. You can also do this later from Tools → Setup & Updates… → Set up drive….",
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

    def _set_read_offset_override(self, value: int) -> bool:
        """Persist `value` as the GUI's `--offset` override and push it into the
        rip controls. This is the single place that records "the offset is now
        configured" (KDD-15), so the offset has one home: the GUI's own config.

        Returns True when the value was accepted. It is validated here against
        the *same* bounds the Settings dialog enforces
        (:data:`settings_validation.OFFSET_MIN` / ``OFFSET_MAX``) because this
        method — not Settings — is the write path for all three offset sources:
        the hand-entered wizard value, the auto-detected one, and the
        AccurateRip lookup overlaid from the user-editable
        ``drive_offsets.csv`` (whose parser accepts any ``-?\\d+``, unbounded).
        None of them went through the validator, so an absurd offset could be
        persisted, reach ``cyanrip -s``, and then be silently reset to 0 by the
        next startup's ``_sanitized()`` — leaving the *following* session
        ripping at the wrong offset with only a log line. Refusing it at the one
        write path fixes all three (audit finding, 2026-07-28).
        """
        if not isinstance(value, int) or isinstance(value, bool):
            log.error("refusing a non-integer read offset: %r", value)
            return False
        if value < OFFSET_MIN or value > OFFSET_MAX:
            log.error(
                "refusing an out-of-range read offset %r (allowed %d..%d)",
                value,
                OFFSET_MIN,
                OFFSET_MAX,
            )
            self._show_offset_rejected(value)
            return False
        self._config.read_offset = value
        self._config.override_read_offset = True
        self._rip_controls.set_config(self._config)
        self._save_config(self._config)
        # Setup & Updates shows the offset beside Set up drive…; keep it true.
        self._refresh_setting_views()
        return True

    def _show_offset_rejected(self, value: int) -> None:
        """Tell the user why an offset was refused — never fail silently."""
        message_boxes.warning(
            self,
            "Read offset out of range",
            f"A read offset of {value:+d} samples is outside the allowed range "
            f"({OFFSET_MIN:+d} to {OFFSET_MAX:+d}), so it was not saved.\n\n"
            "Real drive offsets are small — the AccurateRip database's values "
            "all sit within a few hundred samples of zero. Check the value and "
            "try again, or run Tools → Setup & Updates… → Set up drive… to detect it.",
        )

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
        message_boxes.information(
            self,
            "Read offset set automatically",
            f"Using read offset {known:+d} for {label}, from the AccurateRip "
            "drive list — no setup needed. You can change it any time in "
            "Settings or Tools → Setup & Updates… → Set up drive….",
        )
        return True

    # --- Drive-profile ledger (provenance + trust display, KDD-23) ----------
    #
    # A record/display/guard layer keyed by a stable hardware fingerprint. It
    # NEVER decides which offset a rip uses — the --offset override above
    # stays authoritative. It records where each learned offset
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

    def _read_rate_for_current_drive(self) -> ReadRate | None:
        """The selected drive's measured reading speed, else the rig's for its model.

        ``None`` for a drive with no rip of its own and no measurement of its
        model: drives differ several-fold, and no estimate beats a wrong one
        (`rip_estimate`). Never raises.
        """
        from platterpus import rip_estimate
        from platterpus.adapters.accuraterip_offsets import normalize_drive_name

        try:
            drive = self._drive_picker.current_drive()
            if drive is None:
                return None
            fingerprint, _serial, _wwn = self._fingerprint_for(drive)
            profile = self._drive_profiles.get(fingerprint)
            if profile is not None and profile.read_rate is not None:
                return profile.read_rate
            return rip_estimate.seed_for(
                normalize_drive_name(drive.vendor, drive.model)
            )
        except Exception:  # noqa: BLE001 — an estimate must never stop a rip
            log.exception("could not read the drive's measured reading speed")
            return None

    def _learn_read_rate(self, rip_log: object, *, success: bool) -> None:
        """Fold this rip's first reads into the drive's profile. Never raises.

        Only a first pass that read each track once: a uniform ``-Z`` rip's
        extraction times hold every read of a track, which would make the drive
        look several times slower. A failed rip teaches nothing; a cancelled one
        teaches the tracks it finished, as its log records them.
        """
        from dataclasses import replace

        from platterpus import rip_estimate

        try:
            params = getattr(self, "_active_rip_params", None)
            if params is None or not success and not self._rip_cancelled:
                return
            if params.secure_rerip_matches > 0 and not params.secure_rerip_dynamic:
                return
            sample = rip_estimate.first_pass_sample(
                getattr(rip_log, "tracks", ()) or ()
            )
            drive = self._drive_picker.current_drive()
            if sample is None or drive is None:
                return
            fingerprint, _serial, _wwn = self._fingerprint_for(drive)
            profile = self._drive_profiles.get(fingerprint)
            if profile is None:
                return
            rate = rip_estimate.fold(profile.read_rate, *sample)
            self._drive_profiles.upsert(replace(profile, read_rate=rate))
            self._drive_profiles.save()
            multiple = rate.multiple
            log.info(
                "drive reading speed learned from this rip: %.0f s of audio in "
                "%.0f s; folded over %d rip(s), %.2fx",
                sample[0],
                sample[1],
                rate.rips,
                1 / multiple if multiple else 0.0,
            )
        except Exception:  # noqa: BLE001 — learning must never break the finish
            log.exception("could not record the drive's reading speed")

    def _record_drive_fact(
        self,
        drive: object,
        *,
        offset_value: int | None = None,
        source: OffsetSource | None = None,
        cache_defeat: bool | None = None,
    ) -> None:
        """The single writer of the drive-profile ledger.

        Updates (or creates) the profile for `drive`'s fingerprint, merging any
        new offset fact via the agreement-based model (`reconcile_offset`): two
        independent sources agreeing promote to CONFIRMED/HIGH, while a
        disagreeing automatic source never clobbers a manual or already-confirmed
        value. Stamps last-seen and saves atomically. Never changes which offset
        a rip uses.
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
            new_offset = reconcile_offset(new_offset, candidate)

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

    def _poll_disc_media(self) -> None:
        """Auto-detect a newly-inserted disc and rescan (media-poll timer slot).

        Fixes the "cancel the rip, put a new CD in, nothing happens" gap: cancel
        force-stops AND ejects the drive, and there was no media-change detection,
        so the new disc stayed invisible until a manual Rescan. Cheap and safe:
        skips entirely while a rip or a scan is in flight (the drive is busy and
        the status ioctl would just read 'not ready'/'unavailable'), reads the
        drive's media state best-effort (never raises, never spins the disc), and
        only when the pure MediaWatcher sees a real empty→disc transition does it
        kick the SAME rescan path as the Rescan button. Best-effort throughout —
        a diagnostic poll must never disrupt the UI.
        """
        try:
            # Idle only: a rip holds the drive (_rip_thread), and a scan is
            # already doing exactly what a rescan would (_disc_info_thread).
            if getattr(self, "_rip_thread", None) is not None:
                return
            scan = getattr(self, "_disc_info_thread", None)
            if scan is not None and scan.isRunning():
                return
            device = self._drive_picker.current_device()
            if not device:
                return
            status = self._disc_status_probe(device)
            previous = self._media_watcher.last_status
            event = self._media_watcher.observe_event(status)
            # The raw stream, on change only: when an insertion went missing on
            # the rig (2026-09-28) nothing said what the drive had reported. DEBUG
            # so a flickering drive cannot flood the log; the event lines carry
            # the part that matters at INFO.
            if status != previous:
                log.debug("media status of %s: %s -> %s", device, previous, status)
            bridged = self._media_watcher.bridge_note()
            if event == drive_media.INSERTED:
                log.info(
                    "disc inserted in %s (drive reports %s%s) — auto-rescanning",
                    device,
                    status,
                    bridged,
                )
                # Whatever the view holds belongs to an earlier disc. A removal
                # normally cleared it, but not always: the poll is skipped while
                # a scan runs, so a disc ejected DURING a scan that then fails
                # leaves "open" as the first reading afterwards — a baseline, not
                # a removal — and the next disc fires INSERTED with the old one
                # still on screen. (A scan that READ the disc tells the watcher,
                # so an eject after it is a removal: `note_disc_present`.)
                # (The other route, disc → unknown → empty → disc, now fires
                # REMOVED first: unknown readings are bridged since 2026-09-28.)
                self._reset_disc_view()
                # Say the disc is being read: the reset left only dashes, which is
                # what an app that saw nothing looks like (Rescan does the same).
                self._disc_info_panel.set_disc_info_loading()
                self._start_disc_info(device)
            elif event == drive_media.REMOVED:
                # The disc left the drive (an eject or a physical removal). Clear
                # the now-stale disc-identity view so the app doesn't look like it
                # still has the old disc loaded (the results pane keeps the last
                # rip's outcome — this only clears "what's in the drive now").
                # The drive's own word is logged: whether the rig's removals were
                # real ejects or a drive saying "tray open" with the disc still in
                # is not settled, and this line is what would settle it.
                log.info(
                    "disc removed from %s (drive reports %s%s) — clearing the "
                    "disc view",
                    device,
                    status,
                    bridged,
                )
                # The removal ends the read a pending retry was for. Left armed,
                # its timer replaced the no-disc line with an error about the
                # disc that had left (code review, 2026-09-28). The next disc is
                # read by the insertion, with a fresh budget.
                if self._disc_retries.pending is not None:
                    log.info(
                        "pending automatic re-read of %s dropped: the disc left",
                        device,
                    )
                self._begin_disc_request()
                self._reset_disc_view()
                self._disc_info_panel.set_no_disc()
        except Exception:  # noqa: BLE001 — a background poll must never crash the UI
            log.exception("disc-media poll failed; skipping this tick")

    def _reset_disc_view(self) -> None:
        """Clear the disc-identity view when the disc leaves the drive.

        Called by the media poll on a disc→empty transition. Mirrors the *clear*
        half of ``_on_drive_changed`` but starts no scan (there's no disc to
        read) and does NOT touch the results/verdict pane — the disc-info panel
        answers "what disc is in the drive now", so with no disc it goes empty,
        while the last rip's outcome stays where the user can still see it.
        """
        # The drive rows stay: the same drive is still selected, and nothing
        # refills them on the next disc's insert.
        self._disc_info_panel.clear_disc_state(keep_drive_rows=True)
        self._track_table.clear()
        self._current_release_id = ""
        self._current_release_detail = None
        self._current_num_tracks = 0
        self._current_disc_id = ""
        # Cleared wherever `_current_disc_id` is, never only at the site the bug
        # was found. It is not load-bearing here — a stale value cannot match a
        # new disc's context — but two resets that drift are how the *next* one
        # of these gets written, and `tests/test_ui_main_window.py` now sweeps
        # for the pairing rather than trusting it.
        self._mb_release_chosen_for = ""
        self._manual_cover_path = None
        self._rip_controls.set_release_id("")
        self._rip_controls.set_unknown_mode(False)

    # --- A failed disc read is retried on its own (disc_probe_retry) --------
    #
    # The state and every branch are in `DiscReadRetries`; these methods only
    # read the facts it asks for and do what it decides.

    def _begin_disc_request(self) -> None:
        """A NEW read was asked for (drive change, Rescan, an insertion): a fresh
        retry budget, and any retry pending for an older one is dropped."""
        self._disc_retries.new_request()
        self._disc_retry_timer.stop()

    def _disc_retry_conditions(self, device: str, request: int) -> RetryConditions:
        """Read, now, every fact an automatic retry depends on."""
        scan = self._disc_info_thread
        freeing = self._force_stop_thread
        return RetryConditions(
            rip_running=self._rip_thread is not None,
            scan_running=scan is not None and scan.isRunning(),
            newest_request=request == self._disc_retries.request,
            same_drive=self._drive_picker.current_device() == device,
            drive_being_freed=freeing is not None and freeing.is_alive(),
            media_status=self._disc_status_probe(device),
        )

    def _handle_disc_probe_failure(self, device: str, message: str) -> None:
        """Show a failed read, and retry it automatically when that can help.

        Called by `_on_disc_info_failed` for every failure the user did not cause
        by force-stopping: the panel either says a retry is coming or says what
        to do — never an error on its own.
        """
        conditions = self._disc_retry_conditions(device, self._disc_retries.request)
        self._apply_disc_retry(
            self._disc_retries.after_failure(
                device, message, friendly_disc_scan_error(message), conditions
            )
        )

    def _on_disc_retry_due(self) -> None:
        """The retry timer fired. Everything is checked again HERE: four seconds
        is long enough for a Rescan, a drive change, a rip, an eject or the
        drive-freeing kill."""
        pending = self._disc_retries.pending
        if pending is None:
            return
        conditions = self._disc_retry_conditions(pending.device, pending.request)
        self._apply_disc_retry(
            self._disc_retries.when_due(conditions, friendly_disc_scan_error)
        )

    def _apply_disc_retry(self, decision: RetryDecision) -> None:
        """Do what `DiscReadRetries` decided, and log it."""
        log.info("%s", decision.log_line)
        if decision.retrying_text:
            self._disc_info_panel.set_disc_info_retrying(decision.retrying_text)
        if decision.error_text:
            self._disc_info_panel.set_disc_info_error(decision.error_text)
        if decision.action == RETRY_LATER:
            self._disc_retry_timer.start(AUTO_RETRY_DELAY_MS)
        elif decision.action == READ_NOW:
            self._disc_info_panel.set_disc_info_loading()
            self._start_disc_info(decision.device, automatic_retry=True)

    def _refresh_drive_profile_display(self) -> None:
        """Recompute and push the read-offset trust line for the selected drive.

        Stamps last-seen (and persists the drive's identity), runs the mismatch
        guard across all enumerated drives, and hands the disc-info panel a
        ready-to-show provenance/warning string. It records no offset of its own:
        an offset enters the ledger only from something that set it on purpose
        (the wizard, a hand entry, the AccurateRip list, a matching rip).
        """
        drive = self._drive_picker.current_drive()
        if drive is None:
            return
        fingerprint, _serial, _wwn = self._fingerprint_for(drive)
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
            collisions=find_fingerprint_collisions(all_fingerprints),
            # The AccurateRip drive-list value for this model, so the guard can
            # flag a stored/applied offset that silently disagrees with it.
            accuraterip_value=self._offset_db.lookup(drive.vendor, drive.model),
        )
        self._disc_info_panel.set_drive_offset_provenance(
            _format_offset_provenance(existing, warnings)
        )
        # The measured cache-defeat verdict (cd-paranoia -A, recorded per drive —
        # KDD-29). Drive-derived like the offset, so it's refreshed here too.
        self._disc_info_panel.set_drive_cache_defeat(_format_cache_defeat(existing))

    # --- Slots: drive-access diagnostics -----------------------------------

    def _on_drives_unavailable(self) -> None:
        """A refresh found no drives — proactively offer a fix, once.

        Only auto-interrupts when the diagnosis is *actionable* (a permission
        fix). "No device connected" stays quiet (there's no command to run);
        Tools → Setup & Updates… → Diagnose drive access… is there for that.
        """
        if self._drive_access_nudged:
            return
        diagnosis = diagnose_drive_access()
        if diagnosis.actionable:
            self._drive_access_nudged = True
            self._present_drive_diagnosis(diagnosis)

    def _show_drive_access_diagnosis(self) -> None:
        """Tools → Setup & Updates… → Diagnose drive access…: always show it."""
        self._present_drive_diagnosis(diagnose_drive_access())

    def _present_drive_diagnosis(self, diagnosis: DriveAccessDiagnosis) -> None:
        box = QMessageBox(self)
        # PlainText: `summary`, `detail` and `fix_command` below are assembled from
        # what the system told us — device paths, group names, a command line. Qt's
        # default `AutoText` would interpret any `<` in them as markup and drop the
        # text after it, and this dialog's whole point is that the user can read and
        # copy the fix command exactly (Critical rule #12).
        box.setTextFormat(Qt.TextFormat.PlainText)
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
        # Let the user select/copy the fix command out of the dialog — by
        # keyboard too, since copying the fix command is this dialog's whole
        # point and a keyboard-only user must not be locked out of it (gap #4).
        box.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        # Same Qt quirk as the disc-info panel: keyboard-selectable text gets
        # only ClickFocus, so Tab would skip it. StrongFocus on the message
        # box's labels puts the text in the dialog's tab chain.
        for label in box.findChildren(QLabel):
            if (
                label.textInteractionFlags()
                & Qt.TextInteractionFlag.TextSelectableByKeyboard
            ):
                label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        box.exec()


def _format_offset_provenance(
    profile: DriveProfile | None, warnings: Sequence[object]
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


def _format_cache_defeat(profile: DriveProfile | None) -> str:
    """Build the disc-info panel's cache-defeat trust line from the profile.

    Effect-first and honest about the measurement state: a measured Yes/No names
    that it was measured (cd-paranoia); an unmeasured drive says so plainly rather
    than implying a verdict. Pure; safe to call with no profile.
    """
    if profile is None or profile.cache_defeat is None:
        return "not measured yet — Set up drive → Analyse cache"
    if profile.cache_defeat:
        return "Yes — cache defeated on re-read (measured, cd-paranoia)"
    return "No — drive returns cached audio on re-read (measured, cd-paranoia)"
