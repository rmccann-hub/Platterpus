"""In-app self-update flow for the main window (KDD-17b).

Extracted from ``main_window`` (2026-06-13 modularization) as a mixin so
the update concern lives in one focused file while its methods stay
reachable as ``window._on_...`` (which the test-suite and Qt signal
connections rely on). ``MainWindow`` inherits this; the methods run with
``self`` being the real window.

Contract this mixin expects from the host window (all set in
``MainWindow.__init__``):
  * ``self._update_worker`` / ``self._update_thread`` — the check worker+thread slots
  * ``self._install_worker`` / ``self._install_thread`` — the install worker+thread slots
  * ``self._install_dialog`` / ``self._install_post_download`` — the progress
    dialog handle + phase flag the install signal-handlers read (so they can be
    bound methods queued to the GUI thread, not worker-thread closures)
  * ``self`` is a ``QWidget`` (used as the parent for dialogs)

Future contributors: the actual download/verify/install lives in
``update_install.py`` and ``workers/update_worker.py`` — this file is only
the GUI orchestration (threads, the progress dialog, the restart prompt).
A delta-update path via AppImageUpdate is still possible (the build embeds
zsync update-information); wiring it would slot in at ``_on_update_result``
beside the in-app download branch.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import QMessageBox

from platterpus import hard_exit
from platterpus.ui.main_window_shared import MainWindowShared

log = logging.getLogger(__name__)


# Environment variables the AppImage runtime (python-appimage's AppRun) injects
# into THIS process. They point at the *current* AppImage's mount/interpreter, so
# handing them to the freshly-installed AppImage makes its bundled Python load the
# OLD mount's libs/modules — which crashes the new instance on startup. That's the
# silent "it closed but didn't reopen" after an update (real-user report,
# 2026-06-27). Drop them so the new AppImage's own AppRun sets them fresh.
_APPIMAGE_ENV_VARS: tuple[str, ...] = (
    "APPDIR",
    "APPIMAGE",
    "ARGV0",
    "LD_LIBRARY_PATH",
    "PYTHONHOME",
    "PYTHONPATH",
    "PYTHONNOUSERSITE",
    "PYTHONDONTWRITEBYTECODE",
    "GIT_EXEC_PATH",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "GDK_PIXBUF_MODULE_FILE",
    "GDK_PIXBUF_MODULEDIR",
)


def _relaunch_env() -> dict[str, str]:
    """The environment to launch the updated AppImage with: the current env with
    the OLD AppImage mount scrubbed out of it.

    The old AppImage's AppRun injects **many** vars that point into its mount
    (``$APPDIR``, e.g. ``/tmp/.mount_platterXXXX``): ``LD_LIBRARY_PATH``,
    ``PYTHONPATH``, and — the ones a fixed name-blocklist keeps missing —
    ``QT_PLUGIN_PATH`` / ``QML2_IMPORT_PATH`` / ``GI_TYPELIB_PATH`` /
    ``GST_PLUGIN_*`` / ``XDG_DATA_DIRS`` additions. When *this* process exits the
    mount vanishes, so any such var handed to the NEW instance sends it looking
    into a gone directory and it aborts on startup — the silent "it closed but
    didn't reopen" (real-user reports 2026-06-27 and again on 0.4.6, where the
    Qt platform plugin couldn't be found). A name blocklist can't win that
    whack-a-mole, so we scrub by **value**: drop any var — or any single segment
    of a ``PATH``-style list — whose value points into the old mount, and let the
    new AppRun set everything fresh. Session vars (HOME, DISPLAY, WAYLAND_DISPLAY,
    DBUS_SESSION_BUS_ADDRESS, XDG_RUNTIME_DIR, LANG, XAUTHORITY, …) don't point
    into the mount, so they're kept untouched. The named list is retained as a
    belt for flag-style vars (e.g. PYTHONDONTWRITEBYTECODE) that carry no path.
    """
    import os

    # The old mount root. AppRun sets $APPDIR to it; the AppImage runtime's
    # default mount prefix is /tmp/.mount_ — match either so we catch the mount
    # even if $APPDIR is somehow unset.
    appdir = (os.environ.get("APPDIR") or "").strip()
    markers = [m for m in (appdir, "/tmp/.mount_") if m]

    def _into_old_mount(segment: str) -> bool:
        return any(marker in segment for marker in markers)

    cleaned: dict[str, str] = {}
    for key, value in os.environ.items():
        if key in _APPIMAGE_ENV_VARS:
            continue  # named AppRun var → always let the new AppRun re-set it
        if os.pathsep in value:
            # A path list (PATH, XDG_DATA_DIRS, QT_PLUGIN_PATH, …): keep only the
            # segments that DON'T point into the old mount, so e.g. PATH keeps its
            # system entries while losing the dead /tmp/.mount_* one.
            kept = [s for s in value.split(os.pathsep) if s and not _into_old_mount(s)]
            if kept:
                cleaned[key] = os.pathsep.join(kept)
            # else: entirely old-mount → drop the var
        elif value and _into_old_mount(value):
            continue  # a single value pointing into the old mount → drop it
        else:
            cleaned[key] = value
    return cleaned


def _is_download_phase(status_message: str) -> bool:
    """True while the update is still DOWNLOADING (a determinate %-complete bar),
    False once it's moved to verify/install (a busy "working" bar — those phases
    have no meaningful percentage and are quick, so a bar pinned at 100% looked
    frozen). Keys on the phase labels ``update_install.download_and_install``
    emits via its ``status`` callback ("Checking…", "Downloading…", then
    "Verifying…"/"Installing…")."""
    return status_message.startswith(("Checking", "Downloading"))


class UpdateMixin(MainWindowShared):
    """Help → Check for updates, and the download/verify/install/restart UI."""

    def _on_check_updates(self) -> None:
        """Help → Check for updates: ask GitHub for the newest release.

        Runs off-thread (a slow connection must not freeze the window);
        the result lands in _on_update_result. Delivery of the update is
        NOT ours: the AppImage embeds zsync update-information, so we
        delegate to an AppImageUpdate tool or open the releases page.
        """
        if self._update_thread is not None:  # a check is already running
            return
        from platterpus.workers import start_worker_thread
        from platterpus.workers.update_worker import UpdateCheckWorker

        # The channel is read HERE, on the GUI thread, and handed to the worker as a
        # plain string — the worker must not touch the config off-thread.
        self._update_worker = UpdateCheckWorker(channel=self._update_channel())
        self._update_thread = QThread(self)
        self._update_worker.finished.connect(self._on_update_result)
        start_worker_thread(
            self._update_worker, self._update_thread, self._update_worker.run
        )

    # --- The RIPPER's updates, which are a different question ----------------
    #
    # The app's own update is routine: take it, restart, carry on. A newer *ripper*
    # can be, and used not to be treated that way at all.
    #
    # REDESIGNED 2026-08-18, on the maintainer's instruction: *"the autoupdate on
    # platterpus should take the next viable candidate without the user needing to
    # pick … it shouldnt need to be explicity callled out by eitether rop unless very
    # impartant"*, and *"assume last most stable is good, then if beta flags are
    # checked, look for those, but it should still be an autoupdate."*
    #
    # What was here refused to install anything, ever, and ended every answer with a
    # command line carrying a SHA. The refusal had a real reason — a build our record
    # has not approved makes every subsequent rip report `unapproved` — but it was
    # applied to *every* build rather than to the ones it describes. The operator who
    # reported this had `c4d1a00` installed against a `ddf7ac3` pin and was told their
    # build was unrecognised and to install a released one themselves. The app knew
    # which build it wanted; only the person was allowed to act on it.
    #
    # So the split is by CONSEQUENCE, which is what the original reasoning was
    # actually about (see `deps/ripper_offer.py`):
    #
    #   * `offer.auto_installable` — our own record approves this build, so taking it
    #     costs nothing and there is nothing to read. One click, no SHA. This covers
    #     the overwhelmingly common case: getting back onto the build this Platterpus
    #     was verified against.
    #   * otherwise — the "very important" case. The offer states the consequence and
    #     hands over `--install-ripper <commit>`, and the app does not do it for you.
    #     A specific pin is a deliberate act, which is why it stayed a command line
    #     and is what a rig script calls.
    #
    # The install itself drives `HostSetup` — the SAME step engine as the setup wizard
    # and `--install-ripper` (Critical rules #6 and #12). No second installer exists.

    def _on_check_ripper_updates(self, *, automatic: bool = False) -> None:
        """Ask the fork's release manifest what it has published.

        Off-thread for the same reason every other network call here is: a stalled
        connection must not freeze the window for the whole timeout.

        ``automatic`` marks the launch-time check, whose result stays **silent unless
        it is actionable**. A check the user did not ask for must not interrupt them
        to say "nothing to do" — that is how an update prompt becomes something people
        dismiss without reading, which costs exactly the notice that mattered.

        **Keyword-only, and that is load-bearing.** This is connected to a
        ``QAction.triggered``, which emits ``bool checked`` — a *positional*
        argument. With ``automatic`` positional it happened to work (a non-checkable
        action emits ``False``), but it was right by accident: making the action
        checkable, or any future emitter passing ``True``, would silently turn the
        menu item into a check that stays quiet when it has nothing to offer. Behind
        ``*``, Qt sees a slot taking no positional arguments and passes none, so the
        two can never be confused.
        """
        if self._ripper_update_thread is not None:  # a check is already running
            return
        from platterpus.workers import start_worker_thread
        from platterpus.workers.ripper_update_worker import RipperUpdateWorker

        self._ripper_check_is_automatic = automatic
        # The channel is read HERE, on the GUI thread, and handed over as plain data —
        # the worker must not touch the config off-thread. The installed build is NOT
        # read here: probing it shells out to the host export, which enters a
        # container, so it belongs on the worker (see `_probe_installed_commit`).
        self._ripper_update_worker = RipperUpdateWorker(
            channel=self._ripper_channel(),
        )
        self._ripper_update_thread = QThread(self)
        self._ripper_update_worker.finished.connect(self._on_ripper_update_result)
        start_worker_thread(
            self._ripper_update_worker,
            self._ripper_update_thread,
            self._ripper_update_worker.run,
        )

    def _maybe_check_ripper_updates(self) -> None:
        """The automatic check, fired once shortly after launch.

        Deliberately *not* gated behind a preference. The thing it looks for is a
        mismatch between the installed ripper and the build this Platterpus was
        verified against — a state in which every rip the user makes carries
        ``unapproved`` into its archival record. A setting to stop being told that
        would be a setting to silently degrade one's own library.

        It is silent when there is nothing to do, and it never blocks the window.

        **It does not run during a rip.** A rip can start within the delay — the
        user came to rip a disc — and the one-click offer ends in a modal. Popping
        one over a running rip would steal focus from a progress view somebody is
        watching, and the install it offers replaces the very binary doing the
        ripping. Skipping is free: the check runs at the next launch, or from the
        Help menu whenever they want it.

        **Nor when the window is not on screen.** The timer was armed at launch and
        fires seconds later; by then the window may have been closed, or never shown.
        An offer's whole premise is somebody looking at the app, so `isVisible()` is
        the third of the three conditions this check is subject to — *a person is
        here*, *they are not busy*, *they asked or it matters enough to ask anyway*
        (`docs/architecture.md` §3.12a). Found 2026-08-18: `test_app_smoke` starts
        the real app and closes the window, and the timer still fired on it,
        leaving an install dialog standing over the rest of the suite. A user meets
        the same shape as a dialog appearing after they quit.
        """
        if not self.isVisible():
            log.info("skipping the automatic cyanrip check — the window is not shown")
            return
        if self._rip_thread is not None:
            log.info("skipping the automatic cyanrip check — a rip is running")
            return
        self._on_check_ripper_updates(automatic=True)

    def _ripper_channel(self) -> str:
        """The user's *ripper* update channel, defensively.

        Read off the live config rather than cached at construction, so flipping the
        setting takes effect on the next check without a restart. A value the
        validator would reject falls back to ``stable`` — widening what a user is
        offered is not a safe direction to fail in.
        """
        from platterpus.deps.ripper_manifest import CHANNEL_STABLE, CHANNELS

        channel = str(getattr(self._config, "ripper_channel", CHANNEL_STABLE) or "")
        return channel if channel in CHANNELS else CHANNEL_STABLE

    def _on_ripper_update_result(self, offer: object) -> None:
        """Act on the verdict: install on one click when it costs nothing to.

        The **offer** decides; this method only renders it. That division is
        deliberate and `deps/ripper_offer.py` carries the reasoning — a dialog that
        re-derives "is this safe" is a second opinion free to disagree with the one in
        the report a rip writes.
        """
        from platterpus.deps.ripper_offer import OFFER_AVAILABLE, OFFER_MISMATCHED

        self._ripper_update_worker = None
        self._ripper_update_thread = None
        automatic = self._ripper_check_is_automatic
        self._ripper_check_is_automatic = False

        detail = str(
            getattr(offer, "detail", "") or "Couldn't check for a newer ripper."
        )
        verdict = str(getattr(offer, "verdict", "") or "")
        install_commit = str(getattr(offer, "install_commit", "") or "")
        auto_installable = bool(getattr(offer, "auto_installable", False))

        # An unasked-for check stays quiet unless there is a one-click action. It must
        # not interrupt to report "you're current", and it must not interrupt to
        # report a build the user would have to install by hand — that is a menu
        # answer, not a launch-time one.
        #
        # **And it offers upgrades and repairs, never a step backwards.** A user who
        # is AHEAD of the pin is on a published release they installed on purpose —
        # during a joint test session, say — and `up_to_date` is the verdict that
        # says so. That state still carries a one-click way back (the menu offers
        # it, and the paragraph explains why their rips report `unapproved`), but
        # raising it unprompted at every launch would be the app nagging somebody to
        # undo a deliberate decision. Exactly the *"unless very important"* line the
        # redesign was asked for, applied to the direction of travel.
        auto_surfaceable = verdict in (OFFER_AVAILABLE, OFFER_MISMATCHED)
        if automatic and not (install_commit and auto_installable and auto_surfaceable):
            log.info(
                "automatic cyanrip update check: %s (nothing to offer silently)",
                verdict or "no verdict",
            )
            return

        if install_commit and auto_installable:
            self._offer_ripper_install(offer, detail, install_commit)
            return

        box = QMessageBox(self)
        box.setWindowTitle("Check for cyanrip updates")
        box.setText(detail)
        # PlainText, not Qt's default AutoText: this paragraph carries a version
        # string and a commit from a *network document*, and Qt auto-detects HTML —
        # a value containing `<` would be swallowed as an unknown tag and the user
        # would never learn text went missing. Same sweep as every other widget
        # carrying dependency output (CLAUDE.md rule 12, inbound seam).
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        box.setIcon(
            QMessageBox.Icon.Information
            if verdict in (OFFER_AVAILABLE, OFFER_MISMATCHED)
            else QMessageBox.Icon.NoIcon
        )
        box.exec()

    def _offer_ripper_install(self, offer: object, detail: str, commit: str) -> None:
        """Ask once, then install. Only reached when the offer says it costs nothing.

        "Ask once" is the whole shape: the consent happens here, and the progress
        dialog that follows starts immediately rather than presenting a second button
        for the same decision.

        **`open()`, never `exec()`, and that is not a style choice.** This dialog is
        raised from a *queued signal* — the update worker finishing — which on the
        automatic path was itself started by a timer. `exec()` spins a **nested event
        loop** inside whatever the GUI thread was doing, which is the modal-dialog
        trap `CLAUDE.md`'s GUI-thread rule names, arriving from a new direction: not
        a slot doing blocking work, but a slot *becoming* blocking work for its
        caller. Measured 2026-08-18: the suite reached this line from an unrelated
        test's `qapp.processEvents()` and stopped there with no one to click the
        button. A user can hit the same shape — a nested loop under a repaint, or
        under another dialog — and the symptom there is a frozen window.

        `open()` shows the dialog and returns; the answer arrives on
        :meth:`_on_ripper_offer_answered`, a bound method on the GUI thread. The box
        and the pending offer are held on ``self`` for the same reason the install
        progress dialog is: a handler that must survive the call that created it
        cannot close over local state.
        """
        box = QMessageBox(self)
        box.setWindowTitle("cyanrip update")
        box.setText(detail)
        box.setTextFormat(Qt.TextFormat.PlainText)  # see `_on_ripper_update_result`
        box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        box.setIcon(QMessageBox.Icon.Information)
        install = box.addButton("Install it now", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Not now", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(install)
        self._ripper_offer_box = box
        self._ripper_offer = offer
        self._ripper_offer_commit = commit
        box.buttonClicked.connect(self._on_ripper_offer_answered)
        # `finished` covers the ways out that click no button — Esc, the window's
        # close box. Without it the slots below stay set, pointing at a dialog
        # nobody can answer, and PySide6 turns the next access into "Internal C++
        # object already deleted" once Qt reaps it. Qt emits `buttonClicked` first,
        # so the handler above has already read and cleared them on the normal path
        # and this is a no-op there.
        box.finished.connect(self._on_ripper_offer_dismissed)
        box.open()

    def _on_ripper_offer_dismissed(self, _result: int) -> None:
        """Drop the offer slots when the dialog goes away without a button."""
        if self._ripper_offer_box is None:
            return  # answered already; `_on_ripper_offer_answered` cleared them
        log.info("cyanrip install offer dismissed (%s)", self._ripper_offer_commit)
        self._ripper_offer_box = None
        self._ripper_offer = None
        self._ripper_offer_commit = ""

    def _on_ripper_offer_answered(self, button: object) -> None:
        """The install offer's answer (GUI thread — `buttonClicked` from our own box).

        Keys on the button's **role**, not on identity with a stashed handle: the
        role is what the choice means, and it survives a future edit that rebuilds
        the buttons. Anything that is not an accept is a decline, which is the safe
        direction — an unrecognised answer must not install a ripper.
        """
        box = self._ripper_offer_box
        offer, commit = self._ripper_offer, self._ripper_offer_commit
        self._ripper_offer_box = None
        self._ripper_offer = None
        self._ripper_offer_commit = ""
        if box is None:
            return
        accepted = box.buttonRole(button) == QMessageBox.ButtonRole.AcceptRole
        if not accepted:
            log.info("cyanrip install declined by the user (%s)", commit)
            return
        self._begin_ripper_install(offer, commit)

    def _begin_ripper_install(self, offer: object, commit: str) -> None:
        """Build and install ``commit`` through the setup wizard's own step engine.

        **The same engine, not a copy.** `CLAUDE.md` Critical rule #6 puts every
        dependency install in one subsystem, and rule #12 names ``--install-ripper``
        as driving *"the same step engine as the wizard rather than a copied shell
        snippet"* — a second install path would drift the first time a build
        dependency changed, and would drift silently, because both would still
        produce a working binary most of the time.

        Every step is idempotent, so for a machine that is already set up this is a
        no-op through seven steps and a rebuild on the eighth. That is why it is safe
        to run the whole pipeline rather than reaching inside it for one step: a
        pipeline entered at the middle is a second pipeline.

        The blocking work (git, meson, ninja, `sudo install`, `distrobox-export` —
        minutes of it) runs on `HostSetupWorker`'s thread. Nothing here calls
        subprocess: this is the dialog-that-does-blocking-work trap `CLAUDE.md` names,
        and the dialog below is the one that already avoids it.
        """
        from platterpus.deps.fork_source import target_for_commit
        from platterpus.deps.host_setup import HostSetup
        from platterpus.deps.step_engine import SubprocessRunner
        from platterpus.ui.host_setup_dialog import HostSetupDialog, SetupCopy

        release = getattr(offer, "release", None)
        # The manifest's own build options for THIS commit, when the offer came from a
        # manifest row (schema 2). Round 11 §J1 asks that the options come from their
        # document rather than a constant of ours, and meson fails the whole configure
        # on an unknown `-D` — so passing the wrong ones is not a degraded build, it is
        # no build at all. Validated at the manifest boundary before it reaches here.
        target = target_for_commit(
            commit,
            version=str(getattr(release, "version", "") or "") or None,
            meson_options=tuple(getattr(release, "meson_options", ()) or ()),
        )
        log.info("installing cyanrip %s (expects %s)", target.pin, target.expectation)
        dialog = HostSetupDialog(
            self,
            host_setup=HostSetup(runner=SubprocessRunner(), fork_target=target),
            copy=SetupCopy(
                title="Updating cyanrip",
                intro=(
                    f"Installing cyanrip build <b>{target.pin}</b>.\n\n"
                    "Platterpus builds the ripper from source inside its container, "
                    "so this takes a few minutes. Everything already in place is "
                    "skipped — the rows below say which.\n\n"
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
            ),
            start_immediately=True,
        )
        dialog.exec()

    def _update_channel(self) -> str:
        """The user's update channel, defensively.

        Read off the live config rather than cached at construction, so flipping the
        setting takes effect on the next check without a restart. A value the
        validator would reject falls back to ``stable``: widening what a user is
        offered is not a safe direction to fail in.
        """
        from platterpus.update_check import CHANNEL_STABLE, CHANNELS

        channel = str(getattr(self._config, "update_channel", CHANNEL_STABLE) or "")
        return channel if channel in CHANNELS else CHANNEL_STABLE

    def _on_update_result(self, info: object) -> None:
        """Show the verdict; offer the standard update path when newer."""
        from platterpus import __version__, appimage_integration
        from platterpus.update_check import (
            CHANNEL_BETA,
            RELEASES_PAGE_URL,
            is_newer,
            is_prerelease_version,
        )

        self._update_worker = None
        self._update_thread = None

        if info is None:
            QMessageBox.information(
                self,
                "Check for updates",
                "Couldn't check for updates (no connection, or GitHub is "
                f"unreachable). You can always look yourself:\n{RELEASES_PAGE_URL}",
            )
            return
        version = getattr(info, "version", "")
        url = getattr(info, "url", RELEASES_PAGE_URL)
        on_beta = self._update_channel() == CHANNEL_BETA
        if not is_newer(version, __version__):
            # Name the channel in the "up to date" answer. On the stable channel a
            # user running a beta is genuinely up to date *for that channel* while a
            # newer beta exists, and a bare "newest release" would be the accurate-
            # but-misleading kind of true this project keeps finding.
            channel_note = (
                "\n\nYou're on the BETA channel, so pre-releases are included."
                if on_beta
                else (
                    "\n\nYou're on the stable channel — pre-releases (betas) are not "
                    "offered. Settings → Updates can change that."
                )
            )
            running_beta = (
                "\n\nNote: you are running a pre-release build. Turn on the beta "
                "channel in Settings → Updates to be offered newer betas."
                if is_prerelease_version(__version__) and not on_beta
                else ""
            )
            QMessageBox.information(
                self,
                "Check for updates",
                f"You're up to date — v{__version__} is the newest release "
                f"available to you.{channel_note}{running_beta}",
            )
            return

        # A pre-release offer always says so, in the offer itself. The channel
        # setting is where consent is given; this is where it is honoured visibly,
        # so a tester never installs a beta without having read the word.
        beta_warning = (
            f"\n\n⚠ {version} is a PRE-RELEASE (beta) build. It is published for "
            "testing: it may contain bugs, and its rip reports can name a ripper "
            "build no handshake round has approved. Your existing rips and settings "
            "are untouched, and you can reinstall a stable release at any time from "
            f"{RELEASES_PAGE_URL}."
            if is_prerelease_version(version) or getattr(info, "is_prerelease", False)
            else ""
        )

        # Newer release exists. When running as an AppImage, update fully
        # in-app: download + verify against the published .sha256 + install
        # to ~/Applications + offer a restart (KDD-17b amendment 2026-06-10 —
        # the original delegate-to-AppImageUpdate plan dead-ended because
        # that tool isn't installed on the target systems). Source/pipx
        # installs can't be file-swapped, so they get the release page.
        appimage = appimage_integration.appimage_path()
        if appimage is not None:
            choice = QMessageBox.question(
                self,
                "Update available",
                f"Version {version} is available (you have {__version__}).\n\n"
                "Update now? The new version is downloaded in the background, "
                "verified, and installed to ~/Applications — then the app "
                f"restarts itself.{beta_warning}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                # A pre-release does NOT get the default button. The one keypress a
                # user makes without reading should not install a tester build.
                QMessageBox.StandardButton.No
                if beta_warning
                else QMessageBox.StandardButton.Yes,
            )
            if choice == QMessageBox.StandardButton.Yes:
                self._begin_update_install(version)
            return
        choice = QMessageBox.question(
            self,
            "Update available",
            f"Version {version} is available (you have {__version__}).\n\n"
            f"Open the download page?{beta_warning}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if choice == QMessageBox.StandardButton.Yes:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices

            QDesktopServices.openUrl(QUrl(url))

    def _begin_update_install(self, version: str) -> None:
        """Download + verify + install `version` off-thread with progress.

        The worker's progress/status/finished signals are connected to BOUND
        METHODS of this window — NOT local closures or a lambda. This is for
        correctness, not style: a closure/lambda has no QObject receiver, so Qt
        connects it as a DIRECT connection and runs it on the *worker* thread
        when the signal fires there. These handlers touch the progress dialog (a
        widget) and pop a QMessageBox, and doing that off the GUI thread is
        illegal in Qt — it froze the window mid-update ("Not Responding",
        real-user report 2026-06-27). A bound method of this (GUI-thread) window
        is delivered as a queued connection, so it runs on the GUI thread. (Same
        bug + fix as the launch dependency check.)
        """
        if self._install_thread is not None:  # an install is already running
            return
        from PySide6.QtWidgets import QProgressDialog

        from platterpus.workers import start_worker_thread
        from platterpus.workers.update_worker import UpdateInstallWorker

        self._install_worker = UpdateInstallWorker(version)
        self._install_thread = QThread(self)

        dialog = QProgressDialog(
            f"Downloading Platterpus {version}…", "Cancel", 0, 100, self
        )
        dialog.setWindowTitle("Updating")
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.setMinimumDuration(0)
        # Stashed on self so the worker→GUI handlers can be bound methods
        # (queued to the GUI thread). `_install_post_download` flips once we
        # leave the download phase, so a late progress(100) can't re-pin a
        # static 100% after we've switched to the busy "working" indicator.
        self._install_dialog = dialog
        self._install_post_download = False

        self._install_worker.progress.connect(self._on_install_progress)
        self._install_worker.status.connect(self._on_install_status)
        self._install_worker.finished.connect(self._on_update_install_finished)
        # Cancel button → stop between chunks; the worker cleans up the .part.
        # Route through a GUI-thread bound method (NOT worker.cancel directly):
        # the worker is blocked inside run() on its own thread, so a queued call
        # to its slot would never be delivered until the download already
        # finished. Setting the flag from the GUI thread (the receiver lives
        # here) runs immediately; the worker's chunk loop reads it. (Atomic bool.)
        dialog.canceled.connect(self._on_install_cancel_requested)
        # Standard teardown + start (finished → quit → deleteLater, run on spin-up).
        start_worker_thread(
            self._install_worker, self._install_thread, self._install_worker.run
        )
        dialog.show()

    def _on_install_cancel_requested(self) -> None:
        """Cancel button clicked (GUI thread) — set the worker's flag directly.

        Runs on the GUI thread (the dialog is a GUI-thread object), so this is a
        direct call that flips the worker's atomic ``_cancelled`` bool right away;
        the worker's download loop checks it between chunks. Connecting the
        button to ``worker.cancel`` instead would *queue* the call to the worker's
        blocked event loop, so it would never fire until the download finished.
        """
        if self._install_worker is not None:
            self._install_worker.cancel()

    def _on_install_progress(self, percent: float) -> None:
        """Update the download progress bar (GUI thread — queued from the
        worker's ``progress`` signal)."""
        dialog = self._install_dialog
        if dialog is None or self._install_post_download:
            return  # verify/install run as a busy bar, not a percentage
        if percent < 0:  # size unknown → busy indicator
            dialog.setRange(0, 0)
        else:
            dialog.setRange(0, 100)
            dialog.setValue(int(percent))

    def _on_install_status(self, message: str) -> None:
        """Reflect the current phase (GUI thread — queued from the worker's
        ``status`` signal)."""
        dialog = self._install_dialog
        if dialog is None:
            return
        dialog.setLabelText(message)
        # Once past the download the operation can't be safely cancelled (the
        # file swap is atomic), so retire the Cancel button (real-user report
        # 2026-06-13). And verify/install have no meaningful percentage and are
        # quick, so a bar pinned at 100% looked frozen ("hanging on 100%",
        # 2026-06-27) — switch to a MOVING busy indicator so it reads "working".
        if not _is_download_phase(message):
            dialog.setCancelButton(None)
            self._install_post_download = True
            dialog.setRange(0, 0)

    def _on_update_install_finished(self, ok: bool, payload: str) -> None:
        """Close the progress dialog; restart into the new version on success.

        Runs on the GUI thread (``finished`` is connected to this bound method,
        so Qt queues it there), which is what makes building the QMessageBox
        below safe — doing it on the worker thread is what froze the window.
        """
        from platterpus import appimage_integration as ai

        dialog = self._install_dialog
        self._install_dialog = None
        self._install_post_download = False
        if dialog is not None:
            try:
                dialog.close()
            except Exception:  # noqa: BLE001 — closing UI must never block the flow
                pass
        self._install_worker = None
        self._install_thread = None
        if not ok:
            QMessageBox.warning(
                self,
                "Update failed",
                f"The update wasn't installed: {payload}\n\n"
                "Nothing was changed — you can keep using this version or "
                "download the new one from the releases page.",
            )
            return
        new_path = Path(payload)
        # Point the menu/desktop entries at the new file (best-effort —
        # normally a no-op since the path is the same canonical location).
        try:
            ai.integrate(new_path)
        except Exception:  # noqa: BLE001 — the update itself succeeded
            log.exception("post-update re-integration failed")
        choice = QMessageBox.question(
            self,
            "Update installed",
            "The new version is installed. Restart Platterpus now?\n\n"
            "Heads-up: the first launch of a new version unpacks itself, so "
            "the window can take 20–30 seconds to reappear — that's normal. "
            "Give it a moment before reopening it yourself.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if choice == QMessageBox.StandardButton.Yes:
            import subprocess

            # Log the relaunch explicitly. The new AppImage cold-extracts on its
            # first run (a 230 MB file → the window can take 20-30s to appear),
            # which reads as "it didn't reopen." Logging the spawn here makes the
            # log unambiguous about whether WE relaunched it vs. the user did
            # (real-user question, 2026-06-27), and lets us catch a spawn that
            # fails instead of silently closing into nothing.
            log.info("relaunching into the new version: %s", new_path)
            try:
                subprocess.Popen(  # noqa: S603 — our own verified binary
                    [str(new_path)], start_new_session=True, env=_relaunch_env()
                )
            except OSError as exc:
                log.exception("relaunch failed")
                QMessageBox.information(
                    self,
                    "Update installed",
                    "The update is installed, but I couldn't relaunch the app "
                    f"automatically ({exc}). Please reopen Platterpus from your "
                    "menu or ~/Applications.",
                )
                return  # leave this window open so the user isn't left with nothing
            # The new process now owns everything; this one is being replaced, so a
            # graceful Qt teardown buys nothing and is the only thing that can
            # abort. `self.close()` runs closeEvent (which stops the workers it
            # can and abandons the ones blocked in a container exec), and then we
            # leave immediately rather than letting `app.exec()` return and
            # interpreter shutdown destroy a live QThread — the v0.5.8 SIGABRT.
            # See `platterpus.hard_exit` for the full mechanism.
            #
            # closeEvent still runs first, deliberately: it is what stops the
            # in-container reader and flushes the rip state. We skip *teardown*,
            # not *shutdown*.
            self.close()
            hard_exit.exit_without_teardown(0, "relaunching into the updated version")
