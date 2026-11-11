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

    def _do_expect_track_records(self, step: Step) -> None:
        """Every track's record is truthful, in the EAC-layout log and the report (G3).

        FAIL on ``Accurately ripped`` for a track a CTDB repair rewrote, on any
        ``OK`` over reads that disagree, or on a track with no record; BLOCKED
        when the report predates per-track records. Waits for the record to
        settle, so a CTDB repair still running is waited for, and graded once it
        has rewritten the log. Severity ARCHIVAL, declared in
        :mod:`platterpus.uiscript.track_record_grading`.
        """
        from platterpus.uiscript import track_record_grading

        folder = self._rip_album_dir(step)
        if folder is None:
            return  # the shared reader recorded the FAIL and said why
        self._grade_when_settled(
            step,
            folder,
            lambda path, report: track_record_grading.grade_track_records(report, path),
        )

    def _do_expect_derived_files(self, step: Step) -> None:
        """Each derived file's own length, tags, art and encoder (C4).

        ``expect-derived-files <mp3|wavpack|wav> [quality]``: the quality is the
        ``mp3_vbr_quality`` the script set, required for MP3 and refused for the
        others, so the step states what it proves rather than reading Settings
        back (a setting checked against itself).
        """
        from platterpus.uiscript import derived_grading

        fmt = step.args[0]
        if fmt not in derived_grading.FORMATS:
            self._record(step, Outcome.ERROR, f"{fmt!r} is not mp3, wavpack or wav")
            return
        quality: int | None = None
        if len(step.args) > 1:
            if fmt != "mp3" or not (step.args[1].isascii() and step.args[1].isdigit()):
                self._record(
                    step,
                    Outcome.ERROR,
                    f"{step.args[1]!r}: only mp3 takes a quality, a whole number",
                )
                return
            quality = int(step.args[1])
        elif fmt == "mp3":
            self._record(step, Outcome.ERROR, "name the mp3_vbr_quality the script set")
            return
        folder = self._rip_album_dir(step)
        if folder is None:
            return
        expected = self._expected_tags(folder)
        if expected is None:
            self._record(
                step,
                Outcome.ERROR,
                f"no record of the tags the rip in {folder.name} was handed, so "
                "there is nothing to compare its derived files with",
            )
            return
        mode = str(getattr(getattr(self._window, "_config", None), "cover_art", ""))
        self._grade_when_settled(
            step,
            folder,
            lambda _path, report: derived_grading.grade_derived_files(
                report, folder, fmt, expected, mode, quality
            ),
        )
