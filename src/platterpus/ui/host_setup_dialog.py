"""Host-setup wizard — one-click bootstrap of the host stack from the GUI.

Replaces having to run ``setup-host.sh`` in a terminal (KDD-17, the zero-CLI
goal). The user clicks "Set up"; we run the bootstrap (`deps.host_setup`) off
the GUI thread via :class:`HostSetupWorker`, showing live per-step progress.
Installing *system* packages needs root, so on non-atomic distros a single
graphical polkit prompt appears (via ``pkexec``); on Bazzite/Silverblue the
runtime is preinstalled, so those steps are skipped and nothing is prompted.

The dialog owns the worker thread and tears it down cleanly on close, the same
way DriveSetupDialog does.
"""

from __future__ import annotations

import html
import logging
import math
import time
from dataclasses import dataclass

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from platterpus import diagnostics
from platterpus.deps.host_setup import HostSetup
from platterpus.deps.setup_failure_text import explain_setup_failure
from platterpus.deps.step_engine import StepResult, StepStatus
from platterpus.paths import LOG_PATH
from platterpus.ui.accessibility import announce
from platterpus.ui.dialogs.centering import CenteredDialog
from platterpus.ui.external_open import OpenUrlFn, open_path_externally
from platterpus.ui.plain_text import plain_tooltip
from platterpus.ui.scroll_guards import append_keeping_position
from platterpus.workers import start_worker_thread
from platterpus.workers.host_setup_worker import HostSetupWorker

log = logging.getLogger(__name__)

_STATUS_GLYPH: dict[StepStatus, str] = {
    StepStatus.DONE: "✓",
    StepStatus.RAN: "✓",
    StepStatus.WOULD_RUN: "•",
    StepStatus.FAILED: "✗",
    StepStatus.CANCELLED: "•",
}


@dataclass(frozen=True)
class SetupCopy:
    """The words this dialog wears, so one engine can serve two errands.

    **Why a dataclass and not five keyword arguments.** The ripper *update* runs the
    identical pipeline as first-run setup — the steps are idempotent, so an update is
    a setup where seven of the eight steps report DONE — but it must not say "installs
    Distrobox + a container runtime" to someone who has been ripping for a month.
    Only the prose differs, and `CLAUDE.md` rule #6 is explicit that a second
    installer is not an option: *"no bespoke per-encoder install code"*, and rule #12
    names ``--install-ripper`` driving *"the same step engine as the wizard rather
    than a copied shell snippet"*. A copied dialog would be a copied snippet with a
    layout attached.

    Grouping the strings keeps the constructor honest about what varies (five
    sentences) versus what does not (the engine, the worker, the teardown), and rule
    #10 forbids the untyped-dict shape this would otherwise take.
    """

    title: str = "Set up Platterpus"
    #: MARKUP: the dialog shows it as RichText. Whoever builds a `SetupCopy`
    #: must `html.escape` every value it puts in here, and
    #: tests/test_labels_state_their_text_format.py checks each builder does.
    #: Line breaks are `<br>`, because markup reads a `\n` as a space: until
    #: 2026-10-05 they were `\n`, and the list below showed as one paragraph.
    intro: str = (
        "Platterpus rips through the <b>cyanrip</b> tool, which runs in a "
        "small Linux container so it never touches your system. This sets "
        "that up for you — no terminal needed:<br><br>"
        "• installs Distrobox + a container runtime (if missing)<br>"
        "• creates the 'ripping' container and installs cyanrip + flac into it<br>"
        "• makes the ripping tools available to this app<br><br>"
        # ONE estimate, in the README's own words (*Easiest*, step 3). This
        # said "On Bazzite/Silverblue everything's already there, so this is
        # usually instant": true of Distrobox and Podman only. The container
        # and the ripper build are needed on every system, Bazzite included,
        # and they are the slow part (UX review of 0.7.127, F3). Kept no longer
        # than the sentence it replaced: at 150 % text on a Steam Deck the
        # intro is already the tallest thing in the window
        # (tests/test_ui_conformance.py, clipped_text).
        "It takes a few minutes: it creates the container and builds the "
        "ripper. It may ask for your password once. It's safe to re-run."
    )
    action_label: str = "&Set up"
    rerun_label: str = "Re-run setup"
    #: The headline when the run finished and a ripper is reachable. Named
    #: separately from the failure lines because those must stay identical: a
    #: failure has to read the same however the run was started.
    success: str = (
        "✓ Setup complete — the ripping tools are installed. You can rip now."
    )
    already: str = "✓ Everything was already set up — you're ready to rip."


def ripper_update_copy(pin: str) -> SetupCopy:
    """The words for installing cyanrip build ``pin`` through the setup engine.

    Used by the main window's ripper update (`_begin_ripper_install`). Kept
    beside :class:`SetupCopy` so its markup is built where its contract is
    written, and can be shown, and tested, without a main window.
    """
    return SetupCopy(
        title="Updating cyanrip",
        # Markup (the dialog shows it as RichText): the words, the <b> and the
        # <br> paragraph breaks are ours; the pin names a build the user picked,
        # so it is escaped.
        intro=(
            f"Installing cyanrip build <b>{html.escape(pin)}</b>.<br><br>"
            "Platterpus builds the ripper from source inside its container, "
            "so this takes a few minutes. Everything already in place is "
            "skipped — the rows below say which.<br><br>"
            "The build is verified before anything is installed: if the "
            "binary does not identify as the build we asked for, nothing is "
            "replaced and your current ripper keeps working."
        ),
        action_label="&Install",
        rerun_label="Try again",
        success=(
            "✓ cyanrip updated — the new build is installed and exported. "
            "Your next rip uses it."
        ),
        already="✓ Nothing to do — that build was already installed.",
    )


class HostSetupDialog(CenteredDialog):
    """Modal-ish wizard that bootstraps the host stack (Distrobox + cyanrip)."""

    # Emitted once the run finishes. The payload is REACHABILITY — "is a ripper
    # usable on the host now?" — and deliberately NOT "did every step succeed?".
    # Those are different questions and the difference matters: a run whose fork
    # build failed still leaves a working ripper exported, and the main window's
    # listener wants to refresh the drive list in exactly that case.
    #
    # Spelled out because conflating the two is what produced the "✓ Setup
    # complete" headline over a failed step (see `_on_finished`). The status LABEL
    # must consider the failures; this SIGNAL must not.
    setup_finished = Signal(bool)  # ripper reachable on host — not "no failures"

    def __init__(
        self,
        parent: QWidget | None = None,
        host_setup: HostSetup | None = None,
        copy: SetupCopy | None = None,
        start_immediately: bool = False,
        open_url: OpenUrlFn | None = None,
    ) -> None:
        """`host_setup` is injectable for tests; production builds the real
        one (a SubprocessRunner-backed bootstrap).

        ``copy`` swaps the prose for a caller running the same pipeline for a
        different reason — see :class:`SetupCopy`. ``start_immediately`` skips the
        button press, for a run the user has *already* consented to in the dialog
        that opened this one: asking twice is not extra safety, it is a second
        click on the same decision.

        ``open_url`` is the desktop opener behind **Open log**
        (``QDesktopServices.openUrl`` when None); injected so tests never launch
        a real text editor.
        """
        super().__init__(parent)
        if host_setup is None:
            from platterpus.deps.step_engine import SubprocessRunner

            host_setup = HostSetup(runner=SubprocessRunner())
        self._host: HostSetup = host_setup
        self._copy: SetupCopy = copy or SetupCopy()
        self._thread: QThread | None = None
        self._worker: HostSetupWorker | None = None
        self._closing: bool = False
        self._open_url: OpenUrlFn | None = open_url
        # When the current run started (time.monotonic), for the elapsed-time
        # line; None while no run is in flight.
        self._started_at: float | None = None

        self.setWindowTitle(self._copy.title)
        self.resize(580, 460)
        self.setMinimumSize(480, 360)

        root = QVBoxLayout(self)

        # RichText, stated: `SetupCopy.intro` is markup by contract (the <b>…</b>
        # around the ripper's name is ours), and its builders escape any value
        # they interpolate — the ripper update's build pin. Qt's default AutoText
        # would decide per text, from whatever its first line happened to hold.
        self._intro: QLabel = QLabel(self._copy.intro, self)
        self._intro.setTextFormat(Qt.TextFormat.RichText)
        self._intro.setWordWrap(True)
        root.addWidget(self._intro)

        self._setup_button: QPushButton = QPushButton(self._copy.action_label, self)
        self._setup_button.clicked.connect(self._on_setup_clicked)
        root.addWidget(self._setup_button)

        # Indeterminate bar — neither distrobox nor dnf reports real progress.
        self._progress: QProgressBar = QProgressBar(self)
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        # The bar and the elapsed-time label below share ONE row: a row of its
        # own pushed the ripper-update intro into clipping at 150 % text on a
        # small screen (tests/test_ui_conformance.py, clipped_text).
        progress_row = QHBoxLayout()
        progress_row.addWidget(self._progress, 1)
        root.addLayout(progress_row)

        self._status_label: QLabel = QLabel("", self)
        # PlainText: a step's own words land here (a running step's detail, a
        # failed step's error from the command it ran), and Qt's default AutoText
        # would read a `<` in them as markup.
        self._status_label.setTextFormat(Qt.TextFormat.PlainText)
        self._status_label.setWordWrap(True)
        self._status_label.setAccessibleName("Setup status")
        root.addWidget(self._status_label)

        # How long the run has taken so far. Setup takes minutes and the bar is
        # indeterminate, so a clock that moves is the one honest sign the window
        # is alive between step changes. Ticked by a GUI-thread QTimer once a
        # second; the setup work itself stays on the worker thread. Not
        # announced: a screen reader reading a clock every second is noise.
        self._elapsed_label: QLabel = QLabel("", self)
        self._elapsed_label.setTextFormat(Qt.TextFormat.PlainText)
        self._elapsed_label.setAccessibleName("Setup elapsed time")
        self._elapsed_label.setVisible(False)
        progress_row.addWidget(self._elapsed_label)
        self._elapsed_timer: QTimer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._tick_elapsed)

        # The failed step's OWN words, below the plain sentence that leads. The
        # status line says what happened and what to do; this keeps what the
        # tool actually printed, so nothing captured is dropped (CLAUDE.md:
        # show the user the dependency's own sentence). PlainText, because it
        # is external output; selectable, so it can be copied into a report.
        self._details_label: QLabel = QLabel("", self)
        self._details_label.setTextFormat(Qt.TextFormat.PlainText)
        self._details_label.setWordWrap(True)
        self._details_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._details_label.setAccessibleName("Setup failure details")
        self._details_label.setVisible(False)
        root.addWidget(self._details_label)

        self._results: QPlainTextEdit = QPlainTextEdit("", self)
        self._results.setReadOnly(True)
        self._results.setAccessibleName("Setup step results")
        # Hidden until a step reports, so the wizard does not open on an empty
        # box (UX review of 0.7.127, F4); the stretch below takes its room.
        self._results.setVisible(False)
        root.addWidget(self._results, stretch=1)
        root.addStretch(0)

        self._button_box: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, self
        )
        # Open log: shown once a run has failed. The log path used to be plain
        # text under the failure, which a user had to copy into a file manager.
        self._open_log_button: QPushButton = QPushButton("Open &log", self)
        self._open_log_button.setToolTip(plain_tooltip(str(LOG_PATH)))
        self._open_log_button.clicked.connect(self._on_open_log_clicked)
        self._button_box.addButton(
            self._open_log_button, QDialogButtonBox.ButtonRole.ActionRole
        )
        # Hidden AFTER adding: the button box shows every button it is given.
        self._open_log_button.setVisible(False)
        self._button_box.rejected.connect(self.reject)
        self._button_box.accepted.connect(self.accept)
        root.addWidget(self._button_box)

        if start_immediately:
            # Deferred by one event-loop turn rather than called here. Starting a
            # QThread from inside __init__ means the worker can emit its first
            # `step` before the caller even holds the dialog — and `_on_step`
            # touches widgets this constructor has only just finished building.
            # A zero-delay singleShot costs nothing and removes the ordering
            # question entirely.
            QTimer.singleShot(0, self._on_setup_clicked)

    # --- Run flow -----------------------------------------------------------

    def _on_setup_clicked(self) -> None:
        if self._thread is not None:  # already running
            return
        self._setup_button.setEnabled(False)
        self._results.clear()
        self._progress.setVisible(True)
        self._status_label.setText(
            "Setting up… the first time this takes a few minutes."
        )
        # A re-run starts clean: the last run's failure details no longer
        # describe anything.
        self._details_label.clear()
        self._details_label.setVisible(False)
        self._open_log_button.setVisible(False)
        self._started_at = time.monotonic()
        self._elapsed_label.setText(f"Elapsed: {format_elapsed(0.0)}")
        self._elapsed_label.setVisible(True)
        self._elapsed_timer.start()

        self._worker = HostSetupWorker(self._host)
        self._thread = QThread(self)
        self._worker.step.connect(self._on_step)
        self._worker.finished.connect(self._on_finished)
        start_worker_thread(self._worker, self._thread, self._worker.run)

    def _on_step(self, result: StepResult) -> None:
        """Update progress as steps run/complete. Safe to call in tests.

        A RUNNING ping shows what's happening *now* in the status line (so a
        slow step never looks frozen); terminal results append a ✓/✗ line to
        the log so the user sees what's been done.
        """
        if self._closing:
            return
        if result.status is StepStatus.RUNNING:
            hint = f" — {result.detail}" if result.detail else ""
            step_text = f"⏳ {result.title}{hint}"
            self._status_label.setText(step_text)
            # Steps run for minutes with focus elsewhere — announce each new
            # step start focus-safely (low-frequency, one per step; gap #4).
            announce(self._status_label, step_text)
            return
        glyph = _STATUS_GLYPH.get(result.status, "•")
        line = f"{glyph} {result.title}"
        if result.detail:
            line += f" — {result.detail}"
        # Sticky bottom, not forced bottom: setup runs for minutes and a failing
        # step is exactly when the user scrolls up to read what it said. A plain
        # append would drag them back to the tail on the next step.
        self._results.setVisible(True)
        append_keeping_position(self._results, line)

    def _on_finished(self, results: list[StepResult]) -> None:
        """Render the final summary. Safe to call directly in tests."""
        if self._closing:
            return
        self._progress.setVisible(False)
        self._stop_elapsed(final=True)
        self._setup_button.setEnabled(True)
        self._setup_button.setText(self._copy.rerun_label)
        ready = self._host.is_ready()
        # THE FAILED STEPS DECIDE THE HEADLINE, not `is_ready()` alone.
        #
        # Real-user report (2026-08-04, v0.6.4b1): this dialog said "✓ Setup
        # complete — the ripping tools are installed. You can rip now." while
        # listing, two lines below, "✗ Platterpus fork of cyanrip — installed
        # cyanrip does not identify as the pinned fork build". Both statements were
        # rendered from the same run.
        #
        # `is_ready()` asks *"is a ripper reachable on the host?"* — it is
        # `cyanrip_exported() and flac_exported()`, pure reachability. The PREVIOUS
        # fork build was still exported, so it answered True, and because the
        # verdict never consulted `results`, a FAILED step could not affect it. A
        # check satisfied by the wrong thing: it was asked "did setup succeed?" and
        # it answered a different question correctly.
        #
        # Tri-state, because two of these states are real and different. A user
        # whose fork step failed but who has a working stock/older ripper CAN rip —
        # saying "setup did not complete" would be as wrong as "setup complete". So
        # name both facts in one sentence and let them weigh it.
        failed = [r for r in results if r.status is StepStatus.FAILED]
        # Distinguish "nothing to do" (everything was already present — common
        # on Bazzite, and otherwise looks like the wizard did nothing) from a
        # setup that actually installed things.
        all_already = bool(results) and all(
            r.status is StepStatus.DONE for r in results
        )
        if failed:
            first = failed[0]
            # A PLAIN SENTENCE LEADS; THE TOOL'S OWN WORDS FOLLOW. This printed
            # the raw detail as the headline (`Setup stopped at "Distrobox":
            # command not found: pkexec ([Errno 2] …)`), which named no cause a
            # user could recognise and no next step (UX review of 0.7.127, F3).
            # The mapping is a pure function so each known cause is tested
            # without a window; the raw detail is kept, word for word, below it
            # in `_details_label`, and the log path with it (`ui/failure_text`).
            explained = explain_setup_failure(
                first.step_id,
                first.title,
                first.detail,
                retry_label=self._copy.rerun_label.replace("&", ""),
            )
            log.warning(
                "host setup: step %r failed, shown as cause %s: %s",
                first.step_id,
                explained.cause.value,
                first.detail,
            )
            if ready:
                # Can rip, but not with what we asked for. Both halves, explicitly.
                self._status_label.setText(
                    f"⚠ Setup did NOT fully complete — “{first.title}” failed. "
                    f"{explained.headline}\n"
                    "A working ripper is still installed, so you can rip — but not "
                    "with the build this version of Platterpus expects.\n"
                    f"{explained.action}"
                )
            else:
                self._status_label.setText(
                    f"✗ Setup stopped at “{first.title}”. {explained.headline}\n"
                    f"{explained.action}"
                )
            self._show_failure_details(first.title, explained.raw)
        elif ready and all_already:
            self._status_label.setText(self._copy.already)
        elif ready:
            self._status_label.setText(self._copy.success)
        else:
            # Reached when `ready` is False and NO step is FAILED — empty results, an
            # all-skipped run, or a status the tri-state above does not cover. It said
            # four words, logged nothing, and named nothing: the least diagnosable
            # message in the dialog was the one for the case nobody had thought about.
            # Say what we actually know, and record it.
            log.error(
                "host setup finished with ready=False and no failed step; "
                "%d result(s): %s",
                len(results),
                ", ".join(f"{r.step_id}={r.status.value}" for r in results) or "(none)",
            )
            diagnostics.error(
                "setup.step_failed",
                "setup finished without making the ripper usable, and no single step "
                "reported a failure — so there is no one step to blame",
                detail=(
                    f"{len(results)} step result(s): "
                    + (
                        ", ".join(f"{r.step_id}={r.status.value}" for r in results)
                        or "(none — the pipeline produced no results at all)"
                    )
                ),
                where="ui.host_setup_dialog.HostSetupDialog._on_finished",
            )
            self._status_label.setText(
                "Setup did not complete, and no individual step reported a failure — "
                "so there is nothing specific to point at. The ripper is not usable "
                "yet. Press Open log to see what each step did."
            )
            self._show_failure_details("", "")
        # Announce the final outcome — the run may have taken minutes (gap #4).
        announce(self._status_label, self._status_label.text())
        self._worker = None
        self._thread = None
        self.setup_finished.emit(ready)

    def _show_failure_details(self, title: str, raw: str) -> None:
        """Show the failed step's own words (when it had any) and Open log.

        The log path is no longer written out under the failure: it is behind
        **Open log**, in that button's tooltip, and — on a desktop with nothing
        set up to open a ``.txt`` file — in the dialog `open_path_externally`
        shows instead, which names the full path to copy. Writing it here as
        well cost two lines in a window that is already at its height limit at
        150 % text (tests/test_ui_conformance.py, clipped_text).
        """
        if raw:
            self._details_label.setText(f"What “{title}” reported: {raw}")
            self._details_label.setVisible(True)
        self._open_log_button.setVisible(True)

    def _on_open_log_clicked(self) -> None:
        """Hand the app log to the desktop. Fire-and-forget: ``openUrl`` spawns
        the handler and returns, and a refusal is reported with the path."""
        open_path_externally(
            LOG_PATH, parent=self, open_url=self._open_url, what="log file"
        )

    # --- Elapsed time -------------------------------------------------------

    def _tick_elapsed(self) -> None:
        """Once a second while a run is in flight: refresh the elapsed line."""
        if self._started_at is None or self._closing:
            return
        elapsed = time.monotonic() - self._started_at
        self._elapsed_label.setText(f"Elapsed: {format_elapsed(elapsed)}")

    def _stop_elapsed(self, *, final: bool) -> None:
        """Stop the clock and hide it; ``final`` logs the run's total.

        Hidden rather than left reading "took m:ss": once the bar beside it is
        gone, the label would be a row of its own, and the finished window is
        the one measured at its height limit (tests/test_ui_conformance.py).
        """
        self._elapsed_timer.stop()
        if final and self._started_at is not None:
            took = format_elapsed(time.monotonic() - self._started_at)
            log.info("host setup: the run took %s", took)
        self._elapsed_label.setVisible(False)
        self._started_at = None

    # --- Lifecycle ----------------------------------------------------------

    def _stop(self) -> None:
        """Cancel the run and stop the thread WITHOUT freezing the window.

        A step in flight (dnf, an image pull) can't be interrupted by quit(), so
        we never block the GUI thread waiting for it: stop_thread cancels, waits
        briefly, and ABANDONS a still-running thread, retaining its reference
        (Critical rule #9: Qt has no "detach"), so it finishes its step without
        blocking the window or being destroyed while running (real-user report:
        closing mid-dnf froze the app, then risked a destroyed-while-running
        abort)."""
        from platterpus.workers import stop_thread

        self._stop_elapsed(final=False)
        stop_thread(self._thread, self._worker)
        self._worker = None
        self._thread = None

    def reject(self) -> None:  # Qt override (Close / Esc)
        self._closing = True
        self._stop()
        super().reject()

    def closeEvent(self, event: object) -> None:  # noqa: N802 — Qt API
        self._closing = True
        self._stop()
        super().closeEvent(event)  # type: ignore[arg-type]


def format_elapsed(seconds: float) -> str:
    """``m:ss`` (or ``h:mm:ss`` past an hour) for the elapsed-time line.

    Pure, so the format is tested without a clock. A negative or non-finite value
    (impossible from ``monotonic``, but this must not be what raises) shows as
    ``0:00``.
    """
    if not math.isfinite(seconds) or seconds < 0:
        seconds = 0.0
    whole = int(seconds)
    hours, rest = divmod(whole, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
