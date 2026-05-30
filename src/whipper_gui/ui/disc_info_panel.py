"""Read-only panel showing the currently-loaded disc's identification.

The panel is a pure view — it doesn't fetch anything itself. The main
window observes `drive_changed` from the DrivePicker, runs
`WhipperBackend.disc_info()` and `MusicBrainzClient.releases_by_disc_id()`
on workers, and pushes results into this panel via the `set_*` methods.

Why a pure view: the orchestration of "fetch disc info, then look up
MusicBrainz" is two-step async work. Keeping that logic in the main
window (or a controller) means this widget stays trivially testable
and re-usable.

Fields displayed:
  Drive               — the device path of the currently-selected drive
  MusicBrainz disc ID — from `whipper cd info`
  CDDB disc ID        — same source
  MusicBrainz match   — outcome of the MB lookup (or a status message)
  AccurateRip         — placeholder; whipper verifies AR during the rip,
                        so we surface results in `RipProgress`, not here
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QLabel, QWidget

from whipper_gui.adapters.musicbrainz_client import ReleaseSummary
from whipper_gui.parsers.cd_info import DiscInfo

# Placeholder shown in fields we don't have data for yet.
_PLACEHOLDER: str = "—"


class DiscInfoPanel(QWidget):
    """Read-only panel. Pure view; no data fetching here."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Use TextSelectableByMouse on the value labels so the user
        # can copy a disc ID into Picard or a browser.
        self._drive_value: QLabel = self._value_label("(no drive)")
        self._mb_id_value: QLabel = self._value_label(_PLACEHOLDER)
        self._cddb_id_value: QLabel = self._value_label(_PLACEHOLDER)
        self._mb_match_value: QLabel = self._value_label(_PLACEHOLDER)
        self._accuraterip_value: QLabel = self._value_label(
            "verified during rip"
        )

        form = QFormLayout(self)
        form.addRow("Drive:", self._drive_value)
        form.addRow("MusicBrainz disc ID:", self._mb_id_value)
        form.addRow("CDDB disc ID:", self._cddb_id_value)
        form.addRow("MusicBrainz match:", self._mb_match_value)
        form.addRow("AccurateRip:", self._accuraterip_value)

    # --- Drive selection -----------------------------------------------------

    def set_drive(self, device: str | None) -> None:
        """Set the drive shown at the top of the panel.

        Clears the disc-derived fields — when the user picks a new
        drive, the disc that was loaded is no longer the relevant one.
        """
        self._drive_value.setText(device or "(no drive)")
        self.clear_disc_state()

    def clear_disc_state(self) -> None:
        """Reset every disc-derived field. Called on drive change."""
        self._mb_id_value.setText(_PLACEHOLDER)
        self._cddb_id_value.setText(_PLACEHOLDER)
        self._mb_match_value.setText(_PLACEHOLDER)

    # --- Disc info (from `whipper cd info`) ---------------------------------

    def set_disc_info_loading(self) -> None:
        """Show 'reading disc…' while the disc_info subprocess runs."""
        self._mb_id_value.setText("…")
        self._cddb_id_value.setText("…")
        self._mb_match_value.setText("reading disc…")

    def set_disc_info(self, info: DiscInfo) -> None:
        """Populate the MB/CDDB disc-ID fields."""
        self._mb_id_value.setText(info.musicbrainz_disc_id or _PLACEHOLDER)
        self._cddb_id_value.setText(info.cddb_disc_id or _PLACEHOLDER)

    def set_disc_info_error(self, message: str) -> None:
        """Mark the disc fields as failed and show a short error."""
        self._mb_id_value.setText(_PLACEHOLDER)
        self._cddb_id_value.setText(_PLACEHOLDER)
        self._mb_match_value.setText(f"error: {message}")

    # --- MusicBrainz match (from MusicBrainzClient) --------------------------

    def set_mb_loading(self) -> None:
        """Status while a MB lookup is in flight."""
        self._mb_match_value.setText("querying MusicBrainz…")

    def set_mb_matches(self, releases: list[ReleaseSummary]) -> None:
        """Render the count and (when unique) the matched release."""
        if not releases:
            self._mb_match_value.setText("not in MusicBrainz")
        elif len(releases) == 1:
            release = releases[0]
            artist = release.artist_credit or "Unknown Artist"
            title = release.title or "Unknown Title"
            self._mb_match_value.setText(f"1 match: {artist} — {title}")
        else:
            self._mb_match_value.setText(
                f"{len(releases)} matches found — pick one"
            )

    def set_mb_error(self, message: str) -> None:
        self._mb_match_value.setText(f"MusicBrainz error: {message}")

    # --- Internals ---------------------------------------------------------

    @staticmethod
    def _value_label(text: str) -> QLabel:
        """A monospaced-by-context value label that supports copy-on-select."""
        label = QLabel(text)
        # Selecting with the mouse + Ctrl+C is the easiest way to grab
        # a disc ID into something else (Picard, a web search).
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        return label
