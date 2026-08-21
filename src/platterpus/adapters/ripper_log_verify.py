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
timeout, a missing log, a log **we** could not read, and — round 12 onward — a log
**the ripper** could not read (its ``CRIP_LOG_EXIT_IO_ERROR``; see
:data:`platterpus.cyanrip_cli.VERIFY_LOG_EXIT_NO_VERDICT`). Per the standing rule,
``not_determined`` is never rendered as the negative — an absent verifier is not a
failed verification.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from platterpus.adapters.tool_run import ToolRun, ToolRunner, make_runner
from platterpus.cyanrip_cli import VERIFY_LOG_EXIT_NO_VERDICT, VERIFY_LOG_FLAG
from platterpus.deps import fork_source

log = logging.getLogger(__name__)

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
    build_tag: str = "",
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
    if run.exit_code in VERIFY_LOG_EXIT_NO_VERDICT:
        # THE RIPPER SAID IT COULD NOT LOOK. THAT IS NOT A FINDING ABOUT THE LOG.
        #
        # Round 12 gave `--verify-log` a code per verdict, and one of them —
        # `CRIP_LOG_EXIT_IO_ERROR` — means *"unreadable: no verdict was reached"*.
        # Without this branch that code fell through to the bottom of this function
        # and was reported as *"the file was altered after the ripper signed it and
        # must not be treated as archival evidence"*: an accusation against an
        # archival record, derived from an answer that explicitly says nothing was
        # determined.
        #
        # This is the SAME defect as the `_read_log_text() is None` case below,
        # arriving from the other side of the seam: there *we* could not read the
        # file, here *they* could not. Both are the third state, and neither is the
        # negative. Fixed 2026-08-21 while checking the fork's round-12 exit codes.
        #
        # **Placed before the build-capability gate on purpose.** Both routes return
        # `not_determined`, so ordering cannot make an outcome worse — but this one
        # gives the user the ripper's actual reason instead of "we cannot establish
        # that this build accepts the flag", and it means the fix does not wait on a
        # build tag being added to `BUILD_TAGS_ACCEPTING_VERIFY_LOG`. Reachability is
        # gated (no build in that table emits these codes yet); correctness is not.
        #
        # The wording attributes the meaning to THEIR document rather than asserting
        # a fact about the file, because that is all we know: on a build whose
        # exit-code inventory we have not seen, `5` is either this or unreachable.
        return _not_determined(
            f"{path.name} has no verdict: the ripper exited {run.exit_code}, which "
            "its published exit-code inventory reserves for 'unreadable — no verdict "
            "was reached', so nothing here says anything about the log's contents",
            str(path),
            run,
        )
    # THE DISCRIMINATOR IS THE BUILD, NOT THE RIPPER'S WORDING.
    #
    # A rejected flag and a rejected log both exit non-zero, and only one of them
    # means the archival log is untrustworthy. Our first version told them apart by
    # matching cyanrip's error text; the fork's lap-12 J4 pointed out that string is
    # **genopt's, not theirs, and one upstream sync from changing** — and asked us to
    # key on the exit code plus the flag's presence in their published table instead.
    #
    # They are right, and it is the same lesson from the other direction: a matcher
    # built on a dependency's prose is a hand-maintained list of shapes, which is
    # exactly what hid 16 of their fatal strings in round 5.
    #
    # So `failed` now requires POSITIVE evidence the build accepts the flag. Anything
    # else is `not_determined`, which fails safe: the cost of that is a report line,
    # while the cost of the other error is accusing an intact archival log of being
    # corrupt.
    supported = fork_source.accepts_verify_log(build_tag)
    if supported is not True:
        return _not_determined(
            f"{path.name} was not verified: the ripper exited {run.exit_code}, and "
            f"we cannot establish that this build accepts {VERIFY_LOG_FLAG}"
            + (f" (build tag {build_tag!r})" if build_tag else " (no build tag)")
            + " — a non-zero exit from a build whose flag support is unknown is not "
            "evidence against the log",
            str(path),
            run,
        )
    if _looks_like_flag_rejection(run.output):
        # Kept as a BELT, never the load-bearing check. A build we believe supports
        # the flag but which says otherwise is telling us our table is wrong, and the
        # safe reading of that is still "not determined".
        return _not_determined(
            f"this ripper build appears not to accept {VERIFY_LOG_FLAG} despite "
            f"being listed as supporting it, so {path.name} could not be verified — "
            "a rejected flag is not a failed verification, and the disagreement "
            "means our published-table entry for this build needs re-checking",
            str(path),
            run,
        )
    # ABSENT IS NOT MISMATCHED, AND THE DIFFERENCE IS THE WHOLE FINDING.
    #
    # A log with no `Log FUN512:` line at all and a log whose checksum disagrees
    # with its body both exit non-zero here, and they mean opposite things:
    #
    #   * checksum present, does not match -> the archival record was ALTERED
    #     after the ripper signed it. Alarming, and correctly alarming.
    #   * no checksum line at all -> the ripper never got to write the footer.
    #     Which is exactly what happens when a rip is CANCELLED: cyanrip is
    #     killed mid-track, so the log stops before its own signature.
    #
    # Measured, 2026-08-20: a cancelled rig rip produced *"the ripper REJECTED
    # <log>: it does not match its own FUN512 checksum, so it is not a faithful
    # record of this rip and must not be treated as archival evidence"* — logged
    # at ERROR, written into the report's `issues[]`, and every word of it
    # untrue in kind. Nothing had been altered; the footer was simply never
    # written. That is this project's recurring "every word accurate, the
    # message wrong" defect.
    #
    # DERIVED FROM THE ARTIFACT, NOT FROM THE RIPPER'S PROSE. The obvious
    # implementation — match cyanrip's "No FUN512 checksum found" string — is
    # precisely what the fork's lap-12 J4 told us not to do, because that text
    # is genopt's and one upstream sync from changing (see the comment above).
    # So the discriminator is OUR OWN read of the file for the footer the parser
    # already knows how to find. A claim about an artifact should be derivable
    # from the artifact's content.
    # UNREADABLE IS A THIRD STATE, AND CALLING IT THE SECOND ONE IS THE WORST
    # AVAILABLE ERROR.
    #
    # The two branches below split on "is there a footer". That question has three
    # answers, not two — yes, no, and *we could not look* — and the third one used
    # to be folded into "yes", which routes it to the ALTERED wording at the bottom
    # of this function. So a log we merely failed to open was reported as *"the file
    # was altered after the ripper signed it and must not be treated as archival
    # evidence"*: an accusation about the artifact, from a state where we read
    # nothing about the artifact at all.
    #
    # The old code called that "fail-closed", and the docstring on
    # `_read_log_text` records why that was the wrong word. Fail-closed means
    # refusing to certify. It does not mean volunteering the most alarming
    # explanation available — that is fail-LOUD, and it is exactly the "every word
    # accurate, the message wrong" shape this function's own comment below was
    # written to remove, arriving one branch earlier. Two of this project's rules
    # meet here: a verdict is tri-state, and `not_determined` is never reported as
    # the negative.
    #
    # Found 2026-08-21 while checking the fork's round-12 exit-code work.
    text = _read_log_text(path)
    if text is None:
        # No "this is not an accusation of tampering" disclaimer, deliberately.
        # It answers a question this message never raises, and a user reading
        # "could not be read" does not need to be told what it is not. The
        # reasoning lives in the comment above, where it belongs; the test asserts
        # the accusatory wording is absent *entirely*, which a disclaimer
        # mentioning it would have defeated.
        # No "see the log" clause, and NOT because of a test.
        # `tests/test_failure_surfaces.py` requires any message pointing at "the
        # log" to name it, via `platterpus.ui.failure_text.LOG_POINTER` — and it
        # is right, but the fix it names cannot apply here: that is a UI module,
        # this is an adapter used from workers, and importing the one into the
        # other inverts the layering. A `LogVerification.detail` is DATA; the
        # multi-line pointer belongs to whichever surface renders it.
        #
        # So the errno goes to the log (see `_read_log_text`), the fact goes here,
        # and the pointer stays the renderer's job.
        return _not_determined(
            f"{path.name} could not be read, so there is no verdict about it: the "
            f"ripper exited {run.exit_code}, and we cannot say whether its "
            f"checksum line is present, absent or disagreeing with the log body",
            str(path),
            run,
        )
    if not _has_checksum_line_in(text):
        return LogVerification(
            verdict=FAILED,
            detail=(
                f"{path.name} carries NO 'Log FUN512:' checksum line at all, so the "
                f"ripper had nothing to verify it against (exit {run.exit_code}). "
                f"This is what a rip stopped part-way looks like — the ripper is "
                f"killed before it writes its own signature — and it is a different "
                f"finding from a checksum that disagrees with the log body: nothing "
                f"here says the file was altered. Either way it is not a complete "
                f"archival record, so do not cite it as one"
            ),
            log_path=str(path),
            exit_code=run.exit_code,
            argv=tuple(run.argv),
            output=run.output,
        )
    return LogVerification(
        verdict=FAILED,
        detail=(
            f"the ripper REJECTED {path.name}: it carries a 'Log FUN512:' checksum "
            f"and the log body does NOT match it, so the file was altered after the "
            f"ripper signed it and must not be treated as archival evidence "
            f"(exit {run.exit_code})"
        ),
        log_path=str(path),
        exit_code=run.exit_code,
        argv=tuple(run.argv),
        output=run.output,
    )


def _read_log_text(path: Path) -> str | None:
    """The log's text, or ``None`` if we could not read it. Never raises.

    **Split from the footer check so "unreadable" stops being an answer about
    the footer.** This used to be one function returning ``bool``, and an
    ``OSError`` returned ``True`` — described in its own docstring as
    "fail-closed". It was not: ``True`` means *there is a checksum line*, which
    routes the caller to the ALTERED verdict, so a file we never opened was
    reported as one that had been tampered with. Fail-closed is refusing to
    certify; this was asserting the worst available explanation from a position
    of having read nothing.

    ``errors="replace"`` rather than a raise, because a log with one bad byte is
    still evidence and the footer is ASCII. A decoding problem is not a reason to
    report an alteration either.
    """
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        # Logged, not swallowed: CLAUDE.md's diagnostic-completeness rule. The
        # verdict says "could not be read"; the log file says *why*, which is
        # what a bug report needs.
        log.warning("could not read %s for checksum verification: %r", path, exc)
        return None


def _has_checksum_line_in(text: str) -> bool:
    """Whether log `text` carries cyanrip's own ``Log FUN512:`` footer.

    Delegates to the parser's own :func:`~platterpus.parsers.cyanrip_log.
    has_log_checksum` rather than re-spelling the pattern, so the two can never
    disagree about what the footer looks like — the same one-definition-
    many-callers rule the offer-vs-verdict split was fixed under.

    Takes text rather than a path so it cannot re-acquire an I/O failure mode:
    the caller has already decided what an unreadable file means, and it is not
    this function's business to answer for one.
    """
    from platterpus.parsers.cyanrip_log import has_log_checksum

    return has_log_checksum(text)


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
