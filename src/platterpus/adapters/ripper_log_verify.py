"""Ask the ripper to verify its **own** log — an independent witness.

## Why this exists (round 7 lap 10, J3)

We publish a SHA-256 footer on the EAC-style log *we* write, and we check it. The
fork pointed out what that check is actually worth:

> *"That check verifies **the file Platterpus wrote**, against **a checksum
> Platterpus computed**. The file Platterpus *modified* — ours — is the one whose
> verification now fails, and nothing in the run looks at it."*

They were right, and the defect it hid was real: we appended the auto-fix addendum
after cyanrip's ``Log FUN512:`` line, which makes ``cyanrip --verify-log`` reject
the file. Our integrity check reported *"the EAC-style log matches its own SHA-256
footer"* on the very rip that shipped a broken cyanrip log. **A closed loop agrees
with itself no matter what.**

So this runs the *dependency's* verifier over the *dependency's* artifact. Neither
the file nor the checksum nor the checking code is ours, which is the only
configuration in which a pass means something.

## Threading

``verify_rip_log`` spawns a subprocess that enters the Distrobox container (a cold
exec measured at 3.45 s). It must **never** be called on the Qt main thread — the
rip worker calls it, and the result travels into the report as data. The audit
check in ``rip_audit`` therefore *reads a recorded verdict*; it does not probe.
That split is deliberate: putting the probe inside the audit registry would have
put a container exec inside ``write_report``, which runs in a GUI slot.

## Tri-state, and what each state means

``verified`` the ripper checked its log and accepted it. ``failed`` the ripper
checked and **rejected** it — the log is not a faithful record of that rip and
must not be treated as archival evidence. ``not_determined`` covers every "we
could not ask": no ripper on this machine, the flag unsupported by that build, a
timeout, a missing log. Per the standing rule, ``not_determined`` is never
rendered as the negative — an absent verifier is not a failed verification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from platterpus.adapters.tool_run import ToolRun, ToolRunner, make_runner
from platterpus.cyanrip_cli import VERIFY_LOG_FLAG

#: Generous, because the call may cold-start a container (measured: 3.45 s). Still
#: bounded — a wedged verifier must degrade to ``not_determined``, not hang a rip's
#: report.
VERIFY_TIMEOUT_S: Final[float] = 30.0

#: The default runner. One per adapter, built by :func:`make_runner`, so the only
#: difference between adapters is the timeout and the diagnostic code — not three
#: hand-written capture paths that each drop something different.
_RUN: Final[ToolRunner] = make_runner(
    timeout_s=VERIFY_TIMEOUT_S,
    tool="cyanrip",
    code="ripper.log_verify_failed",
    where="verifying the ripper's own log against its FUN512 checksum",
)

VERIFIED: Final[str] = "verified"
FAILED: Final[str] = "failed"
NOT_DETERMINED: Final[str] = "not_determined"


@dataclass(frozen=True)
class LogVerification:
    """The ripper's verdict on its own log, with everything needed to diagnose it.

    Carries the full diagnostic set CLAUDE.md requires of any external call —
    tri-state exit code, exact argv as spawned, complete output — because a
    ``failed`` verdict with no evidence is an accusation the user cannot check.
    """

    verdict: str
    #: One sentence for a person. Always populated.
    detail: str
    #: The log the ripper was asked about, as a string for the JSON report.
    log_path: str = ""
    #: ``None`` when no child was ever reaped — a real answer, never written as 0.
    exit_code: int | None = None
    argv: tuple[str, ...] = field(default_factory=tuple)
    #: The verifier's complete output, stderr merged and bounded head-and-tail.
    output: str = ""

    @property
    def is_verified(self) -> bool:
        """True only for an affirmative pass. ``not_determined`` is not one."""
        return self.verdict == VERIFIED


def _not_determined(
    reason: str, log_path: str = "", run: ToolRun | None = None
) -> LogVerification:
    return LogVerification(
        verdict=NOT_DETERMINED,
        detail=reason,
        log_path=log_path,
        exit_code=run.exit_code if run is not None else None,
        argv=tuple(run.argv) if run is not None else (),
        output=run.output if run is not None else "",
    )


def verify_rip_log(
    log_path: str | Path,
    binary: str = "cyanrip",
    *,
    runner: ToolRunner | None = None,
) -> LogVerification:
    """Run ``<binary> --verify-log <log_path>`` and classify the result.

    ``runner`` is the injected command seam so tests drive every branch without a
    ripper — and, per the standing rule about stand-ins, the fake must be *less*
    capable than the real thing, not more: it returns a plain :class:`ToolRun`,
    which is exactly what the default runner returns.

    Never raises. Blocking — see the module docstring on threading.
    """
    path = Path(log_path)
    if not path.is_file():
        return _not_determined(
            f"there is no ripper log at {path}, so the ripper could not be asked "
            "to verify one",
            str(path),
        )
    run = (runner or _RUN)([binary, VERIFY_LOG_FLAG, str(path)])

    if not run.started:
        # A missing binary is a fact about this machine, not about the log. The
        # `started` third state exists precisely so these cannot be collapsed —
        # collapsing them is how a missing `flac` came to be reported as a corrupt
        # FLAC.
        return _not_determined(
            f"the ripper could not be run, so {path.name} was not verified against "
            f"its own checksum ({run.summary})",
            str(path),
            run,
        )
    if run.exit_code == 0:
        return LogVerification(
            verdict=VERIFIED,
            detail=(
                f"the ripper verified {path.name} against its own FUN512 checksum — "
                "the log is a faithful, unmodified record of this rip"
            ),
            log_path=str(path),
            exit_code=run.exit_code,
            argv=tuple(run.argv),
            output=run.output,
        )
    if run.exit_code is None:
        return _not_determined(
            f"the ripper's verification of {path.name} never returned an exit status "
            "(the child was not reaped), so the log's integrity is not determined",
            str(path),
            run,
        )
    if _looks_like_flag_rejection(run.output):
        # A build that does not know the flag cannot be reporting a bad log. This
        # is the `-V` lesson applied in the other direction: a rejected flag and a
        # failed operation both exit non-zero, and reading the first as the second
        # is exactly how "the tool is not installed" got reported for a working
        # binary.
        return _not_determined(
            f"this ripper build does not accept {VERIFY_LOG_FLAG}, so "
            f"{path.name} could not be verified — a rejected flag is not a failed "
            "verification",
            str(path),
            run,
        )
    return LogVerification(
        verdict=FAILED,
        detail=(
            f"the ripper REJECTED {path.name}: it does not match its own FUN512 "
            f"checksum, so it is not a faithful record of this rip and must not be "
            f"treated as archival evidence (exit {run.exit_code})"
        ),
        log_path=str(path),
        exit_code=run.exit_code,
        argv=tuple(run.argv),
        output=run.output,
    )


#: What cyanrip prints when it cannot parse an argument (fork ``cyanrip_main.c``).
#: Matched case-insensitively on a substring, deliberately loose: a false
#: ``not_determined`` costs a report line, while a false ``failed`` accuses an
#: intact archival log of being corrupt.
_FLAG_REJECTION_MARKERS: Final[tuple[str, ...]] = (
    "unable to parse command line argument",
    "unrecognized option",
    "unrecognised option",
    "invalid option",
)


def _looks_like_flag_rejection(output: str) -> bool:
    lowered = (output or "").casefold()
    return any(marker in lowered for marker in _FLAG_REJECTION_MARKERS)


__all__ = [
    "FAILED",
    "NOT_DETERMINED",
    "VERIFIED",
    "VERIFY_TIMEOUT_S",
    "LogVerification",
    "verify_rip_log",
]
