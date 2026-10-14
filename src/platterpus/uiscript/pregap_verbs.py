"""The acceptance script's cross-rip verb: ``expect-pregaps-agree`` (R10).

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like
:mod:`platterpus.uiscript.probe_verbs`, so the handler is reachable as
``runner._do_expect_pregaps_agree`` while the runner file does not grow.

**What it asks, and why only a whole run can ask it.** Every other grader reads
ONE rip. This one reads every cyanrip log the run wrote and asks whether the rips
of one disc agree about where its pregaps are, naming each track where they do
not. The 2026-10-13 Full run is why: its secure re-read's log left out track 4's
158-frame pregap that the whole-disc rip of the same disc listed, and no grader
noticed, because no grader compared two rips (TASKS R10; the comparison itself
is :mod:`platterpus.uiscript.pregap_grading`).

**Which logs.** Every file under the rips folder (the window's output
directory, the same folder the ``cyanrip`` verb runs in) that cyanrip wrote and
that was modified since this run started: each album's ``.log``, a script
``cyanrip`` verb's ``.log``, and each securing pass's own log, which the rip
keeps beside the album's as ``.platterpus-securing-pass.txt`` and which is a
rip of the same disc too. "Since this run started" is read off the run's own
record (``RunReport.started_at``), so a library of older rips in the folder is
never compared with this run's.

**Outcomes, declared before any disc goes in** (``docs/testing.md`` →
*Acceptance severity*, row P4):

* ``INFO`` when the lists were compared, agreeing (``✓``) or differing (``⚠``,
  every track named). The disagreement is a known detector variance of the
  fork's, it moves no sample, and nothing in a log can say which reading is
  right, so it is gathered for the fork rather than graded against us. It also
  goes to the app log as a warning, so the bundle carries it outside the
  transcript too.
* ``BLOCKED`` when nothing could be compared: no disc had two readable lists.
  That is the floor. A run whose rips left fewer than two comparable logs of one
  disc has lost the logs that are its provenance record, and a check that passed
  on finding nothing would be decoration.
* ``ERROR`` when the scan itself failed, or the run has no start time to scope
  it by: the harness, not the subject.

**Nothing here blocks the GUI thread.** Walking a folder and parsing a dozen
logs runs on a daemon thread that touches nothing Qt; the runner's deadline
polls for the answer once a tick. On a rips folder that is a whole music library
(the script console's default) the walk is bounded by the modification time and
by :data:`MAX_LOGS`, and a cap that bites is said in the answer, never silent.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final

from platterpus.parsers.cyanrip_log import looks_like_cyanrip_log
from platterpus.rip_addendum import SECURING_PASS_LOG_SUFFIX
from platterpus.uiscript import pregap_grading as grading

# The probe verbs' helper-thread runner, reused rather than restated: it keeps a
# failure as text and sets `done` last, which is the contract the deadline reads.
from platterpus.uiscript.probe_verbs import _start
from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript.report import RunReport
    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)

#: How long the scan may take. A session's rips folder is read in well under a
#: second; this is the backstop for a rips folder on a slow share.
PREGAP_WAIT_S: Final[float] = 120.0

#: At most this many of the run's cyanrip logs are compared. A Full run writes
#: about a dozen; the cap bounds a misconfigured rips folder, and how many it
#: left out is part of the answer.
MAX_LOGS: Final[int] = 200

#: A cyanrip log is tens of kilobytes. A file far past that is not read whole
#: into memory on a guess that it might be one; it is named as set aside.
MAX_LOG_BYTES: Final[int] = 8 * 1024 * 1024

#: How much of a candidate is read to see whether cyanrip wrote it, the same
#: bounded sniff the session's album scan uses (`test_session`).
_SNIFF_BYTES: Final[int] = 16 * 1024


@dataclass
class LogScan:
    """What the walk found: the readings, and what it did not read and why."""

    readings: list[grading.GapReading] = field(default_factory=list)
    #: `.log` files from this run that cyanrip did not write (our EAC-layout
    #: export, chiefly). Counted, not listed: they are not rips.
    not_cyanrip: int = 0
    #: Logs past :data:`MAX_LOGS`, newest kept.
    dropped_by_cap: int = 0


def _label(path: Path, root: Path) -> str:
    """The folder a log sits in, relative to the rips folder, and which pass."""
    try:
        where = path.parent.relative_to(root).as_posix()
    except ValueError:
        where = path.parent.as_posix()
    if path.name.endswith(SECURING_PASS_LOG_SUFFIX):
        return f"{where} (securing pass)"
    return where or path.name


def scan_run_logs(root: Path, *, since: float) -> LogScan:
    """Read every cyanrip log under ``root`` modified at or after ``since``.

    Thread-safe and Qt-free: called on a helper thread. A file it cannot read is
    a reading with a problem, never an exception; an unreadable ``root`` raises
    ``OSError`` to the caller, whose helper keeps it as the step's ERROR.
    """
    scan = LogScan()
    candidates: list[tuple[float, Path]] = []
    for pattern in ("*.log", f"*{SECURING_PASS_LOG_SUFFIX}"):
        for path in root.rglob(pattern):
            try:
                stat = path.stat()
            except OSError:
                continue
            if stat.st_mtime >= since and path.is_file():
                candidates.append((stat.st_mtime, path))
    candidates.sort(reverse=True)
    for _modified, path in candidates:
        try:
            if path.stat().st_size > MAX_LOG_BYTES:
                scan.readings.append(
                    grading.GapReading(
                        _label(path, root),
                        "",
                        None,
                        f"it is over {MAX_LOG_BYTES} bytes, so it was not read",
                    )
                )
                continue
            with path.open("rb") as handle:
                head = handle.read(_SNIFF_BYTES)
            if not looks_like_cyanrip_log(head.decode("utf-8", errors="replace")):
                scan.not_cyanrip += 1
                continue
            if len(scan.readings) >= MAX_LOGS:
                scan.dropped_by_cap += 1
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            scan.readings.append(
                grading.GapReading(
                    _label(path, root), "", None, f"it could not be read ({exc})"
                )
            )
            continue
        scan.readings.append(grading.read_gap_list(text, _label(path, root)))
    return scan


def run_start_epoch(started_at: str) -> float | None:
    """The run's start as a POSIX time, read off its own record, or ``None``.

    ``RunReport.started_at`` is written as an aware ISO-8601 moment when the run
    starts; anything else is "not determined" rather than a guessed zero, which
    would compare every log the rips folder has ever held.
    """
    try:
        moment = datetime.fromisoformat(started_at)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        return None
    return moment.timestamp()


def answer(scan: LogScan) -> tuple[Outcome, str, str]:
    """The step's outcome, its detail, and the comparison's state
    (:data:`~platterpus.uiscript.pregap_grading.AGREE` and its two siblings)
    for one scan. Pure; never raises."""
    result = grading.compare(scan.readings)
    notes: list[str] = []
    if scan.dropped_by_cap:
        notes.append(
            f"{scan.dropped_by_cap} more cyanrip log(s) from this run were NOT "
            f"compared: the cap is {MAX_LOGS}, and the newest were kept"
        )
    if scan.not_cyanrip:
        notes.append(
            f"{scan.not_cyanrip} other .log file(s) from this run were not "
            "cyanrip's (the EAC-layout export, chiefly) and were not compared"
        )
    detail = "\n".join([result.detail, *notes])
    if result.state == grading.NOT_DETERMINED:
        return Outcome.BLOCKED, detail, result.state
    return Outcome.INFO, detail, result.state


class PregapVerbsMixin:
    """The ``expect-pregaps-agree`` handler. Type-only declarations of the
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

    def _do_expect_pregaps_agree(self, step: Step) -> None:
        """Compare the pregap lists of every rip of one disc in this run."""
        # Imported here, not at the top: the runner imports this mixin, and the
        # rips folder has ONE reader, the one the `cyanrip` verb runs in.
        from platterpus.uiscript.runner import _ripper_workdir

        root, refused = _ripper_workdir(self._window)
        if root is None:
            self._record(step, Outcome.ERROR, refused)
            return
        since = run_start_epoch(self._report.started_at)
        if since is None:
            self._record(
                step,
                Outcome.ERROR,
                f"this run has no start time to scope the logs by "
                f"(started_at {self._report.started_at!r}), so the rips folder's "
                "older logs cannot be told from this run's",
            )
            return
        job = _start(lambda: scan_run_logs(root, since=since), "pregaps")

        def answered() -> bool:
            if not job.done.is_set():
                return False
            if job.error or not isinstance(job.value, LogScan):
                self._deadline_outcome = Outcome.ERROR
                self._deadline_detail = (
                    f"the rips folder {root} could not be scanned "
                    f"({job.error or 'no answer'}), so whether the pregap lists "
                    "agree is not determined"
                )
                return True
            outcome, detail, state = answer(job.value)
            if state == grading.DIFFER:
                # To the app log too: the bundle carries it, so the finding is
                # not only in a transcript row that reads "info".
                log.warning("acceptance: %s", detail)
            self._deadline_outcome = outcome
            self._deadline_detail = detail
            return True

        self._arm_deadline(step, PREGAP_WAIT_S, answered)
        self._deadline_timeout_detail = (
            f"the rips folder {root} was not scanned within {PREGAP_WAIT_S:.0f}s, "
            "so whether the pregap lists agree is not determined"
        )
