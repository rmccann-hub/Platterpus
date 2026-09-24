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
    # Round 23 lap 4 — **the lap that closed round 23**, peer-confirmed in their
    # lap 5. Their closing lap declares `HANDSHAKE-PEER-VERDICT: GO` off this
    # file and reproduces the round digest over it.
    #
    # **Its citation is the first one anchored on the HASH rather than a commit.**
    # Their lap 5 adopts the round-24 proposal early: the sha256 is the anchor and
    # the commit is a fetch hint. That is what this row has always been — the
    # difference is that both sides now say so, so a pruned ref degrades a
    # citation from *fetchable* to *verifiable* rather than to nothing.
    #
    # The proposal exists because the hazard fired: PR #237 squash-merged, the
    # branch was deleted, and `b5af9bec`/`19c8ad20` were briefly unreachable on
    # the remote. Recovered from this session's clone before GitHub ran `gc`.
    "outbound/round-23-lap-04.md": "5ba5cea7665d0dc49409bae6732d73d3448aab3b47ac1521347c7ce8368936fe",
    # Round 24 lap 2 — our `GO` on `3e01bb3`, released on the maintainer's word
    # 2026-09-23. Pinned at release, before the peer has read it, because the
    # bytes they will cite are these; the held version (`c60a3a58…`) differed only
    # in its `HANDSHAKE-READY-TO-READ` line and was never released.
    "outbound/round-24-lap-02.md": "222a658f49a6aa4bba2e19d8dbf1dfa584efa642708f2925f1449b9a56f40568",
    # Round 25 lap 2: GO, landing PROTOCOL v6 / OWNERSHIP v3 / seam-rules v6;
    # released on the maintainer's word 2026-09-23.
    "outbound/round-25-lap-02.md": "3ae11ad1d4e3f7f2a18d83f329409c05c81a38a8cdec428b8ce117d8c64f852c",
    # Round 25 lap 4: GO, landing the merged v6 (05abdfde…) and naming 0.6.54 as
    # our candidate; released on the maintainer's word 2026-09-23, after checking
    # their branch held no newer round-25 lap (the K1 lesson of our lap 2).
    "outbound/round-25-lap-04.md": "f6d18230a52f47cebb6ff5b0c1722fa6586b49468bb3f3e451f6c8849464b3df",
    # Round 26 lap 2: OPEN — moves PIN_UNDER_REVIEW to df91ae7, names 0.6.54 as the
    # release that carries it, records the operator's §6b override for v0.6.54;
    # released on the maintainer's word 2026-09-23, after checking their branch held
    # no round-26 lap after their lap 1.
    "outbound/round-26-lap-02.md": "8485afc7f2a7b7e9e7e52733a38234d8d57210c56bf16ca6181ae80620ded0ff",
    # Round 26 lap 3: OPEN — our 0.6.54's section A refused .15 (our defect), the
    # fix, and the operator's §6b override for v0.6.55; released on the maintainer's
    # word 2026-09-24, after checking their branch held no round-26 lap after lap 1.
    "outbound/round-26-lap-03.md": "ba57e7bdbafc10bd67d000572124e2faf752c23d3ced8fc13fe343f3c90be26b",
    # Round 23 lap 2. **Peer-confirmed in their lap 3's `HANDSHAKE-INBOUND-HELD`**,
    # which names it at sha256 `4d1fd006...f38b8`, 18,686 bytes, read at
    # `platterpus@b5af9bec` — and their §D2 says they fetched the branch and
    # reproduced both figures rather than taking the declaration. So this file is
    # cited by two immutable records now: their lap 3 and, indirectly, ours.
    #
    # Frozen at the bytes that were SENT. As with round 20 lap 2 above, the file
    # was edited between being written and being released — the announce moved
    # HANDSHAKE-READY-TO-READ — and that is legal exactly because an unannounced
    # lap has not been sent. This row is what makes the immutability true rather
    # than stated.
    #
    # **This is also why `claude/session-omka9f` must not be deleted** (their §D2,
    # recorded in TASKS.md): we squash-merge, so the commit they cite never becomes
    # an ancestor of `main`, and a branch delete plus routine `gc` destroys it.
    "outbound/round-23-lap-02.md": "4d1fd006ee5dff274c32b9f715e4d2e8e95020d3699b08e81740356a66ef38b8",
    # Round 20 lap 2. **The closing lap of round 20, peer-confirmed with a git
    # blob as well as a digest.** Their lap 3 names it at sha256/16
    # `84fb47ab6b160ed0`, 17,483 bytes, and additionally quotes the blob
    # `7ff5ce4af53faf3336a85aef883783d722cfb1ea` — a second, independent identity
    # for the same bytes, which is stronger than either alone. Both re-derive here.
    #
    # Frozen at the bytes that were SENT, which is the point of this file: the lap
    # was edited once between being written and being released (the announce, which
    # moved HANDSHAKE-READY-TO-READ and finalised HANDSHAKE-FROM-COMMIT), and that
    # is legal precisely because an unannounced lap has not been sent. After the
    # flip it is immutable, and this row is what makes that true rather than said.
    "outbound/round-20-lap-02.md": "84fb47ab6b160ed0181b65db7b0e602273f7740dec7a353aa1908a1588442ca6",
    # Round 21 lap 2. Their lap 3's `HANDSHAKE-INBOUND-HELD` says they filed it
    # byte-exact, and their §0 quotes it back, so it is immutable from that moment
    # and this row is what enforces it. The bytes are the RELEASED ones, at
    # `platterpus@5aeffe9`: the announce moved three cells (the release-state
    # declaration, its note, and HANDSHAKE-FROM-COMMIT) and that is legal only
    # while a lap is unannounced. 19,968 bytes.
    #
    # **This gate caught the omission rather than a reviewer**, on the run right
    # after their lap 3 was filed: the obligation is created by THEIR file, not by
    # anything we do, so there is no step of ours that would naturally prompt it.
    # A pin that had to be remembered when the peer happens to confirm is a pin
    # that eventually is not added.
    "outbound/round-21-lap-02.md": "f6fbc01fe61efea288b1144c0f29508078164e17a2fa57a041b6aec1a5c02774",
    # Round 21 lap 4. **The closing lap of our side**, released 2026-09-18 and
    # confirmed by their lap 5 at sha256 `a0b1719d…`, blob `f1714da1…`, **52,821
    # bytes**, *"read at your `5ea3d2c` on `main`"* and re-derived on their filed
    # copy rather than taken from our message. All three values reproduce here.
    #
    # **It was revised five times while held and is frozen from the release
    # commit**, which is the whole point of the release cell: an unannounced lap has
    # not been sent, so its bytes are not yet anything anyone relies on. Their own
    # `-OBSERVED-HISTORY` records two of those intermediate readings, and the first
    # of them is what would have failed their filing had we not flagged it.
    "outbound/round-21-lap-04.md": "a0b1719db336dbcc74bd5ef4be24ee614ebb257619c14919bd0a52be274e88a6",
    # Round 22 lap 2, confirmed held by their lap 3 at this sha256, 19,775 bytes,
    # read at our `67aa051`. **The lap their §H1 is about** — it declared `yes` in
    # its header and `HELD` in its §F, because `--announce` rewrites the declaration
    # and not the prose. Frozen as sent, defect and all: a sent lap is a record of
    # what was said, and correcting it here would erase the evidence for a finding
    # we accepted. The tool now refuses that shape at release time instead.
    "outbound/round-22-lap-02.md": "206be6e101abb47188e2567460c3afd65e80e7553122adad596dd9bb8d352906",
    # Round 22 lap 4. **The closing lap, and the peer confirms holding it.** Their
    # round-22 lap 5 enumerates it in `HANDSHAKE-INBOUND-HELD` and quotes its §F
    # and "Explicitly not asking" verbatim while explaining that our close-gate
    # question did NOT reach them in it — so the bytes are cited evidence for a
    # finding on the record, in both directions. 15,283 bytes.
    "outbound/round-22-lap-04.md": "614c6115cb5a8601f746f32b579f40b3cdf717d9b542b448db71b4f7a8400e91",
    # Round 16 lap 16. **The closing lap, peer-confirmed twice over.** Their lap 17
    # names it in both line 11 (`HANDSHAKE-PEER-VERDICT-SOURCE`) and line 25
    # (`HANDSHAKE-INBOUND-HELD`) at sha256/16 `18cd6588321002ac`, 14,032 bytes,
    # *"extracted with your published reader and byte-identical to the raw copy"*.
    # Both numbers re-derive here.
    #
    # It is also the lap that closed round 16: with it filed, `--status` moved
    # round-16 to CLOSED and every one of the sixteen rounds is now shut.
    # Round 17 lap 2. **Peer-confirmed, delivered unedited, and it is the lap that
    # earned their GO.** Their lap 3 names it in both line 11
    # (`HANDSHAKE-PEER-VERDICT-SOURCE`) and line 25 (`HANDSHAKE-INBOUND-HELD`) at
    # sha256/16 `404f07b58fec5c98`, 10,785 bytes, *"extracted with your published
    # reader and byte-identical to the raw copy"*. Both numbers re-derive here, and
    # the emitter reported the same pair when it packed the envelope.
    #
    # The round closed on it at three laps: their §5 pre-commit made their lap 3 a
    # GO unless this lap reported a breaking row unhandled or named a defect in
    # `fe4d2c4`, and it did neither. A lap a peer resolves a pre-commit against is
    # one whose bytes must not move afterwards.
    # Round 18 lap 2. **Peer-confirmed twice over, and the confirmation carries the
    # byte COUNT as well as the hash — which in this round is the load-bearing half.**
    # Their lap 3 names it in line 11 (`HANDSHAKE-PEER-VERDICT-SOURCE`) and line 25
    # (`HANDSHAKE-INBOUND-HELD`) at sha256/16 `9ed8d8e4fc6e6aee`, 30,287 bytes,
    # *"extracted from the transport envelope with your published reader"*. Both
    # numbers re-derive here.
    #
    # **Why the count matters here specifically.** Round 18 turned on the difference
    # between the lap and the envelope that carries it: their §4b nearly filed the
    # envelope as the lap, which would have made their digest cover
    # `4135f0bcf1d599e6` / 31,949 bytes where ours covers these. Two sides holding
    # demonstrably different bytes under one lap number is the failure the digest
    # exists to surface, and it was caught by the size disagreeing — a hash alone
    # says *different*, a size says *different and here is roughly how*.
    #
    # It is also the lap that closed the round: their §5 declared GO and asked
    # nothing further. A lap a peer resolves a verdict against is one whose bytes
    # must not move afterwards.
    # Round 19 lap 2. **Peer-confirmed twice over, and this one was fetched from our
    # tree rather than handed over.** Their lap 3 names it in line 11
    # (`HANDSHAKE-PEER-VERDICT-SOURCE`) and line 25 (`HANDSHAKE-INBOUND-HELD`) at
    # sha256/16 `8bc901ae58b5ec6c`, 35,243 bytes, *"fetched from
    # `platterpus@87be510:docs/handshake/outbound/round-19-lap-02.md`"*. Both
    # numbers re-derive here.
    #
    # **First lap either side confirmed holding by GIT FETCH rather than by
    # transport**, which is what the 2026-09-13 rule changed — and it makes the pin
    # matter more, not less. Under hand transport the peer held a copy we could not
    # alter; under git they hold a *reference into our tree*, so an edit here would
    # silently change the artifact their verdict was cast against. The bytes are
    # frozen at what `87be510` published.
    #
    # It is also the lap their lap 3 resolved a pre-commit against: our §I said GO
    # unless they amended the tier-4 spec, and their §0 records that they did not.
    "outbound/round-19-lap-02.md": (
        "8bc901ae58b5ec6ccfb3fbdf97fceb3217541fe476aad159732c85ef6a98fd52"
    ),
    "outbound/round-18-lap-02.md": (
        "9ed8d8e4fc6e6aee70e2dc1f38bf27b70afc89b4431d6ae7ee5001fbf5b7121e"
    ),
    "outbound/round-17-lap-02.md": (
        "404f07b58fec5c982e18f8b5ef803a11c538ed0344870a2986ef72de79fdb15e"
    ),
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
    """``(inbound lap, our lap filename, hashes declared FOR THAT LAP on that line)``.

    One entry per (peer lap, lap of ours it names). The hash list is usually empty —
    most laps name what they hold without publishing a digest for it.

    **Hashes are scoped POSITIONALLY to the lap they follow, and that is the whole
    substance of this function.** The first version collected every hex run on the
    line and handed the same list to every lap the line mentioned, with a comment
    arguing it was safe: *"ANY, not ALL: a line may carry digests for several
    artifacts, so the question is whether ours is among them."* That reasoning holds
    while a field names **one** lap of ours plus unrelated files. It breaks the
    moment a field names **two of our laps and publishes a digest for only one**.

    Round 21 lap 5 did exactly that, correctly and unambiguously, in two fields:
    ``HANDSHAKE-PEER-VERDICT-SOURCE`` cites our lap 4 as the live source and then
    explains that the **superseded** source was our lap 2, quoting lap 2's sha256.
    All-to-all pairing therefore claimed the peer declared lap 2's digest *for our
    lap 4*, and the test failed with *"either the file was edited after it was sent
    … or the peer is holding different bytes"* — **about a file neither side had
    touched.**

    Two reasons this mattered more than a red suite. The failure is a **false
    alarm on an immutability gate**, and its own message instructs a destructive
    remedy — *"restore ours from the commit that sent it"* — so following it would
    have overwritten a correct lap. And it is the same shape the fork had just
    fixed on their side of the same field: **one field carrying two subjects, read
    by something that cannot tell which value belongs to which.** Theirs was in the
    writer; ours is in the reader.

    Scoping rule: a hash belongs to the nearest lap reference **at or before** it.
    Hashes preceding every reference are attributed to nothing, which is correct —
    an unattributed digest is not evidence about any particular lap. A line naming
    exactly one lap is unchanged by this, so the lap-14 case (our lap plus a digest
    for ``fullacceptance.txt``) still works the way its comment describes.
    """
    out: list[tuple[str, str, list[str]]] = []
    for path in sorted(HANDSHAKE.glob("inbound/round-*-lap-*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.split(":", 1)[0] not in _PEER_FIELDS:
                continue
            out += [(path.name, name, hashes) for name, hashes in _on_line(line)]
    return out


def _on_line(line: str) -> list[tuple[str, list[str]]]:
    """``(our lap filename, hashes declared for it)`` for one field line.

    **A repeated mention of the SAME lap is one subject, not two** (round 25,
    2026-09-23). The fork's round 25 lap 3 wrote `round-25-lap-02.md` — `GO`,
    sha256 `3ae11ad1…`, …, *filed byte-exact as*
    `docs/handshake/inbound/round-25-lap-02.md`. *We also hold your standing
    status … (sha256 `f7510382…`)*. The second mention is where they filed their
    copy. Positional scoping read it as a new subject and gave it the standing
    status's hash, and the immutability gate then reported our untouched lap 2 as
    edited after sending, and told the reader to restore it. That is the false
    alarm the docstring above describes, through a new door. The fork fixed the
    same shape in their own audit in the same lap (their lap 3 §F): a dash read as
    the end of a clause. So hashes stay scoped to the nearest reference before
    them, and every mention of one lap POOLS its hashes. An unrelated hash in the
    pool cannot make a wrong declaration pass: the check needs one declared hash
    to equal our bytes, and only our lap's own digest can.
    """
    # (start offset, our-lap filename) for every reference, in line order.
    spans: list[tuple[int, str]] = [
        (m.start(), f"round-{int(m.group(1)):02d}-lap-{int(m.group(2)):02d}.md")
        for m in _LAP_REF.finditer(line)
    ]
    for m in _LAP_BRACE.finditer(line):
        rnd, stem, group = m.group(1), m.group(2), m.group(3)
        spans += [
            (m.start(), f"round-{int(rnd):02d}-lap-{int(stem + d):02d}.md")
            for d in group.split(",")
        ]
    spans.sort()
    hits = [(m.start(), m.group(1)) for m in _HEX.finditer(line)]
    pooled: dict[str, list[str]] = {}
    for index, (start, name) in enumerate(spans):
        end = spans[index + 1][0] if index + 1 < len(spans) else len(line)
        pooled.setdefault(name, []).extend(h for at, h in hits if start <= at < end)
    return list(pooled.items())


def test_a_repeated_mention_of_one_lap_is_one_subject() -> None:
    """Round 25 lap 3's shape: our lap named, then named again as their filing
    path, then a different artifact's hash. The lap's own hash must be among the
    ones attributed to it, and the line must yield ONE entry for it."""
    ours = "3ae11ad1d4e3f7f2a18d83f329409c05c81a38a8cdec428b8ce117d8c64f852c"
    line = (
        "HANDSHAKE-INBOUND-HELD: `round-25-lap-02.md` — `GO`, sha256 "
        f"`{ours}`, 15,042 bytes, filed byte-exact as "
        "`docs/handshake/inbound/round-25-lap-02.md`. We also hold your standing "
        "status (sha256 `f7510382dab187f0…`, 43,724 bytes)."
    )
    entries = _on_line(line)
    assert [name for name, _ in entries] == ["round-25-lap-02.md"], entries
    assert ours in entries[0][1], entries
    # And different laps on one line still keep their own hashes apart.
    two = (
        "HANDSHAKE-PEER-VERDICT-SOURCE: `round-21-lap-04.md`, and the superseded "
        "`round-21-lap-02.md` at sha256 `aaaaaaaaaaaaaaaa`"
    )
    by_name = dict(_on_line(two))
    assert by_name["round-21-lap-04.md"] == [] and by_name["round-21-lap-02.md"] == [
        "aaaaaaaaaaaaaaaa"
    ]


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
