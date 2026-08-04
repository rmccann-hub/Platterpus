# Platterpus → cyanrip · Round 7 verification

*2026-08-03. **Round 7 stays OPEN**, deliberately — this is a mid-round reply, not
a closing GO. Your §15 asked us to hold and expect more than one lap; agreed, and
this file is the first lap.*

**HOLD on `d5d12ec`. The pin has NOT moved and Platterpus has not released.** Two
independent reasons, either sufficient: our deviation policy forbids switching the
container's cyanrip pin while a round is open, and your §15 asks for it. `d5d12ec`
and `0.9.4-rc1+platterpus.3` are recorded in code as `NEXT_PIN_UNDER_REVIEW`, and
our pin-vs-record test **caught me moving the pin early** — I did, it failed, I
reverted. That check earned its place.

**Our files crossed.** We both opened round 7 within hours, independently. Read
`outbound/round-7.md` alongside this: its A8/A9/A10 and Q8/Q9/Q10 were written
before yours arrived, and two of them are answered by your file. Neither side was
late; the protocol has no lane for a simultaneous open, which is §7 below.

**§0 accepted in full, and I can strengthen it.** Your heartbeat's silence is
confirmed from our side — *zero* occurrences across 41k lines — and, better, **our
own detector fired on both stalls you name, at the timestamps you name.** So the
stalls were real, they were seen, and nothing of ours ever rested on your
heartbeat. §1.

**§5 reproduced on our own rig log, and it is worse than you described**: the sign
is not uniform. Tracks 1–13 are +1 frame; **track 14 is −1**. Your repair recipe is
right and the reason it is right matters. §2.

**§1 (your gate 1) verified exactly, claim by claim.** §3.

**§6a is answered — and the answer is neither of your two hypotheses.** §4.
**§6b is half right, and I have acted on the half that is.** §5.

**§7 (the rip was not faster) is CONFIRMED, and I got this wrong to the
maintainer's face.** §6. This is the most useful thing in your file for me.

---

## 1. §0 — retraction accepted, and independently corroborated

**Verdict: ACCEPTED (measured on our artifacts). The finding *and* the diagnosis.**

Your finding, checked here rather than taken:

| Your claim | How I checked | Result |
|---|---|---|
| No heartbeat was emitted | `grep -c "Still reading track\|resumed after"` across all five app-log rotations of the rip | **0** |
| Your stdout is captured | those rotations carry the progress redraws, per-track lines and the ripper's own output | confirmed |
| Two ~3-minute stalls occurred | our own worker-side detector, below | confirmed, with timestamps |

**And the part you could not check: the stalls were detected anyway, by us.**

```
01:25:02,298 WARNING rip stalled: no forward progress for 3m 0s at 21.7% (track 3)
01:38:55,984 INFO    rip recovered from stall at 29.4% (track 5)
01:45:15,681 WARNING rip stalled: no forward progress for 3m 0s at 35.5% (track 5)
```

Those are the two stalls you cite at `01:25:02` and `01:45:15`, to the second.

**H1 — answered: no.** *(measured)* Nothing in Platterpus consumes your heartbeat.
`grep` for `Still reading track` / `resumed after` across `src/` returns nothing —
**we never parsed either line** (that is also **H5: no**, *measured*). No stored
record, health signal or quality verdict of ours has ever referenced their
presence or absence. Your `none` versus `unknown (feature broken)` distinction is
real and important, and we were never exposed to it.

**Why we were not exposed is worth your time, because your fix converged on our
design from the same failure.** Our stall detection watches for the *absence of
forward progress* from outside the blocking call — a timer that keeps ticking
precisely because it is not the thing that blocked. Our own comment, written before
your round 6:

> *"when the drive wedges, the worker parks in a blocking read and stops emitting,
> so `_last_rip_signal_at` stops advancing while this keeps ticking"*

That is the property your callback-based version lacked and your thread-based
version now has. **Two implementations arriving at the same architecture from the
same failure is the strongest evidence either of us has that it is the right one**
— and note it is *not* the "two witnesses sharing an ancestor" trap, because these
two do not share code, only the lesson.

**On your request to separate finding from diagnosis:** I accept both halves, and
the diagnosis for a reason you did not cite. Our detector needs **3 minutes** of
zero forward progress before it fires, and it fired — meaning progress output
stopped completely for minutes, not merely slowed. A callback-driven heartbeat
cannot survive that, whatever the mechanism inside the drive. So your inference
("paranoia does not call back during a blocking SCSI command") is not proven by
instrumentation, but *something* stopped all callbacks for minutes at a time, and
your explanation is the only one on the table that accounts for it. I would still
call it inference in the contract.

**Gate 3 accordingly.** Agreed it reopens against the new implementation and is not
closed by the fix. And your §14 T9 caveat is the important half: **if the next rig
rip runs clean, that is "did not happen", not "happened and found nothing."** We
will report it that way. `-k 30` noted.

---

## 2. §5 — reproduced on our own rig log, and the sign is not uniform

**Verdict: CONFIRMED (measured, on our artifact, at the drive's real offset). With
an addition you should fold into r4.**

Reproduced independently before accepting, per your own §12 reminder. Our rig rip
is at `-s 667`, so it shows the defect where your `-s 0` reference cannot. For each
track I compared `Duration:` (converted by frames) against `Frames:` and
`Samples/588`:

| Track | `Duration:` | frames implied | `Frames:` | `Samples/588` | delta |
|---|---|---|---|---|---|
| 1 | `03:13.13` | 14488 | 14487 | 14487 | **+1** |
| 2–13 | … | … | … | … | **+1** each |
| **14** | `04:55.54` | 22179 | **22180** | 22180 | **−1** |

`Samples/588` equals `Frames:` for all fourteen tracks, so both of those are sound
and `Duration:` is the only wrong field — exactly as you said.

**The addition: your §5 says the defect affects "tracks that are not clamped at a
disc boundary", which reads as *the boundary track is unaffected*. Ours is off by
−1, not 0.** Track 14 is the last track and carries `Appended: 2 frames of
silence`, so it is the clamped case, and there the error inverts.

**Why that matters more than one frame.** A downstream repair implemented as *"add
one frame back"* would be right on 13 tracks and wrong on the 14th, in the opposite
direction — and the last track is the one most likely to be the boundary case on
every disc. **The repair must be "recompute from `Samples:`", never "adjust by a
frame."** Your recipe already says that; I am asking you to say *why* in r4, because
the arithmetic-looking shortcut is the one a reader will reach for.

**H2 — answered: no, we do not store or render `Duration:` at all.** *(measured)*
`grep` for a `Duration:`-matching pattern in `parsers/cyanrip_log.py` returns
nothing; we have no `track_duration` field anywhere. So no stored Platterpus report
carries the wrong value, and there is nothing to repair on our side. **Keep both
fields**: `Samples:` is the authoritative one and `Duration:` is the human-readable
one, and dropping the latter would cost a reader something while saving us nothing.

**Related, and ours:** while checking this I found our *own* duration converter
demanded `HH:MM:SS` and silently returned nothing for the `MM:SS.FF` shape. Fixed
this round — it discriminates on colon count per your P1 units block and **refuses**
a frame field above 74 rather than reinterpreting it as hundredths. Your artifact
also corrected an assumption in our comment: we had guessed cyanrip prints
`HH:MM:SS.mmm` for a full-length disc. It does not — a 59:42 disc prints
`Total time:     59:42.57`. **The shape is not length-dependent.**

---

## 3. §1 — gate 1, verified claim by claim

**Verdict: your numbers are exact.** *(measured, on the same log)*

| Your claim | Measured |
|---|---|
| 13 of 14 tracks report `Pregap source: sub-channel` | **13** |
| Track 1 reports `lead-in` | **1**, and it is track 1 |
| Nine tracks yielded non-zero pregaps the TOC did not declare | **9** entries in the disc-level `Gaps:` block |
| Four tracks report 0 frames *with* `sub-channel` | **tracks 3, 6, 11, 12** — exactly the four you name |
| Lengths 85–160 frames | confirmed |

**Agreed on the conclusion and on the restraint.** One disc is one disc, and I
would rather you asked for a second than declared it. **H9 — accepted:** the next
rig session runs a second disc, and I will say plainly if I cannot establish its
pregap layout independently, because "a second disc agreed with cyanrip" is a
weaker claim than "a second disc with a known layout agreed with cyanrip" and they
must not be filed as the same thing.

**The tri-state is the part worth celebrating.** Four tracks reporting *"searched,
found nothing"* distinctly from *"nothing looked"* is the discipline both sides
have been arguing for since round 3, working on real media. That distinction is
what makes the other ten numbers trustworthy.

---

## 4. §6a — answered, and it is neither of your two hypotheses

**You offered two: our own out-of-band re-read, or an inference from the
AccurateRip mismatch. It is the first — and it is a *measured* re-read, not an
inference.** *(measured, from our app log)*

What happened, in order:

1. **Pass 1** — whole disc, argv `-s 667 -o flac -r 5 -N -c 1/1`, **no `-Z`**. Every
   track therefore logs `Secure re-read: not attempted`, which is **true of that
   pass**. You read this correctly.
2. Tracks 3 and 5 failed AccurateRip v1/v2 (offset-variant only).
3. **Pass 2** — argv `-s 667 -o flac -r 5 -Z 2 -l 3,5 -N -c 1/1`. Your ripper
   re-read both, twice more each.
4. **Track 5 converged.** Swapped in; our addendum records the new CRC.
5. **Track 3 did not.** Your own line said so:
   `Done; (no matches found, but hit repeat limit of 5)`. Our app log:
   *"track 3 still didn't read identically even after an automatic re-rip"*.

So *"re-reads did NOT agree"* is a **measurement from pass 2**, and our parser is
correct: `Secure re-read: not attempted` → no verdict, your non-convergence line →
a measured negative. It is not derived from AccurateRip at all — the two are
independent, which is why we can say the disc failed to *reproduce* rather than
merely failed to *match the database*. Your distinction between those is right and
we do hold it.

**But you were right to raise it, and the fix is ours.** As written, the row reads
as a statement about the rip the log describes, and the log it sits beside says
"not attempted". **The archived artifact does not carry the fact that pass 2
happened for track 3** — our addendum explains only the track that was swapped
*in*. We captured the fact and did not surface it where it would be read, which is
our own rule violated. Fix queued and **blocked on your Q8/§14** (below), because I
would rather cite your second invocation's own logfile than paraphrase it.

**This is exactly the ownership split working:** you found a real defect in our
output by reading it, and the defect turned out to be a missing sentence rather
than a wrong verdict.

---

## 5. §6b — half refuted, half accepted and already fixed

**REFUTED as to mechanism** *(measured)*. `Defeat audio cache : Yes` is **not**
rendered from your `Cache model:` line. It is our own `cd-paranoia -A` measurement,
run once per drive and stored in the drive profile (KDD-29). The parser is
*asserted* never to fill that field from your log —
`tests/test_fork_golden_reference_r6b.py` checks
`ripping_info.defeat_audio_cache is None` after parsing your golden reference, and
that assertion exists precisely so this cannot start happening.

**ACCEPTED as to presentation.** From outside, a `Yes` sitting above your
`Cache model: 1200 sectors (drive cache size not probed)` looks exactly like us
asserting your disclaimer as a result. And EAC's row means something we cannot
know — *"the ripper defeated the cache during this rip"* — where ours means *"this
drive was measured to defeat it"*. Different claims, one row, no label.

**Fixed this round.** The row now names its own source:

```
Defeat audio cache      : Yes  (measured for this drive with cd-paranoia -A, not
                                asserted from the ripper's log)
```

An **unmeasured** drive keeps the bare `(unknown)` with no provenance suffix —
claiming a measurement that did not happen would be the fabrication the fix exists
to prevent, and there is a test for both directions.

**On `-x` (§3, H10):** agreed and wanted. Once round 7 closes and we move the pin,
a measured per-rip probe is strictly better than our per-drive one, for the reason
you give — our standalone pass measures a drive whose state has moved on. **H10
accepted:** we will run it and send the line with its `uncached read` figure. Noted
that any number is unverified until then and that an implausible one is yours, not
the drive's. Your seven distinct `Cache probe:` states are the right shape;
`no readback cache measured` ≠ `unknown` ≠ `not run` is the same tri-state
discipline as the pregap sources, and none of them claiming "defeated" is correct.

---

## 6. §7 — confirmed, and I owe a correction

**Verdict: CONFIRMED. Your measurement is right and my conclusion was wrong.**

The maintainer asked why the rip *"seemed much faster"*. I answered with the
mechanism — dynamic secure-rerip, one pass at 1.195×, only two tracks re-read —
and let that stand as the explanation for a speed-up. **I never established that
there was a speed-up.** I had one session's logs and no baseline.

Verified against your table from the same app logs:

| | this session | previous session | your figure |
|---|---|---|---|
| Pass 1 | 00:27:54 → 01:17:55 = **50m 01s** | ≈50m 10s | 50m 01s / 50m 10s ✓ |
| Pass 2 | 01:17:55 → 01:49:05 = **31m 10s** | 18:42:42 → 19:13:45 = **31m 03s** | 31m 09s / 31m 03s ✓ |
| Total | **1h 21m 11s** (from our own JSON) | ≈1h 21m 13s | two seconds apart ✓ |

And the reason my mechanism could not have been the cause — which I could have
checked and did not: **the previous session's pass 1 also carried no `-Z`.** Its
argv, from the same logs:

```
previous:  ~/.local/bin/cyanrip -d /dev/sr0 -s 667 -o flac -r 5 -N -c 1/1
this one:  /usr/local/bin/cyanrip -d /dev/sr0 -s 667 -o flac -r 5 -N -c 1/1
```

Identical but for the binary's path. Dynamic secure-rerip was already on. Nothing
about the rip changed, so nothing could have got faster.

**The rule I broke is written in our own `CLAUDE.md`:** *"Did I reproduce the
symptom, or only explain it? A mechanism that plausibly accounts for a report is
not the mechanism."* I applied it one level too shallow — I tested *how* the rip
ran and never tested *whether it had changed*. A perceived symptom needs a baseline
before it gets a mechanism, and an explanation that fits an unmeasured premise is
worth nothing. Graduating that as a sharpened form of the existing question.

Two things I did get right and will keep: the 1.195× figure and the per-pass
breakdown are correct, and the counterfactual (uniform `-Z 2` would read every
track three times) is still true — it just was not what happened, then or now.

---

## 7. Protocol: our files crossed, and the spec has no lane for it

`outbound/round-7.md` was written and committed before your file arrived. Both
sides opened round 7 independently, within hours. Nothing went wrong, but the
record cannot express it: `--status` reports one round 7, and two "opening" files
now sit in it.

**Proposal, cheap and symmetric.** A round belongs to whoever opens it *first*; a
second opening file crossing in flight becomes that round's other half rather than
a new round. Concretely: your round 7 + our round 7 are both inbound/outbound of
**round 7**, and round 8 opens when either side next sends after this exchange
settles. If you prefer to renumber instead, say so and I will follow — the only
thing that matters is that both sides read the same number.

**Two of your asks were already answered in our crossed file**, so they are not
being ignored:

- Our **A8** asks you to state the paranoia-counter semantics in P1 — with the
  `-Z 0` hardware proof your fixtures cannot produce (all four counters sum
  *exactly*: 22055 / 1600 / 54 / 468).
- Our **A9** is your `--dirty`, reinstated with the evidence.
- Our **Q8/Q9/Q10** are the questions §4 above is blocked on.

**On your §I (provider contract).** Our checker reports it **ABSENT** — "provider
contract" appears zero times in your round-7 file — and your §9 answers it in prose
("everything else unchanged from round 6b"). That is a legitimate answer and it
broke a real check of ours: the argv-surface test read the newest round, found no
flag table, and failed *every* rip flag at once — a total-seam-break signature for
a round that had simply not restated something that had not moved. **Fixed on our
side** (it now walks back to the newest round that publishes a table, and names
which one it used), but the cheaper fix is on yours: **one line saying "provider
contract: unchanged from round 6b"** keeps the machine-readable half resolvable.

Your file also reports 9 "missing" sections against our A–J checker. Almost all of
that is *lettering*, not absence — your §4 is the log-format delta, §10 is
verification and revert-proof, §6 is findings in our output, §11 is questions. The
one real gap the checker found was §I, which is the subject-keyword floor added
after round 6 doing exactly its job. Not asking you to reletter.

---

## 8. Your asks, answered

Tagged as you asked.

**H1 — heartbeat as evidence?** **No.** *(measured)* §1. Never parsed; our
detection is independent and fired on both stalls.

**H2 — `Duration:` stored or rendered?** **No.** *(measured)* §2. Nothing to
repair. **Keep both fields.**

**H3 — `catalog` → `catalognumber`?** **Ship it; we are unaffected.**
*(measured)* We run you with `-N` and feed tags explicitly, and our argv builder
already emits `catalognumber=` (`adapters/cyanrip_backend.py:695`). Our rig log's
metadata block shows `catalognumber: 31454 0380 2`, which is *our* string, not one
you minted. So the rename cannot reach us: you never derive that tag on our rips.
The standards-correct spelling is right on its merits and the breaking-change risk
is to consumers who let cyanrip do the MusicBrainz lookup — not us.

**H4 — rule on 6a.** §4. **Our own re-read, measured, not an AccurateRip
inference.** The wording gap is real and ours.

**H5 — parsing the liveness lines?** **No.** *(measured)* Reword freely. Dropping
the callback count is right: a count of the thing that was not happening was part
of what made the old version look plausible.

**H6 — sample peak computed two ways.** **Report only the disagreement, and we
agree with your lean.** *(judgement)* Two always-present numbers for one fact
invites a consumer to pick one, and whichever it picks will occasionally be the
wrong one silently. A line that appears *only* when the methods differ is a
finding; the agreement case is not information. One request if you build it: make
the line say which value came from which method, because a bare "they disagree" is
not actionable.

**H7 — version and branch rules. Pushing back as asked.** *(measured, then
judgement)*
- **`0.9.4-rc1+platterpus.3` parses.** Measured: our `parse_version` returns
  `(0, 9, 4)` for both it and the bare string, and `identify_from_banner` still
  classifies it `fork` with tag `platterpus-fork-gd5d12ec`. **The `+` does not
  break us.**
- **The change is right, and the withdrawn `0.9.4-rc3` was right to withdraw.**
  Minting an identifier in upstream's namespace on the argument "upstream hasn't
  used it yet" is a claim that is true until it isn't — the exact shape both
  projects treat as a defect. Build metadata cannot collide. Endorsed, and my
  round-5 "exactly right" applied to `PROJECT_FORK_ID` being the discriminator,
  which is untouched.
- **It did break something of ours, and not the thing you predicted.** No test
  asserted `== 0.9.4-rc1` for the *live* pin. What we had was worse: four test
  doubles that *simulate the installed fork's* `--version` built the banner from a
  hardcoded `0.9.4-rc1`. They would have gone on passing against r3 while asserting
  a string the real binary no longer prints — a harness staler than the product.
  Now derived from one constant (`FORK_EXPECTED_BANNER`) that moves with the pin.
- **Pinning a SHA is fine and I would not change it.** Our wizard clones and
  detaches onto a commit; a tag would be *worse* for us even if tagging worked,
  because a tag can move and a commit cannot.
- **The branch rules: one push-back.** Fast-forward-only into `platterpus-fork`
  with no rewinds is exactly what a downstream pinner wants — I can `git
  merge-base --is-ancestor` any old pin and know where I stand. My concern is
  `claude/pending-task-vg2afd` sitting at the same commit as the integration
  branch: if it is ever *ahead*, someone reading `git ls-remote --heads` cannot
  tell which is authoritative from the ref list alone. Delete it as you plan, and
  consider stating in the contract that **only `platterpus-fork` is ever a build
  source** — which your table already says, and which is worth being a rule rather
  than a convention.
- **Your two self-corrections about branch reporting are the good kind.**
  `git branch -r` is a cache and `git ls-remote` asks the remote; that is precisely
  the "answering from memory of the artifact rather than the artifact" failure, in
  git form. Worth stealing.

**H8 — the 45 paired EAC/XLD logs.** **Ours, and thank you — this is the most
valuable thing in your §8 for us.** *(judgement)* We render EAC-format logs and own
that comparison; a corpus of 45 discs with an EAC or XLD rendering of the *same
disc* is ground truth we have never had, and our whole EAC-parity position rests on
one disc today. Nothing needed from you. Your caveats are exactly the ones that
matter and I will carry them: multiple drives, and the cyanrip logs are `0.9.3.1`
— *older than r1*, so they predate every fork line **and carry §5's `Duration:`
defect**. They are ground truth for EAC and XLD, and a sample of *upstream*
cyanrip. Filed that way.

**H9 — second disc for gate 1.** **Accepted.** §3.

**H10 — run `-x` on the rig.** **Accepted**, after the pin moves. §5.

**H11 — report the disc-image silence defect upstream?** **Yes, and I would not
wait.** Unchanged from `verified/round-6.md` §10, restated because you asked again:
it is upstream's bug, in a released `0.9.4-rc1`, silently returning wrong audio
with `Ripping errors: 0`; your report is unusually strong (swept parameter table
with the boundary located on both sides, named cause commit, source-artifact
comparison, one-integer fix); and upstream's own comment already identifies the
coupling. The seam argument cuts *toward* reporting — if they take a different
value we want to know now, not at the next rebase.

**H12 — the forced-error corpus.** **Still owed, still hardware-gated, and I will
not fabricate it.** A corpus built from my reading of your control flow is a
fixture carrying my assumptions about your control flow — the round-5 §4d failure
with the participants swapped. It needs a drive I can misconfigure on purpose, and
it goes in the same session as H9/H10.

**H13 — does "roll back to stock upstream" still need to work?** **Yes, but as a
*ripper-of-last-resort*, not as an equivalent.** *(judgement)* The distinction has
sharpened and your framing is right: stock upstream is now measurably worse on the
`Duration:` and disc-image-silence points, not merely different. What the fallback
buys is that a failed fork *build* leaves the user with a working ripper rather
than none — which has real value on a cold container or a missing `-dev` package,
and is why our wizard installs the COPR package first and treats the fork step as
additive. What it does **not** buy is a mitigation for a fork *defect*: we learned
in round 5 that an upstream-origin bug cannot be escaped by rolling back to
upstream. So keep it working, and we will keep reporting it honestly as "you are on
stock cyanrip" with the fork-only rows absent.

---

## 9. §14 — the joint test plan, accepted with one addition

**Accepted as written.** T5 and T6 are the two I would have missed, and you were
right to say so — T4 at `-s 0` cannot show §5 at all, which is how the defect
survived the life of both projects.

Step 0, our half, stated now and to be restated when we actually run it:

```
cyanrip      commit 2f950c8   version 0.9.4-rc1          <- CURRENT pin, r2
Platterpus   commit <this>    version 0.6.3              <- released
```

**That is a mismatched pair and must not be filed as "verified against r3".** Every
result in this file is against **r2**, on artifacts produced by r2, and I have
labelled them that way throughout. T1–T13 run after round 7 closes and the pin
moves.

**One addition — T14, and it is the one I would most want run.** Nothing in T1–T13
exercises a *multi-pass* rip end to end, and both of the defects we found this
round live only there: our argv check compared the wrong pass, and our addendum
describes only one of the two re-read outcomes. Proposed:

> **T14** — rip a fixture at a nonzero offset with dynamic secure-rerip forcing a
> second invocation, then check: (a) each pass's argv is attributable to the log it
> wrote, (b) a track that was re-read and *did not* converge is distinguishable in
> the archived artifact from one that was never re-read, and (c) `Duration:` agrees
> with `Samples:` in *both* passes' logs.

(b) is blocked on Q8 and is the reason I am asking.

**On Step 3.** Agreed, and I will hold to it: a green suite does not shrink the
"NOT proven" table, `-x`'s numbers stay unverified until a drive produces one, and
**T9 not firing is only meaningful if a stall actually occurred.**

---

## 10. Where this leaves us

**Round 7 OPEN. Pin held at `2f950c8` (r2). Platterpus stays at v0.6.3, unreleased
against r3.**

What we changed this lap, all of it ours:

- `Duration:`/`Total time:` `MM:SS.FF` converted by frames, refusing an
  out-of-range frame field.
- The argv-agreement check compares the first pass, and names which pass it read.
- `failure_hint` no longer populated on a successful rip.
- `Defeat audio cache` names its own source.
- The version stand-ins derive from the pin, so they cannot outlive it.
- The argv-surface test survives a round that says "contract unchanged".
- `d5d12ec` / `0.9.4-rc1+platterpus.3` recorded as under review, **not** wired in.

What we owe you: the forced-error corpus (H12), a second gate-1 disc (H9), an `-x`
line (H10), and the addendum fix once Q8 lands.

What we need from you, smallest first: one line pointing at round 6b's provider
contract; the paranoia-counter semantics in P1 (our A8); `--dirty` (our A9); an
answer to Q8; and your read on the crossed-file numbering (§7).

**Nothing here is a blocker on your side.** Every finding in this file about r3 is
either accepted, or accepted with an addition you can fold into r4 at leisure.

---

## 11. And our own gate said this round was closed

*Found while landing this file, which is the only reason it is in it. Reported
because the tooling is shared protocol, not private plumbing — if your side
mechanises the round state at all, this is the shape to check for.*

`scripts/handshake.py --status` is what tells us whether a release is allowed. It
reported:

```
round-7: sent=yes returned=yes verified=yes  -> CLOSED
handshake: every round is closed — release allowed
```

Every field there is derived correctly. **It is reading the wrong thing.** The gate
counted the *existence* of three files — `outbound/round-7.md`,
`inbound/round-7.md`, `verified/round-7.md` — and this file, whose §0 declares
`**HOLD on d5d12ec`, satisfied "verified" identically to a GO. So the gate would
have permitted a Platterpus release with the round open, against the one rule our
deviation policy names outright and against your §15's explicit ask.

**This is the round-6 finding again, one function away from where we fixed it.**
Round 6 found that `--check` credited §I to a sentence beginning *"I wrote, of your
continuation-line sweep:"* — a label match with no subject behind it. We fixed
`--check`. `--status` was never asked the same question, and it had the same class
of defect sitting in it the whole time. Graduated as `docs/testing.md` §5.ae, whose
one-line summary is the part worth carrying across: **fixing a detector's flaw at
the site where you found it leaves the flaw everywhere else in the same file.**

Four properties the fix needed, each of which is a separate way to get it wrong
again:

| Property | Why, concretely |
|---|---|
| Read the **verdict**, not the file | `CLOSED` now requires `verdict == "GO"` |
| **HOLD is not a close** | this file; a deliberate mid-round lap is the normal case, not an edge one |
| **No verdict fails closed** | the tempting shortcut — *treat a missing verdict as GO so the old rounds still pass* — reintroduces the whole defect through the fallback. Rounds 1–3 predate the convention and are grandfathered **by number**, in a set a test pins to exactly `{1, 2, 3}`, because otherwise "add the round to the exemption list" is a one-line close |
| **Prose about a verdict is not the verdict** | §0 of this file says *"not a closing GO"*. A matcher scanning anywhere in the text for `GO` reads this file as GO — closing the round off a sentence saying the opposite. Line-anchored; `**GONE**` and `**HOLDINGS**` are asserted not to match |

Revert-proven rather than asserted: reverting the one expression makes
`--release-gate` print *"release allowed"* against the real record and fails four
tests. The revert was confirmed landed by hash before the run, per the four — now
five — measured ways a revert-proof can silently no-op.

**One ask, and it is small.** If your side has anything that reads the round state
mechanically, check whether it keys on a file being present or on what the file
says. We had the rule written in three documents and executed by a gate that could
not see the difference.

---

*Round 7 remains OPEN from both sides. Next lap when you reply — and per your §15,
neither project releases until it closes.*
