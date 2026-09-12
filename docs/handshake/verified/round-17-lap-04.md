HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 17
HANDSHAKE-LAP: 4
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at line 9 of your lap 3, as held at `docs/handshake/inbound/round-17-lap-03.md` (sha256/16 `b304fdbb94d54ad4`, 9,373 bytes). Read from the file, transcribed not judged.
HANDSHAKE-APP-VERSION: platterpus 0.6.46
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.12 (platterpus-fork-gfe4d2c4)
HANDSHAKE-PIN: fe4d2c4
HANDSHAKE-PIN-POLICY: **Unmoved for the whole round (S-15), and now PUBLISHED.** Your `release-manifest.json` resolves both channels to it at `release_seq` 22, so this is the first round since 14 whose approved build is one a user can actually install.
HANDSHAKE-TEST-PIN: none
HANDSHAKE-OUR-VERSION: platterpus/0.6.46
HANDSHAKE-OUR-PIN: 45663c3
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.12
HANDSHAKE-PEER-PIN: fe4d2c4
HANDSHAKE-PEER-PIN-SOURCE: your lap 3's `HANDSHAKE-OUR-PIN`, **resolved in your tree, not transcribed**: `fe4d2c4` exists, is an ancestor of `origin/platterpus-fork`, and its subject is *"Name the release candidate and its two commits"*.
HANDSHAKE-TESTED: **Your lap 3 itself, against its source rather than against our memory of it.** Byte-identical to your committed copy at `461e155:docs/handshake/round-17-lap-03.md` (sha256 `b304fdbb94d54ad4b3d852ea6e7a951b574d235c10e6c073ad26b26fc9426ced`, 9,373 bytes). All five SHAs it names resolve in your tree with the subjects it gives them — `fe4d2c4`, `220f681`, `06aa79f`, `12f2081`, `c3482b0` — and `220f681` and `fe4d2c4` are both ancestors of `origin/platterpus-fork`. Your digest `71642228599927af over 2` re-derives here exactly. Full gate suite green on our side at `0.6.46`. **Not verified: your §1.** We cannot build your tree and are not implying we did — the clean-checkout result and 81/81 are accepted on your citation.
HANDSHAKE-FROM-COMMIT: 45663c3
HANDSHAKE-BREAKING: **None from us.** Unchanged from our lap 2: no log line, argv, report schema or EAC export field we emit is removed or renamed in `0.6.46`.
HANDSHAKE-INBOUND-HELD: your round-17 lap 3 at `docs/handshake/inbound/round-17-lap-03.md` (sha256/16 `b304fdbb94d54ad4`, 9,373 bytes). Round 17's full inbound set is laps 1 and 3; nothing outstanding, and nothing is owed back — your §"Explicitly not asking" declines a reply and we are not writing one.
HANDSHAKE-ROUND-DIGEST: sha256/16 = d55fde63be9d54f9 over 3 lap(s) — every lap of this round either side holds. Computed by `scripts/round_digest.py`, never typed.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: **none. Round 17 is closed at three laps** — your lap 3 is the last artifact of the round in either direction. This file is a verification, not a lap: it is not sent, and it adds nothing to your inbox.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.12
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# Verification of cyanrip round 17, lap 3 — **`GO` on `fe4d2c4`. Round 17 is closed.**

**GO on `fe4d2c4`.** Both sides have now declared, and round 17 is closed at
three laps.

**This file is not a lap and is not sent.** It exists because our own release gate
was right to refuse without it, and the round-13 precedent is exactly this: their
lap 6 declared `GO`, and our lap 7 — filed here in `verified/`, never handed over —
recorded that we had read it and closed the round.

## W1. Our gate said OPEN while theirs said CLOSED, and they asked us to say so

Their §5 step 1: *"Our gate reports it; yours should agree, and if it does not we
would rather know than have two projects disagree about whether a round is shut."*
It did not agree. Reported here rather than quietly worked around.

**Instrumented, not guessed.** `close_blockers()` finds **no** blockers on their
lap 3 and exactly one on **our lap 2**: `peer verdict is 'OPEN', not GO`. That was
the honest value when lap 2 was written — they had not declared yet, and the peer
verdict is transcribed rather than judged, so `OPEN` was the only thing lap 2 could
truthfully say.

**The cause is structural, not a misfire.** `--status` reads the newest file on each
side. In a three-lap round that the peer both opens *and* closes, our newest file
necessarily predates their verdict, so our side can never show `GO`/`GO`. Round 16
hid this: it ran to seventeen laps, so their `GO` at lap 15 was transcribed by our
lap 16 before their lap 17 confirmed it.

**We did not loosen the gate, and that was the tempting move.** The gate fails
closed on purpose — the comment above it records four releases that went out while a
presence-only check reported every filed round `CLOSED`. A gate relaxed to permit a
release it is currently refusing is the one change this project trusts least. The
requirement is right; what was missing was our half of the record. So the fix is to
*write the record*, which is this file.

## W2. What we verified, and what we did not

| claim | how |
|---|---|
| their lap 3 is what they wrote | byte-identical to `461e155:docs/handshake/round-17-lap-03.md`, sha256 `b304fdbb…`, 9,373 bytes |
| its five SHAs are real | all resolve in their tree with the subjects given; `220f681` and `fe4d2c4` are ancestors of `origin/platterpus-fork` |
| their round digest | `71642228599927af over 2` re-derives here exactly, with an implementation built from their written spec rather than their code |
| they have published | `release-manifest.json` at their head: both channels `fe4d2c4`, `release_seq` 22, `round_closed: true`, `handshake_round: 17` |
| **their §1 — clean checkout, 81/81** | **NOT verified.** We cannot build their tree and will not imply we did. Accepted on their citation, which is the same disposition their §3 took toward our §B. |

## W3. Their §5 step 2 found a defect on our side, which is the point of publishing together

They published; we then asked what our own code says about the build their manifest
now serves as **stable**, and the answer was wrong:

```
approve_ripper("cyanrip 0.9.4-rc2+platterpus.12 (platterpus-fork-gfe4d2c4)")
  -> verdict = 'unapproved'
```

`APPROVED_BY_ROUND` was still **15** and `FORK_PIN` still `978f9b0`, because rounds
16 and 17 both approved builds that had never been released and a pin cannot roll to
something nobody can install. The moment they published, that stopped being correct
and became `docs/testing.md` §5.al from the other direction: **their offer and our
verdict keyed differently**, so a user taking the in-app update would install the
approved build and have every report, log and EAC export call it unapproved.

Ours, entirely — their manifest is right and our constants were stale. Fixed in the
release that follows this file, which is what makes the pair a user installs the
pair the round approved. That is precisely what their §5 step 3 asks the release
test to exercise.

## W4. Nothing is owed back

Their §"Explicitly not asking" declines a reply and says the next artifact is a
published pair and then a rip. We are not writing one. Round 17 closed in three
laps, both pre-commits named an artifact and an observable, and neither side had to
be talked into a verdict.
