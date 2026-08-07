# SPDX-License-Identifier: GPL-3.0-only
"""The auto-fix addendum must not claim a re-read *improved* anything.

**The finding, from the cyanrip fork, round 7 — and it is confirmed against the
artifact rather than accepted on their say-so** (`CLAUDE.md`: *did a correction
get less scrutiny than a claim?*).

The addendum carried one unconditional sentence: *"the improved read was swapped
in."* On the J1 rip that sentence was false. Track 5 was re-ripped at `-Z 2`,
converged after 5 reads, and came back with CRC32 **`6902BCF0`** — the value the
album log had **already recorded** for it at line 396. Nothing improved. The
re-read *reproduced* the first pass, which is a better result and a different
claim, and the archival record said the wrong one.

This is the same class as the `+450` and pre-gap over-claims: a record that
asserts more than the measurement supports. So the outcome is now derived per
track from the two CRCs and is **tri-state** — confirmed, replaced, or not
determined — with "not determined" a real answer that is never rounded to either
of the others.
"""

from __future__ import annotations

from platterpus.rip_addendum import (
    OUTCOME_CONFIRMED,
    OUTCOME_REPLACED,
    OUTCOME_UNDETERMINED,
    SupersededTrack,
    render_addendum,
)

# The real values from the J1 rip (2026-08-06, Police disc, beta.8).
_J1_TRACK_5_CRC = "6902BCF0"


def _track(**kwargs: object) -> SupersededTrack:
    base: dict[str, object] = {
        "number": 5,
        "filename": "05 - Don't Stand So Close to Me.flac",
        "crc": _J1_TRACK_5_CRC,
        "secure_reread": "converged after 5 reads",
    }
    base.update(kwargs)
    return SupersededTrack(**base)  # type: ignore[arg-type]  # kwargs typed per call


def _outcome_row(text: str) -> str:
    """The single per-track `Re-read outcome:` line, for scoped assertions."""
    rows = [line for line in text.splitlines() if "Re-read outcome:" in line]
    assert len(rows) == 1, f"expected exactly one outcome row, got {len(rows)}"
    return rows[0]


class TestTheOutcomeIsDerivedNotAsserted:
    def test_identical_crcs_are_confirmed_not_improved(self) -> None:
        entry = _track(previous_crc=_J1_TRACK_5_CRC)
        assert entry.outcome == OUTCOME_CONFIRMED

    def test_different_crcs_are_replaced(self) -> None:
        assert _track(previous_crc="DEADBEEF").outcome == OUTCOME_REPLACED

    def test_a_missing_crc_on_either_side_is_not_determined(self) -> None:
        # Tri-state, and it must not fall through to either positive answer.
        assert _track(previous_crc="").outcome == OUTCOME_UNDETERMINED
        assert _track(crc="", previous_crc=_J1_TRACK_5_CRC).outcome == (
            OUTCOME_UNDETERMINED
        )

    def test_case_and_whitespace_do_not_manufacture_a_replacement(self) -> None:
        # cyanrip prints upper-case hex; a future source might not. A case
        # difference reported as REPLACED would be a fabricated finding in an
        # archival record — worse than the over-claim this replaced.
        assert _track(previous_crc=" 6902bcf0 ").outcome == OUTCOME_CONFIRMED


class TestTheRenderedText:
    def test_the_unconditional_improved_claim_is_gone(self) -> None:
        """The regression. Fails against the sentence that shipped."""
        text = render_addendum("accuraterip", [_track(previous_crc=_J1_TRACK_5_CRC)])
        assert "the improved" not in text
        assert "improved read was swapped in" not in text

    def test_a_confirmed_track_says_confirmed_and_says_why(self) -> None:
        text = render_addendum("accuraterip", [_track(previous_crc=_J1_TRACK_5_CRC)])
        assert "CONFIRMED" in text
        assert "same CRC32" in text
        # And it says a confirmed read is a good outcome, because a reader who
        # sees "not improved" without that reads it as a failure.
        assert "confirmed read is a good outcome" in text

    def test_a_replaced_track_names_the_crc_it_superseded(self) -> None:
        """Naming the old value is what makes the claim checkable."""
        text = render_addendum("accuraterip", [_track(previous_crc="AABBCCDD")])
        assert "REPLACED" in text
        assert "AABBCCDD" in text, "the superseded CRC must be in the record"

    def test_an_undetermined_track_says_so_rather_than_guessing(self) -> None:
        text = render_addendum("accuraterip", [_track(previous_crc="")])
        # Scoped to the TRACK'S OWN row, not the whole document: the preamble
        # names all three outcomes so a reader knows what the row can say, and a
        # document-wide `not in` would fail on the legend rather than the claim.
        # (Written this way after the first version did exactly that — the same
        # substring-collision trap the verb reference had.)
        row = _outcome_row(text)
        assert "NOT DETERMINED" in row
        assert "CONFIRMED" not in row
        assert "REPLACED" not in row

    def test_the_three_outcomes_render_differently(self) -> None:
        """Non-triviality floor: a constant sentence passes every test above."""
        rendered = {
            render_addendum("accuraterip", [_track(previous_crc=prev)])
            for prev in (_J1_TRACK_5_CRC, "AABBCCDD", "")
        }
        assert len(rendered) == 3

    def test_every_track_gets_its_own_outcome_row(self) -> None:
        # A disc can have several superseded tracks with different outcomes; a
        # single summary sentence for the set is how the original bug happened.
        text = render_addendum(
            "accuraterip",
            [
                _track(number=5, previous_crc=_J1_TRACK_5_CRC),
                _track(number=9, crc="11112222", previous_crc="33334444"),
            ],
        )
        assert text.count("Re-read outcome:") == 2
        assert "CONFIRMED" in text and "REPLACED" in text

    def test_it_still_returns_empty_for_no_tracks(self) -> None:
        # Unchanged contract: an empty file reads as "no supersede happened".
        assert render_addendum("accuraterip", []) == ""
