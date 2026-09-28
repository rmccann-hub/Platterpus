"""Qt's stock message boxes, with the text always shown exactly as written.

**Why this module exists.** Qt's static helpers (``QMessageBox.warning(...)``,
``.information(...)``, ``.critical(...)``, ``.question(...)``) build their box
with Qt's default text format, ``Qt.TextFormat.AutoText``, and give the caller no
way to change it. Under AutoText, Qt guesses (``Qt::mightBeRichText``) whether
the text is HTML: if its first line holds a tag Qt's HTML parser knows (``<b>``,
``<p>``, ``<a …>``, …) or an ``&lt;``, the WHOLE message is rendered as markup.
Measured on Qt 6.11: every line break collapses into a space, a tag it does not
know (``<stdin>``) disappears, and ``&amp;`` turns into ``&``, **without a
word**. The user sees a different, shorter message and has no way to know
anything was changed.

For a sentence we wrote, that never happens. For a box that carries what a
DEPENDENCY told us, it can: the dependency summary lists each tool's version and
build tag and the install errors built from a tool's own stderr; the update box
names a version GitHub reported; the read-offset box names the drive's own vendor
and model. Critical rule #12 says every widget carrying dependency output is
PlainText, and a box built by a static helper cannot be. So the product uses no
static helper at all. Every stock box goes through the four functions below,
which build the box the static helper would have built and pin PlainText before
it is shown.

**The contract is Qt's, on purpose.** Each function takes the static helper's
arguments in the static helper's order (parent, title, text, then optionally the
buttons and the default button) and returns the same ``QMessageBox.StandardButton``
the static helper would. Moving a call site here is a change of name only: the
title, the text, the buttons, the default and the answer the caller reads are all
unchanged. Only the text format moves.

**One construction, testable without a modal.** :func:`build` is the box on its
own, returned unshown, so a test can read its text format without opening it.
Opening it (``exec``) blocks forever on the headless test platform, which is why
``tests/conftest.py`` gives the four functions non-blocking answers in every test.

**Enforced, not trusted.** ``tests/test_message_boxes_are_plaintext.py`` refuses
a static helper anywhere else in the package, and reads ``textFormat()`` off the
box :func:`build` returns for every kind.

GUI thread only, like every widget. ``exec()`` runs a nested event loop, so the
window keeps painting while the box is open; the slot that called it simply waits
for the answer.
"""

from __future__ import annotations

import logging
from typing import Final

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QWidget

log = logging.getLogger(__name__)

#: The lowest and highest standard-button bits. Qt's static helper walks the bits
#: between them in this order, adding each button asked for, and the order matters:
#: when no default button is named, the FIRST accept-role button it meets becomes
#: the default. :func:`build` walks them the same way so it picks the same one.
_FIRST_BUTTON_BIT: Final[int] = QMessageBox.StandardButton.FirstButton.value
_LAST_BUTTON_BIT: Final[int] = QMessageBox.StandardButton.LastButton.value


def build(
    icon: QMessageBox.Icon,
    parent: QWidget | None,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
) -> QMessageBox:
    """Build, but do not show, the box a static helper would, with PlainText text.

    ``icon`` is the one thing that tells the four kinds apart (``information``
    shows ``Icon.Information``, and so on). The rest is the static helper's own
    argument list, handled the way Qt handles it:

    * each button in ``buttons`` is added, lowest bit first;
    * ``default_button`` becomes the default. When it is ``NoButton``, the first
      button with the accept role does, which is what Qt does (a lone OK is the
      default; Yes/No has no accept-role button, so neither is);
    * a ``default_button`` that is not among ``buttons`` is added to them. Qt's
      static helper shows it too, through its Qt 4 compatibility path, so the
      button a caller named as the default never silently goes missing.

    The escape button is not set here, and neither does Qt set it: the box works
    it out when it is shown (Cancel if present, else the one No-like button, else
    a lone button), so Esc answers the same as it would for the static helper.
    """
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    # THE line this module exists for. Set before the text, so the text never
    # spends a moment under AutoText, where a `<` in it would be read as markup.
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.setText(text)

    wanted = buttons
    if default_button != QMessageBox.StandardButton.NoButton and not (
        buttons & default_button
    ):
        wanted = buttons | default_button

    default_chosen = False
    bit = _FIRST_BUTTON_BIT
    while bit <= _LAST_BUTTON_BIT:
        if wanted & bit:
            standard = QMessageBox.StandardButton(bit)
            button = box.addButton(standard)
            # Only the first match counts, exactly as in Qt's own loop.
            if not default_chosen and (
                standard == default_button
                or (
                    default_button == QMessageBox.StandardButton.NoButton
                    and box.buttonRole(button) == QMessageBox.ButtonRole.AcceptRole
                )
            ):
                box.setDefaultButton(button)
                default_chosen = True
        bit <<= 1
    return box


def _run_modal(box: QMessageBox) -> QMessageBox.StandardButton:
    """Show ``box`` until it is answered and return what Qt's static helper would.

    The answer is the standard button that closed the box. Esc, and the window's
    own close button, count as a press of the box's escape button, as they do for
    the static helper; a box closed with no button at all answers ``NoButton``.
    (Qt's static helper also turns an ``exec()`` result of -1 into Cancel. That is
    Qt refusing a second, recursive ``exec()`` of a box already open, and a box
    built fresh for this one call cannot be open already, so it cannot happen.)
    """
    box.exec()
    try:
        answer = box.standardButton(box.clickedButton())
    except RuntimeError:
        # Qt already destroyed the box (Shiboken's "Internal C++ object already
        # deleted"): its parent went away while it was open, taking the box with
        # it. There is no answer to read, and a missing answer must never read as
        # consent to whatever the box asked, so it answers NoButton, which no
        # caller treats as a Yes.
        log.warning(
            "a message box was destroyed while it was open, so it has no answer; "
            "reporting NoButton"
        )
        return QMessageBox.StandardButton.NoButton
    # The box is parented to a window that outlives it, so dropping our name for
    # it frees nothing: every box shown would stay behind as a hidden child. Its
    # answer has been read, so hand it back to Qt. (Qt's static helper builds its
    # box on the C++ stack, where it is destroyed as the call returns.)
    box.deleteLater()
    return answer


def information(
    parent: QWidget | None,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
) -> QMessageBox.StandardButton:
    """``QMessageBox.information``, with the text shown as written."""
    return _run_modal(
        build(
            QMessageBox.Icon.Information, parent, title, text, buttons, default_button
        )
    )


def warning(
    parent: QWidget | None,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
) -> QMessageBox.StandardButton:
    """``QMessageBox.warning``, with the text shown as written."""
    return _run_modal(
        build(QMessageBox.Icon.Warning, parent, title, text, buttons, default_button)
    )


def critical(
    parent: QWidget | None,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
) -> QMessageBox.StandardButton:
    """``QMessageBox.critical``, with the text shown as written."""
    return _run_modal(
        build(QMessageBox.Icon.Critical, parent, title, text, buttons, default_button)
    )


def question(
    parent: QWidget | None,
    title: str,
    text: str,
    # Yes and No when a caller names none: the static helper's own default, and
    # the one place the four functions' signatures differ.
    buttons: QMessageBox.StandardButton = (
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    ),
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
) -> QMessageBox.StandardButton:
    """``QMessageBox.question``, with the text shown as written."""
    return _run_modal(
        build(QMessageBox.Icon.Question, parent, title, text, buttons, default_button)
    )
