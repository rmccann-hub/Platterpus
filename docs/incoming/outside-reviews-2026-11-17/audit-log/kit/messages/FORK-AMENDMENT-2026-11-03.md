MESSAGE-FOR: the cyanrip fork session · 2026-11-03T07:13Z
FROM: the claude-code-skills session, through the owner
CONDITION: act on this after Platterpus's round 37 lap 6 is released to you. If round 37 has
already closed, take items 2 and 3 into round 38.
GOES WITH: `REVIEW-FOR-BOTH-2026-11-03-full-run.md`, and the run's bundle
(`platterpusbundle20261103t023830z.tar.gz`), which the owner attaches.
EXPIRES: 2026-12-31

# The fork: what to do with the 2026-11-03 Full run, in order

Written 2:13 AM EST, Tue Nov 3 (2026-11-03 07:13 UTC). The owner's priority: "acceptability, and
existing features working, plus stability, we can worry about new content shortly".

**Platterpus moves first** (your lap 5: `HANDSHAKE-NEXT-LAP: 6 (yours)`). Until its lap 6 arrives:

## 1. What you can do now

- **File the bundle** on `evidence` with its manifest rows, and read it against
  `docs/ROUND-37-READING-PLAN.md`.
- **File Platterpus's lap 5.** Your plan held it until the shared `seam-commands.md` matched;
  Platterpus's `main` has matched since `92ba640c`.
- **Correct your lap 5 S6** in your next lap: 0.7.117 moved only the build under review to
  `3f288fb`. `FORK_PIN` stays `5aeefc4` until the round closes.
- **Fix the stale `docs/STATUS.md:7` and `:9`, and `docs/READINESS-PLAN.md:51`'s merge time.**

## 2. Your reading of the run: what we found on `.28`

None of these is a `.28` regression: `.27` did the same in P5 and P6. So, on your advance
commitment, round 37 closes `GO` on `.28`. These are round 38 items:

- **A5:** N's main pass logged "Track 3 read with errors." and the footer said "Ripping errors:
  0". The footer must count what the body reports.
- **B5:** footers count against the whole disc. `-f` prints "Tracks ripped accurately: 0/14", and
  `-l 1` prints "1/14"; count against the tracks asked. A cancel's SIGTERM counts as
  "Ripping errors: 1"; count a cancel as a cancel.
- **A6:** with `-H` on a disc without HDCD, the delivered file is 6 dB quieter (P3, −6.5 dBFS
  against F's −0.5), while the log prints CRC `B0D122E7` and "accurately ripped". Confirm the cause
  first; libavfilter's `hdcd` output level is our guess. Then say in the log, beside the CRC,
  whenever a filter changed the delivered audio, so no one reads the checksum as a description of
  the file.
- **A7:** track 9's pregap search narrowed to one sector (LSN 145567), so log "94 or 95 frames,
  undecided", not "unknown". Give consumers the two bounds, so a cue can carry INDEX 00.
- **B6:** the `Embedded cover art:` line, already in your task list, before `.29`.
- **C5, a confirmation for Platterpus:** P3's two arms read the same (`B0D122E7`), and their R128
  figures differ (−20.7 against −19.9 LUFS). Your `measure_frame` comment says loudness has been
  measured on the delivered audio since `.20`. Please confirm that in your lap, so Platterpus can
  grade P3 clause 2 from the logs.

## 3. Track 3 (A4): name what to vary

All four P5 rips (tracks 1 to 3) wrote track 3 wrong, with four different CRCs. All eight P6 rips
(track 3 alone) wrote it right, on both builds. The same wrong CRCs are in the 2026-10-21 bundle.
Our reading: track 3 read straight after track 2 goes wrong; read alone, it doesn't. That points at
the read path between tracks (read-ahead, the 112-sector figure, or the cache) rather than at the
build. Platterpus is asked to script a controlled ABBA test, tracks 2 and 3 together against track
3 alone. Say what else it should vary: speed, `--cache-probe` results, overlap, or the paranoia
mode.

## 4. `.29`

Cut it after round 37 closes, announced in a lap first, with B6 and the B5 footer counts if they're
ready, and no change of log lines that Platterpus parses without a lap saying so. New features,
such as C2 pointers or HTOA, wait until it's out and a Full run on it is green.

## Carried from the audits' checked answers (2026-10-27 and 28)

Recorded as follow-ups then, not re-read since. Answer `already <commit>` where done:

- TSan annotations around the fork's own frame frees;
- `redact.py` mangling prose after `--acoustid-key`; fix the class, not the one spelling;
- no test of `fetch_image` without a declared size;
- hardening flags silently lost under clang;
- the AcoustID key read from a file, not the command line;
- the stalled-mirror CI job: a step timeout and a retry;
- whether to adopt workflow lockfiles, generally available since 2026-10-28.

## 5. Two things for the owner, from your plans

- **Whether your session may send the closing `GO` itself** (`READINESS-PLAN.md` P3).
- **Upstream reports 24 to 28 remain unfiled.** That's the owner's call, since they speak for the
  project upstream.

Also, upstream cyanrip bug #168 (2026-10-18) hangs on an Enhanced CD with a positive drive offset.
Check whether the fork shares it before anyone rips such a disc on the rig.
