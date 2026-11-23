"""``run-block`` and ``expect-repeats``: a block as a subroutine, and its comparison.

**The owner's design** (TASKS R188, 2026-11-17): in a custom script, two verbs.
``run-block <name> ×<N> as <label>`` runs a block (``uiscript/blocks.py``) N
times, the runs labelled ``<label>1`` to ``<label>N``; ``expect-repeats <label>
<rule>`` checks what must hold across those runs (``same-crc``, ``verified``,
``at-least K of N``), naming the run and the track that broke it. *No general
loops or variables*: a script stays a list read top to bottom, and every pass or
fail is a named check.

**Expanded when a run starts, not when the step is reached.** The runner calls
:func:`expand_run_blocks` in ``ScriptRunner.start``, so the preflight, the time
estimate and the run sizes see every step a block will run. A ``run-block``
line becomes one ``log`` line per run, then that run's steps, each keeping the
``run-block`` line's number (the line a person can find) and carrying its run's
label in its source. A line that cannot be expanded stays one step, carrying its
own error, which is how the parser treats every bad line.

**Runs are compared through their accuracy records.** A block meant to be
repeated says ``(label)`` where each run's label goes; the repeat-rip block ends
``record-accuracy (label)``, so each run files the record
``uiscript/accuracy_grading.py`` defines, and ``compare-accuracy`` reads the same
labels.

Pure and Qt-free; every function returns, none raises.
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from platterpus.uiscript.accuracy_grading import (
    STATE_WORDS,
    AccuracyRecord,
    label_problem,
)
from platterpus.uiscript.blocks import BY_NAME, LABEL_PLACEHOLDER, block_text
from platterpus.uiscript.script import Step, parse
from platterpus.verdict import AR_STATE_VERIFIED

RUN_BLOCK: Final[str] = "run-block"

#: The most runs one ``run-block`` may ask for. Five is the owner's repeat; a
#: night holds perhaps eight whole-disc rips, so twenty is a typing mistake.
MAX_RUNS: Final[int] = 20

#: ``×5``, ``x5`` or ``X5``: the count, with the multiplication sign optional to
#: type as a letter, because not every keyboard has ``×``.
_COUNT = re.compile(r"^[×xX](?P<n>[0-9]{1,3})$")

#: The rules ``expect-repeats`` knows.
RULE_SAME_CRC: Final[str] = "same-crc"
RULE_VERIFIED: Final[str] = "verified"
RULE_AT_LEAST: Final[str] = "at-least"


@dataclass(frozen=True)
class RunBlock:
    """One parsed ``run-block`` line."""

    block: str
    count: int
    label: str

    def run_labels(self) -> tuple[str, ...]:
        return tuple(f"{self.label}{i}" for i in range(1, self.count + 1))


def parse_run_block(args: Sequence[str]) -> tuple[RunBlock | None, str]:
    """``(run, problem)`` for ``run-block <name> ×<N> as <label>``."""
    if len(args) != 4 or args[2].lower() != "as":
        return None, "write it as: run-block <name> ×<N> as <label>"
    name, count_text, _as, label = args
    block = BY_NAME.get(name)
    if block is None:
        return None, f"no block called {name!r}"
    match = _COUNT.match(count_text)
    if match is None:
        return None, f"{count_text!r} is not a count: write ×<N>, for example ×5"
    count = int(match.group("n"))
    if not 1 <= count <= MAX_RUNS:
        return None, f"×{count}: a block runs 1 to {MAX_RUNS} times"
    problem = label_problem(f"{label}{count}")
    if problem:
        return None, f"label {label!r}: {problem}"
    return RunBlock(name, count, label), ""


@dataclass(frozen=True)
class Expansion:
    """A script with its ``run-block`` lines replaced by the steps they run."""

    steps: list[Step]
    #: ``{label: number of runs}`` for every ``run-block`` that expanded.
    runs: dict[str, int] = field(default_factory=dict)
    #: Each expanded block's name, in order, once per ``run-block`` line.
    blocks: tuple[str, ...] = ()


def _refused(step: Step, problem: str) -> Step:
    return dataclasses.replace(step, error=problem)


def expand_run_blocks(steps: Sequence[Step]) -> Expansion:
    """Replace each valid ``run-block`` step with the steps of its runs."""
    out: list[Step] = []
    runs: dict[str, int] = {}
    names: list[str] = []
    for step in steps:
        if step.verb != RUN_BLOCK or not step.ok:
            out.append(step)
            continue
        run, problem = parse_run_block(step.args)
        if run is None:
            out.append(_refused(step, problem))
            continue
        if run.label in runs:
            out.append(
                _refused(step, f"the label {run.label!r} names an earlier run-block")
            )
            continue
        text, problem = block_text(run.block)
        if text is None:
            out.append(_refused(step, problem))
            continue
        if any(inner.verb == RUN_BLOCK for inner in parse(text)):
            out.append(_refused(step, "a block may not run another block"))
            continue
        runs[run.label] = run.count
        names.append(run.block)
        for number, label in enumerate(run.run_labels(), start=1):
            out.append(
                Step(
                    step.line_no,
                    f"{step.source}: run {number} of {run.count}, {label}",
                    verb="log",
                    args=(
                        f"--- {run.block}: run {number} of {run.count}, {label} ---",
                    ),
                )
            )
            for inner in parse(text.replace(LABEL_PLACEHOLDER, label)):
                out.append(
                    dataclasses.replace(
                        inner, line_no=step.line_no, source=f"[{label}] {inner.source}"
                    )
                )
    return Expansion(out, runs, tuple(names))


# --- expect-repeats ----------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    """One parsed ``expect-repeats`` rule."""

    kind: str
    at_least: int = 0
    of: int = 0

    def describe(self) -> str:
        if self.kind == RULE_AT_LEAST:
            return f"every track verified in at least {self.at_least} of {self.of} runs"
        if self.kind == RULE_VERIFIED:
            return "every track verified in every run"
        return "every track's CRC the same in every run"


def parse_rule(args: Sequence[str]) -> tuple[Rule | None, str]:
    """``(rule, problem)`` for the words after the label."""
    words = [word.lower() for word in args]
    if words in ([RULE_SAME_CRC], [RULE_VERIFIED]):
        return Rule(words[0]), ""
    if len(words) == 4 and words[0] == RULE_AT_LEAST and words[2] == "of":
        if words[1].isdigit() and words[3].isdigit():
            k, n = int(words[1]), int(words[3])
            if 1 <= k <= n <= MAX_RUNS:
                return Rule(RULE_AT_LEAST, k, n), ""
        return None, "at-least K of N needs 1 <= K <= N <= 20"
    return None, "the rule is same-crc, verified, or at-least K of N"


@dataclass(frozen=True)
class RepeatVerdict:
    """What ``expect-repeats`` found: ``pass``, ``fail`` or ``not determined``."""

    verdict: str
    detail: str


PASS: Final[str] = "pass"
FAIL: Final[str] = "fail"
NOT_DETERMINED: Final[str] = "not determined"


def grade_repeats(
    label: str,
    rule: Rule,
    runs: int | None,
    records: Mapping[str, AccuracyRecord],
) -> RepeatVerdict:
    """Check ``rule`` across the runs of ``label``. Never raises.

    A run that left no record is not counted as a failure: it is not determined,
    unless the runs that did record already broke the rule, which is a finding
    either way. Every break names its run and its track.
    """
    if runs is None:
        return RepeatVerdict(
            NOT_DETERMINED,
            f"no run-block in this script ran as {label!r}, so there is nothing "
            "to compare",
        )
    if rule.kind == RULE_AT_LEAST and rule.of != runs:
        return RepeatVerdict(
            NOT_DETERMINED,
            f"the rule counts {rule.of} runs, and {label!r} ran {runs}",
        )
    labels = [f"{label}{i}" for i in range(1, runs + 1)]
    present = [records[name] for name in labels if name in records]
    missing = [name for name in labels if name not in records]
    breaks = _breaks(rule, present, runs, len(missing))
    head = f"{label}: {rule.describe()} ({len(present)} of {runs} runs recorded)"
    lines = [head, *(f"  {line}" for line in breaks)]
    if missing:
        lines.append(f"  no accuracy record from: {', '.join(missing)}")
    if breaks:
        return RepeatVerdict(FAIL, "\n".join(lines))
    if missing or not present:
        lines.append("  not determined: a run that left no record cannot be compared")
        return RepeatVerdict(NOT_DETERMINED, "\n".join(lines))
    return RepeatVerdict(PASS, "\n".join(lines))


def _breaks(
    rule: Rule, present: Sequence[AccuracyRecord], runs: int, missing: int
) -> list[str]:
    """Each run and track that breaks ``rule``, as a sentence.

    ``missing`` runs left no record; for ``at-least`` they could still have been
    verified, so a track breaks that rule only if it would even with them.
    """
    tracks = sorted({t.number for record in present for t in record.tracks})
    found: list[str] = []
    for number in tracks:
        by_run = {
            record.label: next((t for t in record.tracks if t.number == number), None)
            for record in present
        }
        absent = [name for name, track in by_run.items() if track is None]
        if absent:
            found.append(f"track {number}: not in the record of {', '.join(absent)}")
            continue
        if rule.kind == RULE_SAME_CRC:
            crcs = {
                name: (track.crc32 if track else "") for name, track in by_run.items()
            }
            if len(set(crcs.values())) > 1 or "" in crcs.values():
                listed = ", ".join(f"{n} {c or '(none)'}" for n, c in crcs.items())
                found.append(f"track {number}: CRC32 differs: {listed}")
            continue
        not_verified = [
            f"{name} ({STATE_WORDS.get(track.state, track.state)})"
            for name, track in by_run.items()
            if track is not None and track.state != AR_STATE_VERIFIED
        ]
        if rule.kind == RULE_VERIFIED and not_verified:
            found.append(f"track {number}: not verified in {', '.join(not_verified)}")
        elif rule.kind == RULE_AT_LEAST:
            verified = len(by_run) - len(not_verified)
            if verified + missing < rule.at_least:
                found.append(
                    f"track {number}: verified in {verified} of {runs}, fewer than "
                    f"{rule.at_least} (not in {', '.join(not_verified)})"
                )
    return found
