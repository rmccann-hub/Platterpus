"""The disc panel's right-click menu: the album's own actions, beside the album.

**Why this exists (maintainer decision, 2026-09-27).** *Set cover art from file…*
acts on the album on screen — the image it picks is used for this disc's next rip
and forgotten when the disc changes — so a global menu was the wrong home for it.
It now lives where the album is shown: right-click the disc panel (the Drive /
MusicBrainz / AccurateRip rows above the track list). For one release it is ALSO
still in Tools, so nobody who learned it there loses it the day it moves; see the
comment beside that entry in ``MainWindow._build_menus``.

**Why this menu REPLACES the value labels' own menu instead of sitting beside
it.** The panel's values are copy-selectable, so a disc ID can go into Picard,
and a selectable ``QLabel`` brings its own right-click menu (Copy / Select All)
that Qt gives no way to extend: ``QLabel`` has no public
``createStandardContextMenu``. Two facts make "beside it" the wrong answer:

* the values cover most of the panel, so a menu that appeared only in the gaps
  between them is a menu most right-clicks would never find; and
* they are the panel's only tab stops, so the Menu key (or Shift+F10) on one of
  them is the keyboard's only way in. A keyboard user who could not reach the
  album's actions from here would have no route at all once the Tools copy goes.

So this menu keeps the label's two items, *Copy* and *Select All*, and adds the
album's actions below them. Nothing the old menu did is lost.

**The album's actions belong to the window, not to this menu.** The window owns
each ``QAction`` and hands it over (``DiscInfoPanel.set_album_actions``); this
menu shows that SAME object. So every place the action appears is one
implementation by construction: one slot, one enabled state, one label. A second
``QAction`` wired to the same slot would agree today and drift the first time
somebody disabled one of them and not the other.

**Why ``popup()``, not ``exec()``.** ``exec()`` runs a nested event loop inside
the slot that opened it, and a queued signal arriving meanwhile is handled inside
that loop — the shape ``docs/architecture.md`` §3.12a records for dialogs. A
context menu does not need to block anything, and ``popup()`` with
``WA_DeleteOnClose`` is exactly how Qt's own ``QLabel`` and ``QLineEdit`` show
theirs.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import QLabel, QMenu, QWidget

#: The accessible name of the menu, which is what a screen reader announces when
#: it opens. It has no visible title — a popup menu never shows one.
ALBUM_MENU_NAME: str = "Album actions"


def build_album_menu(
    parent: QWidget,
    source: QLabel | None,
    album_actions: Sequence[QAction],
    *,
    empty_value: str,
) -> QMenu:
    """Build (but do not show) the menu for a right-click on the disc panel.

    ``source`` is the value label that was right-clicked, or ``None`` for the
    panel's background (a row caption or the gap between rows). A label gets its
    *Copy* and *Select All* first, because those are what its own menu used to
    offer; both are greyed while the label shows ``empty_value`` (the panel's
    "no data yet" placeholder), since copying a dash is never what anyone meant.
    The album's actions follow, as the window's own ``QAction`` objects.

    Mnemonics are unique within this one menu — &Copy, Select &All, and the
    album actions' own letters (Set cover art from &file…) — which is the group
    that counts, because a letter only has to be unique among the items of the
    menu that is open. ``tests/test_ui_conformance.py`` checks it.
    """
    menu = QMenu(parent)
    menu.setAccessibleName(ALBUM_MENU_NAME)
    if source is not None:
        has_value = bool(source.text()) and source.text() != empty_value
        copy_action = menu.addAction("&Copy")
        copy_action.setEnabled(has_value)
        copy_action.triggered.connect(lambda: copy_value(source))
        select_action = menu.addAction("Select &All")
        select_action.setEnabled(has_value)
        select_action.triggered.connect(lambda: select_whole_value(source))
        if album_actions:
            menu.addSeparator()
    for action in album_actions:
        menu.addAction(action)
    return menu


def copy_value(label: QLabel) -> None:
    """Put the label's selection on the clipboard — or, with nothing selected,
    its whole value.

    The label's own *Copy* was greyed until you had dragged across the text. The
    fallback is the useful half of this menu: right-click a disc ID, *Copy*, and
    it is on the clipboard, without the select step a trackpad makes fiddly.
    """
    text = label.selectedText() if label.hasSelectedText() else label.text()
    QGuiApplication.clipboard().setText(text)


def select_whole_value(label: QLabel) -> None:
    """Select all of the label's text, as its own *Select All* did.

    ``setSelection`` counts in UTF-16 code units, which is what Qt strings are,
    while Python's ``len`` counts code points: an album title containing an
    emoji (one code point, two UTF-16 units) would otherwise lose its last
    character from the selection.
    """
    text = label.text()
    label.setSelection(0, len(text.encode("utf-16-le")) // 2)


def popup_album_menu(menu: QMenu, anchor: QWidget, pos: QPoint) -> None:
    """Show ``menu`` at ``pos`` (in ``anchor``'s coordinates) without blocking.

    An empty menu is deleted here rather than handed to ``popup()``. Qt does not
    show an empty popup, so it would never close — and ``WA_DeleteOnClose``
    frees a menu only when it closes, which would leak one ``QMenu`` per
    right-click. (It is empty only on a background right-click before the window
    has handed the panel its album actions.)
    """
    if menu.isEmpty():
        menu.deleteLater()
        return
    menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    menu.popup(anchor.mapToGlobal(pos))
