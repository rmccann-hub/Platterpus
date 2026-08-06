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

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from platterpus import __version__
from platterpus.uiscript.report import Outcome, RunReport, StepRecord
from platterpus.uiscript.script import Step
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
        self._report = RunReport(
            started_at=datetime.now(UTC).isoformat(timespec="seconds"),
            app_version=__version__,
            script_source=source,
        )
        log.info(
            "ui script run starting: %d step(s), unsafe verbs %s",
            len(self._steps),
            "ALLOWED" if unsafe_allowed else "refused",
        )
        self._timer.start()

    def stop(self, reason: str = "stopped by the user") -> None:
        """End the run now, marking every unreached step as skipped.

        The remaining steps are recorded rather than dropped: "we never got
        there" and "it passed" must not look the same in the transcript.
        """
        if not self.running:
            return
        self._timer.stop()
        for step in self._steps[self._index :]:
            self._report.steps.append(
                StepRecord(step.line_no, step.source, Outcome.SKIPPED)
            )
        self._report.ended_reason = reason
        log.info("ui script run ended: %s", reason)
        self.finished.emit(self._report)

    # --- The tick ------------------------------------------------------------

    def _tick(self) -> None:
        """Execute at most one step, then return to the event loop.

        Never raises: an exception escaping a timer slot crosses into Qt's C++
        frame, where PySide6's behaviour is version-dependent and at worst
        aborts. Any failure becomes an ERROR record instead.
        """
        try:
            if self._deadline is not None:
                self._service_deadline()
                return
            if self._index >= len(self._steps):
                self._timer.stop()
                log.info("ui script run finished: %s", self._report.counts())
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
        satisfied = self._deadline_predicate is not None and self._deadline_predicate()
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
                    f"still not finished after {elapsed:.0f}s",
                    elapsed=elapsed,
                )
            else:
                self._record(step, Outcome.PASS, elapsed=elapsed)

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


def _active_dialog() -> QDialog | None:
    """The dialog on top, if any.

    Prefers the modal one, because that is the thing blocking the app and
    therefore the thing a script means when it says "cancel".
    """
    modal = QApplication.activeModalWidget()
    if isinstance(modal, QDialog):
        return modal
    active = QApplication.activeWindow()
    if isinstance(active, QDialog):
        return active
    for widget in _visible_top_levels():
        if isinstance(widget, QDialog):
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
        ("_cache_defeat_value", "cache defeat"),
    ):
        widget = getattr(panel, attr, None)
        text = getattr(widget, "text", None)
        if callable(text):
            fields[label] = text()
    return fields


def _safe_name(raw: str) -> str:
    """A filename-safe screenshot name. Never empty."""
    cleaned = "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in raw)
    return cleaned.strip("-.") or "screenshot"


def _slug(widget: QWidget) -> str:
    return _safe_name(widget.windowTitle() or type(widget).__name__)[:40]
