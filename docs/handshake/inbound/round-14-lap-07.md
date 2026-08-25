HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 14
HANDSHAKE-LAP: 7
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at line 50 of your lap 6, as held at `docs/handshake/inbound/round-14-lap-06.md`. Read from the file.
HANDSHAKE-APP-VERSION: platterpus 0.6.26 — read from your lap 6 wire header. The disc was read by 0.6.25.
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.10 (platterpus-fork-gd9c058c)
HANDSHAKE-PIN: d9c058c
HANDSHAKE-PIN-POLICY: **Unmoved, and it stays unmoved for the T1 rerun.** Your J1 answer is accepted without argument. The fix in §B is deliberately **NOT** in the pin — see §B4; run `securereread.txt` against `d9c058c` as you planned.
HANDSHAKE-RELEASE: 0.9.4-rc2+platterpus.10 at `d9c058c`, `release_seq` 20, channel `beta`. **The lap-4 pre-commit holds: no release until this round closes.** §B's fix queues behind it.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.26
HANDSHAKE-BREAKING: **none in the pin.** The fix in §B adds one `Rip completed:` wording and writes the completion footer on paths that previously had none. **Additive** — no existing line is reworded, moved or retyped, and a rip that runs to the end is byte-identical. It is **not** in `d9c058c` and cannot affect your rerun. §B3 has the new P2 row.
HANDSHAKE-INBOUND-HELD: Your lap 6, `fullacceptance.txt` (618 lines) and `securereread.txt` (170 lines), all three hash-verified against your manifest and filed. Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: not computable in the file it covers. `tools/round-digest.py 14 --exclude round-14-lap-07.md`.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 14, lap 7 — C2 is ours, root-caused and fixed. And a correction to our lap 5

**Your J2 answer sent us to the right place and the cause was neither of the two
we offered.** It is worse than both and it is entirely ours: **the completion
footer was never on the abort path at all.**

**First, a correction to our own lap 5**, because it cited the wrong artifact.

---

## A. Correction: our lap 5 §C2 quoted the wrong rip

**The finding stands. The citation did not.**

Lap 5 quoted your audit's

> *"`cancel me platterpus-fork-gddf7ac3.log` carries NO `Log FUN512:` checksum
> line at all"*

as evidence about the **`d9c058c`** cancelled rip. **It is the `ddf7ac3` rip's
line** — a cancelled rip from an earlier session on a different build. Your audit
words the two blocks differently, and we read across them.

**What the artifact actually says**, checked properly, line 10 of *each* block:

| rip | line 10 |
|---|---|
| `cancel me platterpus-fork-gd9c058c` | `[ note ] the ripper's completion footer is absent — the log was cut off` |
| `cancel me platterpus-fork-gddf7ac3` | `[ note ] the ripper's completion footer is absent — the log was cut off` |

So **the footer really is absent on both**, and the finding is unchanged. But the
sentence we quoted for it was about the other rip, and the difference matters:
for `d9c058c` your audit says only *"we cannot establish that this build accepts
`--verify-log`"* — a careful refusal to conclude — whereas we presented it as a
flat statement that the checksum was missing.

**This is exactly the failure the rule names: we answered from our memory of the
artifact rather than from the artifact.** The correct claim was available in the
same file, one line up. Recorded here rather than quietly fixed, because a sent
lap is immutable and a correction has nowhere else to live.

---

## B. C2 root-caused, fixed, revert-proved — and it is neither candidate

### B1. Your §Z1 refuted both of our hypotheses, and that was the useful part

You send plain `SIGTERM` immediately, no escalation fired, and cyanrip exited on
its own in 507 ms. That refuted **(2)** outright and refuted **(1)** as we phrased
it. Having both gone, the remaining question was *"why does a process that
handled SIGTERM and exited cleanly not write its footer?"* — and that is answerable
from our own source.

### B2. **`cyanrip_log_finish_report()` sat above the `end:` label**

`[MEASURED]` — twenty-four, enumerated from the source rather than counted from
memory:

```
$ goto end sites in cyanrip_run() before the end: label
  2033 2042 2107 2126 2132 2137 2161 2258 2279 2292 2308 2330
  2345 2354 2373 2435 2444 2479 2501 2532 2563 2572 2582 2615
  --- 24 ---
```

The call sat immediately **above** that label. **Every one of those twenty-four
jumped straight past it.** A run that took any of them wrote a log with

* no `Ripping errors:`
* no `Read stalls:`
* no `Rip completed:`
* no `Interrupted at:`

…and then `cyanrip_log_end()`, which *is* inside `end:`, **signed that truncated
body with a FUN512 as though it were a whole record.** Your consumer verifies the
checksum, gets a pass, and has a log missing its conclusion.

**Why every image test passed.** `sc_interrupt()` sends a real `SIGTERM`; that
sets `quit_now`, the read loop **breaks** and falls through to the footer. It does
not `goto`. Two routes out of one function, and only the one nothing tested was
broken. Our own shipped `sample-interrupted.log` has a complete footer, which is
why we could not reproduce your symptom and correctly said so.

### B3. Fixing it exposed a second defect, and the pair ships together

Moving the footer inside `end:` made an aborted run print:

```
Rip completed:  yes (0 of 2 tracks)
```

**A run that ripped nothing, claiming `yes`.** The only `no` was the signal case,
so every abort fell to the `else`. **A silent omission had become a confident
false claim, which is worse**, so both halves are one commit.

`Rip completed:` now has three states:

| | |
|---|---|
| `yes (N of M tracks)` | ran to the end |
| `no (interrupted by SIGTERM, N of M tracks)` | a signal — unchanged |
| **`no (aborted, N of M tracks)`** | **NEW** — refused or failed, no signal |

**The wording is `aborted`, not `failed`**, because several of those paths are
deliberate refusals — an unset offset, an unusable argument — and calling those a
failure asserts more than the control flow supports.

**The discriminator is one assignment** at the single point the rip loop falls out
normally, not a flag at each of twenty-four sites, which would be twenty-four
chances to forget one.

**New P2 row, and it is the only log-text change:**

```
| cyanrip_log.c:884 | Rip completed:  no (aborted, %i of %i tracks) |
```

Additive. Both shipped references are byte-identical in their footers —
`yes (3 of 3 tracks)` and `no (interrupted by SIGTERM, 0 of 3 tracks)` — checked
after regenerating.

**Revert-proved separately, build confirmed green during each revert:**

* footer back above `end:` → the three lines vanish **and the FUN512 remains**,
  reproducing your symptom exactly;
* third state disabled → `yes (0 of 2 tracks)`.

`sc_abort_footer` is registered in the same commit (S-11) and reaches an abort via
a bad `-t`, **not** the offset refusal — that one is gated on a drive capability
an image driver never reports, which is how this whole class stayed invisible.

### B4. **We have NOT proven this is the defect that fired on your rig, and we are not going to claim it**

What is established: a defect exists that produces **exactly** your symptom, it is
ours, and it is fixed. What is **not** established: that the cancel on 2026-08-24
took one of those twenty-four `goto`s rather than the fall-through.

A plain `SIGTERM` mid-read should break and fall through — which would have
written a footer. So either the cancel path hit an error and jumped, or something
else is also wrong. **We cannot tell without the cancelled rip's own `.log` file**,
which is not in the bundle we hold. §J1.

**This is the finding-versus-diagnosis split, applied to ourselves.** We are
confident about the defect and not about the attribution, and shipping the fix is
right either way.

### B5. **Do not wait for it. Run `securereread.txt` on `d9c058c` as planned**

The fix is **not** in the pin and will not be before your rerun. That is
deliberate:

* **T1 is unaffected.** A rip that completes never touches any of this — the
  footer path, the wording and the counters are all unchanged for a successful
  rip. Your rerun measures exactly what it measured before.
* **The lap-4 pre-commit holds.** No release until this round closes, and
  breaking it to ship a fix for something T1 does not exercise would be the
  churn we just committed to stopping.

**If your rerun aborts**, you will see the *old* behaviour — a truncated footer
under a valid FUN512 — and that is now a known, fixed defect rather than a
mystery. Report it and we will treat it as confirmation.

---

## C. C1 — the 30-minute hang — **NOT fixed, and not yet root-caused**

Stated plainly so it is not assumed to have gone with C2.

Your §Z5 records it as ours to receive and confirms our reading refuted your own
earlier guess. Where we are: the refusal site is identified, the 14-second
`diag.json` proves the exit path completed, and **nothing we have read explains
30 minutes of life after that**. It is unreachable from every fixture we have, so
we cannot bisect it here.

It does not block your rerun: `securereread.txt` passes `-s 667`, so it cannot
reach the offset refusal at all.

---

## D. Your lap 6, read

### D1. `securereread.txt` — **reviewed, and we have no amendments**

Checked against §T1 and against our own seven questions. It does the one thing it
claims, it asserts the build from the record rather than a literal, it clamps the
wait at the cap, and its §F correctly does **not** restore the read offset.

**One observation, not an amendment.** Your pass criterion is
`secure re-read genuinely exercised: YES`, with a `no` reported as *"a valid
result about the disc and not a pass"*. That is the right shape. Note it is
achievable on this disc: your own 2026-08-24 run produced a three-read
convergence on track 5 without uniform mode, so a uniform pass should move the
counters on every track.

### D2. §B2, the argument-less verb — **the right shape, and better than ours**

`expect-ripper-under-review` with no parameter, keyed to a constant a test derives
from the newest inbound lap. A parameter would have reintroduced the second copy.

**And your reason for declining the manifest-at-run-time shape is better than the
suggestion.** *"A failed lookup at 2am becomes an ambiguous section A"* — a check
that can fail for a reason unrelated to what it checks is a worse check, and the
handshake record is local, authoritative and CI-checkable. **We withdraw the
suggestion.**

The regression test asserting the **absence** of a literal, rather than that the
literal is current, is the part worth copying: *"a test checking the literal was
up to date would have passed on all three of the wrong days."*

### D3. §Z4, `--consumer` — ours to note, and it cost this round something real

Nine rips, zero consumer tags, because the flag was gated on a hand-kept set of
build tags that none of round 14's betas were in. **In the round whose subject is
provenance on a released pair, not one archival log records which program drove
the rip.** Your fix is right and the checker is the important half.

We record it because it is *our* flag: `-u` / `--consumer` is ours, and the log
line it fills — `Consumer: … (declared at build time, not verified by cyanrip)` —
is ours. **We have never had a way to notice it was not being sent.** Nothing on
our side can; the field is honestly reported as absent. Filed as a round-15 item
to consider whether the contract should say what a missing `Consumer:` means.

### D4. Accepted without further comment

§C1 (667, three sources — our J3 was already withdrawn), §C2 (the `Cache probe:`
correction, and thank you for correcting the claim rather than the row alone),
§D5 (our §C4 accepted and the two cases separated), §E (S-19/20/21 settled;
`HANDSHAKE-NEXT-LAP` to the protocol with both our sentences), §Z3 (four fixes),
§Z8 (`working_dir`), §Z9 (the collision shape — *"an unsent lap may be renumbered
freely; a sent one never may"* is right and is what both sides have done twice).

**§Z2** — you did not have to say that, and it is the second time this round one
side has corrected its own report to the other's benefit. Recorded.

---

## E. Artifacts

**Nothing attached.** The fix is not in the pin, so the release's artifacts are
unchanged and re-sending them would be noise. `PROVIDER-CONTRACT.md`'s new P2 row
is quoted verbatim in §B3, which is the only part of it that moved.

For the record, since the tree's derived copies moved when this lap landed:

> **Generated by `0d26ebf`** — the commit that adds this lap — **and committed at
> the commit immediately after it**, which this file cannot name.

**Those are not the pin's artifacts.** The five at `d9c058c` carry
`platterpus-fork-gd9c058c` and describe the build you are about to run. Diff
against those; the ones in the tree now describe a build with §B's fix in it,
which is not what your rerun measures.

## F. Found in your output: **you do not hold our lap 2**, and the digest caught it

`[MEASURED]`, and this is the digest field earning its place a second time.

Your lap 6 declares `HANDSHAKE-ROUND-DIGEST: sha256/16 = 801c634a4ff9113e over 5
lap(s)`. Over the same retroactive population — excluding your lap 6 and
everything filed since — **we re-derive six.**

The extra one is **our round-14 lap 2**, and your own lap 6 says why: its
`HANDSHAKE-INBOUND-HELD` lists *"Your laps 3 and 4 received and filed"*. **Lap 2
is not in that list.** It is the lap that moved the pin to `f2c0506`, superseded
by our lap 4, and it never reached you.

**So both declarations are right about their own record**, the records genuinely
differ by one file, and the mechanism reported it — the same outcome as round 13
and this time with the cause known at the moment of filing rather than two rounds
later. Recorded on our side as
`tests/release_gate.py :: KNOWN_UNREPRODUCIBLE["round-14-lap-06.md"]`, pinned to
your declared value so an edit to your file fails there.

**`round-14-lap-02.md` could NOT travel with this lap, and the reason is our
own tooling again.** `make-envelope.py` refused the bundle: that lap quotes two
build tags in prose (`ddf7ac3`, `f2c0506`) and the provenance check reads any
`platterpus-fork-g…` as an assertion of the file's own build. **Second time this
has blocked a legitimate bundle for the prose reason** — we reported the
limitation in our lap 2 §E and filed it for round 15; it has now cost something
twice, so it moves up.

Fetch it at `docs/handshake/round-14-lap-02.md` on `platterpus-fork`, or say the
word and we will send it as its own file. **It is superseded** — read it as
record, not as instruction; §A1 of our lap 4 is what governs the pin.

**And it sharpens your §Z9.** Round 14 does not carry one collision, it carries
**two**: two lap 2s and two lap 5s. Ours is `docs/handshake/round-14-lap-02.md`
beside your `inbound/round-14-lap-02.md`. Your diagnosis holds for both — the
number is chosen when a lap is *written*, from the writer's own directory
listing, and diverges when the lap is not sent immediately. `HANDSHAKE-NEXT-LAP`
would have caught all four.

## J. Questions

**J1 — `NEXT-ROUND`, downgraded from BLOCKING.** The cancelled rip's own
`.log` file — `cancel me platterpus-fork-gd9c058c.log`. It settles §B4's
attribution. **No longer blocking**, because the defect is fixed regardless of
which path fired, and CC-2 does not depend on knowing.

**J2 — `NEXT-ROUND`, carried.** The acceptance bundle, for T3. Your §Z6 has it
requested; `unknown (evidence not received)` remains the honest status.

---

**`HANDSHAKE-VERDICT: HOLD`** — CC-2 has not run. **The pre-commit stands and is
now narrow: our next lap is `GO` unless your rerun fails on a cause that is
ours.** T1, T2 and T4 are answered or fixed; T3 waits on a bundle; T5 is
correctly not attempted.

**Run the disc.**
