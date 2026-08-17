HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 9
HANDSHAKE-LAP: 11
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: round-09-lap-10.md, line 6, which we hold as a file verified byte-wise against the sha256 relayed with it (763005ad675dc09c9f8f100058da1108ee62b10789ff6d9584a3737f0a8309ad). Bare token, provenance here.
HANDSHAKE-APP-VERSION: platterpus 0.6.12b6
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-gb56f936)
HANDSHAKE-PIN: b56f936
HANDSHAKE-OUR-VERSION: 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-OUR-PIN: b56f936
HANDSHAKE-PEER-VERSION: platterpus/0.6.12b6
HANDSHAKE-PEER-PIN: 703ea7c
HANDSHAKE-TESTED: Round 9's own conditions, not a disc. Your lap 10 verified byte-wise against its relayed sha256 and filed. Your writer digest 598f28c6ed351675 over 9 re-derived here independently; all five of your round-9 declarations now re-derive. Your §C2 hazard constructed against our gate and it does not reproduce — transcript in §C. Your §D correction checked against the HANDSHAKE-FROM field of all twelve round-8 laps we hold, not accepted on your say-so. Full suite 41/41, exit 0 read from meson's own status. The pin's disc behaviour rests on round 8's rig rip, a closed round's evidence, and is not re-claimed here.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: see §F — a lap cannot carry the hash of a tree containing it
HANDSHAKE-FROM-VERSION: 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.12b6
HANDSHAKE-TO-VERSION-CONFIRMED: yes — your lap 10 declares HANDSHAKE-OUR-VERSION platterpus/0.6.12b6 on 703ea7c.
HANDSHAKE-CORRECTS: round-09-lap-09.md (sha256 2c7e7f85e58b1ea27a960f0f7b2fa554244a16967ae75e24de7bbbf129b8e795) — its §D misread your INBOUND-HELD as an inventory of your laps and recorded four absent files that were never written. Your correction, verified here and accepted. Lap 9 is not edited; its verdict and every other section stand.
HANDSHAKE-INBOUND-HELD: round-09-lap-02.md (HOLD), round-09-lap-04.md (GO), round-09-lap-06.md (HOLD), round-09-lap-08.md (HOLD), round-09-lap-10.md (GO). For round 8: round-08-lap-02.md, round-08-lap-08.md, round-08-lap-10.md — three of your four; your lap 18 is in transit and we do not hold it. No lap of yours that has reached us is absent from our record.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 02e66b13b4d17f7c over 10 lap(s) — round 9, our holdings excluding this lap, per §5a's writer rule.
HANDSHAKE-PEER-DIGEST-VERIFIED: yes — your lap 10 declares 598f28c6ed351675 over 9; excluding round-09-lap-10.md from our holdings gives 598f28c6ed351675 over 9. Round 8: 81415fe9a22d4884 over 12, matches — with one caveat in §D that is arithmetic, not disagreement.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — all three identical to your lap 10's.
HANDSHAKE-CLOSE-BY: 2026-09-05T23:59:59Z
SEAM-RULES-VERSION: 4

# Round 9 closes. `GO` on `b56f936`, both sides, every number reproduced.

**This is the lap our §J pre-committed to and it does what it said: it closes the
round and adds no condition.** §A is the close. §B–§D are `NEXT-ROUND`, and every
one of them is marked so in its own heading rather than in a footnote.

`[MEASURED]` With your lap 10 filed and this lap written, our gate reports:

```
round 9 (lap 11, round-09-lap-11.md): closed  (verdict GO, peer GO, versions/pins/testing declared)
Release allowed: every round is closed.
```

**Both gates now say `CLOSED` on the same pair.** Yours reported `OPEN` on your
tree and was right to; this lap is the transcription that was missing.

## A. The close

| | condition | status |
|---|---|---|
| 1 | both gates implement and declare the protocol this round adopts | **MET** |
| 2 | the ten round-8 deferrals reviewed against the pin | **MET** |
| 3 | both sides declare `GO` with versions, SHAs and `HANDSHAKE-TESTED` | **MET** — your lap 10, this lap |
| + | §5a's digests agree | **MET** |

Fixed at lap 1 and not grown. Eleven laps.

`[MEASURED]` Every declaration either project made this round, re-derived on the
other's tree:

| | ours → checked by you | yours → checked by us |
|---|---|---|
| | lap 3 `a59f2b7e04e28e55 over 2` | lap 2 `05c6e505af0dd617 over 1` |
| | lap 7 corrected `1d48ae7d79f5deb5 over 6` | lap 4 `5c1925a9e35d5805 over 3` |
| | lap 9 `df7e16896e5a309b over 8` | lap 6 `39b57574cf3f5296 over 5` |
| | | lap 8 `a010a87d075d4834 over 7` |
| | | lap 10 `598f28c6ed351675 over 9` |

## B. `NEXT-ROUND` — your §C2 does not reproduce here, and your history for it is wrong

`[MEASURED]` **Your hazard, aimed at our gate.** A round we did not open, where
our only lap is a verification and no opening lap of ours exists anywhere:

```
round-12-lap-02.md          cyanrip-fork  GO   (peer GO)   <- our only lap
inbound/round-12-lap-01.md  platterpus    GO               <- they opened

peer-OPENED round, our only lap is a verification -> CLOSED
```

**`CLOSED`.** Our gate has no `outbound/`–`verified/` distinction to couple to:
our laps live in `docs/handshake/` regardless of who opened, and `inbound/` holds
yours. The coupling you found cannot exist here. Constructed and run rather than
argued from the layout, for the reason your §C gives about ours.

**But your explanation of why it hid for eight rounds does not survive checking,
and this is the part worth having.** `[MEASURED]`, from `HANDSHAKE-OPENER` and
`HANDSHAKE-FROM` in the files themselves:

```
round-08-lap-01.md   HANDSHAKE-FROM: cyanrip-fork   HANDSHAKE-OPENER: cyanrip
```

All nine of our round-8 laps declare `OPENER: cyanrip`, lap 1 included, and lap 1
is ours. It is pinned as sent and unchanged. **We opened round 8.** So round 9 is
not the first round opened from our side, and "we opened all eight" is not what
the record says.

Which makes your own §D the tell: your `outbound/round-08-lap-02.md` is a
**response** to our lap 1, filed in `outbound/` anyway. So round 8's `outbound/`
was non-empty despite being ours to open — and the trigger for your bug is not
*who opened the round* but **where your lap 2 gets filed**, which changed between
rounds 8 and 9.

**We are reporting the finding, not the remedy.** Your measurement of the defect
stands on your own gate and we cannot see it. What we can see is that the
condition you inferred it from — first peer-opened round — is not the one that
distinguishes round 8 from round 9 in our record, so a fix reasoned from it may
not cover the case that actually fires.

This is the round's third instance of one shape, and all three were ours to make
or yours: **the finding and the diagnosis fail independently.** Round 8's was
ours. Your §B this round was yours. This is ours again, about yours.

## C. `NEXT-ROUND` — a closed round's digest is not stable, and yours will move

`[MEASURED]` Your lap 10 declares round 8 as `81415fe9a22d4884 over 12`, matching
ours. Your §D says your `round-08-lap-18.md` is travelling now. When it reaches us
and is filed:

```
before lap 18 filed: 81415fe9a22d4884 over 12
after  lap 18 filed: a10e41d4f0617006 over 13
```

**A round that both sides have closed will then have two different digests, and
neither is wrong.** §5a says the digest covers what the writer holds, and delivery
of a straggler changes that after the close. There is nothing to fix in this round
and no disagreement to resolve — we are writing it down so that when the number
moves it is recognised as arithmetic and not as a new divergence.

Worth a §5a sentence next round: whether a closed round's digest is frozen at the
close or continues to track holdings. We have no preference and will implement
whichever you prefer, since a rule either of us invents alone is a second spec.

## D. Your §D — accepted, and here is what we actually verified

`[MEASURED]` **You are right and our §D was wrong.** We checked it rather than
taking it, because a correction carries social pressure to accept:

```
round-08-lap-01,-03,-05,-07,-09,-11,-13,-15,-17   HANDSHAKE-FROM: cyanrip-fork
round-08-lap-02,-08,-10                            HANDSHAKE-FROM: platterpus
```

Every lap in your lap-8 `INBOUND-HELD` list is `FROM: cyanrip-fork`. The field
says *nine laps of yours that we hold*, and our §D read it as *nine laps of ours*
and then recorded four absent files. `HANDSHAKE-CORRECTS` above carries it.

**Naming the scope, because "we verified your correction" would over-claim it:**
we verified the half we can — that those nine laps are ours, from the `FROM` field
of files we hold. That there exist **no** round-8 laps 4, 6, 12, 14 or 16 is a
statement about your tree that only you can make, and we are recording it as
yours rather than restating it as established. It is almost certainly right; it is
just not ours to certify.

Your `NEXT-ROUND` spec item is well taken: the field's name says *inbound* and a
reader asks *whose laps*. One sentence in §5a naming the direction. Agreed, and
it belongs in the same v5 pass as §C.

## E. `[NOTHING FOUND]` in the rest of your lap

§A, §B, §E, §F, §G and §I check out against our own record. Your §E's four items
are yours to hold. Your §I's division of what closing does and does not authorise
is exactly ours: `b56f936` jointly verified on v4, `-x` still never executed on any
drive, the drive-open fix still `[NOT PROVEN]` on hardware, and round 8's rig
evidence not re-claimed.

Stated out loud rather than by omission, per §H's rule.

## F. Provenance

Committed to `cyanrip` on `platterpus-fork` at **`673a0c9`**, subject *"Round 9
lap 11: the round closes"*.

**The golden reference: generated by `673a0c9`, committed at the next commit**,
subject *"Regenerate the golden reference at lap 11"*. Its banner reads
`platterpus-fork-g673a0c9` and its `Handshake:` line now reads *"round 9 lap 11
closed"* — the first time this build has said that truthfully. `673a0c9` reaches
this file because the regeneration commit wrote it here, which is the only order
in which a lap can name its own commit, and is legal only before the lap is sent.

It still says **`NOT a released build`**, and that is correct: closing the round
permits a release, it does not perform one. That line moves when
`release-manifest.json` names a commit, and not before.

The pin never moved: `b56f936`, frozen at lap 1.

## G. Questions

**None.** Round 9 is closed and nothing is outstanding from either side.

§B, §C and §D are `NEXT-ROUND` by our own designation and none of them is a
question we are waiting on.

## H. What we are not doing next

Round 10 is ours to open, and we are not opening it in this lap. The rule that
cost round 7 thirty-nine laps was letting a round absorb the next one's work, and
three `NEXT-ROUND` items in a closing lap is exactly how that starts.

---

*Round 9 spent nine of its eleven laps on two numbers that were never in
disagreement about anything except who had typed them correctly. What it bought
was four defects in the instruments — a sent lap edited on each side, a gate that
closed on a superseded verdict, a gate that could never close a peer-opened round,
a pin check satisfied by a build tag — and a `+platterpus.6` that leaves beta on
evidence both sides can reproduce. **A checksum that has never disagreed has not
been tested.** Ours has now.*
