"""The unknown-disc acceptance script's two verbs: the path MusicBrainz cannot answer.

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like
:mod:`platterpus.uiscript.offset_verbs`, so the runner file does not grow.

**Why a second script needs verbs of its own.** ``fullacceptance.txt`` stops at
its section E when the disc is not identified, on purpose: every rip after it
would be evidence about a release nobody chose. So the unknown-album path, the
one a disc MusicBrainz does not know takes, never ran in an acceptance run (TASKS
*"Permutations the acceptance test still does not run"*, (b); ruled 2026-10-05,
``PLANNING.md`` KDD-41 C4: a second script, for a disc MusicBrainz does not know).
That script needs the mirror of ``expect-identified`` and a check that the rip's
own record says what happened:

* ``expect-unidentified`` — the disc was NOT identified and the rip controls are
  in unknown-album mode (the *"Rip as unknown album"* confirmation was accepted),
  with placeholder rows to rip and Picard NOT set to launch: an unattended run
  must not start an external application (``verbs.py``: nothing launches one).
* ``expect-unknown-record`` — the last rip's report records an unknown-album rip
  with no release id, and its placeholder tagging pass did not fail.

The decisions are the two pure functions; the handlers only read the window or
wait for the report, through the runner's own helpers. Nothing here blocks.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from platterpus.uiscript.artifact_grading import Grade
from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript import artifact_grading
    from platterpus.uiscript.script import Step


def grade_unidentified(
    *,
    release_id: str,
    well_formed: bool,
    rows: int,
    unknown_mode: bool | None,
    picker_open: bool,
    picard_pending: bool,
) -> Grade:
    """Is the window ready to rip this disc as an unknown album? Pure.

    Each refusal names its own reason, because each sends the operator somewhere
    different: a disc MusicBrainz knows needs a different disc; a confirmation
    nobody accepted needs the script's ``answer-dialog`` line; Picard set to
    launch would open an application in an unattended run.
    """
    if picker_open:
        return Grade(
            False,
            "MusicBrainz offers releases for this disc (the release picker is "
            "open), so it is not an unknown disc: this script needs a disc "
            "MusicBrainz does not know, such as a CD-R of your own recordings",
        )
    if release_id:
        what = "release" if well_formed else "a malformed release id"
        return Grade(
            False,
            f"the disc was identified ({what} {release_id!r}): this script needs a "
            "disc MusicBrainz does not know, such as a CD-R of your own recordings",
        )
    if rows < 1:
        return Grade(
            False,
            "no track rows are loaded, so there is nothing to rip as an unknown "
            "album: the disc scan did not finish, or found no audio tracks",
        )
    if unknown_mode is not True:
        return Grade(
            False,
            f"the disc was not identified and {rows} placeholder row(s) are loaded, "
            "but the rip controls are not in unknown-album mode: the 'Rip as unknown "
            "album' confirmation was not accepted, so Start would refuse",
        )
    if picard_pending:
        return Grade(
            False,
            "MusicBrainz Picard is set to launch when this rip finishes, and an "
            "unattended run must not start an external application",
        )
    return Grade(
        True,
        f"not identified, as this script needs: no release id, {rows} placeholder "
        "row(s), unknown-album mode on, Picard not set to launch",
    )


def grade_unknown_record(report: Mapping[str, Any]) -> Grade:
    """The rip's own report says it was an unknown-album rip, tagged. Pure.

    Reads the report's ``disc`` block (``unknown``, ``musicbrainz_release_id``)
    and its ``issues``, where a failed placeholder tagging pass is filed as
    ``tagging_failed`` (``rip_report._tagging`` makes no block of its own). A
    block that is missing is a FAIL, never a pass: a record that does not say
    which path it took has not said it took this one.
    """
    disc = report.get("disc")
    if not isinstance(disc, dict):
        return Grade(False, "the report has no `disc` block, so it records no path")
    if disc.get("unknown") is not True:
        return Grade(
            False,
            f"the report records `unknown: {disc.get('unknown')!r}`, not an "
            "unknown-album rip",
        )
    release = disc.get("musicbrainz_release_id")
    if release:
        return Grade(
            False,
            f"the report records an unknown-album rip WITH release {release!r}: the "
            "record disagrees with itself",
        )
    issues = report.get("issues")
    failed = [
        issue
        for issue in (issues if isinstance(issues, list) else [])
        if isinstance(issue, dict) and issue.get("code") == "tagging_failed"
    ]
    if failed:
        return Grade(
            False,
            f"the placeholder tagging pass failed: {failed[0].get('detail') or failed[0]}",
        )
    return Grade(
        True,
        "the report records an unknown-album rip, with no release id and no "
        "tagging failure",
    )


class UnknownDiscVerbsMixin:
    """The ``expect-unidentified`` and ``expect-unknown-record`` handlers.
    Type-only declarations of the runner surface they use."""

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

        def _grade_when_settled(
            self,
            step: Step,
            folder: Path,
            grade: Callable[[Path, dict[str, Any]], artifact_grading.Grade],
            *,
            grade_unfinished: bool = False,
        ) -> None: ...

    def _do_expect_unidentified(self, step: Step) -> None:
        """The disc was not identified, and the window will rip it as unknown.

        Reads the same release id ``expect-identified`` reads, through the same
        helper, so the two verbs cannot disagree about what "identified" means.
        """
        # Read here: the runner imports this mixin, so a top-level import of the
        # runner would be circular.
        from platterpus.uiscript.runner import (
            _MBID_RE,
            _held_release_id,
            _release_picker,
        )

        window = self._window
        release_id = _held_release_id(window)
        table = getattr(window, "_track_table", None)
        controls = getattr(window, "_rip_controls", None)
        is_unknown = getattr(controls, "is_unknown_mode", None)
        grade = grade_unidentified(
            release_id=release_id,
            well_formed=bool(_MBID_RE.match(release_id)),
            rows=len(table.tracks()) if table is not None else 0,
            unknown_mode=bool(is_unknown()) if callable(is_unknown) else None,
            picker_open=_release_picker() is not None,
            picard_pending=bool(getattr(window, "_pending_picard_launch", False)),
        )
        self._record(step, Outcome.PASS if grade.passed else Outcome.FAIL, grade.detail)

    def _do_expect_unknown_record(self, step: Step) -> None:
        """The last rip's report records the unknown-album path. Waits to settle."""
        folder = self._rip_album_dir(step)
        if folder is None:
            return  # the shared reader recorded the FAIL and said why
        self._grade_when_settled(
            step, folder, lambda _path, report: grade_unknown_record(report)
        )
