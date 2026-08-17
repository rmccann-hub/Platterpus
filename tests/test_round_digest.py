"""`HANDSHAKE-ROUND-DIGEST` — protocol v4 §5a, and the ways it can lie.

The digest is the one rule §5a says neither project may override: *a round MUST
NOT close while the digests disagree*. So a tool that produces a **confident wrong
number** is worse here than one that crashes — a manufactured mismatch reads
exactly like a real one, and sends a round into `RECONCILE` with nothing to
exchange.

Every test below is a way the tool could have produced one.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parent.parent


def _load_round_digest() -> ModuleType:
    """Import `scripts/round_digest.py` by path, not by package name.

    `scripts/` is not a package and is not on `sys.path` — a plain
    `from scripts import round_digest` only resolves when the repo root
    happens to be `sys.path[0]`, which is true under `python -m pytest`
    (it prepends the cwd) and false under the bare `pytest` console
    script that CI runs. That difference collected fine locally and
    failed CI on all four Python versions. Every other test that reaches
    into `scripts/` loads by file location for this reason; this one now
    matches them.
    """
    script = REPO_ROOT / "scripts" / "round_digest.py"
    spec = importlib.util.spec_from_file_location("round_digest", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rd: ModuleType = _load_round_digest()


def _lap(round_no: int, lap_no: int, sender: str, body: str = "body\n") -> str:
    return (
        f"HANDSHAKE-PROTOCOL: 4\n"
        f"HANDSHAKE-ROUND: {round_no}\n"
        f"HANDSHAKE-LAP: {lap_no}\n"
        f"HANDSHAKE-FROM: {sender}\n"
        f"HANDSHAKE-VERDICT: HOLD\n\n{body}"
    )


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    for lap_no, sender in ((1, "cyanrip-fork"), (2, "platterpus"), (3, "cyanrip-fork")):
        (tmp_path / f"round-09-lap-{lap_no:02d}.md").write_text(
            _lap(9, lap_no, sender), encoding="utf-8"
        )
    return tmp_path


def test_the_construction_matches_the_spec_step_for_step(tree: Path) -> None:
    """§5a steps 1-5, recomputed here rather than trusting the module.

    Deliberately a second implementation in the test: the module is one witness
    and this is another, and the spec exists so two of them can be compared.
    """
    lines = []
    for lap_no, sender in ((1, "cyanrip-fork"), (2, "platterpus"), (3, "cyanrip-fork")):
        data = (tree / f"round-09-lap-{lap_no:02d}.md").read_bytes()
        lines.append(f"{lap_no}\t{sender}\t{hashlib.sha256(data).hexdigest()}")
    blob = ("\n".join(sorted(lines)) + "\n").encode("utf-8")
    want = hashlib.sha256(blob).hexdigest()[:16]

    got, count = rd.round_digest(rd.laps_for_round(9, tree))
    assert (got, count) == (want, 3)


def test_an_exclusion_that_matches_nothing_refuses(tree: Path) -> None:
    """The defect this file was written for.

    `--exclude` matched on basename and **silently dropped nothing** when the name
    did not match, so passing a path printed a confident digest over the full set —
    including the lap it was told to remove. Found by an adversarial review of a
    diagnosis the tool was being used to produce, not by the tool's own tests,
    which only ever passed names that matched.
    """
    with pytest.raises(rd.UnmatchedExclusion) as caught:
        rd.laps_for_round(9, tree, exclude=("some/path/round-09-lap-02.md",))
    assert "Basenames only" in str(caught.value)

    # A name that DOES match still works, or the fix is a wall rather than a guard.
    assert len(rd.laps_for_round(9, tree, exclude=("round-09-lap-02.md",))) == 2


def test_exclusions_are_plural_because_a_verifier_needs_them_to_be(tree: Path) -> None:
    """Reproducing an older declaration means dropping every lap filed since.

    The single-valued form could not express that, so the natural command for
    re-checking a past number quietly returned a different one — the same class of
    silent-wrong-answer as the no-op above.
    """
    both = rd.laps_for_round(
        9, tree, exclude=("round-09-lap-02.md", "round-09-lap-03.md")
    )
    assert [lap.lap for lap in both] == ["1"]


def test_a_container_is_not_a_lap_however_many_it_carries(tree: Path) -> None:
    """§5a's exactly-once rule, which is what keeps an envelope out of the digest."""
    envelope = tree / "round09envelope.md"
    envelope.write_text(
        _lap(9, 1, "cyanrip-fork") + "\n" + _lap(9, 2, "platterpus"), encoding="utf-8"
    )
    assert not rd.is_a_lap(envelope.read_text(encoding="utf-8"))
    assert len(rd.laps_for_round(9, tree)) == 3, "the envelope entered the digest"


def test_a_quoted_header_inside_a_fence_is_not_a_declaration(tree: Path) -> None:
    """§2 rule 2. A lap documenting the format must not be excluded by its own example."""
    documenting = _lap(9, 4, "platterpus", body="```\nHANDSHAKE-LAP: 99\n```\n")
    (tree / "round-09-lap-04.md").write_text(documenting, encoding="utf-8")
    assert rd.is_a_lap(documenting)
    assert len(rd.laps_for_round(9, tree)) == 4


def test_the_digest_is_keyed_on_lap_and_sender_not_on_the_filename(tree: Path) -> None:
    """Filenames are local layout; the two projects already differ.

    Renaming a lap must not move the digest, or the two sides disagree by
    construction and no exchange of files can fix it.
    """
    before, _ = rd.round_digest(rd.laps_for_round(9, tree))
    (tree / "round-09-lap-02.md").rename(tree / "totally-different-name.md")
    after, count = rd.round_digest(rd.laps_for_round(9, tree))
    assert (after, count) == (before, 3)


def test_an_empty_round_has_a_value_rather_than_an_error(tree: Path) -> None:
    """ "We hold nothing" is a real state, and both sides must compute it alike."""
    digest, count = rd.round_digest(rd.laps_for_round(99, tree))
    assert count == 0 and len(digest) == 16


def test_the_cli_refuses_an_unmatched_exclusion_rather_than_printing(
    tmp_path: Path,
) -> None:
    """End to end: the exit status, because a caller in a script reads that."""
    script = REPO_ROOT / "scripts" / "round_digest.py"
    bad = subprocess.run(
        [sys.executable, str(script), "9", "--exclude", "docs/handshake/nope.md"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert bad.returncode == 2, bad.stdout
    assert "HANDSHAKE-ROUND-DIGEST" not in bad.stdout, "it printed a digest anyway"

    good = subprocess.run(
        [sys.executable, str(script), "9", "--exclude", "round-09-lap-06.md"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert good.returncode == 0 and "HANDSHAKE-ROUND-DIGEST" in good.stdout


def _as_declared_in(lap: tuple[int, int]) -> tuple[str, int]:
    """Reproduce the digest our ``(round, lap)`` declared, from the tree as it is now.

    §5a's writer rule is *"every lap of this round the writer holds, excluding this
    one"* — so reproducing a **past** declaration means excluding that lap **and
    every lap filed since**, because those did not exist when the number was
    computed.

    **Derived from the tree, never listed.** The first version of this test carried a
    hand-written exclusion tuple, and filing lap 8 did not break it loudly — it made
    it reproduce a *different number* for lap 4 and fail on the comparison. That is
    the lucky outcome. Had lap 4's assertion not been pinned, a stale exclusion list
    would have silently validated the wrong figure, which is exactly the
    manufactured-mismatch failure this whole module exists to prevent — one level up,
    in the test rather than the tool.
    """
    root = REPO_ROOT / "docs" / "handshake"
    round_no, lap_no = lap
    stem = f"round-{round_no:02d}-lap-"
    later = tuple(
        path.name
        for directory in ("inbound", "outbound", "verified")
        for path in (root / directory).glob(f"{stem}*.md")
        if (m := re.fullmatch(rf"{re.escape(stem)}(\d+)\.md", path.name))
        and int(m.group(1)) >= lap_no
    )
    assert later, f"no lap at or after {lap} — the exclusion would be a no-op"
    return rd.round_digest(rd.laps_for_round(round_no, root, exclude=later))


def test_our_published_digests_still_reproduce() -> None:
    """Every value we have sent cyanrip, re-derived from the committed tree.

    A number in a lap is a claim the other project acts on and cannot re-derive
    without our tree. This asserts each one is still what the tool produces — so a
    change to the enumerator that would have altered a *sent* figure fails here
    rather than in their `RECONCILE`.

    **Keyed by ``(round, lap)``, and swept across every round.** It was round 9 only
    until 2026-08-17, and the floor below carried the giveaway: its comment promised
    *"every lap of ours in the tree"* while its glob said `round-09-lap-*`. That was
    the same statement when it was written, and stopped being so the moment round 10
    opened — so rounds 10 and 11 each declared digests to the fork that **nothing
    pinned**, silently, which is exactly the invisible-by-omission decay `CLAUDE.md`
    describes and `docs/testing.md` §5.af names. A promise of completeness needs a
    sweep, not a comment.
    """
    published = {
        # --- Round 9 ---
        # Lap 2 is where the writer-exclusion rule was first *proposed* (its §A1-b),
        # and it already computed the number that way — so it reproduces under the
        # same rule as the laps that came after the amendment was adopted.
        (9, 2): ("05c6e505af0dd617", 1),
        (9, 4): ("5c1925a9e35d5805", 3),
        (9, 6): ("39b57574cf3f5296", 5),
        # Lap 8's value moved 1d48ae7d79f5deb5/6 -> a010a87d075d4834/7 when the
        # fork's lap 7 was filed and lap 8 was rewritten to answer it. **That is
        # not an edit to a sent number**: the earlier value lived only in a draft
        # that never left, per the corrected SEND_BOUNDARY. A number this map may
        # never change is one the peer holds -- and the peer holds none of these.
        (9, 8): ("a010a87d075d4834", 7),
        (9, 10): ("598f28c6ed351675", 9),
        # --- Round 10 ---
        (10, 2): ("8ebd52790dedf658", 1),
        (10, 4): ("049fa6ecccaa5328", 3),
        # --- Round 11 ---
        (11, 2): ("32e19aec2253f1dd", 1),
        # Lap 4 closes the round. Its figure covers laps 1-3, which is why the
        # count is 3 and not 1: by lap 4 we hold their lap 1, our lap 2 and their
        # lap 3. Added because the sweep below caught it missing on the very first
        # lap filed after the sweep existed — which is the floor doing its job.
        (11, 4): ("663c687da69fb8e2", 3),
    }
    for lap, expected in published.items():
        assert _as_declared_in(lap) == expected, (
            f"round {lap[0]} lap {lap[1]}'s declared digest moved: it published "
            f"{expected} and the tree now yields {_as_declared_in(lap)}. A sent "
            "number is frozen — find what changed in the enumerator or the laps, do "
            "not edit this map."
        )

    # The floor, derived from the filesystem across EVERY round rather than one.
    # Without it a future lap's published figure goes unpinned and the check quietly
    # stops covering the newest claim — the one most likely to be acted on.
    ours = {
        (int(m.group(1)), int(m.group(2)))
        for path in (REPO_ROOT / "docs" / "handshake" / "verified").glob(
            "round-*-lap-*.md"
        )
        if (m := re.fullmatch(r"round-(\d+)-lap-(\d+)\.md", path.name))
    }
    # Rounds 9 and later only: the digest field postdates the earlier rounds, whose
    # laps declare no number for this to pin. Stated as a boundary rather than left
    # to the map's contents, so "not pinned" and "never declared one" stay distinct.
    declared = {lap for lap in ours if lap[0] >= 9}
    unpinned = sorted(declared - set(published))
    assert not unpinned, (
        f"these laps of ours declare a round digest that nothing pins: {unpinned}. "
        "Add each one's declared value — an unpinned figure is one the fork can act "
        "on and we cannot prove we still reproduce."
    )
