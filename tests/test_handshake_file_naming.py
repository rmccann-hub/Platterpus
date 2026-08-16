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
import tempfile
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


#: Files in the handshake tree that are NOT laps and must not be judged as ones.
#:
#: **Empty, and that is the goal state.** It briefly held a transport envelope —
#: one file wrapping several laps so the operator could send one attachment. That
#: container was retired on 2026-08-15: a lap file **is** the interchange format,
#: cyanrip sends plain laps, and a wrapper that carries wire headers in its body is
#: a thing every content-based sweep on both sides has to be taught to ignore. It
#: cost us one such lesson in `tests/test_handshake_file_naming.py` and another in
#: `scripts/round_digest.py`, where it was silently counted as a lap.
#:
#: Keep it empty. If something must go in, it needs a written reason and a test
#: that the excluded file genuinely cannot be read as a lap.
_NOT_LAPS: frozenset[str] = frozenset()


def _is_one_lap(path: Path) -> bool:
    """v4 §5a — a file is ONE lap only if it declares each of the three
    identifying fields exactly once, fences stripped.

    **Replaces a filename allowlist**, which is the weaker thing it used to be:
    a list only ever excludes the container someone has already met. This is the
    same predicate `scripts/round_digest.py::is_a_lap` uses, and it is the rule
    cyanrip adopted into the shared spec in round 9 lap 3 §B1 — so the naming
    sweep and the digest now agree about what a lap is, which they did not when
    the digest counted an envelope as one.

    **The threshold differs from the digest's on purpose, and the difference is
    the grandfathered files.** Here a file is excluded only when a field is
    declared **more than once** — the §2 rule 3 ambiguity clause. `round_digest`
    additionally requires each field to be present *at all*, because a lap with no
    round number cannot be placed in a round; this sweep must still judge the
    pre-header files of rounds 1–6, which declare none of the three and are
    perfectly legitimate laps. Same rule, two thresholds, each matched to what its
    caller needs from it.
    """
    text = _FENCE.sub("", path.read_text(encoding="utf-8", errors="replace"))
    return not any(
        len(re.findall(rf"^{field}:", text, re.MULTILINE)) > 1
        for field in ("HANDSHAKE-ROUND", "HANDSHAKE-LAP", "HANDSHAKE-FROM")
    )


def _lap_files_in(directory: str) -> list[Path]:
    """Every candidate lap in one directory, envelope excluded.

    A single chokepoint on purpose. Four sweeps in this module globbed the
    directory themselves, and adding the exclusion to `_all_files` alone fixed
    two of them and left two reading the envelope as a lap — the same
    "enforce a rule at the place it was learned" failure `docs/testing.md` §5.o
    records. Route every sweep through here.
    """
    return sorted(
        p
        for p in (_HANDSHAKE / directory).glob("*.md")
        if p.name not in _NOT_LAPS and _is_one_lap(p)
    )


def _all_files() -> list[Path]:
    return sorted(p for d in _DIRS for p in _lap_files_in(d))


def test_nothing_is_excluded_and_the_guard_still_works_if_something_is() -> None:
    """The exclusion list must not become a place to hide a misfiled lap.

    Two checks, because either alone is satisfiable by the wrong thing: the file
    must exist (a stale entry silently excuses nothing and hides that it is
    stale), and it must be structurally incapable of being read as a lap — no
    wire header at column 0 of its own, and a name no gate's glob can reach.
    """
    assert not _NOT_LAPS, (
        "the exclusion list is meant to be empty — a container in the handshake "
        "tree is a thing every sweep on both sides must be taught to ignore. "
        "Adding one needs a written reason here."
    )
    for name in _NOT_LAPS:  # pragma: no cover — empty by design; the guard below
        matches = [p for d in _DIRS for p in (_HANDSHAKE / d).glob(name)]
        assert len(matches) == 1, f"{name}: expected exactly one, found {matches}"
        path = matches[0]
        assert not path.name.lower().startswith("round-"), (
            f"{name} matches the round-*.md glob every gate uses; excluding it "
            "from the naming sweep would leave it readable as a lap"
        )
        first = path.read_text(encoding="utf-8").splitlines()[0]
        assert not first.startswith("HANDSHAKE-"), (
            f"{name} opens with a wire header, so it IS declaring itself a lap"
        )


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
        for path in _lap_files_in(directory):
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
        for path in _lap_files_in(directory):
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
            for p in _lap_files_in(directory)
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
    hs: ModuleType, tmp_path: Path
) -> None:
    """The mechanism, isolated from the real tree so it cannot go quiet.

    The tree happens to contain the mix today. If it ever stops, the test above skips
    and this one still pins the ordering rule — that a file declaring no lap is treated
    as the earliest in its round, which is what the pre-header files are.

    **Written against real files on disk rather than bare `Path` names**, and that is
    the round-7-lap-21 correction: the first version handed `_lap_of` two paths that did
    not exist, so the lap it read for `round-07-lap-16.md` came from the *filename*
    fallback that lap 21 removed. The test passed for a reason unrelated to the property
    it claimed — identify the subject the way production does, which is by reading it.
    """
    legacy = tmp_path / "round-7.md"
    legacy.write_text("# a pre-header file, no wire header at all\n", encoding="utf-8")
    canonical = tmp_path / "round-07-lap-16.md"
    canonical.write_text(
        "\n".join(
            ("HANDSHAKE-PROTOCOL: 2", "HANDSHAKE-ROUND: 7", "HANDSHAKE-LAP: 16", "")
        ),
        encoding="utf-8",
    )

    assert hs._lap_of(legacy) == hs.DEFAULT_LAP == 1, (
        "a file with no declared lap must sort as lap 1 — it IS its round's first, and "
        "lap 0 invents a lap that never existed. The fork's rule, adopted in lap 19 "
        "after their lap 18 showed we had picked different numbers for one convention."
    )
    assert hs._lap_of(canonical) == 16
    assert sorted([canonical, legacy], key=hs.sort_key) == [legacy, canonical]
    # And prove the naive key gets it wrong, so the fix is not decoration.
    assert sorted([canonical, legacy], key=lambda p: p.stem) == [canonical, legacy], (
        "the stem sort no longer misorders these, so this regression is no longer "
        "reachable and the ordering rule needs re-justifying"
    )


def test_a_no_lap_file_is_lap_1_even_when_its_NAME_says_otherwise(
    hs: ModuleType, tmp_path: Path
) -> None:
    """**Divergence 1 of round-7 lap 21's diff. §3: "absent means lap 1".**

    Ours read the *name* when the header was silent, and only fell back to
    `DEFAULT_LAP` if the name had no lap either. On every tree either side has ever
    had, those agree — our only no-lap files are named `round-07-lap-01` (where the
    name says 1 and the default *is* 1) or grandfathered `round-N` (where there is no
    lap in the name to read). So the divergence was invisible to every test both
    projects could write, for the whole life of the convention, and the comparison the
    fork asked for in their lap 20 §I1 was the only instrument that could find it.

    Asserted with the name and the rule in *conflict*, which is the only observation
    that separates them.
    """
    misnamed = tmp_path / "round-07-lap-14.md"
    misnamed.write_text(
        "\n".join(("HANDSHAKE-PROTOCOL: 2", "HANDSHAKE-ROUND: 7", "")),
        encoding="utf-8",
    )
    assert hs._lap_of(misnamed) == hs.DEFAULT_LAP == 1, (
        "the filename fallback is back: a file declaring no lap must be lap 1 per §3 "
        "('absent means lap 1... never by filename or mtime'), not lap 14 because that "
        "is what someone typed in the name"
    )
    # Revert-proof in the other direction: the old rule produced a DIFFERENT answer,
    # so this assertion is discriminating rather than decorative.
    assert (hs.name_round_and_lap(misnamed) or (0, 0))[1] == 14, (
        "the name no longer says 14, so the two rules no longer disagree here and this "
        "test has stopped separating them — pick a name that conflicts with the default"
    )


def test_the_ROUND_half_of_the_sort_key_also_reads_the_header_first(
    hs: ModuleType, tmp_path: Path
) -> None:
    """**Divergence 2 of the lap-21 diff, and it was asymmetric inside one sort key.**

    `_lap_of` already read the header; the round half read `round_number()`, which is
    name-only. One key, two different notions of where the fact lives — and §3 had
    already ruled: *"by declared number, never by filename or mtime."*

    The name fallback stays, and must: 27 of the 41 committed correspondence files
    declare no `HANDSHAKE-ROUND` at all, because the v2 wire header begins at round 7
    lap 2. Both halves of that are asserted here, because "header first" and "name when
    there is no header" are separate claims and only the pair is the rule.
    """
    conflicting = tmp_path / "round-07-lap-05.md"
    conflicting.write_text(
        "\n".join(
            ("HANDSHAKE-PROTOCOL: 2", "HANDSHAKE-ROUND: 8", "HANDSHAKE-LAP: 5", "")
        ),
        encoding="utf-8",
    )
    assert hs.sort_key(conflicting)[0] == 8, (
        "the round half of the sort key read the filename; §3 makes the header the fact"
    )
    assert hs.round_number(conflicting) == 7, (
        "round_number() must stay NAME-only — §3 requires the name and the header to "
        "agree, and a check needs each separately in order to say so"
    )

    headerless = tmp_path / "round-6b.md"
    headerless.write_text("# a round-6 amendment, no wire header\n", encoding="utf-8")
    assert hs.sort_key(headerless)[0] == 6, (
        "a pre-v2 file has no declared round, so the name is the only fact in "
        "existence; 'never the filename' has to mean 'never in preference to the "
        "header' or the rule is unimplementable against its own record"
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


def _round_dirs(base: Path) -> tuple[Path, Path, Path]:
    """Make the three directories `round_status` reads, so a state can be constructed."""
    made = tuple((base / d) for d in ("outbound", "inbound", "verified"))
    for directory in made:
        directory.mkdir(parents=True)
    return made[0], made[1], made[2]


def _closing(
    hs: ModuleType, sender: str, round_: int, lap: int, *, pin: str = "abc1234"
) -> str:
    """A file that WOULD close a round, so a test can prove what stops it.

    Takes ``HANDSHAKE-PROTOCOL`` from the module rather than hard-coding ``2``: a
    fixture that keeps declaring the old version once the spec bumps would be refused
    for a reason unrelated to what each test below is asserting.
    """
    fields = {
        "HANDSHAKE-PROTOCOL": str(hs.PROTOCOL_VERSION),
        "HANDSHAKE-ROUND": str(round_),
        "HANDSHAKE-LAP": str(lap),
        "HANDSHAKE-FROM": sender,
        "HANDSHAKE-VERDICT": "GO",
        "HANDSHAKE-APP-VERSION": "platterpus 0.6.4",
        "HANDSHAKE-RIPPER-VERSION": "cyanrip 0.9.4 (platterpus-fork-gabc1234)",
        "HANDSHAKE-PIN": pin,
        "HANDSHAKE-PEER-VERDICT": "GO",
        "HANDSHAKE-OUR-VERSION": "platterpus 0.6.4",
        "HANDSHAKE-OUR-PIN": pin,
        "HANDSHAKE-PEER-VERSION": "cyanrip 0.9.4 (platterpus-fork-gabc1234)",
        "HANDSHAKE-PEER-PIN": pin,
        "HANDSHAKE-TESTED": "one disc on a BDR-209D",
    }
    return "".join(f"{key}: {value}\n" for key, value in fields.items())


def test_a_constructed_two_sided_round_really_does_CLOSE(hs: ModuleType) -> None:
    """The floor under the three tests below. **Assert the gate can say yes.**

    Protocol §8's last row, and the reason it is there: a gate that refuses everything
    passes every refusal test in the table. Without this, the three "and now it is
    refused" tests below could all be satisfied by a fixture that never closes anything.
    """
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        outbound, inbound, verified = _round_dirs(base)
        (outbound / "round-08-lap-01.md").write_text(
            _closing(hs, "platterpus", 8, 1), encoding="utf-8"
        )
        (inbound / "round-08-lap-02.md").write_text(
            _closing(hs, "cyanrip-fork", 8, 2), encoding="utf-8"
        )
        (verified / "round-08-lap-03.md").write_text(
            _closing(hs, "platterpus", 8, 3), encoding="utf-8"
        )
        lines = hs.round_status(root=base)
    assert any(line.endswith("CLOSED") for line in lines), lines
    assert not any(line.endswith("OPEN") for line in lines), lines


def test_a_v2_file_with_NO_declared_lap_is_REFUSED_not_sorted_oldest(
    hs: ModuleType, tmp_path: Path
) -> None:
    """**The state that dropping the filename fallback creates, and its own test.**

    *"What new state does this fix create, and what tests that?"* — §3's "absent means
    lap 1" sorts a lap-less file **oldest**, so a later `GO` would be read as a round's
    newest word while this file's `HOLD` sorted underneath it. Fail-open, and the
    filename fallback happened to cover it.

    The fix is not the fallback, which §3 forbids in the same sentence. It is §2 rule 4
    — an absent required field fails closed — applied at the **gate**, which was reading
    these files without ever asking whether they were coherent.

    Constructed so the hazard is live: the lap-less file declares `HOLD`, a *later*
    valid file declares a complete `GO`, and without the refusal the round would close
    on the `GO` while the `HOLD` sorted first.
    """
    outbound, inbound, verified = _round_dirs(tmp_path)
    (outbound / "round-08-lap-01.md").write_text(
        _closing(hs, "platterpus", 8, 1), encoding="utf-8"
    )
    (inbound / "round-08-lap-02.md").write_text(
        _closing(hs, "cyanrip-fork", 8, 2), encoding="utf-8"
    )
    (verified / "round-08-lap-03.md").write_text(
        _closing(hs, "platterpus", 8, 3), encoding="utf-8"
    )
    lapless = verified / "round-08-lap-04.md"
    lapless.write_text(
        _closing(hs, "platterpus", 8, 3).replace("HANDSHAKE-LAP: 3\n", "")
        + "\nWe are holding: the rig session has not run.\n",
        encoding="utf-8",
    )

    # It really does sort oldest — the hazard is present, not hypothetical.
    ordered = hs._round_files(verified, 8)
    assert ordered[0] == lapless, [p.name for p in ordered]

    problems = hs.ordering_blockers([lapless])
    assert any("HANDSHAKE-LAP" in p for p in problems), problems
    lines = hs.round_status(root=tmp_path)
    assert any(line.endswith("OPEN") for line in lines), lines
    assert any("cannot order" in line and "HANDSHAKE-LAP" in line for line in lines), (
        f"the gate must NAME the file and the rule, not merely refuse: {lines}"
    )


def test_a_PRE_v2_file_with_no_lap_is_grandfathered_rather_than_refused(
    hs: ModuleType, tmp_path: Path
) -> None:
    """The converse, bounded — or the refusal above would refuse the whole record.

    27 of the 41 committed correspondence files declare no lap, because the wire header
    begins at round 7 lap 2. Grandfathering is **derived** from the absence of
    `HANDSHAKE-PROTOCOL` rather than from a list of round numbers, so it cannot go stale
    the way a frozenset does — and a check whose exemption is a list is a check that
    stops applying to the files added after the list was written.
    """
    legacy = tmp_path / "round-6b.md"
    legacy.write_text("# round 6 amendment, pre-header\n", encoding="utf-8")
    assert hs.ordering_blockers([legacy]) == []
    # A floor: the real record must still contain such a file, or this exemption is
    # being tested against a case that no longer exists.
    grandfathered = [
        p
        for d in _DIRS
        for p in (_HANDSHAKE / d).glob("round-*.md")
        if "HANDSHAKE-PROTOCOL" not in p.read_text(encoding="utf-8")
    ]
    assert len(grandfathered) >= 10, (
        f"only {len(grandfathered)} pre-header files remain; if the record has been "
        "back-filled with headers the exemption needs re-justifying"
    )
    assert hs.ordering_blockers(grandfathered) == [], hs.ordering_blockers(
        grandfathered
    )


def test_a_file_declaring_a_round_it_is_not_filed_under_is_REFUSED_by_the_GATE(
    hs: ModuleType, tmp_path: Path
) -> None:
    """§8 row 10, checked where it decides something. **`--check` had it; the gate did not.**

    Making the sort key header-first is what makes this reachable: a file named
    `round-08-lap-…` declaring round 9 is collected into round 8 **by name** and then
    sorts on the strength of a round it does not belong to. Under the old name-only key
    the two could not disagree, so the fix creates the state — and the state gets a test.

    The permissive reading is the wrong one either way: believe the name and a file
    disowns its own declaration; believe the header and a file votes in a round it says
    it is not in. So neither — refuse, and name the file.
    """
    outbound, inbound, verified = _round_dirs(tmp_path)
    (outbound / "round-08-lap-01.md").write_text(
        _closing(hs, "platterpus", 8, 1), encoding="utf-8"
    )
    (inbound / "round-08-lap-02.md").write_text(
        _closing(hs, "cyanrip-fork", 8, 2), encoding="utf-8"
    )
    (verified / "round-08-lap-03.md").write_text(
        _closing(hs, "platterpus", 8, 3), encoding="utf-8"
    )
    crossed = verified / "round-08-lap-09.md"
    crossed.write_text(
        _closing(hs, "platterpus", 8, 9).replace(
            "HANDSHAKE-ROUND: 8\n", "HANDSHAKE-ROUND: 9\n"
        ),
        encoding="utf-8",
    )

    # It sorts LAST within round 8 on the strength of the round it declares, which is
    # what makes it the file the verdict would be read from.
    assert hs._round_files(verified, 8)[-1] == crossed

    problems = hs.ordering_blockers([crossed])
    assert any("HANDSHAKE-ROUND" in p for p in problems), problems
    lines = hs.round_status(root=tmp_path)
    assert any(line.endswith("OPEN") for line in lines), lines
    assert any("cannot order" in line for line in lines), lines


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


# --- concurrent laps: both sides numbered a lap 25 -------------------------------
#
# WHAT HAPPENED (2026-08-05, round 7). We wrote lap 25 answering their lap 24; they
# wrote lap 25 answering our lap 23. Neither had received the other's file, so both
# picked the same number legitimately. The protocol's §2 rule for
# `HANDSHAKE-LAP` says *"a round's state is its latest lap's verdict — by declared
# number"*, which at a tie names two files and settles nothing.
#
# MEASURED, NOT REASONED: the tie is harmless, because `round_status` reads each
# side's verdict from its OWN directory (`verified/` vs `inbound/`), so "the latest
# lap" is only ever resolved within one sender's files. These two tests pin that,
# so it stays a property the suite checks rather than a claim someone read off the
# code once. The spec sentence still wants the clarification — "each side's latest
# lap", not "the round's" — which is a round-8 shared-spec item.


def test_a_same_lap_collision_across_directories_still_CLOSES(hs: ModuleType) -> None:
    """Both sides at lap 25, both GO: the tie must not block a real close."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        outbound, inbound, verified = _round_dirs(base)
        (outbound / "round-08-lap-01.md").write_text(
            _closing(hs, "platterpus", 8, 1), encoding="utf-8"
        )
        # THE COLLISION: both sides' newest file declares lap 25.
        (inbound / "round-08-lap-25.md").write_text(
            _closing(hs, "cyanrip-fork", 8, 25), encoding="utf-8"
        )
        (verified / "round-08-lap-25.md").write_text(
            _closing(hs, "platterpus", 8, 25), encoding="utf-8"
        )
        lines = hs.round_status(root=base)
    assert any(line.endswith("CLOSED") for line in lines), lines


def test_a_same_lap_collision_cannot_hide_the_peers_HOLD(hs: ModuleType) -> None:
    """The direction that matters: their HOLD at the same lap must still block."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        outbound, inbound, verified = _round_dirs(base)
        (outbound / "round-08-lap-01.md").write_text(
            _closing(hs, "platterpus", 8, 1), encoding="utf-8"
        )
        (inbound / "round-08-lap-25.md").write_text(
            _closing(hs, "cyanrip-fork", 8, 25).replace(
                "HANDSHAKE-VERDICT: GO", "HANDSHAKE-VERDICT: HOLD"
            ),
            encoding="utf-8",
        )
        (verified / "round-08-lap-25.md").write_text(
            _closing(hs, "platterpus", 8, 25), encoding="utf-8"
        )
        lines = hs.round_status(root=base)
    assert any(line.endswith("OPEN") for line in lines), lines
    assert not any(line.endswith("CLOSED") for line in lines), (
        "our GO at lap 25 outranked their HOLD at the same lap — a tie resolved in "
        "favour of releasing is the one resolution the gate must never pick"
    )


# --- a duplicate (round, lap, sender) is unorderable, and it FAILED OPEN ------------
#
# WHAT HAPPENED (2026-08-05). The cyanrip fork revised and re-sent lap 25 — protocol §2
# says *"Each lap is a new file. Never edit a file already sent."* Deleting the first
# copy would destroy the record of what was actually sent and quoted, so both are kept.
# That creates two files at the same (round, lap), and `sort_key` is
# `(round, lap, stem)` — so the tie falls through to the FILENAME.
#
# MEASURED: `round-07-lap-25.md` (the revision) sorted BEFORE
# `round-07-lap-25-as-first-sent.md`, so the gate read the SUPERSEDED file as the
# round's newest word. Both declared HOLD, so nothing broke — which is exactly how
# this class of bug survives long enough to matter.
#
# This is the THIRD fail-open ordering hole in `ordering_blockers`'s own subject
# matter; the other two are the blockers it already had.


def test_an_unmarked_duplicate_lap_is_REFUSED(hs: ModuleType, tmp_path: Path) -> None:
    """Two files at one (round, lap, sender) cannot be ordered, so the gate refuses."""
    (tmp_path / "round-08-lap-03.md").write_text(
        _closing(hs, "cyanrip-fork", 8, 3), encoding="utf-8"
    )
    (tmp_path / "round-08-lap-03-revised.md").write_text(
        _closing(hs, "cyanrip-fork", 8, 3), encoding="utf-8"
    )
    problems = hs.ordering_blockers(sorted(tmp_path.glob("*.md")))
    assert problems, "a duplicate round/lap/sender was accepted — the tie resolves by "
    assert any("same round/lap/sender" in p for p in problems), problems


def test_a_marked_archive_is_out_of_the_sequence_not_refused(
    hs: ModuleType, tmp_path: Path
) -> None:
    """The escape hatch: a preserved earlier copy is archival, not part of the laps.

    Without this the record could only be kept by making the round permanently
    unorderable — so preserving evidence would cost the ability to close a round, and
    the incentive would be to delete the evidence.
    """
    (tmp_path / "round-08-lap-03.md").write_text(
        _closing(hs, "cyanrip-fork", 8, 3), encoding="utf-8"
    )
    (tmp_path / f"round-08-lap-03{hs.SUPERSEDED_MARKER}.md").write_text(
        _closing(hs, "cyanrip-fork", 8, 3), encoding="utf-8"
    )
    assert not hs.ordering_blockers(sorted(tmp_path.glob("*.md"))), (
        "a deliberately-archived earlier copy still blocked ordering"
    )


def test_two_files_at_one_lap_from_DIFFERENT_senders_are_fine(
    hs: ModuleType, tmp_path: Path
) -> None:
    """The floor. Concurrent laps across the two projects are legitimate and common —
    round 7 had exactly that — so the duplicate check must key on the SENDER too or it
    refuses normal traffic."""
    (tmp_path / "round-08-lap-03.md").write_text(
        _closing(hs, "cyanrip-fork", 8, 3), encoding="utf-8"
    )
    (tmp_path / "round-08-lap-03-ours.md").write_text(
        _closing(hs, "platterpus", 8, 3), encoding="utf-8"
    )
    assert not hs.ordering_blockers(sorted(tmp_path.glob("*.md"))), (
        "two senders at the same lap were refused; concurrent laps are legitimate"
    )
