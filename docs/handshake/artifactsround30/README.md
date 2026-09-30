# Round 30 — the Full run, 2026-09-30 03:07 UTC, `174a134` (`+platterpus.19`) on Platterpus 0.6.65

**Read the build, not the date.** Every rip log here opens
`cyanrip 0.9.4-rc2+platterpus.19 (platterpus-fork-g174a134)`, the build round 30
reviews, on our 0.6.65 (`0981c69`), whose `PIN_UNDER_REVIEW` is `174a134` and whose
`FORK_PIN` is round 29's `51cc789`. This is the run the fork's round 30 lap 1 S10
names: *"The Full run on `.19` installed through your first release naming
`174a134` as its build under review"*. Its script report says `run_size: full` and
`counts_as_evidence: true`. It began at 03:07:05 UTC (the app log's 23:07:05 local,
`round30fullplatterpusapplog2.txt:67661`) and ended at 08:27:48 UTC, when it released
both locks and restored the operator's settings (`round30fullplatterpusapplog.txt:59820`).
The host export's banner (`round30fullrigcheckripperversion.txt`) and every rip log's
first line name the same build; none carries a `-dirty` marker.

**The bundle:** `platterpusbundle20260930t030705z.tar.gz`, sha256
`fa1a533363b330711c14129de58b49b042b655f4ca93d085a810d1d316a047ac`, 4,302,318 bytes,
handed over by the operator. The tarball is not committed; its 52 text members are,
**byte for byte**, with a `round30full` prefix, one per row of the table below. **Not
filed:** the 12 screenshots; `session/transcript.txt`, identical to
`session/run/transcript.txt` (`round30fulltranscript.txt`); and the oldest app-log
rotation (`log.txt.3`), which ends on 2026-09-28, before this run. The `.2` rotation is
filed because the run starts in it. **No audio is here**: the bundle's allowlist refused
every audio file, and `MANIFEST` names each refusal.

## What it shows

Read from each rip's own records, not from the headline.

- **316 pass, 7 fail, 0 error, 0 skipped, 1 info** (the wrapper probe). The run reached
  its last step.
- **The seven failures are screenshot steps, and nothing else failed.** L585 (F), L676
  (H), L724 (I), L749 (J), L815 (K1), L850 (K3) and L988 (N): every screenshot after
  section F's 91-minute rip. Each found every window `visible=True`, with a platform
  window, and `exposed=False`: the app was open and the display was not showing it. The
  four at minute 1 (section D) passed. **The screen-saver inhibit 0.6.65 added for
  exactly this was held for the whole run** (taken at 23:07:05, released at 04:27:48
  local), so it did not prevent it, and the cause is still not established. What ties
  them is the display, not the rips beside them, which are complete. **Fixed after this
  run, for future runs only:** a screenshot now renders the open windows when none is
  exposed, labels them, and records `info`, not `pass` (`TASKS.md`, the screenshot row).
- **Eight rips with a report, and cyanrip verified its own log for all eight**
  (`ripper_log_verification: verified`, exit 0), the cancelled one included: its log
  ends `Rip completed:  no (interrupted by SIGTERM, 0 of 14 tracks)` with its footer
  and `Log FUN512:` (`round30fullcancelme.log:90`). The app logs hold no `ERROR`,
  `CRITICAL` or traceback from the run's start to its end.
- **Every rip is stamped `ripper_handshake_unapproved`**, correctly: 0.6.65's approval
  record is round 29's `51cc789`, and `.19` is the build under review. No report
  carries a diagnostics warning or error; each carries the secure re-read verdict's
  `info` rows (2, and 16 in N).
- **The whole-disc rip (F) matches the EAC baseline on all 14 tracks as shipped**
  (`output_reference/EAC_flac/`), with one exception, track 5, and the auto-fix is why.
  Its first pass read track 3 as `FB789B52`, a third distinct reading of that track,
  and track 5 as `E0036697`, EAC's value. The auto-fix re-read both
  (`round30fullwholediscaddendum.txt`): track 3 converged on `59D352DD`, EAC's value,
  AccurateRip-accurate at confidence 200, and REPLACED the first pass; track 5 converged
  on `6902BCF0` and REPLACED `E0036697`. Both of track 5's readings match AccurateRip on
  frame 450 only, so the swap kept a converged read over an unconverged one of the same
  standing, which is the rule. The verdict says *"13 of 14 … only one frame matched"*
  on the other, and CTDB finds no match (102 entries, confidence 1406).
- **The secure re-read (N) converged on every track**, tracks 1 to 4 and 6 to 14 in 3
  reads and track 5 in 5. Track 3 converged on `3D8FCF0C` and track 5 on `6902BCF0`,
  neither AccurateRip-accurate beyond frame 450, so N is 12 of 14 accurate. Round 29's N
  converged track 3 on `59D352DD`. **So `-Z 2` can converge on a reading that is not the
  accurate one**: two reads that agree are two reads that agree. That is a fact about this
  disc and drive, not a defect in `.19`, and it is reported to the fork as such.
- **Tracks 1 and 2 match EAC in all five partial rips that finished**, and each says
  *"Bit-perfect"*. CTDB records each as `not_whole_disc`, not run.
- **De-emphasis (P3).** Both arms, `-H -E` and `-H -W`, read track 1 as `B0D122E7`,
  EAC's value, AccurateRip-accurate. Round 29's control arm misread it.

## What `.19` changed, seen on the rig

- **Tag keys are in capitals**, with both disc-count keys: `TITLE`, `ALBUM`, `ARTIST`,
  `DISCTOTAL` and `TOTALDISCS` (`round30fullderivedmp3.log:105-120`), as our D2 B asked.
- **The re-read loop's "current checksum" is the track's CRC**: *"Repeating ripping (1 out
  of 2 matches for current checksum B0D122E7)"* (`round30fullsecurereread.log:58`), the
  value the track's `EAC CRC32` line then reports. Round 29's `.18` printed the value
  before the final XOR.

## What it shows that is ours

- **The seven screenshot failures** above. They fall in F, H, I, J, K1, K3 and N, which
  the severity table declares ARCHIVAL, so the run is graded `partial` in the evidence
  ledger (`docs/testing.md` → *Field evidence*). Nothing here re-grades them.
- **The bundle's `screen lock` line said** *"The screen is held on, with no blanking and no
  lock"* (`round30fullmanifest.txt:31`), which the screenshots contradict. The line
  reported the desktop's promise as a fact. Fixed after this run to say so.
- **Checked after the run with the graders written for the next release**: each finished
  rip's self-audit reaches `ok` on every check, the EAC-style log's CRCs agree with the
  ripper's once the addendum is applied, every track has an AccurateRip answer, and CTDB
  was looked up for both whole-disc rips and declined for the six partial ones.

## The files

Each row's sha256 prefix and size are computed from the committed copy.

| our file | tarball member | sha256/16 | bytes |
|---|---|---|---|
| `round30fullaftercanceleac.log` | `album/after cancel 20260930t030705 platterpus-fork-g174a134/after cancel 20260930t030705 platterpus-fork-g174a134 (EAC-compatible).log` | `0abd06154235680f` | 3,356 |
| `round30fullaftercancel.cue` | `album/after cancel 20260930t030705 platterpus-fork-g174a134/after cancel 20260930t030705 platterpus-fork-g174a134.cue` | `48bebc394f88ac40` | 685 |
| `round30fullaftercancel.log` | `album/after cancel 20260930t030705 platterpus-fork-g174a134/after cancel 20260930t030705 platterpus-fork-g174a134.log` | `bf47c758395d1982` | 9,202 |
| `round30fullaftercancelreport.json` | `album/after cancel 20260930t030705 platterpus-fork-g174a134/after cancel 20260930t030705 platterpus-fork-g174a134.platterpus.json` | `a01c527ea2e3fc6c` | 502,140 |
| `round30fullcancelmeeac.log` | `album/cancel me 20260930t030705 platterpus-fork-g174a134/cancel me 20260930t030705 platterpus-fork-g174a134 (EAC-compatible).log` | `52b58ca739a18556` | 2,591 |
| `round30fullcancelme.cue` | `album/cancel me 20260930t030705 platterpus-fork-g174a134/cancel me 20260930t030705 platterpus-fork-g174a134.cue` | `65958adc48a97be3` | 372 |
| `round30fullcancelme.log` | `album/cancel me 20260930t030705 platterpus-fork-g174a134/cancel me 20260930t030705 platterpus-fork-g174a134.log` | `4beb47c1344592f7` | 4,750 |
| `round30fullcancelmereport.json` | `album/cancel me 20260930t030705 platterpus-fork-g174a134/cancel me 20260930t030705 platterpus-fork-g174a134.platterpus.json` | `f09037303ba5aa2d` | 175,435 |
| `round30fullderivedmp3eac.log` | `album/derived mp3 20260930t030705 platterpus-fork-g174a134/derived mp3 20260930t030705 platterpus-fork-g174a134 (EAC-compatible).log` | `13814d0b9ea30511` | 3,393 |
| `round30fullderivedmp3.cue` | `album/derived mp3 20260930t030705 platterpus-fork-g174a134/derived mp3 20260930t030705 platterpus-fork-g174a134.cue` | `843489068553dbab` | 684 |
| `round30fullderivedmp3.log` | `album/derived mp3 20260930t030705 platterpus-fork-g174a134/derived mp3 20260930t030705 platterpus-fork-g174a134.log` | `231452c304f1ea63` | 9,196 |
| `round30fullderivedmp3report.json` | `album/derived mp3 20260930t030705 platterpus-fork-g174a134/derived mp3 20260930t030705 platterpus-fork-g174a134.platterpus.json` | `61ccc1c00d83ff0f` | 510,848 |
| `round30fullderivedwaveac.log` | `album/derived wav 20260930t030705 platterpus-fork-g174a134/derived wav 20260930t030705 platterpus-fork-g174a134 (EAC-compatible).log` | `d781a0714022f3be` | 3,393 |
| `round30fullderivedwav.cue` | `album/derived wav 20260930t030705 platterpus-fork-g174a134/derived wav 20260930t030705 platterpus-fork-g174a134.cue` | `998f40eb1559309a` | 684 |
| `round30fullderivedwav.log` | `album/derived wav 20260930t030705 platterpus-fork-g174a134/derived wav 20260930t030705 platterpus-fork-g174a134.log` | `b44182ea65e27226` | 9,196 |
| `round30fullderivedwavreport.json` | `album/derived wav 20260930t030705 platterpus-fork-g174a134/derived wav 20260930t030705 platterpus-fork-g174a134.platterpus.json` | `b03b6adf3d2d8410` | 526,969 |
| `round30fullderivedwavpackeac.log` | `album/derived wavpack 20260930t030705 platterpus-fork-g174a134/derived wavpack 20260930t030705 platterpus-fork-g174a134 (EAC-compatible).log` | `8c5115a128c3dfc5` | 3,405 |
| `round30fullderivedwavpack.cue` | `album/derived wavpack 20260930t030705 platterpus-fork-g174a134/derived wavpack 20260930t030705 platterpus-fork-g174a134.cue` | `a1f6b4180466c5e7` | 688 |
| `round30fullderivedwavpack.log` | `album/derived wavpack 20260930t030705 platterpus-fork-g174a134/derived wavpack 20260930t030705 platterpus-fork-g174a134.log` | `e19498d3032c3c99` | 9,220 |
| `round30fullderivedwavpackreport.json` | `album/derived wavpack 20260930t030705 platterpus-fork-g174a134/derived wavpack 20260930t030705 platterpus-fork-g174a134.platterpus.json` | `cbbd08dfc4b403e6` | 517,364 |
| `round30fullwholedisceac.log` | `album/full acceptance_ angle_bracket 20260930t03__terpus-fork-g174a134/full acceptance∶ angle‹bracket 20260930t030705 platterpus-fork-g174a134 (EAC-compatible).log` | `7f80367cb7304dea` | 9,500 |
| `round30fullwholedisc.cue` | `album/full acceptance_ angle_bracket 20260930t03__terpus-fork-g174a134/full acceptance∶ angle‹bracket 20260930t030705 platterpus-fork-g174a134.cue` | `c096619612930afb` | 3,149 |
| `round30fullwholedisc.log` | `album/full acceptance_ angle_bracket 20260930t03__terpus-fork-g174a134/full acceptance∶ angle‹bracket 20260930t030705 platterpus-fork-g174a134.log` | `2fe217bc7acfc85b` | 40,162 |
| `round30fullwholediscaddendum.txt` | `album/full acceptance_ angle_bracket 20260930t03__terpus-fork-g174a134/full acceptance∶ angle‹bracket 20260930t030705 platterpus-fork-g174a134.platterpus-addendum.txt` | `495e7458c52ce40a` | 2,302 |
| `round30fullwholediscreport.json` | `album/full acceptance_ angle_bracket 20260930t03__terpus-fork-g174a134/full acceptance∶ angle‹bracket 20260930t030705 platterpus-fork-g174a134.platterpus.json` | `dccb3dcffe693716` | 5,581,297 |
| `round30fulloverwriteeac.log` | `album/full acceptance_ angle_bracket 20260930t03__us-fork-g174a134 _2_/full acceptance∶ angle‹bracket 20260930t030705 platterpus-fork-g174a134 (EAC-compatible).log` | `6f722fb63b53d96c` | 3,459 |
| `round30fulloverwrite.cue` | `album/full acceptance_ angle_bracket 20260930t03__us-fork-g174a134 _2_/full acceptance∶ angle‹bracket 20260930t030705 platterpus-fork-g174a134.cue` | `00da832a96fa65e8` | 747 |
| `round30fulloverwrite.log` | `album/full acceptance_ angle_bracket 20260930t03__us-fork-g174a134 _2_/full acceptance∶ angle‹bracket 20260930t030705 platterpus-fork-g174a134.log` | `8d84bb1cd1055a00` | 9,575 |
| `round30fulloverwritereport.json` | `album/full acceptance_ angle_bracket 20260930t03__us-fork-g174a134 _2_/full acceptance∶ angle‹bracket 20260930t030705 platterpus-fork-g174a134.platterpus.json` | `7ef630e4ab558491` | 493,944 |
| `round30fulldeemphoff.cue` | `album/r16deemphoff/Unknown disc (PNTI).cue` | `f3c0672791431738` | 262 |
| `round30fulldeemphoff.log` | `album/r16deemphoff/Unknown disc (PNTI).log` | `157bd97b3789050f` | 4,805 |
| `round30fulldeemphon.cue` | `album/r16deemphon/Unknown disc (PNTI).cue` | `f3c0672791431738` | 262 |
| `round30fulldeemphon.log` | `album/r16deemphon/Unknown disc (PNTI).log` | `c7f58e5db94f4f8b` | 4,823 |
| `round30fullsecurerereadeac.log` | `album/secure reread 20260930t030705 platterpus-fork-g174a134/secure reread 20260930t030705 platterpus-fork-g174a134 (EAC-compatible).log` | `bcfa2ec233c5193a` | 10,197 |
| `round30fullsecurereread.cue` | `album/secure reread 20260930t030705 platterpus-fork-g174a134/secure reread 20260930t030705 platterpus-fork-g174a134.cue` | `01549da5c14f9cba` | 2,956 |
| `round30fullsecurereread.log` | `album/secure reread 20260930t030705 platterpus-fork-g174a134/secure reread 20260930t030705 platterpus-fork-g174a134.log` | `522d65d31624ea35` | 43,347 |
| `round30fullsecurerereadreport.json` | `album/secure reread 20260930t030705 platterpus-fork-g174a134/secure reread 20260930t030705 platterpus-fork-g174a134.platterpus.json` | `1d958896ce31d330` | 6,170,768 |
| `round30fullcomponents.json` | `COMPONENTS.json` | `2fce7043d44c4395` | 1,339 |
| `round30fulldiagnostics.txt` | `DIAGNOSTICS.txt` | `4e9e065e7273ca37` | 5,728 |
| `round30fullmanifest.txt` | `MANIFEST.txt` | `e6ee70ed7e12f9f8` | 23,939 |
| `round30fullsettings.json` | `SETTINGS.json` | `905abbf1ff697864` | 2,760 |
| `round30fullsources.txt` | `SOURCES.txt` | `048a92b6c26bd668` | 1,739 |
| `round30fullplatterpusapplog.txt` | `session/artifacts/02platterpus/log.txt` | `b02ef5d72fe2246e` | 6,775,132 |
| `round30fullplatterpusapplog1.txt` | `session/zz-applog-rotations/03platterpus/log.txt.1` | `42b8aa3d6907ffd5` | 8,388,508 |
| `round30fullplatterpusapplog2.txt` | `session/zz-applog-rotations/04platterpus/log.txt.2` | `93995681743b4f4c` | 8,388,516 |
| `round30fullconfig.toml` | `session/artifacts/06platterpus/config.toml` | `8d816eea558fa8c8` | 1,141 |
| `round30fullscriptreport.json` | `session/run/report.json` | `976ef07181451632` | 257,532 |
| `round30fulltranscript.txt` | `session/run/transcript.txt` | `2d71dc74f4992008` | 114,354 |
| `round30fullrigcheckmanifest.txt` | `session/run/rig-check/MANIFEST.txt` | `e7a665a89427b8d6` | 15,841 |
| `round30fullrigcheckargvprobe.json` | `session/run/rig-check/argv-probe.json` | `0465a0f4c3252507` | 1,628 |
| `round30fullrigcheckargvprobeoutput.txt` | `session/run/rig-check/argv-probe-output.txt` | `053dae5fd738e837` | 484 |
| `round30fullrigcheckripperversion.txt` | `session/run/rig-check/ripper-version.txt` | `3dd6fb1ac56dbfad` | 58 |
