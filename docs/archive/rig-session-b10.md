# Rig session — Platterpus `v0.6.4b10` + cyanrip `9048082`

```
Platterpus  v0.6.4b10       GitHub PRE-RELEASE   (build f8dbedd)
cyanrip     9048082         0.9.4-rc1+platterpus.5-beta.5   (platterpus-fork-g9048082)
drive       Pioneer BDR-209D 1.51, offset +667
round 7     OPEN, HOLD both sides — nothing here is a release
```

**You are already on both.** Confirmed from your own log, not assumed:

```
19:38:36  /home/rmccann/.local/bin/cyanrip -V
          cyanrip 0.9.4-rc1+platterpus.5-beta.5 (platterpus-fork-g9048082)
19:35:41  platterpus 0.6.4b10 (build f8dbedd) starting
```

**So steps 1 and 2 of the previous sheet are done and you can skip them.** This sheet starts at
the disc.

---

## Corrections to the sheet I gave you

**1. `./platterpus-x86_64.AppImage --install-ripper 9048082` was my mistake, not a bug.** When
you accepted the first-run offer, the app **moved** itself to `~/Applications/` (it says so in
the dialog that follows, and in the log at 19:35:44) — so a `./`-relative command run from
`~/Downloads` afterwards finds nothing. The app behaved correctly; my instruction assumed a
path that no longer existed. Use the menu entry, or:

```sh
~/Applications/platterpus-x86_64.AppImage --version
```

**2. You never needed `--install-ripper` at all.** The b10 wizard built `9048082` by itself —
your log shows it at 19:36:00 with `pin=9048082`, then verified the banner at 19:36:03. The
manual step was redundant, and the "had to install manually" friction was caused by my
instruction, not by the app.

**3. The layout fix worked.** You reported **6 track rows** and *"the title is the widest row"*
— against **2 rows** and a Title/Artist split before. That is the b9 fix confirmed on your
hardware, and it is the one thing on this list that needs no further checking. (Your screenshot
title bar reads `0.6.4b9`, which is the build that carries it — so the measurement is of the
right thing.)

**4. What I have NOT fixed, and am not fixing until you say go.** Your settings-naming ask, the
vague version strings, and the picker-logging gap are all recorded in `TASKS.md` under
*"Rig-session findings, 2026-08-05"* with the code verified. Two of them turned out not to be
what they looked like — details at the end of this sheet.

---

## What b9/b10 changed, and how you would notice

| fixed | how you would notice |
|---|---|
| **"The drive is stuck on a hard-to-read spot (a scratch or smudge)"** on a healthy secure re-read, twice per disc | that warning should now appear **only** when the drive genuinely stops. During a re-read you should see `· verifying track 3 (re-read 2) · about 54m left` |
| **The ETA climbed 54m → 1h50m → 5h40m in 70 seconds** during a re-read | it should **hold** at one number, and say why. Holding for several minutes is correct |
| **The track list opened on 2 rows of 14** | **already confirmed fixed — 6 rows.** Nothing to re-check |
| **Columns shuffled sideways twice per track** (Status swung 48→67→53 px) | the grid should sit perfectly still for a whole rip |
| **`INCOMPLETE RIP (cancelled) — this log covers 14 of 14 disc tracks`** — a banner contradicting itself | a cancel *after* all tracks are out now reads `RIP STOPPED (cancelled)` |
| **`the securing pass was INTERRUPTED`** with no cause | now `INTERRUPTED (you cancelled the rip)` when that is what happened |
| **`eta_trace` went silent** for 541 s and 400 s — the exact minutes the estimate was wrong | every sample now carries a `state` (`computed` / `held_no_rate` / `rereading` / `stalled`) |

> **Two things to watch with your own eyes: the stall warning and the ETA, during tracks 3 and 5.**
> Everything else is in the artifacts.

---

## Step 1 — Start the rip and let it finish (~50–70 min)

Launch from the applications menu. Insert the Police disc.

**If MusicBrainz reports more than one match — and on this disc it reports 4 — a modal picker
opens and the app waits for you.** Your last session sat for 96 seconds in exactly that state
before you closed it, and **the log cannot tell me whether the dialog was visible**, because
that code path logs nothing at all on any branch. So:

- If the window looks idle with `MusicBrainz match: 4 matches found — pick one` on screen,
  **look for a separate "Choose a release" window** — check other virtual desktops and behind
  the main window before concluding it is hung.
- If you find no such dialog anywhere, **that is a real finding** and I want to know: it means
  the picker was created and not presented, which is the half I could not settle from the code.

Then start the rip and watch the status line during **tracks 3 and 5** — the two that needed
re-reading in every previous session.

**Should appear:**

```
Ripping track 3 of 14… 14%  ·  verifying track 3 (re-read 2)  ·  about 54m left
```

**Should NOT appear:**

- `stalled 3m 0s — the drive is stuck on a hard-to-read spot (a scratch or smudge)` **while
  cyanrip's own percentage is still climbing**
- the estimate climbing while the overall bar is frozen

If the stall warning appears anyway, note roughly when. Both signals are in the log so I can
settle it from the artifacts — but knowing what you *saw* tells me which of the two misfired.

**Also:** the track grid should not twitch as tracks complete.

---

## Step 2 — Check the cue sheet (2 minutes — this is what closes the handshake round)

The cue fix is **the only change in the fork's pin that no drive has ever run.** One look
settles it:

```sh
cd ~/Music/rips/The\ Police/Every*
grep -n "INDEX 00" *.cue
```

| tracks | expected |
|---|---|
| **3, 6, 11, 12** | **no `INDEX 00`** — the zero-length pre-gaps their fix stops writing |
| 2, 4, 5, 7, 8, 9, 10, 13, 14 | `INDEX 00` still present |

**If a pre-gap you expected has gone missing, that is a finding and their fix goes back** —
their words. Send the cue either way: a correct result closes the round, a wrong one is worth
more.

---

## Step 3 — One command, unattended

```sh
bash ~/path/to/Platterpus/scripts/rig_session.sh ~/rig-b10
```

14 steps, one artifact each, never stops on a failure. Covers `--doctor`, the dependency probe,
the ETA sweep, log sizes and retention, a fresh cyanrip clone + build, handshake status, **and
the fork's `-x` and `-j`** — so you do not need to run those by hand.

**Must end with a `COMPLETE` banner.** If it does not, send what it produced anyway; where it
stopped is the finding. A step timing out on `-x` is the wedge case the fork has been asking
about for four laps — send that too.

---

## Step 4 — Send me these

From the album folder:

```
Every Breath You Take∶ The Classics.log
Every Breath You Take∶ The Classics.platterpus.json
Every Breath You Take∶ The Classics_EACcompatible.log
Every Breath You Take∶ The Classics.cue
Every Breath You Take∶ The Classics.platterpusaddendum.txt   (if any track was re-ripped)
```

Plus:

```
~/.local/share/platterpus/log.txt          (and log.txt.1 … if present)
~/rig-b10/                                 (the whole folder from step 3)
```

**No FLACs** — the repo is public and the logs + CRCs prove everything the audio would.

### The first thing I will open

`eta_trace.samples[].state` in the JSON. The b8 trace had two holes totalling ~16 minutes,
landing exactly on the minutes the estimate was wrong, because a held estimate recorded nothing.
**If b9/b10's trace still has a gap during the re-reads, the fix is incomplete and I will know
immediately.**

---

## Optional — the cancel case (5 minutes)

You partly ran this already at 19:40 and it produced something worth naming, so the shape below
is refined from what actually happened.

1. Start a rip. **Let it get past the last track** — watch for the AccurateRip summary or the
   securing pass starting. (Last time you cancelled at 7 seconds, during `Tracks:`, which is a
   different case: nothing had been written yet.)
2. Cancel.
3. In the `_EACcompatible.log`:
   - **`RIP STOPPED (cancelled)`** — *not* `INCOMPLETE RIP (cancelled) — this log covers 14 of
     14 disc tracks`, which is the self-contradiction b9 fixed
   - if a securing pass had started: **`INTERRUPTED (you cancelled the rip)`**
4. In the JSON: `outcome.status` must be `"cancelled"`, not `"success"`.

**Expected and not a defect:** cancelling early logs
`ripper.log_verify_failed: No FUN512 checksum found` — cyanrip had not written its checksum
footer yet, so its own verifier correctly rejects a partial log. Your 19:40 run shows exactly
this. It is the diagnostic working, not a fault. Worth confirming it *still* says something that
specific rather than a bare failure.

---

## What is still not fixed, honestly

- **Your settings-naming ask is recorded, not started** — and it is a design question rather
  than a bug, because the *auto-Custom* half already works. I verified that by running the real
  dialog: all six preset-driven controls flip the Goal to `Custom (hand-tuned below)`
  immediately, it persists, and a config matching no preset re-opens as Custom. Your screenshot
  shows `Archival exact` with **Debug logging on** because debug logging is not one of the
  preset's fields — so what you are asking for is a label that describes state the preset does
  not cover. That needs a decision on which fields a label may mention before any code moves.
- **One genuine defect fell out of checking that:** the Goal combo ignores the *persisted*
  `rip_goal` and re-derives it from the field values, so a saved goal can disagree with what the
  dialog shows — and the rip report writes `settings.rip_goal`, so the record can name a goal
  the settings never matched. Recorded.
- **The vague version strings are confirmed and are captured-and-discarded**, which is the worse
  kind. The dependency dialog shows `cyanrip 0.9.4 (the Platterpus fork)` while the binary's own
  banner is `0.9.4-rc1+platterpus.5-beta.5 (platterpus-fork-g9048082)` — and **both the full
  banner and the build tag are already in the object that dialog receives.** Same for the wizard
  rows (`✓ Platterpus fork of cyanrip (build + export) — already present` names no commit, while
  the code deciding "already present" reads the expected pin two lines earlier). Recorded.
- **The +450 AccurateRip question is open on the fork's side.** Our half is ruled out. Nothing
  for you to do.
- **Round 7 is still OPEN, both sides HOLD**, so `v0.6.4b10` is a pre-release and not a claim
  that the pair is verified. Your step 2 is what unblocks it.
- **The ETA still under-estimates** (median −23 min on b8). Deliberately untouched: a
  stable-but-low number is a far smaller problem than one that triples in a minute, and the b9/b10
  trace is the data to fix it properly rather than by guessing.

---

*Last updated for Platterpus v0.6.4b13.*
