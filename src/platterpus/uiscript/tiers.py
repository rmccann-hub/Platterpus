"""Tier grouping and dependency pruning for acceptance scripts — the mechanism only.

**What this is for.** Round 18 agreed a tiered acceptance procedure: work is grouped
into tiers, and *a failure prunes its own dependents* rather than halting the run or
escalating. That replaced an earlier escalation gate, for a reason worth keeping in
front of the reader: **a run that stops at the first problem hides every problem
behind it**, and on this project a disc pass costs hours nobody gets back. Pruning
keeps the run going while refusing to report results that rest on something already
known to be broken.

**What this is NOT, deliberately.** It does not say what tiers 0 through 3 *mean*
and it assigns no tier to any existing script. Round 18 lap 1 §2 fixed the meanings
and round 18 closed ``GO``/``GO``, so they are settled and are not re-derived here;
which of *our* acceptance sections sits at which tier is explicitly ours to decide
(round 19 lap 1 §5.4) and is tracked in ``TASKS.md``, not encoded in this module.

**Tier 4 is the exception, and it IS implemented here** — see :data:`SWEEP_TIER`.
It is the one tier whose behaviour is a mechanism rather than a mapping: its steps
assert nothing, so the engine, not the script author, has to guarantee that.

**Why pruning is not skipping, and why that distinction is the whole point.** A
pruned step reports ``BLOCKED`` — *prevented*: it wanted to run and could not, and
the record **names the prerequisite that stopped it**. It is emphatically not
``SKIPPED`` (*declined*), which would claim someone chose to leave it out. Round 18
spent its length establishing that those two are different facts about a run, so a
mechanism that produced one where the other is true would undo the round that
produced it.

**Pure on purpose.** No Qt, no runner state, no I/O — the runner holds a
:class:`PruneLedger` and asks it questions. That keeps the decision testable without
a GUI, and keeps the rule in one readable place rather than spread through the
dispatch loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The declarable tier range. Bounds are checked so a typo (``tier 41``) is reported
#: against its own line rather than silently creating a tier nobody planned. What
#: tiers 0-3 *mean* is not checked here and is not ours to check: round 18 lap 1 §2
#: fixed those meanings and that round closed ``GO``/``GO``. Only :data:`SWEEP_TIER`
#: carries behaviour, because only its meaning is a property of the engine.
MIN_TIER: int = 0
MAX_TIER: int = 4

#: The **sweep** tier. Round 19 lap 1 §5.1, and it is not "the widest tier":
#:
#:     *"`tier 4 sweep` runs, records, and asserts NOTHING. Every step it contains
#:     reports `INFO`, whatever happens. It has no `PASS` and no `FAIL`."*
#:
#: It exists because of the operator's instruction of 2026-09-13 — *"Don't outright
#: fail or stop testing, move to the next branch or step"* — so its output is input
#: to the next round rather than evidence about this one. Two consequences the code
#: has to carry, not just the prose:
#:
#: * **A green sweep is not evidence and must never be reported as any.** A run with
#:   two hundred sweep rows and one tier-2 `FAIL` is a FAILED run; `RunReport.ok`
#:   already refuses to let a good outcome outvote a bad one, and
#:   ``RunReport.sweep_only`` is what stops a sweep-only run being *rendered* as a
#:   pass — `ok` is True for it, correctly, and "all checks passed" would be a lie
#:   about a run that made no check at all.
#: * **A sweep cannot prune anything**, because it cannot fail. The runner does not
#:   register sweep outcomes with the :class:`PruneLedger` at all.
#:
#: And the edge that is not obvious, from §5.2: **tier 4 needs tier 0 and nothing
#: else.** The intuitive graph hangs it off tier 2 or 3, which deletes the feature —
#: under pruning a tier-2 failure would then prune the sweep, *the sweep whose whole
#: purpose is to characterise the failure that just happened.* Expressed by the
#: script writing ``needs core``, which is why ``tier`` clears any inherited
#: ``needs``: a sweep silently carrying the previous block's prerequisites is that
#: same deletion arriving through our state instead of through the graph.
SWEEP_TIER: int = 4


def is_sweep(tier: int | None) -> bool:
    """True for the tier whose steps assert nothing (§5.1).

    A function rather than ``tier == 4`` at three call sites: the number is a
    protocol constant shared with the fork, and one of those sites forgetting to
    change is how two surfaces come to disagree about what a run found.
    """
    return tier == SWEEP_TIER


def parse_tier(text: str) -> int | str:
    """``int`` on success, or a human-readable reason on failure.

    Returns the error rather than raising: this is parser-grade code reached from a
    script line, and every other verb in this language reports a bad argument against
    the line that typed it instead of ending the run.
    """
    try:
        value = int(text)
    except ValueError:
        return f"'{text}' is not a tier number ({MIN_TIER}-{MAX_TIER})"
    if not MIN_TIER <= value <= MAX_TIER:
        return f"tier {value} is outside {MIN_TIER}-{MAX_TIER}"
    return value


@dataclass
class PruneLedger:
    """Which labelled blocks have failed, and therefore what must not be believed.

    One instance per run. The runner registers a failure against whichever block was
    current when it happened, then asks :meth:`pruned_by` before executing each
    subsequent step.
    """

    #: Labels of blocks in which a FAIL or ERROR was recorded, in the order they
    #: first failed. A list rather than a set so the *first* cause is reportable —
    #: when a step depends on two broken things, naming the earlier one points at the
    #: root rather than at whichever happened to sort first.
    failed: list[str] = field(default_factory=list)

    def record_failure(self, label: str) -> None:
        """Note that the block named ``label`` produced a FAIL or ERROR.

        Idempotent: a block that fails twice is still one broken prerequisite, and a
        duplicate would make the ledger's own length a misleading count.
        """
        if label and label not in self.failed:
            self.failed.append(label)

    def pruned_by(self, needs: tuple[str, ...]) -> str | None:
        """The failed prerequisite that prunes a step needing ``needs``, or ``None``.

        **Only FAIL and ERROR prune**, and the omissions are deliberate. A block that
        was itself ``BLOCKED`` did not establish that anything is wrong — propagating
        from it would turn one real failure into a cascade whose reported cause is
        two removes from the defect. A block that was ``SKIPPED`` (*declined*) was a
        decision, not evidence of breakage. This mirrors ``abort-if-failed``, which
        counts FAIL and ERROR for the same reason.
        """
        for label in self.failed:
            if label in needs:
                return label
        return None
