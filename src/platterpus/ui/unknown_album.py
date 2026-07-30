"""Unknown-album flow — dialog confirming the rip + helper functions.

When MusicBrainz returns no matches for the inserted disc, the user
can choose to rip anyway with placeholder tags (the GUI's unknown-album
mode — cyanrip has no `--unknown` flag, so the GUI implements this
itself). This module provides:

- `UnknownAlbumDialog` — modal confirmation. Lets the user toggle
  "auto-launch Picard" before committing.
- `apply_track_tags(metaflac, flac_files, album, tracks)` — writes the
  (possibly user-edited) album + per-track fields from the track table
  to the FLACs, falling back to the "Track NN" / "Unknown Album" /
  "Unknown Artist" placeholders for blank fields. This is the path the
  main window uses after an unknown rip.
- `apply_placeholder_tags(metaflac, flac_files)` — the simpler no-edits
  path: always writes the placeholder template.
- `launch_picard_for(folder)` — runs `flatpak run org.musicbrainz.Picard`
  with the rip folder as an argument. Returns True on success.

The main window orchestrates: it shows the dialog, kicks off the rip
with `unknown=True`, tags the FLACs from the track table after the rip
finishes, and optionally invokes Picard.
"""

from __future__ import annotations

import logging
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from platterpus.adapters.metaflac import MetaflacAdapter, MetaflacError
from platterpus.ui.dialogs.centering import CenteredDialog

if TYPE_CHECKING:  # avoid importing Qt-heavy track_table at runtime
    from platterpus.adapters.musicbrainz_client import TrackSummary
    from platterpus.ui.track_table import AlbumMetadata

log = logging.getLogger(__name__)


# Picard's Flatpak app ID. Single constant so the dependency registry
# and this module agree on the spelling.
_PICARD_FLATPAK_ID: str = "org.musicbrainz.Picard"


class UnknownAlbumDialog(CenteredDialog):
    """Modal confirmation before running an unknown-album rip."""

    def __init__(
        self,
        auto_launch_picard_default: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rip as unknown album")
        self.setModal(True)

        root = QVBoxLayout(self)

        intro = QLabel(
            "MusicBrainz has no record of this disc. You can still rip "
            "it now with placeholder tags (Track 01, Track 02, …). "
            "You can edit the tags later in MusicBrainz Picard."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        self._picard_check: QCheckBox = QCheckBox(
            "Launch MusicBrainz Picard when the rip finishes", self
        )
        self._picard_check.setChecked(auto_launch_picard_default)
        root.addWidget(self._picard_check)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Rip as unknown")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        root.addWidget(button_box)

    # --- Public surface -----------------------------------------------------

    def auto_launch_picard(self) -> bool:
        """Whether the user wants Picard to open after the rip."""
        return self._picard_check.isChecked()


# --- Helper functions -------------------------------------------------------


def apply_placeholder_tags(
    metaflac: MetaflacAdapter,
    flac_files: Sequence[Path],
) -> list[Path]:
    """Apply "Track NN" placeholder tags to each FLAC.

    Tags written per file:
        TITLE       = Track NN
        ARTIST      = Unknown Artist
        ALBUM       = Unknown Album
        TRACKNUMBER = NN

    Returns the list of files that succeeded. Files that fail
    individually are logged at WARNING; we don't abort the whole batch
    because partial placeholders are still better than no tags at all.
    """
    succeeded: list[Path] = []
    for flac_path in flac_files:
        # From the FILENAME, not the list position — see `_leading_track_number` and
        # the note in `apply_track_tags`. Same off-by-one lived here: with track 1
        # deselected, `02 - …` was tagged `Track 01` / `TRACKNUMBER=01`.
        number_from_name = _leading_track_number(flac_path)
        if number_from_name is None:
            log.warning(
                "skipping placeholder tags for %s — its name does not start with a "
                "track number, so we cannot tell which track it is",
                flac_path.name,
            )
            continue
        number = f"{number_from_name:02d}"
        tags = {
            "TITLE": f"Track {number}",
            "ARTIST": "Unknown Artist",
            "ALBUM": "Unknown Album",
            "TRACKNUMBER": number,
        }
        try:
            metaflac.write_tags(flac_path, tags)
            succeeded.append(flac_path)
        except MetaflacError as exc:
            log.warning("placeholder tag write failed for %s: %s", flac_path, exc)
    return succeeded


# cyanrip names unknown-disc files from the `## - Track NN` template, so the file's
# own name carries its track number. Anchored and bounded: a stray leading digit run
# in some other naming scheme must not be mistaken for a track number.
_LEADING_TRACK_NUMBER = re.compile(r"^(?P<number>\d{1,3})\b")


def _leading_track_number(path: Path) -> int | None:
    """The track number a rip filename starts with, or None if it doesn't.

    Returning None rather than a guess is deliberate: the caller skips the file and
    says so, because a *wrong* TRACKNUMBER on an archival master is worse than a
    missing one — it is indistinguishable from a correct one to every later reader.
    """
    match = _LEADING_TRACK_NUMBER.match(path.stem)
    if match is None:
        return None
    number = int(match.group("number"))
    return number if number > 0 else None


def apply_track_tags(
    metaflac: MetaflacAdapter,
    flac_files: Sequence[Path],
    album: AlbumMetadata,
    tracks: Sequence[TrackSummary],
) -> list[Path]:
    """Apply the user's (possibly edited) album + per-track tags to FLACs.

    This is the edit-aware version of `apply_placeholder_tags`: it reads
    whatever the user typed into the track table for an unknown disc and
    writes it to the FLACs after the rip. Files are matched to table rows
    by track number (both are in track order). Any blank field falls back
    to the unknown-album placeholder, so a half-filled table still yields
    complete, sensible tags rather than empty ones.

    Tags written per file:
        TITLE        = edited title          (fallback "Track NN")
        ARTIST       = edited track artist   (fallback album artist)
        ALBUM        = edited album title    (fallback "Unknown Album")
        ALBUMARTIST  = edited album artist   (fallback "Unknown Artist")
        TRACKNUMBER  = NN
        DATE         = edited year           (omitted when blank)

    Returns the list of files that tagged successfully; per-file failures
    are logged at WARNING without aborting the batch.
    """
    album_artist = (album.artist or "").strip() or "Unknown Artist"
    album_title = (album.title or "").strip() or "Unknown Album"
    album_year = (album.year or "").strip()
    by_number = {track.number: track for track in tracks}

    succeeded: list[Path] = []
    for flac_path in flac_files:
        # Take the track number from the FILENAME, not from the file's position in
        # the list. Both agree only when every track was ripped — and the Rip?
        # column lets the user deselect tracks, so they routinely do not.
        #
        # The bug this replaces: `enumerate(flac_files, start=1)` used the position
        # as the track number. Untick track 1, and the files are `02 - …` onward, so
        # the file for track 2 was written track 1's title and `TRACKNUMBER=01`, the
        # file for track 3 got track 2's, and so on — **every tag on the archival
        # master silently off by one**, with the UI reporting success (audit,
        # 2026-07-29).
        number_from_name = _leading_track_number(flac_path)
        if number_from_name is None:
            # Nothing to key on. Tagging with a guessed number is worse than
            # skipping: a wrong TRACKNUMBER is indistinguishable from a real one.
            log.warning(
                "skipping tags for %s — its name does not start with a track "
                "number, so we cannot tell which track it is",
                flac_path.name,
            )
            continue
        number = f"{number_from_name:02d}"
        track = by_number.get(number_from_name)
        title = (track.title or "").strip() if track else ""
        artist = (track.artist_credit or "").strip() if track else ""
        tags = {
            "TITLE": title or f"Track {number}",
            "ARTIST": artist or album_artist,
            "ALBUM": album_title,
            "ALBUMARTIST": album_artist,
            "TRACKNUMBER": number,
        }
        if album_year:
            tags["DATE"] = album_year
        try:
            metaflac.write_tags(flac_path, tags)
            succeeded.append(flac_path)
        except MetaflacError as exc:
            log.warning("tag write failed for %s: %s", flac_path, exc)
    return succeeded


def launch_picard_for(folder: Path) -> bool:
    """Launch MusicBrainz Picard via Flatpak with `folder` as an argument.

    Returns True if the subprocess started, False on FileNotFoundError
    (flatpak missing) or OSError. Doesn't block — Picard runs detached.
    """
    argv: list[str] = [
        "flatpak",
        "run",
        _PICARD_FLATPAK_ID,
        str(folder),
    ]
    try:
        # start_new_session=True detaches Picard into its own session/process
        # group (BUG-7) so it isn't killed when Platterpus exits and can't be
        # caught by a signal aimed at our group — consistent with the other
        # fire-and-forget launch (main_window_update.py).
        subprocess.Popen(argv, start_new_session=True)
    except (FileNotFoundError, OSError) as exc:
        log.warning("launch_picard_for(%s) failed: %s", folder, exc)
        return False
    return True
