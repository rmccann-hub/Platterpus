"""A lap that has been sent is frozen. Enforced by hash, not by intention.

Protocol v4 §4a: *"`SENT` is irreversible and is the whole reason the record is
append-only. A sent lap is never edited; a correction is a **new lap** that says
what it corrects."*

**We broke that rule and it took a cross-project checksum to notice.** Round 8
lap 10 was handed to the operator at `c125acd1…`, which is the value our own
transport manifest declared and the fork verified on receipt. Two commits later
we edited it — added a `HANDSHAKE-SHARED-HASHES` line to its header and appended a
whole section describing a protocol draft that has since been discarded — and it
became `2831e6fc…`. Nothing stopped it. Nothing even noticed, because *every*
check we had was about a file's **content** and none was about its **identity over
time**.

The fork found it in their round-9 lap 3 §C by comparing the hash we reported in
lap 2 against the bytes they held, and their diagnosis was exactly right in the
part that mattered: *"two and two match, which is the diagnosis"* — a
transport-level normalisation would have moved all three round-8 laps, and it
moved one. Their **hypothesis** about the cause (a botched revert probe) was
wrong, and the truth is worse: a deliberate edit to a sent file, by us, twice in
one commit.

**Why a pinned map and not a git check.** "Has this file changed since the commit
that sent it?" needs to know *which* commit sent it, and that is not derivable
from the tree — a lap is sent by an operator attaching it to a message, an event
git never sees. The hash is the only fact that crosses that boundary, so the hash
is what we pin.

**The map may grow and may never change an existing value.** Adding a row records
a new send; editing one would be the very thing this file forbids, performed on
the guard itself.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parent.parent

#: Every lap we have handed over, with the sha256 of the exact bytes sent.
#:
#: **Recorded at send time, from the bytes that left.** A value here is a claim
#: the other side can check against its own copy, and both projects now do.
#:
#: `round-08-lap-10.md` is the row that cost something: the value below is what we
#: sent and what the fork holds; the file in this repository drifted from it and
#: has been restored. It is first in the map for that reason.
SENT_LAPS: dict[str, str] = {
    "verified/round-08-lap-10.md": (
        "c125acd1c8a5bd2c5a2db47827998da24f6554fdab5e5937a3d5b49ea51d0898"
    ),
    "outbound/round-08-lap-02.md": (
        "e4406ff1baca686d70d5cb38c20e0a3bf56d405ff5a3e3ab74cd33f2d2fe21c5"
    ),
    "verified/round-08-lap-08.md": (
        "a2e37bcacbfaea53ffb00c4cdfc2d5c2d6c698ed79bfc0e8d262211f4915734d"
    ),
    # Round 9. Both **confirmed by the peer** rather than only recorded here:
    # cyanrip's lap 5 publishes lap 2's hash in its own digest lines and reports
    # verifying lap 4 against our envelope manifest. A pinned value the other side
    # has independently quoted is the strongest form this row takes.
    "verified/round-09-lap-02.md": (
        "e1499e25f2df98a635567285e115cefd01854b2f09270f43224bfc567697e0b0"
    ),
    "verified/round-09-lap-04.md": (
        "fb25fce0b2eb6bfe103fd505bb2c5b5329e36549842eb79f9dce13be86d95a0b"
    ),
    # Pinned AT HAND-OVER, which is the point: the row records the bytes that left,
    # and the only moment we can observe that is the moment we hand the file to the
    # operator. An earlier draft of this lap existed and was never handed over — it
    # therefore never reached `SENT` (v4 §4a: *"a lap that was drafted and never sent
    # may be edited or deleted freely and leaves no trace"*) and correcting it in
    # place was legal. The value below is the first and only lap 6.
    "verified/round-09-lap-06.md": (
        "f2a866416afcc837942dac4b94b0594107421a36da04bb6147c7aa191d28194d"
    ),
    # Lap 8 corrects three statements lap 6 shipped. **Lap 6's row above is NOT
    # touched** — that is the whole discipline: it is `SENT`, the fork holds those
    # bytes, and a correction is a new lap (v4 §4a). Editing the row to make the
    # record look tidier would be the round-8 lap-10 violation performed on the
    # guard against it.
    "verified/round-09-lap-08.md": (
        "6c5b57678c80947b8e954d47cb78ae18a732373c5a6eb89e1f37b5f60c19177f"
    ),
}

#: Rows whose full hash we do not hold — only the 16-char prefix a manifest
#: published.
#:
#: **Empty, and that is the goal state.** It held two rows for one lap, recorded
#: from prefixes rather than left unguarded, because a prefix is still a check and
#: refusing to record one would have left the file unguarded entirely. Both were
#: promoted the moment the full values were computed. Keep it empty.
PREFIX_ONLY: frozenset[str] = frozenset()

HANDSHAKE: Path = REPO_ROOT / "docs" / "handshake"


def _digest(relative: str) -> str:
    return hashlib.sha256((HANDSHAKE / relative).read_bytes()).hexdigest()


def test_there_are_sent_laps_to_check() -> None:
    """Floor. An empty map passes every assertion below by having nothing to do."""
    assert len(SENT_LAPS) >= 5, f"only {len(SENT_LAPS)} sent lap(s) pinned"


@pytest.mark.parametrize("relative", sorted(SENT_LAPS))
def test_a_sent_lap_still_hashes_to_what_was_sent(relative: str) -> None:
    """The whole file, in one line per lap.

    A failure here means one of two things and both need a person: either the file
    was edited after it was sent — which is the v4 §4a violation — or the pinned
    value is wrong, which is the same problem wearing the other hat. **Neither is
    fixed by updating the constant**; the fix is to restore the file, and to issue
    a *new lap* saying what it corrects.
    """
    path = HANDSHAKE / relative
    assert path.exists(), f"{relative} is pinned as sent but is not in the tree"

    actual = _digest(relative)
    expected = SENT_LAPS[relative]
    if relative in PREFIX_ONLY:
        assert actual.startswith(expected[:16]), (
            f"{relative} was sent as {expected[:16]}… and now hashes to "
            f"{actual[:16]}… — a sent lap is frozen (protocol v4 §4a). Restore it "
            "and issue a new lap that says what it corrects; do NOT edit this "
            "constant."
        )
        return
    assert actual == expected, (
        f"{relative} was sent as {expected[:16]}… and now hashes to {actual[:16]}… "
        "— a sent lap is frozen (protocol v4 §4a). Restore it and issue a new lap "
        "that says what it corrects; do NOT edit this constant."
    )


def test_the_restored_lap_10_is_the_copy_the_fork_verified() -> None:
    """Named separately because it is the incident, not just a row.

    The fork holds `c125acd1…`; their round-9 lap 3 §C asked us to restore rather
    than re-issue, *"since re-issuing changes which bytes are canonical"*. This
    asserts the restore landed and stays landed — the same discipline as proving a
    revert applied before believing the test run that follows it.
    """
    assert (
        _digest("verified/round-08-lap-10.md")
        == SENT_LAPS["verified/round-08-lap-10.md"]
    )


def test_no_pinned_lap_is_missing_its_prefix_marker() -> None:
    """The `PREFIX_ONLY` set must name real rows, or it is silently weakening one.

    A stale name here would let a full-hash row degrade to a prefix comparison
    without anyone choosing that — the exemption list quietly widening, which is
    the failure mode every allowlist in this repository is written against.
    """
    unknown = PREFIX_ONLY - set(SENT_LAPS)
    assert not unknown, f"PREFIX_ONLY names rows that are not pinned: {sorted(unknown)}"
    for relative in PREFIX_ONLY:
        assert len(SENT_LAPS[relative]) >= 16, relative
