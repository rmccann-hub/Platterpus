"""A QDialog base that centres itself on the parent window when first shown.

Real-user report (2026-06-30): on a multi-monitor desktop a first-run modal
popped up on a *different* screen from the main window, so the (application-
modal) window correctly refused all input but the user couldn't see why — it
looked frozen and unclickable. Qt/KDE place a new top-level on the screen under
the cursor or the primary screen, not necessarily over the window the user is
looking at.

Centring every dialog on its parent window puts the prompt where the user's
attention already is. It's best-effort: a no-op under native Wayland (clients
can't position themselves — the app prefers XWayland, where ``move()`` works),
and a no-op in headless tests that construct a dialog but never show it.
"""

from __future__ import annotations

from PySide6.QtCore import QRect
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QApplication, QDialog, QWidget


def _clamp_to(frame: QRect, avail: QRect) -> QRect:
    """Slide `frame` (never resize it) so it lies fully within `avail`.

    Pure and side-effect-free so it's unit-testable without a display. If the
    dialog fits, its edge is pushed just inside the nearest boundary it overran;
    if it's somehow larger than the available area, its top-left is pinned to the
    top-left so at least the title bar and buttons stay reachable. This is the
    guard that keeps a dialog centred on a window near a screen edge — or at a
    global coordinate XWayland reports oddly on a multi-monitor/scaled desktop —
    from landing partly or fully off-screen (real-user "dialog off screen").
    """
    r = QRect(frame)
    # QRect.right() == left + width - 1, so the largest left that still fits is
    # avail.right() - width + 1.
    if r.width() <= avail.width():
        left = min(max(r.left(), avail.left()), avail.right() - r.width() + 1)
    else:
        left = avail.left()
    if r.height() <= avail.height():
        top = min(max(r.top(), avail.top()), avail.bottom() - r.height() + 1)
    else:
        top = avail.top()
    r.moveTo(left, top)
    return r


def center_on_anchor(widget: QWidget) -> None:
    """Place `widget` over its parent window, clamped on-screen, and raise it.

    Moves the dialog to the centre of its parent window (or the active window /
    screen), clamps it fully onto the visible screen, then raises it to the front
    and gives it focus — so it opens where the user is looking, fully visible, and
    not buried behind other windows.

    Best-effort and never raises: a no-op under native Wayland (clients can't
    position themselves — the app prefers XWayland, where ``move()`` works) and
    in headless tests that construct a dialog but never show it. Shared by
    :class:`CenteredDialog` and the app-wide ``auto_center`` filter (which
    catches ``QMessageBox`` and other dialogs that don't subclass this).
    """
    try:
        parent = widget.parentWidget()
        anchor = parent.window() if parent is not None else QApplication.activeWindow()
        frame = widget.frameGeometry()
        if anchor is not None and anchor is not widget:
            frame.moveCenter(anchor.frameGeometry().center())
        else:
            screen = widget.screen() or QApplication.primaryScreen()
            if screen is None:
                return
            frame.moveCenter(screen.availableGeometry().center())
        # Clamp to whichever screen the centred position lands on (screenAt
        # returns None when the point is off ALL screens — exactly the bug — so
        # fall back to the anchor's/widget's screen and pull the dialog back on).
        center = frame.center()
        screen = (
            QApplication.screenAt(center)
            or (anchor.screen() if anchor is not None else None)
            or widget.screen()
            or QApplication.primaryScreen()
        )
        if screen is not None:
            frame = _clamp_to(frame, screen.availableGeometry())
        widget.move(frame.topLeft())
        # Surface it to the FRONT and give it focus. Centring alone isn't enough:
        # a real-user report had the (correctly parented) prompt open on the main
        # window's monitor but BEHIND other windows, so it looked like nothing
        # happened until they clicked the main window to raise its child. raise_()
        # fixes the stacking; activateWindow() gives it keyboard focus. Best-effort
        # — the compositor may override under focus-stealing prevention.
        widget.raise_()
        widget.activateWindow()
    except Exception:  # noqa: BLE001 — placement is cosmetic, never fatal
        pass


class CenteredDialog(QDialog):
    """``QDialog`` that moves itself over its parent window on first show."""

    _centered_once: bool = False

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 — Qt override
        super().showEvent(event)
        if self._centered_once:
            return
        self._centered_once = True
        center_on_anchor(self)
