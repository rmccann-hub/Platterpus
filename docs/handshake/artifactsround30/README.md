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

## The 2026-10-04 runs — a damaged disc, on the same `.19` and 0.6.65

**Four acceptance runs, one afternoon, the same pair as above**: every rip log opens
`cyanrip 0.9.4-rc2+platterpus.19 (platterpus-fork-g174a134)` and every report names
Platterpus 0.6.65 (`0981c69`). A first run at 15:19:39 UTC was not uploaded; run 3's
app log carries it (`round30oct04platterpusapplog2.txt:59929` to `:60048`). The
operator's three bundles:

| run | bundle | sha256 | bytes |
|---|---|---|---|
| run 1 | `platterpusbundle20261004t152045z.tar.gz` | `034682685559cfede1b68cd89fd32bd460f86340f587fd93f4b3a5eaa25f559d` | 3,139,178 |
| run 2 | `platterpusbundle20261004t160027z.tar.gz` | `aeb66f4ed52c9d5bbc4fa22cb06c5bbaff50c935d0b4b4f6acb21ac4d6809bc9` | 3,119,311 |
| run 3 | `platterpusbundle20261004t160255z.tar.gz` | `d7881c27575d42b835f27a0796f4713e9d0e42ddd05f4ea9a79ea14c2fded888` | 6,397,797 |

The tarballs are not committed. Filed byte for byte with a `round30oct04` prefix: run
3's 38 text members below, and each of runs 1 and 2's manifest, transcript and script
report. **Not filed:** every screenshot; `session/transcript.txt`, identical to
`session/run/transcript.txt`; run 3's app-log rotations `.3` to `.5`, which end before
the run began; and runs 1 and 2's app logs, which run 3's `.2` rotation contains. **No
audio is here**: each bundle's allowlist refused every audio file, and its manifest
names each refusal.

### What they show

- **The 15:19 run and runs 1 and 2 stopped in section E, and were right to.** Two
  discs MusicBrainz does not know (disc IDs `PKt4tUZ9zkm_5aEh6ButPQLlNs0-`, 16 tracks,
  at 15:19 and 15:20, and `83jwDRaSUuT.GTqbBXMLHeQRAKw-`, 11 tracks, at 16:00; both
  answer 404 from MusicBrainz): `expect-identified` failed and each run ended there,
  107 of 323. The disc the earlier round-30 runs used, `pNtImOkdBm9RMBIalzx0w9cfsYY-`,
  is in MusicBrainz. `pick-release` had passed just before it, saying the disc
  "identified unambiguously" with "Rip as unknown album" on screen (fixed after these
  runs: it now fails on that dialog and passes only on a held release).
- **Run 3's disc is damaged.** *Roots Music: An American Journey*, disc 1 of 4
  (`zxtbw2JgJ.kZBiyIcKOQvn2ZTUM-`). Track 18 read with 279 reads over 10 s, the
  longest 54 s, and 2,586 paranoia skips; its whole-track AccurateRip checksums were
  not found and one frame matched (`round30oct04full.log`, and line 1501 for the stall
  summary). The album pass took three hours. The securing pass then re-read tracks 12
  to 15, 17 and 18, the six that matched AccurateRip on one frame only; on each of 12
  to 17 the ripper reached its limit of five reads with no two agreeing (the app log's
  `ripper.secure_rerip_verdict` warnings, `round30oct04platterpusapplog1.txt`).
- **Section F's six-hour wait ran out with the securing pass on track 18**, so sections
  H and I failed against a rip still running, and I's `cancel-rip` cancelled F's rip
  at 19:07 local, 7h 3m in. Ten failures, all in ARCHIVAL sections and all downstream
  of the disc. Sections J to M passed. Section N's whole-disc secure re-read was 87
  minutes in, 10 tracks converged after three reads each, when the run was stopped from
  the console; the bundle was written with that rip still running, so its log has no
  footer (`round30oct04securereread.log`).
- **Defects of ours, each fixed after the run with a regression test.** The stopped
  securing pass discarded the verdicts it had reached for tracks 12 to 17, so
  `round30oct04fulleac.log` prints "Copy OK" over them; the status line read "Done —
  all 18 tracks ripped cleanly, no read errors" after the cancel and over track 18's
  skips; `cancel-rip` stopped an earlier step's rip; `pick-release` called an
  unidentified disc identified; and the 42 s quit grace was shorter than the 54 s read
  (now 108 s, read by `tests/test_drive_control.py` from the log filed here).
- **Two smaller things in the logs.** At launch, 11:18:30 local, two cyanrip calls
  entered the cold container together: the dependency check's version probe printed
  its 99-character banner and did not exit until our 60 s timeout, and the startup
  disc scan never returned and was superseded 84 s later
  (`round30oct04platterpusapplog2.txt:59910`, `:59918`). It cost a minute and no
  run. And after each disc swap the disc panel showed "—" for the read offset and
  cache defeat until the next rescan, because the disc-removal reset cleared those
  drive rows too; fixed after these runs. The offset applied was +667 throughout.
- **Of the ripper:** its `Ripping errors: 0` beside 2,586 skips is how cyanrip counts
  (`cyanrip@174a134:src/cyanrip_main.c:537-553` counts only reads that failed
  outright), not a fault in `.19`. Nothing here breaks the pin.

| filed | run | bundle member | sha256/16 | bytes |
|---|---|---|---|---|
| `round30oct04aftercancel.cue` | run 3 | `album/after cancel 20261004t160255 platterpus-fork-g174a134/after cancel 20261004t160255 platterpus-fork-g174a134 CD1.cue` | `9be78ad6111471e4` | 788 |
| `round30oct04aftercancel.log` | run 3 | `album/after cancel 20261004t160255 platterpus-fork-g174a134/after cancel 20261004t160255 platterpus-fork-g174a134 CD1.log` | `70d4bd39259ac0a4` | 9,954 |
| `round30oct04aftercanceleac.log` | run 3 | `album/after cancel 20261004t160255 platterpus-fork-g174a134/after cancel 20261004t160255 platterpus-fork-g174a134 CD1 (EAC-compatible).log` | `3e8ebcad6219dd8c` | 3,381 |
| `round30oct04aftercancelreport.json` | run 3 | `album/after cancel 20261004t160255 platterpus-fork-g174a134/after cancel 20261004t160255 platterpus-fork-g174a134 CD1.platterpus.json` | `785dbd300db548dc` | 505,136 |
| `round30oct04components.json` | run 3 | `COMPONENTS.json` | `36750ddc3ef0a759` | 1,339 |
| `round30oct04config.toml` | run 3 | `session/artifacts/08platterpus/config.toml` | `8d816eea558fa8c8` | 1,141 |
| `round30oct04derivedmp3.cue` | run 3 | `album/derived mp3 20261004t160255 platterpus-fork-g174a134/derived mp3 20261004t160255 platterpus-fork-g174a134 CD1.cue` | `6b9bc9abd3b6130b` | 787 |
| `round30oct04derivedmp3.log` | run 3 | `album/derived mp3 20261004t160255 platterpus-fork-g174a134/derived mp3 20261004t160255 platterpus-fork-g174a134 CD1.log` | `71fcc15f87260416` | 9,892 |
| `round30oct04derivedmp3eac.log` | run 3 | `album/derived mp3 20261004t160255 platterpus-fork-g174a134/derived mp3 20261004t160255 platterpus-fork-g174a134 CD1 (EAC-compatible).log` | `790a75eb66024d8c` | 3,418 |
| `round30oct04derivedmp3report.json` | run 3 | `album/derived mp3 20261004t160255 platterpus-fork-g174a134/derived mp3 20261004t160255 platterpus-fork-g174a134 CD1.platterpus.json` | `5e350794ce9cbb72` | 510,644 |
| `round30oct04derivedwav.cue` | run 3 | `album/derived wav 20261004t160255 platterpus-fork-g174a134/derived wav 20261004t160255 platterpus-fork-g174a134 CD1.cue` | `46d4640d6876193f` | 787 |
| `round30oct04derivedwav.log` | run 3 | `album/derived wav 20261004t160255 platterpus-fork-g174a134/derived wav 20261004t160255 platterpus-fork-g174a134 CD1.log` | `56f113e0569c763c` | 9,892 |
| `round30oct04derivedwaveac.log` | run 3 | `album/derived wav 20261004t160255 platterpus-fork-g174a134/derived wav 20261004t160255 platterpus-fork-g174a134 CD1 (EAC-compatible).log` | `7549e1bdff008799` | 3,418 |
| `round30oct04derivedwavpack.cue` | run 3 | `album/derived wavpack 20261004t160255 platterpus-fork-g174a134/derived wavpack 20261004t160255 platterpus-fork-g174a134 CD1.cue` | `c04ae2052f37b719` | 791 |
| `round30oct04derivedwavpack.log` | run 3 | `album/derived wavpack 20261004t160255 platterpus-fork-g174a134/derived wavpack 20261004t160255 platterpus-fork-g174a134 CD1.log` | `e558d7634a56b42b` | 9,916 |
| `round30oct04derivedwavpackeac.log` | run 3 | `album/derived wavpack 20261004t160255 platterpus-fork-g174a134/derived wavpack 20261004t160255 platterpus-fork-g174a134 CD1 (EAC-compatible).log` | `bf27a3ca0229fbd7` | 3,430 |
| `round30oct04derivedwavpackreport.json` | run 3 | `album/derived wavpack 20261004t160255 platterpus-fork-g174a134/derived wavpack 20261004t160255 platterpus-fork-g174a134 CD1.platterpus.json` | `82749de2935e453e` | 517,195 |
| `round30oct04derivedwavreport.json` | run 3 | `album/derived wav 20261004t160255 platterpus-fork-g174a134/derived wav 20261004t160255 platterpus-fork-g174a134 CD1.platterpus.json` | `319d2843f6cb3f28` | 525,530 |
| `round30oct04diagnostics.txt` | run 3 | `DIAGNOSTICS.txt` | `223b6d3ae4d67c0c` | 4,897 |
| `round30oct04full.cue` | run 3 | `album/full acceptance_ angle_bracket 20261004t16__terpus-fork-g174a134/full acceptance∶ angle‹bracket 20261004t160255 platterpus-fork-g174a134 CD1.cue` | `b3d9c864e7c59141` | 3,519 |
| `round30oct04full.log` | run 3 | `album/full acceptance_ angle_bracket 20261004t16__terpus-fork-g174a134/full acceptance∶ angle‹bracket 20261004t160255 platterpus-fork-g174a134 CD1.log` | `15372c9cc33f6fec` | 53,020 |
| `round30oct04fulleac.log` | run 3 | `album/full acceptance_ angle_bracket 20261004t16__terpus-fork-g174a134/full acceptance∶ angle‹bracket 20261004t160255 platterpus-fork-g174a134 CD1 (EAC-compatible).log` | `f5b9acc4506e01b5` | 11,806 |
| `round30oct04fullreport.json` | run 3 | `album/full acceptance_ angle_bracket 20261004t16__terpus-fork-g174a134/full acceptance∶ angle‹bracket 20261004t160255 platterpus-fork-g174a134 CD1.platterpus.json` | `d658601b45b329e8` | 7,308,860 |
| `round30oct04manifest.txt` | run 3 | `MANIFEST.txt` | `f848aee6ee765796` | 50,213 |
| `round30oct04platterpusapplog.txt` | run 3 | `session/artifacts/02platterpus/log.txt` | `732f9e86403b7db6` | 4,857,449 |
| `round30oct04platterpusapplog1.txt` | run 3 | `session/zz-applog-rotations/03platterpus/log.txt.1` | `102ca6638f2dccda` | 8,388,572 |
| `round30oct04platterpusapplog2.txt` | run 3 | `session/zz-applog-rotations/04platterpus/log.txt.2` | `d81ebcfa49ecd224` | 8,388,557 |
| `round30oct04rigcheckargvprobe.json` | run 3 | `session/run/rig-check/argv-probe.json` | `eefbfbe4c46b1327` | 1,628 |
| `round30oct04rigcheckargvprobeoutput.txt` | run 3 | `session/run/rig-check/argv-probe-output.txt` | `03f6b131d7d2b2b9` | 484 |
| `round30oct04rigcheckmanifest.txt` | run 3 | `session/run/rig-check/MANIFEST.txt` | `d5c892d3a3581b4c` | 13,884 |
| `round30oct04rigcheckripperversion.txt` | run 3 | `session/run/rig-check/ripper-version.txt` | `3dd6fb1ac56dbfad` | 58 |
| `round30oct04run1manifest.txt` | run 1 | `MANIFEST.txt` | `c0b77ae660271e3e` | 5,060 |
| `round30oct04run1scriptreport.json` | run 1 | `session/run/report.json` | `b7d613c094f313d2` | 186,710 |
| `round30oct04run1transcript.txt` | run 1 | `session/run/transcript.txt` | `b3b7406de057c059` | 32,156 |
| `round30oct04run2manifest.txt` | run 2 | `MANIFEST.txt` | `746bd199285fccca` | 5,060 |
| `round30oct04run2scriptreport.json` | run 2 | `session/run/report.json` | `eb3e1af32d362cce` | 186,752 |
| `round30oct04run2transcript.txt` | run 2 | `session/run/transcript.txt` | `ac6e3e7e56529f68` | 32,246 |
| `round30oct04scriptreport.json` | run 3 | `session/run/report.json` | `7c8b727a72a17ea9` | 225,948 |
| `round30oct04securereread.cue` | run 3 | `album/secure reread 20261004t160255 platterpus-fork-g174a134/secure reread 20261004t160255 platterpus-fork-g174a134 CD1.cue` | `248d442185350150` | 2,133 |
| `round30oct04securereread.log` | run 3 | `album/secure reread 20261004t160255 platterpus-fork-g174a134/secure reread 20261004t160255 platterpus-fork-g174a134 CD1.log` | `848fb243d2d5b285` | 32,719 |
| `round30oct04securerereadreport.json` | run 3 | `album/secure reread 20261004t160255 platterpus-fork-g174a134/secure reread 20261004t160255 platterpus-fork-g174a134 CD1.platterpus.json` | `8f3c4dc29e96de07` | 225,045 |
| `round30oct04settings.json` | run 3 | `SETTINGS.json` | `6d5726cad6e6cab6` | 2,623 |
| `round30oct04sources.txt` | run 3 | `SOURCES.txt` | `1fbad15fdbe1b141` | 1,979 |
| `round30oct04transcript.txt` | run 3 | `session/run/transcript.txt` | `005c73757af6a6c6` | 74,919 |

## The 2026-10-05 run — the operator's final Full run on `.19` and 0.6.65

**The run the operator promised for the morning of 2026-10-05, on the same pair as
everything above**: every rip log opens `cyanrip 0.9.4-rc2+platterpus.19
(platterpus-fork-g174a134)`, every report names Platterpus 0.6.65 (`0981c69`), and the
disc is the round's usual one, *The Police — Every Breath You Take: The Classics*
(`pNtImOkdBm9RMBIalzx0w9cfsYY-`). Its script report says `run_size: full` and
`counts_as_evidence: true`. It began at 01:08:35 UTC
(`round30oct05fullplatterpusapplog2.txt:44864`, local 21:08:35) and ended at 06:17:58
UTC, when it released its locks and restored the operator's settings
(`round30oct05fullplatterpusapplog.txt:55405`).

**The bundle:** `platterpusbundle20261005t010835z.tar.gz`, sha256
`d4a35338c6d9466b835f0e7bc33a1ef551a7964b0d91815f6de863ab274ef189`, 5,210,218 bytes,
uploaded by the operator. Filed byte for byte with a `round30oct05full` prefix: its 51
text members, one per row below. **Not filed:** the 12 screenshots;
`session/transcript.txt`, identical to `session/run/transcript.txt`; and the app-log
rotations `.3` to `.5`, which end before the run began. **No audio is here**: the
bundle's allowlist refused every audio file, and its manifest names each refusal.

### What it shows

- **316 pass, 7 fail, 0 error, 0 skipped, 1 info** (the wrapper probe), and the run
  reached its last step: the same count as the 2026-09-30 run above.
- **The seven failures are the same seven screenshot steps**, L585 (F) to L988 (N),
  each finding every window `visible=True` and `exposed=False`
  (`round30oct05fulltranscript.txt:387` to `:866`), with the screen lock held the whole
  run. The fix that renders the open windows and records `info` (`5fe413a5`,
  2026-09-30) is not in 0.6.65, so this run could not have taken it. The sections are
  graded ARCHIVAL in advance, so the run is `partial`.
- **Eight rips with a report, and cyanrip verified its own log for all eight**, the
  cancelled one included: its log ends `Rip completed:  no (interrupted by SIGTERM, 0 of
  14 tracks)` with its footer and `Log FUN512:` (`round30oct05fullcancelme.log:90`).
  Its `Ripping errors: 1` is the interrupted read, which the fork's `KNOWN-ISSUES.md`
  records and every cancel run since round 29 shows. Every report is stamped
  `ripper_handshake_unapproved`, correctly, as above. **No `ERROR`, `CRITICAL` or
  traceback from the run's start to its end.** The two errors in the `.2` rotation, at
  21:03:41 local (`round30oct05fullplatterpusapplog2.txt:44815`), are five minutes
  before it: the 2026-10-04 session's rip, still reading hours after that run was
  stopped, failed when its folder was gone, and the window was closed with it in
  flight. That is the defect `d62f1ca4` fixed (a run's rip is cancelled when the run
  ends), seen once more from its far side.
- **Track 3 of this disc no longer reads the same way twice.** The whole-disc rip (F)
  read it as `35FEA00E` and the securing pass's five re-reads did not agree
  (`round30oct05fullplatterpusapplog1.txt:9584`). The whole-disc secure re-read (N)
  read it five times with five different checksums, none agreeing, and kept the
  last, `601E1A13` (`round30oct05fullsecurereread.log:220-228`). EAC's value is `59D352DD`,
  which the 2026-09-30 run reached by convergence. Track 5 read as `6902BCF0` in F,
  its other stable reading, and its re-reads did not agree either
  (`round30oct05fullplatterpusapplog1.txt:18303`); in N it converged on `E0036697`,
  EAC's. **Every other track matches EAC in both rips** (12 of 14 in F, 13 of 14 in N),
  and in F AccurateRip confirmed 12 of 14, with tracks 3 and 5 matching one frame only.
  CTDB found no match (102 entries, confidence 1408), as before. The EAC-layout logs
  say `Copy NOT confirmed` over each unconverged track and name them under *Read
  stability*, and nothing was swapped. **Nothing here is a defect in `.19` or in
  0.6.65**: it is the disc, as the differing readings of track 3 in the 2026-09-26,
  2026-09-28 and 2026-09-30 runs first suggested.
- **The cancel, measured a third time.** The user cancel at 22:44:57.041 local signalled
  the host wrapper's process group; the rescue's SIGTERM followed at 22:45:01.791
  (`round30oct05fullplatterpusapplog1.txt:22161` and `:22165`), and cyanrip stamped its
  footer at 22:45:02 (`round30oct05fullcancelme.log:92`), about a second after the
  rescue's signal and five after the cancel's. As on 2026-09-09, the rescue's SIGTERM is
  the first signal the reader acts on.
- **The new time estimate, checked against this run** (it was not in 0.6.65; computed
  afterwards from the reports): F took 5,286 s against a model of 5,449 to 6,567 s for
  its main pass plus five reads each of tracks 3 and 5; N took 10,950 s against a floor
  of 11,296 s. Both came in 3% under, because this run's first pass read at 0.84
  seconds per second of audio, faster than any filed before (0.88 to 1.09); a drive's
  own history, which 0.6.66 keeps, moves the estimate with it.
- **No `-j` record is in the bundle**, as on 2026-10-04: 0.6.65 does not collect them,
  and `a7a631b9` does.

### The files

| our file | tarball member | sha256/16 | bytes |
|---|---|---|---|
| `round30oct05fullaftercanceleac.log` | `album/after cancel 20261005t010835 platterpus-fork-g174a134/after cancel 20261005t010835 platterpus-fork-g174a134 (EAC-compatible).log` | `46450cbafcef4710` | 3,353 |
| `round30oct05fullaftercancel.cue` | `album/after cancel 20261005t010835 platterpus-fork-g174a134/after cancel 20261005t010835 platterpus-fork-g174a134.cue` | `3dbcd8b707548047` | 685 |
| `round30oct05fullaftercancel.log` | `album/after cancel 20261005t010835 platterpus-fork-g174a134/after cancel 20261005t010835 platterpus-fork-g174a134.log` | `f01b337b074d7ce8` | 9,202 |
| `round30oct05fullaftercancelreport.json` | `album/after cancel 20261005t010835 platterpus-fork-g174a134/after cancel 20261005t010835 platterpus-fork-g174a134.platterpus.json` | `29f1140eef7716f8` | 489,484 |
| `round30oct05fullcancelmeeac.log` | `album/cancel me 20261005t010835 platterpus-fork-g174a134/cancel me 20261005t010835 platterpus-fork-g174a134 (EAC-compatible).log` | `ec9ef63c45255469` | 2,588 |
| `round30oct05fullcancelme.cue` | `album/cancel me 20261005t010835 platterpus-fork-g174a134/cancel me 20261005t010835 platterpus-fork-g174a134.cue` | `78adc14cf99511a9` | 372 |
| `round30oct05fullcancelme.log` | `album/cancel me 20261005t010835 platterpus-fork-g174a134/cancel me 20261005t010835 platterpus-fork-g174a134.log` | `0fa6fd204bf7edbe` | 4,750 |
| `round30oct05fullcancelmereport.json` | `album/cancel me 20261005t010835 platterpus-fork-g174a134/cancel me 20261005t010835 platterpus-fork-g174a134.platterpus.json` | `97b64c4dfc83c5fd` | 182,554 |
| `round30oct05fullderivedmp3eac.log` | `album/derived mp3 20261005t010835 platterpus-fork-g174a134/derived mp3 20261005t010835 platterpus-fork-g174a134 (EAC-compatible).log` | `fa23634e75db1218` | 3,390 |
| `round30oct05fullderivedmp3.cue` | `album/derived mp3 20261005t010835 platterpus-fork-g174a134/derived mp3 20261005t010835 platterpus-fork-g174a134.cue` | `43792632b49225d1` | 684 |
| `round30oct05fullderivedmp3.log` | `album/derived mp3 20261005t010835 platterpus-fork-g174a134/derived mp3 20261005t010835 platterpus-fork-g174a134.log` | `9aa9101648ebf810` | 9,196 |
| `round30oct05fullderivedmp3report.json` | `album/derived mp3 20261005t010835 platterpus-fork-g174a134/derived mp3 20261005t010835 platterpus-fork-g174a134.platterpus.json` | `53655418c98f5d17` | 498,176 |
| `round30oct05fullderivedwaveac.log` | `album/derived wav 20261005t010835 platterpus-fork-g174a134/derived wav 20261005t010835 platterpus-fork-g174a134 (EAC-compatible).log` | `0dece4b95146391b` | 3,390 |
| `round30oct05fullderivedwav.cue` | `album/derived wav 20261005t010835 platterpus-fork-g174a134/derived wav 20261005t010835 platterpus-fork-g174a134.cue` | `2bb628ba150fa9f5` | 684 |
| `round30oct05fullderivedwav.log` | `album/derived wav 20261005t010835 platterpus-fork-g174a134/derived wav 20261005t010835 platterpus-fork-g174a134.log` | `5684beb45a0acf0b` | 9,196 |
| `round30oct05fullderivedwavreport.json` | `album/derived wav 20261005t010835 platterpus-fork-g174a134/derived wav 20261005t010835 platterpus-fork-g174a134.platterpus.json` | `dc930e314fdc00bd` | 513,211 |
| `round30oct05fullderivedwavpackeac.log` | `album/derived wavpack 20261005t010835 platterpus-fork-g174a134/derived wavpack 20261005t010835 platterpus-fork-g174a134 (EAC-compatible).log` | `0b9f78c63f910484` | 3,402 |
| `round30oct05fullderivedwavpack.cue` | `album/derived wavpack 20261005t010835 platterpus-fork-g174a134/derived wavpack 20261005t010835 platterpus-fork-g174a134.cue` | `8f760467b909daef` | 688 |
| `round30oct05fullderivedwavpack.log` | `album/derived wavpack 20261005t010835 platterpus-fork-g174a134/derived wavpack 20261005t010835 platterpus-fork-g174a134.log` | `90609ca107d58e1e` | 9,220 |
| `round30oct05fullderivedwavpackreport.json` | `album/derived wavpack 20261005t010835 platterpus-fork-g174a134/derived wavpack 20261005t010835 platterpus-fork-g174a134.platterpus.json` | `f3c47394a3eb095f` | 504,424 |
| `round30oct05fullsecurerereadeac.log` | `album/secure reread 20261005t010835 platterpus-fork-g174a134/secure reread 20261005t010835 platterpus-fork-g174a134 (EAC-compatible).log` | `78fd6f3eb013e042` | 10,385 |
| `round30oct05fullsecurereread.cue` | `album/secure reread 20261005t010835 platterpus-fork-g174a134/secure reread 20261005t010835 platterpus-fork-g174a134.cue` | `8a2c42b850435fea` | 2,956 |
| `round30oct05fullsecurereread.log` | `album/secure reread 20261005t010835 platterpus-fork-g174a134/secure reread 20261005t010835 platterpus-fork-g174a134.log` | `b8647b8df82f631c` | 43,471 |
| `round30oct05fullsecurerereadreport.json` | `album/secure reread 20261005t010835 platterpus-fork-g174a134/secure reread 20261005t010835 platterpus-fork-g174a134.platterpus.json` | `8af212575fc1acdb` | 6,169,897 |
| `round30oct05fullwholedisceac.log` | `album/full acceptance_ angle_bracket 20261005t01__terpus-fork-g174a134/full acceptance∶ angle‹bracket 20261005t010835 platterpus-fork-g174a134 (EAC-compatible).log` | `dd4a624f3c941781` | 9,834 |
| `round30oct05fullwholedisc.cue` | `album/full acceptance_ angle_bracket 20261005t01__terpus-fork-g174a134/full acceptance∶ angle‹bracket 20261005t010835 platterpus-fork-g174a134.cue` | `f54d4c6b46c9579a` | 3,149 |
| `round30oct05fullwholedisc.log` | `album/full acceptance_ angle_bracket 20261005t01__terpus-fork-g174a134/full acceptance∶ angle‹bracket 20261005t010835 platterpus-fork-g174a134.log` | `1e7c988457877cc5` | 40,187 |
| `round30oct05fullwholediscreport.json` | `album/full acceptance_ angle_bracket 20261005t01__terpus-fork-g174a134/full acceptance∶ angle‹bracket 20261005t010835 platterpus-fork-g174a134.platterpus.json` | `2d07ac7a32683484` | 6,256,172 |
| `round30oct05fulloverwriteeac.log` | `album/full acceptance_ angle_bracket 20261005t01__us-fork-g174a134 _2_/full acceptance∶ angle‹bracket 20261005t010835 platterpus-fork-g174a134 (EAC-compatible).log` | `980b8d671a5890b4` | 3,456 |
| `round30oct05fulloverwrite.cue` | `album/full acceptance_ angle_bracket 20261005t01__us-fork-g174a134 _2_/full acceptance∶ angle‹bracket 20261005t010835 platterpus-fork-g174a134.cue` | `93e11d866953acf4` | 747 |
| `round30oct05fulloverwrite.log` | `album/full acceptance_ angle_bracket 20261005t01__us-fork-g174a134 _2_/full acceptance∶ angle‹bracket 20261005t010835 platterpus-fork-g174a134.log` | `09bdba09ba14e64b` | 9,575 |
| `round30oct05fulloverwritereport.json` | `album/full acceptance_ angle_bracket 20261005t01__us-fork-g174a134 _2_/full acceptance∶ angle‹bracket 20261005t010835 platterpus-fork-g174a134.platterpus.json` | `02faa20cecf46b6e` | 481,948 |
| `round30oct05fulldeemphoff.cue` | `album/r16deemphoff/Unknown disc (PNTI).cue` | `f3c0672791431738` | 262 |
| `round30oct05fulldeemphoff.log` | `album/r16deemphoff/Unknown disc (PNTI).log` | `cba81f4af7e15066` | 4,805 |
| `round30oct05fulldeemphon.cue` | `album/r16deemphon/Unknown disc (PNTI).cue` | `f3c0672791431738` | 262 |
| `round30oct05fulldeemphon.log` | `album/r16deemphon/Unknown disc (PNTI).log` | `b3ef5844d3e4724e` | 4,823 |
| `round30oct05fullcomponents.json` | `COMPONENTS.json` | `3be5759169a4a284` | 1,339 |
| `round30oct05fulldiagnostics.txt` | `DIAGNOSTICS.txt` | `3e7a1579d5bdafb2` | 5,962 |
| `round30oct05fullmanifest.txt` | `MANIFEST.txt` | `60e623e9dcadf5a3` | 24,372 |
| `round30oct05fullsettings.json` | `SETTINGS.json` | `9cd5a169eb2e0c5a` | 2,760 |
| `round30oct05fullsources.txt` | `SOURCES.txt` | `0fb21815079f0e01` | 2,217 |
| `round30oct05fullplatterpusapplog.txt` | `session/artifacts/02platterpus/log.txt` | `37df2bf17bed8495` | 6,239,918 |
| `round30oct05fullplatterpusapplog1.txt` | `session/zz-applog-rotations/03platterpus/log.txt.1` | `024b3b262fb0c515` | 8,388,508 |
| `round30oct05fullplatterpusapplog2.txt` | `session/zz-applog-rotations/04platterpus/log.txt.2` | `a8cd0f5cb3e042d2` | 8,388,563 |
| `round30oct05fullconfig.toml` | `session/artifacts/10platterpus/config.toml` | `8d816eea558fa8c8` | 1,141 |
| `round30oct05fullscriptreport.json` | `session/run/report.json` | `abdab97ab170dac0` | 256,147 |
| `round30oct05fulltranscript.txt` | `session/run/transcript.txt` | `482e96b048cd62b7` | 112,889 |
| `round30oct05fullrigcheckmanifest.txt` | `session/run/rig-check/MANIFEST.txt` | `f499717f24473d92` | 15,841 |
| `round30oct05fullrigcheckargvprobe.json` | `session/run/rig-check/argv-probe.json` | `368309967ce1e3b2` | 1,628 |
| `round30oct05fullrigcheckargvprobeoutput.txt` | `session/run/rig-check/argv-probe-output.txt` | `321c0320930cf65e` | 484 |
| `round30oct05fullrigcheckripperversion.txt` | `session/run/rig-check/ripper-version.txt` | `3dd6fb1ac56dbfad` | 58 |

## The 2026-10-06 run — round 30's closing run, on `.20` and 0.6.66b1

**The run round 30 closes on, on the pair the operator's conditions name**: every rip log
opens `cyanrip 0.9.4-rc2+platterpus.20 (platterpus-fork-g5704062)`, every report names
Platterpus 0.6.66b1 (`db5fd0e`), and the disc is the round's usual one, *The Police —
Every Breath You Take: The Classics*. Its script report says `run_size: full` and
`counts_as_evidence: true`. It began at 01:58:21 UTC
(`round30oct06fullplatterpusapplog2.txt:55800`, local 21:58:21) and ended at 07:31:45
UTC, when it released its locks and restored the operator's settings
(`round30oct06fullplatterpusapplog.txt:75495`): 5 h 33 m, against the run's own
estimate of *at least 5 h 10 m* stated at its start.

**The bundle:** `platterpusbundle20261006t015821z.tar.gz`, sha256
`bf0aa42428ee5c4b82af332714a36495f134f82dc9af0073866654e9b1ae4879`, 6,836,717 bytes,
uploaded by the operator. Filed byte for byte with a `round30oct06full` prefix: its 76
text members, one per row below, the nine `-j` records among them (0.6.66b1 is the first
release to collect them). **Not filed:** the 26 screenshots; `session/transcript.txt`,
identical to `session/run/transcript.txt`; and the app-log rotations `.3` and `.4`, which
end before the run began. **No audio is here**: the bundle's allowlist refused every
audio file, and its manifest names each refusal.

### What it shows

- **418 pass, 7 fail, 0 error, 1 unreachable, 5 info**, and the run reached its last
  step. Every screenshot step passed: the screen hold (0.6.65) and the rendering of
  unexposed windows (`5fe413a5`) are both in this build.
- **The seven failures are one check, on seven rips**: `expect-album-audit` in sections
  F, H, J, K1, K2, K3 and N (L717, L794, L897, L1041, L1068, L1095, L1260), each failing
  on the audit's `handshake_note` WARN, *"the ripper says it was built from an OPEN
  round: 'round 30 lap 11 OPEN, verdict OPEN -- NOT a released build'"*. That sentence is
  true and required: the fork's release plan for `.20` (§3) says every rip of a build cut
  inside an open round carries it, and our own verdict on the same binary is
  `unapproved`, the build an open round is reviewing, so the two witnesses the check
  compares agree. The check was written when every build a Full run reviewed had been
  released after its round closed (`.19`'s note says *closed*); O3 made the closing
  run's build a beta inside an open round, which this check could not pass. The sections
  are graded ARCHIVAL in advance, and **nothing here re-grades them: the run is
  `partial`.**
- **The unreachable step is E2** (L567), as designed: the BDR-209D is in the AccurateRip
  drive list, so turning the offset override off applies `+667` and rips instead of
  refusing; nothing was changed.
- **Cyanrip's `-f`, its first run on a drive** (section O, L1287-1289): `cyanrip -N -f`
  exited 0 and found **`+667`, confidence 14**, the offset section B set from three
  independent sources.
- **The cache probe, measured both ways** (section P): `.20`'s `-x -I` reports
  `128 to 255 sectors (… uncached read 251.0 ms, cached read 1.7 ms, 3 re-reads after a
  256-sector run took 32.6 ms or more)` (`round30oct06fulltranscript.txt:1230`), and
  `cd-paranoia -A` reports a 137-sector cache, defeated (`round30oct06fullcacheprobe.txt`).
  137 is inside `.20`'s bracket: the measurement the fork's open `cache-probe-calibration`
  item waited for.
- **Nine rips with a report, and cyanrip verified its own log for all nine**, the
  cancelled one included: its log ends `Rip completed:  no (interrupted by SIGTERM, 0 of
  14 tracks)` with its footer (`round30oct06fullcancelme.log:88`). **No `ERROR`,
  `CRITICAL` or traceback from the run's start to its end** in the three app logs that
  cover it. The cancel was measured a fourth time: `sigterm-world` reads *ONE SIGNAL*, the
  rescue's SIGTERM 5 s after Cancel being the first the reader acted on.
- **Each pass's exit and cyanrip's own record** (0.6.66b1's new fields): the whole-disc
  rip's album pass exited 0, its securing pass started and exited 0, and its
  `ripper_record` reads `state: read`, `interrupted: false`, no disagreement with ours.
- **The audio, and track 3 again.** In F (the whole-disc rip at full speed) AccurateRip
  verified 12 of 14 tracks; tracks 3 and 5 matched one frame only. The securing pass
  re-read both with `-Z 2`: track 5 converged on `E0036697`, EAC's, and replaced the
  first read; track 3 did not converge, and the first read, `329DC760`, was kept, a
  reading this drive has produced since round 7. F's whole-disc CTDB found no match
  (102 entries). In N (the whole-disc secure re-read) every track converged; track 3 on
  `2AC1F945`, confirmed across five re-reads, and N's whole-disc CTDB **matched one
  entry with confidence 1**, a single submission. **Neither F's nor N's track 3 is EAC's
  `59D352DD`**, which the 2026-09-30 run converged on: this drive has now converged on
  two different values for track 3, and AccurateRip holds no whole-track checksum for it
  that could choose between them. Every other track is identical in F and N and matches
  EAC. The reports and EAC-layout logs say what they saw: F's track 3 *"Copy NOT
  confirmed — re-reads did not converge"*, N's *"Copy OK"*. **Nothing here is a defect
  in `.20` or in 0.6.66b1**: it is the disc. Two things of ours are found by it and
  recorded in `TASKS.md`: F's headline verdict groups track 3 (re-reads did not agree)
  with track 5 (did) as "only one frame matched", and its disc-level health line says
  *No errors occurred* (our lap 8's round-31 item for that line).

### The files

| our file | tarball member | sha256/16 | bytes |
|---|---|---|---|
| `round30oct06fullwholedisceac.log` | `album/full acceptance_ angle_bracket 20261006t01__terpus-fork-g5704062/full acceptance∶ angle‹bracket 20261006t015821 platterpus-fork-g5704062 (EAC-compatible).log` | `e8254482922bc8e0` | 9,750 |
| `round30oct06fullwholedisc.cue` | `album/full acceptance_ angle_bracket 20261006t01__terpus-fork-g5704062/full acceptance∶ angle‹bracket 20261006t015821 platterpus-fork-g5704062.cue` | `6ce522b261e613bb` | 3,149 |
| `round30oct06fullwholedisc.log` | `album/full acceptance_ angle_bracket 20261006t01__terpus-fork-g5704062/full acceptance∶ angle‹bracket 20261006t015821 platterpus-fork-g5704062.log` | `4b183838983e02d3` | 40,081 |
| `round30oct06fullwholediscaddendum.txt` | `album/full acceptance_ angle_bracket 20261006t01__terpus-fork-g5704062/full acceptance∶ angle‹bracket 20261006t015821 platterpus-fork-g5704062.platterpus-addendum.txt` | `0ad4bcfa7934522d` | 1,769 |
| `round30oct06fullwholediscsecuringpass.txt` | `album/full acceptance_ angle_bracket 20261006t01__terpus-fork-g5704062/full acceptance∶ angle‹bracket 20261006t015821 platterpus-fork-g5704062.platterpus-securing-pass.txt` | `f454365628076320` | 10,810 |
| `round30oct06fullwholediscreport.json` | `album/full acceptance_ angle_bracket 20261006t01__terpus-fork-g5704062/full acceptance∶ angle‹bracket 20261006t015821 platterpus-fork-g5704062.platterpus.json` | `6eb384764abf91eb` | 6,184,183 |
| `round30oct06fulloverwriteeac.log` | `album/full acceptance_ angle_bracket 20261006t01__us-fork-g5704062 _2_/full acceptance∶ angle‹bracket 20261006t015821 platterpus-fork-g5704062 (EAC-compatible).log` | `c90bac32115d0279` | 3,484 |
| `round30oct06fulloverwrite.cue` | `album/full acceptance_ angle_bracket 20261006t01__us-fork-g5704062 _2_/full acceptance∶ angle‹bracket 20261006t015821 platterpus-fork-g5704062.cue` | `c2723104b7d2ee6b` | 795 |
| `round30oct06fulloverwrite.log` | `album/full acceptance_ angle_bracket 20261006t01__us-fork-g5704062 _2_/full acceptance∶ angle‹bracket 20261006t015821 platterpus-fork-g5704062.log` | `819ac7fef67aa828` | 9,523 |
| `round30oct06fulloverwritereport.json` | `album/full acceptance_ angle_bracket 20261006t01__us-fork-g5704062 _2_/full acceptance∶ angle‹bracket 20261006t015821 platterpus-fork-g5704062.platterpus.json` | `77f038790396866e` | 500,751 |
| `round30oct06fullaftercanceleac.log` | `album/after cancel 20261006t015821 platterpus-fork-g5704062/after cancel 20261006t015821 platterpus-fork-g5704062 (EAC-compatible).log` | `f3a4f0159da80f71` | 3,355 |
| `round30oct06fullaftercancel.cue` | `album/after cancel 20261006t015821 platterpus-fork-g5704062/after cancel 20261006t015821 platterpus-fork-g5704062.cue` | `fe5e8021492f80d0` | 685 |
| `round30oct06fullaftercancel.log` | `album/after cancel 20261006t015821 platterpus-fork-g5704062/after cancel 20261006t015821 platterpus-fork-g5704062.log` | `e12708d39610d868` | 9,075 |
| `round30oct06fullaftercancelreport.json` | `album/after cancel 20261006t015821 platterpus-fork-g5704062/after cancel 20261006t015821 platterpus-fork-g5704062.platterpus.json` | `e9a6d0309a83108c` | 506,517 |
| `round30oct06fullcancelmeeac.log` | `album/cancel me 20261006t015821 platterpus-fork-g5704062/cancel me 20261006t015821 platterpus-fork-g5704062 (EAC-compatible).log` | `96aff69e1fdd4ace` | 2,590 |
| `round30oct06fullcancelme.cue` | `album/cancel me 20261006t015821 platterpus-fork-g5704062/cancel me 20261006t015821 platterpus-fork-g5704062.cue` | `99a19ae8af37408e` | 372 |
| `round30oct06fullcancelme.log` | `album/cancel me 20261006t015821 platterpus-fork-g5704062/cancel me 20261006t015821 platterpus-fork-g5704062.log` | `4e45b19f90bfeb86` | 4,650 |
| `round30oct06fullcancelmereport.json` | `album/cancel me 20261006t015821 platterpus-fork-g5704062/cancel me 20261006t015821 platterpus-fork-g5704062.platterpus.json` | `bc5733c7d95fb913` | 199,329 |
| `round30oct06fullderivedmp3eac.log` | `album/derived mp3 20261006t015821 platterpus-fork-g5704062/derived mp3 20261006t015821 platterpus-fork-g5704062 (EAC-compatible).log` | `a159cf46c97b3139` | 3,392 |
| `round30oct06fullderivedmp3.cue` | `album/derived mp3 20261006t015821 platterpus-fork-g5704062/derived mp3 20261006t015821 platterpus-fork-g5704062.cue` | `1b0f28dd34086edd` | 684 |
| `round30oct06fullderivedmp3.log` | `album/derived mp3 20261006t015821 platterpus-fork-g5704062/derived mp3 20261006t015821 platterpus-fork-g5704062.log` | `629a0b8ceded46f7` | 9,069 |
| `round30oct06fullderivedmp3report.json` | `album/derived mp3 20261006t015821 platterpus-fork-g5704062/derived mp3 20261006t015821 platterpus-fork-g5704062.platterpus.json` | `bcca9be4c4559ff5` | 520,611 |
| `round30oct06fullderivedwavpackeac.log` | `album/derived wavpack 20261006t015821 platterpus-fork-g5704062/derived wavpack 20261006t015821 platterpus-fork-g5704062 (EAC-compatible).log` | `e31ae84960d28767` | 3,404 |
| `round30oct06fullderivedwavpack.cue` | `album/derived wavpack 20261006t015821 platterpus-fork-g5704062/derived wavpack 20261006t015821 platterpus-fork-g5704062.cue` | `aba766a258ed2ebe` | 688 |
| `round30oct06fullderivedwavpack.log` | `album/derived wavpack 20261006t015821 platterpus-fork-g5704062/derived wavpack 20261006t015821 platterpus-fork-g5704062.log` | `93ae806eb567d3a0` | 9,093 |
| `round30oct06fullderivedwavpackreport.json` | `album/derived wavpack 20261006t015821 platterpus-fork-g5704062/derived wavpack 20261006t015821 platterpus-fork-g5704062.platterpus.json` | `170403936a5d3bdf` | 527,834 |
| `round30oct06fullderivedwaveac.log` | `album/derived wav 20261006t015821 platterpus-fork-g5704062/derived wav 20261006t015821 platterpus-fork-g5704062 (EAC-compatible).log` | `d5fe35e570ac2dc7` | 3,392 |
| `round30oct06fullderivedwav.cue` | `album/derived wav 20261006t015821 platterpus-fork-g5704062/derived wav 20261006t015821 platterpus-fork-g5704062.cue` | `8dab2ea567c2d11f` | 684 |
| `round30oct06fullderivedwav.log` | `album/derived wav 20261006t015821 platterpus-fork-g5704062/derived wav 20261006t015821 platterpus-fork-g5704062.log` | `ae8a7bc08073f9ad` | 9,069 |
| `round30oct06fullderivedwavreport.json` | `album/derived wav 20261006t015821 platterpus-fork-g5704062/derived wav 20261006t015821 platterpus-fork-g5704062.platterpus.json` | `b622df51e8a63269` | 536,535 |
| `round30oct06fullsecurerereadeac.log` | `album/secure reread 20261006t015821 platterpus-fork-g5704062/secure reread 20261006t015821 platterpus-fork-g5704062 (EAC-compatible).log` | `70a8299b24fee00e` | 10,196 |
| `round30oct06fullsecurereread.cue` | `album/secure reread 20261006t015821 platterpus-fork-g5704062/secure reread 20261006t015821 platterpus-fork-g5704062.cue` | `4725bf2c776a40fd` | 2,956 |
| `round30oct06fullsecurereread.log` | `album/secure reread 20261006t015821 platterpus-fork-g5704062/secure reread 20261006t015821 platterpus-fork-g5704062.log` | `edc3cc68afc60388` | 43,440 |
| `round30oct06fullsecurerereadaddendum.txt` | `album/secure reread 20261006t015821 platterpus-fork-g5704062/secure reread 20261006t015821 platterpus-fork-g5704062.platterpus-addendum.txt` | `4a991283b101496a` | 2,380 |
| `round30oct06fullsecurerereadsecuringpass.txt` | `album/secure reread 20261006t015821 platterpus-fork-g5704062/secure reread 20261006t015821 platterpus-fork-g5704062.platterpus-securing-pass.txt` | `ab710c853d33bcea` | 10,355 |
| `round30oct06fullsecurerereadreport.json` | `album/secure reread 20261006t015821 platterpus-fork-g5704062/secure reread 20261006t015821 platterpus-fork-g5704062.platterpus.json` | `96e7a9a99f0ef769` | 6,058,016 |
| `round30oct06fullpermutationseac.log` | `album/permutations 20261006t015821 platterpus-fork-g5704062/permutations 20261006t015821 platterpus-fork-g5704062 (EAC-compatible).log` | `6add6091cce281f4` | 2,909 |
| `round30oct06fullpermutations.cue` | `album/permutations 20261006t015821 platterpus-fork-g5704062/permutations 20261006t015821 platterpus-fork-g5704062.cue` | `b3323e375ca4a24b` | 491 |
| `round30oct06fullpermutations.log` | `album/permutations 20261006t015821 platterpus-fork-g5704062/permutations 20261006t015821 platterpus-fork-g5704062.log` | `4eada00546804c2d` | 6,626 |
| `round30oct06fullpermutationsreport.json` | `album/permutations 20261006t015821 platterpus-fork-g5704062/permutations 20261006t015821 platterpus-fork-g5704062.platterpus.json` | `349aec1c896b9636` | 320,753 |
| `round30oct06fulldeemphoff.cue` | `album/r16deemphoff/Unknown disc (PNTI).cue` | `801640a40fd2ba0a` | 262 |
| `round30oct06fulldeemphoff.log` | `album/r16deemphoff/Unknown disc (PNTI).log` | `d3473afd286c6bf1` | 4,694 |
| `round30oct06fulldeemphon.cue` | `album/r16deemphon/Unknown disc (PNTI).cue` | `801640a40fd2ba0a` | 262 |
| `round30oct06fulldeemphon.log` | `album/r16deemphon/Unknown disc (PNTI).log` | `fea0dbef017ff680` | 4,766 |
| `round30oct06fullcomponents.json` | `COMPONENTS.json` | `3a9da3bc6df12fad` | 1,558 |
| `round30oct06fulldiagnostics.txt` | `DIAGNOSTICS.txt` | `89ae9d1f00f3b393` | 6,152 |
| `round30oct06fullmanifest.txt` | `MANIFEST.txt` | `f021d2e7b2fba87b` | 29,222 |
| `round30oct06fullsettings.json` | `SETTINGS.json` | `b144137c552c9db1` | 2,682 |
| `round30oct06fullsources.txt` | `SOURCES.txt` | `ace041634a5952a2` | 2,455 |
| `round30oct06fullplatterpusapplog.txt` | `session/artifacts/02platterpus/log.txt` | `7a1ea340c179f5f4` | 8,196,312 |
| `round30oct06fullplatterpusapplog1.txt` | `session/zz-applog-rotations/03platterpus/log.txt.1` | `48cc38e400ca22ed` | 8,388,506 |
| `round30oct06fullplatterpusapplog2.txt` | `session/zz-applog-rotations/04platterpus/log.txt.2` | `43897f0e5d176c4b` | 8,388,528 |
| `round30oct06fullconfig.toml` | `session/artifacts/12platterpus/config.toml` | `b8ae1bfdc7ac4030` | 1,141 |
| `round30oct06fullscriptreport.json` | `session/run/report.json` | `6f245fb7444ff7e4` | 319,172 |
| `round30oct06fulltranscript.txt` | `session/run/transcript.txt` | `9efc65c17a20de11` | 133,024 |
| `round30oct06fullcacheprobe.txt` | `session/run/cacheprobe1348.txt` | `95e61b0f2170be3f` | 2,000 |
| `round30oct06fullrigcheckmanifest.txt` | `session/run/rig-check/MANIFEST.txt` | `6c223988db21e658` | 15,911 |
| `round30oct06fullrigcheckargvprobe.json` | `session/run/rig-check/argv-probe.json` | `ffef720d652932b2` | 1,635 |
| `round30oct06fullrigcheckargvprobeoutput.txt` | `session/run/rig-check/argv-probe-output.txt` | `f8874e9eb888ae4e` | 489 |
| `round30oct06fullrigcheckripperversion.txt` | `session/run/rig-check/ripper-version.txt` | `d7efcb717187db0a` | 58 |
| `round30oct06fulltags0720.txt` | `session/run/tags0720.txt` | `81f135e841afe237` | 847 |
| `round30oct06fulltags0796.txt` | `session/run/tags0796.txt` | `37f9e4be04c51320` | 895 |
| `round30oct06fulltags0900.txt` | `session/run/tags0900.txt` | `49516fccca5693ec` | 807 |
| `round30oct06fulltags1044.txt` | `session/run/tags1044.txt` | `02a8d6463f9c6e4e` | 806 |
| `round30oct06fulltags1071.txt` | `session/run/tags1071.txt` | `45a55032b0b0a712` | 767 |
| `round30oct06fulltags1098.txt` | `session/run/tags1098.txt` | `e07f87c868186775` | 806 |
| `round30oct06fulltags1263.txt` | `session/run/tags1263.txt` | `835a61ea0ec2e977` | 808 |
| `round30oct06fulljrecord20261006t015852z.json` | `ripperdiagnostics/cyanrip-diagnostics-20261006T015852Z.json` | `29710741e72e4d22` | 47,347 |
| `round30oct06fulljrecord20261006t032722z.json` | `ripperdiagnostics/cyanrip-diagnostics-20261006T032722Z.json` | `7f745f4cdc813b37` | 14,757 |
| `round30oct06fulljrecord20261006t033311z.json` | `ripperdiagnostics/cyanrip-diagnostics-20261006T033311Z.json` | `4834026966a7ed7d` | 9,640 |
| `round30oct06fulljrecord20261006t033707z.json` | `ripperdiagnostics/cyanrip-diagnostics-20261006T033707Z.json` | `6318cc4b63385a66` | 14,073 |
| `round30oct06fulljrecord20261006t034259z.json` | `ripperdiagnostics/cyanrip-diagnostics-20261006T034259Z.json` | `5ce49f1dd66fc741` | 11,449 |
| `round30oct06fulljrecord20261006t034604z.json` | `ripperdiagnostics/cyanrip-diagnostics-20261006T034604Z.json` | `2beafb93a4d8f410` | 14,066 |
| `round30oct06fulljrecord20261006t035150z.json` | `ripperdiagnostics/cyanrip-diagnostics-20261006T035150Z.json` | `fd4ff4c8a7246f75` | 14,094 |
| `round30oct06fulljrecord20261006t035731z.json` | `ripperdiagnostics/cyanrip-diagnostics-20261006T035731Z.json` | `e08c044992ac97c5` | 14,066 |
| `round30oct06fulljrecord20261006t040325z.json` | `ripperdiagnostics/cyanrip-diagnostics-20261006T040325Z.json` | `9da01ffd8bebe52c` | 52,451 |
