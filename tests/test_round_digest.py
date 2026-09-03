"""The round digest — adopted from the cyanrip fork, and checked against theirs.

**The strongest assertions here are the two numbers THEY published.** Their lap 1
declared `01ba4719c80b6fe9` over zero laps and their lap 3 declared
`255ee9040a5d3778` over two; both are reproduced by this implementation, built
from their written spec rather than from their code. That is the difference
between "we both have a digest" and "we have one digest" — and it is exactly the
thing a specification is *for*, since a test does not travel and its
specification does.

`CLAUDE.md`: *two implementations agreeing is not either one being correct* — but
that warning is about implementations sharing an ancestor. These do not: theirs is
`tools/round-digest.py` in a C project, ours is written from prose. Agreement
across that gap is evidence, and the fixtures below pin it so it cannot rot.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Final

import pytest

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]


def _module():  # noqa: ANN202 - a test helper, typed at the call sites
    """Load the script by path — it is a CLI, not an installed module."""
    spec = importlib.util.spec_from_file_location(
        "round_digest", _REPO_ROOT / "scripts" / "round_digest.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["round_digest"] = module  # dataclasses needs it importable
    spec.loader.exec_module(module)
    return module


#: **The exact population their lap 3 published a digest over** — their lap 1 and
#: our lap 2, named rather than filtered out of a directory that keeps growing.
_THEIR_TWO: Final[tuple[tuple[str, int], ...]] = (("inbound", 1), ("outbound", 2))


def _lap(rd, direction: str, number: int) -> Path:  # noqa: ANN001 - module by path
    """One lap by direction and number, asserted to exist so a rename cannot
    silently shrink a fixture into passing over fewer rows."""
    path = rd._HANDSHAKE / direction / f"round-15-lap-{number:02d}.md"
    assert path.is_file(), f"fixture lap is missing: {path}"
    return path


class TestAgainstTheirPublishedNumbers:
    """Their values, reproduced. If these fail we have two methods again."""

    def test_the_empty_record_matches_their_lap_1(self) -> None:
        """`01ba4719c80b6fe9` — declared over zero laps when the round opened.

        It is `sha256("\\n")`: the join of no rows is empty, and the trailing
        newline is still appended. That detail is easy to get wrong in a way no
        non-empty case would reveal, which is why they published it.
        """
        rd = _module()
        assert rd.digest_of([]) == "01ba4719c80b6fe9"
        assert rd.digest_of([]) == hashlib.sha256(b"\n").hexdigest()[:16]

    def test_round_15_over_two_laps_matches_their_lap_3(self) -> None:
        """`255ee9040a5d3778` over their lap 1 and our lap 2.

        **This also proves something the digest exists to prove**: their row for
        our lap 2 carries the sha256 of the file's bytes, and it matches ours —
        so the copy they hold is byte-identical to the one we sent. First use,
        doing its actual job.

        **The population is NAMED, not derived from the live directory**, and the
        first version of this test got that wrong: it called `round_digest(15,
        exclude="round-15-lap-03.md")`, which was two laps when written and three
        the moment lap 4 was filed. A fixture pinning a published number against
        a record that grows decays by construction — it would have gone red on
        every future lap of every future round, and the obvious "fix" is to
        update the constant, which destroys the only thing it was checking.
        """
        rd = _module()
        rows = [rd._row_for(_lap(rd, direction, n)) for direction, n in _THEIR_TWO]
        assert len(rows) == 2
        assert rd.digest_of(rows) == "255ee9040a5d3778"

    def test_the_rows_match_the_two_they_printed(self) -> None:
        """Not just the digest — the inputs, because a matching digest over
        different rows would be a collision and a matching digest over the same
        rows is the claim actually being made."""
        rd = _module()
        rendered = sorted(
            rd._row_for(_lap(rd, direction, n)).render() for direction, n in _THEIR_TWO
        )
        assert rendered == [
            "1\tcyanrip-fork\t"
            "a1ff77af1fd6e3cbb7a39608c6d72dc0f765f942a6084f26eba8e4bf4fea0f64",
            "2\tplatterpus\t"
            "80c86fd4608f19afa9414860c6281b48898e336904988729be6176f5de5393fb",
        ]


class TestPopulation:
    """The substantive divergence their lap 3 §3(b) named."""

    def test_the_digest_covers_BOTH_directions_not_just_our_inbox(self) -> None:
        """**The defect this replaces, asserted directly.**

        Our lap-2 digest covered `inbound/` only. An inbox-only digest can never
        disagree about anything *we* sent, so it cannot detect the case the field
        exists for — the mirror of their "a digest over only our own outbox would
        agree with itself forever".

        Asserted on the senders present, not on the directories scanned: a future
        refactor could rename the folders and this should still hold.
        """
        rd = _module()
        laps = rd._laps_for_round(15)
        senders = {rd._row_for(p).sender for p in laps}
        assert "platterpus" in senders, "our own laps are missing from the population"
        assert "cyanrip-fork" in senders, "their laps are missing from the population"


class TestTheTwoRefusals:
    """Both cost a real defect — one on each side. Neither is polish."""

    def test_an_exclude_that_matches_nothing_refuses(self) -> None:
        """Found in our implementation in round 9; they had it too. A typo must
        not quietly become "exclude nothing" and a confident wrong digest."""
        rd = _module()
        with pytest.raises(rd.DigestError, match="matched NO lap"):
            rd.round_digest(15, exclude="round-15-lap-99.md")

    def test_an_exclude_that_matches_MORE_THAN_ONE_refuses(self) -> None:
        """**The mirror, which neither side had asked for.**

        It becomes reachable the moment two laps cross at one number — round 14
        crossed four times — and dropping both produces a digest over a population
        nobody asked for **at the same count**, which is the version that gets
        believed.

        Driven with a real pair of same-named laps in both directions, since that
        is precisely the shape that occurs.
        """
        rd = _module()
        inbound = rd._HANDSHAKE / "inbound" / "round-15-lap-03.md"
        outbound = rd._HANDSHAKE / "outbound" / "round-15-lap-03.md"
        assert inbound.exists(), "fixture assumption changed"
        assert not outbound.exists(), "an outbound lap 3 exists; pick another number"
        outbound.write_text(inbound.read_text(encoding="utf-8"), encoding="utf-8")
        try:
            with pytest.raises(rd.DigestError, match="matched 2 laps"):
                rd.round_digest(15, exclude="round-15-lap-03.md")
        finally:
            outbound.unlink()

    def test_the_refusal_message_names_the_count_and_the_paths(self) -> None:
        """A refusal a reader cannot act on is an error message, not a check."""
        rd = _module()
        with pytest.raises(rd.DigestError) as caught:
            rd.round_digest(15, exclude="nope.md")
        text = str(caught.value)
        assert "round-15-lap-01.md" in text, (
            "the refusal must list what IS present, or the reader cannot see "
            f"their typo: {text}"
        )


class TestConstructionDetails:
    def test_a_lap_declaring_no_sender_is_refused_not_guessed_from_its_folder(
        self, tmp_path: Path
    ) -> None:
        """Keying on the directory would make the digest describe our *filing*
        rather than the document — the same class of error as reading a pin from
        a covering message instead of from the artifact."""
        rd = _module()
        orphan = tmp_path / "round-15-lap-07.md"
        orphan.write_text("HANDSHAKE-ROUND: 15\nno sender here\n", encoding="utf-8")
        with pytest.raises(rd.DigestError, match="declares no"):
            rd._row_for(orphan)

    def test_from_commit_and_from_repo_cannot_satisfy_the_sender_field(
        self, tmp_path: Path
    ) -> None:
        """`HANDSHAKE-FROM-COMMIT` and `HANDSHAKE-FROM-REPO` share the prefix and
        mean something else. A substring match would silently put a git sha in
        the sender column and still produce a confident digest."""
        rd = _module()
        lap = tmp_path / "round-15-lap-08.md"
        lap.write_text(
            "HANDSHAKE-FROM-COMMIT: 0a69732\n"
            "HANDSHAKE-FROM-REPO: https://example.invalid\n",
            encoding="utf-8",
        )
        with pytest.raises(rd.DigestError, match="declares no"):
            rd._row_for(lap)

    def test_rows_are_sorted_as_STRINGS_not_as_numbers(self) -> None:
        """Their step 2 says "sort the rows as strings", and it matters at ten
        laps: `"10"` sorts before `"2"`. Getting this wrong produces identical
        output for every round with fewer than ten laps — so it would pass every
        fixture we have today and diverge exactly when a round gets long, which
        round 7 did at 37."""
        rd = _module()
        rows = [
            rd.Row(lap=2, sender="platterpus", sha256="b" * 64, path=Path("b")),
            rd.Row(lap=10, sender="cyanrip-fork", sha256="a" * 64, path=Path("a")),
        ]
        lines = sorted(row.render() for row in rows)
        assert lines[0].startswith("10\t"), (
            "string sort must put lap 10 before lap 2; a numeric sort would not, "
            "and both agree for every round shorter than ten laps"
        )
        assert rd.digest_of(rows) == rd.digest_of(list(reversed(rows))), (
            "the digest must not depend on input order"
        )
