"""The MusicBrainz release picker: when it opens, and what its answer does.

A mixin ``MainWindow`` inherits (``docs/architecture.md`` §3.6), so its methods
stay reachable as ``window._x`` while this one concern lives in its own file. The
slot that decides a picker is needed, ``_on_mb_releases``, stays in
``main_window.py`` with the other MusicBrainz slots; this file is the picker it
asks for.

**Why the picker waits (TASKS R96, the owner's report of 2026-10-29).** On
0.7.114 the picker opened by itself while the owner was in Tools → Setup &
Updates…, over the window they were using. Nothing is waiting on its answer, so
it is a dialog that *can hold* (`ui.hold_for_user`): it waits until the main
window is the one in use, then opens, if it is still wanted. "Still wanted" is
checked when it is about to open, not when it was queued: the same disc, no
release chosen for it since, no picker for it open, and no rip running (a rip
owns the track table, `_rip_holds_the_track_table`).

**One held picker per disc.** `_mb_picker_held_for` names the disc a picker is
waiting for, so a second lookup's candidates for that disc are declined while it
waits, as they are while it is open (`_mb_picker_open_for`). It is cleared when
the picker opens or is dropped.
"""

from __future__ import annotations

import logging
import time

from PySide6.QtWidgets import QDialog

from platterpus.adapters.musicbrainz_client import ReleaseSummary
from platterpus.ui.hold_for_user import hold_until_free
from platterpus.ui.main_window_shared import MainWindowShared
from platterpus.ui.release_picker import ReleasePickerDialog

log = logging.getLogger(__name__)


class ReleasePickerMixin(MainWindowShared):
    """Open the release picker when the main window is free, and act on its answer."""

    def _hold_release_picker(
        self, releases: list[ReleaseSummary], context: str
    ) -> None:
        """Ask the user to choose among ``releases`` for disc ``context``, once free."""
        self._mb_picker_held_for = context

        def forget() -> None:
            if self._mb_picker_held_for == context:
                self._mb_picker_held_for = ""

        def show() -> None:
            forget()
            self._ask_release_picker(releases, context)

        hold_until_free(
            self,
            show,
            still_wanted=lambda: self._release_picker_still_wanted(context),
            what=f"release picker for disc {context!r}",
            on_drop=forget,
        )

    def _release_picker_still_wanted(self, context: str) -> bool:
        """True while a held picker for ``context`` should still open."""
        return (
            not self._is_stale_mb_result(context)
            and self._mb_release_chosen_for != context
            and self._mb_picker_open_for != context
            and self._rip_worker is None
        )

    def _ask_release_picker(self, releases: list[ReleaseSummary], context: str) -> None:
        """Open the picker for disc ``context`` and wait for the user's answer.

        The picker is modal and runs a nested event loop, so the disc could change
        while it is open; ``context`` is captured here and threaded into the fetch,
        so the fetch stays tagged to *this* disc.

        LOGGED ON EVERY BRANCH, deliberately. This path used to log nothing at all,
        so a user sitting in front of the picker and a genuinely wedged app produced
        byte-identical logs — a 96-second silence, which is what made the maintainer
        close the window (2026-08-05). The base `CenteredDialog` records that the
        dialog was *presented*; these lines record how long the wait lasted and what
        came out of it, which is the half that identifies a user who walked away
        versus one who cancelled.
        """
        log.info(
            "MusicBrainz returned %d candidates for disc %r — opening the "
            "release picker; the app will WAIT here until the user chooses "
            "(this is not a hang)",
            len(releases),
            context,
        )
        dialog = ReleasePickerDialog(releases, self)
        dialog.scan_request = self._disc_retries.request
        waited_from = time.monotonic()
        # Restored, not cleared, when the picker closes: pickers for two
        # discs can nest, and the outer one is still open.
        outer_picker = self._mb_picker_open_for
        outer_dialog = self._open_release_picker
        self._mb_picker_open_for = context
        self._open_release_picker = dialog
        try:
            accepted = dialog.exec() == QDialog.DialogCode.Accepted
        finally:
            self._mb_picker_open_for = outer_picker
            self._open_release_picker = outer_dialog
        waited = time.monotonic() - waited_from
        if dialog.superseded:
            log.info(
                "release picker for disc %r closed unanswered after %.1fs: a "
                "newer disc scan superseded it and asks again",
                context,
                waited,
            )
        elif accepted:
            mbid = dialog.selected_mbid()
            if mbid:
                log.info("release picker: user chose %s after %.1fs", mbid, waited)
                # Same ordering as the single-candidate branch of
                # `_on_mb_releases`: mark before the emit, because the modal ran a
                # nested event loop and a second lookup's result may already be
                # queued behind it.
                self._mb_release_chosen_for = context
                self._fetch_release_detail(mbid, context)
            else:
                # Accepted with nothing selected shouldn't happen (the OK
                # button is gated on a selection) — say so rather than
                # returning silently, because a silent return here is
                # indistinguishable from the cancel below.
                log.warning(
                    "release picker was accepted after %.1fs but reported no "
                    "selected release; nothing to fetch",
                    waited,
                )
        else:
            log.info(
                "release picker: cancelled after %.1fs — the disc stays unidentified",
                waited,
            )
        # Parented to the window, so dropping the name frees nothing: each
        # lookup left one more hidden picker alive (four by the end of the
        # 2026-09-24 run). Its answer has been read, so hand it back to Qt.
        dialog.deleteLater()

    def _close_superseded_picker(self) -> None:
        """A new disc scan was asked for: close a release picker an older scan
        left open, unanswered.

        Its question belongs to a scan nobody is waiting for, and while it is
        open the new scan's own candidates are declined for the same disc (the
        one-picker rule in `_on_mb_releases`), so the new scan could never ask.
        Run A on 0.7.112 (app log lines 690-705): a picker from a scan the drive
        flicker started stayed open 338 s, and the script's `pick-release` after
        a `rescan` answered it instead of the rescan's question.
        """
        dialog = self._open_release_picker
        if dialog is None or not dialog.isVisible():
            return
        log.info(
            "closing the release picker for disc %r unanswered: a new disc scan "
            "supersedes it",
            self._mb_picker_open_for,
        )
        dialog.superseded = True
        dialog.reject()
