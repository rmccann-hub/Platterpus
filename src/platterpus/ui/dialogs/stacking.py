"""Stack a question above the window it blocks, not only above its parent.

**Why this exists (TASKS R96, the owner's report of 2026-10-28).** *"A dialog or
yes/no question can end up behind a window that cannot be closed until the
question is answered, which locks the app."* A question we ``exec()`` is
APPLICATION-modal: until it is answered, every other window of ours refuses
input. But Qt makes a dialog the *transient* of its parent window, and the
transient is what the window manager stacks by. A question parented to the main
window is kept above the main window, and nothing more. When the window the user
was in is another one (a modal dialog such as the setup wizard, or the modeless
Setup & Updates), that window may stay on top, refusing every click because of a
question underneath it that the user cannot see. Measured with PySide6 6.11
offscreen: a box parented to the main window, shown while another modal dialog
was open, was the transient of the main window, not of the dialog it blocked.

**The fix is the stacking, never the ownership.** The question keeps its parent,
the window it is about, which owns it and which it is centred over. Only its
transient parent changes, to the window it blocks: the newest modal dialog if
one is open, else the active window of ours. A desktop keeps a transient above
the window it belongs to, and lets it take focus from that window, so the
question opens on top of the window the user was looking at.

**Application-modal dialogs only.** A window-modal dialog (``open()``) blocks its
transient parent's chain, so moving its transient parent would change WHICH
windows it blocks; and since it blocks only its own window, the window above it
still answers clicks, so it cannot lock the app. A modeless window blocks
nothing and keeps its parent.

**Asked on every show, not the first.** Qt sets the transient parent back to the
parent window each time the dialog is shown (measured, same build), and the
window in use may be a different one the second time.

Best-effort and never raises, like the centring beside it: a desktop may still
refuse to stack a window, and an exception escaping a Qt event filter would reach
the crash dialog.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QWindow
from PySide6.QtWidgets import QApplication, QWidget

log = logging.getLogger(__name__)


def window_it_blocks(dialog: QWidget) -> QWidget | None:
    """The window ``dialog`` should be stacked above, or ``None`` to leave it.

    The newest modal dialog other than ``dialog`` (still the top of Qt's modal
    stack when ``dialog``'s Show event is delivered, because Qt adds ``dialog`` to
    that stack only when it maps the window), else the active window of ours if
    it is shown. ``None`` when neither exists or the answer is ``dialog`` itself
    or one of its own children.
    """
    candidate = QApplication.activeModalWidget()
    if candidate is None or candidate is dialog:
        candidate = QApplication.activeWindow()
        if candidate is not None and not candidate.isVisible():
            # Qt can go on naming a window that has just closed as the active
            # one (`ui/hold_for_user.py`); a hidden window blocks nothing.
            candidate = None
    if candidate is None:
        return None
    target = candidate.window()
    if target is dialog or dialog.isAncestorOf(target):
        return None
    return target


def _chain_contains(start: QWindow | None, wanted: QWindow) -> bool:
    """True when ``wanted`` is ``start`` or one of its transient ancestors."""
    seen: set[int] = set()
    window = start
    while window is not None and id(window) not in seen:
        if window is wanted:
            return True
        seen.add(id(window))
        window = window.transientParent()
    return False


def stack_above_window_it_blocks(dialog: QWidget) -> None:
    """Make an application-modal ``dialog`` the transient of the window it blocks.

    Called from the dialog's Show event (`CenteredDialog.showEvent`, and the
    app-wide `DialogCenterFilter` for every other dialog), which Qt delivers
    before it maps the window, so the window manager is told before the dialog
    appears. Does nothing for a dialog that is not application-modal.
    """
    try:
        if dialog.windowModality() != Qt.WindowModality.ApplicationModal:
            return
        handle = dialog.windowHandle()
        target = window_it_blocks(dialog)
        if handle is None or target is None:
            return
        target_handle = target.windowHandle()
        if target_handle is None or handle.transientParent() is target_handle:
            return
        if _chain_contains(target_handle, handle):
            return  # it would make the two windows each other's transient
        handle.setTransientParent(target_handle)
        log.info(
            "dialog %r stacked above %r, the window it blocks",
            dialog.windowTitle(),
            target.windowTitle(),
        )
    except RuntimeError:
        # A wrapper whose C++ object is already gone (Shiboken's "Internal C++
        # object already deleted"): there is nothing left to stack.
        log.debug("could not stack a dialog whose window is already gone")
