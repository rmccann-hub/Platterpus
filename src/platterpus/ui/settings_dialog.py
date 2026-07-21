"""Settings dialog — edits the Config dataclass.

The dialog is a pure view: it doesn't read or write the config file
itself. The caller passes in a `Config`, the user edits the widgets,
and the caller reads back via `to_config()` and persists through
`platterpus.config.save()`. This keeps the dialog testable without
touching `~/.config`.

A "Check dependencies" button emits the `check_dependencies_requested`
signal; the caller wires it to the DependencyManager.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from platterpus import goal_presets, naming, offset_config, settings_validation
from platterpus.config import Config
from platterpus.settings_validation import ValidationIssue
from platterpus.ui.accessibility import announce
from platterpus.ui.dialogs.centering import CenteredDialog


class SettingsDialog(CenteredDialog):
    """Modal Settings dialog. Wraps an incoming Config; produces a new one."""

    check_dependencies_requested = Signal()
    detect_offset_requested = Signal()

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config: Config = config

        self.setWindowTitle("Settings")
        self.setModal(True)

        root = QVBoxLayout(self)
        form = QFormLayout()

        # --- Goal preset (anchors the rest of the settings to intent) ---
        # First row on purpose: pick a goal and the format/verification/quality
        # controls below snap to sensible values for it (they stay editable —
        # editing one flips this to "Custom"). See goal_presets.py.
        # Guard so applying a preset (which sets the widgets) doesn't recursively
        # flip the combo back to Custom.
        self._applying_preset: bool = False
        # Screen-reader dedup for the live validation banner: _revalidate runs on
        # every keystroke, but the same issue text must be announced only once
        # (announcing per keystroke would drown the reader — gap #4).
        self._announced_validation_text: str = ""
        self._goal_combo: QComboBox = QComboBox(self)
        for key, label in goal_presets.GOAL_LABELS:
            self._goal_combo.addItem(label, key)
        self._goal_combo.addItem("Custom (hand-tuned below)", goal_presets.GOAL_CUSTOM)
        self._goal_combo.setToolTip(
            "Pick what you want this rip to be and the format, verification, and "
            "quality options below snap to good values for it. You can still "
            "tweak any of them — that switches this to Custom."
        )
        form.addRow("Goal:", self._goal_combo)

        # --- Path rows (QLineEdit + Browse button) ---
        # These fields live inside a composite row widget, so the form label is
        # NOT their buddy (QFormLayout only auto-buddies a directly-added
        # field) — without explicit accessible names they read as anonymous
        # text boxes, and the three identical "Browse…" buttons as
        # indistinguishable (gap #4 sweep finding). _build_dir_row/_build_file_row
        # name both widgets from the name we pass.
        self._output_dir_edit, output_row = self._build_dir_row(
            config.output_dir, "Output directory"
        )
        form.addRow("Output directory:", output_row)

        self._working_dir_edit, working_row = self._build_dir_row(
            config.working_dir, "Working directory"
        )
        form.addRow("Working directory:", working_row)

        # Library folder (optional — empty leaves rips in the output directory).
        # When set, a finished rip's album folder is moved here AFTER every
        # post-rip check settles (see main_window_rip._maybe_schedule_library_move).
        self._library_dir_edit, library_row = self._build_dir_row(
            config.library_dir, "Library folder"
        )
        self._library_dir_edit.setToolTip(
            "Optional. When set, a successful rip's album folder is moved here "
            "once every post-rip check has finished (tagging, cover art, the "
            "verification suite, checksums) — so the output directory stays a "
            "workspace and your library only ever receives finished, verified "
            "rips. Leave empty to keep rips in the output directory."
        )
        form.addRow("Move finished rips to:", library_row)

        # --- Templates ---
        # A preset dropdown so the common layouts are one click instead of a
        # hand-written code string (the old default looked terrible — repeated
        # album/artist + a trailing full date). Picking a preset fills the
        # track/disc template fields below; editing those by hand flips the
        # dropdown to "Custom". A live preview shows the real resulting filename.
        self._naming_combo: QComboBox = QComboBox(self)
        self._naming_combo.setAccessibleName("File naming scheme")
        for preset in naming.PRESETS:
            self._naming_combo.addItem(preset.label, preset.key)
        self._naming_combo.addItem(naming.CUSTOM_LABEL, None)
        form.addRow("Naming scheme:", self._naming_combo)

        self._track_template_edit: QLineEdit = QLineEdit(config.track_template, self)
        self._track_template_edit.setToolTip(
            "Path for identified discs. Codes: %A artist, %d album, "
            "%t track #, %n title, %a track artist, %y date, %Y year (4-digit).\n"
            "Pick a preset above, or hand-edit here."
        )
        form.addRow("Track template:", self._track_template_edit)

        self._disc_template_edit: QLineEdit = QLineEdit(config.disc_template, self)
        form.addRow("Disc template (.log/.cue):", self._disc_template_edit)

        # Live preview: the selected template rendered against a metadata-heavy
        # sample (colon in the title, a featured/per-track artist) so the user
        # sees how it copes with the awkward cases before committing. Updates as
        # the preset or the template text changes.
        self._naming_preview: QLabel = QLabel("", self)
        self._naming_preview.setWordWrap(True)
        self._naming_preview.setAccessibleName("Filename preview")
        self._naming_preview.setStyleSheet("color: palette(mid);")
        form.addRow("Example:", self._naming_preview)

        # Wire up: preset → fill fields; manual edit → flip to Custom; either →
        # refresh preview. Signals are blocked while syncing to avoid a loop.
        self._naming_combo.currentIndexChanged.connect(self._on_naming_preset_chosen)
        self._track_template_edit.textChanged.connect(self._on_template_text_changed)
        self._disc_template_edit.textChanged.connect(self._on_template_text_changed)
        self._sync_naming_combo_to_templates()
        self._refresh_naming_preview()

        # Unknown-disc templates: used for the --unknown rip so the
        # disc-ID hash whipper puts in %d never reaches the path.
        self._track_template_unknown_edit: QLineEdit = QLineEdit(
            config.track_template_unknown, self
        )
        form.addRow("Track template (unknown):", self._track_template_unknown_edit)

        self._disc_template_unknown_edit: QLineEdit = QLineEdit(
            config.disc_template_unknown, self
        )
        form.addRow("Disc template (unknown):", self._disc_template_unknown_edit)

        # --- Read offset ---
        # Two ways to set the read offset:
        #   1. The drive-setup wizard ("Re-detect…") detects it and the GUI
        #      saves it here — the recommended path.
        #   2. Type it here and tick "Apply" so each rip uses it (cyanrip's
        #      `-s`). cyanrip needs the offset every run; it has no config file
        #      of its own, so this value is the single source.
        self._read_offset_spin: QSpinBox = QSpinBox(self)
        # In a composite row (spin + Re-detect button), so no auto-buddy — name
        # it explicitly for screen readers (same reasoning as the path rows).
        self._read_offset_spin.setAccessibleName("Read offset in samples")
        # Range comes from settings_validation (the single source of truth) so the
        # widget bound and the validator can never drift. AccurateRip offsets are
        # in the low hundreds of samples; ±5000 blocks typos like "60000".
        self._read_offset_spin.setRange(
            settings_validation.OFFSET_MIN, settings_validation.OFFSET_MAX
        )
        self._read_offset_spin.setValue(config.read_offset)
        self._read_offset_spin.setToolTip(
            "Read offset in samples (signed). Tick Apply to use this value for "
            "rips (cyanrip's -s). Set it once per drive via Re-detect…."
        )
        self._detect_offset_button: QPushButton = QPushButton("Re-&detect…", self)
        self._detect_offset_button.setToolTip(
            "Run the drive setup wizard to auto-detect the read offset and "
            "save it to Platterpus's settings."
        )
        self._detect_offset_button.clicked.connect(self.detect_offset_requested)
        offset_row = QHBoxLayout()
        offset_row.addWidget(self._read_offset_spin, stretch=1)
        offset_row.addWidget(self._detect_offset_button)
        form.addRow("Read offset (samples):", offset_row)

        self._override_offset_check: QCheckBox = QCheckBox(
            "Apply this read offset to rips", self
        )
        self._override_offset_check.setChecked(config.override_read_offset)
        self._override_offset_check.setToolTip(
            "When on, each rip uses the offset above (cyanrip's -s). Leave it on "
            "once you've set your drive's offset — cyanrip needs it every rip to "
            "stay bit-perfect."
        )
        form.addRow("", self._override_offset_check)

        # Show any read offset found in a legacy whipper.conf, as a trust check
        # against the value above. A pre-Platterpus or hand-edited whipper.conf
        # may still hold a per-drive offset; cyanrip doesn't read it (it uses the
        # value above), but surfacing it lets the user spot a mismatch. Reading
        # this tiny file on the GUI thread is fine (bytes, not a subprocess).
        self._live_offset_label: QLabel = QLabel(
            f"Legacy whipper.conf read offset: {offset_config.describe_conf_offsets()}",
            self,
        )
        self._live_offset_label.setWordWrap(True)
        self._live_offset_label.setToolTip(
            "A read offset found in an old whipper.conf, shown for reference. "
            "cyanrip uses the value above, not this file. 'none set' is normal."
        )
        form.addRow("", self._live_offset_label)

        # --- Tool paths ---
        self._metaflac_path_edit, metaflac_row = self._build_file_row(
            config.metaflac_path, "metaflac path"
        )
        form.addRow("metaflac path:", metaflac_row)

        # --- Output format ---
        # Every rip produces FLAC (the lossless master); a non-FLAC choice is
        # derived afterwards by a post-rip ffmpeg transcode, with the FLAC kept.
        # Item data is the raw config value.
        self._format_combo: QComboBox = QComboBox(self)
        for label, value in (
            ("FLAC — lossless archival master (recommended)", "flac"),
            ("WavPack (.wv) — lossless, with tags", "wavpack"),
            ("MP3 — lossy, best-quality VBR, with tags + cover", "mp3"),
            ("WAV — raw PCM, no tags or cover art", "wav"),
        ):
            self._format_combo.addItem(label, value)
        format_index = self._format_combo.findData(config.output_format)
        self._format_combo.setCurrentIndex(format_index if format_index >= 0 else 0)
        self._format_combo.setToolTip(
            "What the rip delivers. FLAC is the lossless archival master and is "
            "always produced; for any other choice the GUI keeps that FLAC and "
            "creates the selected format alongside it (a post-rip transcode). "
            "FLAC and WavPack are lossless; MP3 is high-quality lossy (VBR ~245 "
            "kbps) for portability; WAV is raw PCM and can't store tags or art."
        )
        form.addRow("Output format:", self._format_combo)

        # WAV is the one format that can't carry tags/cover art (RIFF has no
        # tag chunk). Surface that the moment WAV is picked so it's never a
        # silent surprise — WavPack is the lossless-with-tags alternative.
        self._wav_warning_label: QLabel = QLabel(
            "⚠ WAV can't store tags or cover art. For lossless audio that keeps "
            "your metadata, choose WavPack instead.",
            self,
        )
        self._wav_warning_label.setWordWrap(True)
        form.addRow("", self._wav_warning_label)
        self._format_combo.currentIndexChanged.connect(self._update_wav_warning)
        self._update_wav_warning()

        # MP3 encoder quality (ffmpeg -q:a N == lame -V N). 0 is the
        # best-practice VBR (~245 kbps — HydrogenAudio's recommendation, and
        # the fixed value this shipped with); higher numbers trade quality for
        # smaller files. Only meaningful when the output format is MP3, so the
        # control enables/disables with the format combo. Deliberately NOT
        # goal-driven: no preset sets it (Portable picks MP3 but keeps the
        # best-practice quality), so switching Goal never touches it and
        # editing it never flips the Goal to Custom.
        self._mp3_quality_spin: QSpinBox = QSpinBox(self)
        self._mp3_quality_spin.setRange(
            settings_validation.MP3_QUALITY_MIN, settings_validation.MP3_QUALITY_MAX
        )
        self._mp3_quality_spin.setValue(config.mp3_vbr_quality)
        self._mp3_quality_spin.setToolTip(
            "MP3 encoder quality (VBR): 0 = best quality (~245 kbps, the "
            "recommended default — the same as lame -V0), 9 = smallest files. "
            "Only affects MP3 output; the FLAC master is always lossless."
        )
        form.addRow("MP3 VBR quality:", self._mp3_quality_spin)
        self._format_combo.currentIndexChanged.connect(self._update_mp3_quality_enabled)
        self._update_mp3_quality_enabled()

        # --- Toggles ---
        self._auto_picard_check: QCheckBox = QCheckBox(
            "Launch MusicBrainz Picard on unknown discs", self
        )
        self._auto_picard_check.setChecked(config.auto_launch_picard)
        form.addRow("Picard integration:", self._auto_picard_check)

        # Auto-eject the disc when a rip finishes successfully. Convenience
        # only — the manual Eject button next to the drive picker works
        # regardless of this toggle.
        self._auto_eject_check: QCheckBox = QCheckBox(
            "Eject the disc after a successful rip", self
        )
        self._auto_eject_check.setChecked(config.auto_eject_after_rip)
        self._auto_eject_check.setToolTip(
            "When a rip completes successfully, eject the disc automatically. "
            "Leave off if you rip several discs from the same tray."
        )
        form.addRow("After rip:", self._auto_eject_check)

        # Desktop notification when a rip finishes — so an unattended rip alerts
        # you even when Platterpus isn't the focused window. On by default.
        self._notify_check: QCheckBox = QCheckBox(
            "Show a desktop notification when a rip finishes", self
        )
        self._notify_check.setChecked(config.notify_on_completion)
        self._notify_check.setToolTip(
            "Pop a desktop notification when a rip completes (or fails), so you "
            "don't have to watch the window. A rip you cancel yourself is not "
            "announced."
        )
        form.addRow("", self._notify_check)

        # Debug logging — verbose log file for bug reports. Off by default;
        # testers turn it on, reproduce the issue, then attach the log.
        self._debug_logging_check: QCheckBox = QCheckBox(
            "Debug logging (verbose log for bug reports)", self
        )
        self._debug_logging_check.setChecked(config.debug_logging)
        self._debug_logging_check.setToolTip(
            "Record verbose detail to the log file at\n"
            "~/.local/share/platterpus/log.txt — every probe, command, and "
            "parse step. Turn this on, reproduce the problem, then attach that "
            "file to a bug report. Off keeps the log lighter."
        )
        form.addRow("Logging:", self._debug_logging_check)

        # --- EAC bit-perfect parity gaps (KDD-13) ---
        # Cover art: "" = don't fetch. With cyanrip the GUI fetches the front
        # cover from the Cover Art Archive after the rip and embeds it.
        self._cover_art_combo: QComboBox = QComboBox(self)
        for label, value in (
            ("Don't fetch", ""),
            ("Embed in FLAC", "embed"),
            ("Save as file", "file"),
            ("Embed and save file", "complete"),
        ):
            self._cover_art_combo.addItem(label, value)
        cover_index = self._cover_art_combo.findData(config.cover_art)
        self._cover_art_combo.setCurrentIndex(cover_index if cover_index >= 0 else 0)
        self._cover_art_combo.setToolTip(
            "Fetch album cover art and embed it in the FLACs and/or save it "
            "as a file. The app fetches the front cover from the Cover Art "
            "Archive once the rip finishes. EAC embeds by default."
        )
        form.addRow("Cover art:", self._cover_art_combo)

        # Also save back cover + booklet scans (as files — they can't be embedded).
        # "and", not "&": Qt eats a lone "&" in a widget label as a mnemonic
        # marker (it was rendering "back cover  booklet images" + a stray
        # Alt+Space shortcut). Spelling it out avoids the ampersand entirely.
        self._additional_art_check: QCheckBox = QCheckBox(
            "Also save back cover and booklet images", self
        )
        self._additional_art_check.setChecked(config.save_additional_art)
        self._additional_art_check.setToolTip(
            "When fetching cover art, also save any back cover and booklet scans "
            "the Cover Art Archive has (as back.jpg / booklet-NN.jpg beside the "
            "audio). These can't be embedded in FLAC, so they're saved as files."
        )
        form.addRow("", self._additional_art_check)

        self._max_retries_spin: QSpinBox = QSpinBox(self)
        self._max_retries_spin.setRange(
            settings_validation.MAX_RETRIES_MIN, settings_validation.MAX_RETRIES_MAX
        )
        self._max_retries_spin.setValue(config.max_retries)
        self._max_retries_spin.setToolTip(
            "How many times the ripper retries a troublesome track before "
            "giving up (cyanrip's -r). 5 is the default."
        )
        form.addRow("Max retries:", self._max_retries_spin)

        # Overread (cyanrip -O): opt-in, effect-first wording (gap #5 style).
        # Deliberately NOT goal-driven — it's a drive-capability call, not a
        # rip-goal trade-off, so switching Goal never flips it.
        self._force_overread_check: QCheckBox = QCheckBox(
            "Read the disc's outermost samples (overread lead-in/out)", self
        )
        self._force_overread_check.setChecked(config.force_overread)
        self._force_overread_check.setToolTip(
            "With a read offset applied, a disc's very first and last samples "
            "sit in the lead-in/lead-out. Off (default): those few samples are "
            'written as silence — the same as EAC\'s "overread: No", and how '
            "this app's EAC parity baseline matched. On: the drive is asked to "
            "actually read them (cyanrip's -O). Advanced: only some drives can "
            "overread — cyanrip warns an unsupported drive may freeze, so turn "
            "this on only if you know your drive supports it."
        )
        form.addRow("Overread:", self._force_overread_check)

        # --- Marginal-disc convergence (cyanrip -Z N, EAC-parity item 1) ---
        # Secure re-rip effort: the MAX number of reads to spend confirming a
        # track that doesn't match AccurateRip. Ripping is always "dynamic" now —
        # a track that matches the database on its first read is kept as-is; only
        # an unproven track is re-read (up to this many agreeing reads). So this is
        # a ceiling, not a per-track tax, and there's no separate on/off toggle.
        self._secure_rerip_spin: QSpinBox = QSpinBox(self)
        self._secure_rerip_spin.setRange(
            settings_validation.SECURE_REREP_MIN, settings_validation.SECURE_REREP_MAX
        )
        self._secure_rerip_spin.setValue(config.secure_rerip_matches)
        self._secure_rerip_spin.setSpecialValueText("Off")  # shown when value is 0
        self._secure_rerip_spin.setToolTip(
            "The MOST reads to spend confirming a track that doesn't match the "
            "AccurateRip database (cyanrip's -Z). Platterpus rips the disc once at "
            "full speed and only re-reads a track that didn't verify, until this "
            "many reads agree — the number you pick is the ceiling. 2 is a good "
            "value; 0 (Off) accepts the fast read even when it can't be verified. "
            "Clean, in-database discs finish in one fast pass either way."
        )
        form.addRow("Max reads to confirm a shaky track:", self._secure_rerip_spin)

        # --- Adaptive read-speed ladder (headline, 0.4.6) ---
        # "Adaptive ladder" (default): rip fast, and only if a disc reads with
        # errors, re-rip it slower (and, at the floor, harder). "Fixed speed"
        # disables the ladder and always rips at the chosen speed. The fixed
        # spinner is enabled only in Fixed mode.
        self._read_speed_mode_combo: QComboBox = QComboBox(self)
        self._read_speed_mode_combo.addItem(
            "Adaptive ladder — fast, slower only if a disc needs it", "auto_ladder"
        )
        self._read_speed_mode_combo.addItem("Fixed speed (advanced)", "fixed")
        self._read_speed_mode_combo.setAccessibleName("Read speed mode")
        mode_index = self._read_speed_mode_combo.findData(config.read_speed_mode)
        self._read_speed_mode_combo.setCurrentIndex(
            mode_index if mode_index >= 0 else 0
        )
        self._read_speed_mode_combo.setToolTip(
            "Adaptive ladder (recommended): start at the drive's top speed and, "
            "only if a disc reads with errors, re-rip it a rung slower "
            "(max → 8× → 4× → 2×) and then re-read harder. Quality only ever "
            "goes up. Fixed speed disables the ladder and always rips at the "
            "speed below (advanced; some drives read marginal discs better slow)."
        )
        form.addRow("Read speed:", self._read_speed_mode_combo)

        self._read_speed_spin: QSpinBox = QSpinBox(self)
        self._read_speed_spin.setRange(  # 0 = drive max; CD ×-speeds
            settings_validation.READ_SPEED_MIN, settings_validation.READ_SPEED_MAX
        )
        self._read_speed_spin.setValue(config.read_speed)
        self._read_speed_spin.setAccessibleName("Fixed read speed (drive multiplier)")
        self._read_speed_spin.setSpecialValueText("Max")  # shown when value is 0
        self._read_speed_spin.setToolTip(
            "The fixed drive read speed (cyanrip's -S), used only in Fixed-speed "
            "mode. 'Max' (0) lets the drive pick. Whether the drive honours this "
            "depends on the drive + Linux stack."
        )
        form.addRow("Fixed speed (×):", self._read_speed_spin)
        # The fixed-speed spinner only applies in Fixed mode.
        self._read_speed_mode_combo.currentIndexChanged.connect(
            self._update_read_speed_enabled
        )
        self._update_read_speed_enabled()

        # --- CTDB verification (KDD-14 Phase 1) ---
        # A second, TOC-keyed verification path alongside AccurateRip. Off by
        # default: it's a post-rip network call. The audio-CRC algorithm was
        # hardware-validated (KDD-16, 2026-07-07), so a match now reads as a real
        # "verified" — the same standing as an AccurateRip match.
        self._ctdb_verify_check: QCheckBox = QCheckBox(
            "Verify with CTDB after a rip", self
        )
        self._ctdb_verify_check.setChecked(config.ctdb_verify_after_rip)
        self._ctdb_verify_check.setToolTip(
            "After a successful rip, also check it against the CUETools "
            "Database (a second verification path alongside AccurateRip). This "
            "is a network lookup and decodes the FLACs locally (needs `flac`). "
            "The CRC algorithm is confirmed on real hardware, so a match reads "
            "as verified — it can only ever under-claim, never fabricate a "
            "'verified'. Off by default."
        )
        form.addRow("CTDB:", self._ctdb_verify_check)

        # --- FLAC encode-verify ---
        # Post-rip `flac --test` of each output FLAC (decode + MD5 check). On by
        # default — cyanrip (FFmpeg) doesn't self-verify, so this is a real check.
        self._verify_flac_check: QCheckBox = QCheckBox(
            "Verify FLAC files after a rip", self
        )
        self._verify_flac_check.setChecked(config.verify_flac_after_rip)
        self._verify_flac_check.setToolTip(
            "After a successful rip, run `flac --test` on each FLAC to confirm "
            "it decodes back to its stored checksum (catches encode or disk "
            "corruption). Needs `flac`; runs in the background and only speaks "
            "up if a file fails. On by default."
        )
        form.addRow("Verify FLACs:", self._verify_flac_check)

        # --- FLAC re-compress ---
        # Post-rip `flac -8` re-encode to shrink the output. cyanrip (the sole
        # backend) already encodes FLAC at maximum compression, so there's
        # nothing to gain — the post-rip step skips it for cyanrip. The toggle
        # is shown disabled (value kept) with a tooltip saying why, rather than
        # hidden, so the option's existence and rationale stay discoverable.
        self._recompress_flac_check: QCheckBox = QCheckBox(
            "Re-compress FLAC files after a rip (smaller files)", self
        )
        self._recompress_flac_check.setChecked(config.recompress_flac_after_rip)
        self._recompress_flac_check.setEnabled(False)
        self._recompress_flac_check.setToolTip(
            "Read-only: cyanrip already encodes FLAC at maximum compression, so "
            "re-compressing would only burn CPU for no size gain. Your value is "
            "kept either way."
        )
        form.addRow("Re-compress FLACs:", self._recompress_flac_check)

        # --- EAC-layout companion log ---
        # Write an honest, clearly-attributed EAC-*layout* text log beside each
        # rip (never a signed/forged EAC log). Off by default.
        self._eac_log_check: QCheckBox = QCheckBox(
            "Write an EAC-compatible log beside each rip", self
        )
        self._eac_log_check.setChecked(config.write_eac_log_after_rip)
        self._eac_log_check.setToolTip(
            "After a successful rip, save an EAC-layout text log next to the "
            "audio (as '… (EAC-compatible).log') so you can diff it against a "
            "real EAC log or keep a familiar-looking record. It is clearly marked "
            "as generated by Platterpus and is never a signed EAC log."
        )
        form.addRow("EAC-style log:", self._eac_log_check)

        root.addLayout(form)

        # --- Live input validation (visible errors during the change) ---
        # A banner that lists what's wrong with the current inputs and marks the
        # offending fields — required by CLAUDE.md's "validate every input" rule
        # (visible error at the point of entry + logged on save). The heavy
        # lifting is a pure, tested validator (settings_validation); this label is
        # just its view. Starts hidden and only appears when something's off.
        self._validation_label: QLabel = QLabel("", self)
        self._validation_label.setWordWrap(True)
        self._validation_label.setAccessibleName("Settings validation messages")
        self._validation_label.setVisible(False)
        root.addWidget(self._validation_label)

        # Map each validated free-text field to its widget, so an issue can mark
        # the exact row the user needs to fix. (Spinboxes/combos can't produce an
        # invalid value through the UI, so only the free-text edits are marked.)
        self._validated_widgets: dict[str, QWidget] = {
            "output_dir": self._output_dir_edit,
            "working_dir": self._working_dir_edit,
            "library_dir": self._library_dir_edit,
            "track_template": self._track_template_edit,
            "disc_template": self._disc_template_edit,
            "track_template_unknown": self._track_template_unknown_edit,
            "disc_template_unknown": self._disc_template_unknown_edit,
            "metaflac_path": self._metaflac_path_edit,
        }
        # Re-validate as the user edits any free-text field, so the error shows
        # up *during* the change (the two known-disc templates already have a
        # textChanged slot — _on_template_text_changed calls _revalidate too).
        for edit in (
            self._output_dir_edit,
            self._working_dir_edit,
            self._library_dir_edit,
            self._track_template_unknown_edit,
            self._disc_template_unknown_edit,
            self._metaflac_path_edit,
        ):
            edit.textChanged.connect(self._revalidate)

        # --- Goal preset wiring (after all dependent widgets exist) ---
        self._wire_goal_presets()

        # --- Check dependencies action ---
        # This sits between the form and the OK/Cancel row so it's
        # visually associated with the settings (which is where the
        # paths live that the dep check verifies).
        self._check_deps_button: QPushButton = QPushButton("Chec&k dependencies", self)
        self._check_deps_button.clicked.connect(self.check_dependencies_requested)
        root.addWidget(self._check_deps_button)

        # --- OK / Cancel ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        root.addWidget(button_box)

        # Validate the incoming config once so a hand-edited/invalid config.toml
        # surfaces its errors the moment Settings opens, not only on save.
        self._revalidate()

    # --- Public surface -----------------------------------------------------

    def to_config(self) -> Config:
        """Build a new Config reflecting the current widget state.

        Preserves the schema_version from the source Config (since the
        dialog doesn't model that field — bumping it is migration
        plumbing's job, not the user's).
        """
        return Config(
            output_dir=self._output_dir_edit.text(),
            working_dir=self._working_dir_edit.text(),
            library_dir=self._library_dir_edit.text(),
            track_template=self._track_template_edit.text(),
            disc_template=self._disc_template_edit.text(),
            track_template_unknown=self._track_template_unknown_edit.text(),
            disc_template_unknown=self._disc_template_unknown_edit.text(),
            metaflac_path=self._metaflac_path_edit.text(),
            read_offset=self._read_offset_spin.value(),
            override_read_offset=self._override_offset_check.isChecked(),
            auto_launch_picard=self._auto_picard_check.isChecked(),
            auto_eject_after_rip=self._auto_eject_check.isChecked(),
            notify_on_completion=self._notify_check.isChecked(),
            debug_logging=self._debug_logging_check.isChecked(),
            cover_art=self._cover_art_combo.currentData(),
            max_retries=self._max_retries_spin.value(),
            force_overread=self._force_overread_check.isChecked(),
            secure_rerip_matches=self._secure_rerip_spin.value(),
            # Dynamic secure re-rip is the behaviour now, not a UI toggle — carry
            # the stored value through unchanged (a power user can flip it in TOML).
            secure_rerip_dynamic=self._config.secure_rerip_dynamic,
            read_speed_mode=self._read_speed_mode_combo.currentData(),
            read_speed=self._read_speed_spin.value(),
            ctdb_verify_after_rip=self._ctdb_verify_check.isChecked(),
            verify_flac_after_rip=self._verify_flac_check.isChecked(),
            recompress_flac_after_rip=self._recompress_flac_check.isChecked(),
            write_eac_log_after_rip=self._eac_log_check.isChecked(),
            save_additional_art=self._additional_art_check.isChecked(),
            output_format=self._format_combo.currentData(),
            rip_goal=self._goal_combo.currentData(),
            mp3_vbr_quality=self._mp3_quality_spin.value(),
            # Preserve fields the dialog doesn't model, so saving Settings
            # never silently resets them (these one-time "already offered"
            # flags being reset is what re-triggered the first-run prompts).
            drive_setup_prompted=self._config.drive_setup_prompted,
            host_setup_prompted=self._config.host_setup_prompted,
            appimage_integration_prompted=self._config.appimage_integration_prompted,
            integration_declined_path=self._config.integration_declined_path,
            schema_version=self._config.schema_version,
        )

    # --- Internals ---------------------------------------------------------

    def _update_wav_warning(self) -> None:
        """Show the no-tags/art warning only when WAV is the selected format."""
        self._wav_warning_label.setVisible(self._format_combo.currentData() == "wav")

    def _update_mp3_quality_enabled(self) -> None:
        """The MP3 quality knob only applies when MP3 is the chosen format."""
        self._mp3_quality_spin.setEnabled(self._format_combo.currentData() == "mp3")

    def _update_read_speed_enabled(self) -> None:
        """The fixed-speed spinner only applies in Fixed mode; in Adaptive-ladder
        mode the speed is chosen automatically, so grey the spinner out."""
        self._read_speed_spin.setEnabled(
            self._read_speed_mode_combo.currentData() == "fixed"
        )

    # --- Naming presets ----------------------------------------------------

    def _on_naming_preset_chosen(self) -> None:
        """Fill the template fields from the chosen preset.

        "Custom" (data is None) leaves the fields alone — it just means the
        current templates don't match a preset. We block the edits' signals so
        setting their text doesn't immediately re-sync the combo back.
        """
        key = self._naming_combo.currentData()
        if key is None:
            return
        preset = next((p for p in naming.PRESETS if p.key == key), None)
        if preset is None:
            return
        self._track_template_edit.blockSignals(True)
        self._disc_template_edit.blockSignals(True)
        self._track_template_edit.setText(preset.track_template)
        self._disc_template_edit.setText(preset.disc_template)
        self._track_template_edit.blockSignals(False)
        self._disc_template_edit.blockSignals(False)
        self._refresh_naming_preview()

    def _on_template_text_changed(self) -> None:
        """A hand-edit of either template re-syncs the combo, preview, and the
        live validation (so a bad token shows an error as it's typed)."""
        self._sync_naming_combo_to_templates()
        self._refresh_naming_preview()
        self._revalidate()

    # --- Input validation (visible errors + block-on-save + logging) --------

    def accept(self) -> None:  # noqa: D102 — Qt override
        """OK pressed. Refuse to save while any input is a hard error — show the
        errors, mark the fields, and log them (so a bug report carries them).
        Warnings don't block. A clean/valid dialog accepts exactly as before."""
        issues = settings_validation.validate_config(self.to_config())
        if settings_validation.errors_only(issues):
            settings_validation.log_issues(issues)
            self._render_validation(issues)
            return  # keep the dialog open until the errors are fixed
        super().accept()

    def _revalidate(self) -> None:
        """Validate the current widget state and show any issues inline. Cheap
        enough to run on every keystroke (a pure function + a couple of stat
        calls), which is what makes the error visible *during* the change."""
        self._render_validation(settings_validation.validate_config(self.to_config()))

    def _render_validation(self, issues: list[ValidationIssue]) -> None:
        """Paint the validation state: mark offending fields and fill the banner.

        Errors are red, warnings amber; errors are listed first. With no issues
        the banner hides and every field's mark is cleared."""
        # Clear all field marks first so a fixed field loses its red border.
        for widget in self._validated_widgets.values():
            widget.setStyleSheet("")
        if not issues:
            self._validation_label.clear()
            self._validation_label.setVisible(False)
            # Issues cleared: reset the announce dedup so the SAME issue coming
            # back later (e.g. the path re-broken) is announced again.
            self._announced_validation_text = ""
            return
        errors = [i for i in issues if i.is_error()]
        warnings = [i for i in issues if not i.is_error()]
        for issue in issues:
            field_widget = self._validated_widgets.get(issue.field)
            if field_widget is not None:
                colour = "#c0392b" if issue.is_error() else "#b9770e"
                field_widget.setStyleSheet(f"border: 1px solid {colour};")
        lines = [f"✖ {i.message}" for i in errors] + [
            f"⚠ {i.message}" for i in warnings
        ]
        banner_text = "\n".join(lines)
        self._validation_label.setText(banner_text)
        self._validation_label.setStyleSheet(
            "color: #c0392b;" if errors else "color: #b9770e;"
        )
        self._validation_label.setVisible(True)
        # "Visible, specific error at the point of entry" must include hearing
        # it: announce the banner focus-safely, once per distinct text (this
        # runs on every keystroke while an issue persists — see the dedup attr).
        if banner_text != self._announced_validation_text:
            self._announced_validation_text = banner_text
            announce(self._validation_label, banner_text)

    def _sync_naming_combo_to_templates(self) -> None:
        """Point the combo at the matching preset, or "Custom" if hand-edited.

        Combo signals are blocked so this never re-triggers preset application.
        """
        preset = naming.preset_for_templates(
            self._track_template_edit.text(), self._disc_template_edit.text()
        )
        target = preset.key if preset is not None else None
        index = self._naming_combo.findData(target)
        if index < 0:
            return
        self._naming_combo.blockSignals(True)
        self._naming_combo.setCurrentIndex(index)
        self._naming_combo.blockSignals(False)

    def _refresh_naming_preview(self) -> None:
        """Render the current track template against the stress sample."""
        example = naming.render_preview(
            self._track_template_edit.text(), naming.SAMPLE_STRESS
        )
        self._naming_preview.setText(example)

    # --- Goal presets ------------------------------------------------------

    # The controls a goal preset drives — editing any of them flips the goal to
    # "Custom" (their changed-signals are wired to _on_dependent_changed).
    def _goal_driven_widgets(self) -> list[QWidget]:
        return [
            self._format_combo,
            self._ctdb_verify_check,
            self._recompress_flac_check,
            self._secure_rerip_spin,
            self._read_speed_mode_combo,
        ]

    def _wire_goal_presets(self) -> None:
        """Show the goal matching the incoming config, then keep combo and
        controls in sync: picking a goal sets the controls; editing a control
        flips the goal to Custom."""
        detected = goal_presets.detect_goal(self._config)
        index = self._goal_combo.findData(detected)
        self._goal_combo.setCurrentIndex(index if index >= 0 else 0)
        self._goal_combo.currentIndexChanged.connect(self._on_goal_changed)
        # A control changing means the user hand-tuned away from the preset.
        self._format_combo.currentIndexChanged.connect(self._on_dependent_changed)
        self._ctdb_verify_check.toggled.connect(self._on_dependent_changed)
        self._recompress_flac_check.toggled.connect(self._on_dependent_changed)
        self._secure_rerip_spin.valueChanged.connect(self._on_dependent_changed)
        self._read_speed_mode_combo.currentIndexChanged.connect(
            self._on_dependent_changed
        )

    def _on_goal_changed(self) -> None:
        """Apply the selected preset to the dependent controls."""
        goal = self._goal_combo.currentData()
        if goal == goal_presets.GOAL_CUSTOM:
            return  # Custom doesn't impose values
        preset = goal_presets.PRESETS.get(goal)
        if preset is None:
            return
        # Guard so the setValue/setChecked calls below don't re-enter
        # _on_dependent_changed and bounce the combo to Custom.
        self._applying_preset = True
        try:
            fmt_index = self._format_combo.findData(preset.output_format)
            if fmt_index >= 0:
                self._format_combo.setCurrentIndex(fmt_index)
            self._ctdb_verify_check.setChecked(preset.ctdb_verify_after_rip)
            self._recompress_flac_check.setChecked(preset.recompress_flac_after_rip)
            self._secure_rerip_spin.setValue(preset.secure_rerip_matches)
            mode_index = self._read_speed_mode_combo.findData(preset.read_speed_mode)
            if mode_index >= 0:
                self._read_speed_mode_combo.setCurrentIndex(mode_index)
        finally:
            self._applying_preset = False

    def _on_dependent_changed(self) -> None:
        """A goal-driven control was edited by the user → switch to Custom."""
        if self._applying_preset:
            return  # we're the ones setting it, not the user
        custom_index = self._goal_combo.findData(goal_presets.GOAL_CUSTOM)
        if custom_index >= 0 and self._goal_combo.currentIndex() != custom_index:
            self._goal_combo.setCurrentIndex(custom_index)

    def _build_dir_row(
        self, initial_path: str, accessible_name: str
    ) -> tuple[QLineEdit, QWidget]:
        """Build a row: QLineEdit + 'Browse…' button (for directories).

        `accessible_name` names the field for screen readers (the composite row
        breaks QFormLayout's auto-buddy) and disambiguates its Browse button
        from the other rows' identical ones.
        """
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        edit = QLineEdit(initial_path, row)
        edit.setAccessibleName(accessible_name)
        button = QPushButton("Browse…", row)
        button.setAccessibleName(f"Browse for {accessible_name.lower()}")
        button.clicked.connect(lambda: self._pick_directory(edit))

        layout.addWidget(edit, stretch=1)
        layout.addWidget(button)
        return edit, row

    def _build_file_row(
        self, initial_path: str, accessible_name: str
    ) -> tuple[QLineEdit, QWidget]:
        """Build a row: QLineEdit + 'Browse…' button (for an executable).

        Same accessible-name reasoning as `_build_dir_row`.
        """
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        edit = QLineEdit(initial_path, row)
        edit.setAccessibleName(accessible_name)
        button = QPushButton("Browse…", row)
        button.setAccessibleName(f"Browse for {accessible_name.lower()}")
        button.clicked.connect(lambda: self._pick_file(edit))

        layout.addWidget(edit, stretch=1)
        layout.addWidget(button)
        return edit, row

    def _pick_directory(self, edit: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose directory", edit.text())
        if path:
            edit.setText(path)

    def _pick_file(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose binary", edit.text())
        if path:
            edit.setText(path)
