# Rig session — the current sheet

```
Platterpus  v0.6.65        the release round 30's Full run is on, released 2026-09-30
                           02:57Z under the operator's §6b override (our round 30 lap 2):
                           it installs 51cc789 and accepts 174a134 as under review.
            v0.6.64        round 29's closing release, released 2026-09-30: it
                           installs 51cc789 by default.
cyanrip     174a134        0.9.4-rc2+platterpus.19  (platterpus-fork-g174a134)  <- UNDER REVIEW
                           published 2026-09-30 on round 29's authority; round 30's subject
            51cc789        0.9.4-rc2+platterpus.18  (platterpus-fork-g51cc789)  <- PRODUCTION PIN
                           approved by round 29, for Platterpus 0.6.63, on the Full run
drive       Pioneer BDR-209D 1.51, read offset +667
rounds 1-29 ALL CLOSED, bilateral GO (round 29 on 2026-09-29).
round 30    OPEN on 174a134, from the fork's lap 1 (2026-09-30); this run is its S10.
```

> **Header last moved 2026-09-30**, when round 30 opened on `.19` (the fork's lap 1,
> sha256 `6db0ed0d…`) and 0.6.65 was released for its Full run. The move before that
> was the same day, when 0.6.64 was released to carry `51cc789`. Earlier moves are in
> this file's git history.

**This is the one rig sheet.** It is rewritten in place when the pairing moves, never
joined by a sibling — the header above names the pair it is written for. Superseded
originals are in [`docs/archive/`](archive/) with their audit trail intact.

---

## What the next run is for

**Round 30's Full run — 0.6.65 with `.19` installed — started about 03:02Z on
2026-09-30 and is in progress.** It is the round's S10. Section A expects `174a134` as
the build under review, and every rip records its ripper as *being tested, not approved
yet*, which is correct for this run. One run tests both sides.

**What `.19` carries** over `.18`, five commits of the fork's in `src/`: the build-tag
change (`bf50705`), the finalised checksum (`9669d84`), the repeat-limit wording
(`fb31a2b`) and the `-Z`/`-r` refusal (`22f7aae`, `ad11743`) — the fork's round 29 lap 3
S18.

**It is a candidate full-green pass, which the project has never had.** The
field-evidence ledger (`docs/testing.md` §5B) has twelve rows and no `full-green` one.
Round 29's run is `partial` because three screenshot steps, in sections graded archival
in advance, found no window on screen. Our hypothesis is that the display blanked, so
0.6.65 holds the screen awake for the run as well as the machine. Its first notice in
the rip pane says whether it could: if the *Screen lock* line starts with ⚠, set the
screen to never turn off by hand. `0.7.100` is gated on a run with **zero failures in the
ARCHIVAL sections**; `0.9.1` needs two such runs on at least two machines and two
distros. **Only a Full run counts as evidence**; Quick and Standard are for checking the
setup.

**What changed for the person at the rig since 0.6.62:** nothing to do differently.
The acceptance test is under **Tools → Advanced**. A disc the drive briefly reports as
unavailable is read again when it comes back, and a first read on a cold container is
retried, so you should not need to open and close the drive or restart the app.

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
2. **Update Platterpus to 0.6.65 first.** Then check **Help → About Platterpus…**: the
   *Installed* line should name `platterpus-fork-g174a134` (`0.9.4-rc2+platterpus.19`).
   (**Tools → Setup & Updates…** always shows the *approved* build, `51cc789`; that is
   expected.) If it names anything else, **Tools → Setup & Updates… → Check for cyanrip
   updates** offers `.19` as the build handshake round 30 is testing, which *"the
   acceptance test needs"*; choose **Install it anyway**. Then **Tools → Advanced → Run acceptance test…**,
   choose **Full**, and leave it. It holds sleep and the screen off, runs every section (4–6 hours), stops in its first
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

*Last updated for Platterpus v0.6.65.*
