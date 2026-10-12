# Round 31 — the Full run, 2026-10-07 03:39 UTC, `ca3f3ea` (`+platterpus.21`) on Platterpus 0.6.66

**The build.** Every rip log here opens
`cyanrip 0.9.4-rc2+platterpus.21 (platterpus-fork-gca3f3ea)` and logs
`Handshake: round 30 lap 17 closed, verdict GO -- released build`. That is the build
round 31 reviews, installed through our 0.6.66 (`a0330d0`). 0.6.66 pins `174a134` and
accepts `ca3f3ea` as the build under review.

**The bundle.** `platterpusbundle20261007t033944z.tar.gz`: sha256
`a7e51546a8cd6dc14475a07de966a992305ad547410946bac284875abcb932fd`, 7,298,290 bytes,
handed over by the operator. Its 76 text members are filed here byte for byte, each
with a `round31full` prefix. The tarball itself is not committed.

Not filed:
- the 26 screenshots;
- `session/transcript.txt`, which is byte-identical to `round31fulltranscript.txt`;
- the app-log rotations `.4` and `.5`, which end before the run.

There is no audio.

**The run.** It started at 03:39:44 UTC and ended at 08:59:53 UTC, when the app
restored the operator's settings (`round31fullplatterpusapplog.txt:9540`). The script
report says `run_size: full` and `counts_as_evidence: true`.

## What it shows

- **425 pass, 0 fail, 0 error, 1 unreachable, 5 info.** The one unreachable step is
  E2. It checks that the app refuses a drive missing from the AccurateRip list, and
  the BDR-209D is on that list.
- **Graded `full-green`, the project's first** (`docs/testing.md` §5B). The maintainer
  ruled on 2026-10-07 that E2's N/A does not block the grade, with E2 recorded as not
  covered.
- **The derived formats were really written.** K1, K2 and K3 each found two `.mp3`,
  `.wv` or `.wav` files beside two FLAC masters. That is the check whose absence kept
  the 2026-09-15 row from counting.
- **Every rip's cyanrip log verified**, the cancelled rip's included.
- **The app log holds no error or traceback** from launch to the end of the run.
- **Every screenshot caught its window on screen.**
- **The disc behaved as in every earlier run.**
  - Track 3 does not read the same way twice.
  - The whole-disc rip matched only one frame of AccurateRip on two tracks.
  - CTDB finds no match at the standard alignment.

  The verdicts say so, and the script graded their wording.
- **One defect, ours, wording only.** Every report on `.21` said it was "the pin an
  OPEN handshake round proposes", but round 31 had no lap yet. Fixed after the run
  (`d14c315e`): the sentence now names the round.

## The 2026-10-12 Full run, 04:09 UTC, `ca3f3ea` (`.21`) on Platterpus 0.7.103

**Why it is filed here.** It runs the pair round 31 approved, `.21`, through the release
that first installs `.21` by default. It is not round 32's test pair (`.22` with 0.7.103),
so it does not belong to round 32.

**The bundle.** `platterpusbundle20261012t040947z.tar.gz`: sha256
`5d9e90382f76f8459975706fa5b6509964781986601e8764d02e7c227e69ae9a`, 7,309,055 bytes,
handed over by the operator. Its 74 text members are filed here byte for byte, each with
a `v07103full` prefix and the same names as the 2026-10-07 run's. The tarball is not
committed.

Not filed:
- the screenshots;
- `session/transcript.txt`, which is byte-identical to `v07103fulltranscript.txt`;
- app-log rotations `.3` to `.5`, which end before the run.

There is no audio. The app log's times are local, UTC−4 on this rig (the 2026-10-07 run's
end reads 04:59:53 there and 08:59:53 UTC in its transcript).

**The run.** 04:09:47 to 09:28:05 UTC (`v07103fullplatterpusapplog2.txt:9828`,
`v07103fullplatterpusapplog.txt:18788`), the app at `2f7855b` (0.7.103) and every rip on
`cyanrip 0.9.4-rc2+platterpus.21 (platterpus-fork-gca3f3ea)`, which rig-check reports as
the build round 31 approved.

### What it shows

- **424 pass, 0 fail, 0 error, 1 unreachable, 5 info.** The unreachable step is E2 again:
  the BDR-209D is on the AccurateRip list, so the refusal cannot be reached.
- **Graded `full-green`**, the second such row (`docs/testing.md` §5B). The maintainer
  ruled on 2026-10-12 that E2's N/A does not block it, as on 2026-10-07, with E2 recorded
  as not covered. Same machine, distro and person, so it is not 0.9.1's second witness.
- **The witnesses were checked.**
  - K1, K2 and K3 each passed `expect-derived-output` for MP3, WavPack and WAV.
  - All nine album audits reached ok on `ripper_log_integrity`, the cancelled rip's included.
  - The app log holds no error, only warnings.
  - Every screenshot caught the main window on screen.
  - The sections run match the 2026-10-07 run's exactly, A to Q with E2, J2, K1 to K4, P2
    and P3.
- **The disc, again.** Tracks 3 and 5 match AccurateRip only at one frame's offset in both
  14-track rips. Track 3 gave a value not seen before, `029BB984`, in the secure re-read
  (which logged it "ripped with errors"), and `2AC1F945` in the whole-disc rip. Track 5
  gave EAC's unverified `E0036697` in both. CTDB matched the whole-disc rip at confidence 1
  (102 entries), where the 2026-10-07 run found no match at the standard alignment.
  Counts over all 20 committed rips: `docs/eac-parity.md` TL;DR, item 1.
- **The SIGTERM world is unchanged:** ONE SIGNAL (`v07103fulltranscript.txt:575`).
- **Nothing of ours or the ripper's to fix** came out of it.

