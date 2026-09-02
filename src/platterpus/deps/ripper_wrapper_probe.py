"""Find out whether the host-exported ripper wrapper EXITS when cyanrip does.

**Why this module exists.** Two consecutive rig mornings (2026-08-26 and
2026-08-27) produced **zero rip artifacts** because a probe of
``~/.local/bin/cyanrip --version`` never returned. The banner was printed in
full and then the process sat there until a 60-second ``timeout`` killed it
(exit 137). The cyanrip fork established three independent ways that the hang is
not in cyanrip — structurally from their source at the pin, from ``strace`` on
the binary, and, most tellingly, from *our own* installer, whose
``$(... )`` command substitution blocks until the child exits and demonstrably
returned. Their round-15 lap 1 §2 is the write-up.

What differs between the invocation that works and the one that hangs is not the
binary and not the flag: one runs ``/usr/local/bin/cyanrip`` inside the
container, the other runs the host export made by ``distrobox-export``. The
fork's hypothesis — offered as one — is that the wrapper does not exit when its
child does, most commonly because it allocates a PTY and waits on it.

**And their ask was three shell commands.** `CLAUDE.md` is explicit that a
procedure handed back in prose is work handed back, and that *"every 'now run
this, then run that' in a written procedure is a thing the software was supposed
to do"*. So this module is those three commands, absorbed: the app runs them,
bounds them, and reports which link hangs. Nobody types anything.

**Why it is safe for us to run a command that may hang.** The app's own calls
use pipes and do not hang; the rig probe ran the wrapper from an interactive
shell with stdin attached. Every invocation here is spawned with its stdin at
``/dev/null``, its own session (so a group kill cannot reach *our* process
group), and a hard deadline after which the whole group is SIGKILLed. A child we
cannot reap is reported as an unreapable child rather than waited on forever —
a reader wedged in a drive ioctl is in uninterruptible sleep where even SIGKILL
does not land.

**Three-state, never two.** ``hangs``/``exits``/``not_determined``. A wrapper we
could not test — because it is not installed, or the probe itself errored — is
*not* a passing wrapper, and it is not a hanging one either.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final, Protocol

_log: Final[logging.Logger] = logging.getLogger(__name__)

#: Per-invocation deadline. Deliberately short: a wrapper that exits at all
#: exits in well under a second once the container is warm, and the fork measured
#: ``--version`` at 0.039–0.042 s directly against the binary. The generous part
#: of the budget goes to :data:`COLD_CONTAINER_GRACE` instead, because the one
#: legitimate reason for a slow answer is a cold Distrobox container — measured
#: at 3.45 s elsewhere in this codebase.
PER_PROBE_TIMEOUT_S: Final[float] = 12.0

#: Extra budget for the FIRST probe only, which may pay to start the container.
COLD_CONTAINER_GRACE_S: Final[float] = 8.0

#: How long to wait for a group SIGKILL to actually reap the child. Bounded
#: because SIGKILL does not land on a process in uninterruptible sleep, and an
#: unbounded wait there is the deadlock this project has already paid for.
POST_KILL_GRACE_S: Final[float] = 3.0

#: Output kept per probe, head AND tail. Head-only truncation drops the last
#: line a tool prints, which is precisely the line that explains a failure.
_OUTPUT_HEAD_CHARS: Final[int] = 2000
_OUTPUT_TAIL_CHARS: Final[int] = 2000


class ProbeRunner(Protocol):
    """The one-invocation runner, as a type rather than as ``object``.

    Exists so the test seam in :func:`probe` is *typed* instead of being an
    ``object`` with a ``# type: ignore`` over the call — `CLAUDE.md` forbids
    weakening a type to make a checker pass, and "inject anything at all" is
    exactly that. A fake that does not match this signature now fails to
    type-check rather than at runtime on the rig.
    """

    def __call__(
        self,
        label: str,
        argv: list[str],
        *,
        timeout_s: float,
        stdin_devnull: bool = ...,
    ) -> ProbeOutcome: ...


class Verdict(StrEnum):
    """Whether the thing under test terminated on its own.

    A ``StrEnum`` so it serialises into a JSON report with no converter, matching
    ``uiscript.report.Outcome`` — two enums crossing the same boundary should not
    need two different handlings.
    """

    EXITS = "exits"
    HANGS = "hangs"
    NOT_DETERMINED = "not_determined"


@dataclass(frozen=True)
class ProbeOutcome:
    """One invocation's complete record. Every field a bug report needs.

    ``exit_code`` is tri-state: an ``int`` when the child was reaped, ``None``
    when it was not. ``None`` must never be rendered as ``0`` — a child we could
    not reap is a real answer and a different one from a clean exit.
    """

    label: str
    argv: tuple[str, ...]
    verdict: Verdict
    exit_code: int | None
    elapsed_s: float
    output: str
    #: Set when the probe could not be attempted at all (binary absent, OSError).
    skipped_reason: str | None = None
    #: True when the group SIGKILL did not reap the child within the grace.
    unreapable: bool = False


@dataclass(frozen=True)
class WrapperReport:
    """The three probes plus the conclusion they license — and only that.

    The conclusion is deliberately narrow. This report can say *"the wrapper does
    not exit"* or *"the wrapper exits"*; it cannot say *why*, and it does not
    guess. The fork was careful to offer the PTY explanation as a hypothesis and
    we keep it one.
    """

    outcomes: tuple[ProbeOutcome, ...] = ()
    verdict: Verdict = Verdict.NOT_DETERMINED
    summary: str = "not determined"
    #: Which probe settled it, by label, or None when nothing did.
    decided_by: str | None = None

    @property
    def blames_the_wrapper(self) -> bool:
        """True only when a probe of the WRAPPER hung while the bare binary did not.

        A property rather than a stored flag so it cannot disagree with
        ``outcomes``. Requires positive evidence on **both** sides: a hang alone
        is consistent with a broken container, which is not the wrapper's fault.
        """
        hung = {o.label for o in self.outcomes if o.verdict is Verdict.HANGS}
        exited = {o.label for o in self.outcomes if o.verdict is Verdict.EXITS}
        return bool(hung & _WRAPPER_LABELS) and bool(exited & _DIRECT_LABELS)


_WRAPPER_LABELS: Final[frozenset[str]] = frozenset(
    {"host export, stdin open", "host export, stdin closed"}
)
_DIRECT_LABELS: Final[frozenset[str]] = frozenset({"in-container binary"})


def _bounded(text: str) -> str:
    """Head + tail, with any elision COUNTED and marked. Never a silent drop."""
    if len(text) <= _OUTPUT_HEAD_CHARS + _OUTPUT_TAIL_CHARS:
        return text
    dropped = len(text) - _OUTPUT_HEAD_CHARS - _OUTPUT_TAIL_CHARS
    return (
        text[:_OUTPUT_HEAD_CHARS]
        + f"\n… [{dropped} characters elided from the middle] …\n"
        + text[-_OUTPUT_TAIL_CHARS:]
    )


def run_one(
    label: str, argv: list[str], *, timeout_s: float, stdin_devnull: bool = True
) -> ProbeOutcome:
    """Run one invocation under a hard deadline and record everything about it.

    **Never raises.** Every failure path returns a ``ProbeOutcome`` — this is a
    diagnostic, and a diagnostic that throws is one that turns a hang into a
    crash report about the hang-detector.

    ``start_new_session=True`` is not optional: the escalation below is a
    ``killpg``, and without a new session that signal reaches *our own* process
    group. That mistake is recorded in `CLAUDE.md`'s threading rules.
    """
    started = time.monotonic()
    try:
        proc = subprocess.Popen(  # noqa: S603 — argv is built here, never user text
            argv,
            stdin=subprocess.DEVNULL if stdin_devnull else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            start_new_session=True,
        )
    except (OSError, ValueError) as exc:
        _log.warning("wrapper probe %r could not start: %s", label, exc)
        return ProbeOutcome(
            label=label,
            argv=tuple(argv),
            verdict=Verdict.NOT_DETERMINED,
            exit_code=None,
            elapsed_s=time.monotonic() - started,
            output="",
            skipped_reason=f"could not start: {exc}",
        )

    # Read off `proc.args` rather than the local, so the record cannot drift from
    # what the OS actually received (`CLAUDE.md`: diagnostic completeness).
    spawned = tuple(proc.args) if isinstance(proc.args, (list, tuple)) else (argv[0],)
    try:
        out, _ = proc.communicate(timeout=timeout_s)
        return ProbeOutcome(
            label=label,
            argv=tuple(str(a) for a in spawned),
            verdict=Verdict.EXITS,
            exit_code=proc.returncode,
            elapsed_s=time.monotonic() - started,
            output=_bounded(out or ""),
        )
    except subprocess.TimeoutExpired:
        pass  # the interesting case — handled below, outside the except block
    except (OSError, ValueError) as exc:
        _log.warning("wrapper probe %r failed while reading: %s", label, exc)
        return ProbeOutcome(
            label=label,
            argv=tuple(str(a) for a in spawned),
            verdict=Verdict.NOT_DETERMINED,
            exit_code=None,
            elapsed_s=time.monotonic() - started,
            output="",
            skipped_reason=f"error while reading output: {exc}",
        )

    # It did not exit. Kill the GROUP — the child may have started the real work
    # in a subprocess of its own, and signalling only the leader leaves the
    # writer alive holding our pipe open, which is the deadlock in rule #9.
    unreapable = False
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (OSError, ProcessLookupError) as exc:  # already gone, or no permission
        _log.info("wrapper probe %r: group kill did not apply: %s", label, exc)
    collected = ""
    try:
        collected, _ = proc.communicate(timeout=POST_KILL_GRACE_S)
    except subprocess.TimeoutExpired:
        # SIGKILL did not land: the child is in uninterruptible sleep, almost
        # always a drive ioctl. Report it; do not wait forever.
        unreapable = True
        _log.error(
            "wrapper probe %r: child %d survived SIGKILL — reporting unreapable",
            label,
            proc.pid,
        )
    except (OSError, ValueError) as exc:
        _log.warning("wrapper probe %r: could not collect after kill: %s", label, exc)
    return ProbeOutcome(
        label=label,
        argv=tuple(str(a) for a in spawned),
        verdict=Verdict.HANGS,
        # Tri-state, and this is the case that must not become 0: the child was
        # killed, so whatever it "would" have exited with is unknown.
        exit_code=None if unreapable else proc.returncode,
        elapsed_s=time.monotonic() - started,
        output=_bounded(collected or ""),
        unreapable=unreapable,
    )


def probe(
    *,
    export_path: Path | None = None,
    container_path: str = "/usr/local/bin/cyanrip",
    container_name: str = "ripping",
    runner: ProbeRunner | None = None,
) -> WrapperReport:
    """Run the fork's three §2 invocations and report which link hangs.

    ``runner`` is an injection seam for tests — any callable with ``run_one``'s
    signature. Production passes nothing and gets the real one.

    The order matters: the wrapper with stdin **open** first, because that is the
    invocation the rig actually made and the only one observed to hang. Running
    the cheap ones first would let a broken container mask it.
    """
    run: ProbeRunner = run_one if runner is None else runner
    export = export_path or (Path.home() / ".local" / "bin" / "cyanrip")
    outcomes: list[ProbeOutcome] = []

    if export.exists():
        # THE OBSERVED FAILURE, reproduced as closely as we safely can. `stdin`
        # is left inherited rather than /dev/null: closing it is the fork's
        # candidate one-character fix, so a probe that closed it here would test
        # the fix instead of the defect and report "exits" every time.
        outcomes.append(
            run(
                "host export, stdin open",
                [str(export), "--version"],
                timeout_s=PER_PROBE_TIMEOUT_S + COLD_CONTAINER_GRACE_S,
                stdin_devnull=False,
            )
        )
        # The candidate fix, measured rather than assumed.
        outcomes.append(
            run(
                "host export, stdin closed",
                [str(export), "--version"],
                timeout_s=PER_PROBE_TIMEOUT_S,
                stdin_devnull=True,
            )
        )
    else:
        outcomes.append(
            ProbeOutcome(
                label="host export, stdin open",
                argv=(str(export), "--version"),
                verdict=Verdict.NOT_DETERMINED,
                exit_code=None,
                elapsed_s=0.0,
                output="",
                skipped_reason=f"{export} does not exist",
            )
        )

    # The wrapper alone, carrying no cyanrip at all. If THIS hangs, the fork's
    # sentence applies verbatim: no part of either program is involved.
    outcomes.append(
        run(
            "wrapper alone",
            ["distrobox-enter", "-n", container_name, "--", "true"],
            timeout_s=PER_PROBE_TIMEOUT_S,
            stdin_devnull=False,
        )
    )
    # And the binary with no wrapper, which isolates the binary from the export.
    outcomes.append(
        run(
            "in-container binary",
            [
                "distrobox-enter",
                "-n",
                container_name,
                "--",
                container_path,
                "--version",
            ],
            timeout_s=PER_PROBE_TIMEOUT_S,
            stdin_devnull=True,
        )
    )

    return _conclude(tuple(outcomes))


def _conclude(outcomes: tuple[ProbeOutcome, ...]) -> WrapperReport:
    """Turn four observations into the narrowest conclusion they support.

    Split out and pure so the decision table is testable without spawning
    anything — the branch that matters most (a hang) is the one hardest to
    produce on demand.
    """
    by_label = {o.label: o for o in outcomes}
    wrapper_open = by_label.get("host export, stdin open")
    wrapper_closed = by_label.get("host export, stdin closed")
    alone = by_label.get("wrapper alone")

    if alone is not None and alone.verdict is Verdict.HANGS:
        return WrapperReport(
            outcomes=outcomes,
            verdict=Verdict.HANGS,
            summary=(
                "`distrobox-enter -- true` does not return, so the hang is in the "
                "container entry itself — no part of Platterpus or cyanrip is "
                "involved. Nothing this app runs through the wrapper can complete."
            ),
            decided_by=alone.label,
        )

    if wrapper_open is not None and wrapper_open.verdict is Verdict.HANGS:
        if wrapper_closed is not None and wrapper_closed.verdict is Verdict.EXITS:
            return WrapperReport(
                outcomes=outcomes,
                verdict=Verdict.HANGS,
                summary=(
                    "The host export hangs with stdin attached and returns with "
                    "stdin closed. Anything invoking it from an interactive shell "
                    "must redirect stdin from /dev/null; the app already does."
                ),
                decided_by=wrapper_open.label,
            )
        return WrapperReport(
            outcomes=outcomes,
            verdict=Verdict.HANGS,
            summary=(
                "The host export does not exit, with stdin attached or closed. "
                "Closing stdin is not the fix."
            ),
            decided_by=wrapper_open.label,
        )

    if wrapper_open is not None and wrapper_open.verdict is Verdict.EXITS:
        return WrapperReport(
            outcomes=outcomes,
            verdict=Verdict.EXITS,
            summary=(
                f"The host export exited in {wrapper_open.elapsed_s:.2f}s. The "
                f"2026-08-27 hang does not reproduce here."
            ),
            decided_by=wrapper_open.label,
        )

    reasons = "; ".join(
        f"{o.label}: {o.skipped_reason}" for o in outcomes if o.skipped_reason
    )
    return WrapperReport(
        outcomes=outcomes,
        verdict=Verdict.NOT_DETERMINED,
        summary=(
            "Could not establish whether the wrapper exits"
            + (f" — {reasons}" if reasons else ".")
        ),
        decided_by=None,
    )


def render(report: WrapperReport) -> str:
    """A plain-text block for the log and the evidence bundle. No markup.

    Every probe is listed whatever the verdict, with its exact argv and its
    tri-state exit code — a diagnostic that only reports the failing case leaves
    the reader unable to tell a clean run from a run that never happened.
    """
    lines = [
        "Ripper wrapper exit probe",
        f"  verdict: {report.verdict.value}",
        f"  decided by: {report.decided_by or '(nothing settled it)'}",
        f"  summary: {report.summary}",
        f"  blames the wrapper: {report.blames_the_wrapper}",
        "",
    ]
    for outcome in report.outcomes:
        code = "null (never reaped)" if outcome.exit_code is None else outcome.exit_code
        lines.append(f"  [{outcome.label}] {outcome.verdict.value}")
        lines.append(f"    argv: {list(outcome.argv)}")
        lines.append(f"    exit: {code}   elapsed: {outcome.elapsed_s:.3f}s")
        if outcome.unreapable:
            lines.append("    UNREAPABLE: survived a group SIGKILL")
        if outcome.skipped_reason:
            lines.append(f"    not attempted: {outcome.skipped_reason}")
        body = outcome.output.strip()
        lines.append(f"    output: {body or '(nothing)'}")
        lines.append("")
    return "\n".join(lines)
