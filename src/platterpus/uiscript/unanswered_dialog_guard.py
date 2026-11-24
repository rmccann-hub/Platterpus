"""A scripted run never waits on a dialog nobody answers, and never steals focus.

**The run that made this** (the owner's Full acceptance run, 2026-11-23, 0.7.129).
Section D's `open dependencies` started the dependency check, and its result was
held behind a release picker that had opened by itself a moment earlier. The
step's `cancel` closed the picker, not the result; the result box,
*"Dependency check complete"*, then came up with no step left to close it, and
the release picker the next section needed was held behind it. The run sat
**3 minutes 29 seconds** (23:50:28 to 23:53:57 UTC) until the owner happened to
look and clicked OK. Their word, 2026-11-24: *"they should run on their own, not
need acceptance by a user, and also not interrupt a user with bringing windows
and things to the front."*

Two guarantees live here, both for the length of a scripted run:

* **No dialog waits for a person.** A dialog of the app's that stays on top,
  unanswered, for :data:`UNANSWERED_DIALOG_TIMEOUT_S` is closed with **Cancel**
  (`reject()`), and the run records a FAIL row naming it and what it said. The
  run then carries on. Cancel is the safe answer because it is the one that
  does nothing: on a question it declines (no overwrite, no install, no
  setting changed), and on a notice it only closes it. Recorded as a FAIL
  because a dialog nobody predicted is a defect in the run or the app, and a
  run that quietly clicked one away would hide it (`answer-dialog`'s docstring
  says why a silent click is worse than a hang).
* **No window takes focus or comes to the front** while the run runs
  (`ui.dialogs.quiet_presentation`). A `--run-script` launch is quiet
  from its first window (`app.py`); a run started from the menu turns it on when
  it starts and back off when it ends.

Why the timeout is 90 s: long enough that a step answering its own dialog
(`answer-dialog`, `pick-release`, `ok`/`cancel` after a `screenshot`) always
gets there first, as they take seconds, and longer than the fatal-error
dialog's own 60 s self-close (`app.UNATTENDED_FATAL_DIALOG_TIMEOUT_S`), so
that dialog keeps its own, better-worded exit. Short against runs that take
hours.

A mixin of `ScriptRunner` rather than more of `runner.py`, which is past five
thousand lines; it reads only the runner's `_report`, `_steps`, `_index`,
`_deadline_step` and `_record`.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Final

from PySide6.QtWidgets import QDialog, QMessageBox

from platterpus.ui.dialogs.quiet_presentation import (
    present_quietly,
    presenting_quietly,
)
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.script import Step

if TYPE_CHECKING:
    from platterpus.uiscript.report import RunReport

log = logging.getLogger(__name__)

#: How long a dialog of the app's may sit on top, unanswered, during a scripted
#: run before the run closes it with Cancel. The module docstring says why 90.
UNANSWERED_DIALOG_TIMEOUT_S: Final[float] = 90.0

#: How much of a dialog's text the FAIL row quotes. Enough for the sentence
#: that says what it was; the full text goes to the log.
_QUOTED_TEXT_CHARS: Final[int] = 300


def _dialog_text(dialog: QDialog) -> str:
    """What the dialog said, for the record: a message box's text, else ""."""
    if isinstance(dialog, QMessageBox):
        return " ".join(dialog.text().split())
    return ""


class UnansweredDialogGuardMixin:
    """Closes a dialog nobody answers, and keeps windows quiet, during a run."""

    if TYPE_CHECKING:
        _report: RunReport
        _steps: list[Step]
        _index: int
        _deadline_step: Step | None

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

    #: The dialog the guard is timing, and since when (monotonic seconds).
    #: Class-level defaults, so a runner that never started has a quiet guard.
    _unanswered_dialog: QDialog | None = None
    _unanswered_since: float = 0.0
    #: Whether windows were quiet before this run began, so the end of the run
    #: puts back what it found: a `--run-script` launch stays quiet after it.
    _quiet_before_run: bool = False

    def _begin_quiet_run(self) -> None:
        """At the start of a run: windows quiet, guard reset."""
        self._quiet_before_run = presenting_quietly()
        present_quietly(True)
        self._unanswered_dialog = None
        self._unanswered_since = 0.0

    def _end_quiet_run(self) -> None:
        """At the end of a run, however it ends: put the presentation back."""
        present_quietly(self._quiet_before_run)
        self._unanswered_dialog = None

    def _close_dialog_nobody_answered(self, now: float | None = None) -> None:
        """Called every tick of a run. Never raises.

        Times the dialog on top; once the same one has been there for
        :data:`UNANSWERED_DIALOG_TIMEOUT_S`, closes it with Cancel and records
        a FAIL row. ``now`` is for tests; the run passes nothing.
        """
        from platterpus.uiscript.runner import _active_dialog

        try:
            moment = time.monotonic() if now is None else now
            dialog = _active_dialog()
            if dialog is None:
                self._unanswered_dialog = None
                return
            if dialog is not self._unanswered_dialog:
                # A new one (or the first): start its clock.
                self._unanswered_dialog = dialog
                self._unanswered_since = moment
                return
            waited = moment - self._unanswered_since
            if waited < UNANSWERED_DIALOG_TIMEOUT_S:
                return
            title = dialog.windowTitle()
            text = _dialog_text(dialog)
            self._unanswered_dialog = None
            dialog.reject()
        except RuntimeError:
            # The dialog's C++ side went away between the look and the close:
            # it is gone, which is all this wanted.
            self._unanswered_dialog = None
            return
        log.warning(
            "ui script: closed %r with Cancel after %.0fs with nobody answering "
            "it, so the run does not wait for a person; it said: %s",
            title,
            waited,
            text or "(no text)",
        )
        quoted = text[:_QUOTED_TEXT_CHARS] + (
            "…" if len(text) > _QUOTED_TEXT_CHARS else ""
        )
        step = self._deadline_step or self._steps[max(self._index - 1, 0)]
        self._record(
            Step(
                line_no=step.line_no,
                source=f"(no step answered a dialog) {step.source}",
            ),
            Outcome.FAIL,
            f"{title!r} sat on screen {waited:.0f}s with no step to answer it, so "
            "the run closed it with Cancel and carried on (a scripted run never "
            "waits for a person). A dialog no step predicted is a defect in the "
            "script or the app" + (f". It said: {quoted}" if quoted else ""),
        )
