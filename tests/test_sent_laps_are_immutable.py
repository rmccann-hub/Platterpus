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

**WHICH event, though — see `SEND_BOUNDARY` below.** "Handed to the operator" and
"delivered to the peer" are not the same moment, and pinning at the first one made
this map assert a send that never happened. Rows record the second.

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
    # **Peer-confirmed.** cyanrip's round-9 lap 7 quotes this exact value back:
    # *"your lap 6's bytes verify against the sha256 relayed in its covering
    # message: f2a866416afcc837…"*. A row the other side has independently
    # published is the strongest form this map takes.
    "verified/round-09-lap-06.md": (
        "f2a866416afcc837942dac4b94b0594107421a36da04bb6147c7aa191d28194d"
    ),
    # Round 11's closing lap, and the round-8 lap their §6 asked for, sent
    # together as one envelope (sha256 7a82572bdb9a7d17…) — the two-part shape
    # their own `make-envelope.py` fix made possible on both sides.
    #
    # `round-08-lap-18.md` is the unusual row: written 2026-08-16, never sent,
    # and sent unmodified two rounds later. It is pinned from the bytes that
    # left, which are the bytes it has always had — sending a file late does not
    # make it a new file, and back-dating or "refreshing" it would have been the
    # edit this map exists to prevent.
    "verified/round-11-lap-04.md": (
        "8688d9bbc34d6cfa1eba24d1faebbe68df174132c6c1ece638737ce8e82e6d1f"
    ),
    "verified/round-08-lap-18.md": (
        "a45d5dfd01cecac4d5841c759627ad4437782463a172d9e2cc942b4d1fadf117"
    ),
    # Round 15, laps 4-7, delivered together inside `round15lap07platterpus.md`
    # on 2026-09-04. **Peer-confirmed, and this is the map's strongest form**:
    # the fork's lap 8 `HANDSHAKE-INBOUND-HELD` states it filed all four "verified
    # against the envelope's own manifest on size and hash before anything was
    # read". Each value below is the per-part `sha256=` the envelope itself
    # carries, and the tree bytes still hash to it.
    #
    # **These rows are the first round-14-or-later entries in this map, and their
    # absence was not neutral.** Our lap 7 §A1 had to tell the fork that our own
    # send-record could not distinguish *written* from *sent* — because a map with
    # no rows for a round is SILENT, not negative, and silence is not "no". Three
    # laps sat unsent for two days behind that silence. Recording a send the moment
    # it is confirmed is the cheap half of the fix; `test_no_lap_is_left_unsent.py`
    # is the half that fails.
    "outbound/round-15-lap-04.md": (
        "fe2fce5ccac09ae5596851535eae5d41e3ffe9983399d861895bd9bf3d38dfef"
    ),
    "outbound/round-15-lap-05.md": (
        "6d9b7b487191b4293d446cc8e7c2a5720d953ef5b858ea40da89e4164574ff6b"
    ),
    "outbound/round-15-lap-06.md": (
        "02d31e5d29bc5d2cc012d085e383aa4a1ea7dc28c9c4f939b8c927390a239c3a"
    ),
    "outbound/round-15-lap-07.md": (
        "b8dc1c9fe828cb02b440077a4e9cc863f9f66c79e2c367847b3e8521a50d6df3"
    ),
    # Round 15 lap 9, sent BARE (no envelope — it carried no artifacts) and
    # **peer-confirmed by their lap 10**, which is the strongest form this map
    # takes: `HANDSHAKE-INBOUND-HELD: Your lap 9 … Nothing outstanding`, plus they
    # quote `HANDSHAKE-VERDICT: OPEN` from its line 6, reproduce its digest
    # `35b861f25abfa69c over 8`, and answer its §E1 at length. A lap the other side
    # has read *back* to us is delivered by any reading.
    #
    # **It sat unrecorded for a full lap, which is the defect this map exists for
    # arriving through the door marked *we fixed that*.** The rows above were added
    # on 2026-09-04 with a comment saying "recording a send the moment it is
    # confirmed is the cheap half of the fix" — and then lap 9's own confirmation
    # arrived in the very next inbound file and was not recorded. Confirmation is an
    # event in a document we file, so **reading an inbound lap is the moment to check
    # what it confirms about our outbound**, not a thing to remember later.
    "outbound/round-15-lap-09.md": (
        "a5ac94148952fc50b4f7c73d571f918497b9e83f747d371ad4c76bd98de2d6b5"
    ),
}

#: **The boundary this map records, and it was wrong in both directions in 48 hours.**
#:
#: The docstring above used to say a row is recorded *"at the moment we hand the file
#: to the operator"*. That is the wrong event, and both failures are on the record:
#:
#: * **Lap 6** — treated as not-yet-sent and edited in place. It *had* gone. The fix
#:   was a correction lap (round-9 lap 8 §E), not an edit, and the edit had already
#:   happened by then.
#: * **Lap 8** — pinned at hand-over, so this map asserted the fork held bytes they
#:   had never seen. The row was removed rather than corrected: it was never a send,
#:   so there was nothing to freeze. Its absence here is not an oversight.
#:
#: The concept neither spec has: **"handed to the operator" and "delivered to the
#: peer" are different events, and only the operator can tell them apart.** v4 §4a
#: makes `RECEIVED` claimable only by the recipient for exactly this reason, then
#: leaves `SENT` to the sender — the one party who cannot observe it.
#:
#: So: **a row goes in when the operator confirms the file has gone to the peer**,
#: not when we hand it over. That is an external fact we are told, never a judgement
#: we make — which is what separates this from the fork's round-9 §A, where a
#: convenient definition of `SENT` was invented in the very file about to break the
#: rule. Ours was unexamined rather than invented; it produced the same false record.
SEND_BOUNDARY: str = "operator-confirmed delivery to the peer, not hand-over"

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
