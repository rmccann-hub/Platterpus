# Rig session — the current sheet

```
Platterpus  v0.6.66        installs 174a134 by default and accepts ca3f3ea as round
                           31's build under review: the release round 31's run is on.
            v0.6.66b1      round 30's closing-run BETA (installs 51cc789, accepts
                           5704062). Not the build for round 31.
cyanrip     ca3f3ea        0.9.4-rc2+platterpus.21  (platterpus-fork-gca3f3ea)  <- UNDER REVIEW
                           the fork's STABLE and BETA channels, published 2026-10-07 after
                           round 30 closed; src/ byte-identical to 5704062 (.20)
            174a134        0.9.4-rc2+platterpus.19  (platterpus-fork-g174a134)  <- PRODUCTION PIN
                           round 30's declared pin, approved by round 30 for 0.6.66b1
drive       Pioneer BDR-209D 1.51, read offset +667
rounds 1-30 ALL CLOSED, bilateral GO (round 30 on 2026-10-07).
round 31    NOT OPEN yet. The fork writes its lap 1 on .21; that lap sets what closes it.
```

> **Header last moved 2026-10-07**, when round 30 closed on `174a134`, the fork
> published `+platterpus.21` at `ca3f3ea` to both channels, and Platterpus 0.6.66 was
> released to accept it. The move before that was
> 2026-10-06, for round 30's closing run (0.6.66b1 with `.20` at `5704062`). Earlier
> moves are in this file's git history.

**This is the one rig sheet.** It is rewritten in place when the pairing moves, never
joined by a sibling — the header above names the pair it is written for. Superseded
originals are in [`docs/archive/`](archive/) with their audit trail intact.

---

## What the next run is for

**Round 31's run, if its lap 1 asks for one: 0.6.66 with `.21` installed.** Round 31's
lap 1 is the fork's, and it says what closes the round; the steps below are what such a
run takes.

**What such a run would exercise.** `.21`'s program is `.20`'s (`git diff 5704062 ca3f3ea
-- src/` is empty), and round 30's closing run of 2026-10-06 exercised `.20` on this drive
(`docs/handshake/artifactsround30/`). What is new is what `.21` says about itself. Built
as the fork's manifest says (with `-Ddeclare_released=true`, which our in-app update takes
from that manifest), its logs read `Handshake: round 30 lap 17 closed, verdict GO --
released build`, where `.20`'s read an open round and `NOT a released build`, so a rip
records its ripper without the open-round warning. Section A expects `ca3f3ea`.

**Only a Full run counts as evidence**; Quick and Standard are for checking the setup.
`0.7.100` is gated on a Full run with **zero failures in the ARCHIVAL sections**
(`docs/testing.md` §5B), and the field-evidence ledger has no `full-green` row yet.

## Three steps

1. **Put the reference disc in the drive** and open Platterpus. **Tools → Setup &
   Updates… → Check for updates** and take **0.6.66** (it restarts).
2. **Install `.21`:** **Tools → Setup & Updates… → Choose a build…** and pick the one
   labelled as the build handshake round 31 is testing, `ca3f3ea`
   (`0.9.4-rc2+platterpus.21`). **Help → About Platterpus…** should then name
   `platterpus-fork-gca3f3ea` on its *Installed* line. Then **Tools → Advanced → Run
   acceptance test…**, choose **Full**, and leave it. It states its estimate when it
   starts, holds sleep and the screen off, stops in its first seconds if the ripper is
   not the build under review (saying what to install), and puts your settings back
   when it ends. **During the run, don't close any other Platterpus window or any
   terminal you have used distrobox in.**
3. **Upload the one `platterpusbundle….tar.gz`** from the run's session folder under
   `~/platterpus-rig/` here, and point the cyanrip session at it too.

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

*Last updated for Platterpus v0.6.66.*
