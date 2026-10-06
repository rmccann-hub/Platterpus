"""The acceptance script's offset-override verb: a drive nobody knows is refused.

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like
:mod:`platterpus.uiscript.permutation_verbs`, so the runner file does not grow.

**The path.** With the read-offset override off, Start goes one of two ways
(``RipMixin._on_rip_requested``): a drive in AccurateRip's drive list gets the
list's offset and rips (``_auto_apply_known_offset``); any other drive is refused
with *"Set up your drive first"*, so no rip starts at an offset nobody chose. One
script line therefore passes on one rig and fails on another, and on a listed
drive the first branch rewrites the offset ``set-drive-offset`` set. The ruling
(2026-10-05, ``PLANNING.md`` KDD-41, C4): turn the override off, **skip, saying
why, on a listed drive**, and grade the refusal on any other.

**The skip is ``UNREACHABLE``**, round 18's token for a step this equipment
cannot run: ``SKIPPED`` would read as a choice a re-run could reverse, and
``PASS`` would claim a refusal nobody saw. The transcript and the session's
closing dialog count such steps, so a skip never reads as a pass
(``RunReport.unreachable``).

**Every exit path puts the override back**: the refusal answered, a rip that
should not have started, the wait running out, the run stopped (the runner's
``_deadline_cancel``). The script's next lines prove it.

**Nothing here blocks the GUI thread.** Start is pressed on the next event-loop
turn, as ``rip`` presses it, so the refusal's modal loop runs outside this
handler, and the wait is the runner's deadline machinery.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer

from platterpus.uiscript.offset_grading import (
    DECLINE_LABEL,
    OFFSET_REFUSAL_TITLE,
    OFFSET_REFUSAL_WAIT_S,
    drive_in_offset_list,
    start_blocker,
    unreachable_detail,
)
from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)


class OffsetVerbsMixin:
    """The ``expect-offset-refusal`` handler. Type-only declarations of the
    runner surface it uses; the attributes and methods themselves are the
    runner's."""

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

    def _do_expect_offset_refusal(self, step: Step) -> None:
        """Turn the override off, press Start, and grade the refusal.

        On a drive the AccurateRip list carries the step records
        ``UNREACHABLE`` and touches nothing (module docstring). Otherwise it
        needs Start to be pressable, as a person's click would: an identified
        disc, no dialog up, no rip running. It then turns the override off
        through the window's single-setting writer (the validator runs), presses
        Start, waits for the refusal, declines the wizard with ``No``, and passes
        only once the refusal has closed with no rip started. The override is
        put back on every path.
        """
        # Read here: the runner imports this mixin, so a top-level import would
        # be circular. `answer-dialog`'s own helpers, so dialogs are found alike.
        from platterpus.uiscript.runner import _active_dialog, _click_named_button

        window = self._window
        config = getattr(window, "_config", None)
        controls = getattr(window, "_rip_controls", None)
        save = getattr(window, "_save_user_setting", None)
        put_back = getattr(window, "_set_read_offset_override", None)
        if (
            config is None
            or controls is None
            or not callable(save)
            or not callable(put_back)
        ):
            self._record(step, Outcome.ERROR, "no application window to test it on")
            return
        label, listed = drive_in_offset_list(window)
        if not label:
            self._record(
                step,
                Outcome.FAIL,
                "no drive is selected, so there is no drive whose offset the app "
                "could refuse to guess",
            )
            return
        if listed is not None:
            self._record(step, Outcome.UNREACHABLE, unreachable_detail(label, listed))
            return
        blocking = _active_dialog()
        blocker = start_blocker(window, blocking.windowTitle() if blocking else "")
        if blocker:
            self._record(step, Outcome.FAIL, blocker)
            return
        start = getattr(controls, "_on_start", None)
        if not callable(start):
            self._record(step, Outcome.ERROR, "the rip controls have no _on_start()")
            return

        was_on = bool(getattr(config, "override_read_offset", False))
        value = int(getattr(config, "read_offset", 0))
        written = save("override_read_offset", False)
        if not bool(getattr(written, "applied", False)):
            self._record(
                step,
                Outcome.FAIL,
                "the app refused to turn the override off: "
                f"{getattr(written, 'message', '') or 'no reason given'}",
            )
            return
        log.info(
            "expect-offset-refusal: override off on %s (not in the AccurateRip "
            "list); pressing Start, expecting %r",
            label,
            OFFSET_REFUSAL_TITLE,
        )

        restored: list[str] = []  # one entry once the restore has run
        answered: list[str] = []  # the button clicked on the refusal
        seen: list[str] = []  # other dialogs that came up instead

        def restore() -> str:
            """Put the override back as it was. Runs once; never raises."""
            if restored:
                return restored[0]
            try:
                if was_on:
                    ok = bool(put_back(value))
                    text = (
                        f"the override was put back on at {value:+d}"
                        if ok
                        else f"the override could NOT be put back on at {value:+d}"
                    )
                else:
                    text = "the override was left off, as it was before this step"
            except Exception as exc:  # noqa: BLE001 — a restore must not raise into Qt
                log.exception("expect-offset-refusal: the restore failed")
                text = f"putting the override back raised {exc!r}"
            restored.append(text)
            log.info("expect-offset-refusal: %s", text)
            return text

        def stop_unwanted_rip() -> str:
            """Cancel a rip this step started; "" when none is running."""
            if getattr(window, "_rip_worker", None) is None:
                return ""
            cancel = getattr(window, "_on_rip_cancel", None)
            if callable(cancel) and not getattr(window, "_rip_cancelled", False):
                try:
                    cancel()
                except Exception:  # noqa: BLE001 — the step still records why
                    log.exception("expect-offset-refusal: cancelling the rip failed")
            return "a rip STARTED with the override off, and it was cancelled"

        def settled() -> bool:
            started = stop_unwanted_rip()
            if started:
                self._deadline_outcome = Outcome.FAIL
                self._deadline_detail = (
                    f"{started}: {label} is not in the AccurateRip drive list, so "
                    "the app had no offset to rip at and should have refused. "
                    f"{restore()}."
                )
                return True
            dialog = _active_dialog()
            if answered:
                if dialog is not None and OFFSET_REFUSAL_TITLE in dialog.windowTitle():
                    return False  # still closing; ask again next tick
                outcome_text = restore()
                self._deadline_outcome = (
                    Outcome.PASS if "could NOT" not in outcome_text else Outcome.FAIL
                )
                self._deadline_detail = (
                    f"{label} is not in the AccurateRip drive list: with the "
                    f"override off, Start was refused with {OFFSET_REFUSAL_TITLE!r} "
                    f"and no rip started; clicked {answered[0]!r} so the wizard did "
                    f"not open. {outcome_text}."
                )
                return True
            if dialog is None:
                return False  # Start has not raised anything yet
            title = dialog.windowTitle()
            if OFFSET_REFUSAL_TITLE.casefold() not in title.casefold():
                # Not answered: an unattended run must not click a dialog it was
                # not told to expect. Named in the timeout instead.
                if title not in seen:
                    seen.append(title)
                self._deadline_timeout_detail = (
                    f"no {OFFSET_REFUSAL_TITLE!r} refusal within "
                    f"{OFFSET_REFUSAL_WAIT_S:.0f}s; a different dialog was up and "
                    f"was left untouched: {', '.join(repr(t) for t in seen)}. The "
                    "override was put back."
                )
                return False
            clicked, why = _click_named_button(dialog, DECLINE_LABEL)
            if clicked is None:
                dialog.reject()
                self._deadline_outcome = Outcome.FAIL
                self._deadline_detail = (
                    f"the refusal came up but {why}; it was dismissed instead. "
                    f"{restore()}."
                )
                return True
            answered.append(clicked)
            return False  # confirm on the next tick that no rip followed

        def cancel() -> None:
            """The wait ended without an answer, or the run stopped."""
            dialog = _active_dialog()
            if dialog is not None and OFFSET_REFUSAL_TITLE in dialog.windowTitle():
                _click_named_button(dialog, DECLINE_LABEL)
            stop_unwanted_rip()
            restore()

        # Pressed on the next event-loop turn, as `rip` presses it, so the
        # refusal's modal loop runs outside this handler and the tick that
        # follows can answer it.
        QTimer.singleShot(0, start)
        self._arm_deadline(step, OFFSET_REFUSAL_WAIT_S, settled)
        self._deadline_cancel = cancel
        self._deadline_timeout_detail = (
            f"Start raised no {OFFSET_REFUSAL_TITLE!r} refusal within "
            f"{OFFSET_REFUSAL_WAIT_S:.0f}s and no rip started either. The override "
            "was put back."
        )
