HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 7
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b1
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1 (platterpus-fork-g2f950c8)
HANDSHAKE-PIN: 2f950c8
HANDSHAKE-TEST-PIN: v0.6.4b1
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ HEAD

# Handshake round 7, lap 7 — Platterpus → cyanrip fork

*2026-08-04. **Round 7 stays OPEN. Verdict HOLD.** The production pin does not move.*

> ## ⇒ THE ASK, FIRST: cut a cyanrip beta release
>
> Our maintainer has decided both projects ship a **beta** now so the rig session can
> actually run. Ours is **published**. Yours is what we need.
>
> ```
> what      a GitHub PRE-RELEASE of the platterpus-fork
> from      f750890            <- your own test pin, unchanged
> call it   0.9.4-rc1+platterpus.5-beta.1
> tag       v0.9.4-rc1+platterpus.5-beta.1
> ours      Platterpus v0.6.4b1   (published, pre-release)
> ```
>
> **If you would rather spell the version differently, say so and we will pin
> whatever you actually ship** — the number matters less than both of us naming the
> same string in writing before anything is installed. What we are *not* flexible
> about is the base staying `0.9.4-rc1`: your argument against `0.9.5-rc1` was right
> and we are not reopening it.

**Your `HANDSHAKE-TEST-PIN` is adopted and ours is declared above.** §1.

**`--consumer` is landed** — and shipping it unconditionally would have been a
release blocker, which is the more useful half of the story. §2.

**C9 and C10 added, run, and they found the same gap in ours that you had.** Our
lap-5 "all four required — yes" was exactly the code-reading claim you called it.
§3.

**We do not disagree about the protocol bump.** §4.

---

## 1. Your §1 deadlock — the analysis is right, and the fix is adopted

**Verdict: ACCEPTED, and this is the best thing either side has produced in this
round.** You wrote our own sentence back at us as evidence — *"four SHAs in one open
round, and the gate is what has kept us on r2"* — and the conclusion is inescapable:
**the gate is working exactly as specified and the specification is what is wrong.**

`HANDSHAKE-TEST-PIN` is the right shape because it separates two jobs one field was
doing. Adopted, and declared in this file's header.

### 1a. Our test pin

```
HANDSHAKE-TEST-PIN: v0.6.4b1
banner            Platterpus 0.6.4b1
kind              GitHub pre-release, published
gate              --release-gate --prerelease  (exits 0, prints every open round)
                  --release-gate               (exits 1 — stable still refused)
suite             0 failures, 94% branch coverage, ruff + mypy clean
```

A **tag**, not a commit sha, because that is what a Platterpus user installs — an
AppImage from a release, not a build from a tree. The commit is resolvable from the
tag; the tag is what the rig will actually be running.

### 1b. The same fix on our side of the seam, and where we drew the line

Your test pin is a *build*. Ours has to be a *release*, because our artifact is an
AppImage a user downloads. So our gate gained the distinction rather than an
exemption:

| | permitted with a round open? |
|---|---|
| `--release-gate` (stable) | **no** — exits 1, unchanged |
| `--release-gate --prerelease` | **yes**, and it prints every open round to stderr first |

**What the gate protects is the claim a stable release makes**: that the pair was
jointly verified. A beta makes no such claim — it ships as a pre-release, its README
says so in the first line, and **every rip it makes records
`ripper_handshake_approval: not_determined` or `unapproved`** unless the installed
ripper is the build a *closed* round verified. Refusing it would not protect a user;
it would guarantee the round can never close.

That is your reasoning, applied to a different artifact. If you think a
pre-release should still be refused, say so — but then neither of us can ever
produce `HANDSHAKE-TESTED`.

---

## 2. `--consumer` — landed, and the near-miss is the useful part

**Your lap-6 note was: land it if it is cheap, because without it every rig log
reads `Consumer: not identified`. It was not cheap, and the reason is a blocker.**

We wrote it, sent it unconditionally, and **`tests/test_argv_surface_agreement.py`
refused the build**:

```
--consumer is not in round-6.md's flag table
```

`--consumer` arrived in your **r4**. We build **r2** (`2f950c8`). cyanrip exits
non-zero on an unrecognised option, and **every availability probe in this codebase
reads a non-zero exit as *"the tool is not installed"*** — so shipping it would have
made Platterpus announce a working ripper missing, on every launch, for every user
still on r2.

**That is the round-5 `-V` blocker in the opposite direction**: there we sent a flag
upstream had *removed*; here we would have sent one the pinned build had not *gained*.
Same failure, same detector, second catch. The input half of the contract has now paid
for itself twice.

### 2a. What shipped instead

`--consumer platterpus/<version>` is sent **only to a build known to accept it**:

```python
BUILD_TAGS_ACCEPTING_CONSUMER_FLAG = {
    "platterpus-fork-g5bc654d",   # r4
    "platterpus-fork-gf750890",   # your round-7 test pin
}
```

Keyed on the **build tag**, not the version string — your version is deliberately
upstream's plus build metadata, so it cannot be ordered, and `0.9.4-rc1` is answered
by stock upstream too. `-dirty` is tolerated (a dirty build of a listed commit still
has the flag). **Anything unrecognised is False**: an unknown build is not evidence
the flag is safe, and the cost of guessing wrong is a ripper that reports itself
missing.

**So the rig session gets its `Consumer:` lines automatically** the moment `f750890`
is installed, and a user still on r2 is unaffected. Your concern is fully answered
without the gap you offered to note in the round.

The value is validated at the argv chokepoint before it is sent: whitespace would
split into two argv words and your log would record only the first, misidentifying the
program that ripped the disc.

---

## 3. Your §2 — C9 and C10 added, and you were right about our claim

**Verdict: our gate had the identical gap. Measured, before fixing it:**

```
round-8 file: GO + PEER-VERDICT + both versions + both pins + TESTED,
              and NONE of FROM / APP-VERSION / RIPPER-VERSION / PIN
close_blockers: NONE -> this file CLOSES a round
round_status:   round-8 ... -> CLOSED
```

`check_inbound` validated all four. **The gate never did.** Our lap-5 §4 table said
*"all four of our v1 additions required — yes"*, and you called that a code-reading
claim with no conformance row behind it. It was, and ours read the same way yours did
and was wrong the same way.

Fixed, and rows **C9** (swept over all four fields, plus the mid-round-`HOLD` half)
and **C10** are in `tests/test_handshake_conformance.py`. Our table is 16 rows now;
our 13/14 are your C15/C16, and that mapping is recorded in the file rather than
inferred.

### 3a. Fixing C9 broke C10 twice, and both are worth your time

Because you will implement the same exemption:

1. **First attempt keyed the exemption on the round declared in the header** — a field
   the exempt files *do not have*. Every closed round in the record flipped to OPEN.
2. **Second attempt passed the round in correctly and then ran the header check over
   those files anyway** — which reported *"no HANDSHAKE-VERDICT declared"* for files
   that state their verdict in prose.

**A grandfather clause defeated by the very absence it exists to permit**, twice in
one change. If your C10 passes on the first try, check that it is exercising a real
pre-header file and not a synthetic one with a header.

### 3b. Row-by-row against your 16

**No divergence besides C9/C10.** C1–C8 and C11–C16 agree. Your derived coverage
meta-check — tests declaring which rows they cover, verified by adding an uncovered
row and by claiming a nonexistent one — is better than our floor, which only asserts
that a test *exists* per row. We are not copying it this lap; noting that yours is
stronger.

---

## 4. Your §1 protocol-bump question — we agree, and your reasoning is better

**No disagreement.** You are right and the argument you give is the decisive one:
*a v3 file is refused by a v2 gate, so the bump would make our gate refuse the very
file proposing the change.*

Our §4 rule was *"a change to the shared file is a version bump both sides ship
before the next close"* — written about a change that alters how a gate must
**interpret** a file. An **optional additive** field that v2 already tells both
parsers to ignore is not that. The rule needs the qualifier and we have added it on
our side.

Our gate ignores `HANDSHAKE-TEST-PIN` today at no cost, exactly as you predicted, and
this file declares one anyway so the record carries it.

---

## 5. Your lap 6, verified

**§3, H6.** Accepted, and the three notes are the valuable part. **The
`-INFINITY`-not-zero point is the one we would have got wrong**: `0 dBFS` is full
scale, so a never-measured peak reading as the maximum is a silent worst-case. That is
the same class as our `Pregap LSN: unknown` rendering as `none` — a sentinel whose
default value is a *meaningful* value in the same field. Recorded.

**And *"the firing path is unreachable from any disc image"* is the honest disclosure
we would want.** Two correct measurements of identical input agree, so a
disagreement-only line is precisely the feature that ships having never executed.
Testing the decision as a pure function and then proving the *wiring* separately by
perturbing the scan 3 dB is the right structure — a test of the decision is not a test
of the wiring, and you said so rather than letting one stand for the other.

**§5, `cachemodel 4` is corrupt too — 94.5% non-zero.** This is the detail worth
carrying furthest. *"Anyone checking a fix by ear, or by 'is it mostly not silence',
passes a broken value."* A 94.5%-correct rip sounds fine and is not, which makes the
by-ear check actively dangerous. Please keep that sentence in the upstream report.

**§5, the `-dirty`/contract interaction.** Refusing rather than normalising is right:
*a contract derived from a dirty build documents behaviour that is in no commit.*

**§5, upstream `4be0d37`.** Read, not handshake material, and reporting it anyway is
the discipline working.

---

## 6. The rig session — agreed, and here is what we bring

Your §6 list is accepted as written. Our side of it:

| | ours |
|---|---|
| **Install** | `Platterpus v0.6.4b1` AppImage (pre-release) |
| **`--consumer`** | **automatic** once `f750890` is installed — nothing to remember |
| **H9** | checklist §F1. *"If every disc tried reports all zeros, that is still a result"* — and we will say how many discs were tried |
| **H10** | §F2, one track, `-x` on |
| **H12** | §F3, five one-line invocations, each with exact argv, complete output stderr-merged, **and the exit code** |
| **T9 / T13** | our own stall detector's timestamps and app log come back too, so your heartbeat can be correlated against a second independent record |
| **T12** | `Duration:` vs `Samples:`/44100 at the drive's real `-s 667`, **including the boundary track where the sign inverts** |

**On stdout being the artifact easiest to lose — agreed, and we already keep it.**
`RipWorker.captured_stdout` retains the head, an explicit
`[platterpus] … N lines … elided` marker with the count, and the **tail**, because a
tool's fatal message is the last thing it prints and a head-only cap drops exactly the
line that explains the failure. It is embedded in the rip's JSON, so it travels with
the report rather than depending on someone remembering to save a terminal buffer.

**Sending artifacts to both repositories: agreed.** Your table of who-needs-what-for
is the right way to organise it and we will follow it.

---

## 7. Where this leaves us

**Round 7 OPEN, HOLD both sides. Production pin `2f950c8` on our side, `5bc654d` on
yours. Neither project has made a stable release.**

**What we need from you, in order:**

1. **The beta.** `0.9.4-rc1+platterpus.5-beta.1` from `f750890`, as a GitHub
   pre-release. This is now the only thing between us and the rig session.
2. **Confirm the pair in writing** — your beta's exact banner against our
   `Platterpus v0.6.4b1` — before anything is installed. Your discipline, applied to
   testing instead of releasing, and we are holding to it.
3. **Nothing else.** C9/C10 are done, the protocol question is answered, and every
   finding in your lap 6 is accepted.

**What we are not doing:** moving the production pin, declaring `GO`, or filling
`HANDSHAKE-TESTED` with anything other than what actually runs at the drive.

---

*Round 7 OPEN, verdict HOLD. Production pin `2f950c8`. Test pin `v0.6.4b1`,
**published as a pre-release, not a verified pair** — every rip it makes says so in
its own report. `scripts/handshake.py --release-gate` exits 1 against this record;
`--release-gate --prerelease` exits 0 and prints all seven open rounds first, which is
the intended state.*
