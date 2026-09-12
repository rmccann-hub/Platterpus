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
import re
from pathlib import Path
from typing import Final

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
    # Round 16 lap 16. **The closing lap, peer-confirmed twice over.** Their lap 17
    # names it in both line 11 (`HANDSHAKE-PEER-VERDICT-SOURCE`) and line 25
    # (`HANDSHAKE-INBOUND-HELD`) at sha256/16 `18cd6588321002ac`, 14,032 bytes,
    # *"extracted with your published reader and byte-identical to the raw copy"*.
    # Both numbers re-derive here.
    #
    # It is also the lap that closed round 16: with it filed, `--status` moved
    # round-16 to CLOSED and every one of the sixteen rounds is now shut.
    "outbound/round-16-lap-16.md": (
        "18cd6588321002ace694176901e6a1706bdfdf2ff7dc626bd245cd51d4515cc9"
    ),
    # Round 16 lap 14. **Peer-confirmed, delivered unedited, and the lap it
    # confirms is the one that closes the round.** Their lap 15 line 24 declares
    # holding it at sha256/16 `2503184660c83ad0`, 17,199 bytes, *"extracted with
    # your published reader and byte-identical to the raw copy"*, and their line
    # 11 quotes its `HANDSHAKE-VERDICT`. Both numbers re-derive here.
    #
    # It is also the lap their §2 leans on: our §A2 pre-authorised taking a grader
    # SHA as they name it, and they moved the grader to `9ec722e` and cited that
    # sentence back. A lap that gets acted on by the peer is one whose bytes must
    # not move afterwards.
    "outbound/round-16-lap-14.md": (
        "2503184660c83ad0f73cc3d93d6f2529f9b6464de2f2fed1e32ac0f2932fe0f2"
    ),
    # Round 16 lap 12. **Peer-confirmed, delivered unedited, and confirmed by
    # the byte COUNT as well as the hash.** Their lap 13 line 24 declares holding
    # it at sha256/16 `4a69990fac889b83`, *"extracted from your envelope with your
    # own published reader and byte-identical to the raw copy, 24,150 bytes"*, and
    # their line 11 quotes its `HANDSHAKE-VERDICT`. The file here is 24,150 bytes
    # and hashes to that value, so three independent constructions agree: their
    # reader's output, their raw upload, and this tree.
    #
    # Fourth consecutive round-16 lap of ours that went out and stayed put.
    "outbound/round-16-lap-12.md": (
        "4a69990fac889b83bc68d92232f69e7f571edb53772e19cd8ad8a7a1791aff7b"
    ),
    # Round 16 lap 10. **Peer-confirmed, and confirmed by a route no previous row
    # had.** Their lap 11 line 24 declares holding it at sha256/16
    # `c5ab86e5fedfc33c` — and says they ran **our** published reader over the
    # transport envelope and that the part it produced is byte-identical to the
    # raw upload, 44,559 bytes, *"so the filed copy is the reader's output and not
    # a hand-picked one"*.
    #
    # That is the envelope's reader validating itself from the far side, which is
    # the only place it can be validated: we can round-trip it here all day and
    # only prove our own two implementations agree. Their line 11 also quotes its
    # `HANDSHAKE-VERDICT`, so the document is confirmed twice by two constructions.
    "outbound/round-16-lap-10.md": (
        "c5ab86e5fedfc33c7e69c7e56d112ec180e74c122bbbaf9f4ab3f9a18e233d39"
    ),
    # Round 16 lap 7. **Peer-confirmed, delivered unedited.** Their lap 8 line 24
    # declares holding it at sha256/16 `990bb6bb7d25ee4b`, *"split with your
    # reader and its part hash verified against your manifest before filing"*, and
    # line 11 quotes its `HANDSHAKE-VERDICT`. Second consecutive round-16 lap of
    # ours that went out and stayed put.
    "outbound/round-16-lap-07.md": (
        "990bb6bb7d25ee4bc74004e54a84a62f565c9ceee28dc065a903f8cd93bd04b0"
    ),
    # Round 16 lap 5. **Peer-confirmed, and delivered without an edit** — the
    # first round-16 lap of ours that can be said of. Their lap 6 line 24 declares
    # holding it at sha256/16 `ad77e1346fd47218`, *"split with your reader and its
    # part hash verified against your manifest before filing"*, and line 11 quotes
    # its `HANDSHAKE-VERDICT`. Their lap 6 digest row 5 carries the same value, so
    # it is confirmed twice by two constructions in one document.
    #
    # This is the row lap 3's failure was supposed to buy: the lap went out, the
    # peer vouched for the bytes, and the file here still hashes to them.
    "outbound/round-16-lap-05.md": (
        "ad77e1346fd4721811a3415c3be0b303e732dcbe1986bb274f6e19ff4c792a98"
    ),
    # Round 16 lap 3. **Recorded from the PEER'S declaration, and it caught an
    # edit I had already made.** Their lap 4 line 11 quotes our lap 3 at
    # sha256/16 `47368738c317f930`; the file in this repository had moved to
    # `5ac4edf670675f0b` because I revised it TWICE after handing it over — the
    # §D4 answer, then the 0.6.42 references. §4a says a sent lap is never
    # edited, and this is the FOURTH time this project has done it.
    #
    # Restored byte-exact from `6576d14`, which is the tree whose lap 3 hashes to
    # the value they hold. Everything I had added afterwards belongs in a NEW lap
    # and is going into lap 5.
    #
    # `test_every_lap_the_peer_confirms_holding_is_pinned_or_ratcheted` found this
    # on its own, off their enumeration, before I had finished reading their lap.
    "outbound/round-16-lap-03.md": (
        "47368738c317f9302adcc7f4f67734965f88c26a04cb71aaadd07ae7d1f69330"
    ),
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
    # Round 15 lap 11, sent bare and **peer-confirmed by their lap 12**:
    # `HANDSHAKE-INBOUND-HELD: Your lap 11 ... Nothing outstanding`, and their §5
    # reproduces its digest `f685729d41cf7f5b over 10`.
    #
    # **Recorded in the same commit that read the lap confirming it**, which is
    # the rule the lap-9 row above had to be added a lap late to learn. The
    # mechanism works: this row exists because reading lap 12 included asking
    # what lap 12 confirms about our outbound.
    "outbound/round-15-lap-11.md": (
        "5273610e96f14802e3df569db78b84bc31e8ffc2c8ac146ca4561057fa78a03c"
    ),
    # Round 15 lap 13 — **the second time we edited a sent lap, and the file whose
    # docstring opens with the first time.** Sent at the value below; two commits
    # later `784543d` rewrote a paragraph of it in place (an `[INFERRED]` label
    # corrected to `[MEASURED]`) and it became `a9e53304…`, 23,602 B. Restored.
    #
    # The correction was right and the method was wrong: protocol v4 §4a says a
    # correction is a NEW LAP, and the substance survives in
    # `scripts/revert_probe.py`, this suite's docstrings and the changelog, so
    # restoring the wire bytes loses nothing but the retro-edit.
    #
    # **The value is the fork's, not ours.** Their lap 14 declares
    # `7adffe7dc8f11983…` for the copy they hold; substituting it for our drifted
    # row reproduced their whole-round digest `6044c992bfe49c41` exactly, which is
    # how the drift was found. A hash we assert about our own file proves nothing
    # about what was sent; one the peer declares does.
    "outbound/round-15-lap-13.md": (
        "7adffe7dc8f119834699962fbabde12507b22cb70bc4f4b752d209dc89d396ae"
    ),
    # Round 15 lap 15 — **the THIRD lap the unpinned window has claimed, and it was
    # caught inside the hour rather than a round later.** Recorded the moment the
    # operator said "I've sent 15", which is precisely the `SEND_BOUNDARY` event
    # below: delivery to the peer, an external fact we are told and cannot observe.
    #
    # It was already being edited when that arrived. The lap promised a fix for the
    # fork's §5 item 7 and the fix had since been made, so a revision looked
    # obviously right — §310 does permit revising an *unsent* lap, and nothing in
    # this repository knew it had gone. Restored to the bytes above before anything
    # else, and the new material became a NEW LAP (round 15, lap 16), which is what
    # v4 §4a required all along.
    #
    # The window is the same one lap 13 fell through and §A1 of lap 15 describes:
    # a hand-populated map cannot close a gap between "sent" and "somebody told us
    # it was sent". The peer-declared-hash gate added alongside it does not help
    # here either — they have not yet published a hash for this lap. What ended it
    # was being told, which is the one signal the protocol says only the operator
    # has.
    "outbound/round-15-lap-15.md": (
        "6f201fb75568f53a352d767cf9a1223418e735eba570df25eef2518c7b38dba4"
    ),
    # Round 15 lap 16 — **the first row in this map recorded from the PEER's
    # declaration rather than from being told.** Their round-16 lap 1 opens
    # `HANDSHAKE-INBOUND-HELD: your lap 16 … sha256/16 32b393f458c4edec`, which is
    # a fact about delivery that neither of our trees can produce: they cannot hold
    # a file they were not sent.
    #
    # So the three-failure sequence above ends differently here. Laps 13 and 15 were
    # caught by a digest mismatch and by the operator saying so; this one was pinned
    # *because the peer said they had it*, and the value below is theirs, verified
    # byte-for-byte against ours rather than assumed to agree. That is the strongest
    # form of evidence this protocol has for "sent" — and it is still retrospective,
    # which is the whole of their round-16 §B and our §G question.
    "outbound/round-15-lap-16.md": (
        "32b393f458c4edeca455ef10acab7fff4c55246dd8092c1a93bd9ce0a9bd1ad6"
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


# ---------------------------------------------------------------------------
# WHAT THE PEER SAYS IT HOLDS — the half `SENT_LAPS` could not see.
#
# `SENT_LAPS` is populated by hand when we learn a lap went out, and we usually
# learn that from the peer's NEXT lap. That leaves a window in which a sent lap
# is unpinned and editable, and on 2026-09-06 a lap was edited inside it: round 15
# lap 13, sent at `7adffe7d…`, rewritten two commits later, caught only because
# the fork's lap 14 declared the hash they hold and our whole-round digest came
# out `1e91b168…` against their `6044c992…` — SAME COUNT, DIFFERENT HASH, over
# thirteen laps that were otherwise identical.
#
# So the obligation is DERIVED from the inbound artifacts instead of remembered:
# a peer lap that names one of our laps in `HANDSHAKE-INBOUND-HELD` or
# `HANDSHAKE-PEER-VERDICT-SOURCE` is the operator-independent evidence of the very
# event `SEND_BOUNDARY` describes, and it is sitting in this repository already.
# ---------------------------------------------------------------------------

#: The two header fields that describe **our** laps from the peer's side. Scoped to
#: these rather than to the whole document on purpose: body prose cites laps in both
#: directions, and a match there would attribute their laps to us.
_PEER_FIELDS: Final[tuple[str, ...]] = (
    "HANDSHAKE-INBOUND-HELD",
    "HANDSHAKE-PEER-VERDICT-SOURCE",
)

#: `round-15-lap-13.md`, and the brace form their lap 8 uses for a run of ours
#: (`round-15-lap-0{4,5,6,7}.md`). The brace form is not decoration — it names four
#: laps, and a plain-only parser would silently see none of them.
_LAP_REF: Final[re.Pattern[str]] = re.compile(r"round-(\d{1,2})-lap-(\d{1,2})\.md")
_LAP_BRACE: Final[re.Pattern[str]] = re.compile(
    r"round-(\d{1,2})-lap-(\d*)\{([\d,]+)\}\.md"
)

#: A 16-to-64 character hex run: the peer publishes both truncated and full digests.
_HEX: Final[re.Pattern[str]] = re.compile(r"\b([0-9a-f]{16,64})\b")


def _our_lap_path(name: str) -> Path | None:
    """Where one of our laps lives, or ``None`` if we hold no such file.

    Ours land in `outbound/` or `verified/` depending on the round; where a lap is
    filed is local bookkeeping, so both are searched (the same reasoning
    `handshake.round_status` gives for reading our verdict across both).
    """
    for prefix in ("outbound", "verified"):
        candidate = HANDSHAKE / prefix / name
        if candidate.is_file():
            return candidate
    return None


def _peer_references() -> list[tuple[str, str, list[str]]]:
    """``(inbound lap, our lap filename, hashes declared on that line)``.

    One entry per (peer lap, lap of ours it names). The hash list is usually empty —
    most laps name what they hold without publishing a digest for it.
    """
    out: list[tuple[str, str, list[str]]] = []
    for path in sorted(HANDSHAKE.glob("inbound/round-*-lap-*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.split(":", 1)[0] not in _PEER_FIELDS:
                continue
            refs = list(_LAP_REF.findall(line))
            for rnd, stem, group in _LAP_BRACE.findall(line):
                refs += [(rnd, stem + digit) for digit in group.split(",")]
            hashes = _HEX.findall(line)
            for rnd, lap in refs:
                out.append(
                    (path.name, f"round-{int(rnd):02d}-lap-{int(lap):02d}.md", hashes)
                )
    return out


#: Laps the peer says it holds whose sent bytes were never independently attested.
#:
#: **A ratchet, and deliberately not a set of `SENT_LAPS` rows.** Pinning today's
#: bytes for these would assert a byte-identity nobody measured — the same objection
#: `SENT_OUTSIDE_THE_ENVELOPE` states in its own docstring, and asserting it here
#: would put the unmeasured claim inside the guard that exists to refuse them.
#:
#: A row leaves this set the moment a peer lap declares a digest for it, which is a
#: measurement rather than an assertion; that is exactly how lap 13 graduated. The
#: set may SHRINK and must never grow: a new send is pinned in `SENT_LAPS` when the
#: operator confirms it, and if it reaches this set instead, the window it names has
#: claimed another lap.
PEER_CONFIRMED_UNPINNED: Final[frozenset[str]] = frozenset(
    {
        "verified/round-09-lap-08.md",
        "verified/round-09-lap-10.md",
        "verified/round-10-lap-02.md",
        "verified/round-10-lap-04.md",
        "verified/round-11-lap-02.md",
        "verified/round-12-lap-02.md",
        "verified/round-12-lap-04.md",
        "outbound/round-13-lap-02.md",
        "outbound/round-13-lap-05.md",
        "verified/round-13-lap-07.md",
        "outbound/round-14-lap-02.md",
        "outbound/round-14-lap-06.md",
        "outbound/round-14-lap-08.md",
        "outbound/round-14-lap-10.md",
        "outbound/round-14-lap-12.md",
        "outbound/round-14-lap-13.md",
        "outbound/round-14-lap-16.md",
        "outbound/round-14-lap-18.md",
        "outbound/round-15-lap-02.md",
    }
)


def test_a_hash_the_peer_DECLARES_for_our_lap_matches_our_copy() -> None:
    """The strongest check available, and it costs nothing: they already published it.

    A hash we compute over our own file proves the file is internally consistent and
    says nothing about what was sent. A hash the **peer** declares for the copy they
    hold is an independent witness, and seven of them are sitting in `inbound/`.

    This is the check that would have caught the lap-13 drift the moment lap 14
    arrived, instead of when someone thought to recompute a whole-round digest.
    """
    checked = 0
    for source, name, hashes in _peer_references():
        if not hashes:
            continue
        path = _our_lap_path(name)
        if path is None:
            continue  # a lap of theirs, or one we never filed — not our identity
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        # ANY, not ALL: a line may carry digests for several artifacts (lap 14
        # publishes one for our lap and one for `fullacceptance.txt`), so the
        # question is whether ours is among them.
        assert any(actual.startswith(h) for h in hashes), (
            f"{source} declares {hashes} for our {name}, and our copy hashes to "
            f"{actual[:16]}…. Either the file was edited after it was sent — which "
            "protocol v4 §4a forbids, a correction being a NEW LAP — or the peer is "
            "holding different bytes. Restore ours from the commit that sent it "
            "before deciding it is theirs."
        )
        checked += 1
    # FLOOR. Every clause above is skippable, so a parser that stopped matching
    # would pass this test by examining nothing — the failure mode this suite is
    # built around.
    assert checked >= 5, (
        f"only {checked} peer-declared hash(es) checked; the inbound record carried "
        "seven when this was written, so the extractor has probably stopped matching"
    )


def test_every_lap_the_peer_confirms_holding_is_pinned_or_ratcheted() -> None:
    """No lap of ours is both known-sent and silently unguarded.

    The peer naming our lap is evidence of delivery that does not depend on anyone
    remembering to record it — which is what makes it a gate rather than a habit.
    """
    named = {
        f"{path.parent.name}/{name}"
        for _, name, _ in _peer_references()
        if (path := _our_lap_path(name)) is not None
    }
    assert len(named) >= 20, (
        f"only {len(named)} lap(s) of ours found in the peer's held/verdict fields; "
        "33 resolved when this was written, so the extractor has probably broken"
    )
    unguarded = sorted(named - set(SENT_LAPS) - PEER_CONFIRMED_UNPINNED)
    assert not unguarded, (
        "the peer says it holds these laps of ours and nothing freezes them: "
        f"{unguarded}. Pin each in SENT_LAPS at the bytes that were sent. Do NOT "
        "add them to PEER_CONFIRMED_UNPINNED — that set is a ratchet over laps "
        "predating this check and may only shrink."
    )


def test_the_unpinned_ratchet_names_only_real_unpinned_laps() -> None:
    """A ratchet that names a pinned or non-existent lap is quietly weakening itself.

    Both directions matter: a row that no longer exists is dead weight that makes the
    set look larger than the debt, and a row also in `SENT_LAPS` is an exemption for
    something already guarded — which would let the real row be deleted unnoticed.
    """
    for relative in sorted(PEER_CONFIRMED_UNPINNED):
        assert (HANDSHAKE / relative).is_file(), (
            f"{relative} is ratcheted as unpinned but no such file exists"
        )
        assert relative not in SENT_LAPS, (
            f"{relative} is BOTH pinned and ratcheted as unpinned — remove it from "
            "PEER_CONFIRMED_UNPINNED; the ratchet shrinks, and this is a shrink"
        )
