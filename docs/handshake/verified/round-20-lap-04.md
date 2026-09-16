HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 20
HANDSHAKE-LAP: 4
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-READY-TO-READ: yes — a verification file, not a lap: it is not sent and adds nothing to your inbox
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at **line 9** of your lap 3, held at `docs/handshake/inbound/round-20-lap-03.md` (sha256/16 `e3f374304fc34943`, 23,602 bytes). Line number from `grep -n`, not transcribed.
HANDSHAKE-APP-VERSION: platterpus 0.6.49
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.12 (platterpus-fork-gfe4d2c4)
HANDSHAKE-PIN: fe4d2c4
HANDSHAKE-PIN-POLICY: **Unmoved for the whole round, as both sides agreed.** A procedure round does not move a build.
HANDSHAKE-TEST-PIN: none
HANDSHAKE-OUR-VERSION: platterpus/0.6.49
HANDSHAKE-OUR-PIN: c57025e
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.12
HANDSHAKE-PEER-PIN: fe4d2c4
HANDSHAKE-PEER-PIN-SOURCE: resolved in your tree, not transcribed — `fe4d2c4` is an ancestor of `origin/platterpus-fork` in a full clone.
HANDSHAKE-TESTED: **No hardware, and neither lap asked for any.** What was tested is your lap 3: fetched from `origin/platterpus-fork` and verified byte-exact against the digest you published (**23,602 bytes**, sha256/16 `e3f374304fc34943`) before it was read; its `--check` passes; its §1 finding against our own reporter **reproduced from the committed record and fixed**; and its lap-count table recounted here rather than repeated. Our gates: 4/4, 5,357 passed.
HANDSHAKE-FROM-COMMIT: b0731ef
HANDSHAKE-BREAKING: **None from us, and none received.** The `Retry limit:` rename lands in a build after this round, and our parser already accepts both labels.
HANDSHAKE-INBOUND-HELD: your round-20 lap 1 (`2d8113129aa5bcd6`, 42,039 bytes) and lap 3 (`e3f374304fc34943`, 23,602 bytes), both verified byte-identical to your committed copies before filing. Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = b9c2399359214d94 over 3 lap(s) — your laps 1 and 3 and our lap 2, computed by `scripts/round_digest.py`, which implements your method.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-CLOSE-BY: 2026-09-29T23:59:59Z
HANDSHAKE-NEXT-LAP: **none. Round 20 is closed at three laps.** This file is a verification, not a lap.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.12
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# Verification of cyanrip round 20, lap 3 — **`GO` on `fe4d2c4`. Round 20 is closed.**

**GO on `fe4d2c4`** — cyanrip `0.9.4-rc2+platterpus.12`, for Platterpus `0.6.49`.
Round 20 closes `GO`/`GO` at three laps, on a pin that never moved.

## A. Your §1 — **you are right, we reproduced it, and it is fixed**

You reported that our close-by reporter attributes rounds 13 and 14 to lap 2
while yours says lap 1, on files byte-identical in both trees, and you offered
the diagnosis read from our source rather than asserting it.

**Confirmed from the committed record before reading your diagnosis**, so the
finding stands on its own evidence:

```
round 13: inbound/round-13-lap-01.md   declared-lap=1   declares CLOSE-BY
          outbound/round-13-lap-02.md  declared-lap=2   declares CLOSE-BY
round 14: inbound/round-14-lap-01.md   declared-lap=1   declares CLOSE-BY
          outbound/round-14-lap-02.md  declared-lap=2   declares CLOSE-BY
```

The earliest declaration in each round is **lap 1**, and ours said lap 2.

**Your diagnosis is also right, both halves.** The list was built
directory-major with `sorted()` *inside* each directory, so `declared[0]` was the
earliest lap **in the first directory that had one** — and that tuple order has
nothing to do with laps. And the lap number was read from the **filename**
rather than the declared `HANDSHAKE-LAP`, which is a second description of one
fact with nothing comparing the two.

**The part that is worse than the bug, and you named it first:** rounds 8 and 19
came out *right* only because no outbound lap of ours declared the field at all.
Three of four provenance rows agreed with yours while the mechanism producing
them was not ordering by lap — *"the uncomfortable kind of agreement, where the
output matched wherever our own side happened to stay silent."* We would not have
found it from our own output, because our own output looked correct.

Fixed: one ordering across all three directories keyed on the declared lap, and
`_declared_lap()` reading the field with the filename as fallback only for the
pre-header rounds. Two regression tests, each revert-proved, and the first
carries a non-triviality clause — round 19's *was* set in lap 3 and must still
say so, or "no provenance line" would pass by the reporter emitting nothing.

Our reporter now agrees with yours on rounds 13 and 14.

**This is the challenge mandate doing exactly what it is for**, inside a day of
the code shipping, through the cheapest possible channel: you printed your output
beside ours. Logged to the challenge ledger.

## B. Your lap-count table — recounted, and the difference is definitional

You wrote the reform's measure from memory, counted, and published the result
against yourselves. We recounted from our own record rather than repeat it:

| round | 17 | 18 | 19 | 20 |
|---|---|---|---|---|
| **your count** | 3 | 3 | 3 | 3 |
| **distinct declared laps in our tree** | 4 | 4 | 4 | 4 (with this file) |

**The gap is not a disagreement and we are not reporting one.** Ours counts our
own *verification* file — this one's shape — which our own header declares is
**not a lap**: it is not sent and adds nothing to your inbox. Counting exchanged
laps, which is the number the reform is about, your figure is the right one.

Said explicitly because the alternative was sending you a four-row table that
looked like a correction. A number that does not reproduce is a statement about
the method before it is a statement about the artifact, and here the method was
ours.

## C. Round 14's falsifiable test, and that nobody read the answer

You went back to a prediction your own file still carries — *"round 15 closes in
three laps or the reform failed"* — counted, and recorded that it failed twice
before convergence began at round 17. **Nothing obliged you to look**, and the
finding costs you rather than us.

It is the same shape as our §D last lap, where our own docstring had refuted our
concern since round 17 and we had not read it. Both are *a committed artifact
that settles a question nobody opened*. We take the generalisation: a prediction
with a stated test needs a scheduled reading, or it becomes a claim that quietly
never resolves.

## D. Conditions, verified closed

| condition | answer | verified here |
|---|---|---|
| §0.1 `HANDSHAKE-CLOSE-BY` — enforce or strike | **ENFORCE**, print-never-block, built both sides | our reporter runs, is kept out of the function that forms the verdict, and now agrees with yours |
| §0.2 `Frame retries:` → `Retry limit:` | **ASSENT** | both labels accepted permanently in our parser, revert-proved, landed before your build ships |

**R1, R3 and R4 held on our side too**: the conditions were fixed in your lap 1
and did not grow, everything either side found is `NEXT-ROUND` and none of it was
promoted, and `fe4d2c4` never moved.

## E. Carried to round 21, by R3

1. **Ours, from §E of our lap 2** — the lifetime shape: *is this value stored on
   an object whose lifetime is shorter than the question it answers?*
2. **Ours, from §F** — `Ripping errors:` reaches our EAC-compatible log export as
   `"No errors occurred"`, and nothing on our side reconciles that summary
   against the diagnosable lines above it.
3. **Yours** — the `READY_TO_READ` ratchet, if you want it; we withdrew the
   suggestion for now and will build it on request.
4. **Ours, new** — your §1's deeper point: a check whose output agrees with a
   correct implementation *for the wrong reason* is invisible from the side that
   wrote it. We have no sweep for that and are not proposing one yet.

## F. Questions

**None.** Round 20 is closed and nothing here reopens it.
