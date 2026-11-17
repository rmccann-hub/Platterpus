REVIEW-FOR: the Platterpus session and the cyanrip fork session · 2026-11-03T07:13Z
FROM: the claude-code-skills session, through the owner
CONDITION: applies to the Full run of 2026-11-03 02:38 UTC (bundle 20261103t023830z), Platterpus
0.7.117 (`104c82d`) with the fork's `.28` (`3f288fb`). Where your `main` has moved past a point,
say `already <commit>`.
EXPIRES: 2026-12-31

# The 2026-11-03 Full run: what it found, and what comes first

Written 2:13 AM EST, Tue Nov 3 (2026-11-03 07:13 UTC). The owner's priority, in their words:
"a focus on acceptability, and existing features working, plus stability, we can worry about new
content shortly". This file sorts every finding by that rule. New features are in a separate
list at the end, for after the next release.

Every finding below was checked against the bundle, and those marked **source** against your code
at the commit named. Answer each with `done <commit>`, `already <where>`, `not doing: <why>` or
`wrong: <what>`.

## The run in one paragraph

553 passed, 0 failed, 1 unreachable (E2, the listed drive), 22 info, in 2 h 22 min (02:38:30 to
05:00:58 UTC). The run is green, but a green run here isn't yet a correct one. Track 5 was written
wrong in every rip, as on every earlier run on this drive, and track 3 was written wrong in all four
P5 rips. Every surface but the EAC-layout log called those rips clean, and no step could fail on
either. Neither is a `.28` regression: `.27` and `.28` did the same in P5 and P6. So nothing here
stops round 37 closing `GO` on `.28`, which both of you committed to. What it does stop is calling
a green run "the audio is right".

## A. Accuracy, and saying it truthfully (fix first)

| # | Finding | Evidence | Whose |
|---|---|---|---|
| A1 | **The report says "No errors occurred" over a track it knows is wrong.** F's and N's `health_status` reads "No errors occurred"; the same rip's EAC-layout log says "Proof: none — WRONG" for track 5, and the report's own CTDB message says "track 5 differs in 3 samples @02:24:59 from the 1,423-submission entry". The same holds for all four P5 rips (track 3). | F's `.platterpus.json` `health_status`; its EAC log, track 5 lines 126 to 129 | Platterpus |
| A2 | **Track 5 is called "offset-variant", "13 of 14 matched" and, in the addendum, "CONFIRMED".** It's the drive's known consistent misread (the EAC parity plan's row 7). Only the EAC log says so. | transcript L729, L1277; the snapshot's AccurateRip line | Platterpus |
| A3 | **CTDB "match" at confidence 1, against 1,524 disagreeing, passes `expect-ctdb whole`.** The report itself says it "does not corroborate the rip". | F's `ctdb.message` | Platterpus |
| A4 | **P5's four rips wrote track 3 wrong, four different CRCs (`2363932F`, `28D42AE3`, `3D8FCF0C`, `AD24D3ED`), each "WRONG" in its EAC log, and nothing graded it.** P6, track 3 alone, was right 8 of 8 (`59D352DD`) on both builds. So on this drive, track 3 read straight after track 2 comes out wrong, and read alone comes out right. The same wrong CRCs appear in the 2026-10-21 bundle. That's the best lead yet on the track 3 question (TASKS R42): a controlled test, below, can settle it. | `timing A1`, `A2`, `B1`, `B2` EAC logs, track 3 | Both |
| A5 | **N's main pass read track 3 five times to four CRCs and logged "Track 3 read with errors.", with "Ripping errors: 0" in the footer.** A securing pass then agreed, and the EAC log shows "Copy OK … confirmed across 3 secure re-reads" next to the main pass's extraction time. | N's cyanrip log, track 3 and footer | Fork (footer); Platterpus (EAC log) |
| A6 | **With `-H` on a disc without HDCD, the written file is 6 dB quieter, while the log certifies CRC `B0D122E7` and "accurately ripped, confidence 200".** The CRC is taken before the filter. Platterpus's own rips don't pass `-H`, so only a user who adds it is hit. Please confirm the cause (libavfilter's `hdcd` output level) before changing anything. | P3 logs: −6.5 dBFS against F's −0.5 | Fork |
| A7 | **Track 9's pregap is logged "unknown", though the search narrowed it to one sector (LSN 145567): 94 or 95 frames.** The cue then omits INDEX 00 for track 9, which tells a player there's no gap at all. Say "94 or 95, undecided", and keep the INDEX 00 at the earlier bound, or record why not. | P3 log "Pregap searches", track 9 | Fork; Platterpus for the cue |

## B. Existing features showing the wrong thing (stability and trust)

| # | Finding | Evidence | Whose |
|---|---|---|---|
| B1 | **The AccurateRip line on the main window is never reset when a rip starts.** During the cancel rip it still read the previous rip's "verified — all 2 tracks matched"; after a 3-track rip cancelled at track 2 it read "verified — all 1 tracks matched". | snapshots `beforecancel`, `aftercancel`, `atend`; `disc_info_panel.py:237` (**source**, `75915aa9`) | Platterpus |
| B2 | **A hidden modal dialog leaks on every cyanrip update offer.** `_offer_ripper_install` (`main_window_update.py:540-569`) doesn't set `WA_DeleteOnClose`; its sibling at line 490 does, with a comment about this exact leak. Every screenshot step lists `QMessageBox 'cyanrip update' visible=False modal=True`. | **source**; every screenshot step | Platterpus |
| B3 | **The run estimate was 2.8 times too long.** It said "at least 6h 40m … at 1.0x"; the run took 2 h 22 min and the drive read at 2.6× to 4.5×. The app log shows the learned speed "folded over 1 rip(s)" after each rip and lost at each rescan, back to the 1.05 default in `rip_estimate.py:60`. F was estimated at 1 h 2 min and took 20 min. The file header's "Full: 4 to 6 hours" is wrong for the same reason. | transcript header; report.json `elapsed_s` sums to 8,464 s | Platterpus |
| B4 | **rig-check says F's secure re-read "exercised: no"**, but a securing pass ran on track 5 (`-Z 2 -l 5`, 02:55:58 to 02:59:37 UTC). rig-check reads only the whole-disc log, and the report's paranoia counts leave out the securing pass. | F's rig-check row; `.platterpus-securing-pass.txt` | Platterpus |
| B5 | **Fork footers count against the whole disc.** `-f` prints "Tracks ripped accurately: 0/14"; `-l 1` prints "1/14"; a cancelled rip counts "Ripping errors: 1" for the SIGTERM; the cancel rip's EAC log says "All ripped tracks accurately ripped" for 1 of the 3 asked. | O, P3 and I outputs | Fork; Platterpus for the EAC line |
| B6 | **The fork's `Embedded cover art:` line can claim a cover the file doesn't hold.** It's in the fork's own task list as a known bug. | fork task list | Fork |
| B7 | **The app log's warnings are almost all noise:** 1,942 of 2,017 are `safe_int … undecided from/to: None`, one per normal track. A real warning can't be seen among them. | app log | Platterpus |
| B8 | **The bundle's `SOURCES.txt` contradicts its `MANIFEST`** about app logs `.6` to `.10`, and the size budget went on 42 MB of app logs from 10-14 to 10-29, unrelated to this run. The run also wrote 20 per-rip bundles (89.8 MB) where the closing text promises one file. | bundle root | Platterpus |
| B9 | **Cancel relies on `fuser -k TERM /dev/sr0`, which signals whatever holds the drive, not only cyanrip.** Podman doesn't forward the wrapper's SIGTERM (`sigterm-world`: "ONE SIGNAL"). Signal the container's process instead, or record why the device-wide signal is safe. | I's `sigterm-world` | Platterpus |

## C. The acceptance test: steps that pass without checking (fix with A and B)

| # | Gap | Evidence | Whose |
|---|---|---|---|
| C1 | **`expect-verification` passes when a check ran and FAILED.** It needs some gate to say "ran", and `gate_claims_ran` accepts "ran — failed"; `derived_verification_refusal` rejects only "not run" and "cut short". A FLAC that fails `flac --test`, or a derived file that isn't its master, passes F, H, J, K and N. | **source**, `runner.py:2948-2966` and `artifact_grading.py:112-138`, `75915aa9` | Platterpus |
| C2 | **No step can fail on accuracy.** `expect-accuraterip` passes a "no-match" by design. Keep that, and add the honest assertion: **every track AccurateRip or CTDB contradicts is shown as wrong on every surface** (report, window, EAC log, notification). That fails A1 and A2 today, and stays green on a bad drive that is reported truthfully. | — | Platterpus |
| C3 | **Nothing asserts the read offset a rip used.** The report computes `rip.read_offset_check`; no verb reads it. A sign flip in `-s` would leave the run green. | coverage audit | Platterpus |
| C4 | **K1 to K3 grade the FLAC masters, not the MP3, WavPack or WAV files.** Nothing proves `mp3_vbr_quality 2` reached the encoder, and the K3 title's "the UI must say so" has no step. | transcript L1060, L1087, L1114 | Platterpus |
| C5 | **P3 can decide clause 2, and its comment says it can't.** Since `.20` the fork measures loudness on the delivered audio and the checksums on the read (`cyanrip_encode.c`, `measure_frame`). The run: both arms CRC `B0D122E7`; `-H -E` −20.7 LUFS, `-H -W` −19.9 LUFS. Same read, different delivered audio, quieter with de-emphasis, as it should be. A verb that asserts "CRCs equal, R128 differs by at least a set amount" settles it on any disc. | P3 logs; **source** at the fork's `239adda` | Platterpus, with the fork to confirm |
| C6 | **The transcript lost P3's result.** Each P3 step captured about 898 KB of `progress - xx.xx%` lines, and the elision cut the track block. Fold carriage-return progress lines before storing. | transcript L1547, L1553 | Platterpus |
| C7 | **O, P, P2 and P3 pass no `-d`.** On a two-drive machine they'd test another drive than the one B set. Add a `(device)` placeholder; `docs/dependency-contracts.md` already says `-d` is passed when known. | script | Platterpus |
| C8 | **P5's `record-timing` records time only.** Add each track's AccurateRip state, so A4 can't happen unseen again. | transcript L1636 | Platterpus |
| C9 | **Settings OK, overwrite Replace and Cancel, cancel during the securing pass, Force stop, eject and re-insert, an unwritable output folder, and Tools → Setup & Updates are never exercised.** Each is an existing feature a user reaches. The first six are scriptable on one drive. | coverage audit, gaps 4, 6, 7, 9, 10, 13 | Platterpus |
| C10 | **No free-space check exists anywhere** (`statvfs`/`disk_usage` absent from `src/`). A full disk mid-rip is an existing-feature failure, not a new feature. | **source** search | Platterpus |

Already fixed on `main` since 0.7.117, so not asked: P4 now runs after P6 (`7af6c680`).

## D. A controlled test for track 3 (A4), worth one short run

On the reference disc, alternate four rips of tracks 2 and 3 together with four of track 3 alone,
same build, same settings as P6 (ABBA order). If "after track 2" is wrong and "alone" right
again, the cause is the read path between tracks (read-ahead or cache), not the build. Then
compare with `--cache-probe`'s figure and cd-paranoia's `-A`. About 25 minutes. This can be a P6b
section, or a one-off script. The fork names what to vary next.

## E. How to find what we don't know we're missing

Ranked by value for the effort:

1. **Plant defects and check that the graders catch them.** Take real filed reports, plant one
   fault each (a failed gate, a stripped tag, a truncated FLAC, a changed `-s`, a missing `FLAGS
   PRE`, a WRONG track shown as OK), and replay every verb. A planted fault no step catches is a
   hole. This finds C1 to C4 in an afternoon, and needs no drive.
2. **An inventory guard, generated from the source.** Every verb, dialog, menu action, Setup &
   Updates action, setting value and command-line flag is used by a rig script, or listed with
   its reason and the unit test that covers it. Like the settings guard you already have.
   Today 8 of 70 verbs and the getting-started dialog are unused.
3. **One Standard run under coverage.py,** compared with CI's coverage. The lines only hardware
   reaches are what CI can't see; the lines nothing reaches are the gap list.
4. **Differential rips.** Rip the reference disc with whipper (Linux) and compare per-track CRCs,
   pregaps, ISRCs and the cue. Use the owner's EAC log of the same pressing, which has already
   shown EAC calling a wrong track 5 "Copy OK".
5. **Mine the filed runs.** Steps whose pass text never varies across builds and discs probably
   don't read their subject; info rows that never vary are candidates to become assertions.
6. **A disc corpus.** The run can't reach damaged media, HTOA, pre-emphasis, Enhanced CD,
   CD-Text, a CD-R, a disc unknown to AccurateRip, or an unlisted drive (E2). One disc of each
   kind, recorded as the run's inputs, turns "never exercised" into a row.

## F. After the next release: features others have and we don't

From a survey of EAC 1.8, dBpoweramp, CUETools, XLD, whipper, redumper and others, checked
2026-11-03. Correctness first:

1. **CTDB repair** (only CUETools; a Linux .NET `ctdb-cli` exists).
2. **C2 pointers as extra evidence**, with the drive's error masking off, after a per-drive trust
   test (libcdio's `mmc_read_cd` exposes them).
3. **A per-track time limit as a multiple of real time,** as EAC has, and **a tray lock during a
   rip,** EAC's default, which bears on the tray-blip row.
4. **HTOA**, with read agreement as its check, since neither database covers it.
5. **Lead-in and lead-out:** probe each drive for overread; log which edge samples were read,
   padded or unverified.
6. **The sub-channel as a second source** for pre-emphasis and layout. EAC reads pre-emphasis
   from the table of contents only.
7. Data tracks and Enhanced CD (upstream cyanrip bug #168 hangs on one with a positive offset),
   image + cue, CTDB submission, CD-Text reading, re-verifying an existing library.

Corrections to the EAC parity plan of record (2026-10-26):
- **Reading did change after 1.0 beta 3.** Beta 6 fixed crashes on read errors; 1.1 fixed
  "extraction problems with some LG drives"; 1.2 fixed read-command detection. Run 1.8; it's
  still the newest (15 July 2024).
- **EAC's log checksum isn't secret.** The key is in OPS's open logchecker, so row 28's
  "closed, obfuscated" should read "public, catches only casual edits".
- **EAC 1.x submits AcoustID fingerprints by default.** Untick it in the installer.
- **EAC's own log of this disc** shows "Copy OK" over track 5 with Test and Copy CRCs matching,
  and "Copy OK" over tracks 3 and 4 with them differing. Matching CRCs prove consistency, not
  correctness. Platterpus already does better here whenever it says WRONG; A1 and A2 are where it
  doesn't yet.

The full survey, the EAC delta and the coverage audit go with this file.
