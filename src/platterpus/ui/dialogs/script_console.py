"""Tools → Run test script… — the console that makes the batch runner reachable.

**The gap this closes.** :mod:`platterpus.uiscript` was built to the maintainer's
own specification — *"give me a debug testing option where i can copy and paste
command code into it so i dont need to be present but tests get executed anyway
in my absense"* — and shipped **entirely unwired**: a parser, a vocabulary, a
runner, a transcript renderer and a test file, with no menu item, no dialog and
no CLI flag anywhere in the application. `grep` for the package outside itself
returned nothing. A capability nobody can invoke is not a capability
(``docs/testing.md`` §5.p, the rule this is the second instance of), and the
version that made it *look* delivered is the changelog entry that announced it.

So this file is small on purpose. It adds no behaviour: it is the surface.

**Why it is modeless.** A script drives the main window and opens other dialogs.
An application-modal console would sit in front of the very thing it is meant to
operate, and the ``open`` verb's dialogs would stack behind it. ``show()`` keeps
the app usable and the runner's ``QTimer`` ticks the same either way.

**Why the transcript widget is PlainText.** It carries the ripper's own output
verbatim, and Qt's default ``AutoText`` *interprets* anything that looks like
markup. A cyanrip line containing ``<`` would be swallowed as an unknown tag and
the reader would never learn text went missing — ``CLAUDE.md``'s inbound-seam
rule, applied at the one widget that displays dependency output here.

**Why nothing here blocks.** The one verb that runs a subprocess does it on a
helper thread (:class:`platterpus.uiscript.runner._CyanripJob`); this dialog only
ever appends text in response to a signal. Every button slot is a few
microseconds of work — no ``subprocess``, no network, no ``exec()`` of anything
that does either. That is the recurring trap CLAUDE.md names for dialogs.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from platterpus.ui.dialogs.centering import CenteredDialog
from platterpus.ui.scroll_guards import append_keeping_position
from platterpus.uiscript.report import Outcome, RunReport, StepRecord, render
from platterpus.uiscript.runner import ScriptRunner
from platterpus.uiscript.script import parse
from platterpus.uiscript.verbs import verb_reference

log = logging.getLogger(__name__)

#: Shown in an empty console. A first-time reader should be able to press Run
#: without reading anything else and get a transcript that proves the feature
#: works — which is also the smallest possible smoke test of the wiring.
STARTER_SCRIPT: str = """\
# Lines starting with # are comments. Press Run.
log starting a self-check
snapshot before-anything
open settings
expect-dialog "Settings"
screenshot settings-open
cancel
expect-dialog none
log finished
"""


class ScriptConsoleDialog(CenteredDialog):
    """Paste a batch, run it against the live window, read the transcript."""

    def __init__(
        self,
        window: QWidget,
        *,
        script_path: str = "",
        allow_unsafe: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent or window)
        self.setWindowTitle("Run test script")
        self.setModal(False)
        self.resize(760, 640)

        #: The window the script drives. Held so `Run` can build a runner against
        #: the real main window rather than against this dialog.
        self._target: QWidget = window
        #: Where `Load` and `Save` start, and what the Settings field named.
        self._script_path: str = script_path

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Type or paste a batch of steps and press Run. Each step runs one "
            "at a time against the real window, so a script can open a dialog, "
            "check what is on screen, take a screenshot and dismiss it — the "
            "same actions a person would take, without a person.\n\n"
            "A failing step does NOT stop the batch: it is recorded and the run "
            "continues, because the point is to come back to a complete "
            "transcript.",
            self,
        )
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(intro)

        self._editor: QPlainTextEdit = QPlainTextEdit(self)
        self._editor.setPlainText(STARTER_SCRIPT)
        self._editor.setFont(_mono())
        self._editor.setAccessibleName("Test script")
        layout.addWidget(self._editor, stretch=3)

        # "not built yet" for the reason spelled out at the Settings twin: both
        # verbs are reserved with `implemented=False` and no handler, so this box
        # currently gates nothing. Same class as the `expect-status` gap — a
        # control that advertises a capability it cannot deliver.
        self._unsafe_check: QCheckBox = QCheckBox(
            "Allow the unsafe verbs (eval, call — not built yet) in this run", self
        )
        self._unsafe_check.setChecked(allow_unsafe)
        self._unsafe_check.setToolTip(
            "Off by default, and nothing to allow yet: eval and call are reserved "
            "but not implemented, so a script using either is refused either way. "
            "The vocabulary is otherwise a closed list of named actions with "
            "nothing that can run arbitrary code. A run that used the hatch would "
            "say so at the top of its own transcript."
        )
        layout.addWidget(self._unsafe_check)

        buttons = QHBoxLayout()
        self._run_button: QPushButton = QPushButton("&Run", self)
        self._run_button.setDefault(True)
        self._run_button.clicked.connect(self._on_run)
        buttons.addWidget(self._run_button)

        self._stop_button: QPushButton = QPushButton("&Stop", self)
        self._stop_button.setEnabled(False)
        self._stop_button.clicked.connect(self._on_stop)
        buttons.addWidget(self._stop_button)

        load_button = QPushButton("&Load…", self)
        load_button.clicked.connect(self._on_load)
        buttons.addWidget(load_button)

        save_button = QPushButton("Sa&ve transcript…", self)
        save_button.clicked.connect(self._on_save_transcript)
        buttons.addWidget(save_button)

        help_button = QPushButton("&Commands", self)
        help_button.clicked.connect(self._on_show_reference)
        buttons.addWidget(help_button)

        buttons.addStretch(1)
        close_button = QPushButton("&Close", self)
        close_button.clicked.connect(self.reject)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        transcript_label = QLabel("Transcript", self)
        transcript_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(transcript_label)

        self._transcript: QPlainTextEdit = QPlainTextEdit(self)
        self._transcript.setReadOnly(True)
        self._transcript.setFont(_mono())
        self._transcript.setAccessibleName("Transcript")
        # PLAIN TEXT, deliberately — see the module docstring. This widget shows
        # the ripper's own output and MusicBrainz-sourced titles.
        self._transcript.setPlaceholderText("The run's results appear here.")
        layout.addWidget(self._transcript, stretch=2)

        #: The runner for the current/last run. Recreated per run so a report
        #: from a previous run can never be appended to.
        self._runner: ScriptRunner | None = None

        if script_path:
            # A saved path is a statement of intent: load it, but say so in the
            # transcript rather than silently replacing what the user sees.
            self._load_path(Path(script_path).expanduser(), announce=True)

    # --- Public surface, used by the autorun path ----------------------------

    def run_now(self) -> None:
        """Start the batch that is currently in the editor. Idempotent-ish.

        Public so `--run-script` and the autorun-on-launch path drive the *same*
        code the Run button does. A second description of "how a script starts"
        would be the drift this project keeps naming.
        """
        self._on_run()

    def load_file(self, path: Path) -> bool:
        """Load a script file into the editor. Returns whether it loaded.

        Public because `--run-script` needs it and reaching into `_load_path`
        from `app.py` would make the console's internals part of the CLI's
        contract.

        **The return value is the fix for a run that was lost on the rig**
        (2026-08-13). This used to return ``None``, so `app.py` called
        ``run_now()`` unconditionally — and a path that could not be read left
        the editor holding :data:`STARTER_SCRIPT`, which then ran. The operator
        got a clean-looking transcript, correctly stamped with the app version,
        of a nine-line sample they never asked for. `_load_path` *had* reported
        the failure into the transcript pane; ``_on_run`` clears that pane as its
        first act, so the one sentence explaining what happened was erased about
        120 ms after it was written, by the very call that followed it.
        """
        return self._load_path(path, announce=True)

    def report_autorun_refused(self, path: Path, detail: str = "") -> None:
        """Say, in the transcript and on screen, that no script was run.

        Called by ``--run-script`` when the named file would not load. It has to
        be *both*: the transcript is what the operator reads, and nothing else
        will overwrite it now that the run is refused — but an unattended launch
        may be watched from across the room, so the empty-looking window also
        gets a message box it cannot be mistaken for a finished run.

        ``detail`` is the resolver's own account of what it searched. It is
        passed through verbatim rather than summarised: "not found" is only
        useful next to *where it looked*, and the operator is the one who knows
        which of those directories the file is actually in.
        """
        self._append(
            f"REFUSED TO RUN.\n"
            f"  --run-script named: {path}\n"
            + (f"  {detail}\n" if detail else "")
            + "  Nothing was run. The editor still holds the previous script, and\n"
            "  running it would have produced a transcript of the wrong thing."
        )
        QMessageBox.warning(
            self,
            "Platterpus — no script was run",
            f"--run-script could not open:\n\n{path}\n\n"
            + (f"{detail}\n\n" if detail else "")
            + "Nothing was run.",
        )

    def script_text(self) -> str:
        return self._editor.toPlainText()

    def set_script_text(self, text: str) -> None:
        self._editor.setPlainText(text)

    def transcript_text(self) -> str:
        return self._transcript.toPlainText()

    @property
    def runner(self) -> ScriptRunner | None:
        return self._runner

    # --- Slots ---------------------------------------------------------------

    def _on_run(self) -> None:
        if self._runner is not None and self._runner.running:
            log.info("script console: Run pressed while a run was in progress")
            return
        source = self._editor.toPlainText()
        steps = parse(source)
        # A parse problem is NOT a refusal to run. Bad lines become steps that
        # carry their own error and are reported at their line number; the other
        # lines still run. That is the parser's contract and the console must not
        # second-guess it — a batch left overnight is worth more with 58 of 60
        # steps done than with none.
        bad = [s for s in steps if not s.ok]
        self._transcript.clear()
        self._append(f"{len(steps)} step(s) parsed; {len(bad)} will report an error.")
        runner = ScriptRunner(self._target, parent=self)
        runner.step_recorded.connect(self._on_step)
        runner.finished.connect(self._on_finished)
        self._runner = runner
        self._run_button.setEnabled(False)
        self._stop_button.setEnabled(True)
        runner.start(
            steps,
            unsafe_allowed=self._unsafe_check.isChecked(),
            source=source,
        )

    def _on_stop(self) -> None:
        if self._runner is not None:
            self._runner.stop("stopped from the console")

    def _on_step(self, record: object) -> None:
        # Typed `object` because Qt's queued connections force it; narrowed here
        # rather than trusted (CLAUDE.md typing rule).
        if not isinstance(record, StepRecord):
            log.warning("script console got a non-StepRecord payload: %r", type(record))
            return
        marker = "ok  " if record.outcome is Outcome.PASS else record.outcome.value
        line = f"L{record.line_no:>3} {marker:<8} {record.source}"
        if record.detail:
            line += "\n" + "\n".join(
                f"          {part}" for part in record.detail.splitlines()
            )
        self._append(line)

    def _on_finished(self, report: object) -> None:
        self._run_button.setEnabled(True)
        self._stop_button.setEnabled(False)
        if not isinstance(report, RunReport):
            log.warning("script console got a non-RunReport payload: %r", type(report))
            return
        # The full render, not a summary line: this is the thing the maintainer
        # pastes back, and a verdict without the steps under it is half a report.
        self._transcript.setPlainText(render(report))

    def _on_load(self) -> None:
        start = self._script_path or str(Path.home())
        chosen, _ = QFileDialog.getOpenFileName(
            self,
            "Open a test script",
            start,
            "Scripts (*.txt *.pscript);;All files (*)",
        )
        if chosen:
            self._load_path(Path(chosen), announce=True)

    def _load_path(self, path: Path, *, announce: bool) -> bool:
        """Read a script file into the editor, reporting failure visibly.

        A path that cannot be read is stated in the transcript AND logged AND
        reported to the caller. The alternative — leaving whatever was in the
        editor — is the silent-failure shape: the *next* run looks exactly like a
        successful one, because it is a successful run of the wrong script.
        """
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            log.warning("script console could not read %s: %s", path, exc)
            self._append(f"could not read {path}: {exc}")
            return False
        self._editor.setPlainText(text)
        self._script_path = str(path)
        if announce:
            self._append(f"loaded {path} ({len(text.splitlines())} lines)")
        return True

    def _on_save_transcript(self) -> None:
        text = self._transcript.toPlainText()
        if not text.strip():
            self._append("nothing to save yet — run a script first.")
            return
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Save the transcript", str(Path.home() / "platterpus-transcript.txt")
        )
        if not chosen:
            return
        try:
            Path(chosen).write_text(text, encoding="utf-8")
        except OSError as exc:
            log.warning("script console could not write %s: %s", chosen, exc)
            QMessageBox.warning(self, "Could not save", f"{chosen}\n\n{exc}")
            return
        self._append(f"transcript saved to {chosen}")

    def _on_show_reference(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Script commands")
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(verb_reference())
        box.exec()

    def _append(self, text: str) -> None:
        # Sticky bottom: follow the tail only if we were already at it. Appending
        # unconditionally scrolls to the end, which is right while a run streams
        # past and wrong the moment you scroll up to read a failure — the next
        # step drags you away from the thing you stopped to look at (maintainer,
        # 2026-08-13).
        append_keeping_position(self._transcript, text)

    # --- Teardown ------------------------------------------------------------

    def closeEvent(self, event: object) -> None:  # noqa: N802 — Qt override
        """Stop a run before the window that hosts its timer goes away.

        The runner is parented to this dialog, so closing without stopping would
        destroy a live ``QTimer`` mid-run — and, worse for the person reading the
        result, leave a transcript with no verdict. ``stop()`` also kills any
        ripper call still in flight.
        """
        if self._runner is not None and self._runner.running:
            self._runner.stop("the console was closed")
        super().closeEvent(event)  # type: ignore[arg-type]  # Qt's QCloseEvent, typed loosely at this seam


def _mono() -> QFont:
    """A fixed-pitch font, so a transcript's columns line up when pasted."""
    font = QFont("monospace")
    font.setStyleHint(QFont.StyleHint.TypeWriter)
    return font
