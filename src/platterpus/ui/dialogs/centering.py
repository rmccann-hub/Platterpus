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

from PySide6.QtCore import QRect, QSize
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QApplication, QDialog, QWidget

log = logging.getLogger(__name__)


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
        """Give wrapped text the height it needs, and never outgrow the screen.

        **Why every dialog, and why here.** Qt sizes a new window from its size
        hint and then caps it at two-thirds of the screen (`adjustedSize`), and a
        word-wrapped `QLabel` will be squeezed below the height its own text needs
        rather than push the window taller — its minimum is one line. So on a
        short *logical* screen (a 1080p panel at 200% scaling is 540 px tall) the
        cyanrip build picker opened 360 px tall with every one of its five
        paragraphs cut off mid-sentence. Real-user report, 2026-09-23. Measured,
        not assumed: the picker came up at exactly two-thirds of a 540, 720 and
        800 px virtual screen, clipping 5, 1 and 1 labels.

        The two halves of the rule already existed, each in ONE dialog:
        `SettingsDialog` clamps itself to the screen, and `DriveSetupDialog`
        refuses to be shorter than its prose. The other thirteen had neither,
        which is `docs/testing.md` §5.o — a rule enforced at the place it was
        learned. So it lives on the base class now.

        **What it does**, on first show only:

        * width is kept, unless it is wider than the screen;
        * height grows to what the content needs AT THAT WIDTH (height-for-width,
          which is the number a wrapped label actually needs — `sizeHint` is
          computed at a different width and is the wrong number), and is capped
          at the screen;
        * an explicit minimum larger than the screen is lowered to fit, because a
          window the user cannot fully see has buttons they cannot reach.

        Content taller than the screen cannot be fitted by resizing; it has to
        scroll. That is what
        :class:`~platterpus.ui.dialogs.fit_scroll_area.FitScrollArea` is for, and
        `tests/test_dialogs_fit_their_content.py` is the gate that finds a dialog
        which needed one and has none.
        """
        avail = self.available_screen_size()
        # The margin is VERTICAL only: it is for the taskbar and the title bar,
        # which is where a dialog loses its buttons. Sideways a chosen width is
        # kept unless it is wider than the screen itself — a dialog that asked
        # for 800 px on an 800 px screen fits, and shrinking it to make room for
        # a margin nobody needs would override a size it chose deliberately.
        max_w = max(avail.width(), 320)
        max_h = max(avail.height() - self.SCREEN_MARGIN_PX, 240)
        if self.minimumWidth() > max_w:
            self.setMinimumWidth(max_w)
        if self.minimumHeight() > max_h:
            self.setMinimumHeight(max_h)
        width = min(max(self.width(), self.minimumWidth()), max_w)
        if self.hasHeightForWidth():
            need = self.heightForWidth(width)
        else:
            need = self.sizeHint().height()
        height = min(max(self.height(), need), max_h)
        if (width, height) != (self.width(), self.height()):
            self.resize(width, height)

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
