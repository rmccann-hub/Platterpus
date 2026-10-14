# Round 26 — the real test, 2026-09-24, `df91ae7` (`+platterpus.15`) on Platterpus 0.6.55

**Read the build, not the date.** Every rip log here opens
`cyanrip 0.9.4-rc2+platterpus.15 (platterpus-fork-gdf91ae7)`: the build round 26
reviews, installed through our 0.6.55 (`629ffa2`). This is round 26 lap 1 §0.1's
real test, and round 26 lap 1 requires it committed byte-identical to both trees.

**The bundle:** `platterpusbundle20260924t011421z.tar.gz`, sha256
`f14864171bdbb215e555e777d51fc8dcbd466b4306d56a9441d42640d01a4571`, 8,586,192 bytes,
handed over by the operator. The tarball itself is not committed. Its text members
are, **byte for byte**, and the table below names the member behind every file,
so each one can be checked with `sha256sum`.

**The fork filed the same set** at `cyanrip@9764970:docs/rig-2026-09-24-df91ae7/`.
Its 40 files have the **same git blob ids** as our copies, 40 of 40, so the two
trees hold identical bytes under different names. Ours use this directory's
naming convention (`docs/handshake/README.md` → *Artifacts*). **Six more are ours
alone:** the rip reports the fork left to us as Platterpus's artifact. Their
hashes match the ones the fork's README gives.

**Not filed:** the 229 screenshots, pictures of our own windows that neither
side's reading rests on. Every other member's content is here; where the tarball
holds two identical copies (the transcript, the script's report, the rig-check
files), one of them is filed. **No audio can be here**: the bundle's own allowlist refused
every audio file, and `MANIFEST` lists each refusal.

**What happened on this run** is in `docs/testing.md` §5.br and our round 26 lap 5.
In short: 258 of 261, and all three failures are section F's whole-disc rip,
killed when its container was stopped from outside both programs.

| our file | tarball member | fork's file (`cyanrip@9764970`) | sha256/16 |
|---|---|---|---|
| `round26aftercancel.cue` | `album/after cancel 20260924t011421 platterpus-fork-gdf91ae7/after cancel 20260924t011421 platterpus-fork-gdf91ae7.cue` | `rips/after-cancel.cue` | `ff371e962e84997e` |
| `round26aftercancel.log` | `album/after cancel 20260924t011421 platterpus-fork-gdf91ae7/after cancel 20260924t011421 platterpus-fork-gdf91ae7.log` | `rips/after-cancel.log` | `674aa2bac466cdc2` |
| `round26aftercanceleac.log` | `album/after cancel 20260924t011421 platterpus-fork-gdf91ae7/after cancel 20260924t011421 platterpus-fork-gdf91ae7 (EAC-compatible).log` | `rips/after-cancel.eac.log` | `719adbd2e142a4e7` |
| `round26aftercancelreport.json` | `album/after cancel 20260924t011421 platterpus-fork-gdf91ae7/after cancel 20260924t011421 platterpus-fork-gdf91ae7.platterpus.json` | `— (not filed by the fork)` | `ddfbde40d6bc8181` |
| `round26cancelme.cue` | `album/cancel me 20260924t011421 platterpus-fork-gdf91ae7/cancel me 20260924t011421 platterpus-fork-gdf91ae7.cue` | `rips/cancel-me.cue` | `ce3974ab860c42bf` |
| `round26cancelme.log` | `album/cancel me 20260924t011421 platterpus-fork-gdf91ae7/cancel me 20260924t011421 platterpus-fork-gdf91ae7.log` | `rips/cancel-me.log` | `b7fa5de1e258d067` |
| `round26cancelmeeac.log` | `album/cancel me 20260924t011421 platterpus-fork-gdf91ae7/cancel me 20260924t011421 platterpus-fork-gdf91ae7 (EAC-compatible).log` | `rips/cancel-me.eac.log` | `d6fb78f163e6f279` |
| `round26cancelmereport.json` | `album/cancel me 20260924t011421 platterpus-fork-gdf91ae7/cancel me 20260924t011421 platterpus-fork-gdf91ae7.platterpus.json` | `rips/cancel-me.platterpus.json` | `b2527907bfff80e5` |
| `round26config.toml` | `session/artifacts/04platterpus/config.toml` | `session/config.toml` | `34b64c61c3c6aeb2` |
| `round26derivedmp3.cue` | `album/derived mp3 20260924t011421 platterpus-fork-gdf91ae7/derived mp3 20260924t011421 platterpus-fork-gdf91ae7.cue` | `rips/derived-mp3.cue` | `e095deb7747a1fbf` |
| `round26derivedmp3.log` | `album/derived mp3 20260924t011421 platterpus-fork-gdf91ae7/derived mp3 20260924t011421 platterpus-fork-gdf91ae7.log` | `rips/derived-mp3.log` | `9c97868da2e9003e` |
| `round26derivedmp3eac.log` | `album/derived mp3 20260924t011421 platterpus-fork-gdf91ae7/derived mp3 20260924t011421 platterpus-fork-gdf91ae7 (EAC-compatible).log` | `rips/derived-mp3.eac.log` | `acfd65a853a09a4b` |
| `round26derivedmp3report.json` | `album/derived mp3 20260924t011421 platterpus-fork-gdf91ae7/derived mp3 20260924t011421 platterpus-fork-gdf91ae7.platterpus.json` | `— (not filed by the fork)` | `1a2a9c5fdf7858a9` |
| `round26derivedwav.cue` | `album/derived wav 20260924t011421 platterpus-fork-gdf91ae7/derived wav 20260924t011421 platterpus-fork-gdf91ae7.cue` | `rips/derived-wav.cue` | `1f70440531786975` |
| `round26derivedwav.log` | `album/derived wav 20260924t011421 platterpus-fork-gdf91ae7/derived wav 20260924t011421 platterpus-fork-gdf91ae7.log` | `rips/derived-wav.log` | `fe19bfad51858544` |
| `round26derivedwaveac.log` | `album/derived wav 20260924t011421 platterpus-fork-gdf91ae7/derived wav 20260924t011421 platterpus-fork-gdf91ae7 (EAC-compatible).log` | `rips/derived-wav.eac.log` | `b0c22232f54bfb86` |
| `round26derivedwavpack.cue` | `album/derived wavpack 20260924t011421 platterpus-fork-gdf91ae7/derived wavpack 20260924t011421 platterpus-fork-gdf91ae7.cue` | `rips/derived-wavpack.cue` | `4ad337b57eaaad93` |
| `round26derivedwavpack.log` | `album/derived wavpack 20260924t011421 platterpus-fork-gdf91ae7/derived wavpack 20260924t011421 platterpus-fork-gdf91ae7.log` | `rips/derived-wavpack.log` | `c77f39f3da9873e4` |
| `round26derivedwavpackeac.log` | `album/derived wavpack 20260924t011421 platterpus-fork-gdf91ae7/derived wavpack 20260924t011421 platterpus-fork-gdf91ae7 (EAC-compatible).log` | `rips/derived-wavpack.eac.log` | `96631db79e25ffdd` |
| `round26derivedwavpackreport.json` | `album/derived wavpack 20260924t011421 platterpus-fork-gdf91ae7/derived wavpack 20260924t011421 platterpus-fork-gdf91ae7.platterpus.json` | `— (not filed by the fork)` | `da914cdcac6f0125` |
| `round26derivedwavreport.json` | `album/derived wav 20260924t011421 platterpus-fork-gdf91ae7/derived wav 20260924t011421 platterpus-fork-gdf91ae7.platterpus.json` | `— (not filed by the fork)` | `17b2f1e57e09ef29` |
| `round26diagnostics.txt` | `DIAGNOSTICS.txt` | `session/DIAGNOSTICS.txt` | `9f265055321c6494` |
| `round26fullacceptanceanglebracket.cue` | `album/full acceptance_ angle_bracket 20260924t01__terpus-fork-gdf91ae7/full acceptance∶ angle‹bracket 20260924t011421 platterpus-fork-gdf91ae7.cue` | `rips/full-acceptance-angle-bracket.cue` | `ba68938e6114fa4f` |
| `round26fullacceptanceanglebracket.log` | `album/full acceptance_ angle_bracket 20260924t01__terpus-fork-gdf91ae7/full acceptance∶ angle‹bracket 20260924t011421 platterpus-fork-gdf91ae7.log` | `rips/full-acceptance-angle-bracket.log` | `57ed3e8fa8ed933c` |
| `round26fullacceptanceanglebracket2.cue` | `album/full acceptance_ angle_bracket 20260924t01__us-fork-gdf91ae7 _2_/full acceptance∶ angle‹bracket 20260924t011421 platterpus-fork-gdf91ae7.cue` | `rips/full-acceptance-angle-bracket-2.cue` | `fda974a5843166d5` |
| `round26fullacceptanceanglebracket2.log` | `album/full acceptance_ angle_bracket 20260924t01__us-fork-gdf91ae7 _2_/full acceptance∶ angle‹bracket 20260924t011421 platterpus-fork-gdf91ae7.log` | `rips/full-acceptance-angle-bracket-2.log` | `f896ea2c75c046d2` |
| `round26fullacceptanceanglebracket2eac.log` | `album/full acceptance_ angle_bracket 20260924t01__us-fork-gdf91ae7 _2_/full acceptance∶ angle‹bracket 20260924t011421 platterpus-fork-gdf91ae7 (EAC-compatible).log` | `rips/full-acceptance-angle-bracket-2.eac.log` | `c509c86851db3d6c` |
| `round26fullacceptanceanglebracket2report.json` | `album/full acceptance_ angle_bracket 20260924t01__us-fork-gdf91ae7 _2_/full acceptance∶ angle‹bracket 20260924t011421 platterpus-fork-gdf91ae7.platterpus.json` | `— (not filed by the fork)` | `b79bb91f0f71c013` |
| `round26fullacceptanceanglebracketeac.log` | `album/full acceptance_ angle_bracket 20260924t01__terpus-fork-gdf91ae7/full acceptance∶ angle‹bracket 20260924t011421 platterpus-fork-gdf91ae7 (EAC-compatible).log` | `rips/full-acceptance-angle-bracket.eac.log` | `c620c4624b2675d8` |
| `round26fullacceptanceanglebracketreport.json` | `album/full acceptance_ angle_bracket 20260924t01__terpus-fork-gdf91ae7/full acceptance∶ angle‹bracket 20260924t011421 platterpus-fork-gdf91ae7.platterpus.json` | `rips/full-acceptance-angle-bracket.platterpus.json` | `f65fcae8ef0dbc3c` |
| `round26manifest.txt` | `MANIFEST.txt` | `session/MANIFEST.txt` | `767a57ba2e95ae57` |
| `round26platterpusapplog.txt` | `session/artifacts/02platterpus/log.txt` | `session/platterpus-app-log.txt` | `0b2114dcfda84b68` |
| `round26platterpusapplog1.txt` | `session/zz-applog-rotations/03platterpus/log.txt.1` | `session/platterpus-app-log.1.txt` | `0b6b682097c164b8` |
| `round26rigcheckargvprobe.json` | `extra0520260924T011421_0000/rig-check/argv-probe.json` | `session/rig-check-argv-probe.json` | `0b01b7792a502319` |
| `round26rigcheckargvprobeoutput.txt` | `extra0520260924T011421_0000/rig-check/argv-probe-output.txt` | `session/rig-check-argv-probe-output.txt` | `9a6fb6404235f774` |
| `round26rigcheckmanifest.txt` | `extra0520260924T011421_0000/rig-check/MANIFEST.txt` | `session/rig-check-manifest.txt` | `e3f4d89b51fdd8bd` |
| `round26rigcheckripperversion.txt` | `extra0520260924T011421_0000/rig-check/ripper-version.txt` | `session/rig-check-ripper-version.txt` | `dc26ce8e22215bb0` |
| `round26scriptreport.json` | `extra0520260924T011421_0000/report.json` | `session/script-report.json` | `063fa6cecc16a169` |
| `round26securereread.cue` | `album/secure reread 20260924t011421 platterpus-fork-gdf91ae7/secure reread 20260924t011421 platterpus-fork-gdf91ae7.cue` | `rips/secure-reread.cue` | `83d9ef7f60926bcd` |
| `round26securereread.log` | `album/secure reread 20260924t011421 platterpus-fork-gdf91ae7/secure reread 20260924t011421 platterpus-fork-gdf91ae7.log` | `rips/secure-reread.log` | `195cdbe4935053c6` |
| `round26securerereadaddendum.txt` | `album/secure reread 20260924t011421 platterpus-fork-gdf91ae7/secure reread 20260924t011421 platterpus-fork-gdf91ae7.platterpus-addendum.txt` | `rips/secure-reread.platterpus-addendum.txt` | `97598b3b84e2fa38` |
| `round26securerereadeac.log` | `album/secure reread 20260924t011421 platterpus-fork-gdf91ae7/secure reread 20260924t011421 platterpus-fork-gdf91ae7 (EAC-compatible).log` | `rips/secure-reread.eac.log` | `dfa1a4c081f76e4b` |
| `round26securerereadreport.json` | `album/secure reread 20260924t011421 platterpus-fork-gdf91ae7/secure reread 20260924t011421 platterpus-fork-gdf91ae7.platterpus.json` | `— (not filed by the fork)` | `30601f0351de12a9` |
| `round26settings.json` | `SETTINGS.json` | `session/SETTINGS.json` | `1fca369bccdc1472` |
| `round26sources.txt` | `SOURCES.txt` | `session/SOURCES.txt` | `558ae12d64317d71` |
| `round26transcript.txt` | `session/transcript.txt` | `session/transcript.txt` | `7c36323513cd7ad4` |
