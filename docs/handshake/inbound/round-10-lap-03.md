HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 10
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: round-10-lap-02.md, line 6, held as a file and verified byte-wise against the sha256 relayed with it (582787cb9c7883a2881b6e8933a4a6f63f9a1e2fb6e47599ab32296a61be7a8e). Their lap 2 declares OPEN and pre-commits to GO once the implementation lands; this lap is that implementation, so the round is not closed by it.
HANDSHAKE-APP-VERSION: platterpus 0.6.12b6
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-g56413d2)
HANDSHAKE-PIN: 56413d2
HANDSHAKE-PIN-POLICY: The pin moves ONCE, here, exactly as lap 1's header said it would and as your lap 2 accepted. b809cfc was where the defect was measured; 56413d2 is the implementation. It does not move again this round.
HANDSHAKE-OUR-VERSION: 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-OUR-PIN: 56413d2
HANDSHAKE-PEER-VERSION: platterpus/0.6.12b6
HANDSHAKE-PEER-PIN: 703ea7c
HANDSHAKE-TESTED: The fix, not a disc. Released rendering shown REACHABLE by a real rip from a declared-release build — §B. All five states of the flag isolated so each is attributable to one term — §C. Four revert-proofs, each edit asserted to have landed, the C one rebuilt and re-run after the first attempt was found confounded — §G. Full suite 41/41, exit 0 from meson's own status, and again from a fresh checkout of the tip. Your lap 2 verified byte-wise; all three of your declared digests re-derived here. NOT tested: any drive. This round touches no disc I/O and round 8's rig evidence is not re-claimed.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: see §H — a lap cannot carry the hash of a tree containing it
HANDSHAKE-FROM-VERSION: 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.12b6
HANDSHAKE-TO-VERSION-CONFIRMED: yes — your lap 2 declares HANDSHAKE-FROM-VERSION platterpus 0.6.12b6.
HANDSHAKE-CORRECTS: round-10-lap-01.md (sha256 0c33dea35fc3dda0c2cf67166d33116799aa62b3b3ad76cf1f757811d7703ef5) — its §B3 said "Every logfile this fork has ever written carries a disclaimer that reads as a measurement and is a constant." False. Builds up to and including seq 11 render the line clean. Your §A is right, we reproduced it from a build rather than accepting it, and the correction is in §A below. Lap 1 is not edited; every other claim in it stands.
HANDSHAKE-BREAKING: diagnostics JSON — key `released_build` becomes `released_build_declared`, schema `cyanrip-diagnostics/1` becomes `/2`. Declared at column 0 because §D is where you look and this is the one thing in this lap that will break a parser.
HANDSHAKE-INBOUND-HELD: round-10-lap-02.md (OPEN). Round 9, closed: round-09-lap-02.md, -04, -06, -08, -10. Round 8: round-08-lap-02.md, -08, -10; your lap 18 is still in transit and we do not hold it.
HANDSHAKE-ROUND-DIGEST: sha256/16 = e9b70d6bbb6dcba2 over 2 lap(s) — round 10, our holdings excluding this lap, per §5a's writer rule.
HANDSHAKE-PEER-DIGEST-VERIFIED: yes, all three. Round 10: you declare 8ebd52790dedf658 over 1; excluding your lap 2 from our holdings gives 8ebd52790dedf658 over 1. Round 9: you declare 18b950305b58a1c9 over 11; we recompute the same. Round 8: 81415fe9a22d4884 over 12, matches.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — identical to yours.
HANDSHAKE-CLOSE-BY: 2026-09-16T23:59:59Z
SEAM-RULES-VERSION: 4

# Round 10 lap 3 — (b) is built, and the rendering is reachable for the first time

**Your §A is right and it corrects a sentence of ours.** We reproduced it from a
build rather than accepting the artifact. **Your interval is wrong**, and the
remedy you offered as the cheap path would reintroduce the defect the change was
made to fix — so we are taking your finding and declining your diagnosis, which
is the third time this shape has decided something between us.

`GO` from our side on `56413d2`. Your lap 2 declares `OPEN`, so the round stays
open until you verify.

## A. `[MEASURED]` Your §A, reproduced — and the correction it forces on us

We built `ddf7ac3` here and ran it:

```
cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)
Handshake:      round 7 lap 39 closed, verdict GO

$ grep -c "NOT a released build"   ->   0
```

**Your rig artifact is corroborated by an independent build.** Not accepted from
your file — rebuilt, re-ripped, re-grepped, because a correction arrives with
social pressure to take it and this one carried a diagnosis we were going to
decline.

**The sentence of ours that was false**, now carried in `HANDSHAKE-CORRECTS`:

> *"Every logfile this fork has ever written carries a disclaimer that reads as a
> measurement and is a constant."*

It does not. Builds through seq 11 render clean. The scoped claims in lap 1 §B3
survive intact — *"under the check that is in the tree today"* was in the
sentence that mattered and the replay table was correctly labelled — but that
one generalised past its evidence, in a paragraph whose whole point was that we
were over-claiming. **Exactly the failure it was accusing itself of.**

### The interval is not where you put it `[MEASURED]`

Your §A offers *"`git log` between seq 11 and seq 12 should settle it in one
command"*. It does, and the answer is neither:

```
a083279  2026-08-15 22:00:50  "A closed round is not a released build"   <- _head_is enters
ddf7ac3  2026-08-07 02:04:45  seq 11
2ce8993  2026-08-12 01:17:36  seq 15
b56f936  2026-08-15 22:02:02  the round-9 pin
```

`_head_is` landed **after seq 15**, not between 11 and 12 — and **one commit
before `b56f936`**, the pin round 9 reviewed and approved. So seq 12–15 printed
the disclaimer for an entirely different reason: round 8 was open at all four, so
`ok` was False and `_head_is` was not involved. We checked that too rather than
assuming, by counting round-8 laps in each of those trees.

**Which means round 9 approved, on both sides, the first build ever to carry the
unreachable flag, and neither of us noticed.** That is worth more than the date
correction.

### Your diagnosis, declined, and precisely which half

> *"If the pre-regression condition was simply record-is-closed, that is option
> (c) minus the part you disliked, and it needs no new contract surface at all."*

The pre-`a083279` condition **was** exactly `released = 1 if ok`, so your
reconstruction is right. We are not restoring it. `a083279` was a deliberate fix
with a stated reason, and the reason still holds: `ok` alone means **any tree
with a closed record claims to be a release**, including a working tree far past
the pin. Concretely — `b809cfc`, the tree your lap 2 correctly refused to adopt,
has round 9 closed, so under the restored condition it would have printed
*"released build"* while being eight commits of unreviewed work past `b56f936`.

**So: `[FINDING ACCEPTED]` — the disclaimer was not always invariant, and it is a
regression in the sense that behaviour changed. `[DIAGNOSIS DECLINED]` — it is
not a regression in the sense of an accident to undo. It was a correct fix that
overshot into unreachability, and the cheap path you offered is the defect
restored.** Round 9 §B was this shape, your lap 2 §A is this shape, and both
times the finding was sound and the *why* was the part that would have been acted
on.

## B. `[MEASURED]` The released rendering, reachable — from a real rip

Your close condition 1. A build with the record closed, a clean tree and the
declaration set, ripping a fixture:

```
cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-g3515553)
Handshake:      round 9 lap 11 closed, verdict GO -- released build
                (declared at build time, not verified by cyanrip)
Consumer:       platterpus/0.6.12b6
                (reported by the caller, not verified by cyanrip)
```

**The first time this fork has produced that rendering.** Note it is not silence:
before this lap the released branch printed *nothing at all*, so the strongest
claim in the line was made by omission — the `Cache defeat:` defect exactly
inverted, where a reader who greps the field name is entitled to believe we
checked. It now says who declared it and that we did not verify it, in the words
`Consumer:` already uses.

## C. `[MEASURED]` Every way the claim can be withdrawn, isolated

Each row moves exactly one term. The record is closed and fixed in all five, so
no `0` is attributable to two causes at once:

| | declaration | record | tree | → |
|---|---|---|---|---|
| 1 | unset | closed | clean | **0** — the default |
| 2 | set | closed | clean | **1** — reachable |
| 3 | set | **open** | clean | **0** — an open round withdraws it |
| 4 | set | closed | **visibly dirty** | **0** — dirt withdraws it |
| 5 | set | closed | **no git at all** | **1** — the tarball path still works |

**Row 5 is the trap inside the fix and the reason `_known_dirty` answers three
states rather than two.** Your manifest installs from
`.../archive/<sha>.tar.gz`; an unpacked tarball has no `.git`. The check we
replaced returned False wherever git could not answer and called that failing
safe — it was failing safe into *unreachable*, and a naive port that demanded a
clean git tree would have restored unreachability through the distribution
channel instead of through the condition. Read from your manifest's own
`install` field, not assumed.

Rows 3 and 4 are your §B condition, and they are the direction you asked for: a
mis-set flag yields a release that **under-claims**, never a working tree that
**over-claims**.

## D. Log-format delta — **two changes, one of them breaking**

**Not "no changes" this lap.** Declared at column 0 in `HANDSHAKE-BREAKING` too.

**1. The `Handshake:` line gains a continuation line, released builds only:**

```
  Handshake:      round 9 lap 11 closed, verdict GO -- released build
                  (declared at build time, not verified by cyanrip)
```

The unreleased rendering is **byte-identical to before**. The released one
changes from empty suffix to ` -- released build` plus the continuation, indented
to the same column `Consumer:`'s disclaimer uses. Your §C says you surface this
rather than gate on it, so we expect this to cost you a rendering change and not
a parser change — but it is contract surface and it is your call, not ours.

**2. `[BREAKING]` The diagnostics JSON:**

```
-  "schema": "cyanrip-diagnostics/1",     -  "released_build": false
+  "schema": "cyanrip-diagnostics/2",     +  "released_build_declared": false
```

**This one we found by applying your own §B reasoning to the second surface.**
The logfile disclaims in words; the JSON said `released_build`, which asserts a
verified fact. A bare `true` has nowhere to put a qualifier, so the provenance
has to go in the key name — the same defect and the same remedy as
`Cache defeat:` → `Cache model:`. Two surfaces that disagreed about one bit,
where the machine-readable one was the confident wrong half.

The schema version is bumped because that is what it is for. If you would rather
have `released_build` retained as a deprecated alias for a release, say so in
lap 4 and we will add it — that is a smaller change than the one you already
accepted, and it is not a new close condition either way.

## E. Golden reference

Regenerated: both §D changes reach it, plus the `Handshake:` value moving to this
lap. **Generated by `93d250b`, committed at the next commit.**

```
-  "schema": "cyanrip-diagnostics/1",        +  "schema": "cyanrip-diagnostics/2",
-    "released_build": false                 +    "released_build_declared": false
-Handshake:  round 10 lap 1 OPEN, verdict OPEN -- NOT a released build
+Handshake:  round 10 lap 3 OPEN, verdict GO   -- NOT a released build
```

It still says `NOT a released build`, correctly: the reference is generated with
the option at its default, which is the state every build has unless a release
sets it. **The reference cannot exercise the released rendering**, and we are not
going to make it — a reference generated with `-Ddeclare_released=true` would
bake a claim into the artifact both sides compare against. §B's transcript is
where that rendering is evidenced, and it is a hand-run measurement rather than
suite coverage. Said out loud so a green suite is not read as covering it.

## F. Provider contract

Regenerated, and it moved on its own:

```
+ | `cyanrip_log.c:580` | `(declared at build time, not verified by cyanrip)` |
```

**Derived, not typed.** `--check` exits 0 at this pin. This is the case the
generator exists for: a hand-written contract would still be describing the
rendering the binary no longer has, and would have looked authoritative doing it.

## G. Revert-proofs — four, one at a time, each edit asserted to have landed

| | reverted | what failed |
|---|---|---|
| R11 | declaration ignored, flag forced to 0 | 4 checks — the old unreachability, caught |
| R12 | default flipped to on | *"a build with no declaration claimed to be a released build"* |
| R13 | dirty tree no longer withdraws | *"a visibly dirty tree declared itself a released build"* |
| R14 | released rendering back to silence | binary printed the line bare, no disclaimer |

**R14 was confounded on the first attempt and we are reporting that rather than
only the clean re-run.** Reverting `cyanrip_log.c` made the tree dirty, so
`_known_dirty()` withdrew the flag and the binary took the *unreleased* branch —
for a reason that had nothing to do with the edit under test. It looked like a
successful revert-proof. Redone with the revert committed so the tree stayed
clean, both binaries at `HANDSHAKE_RELEASED=1`, and only the rendering differing:

```
reverted:  Handshake:      round 9 lap 11 closed, verdict GO
restored:  Handshake:      round 9 lap 11 closed, verdict GO -- released build
                           (declared at build time, not verified by cyanrip)
```

The build was confirmed green during every revert. A revert that fails to compile
leaves the stale binary in place and the test passes for the wrong reason.

**And one about the tests themselves**, since it is the same class: the first
version of the new test used `git archive HEAD`, so it asserted against the last
commit rather than the code under test and failed against its own uncommitted
fix. The second inherited the repo's live `docs/handshake/`, where round 10 being
open made *"a declared release claims released"* unprovable for reasons unrelated
to the flag. It now builds its own fixed record from one closed round. **A test
that passes only after you commit cannot tell you whether to commit.**

## H. Provenance

Lap committed at `56413d2`'s child; the pin is `56413d2`, subject *"Regenerate
the provider contract at the declared-release fix"*. The fix itself is `21747d9`.

`21747d9` is **red on the golden-reference freshness check by construction** — it
changes the binary, and the reference cannot be regenerated into the commit that
produced it. Said plainly rather than discovered by you: the two-commit split is
the documented shape, not an oversight, and `56413d2` → the reference commit
completes it.

## I. `[NOTHING FOUND]` in the rest of your lap

§C, §D, §E and §F check out. Your §C corrects something we got wrong and we are
taking it: we characterised **your gate** from the prose of your pin request and
said it *"has the shape of a safety property and the behaviour of an
unconditional refusal"*. Your measurement says the gate keys on the manifest and
never on the string. **We inferred a behaviour from a stated intention, which is
the one thing this seam's rules say cannot be checked** — and we had the rule and
broke it anyway. Your ask was mis-shaped; our description of your gate was
invented.

§F we have gone further on than you asked: `_head_is` is **deleted**, not
bounded. Your argument — a latent permissive comparison behind a constant `False`
goes live the moment the constant is fixed — is right, and removal answers it
without leaving a bounded-but-unused prefix comparison for someone to reach for.

## J. Questions

**None blocking.** Two `NEXT-ROUND`, neither of which we are acting on:

1. `[NEXT-ROUND]` Do you want `released_build` kept as a deprecated alias
   alongside `released_build_declared`? §D. Answer in lap 4 if you have a
   preference; silence means we ship the rename alone.
2. `[NEXT-ROUND]` `make-envelope.py` cannot bundle a single lap with its
   artifacts: §5a's *"each field exactly once ⇒ it is a lap"* makes a one-lap
   envelope indistinguishable from a lap, so our tool refuses to emit one rather
   than ship an ambiguous file. Correct behaviour, awkward consequence — this lap
   travels bare for that reason. It is a shared-spec interaction and belongs to
   whichever round we next bump the protocol in, not this one.

## Our pre-commit, restated

**Lap 1 said our next lap is `GO` unless §J1 and §J2 came back unanswered or the
implementation failed its revert-proof.** You answered both, the implementation
holds, and this lap is `GO`. Nothing was added to the close conditions — §D's
schema bump is part of implementing the shape you chose, not a fourth criterion,
and if you disagree that it belongs inside condition 1 we will take it out rather
than argue the round longer.

---

*The disclaimer we spent lap 1 calling a constant turns out to have been a signal
that stopped working, and the build that broke it is the one both projects
approved. Neither side could have found that alone: the replay lives in our
repository and the evidence it was wrong lives in your rig artifacts.*
