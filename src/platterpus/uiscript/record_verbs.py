"""Acceptance verbs that grade a verdict the rip's report computed, or its derived files.

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like the
other ``*_verbs`` modules, so each handler stays reachable as
``runner._do_<verb>`` while the runner file does not grow. The grading is pure
and lives in :mod:`platterpus.uiscript.record_grading` and
:mod:`platterpus.uiscript.derived_grading`; these handlers find this section's
rip and wait for its record to settle through
:meth:`~platterpus.uiscript.artifact_verbs.ArtifactVerbsMixin._grade_when_settled`,
the one wait every artifact verb shares.

Added for the review of the owner's 2026-11-03 Full run: C3 (nothing asserted
the read offset a rip used) and C4 (sections K1 to K3 graded the FLAC masters,
never the MP3, WavPack and WAV files a user of those formats keeps).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from platterpus.uiscript import record_grading
from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript import artifact_grading, tag_grading
    from platterpus.uiscript.script import Step


class RecordVerbsMixin:
    """The ``expect-read-offset`` and ``expect-derived-files`` handlers.

    Type-only declarations of the runner surface these methods use, so mypy can
    check them; the attributes and methods themselves are the runner's and
    :class:`~platterpus.uiscript.artifact_verbs.ArtifactVerbsMixin`'s.
    """

    if TYPE_CHECKING:
        _window: QWidget

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

        def _rip_album_dir(self, step: Step) -> Path | None: ...

        def _expected_tags(self, folder: Path) -> tag_grading.ExpectedTags | None: ...

        def _grade_when_settled(
            self,
            step: Step,
            folder: Path,
            grade: Callable[[Path, dict[str, Any]], artifact_grading.Grade],
            *,
            grade_unfinished: bool = False,
            still_waiting: Callable[[dict[str, Any]], bool] | None = None,
            still_waiting_s: float = 0.0,
        ) -> None: ...

    def _do_expect_read_offset(self, step: Step) -> None:
        """The read offset this rip used is the drive's, read from its report (C3).

        PASS when the AccurateRip drive list agrees or AccurateRip confirmed the
        offset on this disc; FAIL when the list gives another offset or the
        ``-s`` we sent is not what the log says was applied; BLOCKED (not
        determined, never a pass) otherwise.
        """
        folder = self._rip_album_dir(step)
        if folder is None:
            return  # the shared reader recorded the FAIL and said why
        self._grade_when_settled(
            step,
            folder,
            lambda _path, report: record_grading.grade_read_offset(report),
        )
