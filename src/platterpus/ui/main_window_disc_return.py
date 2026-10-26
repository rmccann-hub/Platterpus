"""A disc that leaves the drive and comes back keeps the release the user chose.

A mixin ``MainWindow`` inherits (``docs/architecture.md`` §3.6), so its methods
stay reachable as ``window._x`` while this one concern lives in its own file.

**Why it exists** (the owner's Full run A on 0.7.112, app log of bundle
``platterpusbundle20261021t113505z`` lines 649-705). Forty-one seconds after a
rip finished, the drive reported ``disc → open → unavailable → disc`` within
2.5 s with nobody touching it. The app took the ``open`` reading as an eject,
cleared the disc view (the chosen release with it), re-read the disc, asked
MusicBrainz again and opened the release picker over the unattended script.
Fifty-seven of that run's sixty failures descend from that one reading.

Two halves, in two places:

* the media watcher no longer believes an empty tray until it has lasted
  (:data:`platterpus.drive_media.REMOVAL_CONFIRM_S`); a disc read again before
  then is :data:`~platterpus.drive_media.RETURNED`, not an insertion;
* this file: before the view is cleared, or before a returned disc is re-read,
  the disc's state is **parked**. When the next read of the drive finds the
  SAME MusicBrainz disc ID, the parked release and the user's edits come back
  and no lookup runs. A different disc ID is a different disc, and gets the
  full treatment. The disc ID is read, never predicted: a quick swap looks
  exactly like a flicker from the tray's side.

A deliberate Rescan or a drive change drops the parked state, so asking again
still asks (``_on_drive_changed``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from platterpus.adapters.musicbrainz_client import ReleaseDetail, TrackSummary
from platterpus.parsers.cd_info import DiscInfo
from platterpus.ui.main_window_shared import MainWindowShared
from platterpus.ui.track_table import AlbumMetadata

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParkedDisc:
    """What the window held for one disc, taken just before it was cleared.

    Only the facts the user chose or edited: the release (and the disc it was
    chosen for), a hand-picked cover, and the track table as typed. Anything the
    next read of the drive will report again (track count, TOC) is re-read.
    """

    disc_id: str
    release_id: str
    release_detail: ReleaseDetail | None
    release_chosen_for: str
    manual_cover_path: str | None
    album: AlbumMetadata
    tracks: tuple[TrackSummary, ...]
    selected: tuple[int, ...]


class DiscReturnMixin(MainWindowShared):
    """Park a disc's state when it may be leaving, restore it when it comes back."""

    def _park_disc(self) -> None:
        """Remember the disc on screen before its view is cleared or re-read.

        Overwrites any older parked disc: only the most recent one can come back.
        """
        table = self._track_table
        self._parked_disc = ParkedDisc(
            disc_id=self._current_disc_id,
            release_id=self._current_release_id,
            release_detail=self._current_release_detail,
            release_chosen_for=self._mb_release_chosen_for,
            manual_cover_path=self._manual_cover_path,
            album=table.album_metadata(),
            tracks=tuple(table.tracks()),
            selected=tuple(table.selected_track_numbers()),
        )

    def _on_disc_returned(self, device: str, status: str, gap_s: float) -> None:
        """The tray read empty for less than the removal bound, then a disc again.

        The view was never cleared. Re-read the disc to learn whether it is the
        same one; :meth:`_restore_parked_disc` settles it when the read lands.
        """
        log.info(
            "drive %s reported no disc for %.1fs, then %s again: too short to be "
            "a removal, so the disc view is kept and the disc is re-read to check "
            "it is the same one",
            device,
            gap_s,
            status,
        )
        self._park_disc()
        self._disc_info_panel.set_disc_info_loading()
        self._start_disc_info(device)

    def _restore_parked_disc(self, info: DiscInfo) -> bool:
        """Settle a parked disc against the disc just read. True when restored.

        Called by ``_on_disc_info_ready`` before it shows the read. The parked
        state is consumed either way: it describes one departure.

        * Same MusicBrainz disc ID, and a release had been chosen for it: put the
          release, the chosen marker, the cover and (when the view was cleared)
          the user's edits back, and say so. The caller then skips the lookup.
        * A different disc: if the view still shows the old one (the RETURNED
          path keeps it), clear it now, so the new disc's lookup starts clean.
        """
        parked = self._parked_disc
        self._parked_disc = None
        if parked is None:
            return False
        same_disc = bool(info.musicbrainz_disc_id) and (
            info.musicbrainz_disc_id == parked.disc_id
        )
        if not same_disc:
            if self._current_release_id or self._track_table.tracks():
                log.info(
                    "the disc now in the drive (disc ID %r) is not the one shown "
                    "(disc ID %r): clearing the old disc's view",
                    info.musicbrainz_disc_id,
                    parked.disc_id,
                )
                self._reset_disc_view()
            return False
        if not parked.release_id or parked.release_detail is None:
            return False  # nothing was chosen for it; the lookup asks as before
        self._current_disc_id = parked.disc_id
        self._current_release_id = parked.release_id
        self._current_release_detail = parked.release_detail
        self._mb_release_chosen_for = parked.release_chosen_for or parked.disc_id
        self._manual_cover_path = parked.manual_cover_path
        # The RETURNED path never cleared the table, and the user may have typed
        # into it since: what is on screen is newer than the parked copy.
        if not self._track_table.tracks():
            self._track_table.set_release(parked.release_detail)
            self._track_table.restore_edits(
                parked.album, parked.tracks, parked.selected
            )
        self._rip_controls.set_release_id(parked.release_id)
        summary = parked.release_detail.summary
        self._disc_info_panel.set_mb_applied(summary.artist_credit, summary.title)
        log.info(
            "the disc back in the drive is the one shown (disc ID %r): keeping "
            "release %s and the edits made to it; no new MusicBrainz lookup",
            parked.disc_id,
            parked.release_id,
        )
        return True
