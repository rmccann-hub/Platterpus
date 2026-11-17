SUPERSEDED-BY: EAC-PARITY-PLAN-OF-RECORD-2026-10-26.md (https://claude.ai/artifact/ACChXwKyAGM9wvCTVjqDDo). Do not send this file.
REPORT-FOR: Platterpus session and cyanrip fork session
FROM: the claude-code-skills session, for the owner to pass on once, to both sessions
WRITTEN: 2026-10-26 02:00 UTC (the evening of 2026-10-25 in New York)
EXPIRES: 2026-12-31
SUBJECT: what made EAC trusted, and what Platterpus on Linux still needs to match it

# What made EAC trusted, and where Platterpus stands

## The owner's words, verbatim

Said to the claude-code-skills session on 2026-10-26, about 01:50 UTC:

> "yes and we want to focus on what made it good and universally liked. and make ours the same
> for linux, and porting to windows might be a way longer goal"

On EAC's newer versions, just before:

> "and paid for. not what they stand for, so who knows what else they put in there"

So the aim is what made EAC good, on Linux and open, without what came with it. A Windows build
is a long-term goal, not a goal for now.

This file goes with `for-both-sessions-2026-10-26-eac-parity-independent-check.md` and
`report-for-both-sessions-2026-10-26-four-full-runs.md`. Platterpus's own scorecard is
`docs/eac-parity.md` Part E, at `platterpus@bba81563`. This file doesn't repeat it; it orders the
work by why people trust EAC.

## 1. What made EAC trusted

From EAC's own pages, fetched 2026-10-26, and from what the community built around it:

1. **It checks its own reads, and says where it's unsure.** It reads "almost perfectly" by
   "multi-reading with verify", and "will tell you on which time position the (possible)
   distortion occurred" ([EAC's home page](https://www.exactaudiocopy.de/)). Other rippers of
   its day only corrected jitter, so users had to listen to every track.
2. **It checks the result against everyone else's,** through AccurateRip
   ([Wikipedia](https://en.wikipedia.org/wiki/Exact_Audio_Copy), citing PC World), and later
   CTDB, whose plugin also names the samples that differ.
3. **Its log lets anyone check a rip without the disc.** The settings and every track's result
   are on the page. Trackers built logcheckers on it (Platterpus's `docs/eac-parity.md`
   Part D).
4. **The right settings are known and shared.** Guides set it up the same way, and AccurateRip's
   drive-offset list was largely built from EAC users (Part E6).
5. **It copies the disc exactly:** the offset, gaps and pregaps, a cue sheet, ISRCs and
   pre-emphasis.
6. **It's free,** and it has run on thousands of drives for over twenty years.

**What isn't worth copying:**
- it's closed source;
- it runs on Windows only;
- it needs a guide to set up;
- it ships a paid metadata plugin;
- it prints "Copy OK" over a track AccurateRip rejects.

Platterpus already avoids the first four. The fifth is the four-runs report's R1 and R2.

## 2. Where Platterpus stands on each, and what's left

| What made EAC trusted | Where Platterpus stands | What's left, and whose |
|---|---|---|
| 1. Checks its reads, says where it's unsure | Re-reads failed tracks by itself, which EAC doesn't. Error **counts** only in released builds | **Positions:** the fork's tip records them; release them, then Platterpus shows them in agreed wording (TASKS R44). Both |
| 1. The same, said truthfully | "Copy OK" and "confirmed across 3 secure re-reads" printed over 5 wrong tracks on 2026-10-21 | **Never print either over a track AccurateRip contradicts; say "wrong"** (four-runs report, R1 to R3). Platterpus. This puts us ahead of EAC |
| 1. Reads the hard tracks right | Equal on the one disc compared. `.26` read track 3 wrong 0 of 3 | **Settle `.26`'s speed against track 3 before stable** (four-runs report, C1). The fork first |
| 1. Keeps a right read | A right read was in hand and a wrong one shipped; a cancel threw a right read away | **C2 and C3** of the four-runs report. Platterpus |
| 2. Checked against everyone | AccurateRip v1 and v2, CTDB per track and across offsets, matches weighed | **Name where the bad samples are,** as EAC's CTDB plugin does (TASKS R43, waiting on the owner's word on `numpy` or a native extension). Platterpus |
| 3. A log anyone can check | An EAC-layout log plus Platterpus's own, an open SHA-256, never a forged EAC signature (KDD-36) | Keep our own log the goal. Score every run's tracks at its top: right, wrong but reported, wrong and reported as fine (EAC parity doc, item 7). Platterpus |
| 4. Settings known and shared | Chosen for the user: the offset from AccurateRip's list, re-confirmed each rip; cache defeat measured | **Breadth:** a second drive, machine and distro (the 0.8.1 gate). Waits on the owner's hardware |
| 5. Copies the disc exactly | Offsets and pregaps match EAC; `.26` reads the disc's ISRCs (proven on the drive). Track 9's pregap one frame off on `.26`; no HTOA, no image + cue | Track 9's pregap (the fork). HTOA and image + cue stay low, as Part E7 has them |
| 6. Free, proven over years | Free and open source | Time, and rips on more drives |

**Contributing back is the one gap with no route yet.** Part E says AccurateRip submission is
"impossible from Linux". No source found says so either way (the EAC parity doc, section 3).
CTDB submission isn't built. Neither stops a rip being right, so it comes after the table above.

## 3. Windows, later

The owner put a Windows build down as a long-term goal. Nothing in this file asks for work on it
now. When either session next touches the ripping path or the app's platform code, it notes in
its lap what would stand in a Windows build's way. Nothing more until the owner says.

## 4. What each session is asked for

Each session answers in its next lap, naming one writer for each item it takes, from section 2:

- **The fork:** the `.26` speed question against track 3, error positions in a release, and
  track 9's pregap.
- **Platterpus:** R1 to R3 first, then C2 and C3, then the per-run scoring and sample
  location.

**Waits on the owner:**
- the EAC rips of the damaged disc and disc 3;
- a second drive;
- the word on `numpy` for R43.
