"""Two scrolling rules the whole UI obeys, in one place.

Both were reported by the maintainer on 2026-08-13, and both are cases of a
widget deciding something on the user's behalf.

**1. A scroll gesture must never change a value.** Qt's default is that a
``QSpinBox`` / ``QComboBox`` / ``QSlider`` under the pointer swallows the wheel
event and *increments itself* — so scrolling the Settings page past a control
silently edits it. The maintainer hit exactly this: *"the scrolling on the
settings page, I have accidentally scrolled down on options I did not mean to."*

For most apps that is an annoyance. Here it is a **data-integrity** defect, and
that is why this is a guard rather than a polish item: a nudged
``read_offset`` or ``secure_rerip_matches`` rips the **next disc wrong** and
looks completely normal doing it — no error, no warning, a clean-looking log
with the wrong offset baked into every sample. Settings that reach cyanrip's
argv are not preferences, they are calibration.

The fix is the standard one and it keeps deliberate edits working: ignore the
wheel unless the widget already holds keyboard focus. Click (or Tab) into a spin
box and the wheel adjusts it as always; scroll *past* one and the page scrolls.

**2. A log pane must not yank you back to the bottom.** Appending text scrolls
the view to the end, which is right when you are following a live run and wrong
the moment you scroll up to read something — the next line drags you away.
"Sticky bottom" is the settled answer: remember whether the scrollbar was
already at the maximum *before* appending, and only restore it to the maximum if
it was. Scrolled up → your position is kept. At the bottom → it follows.

Neither rule is Platterpus-specific, which is why they live here and are applied
by sweep rather than one widget at a time (`CLAUDE.md`: enforce a rule across
the codebase, not at the place it was learned).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import (
    QAbstractSlider,
    QAbstractSpinBox,
    QComboBox,
    QPlainTextEdit,
    QTextEdit,
    QWidget,
)

#: Widget types that steal the wheel and change their own value doing it.
#: `QAbstractSpinBox` covers QSpinBox / QDoubleSpinBox / QDateTimeEdit;
#: `QAbstractSlider` covers QSlider / QDial — but NOT QScrollBar, which is
#: excluded below because a scrollbar consuming the wheel is the entire point.
VALUE_STEALERS: tuple[type[QWidget], ...] = (
    QAbstractSpinBox,
    QComboBox,
    QAbstractSlider,
)


class WheelGuard(QObject):
    """Event filter: a value widget ignores the wheel unless it has focus.

    Install once on a dialog and call :func:`protect_value_widgets`; it filters
    every descendant, so a control added later is covered as long as the sweep
    runs after construction.

    **Why focus and not "always ignore".** Always-ignore would break the
    keyboard-and-wheel workflow of someone deliberately dialling a number in.
    Focus is the signal that the user chose this widget — which is exactly the
    distinction between "I am editing this" and "I am scrolling past it".
    """

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() is not QEvent.Type.Wheel:
            return False
        if not isinstance(watched, VALUE_STEALERS):
            return False
        from PySide6.QtWidgets import QScrollBar

        if isinstance(watched, QScrollBar):
            return False  # a scrollbar SHOULD eat the wheel
        if watched.hasFocus():
            return False  # deliberate adjustment — let it through
        # Refuse it AND hand it up, so the scroll area still scrolls. Without
        # `ignore()` the gesture would be swallowed and the page would feel dead
        # over every control, which is a different bug with the same cause.
        event.ignore()
        return True


def protect_value_widgets(root: QWidget, guard: WheelGuard | None = None) -> WheelGuard:
    """Install :class:`WheelGuard` on ``root`` and every value widget under it.

    Returns the guard so the caller can retain it — an event filter whose last
    Python reference is dropped stops filtering, silently, which would look
    exactly like the fix never landing.
    """
    guard = guard or WheelGuard(root)
    for widget in root.findChildren(QWidget):
        if isinstance(widget, VALUE_STEALERS):
            widget.installEventFilter(guard)
    return guard


def append_keeping_position(view: QPlainTextEdit | QTextEdit, text: str) -> None:
    """Append ``text``, following the tail only if the view was already at it.

    The check must happen **before** the append: once the document has grown,
    `maximum()` has already moved and "were we at the bottom?" is unanswerable.
    That ordering is the whole trick, and getting it backwards produces a
    version that looks correct and always scrolls.
    """
    bar = view.verticalScrollBar()
    was_at_bottom = bar is None or bar.value() >= bar.maximum() - 2
    previous = bar.value() if bar is not None else 0
    if isinstance(view, QPlainTextEdit):
        view.appendPlainText(text)
    else:
        view.append(text)
    if bar is None:
        return
    bar.setValue(bar.maximum() if was_at_bottom else previous)
