"""The transcript: what the run did, rendered for a human to paste back.

Two consumers, one source. The console shows this live, and the same records are
folded into the rip's JSON report so that **one file carries the whole session** —
the maintainer's standing preference: *"if there is a way to amalgamate logs or
anything into the json file this is the preferance, it must be below 25
megabytes."*

Every record carries its outcome, its elapsed time and its detail, and a run that
ended early says why. A transcript that stops without a verdict reads exactly
like a transcript of a run that passed, which is the failure this project keeps
paying for.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum


class Outcome(StrEnum):
    """What happened to one step.

    A ``StrEnum`` so it serialises into the JSON report without a converter, and
    so a transcript read by eye shows the word rather than an integer.
    """

    PASS = "pass"
    FAIL = "fail"  # an assertion did not hold — the script's finding
    ERROR = "error"  # the step could not run — our problem, not the script's
    SKIPPED = "skipped"  # never reached (the batch aborted before it)
    BLOCKED = "blocked"  # refused: needs the escape hatch the user has not enabled
    # A step that GATHERS rather than asserts. Added for `probe-ripper-wrapper`,
    # whose whole job is to record which link in the ripper chain fails to exit —
    # a fact worth having in the transcript and never a reason to fail a run,
    # because it changes no rip. Distinguishing it from PASS matters for honesty
    # in the other direction too: `[  ok  ]` beside a hanging wrapper would be a
    # transcript claiming an assertion held when none was made.
    INFO = "info"


#: Outcomes that mean the step ran and did what it said.
#:
#: `INFO` belongs here: the step's contract is *"obtain a verdict"*, and it did.
#: Excluding it would count every gather-only step against the run's own tally
#: and make an acceptance pass look worse the more diagnostics it collected.
GOOD: frozenset[Outcome] = frozenset({Outcome.PASS, Outcome.INFO})


@dataclass
class StepRecord:
    """One executed step and its outcome."""

    line_no: int
    source: str
    outcome: Outcome
    detail: str = ""
    elapsed_s: float = 0.0
    #: Absolute path of anything the step produced (a screenshot). Recorded even
    #: when the file is later embedded elsewhere, because a reader needs to know
    #: it existed on disk.
    artifact: str = ""

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["outcome"] = self.outcome.value
        return data


@dataclass
class RunReport:
    """A whole run.

    ``ended_reason`` is empty for a run that reached the last step. Anything else
    is a real answer — "aborted at line 12", "stopped by the user", "the window
    closed" — and must survive into the JSON, because *why a batch stopped* is
    usually the finding.
    """

    started_at: str
    app_version: str
    #: The script EXACTLY as pasted, kept verbatim. A transcript that says which
    #: step failed but not what was asked of it is not reproducible, and this
    #: whole feature exists to produce evidence somebody else can act on. Bounded
    #: head-and-tail on the way into the JSON, never silently.
    script_source: str = ""
    steps: list[StepRecord] = field(default_factory=list)
    ended_reason: str = ""
    used_unsafe: bool = False
    #: Directory holding this run's screenshots, if any were taken.
    artifact_dir: str = ""
    #: Problems found by reading the whole script BEFORE step 1 ran — today, the
    #: cyanrip invocations the sanitiser will refuse. One string per problem,
    #: naming the line.
    #:
    #: **Why up front rather than in situ.** A refusal is a run-time outcome, so
    #: on a 60-step hardware batch the operator learns about it forty minutes in,
    #: standing next to a drive, with the disc pass already spent. The information
    #: was available before the first step: the sanitiser is pure and the argv is
    #: in the file. Reporting it at the top costs nothing and turns an hour into a
    #: sentence. It does NOT stop the run — a refused step is still recorded as a
    #: failure in its own place, and stopping early would hide every finding
    #: behind it.
    preflight: list[str] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        """Outcome tallies, every category present even at zero.

        Zeros are written out on purpose: "0 failures" is a measurement, and an
        absent key reads as "not checked" (`docs/testing.md` — record the
        denominator, don't recompute it).
        """
        tally = {outcome.value: 0 for outcome in Outcome}
        for step in self.steps:
            tally[step.outcome.value] += 1
        return tally

    @property
    def ok(self) -> bool:
        """True only when every step that ran passed and nothing was skipped."""
        return (
            all(step.outcome in GOOD for step in self.steps) and not self.ended_reason
        )

    def as_dict(self) -> dict[str, object]:
        """The shape embedded in the rip report's ``ui_script`` block."""
        return {
            "started_at": self.started_at,
            "app_version": self.app_version,
            # The input, beside the outcome. The maintainer's instruction:
            # "you need to make sure errors and error logs record anything we
            # are inputting as well." A failure whose input is not recorded
            # cannot be reproduced by the person reading the report.
            "script_source": _bounded(self.script_source),
            "ended_reason": self.ended_reason or None,
            "used_unsafe_verbs": self.used_unsafe,
            "artifact_dir": self.artifact_dir or None,
            "preflight": list(self.preflight),
            "counts": self.counts(),
            "ok": self.ok,
            "steps": [step.as_dict() for step in self.steps],
        }


#: Cap on the script text carried into the JSON. The report is already the one
#: per-album debug artifact and must stay under the maintainer's 25 MB ceiling; a
#: pasted script is a few KB, so this only ever fires on an accident.
MAX_SOURCE_CHARS: int = 20_000


def _bounded(text: str) -> str:
    """Head and tail, with the elision counted — never a silent truncation.

    Head *and* tail because the interesting part of an over-long paste is as
    likely to be at the end as the start, and a head-only cap drops exactly the
    line that explains it (`CLAUDE.md` — a silent truncation reads as
    completeness).
    """
    if len(text) <= MAX_SOURCE_CHARS:
        return text
    half = MAX_SOURCE_CHARS // 2
    dropped = len(text) - 2 * half
    return f"{text[:half]}\n… [{dropped} characters omitted] …\n{text[-half:]}"


def render(report: RunReport) -> str:
    """The transcript as plain text — what the console shows and the user pastes.

    Deliberately plain: it gets copied into a chat window, a GitHub issue and a
    JSON string, and anything relying on colour or terminal width would survive
    none of those.
    """
    tally = report.counts()
    head = [
        "=" * 64,
        f"Platterpus UI script run — {report.started_at}",
        f"app: {report.app_version}",
    ]
    if report.used_unsafe:
        # Loud, and at the top. A transcript produced with arbitrary code in play
        # is not the same evidence as one produced by the closed vocabulary, and
        # a reader must not have to scroll to find that out.
        head.append("*** THIS RUN USED UNSAFE VERBS (eval/call) ***")
    if report.artifact_dir:
        # Named as the thing to upload, not as "where the screenshots went". The
        # runner writes `transcript.txt` and `report.json` into this same folder
        # when the run ends, so one path is the whole answer to "what do I send
        # back" — which is the question the operator actually has.
        head.append(f"saved to: {report.artifact_dir}")
        head.append("  (transcript.txt, report.json, and any screenshots)")
    if report.preflight:
        # Above the steps, because the point is that the reader sees it before
        # spending a disc pass finding out the same thing the slow way.
        head.append("")
        head.append(
            f"read before running — {len(report.preflight)} step(s) cannot run "
            "as written:"
        )
        head.extend(f"  {problem}" for problem in report.preflight)
    head.append("=" * 64)

    body: list[str] = []
    for step in report.steps:
        mark = {
            Outcome.PASS: "  ok  ",
            Outcome.FAIL: " FAIL ",
            Outcome.ERROR: "ERROR ",
            Outcome.SKIPPED: " skip ",
            Outcome.BLOCKED: "BLOCK ",
            Outcome.INFO: " info ",
        }[step.outcome]
        line = f"[{mark}] L{step.line_no:<4} {step.source}"
        if step.elapsed_s >= 0.05:
            line += f"   ({step.elapsed_s:.1f}s)"
        body.append(line)
        if step.detail:
            for detail_line in step.detail.splitlines():
                body.append(f"           {detail_line}")
        if step.artifact:
            body.append(f"           -> {step.artifact}")

    tail = [
        "=" * 64,
        "  ".join(f"{name}={count}" for name, count in tally.items()),
    ]
    if report.ended_reason:
        tail.append(f"ENDED EARLY: {report.ended_reason}")
    tail.append(
        "RESULT: " + ("all checks passed" if report.ok else "see failures above")
    )
    tail.append("=" * 64)
    return "\n".join(head + body + tail)
