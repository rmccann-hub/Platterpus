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

import logging
import threading
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QMainWindow, QMessageBox

from platterpus.deps import manager as dep_manager
from platterpus.deps.resolvers import (
    AutoInstaller,
    InstallResult,
    MissingItem,
)
from platterpus.deps.version import format_version
from platterpus.paths import LOG_PATH
from platterpus.ui import dependency_check_status as dep_status
from platterpus.ui.accessibility import announce
from platterpus.ui.dialogs.manual_install import ManualInstallDialog
from platterpus.ui.dialogs.pending_installs import PendingInstallsDialog
from platterpus.ui.main_window_shared import MainWindowShared

if TYPE_CHECKING:
    from platterpus.deps.build_notes import BuildNote
    from platterpus.deps.manager import DependencyManager, DependencyReport
    from platterpus.deps.registry import DependencySpec


log = logging.getLogger(__name__)

#: How long to wait before re-offering a dependency report that arrived while a
#: dialog had the floor. Short enough that a user who dismisses the blocking box
#: sees the result as part of the same moment, long enough not to spin.
_DEP_RESOLVE_RETRY_MS: int = 750

#: How many times to re-offer before giving up **loudly**. 40 x 750 ms is 30
#: seconds. The bound is the point: a modal the user never closes must not leave
#: a timer firing for the life of the process, and a dependency dialog that
#: surfaces minutes later is attached to nothing the user is still doing.
_DEP_RESOLVE_MAX_DEFERRALS: int = 40

#: How long past the check's own deadline (`deps.manager.CHECK_DEADLINE_S`) the
#: window waits before saying the check is overdue. The BACKSTOP, and it needs no
#: cooperation from the check: every probe the registry has today is capped by the
#: deadline, so this only speaks if a probe ignores it — but when one does, the
#: user is told on screen rather than left looking at "Checking…" forever. The
#: grace covers the kill itself: a SIGKILLed child can take up to
#: `killable.REAP_TIMEOUT_S` (5 s) to be reaped.
_OVERDUE_GRACE_S: float = 15.0


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


def _installed_line(
    spec: DependencySpec,
    ok_versions: Mapping[str, tuple[int, ...] | None],
    build_notes: Mapping[str, BuildNote],
) -> str:
    """One entry in the summary's "Installed:" list.

    Two shapes, and which one you get is the point of this function:

    - **A dep with a build note** reports the tool's *own* version string and its
      build tag — ``cyanrip 0.9.4-rc1+platterpus.5-beta.5 (the Platterpus fork,
      build platterpus-fork-g9048082)``. This line used to read
      ``cyanrip 0.9.4 (the Platterpus fork)``: every word true, and it named
      neither the pre-release nor the commit, on the one surface a user actually
      reads. Both facts were already in the object passed in here — see
      :class:`~platterpus.deps.build_notes.BuildNote`.
    - **Everything else** reports the parsed int-triple, which is all we have and
      all those tools need.

    Kept a module-level pure function rather than an inline comprehension so the
    formatting is unit-testable without constructing a window — the same reason
    the validators live in their own module.
    """
    note = build_notes.get(spec.dep_id)
    if note is not None:
        return note.identity_line(spec.display_name)
    return f"{spec.display_name} {format_version(ok_versions.get(spec.dep_id))}"


class DependencyMixin(MainWindowShared):
    """Run the dependency subsystem with GUI-backed resolvers + summary."""

    #: How many times the current report has been held back because a dialog had
    #: the floor. Reset the moment it is delivered, so the budget is per-report
    #: rather than per-session — a second check hours later starts fresh.
    _dep_resolve_deferrals: int = 0
    #: The status-bar sentence the last check landed with, so a result that had to
    #: wait for another dialog can put it back when it is finally shown.
    _dep_check_outcome: str = ""
    #: Whether the running check has put its overdue warning on the status bar.
    #: Such a check owes the status bar its outcome even when it is a silent one,
    #: or the warning would outlive the check it describes.
    _dep_check_overdue_said: bool = False

    def _on_check_dependencies(self) -> None:
        """Run the dependency subsystem with GUI-backed resolvers.

        Runs the probe OFF the GUI thread (Setup & Updates → Check dependencies
        and the launch-time check both land here): ``check_all()`` shells out per
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
        One check at a time — and a request while one runs is ANSWERED, not
        dropped: see `_on_check_requested_while_running`.
        """
        if self._dep_check_thread is not None:  # a check is already running
            if show_summary:
                self._on_check_requested_while_running()
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
        self._on_dependency_check_started(user_requested=show_summary)

    def _on_dependency_check_started(self, *, user_requested: bool) -> None:
        """Say a check is running, and arm the backstop that says if it overruns.

        A check the user asked for is announced on the status bar and greys the
        Setup & Updates button; before 2026-09-28 nothing on screen changed until
        the result arrived, which on a cold container is a minute of a button
        that appears to do nothing. A check nobody asked for (the launch check)
        only updates an open Setup & Updates window's line, so it never nags.
        """
        deadline_s = dep_manager.CHECK_DEADLINE_S
        message = dep_status.running_message(deadline_s)
        if user_requested:
            self._show_dependency_status(message)
        self._show_dependency_check_in_setup_center()
        # The backstop. `self` as the timer's context object means Qt drops the
        # call if the window is destroyed first, so it never reaches a dead
        # widget; the worker identity check means a check that landed (or was
        # replaced) in the meantime is never reported as overdue.
        from PySide6.QtCore import QTimer

        worker = self._dep_check_worker
        waited = deadline_s + _OVERDUE_GRACE_S
        QTimer.singleShot(
            int(waited * 1000),
            self,
            lambda: self._warn_if_check_overdue(worker, waited),
        )

    def _warn_if_check_overdue(self, worker: object, waited: float) -> None:
        """Tell the user a check is still running long past its deadline."""
        if worker is None or self._dep_check_worker is not worker:
            return  # that check landed, or another replaced it: nothing overdue
        thread = self._dep_check_thread
        if thread is None or not thread.isRunning():
            return  # stopped without reporting (closing the window cancels it)
        log.error(
            "dependency check still running %.0f s after it started, past its own "
            "deadline — a probe is not honouring it",
            waited,
        )
        self._dep_check_overdue_said = True
        self._show_dependency_status(dep_status.overdue_message(waited))

    def _on_check_requested_while_running(self) -> None:
        """The user asked for a check while one runs: say so, and show its result.

        **Never a second probe.** Two checks would race for one container and
        for the one shared `VERSION_PROBE` slot, whose kill can only name one
        child. So the running check is reused — and if it was started silently
        (the launch check, About's Check again), it is UPGRADED so its summary
        is shown when it lands, because the user has now asked for exactly that.
        Before 2026-09-28 this returned without a word, so a second click on a
        button that already looked dead confirmed that it was.
        """
        upgraded = not self._dep_check_show_summary
        self._dep_check_show_summary = True
        log.info(
            "dependency check requested while one is running — not starting a "
            "second; %s",
            "the running check will now show its summary"
            if upgraded
            else "its summary was already due",
        )
        self._show_dependency_status(dep_status.already_running_message())
        self._show_dependency_check_in_setup_center()

    def _show_dependency_check_in_setup_center(self) -> None:
        """Show the check in flight, if any, on an open Setup & Updates window.

        Called when a check starts, when a click upgrades one, and when the
        window is OPENED — so a window opened during the launch check says
        "Checking…" rather than whatever the last finished check said. The
        button is greyed only for a check whose summary is due, since clicking it
        during a silent check is how the user asks to see that check's result.
        """
        center = self._setup_center
        if center is None or self._dep_check_thread is None:
            return
        center.show_dependency_check_running(
            dep_status.running_message(dep_manager.CHECK_DEADLINE_S),
            busy=self._dep_check_show_summary,
        )

    def _show_dependency_status(self, text: str) -> None:
        """Put a dependency-check sentence on the status bar, and say it.

        Timestamped like the rip status line (``HH:MM:SS · …``), so a message
        that stops changing shows a time that stops changing. No timeout: it
        stays until the next dependency sentence replaces it, because a message
        that vanished before the user looked would be the silence it replaces.
        The status bar paints plain text, so a tool name cannot be read as
        markup. Logged too, so a bug report carries what the user was shown.
        """
        log.info("dependency status: %s", text)
        if not isinstance(self, QMainWindow):
            return  # a test double; the log line above is the whole record
        bar = self.statusBar()
        stamped = f"{datetime.now():%H:%M:%S} · {text}"
        bar.showMessage(stamped)
        # A status bar clips a long line at the window's edge. The sentence that
        # names what was not checked is the long one, so the whole of it is kept
        # reachable on hover rather than cut off where the window happens to end.
        bar.setToolTip(stamped)
        announce(bar, text)

    def _recheck_dependencies_for(
        self, on_done: Callable[[], None]
    ) -> Callable[[], None]:
        """Run the dependency check and call ``on_done`` once when it lands.

        For Help → About's **Check again**. The check is the app's own, off the
        GUI thread; if one is already running, ``on_done`` waits for that one
        rather than starting a second. Returns a function that forgets
        ``on_done``, which the dialog calls when it closes, so a check that lands
        after the dialog is gone never reaches a deleted widget.
        """
        self._dep_check_listeners.append(on_done)
        self.run_dependency_check_async(show_summary=False)

        def forget() -> None:
            if on_done in self._dep_check_listeners:
                self._dep_check_listeners.remove(on_done)

        return forget

    def _on_dependency_check_done(self, report: DependencyReport | None) -> None:
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
            # And into the subsystem's own store, which the Diagnostics dialog
            # reads — it has no window to ask, and asking `environment_report()`
            # got it None forever (see deps/manager.remember_report).
            from platterpus.deps import manager as _dep_manager

            _dep_manager.remember_report(self._last_dependency_report)
        # Whoever asked to be told (About's "Check again"), told once, BEFORE the
        # report is applied: applying it can open a resolver dialog, and the
        # listener only re-reads the stored report.
        listeners, self._dep_check_listeners = self._dep_check_listeners, []
        for listener in listeners:
            try:
                listener()
            except Exception:  # noqa: BLE001 — one listener must not stop the rest
                log.exception("a dependency-check listener raised")
        self._on_dependency_check_landed(report, show_summary=show_summary)
        # `show_summary` is True for the user-clicked Tools/Settings check and
        # False for the silent launch check; resolver dialogs surface for
        # genuinely-missing deps regardless.
        self._apply_dependency_report(gui_manager, report, show_summary=show_summary)

    def _on_dependency_check_landed(
        self, report: DependencyReport | None, *, show_summary: bool
    ) -> None:
        """Replace "Checking…" with the outcome, BEFORE any dialog can open.

        Before the report is applied, because applying it can hold it back for
        another dialog (`_defer_if_floor_is_busy`) or open resolver dialogs —
        and the running message must not outlive the check it describes. The
        Setup & Updates line always shows the result; the status bar shows it
        for a check the user asked for, and for a silent check only when that
        check did not finish, since then the ripper's state is unknown.
        """
        outcome = dep_status.outcome_message(report)
        center = self._setup_center
        if center is not None:
            center.show_dependency_check_finished(
                report, failure=outcome if report is None else ""
            )
        overdue_said, self._dep_check_overdue_said = self._dep_check_overdue_said, False
        if show_summary or overdue_said:
            self._dep_check_outcome = outcome
            self._show_dependency_status(outcome)
        elif report is not None and dep_manager.unchecked_names(report):
            self._show_dependency_status(
                dep_status.incomplete_background_message(report)
            )

    def _build_gui_dependency_manager(self) -> DependencyManager:
        """A DependencyManager over the injected manager's registry.

        The manager now only *probes* (check_all) — resolution is done by
        `_resolve_missing_unified` on the GUI thread. We reuse the injected
        manager's spec list so the check sees exactly the deps the app cares
        about."""
        from platterpus.deps.manager import DependencyManager

        return DependencyManager(
            specs=self._dependency_manager._specs,
        )

    def _apply_dependency_report(
        self, gui_manager: object, report: DependencyReport | None, show_summary: bool
    ) -> None:
        """GUI-thread half: set optional deps aside, resolve the required
        missing ones (dialogs), then show the summary.

        ``report`` is None only if the off-thread probe crashed. That used to be a
        silent ``return``: a user who chose **Check dependencies** got no
        window, no message and no change — indistinguishable from a dead menu item —
        with the traceback going only to a log file that is INFO-only by default. A
        user-initiated action must never no-op silently, so when the user asked for
        this check we now say it failed and where to look.
        """
        if report is None:
            if show_summary:
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.warning(
                    self,
                    "Couldn't check dependencies",
                    "The dependency check stopped with an unexpected error, so "
                    "nothing could be reported about the tools Platterpus needs.\n\n"
                    "This does not mean a tool is missing — it means the check "
                    "itself failed.\n\n"
                    f"The error and its traceback are in:\n{LOG_PATH}",
                )
            return
        # Optional deps (e.g. Picard) shouldn't nag at launch or count as a
        # problem — set them aside so only required deps drive resolution.
        optional_missing = [
            item for item in report.missing if getattr(item.spec, "optional", False)
        ]
        required_missing = [
            item for item in report.missing if not getattr(item.spec, "optional", False)
        ]
        # Decided BEFORE `report.missing` is narrowed below, and the narrowing
        # happens only once the report is actually being delivered. It used to be
        # narrowed first, so a report held back for another dialog came back with
        # its optional tools already gone — and the summary shown after the wait
        # silently dropped its "Optional (not installed)" line.
        had_required_missing = bool(required_missing)
        # A check that stopped part-way (`report.unchecked`) must not be summarised
        # as "everything required is installed": it did not look at everything.
        complete = not dep_manager.unchecked_names(report)
        # **NOTHING BELOW MAY OPEN A DIALOG WHILE SOMETHING ELSE HAS THE FLOOR.**
        #
        # This method runs from `_on_dependency_check_done`, a QUEUED SLOT off the
        # probe worker's `finished` signal — so Qt delivers it on the GUI thread
        # inside whatever nested `exec()` loop happens to be spinning. At launch
        # that is routinely the first-run *"Set up Platterpus?"* question, because
        # `singleShot(0)` opens it while the probe is still entering a cold
        # container. `_resolve_missing_unified` then opens the setup wizard for its
        # container tools, stacked on top of a box the user has not answered.
        #
        # `_modal_floor_blocker` is the project's existing answer to *"may I raise
        # a dialog right now?"*, and its own docstring predicted this exact failure
        # — *"answering both runs the install pipeline twice"*. It was written for
        # the cyanrip check and applied only there, at one of the three launch-time
        # surfaces that raise modals. `docs/testing.md` §5.o: enforce a rule across
        # the codebase, not at the place it was learned.
        #
        # **The NARROW half of it**, and the distinction matters here more than
        # anywhere. The wide test also refuses when the window is not visible —
        # right for an offer nobody asked for, wrong for this, which resolves a
        # MISSING REQUIRED DEPENDENCY and must not be dropped because the window
        # had not been shown yet when a launch-time probe returned.
        #
        # **DEFERRED, NEVER DROPPED.** A missing required dependency is the thing
        # that stops the app working, so skipping its resolution silently would be
        # the no-op-failure shape this project forbids — and worse than the stacking
        # it avoids. We re-deliver once the floor is free, bounded, and say so in
        # the log either way. The bound matters: a modal a user never closes must
        # not leave a timer firing for the life of the process.
        if (had_required_missing or show_summary) and self._defer_if_floor_is_busy(
            gui_manager, report, show_summary
        ):
            return
        # Narrowed only now, once the report is really being delivered (see the
        # note where `had_required_missing` is set): resolution and the summary
        # work from the required tools, and the optional ones travel separately.
        report.missing = required_missing
        if had_required_missing:
            self._resolve_missing_unified(report)

        # Healthy common case on a user-initiated check: everything *required*
        # is present and only optional extras are absent. Show ONE outcome-first
        # offer instead of an info popup ("0 missing/needs-attention") chased by
        # a separate "install optional?" question — that back-to-back pair read
        # as a contradiction to a real user on 0.4.2 ("it told me 0 dependencies
        # then gave me this option"). Launch-time checks (show_summary=False)
        # stay silent so optional deps never nag.
        #
        # NOT for an incomplete check: "Everything required is installed" is the
        # one sentence a check that stopped part-way cannot say, so it gets the
        # full summary, which names what was not checked.
        if show_summary and optional_missing and not had_required_missing and complete:
            self._offer_optional_install(
                gui_manager, optional_missing, required_all_ok=True
            )
            return

        if show_summary or had_required_missing:
            self._show_dep_summary(report, optional_missing=optional_missing)
        # When required deps also needed attention we still show the full summary
        # first (above), then offer the optional extras so the user has an in-app
        # way to add Picard/flac. Not after an incomplete check: the right next
        # step there is to check again, and a second dialog would bury that.
        if optional_missing and show_summary and complete:
            self._offer_optional_install(gui_manager, optional_missing)

    def _defer_if_floor_is_busy(
        self, gui_manager: object, report: DependencyReport, show_summary: bool
    ) -> bool:
        """Re-deliver this report later if a dialog already has the floor.

        Returns True when it has taken responsibility for the report (the caller
        must return); False when it is safe to open dialogs now.

        The retry is bounded. An unbounded one would keep firing against a modal
        the user simply leaves open — a timer for the life of the process, and a
        dependency dialog that appears minutes later attached to nothing the user
        is doing. When the budget runs out we give up **loudly**, in the log, with
        the reason: the check can be re-run from Settings, and a user whose
        required tools are missing will be told so by the thing that needs them.

        **And on screen, for a check the user asked for.** Giving up used to be
        log-only, so a click on Check dependencies could end with nothing shown
        at all — the report the maintainer filed on 2026-09-28. Now the status
        bar says the result is waiting (first hold), says where to find it when
        the wait is abandoned (the report stays stored, and Setup & Updates shows
        it), and puts the outcome back when it is finally delivered. A launch
        check nobody asked for keeps the log-only behaviour: it must not nag.
        """
        from PySide6.QtCore import QTimer

        blocker = self._modal_floor_blocker()
        if not blocker:
            if self._dep_resolve_deferrals and show_summary and self._dep_check_outcome:
                # The wait is over and the result is about to be shown: the
                # "will be shown when the dialog closes" line is no longer true.
                self._show_dependency_status(self._dep_check_outcome)
            self._dep_resolve_deferrals = 0
            return False
        self._dep_resolve_deferrals += 1
        if self._dep_resolve_deferrals > _DEP_RESOLVE_MAX_DEFERRALS:
            log.warning(
                "gave up re-delivering the dependency report after %d attempts — "
                "%s. Re-run the check from Settings once the dialog is closed.",
                _DEP_RESOLVE_MAX_DEFERRALS,
                blocker,
            )
            self._dep_resolve_deferrals = 0
            if show_summary:
                self._show_dependency_status(dep_status.gave_up_message())
            return True
        log.info(
            "holding the dependency report (attempt %d) — %s",
            self._dep_resolve_deferrals,
            blocker,
        )
        if self._dep_resolve_deferrals == 1 and show_summary:
            self._show_dependency_status(dep_status.waiting_for_dialog_message())
        QTimer.singleShot(
            _DEP_RESOLVE_RETRY_MS,
            lambda: self._apply_dependency_report(
                gui_manager, report, show_summary=show_summary
            ),
        )
        return True

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
                "later from Tools → Setup & Updates… → Check dependencies.)"
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
            "Done. Re-run Tools → Setup & Updates… → Check dependencies to "
            "confirm what's now "
            "installed. (Picard and flac take effect immediately; if flac was "
            "set up via the container wizard, it's ready now too.)",
        )

    def _resolve_missing_unified(self, report: DependencyReport) -> None:
        """Resolve every missing dependency through **one** dialog (items 2+6).

        This replaces the old per-tier fan-out — a consent box for auto deps,
        a separate queued dialog, and *one manual dialog per item* — which is
        what produced the "two popups" the maintainer hit on a fresh install
        (the ripper + metaflac each opened their own dialog). Now every installable
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
        # For tools the setup wizard provides (cyanrip, metaflac, flac and
        # cd-paranoia), hand the dialog a callback so it can offer the one-click
        # wizard instead of only a copyable search string — the user shouldn't
        # have to paste a query to install something the app installs itself
        # (Tools → Setup & Updates… → Run setup…).
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
            "<ok_count> ok, <n> missing/needs-attention."
            "Installed: <name> <version> (<build note>), …"  ← when any are OK
                    where a dep WITH a build note reports the tool's own version
                    string and build tag rather than the parsed int-triple:
                    cyanrip 0.9.4-rc1+platterpus.5-beta.5 (the Platterpus fork;
                    build tag "platterpus-fork-g9048082")
            "Optional (not installed): <names>"   ← only when present
            (blank line)
            "Wrong build:"                ← only when a build note says so
            "  - <dep>: <summary>" + detail + how to fix
            (blank line)
            "Install failures:"           ← only when failures exist
            "  - <dep>: <error message>"  ← one per failure

        **An incomplete check leads with that fact** — "Check incomplete: N tools
        were not checked" — and ends with which ones, why, and how to check again,
        under a warning icon and its own title. The counts below the headline are
        still true of what WAS checked; what they may not do is read as the whole
        picture, which is what a stopped check's partial report used to do.

        **Why the build notes are here at all.** This dialog is the surface a
        user actually reads at launch, and it used to print a bare version —
        which for cyanrip is the one fact that cannot distinguish the
        Platterpus fork from stock upstream (the fork keeps upstream's version
        string deliberately). A maintainer looking at "cyanrip 0.9.3" had no
        way to know the fork install had never happened. Naming the build is
        CLAUDE.md's *"say which build produced an artifact"* rule; it had been
        applied to the log, the report and ``--doctor``, and missed here.
        """
        ok_specs = getattr(report, "ok", [])
        ok_count = len(ok_specs)
        missing_count = len(getattr(report, "missing", []))
        ok_versions = getattr(report, "ok_versions", {}) or {}
        build_notes: Mapping[str, BuildNote] = getattr(report, "build_notes", {}) or {}
        # Deps that are installed and current but are the WRONG BUILD. Counted
        # into the headline: a summary that says "0 needs-attention" while
        # cyanrip is stock is precisely the message that misled the maintainer.
        attention: list[tuple[DependencySpec, BuildNote]] = list(
            getattr(report, "build_attention", []) or []
        )
        # Collect real install failures (not user declines — those are
        # surfaced via the dialog the user already saw).
        install_results = getattr(report, "install_results", [])
        failures = [
            r
            for r in install_results
            if not r.success and not getattr(r, "user_declined", False)
        ]

        not_checked = dep_manager.unchecked_names(report)
        message = (
            f"{ok_count} ok, {missing_count + len(attention)} missing/needs-attention."
        )
        if not_checked:
            message = (
                f"Check incomplete: {len(not_checked)} tool(s) were not checked, so "
                f"this is not the full picture.\n{message}"
            )
        # Stamp the detected version next to each OK dep so the user knows
        # exactly what's installed (reproducibility), not just that it's there —
        # plus the build, where the version alone doesn't identify the binary.
        if ok_specs:
            installed = "; ".join(
                _installed_line(spec, ok_versions, build_notes) for spec in ok_specs
            )
            message += f"\nInstalled: {installed}."
        if optional_missing:
            names = ", ".join(item.spec.display_name for item in optional_missing)
            message += f"\nOptional (not installed): {names}."
        if attention:
            attention_lines = "\n".join(
                f"  • {spec.display_name}: {note.summary}\n"
                f"    {note.detail}"
                + (f"\n    Fix: {note.fix_hint}" if note.fix_hint else "")
                for spec, note in attention
            )
            message += f"\n\nWrong build:\n{attention_lines}"
        if failures:
            failure_lines = "\n".join(
                f"  • {r.spec.display_name}: {r.message}" for r in failures
            )
            message = (
                f"{message}\n\nInstall failures:\n{failure_lines}\n\n"
                # The REAL path. This hardcoded `~/.local/share/...` while
                # `paths.py` honours `XDG_DATA_HOME`, so under a relocated data dir
                # it named a file the user does not have — worse than no path, since
                # they conclude no log exists.
                f"Full output is in {LOG_PATH}."
            )
        if not_checked:
            reason = str(getattr(report, "unchecked_reason", "") or "") or (
                "the check stopped before it reached them"
            )
            message += (
                f"\n\nNot checked: {', '.join(not_checked)}.\n"
                f"Why: {reason}.\n"
                "These are neither confirmed present nor confirmed missing. Check "
                f"again in a minute: {dep_status.RERUN_PATH}."
            )

        # The icon is part of the message. A wrong-build cyanrip reported with
        # an "information" ⓘ reads as "all fine, here are the details" — which
        # is how a stock install went unnoticed. Warn when something needs
        # attention; inform when nothing does. An incomplete check is not
        # "complete", so it does not say so in its title either.
        if not_checked:
            QMessageBox.warning(self, "Dependency check incomplete", message)
        elif attention:
            QMessageBox.warning(self, "Dependency check complete", message)
        else:
            QMessageBox.information(self, "Dependency check complete", message)
