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
