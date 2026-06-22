# SPDX-License-Identifier: GPL-3.0-only
"""Shared vocabulary for the host step-engines (setup + teardown).

Both arms of the host side of the dependency subsystem — ``host_setup.py``
(bootstrap) and ``host_teardown.py`` (the in-app uninstaller) — are idempotent,
cancellable, dry-run-capable step pipelines. They share the *same* small set of
types: the per-step outcome (:class:`StepStatus` / :class:`StepResult`), the
injected host-operations seam (:class:`CommandRunner` + its real
:class:`SubprocessRunner`), and the engine shape one worker drives them both
through (:class:`StepEngine`).

These used to live in ``host_setup.py``, which meant the *teardown* engine had to
import its core vocabulary from the *setup* engine — a backwards dependency. They
now live here so both engines (and the worker + dialogs that consume them) depend
on a shared base, not on each other.
"""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

log = logging.getLogger(__name__)

# Generous timeout: a `dnf install` inside a fresh container or an image pull
# can legitimately take minutes.
_STEP_TIMEOUT_S: float = 1800.0


class StepStatus(Enum):
    """Outcome of one bootstrap step."""

    RUNNING = "running"  # step is executing now (transient, for live progress)
    DONE = "done"  # already satisfied — nothing to do
    RAN = "ran"  # action ran successfully
    FAILED = "failed"  # action ran and failed (stops the pipeline)
    WOULD_RUN = "would_run"  # dry-run: this is what *would* happen
    CANCELLED = "cancelled"  # user cancelled before this step


@dataclass(frozen=True)
class StepResult:
    """Result of attempting one step, for progress display + the final report."""

    step_id: str
    title: str
    status: StepStatus
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status in (StepStatus.DONE, StepStatus.RAN, StepStatus.WOULD_RUN)


class CommandRunner(Protocol):
    """The host operations the bootstrap needs. Injected so it's testable."""

    def which(self, name: str) -> bool:
        """True if `name` is an executable on PATH."""
        ...

    def exists(self, path: Path) -> bool:
        """True if `path` exists on the host filesystem."""
        ...

    def run(self, argv: list[str]) -> tuple[int, str]:
        """Run `argv`; return (returncode, combined stdout+stderr)."""
        ...


class SubprocessRunner:
    """Real :class:`CommandRunner` backed by subprocess (production)."""

    def which(self, name: str) -> bool:
        import shutil

        return shutil.which(name) is not None

    def exists(self, path: Path) -> bool:
        return path.exists()

    def run(self, argv: list[str]) -> tuple[int, str]:
        log.info("host-setup: %s", " ".join(argv))
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=_STEP_TIMEOUT_S,
                stdin=subprocess.DEVNULL,  # never consume a parent stdin
            )
        except FileNotFoundError as exc:
            return 127, f"command not found: {argv[0]} ({exc})"
        except subprocess.TimeoutExpired:
            return 124, f"timed out after {_STEP_TIMEOUT_S:.0f}s: {' '.join(argv)}"
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


class StepEngine(Protocol):
    """Anything with HostSetup's run() shape. Both the setup engine
    (deps/host_setup.HostSetup) and the uninstaller's engine
    (deps/host_teardown.HostTeardown) qualify, so one worker drives both."""

    def run(
        self,
        progress: Callable[[StepResult], None] | None = None,
        dry_run: bool = False,
        cancelled: Callable[[], bool] | None = None,
    ) -> list[StepResult]: ...
