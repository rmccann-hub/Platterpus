"""A scroll area for a dialog BODY that asks for all of its content.

Split out of `centering.py` on 2026-09-23 when that module passed the ~300-line
cohesion heuristic: `CenteredDialog` places and sizes a window, and this is a
widget a dialog puts inside itself. They cooperate — the base class's fit reads
this widget's size hint — but they are two jobs, and a reader looking for "why
does the picker scroll?" should not have to read about multi-monitor placement
first.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QWidget


class FitScrollArea(QScrollArea):
    """A scroll area that asks for ALL of its content, and scrolls only when the
    screen cannot give it that much.

    **Why not a plain `QScrollArea`.** A scroll area reports a small, arbitrary
    size hint of its own, because it is designed to be smaller than what it holds.
    `SettingsDialog._opening_size` exists entirely to work around that: a dialog
    sized from its hint opened showing a third of the form. This class answers the
    size hint with its CONTENT's full height, so the dialog around it sizes to
    the text like any other layout, and
    :meth:`CenteredDialog._fit_content_to_screen` caps it at the screen. On a big
    screen there is no scrollbar and it is invisible; on a small one the body
    scrolls and the buttons outside it stay reachable.

    Use it for a dialog BODY whose length is not ours to fix — the cyanrip build
    picker lists whatever builds the handshake record currently names, and that
    list grows. Keep the button box outside it. Never nest it inside another
    scroll surface: an inner surface with nothing left to scroll swallows the
    wheel (the v0.5.15 lesson in `DriveSetupDialog`).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Without this the inner widget keeps its own size and the area shows it
        # at a fixed width, which reintroduces horizontal clipping.
        self.setWidgetResizable(True)
        # No sunken border: a framed box inside a dialog reads as a nested panel,
        # and this is meant to be invisible whenever everything fits.
        self.setFrameShape(QFrame.Shape.NoFrame)
        # Wrapped text never needs to scroll sideways; a horizontal bar here would
        # only ever mean the width arithmetic below was off by a pixel.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def _bar_width(self) -> int:
        # Reserved up front so the content is laid out at the width it will
        # actually get once the vertical bar appears; otherwise the text is
        # measured one bar too wide and comes out one line too short.
        return self.verticalScrollBar().sizeHint().width()

    def _content_height_for(self, width: int) -> int:
        """The height the content needs when this area is ``width`` wide.

        Deliberately NOT a `heightForWidth` override. Overriding the Qt pair
        (`hasHeightForWidth` + `heightForWidth`) was the first version, and a
        revert probe showed it was not load-bearing: the size hint below already
        carries the full content height, which is what the dialog's fit reads. An
        override nothing depends on is a second mechanism waiting to disagree
        with the first, so it went.
        """
        inner = self.widget()
        if inner is None:
            return super().sizeHint().height()
        inner_width = max(width - self._bar_width() - 2 * self.frameWidth(), 1)
        if inner.hasHeightForWidth():
            content = inner.heightForWidth(inner_width)
        else:
            content = inner.sizeHint().height()
        return content + 2 * self.frameWidth()

    def sizeHint(self) -> QSize:  # noqa: N802 — Qt override
        inner = self.widget()
        if inner is None:
            return super().sizeHint()
        width = inner.sizeHint().width() + self._bar_width() + 2 * self.frameWidth()
        return QSize(width, self._content_height_for(width))

    def unmet_height(self) -> int:
        """How many pixels taller this area would have to be to stop scrolling.

        Read from the area's ACTUAL width, which is the whole point: the size hint
        above measures the content at its natural width, and a dialog that opened
        narrower than that wraps its text onto more lines than the hint counted.
        Found by `tests/test_ui_conformance.py` at 150% text on a 1024×768 screen:
        the build picker scrolled 63 px in a window with 99 px of screen left.
        `CenteredDialog._fit_content_to_screen` reads this after it has chosen a
        width, and grows the window by it (still capped at the screen).
        """
        inner = self.widget()
        if inner is None:
            return 0
        width = inner.width()
        need = inner.heightForWidth(width) if inner.hasHeightForWidth() else -1
        need = max(need, inner.minimumSizeHint().height())
        return max(0, need - self.viewport().height())

    def minimumSizeHint(self) -> QSize:  # noqa: N802 — Qt override
        # Small on purpose: this is the widget that yields when there is not
        # enough screen, and a large minimum here would push the buttons off it.
        return QSize(super().minimumSizeHint().width(), 80)
