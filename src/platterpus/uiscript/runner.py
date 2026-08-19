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
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from platterpus import __version__
from platterpus.uiscript.report import Outcome, RunReport, StepRecord, render
from platterpus.uiscript.script import Step, sanitise_cyanrip_args
from platterpus.uiscript.verbs import OPENABLE

log = logging.getLogger(__name__)

#: Gap between steps. Long enough that Qt repaints and a screenshot shows a
#: settled frame, short enough that a 60-step batch is not a coffee break.
TICK_MS: int = 120

#: Hard ceiling on a single `wait`. A pasted typo of `wait 100000` must not
#: strand an unattended run for a day.
MAX_WAIT_S: float = 600.0

#: Hard ceiling on `wait-for-rip`. A full disc is ~50-70 minutes on this
#: hardware; three hours is generous and still bounded.
MAX_RIP_WAIT_S: float = 3 * 60 * 60

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
    """Every `cyanrip` step the sanitiser will refuse, found before step 1 runs.

    Pure, and it reruns the **real** sanitiser rather than a summary of its
    rules — a second description of what is refused would drift from the guard
    the first time either changed, and the wrong copy is the one the operator
    would be reading.

    Why it exists: a refusal is a run-time outcome, so on a 60-step hardware
    batch the operator learns about it forty minutes in, next to a drive, with
    the disc pass already spent. Every fact needed was in the file before the run
    started. Found while validating the cyanrip fork's returned round-8 script:
    three of their six ripper tests would have been refused, and nothing would
    have said so until each one's turn came round.

    Does **not** filter or reorder the run. The refused steps still execute and
    still record their own failures in place; this only moves the *notice*
    earlier.
    """
    problems: list[str] = []
    for step in steps:
        if step.verb != "cyanrip" or not step.ok:
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
        if step.unsafe and not self._unsafe_allowed:
            self._record(
                step,
                Outcome.BLOCKED,
                "this verb needs the 'allow unsafe script verbs' setting, which is off",
            )
            return
        if step.unsafe:
            self._report.used_unsafe = True
        handler = getattr(self, f"_do_{step.verb.replace('-', '_')}", None)
        if handler is None:
            self._record(step, Outcome.ERROR, f"'{step.verb}' is not implemented yet")
            return
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
        capped = min(seconds, MAX_WAIT_S)
        if capped < seconds:
            # Never a silent clamp: the transcript says the wait was shortened.
            self._record(
                step,
                Outcome.FAIL,
                f"asked for {seconds:.0f}s; the cap is {MAX_WAIT_S:.0f}s",
            )
            return
        self._arm_deadline(step, capped)

    def _do_abort(self, step: Step) -> None:
        self._record(step, Outcome.PASS, step.joined() or "abort")
        reason = step.joined() or f"aborted at line {step.line_no}"
        # Everything after this is recorded as skipped by stop().
        self.stop(reason)

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
        # SANITISE FIRST. This verb is a straight passthrough that bypasses
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
        self._record(
            job.step,
            Outcome.PASS,
            f"argv: {' '.join(job.argv)}\nexit: {code}\n{_bounded_output(output)}",
            elapsed=elapsed,
        )

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

        Spelled `(ripper)` to match the `(track) - (title)` placeholder syntax
        this project already hands cyanrip in `-F`, rather than inventing a
        second convention for the same idea.
        """
        if "(ripper)" not in value:
            return value, ""
        from platterpus.ripper_identity import identify_from_banner

        tag = identify_from_banner(self._last_cyanrip_output).build_tag
        if not tag:
            return value, (
                "(ripper) could not be expanded: no cyanrip build tag has been "
                "captured yet. Put a `cyanrip --version` step before this one — "
                "the placeholder reads that banner. Refusing rather than writing "
                "the literal text, which would give two passes the same album "
                "folder and overwrite the first pass's evidence."
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
        """
        try:
            wanted = int(step.args[0])
        except ValueError:
            self._record(step, Outcome.ERROR, f"{step.args[0]!r} is not a count")
            return
        table = getattr(self._window, "_track_table", None)
        if table is None:
            self._record(step, Outcome.ERROR, "no track table on the window")
            return
        actual = len(table.tracks())
        if actual == wanted:
            self._record(step, Outcome.PASS, f"{actual} track rows, as expected")
        else:
            self._record(
                step, Outcome.FAIL, f"expected {wanted} track rows, found {actual}"
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
        """
        controls = getattr(self._window, "_rip_controls", None)
        if controls is None:
            self._record(step, Outcome.ERROR, "no rip controls on the window")
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
        capped = min(seconds, MAX_RIP_WAIT_S)
        if capped < seconds:
            self._record(
                step,
                Outcome.FAIL,
                f"asked to wait {seconds:.0f}s; the cap is {MAX_RIP_WAIT_S:.0f}s",
            )
            return
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
            self._record(
                step,
                Outcome.FAIL,
                "no rip is running, so there is nothing to wait for — this step "
                "reports the state it found rather than passing on an empty room",
            )
            return
        self._arm_deadline(
            step, capped, lambda: getattr(window, "_rip_worker", None) is None
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

        threading.Thread(target=work, daemon=True).start()

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
