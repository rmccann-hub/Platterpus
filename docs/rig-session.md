# Rig session — the current sheet

```
Platterpus  v0.6.61        the release for round 28's run. It installs 221a1df by
                           default, and accepts e0471f4 as the build under review.
            v0.6.60        the release before it: installs df91ae7 and cannot run
                           round 28's test (section A refuses e0471f4).
cyanrip     221a1df        0.9.4-rc2+platterpus.16  (platterpus-fork-g221a1df)  <- PRODUCTION PIN
                           approved by round 27, for Platterpus 0.6.60, on a quick run
            e0471f4        0.9.4-rc2+platterpus.17  (platterpus-fork-ge0471f4)  <- UNDER REVIEW
                           released, release_seq 27, both channels; round 28's subject
drive       Pioneer BDR-209D 1.51, read offset +667
rounds 1-27 ALL CLOSED on our gate, bilateral GO.
round 28    OPEN on e0471f4. Close condition 1 is this sheet's run.
```

> **Header last moved 2026-09-26**, when round 28 opened on `.17` (the fork's lap 1,
> sha256 `060fd251…`) and 0.6.61 was staged to carry it. Before that, the same day,
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

**Round 28's close condition 1** (their lap 1 S6): our **Full** acceptance run on the rig,
with `.17` installed through the app, from 0.6.61, whose `PIN_UNDER_REVIEW` is
`e0471f4`, and the bundle committed to both repositories. Then each side reads it (S7):
they read every cyanrip log in the bundle and we read our reports. Round 28 closes when
both closing laps name their releases (S8): ours rolls `FORK_PIN` to `e0471f4`, and
theirs is `+platterpus.18`.

**That run will also be a candidate full-green pass, which the project has never had.**
The field-evidence ledger (`docs/testing.md` §5B) has no `full-green` row. `0.7.100` is
gated on a run with **zero failures in the ARCHIVAL sections**; `0.9.1` needs two such
runs on at least two machines and two distros. Its ripper will be stamped `unapproved`
in every report, correctly, while round 28 is open. That stamp is not an archival
failure: it is the record saying truthfully that the approval is still pending. **Only a
Full run counts as evidence**; Quick and Standard are for checking the setup.

**A run on 0.6.60 is a setup check, not evidence**: 0.6.60 does not accept `.17` as the
build under review, so section A stops it in its first seconds.

**What `.17` carries** over `.16`, three commits in `src/`: an Accurip 450 lookup compares
only 450 checksums (`10f36fe`); a one-frame match says what it covers, *"one frame only;
whole-track checksums not found"*, instead of *"partially accurately ripped"* (`ec0fe47`);
and the banner is written as soon as the log opens, so the log of a rip that fails early
still names its build (`ee0221c`). **What `.16` carries**, now the production pin: every
file is tagged `media: CD` whatever `-H` says, and an interrupted track is left out of
the AccurateRip tally. The round 27 quick run declined the sections that reach both, so
this Full run is their first test on a drive too.

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
2. **Update Platterpus to 0.6.61 first.** Then check **Tools → Setup & Updates…**: the
   cyanrip line should read `platterpus-fork-ge0471f4` (`0.9.4-rc2+platterpus.17`). If it
   reads anything else, **Check for cyanrip updates** offers `.17` as *"the build the
   acceptance test needs"*; choose **Install it anyway**. Then **Tools → Run acceptance test…**, choose **Full**, and
   leave it. It holds sleep off, runs every section (4–6 hours), stops in its first
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

*Last updated for Platterpus v0.6.60.*
