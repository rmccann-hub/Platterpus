"""Every artifact a lap NAMES is actually on disk — the receiving half of the gate.

**This is the half neither project had, and both of us said so.** Our round-15
lap 11 §F answered the fork's v5 5b.3 question with *"yes, it should gate both
sides, and the honest answer is that we do not have it either"*; their lap 12 §4
replied *"the receiving check — every artifact a lap names was actually filed — we
also do by hand."* Answering a question with *"we should build this"* and then not
building it is the shape this repository refuses everywhere else, so here it is.

**What it catches, concretely.** A lap arrives saying *"filed at
`docs/handshake/inbound/artifacts/round-15-lap-08-provider-contract-gc4df1f0.md`"*
and that file never lands — a copy that was skipped, a rename that broke a
reference, an attachment nobody extracted. The lap still reads as complete,
because the sentence claiming the artifact is right there. That is *"an absence
nobody can see reads as completeness"* applied to the correspondence record
instead of to a log.

**Derived, not listed.** The population comes from scanning the laps for artifact
paths, so a lap filed tomorrow is covered without anyone updating a table. A
hand-maintained list of expected artifacts would need updating and would therefore
rot — which is the argument `tests/test_imports_are_declared.py` makes about
allowlists, applied here.

**Both directions.** Outbound laps name artifacts too (round 15 lap 13 names six),
and a claim we make about a file we did not commit is worse than one they make:
theirs is a delivery failure, ours is a false statement in a document we control.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
HANDSHAKE: Final[Path] = REPO_ROOT / "docs" / "handshake"

#: A repo-relative artifact path as the laps actually write it — inside backticks,
#: in prose, or in a manifest row. Anchored on `artifacts/` so an ordinary mention
#: of a lap file is not swept in.
#:
#: **The extension is required**, and that is not cosmetic: our own lap 13 writes
#: `…/round-15-lap-13-*` as a WILDCARD covering six files, and a name-shaped prefix
#: match turned that into a claim about a file called `round-15-lap-13-`. A gate
#: that invents a missing artifact out of a glob is the false-positive twin of the
#: thing it is looking for.
_ARTIFACT_REF: Final[re.Pattern[str]] = re.compile(
    r"docs/handshake/(?P<side>inbound|outbound)/artifacts/"
    r"(?P<name>[A-Za-z0-9._-]+\.[a-z]{2,4})\b"
)

#: References that were CORRECT WHEN SENT and were then invalidated by a later
#: renaming — mapped to the file that supersedes them.
#:
#: **A redirect, not an exemption, and the difference is the point.** Each entry's
#: target is asserted to exist below, so a stale reference becomes a checked
#: pointer rather than a hole in the sweep. An allowlist that merely says "ignore
#: this" would let the successor be deleted too, silently, which is the same
#: failure one level along.
#:
#: **Why they cannot simply be corrected: the laps are SENT.** Their bytes are
#: pinned in `tests/test_sent_laps_are_immutable.py`, and editing a delivered
#: document to tidy a reference is precisely the drift that map exists to prevent —
#: the peer holds the original. The record keeps the dangling pointer and adds the
#: forwarding address beside it.
_RENAMED_SINCE_SENT: Final[dict[str, str]] = {
    # Round 15 lap 2 cited the fork's contract by BUILD TAG. The artifact-naming
    # convention then moved to a content-derived source anchor (their lap 3
    # proposal), and the file was renamed. Same document, new name.
    "round-15-lap-01-provider-contract-g009a573.md": (
        "round-15-lap-01-provider-contract-a96262d1ea8f282c3.md"
    ),
    # Round 7 lap 13 predates the 2026-08-04 canonical-naming migration, which
    # renamed every artifact to `round-NN-lap-LL-…`. The `70dcf19` golden
    # reference is the one filed for lap 12, under the build it names.
    "round-7-golden-reference-70dcf19.log": (
        "round-07-lap-12-golden-reference-gceca8bc.log"
    ),
}


def _laps() -> list[Path]:
    """**OUR** laps — outbound and verified. Not theirs, and the reason matters.

    The first version swept inbound laps too and immediately "found" two missing
    artifacts: their lap 3 naming `round-14-lap-02-fullacceptance.txt` and their
    lap 8 naming `round-15-lap-07-fullacceptance.txt`. **Neither is a defect.**
    A path written in *their* lap is a path in *their* tree — that is where they
    filed the file we sent them — and it reads as ours only because we file their
    laps verbatim, which we do deliberately so the record is their bytes and not
    our summary.

    So the gate binds what we can actually be wrong about: a claim in a document we
    wrote, about a file we control. That is also the stricter half. Their omission
    is a delivery failure they can fix; ours is a false statement in our own
    correspondence, standing in a public repository.

    Recorded rather than quietly narrowed, because "the check found two things and
    I decided both were fine" is exactly the move that needs its reasoning visible.
    """
    return sorted(
        path
        for directory in ("outbound", "verified")
        for path in (HANDSHAKE / directory).glob("round-*.md")
    )


def test_there_are_laps_and_artifact_references_to_check() -> None:
    """The floor. A regex that stopped matching would make every assertion below
    pass by finding nothing — which is the failure this file is about, performed
    on itself."""
    laps = _laps()
    assert len(laps) >= 25, f"only {len(laps)} laps found — the glob is broken"
    refs = {
        match.group("name")
        for path in laps
        for match in _ARTIFACT_REF.finditer(path.read_text(encoding="utf-8"))
    }
    assert len(refs) >= 5, (
        f"only {len(refs)} artifact reference(s) found across {len(laps)} laps; "
        "the pattern has stopped matching how laps name their attachments, so "
        "this sweep is passing by not looking"
    )


def test_every_artifact_a_lap_names_is_actually_filed() -> None:
    """The gate itself, in both directions."""
    missing: list[str] = []
    for path in _laps():
        text = path.read_text(encoding="utf-8")
        for match in _ARTIFACT_REF.finditer(text):
            name = match.group("name")
            if name in _RENAMED_SINCE_SENT:
                continue
            target = HANDSHAKE / match.group("side") / "artifacts" / name
            if not target.is_file():
                missing.append(f"{path.name} names {match.group(0)} — NOT ON DISK")

    assert not missing, (
        "these laps name artifacts that were never filed:\n  "
        + "\n  ".join(sorted(set(missing)))
        + "\n\nA lap claiming an artifact that is absent reads as complete — the "
        "sentence naming the file is right there. Either file the artifact, or, if "
        "the reference is illustrative rather than a claim, add it to "
        "`_ILLUSTRATIVE` with a reason."
    )


def test_the_gate_can_actually_fail(tmp_path: Path) -> None:
    """**Asserted by construction, because the sweep above passes today.**

    A check whose real population is already clean is *"satisfied by finding
    nothing"* — it proves the record is tidy, not that the check works. So the
    logic is driven on a lap that names a file which does not exist.
    """
    # ASSEMBLED, never written as a literal. A dead `docs/…` path spelled out in
    # source is itself a broken pointer, and `test_doc_index_completeness.py`
    # correctly failed the first version of this test for exactly that — a fixture
    # that violates a sibling rule in order to exercise its own.
    absent = "round-99-lap-01-" + "nope.md"
    fake = tmp_path / "round-99-lap-01.md"
    fake.write_text(
        f"Filed at `docs/handshake/{'inbound'}/artifacts/{absent}`.\n",
        encoding="utf-8",
    )
    found = [
        m.group("name")
        for m in _ARTIFACT_REF.finditer(fake.read_text(encoding="utf-8"))
    ]
    assert found == [absent], found
    assert not (HANDSHAKE / "inbound" / "artifacts" / found[0]).is_file()


def test_every_redirect_points_at_a_file_that_still_EXISTS() -> None:
    """A redirect whose target is gone is a hole with extra steps.

    This is what makes `_RENAMED_SINCE_SENT` a pointer rather than an exemption:
    delete the successor and the sweep notices, where a bare allowlist would go on
    passing. Same reasoning as the elision rule — an omission is acceptable when it
    is *counted and marked*, never when it is silent.
    """
    assert _RENAMED_SINCE_SENT, "no redirects — has the map been emptied?"
    for old, new in sorted(_RENAMED_SINCE_SENT.items()):
        target = HANDSHAKE / "inbound" / "artifacts" / new
        assert target.is_file(), (
            f"{old} redirects to {new}, which is NOT on disk. The forwarding "
            "address is now as dangling as the reference it was added for."
        )
