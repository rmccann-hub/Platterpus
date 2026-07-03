"""Dependency-check UI for the main window.

Extracted from ``main_window`` (2026-06-13 modularization, KDD-19) as a
mixin so the GUI side of the dependency self-management subsystem lives in
one focused file while its methods stay reachable as ``window._x`` (tests +
Qt signal wiring rely on that). ``MainWindow`` inherits this; methods run
with ``self`` being the window.

This is *only* the GUI glue: it probes via the injected ``DependencyManager``'s
``check_all`` (off the GUI thread) and then, for anything missing, resolves it on
the GUI thread through ``_resolve_missing_unified`` — the single resolution path
(a setup-wizard tier for container tools, a live-progress ``PendingInstallsDialog``
for packaged installs, and a manual-search dialog otherwise). All the "is it
present / what version" logic lives in ``deps/`` (Critical Rule #6) — this file
must never grow an ad-hoc ``shutil.which`` check.

Contract this mixin expects from the host window (set in
``MainWindow.__init__``): ``self._config``, ``self._dependency_manager``;
``self`` is a ``QWidget`` (dialog parent); and the cross-mixin method
``self.open_host_setup_dialog`` (ProvisioningMixin).
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QMessageBox

from platterpus.deps.resolvers import (
    AutoInstaller,
    InstallResult,
    MissingItem,
)
from platterpus.deps.version import format_version
from platterpus.ui.dialogs.manual_install import ManualInstallDialog
from platterpus.ui.dialogs.pending_installs import PendingInstallsDialog


def _optional_purpose(item: MissingItem) -> str:
    """A short "what it does for you" for an optional dependency.

    Pulled from the spec's own `description`, which starts with the literal
    "Optional." marker — we drop that (the dialog already says it's optional)
    and take the first sentence, so the user reads the *effect* rather than a
    package blurb. Falls back to the display name if there's no description.
    """
    text = (getattr(item.spec, "description", "") or "").strip()
    # Strip the leading "Optional." / "Optional —" marker the specs use.
    for prefix in ("Optional.", "Optional —", "Optional -", "Optional"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    if not text:
        return "optional extra"
    # First sentence only — the descriptions are written sentence-first.
    sentence = text.split(". ", 1)[0].rstrip(".")
    return sentence or "optional extra"


class DependencyMixin:
    """Run the dependency subsystem with GUI-backed resolvers + summary."""

    def _on_check_dependencies(self) -> None:
        """Run the dependency subsystem with GUI-backed resolvers.

        Runs the probe OFF the GUI thread (Tools → Check dependencies and the
        Settings button both land here): ``check_all()`` shells out per
        dependency and enters the Distrobox container, which is slow on a cold
        start and would otherwise freeze the window. The summary popup shows when
        the probe finishes.
        """
        self.run_dependency_check_async(show_summary=True)

    def run_dependency_check(self, show_summary: bool = True) -> None:
        """Probe (check_all) then resolve any missing deps, **synchronously**.

        Retained for tests (which drive it directly and assert on the result).
        Every in-app entry point uses `run_dependency_check_async` instead so a
        cold-container probe can't freeze the window — `check_all()` shells out
        per dependency and enters the Distrobox container.
        """
        gui_manager = self._build_gui_dependency_manager()
        self._apply_dependency_report(
            gui_manager, gui_manager.check_all(), show_summary=show_summary
        )

    def run_dependency_check_async(self, show_summary: bool = False) -> None:
        """Dependency check that probes **off the GUI thread**.

        `check_all()` shells out per dependency, and the cyanrip probe enters
        the Distrobox container — slow on a cold start. Running it on the GUI
        thread froze the window; here the probing runs on a worker and only the
        *result* is applied on the GUI thread (where the resolver dialogs must
        live). `show_summary` controls the end-of-check popup (True for the
        user-clicked Tools/Settings paths; False for the silent launch check).
        One check at a time.
        """
        if self._dep_check_thread is not None:  # a check is already running
            return
        from platterpus.workers import start_worker_thread
        from platterpus.workers.dependency_worker import DependencyCheckWorker

        self._dep_check_show_summary = show_summary
        gui_manager = self._build_gui_dependency_manager()
        # Stash the manager so `finished` can connect to a BOUND METHOD rather
        # than a lambda. This matters for correctness, not just style: a lambda
        # has no QObject context, so Qt connects it as a DirectConnection and
        # runs it on the *worker* thread when `finished` is emitted there — and
        # the handler builds resolver dialogs / touches widgets, which must
        # happen on the GUI thread. A bound method of this window (a GUI-thread
        # QObject) is delivered as a queued connection, on the GUI thread.
        self._dep_check_manager = gui_manager
        self._dep_check_worker = DependencyCheckWorker(gui_manager)
        self._dep_check_thread = QThread(self)
        self._dep_check_worker.finished.connect(self._on_dependency_check_done)
        start_worker_thread(
            self._dep_check_worker, self._dep_check_thread, self._dep_check_worker.run
        )

    def _on_dependency_check_done(self, report: object) -> None:
        """Worker finished probing — apply the report on the GUI thread.

        Runs on the GUI thread (queued from the worker's `finished` signal),
        so it's safe to build resolver dialogs here.
        """
        gui_manager = self._dep_check_manager
        show_summary = self._dep_check_show_summary
        self._dep_check_worker = None
        self._dep_check_thread = None
        self._dep_check_manager = None
        self._dep_check_show_summary = False
        # Stash the launch-time probe so the rip report's
        # environment.dependencies can record each tool's version + location
        # WITHOUT re-probing on the GUI thread (a probe enters the Distrobox
        # container — the exact freeze the never-block rule forbids). A shallow
        # copy, because _apply_dependency_report below filters report.missing to
        # required-only; the copy keeps the full picture (incl. optional deps
        # like Picard). Guarded so a non-dataclass test double doesn't break.
        if report is not None:
            from dataclasses import replace

            try:
                self._last_dependency_report = replace(report)
            except TypeError:
                self._last_dependency_report = report
        # `show_summary` is True for the user-clicked Tools/Settings check and
        # False for the silent launch check; resolver dialogs surface for
        # genuinely-missing deps regardless.
        self._apply_dependency_report(gui_manager, report, show_summary=show_summary)

    def _build_gui_dependency_manager(self) -> object:
        """A DependencyManager over the injected manager's registry.

        The manager now only *probes* (check_all) — resolution is done by
        `_resolve_missing_unified` on the GUI thread. We reuse the injected
        manager's spec list so the check sees exactly the deps the app cares
        about."""
        from platterpus.deps.manager import DependencyManager

        return DependencyManager(
            specs=self._dependency_manager._specs,  # type: ignore[attr-defined]
        )

    def _apply_dependency_report(
        self, gui_manager: object, report: object, show_summary: bool
    ) -> None:
        """GUI-thread half: set optional deps aside, resolve the required
        missing ones (dialogs), then show the summary. `report` is None only
        if the off-thread probe crashed — then this is a no-op (already logged)."""
        if report is None:
            return
        # Optional deps (e.g. Picard) shouldn't nag at launch or count as a
        # problem — set them aside so only required deps drive resolution.
        optional_missing = [
            item for item in report.missing if getattr(item.spec, "optional", False)
        ]
        report.missing = [
            item for item in report.missing if not getattr(item.spec, "optional", False)
        ]
        # Snapshot *before* resolving: _resolve_missing_unified leaves
        # report.missing in place and only appends results, so we'd lose the
        # "was anything required actually wrong?" signal otherwise.
        had_required_missing = bool(report.missing)
        if had_required_missing:
            self._resolve_missing_unified(report)

        # Healthy common case on a user-initiated check: everything *required*
        # is present and only optional extras are absent. Show ONE outcome-first
        # offer instead of an info popup ("0 missing/needs-attention") chased by
        # a separate "install optional?" question — that back-to-back pair read
        # as a contradiction to a real user on 0.4.2 ("it told me 0 dependencies
        # then gave me this option"). Launch-time checks (show_summary=False)
        # stay silent so optional deps never nag.
        if show_summary and optional_missing and not had_required_missing:
            self._offer_optional_install(
                gui_manager, optional_missing, required_all_ok=True
            )
            return

        if show_summary or had_required_missing:
            self._show_dep_summary(report, optional_missing=optional_missing)
        # When required deps also needed attention we still show the full summary
        # first (above), then offer the optional extras so the user has an in-app
        # way to add Picard/flac.
        if optional_missing and show_summary:
            self._offer_optional_install(gui_manager, optional_missing)

    def _offer_optional_install(
        self,
        gui_manager: object,
        optional_missing: list[MissingItem],
        required_all_ok: bool = False,
    ) -> None:
        """Offer to install the optional, not-installed deps on demand.

        `required_all_ok` leads with the reassurance that nothing is *wrong* —
        the only thing absent is optional. That matters because this dialog can
        be the first thing the user sees after a clean check, and "install X?"
        with no context reads like a problem (the 0.4.2 "0 dependencies then it
        gave me this option" confusion). Each component is listed with *what it
        does for you*, taken from its spec, so the choice is informed.

        Routes each through the SAME unified dialog the required deps use, so
        there's no second install path (Critical Rule #6): Picard auto-installs,
        and flac/ffmpeg — `from_setup_wizard` tools — install via the one-click
        container wizard. After resolving, a nudge to re-check (the installers
        give their own feedback).
        """
        from platterpus.deps.manager import DependencyReport

        # One "• Name — what it's for" line per component, so the user decides
        # on the *effect*, not the package name (ux-design-principles #4).
        bullets = "\n".join(
            f"• {item.spec.display_name} — {_optional_purpose(item)}"
            for item in optional_missing
        )
        if len(optional_missing) > 1:
            plural = "these optional extras aren't"
        else:
            plural = "this optional extra isn't"
        if required_all_ok:
            lead = (
                "✓ Everything required is installed — you're ready to rip.\n\n"
                f"Just so you know, {plural} installed. None of it is needed to "
                f"rip:\n\n{bullets}\n\nInstall it now? (You can always do this "
                "later from Tools → Settings → Check dependencies.)"
            )
        else:
            lead = (
                f"For reference, {plural} installed — none of it is required to "
                f"rip:\n\n{bullets}\n\nInstall it now?"
            )
        choice = QMessageBox.question(
            self,
            "Optional components",
            lead,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return
        opt_report = DependencyReport(missing=list(optional_missing))
        self._resolve_missing_unified(opt_report)
        QMessageBox.information(
            self,
            "Optional components",
            "Done. Re-run Tools → Check dependencies to confirm what's now "
            "installed. (Picard and flac take effect immediately; if flac was "
            "set up via the container wizard, it's ready now too.)",
        )

    def _resolve_missing_unified(self, report: object) -> None:
        """Resolve every missing dependency through **one** dialog (items 2+6).

        This replaces the old per-tier fan-out — a consent box for auto deps,
        a separate queued dialog, and *one manual dialog per item* — which is
        what produced the "two popups" the maintainer hit on a fresh install
        (whipper + metaflac each opened their own dialog). Now every installable
        missing dep is a single checkbox row (ticked by default) in one
        `PendingInstallsDialog`; the dialog installs the ticked rows inline with
        per-row progress, and its dismiss button stays greyed out until the
        install actually finishes (`set_install_phase_active` disables Cancel;
        `show_close_button` reveals Close at the end).

        The install machinery is reused, not duplicated (Critical Rule #6), but
        it splits by *where the install has to run*:

        * `from_setup_wizard` tools (cyanrip, flac, metaflac) install through the
          host-setup wizard, which is a **GUI** dialog with its own gated,
          off-thread progress — so it's opened here on the GUI thread, once (it
          installs the whole container stack in one run), and each tool is then
          re-probed for its result. These never go through the PendingInstalls
          loop, because that loop now runs off the GUI thread and must not open
          a dialog from a worker thread.
        * packaged deps (`install_command`, e.g. Picard) are a plain subprocess
          install, so they go through the `PendingInstallsDialog`, which runs the
          install **off the GUI thread** (the fix for the 0.4.2 freeze where a
          Picard Flatpak install on the GUI thread locked the whole window).

        Deps that genuinely can't be installed from here (a missing bundled
        package → "reinstall the AppImage") fall back to the per-item manual
        dialog. Outcomes land in `report.install_results`.
        """
        missing = list(getattr(report, "missing", []))
        wizard_items = [
            item for item in missing if getattr(item.spec, "from_setup_wizard", False)
        ]
        command_items = [
            item
            for item in missing
            if item not in wizard_items and item.spec.install_command is not None
        ]
        manual_only = [
            item
            for item in missing
            if item not in wizard_items and item not in command_items
        ]

        # 1. Container tools → the setup wizard (GUI thread, internally async).
        #    Open it once; it installs them all, then re-probe each for its result
        #    OFF the GUI thread (BUG-9) — probe() shells into the Distrobox
        #    container, which can take up to minutes on a cold container.
        if wizard_items:
            self.open_host_setup_dialog()
            report.install_results.extend(self._reprobe_wizard_items(wizard_items))

        # 2. Packaged deps → the off-GUI-thread PendingInstallsDialog.
        if command_items:
            dialog = PendingInstallsDialog(
                command_items, install_one=self._make_install_one(), parent=self
            )
            dialog.exec()
            report.install_results.extend(dialog.results())

        # Anything not installable from here still gets its own manual dialog
        # (rare: a broken bundled package, where the fix is reinstalling).
        for item in manual_only:
            self._gui_manual_dialog(item)
            report.install_results.append(
                InstallResult(
                    spec=item.spec,
                    success=False,
                    message=(
                        f"manual install required — search: {item.spec.search_string}"
                    ),
                )
            )

    def _reprobe_wizard_items(self, items: list[MissingItem]) -> list[InstallResult]:
        """Re-probe each wizard item's spec OFF the GUI thread (BUG-9).

        ``spec.probe()`` for a container tool shells into the Distrobox container
        (a subprocess that can take up to *minutes* on a cold container), so
        running it inline after the setup wizard froze the window — the exact
        never-block-the-GUI-thread rule this project keeps re-learning. A daemon
        thread does the probing while a nested ``QEventLoop`` keeps the window
        responsive; a ``QTimer`` polls for completion and quits the loop. Returns
        the per-item :class:`InstallResult` list (present-and-current → success).
        """
        from PySide6.QtCore import QEventLoop, QTimer

        from platterpus.deps.version import meets_minimum

        results: list[InstallResult] = []
        done = threading.Event()

        def work() -> None:
            try:
                for item in items:
                    probe = item.spec.probe()
                    ok = probe.present and meets_minimum(
                        probe.version, item.spec.min_version
                    )
                    results.append(
                        InstallResult(
                            spec=item.spec,
                            success=ok,
                            message=(
                                "installed via setup wizard"
                                if ok
                                else "still missing after setup — re-run the wizard"
                            ),
                        )
                    )
            finally:
                done.set()

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        # Spin a nested event loop so the window keeps repainting while we wait;
        # the timer quits it as soon as the probe thread signals completion.
        loop = QEventLoop()
        timer = QTimer()
        timer.setInterval(30)
        timer.timeout.connect(lambda: loop.quit() if done.is_set() else None)
        timer.start()
        loop.exec()
        timer.stop()
        thread.join(timeout=5)  # already finished (done is set) — instant
        return results

    def _make_install_one(self) -> Callable[[MissingItem], InstallResult]:
        """Build the per-item installer the PendingInstallsDialog drives.

        Reuses AutoInstaller's install machinery (subprocess run + error
        handling) with an always-yes consent — the user already consented
        per-item via the dialog's checkboxes.
        """
        installer = AutoInstaller(consent=lambda _: True)

        def install_one(item: MissingItem) -> InstallResult:
            results = installer.resolve([item])
            if results:
                return results[0]
            # AutoInstaller skips items with no install_command; a queued-tier
            # item should always have one, but never return an empty list.
            return InstallResult(
                spec=item.spec,
                success=False,
                message="no install command available",
            )

        return install_one

    def _gui_manual_dialog(self, item: MissingItem) -> None:
        # For tools the setup wizard provides (whipper/metaflac/flac), hand the
        # dialog a callback so it can offer the one-click wizard instead of only
        # a copyable search string — the user shouldn't have to paste a query to
        # install something the app installs itself (Tools → Set up Platterpus…).
        on_setup_wizard = (
            self.open_host_setup_dialog
            if getattr(item.spec, "from_setup_wizard", False)
            else None
        )
        dialog = ManualInstallDialog(
            item.spec, item.probe, self, on_setup_wizard=on_setup_wizard
        )
        dialog.exec()

    def _show_dep_summary(
        self, report: object, optional_missing: list[MissingItem] | None = None
    ) -> None:
        """Post-check summary popup with install-failure detail when present.

        The popup format:
            "<ok_count> ok, <missing_count> missing/needs-attention."
            "Installed: <name> <version>, …"      ← when any deps are OK
            "Optional (not installed): <names>"   ← only when present
            (blank line)
            "Install failures:"           ← only when failures exist
            "  - <dep>: <error message>"  ← one per failure
        """
        ok_specs = getattr(report, "ok", [])
        ok_count = len(ok_specs)
        missing_count = len(getattr(report, "missing", []))
        ok_versions = getattr(report, "ok_versions", {}) or {}
        # Collect real install failures (not user declines — those are
        # surfaced via the dialog the user already saw).
        install_results = getattr(report, "install_results", [])
        failures = [
            r
            for r in install_results
            if not r.success and not getattr(r, "user_declined", False)
        ]

        message = f"{ok_count} ok, {missing_count} missing/needs-attention."
        # Stamp the detected version next to each OK dep so the user knows
        # exactly what's installed (reproducibility), not just that it's there.
        if ok_specs:
            installed = ", ".join(
                f"{spec.display_name} {format_version(ok_versions.get(spec.dep_id))}"
                for spec in ok_specs
            )
            message += f"\nInstalled: {installed}."
        if optional_missing:
            names = ", ".join(item.spec.display_name for item in optional_missing)
            message += f"\nOptional (not installed): {names}."
        if failures:
            failure_lines = "\n".join(
                f"  • {r.spec.display_name}: {r.message}" for r in failures
            )
            message = (
                f"{message}\n\nInstall failures:\n{failure_lines}\n\n"
                f"Full output is in ~/.local/share/platterpus/log.txt."
            )

        QMessageBox.information(self, "Dependency check complete", message)
