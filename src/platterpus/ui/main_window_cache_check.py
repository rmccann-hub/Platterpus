"""The main window's half of the automatic cache check (TASKS R53).

Extracted as a mixin, like the other ``main_window_*`` concerns (KDD-19), so the
drive-calibration mixin (`main_window_drive`) does not grow by a second job. Its
methods stay reachable as ``window._x``. What it does:

* tells an open *Set up drive* window that a disc has been read, so a check
  that was waiting for a CD starts (`_tell_drive_setup_disc_ready`);
* answers "is something already reading this drive?" for that window, because a
  second reader is how a drive wedges (`_drive_is_busy_for_setup`);
* at rip start, on a drive with no cache verdict, shows a status-bar note with a
  Dismiss button, and never a box and never the probe: the rip goes ahead
  (`_note_cache_check_at_rip_start`).

The decisions are the pure `cache_check_plan` module's; this file only shows
them. Contract it expects from the host window: ``self._drive_picker``,
``self._drive_profiles``, ``self._backend``, ``self._fingerprint_for`` and
``self._drive_being_freed`` (DriveMixin), and, for the note, a ``QMainWindow``.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QWidget,
)

from platterpus import cache_check_plan
from platterpus.ui.accessibility import announce
from platterpus.ui.drive_setup_dialog import DriveSetupDialog
from platterpus.ui.main_window_shared import MainWindowShared

log = logging.getLogger(__name__)


class CacheCheckMixin(MainWindowShared):
    """Wakes a waiting Set up drive window; notes a missing verdict at rip start."""

    #: The Set up drive window while it is open (``exec()`` is running), so a
    #: disc read that lands meanwhile can start its waiting cache check
    #: (`_tell_drive_setup_disc_ready`). ``None`` otherwise.
    _drive_setup_dialog: DriveSetupDialog | None = None
    #: The status-bar note shown when a rip starts on a drive with no cache
    #: verdict (`_note_cache_check_at_rip_start`), built on first use.
    _cache_check_note: QWidget | None = None
    _cache_check_note_label: QLabel | None = None

    def _drive_is_busy_for_setup(self) -> bool:
        """Whether something already reads the drive: a rip, a disc read, or the
        drive-freeing kill. A cache check started then would be a second reader,
        which is how a drive wedges."""
        if getattr(self, "_rip_thread", None) is not None:
            return True
        scan = getattr(self, "_disc_info_thread", None)
        if scan is not None and scan.isRunning():
            return True
        return self._drive_being_freed()

    def _tell_drive_setup_disc_ready(self, device: str, num_tracks: int) -> None:
        """A disc read landed: let an open Set up drive start its waiting check.

        Called from the disc-read success slot. Only an audio CD (tracks read)
        counts; the dialog itself ignores a read of a different drive.
        """
        dialog = self._drive_setup_dialog
        if dialog is None or num_tracks <= 0:
            return
        dialog.notify_disc_ready(device)

    def _note_cache_check_at_rip_start(self) -> None:
        """At rip start, say so when this drive's cache check has not run.

        Never a gate and never a probe: the rip goes ahead, and the multi-minute
        check is not started behind the user's back. The note is a status-bar
        line with a Dismiss button, marked ``ⓘ`` so it is not colour alone, and
        logged so a bug report carries it. Best-effort: a note must not stop a
        rip from starting.
        """
        try:
            drive = self._drive_picker.current_drive()
            note: str | None = None
            if drive is not None:
                verdict = cache_check_plan.verdict_state(
                    self._drive_profiles.get(self._fingerprint_for(drive)[0]),
                    getattr(drive, "release", ""),
                )
                note = cache_check_plan.rip_start_note(
                    can_analyze=self._backend.supports_cache_analysis(),
                    verdict=verdict,
                )
            if note:
                log.info("cache check at rip start: %s", note)
            self._show_cache_check_note(note)
        except Exception:  # noqa: BLE001 — a note is never load-bearing
            log.warning("could not check the drive's cache verdict", exc_info=True)

    def _show_cache_check_note(self, text: str | None) -> None:
        """Show ``text`` in the status-bar note, or hide the note (``None``)."""
        if not text:
            if self._cache_check_note is not None:
                self._cache_check_note.setVisible(False)
            return
        if not isinstance(self, QMainWindow):
            return  # a test double; the log line is the whole record
        if self._cache_check_note is None or self._cache_check_note_label is None:
            # One return value, not a tuple, so the label sweep can trace this
            # label to where it states PlainText; the note is its parent.
            label = _new_cache_check_note(self.statusBar())
            self._cache_check_note_label = label
            self._cache_check_note = label.parentWidget()
        self._cache_check_note_label.setText(text)
        if self._cache_check_note is not None:  # the label's parent; always set
            self._cache_check_note.setVisible(True)
        announce(self._cache_check_note_label, text)


def _new_cache_check_note(bar: QStatusBar) -> QLabel:
    """Build the rip-start cache note and return its label (the note is the
    label's parent): a wrapped label and a Dismiss button.

    A widget rather than ``showMessage`` for the reason the dependency line is
    one (`main_window_deps._new_dependency_status_label`): a temporary message
    is wiped by any menu's empty status tip. Dismissible because it is advice,
    not state: the user may know and not care, and it must not sit there
    nagging. PlainText because it is set later; the ``ⓘ`` carries its meaning
    without colour.
    """
    note = QWidget(bar)
    row = QHBoxLayout(note)
    row.setContentsMargins(0, 0, 0, 0)
    label = QLabel(note)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    label.setAccessibleName("Audio-cache check note")
    row.addWidget(label, 1)
    dismiss = QPushButton("Dismiss", note)
    dismiss.setAccessibleName("Dismiss the audio-cache check note")
    dismiss.clicked.connect(lambda: note.setVisible(False))
    row.addWidget(dismiss)
    bar.addWidget(note, 1)
    note.setVisible(False)
    return label
