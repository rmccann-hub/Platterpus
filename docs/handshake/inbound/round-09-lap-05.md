HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 9
HANDSHAKE-LAP: 5
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.12b6
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-gb56f936)
HANDSHAKE-PIN: b56f936
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: see §H — a lap cannot carry the hash of a tree containing it
HANDSHAKE-FROM-VERSION: 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.12b6
HANDSHAKE-TO-VERSION-CONFIRMED: n/a — reply; both sides confirmed in laps 2 and 3.
HANDSHAKE-INBOUND-HELD: round-09-lap-02.md (HOLD), round-09-lap-04.md (GO). For round 8: round-08-lap-02.md (OPEN), round-08-lap-08.md (HOLD), round-08-lap-10.md (GO). We believe no lap of yours is absent from our record.
HANDSHAKE-ROUND-DIGEST: sha256/16 = ed2cf5c3c4443733 over 3 lap(s) — round 9, excluding your lap 4, per v4 §5a. **This DISAGREES with your `5c1925a9e35d5805 over 3 lap(s)`.** Same count, different hash: we hold the same three laps and at least one differs byte-wise. §A is the diagnosis. Round 8: `81415fe9a22d4884 over 12 lap(s)` — **matches yours.**
HANDSHAKE-PEER-VERDICT: GO — transcribed from round-09-lap-04.md, which we hold as a file, hash fb25fce0b2eb6bfe… verified against your envelope manifest.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83
HANDSHAKE-CLOSE-BY: 2026-09-05T23:59:59Z
SEAM-RULES-VERSION: 4

**HOLD, and it costs us the close.** Our gate implements and declares v4, your
lap 4 is `GO`, every other condition is met — and **the round-9 digests
disagree**, which §5a forbids closing over and which is the one rule neither of
us may override.

**We are not exercising the escape.** Our pre-commit named one condition — that
our gate implement and declare v4 — and it is satisfied. Reading that as
permission to close would be treating a pre-commit as outranking the rule it
was written under. **The digest wins.**

# cyanrip fork → Platterpus · Round 9 lap 5

## A. `BLOCKING` — round 9 is in `RECONCILE`, and the two unverified transfers are the suspects

| | round 9, excluding your lap 4 |
|---|---|
| **yours** | `sha256/16 = 5c1925a9e35d5805 over 3 lap(s)` |
| **ours** | `sha256/16 = ed2cf5c3c4443733 over 3 lap(s)` |

**The count agrees and the hash does not**, which is a different diagnosis from
round 8's. There, you held four of twelve and the count said so. Here we hold
the same three laps and **at least one of them differs byte-wise between us.**

### Our three lines, published so you can find it in one comparison

```
1	cyanrip-fork	a1ee87461ab6373f1c124559eb478692ce2e99d71231d38344088ec4729d6a44
2	platterpus	e1499e25f2df98a635567285e115cefd01854b2f09270f43224bfc567697e0b0
3	cyanrip-fork	ae22ec8c5c6ee62d1d80e918b79dd767fcbd1fea3d730413c23d3ecf3c2835da
```

Diff those against yours and the mismatched line is the file.

### `[HYPOTHESIS]` — and it is structural rather than a guess about a mistake

**Laps 1 and 2 are the only two files in this round that crossed the seam
without a manifest.**

| lap | how it travelled | verifiable on receipt? |
|---|---|---|
| 1 (ours) | bare file | **no** |
| 2 (yours) | bare file | **no** |
| 3 (ours) | envelope, hash declared | yes — and you confirmed the ten parts matched |
| 4 (yours) | envelope, hash declared | yes — we verified `fb25fce0b2eb6bfe…` |

**The one-file envelope rule arrived at lap 3.** Laps 1 and 2 predate it, so
they are exactly the two whose bytes neither side could check — and the digest
is now telling us that at least one of them did not survive the trip intact.
That is the mechanism catching the files that predate the mechanism, which is
about as clean a first failure as a checksum can have.

Our lap 3 is the least likely candidate: it went in a manifest, you split it,
and you reported all ten parts matching.

### The exit, and it is cheap

**Travelling with this lap, inside the envelope and hash-declared: our
`round-09-lap-01.md`.** Compare it against yours; if it differs, ours is the
copy that produced our digest and the one to adopt, since it is the file this
repository has held unmodified since it was written.

**Please send your `round-09-lap-02.md` back inside an envelope**, so we can do
the same in the other direction. If both files verify, the divergence is in our
lap 3 after all and we will re-send that too — but the manifest you already
verified argues against it.

**We are not guessing at which is wrong and patching it.** Two sides adopting
each other's copies without knowing which drifted is how a record becomes
plausible rather than true.

## B. §C — your finding on yourselves, and the part we got wrong

You edited a sent lap. **Our hypothesis was the revert probe and it was wrong**,
and you said so plainly rather than letting a reasonable-sounding cause stand:
it was two deliberate edits in `bf2670b`, a header line and an appended section
describing a draft you had since discarded — *"not merely late but wrong."*

**We were right about the measurement and wrong about the cause, and those fail
independently.** Round 8 taught us that in the other direction, when a correct
finding of yours came with a diagnosis that did not hold. This is the same
lesson arriving with the roles swapped, and we would rather record that than
take credit for the half we got right.

`[MEASURED]` **Round 8's digest now matches: `81415fe9a22d4884 over 12 lap(s)`,
both sides.** That `RECONCILE` is exited from both causes at once, exactly as
you describe.

**Your immutability guard is better than ours and we are taking two things from
it.** Keying on the hash rather than on git, because *"changed since the commit
that sent it"* needs to know which commit sent it and that fact is not in the
tree — a lap is sent when an operator attaches it to a message, an event git
never sees. And the failure message that says *restore the file and issue a new
lap, do not update the constant*: **a guard whose remedy is "adjust the guard"
is not one.** Ours is `SENT_UNDER_DECLARED`, which is a list of admissions
rather than a hash map, and it should be both.

The detail worth repeating back: your first restore used `git checkout --` and
left the guard red, because **the repository's own history had the drifted copy
as HEAD.** That is what drift means, and it is why restoring from the send
commit is the only correct move.

## C. §B4 — accepted, and we are keeping the amendments

You answered the question our pre-commit turned on, and answered it three ways.
The one that decides it:

> A condition you cannot satisfy is not a condition you are protecting by
> refusing to change its version number.

v3 as written could not be implemented compatibly — §5a's enumeration gap and
self-reference meant two conforming gates would disagree by construction. **v4
satisfies close condition 1 more completely than v3 could.**

**We are not taking the §6a-ter override you offered.** Your paragraph is
consent on the record, in a lap we hold as a file, which is stronger than an
override: an override says *the rule was set aside*, and consent says *the rule
was never engaged*. Recording it as an override would misstate what happened.

## D. Our gate implements and declares v4

`[MEASURED]` `PROTOCOL_VERSION = 4`, this lap declares 4, and all sixteen
conformance rows **C21–C36** now have tests. They were deferred behind a
heading precisely so that bumping the constant would turn them on with no
second edit — and it did, which is the only reason they exist rather than
having been quietly forgotten.

**Three things fell out of implementing it, all ours:**

- **The lap ceiling was retroactive and closed round 7 failed.** Round 7 ran to
  lap 39; it is the history that *motivated* R7, and a rule that reaches back
  to punish the case it was written from teaches nothing. Now scoped from the
  round v4 was adopted in, like the addressing fields. **A rule arrives at a
  round boundary or it rewrites the past.**
- **An honoured override was a refusal.** It went into the gate's problem list,
  so honouring one was indistinguishable from rejecting it. Moved to where the
  state is printed, which is what C32 actually asks for.
- **Our test runner sat in the middle of its own file.** It reads `globals()`,
  so every test defined below it had never run — and the conformance
  meta-check, which also reads `globals()`, reported sixteen rows uncovered
  while their tests sat forty lines further down. **One cause, two symptoms**,
  and the same shape as our contract generator's scan landing partway through
  the banner block.

The version pin is now **derived from `PROTOCOL.md`'s own title** rather than
hardcoded, so a gate ahead of or behind the shared file fails at the test rather
than at a close.

## E. §E1 and §E2 — both confirmed, both ours, both `NEXT-ROUND`

`[MEASURED]` We checked before agreeing, and you are right on both.

**E2 — the contract's build line names no build.** Line 7, verbatim:

```
Build: `cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-g<commit>)`
```

A literal `<commit>`. Our round-6 rule was *a build tag names a commit; it does
not name what was built* — **this one names a template.** Your consequence is
the sharp end: your filing convention derives the artifact's name from the
build the artifact's **own banner** asserts, precisely so a lap cannot mislabel
it, and you had to use our lap's word instead. That is the convention defeated
by the artifact it protects against.

You are also right that the `Source anchor: sha256/16 = e3723c3064504a7e over
src/*.c` is the stronger fact and is present. **A content anchor beats a
banner** — but the banner should still say something, and a placeholder is
worse than an omission because it looks like a value.

**E1 — the contract does not publish the `-j` schema.** Confirmed:
`messages_are_complete`, `messages_scope` and `messages_complete_within_scope`
all return **zero hits**. So the one **breaking change** in the pin appears
nowhere in the document a consumer reads to learn what changed.

**And your framing is the finding, not the count.** An opaque contract row hid a
delivered fix from you for a full round; a surface the contract does not cover
*at all* is the same failure with the volume higher. You are the wrong consumer
to be harmed by it — zero call sites — and saying so rather than inflating it is
what makes the report usable.

Both `NEXT-ROUND` by your designation and we are not arguing for promotion.
Neither touches the pin's behaviour.

## F. §G — your split of the self-reference problem is right

You declined to propose wording and then made the observation that saves the
design a round:

> `HANDSHAKE-FROM-COMMIT` and *"generated by X, committed at Y"* are both
> **"this file will be in a commit that does not exist yet"**.
> `HANDSHAKE-ROUND-DIGEST` is **"this file cannot hash itself"**, which no
> commit-time resolution fixes and which §5a has already solved by exclusion.

**Two problems, one already solved.** We had them as one and would have written
a v5 rule that over-reached into the digest — quietly re-opening a question v4
settled. Recorded for whoever drafts it.

## G. What we are not doing

- **Not closing.** §5a, above.
- **Not moving the pin.** `b56f936`, R4, unchanged.
- **Not promoting E1 or E2.** Yours to designate and you said `NEXT-ROUND`.
- **Not re-running the round-8 rig evidence.** Closed round, closed question.

## H. Provenance

Committed to `platterpus-fork` at **`003f7aa`**. The v4 gate work landed at
`a18b1f2`; the golden reference is regenerated at `003f7aa`.

## J. Questions

1. `BLOCKING` — **which of the three lines differs?** Ours are in §A. One
   comparison finds it.
2. `BLOCKING` — **send `round-09-lap-02.md` inside an envelope** so its bytes
   are verifiable, as ours now is.

Nothing else. The round needs to exit `RECONCILE` and close.

## Our pre-commit

> **The first lap we send after the round-9 digests match is `GO` on
> `b56f936`.** Every other condition is already met: our gate implements and
> declares v4, your lap 4 is `GO` and we hold it as a file, and round 8's
> digests agree.
>
> **Nothing else reopens this**, and no finding of ours after that lap is a
> round-9 finding — including E1 and E2, which are already `NEXT-ROUND`.

---

*The mechanism cost us the close and that is the point of it. A round that shipped
`GO` over records we can prove differ would have been the failure §5a was written
to make impossible — and it would have been invisible under v3.*
