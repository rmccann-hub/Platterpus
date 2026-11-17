"""The main window's "ripping tools aren't installed yet" notice: in the window, never a modal.

Why this exists
---------------
On a fresh install the first launch asks **"Install the ripping tools?"**. Until
2026-11-17 a **No** did not mean no: the launch dependency check (held while the
question was open) was delivered the moment it closed and opened the setup
wizard anyway, then a "Dependency check complete" box listing an install
failure for a setup that never ran, then a cyanrip update offer. Four modals
after the user had just declined one (UX review of 0.7.127, finding F1).

The answer is now the decision for that launch. But a missing ripper is the one
fact that stops the app working, so the rule recorded beside the dependency
check, *deferred, never dropped*, still holds in the sense that matters: the user
is told, visibly, that the tools are missing and how to install them. They are
told by this strip at the top of the main window, which stays until setup has
run, instead of by a dialog they have already said no to.

What the strip holds: one sentence and one **Set up…** button, which opens the
same wizard as Tools → Setup & Updates… → Run setup…. It is built only when it
is first needed, so a machine that never needs it never carries the widget.

Accessibility (`docs/ux-design-principles.md` → *Conformance target*): the
status is carried by the ⚠ glyph and the words, never by colour alone; the
button has no single-character shortcut; no size is set explicitly, so no size
floor applies; and the sentence is announced to a screen reader when it appears.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Final

from PySide6.QtCore import Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QWidget,
)

from platterpus.ui.accessibility import announce

log = logging.getLogger(__name__)

#: The sentence on the strip. It says what is missing, what that means for the
#: user, and what the button does. "Not installed yet", never "failed": nothing
#: was attempted, so nothing failed.
NOTICE_TEXT: Final[str] = (
    "⚠ The ripping tools are not installed yet, so discs can't be ripped. "
    "Setup installs them for you; it takes a few minutes and needs no terminal."
)

#: The button's label. The ellipsis says it opens a window rather than acting at
#: once, the same convention as the menu item it shares a wizard with.
SET_UP_LABEL: Final[str] = "Set up…"


class SetupNeededNotice(QFrame):
    """A one-line strip: what is missing, and a button that starts setup.

    ``on_set_up`` is the window's own ``open_host_setup_dialog``, handed in
    rather than looked up, so this widget knows nothing about the window and
    the one route into the wizard stays the window's (its
    ``run_setup_wizard`` refuses a second wizard over the first).
    """

    def __init__(self, on_set_up: Callable[[], None], parent: QWidget) -> None:
        super().__init__(parent)
        # A styled panel so the strip reads as a notice set apart from the
        # drive picker below it, in the platform's own frame style.
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAccessibleName("Ripping tools not installed")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # PlainText, stated: the sentence is ours, and stating the format means
        # Qt never guesses it (tests/test_labels_state_their_text_format.py).
        self._label: QLabel = QLabel(NOTICE_TEXT, self)
        self._label.setTextFormat(Qt.TextFormat.PlainText)
        self._label.setWordWrap(True)
        # Word wrap makes a label ask for "height for width", and that request
        # travels up to the page, where the scroll area obeys it: the page was
        # then held at its tallest and scrolled even in a window tall enough to
        # show everything, squeezing the track lists to their floors (measured,
        # PySide6 6.11.2 offscreen: page 888 px in an 840 px view). So it is
        # switched off here, and `resizeEvent` gives the label the height its
        # wrapped text needs at its current width instead.
        policy = self._label.sizePolicy()
        policy.setHeightForWidth(False)
        self._label.setSizePolicy(policy)
        layout.addWidget(self._label, 1)

        self._button: QPushButton = QPushButton(SET_UP_LABEL, self)
        self._button.setAccessibleName("Set up the ripping tools")
        self._button.clicked.connect(on_set_up)
        layout.addWidget(self._button)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 — Qt API
        """Keep the label tall enough for its wrapped text at this width.

        Without it a narrow window clipped the second line (measured: 30 px
        needed, 23 px given, at a 640 px window). Only the label's minimum
        height changes, and its width does not depend on it, so this settles
        after one pass.
        """
        super().resizeEvent(event)
        # Measured from the font, not `heightForWidth`, which never reports
        # less than the minimum already set, so the label could grow and
        # never shrink back once the window was widened again.
        label = self._label
        frame = label.height() - label.contentsRect().height()
        wrapped = label.fontMetrics().boundingRect(
            0,
            0,
            max(1, label.contentsRect().width()),
            100_000,
            int(Qt.TextFlag.TextWordWrap),
            label.text(),
        )
        needed = wrapped.height() + frame
        if needed != label.minimumHeight():
            label.setMinimumHeight(needed)

    def text(self) -> str:
        """The sentence the strip shows, for the window's log line and tests."""
        return self._label.text()

    def set_up_button(self) -> QPushButton:
        """The **Set up…** button, so a test can click the real thing."""
        return self._button

    def reveal(self) -> None:
        """Show the strip, and tell a screen reader once; it never takes focus."""
        if self.isHidden():
            self.show()
            announce(self._label, NOTICE_TEXT)
            log.info("setup notice shown: %s", NOTICE_TEXT)

    def conceal(self) -> None:
        """Hide the strip: the ripping tools are installed now."""
        if not self.isHidden():
            self.hide()
            log.info("setup notice hidden: the ripping tools are installed")


def place_notice(
    window: QWidget, on_set_up: Callable[[], None]
) -> SetupNeededNotice | None:
    """Build the strip at the top of ``window``'s page, above the drive picker.

    The main window's page is a widget inside a scroll area, laid out top to
    bottom. The strip is created INSIDE that page, its final parent, and only
    then inserted into the page's layout: `MainWindow.__init__` records a crash
    on exit caused by a populated widget being moved into a container made
    after it, so nothing in the window is reparented.

    Returns ``None``, with a log line naming the menu route instead, when the
    window has no such page (a test double); hidden until :meth:`reveal`.
    """
    scroll = window.centralWidget() if isinstance(window, QMainWindow) else None
    page = scroll.widget() if isinstance(scroll, QScrollArea) else None
    layout = page.layout() if page is not None else None
    if page is None or not isinstance(layout, QBoxLayout):
        log.warning(
            "ripping tools not installed yet, and the window has no page to say "
            "so on; Tools → Setup & Updates… → Run setup… installs them"
        )
        return None
    notice = SetupNeededNotice(on_set_up, page)
    notice.hide()
    layout.insertWidget(0, notice)
    return notice
