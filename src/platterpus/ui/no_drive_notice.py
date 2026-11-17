"""The main window's empty state when no CD drive is found: one line, not a form of dashes.

Why this exists
---------------
With no drive connected (or none the ripper can see), the window showed
"(no drives found)" in the drive picker and, under it, the disc panel's seven
rows of "—", which look like data about a disc that is not there (UX review of
0.7.127, finding E3). Nothing on screen said what to do next.

Now, while the last drive listing came back empty, the disc panel is hidden and
this one line takes its place, under the drive picker: what is wrong and the
next action, naming the picker's real **Refresh** button. It is non-modal, it
never takes focus, and it goes away the moment a listing finds a drive.

**It does not repeat the setup strip.** Before setup, the ripper that lists the
drives is not installed, so "connect a drive" would be the wrong advice; the
strip at the top of the window (`ui/setup_needed_notice.py`) already says the
tools are missing, with its own button. While that strip shows, this line does
not (the disc panel is still hidden: its dashes are no truer then).

What it leaves alone, on purpose (wave 1 of the review, the owner's plan of
2026-11-17): the track table and the progress bars, which wave 2 redesigns. The
layout is not restructured: the line is inserted into the page below the
picker, the way the setup strip is inserted above it.

Accessibility (`docs/ux-design-principles.md` → *Conformance target*): the
status is carried by the ⓘ glyph and the words, never by colour; no size is set
explicitly; and the sentence is announced once when it appears.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Final

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QBoxLayout, QLabel, QWidget

from platterpus.ui.accessibility import announce
from platterpus.ui.dependency_check_status import INFO_MARK
from platterpus.ui.drive_picker import REFRESH_LABEL, DrivePicker

log = logging.getLogger(__name__)

#: The sentence: what is wrong, and the next action, naming the real button.
NOTICE_TEXT: Final[str] = (
    f"{INFO_MARK} No CD drive found. Connect a drive, then press "
    f"{REFRESH_LABEL.replace('&', '')}."
)


class NoDriveNotice(QLabel):
    """The one-line empty state, kept in step with the drive picker's listing.

    ``hidden_by`` answers "is something else already explaining this?" (the
    setup strip), and ``placeholders`` is the disc panel, whose dashes this line
    stands in for. Both are handed in, so this widget knows nothing of the
    window.
    """

    def __init__(
        self,
        picker: DrivePicker,
        placeholders: QWidget,
        hidden_by: Callable[[], bool],
        parent: QWidget,
    ) -> None:
        super().__init__(NOTICE_TEXT, parent)
        # PlainText, stated (tests/test_labels_state_their_text_format.py).
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setWordWrap(True)
        self.setAccessibleName("No CD drive found")
        self._picker: DrivePicker = picker
        self._placeholders: QWidget = placeholders
        self._hidden_by: Callable[[], bool] = hidden_by
        self.hide()
        picker.listing_changed.connect(self.sync)

    def sync(self) -> None:
        """Show the line in place of the dashes while no drive is listed."""
        empty = self._picker.found_no_drives()
        self._placeholders.setHidden(empty)
        show = empty and not self._hidden_by()
        if show and self.isHidden():
            self.show()
            announce(self, NOTICE_TEXT)
            log.info("empty state shown: %s", NOTICE_TEXT)
        elif not show and not self.isHidden():
            self.hide()


def place_no_drive_notice(
    picker: DrivePicker,
    placeholders: QWidget,
    hidden_by: Callable[[], bool],
) -> NoDriveNotice | None:
    """Build the line into the picker's own page, directly below the picker.

    Created inside that page, its final parent, then inserted into the page's
    layout, as `setup_needed_notice.place_notice` does and for the same reason
    (`MainWindow.__init__`: a populated widget moved into a container made after
    it crashed on exit). Returns None, with a log line, when the picker sits in
    no box layout (a test double).
    """
    page = picker.parentWidget()
    layout = page.layout() if page is not None else None
    if page is None or not isinstance(layout, QBoxLayout):
        log.warning("no drive found, and the window has no page to say so on")
        return None
    notice = NoDriveNotice(picker, placeholders, hidden_by, page)
    layout.insertWidget(layout.indexOf(picker) + 1, notice)
    return notice
