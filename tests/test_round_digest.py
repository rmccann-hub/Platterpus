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
from types import ModuleType
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


class TestTheThreeRefusals:
    """Each cost a real defect. None is polish."""

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


class TestExcludeAccumulates:
    """**The third refusal: a repeated `--exclude` silently kept one name.**

    `--exclude` was a single-value argparse option, so ``--exclude A --exclude B``
    resolved to `B` alone and the command printed a digest, exit 0, and a lap
    count over a population that still held `A`. Found 2026-09-07 while
    re-deriving the fork's lap-4 digest, which needs BOTH their lap 4 and our
    lap 5 left out — the case is reachable whenever a peer's number predates a lap
    now in the tree, which is every time a round continues.

    Same family as the two refusals above and it arrived through the *interface*
    rather than the matching, which is why neither of those caught it.

    **THE EXCLUSION LISTS BELOW ARE DERIVED FROM THE TREE, NOT WRITTEN DOWN, AND
    THAT IS THE SECOND LESSON OF THIS CLASS.** The first version of these two
    tests hard-coded ``["round-16-lap-04.md", "round-16-lap-05.md"]`` against
    `a82355334b9d1bfe over 3` — correct on the day, and red within the hour, when
    the fork's lap 6 arrived and made that same exclusion a **4**-lap population.

    A regression test for *"a digest read from an open population"* had itself
    pinned a digest read from an open population. `CLAUDE.md`'s question is *is
    the population I measured closed?* and the answer for a round in progress is
    permanently no: laps keep arriving, so any list of "the laps after N" written
    as a literal expires at the next one. Deriving it means the assertion is about
    the *cutoff* — which is the fixed thing a peer's published digest names — and
    not about which laps happen to exist today.
    """

    @staticmethod
    def _laps_above(rd: ModuleType, round_: int, cutoff: int) -> list[str]:
        """Every lap filename of ``round_`` numbered above ``cutoff``.

        Derived, for the reason in the class docstring. Also the reason the
        callers assert a floor of two: if this ever returns one name the
        multi-exclude path stops being exercised and the test degrades into the
        single-exclude case it was written to distinguish from.
        """
        names = [p.name for p in rd._laps_for_round(round_)]
        return [n for n in names if int(rd._LAP_NAME.match(n).group("lap")) > cutoff]

    def test_two_excludes_drop_two_laps(self) -> None:
        """The regression, on the real record, against numbers THEY published.

        Both values are declared in the fork's own lap headers, so this asserts
        against their artifacts rather than against our re-run — and neither is
        reachable unless every name in the derived list is honoured.
        """
        rd = _module()
        # (cutoff, the digest the fork published over laps 1..cutoff)
        published = [(3, "a82355334b9d1bfe"), (5, "c880f1e2f9d32e35")]
        checked = 0
        for cutoff, expected in published:
            drop = self._laps_above(rd, 16, cutoff)
            if len(drop) < 2:
                continue  # not yet enough laps above it to exercise the path
            got = rd.round_digest(16, exclude=drop)
            assert got == (expected, cutoff), (
                f"excluding {len(drop)} laps above {cutoff} must leave {cutoff}: "
                f"this is the fork's own published digest and we got {got} "
                f"having dropped {drop}"
            )
            checked += 1
        assert checked >= 1, (
            "no cutoff had two or more laps above it, so the multi-exclude path "
            "was never exercised and this test asserted nothing"
        )

    def test_one_exclude_and_many_are_not_the_same_population(self) -> None:
        """The direct statement of the defect, independent of any published value.

        Kept separate from the test above so the regression survives a round with
        no peer digest to compare against: dropping N names must remove N laps,
        whatever the digest comes out as.
        """
        rd = _module()
        drop = self._laps_above(rd, 16, 3)
        assert len(drop) >= 2, f"need two laps above 3 to test this; got {drop}"
        many = rd.round_digest(16, exclude=drop)
        one = rd.round_digest(16, exclude=drop[:1])
        assert many[1] == one[1] - (len(drop) - 1), (
            f"dropping {len(drop)} names removed {one[1] - many[1] + 1} laps, "
            f"not {len(drop)}: {one} vs {many}"
        )
        assert many[0] != one[0], (
            "two different populations produced the same digest, so the extra "
            f"names were ignored: {one} vs {many}"
        )

    def test_the_cli_accumulates_rather_than_overwriting(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Through `main`, because the defect lived in the argparse spec.

        **And it asserts the DIGEST IT PRINTED, not that it exited 0.** The first
        version of this test checked only the return code — which a revert probe
        graded VACUOUS in one run, because dropping `action="append"` leaves a
        perfectly successful command that silently excluded one lap instead of
        two. An exit code cannot distinguish "did the right thing" from "did a
        different thing without complaining", and a silent wrong answer is the
        whole subject here.
        """
        rd = _module()
        drop = self._laps_above(rd, 16, 3)
        assert len(drop) >= 2, f"need two laps above 3 to test this; got {drop}"
        argv = ["16"]
        for name in drop:
            argv += ["--exclude", name]
        code = rd.main(argv)
        assert code == 0
        printed = capsys.readouterr().out
        assert "a82355334b9d1bfe" in printed and "over 3 lap(s)" in printed, (
            "the CLI did not honour every exclude — it printed a digest over the "
            f"wrong population: {printed.strip()!r} after dropping {drop}"
        )

    def test_a_bare_string_is_ONE_name_not_a_sequence_of_characters(self) -> None:
        """`str` is a `Sequence[str]`, so the widened parameter had a trap in it.

        Without the normalisation, ``exclude="round-16-lap-05.md"`` iterates 22
        characters and raises "matched NO lap" on the first — a confusing refusal
        for a correct call, and the shape every existing caller here uses.
        """
        rd = _module()
        assert rd.round_digest(16, exclude="round-16-lap-05.md") == rd.round_digest(
            16, exclude=["round-16-lap-05.md"]
        )

    def test_show_rows_and_the_digest_share_ONE_exclusion_filter(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The rows PRINTED must describe the population the digest used.

        `--show-rows` filtered the list inline with no refusals, so an ambiguous
        or typo'd exclude printed a full set of rows and only then errored — rows
        describing a population the digest had refused to compute. Two
        implementations of one filter.

        **Driven through `main`, not through `laps_after_exclusions`.** The first
        version called the shared helper directly and a revert probe graded it
        VACUOUS: the helper was never the broken half, the CALL SITE was, so a
        test of the helper passes against a `--show-rows` that ignores it
        entirely. Asserting the function is not asserting the caller.
        """
        rd = _module()
        assert rd.main(["16", "--show-rows", "--exclude", "round-16-lap-05.md"]) == 0
        out = capsys.readouterr().out
        rows = [line for line in out.splitlines() if "\t" in line]
        _, count = rd.round_digest(16, exclude=["round-16-lap-05.md"])
        assert len(rows) == count >= 3, (
            f"--show-rows printed {len(rows)} rows for a {count}-lap digest:\n{out}"
        )
        excluded_sha = hashlib.sha256(
            (rd._HANDSHAKE / "outbound" / "round-16-lap-05.md").read_bytes()
        ).hexdigest()
        assert excluded_sha not in out, (
            "--show-rows printed the row for the lap it was told to exclude"
        )

    def test_a_typod_exclude_refuses_BEFORE_show_rows_prints_anything(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The other half: rows must not be printed for a population that refuses.

        A reader who sees rows and then an error has been shown a population the
        tool declined to compute — worse than no output, because the rows look
        like the answer.
        """
        rd = _module()
        assert rd.main(["16", "--show-rows", "--exclude", "nope.md"]) == 2
        captured = capsys.readouterr()
        assert not [line for line in captured.out.splitlines() if "\t" in line], (
            f"rows were printed despite the refusal:\n{captured.out}"
        )
        assert "matched NO lap" in captured.err
