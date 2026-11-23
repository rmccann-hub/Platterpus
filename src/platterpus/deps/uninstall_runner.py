"""The uninstaller's command runner: bounded, logged, and killable from another thread.

The old uninstaller ran its commands through the setup engine's
``SubprocessRunner``, which waits up to 30 minutes and cannot be interrupted:
``subprocess.run`` never hands out the child to signal, so the dialog's
``cancel()`` could only set a flag the blocked call never read (CLAUDE.md rule
9's false promise). Here every command runs through one
:class:`~platterpus.killable.KillableJob`, so :meth:`UninstallRunner.cancel`
SIGKILLs the child's whole process group and refuses every later command, and
each command has its own bounded wait.

Every command is logged with its exact argv, its exit code and, on failure, its
output (head and tail, counted), so a failed uninstall leaves the tool's own
sentence in the log.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Final, Protocol

from platterpus.deps.step_engine import _bounded_output, one_line_argv
from platterpus.killable import KillableJob, was_cancelled

log = logging.getLogger(__name__)

#: A listing or a probe: answered in seconds when the tool is healthy.
PROBE_TIMEOUT_S: Final[float] = 60.0
#: Removing a container, an image or a Flatpak, or a system package.
REMOVE_TIMEOUT_S: Final[float] = 900.0

#: The exit code reported for a program that is not installed (as a shell does).
NOT_FOUND: Final[int] = 127
#: The exit code reported for a command that ran out of time (as ``timeout`` does).
TIMED_OUT: Final[int] = 124
#: The exit code reported for a command our own cancel ended.
CANCELLED: Final[int] = -9


class TeardownRunner(Protocol):
    """What the uninstall engine needs from the host. Injected so tests fake it."""

    def which(self, name: str) -> bool:
        """True if ``name`` is a program on PATH."""
        ...

    def run(self, argv: list[str], timeout: float = PROBE_TIMEOUT_S) -> tuple[int, str]:
        """Run ``argv``; return its exit code and its output, stderr merged."""
        ...


class CommandKiller(Protocol):
    """Whatever can kill the uninstall's command in flight (``UninstallRunner``)."""

    def cancel(self) -> None:
        """SIGKILL the running command and refuse later ones. Never blocks."""
        ...


class UninstallRunner:
    """The real :class:`TeardownRunner`. One per uninstall; cancel ends the job."""

    def __init__(self) -> None:
        self._job: KillableJob = KillableJob("uninstall")

    @property
    def cancelled(self) -> bool:
        return self._job.cancelled

    def cancel(self) -> None:
        """Kill the command in flight and refuse every later one. Never blocks."""
        self._job.cancel()

    def which(self, name: str) -> bool:
        return shutil.which(name) is not None

    def run(self, argv: list[str], timeout: float = PROBE_TIMEOUT_S) -> tuple[int, str]:
        log.info("uninstall: %s", one_line_argv(argv))
        try:
            proc = self._job.run(argv, timeout=timeout)
        except FileNotFoundError as exc:
            log.error("uninstall: %s — command not found", argv[0])
            return NOT_FOUND, f"command not found: {argv[0]} ({exc})"
        except subprocess.TimeoutExpired as exc:
            said = "".join(
                part if isinstance(part, str) else ""
                for part in (exc.stdout, exc.stderr)
            )
            log.error(
                "uninstall: timed out after %.0fs: %s\n%s",
                timeout,
                one_line_argv(argv),
                _bounded_output(said),
            )
            return TIMED_OUT, f"timed out after {timeout:.0f}s: {one_line_argv(argv)}"
        output = (proc.stdout or "") + (proc.stderr or "")
        if was_cancelled(proc):
            log.info("uninstall: cancelled during %s", argv[0])
            return CANCELLED, "cancelled"
        if proc.returncode != 0:
            log.error(
                "uninstall: exit %d from %s\n%s",
                proc.returncode,
                one_line_argv(argv),
                _bounded_output(output),
            )
        else:
            log.debug("uninstall: exit 0 from %s", argv[0])
        return proc.returncode, output
