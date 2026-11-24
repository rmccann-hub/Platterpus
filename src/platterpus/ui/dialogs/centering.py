"""A QDialog base that centres itself on its parent window, and fits its content
and the screen, when first shown.

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

import logging

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from platterpus.ui.dialogs.fit_scroll_area import SIDE_MARGIN_PX, fit_dialog_to_screen
from platterpus.ui.dialogs.stacking import stack_above_window_it_blocks

log = logging.getLogger(__name__)


#: True while windows must appear WITHOUT taking focus or jumping to the front:
#: a `--run-script` launch, and any scripted run while it runs (the owner,
#: 2026-11-24: *"they should run on their own ... and also not interrupt a user
#: with bringing windows and things to the front"*). A scripted run opens and
#: closes dozens of dialogs; with this off, each one took the keyboard from
#: whatever the person was doing in another program. A plain module flag, read
#: and written on the GUI thread only. Set through :func:`present_quietly`.
_present_quietly: bool = False

#: The window property Qt's X11 (xcb) plugin reads at the moment it maps a
#: window: true sends `_NET_WM_USER_TIME` 0, which tells the window manager
#: "this window was not asked for by a click; do not give it focus". It is how
#: `Qt.WA_ShowWithoutActivating` reaches the window manager, set here directly
#: as well because the attribute alone is copied to the window only when the
#: native window is created, and a dialog shown a second time already has one.
SHOW_WITHOUT_ACTIVATING_PROPERTY: str = "_q_showWithoutActivating"


def present_quietly(enabled: bool) -> None:
    """Turn quiet presentation on or off for every window shown from now on."""
    global _present_quietly  # one process-wide switch, GUI thread only
    if enabled != _present_quietly:
        log.info(
            "windows now %s",
            "open without taking focus or coming to the front (a scripted run)"
            if enabled
            else "open normally, in front and focused",
        )
    _present_quietly = enabled


def presenting_quietly() -> bool:
    """Whether windows are being shown without taking focus (see the flag)."""
    return _present_quietly


def mark_show_without_activating(widget: QWidget) -> None:
    """In quiet mode, make ``widget`` appear without taking focus. Never raises.

    Called from the window's Show event, which Qt delivers before it maps the
    window, so the window manager hears it in time (`stacking.py` relies on the
    same ordering). Does nothing outside quiet mode.
    """
    if not _present_quietly:
        return
    try:
        widget.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        handle = widget.windowHandle()
        if handle is not None:
            handle.setProperty(SHOW_WITHOUT_ACTIVATING_PROPERTY, True)
    except RuntimeError:
        # A wrapper whose C++ object is already gone: nothing left to show.
        log.debug("could not mark a window whose C++ side is already gone")


def bring_to_front(widget: QWidget) -> None:
    """Raise ``widget`` and give it focus, except in quiet mode. Never raises.

    The one place the app asks for the front. In quiet mode it does nothing:
    the window is already shown (and stacked above the window it blocks, by
    `stacking.py`), and taking the keyboard from another program is exactly
    what a scripted run must not do.
    """
    if _present_quietly:
        return
    try:
        widget.raise_()
        widget.activateWindow()
    except RuntimeError:
        log.debug("could not raise a window whose C++ side is already gone")


def _clamp_to(frame: QRect, avail: QRect, side_margin: int = 0) -> QRect:
    """Slide `frame` (never resize it) so it lies fully within `avail`.

    Pure and side-effect-free so it's unit-testable without a display. If the
    dialog fits, its edge is pushed just inside the nearest boundary it overran;
    if it's somehow larger than the available area, its top-left is pinned to the
    top-left so at least the title bar and buttons stay reachable. This is the
    guard that keeps a dialog centred on a window near a screen edge — or at a
    global coordinate XWayland reports oddly on a multi-monitor/scaled desktop —
    from landing partly or fully off-screen (real-user "dialog off screen").

    Up to ``side_margin`` is kept clear on the left and the right too — as much
    of it as the frame's width leaves room for, equally on both sides
    (2026-10-05, KDD-41). The reason is the frame itself: a window is placed on
    its first show, usually before the window manager has decorated it, so the
    `frame` measured here is often just the window, and a window slid flush
    against the screen's edge then has its border off it. The fit
    (`fit_scroll_area.SIDE_MARGIN_PX`) leaves room for this margin on both
    sides; this is what keeps a window centred on an anchor near the edge from
    giving that room back.
    """
    r = QRect(frame)
    inset = max(0, min(side_margin, (avail.width() - r.width()) // 2))
    avail = avail.adjusted(inset, 0, -inset, 0)
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
            frame = _clamp_to(frame, screen.availableGeometry(), SIDE_MARGIN_PX)
        widget.move(frame.topLeft())
        # Surface it to the FRONT and give it focus. Centring alone isn't enough:
        # a real-user report had the (correctly parented) prompt open on the main
        # window's monitor but BEHIND other windows, so it looked like nothing
        # happened until they clicked the main window to raise its child. raise_()
        # fixes the stacking; activateWindow() gives it keyboard focus. Best-effort
        # — the compositor may override under focus-stealing prevention. Not
        # in a scripted run: `bring_to_front` explains why.
        bring_to_front(widget)
    except Exception:  # noqa: BLE001, S110 — placement is cosmetic, never fatal
        pass


def _result_word(result: int) -> str:
    """``"accepted"`` / ``"rejected or closed"`` / the raw code.

    Qt maps a window-manager close and ``Esc`` onto ``Rejected``, so those two are
    genuinely indistinguishable at this level and the wording says so instead of
    picking one. A custom ``done(N)`` code is reported verbatim rather than
    bucketed into "rejected", which would be a claim we do not have.
    """
    if result == QDialog.DialogCode.Accepted:
        return "accepted"
    if result == QDialog.DialogCode.Rejected:
        return "rejected or closed"
    return f"result={result}"


class CenteredDialog(QDialog):
    """``QDialog`` that moves itself over its parent window on first show.

    It also **logs its own lifecycle** — presented, and closed with which result.
    That is not decoration. A modal dialog stops the whole application until the
    user answers it, so from a log's point of view "waiting for a human" and
    "wedged" are the same silence — and the maintainer closed the app during one
    of those silences (96 seconds, 2026-08-05) because it *"looked hung"*. The
    release picker's call site logged nothing on any branch: not opened, not
    waiting, not accepted, not cancelled. So the artifact could not answer even
    the first question, whether the dialog had been put on screen at all.

    The lines live **here**, on the shared base, rather than at the one call site
    that was found wanting — ``docs/testing.md`` §5.o, *enforce a rule across the
    codebase, not at the place it was learned*. Every dialog in the app inherits
    from this class, so every one of them now leaves a trace, and a future modal
    cannot reintroduce the hole by forgetting.

    ``showEvent`` fires when Qt actually maps the window, which makes its line
    *evidence the dialog was presented* — a stronger claim than a log line before
    ``exec()``, which only proves we asked.
    """

    _centered_once: bool = False
    _width_floor_applied: bool = False

    #: The width a dialog gets when it does not choose one.
    #:
    #: **Word-wrapped prose with no width is an unpredictable dialog.** A
    #: `QLabel` with `setWordWrap(True)` has a height-for-width policy, so with no
    #: width to wrap to Qt takes one from whatever else is in the layout — and in
    #: this app that is usually a `QRadioButton` or a `QCheckBox`, whose label
    #: does NOT wrap. The dialog therefore ends up as wide as its longest
    #: unwrappable line, and the paragraphs reflow to that: a build label like
    #: `approved: 2cce60d (platterpus-fork-g2cce60d)` stretches the whole window,
    #: while a dialog with no such control collapses and goes very tall.
    #: Real-user report, 2026-09-21, on the cyanrip build picker: *"window sizing
    #: is wrong."*
    #:
    #: 560 px matches the settled dialogs: the setup wizard opens at 580 with a
    #: 480 minimum, the uninstaller and drive setup are in the same band. Chosen
    #: to sit inside that range rather than invent a number.
    #:
    #: **A MINIMUM, not a fixed size**, and only applied when the subclass has not
    #: set one — so a dialog that knows its own shape keeps it, and this is a
    #: floor for the ones that never thought about it rather than a value imposed
    #: on the ones that did. `CLAUDE.md`'s *"an explicit size is a size you own"*
    #: cuts both ways: the four dialogs that set nothing were not exercising Qt's
    #: default deliberately, they had simply never been sized.
    DEFAULT_MINIMUM_WIDTH: int = 560

    #: Kept clear of the panel/taskbar and the window frame. The value Settings
    #: measured for the same job (`SettingsDialog._SCREEN_MARGIN_PX`):
    #: `availableGeometry` excludes reserved struts on most desktops but not the
    #: frame Qt adds around the dialog, and an OK button sitting exactly on the
    #: screen edge is the same defect in a milder form.
    SCREEN_MARGIN_PX: int = 64

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 — Qt override
        # Applied HERE rather than in `__init__` because a subclass populates its
        # layout after calling `super().__init__()`, so at construction time there
        # is nothing to measure and `minimumWidth()` is still Qt's placeholder.
        # First show is the first moment the question "did this dialog choose a
        # width?" has a real answer.
        if not self._width_floor_applied:
            self._width_floor_applied = True
            if (
                self.minimumWidth() < self.DEFAULT_MINIMUM_WIDTH
                and not self.isMaximized()
            ):
                self.setMinimumWidth(self.DEFAULT_MINIMUM_WIDTH)
            if not self.isMaximized():
                self._fit_content_to_screen()
        super().showEvent(event)
        # On EVERY show, before the first-show-only placement: a question opened
        # over another window of ours is stacked above that window (TASKS R96).
        stack_above_window_it_blocks(self)
        if self._centered_once:
            return
        self._centered_once = True
        # INFO, not DEBUG: this must be in a default-level log, because the user
        # who needs it is the one who could not tell a prompt from a freeze.
        log.info(
            "dialog presented: %s (%r) — the app now waits for the user",
            type(self).__name__,
            self.windowTitle(),
        )
        center_on_anchor(self)

    def available_screen_size(self) -> QSize:
        """Usable area of the screen this dialog is on, or a small fallback.

        A method so a test can constrain it, and the same shape as
        `SettingsDialog.available_screen_size`, which this generalises. The
        fallback is deliberately SMALL: guessing big on a headless or odd-screen
        host would reproduce the very bug the fit exists to prevent, while a dialog
        that opens smaller than it needed to is merely scrollable.
        """
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return QSize(1024, 720)
        return screen.availableGeometry().size()

    def _fit_content_to_screen(self) -> None:
        """Size to the content and the screen — see :func:`fit_dialog_to_screen`."""
        fit_dialog_to_screen(self, self.available_screen_size(), self.SCREEN_MARGIN_PX)

    def done(self, result: int) -> None:
        """Log how the dialog closed, then close it.

        ``done`` is the single funnel Qt routes ``accept()``, ``reject()``, the
        window-manager close button and ``Esc`` through, so one override here
        covers every exit — which a pair of ``accepted``/``rejected`` connections
        would not.
        """
        log.info(
            "dialog closed: %s (%r) — %s",
            type(self).__name__,
            self.windowTitle(),
            _result_word(result),
        )
        super().done(result)
