"""The drive-setup window's automatic cache check (TASKS R53).

A mixin of `DriveSetupDialog`, split out so the dialog's own file keeps to
building the window and running the worker, and this one to the question
*should the cache check start by itself now, and what does the window say about
it?* The answer comes from the pure `cache_check_plan.decide_auto_check`; this
file only applies it: show the line, start the dialog's own worker
(`_start_calibration`, the same one *Analyze cache* starts), and stop it on
*Skip check*.

**The owner's rule of 2026-11-12:** drive properties are tested once, up front,
at drive setup, and saved per drive. The cache verdict fills the EAC-compatible
log's "Defeat audio cache" line, which log checkers mark down when it is
missing, and it used to be measured only if the user pressed the button.

Nothing here blocks the GUI thread: starting is handing the work to the
worker's thread, and stopping is the worker's ``cancel()``, which SIGKILLs the
probe's process group and returns at once (CLAUDE.md rule 9).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from platterpus import cache_check_plan
from platterpus.ui.accessibility import announce

if TYPE_CHECKING:
    from PySide6.QtCore import QThread

    from platterpus.ui.dialogs.centering import CenteredDialog
    from platterpus.workers.drive_setup_worker import DriveSetupWorker

    # mypy sees the dialog's Qt base, so `self.isVisible()` and friends resolve;
    # at run time the mixin is a plain object and adds nothing to the MRO (the
    # pattern of `main_window_shared._SeamBase`).
    _DialogBase = CenteredDialog
else:
    _DialogBase = object

log = logging.getLogger(__name__)


class AutoCacheCheckMixin(_DialogBase):
    """Starts, describes and stops the automatic cache check of one window."""

    # Set by `DriveSetupDialog.__init__`; declared here so this file type-checks
    # on its own.
    _can_analyze: bool
    _cache_verdict: str | None
    _audio_disc_present: bool
    _drive_busy: bool
    _auto_check_attempted: bool
    _skip_requested: bool
    _closing: bool
    _device: str
    _thread: QThread | None
    _worker: DriveSetupWorker | None
    _auto_note_label: QLabel
    _status_label: QLabel
    _skip_button: QPushButton | None
    _root_layout: QVBoxLayout
    _shown_once: bool

    if TYPE_CHECKING:
        # Defined on DriveSetupDialog.
        def _start_calibration(self) -> None: ...
        def _apply_content_derived_minimum_size(self, root: QVBoxLayout) -> None: ...

    def _init_auto_check(
        self, cache_verdict: str | None, audio_disc_present: bool, drive_busy: bool
    ) -> None:
        """The automatic check's inputs and its once-per-window latch.

        One automatic run per opening, so a drive that answers "inconclusive"
        every time is not read again and again while the window sits open.
        """
        self._cache_verdict = cache_verdict
        self._audio_disc_present = audio_disc_present
        self._drive_busy = drive_busy
        self._auto_check_attempted = False
        self._shown_once = False
        # True after Skip check, so the finish slot can say "stopped" rather than
        # report the killed probe's "could not be determined" as a failure.
        self._skip_requested = False

    def _build_skip_button(self, row: QHBoxLayout) -> QPushButton:
        """*Skip check*: stops a run in progress, automatic or pressed for.

        Shown only while one runs. Before it existed the only way to stop a
        ten-minute probe was to close the window: acceptable for a run the user
        started, not for one that starts by itself.
        """
        button = QPushButton("S&kip check", self)
        button.setToolTip(
            "Stop the running check. Nothing is saved; it runs by itself the "
            "next time this window opens with an audio CD in the drive."
        )
        button.clicked.connect(self._on_skip_clicked)
        button.setVisible(False)
        row.addWidget(button)
        return button

    def _build_auto_note(self, root: QVBoxLayout) -> QLabel:
        """The line that says what the automatic check is doing, and why.

        Running, waiting for a disc, or waiting for the drive. Its own label
        because the worker's status lines overwrite the status label the moment
        it starts. PlainText: our own sentence, but set later, so it states its
        format (`tests/test_labels_state_their_text_format.py`).
        """
        label = QLabel("", self)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        label.setAccessibleName("Automatic cache check")
        label.setVisible(False)
        root.addWidget(label)
        return label

    def _auto_check_decision(self) -> cache_check_plan.AutoCheckDecision:
        """What the automatic check should do right now (pure decision)."""
        return cache_check_plan.decide_auto_check(
            can_analyze=self._can_analyze,
            verdict=self._cache_verdict,
            audio_disc_present=self._audio_disc_present,
            drive_busy=self._drive_busy,
            already_attempted=self._auto_check_attempted,
        )

    def _set_auto_note(self, message: str, *, refit: bool = True) -> None:
        """Show ``message`` in the automatic-check line, or hide the line."""
        if message == self._auto_note_label.text():
            # Nothing changed, so nothing to re-measure. Refitting anyway undid
            # what `CenteredDialog` does on show (fit the window to a small
            # screen): measured by the conformance matrix, a 586 px dialog on a
            # 533 px screen, because a no-op note on show re-set the minimum.
            return
        self._auto_note_label.setText(message)
        self._auto_note_label.setVisible(bool(message))
        if refit:
            # The line's height changed; keep the minimum honest so the prose
            # is never clipped (`_apply_content_derived_minimum_size`).
            self._apply_content_derived_minimum_size(self._root_layout)
            if self.isVisible() and not self.isMaximized():
                # Once shown, the new minimum must still fit the screen: the
                # base class fits it on first show only, and this line changes
                # after that (the check starts on show, and ends minutes later).
                self._fit_content_to_screen()

    def _maybe_auto_start(self) -> str:
        """Start the cache check if this drive needs it and the disc allows.

        Returns the decision's action (a `cache_check_plan` constant), so the
        caller and the tests can tell "started" from each reason it did not.
        Never blocks: starting is handing the work to the worker thread.
        """
        if self._closing or self._thread is not None:
            # Closing, or a run (pressed for, or automatic) already holds the
            # drive: never a second reader.
            return cache_check_plan.NOTHING
        decision = self._auto_check_decision()
        self._set_auto_note(decision.message)
        log.info(
            "automatic cache check for %s: %s (verdict %s, disc %s, drive busy %s)",
            self._device or "(auto-detected drive)",
            decision.action,
            self._cache_verdict,
            self._audio_disc_present,
            self._drive_busy,
        )
        if decision.action == cache_check_plan.START:
            self._auto_check_attempted = True
            self._start_calibration()
            announce(self._auto_note_label, decision.message)
        return decision.action

    def notify_disc_ready(self, device: str) -> str:
        """The main window read an audio CD in ``device``: start if waiting.

        Called while this window is open, so "it starts by itself when you
        insert a CD" is something the window does rather than a promise about
        the next time it is opened. A read of a different drive is ignored.
        """
        if device and self._device and device != self._device:
            return cache_check_plan.NOTHING
        self._audio_disc_present = True
        # The read that reported this disc has finished, so the drive is free.
        self._drive_busy = False
        return self._maybe_auto_start()

    def _on_skip_clicked(self) -> None:
        """Stop the running check. Non-blocking: the kill is the worker's cancel.

        ``DriveSetupWorker.cancel`` SIGKILLs the probe's process group (through
        the backend's ``cancel_setup``), which ends the worker's blocked call;
        the worker then reports, and `_on_finished` tidies up. Nothing here
        waits, so the window stays responsive while the child dies.
        """
        worker = self._worker
        if worker is None:
            return
        self._skip_requested = True
        if self._skip_button is not None:
            self._skip_button.setEnabled(False)
        self._status_label.setText("Stopping the check…")
        log.info("drive setup: Skip check pressed for %s", self._device)
        worker.cancel()
