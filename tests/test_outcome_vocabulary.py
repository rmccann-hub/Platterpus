"""Our outcome tokens against round 18's agreed seven-concept table.

**Why this file exists.** Round 18 found that Platterpus and the cyanrip fork used
the same two tokens for **opposite** halves of one distinction: our `SKIPPED` was a
*consequence* and theirs a *decision*; our `BLOCKED` a decision and theirs a
consequence. We found it ourselves and reported it (our round-18 lap 2 §B2); they
confirmed it *"exactly as you stated it"*.

**The dangerous part was that nothing could see it.** Each side's tokens were
internally consistent, so every gate on both sides was green, and a transcript
carrying inverted meanings still parsed as well-formed. *"Adopt their word"* — which
our own status had recommended — would have inverted both meanings silently.

Round 18's fix was structural rather than either side renaming quietly: **the spec
names the CONCEPT and the TOKEN separately**, so a project whose token already means
the other thing renames once, deliberately. This file is the standing check that our
half of that mapping is what was agreed, and it is written against the table as
published in their lap 3 §2 rather than against our own belief about it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from platterpus.uiscript.report import (
    CONCEPT,
    GOOD,
    OUTCOME_VOCABULARY,
    Outcome,
    RunReport,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_THEIR_LAP = _REPO_ROOT / "docs" / "handshake" / "inbound" / "round-18-lap-03.md"

#: concept -> the token we agreed to emit for it. Their lap 3 §2, "our token"
#: column — theirs is the agreed spelling and ours is what moved.
_AGREED: dict[str, str] = {
    "pass": "PASS",
    "assertion-failed": "FAIL",
    "harness-failed": "ERROR",
    "declined": "SKIPPED",
    "prevented": "BLOCKED",
    "unreachable": "UNREACHABLE",
    "gathered": "INFO",
}


def test_we_emit_every_agreed_token() -> None:
    """Seven concepts, seven tokens, and we have all of them.

    `UNREACHABLE` is the one we had no state for at all — our own §B3 said so — so
    a step impossible on this equipment was reported as one we *declined*, which
    reads as a choice the operator could reverse.
    """
    have = {o.name for o in Outcome}
    missing = sorted(set(_AGREED.values()) - have)
    assert not missing, (
        f"agreed token(s) {missing} are not in Outcome. The concepts are settled "
        "(round 18 lap 3 §2); a missing token means a real state has nowhere to go "
        "and gets reported as a neighbouring one."
    )


def test_the_two_that_were_swapped_now_mean_what_was_agreed() -> None:
    """The actual subject of the round, asserted on the CONCEPT and not the spelling.

    A rename test that only checked *"both names exist"* would pass against the
    inverted mapping, which is the state this round was called to fix.

    **The first version of this read the meanings out of the enum's inline comments,
    and `ruff format` broke it within the hour** by wrapping one member onto two
    lines — the reflowed-anchor failure this repo already documents, arriving in a
    test written the same morning it was documented. Layout is not a data structure;
    `CONCEPT` is.
    """
    assert CONCEPT[Outcome.SKIPPED] == "declined", (
        f"SKIPPED names {CONCEPT[Outcome.SKIPPED]!r}. Round 18 settled it as "
        "'declined' — *we chose not to run it*. If this inverted, every transcript "
        "written since 2026-09-14 disagrees with the ones before it, invisibly, and "
        "both projects' gates stay green while it happens."
    )
    assert CONCEPT[Outcome.BLOCKED] == "prevented", (
        f"BLOCKED names {CONCEPT[Outcome.BLOCKED]!r}. Round 18 settled it as "
        "'prevented' — *wanted to, could not; names the failed prerequisite*."
    )
    # Every token carries a concept, and every agreed concept has a token. Either
    # gap would let a state be emitted that the other project cannot interpret.
    assert set(CONCEPT) == set(Outcome), sorted(
        o.name for o in set(Outcome) - set(CONCEPT)
    )
    assert set(CONCEPT.values()) == set(_AGREED), (
        f"our concepts are {sorted(set(CONCEPT.values()))}; the agreed seven are "
        f"{sorted(_AGREED)}"
    )
    for concept, token in _AGREED.items():
        assert CONCEPT[Outcome[token]] == concept, (
            f"{token} names {CONCEPT[Outcome[token]]!r}, agreed as {concept!r}"
        )


def test_the_agreed_table_is_still_the_one_we_are_matching() -> None:
    """Read the CONCEPTS out of their committed lap, not out of this file.

    `CLAUDE.md`: *am I answering from the artifact, or from my memory of it?* The
    table above is a transcription, and a transcription can drift from its source.
    This fails if their lap no longer contains a concept we claim it agreed — which
    is the only way to notice that `_AGREED` has become our own invention.
    """
    assert _THEIR_LAP.is_file(), (
        f"{_THEIR_LAP.name} is missing — the source of the table"
    )
    lap = _THEIR_LAP.read_text(encoding="utf-8")
    missing = [c for c in _AGREED if f"**{c}**" not in lap]
    assert not missing, (
        f"concept(s) {missing} are not named in their lap 3 §2, so `_AGREED` is no "
        "longer a transcription of the agreed table."
    )
    # FLOOR: a lap that lost its table entirely would make the check above pass by
    # having nothing to disagree with.
    assert lap.count("| **") >= 7, (
        "their lap no longer parses as carrying a seven-row concept table"
    )


def test_the_good_sweep_has_something_to_sweep() -> None:
    """The floor for the parametrized check below.

    That check generates one case per agreed token, so an emptied `_AGREED` would
    generate **no** cases and the sweep would pass having examined nothing — pytest
    reports `1 skipped`, exit 0. `CLAUDE.md`: *can this check be satisfied by
    finding nothing?*
    """
    assert len(_AGREED) == 7, (
        f"_AGREED holds {len(_AGREED)} concept(s); round 18 settled SEVEN, and each "
        "implies a different action — none is a synonym. A shrunken table makes the "
        "per-token sweep below examine less while still reporting green."
    )
    assert len(set(_AGREED.values())) == 7, "two concepts share a token"


@pytest.mark.parametrize("token", sorted(_AGREED.values()))
def test_only_pass_and_gathered_count_as_good(token: str) -> None:
    """A run is ok only when every step passed or merely measured.

    Stated per-token so a future state cannot be added straight into `GOOD` without
    this saying so. `UNREACHABLE` is deliberately NOT good: a step that cannot run
    on this equipment is honestly unverified, and counting it as a pass would let a
    rig with missing hardware report a complete run.
    """
    outcome = Outcome[token]
    expected_good = token in {"PASS", "INFO"}
    assert (outcome in GOOD) is expected_good, (
        f"{token} is {'in' if outcome in GOOD else 'not in'} GOOD; expected the "
        f"opposite. GOOD decides whether a whole run reads as ok."
    )


def test_the_report_declares_which_vocabulary_it_speaks() -> None:
    """Without this, our own archive carries the collision the round existed to fix.

    `"skipped"` in a report written before 2026-09-14 means *prevented*; in one
    written after it means *declined*. **Three committed handshake artifacts already
    carry the old spelling** and were sent to the fork as evidence, so the two
    vocabularies coexist in this repository permanently. `app_version` was the only
    version the script report carried, which makes the vocabulary derivable only by
    looking up which release changed it.
    """
    report = RunReport(started_at="t", app_version="v")
    emitted = json.loads(json.dumps(report.as_dict()))
    assert emitted.get("outcome_vocabulary") == OUTCOME_VOCABULARY, (
        "the script report does not declare `outcome_vocabulary`. Two of its "
        "`outcome` values changed meaning on 2026-09-14; a reader without this "
        "field cannot tell which sense a given transcript uses."
    )
    assert OUTCOME_VOCABULARY >= 2, (
        f"OUTCOME_VOCABULARY is {OUTCOME_VOCABULARY}; the round-18 rename is "
        "vocabulary 2. Bump it when a token changes MEANING — not when one is added."
    )


def test_the_frozen_evidence_we_already_sent_is_vocabulary_one() -> None:
    """The artifacts that make the versioning necessary, named so they stay named.

    These are committed, frozen and correct **for vocabulary 1**. They must not be
    'fixed' to the new spelling: they record what those runs actually reported, and
    rewriting sent evidence is the §4a violation this project has already had once.
    """
    frozen = [
        _REPO_ROOT
        / "docs/handshake/outbound/artifacts/round-15-lap-13-run-report.json",
        _REPO_ROOT / "docs/handshake/artifactsround08/round08scriptreport.json",
        _REPO_ROOT / "docs/handshake/artifactsround08/round08pinscriptreport.json",
    ]
    present = [p for p in frozen if p.is_file()]
    assert len(present) >= 2, (
        f"only {len(present)} of the named vocabulary-1 artifacts resolve; this "
        "check would pass by not looking. If they moved, move this list with them."
    )
    for path in present:
        blob = json.loads(path.read_text(encoding="utf-8"))
        assert "outcome_vocabulary" not in json.dumps(blob), (
            f"{path.name} declares an outcome vocabulary. It predates the field, so "
            "either it was rewritten — which sent evidence must never be — or the "
            "field's meaning has drifted."
        )
