# Rig session — Platterpus `v0.6.4b9` + cyanrip `f5e11ba`

```
Platterpus  v0.6.4b9        GitHub PRE-RELEASE   (app-only change; the ripper pin did NOT move)
cyanrip     f5e11ba         0.9.4-rc1+platterpus.5-beta.4   (platterpus-fork-gf5e11ba)
drive       Pioneer BDR-209D
round 7     OPEN, HOLD both sides — nothing here is a release
```

**Your last rip found the real bug, and it was not the one I fixed in b8.** The b8 floor cut
the ETA's peak from 61.9 hours to 8.3 — better, and still wrong, which is the useful kind of
partial fix because what is left over points at the cause. It did, and the cause was not the
arithmetic at all.

**Your own debug log had it, twice:**

```
01:38:57 WARNING rip stalled: no forward progress for 3m 2s at 21.7% (track 3)
                 — the drive is stuck on a hard-to-read spot
01:38:50 DEBUG   cyanrip │ Ripping track 3, progress - 52.29%
01:38:55 DEBUG   cyanrip │ Ripping track 3, progress - 54.50%
```

**Nothing was wrong with your disc.** That is the secure re-read doing exactly its job at 1×,
and we told you it was scratched — because the album progress bar cannot move during a re-read
(it is re-reading a track the bar already counted, and the bar is not allowed to go backwards),
and both the stall warning and the ETA were reading only that bar.

So b9 is mostly about **what you see on screen while a disc rips**. Four things you can check
with your eyes, and everything else is scripted.

---

## What changed, and how you would notice

| fixed | how you would notice |
|---|---|
| **"The drive is stuck on a hard-to-read spot (a scratch or smudge)"** on a healthy re-read, twice per disc | that warning should now appear **only** when the drive genuinely stops. During a re-read you should see `· verifying track 3 (re-read 2) · about 54m left` instead |
| **The ETA climbed 54m → 1h50m → 5h40m in 70 seconds** during the re-read | the estimate should **hold** through a re-read, not climb. It stops moving *and says why* |
| **The track list opened showing 2 rows of 14** | it should open showing **6–8 rows**, and the window opens a bit taller |
| **The columns shuffled sideways on every track** (Status swung 48→67→53 px, twice per track) | the grid should sit perfectly still for the whole rip. Title should also be much wider than Artist now |
| **`INCOMPLETE RIP (cancelled) — this log covers 14 of 14 disc tracks`** — a banner contradicting itself | on a cancel *after* all tracks are out, it now reads `RIP STOPPED (cancelled)` and says the extraction is complete |
| **`the securing pass was INTERRUPTED`** with no cause | now `INTERRUPTED (you cancelled the rip)` when that is what happened |
| **The report's `eta_trace` went silent** for 541 s and 400 s — exactly the minutes the estimate was wrong | every sample is now recorded with a `state` (`computed` / `held_no_rate` / `rereading` / `stalled`), so the next trace has no holes |

> **The two to watch with your own eyes are the stall warning and the ETA during a re-read.**
> Everything else the script checks or the artifacts show.

---

## Step 1 — Update (2 minutes, no disc)

**Settings → Updates → "Offer beta (pre-release) updates"** is already ticked from last time.

> **Help → Check for updates** → accept → **restart**.

Then confirm — **`Help → About` must say 0.6.4b9**. If it still says b8, the update did not take;
tell me rather than working around it.

### The ripper pin: move it to `9048082`, and this is your call

**Changed since this sheet was first written.** The fork shipped `beta.5` (`9048082`) and
**superseded `beta.4` (`f5e11ba`) — the build you have.** Their reason is a defect *your
last rip found*: on tracks 3, 6, 11 and 12 the log says `Pregap length: 0 frames` and the
cue writes an `INDEX 00` anyway, one frame past the end of the previous `FILE`. Present in
all three cue sheets on record, so it is not a `beta.4` regression — it is as old as their
sub-channel pre-gap search.

**Why moving is the right call, and it costs you nothing extra.** `beta.5`'s only change
over `beta.4` is that cue fix, and it is **the one change in their pin no drive has run**.
Their own §E1 says they are not asking us to approve it untested, and cites our rule back
at us: *a round approves the pin you tested*. That leaves a genuine bind — `f5e11ba` is the
most-tested build **and** the one with the defect — except that you are about to rip
anyway. Ripping on `9048082` converts "untested" into "tested" in the same session, and
then the round can close on a build with no known defect and no untested change.

**Switching the container's ripper pin while a round is open is a decision the rules
reserve for you** (`CLAUDE.md` deviation policy), which is why this is a marked step and
not an instruction. If you would rather not, say so and rip on `f5e11ba`; the b9 app fixes
are what this session is mainly for and they do not depend on the ripper at all.

```sh
platterpus --install-ripper        # or ./platterpus-x86_64.AppImage --install-ripper
~/.local/bin/cyanrip --version     # expect 0.9.4-rc1+platterpus.5-beta.5 / platterpus-fork-g9048082
```

A banner ending `-dirty` means the tree had uncommitted changes and the commit does not
describe the binary — stop and tell me if you see one.

---

## Step 2 — Look at the window before you put a disc in (30 seconds)

This is the one check that costs you nothing and covers the layout fix.

1. Open Platterpus. **Do not resize it.**
2. Put the Police disc in and let it identify.
3. **Count the visible track rows.** Should be **6 or more** without scrolling. It was 2.
4. Glance at the column widths: **Title should be clearly the widest column**, Artist narrow
   (it holds the same "The Police" on every row).

If it still opens on 2 rows, screenshot it and send the screenshot — that is a measurement I
can act on and a description is not.

---

## Step 3 — Rip the Police disc, and watch the re-reads (~50–70 minutes)

Same disc as always. Start the rip and then **just watch the status line during tracks 3 and 5**
— those are the two that needed re-reading last time.

**What you should see when a re-read starts:**

```
Ripping track 3 of 14… 14%  ·  verifying track 3 (re-read 2)  ·  about 54m left
```

**What you should NOT see:**

- `stalled 3m 0s — the drive is stuck on a hard-to-read spot (a scratch or smudge)` while the
  percentage is still climbing.
- The estimate climbing while the overall bar is frozen. It may **hold** at one number for
  several minutes — that is correct and deliberate.

**If the stall warning appears anyway:** note roughly when, and whether cyanrip's own
percentage was moving at that moment. Both are in the log, so I can settle it from the
artifacts — but knowing what you *saw* tells me which of the two signals misfired.

**Also worth a glance:** the track grid should not twitch as tracks complete. If any column
jumps width mid-rip, that is a miss and I want to know.

### If you moved to `9048082`: check the cue sheet (2 minutes, and it closes the round)

This is the only thing in their pin no drive has run, and it is a one-look check. Open
`Every Breath You Take∶ The Classics.cue` and count `INDEX 00` lines:

```sh
grep -n "INDEX 00" "<album>/Every Breath You Take∶ The Classics.cue"
```

| tracks | expected |
|---|---|
| **3, 6, 11, 12** | **no `INDEX 00`** — these are the zero-length pre-gaps their fix stops writing |
| 2, 4, 5, 7, 8, 9, 10, 13, 14 | `INDEX 00` still present |

**If a pre-gap you expect has gone missing, that is a finding and their fix goes back** —
their words, and they mean it. Send the cue either way; a correct result is what lets the
round close, and a wrong one is worth more.

---

## Step 4 — One command (unattended, most of the session)

```sh
bash ~/path/to/Platterpus/scripts/rig_session.sh ~/rig-b9
```

**14 steps, one artifact each, never stops on a failure** — a failing step is data, and every
exit code is recorded including the successes. Covers both projects: the app's `--doctor`, the
dependency probe, the ETA sweep, log sizes and retention, a fresh cyanrip clone + build check,
handshake status and preflight.

It ends with a `COMPLETE` banner. **If you do not see that banner, the run was cut short** — send
what it produced anyway; a truncated run is still evidence, and the missing steps tell me where
it stopped.

---

## Step 5 — Send me these (the whole point)

From the album folder:

```
<album>/Every Breath You Take∶ The Classics.log                     (cyanrip's own log)
<album>/Every Breath You Take∶ The Classics.platterpus.json         (the report — the big one)
<album>/Every Breath You Take∶ The Classics_EACcompatible.log
<album>/Every Breath You Take∶ The Classics.cue
<album>/Every Breath You Take∶ The Classics.platterpusaddendum.txt  (if tracks were re-ripped)
```

Plus:

```
~/.local/share/platterpus/log.txt          (and log.txt.1 … if they exist)
~/rig-b9/                                  (the whole folder from step 4)
```

**Do not send FLACs.** The logs and CRCs prove everything the audio would, and the repo is
public — a music file must never reach it, even temporarily.

### The one thing I will look at first

`eta_trace.samples[]` in the JSON, specifically the `state` field. On the b8 rip that series had
two holes totalling ~16 minutes, right where the estimate was wrong, because a held estimate
recorded nothing. If b9's trace still has a gap during the re-reads, the fix is incomplete and
I will know immediately.

---

## Optional — the cancel case (5 minutes, only if you feel like it)

This exercises the two banner fixes, and only a real cancel produces the shape.

1. Start a rip of any disc. Let it get **past the last track** (watch for the AccurateRip
   summary or the securing pass starting).
2. **Cancel.**
3. Open the `_EACcompatible.log` and check two lines:
   - It should say **`RIP STOPPED (cancelled)`** — *not* `INCOMPLETE RIP (cancelled) — this log
     covers 14 of 14 disc tracks`, which is the self-contradiction b9 fixes.
   - If a securing pass had started, its line should read **`INTERRUPTED (you cancelled the
     rip)`**.
4. And in the JSON: `outcome.status` must be `"cancelled"`, not `"success"`. That was the b8 fix
   and it is worth one more confirmation on a *different* cancel point than last time.

---

## What is still not fixed, honestly

- **The +450 AccurateRip question is open on the fork's side.** Our half is ruled out: our swap
  path takes AccurateRip results from the shipped read only and refuses to inherit a previous
  pass's verdict. Lap 27 asks them what buffer the +450 variant is computed over. Nothing for
  you to do.
- **Round 7 is still OPEN, both sides HOLD**, so `v0.6.4b9` is a **pre-release** and not a claim
  that the pair is verified. The one thing blocking a GO from us is the fork's flag table, which
  has not arrived for three laps. No stable `v0.6.4` until it does.
- **The ETA is better, not perfect.** It systematically *under*-estimates (median −23 min on b8).
  I have not touched that yet — a wrong-but-stable estimate is a different and much smaller
  problem than one that triples in a minute, and the b9 trace is the data I need to fix it
  properly rather than by guessing.

---

*Last updated for Platterpus v0.6.4b9.*
