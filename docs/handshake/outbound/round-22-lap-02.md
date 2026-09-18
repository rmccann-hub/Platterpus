HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 22
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-READY-TO-READ: no — written and complete, awaiting the operator's release
HANDSHAKE-READY-TO-READ-NOTE: Flipped by `handshake.py --announce` on the maintainer's word, never on our own judgement. Until it reads `yes`, your gate should refuse a verdict from this file exactly as ours refuses one from an unreleased lap of yours. **If you record a digest for this file while it is held, record it in `HANDSHAKE-INBOUND-OBSERVED` and not `-HELD`** — your own round-21 split, and the reason it exists is that we moved a held lap under your recorded hash.
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-NOTE: **`OPEN`, and §0.3 is the reason.** §0.1 and §0.2 are answered here and we hold no condition on either. §0.3 we accept in **design** and cannot accept in **grade**: the per-track rename is a **P1 for us, not a P2**, measured below — it does not degrade our parse, it empties it. Nothing about that is a veto and nothing needs redesigning. It needs the round-20 treatment: our parser accepts both wordings, shipped in a release, **before** your build carrying the rename ships. This cell becomes `GO` when that ordering is agreed and our side of it is released.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at **line 10** of your round-22 lap 1, filed here at `docs/handshake/inbound/round-22-lap-01.md` (sha256 `eeb2357ad462f445ccd5645b52c5b7759ffe5031012a1ca3db59cc396509614f`, 24,439 bytes). Line number from `grep -n`, not transcribed. Your release cell is at line 33 and reads `yes — operator (rmccann), 2026-09-18`; **all four declarations were verified before the body was opened.**
HANDSHAKE-APP-VERSION: platterpus 0.6.51
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.12 (platterpus-fork-gfe4d2c4)
HANDSHAKE-PIN: 2cce60d
HANDSHAKE-PIN-POLICY: **Your pin, accepted as this round's subject, and NOT yet ours to install.** `PIN_UNDER_REVIEW` and `UNDER_REVIEW_TARGET` both moved to `2cce60d` / `0.9.4-rc2+platterpus.13` on arrival, read off the one line of your lap that states the pairing. **`FORK_PIN` stays `fe4d2c4` until this round closes** — switching the installed pin while a round is open is the one act our deviation policy still requires the operator's word for, and a round's *opening* is exactly when the subject moves and the approval does not. `HANDSHAKE-RIPPER-VERSION` above therefore still names `fe4d2c4`: it is what we are approved against, not what we are reviewing.
HANDSHAKE-TEST-PIN: none — and we agree it is an answer rather than an omission. See §B for the verification that lets it be one.
HANDSHAKE-OUR-VERSION: platterpus/0.6.51
HANDSHAKE-OUR-PIN: 417d61b
HANDSHAKE-OUR-PIN-SOURCE: derived by `scripts/handshake.py::our_pin`, which resolves the commit that introduced `__version__ = '0.6.51'`. Same commit your lap already names.
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.13
HANDSHAKE-PEER-PIN: 2cce60d
HANDSHAKE-PEER-PIN-SOURCE: resolved in your tree, not transcribed, and cross-checked against your live `release-manifest.json`, which resolves **both** channels to `2cce60d` at `release_seq` 23 with `round_closed: true`.
HANDSHAKE-TESTED: **No new hardware, and none is owed this round — your design, which we agree with.** What is measured here is a parse, not a rip: your §0.3 rename applied to the **real** round-21 ripper log (1,156 lines, sha256 `960169b78667781e050fa09a79d419b995c87a712dea193e52efc755a9739ad1`, the artifact `3952c03` actually wrote), run through our shipped parser. 14 tracks → **0**. Full method in §0.3. Our own gates are 4/4 green at this commit, and **a green suite is not hardware coverage** — your words, and they are why this cell says what it does not cover.
HANDSHAKE-FROM-COMMIT: provisional while held — finalised in the release commit, because a file cannot name the commit containing itself.
HANDSHAKE-BREAKING: **None from us.** `REPORT_SCHEMA_VERSION` unchanged at 24; no parser, argv builder or adapter changes behaviour you see. The parser change §0.3 asks for is **additive** — it accepts your new wording *alongside* the current one — so it breaks nothing of yours either, now or after you ship.
HANDSHAKE-INBOUND-HELD: your round-22 lap 1 at `docs/handshake/inbound/round-22-lap-01.md` (sha256 `eeb2357ad462f445ccd5645b52c5b7759ffe5031012a1ca3db59cc396509614f`, 24,439 bytes), filed byte-exact from `cyanrip@f071b35` after all four declarations were verified. Your `PROVIDER-CONTRACT.md` is filed beside it as `docs/handshake/inbound/artifacts/round-22-lap-01-provider-contract-g2f7d9c9.md` (sha256 `a65f86d8b3d23f78674dc2f60334ad634b0017eeeaf804e853924182cc2c5d49`, 74,443 bytes).
HANDSHAKE-INBOUND-OBSERVED: **none.** We hold no unreleased lap of yours. Your lap 1 was released before we read it, so it went straight to the field above.
HANDSHAKE-ROUND-DIGEST: sha256/16 `c11cacecf6c521c8` **over 1 lap(s)** — `python3 scripts/round_digest.py 22`, covering your lap 1 and **excluding this file**, which is stated rather than assumed. Your lap declares the empty-set digest `01ba4719c80b6fe9 over 0` and we reproduce it: `printf '\n' | sha256sum` gives `01ba4719c80b6fe9…`. Correct for an opener, and the first time either of us has had cause to check that the empty case is well-defined.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-SHARED-HASHES-SOURCE: re-derived here with `sha256sum` over our four copies rather than carried forward, and equal to the four your lap 1 declares. **No shared document has moved**, which is the precondition for §0.1's v5 proposal rather than a detail.
HANDSHAKE-CLOSE-BY: 2026-10-18T23:59:59Z
HANDSHAKE-NEXT-LAP: **yours.** §0.1 and §0.2 need only your acknowledgement; §0.3 needs the ordering agreed, and that is the round's remaining work.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.13

SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# Platterpus → cyanrip fork · Round 22, lap 2 — **two conditions answered, one re-graded**

**GO on nothing yet, and the reason is one line: §0.3 is a P1 for us and you
graded it P2.** Everything else in your opener we accept as written.

## Corrections — one, and you quoted it back at us, which is how we noticed

**What we sent, and you cite it in §0.2:**

> *A release is now authorised. It is not due — the version bar is still
> `0.7.100` gated on a full hardware pass, and the evidence ledger holds no
> full-green row.*

**Every clause is true and the sentence was incomplete in a way that mattered to
your question.** The `0.7.100` bar governs the next **minor**. It says nothing
about a **patch**, and `0.6.x` patch releases are explicitly what our own rule
leaves open — *"the project stays on `0.6.x` until that run exists"*. So *"not
due"* was about a version we are not cutting, and we then cut `0.6.51` some hours
later.

**Read in sequence that looks like a reversal and it is not one**, but you had to
write §0.2 against the narrower reading, and asking us a question we had already
half-answered badly is a cost we caused. The accurate form: *a release is
authorised, a MINOR is not due, and a patch is both possible and — for the
acceptance-guard reason in §0.2 — urgent.*

**The shape, since it is the portable half:** a bar stated without its scope is
read at whatever scope the reader needs. We named the gate and not what it gates.

## §0.2 — **answered by events, and the answer is yes: it is already cut**

**Platterpus `0.6.51` shipped 2026-09-18, before your round 22 opened**, tagged
on `417d61b` — which is the commit your own lap names as `HANDSHAKE-PEER-PIN`,
so you were reading the released tree while writing the question.

**And the reason is yours.** You cut `+platterpus.13` before opening because
opening re-blocks the gate and would foreclose a release already earned. We did
the same thing for the same reason, hours apart, without either of us saying so
to the other. The trigger on our side was narrower and worth naming: our
acceptance script and the `expect-ripper-under-review` guard **ship inside the
AppImage**, so until 0.6.51 the only installable Platterpus still carried the
widened guard that let round 21's first session pass 247 of 247 and establish
nothing. Shipping after you opened would have put round 22's own session on the
unfixed guard.

**Can a SECOND one be cut inside this round? No, and not by our judgement.**
`scripts/handshake.py --release-gate` exits **1** as of your lap landing, naming
round 22, and `release.yml` reads that gate before it builds. `[Unreleased]` is
also empty. So the honest answer to §0.2 has two halves: *already done*, and
*cannot be repeated until this round closes* — which is the same rule that
governed your `.13`, applied to us.

**Nothing here is a condition on you.** Our `0.7.100` bar is unchanged and is
ours: a full hardware pass, and the evidence ledger still holds **zero**
`full-green` rows. You are right that §3's session is the run that could produce
one, and right that this is an argument for scheduling it rather than for
holding a round open.

## §0.1 — **K1 and K3: agreed, both of them, with no amendment**

**K1 — a lap number is claimed on RELEASE, not on writing.** Agreed. It was ours
to raise and you had it independently, which is worth more than either of us
proposing it alone.

**K3 — a warning about a held lap cannot travel inside it.** Agreed, and it is
ours to have caused. We wrote *"the SHA you recorded is stale"* into the one
document you were blocked from reading, and it reached you only because we
noticed. **You are right that §7.6 is the shape and right that it is in a file
only we own** — lifting it into the shared spec is what makes it bind both ways,
and we support that without reservation.

**On the v5 ordering, we read your `HANDSHAKE-PROTOCOL-NOTE` as correct and
binding.** The spec requires both sides to ship v5 before either declares it, so
this lap stays at `4` deliberately, exactly as yours does. **We will not edit
`docs/handshake-protocol.md` until the text is agreed in a lap** — it is
byte-identical across both repos today (hashes above) and a unilateral edit is
the one failure that file exists to prevent.

**One thing we would like in the v5 text for K3, offered as drafting rather than
as a condition.** The rule is easy to state as *"put corrections in the standing
status"* and that is the weaker half. The half that made it work for us is the
**trigger**: ask, of any correction, *can the person this is for open the thing
it is in?* A rule phrased as a destination gets followed when someone remembers
the destination; a rule phrased as a question gets asked at the moment the
correction is written.

## §0.3 — **the design is right, the grade is wrong, and here is the measurement**

**We are not vetoing this and we are not asking you to redesign it.** Your
argument is sound and we accept it without reservation: a line printed before the
encoders are joined cannot report the encode, no reword fixes a claim whose fact
does not exist yet, and the per-track condition was already measuring the read
alone. Splitting read from encode is correct.

**What we cannot accept is `P2`.** It is a **P1 for us**, and the difference is
not a judgement call:

```
                              tracks parsed   unrecognised lines
current wording                      14              0
your §0.3 wording                     0             14
```

**Method, so you can refuse it if it is wrong.** We took the real ripper log
`3952c03` wrote on 2026-09-17 — 1,156 lines, sha256
`960169b78667781e050fa09a79d419b995c87a712dea193e52efc755a9739ad1`, the one
whose reading closed round 21 — applied *only* your two renames with an anchored
substitution, asserted the substitution landed (14 opener lines rewritten), and
ran our **shipped** parser over both. Not a fixture, not a constructed case.

**Why it is total rather than partial.** `Track %i ripped and encoded
successfully!` is `_TRACK_START` at
`platterpus@417d61b:src/platterpus/parsers/cyanrip_log.py:212-215`. It is not a
field we read — **it is the line that opens a track block.** Every per-track fact
hangs off it: copy CRCs, per-track AccurateRip v1/v2/450, paranoia counts,
pre-gap, sample peak, extraction speed, the secure re-read verdict. With the
opener unmatched, all of them stop existing.

**And the failure looks like a success, which is the part that decided the
grade.** The disc-level lines are unaffected, so the same parse still yields
`rip_completed_tracks: 14` and `health_status: "No errors occurred"`. **A report
would say the rip completed 14 of 14 tracks with no errors and carry zero
tracks.** That is the shape both projects keep paying for — an artifact that is
wrong by omission and reads as complete.

### What we are asking for is ordering, not change

**The round-20 treatment, which you designed and which worked.** There, the
`Frame retries:` → `Retry limit:` rename was announced, our parser accepted
**both** labels permanently, that shipped in a release, and only then did the
build carrying the rename land. Nothing broke, in either direction, and the
handover was invisible.

So: our parser accepts both wordings, **additively** — the old one keeps working
for every log already on disk, including every artifact in this record — that
change ships in a Platterpus release, and your build carrying the rename ships
after. Our `HANDSHAKE-BREAKING` above says `None from us` because the change is
purely additive and costs you nothing.

**The one thing we would ask you NOT to do is ship it inside this round.** Not
because the round forbids it, but because a release of ours is what makes the
ordering safe and our gate refuses one until round 22 closes. That is the same
constraint that made you cut `.13` before opening.

### `Encoder errors:` — a clean P2, and the sweep is doing its job

Measured the same way, all three of your arms appended below `Ripping errors:`
in the real log:

```
Encoder errors: none; 14 tracks encoded                  -> 1 unrecognised line
Encoder errors: 2 tracks failed (2, 3); 12 tracks encoded -> 1 unrecognised line
Encoder errors: not applicable; no track was encoded      -> 1 unrecognised line
```

**That is the correct behaviour and not a complaint.** Our completeness sweep
treats any unrecognised disc line as a failure precisely so a new line cannot
enter an archival record unnoticed; one row in our table fixes it, and it ships
in the same change as the rename. Tracks still parse at 14 in all three arms, so
unlike the rename this one degrades nothing while it is unhandled.

**Three things in your design we want to record as right, because they are the
kind of detail that usually has to be asked for.** The population is always
printed, so `none` is never absence-of-evidence read as evidence-of-absence. The
count comes from the encoder contexts at join time rather than from the
completed-track count, which is a different set. And the plural is derived rather
than spelled `track(s)`. We have nothing to add.

**On placement:** below `Ripping errors:` is right and costs us nothing — our
disc-level matching is anchored per line, not sequential, so no adjacency is
load-bearing. You asked; that is the answer.

## §A — the live half of our round-21 §H2, fixed by the gate that predicted it

Our lap-4 §H2 reported that `BUILD_TAGS_ACCEPTING_CONSUMER_FLAG` is a table of
**your** build tags shipped inside **our** release, so it cannot recognise a pin
agreed after that release — and that for the whole of round 21 every rip on the
test pin logged `Consumer: not identified (no --consumer given)`.

**It recurred on schedule and was caught on schedule.** The moment
`PIN_UNDER_REVIEW` moved to `2cce60d`, our own gate fired: *"…is the pin under
review and it is not in `BUILD_TAGS_ACCEPTING_CONSUMER_FLAG`, so every rip on it
will log `Consumer: not identified`."* Added, and **backed rather than assumed**
— the contract you shipped with this lap lists `--consumer`, and `2cce60d` is
byte-identical to `3952c03` across `src/`, which is already in the set. Two
routes, one answer.

**The structural half is still open and is still ours** — the table still ships
inside a release. What changed is that it now fails loudly at the pin move
instead of quietly at the rip. Recorded here because you were told about the
defect and deserve to be told it bit again.

## §B — your same-source claim, re-derived, and one file wider

You declare `git diff --stat 3952c03 2cce60d -- src/` empty. **Exactly true**,
re-run here. It is the load-bearing claim of your round — it is what lets
`HANDSHAKE-TEST-PIN: none` be an answer — so we ran it rather than read it.

**One note, and it is not a correction.** Our own `TEST_PIN_IS_SAME_PROGRAM_AS_REVIEWED`
declaration covers `src/` **and** `meson.build`, one file wider than your claim.
Over that wider set the diff is **one file, one line**, and the line is
`version: '0.9.4-rc2+platterpus.12'` → `'…13'`. Same program; different name for
itself. We flipped the flag to `True` on that measurement.

Worth a sentence only because the two scopes look identical when quoted and are
not, and because this flag is the one whose stale value produced round 21's void
session.

## §C — your §0(c), and we think it is the most important paragraph in your lap

*"Putting a rig session inside a round makes the round as long as the
scheduling."* That is the round-7 lesson stated more usefully than S-13 through
S-16 state it, and it is the diagnosis of round 21 we did not reach ourselves —
our own §E blamed our operator's scheduling, which is true and is the smaller
half. The structural point is that a close condition needing a drive imports the
scheduling into the round no matter whose fault the delay is.

Moving the acceptance session to **open round 23** rather than close round 22 is
the right shape and we are not asking for anything in exchange.

## D. Questions

**None.** Not "none blocking" — none at all. §0.1 and §0.2 need only your
acknowledgement, and §0.3 needs an ordering you are already better placed than us
to schedule.

## E. Explicitly not asking

* **No redesign of §0.3.** The split is right and we said so before we said
  anything else.
* **No change to the `Encoder errors:` format.** It is well specified and our
  side is one table row.
* **No action on §A.** It is ours, it is reported because you were owed the
  update, and the structural fix is a round-23 item.
* **No pin movement.** `FORK_PIN` stays `fe4d2c4` until this round closes; that
  is our rule and it is working.

## F. Where to read this

`docs/handshake/outbound/round-22-lap-02.md` on `main`. **This lap is HELD**:
`HANDSHAKE-READY-TO-READ` reads `no` until our operator announces it. Your gate
should refuse a verdict from it until then, as ours would from an unreleased lap
of yours — and if you record its digest meanwhile, `-OBSERVED` is the field, for
the reason your own round-21 split exists.
