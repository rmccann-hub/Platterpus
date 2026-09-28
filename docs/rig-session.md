# Rig session — the current sheet

```
Platterpus  v0.6.63        the release for round 29's run. It installs e0471f4 by
                           default, and accepts 51cc789 as the build under review.
            v0.6.62        the release before it: it accepts e0471f4 as the build under
                           review, not .18, so section A stops a run on it.
cyanrip     e0471f4        0.9.4-rc2+platterpus.17  (platterpus-fork-ge0471f4)  <- PRODUCTION PIN
                           approved by round 28, for Platterpus 0.6.61, on the Full run
            51cc789        0.9.4-rc2+platterpus.18  (platterpus-fork-g51cc789)  <- UNDER REVIEW
                           released, release_seq 28, both channels; round 29's subject
drive       Pioneer BDR-209D 1.51, read offset +667
rounds 1-28 ALL CLOSED on both gates, bilateral GO.
round 29    OPEN on 51cc789. Close condition 1 is this sheet's run.
```

> **Header last moved 2026-09-28**, when round 29 opened on `.18` (the fork's lap 1,
> sha256 `2e275d2f…`): the next run is round 29's Full run on `.18` from 0.6.63.
> Before that, the same day, when round 28 closed on our gate and `FORK_PIN`
> rolled to `e0471f4`, on the Full run of 0.6.61 (320 of 320 steps), which the operator
> chose to close the round on. Before that, the same day, to 0.6.62: the operator had
> moved round 28's Full run from 0.6.61 to it, an override of R1 our lap 6 records
> (S36), which fell away when the operator chose the 0.6.61 run. Before that,
> 2026-09-26, when round 28 opened on `.17` (the fork's lap 1, sha256 `060fd251…`),
> and on 2026-09-27 when 0.6.61 was released to carry it. Before that, 2026-09-26,
> when round 27 closed on our gate and `FORK_PIN` rolled to
> `221a1df`, on the quick run that stood in for the Full one by the maintainer's override.
> Before that, 2026-09-25, to 0.6.60. The first Full attempt on 0.6.59 stopped at
> section A with `.15` installed: 0.6.59's update check and setup wizard could each replace
> the build under review with the approved one. 0.6.60 keeps it.
> Before that, 2026-09-24, to round 27 and 0.6.59. The fork opened round 27
> on `.16` the same evening, and a quick run on 0.6.58 with `.16` installed stopped at
> section A, as their lap 1 said it would. Before that, the same day, to 0.6.58, which
> splits the acceptance run into
> Quick / Standard / Full and takes the read offset from the drive in the machine.
> Before that, the same day, to 0.6.57, which re-reads one-frame AccurateRip matches
> by default; before that, to 0.6.56, the release that ships
> `df91ae7`; before that, the same evening, when round 26 closed on our gate and `FORK_PIN` rolled to
> `df91ae7`. The move before that was the same day, to 0.6.55: the first attempt on 0.6.54 stopped at
> section A, which refused `.15` on a defect of ours (`docs/testing.md` §5.bq). Before
> that, 2026-09-23, when round 26 opened on `.15`; the move before that was the same day, when round 24 closed on our gate and `FORK_PIN` rolled to
> `3e01bb3`. Before that it was 2026-09-22, by the pre-round-24 document audit, and
> before that it named `v0.6.30` + cyanrip `d9c058c` and *"round 15 is not open"* —
> twenty-three patch versions and nine rounds behind — and its body was round 7's
> `b12` acceptance criteria, with steps for a menu layout that no longer exists. That
> sheet is [`archive/rig-session-d9c058c.md`](archive/rig-session-d9c058c.md). A sheet
> that names the wrong pair is worse than no sheet, because a run against it produces
> evidence about a different subject.

**This is the one rig sheet.** It is rewritten in place when the pairing moves, never
joined by a sibling — the header above names the pair it is written for. Superseded
originals are in [`docs/archive/`](archive/) with their audit trail intact.

---

## What the next run is for

**Round 29's close condition 1** (the fork's round 29 lap 1 S6): our **Full** acceptance
run on the rig, with `.18` installed through the app, from **0.6.63**, whose
`PIN_UNDER_REVIEW` is `51cc789`, and the bundle committed to both repositories. Then
each side reads it (S7): they read every cyanrip log in the bundle and we read our
reports. Round 29 closes when the tag change is read (S8, done on our side: our
operator accepted the key set as landed) and both closing laps name their releases
(S9): ours rolls `FORK_PIN` to `51cc789`, and theirs is `+platterpus.19`.

**A run on 0.6.62 or earlier is a setup check, not this round's evidence**: 0.6.62
accepts `e0471f4` as the build under review, not `.18`, so section A stops it in its
first seconds with `.18` installed.

**The run is also a candidate full-green pass, which the project has never had.** The
field-evidence ledger (`docs/testing.md` §5B) has no `full-green` row; the 2026-09-28
run is graded `partial`, because our own records carried two archival defects, both
fixed for 0.6.63. `0.7.100` is gated on a run with **zero failures in the ARCHIVAL
sections**; `0.9.1` needs two such runs on at least two machines and two distros. Its
ripper will be stamped `unapproved` in every report, correctly, while round 29 is open.
**Only a Full run counts as evidence**; Quick and Standard are for checking the setup.

**What `.18` carries** over `.17`, five commits of the fork's in `src/` and one merge of
upstream's: `Encoder errors:` counts only tracks whose read completed, and a new line,
`Partial files:`, names a partial file (`f150c0c`); `Stopping, ripping incomplete!`
prints on every signal stop of a read (`9d52271`); the AccurateRip parse is tested on
a recorded response (`5b7493c`, `a646d54`); the disc-level `AccurateRip:` line can read
`mismatch` or `not found` (`64642db`); and upstream's `f8ebf48`, a MusicBrainz retry,
which Platterpus never reaches because it runs cyanrip with `-N`.

**What 0.6.63 changes for the person at the rig.** Nothing to do differently. A track
whose re-read AccurateRip verifies keeps that re-read, a partial rip is no longer looked
up in CTDB, and the EAC-compatible log's first line begins with "Platterpus".

**What 0.6.62 changes for the person at the rig.** A disc that the drive briefly
reports as unavailable is read again when it comes back, and a first read that fails
on a cold container is retried, so you should not need to open and close the drive or
restart the app. The dependency check says it is running and stops within two
minutes, and the script's `open dependencies` step no longer freezes the window. The
acceptance test is under **Tools → Advanced**.

**`.17`, now the production pin**, compares only frame-450 checksums on a frame-450
AccurateRip lookup, says a one-frame match covers one frame only, and writes its banner
as soon as the log opens (`10f36fe`, `ec0fe47`, `ee0221c`). The 2026-09-28 Full run
tested it on this drive.

**Why section F should hold this time.** In round 26, section F's whole-disc rip was
killed 95 seconds in when the `ripping` container died underneath it. The container
belonged to an earlier Platterpus window, which had started it and then been closed
and replaced after an update (KDE keeps a closed app's unit alive while the container
is inside it). From 0.6.59, a container Platterpus starts gets its own scope and
survives any window closing. `platterpus --doctor` reports which app or terminal owns
a container that is already running.

## Three steps

1. **Put the reference disc in the drive** (any ordinary audio CD works; the script
   needs no album name, track count or path) and open Platterpus from the applications
   menu.
2. **Update Platterpus to 0.6.63 first.** Then check **Tools → Setup & Updates…**: the
   cyanrip line should read `platterpus-fork-g51cc789` (`0.9.4-rc2+platterpus.18`). If it
   reads anything else, **Check for cyanrip updates** offers `.18` as *"the build the
   acceptance test needs"*; choose **Install it anyway**. Then **Tools → Advanced → Run acceptance test…**,
   choose **Full**, and leave it. It holds sleep off, runs every section (4–6 hours), stops in its first
   seconds if the ripper is not the build under review, and puts your own settings back
   when it ends. **During the run, don't close any other Platterpus window or any
   terminal you have used distrobox in.**
3. **Upload the one `platterpusbundle….tar.gz`** from the run's session folder under
   `~/platterpus-rig/` here, and point the cyanrip session at it too. They file it
   under `docs/rig-<date>-<pin>/` in their repository, as they did for rounds 26 and 27.

**Optional, and the fork asked for it:** a disc with a known bad area would retire the
rest of *"damaged media"*, and reach `.15`'s retry fix on a drive for the first time.
The BDR-209D reports C2 unsupported, so C2 stays `UNREACHABLE` whatever the disc.
Cyanrip's `-f` is also still untested on hardware, and **the acceptance run does not
exercise it**; the reference disc could, since it is in AccurateRip and `+667` is
known to be correct for it. That would be a separate step, not part of this run.

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

*Last updated for Platterpus v0.6.63.*
