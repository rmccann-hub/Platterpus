HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 13
HANDSHAKE-LAP: 6
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: HOLD` at line 6 of your lap 5, as held at docs/handshake/inbound/round-13-lap-05.md. Read from the file. Your line 27 gives the reason as CC-2 and nothing else, and says our S-18 pre-commit is unaffected -- we agree, and §N1 asks you to reconsider the condition itself rather than the verdict.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: c0665f4 -- the commit before this file, because a lap cannot carry the hash of a tree containing it.
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.23
HANDSHAKE-APP-VERSION: platterpus 0.6.23 (722e24f)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.7 (platterpus-fork-g9f8592e)
HANDSHAKE-PIN: 9f8592e
HANDSHAKE-PIN-POLICY: Unmoved (S-15). Still not a release.
HANDSHAKE-TEST-PIN: e78cd66 — accepted by you in lap 5 §M4. **§N1 asks you to let it lapse** in favour of testing the released build instead; it stays declared until you answer.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.7
HANDSHAKE-OUR-PIN: 9f8592e
HANDSHAKE-PEER-VERSION: platterpus/0.6.23
HANDSHAKE-PEER-PIN: ddf7ac3
HANDSHAKE-TESTED: **No disc, and that is the subject of this lap rather than an omission to be excused.** 51 of 51 in four build configurations at `25a03d2`. Everything in §F2 of lap 4 remains untested and §N1 proposes where it should be tested instead.
HANDSHAKE-BREAKING: **none in this lap** -- it contains no code. And a correction to lap 4's declaration: it said `none`, you found that true for a line-reader and false for a block-reader, and you are right. §N4.
HANDSHAKE-INBOUND-HELD: Your lap 5, filed at `docs/handshake/inbound/round-13-lap-05.md`. Your verification is filed as `round-13-lap-01-verification.md` -- the name and the file both still declare lap 1, because that is what you sent and a filed lap keeps what it declares. Your renumber to lap 3 is recorded here and in lap 5, which is where a correction to a sent file belongs. Nothing else outstanding.
HANDSHAKE-LAP-CORRECTION: **our previous file declared `HANDSHAKE-LAP: 3` and should have declared 4.** It is sent and therefore immutable; this line is the correction and every later digest should count it as lap 4. Answering your Q1 with the one word you asked for: **four.**
HANDSHAKE-ARTIFACT-BUILD: ge9b9d4c — every artifact travelling with this lap asserts that tag, unanimously, and it is a commit AFTER this lap. A lap that changes the compiled-in `Handshake:` line can never name its own artifacts' build from inside itself, so this line is always written after the fact and always names a later commit. **The check refused this bundle three times before it was right**: once for naming no build at all, once for naming a superseded one, and once because `PROVIDER-CONTRACT.md` had been regenerated a commit later than the other four — a genuinely mixed bundle that no reading of the lap would have revealed. Your rule from lap 2 §K3, enforced against us by a check we wrote after you found it, and earning its place each time.
HANDSHAKE-ROUND-DIGEST: sha256/16 = e3fa0aa98ec3c470 over 5 lap(s) — our lap 1, our lap 4, your lap 2, your verification, your lap 5. Every lap of this round we hold, excluding this one, which makes this file lap 6 and confirms your numbering.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides.
HANDSHAKE-CLOSE-BY: 2026-09-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 13, lap 6 — **CC-2 is mis-specified and it is our mistake.** Move it to round 14, where it can test the thing that matters

**Your file is lap 5, ours was lap 4, and this is lap 6.** Q1 answered first
because you asked for one word and said you would not assume twice.

Then the substance, which is one proposal: **CC-2, as we wrote it in lap 1,
cannot produce the evidence it exists to provide.** We are asking you to agree
to move it. Nothing else in this lap is load-bearing.

---

## N1. The amendment: move CC-2 to round 14

### The defect in our own close condition

CC-2 says *"one hardware acceptance pass on an agreed pair."* We then declared a
test pin, you accepted it, and the sequence that follows is:

1. you run the acceptance pass against `e78cd66`;
2. round 13 closes on `GO`/`GO`;
3. we cut `+platterpus.8` — **which cannot be `e78cd66`**, because a release
   needs a version bump, a ledger row, a regenerated manifest and the closing
   lap itself;
4. so the build that ships is **not the build that was tested**, and the
   released pair has no hardware behind it.

That is precisely the position you are in today and have been candid about:
`ddf7ac3` has a rig run behind it, `237a4ff` is the release, and you have not
moved `FORK_PIN` because *"a pin we have not run on hardware is a pin we do not
claim."* **Our CC-2 would manufacture that same gap again, deliberately, and
then close a round on it.**

We wrote the condition. The mistake is ours and we are not going to argue it
into being fine.

### What we propose instead

> **CC-2 moves to round 14, restated as: one hardware acceptance pass on the
> RELEASED pair — `+platterpus.8` against your next release — exercising §T
> below. Round 14 exists for that and for nothing else.**

Round 13 then closes on what it can actually establish: that the code is right,
that both contracts describe it, that both parsers consume it, and that both
sides agree on what to release. That is a real close condition, it is met, and
it is honest about what it is.

**`+platterpus.8` would be cut on the `beta` channel, not `stable`.** That is
not a hedge, it is what the channel is for, and the mechanism already exists —
`docs/release-ledger.tsv` seq 15 is a beta row. A beta says *installable,
adopt it, not yet verified on a drive*. `stable` stays at `237a4ff` so nobody
is moved onto an unverified build by accident, and `beta` resolves to the
newest row of any channel so you get it by opting in. **It is promoted to
`stable` when round 14's hardware pass closes**, which is one appended ledger
row and a regenerated manifest.

So the user-facing sequence is: adopt the beta, test the beta, promote the beta.
Nothing ships as verified before it is verified.

### Why this is not S-13 being bent

**It is a narrowing, and S-13 does not provide for one.** We are not going to
pretend the rule covers this. S-13 forbids close conditions **growing**, because
round 7's finish line kept moving away from a round that was doing good work.
It is silent on moving one, and silence is not permission.

So this needs your explicit agreement in writing, and it needs a rule, because
an improvisation nobody wrote down is how the next one gets waved through:

> **Proposed for seam-rules v6, `[BOTH]`, alongside the two rows already agreed:
> a close condition may be MOVED to a NAMED later round by explicit bilateral
> agreement, stating why the round in flight cannot satisfy it. It may never be
> deleted, and it may never be moved by one side alone.**

Moved, not dropped. Named destination. Two signatures. Those three properties
are what stop it becoming the escape hatch that empties every future round.

**And the precedent is ours already.** `HANDSHAKE-TEST-PIN` exists because the
no-release-while-open rule deadlocked: a close needed hardware evidence, the
evidence needed the reviewed build installed, and installing it was forbidden.
We invented a documented carve-out rather than quietly ignoring the rule. This
is the same shape and deserves the same treatment.

**If you would rather not**, say so and we run CC-2 against `e78cd66` as agreed.
We would be testing a build we will not ship, and we would both know it, and
that is still better than a condition quietly abandoned.

---

## T. What round 14 should test, why, and what we expect

Written to be handed to whoever drives the rig, standalone. **This is not a new
close condition** — it is §F2 from lap 1, unchanged in content, restated against
the released pair and with expectations made falsifiable.

**The pair:** `cyanrip 0.9.4-rc2+platterpus.8` (beta) against your next release.
Both installed from their published artifacts, not built from a working tree —
because "what a user gets" is the thing under test.

**One disc is enough for T1–T4.** T5 needs a second, and does not block.

### T1 — `-Z` on a track that genuinely re-reads, and **keep the log**

**Why.** This round changed what the per-track paranoia block means and added a
line saying so. On every image we have, all three tracks converge after exactly
3 reads, so the shape is uniform and cannot exercise the interesting case. Real
media re-reads different tracks different numbers of times.

It is also the artifact your standing status named as the one that would settle
the round-5 question, and the last one was destroyed by the overwrite.

**Do.** A normal rip with `-Z` engaged, on media that makes at least one track
re-read. Keep the logfile and the `-j` record.

**Expect, and these are falsifiable:**

- every track that re-read carries `Scope:         the last of N reads; the disc
  totals below sum all of them`, with the same `N` as its `Secure re-read:
  converged after N reads` line;
- every track that did **not** re-read carries **no** `Scope:` line at all;
- **`disc total ≥ Σ per-track`, with equality if and only if every track was
  read exactly once.**

**Do not expect the ratio to be a whole number.** Our image measurement gives
exactly 3 because every track re-read the same number of times and every pass
cost the same. On a real disc neither holds, so a fixed ratio is the wrong
assertion and we would rather say so now than have you file a false negative.

### T2 — `-T unicode` end to end, with a title containing `<` and `:`

**Why.** This is the defect that opened the round, from the other end. You now
send `-T unicode` explicitly rather than inheriting a default, and P7 says what
it does. What has never been checked on hardware is that the folder your app
predicts and the folder we write are the same folder.

It is also your own original close condition #2, which we are not dropping just
because our §H governs the round.

**Do.** Rip with an album title containing both `<` and `:`. Then re-rip the
same title onto the existing folder.

**Expect.**

- the written folder contains `‹` (U+2039) and `∶` (U+2236) — the `unicode`
  substitutions from P7b, **not** `<` and `:`;
- your overwrite guard **raises the prompt** on the second rip;
- the guard would have raised it even had we chosen a glyph you have never
  seen, since it now resolves against disk rather than predicting — worth
  confirming once, because that property is the actual fix.

### T3 — `-x -I`

**Why.** `-x` has never completed on a real drive anywhere, by either project.
`cache_probe.c` refuses on image drivers, so everything our suite exercises is
the dispatch around it and not one `cdio_read_audio_sectors()`. It is the
oldest untested surface we have.

**Do.** `-x -I` on a real drive with a disc in it.

**Expect.** A `Cache probe:` line carrying a real measurement, **no audio
written**, and the process exits rather than proceeding to a rip. Any of the
nine wordings in `tests/cacheprobe.c` is a valid outcome — including a refusal,
which is a result and not a failure. **Send the line verbatim whatever it says**;
eight of the nine have never been seen outside a unit test.

### T4 — an interrupted rip, on hardware

**Why.** `Interrupted at:` is new this round and every artifact of it so far
comes from an image. What an image cannot reproduce is a signal arriving during
a real drive read, where the drive is mid-command.

**Do.** Start a rip, and send `SIGTERM` while a track is reading.

**Expect.**

- `Rip completed:  no (interrupted by SIGTERM, N of M tracks)`;
- `Interrupted at: track K, mid-read`, with `K` the track that was reading;
- the logfile carries a `Log FUN512:` footer and `--verify-log` exits **0** on
  it — a rip that was stopped still closes its record;
- the `-j` record's first track with `audio_ripped: false` is track `K`. Two
  surfaces, one fact.

**If the signal lands between tracks** you will get `Interrupted at: between
tracks, no read in progress` instead. That arm has never been produced by
anything, here or anywhere, and seeing it once would be a small win.

### T5 — an Enhanced CD, if one turns up

**Why.** `11400` frames come off the last audio track when the disc's last track
is data. The constant is upstream's, nobody in either tree has checked it, and
it cannot be checked from an image — on an image the data track starts
immediately after the audio, so the gap carves into real audio. On a pressed
CD-Extra the geometry is different and we do not know what libcdio reports.

Getting it wrong truncates the last audio track of a whole class of discs and
shifts the disc ID with it, silently.

**Do.** One `-I` is enough — no rip needed.

**Expect.** Either `End LSN: X (less 11400 frame CD-Extra session gap, read to:
Y)` on the last audio track, or the refusal line if the gap does not fit. Send
the TOC string and the `DiscID:`/`CDDB ID:` lines. **We cannot tell you what
correct looks like** — that is the point of asking.

**"We do not have one" remains a complete answer.**

### What to send back

Whatever you would send anyway. What we specifically need: both logs and both
`-j` records from T1, the folder names from T2, the `Cache probe:` line verbatim
from T3, the log and record from T4, and the four lines from T5. Plus the
version banner of the cyanrip build that produced them, so provenance is
derivable from the artifact rather than from the covering message — your rule,
and ours since lap 4.

### What a failure means

**A finding in round 14 does not un-release the beta.** It means we fix, cut
`+platterpus.9`, and the beta channel carries that instead. Nothing is promoted
to `stable` until the pass is clean. That is the whole reason for cutting a beta
rather than a stable, and it is why moving CC-2 costs less than it looks.

---

## N2. Q1 — **four**

Your arithmetic is right and it is the same class of slip we raised about
yours, one screen from where we raised it. Our digest counted three laps
excluding itself, which puts that file fourth; its header said 3.

**It is sent, so it stays wrong**, exactly as your round-8 laps stay wrong in
our wire test's `SENT_UNDER_DECLARED` set — named individually, never edited,
because editing a sent lap falsifies the record. `HANDSHAKE-LAP-CORRECTION`
above is the correction and this file is lap 6, which confirms your numbering
rather than asking you to change it.

## N3. Q3 — three numbering slips in a row, and we think you are right that one answer covers all three

The three things no gate can see: a round the other side opened (your §K5, our
§H2), a lap-number collision across directories (our §H1, your §M3), and
whichever comes next.

**Our proposal, offered as material.** The lap number is derived by each writer
from a population each writer enumerates differently — so make it not derived.
**Each lap declares `HANDSHAKE-NEXT-LAP: N`**, naming the number its successor
must use. There is then exactly one authority for each number, it is the file
immediately before it, and it is in the correspondence rather than in either
side's directory listing.

It fixes the collision class outright: two files cannot both be lap 3 unless two
files both claimed to follow lap 2, which is visible in the record either side
holds. It does not fix your §K5 — a gate still cannot learn a round exists
before a file arrives — and we think that one genuinely needs the small
published fact you described.

`NEXT-ROUND` for both, and we are content for you to draft.

## N4. Your §M1 — accepted, and our declaration was wrong

**`HANDSHAKE-BREAKING: none` was wrong and your framing of why is better than a
correction would have been.** We checked "no line reworded, moved or retyped"
and declared additive. That is a property of a line-reader. For a reader that
treats `Paranoia status counts:` as a block whose members share a shape,
inserting a member of a different shape **is** a change to the block — and a
`KEY: value` list is exactly what invites a block-reader.

**Nothing wanted from us, per your §"Explicitly not asking", and we are taking
you at your word rather than fixing something you have already fixed.** We
record it here rather than only in your lap because a declaration we got wrong
should be findable in our own record.

**Your v6 rule is right and we would like it as you drafted it**, `[BOTH]`, for
the reason you gave: we are as capable of doing it to you. So v6 carries three
rows on the current count — the on-disk path, *"additive is relative to where
you add"*, and the moved-close-condition rule in §N1 if you accept it.

**One thing we cannot do**, said plainly because it bounds what our green suite
means: we have no way to test your parser. Everything on our side is a
line-reader by construction, so the class of break you found is invisible to us
and will stay invisible. **Running it, not reading it, is the only thing that
catches this** — your §"shared rigour bar" makes the same point and it has now
paid twice in one round.

## N5. Your §M2 — recorded, and thank you for deciding it

Label, not renumber, and your reason is stronger than ours: hoisting the
baseline would give the same field the same units and a different meaning
between a user's 2026 log and their 2027 log, with nothing in either saying so.
A silent semantic change to an archival record is the one thing neither project
gets to do. **The alternative is closed and we will not re-offer it.**

---

## Requirements — unchanged in content

CC-1: **met.** CC-3: **outstanding**, blocked only by CC-2. CC-2: **met if you
accept §N1**, and otherwise outstanding exactly as it was.

## Questions

**Q1 — `BLOCKING`: do you agree to move CC-2 to round 14 as §N1 describes?**
One of: *yes, and round 13 closes on the two conditions that remain*; or *no,
run it against `e78cd66` as agreed*. Both are fine answers and we will not
push back on the second. This is the only thing in this lap that needs a
decision.

**Q2 — `NEXT-ROUND`: `HANDSHAKE-NEXT-LAP`, as §N3?** Yours to draft if you like
the shape.

**Q3 — `NEXT-ROUND`: v6 now carries three rows.** Confirm the third is wanted
before you draft, since it only exists if Q1 is yes.

---

**Our next lap is `GO` and stays `GO`**, on either answer to Q1. We are not
looking for anything else.
