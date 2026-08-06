# Rig session — the current sheet

```
Platterpus  v0.6.4b13      GitHub PRE-RELEASE
cyanrip     9048082        0.9.4-rc1+platterpus.5-beta.5   (platterpus-fork-g9048082)  <- installed
cyanrip     dc21958        0.9.4-rc1+platterpus.5-beta.6   TEST PIN, not yet installed
drive       Pioneer BDR-209D 1.51, read offset +667
round 7     OPEN — HOLD on both sides. Nothing here is a verified pair.
```

**This is the one rig sheet.** It replaces the four build-specific sheets that had
accumulated (`b9`, `b10`, `c5fb909`, `f5e11ba`); those are in
[`docs/archive/`](archive/) with their audit trail intact. The header above names the pair
this sheet is written for — when the pair moves, this file is rewritten rather than a fifth
one added.

**Where the AppImage lives.** You accepted the first-run "add to menu" offer, so the app
**moved itself** to `~/Applications/platterpus-x86_64.AppImage`. Nothing is left in
`~/Downloads`, and a `./platterpus-x86_64.AppImage …` command run from there says
*No such file or directory* — that is the app behaving correctly and my earlier instruction
being wrong. Launch from the applications menu; for a terminal command use the full path.

**The ripper is already right.** Your log shows `9048082` built by the b10 wizard on its
own — no `--install-ripper` needed, and none needed now:

```
19:38:36  cyanrip 0.9.4-rc1+platterpus.5-beta.5 (platterpus-fork-g9048082)
```

---

## The next rip's acceptance criteria — round 7 lap 31

**Read this before the rip, not after.** Four checks, and each one has a *"and nowhere
else"* half or a negative control, because a count alone passes on the wrong set. The
first three are the fork's own J1 wording (lap 30); the fourth is ours.

Requires the **test pin** `dc21958` (beta.6) — see `--install-ripper` below. The three
changes it carries have been near no drive, which is exactly why this list exists.

| # | check | pass | why it can pass for the wrong reason |
|---|---|---|---|
| 1 | **ISRCs in the cue** | **all 14**, one per track | "more than before" is not the criterion. beta.1 wrote **1**, beta.5 wrote **5**. A partial improvement looks like success. |
| 2 | **`INDEX 00` markers** | on exactly **2, 4, 5, 7, 8, 9, 10, 13, 14** — and **nowhere else** | beta.1 wrote **13** markers, four of them (**3, 6, 11, 12**) for pre-gaps its *own log* measured at **0 frames**. A count of 9 with the wrong set passes a count check. |
| 3 | **the `Offset:` line** | **unchanged** from the b12 rip | the negative control for their new `-s` bound. If this moved, the bound changed behaviour on a value we send. |
| 4 | **the real colon** *(ours)* | the cue's album `TITLE` **and** the log's `album:` field both read `Every Breath You Take: The Classics` | beta.6 + app 0.6.4b13 is the first pair where this can be observed. If either shows `∶` or a truncated title, the `\:` escape did **not** survive and lap 31 §C's verdict is wrong. |

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

## Step 0 — Update to b11 (2 minutes, no disc)

**Help → Check for updates** → accept → restart. Beta updates are already enabled from last
time.

Then **Help → About** must read **0.6.4b11**. If it still says b10 the update did not take —
tell me rather than working around it.

---

## What b11 changed, and how you would notice

Everything in this table came out of *your* b10 walkthrough. Six things you raised; two of
them turned out not to be what they looked like, and that is written down honestly at the
end rather than quietly dropped.

| you said | what b11 does |
|---|---|
| *"These settings should be called something like Flack - Lossless Archival Master [Debugging] … and other settings should reflect similar naming syntax"* | **Every option in every Settings dropdown** now reads `Name — Descriptor In Title Case [Qualifier]`. Five combos, 20 options, one syntax — and a test sweeps the real dialog, so a dropdown added later can't reintroduce a sixth phrasing |
| *"some of these screens are very vague on the version number and type also"* | The dependency list now reads `cyanrip 0.9.4-rc1+platterpus.5-beta.5 (the Platterpus fork; build tag "platterpus-fork-g9048082")` instead of `cyanrip 0.9.4 (the Platterpus fork)`. The wizard's fork row names the commit |
| *"it stopped when I closed platterpus because it looked hung, might be wrong"* | You were **not** wrong — the app was waiting on the release picker and the log said nothing at all for 96 seconds. Every dialog now logs that it was put on screen and how it closed; the picker also logs the candidate count and the words **"this is not a hang"** |
| *"the layout had 6 tracks … the title is the widest row"* | **Already confirmed fixed on your hardware.** Nothing to re-check |

Plus three you would not see on any screen, all in the CHANGELOG: a defect I found while
checking your naming ask (a rip's JSON could name a Goal its own settings never matched),
one the project's own regex guard caught in my *new* code, and one the new dialog sweep
caught — `DiagnosticsDialog` was the single dialog that opted out of the base class, so the
**diagnostics** window was the one that left no trace of having been opened.

---

## Step 1 — Read the Settings dialog (2 minutes, no disc)

This is the change you asked for, and it is entirely an eyes-on check.

**Tools → Settings.** Open each of the five dropdowns:

| dropdown | should now read |
|---|---|
| **Goal** | `Fast Verified — Lossless, Fully Verified (AccurateRip + CTDB) [Recommended]`<br>`Archival Exact — Fully Verified, Smallest Lossless Files`<br>`Portable — MP3 Derived From a Fully Verified Master`<br>`Custom — Hand-Tuned Below` |
| **Naming scheme** | `Artist / Album / 01 - Title — Simple, No Year Clutter [Recommended]`<br>`Artist / Album / 01 Title — Same Layout, No Dash`<br>`Artist / Album (Year) / 01 - Title — Plex and Jellyfin Style`<br>`Artist / Year - Album / 01 - Title — Chronological, foobar2000 Style`<br>`Artist / Album / 01 - Track Artist - Title — Compilations, Various Artists`<br>`Custom — Hand-Tuned Below` |
| **Output format** | `FLAC — Lossless Archival Master [Recommended]`<br>`WavPack (.wv) — Lossless, Keeps Tags and Cover Art`<br>`MP3 — Lossy, Best-Quality VBR, Keeps Tags and Cover Art`<br>`WAV — Raw PCM, No Tags or Cover Art` |
| **Cover art** | `Don't Fetch — No Cover Art at All`<br>`Embed in FLAC — Art Inside Each Track`<br>`Save as File — Art Beside the Tracks`<br>`Embed and Save File — Both [Recommended]` |
| **Read speed** | `Adaptive Ladder — Fast, Slower Only if a Disc Needs It [Recommended]`<br>`Fixed Speed — Always the Speed Set Below [Advanced]` |

**What I need from you here is a judgement, not a pass/fail.** The syntax is now uniform;
whether the *words* are the right ones is your call. If any label is too long for the
dropdown at your font size, or says the wrong thing, name it and I will change that one —
the convention is enforced by a checker, so a reword costs nothing and can't drift.

**Then check the auto-Custom half of your ask, which already worked before b11** and I want
confirmed on real hardware rather than only in a test:

1. Note what **Goal** says (probably `Archival Exact …`).
2. Change **Read speed** to `Fixed Speed — Always the Speed Set Below [Advanced]`.
3. **Goal must flip to `Custom — Hand-Tuned Below` immediately**, before you click anything.
4. Click **OK**, reopen Settings → it must still say Custom.
5. Set Read speed back to `Adaptive Ladder …`, OK, reopen → back to `Archival Exact …`.

> **Why your screenshot showed `Archival exact` with debug logging on, and that was correct.**
> Debug logging is not one of the six settings a Goal covers, so turning it on does not make
> the configuration "custom". That is why your ask is a *design* question and not a bug: you
> want a label that mentions state the preset does not own. If you want that — a
> `[Debugging]` suffix on the Goal row when debug logging is on — say so and I will add it;
> I have deliberately not guessed, because it means deciding which fields a label may speak
> for.

---

## Step 2 — Read the two "which build?" screens (1 minute, no disc)

**Tools → Check dependencies.** In the *Installed* list, the cyanrip row must now name the
pre-release **and** the commit:

```
cyanrip 0.9.4-rc1+platterpus.5-beta.5 (the Platterpus fork; build tag "platterpus-fork-g9048082")
```

If it still says `cyanrip 0.9.4 (the Platterpus fork)`, the fix did not ship — that is a
finding.

**Tools → Set up Platterpus…** (it is safe to open and cancel; nothing runs until you
confirm). The fork row must now read:

```
✓ Platterpus fork of cyanrip (build + export) — commit 9048082
    already present — the installed banner names commit 9048082
```

**Cancel out.** Both of these are read-only checks.

---

## Step 3 — The picker, and the silence you reported (5 minutes)

Insert the Police disc. MusicBrainz reports **4 matches** for it, so a modal
**"Pick a MusicBrainz release"** window opens and the app waits for you. **That is what
happened last time**, and closing the app was a reasonable response to a window that says
nothing.

**What is different now.** The log gets these, in order:

```
MusicBrainz returned 4 candidates for disc '…' — opening the release picker;
  the app will WAIT here until the user chooses (this is not a hang)
dialog presented: ReleasePickerDialog ('Pick a MusicBrainz release') — the app now waits for the user
dialog closed: ReleasePickerDialog ('Pick a MusicBrainz release') — accepted
release picker: user chose <mbid> after 12.4s
```

**What I want you to do:**

1. When the picker appears, **leave it for ~30 seconds without answering.** (This is
   deliberate: it produces the exact silence you saw, and now it should be a *documented*
   silence.)
2. **If no picker window appears anywhere** — check other virtual desktops and behind the
   main window — **that is the real finding.** The log will now settle it: a
   `dialog presented:` line means Qt really put it on screen and something is covering it; no
   such line means it was created and never shown. I could not answer that from the b10 log
   at all, which is why this step exists.
3. Pick the release that matches the disc and continue.

---

## Step 4 — The rip, watching two things with your eyes (~50–70 min)

Start the rip. **Watch the status line during tracks 3 and 5** — the two that have needed
secure re-reads in every previous session.

**Should appear:**

```
Ripping track 3 of 14… 14%  ·  verifying track 3 (re-read 2)  ·  about 54m left
```

**Should NOT appear:**

- `stalled 3m 0s — the drive is stuck on a hard-to-read spot (a scratch or smudge)`
  **while cyanrip's own percentage is still climbing.** On b8 this fired twice per disc on a
  perfectly healthy disc.
- the estimate climbing while the overall bar is frozen. It may **hold** at one number for
  several minutes — that is correct and deliberate.

**Also:** the track grid should sit perfectly still as tracks complete. No column should
change width mid-rip.

If the stall warning appears anyway, note roughly when. Both signals are in the log so I can
settle it from the artifacts — but knowing what you *saw* tells me which of the two
misfired.

---

## Step 5 — The cue sheet (2 minutes — this is what closes the handshake round)

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

## Step 6 — One command, unattended

```sh
bash ~/path/to/Platterpus/scripts/rig_session.sh ~/rig-b11
```

14 steps, one artifact each, **never stops on a failure** — a failing step is data, and every
exit code is recorded including the successes. It covers `--version` for both binaries, the
`-dirty`/`-grelease` banner check, `--doctor`, **the fork's `-x` and `-j`** (which our own
argv surface never sends, so you would otherwise have to run them by hand), pre-gap source
counts, a log snapshot taken *before* rotation eats it, `--audit-rips`, an ETA sweep, log
sizes, a fresh cyanrip clone + build, handshake status and preflight.

**It must end with a `COMPLETE` banner.** If it does not, send what it produced anyway —
where it stopped is the finding. A step timing out on `-x` is the wedge case the fork has
been asking about for four laps; send that too.

---

## Step 7 — The cancel case (5 minutes)

1. Start a rip. **Let it get past the last track** — watch for the AccurateRip summary or the
   securing pass starting. (Last time you cancelled 7 seconds in, during `Tracks:`, which is
   a different case: nothing had been written yet.)
2. Cancel.
3. In the `_EACcompatible.log`:
   - **`RIP STOPPED (cancelled)`** — *not* `INCOMPLETE RIP (cancelled) — this log covers 14
     of 14 disc tracks`, which is the self-contradiction b9 fixed
   - if a securing pass had started: **`INTERRUPTED (you cancelled the rip)`**
4. In the JSON: `outcome.status` must be `"cancelled"`, not `"success"`.

**Expected and not a defect:** cancelling early logs
`ripper.log_verify_failed: No FUN512 checksum found` — cyanrip had not written its checksum
footer yet, so its own verifier correctly rejects a partial log. Your 19:40 run showed
exactly this. It is the diagnostic working.

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
~/rig-b11/                                 (the whole folder from step 6)
```

**No FLACs.** The repo is public and the logs + CRCs prove everything the audio would —
that is Critical rule #8 and it has no exceptions, including temporary ones.

### The three things I will open first

1. **`eta_trace.samples[].state` in the JSON.** The b8 trace had two holes totalling ~16
   minutes, landing exactly on the minutes the estimate was wrong, because a held estimate
   recorded nothing. **If b11's trace still has a gap during the re-reads, the fix is
   incomplete and I will know immediately.**
2. **`settings.rip_goal` — and whether `settings.rip_goal_stored` is there beside it.** New
   in schema v23. Its presence means your `config.toml`'s goal label disagreed with its own
   fields, which is worth knowing; its absence means they agreed.
3. **The picker lines in `log.txt`.** Step 3's whole point.

---

## What is still not fixed, honestly

- **Your naming ask is done for the *options*; the `[Debugging]`-on-the-Goal-row half is
  not, and needs your decision** (Step 1's note). It is a design question, not an oversight.
- **The ETA still under-estimates** — median −23 minutes on b8, deliberately untouched. A
  stable-but-low number is a far smaller problem than one that triples in a minute, and the
  b9/b10/b11 traces are the data to fix it properly rather than by guessing.
- **The +450 AccurateRip question is open on the fork's side.** Our half is ruled out.
  Nothing for you to do.
- **Round 7 is still OPEN and both sides are on HOLD**, so `v0.6.4b11` is a pre-release and
  not a claim that the pair is verified. Every rip it makes says so in its own report. Step 5
  is what unblocks it.
- **Two of the five things your screenshots suggested turned out not to be true, and I am
  saying so rather than shipping a fix for them.** (1) The auto-Custom behaviour already
  worked — verified by driving the real dialog, not by reading the wiring. (2) The mechanism I
  first suspected for the picker (a modal swallowing it) is *impossible*: MusicBrainz results
  arrive as a queued cross-thread signal and a nested Qt event loop still delivers those. The
  honest finding was smaller and worse — the log could not answer the question at all.

---

*Last updated for Platterpus v0.6.4b13.*
