"""What LSL 3 adds to a lap's own checks: B1 and B3. B2 reads the round, in `round_rules`.

The spec is the shared proposal's §"LSL 3"
(`cyanrip@889a375:docs/handshake/PROPOSAL-lap-statement-language.md:204-252`),
read as both projects agreed in round 29 (below), and every refusal here names
its id, the id both checkers report:

* **B1** — a `run:` names the commit it ran at: an `at:` on its statement
  (`<sha>` or `<side>@<sha>`, a commit of the author's tree, and nothing else),
  else the lap's `HANDSHAKE-FROM-COMMIT`, which must name one commit. Refused: a
  `run:` with neither; an `at:` naming anything but a commit of the author's
  tree, or a commit with more written after it; and a `run:` with no `at:` on a
  lap whose `HANDSHAKE-FROM-COMMIT` names no single commit. With `--rerun`, each
  `run:` whose command can depend on nothing but that commit is re-run
  (`rerun.plan_command`, `scratch.Scratch`), and refused when a string its
  result quotes is not in what it printed, or when it exited with a code other
  than the `exit N` its result states outside its quotes (`rerun.stated_exits`).
  Anything else is `UNCHECKED run:`, a warning with its reason, never a refusal
  and never a guess. A re-run whose result states no exit code and whose quoted
  strings are all printed, but which exited non-zero, is matched, since there
  was nothing else to compare, and is warned about as `UNCHECKED exit:` and
  counted apart, so a failed command never reads as a plain match. What B1
  covered is counted on `Lap.runs` and printed.
* **B3** — an `answers:` on a statement A6 lets carry no weight (`NOTE`, `ASK`,
  `VERDICT`, `WILL`, `UNKNOWN`, `FACT relayed`) is refused here, and answers
  nothing for A7 in `round_rules`, which asks the same predicate.

**Where we read the text one way of two.** Only a `run:` in an `evidence:` field
is a `run:` here, because `evidence:` is the one field LSL 1 gives the
`run: CMD => RESULT` form; a `was:` that quotes an old, wrong `run:` is a quotation,
and re-running it would refuse a correction for being one.

**Three readings both projects agreed in round 29.** B1's text left three
questions open, and on each this checker reads it the way the fork proposed in
their round 29 lap 1, S28 and S29, which we accepted. They are the fork's to
write into the shared proposal (their S30), so until that lands the proposal at
`889a375` is silent where this checker is not:

* **An `at:` is a commit and nothing else** (S29). `at: 785925a (the release)` is
  refused; `at: 785925a` and `at: platterpus@785925a` are accepted. We used to
  read its first word and treat the rest as a remark (`_at_commits`).
* **A `run:` needs a `HANDSHAKE-FROM-COMMIT` that names one commit** (S29), when
  it has no `at:` to name one itself. A header that is prose, or is declared more
  than once (the header is `PROTOCOL.md`'s, and the protocol does not let a
  reader settle a doubly-declared field by taking the first), names no single
  commit, and each `run:` leaning on it is refused, once per `run:`. A lap with
  such a header and no `run:` that needs it is not refused by B1, because the
  header itself is not LSL's to refuse. We used to warn, reading B1's row as
  asking only whether the header is there (`_job`).
* **A stated exit code is held** (S28). A result that states `exit N` outside its
  quotes is refused when the re-run exited with another code, and is a plain
  match when it exited N, whatever N is; a result that states none is
  `UNCHECKED exit:` when the command exits non-zero, exactly as before. We used
  to read every `exit N` in a result as prose (`_rerun_one`). A result that
  quotes nothing is still prose and is not re-run, whatever it states: S28 adds
  to the proposal's item 4, and does not amend it.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .context import Context
from .model import Field, RunCoverage, Statement
from .refs import first_token, is_run
from .rerun import (
    Plan,
    appears,
    plan_command,
    quoted_parts,
    split_run,
    stated_exits,
)
from .scratch import Ran, Scratch, marker_reason, ref_names
from .tables import carries_no_weight

#: `at:` — a commit, bare or with its side: `785925a`, `platterpus@785925a`.
AT_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:(?P<side>cyanrip|platterpus)@)?(?P<sha>[0-9a-f]{7,40})$"
)
SHA_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{7,40}$")
#: How much of an output a refusal quotes, from each end.
_SHOWN: Final[int] = 160


@dataclass(frozen=True)
class Job:
    """One `run:` of the lap, and the commit it ran at or why it has none."""

    statement: Statement
    field: Field
    commit: str | None
    no_commit: str | None


def check_lsl3(ctx: Context) -> None:
    """B1 and B3, whichever are switched on (an `LSL: 3` lap switches on both)."""
    on = ctx.tables.amendments
    if "B3" in on:
        for stmt in ctx.lap.statements:
            _check_answers_carry_weight(ctx, stmt)
    if "B1" in on:
        _check_runs(ctx)


def _check_answers_carry_weight(ctx: Context, stmt: Statement) -> None:
    if not carries_no_weight(stmt.kind, stmt.grade):
        return
    what = stmt.kind + (f" {stmt.grade}" if stmt.grade else "")
    for fld in stmt.values("answers"):
        ctx.refuse(
            fld.line,
            "B3",
            f"{stmt.tag}: answers: on a {what}, which carries no weight, answers "
            "nothing; answer with a statement A6 lets carry weight",
        )


@dataclass(frozen=True)
class Header:
    """What the lap's `HANDSHAKE-FROM-COMMIT` gives a `run:` with no `at:`.

    `present` is whether the lap has the header at all. `commit` is the one
    commit it names, or None, and `why_not` says why not: its first word is not a
    commit, or it is declared more than once, which the protocol does not let a
    reader settle by taking the first (`handshake-protocol.md` §2 rule 3;
    `round_digest.py` says the same of `HANDSHAKE-FROM`). B1 refuses a `run:`
    with no `at:` whether the header is absent or names no single commit: both
    leave it naming no commit it ran at (the fork's round 29 lap 1 S29).
    """

    present: bool
    commit: str | None
    why_not: str | None


def lap_commit(values: list[str]) -> Header:
    """The `HANDSHAKE-FROM-COMMIT` values of a lap, read for B1."""
    if not values:
        return Header(False, None, None)
    if len(values) > 1:
        return Header(True, None, f"declared {len(values)} times")
    token = first_token(values[0])
    if not SHA_RE.match(token):
        return Header(True, None, f"{token!r}, not a commit")
    return Header(True, token, None)


def _check_runs(ctx: Context) -> None:
    lap = ctx.lap
    coverage = RunCoverage(rerun=ctx.rerun)
    lap.runs = coverage
    header = lap_commit(lap.headers.get("FROM-COMMIT", []))
    jobs: list[Job] = []
    for stmt in lap.statements:
        commits = _at_commits(ctx, stmt)
        for fld in stmt.values("evidence"):
            if not is_run(fld.value):
                continue
            coverage.total += 1
            jobs.append(_job(ctx, stmt, fld, commits, header))
    if ctx.rerun and jobs:
        _rerun(ctx, jobs, coverage)


def _job(
    ctx: Context,
    stmt: Statement,
    fld: Field,
    commits: list[str] | None,
    header: Header,
) -> Job:
    """Refuse a `run:` that names no commit; say which commit a re-run would use."""
    if stmt.has("at"):
        named = sorted(set(commits or []))
        if commits is None or not named:
            return Job(
                stmt,
                fld,
                None,
                "its statement's at: names no commit of the author's tree",
            )
        if len(named) > 1:
            return Job(
                stmt, fld, None, f"its statement's at: fields name {len(named)} commits"
            )
        return Job(stmt, fld, named[0], None)
    if not header.present:
        ctx.refuse(
            fld.line,
            "B1",
            f"{stmt.tag}: a run: names the commit it ran at, by an at: on its "
            "statement or the lap's HANDSHAKE-FROM-COMMIT, and this has neither",
        )
        return Job(stmt, fld, None, "it names no commit it ran at")
    if header.commit is None:
        # Refused, where it used to be a warning: the header is there, but it
        # names no single commit, so this run: names none it ran at, which is
        # what B1 refuses (the fork's round 29 lap 1 S29, accepted). It is the
        # run: that is refused, once per run: leaning on the header; the header
        # itself is PROTOCOL.md's, and a lap with no run: needing it is not
        # refused by this rule.
        ctx.refuse(
            fld.line,
            "B1",
            f"{stmt.tag}: a run: with no at: ran at the lap's HANDSHAKE-FROM-COMMIT, "
            f"which is {header.why_not}, so this run: names no single commit it "
            "ran at; give its statement an at:, or the lap a HANDSHAKE-FROM-COMMIT "
            "that is one commit, declared once",
        )
        return Job(stmt, fld, None, f"HANDSHAKE-FROM-COMMIT is {header.why_not}")
    return Job(stmt, fld, header.commit, None)


def _at_commits(ctx: Context, stmt: Statement) -> list[str] | None:
    """The commits `stmt`'s `at:` fields name; None when one of them is refused.

    Each is checked the way a `DID`'s `commit:` is: it resolves in the author's
    tree and sits on its ref of record (`refs.Trees.commit`), and a failure is
    reported under B1. A tree we were not given leaves it unchecked, not refused.

    The value is the commit and nothing else (the fork's round 29 lap 1 S29,
    accepted): `at: 785925a (the release)` is refused, not read as `785925a`
    with a remark, because a checker that read past the first word would accept
    an `at:` the other checker refuses.
    """
    author = ctx.lap.author
    commits: list[str] = []
    refused = False
    for fld in stmt.values("at"):
        token = first_token(fld.value)
        match = AT_RE.match(token)
        if match is None:
            ctx.refuse(
                fld.line,
                "B1",
                f"{stmt.tag}: at: names a commit of the author's tree, as <sha> "
                f"or <side>@<sha>, not {token!r}",
            )
            refused = True
            continue
        # Whatever follows the first word, however it is spaced (a value whose
        # continuation lines were joined included).
        words = fld.value.split(None, 1)
        rest = words[1].strip() if len(words) > 1 else ""
        if rest:
            ctx.refuse(
                fld.line,
                "B1",
                f"{stmt.tag}: an at: names a commit and nothing else; this one "
                f"names {token} and then {rest[:80]!r}, so move what follows the "
                "commit into the statement's sentence or another field",
            )
            refused = True
            continue
        if author is None:
            continue  # LSL.header has refused the lap already
        if match["side"] is not None and match["side"] != author:
            ctx.refuse(
                fld.line,
                "B1",
                f"{stmt.tag}: at: {token} is a commit of {match['side']}'s tree; a "
                f"run: in this lap ran at a commit of its author's, {author}'s",
            )
            refused = True
            continue
        resolution = ctx.trees.commit(author, match["sha"])
        ctx.report(fld.line, "B1", resolution)
        if resolution.outcome == "refused":
            refused = True
            continue
        commits.append(match["sha"])
    return None if refused else commits


def _rerun(ctx: Context, jobs: list[Job], coverage: RunCoverage) -> None:
    """Re-run what B1 re-runs; count and report every `run:`, whatever became of it."""
    author = ctx.lap.author
    clone = ctx.trees.roots.get(author) if author is not None else None
    refs = ref_names(clone) if clone is not None else frozenset()
    scratch = Scratch(clone) if clone is not None else None
    try:
        for job in jobs:
            outcome = _rerun_one(ctx, job, clone, refs, scratch)
            if outcome in ("matched", "matched-nonzero"):
                coverage.matched += 1
                if outcome == "matched-nonzero":
                    coverage.matched_nonzero += 1
            elif outcome == "mismatched":
                coverage.mismatched += 1
            else:
                coverage.not_rerun += 1
    finally:
        if scratch is not None:
            coverage.leftovers = scratch.close()


def _rerun_one(
    ctx: Context,
    job: Job,
    clone: Path | None,
    refs: frozenset[str],
    scratch: Scratch | None,
) -> str:
    """`matched`, `matched-nonzero`, `mismatched` or `unchecked`, with the
    refusal or warning made.

    `matched-nonzero` is a match whose result stated no exit code and whose
    command exited non-zero: the one case B1 matches without having compared
    everything the lap claimed, so it is warned about and counted apart.
    """
    claim = split_run(job.field.value)

    def unchecked(reason: str) -> str:
        ctx.warn(
            job.field.line,
            "LSL.unchecked",
            f"UNCHECKED run: {job.statement.tag}: {reason}: {claim.command[:80]!r}",
        )
        return "unchecked"

    if claim.result is None:
        return unchecked("it names no result (run: CMD => RESULT)")
    plan = plan_command(claim.command, refs)
    if isinstance(plan, str):
        return unchecked(plan)
    quoted = quoted_parts(claim.result)
    # A result that quotes nothing is prose (the proposal, "What B1 re-runs",
    # item 4), and is not re-run even when it states an exit code (`=> exit 0`):
    # S28 adds a rule for the exit code of a result B1 compares, and does not
    # amend item 4. The fork's checker reads it the same way (`cyanrip@e5a4ddf:
    # tools/lap-statements.py:874-875`, read after this was written).
    if not quoted:
        return unchecked(
            "its result quotes nothing, so it is prose, and prose is not compared"
        )
    # The exit codes the result states outside its quotes: each one is held (the
    # fork's round 29 lap 1 S28, accepted).
    stated = stated_exits(claim.result)
    if job.commit is None:
        return unchecked(job.no_commit or "it names no commit it ran at")
    if clone is None or scratch is None:
        return unchecked(
            "no clone of the author's tree was given (--peer for the fork's)"
        )
    if plan.tree_file is not None:
        unmarked = marker_reason(clone, job.commit, plan.tree_file)
        if unmarked is not None:
            return unchecked(unmarked)
    tree = scratch.tree(job.commit)
    if isinstance(tree, str):
        return unchecked(tree)
    ran = scratch.run(plan, tree)
    if isinstance(ran, str):
        return unchecked(ran)
    for parts in quoted:
        if not appears(parts, ran.output):
            ctx.refuse(job.field.line, "B1", _mismatch(job, plan, ran, parts))
            return "mismatched"
    if stated:
        # The result said how the command ended, so B1 holds it to that: a code
        # other than the stated one is refused, and the stated one is a plain
        # match even when it is non-zero, because the lap claimed the failure
        # (`=> exit 1, "refused"`) and the re-run reproduced it.
        if stated != [ran.exit_code]:
            ctx.refuse(job.field.line, "B1", _exit_mismatch(job, plan, ran, stated))
            return "mismatched"
        return "matched"
    if ran.exit_code != 0:
        # Matched: every string the result quotes is in the output, and the
        # result states no exit code, so there is nothing else B1 can hold it to
        # (a result that states one is held to it, above). So this is not
        # refused. But a command that FAILED and still printed the quoted words
        # is not the run the lap describes, and must not read as a plain match
        # (review finding R13): said here, and counted on its own in the report.
        ctx.warn(
            job.field.line,
            "LSL.unchecked",
            f"UNCHECKED exit: {job.statement.tag}: re-ran "
            f"{shlex.join(plan.words)} at {job.commit}; its result's quoted "
            f"strings are in the output, but it {_how(ran)}, and its result "
            "states no exit code for B1 to hold it to, so whether the run "
            "succeeded is for a reader to check",
        )
        return "matched-nonzero"
    return "matched"


def _how(ran: Ran) -> str:
    """How a re-run ended, in words: `exited 1`, or `was ended by signal 9`."""
    if ran.exit_code >= 0:
        return f"exited {ran.exit_code}"
    return f"was ended by signal {-ran.exit_code}"


def _shown(output: str) -> str:
    """`output` for a refusal: whole when short, else its head and tail with the
    elision counted, so a long output is never cut silently."""
    if len(output) > 2 * _SHOWN:
        elided = len(output) - 2 * _SHOWN
        return f"{output[:_SHOWN]!r} [… {elided} characters …] {output[-_SHOWN:]!r}"
    return repr(output)


def _mismatch(job: Job, plan: Plan, ran: Ran, parts: list[str]) -> str:
    """The refusal for a quoted string not in the output, with what the output was."""
    quoted = "…".join(parts)
    output = ran.output
    return (
        f"{job.statement.tag}: re-ran {' '.join(plan.words)!r} at {job.commit} "
        f"(exit {ran.exit_code}, {len(output)} characters); its result quotes "
        f'"{quoted}", which is not in the output: {_shown(output)}'
    )


def _exit_mismatch(job: Job, plan: Plan, ran: Ran, stated: list[int]) -> str:
    """The refusal for a re-run that did not end with the code its result states.

    Names both codes, and quotes the output the way `_mismatch` does, so a reader
    can tell a tool that failed from one whose lap misremembered how it ended.
    """
    said = " and ".join(f"exit {code}" for code in stated)
    if len(stated) > 1:
        said += ", and no run ends with two codes"
    return (
        f"{job.statement.tag}: re-ran {' '.join(plan.words)!r} at {job.commit}; "
        f"its result states {said}, but it {_how(ran)} (exit {ran.exit_code}, "
        f"{len(ran.output)} characters): {_shown(ran.output)}"
    )
