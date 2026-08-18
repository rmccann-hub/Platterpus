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

import logging
from dataclasses import dataclass

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from platterpus import diagnostics
from platterpus.deps.host_setup import HostSetup
from platterpus.deps.step_engine import StepResult, StepStatus
from platterpus.ui.accessibility import announce
from platterpus.ui.dialogs.centering import CenteredDialog
from platterpus.ui.failure_text import LOG_POINTER
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
    intro: str = (
        "Platterpus rips through the <b>cyanrip</b> tool, which runs in a "
        "small Linux container so it never touches your system. This sets "
        "that up for you — no terminal needed:\n\n"
        "• installs Distrobox + a container runtime (if missing)\n"
        "• creates the 'ripping' container and installs cyanrip + flac into it\n"
        "• makes the ripping tools available to this app\n\n"
        "Installing system packages may pop up your system password prompt "
        "once. On Bazzite/Silverblue everything's already there, so this is "
        "usually instant. It's safe to re-run."
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
    ) -> None:
        """`host_setup` is injectable for tests; production builds the real
        one (a SubprocessRunner-backed bootstrap).

        ``copy`` swaps the prose for a caller running the same pipeline for a
        different reason — see :class:`SetupCopy`. ``start_immediately`` skips the
        button press, for a run the user has *already* consented to in the dialog
        that opened this one: asking twice is not extra safety, it is a second
        click on the same decision.
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

        self.setWindowTitle(self._copy.title)
        self.resize(580, 460)
        self.setMinimumSize(480, 360)

        root = QVBoxLayout(self)

        self._intro: QLabel = QLabel(self._copy.intro, self)
        self._intro.setWordWrap(True)
        root.addWidget(self._intro)

        self._setup_button: QPushButton = QPushButton(self._copy.action_label, self)
        self._setup_button.clicked.connect(self._on_setup_clicked)
        root.addWidget(self._setup_button)

        # Indeterminate bar — neither distrobox nor dnf reports real progress.
        self._progress: QProgressBar = QProgressBar(self)
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        self._status_label: QLabel = QLabel("", self)
        self._status_label.setWordWrap(True)
        self._status_label.setAccessibleName("Setup status")
        root.addWidget(self._status_label)

        self._results: QPlainTextEdit = QPlainTextEdit("", self)
        self._results.setReadOnly(True)
        self._results.setAccessibleName("Setup step results")
        root.addWidget(self._results, stretch=1)

        self._button_box: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, self
        )
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
        self._status_label.setText("Setting up… this can take a few minutes.")

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
        append_keeping_position(self._results, line)

    def _on_finished(self, results: list[StepResult]) -> None:
        """Render the final summary. Safe to call directly in tests."""
        if self._closing:
            return
        self._progress.setVisible(False)
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
            if ready:
                # Can rip, but not with what we asked for. Both halves, explicitly.
                self._status_label.setText(
                    f"⚠ Setup did NOT fully complete — “{first.title}” failed: "
                    f"{first.detail}\n"
                    "A working ripper is still installed, so you can rip — but not "
                    "with the build this version of Platterpus expects. Re-run setup, "
                    "or send the log if it fails again.\n"
                    # NAME THE FILE. This said "send the log" and named nothing, which
                    # asks the user to find something they have never been told the
                    # location of. One shared sentence (`ui/failure_text`) rather than
                    # a twenty-first hand-written variant.
                    f"{LOG_POINTER}"
                )
            else:
                self._status_label.setText(
                    f"Setup stopped at “{first.title}”: {first.detail}\n{LOG_POINTER}"
                )
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
                f"yet.\n{LOG_POINTER}"
            )
        # Announce the final outcome — the run may have taken minutes (gap #4).
        announce(self._status_label, self._status_label.text())
        self._worker = None
        self._thread = None
        self.setup_finished.emit(ready)

    # --- Lifecycle ----------------------------------------------------------

    def _stop(self) -> None:
        """Cancel the run and stop the thread WITHOUT freezing the window.

        A step in flight (dnf, an image pull) can't be interrupted by quit(), so
        we never block the GUI thread waiting for it: stop_thread cancels, waits
        briefly, and detaches a still-running thread (which finishes its step and
        reaps itself) rather than blocking or destroying it (real-user report:
        closing mid-dnf froze the app, then risked a destroyed-while-running
        abort)."""
        from platterpus.workers import stop_thread

        stop_thread(self._thread, self._worker)
        self._worker = None
        self._thread = None

    def reject(self) -> None:  # noqa: D102 — Qt override (Close / Esc)
        self._closing = True
        self._stop()
        super().reject()

    def closeEvent(self, event: object) -> None:  # noqa: N802 — Qt API
        self._closing = True
        self._stop()
        super().closeEvent(event)  # type: ignore[arg-type]
