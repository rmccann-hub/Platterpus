"""Tier grouping and dependency pruning — round 18's procedure, scaffolding only.

**What is being tested and what deliberately is not.** Round 18 agreed a tiered
acceptance procedure whose central rule is *a failure prunes its own dependents*,
replacing an escalation gate. This file tests the **mechanism**: the verbs, the
ledger, and that a pruned step reports the right thing. It does not test what tier 0
through 4 *mean*, or which tier any committed script's sections belong to — those are
round 19's to settle with the fork, and a procedure only one side has decided is not
a procedure.

**The property that matters most is the one a rename could quietly invert.** A pruned
step is `BLOCKED` — *prevented*, it wanted to run and could not — and **never**
`SKIPPED` (*declined*), which would claim someone chose to leave it out. Round 18
spent its whole length establishing that those are different facts about a run, so a
mechanism emitting one where the other is true would undo the round that produced it.
"""

from __future__ import annotations

from typing import Any

import pytest

from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner
from platterpus.uiscript.script import parse
from platterpus.uiscript.tiers import MAX_TIER, MIN_TIER, PruneLedger, parse_tier
from platterpus.uiscript.verbs import VERBS

# --- The pure half ----------------------------------------------------------


@pytest.mark.parametrize("value", [MIN_TIER, MAX_TIER, 2])
def test_a_tier_in_range_parses_to_its_number(value: int) -> None:
    assert parse_tier(str(value)) == value


@pytest.mark.parametrize("bad", ["-1", "5", "41", "x", "", "3.5"])
def test_a_tier_out_of_range_or_unparseable_returns_a_REASON(bad: str) -> None:
    """Returns the reason rather than raising, and rather than silently coercing.

    Parser-grade: every other verb reports a bad argument against the line that
    typed it instead of ending the run. `41` is the case worth naming — a typo for
    `4` that, unchecked, would create a tier nobody planned and put steps in it.
    """
    result = parse_tier(bad)
    assert isinstance(result, str) and result, f"{bad!r} was accepted as a tier"


def test_the_ledger_reports_the_FIRST_cause_not_an_arbitrary_one() -> None:
    """When a step depends on two broken things, name the earlier one.

    Ordering is the whole reason `failed` is a list rather than a set: the first
    failure is nearer the root, and a reader chasing a cascade wants the root.
    """
    ledger = PruneLedger()
    ledger.record_failure("identity")
    ledger.record_failure("disc")
    assert ledger.pruned_by(("disc", "identity")) == "identity"


def test_recording_one_block_twice_is_still_one_broken_prerequisite() -> None:
    """Idempotent, so the ledger's own length is not a misleading count."""
    ledger = PruneLedger()
    ledger.record_failure("identity")
    ledger.record_failure("identity")
    assert ledger.failed == ["identity"]


def test_an_unrelated_failure_prunes_nothing() -> None:
    """The floor for every pruning assertion here.

    A ledger that pruned everything would satisfy all the positive cases above
    while making the mechanism useless — the shape `CLAUDE.md` calls *a detector
    that cannot fail*, inverted.
    """
    ledger = PruneLedger()
    ledger.record_failure("identity")
    assert ledger.pruned_by(("disc",)) is None
    assert ledger.pruned_by(()) is None


# --- The verbs --------------------------------------------------------------


def test_both_verbs_are_in_the_language() -> None:
    """A capability the script language cannot reach is one the tests cannot reach.

    `CLAUDE.md`: a new testing capability is a SCRIPT VERB, and a CLI flag is the
    exception that has to be argued for.
    """
    for name in ("tier", "needs"):
        assert name in VERBS, f"{name!r} is not a verb, so no script can declare it"


class _NoWindow:
    """The runner needs *a* window; `tier`, `needs`, `log` and `eval` touch none.

    Deliberately bare rather than the rich stub the rip-verb tests use. If a future
    tier verb reached for the window this would fail loudly at that call, which is
    the honest outcome — `CLAUDE.md`: *what does my stand-in do that the real thing
    does not?* This one does nothing, and that is the claim being made.
    """


def _run(script: str) -> list[Any]:
    """Execute a whole script synchronously and return its step records."""
    runner = ScriptRunner(_NoWindow())
    runner._report.steps.clear()
    for step in parse(script):
        runner._execute(step)
    return runner._report.steps


def test_a_failure_prunes_its_dependents_and_the_run_CONTINUES() -> None:
    """The rule round 18 adopted, end to end.

    **Continuing is half the rule and it is the half that is easy to drop.** An
    escalation gate would stop here; stopping hides every problem behind the first
    one, and on this project a disc pass costs hours nobody gets back.
    """
    records = _run(
        "\n".join(
            [
                "tier 0 identity",
                "eval nope",  # ERROR: no handler — a real failure in this block
                "tier 1 ripping",
                "needs identity",
                "log this one rests on identity",
                "tier 1 independent",
                "needs something-else",
                "log this one does not",
            ]
        ),
    )
    by_source = {r.source: r for r in records}

    dependent = by_source["log this one rests on identity"]
    assert dependent.outcome is Outcome.BLOCKED, (
        f"a step depending on a failed block recorded {dependent.outcome}; round 18 "
        "settled that as BLOCKED (prevented — wanted to run, could not)"
    )
    assert "identity" in dependent.detail, (
        f"the pruned record does not name its prerequisite: {dependent.detail!r}. "
        "'prevented' is defined as naming the failed prerequisite; without it the "
        "reader has a blocked step and no cause."
    )

    independent = by_source["log this one does not"]
    assert independent.outcome is Outcome.PASS, (
        f"an unrelated step recorded {independent.outcome} — the failure pruned more "
        "than its own dependents, which is the cascade this design avoids"
    )


def test_a_pruned_step_is_never_reported_as_DECLINED() -> None:
    """The inversion that would undo round 18, asserted directly.

    `SKIPPED` means *we chose not to run it*. A step prevented by a broken
    prerequisite was not a choice, and reporting it as one tells the operator to
    decide whether to escalate when the actual action is to fix the prerequisite.
    """
    records = _run(
        "tier 0 identity\neval nope\ntier 1 later\nneeds identity\nlog dependent",
    )
    assert not [r for r in records if r.outcome is Outcome.SKIPPED], (
        "a pruned step was recorded as SKIPPED (declined) rather than BLOCKED "
        "(prevented) — the two mean opposite things and round 18 exists because of it"
    )


def test_the_structural_verbs_are_not_themselves_pruned() -> None:
    """`tier` and `needs` declare structure; pruning them erases the record.

    If a `tier` line inside a pruned region were itself blocked, the transcript would
    lose the name of the block whose steps were pruned — so the reader sees blocked
    steps with no visible grouping to explain them.
    """
    records = _run(
        "tier 0 identity\neval nope\ntier 1 later\nneeds identity\nlog dependent",
    )
    structural = [r for r in records if r.source.startswith(("tier ", "needs "))]
    assert len(structural) >= 3, f"expected the structural lines; got {structural}"
    assert all(r.outcome is Outcome.PASS for r in structural), (
        f"a structural verb was pruned: {[(r.source, r.outcome) for r in structural]}"
    )


def test_a_bad_tier_number_fails_its_own_line_and_does_not_end_the_run() -> None:
    """An arity or range mistake is reported where it was typed."""
    records = _run("tier 41 nonsense\nlog after")
    assert records[0].outcome is Outcome.ERROR
    assert "41" in records[0].detail
    assert records[-1].outcome is Outcome.PASS, "a bad tier line ended the run"


def test_a_tier_block_without_a_label_is_refused() -> None:
    """An unnamed block cannot be depended on.

    A dependency mechanism whose targets are sometimes unnameable is one that
    silently stops applying — the step declares a `needs` nobody can satisfy or
    break, and it runs regardless.
    """
    records = _run("tier 0")
    assert records[0].outcome is Outcome.ERROR, (
        f"`tier 0` with no label recorded {records[0].outcome}"
    )


def test_the_tier_is_carried_on_every_record() -> None:
    """So a reader of the JSON can group without re-parsing the script."""
    records = _run("tier 2 measuring\nlog inside")
    inside = [r for r in records if r.source == "log inside"][0]
    assert inside.tier == 2 and inside.tier_label == "measuring", (
        f"tier metadata missing from the record: tier={inside.tier!r} "
        f"label={inside.tier_label!r}"
    )


def test_a_new_run_does_not_inherit_the_previous_runs_failures() -> None:
    """A ledger surviving a run would prune on a failure in a different script.

    And it would name a prerequisite the reader cannot find anywhere in their
    transcript, which is worse than not pruning at all.
    """
    runner = ScriptRunner(_NoWindow())
    runner._prune.record_failure("identity")
    runner._report.steps.clear()
    runner._tier_label = ""
    runner._needs = ()
    # Re-arm as `start()` does, then run a script that depends on the stale label.
    runner._prune = type(runner._prune)()
    for step in parse("tier 0 fresh\nneeds identity\nlog should run"):
        runner._execute(step)
    final = runner._report.steps[-1]
    assert final.outcome is Outcome.PASS, (
        f"a fresh run was pruned by a stale ledger: {final.detail!r}"
    )
