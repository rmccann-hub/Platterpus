# Round 28 — the Full run, 2026-09-28, `e0471f4` (`+platterpus.17`) on Platterpus 0.6.61

**Read the build, not the date.** Every rip log here opens
`cyanrip 0.9.4-rc2+platterpus.17 (platterpus-fork-ge0471f4)`: the build round 28
reviews, on our 0.6.61 (`59f4c00`), a release whose `PIN_UNDER_REVIEW` is `e0471f4`.
This is the run the fork's round 28 lap 1 S6 names, as that lap wrote it: *"the operator
runs your Full acceptance on the rig with `.17` installed through your app, from your
0.6.61 with `PIN_UNDER_REVIEW` `e0471f4`"*. Its script report says `run_size: full` and
`counts_as_evidence: true`. It started at 01:48 UTC, before our round 28 lap 6 (S36)
moved the run to 0.6.62 on the operator's override; which of the two readings round 28
closes on is the operator's to say.

**How `.17` got there is not in this bundle.** The app logs begin with the run's own
launch, so the install is in an earlier session. What the bundle does show: section A
asserted the build under review and passed on it (script report L274), the host export
and the in-container binary print the same banner (L288), and every rip log and the argv
probe (`"vcs": "e0471f4"`) name the build from the artifact's own content. No `-dirty`
marker appears anywhere.

**The bundle:** `platterpusbundle20260928t014808z.tar.gz`, sha256
`9182201706006872c79663d14a2396a46fd0793914da359a9b15fc8f33fee2c9`, 4,929,294 bytes,
handed over by the operator. The tarball is not committed; its text members are, **byte
for byte**, 46 files, named on round 27's pattern with a `round28full` prefix. The table
below names the member behind every file, so each can be checked with `sha256sum`.
**Not filed:** the 25 screenshots, and `session/transcript.txt`, byte-identical to
`session/run/transcript.txt` (`round28fulltranscript.txt`). No re-read addendum exists,
because no track was replaced. **No audio is here**: the bundle's allowlist refused every
audio file, and `MANIFEST` names each refusal.

**What it shows**, read from each rip's own records and not from the headline:

- **320 pass, 0 fail, 0 error, 0 skipped, 1 info** (the wrapper probe: the host export
  exited in 0.29 s). Wall clock 01:48 to 07:08 UTC.
- **Eight rips.** Two whole-disc: the first (`wholedisc`, section F) and the uniform
  secure re-read (`securereread`, section N). Six of tracks 1-2 or less: the overwrite
  (`overwrite`, a `(2)` folder), the cancel (`cancelme`), the rip after it
  (`aftercancel`), and MP3, WavPack and WAV (`derived*`). Every ripper log verifies
  against its own FUN512 footer; the app logs hold no `ERROR`, `CRITICAL` or traceback in
  137,189 lines.
- **Every rip is stamped `ripper_handshake_unapproved`**, with the detail naming `.17` as
  the pin of an open round. That is correct for the binary.
- **Twelve tracks read identically everywhere** they were read, and agree with the EAC
  baseline in `output_reference/EAC_flac/`. The derived formats were produced and
  checked: MP3 decodes cleanly, WavPack and WAV are bit-identical to their FLAC masters.
- **Track 5 never matched AccurateRip** in ten reads across both whole-disc rips (six
  `6902BCF0`, four `E0036697`; frame 450 matches every time), as it has not since round
  21. Both whole-disc rips ship `6902BCF0` and report 13 or 12 of 14 accordingly; CTDB
  answers `no_match` for both.

**What it found that is ours** (fixes and their tests are in the CHANGELOG and our round
28 lap 8):

- **The first whole-disc rip shipped an unverified track 3 after our re-read had a
  verified one.** Its first pass read `15D16895` (no whole-track AccurateRip match). Our
  automatic re-read ran `-Z 2 -l 3,5` and kept `59D352DD`, accurately ripped on
  AccurateRip v1 (confidence 128) and v2 (200), the same read the secure re-read rip
  converged on three times. The re-read had not converged, and our swap rule accepted a
  converged re-read only, so the verified copy was deleted with its temp folder and the
  status line said we *"kept the best read"*.
- **Five reports say the disc is not in CTDB.** The partial rips' CTDB lookup built its
  table of contents from the two files ripped, and CTDB has no two-track disc of that
  shape; the whole-disc rips found the same disc with 102 entries.
- **Section B's retry limit of 3 governed every secure re-read**, so `-Z 2`, which needs
  three identical reads, tolerated none that disagreed. The shipped default is 5.
- Smaller record defects: the cancelled rip's EAC-layout log says the track it was
  interrupted in was *"never extracted"*; the diagnostics file files every re-read that
  never converged at `info`, so its worst item is a deliberate negative test; and its
  approved-pair line names the running version beside an approval for another.

**What it found that is the ripper's**, for the fork: at the repeat limit cyanrip encodes
the last read, not a pair that agreed, and prints *"no matches found"* after a read that
matched (`cyanrip@faec4a8:src/cyanrip_main.c:1010-1022`; the same code is upstream's,
`src/cyanrip_main.c:859-866` on `master`); `Ripping errors: 0` sits over reads that
disagreed; and the cancelled rip's `Encoder errors: none; 1 track encoded`, which the
fork has already fixed for `.18`.

| our file | tarball member | sha256/16 | bytes |
|---|---|---|---|
| `round28fullaftercanceleac.log` | `album/after cancel 20260928t014808 platterpus-fork-ge0471f4/after cancel 20260928t014808 platterpus-fork-ge0471f4 (EAC-compatible).log` | `39b05ab5204f483d` | 3,343 |
| `round28fullaftercancel.cue` | `album/after cancel 20260928t014808 platterpus-fork-ge0471f4/after cancel 20260928t014808 platterpus-fork-ge0471f4.cue` | `1667aec9dc1824cf` | 685 |
| `round28fullaftercancel.log` | `album/after cancel 20260928t014808 platterpus-fork-ge0471f4/after cancel 20260928t014808 platterpus-fork-ge0471f4.log` | `caf917634210d7c1` | 9,198 |
| `round28fullaftercancelreport.json` | `album/after cancel 20260928t014808 platterpus-fork-ge0471f4/after cancel 20260928t014808 platterpus-fork-ge0471f4.platterpus.json` | `bcbfc0b8dc0dbe63` | 482,981 |
| `round28fullcancelmeeac.log` | `album/cancel me 20260928t014808 platterpus-fork-ge0471f4/cancel me 20260928t014808 platterpus-fork-ge0471f4 (EAC-compatible).log` | `88fe595fbaedc802` | 2,358 |
| `round28fullcancelme.cue` | `album/cancel me 20260928t014808 platterpus-fork-ge0471f4/cancel me 20260928t014808 platterpus-fork-ge0471f4.cue` | `6f1e5d9f45f6cc64` | 372 |
| `round28fullcancelme.log` | `album/cancel me 20260928t014808 platterpus-fork-ge0471f4/cancel me 20260928t014808 platterpus-fork-ge0471f4.log` | `39c1a87591502b27` | 4,727 |
| `round28fullcancelmereport.json` | `album/cancel me 20260928t014808 platterpus-fork-ge0471f4/cancel me 20260928t014808 platterpus-fork-ge0471f4.platterpus.json` | `8b9be599b6c29e61` | 157,721 |
| `round28fullderivedmp3eac.log` | `album/derived mp3 20260928t014808 platterpus-fork-ge0471f4/derived mp3 20260928t014808 platterpus-fork-ge0471f4 (EAC-compatible).log` | `561cf26691f6937b` | 3,380 |
| `round28fullderivedmp3.cue` | `album/derived mp3 20260928t014808 platterpus-fork-ge0471f4/derived mp3 20260928t014808 platterpus-fork-ge0471f4.cue` | `00c458d6f7b93d29` | 684 |
| `round28fullderivedmp3.log` | `album/derived mp3 20260928t014808 platterpus-fork-ge0471f4/derived mp3 20260928t014808 platterpus-fork-ge0471f4.log` | `1ff1451d3508d6e7` | 9,192 |
| `round28fullderivedmp3report.json` | `album/derived mp3 20260928t014808 platterpus-fork-ge0471f4/derived mp3 20260928t014808 platterpus-fork-ge0471f4.platterpus.json` | `5cc4b1dd6353437e` | 490,817 |
| `round28fullderivedwaveac.log` | `album/derived wav 20260928t014808 platterpus-fork-ge0471f4/derived wav 20260928t014808 platterpus-fork-ge0471f4 (EAC-compatible).log` | `0d401578dbcbaf39` | 3,380 |
| `round28fullderivedwav.cue` | `album/derived wav 20260928t014808 platterpus-fork-ge0471f4/derived wav 20260928t014808 platterpus-fork-ge0471f4.cue` | `5e3697189b6a9ecf` | 684 |
| `round28fullderivedwav.log` | `album/derived wav 20260928t014808 platterpus-fork-ge0471f4/derived wav 20260928t014808 platterpus-fork-ge0471f4.log` | `6aeb1ee37364c7ff` | 9,192 |
| `round28fullderivedwavreport.json` | `album/derived wav 20260928t014808 platterpus-fork-ge0471f4/derived wav 20260928t014808 platterpus-fork-ge0471f4.platterpus.json` | `02d70bc97139a508` | 489,122 |
| `round28fullderivedwavpackeac.log` | `album/derived wavpack 20260928t014808 platterpus-fork-ge0471f4/derived wavpack 20260928t014808 platterpus-fork-ge0471f4 (EAC-compatible).log` | `56c9411cdc5c067f` | 3,392 |
| `round28fullderivedwavpack.cue` | `album/derived wavpack 20260928t014808 platterpus-fork-ge0471f4/derived wavpack 20260928t014808 platterpus-fork-ge0471f4.cue` | `a1c51f2888a5aa52` | 688 |
| `round28fullderivedwavpack.log` | `album/derived wavpack 20260928t014808 platterpus-fork-ge0471f4/derived wavpack 20260928t014808 platterpus-fork-ge0471f4.log` | `9beee86cfe463d9c` | 9,216 |
| `round28fullderivedwavpackreport.json` | `album/derived wavpack 20260928t014808 platterpus-fork-ge0471f4/derived wavpack 20260928t014808 platterpus-fork-ge0471f4.platterpus.json` | `621ab6ff373b5837` | 480,143 |
| `round28fullwholedisceac.log` | `album/full acceptance_ angle_bracket 20260928t01__terpus-fork-ge0471f4/full acceptance∶ angle‹bracket 20260928t014808 platterpus-fork-ge0471f4 (EAC-compatible).log` | `f17f1370b7fc9ba9` | 9,824 |
| `round28fullwholedisc.cue` | `album/full acceptance_ angle_bracket 20260928t01__terpus-fork-ge0471f4/full acceptance∶ angle‹bracket 20260928t014808 platterpus-fork-ge0471f4.cue` | `23b598dea644b99e` | 3,149 |
| `round28fullwholedisc.log` | `album/full acceptance_ angle_bracket 20260928t01__terpus-fork-ge0471f4/full acceptance∶ angle‹bracket 20260928t014808 platterpus-fork-ge0471f4.log` | `d232789a048ad1f1` | 39,739 |
| `round28fullwholediscreport.json` | `album/full acceptance_ angle_bracket 20260928t01__terpus-fork-ge0471f4/full acceptance∶ angle‹bracket 20260928t014808 platterpus-fork-ge0471f4.platterpus.json` | `e20a930638619286` | 5,287,822 |
| `round28fulloverwriteeac.log` | `album/full acceptance_ angle_bracket 20260928t01__us-fork-ge0471f4 _2_/full acceptance∶ angle‹bracket 20260928t014808 platterpus-fork-ge0471f4 (EAC-compatible).log` | `9271542f9b28dbc8` | 3,446 |
| `round28fulloverwrite.cue` | `album/full acceptance_ angle_bracket 20260928t01__us-fork-ge0471f4 _2_/full acceptance∶ angle‹bracket 20260928t014808 platterpus-fork-ge0471f4.cue` | `80fcbf824b4232b9` | 747 |
| `round28fulloverwrite.log` | `album/full acceptance_ angle_bracket 20260928t01__us-fork-ge0471f4 _2_/full acceptance∶ angle‹bracket 20260928t014808 platterpus-fork-ge0471f4.log` | `4d5d831ca293b6dd` | 9,571 |
| `round28fulloverwritereport.json` | `album/full acceptance_ angle_bracket 20260928t01__us-fork-ge0471f4 _2_/full acceptance∶ angle‹bracket 20260928t014808 platterpus-fork-ge0471f4.platterpus.json` | `60193b367dee88c0` | 478,321 |
| `round28fullsecurerereadeac.log` | `album/secure reread 20260928t014808 platterpus-fork-ge0471f4/secure reread 20260928t014808 platterpus-fork-ge0471f4 (EAC-compatible).log` | `97e4b7f6a9cf2dd6` | 10,318 |
| `round28fullsecurereread.cue` | `album/secure reread 20260928t014808 platterpus-fork-ge0471f4/secure reread 20260928t014808 platterpus-fork-ge0471f4.cue` | `410acb43df5e027d` | 2,956 |
| `round28fullsecurereread.log` | `album/secure reread 20260928t014808 platterpus-fork-ge0471f4/secure reread 20260928t014808 platterpus-fork-ge0471f4.log` | `e92556714bab349c` | 42,622 |
| `round28fullsecurerereadreport.json` | `album/secure reread 20260928t014808 platterpus-fork-ge0471f4/secure reread 20260928t014808 platterpus-fork-ge0471f4.platterpus.json` | `82daae2c16c5e069` | 6,422,604 |
| `round28fullcomponents.json` | `COMPONENTS.json` | `b1dac34ee852afa9` | 1,339 |
| `round28fulldiagnostics.txt` | `DIAGNOSTICS.txt` | `89cf766eb198116c` | 5,089 |
| `round28fullmanifest.txt` | `MANIFEST.txt` | `41acb1bf99457fb6` | 23,303 |
| `round28fullsettings.json` | `SETTINGS.json` | `24f8e8f21c39d3bc` | 2,760 |
| `round28fullsources.txt` | `SOURCES.txt` | `ef1b6e798a7e3269` | 1,501 |
| `round28fullplatterpusapplog.txt` | `session/artifacts/02platterpus/log.txt` | `480509485c4c1c66` | 7,430,283 |
| `round28fullplatterpusapplog1.txt` | `session/zz-applog-rotations/03platterpus/log.txt.1` | `9c7ea4e71f0edd37` | 8,388,570 |
| `round28fullconfig.toml` | `session/artifacts/04platterpus/config.toml` | `8d816eea558fa8c8` | 1,141 |
| `round28fullscriptreport.json` | `session/run/report.json` | `b535c501200dbba4` | 201,431 |
| `round28fulltranscript.txt` | `session/run/transcript.txt` | `4dbda52984b68548` | 110,994 |
| `round28fullrigcheckmanifest.txt` | `session/run/rig-check/MANIFEST.txt` | `2e8efa53980d02ed` | 15,834 |
| `round28fullrigcheckargvprobe.json` | `session/run/rig-check/argv-probe.json` | `e1f5fd6fd7306ac5` | 1,628 |
| `round28fullrigcheckargvprobeoutput.txt` | `session/run/rig-check/argv-probe-output.txt` | `1676fdf993f40d47` | 484 |
| `round28fullrigcheckripperversion.txt` | `session/run/rig-check/ripper-version.txt` | `29b7ef415cd1bede` | 58 |

*Last updated for Platterpus v0.6.62.*
