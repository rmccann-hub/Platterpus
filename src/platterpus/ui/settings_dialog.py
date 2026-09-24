"""Settings dialog — edits the Config dataclass.

The dialog is a pure view: it doesn't read or write the config file
itself. The caller passes in a `Config`, the user edits the widgets,
and the caller reads back via `to_config()` and persists through
`platterpus.config.save()`. This keeps the dialog testable without
touching `~/.config`.

It opens nothing else. It used to carry two doors to other windows — a
"Check dependencies" button and a "Re-detect…" button beside the read offset —
and both were removed on 2026-09-23 (maintainer: *"this probably doesnt need
multiple access points"*). Each duplicated a button in **Tools → Setup &
Updates…**, and the second one was worse than a duplicate: the drive wizard it
opened saved a new offset while this dialog still showed the old one, so
pressing OK wrote the old one back. See :func:`apply_user_edits`.

**It edits the rip, and only the rip** (2026-09-24). Seven settings used to have
a second editor here as well as their real one, and each now has ONE home,
recorded in :mod:`platterpus.ui.setting_homes`: the read offset and its Apply
tick-box live in the drive wizard (this dialog still SHOWS the offset, read-only,
because a rip depends on it), the two update channels live beside the checks
they steer in Setup & Updates, and the startup test script lives in the script
console. A field this dialog does not edit is carried through untouched from the
config it opened with, so pressing OK can never write it — and its validation is
not this dialog's to show, because a user cannot fix it here.

**OK, Apply, Cancel, Restore Defaults** — KDE's convention. Apply saves what you
changed and keeps the window open; Cancel then discards only what changed after
the last Apply; Restore Defaults resets this dialog's controls to the shipped
defaults and saves nothing until OK or Apply. It is safe to offer now that OK
writes only the fields you changed, and it touches none of the settings homed
elsewhere: resetting the read offset from here would rip the next disc at +0.
"""

from __future__ import annotations

import dataclasses
import logging

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from platterpus import (
    goal_presets,
    naming,
    offset_config,
    option_labels,
    settings_validation,
)
from platterpus.config import Config
from platterpus.paths import LOG_PATH
from platterpus.settings_validation import ValidationIssue
from platterpus.ui.accessibility import announce
from platterpus.ui.dialogs.centering import CenteredDialog
from platterpus.ui.scroll_guards import WheelGuard, protect_value_widgets
from platterpus.ui.setting_homes import (
    DRIVE_SETUP,
    SETTING_HOMES,
    SETTINGS,
    WINDOW_PATHS,
    fields_homed_in,
)
from platterpus.ui.status_colours import SECONDARY_STYLE, status_colour, status_style
from platterpus.user_settings import apply_user_edits, with_values

log: logging.Logger = logging.getLogger(__name__)


class SettingsDialog(CenteredDialog):
    """Modal Settings dialog. Wraps an incoming Config; produces a new one."""

    #: Apply was pressed with valid inputs. The window saves exactly what OK
    #: would (``user_edits_applied_to``) and then calls :meth:`mark_applied`, so
    #: the dialog stays a view and there is one save path, not two.
    apply_requested = Signal()

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config: Config = config
        # What the widgets were loaded from, as an independent copy. `config` is
        # usually the window's LIVE object, which other code may change while
        # this modal is open; the widgets are not refreshed when it does. So the
        # only honest record of "what the user saw" is a snapshot taken here, and
        # `user_edits()` compares against it.
        self._opened_with: Config = dataclasses.replace(config)

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
        # One shared constant, not a second literal: the naming-scheme combo
        # four hundred lines below needs the same row, and the two spellings
        # used to sit far enough apart to drift unnoticed.
        self._goal_combo.addItem(option_labels.CUSTOM_LABEL, goal_presets.GOAL_CUSTOM)
        self._goal_combo.setToolTip(
            "Pick what you want this rip to be and the format, verification and "
            "effort options below snap to good values for it. 'Fast Verified' "
            "(recommended): FLAC, AccurateRip + CTDB, and a track is re-read only "
            "when it fails to verify (one frame matching is not verifying) — one "
            "fast pass on a clean disc. 'Archival': the same, plus EAC-style Test "
            "and Copy (EVERY track read until two reads agree) — slower, and the "
            "most reproducible result. 'Portable': MP3 derived from a "
            "fully verified FLAC master, which is still kept. Changing any option "
            "below switches this to Custom; nothing is lost when it does."
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
        self._output_dir_edit.setToolTip(
            "Where finished rips are written. Each album lands in its own "
            "folder here, built from the naming template below."
        )
        form.addRow("Output directory:", output_row)

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
        self._naming_combo.setToolTip(
            "A shortcut that fills the two template boxes below — it stores "
            "nothing of its own, so whatever it writes there is what a rip "
            "uses. Each choice names the folder layout it produces: the "
            "recommended one gives Artist/Album/01 - Title, the year presets "
            "put the year in the FOLDER (Album (1995)) rather than in every "
            "filename, and the compilation preset adds the per-track artist "
            "for discs where it differs from the album artist. Watch the "
            "Example line below — it renders the real filename. Hand-editing "
            "either template switches this to Custom and changes nothing else."
        )
        form.addRow("Naming scheme:", self._naming_combo)

        self._track_template_edit: QLineEdit = QLineEdit(config.track_template, self)
        self._track_template_edit.setToolTip(
            "Path for identified discs. Codes: %A artist, %d album, "
            "%t track #, %n title, %a track artist, %y date, %Y year (4-digit).\n"
            "Pick a preset above, or hand-edit here."
        )
        form.addRow("Track template:", self._track_template_edit)

        self._disc_template_edit: QLineEdit = QLineEdit(config.disc_template, self)
        self._disc_template_edit.setToolTip(
            "Folder path for the rip's .log and .cue on identified discs. Same "
            "codes as the track template above."
        )
        form.addRow("Disc template (.log/.cue):", self._disc_template_edit)

        # Live preview: the selected template rendered against a metadata-heavy
        # sample (colon in the title, a featured/per-track artist) so the user
        # sees how it copes with the awkward cases before committing. Updates as
        # the preset or the template text changes.
        self._naming_preview: QLabel = QLabel("", self)
        self._naming_preview.setWordWrap(True)
        self._naming_preview.setAccessibleName("Filename preview")
        # Quieter than the fields, but in the TEXT colour. `palette(mid)` is a
        # bevel-shading colour and measured ~1.1:1 on Breeze Dark — the dim line
        # the maintainer reported (2026-09-23).
        self._naming_preview.setStyleSheet(SECONDARY_STYLE)
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
        self._track_template_unknown_edit.setToolTip(
            "Track path used when a disc isn't identified (File → Rip as Unknown "
            "Album). Uses the literal 'Unknown Album' names, never a disc-ID hash."
        )
        form.addRow("Track template (unknown):", self._track_template_unknown_edit)

        self._disc_template_unknown_edit: QLineEdit = QLineEdit(
            config.disc_template_unknown, self
        )
        self._disc_template_unknown_edit.setToolTip(
            "Folder path for the .log/.cue of an unidentified disc "
            "(File → Rip as Unknown Album)."
        )
        form.addRow("Disc template (unknown):", self._disc_template_unknown_edit)

        # --- Read offset: SHOWN here, edited in the drive wizard ---
        # A rip depends on it, so Settings says what it is — but it has one home,
        # the drive wizard, and a second editor here is how an OK once wrote a
        # stale offset over one the wizard had just saved (`apply_user_edits`).
        # Read-only text, so there is nothing here a scroll or a click can change.
        applied = offset_config.describe_applied_offset(
            config.read_offset, config.override_read_offset
        )
        self._offset_status_label: QLabel = QLabel(
            f"{applied}\nSet it in {WINDOW_PATHS[DRIVE_SETUP]}", self
        )
        self._offset_status_label.setTextFormat(Qt.TextFormat.PlainText)
        self._offset_status_label.setWordWrap(True)
        self._offset_status_label.setAccessibleName("Read offset")
        self._offset_status_label.setToolTip(
            "Your drive's read offset, in samples (cyanrip's -s). It is a "
            "property of the DRIVE, not of the disc, so it is set once, in the "
            "drive wizard, where it can be looked up from the AccurateRip drive "
            "list. Shown here because every rip depends on it."
        )
        form.addRow("Read offset:", self._offset_status_label)

        # --- Tool paths ---
        self._metaflac_path_edit, metaflac_row = self._build_file_row(
            config.metaflac_path, "metaflac path"
        )
        self._metaflac_path_edit.setToolTip(
            "Path to the 'metaflac' tool used to adjust FLAC tags after a rip. "
            "Leave as 'metaflac' to use the host-exported command on your PATH "
            "(the normal case). Advanced."
        )
        form.addRow("metaflac path:", metaflac_row)

        # --- Output format ---
        # Every rip produces FLAC (the lossless master); a non-FLAC choice is
        # derived afterwards by a post-rip ffmpeg transcode, with the FLAC kept.
        # Item data is the raw config value.
        self._format_combo: QComboBox = QComboBox(self)
        for label, value in (
            ("FLAC — Lossless Archival Master [Recommended]", "flac"),
            ("WavPack (.wv) — Lossless, Keeps Tags and Cover Art", "wavpack"),
            ("MP3 — Lossy, Best-Quality VBR, Keeps Tags and Cover Art", "mp3"),
            ("WAV — Raw PCM, No Tags or Cover Art", "wav"),
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
            # It does NOT launch anything on its own: the only path to Picard is
            # the Unknown Album dialog, which you open deliberately. This setting
            # is that dialog's checkbox default. The old wording read as automatic
            # and cost a reviewer a check of whether it could fire mid-run.
            "Tick \u201claunch Picard\u201d by default on unknown discs",
            self,
        )
        self._auto_picard_check.setChecked(config.auto_launch_picard)
        self._auto_picard_check.setToolTip(
            "This launches nothing on its own. It sets the default state of the "
            "'open in Picard' checkbox inside the Rip as Unknown Album dialog, "
            "which you open deliberately. ON: that box starts ticked, so accepting "
            "the dialog opens Picard after the rip. OFF (default): it starts "
            "unticked and Picard is never opened unless you tick it there."
        )
        form.addRow("Picard integration:", self._auto_picard_check)

        # Auto-eject the disc when a rip finishes successfully. Convenience
        # only — the manual Eject button next to the drive picker works
        # regardless of this toggle.
        self._auto_eject_check: QCheckBox = QCheckBox(
            "Eject the disc after a successful rip", self
        )
        self._auto_eject_check.setChecked(config.auto_eject_after_rip)
        self._auto_eject_check.setToolTip(
            "ON: the tray opens as soon as a rip finishes successfully. OFF "
            "(default): the disc stays in, which is what you want when ripping "
            "several discs in a row or re-reading one. A failed or cancelled rip "
            "never ejects either way."
        )
        form.addRow("After rip:", self._auto_eject_check)

        # Desktop notification when a rip finishes — so an unattended rip alerts
        # you even when Platterpus isn't the focused window. On by default.
        self._notify_check: QCheckBox = QCheckBox(
            "Show a desktop notification when a rip finishes", self
        )
        self._notify_check.setChecked(config.notify_on_completion)
        self._notify_check.setToolTip(
            "ON: a desktop notification appears when a rip finishes or fails, so "
            "you need not watch the window. OFF: no notification — the window is "
            "the only place the result appears. A rip you cancel yourself is "
            "never announced either way."
        )
        form.addRow("", self._notify_check)

        # Debug logging — verbose log file for bug reports. Off by default;
        # testers turn it on, reproduce the issue, then attach the log.
        self._debug_logging_check: QCheckBox = QCheckBox(
            "Debug logging (verbose log for bug reports)", self
        )
        self._debug_logging_check.setChecked(config.debug_logging)
        # The REAL log path, resolved through `paths.LOG_PATH` rather than the
        # `~/.local/share/...` literal this used to name. That literal is wrong under
        # a custom `XDG_DATA_HOME` or a sandbox, and this tooltip's whole job is to
        # tell a user which file to attach to a bug report — naming a path they do
        # not have is worse than naming none, because they conclude it is missing.
        self._debug_logging_check.setToolTip(
            f"ON: every probe, command and parse step is recorded to the log file "
            f"at\n{LOG_PATH} — turn this on, reproduce the problem, then attach "
            "that file to a bug report. OFF (default): only notable events are "
            "logged, which keeps the file small but usually will not contain "
            "enough to diagnose a failure after the fact."
        )
        form.addRow("Logging:", self._debug_logging_check)

        # --- EAC bit-perfect parity gaps (KDD-13) ---
        # Cover art: "" = don't fetch. With cyanrip the GUI fetches the front
        # cover from the Cover Art Archive after the rip and embeds it.
        self._cover_art_combo: QComboBox = QComboBox(self)
        for label, value in (
            ("Don't Fetch — No Cover Art at All", ""),
            ("Embed in FLAC — Art Inside Each Track", "embed"),
            ("Save as File — Art Beside the Tracks", "file"),
            ("Embed and Save File — Both [Recommended]", "complete"),
        ):
            self._cover_art_combo.addItem(label, value)
        cover_index = self._cover_art_combo.findData(config.cover_art)
        self._cover_art_combo.setCurrentIndex(cover_index if cover_index >= 0 else 0)
        self._cover_art_combo.setToolTip(
            "What to do with the front cover, fetched from the Cover Art Archive "
            "once the rip finishes. 'Embed in FLAC': the image is written inside "
            "each track, so it travels with the file and most players show it — "
            "this is what EAC does by default. 'Save as File': cover.jpg is "
            "written beside the tracks and the audio files carry no image, which "
            "suits players that read a folder image. 'Embed and Save File' "
            "(recommended): both, so neither kind of player misses it. Nothing is "
            "fetched if the release has no art in the archive."
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
            "ON: any back cover and booklet scans the Cover Art Archive holds are "
            "saved beside the audio (back.jpg, booklet-NN.jpg) as well as the "
            "front cover. OFF: only the front cover is fetched. These extra images "
            "cannot be embedded in FLAC so they are always files on disk, and this "
            "setting does nothing when cover art is off above."
        )
        form.addRow("", self._additional_art_check)

        self._max_retries_spin: QSpinBox = QSpinBox(self)
        self._max_retries_spin.setRange(
            settings_validation.MAX_RETRIES_MIN, settings_validation.MAX_RETRIES_MAX
        )
        self._max_retries_spin.setValue(config.max_retries)
        self._max_retries_spin.setToolTip(
            "How many times the ripper re-attempts a track it cannot read cleanly "
            "before giving up on it (cyanrip's -r). This is the CEILING on "
            "attempts — not the same as 'Reads that must agree' below, which is "
            "how many must match. 0: no retries, a bad sector fails the track at "
            "once. 5 (default): a good balance. Higher can recover a scratched "
            "disc, but a badly damaged track then takes much longer to give up."
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
        # Secure re-rip effort: **how many reads must AGREE** before a track that
        # did not match AccurateRip is trusted. Ripping is always "dynamic" — a
        # track that matches the database on its first read is kept as-is; only an
        # unproven track is re-read, until this many reads match.
        #
        # **This comment said "the MAX number of reads" and "a ceiling", and both
        # were wrong** (corrected 2026-09-21). The fork's provider contract defines
        # the flag as `--repeat-rips`, *"rip tracks until checksums match N
        # times"*; the ceiling is `-r`. Four places, one fact, corrected together.
        self._secure_rerip_spin: QSpinBox = QSpinBox(self)
        self._secure_rerip_spin.setRange(
            settings_validation.SECURE_REREP_MIN, settings_validation.SECURE_REREP_MAX
        )
        self._secure_rerip_spin.setValue(config.secure_rerip_matches)
        self._secure_rerip_spin.setSpecialValueText("Off")  # shown when value is 0
        # **This is an AGREEMENT COUNT, not a ceiling, and the label said ceiling.**
        # The fork's own provider contract defines the flag as `-Z` /
        # `--repeat-rips`: *"Rip tracks until checksums match N times."* The ceiling
        # is `-r` (Max retries) — which is why cyanrip prints "no matches found, but
        # hit repeat limit of 5" when it gives up. Saying "Max reads" here put two
        # rows on one screen that read as contradicting each other ("Max retries: 5"
        # directly above "Max reads…: 2"), and the tooltip made it worse by asserting
        # "the number you pick is the ceiling". Our own `docs/dependency-contracts.md`
        # was the origin of the wrong gloss and is corrected in the same change.
        self._secure_rerip_spin.setToolTip(
            "How many reads of a track must AGREE before Platterpus trusts it "
            "(cyanrip's -Z). It rips the disc once at full speed and re-reads only "
            "a track that didn't verify against AccurateRip, until this many reads "
            "match. This is NOT a limit on how many reads it may take — that is "
            "'Max retries' above. 2 is a good value; 0 (Off) accepts the fast read "
            "even when it can't be verified. Clean, in-database discs finish in one "
            "fast pass either way."
        )
        form.addRow("Reads that must agree to trust a track:", self._secure_rerip_spin)

        # Re-read "partially accurate" tracks too (on by default since the release
        # after 0.6.56): only one frame of them matched, so the match is not
        # accepted on the fast read and they get the same secure re-read as an
        # AccurateRip miss. Unticked restores the old fast path.
        self._rerip_offset_variant_check: QCheckBox = QCheckBox(
            "Also re-read tracks where only one frame matched AccurateRip", self
        )
        self._rerip_offset_variant_check.setChecked(config.rerip_offset_variant)
        self._rerip_offset_variant_check.setToolTip(
            "On by default. A 'partially accurate' match checks only one frame "
            "of the track (frame 450), so it does NOT prove the read is right — a "
            "wrong read has passed it. When on, those tracks get the same secure "
            "re-read (cyanrip's -Z) as an AccurateRip miss, until reads agree, so "
            "the result is stable and repeatable. Costs extra time on discs where "
            "it happens. When off, the match is accepted on the first read."
        )
        form.addRow("", self._rerip_offset_variant_check)

        # EAC-style Test & Copy: read EVERY track (at least) twice and confirm
        # the two reads agree, not just the marginal ones. Checked flips the
        # dynamic fast-path OFF (secure_rerip_dynamic=False) so `-Z` runs on the
        # whole disc; unchecked is the default fast path (verify only tracks that
        # didn't match AccurateRip). The converged CRC appears as a Test/Copy CRC
        # pair in the EAC-compatible log (KDD-30).
        self._verify_every_track_check: QCheckBox = QCheckBox(
            "Verify every track with a second read (EAC-style Test && Copy)", self
        )
        self._verify_every_track_check.setChecked(not config.secure_rerip_dynamic)
        self._verify_every_track_check.setToolTip(
            "Off by default. Normally Platterpus rips fast and only re-reads a "
            "track that didn't match AccurateRip. When on, EVERY track is read at "
            "least twice and kept only once the reads agree — EAC's Test & Copy "
            "guarantee for the whole disc, shown as a matching Test/Copy CRC pair "
            "in the EAC-compatible log. Needs “Reads that must agree” at 2 or more (a second "
            "read is what there is to compare). Slower — it double-reads clean "
            "tracks too; leave off for the fast path."
        )
        form.addRow("", self._verify_every_track_check)

        # --- Adaptive read-speed ladder (headline, 0.4.6) ---
        # "Adaptive ladder" (default): rip fast, and only if a disc reads with
        # errors, re-rip it slower (and, at the floor, harder). "Fixed speed"
        # disables the ladder and always rips at the chosen speed. The fixed
        # spinner is enabled only in Fixed mode.
        self._read_speed_mode_combo: QComboBox = QComboBox(self)
        self._read_speed_mode_combo.addItem(
            "Adaptive Ladder — Fast, Slower Only if a Disc Needs It [Recommended]",
            "auto_ladder",
        )
        self._read_speed_mode_combo.addItem(
            "Fixed Speed — Always the Speed Set Below [Advanced]", "fixed"
        )
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
            "'verified'. ON (default): every rip is checked against CTDB, which "
            "sends the disc's table of contents over the network. OFF: no CTDB "
            "lookup and nothing leaves your machine; AccurateRip still runs, so "
            "the rip is still verified, by one path instead of two."
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
            "ON (default): after a successful rip every FLAC is decoded with "
            "`flac --test` to confirm it matches its stored checksum, catching "
            "encode or disk corruption. Runs in the background and only speaks up "
            "if a file fails. OFF: the files are written and never read back, so "
            "a corrupt master would not be noticed here. Needs `flac`; if it is "
            "missing the check reports as not run, never as a failure."
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
            "ON: a second, EAC-layout text log is written beside the audio (as "
            "'… (EAC-compatible).log') in addition to Platterpus's own log, so "
            "you can diff it against a real EAC log or keep a familiar-looking "
            "record. OFF (default): only Platterpus's own log is written. The "
            "EAC-layout file is clearly marked as generated by Platterpus and is "
            "never a signed EAC log — we do not forge that signature."
        )
        form.addRow("EAC-style log:", self._eac_log_check)

        # --- The form scrolls; the actions never do --------------------------
        # Measured, not guessed (2026-08-06, real hardware): this form is 35 rows
        # and its `minimumSizeHint` was **739 × 971** — meaning the dialog could
        # not be made shorter than 971 px *by any means*, because a QFormLayout's
        # minimum is the sum of its rows. On a 1080p desktop with a panel, that
        # does not fit, so Qt placed the dialog with **OK and Cancel below the
        # bottom of the screen** and there was no way to reach them. The
        # `CenteredDialog` base clamps a dialog's *position* onto the screen but
        # deliberately never resizes it (`centering._clamp_to`: "slide `frame`
        # (never resize it)"), so it could not rescue this.
        #
        # Putting the form inside a scroll area collapses that floor: the dialog's
        # minimum height becomes the scroll viewport's minimum plus the two action
        # rows, so it fits any screen and the content scrolls instead.
        #
        # **What is deliberately OUTSIDE the scroll area, and why:** the validation
        # banner and OK/Cancel. A validation error that
        # scrolled out of view would defeat the rule it exists to serve
        # (CLAUDE.md — a visible, specific error), and an OK button that can scroll
        # away is the bug this whole change is fixing, one level down.
        #
        # New state this creates (CLAUDE.md's "what does the fix itself break?"):
        # the form's widgets are now nested inside a viewport rather than being
        # direct children of the dialog. Every one is still reachable as
        # `dialog._x` — which the tests and the Qt signal wiring depend on — and
        # `tests/test_ui_settings_dialog.py` asserts exactly that alongside the
        # constrained-size checks, because "it still looks right at its natural
        # size" is not a test of a scroll area (docs/testing.md §5.v).
        form_host = QWidget(self)
        form_host.setLayout(form)
        self._form_scroll: QScrollArea = QScrollArea(self)
        self._form_scroll.setWidget(form_host)
        # Without this the inner widget keeps its own size and the scroll area
        # shows it at a fixed width, which reintroduces horizontal clipping.
        self._form_scroll.setWidgetResizable(True)
        # No sunken border: a framed box inside a dialog reads as a nested panel,
        # and this is meant to be invisible when everything fits.
        self._form_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._form_scroll.setAccessibleName("Settings")
        root.addWidget(self._form_scroll, stretch=1)

        # A scroll gesture must never change a value. Qt's default is that a
        # spin box or combo under the pointer eats the wheel and increments
        # ITSELF, so scrolling this page past a control silently edits it — the
        # maintainer hit exactly that (2026-08-13). Here it is a data-integrity
        # defect, not an annoyance: a nudged read offset or `-Z` count rips the
        # NEXT disc wrong and looks completely normal doing it. The guard is
        # retained on `self` because an event filter whose last Python reference
        # is dropped stops filtering, silently.
        self._wheel_guard: WheelGuard = protect_value_widgets(form_host)

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
            self._library_dir_edit,
            self._track_template_unknown_edit,
            self._disc_template_unknown_edit,
            self._metaflac_path_edit,
        ):
            edit.textChanged.connect(self._revalidate)

        # --- Goal preset wiring (after all dependent widgets exist) ---
        self._wire_goal_presets()

        # --- OK / Apply / Cancel / Restore Defaults ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.RestoreDefaults
            | QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self._apply_button: QPushButton | None = button_box.button(
            QDialogButtonBox.StandardButton.Apply
        )
        if self._apply_button is not None:
            self._apply_button.clicked.connect(self._on_apply_clicked)
            self._apply_button.setToolTip(
                "Save what you changed and keep Settings open."
            )
        self._restore_button: QPushButton | None = button_box.button(
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        if self._restore_button is not None:
            self._restore_button.clicked.connect(self.restore_defaults)
            self._restore_button.setToolTip(
                "Put every control in this window back to the shipped default. "
                "Nothing is saved until you press OK or Apply, and settings kept "
                "elsewhere (the read offset, update channels, test script) are "
                "not touched."
            )
        root.addWidget(button_box)
        # Apply is enabled only while there is something to apply, which is how a
        # user can tell an Apply has taken. Every control this dialog owns reports
        # a change here, found through the home table rather than listed again.
        self._wire_change_tracking()

        # Validate the incoming config once so a hand-edited/invalid config.toml
        # surfaces its errors the moment Settings opens, not only on save.
        self._revalidate()

        # Open at the size the content wants, but never larger than the screen.
        # The scroll area above makes a *smaller* dialog possible; this is what
        # makes it actually happen, because Qt's default is the size hint and the
        # size hint is still the full 35-row form.
        self.resize(self._opening_size())

    # --- Sizing --------------------------------------------------------------

    #: Kept clear of the panel/taskbar and the window frame. `availableGeometry`
    #: already excludes reserved struts on most desktops, but not the frame Qt
    #: adds around the dialog itself, and a dialog whose OK button sits exactly on
    #: the screen edge is the same defect in a milder form.
    _SCREEN_MARGIN_PX: int = 64

    def _opening_size(self) -> QSize:
        """The content's preferred size, clamped to the usable screen.

        **Measured off the form, not off `self.sizeHint()`** — and that is the
        whole subtlety of adding a scroll area. A `QScrollArea` reports a small,
        arbitrary hint of its own (526 × 414 here) because it is *designed* to be
        smaller than its content, so a dialog sized from `self.sizeHint()` opened
        showing about a third of the form: fewer options visible, not more, which
        is the complaint inverted rather than fixed. The preferred size is the
        inner form's hint plus the chrome we deliberately kept outside it.

        Pure enough to test: it reads the screen through
        :meth:`available_screen_size`, which a test overrides. Returning a size
        rather than calling ``resize`` keeps the arithmetic assertable without a
        display — the lesson from the window-default fix, where CI's 800 × 800
        virtual screen made two different defaults measure identically
        (`docs/testing.md` §5.v).
        """
        # `QScrollArea.widget()` is typed `QWidget | None`. We set it in
        # `__init__` so it is never None in practice — but a sizing routine
        # that assumes that would crash the dialog open, so fall back to the
        # dialog's own hint instead of asserting.
        inner = self._form_scroll.widget()
        content = inner.sizeHint() if inner is not None else self.sizeHint()
        chrome = self.sizeHint() - self._form_scroll.sizeHint()
        # A vertical scrollbar steals width from the viewport; reserving it up
        # front is what stops the *horizontal* bar appearing the moment the
        # dialog is one pixel too short.
        bar = self._form_scroll.verticalScrollBar()
        wanted = QSize(
            content.width() + chrome.width() + bar.sizeHint().width(),
            content.height() + chrome.height(),
        )
        avail = self.available_screen_size()
        return QSize(
            min(wanted.width(), max(avail.width() - self._SCREEN_MARGIN_PX, 320)),
            min(wanted.height(), max(avail.height() - self._SCREEN_MARGIN_PX, 240)),
        )

    def available_screen_size(self) -> QSize:
        """Usable screen area, or a conservative fallback when there is none.

        Split out so a test can constrain it. The fallback is deliberately small
        rather than large: guessing *big* on a headless or odd-screen host would
        reproduce the very bug this fixes, and a dialog that opens smaller than it
        needed to is merely scrollable.
        """
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return QSize(1024, 720)
        return screen.availableGeometry().size()

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 — Qt override
        """Re-clamp on show, because the screen is not knowable in ``__init__``.

        A dialog constructed before it has been assigned to a screen reports the
        primary screen's geometry; on a multi-monitor desktop the parent window
        may be on a *different*, smaller one, and the base class moves us there
        during this same event. Clamping again here — and only ever shrinking —
        means the size matches the screen we actually land on.
        """
        super().showEvent(event)
        clamped = self._opening_size()
        if clamped.width() < self.width() or clamped.height() < self.height():
            self.resize(
                min(self.width(), clamped.width()),
                min(self.height(), clamped.height()),
            )

    # --- Public surface -----------------------------------------------------

    def user_edits_applied_to(self, current: Config) -> Config:
        """The config to save: ``current`` plus only what the user changed here.

        The caller passes its live config rather than the one this dialog was
        opened with, because that object may have moved on while the dialog was
        up — see :func:`apply_user_edits`.
        """
        return apply_user_edits(current, self._opened_with, self.to_config())

    def to_config(self) -> Config:
        """The config the dialog would save: what it opened with, plus its widgets.

        Every field this dialog edits is read off its widget
        (:meth:`widget_values`); every other field — the app's own bookkeeping,
        and each setting homed in another window — is the value it opened with.
        Built on the snapshot rather than the live config so a field edited
        elsewhere while this was open can never look like an edit made here.
        """
        return with_values(self._opened_with, self.widget_values())

    def widget_values(self) -> dict[str, object]:
        """``{field: value}`` for exactly the settings this dialog edits.

        ``tests/test_setting_homes.py`` holds the key set to
        ``fields_homed_in(SETTINGS)``, so this and the home table cannot drift.
        """
        return {
            "output_dir": self._output_dir_edit.text(),
            "library_dir": self._library_dir_edit.text(),
            "track_template": self._track_template_edit.text(),
            "disc_template": self._disc_template_edit.text(),
            "track_template_unknown": self._track_template_unknown_edit.text(),
            "disc_template_unknown": self._disc_template_unknown_edit.text(),
            "metaflac_path": self._metaflac_path_edit.text(),
            "auto_launch_picard": self._auto_picard_check.isChecked(),
            "auto_eject_after_rip": self._auto_eject_check.isChecked(),
            "notify_on_completion": self._notify_check.isChecked(),
            "debug_logging": self._debug_logging_check.isChecked(),
            "cover_art": self._cover_art_combo.currentData(),
            "max_retries": self._max_retries_spin.value(),
            "force_overread": self._force_overread_check.isChecked(),
            "secure_rerip_matches": self._secure_rerip_spin.value(),
            # Checked = verify every track (whole-disc Test & Copy) = dynamic OFF.
            "secure_rerip_dynamic": not self._verify_every_track_check.isChecked(),
            "rerip_offset_variant": self._rerip_offset_variant_check.isChecked(),
            "read_speed_mode": self._read_speed_mode_combo.currentData(),
            "read_speed": self._read_speed_spin.value(),
            "ctdb_verify_after_rip": self._ctdb_verify_check.isChecked(),
            "verify_flac_after_rip": self._verify_flac_check.isChecked(),
            "recompress_flac_after_rip": self._recompress_flac_check.isChecked(),
            "write_eac_log_after_rip": self._eac_log_check.isChecked(),
            "save_additional_art": self._additional_art_check.isChecked(),
            "output_format": self._format_combo.currentData(),
            "rip_goal": self._goal_combo.currentData(),
            "mp3_vbr_quality": self._mp3_quality_spin.value(),
        }

    def has_unapplied_edits(self) -> bool:
        """Whether any control differs from what was last opened or applied."""
        return self.to_config() != self._opened_with

    def mark_applied(self) -> None:
        """Make the current widget state the new baseline, after a save.

        Called by the window once it has saved an Apply. From here on, OK and a
        second Apply write only what changes AFTER this point, and Cancel keeps
        what was applied — the KDE meaning of Cancel after Apply.
        """
        self._opened_with = self.to_config()
        self._update_apply_enabled()

    def restore_defaults(self) -> None:
        """Reset this dialog's controls to the shipped defaults. Saves nothing.

        Only the settings homed HERE: the read offset, the channels and the test
        script keep their values, because they are not this window's to reset.
        """
        log.info("settings: restore defaults pressed")
        self._load_widgets(Config())
        self._revalidate()

    def _load_widgets(self, source: Config) -> None:
        """Set every control this dialog owns from ``source``.

        Driven by the home table, so a new Settings control is reset along with
        the rest the day it is added. The goal combo is set LAST and quietly: it
        describes the values above it rather than imposing its preset on them.
        """
        self._applying_preset = True
        try:
            for field in sorted(fields_homed_in(SETTINGS) - {"rip_goal"}):
                widget = getattr(self, SETTING_HOMES[field].control)
                value = getattr(source, field)
                if field == "secure_rerip_dynamic":
                    value = not value  # the box reads "verify every track"
                _set_widget_value(widget, value)
        finally:
            self._applying_preset = False
        goal_index = self._goal_combo.findData(goal_presets.detect_goal(source))
        self._goal_combo.blockSignals(True)
        self._goal_combo.setCurrentIndex(goal_index if goal_index >= 0 else 0)
        self._goal_combo.blockSignals(False)
        self._sync_naming_combo_to_templates()
        self._refresh_naming_preview()
        self._update_apply_enabled()

    def _wire_change_tracking(self) -> None:
        """Re-evaluate Apply whenever any control this dialog owns changes."""
        for field in fields_homed_in(SETTINGS):
            widget = getattr(self, SETTING_HOMES[field].control)
            if isinstance(widget, QCheckBox):
                widget.toggled.connect(self._update_apply_enabled)
            elif isinstance(widget, QSpinBox):
                widget.valueChanged.connect(self._update_apply_enabled)
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self._update_apply_enabled)
            elif isinstance(widget, QLineEdit):
                widget.textChanged.connect(self._update_apply_enabled)
        self._update_apply_enabled()

    def _update_apply_enabled(self) -> None:
        if self._apply_button is not None:
            self._apply_button.setEnabled(self.has_unapplied_edits())

    def _on_apply_clicked(self) -> None:
        """Apply: the same refusal as OK, then ask the window to save."""
        if self._blocking_issues():
            return
        self.apply_requested.emit()

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
        if self._blocking_issues():
            return  # keep the dialog open until the errors are fixed
        super().accept()

    def _own_issues(self) -> list[ValidationIssue]:
        """Validation issues for the settings THIS dialog edits.

        A problem with a setting homed elsewhere (a startup script that has
        since been deleted, say) is not shown here and does not block OK: the
        user cannot fix it in this window, and a dialog that refused to save
        over something it does not display would be a trap. Its own window
        validates it where it is edited.
        """
        owned = fields_homed_in(SETTINGS)
        return [
            issue
            for issue in settings_validation.validate_config(self.to_config())
            if issue.field in owned
        ]

    def _blocking_issues(self) -> bool:
        """Show and log any hard error; True when saving must be refused."""
        issues = self._own_issues()
        if settings_validation.errors_only(issues):
            settings_validation.log_issues(issues)
            self._render_validation(issues)
            return True
        return False

    def _revalidate(self) -> None:
        """Validate the current widget state and show any issues inline. Cheap
        enough to run on every keystroke (a pure function + a couple of stat
        calls), which is what makes the error visible *during* the change."""
        self._render_validation(self._own_issues())

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
                colour = status_colour(
                    "error" if issue.is_error() else "warn", field_widget.palette()
                )
                field_widget.setStyleSheet(f"border: 1px solid {colour};")
        lines = [f"✖ {i.message}" for i in errors] + [
            f"⚠ {i.message}" for i in warnings
        ]
        banner_text = "\n".join(lines)
        self._validation_label.setText(banner_text)
        self._validation_label.setStyleSheet(
            status_style("error" if errors else "warn", self._validation_label)
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
    #
    # `_wire_goal_presets` below is the SINGLE list of the controls a goal preset
    # drives. There used to be a second one here — a `_goal_driven_widgets()`
    # accessor, commented "the controls a goal preset drives", called from nowhere
    # and already out of date: it named five of the six, omitting
    # `_verify_flac_check`. That is the same omission the comment inside
    # `_wire_goal_presets` records as a shipped bug, preserved in a method that
    # read as the authoritative roster. Removed 2026-07-31 rather than repaired,
    # because a second list is the drift; `test_goal_presets` now asserts the
    # wiring covers every `GoalPreset` field, which is what catches the next one.

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
        # Same omission in the other direction: editing this box by hand did not
        # flip the combo to Custom, so the label kept claiming a preset the
        # config no longer matched.
        self._verify_flac_check.toggled.connect(self._on_dependent_changed)
        self._secure_rerip_spin.valueChanged.connect(self._on_dependent_changed)
        # The two controls that make "Archival Exact" a different rip from "Fast
        # Verified" rather than a different name for it (2026-08-24). Until the
        # preset carried them, the archival goal was byte-identical to the fast
        # one and its label promised smaller files it could not produce.
        self._verify_every_track_check.toggled.connect(self._on_dependent_changed)
        self._rerip_offset_variant_check.toggled.connect(self._on_dependent_changed)
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
            # `verify_flac_after_rip` is one of the SIX fields a preset defines
            # and `goal_presets.detect_goal` compares — but it was the one this
            # handler never set. Picking "Archival Exact" therefore left it
            # untouched, and the next time Settings opened, detect_goal saw a
            # config that didn't match any preset and silently reported
            # "Custom" (audit, 2026-07-28). The list here must stay in step with
            # GoalPreset's fields; that is why the dead `apply_preset` existed.
            self._verify_flac_check.setChecked(preset.verify_flac_after_rip)
            self._recompress_flac_check.setChecked(preset.recompress_flac_after_rip)
            self._secure_rerip_spin.setValue(preset.secure_rerip_matches)
            # The checkbox is the INVERSE of the field: ticked means "verify every
            # track", which is `secure_rerip_dynamic=False`. Getting this backwards
            # would make picking Archival Exact silently select the fast path.
            self._verify_every_track_check.setChecked(not preset.secure_rerip_dynamic)
            self._rerip_offset_variant_check.setChecked(preset.rerip_offset_variant)
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


def _set_widget_value(widget: QWidget, value: object) -> None:
    """Put ``value`` into a value control, whatever kind it is.

    A combo is matched on its item DATA (the stored config value), never on its
    label; a value no item carries leaves the combo where it is and is logged,
    rather than silently selecting row 0.
    """
    if isinstance(widget, QCheckBox):
        widget.setChecked(bool(value))
    elif isinstance(widget, QSpinBox):
        widget.setValue(int(value))  # type: ignore[call-overload]  # an int field, by the home table
    elif isinstance(widget, QComboBox):
        index = widget.findData(value)
        if index >= 0:
            widget.setCurrentIndex(index)
        else:
            log.warning("settings: no option carries %r; left as it was", value)
    elif isinstance(widget, QLineEdit):
        widget.setText(str(value))
    else:
        log.error("settings: cannot set a %s", type(widget).__name__)
