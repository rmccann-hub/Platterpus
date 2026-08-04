"""The handshake file naming convention, and why a filename needs a check.

## Why this exists (maintainer directive, 2026-08-04)

> *"also agree on a naming convention for the handshake files and both use it"*

The old scheme was `round-N` plus the next free letter, and **the letter encoded
nothing**. Three consequences, all real:

* `inbound/round-7f.md` was **lap 12** while `verified/round-7f.md` was **lap 10** —
  the same suffix meant different laps depending on the directory;
* `inbound/round-7d.md` and `verified/round-7d.md` were *both* lap 7, by coincidence;
* filing a received file meant finding "the next free letter", and doing it wrong
  **overwrote a previous lap**. That happened in this session: lap 12 was copied over
  `round-7c.md`, which was lap 4, and had to be restored from git.

The convention is `round-NN-lap-LL.md`, and the point is not tidiness. **The filename
now states two facts the wire header already declares**, which makes it a second
description of one thing — the exact drift this project has spent a round finding
instances of. A second description is only safe when something checks the two agree.
This file is that something.

## What is checked

1. Every file that **declares** a round and lap has a name stating them. Derived from
   the headers, so a new file is covered without a list to maintain.
2. Grandfathered files (no lap header) keep their old names, and the *converse* is
   enforced too: a canonical name must not appear on a file with no lap to state.
3. `HANDSHAKE-FROM` agrees with the directory. Direction is the directory's job.
4. Zero-pad width is uniform, so a lexical sort is chronological.
5. The generator, the parser, and the files on disk all agree.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

_REPO = Path(__file__).resolve().parents[1]
_HANDSHAKE = _REPO / "docs" / "handshake"
_DIRS = ("inbound", "outbound", "verified")

#: Which sender each directory holds. `verified` is ours — a verification of *their*
#: file, written by us.
_EXPECTED_FROM: dict[str, str] = {
    "inbound": "cyanrip-fork",
    "outbound": "platterpus",
    "verified": "platterpus",
}

_ROUND = re.compile(r"^HANDSHAKE-ROUND:\s*(\d+)\s*$", re.M)
_LAP = re.compile(r"^HANDSHAKE-LAP:\s*(\d+)\s*$", re.M)
_FROM = re.compile(r"^HANDSHAKE-FROM:\s*(\S+)\s*$", re.M)
_FENCE = re.compile(r"^```.*?^```", re.M | re.S)


def _handshake() -> ModuleType:
    """The module that OWNS the convention. Loaded, never re-implemented here."""
    script = _REPO / "scripts" / "handshake.py"
    spec = importlib.util.spec_from_file_location("handshake_naming_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def hs() -> ModuleType:
    return _handshake()


def _declared(path: Path) -> tuple[int | None, int | None, str]:
    """`(round, lap, from)` a file declares. Fenced examples stripped first.

    A declaration is what a file *states*, never what it *quotes* — the protocol's own
    rule, and the reason the spec's own examples do not register as declarations.
    """
    text = _FENCE.sub("", path.read_text(encoding="utf-8", errors="replace"))
    r, lap, sender = _ROUND.search(text), _LAP.search(text), _FROM.search(text)
    return (
        int(r.group(1)) if r else None,
        int(lap.group(1)) if lap else None,
        sender.group(1) if sender else "",
    )


def _all_files() -> list[Path]:
    return sorted(p for d in _DIRS for p in (_HANDSHAKE / d).glob("*.md"))


def test_there_are_files_to_check() -> None:
    """Floor. Every assertion below iterates; an empty tree passes them all."""
    files = _all_files()
    assert len(files) >= 20, f"only {len(files)} handshake files found"
    with_laps = [p for p in files if _declared(p)[1] is not None]
    assert len(with_laps) >= 10, (
        f"only {len(with_laps)} files declare a lap — the convention binds those, so "
        "with too few there is nothing to enforce"
    )


def test_every_lap_declaring_file_is_named_for_its_round_and_lap(
    hs: ModuleType,
) -> None:
    """The convention itself, checked against each file's own header.

    Generated with `handshake_filename`, not string-formatted here: a third description
    of the format would be the same mistake one level up.
    """
    checked = 0
    for path in _all_files():
        round_, lap, _sender = _declared(path)
        if round_ is None or lap is None:
            continue
        checked += 1
        expected = hs.handshake_filename(round_, lap)
        assert path.name == expected, (
            f"{path.parent.name}/{path.name} declares round {round_} lap {lap}, so its "
            f"name must be {expected}. The filename and the header are two descriptions "
            "of one fact; when they disagree, filing the next file guesses."
        )
    assert checked >= 10, f"only {checked} files were held to the convention"


def test_a_canonical_name_is_never_worn_by_a_file_with_nothing_to_state(
    hs: ModuleType,
) -> None:
    """The converse, which is the half a naming rule usually forgets.

    Requiring "declares a lap → named for it" alone would let a file be *named*
    `round-07-lap-99.md` while declaring nothing, which is worse than a legacy name: it
    looks canonical and is unverifiable. A check that can be satisfied by the wrong
    thing is the failure this round found twice in one file.
    """
    checked = 0
    exempt = 0
    for path in _all_files():
        pair = hs.name_round_and_lap(path)
        if pair is None:
            continue  # a grandfathered name; the test above does not bind it either
        checked += 1
        round_, lap, _sender = _declared(path)
        if lap is None:
            # THE ONE EXEMPTION, and it is derived rather than granted.
            #
            # A file that declares no lap IS its round's first (`DEFAULT_LAP`), so
            # `lap-01` states a fact about it rather than a guess. The fork reached this
            # independently in their lap 18 — they renamed their round-7 no-lap file to
            # `round-07-lap-01.md` — and our first version of this rule would have
            # rejected their tree. Two conditions keep it from becoming a hole:
            #   * the name must claim lap 1 specifically, not any lap;
            #   * it must be the round's ONLY no-lap file, checked below, or two files
            #     would both be "the first".
            assert pair[1] == hs.DEFAULT_LAP, (
                f"{path.parent.name}/{path.name} declares no lap but is named lap "
                f"{pair[1]}. Only lap {hs.DEFAULT_LAP} is derivable for a no-lap file "
                "(it is its round's first); any other number is invented."
            )
            assert round_ == pair[0] or round_ is None, (
                f"{path.parent.name}/{path.name} declares round {round_} and is named "
                f"round {pair[0]}"
            )
            exempt += 1
            continue
        assert (round_, lap) == pair, (
            f"{path.parent.name}/{path.name} wears a canonical name claiming round "
            f"{pair[0]} lap {pair[1]}, but declares {(round_, lap)}. A canonical name "
            "on a file that cannot back it up is a false label."
        )
    assert checked >= 10, f"only {checked} canonical names were verified"
    assert exempt >= 1, (
        "no no-lap file wears a lap-01 name, so the derived exemption above is "
        "untested — and it is the clause that lets our tree and the fork's agree"
    )


def test_only_one_file_per_round_can_be_its_first(hs: ModuleType) -> None:
    """The second condition on the lap-01 exemption, which makes it safe.

    `lap-01` is derivable for a no-lap file *because* the file is its round's first. Two
    no-lap files in one round would both claim that, and the name would be back to
    stating a guess — which is how round 6's three amendment files must keep their legacy
    names rather than all becoming lap 1.
    """
    checked = 0
    for directory in _DIRS:
        rounds: dict[int, list[Path]] = {}
        for path in sorted((_HANDSHAKE / directory).glob("*.md")):
            number = hs.round_number(path)
            if number is None:
                continue
            rounds.setdefault(number, []).append(path)
        for number, members in rounds.items():
            no_lap = [p for p in members if _declared(p)[1] is None]
            named_first = [
                p for p in no_lap if (hs.name_round_and_lap(p) or (0, 0))[1] == 1
            ]
            if not named_first:
                continue
            checked += 1
            assert len(no_lap) == 1, (
                f"{directory}/round {number}: {[p.name for p in no_lap]} all declare no "
                f"lap, and {[p.name for p in named_first]} claims to be the first. With "
                "more than one, 'the round's first file' is not a derivable fact and "
                "they must keep legacy names."
            )
    assert checked >= 1, "no round exercises the first-file claim"


def test_grandfathered_files_are_exactly_the_ones_with_no_lap_header(
    hs: ModuleType,
) -> None:
    """The exemption is *derived*, not a list — which is why it cannot rot.

    A file predating the lap header has nothing to name itself with, so it keeps its
    old name. That is a property of the file, checkable, and it needs no allowlist —
    the shape that hid 16 of the fork's fatal strings behind their generator's filter.
    """
    legacy = 0
    out_of_scope: list[str] = []
    for path in _all_files():
        round_, lap, _sender = _declared(path)
        canonical = hs.name_round_and_lap(path) is not None
        named_round = hs.round_number(path)
        if round_ is None and named_round is None:
            # Not round correspondence at all — the directory also holds standalone
            # notes (a beta announcement). `--status` already ignores these by
            # returning None rather than raising, which is the behaviour that keeps an
            # unrelated file from taking the report down.
            out_of_scope.append(path.name)
            continue
        if lap is None:
            legacy += 1
            if canonical:
                # The derived exemption: a no-lap file IS its round's first, so
                # `lap-01` states a fact. Bounded to lap 1 and to being the round's
                # only no-lap file — both checked by the two tests above.
                assert (hs.name_round_and_lap(path) or (0, 0))[1] == hs.DEFAULT_LAP, (
                    f"{path.parent.name}/{path.name} declares no lap and is named for "
                    f"a lap other than {hs.DEFAULT_LAP}, which is not derivable"
                )
        else:
            assert canonical, (
                f"{path.parent.name}/{path.name} declares a lap, so its name must be "
                "canonical"
            )
        assert named_round is not None, (
            f"{path.parent.name}/{path.name}: no round can be read from the name, so "
            "the status report cannot place it in a round at all"
        )
    assert legacy >= 5, (
        f"only {legacy} grandfathered files — if that reached zero the legacy branch "
        "of the parser is untested by the real tree"
    )
    # The skip must stay a narrow escape hatch, not a hole the whole sweep falls into.
    assert len(out_of_scope) <= 3, (
        f"{len(out_of_scope)} files are neither named for a round nor declare one: "
        f"{out_of_scope}. Too many, and this test is skipping the tree rather than "
        "checking it."
    )


def test_the_sender_agrees_with_the_directory() -> None:
    """Direction is the directory's job, so the two must not disagree.

    This is the check that would have caught the filing mistake by its *other* face:
    dropping their file into `verified/` would put a `cyanrip-fork` declaration in a
    directory of ours.
    """
    checked = 0
    for path in _all_files():
        _round, lap, sender = _declared(path)
        if lap is None or not sender:
            continue  # pre-header files declare no sender
        checked += 1
        assert sender == _EXPECTED_FROM[path.parent.name], (
            f"{path.parent.name}/{path.name} declares HANDSHAKE-FROM: {sender}, but "
            f"{path.parent.name}/ holds {_EXPECTED_FROM[path.parent.name]} files. "
            "Either it is filed in the wrong directory or the header is wrong."
        )
    assert checked >= 8, f"only {checked} files declared a sender"


def test_no_two_files_in_a_directory_claim_the_same_lap() -> None:
    """The failure that actually happened, asserted directly.

    Lap 12 was copied over lap 4 because the old scheme's "next free letter" is a
    judgement, not a fact. Under the convention a collision is a name collision, which
    the filesystem itself refuses — but only while every file is named canonically, and
    only while nothing files by hand into a legacy name. So: check it.
    """
    for directory in _DIRS:
        seen: dict[tuple[int, int], Path] = {}
        for path in sorted((_HANDSHAKE / directory).glob("*.md")):
            round_, lap, _sender = _declared(path)
            if round_ is None or lap is None:
                continue
            key = (round_, lap)
            assert key not in seen, (
                f"{directory}/: both {seen[key].name} and {path.name} claim round "
                f"{round_} lap {lap}. One of them is a misfiled copy."
            )
            seen[key] = path


def test_the_pad_width_is_uniform_so_a_lexical_sort_is_chronological(
    hs: ModuleType,
) -> None:
    """Mixed widths silently break `sorted()`, which several tools here rely on.

    `scripts/handshake.py` sorts by stem to establish reading order within a round, and
    `round-7-lap-9` would sort after `round-7-lap-10`. The convention pads; this checks
    the tree actually did.
    """
    widths: set[int] = set()
    for path in _all_files():
        pair = hs.name_round_and_lap(path)
        if pair is None:
            continue
        match = re.match(r"^round-(\d+)-lap-(\d+)$", path.stem)
        assert match, path.name
        widths.add(len(match.group(1)))
        widths.add(len(match.group(2)))
    assert widths, "no canonical names to measure"
    assert widths == {hs.NAME_PAD}, (
        f"canonical names use pad widths {sorted(widths)}, expected all "
        f"{hs.NAME_PAD}. Mixed widths make a lexical sort non-chronological, which is "
        "the property the padding exists for."
    )


def test_a_canonical_sort_really_is_chronological(hs: ModuleType) -> None:
    """The property, not just the padding that is supposed to deliver it.

    Checking the pad width is checking the mechanism; this checks the outcome. With
    laps 2..16 present in one round, a nine-to-ten boundary is actually crossed, which
    is where an unpadded scheme breaks.
    """
    for directory in _DIRS:
        pairs = [
            hs.name_round_and_lap(p)
            for p in sorted((_HANDSHAKE / directory).glob("*.md"))
            if hs.name_round_and_lap(p) is not None
        ]
        if len(pairs) < 3:
            continue
        assert pairs == sorted(pairs), (
            f"{directory}/: lexical filename order {pairs} is not chronological"
        )
        # And the boundary that matters is actually exercised somewhere.
        laps = [lap for _round, lap in pairs]
        if max(laps) >= 10:
            assert min(laps) < 10, (
                f"{directory}/: laps {laps} never cross the 9→10 boundary, so this "
                "test would pass under an unpadded scheme too"
            )


def test_the_artifacts_name_their_round_lap_and_build() -> None:
    """Inbound artifacts follow too, with the build that PRODUCED them.

    `round-07-lap-14-golden-reference-g486dce3.log`. The build rather than the commit
    the lap file names it by, because the build is the fact **derivable from the
    artifact's own content** — see `tests/test_golden_reference_parse.py`, where that
    distinction is a finding rather than a preference.
    """
    artifacts = sorted((_HANDSHAKE / "inbound" / "artifacts").glob("*"))
    assert artifacts, "no inbound artifacts; nothing to check"
    pattern = re.compile(r"^round-\d{2,4}-lap-\d{2,4}-[a-z0-9-]+-g[0-9a-f]{7,40}$")
    for path in artifacts:
        assert pattern.match(path.stem), (
            f"{path.name} does not follow round-NN-lap-LL-<kind>-g<build>.<ext>"
        )


def test_the_newest_file_in_a_round_is_the_highest_lap(hs: ModuleType) -> None:
    """**REGRESSION, and it flipped a release gate.**

    The rename left the pre-lap-header `round-7.md` beside `round-07-lap-16.md`, and
    lexically `"round-07-lap-16" < "round-7"` — `'0' < '7'` at the seventh character.
    `_round_files` sorted by stem, so the fork's **lap 1** file sorted last and was read
    as the newest. `--status` went from `they-verified=HOLD` to **`GO`** for an open
    round: a gate that refuses a release said the round had closed, because of a
    filename.

    Fixed by ordering on the declared lap rather than the string. Asserted here because
    "the newest file is the latest lap" is the property every verdict read depends on,
    and it was silently false for one commit.
    """
    for directory in _DIRS:
        files = hs._round_files(_HANDSHAKE / directory, 7)
        if len(files) < 3:
            continue
        laps = [hs._lap_of(p) for p in files]
        assert laps == sorted(laps), (
            f"{directory}/: round 7 files are ordered {[p.name for p in files]}, laps "
            f"{laps} — not oldest-first by lap, so the newest verdict read is wrong"
        )
        # A floor on the REAL tree: without a lap past 9 the string sort and the lap
        # sort agree and this proves nothing.
        assert max(laps) >= 10, (
            f"{directory}/: highest lap is {max(laps)}; below 10 the string sort and "
            "the lap sort agree and the bug is unreachable"
        )
        # NOT a floor requiring a legacy-named file. The first version of this test
        # demanded one, because the tree had one — and the fork's lap 18 renamed theirs
        # to `round-07-lap-01.md`, which we matched, so the mix vanished and the floor
        # started failing on a tree that was MORE correct. A floor tied to incidental
        # tree contents expires; the mixed-scheme proof lives in the synthetic test
        # below, which cannot.


def test_a_legacy_name_sorts_before_a_canonical_one_in_the_same_round(
    hs: ModuleType,
) -> None:
    """The mechanism, isolated from the real tree so it cannot go quiet.

    The tree happens to contain the mix today. If it ever stops, the test above skips
    and this one still pins the ordering rule — that a file declaring no lap is treated
    as the earliest in its round, which is what the pre-header files are.
    """
    assert hs._lap_of(Path("round-7.md")) == hs.DEFAULT_LAP == 1, (
        "a file with no declared lap must sort as lap 1 — it IS its round's first, and "
        "lap 0 invents a lap that never existed. The fork's rule, adopted in lap 19 "
        "after their lap 18 showed we had picked different numbers for one convention."
    )
    assert hs._lap_of(Path("round-07-lap-16.md")) == 16
    assert sorted(
        [Path("round-07-lap-16.md"), Path("round-7.md")],
        key=lambda p: (hs._lap_of(p), p.stem),
    ) == [Path("round-7.md"), Path("round-07-lap-16.md")]
    # And prove the naive key gets it wrong, so the fix is not decoration.
    assert sorted(
        [Path("round-07-lap-16.md"), Path("round-7.md")], key=lambda p: p.stem
    ) == [Path("round-07-lap-16.md"), Path("round-7.md")], (
        "the stem sort no longer misorders these, so this regression is no longer "
        "reachable and the ordering rule needs re-justifying"
    )


def test_the_declared_lap_beats_the_name_when_they_could_disagree(
    hs: ModuleType, tmp_path: Path
) -> None:
    """The header is the declaration; the name describes it. Order on the declaration.

    They cannot disagree in our tree — a test above forbids it — but `_lap_of` is also
    handed *their* files, which we do not control, and a mislabelled incoming file must
    still be ordered by what it says it is.
    """
    mislabelled = tmp_path / "round-07-lap-02.md"
    mislabelled.write_text(
        "\n".join(
            ("HANDSHAKE-PROTOCOL: 2", "HANDSHAKE-ROUND: 7", "HANDSHAKE-LAP: 20", "")
        ),
        encoding="utf-8",
    )
    assert hs._lap_of(mislabelled) == 20, (
        "the name was trusted over the header; a file that says lap 20 must sort as 20"
    )


def test_an_ambiguous_lap_declaration_sorts_LAST_so_it_cannot_hide(
    hs: ModuleType, tmp_path: Path
) -> None:
    """**A hole on our side, closed by adopting the fork's rule (their lap 18 §B1).**

    We used to fall back to the *filename* when `HANDSHAKE-LAP` was declared twice with
    different values. So a file named `lap-09` declaring both 9 and 20 sorted at 9, a
    later valid file was read as the newest, and **the ambiguity was never examined by
    the gate at all** — the protocol's own "present-but-ambiguous is worse than absent"
    principle broken in the direction that hides it.

    Their rule: ambiguous **wins** the sort, so it becomes the file the verdict is read
    from and `check_wire_header` refuses it by name. Comparing two implementations of
    one convention is what surfaced this; no test on either side had it.
    """
    lines = ("HANDSHAKE-PROTOCOL: 2", "HANDSHAKE-ROUND: 7")
    good = tmp_path / "round-07-lap-16.md"
    good.write_text("\n".join((*lines, "HANDSHAKE-LAP: 16", "")), encoding="utf-8")
    ambiguous = tmp_path / "round-07-lap-09.md"
    ambiguous.write_text(
        "\n".join((*lines, "HANDSHAKE-LAP: 9", "HANDSHAKE-LAP: 20", "")),
        encoding="utf-8",
    )

    assert hs._lap_of(ambiguous) == hs.AMBIGUOUS_LAP
    assert hs._lap_of(ambiguous) > hs._lap_of(good), (
        "an ambiguous declaration must outrank every real lap, or a later valid file "
        "is read as the newest and the ambiguity is never surfaced"
    )
    ordered = sorted([good, ambiguous], key=hs.sort_key)
    assert ordered[-1] == ambiguous, [p.name for p in ordered]

    # And prove the OLD behaviour would have hidden it — the fix is not decoration.
    naive = sorted([good, ambiguous], key=lambda q: hs.name_round_and_lap(q) or (0, 0))
    assert naive[-1] == good, (
        "reading the name would no longer put the valid file last, so this regression "
        "is unreachable and the rule needs re-justifying"
    )

    # The ambiguity is then actually refused, rather than merely sorted first.
    problems = hs.check_wire_header(ambiguous, expect_from=None)
    assert any("more than once" in str(x) for x in problems), problems


def test_the_generator_round_trips_through_the_parser(hs: ModuleType) -> None:
    """A name we can write but not read back is a convention with a hole in it."""
    for round_, lap in ((7, 16), (1, 1), (99, 99), (12, 3)):
        name = hs.handshake_filename(round_, lap)
        assert hs.name_round_and_lap(Path(name)) == (round_, lap), name
        assert hs.round_number(Path(name)) == round_, name


def test_the_convention_is_documented_where_a_reader_will_look() -> None:
    """A convention only in code is one the next person re-invents.

    Deliberately checks for the *shape* rather than prose about it: the example name
    has to be present, because that is what someone filing a file copies.
    """
    readme = _HANDSHAKE / "README.md"
    assert readme.is_file(), "docs/handshake/README.md is missing"
    text = readme.read_text(encoding="utf-8")
    assert "round-NN-lap-LL" in text or "round-07-lap" in text, (
        "the handshake README does not state the file naming convention, so the next "
        "person to file a received file will guess — which is how lap 4 got overwritten"
    )
