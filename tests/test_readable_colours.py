"""Every coloured line of text is readable on light AND dark themes.

**The defect this gates** (measured 2026-09-23, after the maintainer reported the
Settings "Example:" line as hard to read): every status colour in the app was a
fixed hex value commented as reading "on both light and dark Qt palettes", and on
Breeze Dark — Bazzite's default — the rip verdict's green measured 3.1:1, the
amber warning 3.2:1, and three secondary lines drawn in `palette(mid)` about
1.1:1. WCAG 2.2 AA, which this project targets, is 4.5:1 for normal text.

Two halves, the same shape as the handshake's input/output checks:

* the NUMBERS — every variant against every background on its side, computed;
* the SOURCE — no string literal in the UI may carry a raw hex colour or
  `palette(mid)`, because a colour chosen at a call site is one nobody measured.
  String literals only (read with `ast`), so a comment that explains the history
  does not trip it.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QLabel

from platterpus.ui import status_colours as sc

UI: Path = Path(__file__).resolve().parents[1] / "src" / "platterpus" / "ui"

#: WCAG 2.2 AA, normal-size text.
AA_TEXT: float = 4.5


@pytest.mark.parametrize(
    ("variants", "backgrounds"),
    [
        (sc.LIGHT_VARIANTS, sc.LIGHT_BACKGROUNDS),
        (sc.DARK_VARIANTS, sc.DARK_BACKGROUNDS),
    ],
    ids=["light", "dark"],
)
def test_every_variant_meets_AA_on_every_background_on_its_side(
    variants: dict[str, str], backgrounds: tuple[str, ...]
) -> None:
    failures = [
        f"{level} {colour} on {bg}: {sc.contrast_ratio(colour, bg):.2f}:1"
        for level, colour in variants.items()
        for bg in backgrounds
        if sc.contrast_ratio(colour, bg) < AA_TEXT
    ]
    assert not failures, failures


def test_both_sides_define_the_same_levels() -> None:
    """A level present on one side only would fall back silently on the other."""
    assert set(sc.LIGHT_VARIANTS) == set(sc.DARK_VARIANTS)
    assert {"ok", "warn", "neutral", "error"} <= set(sc.LIGHT_VARIANTS)


def test_the_colours_that_shipped_would_fail_this_test() -> None:
    """Non-triviality: the old fixed values, on Breeze Dark, must be refused."""
    shipped = ("#1a7f37", "#9a6700", "#57606a", "#c0392b", "#b9770e")
    assert all(sc.contrast_ratio(c, "#202326") < AA_TEXT for c in shipped)


def _palette(window: str) -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(window))
    return palette


def test_the_variant_follows_the_window_colour(qapp: QApplication) -> None:
    del qapp
    for bg in sc.DARK_BACKGROUNDS:
        assert sc.palette_is_dark(_palette(bg)), bg
        assert sc.status_colour("ok", _palette(bg)) == sc.DARK_VARIANTS["ok"]
    for bg in sc.LIGHT_BACKGROUNDS:
        assert not sc.palette_is_dark(_palette(bg)), bg
        assert sc.status_colour("ok", _palette(bg)) == sc.LIGHT_VARIANTS["ok"]


def test_a_label_gets_the_variant_for_ITS_palette(qapp: QApplication) -> None:
    """The style is computed from the widget it will be drawn on."""
    del qapp
    label = QLabel()
    label.setPalette(_palette("#202326"))
    assert sc.DARK_VARIANTS["warn"] in sc.status_style("warn", label)
    label.setPalette(_palette("#eff0f1"))
    assert sc.LIGHT_VARIANTS["warn"] in sc.status_style("warn", label)


_HEX: re.Pattern[str] = re.compile(r"#[0-9a-fA-F]{6}\b")


def test_no_ui_string_carries_an_unmeasured_colour() -> None:
    """The source half: colours come from `status_colours` or not at all."""
    offenders: list[str] = []
    examined = 0
    for path in sorted(UI.rglob("*.py")):
        if path.name == "status_colours.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                examined += 1
                text = node.value
                if "palette(mid)" in text or (
                    _HEX.search(text) and ("color" in text or "border" in text)
                ):
                    offenders.append(
                        f"{path.relative_to(UI)}:{node.lineno}: {text[:60]!r}"
                    )
    assert examined > 500, f"only {examined} UI strings examined — the scan broke"
    assert not offenders, (
        "UI strings choosing a colour that no test measured — use "
        "`ui/status_colours.py`:\n  " + "\n  ".join(offenders)
    )
