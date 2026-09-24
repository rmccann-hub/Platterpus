"""Fitting a dialog to its content and to the screen: the fit, and the scroll area.

Split out of `centering.py` on 2026-09-23, and the fit itself followed on
2026-09-24, both times when that module passed the ~300-line cohesion heuristic.
The split is by job: `centering.py` PLACES a window (which screen, where on it)
and logs its lifecycle; this module SIZES one. The two halves here belong
together — :func:`fit_dialog_to_screen` reads :class:`FitScrollArea`'s size hint
and its :meth:`~FitScrollArea.unmet_height` — so a reader asking "why is this
dialog this tall?" finds the whole answer in one file.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QDialog, QFrame, QScrollArea, QWidget


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


def fit_dialog_to_screen(dialog: QDialog, avail: QSize, margin: int) -> None:
    """Give wrapped text the height it needs, and never outgrow the screen.

    **Why every dialog, and why here.** Qt sizes a new window from its size
    hint and then caps it at two-thirds of the screen (`adjustedSize`), and a
    word-wrapped `QLabel` will be squeezed below the height its own text needs
    rather than push the window taller — its minimum is one line. So on a
    short *logical* screen (a 1080p panel at 200% scaling is 540 px tall) the
    cyanrip build picker opened 360 px tall with every one of its five
    paragraphs cut off mid-sentence. Real-user report, 2026-09-23. Measured,
    not assumed: the picker came up at exactly two-thirds of a 540, 720 and
    800 px virtual screen, clipping 5, 1 and 1 labels.

    The two halves of the rule already existed, each in ONE dialog:
    `SettingsDialog` clamps itself to the screen, and `DriveSetupDialog`
    refuses to be shorter than its prose. The other thirteen had neither,
    which is `docs/testing.md` §5.o — a rule enforced at the place it was
    learned. So it lives on the base class now.

    **What it does**, on first show only:

    * width is kept, unless it is wider than the screen — or NARROWER than
      the content can be: a checkbox or a button cannot wrap, and a dialog
      that sets its own minimum size switches off the layout's minimum, so
      Qt no longer stops it being squeezed (the uninstall dialog's checkbox,
      at 150% text; found by the conformance matrix);
    * height grows to what the content needs AT THAT WIDTH (height-for-width,
      which is the number a wrapped label actually needs — `sizeHint` is
      computed at a different width and is the wrong number), and is capped
      at the screen;
    * an explicit minimum larger than the screen is lowered to fit, because a
      window the user cannot fully see has buttons they cannot reach.

    Content taller than the screen cannot be fitted by resizing; it has to
    scroll. That is what
    :class:`~platterpus.ui.dialogs.fit_scroll_area.FitScrollArea` is for; once
    the width is settled, the window also grows by whatever such an area
    still cannot show, because its size hint was measured at a different
    width. `tests/test_ui_conformance.py` is the gate: every rule, every
    window, every screen shape, theme and text size.
    """
    # The margin is VERTICAL only: it is for the taskbar and the title bar,
    # which is where a dialog loses its buttons. Sideways a chosen width is
    # kept unless it is wider than the screen itself — a dialog that asked
    # for 800 px on an 800 px screen fits, and shrinking it to make room for
    # a margin nobody needs would override a size it chose deliberately.
    max_w = max(avail.width(), 320)
    max_h = max(avail.height() - margin, 240)
    if dialog.minimumWidth() > max_w:
        dialog.setMinimumWidth(max_w)
    if dialog.minimumHeight() > max_h:
        dialog.setMinimumHeight(max_h)
    layout = dialog.layout()
    content_min_w = layout.totalMinimumSize().width() if layout is not None else 0
    if dialog.minimumWidth() < min(content_min_w, max_w):
        # So the user cannot drag it narrower than its content, either.
        dialog.setMinimumWidth(min(content_min_w, max_w))
    width = min(max(dialog.width(), dialog.minimumWidth()), max_w)
    if dialog.hasHeightForWidth():
        need = dialog.heightForWidth(width)
    else:
        need = dialog.sizeHint().height()
    height = min(max(dialog.height(), need), max_h)
    if (width, height) != (dialog.width(), dialog.height()):
        dialog.resize(width, height)
    if layout is None or height >= max_h:
        return
    # Second pass, at the real width: a scrolling body whose size hint was
    # measured at another width may still be short of its content.
    layout.activate()
    unmet = max(
        (a.unmet_height() for a in dialog.findChildren(FitScrollArea)), default=0
    )
    if unmet:
        dialog.resize(width, min(height + unmet, max_h))
