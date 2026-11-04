"""The ``expect-deemphasis-pair`` verb: grade section P3's two rips (round 16, clause 2).

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like the other
``*_verbs`` modules. The grade itself is
:mod:`platterpus.uiscript.deemphasis_grading`, pure; this module finds the two
logs and reads them.

**Which logs.** Section P3 runs ``cyanrip ... -D r16deemphon`` and ``... -D
r16deemphoff`` through the ``cyanrip`` verb, which runs the ripper in the rips
folder (``runner._ripper_workdir``), so each arm's log is in that folder's named
subfolder. The verb takes the two folder names, forced arm first, and reads the
cyanrip log in each that was written since this run started (read off the run's
own ``RunReport.started_at``, as ``expect-pregaps-agree`` does). Exactly one
such log per folder: none, or more than one, is not determined, because grading
a log from an earlier run, or guessing between two, would grade the wrong rip.

**Nothing here blocks the GUI thread.** The folder may be on a network share, so
the read runs on a daemon thread that touches nothing Qt, and the runner's
deadline polls for the answer (the shape ``pregap_verbs`` uses).

**Outcomes, declared before any disc goes in** (P3 is ARCHIVAL, ``docs/testing.md``
→ *Acceptance severity*): ``PASS`` when the CRCs agree and the loudness moved by
the floor; ``FAIL`` when either half does not hold; ``BLOCKED`` (prevented, the row
stays unknown) when a value is missing or the build measures before the filter.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Final

from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.uiscript import deemphasis_grading as grading
from platterpus.uiscript.folder_logs import folder_problem, read_one_log
from platterpus.uiscript.pregap_verbs import run_start_epoch
from platterpus.uiscript.probe_verbs import _start
from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript.report import RunReport
    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)

#: How long reading the two logs may take: well under a second locally; this is
#: the backstop for a rips folder on a slow share.
DEEMPHASIS_WAIT_S: Final[float] = 60.0


def read_arm(root: Path, name: str, *, since: float) -> grading.Arm:
    """The arm in ``root/name``: its one cyanrip log from this run, parsed.

    Thread-safe and Qt-free; called on a helper thread. Never raises: anything
    that stops the read is the arm's ``problem``. Which log is read is
    ``folder_logs.read_one_log``'s rule, shared with ``record-accuracy``.
    """
    found = read_one_log(root, name, since=since)
    if found.problem or found.path is None:
        return grading.Arm(name=name, problem=found.problem or "no log found")
    return grading.arm_from_log(name, str(found.path), parse_cyanrip_log(found.text))


class DeemphasisVerbsMixin:
    """The ``expect-deemphasis-pair`` handler. Type-only declarations of the
    runner surface it uses; the attributes and methods are the runner's."""

    if TYPE_CHECKING:
        _window: QWidget
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

        def _arm_deadline(
            self,
            step: Step,
            seconds: float,
            predicate: Callable[[], bool] | None = None,
        ) -> None: ...

    def _do_expect_deemphasis_pair(self, step: Step) -> None:
        """``expect-deemphasis-pair <forced-folder> <disabled-folder>``."""
        # Imported here: the runner imports this mixin, and the rips folder has
        # ONE reader, the one the `cyanrip` verb runs in.
        from platterpus.uiscript.runner import _ripper_workdir

        forced_name, disabled_name = step.args[0], step.args[1]
        for name in (forced_name, disabled_name):
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
                f"this run has no start time (started_at "
                f"{self._report.started_at!r}), so an earlier run's logs in "
                "these folders cannot be told from this run's",
            )
            return

        def work() -> grading.PairVerdict:
            forced = read_arm(root, forced_name, since=since)
            disabled = read_arm(root, disabled_name, since=since)
            return grading.grade_pair(forced, disabled)

        job = _start(work, "deemphasis")
        outcomes: dict[str, Outcome] = {
            grading.PASS: Outcome.PASS,
            grading.FAIL: Outcome.FAIL,
            grading.NOT_DETERMINED: Outcome.BLOCKED,
        }

        def answered() -> bool:
            if not job.done.is_set():
                return False
            verdict = job.value
            if job.error or not isinstance(verdict, grading.PairVerdict):
                self._deadline_outcome = Outcome.ERROR
                self._deadline_detail = (
                    f"the two arms' logs under {root} could not be read "
                    f"({job.error or 'no answer'}), so clause 2 is not determined"
                )
                return True
            if verdict.state == grading.FAIL:
                log.warning("acceptance P3: %s", verdict.detail)
            self._deadline_outcome = outcomes[verdict.state]
            self._deadline_detail = verdict.detail
            return True

        self._arm_deadline(step, DEEMPHASIS_WAIT_S, answered)
        self._deadline_timeout_detail = (
            f"the two arms' logs under {root} were not read within "
            f"{DEEMPHASIS_WAIT_S:.0f}s, so clause 2 is not determined"
        )
