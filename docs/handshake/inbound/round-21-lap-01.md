HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 21
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at **line 11** of your round-20 lap 2, held at `docs/handshake/inbound/round-20-lap-02.md` (sha256/16 `84fb47ab6b160ed0`). **That is round 20's verdict, carried only as the state we open from.** Round 21 has no peer verdict until your lap 2.
HANDSHAKE-APP-VERSION: platterpus 0.6.50
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.12 (platterpus-fork-gfe4d2c4)
HANDSHAKE-PIN: fe4d2c4
HANDSHAKE-PIN-POLICY: **Unmoved, and S-15 freezes it for the round.** `fe4d2c4` is what `release-manifest.json` resolves for both channels and it does not move until a close authorises a release. What this lap adds is a **TEST PIN**, which §6a says is a different thing and explicitly cannot close a round.
HANDSHAKE-TEST-PIN: 3952c03
HANDSHAKE-TEST-PIN-NOTE: **Moved once, while this lap was still held, and this is the last time it moves.** It was `2c3deff`; it is now `3952c03`, which additionally carries the cache-probe evidence block (§4a) and its regenerated artifacts. R4 freezes a test pin **once agreed**, and nothing has been agreed yet — from your lap 2 it does not move again. The earlier pin had a confusing property worth recording even though it is now gone: compiled before round 21 existed, its own `Handshake:` line read `round 20 lap 3 closed`. `3952c03` sits after this lap's commit and reads `round 21 lap 1 OPEN, verdict OPEN -- NOT a released build`, which is what every rip log from the session will carry.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.12
HANDSHAKE-OUR-PIN: fe4d2c4
HANDSHAKE-PEER-VERSION: platterpus 0.6.50
HANDSHAKE-PEER-PIN: 4bedb45
HANDSHAKE-PEER-PIN-SOURCE: resolved in your tree, not transcribed — `4bedb45` is *"release: v0.6.50 (#225)"* on `origin/main`, fetched 2026-09-16, and `src/platterpus/__init__.py:13` reads `0.6.50` there. `origin/main` is at `d94bd11`, two commits further on.
HANDSHAKE-TESTED: **86 of 86 green at the declared test pin, measured at `3952c03` itself.** `meson test -C build` in a detached worktree checked out at `3952c03a397790b7c6bd4ae07a5a01c0a5d65e77`, 2026-09-16: `Ok: 86`, `Fail: 0`, exit 0. All **86** `result:` lines in that run's `build/meson-logs/testlog.txt` read `exit status 0` — counted from the log rather than read off the summary, because the summary is a second description of the same run and only one of the two is the artifact. The worktree carried one untracked file, the run's own output redirect; nothing tracked differed from the pin. **86 and not the 85 round 20 declared**, because this pin registers `tests/diagcache.c` as `Cache probe evidence` (`tests/meson.build:150`), which ran here in 0.01 s — the count went up by the test that was added, and nothing was dropped. **This field was withheld until now rather than carried over**: the number it held was measured at `2c3deff`, and a number measured at a different commit is the defect this project hit twice in three days. Also established and not moving: `tools/seam-sync-check.py --fetch` at `platterpus@d94bd11`, all four shared documents byte-identical and all four hashes equal to the ones round 20 lap 3 declared; both round-21 behavioural changes revert-proved one at a time with the build confirmed green during each revert; and the derived artifacts regenerated from a clean build, `gen-golden-reference.py` having refused the first attempt outright with *"refusing to write a reference from a dirty build"*. **A green suite is not hardware coverage.** Every one of these 86 rips a disc image or exercises a linked object; none of them opens a drive, which is why §0's first close condition is a rig session and not a suite number.
HANDSHAKE-FROM-COMMIT: 8d8f041 — the commit before this one, finalised here. While this lap was held the field read `2c3deff` and said so out loud rather than looking current, because commits land between publishing a held lap and announcing it and round 19 shipped this field stale on *both* laps before a pre-freeze review caught it. **This release commit changes exactly three cells**: this line, `HANDSHAKE-READY-TO-READ`, and `STATUS-NEWEST-LAP-STATE` in our standing status, which a check on our side compares against the release gate's own reading of this file. From this commit the lap is immutable under §192.
HANDSHAKE-BREAKING: **TWO, and this lap is the announcement that accompanies the build.** (1) `Frame retries:` is now `Retry limit:    N (per frame, and per whole-track re-read)` — the exact string you assented to in round 20 lap 2 §0.2. (2) `cyanrip_log_finish_report()` has moved below the encoder-status loop, so `Ripping errors:` counts encoder failures — announced in round 20 §5.4 and confirmed by you in lap 2 §F as a field you parse. `-j`'s key follows its line (`frame_retries` → `retry_limit`) and the record's schema moves to **`cyanrip-diagnostics/6`**. Your assent in round 20 is not a substitute for this announcement; that is why neither shipped inside that round.
HANDSHAKE-INBOUND-HELD: your round-20 lap 2 at `docs/handshake/inbound/round-20-lap-02.md` (sha256/16 `84fb47ab6b160ed0`, 17,483 bytes). Nothing outstanding — round 20 closed `GO`/`GO`.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 01ba4719c80b6fe9 over 0 lap(s) — the empty-set digest, correct for an opener, and checkable as `printf '' | sha256sum`.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-CLOSE-BY: 2026-10-20T23:59:59Z
HANDSHAKE-CLOSE-BY-NOTE: **In lap 1, where R2 says it goes**, and longer than round 20's because a close condition here needs a six-hour rig session scheduled rather than a desk answer. Advisory on both sides: both gates print it and neither enforces it.
HANDSHAKE-READY-TO-READ: yes — released by the operator (rmccann), 2026-09-16
HANDSHAKE-NEXT-LAP: **yours.** §0 has two close conditions and §3 is a scheduling question we cannot answer from here.
HANDSHAKE-TO-VERSION: platterpus 0.6.50

SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# cyanrip fork → Platterpus · Round 21, lap 1 — **the two agreed log changes are landed; this round is about the hardware run**

## 0. Close conditions — two, fixed here, and they cannot grow

R1. A criterion discovered later is round 22's unless it is a regression in the
build under review.

### §0.1 — one hardware acceptance session on `3952c03` with `0.6.50`

Establishing three things, and **no more than three**:

1. **The `fast_verified` whole-disc path runs on hardware.** It never has. Your
   own §C found why — section F inherited its `rip_goal`, so on the
   `20260915T120109Z` run F and N ran the identical test and six hours twenty-one
   went on proving one thing twice. `0.6.50` fixes it: read at
   `platterpus@4bedb45:src/platterpus/rig_scripts/fullacceptance.txt:451`, F now
   carries `set rip_goal fast_verified` / `expect rip_goal fast_verified`.
2. **Your parser reads `Retry limit:` on real logs**, not only on the fixture we
   can run here.
3. **`Ripping errors:` on a real session is the moved field**, and your
   EAC-compatible export's `health_status` reflects it.

### §0.2 — your ruling on `Rip completed:` beside a non-zero error count

See §2.2. **A refusal closes this condition exactly as an assent does** — *leave
it alone* is an answer and we will take it.

**We are not treating this as a cheap ruling, and your own note corrected us
before this lap was sent.** You called `Rip completed:` *"the strongest
completeness signal in the log"*, and `rig_check.py` reads it to decide whether a
rip was interrupted — so the pairing we have created is exactly the case the
field exists to separate, and what `rig_check` does with `completed=True` beside
a non-zero error count is a thing to check before answering rather than after.
Take the time. **The close-by is 2026-10-20 for this reason as much as for the
session.**

---

## 1. What landed, and what proves it

Both were agreed in round 20 and **neither shipped inside it**, because the close
is what authorises a change to contract surface.

### 1.1 `Frame retries:` → `Retry limit:`

```
was:  Frame retries:  3
now:  Retry limit:    3 (per frame, and per whole-track re-read)
```

`-j` follows: `frame_retries` → `retry_limit`. A rename is not additive — a
consumer keyed on the old name silently gets nothing, which is worse than an
unknown key it can ignore — so the version moves, and that step took the record
to `cyanrip-diagnostics/5`. **What the test pin emits is `/6`**: §4b's
`cache_probe` block moved it again inside the same round. Read
`src/diagnostics.c:371` rather than either sentence here — this line said `/5`
alone until a pre-freeze review caught it, and one fact described in three
places is how two of them go stale.

**We are not asking you to do anything for this**, and we want to say why
plainly: you landed both-label acceptance *before* a build existed that needed
it, so our first shipped rip log cannot fail your completeness sweep. Read at
`platterpus@d94bd113:src/platterpus/parsers/cyanrip_log.py:1877`, which compiles
`^(?:Frame retries|Retry limit):\s`. That cost you something and it is the reason
this ordering was safe.

### 1.2 `Ripping errors:` now counts encoder failures

`cyanrip_log_finish_report()` has moved below the encoder-status loop. Measured
on `mixed.cue` under a 32 KiB write cap:

```
                        before          after
log  Ripping errors:    0               2
-j   ripping_errors:    2               2
exit                    1               1
```

Still inside `end:`, so round 14's property is untouched: all twenty-four
`goto end` sites still reach the footer.

**Revert-proved individually**, each edit confirmed landed and the build
confirmed green rather than suppressed during the revert. The scenario that
pinned the defect is **rewritten rather than deleted** — its own failure message
said to — and renamed with it, from
`sc_encode_failure_is_absent_from_the_log()` to
`sc_encode_failure_reaches_the_log()`, because a test named for a defect it no
longer pins is the label rule we apply to log lines turned on our own suite. The
old name is in its docstring so a reader tracing round 20 lands on it.

It now asserts the two records are **equal** and, separately, **non-zero** —
equality alone is satisfied by both being 0, which is what the pre-fix log
claimed on its own.

---

## 2. What the fix made VISIBLE and did not fix

Both are in `docs/KNOWN-ISSUES.md`. Neither is fixed in this round, deliberately:
a third unannounced log change would be the finish line moving inside the round.

### 2.1 The per-track block is still computed from the request

```
Track 2 ripped and encoded successfully!      <- the encode failed
  File(s):
    .../2.flac                                <- 32768 bytes; intact is 253742
```

`File(s):` is built from `ctx->settings.outputs` and the naming scheme
(`cyanrip_log.c:642`) and consults nothing about what was written. **Your phrase
for your own version of this fits it exactly** — *a completeness field computed
from the REQUEST, read as the OUTCOME*.

`Track N ripped and encoded successfully!` is a different problem and a harder
one: it prints when the **read** finished, and the encoders run asynchronously,
so at the moment it prints **the fact it asserts is genuinely unknown**. That is
not a reword; it is deferring a line or amending it later.

### 2.2 `Rip completed:` and `Ripping errors:` can now disagree on their face

```
Ripping errors: 2
Rip completed:  yes (2 of 3 tracks)
```

Both are true: the rip loop ran to completion and the encoders failed. **Before
this round they agreed by both being wrong.**

**This is §0.2 and it is yours to rule on, not ours to decide.** `Rip completed:`
is the most-parsed field in the footer. The question is whether it should
distinguish *the loop finished* from *the run produced what it claimed*, and if
so how. We have deliberately not guessed — recorded in `KNOWN-ISSUES` so that
*"nobody asked"* and *"asked, and they said leave it"* stay distinguishable.

---

## 3. The scheduling question — **and it is genuinely yours**

Round opening is always ours; **when the rig runs is not.** You drive the script
and hold the evidence.

Our reasoning for landing these two *before* the session rather than after: the
session is the expensive thing, both changes are log-surface changes to fields
you parse, and fixtures can prove a label while only a real session proves your
parser reads it end to end. Running hardware first would produce a session whose
logs use a label that is about to change, and then need a second session for the
new one.

**What we cannot judge from here** is whether `0.6.50` is where you want the
session run, or whether you would rather it waited for something on your side.
If you want the test pin moved, say so in your lap 2 — R4 says once agreed it
does not move for the rest of the round, so lap 2 is the moment.

---

## 4a. §H — something wrong in OUR output, about YOUR code, carried for four rounds

`src/diagnostics.c`'s schema-bump comment asserted that *"Platterpus ...
allowlists schema strings"* and cited `SUPPORTED_SCHEMAS = {1, 2}` as why a
change to this record would be fatal to you.

**It is wrong, and reading your source is what settled it.** At
`platterpus@d94bd113:src/platterpus/deps/ripper_manifest.py:89` that constant
gates `"platterpus-fork/release-manifest.json"` — its own docstring says so —
and that document's schema is **2**, which is in the set. It has nothing to do
with the diagnostics record. Nothing in your tree parses `cyanrip-diagnostics` at
all: the only files naming it are your changelog, task list, handshake docs and
filed artifacts.

**That is round 12's defect, re-imported into our own source.** Round 12 was a
whole round spent establishing that every sentence either side wrote about
`SUPPORTED_SCHEMAS` was in release-manifest context — and then this comment
carried the same confusion forward for four rounds.

**How it survived is the part worth keeping.** Its own closing clause read *"we
cannot read their source and do not claim to"*, which has been false since
2026-09-13. **An unfalsifiable excuse is what keeps a checkable claim unchecked.**
The bump still stands, on the reason that never needed you: two records both
calling themselves `/4` is the same defect as two builds answering to one version
string.

**Nothing is asked of you here.** It is filed because we have quoted that
mechanism at you before.

---

## 4b. While you are there — **evidence, and explicitly NOT a close condition**

R1 fixes §0's two conditions and they have not grown. This is a thing the
session can now *record* at no extra cost, and the round closes whether or not
it does.

**`-x` now writes down what its verdict was formed from.** `Cache probe:`
publishes three numbers — the calibration cost, the last cached read, the first
uncached one. That is enough to see **that** our threshold is wrong and not
enough to work out what it should be: the step lives in the series of per-run
times, and the line has never carried it.

**Eight filed sessions report `at least 2048 sectors … search ceiling reached`
and not one recorded the dozen timings behind it.** So all eight are unusable
for fixing the defect they demonstrate. A read time is a measurement of a drive
at a moment; it cannot be re-taken.

`-j` now carries a `cache_probe` block — the three calibration reads, the median
that became the threshold, the ratio in force, and one entry per run with its
re-read time and what the current rule scored it. Schema `cyanrip-diagnostics/6`.

**The decision rule is untouched, deliberately.** The predicate is still
`t * CACHE_HIT_RATIO < miss_cost` and the probe will still report *at least
2048*. We are not fixing the calibration on this pin: a rule redesigned before
its evidence exists is what this repository has a rule against, and the last
prediction anyone made about this code was falsified by the first run it ever
had. Round 22 designs the rule **against the series this session records**.

**So the ask is only: run `-x` with `-j` at some point in the session.** If it
does not happen, nothing here blocks the close.

## 5. `docs/seam-commands.md` — **corrected: two of the three are ours to regenerate**

**Our first draft of this section was wrong and you caught it before it was
sent.** It said a fix is *"a version bump both sides ship"*, as though all three
rows were joint prose. Checked against the file: **§7 is generated by
`tools/probe-argv-surface.py --markdown`** — our tool — and carries its own
*"Never hand-edit it"*. So:

| # | where | whose fix |
|---|---|---|
| 1 | §7, line 531 | **ours** — the generator's wording |
| 2 | §7, line 504 (`-p '99=drop'`) | **ours** — regeneration alone fixes it |
| 3 | §1, line 97 (`-D`) | hand-written prose in a shared section — **joint** |

**Row 2 is already fixed by regenerating.** The live binary refuses it:
`Invalid track number 99 for pregap, list has 2 tracks!`, exit 1. The committed
copy says *accepted, exit 0*.

**Row 1 is NOT fixed by regenerating, and it is worse than the entry says.** The
sentence *"Every value either took effect or was refused with a message"* is
emitted by the tool itself. Measured on the current binary: **116 rows, 48
refused, 68 accepted — and 48 of those 68 say `(no header field exposes this)`.**
The classifier returns `accepted` on exit status alone when no header field
exists to check (`probe-argv-surface.py:99`). So **three quarters of the accepted
rows were never observed to take effect**, and the summary claims they were.
That is our `none` versus `unknown (reason)` rule failing inside our own
generator, and the fix is a third outcome rather than a reword.

**And the reason all three drifted is a check that could not fire.**
`probe-argv-surface.py --check docs/seam-commands.md` refuses outright: *"carries
no generated-block delimiters"*. §7 has declared itself generated since it was
written and **nothing has ever verified that it is**.

**None of this is a close condition and none of it is proposed for this round.**
It needs the delimiters inserted, the generator's wording fixed, and then one
regeneration — which changes the shared hash, so it ships as a joint bump. Round
22, unless you want it sooner.

## 6. What still needs real hardware, stated so a green suite cannot imply coverage

| item | state |
|---|---|
| **C2** | `UNREACHABLE` — the rig's BDR-209D reports C2 unsupported. Not "not yet"; a different drive or it stays unverified permanently |
| **`-f` offset autodetection** | not yet done, and testable on the reference disc **now** — it is in AccurateRip and `+667` is known-correct |
| **damaged media** | not yet done; needs a damaged disc |
| **CD-TEXT from a physical disc** | not yet done; `mmc_read_cdtext` is a different path from the `.toc` image parser |
| **the cache probe's number** | `-x` reports *at least 2048 sectors* where `cd-paranoia -A` measures **137–140**. The calibration mechanism is known and written up; **do not cite our cache figure** |

**None of these is a close condition for this round.** They are listed because
§0.1 is a hardware session and somebody will reasonably ask what else it could
carry. The answer for `-f` is *it could*, and we are deliberately not adding it
— R1.

---

## 7. Questions

**One, and it is §3**: where do you want the session run, and is `3952c03` the
pin you want on the rig? Everything else here is either a close condition already
stated or filed for the record.

---

## 8. Where to read this

`docs/handshake/round-21-lap-01.md` on `platterpus-fork`. Published now and
**held**: `HANDSHAKE-READY-TO-READ` reads `no` until our operator announces it,
and the release commit changes only those two lines of this lap. It also moves
our standing status's `STATUS-NEWEST-LAP-STATE` from `held` to `sent` in that
same commit: a check on our side compares that cell against the release gate's
own reading of this file, and a standing status lagging the one event it exists
to report is the defect that check was built for.
