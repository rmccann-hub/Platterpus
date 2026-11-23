"""The verbs a test block is framed with: ``expect-kept``, ``run-block``, ``expect-repeats``.

**``expect-kept <setting>``** (TASKS R189). A block restores what it changes
(TASKS R188's rule), and a probe that may change a setting proves it left it as
it found it: ``keep <setting>`` before (the runner records the value), and
``expect-kept <setting>`` after. The over-read probe ended ``expect
force_overread off`` until 2026-11-23, which failed the probe on the owner's own
Overread setting: on before the run, and neither set nor changed by it. A check
against a typed value graded the operator's choice; this one grades the probe.

**``run-block``** is expanded by the runner when a run starts
(``uiscript/run_block.py``), so its handler here is reached only if that did not
happen, and says so. **``expect-repeats``** grades the runs' accuracy records
with :func:`platterpus.uiscript.run_block.grade_repeats`.

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like the other
``*_verbs`` modules. Nothing here blocks: each handler reads a value or a dict
the runner holds.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)


class BlockVerbsMixin:
    """The block-framing handlers. Type-only declarations of the runner surface."""

    if TYPE_CHECKING:
        _window: QWidget
        _kept: dict[str, object]

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

    def _do_expect_kept(self, step: Step) -> None:
        """``expect-kept <config-field>`` — the setting still has its kept value.

        With no ``keep`` of the field earlier in the run there is nothing to
        compare: an ERROR, never a pass.
        """
        field = step.args[0]
        config = getattr(self._window, "_config", None)
        if config is None or not hasattr(config, field):
            self._record(step, Outcome.ERROR, f"no setting called {field!r}")
            return
        if field not in self._kept:
            self._record(
                step,
                Outcome.ERROR,
                f"nothing to compare: no `keep {field}` ran earlier in this run",
            )
            return
        kept = self._kept[field]
        actual = getattr(config, field)
        if actual == kept:
            self._record(step, Outcome.PASS, f"{field} is still {actual!r}")
            return
        log.warning(
            "ui script L%d: %s changed from %r to %r", step.line_no, field, kept, actual
        )
        self._record(
            step, Outcome.FAIL, f"{field} was {kept!r} when kept, and is {actual!r}"
        )
