# Rig session — the current sheet

```
Platterpus  v0.6.30        GitHub PRE-RELEASE (all v0.* are)
cyanrip     d9c058c        0.9.4-rc2+platterpus.10  (platterpus-fork-gd9c058c)  <- PRODUCTION PIN
                           approved by round 14, for Platterpus 0.6.28
cyanrip     978f9b0        0.9.4-rc2+platterpus.11  the fork's newest — NO round has
                           reviewed it; installing it reports `unapproved`, correctly
drive       Pioneer BDR-209D 1.51, read offset +667
rounds 1-14 ALL CLOSED, bilateral GO. Round 15 is not open and is the fork's to open.
            This IS a verified pair.
```

> **Header last moved 2026-08-27.** Before that it named `v0.6.4b15` + cyanrip
> `104f6d4`/`9048082` and *"round 7 OPEN — HOLD on both sides"* — 26 minors and seven
> rounds behind, in a sheet whose own contract one paragraph down is *"rewritten in
> place when the pairing moves"*. A sheet that names the wrong pair is worse than no
> sheet, because a run against it produces evidence about a different subject.

**This is the one rig sheet.** It is rewritten in place when the pairing moves, never
joined by a sibling — the header above names the pair it is written for. Superseded
originals are in [`docs/archive/`](archive/) with their audit trail intact.

**Where the AppImage lives.** You accepted the first-run "add to menu" offer, so the app
**moved itself** to `~/Applications/platterpus-x86_64.AppImage`. A `./platterpus-x86_64.AppImage …`
command run from `~/Downloads` says *No such file or directory* — that is the app behaving
correctly. Launch from the applications menu; for a terminal command use the full path.

---

## Read this first: `-Z` is ON, and it is not doing what "on" sounds like

**You asked the right question — *"the app builds the argv, so `-j` and `-Z` are its call;
worth checking they're on before you start rather than discovering afterwards."*** Here is
the answer, measured from the code rather than remembered:

| flag | what a default rip actually does |
|---|---|
| **`-Z` (secure re-read)** | **On at 2 — but in DYNAMIC mode.** Pass 1 reads the whole disc **without `-Z`** at speed. Only tracks that then *miss* AccurateRip are re-read with `-Z 2`. On a disc that fully matches AccurateRip, **`-Z` is never applied at all.** |
| **`-j` (diagnostics record)** | **Never sent.** It is not in our argv surface — 16 flags, and `-j` is not one of them. The rig harness runs it directly against the binary (step 5b), which is the only way that record exists. |
| **`-N`** | Always sent, unconditionally, and asserted at the argv chokepoint. |

**Neither is a bug**, and both are now stated *before* the rip rather than discoverable
afterwards: b15 prints a **`[plan]`** block into the log and the on-screen live log as the
very first thing a rip does, naming every flag it is about to use. Read it; it takes ten
seconds and it is the whole point of this change.

### The `-Z`-on-every-track rip: **do not run it.** The question is already answered.

The earlier version of this sheet asked for one Test & Copy rip (roughly double
the time) to check the fork's claim that per-track paranoia counters sum to the
disc totals — because both previous checks had been made on rips *without* `-Z`,
where the sum is arithmetically forced.

**The J1 rip already contained both cases**, in two separate invocations, and it
settles it:

| pass | argv | tracks | per-track sum | disc total | |
|---|---|---|---|---|---|
| album | no `-Z` | 14 | READ **21972** | READ **21972** | equal, all four counters |
| refix | `-Z 2 -l 5` | **1** | READ **1538** | READ **7738** | **not equal** |

One track in the refix pass, so there is no summation ambiguity: the per-track
figure *is* the sum. Track 5 converged after 5 reads; 7738 / 1538 = 5.03.

**The invariant does not hold under `-Z`.** Under it, the per-track number is the
*last* pass and the disc total is *every* pass. The consequence is a rendering
caveat for whoever displays disc-level tallies, not a defect in the ripper — and
it cost no rig time, because the evidence was in the artifact you already sent.

So: **rip with your normal settings.** Nothing on this sheet needs Test & Copy.

---

## The next rip's acceptance criteria — round 7 laps 31/33

**Read this before the rip, not after.** Four checks, and each one has a *"and nowhere
else"* half or a negative control, because a count alone passes on the wrong set. The first
three are the fork's own J1 wording (lap 30); the fourth is ours.

Requires the **test pin** `104f6d4` (beta.8). `beta.6` was withdrawn by the fork (a `-t`
with no `=` read past the end of the string and published what it read); `beta.7` fixed it
plus four segfaults, and **beta.8 is beta.7's ripping code with different packaging** —
`git diff 4a35604..104f6d4 -- 'src/*.c' 'src/*.h'` is empty, and their source anchor is
unchanged across the pair.

| # | check | pass | why it can pass for the wrong reason |
|---|---|---|---|
| 1 | **ISRCs in the cue** | **all 14**, one per track | "more than before" is not the criterion. beta.1 wrote **1**, beta.5 wrote **5**. A partial improvement looks like success. |
| 2 | **`INDEX 00` markers** | on exactly **2, 4, 5, 7, 8, 9, 10, 13, 14** — and **nowhere else** | beta.1 wrote **13** markers, four of them (**3, 6, 11, 12**) for pre-gaps its *own log* measured at **0 frames**. A count of 9 with the wrong set passes a count check. |
| 3 | **the `Offset:` line** | **unchanged** from the b12 rip | the negative control for their new `-s` bound. If this moved, the bound changed behaviour on a value we send. |
| 4 | **the real colon** *(ours)* | the cue's album `TITLE` **and** the log's `album:` field both read `Every Breath You Take: The Classics` | this is the first pair where it can be observed. If either shows `∶` or a truncated title, the `\:` escape did **not** survive and lap 31 §C's verdict is wrong. |

Commands, run in the rip folder afterwards:

```bash
# 1 — must print 14
grep -c '^ *ISRC ' *.cue

# 2 — must print exactly: 2 4 5 7 8 9 10 13 14
awk '/^ *TRACK/ {t=$2+0} /^ *INDEX 00/ {printf "%d ", t} END {print ""}' *.cue

# 3 — compare against the b12 rip's log; the number must be identical
grep -n 'Offset:' *.log

# 4 — all three must show a real ':' and no U+2236
grep -n '^TITLE' *.cue
grep -n 'album:' *.log
metaflac --show-tag=ALBUM *.flac | head -1
```

**If any of the four fails, stop and report it rather than re-ripping.** A failure here is
information the round needs; a second rip over the top of it loses the artifact that proves
which build did what.

---

## Step 0 — Update, and confirm both halves

**Help → Check for updates** → accept → restart. Beta updates are already enabled.

Then:

- **Help → About** must read **0.6.4b15**.
- **Tools → Check dependencies** — the cyanrip row must read
  `cyanrip 0.9.4-rc1+platterpus.5-beta.8 (the Platterpus fork; build tag "platterpus-fork-g104f6d4")`.

If the ripper still says beta.5/`9048082`, install the test pin — no source checkout needed:

```sh
~/Applications/platterpus-x86_64.AppImage --install-ripper 104f6d4
```

---

## Step 1 — Settings

1. **Turn ON** "Verify every track with a second read (EAC-style Test & Copy)" (see the
   section above — this is the one deliberate change for this rip).
2. Leave everything else as it is.
3. **OK**, then reopen Settings and confirm it stuck.

Note that the **Goal** will flip to `Custom — Hand-Tuned Below`. That is correct: you have
hand-tuned a field the preset owns.

---

## Step 2 — The picker

Insert the Police disc. MusicBrainz reports **4 matches**, so a modal **"Pick a MusicBrainz
release"** window opens and the app waits for you. **Leave it ~30 seconds without answering**
— that reproduces the silence you reported, and it should now be a *documented* silence:

```
MusicBrainz returned 4 candidates for disc '…' — opening the release picker;
  the app will WAIT here until the user chooses (this is not a hang)
dialog presented: ReleasePickerDialog ('Pick a MusicBrainz release') — the app now waits for the user
```

**If no picker window appears anywhere** — check other virtual desktops and behind the main
window — **that is the real finding.** A `dialog presented:` line means Qt really put it on
screen and something is covering it; no such line means it was created and never shown.

---

## Step 3 — The rip (~100–140 min with Test & Copy on)

**Before the disc spins, read the `[plan]` block** in the live log pane (or
`~/.local/share/platterpus/log.txt`). Confirm:

- `Secure re-read (-Z): ON at 2 … UNIFORM`
- `Read offset (-s): +667 samples`
- `Tracks (-l): whole disc (14 on the TOC)`
- `MusicBrainz lookup (-N): ALWAYS disabled`

**Then watch two things with your eyes.**

**Should appear:**

```
Ripping track 3 of 14… 14%  ·  verifying track 3 (re-read 2)  ·  about 54m left
```

**Should NOT appear:**

- `stalled 3m 0s — the drive is stuck on a hard-to-read spot (a scratch or smudge)`
  **while cyanrip's own percentage is still climbing.**
- the estimate climbing while the overall bar is frozen. It may **hold** at one number for
  several minutes — that is correct and deliberate.

The track grid should sit perfectly still as tracks complete; no column should change width
mid-rip.

---

## Step 4 — The cue sheet (2 minutes — this is what closes the round)

```sh
cd ~/Music/rips/The\ Police/Every*
grep -n "INDEX 00" *.cue
```

| tracks | expected |
|---|---|
| **3, 6, 11, 12** | **no `INDEX 00`** — the zero-length pre-gaps their fix stops writing |
| 2, 4, 5, 7, 8, 9, 10, 13, 14 | `INDEX 00` still present |

**If a pre-gap you expected has gone missing, that is a finding and their fix goes back** —
their words. Send the cue either way: a correct result closes the round, a wrong one is
worth more.

---

## Step 5 — One command, unattended

**This no longer needs a source checkout.** It used to say
`bash ~/path/to/Platterpus/scripts/rig_session.sh …` — a placeholder path to a file that
only exists in the git repository, which you do not have on the rig. The harness now ships
*inside* the app:

```sh
~/Applications/platterpus-x86_64.AppImage --rig-session ~/rig-b15
```

Fourteen steps, one artifact each, **never stops on a failure** — a failing step is data, and
every exit code is recorded including the successes. It covers `--version` for both binaries,
the `-dirty`/`-grelease` banner check, `--doctor`, **the fork's `-x` and `-j`** (which our
own argv surface never sends, so this is the only place those records come from), pre-gap
source counts, a log snapshot taken *before* rotation eats it, `--audit-rips`, an ETA sweep,
log sizes, a fresh cyanrip clone + build, handshake status and preflight.

**It must end with a `COMPLETE` banner.** If it does not, send what it produced anyway —
where it stopped is the finding. A step timing out on `-x` is the wedge case the fork has
been asking about for four laps; send that too.

---

## Step 6 — The cancel case (5 minutes)

1. Start a rip. **Let it get past the last track** — watch for the AccurateRip summary or the
   securing pass starting.
2. Cancel.
3. In the `_EACcompatible.log`:
   - **`RIP STOPPED (cancelled)`** — *not* `INCOMPLETE RIP (cancelled) — this log covers 14
     of 14 disc tracks`
   - if a securing pass had started: **`INTERRUPTED (you cancelled the rip)`**
4. In the JSON: `outcome.status` must be `"cancelled"`, not `"success"`.

**Expected and not a defect:** cancelling early logs
`ripper.log_verify_failed: No FUN512 checksum found` — cyanrip had not written its checksum
footer yet, so its own verifier correctly rejects a partial log. That is the diagnostic
working.

---

## Step 7 — Optional: the in-app test console

New in b15, and the reason it is worth two minutes of your time: the scripting subsystem
you asked for (*"a debug testing option where i can copy and paste command code into it so i
dont need to be present"*) had been **built and left unreachable** — no menu item, no
dialog, no flag. It is now **Tools → Run test script…**.

Open it and press **Run** on the starter script it comes with. It should open Settings,
screenshot it, close it, and print a transcript ending in a verdict. That is the smallest
possible proof the wiring works.

Settings also has a **Test script** field (a file it loads by default) and **Run it
automatically when Platterpus starts** — both off unless you set them, and both needed for
an unattended launch to run a batch.

---

## Step 8 — Send me these

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
~/rig-b15/                                 (the whole folder from step 5)
```

**No FLACs.** The repo is public and the logs + CRCs prove everything the audio would —
Critical rule #8, no exceptions including temporary ones.

### The four things I will open first

1. **The `[plan]` block in `log.txt`** — confirming the rip ran with the flags you set,
   checked against the ripper's own `Invoked as:` line. Two independent records of the same
   decision; if they disagree, that is a finding worth more than the rip.
2. **The per-track paranoia counters under `-Z`** — the round-5 claim, finally checked where
   it could have failed.
3. **`eta_trace.samples[].state` in the JSON.** The b8 trace had two holes totalling ~16
   minutes, landing exactly on the minutes the estimate was wrong.
4. **The picker lines in `log.txt`.** Step 2's whole point.

---

## What is still not fixed, honestly

- **The ETA still under-estimates** — median −23 minutes on b8, deliberately untouched. A
  stable-but-low number is a far smaller problem than one that triples in a minute.
- **The `[Debugging]`-on-the-Goal-row half of your naming ask is not done, and needs your
  decision.** It is a design question (which fields a label may speak for), not an oversight.
- **The +450 AccurateRip question is open on the fork's side.** Our half is ruled out.
- **Round 7 is still OPEN and both sides are on HOLD**, so `v0.6.4b15` is a pre-release and
  not a claim that the pair is verified. Every rip it makes says so in its own report.
- **The `-j` record still comes only from the harness**, not from a rip. We do not send it
  and are not proposing to: adding a flag to every rip's argv to satisfy one round's evidence
  need is the wrong trade. Step 5 produces the record.

---

*Last updated for Platterpus v0.6.30.*
