# SPDX-License-Identifier: GPL-3.0-only
"""Every script verb is exercised by a committed rig script, or says why not.

**Why this exists** (the review of the 2026-11-03 Full run, E2). The script
language is where this project's acceptance tests are written, and a verb no rig
script uses is a capability no hardware run exercises: its handler is reached
only by unit tests, against stand-ins. The review counted 8 of 70 verbs unused by
``fullacceptance.txt``: ``abort``, ``callout``, ``record``, ``ok``,
``expect-unidentified``, ``expect-unknown-record``, ``tier`` and ``needs``.
Across every script under ``rig_scripts/`` five of those are used (the
walkthrough script's ``callout`` and ``record``, the unknown-disc script's
``expect-unidentified`` and ``expect-unknown-record``, and from 2026-11-03 section
D2's ``ok``), which leaves the three listed below.

**A ratchet, in the shape of** ``tests/test_script_surface_is_the_default.py``:
the population is derived from the verb table and the committed scripts, never
typed here. A verb no script uses must be listed with the reason a script does not
use it and the unit test that covers it instead. The list may shrink; it may not
grow without a reason written beside the new entry and in the commit message,
and :data:`_ALLOWLIST_CEILING` is the number that makes growing it a deliberate
edit.
"""

from __future__ import annotations

import re
from pathlib import Path

from platterpus.uiscript.script import parse
from platterpus.uiscript.verbs import VERBS

_REPO = Path(__file__).resolve().parents[1]
_RIG_SCRIPTS = _REPO / "src" / "platterpus" / "rig_scripts"

#: Every verb no committed rig script uses: why, and the unit test that covers it.
UNUSED_BY_ANY_RIG_SCRIPT: dict[str, tuple[str, str]] = {
    "abort": (
        "an unconditional stop. A committed script must not stop for no reason: "
        "its preconditions use `abort-if-failed`, which stops only on a failure. "
        "Kept for the script console, where a person ends a run they are writing",
        "tests/test_rig_script_verb_inventory.py::test_abort_stops_the_batch_and_prevents_the_rest",
    ),
    "tier": (
        "the tier engine's block header. The committed scripts mark sections with "
        "`run-size`, and each section's tier and prerequisite are declared in "
        "docs/testing.md's tier table, swept against the script; `tier` is for a "
        "sweep run, which no committed script is (round 19 lap 1 §5.1)",
        "tests/test_uiscript_tiers.py::test_a_failure_prunes_its_dependents_and_the_run_CONTINUES",
    ),
    "needs": (
        "the tier engine's prerequisite line, used with `tier` and unused for the "
        "same reason",
        "tests/test_uiscript_tiers.py::test_a_failure_prunes_its_dependents_and_the_run_CONTINUES",
    ),
    "expect-track-records": (
        "round 39's G3 (2026-11-11), built for the burn; it belongs in "
        "fullacceptance.txt's sections F and N after `expect-ctdb whole`, so the "
        "CTDB repair has landed. The change that built it was not to edit the rig "
        "scripts (another change owned them that day), so adding the step is a "
        "TASKS row, and this entry goes when it lands",
        "tests/test_track_record.py::test_expect_track_records_runs_through_the_runner",
    ),
}

#: How many entries the list above may hold. Lower it when an entry goes; raising
#: it is a decision, made with the reason in the new entry and the commit message.
#: 3 -> 4 on 2026-11-11 for `expect-track-records`, whose rig-script step is a
#: TASKS row (see its entry); back to 3 when the step lands.
_ALLOWLIST_CEILING: int = 4


def _verbs_used_by_rig_scripts() -> dict[str, set[str]]:
    """``{verb: {script, …}}`` read from every committed rig script."""
    used: dict[str, set[str]] = {}
    scripts = sorted(_RIG_SCRIPTS.glob("*.txt"))
    # Floor: an empty folder would make every verb "unused" and every test
    # below about nothing.
    assert len(scripts) >= 5, f"only {len(scripts)} rig scripts found in {_RIG_SCRIPTS}"
    for path in scripts:
        for step in parse(path.read_text(encoding="utf-8")):
            if step.verb:
                used.setdefault(step.verb, set()).add(path.name)
    return used


def test_every_verb_is_used_by_a_rig_script_or_says_why_not() -> None:
    used = _verbs_used_by_rig_scripts()
    assert len(used) >= 60, f"only {len(used)} verbs used: the parse found too little"
    unexplained = sorted(set(VERBS) - set(used) - set(UNUSED_BY_ANY_RIG_SCRIPT))
    assert not unexplained, (
        f"verbs no committed rig script uses: {unexplained}. Use each in the script "
        "whose section exercises it, or list it in UNUSED_BY_ANY_RIG_SCRIPT with the "
        "reason and the unit test that covers it instead."
    )


def test_the_list_shrinks_when_a_verb_comes_into_use() -> None:
    """A stale entry hides the next verb that falls out of use behind it."""
    used = _verbs_used_by_rig_scripts()
    now_used = sorted(set(UNUSED_BY_ANY_RIG_SCRIPT) & set(used))
    assert not now_used, f"now used by a rig script, remove from the list: {now_used}"
    unknown = sorted(set(UNUSED_BY_ANY_RIG_SCRIPT) - set(VERBS))
    assert not unknown, f"not verbs at all, remove from the list: {unknown}"


def test_the_list_does_not_grow_without_a_decision() -> None:
    assert len(UNUSED_BY_ANY_RIG_SCRIPT) <= _ALLOWLIST_CEILING, (
        "a verb joined the unused list. Prefer using it in a rig script; if it "
        "truly cannot be, raise _ALLOWLIST_CEILING in the same change and say why "
        "in the commit message."
    )


def test_every_entry_names_a_reason_and_a_test_that_exists() -> None:
    for verb, (reason, node) in UNUSED_BY_ANY_RIG_SCRIPT.items():
        assert len(reason) >= 40, f"{verb}: the reason is not a reason: {reason!r}"
        path_text, _, name = node.partition("::")
        path = _REPO / path_text
        assert path.is_file(), f"{verb}: {path_text} does not exist"
        source = path.read_text(encoding="utf-8")
        assert re.search(rf"^\s*def {re.escape(name)}\(", source, re.MULTILINE), (
            f"{verb}: {node} names no test function"
        )


def test_abort_stops_the_batch_and_prevents_the_rest(qapp: object) -> None:
    """The one unit test of `abort` itself, named by its entry above."""
    del qapp  # the runner's timer needs the application
    from platterpus.uiscript.report import Outcome
    from platterpus.uiscript.runner import ScriptRunner

    class _NoWindow:
        """`log` and `abort` touch no window."""

    runner = ScriptRunner(_NoWindow())  # type: ignore[arg-type]  # a bare stand-in: these verbs read nothing from the window
    runner.start(parse("log before\nabort the operator stopped it\nlog after"))
    for _ in range(100):  # bounded: three steps, one per tick
        if not runner.running:
            break
        runner._tick()
    outcomes = [(s.source, s.outcome) for s in runner._report.steps]
    assert outcomes == [
        ("log before", Outcome.PASS),
        ("abort the operator stopped it", Outcome.PASS),
        ("log after", Outcome.BLOCKED),
    ], outcomes
    assert runner._report.ended_reason == "the operator stopped it"
