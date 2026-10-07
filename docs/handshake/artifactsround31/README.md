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
