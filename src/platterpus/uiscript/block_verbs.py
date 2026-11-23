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
from collections.abc import Sequence
from typing import TYPE_CHECKING, Final

from platterpus.uiscript.report import Outcome
from platterpus.uiscript.run_block import (
    FAIL,
    PASS,
    expand_run_blocks,
    grade_repeats,
    parse_rule,
)

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript.accuracy_grading import AccuracyRecord
    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)

#: How each `expect-repeats` verdict is recorded. Not determined is an ERROR,
#: never a pass: a run that left no record cannot be compared.
_OUTCOMES: Final[dict[str, Outcome]] = {PASS: Outcome.PASS, FAIL: Outcome.FAIL}


class BlockVerbsMixin:
    """The block-framing handlers. Type-only declarations of the runner surface."""

    if TYPE_CHECKING:
        _window: QWidget
        _kept: dict[str, object]
        _accuracies: dict[str, AccuracyRecord]
        _test_name: str
        _test_blocks: tuple[str, ...]
        _expanded_blocks: tuple[str, ...]
        _repeat_runs: dict[str, int]

        @property
        def running(self) -> bool: ...

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

    # --- The test a run is, and its blocks (TASKS R188) ---------------------

    def name_test(self, name: str, blocks: Sequence[str]) -> None:
        """Name the pre-built test the NEXT run is, and its blocks, for the report.

        Called before ``start``, like ``set_run_size``. The report records both,
        and evidence needs the Full test or no name (``run_sizes``), so a run
        that names a different test can never be read as the Full one.
        """
        if self.running:
            raise RuntimeError("cannot rename the test of a running batch")
        self._test_name = name
        self._test_blocks = tuple(blocks)

    def _expand_blocks(self, steps: Sequence[Step]) -> list[Step]:
        """The steps with every ``run-block`` expanded; remembers the runs."""
        expansion = expand_run_blocks(steps)
        self._repeat_runs = dict(expansion.runs)
        self._expanded_blocks = expansion.blocks
        if expansion.runs:
            log.info(
                "ui script: run-block expanded %s into %d step(s)",
                ", ".join(f"{k} x{v}" for k, v in expansion.runs.items()),
                len(expansion.steps),
            )
        return expansion.steps

    def _do_run_block(self, step: Step) -> None:
        """Reached only if ``start`` did not expand this step: say so, loudly."""
        self._record(
            step,
            Outcome.ERROR,
            "this run-block was not expanded when the run started, so its block "
            "did not run; nothing was compared",
        )

    def _do_expect_repeats(self, step: Step) -> None:
        """``expect-repeats <label> <rule>`` — the rule across ``label``'s runs."""
        label = step.args[0]
        rule, problem = parse_rule(step.args[1:])
        if rule is None:
            self._record(step, Outcome.ERROR, problem)
            return
        verdict = grade_repeats(
            label, rule, self._repeat_runs.get(label), self._accuracies
        )
        outcome = _OUTCOMES.get(verdict.verdict, Outcome.ERROR)
        if outcome is not Outcome.PASS:
            log.warning(
                "ui script L%d: %s", step.line_no, verdict.detail.splitlines()[0]
            )
        self._record(step, outcome, verdict.detail)

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
