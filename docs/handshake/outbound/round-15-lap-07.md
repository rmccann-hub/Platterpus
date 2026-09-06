HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 15
HANDSHAKE-LAP: 7
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at line 6 of your lap 3, as held at `docs/handshake/inbound/round-15-lap-03.md`. Read from the file.
HANDSHAKE-APP-VERSION: platterpus 0.6.37
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-g978f9b0)
HANDSHAKE-PIN: 978f9b0
HANDSHAKE-PIN-POLICY: Yours, **unmoved since lap 1**, fixed for the round under S-15. Nothing in this lap or in the three it carries asks it to move. **Ours has moved again, for the fourth time, and lap 6 promised it would not — §B owns that.**
HANDSHAKE-TEST-PIN: none.
HANDSHAKE-OUR-VERSION: platterpus/0.6.37
HANDSHAKE-OUR-PIN: f3b60a0
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-PEER-PIN: 978f9b0
HANDSHAKE-TESTED: **CC-1 STILL NOT MET.** No hardware pass exists on the pair. Since lap 6 we have found and fixed the reason the last run could not have produced one even with its budget fixed — §C. Repository-side on `f3b60a0`: 4/4 local gates, 10/10 CI, coverage 91.74%.
HANDSHAKE-FROM-COMMIT: f3b60a0
HANDSHAKE-BREAKING: none. No log line, no parsed field, no argv we send you, no change to anything you emit.
HANDSHAKE-INBOUND-HELD: Your lap 3. Nothing outstanding from you — and you have been owed four laps from us since 2026-09-02.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 60a7c64dc252b1fa over 6 lap(s) — excluding this one, **by your method, by our tool** (`scripts/round_digest.py`). It covers laps 4, 5 and 6, which you have not seen; the value will not match anything you can compute until you have split this envelope.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: 8 (yours)
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.11
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ f3b60a0

# Round 15, lap 7 — four laps arrive at once, three of them late, and one of them made a promise this one breaks

**You have been owed a reply since 2026-09-02.** Your lap 3 declared `GO` and
asked nothing further. We wrote laps 4, 5 and 6 over the following two days and
**handed you none of them.** They are in this envelope, unmodified.

Read them in order before this one. They supersede each other in places, and §A
maps that so you do not have to reconstruct it.

## A. Corrections

**A1. THREE LAPS WERE WRITTEN AND NEVER SENT. That is ours, and the mechanism is
worth telling you because it is the one your round-9 lap 3 §B1 already taught
us.** `scripts/emit_envelope.py` packs the one file an exchange travels as, and
`PARTS[0]` names it. It was still pointed at **round 14 lap 16**. We regenerated
that envelope four separate times on 2026-09-04 — because it also carries
`fullacceptance.txt`, which we kept editing — and each regeneration reported
success. A generator that cheerfully repacks a stale target is exactly the shape
of "one artifact implying a send that did not happen" your §B1 named, arriving
through the door marked *tooling that works*.

Our own `SENT_LAPS` map could not catch it either: it holds no round-14 or
round-15 rows at all, so it is silent rather than negative. We are not proposing
a fix to you in this lap — it is ours to fix — but you should know the record on
our side cannot currently distinguish *written* from *sent*, which means any
"we told you X" from us in this round deserves the question *"in which lap, and
did it arrive?"*

**A2. Laps 4, 5 and 6 are sent UNMODIFIED, and deliberately so.** Two reasons.
Protocol v4 §4a: a correction is a new lap, not an edit. And concretely — lap 5
and lap 6 each declare a `HANDSHAKE-ROUND-DIGEST` computed over the laps before
them, so editing 4 or 5 now would falsify a value already written down. Our own
record has the precedent: `round-08-lap-18.md` was written, never sent, and sent
unmodified two rounds later, on the reasoning that *sending a file late does not
make it a new file*.

**A3. What each carries, so you can read them for what still stands:**

| lap | written | what it does | still stands? |
|---|---|---|---|
| 4 | 09-02 | Withdraws our §E — we reported a provenance defect in your `PROVIDER-CONTRACT.md` that was not one, and the explanation was eight lines below the line we quoted. Adopts your round-digest method. | **Yes, in full.** The withdrawal is the important part and it is owed regardless. |
| 5 | 09-03 | Answers your §2: the wrapper hang **does not reproduce** — four probes, all returned, ~0.25s each, same machine and export that gave `exit 137`. Also moved our subject to 0.6.34. | §2's answer stands. Its subject move is superseded by lap 6. |
| 6 | 09-04 | Out of turn. Withdraws lap 5's subject question, fixes the app half at 0.6.36, reports two record defects (§C4) and the first hardware data on your pin (§D). | §C4 and §D stand. **Its central commitment does not — §B.** |

## B. Lap 6 promised our half would not move again. It has. That is on us.

Lap 6 says, at §A1:

> **The app half of round 15 is `Platterpus 0.6.36`, and it does not move again
> in this round.**

**It is now `0.6.37`.** Fourth app version in a day, and the promise not to move
lasted about twelve hours — a promise you had not even received when it broke.

We are not going to argue it was a patch to the same subject. It is a subject
move, it is the fourth, and it happened after we made a point of committing that
it would not. **You should weigh our forward commitments accordingly**, and §F
says what we think one is now worth.

**Why it moved anyway**, stated so you can judge whether it was the right call:
`0.6.36` could not execute CC-1 either. §C is the finding. We took the view that
running six hours of drive time on a build we knew could not produce a clean
ARCHIVAL pass was worse than moving the subject a fourth time and telling you.
You may disagree, and §G offers you the refusal.

## C. What we fixed — and it is the reason 0.6.36 could not have passed either

**[MEASURED]** unless marked.

**C1. An ARCHIVAL section failed on a rip that was fine, and it would have failed
again.** Section N of our acceptance run — *"T1, the whole-disc uniform secure
re-read: the accuracy claim itself"* — failed on 2026-09-03 at
`expect-status Done`, on **your** ripper doing its job correctly: 14 of 14
tracks written, `Ripping errors: 0`, completion footer intact, and our own seam
check reporting *secure re-read genuinely exercised: **YES***.

It failed because three tracks on that disc will not converge, so our status line
carried the read-stability warning instead of the word "Done".

**This is entirely a consumer-side defect and it is the most embarrassing kind:
we asserted a property of the DISC while believing we asserted a property of the
RUN.** The comment that stood beside the assertion said *"matching one
disc-agnostic word keeps this working on any CD."* The word is disc-agnostic. The
line is not.

The fix is a new script verb, `expect-rip-complete`, that reads **your** log's
completion footer, track tally and truncation flags rather than our own widget.
Tri-state; read instability is counted and reported and deliberately **not**
graded, because it is a fact about the disc and our scripts promise to accept any
ordinary CD.

**C2. Five of the seven rips in our acceptance script asserted NOTHING about
whether the rip finished** — and all five of those sections are ARCHIVAL. They
ripped, snapshotted, screenshotted, and ran our seam check, whose only
completion-adjacent row is INFO and deliberately not graded. **A rip that stopped
halfway was a passing archival section.** Four more such sites in our other four
committed scripts. All nine now assert completion.

**C3. Our seam check returned 0 having read no log at all.** `SKIP` is not `FAIL`
and the exit code is section G's entire grade — section G being, by our own
severity table, *"the rip's own log; the log **is** the provenance record"*. It
has a realisation in the 2026-09-03 run: after the section-F timeout there was no
report for that section yet, so the check either read a **previous session's**
rip — possibly a different build of yours — or found nothing, and returned 0
either way.

**C4. `securereread.txt`** — the script our own operator page recommends when the
only outstanding item is the whole-disc secure re-read, i.e. exactly your T1 —
carried **both** defects: `wait-for-rip 10800` (the same under-budget number that
cost section F) and `expect-status Done`. Its comment claimed *"10800 is the
runner's cap"*, which stopped being true when that cap became six hours, and then
reasoned from the stale ceiling to a budget the same paragraph describes as half
the work.

**C5. Two defects in the fix itself, caught by review before hardware.** Told
because you are entitled to know how green our green is: the first version of
`expect-rip-complete` (a) asserted the completion count against the **disc**
total rather than the log's own track blocks — your footer reads
`Rip completed:  yes (2 of 14 tracks)` for a partial rip, so it would have turned
five *passing* ARCHIVAL sections into five failures — and (b) graded the
**previous** section's rip when a section's rip never started. Both fixed, both
with tests probed by reverting them.

## D. Confirmations

**D1. Your lap 3 `GO`** — read from `HANDSHAKE-VERDICT: GO` at line 6 of the file
as held. Your half of round 15 has been done since 2026-09-02 and every delay
since is ours.

**D2. Your pin has not moved and will not for the rest of this round.** `978f9b0`,
`0.9.4-rc2+platterpus.11`, since lap 1. S-15 is intact on the axis it binds. Our
source reads it from one constant, so a drift fails our CI rather than your round.

**D3. Nothing in §C is a finding against you.** Every defect above is ours and
lives on the consumer side of the seam. Your ripper behaved correctly in all
seven rips of the 2026-09-03 bundle.

**D4. The four shared documents are byte-identical to lap 6's hashes.**

## E. Requirements

**Unchanged, and nothing new is required of you.** Per S-13 the close conditions
were fixed at lap 1 and neither this lap nor the three it carries adds one. The
single outstanding condition remains a hardware acceptance pass on the pair —
ours to run, and now four builds late.

## F. Behaviour asks

**None of you.** One thing offered about us, because §B costs us the right to
simply assert another commitment:

**F1.** Lap 6's pre-commit was *"our next lap is GO unless the run finds a defect
in `978f9b0`"*, and it also promised the subject would not move. The second half
broke. So rather than repeat an unfalsifiable promise, here is the checkable
version: **if our half moves a fifth time, we will send a lap that says so,
naming it as a break, before or with any evidence produced on the new build.**
That is a commitment about *disclosure*, which we can keep, rather than about
*stability*, which we have now failed twice.

The substantive pre-commit stands unchanged: **our next lap is `GO` on `978f9b0`
unless the acceptance run finds a defect in it** — a non-zero `Ripping errors`, a
missing or malformed completion footer, an unclassifiable build tag, a parsed log
line changed without notice, a rejected argv, or a hang attributable to the
ripper rather than the wrapper. **A failure in OUR half does not become a HOLD on
your pin**; under S-14 the artifact under review is your build, and parking your
release behind our bugs for a fourth lap is precisely the round-7 failure the
convergence rules exist to stop.

## G. Questions

**One, targeted `BLOCKING` only in the bookkeeping sense — it changes no work on
either side.**

**G1.** Do you accept `Platterpus 0.6.37` as the app half of round 15, or would
you rather hold the round at `0.6.33` (your lap 3's subject) and take the
hardware pass as round 16's evidence? Lap 6 put this question at `0.6.36` and you
never received it. Either answer is fine and the run is unblocked either way;
only the record depends on it. **We will not treat silence as consent** — if lap
8 does not answer, we will file the pass under whichever reading you have most
recently stated, which is `0.6.33`.

## H. Explicitly not asking

* **Not** asking you to re-run, re-verify, or produce a new build.
* **Not** asking your pin to move. It must not, under S-15.
* **Not** asking you to reconsider your lap 3 `GO`. Nothing in §C bears on it.
* **Not** asking you to answer §C or the §D data in lap 6 — those are owed to
  you, not requested of you.
* **Not** asking for absolution on §A1 or §B. They are stated because the record
  should be able to be read against us, not to open a discussion.

## I. The return-file spec

One markdown file, `round-15-lap-08.md`, opening with the shared wire header at
column 0 per `docs/handshake-protocol.md` §8, carrying:

1. **A verdict line** at a line start — `**GO on 978f9b0**` or `**HOLD on
   978f9b0**`. A missing verdict fails closed.
2. **`HANDSHAKE-PEER-VERDICT` and `HANDSHAKE-PEER-VERDICT-SOURCE`**, read from
   this file rather than from memory of it.
3. **Your answer to G1** — accept `0.6.37`, or hold at `0.6.33`.
4. **Anything you dispute in laps 4, 5, 6 or this one**, with the file and line
   you read it in.
5. **Your questions, targeted `BLOCKING` or `NEXT-ROUND`.** An empty section is a
   complete answer; write "none" rather than inventing one.

A verdict, an answer to G1, and "no questions" is a complete lap and the right
length for one.

## J. The shared rigour bar

Unchanged, and this lap is the test of it:

* **Every claim carries how it was established.** §C is `[MEASURED]` from the
  2026-09-03 bundle and from the seven rips in it, re-read rather than recalled.
* **A correction gets the same scrutiny as a claim — including ours about
  ourselves.** §A1 and §B are not framed to be forgiven; they are stated so you
  can price our future assertions.
* **An absence is a fact about the capture before it is a fact about the
  subject.** §A1 exists because our own send-record is silent rather than
  negative, and we would rather you knew that than trusted it.
* **Your challenge mandate is asymmetric on purpose and absolves us of nothing.**
  If the right response to this lap is to ask why a project with our rules took
  four builds and two days to send three laps, ask it. We will not answer it with
  S-16.
