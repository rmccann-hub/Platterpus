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
from typing import ClassVar

from platterpus.uiscript.tiers import is_sweep


class Outcome(StrEnum):
    """What happened to one step.

    A ``StrEnum`` so it serialises into the JSON report without a converter, and
    so a transcript read by eye shows the word rather than an integer.
    """

    PASS = "pass"
    FAIL = "fail"  # an assertion did not hold — the script's finding
    ERROR = "error"  # the step could not run — our problem, not the script's
    # THESE TWO WERE SWAPPED RELATIVE TO THE AGREED VOCABULARY, AND WE FOUND IT
    # OURSELVES — round 18 §B2. Our `SKIPPED` was a CONSEQUENCE and the fork's is a
    # DECISION; our `BLOCKED` was a decision and theirs is a consequence. Two
    # vocabularies used the same two tokens for opposite halves of one distinction,
    # so *"adopt their word"* in either direction would have inverted both meanings
    # **in transcripts that still look well-formed**, and neither project's gate
    # could have seen it, because each side's tokens were internally consistent.
    #
    # Round 18 settled it structurally rather than by either side renaming quietly:
    # the spec names the CONCEPT and the TOKEN separately. These are ours moving to
    # the agreed spelling. The concepts are unchanged; only the words are.
    SKIPPED = (
        "skipped"  # DECLINED: we chose not to run it -> decide whether to escalate
    )
    BLOCKED = "blocked"  # PREVENTED: wanted to, could not -> fix the prerequisite; row stays unknown
    # Cannot be run on this equipment at all — different hardware, or permanently
    # unverified. Added in the same change: we had no machine state for it (our own
    # §B3 said so), so a step that is impossible here was reported as one we
    # declined, which reads as a choice we could reverse.
    UNREACHABLE = "unreachable"
    # A step that GATHERS rather than asserts. Added for `probe-ripper-wrapper`,
    # whose whole job is to record which link in the ripper chain fails to exit —
    # a fact worth having in the transcript and never a reason to fail a run,
    # because it changes no rip. Distinguishing it from PASS matters for honesty
    # in the other direction too: `[  ok  ]` beside a hanging wrapper would be a
    # transcript claiming an assertion held when none was made.
    INFO = "info"


#: The CONCEPT each token names, as round 18 settled it.
#:
#: **The concept and the token are separate columns, and this is that idea in code.**
#: Round 18's finding was that two projects can share a token and mean opposite
#: things by it; the structural fix was to name the concept independently of its
#: spelling, so a rename is one deliberate edit instead of two sides quietly
#: believing they agree.
#:
#: **A mapping rather than the enum's inline comments, because layout is not a data
#: structure.** The first conformance test read these meanings out of the comments
#: and `ruff format` broke it the same hour by wrapping one member onto two lines —
#: the reflowed-anchor failure this repo documents, arriving in a test written the
#: morning it was documented.
CONCEPT: dict[Outcome, str] = {
    Outcome.PASS: "pass",
    Outcome.FAIL: "assertion-failed",
    Outcome.ERROR: "harness-failed",
    Outcome.SKIPPED: "declined",
    Outcome.BLOCKED: "prevented",
    Outcome.UNREACHABLE: "unreachable",
    Outcome.INFO: "gathered",
}


#: Which OUTCOME VOCABULARY this report speaks. Bumped when a token changes
#: meaning — not when one is added.
#:
#: **Without this the rename would have created, inside our own archive, the exact
#: collision round 18 existed to fix.** ``"skipped"`` in a report written before
#: 2026-09-14 means *prevented*; in one written after it means *declined* —
#: opposite halves of one distinction, same six characters, and nothing in the file
#: to tell a reader which. Three committed handshake artifacts already carry the old
#: spelling and were sent to the fork as evidence
#: (``docs/handshake/outbound/artifacts/round-15-lap-13-run-report.json`` and the
#: two ``artifactsround08`` script reports); they are frozen and correct **for
#: vocabulary 1**.
#:
#: ``app_version`` was the only version this report carried, which makes the
#: vocabulary derivable only by looking up which release changed it — indirect,
#: and exactly the kind of provenance this project refuses elsewhere.
#:
#: **1** = pre-2026-09-14: ``skipped`` prevented, ``blocked`` declined, no
#: ``unreachable``.
#: **2** = round 18's agreed vocabulary: ``skipped`` declined, ``blocked``
#: prevented, ``unreachable`` added.
OUTCOME_VOCABULARY: int = 2

#: Outcomes that mean the step ran and did what it said.
#:
#: `INFO` belongs here: the step's contract is *"obtain a verdict"*, and it did.
#: Excluding it would count every gather-only step against the run's own tally
#: and make an acceptance pass look worse the more diagnostics it collected.
GOOD: frozenset[Outcome] = frozenset({Outcome.PASS, Outcome.INFO})

#: Outcomes that are a **verdict about the subject** rather than a statement about
#: the run. Only these three claim something is or is not true; the rest
#: (`SKIPPED`, `BLOCKED`, `UNREACHABLE`, `INFO`) say the step did not reach a
#: verdict, and say *why*.
#:
#: The distinction earns its place in tier 4, whose steps assert nothing (round 19
#: lap 1 §5.1) and whose outcomes are therefore converted to `INFO`. Converting the
#: non-verdicts too would be a real loss of fact: a pruned sweep step reported as
#: *gathered* claims data was collected from a step that never ran, which is the
#: same shape as the skipped-reads-like-passed defect the round was about. A sweep
#: may not assert; it must still be able to say it did not run.
VERDICTS: frozenset[Outcome] = frozenset({Outcome.PASS, Outcome.FAIL, Outcome.ERROR})


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
    #: Tier of the block this step ran in, and that block's label. `None`/`""` on a
    #: run that declares no tiers — which is every committed script today, because
    #: round 18 agreed the procedure and round 19 assigns it. The fields arrive
    #: before their users on purpose: a transcript written now stays readable by a
    #: reader that expects them.
    #: True for a step that declares the run's SHAPE rather than testing anything —
    #: today `tier` and `needs`. Kept as a field rather than re-derived from
    #: `source` by the reader: the verb is known for certain at record time and
    #: guessing it back out of the script text is the kind of second, disagreeing
    #: surface this project keeps paying for.
    structural: bool = False
    tier: int | None = None
    tier_label: str = ""

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

    #: Verbs whose EXECUTION can leave a file outside the transcript. A run that
    #: reached none of them has produced nothing the archive exists to carry:
    #: no album folder, no screenshot, no rig-check manifest.
    #:
    #: `snapshot` is deliberately absent — it renders into the transcript and
    #: writes no separate file, so counting it would make every run look like it
    #: had artifacts and the predicate below would always answer False.
    ARTIFACT_VERBS: ClassVar[frozenset[str]] = frozenset(
        {"rip", "screenshot", "rig-check"}
    )

    def produced_no_artifacts(self) -> bool:
        """True when this run's only output is its transcript and the app log.

        **Asked before building the evidence archive, and the asymmetry decides
        the shape of it.** Suppressing an archive that HAD evidence costs an
        overnight disc pass; building one nothing needed costs a dialog. So this
        answers True only when it is *certain* there is nothing — no executed
        `rip`, `screenshot` or `rig-check`. A run that recorded NO steps also
        answers True: nothing executed, so nothing was produced.

        The genuinely doubtful case — a payload that is not a `RunReport` at all
        — cannot be judged here and belongs to the caller, which builds the
        archive rather than skipping it. Said explicitly because the first
        version of this docstring claimed False for an empty list while the code
        returned True, which is the kind of comment that outlives its code.

        Written 2026-09-08, after a run that aborted at section A four seconds in
        still packed a multi-hundred-megabyte archive (the app log dominates it)
        and put up a modal offering to open the folder. Three attempts produced
        three archives and three dialogs, and the maintainer's report was *"it
        keeps asking me to open a folder and makes a new compressed file"*.
        A precondition abort is exactly the run with nothing in it: 14 steps
        executed, 223 skipped, no disc touched.

        Never raises. A step whose source cannot be read is treated as an
        artifact-producing step, which is the safe direction here.
        """
        for step in self.steps:
            # PREVENTED — the batch aborted before this step, so it produced
            # nothing. Named `SKIPPED` until round 18's rename; the docstring
            # above ("223 skipped") describes this same state under the old word.
            if step.outcome is Outcome.BLOCKED:
                continue
            try:
                verb = step.source.strip().split()[0].casefold()
            except Exception:  # noqa: BLE001 — an unreadable step is not proof
                return False
            if verb in self.ARTIFACT_VERBS:
                return False
        return True

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
        """True only when every step that ran passed and nothing was skipped.

        **A sweep cannot rescue a failure, and the shape of this expression is why.**
        Round 19 lap 1 §5.1: *"a run whose tier 4 emits two hundred INFO rows and
        whose tier 2 emitted one FAIL is a FAILED run… a summary that lets the INFO
        count soften the FAIL is the skipped-reads-like-passed defect in a new
        suit."* ``all()`` over the steps cannot be outvoted by volume — there is no
        ratio here and there must never be one.
        """
        return (
            all(step.outcome in GOOD for step in self.steps) and not self.ended_reason
        )

    @property
    def sweep_only(self) -> bool:
        """True when every step that ran was a sweep step, so nothing was asserted.

        The other half of §5.1: *"a green tier 4 is not evidence and must never be
        reported as any."* Such a run is legitimately :attr:`ok` — nothing failed,
        because nothing could — and rendering that as *"all checks passed"* would be
        a true flag on a false sentence, which is the failure mode this project
        keeps meeting (`cyanrip 0.9.3 / 0 missing`: every word accurate, the message
        wrong). ``ok`` answers *did anything go wrong*; this answers *was anything
        checked*, and only the pair is a verdict.

        Structural steps — the ``tier`` and ``needs`` declarations — are excluded:
        they state the shape of the run rather than testing anything, and counting
        them as checks would make a sweep look like it had asserted something merely
        because it announced itself.

        False for a run with no sweep steps at all, including an empty one. A run
        that asserted nothing because it never started is also not evidence, but it
        is a different problem and calling it a sweep would put a reassuring label
        on a harness that never ran.
        """
        real = [step for step in self.steps if not step.structural]
        return bool(real) and all(is_sweep(step.tier) for step in real)

    def as_dict(self) -> dict[str, object]:
        """The shape embedded in the rip report's ``ui_script`` block."""
        return {
            "started_at": self.started_at,
            "app_version": self.app_version,
            # WHICH VOCABULARY THE `outcome` VALUES BELOW SPEAK. See
            # OUTCOME_VOCABULARY: two of the tokens changed meaning on 2026-09-14,
            # so a reader without this field cannot tell `"skipped"` meaning
            # *declined* from `"skipped"` meaning *prevented*.
            "outcome_vocabulary": OUTCOME_VOCABULARY,
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
            Outcome.UNREACHABLE: "N/A   ",
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
    if report.ok and report.sweep_only:
        # A SWEEP IS NOT A PASS, and `ok` alone would say it was. Round 19 lap 1
        # §5.1: *"a green tier 4 is not evidence and must never be reported as
        # any."* Every step here reported INFO by construction, so "all checks
        # passed" would be a true flag on a false sentence — the `0 missing`
        # shape, where every word is accurate and the message is wrong.
        tail.append(
            "RESULT: gathered only — tier 4 asserts nothing, so this run is DATA "
            "for the next round, not evidence about this one"
        )
    else:
        tail.append(
            "RESULT: " + ("all checks passed" if report.ok else "see failures above")
        )
    tail.append("=" * 64)
    return "\n".join(head + body + tail)
