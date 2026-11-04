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

**And the track-3 script** (TASKS R123, ``rig_scripts/track3abba.txt``): its rips
call cyanrip directly, so ``--cache-probe`` and ``-P 0`` can be given, which an
app rip cannot. ``record-accuracy <label> <folder>`` reads the one log such a
``cyanrip … -D <folder>`` step wrote this run (``folder_logs.read_one_log``, the
reader section P3's verb uses), on a helper thread under the runner's deadline,
and ``compare-conditions`` counts one track's rips per condition on one build
(``condition_grading.py``).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Final

from platterpus.uiscript.accuracy_grading import (
    AccuracyRecord,
    accuracy_from_log,
    compare_accuracy,
    label_problem,
)
from platterpus.uiscript.condition_grading import (
    cache_probe_value,
    compare_conditions,
    track_problem,
)
from platterpus.uiscript.folder_logs import folder_problem, read_one_log
from platterpus.uiscript.pregap_verbs import run_start_epoch
from platterpus.uiscript.probe_verbs import _start
from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.parsers.rip_log import RipLog
    from platterpus.uiscript.report import RunReport
    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)

#: How long reading a ``-D`` folder's log may take: well under a second locally;
#: the backstop for a rips folder on a slow share, as section P3's verb has.
FOLDER_READ_WAIT_S: Final[float] = 60.0


class AccuracyVerbsMixin:
    """The paired-rip handlers. Type-only declarations of the runner surface."""

    if TYPE_CHECKING:
        _window: QWidget
        _accuracies: dict[str, AccuracyRecord]
        _ripper_build_tag: str
        _report: RunReport
        _deadline_outcome: Outcome
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

        def _rip_log_from_disk(self, step: Step) -> RipLog | None: ...

        def _arm_deadline(
            self,
            step: Step,
            seconds: float,
            predicate: Callable[[], bool] | None = None,
        ) -> None: ...

    def _do_record_accuracy(self, step: Step) -> None:
        """``record-accuracy <label>``: the last rip's per-track AccurateRip result."""
        label = step.args[0]
        problem = label_problem(label)
        if problem:
            self._record(step, Outcome.ERROR, problem)
            return
        if len(step.args) > 1:
            self._record_accuracy_from_folder(step, label, step.args[1])
            return
        parsed = self._rip_log_from_disk(step)
        if parsed is None:
            return  # the shared reader recorded why, and names the file
        source = str(getattr(self._window, "_last_rip_log_file", "") or "")
        outcome, detail = self._file_accuracy(accuracy_from_log(label, parsed, source))
        if outcome is Outcome.INFO:
            log.info("ui script L%d: %s", step.line_no, detail.splitlines()[0])
        self._record(step, outcome, detail)

    def _record_accuracy_from_folder(self, step: Step, label: str, name: str) -> None:
        """``record-accuracy <label> <folder>``: the log a scripted rip wrote."""
        # Imported here: the runner imports this mixin, and the rips folder has
        # ONE reader, the one the `cyanrip` verb runs in.
        from platterpus.parsers.cyanrip_log import parse_cyanrip_log
        from platterpus.uiscript.runner import _ripper_workdir

        problem = folder_problem(name)
        if problem:
            self._record(step, Outcome.ERROR, problem)
            return
        root, refused = _ripper_workdir(self._window)
        if root is None:
            self._record(step, Outcome.ERROR, refused)
            return
        since = run_start_epoch(self._report.started_at)
        if since is None:
            self._record(
                step,
                Outcome.ERROR,
                f"this run has no start time (started_at {self._report.started_at!r}),"
                " so an earlier run's log in that folder cannot be told from this "
                "run's",
            )
            return

        def work() -> AccuracyRecord | str:
            found = read_one_log(root, name, since=since)
            if found.problem or found.path is None:
                return found.problem or "no log found"
            return accuracy_from_log(
                label,
                parse_cyanrip_log(found.text),
                str(found.path),
                cache_probe_value(found.text),
            )

        job = _start(work, "record-accuracy")

        def answered() -> bool:
            if not job.done.is_set():
                return False
            value = job.value
            if isinstance(value, AccuracyRecord):
                self._deadline_outcome, self._deadline_detail = self._file_accuracy(
                    value
                )
                return True
            self._deadline_outcome = Outcome.ERROR
            self._deadline_detail = (
                f"accuracy {label}: not determined: {job.error or value or 'no answer'}"
            )
            return True

        self._arm_deadline(step, FOLDER_READ_WAIT_S, answered)
        self._deadline_timeout_detail = (
            f"accuracy {label}: the log under {root / name} was not read within "
            f"{FOLDER_READ_WAIT_S:.0f}s, so it is not determined"
        )

    def _file_accuracy(self, record: AccuracyRecord) -> tuple[Outcome, str]:
        """Keep ``record`` under its label; the outcome and transcript text."""
        label = record.label
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
            return (
                Outcome.ERROR,
                detail + "\n  not determined: a comparison needs the build named "
                "and at least one audio track",
            )
        return Outcome.INFO, detail

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

    def _do_compare_conditions(self, step: Step) -> None:
        """``compare-conditions <track> <label>…``: one track, per condition."""
        number, problem = track_problem(step.args[0])
        if number is None:
            self._record(step, Outcome.ERROR, problem)
            return
        verdict = compare_conditions(number, list(step.args[1:]), self._accuracies)
        if verdict.determined:
            self._record(step, Outcome.INFO, verdict.detail)
            return
        text = verdict.refusal
        if verdict.detail:
            text += "\n" + verdict.detail
        self._record(step, Outcome.ERROR, text)
