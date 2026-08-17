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
import subprocess
import sys
from pathlib import Path

import pytest
from scripts import round_digest as rd

REPO_ROOT: Path = Path(__file__).resolve().parent.parent


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


def test_our_published_round_9_numbers_still_reproduce() -> None:
    """The values sent to cyanrip, re-derived from the committed tree.

    A number in a lap is a claim the other project acts on. This asserts the two
    we have published are still what the tool produces — so a change to the
    enumerator that would have altered a sent figure fails here rather than in
    their `RECONCILE`.
    """
    ours = REPO_ROOT / "docs" / "handshake"
    lap4, count4 = rd.round_digest(
        rd.laps_for_round(
            9,
            ours,
            exclude=("round-09-lap-04.md", "round-09-lap-05.md", "round-09-lap-06.md"),
        )
    )
    assert (lap4, count4) == ("5c1925a9e35d5805", 3), "lap 4's declared digest moved"

    lap6, count6 = rd.round_digest(
        rd.laps_for_round(9, ours, exclude=("round-09-lap-06.md",))
    )
    assert (lap6, count6) == ("39b57574cf3f5296", 5), "lap 6's declared digest moved"
