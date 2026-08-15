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

# How much of a command's output reaches the log. A container `dnf install` can
# emit thousands of lines; an unbounded dump would bury every other entry and make
# the log a user attaches to a bug report unreadable.
_OUTPUT_HEAD_LINES: int = 40
_OUTPUT_TAIL_LINES: int = 60
_OUTPUT_ELISION: str = "  … [{count} line(s) omitted] …"


def one_line_argv(argv: list[str]) -> str:
    """Render an argv as exactly one log line, losing nothing.

    **The problem this solves.** Several steps pass a multi-line shell script as
    a single ``sh -c`` argument. ``" ".join(argv)`` embeds those newlines
    verbatim, so one INFO record became ~100 physical lines — and because the
    log also goes to the terminal, ``--install-ripper`` appeared to print its own
    source code at the operator between progress rows. Reported from real use on
    2026-08-15: excellent diagnostics, unusable terminal output.

    **Why escaping and not truncating.** The obligation to record the exact argv
    is not negotiable — a run whose command we cannot reconstruct is a run we
    cannot diagnose, which is the gap that cost a diagnosis the same day. So
    nothing is dropped: newlines, tabs and carriage returns become their
    two-character escapes, which is reversible, greppable, and one line. A cap
    would have been easier and would have thrown away the middle of the script,
    where the interesting part lives.

    Arguments are separated by a space and left otherwise verbatim; this is a
    log line, not a shell-quoting round trip, and pretending otherwise would
    invite someone to paste it back into a terminal.
    """
    return " ".join(
        arg.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        for arg in argv
    )


def _bounded_output(output: str) -> str:
    """``output`` capped to a head and a tail, with the gap counted and marked.

    **Head AND tail, never head alone.** A tool's fatal message is the *last* thing
    it prints, so a head-only cap drops exactly the line that explains the failure —
    while still looking like a complete capture. The tail is the larger half for the
    same reason.

    **The marker is load-bearing.** An unmarked jump reads as a command that fell
    silent, which is a different and more alarming fact than "we elided some lines".
    A silent truncation reads as completeness.
    """
    lines = output.rstrip("\n").splitlines()
    if len(lines) <= _OUTPUT_HEAD_LINES + _OUTPUT_TAIL_LINES:
        return "\n".join(lines)
    elided = len(lines) - _OUTPUT_HEAD_LINES - _OUTPUT_TAIL_LINES
    return "\n".join(
        [
            *lines[:_OUTPUT_HEAD_LINES],
            _OUTPUT_ELISION.format(count=elided),
            *lines[-_OUTPUT_TAIL_LINES:],
        ]
    )


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
        log.info("host-setup: %s", one_line_argv(argv))
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=_STEP_TIMEOUT_S,
                stdin=subprocess.DEVNULL,  # never consume a parent stdin
            )
        except FileNotFoundError as exc:
            log.error("host-setup: %s — command not found", argv[0])
            return 127, f"command not found: {argv[0]} ({exc})"
        except subprocess.TimeoutExpired:
            # One line here too. A timeout is precisely when the operator reads
            # this line, and a multi-line `sh -c` script would bury it.
            log.error(
                "host-setup: timed out after %.0fs: %s",
                _STEP_TIMEOUT_S,
                one_line_argv(argv),
            )
            return (
                124,
                f"timed out after {_STEP_TIMEOUT_S:.0f}s: {one_line_argv(argv)}",
            )
        output = (proc.stdout or "") + (proc.stderr or "")
        # LOG THE OUTPUT, NOT ONLY THE ARGV.
        #
        # This logged the command and threw away everything the command said. The
        # caller (`HostSetup._run_commands`) then reduced that output to its LAST
        # LINE for the UI — so a failed `meson`/`ninja`/`git` inside the container
        # left exactly one line of evidence anywhere in the system, and the log file
        # a user is asked to attach to a bug report contained none of it.
        #
        # Found while trying to diagnose a real report (2026-08-04): the fork build
        # step failed with "installed cyanrip does not identify as the pinned fork
        # build", every command had exited 0 up to the verify, and there was no way
        # to see what git checked out or what ninja did. The facts existed and were
        # discarded — which CLAUDE.md calls out as worse than never having them,
        # because the report still looks complete.
        #
        # Failure logs at ERROR with the exit code and the output; success logs the
        # output at DEBUG so a normal run stays readable but `debug_logging` captures
        # a full transcript. Bounded head+tail with a counted elision marker, because
        # a fatal message is the LAST thing a tool prints and a head-only cap drops
        # precisely the line that explains the failure.
        if proc.returncode != 0:
            log.error(
                "host-setup: exit %d from %s\n%s",
                proc.returncode,
                one_line_argv(argv),
                _bounded_output(output),
            )
        elif output.strip():
            log.debug(
                "host-setup: exit 0 from %s\n%s", argv[0], _bounded_output(output)
            )
        else:
            # ALWAYS record the exit, even with no output. A command that succeeds
            # silently otherwise leaves *nothing* between the argv line before it and
            # the argv line after it, so "did it run?" is unanswerable from the log.
            # The real report had exactly this hole for `sudo install`: two
            # consecutive argv lines and no verdict for the first.
            log.debug("host-setup: exit 0 from %s (no output)", argv[0])
        return proc.returncode, output


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
