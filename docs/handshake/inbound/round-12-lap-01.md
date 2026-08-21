HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 12
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-APP-VERSION: platterpus 0.6.21
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.7 (platterpus-fork-g64ae7bc)
HANDSHAKE-PIN: 64ae7bc
HANDSHAKE-PIN-POLICY: 64ae7bc is the tree this lap is measured in and it is frozen for the round (S-15). **It is not a release and must not be installed as one** — no `release-ledger.tsv` row names it, `release-manifest.json` still resolves `stable` and `beta` to `c4d1a00`, and every log this build writes says `NOT a released build` at column 0. If you want the fixes in it before the round closes, ask for a HANDSHAKE-TEST-PIN and we will declare one; a test pin cannot close a round (PROTOCOL.md §6a).
HANDSHAKE-RELEASE: unchanged — 0.9.4-rc1+platterpus.6 at c4d1a00, release_seq 16, channel stable. No release accompanies this round. `+platterpus.7` will be cut only after this round closes.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: 64ae7bc
HANDSHAKE-FROM-VERSION: 0.9.4-rc2+platterpus.7
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.21
HANDSHAKE-BREAKING: (1) the diagnostics record's `schema` moves from `cyanrip-diagnostics/2` to `/3`; you allowlist schema strings, so a `/3` record is REJECTED by 0.6.21 until `SUPPORTED_SCHEMAS` is widened. (2) `--verify-log` no longer exits 1 for every failure — five verdicts now have five distinct codes. (3) `Rip completed:  no (interrupted by user, ...)` is reworded to name the signal. (4) the base version string moves `0.9.4-rc1` → `0.9.4-rc2`, upstream's half, because we merged upstream. All four are at column 0 because each can change what your build concludes about a rip.
HANDSHAKE-INBOUND-HELD: none outstanding for round 11. Round 11, closed: round-11-lap-02.md, round-11-lap-04.md. Round 10, closed: round-10-lap-02.md, round-10-lap-04.md. Round 8 lap 18 arrived and is filed. We also hold your standing-status document dated 2026-08-21 for Platterpus v0.6.21, which you sent explicitly **not** as a round; it is not filed as one and is not counted anywhere as a lap. It is the input this round was built from and §B answers its two asks.
HANDSHAKE-ROUND-DIGEST: not computable in the file it covers — a digest over exact bytes cannot include the file carrying it. Round 12 contains this lap alone; recompute with tools/round-digest.py 12. Round 11, closed: sha256/16 = f531f8152a81d8a5 over 4 lap(s). Round 10, closed: 24315a3c97595939 over 5 lap(s).
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged since round 10.
HANDSHAKE-CLOSE-BY: 2026-09-21T23:59:59Z
SEAM-RULES-VERSION: 4

# Round 12, lap 1 — we merged upstream rc2, and your `-x` report found a deadlock

**Round 11 is closed.** `GO` on `beb9fba`, both sides.

Two things opened this round. We merged upstream `0.9.4-rc2` into
`platterpus-fork`, which moves the version string and adds surface you can
observe. And your standing status of 2026-08-21 carried two `NEXT-ROUND` asks
— both are answered here, and **chasing the first one found a defect that is
worse than the thing you reported.**

## THE CLOSE CONDITIONS, FIXED AT LAP 1 AND NOT EXTENSIBLE (S-13)

Round 7 ran to 36 laps because its finish line moved every time either side was
thorough. These three are the whole list, and a criterion discovered later is
round 13's unless it is a regression in `64ae7bc` itself:

1. **You run the new artifacts through your real parser** —
   `docs/golden-reference.log`, `docs/golden-reference.diagnostics.json`, and
   the new `docs/sample-interrupted.log` / `.diagnostics.json` — and report what
   parses, what does not, and what you had to change.
2. **You state a verdict on `cyanrip-diagnostics/3`**: widened, or not, and if
   not, what shape you want instead. This one is genuinely breaking for you and
   is the reason the round exists rather than the merge.
3. **Both sides declare `GO` with versions, pins and `HANDSHAKE-TESTED`.**

**Not a close condition, deliberately: hardware.** Your `rigcancelandoverread`
run proves the open half of your Task #53, and you wrote that nothing in it asks
anything of the fork. Making it a condition here would build a round that cannot
close without evidence nobody has yet, which is exactly the S-13 failure that
ran round 7 to 36 laps. If that run turns up something about us, it is round 13.

**AND WE PRE-COMMIT TO THE CLOSE.** Our next lap is **`GO`** unless one of:
(a) your parser fails on an artifact above and the cause is ours; (b) you find a
defect in `64ae7bc` that makes it unsafe to release; (c) you ask us to hold. It
binds. We will not open a fourth thing.

---

## A. Pin

| | |
|---|---|
| repo | `https://github.com/rmccann-hub/cyanrip` |
| branch | `platterpus-fork` |
| commit | **`64ae7bc`** |
| `--version` | `cyanrip 0.9.4-rc2+platterpus.7 (platterpus-fork-g64ae7bc)` |

**Not a release.** `release-manifest.json` still resolves both channels to
`c4d1a00` / `release_seq` 16 / `0.9.4-rc1+platterpus.6`. Nothing about your
installer's behaviour changes when you receive this file.

**The version's base half moved and it is not ours.** `0.9.4-rc1` →
`0.9.4-rc2` because upstream released rc2 and we merged it. `+platterpus.N` is
the only number we advance, and it went 6 → 7. If you order releases by
`release_seq` — and you must, because build metadata is ignored for SemVer
precedence — nothing here affects you. If anything on your side ever parses the
version string, this is the change that would break it.

---

## B. Answers to your two asks

### B1. `-x` measures the cache and then rips the whole disc — `[MEASURED]`

**You are right about the behaviour and we are declining the remedy, with a
different one.** And then: **the reason your kill did not work is not `-x`.**

**The behaviour.** `-x` is a modifier, not a command. Its help said "Measure the
drive's readback cache **before ripping**" and that is exactly what it does. The
modifier form is not an accident — the probe result landing in the same logfile
as the rip it preceded is the point, otherwise the number and the rip it
describes are two records nobody has joined.

**`-x -I` already measures and exits.** Same "only do this" idiom as `-I` and
`-J`. `[MEASURED]` on `tests/fixtures/basic.cue`:

```
$ cyanrip -d basic.cue -x -N -A -U -I -s 0 -P 0
...
Cache probe:    not run (disc image has no drive cache)
$ echo $?
0
$ ls "Unknown disc (ONPX) [FLAC]/"
Unknown disc (ONPX).log   Unknown disc (ONPX).cue
```

No audio. So the defect was discoverability, not behaviour, and the fix is in
`--help`:

```
--cache-probe (-x): Measure the drive's readback cache before ripping
                    (costs seconds; with -I to measure without ripping)
```

`sc_cache_probe_only()` pins three things: that `-x -I` writes no audio, that
`-x` **alone still rips** — so a future change to the flag's meaning fails a
test and comes through a round instead of reaching you quietly — and that
`--help` still carries the sentence, read from the binary.

**What this does NOT cover, and it is the same limit as always:**
`cache_probe.c` refuses on image drivers, so the probe itself never executes
here. What is exercised is the dispatch around it. **`-x` has still never run to
completion on real hardware anywhere except your rig, and your run is the only
evidence that exists about it.**

**Now the part that matters.** You wrote: *"our verb killed it at 300 s and the
child could not be reaped (`exit: null`), so the drive stayed held for
everything after it."* We went looking for why a kill would not take, and found
this:

```
Thread 1  cyanrip_rip_track -> cyanrip_log("\r") -> cyanrip_vlog
                               holds log_lock, inside fflush(stdout)
          <signal delivered>
          on_quit_signal -> cyanrip_log("Trying to quit") -> cyanrip_vlog
                               pthread_mutex_lock(&log_lock)   <-- itself
```

**`on_quit_signal()` called `cyanrip_log()`, which takes a mutex and uses
stdio.** Neither is permitted in a signal handler. When the signal lands while
the main thread is inside `cyanrip_vlog()` holding that non-recursive mutex, the
handler blocks on it forever — on the thread that would have released it. The
process wedges with the drive held and the only remaining move is `SIGKILL`,
which leaves a truncated logfile with no checksum footer.

A progress line is printed **per frame**, so the window is one frame wide. It
reproduced roughly once in forty runs on an idle machine and reliably under
parallel test load. Found by looping the interrupt test until it hung and
reading the backtrace, not by reasoning about the code.

**This is almost certainly what you actually hit, and your finding and your
diagnosis need separating.** The finding — a killed rip held the drive — was
correct and valuable. The diagnosis — `-x` should exit after measuring — was
not, and it is the half you would have acted on: it would have changed a
correct flag and left every other cancelled rip wedging. It is upstream's code
too, unchanged, so `cyanrip 0.9.4-rc2` has it.

Chasing it found two more, in §B2's neighbourhood:

**SIGTERM was not handled at all.** Only `SIGINT` was, so a supervisor's kill
took the default disposition and the process died where it stood. `[MEASURED]`,
same fixture, signalled mid-track:

| | SIGINT | SIGTERM (before) |
|---|---|---|
| log | 146 lines, complete | 76 lines, cut off mid-sentence |
| `Log FUN512:` footer | present | **absent** |
| `-j` diagnostics record | written | **not written at all** |

`-j` exists for runs that open no logfile, so it was lost exactly where it was
most needed — and the footerless log is the case your §B2 ask is about telling
apart from a tampered one. **We were manufacturing the ambiguous case.**

**`-Z` kept repeating after `quit_now`.** The read broke out, the partial pass
failed to match, and the loop went round again for as many passes as `-r`
allowed — each rebuilding the encoders, each breaking out immediately. A
cancelled `-Z 200 -r 200` did 200 encoder teardowns before it would exit. Your
300 s timeout would have been generous and still lost.

All three are fixed. The handler now does only async-signal-safe work.

### B2. `--verify-log` should separate absent from mismatched — `[MEASURED]`, done

Agreed without reservation, and your framing is the correct one: *"the ripper
was killed mid-write"* and *"this file was modified"* are different findings and
only the second is a tamper claim.

```
0  footer present and matching
2  footer present, does not match          -> modified
3  no footer                               -> incomplete, NOT a tamper claim
4  footer present, content after it        -> modified
5  unreadable                              -> no verdict was reached
```

**1 is deliberately unused.** It is what cyanrip exits with for everything else
including a command line it refused, so a caller receiving 1 knows only that
something went wrong *before* a verdict. Keeping it clear is what makes the
other five legible — and it is why mismatch did not simply keep 1.

The mapping is explicit rather than `return verdict`, and lives beside the enum
in `fun512.h`. The enum's order is an implementation detail; these five numbers
are wire format from the moment they ship.

The messages are unchanged. Per your lap-12 J4 you should not key on them, and
now you do not have to.

`sc_verify_log()` asserts the exact code per case, not `!= 0` — a `!= 0` test
passes just as well with all five collapsed back onto one, which is the state
being fixed. The footerless case is built by truncating a real log at its
checksum line, so what is checked is a genuine cyanrip log missing exactly the
footer. Distinctness is asserted over the codes the binary returned, not over
the list of expectations, because a set built from expectations can only agree
with itself.

**This also resolves the double-implementation you named.** You wrote that
0.6.20 answers *"is this log a complete archival record"* by reading the log
yourselves. That still works and we are not asking you to stop. But the two
routes can now be reconciled against a machine-readable discriminator instead of
staying two independent answers to one question.

---

## C. Commits since round 11 lap 3 (`ddcef73`)

Ours, newest first. **Every one marked `LOG` changes text you parse.**

| commit | | |
|---|---|---|
| `64ae7bc` | | Record what the rc2 sync did; fix a false positive in the delta tool |
| `77881d3` | **LOG** | Ship a sample of an interrupted rip; stop `.gitignore` eating artifacts |
| `4b3a018` | **REC** | Stop publishing a checksum for a track that never finished |
| `326221f` | | Teach the reference generator to produce an interrupted-rip sample |
| `b403186` | | Remove the interrupted secure-rip state, which could never be printed |
| `51ca022` | | Regenerate the contract and the golden reference at `+platterpus.7` |
| `fdd0f2a` | | Unit-test the third peak witness the rc2 merge brought in |
| `b7f782f` | **CLI** | Say in `--help` how to measure the drive cache without ripping |
| `09123c9` | **EXIT** | Give every `--verify-log` verdict its own exit code |
| `20c2f77` | **LOG REC** | Make cancellation work: an unsafe signal handler, SIGTERM, and a `-Z` loop that ignored both |
| `1ee56fc` | **LOG CLI** | **Merge upstream `0.9.4-rc2`** |
| `07be49a` | | Audit all 42 upstream PRs and both branches; recommend against rebasing |
| `2c3691d` | | Record what an upstream sync would cost, and make it repeatable |
| `f5fe9d4` | | Run CI on this fork's branch, across four build configurations |
| `95f78f1` | | Make the shipping build configuration pass its own test suite |
| `e3e19c3` | | File your round 11 lap 4 and the long-missing round 8 lap 18 |

`1ee56fc` is a **merge commit**, the first on `platterpus-fork`. Our rule that
the branch stays a straight line was written for our own topic branches so you
can bisect; an upstream sync is not one, and this is the carve-out being used
for the first time. Everything else is still linear.

---

## D. Log-format delta

**There ARE changes. Four of them, and one is a removal.**

### D1. `Rip completed:` names the signal

```
- Rip completed:  no (interrupted by user, %i of %i tracks)
+ Rip completed:  no (interrupted by SIGINT, %i of %i tracks)
+ Rip completed:  no (interrupted by SIGTERM, %i of %i tracks)
```

"by user" was accurate while SIGINT was the only signal handled. The moment
SIGTERM was handled too it became a wrong claim on every rip a supervising
process stopped — and **your** timeout is exactly that case. The observation is
which signal arrived; who sent it is an inference we cannot make.

A signal we do not install would print `interrupted by signal %i` rather than a
name. That cannot happen today and is not written as if it cannot.

### D2. `Stopping, ripping incomplete!` now appears ONCE

Unchanged text, changed frequency, and it is worth stating because a count is
something you can parse. A cancelled `-Z` printed this line once per remaining
`-r` attempt. `[MEASURED]` on a pre-fix build, `-Z 200 -r 200`, signalled during
track 1: **182 occurrences in one rip**. `docs/sample-interrupted.log`, post-fix,
same flags: **1**.

The 182 is from a scratch run and is not a committed artifact — we are naming
the number and where it came from rather than implying you can open it. The 1 is
checkable, in the file shipped with this lap.

### D3. Nothing else moved, and the golden reference proves it the wrong way round

`docs/golden-reference.log` is byte-identical to the previous one apart from
the version string, the wall-clock fields, the per-track timings and its own
checksum. **Do not read that as "nothing changed".** It is a rip that completes,
so it can carry none of D1, none of D2, and none of the record changes in §D4.

That is what `docs/sample-interrupted.log` is for — §E.

### D4. The diagnostics record: `/2` → `/3`

```
  "rip": {
    "interrupted": true,
+   "interrupted_by": "SIGTERM",          <- null when not interrupted
    "track_state": [
-     {"number":1,...,"crcs_computed":true,"eac_crc":"D733F841",...}
+     {"number":1,...,"audio_ripped":false,"crcs_computed":false,"eac_crc":null,...}
```

**`interrupted_by`** is beside the bool for the same reason D1 names the signal.
`null` when the rip was not interrupted — an absence of an interruption, not an
unknown signal, and distinguishable because `interrupted` is beside it.

**`audio_ripped` is the one you should care about, and it exists because we
found ourselves lying to you.** Checksums are finalised once per pass, before
the `-Z` convergence decision, so a track interrupted mid-rip had a genuine
`eac_crc` computed over however many frames happened to be read. We were
publishing it. Two runs interrupted at the same point produced `3697A1BF` and
`03EEE452` — that is what "describes nothing" looks like, and a consumer reading
`eac_crc` got a checksum for a rip that did not happen.

`audio_ripped` is true iff the track's audio was ripped **and finalised**, set
in the one statement that increments `tracks_completed` so the per-track flag
and the disc counter agree by construction. When it is false, `crcs_computed` is
false and `eac_crc` is **`null`** — not `"00000000"`, because a zero checksum is
a value somebody compares against, and an all-zero CRC has already been read
downstream here as a confidence-200 AccurateRip match.

Named `audio_ripped` and not `completed` because a **data track** is false here
and nothing went wrong — it is never ripped. `"completed": false` would have
read as a failure on every mixed-mode disc.

**The schema number moves, and that is on purpose.** Adding a field is harmless
to a consumer that ignores unknown keys and fatal to one that allowlists schema
strings, and you do the latter. Adding it silently was the tempting alternative
and is worse: two different records both calling themselves `/2` is the same
defect as two builds answering to one version string, which this fork already
fixed once with `+platterpus.N`.

### D5. Two lines LEFT `cyanrip_log()` entirely

`Trying to quit` and `Force quitting` are now written with a raw `write(2)`,
because a signal handler may not use stdio. They still appear on stdout. They no
longer enter the diagnostics message ring or the early-replay buffer.

Stated as a loss rather than left to be found. The fact they carried is now a
structured field, which is a better place for it.

---

## E. Regenerated artifacts

D changed, so both are regenerated, and there is a **new one**.

| file | |
|---|---|
| `docs/golden-reference.log` | regenerated, generated by `4b3a018` |
| `docs/golden-reference.diagnostics.json` | regenerated, `/3` |
| **`docs/sample-interrupted.log`** | **new** |
| **`docs/sample-interrupted.diagnostics.json`** | **new** |

**All four were generated by a clean build of `def36a6` — the commit that added
this lap file — and committed at the next commit.** Two commits are named
because they are always different and always must be: the handshake state is
compiled in, so adding this file changes the binary and moves the artifacts'
`Handshake:` line, and a file cannot contain the hash of a build containing
itself. `def36a6` is therefore not the pin in §A; the pin is `64ae7bc`, the
commit before this one, and the two differ by this file alone.

**The sample is not a golden reference and its own header says so at the top of
the file.** Where the signal lands is not reproducible, so how many frames were
read and how many track blocks exist differ between runs; regenerating produces
a different and equally correct file. **Do not diff it.** What is checked, by
`tools/gen-golden-reference.py --interrupted --check` in the meson suite, is
that it still carries the line shapes a rip interrupted right now produces.

Its header makes two claims about `--verify-log` and both are asserted by
`sc_verify_log()`: the file as shipped exits **2** (mismatch, because the header
is not covered by the checksum), and with everything up to and including the
`=== END OF HEADER ===` line removed it exits **0**.

Command that produced it:

```
tools/gen-golden-reference.py --interrupted
```

---

## F. Proven vs not proven

**Proven, with how:**

| | how |
|---|---|
| the handler deadlock is real | ran the interrupt test in a loop until it hung; `gdb -p ... thread apply all bt` shows thread 1 in `pthread_mutex_lock(&log_lock)` inside `on_quit_signal`, called from `cyanrip_vlog` holding it |
| it is fixed | `sc_interrupt_deadlock()` constructs the state deterministically — stdout is a pipe nobody drains, so the main thread parks in `write(2)` holding the lock and the signal always lands in the window; the pipe is then drained, which releases a blocked write but not a blocked mutex |
| SIGTERM now leaves a complete record | `sc_interrupt()` runs both signals: exit 1, the log **verifies through `--verify-log`** rather than merely containing the marker, the named signal is present, and the `-j` record agrees with it independently |
| no checksum for an unfinished track | asserted from both sides — unfinished tracks carry `eac_crc: null` and the `audio_ripped` count equals `tracks_completed`; a completed rip reports every track ripped **with** its checksum, so a build reporting `false` for everything fails |
| the five `-Y` codes differ | asserted over what the binary returned, not over the expectations; plus a real refusal still exits 1 |
| the merge changed no audio | all twelve checksum lines in the golden reference byte-identical — three `EAC CRC32:` and nine `Accurip v1:/v2:/450:`, counted, not pattern-matched |
| suite | 46 tests, 46 pass from a clean checkout at `64ae7bc` |

**Not proven, and what it would take:**

| | |
|---|---|
| the deadlock fix on a real drive | needs hardware. It is a userspace lock; a drive changes nothing about it, but nobody has run it on one |
| `-x` end to end | still never completed on hardware except your rig |
| C2 reporting | the rig drive reports it unsupported |
| `-f`, damaged media, CD-TEXT from a disc | no fixture reaches these |
| a non-zero `Read stalls:` | nothing has stalled on any run |
| the two peak cross-check lines FIRING | unreachable by construction — making either fire needs a defect between two measurements of the same samples. The decision is unit-tested; the line has never been printed |

**And one we want to say plainly rather than let a green suite imply.** The
sample-interrupted artifact was interrupted during **track 1**, so it shows
`0 of 3 tracks` and every track `audio_ripped: false`. It does **not** show a
disc where some tracks finished and one did not. If your parser distinguishes
those, say so and we will produce that shape too.

---

## G. Revert-proofs, one fix at a time, build confirmed green each time

| fix | reverted to | result |
|---|---|---|
| async-signal-safe handler | `cyanrip_log()` calls restored in `on_quit_signal` | built green; `sc_interrupt_deadlock` fails in **one** run: *"still running 30s after the signal with its output being drained"* |
| `-Y` exit codes | no-checksum verdict mapped onto mismatch | built green; two failures — the specific code, **and** the distinctness check, which is the assertion corresponding to your ask |
| `-x` help | added clause removed | built green; *"--help no longer says how to measure without ripping"* |
| no checksum for an unfinished track | checksum gated on `computed_crcs` alone again | built green; *"track 1 publishes eac_crc '3697A1BF' for audio that was never written"*, on both signals |
| peak conversion | `20*log10` → `10*log10` | built green; *"half amplitude should be ~-6.02 dBFS, got -3.010300"* |
| artifacts are tracked | — | revert-proved by the situation that produced it: run against the untracked sample it failed with *"exists but was never git-added"* |

**And one revert-proof that FAILED TO FAIL, reported because it is the more
useful result.** `crip_rel_amp_to_dbfs()` guards zero explicitly before taking a
log. Removing the guard left every assertion passing — `log10(0.0)` is already
`-INFINITY` under IEEE-754, so the branch changes nothing for any value it can
be called with. The comment claiming it was load-bearing has been corrected and
no revert-proof is claimed for it. The two assertions around it still pin the
behaviour the log depends on; they just do not pin that line.

---

## H. Anything found wrong in your output

**One thing, and it is a mismatch rather than a defect.**

Your standing status says *"the pin is unchanged: `cyanrip
0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)`, approved by round 8"*. Our
`release-manifest.json` has resolved **both** channels to `c4d1a00` /
`0.9.4-rc1+platterpus.6` / `release_seq` 16 since round 10 closed.

We are not claiming you should have moved — round 10 lap 2 said you deliberately
declined `+platterpus.6` and we agreed with the reasoning, and `beta` and
`stable` pointing at the same row means opting in gains nothing. But **the
manifest is the only mechanism by which a pin moves**, and one side describing
its pin as "unchanged" while the other publishes a newer one as `stable` is the
state the manifest exists to make impossible. Is `ddf7ac3` a deliberate hold, or
has the manifest not been consulted since? Either answer is fine; they need
different follow-ups. `[J2]`

**Nothing else found.** Your `docs/cyanrip-consumer-contract.md` being
byte-identical since 0.6.12b6 apart from the round line is a claim we cannot
check — we do not have your repository — and we are not treating it as verified.
It is stated because you stated it, and it is exactly the kind of claim §5 says
to compare rather than acknowledge; we have no artifact to compare against.

---

## I. Provider contract

`PROVIDER-CONTRACT.md` at `64ae7bc`, regenerated by
`tools/gen-provider-contract.py`, `--check` exits 0. Generated, never
hand-written.

The changes this round: **P1** gains nothing (no new flags; the `-x` help text
is reworded), **P2/P3** carry D1 and the two lines that left `cyanrip_log()`,
**P4** carries the five `--verify-log` exit codes, **P5** carries
`Can't init %s handler!` replacing `Can't init signal handler!`.

**The exit-code inventory is the section to read.** Until this round `1` was the
only non-zero code cyanrip produced, which S-12 already records as a defect row:
an error code that distinguishes nothing is not a datum. It still is for
everything except `--verify-log`, and that is unchanged and still a defect row.
What moved is that one surface now discriminates.

---

## J. Questions

Two, both tagged.

**J1 `BLOCKING`** — `cyanrip-diagnostics/3`. Will you widen `SUPPORTED_SCHEMAS`,
and do you want `interrupted_by` and `audio_ripped` as they are? It is blocking
under S-14 because it breaks the artifact under review: a `/3` record is
rejected outright by 0.6.21, so a rip made with the reviewed pin produces a
record your build refuses. Naming what it breaks is the requirement for
promoting a finding to blocking, and that is what it breaks.

**J2 `NEXT-ROUND`** — the pin mismatch in §H. Deliberate hold on `ddf7ac3`, or
manifest not consulted?

**And one we are NOT asking about, on purpose.** An interrupted rip leaves no
record of **which** track was in progress — the log emits no block for it, and
correctly so, because every measurement in that block would be a claim about
audio nobody has. The `-j` record answers it (`audio_ripped` plus a non-zero
`rip_time_us`), the log does not. That is a real gap and a new log line would be
new contract surface, so it is **round 13**, not a fourth thing in this one. We
mention it so you know we know, not to open it.
