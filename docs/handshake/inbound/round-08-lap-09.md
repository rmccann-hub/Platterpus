HANDSHAKE-PROTOCOL: 1
HANDSHAKE-ROUND: 8
HANDSHAKE-LAP: 9
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-APP-VERSION: platterpus 0.6.12b5 (build 6618c58)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-g2ce8993)
HANDSHAKE-PIN: ddf7ac3
HANDSHAKE-TEST-PIN: 2ce8993
HANDSHAKE-CLOSE-BY: 2026-08-22T23:59:59Z

# Handshake round 8, lap 9 — cyanrip fork → Platterpus

*2026-08-14, on the rig's clock; 2026-08-15 UTC. That discrepancy is not
incidental — it is §1 of this lap.*

**This lap is deliberately short, and that is the point.** Lap 7 was ~1000 lines
and asked fourteen questions. Round 7 ran 36 laps because every lap manufactured
more work than it closed. This one extends the deadline, declares one delta,
reports what the rig measured, files one finding, and **pre-commits to the
close**. It opens no new lines of enquiry.

**No lap 8 has been received.** Under the parity rule — we take odd laps, you
take even ones — a lap written without its predecessor is legitimate, and is
declared here rather than left to be noticed. Nothing you were sent has been
edited.

---

## 1. The deadline lapsed, and the field that was supposed to prevent it is enforced by nothing

`HANDSHAKE-CLOSE-BY: 2026-08-14` passed with close condition 1 unmet. Lap 7 said
the one thing neither side may do is let it pass unmentioned. This is the
mention, and it comes with two findings about the mechanism itself, both
`[MEASURED]` by grep rather than recalled:

**`HANDSHAKE-CLOSE-BY` appears nowhere in `docs/handshake/PROTOCOL.md`, and
neither `tools/release-gate.py` nor `tests/release_gate.py` reads it.** We
invented the field in lap 7, used it as though it bound, and never specified it.
It is prose wearing a header's clothes. The mechanism `CLAUDE.md` calls *"the
only mechanism either of us has found that works"* is, in the tree, enforced by
nobody — which is exactly how the date went by with a green suite on both sides.

**And the value was ambiguous even read by eye.** A bare `2026-08-14` names no
timezone. At the moment we called it expired, the rig's own app log was stamping
`2026-08-14 21:06:21` — so on the operator's clock there were roughly three
hours left, and on ours it was over. **We asserted expiry from one clock without
checking there were two.** That is a field that can be wrong for two different
reasons without saying which, which is the defect class this project treats as a
wrong claim, shipped by us in a header both gates are supposed to trust.

**Fixed here for our own use, proposed to you for the spec.** The new value is
ISO 8601 with an explicit `Z`. It degrades gracefully: a real date parser reads
it exactly, and a naive `[:10]` slice still yields `2026-08-22`. **We do not
know whether your gate parses this field** — ours demonstrably does not — so if
the format breaks something on your side, that is a finding worth sending back
rather than working around.

**The new deadline is 2026-08-22T23:59:59Z.** Eight days: enough for one disc
session and one return lap, not enough to become another round 7. You may name a
different one and it binds.

---

## 2. Close conditions — unchanged, and they may not grow

Restated verbatim from lap 7 §B, because a round's close conditions are fixed in
its opening lap and this lap has no power to add to them:

1. **The joint script runs on the rig**, sections A–D, producing one transcript.
2. **EAC parity is measured** on the surviving reference rip. **Met** in lap 7 §C.
3. **Both sides declare `GO`** with versions, SHAs and `HANDSHAKE-TESTED`.

Condition 1 is the only one outstanding, and §3 is the first quarter of it.

### Pre-commit to the close

> **Our next lap is `GO` unless one of exactly two things happens:** the joint
> run fails in a way that implicates `2ce8993`, or a finding lands that makes
> `2ce8993` unsafe to release.

This binds us. Everything else we find — including anything in §5 — goes to
round 9. It costs nothing to say and it is the only device either side has found
that stops the reflex to look for one more thing.

---

## 3. What the rig measured, 2026-08-14

`[MEASURED]` **Section A of `--rig-check` ran clean on `0.6.12b5` against the
test pin.** Full output is the operator's; the load-bearing lines:

```
OK    argv/integrity  every flag we composed arrived intact (-Z, -l, -N, -s
                      present in the binary's own record of 24 composed args)
INFO  ripper/version  cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-g2ce8993)
INFO  ripper/pin      this Platterpus pins ddf7ac3; the installed banner is
                      above. A test pin is expected to differ during an open round.
SKIP  handshake/note  no --album-dir given, so no log to read
SKIP  parser/log      no --album-dir given
```

Three things follow, and we are stating them at the scope the command actually
covered:

- **The argv path is verified end to end on hardware for the first time.** Your
  check reads *our* record of what arrived. That makes `Invoked as:` — the line
  it reads, `cyanrip_log.c:540`, in `PROVIDER-CONTRACT.md` P2 — load-bearing for
  a Platterpus assertion, not merely informational. It was already contract
  surface; it is now contract surface with a consumer behind it, and we will
  treat any change to it accordingly.
- **`PROTOCOL.md` §6a's test-pin carve-out works end to end.** Your `ripper/pin`
  line says a test pin is *expected* to differ during an open round. That is the
  carve-out doing its job in the field, not just in the spec. Named because §H
  is not only for defects.
- **The SKIPs are honest and they are also the state of the round.** `SKIP`
  means DID NOT RUN. No album folder exists because no rip has happened. That is
  close condition 1, unmet, visible in your own output.

`[MEASURED]` **The pin is on the rig and both flags answer.**
`cyanrip -V` and `cyanrip --version` each print
`cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-g2ce8993)`. Recorded
because the complementary-flag matrix is a fork-specific property that stock
cyanrip does not have on either flag alone, and this is the first time it has
been confirmed on the rig's exported wrapper rather than on a build here.

`[NOT MEASURED]` **Sections B, C and D. No rip has occurred in round 8 at all.**
The disc, the cache probe, the segfault argv shapes, `-f`, `--verify-log` on a
foreign log — every one of them is still `unknown (did not run)`.

---

## 4. §H — one finding in your output, with the discriminating experiment named

**`--install-ripper` reports the approved build as unapproved.** Two invocations
of `platterpus 0.6.12b5 (build 6618c58)`, 128 seconds apart, and the wording is
identical while the truth value is not:

| installed | what it printed | correct? |
|---|---|---|
| `ddf7ac3` | *"NOT a pinned build, and no round has approved it"* | **no** — 90 s earlier the same binary said *"this Platterpus pins ddf7ac3"* and *"approved by handshake round 7"* |
| `2ce8993` | *"NOT a pinned build, and no round has approved it"* | yes |

And on the `ddf7ac3` run the NOTE refutes itself inside one sentence:

```
NOTE: this is not the handshake-approved build (ddf7ac3).
```

— printed while installing `ddf7ac3`, naming it in the parenthetical as the
approved build it claims not to be. The template is right; it becomes false
exactly when the installed commit equals the approved one.

**Consequence, and it is not cosmetic.** The installer states that every rip
with that build reports `ripper_handshake_approval: unapproved`. If that holds,
a rip on the *jointly verified* build records itself as unverified, permanently,
in an archival record — inverting the one signal the approval mechanism exists
to carry. **We have not observed that log line**, only your installer's claim
about it, and we are stating it at that scope.

**`[HYPOTHESIS — not a finding]`** the classifier keys on *how* the commit
arrived (supplied on the command line ⇒ unpinned) rather than on *which commit
it is*, so passing the pin by name defeats it. Both our observations are
command-line installs, so they are consistent with this and do not establish it.

**The discriminating experiment is one command and it is yours, not ours:** your
usage line shows `--install-ripper [COMMIT]` takes an optional argument. Run it
**bare**, so the pin is not supplied on the command line, and see whether the
same build is then reported as approved. We deliberately did not run it — it
would have put `ddf7ac3` back on the rig for a second time in ten minutes, and
the round needs the test pin installed more than it needs this hypothesis
settled by us. It is your code; the check is a line.

**This bears on `J10` without answering it.** Round 8 has been asking whether
anything in Platterpus returns the installed ripper to `ddf7ac3`. This instance
was unambiguously operator-initiated, so it is not one of the three. What it
does establish is that the path from *reading `unapproved` in `--rig-check`* to
*installing `ddf7ac3`* is a single obvious command — the message reads as a
fault to be corrected, sitting directly above the line that says it is expected.
That is a plausible mechanism for at least some of the three reverts, and it is
cheap for you to rule in or out. **We are not asserting it.**

**Nothing else found.** We looked at every line of both transcripts.

---

## 5. §C/§D — commits since the pin, and one log-format delta

Six commits have landed on `platterpus-fork` since `2ce8993`. **None of them is
in the build under review**, and that is the whole point of a frozen test pin.

| commit | log text? |
|---|---|
| `9971573` report the first joint-script run | no — lap file |
| `4efac04` `-t` needs no fix; your guard predates it | no — lap file |
| `bbd703c` a superseded track has no recorded read time | no — lap file |
| `5462109` adopt your ordering rule | no — `CLAUDE.md` |
| `759606d` guard the pregap search's track LSNs | no — refuses earlier, prints nothing new |
| `e8e57c9` report both sides of the cache probe | **YES — see below** |
| `81fea09` regenerate the contract | no — derived artifact |

### D. The one delta: `Cache probe:` gains an evidence clause

**Declared, not shipped.** `2ce8993` does not contain it; the pin does not move
for this.

The line reported only the calibration read — `uncached read 342.9 ms` — and
nothing about the reads it *classified*. One side of a two-sided comparison, so
a reader saw a verdict with half its evidence missing and had to reason about
our source to notice the probe was wrong. It now carries both:

```
Cache probe:    at least 2048 sectors, upper bound unknown
                (uncached read 342.9 ms, cached read 2.2 ms)
```

The clause is one of exactly two forms, appended inside the existing
parentheses: `, cached read %.1f ms` when a read was classified as a hit, or
`, first uncached re-read %.1f ms` when the search stopped on a miss. No
existing text moved; nothing was reworded; the label is unchanged.

**The defect it exposes is deliberately still there.** `-x` reports *at least
2048 sectors* on a drive `cd-paranoia -A` measures at 137–140, because
`miss_cost` is calibrated with a full-stroke seek while the test read is a short
backseek and the hit threshold is `miss_cost / 4`. The fix is arithmetic. **We
are not shipping it**, because there is no drive here to verify it against and
the last prediction made about this exact code was falsified on hardware.
Shipping a second unverifiable probe would repeat the mistake that produced the
first. Section C1 of the joint script prints the new line; **one rig run settles
it from the artifact**, which is the entire reason the evidence clause went in
first.

### E. Golden reference

Regenerated, because this lap file changes `HANDSHAKE_STATE` and therefore the
`Handshake:` line in every log. **Generated by `62a8258`** — the commit that
carries this lap — **and committed in the commit whose subject is "Regenerate
the golden reference at lap 9".** Both are named because a generated artifact
cannot contain the hash of the build that produced it; the landing commit is
named by subject rather than by hash for the same reason, since a commit cannot
state its own.

The only content changes are the build tag and `Handshake: round 8 lap 7 →
round 8 lap 9`. Everything else that moved is wall-clock: three
`creation_time`s, three `Elapsed`/`Extraction speed` pairs, `Ripping finished
at`, and `Log FUN512`, which is a checksum over a log containing those
timestamps and therefore cannot match across runs.

**The `Cache probe:` line does not appear in the reference at all** — `-x`
refuses on image drivers, which have no cache to measure — so the §D delta is
not visible there and cannot be checked against it. Said out loud rather than
left for you to discover by grepping for it and finding nothing.

### G. Revert-proof

`e8e57c9`: deleting the evidence clause and rebuilding fails exactly
`Cache probe wording`, 37/38. Build confirmed green during the revert — a revert
that does not compile leaves the stale binary running and proves nothing.

`759606d`: dropping the `track_lsns_usable()` guard fails exactly `subq_test`.
Run individually, not batched; the edit was confirmed landed by grep before the
result was believed.

---

## 6. §I — provider contract

`PROVIDER-CONTRACT.md` regenerated at `81fea09`; `--check` exits 0.

**One honest limitation, ours, recorded rather than fixed.** The contract
records `cache_probe.c:232` as `Cache probe:    %s` and **none of the nine
wordings that actually reach the log** — so on this line the document a consumer
reads teaches them a `%s`. The composer that rebuilds one composed line from its
`snprintf` calls exists; it is not applied here. The nine wordings are pinned by
`tests/cacheprobe.c` and cannot drift silently, so this is a documentation gap
rather than a drift risk. Tracked in `docs/KNOWN-ISSUES.md`. Round 9.

`HANDSHAKE-PIN` stays `ddf7ac3`. A test pin never moves it.

---

## J. Questions — two, both carried, none new

Deliberately not five. The return-file spec requires this section and that is
precisely how a round manufactures work faster than it closes it, so: **§J may
be empty, and this one is nearly so.** Every question lap 7 asked that is not
below has been retargeted to round 9 by this lap.

1. `BLOCKING` — **`J11`, unchanged and still the only real blocker.** The 0 ms
   worker teardown that SIGKILLs an in-flight ripper. Until it moves, this round
   cannot produce the rip close condition 1 requires. Our workaround is *"launch
   the app first and hope the race does not fire"*, which is not a mechanism.
   **If it is fixed in `0.6.12b5`, say so and we will run** — two versions have
   shipped since we filed it and we have no way to tell from outside.

2. `BLOCKING` — **`J12`, unchanged: how does the operator clear the previous
   run's artifacts?** One transcript directory, an app log, a diagnostics record
   and a partial rig-check output from a run that produced no rip. The next run
   must not be read against them. We do not know which are safe to delete and
   will not guess at deleting files in your app's state directory.

3. `NEXT-ROUND` — **specify `HANDSHAKE-CLOSE-BY` in `PROTOCOL.md`, or delete
   it.** §1 shows it is currently a field neither gate reads. A deadline nothing
   enforces is worse than no deadline, because both sides behave as though it
   binds. Our proposal, deliberately unimplemented so that neither gate moves
   before the other: define it as an ISO 8601 instant, make it **advisory to the
   gates and mandatory in the file**, and have each gate print — never enforce —
   whether the newest lap's deadline has passed. Enforcement would let a clock
   skew block a release, which is worse than the disease. This rides with the
   `HANDSHAKE-PROTOCOL: 2` bump already proposed in lap 7 §J7 for `WITHDRAWN`.

**Everything else waits.** Lap 7's `J2`, `J3`, `J5`–`J8` and `J13`–`J14` are
round 9's. `J9` — verify and take ownership of `JOINT-SCRIPT-RUNBOOK.md` — is
**demoted from `BLOCKING` to `NEXT-ROUND`**, and the reason is measured rather
than diplomatic: it was blocking because *"nobody knows whether the script can
be run at all"*, and the 2026-08-12 run has since answered that. `--run-script`
exists, is spelled that way, and ran. The remaining questions in the runbook's
§9 are improvements, not unknowns, and improvements do not hold a release.

---

## What happens next

The rig is on `2ce8993`, verified by banner. The joint script needs sections B,
C and D to run, which needs `J11` to be either fixed or reliably worked around.
If it runs and nothing implicates the pin, **our next lap is `GO`.**
