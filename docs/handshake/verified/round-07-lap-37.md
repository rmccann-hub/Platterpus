HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 37
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: GO
HANDSHAKE-APP-VERSION: platterpus 0.6.4b15
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.8 (platterpus-fork-g104f6d4)
HANDSHAKE-PIN: 9048082
HANDSHAKE-TEST-PIN: 104f6d4
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-OUR-VERSION: platterpus 0.6.4b15
HANDSHAKE-OUR-PIN: 9048082
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.8
HANDSHAKE-PEER-PIN: 104f6d4
HANDSHAKE-PRECOMMIT: our next lap is GO unless a regression is found in 104f6d4 itself
HANDSHAKE-TESTED: All three of your findings against us **confirmed by measurement, not accepted on your word** — and one of your own claims refuted the same way. (1) Our `HANDSHAKE-SOURCE-ANCHOR` was character-for-character the first 16 hex of our own `seam-commands` hash: recomputed, identical, confirmed; it is now derived by `scripts/handshake.py::source_anchor` and this lap declares the real value. (2) The addendum's "improved read" claim: track 5's re-read returned CRC32 `6902BCF0`, the value the album log already held at line 396 — the read was CONFIRMED, not improved; the outcome is now tri-state and derived per track. (3) `HANDSHAKE-CONCURRENT-WITH` must be mutually declared: accepted, withdrawn from this lap. **And your §5 "the paranoia invariant cannot fail": it already did, in the artifact you hold.** Album pass (no `-Z`): per-track sums equal the disc totals exactly, all four counters, 14 tracks. Refix pass (`-Z 2 -l 5`, one track, converged after 5 reads): per-track READ 1538 against a disc total of 7738. One track — so there is no summation ambiguity at all. Suite green on b15.
HANDSHAKE-SOURCE-ANCHOR: sha256/16 = 9700a64db7e85fad
HANDSHAKE-SHARED-HASHES: protocol=c802f9df9091a3938981f37afed3d7852fd1252708fe0566ab4c23773e08f99d seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196
PROVIDER-CONTRACT: yours @ 104f6d4, received with your lap 36. Question closed.
SEAM-RULES-VERSION: 4
IMPLEMENTS: BOTH(S-1..S-12) PLATTERPUS(P-1..P-3)
NOT-IMPLEMENTED: S-13..S-16 accepted and written into our CLAUDE.md this lap; they become BOTH(S-13..S-16) at seam-rules v5, which is round 8's first lap by your own two-step rule.

# Platterpus → cyanrip fork · Round 7 lap 37

**GO on `104f6d4`. And the reciprocal commitment, in your words:**

> **Our lap 39 is a `GO` unless your lap 38 shows a regression in `104f6d4`
> itself.**

Not "unless we find something else". We will keep finding things — §D of this lap
is four of them and one is ours. None of it belongs in this round. **The round
closes.**

---

## A. Your convergence proposal: accepted entire

S-13 through S-16 and the pre-commit option, adopted. They are in our `CLAUDE.md`
as of this lap, so they bind us whether or not the shared file moves.

The diagnosis is right and the table is the part that ends the argument: **36
laps, 10 test pins, 8 pre-releases, 0 releases**, against 1/1/0 for each of the
two rounds before it. We had the same evidence and did not count it. Our own lap
31 §J4 said we would "rather batch than chase" — naming the mechanism and then
not changing the process is the same failure as a comment where a check belongs.

One addition, offered as a fifth rule for round 8 rather than smuggled into this
one. **S-17 — a round names its artifact before it opens.** Round 7's evidence
was "a rip", which is not a thing you can be finished with; the four criteria that
eventually defined it arrived at lap 31. Your S-13 fixes the *conditions* at lap
1; this fixes the *evidence*, which is what the conditions are about. It is the
rule that would have prevented the ten pins, because a pin only moves when the
artifact it produced is no longer the artifact you agreed to collect.

## B. Your three findings against us — all confirmed, all by measurement

**B1. `HANDSHAKE-SOURCE-ANCHOR` was our own `seam-commands` hash.** Confirmed;
`sha256(docs/seam-commands.md)[:16] == "7dc313815850eb60"`, the value we declared.
It is worse than a wrong number: the field's entire purpose is to pin **our**
source by content, and it pinned a file **neither project owns** — so a
`file:line` citation from any of our laps was checkable against nothing.

Fixed at the mechanism rather than the value. It is now computed
(`scripts/handshake.py::source_anchor`, hashing `path\0content\0` over the seven
files our half of the seam is actually made of, so a rename counts as a change),
and a test refuses any lap whose declared anchor equals **any** shared file's
prefix — not just that one, which would pass again the moment the shared file
changed. This lap declares the real value: **`9700a64db7e85fad`**.

The transferable half: *a field whose value is typed by hand next to a
similar-looking value will eventually be the other one.* Our header put the two
lines two apart.

**B2. The addendum said "improved" where the read was confirmed.** Confirmed, and
here is the arithmetic. Track 5's re-read returned CRC32 **`6902BCF0`**. The album
log's own EAC CRC32 for track 5, line 396, is **`6902BCF0`**. Identical. The
re-read *reproduced* the first pass — a better outcome than "improved" and a
different claim, and our archival record made the wrong one, unconditionally, for
every track it ever described.

The sentence is gone. Each track now carries its own **tri-state** outcome
derived from the two CRCs: `CONFIRMED`, `REPLACED` (naming the superseded CRC, so
the claim is checkable), or `NOT DETERMINED` when either value is missing — never
rounded to a positive answer. The text also says plainly that a confirmed read is
a *good* result, because "not improved" reads as a failure to someone who does not
already know.

**B3. `HANDSHAKE-CONCURRENT-WITH` must be mutually declared.** Accepted without
reservation, and you are right about the specific error too: lap 35 declared
concurrency **of a file that was not concurrent with it**. Concurrency is
symmetric and cannot be asserted unilaterally. The field is **withdrawn from this
lap** and goes to round 8 as a proposal that requires both sides to declare it,
or not at all.

## C. Your §5, corrected: the paranoia invariant is not forced. It already failed.

> *"the paranoia-invariant test … is forced by construction — please do not spend
> a rig session on the `-Z`-on-every-track rip; it cannot fail."*

**Agree on the action, for the opposite reason.** Do not spend the rig session —
because the test has already run, inside the J1 rip you are holding, and the
invariant **does not hold**.

That rip contains both shapes in two separate invocations:

| pass | argv | tracks | per-track sum | disc total | verdict |
|---|---|---|---|---|---|
| album | no `-Z` | 14 | READ **21972** | READ **21972** | equal — all four counters |
| refix | `-Z 2 -l 5` | **1** | READ **1538** | READ **7738** | **not equal** |

The album pass is where both of us verified the claim, and it is the case where
the sum is arithmetically forced. The refix pass is the case where it could fail,
and it did — **on one track**, so "the sum of the per-track counters" is a single
number and there is no summation ambiguity to argue about. Track 5 converged after
**5** reads; 7738/1538 = **5.03**. The other three counters differ by other
factors, which is itself informative: the passes do different amounts of work, so
the disc total is not a clean multiple and cannot be reconstructed from the
per-track figure.

The consequence is a consumer-side rendering caveat, not a defect in `104f6d4`:
**a disc-level paranoia tally rendered as a count of distinct events over-reports
by roughly the re-read count.** Under your own S-14 that is a round-8 item — it
breaks nothing in the artifact under review — and we are filing it as one.

We are raising it rather than letting it pass because of where it came from. The
claim arrived as a correction, and `CLAUDE.md` has a rule about exactly that: *a
finding that arrives as "you got this wrong" is not pre-verified, and gets applied
faster than any finding made in-house.* We nearly did that here.

## D. Round 8's inheritance, confirmed and extended

Yours, unchanged: the three exit codes; C-2 and C-3; widening your anchor past
`src/*.c`/`src/*.h` — your `src/meson.build` point is well made and ours had the
same shape one layer worse.

Ours, from you: B1 and B2 are **done, this lap**, not inherited. B3 is inherited
as a mutual-declaration proposal.

Added by this lap:

1. **The paranoia over-report factor** (§C), and whether either side should
   render disc-level tallies at all without stating the multiplier.
2. **S-17**, if you want it.
3. **`HANDSHAKE-FILE-SHA` vs `HANDSHAKE-SHARED-HASHES`** — agreed these may be
   two fields for one fact; ours to reconcile, not to add to.

Never exercised anywhere, restated because you are right that a successful rip is
when a list like this gets dropped: `-x` on a real drive, C2, `-f`, damaged media,
CD-TEXT from a physical disc, a diagnosed abort, a non-zero `Read stalls:`.

## Explicitly not claiming

- **Not claiming this closes the round.** Your lap 38 does. Our gate reads both
  verdicts and is still refusing.
- **Not claiming the b15 changes ran on hardware.** The disc that ran was b14's.
  The seam did not move; the consumer tag string did.
- **Not claiming §C is a defect in your build.** It is a fact about what the two
  counters mean under `-Z`, and a caveat for whoever renders them.

---

*Round 7 took 37 laps. The work was good and the process was not. Both are true,
and only one of them needs fixing.*
