"""The walkthrough's ``callout`` verb, and the hook ``screenshot`` draws it through (KDD-42, W3).

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like the
other ``*_verbs`` modules, so each handler stays reachable as
``runner._do_<verb>`` while the runner file does not grow.

The getting-started guide (KDD-42) is shot by a script on the rig. This verb
and ``record`` are what that script needs beyond ``screenshot``:

* ``callout <n> <label…>`` marks the widget that reads ``<label>`` with the
  number ``<n>``, and the **next** ``screenshot`` draws the mark on its picture
  (:mod:`platterpus.uiscript.callout`). The label must match exactly one visible
  widget, or the step fails naming what it found: a renamed button fails the
  walkthrough rather than shipping a picture that points at nothing.

The frame bursts the guide's GIFs are made from are the other verb,
``record`` (:mod:`platterpus.uiscript.burst_verbs`).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from PySide6.QtCore import QPoint
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QAbstractButton, QApplication, QGroupBox, QLabel

from platterpus.uiscript.callout import (
    MAX_CALLOUT_NUMBER,
    CalloutMark,
    draw_callouts,
    label_matches,
    normalise_label,
)
from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)

#: How many visible labels a failed callout names, to help the script's author.
_LABELS_NAMED_ON_A_MISS: Final[int] = 8


@dataclass
class PendingCallout:
    """A callout waiting for the next ``screenshot``: its number, the widget it
    marks, and the words the script named it by."""

    number: int
    target: QWidget
    wanted: str


def _text_of(widget: QWidget) -> str | None:
    """The words a user reads on ``widget``, for the kinds a callout can name."""
    if isinstance(widget, QAbstractButton):
        return widget.text()
    if isinstance(widget, QGroupBox):
        return widget.title()
    if isinstance(widget, QLabel):
        return widget.text()
    return None


def callout_candidates(wanted: str) -> tuple[list[QWidget], list[str]]:
    """(visible widgets that read ``wanted``, every visible label seen).

    Searched in every top-level window that is on screen, the runner's own test
    of "on screen", so a widget in a hidden dialog can never be marked. The
    second list is what a failed callout names to help the author.
    """
    from platterpus.uiscript.runner import _is_on_screen

    matches: list[QWidget] = []
    seen: list[str] = []
    for window in QApplication.topLevelWidgets():
        if not _is_on_screen(window):
            continue
        for kind in (QAbstractButton, QGroupBox, QLabel):
            for child in window.findChildren(kind):
                text = _text_of(child)
                if not text or not child.isVisible():
                    continue
                seen.append(normalise_label(text))
                if label_matches(text, wanted):
                    matches.append(child)
    return matches, seen


class WalkthroughVerbsMixin:
    """The ``callout`` handler, and the hook ``screenshot`` uses.

    Type-only declarations of the runner surface these methods use; the
    attributes and methods themselves are the runner's.
    """

    if TYPE_CHECKING:
        _window: QWidget
        _deadline_outcome: Outcome
        _deadline_detail: str
        _deadline_timeout_detail: str
        _deadline_cancel: Callable[[], None] | None

        def _record(
            self,
            step: Step,
            outcome: Outcome,
            detail: str = "",
            *,
            elapsed: float = 0.0,
            artifact: str = "",
            declined_by_size: bool = False,
        ) -> None: ...

        def _arm_deadline(
            self,
            step: Step,
            seconds: float,
            predicate: Callable[[], bool] | None = None,
        ) -> None: ...

        def _ensure_artifact_dir(self) -> Path | None: ...

        _callouts: list[PendingCallout]

    # --- callout ---------------------------------------------------------------

    def _pending_callouts(self) -> list[PendingCallout]:
        """The callouts waiting for the next screenshot, created on first use."""
        pending: list[PendingCallout] | None = getattr(self, "_callouts", None)
        if pending is None:
            pending = []
            self._callouts = pending
        return pending

    def _do_callout(self, step: Step) -> None:
        """Mark the one visible widget reading ``<label>`` for the next screenshot."""
        try:
            number = int(step.args[0])
        except ValueError:
            self._record(step, Outcome.ERROR, f"{step.args[0]!r} is not a number")
            return
        if not 1 <= number <= MAX_CALLOUT_NUMBER:
            self._record(
                step,
                Outcome.ERROR,
                f"callout numbers run 1 to {MAX_CALLOUT_NUMBER}; got {number}",
            )
            return
        wanted = step.joined(1)
        pending = self._pending_callouts()
        if any(p.number == number for p in pending):
            self._record(
                step,
                Outcome.ERROR,
                f"callout {number} is already waiting for the next screenshot",
            )
            return
        matches, seen = callout_candidates(wanted)
        if len(matches) != 1:
            named = ", ".join(
                repr(s) for s in sorted(set(seen))[:_LABELS_NAMED_ON_A_MISS]
            )
            why = (
                f"no visible widget reads {wanted!r}"
                if not matches
                else f"{len(matches)} visible widgets read {wanted!r}; a callout "
                "must name exactly one"
            )
            self._record(
                step,
                Outcome.FAIL,
                f"{why} (visible labels include: {named or 'none'})",
            )
            return
        target = matches[0]
        pending.append(PendingCallout(number, target, wanted))
        self._record(
            step,
            Outcome.PASS,
            f"callout {number} on {type(target).__name__} "
            f"{normalise_label(_text_of(target) or '')!r} waits for the next screenshot",
        )

    def _take_callouts(self) -> list[PendingCallout]:
        """Hand the waiting callouts to a screenshot, and clear them.

        Cleared whatever happens next, so a callout is drawn on one picture only
        and a later screenshot cannot inherit a mark meant for an earlier one.
        """
        pending = list(self._pending_callouts())
        self._pending_callouts().clear()
        return pending

    def _render_with_callouts(
        self, window: QWidget, callouts: list[PendingCallout], drawn: set[int]
    ) -> QPixmap | QImage:
        """``window`` rendered, with every waiting callout whose widget is in it.

        The numbers drawn are added to ``drawn``, so the screenshot can name any
        callout it could not place. A window with no callout is rendered exactly
        as before: the same ``grab()``, untouched.
        """
        pixmap = window.grab()
        mine = [
            c for c in callouts if c.target.window() is window and c.target.isVisible()
        ]
        if not mine:
            return pixmap
        marks = []
        for callout in mine:
            corner = callout.target.mapTo(window, QPoint(0, 0))
            marks.append(
                CalloutMark(
                    callout.number,
                    corner.x(),
                    corner.y(),
                    callout.target.width(),
                    callout.target.height(),
                )
            )
            drawn.add(callout.number)
        return draw_callouts(pixmap.toImage(), marks, pixmap.devicePixelRatio())
