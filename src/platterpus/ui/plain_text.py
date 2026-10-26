"""Text from outside the app, shown by the two Qt surfaces that cannot be told PlainText.

**The rule** (Critical rule #12, the inbound half): every widget carrying text we
did not write is ``PlainText``, so a ``<`` in a title, a drive name or a server's
answer is shown as typed and never read as markup. Labels and message boxes state
their format and are swept for it (``tests/test_labels_state_their_text_format.py``,
``tests/test_labels_given_text_later_state_their_format.py``,
``tests/test_message_boxes_are_plaintext.py``). Two surfaces have no format to
state, and guess with ``Qt::mightBeRichText`` instead:

* **A tooltip.** ``setToolTip`` takes no format. A tooltip quoting the ripper's
  own status row (the AccurateRip and Copy CRC cells of the results table) or a
  dependency's version (the status bar) rendered a value holding ``<b>`` as bold
  and dropped the tags. :func:`plain_tooltip` hands Qt rich text it builds itself
  from the plain text, every ``<`` and ``&`` escaped, so the guess is always
  right.
* **A progress dialog's label.** ``QProgressDialog`` builds its own ``QLabel`` in
  ``AutoText``. The update dialog's label shows the version the update server
  named and the update worker's status sentences. :func:`plain_progress_dialog`
  gives the dialog a ``PlainText`` label of ours before any text reaches it.

Peer review 2.6 (the claude-code-skills session, 2026-10-26). Swept by
``tests/test_tooltips_and_progress_labels_are_plaintext.py``.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import Qt as GuiQt  # the Qt namespace that carries QtGui's functions
from PySide6.QtWidgets import QLabel, QProgressDialog, QWidget


def plain_tooltip(text: str) -> str:
    """``text`` as a tooltip shows it: every character as written, never markup.

    Empty stays empty, because Qt shows no tooltip for an empty string and callers
    rely on that to show none. Otherwise Qt's own ``convertFromPlainText`` wraps
    the escaped text in ``<p>``, which makes Qt's guess say "rich text" and the
    escaping make that rich text say exactly ``text``. A run of spaces shows as
    one, as rich text always shows it; a line break is kept. Never raises.
    """
    if not isinstance(text, str) or not text:
        return ""
    return GuiQt.convertFromPlainText(text, Qt.WhiteSpaceMode.WhiteSpaceNormal)


def plain_progress_dialog(
    text: str,
    cancel_text: str,
    minimum: int,
    maximum: int,
    parent: QWidget | None,
) -> QProgressDialog:
    """A ``QProgressDialog`` whose label is ``PlainText`` from its first text on.

    The label is ours, set with ``setLabel`` before the text, so every later
    ``setLabelText`` lands in a label that does not guess.
    """
    dialog = QProgressDialog(parent)
    label = QLabel(dialog)
    label.setTextFormat(Qt.TextFormat.PlainText)
    dialog.setLabel(label)
    dialog.setLabelText(text)
    dialog.setCancelButtonText(cancel_text)
    dialog.setRange(minimum, maximum)
    return dialog
