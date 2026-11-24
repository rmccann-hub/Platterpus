"""`open dependencies`: start the app's own dependency check, then wait for it.

A mixin of `ScriptRunner`, split out of `runner.py` (past five thousand lines)
when the wait learned that a result held behind another dialog has not landed
(TASKS R195, 2026-11-24). It reads the runner's `_window`, `_record`,
`_arm_deadline` and the deadline's detail fields, and nothing else.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Final

from PySide6.QtWidgets import QWidget

from platterpus.uiscript.report import Outcome
from platterpus.uiscript.script import Step

#: How long past the dependency check's own deadline `open dependencies` waits for
#: it to land. The check stops itself at `deps.manager.CHECK_DEADLINE_S` and kills
#: the probe in flight; this covers the kill, the reap and the queued hand-back to
#: the GUI thread. A check still out after that is reported, not waited on.
_DEPENDENCY_LANDING_GRACE_S: Final[float] = 30.0


class DependencyVerbsMixin:
    """`open dependencies`, which waits until its own result is on screen."""

    if TYPE_CHECKING:
        _window: QWidget
        _deadline_detail: str
        _deadline_timeout_detail: str

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

    def _open_dependency_check(self, step: Step, start: Callable[[], None]) -> None:
        """`open dependencies`: start the app's own check, then WAIT for it to land.

        **This used to freeze the window** (fixed 2026-09-28). The target named
        `run_dependency_check`, the synchronous form kept for tests, so a script's
        `open dependencies` ran every probe on the GUI thread — the ripping
        container's cold start included — and the window showed "Not Responding"
        for as long as that took. The scripts never noticed, because they did not
        need to: `open dependencies` → `screenshot` → `cancel` found the summary
        up only because the freeze had held every later step back until it was.

        Now the target is the Setup & Updates button's own entry point, which
        probes on a worker and shows its summary when it lands, and the waiting
        the freeze used to do by accident is done here on purpose: the step holds
        until the check it started (or the one already running, which it adopts)
        has landed, so the next step still finds its result on screen. It is
        bounded by the check's own deadline plus a grace, and a check that has not
        landed by then is reported as a FAIL rather than waited on.
        """
        from platterpus.deps import manager as dep_manager
        from platterpus.uiscript.runner import _active_dialog

        window = self._window
        start()  # returns at once: the probing happens on a worker thread
        worker = getattr(window, "_dep_check_worker", None)
        if worker is None:
            self._record(
                step,
                Outcome.ERROR,
                "the dependency check did not start, so there is no result to wait for",
            )
            return
        seconds = dep_manager.CHECK_DEADLINE_S + _DEPENDENCY_LANDING_GRACE_S

        def landed() -> bool:
            # Identity, not "is there a worker": a check started after ours (by the
            # next step, or by the user) must not keep this one waiting, and ours
            # being replaced means it has already landed.
            if getattr(window, "_dep_check_worker", None) is worker:
                return False
            # The deferral is asked FIRST: while the result is held, the dialog
            # on top is the one holding it, and reading that as "the result is
            # up" is exactly the mistake below.
            if getattr(window, "_dep_resolve_deferrals", 0):
                # NOT LANDED: the result is held behind another dialog, so the
                # next step (`screenshot`, then `cancel`) would act on THAT one.
                # On 2026-11-23 it did: `cancel` closed a release picker that had
                # opened by itself, and the result box came up afterwards with
                # no step left to close it, holding the run 3m29s until the
                # owner clicked OK. So wait for the result to come up; the
                # unanswered-dialog guard closes the one in the way if nobody
                # does (`unanswered_dialog_guard.py`).
                held_by = _active_dialog()
                self._deadline_timeout_detail = (
                    "the dependency check finished, but its result was still "
                    f"waiting for another dialog to close after {seconds:.0f}s"
                    + (f" ({held_by.windowTitle()!r})" if held_by is not None else "")
                )
                return False
            dialog = _active_dialog()
            if dialog is not None:
                self._deadline_detail = (
                    f"the dependency check finished; {dialog.windowTitle()!r} is up"
                )
            else:
                self._deadline_detail = (
                    "the dependency check finished with no dialog left on screen"
                )
            return True

        self._arm_deadline(step, seconds, landed)
        # After arming, which resets it.
        self._deadline_timeout_detail = (
            f"the dependency check had not finished after {seconds:.0f}s, past its "
            f"own {dep_manager.CHECK_DEADLINE_S:.0f}s deadline; a probe is not "
            f"honouring it"
        )
