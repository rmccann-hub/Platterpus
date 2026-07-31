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
import logging
import signal
import sys
import threading
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
        "--ctdb-calibrate",
        metavar="FOLDER",
        type=Path,
        help="verify an already-ripped album folder against CTDB and sweep the "
        "CRC-offset trims to pin the CTDB-CRC algorithm on real hardware "
        "(KDD-16), then exit; no CD or re-rip needed",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("PREVIOUS.json", "LATER.json"),
        type=Path,
        help="compare two .platterpus.json rip reports of the same disc "
        "track-by-track (which tracks are byte-identical, which differ, and "
        "which rip is the better master), then exit; no CD needed",
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
    log.info("platterpus %s (build %s) starting", __version__, build_fingerprint())

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

    # Compare two rip reports of the same disc (a re-rip vs the previous one).
    # Terminal diagnostic like --doctor: no GUI, no CD.
    if args.compare is not None:
        from platterpus import cli_compare

        previous, later = args.compare
        return cli_compare.run_compare(previous, later)

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
