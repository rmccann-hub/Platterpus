SUPERSEDED-BY: EAC-PARITY-PLAN-OF-RECORD-2026-10-26.md (https://claude.ai/artifact/ACChXwKyAGM9wvCTVjqDDo). Do not send this file.
REPORT-FOR: Platterpus session and cyanrip fork session
FROM: the claude-code-skills session, for the owner to pass on once, to both sessions, with the
four bundles
WRITTEN: 2026-10-26 (times below in UTC). This replaces the version of the same name sent
earlier the same day.
EXPIRES: 2026-11-30
SUBJECT: four Full runs of 0.7.112 with `.26`: did the rips come out right, and did we say so
truthfully

# Did the rips come out right, and did we say so truthfully?

## The owner's word, verbatim

> "look, for this, both reops, they need to rip and be correrct, reporting on files is good, but
> ripping ir the goal. we need to report on that accuractly to confirm, that is what we do."

So this report leads with two questions, for every track the four runs wrote:
1. Is the audio right?
2. Did Platterpus tell the user the truth about it?

Everything else, the test script's own failures included, comes after.

## How "right" is decided

- **Right:** AccurateRip verified the track's whole checksum in that rip, or another rip of the
  same disc verified that same checksum.
- **Wrong:** the track's first-frame checksum (frame 450) matched AccurateRip while its whole
  checksum did not. The frame match proves we read the same pressing AccurateRip knows, at
  confidence 24 to 200. A whole-track mismatch then means our bytes differ from everyone
  else's rips of that pressing. That is a wrong rip, not just an unverified one.
- **Cross-check:** for The Police's track 5, AccurateRip's value is `C96464AB`, from the repos'
  own records.

The scripts that did the counting read only the bundles' `.platterpus.json` records and
EAC-layout logs; nothing was executed from the bundles.

## 1. Was the audio right?

All four runs ran Platterpus 0.7.112 (`9bf0cd3`), with `.25` only in the timing rips.

| Disc | Rips | Right | Wrong | Notes |
|---|---|---|---|---|
| *Roots Music* disc 4 (`rBin7…`) | every rip in run 4 | **all** | 0 | Every track, both builds |
| *Roots Music* disc 3 (`bkyFF…`) | run 3 | all but 1 | 1 | Track 16 is damaged. The main rip's read was wrong (`8B597546`); the secure re-rip's fifth read verified (`3EACDE74`) and shipped. **Final copy: 16 of 16 right** |
| The Police (`pNtIm…`) | run 1 | 37 | **5** | Track 3: `.26` wrong in both timing rips and in the secure re-rip, while `.25` was right twice. Track 5: wrong in the main rip and the secure re-rip, and its right value `C96464AB` was never read. **Final main rip: 13 of 14 right** |
| The damaged disc, *Roots Music* disc 1 (`zxtbw…`) | run 2 | 10 | **8** | Tracks 11 to 18 wrong. The run hit its 6-hour limit inside the re-reads. One of track 11's re-reads did verify, and the cancel threw it away |

**In total, 158 of 172 tracks written were right and 14 were wrong.** Every wrong track is on
the two hard discs, or on The Police's tracks 3 and 5, which have always been the hard ones on
this drive.

## 2. Did Platterpus tell the truth?

**Every claim of success was true.** Each album verdict reading "✓ Bit-perfect" had every track
verified. No wrong track was ever called verified.

**Where the wording was wrong:** for the 14 wrong tracks, Platterpus said less than the truth,
and in places the opposite.

| Where | What it said over a wrong track | What's true |
|---|---|---|
| The album verdict, every case | "only one frame matched, so the rest of each is unverified" | It is wrong: the pressing matched, and the audio didn't |
| The EAC-layout log, 5 of 14 wrong tracks | **"Copy OK"** | No read error was seen, yet the copy is wrong |
| The EAC-layout log, 3 of those 5 | "Test and Copy CRC identical — **confirmed across 3 secure re-reads**" | The re-reads agreed with each other on wrong bytes |
| The record's per-track `status`, 9 of 14 | "ripped successfully" | The rip finished, but its audio is wrong |

A user reading "Copy OK, confirmed across 3 secure re-reads" believes the track is right. That
is the one report failure that matters most here.

## 3. What to fix, in order

### First, so the report says the truth (Platterpus)

- **R1. Say "wrong" when the evidence says wrong.** When the first-frame checksum matches
  AccurateRip and the whole track doesn't, the verdict, the results pane and the EAC-layout log
  each say the copy differs from AccurateRip's for this pressing: it is not a good copy, and it
  should be re-ripped or replaced.
  - Keep "unverified" for a track AccurateRip can't speak to at all.
  - **Proof without the drive:** the five Police logs and the eight damaged-disc logs here, as
    fixtures.
- **R2. Never print "Copy OK" or "confirmed" over a track AccurateRip contradicts.** EAC's "Copy
  OK" means only that no read error was seen, and users don't read it that way. Where the whole
  track mismatches, print what EAC prints for a suspicious copy, and drop "confirmed across N
  re-reads".
  - **Proof:** the same fixtures, asserting neither phrase appears.
- **R3. The per-track status says the outcome, not that the process finished.** For example,
  "ripped, differs from AccurateRip".

### Second, so more rips come out right

- **C1. Track 3 at `.26`'s speed (the fork first, then both).**
  - **What happened:** `.25` read The Police's track 3 right in 2 of 2 rips (`59D352DD`,
    confidence 200). `.26` read it wrong in all 3 of its single reads, each time differently,
    and in the secure re-rip.
  - **Likely cause:** `.26` reads 2.9 times faster. Upstream `7dbe56a` removed a check that held
    the drive near 1×, and the track is marginal at full speed. That's a correlation, on one
    drive.
  - **For the fork:** say whether `7dbe56a` changes the read speed, and whether `-S` can hold it
    down.
  - **For both:** when a track fails AccurateRip, re-read it at a lower speed before anything
    else.
  - Keep `.26` off the stable channel until this is settled. Proof needs the drive, a few rips
    at a time the owner chooses.
- **C2. A right read was in hand, and a wrong one shipped (Platterpus).** In the secure re-rip,
  track 3's first read was `59D352DD`, the right value, and cyanrip's `-Z` converged on
  `3D8FCF0C` over 3 reads, which shipped.
  - **Fix:** whenever any read of a track matches AccurateRip, that read ships, whichever path
    read it. Today only the securing pass's chase does this.
  - **Proof:** this run's secure re-rip logs.
- **C3. A cancel must keep what's right (Platterpus).** On the damaged disc, a re-read of track
  11 verified (confidence 29), and the cancel discarded it.
  - **Fix:** keep each finished track when a pass stops.
  - **Proof:** this bundle's logs, with a fake ripper and an injected clock.
- **C4. A damaged disc needs a time bound (Platterpus).** Track 18 took 5 h 18 min; the worst
  case for this disc is roughly 20 to 24 hours.
  - **Fix:** give each track a time budget from its first read, applied to the chase too. Record
    a track whose every read has skips as "unreadable on this drive", with its positions,
    rather than re-reading it for hours.
- **C5. Track 5's right value was never read** in these runs, by either build. It has been the
  hard track all along. Say in your next laps what would read it: a lower speed, more reads, or
  another drive.

### What's proven right on the drive, and keeps the rips correct

- **The disc's own ISRCs (item 8).** `.26` read all 14 on The Police, matching EAC's cue
  (track 1 `GBAAM7800003`), and 13 of 16 on disc 4. `.25` read none in the same runs.
- **Re-reading until a read verifies (item 2), by the chase.** On disc 3's track 16, 14 reads
  gave 14 different checksums, and the one that verified shipped.
- **CTDB per track (item 7)** agrees with AccurateRip on every disc.
- **Error positions (item 6) and paranoia counters** match the ripper on the damaged discs.

## 4. The test harness, which doesn't decide correctness

These failed steps, not rips, and none touched the audio. Fix them so the next run's failures
are about rips:

- **The cue's ISRC check** compares with the MusicBrainz codes sent, not the disc's codes
  written. Five steps across two runs fail the right answer.
- **One "tray open" blip** from the drive cleared the app's disc view and cost 57 of run 1's 60
  failures. Confirm a removal before acting on it. It can also happen to a user.
- **The cover-art grade races** the booklet download.
- **The derived-file check runs before the files are written.**
- **The audit expects clean** on a damaged disc, and counts a replaced read's errors.
- **The chase's diagnostics records are missing** from the bundle.
- **`Recordable:` reads "unknown"** on every disc on this drive (the fork).
- **The Police's track 9 pregap** reads 95 or "unknown" on `.26`, never 94 as on `.25` and in
  EAC (the fork).

The detail for each is in `run1-findings.md`, `run2-findings.md` and `run34-findings.md`.

## 5. The timed comparison, for the record

Tracks 1 to 3, two rips each:
- `.26` is 2.9× faster on The Police, 2.8× on disc 3 and 5.1× on disc 4.
- Each pair agrees within 1%.

Speed is settled. Whether it costs accuracy is C1.
