"""Drive calibration, read-offset, and access diagnostics for the main window.

Extracted from ``main_window`` (2026-06-13 modularization, KDD-19) as a
mixin so the "is the drive ready to rip bit-perfectly?" concern lives in one
focused file while its methods stay reachable as ``window._x`` (tests + Qt
signal wiring rely on that). ``MainWindow`` inherits this; methods run with
``self`` being the window.

The read offset is what makes a rip bit-perfect, so this group is load-bearing:
it resolves the offset from the bundled AccurateRip list by drive model
(`_auto_apply_known_offset`, the disc-free primary path), runs the wizard for
the unknown-drive case (`_on_drive_setup` → `DriveSetupDialog`), saves every
offset into the SELECTED drive's profile (`_set_read_offset_override` — the
single write path, KDD-15), answers "which offset does the next rip use?" for
the selected drive (`_selected_drive_offset`, which delegates to
`offset_config.offset_for_drive`; since 2026-11-12 each drive keeps its own),
and diagnoses the no-drive case (permission vs. no device).

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

from platterpus import cache_check_plan, drive_media, exit_work
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
from platterpus.offset_config import (
    MOVE_WAIT,
    DriveOffset,
    is_offset_configured,
    move_global_offset,
    offset_for_drive,
)
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
        # The automatic cache check (TASKS R53): whether this drive still needs
        # its verdict, whether an audio CD has been read, and whether anything
        # else is reading the drive right now. The dialog decides with
        # `cache_check_plan.decide_auto_check`; a descriptor-less selection says
        # nothing (None), so nothing starts by itself.
        cache_verdict: str | None = None
        if drive is not None:
            cache_verdict = cache_check_plan.verdict_state(
                self._drive_profiles.get(self._fingerprint_for(drive)[0]),
                getattr(drive, "release", ""),
            )
        # This drive's own saved offset prefills the form (else 0); another
        # drive's value must never appear here as if it were this one's.
        saved = self._selected_drive_offset().record
        dialog = DriveSetupDialog(
            self._backend,
            device,
            self,
            current_offset=saved.value if saved is not None else 0,
            known_offset=known_offset,
            drive_label=drive_label,
            offset_applied=self._config.override_read_offset,
            cache_verdict=cache_verdict,
            audio_disc_present=self._current_num_tracks > 0,
            drive_busy=self._drive_is_busy_for_setup(),
        )
        dialog.manual_offset_saved.connect(self._on_manual_offset_saved)
        # The Apply tick-box moved here from Settings (2026-09-24): the offset
        # and the switch that makes it count are edited in one window.
        dialog.offset_applied_changed.connect(self._on_offset_applied_changed)
        # Record a successful auto-detect's provenance (measured on this drive →
        # high confidence). Provenance only — the offset itself is saved to
        # Platterpus config by the manual-save path.
        dialog.detection_recorded.connect(self._on_detection_recorded)
        self._drive_setup_dialog = dialog
        try:
            dialog.exec()
        finally:
            self._drive_setup_dialog = None

    def _should_offer_drive_setup(self) -> bool:
        """True when we should auto-offer calibration on first run.

        Only when (a) we haven't offered before and (b) the selected drive has no
        read offset that will reach the ripper (`offset_config.offset_for_drive`).
        A bit-perfect rip needs one, so a fresh user is otherwise stuck. (Every
        user who ran an earlier version was offered this once already —
        ``drive_setup_prompted`` — so moving offsets per drive offers nothing new
        to them.)
        """
        if self._config.drive_setup_prompted:
            return False
        return not is_offset_configured(self._selected_drive_offset())

    def _maybe_offer_drive_setup(self) -> None:
        """Show the one-time, dismissible first-run calibration offer."""
        if not self._should_offer_drive_setup():
            return
        # Record the offer first so a decline (or any path out) never re-nags;
        # afterwards calibration lives on Tools → Setup & Updates… → Set up drive….
        self._config.drive_setup_prompted = True
        self._save_config_or_report("the drive-setup offer was made")
        choice = message_boxes.question(
            self,
            "Set up your drive",
            "Your drive's read offset isn't configured yet — it's needed for "
            "a bit-perfect rip. Set it up now?\n\n"
            # cyanrip has no offset finder wired in (TASKS R150), so this says
            # what setup does: the AccurateRip list value, or one typed by hand.
            "If AccurateRip's drive list has your drive, its offset is filled "
            "in for you; otherwise you enter it by hand. With an audio CD in "
            "the drive, setup also checks the drive's audio cache by itself. "
            "You can also do this later from Tools → Setup & Updates… → Set up drive….",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if choice == QMessageBox.StandardButton.Yes:
            self._on_drive_setup()

    def _on_manual_offset_saved(self, value: int) -> None:
        """Save a hand-entered read offset for the selected drive.

        Recorded as MANUAL — a deliberate user entry, which always wins in the
        ledger (`reconcile_offset`), so the value typed is the value applied.
        """
        if self._set_read_offset_override(value, OffsetSource.MANUAL):
            log.info("manual read offset saved: %+d", value)

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
            # Save it for this drive (cyanrip's -s for its rips).
            self._set_read_offset_override(offset, OffsetSource.OFFSET_FIND)
        if isinstance(cache, bool):
            # The note "the check has not run" is no longer true.
            self._show_cache_check_note(None)
            self._record_drive_fact(
                drive, source=OffsetSource.OFFSET_FIND, cache_defeat=cache
            )
        self._refresh_drive_profile_display()

    def _set_read_offset_override(
        self, value: int, source: OffsetSource = OffsetSource.MANUAL
    ) -> bool:
        """Save `value` as the SELECTED drive's read offset and switch offsets on.

        The single write path for a read offset (KDD-15): the hand-entered
        wizard value, the auto-detected one, the AccurateRip lookup, an accepted
        correction, and the script verbs all come here. Since 2026-11-12 the
        value goes into the selected drive's profile — the record a rip on that
        drive applies (`offset_config.offset_for_drive`) — through the ledger's
        writer, with `source` as its provenance. ``Config.read_offset`` is
        written too, as the value most recently saved for a drive, so an older
        Platterpus reading this config still finds a sane number; no rip reads it.

        Returns True when the value was accepted. Refused, and said:

        * **out of range** — validated against the *same* bounds the Settings
          dialog enforces (:data:`settings_validation.OFFSET_MIN` / ``OFFSET_MAX``),
          because the AccurateRip lookup is overlaid from the user-editable
          ``drive_offsets.csv`` (whose parser accepts any ``-?\\d+``, unbounded)
          and an absurd value once persisted, reached ``cyanrip -s``, and was
          then silently reset to 0 at the next startup (audit, 2026-07-28);
        * **no drive selected** — an offset belongs to one drive, and saving one
          for no drive would either reach no rip or, as the single global value
          once did, every drive's.
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
        drive = self._drive_picker.current_drive()
        if drive is None:
            log.error("refusing read offset %+d: no drive is selected", value)
            message_boxes.warning(
                self,
                "Select a drive first",
                f"The read offset {value:+d} was not saved: a read offset belongs "
                "to one drive, and no drive is selected. Select the drive, then "
                "save it again.",
            )
            return False
        self._record_drive_fact(drive, offset_value=value, source=source)
        # What the drive now holds. The ledger's agreement rule
        # (`reconcile_offset`) keeps a deliberate or confirmed record over a
        # disagreeing AUTOMATIC source, so this can differ from `value`; MANUAL
        # always wins, so a value the user typed is always the one held.
        held = self._selected_drive_offset().record
        applied = held.value if held is not None else value
        if held is not None and applied != value:
            log.warning(
                "read offset %+d (%s) not saved over the %+d already recorded "
                "for this drive (%s); the drive keeps %+d",
                value,
                source.value,
                applied,
                describe_source(held.source),
                applied,
            )
        # The mirror only ever holds a value Settings would accept: a held record
        # outside the range (a hand-edited profile) is not copied into config.
        if OFFSET_MIN <= applied <= OFFSET_MAX:
            self._config.read_offset = applied
        self._config.override_read_offset = True
        self._rip_controls.set_config(self._config)
        self._save_config_or_report(f"The read offset {applied:+d}", tell_user=True)
        # Setup & Updates shows the offset beside Set up drive…; keep it true,
        # and the drive's trust line with it.
        self._refresh_setting_views()
        self._refresh_drive_profile_display()
        return True

    def _selected_drive_offset(self) -> DriveOffset:
        """Which read offset the next rip on the SELECTED drive applies.

        The window's one caller of `offset_config.offset_for_drive`: the Start
        gate, the argv, the displays and the script verbs all ask here, so none
        of them can answer from a different key (a global value, another drive).
        Hands the old global offset to its drive first, once
        (`_move_global_offset_once`), so the answer for an existing user is the
        one their rips already had.
        """
        drive = self._drive_picker.current_drive()
        if drive is None:
            return offset_for_drive(
                None,
                apply_offsets=self._config.override_read_offset,
                drive_selected=False,
            )
        fingerprint, _serial, _wwn = self._fingerprint_for(drive)
        self._move_global_offset_once(fingerprint)
        profile = self._drive_profiles.get(fingerprint)
        return offset_for_drive(
            profile.offset if profile is not None else None,
            apply_offsets=self._config.override_read_offset,
        )

    def _move_global_offset_once(self, fingerprint: str) -> None:
        """Hand the single global offset of older versions to its drive, once.

        `fingerprint` is the selected drive's. Which drive inherits, and why, is
        decided by `offset_config.plan_global_offset_move` (pure, tested on its
        own): a drive whose profile already records the global value keeps it as
        its own and nobody inherits; otherwise the selected drive — the one that
        has been ripping at it — does. The "done" mark is saved in the same file,
        in the same write, so a crash cannot leave the move half-made.

        The store is changed by `offset_config.move_global_offset`, not through
        `_record_drive_fact`, because that writer calls this first; it is the
        ledger's second writer, the only one that may replace a record without
        `reconcile_offset`. Saved here, on the GUI thread like every ledger
        write: one small JSON file.
        """
        store = self._drive_profiles
        if store.global_offset_moved:
            return
        plan = move_global_offset(
            store,
            fingerprint,
            override_read_offset=self._config.override_read_offset,
            read_offset=self._config.read_offset,
            now_iso=self._now_iso(),
        )
        if plan != MOVE_WAIT:
            store.save()

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
        """Give the selected drive its AccurateRip-list offset, when it is listed.

        Called by Start when the drive has no offset that will reach the ripper.
        Records the list value in THIS drive's profile and switches offsets on,
        then returns True only if the drive now has an offset the rip will
        apply. Returns False when there's no selected drive or its model is not
        listed, so the caller stops and offers the drive-setup wizard — never
        another drive's value.

        If the drive already holds a deliberate value (typed by hand, or
        confirmed by agreement) the ledger keeps it over the list's, and the
        message says which value is used and where it came from.
        """
        drive = self._drive_picker.current_drive()
        if drive is None:
            return False
        known = self._offset_db.lookup(drive.vendor, drive.model)
        if known is None:
            return False
        label = f"{drive.vendor.strip()} {drive.model.strip()}".strip()
        if not self._set_read_offset_override(known, OffsetSource.ACCURATERIP_LIST):
            return False
        decision = self._selected_drive_offset()
        if decision.value is None:
            return False
        log.info(
            "auto-applied read offset %+d for %s (AccurateRip list: %+d)",
            decision.value,
            label,
            known,
        )
        # Tell the user once where the value came from (and that it's editable).
        if decision.value == known or decision.record is None:
            origin = "from the AccurateRip drive list — no setup needed"
        else:
            origin = (
                "the offset saved for this drive "
                f"({describe_source(decision.record.source)}); the AccurateRip "
                f"drive list says {known:+d}"
            )
        message_boxes.information(
            self,
            "Read offset set automatically",
            f"Using read offset {decision.value:+d} for {label}, {origin}. You "
            "can change it any time in Tools → Setup & Updates… → Set up drive….",
        )
        return True

    # --- Drive-profile ledger (per-drive offsets + trust display, KDD-23) ----
    #
    # Keyed by a stable hardware fingerprint. Since 2026-11-12 the selected
    # drive's record IS the offset a rip applies (`_selected_drive_offset`). It
    # also records where each learned offset came from + how sure we are, and
    # surfaces collision/drift warnings so a wrong-offset rip becomes visible.
    # The writer is `_record_drive_fact` (plus the one-time move of the old
    # global offset, `_move_global_offset_once`, which it calls first).

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
        teaches the tracks it finished, as its log records them, less any track
        paranoia skipped on (`rip_estimate.struggled`, TASKS R63).
        """
        from dataclasses import replace

        from platterpus import rip_estimate

        try:
            params = getattr(self, "_active_rip_params", None)
            if params is None or not success and not self._rip_cancelled:
                return
            if params.secure_rerip_matches > 0 and not params.secure_rerip_dynamic:
                return
            tracks = getattr(rip_log, "tracks", ()) or ()
            sample = rip_estimate.first_pass_sample(tracks)
            # Said, so a reader of the log knows the figure is not the whole rip.
            hard = sum(1 for track in tracks if rip_estimate.struggled(track))
            if hard:
                log.info(
                    "drive reading speed: left out %d track(s) with paranoia skips, "
                    "whose time measures the disc, not the drive",
                    hard,
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
        value. Stamps last-seen and saves atomically. Never touches the config:
        the record IS the drive's offset (`_selected_drive_offset`), and the
        config's mirror is written by `_set_read_offset_override` alone.

        The old global offset is handed to its drive first
        (`_move_global_offset_once`): a record written before the move would be
        mistaken by it for where the global value came from.
        """
        fingerprint, serial, wwn = self._fingerprint_for(drive)
        self._move_global_offset_once(fingerprint)
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
        new_cache_release = existing.cache_defeat_release if existing else ""
        if cache_defeat is not None:
            new_cache = cache_defeat
            new_cache_source = source
            # The firmware it was measured under, kept beside the verdict: a
            # firmware update later is the one thing that re-runs the automatic
            # check (`cache_check_plan.verdict_state`), and `release` below is
            # overwritten on every sighting so it cannot tell us.
            new_cache_release = getattr(drive, "release", "") or ""

        # Built FROM the existing profile, so a field this writer does not set
        # survives it. It used to build a fresh DriveProfile, and `read_rate`
        # (added after this writer) was dropped on every drive sighting: the
        # speed a rip had just learned was gone by the next rescan, so every
        # estimate fell back to the rig's seed (found 2026-11-03, TASKS R109).
        from dataclasses import replace

        base = existing or DriveProfile(fingerprint=fingerprint, vendor="", model="")
        self._drive_profiles.upsert(
            replace(
                base,
                vendor=getattr(drive, "vendor", ""),
                model=getattr(drive, "model", ""),
                release=getattr(drive, "release", ""),
                serial=serial,
                wwn=wwn,
                offset=new_offset,
                cache_defeat=new_cache,
                cache_defeat_source=new_cache_source,
                cache_defeat_release=new_cache_release,
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
        kick the SAME rescan path as the Rescan button. An empty tray is a removal
        only once it has lasted (`drive_media.REMOVAL_CONFIRM_S`); shorter, and the
        disc is re-read instead (`drive_media.RETURNED`). Best-effort throughout —
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
            if self._drive_being_freed():
                return  # never a holder while `fuser -k` is out (B9)
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
            elif event == drive_media.RETURNED:
                # Empty for less than the removal bound, then a disc: kept, and
                # re-read to learn whether it is the same disc (disc_return).
                self._on_disc_returned(
                    device, status, self._media_watcher.last_gap_seconds
                )
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
                # Kept, so the same disc put back keeps its release and edits.
                self._park_disc()
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

    def _drive_being_freed(self) -> bool:
        """Whether a force-stop thread is running: the post-cancel rescue, Force
        stop, or a stuck scan's free. Each signals EVERY process holding the
        drive's node (`fuser -k`), so while one runs nothing of ours may open it:
        the media probe's open would make this app a holder, and its SIGTERM
        handler closes the window (`docs/dependency-contracts.md`, why the
        rescue is device-wide)."""
        freeing = self._force_stop_thread
        return freeing is not None and freeing.is_alive()

    def _disc_retry_conditions(self, device: str, request: int) -> RetryConditions:
        """Read, now, every fact an automatic retry depends on."""
        scan = self._disc_info_thread
        freeing = self._drive_being_freed()
        return RetryConditions(
            rip_running=self._rip_thread is not None,
            scan_running=scan is not None and scan.isRunning(),
            newest_request=request == self._disc_retries.request,
            same_drive=self._drive_picker.current_device() == device,
            drive_being_freed=freeing,
            # Not opened while it is being freed (`_drive_being_freed`); the
            # blocker refuses on `drive_being_freed` before it reads this.
            media_status=(
                drive_media.UNAVAILABLE if freeing else self._disc_status_probe(device)
            ),
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
        # Setup & Updates shows THIS drive's offset; a drive change changes it.
        self._refresh_setting_views()

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

    # --- Freeing the drive after a disc probe is cancelled (2026-11-05) ------
    #
    # Cancelling a disc probe kills its HOST side (the wrapper and the `podman
    # exec` client), not the `cyanrip -I` inside the container, which reads on
    # and holds the drive. On the owner's rig (2026-11-05) that left a probe
    # reading beside its replacement, and readers running after the app had
    # closed. These decide when the drive is freed, and when doing so is unsafe.

    def _disc_probe_in_flight_device(self) -> str:
        """The drive a running disc probe is reading, or "" when none is running."""
        thread = self._disc_info_thread
        worker = self._disc_info_worker
        if thread is None or worker is None or not thread.isRunning():
            return ""
        return worker.device

    def _drive_free_refusal(self, device: str) -> str:
        """Why freeing ``device`` after a probe's cancel would be unsafe, or "".

        The free is a device-scoped SIGKILL, and it cannot tell a probe's reader
        from anything else holding the drive. So it is refused while something
        else may legitimately hold it: a rip (whose own stop frees the drive
        gracefully, so its log keeps its footer), a cancelled rip's pending
        rescue, a ui-script ``cyanrip`` call, or a stop already under way.
        """
        if self._rip_thread is not None:
            return "a rip is in flight, and its own stop frees the drive"
        if self._force_stop_timer.isActive():
            return "a cancelled rip's rescue is pending"
        console = self._script_console
        runner = console.runner if console is not None else None
        if runner is not None and runner.cyanrip_in_flight:
            return "a ui-script cyanrip call is running and may be reading it"
        if exit_work.freeing(device):
            return "it is already being freed"
        return ""

    def _superseded_probe_device(self) -> str:
        """The drive the probe being superseded reads, to free before the new one.

        "" when no probe is running, or when freeing is unsafe
        (:meth:`_drive_free_refusal`, said in the log). The NEW worker frees it
        on its own thread before it reads (``DiscInfoWorker``'s ``free_first``),
        so the two probes never read one drive at once.
        """
        device = self._disc_probe_in_flight_device()
        if not device:
            return ""
        refusal = self._drive_free_refusal(device)
        if refusal:
            log.info("not freeing %s before the new disc probe: %s", device, refusal)
            return ""
        return device

    def _free_drive_after_probe_cancel(self, device: str, why: str) -> None:
        """Free ``device`` after its probe was cancelled at close, as exit work.

        Exit work (``exit_work.free_drive_after_cancel``) so the GUI thread does
        not wait and the process does not exit first; the exit check then reports
        what is left after it.
        """
        if not device:
            return
        refusal = self._drive_free_refusal(device)
        if refusal:
            log.info("%s: not freeing %s: %s", why, device, refusal)
            return
        exit_work.free_drive_after_cancel(device, writes_log=False, why=why)


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
        return "not measured yet — runs in Set up drive with an audio CD in"
    if profile.cache_defeat:
        return "Yes — cache defeated on re-read (measured, cd-paranoia)"
    return "No — drive returns cached audio on re-read (measured, cd-paranoia)"
