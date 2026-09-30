"""The acceptance script's artifact verbs: grade what a rip left on disk.

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, so each
handler stays reachable as ``runner._do_<verb>`` (the dispatcher looks them up
by name) while the runner file does not grow — the same split ``MainWindow``
uses (``docs/architecture.md``). The grading itself is in
:mod:`platterpus.uiscript.artifact_grading`, pure and tested against committed
rip reports; these handlers only find this section's rip, wait for its record
to settle, and hand the answer to ``_record``.

**Why they wait.** The report is rewritten as each post-rip check lands, after
``wait-for-rip`` has returned — the deferral ``expect-verification`` documents.
Grading the report before it settles would grade a record the product has not
finished writing, so every verb here polls :func:`artifact_grading.
settle_state`, the one predicate ``expect-verification`` also uses.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from platterpus.uiscript import artifact_grading as grading
from platterpus.uiscript import tag_grading
from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.parsers.rip_log import RipLog
    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)

#: How long an artifact verb waits for the rip's record to settle. The same
#: default as ``expect-verification``; in the script these verbs come after it,
#: so on a healthy run the record has already settled and the wait is zero.
ARTIFACT_WAIT_S: Final[float] = 600.0


class ArtifactVerbsMixin:
    """The ``expect-album-audit`` … ``track-title`` handlers.

    Type-only declarations of the runner surface these methods use, so mypy can
    check them; the attributes and methods themselves are the runner's.
    """

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

        def _rip_log_from_disk(self, step: Step) -> RipLog | None: ...

        def _rip_album_dir(self, step: Step) -> Path | None: ...

    def _grade_when_settled(
        self,
        step: Step,
        folder: Path,
        grade: Callable[[Path, dict[str, Any]], grading.Grade],
        *,
        grade_unfinished: bool = False,
    ) -> None:
        """Wait for this rip's report to settle, then grade it once.

        ``grade_unfinished`` is for the one verb whose question still stands
        after a cancelled rip (``expect-album-audit ripper_log_integrity``: did
        cyanrip sign off the record it was stopped in the middle of). Every
        other grader FAILs an unfinished rip at once, the way
        ``expect-verification`` does — there is nothing for it to wait for.
        """

        def settled() -> bool:
            path = grading.report_path(folder)
            report = grading.read_report(path) if path is not None else None
            state = grading.settle_state(report)
            if path is None or report is None or state == grading.SETTLE_PENDING:
                return False
            if state == grading.SETTLE_UNFINISHED and not grade_unfinished:
                self._deadline_outcome = Outcome.FAIL
                self._deadline_detail = (
                    f"the rip for {folder.name} did not finish, so there is "
                    f"nothing here to grade — the rip's own failure is the finding"
                )
                return True
            result = grade(path, report)
            self._deadline_outcome = (
                Outcome.BLOCKED
                if result.blocked
                else (Outcome.PASS if result.passed else Outcome.FAIL)
            )
            self._deadline_detail = result.detail
            return True

        self._arm_deadline(step, ARTIFACT_WAIT_S, settled)
        self._deadline_timeout_detail = (
            f"the report for {folder.name} did not settle within "
            f"{ARTIFACT_WAIT_S:.0f}s — its checks are still running, or one was "
            f"dropped (see its `issues`). An unsettled record is not graded."
        )

    def _do_expect_album_audit(self, step: Step) -> None:
        """Grade the rip's own self-audit, re-run now against the files on disk.

        With no arguments every registered check must run, not warn, and reach
        ok; naming checks grades only those (the cancel section asks only
        whether cyanrip still verifies its log). The twelve checks were already
        embedded in every report as ``self_check`` — and nothing graded them.
        """
        folder = self._rip_album_dir(step)
        if folder is None:
            return  # the shared reader recorded the FAIL and said why
        only = tuple(step.args)
        self._grade_when_settled(
            step,
            folder,
            lambda path, _report: grading.grade_album_audit(path, only),
            grade_unfinished=bool(only),
        )

    def _do_expect_accuraterip(self, step: Step) -> None:
        """Every ripped track has an AccurateRip answer, and the report agrees."""
        parsed = self._rip_log_from_disk(step)
        if parsed is None:
            return
        log_file = getattr(self._window, "_last_rip_log_file", None)
        if log_file is None:  # pragma: no cover — the reader above requires it
            self._record(step, Outcome.FAIL, "the rip log's path is unknown")
            return
        self._grade_when_settled(
            step,
            Path(log_file).parent,
            lambda _path, report: grading.grade_accuraterip(parsed, report),
        )

    def _do_expect_ctdb(self, step: Step) -> None:
        """CTDB reached the verdict the rip's scope calls for (whole | partial)."""
        folder = self._rip_album_dir(step)
        if folder is None:
            return
        scope = step.args[0]
        if scope not in ("whole", "partial"):
            self._record(step, Outcome.ERROR, f"{scope!r} is not `whole` or `partial`")
            return
        self._grade_when_settled(
            step, folder, lambda _path, report: grading.grade_ctdb(report, scope)
        )

    def _expected_tags(self) -> tag_grading.ExpectedTags | None:
        """The album, artist and titles the user chose, from the track table."""
        table = getattr(self._window, "_track_table", None)
        if table is None:
            return None
        album = table.album_metadata()
        return tag_grading.ExpectedTags(
            album=album.title,
            album_artist=album.artist,
            tracks={t.number: (t.title, t.artist_credit) for t in table.tracks()},
        )

    def _do_expect_tags(self, step: Step) -> None:
        """Every ripped FLAC carries exactly the album, artist and titles chosen."""
        folder = self._rip_album_dir(step)
        if folder is None:
            return
        expected = self._expected_tags()
        if expected is None:
            self._record(step, Outcome.ERROR, "no track table on the window")
            return
        self._grade_when_settled(
            step,
            folder,
            lambda _path, report: tag_grading.grade_tags(
                tag_grading.ripped_masters(report, folder), expected
            ),
        )

    def _do_expect_cover_art(self, step: Step) -> None:
        """The cover art on disk is what the ``cover_art`` setting asks for."""
        folder = self._rip_album_dir(step)
        if folder is None:
            return
        config = getattr(self._window, "_config", None)
        mode = str(getattr(config, "cover_art", ""))
        release_id = str(getattr(self._window, "_current_release_id", "") or "")
        self._grade_when_settled(
            step,
            folder,
            lambda _path, report: tag_grading.grade_cover_art(
                tag_grading.ripped_masters(report, folder), report, mode, release_id
            ),
        )

    def _do_track_title(self, step: Step) -> None:
        """Set one track's title, as a typed edit would."""
        table = getattr(self._window, "_track_table", None)
        if table is None:
            self._record(step, Outcome.ERROR, "no track table on the window")
            return
        try:
            number = int(step.args[0])
        except ValueError:
            self._record(step, Outcome.ERROR, f"{step.args[0]!r} is not a track number")
            return
        title = step.joined(1)
        refused = table.edit_track_title(number, title)
        if refused:
            self._record(
                step, Outcome.FAIL, f"track {number}'s title was not set: {refused}"
            )
            return
        self._record(step, Outcome.PASS, f"track {number} title set to {title!r}")
