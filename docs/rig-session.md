# Rig session — the current sheet

```
Platterpus  v0.6.58        GitHub pre-release flag (every v0.* tag carries it);
                           offered on the STABLE update channel. Installs df91ae7 by
                           default (since 0.6.56); acceptance run in Quick / Standard /
                           Full sizes, from a fixed baseline, at the drive's own offset.
cyanrip     df91ae7        0.9.4-rc2+platterpus.15  (platterpus-fork-gdf91ae7)  <- PRODUCTION PIN
                           approved by round 26, for Platterpus 0.6.55, on its real test;
                           installed by default from 0.6.56 (0.6.55 installs 3e01bb3)
drive       Pioneer BDR-209D 1.51, read offset +667
rounds 1-26 ALL CLOSED on our gate, bilateral GO. No round is reviewing a build;
            round 27 opens on the fork's .16.
```

> **Header last moved 2026-09-24, to 0.6.58**, which splits the acceptance run into
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

**Round 26's close condition, and it cannot be met any other way.** The fork's round
26 lap 1 names `+platterpus.15` (`df91ae7`) and closes on the real test: our full
acceptance run with `.15` installed **through this app**, from a release whose
`PIN_UNDER_REVIEW` is `df91ae7`, with the bundle committed to both repositories. Round
26 then closes on each side's reading of it, our 0.6.x release rolls `FORK_PIN` to
`df91ae7`, and theirs is `+platterpus.16`.

**It is also a candidate full-green pass, which the project has never had.** The
field-evidence ledger (`docs/testing.md` §5B) carries seven rows, every one
`partial`. `0.7.100` is gated on a run with **zero failures in the ARCHIVAL
sections**; `0.9.1` needs two such runs on at least two machines and two distros.
This run's ripper is stamped `unapproved` in every report, correctly — round 26 has
not closed — and that stamp is not an archival failure: it is the record saying
truthfully that the approval is still pending.

**Why `.15` and not `.14`.** Section B sets `max_retries 3` (`-r 3`), and the
fork measured that on `.14` a read of an unreadable sector at `-r 3` can hang; on
`.15` it returns at the paranoia level we run. Both were measured by fault injection
on a disc image, not on a drive, so this run is the first on hardware.

## Three steps

1. **Put any ordinary audio CD in the drive** — the Police disc is the reference, but
   the script needs no album name, track count or path — and open Platterpus from the applications menu. (It moved itself to
   `~/Applications/` when you accepted the first-run offer, so a
   `./platterpus-x86_64.AppImage` typed in `~/Downloads` is *No such file or
   directory*, correctly.)
2. **Update Platterpus to 0.6.55 first**, then **Tools → Setup & Updates… → Check for
   cyanrip updates.** It offers `0.9.4-rc2+platterpus.15` (`df91ae7`) with a ⚠ saying
   rips on it will read `unapproved`, and a line saying *"This is the build the
   acceptance test needs"*. Choose **Install it anyway**; the build it should then
   report is `platterpus-fork-gdf91ae7`. (0.6.54 cannot run this: its section A refuses
   `.15` and stops in its first seconds. 0.6.53 demands round 23's `2cce60d`.) Then **Tools → Run
   acceptance test…** and leave it — it holds sleep off, runs every section (4–6 hours;
   2026-09-22 took 4h14m), and stops in its first seconds if the ripper is not `.15`.
   When it ends, the app puts your own settings back itself (new in 0.6.55), and
   the bundle's `SETTINGS.json` records the settings the run used.
3. **Upload the one `platterpusbundle….tar.gz`** — on 0.6.55 it is in `~/Downloads`
   (the next release keeps it, the rips and the screenshots in the run's one session
   folder under `~/platterpus-rig/` instead) — here,
   and point the cyanrip session at it too; they file it under
   `docs/rig-<date>-df91ae7/` in their repository, as they did for 2026-09-22.

**Optional, and the fork asked for it:** a disc with a known bad area would retire the
rest of *"damaged media"* — how the drive fails, and how slowly. The BDR-209D reports
C2 unsupported, so C2 stays `UNREACHABLE` whatever the disc. Cyanrip's `-f` is also
still untested on hardware, and **the acceptance run does not exercise it**; the fork
notes the reference disc could, since it is in AccurateRip and `+667` is known to be
correct for it. That would be a separate step, not part of this run.

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

*Last updated for Platterpus v0.6.58.*
