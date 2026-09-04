"""The executor: one step per event-loop tick, driving the real widgets.

**Why a timer and not a loop.** This runs on the GUI thread. A
``for step in steps: do(step)`` would freeze the window for the whole batch —
``CLAUDE.md``'s never-block rule, which this project has paid for three times —
and it would *deadlock outright* the first time a step opened a modal, because
``exec()`` does not return until the dialog closes and the loop would never reach
the step that closes it.

A ``QTimer`` inverts that. Each tick executes exactly one step and returns to the
event loop. Qt keeps delivering timer events **inside a modal dialog's nested
event loop**, so the runner can open a modal on one tick and dismiss it on a
later one. That property is the entire reason this design can test the release
picker — the case that prompted the feature, where the maintainer could not tell
a waiting modal from a hung app.

It also makes the run *human-paced* rather than instantaneous, which is what the
maintainer asked for ("do all commands human like"): each step is separated by at
least one event-loop turn, so repaints happen and a screenshot shows what a
person would have seen.

**Failure policy.** A failing step is recorded and the batch continues. Only
``abort``, a stop from the console, or the window disappearing ends a run early —
and in every one of those cases ``ended_reason`` is set, because a transcript
that stops without a verdict reads exactly like one that passed.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QAbstractButton, QApplication, QDialog, QWidget

from platterpus import __version__, build_info
from platterpus.uiscript.report import Outcome, RunReport, StepRecord, render
from platterpus.uiscript.script import Step, sanitise_cyanrip_args
from platterpus.uiscript.verbs import OPENABLE, VERBS

log = logging.getLogger(__name__)

#: Gap between steps. Long enough that Qt repaints and a screenshot shows a
#: settled frame, short enough that a 60-step batch is not a coffee break.
TICK_MS: int = 120

#: Hard ceiling on a single `wait`. A pasted typo of `wait 100000` must not
#: strand an unattended run for a day.
MAX_WAIT_S: float = 600.0

#: Hard ceiling on `wait-for-rip`. Bounded so an unattended batch cannot be
#: stranded by a wedged rip that never finishes.
#:
#: **SIX HOURS, RAISED FROM THREE ON 2026-08-29, AND THE OLD VALUE WAS SET
#: AGAINST THE WRONG OPERATION.** Its note read *"a full disc is ~50-70 minutes
#: on this hardware; three hours is generous"* — true of an ordinary rip and not
#: of the longest wait the suite actually performs. `fullacceptance.txt` §N is a
#: whole-disc **uniform secure re-read**, which this project's own rig sheet puts
#: at **2 to 2.5 hours**, and that section asks for `wait-for-rip 21600` — six
#: hours, because its author meant *"wait a long time"*. So the cap sat barely
#: above the expected duration of the very step most likely to exceed it.
#:
#: What the clamp then does is honest — it logs, it marks the outcome `[CLAMPED
#: …]`, and it waits the cap rather than skipping the wait — but honesty is not
#: safety here. **Past the cap the batch continues while the rip is still
#: running**, and §N is followed by `rig-check` (which would read a half-written
#: album) and then §P's `cyanrip -x -I` (which touches the drive the ripper still
#: holds). Every step after the timeout measures a machine state the script does
#: not think it is in — the same failure `abort-if-failed`'s docstring describes
#: for a wrong ripper: not partially useful, but *evidence about a different
#: subject*.
#:
#: The rule that replaces the guess: **the cap is at least as large as the
#: longest wait any committed script asks for**, which
#: `tests/test_rig_scripts.py` now enforces by deriving both sides. A cap chosen
#: from a remembered duration is a number nobody re-checks when the suite grows a
#: slower step; a cap checked against the scripts fails in CI the day it does.
MAX_RIP_WAIT_S: float = 6 * 60 * 60

#: Sentinel for "no `rip` step has run yet in this batch".
#:
#: `None` cannot serve: it is a legitimate value of `window._last_rip_log` — the
#: state a fresh window is in — so a `None` marker could not tell "no rip was
#: requested" from "a rip was requested while no log existed". Two facts, and
#: giving them one slot is the defect this project keeps paying for.
_NO_RIP_REQUESTED: Final[object] = object()

#: Timeout for a scripted `cyanrip` invocation. Generous enough for a cold
#: container exec (measured at 3.45 s) and a `-x` cache probe, bounded so an
#: unattended batch cannot be stranded by a wedged drive.
CYANRIP_VERB_TIMEOUT_S: float = 300.0

#: Cap on captured tool output carried into a single transcript record.
MAX_TOOL_OUTPUT_CHARS: int = 8000

#: Grace on top of `CYANRIP_VERB_TIMEOUT_S` before the runner stops waiting for
#: its own helper thread. `run_capture` enforces the timeout itself and kills the
#: child, so this only fires when the child is **unreapable** — wedged in a drive
#: ioctl, where even SIGKILL does not land (`CLAUDE.md`, Qt threading rules). The
#: runner then reports an unreapable child and moves on rather than waiting
#: forever, which is the whole difference between a bounded run and a hung one.
CYANRIP_VERB_GRACE_S: float = 20.0

#: Outer bound on the `rig-check` verb. Its two ripper probes are each bounded at
#: `platterpus.rig_check.PROBE_TIMEOUT_S`, so this only fires when one of them is
#: unreapable — same case, same reasoning, as `CYANRIP_VERB_GRACE_S`. Generous
#: enough to cover both probes plus a cold container exec, and still finite.
RIG_CHECK_VERB_TIMEOUT_S: float = 360.0


def _coerce_setting(current: object, raw: str) -> tuple[object, str]:
    """Turn a script's string into the type the config field already holds.

    Returns ``(value, "")`` or ``(None, reason)``. The *existing* value decides the
    type rather than a table of field names, so a new setting needs no entry here —
    the same reason the verb takes a config field name at all.

    ``bool`` is checked before ``int`` because ``bool`` is an ``int`` subclass, and a
    field holding ``False`` would otherwise be parsed as a number and set to ``0`` —
    equal to ``False`` today and a different thing the moment anything compares
    identity or writes it back to TOML.
    """
    text = raw.strip()
    if isinstance(current, bool):
        lowered = text.casefold()
        if lowered in {"on", "true", "yes", "1"}:
            return True, ""
        if lowered in {"off", "false", "no", "0"}:
            return False, ""
        return None, f"{text!r} is not on/off (accepted: on, off, true, false, yes, no)"
    if isinstance(current, int):
        try:
            return int(text), ""
        except ValueError:
            return None, f"{text!r} is not a whole number"
    if isinstance(current, float):
        try:
            return float(text), ""
        except ValueError:
            return None, f"{text!r} is not a number"
    if isinstance(current, str):
        return text, ""
    return None, f"settings of type {type(current).__name__} cannot be set by script"


def _validation_error_for(candidate: object, field: str) -> str:
    """The validator's own complaint about ``field``, or ``""`` if it has none.

    Delegates to `settings_validation` rather than re-checking anything: a second
    copy of a safety check is a second thing to drift, and this one already exists,
    is pure, and is what the Settings dialog is held to.
    """
    try:
        from platterpus.settings_validation import validate_config

        issues = validate_config(candidate)  # type: ignore[arg-type]  # a Config
    except Exception:  # noqa: BLE001 — a validator fault must not become a silent set
        log.exception("settings validation raised while checking %s", field)
        return "the settings validator could not evaluate this value"
    for issue in issues:
        if getattr(issue, "field", "") != field:
            continue
        # Only a hard error blocks. A warning is advice — the Settings dialog shows
        # it and still lets a person proceed, so a script must not be stricter than
        # the UI it is standing in for.
        #
        # `is_error` is a METHOD, not a property, and it has to be CALLED. Reading it
        # as an attribute yields a bound method, which is always truthy — so every
        # warning would have been reported as a rejection and the verb would refuse
        # values the dialog accepts. Exactly the shape of the "check that can be
        # satisfied by the wrong thing" this project keeps finding, and
        # `test_uiscript_settings.py` pins it with a warning-level field.
        if issue.is_error():
            return str(getattr(issue, "message", "rejected"))
    return ""


def _parse_track_spec(spec: str) -> tuple[list[int], str]:
    """``"1,3,5-7"`` → ``[1, 3, 5, 6, 7]``. Returns ``(numbers, "")`` or ``([], why)``.

    Bounded deliberately: a range is capped so a typo like ``1-999999`` is refused
    rather than materialised into a list that stalls the GUI thread building it.
    """
    numbers: set[int] = set()
    for chunk in spec.replace(" ", "").split(","):
        if not chunk:
            continue
        if "-" in chunk.lstrip("-"):
            low_text, _, high_text = chunk.partition("-")
            try:
                low, high = int(low_text), int(high_text)
            except ValueError:
                return [], f"{chunk!r} is not a track range like 5-7"
            if low > high:
                return [], f"{chunk!r} counts backwards"
            if high - low > _MAX_TRACK_RANGE:
                return [], f"{chunk!r} spans more than {_MAX_TRACK_RANGE} tracks"
            numbers.update(range(low, high + 1))
            continue
        try:
            numbers.add(int(chunk))
        except ValueError:
            return [], f"{chunk!r} is not a track number"
    if not numbers:
        return [], f"{spec!r} named no tracks"
    return sorted(numbers), ""


#: Widest range a single `select-tracks` chunk may expand to. A CD holds 99 tracks;
#: this is generous and still refuses a pasted typo.
_MAX_TRACK_RANGE: int = 200

#: The MusicBrainz release picker's window title, used to point a blocked `rip`
#: at the verb that actually answers it.
#:
#: **A second description of one fact, which is only safe because a test ties
#: them**: `tests/test_uiscript_runner.py` asserts this equals the title
#: `ui.release_picker.ReleasePicker` really sets. Read here rather than imported
#: because `rip`'s guard runs on every rip step and must not pull a widget module
#: in to compare a string.
_RELEASE_PICKER_TITLE: Final[str] = "Pick a MusicBrainz release"


@dataclass
class _CyanripJob:
    """A `cyanrip` verb running on a helper thread, watched by the tick.

    **Why a thread at all.** ``run_capture`` can take up to five minutes, and
    ``CLAUDE.md``'s never-block rule has no case exemption: five minutes of a
    dead window is exactly the "Not Responding" the maintainer reports on sight.
    The first version of this verb ran it inline and justified it in a comment —
    the shape this project has an explicit rule against (*a comment where a check
    belongs is not a fix*).

    **Why not a QThread.** Nothing here needs a Qt event loop; a daemon thread
    reporting back through a value the tick polls is the lighter of the two
    options ``CLAUDE.md`` permits, and it carries none of the ownership
    obligations a ``QThread`` slot would (``tests/test_qthread_ownership.py``).

    **Publication.** The worker writes ``result``/``error`` and *then* sets
    ``done``; the tick reads them only after seeing ``done``. That ordering is
    the whole synchronisation — no lock, and no field read before it is written.
    """

    step: Step
    argv: list[str]
    started: float
    done: threading.Event
    result: tuple[int, str] | None = None
    error: str = ""


@dataclass
class _RigCheckJob:
    """A `rig-check` verb running on a helper thread, watched by the tick.

    Same shape and same reasoning as :class:`_CyanripJob` — the seam check runs
    the ripper twice (``-v``, then a ``-j`` probe), so it is subprocess work and
    the never-block rule applies with no case exemption.

    It is a *separate* job type rather than a reuse of ``_CyanripJob`` because
    the two carry different results: a cyanrip call yields ``(exit, output)``
    that ``expect-cyanrip`` / ``expect-exit`` then assert against, and letting a
    rig check overwrite ``_last_cyanrip_exit`` would silently change what a
    following assertion was talking about.
    """

    step: Step
    out_dir: Path
    album_dir: Path | None
    started: float
    done: threading.Event
    #: Exit code of the check: 0 when nothing FAILed. ``None`` means the worker
    #: died before producing one — tri-state, never written as 0.
    code: int | None = None
    lines: list[str] = field(default_factory=list)
    error: str = ""


def _preflight(steps: list[Step]) -> list[str]:
    """Every step that cannot run as written, found before step 1 runs.

    Two kinds, and both were learned the same way — from a long hardware batch
    discovering at step N what the file already said at parse time.

    **`cyanrip` steps the sanitiser will refuse.** Reruns the **real** sanitiser
    rather than a summary of its rules — a second description of what is refused
    would drift from the guard the first time either changed, and the wrong copy
    is the one the operator would be reading. Found while validating the cyanrip
    fork's returned round-8 script: three of their six ripper tests would have
    been refused, and nothing would have said so until each one's turn came round.

    **Verbs with no handler.** Added 2026-08-24. The verb table can mark a verb
    unimplemented and the generated reference prints `NOT IMPLEMENTED`, but that
    is only read by whoever reads it: the full-acceptance script used
    `expect-status` and found out at **step 179 of 288, 1h 49m in**, because the
    handler lookup happens at dispatch. The check that fixes it was already here,
    one function wide, doing the identical job for a different verb — the same
    shape as `docs/testing.md` §5.o (enforce a rule across the surface, not at the
    place it was learned) and as the `-V` half-contract lesson, where the evidence
    sat in a committed file for a full round. `uiscript.script.uses_unsafe` states
    the principle outright: *"an unattended run that dies two-thirds through is
    worse than one that never started."*

    Does **not** filter or reorder the run. Those steps still execute and still
    record their own failures in place; this only moves the *notice* earlier — the
    file's contract is that a bad step never stops the batch.
    """
    problems: list[str] = []
    for step in steps:
        if not step.ok:
            continue
        verb = VERBS.get(step.verb)
        if verb is not None and not verb.implemented:
            problems.append(
                f"L{step.line_no}: {step.source} — '{step.verb}' is in the verb "
                "table with no handler, so this step will ERROR. See the "
                "'NOT IMPLEMENTED' rows in docs/script-language.md"
            )
            continue
        if step.verb != "cyanrip":
            continue
        refusal = sanitise_cyanrip_args(list(step.args))
        if refusal is not None:
            problems.append(f"L{step.line_no}: {step.source} — {refusal}")
    return problems


class ScriptRunner(QObject):
    """Runs parsed steps against a live MainWindow, one per event-loop tick.

    The window is passed in rather than discovered, so tests can drive a real
    ``MainWindow`` built by the existing fixture and nothing has to guess which
    top-level is "the app".
    """

    #: Emitted after each step with its :class:`StepRecord`. Payload is typed
    #: `object` because Qt's queued connections force it (CLAUDE.md typing rule).
    step_recorded = Signal(object)  # StepRecord
    #: Emitted once, with the finished :class:`RunReport`.
    finished = Signal(object)  # RunReport

    def __init__(self, window: QWidget, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._window: QWidget = window
        self._steps: list[Step] = []
        self._index: int = 0
        self._report: RunReport = RunReport(started_at="", app_version=__version__)
        self._unsafe_allowed: bool = False
        self._artifact_dir: Path | None = None
        #: The daemon thread building this run's single-file evidence bundle, kept
        #: so the unattended-quit helper can WAIT for it. Retained rather than
        #: fire-and-forget: `_write_run_bundle` archives the app log (megabytes,
        #: with rotations) plus every screenshot the run took, and the quit helper
        #: ticks once a second — measured at **215 ms for 169 files** on the
        #: 2026-08-24 overnight run, i.e. it finished with under a second to spare
        #: on a run whose bundle is the entire deliverable. A plain `threading`
        #: thread, not a QThread, so retaining it carries none of the `~QThread()`
        #: hazard and abandoning it at exit is safe.
        self._bundle_thread: threading.Thread | None = None
        #: Set while a `wait`-family step is pending; the tick returns early
        #: until the deadline passes. This is what keeps waiting non-blocking.
        self._deadline: float | None = None
        self._deadline_step: Step | None = None
        self._deadline_started: float = 0.0
        self._deadline_predicate: Callable[[], bool] | None = None
        #: Set by a predicate that does real work (today: `pick-release`) so the
        #: transcript records *what it did* rather than a bare "ok". Cleared when
        #: the deadline is armed, so one verb's result can never be reported
        #: against the next.
        self._deadline_outcome: Outcome = Outcome.PASS
        self._deadline_detail: str = ""
        #: Replaces the generic "still not finished after Ns" when a verb can say
        #: something more useful about having run out of time.
        self._deadline_timeout_detail: str = ""
        #: `pick-release` phase 2: `(mbid, title, row, of_total)` once a release
        #: has been chosen and the verb is waiting for the track table to fill.
        #: `None` means no choice has been made on this arming yet. Cleared in
        #: `_arm_deadline` for the same reason the two fields above are — one
        #: verb's half-finished state must never grade the next one.
        self._picked_release: tuple[str, str, int, int] | None = None
        #: The last `cyanrip` invocation, so `expect-cyanrip` / `expect-exit`
        #: assert against what actually ran rather than re-running it.
        self._last_cyanrip_exit: int | None = None
        self._last_cyanrip_output: str = ""
        self._last_cyanrip_argv: list[str] = []
        #: The installed ripper's build tag, LATCHED — set the first time any
        #: `cyanrip` verb's output yields one, updated if a later one yields a
        #: different one, and **never cleared**. `(ripper)` reads this and not
        #: `_last_cyanrip_output`, which is deliberately invalidated by the very
        #: next `cyanrip` step (a refusal, a timeout, or just a different
        #: command) so that `expect-cyanrip`/`expect-exit` can never grade a
        #: subject two commands old. Those are opposite requirements on one
        #: field, and in 0.6.17 the assertion half won: the section-C cache-probe
        #: timeout wrote `job.error` into the slot, so both `album … (ripper)`
        #: steps in section A's own script failed with "no build tag has been
        #: captured yet" — while the banner they needed had been captured 20
        #: minutes earlier and thrown away. The rip then used the default album
        #: title, which is how a cancelled rip's two FLACs landed in the real
        #: album folder and produced an overwrite prompt nobody expected.
        #: Identity is a property of the *installed binary*, not of the last
        #: command; it gets its own field so no assertion's bookkeeping can
        #: reach it.
        self._ripper_build_tag: str = ""
        #: The `cyanrip` verb currently running on a helper thread, if any. While
        #: this is set the tick services it instead of advancing, which is what
        #: keeps a five-minute ripper call off the GUI thread.
        self._pending_cyanrip: _CyanripJob | None = None
        self._pending_rig_check: _RigCheckJob | None = None
        self._timer: QTimer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)

    # --- Public surface ------------------------------------------------------

    @property
    def running(self) -> bool:
        return self._timer.isActive()

    def start(
        self,
        steps: list[Step],
        *,
        unsafe_allowed: bool = False,
        source: str = "",
    ) -> None:
        """Begin a run.

        ``source`` is the script exactly as pasted. It is carried into the report
        so a failure is reproducible by whoever reads it — recording *which* step
        failed without recording *what was asked of it* is half a bug report.
        """
        if self.running:
            log.warning("script runner asked to start while already running; ignored")
            return
        self._steps = list(steps)
        self._index = 0
        self._unsafe_allowed = unsafe_allowed
        self._artifact_dir = None
        self._deadline = None
        self._pending_cyanrip = None
        self._report = RunReport(
            started_at=datetime.now(UTC).isoformat(timespec="seconds"),
            app_version=__version__,
            script_source=source,
            preflight=_preflight(self._steps),
        )
        log.info(
            "ui script run starting: %d step(s), unsafe verbs %s",
            len(self._steps),
            "ALLOWED" if unsafe_allowed else "refused",
        )
        for problem in self._report.preflight:
            # WARNING, not debug: this is a finding about the batch about to run,
            # and it must be in the log file a bug report carries.
            log.warning("ui script preflight: %s", problem)
        self._timer.start()

    def stop(self, reason: str = "stopped by the user") -> None:
        """End the run now, marking every unreached step as skipped.

        The remaining steps are recorded rather than dropped: "we never got
        there" and "it passed" must not look the same in the transcript.
        """
        if not self.running:
            return
        self._timer.stop()
        # A ripper call still in flight must be KILLED, not merely forgotten: a
        # `cancel()` that only drops a reference is the false promise CLAUDE.md
        # names. The helper thread is a daemon, so once its child dies the thread
        # ends; if the child is unreapable the thread is abandoned deliberately,
        # which is safe precisely because it is not a QThread.
        if self._pending_cyanrip is not None:
            from platterpus.adapters.rip_backend import cancel_info_probe

            log.info("ui script stopping with a cyanrip call in flight; killing it")
            cancel_info_probe()
            self._report.steps.append(
                StepRecord(
                    self._pending_cyanrip.step.line_no,
                    self._pending_cyanrip.step.source,
                    Outcome.ERROR,
                    "stopped while this command was still running; the child was "
                    "sent a kill. Its exit code is null, not 0.",
                    time.monotonic() - self._pending_cyanrip.started,
                )
            )
            self._pending_cyanrip = None
        # A seam check in flight is recorded as stopped rather than dropped. Its
        # probes are bounded and its thread is a daemon, so abandoning it is safe;
        # what is NOT safe is letting the transcript end with no row for a step
        # that started, because a run that stopped mid-check and a run that never
        # reached the check read identically.
        if self._pending_rig_check is not None:
            job = self._pending_rig_check
            log.info("ui script stopping with a rig check in flight; abandoning it")
            self._report.steps.append(
                StepRecord(
                    job.step.line_no,
                    job.step.source,
                    Outcome.ERROR,
                    "stopped while the seam check was still running; its exit code "
                    f"is null, not 0. Partial output is under {job.out_dir}.",
                    time.monotonic() - job.started,
                )
            )
            self._pending_rig_check = None
        for step in self._steps[self._index :]:
            self._report.steps.append(
                StepRecord(step.line_no, step.source, Outcome.SKIPPED)
            )
        self._report.ended_reason = reason
        log.info("ui script run ended: %s", reason)
        self._persist()
        self.finished.emit(self._report)

    # --- The tick ------------------------------------------------------------

    def _tick(self) -> None:
        """Execute at most one step, then return to the event loop.

        Never raises: an exception escaping a timer slot crosses into Qt's C++
        frame, where PySide6's behaviour is version-dependent and at worst
        aborts. Any failure becomes an ERROR record instead.
        """
        try:
            # An in-flight ripper call outranks everything: it holds this step
            # open, and advancing past it would record the NEXT step's outcome
            # against a command that had not finished.
            if self._pending_cyanrip is not None:
                self._service_cyanrip()
                return
            if self._pending_rig_check is not None:
                self._service_rig_check()
                return
            if self._deadline is not None:
                self._service_deadline()
                return
            if self._index >= len(self._steps):
                self._timer.stop()
                log.info("ui script run finished: %s", self._report.counts())
                self._persist()
                self.finished.emit(self._report)
                return
            step = self._steps[self._index]
            self._index += 1
            self._execute(step)
        except Exception as exc:  # noqa: BLE001 — a runner fault must not abort Qt
            log.exception("ui script runner fault")
            self._record(
                self._steps[max(self._index - 1, 0)],
                Outcome.ERROR,
                f"runner fault: {exc!r}",
            )

    def _service_deadline(self) -> None:
        """Handle a pending `wait` / `wait-for-rip` without blocking."""
        assert self._deadline is not None
        step = self._deadline_step
        assert step is not None
        now = time.monotonic()
        # A predicate that RAISES must end the step, not be retried every tick.
        # On the rig one `AttributeError` inside `pick-release` was re-recorded
        # **25 times** for a single line, because `_tick`'s catch-all logged it
        # and returned with the deadline still armed — so the next tick called
        # the same broken predicate again, and the only thing that stopped it
        # was a human clicking the dialog. A transcript with 25 identical ERROR
        # rows for one step also buries every other finding in the run.
        try:
            satisfied = (
                self._deadline_predicate is not None and self._deadline_predicate()
            )
        except Exception as exc:  # noqa: BLE001 — a faulty predicate ends its step
            log.exception("ui script deadline predicate faulted")
            elapsed = now - self._deadline_started
            self._deadline = None
            self._deadline_predicate = None
            self._deadline_step = None
            self._record(
                step,
                Outcome.ERROR,
                f"the wait's own check faulted and the step was ended rather "
                f"than retried: {exc!r}",
                elapsed=elapsed,
            )
            return
        if satisfied or now >= self._deadline:
            elapsed = now - self._deadline_started
            timed_out = not satisfied and self._deadline_predicate is not None
            self._deadline = None
            self._deadline_predicate = None
            self._deadline_step = None
            if timed_out:
                self._record(
                    step,
                    Outcome.FAIL,
                    self._deadline_timeout_detail
                    or f"still not finished after {elapsed:.0f}s",
                    elapsed=elapsed,
                )
            else:
                self._record(
                    step,
                    self._deadline_outcome,
                    self._deadline_detail,
                    elapsed=elapsed,
                )

    def _arm_deadline(
        self,
        step: Step,
        seconds: float,
        predicate: Callable[[], bool] | None = None,
    ) -> None:
        self._deadline_started = time.monotonic()
        self._deadline = self._deadline_started + seconds
        self._deadline_step = step
        self._deadline_predicate = predicate
        # Reset per arming, so a previous verb's result can never be reported
        # against this one — the same defect class as the stale `cyanrip`
        # invocation that graded a step two lines earlier (0.6.12b2).
        self._deadline_outcome = Outcome.PASS
        self._deadline_detail = ""
        self._deadline_timeout_detail = ""
        self._picked_release = None

    def _record(
        self,
        step: Step,
        outcome: Outcome,
        detail: str = "",
        *,
        elapsed: float = 0.0,
        artifact: str = "",
    ) -> None:
        record = StepRecord(
            step.line_no, step.source, outcome, detail, elapsed, artifact
        )
        self._report.steps.append(record)
        if outcome is not Outcome.PASS:
            # WARNING, not DEBUG: a failing assertion in an unattended run is
            # exactly what a later bug report needs to carry.
            log.warning("ui script L%d %s: %s", step.line_no, outcome.value, detail)
        self.step_recorded.emit(record)

    # --- Dispatch ------------------------------------------------------------

    def _execute(self, step: Step) -> None:
        if step.error:
            self._record(step, Outcome.ERROR, step.error)
            return
        # HANDLER FIRST, then the unsafe gate — the order carries the honesty.
        # Reversed, a script using `eval` (unsafe AND unimplemented) was told "this
        # verb needs the 'allow unsafe script verbs' setting, which is off", which
        # points the reader at a checkbox that would not have helped: with it
        # ticked the very next line refuses the same step for having no handler.
        # A true diagnosis of the wrong cause is the expensive kind — it sends
        # somebody into Settings instead of telling them the verb does not exist
        # (found 2026-08-24, in the sweep that followed `expect-status`).
        handler = getattr(self, f"_do_{step.verb.replace('-', '_')}", None)
        if handler is None:
            self._record(step, Outcome.ERROR, f"'{step.verb}' is not implemented yet")
            return
        if step.unsafe and not self._unsafe_allowed:
            self._record(
                step,
                Outcome.BLOCKED,
                "this verb needs the 'allow unsafe script verbs' setting, which is off",
            )
            return
        if step.unsafe:
            self._report.used_unsafe = True
        handler(step)

    # --- Verbs: narration and pacing ----------------------------------------

    def _do_log(self, step: Step) -> None:
        self._record(step, Outcome.PASS, step.joined())

    def _do_wait(self, step: Step) -> None:
        try:
            seconds = float(step.args[0])
        except ValueError:
            self._record(step, Outcome.ERROR, f"'{step.args[0]}' is not a number")
            return
        if seconds < 0:
            self._record(step, Outcome.ERROR, "a negative wait is not a wait")
            return
        # Same reasoning as `wait-for-rip` above, and fixed in the same change: the
        # comment "never a silent clamp" was right about the reporting and wrong
        # about the behaviour — it did not clamp at all, it *refused*, so the
        # script carried on immediately. A `wait` is almost always there to let
        # something settle before the next assertion, and skipping it entirely
        # turns the next step into a measurement of the wrong moment.
        capped = min(seconds, MAX_WAIT_S)
        self._arm_deadline(step, capped)
        if capped < seconds:
            note = (
                f"[CLAMPED: asked for {seconds:.0f}s, the cap is "
                f"{MAX_WAIT_S:.0f}s — waited the cap, not zero]"
            )
            log.warning("ui script L%s: wait %s", step.line_no, note)
            self._deadline_detail = note

    def _do_abort(self, step: Step) -> None:
        self._record(step, Outcome.PASS, step.joined() or "abort")
        reason = step.joined() or f"aborted at line {step.line_no}"
        # Everything after this is recorded as skipped by stop().
        self.stop(reason)

    def _do_abort_if_failed(self, step: Step) -> None:
        """Stop the batch, but ONLY if something has already failed.

        **A precondition and a finding are different things, and this file's rule
        that "a failing step does not stop the batch" is about findings.** That
        rule is right: a run that halts on the first problem hides every problem
        behind it, and a disc pass costs hours nobody gets back. It is the wrong
        rule for *"am I even testing the right binary?"* — a wrong ripper does not
        make the next six hours partially useful, it makes them **evidence about
        a different subject**, which is precisely what the handshake exists to
        prevent (`CLAUDE.md` rule 12: two artifacts from the same ripper under
        different app versions are not interchangeable evidence).

        Written because `fullacceptance.txt` **claimed** the identity section
        *"stops you in the first four seconds if you are not"* on the right build,
        and it did not — nothing but `abort` stops a batch, and the file never used
        it. A header promising a stop that cannot happen is worse than no promise:
        the cyanrip fork read that sentence and told the operator to run the file
        overnight partly on the strength of it (round 14 lap 11 §J7, which asked us
        to correct them if §A did not do what its header said — it did not).

        Counts **FAIL and ERROR, not BLOCKED** — a verb refused for want of a
        setting has not established that anything is wrong with the rig.
        """
        failed = [
            r for r in self._report.steps if r.outcome in (Outcome.FAIL, Outcome.ERROR)
        ]
        if not failed:
            self._record(
                step,
                Outcome.PASS,
                f"no failures in the {len(self._report.steps)} step(s) so far — "
                "continuing",
            )
            return
        first = failed[0]
        detail = (
            f"{len(failed)} step(s) have failed; the first was L{first.line_no} "
            f"({first.source!r}: {first.detail}). "
            + (step.joined() or "stopping rather than spending the run on it")
        )
        self._record(step, Outcome.PASS, detail)
        self.stop(detail)

    # --- Verbs: evidence -----------------------------------------------------

    def _do_screenshot(self, step: Step) -> None:
        """Render every top-level window, and record a manifest beside the PNGs.

        **The PNG is not the evidence. The manifest is.** Measured against
        PySide6 6.11.1: ``QWidget.grab()`` on a dialog that was *never shown*
        still returns a valid, non-null 59×36 pixmap, with ``isVisible()`` False
        and ``windowHandle()`` None. So a script that captured a picture and
        concluded "the dialog was on screen" would answer the maintainer's
        question **wrongly** — which is the exact class of bug this project keeps
        paying for, arriving through a new door.

        What actually distinguishes "on screen" from "constructed and never
        shown" is ``windowHandle()`` being non-None and ``isExposed()`` being
        true, plus the frame geometry lying inside a real screen. All of it is
        recorded per window, so a picker-absent verdict rests on facts rather
        than on a picture.

        Also worth stating plainly: this is *not* a desktop capture.
        ``QScreen.grabWindow()`` is unsupported on Wayland, which is the default
        on the Bazzite/Plasma 6 target, so per-widget rendering is the only thing
        that works there. The upside is that the same script runs headless in CI.
        """
        directory = self._ensure_artifact_dir()
        if directory is None:
            self._record(step, Outcome.ERROR, "could not create the screenshot folder")
            return
        name = _safe_name(step.args[0])
        written: list[str] = []
        manifest: list[str] = []
        for index, widget in enumerate(_all_top_levels()):
            path = directory / (
                f"{name}.png" if index == 0 else f"{name}-{index}-{_slug(widget)}.png"
            )
            manifest.append(_window_manifest_line(widget))
            try:
                if widget.grab().save(str(path), "PNG"):
                    written.append(path.name)
            except Exception as exc:  # noqa: BLE001 — evidence is best-effort
                log.warning("screenshot of %r failed: %r", widget, exc)
                manifest.append(f"    (grab failed: {exc!r})")
        # "examined 0 windows" is a distinct, recordable outcome — not a pass.
        if not manifest:
            self._record(step, Outcome.FAIL, "no top-level window existed to examine")
            return
        detail = "\n".join(
            [f"examined {len(manifest)} window(s); wrote {len(written)} PNG(s)"]
            + manifest
        )
        self._record(
            step,
            Outcome.PASS,
            detail,
            artifact=str(directory / f"{name}.png") if written else "",
        )

    def _do_snapshot(self, step: Step) -> None:
        """Record the visible state as text — cheap, greppable, always embedded."""
        lines = [f"snapshot '{step.args[0]}':"]
        top = _active_dialog()
        lines.append(f"  dialog on top: {top.windowTitle() if top else '(none)'}")
        lines.append(f"  window title : {self._window.windowTitle()}")
        for label, value in _panel_fields(self._window).items():
            lines.append(f"  {label}: {value}")
        self._record(step, Outcome.PASS, "\n".join(lines))

    # --- Verbs: dialogs ------------------------------------------------------

    def _do_open(self, step: Step) -> None:
        target = step.args[0].lower()
        method_name = OPENABLE.get(target)
        if method_name is None:
            self._record(
                step,
                Outcome.ERROR,
                f"'{target}' is not openable; try one of {', '.join(sorted(OPENABLE))}",
            )
            return
        method = getattr(self._window, method_name, None)
        if method is None:
            self._record(
                step, Outcome.ERROR, f"the window has no {method_name}() — a code bug"
            )
            return
        # Modal dialogs exec() and do not return until dismissed. The record is
        # written FIRST so the transcript shows the open even if the batch is
        # stopped while the dialog is up.
        self._record(step, Outcome.PASS, f"opening {target}")
        QTimer.singleShot(0, method)

    def _do_ok(self, step: Step) -> None:
        self._dismiss(step, accept=True)

    def _do_cancel(self, step: Step) -> None:
        self._dismiss(step, accept=False)

    def _dismiss(self, step: Step, *, accept: bool) -> None:
        dialog = _active_dialog()
        if dialog is None:
            self._record(step, Outcome.FAIL, "no dialog is open")
            return
        title = dialog.windowTitle()
        if accept:
            dialog.accept()
        else:
            dialog.reject()
        self._record(
            step, Outcome.PASS, f"{'accepted' if accept else 'cancelled'} {title!r}"
        )

    def _do_answer_dialog(self, step: Step) -> None:
        """Wait for a NAMED dialog, then answer it. The waiting is the point.

        `ok` and `cancel` answer whatever is on top at the instant they run, and
        fail when nothing is. That works for a dialog the script itself opened
        with `open`, which is synchronous. It does **not** work for a dialog
        raised as a consequence of an action, because the action only *requests*
        the work: `rip` returns as soon as the start is posted, and the
        "Album already ripped" confirmation appears a beat later. `rip` then `ok`
        is therefore a race, and it is the same defect as v0.6.17's
        `pick-release` — asserting a thing was REQUESTED when the claim needed is
        that it HAPPENED.

        Measured, 2026-08-20: section E of the cancel-path script did exactly
        this. `rip` recorded "start requested", `wait-for-rip` found no worker
        because the app was blocked on the confirmation, and **both** of that
        run's two failures followed from it — the second being `rig-check`
        grading the *cancelled* rip, since no second rip was ever produced. The
        failure message even advised adding `ok`, which would have raced.

        **Why the title is mandatory.** A bare accept in an unattended run will
        answer a dialog nobody predicted — a crash report, an overwrite prompt, a
        "disc has changed" — and there is no operator to notice it happened. So
        this verb refuses to answer anything but the dialog it was told to
        expect: a mismatching dialog is never touched, the wait continues, and
        the timeout names what was sitting there instead. That makes the step an
        assertion as well as an action, which is what stops "the script clicked
        OK on something" from being a silent outcome.

        **Three answers, not two.** ``ok``/``cancel`` call ``accept()``/
        ``reject()``, which is the whole vocabulary a two-button dialog needs. A
        dialog with three *named* choices cannot be answered that way at all —
        see the ``click=`` comment below for the measured reason — so
        ``click=<substring>`` names the button instead.
        """
        action = step.args[0].lower()
        # `click=<substring>` NAMES A BUTTON, and it exists because `ok` cannot
        # answer a multi-button dialog at all.
        #
        # `ok` calls `dialog.accept()`. On a QMessageBox built with `addButton`,
        # accept() closes the dialog but leaves `clickedButton()` as **None** — so
        # a caller written as
        #
        #     if clicked is replace_btn: ...
        #     if clicked is new_folder_btn: ...
        #     return None  # Cancel
        #
        # falls through to the CANCEL branch. `_confirm_known_overwrite` is exactly
        # that shape, so `answer-dialog ok` on "Album already ripped" would silently
        # CANCEL the rip while the transcript recorded "accepted". Found 2026-08-21
        # while writing a script that relied on it — before it shipped, and only
        # because the fall-through was read rather than assumed.
        #
        # A substring rather than a full label because the script language splits
        # args on whitespace with no quoting (`script.parse`: `args = tokens[1:]`),
        # so "Rip to a new folder" cannot be one argument. `click=new` can.
        refusal = answer_dialog_action_error(step.args[0])
        if refusal is not None:
            self._record(step, Outcome.ERROR, refusal)
            return
        click_label = ""
        if action.startswith(ANSWER_DIALOG_CLICK_PREFIX):
            click_label = step.args[0][len(ANSWER_DIALOG_CLICK_PREFIX) :].strip()
        try:
            seconds = float(step.args[1])
        except ValueError:
            self._record(
                step,
                Outcome.ERROR,
                f"{step.args[1]!r} is not a number of seconds",
            )
            return
        if seconds <= 0:
            self._record(
                step,
                Outcome.ERROR,
                f"the timeout must be positive; got {seconds:g}. A zero wait is "
                "what `ok`/`cancel` already do, and it is the race this verb "
                "exists to remove.",
            )
            return
        wanted = " ".join(step.args[2:]).strip()
        if not wanted:
            self._record(
                step,
                Outcome.ERROR,
                "a title substring is required (see the verb's help)",
            )
            return
        capped = min(seconds, MAX_WAIT_S)
        accept = action == "ok"
        # Names the dialog that WAS there when time ran out. Without it a timeout
        # reads as "no dialog appeared", which is a different finding from "a
        # dialog appeared and it was not the one you named" — and only the second
        # tells you the app did something unexpected.
        seen: list[str] = []

        def answer_when_it_appears() -> bool:
            dialog = _active_dialog()
            if dialog is None:
                return False
            title = dialog.windowTitle()
            if wanted.casefold() not in title.casefold():
                # Deliberately NOT answered and deliberately not a failure yet:
                # the dialog we want may still be behind this one.
                if title not in seen:
                    seen.append(title)
                self._deadline_timeout_detail = (
                    f"waited {capped:.0f}s for a dialog matching {wanted!r} and "
                    f"never saw one; a dialog WAS open and was left untouched: "
                    f"{', '.join(repr(t) for t in seen)}. This verb refuses to "
                    f"answer a dialog it was not told to expect."
                )
                return False
            if click_label:
                # The dialog we were told to expect IS on screen, so this is the
                # last chance to answer it — a refusal here ends the wait with a
                # FAIL rather than looping, because looping would just re-find
                # the same dialog and the same wrong button until the deadline,
                # then report the far less useful "never saw one".
                clicked, why = _click_named_button(dialog, click_label)
                if clicked is None:
                    self._deadline_outcome = Outcome.FAIL
                    self._deadline_detail = f"{title!r} was up but {why}"
                    return True
                self._deadline_outcome = Outcome.PASS
                self._deadline_detail = (
                    f"clicked {clicked!r} on {title!r} (matched {wanted!r})"
                )
                return True
            if accept:
                dialog.accept()
            else:
                dialog.reject()
            self._deadline_outcome = Outcome.PASS
            self._deadline_detail = (
                f"{'accepted' if accept else 'dismissed'} {title!r} "
                f"(matched {wanted!r})"
            )
            return True

        self._arm_deadline(step, capped, answer_when_it_appears)
        # `_arm_deadline` resets the timeout detail, so the no-dialog-at-all
        # message is set after it and is overwritten only if one does show up.
        self._deadline_timeout_detail = (
            f"waited {capped:.0f}s for a dialog matching {wanted!r} and no dialog "
            f"opened at all — so the action that was supposed to raise it either "
            f"did not run or did not need confirming"
        )

    def _do_expect_dialog(self, step: Step) -> None:
        wanted = step.args[0]
        dialog = _active_dialog()
        actual = dialog.windowTitle() if dialog else ""
        if wanted.lower() == "none":
            if dialog is None:
                self._record(step, Outcome.PASS, "no dialog, as expected")
            else:
                self._record(step, Outcome.FAIL, f"a dialog is open: {actual!r}")
            return
        if dialog is None:
            self._record(step, Outcome.FAIL, f"no dialog open; expected {wanted!r}")
        elif wanted.lower() in actual.lower():
            self._record(step, Outcome.PASS, f"dialog is {actual!r}")
        else:
            self._record(
                step, Outcome.FAIL, f"expected {wanted!r} but the dialog is {actual!r}"
            )

    # --- Verbs: cyanrip, for real --------------------------------------------

    def _do_cyanrip(self, step: Step) -> None:
        """Start the host-exported ripper on a helper thread; the tick collects it.

        Deliberately :func:`~platterpus.adapters.rip_backend.run_capture` and not
        a fresh ``subprocess`` call: that is the seam the application's own
        probes use, so a script exercises the **real** path rather than a
        parallel one that could drift from it. It brings a killable child, a
        bounded timeout and diagnostics-on-failure with it.

        Records the exit code, the exact argv and the complete output, because
        that trio is what makes a ripper failure reproducible by hand
        (``CLAUDE.md`` — diagnostic completeness), and because the maintainer
        asked that inputs be recorded beside errors.

        **It does not block.** ``run_capture`` can take five minutes; running it
        on the GUI thread froze the window for exactly that long. The call is
        unchanged — the *same* function, the *same* arguments — it simply happens
        on a daemon thread while the tick keeps returning to the event loop. See
        :class:`_CyanripJob`.
        """
        from platterpus.adapters.rip_backend import RipError, run_capture
        from platterpus.paths import CYANRIP_BINARY_DEFAULT

        args = list(step.args)
        # NOT WHILE A RIP IS READING THE DISC.
        #
        # **Measured, 2026-08-24:** `cyanrip -N -x -I` opened /dev/sr0 **1.2
        # seconds** after a whole-disc rip started on the same device — two ripper
        # processes on one drive. The script's ordering was correct and assumed
        # `wait-for-rip` blocks; it did not (an over-cap request refused to wait,
        # fixed separately), and nothing else stood between a live rip and a step
        # that opens the drive. A cache probe is the worst possible thing to do to
        # a drive mid-read: it exists to defeat the readback cache.
        #
        # Two independent defects had to line up for that, which is exactly why
        # the guard belongs HERE rather than only in the wait: this verb knows it
        # touches the drive, and no ordering assumption elsewhere can be trusted
        # to hold on a run that has already gone sideways.
        #
        # Probe invocations are exempt — `--version` and `--help` print and exit
        # without opening the device, and the acceptance script's section A runs
        # one deliberately while nothing else is happening.
        from platterpus.uiscript.verbs import PROBE_FLAGS

        is_probe = bool(args) and all(arg in PROBE_FLAGS for arg in args)
        if not is_probe and getattr(self._window, "_rip_worker", None) is not None:
            self._last_cyanrip_argv = []
            self._last_cyanrip_output = ""
            self._last_cyanrip_exit = None
            self._record(
                step,
                Outcome.FAIL,
                "refusing to run the ripper while a rip is READING THE DISC — "
                "two ripper processes on one drive. Put a `wait-for-rip` before "
                "this step, or move it after the rip finishes. (Only "
                f"{sorted(PROBE_FLAGS)} are exempt: they print and exit without "
                "opening the device.)",
            )
            return
        # SANITISE NEXT. This verb is a straight passthrough that bypasses
        # `assert_metadata_lookup_disabled`, the one chokepoint every rip argv
        # the application builds must pass. Re-establishing the guard here is
        # not belt-and-braces: without `-N` cyanrip runs its own MusicBrainz
        # lookup, which can block on an interactive prompt with no terminal
        # attached — an unattended batch would hang forever, which is precisely
        # the failure this whole feature exists to prevent.
        refusal = sanitise_cyanrip_args(args)
        if refusal is not None:
            # INVALIDATE THE LAST RESULT. A refused step ran nothing, so every
            # `expect-cyanrip` / `expect-exit` after it must have no subject —
            # not the subject two commands ago.
            #
            # On the rig this happened four times in one run: L316's *"expected
            # exit 1, got 0"* was grading C5's `-f` offset probe, not the C6
            # `--verify-log` line it followed. It failed, which was luck. **Had
            # `-f` exited 1, that assertion would have PASSED for a command that
            # never ran** — an assertion satisfied by the wrong thing, inside the
            # surface this project writes its tests in. Found by the cyanrip fork
            # reading their own transcript (round 8 lap 7 §0b, item 2).
            self._last_cyanrip_argv = []
            self._last_cyanrip_output = ""
            self._last_cyanrip_exit = None
            self._record(step, Outcome.FAIL, refusal)
            return
        argv = [str(CYANRIP_BINARY_DEFAULT), *args]
        self._last_cyanrip_argv = argv
        job = _CyanripJob(
            step=step,
            argv=argv,
            started=time.monotonic(),
            done=threading.Event(),
        )

        def _work() -> None:
            # Everything this closure touches is either local or a field of
            # `job`; it never touches Qt, a widget, or the report. That is the
            # rule the GUI-thread boundary is made of.
            try:
                job.result = run_capture(
                    "cyanrip",
                    str(CYANRIP_BINARY_DEFAULT),
                    args,
                    timeout=CYANRIP_VERB_TIMEOUT_S,
                    stdin_devnull=True,  # cyanrip reads stdin; it must be closed
                )
            except RipError as exc:
                job.error = str(exc)
            except Exception as exc:  # noqa: BLE001 — a helper thread must not die silently
                job.error = f"unexpected {type(exc).__name__}: {exc}"
            finally:
                # LAST, always: the tick reads the fields above only after this.
                job.done.set()

        self._pending_cyanrip = job
        thread = threading.Thread(target=_work, name="uiscript-cyanrip", daemon=True)
        thread.start()

    def _service_cyanrip(self) -> None:
        """Poll the pending `cyanrip` job; record it once, when it finishes.

        Called from the tick instead of executing a step, so the batch pauses
        here without the event loop pausing with it.
        """
        job = self._pending_cyanrip
        assert job is not None
        elapsed = time.monotonic() - job.started
        if not job.done.is_set():
            if elapsed <= CYANRIP_VERB_TIMEOUT_S + CYANRIP_VERB_GRACE_S:
                return
            # `run_capture` enforces its own timeout and kills the child, so
            # reaching here means the child could not be reaped — the drive-ioctl
            # case where SIGKILL does not land. Ask for the kill anyway, report an
            # unreapable child (tri-state: the exit code is null, never 0), and
            # abandon the thread rather than waiting on it forever.
            from platterpus.adapters.rip_backend import cancel_info_probe

            cancel_info_probe()
            self._pending_cyanrip = None
            self._last_cyanrip_exit = None
            self._last_cyanrip_output = ""
            self._record(
                job.step,
                Outcome.ERROR,
                f"argv: {' '.join(job.argv)}\nexit: null (never reaped)\n"
                f"the ripper did not return after {elapsed:.0f}s and did not "
                "respond to a kill — the child is unreapable (a reader wedged in "
                "a drive ioctl is in uninterruptible sleep). The batch continues.",
                elapsed=elapsed,
            )
            return
        self._pending_cyanrip = None
        if job.result is None:
            # Tri-state, always: nothing was reaped, so the exit code is None and
            # must never be written as 0.
            self._last_cyanrip_exit = None
            self._last_cyanrip_output = job.error
            self._latch_ripper_identity(job.error)
            self._record(
                job.step,
                Outcome.ERROR,
                f"argv: {' '.join(job.argv)}\nexit: null (never reaped)\n{job.error}",
                elapsed=elapsed,
            )
            return
        code, output = job.result
        self._last_cyanrip_exit = code
        self._last_cyanrip_output = output
        self._latch_ripper_identity(output)
        self._record(
            job.step,
            Outcome.PASS,
            f"argv: {' '.join(job.argv)}\nexit: {code}\n{_bounded_output(output)}",
            elapsed=elapsed,
        )

    def _latch_ripper_identity(self, text: str) -> None:
        """Remember the ripper's build tag if ``text`` carries one; never forget.

        Called from **every** place a `cyanrip` verb's output lands, so there is
        one absorber rather than one reader per consumer. It only ever *sets* the
        latch: output with no recognisable banner (a probe's error text, a rip's
        progress spew) leaves the previously captured tag alone.

        Latest-wins rather than first-wins, deliberately: the field answers
        "which binary is installed", and if a later banner disagrees with an
        earlier one then the later one is the current truth. Within a single
        script run the two are the same value, so the choice only matters if a
        script ever reinstalls the ripper mid-run — in which case naming the new
        build is the correct answer.
        """
        if not text:
            return
        from platterpus.ripper_identity import identify_from_banner

        tag = identify_from_banner(text).build_tag
        if tag:
            self._ripper_build_tag = tag

    def _do_rig_check(self, step: Step) -> None:
        """Run the cyanrip seam check on a helper thread; the tick collects it.

        **Why this verb exists at all.** The check is also a terminal flag
        (``--rig-check``), which the fork's own script calls so both projects'
        evidence lands in one ``MANIFEST.txt``. That is a machine-to-machine
        interface. This verb is the *person's* one: the script language is where
        this project's tests are written, and a capability the language cannot
        reach is a capability that lives somewhere the tests do not. Both call
        :func:`platterpus.rig_check.run_rig_check` — neither reimplements it, so
        the two surfaces cannot disagree about what the check found.

        The album folder is optional and is **not** guessed from the window: the
        log-reading checks report ``SKIP`` without it, and SKIP means *did not
        run*, which is the honest answer. Auditing the wrong album still produces
        a clean-looking report, so a folder the script names is worth more than a
        folder something inferred.
        """
        from platterpus.rig_check import run_rig_check

        directory = self._ensure_artifact_dir()
        if directory is None:
            self._record(step, Outcome.ERROR, "cannot create the artifact directory")
            return
        album: Path | None = None
        if step.args:
            album = Path(step.joined()).expanduser()
            if not album.is_dir():
                self._record(
                    step,
                    Outcome.FAIL,
                    f"album folder does not exist: {album}. Refusing rather than "
                    "running the log checks as SKIP — a folder named and missing "
                    "is a mistake, not an omission.",
                )
                return
        job = _RigCheckJob(
            step=step,
            out_dir=directory / "rig-check",
            album_dir=album,
            started=time.monotonic(),
            done=threading.Event(),
        )

        def _work() -> None:
            # Same boundary rule as `_do_cyanrip`: this closure touches nothing
            # Qt, no widget and no report — only locals and fields of `job`.
            try:
                job.code = run_rig_check(
                    job.out_dir,
                    album_dir=job.album_dir,
                    sink=job.lines.append,
                )
            except Exception as exc:  # noqa: BLE001 — a helper thread must not die silently
                job.error = f"unexpected {type(exc).__name__}: {exc}"
            finally:
                # LAST, always — the tick reads the fields above only after this.
                job.done.set()

        self._pending_rig_check = job
        thread = threading.Thread(target=_work, name="uiscript-rig-check", daemon=True)
        thread.start()

    def _service_rig_check(self) -> None:
        """Poll the pending `rig-check` job; record it once, when it finishes.

        The check runs the ripper twice, and each probe is bounded inside
        :mod:`platterpus.rig_check`; the outer bound here is the same shape as
        the cyanrip verb's, so a wedged drive ioctl cannot hold the batch open
        forever. An abandoned daemon thread is safe — it is not a ``QThread``.
        """
        job = self._pending_rig_check
        assert job is not None
        elapsed = time.monotonic() - job.started
        if not job.done.is_set():
            if elapsed <= RIG_CHECK_VERB_TIMEOUT_S:
                return
            self._pending_rig_check = None
            self._record(
                job.step,
                Outcome.ERROR,
                f"the seam check did not return after {elapsed:.0f}s — a probe is "
                "wedged (a reader in a drive ioctl is in uninterruptible sleep). "
                f"Whatever it wrote is under {job.out_dir}. The batch continues.\n"
                + "\n".join(job.lines),
                elapsed=elapsed,
            )
            return
        self._pending_rig_check = None
        if job.code is None:
            # Tri-state: no exit code was produced, so it is null and never 0.
            self._record(
                job.step,
                Outcome.ERROR,
                f"exit: null (the check did not finish)\n{job.error}\n"
                + "\n".join(job.lines),
                elapsed=elapsed,
            )
            return
        body = f"exit: {job.code}\nmanifest under {job.out_dir}\n" + "\n".join(
            job.lines
        )
        # FAIL, not ERROR: a non-zero code means a check ran and found something
        # wrong, which is a result. ERROR is reserved for the check not running.
        outcome = Outcome.PASS if job.code == 0 else Outcome.FAIL
        self._record(job.step, outcome, body, elapsed=elapsed)

    def _do_expect_cyanrip(self, step: Step) -> None:
        # THE RAW TAIL, not the re-joined tokens. This verb matches against a
        # tool's own output, so every character the operator typed is meaningful
        # — including quotes, which tokenising eats because they are grouping
        # characters everywhere else in the language.
        #
        # cyanrip prints `Missing "=" in track metadata "1"`. Asserting that was
        # impossible until now: the quotes vanished before the comparison, so the
        # fork's C3 could only assert a weakened, quote-free substring and said so
        # (round 8 lap 7 §0b — *"a gap in the language, not in the test"*).
        # `joined()` stays for the verbs whose tokens really are just words.
        wanted = step.raw_tail or step.joined()
        if not self._last_cyanrip_argv:
            self._record(step, Outcome.ERROR, "no cyanrip command has run yet")
            return
        if wanted in self._last_cyanrip_output:
            self._record(step, Outcome.PASS, f"found {wanted!r}")
        else:
            self._record(
                step,
                Outcome.FAIL,
                f"{wanted!r} is not in the output of "
                f"{' '.join(self._last_cyanrip_argv)}\n"
                f"{_bounded_output(self._last_cyanrip_output)}",
            )

    def _do_expect_exit(self, step: Step) -> None:
        if not self._last_cyanrip_argv:
            self._record(step, Outcome.ERROR, "no cyanrip command has run yet")
            return
        raw = step.args[0]
        if raw.lower() in {"null", "none"}:
            wanted: int | None = None
        else:
            try:
                wanted = int(raw)
            except ValueError:
                self._record(step, Outcome.ERROR, f"{raw!r} is not an exit code")
                return
        if self._last_cyanrip_exit == wanted:
            self._record(step, Outcome.PASS, f"exit was {wanted}")
        else:
            self._record(
                step,
                Outcome.FAIL,
                f"expected exit {wanted}, got {self._last_cyanrip_exit} from "
                f"{' '.join(self._last_cyanrip_argv)}",
            )

    # --- Verbs: the disc and the rip -----------------------------------------
    #
    # **These drive the REAL widgets, not a parallel path.** Every verb below
    # reaches the same method a human's click reaches — `_on_drive_changed` for
    # Rescan, `RipControls._on_start` for Start, `_on_rip_cancel` for Cancel — so a
    # scripted run exercises the product rather than a simulation of it. That is the
    # same reasoning the `cyanrip` verb is a real passthrough for: a test harness
    # that is safer or simpler than the product makes the product's gap invisible
    # (`CLAUDE.md`, *what does my stand-in do that the real thing does not?*).
    #
    # They are also the verbs that make an unattended hardware session possible at
    # all. Until now the vocabulary could open dialogs and probe the ripper but could
    # not start a rip, so the one thing a rig session exists to do needed a person.

    def _do_rescan(self, step: Step) -> None:
        """Re-run the whole disc pipeline (disc info → MusicBrainz) for the drive.

        Goes through the window's own `_on_drive_changed`, which is exactly what the
        Rescan button's `drive_changed` signal triggers — rather than poking the
        probe directly, which would skip the wiring the button depends on.
        """
        picker = getattr(self._window, "_drive_picker", None)
        device = picker.current_device() if picker is not None else None
        if not device:
            self._record(
                step,
                Outcome.FAIL,
                "no drive is selected, so there is nothing to rescan",
            )
            return
        handler = getattr(self._window, "_on_drive_changed", None)
        if handler is None:
            self._record(step, Outcome.ERROR, "the window has no _on_drive_changed()")
            return
        self._record(step, Outcome.PASS, f"rescanning {device}")
        # Deferred like `open`: the scan spawns workers, and returning to the event
        # loop first keeps the runner's own tick responsive.
        QTimer.singleShot(0, lambda: handler(device))

    def _do_album(self, step: Step) -> None:
        """Set the album title.

        The point for a repeat rip: the title decides the output folder, so giving
        each pass its own title is what stops the second rip landing on top of the
        first. A hardware session that overwrites its own evidence has destroyed the
        thing it was run to produce.
        """
        self._set_album_field(step, "_album_title_edit", "album title")

    def _do_album_artist(self, step: Step) -> None:
        """Set the album artist (and propagate it to the per-track artist column)."""
        self._set_album_field(step, "_album_artist_edit", "album artist")

    def _expand_ripper_placeholder(self, value: str) -> tuple[str, str]:
        """Expand ``(ripper)`` to the installed ripper's build tag.

        Returns ``(expanded, error)``; a non-empty error means the caller must
        FAIL the step rather than proceed.

        **Why this exists (0.6.17).** A two-pass hardware session rips the same
        disc on two ripper builds, and the album title is what decides the output
        folder — so with a fixed title the second pass lands on top of the first
        and destroys the evidence the session was run to produce. The workaround
        was telling the operator to `mv` two folders between passes, which is
        exactly the hand-work `CLAUDE.md` says never to hand back: *"every
        hand-edit and every 'now run this, then run that' in a written procedure
        is a thing the software was supposed to do."*

        The tag comes from the `cyanrip --version` banner the script has already
        captured, so it needs no new probe — but that means ORDER MATTERS, and
        an unresolved placeholder is not something to paper over: it would put
        the literal string `(ripper)` in both passes' titles and silently restore
        the collision. So it is a hard failure that names the cause.

        **It reads the LATCH, not the last output (fixed 0.6.18).** The first
        version read `_last_cyanrip_output`, which every subsequent `cyanrip`
        step overwrites on purpose — see `_ripper_build_tag` for the measured
        failure that cost a hardware session. The placeholder now only needs a
        `cyanrip` step to have run *at some point*, not to be the most recent
        one, which is the property a two-pass script actually depends on.

        Spelled `(ripper)` to match the `(track) - (title)` placeholder syntax
        this project already hands cyanrip in `-F`, rather than inventing a
        second convention for the same idea.
        """
        # `(run)` FIRST, and it never fails: it is a fact about this run, always
        # available, where `(ripper)` is a fact about a binary that may not have
        # been probed yet.
        #
        # **Why it exists.** Every album name in an acceptance script is a fixed
        # string plus `(ripper)`, so a second run against the same build produces
        # the same folders — and the app, correctly, raises "Album already ripped"
        # over each one. On the 2026-08-25 run that cost sixteen of seventeen
        # failures and the whole of T1: the script answers that prompt at exactly
        # one of its eight rips, so the other seven were refused behind an
        # unanswered modal. An acceptance script that only works on a machine that
        # has never run it is not an acceptance script.
        #
        # `answer-dialog` after every rip is the obvious repair and is WRONG: it
        # FAILS when the dialog does not appear, so it would break the first run on
        # a clean library — trading one broken case for the other. Making the names
        # unique removes the collision instead of answering it, and the deliberate
        # intra-run collision (§H rips the same album name twice on purpose, to
        # exercise the prompt) still works, because both steps expand to the same
        # value within one run.
        if "(run)" in value:
            # A COMPACT, FILESYSTEM-SAFE STAMP, not the raw ISO string.
            # `started_at` is `...isoformat(timespec="seconds")`, so it carries
            # `:` and `+` — and the album sanitiser would render those as `∶`
            # (U+2236) and friends, giving a folder named `22∶57∶21+00∶00`. That
            # is legal and horrible, and it drags a Unicode substitution into the
            # one string whose whole job is to be boringly unique. Digits and one
            # `t`, matching `CLAUDE.md`'s cross-machine artifact spelling.
            stamp = "".join(
                ch for ch in self._report.started_at.split("+")[0] if ch.isalnum()
            ).lower()
            value = value.replace("(run)", stamp)
        if "(ripper)" not in value:
            return value, ""
        tag = self._ripper_build_tag
        if not tag:
            return value, (
                "(ripper) could not be expanded: no cyanrip build tag has been "
                "captured yet — no `cyanrip` step in this script has produced a "
                "recognisable version banner. Put a `cyanrip --version` step "
                "before this one; the tag it captures is latched for the whole "
                "run, so any later step may follow it. Refusing rather than "
                "writing the literal text, which would give two passes the same "
                "album folder and overwrite the first pass's evidence."
            )
        return value.replace("(ripper)", tag), ""

    def _set_album_field(self, step: Step, widget_name: str, label: str) -> None:
        table = getattr(self._window, "_track_table", None)
        edit = getattr(table, widget_name, None) if table is not None else None
        if edit is None:
            self._record(step, Outcome.ERROR, f"no {label} field on the window")
            return
        value, placeholder_error = self._expand_ripper_placeholder(step.joined())
        if placeholder_error:
            self._record(step, Outcome.FAIL, placeholder_error)
            return
        edit.setText(value)
        # `editingFinished` is what propagates the artist down the track rows; a
        # bare setText does not emit it, so a scripted edit would behave differently
        # from a typed one. Emit it explicitly rather than leaving that difference.
        try:
            edit.editingFinished.emit()
        except (AttributeError, RuntimeError):  # not a QLineEdit, or already gone
            log.debug("could not emit editingFinished for %s", label, exc_info=True)
        self._record(step, Outcome.PASS, f"{label} set to {value!r}")

    def _do_expect_tracks(self, step: Step) -> None:
        """Assert how many track rows are loaded.

        The **floor** for everything after it: a script that rips without checking
        this can rip a disc it never identified, and a zero-track "success" reads
        the same as a real one in a transcript.

        Two forms — ``expect-tracks 14`` (exactly) and ``expect-tracks 3+`` (at
        least). **The at-least form exists because the exact form made a script
        lie** (0.6.18). ``rigcancelandoverread.txt`` opens by promising it needs no
        editing and works on any ordinary CD, and it then asserted
        ``expect-tracks 3`` — meaning "this disc has exactly three tracks" — while
        *intending* "at least the three I am about to select". On the rig disc (14
        tracks) it failed every run, twice per run, in a transcript whose purpose
        was proving the rip worked. Hardcoding ``14`` would have fixed the failure
        and broken the promise; there was no exact number that could satisfy both.

        A trailing ``+`` rather than a second argument or a new verb: the arity
        stays 1, every existing script keeps its meaning, and the reader needs no
        vocabulary they do not already have. `CLAUDE.md`: a capability the script
        language cannot reach is one the tests cannot reach — so the fix goes in
        the language, not into an operator's instructions.
        """
        raw = step.args[0]
        at_least = raw.endswith("+")
        try:
            wanted = int(raw[:-1] if at_least else raw)
        except ValueError:
            self._record(
                step,
                Outcome.ERROR,
                f"{raw!r} is not a count — use a number, or a number with a "
                "trailing '+' for 'at least this many'",
            )
            return
        table = getattr(self._window, "_track_table", None)
        if table is None:
            self._record(step, Outcome.ERROR, "no track table on the window")
            return
        actual = len(table.tracks())
        if at_least:
            if actual >= wanted:
                self._record(
                    step, Outcome.PASS, f"{actual} track rows (at least {wanted})"
                )
            else:
                self._record(
                    step,
                    Outcome.FAIL,
                    f"expected at least {wanted} track rows, found {actual}",
                )
            return
        if actual == wanted:
            self._record(step, Outcome.PASS, f"{actual} track rows, as expected")
        else:
            self._record(
                step, Outcome.FAIL, f"expected {wanted} track rows, found {actual}"
            )

    def _do_expect_status(self, step: Step) -> None:
        """Assert the rip status line contains some text.

        **The surface is named, not implied.** This verb spent its life
        unimplemented on the argument that there is no single "status line" — the
        rip pane has one, the disc panel has another — so any implementation would
        pick one and silently mean only that. The objection is about *silence*, not
        about ambiguity: the fix is to pick the surface and say which, here, in the
        help text, and in every message this emits. It reads
        `RipProgress.current_status()`, the label under the Overall bar, which is
        also what the desktop notification reads — so the two cannot disagree about
        what the status is.

        The alternative was deleting the verb. It could not stay as it was: it is
        published in the generated `docs/script-language.md`, so the full-acceptance
        rig script used it and got an ERROR back (2026-08-23). A row kept as a
        marker of a known gap is, from a script author's side, indistinguishable
        from a capability.

        **Matching is case-insensitive and substring**, like `expect-dialog`: the
        line carries a `HH:MM:SS ·` stamp and a sentence assembled from several
        sources, so an exact match would be unusable and a case-sensitive one would
        fail on sentence capitalisation nobody can predict from a script.

        The whole rest of the line is reported on a failure. A status assertion that
        says only "no match" makes the reader re-run a two-hour rip to find out what
        it *did* say.
        """
        wanted = " ".join(step.args).strip()
        if not wanted:
            self._record(
                step, Outcome.ERROR, "expect-status needs some text to look for"
            )
            return
        progress = getattr(self._window, "_rip_progress", None)
        reader = getattr(progress, "current_status", None)
        if not callable(reader):
            self._record(
                step,
                Outcome.ERROR,
                "no rip-progress status line on the window to read",
            )
            return
        actual = str(reader() or "")
        if wanted.casefold() in actual.casefold():
            self._record(step, Outcome.PASS, f"status line contains {wanted!r}")
            return
        self._record(
            step,
            Outcome.FAIL,
            f"the rip status line does not contain {wanted!r} — it reads {actual!r}"
            if actual
            else f"the rip status line does not contain {wanted!r} — it is empty "
            "(no status has been set yet)",
        )

    def _do_expect_rip_complete(self, step: Step) -> None:
        """Assert the last rip FINISHED, read from the ripper's own log.

        **The assertion `expect-status Done` should always have been.** On
        2026-09-03 section N — ARCHIVAL, *"the accuracy claim itself"* — failed
        while its rip was fine: 14 of 14 tracks written, ``Ripping errors: 0``,
        completion footer intact, ``secure re-read genuinely exercised: YES``.
        The step failed because the status line read *"Read stability: tracks 3,
        4, 5 still didn't read identically even after an automatic re-rip"*, and
        that sentence does not contain the word "Done".

        The product is right and the assertion was wrong.
        :mod:`platterpus.ui.rip_progress` deliberately overwrites the completion
        line with the stability summary, because a 2026-07-28 audit found the
        unattended user being told *"all tracks ripped cleanly"* while the window
        said a track never read reproducibly. `expect-status Done` therefore
        conflates **finished** with **finished clean**, and on a disc holding one
        track that will not converge it can only ever report the second.

        **The fix is not a looser match.** A loosened assertion with a confident
        comment is worse than no assertion — so this does not accept "Done or a
        warning"; it asserts a different and stronger proposition, against the
        artifact rather than the display: the *ripper's own* completion record.
        That is `CLAUDE.md`'s *assert against the source artifact* applied to the
        acceptance script, and it makes the check disc-independent, which
        `expect-status Done` could never be.

        **Every answer here is tri-state.** A log with no completion footer
        reports NOT DETERMINED and FAILS: an absence is a fact about the capture
        before it is a fact about the rip, and it is never a pass.

        **What it deliberately does NOT grade: read instability.** A track whose
        re-reads disagree is a fact about the *disc*, already surfaced three other
        ways (the status line, `rig-check`'s paranoia row, and the per-track
        verdict in the EAC-compatible log, which since 0.6.35 no longer stamps
        such a track ``Copy OK``). Grading it here would make the acceptance run
        fail on an ordinary CD, which the script's own header promises it accepts.
        It is *counted and reported* in the detail either way, because a fact
        dropped silently reads as a fact absent.

        Floors, so this cannot pass by finding nothing: a log must exist, it must
        carry at least one track, and its own tally must agree with itself.
        """
        # Imported here rather than at module scope: the ui-script layer is
        # otherwise free of parser imports, and this is the one handler that
        # needs the type. A lazy import keeps that boundary while still giving
        # mypy something better than `Any` to narrow against.
        from platterpus.parsers.rip_log import RipLog

        parsed = getattr(self._window, "_last_rip_log", None)
        requested = getattr(self, "_rip_log_when_requested", _NO_RIP_REQUESTED)
        if requested is not _NO_RIP_REQUESTED and parsed is requested:
            self._record(
                step,
                Outcome.FAIL,
                "no rip has finished since this section asked for one — the "
                "window still holds the SAME parsed log it held when `rip` ran, "
                "so grading it would report a previous section's rip as this "
                "one's. `rip` can be refused (no disc, Start disabled, a rip "
                "already running) and leave that field untouched.",
            )
            return
        if not isinstance(parsed, RipLog):
            self._record(
                step,
                Outcome.FAIL,
                "no rip log has been parsed in this session, so there is no "
                "completion record to read — this step reports the state it "
                "found rather than passing on an empty room. Put it after a "
                "`rip` and its `wait-for-rip`.",
            )
            return

        problems: list[str] = []

        completed = parsed.rip_completed
        if completed is None:
            problems.append(
                "the log carries no completion footer, so whether the rip "
                "finished is NOT DETERMINED — which is never a pass"
            )
        elif not completed:
            reason = parsed.rip_completed_reason.strip()
            problems.append(
                "the log says the rip did not complete"
                + (f" ({reason})" if reason else " and gives no reason")
            )

        if parsed.interrupted_at:
            problems.append(
                f"the ripper recorded an interruption at {parsed.interrupted_at!r}"
            )
        if parsed.log_truncated:
            problems.append("the log is truncated — the record itself is incomplete")
        if parsed.last_track_incomplete:
            problems.append("the last track's block is incomplete in the log")

        # FLOORS. A completion footer on a log with no tracks is not a rip.
        if not parsed.tracks:
            problems.append("the log carries no track blocks at all")
        # THE DENOMINATOR IS THE DISC, NOT THE SELECTION — measured, from seven
        # real rips in the 2026-09-03 bundle. cyanrip's footer reads
        # ``Rip completed:  yes (2 of 14 tracks)`` for a two-track selection off
        # a fourteen-track disc, so ``tracks == total`` is TRUE ONLY for a
        # whole-disc rip. The first version of this handler asserted exactly
        # that, which would have failed all five partial-rip sites it was added
        # to — turning five passing ARCHIVAL sections into five failures, worse
        # than the defect it was written for.
        #
        # The invariant that actually holds, on all seven of those rips, is that
        # the footer's completed count equals the number of track blocks the log
        # carries: the record agrees with itself. That is disc-independent AND
        # selection-independent, which is the property this verb exists to have.
        done, total = parsed.rip_completed_tracks, parsed.rip_completed_total
        if total is not None and total < 1:
            problems.append(f"the log's own disc total is {total}")
        if done is not None and done < 1:
            problems.append(f"the log says {done} tracks completed")
        if done is not None and done != len(parsed.tracks):
            problems.append(
                f"the log claims {done} track(s) completed but carries "
                f"{len(parsed.tracks)} track block(s) — the record disagrees "
                "with itself"
            )
        if done is not None and total is not None and done > total:
            problems.append(f"the log tallies {done} completed of a {total}-track disc")

        # The disc-quality census: reported, never graded. Tri-state per track,
        # so "we did not measure convergence" cannot render as "it converged".
        unstable = [
            t.number for t in parsed.tracks if t.secure_rerip_converged is False
        ]
        unmeasured = sum(1 for t in parsed.tracks if t.secure_rerip_converged is None)
        census = f"{len(parsed.tracks)} track(s) in the log"
        if unstable:
            census += (
                f"; read stability: track(s) {', '.join(str(n) for n in unstable)} "
                "did NOT converge — a property of the disc, reported here and "
                "deliberately not graded by this step"
            )
        elif unmeasured == len(parsed.tracks):
            census += "; convergence not measured (no secure re-read in this rip)"
        else:
            census += "; every measured track converged"

        if problems:
            self._record(step, Outcome.FAIL, "; ".join(problems) + f" [{census}]")
            return
        self._record(
            step,
            Outcome.PASS,
            f"the ripper's own log records the rip as complete — {census}",
        )

    def _do_rip(self, step: Step) -> None:
        """Press Start.

        Routed through `RipControls._on_start`, which is the slot the button is
        connected to: it builds the real `RipParameters` from the real UI state and
        emits `rip_requested`. Constructing parameters here instead would be a second
        description of what a rip *is*, and it would drift the first time a control
        was added.

        Refuses when the controls themselves say they cannot start, and says which —
        an unstarted rip that reports PASS is the worst outcome available here.

        **Why an open dialog is one of those refusals (0.6.18).** The two guards
        below it — "a rip is already running" and `can_start()` — are both read on
        the GUI thread and **both pass while a modal is up**, because the window
        opens the overwrite confirmation *before* it creates the worker and the
        controls are still enabled behind it. Qt delivers this runner's timer
        events inside a modal's nested event loop (the property that lets a
        script dismiss a modal at all), so the batch keeps advancing: a second
        `rip` step reaches here, both guards say yes, and answering the first
        dialog then launches **two concurrent cyanrip processes against one
        drive**. `CLAUDE.md`'s recurring trap, in the harness rather than the
        product — *did I check the preconditions where the thing HAPPENS, or
        where it was scheduled?*
        """
        # REMEMBER WHICH LOG WAS CURRENT WHEN THIS SECTION ASKED FOR A RIP —
        # TAKEN HERE, AHEAD OF EVERY REFUSAL PATH, AND THAT PLACEMENT IS THE FIX.
        #
        # `expect-rip-complete` reads `window._last_rip_log`, which is
        # SESSION-scoped: it holds the previous section's log until a new rip
        # finishes and replaces it. Without a freshness key the verb reports a
        # green completion for a rip that never started — the previous
        # section's, in a transcript claiming this one's. That is the "satisfied
        # by the WRONG thing" shape, and strictly worse than the
        # `expect-status Done` it replaced.
        #
        # The first version of this marker sat on the SUCCESS path, one line
        # above `QTimer.singleShot`. That is precisely backwards: the case the
        # guard exists for is a rip that was REFUSED — no disc, Start disabled,
        # a rip already running — and on every one of those paths the marker was
        # never taken, so the guard could not fire. Caught by the test written
        # for it, which is the only reason it is not in the release.
        #
        # Keyed on OBJECT IDENTITY rather than a bool: "has a rip finished since
        # I asked for one" is a fact about a specific log, and a flag scoped to
        # the runner would need resetting at a moment no call site owns — the
        # `_signalled` defect `CLAUDE.md` records under *when a flag needs a
        # reset, ask whether it wanted to be an identity comparison*.
        self._rip_log_when_requested = getattr(self._window, "_last_rip_log", None)
        controls = getattr(self._window, "_rip_controls", None)
        if controls is None:
            self._record(step, Outcome.ERROR, "no rip controls on the window")
            return
        blocking = _active_dialog()
        if blocking is not None:
            title = blocking.windowTitle()
            # **NAME THE VERB THAT ANSWERS *THIS* DIALOG.** The generic advice was
            # `ok` / `cancel`, which is wrong for the release picker: `answer-dialog`
            # presses a button, and the picker needs a ROW CHOSEN, which only
            # `pick-release` does. An operator who followed the message would press
            # Ok on a picker with no selection. Reported from the rig on 2026-08-26,
            # where this exact message sent someone to the wrong verb — a diagnosis
            # that is accurate about the problem and wrong about the remedy is the
            # shape `CLAUDE.md` warns about (every word true, the message wrong).
            fix = (
                "Answer it in the script with `pick-release <mbid|N>` — "
                "`answer-dialog` presses a button and this dialog needs a row "
                "selected, so Ok alone would not resolve it."
                if title == _RELEASE_PICKER_TITLE
                else "Answer it in the script (`ok` / `cancel`) before ripping."
            )
            self._record(
                step,
                Outcome.FAIL,
                f"a dialog is waiting for an answer: {title!r}. Refusing to press "
                "Start behind it — the previous step's rip may not have been "
                "created yet, and starting a second one would put two ripper "
                f"processes on one drive. {fix}",
            )
            return
        if getattr(self._window, "_rip_worker", None) is not None:
            self._record(step, Outcome.FAIL, "a rip is already running")
            return
        can_start = getattr(controls, "can_start", None)
        if callable(can_start) and not can_start():
            self._record(
                step,
                Outcome.FAIL,
                "the Start button is not enabled — no disc identified, no drive "
                "selected, or a rip/scan is already active",
            )
            return
        start = getattr(controls, "_on_start", None)
        if start is None:
            self._record(step, Outcome.ERROR, "the rip controls have no _on_start()")
            return
        self._record(step, Outcome.PASS, "start requested")
        QTimer.singleShot(0, start)

    def _do_pick_release(self, step: Step) -> None:
        """Answer the MusicBrainz release picker without a person.

        **Why this is a verb and not an app setting.** A disc with more than one
        MusicBrainz candidate opens a modal picker and waits, which is correct
        behaviour for a person and fatal for an unattended batch — the rig disc
        (*Every Breath You Take — The Classics*) returns **four**. Auto-choosing
        one *in the product* would silently pick the tags for every ambiguous
        disc a user ever rips, which is a real archival decision and not ours to
        make on their behalf. In a **script** it is exactly right: the choice is
        written down, it is in the transcript, and it applies only to this run.
        `CLAUDE.md`: a new testing capability is a script verb.

        Usage — ``pick-release <mbid|prefix|N>``. An MBID (or an unambiguous
        prefix of one) is preferred over a row number, because MusicBrainz
        ordering is not stable and ``pick-release 2`` would silently mean a
        different release next month.

        Non-blocking, like `wait-for-rip`: it arms the deadline with a predicate
        the tick polls, so the GUI keeps running while the scan finishes. Qt
        delivers timer events inside a modal's nested event loop, which is the
        whole reason a script can dismiss a modal at all.

        **A picker that never appears is a PASS, and that needs justifying** —
        it is exactly the "satisfied by finding nothing" shape. It is only
        accepted alongside *positive* evidence: tracks are loaded, so the disc
        identified unambiguously and there was genuinely nothing to pick. Waiting
        with an empty track table keeps waiting until the timeout.
        """
        # `args[0]`, never `joined()`: with the optional timeout present,
        # `joined()` returns "d14a7546… 60" and the MBID would match nothing.
        # Caught by a test that passes the timeout, which the first version
        # of this verb did not have.
        wanted = step.args[0].strip()
        if not wanted:
            self._record(
                step, Outcome.ERROR, "pick-release needs an MBID or a row number"
            )
            return
        try:
            seconds = float(step.args[1]) if len(step.args) > 1 else 120.0
        except ValueError:
            self._record(
                step, Outcome.ERROR, f"{step.args[1]!r} is not a number of seconds"
            )
            return
        if seconds <= 0:
            self._record(step, Outcome.ERROR, "the timeout must be positive")
            return
        seconds = min(seconds, MAX_WAIT_S)
        self._arm_deadline(step, seconds, lambda: self._try_pick_release(wanted))
        self._deadline_timeout_detail = (
            f"no release picker appeared within {seconds:.0f}s and no tracks "
            "loaded either — the disc scan did not finish, so nothing was chosen"
        )

    def _loaded_track_count(self) -> int:
        """How many track rows the window is showing right now.

        One reader, used by both phases of `pick-release`, so "are the tracks
        there yet" cannot be answered two different ways by the same verb.
        """
        table = getattr(self._window, "_track_table", None)
        if table is None:
            return 0
        tracks = getattr(table, "tracks", None)
        return len(tracks()) if callable(tracks) else 0

    def _try_pick_release(self, wanted: str) -> bool:
        """One poll: choose in the picker if it is up, then wait for the tracks.

        Returns True when the wait is over. Sets `_deadline_outcome` /
        `_deadline_detail` so the transcript records *which* release was taken,
        out of how many, rather than a bare "ok".

        **Two phases, and the second one is the bug fix (0.6.17).** Accepting the
        dialog is not the end of the work: `MainWindow._fetch_release_detail`
        *emits* to the MusicBrainz worker thread rather than calling it, so when
        `dialog.accept()` returns, the release detail has not been fetched, the
        tags are not applied and the track table is still empty. The first
        version of this verb returned True right there, so every step after it
        raced a network round-trip it never waited for — and lost, every time.
        Measured on the rig (2026-08-18, app 0.6.16): the picker was accepted at
        `20:08:25,436` and `expect-tracks 3` failed with "found 0" at
        `20:08:25,560` — **124 ms** later, three times in one run across two
        sections. The tracks did arrive; nothing was watching for them. Eight of
        that run's eight failures descend from this one line.

        So after choosing we keep polling until the track table is non-empty.
        That also makes the two arms of this verb symmetric, which is the deeper
        point: the "no picker appeared" arm already refused to pass on an empty
        table (see the docstring above — *satisfied by finding nothing*), while
        the "picker appeared" arm passed on one. A verb that demands positive
        evidence on one branch and not the other has not applied the rule; it
        has applied it where it was first noticed.
        """
        # Phase 2: a release was chosen on an earlier tick — wait for it to land.
        if self._picked_release is not None:
            mbid, title, row, total = self._picked_release
            loaded = self._loaded_track_count()
            if loaded == 0:
                # Re-point the timeout message at where we actually are. The one
                # set at arming time ("no release picker appeared") would now be
                # a false statement — the picker appeared and was answered, and
                # a report that says otherwise sends the next reader looking in
                # the wrong subsystem.
                # `LOG_POINTER` names the log FILE, rather than saying "the log"
                # and leaving the reader to find it — the rule
                # `tests/test_failure_surfaces.py` enforces, and a transcript
                # read on another machine is exactly where a bare "check the
                # log" has no referent.
                from platterpus.ui.failure_text import LOG_POINTER

                self._deadline_timeout_detail = (
                    f"chose {mbid} ({title}) — row {row} of {total} — but no "
                    "tracks ever loaded. The release detail fetch (MusicBrainz) "
                    f"did not finish or returned nothing. {LOG_POINTER}"
                )
                return False  # the MB detail fetch is still in flight
            self._deadline_detail = (
                f"chose {mbid} ({title}) — row {row} of {total}; "
                f"{loaded} track(s) loaded"
            )
            return True

        dialog = _release_picker()
        if dialog is None:
            loaded = self._loaded_track_count()
            if loaded > 0:
                self._deadline_detail = (
                    f"no picker appeared and {loaded} track(s) are loaded — the "
                    "disc identified unambiguously, so there was nothing to pick"
                )
                return True
            return False  # scan still running; keep waiting

        releases = list(getattr(dialog, "_releases", []))
        index = _match_release(releases, wanted)
        if index is None:
            offered = ", ".join(getattr(r, "mbid", "?") for r in releases) or "none"
            self._deadline_outcome = Outcome.FAIL
            self._deadline_detail = (
                f"{wanted!r} is not among the {len(releases)} release(s) offered: "
                f"{offered}. Leaving the picker open rather than choosing something "
                "else — a rip tagged from the wrong release is worse than a failed step."
            )
            return True

        chosen = releases[index]
        # `getattr`, not `dialog._table`: mypy types this as a bare `QDialog`
        # (the module is imported *by* the picker, so the real class cannot be
        # imported here without a cycle) and a private attribute on it is an
        # `attr-defined` error. It is also the honest shape — the attribute is
        # reached duck-typed, so a rename should be a legible failure rather
        # than an AttributeError inside an unattended batch.
        table = getattr(dialog, "_table", None)
        # `setCurrentCell(row, 0)`, NOT `setCurrentRow`. The picker's table is a
        # `QTableWidget`, which has no `setCurrentRow` — that is `QListWidget`'s
        # API. Shipped in 0.6.12b4 and raised `AttributeError` on the rig 25
        # times in one step (2026-08-13). Checked against the real class here
        # rather than written from memory a second time.
        select = getattr(table, "setCurrentCell", None) if table is not None else None
        if select is None:
            self._deadline_outcome = Outcome.ERROR
            self._deadline_detail = (
                "the release picker's table has no `setCurrentCell` — its "
                "internals changed and this verb needs updating; refusing rather "
                "than guessing"
            )
            return True
        select(index, 0)
        mbid = getattr(chosen, "mbid", "?")
        title = getattr(chosen, "title", "") or "?"
        dialog.accept()
        # Hand off to phase 2 rather than declaring victory: the window has only
        # just *asked* for the release detail. See this method's docstring.
        self._picked_release = (mbid, title, index + 1, len(releases))
        return False

    def _do_wait_for_rip(self, step: Step) -> None:
        """Wait for the rip to finish, up to a timeout.

        Non-blocking: it arms the runner's own deadline with a predicate, so the GUI
        thread keeps running its event loop while a rip that takes 25 minutes
        proceeds. A `time.sleep` here would freeze the window for the whole rip and
        break the very thing being measured.

        The predicate is "the window no longer holds a rip worker", which is what
        `_on_rip_finished` clears — the same fact the UI uses to re-enable its
        controls, rather than a second notion of doneness that could disagree.
        """
        try:
            seconds = float(step.args[0])
        except ValueError:
            self._record(step, Outcome.ERROR, f"{step.args[0]!r} is not a number")
            return
        if seconds <= 0:
            self._record(step, Outcome.ERROR, "a rip needs a positive timeout")
            return
        # A BOUND THAT IS TOO GENEROUS MUST NOT BECOME NO BOUND AT ALL.
        #
        # **This cost a night of drive time on 2026-08-24.** The old code recorded
        # FAIL and `return`ed on an over-cap request, so `wait-for-rip 21600` — six
        # hours, against a three-hour cap — waited **zero seconds**. The very next
        # step then graded a rip that had started 0.4 s earlier, the remaining
        # sections ran against a live drive, a `-x -I` cache probe opened the same
        # device 1.2 s later, and the unattended-quit helper declared the batch
        # finished and killed the reader at 1.48% of track 1. The whole-disc secure
        # re-read that section existed for produced no evidence at all.
        #
        # The author's intent in an over-long timeout is unambiguously *"wait a
        # long time"*. Refusing to wait is the one reading that cannot be what they
        # meant, and it is the dangerous one: every later step silently becomes a
        # measurement of a different machine state. So the request is CLAMPED and
        # the wait happens.
        #
        # The clamp is still reported — loudly, in the outcome's detail either way
        # — because a script asking for more than the cap is a script whose author
        # believes something false about the harness, and silence would leave them
        # believing it. Reported and honoured, rather than reported and refused.
        #
        # (`CLAUDE.md`: *"fail-safe" is defined against the thing being protected*.
        # The thing protected here is the disc pass, not the harness's tidiness.)
        capped = min(seconds, MAX_RIP_WAIT_S)
        clamp_note = ""
        if capped < seconds:
            clamp_note = (
                f" [CLAMPED: asked for {seconds:.0f}s, the cap is "
                f"{MAX_RIP_WAIT_S:.0f}s — waiting the cap, not skipping the wait]"
            )
            log.warning(
                "ui script L%s: wait-for-rip asked for %.0fs; clamping to the "
                "%.0fs cap and waiting it",
                step.line_no,
                seconds,
                MAX_RIP_WAIT_S,
            )
        window = self._window
        # NOTHING RUNNING IS A FAILURE, NOT AN INSTANT PASS.
        #
        # The predicate below is "no rip worker exists", which is true both when a
        # rip has finished and when one never started. On the 2026-08-12 rig run
        # `rip` had just failed — Start was disabled because the disc never
        # identified — and this step then reported **ok immediately**, in SECTION
        # D, in a transcript whose whole purpose was proving the rip happened.
        # The fork logged it as a vacuous pass and they were right: a wait that
        # succeeds by finding nothing is the shape this script's own header
        # forbids in point 3.
        if getattr(window, "_rip_worker", None) is None:
            # NAME THE MODAL IF THERE IS ONE. "No rip is running" is true and
            # useless when the reason is that the app is holding a confirmation
            # up and waiting for a person: the rip was requested, the worker just
            # does not exist yet. On the rig that read as an unexplained failure
            # (0.6.18) — the diagnosis was in the app, on screen, and not in the
            # transcript.
            blocking = _active_dialog()
            detail = (
                "no rip is running, so there is nothing to wait for — this step "
                "reports the state it found rather than passing on an empty room"
            )
            if blocking is not None:
                title = blocking.windowTitle()
                # SAME CORRECTION AS `rip`'s GUARD, APPLIED HERE TOO. Both sites
                # named `answer-dialog` unconditionally, and for the release picker
                # that is the wrong verb: `answer-dialog` presses a button and the
                # picker needs a ROW SELECTED, so Ok alone resolves nothing. Fixed
                # in both places at once rather than at the one an operator
                # happened to hit — `CLAUDE.md` / `docs/testing.md` §5.o: a rule
                # enforced at the place it was learned is not enforced.
                if title == _RELEASE_PICKER_TITLE:
                    remedy = (
                        "Put `pick-release <mbid|N> 120` BEFORE `rip`, not after: "
                        "this dialog opens from the disc scan rather than from the "
                        "rip, and it needs a row chosen — `answer-dialog ok` "
                        "presses a button and would leave it unresolved."
                    )
                else:
                    remedy = (
                        f"Put `answer-dialog ok 30 {title}` between `rip` and this "
                        "step. NOT a bare `ok`: the confirmation appears a beat "
                        "after `rip` returns, so `ok` would race it and fail with "
                        "'no dialog is open' about half the time."
                    )
                detail += (
                    f". A dialog is waiting for an answer: {title!r} — the rip was "
                    "requested but the app is blocked on it, so no worker exists "
                    f"yet. {remedy}"
                )
            # The clamp travels here too. It is already in the app log, but the
            # TRANSCRIPT is what the other project reads and what a person greps
            # at 6am — `CLAUDE.md`: a diagnosis captured and never surfaced is the
            # same bug from the reader's side.
            self._record(step, Outcome.FAIL, (detail + clamp_note).strip())
            return
        self._arm_deadline(
            step, capped, lambda: getattr(window, "_rip_worker", None) is None
        )
        # AFTER arming, which resets both detail fields. Carried into whichever
        # outcome the wait produces, so the clamp is visible in the transcript on
        # the success path too — a script that asked for six hours and got three
        # needs to know that on the run where it did not matter, not only on the
        # run where it did.
        if clamp_note:
            self._deadline_detail = (self._deadline_detail + clamp_note).strip()
            self._deadline_timeout_detail = (
                f"the rip was still running when the {capped:.0f}s cap "
                f"expired{clamp_note}"
            )

    def _do_cancel_rip(self, step: Step) -> None:
        """Cancel a rip in progress, through the window's own Cancel handler."""
        if getattr(self._window, "_rip_worker", None) is None:
            self._record(step, Outcome.FAIL, "no rip is running")
            return
        handler = getattr(self._window, "_on_rip_cancel", None)
        if handler is None:
            self._record(step, Outcome.ERROR, "the window has no _on_rip_cancel()")
            return
        self._record(step, Outcome.PASS, "cancel requested")
        QTimer.singleShot(0, handler)

    # --- Verbs: Settings, by config field name --------------------------------
    #
    # **Field names, not row labels**, and that is a deliberate change from the
    # vocabulary's first draft. A row label is display text: it is translated,
    # re-worded, and re-ordered, so a script keyed on it breaks for reasons that have
    # nothing to do with the setting. The `Config` field name is the same string the
    # TOML file uses, the validator names in its errors, and a bug report quotes —
    # one identifier all the way down.
    #
    # **Every scripted set goes through the real validator.** `settings_validation`
    # is the source of truth for what a field may hold (`CLAUDE.md`: validation lives
    # in a pure, testable function, and the widget's own range is a convenience, not
    # the check). A script bypassing it could persist a value the dialog would have
    # refused, and the next launch would silently reset it — a config file that
    # disagrees with the run that wrote it.

    def _do_set(self, step: Step) -> None:
        """``set <config-field> <value>`` — change a setting and persist it."""
        field = step.args[0]
        raw = " ".join(step.args[1:])
        current = getattr(self._window, "_config", None)
        if current is None:
            self._record(step, Outcome.ERROR, "the window has no config")
            return
        if not hasattr(current, field):
            self._record(
                step,
                Outcome.ERROR,
                f"no setting called {field!r} — use the config.toml field name",
            )
            return

        coerced, problem = _coerce_setting(getattr(current, field), raw)
        if problem:
            self._record(step, Outcome.ERROR, f"{field}: {problem}")
            return

        import dataclasses

        candidate = dataclasses.replace(current, **{field: coerced})
        # `rip_goal` IS NOT A SETTING; IT IS A NAME FOR A SET OF THEM.
        #
        # In Settings, choosing a goal calls `apply_preset`, which writes every
        # field the preset defines. Writing the field alone produced a config no
        # dialog could ever create: `rip_goal="archival"` beside fast-verified
        # values, which `detect_goal` then reports as `custom` — the label and the
        # settings disagreeing, in the one surface this project writes its tests
        # in. A script could therefore "select the archival goal" and rip with
        # exactly the settings it was trying not to use.
        #
        # Delegated to the real `apply_preset`, never restated here, so the script
        # surface and the dialog cannot answer "what does this goal mean?"
        # differently (`CLAUDE.md`: two surfaces, one question, one key).
        if field == "rip_goal":
            from platterpus.goal_presets import GOAL_CUSTOM, apply_preset

            if coerced != GOAL_CUSTOM:
                candidate = apply_preset(current, str(coerced))
        rejection = _validation_error_for(candidate, field)
        if rejection:
            # Refused, and the validator's own sentence is what the transcript
            # carries — a script must not be able to write a value the dialog
            # would have rejected.
            self._record(step, Outcome.FAIL, f"{field} rejected: {rejection}")
            return

        # `setattr` rather than a direct assignment, and NOT a `# type: ignore`.
        # The runner's window is typed `QWidget` on purpose — it is the widest thing
        # this module needs and it keeps `uiscript` from importing `MainWindow` (an
        # import cycle, since the window constructs the runner). Every other window
        # access here already goes through `getattr` with a None fallback for the
        # same reason; the assignment was the one place that reached for a concrete
        # attribute and it is what mypy flagged. Silencing the checker would have
        # hidden a real inconsistency rather than resolved it.
        setattr(self._window, "_config", candidate)  # noqa: B010 — see above
        controls = getattr(self._window, "_rip_controls", None)
        if controls is not None:
            # The same push the Settings dialog does on Accept, so the next rip
            # reflects the edit instead of the config the controls were built with.
            controls.set_config(candidate)
        saver = getattr(self._window, "_save_config", None)
        saved = ""
        if saver is not None:
            try:
                saver(candidate)
            except OSError as exc:
                saved = f" (in effect for this session; not saved to disk: {exc})"
        self._record(step, Outcome.PASS, f"{field} = {coerced!r}{saved}")

    def _do_expect_ripper_under_review(self, step: Step) -> None:
        """``expect-ripper-under-review`` — the installed build is the round's subject.

        **Reads the constant, never a literal in the script.** The acceptance
        script used to assert an exact build tag, and the cyanrip fork published
        three betas in two days on the channel our own installer resolves — so
        three times an operator who followed our instructions installed the build
        we sent them to and was told by our own section A that it was the wrong
        one. Their lap 4 §C named the shape: *a hardcoded build tag in a committed
        script is a second copy of a fact that lives in `release-manifest.json`,
        and only one copy has a checker.*

        `PIN_UNDER_REVIEW` is derived from the newest inbound handshake lap by
        ``tests/test_handshake_pin_under_review.py``, so this reads one key rather
        than a duplicate of one, and a pin move now fails in CI rather than on a
        rig.

        Matches against the previous ``cyanrip`` step's output, exactly as
        ``expect-cyanrip`` does — the banner is the only statement of identity
        derivable from the binary itself.
        """
        from platterpus.deps import fork_source

        expected = f"{fork_source.FORK_BRANCH}-g{fork_source.PIN_UNDER_REVIEW}"
        if not self._last_cyanrip_argv:
            self._record(
                step,
                Outcome.ERROR,
                "no cyanrip command has run yet — put `cyanrip --version` above "
                "this step so there is a banner to read",
            )
            return
        if expected in self._last_cyanrip_output:
            self._record(
                step,
                Outcome.PASS,
                f"installed build is {expected} — {_pin_role_phrase()}",
            )
            return
        # **NAME THE COMMAND, AND DO NOT CLAIM A ROUND IS OPEN WHEN NONE IS.**
        # This said "the build the open handshake round is reviewing" and pointed at
        # "Settings -> the ripper beta channel, then take the offer". Both went wrong
        # on 2026-08-27, minutes apart, in the one message an operator reads at 2am:
        #
        #   * round 14 had CLOSED, so no round was reviewing anything — the sentence
        #     was false, and it is the kind of false that misdirects, because it
        #     implies the operator is behind rather than ahead;
        #   * the remedy named a GUI path when a one-line command exists. `CLAUDE.md`
        #     is explicit that a procedure handed back in prose is work handed back;
        #     an operator who can paste one command should be given one command.
        #
        # The run itself was fine — it aborted in two seconds rather than spending a
        # night on the wrong binary, which is the abort machinery working. What cost
        # the attempt was advice that did not match the assertion.
        #
        # And the invocation comes from `build_info.self_invocation()` rather than
        # the literal `platterpus`: there is no such command on PATH for an AppImage
        # install, which is this project's PRIMARY channel. The first draft of this
        # message hardcoded both spellings joined by an "or", and
        # `tests/test_self_invocation_sweep.py` refused it — correctly, and for a
        # second reason it does not state: handing an operator a choice of two
        # commands, one of which will fail, is the "work handed back" shape again.
        self._record(
            step,
            Outcome.FAIL,
            f"the installed cyanrip is NOT {expected} — {_pin_role_phrase()}. "
            f"Every later section would be evidence about a different binary.\n"
            f"FIX IT WITHOUT LEAVING THE APP:\n"
            f"    Help -> Check for cyanrip updates... -> Install it anyway\n"
            f"then start the acceptance test again.\n"
            f"(Or, if you prefer a terminal: {build_info.self_invocation()} "
            f"--install-ripper {fork_source.PIN_UNDER_REVIEW})\n"
            f"{_bounded_output(self._last_cyanrip_output)}",
        )

    def _do_probe_ripper_wrapper(self, step: Step) -> None:
        """``probe-ripper-wrapper`` — which link in the chain fails to exit.

        **The fork's round-15 §2 ask, absorbed.** Two consecutive rig mornings
        produced zero rip artifacts because a probe of
        ``~/.local/bin/cyanrip --version`` printed its banner and then never
        returned. Their lap established three independent ways the hang is not in
        cyanrip and asked the maintainer to run three shell commands. `CLAUDE.md`
        forbids handing that back: *every "now run this, then run that" in a
        written procedure is a thing the software was supposed to do.*

        **It never records FAIL, and that is deliberate rather than lenient.** A
        wrapper that hangs from an interactive shell does not affect the app,
        which pipes its I/O — so the only thing a FAIL would achieve is aborting
        a multi-hour pass over a condition that changes no rip. What matters is
        that the verdict reaches the transcript, because the transcript is the
        one file the operator uploads.

        Runs on the script runner's own thread, which is not the GUI thread — the
        probe spawns processes and bounds them, and doing that in a dialog slot is
        the freeze this project has paid for three times.
        """
        from platterpus.deps import ripper_wrapper_probe

        try:
            report = ripper_wrapper_probe.probe()
        except Exception as exc:  # noqa: BLE001 — a diagnostic must not end the run
            log.exception("probe-ripper-wrapper: the probe itself failed")
            self._record(
                step,
                Outcome.INFO,
                f"the wrapper probe could not run: {exc!r} — recorded as "
                f"not determined, which is not a pass",
            )
            return
        # The whole rendered record, not just the verdict: a diagnosis we captured
        # and did not surface is the same bug from the reader's side.
        self._record(
            step,
            Outcome.INFO,
            f"{report.verdict.value}: {report.summary}\n"
            f"{ripper_wrapper_probe.render(report)}",
        )

    def _do_expect_refused(self, step: Step) -> None:
        """``expect-refused <field> <value>`` — assert the validator refuses it.

        **The inverse of :meth:`_do_set`, and the only shape in which a script can
        test that a guard fired.** `set` records FAIL on a refusal, which is the
        right report for an accidental bad value and the wrong one for a
        deliberate probe — so before this verb existed, the acceptance suite
        exercised none of the input validation `CLAUDE.md` calls institutional.

        **Both halves are asserted.** A refusal that still writes the value is
        worse than no guard at all, because the log says the input was rejected
        while the setting reaches cyanrip's argv anyway. Checking only the
        refusal cannot see that, and *"can this check be satisfied by the wrong
        thing?"* is the question this project keeps paying for.

        Delegates to the same `_coerce_setting` + `_validation_error_for` pair
        `_do_set` uses, never a second copy: a validator a test calls differently
        from the product is a validator two things can disagree about.
        """
        field = step.args[0]
        raw = " ".join(step.args[1:])
        current = getattr(self._window, "_config", None)
        if current is None:
            self._record(step, Outcome.ERROR, "the window has no config")
            return
        if not hasattr(current, field):
            self._record(
                step,
                Outcome.ERROR,
                f"no setting called {field!r} — use the config.toml field name",
            )
            return
        before = getattr(current, field)

        coerced, problem = _coerce_setting(before, raw)
        if problem:
            # A value the COERCER rejects never reaches the validator, and that is
            # still a refusal at the boundary — which is what this verb asserts.
            # Named separately so the transcript says which layer caught it.
            self._record(
                step,
                Outcome.PASS,
                f"refused at type coercion: {problem}; {field} is still {before!r}",
            )
            return

        import dataclasses

        candidate = dataclasses.replace(current, **{field: coerced})
        rejection = _validation_error_for(candidate, field)
        if rejection:
            # The value is NOT written — `candidate` is a local and nothing above
            # assigned it to the window. Asserted rather than assumed, because the
            # whole point of the verb is the pair.
            still = getattr(getattr(self._window, "_config"), field)  # noqa: B009
            if still != before:
                self._record(
                    step,
                    Outcome.FAIL,
                    f"the validator refused {raw!r} — {rejection} — but {field} "
                    f"CHANGED from {before!r} to {still!r}. A refusal that writes "
                    f"the value anyway is worse than no guard: the log says the "
                    f"input was rejected while the setting still reaches the rip.",
                )
                return
            self._record(
                step,
                Outcome.PASS,
                f"refused, and {field} is still {before!r} — {rejection}",
            )
            return
        self._record(
            step,
            Outcome.FAIL,
            f"expected {field}={raw!r} to be REFUSED and it was ACCEPTED. The "
            f"validator is the source of truth for this input and it let it "
            f"through; a widget range is a convenience, not the validation.",
        )

    def _do_expect(self, step: Step) -> None:
        """``expect <config-field> <value>`` — assert a setting equals a value."""
        self._compare_setting(step, contains=False)

    def _do_expect_contains(self, step: Step) -> None:
        """``expect-contains <config-field> <text>`` — assert a setting contains text."""
        self._compare_setting(step, contains=True)

    def _compare_setting(self, step: Step, *, contains: bool) -> None:
        field = step.args[0]
        wanted = " ".join(step.args[1:])
        config = getattr(self._window, "_config", None)
        if config is None or not hasattr(config, field):
            self._record(step, Outcome.ERROR, f"no setting called {field!r}")
            return
        actual = getattr(config, field)
        if contains:
            if wanted in str(actual):
                self._record(step, Outcome.PASS, f"{field} contains {wanted!r}")
            else:
                self._record(
                    step, Outcome.FAIL, f"{field} is {actual!r}, which lacks {wanted!r}"
                )
            return
        coerced, problem = _coerce_setting(actual, wanted)
        if problem:
            self._record(step, Outcome.ERROR, f"{field}: {problem}")
            return
        if actual == coerced:
            self._record(step, Outcome.PASS, f"{field} is {actual!r}")
        else:
            self._record(
                step, Outcome.FAIL, f"expected {field} == {coerced!r}, got {actual!r}"
            )

    def _do_select_tracks(self, step: Step) -> None:
        """``select-tracks <all|none|1,3,5-7>`` — choose which tracks the rip covers.

        The per-track half of the surface, and the one a person cannot do
        reproducibly: this is what reaches cyanrip's ``-l``. Ranges are accepted
        because a re-rip of "the tracks that failed last time" is the actual use, and
        spelling out 1-14 by hand is where a transcription error enters.

        Refuses a track number the disc does not have rather than silently ignoring
        it — a selection that quietly drops a number rips a different disc than the
        script says it does.
        """
        table = getattr(self._window, "_track_table", None)
        if table is None:
            self._record(step, Outcome.ERROR, "no track table on the window")
            return
        available = [t.number for t in table.tracks()]
        if not available:
            self._record(step, Outcome.FAIL, "no tracks are loaded to select from")
            return

        spec = step.args[0].strip().lower()
        if spec == "all":
            table.set_all_selected(True)
            self._record(step, Outcome.PASS, f"all {len(available)} tracks selected")
            return
        if spec == "none":
            table.set_all_selected(False)
            self._record(step, Outcome.PASS, "no tracks selected")
            return

        wanted, problem = _parse_track_spec(spec)
        if problem:
            self._record(step, Outcome.ERROR, problem)
            return
        missing = sorted(set(wanted) - set(available))
        if missing:
            self._record(
                step,
                Outcome.FAIL,
                f"the disc has no track(s) {missing} — it has "
                f"{min(available)}-{max(available)}",
            )
            return
        table.set_only_selected(wanted)
        self._record(
            step, Outcome.PASS, f"selected {len(wanted)} track(s): {sorted(wanted)}"
        )

    def _persist(self) -> None:
        """Write the finished run to disk beside its screenshots. Never raises.

        **Why the runner does this and not the console.** Until now the only way
        to get a transcript off the rig was the console's *Save transcript…*
        button — a human selecting text in a window and choosing a filename,
        after an unattended run whose entire purpose was to need no human. On the
        2026-08-12 rig pass the operator pasted it into a chat message instead,
        which is the same work wearing a different hat, and it is the shape
        `CLAUDE.md` names as a defect: *every hand-edit in a written procedure is
        a thing the software was supposed to do.* Now the run leaves a folder and
        the instruction is "upload this folder".

        Both forms, deliberately. ``transcript.txt`` is what a person reads and
        what goes into a handshake lap; ``report.json`` is the same run in the
        shape a parser takes, and the two must come from one render so they
        cannot disagree about what happened.

        Failure is logged and swallowed: a full disk at the end of an hour-long
        disc pass must not lose the run that is still sitting in the window. The
        console's Save button remains as the manual fallback for exactly that.
        """
        directory = self._ensure_artifact_dir()
        if directory is None:
            return  # `_ensure_artifact_dir` already logged why
        for name, text in (
            ("transcript.txt", render(self._report)),
            ("report.json", json.dumps(self._report.as_dict(), indent=2)),
        ):
            try:
                (directory / name).write_text(text, encoding="utf-8")
            except OSError as exc:
                log.error("could not write %s: %r", directory / name, exc)
        log.info("ui script run saved to %s", directory)
        self._write_run_bundle(directory)

    def bundle_in_progress(self) -> bool:
        """Whether this run's evidence bundle is still being written.

        Read by the unattended-quit helper. **The bundle is the deliverable of an
        overnight run** — one `.tar.gz` holding the transcript, the reports, the
        screenshots, the app log and the rig-check manifest — and it is built on a
        daemon thread, which interpreter shutdown kills mid-archive without a
        word. Quitting while it runs would leave the operator with a truncated
        file or none at all, after a six-hour disc pass.

        Never raises: a quit helper that can throw is a quit helper that can put a
        modal on screen (see `_arm_unattended_quit`).
        """
        thread = self._bundle_thread
        try:
            return thread is not None and thread.is_alive()
        except Exception:  # noqa: BLE001 — never block a quit on our own bug
            return False

    def _write_run_bundle(self, directory: Path) -> None:
        """Fold the whole run into one archive the operator can attach.

        **Why.** The instruction used to be *"upload this folder"*, and a folder
        is not a thing a chat client accepts — so the operator selected files,
        compressed them, and uploaded the result, which is three manual steps the
        software should have done. The maintainer said both halves of this out
        loud on 2026-08-19: *"why make me bundle it into one compressed file?"*
        and, of the screenshots, *"it is a lot"*. Neither is answered by taking
        fewer measurements; both are answered by there being one file.

        Screenshots go in. They are PNGs, admitted under the widened
        `EXTRA_DIR_SUFFIXES` because this directory holds pictures *this program
        took of its own window* — never an album folder, where the images are
        record-label artwork (Critical rule #8).

        Off the GUI thread: the archive includes the app log, routinely megabytes
        with its rotations, plus every screenshot the run took. Best-effort — the
        run is already saved to `directory`, so a failure here costs a
        convenience and never the evidence.
        """
        import threading

        from platterpus import __version__, evidence_bundle
        from platterpus.paths import LOG_PATH

        log_dir = LOG_PATH.parent
        counts = self._report.counts() if hasattr(self._report, "counts") else {}
        stamp = self._report.started_at

        def work() -> None:
            result = evidence_bundle.build_bundle(
                dest_dir=log_dir / "bundles",
                stamp=stamp,
                app_version=__version__,
                outcome="test script run",
                facts={
                    "steps": str(len(self._report.steps)),
                    "results": ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
                    or "(not counted)",
                    "run folder": str(directory),
                },
                log_dir=log_dir,
                extra_dirs={"scriptrun": directory},
            )
            if result.ok and result.path is not None:
                log.info(
                    "SEND THIS ONE FILE: %s (%d file(s) in, %d excluded; no audio)",
                    result.path,
                    len(result.included),
                    len(result.skipped),
                )
            else:
                log.error(
                    "could not bundle the script run (the folder is still "
                    "complete at %s): %s",
                    directory,
                    result.error,
                )

        thread = threading.Thread(target=work, daemon=True, name="uiscript-bundle")
        self._bundle_thread = thread
        thread.start()

    def _ensure_artifact_dir(self) -> Path | None:
        if self._artifact_dir is not None:
            return self._artifact_dir
        from platterpus.paths import LOG_PATH

        stamp = self._report.started_at.replace(":", "").replace("-", "")
        directory = LOG_PATH.parent / "uiscript" / stamp
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log.error("cannot create %s: %r", directory, exc)
            return None
        self._artifact_dir = directory
        self._report.artifact_dir = str(directory)
        return directory


# --- Small helpers, kept module-level so they are testable without a runner ---


def _visible_top_levels() -> list[QWidget]:
    """Every *visible* top-level window, the active one first.

    Order matters: the first grab becomes ``<name>.png``, and the thing a reader
    wants first is whatever currently has focus.
    """
    widgets = [w for w in QApplication.topLevelWidgets() if w.isVisible()]
    active = QApplication.activeWindow()
    if active in widgets:
        widgets.remove(active)
        widgets.insert(0, active)
    return widgets


def _all_top_levels() -> list[QWidget]:
    """Every top-level, **visible or not**, the active one first.

    Deliberately unfiltered. A dialog that was constructed and never shown is the
    single most interesting object in a "nothing happened that I can see"
    investigation, and filtering on ``isVisible()`` would discard exactly the
    evidence that answers it.
    """
    widgets = list(QApplication.topLevelWidgets())
    active = QApplication.activeWindow()
    if active in widgets:
        widgets.remove(active)
        widgets.insert(0, active)
    return widgets


def _window_manifest_line(widget: QWidget) -> str:
    """One window's identity and on-screen status, as a transcript line.

    This is the part that settles whether a dialog reached the screen —
    ``windowHandle()`` is None until Qt creates a platform window, and
    ``isExposed()`` is false while it is mapped but not actually showing. A
    geometry that lies outside every screen is the other real explanation for
    "nothing happened", and it is invisible in a PNG.
    """
    handle = widget.windowHandle()
    geometry = widget.frameGeometry()
    screen = widget.screen()
    on_a_screen = screen is not None and screen.availableGeometry().intersects(geometry)
    return (
        f"  {type(widget).__name__} {widget.windowTitle()!r} "
        f"visible={widget.isVisible()} "
        f"platform_window={'yes' if handle is not None else 'NO (never shown)'} "
        f"exposed={handle.isExposed() if handle is not None else 'n/a'} "
        f"modal={widget.isModal()} "
        f"geom={geometry.x()},{geometry.y()} {geometry.width()}x{geometry.height()} "
        f"on_a_screen={on_a_screen}"
    )


def _release_picker() -> QDialog | None:
    """The MusicBrainz release picker, if it is on screen.

    Matched by class name for the same reason as `_is_the_harness`: importing
    the dialog here would be circular. Unlike `_active_dialog` this looks at
    *every* top level rather than the active one, because the picker can be up
    while a `QMessageBox` sits in front of it.
    """
    for widget in QApplication.topLevelWidgets():
        if type(widget).__name__ == "ReleasePickerDialog" and widget.isVisible():
            return widget if isinstance(widget, QDialog) else None
    return None


def _match_release(releases: list[object], wanted: str) -> int | None:
    """Index of the release `wanted` names, or None.

    Accepts a full MBID, an unambiguous **prefix** of one (so a script can carry
    the readable first block of a UUID), or a 1-based row number. A prefix that
    matches more than one release returns None rather than the first hit —
    guessing here would tag a rip from the wrong release, which is the kind of
    error that survives into an archive.
    """
    if wanted.isdigit():
        row = int(wanted) - 1
        return row if 0 <= row < len(releases) else None
    key = wanted.casefold()
    ids = [str(getattr(r, "mbid", "")).casefold() for r in releases]
    if key in ids:
        return ids.index(key)
    hits = [i for i, mbid in enumerate(ids) if mbid.startswith(key)]
    return hits[0] if len(hits) == 1 else None


#: The two whole-dialog answers `answer-dialog` accepts, and the prefix of its
#: third, named-button form.
ANSWER_DIALOG_ACTIONS: Final[tuple[str, str]] = ("ok", "cancel")
ANSWER_DIALOG_CLICK_PREFIX: Final[str] = "click="


def answer_dialog_action_error(arg: str) -> str | None:
    """``None`` if `arg` is a usable `answer-dialog` first argument, else why not.

    **Split out so the shipped-script gate can check the real vocabulary rather
    than a restatement of it.** ``tests/test_rig_check.py`` runs every script
    under ``rig_scripts/`` through this function, because the script
    *parser* cannot catch a bad value here — arity is all it knows, so
    ``answer-dialog maybe 60 …`` parses perfectly and fails at run time, which on
    a rig script means it fails an hour into a hardware session with a disc in
    the drive. Same reasoning as the `cyanrip` argv sanitiser being shared with
    that gate instead of re-implemented beside it.
    """
    if arg.lower().startswith(ANSWER_DIALOG_CLICK_PREFIX):
        if not arg[len(ANSWER_DIALOG_CLICK_PREFIX) :].strip():
            return (
                f"{ANSWER_DIALOG_CLICK_PREFIX} needs a substring of the button's "
                f"label, e.g. {ANSWER_DIALOG_CLICK_PREFIX}new"
            )
        return None
    if arg.lower() in ANSWER_DIALOG_ACTIONS:
        return None
    return (
        f"the first argument must be "
        f"{' or '.join(repr(a) for a in ANSWER_DIALOG_ACTIONS)} or "
        f"'{ANSWER_DIALOG_CLICK_PREFIX}<substring>', not {arg!r}"
    )


def _plain_label(text: str) -> str:
    """A button's label as a *person* reads it, with Qt's mnemonic markup gone.

    Qt spells a keyboard accelerator with an ampersand — ``&Replace`` underlines
    the R — and a literal ampersand as ``&&``. A script author reads the button
    on screen, not the markup behind it, so ``click=replace`` has to match
    ``&Replace``. Restoring ``&&`` afterwards matters for a label like
    ``Save && Close``: dropping every ampersand blindly would turn it into
    ``Save  Close`` and a substring of ``&`` would then match nothing.
    """
    return text.replace("&&", "\x00").replace("&", "").replace("\x00", "&")


def _dialog_buttons(dialog: QDialog) -> list[QAbstractButton]:
    """Every clickable button in a dialog — message box or hand-built.

    **One sweep, not a special case for QMessageBox.** The first version of this
    branched on ``isinstance(dialog, QMessageBox)`` to use its own ``buttons()``,
    on the stated grounds that a ``findChildren`` sweep would additionally find
    the box's internal "Show Details…" toggle. That reason is **false, and was
    measured false rather than reasoned about**: on PySide6 6.9.1
    ``buttons()`` returns ``['Cancel', 'Replace it', 'Show Details...']`` and the
    sweep returns the same three. The branch distinguished nothing, and the
    revert-proof said so — reverting it left every test passing, which is the
    result worth reporting rather than explaining away.

    So the special case is gone. ``findChildren`` is also the *more* correct of
    the two for the general case, because it recurses: a hand-built dialog can
    nest its buttons inside a layout widget, and ``buttons()`` does not exist
    there at all.
    """
    return [w for w in dialog.findChildren(QAbstractButton)]


def _match_button_label(labels: Sequence[str], needle: str) -> tuple[int | None, str]:
    """Index of the ONE button whose label contains `needle`, or why not.

    Pure — labels in, index out — so the matching rule is testable without a
    live modal on screen, which is the only way to get coverage of the refusal
    branches. ``(None, reason)`` on every refusal, and the reason **names every
    label the dialog actually had**: a bare "no match" leaves the script author
    guessing at the very text they needed to see.

    An ambiguous substring is a **refusal, not a pick**, the same call
    ``uiscript/find_script.py`` makes for two files matching one name. Guessing
    would silently answer a question with the wrong answer, and this verb exists
    precisely because answering the wrong way was indistinguishable from
    answering the right way (see :meth:`Runner._do_answer_dialog`).
    """
    folded = needle.casefold()
    hits = [i for i, label in enumerate(labels) if folded in label.casefold()]
    if not hits:
        if not labels:
            return None, (
                f"nothing matches {needle!r}: the dialog has no buttons at all, "
                f"so only 'ok' or 'cancel' can answer it"
            )
        return None, (
            f"no button matches {needle!r}; this dialog's buttons are "
            f"{', '.join(repr(label) for label in labels)}"
        )
    if len(hits) > 1:
        return None, (
            f"{needle!r} matches {len(hits)} buttons — "
            f"{', '.join(repr(labels[i]) for i in hits)} — and this verb refuses "
            f"to guess which one was meant; lengthen the substring"
        )
    return hits[0], ""


def _click_named_button(dialog: QDialog, needle: str) -> tuple[str | None, str]:
    """Click the one button whose label contains `needle`; return its label.

    Returns ``(None, reason)`` and clicks **nothing** on any refusal, including
    the one a caller would never think of: a button that matched but is
    *disabled*. ``QAbstractButton.click()`` on a disabled button is a no-op that
    raises nothing and returns nothing, so without this check the step would
    record a confident PASS for a dialog still sitting on screen — and the next
    step's failure would be blamed on the next step.
    """
    buttons = _dialog_buttons(dialog)
    labels = [_plain_label(button.text()) for button in buttons]
    index, why = _match_button_label(labels, needle)
    if index is None:
        return None, why
    button = buttons[index]
    if not button.isEnabled():
        return None, (
            f"the button matching {needle!r} is {labels[index]!r}, and it is "
            f"DISABLED — clicking it would have done nothing at all, silently"
        )
    button.click()
    return labels[index], ""


def _is_the_harness(widget: QWidget) -> bool:
    """True for the script console itself — the thing *running* the script.

    Compared by class name rather than by importing `ScriptConsoleDialog`,
    because this module is imported *by* the console: a real import would be
    circular. The name is pinned by a test that instantiates the real class, so
    a rename cannot quietly turn this back into `False` for everything.
    """
    return type(widget).__name__ == "ScriptConsoleDialog"


def _active_dialog() -> QDialog | None:
    """The dialog on top, if any — **excluding the script console itself.**

    Prefers the modal one, because that is the thing blocking the app and
    therefore the thing a script means when it says "cancel".

    **Why the console is excluded** (2026-08-13, found on the rig). The console
    is a `QDialog`, and it is by definition open whenever a script is running, so
    without this it always answered "yes, a dialog is open". Three consequences,
    the first of which shipped:

    * ``expect-dialog none`` could **never pass** — including in
      :data:`~platterpus.ui.dialogs.script_console.STARTER_SCRIPT`, the sample a
      first-time reader is told to press Run on to prove the feature works. It
      has always reported ``FAIL … a dialog is open: 'Run test script'``.
    * ``cancel`` with no application dialog open would have found the console and
      **rejected it**, closing the window hosting the runner's own timer, mid-run.
    * ``expect-dialog`` for a real dialog could match the console's title first.

    The console is the harness, not the application under test. A script that
    says "no dialog is open" plainly means *no dialog of the app's* — nobody
    writes an assertion about the window they are typing into.
    """
    modal = QApplication.activeModalWidget()
    if isinstance(modal, QDialog) and not _is_the_harness(modal):
        return modal
    active = QApplication.activeWindow()
    if isinstance(active, QDialog) and not _is_the_harness(active):
        return active
    for widget in _visible_top_levels():
        if isinstance(widget, QDialog) and not _is_the_harness(widget):
            return widget
    return None


def _panel_fields(window: QWidget) -> dict[str, str]:
    """Whatever the disc panel is currently showing, best-effort.

    Reads through ``getattr`` rather than importing the panel, so a snapshot of a
    window shape this module does not know about degrades to fewer lines instead
    of raising.
    """
    fields: dict[str, str] = {}
    panel = getattr(window, "_disc_info_panel", None)
    if panel is None:
        return fields
    for attr, label in (
        ("_drive_value", "drive"),
        ("_mb_match_value", "musicbrainz"),
        ("_accuraterip_value", "accuraterip"),
        ("_offset_value", "read offset"),
        ("_cache_value", "cache defeat"),
    ):
        widget = getattr(panel, attr, None)
        text = getattr(widget, "text", None)
        if callable(text):
            fields[label] = text()
    return fields


def _pin_role_phrase() -> str:
    """What `PIN_UNDER_REVIEW` *is* right now, in words that are true either way.

    **A thin delegate, deliberately.** The first version of this function
    computed the answer itself — and `fork_source.UNDER_REVIEW_TARGET` carried a
    third copy of the same sentence, hard-coded, which had already gone stale.
    Three surfaces answering *"is a round open?"* with three implementations is
    the shape `CLAUDE.md` names; two of them were wrong within the same hour on
    2026-08-27. So the predicate lives in `fork_source` beside the pins it reads,
    and this exists only so the call site stays readable.

    Imported locally because `fork_source` reaches the network stack for release
    metadata and this module is imported by the script parser, which must not.
    """
    from platterpus.deps import fork_source  # noqa: PLC0415

    return fork_source.pin_under_review_role()


def _bounded_output(text: str) -> str:
    """Head AND tail, with the elision counted.

    A tool's fatal message is the *last* thing it prints, so a head-only cap
    drops precisely the line that explains the failure — and a silent truncation
    reads as completeness (`CLAUDE.md`).
    """
    if len(text) <= MAX_TOOL_OUTPUT_CHARS:
        return text
    half = MAX_TOOL_OUTPUT_CHARS // 2
    dropped = len(text) - 2 * half
    return f"{text[:half]}\n… [{dropped} characters omitted] …\n{text[-half:]}"


def _safe_name(raw: str) -> str:
    """A filename-safe screenshot name. Never empty."""
    cleaned = "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in raw)
    return cleaned.strip("-.") or "screenshot"


def _slug(widget: QWidget) -> str:
    return _safe_name(widget.windowTitle() or type(widget).__name__)[:40]
