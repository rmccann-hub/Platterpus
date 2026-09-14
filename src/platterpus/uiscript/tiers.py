"""Tier grouping and dependency pruning for acceptance scripts — the mechanism only.

**What this is for.** Round 18 agreed a tiered acceptance procedure: work is grouped
into tiers, and *a failure prunes its own dependents* rather than halting the run or
escalating. That replaced an earlier escalation gate, for a reason worth keeping in
front of the reader: **a run that stops at the first problem hides every problem
behind it**, and on this project a disc pass costs hours nobody gets back. Pruning
keeps the run going while refusing to report results that rest on something already
known to be broken.

**What this is NOT, deliberately.** It does not say what tier 0 through 4 *mean*, it
assigns no tier to any existing script, and it does not implement tier 4's sweep
verb. Those are round 19's to settle with the fork, and a procedure only one side has
decided is not a procedure. This module is the scaffolding those decisions attach
to — the numbers are a range, not a vocabulary.

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

#: The declarable tier range. **A range, not a vocabulary** — round 18 settled that
#: there are tiers 0-3 plus a tier 4 "sweep", and left what each one *means* to the
#: round that implements the procedure. Bounds are checked so a typo (``tier 41``)
#: is reported against its own line rather than silently creating a tier nobody
#: planned; the meanings are not checked, because we do not own them yet.
MIN_TIER: int = 0
MAX_TIER: int = 4


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
