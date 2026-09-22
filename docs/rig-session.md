# Rig session — the current sheet

```
Platterpus  v0.6.53        GitHub pre-release flag (every v0.* tag carries it);
                           offered on the STABLE update channel
cyanrip     2cce60d        0.9.4-rc2+platterpus.13  (platterpus-fork-g2cce60d)  <- PRODUCTION PIN
                           pin moved in round 22; approved by round 23, for Platterpus 0.6.52
drive       Pioneer BDR-209D 1.51, read offset +667
rounds 1-23 ALL CLOSED, bilateral GO. Round 24 is not open and is the fork's to open.
```

> **Header last moved 2026-09-22**, by the pre-round-24 document audit. Before that it
> named `v0.6.30` + cyanrip `d9c058c` and *"round 15 is not open"* — twenty-three patch
> versions and nine rounds behind — and its body was round 7's `b12` acceptance
> criteria, with steps for a menu layout that no longer exists. That sheet is
> [`archive/rig-session-d9c058c.md`](archive/rig-session-d9c058c.md). A sheet that names
> the wrong pair is worse than no sheet, because a run against it produces evidence
> about a different subject.

**This is the one rig sheet.** It is rewritten in place when the pairing moves, never
joined by a sibling — the header above names the pair it is written for. Superseded
originals are in [`docs/archive/`](archive/) with their audit trail intact.

---

## What the next run is for

**A full-green pass, which the project has never had.** The field-evidence ledger
(`docs/testing.md` §5B) carries seven rows, every one `partial`. `0.7.100` is gated on
a run with **zero failures in the ARCHIVAL sections**; `0.9.1` needs two such runs on
at least two machines and two distros.

**What makes this run different from 2026-09-22's**: v0.6.53 is the first build whose
script can *fail* over the thing that made that run `partial`. Sections F, H, J,
K1–K3 and N now carry `expect-verification`, which grades what the CTDB and
FLAC-integrity checks actually left behind — on 2026-09-22 three of eight rips had
those checks dropped unfinished and every step still passed. So a green result here
means more than the last one could, and a red one is the script doing its job.

**It is new evidence, not a repeat.** Round 23's approval names Platterpus **0.6.52**.
Two runs of one ripper under different app versions are not interchangeable
(`CLAUDE.md` Critical rule #12, obligation 3), so this run is a first on 0.6.53, not a
second on 0.6.52.

**Not for `+platterpus.14`.** When the fork ships `.14` (the per-track `read
successfully!` rename), pairing it with 0.6.53 is the first real test of our
both-wordings parser — but installing it needs a round to move the pin, and any
build no closed round approved is stamped `unapproved`. Do not install it for this run.

## Three steps

1. **Put any ordinary audio CD in the drive** — the Police disc is the reference, but
   the script needs no album name, track count or path — and open Platterpus from the
   applications menu. (It moved itself to `~/Applications/` when you accepted the
   first-run offer, so a `./platterpus-x86_64.AppImage` typed in `~/Downloads` is
   *No such file or directory*, correctly.)
2. **Tools → Setup & Updates… → Check for cyanrip updates.** No round is open, so take
   the offer only if it is a plain one-click install; the build it should report is
   `platterpus-fork-g2cce60d`. Then **Tools → Run acceptance test…** and leave it —
   it holds sleep off, runs every section (4–6 hours; 2026-09-22 took 4h14m), stops
   in its first seconds if the ripper is not the expected build, and restores
   `max_retries 5` and `ripper_channel stable` at the end.
3. **Upload the one `platterpusbundle….tar.gz` it leaves in `~/Downloads`** — here,
   and point the cyanrip session at it too; they file it under
   `docs/rig-<date>-2cce60d/` in their repository, as they did for 2026-09-22.

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

*Last updated for Platterpus v0.6.53.*
