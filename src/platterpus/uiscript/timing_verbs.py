"""The timed-rip verbs: ``skip-if-same-build``, ``record-timing``, ``compare-timings``.

The owner asked for a timed rip comparing two cyanrip fork builds in the Full run,
and the fork's round 36 lap 1 S15 proposed the method (see
:mod:`platterpus.uiscript.timing_grading`, the pure half). These three verbs plus
``install-ripper`` (``install_verbs.py``) are what section P5 of
``fullacceptance.txt`` is written in.

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like the other
``*_verbs`` modules. Nothing here blocks: each handler reads a parsed log or a
dict the runner holds, and the one file read goes through the runner's shared
``_rip_log_from_disk`` (its staleness and existence guards come with it).

**Every grade is a measurement** (``INFO``) or a refusal (``ERROR``, "not
determined"); none is a pass or a fail, because a slower build is a finding for
the fork rather than a defect of the rip.

**When there is nothing to compare.** Between rounds the build under review IS
the approved pin, and timing a build against itself measures the drive. So
``skip-if-same-build`` records ``INFO`` "nothing to compare" and every later step
of the same section is recorded ``UNREACHABLE`` (N/A) rather than run: the
comparison cannot happen on this record state, which is neither a pass nor a
failure — ``RunReport.ok`` forgives it, and the RESULT line names it, exactly as
it names an offset refusal a listed drive cannot make. ``SKIPPED`` would fail the
run (only a run size's declines are forgiven), and ``INFO`` would claim a step
gathered something it never ran. ``tests/test_uiscript_offset_refusal.py`` holds
this module in its list of producers, by name and with that reason.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from platterpus.uiscript.report import Outcome
from platterpus.uiscript.timing_grading import (
    TimingRecord,
    agreement,
    label_problem,
    ratio,
    timing_from_log,
)

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.parsers.rip_log import RipLog
    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)


class TimingVerbsMixin:
    """The timing handlers. Type-only declarations of the runner surface."""

    if TYPE_CHECKING:
        _window: QWidget
        _timings: dict[str, TimingRecord]
        _same_build_skip: str
        _ripper_build_tag: str

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

        def _rip_log_from_disk(self, step: Step) -> RipLog | None: ...

    # --- nothing to compare ------------------------------------------------------

    def _skip_for_same_build(self, step: Step) -> bool:
        """Record ``step`` as not runnable when its section has nothing to compare.

        Called by the runner's dispatch for every step after the run size has had
        its say. A section header ends the skip, so it never reaches past the
        section that declared it. Structural verbs still run: they state the run's
        shape. Returns True when the step was recorded here and must not run.
        """
        from platterpus.uiscript.runner import _STRUCTURAL_VERBS, _is_section_header

        if _is_section_header(step):
            self._same_build_skip = ""
            return False
        if not self._same_build_skip or step.verb in _STRUCTURAL_VERBS:
            return False
        self._record(step, Outcome.UNREACHABLE, f"not run: {self._same_build_skip}")
        return True

    def _do_skip_if_same_build(self, step: Step) -> None:
        """``skip-if-same-build <A> <B>``: no comparison when both name one build."""
        from platterpus.deps.fork_source import same_commit, target_for_commit
        from platterpus.deps.ripper_install import resolve_script_commit

        resolved: list[str] = []
        for spec in step.args:
            commit, refusal = resolve_script_commit(spec)
            if refusal:
                # The comparison cannot be set up, so the rest of the section
                # would spend drive time on nothing. The ERROR fails the run; the
                # steps after it say why they did not run.
                self._same_build_skip = (
                    f"L{step.line_no} could not resolve {spec!r}, so there is no "
                    "comparison to make"
                )
                self._record(step, Outcome.ERROR, refusal)
                return
            resolved.append(commit)
        first, second = resolved
        if same_commit(first, second):
            self._same_build_skip = (
                f"nothing to compare — {step.args[0]} and {step.args[1]} both name "
                f"{first} (L{step.line_no})"
            )
            self._record(
                step,
                Outcome.INFO,
                f"nothing to compare: {step.args[0]} and {step.args[1]} are both "
                f"{first}, and timing a build against itself measures the drive, "
                "not the build. The rest of this section is not run (marked N/A); "
                "it runs once the record names a second build.",
            )
            return
        self._same_build_skip = ""
        versions = [target_for_commit(c).version for c in resolved]
        self._record(
            step,
            Outcome.INFO,
            f"comparing {step.args[0]} = {first} ({versions[0]}) with "
            f"{step.args[1]} = {second} ({versions[1]})",
        )

    # --- one rip's timing --------------------------------------------------------

    def _do_record_timing(self, step: Step) -> None:
        """``record-timing <label>``: the last rip's per-track ``Elapsed:`` seconds."""
        label = step.args[0]
        problem = label_problem(label)
        if problem:
            self._record(step, Outcome.ERROR, problem)
            return
        parsed = self._rip_log_from_disk(step)
        if parsed is None:
            return  # the shared reader recorded why, and names the file
        source = str(getattr(self._window, "_last_rip_log_file", "") or "")
        record = timing_from_log(label, parsed, source)
        replaced = label in self._timings
        self._timings[label] = record
        detail = record.describe()
        if replaced:
            detail += f"\n  (replaces an earlier timing recorded as {label})"
        if (
            record.build
            and self._ripper_build_tag
            and (record.build.casefold() != self._ripper_build_tag.casefold())
        ):
            # Said, not graded: the log is the artifact and wins, but a reader
            # needs to know the run believed another build was installed.
            detail += (
                f"\n  NOTE: the log names {record.build}, while the last banner "
                f"this run read named {self._ripper_build_tag}"
            )
        if not record.complete or not record.build:
            self._record(
                step,
                Outcome.ERROR,
                detail + "\n  not determined: a comparison needs every track timed and "
                "the build named",
            )
            return
        log.info("ui script L%d: %s", step.line_no, detail.splitlines()[0])
        self._record(step, Outcome.INFO, detail)

    # --- the comparison ----------------------------------------------------------

    def _do_compare_timings(self, step: Step) -> None:
        """``compare-timings <base> <candidate> [<base2> <candidate2>]``.

        Two labels: the ratio ``candidate / base``. Four: both pairs' ratios and
        whether they agree within the tolerance, which is when S15 calls the
        comparison done.
        """
        labels = list(step.args)
        if len(labels) not in (2, 4):
            self._record(
                step,
                Outcome.ERROR,
                f"compare-timings takes two labels or four, got {len(labels)}",
            )
            return
        first = ratio(self._timings.get(labels[0]), self._timings.get(labels[1]))
        if len(labels) == 2:
            if first.value is None:
                self._record(step, Outcome.ERROR, first.refusal)
            else:
                self._record(step, Outcome.INFO, first.detail)
            return
        second = ratio(self._timings.get(labels[2]), self._timings.get(labels[3]))
        verdict = agreement(first, second)
        lines = [
            first.detail or first.refusal,
            second.detail or second.refusal,
            verdict.detail,
        ]
        outcome = Outcome.ERROR if verdict.agree is None else Outcome.INFO
        self._record(step, outcome, "\n".join(lines))
