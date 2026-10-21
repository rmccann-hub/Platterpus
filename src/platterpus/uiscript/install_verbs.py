"""The ``install-ripper`` script verb: switch the installed cyanrip build mid-run.

**The one argued exception to "no verb installs a dependency"** (``verbs.py``):
the owner's timed rip compares two fork builds (the fork's round 36 lap 1 S15),
which needs each installed in turn. It installs only a build our record knows
(``ripper_install.resolve_script_commit``), through the SAME function as
``--install-ripper <commit>`` (``deps/ripper_install.run_install``, the setup
wizard's step engine), so Critical rules #3 and #6 hold as for every install.

**Nothing here blocks the GUI thread** (rule #9): the install runs on a daemon
thread that touches nothing Qt, and the runner's deadline polls for its answer.

**Cancellation, exactly as promised.** A stopped run or a passed deadline sets
the job's cancel flag, which the step engine reads before each step, and kills
the post-install version probe. A step already running (a package install, a
compile, the binary's copy) finishes, bounded by the engine's per-command
timeout, because a half-copied binary is worse than waiting: the boundary
``HostSetupWorker``'s allowlisted cancel states (``tests/test_qthread_ownership.py``).

**What it records** (diagnostic completeness): every step's row, every command's
exact argv, exit code and bounded output (a file in the run folder; the short
form in the transcript), and the host export's banner read AFTER the install,
latched as the run's build tag so ``(ripper)`` names the build now installed.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final

from platterpus import inbound_text
from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.deps.fork_source import ForkTarget
    from platterpus.deps.ripper_install import (
        InstallOutcome,
        RecordedCommand,
        RecordingRunner,
    )
    from platterpus.deps.step_engine import StepResult
    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)

#: The runner's backstop on one install. The step engine bounds each command at
#: 30 minutes, and a rebuild of an already-set-up rig is a few commands of a few
#: minutes each; 45 minutes is past any healthy install and still finite. When it
#: fires the job is cancelled between steps and the batch continues.
INSTALL_RIPPER_WAIT_S: Final[float] = 2700.0


@dataclass
class _InstallJob:
    """One install on its helper thread. ``done`` is set LAST, after every field.

    The worker writes the fields and then sets ``done``; the GUI thread reads them
    only after seeing ``done``. That ordering is the whole synchronisation.
    """

    recorder: RecordingRunner
    done: threading.Event = field(default_factory=threading.Event)
    cancel: threading.Event = field(default_factory=threading.Event)
    progress: list[StepResult] = field(default_factory=list)
    outcome: InstallOutcome | None = None
    #: The post-install banner probe's exit code and output. ``None`` exit means
    #: the probe never ran or never reaped — tri-state, never written as 0.
    banner_exit: int | None = None
    banner: str = ""
    error: str = ""


class InstallVerbsMixin:
    """The ``install-ripper`` handler. Type-only declarations of the runner
    surface it uses; the attributes and methods themselves are the runner's."""

    if TYPE_CHECKING:
        _window: QWidget
        _deadline_outcome: Outcome
        _deadline_detail: str
        _deadline_timeout_detail: str
        _deadline_cancel: Callable[[], None] | None

        def _record(
            self,
            step: Step,
            outcome: Outcome,
            detail: str = "",
            *,
            elapsed: float = 0.0,
            artifact: str = "",
            declined_by_size: bool = False,
        ) -> None: ...

        def _arm_deadline(
            self,
            step: Step,
            seconds: float,
            predicate: Callable[[], bool] | None = None,
        ) -> None: ...

        def _ensure_artifact_dir(self) -> Path | None: ...

        def _latch_ripper_identity(self, text: str) -> None: ...

    def _do_install_ripper(self, step: Step) -> None:
        """``install-ripper <commit|(pin)|(under-review)|(fork-pin)>``."""
        from platterpus.adapters.rip_backend import cancel_info_probe
        from platterpus.deps import ripper_install
        from platterpus.deps.fork_source import target_for_commit
        from platterpus.deps.step_engine import SubprocessRunner

        spec = step.args[0]
        commit, refusal = ripper_install.resolve_script_commit(spec)
        if refusal:
            self._record(step, Outcome.ERROR, f"nothing was installed: {refusal}")
            return
        # NOT WHILE A RIP IS READING: the rip's own ripper would be replaced under
        # it, and the post-rip `--verify-log` would run whichever binary is there.
        if getattr(self._window, "_rip_worker", None) is not None:
            self._record(
                step,
                Outcome.FAIL,
                "refusing to replace the ripper while a rip is running. Put a "
                "`wait-for-rip` (and `expect-verification`) before this step.",
            )
            return
        target = target_for_commit(commit)
        job = _InstallJob(recorder=ripper_install.RecordingRunner(SubprocessRunner()))
        preamble = ripper_install.install_preamble(target)
        log.info(
            "ui script L%d: installing cyanrip %s (from %r)", step.line_no, commit, spec
        )

        def work() -> None:
            # Local state and `job` only; never Qt, a widget or the report.
            from platterpus.adapters.rip_backend import RipError
            from platterpus.composition import build_cyanrip_backend
            from platterpus.paths import CYANRIP_BINARY_DEFAULT

            try:
                job.outcome = ripper_install.run_install(
                    target,
                    progress=job.progress.append,
                    cancelled=job.cancel.is_set,
                    runner=job.recorder,
                )
                if job.outcome.ready and not job.cancel.is_set():
                    # The banner the HOST EXPORT prints now: the binary every rip
                    # after this one runs, by the route every rip takes. Asked of
                    # the cyanrip ADAPTER (Critical rule #1), whose `version()`
                    # tries each version flag through the killable info probe and
                    # raises on a non-zero exit rather than returning error text.
                    backend = build_cyanrip_backend(CYANRIP_BINARY_DEFAULT)
                    job.banner = backend.version()
                    job.banner_exit = 0
            except RipError as exc:
                job.error = f"the version probe after the install failed: {exc}"
            except Exception as exc:  # noqa: BLE001 — a helper thread must not die silently
                log.exception("ui script install-ripper helper failed")
                job.error = f"unexpected {type(exc).__name__}: {exc}"
            finally:
                job.done.set()

        threading.Thread(
            target=work, name="uiscript-install-ripper", daemon=True
        ).start()

        def cancel() -> None:
            job.cancel.set()
            cancel_info_probe()

        def answered() -> bool:
            if not job.done.is_set():
                return False
            outcome, detail = self._grade_install(step, spec, target, job, preamble)
            self._deadline_outcome = outcome
            self._deadline_detail = detail
            return True

        self._arm_deadline(step, INSTALL_RIPPER_WAIT_S, answered)
        self._deadline_cancel = cancel
        self._deadline_timeout_detail = (
            f"the install of {commit} did not finish within "
            f"{INSTALL_RIPPER_WAIT_S:.0f}s. It was cancelled between steps; a "
            "step already running finishes in the container, bounded by the step "
            "engine's own timeout. Which build is installed is NOT DETERMINED — the "
            "next `cyanrip --version` or rip log will say."
        )

    def _grade_install(
        self,
        step: Step,
        spec: str,
        target: ForkTarget,
        job: _InstallJob,
        preamble: str,
    ) -> tuple[Outcome, str]:
        """The verdict and transcript text for a finished install. GUI thread."""
        from platterpus.deps import ripper_install
        from platterpus.deps.step_engine import StepStatus
        from platterpus.ripper_identity import identify_from_banner, version_banner_in

        expected_tag = target.build_tag
        lines = [f"install-ripper {spec} -> {target.pin}", preamble.rstrip("\n")]
        # The final row of each step; the engine's transient RUNNING pings are
        # progress for a live display, not results.
        lines.extend(
            ripper_install.step_line(r)
            for r in job.progress
            if r.status is not StepStatus.RUNNING
        )
        commands = job.recorder.commands
        saved = self._save_install_record(step, commands)
        lines.append(
            f"commands run: {len(commands)}"
            + (f" (argv, exit code and output of each in {saved})" if saved else "")
        )
        lines.extend(f"  exit {c.exit_code}: {c.argv_short}" for c in commands)
        outcome = job.outcome
        if job.error and outcome is None:
            lines.append(job.error)
            return Outcome.ERROR, "\n".join(lines)
        if outcome is None:  # pragma: no cover — the worker always sets one
            lines.append("the installer returned nothing; not determined")
            return Outcome.ERROR, "\n".join(lines)
        lines.append(ripper_install.outcome_text(outcome))
        if not outcome.ready:
            return Outcome.FAIL, "\n".join(lines)
        if job.error:
            lines.append(job.error)
            return Outcome.FAIL, "\n".join(lines)
        # Screened for the record a person reads (Critical rule #12, inbound).
        banner_line = version_banner_in(job.banner)
        shown = inbound_text.screen_text(banner_line or job.banner.strip()).text
        lines.append(f"banner after the install (exit {job.banner_exit}): {shown}")
        # The latch is updated whatever the banner says: it names the INSTALLED
        # build, and a wrong one is exactly what the next steps must see.
        self._latch_ripper_identity(job.banner)
        installed = identify_from_banner(banner_line).build_tag
        if job.banner_exit != 0 or not installed:
            lines.append(
                "the host export did not print a build tag after the install, so "
                "which build is installed is not determined"
            )
            return Outcome.FAIL, "\n".join(lines)
        if installed.casefold() != expected_tag.casefold():
            lines.append(
                f"the host export prints {installed}, not {expected_tag}: the "
                "install reported ready and the binary every rip runs is another "
                "build"
            )
            return Outcome.FAIL, "\n".join(lines)
        lines.append(f"installed and verified: {installed}")
        return Outcome.PASS, "\n".join(lines)

    def _save_install_record(self, step: Step, commands: list[RecordedCommand]) -> str:
        """Write each command's exact argv, exit code and output; return the name.

        Returns ``""`` when it could not be written, which the transcript then
        says by omission of the file name, and the log says by an error.
        """
        directory = self._ensure_artifact_dir()
        if directory is None or not commands:
            return ""
        name = f"installripper{step.line_no:04d}.txt"
        blocks: list[str] = []
        for command in commands:
            # Screened like all dependency output we store: a control character
            # becomes a visible escape rather than vanishing.
            screened = inbound_text.screen_text(command.output).text
            blocks.append(
                f"argv: {command.argv}\nexit: {command.exit_code}\n{screened}\n"
            )
        try:
            (directory / name).write_text("\n".join(blocks), encoding="utf-8")
        except OSError as exc:
            log.error("cannot write %s: %r", name, exc)
            return ""
        return name
