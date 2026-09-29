# Round 29 — the Full run, 2026-09-28 22:33 UTC, `51cc789` (`+platterpus.18`) on Platterpus 0.6.63

**Read the build, not the date.** Every rip log here opens
`cyanrip 0.9.4-rc2+platterpus.18 (platterpus-fork-g51cc789)`, the build round 29
reviews, on our 0.6.63 (`d226c03`), whose `PIN_UNDER_REVIEW` is `51cc789` and whose
`FORK_PIN` is still round 28's `e0471f4`. This is the run the fork's round 29 lap 1 S6
names: *"the operator runs your Full acceptance on the rig with `.18` installed through
your app, from a release of yours whose `PIN_UNDER_REVIEW` is `51cc789`"*. Its script
report says `run_size: full` and `counts_as_evidence: true`. It began at 22:33:56 UTC and
its last line is at 03:55 UTC (the app log's 23:55 local, when the run restored the
operator's settings).

**How `.18` got there is in this bundle.** The rotated app log
(`round29fullplatterpusapplog1.txt`) begins with the Quick run the operator started at
18:13 local, which stopped at section A because `.17` was still installed (line 82).
At 18:32 the operator ran the ripper update from Setup & Updates (line 145), which
installed `51cc789` (line 147): it built from a clean tree at
`51cc7892888bb3eaae20caf5cfbea46ec1aa4d8e` with `-Ddeclare_released=true`, and both
the built and the installed binary identify as `platterpus-fork-g51cc789` (lines 286
and 304). The Full run began a minute later. The host export's banner
(`round29fullrigcheckripperversion.txt`), every rip log's first line and the argv probe
(`"vcs": "51cc789"`) name the same build from the artifact's own content. No
banner carries a `-dirty` marker; the one `-dirty` in the bundle is the install
script's own check for it (`round29fullplatterpusapplog1.txt:190`).

**The bundle:** `platterpusbundle20260928t223356z.tar.gz`, sha256
`43a837415e51157b4a8464d2601c6b38453a52eddf818684c275acb21a4237a6`, 4,293,783 bytes,
handed over by the operator. The tarball is not committed; its 51 text members are, **byte
for byte**, with a `round29full` prefix, one per row of the table below, which names the
member behind every file so each can be checked with `sha256sum`. **Not filed:** the 20
screenshots, and `session/transcript.txt`, identical to `session/run/transcript.txt`
(`round29fulltranscript.txt`). **No audio is here**: the bundle's allowlist refused all 47
audio files and two cover images, and `MANIFEST` names each refusal.

## What it shows

Read from each rip's own records, not from the headline.

- **320 pass, 3 fail, 0 error, 0 skipped, 1 info** (the wrapper probe: the host export
  exited in 0.27 s). The run reached its last step.
- **The three failures are screenshot steps, and nothing else failed.** L676
  `afteroverwrite` (section H), L724 `aftercancel` (section J) and L850 `afterwav` (section
  K3) each say *"examined 12 window(s) and none was on screen"*. The main window and the
  script console were `visible=True` with `exposed=False`: Qt had the windows, and the
  display was not showing them. Screenshots at 86, 103, 110 and 313 minutes into the run
  passed; these three were at 94, 96 and 124 minutes (sums of the report's step times).
  The rips beside them are complete. **The cause is not established.** Our reading is that
  the display blanked or locked: the run's sleep lock holds `idle:sleep:handle-lid-switch`,
  which stops the machine sleeping and does not, on its own evidence, stop the screen
  turning off. That is a hypothesis for a hardware run to test, not a finding. The hidden
  `cyanrip update` message box in the list is the beta offer the operator accepted before
  the run.
- **Ten rips.** Two whole-disc: the first (`wholedisc`, section F, `-r 5`) and the
  uniform secure re-read (`securereread`, section N, `-r 5 -Z 2`). Six of tracks 1 and 2
  or less: the overwrite (`overwrite`, a `(2)` folder), the cancel (`cancelme`), the rip
  after it (`aftercancel`), and MP3, WavPack and WAV (`derived*`). Two de-emphasis rips of
  track 1 (`deemphon` with `-H -E`, `deemphoff` with `-H -W`, section P3). The ripper
  verified its own log for each of the eight rips with a report
  (`ripper_log_verification: verified`); the two de-emphasis rips have no report, and
  nothing in the bundle verified theirs. The app logs hold no `ERROR`, `CRITICAL` or
  traceback in the 137,646 lines from the run's launch.
- **Every rip is stamped `ripper_handshake_unapproved`**, correctly: 0.6.63's approval
  record is round 28's `e0471f4`, and `.18` is the build under review. Every report
  carries the same single diagnostics warning, `deps.command_failed`: *"cyanrip exited
  -9"* for `cyanrip -I -N -d /dev/sr0` at 22:13 UTC, twenty minutes before the run. **It is
  not the ripper's failure; it is ours.** The operator pressed Rescan while that disc
  probe was still waiting on the starting container, and the rescan killed it
  (`round29fullplatterpusapplog1.txt:20-36`). The warning's scope is *"process session
  (not only this rip)"*, so every rip of that app session carried it (below).
- **The whole-disc rip matches the EAC baseline on 13 of 14 tracks**
  (`output_reference/EAC_flac/`), track 5 at `E0036697` among them. Track 3 is the
  exception: `3D8FCF0C`, where EAC has `59D352DD`. Our automatic re-read of tracks 3 and 5
  converged on the first pass's CRC each time (3 reads), so the addendum records both first
  reads as CONFIRMED, not replaced. Both match AccurateRip on frame 450 only. The verdict
  says so (*"12 of 14 … only one frame matched"*), and CTDB finds no match (102 entries).
  `3D8FCF0C` is not new: round 27's whole-disc rip on 2026-09-26 read the same value
  (`../artifactsround27/round27fullwholedisc.log`). So track 3, like track 5, has a second
  reading that is stable within a pass.
- **The secure re-read rip converged on every track.** Tracks 1, 3 and 4 took 4 reads,
  and the rest 3. Under 0.6.62's `-r 3`, those three could not have converged; 0.6.63's
  `-r 5` is what let them. Track 3 converged on `59D352DD`, EAC's value. Track 5 converged
  on `6902BCF0`, the other reading, so this rip is 13 of 14 accurate and CTDB finds no
  match. The report warns `heavy_reread` for tracks 1, 3 and 4.
- **Tracks 1 and 2 match EAC in all five partial rips that finished**, and each says
  *"Bit-perfect"*.
- **De-emphasis (P3).** With de-emphasis forced (`-H -E`), track 1 reads `B0D122E7`,
  EAC's value, AccurateRip-accurate. The control (`-H -W`) reads `64CA69D1`, which matches
  AccurateRip on frame 450 only: a misread of track 1, which has read differently before
  (`0E91CD1A`, `../artifactsround27/round27fullderivedmp3addendum.txt`). The section
  asserts only that both exit 0, and both did.

## What the fixes in 0.6.63 look like on the rig

Each was a finding of an earlier run, and each shows here as fixed:

- **The partial rips no longer say the disc is not in CTDB.** Each partial rip's report
  records CTDB as `not_whole_disc` and not run
  (`round29fullderivedmp3report.json:640`).
- **The cancelled rip's EAC-layout log says what happened to track 1**: it *"was being
  read when the rip stopped"* (`round29fullcancelmeeac.log:11`), where 0.6.62 said every
  track was *"never extracted"*.
- **`DIAGNOSTICS` names the approved pair and says this app is not it**
  (`round29fulldiagnostics.txt:3`): the pair is 0.6.61 with `.17`, and *"This app is
  Platterpus 0.6.63, which that round did NOT approve"*.

`.18`'s own new lines are in the cancelled rip's cyanrip log
(`round29fullcancelme.log:87-88`): *"Encoder errors: not applicable; no whole track was
encoded"* and *"Partial files: 1 track (1), read not completed; encoder failures: none"*.
The repeat loop's `current checksum` is still the value before the final XOR, and the
tag keys are still in lower case, as they should be in `.18`: the fork's changes to both
(`9669d84`, `bf50705`) come after `51cc789`.

## What it shows that is ours

- **The three screenshot failures** above. They fall in sections H, J and K3, which the
  severity table declares ARCHIVAL, so the run is graded `partial` in the evidence ledger
  (`docs/testing.md` → *Field evidence*). Nothing here re-grades them.
- **The rig check's pin line** said *"A test pin is expected to differ during an open
  round"* beside `.18` (`round29fullrigcheckmanifest.txt:5`), when round 29 names no test
  pin. Fixed after this run: it now names the build under review and its round.
- **The `-9` warning in every report** above: a probe our own Rescan stopped, recorded
  as the ripper failing. Fixed after this run: a probe Platterpus cancels is recorded as
  an `info` saying so (`deps.command_cancelled`), and a `-9` we did not send is still a
  failure.
- **`COMPONENTS.json` records the ripper as bare `0.9.4`**
  (`round29fullcomponents.json:11`), which cannot say which build ran. Known, and a
  NEXT-ROUND row in `TASKS.md`, because the file crosses the seam.

## The files

Each row's sha256 prefix and size are computed from the committed copy.

| our file | tarball member | sha256/16 | bytes |
|---|---|---|---|
| `round29fullaftercanceleac.log` | `album/after cancel 20260928t223356 platterpus-fork-g51cc789/after cancel 20260928t223356 platterpus-fork-g51cc789 (EAC-compatible).log` | `78c50cb9a0833540` | 3,356 |
| `round29fullaftercancel.cue` | `album/after cancel 20260928t223356 platterpus-fork-g51cc789/after cancel 20260928t223356 platterpus-fork-g51cc789.cue` | `5ddf7bd0cc86f311` | 685 |
| `round29fullaftercancel.log` | `album/after cancel 20260928t223356 platterpus-fork-g51cc789/after cancel 20260928t223356 platterpus-fork-g51cc789.log` | `1b3880c82b6d63aa` | 9,170 |
| `round29fullaftercancelreport.json` | `album/after cancel 20260928t223356 platterpus-fork-g51cc789/after cancel 20260928t223356 platterpus-fork-g51cc789.platterpus.json` | `c9142377644b1470` | 528,422 |
| `round29fullcancelmeeac.log` | `album/cancel me 20260928t223356 platterpus-fork-g51cc789/cancel me 20260928t223356 platterpus-fork-g51cc789 (EAC-compatible).log` | `6c3c03f4f65222de` | 2,591 |
| `round29fullcancelme.cue` | `album/cancel me 20260928t223356 platterpus-fork-g51cc789/cancel me 20260928t223356 platterpus-fork-g51cc789.cue` | `07127be3448bde57` | 372 |
| `round29fullcancelme.log` | `album/cancel me 20260928t223356 platterpus-fork-g51cc789/cancel me 20260928t223356 platterpus-fork-g51cc789.log` | `f195866993ad102b` | 4,750 |
| `round29fullcancelmereport.json` | `album/cancel me 20260928t223356 platterpus-fork-g51cc789/cancel me 20260928t223356 platterpus-fork-g51cc789.platterpus.json` | `783c5b1e4e612134` | 203,854 |
| `round29fullderivedmp3eac.log` | `album/derived mp3 20260928t223356 platterpus-fork-g51cc789/derived mp3 20260928t223356 platterpus-fork-g51cc789 (EAC-compatible).log` | `f9bb204a79ed34f0` | 3,393 |
| `round29fullderivedmp3.cue` | `album/derived mp3 20260928t223356 platterpus-fork-g51cc789/derived mp3 20260928t223356 platterpus-fork-g51cc789.cue` | `2e8cdf7958eff76e` | 684 |
| `round29fullderivedmp3.log` | `album/derived mp3 20260928t223356 platterpus-fork-g51cc789/derived mp3 20260928t223356 platterpus-fork-g51cc789.log` | `5b2c7c2ce371c883` | 9,122 |
| `round29fullderivedmp3report.json` | `album/derived mp3 20260928t223356 platterpus-fork-g51cc789/derived mp3 20260928t223356 platterpus-fork-g51cc789.platterpus.json` | `efb055478d7de343` | 535,281 |
| `round29fullderivedwaveac.log` | `album/derived wav 20260928t223356 platterpus-fork-g51cc789/derived wav 20260928t223356 platterpus-fork-g51cc789 (EAC-compatible).log` | `2de2279d3f0ea142` | 3,393 |
| `round29fullderivedwav.cue` | `album/derived wav 20260928t223356 platterpus-fork-g51cc789/derived wav 20260928t223356 platterpus-fork-g51cc789.cue` | `0bdb1fe1441604bb` | 684 |
| `round29fullderivedwav.log` | `album/derived wav 20260928t223356 platterpus-fork-g51cc789/derived wav 20260928t223356 platterpus-fork-g51cc789.log` | `7f855583dee17743` | 9,122 |
| `round29fullderivedwavreport.json` | `album/derived wav 20260928t223356 platterpus-fork-g51cc789/derived wav 20260928t223356 platterpus-fork-g51cc789.platterpus.json` | `627fa78d42c0bf36` | 552,965 |
| `round29fullderivedwavpackeac.log` | `album/derived wavpack 20260928t223356 platterpus-fork-g51cc789/derived wavpack 20260928t223356 platterpus-fork-g51cc789 (EAC-compatible).log` | `6a4e35cf4894bae1` | 3,405 |
| `round29fullderivedwavpack.cue` | `album/derived wavpack 20260928t223356 platterpus-fork-g51cc789/derived wavpack 20260928t223356 platterpus-fork-g51cc789.cue` | `a45f1fe88f3d42f3` | 688 |
| `round29fullderivedwavpack.log` | `album/derived wavpack 20260928t223356 platterpus-fork-g51cc789/derived wavpack 20260928t223356 platterpus-fork-g51cc789.log` | `9b0d5c75acd05129` | 9,146 |
| `round29fullderivedwavpackreport.json` | `album/derived wavpack 20260928t223356 platterpus-fork-g51cc789/derived wavpack 20260928t223356 platterpus-fork-g51cc789.platterpus.json` | `49183500e79127ea` | 542,356 |
| `round29fullwholedisceac.log` | `album/full acceptance_ angle_bracket 20260928t22__terpus-fork-g51cc789/full acceptance∶ angle‹bracket 20260928t223356 platterpus-fork-g51cc789 (EAC-compatible).log` | `9c6cdb880be74f09` | 9,557 |
| `round29fullwholedisc.cue` | `album/full acceptance_ angle_bracket 20260928t22__terpus-fork-g51cc789/full acceptance∶ angle‹bracket 20260928t223356 platterpus-fork-g51cc789.cue` | `b099a1324650b5a6` | 3,149 |
| `round29fullwholedisc.log` | `album/full acceptance_ angle_bracket 20260928t22__terpus-fork-g51cc789/full acceptance∶ angle‹bracket 20260928t223356 platterpus-fork-g51cc789.log` | `e4467f07f63d1637` | 39,666 |
| `round29fullwholediscaddendum.txt` | `album/full acceptance_ angle_bracket 20260928t22__terpus-fork-g51cc789/full acceptance∶ angle‹bracket 20260928t223356 platterpus-fork-g51cc789.platterpus-addendum.txt` | `180cb9327b9e32f9` | 2,444 |
| `round29fullwholediscreport.json` | `album/full acceptance_ angle_bracket 20260928t22__terpus-fork-g51cc789/full acceptance∶ angle‹bracket 20260928t223356 platterpus-fork-g51cc789.platterpus.json` | `debe6cf4f7c510ad` | 5,331,469 |
| `round29fulloverwriteeac.log` | `album/full acceptance_ angle_bracket 20260928t22__us-fork-g51cc789 _2_/full acceptance∶ angle‹bracket 20260928t223356 platterpus-fork-g51cc789 (EAC-compatible).log` | `fd1e6a3848d60547` | 3,459 |
| `round29fulloverwrite.cue` | `album/full acceptance_ angle_bracket 20260928t22__us-fork-g51cc789 _2_/full acceptance∶ angle‹bracket 20260928t223356 platterpus-fork-g51cc789.cue` | `77060e6606bf4089` | 747 |
| `round29fulloverwrite.log` | `album/full acceptance_ angle_bracket 20260928t22__us-fork-g51cc789 _2_/full acceptance∶ angle‹bracket 20260928t223356 platterpus-fork-g51cc789.log` | `636bbb9c8d85147c` | 9,501 |
| `round29fulloverwritereport.json` | `album/full acceptance_ angle_bracket 20260928t22__us-fork-g51cc789 _2_/full acceptance∶ angle‹bracket 20260928t223356 platterpus-fork-g51cc789.platterpus.json` | `efb56b5f30ee1d69` | 522,381 |
| `round29fulldeemphoff.cue` | `album/r16deemphoff/Unknown disc (PNTI).cue` | `62f5d1f150e71e71` | 262 |
| `round29fulldeemphoff.log` | `album/r16deemphoff/Unknown disc (PNTI).log` | `7c9141a215dcbe4b` | 4,980 |
| `round29fulldeemphon.cue` | `album/r16deemphon/Unknown disc (PNTI).cue` | `62f5d1f150e71e71` | 262 |
| `round29fulldeemphon.log` | `album/r16deemphon/Unknown disc (PNTI).log` | `66a42a7d296e48b8` | 4,823 |
| `round29fullsecurerereadeac.log` | `album/secure reread 20260928t223356 platterpus-fork-g51cc789/secure reread 20260928t223356 platterpus-fork-g51cc789 (EAC-compatible).log` | `b9d39a92481a8858` | 10,140 |
| `round29fullsecurereread.cue` | `album/secure reread 20260928t223356 platterpus-fork-g51cc789/secure reread 20260928t223356 platterpus-fork-g51cc789.cue` | `a0c77b89dcb14f00` | 2,956 |
| `round29fullsecurereread.log` | `album/secure reread 20260928t223356 platterpus-fork-g51cc789/secure reread 20260928t223356 platterpus-fork-g51cc789.log` | `76dea5f4254d414c` | 42,744 |
| `round29fullsecurerereadreport.json` | `album/secure reread 20260928t223356 platterpus-fork-g51cc789/secure reread 20260928t223356 platterpus-fork-g51cc789.platterpus.json` | `6e91c1c170227025` | 6,215,215 |
| `round29fullcomponents.json` | `COMPONENTS.json` | `d030b8229f3b6c61` | 1,339 |
| `round29fulldiagnostics.txt` | `DIAGNOSTICS.txt` | `da890d5a426a1fc9` | 5,616 |
| `round29fullmanifest.txt` | `MANIFEST.txt` | `af09b1d9fd99c69e` | 24,134 |
| `round29fullsettings.json` | `SETTINGS.json` | `551e8b2b536c471f` | 2,760 |
| `round29fullsources.txt` | `SOURCES.txt` | `344a914b728b0fc3` | 1,501 |
| `round29fullplatterpusapplog.txt` | `session/artifacts/02platterpus/log.txt` | `034c6afa30b9dc48` | 7,525,050 |
| `round29fullplatterpusapplog1.txt` | `session/zz-applog-rotations/03platterpus/log.txt.1` | `a3c66d5014a89d1e` | 8,388,586 |
| `round29fullconfig.toml` | `session/artifacts/04platterpus/config.toml` | `8d816eea558fa8c8` | 1,141 |
| `round29fullscriptreport.json` | `session/run/report.json` | `45b89f288a8900d3` | 263,511 |
| `round29fulltranscript.txt` | `session/run/transcript.txt` | `d312cc7d3a0daeb9` | 120,724 |
| `round29fullrigcheckmanifest.txt` | `session/run/rig-check/MANIFEST.txt` | `c653ae2f3b0236f8` | 15,846 |
| `round29fullrigcheckargvprobe.json` | `session/run/rig-check/argv-probe.json` | `71f16bc3ac4ff7e4` | 1,628 |
| `round29fullrigcheckargvprobeoutput.txt` | `session/run/rig-check/argv-probe-output.txt` | `9666539892406fec` | 484 |
| `round29fullrigcheckripperversion.txt` | `session/run/rig-check/ripper-version.txt` | `c0c6fd32cd89dda3` | 58 |
