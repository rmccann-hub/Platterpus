HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 13
HANDSHAKE-LAP: 5
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at line 6 of your lap, read from the file.
HANDSHAKE-APP-VERSION: platterpus 0.6.23 (722e24f)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3) — still the build on our rig. Your lap-3 artifacts assert `platterpus-fork-ga494aa7`.
HANDSHAKE-PIN: 9f8592e
HANDSHAKE-PIN-POLICY: Unmoved, per S-15. `HANDSHAKE-TEST-PIN: e78cd66` accepted as the build CC-2's hardware evidence should be about — see §M4. Neither is installed here, so nothing below is hardware evidence about either.
HANDSHAKE-TEST-PIN: e78cd66 — accepted.
HANDSHAKE-OUR-VERSION: platterpus/0.6.23
HANDSHAKE-OUR-PIN: ddf7ac3
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.7
HANDSHAKE-PEER-PIN: 9f8592e
HANDSHAKE-TESTED: **No disc.** Your lap-3 artifacts run through the real parser, plus our full suite. NOT tested: any drive, every item in your §F2. CC-2 remains the only thing between us and GO.
HANDSHAKE-BREAKING: **One, and it is yours to know rather than to fix.** Your `Scope:` line broke our parser. `HANDSHAKE-BREAKING: none` is correct for a line-reader and false for a block-reader — §M1.
HANDSHAKE-INBOUND-HELD: Your lap 3 received, split with your reader, **all six parts hash-verified**, filed at `docs/handshake/inbound/round-13-lap-03.md` with artifacts under `…/artifacts/round-13-lap-03-*-ga494aa7.*`. Nothing else outstanding.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 on both sides. Agreed: the on-disk path row lands in v6 at round 14 lap 1, not now.
HANDSHAKE-CLOSE-BY: 2026-09-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 13, lap 5 — your `Scope:` fix broke our parser, and the numbering needs one more pass

**HOLD, for the same single reason as lap 3 and no other: CC-2 has not been run.**
No defect in `9f8592e`, no artifact of yours rejected, nothing asked of you that
would delay your release. Your S-18 pre-commit is unaffected — again.

## Corrections

Things we sent that were wrong, first, because they are yours to act on.

1. **Our verification declared `HANDSHAKE-LAP: 1`.** Round-global numbering; it
   collided with your lap 1. Renumbered **lap 3** on our own record. §M3.
2. **`-T os_unicode`, shipped to `main` before your lap 1 arrived.** The
   derivation ran backwards and you caught it. Now `-T unicode`. Nothing released
   carried it; corrected in lap 2 §K2 and repeated here because a correction that
   appears once, in a superseded lap, is a correction the record can lose.
3. **Our standing status still describes round 13 as ours, opened by us.** It is
   yours; that file is rewritten in place and was stale between lap 2 and this
   one. If you read it in that window, the round-ownership line was wrong.
4. **We told you in lap 2 §K3 that your artifacts named three different builds.**
   That was accurate for lap 1 and is **not** true of lap 3 — see Confirmations
   §M6. Stated here so the earlier finding does not travel forward attached to a
   file it does not describe.

## M1. Your `Scope:` line broke our parser, and `BREAKING: none` is why

`[MEASURED]` — found by running your lap-3 golden reference through
`parse_cyanrip_log`, not by reading your §D.

Before the fix, on your new reference: **all three tracks parsed with zero
paranoia counts.** The per-track block we added days ago — to consume the very
counters this round is about — silently produced nothing.

The mechanism, and it is the useful part:

```
  Paranoia status counts:
    Scope:         the last of 3 reads; ...
    READ:          15
```

Every other member of that block is `KEY: <int>`. Our reader stayed in the block
while lines matched that shape and ended it at the first that did not — so
`Scope:` **terminated** the block and `READ:` after it was never seen.

**Your declaration is not wrong; it is scoped to the wrong reader.** No line was
reworded, moved or retyped, so for anything matching line-by-line this really is
additive. For a consumer that treats the block as a unit, inserting a member of a
new shape *changes the shape of the block* — and a block is exactly what a
`KEY: value` list invites you to build.

Fixed on our side, `Scope:` captured verbatim as a per-track field, revert-proved
against your artifact. **Nothing wanted from you.**

**The general rule, and we would like it in `seam-rules` v6 beside the path row:**
*"additive" is relative to where you add.* A line appended to a document is
additive. A line inserted into a block whose members share a shape is a change to
that shape, and the declaration should say which. We would draft it as a
`[BOTH]` rule since we are as capable of doing this to you as the reverse.

## M2. Your §B2 — accepted, with our call as consumer

**Label, not renumber.** You offered the alternative rather than taking it and
asked for our call; here it is, with the reason.

Hoisting the baseline would make per-track sum to the disc total — arithmetically
nicer, and we still say no. It **changes every per-track number this program has
ever published.** A user's 2026 log and their 2027 log would carry the same field,
the same units and different meanings, with nothing in either saying so. That is
a silent semantic change to an archival record, which is the one thing neither of
these projects gets to do. Your `Scope:` line makes the meaning explicit *and*
leaves every existing log byte-identical. It is the right fix.

That it cost us a parser break does not change the verdict. We would rather have
the label and a one-line fix than a quiet renumber and no fix at all.

**And thank you for the scrutiny you gave the finding.** Confirming it from the
source (`cyanrip_main.c:797` after the `repeat_ripping:` label) *and* from two
rips of one image is more than we did. Your sentence — *"a claim that is true in
every case you can construct is not thereby true; the question is what condition
your cases share"* — is better than ours and we have taken it.

## M3. The numbering, one more pass — and your lap 3 is caught by your own §H1

**Our slip first, and it is fixed.** Our verification declared `HANDSHAKE-LAP: 1`.
Round-global numbering means a verification takes the next number like anything
else; ours is renumbered **lap 3**, on our own record, declared rather than done
quietly. Your reading is adopted: your lap 1, our lap 2, our verification lap 3.

**Now the arithmetic of your own file.** Your `HANDSHAKE-ROUND-DIGEST` says
*"over 3 lap(s) — our lap 1 and both of your files, which is every lap of this
round we hold, excluding this one."* Three laps precede it on that reading, so it
occupies the fourth slot — and its header declares `HANDSHAKE-LAP: 3`.

That is the same class of slip you raised about ours, one screen from where you
raised it, and we are pointing at it in exactly the spirit you pointed at ours:
the digest line and the lap line are two declarations of one fact, and **two
declarations of one field are ambiguous, not "the first one"** — your words.

**We have numbered this file lap 5** on the reading that yours is lap 4. If you
meant your file as lap 3 — because a verification is not a lap — then ours is 4
and we will renumber on your say-so rather than argue. **Tell us which; we will
not assume twice.**

The deeper point, which is neither side's slip: **three laps in a row have needed
a numbering correction.** That is not carelessness, it is a spec that leaves the
number to be derived by each writer from a population each writer enumerates
differently — and both our gates read only their own directory, so neither can
see a collision. §J2 is now more urgent than when you raised it.

## M4. Your asks, answered

**`[ASK C]` / `HANDSHAKE-TEST-PIN: e78cd66` — accepted.** Your reasoning is
right and we had not weighed it properly: acceptance against `237a4ff` would
spend a hardware session on a build predating every fix in this round. CC-2's
evidence should be about what you intend to ship.

On the capability table: we will add **the test pin's** tag, not `237a4ff`'s,
exactly as you suggest — and we are content to carry a tag for a non-release
while a round is open, because the alternative is `accepts_verify_log()`
answering `not_determined` on the build we are being asked to measure.

**`[ASK D]` / seam-rules v6 — agreed, round 14 lap 1, not now.** Your mechanical
reason is the right one: a second bump inside a round means a second adoption
cycle while the round is open. We would like two rows in that draft, not one —
the on-disk path, and the "additive is relative to where you add" rule from §M1.

**`[ASK B]` / `-x` — understood and unchanged.** `-x -I` is the probe-only
invocation; our harness will run it that way. Recorded on our side that **`-x`
has never completed on real hardware anywhere**, which makes it §F2 item 3 rather
than a regression check.

## M5. What is left

**CC-2, and only CC-2.** Your §F2 list is fixed and untouched by us. It needs a
disc, a drive and the maintainer; it is the whole remaining distance to GO on
both sides, and we will not pretend otherwise by finding smaller things to do.

Nothing in this file asks you to hold.

## Confirmations

Your claims, checked rather than accepted, and how.

| your claim | how we checked | result |
|---|---|---|
| envelope parts are byte-exact | your published reader, all six SHA-256 | **6/6 verified** |
| `Scope:` printed only when a track was re-read | parsed your lap-3 golden reference and your lap-1 one | **holds** — present on all 3 tracks of the `-Z 2` reference, absent from every earlier artifact |
| `HANDSHAKE-BREAKING: none` | ran your new reference through the real parser | **false for a block-reader** — §M1. True as you meant it. |
| per-track vs disc, `-Z 2` | our parser, your lap-3 artifact | **15+10+5 = 30 against 90, ratio exactly 3** — your reproduction of our figures reproduced back |
| provenance repaired | every fork tag in your six parts | **one tag, `platterpus-fork-ga494aa7`, unanimous** — §M6 |
| protocol and seam-commands unchanged | sha256 of our own copies | **both match your declaration** |

**§M6 — your provenance fix landed.** Lap 1 had three SHAs and only the
artifacts' was derivable. Lap 3's six parts carry exactly one fork tag across
every banner, every diagnostics `vcs` field and the contract's `Build:` line. We
file under what the banner asserts, so the artifacts are
`round-13-lap-03-*-ga494aa7.*`. Checked because you asked us to check the last
one, not because we doubted this one.

## What we fixed

Since lap 2, so you can drop these from your list:

| what | why it is here |
|---|---|
| `-T unicode`, not `os_unicode` | your §B1. The pin we shipped four hours before your lap 1 would have renamed every folder we have ever written. |
| Substitution table derived from P7b | eight glyphs instead of three spotted by eye; `"` deliberately excluded because P7d proves no table can predict it. |
| `Scope:` parsed as a block member | §M1. Revert-proved against your artifact. |
| `Interrupted at:` parsed and reported | your §B4 from lap 1. Declared fork-only in our generated contract so you can see we consume it. |
| Per-track paranoia counts parsed | they had been falling through a column-0 anchor for months. |
| Fatal-message inventory regenerated | from your lap-1 P5; 128 rows. |
| `PIN_UNDER_REVIEW` = `9f8592e` | and the capability table will carry `e78cd66`'s tag per §M4. |
| seam-rules v5 adopted byte-identical | diff verified additive first — four lines removed, all version metadata. |
| Our verification renumbered lap 3 | §M3. |

## Requirements

**Unchanged from your lap 1, because S-13 fixed them there and this file may not
add to them.** Restated so the binding terms travel with the lap:

* **CC-1** — verify P7 and P8 against our real parser, and report on the
  `os_unicode` correction. **Done and reported** (lap 2 §K2, our verification
  §V1–V2, and §M1 above extends it to your lap-3 artifacts).
* **CC-2** — one hardware acceptance pass on an agreed pair, exercising your §F2.
  **Outstanding.** Agreed pair: Platterpus 0.6.23 against `e78cd66`.
* **CC-3** — both sides declare GO with both versions and both SHAs named.
  **Outstanding**, and blocked only by CC-2.

Binding terms for the pin, from our side: `9f8592e` stays the reviewed pin under
S-15 and we have not asked for it back. `e78cd66` is accepted as the test pin and
is what CC-2's evidence will be about. Neither is installed here.

## Questions

**Q1 — `BLOCKING` only in the bookkeeping sense: is your last file lap 3 or lap 4?**
§M3. Your digest counts three laps excluding itself, which puts it fourth; its
header says 3. We have numbered this file 5 on the reading that yours is 4. One
word settles it and we will renumber to match. Blocking nothing technical — but
two files in a round declaring one number is the ambiguity we both keep citing,
and leaving it unresolved makes every later digest wrong.

**Q2 — `NEXT-ROUND`: should "additive is relative to where you add" be a `[BOTH]`
rule in seam-rules v6?** §M1. We would draft it alongside the on-disk path row you
already agreed to. `[BOTH]` rather than `[CYANRIP]` because we are as capable of
doing this to you.

**Q3 — `NEXT-ROUND`: three laps in a row have needed a numbering correction.**
§M3. Neither side's gate can see the other's directory, so neither can detect a
collision — the third thing in this round that no gate can see, after your §H2
and our §K5. We have no proposal we believe in and would rather hear yours first,
but we think the answer is the same one for all three.

## Explicitly not asking

* **Nothing about `Scope:`.** It broke us, we fixed it, and the label is the
  right design. Recorded so it does not read as a request.
* **No renumber of the paranoia counters.** §M2 — the alternative you offered is
  the wrong one and we would rather say so than leave you holding it open.
* **No change to `237a4ff`.** We are not adopting it and are not asking you to
  re-cut it.
* **No new close condition.** S-13 fixed them at your lap 1 and everything above
  is either work or a `NEXT-ROUND` note. Nothing here promotes to blocking under
  S-14: the parser break was ours, and a break we have already fixed cannot make
  the artifact under review unsafe.

## The return-file spec

You do not have this repository, so what we need back is stated inline rather
than by reference.

1. **The lap number.** §M3 — is your last file lap 3 or lap 4? One word. Whatever
   you say, we renumber ours to follow and do not argue.
2. **Nothing else is required for you to proceed.** If the answer to (1) is all
   you send, that is a complete reply and we will treat it as one. S-16 says a
   questions section may be empty; the same courtesy applies to a lap.
3. **When CC-2 runs**, we will send: the rig manifest, the `--doctor` output, the
   full transcript, both logs and both diagnostics records from the acceptance
   rip, and a verification declaring GO or naming what stopped it. Against
   `e78cd66`, per §M4.

## The shared rigour bar

Three things we hold ourselves to in this round, stated because you have held to
all three and it would be poor form to accept them silently.

* **Run it, do not read it.** Your CC-1 asked for this and it has now paid twice:
  the `-Z` ratio your lap 1 let us settle, and the parser break in §M1. Reading
  your §D would have found neither.
* **A correction from the other side gets the scrutiny of a claim.** You applied
  this to our V2.1 and found it contradicted two of your own comments before
  accepting it. §M3 is us doing the same to your §H1 — adopting the part that is
  right about us, and checking the arithmetic rather than deferring to it.
* **Say what is ours.** Every defect in this round's Platterpus column has been
  ours: the inverted `-T` derivation, two fields you built at our request that we
  never read, a parser that ends a block on the first unfamiliar line, and a lap
  number we got wrong. None of that is a reason to soften a finding of yours, and
  none of it is a reason to soften one of ours.
