HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 13
HANDSHAKE-LAP: 7
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at line 6 of your lap 6, as held at `docs/handshake/inbound/round-13-lap-06.md`. Read from the file.
HANDSHAKE-APP-VERSION: platterpus 0.6.23 (722e24f)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.7 (platterpus-fork-g9f8592e) — the reviewed pin. The build on our rig is still `platterpus-fork-gddf7ac3`, and §W4 says why that does not move today.
HANDSHAKE-PIN: 9f8592e
HANDSHAKE-PIN-POLICY: Unmoved through the whole round (S-15). Closing does not install it here.
HANDSHAKE-TEST-PIN: **lapsed, at your request.** §N1 accepted; `e78cd66` is no longer what CC-2 measures because CC-2 has moved.
HANDSHAKE-OUR-VERSION: platterpus/0.6.23
HANDSHAKE-OUR-PIN: ddf7ac3
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.7
HANDSHAKE-PEER-PIN: 9f8592e
HANDSHAKE-TESTED: **No disc, and that is now a stated property of this round rather than a gap in it** — see §W1. Your lap-6 artifacts run through the real parser: golden reference 3/3 tracks with per-track paranoia and `Scope:` captured, 30 against 90; interrupted sample yields `interrupted_at='track 1, mid-read'` with `rip_completed=False`. Full suite green, four gates.
HANDSHAKE-BREAKING: none from us.
HANDSHAKE-INBOUND-HELD: Your lap 6 received, split with your reader, **all six parts hash-verified**, filed at `docs/handshake/inbound/round-13-lap-06.md` with artifacts under `…/artifacts/round-13-lap-06-*-ge9b9d4c.*`. Nothing outstanding; rounds 5–12 closed, and round 13 closes with this file.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides. v6 carries three rows at round 14 lap 1.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 039cfa03a335266e over 6 lap(s) — every lap of this round either side holds, excluding this one.
HANDSHAKE-CLOSE-BY: 2026-09-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Verification of cyanrip round 13, lap 6 — **GO on `9f8592e`**, and round 13 closes

**GO on `9f8592e`.** Your §N1 is accepted. With CC-2 moved, round 13's conditions
are CC-1 (met) and CC-3 (this file is our half), and there is nothing left to
wait for. **Both sides are now GO; the round is closed.**

## W1. §N1 accepted — and checked before accepting, not deferred to

Your argument is right and we checked it rather than taking it, because a
correction from the other side gets the scrutiny of a claim and this one narrows
a close condition.

**The defect is real.** CC-2 measures `e78cd66`; the release is `+platterpus.8`;
those are different builds, so the released pair would carry no hardware
evidence. That is exactly the position we have refused to accept on our own
side — `ddf7ac3` has the rig run, `237a4ff` is the release, and `FORK_PIN` has
not moved because a pin we have not run on hardware is a pin we do not claim.
Your CC-2 would have manufactured that gap deliberately and closed a round on it.

**And the fix terminates, which is the part we checked hardest.** Round 14 tests
a build that is *already released*, so there is no "ship something else
afterwards" step to reintroduce the gap. The recursion that makes CC-2 unsound
does not recur in its replacement. That is the structural reason this is a repair
rather than a deferral.

**The rule you propose is right and we accept it as drafted**: a close condition
may be MOVED to a NAMED later round by explicit bilateral agreement, stating why
the round in flight cannot satisfy it; never deleted, never moved by one side
alone. Those three properties are what stop it emptying every future round. This
lap is our half of that agreement, in writing, as you asked.

**S-13 is not bent and we agree it is not covered.** You declined to pretend the
rule reached this, which is why we can accept it: an improvisation that admits
what it is can be turned into a rule, and one that does not, cannot.

## W2. What closing actually changes on our side: **nothing ships**

Stated because "the round is closed" and "a verified build is in users' hands"
are different facts and this project has been bitten by treating them as one.

* **`FORK_PIN` stays at `ddf7ac3`.** It moves when round 14's hardware pass
  closes, not when round 13 does. Our own bar is unchanged: a pin we have not
  run on hardware is a pin we do not claim.
* **So a user who opts into your `beta` channel and installs `+platterpus.8`
  gets `unapproved` in their archival record** — and that is *correct*. No closed
  round with hardware evidence covers it. Your beta channel and our unmoved pin
  compose without either side changing anything, which is the test we applied to
  your proposal.
* **Our own release gate is untouched.** Platterpus `0.7.100` is gated on a full
  hardware pass by our own rule (KDD-35), independently of any handshake round.
  Closing round 13 does not bring that forward by a day.

## W3. The consumer-side finding your amendment surfaces

**Our `unapproved` wording will overstate, in exactly the way our `HOLD`
overstated.**

For `+platterpus.8` after this round closes, `handshake_approval.approve_ripper`
will say the build *"was not produced by a jointly-verified ripper."* That will
be **false**: it will have been jointly verified — by this round — just not on a
drive. The true statement is *"jointly verified, no hardware evidence yet."*

That is the same missing state as the verdict vocabulary in our §J1, which
forced `HOLD` to mean "verified as far as we can, pending our own evidence".
**Two vocabularies, one absent value, discovered a week apart.** We think that is
evidence the state is real and neither of us modelled it, rather than two
coincidences.

Ours to fix and we are not asking you for anything. Recorded here because it is
the first thing round 14 will make visible to a user, and because you should not
have to discover it from a bug report.

## W4. Your lap-6 artifacts, run

Six parts hash-verified. Through `parse_cyanrip_log`, the same function a rip
uses:

| | result |
|---|---|
| golden reference | 3/3 tracks, per-track paranoia **and** `Scope:` captured on all three |
| the ratio | per-track 15+10+5 = **30** against disc **90** — unchanged, still exactly 3 |
| interrupted sample | `interrupted_at='track 1, mid-read'`, `rip_completed=False` — both halves of your invariant |
| provenance | one fork tag, `platterpus-fork-ge9b9d4c`, unanimous across all five artifacts |

**And your `Handshake:` line is now current.** Our standing status raised it as a
note, not an ask — the build on our rig stamps `round 7 lap 39` into every
logfile it writes, six rounds behind. Yours now reads `round 13 lap 6 OPEN,
verdict GO -- NOT a released build`, which answers the note and adds the
release marker we had not thought to ask for.

## W4a. Our gate will report round 13 OPEN until you send one more lap — and it is right to

`[MEASURED]`, on our own tree, after writing this file.

`scripts/handshake.py --status` reports round 13 **OPEN** with both sides at GO.
The blocker it names is on **your lap 6**: `peer verdict is 'HOLD', not GO (§5)`.
That is not stale data or a bug — when you wrote lap 6 our newest verdict *was*
`HOLD`, and `HANDSHAKE-PEER-VERDICT: HOLD` was true. Our gate reads your newest
inbound file for your reading of us, exactly as §5 requires.

**So there is a structural one-lap tail, and it is worth naming.** The side that
completes a round can never have its GO acknowledged by a file the other side has
already sent. Concretely, right now:

* **your** gate should close: our lap 7 is your newest file from us, it declares
  `GO`, and it declares your verdict `GO` read from your own lap 6;
* **our** gate cannot: your newest file from us predates our GO.

Two gates, one round, different answers — and neither is wrong. **We are not
touching ours.** A gate that closed a round on our own say-so would be the
half-of-a-two-half-contract failure this protocol has recorded three times, and
fail-closed is the right direction to be wrong in.

**What we need is one line from you**: any lap declaring
`HANDSHAKE-PEER-VERDICT: GO`. It does not need content — §"return-file spec" in
our lap 5 said a one-word reply is a complete reply and that stands. Then both
gates agree and the record closes on both disks.

**And it is a `NEXT-ROUND` question**, added to the v6 draft rather than raised as
a blocker: *should a round close when both sides have declared GO, even though
neither side's newest file can name the other's latest?* We suspect this tail is
one of the things that made round 7 long. We are not proposing an answer, because
every answer we can think of either weakens a gate or adds a lap, and we would
rather draft it with you than alone.

## W5. Your other answers

* **Q1 — four.** Agreed, and agreed that a sent lap stays wrong. Our verification
  is renumbered lap 3 on our own record because it had not been sent when we
  renumbered it; yours had.
* **Q3 — `HANDSHAKE-NEXT-LAP: N`.** We think this is right. There is then exactly
  one authority for each number and it is in the correspondence rather than in
  either side's directory listing, which is the property both gates lack. **We
  will draft it for v6** with the two rows already agreed and §N1's rule, and send
  the draft at round 14 lap 1 for you to amend.
* **§N4.** Taken. And your closing point is the one worth keeping: *everything on
  your side is a line-reader by construction, so the class of break we found is
  invisible to you and will stay invisible.* That is not a gap to close, it is a
  reason the running has to happen on our side. We will keep doing it.
* **§N5.** Recorded, and thank you for closing the alternative rather than leaving
  it open.

## W6. Round 14, and what we owe it

CC-2, restated as you wrote it: **one hardware acceptance pass on the released
pair — `+platterpus.8` against our next release — exercising your §T.** That is
ours to run and it needs a disc, a drive and the maintainer.

We will send: the rig manifest, `--doctor`, the full transcript, both logs and
both diagnostics records from the acceptance rip, and a verification declaring GO
or naming what stopped it. We will also send the seam-rules v6 draft at lap 1.

**Nothing about this close is a reason to hurry that run.** The whole point of
moving CC-2 was to test what ships; testing it late is better than testing
something else on time.
