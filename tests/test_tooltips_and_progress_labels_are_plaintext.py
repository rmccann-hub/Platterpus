"""A tooltip or a progress dialog's label shows outside text as written, never markup.

Peer review 2.6 (the claude-code-skills session, 2026-10-26) asked that every Qt
surface showing a title, an artist, a track name or a server's message render it
as plain text. Labels and message boxes are swept by three files already
(`test_labels_state_their_text_format.py`, `test_labels_given_text_later_state_
their_format.py`, `test_message_boxes_are_plaintext.py`). Two surfaces were outside
all three, because they have no format to state and Qt guesses
(`ui/plain_text.py` says how): `setToolTip(...)`, and the label a
`QProgressDialog` builds for itself. This file is their sweep.

**The population, and its floors.** Every `setToolTip(<argument>)` call in
`src/platterpus` whose argument is not a string literal must be
`plain_tooltip(...)`. A literal is ours and cannot change under the call, so it
is outside; anything else is a value, and "this value is ours" is a claim about
every future edit, not about today's. Every `QProgressDialog(...)` construction
must be inside `ui/plain_text.py`. The scan must find at least the counts measured
on 2026-10-26 before its verdict means anything.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

import pytest
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QApplication, QWidget

from platterpus.ui.plain_text import plain_progress_dialog, plain_tooltip

SRC: Final[Path] = Path(__file__).resolve().parents[1] / "src" / "platterpus"

#: Non-literal `setToolTip` sites measured 2026-10-26: six (four in the results
#: table of `ui/rip_progress.py`, the dependency status label, the Start button).
_MIN_VALUE_TOOLTIPS: Final[int] = 6
#: Every `setToolTip` call, literal or not, so the scan cannot pass by missing
#: the whole population (about forty literal sites on 2026-10-26).
_MIN_ALL_TOOLTIPS: Final[int] = 30

#: Text a server, a disc or a dependency could hand us, each one markup to Qt.
_HOSTILE: Final[tuple[str, ...]] = (
    "<b>bold</b> & co",
    "TSST <corp> & Co",
    "<a href='file:///etc/passwd'>click</a>",
    "<img src=x>",
    "&lt;already escaped&gt;",
)


def _calls(name: str) -> list[tuple[Path, ast.Call]]:
    found: list[tuple[Path, ast.Call]] = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            called = (
                func.attr
                if isinstance(func, ast.Attribute)
                else func.id
                if isinstance(func, ast.Name)
                else ""
            )
            if called == name:
                found.append((path, node))
    return found


def _is_literal(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _is_plain_tooltip_call(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "plain_tooltip"
    )


def test_every_tooltip_built_from_a_value_goes_through_plain_tooltip() -> None:
    sites = _calls("setToolTip")
    valued = [(p, c) for p, c in sites if c.args and not _is_literal(c.args[0])]
    offenders = [
        f"{p.relative_to(SRC)}:{c.lineno}"
        for p, c in valued
        if not _is_plain_tooltip_call(c.args[0])
    ]
    assert len(sites) >= _MIN_ALL_TOOLTIPS, len(sites)
    assert len(valued) >= _MIN_VALUE_TOOLTIPS, len(valued)
    assert not offenders, (
        "these tooltips show a value Qt may read as markup; wrap it in "
        f"ui.plain_text.plain_tooltip(...): {offenders}"
    )


def test_every_progress_dialog_is_built_with_a_plaintext_label() -> None:
    sites = _calls("QProgressDialog")
    outside = [
        f"{p.relative_to(SRC)}:{c.lineno}"
        for p, c in sites
        if p.name != "plain_text.py"
    ]
    assert sites, "floor: the one sanctioned construction must be found"
    assert not outside, (
        "build progress dialogs with ui.plain_text.plain_progress_dialog, whose "
        f"label is PlainText: {outside}"
    )


# --- behaviour: what a reader actually sees -----------------------------------


@pytest.mark.parametrize("text", _HOSTILE)
def test_a_tooltip_shows_every_character_as_written(text: str) -> None:
    """Qt renders a tooltip as rich text when it guesses so; ours always says
    exactly ``text``."""
    doc = QTextDocument()
    doc.setHtml(plain_tooltip(text))
    assert doc.toPlainText() == text


def test_the_unescaped_tooltip_WOULD_be_read_as_markup() -> None:
    """The floor: without the wrapper, Qt drops the tags (so the test above is
    not passing against a renderer that never interprets markup)."""
    doc = QTextDocument()
    doc.setHtml(_HOSTILE[0])
    assert doc.toPlainText() != _HOSTILE[0]


def test_an_empty_tooltip_stays_empty() -> None:
    """Qt shows no tooltip for "", and the results table relies on that."""
    assert plain_tooltip("") == ""


def test_the_progress_dialog_label_never_guesses(qapp: QApplication) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel

    parent = QWidget()
    dialog = plain_progress_dialog("<b>9.9.9</b>", "Cancel", 0, 100, parent)
    labels = dialog.findChildren(QLabel)
    assert labels and all(
        label.textFormat() == Qt.TextFormat.PlainText for label in labels
    )
    dialog.setLabelText("Verifying <i>x</i>")
    assert any(label.text() == "Verifying <i>x</i>" for label in labels)
    assert dialog.maximum() == 100
    dialog.close()
    dialog.deleteLater()
    parent.deleteLater()
