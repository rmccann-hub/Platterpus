"""The acceptance script's permutation verbs: settings no other rip uses.

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like
:mod:`platterpus.uiscript.artifact_verbs`, so each handler is reachable as
``runner._do_<verb>`` while the runner file does not grow.

* ``set-library-scratch`` — point ``library_dir`` at a scratch folder inside the
  run's rips folder, so a library move can be tested without the user's library.
* ``expect-library-move`` — the last rip's album folder was filed there.
* ``expect-rip-argv`` — the last rip's argv carried a flag, or left it out.

Written for section J2 (TASKS *"Permutations the acceptance test still does not
run"*). The decisions are pure and live in
:mod:`platterpus.uiscript.permutation_grading`; these handlers only find this
section's rip, wait for it to settle, and record the answer.

**Nothing here blocks the GUI thread.** The waits are the runner's deadline
machinery: a predicate polled once a tick, which reads a path and globs one
folder, both bounded by the folder's size.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from platterpus.uiscript import permutation_grading as grading
from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript import artifact_grading
    from platterpus.uiscript.script import Step

#: How long ``expect-library-move`` waits for the album to be filed. The move
#: runs only once every post-rip check has finished (the window's
#: `_post_rip_work_settled`), and ``expect-verification`` waits 600 s for those
#: same checks, so the move gets the same budget.
LIBRARY_MOVE_WAIT_S: Final[float] = 600.0

#: The two words ``expect-rip-argv`` takes before its flag.
_WITH: Final[str] = "with"
_WITHOUT: Final[str] = "without"


class PermutationVerbsMixin:
    """The ``set-library-scratch``, ``expect-library-move`` and
    ``expect-rip-argv`` handlers. Type-only declarations of the runner surface
    they use; the attributes and methods themselves are the runner's."""

    if TYPE_CHECKING:
        _window: QWidget
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

        def _do_set(self, step: Step) -> None: ...

        def _rip_album_dir(self, step: Step) -> Path | None: ...

        def _grade_when_settled(
            self,
            step: Step,
            folder: Path,
            grade: Callable[[Path, dict[str, Any]], artifact_grading.Grade],
            *,
            grade_unfinished: bool = False,
        ) -> None: ...

    def _do_set_library_scratch(self, step: Step) -> None:
        """Set ``library_dir`` to ``<output_dir>/libraryscratch``.

        **A verb, because the value cannot be typed.** The library folder must
        be an absolute path, and the run's rips folder is only known once the
        session has made it, so no ``set library_dir …`` line could name it on
        every machine. ``set library_dir ""`` turns the move off again.

        **Delegated to ``set``, never restated**: the one path that validates a
        value, installs it, pushes it to the rip controls and saves it, so this
        verb cannot write a library folder the Settings dialog would refuse.
        """
        config = getattr(self._window, "_config", None)
        output = str(getattr(config, "output_dir", "") or "")
        scratch, problem = grading.scratch_library_dir(output)
        if scratch is None:
            self._record(step, Outcome.FAIL, f"no scratch library was set: {problem}")
            return
        self._do_set(dataclasses.replace(step, args=("library_dir", str(scratch))))

    def _do_expect_library_move(self, step: Step) -> None:
        """The last rip's album folder was filed in the library folder.

        **It WAITS, and on what the product records.** The window files a rip
        only after every post-rip check has finished, then repoints
        ``_last_rip_log_file`` at the album's new home
        (``MainWindow._on_library_moved``). So a step that looked once would
        assert the move was *requested*; this one polls until the window's own
        pointer has moved into the library, then reads the folder on disk.

        Refuses at once when the library folder is off, because then no rip is
        ever filed and waiting would only spend the timeout.
        """
        config = getattr(self._window, "_config", None)
        library_text = str(getattr(config, "library_dir", "") or "").strip()
        if not library_text:
            self._record(
                step,
                Outcome.FAIL,
                "library_dir is off, so no rip is filed anywhere — put "
                "`set-library-scratch` above the `rip`",
            )
            return
        # The freshness guard: this must be the rip THIS section started, and
        # its log must be readable where the window says it is.
        before = self._rip_album_dir(step)
        if before is None:
            return  # the shared reader recorded the FAIL and said why
        library = Path(library_text)

        def filed() -> bool:
            log_file = getattr(self._window, "_last_rip_log_file", None)
            grade = grading.grade_library_move(log_file, library, before)
            if grade is None:
                return False
            self._deadline_outcome = Outcome.PASS if grade.passed else Outcome.FAIL
            self._deadline_detail = grade.detail
            return True

        self._arm_deadline(step, LIBRARY_MOVE_WAIT_S, filed)
        self._deadline_timeout_detail = (
            f"the album was not filed in {library} within {LIBRARY_MOVE_WAIT_S:.0f}s "
            f"and is still at {before}: the move failed (the rip's log pane and "
            "the app log say why), a post-rip check never finished, or a newer "
            "rip started, which abandons it"
        )

    def _do_expect_rip_argv(self, step: Step) -> None:
        """``expect-rip-argv <with|without> <flag>`` — what the last rip SENT.

        Reads the argv recorded in the rip's report once the record has settled
        (``_grade_when_settled``, shared with the artifact verbs), and grades it
        with :func:`permutation_grading.grade_rip_argv`. A wrong first word or a
        flag that is not spelled like one is an ERROR in the script, not a FAIL
        of the rip: the step never asked a question.
        """
        mode = step.args[0].casefold()
        flag = step.args[1]
        if mode not in (_WITH, _WITHOUT):
            self._record(
                step,
                Outcome.ERROR,
                f"{step.args[0]!r} is neither `{_WITH}` nor `{_WITHOUT}`",
            )
            return
        problem = grading.flag_problem(flag)
        if problem:
            self._record(step, Outcome.ERROR, problem)
            return
        folder = self._rip_album_dir(step)
        if folder is None:
            return  # the shared reader recorded the FAIL and said why
        present = mode == _WITH
        self._grade_when_settled(
            step,
            folder,
            lambda _path, report: grading.grade_rip_argv(report, flag, present=present),
        )
