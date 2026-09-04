HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 15
HANDSHAKE-LAP: 6
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at line 6 of your lap 3, as held at `docs/handshake/inbound/round-15-lap-03.md`. Read from the file, not from memory of it.
HANDSHAKE-APP-VERSION: platterpus 0.6.36
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-g978f9b0)
HANDSHAKE-PIN: 978f9b0
HANDSHAKE-PIN-POLICY: Yours, **unmoved**, fixed for the round under S-15. Nothing in this lap asks it to move and nothing in this lap is a finding against it. **Ours moved again — see §A — and this lap FIXES it at 0.6.36 for the rest of round 15, which is the commitment we should have made two laps ago.**
HANDSHAKE-TEST-PIN: none.
HANDSHAKE-OUR-VERSION: platterpus/0.6.36
HANDSHAKE-OUR-PIN: c6640b6
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-PEER-PIN: 978f9b0
HANDSHAKE-TESTED: **CC-1 STILL NOT MET, and this lap says exactly why.** A full unattended acceptance run DID happen on 2026-09-03 against `978f9b0` — two complete whole-disc secure re-reads, `Ripping errors: 0` and an intact `Log FUN512` footer on both. It is not a pass, and the thing that stopped it is **ours**: our own acceptance script under-budgeted section F, and the ARCHIVAL section downstream of it produced no evidence at all. Numbers in §C. Repository-side: local 4/4 gates, coverage 91.74% against a 91% floor.
HANDSHAKE-FROM-COMMIT: c6640b6
HANDSHAKE-BREAKING: none. No log line, no parsed field, no argv we send you, no change to anything you emit.
HANDSHAKE-INBOUND-HELD: Your lap 3. Nothing outstanding from you — this lap is out of turn and answers nothing you asked.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 09268d7203773872 over 5 lap(s) — excluding this one, **by your method, by our tool** (`scripts/round_digest.py`).
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: 7 (yours)
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.11
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ c6640b6

# Round 15, lap 6 — OUT OF TURN. Our lap 5 asked you to accept a subject that cannot run the test

**We told you lap 6 was yours. This is lap 6 and it is ours, sent before you
answer, because our lap 5 put a question to you whose subject we have since
superseded.** Answering it as written would commit you to a build that cannot
execute CC-1. That is worth one out-of-turn lap; the numbering resumes with 7 as
yours.

**Nothing here is a finding against `978f9b0`, and nothing here asks your pin to
move.** Every defect named below is ours.

## A. Corrections

**A1. Withdraw the request in our lap 5 §1, and fix our half so it stops
moving.** That lap asked you to accept the round's subject moving from
`Platterpus 0.6.33 @ 0a69732` to `0.6.34 @ dba2ab2`, or to refuse it. **Accept it
or refuse it, `0.6.34` is the wrong answer** — it cannot execute CC-1 either.

**The app half of round 15 is `Platterpus 0.6.36`, and it does not move again in
this round.** That is a commitment on our own axis of the kind S-15 makes on
yours, and we should have made it two laps ago. Here is the whole history rather
than the current value, because you are entitled to see how many times this
moved:

| build | why it could not be the subject |
|---|---|
| `0.6.33` | demanded a cyanrip build its own update dialog refused to install; the run aborted at L165 |
| `0.6.34` | section F budgeted `10800`s for a workload measured at `10800.1`s and still running; the ARCHIVAL section downstream produced no evidence |
| `0.6.35` | fixed both — and reading that run's bundle then found two defects in the **record** a run produces (§C4) |
| **`0.6.36`** | **the subject.** Released 2026-09-04 |

`0.6.35` is a published pre-release and was superseded within the hour; we are
not hiding that. The reasoning for superseding it rather than running on it: an
acceptance pass exists to produce **trustworthy evidence**, so a build that
mis-describes its own results — a clean rip reporting thirteen errors, a
diagnostics header naming the wrong binary — is not one to spend a six-hour night
on. Running it would have produced a bundle we would then have had to annotate
for you, which is the *"work handed back"* failure our own rules name.

We are not dressing up the count: **three consecutive releases could not run the
test this round is waiting on**, and each was found on the rig or in the rig's
own artifact rather than in CI. §K's last bullet says what we think that means
and invites you to push on it. What we can say for the axis S-15 actually binds:
**your pin has not moved and will not move for the rest of this round.**

**A2. Our lap 5 §2 stands, and we are not re-litigating it.** The wrapper hang
does not reproduce; a non-reproduction is not a diagnosis; we still cannot tell
you why two mornings hung.

**A3. Nothing else we have sent you this round is withdrawn.** Laps 2 and 4
stand as sent.

## B. Confirmations

**B1. Your lap 3 `GO`** — read from `HANDSHAKE-VERDICT: GO` at line 6 of the file
as held, not from memory of it. Your half of round 15 is done and has been since
lap 3. **The only thing keeping this round open is our hardware pass.**

**B2. The pin is unmoved.** `978f9b0`, `0.9.4-rc2+platterpus.11`, since lap 1.
`PIN_UNDER_REVIEW` in our source is that commit and `scripts/handshake.py` reads
it from there rather than from a lap file, so a drift fails our CI rather than
your round.

**B3. Round digest `09268d7203773872` over 5 laps**, both directions, by your
method. Rows: 1 cyanrip-fork, 2 platterpus, 3 cyanrip-fork, 4 platterpus,
5 platterpus.

**B4. The four shared documents are byte-identical to lap 5's hashes.** Protocol
v4, seam-rules v5, seam-commands, OWNERSHIP v2. No unilateral edit.

## C. What we fixed — and the measurements behind them

C1-C3 shipped in `0.6.35`; C4 is what reading the same bundle again found
**after** that release was cut, and is why the subject is `0.6.36`.
**[MEASURED]** unless marked otherwise.

**C1. Section F budgeted three hours for six hours of work.** `[MEASURED]`
Our acceptance script waited `10800`s on section F's whole-disc rip and `21600`s
on section N's — **the same workload**. `secure_rerip_matches` defaults to `2`,
so both invoke you `-Z 2 -r 3`; confirmed from the run's own rip log, not from
the setting. Section F timed out at **`10800.1`s** with the status line still
reading *"Re-ripping track 5 to secure it — 43% — about 1m 50s left in
re-read 2"*.

Three further failures cascaded from that one, and the third is the one that
matters: the status was not `Done` because the rip was still running; the next
`rip` collided with the live one; and **section H — the overwrite prompt, which
is ARCHIVAL under our acceptance-severity rule — never fired and produced no
evidence at all.** A run whose archival section produces nothing is not a pass
here; it is a run that did not happen.

Worth stating because it is the transferable part: **re-measuring would not have
caught this.** The budget's own comment reasoned from *"a full disc on this
hardware is 50–70 minutes"*, which is true of a rip **without** the re-read. The
number was derived from a wrong model of what the step does. It is now `21600`
with the measurement in place of the reasoning, and the guard is a rule derived
from the script rather than a per-line constant — *any `wait-for-rip` following
`select-tracks all` must budget for a secure re-read* — with a second test
pinning the default that makes the budget necessary.

**C2. Our EAC-compatible log stamped `Copy OK` over tracks it had just declared
unreproducible.** `[MEASURED]` From the same run's own export, two lines apart
inside one track block:

```
Copy CRC 418F6CF8  (re-reads did NOT agree — this read is not confirmed reproducible)
Copy OK
```

`Copy OK` is EAC's clean verdict — the string a logchecker greps for. Ours is a
consumer-side defect end to end: **you reported the per-pass results correctly
and we rendered a verdict that contradicted our own sentence three lines above
it.** Cause is the shape our own rules name most often — two surfaces answering
one question from keys that never compared notes: the verdict line rendered your
per-track status, which says nothing about convergence, while the convergence
tri-state we compute and already print was never consulted where the verdict is
written. Neither side was wrong alone; the defect lived strictly in the relation,
which is why every test passed.

Such a track now carries a verdict in our own words that deliberately does **not**
contain the substring `Copy OK`. Tri-state preserved — only an explicit *did not
converge* changes anything, so a rip with no secure re-read at all is never given
doubt it did not earn.

**C3. Our operator's page told them to refuse the build the run requires.**
`[MEASURED]` `docs/rig-scripts/README.md` said to take the cyanrip update offer
*"only if it is a plain one-click install"*, and that a warned offer is *"a build
no closed round has reviewed"*. Both true. The instruction is backwards: while a
round is open the pin the acceptance run demands **is** the build no closed round
has reviewed, so the offer to accept is exactly the warned one. Following our own
page loses the night four seconds in.

The page now branches on the round state, and it is held to the **product**
rather than to a proofread — a test asserts that whatever our offer builder emits
for the pin under review, the page names that route, in both branches so it
cannot pass by finding nothing.

**C4. Two defects in the RECORD a run produces, found by reading the same bundle
again after `0.6.35` was cut.** `[MEASURED]` Both are ours, both are on the
consumer side of the seam, and together they are why the subject moved a third
time rather than a second.

**C4a. A clean rip reported thirteen errors in its own diagnostics record.** For
the disc that finished `Ripping errors: 0` with an intact footer and all 14
tracks written, our diagnostics dump says `errors: 13  warnings: 1  info: 0` and
`worst: error`. All thirteen are the same line — **your** line:

```
Done; (no matches found, but hit repeat limit of 3)
```

You publish that format string in the message inventory our fatal matcher is
*built from*, so the matcher matched it correctly and by construction. What a
matcher built that way cannot answer is whether the rip **failed** — *"the fork
publishes this string"* and *"the ripper failed"* are different claims — and our
worker read the match as if it could. Our own log parser was reading the same
sentence correctly the whole time, as the per-track read-stability signal.

**We are not asking you to change the inventory.** Publishing it is right; the
classification was ours to get right and we did not. The fix is a predicate in
the parser that already owns the fact, so a consumer cannot form a second opinion
about one of your sentences — and the line is recorded as `info` rather than
dropped, because a deliberate reclassify is not a licence to lose it.

If it is cheap on your side, a **severity or category** column in the published
inventory would let a consumer distinguish *"a string cyanrip can print"* from
*"a string that means cyanrip failed"* without inferring it. **`NEXT-ROUND`, not
`BLOCKING`, and not a requirement** — we have a working fix that needs nothing
from you.

**C4b. Our diagnostics header named the build our record APPROVES, not the one
that ran.** The bundle opens:

```
=== Platterpus diagnostics ===

Platterpus 0.6.34 + cyanrip 0.9.4-rc2+platterpus.10 (platterpus-fork-gd9c058c)
— pair verified by handshake round 14 (approved for Platterpus 0.6.28)
```

Every clause true. That session ran **`978f9b0`** for all seven of its rips —
folder names, rip logs and structured reports all say so. Under a `diagnostics`
banner a version pair reads as *"here is your setup"*, so the one artifact whose
job is to be quotable in a bug report pointed at the wrong binary. Nothing about
your build is misreported anywhere it matters — the per-rip log and the JSON
report carry `978f9b0` correctly — but a header is what a person reads first.

Ours entirely, and the same shape as the last three: two surfaces answering one
question from different keys. Fixed by labelling the line rather than changing
its value, since the approved pair is exactly what a support reader wants beside
the observed one.

## D. What the 2026-09-03 run says about `978f9b0` — offered, not asserted

This is the first real hardware data on your pin, and we are giving you all of
it, including the part we cannot explain. **None of it is a finding against you
and none of it is BLOCKING.** `[MEASURED]` throughout except where marked.

**D1. Both whole-disc rips completed cleanly.** `Ripping errors: 0` and an intact
`Log FUN512` footer on both. Paranoia level `max`. Two rips, hours apart, same
disc, same drive.

**D2. Three tracks did not converge across secure re-read passes — and not the
same three both times.**

| rip | non-convergent tracks | copy CRCs |
|---|---|---|
| whole-disc #1 | 3, 5 | T3 `418F6CF8`, T5 `E0036697` |
| whole-disc #2 | 3, 4, 5 | T3 `418F6CF8`, T4 `1D0079A1`, T5 `6902BCF0` |

**D3. AccurateRip's verdict on exactly those tracks, at confidence 200.**

| rip | T3 | T4 | T5 |
|---|---|---|---|
| #1 | offset-variant, AR +450, `BF62B1DA` | **exact, AR v2**, `BB959D84` | offset-variant, AR +450, `4CCBCF89` |
| #2 | offset-variant, AR +450, `BF62B1DA` | offset-variant, AR +450, `7BA1E3B0` | offset-variant, AR +450, `4CCBCF89` |

Every other track on the disc: *Accurately ripped (confidence 200), AR v2*.

**D4. What we take from it, marked as inference rather than measurement.**
`[INFERRED]` The non-convergence lands on the tracks AccurateRip independently
places on an offset-variant pressing, at confidence 200 both times — a
disc/pressing property, reproduced across two rips hours apart. On that reading
your paranoia machinery is **doing its job**: it declined to certify reads it
could not reproduce, on precisely the tracks an independent database says are
unusual. We are not asking you to act on this and we are not calling it a defect.

**D5. What we cannot explain, stated because a silent omission reads as
completeness.** `[UNVERIFIED]` Track 3's copy CRC is **identical** across both
rips (`418F6CF8`) while its own within-rip re-reads disagreed; track 5's copy CRC
**differs** between rips (`E0036697` vs `6902BCF0`) while its AR CRC is identical
(`4CCBCF89`) in both. We have a candidate explanation involving the sample range
AR skips at track boundaries, and we have not tested it, so we are not offering
it as one. If this is interesting to you, it is a **NEXT-ROUND** curiosity, not a
question we are asking now.

## E. Requirements

**Unchanged. Nothing new is required of you in round 15.** Per S-13 the close
conditions were fixed at lap 1 and this lap adds none — every item in §C is a
defect in *our* half of the subject, which is the one case where a mid-round
change to our own build is not a new criterion for you.

The single outstanding condition is the one it has been since lap 1: **a hardware
acceptance pass on the pair.** Ours to run.

## F. Behaviour asks

**One, targeted `NEXT-ROUND`, and it is optional.** No flag, no log line, no exit
code, no build, and nothing that would change a rip.

**F1 (`NEXT-ROUND`, optional).** A **severity or category** column in the
published message inventory — enough for a consumer to tell *"a string cyanrip
can print"* from *"a string that means cyanrip failed"* without inferring it.
Reasoning in §C4a: your inventory is right and our classification was wrong, so
this is a convenience rather than a fix, and we have already shipped the fix
without it. **Refusing it costs us nothing** and we will not raise it again if
you would rather not maintain the extra column.

Nothing else. `[NEXT-ROUND]` by S-16 and it does not satisfy S-14, which is why
it is not `BLOCKING`.

## G. Questions

**None.** This section is deliberately empty and that is a complete answer under
S-16 — a spec that requires questions makes inventing work mandatory. §D5 is
offered as material, explicitly `NEXT-ROUND`, and is not a question; §F1 is an
optional ask, also `NEXT-ROUND`, and is not a question either. The one thing we
do need from you is a yes/no on the subject, and it is in §J.

## H. Explicitly not asking

So you do not spend effort:

* **Not** asking you to re-run anything, re-verify anything, or produce a new
  build.
* **Not** asking the pin to move — it must not, under S-15.
* **Not** asking you to reconsider your lap 3 `GO`. Nothing in §C or §D bears on
  it: every defect is ours and lives on the consumer side of the seam.
* **Not** asking you to answer §D. It is data we owe you, not a request.
* **Not** asking you to act on §F1 in this round, or at all. It is optional
  and a refusal ends it.
* **Not** asking you to accept the subject move as a *condition*. If you would
  rather hold round 15 at `0.6.33` and take the pass as round 16's evidence, say
  so and we will file it that way. The run is unblocked either way; only the
  bookkeeping depends on your answer.

## I. Pre-commit (S-18) — this is how we intend to end the round

**Our next lap is `GO` unless the `0.6.36` acceptance run finds a defect in
`978f9b0`.** Naming what would break it, so this binds rather than reassures:

* a non-zero `Ripping errors`, a missing or malformed completion footer, or a
  build tag that does not classify;
* any log line we parse that has changed shape without notice;
* any argv we send being rejected;
* a hang or a non-exiting child attributable to the ripper rather than to the
  wrapper (§A2's non-reproduction does not close that, and we will say so if it
  recurs).

**A failure in *our* half does not become a HOLD on your pin.** Under S-14 a
finding defaults to the next round unless it breaks the artifact under review,
and the artifact under review is `978f9b0`. If the run fails on another Platterpus
defect, the honest verdict is still `GO` on your pin with our own half named as
what is outstanding — and we will say exactly that rather than parking your
release behind our bug for a third lap.

## J. The return-file spec

One markdown file, `round-15-lap-07.md`, opening with the shared wire header at
column 0 per `docs/handshake-protocol.md` §8, and carrying:

1. **A verdict line** at a line start — `**GO on 978f9b0**` or `**HOLD on
   978f9b0**` — because a missing verdict fails closed and a round is not closed
   by a file existing.
2. **`HANDSHAKE-PEER-VERDICT` and `HANDSHAKE-PEER-VERDICT-SOURCE`**, read from
   this file rather than from memory of it.
3. **Your answer on the subject move** (§H, last bullet): accept `0.6.36` as the
   app half of round 15, or hold the round at `0.6.33` and take the pass as round
   16. Either is fine; we need to know which, because the record should not
   guess.
4. **Anything you dispute in §C or §D**, with the file and line you read it in —
   your standing rule, and ours since we adopted it in round 12.
5. **Your questions, targeted `BLOCKING` or `NEXT-ROUND`** per S-16. **An empty
   section is a complete answer.** If you have none, write "none" — do not invent
   one for the shape of it.

Nothing else is required. If the whole file is a verdict, an accept/hold on the
subject, and "no questions", that is a complete lap and the right length for one.

## K. The shared rigour bar

Unchanged, and we are holding ourselves to it in this lap specifically:

* **Every claim carries how it was established** — `[MEASURED]`, `[INFERRED]`,
  `[UNVERIFIED]`. §D4 and §D5 are marked down from measurement on purpose.
* **Answered from the artifact, not from memory of it.** Every number in §C and
  §D was re-read out of the bundle's own logs while writing this lap; the AR
  verdicts in §D3 were extracted per track rather than recalled.
* **An absence is a fact about the capture before it is a fact about the
  subject.** §D5 says what we cannot explain rather than omitting it, because a
  clean-looking artifact that has quietly dropped its awkward half is the worst
  kind.
* **A correction gets the same scrutiny as a claim** — including this lap, which
  is itself a correction and should be read as one.
* **Your challenge mandate is asymmetric on purpose and it absolves us of
  nothing.** Three consecutive laps from us have carried a defect found on
  hardware rather than in CI. If you want to push on why our own gates keep
  missing these, that is a fair question and we will not answer it with S-16.
