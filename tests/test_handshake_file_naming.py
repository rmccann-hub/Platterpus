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

import fnmatch
import importlib.util
import re
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import pytest

from platterpus.uiscript.find_script import normalise

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


def _load(script_name: str, as_: str) -> ModuleType:
    """Load a `scripts/` module by path. Loaded, never re-implemented here."""
    script = _REPO / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(as_, script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def hs() -> ModuleType:
    """The module that OWNS the lap-file convention."""
    return _load("handshake.py", "handshake_naming_test")


@pytest.fixture(scope="module")
def envelope() -> ModuleType:
    """The module that OWNS the transport-envelope name."""
    return _load("emit_envelope.py", "emit_envelope_naming_test")


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
_NOT_LAPS: frozenset[str] = (
    frozenset()
)  # the envelope is excluded structurally, by _is_one_lap


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
    # A RUNNABLE TOOL CARRIES NO BUILD FIELD, and that is not a loosening.
    #
    # The `-g<build>` field exists because an artifact's filename must assert a
    # provenance **the artifact's own content supports** — a golden reference log
    # names the build in its banner, and `test_handshake_artifact_naming.py`
    # checks the two agree. A shell script the operator executes describes no
    # build: it is an instrument, not evidence about a binary. Naming one
    # `-g29d59b2` made the filename assert something nothing in the file backs,
    # which is precisely the defect the build field was added to prevent — the
    # sibling test caught it, correctly, the moment it was tried.
    #
    # The fork treats executables as their own category too: `rig-c1-probe.sh`
    # travelled OUTSIDE their lap-11 envelope, on the stated ground that the one
    # exception to the one-file transport rule is a file meant to be run.
    #
    # Scoped to `.sh`, so it cannot spread to a log or a contract; and such a file
    # still carries round, lap and kind, so it is placeable in the record.
    tool = re.compile(r"^round-\d{2,4}-lap-\d{2,4}-[a-z0-9-]+$")
    for path in artifacts:
        if path.suffix == ".sh":
            assert tool.match(path.stem), (
                f"{path.name} is a received tool, so it must be named "
                "round-NN-lap-LL-<kind>.sh with NO build field — a script asserts "
                "no build and a filename must not claim what the file cannot back"
            )
            continue
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
        # Long enough to clear the evidence floor. It read 'one disc on a BDR-209D' — 22 characters
        # naming nothing in particular — and the close/status tests leaned on that
        # passing. `evidence_blockers` (2026-08-18) refuses content-free evidence, so
        # this went red: the gate was correct and the STAND-IN WAS MORE PERMISSIVE THAN
        # THE PRODUCT. CLAUDE.md, "what does my stand-in do that the real thing does
        # not?" — the answer here was "accept a close with no evidence".
        "HANDSHAKE-TESTED": (
            "one disc on a BDR-209D — the full suite green under CI's import path, with "
            "PYTEST_EXIT read from pytest's own status. NOT tested: any drive."
        ),
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


# --- the transport envelope's name -------------------------------------------------
#
# THE SECOND NAME IN THIS TREE, and it is deliberately unlike the first. The envelope
# is one file wrapping several laps verbatim, so the operator sends one attachment
# instead of nine; it crosses two repositories by hand, through a chat client and a
# file manager.
#
# WHY IT NEEDS ITS OWN CHECKS. There WAS one — `test_handshake_bundle.py` pinned
# exactly this property — and it was deleted along with the envelope on 2026-08-15,
# then never restored when `emit_envelope.py` re-created the envelope hours later
# under protocol v4 §5a. For two commits the only statement of the rule was a comment
# in the generator saying the name satisfied it. *A comment where a check belongs is
# not a fix* (CLAUDE.md), and the proof is that the literal then drifted three times in
# one session — `round08platterpusbundle` → `round09platterpusenvelope` →
# `round09lap06platterpus` — with no gate noticing. The operator asked whether the name
# deviated from the convention, which is the question a test should have been answering.


def test_the_envelope_name_cannot_be_read_as_a_lap_by_either_gate(
    hs: ModuleType, envelope: ModuleType
) -> None:
    """**RESTORED GUARD.** The envelope carries wire headers, so its NAME must not
    be resolvable as a lap by anything on either side.

    Both projects' gates glob `round-*.md`. A matching name on a file that declares
    a round and a lap per part would be collected into the round and could sort as
    its newest — displacing the real latest lap and deciding a verdict read.

    Three assertions, because each covers a different reader: the shared glob, our
    own name parser, and the case-insensitive filesystem an operator may be on.
    """
    name = envelope.OUT.name
    assert not fnmatch.fnmatch(name, "round-*.md"), (
        f"{name} matches round-*.md, the glob both gates use to collect laps"
    )
    assert not fnmatch.fnmatch(name.lower(), "round-*.md"), (
        f"{name} matches round-*.md once case is folded — a case-insensitive "
        "filesystem would collect it even though a case-sensitive one would not"
    )
    assert hs.name_round_and_lap(envelope.OUT) is None, (
        f"{name} parses as a canonical lap name, so `--status` would read a verdict "
        "off a container"
    )
    assert hs.round_number(envelope.OUT) is None, (
        f"{name} parses as belonging to a round, so the status report would place a "
        "container among that round's laps"
    )

    # NON-TRIVIALITY. Every assertion above can be satisfied by a name that is
    # simply unlike anything — so prove the checks discriminate by running them on
    # the name the envelope must NOT have.
    forbidden = Path(hs.handshake_filename(*envelope.lead_identity()))
    assert fnmatch.fnmatch(forbidden.name, "round-*.md")
    assert hs.name_round_and_lap(forbidden) is not None
    assert hs.round_number(forbidden) is not None


def test_the_envelope_name_is_safe_to_cross_machines(envelope: ModuleType) -> None:
    """CLAUDE.md → *Artifact filenames that cross machines*, checked on the real name.

    > Lowercase ASCII letters and digits only. No hyphens, no underscores, no spaces,
    > no case. Numbers zero-padded.

    Asserted against `find_script.normalise` — the function `--run-script` uses to
    resolve an operator-typed path — rather than a second regex here. A name is
    already in the canonical spelling exactly when normalising it is a no-op, so the
    rule and the resolver cannot drift apart into two different ideas of "safe".

    This is the rule a lost rig run paid for: the same artifact was `round08joint.txt`
    on the operator's disk and `round-08-joint.txt` in the instructions written for
    them, and a path is an exact-match string.
    """
    name = envelope.OUT.name
    stem, dot, suffix = name.partition(".")
    assert dot and suffix == "md", f"{name} must be a single-suffix .md file"
    assert normalise(stem) == stem, (
        f"{name} is not in the cross-machine spelling: `{stem}` normalises to "
        f"`{normalise(stem)}`. Lowercase ASCII letters and digits only — no hyphens, "
        "underscores, spaces or capitals (CLAUDE.md → Artifact filenames that cross "
        "machines)."
    )
    assert re.fullmatch(r"round\d{2}lap\d{2}platterpus", stem), (
        f"{name} does not follow round<NN>lap<LL>platterpus.md. The numbers are "
        "zero-padded so a directory listing sorts chronologically, and the sender is "
        "named so the operator can tell our envelope from theirs at a glance."
    )


def test_the_envelope_name_is_generated_from_the_lap_it_carries(
    envelope: ModuleType,
) -> None:
    """**The anti-drift property, and the reason this is a template not a literal.**

    A hand-typed name is a second description of a fact the lead part's header already
    declares. `handshake_filename` exists for exactly that reason on the lap side; the
    envelope had no equivalent, and three sends produced three unrelated names.

    Both directions are asserted: the name matches the header, and the generator
    actually varies with its inputs — a `envelope_filename` that ignored its arguments
    would satisfy the first assertion on a tree of one envelope.
    """
    round_, lap = envelope.lead_identity()
    assert envelope.OUT.name == envelope.envelope_filename(round_, lap), (
        f"{envelope.OUT.name} does not state round {round_} lap {lap}, which is what "
        f"{envelope.PARTS[0].name} declares. Regenerate rather than rename."
    )
    assert envelope.envelope_filename(9, 6) == "round09lap06platterpus.md"
    assert envelope.envelope_filename(10, 21) == "round10lap21platterpus.md"
    assert envelope.envelope_filename(9, 6) != envelope.envelope_filename(9, 7), (
        "the generator does not vary with the lap, so the name cannot track the "
        "contents and the check above proves nothing"
    )


def test_the_naming_sweep_reaches_the_real_envelope_and_excludes_it(
    envelope: ModuleType,
) -> None:
    """The *content* half, asserted on the file that actually exists.

    The name checks above stop a gate resolving it as a lap; this stops the sweep in
    THIS module judging it as one. `_NOT_LAPS` is empty by design, so the exclusion is
    structural (v4 §5a — a field declared more than once is ambiguous, so the file is
    not one lap). Structural exclusions are the kind that quietly stop applying, so
    the real file is the subject here rather than a fixture.
    """
    out = envelope.OUT
    assert out.is_file(), (
        f"{out.name} is not in the tree — regenerate with "
        "`python scripts/emit_envelope.py` or this test is checking nothing"
    )
    assert out.parent == _HANDSHAKE / "outbound", out.parent
    raw = list((_HANDSHAKE / "outbound").glob("*.md"))
    assert out in raw, (
        f"{out.name} is not reached by the sweep's own glob, so its exclusion below "
        "would pass for the wrong reason"
    )
    assert not _is_one_lap(out), (
        f"{out.name} declares each wire field at most once, so every content-based "
        "sweep on both sides reads it as a lap. `emit_envelope.assert_not_a_lap` is "
        "supposed to make that impossible before the file is written."
    )
    assert out not in _lap_files_in("outbound")


def test_a_ONE_PART_envelope_is_still_not_a_lap(envelope: ModuleType) -> None:
    """The case the structural rule does NOT cover for free, exercised directly.

    An envelope carrying N parts declares each field N times, so v4 §5a excludes it —
    for N ≥ 2. At **N = 1** the count is one and the envelope is indistinguishable
    from the lap inside it. The preamble's own `not-a-lap` declarations are what keep
    the count at two; without them a single-lap send would be filed as a duplicate of
    the lap it wraps, in both trees.

    Nothing in the suite touched `emit_envelope.py` before this — the guard was
    written, documented, and never run by a test.
    """
    parts = envelope.read_parts()[:1]
    text = envelope._FENCE_RE.sub("", envelope.render(parts))
    for field in envelope._LAP_FIELDS:
        assert len(re.findall(rf"^{field}:", text, re.MULTILINE)) == 2, (
            f"a one-part envelope declares {field} an ambiguous number of times; it "
            "must be exactly two (the preamble's, and the lap's)"
        )
    envelope.assert_not_a_lap(text)  # and the guard agrees


def test_the_not_a_lap_guard_actually_fires(envelope: ModuleType) -> None:
    """Revert-proof. Remove what makes a one-part envelope safe; the guard must refuse.

    Without this, the test above passes and `assert_not_a_lap` could be a no-op — the
    *"can this check be satisfied by finding nothing?"* question asked of the one
    check standing between a container and both projects' lap enumerators.
    """
    text = envelope.render(envelope.read_parts()[:1])
    for field in envelope._LAP_FIELDS:
        text = text.replace(f"{field}: not-a-lap (transport envelope)\n", "")
    with pytest.raises(SystemExit, match="exactly once"):
        envelope.assert_not_a_lap(text)


def test_the_envelope_splits_back_into_byte_identical_parts(
    envelope: ModuleType,
) -> None:
    """The envelope's whole promise: the receiver gets the originals, provably.

    A merged round file would be a falsified record. This is a wrapper, so the
    inverse must be exact — asserted on the file as published, with the published
    reader, over every part.
    """
    published = envelope.OUT.read_text(encoding="utf-8")
    recovered = envelope.split(published)
    assert len(recovered) == len(envelope.PARTS), (
        f"{envelope.OUT.name} splits into {sorted(recovered)}, but was packed from "
        f"{[p.name for p in envelope.PARTS]}"
    )
    for part in envelope.PARTS:
        assert recovered[part.name] == part.read_bytes(), (
            f"{part.name} does not survive the round trip byte-for-byte"
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


# --- a round the PEER opened must be able to close ---------------------------------
#
# WHAT HAPPENED (2026-08-17). `round_status` required an OUTBOUND file to close a
# round: `state = "CLOSED" if (sent and back and both_go)`. Protocol v4 §1a -- adopted
# in round 9 -- says the PROVIDER opens, "because only the provider can mint the unit
# of work". When cyanrip opens, every lap of ours is a verification and lives in
# `verified/`; `outbound/` stays empty for the whole round.
#
# So round 9 reported OPEN with BOTH SIDES DECLARING GO, and would have done so
# forever -- blocking every release, because the deviation policy forbids releasing
# while a round is open. Invisible for eight rounds because we opened all eight.
#
# The mirror of the fork's own round-9 lap-7 §C: a gate reading the wrong directory.
# Theirs failed OPEN and permitted a release it should have refused; ours failed
# CLOSED. Fail-closed is the right direction to be wrong in and is still wrong.


def _peer_opened_round(hs: ModuleType, base: Path, *, their_newest: str) -> list[str]:
    """A round with NO outbound file: they opened it, we only ever verified.

    Returns `round_status` lines. `their_newest` is the verdict on the newest inbound
    lap, so one helper covers both the close and the refusal.
    """
    outbound, inbound, verified = _round_dirs(base)
    # NOTHING in outbound/ -- that is the whole point.
    (inbound / "round-09-lap-09.md").write_text(
        _closing(hs, "cyanrip-fork", 9, 9).replace(
            "HANDSHAKE-VERDICT: GO", f"HANDSHAKE-VERDICT: {their_newest}"
        ),
        encoding="utf-8",
    )
    (verified / "round-09-lap-10.md").write_text(
        _closing(hs, "platterpus", 9, 10), encoding="utf-8"
    )
    assert not list(outbound.glob("*.md")), "the fixture must have no outbound file"
    return hs.round_status(root=base)


def test_a_peer_opened_round_can_CLOSE_without_an_outbound_file(
    hs: ModuleType, tmp_path: Path
) -> None:
    """The regression. Both sides GO, no outbound file, round 9 must CLOSE."""
    lines = _peer_opened_round(hs, tmp_path, their_newest="GO")
    assert any(line.endswith("CLOSED") for line in lines), lines
    assert not any(line.endswith("OPEN") for line in lines), lines

    # REVERT-PROOF. Re-impose the old requirement and the same tree must go OPEN, or
    # this test passes for a reason unrelated to the fix.
    verified = tmp_path / "verified"
    inbound = tmp_path / "inbound"
    sent = list((tmp_path / "outbound").glob("*.md"))
    done = list(verified.glob("*.md"))
    back = list(inbound.glob("*.md"))
    assert done and back and not sent, (sent, done, back)
    assert not (sent and back and done), (
        "the old condition `sent and back and both_go` is no longer unsatisfiable on "
        "this fixture, so the regression is unreachable and the fix needs "
        "re-justifying"
    )


def test_a_peer_opened_round_still_refuses_when_their_NEWEST_lap_is_not_GO(
    hs: ModuleType, tmp_path: Path
) -> None:
    """The floor, and the direction that matters.

    Dropping the outbound requirement must not make a peer-opened round close on our
    verdict alone — that would trade a gate that refuses everything for one that
    refuses nothing, which is how the fork's own §C defect behaved.
    """
    lines = _peer_opened_round(hs, tmp_path, their_newest="HOLD")
    assert any(line.endswith("OPEN") for line in lines), lines
    assert not any(line.endswith("CLOSED") for line in lines), (
        "a peer-opened round closed while their newest lap declared HOLD"
    )


def test_a_round_with_NO_lap_of_ours_anywhere_stays_open(
    hs: ModuleType, tmp_path: Path
) -> None:
    """The real floor: holding only THEIR file never closes a round.

    **This test previously asserted the opposite of the truth, and that is worth
    keeping.** Written from our own wrong diagnosis, it put a lap of ours in
    `outbound/` with an empty `verified/` and asserted the round stays OPEN — which
    encoded the symmetric coupling as *desired behaviour*. The fork's round-9 lap 11
    §B corrected the diagnosis, and correcting it turned this test red, which is how
    we learned a wrong explanation had already been written into a guard.

    **A test derived from a wrong diagnosis locks the defect in.** The floor that
    actually matters is this one: with nothing of ours at all, no verdict of ours
    exists, and the round cannot close however emphatic theirs is.
    """
    _outbound, inbound, _verified = _round_dirs(tmp_path)
    (inbound / "round-09-lap-09.md").write_text(
        _closing(hs, "cyanrip-fork", 9, 9), encoding="utf-8"
    )
    lines = hs.round_status(root=tmp_path)
    assert any(line.endswith("OPEN") for line in lines), lines
    assert not any(line.endswith("CLOSED") for line in lines), (
        "a round closed with no lap of ours in either directory"
    )


def test_our_verdict_is_read_from_our_newest_lap_in_EITHER_directory(
    hs: ModuleType, tmp_path: Path
) -> None:
    """**The symmetric hole, found by the fork correcting our diagnosis.**

    Our first fix dropped the `outbound/` requirement from the close condition but
    still read the verdict from `verified/` only. The fork's round-9 lap 11 §B showed
    the trigger was never *who opened the round* — they opened round 8 as well as
    round 9, declared in all nine of their round-8 laps — but **where our reply gets
    filed**, which changed between the two rounds.

    That makes the mirror case reachable: a round whose newest lap of ours sits in
    `outbound/` would read its verdict from an older `verified/` file, or from none,
    and could never close. Constructed here with the newest lap of ours in
    `outbound/` and an OLDER, superseded one in `verified/`, so reading the wrong
    directory yields the wrong verdict rather than merely no verdict.
    """
    outbound, inbound, verified = _round_dirs(tmp_path)
    # Superseded: an earlier HOLD of ours, in verified/.
    (verified / "round-12-lap-02.md").write_text(
        _closing(hs, "platterpus", 12, 2).replace(
            "HANDSHAKE-VERDICT: GO", "HANDSHAKE-VERDICT: HOLD"
        ),
        encoding="utf-8",
    )
    # Our NEWEST lap, filed in outbound/ — the case the first fix missed.
    (outbound / "round-12-lap-04.md").write_text(
        _closing(hs, "platterpus", 12, 4), encoding="utf-8"
    )
    (inbound / "round-12-lap-03.md").write_text(
        _closing(hs, "cyanrip-fork", 12, 3), encoding="utf-8"
    )

    lines = hs.round_status(root=tmp_path)
    assert any(line.endswith("CLOSED") for line in lines), lines

    # REVERT-PROOF, and it must discriminate: reading `verified/` only would find our
    # lap 2's HOLD and report OPEN. Assert that is really what the old rule yields.
    stale = hs.wire_verdict(
        (verified / "round-12-lap-02.md").read_text(encoding="utf-8")
    )
    fresh = hs.wire_verdict(
        (outbound / "round-12-lap-04.md").read_text(encoding="utf-8")
    )
    assert (stale, fresh) == ("HOLD", "GO"), (
        "the fixture no longer puts a superseded HOLD in verified/ and a newer GO in "
        "outbound/, so this test cannot separate the two readings"
    )


def test_a_superseded_verdict_of_OURS_in_the_other_directory_cannot_close_a_round(
    hs: ModuleType, tmp_path: Path
) -> None:
    """The floor on the fix above: newest wins, in the refusing direction too.

    Spanning both directories must not become "any GO of ours anywhere closes it".
    Newest lap of ours is a HOLD in `verified/`; an older GO sits in `outbound/`.
    """
    outbound, inbound, verified = _round_dirs(tmp_path)
    (outbound / "round-12-lap-02.md").write_text(
        _closing(hs, "platterpus", 12, 2), encoding="utf-8"
    )
    (inbound / "round-12-lap-03.md").write_text(
        _closing(hs, "cyanrip-fork", 12, 3), encoding="utf-8"
    )
    (verified / "round-12-lap-04.md").write_text(
        _closing(hs, "platterpus", 12, 4).replace(
            "HANDSHAKE-VERDICT: GO", "HANDSHAKE-VERDICT: HOLD"
        ),
        encoding="utf-8",
    )
    lines = hs.round_status(root=tmp_path)
    assert any(line.endswith("OPEN") for line in lines), lines
    assert not any(line.endswith("CLOSED") for line in lines), (
        "an older GO of ours in outbound/ closed a round our newest lap HOLDs"
    )


# --- Unpacking a RECEIVED envelope -----------------------------------------
#
# The inbound direction, added 2026-08-21. `split()` had existed for rounds and
# was reachable from no CLI, so every actual split was done by hand-writing the
# regex again — three times in one session. Worse, `split()` parses each part's
# declared `sha256=` and then ignores it, so the integrity claim the delimiter
# carries was checked by nothing. Same shape as CLAUDE.md rule #9's
# fully-implemented `cancel()` called from nowhere: the capability existed and
# could not be used, and the part that made it trustworthy was absent.


def _envelope_of(envelope: ModuleType, parts: dict[str, str]) -> str:
    """Build a well-formed envelope carrying `parts`, using the real delimiters."""
    import hashlib

    chunks = []
    for name, body in parts.items():
        sha = hashlib.sha256((body + "\n").encode("utf-8")).hexdigest()
        chunks.append(
            envelope.BEGIN.format(name=name, sha=sha)
            + "\n"
            + body
            + "\n"
            + envelope.END.format(name=name)
        )
    return "preamble prose\n\n" + "\n\n".join(chunks) + "\n"


def test_verify_split_reports_both_hashes_so_a_mismatch_can_be_named(
    envelope: ModuleType,
) -> None:
    """A corrupted transfer must be describable, not just refusable.

    Returning declared AND computed is deliberate: a splitter that says only
    "failed" leaves two projects unable to tell a truncation from a re-encoding,
    which need different follow-ups. This is the diagnostic-completeness rule at
    the size of one function.
    """
    good = _envelope_of(envelope, {"a.md": "hello", "b.log": "line one\nline two"})
    rows = envelope.verify_split(good)
    assert len(rows) == 2, rows
    for name, body, declared, computed in rows:
        assert declared == computed, f"{name}: {declared} != {computed}"
        assert body.endswith(b"\n"), f"{name}: the trailing newline was dropped"

    # Corrupt ONE part's body, leaving its declared hash in place.
    tampered = good.replace("line one", "line ONE")
    rows = envelope.verify_split(tampered)
    bad = [(n, d, c) for n, _b, d, c in rows if d != c]
    assert len(bad) == 1, f"expected exactly one mismatch, got {bad}"
    assert bad[0][0] == "b.log", bad
    assert bad[0][1] != bad[0][2], "the two hashes are equal, so nothing was detected"


def test_split_round_trips_the_envelope_we_ourselves_produce(
    envelope: ModuleType,
) -> None:
    """Our reader must invert our writer — asserted against real repo files.

    `CLAUDE.md`: two implementations agreeing is not either being correct, so this
    checks the split against the **source artifacts on disk** rather than against
    another parse of the same text.

    **The source path comes from `PARTS`, not from a rebuilt one.** This test used
    to read every part from `HANDSHAKE_DIR / "verified"`, which was true only while
    `PARTS` happened to hold two verification files — a fact about one send, baked
    into the checker as if it were a rule. The first envelope carrying an outbound
    lap and a rig script broke it with `FileNotFoundError`, which is the polite
    version: had a same-named file existed under `verified/`, this would have
    compared the round trip against **the wrong document** and passed. Re-deriving
    a location the module already knows is the defect, not the directory it
    guessed.
    """
    parts = envelope.read_parts()
    assert len(parts) >= 2, f"only {len(parts)} parts to round-trip"
    assert len(envelope.PARTS) == len(parts), "PARTS and read_parts() disagree"
    rendered = envelope.render(parts)
    rows = {name: body for name, body, _d, _c in envelope.verify_split(rendered)}
    assert len(rows) == len(parts), f"{len(parts)} packed, {len(rows)} recovered"
    for source_path, part in zip(envelope.PARTS, parts, strict=True):
        assert source_path.name == part.name, (source_path.name, part.name)
        assert rows[part.name] == source_path.read_bytes(), (
            f"{part.name} did not survive the round trip byte-identically"
        )


def test_a_file_with_no_delimiters_is_refused_rather_than_read_as_empty(
    envelope: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Zero parts is a REFUSAL, not a successful split of nothing.

    The "can this check be satisfied by finding nothing?" question, asked of the
    splitter: an envelope a chat client reflowed produces no matches, and reading
    that as "unpacked 0 files, done" is exactly how a lost lap looks healthy.
    """
    plain = tmp_path / "notanenvelope.md"
    plain.write_text("just some prose, no delimiters at all\n", encoding="utf-8")
    out = tmp_path / "out"
    assert envelope._do_split(plain, out) == 1
    assert not out.exists(), "a refused split created its output directory anyway"
    assert "no envelope parts found" in capsys.readouterr().err


def test_a_mismatching_part_writes_NOTHING(
    envelope: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """All-or-nothing, because the next step reads whatever is on disk.

    A half-written split leaves a directory where some files are trustworthy and
    some are not, with no way to tell them apart afterwards — worse than no split
    at all.
    """
    good = _envelope_of(envelope, {"a.md": "intact", "b.log": "will be corrupted"})
    tampered = good.replace("will be corrupted", "corrupted!!!!!!!!")
    src = tmp_path / "envelope.md"
    src.write_text(tampered, encoding="utf-8")
    out = tmp_path / "out"

    assert envelope._do_split(src, out) == 1
    assert not (out / "a.md").exists(), (
        "the INTACT part was written despite a sibling failing — a later reader "
        "cannot tell which files in that directory are trustworthy"
    )
    err = capsys.readouterr().err
    assert "1 of 2 parts" in err, err
    assert "NOTHING was written" in err, err


def test_a_part_name_cannot_escape_the_output_directory(
    envelope: ModuleType, tmp_path: Path
) -> None:
    """An envelope is EXTERNAL INPUT from another repository (Critical rule #12).

    A part named `../../etc/passwd` must land as `passwd` inside the target, not
    two levels up. Nothing crosses that seam unchecked — and a path is the one
    field where "we trust them" has consequences beyond a wrong verdict.
    """
    good = _envelope_of(envelope, {"../../escaped.md": "gotcha"})
    src = tmp_path / "envelope.md"
    src.write_text(good, encoding="utf-8")
    out = tmp_path / "nested" / "out"

    assert envelope._do_split(src, out) == 0
    assert (out / "escaped.md").is_file(), "the part was not written at all"
    assert not (tmp_path / "escaped.md").exists(), (
        "a part name traversed out of the output directory"
    )


def test_split_needs_no_outbound_lap_staged(
    envelope: ModuleType, tmp_path: Path
) -> None:
    """Unpacking what they sent must work when we have nothing staged to send.

    `main()` used to build our own envelope before parsing arguments, so the
    inbound path would have depended on `PARTS` resolving — which is unrelated
    state, and exactly the coupling that makes a tool unusable at the moment it
    is needed.
    """
    good = _envelope_of(envelope, {"theirs.md": "their lap"})
    src = tmp_path / "envelope.md"
    src.write_text(good, encoding="utf-8")
    out = tmp_path / "out"

    original = envelope.PARTS
    try:
        envelope.PARTS = ()  # nothing of ours staged
        assert envelope.main(["--split", str(src), "--into", str(out)]) == 0
    finally:
        envelope.PARTS = original
    assert (out / "theirs.md").read_text(encoding="utf-8") == "their lap\n"
