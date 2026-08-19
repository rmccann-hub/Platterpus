"""Application entry point.

Wires the persistent-state layers (config, logging) and the running-app
layers (QApplication, adapters, workers, MainWindow) into the correct
startup order.

Order:
  1. configure_logging() — captures any startup failure
  2. config.load()       — falls back to defaults on first run
  3. QApplication        — required before any QWidget
  4. construct adapters  — WhipperHostExportedImpl, MusicBrainzNgsImpl,
                           MetaflacAdapter, DependencyManager
  5. construct MainWindow
  6. run_dependency_check(show_summary=False) — silent unless missing
  7. window.show() and refresh_drives()
  8. app.exec()
"""

from __future__ import annotations

import argparse
import datetime
import logging
import os
import signal
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, cast

from platterpus import __version__, hard_exit

if TYPE_CHECKING:
    # Type-only. Qt is imported lazily inside the functions that need it, so
    # importing it at module scope purely to annotate a signature would undo that
    # (and `from __future__ import annotations` means these names are never
    # evaluated at runtime).
    from PySide6.QtCore import QCoreApplication, QTimer
    from PySide6.QtWidgets import QWidget

    from platterpus.ui.dialogs.script_console import ScriptConsoleDialog
    from platterpus.ui.main_window import MainWindow
from platterpus.build_info import build_fingerprint

log = logging.getLogger(__name__)


def _prefer_xwayland_on_wayland() -> None:
    """On a Wayland session, ask Qt to run via XWayland (the ``xcb`` platform)
    unless the user already chose a platform.

    Why: on KDE Plasma 6 Wayland, this app's Qt build doesn't repaint a window
    region that was covered and then re-exposed while a rip is running — the
    window goes black until you interact with it (real-user report, 2026-06-27).
    Running through XWayland fixes it (X11's expose/repaint works correctly).

    The value is a FALLBACK LIST — ``xcb;wayland`` — so if the xcb plugin can't
    load (e.g. missing libs) Qt falls straight back to native Wayland. That means
    this can never stop the app from starting; the worst case is the previous
    behaviour. Set ``QT_QPA_PLATFORM`` yourself (e.g. ``wayland``) to override and
    keep native Wayland. Must run BEFORE QApplication is constructed — Qt reads
    the variable then.
    """
    import os

    if os.environ.get("QT_QPA_PLATFORM"):
        return  # respect an explicit user choice
    on_wayland = os.environ.get("XDG_SESSION_TYPE") == "wayland" or bool(
        os.environ.get("WAYLAND_DISPLAY")
    )
    if on_wayland:
        os.environ["QT_QPA_PLATFORM"] = "xcb;wayland"
        log.info(
            "Wayland session detected — preferring XWayland "
            "(QT_QPA_PLATFORM=xcb;wayland) to avoid the Plasma 6 black-window "
            "repaint bug; set QT_QPA_PLATFORM=wayland to force native Wayland."
        )


def _show_fatal_dialog(title: str, exc: BaseException) -> None:
    """Show a last-resort error dialog so a crash is never silent.

    The window otherwise just disappears, leaving the user with nothing
    to report. We surface the exception text plus the log-file path (the
    full traceback is already in the log) so a screenshot is actionable.
    A QApplication must already exist; if the GUI itself is what failed
    to come up, this is best-effort and may no-op.
    """
    try:
        from PySide6.QtCore import QThread
        from PySide6.QtWidgets import QApplication, QMessageBox

        from platterpus.paths import LOG_PATH

        app = QApplication.instance()
        if app is None:
            return
        # Only the GUI thread may touch widgets. An exception escaping a slot that
        # runs on a worker QThread invokes `sys.excepthook` **on that worker thread**
        # (verified by probe), so without this guard the crash handler would build a
        # QMessageBox and enter a nested event loop off the GUI thread — undefined
        # behaviour, and `exec()` may never return, in which case the worker's
        # `finished` never fires and its thread is abandoned at shutdown. A crash
        # handler that is unsafe exactly when it is needed is worse than none, so off
        # the GUI thread we log and return; the traceback is already in the log via
        # the caller (audit, 2026-07-29).
        if QThread.currentThread() is not app.thread():
            # Log the PYTHON thread name, not the QThread object. `logging` formats
            # lazily, so a Qt wrapper handed in as a `%s` arg is formatted whenever a
            # handler gets to it — by which time the C++ object may be destroyed, and
            # `str()` on a dead shiboken wrapper RAISES inside logging. A crash
            # handler whose own log call can throw is not a crash handler. The name is
            # also what a reader actually wants ("post-rip-hash", not an address).
            log.error(
                "fatal error on non-GUI thread %r — logged only, no dialog: %s: %s",
                threading.current_thread().name,
                type(exc).__name__,
                exc,
            )
            return
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle(title)
        box.setText(
            f"Platterpus hit an unexpected error.\n\n{type(exc).__name__}: {exc}"
        )
        box.setDetailedText(
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        )
        box.setInformativeText(f"Details were written to:\n{LOG_PATH}")
        box.exec()
    except Exception:  # noqa: BLE001 — the crash handler must never crash
        log.exception("failed to show the fatal-error dialog")


# How often the signal-relay timer ticks. Qt's event loop is C++ code, so a
# pending Python signal handler is only *run* when the interpreter regains
# control — a process sitting in `app.exec()` would otherwise ignore SIGTERM
# until the next user interaction. A short no-op timer guarantees the handler
# runs promptly. 200 ms is imperceptible to the user and negligible in CPU.
_SIGNAL_POLL_MS: int = 200

# Signals that mean "shut down now": a desktop-session logout or `systemctl`
# stop sends SIGTERM, and Ctrl-C in a terminal sends SIGINT.
_TERMINATION_SIGNALS: tuple[int, ...] = (signal.SIGTERM, signal.SIGINT)


def _install_termination_handlers(
    app: QCoreApplication, window: QWidget
) -> QTimer | None:
    """Make SIGTERM/SIGINT close the window properly instead of killing us dead.

    **The bug this closes.** ``closeEvent`` was the *only* thing that stopped the
    in-container reader. A rip runs as a host wrapper → podman → cyanrip inside
    the container, and podman does not forward signals into the container — so a
    session logout, a ``kill <pid>``, or Ctrl-C during a rip killed the GUI and
    left cyanrip ripping, holding the drive. The drive ignores its own eject
    button while a read holds the device, so the user had **no in-app and no
    hardware** way to stop it. That is the 2026-07-01 real-user bug arriving
    through a third door, found by a rip-path audit.

    **Why a timer, and why the handler does almost nothing.** Two separate
    hazards, both worth naming because each is easy to get wrong:

    * A Python signal handler installed while Qt owns the loop does not run until
      the interpreter next executes bytecode. Without something to yield control,
      SIGTERM would sit pending indefinitely. The timer exists solely to give the
      interpreter that chance — its slot does no work in the common case.
    * A signal handler runs at an arbitrary point between bytecodes, so doing
      real work there (touching widgets, killing subprocesses) is asking for
      re-entrancy bugs. So the handler only records the signal number; the timer
      slot — an ordinary, fully event-loop-safe callback — does the shutdown.

    Returns the timer so the caller can keep a reference (a QTimer whose last
    Python reference is dropped stops firing), or ``None`` when handlers cannot
    be installed. ``signal.signal`` raises :class:`ValueError` off the main
    thread, which is the normal case under a test runner or an embedded
    interpreter; that is not an error and must not stop the app from starting.
    """
    # Written by the signal handler, read by the timer slot. A list because a
    # handler must not rebind a module global under a lock it cannot take; append
    # is atomic enough for a one-shot flag and needs no synchronisation.
    from PySide6.QtCore import QTimer as _QTimer

    pending: list[int] = []

    def _handler(signum: int, _frame: object) -> None:
        # Absolute minimum inside a signal handler: record and return.
        pending.append(signum)

    installed: list[int] = []
    for sig in _TERMINATION_SIGNALS:
        try:
            signal.signal(sig, _handler)
        except (ValueError, OSError) as exc:
            # ValueError: not the main thread (test runners, embedded use).
            # OSError: the platform refuses this signal. Neither is fatal — the
            # app simply keeps the previous behaviour for that one signal.
            log.warning("could not install a handler for signal %s: %s", sig, exc)
            continue
        installed.append(sig)

    if not installed:
        log.warning(
            "no termination-signal handlers installed — a logout or kill during a "
            "rip will not stop the in-container reader"
        )
        return None

    def _drain() -> None:
        if not pending:
            return
        signum = pending[0]
        log.info(
            "received signal %s — closing the window so the rip and the drive are "
            "stopped, then quitting",
            signum,
        )
        # `close()` runs the real `closeEvent`: it cancels every worker, stops the
        # in-container reader within a bounded budget, and frees the drive. Going
        # through it rather than reimplementing the teardown is the whole point —
        # a second copy of shutdown logic is how the two paths drift apart.
        try:
            window.close()
        except Exception:  # noqa: BLE001 — shutdown must not raise into the loop
            log.exception("window.close() during signal shutdown failed; quitting")
        # Quit regardless of whether the close was accepted: the user (or the
        # session) asked us to terminate, and a vetoed close must not turn a
        # logout into a window that refuses to go away.
        app.quit()

    timer = _QTimer(app)
    timer.setInterval(_SIGNAL_POLL_MS)
    timer.timeout.connect(_drain)
    timer.start()
    log.info("termination-signal handlers installed for %s", installed)
    return timer


def _install_excepthook() -> None:
    """Route otherwise-uncaught exceptions (e.g. raised inside a Qt slot
    during the event loop) to the log file and an on-screen dialog,
    instead of letting them print to a stderr the user never sees."""

    def hook(exc_type, exc_value, exc_tb):  # type: ignore[no-untyped-def]
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        log.error("uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
        _show_fatal_dialog("Platterpus — error", exc_value)

    sys.excepthook = hook

    # `sys.excepthook` does NOT cover plain `threading.Thread`s: CPython routes
    # those to `threading.excepthook`, whose default writes to stderr and returns.
    # An AppImage launched from the applications menu has no attached stderr, so
    # every exception from the fire-and-forget post-rip daemon threads went
    # **nowhere** — not the log, not the report, not the screen. The user saw a step
    # silently never complete and filed a bug report with no evidence it ever ran
    # (audit, 2026-07-29). No dialog here: these are worker threads, so showing one
    # would be the wrong-thread hazard `_show_fatal_dialog` now guards against.
    def thread_hook(args: threading.ExceptHookArgs) -> None:
        if issubclass(args.exc_type, SystemExit):
            return  # a thread exiting deliberately is not a crash
        thread_name = getattr(args.thread, "name", "(unknown)")
        # `exc_value` is Optional in the stubs and genuinely can be None during
        # interpreter shutdown; narrow rather than widen the log call's type.
        if args.exc_value is None:
            log.error(
                "uncaught exception on thread %s (no exception object)", thread_name
            )
            return
        log.error(
            "uncaught exception on thread %s",
            thread_name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = thread_hook


#: How long an unattended run may keep the process alive after its batch ends,
#: waiting for post-rip work to settle. Generous — a 14-track transcode plus
#: hashing plus a CTDB round-trip is minutes — and bounded, because a wedged step
#: must not leave a process behind forever. That is the whole point of the timer.
UNATTENDED_QUIT_BUDGET_S: float = 900.0


def _arm_unattended_quit(
    app: QCoreApplication, window: MainWindow, console: ScriptConsoleDialog
) -> QTimer:
    """Quit once an unattended `--run-script` batch is genuinely finished.

    **The defect this closes** (maintainer, 2026-08-19: *"we shouldn't need to
    hard quit these consoles if they are done actually"*). `--run-script` ran the
    batch and then simply left the window open, so the terminal that launched it
    kept a live `python3.12` and Konsole asked *"There is a process running in
    this window. Do you still want to quit?"* on close. On the 2026-08-19 rig the
    process sat idle for **five and a half minutes** after its last step until a
    person closed the dialog. An unattended run that needs an attendant to end it
    is not unattended.

    **Why it is a poll and not a `finished` connection.** The batch ending is NOT
    the work ending. On that same run the script finished at 17:51:15.8 and the
    rip's own evidence bundle sealed at **17:51:18.4** — after the CTDB verdict,
    the FLAC verify and the checksums landed. Quitting on `finished` would have
    truncated exactly the artifact this session spent its time making trustworthy.
    So the gate is the settlement predicate the bundle itself waits on, and the
    quit happens when the *last* of those is done.

    Bounded and loud in both directions: it says why it is quitting, and if the
    budget runs out it says what was still alive rather than leaving silently.
    """
    from PySide6.QtCore import QTimer

    deadline = time.monotonic() + UNATTENDED_QUIT_BUDGET_S
    timer = QTimer(window)  # parented, so the window's teardown owns it
    timer.setInterval(1000)

    def _tick() -> None:
        runner = getattr(console, "runner", None)
        if runner is not None and getattr(runner, "running", False):
            return  # the batch itself is still going
        # The batch is done. Wait for everything it STARTED — the same predicate
        # the evidence bundle is gated on, so the two cannot disagree about what
        # "finished" means.
        settled = True
        try:
            if getattr(window, "_pending_evidence_bundle", None) is not None:
                settled = False
            elif not window._post_rip_work_settled():
                settled = False
        except Exception:  # noqa: BLE001 — a quit helper must never be the crash
            log.exception("could not read post-rip state; quitting anyway")
            settled = True
        if settled:
            timer.stop()
            log.info(
                "unattended run finished and post-rip work has settled — quitting. "
                "Nothing is left running, so the terminal will not ask."
            )
            app.quit()
            return
        if time.monotonic() >= deadline:
            timer.stop()
            still = ""
            try:
                still = window._post_rip_still_running()
            except Exception:  # noqa: BLE001
                pass
            log.warning(
                "unattended run: gave up waiting after %.0fs for post-rip work to "
                "settle (still running: %s) — quitting anyway. Results already "
                "written are complete; anything from those steps is not.",
                UNATTENDED_QUIT_BUDGET_S,
                still or "(unknown)",
            )
            app.quit()

    timer.timeout.connect(_tick)
    timer.start()
    # RETURNED so a caller — in practice a test — can stop it. A test that armed
    # this and walked away left a live 1000 ms QTimer parented to a widget it then
    # only `deleteLater()`d, which is precisely the harness-fidelity violation
    # `CLAUDE.md` forbids: a timer production would own, left running by the
    # harness. Handing it back is cheaper than making the test guess at
    # `findChild`.
    return timer


def rig_session_script() -> Path:
    """Absolute path of the shipped rig-session harness.

    One function, so the CLI, the tests and any future caller all name the same
    file. The script sits beside this module inside the package precisely so this
    resolves identically from a checkout, a pipx install and the AppImage.
    """
    return Path(__file__).resolve().parent / "rig_session.sh"


def _run_rig_session(output_dir: Path) -> int:
    """Run the rig-session harness into ``output_dir`` and return its exit code.

    Deliberately thin. The harness itself is the authority on what a rig session
    does — porting its fourteen steps into Python here would be a second
    description of the same procedure, and the two would disagree the first time
    one changed. What this adds is *reachability*: resolving the script inside
    the package, telling the harness which app binary to interrogate, and
    streaming its output to the terminal.
    """
    import subprocess

    from platterpus import settings_validation

    script = rig_session_script()
    if not script.is_file():
        # A packaging failure, not a user error — say which, and say where we
        # looked, because "it didn't run" with no path is undiagnosable.
        print(f"error: the rig-session harness is missing from this build: {script}")
        return 2
    # The output dir is CLI input and gets the same boundary treatment as every
    # other path flag: `type=Path` constructs, it does not check. A relative dir
    # beginning with "-" would reach the shell script as an option.
    resolved, error = settings_validation.resolve_input_directory(
        "--rig-session output dir", output_dir, must_exist=False
    )
    if resolved is None:
        print(f"error: {error}")
        return 2
    # Which app binary the harness should ask for `--version` and `--doctor`.
    # Inside an AppImage that is the AppImage itself ($APPIMAGE, set by the
    # runtime); otherwise it is whatever launched us. Passing it explicitly beats
    # the harness's own default, which guesses a path in ~/Applications.
    app_binary = os.environ.get("APPIMAGE") or sys.argv[0]
    argv = ["bash", str(script), str(resolved), app_binary]
    log.info("rig session starting: %s", " ".join(argv))
    print(f"Running the rig-session harness into {resolved}")
    print(f"  harness: {script}")
    print(f"  app:     {app_binary}")
    try:
        # Streamed, not captured: a rig session takes minutes and the person
        # running it wants to see it progress. The harness writes every step's
        # artifact to disk anyway, so nothing depends on this terminal output.
        completed = subprocess.run(argv, check=False)  # noqa: S603 — argv list, no shell
    except OSError as exc:
        print(f"error: could not run the harness: {exc}")
        log.exception("rig session could not start")
        return 2
    print(f"\nrig session finished with exit code {completed.returncode}")
    print(f"Send the whole folder: {resolved}")
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    """Process entry point.

    `argv` defaults to `sys.argv[1:]` for normal invocation. Tests pass
    an explicit list (typically `["--version"]` to exercise the parser
    without spinning up the full GUI).
    """
    parser = argparse.ArgumentParser(
        prog="platterpus",
        description="A secure, EAC-style CD ripper for Linux (FLAC, WAV, WavPack, MP3)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"platterpus {__version__} ({build_fingerprint()})",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="open only the uninstaller (used by the Uninstall menu entry)",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="run a first-pass check of the rip environment (no CD needed) "
        "and exit; prints a pass/fail report",
    )
    parser.add_argument(
        "--install-ripper",
        nargs="?",
        const="",
        default=None,
        metavar="COMMIT",
        help="set up the ripping stack from the terminal and exit: the Distrobox "
        "container, cyanrip, and the pinned Platterpus fork of cyanrip built over "
        "it, then re-point the host export at the fork. Idempotent — steps already "
        "satisfied report 'already present'. Same steps the GUI's setup wizard "
        "runs; this is the no-GUI front end for them. Optionally takes a fork "
        "COMMIT to build instead of the pinned one, so a pin that moves mid-round "
        "is reachable without waiting for a Platterpus release",
    )
    parser.add_argument(
        "--run-script",
        metavar="FILE",
        type=Path,
        default=None,
        help="launch the GUI, open the test-script console with FILE loaded, and "
        "run it immediately — the unattended-testing path. The window is real and "
        "on screen (the script drives it), so this needs a display; it is 'no "
        "person needed', not 'no display needed'. Overrides the saved script path "
        "for this launch only",
    )
    parser.add_argument(
        "--rig-session",
        nargs="?",
        const="",
        metavar="OUTPUT-DIR",
        default=None,
        help="run the unattended rig-session harness into OUTPUT-DIR and exit: "
        "app and ripper versions, --doctor, the ripper's own -x and -j (which a "
        "rip never sends), pre-gap screening, --audit-rips, handshake status and "
        "preflight — one artifact per step, never stopping on a failure. Works "
        "from the AppImage, so a hardware session needs no source checkout",
    )
    parser.add_argument(
        "--rig-check",
        metavar="OUTPUT-DIR",
        type=Path,
        default=None,
        help="run Platterpus's half of the cyanrip seam check into OUTPUT-DIR and "
        "exit, appending to the MANIFEST.txt their script writes into the same "
        "directory so the two projects' evidence is ONE upload rather than two "
        "piles. Read-only: nothing rips, re-encodes or writes into the library. "
        "--rig-session runs this for you; the flag exists so their script can too",
    )
    parser.add_argument(
        "--rig-check-album",
        metavar="FOLDER",
        type=Path,
        default=None,
        help="the already-ripped album folder --rig-check should read its log "
        "from. Optional: without it the log-reading checks report SKIP (did not "
        "run) rather than a pass, because a check that quietly found nothing and "
        "a check that quietly did not run look identical in a summary",
    )
    parser.add_argument(
        "--rig-check-device",
        metavar="DEVICE",
        default=None,
        help="the optical device --rig-check should name in its record, e.g. "
        "/dev/sr0. It is recorded, not opened — the drive passes belong to "
        "cyanrip's own script and are deliberately not duplicated here",
    )
    parser.add_argument(
        "--ctdb-calibrate",
        metavar="FOLDER",
        type=Path,
        help="verify an already-ripped album folder against CTDB and sweep the "
        "CRC-offset trims to pin the CTDB-CRC algorithm on real hardware "
        "(KDD-16), then exit; no CD or re-rip needed",
    )
    parser.add_argument(
        "--audit-rips",
        metavar="FOLDER",
        type=Path,
        help="audit every already-ripped album under FOLDER and exit: which "
        "cyanrip built each rip, whether the ripper said it finished, which "
        "disc of a multi-disc set the tags came from, what pre-gap provenance "
        "was observed, and whether the audio files the log claims actually "
        "have bytes in them. Read-only; no CD, no re-rip, nothing modified",
    )
    parser.add_argument(
        "--compare",
        nargs="*",
        metavar="REPORT.json",
        type=Path,
        default=None,
        help="compare two .platterpus.json rip reports of the same disc "
        "track-by-track (which tracks are byte-identical, which differ, and "
        "which rip is the better master), then exit; no CD needed. "
        "WITH NO ARGUMENTS it finds them itself: the newest rip and the best "
        "earlier rip of the same disc — which is what makes a double test rip "
        "one command instead of two pasted paths",
    )
    parser.add_argument(
        "--assemble-best-of",
        nargs=3,
        metavar=("DEST", "A.json", "B.json"),
        type=Path,
        help="assemble a best-of-both master folder DEST by copying, per track, "
        "the better of two rips of the same disc (non-destructive — the source "
        "folders are untouched), then exit",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    # Logging is the first thing — any failure below this line shows up
    # in ~/.local/share/platterpus/log.txt.
    from platterpus.logging_setup import configure_logging, set_debug_logging

    configure_logging()
    # Log OUR OWN argv, not just the version. Critical rule #12 requires the
    # exact argv of every dependency we spawn; the same reasoning applies to the
    # invocation that produced the run, because this program's behaviour changes
    # completely by flag — `--install-ripper` rebuilds and replaces the ripper,
    # `--doctor` touches nothing.
    #
    # Measured cost of not having it (2026-08-14): the rig's installed ripper
    # silently changed from the approved pin to another build. The log showed a
    # second `platterpus … starting` at the exact minute, followed by the whole
    # build-install-export sequence — but not WHICH pin it was asked for, so the
    # question could only be answered from the operator's shell history, which
    # no bug report carries. `--rig-session` already logs its argv (see
    # `rig session starting:` above); the main entry point did not.
    #
    # `argv` is the caller-supplied list in tests and `sys.argv[1:]` in
    # production, so this records what was actually parsed rather than
    # re-reading the process arguments and risking the two disagreeing.
    _invoked = argv if argv is not None else sys.argv[1:]
    log.info(
        "platterpus %s (build %s) starting; args: %s",
        __version__,
        build_fingerprint(),
        " ".join(_invoked) if _invoked else "(none — GUI launch)",
    )

    # Config first; both the logging path and the adapter constructors
    # depend on what the user has configured.
    from platterpus import config as config_module

    cfg = config_module.load()
    # Apply the user's debug-logging preference now that config is loaded
    # (configure_logging ran first, before config, to catch startup failures).
    set_debug_logging(cfg.debug_logging)

    # Doctor mode: a no-GUI, no-disc first-pass test of the rip environment.
    # Runs before QApplication — it's a terminal diagnostic, not a window.
    if args.doctor:
        from platterpus import preflight, settings_validation

        ctx = preflight.default_context(cfg)
        color = sys.stdout.isatty()
        print(
            f"Platterpus {__version__} (build {build_fingerprint()}) preflight "
            f"— backend: {ctx.backend_name}\n"
        )
        # Config values that failed validation were reset to defaults above. Say
        # so *here*, on the terminal: doctor is the no-GUI front end, so a reset
        # that only reached the log file would be the same silent reset the GUI
        # notice exists to prevent (a reset read_offset rips at the wrong offset).
        reset_notice = settings_validation.describe_resets(
            config_module.take_load_resets()
        )
        if reset_notice:
            print(reset_notice + "\n")
        results = preflight.run_preflight(
            ctx, on_result=lambda r: print(preflight.format_line(r, color=color))
        )
        details = preflight.format_details(results)
        if details:
            print("\n" + details)
        print("\n" + preflight.format_summary(results, color=color))
        return preflight.exit_code(results)

    # Install the ripping stack from the terminal. Like --doctor this runs before
    # QApplication — no window, no event loop, so none of the GUI-thread rules
    # apply and the multi-minute dnf/meson/ninja commands can run inline.
    #
    # WHY THIS EXISTS AT ALL, given the wizard does the same thing: the wizard
    # ships *inside* a Platterpus release, so a user on an older build has no
    # in-app route to a newer ripper pin — the very situation a moving fork pin
    # creates every time it moves. This flag is that route, and it reuses the one
    # step engine rather than duplicating the commands (Critical rule #6): a
    # hand-copied shell snippet in the docs would be a second description of the
    # install that drifts the first time the pin or a build dep changes.
    if args.install_ripper is not None:
        from platterpus.deps.fork_source import (
            PRODUCTION_TARGET,
            WIZARD_TARGET,
            ripper_choices,
            same_commit,
            target_for_commit,
        )
        from platterpus.deps.host_setup import HostSetup
        from platterpus.deps.step_engine import StepResult, StepStatus, SubprocessRunner

        # `--install-ripper list` shows the menu instead of installing. A
        # literal, because the flag already takes an optional COMMIT and a
        # separate --list-ripper-builds would be a second surface for one
        # question. "list" is not a valid abbreviated SHA — git requires at
        # least 4 hex characters — so it cannot collide with a real commit.
        if args.install_ripper.strip().lower() == "list":
            print(
                f"Platterpus {__version__} — cyanrip builds this version can install\n"
            )
            for choice in ripper_choices():
                print(f"  {choice.label}")
                print(f"      {choice.why}\n")
            print(
                "Install one with:  --install-ripper <commit>\n"
                "The build tag in brackets is what the binary prints and what\n"
                "--rig-check compares, so it is how a rip is traced to a build later.\n"
                "Any other commit on the fork works too; it reports as unapproved,\n"
                "which is the correct answer for a build no round has verified."
            )
            return 0

        # An operator-supplied commit wins over the pinned one. Resolved HERE, once, so
        # every line below — the banner we print, the build, and the verify — reads the
        # same target; the whole reason `ForkTarget` bundles the pin with the tag it must
        # print is that "build X, verify Y" was once two independent edits.
        target = (
            target_for_commit(args.install_ripper)
            if args.install_ripper
            else WIZARD_TARGET
        )
        # Name the build being installed AND, when it is not the approved one, say so
        # here — before minutes of dnf and meson, not in the rip report afterwards.
        # A test pin is installed on purpose during a session and reports
        # `unapproved` on every rip; the install is the honest place to set that
        # expectation, because a surprise in a rip report reads as a defect.
        print(
            f"Platterpus {__version__} (build {build_fingerprint()}) — installing "
            f"the ripping stack\n"
            f"cyanrip build: {target.pin} — {target.why}\n"
            f"expects banner: {target.expectation}\n"
        )
        # Compare the PIN, not the whole ForkTarget. `target_for_commit` builds a
        # target whose `version` and `why` differ by construction, so `!=` was
        # true even when the operator asked for the approved pin by name — and
        # the note then announced "no round has approved it" while installing the
        # build round 7 approved, contradicting what `--rig-check` reports for
        # the same binary minutes later (measured on the rig, 2026-08-14).
        # Approval is a property of the commit; only the commit may decide it.
        if not same_commit(target.pin, PRODUCTION_TARGET.pin):
            print(
                f"NOTE: this is not the handshake-approved build "
                f"({PRODUCTION_TARGET.pin}). Every rip will report\n"
                f"      'ripper handshake approval: unapproved' — that is correct, "
                f"not a fault: the\n"
                f"      round is open and no round has approved a test pin.\n"
            )
        # A step can take minutes (an image pull, a dnf transaction, a meson
        # build). Print each result as it lands rather than batching at the end,
        # so a long step looks like progress instead of a hang — the terminal
        # equivalent of the wizard's live row updates.
        _MARK: dict[StepStatus, str] = {
            StepStatus.DONE: "  ok  ",
            StepStatus.RAN: " done ",
            StepStatus.FAILED: " FAIL ",
            StepStatus.WOULD_RUN: " plan ",
            StepStatus.CANCELLED: "  --  ",
            StepStatus.RUNNING: "  ..  ",
        }

        def _show(result: StepResult) -> None:
            line = f"[{_MARK[result.status]}] {result.title}"
            if result.detail:
                line += f" — {result.detail}"
            print(line, flush=True)

        setup = HostSetup(runner=SubprocessRunner(), fork_target=target)
        # `step_results`, not `results`: the --doctor block above binds that name
        # to a list of preflight CheckResults, and reusing it here would make the
        # two blocks' types collide for no reader benefit.
        step_results = setup.run(progress=_show)
        # Report against the ripper being usable, not against every step passing:
        # cd-paranoia is optional and deliberately last (KDD-29), so its failure
        # must not read as "the ripper is not installed".
        failed = [r for r in step_results if r.status is StepStatus.FAILED]
        print()
        if setup.is_ready():
            print("Ripping stack is ready. Launch Platterpus and insert a disc.")
            if failed:
                names = ", ".join(r.title for r in failed)
                print(f"Optional step(s) did not complete: {names}")
            return 0
        names = ", ".join(r.title for r in failed) or "unknown"
        print(f"Setup did not complete. Failed step(s): {names}")
        # Every command's argv and its combined output went to the log via
        # SubprocessRunner — say where, so the failure is diagnosable without
        # re-running anything (the diagnostic-completeness rule).
        from platterpus.paths import LOG_PATH

        print(f"The full command output is in the log: {LOG_PATH}")
        return 1

    # Rig-session mode: the unattended hardware-session harness. A terminal
    # diagnostic like --doctor, so it runs before QApplication and exits.
    #
    # The harness is a shell script SHIPPED INSIDE THE PACKAGE, and this flag
    # exists because of where it used to live. It sat in `scripts/`, reachable
    # only from a source checkout — while the person who runs it has an AppImage
    # and the rig sheet told him to run `bash ~/path/to/Platterpus/scripts/…`.
    # A test nobody can start is not a test.
    if args.rig_session is not None:
        # OUTPUT-DIR is optional. Requiring it made the one command a person runs
        # after a rip into a command they have to *compose*, and a directory they
        # invent per session is one they can collide with a previous one. The
        # default is timestamped, so re-running never overwrites the last session's
        # evidence — the same reasoning as giving each rip pass its own album title.
        chosen = str(args.rig_session or "")
        if not chosen:
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            chosen = str(Path.home() / f"platterpus-rig-{stamp}")
            print(f"no output directory given — using {chosen}")
        return _run_rig_session(Path(chosen))

    # Platterpus's half of the cyanrip seam check. A terminal diagnostic like
    # --doctor: no GUI, no disc, read-only. `--rig-session` calls it for us, so an
    # operator still runs one command; the flag exists because the FORK's script
    # calls it too, and both writing into one directory is what makes the two
    # projects' evidence a single upload instead of two piles to reconcile.
    if args.rig_check is not None:
        from platterpus import settings_validation
        from platterpus.rig_check import run_rig_check

        # Validate at the boundary: `type=Path` constructs, it does not check.
        out_dir, error = settings_validation.resolve_input_directory(
            "--rig-check output dir", args.rig_check, must_exist=False
        )
        if out_dir is None:
            print(f"error: {error}")
            return 2
        album: Path | None = None
        if args.rig_check_album is not None:
            # must_exist=True: refuse rather than degrade to SKIP. A folder that
            # was named and is missing is a mistake, and SKIP would report it as
            # an omission — the two are not the same answer.
            album, error = settings_validation.resolve_input_directory(
                "--rig-check-album", args.rig_check_album, must_exist=True
            )
            if album is None:
                print(f"error: {error}")
                return 2
        return run_rig_check(out_dir, album_dir=album, device=args.rig_check_device)

    # CTDB calibrate mode: a no-GUI, no-disc CTDB verify + CRC-trim sweep over an
    # already-ripped folder (KDD-16 hardware validation from the AppImage). Like
    # --doctor, it's a terminal diagnostic that runs before QApplication.
    if args.ctdb_calibrate is not None:
        from platterpus import settings_validation
        from platterpus.ctdb.diagnose import run_diagnostics

        # Validate the CLI path at its boundary: `type=Path` constructs, it does
        # not check. An absent folder used to be reported as "no .flac files
        # found" (wrong subsystem), and a relative folder starting with "-"
        # ("./-x" normalises to "-x") produced "-x/track.flac" argv entries that
        # `flac`/`metaflac` parse as OPTIONS. Resolving makes both impossible.
        folder, error = settings_validation.resolve_input_directory(
            "--ctdb-calibrate folder", args.ctdb_calibrate
        )
        if folder is None:
            print(f"error: {error}")
            return 2
        return run_diagnostics(folder, calibrate_crc=True)

    # Audit a whole library of finished rips. Terminal diagnostic like
    # --doctor: no GUI, no CD, and read-only — it answers the questions the
    # hardware test plan used to ask a human to answer by opening files.
    if args.audit_rips is not None:
        from platterpus import rip_audit, settings_validation

        folder, error = settings_validation.resolve_input_directory(
            "--audit-rips folder", args.audit_rips
        )
        if folder is None:
            print(f"error: {error}")
            return 2
        return rip_audit.run_audit(folder)

    # Compare two rip reports of the same disc (a re-rip vs the previous one).
    # Terminal diagnostic like --doctor: no GUI, no CD.
    if args.compare is not None:
        from platterpus import cli_compare, rip_compare

        if len(args.compare) == 2:
            previous, later = args.compare
            return cli_compare.run_compare(previous, later)
        if args.compare:
            # One path, or three. Refuse with the count rather than silently
            # comparing the wrong things or falling through to discovery — a
            # caller who named files meant those files.
            print(
                f"error: --compare takes two report paths or none (got "
                f"{len(args.compare)}). With no arguments it discovers the "
                "newest rip and the best earlier rip of the same disc."
            )
            return 2
        # Zero arguments: discover. This is the double-test-rip path — rip the
        # disc twice, then ask for the comparison without naming either folder.
        pair = rip_compare.discover_pair_to_compare()
        if not pair.found:
            # Never silent, and never a bare "nothing found": the four causes
            # are genuinely different and the operator acts differently on each.
            print(f"nothing to compare: {pair.reason}")
            return 1
        print(f"comparing (found automatically): {pair.reason}\n")
        assert pair.previous is not None and pair.later is not None
        return cli_compare.run_compare(pair.previous, pair.later)

    # Assemble a best-of-both master folder from two rips of the same disc.
    if args.assemble_best_of is not None:
        from platterpus import cli_compare

        dest, report_a, report_b = args.assemble_best_of
        return cli_compare.run_assemble_best_of(dest, report_a, report_b)

    # QApplication MUST exist before any QWidget. Build it as early as
    # possible so the dep-check dialogs can run.
    from PySide6.QtWidgets import QApplication

    # Prefer XWayland on Wayland (fixes the Plasma 6 black-window repaint bug).
    # Must happen before QApplication reads the platform.
    _prefer_xwayland_on_wayland()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("platterpus")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("platterpus")  # affects QSettings paths
    # The app/window icon (the Platterpus logo). Best-effort: app_icon()
    # returns None if the bundled SVG or the Qt SVG plugin is unavailable, in
    # which case we simply leave the default icon rather than fail startup.
    from platterpus.app_icon import app_icon

    _icon = app_icon()
    if _icon is not None:
        # `QApplication.instance()` is typed as the base QCoreApplication (which
        # has no window-icon concept); the instance we hold is always the concrete
        # QApplication created just above, so the cast is safe.
        cast("QApplication", app).setWindowIcon(_icon)

    # Centre every dialog (incl. QMessageBox / QFileDialog) over the window the
    # user is looking at, so a prompt never opens on a different monitor and
    # looks frozen. Parented to `app` so it lives for the whole session. No-op
    # under native Wayland (clients can't self-position). See auto_center.
    from platterpus.ui.dialogs.auto_center import DialogCenterFilter

    _dialog_center_filter = DialogCenterFilter(app)
    app.installEventFilter(_dialog_center_filter)

    # From here on, any uncaught exception (including ones raised inside a
    # Qt slot during the event loop) goes to the log + an on-screen dialog
    # rather than silently aborting the process.
    _install_excepthook()

    # Uninstaller-only mode: the "Uninstall Platterpus" menu entry launches
    # `<app> --uninstall`, so removal works without opening (or needing) the
    # main window — none of the adapters below are required for it.
    if args.uninstall:
        from platterpus.ui.uninstall_dialog import UninstallDialog

        log.info("uninstall mode requested")
        dialog = UninstallDialog()
        dialog.exec()
        # Same guard as the main exit below. The uninstall dialog's worker runs
        # `podman`/`dnf` steps whose in-flight subprocess cannot be interrupted
        # (its cancel flag is only polled *between* steps, and a step's timeout is
        # 1800 s), so closing mid-teardown reliably abandons a running thread —
        # and this path used to return straight into interpreter shutdown, which
        # then destroyed it. Found by a threading audit, 2026-07-29.
        hard_exit.exit_now_if_threads_abandoned(0)
        return 0

    # Bringing up the adapters + window can fail (bad config path, an
    # unexpected ripper output that trips a parser, a Qt error). Guard the
    # whole bring-up so the user gets a dialog they can screenshot instead
    # of a window that flashes and disappears with nothing to report.
    try:
        # Adapter layer. Per CLAUDE.md Critical Rule #1, every external tool is
        # reached through an adapter constructed exactly once here. The cyanrip
        # backend (the sole engine since the whipper removal, KDD-18) and the
        # MusicBrainz client are built via the shared composition root so the
        # GUI and `--doctor` can never wire the adapters differently.
        from platterpus import composition
        from platterpus.adapters.ctdb_client import CtdbHttpImpl
        from platterpus.adapters.metaflac import MetaflacAdapter
        from platterpus.deps.manager import DependencyManager
        from platterpus.ui.main_window import MainWindow

        backend, _backend_name = composition.build_backend(cfg)
        mb_client = composition.build_musicbrainz_client()
        metaflac = MetaflacAdapter(binary_name=cfg.metaflac_path)

        # CTDB lookup transport (KDD-14 Phase 1) — only used when the user
        # enables "Verify with CTDB after a rip".
        ctdb_client = CtdbHttpImpl()

        dependency_manager = DependencyManager()

        window = MainWindow(
            config=cfg,
            backend=backend,
            mb_client=mb_client,
            metaflac=metaflac,
            dependency_manager=dependency_manager,
            ctdb_client=ctdb_client,
        )

        window.show()
        # The launch dependency check shells out to whipper (which enters the
        # Distrobox container — slow on a cold start), so run it OFF the GUI
        # thread: the window is responsive immediately and the probe can't
        # freeze it. Resolver dialogs for anything missing surface on the GUI
        # thread when the probe finishes. Guarded so a failure still leaves a
        # usable window.
        try:
            window.run_dependency_check_async()
        except Exception:  # noqa: BLE001 — last-resort guard
            log.exception("initial dependency check failed; continuing anyway")
        # Drive listing also shells to whipper; kept after show() so the window
        # appears immediately. (Off-threading this probe too is tracked in TASKS.)
        try:
            window.refresh_drives()
        except Exception:  # noqa: BLE001 — last-resort guard
            log.exception("initial drive refresh failed; continuing anyway")

        # Unattended testing. `--run-script FILE` wins over the saved config,
        # because a flag typed for one launch is a more specific statement of
        # intent than a setting saved weeks ago; the config pair only fires when
        # BOTH a path and the autorun flag were set deliberately.
        #
        # Guarded like the two probes above: a broken script must leave a usable
        # window, not a failed startup. And it goes through the window's own
        # `open_script_console`, so the menu, the flag and the config setting all
        # reach the batch by one route.
        _script = args.run_script
        _autorun = _script is not None or (
            cfg.test_script_autorun and bool(cfg.test_script_path)
        )

        # The automatic cyanrip check — armed HERE, from the launch path, and not
        # from `MainWindow.__init__`. Building a window is not the same event as
        # starting the application, and only the second one licenses interrupting
        # somebody with a dialog. See `MainWindow.schedule_ripper_update_check`.
        #
        # **NOT during a scripted run**, and that is the important half. A script
        # drives the real GUI unattended, for 30–50 minutes on the rig, with nobody
        # watching — so a modal appearing eight seconds in would sit there blocking
        # the batch until a person happened to look, and answering it "yes" would
        # swap the ripper *mid-session*, invalidating the evidence the session
        # exists to produce. Found 2026-08-18 by the suite, which drives this same
        # path: two `cyanrip update` dialogs were left standing over the script
        # console. A harness run is not a person sitting down, which is the same
        # distinction the arming rule above is already about.
        #
        # It runs off-thread, stays silent unless it finds something it can fix in
        # one click, and never blocks the window.
        # Tell the window it is being driven, before the event loop starts. Every
        # launch-time modal reads this at the moment it would appear — see
        # `ProvisioningMixin._maybe_offer_first_run_setup`. Nothing between
        # `MainWindow(...)` above and here spins the event loop, so the deferred
        # first-run offers cannot have fired yet.
        window._unattended = _autorun

        if not _autorun:
            try:
                window.schedule_ripper_update_check()
            except Exception:  # noqa: BLE001 — last-resort guard
                log.exception("could not arm the cyanrip update check; continuing")
        else:
            log.info(
                "not arming the automatic cyanrip check — this launch runs a script"
            )

        if _autorun:
            try:
                console = window.open_script_console(autorun=False)
                # A named file that will not load must STOP the run, not fall
                # through to whatever the editor happens to hold — which is the
                # built-in starter sample on a fresh install. On the rig
                # (2026-08-13) that produced a nine-line transcript stamped with
                # the right app version and reading like a real result, for a
                # script the operator had never seen. `run_now()` clears the
                # transcript pane, so the "could not read" line `load_file` had
                # just written was erased before anyone could read it.
                #
                # The file the operator named IS the run. There is no sensible
                # fallback, so there is no fallback.
                #
                # The path is resolved leniently first: the same artifact is
                # spelled `round08joint.txt` by the cyanrip fork and
                # `round-08-joint.txt` here, and that mismatch is what lost the
                # run. Matching ignores case and separators, which works
                # whichever convention either side picks. It does NOT guess:
                # ambiguity is a refusal, same as absence.
                _resolved: Path | None = None
                _why = ""
                if _script is not None:
                    from platterpus.uiscript.find_script import resolve_script_path

                    _resolved, _why = resolve_script_path(str(_script))
                    log.info("--run-script %s -> %s", _script, _why)
                if _script is not None and (
                    _resolved is None or not console.load_file(_resolved)
                ):
                    log.error(
                        "--run-script %s could not be read; NOT running anything "
                        "else. The console is open with the reason in it.",
                        _script,
                    )
                    console.report_autorun_refused(Path(_script).expanduser(), _why)
                else:
                    log.info(
                        "unattended test script starting (%s)",
                        "--run-script" if _script is not None else "config autorun",
                    )
                    console.run_now()
                    _arm_unattended_quit(app, window, console)
            except Exception:  # noqa: BLE001 — last-resort guard
                log.exception("the unattended test script could not be started")
    except Exception as exc:  # noqa: BLE001 — fatal-startup guard
        log.exception("fatal error during startup")
        _show_fatal_dialog("Platterpus — startup failed", exc)
        return 1

    # A logout, a `kill <pid>` or a Ctrl-C during a rip must stop the
    # in-container reader, which until now only `closeEvent` did. The timer is
    # retained deliberately: a QTimer whose last Python reference is dropped stops
    # firing, and this one is the only thing that lets a pending signal handler
    # run while Qt owns the loop.
    _termination_timer = _install_termination_handlers(app, window)

    status = int(app.exec())
    # Referenced after the loop so no linter or future refactor can decide the
    # assignment above is dead and remove the reference that keeps it alive.
    del _termination_timer
    # If any worker thread had to be abandoned still-running, returning from here
    # would let interpreter shutdown clear `workers._abandoned_threads`, drop the
    # last reference to a live QThread, and abort with SIGABRT (the v0.5.8 crash —
    # see `hard_exit`). In that case leave the process immediately instead, after
    # flushing the log. A clean shutdown is unaffected and unwinds normally.
    hard_exit.exit_now_if_threads_abandoned(status)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
