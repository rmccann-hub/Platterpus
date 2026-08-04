# SPDX-License-Identifier: GPL-3.0-only
"""One shape for *"we ran an external tool; here is everything it told us."*

**Why this module exists.** Three adapters — ``flac_verify``, ``transcode`` and
``flac_recompress`` — each declared their injected command seam as::

    Runner = Callable[[list[str]], int]

An ``int``. That single design choice made it **structurally impossible** for the
dependency's own words to reach anywhere useful: the tool's stderr was captured
inside each adapter's default runner, its last line or two logged, and the rest
discarded before the function returned. So a report reading

    ⚠ FLAC verify FAILED for 3 file(s): a.flac, b.flac, c.flac

named the *files* and could not name **what ``flac`` said about them** — not in the
UI, not in the JSON report, not in the log. Not an oversight at a call site; a
missing channel. CLAUDE.md's diagnostic-completeness rule asks for the exit code,
the exact argv and the complete output of every external tool, and no amount of
care at the call sites could satisfy it through a return type that carried one
integer.

:class:`ToolRun` is that channel, and it is deliberately shared rather than
per-adapter: the four facts drift to three the moment there are three copies of
them (which is exactly what happened to the head-and-tail output cap before
:func:`platterpus.diagnostics.bounded_output` centralised it).

**This module never raises.** :func:`run_tool` converts every failure mode —
missing binary, timeout, OSError — into a :class:`ToolRun` with ``error`` set,
because the callers are post-rip best-effort steps whose whole contract is that a
broken dependency is a *result*, never an exception into the GUI.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from platterpus import diagnostics

#: What we say instead of a real exit code when the child was never reaped. Kept as
#: a named constant so the tri-state is visible at every comparison site rather
#: than implied by a bare ``None``.
NOT_REAPED: Final[None] = None


@dataclass(frozen=True)
class ToolRun:
    """Everything one external-tool invocation told us.

    Frozen: a run is a record of a moment, and a mutable one could disagree with
    the log line already written about it.
    """

    #: Tri-state, and the reason this is not an ``int``. ``None`` means the child
    #: was **never reaped** — a timeout we killed, a binary that never started —
    #: which is a real and different answer from ``0``, and must never be written
    #: as ``0``. Every consumer that treats ``None`` as success is a bug.
    exit_code: int | None
    #: The tool's complete output, **stderr merged into stdout**, bounded head and
    #: tail with the elision counted (see :func:`diagnostics.bounded_output`).
    #: Merged rather than kept apart because the interleaving is itself evidence:
    #: which line of progress the error interrupted is often the whole diagnosis.
    output: str = ""
    #: The exact argv **as spawned**, so it cannot drift from what the OS received.
    argv: tuple[str, ...] = ()
    #: Set when the run did not produce a verdict — binary missing, OSError, or a
    #: timeout we killed. Kept separate from a non-zero exit because "could not
    #: check" and "checked and failed" are different claims, and collapsing them is
    #: how a missing ``flac`` came to look like a corrupt FLAC.
    error: str = ""
    #: Did the child actually launch? **Three states, not two.** A missing binary
    #: (``started=False``) is a problem with the *pass* — nothing was checked and
    #: nothing should be blamed. A timeout (``started=True``, ``error`` set) is a
    #: problem with *this input* — the tool ran and wedged on it. Before this
    #: distinction existed, a single wedged file and an uninstalled ``flac`` were
    #: the same value, and the caller had to guess which it was.
    started: bool = True

    @property
    def ok(self) -> bool:
        """True only for an affirmative exit 0 with no run error.

        Written as an explicit ``== 0`` rather than ``not exit_code`` because
        ``not None`` is also true, and that is the tri-state collapse this class
        exists to prevent.
        """
        return self.started and self.error == "" and self.exit_code == 0

    @property
    def ran(self) -> bool:
        """The child launched **and** we reaped a real exit status from it."""
        return self.started and self.error == ""

    @property
    def summary(self) -> str:
        """One line naming what happened, for a status label or an issue message.

        Always says *something*: a tool that failed silently still gets
        "exit N (no output)" rather than an empty string, because an empty
        explanation is the failure this whole subsystem exists to remove.
        """
        if self.error:
            return self.error
        code = (
            "no exit status (child never reaped)"
            if self.exit_code is None
            else (f"exit {self.exit_code}")
        )
        last = ""
        for line in reversed(self.output.splitlines()):
            if line.strip():
                last = line.strip()
                break
        return f"{code}: {last}" if last else f"{code} (no output)"

    def to_json(self) -> dict[str, Any]:
        """The JSON form. Keys are stable; consumers pin them."""
        return {
            "exit_code": self.exit_code,
            "argv": list(self.argv) or None,
            "output": self.output or None,
            "error": self.error or None,
            "started": self.started,
        }

    @classmethod
    def of(
        cls,
        exit_code: int | None,
        output: str = "",
        argv: tuple[str, ...] = (),
    ) -> ToolRun:
        """Terse constructor, mostly for tests and for hand-built results.

        Exists so a fake runner reads ``lambda argv: ToolRun.of(0)`` rather than
        spelling out four keywords — a fixture that is annoying to write is a
        fixture people work around.
        """
        return cls(exit_code=exit_code, output=output, argv=argv)

    @classmethod
    def failed_to_run(cls, error: str, argv: tuple[str, ...] = ()) -> ToolRun:
        """The child never launched. ``exit_code`` stays ``None`` — see above."""
        return cls(
            exit_code=NOT_REAPED, output="", argv=argv, error=error, started=False
        )

    @classmethod
    def timed_out(
        cls, error: str, output: str = "", argv: tuple[str, ...] = ()
    ) -> ToolRun:
        """The child launched, then wedged, and we killed it. ``started`` stays True.

        Distinct from :meth:`failed_to_run` so a caller can blame *this input*
        rather than the whole pass — the tool demonstrably works, it just did not
        finish on this file.
        """
        return cls(
            exit_code=NOT_REAPED, output=output, argv=argv, error=error, started=True
        )


#: The injected command seam. Takes the argv, returns everything the tool said.
ToolRunner = Callable[[list[str]], ToolRun]


def run_tool(
    argv: list[str],
    *,
    timeout_s: float,
    tool: str,
    code: str,
    where: str = "",
    record_failure: bool = True,
) -> ToolRun:
    """Run ``argv`` to completion and return everything it told us. Never raises.

    ``stderr`` is merged into ``stdout`` so the output is in the order the tool
    produced it. ``stdin`` is ``DEVNULL`` unconditionally: a tool that decides to
    prompt would otherwise block forever in a GUI process with no terminal, and
    "hung with no explanation" is the least diagnosable failure there is.

    ``record_failure`` routes a non-zero exit (or a failure to run) through
    :func:`diagnostics.record_command_failure`, which writes it to the text log
    **and** puts it in the report's ``diagnostics`` block in one call. Pass
    ``False`` only where the caller records a richer diagnostic itself and a second
    entry would double-count.
    """
    frozen_argv = tuple(argv)
    try:
        proc = subprocess.run(  # noqa: S603 — callers pass a resolved binary
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # merged: the interleaving is evidence
            stdin=subprocess.DEVNULL,
            timeout=timeout_s,
            text=True,
            errors="replace",  # a stray non-UTF-8 byte must not raise here
        )
    except FileNotFoundError:
        run = ToolRun.failed_to_run(
            f"'{argv[0] if argv else '?'}' not found", frozen_argv
        )
    except subprocess.TimeoutExpired as exc:
        # NAME THE DURATION. "timed out" without the limit leaves a reader unable to
        # tell a wedged drive from a bound that is simply too tight for their disc.
        partial = exc.output or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", "replace")
        run = ToolRun.timed_out(
            f"timed out after {timeout_s:.0f}s (child killed, never reaped)",
            output=diagnostics.bounded_output(partial),
            argv=frozen_argv,
        )
    except OSError as exc:
        run = ToolRun.failed_to_run(f"could not run {tool}: {exc}", frozen_argv)
    else:
        run = ToolRun(
            exit_code=proc.returncode,
            output=diagnostics.bounded_output(proc.stdout or ""),
            # Read off `Popen.args`-equivalent rather than re-deriving: the argv we
            # report must be the argv the OS received.
            argv=tuple(proc.args)
            if isinstance(proc.args, list | tuple)
            else frozen_argv,
        )
    if record_failure and not run.ok:
        diagnostics.record_command_failure(
            code,
            tool,
            run.argv,
            run.exit_code,
            run.output or run.error,
            message=f"{tool} {run.summary}",
            where=where,
        )
    return run


def make_runner(
    *, timeout_s: float, tool: str, code: str, where: str = ""
) -> ToolRunner:
    """A :data:`ToolRunner` bound to one tool's timeout and diagnostic code.

    Adapters keep a module-level default built by this, so the *only* difference
    between them is the three values above — not three hand-written runners that
    can each capture a little differently.
    """

    def _runner(argv: list[str]) -> ToolRun:
        return run_tool(argv, timeout_s=timeout_s, tool=tool, code=code, where=where)

    return _runner


__all__ = [
    "NOT_REAPED",
    "ToolRun",
    "ToolRunner",
    "make_runner",
    "run_tool",
]
