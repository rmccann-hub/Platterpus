# Round 27 — the quick run, 2026-09-26, `221a1df` (`+platterpus.16`) on Platterpus 0.6.60

**Read the build, not the date.** The one rip log here opens
`cyanrip 0.9.4-rc2+platterpus.16 (platterpus-fork-g221a1df)`: the build round 27
reviews, installed through our 0.6.60 (`88c09dd`). This is the run that stands in for
round 27 lap 1 §0.1's Full acceptance, **by the operator's override of R1** (the fork's
round 27 lap 4 records it as `HANDSHAKE-OVERRIDE`). It is a **quick** run and says so
itself: its script report carries `counts_as_evidence: false`, and it is not evidence
for a version (KDD-35).

**The bundle:** `platterpusbundle20260926t000413z.tar.gz`, sha256
`827d43da95f4dfe150e70900b56d5e96163cff41f7a6e117819760970e9cc4e0`, 1,656,589 bytes,
handed over by the operator. The tarball itself is not committed. Its text members
are, **byte for byte**, and the table below names the member behind every file,
so each one can be checked with `sha256sum`.

**The fork filed the same set** at `cyanrip@29cae9e:docs/rig-2026-09-26-221a1df-quick/`.
Its 15 files have the **same git blob ids** as our copies, 15 of 15, so the two trees
hold identical bytes under different names. Ours use this directory's naming convention
(`docs/handshake/README.md` → *Artifacts*). Unlike round 26, the fork filed our rip
report too, so nothing here is ours alone.

**Not filed:** the 13 screenshots, pictures of our own windows that neither side's
reading rests on, and `session/transcript.txt`, which is byte-identical to
`session/run/transcript.txt` (filed as `round27transcript.txt`). **No EAC-compatible log
exists for this rip:** the script turns that export off for section K1 (step L223).
**No audio can be here**: the bundle's own allowlist refused every audio file, and
`MANIFEST` lists each refusal.

**What happened on this run** is in our round 27 lap 5 and `docs/session-log.md`
(2026-09-26). In short: 206 passed, 0 failed, 114 declined by the run size, one `info`.
The only rip, section K1, took tracks 1–2 and both are exact AccurateRip v1 and v2
matches. The run found three defects, all ours, all fixed before `main` saw them.
One of them is the run's own manifest line calling this complete run incomplete,
which the fork found independently in their lap 4 §E.

| our file | tarball member | fork's file (`cyanrip@29cae9e`) | sha256/16 |
|---|---|---|---|
| `round27derivedmp3.cue` | `album/derived mp3 20260926t000413 platterpus-fork-g221a1df.cue` | `rips/derived-mp3.cue` | `424befb1cd88a2eb` |
| `round27derivedmp3.log` | `album/derived mp3 20260926t000413 platterpus-fork-g221a1df.log` | `rips/derived-mp3.log` | `49f4b6ef41b1e1df` |
| `round27derivedmp3report.json` | `album/derived mp3 20260926t000413 platterpus-fork-g221a1df.platterpus.json` | `rips/derived-mp3.platterpus.json` | `be2cfa5db0bef61e` |
| `round27components.json` | `COMPONENTS.json` | `session/COMPONENTS.json` | `6d4c4dd66afa50fc` |
| `round27diagnostics.txt` | `DIAGNOSTICS.txt` | `session/DIAGNOSTICS.txt` | `66781958ada452cd` |
| `round27manifest.txt` | `MANIFEST.txt` | `session/MANIFEST.txt` | `82fdd94760d25c77` |
| `round27settings.json` | `SETTINGS.json` | `session/SETTINGS.json` | `c370dd3f5555dcb8` |
| `round27sources.txt` | `SOURCES.txt` | `session/SOURCES.txt` | `4dd4b28124a6981c` |
| `round27config.toml` | `session/artifacts/03platterpus/config.toml` | `session/config.toml` | `8d816eea558fa8c8` |
| `round27scriptreport.json` | `session/run/report.json` | `session/report.json` | `354ca837d0e6a1d7` |
| `round27rigcheckmanifest.txt` | `session/run/rig-check/MANIFEST.txt` | `session/rig-check-MANIFEST.txt` | `283f43dba4e69989` |
| `round27rigcheckargvprobeoutput.txt` | `session/run/rig-check/argv-probe-output.txt` | `session/rig-check-argv-probe-output.txt` | `dae8e715b1a6664c` |
| `round27rigcheckargvprobe.json` | `session/run/rig-check/argv-probe.json` | `session/rig-check-argv-probe.json` | `e7dc0ffbdb5cd222` |
| `round27rigcheckripperversion.txt` | `session/run/rig-check/ripper-version.txt` | `session/rig-check-ripper-version.txt` | `5f3153bbf48a5103` |
| `round27transcript.txt` | `session/run/transcript.txt` | `session/transcript.txt` | `c2525b537e13e0a7` |

---

## The Full run, 2026-09-26 04:13 UTC, on the same pair — filed as `round27full*`

**This is the run round 27 lap 1 §0.1 asked for, before the override replaced it
with the quick run.** Our **Full** acceptance, on `.16` (`221a1df`) installed through
our 0.6.60 (`88c09dd`), a release whose `PIN_UNDER_REVIEW` is `221a1df`. Its script
report says `run_size: full` and `counts_as_evidence: true`.

**The bundle:** `platterpusbundle20260926t041308z.tar.gz`, sha256
`7b6b45d38f1e723551fcbb1fe41262faa968abdddc4d475d903b39a1bada7ae8`, 4,826,147 bytes,
handed over by the operator. The tarball is not committed; its text members are,
**byte for byte**, 48 files, named on round 26's pattern with a
`round27full` prefix so they sit beside the quick run without colliding (the
round-8 precedent). **Not filed:** the 29 screenshots, and `session/transcript.txt`,
byte-identical to `session/run/transcript.txt` (`round27fulltranscript.txt`). **No
audio is here**: the bundle's allowlist refused every audio file.

**What it shows**, read from each rip's own report and not from the headline:

- **320 pass, 0 fail, 0 error, 0 skipped, 1 info** (the wrapper probe: the host
  export exited in 0.28 s).
- **Eight rips, and every log verifies against its own FUN512 checksum.** The app
  log has no `ERROR`, `CRITICAL` or traceback in 71,328 lines, and the rig check
  reports no failure.
- **The derived formats were produced and checked.** MP3, WAV and WavPack each
  report `derived: ran`, 2 of 2 checked, complete. This is the check the
  2026-09-15 run could not make (§5.bi).
- **The re-read replaced two misreads.** Track 1 in the MP3 rip and track 3 in the
  whole-disc rip first read as different audio: `D6EB57D9` and `1B28C061`, with
  only the frame-450 checksum matching. Each was re-read, replaced by a read
  matching AccurateRip v1 and v2, and recorded in an addendum. The re-read has
  been on by default since 0.6.57.
- **Both whole-disc rips**: 13 of 14 tracks exact, CTDB `match`. Track 5 matches on
  frame 450 only (`4CCBCF89`), as it has since round 21. The secure re-read ran
  every track: 65,364 reads against 21,678 for one pass.
- **Every rip is stamped `ripper_handshake_unapproved`.** That is correct for the
  binary: released 0.6.60 carries round 26's approval of `df91ae7`. Round 27's
  approval of `221a1df` ships in 0.6.61.

**What it found, and it is ours:** the report's note beside the one-frame count said
the ripper's tally *"does not agree with the tracks listed per track in this log"*.
The log and its tally agree; our re-read changed the count. Fixed, with a test that
reads `round27fullwholedisc.log` (`docs/session-log.md`, 2026-09-26).

| our file | tarball member | sha256/16 | bytes |
|---|---|---|---|
| `round27fullaftercanceleac.log` | `album/after cancel 20260926t041308 platterpus-fork-g221a1df/after cancel 20260926t041308 platterpus-fork-g221a1df (EAC-compatible).log` | `79d6e4f7bb31c896` | 3,343 |
| `round27fullaftercancel.cue` | `album/after cancel 20260926t041308 platterpus-fork-g221a1df/after cancel 20260926t041308 platterpus-fork-g221a1df.cue` | `7524d63aa5e236f1` | 685 |
| `round27fullaftercancel.log` | `album/after cancel 20260926t041308 platterpus-fork-g221a1df/after cancel 20260926t041308 platterpus-fork-g221a1df.log` | `fb4ae1299c480d55` | 9,198 |
| `round27fullaftercancelreport.json` | `album/after cancel 20260926t041308 platterpus-fork-g221a1df/after cancel 20260926t041308 platterpus-fork-g221a1df.platterpus.json` | `ad4989c0a59bbd9b` | 492,272 |
| `round27fullcancelmeeac.log` | `album/cancel me 20260926t041308 platterpus-fork-g221a1df/cancel me 20260926t041308 platterpus-fork-g221a1df (EAC-compatible).log` | `2d8de8441d0c11ef` | 2,358 |
| `round27fullcancelme.cue` | `album/cancel me 20260926t041308 platterpus-fork-g221a1df/cancel me 20260926t041308 platterpus-fork-g221a1df.cue` | `3b1d169a3fc7e0a4` | 372 |
| `round27fullcancelme.log` | `album/cancel me 20260926t041308 platterpus-fork-g221a1df/cancel me 20260926t041308 platterpus-fork-g221a1df.log` | `504dea64010bb6be` | 4,727 |
| `round27fullcancelmereport.json` | `album/cancel me 20260926t041308 platterpus-fork-g221a1df/cancel me 20260926t041308 platterpus-fork-g221a1df.platterpus.json` | `3432d387e8a2a431` | 167,119 |
| `round27fullderivedmp3eac.log` | `album/derived mp3 20260926t041308 platterpus-fork-g221a1df/derived mp3 20260926t041308 platterpus-fork-g221a1df (EAC-compatible).log` | `33d9d3ea7e5843b7` | 3,473 |
| `round27fullderivedmp3.cue` | `album/derived mp3 20260926t041308 platterpus-fork-g221a1df/derived mp3 20260926t041308 platterpus-fork-g221a1df.cue` | `391870630f661629` | 684 |
| `round27fullderivedmp3.log` | `album/derived mp3 20260926t041308 platterpus-fork-g221a1df/derived mp3 20260926t041308 platterpus-fork-g221a1df.log` | `716130fb3e1c0144` | 9,356 |
| `round27fullderivedmp3addendum.txt` | `album/derived mp3 20260926t041308 platterpus-fork-g221a1df/derived mp3 20260926t041308 platterpus-fork-g221a1df.platterpus-addendum.txt` | `bc66513987e182ed` | 1,585 |
| `round27fullderivedmp3report.json` | `album/derived mp3 20260926t041308 platterpus-fork-g221a1df/derived mp3 20260926t041308 platterpus-fork-g221a1df.platterpus.json` | `706107f582aaa04a` | 1,051,684 |
| `round27fullderivedwaveac.log` | `album/derived wav 20260926t041308 platterpus-fork-g221a1df/derived wav 20260926t041308 platterpus-fork-g221a1df (EAC-compatible).log` | `4d2370e73c1927b5` | 3,380 |
| `round27fullderivedwav.cue` | `album/derived wav 20260926t041308 platterpus-fork-g221a1df/derived wav 20260926t041308 platterpus-fork-g221a1df.cue` | `b656281a856eb63e` | 684 |
| `round27fullderivedwav.log` | `album/derived wav 20260926t041308 platterpus-fork-g221a1df/derived wav 20260926t041308 platterpus-fork-g221a1df.log` | `5a177d4c328a9800` | 9,192 |
| `round27fullderivedwavreport.json` | `album/derived wav 20260926t041308 platterpus-fork-g221a1df/derived wav 20260926t041308 platterpus-fork-g221a1df.platterpus.json` | `75e62c94d39c8ea6` | 505,703 |
| `round27fullderivedwavpackeac.log` | `album/derived wavpack 20260926t041308 platterpus-fork-g221a1df/derived wavpack 20260926t041308 platterpus-fork-g221a1df (EAC-compatible).log` | `c09fc9e74ce9c11a` | 3,392 |
| `round27fullderivedwavpack.cue` | `album/derived wavpack 20260926t041308 platterpus-fork-g221a1df/derived wavpack 20260926t041308 platterpus-fork-g221a1df.cue` | `b9ba7643d9ddd572` | 688 |
| `round27fullderivedwavpack.log` | `album/derived wavpack 20260926t041308 platterpus-fork-g221a1df/derived wavpack 20260926t041308 platterpus-fork-g221a1df.log` | `a7b3bb6bda0737b2` | 9,256 |
| `round27fullderivedwavpackreport.json` | `album/derived wavpack 20260926t041308 platterpus-fork-g221a1df/derived wavpack 20260926t041308 platterpus-fork-g221a1df.platterpus.json` | `8b45e667d7f41cc3` | 496,708 |
| `round27fullwholedisceac.log` | `album/full acceptance_ angle_bracket 20260926t04__terpus-fork-g221a1df/full acceptance∶ angle‹bracket 20260926t041308 platterpus-fork-g221a1df (EAC-compatible).log` | `192e5073a2f2ab1b` | 9,686 |
| `round27fullwholedisc.cue` | `album/full acceptance_ angle_bracket 20260926t04__terpus-fork-g221a1df/full acceptance∶ angle‹bracket 20260926t041308 platterpus-fork-g221a1df.cue` | `fa480d3218552d5a` | 3,149 |
| `round27fullwholedisc.log` | `album/full acceptance_ angle_bracket 20260926t04__terpus-fork-g221a1df/full acceptance∶ angle‹bracket 20260926t041308 platterpus-fork-g221a1df.log` | `8dfdb149b68f1ad5` | 39,694 |
| `round27fullwholediscaddendum.txt` | `album/full acceptance_ angle_bracket 20260926t04__terpus-fork-g221a1df/full acceptance∶ angle‹bracket 20260926t041308 platterpus-fork-g221a1df.platterpus-addendum.txt` | `5723b9773a5e2a36` | 1,631 |
| `round27fullwholediscreport.json` | `album/full acceptance_ angle_bracket 20260926t04__terpus-fork-g221a1df/full acceptance∶ angle‹bracket 20260926t041308 platterpus-fork-g221a1df.platterpus.json` | `ed747d731ac06a57` | 5,297,141 |
| `round27fulloverwriteeac.log` | `album/full acceptance_ angle_bracket 20260926t04__us-fork-g221a1df _2_/full acceptance∶ angle‹bracket 20260926t041308 platterpus-fork-g221a1df (EAC-compatible).log` | `3518a96998dbd12a` | 3,446 |
| `round27fulloverwrite.cue` | `album/full acceptance_ angle_bracket 20260926t04__us-fork-g221a1df _2_/full acceptance∶ angle‹bracket 20260926t041308 platterpus-fork-g221a1df.cue` | `0b7f208bb7d011fb` | 747 |
| `round27fulloverwrite.log` | `album/full acceptance_ angle_bracket 20260926t04__us-fork-g221a1df _2_/full acceptance∶ angle‹bracket 20260926t041308 platterpus-fork-g221a1df.log` | `6499d7ae481f2432` | 9,613 |
| `round27fulloverwritereport.json` | `album/full acceptance_ angle_bracket 20260926t04__us-fork-g221a1df _2_/full acceptance∶ angle‹bracket 20260926t041308 platterpus-fork-g221a1df.platterpus.json` | `326ed50c4c5b55c1` | 487,510 |
| `round27fullsecurerereadeac.log` | `album/secure reread 20260926t041308 platterpus-fork-g221a1df/secure reread 20260926t041308 platterpus-fork-g221a1df (EAC-compatible).log` | `f6f025170bc0bdc1` | 10,326 |
| `round27fullsecurereread.cue` | `album/secure reread 20260926t041308 platterpus-fork-g221a1df/secure reread 20260926t041308 platterpus-fork-g221a1df.cue` | `093eeb42fdf2a678` | 2,956 |
| `round27fullsecurereread.log` | `album/secure reread 20260926t041308 platterpus-fork-g221a1df/secure reread 20260926t041308 platterpus-fork-g221a1df.log` | `dcefc5ef108cb7a9` | 42,633 |
| `round27fullsecurerereadreport.json` | `album/secure reread 20260926t041308 platterpus-fork-g221a1df/secure reread 20260926t041308 platterpus-fork-g221a1df.platterpus.json` | `67af4d42584c0c36` | 6,470,344 |
| `round27fullplatterpusapplog.txt` | `session/artifacts/02platterpus/log.txt` | `2aabc38707c9028f` | 8,050,002 |
| `round27fullplatterpusapplog1.txt` | `session/zz-applog-rotations/03platterpus/log.txt.1` | `9acf533d184c6871` | 8,388,569 |
| `round27fullconfig.toml` | `session/artifacts/04platterpus/config.toml` | `8d816eea558fa8c8` | 1,141 |
| `round27fullscriptreport.json` | `session/run/report.json` | `78d43ff868cf6782` | 204,195 |
| `round27fulltranscript.txt` | `session/run/transcript.txt` | `3bd5b4e8ad559f3d` | 113,990 |
| `round27fullrigcheckmanifest.txt` | `session/run/rig-check/MANIFEST.txt` | `f7d3825d16c978a8` | 15,846 |
| `round27fullrigcheckargvprobe.json` | `session/run/rig-check/argv-probe.json` | `bd47e9ecbed497a6` | 1,628 |
| `round27fullrigcheckargvprobeoutput.txt` | `session/run/rig-check/argv-probe-output.txt` | `a346bf0b45de8dec` | 484 |
| `round27fullrigcheckripperversion.txt` | `session/run/rig-check/ripper-version.txt` | `5f3153bbf48a5103` | 58 |
| `round27fullcomponents.json` | `COMPONENTS.json` | `ede8e403b686da4c` | 1,339 |
| `round27fulldiagnostics.txt` | `DIAGNOSTICS.txt` | `4e26fd4fc2e1cfc3` | 5,280 |
| `round27fullsettings.json` | `SETTINGS.json` | `4fac3a7c2a853983` | 2,760 |
| `round27fullsources.txt` | `SOURCES.txt` | `76f766264a1f0ad3` | 1,501 |
| `round27fullmanifest.txt` | `MANIFEST.txt` | `915ce6688e7ddbc5` | 23,640 |
