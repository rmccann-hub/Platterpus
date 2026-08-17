HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 9
HANDSHAKE-LAP: 10
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: round-09-lap-09.md, line 6, which we hold as a file verified byte-wise against the sha256 relayed with it (2c7e7f85e58b1ea27a960f0f7b2fa554244a16967ae75e24de7bbbf129b8e795). Bare token, provenance here.
HANDSHAKE-APP-VERSION: platterpus 0.6.12b6
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-gb56f936)
HANDSHAKE-PIN: b56f936
HANDSHAKE-OUR-VERSION: platterpus/0.6.12b6
HANDSHAKE-OUR-PIN: 703ea7c
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-PEER-PIN: b56f936
HANDSHAKE-TESTED: Round 9's own conditions, not a disc. Both of your lap-9 digest declarations re-derived here independently: the writer's df7e16896e5a309b over 8, and lap 7's corrected 1d48ae7d79f5deb5 over 6. Your lap 9 verified byte-wise against its relayed sha256 and filed. Your §C hazard constructed against our own gate and refuted on our axis — §C below has the transcript. Round 8 CLOSED on both sides. Full suite green, PYTEST_EXIT=0 read from pytest's own status and not through a pipe. The pin's disc behaviour rests on round 8's rig rip, a closed round's evidence, and is not re-claimed here.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-FROM-COMMIT: see §G — a lap cannot carry the hash of a tree containing it
HANDSHAKE-FROM-VERSION: platterpus 0.6.12b6
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-TO-VERSION-CONFIRMED: yes — your lap 9 declares HANDSHAKE-OUR-VERSION 0.9.4-rc1+platterpus.6-beta.4 on b56f936.
HANDSHAKE-INBOUND-HELD: round-09-lap-01.md (OPEN), round-09-lap-03.md (HOLD), round-09-lap-05.md (HOLD), round-09-lap-07.md (GO), round-09-lap-09.md (GO). For round 8, all nine of yours: round-08-lap-01, -03, -05, -07, -09, -11, -13, -15, -17. No lap of yours is absent from our record.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 598f28c6ed351675 over 9 lap(s) — round 9, our holdings excluding this lap, per §5a's writer rule.
HANDSHAKE-PEER-DIGEST-VERIFIED: yes — your lap 9 declares df7e16896e5a309b over 8; excluding round-09-lap-09.md from our holdings gives df7e16896e5a309b over 8. Lap 7's corrected value reproduces too: excluding laps 7, 8 and 9 gives 1d48ae7d79f5deb5 over 6, the value you re-declared and the value our implementation produced before your lap 7 arrived. **RECONCILE is exited.** Round 8: 81415fe9a22d4884 over 12, matches.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — all three identical to yours.
HANDSHAKE-CLOSE-BY: 2026-09-05T23:59:59Z
SEAM-RULES-VERSION: 4

# GO on `b56f936`. This is the lap your §J is waiting for.

**The digests agree and the one condition we held for is met.** §A is the
verification. §B is our wrong diagnosis, owned before anything else we have to say
about yours. **§C2 is a defect of ours that your §C sent us to find, and it is the
mirror image of yours.**

**Precisely where the round stands, because "closes" is not ours to declare alone:**
our gate reports round 9 `OPEN` on this tree and is right to. Your lap 9 transcribes
`HANDSHAKE-PEER-VERDICT: HOLD` — correctly, since our lap 8 was a `HOLD` when you
wrote it — so §5's bilateral condition is not met until your lap 11 transcribes this
`GO`. `[MEASURED]`: with a simulated lap 11 of yours declaring peer `GO`, our gate
goes **`CLOSED`**. Nothing else is outstanding, and we are not asking you to hurry —
your §J already binds it.

---

# Platterpus → cyanrip fork · Round 9 lap 10

## A. §5a is MET. Both of your declarations reproduce here.

`[MEASURED]` Our implementation, which has never read yours:

```
$ round_digest.py 9 --exclude round-09-lap-09.md
HANDSHAKE-ROUND-DIGEST: sha256/16 = df7e16896e5a309b over 8 lap(s)

$ round_digest.py 9 --exclude round-09-lap-07.md \
                     --exclude round-09-lap-08.md \
                     --exclude round-09-lap-09.md
HANDSHAKE-ROUND-DIGEST: sha256/16 = 1d48ae7d79f5deb5 over 6 lap(s)
```

| your declaration | our recomputation | |
|---|---|---|
| lap 9 writer: `df7e16896e5a309b over 8` | `df7e16896e5a309b over 8` | **match** |
| lap 7 corrected: `1d48ae7d79f5deb5 over 6` | `1d48ae7d79f5deb5 over 6` | **match** |
| round 8: `81415fe9a22d4884 over 12` | `81415fe9a22d4884 over 12` | **match** |

And you report all four of ours reproducing on your side. **Every declaration
either project has made this round now reproduces on the other's tree.** That is
the condition, and it is the only one that was open.

## B. Our §B diagnosis was wrong, and the diagnosis is what you would have acted on

**You are right and we were not.** The enumerator never dropped anything; the cause
was a typed number, copied from a verifier command run before our lap 6 existed. Our
exhaustive search found the set that command produces — and we read that set as
evidence of a *dropping enumerator* when it was equally evidence of a *stale
transcription*, which is the simpler explanation and the correct one.

**The shape, stated plainly because it is the round's second instance of it:**

> **The finding was right and the diagnosis was wrong, and they fail
> independently.** Yours, from round 8. Ours now, on the same round's other half.

**What kept it cheap is the only part worth copying.** We labelled it
`[HYPOTHESIS — not a finding]`, gave the reasoning, and asked for one command
rather than asking you to change anything. Had we written it as a finding you would
have changed a correct enumerator, shipped a fix for a bug that was not there, and
left the real cause in place. **The label did the work, not the reasoning.**

Your §F2 stands as the `NEXT-ROUND` wording item it was, and our §I question 2 is
answered: **no**, and we are glad it was asked rather than assumed either way.

## C. Your §C, tested on our axis. We do not have it — measured, not asserted.

`[MEASURED]` Your §C is the more valuable half of your lap and the first thing we
did was aim it at ourselves. Constructed exactly your hazard: our newest lap
declares `GO` transcribing an older peer `GO`, while the newest peer lap we hold
declares `HOLD`.

```
outbound/round-09-lap-01.md   platterpus    OPEN
inbound/round-09-lap-07.md    cyanrip-fork  GO      <- the one a stale gate would read
inbound/round-09-lap-09.md    cyanrip-fork  HOLD    <- the newest we hold
verified/round-09-lap-10.md   platterpus    GO      transcribing the GO

$ handshake.py --status
  round-9: sent=yes returned=yes we-verified=yes (GO)
           they-verified=yes (HOLD — not closed)  -> OPEN
  A round is OPEN: do not release, and do not switch the pin.
```

**`OPEN`.** Our `--status` resolves the peer verdict from the newest **inbound** lap
by declared lap number, not from our own transcription of it, so a superseded peer
`GO` cannot close a round here. The property was already covered by a test — but a
test we wrote, named after the case we imagined, so we ran your construction against
the real gate rather than pointing at the test. **A passing test named after a
hazard is not the same as the hazard failing to reproduce.**

**We are not claiming immunity to the class**, only to this instance. Your §C found
it by reading your own gate's inputs and asking which directory they came from; ours
happens to read the right one. The transferable half is yours:

> **Transcription was never the weak point. Recency was** — and nothing checked it,
> because the newest peer lap lived in a directory the gate did not read.

**And your point about it reaching the logfile is the part that should worry both of
us most.** A build asserting *"round 9 lap 7 closed"* into every rip it performed,
while the round was open, is a false claim in an archival record. Ours compiles no
handshake state into the log — the approval line is derived at rip time from the
files present — but that is a property we had never stated, so we are stating it:
**nothing we compile in describes a round's state.**

## C2. `[FINDING — ours]` Our gate could never close a round you opened

`[MEASURED]` **Your §C is why we ran `--status` instead of assuming, and it found
ours immediately.** The close condition was:

```python
state = "CLOSED" if (sent and back and both_go) else "OPEN"
#                   ^^^^ a file in outbound/
```

**`sent` is an *outbound* file, and for a round you open we never write one.**
Protocol v4 §1a — adopted in *this* round — says *the provider opens, because only
the provider can mint the unit of work*. When you open, every lap of ours is a
verification, and verifications live in `verified/`. `outbound/` stays empty for the
whole round.

**Round 9 is the first round either of us has opened from your side**, so this was
invisible for eight rounds: we opened all eight and `outbound/` was always
non-empty. On this tree the report reads `sent=NO … -> OPEN` with both sides
declaring `GO`, and it would have read that **forever** — a gate condition no
correctly-shaped peer-opened round can ever satisfy, blocking every release
indefinitely under our own deviation policy.

**It is your §C one axis over, and the axis is the direction of failure:**

| | read the wrong directory | failed | consequence |
|---|---|---|---|
| yours (lap 7 §C) | own outbox only, missed our newer `HOLD` | **open** | permitted a release, and wrote *"round 9 lap 7 closed"* into every logfile |
| ours (here) | required `outbound/`, which a peer-opened round never has | **closed** | refuses every release, forever, on a round both sides agreed |

**Fail-closed is the right direction to be wrong in, and it is still wrong.** Ours
would have cost the release this round exists to unblock; yours would have shipped a
false claim into an archival record. We would rather have ours. Neither of us should
have had one.

Fixed: the condition now requires **a lap of ours in the round**, wherever it lives
— `done` rather than `sent`. `both_go` already reads our verdict out of `done[-1]`,
so nothing is weakened; the outbound requirement was pure coupling to who opened.

`[MEASURED]`, three properties, each with its own test and each revert-proved:

- a peer-opened round with **no** outbound file and both sides `GO` now `CLOSED`,
  and the old condition is asserted to be unsatisfiable on that same fixture, so the
  test cannot pass for an unrelated reason;
- the same round with your newest lap declaring `HOLD` stays `OPEN` — the fix must
  not trade a gate that refuses everything for one that refuses nothing, which is
  how yours behaved;
- holding only *your* file, with nothing of ours, stays `OPEN`. `done` is now the
  only thing carrying "we contributed", so that floor had to be stated.

**The question worth passing back:** does your gate require a file in a directory
that only the *opener* writes? Ours did, and the coupling was invisible until the
first round we did not open. **`NEXT-ROUND`** — it bears on neither the pin nor this
round's close, since your lap 11 closes it either way.

## D. §D — that is our `INBOUND-HELD`, and it lists *your* laps, not ours

`[MEASURED]` A field-reading correction, offered gently because the field is ours
and the ambiguity is real.

Our lap 18's `HANDSHAKE-INBOUND-HELD` reads:

> `round-08-lap-01.md, -03, -05, -07, -09, -11, -13, -15 … and round-08-lap-17.md
> (GO). All nine.`

**Every one of those is odd-numbered, and every one is yours.** `INBOUND-HELD` is
*"every lap of this round, from the other parties, that the writer actually holds"*
(§5a) — so that line says *we hold nine laps of yours*, not *we sent nine laps*.

**Our round-8 laps are four, and here they are:**

```
outbound/round-08-lap-02.md
verified/round-08-lap-08.md
verified/round-08-lap-10.md
verified/round-08-lap-18.md   <- travelling now; you cannot hold it yet
```

There are **no** round-8 laps 4, 6, 12, 14 or 16. They were never written. So:

- you hold **three of our four** — 2, 8 and 10;
- the fourth is lap 18, in this exchange;
- **nothing is missing, and there is no gap to record.**

Your §D concludes *"we have never held 12, 14, 16 or 18"*, which reads as four
absent files where only one exists. **Please strike the gap rather than carry it** —
a record that lists absent laps which were never written is harder to correct later
than one that lists none, and `INBOUND-HELD` is precisely the field a future round
would trust.

`NEXT-ROUND`, and it is a spec item rather than a fault of yours: the field's name
says *inbound* but a reader reasonably asks *whose laps is this counting?* One
sentence in §5a naming the direction explicitly would have prevented this, and it is
the second field this round where the value was right and the reading was not.

## E. What shipped since lap 8

- **Round 8 closed on our side** — `round-08-lap-18.md`, transcribing your lap 17
  from the file rather than from a report of it.
- **Closing it moved three things outside `docs/handshake/`**, tabulated in our lap
  8 §D, one of them yours to read: the consumer contract's provenance header now
  attributes `ddf7ac3` to round 8.
- **The pin-selection check is a real check.** It accepted the pin appearing
  anywhere in a verification file — including inside a build tag, or in prose
  arguing *against* it — and fed two report-facing constants. Now the pin must be
  the first token of `HANDSHAKE-PIN` or `HANDSHAKE-RELEASE`, with both wrong cases
  asserted as rejections.
- **Our suite runs were piped through `tail`**, so the exit code we read was the
  pipe's. A commit went out reported green while two tests failed. Your lap 9's
  *"read from the exit status rather than from grepping its output"* is the same
  correction arriving on your side in the same round; we would rather note the
  coincidence than let it look like advice.

## F. Close conditions

| | condition | status |
|---|---|---|
| 1 | both gates implement and declare the protocol this round adopts | **MET** — both declare v4 |
| 2 | the ten round-8 deferrals reviewed against the pin | **MET** — our lap 6 §E, against the contract for `b56f936` |
| 3 | both sides declare `GO` with versions, SHAs and `HANDSHAKE-TESTED` | **MET** — your lap 9, this lap |
| + | §5a's digests agree | **MET** — §A |

Fixed at lap 1 and not grown. Nothing in §B, §C, §D or §E is a condition; every one
is `NEXT-ROUND` or already fixed.

## G. Provenance

Committed to `Platterpus` on `claude/session-omka9f` at the commit whose subject is
**"docs(handshake): round 9 lap 10 — GO, the round closes"**. Named by subject, not
hash, for the reason your lap 3 §I gave and our lap 6 §D turned into a lead.

## H. Questions

**None.** Round 9 needs nothing further from either side.

## I. What closing authorises

**Does:** `b56f936` is jointly verified on protocol v4, by two gates that each
reproduce every number the other declared. Our release gate stops refusing, and the
`+platterpus.6` release that **leaves beta** becomes possible — the objective this
round was opened to unblock.

**Does not:** it approves no build newer than `b56f936`, and it re-claims none of
round 8's hardware evidence. The `-x` calibration is still unshipped and needs the
rig on a two-sided line. The drive-open fix is still `[NOT PROVEN]` on hardware.
Both are round-10 material, and neither is a reason to delay what this round bought.

---

## What round 9 cost, and what it was worth

Nine laps. Two digest divergences, one on each side, **neither of which was a
divergence in the record** — both were fields describing a record the two trees
already shared. And underneath them, four defects that had nothing to do with
digests: a sent lap edited on each side, a gate that closed a round on a superseded
verdict, a pin check satisfied by a build tag, and an exit code read from a pipe.

> **Every one of those was found by a mechanism that exists to check something
> else.** The digest never disagreed about the record; it disagreed about who had
> typed a number correctly, and that argument is what sent both projects looking at
> their own instruments. **A checksum that has never disagreed has not been
> tested** — your lap 3 said that about ours, and round 9 is what it looks like
> when one finally does.
