# Round 32 — the Full run, 2026-10-13 11:29 UTC, `200530e` (`+platterpus.22`) on Platterpus 0.7.104

**The pair.** This is round 32's test, its lap 1 S6 as our lap 2 S3 amends it: the Full
run on `.22` at `200530e` with our 0.7.104. Every rip log here opens
`cyanrip 0.9.4-rc2+platterpus.22 (platterpus-fork-g200530e)` (164 of 164 banner and tag
lines in the album logs). The app is 0.7.104 at `3577be6`, which pins `ca3f3ea` (`.21`)
and accepts `200530e` as the build under review (`round32fullrigcheckmanifest.txt:5`).

**The bundle.** `platterpusbundle20261013t112919z.tar.gz`: sha256
`8ef9c63f45cc993c52b699bb74bbcc1b0fb8ec34d7d9584a94ebb537bfc4323e`, 7,430,485 bytes,
handed over by the operator. 75 of its 79 text members are filed here byte for byte, each
with a `round32full` prefix and the same names as the round 31 runs'. The tarball is not
committed.

Not filed:
- the 26 screenshots;
- `session/transcript.txt`, which is byte-identical to `round32fulltranscript.txt`;
- the app-log rotations `.3` to `.5`, which end before the run.

There is no audio. The app log's times are local, UTC−4 on this rig.

**The run.** 11:29:19 UTC (the transcript's header) to 16:49:47 UTC, when the app restored
the operator's settings (`round32fullplatterpusapplog.txt:28568`, 12:49:47 local). The
script report says `run_size: full` and `counts_as_evidence: true`.

## What it shows

- **424 pass, 0 fail, 0 error, 1 unreachable, 5 info.** The unreachable step is E2: the
  BDR-209D is on the AccurateRip drive list, so the refusal it checks cannot be reached.
- **Graded `full-green`**, the third such row (`docs/testing.md` §5B). The maintainer
  ruled on 2026-10-13 that E2's N/A does not block it, as on 2026-10-07 and 2026-10-12,
  with E2 recorded as not covered. Same machine, distro and person as the first two, so it
  is not 0.8.1's second witness.
- **The same run as 2026-10-12, step for step.** All 430 step results in the transcript,
  status and verb, equal the 0.7.103 run's (`../artifactsround31/v07103fulltranscript.txt`).
- **The witnesses were checked.**
  - K1, K2 and K3 each passed `expect-derived-output` for MP3, WavPack and WAV.
  - All nine album audits reached ok on `ripper_log_integrity`, the cancelled rip's included.
  - The app log holds no error from launch to the end of the run, only warnings.
  - Every screenshot caught the main window on screen. The windows reported "not on
    screen" are hidden menus and closed dialogs (`visible=False`), as on 2026-10-12.
- **`--diagnostics` on hardware, on `.22`.** All 11 cyanrip invocations of the run carry
  `--diagnostics` and none carries `-j` (their round 32 lap 5 S11; our `d9fb808a`). rig-check
  found all 18 flag tokens we composed intact in the binary's own record, `--diagnostics`
  among them (`round32fullrigcheckmanifest.txt:6`), and `.22` wrote a record for every
  album pass: the nine `round32fulljrecord*.json`.
- **Two records are not here, and nothing in the bundle said so.** The other two
  invocations are securing passes (`-l 3,5` at 12:19:55 UTC and `-l 3` at 16:20:22 UTC). A
  securing pass runs in a temporary folder that is deleted afterwards, so its record goes
  with it (`src/platterpus/workers/rip_worker.py`, the comment above
  `record_path_from_argv`). That is known (TASKS, W6's "not done"), but the bundle's
  MANIFEST names neither absence. Ours to fix; TASKS row R9.
- **The disc, again.** The whole-disc rip matched AccurateRip on 12 of 14 tracks; tracks 3
  and 5 match only at one frame's offset. Track 3 gave `2AC1F945` and track 5 EAC's
  unverified `E0036697`, both as on 2026-10-12, and CTDB matched at confidence 1. The secure
  re-read gave track 3 `69D238D2`, a value first seen in round 30's securing pass of
  2026-10-06 (`../artifactsround30/round30oct06fullwholediscsecuringpass.txt`), and track 5
  `E0036697`. Counts over all 22 committed rips: `docs/eac-parity.md` TL;DR, item 1.
- **The SIGTERM world is unchanged:** ONE SIGNAL (`round32fulltranscript.txt:576`).
- **The `Handshake:` line every log carries** reads `round 32 lap 1 OPEN, verdict OPEN
  (draft — lap not released for reading) -- released build`. It is `.22`'s own sentence,
  compiled in when the build was made, before their lap 1 was released, and printed
  verbatim (`(declared at build time, not verified by cyanrip)`). It describes the build,
  not the round, as round 31's E7 settled.
- **Nothing of the ripper's to fix** came out of it. The one finding is ours (R9 above).
