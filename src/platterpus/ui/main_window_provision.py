"""Host provisioning, AppImage integration, and uninstall for the main window.

Extracted from ``main_window`` (2026-06-13 modularization, KDD-19) as a
mixin so the "get the app and its ripping stack installed / updated /
removed" concern lives in one focused file while its methods stay reachable
as ``window._x`` (tests + Qt signal wiring rely on that). ``MainWindow``
inherits this; methods run with ``self`` being the window.

This is the GUI-facing complement to the dependency subsystem's two arms:
``deps/host_setup.py`` (bootstrap) and ``deps/host_teardown.py`` (uninstall),
plus ``appimage_integration.py`` (menu/desktop self-integration). The heavy
imports are loaded lazily inside the methods, so this module stays light and
import-cheap.

Contract this mixin expects from the host window (set in
``MainWindow.__init__``): ``self._config``, ``self._save_config``,
``self._backend``; ``self`` is a ``QWidget`` (dialog parent); and the
cross-mixin methods ``self._maybe_offer_drive_setup`` (DriveMixin),
``self.refresh_drives`` / ``self.run_dependency_check`` (assembler /
DependencyMixin) — all resolved via inheritance at call time.

Future contributors: a new install channel (e.g. a different packaging
format) plugs in at ``_maybe_offer_appimage_integration`` /
``open_host_setup_dialog``; the actual idempotent step engines live in
``deps/`` behind an injectable ``CommandRunner`` (see ``docs/architecture.md``).
"""

from __future__ import annotations

import dataclasses
import logging
import threading
import time
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from platterpus.ui.main_window_shared import MainWindowShared

if TYPE_CHECKING:  # import only for type hints — runtime import stays lazy
    from collections.abc import Callable
    from pathlib import Path

    from PySide6.QtCore import Signal

    from platterpus.config import Config
    from platterpus.deps.host_setup import HostSetup
    from platterpus.sleep_inhibit import SleepInhibitor
    from platterpus.test_session import SessionLayout
    from platterpus.ui.dialogs.script_console import ScriptConsoleDialog
    from platterpus.ui.dialogs.setup_center import (
        SetupCenterDialog as SetupCenterDialogT,
    )
    from platterpus.ui.host_setup_dialog import HostSetupDialog as HostSetupDialogT

log = logging.getLogger(__name__)


class ProvisioningMixin(MainWindowShared):
    """First-run offers, AppImage menu integration, host-setup, and uninstall."""

    #: The modeless test-script console, once opened. Held so the dialog (and the
    #: ``QTimer`` its runner lives on) is not garbage-collected the moment
    #: ``open_script_console`` returns, and so re-opening raises the existing one.
    #: The type is a forward reference: importing the dialog at module scope
    #: would pull the whole scripting package into every main-window import for
    #: a feature most sessions never open.
    _script_console: ScriptConsoleDialog | None = None

    #: The setup/install wizard **that is currently on screen**, or None.
    #:
    #: Doubles as the "is an install running?" flag, and that is the whole point:
    #: `HostSetupDialog` guards its own worker (`if self._thread is not None`),
    #: but that guard is PER DIALOG, so two dialogs are two workers running `git`,
    #: `meson`, `ninja`, `sudo install` and `distrobox-export` against the same
    #: `ripping` container at once. The guard has to live where the dialogs are
    #: created, not inside one of them.
    #:
    #: Declared on the mixin that owns the wizard even though
    #: `_begin_ripper_install` (UpdateMixin) is the other creator — one flag, one
    #: meaning. Two flags would be two answers to "is an install running?".
    _host_setup_dialog: HostSetupDialogT | None = None

    #: The modeless Setup & Updates window, once opened. Held for the same reason
    #: `_script_console` is: `show()` alone would let Qt collect it as soon as the
    #: opening call returns, and re-opening must raise the existing one rather
    #: than stack a second copy of a window whose whole purpose is to be the one
    #: place these answers live.
    _setup_center: SetupCenterDialogT | None = None

    # --- Acceptance-session state ------------------------------------------
    #
    # Declared here as class attributes with `None` defaults, rather than in
    # `MainWindow.__init__`, for the same reason `_script_console` above is: this
    # mixin owns the concern, and a window that never opens the feature should
    # not have to know it exists. They are read on the GUI thread only.

    #: The paths of the acceptance session **that is currently running**, or None.
    #: This doubles as the "is a session armed?" flag, and clearing it is how the
    #: window disarms one — a run that finishes after it has been cleared builds
    #: no bundle (see :meth:`_end_acceptance_session`).
    _acceptance_layout: SessionLayout | None = None
    #: The sleep-inhibitor holding this session's lock. It owns a **child
    #: process**, so every exit path has to release it; see
    #: :meth:`_release_acceptance_inhibitor`.
    _acceptance_inhibitor: SleepInhibitor | None = None
    #: The tri-state sleep-lock verdict, already rendered for a person. Kept
    #: after the layout is cleared so the end-of-session dialog can repeat it —
    #: the operator reads that dialog in the morning, hours after the notice that
    #: appeared when the run started.
    _acceptance_inhibit_note: str = ""
    #: The packaged acceptance script this session runs.
    _acceptance_script: Path | None = None
    #: The run size chosen for this session (Quick, Standard or Full).
    _acceptance_run_size: str = "full"
    #: **The user's own settings, as they were when the session was armed.** The
    #: script writes settings as it tests them, and it used to end by resetting
    #: to the SHIPPED DEFAULTS — its own comment admitted it could do no better,
    #: because "a script that writes a setting never captured the value it
    #: overwrote". The app can: it snapshots here and puts the snapshot back on
    #: every way a session ends. Real-user question that found it, 2026-09-23:
    #: *"should an acceptance run be based on my settings or baked into the
    #: run"* — asked by someone whose Archival Exact goal, beta ripper channel,
    #: debug logging and EAC log would all have been switched off by the run.
    _acceptance_user_config: Config | None = None
    #: The session folder, kept past the end of the session so the "the bundle
    #: could not be written" dialog can still point at the complete workspace.
    _acceptance_root: Path | None = None
    #: The console we connected :attr:`ScriptConsoleDialog.run_finished` on, so a
    #: second session against the same console does not connect the slot twice.
    _acceptance_console: ScriptConsoleDialog | None = None
    #: When the session started, as a POSIX timestamp. It decides which rip
    #: folders belong to THIS session rather than to the library it wrote into —
    #: read off the disk at the end rather than remembered as rips finish,
    #: because a run that crashes or is cancelled still leaves finished rips and
    #: those are the ones somebody needs to send.
    _acceptance_started_at: float = 0.0
    #: The daemon that packs the bundle. Retained so a test can join it; nothing
    #: in production waits on it (it is fire-and-forget by design — see
    #: :meth:`_launch_acceptance_bundle`).
    _acceptance_bundle_thread: threading.Thread | None = None
    #: The run's own outcome, rendered for a person by
    #: :meth:`_acceptance_run_headline`. Kept on the window because the run ends
    #: and the *bundle* ends at two different moments, and the closing dialog —
    #: the one thing the operator reads in the morning — is raised at the second
    #: one. Empty means "no run has finished in this window yet", which the
    #: dialog reports as *not determined* rather than as a pass.
    _acceptance_run_verdict: str = ""

    # --- Signals the concrete MainWindow declares --------------------------
    #
    # Bare annotations: they create no attribute at runtime, they exist so mypy
    # can resolve `self.<signal>.emit(...)` from inside this mixin. The real
    # `Signal(object)` objects are class attributes of `MainWindow`, because a
    # PySide6 signal must be declared in a QObject subclass body and at runtime
    # this mixin's base is a plain `object`.
    acceptance_inhibitor_done: Signal  # sleep_inhibit.InhibitOutcome
    acceptance_bundle_done: Signal  # evidence_bundle.BundleResult

    def _maybe_offer_first_run_setup(self) -> None:
        """First-run offers, in dependency order.

        The host stack (whipper in its container) must exist before anything
        else works, so offer that first; only once whipper is present does the
        drive-calibration offer make sense. Deferred to the event loop, so in
        tests (no exec loop) neither fires — both are unit-tested directly.

        **Nothing here fires on an unattended launch (0.6.17).** A script drives
        the real GUI with nobody watching, so a spontaneous modal sits there
        until a person happens to look — and any answer it gets is an answer
        nobody gave. On the rig (2026-08-18) the AppImage's *"Add to your
        applications menu?"* offer opened four seconds into a scripted run,
        failed the step that was mid-flight, and was then swept up by the
        script's next click — which relocated the running AppImage out of
        `~/Downloads` while the batch was using it.

        `app.py` already refused to arm the automatic cyanrip check for exactly
        this reason, and the reasoning it wrote down is about *any* launch-time
        modal, not that one dialog — so it belongs at the gate they all share.
        Enforcing a rule only at the place it was learned is how the last one
        was missed (`docs/testing.md` §5.o).

        The check is HERE, not at the `singleShot` that schedules this, because
        the flag is set after the window is built: read a precondition where the
        thing happens, never where it was queued (`CLAUDE.md`).
        """
        if self._unattended:
            log.info(
                "not making the first-run offers — this launch is running a "
                "script, so there is nobody to answer them"
            )
            return
        # Anything the config load had to throw away comes first: it tells the
        # user their settings are not what the file says, which changes how they
        # read every offer below it (a reset read_offset in particular).
        self._show_config_reset_notice()
        # AppImage menu integration is independent of the host/drive state —
        # offer it first (it's a no-op on source/pipx installs and when already
        # integrated), so a double-clicked AppImage becomes a real menu app.
        self._maybe_offer_appimage_integration()
        if not self._host_stack_ready():
            self._maybe_offer_host_setup()
            return
        self._maybe_offer_drive_setup()

    def _show_config_reset_notice(self) -> None:
        """Tell the user, on screen, which settings the config load had to reset.

        ``config.load()`` resets any value that fails validation to its default so
        an invalid value can never reach the ripper. That part is right; doing it
        with **only a log line** was the "silent reset" the *validate every input*
        convention explicitly forbids, and the dangerous instance is concrete: a
        hand-edited ``read_offset`` outside its bounds becomes ``0`` while
        ``override_read_offset`` stays on, so the next disc is ripped at the wrong
        offset with nothing on screen to say so. (``main_window_drive.
        _set_read_offset_override`` already named this hazard; it was closed on the
        write path only — audit, 2026-07-31.)

        The message text comes from ``settings_validation.describe_resets`` — a
        pure function — so it is asserted in tests without a dialog. Runs from the
        deferred first-run hook, so it appears over a window that is already up,
        and never fires in tests (no event loop).
        """
        from platterpus import config as config_module
        from platterpus import settings_validation

        resets = config_module.take_load_resets()
        if not resets:
            return
        QMessageBox.warning(
            self,
            "Some settings were reset",
            settings_validation.describe_resets(resets),
        )

    def _on_add_app_shortcut(self) -> None:
        """Tools → Setup & Updates… → Add app shortcut: (re)create the menu entry + desktop icon.

        Always available, so a user who dismissed the first-run offer (or whose
        menu cache went stale) can redo it. Only meaningful for the AppImage —
        source/pipx installs get their launcher from dev-setup.sh.
        """
        from platterpus import appimage_integration as ai

        appimage = ai.appimage_path()
        if appimage is None:
            QMessageBox.information(
                self,
                "Add app shortcut",
                "This adds a menu/desktop shortcut for the AppImage. You're not "
                "running the AppImage build, so there's nothing to add — a source "
                "or pipx install already provides a launcher.",
            )
            return
        try:
            # Same flow as the first-run offer: settle the file into
            # ~/Applications first so the shortcuts never point into
            # Downloads, then integrate from there.
            new_path = ai.relocate_to_applications(appimage)
            ai.integrate(new_path)
            self._config.appimage_integration_prompted = True
            self._save_config(self._config)
            moved = (
                f"The app file was moved to {new_path}. "
                if new_path != appimage
                else ""
            )
            QMessageBox.information(
                self,
                "Shortcut added",
                f"Added Platterpus to your applications menu and your Desktop. "
                f"{moved}"
                "If the Desktop icon shows as untrusted, right-click it and "
                "choose “Allow Launching” (GNOME).",
            )
        except Exception:  # noqa: BLE001 — convenience action
            log.exception("manual AppImage integration failed")
            QMessageBox.warning(
                self,
                "Couldn't add shortcut",
                "Adding the shortcut didn't work, but the app still runs from "
                "the AppImage file.",
            )

    def _maybe_offer_appimage_integration(self) -> None:
        """Offer to add a menu entry + move the file to ~/Applications.

        Re-offers for any AppImage that isn't integrated yet — so a freshly
        downloaded UPDATE (a new file, or shortcuts the user deleted) gets
        the offer again (real-user report, 2026-06-10). Declining is
        remembered per-file, so saying No silences the nag for this file
        only, not for every future version.
        """
        from platterpus import appimage_integration as ai

        appimage = ai.appimage_path()
        if appimage is None:  # not running from an AppImage — nothing to do
            return
        # "Integrated" alone isn't enough: an update saved over the path an
        # old menu entry pointed at matches the entry but still lives in
        # Downloads — offer anyway so it gets settled into ~/Applications
        # (real-user report, 2026-06-10).
        if ai.is_integrated(appimage) and ai.is_settled(appimage):
            return
        # **The pair, and BOTH halves must match to stay silent.** Keying on the
        # path alone silenced this offer forever for anyone who updates in place:
        # `update_install` writes the canonical name into `~/Applications` and
        # replaces it, so the path is byte-identical across every update, and one
        # "No" was permanent (real-user report, 2026-09-18 — the same reporter,
        # and the same symptom, as the boolean this key replaced in June).
        # Including the version means a decline lasts exactly one release.
        from platterpus import __version__  # noqa: PLC0415

        if (
            self._config.integration_declined_path == str(appimage)
            and self._config.integration_declined_version == __version__
        ):
            return  # said No to this file at this version — don't nag until the next
        choice = QMessageBox.question(
            self,
            "Add to your applications menu?",
            "Add Platterpus to your applications menu, and move this file "
            "to ~/Applications so it lives with your other apps?\n\n"
            "(Leaving it in Downloads is fragile — clearing that folder "
            "would remove the app.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if choice != QMessageBox.StandardButton.Yes:
            self._config.integration_declined_path = str(appimage)
            self._config.integration_declined_version = __version__
            self._config.appimage_integration_prompted = True  # legacy flag
            self._save_config(self._config)
            return
        try:
            # Give the file a proper home FIRST, then point the menu entry at
            # it. The running session keeps working from the old mount; only
            # future launches (the menu entry) use the new location.
            new_path = ai.relocate_to_applications(appimage)
            ai.integrate(new_path)
            self._config.integration_declined_path = ""
            self._config.integration_declined_version = ""
            self._config.appimage_integration_prompted = True  # legacy flag
            self._save_config(self._config)
            if new_path != appimage:
                detail = (
                    f"Platterpus now lives at {new_path} and is in your "
                    "applications menu. Launch it from the menu from now on."
                )
            else:
                detail = "Platterpus is now in your applications menu."
            QMessageBox.information(self, "Added to menu", detail)
        except Exception:  # noqa: BLE001 — integration is a convenience
            log.exception("AppImage integration failed")
            QMessageBox.warning(
                self,
                "Couldn't add to menu",
                "Adding the menu entry didn't work, but the app still runs "
                "normally from this file.",
            )

    def _host_stack_ready(self) -> bool:
        """True if cyanrip is reachable from the host (setup done, or native).

        Delegates to the dependency subsystem's ``cyanrip_on_host`` rather than
        re-checking inline: that keeps dependency-presence logic in one place
        (Critical Rule #6) AND it also counts a PATH-native cyanrip — the inline
        ``CYANRIP_BINARY_DEFAULT.exists()`` missed that, so a user who installed
        cyanrip natively (no exported wrapper) was still nagged to run host setup
        (#36)."""
        from platterpus.deps.host_setup import cyanrip_on_host

        return cyanrip_on_host()

    def _maybe_offer_host_setup(self) -> None:
        """One-time, dismissible offer to run the host-setup wizard."""
        if self._config.host_setup_prompted:
            return
        self._config.host_setup_prompted = True
        self._save_config(self._config)
        choice = QMessageBox.question(
            self,
            "Set up Platterpus",
            "Platterpus needs a one-time setup to install its ripping tool "
            "(cyanrip) in a small container — no terminal required. Set it up "
            "now?\n\nYou can also do this later from Tools → Setup & Updates… → Run setup….",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if choice == QMessageBox.StandardButton.Yes:
            self.open_host_setup_dialog()

    def _build_host_setup(self) -> HostSetup:
        """The HostSetup the wizard runs.

        Installs cyanrip — the sole ripping backend (KDD-18) — from its COPR
        (Fedora doesn't package it), plus flac and metaflac, into the `ripping`
        container and exports them to ~/.local/bin. One setup, no terminal.
        """
        from platterpus.deps.host_setup import HostSetup
        from platterpus.deps.step_engine import SubprocessRunner

        return HostSetup(runner=SubprocessRunner())

    def run_setup_wizard(self, build: Callable[[], HostSetupDialogT]) -> None:
        """Run ``build()``'s wizard as **the** install, or refuse and raise the open one.

        THE chokepoint for every `HostSetupDialog` this window shows. Both creators
        — `open_host_setup_dialog` here and `_begin_ripper_install` in UpdateMixin —
        go through it, because they install the same thing into the same container
        and "is an install running?" must have one answer. A second copy of this
        check is a second thing to drift (`CLAUDE.md`: one predicate, N callers).

        **Why `exec()` is not already the guard.** It blocks *clicks*, so this
        cannot be reached by a second menu selection — and that is exactly why it
        went unnoticed. It does not block a **queued slot**, which Qt delivers on
        the GUI thread inside whatever nested loop is spinning. Three launch-time
        surfaces raise modals and only the cyanrip check asked whether something
        else had the floor; `_interruption_blocker`'s own docstring predicted this
        failure — *"answering both runs the install pipeline twice"* — for that one
        surface and was never applied to the others. `docs/testing.md` §5.o.

        The sequence, on a machine with no cyanrip, which is every fresh install:
        `app.py` arms the off-thread dependency probe; `singleShot(0)` opens
        *"Set up Platterpus?"*; the probe finishes inside that nested loop and
        `_resolve_missing_unified` opens the wizard for its container tools; the
        user then answers Yes to the question still underneath and opens a second.
        Two wizards, two workers, one container — the double dialog and the failed
        install are the same defect.

        Refusing RAISES rather than silently dropping, the same choice
        `open_script_console` makes below: the user asked for a setup window and
        there is one, so put it in front of them.
        """
        existing = self._host_setup_dialog
        if existing is not None:
            log.info(
                "a setup/install wizard is already open — raising it instead of "
                "starting a second install into the same container"
            )
            existing.raise_()
            existing.activateWindow()
            return
        dialog = build()
        self._host_setup_dialog = dialog
        try:
            dialog.exec()
        finally:
            # `finally`, not after `exec()`: the dialog runs a nested event loop, so
            # anything delivered into it can raise — and a flag left set would make
            # the wizard permanently unopenable, turning a double-install bug into a
            # dead menu item. Fail toward the state the user can recover from.
            self._host_setup_dialog = None

    def open_host_setup_dialog(self) -> None:
        """Open the host-setup wizard (Tools → Setup & Updates… → Run setup…)."""
        from platterpus.ui.host_setup_dialog import HostSetupDialog

        def build() -> HostSetupDialogT:
            dialog = HostSetupDialog(self, host_setup=self._build_host_setup())
            dialog.setup_finished.connect(self._on_host_setup_finished)
            return dialog

        self.run_setup_wizard(build)

    def open_setup_center(self) -> SetupCenterDialogT:
        """Open Tools → Setup & Updates… — one window for six old menu items.

        **Modeless, and re-opening raises rather than stacks.** Its buttons open
        modal dialogs, so this window must not be modal itself: an `exec()` here
        would nest every one of them inside this window's event loop, which is the
        stacking `run_setup_wizard` exists to stop. Same shape as
        `open_script_console` below, for the same two reasons.

        The dialog is handed callables rather than the window, so what it may do
        is visible here in one list instead of being discoverable only by reading
        the dialog. Everything it calls already existed — this method adds a
        place, not a behaviour.
        """
        from platterpus.ui.dialogs.setup_center import SetupCenterDialog

        existing = self._setup_center
        if existing is not None and existing.isVisible():
            existing.raise_()
            existing.activateWindow()
            return existing

        from platterpus import __version__
        from platterpus.deps import fork_source
        from platterpus.handshake_approval import APPROVED_BY_ROUND

        dialog = SetupCenterDialog(
            self,
            app_version=__version__,
            ripper_pin=fork_source.FORK_PIN,
            ripper_version=fork_source.FORK_EXPECTED_VERSION,
            approved_by_round=APPROVED_BY_ROUND,
            dependency_report=getattr(self, "_last_dependency_report", None),
            actions={
                "app_update": self._on_check_updates,
                "ripper_update": self._on_check_ripper_updates,
                "ripper_pick": self._on_pick_ripper_build,
                "dep_check": self._on_check_dependencies,
                "host_setup": self.open_host_setup_dialog,
                "shortcut": self._on_add_app_shortcut,
                "drive_setup": self._on_drive_setup,
                "drive_diagnose": self._show_drive_access_diagnosis,
            },
            config=self._config,
            save_setting=self._save_user_setting,
        )
        self._setup_center = dialog
        dialog.show()
        return dialog

    def open_script_console(self, *, autorun: bool = False) -> ScriptConsoleDialog:
        """Open Tools → Run test script…, the unattended-batch console.

        **Modeless and kept alive by a reference on the window.** A script drives
        *this* window and opens other dialogs, so an ``exec()`` here would sit in
        front of the thing under test. ``show()`` alone would let the dialog be
        garbage-collected the moment this method returns, taking its runner's
        ``QTimer`` with it — so the window holds the reference, and re-opening
        raises the existing console rather than stacking a second one (two
        consoles driving one window is a race with no useful outcome).

        ``autorun`` starts the loaded script immediately. That is how
        ``--run-script`` and the config's ``test_script_autorun`` reach the batch:
        through this one method, not through a second copy of the start logic.

        Returns the console so the CLI path can observe it; the menu ignores it.
        """
        from platterpus.config import load as load_config
        from platterpus.ui.dialogs.script_console import ScriptConsoleDialog

        existing = self._script_console
        if existing is not None and existing.isVisible():
            existing.raise_()
            existing.activateWindow()
            if autorun and not existing.run_now():
                # A refusal here is the likeliest one in the whole feature: the
                # console was already open, so it may well already be running.
                # Logged rather than swallowed — this method's contract is to
                # return the console, so the caller's own check is the console's
                # `runner`, and a silent discard would leave nothing in the log
                # file a bug report carries.
                log.warning(
                    "autorun asked an already-open console to run and it declined "
                    "— a run is most likely still in progress"
                )
            return existing
        cfg = getattr(self, "_config", None) or load_config()
        console = ScriptConsoleDialog(
            self,
            script_path=cfg.test_script_path,
            allow_unsafe=cfg.test_script_allow_unsafe,
            autorun=cfg.test_script_autorun,
            save_setting=self._save_user_setting,
        )
        self._script_console = console
        console.show()
        if autorun and not console.run_now():
            # A freshly-built console cannot be running, so this is close to
            # unreachable — which is precisely why it is logged rather than
            # ignored: if it ever fires, the reason will not be guessable.
            log.warning("autorun did not start a run on a newly-opened console")
        return console

    # ----------------------------------------------------------------------
    # The overnight acceptance session — Tools → Run acceptance test…
    # ----------------------------------------------------------------------
    #
    # **What this replaces, and why it is in the app.** Running an acceptance
    # session used to mean downloading `docs/rig-scripts/platterpusovernight.sh`,
    # typing a command, and then remembering to run `platterpusmorning.sh` in the
    # morning to collect and tar the result. The maintainer's ruling was that this
    # is work handed back: *"make the app make the rig folder and anything else,
    # this was supposed to be a no cli program, not give me commands to use"* and
    # *"i should just be able to run this with an specific script file i can use
    # with the settings window, and run it, not a ton of scripts and shit in bash,
    # make it all verify and do it itself"*.
    #
    # So the menu item does the whole night: resolve the packaged acceptance
    # batch, make the session folder, hold sleep off, run the batch through the
    # console the Run-test-script menu item already opens, and at the end pack
    # ONE file and name it on screen with a button that opens its folder.
    #
    # **Nothing here reimplements any of it.** The sleep lock is
    # `platterpus.sleep_inhibit`, the paths and the packing are
    # `platterpus.test_session`, the archive itself is
    # `platterpus.evidence_bundle`, and the run is the same `ScriptConsoleDialog`
    # + `ScriptRunner` a person drives by hand. This mixin is the wiring.
    #
    # **Two things are off the GUI thread, and both have to be.**
    # `SleepInhibitor.acquire()` runs a real `systemd-inhibit` probe with a 10 s
    # budget, and the bundle gzips an app log measured at 4.4 MB plus its
    # rotations. Each gets a plain daemon thread that closes over PLAIN VALUES and
    # reports back through a queued signal — the pattern
    # `main_window_rip._arm_evidence_bundle` established, for the reasons its
    # docstring gives (a daemon owns no Qt object, so it adds no `closeEvent`
    # teardown obligation, and it must never be joined from the GUI thread).
    #
    # **No modal is ever shown while the batch is running.** A spontaneous dialog
    # over an unattended run is a measured defect in this project (2026-08-18: an
    # AppImage-integration offer opened four seconds into a scripted run, failed
    # the step in flight, and was then swept up by the script's next click). So
    # the sleep-lock verdict — which must be visible, because a silent downgrade
    # is exactly what the shell script refused to do — goes to the log, to the rip
    # pane's live log view, and into the end-of-session dialog and the bundle's
    # own facts. Three surfaces, none of them a dialog racing the script.

    def run_acceptance_session(self, size: str | None = None) -> bool:
        """Run the whole overnight acceptance session. Returns whether it started.

        The first half runs here, on the GUI thread, because it is a handful of
        `stat`/`mkdir` syscalls and because **it must be able to refuse before
        anything else happens**: a session that cannot find its script, or cannot
        create its own workspace, has to stop before the disc spins rather than
        discover it six hours later (`test_session.prepare_session` says the same
        thing at greater length).

        The second half is asynchronous by necessity — see the block comment
        above. The chain is:

            run_acceptance_session
              → (daemon) SleepInhibitor.acquire
              → acceptance_inhibitor_done  → _on_acceptance_inhibitor_ready
              → _start_acceptance_script   → the console runs the batch
              → ScriptConsoleDialog.run_finished → _on_acceptance_run_finished
              → (daemon) test_session.finish_session
              → acceptance_bundle_done     → _on_acceptance_bundle_done

        Returns True when the session was armed. **A False is always accompanied
        by a message on screen** — a menu item that does nothing and says nothing
        is the silent no-op this codebase keeps finding — except when the operator
        cancelled the size choice, which is their own answer on screen.

        ``size`` is the run size (`uiscript/run_sizes.py`). ``None`` asks, in the
        one question this session puts BEFORE anything starts: once the batch is
        going, no modal may appear. Tests pass it explicitly.
        """
        from datetime import UTC, datetime
        from pathlib import Path

        from platterpus.test_session import (
            builtin_acceptance_script,
            plan_session,
            prepare_session,
            session_stamp,
        )

        if self._acceptance_layout is not None:
            self._acceptance_message(
                QMessageBox.Icon.Information,
                "An acceptance run is already going",
                "An acceptance session is already running in this window. Let it "
                "finish, or close the test-script console to stop it.\n\n"
                f"Its session folder is:\n{self._acceptance_root}",
                open_path=self._acceptance_root,
            )
            return False

        # 1. The script. `builtin_acceptance_script` never raises and always
        #    returns a sentence written for a person, whether it found the file or
        #    not — so the refusal below can name the path it looked for. An error
        #    that cannot say where it looked is not a diagnosis.
        # 0. The size, asked first: nothing has been created or held yet, so a
        #    Cancel here leaves nothing to undo.
        from platterpus.uiscript import run_sizes

        chosen = run_sizes.parse_size(size) if size is not None else None
        if size is not None and chosen is None:
            raise ValueError(f"unknown run size {size!r}")
        if chosen is None:
            chosen = self._ask_acceptance_run_size()
            if chosen is None:
                log.info(
                    "acceptance session not started: the size choice was cancelled"
                )
                return False

        script, explanation = builtin_acceptance_script()
        if script is None:
            log.error("acceptance session refused: %s", explanation)
            self._acceptance_message(
                QMessageBox.Icon.Critical,
                "The acceptance test cannot run",
                f"⚠ Nothing was started.\n\n{explanation}",
            )
            return False

        # 2. The paths — every one of them inside ONE session folder, bundle
        #    included (maintainer, 2026-09-24). `plan_session` is pure.
        layout = plan_session(home=Path.home(), stamp=session_stamp(datetime.now(UTC)))
        try:
            prepare_session(layout)
        except OSError as exc:
            log.error("acceptance session could not create %s: %r", layout.root, exc)
            self._acceptance_message(
                QMessageBox.Icon.Critical,
                "The acceptance test cannot run",
                "⚠ Nothing was started — the session folder could not be "
                f"created.\n\n{layout.root}\n\n{type(exc).__name__}: {exc}",
            )
            return False

        self._acceptance_layout = layout
        self._acceptance_root = layout.root
        self._acceptance_started_at = time.time()
        self._acceptance_script = script
        self._acceptance_run_size = chosen
        self._acceptance_user_config = dataclasses.replace(self._config)
        # THE RIPS STAY IN THE SESSION FOLDER TOO, and out of the user's library.
        # After the snapshot above, so the restore puts both settings back on
        # every exit. Not saved to disk here: the user's own values are what
        # config.toml should hold if the app stops before the restore runs.
        self._config = dataclasses.replace(
            self._config, output_dir=str(layout.rips), library_dir=""
        )
        self._rip_controls.set_config(self._config)
        self._acceptance_inhibit_note = ""
        # Cleared per session: a verdict left over from the PREVIOUS run would be
        # stamped on this one's closing dialog, which is the same "every field
        # true, the sentence false" shape this field exists to fix.
        self._acceptance_run_verdict = ""
        log.info(
            "acceptance session %s starting: script=%s folder=%s deliverable=%s",
            layout.stamp,
            script,
            layout.root,
            layout.bundle,
        )
        # 3. The sleep lock, off-thread. The script starts when it answers.
        self._start_acceptance_inhibitor()
        return True

    def _start_acceptance_inhibitor(self) -> None:
        """Take the idle/sleep/lid lock on a daemon thread, then start the batch.

        **Off the GUI thread because `acquire()` says so.** It runs a real
        `systemd-inhibit` over `true` to find out whether the lock can actually be
        taken — "installed" is not "working" — and that probe carries a 10 s
        budget for a sick D-Bus. Ten seconds of a frozen window is not something
        this project ships (`CLAUDE.md`, and `sleep_inhibit`'s own docstring says
        it in as many words).

        The daemon closes over the inhibitor and nothing Qt-shaped, and reports
        through a queued signal. If the window has gone in the meantime the emit
        raises ``RuntimeError`` and we release immediately — a lock nobody can
        hear about is a machine held awake until reboot.
        """
        from platterpus.sleep_inhibit import SleepInhibitor

        inhibitor = SleepInhibitor(why="Platterpus acceptance test session")
        self._acceptance_inhibitor = inhibitor

        def work() -> None:
            # `acquire()` never raises: every failure comes back as a tri-state
            # outcome carrying a sentence, which is the whole point of it.
            outcome = inhibitor.acquire()
            try:
                self.acceptance_inhibitor_done.emit(outcome)
            except RuntimeError:  # the window was destroyed while we probed
                log.warning(
                    "acceptance session: the window went away during the sleep "
                    "probe; releasing the lock rather than leaking it"
                )
                inhibitor.release()

        threading.Thread(
            target=work, daemon=True, name="platterpus-acceptance-inhibit"
        ).start()

    def _on_acceptance_inhibitor_ready(self, outcome: object) -> None:
        """The sleep lock has answered — runs on the GUI thread. Start the batch.

        **The outcome never aborts the run.** `unavailable` and `not_installed`
        are downgrades, not failures: a run that happens and might get suspended
        beats a run that did not happen. What is not acceptable is a downgrade
        nobody was told about, so the tri-state verdict is rendered here and
        carried to three surfaces (see the block comment above this section).
        """
        from platterpus.sleep_inhibit import STATE_HELD, InhibitOutcome

        if self._acceptance_layout is None:
            # The session was abandoned while the probe ran (the window is
            # closing, or the console was shut). Do not start anything, and do
            # not leave the lock held.
            log.info(
                "acceptance session: the sleep lock landed after the session "
                "was ended; releasing it"
            )
            self._release_acceptance_inhibitor()
            return

        # Narrowed rather than trusted — Qt's queued connections hand us `object`.
        # An unrecognised payload is reported as NOT DETERMINED, never as held:
        # tri-state honesty, same as everywhere else in this project.
        if isinstance(outcome, InhibitOutcome):
            marker = "✓" if outcome.state == STATE_HELD else "⚠"
            note = f"{marker} Sleep lock: {outcome.state} ({outcome.what}) — {outcome.detail}"
        else:
            note = (
                "⚠ Sleep lock: not determined — the probe reported a "
                f"{type(outcome).__name__}, which this window cannot read. Treat "
                "this machine as ABLE to suspend part-way through the run."
            )
        self._acceptance_inhibit_note = note
        log.info("acceptance session: %s", note)
        self._show_acceptance_notice(note)
        self._start_acceptance_script()

    def _show_acceptance_notice(self, text: str) -> None:
        """Put one line where the operator is already looking. Never a dialog.

        The rip pane's live log view is on screen, is not a `QDialog`, and so
        cannot be found by the script's own `expect-dialog` checks or closed by
        its `cancel` verb — which a message box would be, and which is the
        2026-08-18 defect this avoids. Best-effort by design: this is a courtesy
        surface, and the durable copies are the log file, the end-of-session
        dialog and the bundle's facts.
        """
        try:
            self._rip_progress.append_log_line(text)
        except Exception:  # noqa: BLE001 — a notice must never break the session
            log.exception("could not show the acceptance-session notice on screen")

    def _start_acceptance_script(self) -> None:
        """Load the packaged batch into the console and run it.

        Goes through :meth:`open_script_console` and then
        :meth:`ScriptConsoleDialog.run_now` — the one public entry point that
        `--run-script` and the config's autorun both use, so there is exactly one
        description of how a batch starts. (``open_script_console(autorun=True)``
        cannot be used in a single call here: it would start whatever the editor
        already holds *before* our script is loaded, which is precisely the rig
        defect of 2026-08-13 — a clean-looking transcript of a nine-line sample
        the operator never asked for. `app.py`'s `--run-script` path takes the
        same two steps in the same order and for the same reason.)

        **The load is checked.** A script that will not load stops the session; it
        does not fall through to whatever is in the editor.
        """
        layout = self._acceptance_layout
        script = self._acceptance_script
        if layout is None or script is None:  # pragma: no cover — guarded upstream
            return
        console = self.open_script_console()
        if not console.load_file(script):
            log.error("acceptance session: %s would not load; nothing was run", script)
            console.report_autorun_refused(
                script,
                "this is the acceptance script that ships inside Platterpus, so a "
                "read failure here means the app's own files are unreadable",
            )
            self._end_acceptance_session("the acceptance script would not load")
            self._acceptance_message(
                QMessageBox.Icon.Critical,
                "The acceptance test did not start",
                "⚠ Nothing was run.\n\nThe acceptance script that ships inside "
                f"Platterpus could not be read:\n{script}\n\nThe sleep lock has "
                "been released.",
            )
            return
        # Connect once per console. The slot is also guarded on
        # `_acceptance_layout`, so a duplicate connection would be harmless — but
        # a connection per session against one long-lived dialog is untidy, and
        # untidy grows.
        if self._acceptance_console is not console:
            console.run_finished.connect(self._on_acceptance_run_finished)
            self._acceptance_console = console
        log.info("acceptance session: starting the batch (%s)", script)
        # The run's transcript, report and screenshots go into the session folder,
        # and the runner builds no bundle of its own: the session builds the one.
        console.contain_next_run_in(layout.run_dir)
        console.size_next_run(self._acceptance_run_size)
        # **The start is CHECKED, not assumed.** `run_now()` declines when a run
        # is already in flight — the operator triggered Tools → Run acceptance
        # test twice, or left a console running from earlier — and until it
        # returned a value this method logged *"starting the batch"* and then
        # armed a session around a batch that never began: the sleep lock held,
        # the layout armed, and the window waiting on a `run_finished` that
        # belongs to somebody else's script or to nothing at all. Asserting that
        # a thing was REQUESTED where the claim is that it HAPPENED (`CLAUDE.md`).
        if not console.run_now():
            self._refuse_acceptance_start(console, script)
            return

    def _refuse_acceptance_start(
        self, console: ScriptConsoleDialog, script: Path
    ) -> None:
        """End a session whose batch would not start, saying why on screen.

        Split out of :meth:`_start_acceptance_script` so the refusal reads as one
        thing: **disarm, release, explain**. Getting any one of those wrong leaves
        either a machine held awake or an operator who believes a six-hour run is
        under way.

        **The reason is read from the console, not guessed.** The only refusal
        `run_now()` has today is "a run is already in progress", and naming *that*
        is what makes the message actionable — "it did not start" tells nobody
        what to do next. A refusal we cannot place is reported as exactly that,
        never as a cause we made up (tri-state, as everywhere else here).

        **Why a modal is right here even though a script may be running.** A
        spontaneous dialog over an unattended batch is a measured defect in this
        project — but this one is the answer to a menu item the operator chose
        seconds ago, and the alternative is the silent no-op the whole feature is
        written against: a menu item that does nothing and says nothing. The live
        log line goes out too, because that is where an operator watching a
        running batch is already looking.
        """
        runner = console.runner
        if runner is not None and runner.running:
            reason = "a test script is ALREADY RUNNING in the Run test script console."
            what_to_do = (
                "Stop that run (the Stop button in that console), then start the "
                "acceptance test again."
            )
        else:
            # Not determined: the console declined for a reason this window
            # cannot place. Say so rather than inventing one.
            reason = "the test-script console declined to start it, for a reason this window could not read."
            what_to_do = (
                "Open Tools → Run test script… to see what the console says, then "
                "start the acceptance test again."
            )
        log.error("acceptance session: the batch did not start — %s", reason)
        self._show_acceptance_notice(f"⚠ The acceptance test did not start — {reason}")
        self._end_acceptance_session("the batch would not start")
        self._acceptance_message(
            QMessageBox.Icon.Critical,
            "The acceptance test did not start",
            f"⚠ Nothing was run — {reason}\n\n{what_to_do}\n\n"
            f"The script that would have run:\n{script}\n\n"
            "The sleep lock has been released.",
        )

    def _on_acceptance_run_finished(self, report: object) -> None:
        """The batch is over — runs on the GUI thread. Release, then pack.

        **Release first, and in a `finally`.** The lock owns a child process, and
        the one ordering that can leak it is "release after the bundle": a bundle
        that wedges, or a bug in the reads below, would hold the machine awake
        until reboot. The archive is a gzip of text files measured in seconds, so
        nothing about it needs the lock — unlike the shell collector it replaces,
        which tarred hundreds of megabytes of rip folders under the lock
        deliberately.

        Everything Qt-shaped is read HERE, on the GUI thread, and handed to the
        daemon as plain values. A worker that reaches back into a widget is a bug
        this codebase has already paid for.
        """
        layout = self._acceptance_layout
        if layout is None:
            return  # not our run, or the session was already ended
        # Clear FIRST: one bundle per session, whatever else happens below.
        self._acceptance_layout = None

        facts: dict[str, str] = {}
        transcript = ""
        artifact_dir: Path | None = None
        settings_record = ""
        album_roots: list[Path] = []
        try:
            facts["sleep lock"] = self._acceptance_inhibit_note or "not determined"
            # Which size ran. Only `full` is evidence, so the archive says which.
            facts["run size"] = self._acceptance_run_size
            script = self._acceptance_script
            facts["acceptance script"] = str(script) if script else "(not recorded)"
            console = self._acceptance_console
            if console is not None:
                try:
                    transcript = console.transcript_text()
                except RuntimeError:
                    # The dialog's C++ half is already gone (a close raced us).
                    # Named rather than dropped — an empty transcript in the
                    # archive would otherwise read as a run that printed nothing.
                    log.warning("the acceptance transcript could not be read back")
                    facts["transcript"] = "NOT CAPTURED — the console was destroyed"
            facts.update(self._acceptance_run_facts(report))
            # The same report, rendered for the morning dialog. Read HERE, while
            # the report is in hand: the bundle finishes seconds-to-minutes later
            # and the payload is not carried through the daemon.
            self._acceptance_run_verdict = self._acceptance_run_headline(report)
            facts["run outcome"] = self._acceptance_run_verdict
            artifact_dir = self._acceptance_artifact_dir(report)
            from platterpus.user_settings import settings_record_text

            # Before the restore below: afterwards `_config` is the user again.
            settings_record = settings_record_text(
                self._acceptance_user_config, self._config
            )
            album_roots = self._acceptance_album_roots(layout)
        finally:
            self._release_acceptance_inhibitor()
            # After the facts are read (they describe the run's own settings) and
            # in the `finally`, so an exception while reading them cannot leave
            # the user on the run's test values.
            restored = self._restore_settings_after_acceptance()
        facts["your settings"] = (
            "restored after the run; it had changed " + ", ".join(restored)
            if restored
            else "unchanged by the run"
        )

        # **A RUN WITH NOTHING IN IT GETS NO ARCHIVE AND NO FOLDER PROMPT.**
        # A precondition abort — the wrong ripper installed, the disc not
        # identified — stops in seconds having touched no drive, and still packed
        # a multi-hundred-megabyte archive (the app log dominates it) and put up
        # a modal offering to open the folder. Three attempts, three archives,
        # three dialogs; the maintainer's report on 2026-09-08 was *"it keeps
        # asking me to open a folder and makes a new compressed file"*.
        #
        # **The asymmetry decides the direction.** Suppressing an archive that
        # HAD evidence costs an overnight disc pass; skipping one nothing needed
        # costs a dialog. So the predicate answers True only when it is certain
        # there is nothing (`RunReport.produced_no_artifacts`), and a payload we
        # cannot read at all falls through to building the archive.
        #
        # The transcript is NOT lost: `ScriptRunner` has already written it, the
        # report JSON and any screenshots to its own run folder, which the
        # message below names. What is skipped is the redundant archive around
        # them — and the prompt that implies there is something to send.
        nothing_to_send = False
        predicate = getattr(report, "produced_no_artifacts", None)
        if callable(predicate):
            try:
                nothing_to_send = bool(predicate())
            except Exception:  # noqa: BLE001 — never end a session on our own bug
                log.exception("could not decide whether the run produced artifacts")
                nothing_to_send = False
        if nothing_to_send:
            self._announce_run_with_nothing_to_send(report, artifact_dir)
            return

        self._launch_acceptance_bundle(
            layout,
            transcript=transcript,
            facts=facts,
            artifact_dir=artifact_dir,
            settings_record=settings_record,
            album_roots=album_roots,
        )

    def _announce_run_with_nothing_to_send(
        self, report: object, artifact_dir: Path | None
    ) -> None:
        """Say what stopped the run and what to do — no archive, no folder button.

        **The dialog states the fix rather than offering a folder.** A run that
        aborted on a precondition has one useful sentence in it, and it is
        already in the transcript: the failing step's own message, which names
        the command that repairs it. Offering to open a folder instead asks the
        operator to go and find that sentence.

        `open_path` is deliberately omitted even though the run folder exists.
        There is nothing in it to send, and a button that opens a folder is a
        button that says *"there is something here for you"*.
        """
        reason = str(getattr(report, "ended_reason", "") or "")
        first = ""
        for step in getattr(report, "steps", []) or []:
            outcome = str(getattr(step, "outcome", ""))
            if outcome in ("fail", "error"):
                detail = str(getattr(step, "detail", "") or "").strip()
                line = getattr(step, "line_no", "?")
                source = str(getattr(step, "source", "") or "").strip()
                first = f"L{line}  {source}\n\n{detail}"
                break
        body = (
            "The run stopped before it touched the drive, so there is nothing to "
            "send and no archive was made.\n\n"
            + (f"{first}\n\n" if first else "")
            + (f"Why it stopped: {reason}\n\n" if reason else "")
            + "Fix the step above and start the acceptance test again. The "
            "transcript of this attempt is kept"
            + (f" in {artifact_dir}" if artifact_dir is not None else "")
            + "."
        )
        self._acceptance_message(
            QMessageBox.Icon.Warning,
            "The acceptance run stopped early — nothing to send",
            body,
        )

    def _acceptance_run_facts(self, report: object) -> dict[str, str]:
        """The run's own verdict, as facts for the bundle manifest. Never raises.

        Read through `getattr` rather than an `isinstance` narrow because this is
        a report we only describe: an unexpected payload becomes a stated
        "not determined" line rather than an exception on top of a finished run.
        """
        counts = getattr(report, "counts", None)
        if not callable(counts):
            return {
                "run verdict": f"not determined (payload was {type(report).__name__})"
            }
        try:
            tally = counts()
        except Exception as exc:  # noqa: BLE001 — a fact must not end the session
            log.exception("could not read the acceptance run's counts")
            return {"run verdict": f"not determined ({type(exc).__name__}: {exc})"}
        ended = str(getattr(report, "ended_reason", "") or "reached the last step")
        return {
            "run verdict": ", ".join(
                f"{name} {value}" for name, value in tally.items()
            ),
            "run ended": ended,
        }

    def _acceptance_run_headline(self, report: object) -> str:
        """The RUN's outcome in one sentence, for the closing dialog. Never raises.

        **Why this exists.** The end-of-session dialog used to open with
        *"✓ Send this one file"* whenever the **bundle** succeeded — and a bundle
        succeeding says nothing whatever about the run inside it. An operator who
        aborted in section A, or whose batch recorded forty failures, was handed a
        tick. Every field in that message was true and the sentence it left behind
        was false, which is the failure shape this project keeps paying for.

        **Tri-state, and a verdict is never invented.** Three real answers:

        * *passed* — every step ran and passed, and the run reached the end;
        * *finished with N failure(s)* — it ran to the end and found things;
        * *did not complete* — it stopped early (aborted, stopped, the window
          went), so the steps after that point measured nothing.

        Anything we cannot read is **not determined**, which is a real answer and
        not a pass. So is a report with **zero steps**: "all 0 steps passed" is a
        sentence that can be satisfied by finding nothing, and this is the dialog
        somebody acts on (`CLAUDE.md` — give a check that can pass on emptiness a
        floor).

        Read through `getattr` rather than an `isinstance` narrow for the same
        reason :meth:`_acceptance_run_facts` is: an unexpected payload becomes a
        stated line, never an exception raised on top of a finished six-hour run.

        Every branch carries a `✓`/`⚠`/`ⓘ` marker, because status is never
        colour alone (`CLAUDE.md`, accessibility) — and this text is read in a
        screenshot as often as on screen.
        """
        counts = getattr(report, "counts", None)
        if not callable(counts):
            return (
                "ⓘ Run outcome: NOT DETERMINED — the console reported a "
                f"{type(report).__name__}, which this window cannot read. Open "
                "the transcript in the bundle to see what the run did."
            )
        try:
            tally = counts()
        except Exception as exc:  # noqa: BLE001 — a verdict must not end the session
            log.exception("could not read the acceptance run's counts")
            return (
                "ⓘ Run outcome: NOT DETERMINED — the run's own tally could not be "
                f"read ({type(exc).__name__}: {exc}). The transcript in the bundle "
                "is the record."
            )

        # Defensive reads: `tally` comes from a payload we only describe.
        def _n(name: str) -> int:
            value = tally.get(name, 0) if isinstance(tally, dict) else 0
            return value if isinstance(value, int) else 0

        passed = _n("pass")
        failures = _n("fail") + _n("error") + _n("blocked")
        skipped = _n("skipped")
        total = passed + failures + skipped
        ended = str(getattr(report, "ended_reason", "") or "")

        if total == 0:
            # The floor. A report with no steps is not a clean run — it is a run
            # that recorded nothing, and the two must not read alike.
            return (
                "ⓘ Run outcome: NOT DETERMINED — the report records no steps at "
                "all, so nothing was measured. Read the transcript in the bundle."
            )
        if ended or skipped:
            why = ended or "it stopped before the last step"
            return (
                f"⚠ The run DID NOT COMPLETE — {why}. {passed} of {total} step(s) "
                f"passed, {failures} failed, {skipped} never ran. The steps after "
                "the stop measured nothing."
            )
        if failures:
            return (
                f"⚠ The run finished with {failures} FAILURE(S) — {passed} of "
                f"{total} step(s) passed. Send the file anyway: the failures are "
                "the point."
            )
        return f"✓ The run PASSED — all {total} step(s) passed."

    def _acceptance_artifact_dir(self, report: object) -> Path | None:
        """The run's screenshot directory, if it took any.

        This is the one directory it is safe to hand `finish_session` as an
        `extra` source: `test_session._stage` admits a *directory* under the
        widened allowlist that exists for screenshots this program took of its
        own window. An **album** folder must never be named there — its
        `cover.png` is record-label artwork (Critical rule #8) — which is why the
        rip folders are not collected here.
        """
        from pathlib import Path

        raw = getattr(report, "artifact_dir", "")
        if not isinstance(raw, str) or not raw:
            return None
        return Path(raw)

    def _acceptance_album_roots(self, layout: object) -> list[Path]:
        """Where this run's albums are: the session's rips, plus any folder the
        run's own settings pointed rips at instead. Read BEFORE the restore.
        """
        from pathlib import Path

        # `getattr`: the finish handler must never raise on a layout it did not
        # expect (a test stand-in, or a future shape) — an archive with fewer
        # albums beats no archive.
        rips = getattr(layout, "rips", None)
        roots: list[Path] = [rips] if isinstance(rips, Path) else []
        for value in (self._config.output_dir, self._config.library_dir):
            if value and Path(value) not in roots:
                roots.append(Path(value))
        return roots

    def _launch_acceptance_bundle(
        self,
        layout: SessionLayout,
        *,
        transcript: str,
        facts: dict[str, str],
        artifact_dir: Path | None,
        settings_record: str = "",
        album_roots: list[Path] | None = None,
    ) -> None:
        """Pack the session into ONE file, on a daemon thread.

        Off-thread because it gzips the app log and its rotations — 4.4 MB in one
        measured session, plus however many rotations — and the GUI-thread rule
        has no exception for "usually fast". A plain daemon rather than a
        `QThread`: it owns no Qt object, it guards its own emit, and it adds no
        `closeEvent` teardown obligation (the pattern
        `main_window_rip._launch_evidence_bundle` set out, for those reasons).

        The closure holds plain values only. `finish_session` never raises by
        contract; the `try` around it is for everything else in here, so that a
        failure still arrives as a `BundleResult.error` the user is shown rather
        than as a traceback nobody sees.
        """

        from platterpus.evidence_bundle import BundleResult
        from platterpus.paths import CONFIG_PATH, LOG_PATH
        from platterpus.test_session import (
            finish_session,
            session_album_dirs,
            session_sources,
        )

        extra: list[Path] = [CONFIG_PATH]
        if artifact_dir is not None:
            extra.append(artifact_dir)

        # THE DIAGNOSTICS BLOB, rendered HERE on the GUI thread and carried into
        # the archive as text — the same thing every per-rip evidence bundle has
        # carried since 0.6.19, and which the session bundle was silently missing.
        #
        # It is the version PAIR (ours and the ripper's), the environment block
        # and the dependency states. The app log holds most of that scattered
        # across six hours of lines; this is the one place it is assembled, and
        # assembling it is exactly what a person should not have to do from a
        # transcript at 7am.
        #
        # On the GUI thread deliberately, and measured before deciding: it is
        # pure — no subprocess, no network — and renders in 29 ms. `build_bundle`
        # takes it as `extra_text` precisely so a Qt-free module never has to
        # reach into the UI for it.
        try:
            from platterpus.ui.dialogs.diagnostics_dialog import build_diagnostics_text

            diagnostics = build_diagnostics_text()
        except Exception as exc:  # noqa: BLE001 — the bundle must survive this
            log.exception("could not render diagnostics for the session bundle")
            diagnostics = f"(diagnostics could not be rendered: {exc!r})"

        # WHERE THE RIPS LANDED: handed in, read before the user's settings were
        # restored. Reading the config here, after the restore, searched the
        # USER's folders — and with the rips now in the session folder, would
        # have found none of this run's albums.
        roots: list[Path] = list(album_roots or [])
        since = self._acceptance_started_at
        # Every component and its version, read here (plain reads, no probe) so
        # the daemon closes over a string: the same inventory Help → About shows.
        import json

        from platterpus import build_info
        from platterpus.deps import manager as dep_manager

        components = json.dumps(
            build_info.component_inventory(dep_manager.latest_report()), indent=2
        )

        def work() -> None:
            result = BundleResult()
            try:
                try:
                    layout.transcript.write_text(transcript, encoding="utf-8")
                except OSError as exc:
                    # Named, not dropped: `session_sources` still lists the
                    # transcript, so the archive's SOURCES.txt will report it
                    # ABSENT — an absence somebody can read.
                    log.warning(
                        "could not write the acceptance transcript to %s: %r",
                        layout.transcript,
                        exc,
                    )
                albums = session_album_dirs(roots, since=since)
                result = finish_session(
                    layout,
                    sources=session_sources(layout, log_path=LOG_PATH, extra=extra),
                    outcome="acceptance test session",
                    facts=facts,
                    album_dirs=albums,
                    embedded_text={
                        "DIAGNOSTICS.txt": diagnostics,
                        # Every user setting before and at the end of the run —
                        # the bundle's config.toml is read after the restore.
                        **(
                            {"SETTINGS.json": settings_record}
                            if settings_record
                            else {}
                        ),
                        "COMPONENTS.json": components,
                    },
                )
            except Exception as exc:  # noqa: BLE001 — must never crash the session
                log.exception("could not pack the acceptance session")
                result = BundleResult(error=f"{type(exc).__name__}: {exc}")
            try:
                self.acceptance_bundle_done.emit(result)
            except RuntimeError:  # window destroyed while we worked
                pass

        thread = threading.Thread(
            target=work, daemon=True, name="platterpus-acceptance-bundle"
        )
        self._acceptance_bundle_thread = thread
        thread.start()

    def _on_acceptance_bundle_done(self, result: object) -> None:
        """Name the one file — runs on the GUI thread.

        **Tri-state, and an error is a real answer.** A `BundleResult` carrying
        `.error` is never reported as a bundle that was written: the session
        folder is still complete on disk, so the dialog says so and offers to open
        *that* instead. Reporting a failed archive as a success is how somebody
        uploads a file that is not there.
        """
        path = getattr(result, "path", None)
        error = str(getattr(result, "error", "") or "")
        note = self._acceptance_inhibit_note or "Sleep lock: not determined."
        if error or path is None:
            reason = error or "the bundler returned no path and no error"
            log.error("acceptance session bundle failed: %s", reason)
            self._acceptance_message(
                QMessageBox.Icon.Warning,
                "The acceptance run finished — the bundle did not",
                # The run's own outcome belongs here too: "the bundle failed" is
                # not an answer to "did the run pass", and the operator needs
                # both before deciding what to do with the session folder.
                f"{self._acceptance_run_verdict or 'ⓘ Run outcome: NOT DETERMINED.'}"
                "\n\n⚠ The run is over, but the single file could not be "
                f"written.\n\n{reason}\n\nEverything it would have contained is "
                f"still in the session folder:\n{self._acceptance_root}\n\n{note}",
                open_path=self._acceptance_root,
            )
            return
        included = len(getattr(result, "included", []) or [])
        excluded = len(getattr(result, "skipped", []) or [])
        # THE RUN'S OUTCOME LEADS, THE FILE FOLLOWS. This message used to open
        # with "✓ Send this one file" on the strength of the *bundle* having been
        # written — a tick over a run that had aborted in section A or recorded
        # forty failures. The bundle succeeding and the run passing are two
        # different facts and only one of them is what the operator is asking.
        #
        # An unset verdict is NOT DETERMINED, never a pass: this branch can be
        # reached by a bundle that finished for a run whose report never arrived.
        verdict = self._acceptance_run_verdict or (
            "ⓘ Run outcome: NOT DETERMINED — no finished run was recorded for "
            "this session. The transcript in the file below is the record."
        )
        # The FILE LINE STAYS whatever the verdict is: a failed run's evidence is
        # exactly what has to be sent, and a dialog that withheld the path on a
        # failure would lose the run it was written to capture.
        log.info(
            "acceptance session: SEND THIS ONE FILE: %s (%s)",
            path,
            self._acceptance_run_verdict or "run outcome not determined",
        )
        self._acceptance_message(
            QMessageBox.Icon.Information,
            "Acceptance run finished",
            f"{verdict}\n\n"
            "Send this one file:\n\n"
            f"{path}\n\n"
            "Everything the run made — its rips, transcript, report and "
            f"screenshots — is in that one folder:\n{self._acceptance_root}\n\n"
            f"{included} file(s) included, {excluded} excluded; no audio.\n\n"
            f"{note}",
            open_path=path.parent,
        )

    def _release_acceptance_inhibitor(self) -> None:
        """Drop the sleep lock. Idempotent, bounded, and never raises.

        `SleepInhibitor.release()` is safe to call twice or never, and it raises
        a watermark that kills a lock child which is still being spawned — so
        calling this while an `acquire()` is in flight is correct, not a race.
        """
        inhibitor = self._acceptance_inhibitor
        self._acceptance_inhibitor = None
        if inhibitor is None:
            return
        inhibitor.release()
        log.info("acceptance session: the sleep lock has been released")

    def _end_acceptance_session(self, reason: str) -> None:
        """Disarm a running session and release its lock. Safe to call always.

        Clearing :attr:`_acceptance_layout` is what stops a run that ends *after*
        this — a console closed during teardown emits `run_finished` — from
        starting a bundle daemon while the window is being destroyed.
        """
        if self._acceptance_layout is None and self._acceptance_inhibitor is None:
            return
        log.info("acceptance session ending: %s", reason)
        self._acceptance_layout = None
        self._release_acceptance_inhibitor()
        # An aborted run is exactly the case the script's own final reset never
        # reaches: stopped during the format sections, it would leave the user
        # ripping WAV. So the restore belongs to every exit, not to the script.
        self._restore_settings_after_acceptance()

    def _restore_settings_after_acceptance(self) -> list[str]:
        """Put the user's settings back; return which fields the run had changed.

        Safe to call more than once — the snapshot is consumed, so the second
        call is a no-op and cannot restore a stale copy over a later edit.
        No SETTING is kept from the run: its values are test values, and even
        the read offset it sets (`667`, the maintainer's drive) belongs to one rig
        rather than to whoever runs the script. The app's own state
        (:data:`~platterpus.config.APP_STATE_FIELDS`) is left as it now is.
        """
        saved = self._acceptance_user_config
        self._acceptance_user_config = None
        if saved is None:
            return []
        from platterpus.user_settings import changed_settings

        # The user's SETTINGS only. The app's own bookkeeping moves on during a
        # run for real reasons (a first-run offer made and answered), and putting
        # the old value back would re-ask a question the user already answered —
        # the first version of this did exactly that with `host_setup_prompted`.
        changed = changed_settings(saved, self._config)
        restored = dataclasses.replace(
            self._config, **{name: getattr(saved, name) for name in changed}
        )
        self._config = restored
        self._rip_controls.set_config(restored)
        from platterpus.logging_setup import set_debug_logging

        set_debug_logging(restored.debug_logging)
        try:
            self._save_config(restored)
        except OSError as exc:
            log.warning("acceptance session: could not save restored settings: %s", exc)
        log.info(
            "acceptance session: restored your settings (the run had changed %s)",
            ", ".join(changed) or "nothing",
        )
        return changed

    def _on_run_acceptance_action(self) -> None:
        """Tools → Run acceptance test…: ask the size, then run the session."""
        self.run_acceptance_session()

    def _ask_acceptance_run_size(self) -> str | None:
        """Which run size? ``None`` when the operator cancels. PlainText.

        One question, asked before anything is created or held. The wording is
        :data:`run_sizes.CHOICES`, the one place a size is described, and it says
        which size counts as evidence, because a person choosing Quick to save the
        evening should know what it will not prove.
        """
        from platterpus.uiscript import run_sizes

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Run acceptance test")
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(
            "Which run?\n\n"
            + "\n".join(label for _size, label in run_sizes.CHOICES)
            + "\n\nEvery size is cut from the same script. Only Full counts toward "
            "a version or a handshake close; a smaller run marks each section it "
            "leaves out."
        )
        buttons = [
            (
                box.addButton(
                    "&" + label.split(" — ", 1)[0], QMessageBox.ButtonRole.AcceptRole
                ),
                size,
            )
            for size, label in run_sizes.CHOICES
        ]
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        clicked = box.clickedButton()
        return next((size for button, size in buttons if button is clicked), None)

    def _acceptance_message(
        self,
        icon: QMessageBox.Icon,
        title: str,
        text: str,
        *,
        open_path: Path | None = None,
    ) -> None:
        """The one message box this feature uses. PlainText, with a way out.

        **PlainText, always.** The text carries filesystem paths and
        `systemd-inhibit`'s own sentences; Qt's default `AutoText` auto-detects
        markup, so a `<` in either is swallowed as an unknown tag and the reader
        never learns text went missing (`CLAUDE.md`, inbound seam).

        `open_path` adds a button that opens a folder — because a path a user has
        to retype is a path they will mistype, and `~/Downloads` is where a
        browser's upload dialog already looks. The folder is opened **after**
        `exec()` returns, so no work happens inside the modal's nested loop.
        """
        box = QMessageBox(self)
        box.setIcon(icon)
        box.setWindowTitle(title)
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(text)
        open_button = (
            box.addButton("&Open the folder", QMessageBox.ButtonRole.ActionRole)
            if open_path is not None
            else None
        )
        box.addButton(QMessageBox.StandardButton.Close)
        box.exec()
        if open_path is not None and box.clickedButton() is open_button:
            from platterpus.ui.external_open import open_path_externally

            open_path_externally(open_path, parent=self, what="session folder")

    def open_uninstall_dialog(self) -> None:
        """Open the in-app Uninstaller (Tools → Uninstall Platterpus…)."""
        from platterpus.ui.uninstall_dialog import UninstallDialog

        dialog = UninstallDialog(self)
        dialog.uninstall_finished.connect(self._on_uninstall_finished)
        dialog.exec()

    def _on_uninstall_finished(self, complete: bool) -> None:
        """After a successful uninstall, offer to close the app right away.

        The config/log dirs are gone; anything that saves config from here
        on would recreate them, so quitting immediately is the clean path.
        """
        if not complete:
            return
        choice = QMessageBox.question(
            self,
            "Uninstall complete",
            "Platterpus has been removed from this computer.\n\n"
            "Close the app now? (Recommended — staying open could "
            "recreate settings files.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if choice == QMessageBox.StandardButton.Yes:
            self.close()

    def _on_host_setup_finished(self, ready: bool) -> None:
        """After the wizard runs, re-probe the world if whipper now exists.

        Refresh the drive list ONLY when no drive is selected yet — i.e. the
        FIRST time setup makes the stack usable. A later wizard run (e.g.
        installing flac from the dependency check) leaves the drive already
        selected; re-listing it there re-fires the disc scan for no reason,
        which the user (rightly) found annoying — "after every install it asked
        me about scanning the disk" (real-user report, 2026-06-27). The dep
        re-check is cheap and always runs.
        """
        if ready:
            log.info("host setup reported ready — refreshing deps")
            try:
                if not self._drive_picker.current_device():
                    log.info("no drive selected yet — refreshing drive list")
                    self.refresh_drives()
                # Off the GUI thread: the re-probe shells into the container.
                self.run_dependency_check_async(show_summary=False)
            except Exception:  # noqa: BLE001 — best-effort refresh
                log.exception("post-host-setup refresh failed")
