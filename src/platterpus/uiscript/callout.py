"""Numbered callouts drawn onto a walkthrough screenshot (``PLANNING.md`` KDD-42, W3).

The getting-started guide shows, on each picture, the button the next step
presses: a highlight around it and a number beside it. The walkthrough script
names the button by the words the user sees on it (``callout 1 Rip``), the
runner finds the one widget that reads that, and the next ``screenshot`` draws
the mark here.

**Matched on the label the user reads, on purpose.** The guide exists to say
*press the button that reads "Rip"*. Keying the callout on the same words means
a renamed button fails the walkthrough step instead of shipping a picture that
points at a word the app no longer shows.

**Drawn on the picture, never on the window.** The overlay is painted onto the
captured image, so nothing the user or a test sees in the live app changes, and
the same pixels the product drew are underneath.

**Readable in both themes.** The outline is amber (``#B45309``) over a white halo,
so it shows on a light or a dark window; the number is white on that amber, which
measures 5.0:1, above WCAG AA's 4.5:1 for text.

Pure apart from the painting itself, which needs only a ``QImage``: no window,
no event loop. Tested on rendered images in ``tests/test_uiscript_walkthrough.py``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen

#: The mark's colour. White text on it measures 5.0:1 (WCAG AA for text: 4.5:1).
CALLOUT_COLOUR: Final[str] = "#B45309"
#: Drawn under the outline and around the badge, so the mark shows on dark windows.
HALO_COLOUR: Final[str] = "#FFFFFF"
#: Callout numbers run 1 to 99: one or two digits always fit the badge.
MAX_CALLOUT_NUMBER: Final[int] = 99
#: Sizes in logical pixels; each is multiplied by the capture's device pixel ratio.
BADGE_DIAMETER_PX: Final[float] = 26.0
OUTLINE_PX: Final[float] = 3.0
HALO_PX: Final[float] = 7.0
PADDING_PX: Final[float] = 4.0
CORNER_RADIUS_PX: Final[float] = 6.0


def normalise_label(text: str) -> str:
    """A widget's text as the user reads it: mnemonics gone, whitespace collapsed.

    Qt marks a keyboard mnemonic with ``&`` (``"&Rip"`` shows as *Rip*) and
    writes a literal ampersand as ``&&``. Both are undone here, so a script
    names the button by what is on the screen.
    """
    shown = re.sub(r"&(&?)", lambda m: "&" if m.group(1) else "", text or "")
    return " ".join(shown.split())


def label_matches(text: str, wanted: str) -> bool:
    """Whether a widget reading ``text`` is the one ``wanted`` names.

    Exact, after :func:`normalise_label` on both. A trailing ``*`` asks for a
    prefix instead (``callout 2 Bit-perfect*`` for a verdict whose tail varies);
    a bare ``*`` names nothing, so it cannot match every widget at once.
    """
    have = normalise_label(text)
    want = normalise_label(wanted)
    if want.endswith("*"):
        stem = want[:-1].rstrip()
        return bool(stem) and have.startswith(stem)
    return bool(want) and have == want


@dataclass(frozen=True)
class CalloutMark:
    """One mark: its number, and the widget's rectangle in the window's logical
    coordinates (the coordinates ``QWidget.mapTo`` returns)."""

    number: int
    x: int
    y: int
    width: int
    height: int


def draw_callouts(
    image: QImage, marks: Sequence[CalloutMark], scale: float = 1.0
) -> QImage:
    """``image`` with each mark drawn on it: an outline and a numbered badge.

    ``scale`` is the capture's device pixel ratio, so a mark lands on its widget
    on a 2x screen too. The badge sits at the outline's top-left corner and is
    kept inside the image, so a widget at the window's edge still shows its
    number. Returns a new image; ``image`` is not changed.
    """
    out = image.convertToFormat(QImage.Format.Format_ARGB32)
    if not marks:
        return out
    ratio = scale if scale > 0 else 1.0
    painter = QPainter(out)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for mark in marks:
            pad = PADDING_PX * ratio
            outline = QRectF(
                mark.x * ratio - pad,
                mark.y * ratio - pad,
                mark.width * ratio + 2 * pad,
                mark.height * ratio + 2 * pad,
            )
            radius = CORNER_RADIUS_PX * ratio
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(HALO_COLOUR), HALO_PX * ratio))
            painter.drawRoundedRect(outline, radius, radius)
            painter.setPen(QPen(QColor(CALLOUT_COLOUR), OUTLINE_PX * ratio))
            painter.drawRoundedRect(outline, radius, radius)
            _draw_badge(painter, out, outline, mark.number, ratio)
    finally:
        painter.end()
    return out


def _draw_badge(
    painter: QPainter, image: QImage, outline: QRectF, number: int, ratio: float
) -> None:
    """The numbered circle at ``outline``'s top-left corner, kept on the image."""
    diameter = BADGE_DIAMETER_PX * ratio
    half = diameter / 2
    centre_x = min(max(outline.left(), half + 1), image.width() - half - 1)
    centre_y = min(max(outline.top(), half + 1), image.height() - half - 1)
    centre = QPointF(centre_x, centre_y)
    painter.setPen(QPen(QColor(HALO_COLOUR), 2 * ratio))
    painter.setBrush(QColor(CALLOUT_COLOUR))
    painter.drawEllipse(centre, half, half)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(max(1, round(diameter * 0.55)))
    painter.setFont(font)
    painter.setPen(QColor(HALO_COLOUR))
    painter.drawText(
        QRectF(centre_x - half, centre_y - half, diameter, diameter),
        int(Qt.AlignmentFlag.AlignCenter),
        str(number),
    )
