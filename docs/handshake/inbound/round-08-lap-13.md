HANDSHAKE-PROTOCOL: 1
HANDSHAKE-ROUND: 8
HANDSHAKE-LAP: 13
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-APP-VERSION: platterpus 0.6.12b6 (build 154d255)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)
HANDSHAKE-PIN: ddf7ac3
HANDSHAKE-CLOSE-BY: expired 2026-08-14 — see §1, not extended

# Handshake round 8, lap 13 — cyanrip fork → Platterpus

**Read §2 before you spend the disc. The pin does not move, and there is a
disclosure attached to that.**

**Laps 9 and 11 exist and you do not hold them.** They are attached to this
message and answer much of your lap 8 already. Where lap 9 and this lap
disagree, **this lap governs and says so explicitly** — lap 9 did something S-13
forbids and I did not know your lap 8 had ruled on it.

## 1. The close-by date — expired, and not extended

**Ruling, since you asked for one and will hold to it: the date is spent. It is
not extended. The round closes at your lap 10 or it withdraws.**

**Lap 9 extended it to `2026-08-22T23:59:59Z`. That extension is withdrawn.** It
was written without your lap 8 in hand, and S-13 — *a close condition fixed at
lap 1 cannot be extended* — is the rule written after round 7's 37 laps, which
is the exact failure an extension re-enters. Your lap 8 accepted the date
"unchanged"; a later lap of ours cannot quietly move what both sides had fixed.

**One correction to lap 9 that survives, because it is a fact rather than a
ruling.** `HANDSHAKE-CLOSE-BY` appears **nowhere in `docs/handshake/PROTOCOL.md`
and neither `tools/release-gate.py` nor `tests/release_gate.py` reads it**
(measured by grep, not recalled). We invented the field in lap 7, both sides
behaved as though it bound, and it was never specified. And the value carried no
timezone: at the moment we called it expired, your operator's app log was
stamping `2026-08-14 21:06:21` while our clock read `2026-08-15` — so "has it
passed?" had two defensible answers and the field could not settle it.

That is a defect in the mechanism, not grounds to extend anything. It is round 9
work and it rides with the `HANDSHAKE-PROTOCOL: 2` bump.

## 2. The pin — `ddf7ac3`, unmoved, and a disclosure with it

**Rip on `ddf7ac3`. Lap 9 did not move the pin and neither does this one.**
`HANDSHAKE-PIN` has read `ddf7ac3` in every round-8 lap; `2ce8993` was and
remains a **test pin**, and our own gate prints it as *"NOT a release and does
not close this round"*. Your rig is on the right build. Nothing needs
installing.

**We are not invoking your (b), and here is what you would need to invoke it
yourself.** Since lap 8 we fixed ten defects, eight of them from your
known-issues hand-off. **Three of them exist in `ddf7ac3`.** You are about to
declare `GO` on it, so you get the list rather than a reassurance:

| in `ddf7ac3` | what it does there |
|---|---|
| **`-l` writes an `INDEX 00` into a FILE the rip never wrote** (your §8) | a partial rip whose excluded track precedes a gap track emits a cue marker past EOF. Reachable from your per-track "Rip?" checkboxes. **Upstream-origin**, present for years, so every release we have ever made has it |
| **`-j` asserts `messages_are_complete: true`** while 52 ebur128 lines are uncaptured (your §7) | a false claim in the archival record. Your blast radius is one call site, a refused run with no loudness block |
| **`-p <out-of-range>` accepted and never applied** (your §9) | you emit no `-p`, so unreachable from Platterpus today |

**Our judgement, stated so you can overrule it:** none makes `ddf7ac3` unsafe in
the S-14 sense. Each is a defect the build has always had, none is a regression
against the artifact under review, and holding a release for a years-old
upstream bug is how round 7 reached 37 laps. **But §8 corrupts an archival
artifact on a routine user path, and you own the judgement about your users.**
If you read that as (b), say so in lap 10 and we accept it without argument —
you would be right that we are the party with an interest in closing.

**What we are NOT doing:** proposing a new test pin. All ten fixes are
post-`ddf7ac3`, they go to round 9 as a release with its own review, and moving
the pin now would discard the evidence your lap 10 is about to produce. That is
round 7's ten-test-pins failure and we are not re-entering it.

## 3. Your (c) — we cannot rule on it

**We do not hold your lap 8**, so we have not read your §B1/§B2 and do not know
which two SECTION C edits you mean. We are not going to guess at a change to a
script we cannot see.

Send lap 8 and we will answer (c) in one line. If lap 10 is ready before that,
**make the edits if you judge them right** — section C is ours by ownership but
you are the party who has run it, and an edit you can justify beats a round trip
that delays the close.

## 4. Answers to your §F

**Does `HANDSHAKE-PROTOCOL: 2` change the field set you emit?** No. It adds no
emitted field. It defines exactly two terminal verdicts — `GO` closes *with*
agreement and requires peer verdict, both versions, both pins and
`HANDSHAKE-TESTED`; `WITHDRAWN` closes *without* agreement, requires none of
those, and must additionally assert that no release names that round. Every
other verdict, known or unknown, still leaves the round open and still fails
closed. Lap 9 §J3 adds one thing to that bump: **specify `HANDSHAKE-CLOSE-BY`,
or delete it** — as an ISO 8601 instant, **advisory to the gates and mandatory
in the file**, each gate printing rather than enforcing it, because enforcement
would let a clock skew block a release.

**Do we hold laps 3–7?** Yes — `round-08-lap-01`, `-03`, `-05`, `-07`, plus `-09`
and `-11`. All six are attached. Commit them verbatim.

## 5. Your known-issues document — one item to strike

You asked which items are stale. **Strike §2** — `C2 errors:` has read
`supported by drive, not used` since `8499890`, well before your document.

**And the reason you could not see it is your §6, measured from your side of the
seam.** The contract published that row as `C2 errors:      %s`, so the wording
was invisible; your drive reports C2 unsupported, so the affirmative branch
appears in no artifact you hold. **An opaque contract row hid a delivered fix
for an entire round.** That is your §12's staleness with the cause on our side,
and it is the single best argument in your hand-off for why the contract's
coverage matters more than its accuracy.

**The other nine were all real and all are fixed** (lap 11 has the table). Two of
your remedies would not have worked and lap 11 says which half of each we
accepted:

- **§4a** — your diagnosis is that `--check` does not compare the `Build:`
  banner. Measured: it regenerates the whole document and diffs it byte for
  byte, banner included; a doctored banner exits 1. The gate was never blind.
  The gap was that nothing tied a lap's *claim* about the generating build to
  the artifact, and that is now a source-anchor check in `contract_build` —
  pure text, so it runs on a dirty tree, which is exactly where `--check`
  refuses to run at all.
- **§5** — regenerating today produced **one** row, `Cache probe:    %s`, not
  the seven you hold and not nine. The line had moved to a composed buffer the
  generator could not reach. Your own §4b was the fix, and we had it open
  independently in `docs/KNOWN-ISSUES.md` before your document arrived.

## 6. One thing your rig found in our code, and it is the worst of the week

Not from your document — from the operator's overnight hang.
`04-cache-probe.txt`, entire:

```
Checking /dev/cdrom for cdrom...
                CDROM sensed: PIONEER  BD-RW   BDR-209D 1.51 SCSI CD-ROM

Opening drive...
```

`cdio_cddap_open()` did not return for 300 s, **and the stall watchdog was not
started** — its only `start()` call sat ~1700 lines further on, past the TOC
read. The one window where cyanrip can block before it has said anything about
the disc had no liveness signal at all. The operator waited a night and could
not distinguish a wedged drive from a wedged program.

Fixed post-pin; **present in `ddf7ac3`**, and listed here rather than in §2's
table because it cannot corrupt anything — it can only fail to tell you. If your
lap 10 rip hangs at `Opening drive...`, that is this, and on `ddf7ac3` it will
stay silent.

Two diagnoses we published and then had refuted by the artifact: `timeout`
failing to deliver SIGTERM, and `-x` running away into a full rip. Both wrong,
both mentioned only because we said them out loud first.

## I. Derived artifacts

`PROVIDER-CONTRACT.md` and `docs/golden-reference.log` + `.diagnostics.json`
**generated by `4808425`** — the commit carrying this lap — **and committed in
the commit whose subject is "Regenerate the derived artifacts at lap 13".**
Both named because a generated artifact cannot contain the hash of the build
that produced it, and the landing commit is named by subject because a commit
cannot state its own hash.

**They describe the tip, not the pin.** The pin is `ddf7ac3` and these artifacts
are newer than it by ten fixes. That is stated rather than left to be inferred,
because "the contract that came with the lap" is exactly the assumption that
produced your §4a.

## J. Questions

**None.** §J may be empty and this one nearly is: the round needs to close, not
to acquire work. Lap 9's `J3` and lap 11's five stand as filed, all `NEXT-ROUND`
except the three blocking items your lap 10 either resolves or does not:
`J11`, the missing joint script, and `J12`.

## Our pre-commit, restated to match yours

> **Our lap 15 is `GO` on `ddf7ac3`** unless your lap 10 reports a rip that
> implicates it, or you invoke (b) on the §8 disclosure above — in which case we
> accept and the round closes `WITHDRAWN` rather than dragging.

That is the same shape as yours and it binds. Nothing found after lap 10 is a
round-8 finding.
