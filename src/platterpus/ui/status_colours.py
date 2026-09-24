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
"""

from __future__ import annotations

from typing import Final

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QWidget

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


def status_style(level: str, widget: QWidget, *, bold: bool = True) -> str:
    """A ``QLabel`` stylesheet for a status line at ``level`` on ``widget``.

    Takes the widget rather than a palette so a call site cannot pass the wrong
    one: the label's palette is what its text is drawn on.
    """
    weight = " font-weight: bold;" if bold else ""
    colour = status_colour(level, widget.palette())
    return f"QLabel {{ color: {colour};{weight} padding: 2px; }}"


#: For a secondary line that should read as quieter than the main text. It
#: keeps the TEXT colour — dimming it is what made the "Example:" line
#: illegible — and de-emphasises with italics instead.
SECONDARY_STYLE: Final[str] = "QLabel { font-style: italic; }"
