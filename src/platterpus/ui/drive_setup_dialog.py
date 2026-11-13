"""Drive setup wizard — one-click calibration of the optical drive.

Replaces the manual hand-edit of a config file (the worst first-run step) with a
guided flow. The read offset (what makes a rip bit-perfect) comes from the
bundled AccurateRip drive-model list — pre-filled and saved in one click when the
drive is recognised — or is entered by hand. The main window persists it as
Platterpus's `--offset` override (the backend writes no config file of its own).

Backends that can genuinely MEASURE an offset from a disc
(``RipBackend.supports_offset_detection()``) additionally get a "Detect" button
that runs off the GUI thread via ``DriveSetupWorker``. **cyanrip's finder is
deliberately not used** — its ``-f`` IS a "find drive offset" mode (verified
against 0.9.3.1 + master, 2026-07-21), but the earlier integration mis-scraped
its output (read a default 0 and silently overrode the correct list value) and
was removed — so the button is hidden for it rather than offering a probe we
don't trust. The ``DriveSetupWorker``/detection seam remains for a future
measuring backend (or a re-vetted ``-f`` integration).

**This is the read offset's ONE home** (2026-09-24). Settings used to carry a
second copy — a spin box and the "Apply" tick-box — and two editors of one
calibration value is how an OK in Settings once wrote a stale offset over the one
this wizard had just saved. Settings now shows the offset read-only and names
this window; `ui/setting_homes.py` records the placement and
`tests/test_setting_homes.py` refuses a second editor anywhere else.

**The cache check runs by itself, once per drive** (TASKS R53, the owner's rule
of 2026-11-12: drive properties are tested once, up front, and saved per drive).
When the window opens for a drive whose profile holds no cache verdict and an
audio CD is in the drive, the same worker the *Analyze cache* button starts is
started on show, on the same thread and with the same cancel path; *Skip check*
stops it (killing ``cd-paranoia``). With no disc in, the window says the check
starts when one is inserted, and the main window tells it when a disc has been
read (`notify_disc_ready`). Whether to start is decided by the pure
`cache_check_plan.decide_auto_check`, never inline here.

The dialog owns the worker thread; `_on_finished` is a plain slot so tests can
exercise the result rendering without a live event loop.
"""

from __future__ import annotations

import html
import logging

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from platterpus import cache_check_plan
from platterpus.adapters.rip_backend import RipBackend
from platterpus.settings_validation import OFFSET_MAX, OFFSET_MIN
from platterpus.ui.accessibility import announce
from platterpus.ui.dialogs.centering import CenteredDialog
from platterpus.ui.drive_setup_auto_check import AutoCacheCheckMixin
from platterpus.ui.scroll_guards import WheelGuard, protect_value_widgets
from platterpus.workers import start_worker_thread
from platterpus.workers.drive_setup_worker import (
    DriveSetupResult,
    DriveSetupWorker,
)

log = logging.getLogger(__name__)

# Layout bounds for the content-derived minimum size (see
# `DriveSetupDialog._apply_content_derived_minimum_size`). Named rather than inline
# because each one encodes a decision, not a magic number.
#
# The results box is the dialog's ONLY scroll surface, so it is the widget allowed to
# shrink when the user makes the window smaller — enough to stay usable, no more.
_RESULTS_MIN_HEIGHT_PX: int = 60
# A floor under the width so a very short intro can't yield a comically narrow
# dialog; the measured content width is 494, so this only ever binds in odd cases.
_DIALOG_MIN_WIDTH_PX: int = 460
# A ceiling on the *minimum* height, so a long known-offset line can never demand a
# dialog taller than a modest laptop screen. Past this the results box scrolls, which
# is what it is for.
_DIALOG_MAX_MIN_HEIGHT_PX: int = 620


class DriveSetupDialog(AutoCacheCheckMixin, CenteredDialog):
    """Modal-ish dialog that calibrates one drive via the backend's commands."""

    # Emitted when the user saves a manually-entered offset (the fallback for
    # when auto-detection can't run — e.g. no AccurateRip disc to hand). The
    # main window persists it as the GUI's `--offset` override; this dialog
    # stays a view and never writes config itself.
    manual_offset_saved = Signal(int)

    # Emitted after a successful auto-detect (only reachable for a backend that
    # can measure — not cyanrip). Carries the DriveSetupResult so the main window
    # can persist the measured offset and record its provenance in the
    # drive-profile ledger. Confidence is earned by AGREEMENT with the AccurateRip
    # list (reconcile_offset), never granted to a lone reading. The dialog stays
    # a view.
    detection_recorded = Signal(object)

    # Emitted when the user ticks or unticks "Apply this read offset to every
    # rip". Applied at once, like the offset's own Save: the window writes
    # `override_read_offset` and saves, and this dialog says so in its status
    # line. A tick-box that took effect only on some later button would be a
    # change the user could believe they had made and had not.
    offset_applied_changed = Signal(bool)

    def __init__(
        self,
        backend: RipBackend,
        device: str,
        parent: QWidget | None = None,
        current_offset: int = 0,
        known_offset: int | None = None,
        drive_label: str = "",
        offset_applied: bool = True,
        cache_verdict: str | None = None,
        audio_disc_present: bool = False,
        drive_busy: bool = False,
    ) -> None:
        """`known_offset`, when provided, is the AccurateRip read offset
        looked up by drive model (the primary, disc-free path). We prefill
        the manual field with it and call it out so the user can save it in
        one click — no disc or ripper probe required. `drive_label` is the
        human drive name shown in that callout. `offset_applied` is the config's
        ``override_read_offset``: whether rips pass the offset to cyanrip at all.

        The last three feed the automatic cache check (`cache_check_plan`):
        ``cache_verdict`` is this drive's `verdict_state` (``None``, the default,
        means the caller did not say, and nothing starts by itself);
        ``audio_disc_present`` is whether an audio CD has been read in the drive;
        ``drive_busy`` is whether something else is reading it right now.
        """
        super().__init__(parent)
        self._backend: RipBackend = backend
        # Whether this backend can genuinely measure the offset from a disc. When
        # False (cyanrip), we do NOT show a "Detect" button that can only fail —
        # the offset comes from the AccurateRip drive list (pre-filled below) or
        # manual entry. Honest UI: never present a non-working path as working.
        self._can_detect: bool = backend.supports_offset_detection()
        # Whether this backend can MEASURE the drive's audio-cache behaviour
        # (cd-paranoia -A for cyanrip — KDD-29). Distinct from offset detection:
        # cyanrip can do this even though it can't auto-detect the offset, so the
        # calibration action is offered when EITHER capability is present.
        self._can_analyze: bool = backend.supports_cache_analysis()
        self._device: str = device
        self._known_offset: int | None = known_offset
        self._thread: QThread | None = None
        self._worker: DriveSetupWorker | None = None
        # Set true once the dialog is closing, so a late worker result
        # doesn't poke widgets that are being torn down.
        self._closing: bool = False
        self._init_auto_check(cache_verdict, audio_disc_present, drive_busy)

        self.setWindowTitle("Set up drive")
        # Open at a readable size (the default was cramped — labels and the
        # detection output were clipped and unscrollable). Resizable.
        #
        # The minimum is NOT set here any more. It used to be a hand-picked
        # `setMinimumSize(460, 320)`, which was 185 px shorter than the content
        # actually needs, so the dialog could be shrunk until its own explanation of
        # what a read offset *is* was clipped away. It is now derived from the laid-out
        # content at the end of `__init__` — see
        # `_apply_content_derived_minimum_size`, which explains why measuring beats
        # guessing here and why a scroll area would be the wrong fix.
        self.resize(560, 460)

        root = QVBoxLayout(self)

        if self._can_detect:
            intro_text = (
                "This calibrates your drive for bit-perfect rips. It detects the "
                "drive's read offset and audio-cache behaviour and saves the "
                "offset to Platterpus's own settings, which are applied to "
                "cyanrip on every rip.\n\n"
                "Insert a popular commercial CD — one likely to be in the "
                "AccurateRip database — then click Detect. This can take a minute."
            )
        elif self._can_analyze:
            # cyanrip: no offset finder, but we CAN measure the audio cache with
            # cd-paranoia -A (KDD-29). Offer that as its own action; the offset
            # still comes from the AccurateRip list / manual entry below.
            intro_text = (
                "The read offset is what makes a rip bit-perfect. Platterpus "
                "applies it to cyanrip on every rip; it comes from the AccurateRip "
                "drive list (pre-filled below when your drive is recognised) or "
                "you can enter it by hand.\n\n"
                "This window also measures the drive's audio-cache behaviour, which "
                "confirms re-reads reach the disc (not a stale cache). It runs by "
                "itself once per drive when an audio CD is in the drive, and the "
                "measured Yes/No is saved and recorded in the EAC-compatible log. "
                "Analyze cache runs it again."
            )
        else:
            # cyanrip can't measure the offset from a disc, so we don't pretend
            # to. The read offset — what makes a rip bit-perfect — comes from the
            # AccurateRip drive list (pre-filled below when your drive is known)
            # or is entered by hand. It's saved to Platterpus's settings and
            # applied to cyanrip on every rip.
            intro_text = (
                "The read offset is what makes a rip bit-perfect. Platterpus "
                "applies it to cyanrip on every rip.\n\n"
                "Your drive's offset comes from the AccurateRip drive list "
                "(pre-filled below when your drive is recognised) or you can "
                "enter it by hand. On-disc auto-detection isn't available with "
                "this backend."
            )
        # Every label built from a value STATES its text format: Qt's default,
        # AutoText, treats text as HTML when its first line happens to hold a
        # known tag, so the choice would depend on the value inside it (CLAUDE.md
        # Critical rule #12; tests/test_labels_state_their_text_format.py). The
        # intro is our own prose, and its blank lines survive only as PlainText.
        intro = QLabel(intro_text, self)
        intro.setTextFormat(Qt.TextFormat.PlainText)
        intro.setWordWrap(True)
        root.addWidget(intro)

        # PlainText: the device path is the system's, not ours.
        self._device_label: QLabel = QLabel(
            f"Drive: {device or '(auto-detected)'}", self
        )
        self._device_label.setTextFormat(Qt.TextFormat.PlainText)
        root.addWidget(self._device_label)

        # Primary path: if we already know this drive's offset from the
        # AccurateRip drive list (looked up by model), say so prominently —
        # the user can save it in one click below without inserting a disc.
        # This sidesteps cyanrip's disc-based offset detection entirely.
        if known_offset is not None:
            # Escaped: the name is the drive's own vendor/model string, which the
            # drive reports and we only pass on. It goes into markup below.
            name = html.escape(drive_label or "this drive")
            verify_clause = (
                " Auto-detect (Detect) is optional verification."
                if self._can_detect
                else ""
            )
            suggestion = QLabel(
                f"✓ Known read offset for {name}: <b>{known_offset:+d}</b> "
                "(from the AccurateRip drive list). It's pre-filled below — "
                'click "Save offset" to use it. No disc needed.' + verify_clause,
                self,
            )
            # RichText on purpose: the sentence, the <b>…</b> around the offset
            # (an int) and `verify_clause` are ours; the drive name is escaped
            # above. Left to AutoText, a drive named "TSST <corp>" made Qt read
            # the whole label as plain text and show the <b> tags literally.
            suggestion.setTextFormat(Qt.TextFormat.RichText)
            suggestion.setWordWrap(True)
            root.addWidget(suggestion)

        # The "Detect" action + its busy bar only exist when the backend can
        # actually measure an offset from a disc. cyanrip can't, so we don't show
        # a button that would only ever report "can't do it" — honest UI (the
        # offset comes from the AccurateRip list / manual entry below instead).
        self._detect_button: QPushButton | None = None
        self._skip_button: QPushButton | None = None
        self._progress: QProgressBar | None = None
        if self._can_detect or self._can_analyze:
            # "Detect" when there's a real offset finder (offset + cache);
            # "Analyze cache" when only the cache probe runs (cyanrip), and
            # "Re-analyze" once this drive already has a saved verdict, so the
            # button says that pressing it measures again.
            if self._can_detect:
                label = "&Detect"
            elif cache_verdict == cache_check_plan.MEASURED:
                label = "Re-analy&ze cache"
            else:
                label = "Analy&ze cache"
            action_row = QHBoxLayout()
            self._detect_button = QPushButton(label, self)
            self._detect_button.clicked.connect(self._on_detect_clicked)
            action_row.addWidget(self._detect_button, 1)
            self._skip_button = self._build_skip_button(action_row)
            root.addLayout(action_row)

            # Indeterminate (busy) bar — min==max==0 animates with no percentage,
            # honest here since the detection command reports no progress.
            self._progress = QProgressBar(self)
            self._progress.setRange(0, 0)
            self._progress.setVisible(False)
            root.addWidget(self._progress)

        self._auto_note_label = self._build_auto_note(root)

        self._status_label: QLabel = QLabel("", self)
        # PlainText: the detection worker's status and outcome lines land here,
        # and they quote the drive and the tool. Qt's default AutoText would read
        # a `<` in them as markup.
        self._status_label.setTextFormat(Qt.TextFormat.PlainText)
        self._status_label.setWordWrap(True)
        self._status_label.setAccessibleName("Drive setup status")
        root.addWidget(self._status_label)

        # Read-only, scrollable: detection output can be several lines and
        # the offset-find guidance is long, so a label clipped it.
        self._results_label: QPlainTextEdit = QPlainTextEdit("", self)
        self._results_label.setReadOnly(True)
        self._results_label.setAccessibleName("Drive setup results")
        root.addWidget(self._results_label, stretch=1)

        # --- Manual fallback ---------------------------------------------------
        # Auto-detection needs a disc that's in AccurateRip; a user with only
        # CD-Rs (or an obscure pressing) can't run it. Let them enter the
        # offset by hand — every drive model's value is published at
        # AccurateRip's list, keyed by the exact drive the GUI already shows.
        # One sentence, not two: the intro above already says the offset is saved
        # in Platterpus's settings and applied to cyanrip on every rip, and saying
        # it twice cost the line that clipped this dialog on a short screen.
        manual_intro = QLabel(
            "No AccurateRip disc handy? Look up your drive's offset at "
            '<a href="https://www.accuraterip.com/driveoffsets.htm">'
            "accuraterip.com/driveoffsets.htm</a> and enter it here.",
            self,
        )
        manual_intro.setWordWrap(True)
        manual_intro.setOpenExternalLinks(True)
        # QLabel links are mouse-only by default — LinksAccessibleByKeyboard
        # puts the label in the tab chain (Qt sets StrongFocus for it) so the
        # accuraterip.com link can be reached and opened with Tab + Enter
        # (gap #4 sweep finding: this was the one unreachable affordance here).
        manual_intro.setTextInteractionFlags(
            Qt.TextInteractionFlag.LinksAccessibleByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByKeyboard
        )
        root.addWidget(manual_intro)

        manual_row = QHBoxLayout()
        manual_row.addWidget(QLabel("Read offset (samples):", self))
        self._offset_spin: QSpinBox = QSpinBox(self)
        # The plain QLabel beside it isn't a buddy, so name the spin box for
        # screen readers explicitly.
        self._offset_spin.setAccessibleName("Read offset in samples")
        # Read the SAME bounds the pure validator enforces, rather than the
        # hardcoded ±2000 this used to carry — a widget range that disagrees
        # with the validator is a second, silently-different rule for the same
        # field (audit finding, 2026-07-28). Real AccurateRip offsets sit well
        # inside this range; the bound is a sanity cap, not a claim about drives.
        self._offset_spin.setRange(OFFSET_MIN, OFFSET_MAX)
        # Prefill with the model-looked-up offset when we have one (the
        # primary path); otherwise fall back to the currently-configured
        # value passed in.
        self._offset_spin.setValue(
            known_offset if known_offset is not None else current_offset
        )
        self._offset_spin.setToolTip(
            "Your drive's read offset, in samples, signed (cyanrip's -s). Every "
            "drive reads a fixed distance early or late; correcting for it is what "
            "makes a rip bit-perfect and lets AccurateRip match. It is a property "
            "of the DRIVE, not of the disc, so set it once. Typical values are "
            "within a few hundred of zero; 0 means no correction, right only for "
            "the rare drive that needs none. Press Save offset to use it."
        )
        manual_row.addWidget(self._offset_spin)
        self._save_offset_button: QPushButton = QPushButton("&Save offset", self)
        self._save_offset_button.clicked.connect(self._on_save_offset_clicked)
        manual_row.addWidget(self._save_offset_button)
        manual_row.addStretch(1)
        root.addLayout(manual_row)

        # Whether rips pass the offset at all (cyanrip's `-s`). Moved here from
        # Settings with the offset itself, so the number and the switch that
        # makes it count are edited in one place.
        self._apply_offset_check: QCheckBox = QCheckBox(
            "Apply this read offset to every rip", self
        )
        self._apply_offset_check.setChecked(offset_applied)
        self._apply_offset_check.setToolTip(
            "ON: every rip is corrected by the saved offset (cyanrip's -s). OFF: "
            "no -s is passed at all and the drive's raw alignment is used, which "
            "for most drives is NOT bit-perfect, so AccurateRip then fails to "
            "match even a clean disc. Saving an offset turns this on. The change "
            "takes effect as soon as you click it."
        )
        self._apply_offset_check.toggled.connect(self._on_apply_offset_toggled)
        root.addWidget(self._apply_offset_check)

        # Close only — there's no "apply" step because the offset is saved to
        # Platterpus's own config the moment detection (or a manual save)
        # succeeds, and cyanrip is fed it via -s at rip time.
        self._button_box: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, self
        )
        self._button_box.rejected.connect(self.reject)
        self._button_box.accepted.connect(self.accept)
        root.addWidget(self._button_box)

        # A scroll gesture must never change a value — and of every value widget
        # in the app, THIS is the one the rule was written for. The offset above
        # is fed straight to cyanrip as `-s`, so a wheel nudge while reading this
        # dialog rips the next disc at the wrong offset: no error, no warning, a
        # clean-looking log with every sample shifted. Installed last so the
        # sweep sees a fully-built widget tree.
        self._wheel_guard: WheelGuard = protect_value_widgets(self)

        self._root_layout: QVBoxLayout = root
        # Say now what the automatic check will do, so a window opened with no
        # disc explains itself before anything is pressed. Starting it waits for
        # the first show (`showEvent`): constructing the window must not read a
        # disc.
        initial = self._auto_check_decision()
        if initial.action != cache_check_plan.START:
            self._set_auto_note(initial.message, refit=False)
        self._apply_content_derived_minimum_size(root)

    def _apply_content_derived_minimum_size(self, root: QVBoxLayout) -> None:
        """Stop the dialog being shrunk to a size that clips its own text.

        **The measured bug (2026-07-29).** `setMinimumSize(460, 320)` above was a
        hand-picked guess, and it was too small: laid out at 438 px wide this
        dialog's content needs ~505 px of height, so anywhere below that the wrapped
        labels were clipped. At 440×300 the intro label was **73 px short** — the
        last two lines of the explanation of what a read offset *is* simply were not
        drawn. Nothing overlapped (unlike the rip pane), because `_results_label` has
        `stretch=1` and absorbed the squeeze until it had nothing left to give; after
        that the fixed labels took it.

        The cause is the same under-reporting as the rip pane (`architecture.md`
        §3.9): a word-wrapped `QLabel`'s `minimumSizeHint` height is **one line**
        while its `heightForWidth` is three or four, so the layout's own minimum is a
        large underestimate — measured 314×285 against a real need of 494×505.

        **Why a minimum size rather than a scroll area.** Wrapping the whole dialog
        in a `QScrollArea` is what the rip pane does, and here it would be the
        v0.5.15 mistake repeated: `_results_label` is a `QPlainTextEdit`, which *is*
        a scroll area, so it would become nested — and a nested scroll surface with
        nothing left to scroll swallows the wheel instead of passing it up. The rip
        pane needs a scroll area because it competes for space with a track table and
        can legitimately be tall; a modal dialog has no such pressure, so the honest
        fix is to refuse to be smaller than its content. One scroll surface
        (`_results_label`), never nested.

        `sizeHint()` is used rather than `minimumSizeHint()` precisely because it
        resolves wrapped labels at the hinted width instead of collapsing them to one
        line. `_results_label` gets a small minimum of its own so it stays the widget
        that yields when the user *shrinks* the dialog — the labels can't.
        """
        # The scroll surface is allowed to get small; the prose is not.
        self._results_label.setMinimumHeight(_RESULTS_MIN_HEIGHT_PX)
        root.activate()  # resolve heightForWidth before reading the hint
        hint = self.sizeHint()
        # Cap the height so an unusually long known-offset line can never demand a
        # dialog taller than a modest laptop screen; past the cap `_results_label`
        # (the one scroll surface) absorbs the rest, which is what it is for.
        self.setMinimumSize(
            max(hint.width(), _DIALOG_MIN_WIDTH_PX),
            min(hint.height(), _DIALOG_MAX_MIN_HEIGHT_PX),
        )

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 — Qt API
        """On the first show, start the automatic cache check if it is due."""
        super().showEvent(event)
        if not self._shown_once:
            self._shown_once = True
            self._maybe_auto_start()

    # --- Detection flow -----------------------------------------------------

    def _on_detect_clicked(self) -> None:
        """Kick off calibration on a worker thread (the button's slot)."""
        self._start_calibration()

    def _start_calibration(self) -> None:
        """Start the worker: the button's run and the automatic one alike."""
        # Only reachable when the backend can detect or analyze (the button
        # doesn't exist otherwise), but guard defensively.
        if self._detect_button is None or self._thread is not None:
            return
        self._detect_button.setEnabled(False)
        self._skip_requested = False
        if self._skip_button is not None:
            self._skip_button.setEnabled(True)
            self._skip_button.setVisible(True)
        # Lock the manual-offset controls while an OFFSET FINDER runs: editing
        # or saving an offset mid-detection would race the value the ripper is
        # about to report. A cache-only run reports no offset, so it leaves them
        # alone: the automatic check can take minutes, and the user who opened
        # this window to save an offset must still be able to. They're
        # re-enabled in `_on_finished`.
        if self._can_detect:
            self._set_manual_controls_enabled(False)
        self._results_label.clear()
        if self._progress is not None:
            self._progress.setVisible(True)
        self._status_label.setText("Starting…")

        self._worker = DriveSetupWorker(self._backend, self._device)
        self._thread = QThread(self)
        self._worker.status.connect(self._status_label.setText)
        self._worker.finished.connect(self._on_finished)
        start_worker_thread(self._worker, self._thread, self._worker.run)

    def _on_finished(self, result: DriveSetupResult) -> None:
        """Render the calibration outcome. Safe to call directly in tests."""
        # If the dialog is closing, the worker's final (likely cancelled)
        # result is irrelevant and the widgets may be on their way out —
        # don't touch them.
        if self._closing:
            return
        if self._progress is not None:
            self._progress.setVisible(False)
        if self._skip_button is not None:
            self._skip_button.setVisible(False)
        # The automatic-check line described the run that just ended.
        self._set_auto_note("")
        skipped = self._skip_requested and result.can_defeat_cache is None
        self._skip_requested = False
        if skipped:
            # The user stopped it: say so, not "Finished with issues" over the
            # killed probe's own "could not be determined".
            outcome = "Check stopped."
            summary = (
                "ⓘ The audio-cache check was stopped before it finished, so "
                "nothing was saved. It runs by itself the next time this window "
                "opens with an audio CD in the drive, or press Analyze cache to "
                "run it now."
            )
        else:
            outcome = "Done." if result.ok else "Finished with issues."
            summary = _format_result(result)
        self._status_label.setText(outcome)
        self._results_label.setPlainText(summary)
        # Detection ran for up to a minute with focus elsewhere — announce the
        # outcome + summary focus-safely (gap #4).
        announce(self._status_label, f"Drive setup: {outcome} {summary}")
        if result.can_defeat_cache is not None:
            # A verdict now exists for this drive; nothing more is due.
            self._cache_verdict = cache_check_plan.MEASURED
        if self._detect_button is not None:
            self._detect_button.setEnabled(True)
            self._detect_button.setText(
                "Re-detect" if self._can_detect else "Re-analy&ze cache"
            )
        self._set_manual_controls_enabled(True)
        self._worker = None
        self._thread = None
        # Tell the main window to persist what we measured and record it in the
        # drive profile. Fire when EITHER a read offset OR a cache verdict came
        # back — a cache-only run (cyanrip) still has a fact worth recording; only
        # a run that produced neither has nothing to persist.
        if result.offset is not None or result.can_defeat_cache is not None:
            self.detection_recorded.emit(result)

    def _set_manual_controls_enabled(self, enabled: bool) -> None:
        """Enable/disable the manual read-offset controls as a unit.

        The QSpinBox covers its own up/down arrows, so disabling it locks the
        whole numeric entry; the Save button is locked alongside it.
        """
        self._offset_spin.setEnabled(enabled)
        self._save_offset_button.setEnabled(enabled)
        self._apply_offset_check.setEnabled(enabled)

    def _on_save_offset_clicked(self) -> None:
        """Persist a hand-entered offset via the main window (--offset path)."""
        value = self._offset_spin.value()
        self.manual_offset_saved.emit(value)
        # Saving an offset turns it on (`_set_read_offset_override`), so the
        # tick-box follows without emitting a second, redundant change.
        self._apply_offset_check.blockSignals(True)
        self._apply_offset_check.setChecked(True)
        self._apply_offset_check.blockSignals(False)
        confirmation = f"Saved read offset {value:+d} — it will be used for rips."
        self._status_label.setText(confirmation)
        # The save confirmation lands in a passive label — announce it so a
        # screen-reader user hears that the click took effect (gap #4).
        announce(self._status_label, confirmation)

    def _on_apply_offset_toggled(self, applied: bool) -> None:
        """Tell the window, and say what the next rip will now do."""
        self.offset_applied_changed.emit(applied)
        confirmation = (
            "Rips will apply the saved read offset."
            if applied
            else "⚠ Rips will not apply any read offset — most drives are then "
            "not bit-perfect."
        )
        self._status_label.setText(confirmation)
        announce(self._status_label, confirmation)

    # --- Lifecycle ----------------------------------------------------------

    def _stop_detection(self) -> None:
        """Cancel a running detection and join its thread before teardown.

        Cancelling terminates the ripper subprocess, which unblocks the
        worker's run() so the QThread can quit and be waited on. Without
        this, closing mid-detection destroys a still-running QThread (Qt
        aborts the process) and leaves the ripper spinning the drive.
        """
        # cancel_setup() SIGKILLs the cd-paranoia process group so run() returns
        # promptly; stop_thread waits briefly for that and ABANDONS the thread
        # (retaining the reference — Qt has no "detach") if the kill is slow, so
        # closing the dialog never blocks the GUI thread nor destroys a
        # still-running QThread.
        #
        # This comment used to describe that kill as already happening. It was not:
        # `cancel_setup` resolved to the ABC's concrete no-op because the cyanrip
        # backend never overrode it, so this dialog closed while cd-paranoia kept
        # the disc spinning for up to 600 s. Fixed 2026-07-29 by implementing the
        # override — the comment is now true, but it was aspirational for a while,
        # which is precisely how a false promise survives review.
        from platterpus.workers import stop_thread

        stop_thread(self._thread, self._worker)
        self._worker = None
        self._thread = None

    def reject(self) -> None:  # Qt override (Close button / Esc)
        self._closing = True
        self._stop_detection()
        super().reject()

    def closeEvent(self, event: object) -> None:  # noqa: N802 — Qt API
        """Stop the worker thread cleanly if detection is still running."""
        self._closing = True
        self._stop_detection()
        super().closeEvent(event)  # type: ignore[arg-type]


def _format_result(result: DriveSetupResult) -> str:
    """Build the human-readable summary block for the dialog."""
    lines: list[str] = []

    if result.offset is not None:
        lines.append(
            f"✓ Read offset: {result.offset:+d} samples — saved to Platterpus settings."
        )
    elif result.offset_error is not None:
        # An offset finder ran and failed. (A cache-only run leaves offset_error
        # None — "not attempted" — so we omit the offset line entirely instead of
        # printing a misleading ✗ for something the user didn't ask to detect.)
        lines.append(f"✗ Read offset: {result.offset_error}")

    # NB the polarity: can_defeat_cache is "are re-reads reaching the disc?", NOT
    # "does this drive have a cache". True is the GOOD outcome and False is the
    # dangerous one. The earlier wording had these effectively inverted — it
    # greeted False ("the cache can't be defeated") with the reassuring "doesn't
    # need to read around a cache", presenting the one genuinely worrying result
    # as fine. Keep each branch saying what was actually measured.
    if result.can_defeat_cache is True:
        lines.append(
            "✓ Audio cache: re-reads reach the disc, not a stale cache — so a "
            "re-read really re-reads, which is what makes verification meaningful "
            "(measured and saved)."
        )
    elif result.can_defeat_cache is False:
        lines.append(
            "⚠ Audio cache: this drive returns CACHED audio on a re-read and the "
            "cache could not be defeated. Re-reads may not reach the disc, so a "
            "track that fails verification might not improve on a retry. "
            "AccurateRip/CTDB still prove the audio (measured and saved)."
        )
    else:
        lines.append(
            f"• Audio cache: {result.analyze_error or 'could not be determined'}"
        )

    return "\n".join(lines)
