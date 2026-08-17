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
    # is not, and that asymmetry is why this is a separate action rather than a
    # second line in the dialog above. Installing a fork build our handshake record
    # has not approved makes every subsequent rip report its ripper as `unapproved`
    # — correctly — so this flow's job is to say what is available and what taking
    # it costs, and then stop. It installs nothing. See `deps/ripper_offer.py`.

    def _on_check_ripper_updates(self) -> None:
        """Help → Check for cyanrip updates: ask the fork's release manifest.

        Off-thread for the same reason every other network call here is: a stalled
        connection must not freeze the window for the whole timeout.
        """
        if self._ripper_update_thread is not None:  # a check is already running
            return
        from platterpus.workers import start_worker_thread
        from platterpus.workers.ripper_update_worker import RipperUpdateWorker

        # Both values are read HERE, on the GUI thread, and handed over as plain
        # data — the worker must not touch the config or probe a binary off-thread.
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
        """Show the verdict. Never installs — see the section comment above."""
        from platterpus.deps.ripper_offer import OFFER_AVAILABLE

        self._ripper_update_worker = None
        self._ripper_update_thread = None

        detail = str(
            getattr(offer, "detail", "") or "Couldn't check for a newer ripper."
        )
        verdict = str(getattr(offer, "verdict", "") or "")
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
            if verdict == OFFER_AVAILABLE
            else QMessageBox.Icon.NoIcon
        )
        box.exec()

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
