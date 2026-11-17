# Defect hunt: Full acceptance bundle 20261103T023830Z

Subject: Platterpus 0.7.117 (build 104c82d), cyanrip fork 3f288fb (`0.9.4-rc3+platterpus.28`), PIONEER BDR-209D, "The Police — Every Breath You Take: The Classics" (disc ID `pNtImOkdBm9RMBIalzx0w9cfsYY-`).
Reported result: `pass=553 fail=0 unreachable=1 info=22`.
Bundle: `scratchpad/b1103`. All paths below are relative to it unless they start with `src/`, which means the Platterpus source at 104c82d (or the fork at 3f288fb where named).
Baselines: the 2026-10-21T11:35Z bundle is the same disc. The 2026-10-22T21:57Z bundle is another disc.
Method: read-only. Python ran with `-I` only, from scripts kept outside the bundle.

Times: the run started at 02:38:30 UTC and the last app-log line is at 05:00:58 UTC (`2026-11-03 00:00:58` in the log's zone-less local time, UTC−5). Wall time was 2 h 22 m 28 s.

Severity keys: **accuracy**, **misleading-to-user**, **stability**, **test-gap**, **cosmetic**.

---

## Confirmed findings, ranked

### 1. accuracy: track 5 is a reproducible 3-sample misread, and every surface except the EAC log softens it
- CTDB pins the error to one place. `album/full acceptance_…terpus-fork-g3f288fb/…platterpus.json` → `ctdb.message`: "matched 1 of 1,525 CTDB submissions; 1,524 disagree … **track 5 differs in 3 samples @02:24:59 from the 1,423-submission entry**". `ctdb.tracks[4]`: `confidence 2, disagreeing_confidence 1523, outvoted true`. N's report says the same.
- AccurateRip: v1 `F5426D5F` and v2 `9EEB8843` were not found. Only frame 450 (`4CCBCF89`, confidence 200) matched. Frame 450 is six seconds into the track. The error is at 2:24, so a frame-450 match is exactly what a correct pressing read with a mid-track misread would produce.
- The reads are consistent but not correct. In F the securing pass converged on `E0036697` three times (`…platterpus-securing-pass.txt`: "Done; (2 out of 2 matches for current checksum E0036697)"). In N, read 2 gave `6902BCF0` (`album/secure reread…/…g3f288fb.log:420`). `src/platterpus/one_frame_match.py` itself records `E0036697` ×4 and `6902BCF0` ×2 across earlier rips.
- What each surface says:
  - EAC-layout log, track 5: "Proof: none — WRONG … the audio differs from it". This is the only accurate statement.
  - JSON: `health_status: "No errors occurred"`. `ctdb.verdict: "match"`. `verdict.message`: "on the other 1, only one frame matched, so the rest of each is unverified".
  - Addendum: "the original read is CONFIRMED". DIAGNOSTICS.txt logs this as `[info] … (2 out of 2 matches for current checksum E0036697)`.
  - UI: "accuraterip: 13 of 14 tracks matched".
  - Transcript: L730 `expect-ctdb whole` → "match, confidence 1, 102 entr(ies)". L729 `expect-accuraterip` → "offset-variant: 5". `one_frame_match.py` calls that name wrong on the mechanism, and the transcript is a surface its sweep does not cover.
- **Owner:** the app (verdict, health and CTDB surfaces), the test script (the graders, see #12), and the fork (it presents convergence as "secured").
- **Fix:**
  - When CTDB localises a difference, surface it: name the track and position, and set the verdict to error.
  - Treat `outvoted:true` as a CTDB non-match.
  - Derive `health_status` from the same verdict the EAC export uses.
  - Never say "CONFIRMED" or "secured" for a read that AccurateRip contradicts.

### 2. accuracy and test-gap: all four P5 timing rips wrote track 3 wrong, and nothing graded it
- `album/timing A1|A2|B1|B2/…log`: track 3 CRCs are `2363932F`, `28D42AE3`, `3D8FCF0C` and `AD24D3ED`. That is four different values, none matching AccurateRip, and each EAC log says "Proof: none — WRONG". The FIXUP_ATOM counts are 12 to 24.
- Each cyanrip log still says "Track 3 read with no error reported." and "Ripping errors: 0". Each JSON has `health_status: "No errors occurred"`.
- Transcript L1634–1657 has only `expect-rip-complete` and `expect-verification` passes plus info lines. L1658 compares timings over rips whose data is wrong.
- P6 rips track 3 alone and concludes "right in 4 of 4" for both builds (L1789). P5 contradicts that in the same run, and nothing compares the two.
- The same wrong CRCs recur across runs. The 2026-10-21 bundle (same disc) has `2363932F` in F and timing B2, `3D8FCF0C` in N, and `D7314554` in timing B1. A drive that reproduces identical wrong data is why convergence (#1, #3) is not proof.
- **Owner:** the test script (P5/P6 design, no grading), the fork (no error reported despite fixups and a wrong result), and the app (health).
- **Fix:**
  - Have `record-timing` and `record-accuracy` flag any track that is not verified.
  - Rip track 3 in P6 both in context (tracks 2–3) and in isolation.
  - Make P5 fail or warn when its rips are not accurate.

### 3. accuracy and misleading-to-user: N's main pass never converged on track 3, and the EAC log hides it
- `album/secure reread…/…g3f288fb.log:243-252`: five reads gave four distinct CRCs (`59D352DD` ×2, `B3A1A10D`, `C553E601`, `5D24EB87`). The log says "Done; (repeat limit of 5 reads reached; at most 2 reads agreed…)" and "Track 3 read with errors.", but its footer says "Ripping errors: 0".
- A securing pass then converged (`ripperdiagnostics/…041449Z-securingpass.json`, DIAGNOSTICS 04:19:49).
- The EAC-layout log shows track 3 as "Copy CRC 59D352DD (Test and Copy CRC identical — confirmed across 3 secure re-reads) … Copy OK", next to "Extraction time 0:04:51", which is the five-read main pass. The instability is not mentioned.
- Transcript L1261 says "every measured track converged".
- **Owner:** the fork ("read with errors" not counted) and the app (the EAC export and JSON drop the instability; `read_speed.retried_tracks[0].trigger:"instability"` exists only in JSON).
- **Fix:**
  - Count non-convergence in "Ripping errors".
  - Have the EAC export print a "suspicious / re-read" note, and the extraction time of the read it actually kept.

### 4. accuracy: with `-H` the FLAC is 6 dB quieter, yet the log certifies it "accurately ripped"
- P3 control `-H -W` (`album/r16deemphoff/Unknown disc (PNTI).log`), track 1: "HDCD detected: no", sample peak −6.5 dBFS, I −19.9 LUFS.
- F track 1 (no `-H`): sample peak −0.5 dBFS, I −13.9 LUFS. The gap is exactly 6.0 dB and 6.0 LU, so the written audio was attenuated.
- `-E` (`r16deemphon`) changes it again: −6.3 dBFS, −20.7 LUFS.
- All three logs print "EAC CRC32: B0D122E7" and "Accurip v2: 22B9924D (accurately ripped, confidence 200)", plus "Tracks ripped accurately: 1/14". The CRC and AccurateRip result describe the pre-filter PCM, not the file on disk.
- P3 grades only `expect-exit 0` (L1548, L1554). Normal Platterpus rips pass `-W` and no `-H` (F argv), so this hits only users who pass `-H` or `-E` themselves.
- **Owner:** the fork (log claims) and the test script (no comparison).
- **Fix:**
  - The fork should mark CRC/AR as "of the read, not the file" when any filter alters samples, or compute a post-filter CRC.
  - P3 should diff the two logs' peak and loudness values and assert the CRC caveat.

### 5. accuracy (minor) and misleading-to-user: the track 9 pregap was narrowed to one sector but is reported "unknown", and the cue claims none
- F JSON `tracks[8].pregap_search`: `undecided_from 145567, undecided_to 145567`. That is one sector, so the pregap is 94 or 95 frames. Yet the log says "pregap of track 9 unknown (sub-channel search bounds did not meet)", which the numbers contradict.
- The 2026-10-21 logs found "94 frame" ×2 and "95 frame" ×2 for track 9.
- The F `.cue` has no `INDEX 00` for track 9, which tells cue consumers that the track has no gap.
- The EAC header says "Gap handling: (undetermined: the ripper could not measure a pregap)" for the whole disc. It says this even in rips that never contained track 9 (all P5/P6 EAC logs; app log warns 21×).
- The pregap search's "frames answered −1 sectors off" varies between +0 and −1 across runs.
- **Owner:** the fork (message and resolution) and the app (cue, EAC header scope).
- **Fix:**
  - Report "94–95 frames (1 sector undecided)".
  - In the cue, add a `REM` noting the uncertainty.
  - Scope the Gap-handling row to the tracks actually ripped.

### 6. misleading-to-user: the run estimate is about 2.8× too long, because the drive's learned speed is thrown away
- The printed estimate says "at least 6h 40m … 21 rip(s) about 6h 30m at 1.0x (the speed the project's rig measured for this drive model)". The actual run took 2 h 22 m.
- Measured first-pass speeds were 2.6× to 4.5× (F EAC log; cd-paranoia raw reads were 6.1× to 13.4×).
- Per-rip estimates were also wrong. App log: F "estimated before it began: 1h 2m 36s" against 20m 32s actual. N "3h 7m 29s" against 59m 45s.
- Root cause, from the app log:
  - Every rip logs "drive reading speed learned … **folded over 1 rip(s)**". Only once does it say 2.
  - After each rescan ("drive changed: /dev/sr0" at 22:06:55 and 22:19:48), the next plan falls back to the seed "at 1.0x (the speed measured on the project's test rig…)".
  - So a drive with dozens of past rips still starts at the seed. `src/platterpus/rip_estimate.py:60` `MODEL_SEEDS = {"PIONEER BD-RW BDR-209D": 1.05}`.
- The seed is stale. The same disc read at 2.6× to 4.4× on 2026-10-21.
- The wording also misleads. "NOT counted … section(s) E2, J2, O, P4, P5, P6" refers only to non-rip steps, but J2, P5 and P6 own 13 of the 21 rips that *are* counted.
- **Owner:** the app (`main_window_drive` and the drive-profile fold, `rip_estimate`, `run_estimate.describe`).
- **Fix:**
  - Persist the folded `read_rate` across rescans and sessions. Find the triple "drive profiles saved" write that clobbers it.
  - Re-derive the seed from current reports.
  - Reword to "non-rip steps of sections … not counted".

### 7. misleading-to-user: rig-check says F's secure re-read was not exercised, and the report under-counts reads
- F did run a dynamic securing pass: track 5 only, `-Z 2 -l 5`, three reads, from 02:55:58 to 02:59:37 UTC (`outcome.securing_pass_*`, `read_speed.retried_tracks[0].trigger:"accuraterip"`). The securing-pass log says "Scope: the last of 3 reads".
- rig-check, which parses only the whole-disc log, prints "Scope: line present on 0 of 14 track(s) — secure re-read genuinely exercised: no" (`session/run/rig-check/MANIFEST.txt`, first block).
- F JSON `paranoia_counts.READ = 21972` leaves out the securing pass's 4,422 READs.
- **Owner:** the rig-check tool and the app report.
- **Fix:** have rig-check and the report read `*.platterpus-securing-pass.txt` too, and say "exercised on track(s) 5 (securing pass)".

### 8. misleading-to-user: the AccurateRip status line is stale, claims too much, and has a grammar error
- `src/platterpus/ui/disc_info_panel.py:237` prints `f"verified — all {total} tracks matched"`. It is set only after a rip and never cleared when a rip starts.
- `beforecancel` (L832), taken during the 3-track cancel rip, still shows H's "verified — all 2 tracks matched".
- After the cancelled rip it shows "verified — all 1 tracks matched" (L876 and L879). Two of the three requested tracks were never ripped. The JSON verdict correctly says "1 of 3 … cancelled".
- `atend` shows "verified — all 1 tracks matched", which is from P6.
- **Owner:** the app.
- **Fix:**
  - Reset the line to "—" or "reading…" on rip start.
  - Use the rip's requested track count, and say "cancelled" or "partial".
  - Pluralise correctly.

### 9. misleading-to-user: `health_status` contradicts the EAC log
F, N and P5 ×4 have `health_status: "No errors occurred"` while their EAC logs end "There were errors" / "Some tracks could not be verified". The cancel rip says "1 ripping errors" (grammar).
- **Owner:** the app.
- **Fix:** derive one health word from the verdict, and pluralise.

### 10. stability: a hidden modal QMessageBox titled "cyanrip update" leaks for the life of the process
- It comes from `src/platterpus/ui/main_window_update.py:540-569` (`_offer_ripper_install`), which builds `QMessageBox(self)` titled "cyanrip update" and opens it with `open()`. It **never sets `WA_DeleteOnClose`**.
- Its sibling at lines 487–490 does set it, with the comment "without it every check would leave a hidden QMessageBox parented to the window for the life of the process."
- The app log shows the box was created when the operator ran Setup & Updates → ripper_update at 02:33:51 UTC and installed 3f288fb (log line `21:33:58 installing cyanrip 3f288fb`).
- Can it pop up later? I found no path:
  - `_on_ripper_offer_answered` drops the only reference.
  - `_modal_floor_blocker` uses `activeModalWidget()`, which ignores hidden widgets.
  - It does pile up, one per accepted or declined offer, and it pollutes every screenshot inventory.
- **Owner:** the app.
- **Fix:** add `box.setAttribute(Qt.WA_DeleteOnClose)`, or `deleteLater()` in both answer handlers. Add a test asserting no hidden `QMessageBox` children after an offer.

### 11. misleading-to-user: bundle provenance lies about what it holds
- `SOURCES.txt` says "asked for 15: 15 collected, 0 absent, 0 failed" and lists `log.txt.6`–`.10` as "archived as …".
- `MANIFEST.txt` says those five were "excluded: the bundle's 67108864-byte total budget was already spent".
- The budget went to `log.txt.1`–`.5`: 42 MB of app logs dated 2026-10-14 to 10-29, from Platterpus 0.7.105–0.7.112, unrelated to this run. This run is entirely in `log.txt` from line 4462.
- **Owner:** the app (`evidence_bundle`).
- **Fix:**
  - Include only rotations whose time span overlaps the session.
  - Make SOURCES.txt agree with MANIFEST.

### 12. test-gap: the graders cannot fail on accuracy
- `src/platterpus/uiscript/artifact_grading.py:230` passes `expect-accuraterip` on any "determined" state, `no-match` included ("Passes on any disc").
- `expect-ctdb whole` passed an outvoted, confidence-1 match.
- With those two, a run whose tracks are wrong is green (#1, #2).
- **Owner:** the test script.
- **Fix:**
  - On a disc AccurateRip holds, grade `verified` or explain the exception.
  - Fail CTDB `outvoted:true`.

### 13. test-gap: P4 runs before P5 and P6 (confirmed)
- P4 is at L1576. P5 starts at L1614 and P6 at L1720.
- "13 log(s) compared" = 9 album logs (F, H, I, J, J2, K1–K3, N) + 2 securing passes (F, N) + 2 R16 logs. The 12 P5/P6 rips are not compared.
- P4 also counts a uniform "unknown" as agreement (track 9), and it compares only the summary gap list. The per-track search detail varies (track 4 "10" vs "18 frames were another sector's"; track 9 shift +0 vs −1).
- **Fix:**
  - Move P4 after P6.
  - Treat "unknown in every log" as not determined.

### 14. test-gap: K1–K3 grade the FLAC masters, not the derived files
- `expect-tags` and `expect-cover-art` report "2 FLAC(s)…" (L1060, L1087, L1114). The script is at `fullacceptance.txt` lines 1039–1116.
- `mp3_vbr_quality 2` is never verified: no encoder argv appears in the app log or the report, and `verification.derived.proof` is "decodes cleanly + complete".
- MP3 and WavPack tags are unchecked.
- K3 is titled "no tags, no art – the UI must say so", yet no step checks a UI warning. K3 actually embedded art in the FLACs and saved `cover.jpg` (`cover_art.mode:"complete"`).
- **Fix:** add verbs that read tags, art and bitrate mode from the `.mp3`/`.wv`/`.wav` files, plus an `expect-status` (or similar) check for the WAV warning.

### 15. test-gap and cosmetic: the transcript is large, and the evidence that matters was elided
- `session/transcript.txt` is 186,720 B. By step type:

  | Step type | Size |
  |---|---|
  | `cyanrip` verbs | 35.8 KB |
  | `install-ripper` | 31.2 KB (11 runs, compile lists) |
  | `screenshot` | 21.9 KB (each lists 8 hidden windows, the leaked box among them) |
  | `rig-check` | 19.0 KB (identical boilerplate ×7) |
  | `snapshot` | 13.0 KB |

- `report.json` is 419,986 B. `script_source` alone is 101.8 KB.
- The two P3 `cyanrip` steps captured ~900 KB each of `Ripping and encoding track 1, progress - xx.xx%` lines, carriage-return updates stored as separate lines. Transcript lines 1545 and 1751: "… [897766 characters omitted] …" and "[897748 …]".
- The elision removed the track result block, so neither the transcript nor `report.json` holds P3's outcome. The cache-probe step lost 11,736 chars the same way.
- **Owner:** the test runner's `cyanrip` verb.
- **Fix:**
  - Collapse CR-overwritten lines, as the fork's diagnostics JSON already does.
  - Keep the tail block whole.
  - Print the screenshot inventory only for visible windows.

### 16. stability and noise: warning spam in the app log
- Of the session's 2,017 WARNING lines, 1,942 are `safe_int: unusable integer for Pregap search undecided from/to: None`. They fire for every normal track (the field is legitimately absent) on every re-parse.
- About 20 more are `uiscript.runner` "info" outcomes logged at WARNING.
- The P2 refusal, which the test expected, lands in user-facing DIAGNOSTICS as `[warning] deps.command_failed`, making "worst: warning".
- There are seven ETA sanity warnings ("computed 71580s remaining … read at 0.01%").
- **Fix:**
  - Treat an absent `undecided` as normal.
  - Log info at INFO.
  - Tag expected script refusals.
  - Do not compute an ETA below about 1% progress.

### 17. misleading-to-user: rig-check `argv/integrity` is a synthetic probe presented as the rip's own
- `rig-check/argv-probe.json` invokes `… -d /nonexistent-platterpus-rig-check.cue … -Z 2 -l 1,2 …` and exits with 74.
- Every rig-check prints the same "all 19 flag token(s) we composed arrived intact (… -Z … -l …)". F's own argv has neither `-Z` nor `-l`, and has `--prefer-disc-isrc` and `-D`, which the probe never sends.
- "19" counts `-t` twice while 18 flags are listed.
- The rip's real argv check is the report's `argv_agreement`, which says "18 flags".
- **Fix:** label the row "synthetic probe argv" and use the rip's actual flag set. Also note that `device` is always SKIPped.

### 18. misleading-to-user: fork footers on non-rips and partial rips
- `-f`: "Tracks ripped accurately: 0/14".
- P2 `-l 1`: "Rip completed: no (aborted, 0 of 14 tracks)".
- P3 `-l 1`: "Tracks ripped accurately: 1/14".
- F securing pass: "Tracks ripped accurately: 0/14" for a one-track pass.
- Cancel rip: "Ripping errors: 1" for a SIGTERM, with no read error. The EAC log reads "All ripped tracks accurately ripped — this log covers 1 of 14 disc tracks" when 3 were requested.
- **Owner:** the fork, and the app for the EAC line.
- **Fix:** use the requested track count as the denominator, suppress the accuracy line in `-f` mode, and do not count an interruption as a ripping error.

### 19. cosmetic: mixed provenance and formats
- The EAC "Extraction logfile from" header uses `rip.creation_date`, which is the rip's end or the securing-pass start. F shows 21:55 for a start of 21:39; N shows 23:14 for a start of 22:20.
- `tracks[].kept_read_began` names the first pass, while the kept file came from the securing pass. F track 5 says 02:44:42Z against 02:58:26Z; N track 3 is the same.
- EAC "Extraction time 47.35 s" sits beside "0:01:13".
- The cyanrip pregap "00:01.40" is in frames, while the EAC log's "0:00:01.53" is in centiseconds.
- The addendum repeats itself: "confidence 128 — confidence 128".
- The verdict says "the rest of each" about one track.
- The F CTDB top-level confidence is 1 while track 5 says 2.
- App-log timestamps carry no zone.
- `cacheprobe1364.txt` holds raw `\x08` characters.
- The probe ran `/usr/bin/cd-paranoia` (libcdio 2.1.0), while COMPONENTS lists `~/.local/bin/cd-paranoia`.
- The cyanrip header "Cache model: 1200 sectors (… not probed)" disagrees with the fork probe ("128 to 255") and cd-paranoia (144).
- Twenty per-rip bundles (89.8 MB) were written under `ripbundles/`, while the closing text says "ONE .tar.gz".
- Section Q "leaving the rig on the shipped defaults" is undone by the session restore (SETTINGS.json `before_run` vs `config.toml`).

### 20. stability (design note): Cancel does not reach the ripper
L875: "ONE SIGNAL (podman does not forward the wrapper's SIGTERM)". The app's rescue at +5 s runs `fuser -k TERM /dev/sr0` (app log 22:04:43), which signals whatever process holds the drive, not only cyanrip.
- **Fix:** signal the container PID (`podman exec … kill`), or forward the signal in the wrapper.

---

## Questions answered directly
- **The probe-only `-I` and `-f` steps wrote no folder or files.** Fork source `src/cyanrip_main.c` at 3f288fb:
  - With `-I`, `print_info_only` skips `cyanrip_log_init` and `cyanrip_cue_init` (lines 3774–3828), and calls `crip_get_path(…, create_dirs=0, …)`.
  - `-f` reaches `goto end` (line 3719) before log init. No `--diagnostics` was passed.
  - The MANIFEST lists 23 album folders, none from either step, and P4's count of 13 logs leaves no room for one. An empty directory cannot be excluded from the bundle alone, but the source says none is made.
- **The F secure pass** ran on track 5 only, and is not reflected in the rig-check row (#7).
- **The estimate against reality:** see #6.
- **The hidden box:** see #10.
- **P4 order:** confirmed in #13.
- **K1–K3:** see #14.

## Suspicions (not confirmed)
- The single confidence-1 CTDB entry matching our whole disc may be this rig's own earlier submission, or another drive with the same misread. Check whether anything on the rig submits to CTDB.
- Track 3 reads wrong when it is read continuously after track 2 (P5 4/4 here; 2/4 on 10-21), and right when the rip starts at track 3 (P6 8/8). This points to a readahead or seek-context effect: cd-paranoia reports "Drive readahead past read cursor: 112 sector(s)", and `cyanrip` runs with a 1200-sector cache model. It is worth a controlled test (tracks 2–3 against 3 alone, at fixed speeds).
- "Appended silence: track(s) 14 (2 frame(s))": the +667-sample shift is 1.13 frames of samples. The wording may overstate how much is silence.
- `REPLAYGAIN_*_PEAK` holds the true peak (above 1.0, for example `1.029445`) where ReplayGain readers expect the sample peak.
