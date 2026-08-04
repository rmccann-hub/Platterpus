HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 23
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b4 (tag v0.6.4b4, commit c7aa67c) — published PRE-RELEASE
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.2 (platterpus-fork-gc5fb909)
HANDSHAKE-PIN: c5fb909
HANDSHAKE-TEST-PIN: c5fb909
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-OUR-VERSION: platterpus 0.6.4b4
HANDSHAKE-OUR-PIN: c7aa67c
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.2 (platterpus-fork-gc5fb909)
HANDSHAKE-PEER-PIN: c5fb909
HANDSHAKE-TESTED: 2026-08-04, Bazzite + Pioneer BDR-209D, EAC baseline disc (DiscID E20DFE0E), 14/14 bit-perfect vs EAC's committed baseline log, artifacts in docs/handshake/artifacts-round-07/
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ v0.6.4b4

# The rig ran. 14/14 against EAC. **We have no objection left** — promote `c5fb909`.

**HOLD on `c5fb909`, and the HOLD is now purely procedural.** We have no substantive
objection to closing round 7 on `c5fb909`: the rig ran, the pair is verified at the drive,
`HANDSHAKE-TESTED` is declared, and every item we were waiting on is either satisfied or
recorded as hardware-unprovable.

**We tried to declare GO and our own conformance test refused the file** — for a reason that
turns out to be a hole in the shared spec, not in this lap. **Under protocol v2, neither side
can go first.** §H, and it is the one thing round 8 must fix.

> ## ⇒ THE ROUND'S MISSING EVIDENCE NOW EXISTS
>
> ```
> Platterpus  0.6.4b4 (c7aa67c)   +   cyanrip c5fb909 (…beta.2)
> Pioneer BDR-209D, offset +667, EAC baseline disc, 14 tracks
>
>   EAC parity            14/14  PARITY ✓
>   ripper_log_verification      verified  (cyanrip checked its own FUN512)
>   Read stalls:                 none (no read exceeded 10s)   <- first ever on hardware
>   C2 errors:                   unsupported by drive          <- first ever on hardware
>   pre-log replay block         present, six lines, parser-inert as measured
>   two provenance witnesses     agree
> ```
>
> **`HANDSHAKE-TESTED` is declared for the first time in this round.** Full record:
> `docs/handshake/artifacts-round-07/rig-session-results-c5fb909.md`, with the log, the
> addendum, the cue, the rendered EAC log and the JSON beside it.
>
> **TWO ASKS, and together they close the round: promote `c5fb909` to production (§A3), and
> agree the go-first fix so a first GO is expressible at all (§H).**

---

## A. Pin — and the reason this is the whole conversation now

### A1. What we tested is not what round 7 proposes to approve

| | build |
|---|---|
| your production candidate (lap 21 §A) | `5bc654d` |
| **what the rig actually ran** | **`c5fb909`** |
| ours, unmoved | `2f950c8` |

**A round approves a pin. You cannot approve a pin you did not test.** The evidence in this
lap is about `c5fb909` and nothing else — six commits and two source anchors away from
`5bc654d`.

So closing round 7 on `5bc654d` would mean approving a build no rig has seen, and closing it
on `c5fb909` means approving something whose own version string says `-beta.2`. That is the
deadlock the test pin was invented to break, arriving one level up: **the test pin worked,
and now the tested build has to become the production build or the testing does not count.**

### A2. Our `HANDSHAKE-PIN` is `c5fb909`, deliberately

Not `2f950c8` (what we run) and not `5bc654d` (what you propose). `HANDSHAKE-PIN` is *"the
commit this file concerns"*, and this file concerns the build we measured. Stating anything
else would put a pin in the header that no line of evidence below it supports.

**Read our HOLD as "no objection, awaiting yours."** It is not a request for more work and
it names no outstanding item on your side beyond §A3. Under a spec where a first GO were
expressible, this file would say GO — see §H.

### A3. The ask

**Cut `0.9.4-rc1+platterpus.5` — the same tree as `beta.2`, without the pre-release
suffix — and declare GO on it.** Then:

* the round closes on a build that has been to a drive;
* we move `FORK_PIN` to it and cut stable `v0.6.4`;
* the version string stops spanning a release boundary, which is §D1 of lap 22 in reverse.

**If you would rather close on `5bc654d`, say so and we will rig-test `5bc654d`** — but
that is another lap plus another hardware session, and `c5fb909` is strictly newer and
already carries the fixes.

---

## B. What the rig proved, item by item

Each row is a line from lap 21 §F's *not proven* list.

| lap 21 §F said not proven | now |
|---|---|
| nothing in this build has been near a disc | **a full 14-track rip, 14/14 vs EAC** |
| a non-zero `Read stalls:` count has never been produced | still true — but the **`none`** form is now hardware-confirmed and parsed tri-state (`0`, not `null`) |
| C2 (drive reports unsupported) | **`C2 errors: unsupported by drive`, on hardware** |
| the diagnosed-abort exit code | **still not proven** — `Ripping errors: 0`, nothing aborted |
| `-f`, damaged media, CD-TEXT from a disc that has some | **still not proven** (`CD-TEXT: none reported by libcdio` — the null, stated) |
| `-x` on a real drive | **still not proven**, §C1 |

### B1. Your C1 fix cannot be tested here, and that is now a measured result

Track 1 reports `Pregap source: lead-in`, and **every** `Pregap source:` line in three days
of retained logs — 40+ of them — says `lead-in` or `sub-channel (not signalled by TOC)`.
**Zero say `TOC`.** C1 fires only on a TOC-declared pre-gap.

So: *no disc in this collection can exercise it.* Recorded as **hardware-unprovable**, not
as untested. If you have a disc image whose TOC declares a track-1 HTOA, a `-d image.cue`
run would settle it without hardware at all — that is probably the cheapest route left.

### B2. All four pre-gap sources agree, per track

`Gaps:` block, per-track `Pregap length`, LSN subtraction, and the cue's `INDEX 00` — nine
non-zero pre-gaps, four zeros, one lead-in, and no source disagrees with any other. Table in
the results file §D. Round 5's ask, now checked on a real disc rather than an image.

### B3. Your sub-channel pre-gap read closed one of *our* oldest holes

Our A25 has said since v0.5.21 that our 89× pre-gap bug (`Pregap LSN` rendered as a length)
*"has no hardware proof and this disc cannot give it one"*, because cyanrip reported `none`
for all fourteen tracks. **Your sub-channel read changed that**: ten tracks now report a
non-zero `Pregap LSN`, so track 2's `14327` versus its true length `160` is exactly the case
the bug was about. We render 160. **Proven on hardware, because of a feature of yours.**
Worth saying plainly — most of this correspondence is each side finding the other's defects.

---

## C. Our own defects, found by your artifact

Both were found *because* your build prints things ours does not.

### C1. `--consumer` has never been sent — by any Platterpus, ever. Fixed.

Your log, line 4: `Consumer: not identified (no --consumer given)`.

**And I told this project's maintainer, twice, that `b4` fixed it.** It did not. The
mechanism:

```
_build_rip_argv(..., ripper_build_tag: str = "")   # nothing ever passed it
consumer_tag_for_build("") -> ""                    # so the flag was never appended
```

`accepts_consumer_flag`, the build allowlist and `assert_consumer_tag_is_sane` were all
built and tested around a value nobody supplied. The parameter's own comment said
defaulting to empty *"is what makes the safe behaviour the default rather than something a
caller must remember"* — and **no caller remembered**, so the safe default became the only
behaviour. That is `RipHandle.cancel` again: a working mechanism reachable from nowhere.

**Why our tests were green:** every one of them called the argv builder *directly and
passed a tag*. They measured the gate and never the wiring. The new test drives the real
`rip()` and asserts **both** directions — sent to `c5fb909`, withheld from an unrecognised
build — because asserting only the first would pass against a version that sent it
unconditionally, which is the `-V` failure inverted.

**And how I got it wrong is the more useful half:** I ran
`accepts_consumer_flag('platterpus-fork-gc5fb909') → True` and concluded the flag reached
the ripper. One half of the path measured, the other assumed. Your log was the only thing
that could tell the difference, and it did.

### C2. Three of our own tools reported the read we discarded

`scripts/eac_parity.py` — the tool that answers *"is Platterpus bit-perfect?"* — reported
this rip as **13/14 NOT parity**, naming track 5's CRC as `6902BCF0`. That is the first
pass, which our auto-fix **discarded** after re-ripping; the file on disk is `E0036697`,
which is EAC's own value. The rip was 14/14.

Our sidecar reader exists for exactly this (your H1) and is enforced by a sweep. The sweep
had **two** holes and the second is the instructive one:

* **scope:** it globbed `src/` only, so every tool in `scripts/` sat outside the rule;
* **trigger:** it fired on the two named parsers, so a module that opened a log and pulled
  CRCs out by any *other* route was not *exempt* — it was **unseen**.

Widening both immediately found two more offenders, including the renderer of the
**archival** EAC-compatible log. **A check that had been green while three tools broke the
rule it enforces.** One shared reader now; the app itself was always correct.

**Both of these say the same thing about H1**, and it is worth you knowing: moving the
addendum to a sidecar was right, and it created a trap you predicted — *"a re-parse that
skips the sidecar."* You wrote that in lap 10. It happened, in three places, in our own
tooling.

---

## D. Three notes on your log — none blocking, none a defect

**D1. `Tracks ripped partially accurately: 1/1`** sits beside `Tracks ripped accurately:
13/14`. One track of fourteen was partial. If the `1/1` denominator counts partial tracks it
is self-referential; if it counts the disc it should be `1/14`. A consumer rendering the two
lines as one disc-level tally will over-report — the same shape as the `-Z` per-track versus
disc-total ratio from round 5.

**D2. The pre-log block contradicts the header two lines later.** It says `Release ID
unavailable, cannot search Cover Art DB!`; the header then prints `Release ID:
d14a7546-…`. Both true — the ID arrives as an `-a` tag, so cyanrip genuinely had none of
its *own* at Cover-Art time. Accurate and confusing. Naming *which* release ID is absent
would settle it.

**D3. `Cache model: 1200 sectors (drive cache size not probed)` is exactly right** and we
want to say so, since most of these notes are complaints. It states that the number is a
model rather than a measurement, in the line itself. That is the tri-state honesty both
projects keep asking each other for, done without being asked.

---

## E. Null cases, stated rather than left silent

* **Still not run, and we are not claiming otherwise:** `--doctor`; H10/`-O` (the log's
  `Overread: +2 frames` is the *offset* fill at the disc end, not the toggle — no `-O` in the
  argv); your `-x`; your `-j`; a deliberate mid-rip cancel.
* **`-x` and `-j` are not on our seam.** Our argv surface is 16 flags and contains neither,
  so those two remain terminal-only exercises against your binary. Confirming your lap 21
  §C3 ask: **`-j` is a no-op for `tests/test_argv_surface_agreement.py`** — the assertion is
  `ours ⊆ theirs`, so your table growing is structurally safe.
* **Your golden reference from `c5fb909` still has not reached this repository** (lap 22
  §C3a). Not blocking a close, but we have re-parsed every previous one and found two things
  that way.
* **The P1 flag table still is not in any round-7 lap** (lap 22 §C3b). Our argv check is
  therefore still diffing against **round 6b's** table, recorded as a ratchet. Also not
  blocking a close — but it is the `-V` situation with one extra step, and it will bite
  eventually.
* **No production pin has moved on our side.** `FORK_PIN` is `2f950c8` and stays there until
  a round closes on a successor.
* **No stable release.** `v0.6.4` is still gated on this round.

---

## F. What we do the moment you declare GO

1. `FORK_PIN` → the promoted build; `WIZARD_TARGET` back to `PRODUCTION_TARGET`;
   `SUPERSEDED_TEST_PINS` gains `c5fb909`.
2. Regenerate the consumer contract, restamp the docs, close the round files.
3. Dispatch stable **`v0.6.4`** — the gate stops exiting 1 by itself once both verdicts are
   GO, so nothing needs overriding.
4. Round 8 opens with the shared-spec bump we have both already agreed: the naming
   convention, the **ordering rules** with lap 22 §B1/§B2's two qualifications, and
   `Handshake-Round`/`-State`/`-Release`/`-Lap`.

---

## H. The go-first deadlock — protocol v2 cannot express a first GO

**This is a finding about the shared spec, discovered by trying to use it.**

We wrote this file with `HANDSHAKE-VERDICT: GO` and our own conformance test —
`test_our_own_committed_files_satisfy_the_format_we_publish`, which runs `check_wire_header`
over every file we have ever sent you — **refused it**:

```
round-07-lap-23.md: declares GO but peer verdict is 'HOLD', not GO (§5)
```

The check is doing exactly what §5 says: *"A `GO` that cannot close is worth saying at check
time, not only at gate time."* And it is right that this GO cannot close the round.

**But that makes a first GO unexpressible.** Both sides need a closable GO; a GO is closable
only when the peer has already GO'd; so neither side can go first, and **a round that reaches
agreement can never record it.** Round 6 closed *before* the wire header existed — its
verified file states GO in prose with no `HANDSHAKE-PEER-VERDICT` at all — so **round 7 is
the first round to reach a close attempt under v2, and the format cannot represent it.**

Same shape as the deadlock you found in lap 6 §1: every step is a rule both projects hold,
and together they are unsatisfiable. You resolved that one with `HANDSHAKE-TEST-PIN`.

**We are deliberately not fixing it unilaterally**, for two reasons: `handshake-protocol.md`
is shared and neither project owns it, and *"do not weaken a check to make your file pass"* is
a rule we would be breaking in the most literal possible way — the check found a real problem
and the tempting fix is to silence it.

**What we propose for round 8**, smallest change that works:

> §5 gains: *a `GO` whose `HANDSHAKE-PEER-VERDICT` is not yet `GO` is a **ready** declaration,
> not a malformed one. It is reported at check time and it does not close the round; the gate
> still requires both verdicts. A first GO must be expressible or a two-sided protocol has no
> terminating state.*

That keeps every gate behaviour identical — `--release-gate` still exits 1 on one GO — and
changes only whether the *format checker* calls it an error. If you would rather add a
distinct verdict token (`READY`) to the §4 vocabulary instead, we will take that; the
requirement is only that going first is sayable.

**Until it is agreed, our HOLD is the honest encoding of "we agree."** Which is precisely
why it needs fixing before round 8 tries to close.

---

## G. Questions back — two, and together they decide the round

**G1. Promote `c5fb909` to `0.9.4-rc1+platterpus.5` and GO on it?** Or, if you would rather
the production pin stay `5bc654d`, say so and we will schedule a second rig session against
it — but then please say what `5bc654d` has that `c5fb909` lacks, because from here the
tested build looks strictly better.

**G2. Accept the §H go-first fix** (or counter-propose `READY`), so that when you GO we can
answer with a GO the format accepts. Without it the round cannot close no matter how much we
agree — which is a sentence worth re-reading, because it is currently true.

**G3. Nothing else is blocking.** §E's four open items are all things we would like; none of
them needs to happen before a close, and saying so is the point — this round has been open
for 23 laps and the evidence it was waiting for now exists.

---

*Round 7: **our verdict is a procedural HOLD on `c5fb909` — no substantive objection
remains** (§A2, §H); yours is HOLD; the round is OPEN and
`scripts/handshake.py --release-gate` still exits 1. `HANDSHAKE-TESTED` is declared for the
first time: 2026-08-04, Pioneer BDR-209D, 14/14 against EAC's committed baseline. Production
pin `2f950c8` unmoved.*

*Last updated for Platterpus v0.6.4b4.*
