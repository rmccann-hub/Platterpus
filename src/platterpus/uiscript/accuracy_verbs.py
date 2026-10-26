"""The paired-rip verbs: ``record-accuracy`` and ``compare-accuracy`` (section P6).

The owner's word (2026-10-26): *"add paired .25/.26 rips of track 3 to the Full
run."* Section P6 of ``fullacceptance.txt`` rips track 3 of the reference disc
eight times, alternating the approved build and the build under review in ABBA
order, and these two verbs record each rip's per-track AccurateRip outcome and
then count, per build, how many of those rips AccurateRip verified. The pure half
is :mod:`platterpus.uiscript.accuracy_grading`; the section reuses
``install-ripper`` (``install_verbs.py``) and ``skip-if-same-build``
(``timing_verbs.py``) from P5.

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like the other
``*_verbs`` modules. Nothing here blocks: each handler reads a parsed log or a
dict the runner holds, and the one file read goes through the runner's shared
``_rip_log_from_disk`` (its staleness and existence guards come with it).

**Every grade is a measurement** (``INFO``) or a refusal (``ERROR``, "not
determined"); none is a pass or a fail, because a build that misreads a track is
a finding for the fork rather than a defect of the rip (``docs/testing.md``,
Acceptance severity, P6, declared before any run).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from platterpus.uiscript.accuracy_grading import (
    AccuracyRecord,
    accuracy_from_log,
    compare_accuracy,
    label_problem,
)
from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.parsers.rip_log import RipLog
    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)


class AccuracyVerbsMixin:
    """The paired-rip handlers. Type-only declarations of the runner surface."""

    if TYPE_CHECKING:
        _window: QWidget
        _accuracies: dict[str, AccuracyRecord]
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

    def _do_record_accuracy(self, step: Step) -> None:
        """``record-accuracy <label>``: the last rip's per-track AccurateRip result."""
        label = step.args[0]
        problem = label_problem(label)
        if problem:
            self._record(step, Outcome.ERROR, problem)
            return
        parsed = self._rip_log_from_disk(step)
        if parsed is None:
            return  # the shared reader recorded why, and names the file
        source = str(getattr(self._window, "_last_rip_log_file", "") or "")
        record = accuracy_from_log(label, parsed, source)
        replaced = label in self._accuracies
        self._accuracies[label] = record
        detail = record.describe()
        if replaced:
            detail += f"\n  (replaces an earlier record named {label})"
        if (
            record.build
            and self._ripper_build_tag
            and record.build.casefold() != self._ripper_build_tag.casefold()
        ):
            # Said, not graded: the log is the artifact and wins, but a reader
            # needs to know the run believed another build was installed.
            detail += (
                f"\n  NOTE: the log names {record.build}, while the last banner "
                f"this run read named {self._ripper_build_tag}"
            )
        if not record.build or not record.tracks:
            self._record(
                step,
                Outcome.ERROR,
                detail + "\n  not determined: a comparison needs the build named "
                "and at least one audio track",
            )
            return
        log.info("ui script L%d: %s", step.line_no, detail.splitlines()[0])
        self._record(step, Outcome.INFO, detail)

    def _do_compare_accuracy(self, step: Step) -> None:
        """``compare-accuracy <label> <label>…``: right in N of M rips, per build."""
        verdict = compare_accuracy(list(step.args), self._accuracies)
        if verdict.determined:
            self._record(step, Outcome.INFO, verdict.detail)
            return
        text = verdict.refusal
        if verdict.detail:
            text += "\n" + verdict.detail
        self._record(step, Outcome.ERROR, text)
