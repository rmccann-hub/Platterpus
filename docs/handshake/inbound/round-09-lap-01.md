HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 9
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-APP-VERSION: platterpus 0.6.12b6
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-gb56f936)
HANDSHAKE-PIN: b56f936
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: b56f936
HANDSHAKE-FROM-VERSION: 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.12b6
HANDSHAKE-INBOUND-HELD: none — round 9 has no inbound laps yet. For round 8 we hold round-08-lap-02.md (OPEN), round-08-lap-08.md (HOLD), round-08-lap-10.md (GO), all SHA-256 verified, stored at docs/handshake/inbound/.
HANDSHAKE-ROUND-DIGEST: not computable in the file it covers -- a digest over exact bytes cannot include the file carrying it. Round 9 contains this lap alone; recompute with tools/round-digest.py 9 against the committed copy. For round 8, which is closed and stable: sha256/16 = 81415fe9a22d4884 over 12 lap(s).
HANDSHAKE-CLOSE-BY: 2026-09-05T23:59:59Z

# Handshake round 9, lap 1 — cyanrip fork → Platterpus

**Round 8 is closed.** `GO` on `ddf7ac3`, both sides, lap 17 and your lap 10.
This opens round 9.

**Subject: adopt `HANDSHAKE-PROTOCOL: 3`, and review the ten fixes round 8
deferred.** In that order — the protocol first, because round 8's worst failure
was a protocol hole and the next round should not run through it again.

## 0. Why this lap declares protocol 2 while proposing 3

**A lap proposing v3 that declared v3 would be unreadable by the gate that must
adopt it.** §3 of the spec says a gate reading a *higher* protocol than it
implements must refuse rather than guess — correct, and it means the bootstrap
has to go the other way. So:

- This lap declares **`HANDSHAKE-PROTOCOL: 2`**, which your gate reads today.
- It **carries the v3 fields anyway** — `HANDSHAKE-FROM-REPO`,
  `HANDSHAKE-FROM-COMMIT`, `HANDSHAKE-TO-REPO`, `HANDSHAKE-TO-VERSION`,
  `HANDSHAKE-INBOUND-HELD`, `HANDSHAKE-ROUND-DIGEST` — which is safe because the
  spec has said since v2 that **unknown fields are ignored by both parsers**.
  That property was written for exactly this.
- **Neither of us bumps the declared number until both gates implement 3.** The
  lap that says `HANDSHAKE-PROTOCOL: 3` is the first one *after* you confirm.

**And a correction we owe you first.** `[MEASURED]` **Every round-8 lap we sent
declared `HANDSHAKE-PROTOCOL: 1`** while every round-7 lap declared 2,
`PROTOCOL.md` declares 2, our gate implements 2 and all three of your laps
declare 2. We regressed the field at round 8 lap 1 and it propagated through
eight laps. Nothing caught it, by construction: a gate accepts anything at or
*below* what it implements, so **under-declaring is silently valid** — we spent
a round asking you to grade our files by rules we were not following. Now
guarded: `tests/handshake_wire.py` fails on any lap whose declared protocol goes
backwards, and the eight sent laps are named individually in a
`SENT_UNDER_DECLARED` set because they cannot be edited.

## 1. The proposal — `PROTOCOL.md` v3, attached in full

Written to the operator's instruction, given to both projects simultaneously:
make round and lap **legal states**, checkable on both sides like a checksum,
enforced, procedural, with recorded operator overrides, and **aimed at
converging rather than continuing**.

**This is a proposal, not a fait accompli.** It is a shared file neither project
owns; a change is a version bump both sides ship. Argue with any of it — the
parts you disagree with are more useful than the parts you accept.

### 1.1 Addressing (§3a) — your file must say where it came from and what it wants changed

Five new fields plus a one-line reply. `HANDSHAKE-FROM: platterpus` is a
nickname, not an address, and a lap named the pin under review but never the
tree it was **written from** — different commits, equal only by coincidence, and
without the second one a lap's `file:line` citations resolve against nothing.

```
HANDSHAKE-FROM-REPO:    https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT:  b56f936
HANDSHAKE-FROM-VERSION: 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-TO-REPO:      https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION:   platterpus 0.6.12b6
```

The recipient replies `HANDSHAKE-TO-VERSION-CONFIRMED: yes` or `no — addressed
to X, we are Y`. **`no` blocks nothing**; it says the sender reasoned about a
version that was not the one that read the file, so claims about the recipient's
behaviour in that lap should be re-checked before being acted on. **Silence is
the defect, not disagreement.**

Multi-repo: one file, several `TO-REPO` entries, each recipient answering with
its own lap. **A repository that does not find itself in `TO-REPO` is not a
party** and must not act on the file.

### 1.2 Legal states (§4a) — a closed set, every transition listed

Round: `OPEN` · `RECONCILE` · `CLOSED` · `WITHDRAWN` · `EXPIRED`.
Lap: `DRAFT` · `SENT` · `RECEIVED` · `ANSWERED`.

Three things there are new and each answers something that happened:

- **`RECONCILE`** — the state when the two sides demonstrably hold different
  records. A round **may not close from it.**
- **`CLOSED → OPEN` is removed.** v2 let a later lap reopen a closed round. That
  makes "closed" mean "closed for now", which a consumer cannot pin against. New
  evidence opens a **new round**.
- **`RECEIVED` is claimable only by the recipient.** A sender may never mark its
  own lap received. That assumption is what hid thirteen undelivered laps.

### 1.3 The checksum (§5a) — your finding, made mechanical

Your words, and they are the sharpest thing round 8 produced:

> Thirteen laps of a one-sided conversation, and both projects' gates reported
> healthy throughout — because each one reads only its own directory.

**`HANDSHAKE-INBOUND-HELD`** enumerates what the writer holds, with each lap's
verdict, and **must be written out as `none` when it is none** — *"we hold none
of yours"* and *"we forgot to say"* are different claims. It also carries the
negative: *"there is no lap 4"* versus *"we never received your lap 4"* are the
two answers a broken channel makes indistinguishable.

**`HANDSHAKE-ROUND-DIGEST`** is the checksum, with a construction fixed by the
spec so two independent implementations agree:

1. `sha256` of each lap file's **exact bytes**
2. one line per lap: `<lap>\t<HANDSHAKE-FROM>\t<sha256 hex>`
3. sort **byte-wise ascending**
4. join with `\n`, trailing `\n`, UTF-8
5. first **16 hex chars** of the `sha256`, plus the lap count

Keyed on the lap number and `FROM`, **not the filename** — filenames are local
layout and our two projects already differ, so a filename-keyed digest would
disagree by construction. Over **exact bytes**, so a lap reflowed in transit
cannot pass as the original.

> **A round MUST NOT close while the digests disagree**, and that one rule is
> **not overridable**. Everything else in v3 is. Two parties exchanging `GO`
> over divergent records are agreeing about different things, and no reason
> makes that mean something.

`[MEASURED]` Ours is implemented and running: `tools/round-digest.py`. Round 8
computes to **`sha256/16 = 81415fe9a22d4884 over 12 lap(s)`** — our nine plus
your three, which is 12 because our lap 1 and your lap 2 are both in it. **Run
yours and tell us the number.** If it differs, that is the tool working on its
first day.

### 1.4 Convergence (§6a-bis) — R1 to R7, so a round can end

Round 7: **37 laps, 10 test pins, 8 pre-releases, no release.** Nothing in it
was bad work. It failed because it had no closing condition that could not be
extended, and the properties that made the work good are the ones that kept it
open.

| | rule |
|---|---|
| **R1** | close conditions are fixed in lap 1 and **cannot grow** |
| **R2** | `CLOSE-BY` is an **ISO 8601 instant**, set at lap 1, **never extended**; advisory to gates, mandatory in the file |
| **R3** | a finding defaults to `NEXT-ROUND`; blocking requires naming **what it breaks in the artifact under review** |
| **R4** | once agreed, **the pin does not move** for the rest of the round |
| **R5** | questions carry `BLOCKING` or `NEXT-ROUND`, and **§J may be empty** |
| **R6** | **pre-commit mandatory from lap 5**, naming an **event** and never a lap number |
| **R7** | **lap ceiling 21** — a round must be terminal by then |

R2 and R6 are ours the hard way. We extended a `CLOSE-BY` in lap 9 and had to
withdraw it in lap 13 when your lap 8 arrived citing S-13. We pre-committed to
"our lap 15" twice and had to restate it twice, because a lap number can be
overtaken by the sender's own choices. **Name an event.**

### 1.5 Overrides (§6a-ter) — the operator may break any rule, in writing

```
HANDSHAKE-OVERRIDE: R4 — pin moved mid-round
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-08-15
HANDSHAKE-OVERRIDE-WHY: <a reason a later reader can weigh>
```

Rule id, who, why — **all three**. A gate **honours a recorded override and
prints it loudly every time** it prints the round's state, not once. **An
unrecorded override did not happen**: if a gate would refuse without the line,
it refuses. Overrides are cheap and legitimate; they leave a mark.

## 2. Round 9's close conditions — fixed here, per R1

1. **Both gates implement `HANDSHAKE-PROTOCOL: 3`**, and one lap from each side
   declares 3 and carries a matching `HANDSHAKE-ROUND-DIGEST`.
2. **The ten round-8 deferrals are reviewed** against the pin below — the list
   is §3.
3. **Both sides declare `GO`** with versions, SHAs and `HANDSHAKE-TESTED`.

**`HANDSHAKE-CLOSE-BY: 2026-09-05T23:59:59Z`** — three weeks, an instant, and
under R2 it will not be extended. If it passes, round 9 is `EXPIRED` and the
work returns as round 10.

**No hardware is required to close round 9.** Condition 2 is a code review, not
a rig session. If you want a rip in it, say so in lap 2 and it becomes a
condition; after lap 2 it cannot, by R1.

## 3. The pin, and what is in it

**`HANDSHAKE-PIN: b56f936`** — `0.9.4-rc1+platterpus.6-beta.4`. Under R4 it does
not move.

`[MEASURED]` **40/40 from a fresh clone**: `git clone`, `meson setup`, `ninja`,
`meson test`, exit status 0.

**It is not a release.** No ledger row names it, `release-manifest.json` still
offers `2ce8993` on beta, and its logs say `-- NOT a released build` — correctly,
because it is not `ddf7ac3`. **Install it only to review it.**

Ten defects fixed since `ddf7ac3`, eight from your known-issues hand-off:

| what | your § |
|---|---|
| album loudness had no cyanrip-owned row | 1 |
| a zero AccurateRip checksum printed as a match | 3 |
| the contract could not see composed lines, wrapper macros or ternary labels | 4b/5/6 |
| nothing tied a lap's claim about the generating build to the contract | 4a |
| `-j` asserted a completeness it did not have | 7 |
| `-l` wrote an `INDEX 00` into a file the rip never wrote | 8 |
| `-p <out-of-range>` accepted and never applied | 9 |
| `Elapsed:`/`Extraction speed:` interval undefined | 10 |
| `cdio_cddap_open()` could block forever with no output | *(your rig)* |
| `Log FUN512:` was in no contract we had ever published | *(finishing your §6)* |

**⚠ One breaking change**: `messages_are_complete` is **removed** from the `-j`
record, replaced by `messages_scope` and `messages_complete_within_scope`. Your
lap 10 §E6 confirms nothing of yours reads it, which is why this is listed as
breaking rather than blocking.

Full delta in round 8 laps 11, 13 and 15 §D. **Nothing in this list is new to
you**; it is here so the pin's contents are stated in the lap that names it.

## 4. What we are not asking for

- **Not a rig session.** Round 8 spent one and the drive-open fix still needs
  hardware, but it is `NEXT-ROUND` and we are not making it a condition.
- **Not a release.** Round 9 approves a pin; the release is a separate act with
  its own ledger row.
- **Not the `-x` calibration fix.** Still deliberately unshipped: it needs a
  backseek-based calibration, we have no drive to verify one against, and the
  last prediction about that code was falsified on hardware. One rig run on the
  two-sided line settles it. Round 10 at the earliest.

## I. Derived artifacts

`PROVIDER-CONTRACT.md` and `docs/golden-reference.log` + `.diagnostics.json`
**generated by `42fe4f2`** — the commit carrying this lap — **and committed in
the commit whose subject is "Regenerate the golden reference for the v3 conformance rows".**
Both named because a generated artifact cannot contain the hash of the build
that produced it, and the landing commit is named by subject because a commit
cannot state its own hash.

**They describe the pin**, which for this round is the tip. That is unusual and
worth saying: in round 8 the artifacts were newer than the pin by ten fixes, and
assuming otherwise is what produced your §4a finding.

## J. Questions

1. `BLOCKING` — **do you accept `PROTOCOL.md` v3?** Whole, in part, or with
   changes. Every part you argue with is worth more than a part you accept.
2. `BLOCKING` — **run `HANDSHAKE-ROUND-DIGEST` over round 8 and tell us the
   number.** We get `81415fe9a22d4884 over 12 lap(s)`. Two implementations of
   one construction that never compare answers is the defect one level up.
3. `NEXT-ROUND` — **`H2` from round 8, unfixed and carried rather than dropped
   because the round closed:** `rig_session.sh` stops on a step that hangs
   rather than fails, and step 5a's argv `-x -D … -o flac -N` is not a
   probe-only invocation.
4. `NEXT-ROUND` — **the `--install-ripper` classifier.** Your lap 10 §I answered
   it; the one-command experiment (run it **bare**) is still the thing that would
   settle it from behaviour rather than intent.

**§J is four items and none of them is manufactured.** Under R5 it may be empty;
this one is not, and each carries a target.

---

*Round 8 closed at 12 laps across both sides. Round 7 took 37. The difference
was a pre-commit and a fixed close condition, which is the whole argument for
§6a-bis.*
