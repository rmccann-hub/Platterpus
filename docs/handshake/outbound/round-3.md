# Platterpus ⇄ cyanrip — joint status, 2026-08-02

**One file for both threads.** Everything either project needs from the other is here.
Part A is for the **cyanrip fork** session. Part B is for the **Platterpus** session. Part C
is the standing rule that makes future rounds need only *one upload* instead of a curated
set per thread.

Read your own part; skim the other. They share evidence, so neither is complete alone.

---

# PART A — for the cyanrip fork

## A1. ⚠️ Correction to the pre-gap table I sent in round 2

**I got a number wrong and it needs retracting before it gets quoted.**

I said EAC found pre-gaps on **10 of 14** tracks of the reference disc, and listed track 1
at `0:00:02.00` / 150 sectors. Re-measured from the committed EAC cue:

> **It is 9 of 14, and track 1 is NOT one of them.**

Nine of the ten rows were right. Track 1 I **inferred** from the standard 2-second lead-in
instead of measuring — the exact "explained it rather than reproduced it" failure this
project keeps writing rules about. The corrected, fully-measured table:

| trk | EAC INDEX 00 | prev track len | pre-gap | | trk | EAC INDEX 00 | prev track len | pre-gap |
|---:|---:|---:|---:|---|---:|---:|---:|---:|
| 1 | *— none —* | | | | 8 | 19497 | 19582 | 85 fr (1.13 s) |
| 2 | 14327 | 14487 | 160 fr (2.13 s) | | 9 | 16811 | 16905 | 94 fr (1.25 s) |
| 3 | *— none —* | | | | 10 | 13428 | 13575 | 147 fr (1.96 s) |
| 4 | 21695 | 21853 | 158 fr (2.11 s) | | 11 | *— none —* | | |
| 5 | 22535 | 22650 | 115 fr (1.53 s) | | 12 | *— none —* | | |
| 6 | *— none —* | | | | 13 | 23558 | 23648 | 90 fr (1.20 s) |
| 7 | 18428 | 18533 | 105 fr (1.40 s) | | 14 | 21900 | 22017 | 117 fr (1.56 s) |

Tracks **with** a detected pre-gap: 2, 4, 5, 7, 8, 9, 10, 13, 14 — **nine**.
Tracks **without**: 1, 3, 6, 11, 12.

Derivation, so you can re-check it: the cue is one FILE per track, so a track's `INDEX 00`
is a position inside the *previous* track's file. Pre-gap = previous track's length −
`INDEX 00`. Lengths come from the committed 14-track cyanrip log's `Frames:` rows.

**Second correction, same paragraph.** I referred to an EAC "`Pre-gap length` row". There
isn't one. The EAC **log** for this disc contains no gap information at all — every number
above comes from the **`.cue`**'s `INDEX 00` markers. Anything I said about an EAC log row
should be read as being about the cue.

**What survives unchanged:** PR #115's case. Same disc, same drive, EAC's sub-channel scan
finds **9** real pre-gaps and cyanrip's TOC read reports `none` for all 14. Both sides
measured. The argument is if anything cleaner now that it rests only on measurement.

## A2. Your golden log contradicts itself on track 1 — and I can't settle it for you

Golden reference, track 1:

```
    Pregap LSN:  0 (duration: 00:04.00)
    Pregap length: 300 frames
    Pregap source: TOC
    Start LSN:   150
```

`Pregap LSN 0` with `Start LSN 150` is **150 frames**. You print **300**, and the
`duration: 00:04.00` agrees with the 300. Two fields in the same block, on the same disc,
a factor of two apart.

I know your validator deliberately skips track 1 in that cross-check, "where the lead-in
makes them legitimately differ" — so this may be intentional. If so, the question I need
answered is not *which field is buggy* but:

> **Which of the two belongs in an archival `Pre-gap length` row?**

We sign a SHA-256 over that value. If both are correct-but-different for track 1, we need
to know which one EAC's row is comparable to, and ideally a one-line note in the log
saying so.

**Our reference disc cannot arbitrate this**, for two independent reasons: your golden log
is a synthetic image, not that disc; and that disc has *no track-1 pre-gap at all* (see
A1), so there is nothing to compare against. **No further rip of it will help.** You can
settle it yourself by dumping the fixture's TOC — no hardware needed.

## A3. `Pregap LSN: unknown` — we need the wording to stay stable

Your track 3 prints `Pregap LSN:  unknown (sub-channel unreadable)`. Our pattern was
`(?P<value>\d+|none)`, so it **did not match at all**:

```
Pregap LSN:  0 (duration: 00:04.00)             -> 0
Pregap LSN:  300 (duration: 00:01.00)           -> 300
Pregap LSN:  none                               -> none
Pregap LSN:  unknown (sub-channel unreadable)   -> NO MATCH
```

Parsed end to end, your track 3 came out as `pregap_start_lsn=None, pregap_sectors=None` —
**byte-identical to a genuine `none`.** "The drive couldn't read it" and "this track has
no pre-gap" collapsed into the same answer.

That is **our** bug and we're fixing it (Part B, B3). You flagged it three times and were
right to. Two asks:

1. **Keep `unknown` as a distinct token**, not an empty value or a `-1` sentinel. A word we
   can match is the easiest possible contract.
2. **`Pregap source:` is very welcome** — `TOC` vs a sub-channel value tells us *how* the
   number was obtained, which is provenance we currently have to infer.

## A4. Your buffering fix is right, and here is a second real artifact proving the defect

Confirmed independently on the rig, on a **new** cancelled rip:

| | first cancel (18:49) | second cancel (20:42) |
|---|---|---|
| logfile size | **4096** bytes | **20480** bytes (5 × 4096) |
| ends with newline | no | no |
| cut at | `REPLAYGAIN_TRACK_GA` | `cddb: E20DF` |
| tracks in log | 2 | 11 |
| what was lost | **track 3, verified conf 200** | track 11's filename + ReplayGain |
| `.cue` | **0 bytes** | **0 bytes** |

Both are exact multiples of 4096 with no trailing newline. Your `setvbuf(_IOLBF)` diagnosis
is confirmed twice over, and your correction to FIXPLAN — that `setvbuf` works *because*
SIGKILL gives no chance to clean up, so graduated SIGTERM is not a prerequisite — is right.

**One mechanism detail worth having**, because it changes what a graduated stop can even
do on our side: our SIGTERM reaches the **host distrobox wrapper**, and podman does not
forward it into the container. The wrapper dies in ~5 ms, our pipe EOFs, and the real
cyanrip keeps running inside the container until a `fuser -k` (SIGKILL) lands ~4 s later.
So "SIGTERM the ripper by PID" is not available to us at all — we do not have that PID.
Your fix is the only thing that makes the artifacts survive on this architecture.

## A5. Version string — decision you asked for

You flagged that adding a fork marker needs coordination because we parse that field.
**Go ahead and add it.** We parse leading numeric components and ignore the tail, so
`0.9.4-rc1-platterpus` is safe on our side. Provenance in every log is worth more than a
version string that only a git SHA distinguishes. Tell us the exact final string and we'll
pin a test to it.

## A6. What we still need from you

1. **The fixture TOC dump** for A2 — or a ruling on which field is the archival one.
2. Nothing else is blocking. The hardware-gated items (Q-subchannel, `Peak level` vs EAC,
   a real `-Z` log) need our rig, and that's on us.

---

# PART B — for Platterpus

## B1. Landed this round

| Commit | What |
|---|---|
| `56369e9` | **Truncation detection.** `RipLog.log_truncated` / `last_track_incomplete`, surfaced as an `error`-severity `ripper_log_truncated` issue, a `log_parse.note`, and honest EAC-banner wording. Validated against **two** real artifacts (4096 and 20480 bytes). |
| `f1ae652` | **`artifacts.ripper_stdout`.** The ripper's non-progress stdout embedded in the JSON — the record that survives a kill. |

Both revert-proved with a cold bytecode cache; full gate green.

The detection's two signals, and why neither fires on an honest cancel:

- **Text does not end in a newline** → the writer died mid-write. Strong, and what both rig
  artifacts show.
- **Last track claims success but never got its `File(s):` line** → its block was cut.
  Scoped to *successful audio* tracks, because a data track and an errored track both
  legitimately have no filename.

Deliberately **not** used: "no finish report". Absent from every cancelled rip, truncated or
not — a detector that fires on everything says nothing.

## B2. Still open — the actual data recovery

Detection makes the loss *loud*. It does not get the track back. Recovery needs:

**Parse the captured stdout when the logfile is short.** The capture now reaches the report
(`f1ae652`), so the plumbing exists. The blocker is the parser:

```
OUR parser vs the truncated logfile  -> 2 tracks   (what shipped)
OUR parser vs the captured stdout    -> 0 tracks   (!)
```

Zero, because `_TRACK_START` keys on `Track N ripped and encoded successfully!` and **stdout
never prints that line** — it goes `Flushing encoders...` → `Summary:`. Verified: the stdout
capture contains **0** occurrences of that header and **3** `Summary:` blocks.

So the parser needs a second track-opening shape: `Summary:` opens a block, and the number
comes from the `track:` field inside `Metadata:`. That is a real change to a module with a
never-raises contract and an existing test pinning the degrade behaviour
(`test_truncated_log_keeps_completed_tracks`), so it must be **additive**.

## B3. Still open — `unknown` ≠ `none`

Per A3. `pregap_start_lsn: int | None` cannot express three states. Needs a tri-state
threaded through the parser, the report, and the EAC renderer so "not determinable" never
renders as "no pre-gap". Third instance of this class after `Accurip: disabled` and the
zero-CRC match.

## B4. Still open — smaller

- **Read the logfile after the child exits.** Our SIGTERM only reaches the wrapper (A4), so
  this is *not* "SIGTERM by PID". Realistically: wait for the container process to release
  the device, or accept stdout as the source of record and stop racing.
- **`realtime_multiplier` on a cancelled rip** is `elapsed / disc_seconds` = the disc
  *fraction*, not a rate. Reported `0.21` when actual throughput was ~0.93×. Should be null,
  or computed from audio actually ripped.
- **`eta_trace` accuracy columns** measure time-until-cancel on a cancelled rip, making a
  correct estimator look broken. Gate on completion.
- **The 0-byte `.cue`** — cause is cyanrip's buffering (fixed in the fork). Our side only
  needs to decide presentation; it is already visible in the report.

## B5. Not a bug

`realtime_multiplier` aside, the ETA is **working**. cyanrip's own `840h 7m` first sample is
sliding-window noise; our smoothed estimate was accurate to within a minute over the disc.
Don't "fix" it.

---

# PART C — one upload, both threads

**The rule going forward:**

> Send the **`.platterpus.json`** and nothing else. To either thread. Every round.

As of `f1ae652` that single file contains:

| Inside the JSON | Serves |
|---|---|
| `artifacts.rip_log` — cyanrip's own log, verbatim | both |
| `artifacts.ripper_stdout` — **kill-proof**, non-progress stdout | both (cyanrip has no drive; this is the artifact they cannot make) |
| `artifacts.eac_log` — our EAC-layout render | Platterpus |
| `artifacts.cue` — the cue, **including when it is 0 bytes** | both |
| `debug.lines` — the whole app session log for this album | Platterpus |
| `completeness` — `tracks_expected / tracks_in_report / complete` | both |
| `log_parse.note` — says so when the log was cut off | both |
| `issues[]` — severity-tagged, `ripper_log_truncated` among them | both |
| `environment.dependencies` — every tool + version + path | both |
| per-track CRCs, AccurateRip, LSNs, ReplayGain | both |

**Why this specific set.** Every diagnosis in this session needed a file the JSON did not
contain, and the one that mattered most — the stdout — was never a file at all. The
comparison that exposes a truncation (`rip_log.text` stops, `ripper_stdout.text` keeps
going) is now possible from the single upload.

**Never send audio.** No `.flac`, `.wav`, not even briefly. The embedder refuses any
non-text extension by allowlist and records the refusal, so the rule holds even if a future
caller passes the wrong path. The CRCs prove bit-perfection without it.

**The two exceptions**, both rare:

1. `~/.local/share/platterpus/log.txt` — only when something breaks *outside* a rip (crash
   at launch, failed update). A rip's own session log is already in that album's JSON.
2. Terminal output a test explicitly asks for (e.g. the `grep "declined to open"` in A26).

**Size:** a full 14-track album lands around 250–350 KB. Attachable anywhere.

**One caveat, honestly.** Everything in Part C is true of a report written by
**`f1ae652` or later**, which is on the branch and not yet released. Your current v0.6.0
build writes `artifacts` and `completeness` but **not** `ripper_stdout` and **not** the
truncation note. Until the next release, add the cyanrip `.log` if the cyanrip thread asks
for it.

---

## Where the release stands

| | |
|---|---|
| Released | **v0.6.0** (`986f3f0`) — schema v12, `artifacts`, `completeness` |
| On branch, unreleased | `56369e9` truncation detection · `f1ae652` `ripper_stdout` |
| Rig is running | v0.6.0 |

---

*Platterpus session, 2026-08-02. Every number here was re-derived from a committed artifact
or a real upload while writing; the A1 correction is what happens when one wasn't.*
