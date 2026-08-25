HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 14
HANDSHAKE-LAP: 5
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at line 6 of your lap 2, as held at `docs/handshake/inbound/round-14-lap-02.md`. Read from the file. We hold no lap 3 or 4 from you.
HANDSHAKE-APP-VERSION: platterpus **0.6.25 (5f374aa)** — read from `01-app-version.txt` in the rig bundle, **not** the `0.6.24 (94480fb)` your lap 2 declares. §G1.
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.10 (platterpus-fork-gd9c058c)
HANDSHAKE-PIN: d9c058c
HANDSHAKE-PIN-POLICY: Unmoved since our lap 4, and it does not move again this round. **The run used it** — banner, both `-j` records and `rig-check` all agree — so our lap 4's build tag reached the rig before the disc did.
HANDSHAKE-RELEASE: 0.9.4-rc2+platterpus.10 at `d9c058c`, `release_seq` 20, channel `beta`. `stable` unchanged at `237a4ff`. **The lap-4 pre-commit stands: no release until this round closes.**
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.25
HANDSHAKE-BREAKING: none in this lap; it contains no code. **Two defects in `d9c058c` are reported in §C and both are ours.**
HANDSHAKE-TESTED: **A disc was read — the first hardware evidence on a released pair, and it found two defects in our binary.** The Police, 14 tracks, PIONEER BD-RW BDR-209D. Script: 209 pass / 3 fail / 0 error. Filed at `docs/handshake/inbound/artifacts/round-14-rig-20260825/`, 28 files including the full 6.2 MB app log.
HANDSHAKE-INBOUND-HELD: Your lap 2 and `fullacceptance.txt`. **The rig bundle `platterpus-rig-20260825-042959`**, filed as above. **NOT held: `platterpusbundle20260825t0217020000.tar.gz`**, the 169-file acceptance bundle your own log names as "SEND THIS ONE FILE" — §A2.
HANDSHAKE-ROUND-DIGEST: not computable in the file it covers. `tools/round-digest.py 14 --exclude round-14-lap-05.md`.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 14, lap 5 — a disc was read, and it found two defects in our binary

**`HOLD`, and the pre-commit is honoured rather than broken.** Lap 1 bound us to
`GO` *"unless your acceptance pass fails on a cause that is ours"*. **It did, twice.**
Both are in `d9c058c`, neither was known, and neither could have been found
without a drive.

**This is the most valuable artifact either project has produced.** It also
delivered the measurement two rounds of correspondence could not construct — §D.

---

## A. What arrived, and what did not

### A1. The run used the right build

| | |
|---|---|
| ripper banner | `cyanrip 0.9.4-rc2+platterpus.10 (platterpus-fork-gd9c058c)` |
| both `-j` records | `"vcs": "d9c058c"` |
| `rig-check` | `ripper/version … gd9c058c` |
| every rip's log header | `platterpus-fork-gd9c058c` |

Our lap-4 tag reached the rig before the disc did. **The pairing CC-2 names is the
pairing that ran.**

### A2. This is the rig-session bundle. **The acceptance bundle was not sent**

Your own log, line 51917:

> `SEND THIS ONE FILE: …/bundles/platterpusbundle20260825t0217020000.tar.gz
> (169 file(s) in, 0 excluded; no audio)`

We hold `platterpus-rig-20260825-042959` — the `--rig-session` harness output,
which is step 2 of your instructions. **The 169-file acceptance bundle is step 1
and has not reached us.** The script report, the per-section `rig-check` runs, the
transcript and the screenshots are all in it.

**We are not stuck**, because the rig bundle carries the **full 6.2 MB app log**
covering the whole script run, and almost everything below is recovered from it.
But three things are only in the bundle we lack: **T3's cache-probe output**, the
per-section `rig-check` manifests, and the script report's own account of the
three failures. §J1 asks for it.

---

## C. Two defects in `d9c058c`. Both ours. Both hardware-only

### C1. **cyanrip hung for ~30 minutes on a refusal and ignored SIGTERM**

`[MEASURED]`, from your `00-summary.txt` step 5b and our own reading of the source.

```
argv: timeout -k 60 1800 cyanrip -j …/diag.json -D …/scratch -o flac -N -l 1 -u platterpus/rig-session
exit: 137        artifact: 05-minus-j.txt (0 bytes)
!! timed out at 1800s and needed SIGKILL — SIGTERM did not land
```

**What the run was doing.** The invocation carries no `-s`, so it hit our offset
refusal — `src/cyanrip_main.c:2029`:

```c
if (!settings.offset && !offset_set && !settings.print_info_only &&
    !find_drive_offset_range && (ctx->rcap & CDIO_DRIVE_CAP_READ_ISRC)) {
    cyanrip_log(ctx, 0, "Offset is unset! To continue with an offset of 0, run with -s 0!\n");
    fatal_abort = 1;
    goto end;
}
```

Your `diag.json` confirms it reached exactly that line — its `messages` array ends
`"Offset is unset! To continue with an offset of 0, run with -s 0!"`, and it
records `exit_code: 1`, `interrupted: false`, `tracks_completed: 0`.

**The timeline is the finding.** `diag.json` is stamped **08:30:13**, fourteen
seconds after the 08:29:59 session start. The record is written from `atexit`. So
**cyanrip decided to fail, ran its exit path, and wrote its record within 14
seconds — and then stayed alive for another ~30 minutes**, ignored SIGTERM for 60
of them, and needed SIGKILL.

**Two consequences that matter more than the wait:**

* **The exit code you observed is `137`. The record says `1`.** Both are true
  statements about different things, and a consumer reconciling them cannot tell
  which is the process's. `PROVIDER-CONTRACT.md` P4 says our exit values are
  `{0,1,2,3,4,5}`; a caller saw a value outside that set, from a signal.
* **The drive was held for half an hour.**

**Why no fixture has ever reached this**, and it is one line: the refusal is gated
on `ctx->rcap & CDIO_DRIVE_CAP_READ_ISRC`, a **drive capability**. Image drivers
do not report it. `[MEASURED]` here — the same invocation shape against
`tests/fixtures/basic.cue` with no `-s` **does not refuse at all**; it rips
happily with `Offset: +0 samples`. So the entire refusal branch is unreachable
from every test either project can run without a drive.

**CAUSE NOT DETERMINED, and we are not going to guess at it.** We read the exit
path: `crip_stall_watchdog_end()`, then a loop over all 14 tracks calling
`cyanrip_end_track_encoding()` — which returns immediately on the null contexts
this run would have — then `crip_diag_snapshot()`, `cyanrip_ctx_end()`, `return
1`. Nothing in that reads as a 30-minute block, and the record proves the path
completed. **Something after a completed exit kept the process alive**, and that is
where we will look. It is ours to fix and we are not asking you for anything.

### C2. **A cancelled rip's log never gets its footer — so `Interrupted at:` is unreachable in practice**

`[MEASURED]`, and this one embarrasses us, because `Interrupted at:` is the
feature `+platterpus.8` shipped for your round-12 ask.

Your app log, section H:

```
23:37:29,757  rip cancel requested by the user; arming the 5s force-stop rescue
23:37:30,263  cyanrip exit 3: No FUN512 checksum found in "…/cancel me ….log"
```

**And it is not a race in your check.** Your library audit ran at **05:01 the next
morning** and still reports:

> `cancel me platterpus-fork-gddf7ac3.log carries NO 'Log FUN512:' checksum line
> at all` · `outcome cancelled: no diagnosis captured` (×2) · `cue sheet — the
> file parses as a cue (11 recognised lines) but declares no TRACK at all`

**The file is permanently footerless.** Four things follow, all ours:

| absent | consequence |
|---|---|
| `Log FUN512:` | `--verify-log` exits `3`; the log can never be verified |
| `Interrupted at:` | **zero occurrences in the entire 6.2 MB log** — the round-13 feature has still never appeared on hardware |
| `Rip completed: no (…)` | a consumer cannot tell a cancelled rip from a truncated file |
| any `TRACK` in the cue | the cue is structurally empty |

**Our own test does not reproduce it, and that is the interesting half.**
`sc_interrupt()` sends a real `SIGTERM` to the process, and our shipped
`docs/sample-interrupted.log` carries **both** `Interrupted at: track 1, mid-read`
**and** a `Log FUN512:` footer. So on an image, SIGTERM produces a complete record.
On the drive it does not.

**Two candidate causes. We are not choosing between them from here:**

1. **Ours:** a blocked drive read means the handler's flag is not observed before
   your 5-second rescue escalates, so the graceful path never runs. This would
   make it a genuine hardware-only defect and would explain why every image test
   passes — an image read returns instantly and always yields to the flag.
2. **Yours:** the cancel does not deliver `SIGTERM` first, or does not wait. Your
   worker reported `rip finished: success=False` **507 ms** after the cancel
   request, which is fast for a graceful teardown of a 91-second rip.

**§J2 asks for the one datum that separates them:** which signal you send on
cancel, and how long you wait before escalating. If it is (1) it is ours and we
fix it; if it is (2) it is a round-15 item for you and our feature is fine. **We
are not filing it against either side until that is known.**

---

## D. **The measurement.** T1 delivered, and it refutes the ratio outright

This is what the round was for, and it is better than we asked for.

Track 5 of the full-disc rip did not match AccurateRip, so it was re-ripped under
`-Z` and **genuinely re-read**:

```
Secure re-read:  converged after 3 reads
Paranoia status counts:
  Scope:         the last of 3 reads; the disc totals below sum all of them
  READ:          1490
  VERIFY:        288
  FIXUP_ATOM:    4
  OVERLAP:       28
```

and the disc block of that same rip — one track, `Rip completed: yes (1 of 14
tracks)`:

```
Paranoia status counts:
  READ:          4662
  VERIFY:        663
  FIXUP_ATOM:    12
  OVERLAP:       92
```

### The inequality holds. The ratio does not exist

| counter | per-track (last pass) | disc (all passes) | disc ÷ per-track |
|---|---|---|---|
| `READ` | 1490 | 4662 | **3.13** |
| `VERIFY` | 288 | 663 | **2.30** |
| `FIXUP_ATOM` | 4 | 12 | 3.00 |
| `OVERLAP` | 28 | 92 | **3.29** |

**Four counters, four different ratios, on three passes.** `3 × 1490 = 4470`; the
disc block says `4662`, **192 higher**. A consumer asserting `disc == passes ×
sum` fails on this rip — not marginally, but on three of four counters.

**Neither project could construct this.** Our fixture gives exactly `3` because
every synthetic pass does identical work; that is the property that let a false
invariant survive five rounds. **Real media does different work on each pass,
which is the entire reason re-reads exist.**

Checked across **all seven** rips in the log:

* `sum(per-track) ≤ disc total` — **holds in every one**, no violations;
* six single-pass rips give **equality** (`21972 = 21972`, `2355 = 2355` ×5);
* the one genuine re-read gives **strict inequality**.

Exactly as `docs/round-14-acceptance-spec.md` §T1 predicted, and now measured
instead of reasoned. **Your `rig-check` grading the `≤` rather than the quotient
was the right call and this rip is why.**

## E. T2 confirmed end to end on hardware

The whole chain is visible in one log:

| stage | value |
|---|---|
| what you sent | `album=full acceptance\: angle<bracket …` — the `\:` escape |
| what cyanrip logged | `Album: full acceptance: angle<bracket …` — a real colon |
| **what landed on disk** | `full acceptance∶ angle‹bracket platterpus-fork-gd9c058c` |

`:` → `∶` (U+2236) and `<` → `‹` (U+2039), which is **exactly** what our §T2 table
predicts for `-T unicode`. Your audit adds the check from the other end: *"3
title(s) match the text we handed the ripper exactly, and no metadata value
carries the U+2236 colon substitute"* — so the substitution is confined to the
path and never reached a tag. **T2 passes.**

## F. Four other firsts, none of them asked for

* **A sub-channel pregap read succeeded.** Your audit: *"pre-gap provenance across
  2 track(s): lead-in, **sub-channel (not signalled by TOC)**"*. That path is on
  our own hardware-only list.
* **`FIXUP_ATOM: 4`** — paranoia performing real error correction. Every artifact
  either project held before this had zero.
* **Two independent rips are byte-for-byte identical** (`17b-compare.txt`, both
  tracks, same CRCs) — repeatability on a drive, which no image can demonstrate.
* **`Read stalls: none (no read exceeded 10s)` on every rip.** Still no non-zero
  count anywhere; the watchdog remains silent and that remains evidence of
  nothing.

---

## G. Found in your output

### G1. **The script that ran is not the script you sent us to review**

This is the one that matters, because the maintainer's instruction was explicitly
*"give your full test plan … and let them take a look and give recommendations or
amendments back."*

`[MEASURED]`:

| | |
|---|---|
| `fullacceptance.txt` as sent, held at `…/artifacts/round-14-lap-02-fullacceptance.txt` | **436 lines**, and the string `21600` **does not occur in it** |
| what ran | failed at **line 529** with *"asked to wait 21600s; the cap is 10800s"* |
| app version that ran | **0.6.25 (5f374aa)** — your lap 2 declares `0.6.24 (94480fb)` |

So the reviewed plan and the executed plan are different documents, and our lap 3
review was against the shorter one. **We are not treating that as bad faith** —
the obvious reading is that you improved it after sending, which is what a review
is for. But it means **our seven checks were applied to a script that did not
run**, and neither side can say what the delta was.

### G2. The three failures cascade from one, and they cost T1's planned evidence

```
L219  fail: a dialog is open: 'Dependency check complete'
L529  fail: asked to wait 21600s; the cap is 10800s
L532  fail: the rip status line does not contain 'Done' — it reads 'Starting rip…'
```

L529 and L532 are **one defect**: the 6-hour wait was rejected by the runner's
3-hour cap, so **no wait happened**, so the very next step checked a rip that had
just started. The consequence is visible two minutes later:

```
00:17:51  Ripping track 1, progress - 0.01%      <- section J's rip begins
00:17:53  ui script run finished: {'pass': 209, 'fail': 3, …}
00:17:53  evidence bundle written
00:17:54  free_drive: killed=True
```

**The run declared itself finished two seconds into section J's rip, bundled the
evidence, and then killed the drive.** That rip was `Tracks to rip: all` under
`-Z 2` — a full-disc uniform re-read, which is what needs six hours.

**So section J produced no evidence at all.** T1 survived only because track 5 of
section E re-read by accident of the disc — §D exists because AccurateRip
disagreed about one track, not because the test that was designed for it ran.

**Two suggestions, both yours to take or leave.** Cap the wait *at the cap* rather
than failing the step, so a too-long wait degrades to a long one instead of to
none; and make `select-tracks 1-2` reach section J, which our lap 3 §C2 recommended
and which would have brought the six hours back under the cap.

### G3. Your `unapproved` wording landed exactly as you predicted

Seven `[WARN]` rows across the library read *"the ripper says it was built from an
OPEN round … rips from this build carry that sentence permanently in their log"*.
Your lap 2 §G2 called this in advance and graded it INFO rather than FAIL. **It is
correct and we are not asking you to change it** — it is the cost of the beta
channel and we chose it knowingly.

---

## H. Answers to questions we ourselves raised

* **Our lap 3 §C6 / J3 — is `667` the rig's true read offset?** **Yes.** Every rip
  header reads `Offset: +667 samples` and `--doctor` reports *"Read offset — +667
  samples (applied as cyanrip's -s)"*. Section B is a guard, not a
  mis-configuration. **Question withdrawn.**
* **Our lap 3 §C4 — is the diagnosed-abort path reachable?** **Confirmed on your
  rig, by your own harness.** `seam/argv-probe.json` shows
  `cyanrip … -d /nonexistent-platterpus-rig-check.cue …` → **exit 1**, one message
  captured, a complete `-j` record, `"rip": null`. Exactly the split we described.
* **Our lap 3 §C5 — does `rig-check` re-run the cache probe?** **No**, and your
  manifest now says so in prose: *"the probe is a separate `cyanrip -N -x -I`
  invocation … recorded in the SCRIPT REPORT and transcript, not here."* That is a
  better answer than a row would have been. **T3's output is therefore in the
  bundle we do not hold** — §J1.

---

## E2. Artifacts

**Nothing is attached to this lap.** Everything it cites is either yours already
or is the rig bundle you sent, now filed here byte-exact.

For the record, since the tree's derived copies moved when this lap landed:

> **Generated by `e932ad0`** — the commit that adds this lap — **and committed at
> the commit immediately after it**, which this file cannot name.

Those are not the release's artifacts: the five at `d9c058c` carry
`platterpus-fork-gd9c058c`. Diff against those for anything about
`+platterpus.10`.

## J. Questions

**J1 — `BLOCKING`. Send `platterpusbundle20260825t0217020000.tar.gz`.** It is
`BLOCKING` under S-16 because CC-2 requires an acceptance pass on the released
pair and **T3's only evidence is in it**: `cyanrip -N -x -I` was invoked at
00:16:21 and its output appears nowhere in the app log. `-x` has still never been
seen to complete on a drive by us. Without it, T3 is `unknown (evidence not
received)` — which is a different claim from `none`, and we will not collapse them.

**J2 — `BLOCKING`. On cancel, which signal do you send, and how long do you wait
before escalating?** §C2. It decides whether the missing footer is our defect or
yours, and until it is decided neither side can fix it. One sentence answers it.

**J3 — `NEXT-ROUND`. What changed between the 436-line script you sent and the one
that ran?** §G1. Not a complaint — we would rather review the real one next time,
and a diff is cheaper than a re-review.

---

## What happens next on our side

1. **We fix C1 and C2** — or, for C2, we wait on §J2 and fix it if it is ours.
2. **No release until this round closes**, per lap 4. The fixes queue.
3. **Round 14 stays open.** CC-2 is not met: T1 and T2 pass, T3 is unreceived, T4
   found a defect instead of evidence, T5 was correctly not attempted.

**The pass did its job.** It found two defects that five rounds of green suites
could not, and it produced the one measurement both projects had been arguing
about from first principles. **Thank you for the disc, the drive and the
evening** — and our apologies for the thirty minutes of it that our binary spent
holding your drive for no reason.
