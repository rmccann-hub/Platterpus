"""Status colours that stay readable on light AND dark themes — the one place.

**Why this module exists.** Every coloured status line in the app — the rip
verdict ("✓ Bit-perfect"), the CTDB line, the stall and read-effort warnings,
the Settings validation banner — used a fixed hex colour, commented as a
*"muted, theme-neutral hue that reads on both light and dark Qt palettes"*. It
did not. Measured against the WCAG 2.2 AA bar this project targets (4.5:1 for
normal text), on Breeze Dark — Bazzite's default, and the maintainer's theme —
the green verdict was **3.1:1**, the amber warning **3.2:1**, the grey neutral
**2.5:1** and the red error **2.9:1**. Three lines of secondary text were worse:
they used ``palette(mid)``, a colour Qt defines for bevel shading, which on a
dark theme sits at about **1.1:1** against the window — the dim "Example:" line
in Settings that the maintainer noticed on 2026-09-23.

**No single colour can pass on both.** A green dark enough for a white window is
too dark for a charcoal one. So each level has two variants, and the one used is
chosen from the widget's own palette at the moment the style is set. Each
variant is checked against a range of real backgrounds for its side —
`tests/test_readable_colours.py` computes the ratios, and a sweep refuses a raw
hex colour or ``palette(mid)`` anywhere else in the UI, because a colour chosen
at a call site is a colour nobody measured.

Colour is never the only signal (`CLAUDE.md`, accessibility rule 1): every
level's text also carries its marker (✓ / ⚠ / ✖ / ⓘ). This module makes the
colour legible; the marker makes it unnecessary.

**A theme change while the app is open (UX review L1, 2026-11-17).** "At the
moment the style is set" used to mean *only* then: switching Breeze to Breeze
Dark with the window open left the light-theme amber ``#7d4e00`` on a charcoal
background, because nothing set the style again. So a label styled here is
styled through :func:`apply_status_style`, which remembers the label's level on
the label itself (a Qt *dynamic property*, the ordinary Qt way to hang a value
on a widget), and a widget that owns such labels calls
:func:`reapply_status_styles` from its ``changeEvent`` when Qt reports a palette
or theme change (:data:`PALETTE_EVENTS`).

**Which palette says "dark".** Measured with PySide6 6.11 (offscreen): once a
``QLabel`` has a style sheet, *its own* ``palette()`` is frozen at the last
time the sheet was applied. After ``QApplication.setPalette(dark)`` the label
still reported the light window colour while its parent already reported the
dark one; only setting a sheet again refreshed it. So the colour is chosen from
:func:`backdrop_palette`: the nearest widget, starting at the label, that has no
style sheet of its own, which is the palette the label's background is actually
drawn from.
"""

from __future__ import annotations

from typing import Final

from PySide6.QtCore import QEvent
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QLabel, QWidget

#: For light windows (#ffffff … #dedede). Each is at least 5.2:1 on the darkest
#: background in that range.
LIGHT_VARIANTS: Final[dict[str, str]] = {
    "ok": "#116329",
    "warn": "#7d4e00",
    "neutral": "#4b535c",
    "error": "#a40e26",
}

#: For dark windows (#141618 … #3b4045 — Breeze Dark in Plasma 5 and 6, Fusion
#: dark). Each is at least 4.6:1 on the lightest background in that range.
DARK_VARIANTS: Final[dict[str, str]] = {
    "ok": "#56d364",
    "warn": "#e3b341",
    "neutral": "#b1bac4",
    "error": "#ff8b83",
}

#: The backgrounds each side is held to, used by the test. Named so a change to
#: the range is a visible edit rather than a silent widening.
LIGHT_BACKGROUNDS: Final[tuple[str, ...]] = (
    "#ffffff",
    "#fcfcfc",
    "#eff0f1",
    "#efefef",
    "#e3e5e7",
    "#dedede",
)
DARK_BACKGROUNDS: Final[tuple[str, ...]] = (
    "#141618",
    "#1b1e20",
    "#202326",
    "#232629",
    "#2a2e32",
    "#31363b",
    "#353535",
    "#3b4045",
)

#: The level used when a caller passes one this module does not know.
DEFAULT_LEVEL: Final[str] = "neutral"


def relative_luminance(hex_colour: str) -> float:
    """WCAG 2.x relative luminance of ``#rrggbb``. Pure."""
    digits = hex_colour.lstrip("#")
    channels = [int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [
        c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(a: str, b: str) -> float:
    """WCAG contrast ratio between two ``#rrggbb`` colours, 1.0 … 21.0. Pure."""
    high, low = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def palette_is_dark(palette: QPalette) -> bool:
    """Whether text sits on a dark window in ``palette``.

    Decided by the window colour's luminance rather than by a theme name, so it
    follows whatever the desktop actually applied — including a custom scheme.
    """
    window = palette.color(QPalette.ColorRole.Window).name()
    return relative_luminance(window) < 0.2


def status_colour(level: str, palette: QPalette) -> str:
    """The ``#rrggbb`` for ``level`` that is legible on ``palette``'s window."""
    variants = DARK_VARIANTS if palette_is_dark(palette) else LIGHT_VARIANTS
    return variants.get(level, variants[DEFAULT_LEVEL])


def backdrop_palette(widget: QWidget) -> QPalette:
    """The palette ``widget``'s background is drawn from, current after a theme change.

    The nearest widget, starting at ``widget`` itself and walking up its
    parents, that carries no style sheet of its own; the application palette if
    every one of them does. See the module docstring for why a styled label's
    own palette cannot be trusted: it still described the old theme in the
    measurement.
    """
    current: QWidget | None = widget
    while current is not None:
        if not current.styleSheet():
            return current.palette()
        current = current.parentWidget()
    return QApplication.palette()


def status_style(level: str, widget: QWidget, *, bold: bool = True) -> str:
    """A ``QLabel`` stylesheet for a status line at ``level`` on ``widget``.

    Takes the widget rather than a palette so a call site cannot pass the wrong
    one: the colour is chosen for what the label is drawn on
    (:func:`backdrop_palette`).
    """
    weight = " font-weight: bold;" if bold else ""
    colour = status_colour(level, backdrop_palette(widget))
    return f"QLabel {{ color: {colour};{weight} padding: 2px; }}"


#: The dynamic property :func:`apply_status_style` records a label's level in,
#: and the one beside it for its weight. Read back only by
#: :func:`reapply_status_styles`.
STATUS_LEVEL_PROPERTY: Final[str] = "platterpusStatusLevel"
STATUS_BOLD_PROPERTY: Final[str] = "platterpusStatusBold"

#: The ``changeEvent`` types after which the colours must be chosen again: the
#: widget's own palette changed, the application's did, or the desktop theme did.
PALETTE_EVENTS: Final[frozenset[QEvent.Type]] = frozenset(
    {
        QEvent.Type.PaletteChange,
        QEvent.Type.ApplicationPaletteChange,
        QEvent.Type.ThemeChange,
    }
)


def apply_status_style(label: QLabel, level: str, *, bold: bool = True) -> None:
    """Colour ``label`` at ``level`` and remember the level for a theme change.

    The style sheet is set only when it differs from the one the label has, so
    calling this again with the same answer (every palette event does) costs
    no re-polish and cannot loop through the events a re-polish sends.
    """
    label.setProperty(STATUS_LEVEL_PROPERTY, level)
    label.setProperty(STATUS_BOLD_PROPERTY, bold)
    style = status_style(level, label, bold=bold)
    if label.styleSheet() != style:
        label.setStyleSheet(style)


def reapply_status_styles(root: QWidget) -> int:
    """Choose every status colour under ``root`` again; return how many labels.

    For a widget's ``changeEvent`` on any of :data:`PALETTE_EVENTS`: each
    ``QLabel`` below ``root`` that :func:`apply_status_style` coloured is
    coloured again for the palette in force now. A label that was never given
    a level is left alone. The count is for the tests, so a sweep that found no
    label cannot read as one that fixed them all.
    """
    count = 0
    for label in root.findChildren(QLabel):
        level = label.property(STATUS_LEVEL_PROPERTY)
        if not isinstance(level, str) or not level:
            continue
        bold = label.property(STATUS_BOLD_PROPERTY)
        apply_status_style(label, level, bold=bold if isinstance(bold, bool) else True)
        count += 1
    return count


#: For a secondary line that should read as quieter than the main text. It
#: keeps the TEXT colour — dimming it is what made the "Example:" line
#: illegible — and de-emphasises with italics instead.
SECONDARY_STYLE: Final[str] = "QLabel { font-style: italic; }"
