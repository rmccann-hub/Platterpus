# Rig session — the current sheet

```
Platterpus  v0.6.66b1      round 30's closing-run BETA, a pre-release: offered on the
                           Beta update channel only, never on Stable. It installs
                           51cc789 by default and accepts 5704062 as under review.
            v0.6.65        the release of round 30's first Full run (2026-10-05).
cyanrip     5704062        0.9.4-rc2+platterpus.20  (platterpus-fork-g5704062)  <- UNDER REVIEW
                           the fork's BETA channel, published 2026-10-06 inside round 30
            174a134        0.9.4-rc2+platterpus.19  (platterpus-fork-g174a134)
                           the fork's STABLE channel; round 30's pin; tested 2026-10-05
            51cc789        0.9.4-rc2+platterpus.18  (platterpus-fork-g51cc789)  <- PRODUCTION PIN
                           approved by round 29, for Platterpus 0.6.63, on the Full run
drive       Pioneer BDR-209D 1.51, read offset +667
rounds 1-29 ALL CLOSED, bilateral GO (round 29 on 2026-09-29).
round 30    OPEN. It closes on THIS run: betas of both applications, and a Full
            acceptance run of both on that pair (the operator's conditions, 2026-10-05).
```

> **Header last moved 2026-10-06**, for round 30's closing run: the fork published
> `+platterpus.20` on its beta channel at `5704062`, and Platterpus 0.6.66b1 is the beta
> that names it as the build under review. The move before that was 2026-09-30, when
> round 30 opened on `.19` and 0.6.65 was released for its first Full run. Earlier moves
> are in this file's git history.

**This is the one rig sheet.** It is rewritten in place when the pairing moves, never
joined by a sibling — the header above names the pair it is written for. Superseded
originals are in [`docs/archive/`](archive/) with their audit trail intact.

---

## What the next run is for

**Round 30's closing run: 0.6.66b1 with `.20` installed.** The round closes when both
betas are released, this Full run on the pair is filed and read in both trees, and both
closing laps declare `GO`. Section A expects `5704062` as the build under review, and
every rip records its ripper as *being tested, not approved yet*, which is correct: `.20`
itself logs `NOT a released build`, since round 30 is open while it runs.

**What this run exercises for the first time on a drive:**
- **Platterpus:** the secure re-read after a pass the drive could not read cleanly (it
  used to run only after exit 0); cyanrip's own `-j` record of how a rip ended, read
  into the report beside ours (`ripper_record`); the new section **E2** (turn the offset
  override off; on this drive it is N/A, because AccurateRip lists the BDR-209D); the
  hardware-only checks folded into the run (the cold-container start, how many signals a
  cancel sent); and the run's overall estimate, stated when it starts and again after
  section E.
- **cyanrip `.20`:** nineteen `src/` commits over `.19` (the fork's release plan, §2):
  paranoia skips read `with errors` and counted in `Ripping errors:`, the `-Z` spool that
  encodes only the kept read, the cache probe scored by cd-paranoia's 6 ms, and `-f`
  exiting 1 when it finds no offset. **`-f` has never run on a drive, and this run is
  its first:** section O runs `cyanrip -N -f` and grades the offset it finds against
  the `+667` section B sets.

**It is also a candidate full-green pass, which the project has never had.** The
field-evidence ledger (`docs/testing.md` §5B) has no `full-green` row. `0.7.100` is
gated on a run with **zero failures in the ARCHIVAL sections**. **Only a Full run counts
as evidence**; Quick and Standard are for checking the setup.

## Three steps

1. **Put the reference disc in the drive** and open Platterpus. Then **Tools → Setup &
   Updates…**: under **Platterpus**, tick **Offer beta (pre-release) updates**, press
   **Check for updates**, and take **0.6.66b1** (it restarts). A beta is never offered
   with that box off, which is the point of it.
2. **Install `.20`:** **Tools → Setup & Updates… → Choose a build…** and pick the one
   labelled as the build handshake round 30 is testing, `5704062`
   (`0.9.4-rc2+platterpus.20`). (Ticking **Offer beta (pre-release) cyanrip builds** and
   pressing **Check for cyanrip updates** reaches the same build; with that box off,
   `.19` reads as up to date.) **Help → About
   Platterpus…** should then name `platterpus-fork-g5704062` on its *Installed* line.
   Then **Tools → Advanced → Run acceptance test…**, choose **Full**, and leave it. It
   states its estimate when it starts, holds sleep and the screen off, runs every
   section, stops in its first seconds if the ripper is not the build under review
   (saying what to install), and puts your settings back when it ends. **During the run,
   don't close any other Platterpus window or any terminal you have used distrobox in.**
3. **Upload the one `platterpusbundle….tar.gz`** from the run's session folder under
   `~/platterpus-rig/` here, and point the cyanrip session at it too. They file it under
   `docs/rig-<date>-<pin>/` in their repository.

**Afterwards, both beta tick-boxes can go back off.**

**Optional, and the fork asked for it:** a disc with a known bad area would exercise
`.20`'s skip counting and the new secure re-read on real damage. The BDR-209D reports C2
unsupported, so C2 stays `UNREACHABLE` whatever the disc. A disc MusicBrainz does not
know runs the second script, **Tools → Advanced → Run acceptance test with an unknown
disc…**; it is separate from this run.

## Before you start

- **Do not enable Overread (`-O`) on this drive.** It has run on the BDR-209D and hung
  the drive for about 23 minutes (`docs/dependency-contracts.md`). The acceptance
  script never sets it.
- **`-Z` is on, in dynamic mode.** A default rip reads the whole disc once at speed and
  re-reads with `-Z 2` only the tracks that miss AccurateRip; sections F and N pin the
  rip goal so the run covers both the default path and the whole-disc secure re-read.
  The `[plan]` block at the top of each rip's live log names every flag it is about to
  use.
- **Never send audio.** The bundle carries logs, cue sheets, reports and CRCs only
  (Critical rule #8).

---

*Last updated for Platterpus v0.6.66b1.*
