# Full runs of 2026-10-22: Platterpus 0.7.112 with ripper `.26` (ca0f097)

Read-only analysis. Nothing in either bundle was executed. All times are UTC. The app log and the rip logs stamp local time (UTC-04:00), which is converted here.

Sources read against: Platterpus `origin/main` bba81563 (the run's embedded `script_source` is byte-identical to `src/platterpus/rig_scripts/fullacceptance.txt` there), and the fork `origin/platterpus-fork` fc73b4d (`docs/handshake/STATUS.md`) with `.26`'s source at ca0f097.

## Path legend

Every citation is bundle-relative. `R1:` means `20261022t114515z/` and `R2:` means `20261022t215702z/`. The aliases below each stand for a bundle-relative path.

| Alias | Bundle-relative path |
|---|---|
| `FA1` | `album/full acceptance_ angle_bracket 20261022t11__terpus-fork-gca0f097/full acceptance∶ angle‹bracket 20261022t114515 platterpus-fork-gca0f097 CD3` (+ `.log`, ` (EAC-compatible).log`, `.platterpus.json`, `.platterpus-securing-pass.txt`, `.platterpus-verified-read.txt`, `.cue`) |
| `SR1` | `album/secure reread 20261022t114515 platterpus-fork-gca0f097/secure reread 20261022t114515 platterpus-fork-gca0f097 CD3` (+ the same suffixes, and `.platterpus-addendum.txt`) |
| `FA2` | `album/full acceptance_ angle_bracket 20261022t21__terpus-fork-gca0f097/full acceptance∶ angle‹bracket 20261022t215702 platterpus-fork-gca0f097 CD4` |
| `SR2` | `album/secure reread 20261022t215702 platterpus-fork-gca0f097/secure reread 20261022t215702 platterpus-fork-gca0f097 CD4` |
| `TA1_2` | `album/timing A1 20261022t215702 platterpus-fork-g5f1d036/timing A1 20261022t215702 platterpus-fork-g5f1d036 CD4.log` (`TA2_2` is the same for A2) |
| `DM1` | `album/derived mp3 20261022t114515 platterpus-fork-gca0f097/derived mp3 20261022t114515 platterpus-fork-gca0f097 CD3.platterpus.json` |
| `APP` | `session/artifacts/02platterpus/log.txt` |
| `TR` | `session/run/transcript.txt` |
| `REP` | `session/run/report.json` |

## 0. The two runs are not of the same disc

The brief says the two runs read the same disc. They did not. They read **two different discs of one 4-CD release**:

| | R1 (11:45:15Z to 14:42:05Z) | R2 (21:57:02Z to 23:34:41Z) |
|---|---|---|
| `-c` sent | `3/4` (R1:FA1.log:2) | `4/4` (R2:FA2.log:2) |
| Disc number | 3 (R1:FA1.log:25-26) | 4 (R2:FA2.log:25-26) |
| DiscID | `bkyFFk2LvIJXMj3E1Is2rA8Rj9U-` (R1:FA1.log:29) | `rBin7wC6wjdr7ZsrLr.6j6rYAkA-` (R2:FA2.log:29) |
| AccurateRip ID | `002086bf-0189efd1-f80d8b10` (R1:FA1.log:34) | `0024d7eb-01b5ecd5-d30e6e10` (R2:FA2.log:34) |
| Total time | 57:47.65 (R1:FA1.log:37) | 61:34.30 (R2:FA2.log:37) |
| Platterpus medium match | "medium 3 of 4" (R1:FA1.platterpus.json, `disc.medium_detail`) | "medium 4 of 4" (R2:FA2.platterpus.json) |
| File names | `… CD3.*` | `… CD4.*` |

The r16 folders are named after each DiscID's first four letters: `Unknown disc (BKYF)` in R1 and `Unknown disc (RBIN)` in R2.

**Consequence:** comparing the runs' per-track checksums, AccurateRip results, pregaps, ISRCs or CTDB results tests nothing about consistency, because every one of them is a property of the medium. Section 3 therefore checks consistency **within** each run, where every disc was read 2 to 15 times. It then lists every difference between the runs and says which ones come from the medium.

## 1. Which disc

**Release.** MusicBrainz `53d0f596-95a3-4e60-b4aa-09f5f7532b1e` (R1:FA1.log:30, R2:FA2.log:30). That is *Roots Music: An American Journey* (Various Artists, Rounder 11661-0501-2, barcode 011661050129, US, 2001-10-09), four CDs of 18, 18, 16 and 16 tracks.

The title comes from a read-only MusicBrainz web-service lookup made on 2026-10-26. The label, catalog number, barcode and date also appear in the `-a` argument at R1:FA1.log:2.

MusicBrainz lists `bkyFF…` under medium 3 and `rBin7…` under medium 4. Each of those media also carries a second disc ID.

| Property | Disc 3 (R1) | Disc 4 (R2) | Evidence |
|---|---|---|---|
| Track count | 16, all audio | 16, all audio | R1:FA1.log:27 and R2:FA2.log:27; CDDB IDs end in `0x10`; every `-j` record has `cd_tracks: 16` with `data_ripped: false` |
| TOC | Track 1 at sector 0; track 16 runs 245135-260089 | Track 1 at sector 0; track 16 runs 258525-277079 | R1:FA1 (EAC-compatible).log:38-57; R2:FA2 (EAC-compatible).log:38-57 |
| CD-R? | **Not determined by the drive** | **Not determined by the drive** | See below |
| Enhanced CD | No | No | No data track in the TOC, `cd_tracks` or the `-j` records |
| CD-TEXT | None reported by libcdio | None reported by libcdio | R1:FA1.log:17; R2:FA2.log:17; every `-j` record has `cdtext.status` "none reported by libcdio" |
| Pre-emphasis | None, all 16 tracks | None, all 16 tracks | R1:FA1.log:78 and the other track blocks; `-j` `preemphasis: "none"` on all 118 track entries read |
| Hidden track before track 1 | No | No | Track 1: `Pregap source: lead-in`, 150 frames, `Start LSN: 0` (R1:FA1.log:93-94; R2:FA2.log:97-98) |
| AccurateRip | Found; per-track maximum confidence 23-24 | Found; per-track maximum confidence 25-28 | R1:FA1.log:35; R2:FA2.log:35 |
| CTDB | In CTDB with 5 entries: best confidence 52, total 56 | In CTDB with 4 entries: best confidence 65, total 68 | R1:SR1.platterpus.json:2657-2664; R2:FA2.platterpus.json:2248-2255 |
| Disc ISRCs | None on any track, even after 200 Q frames | Read on 13 of 16 tracks (all but 4, 8 and 15) | Section 3c |

**CD-R.** The `Recordable:` line reads `unknown (profile 0xffff is not a CD profile)` on both discs (R1:FA1.log:16; R2:FA2.log:16).

- The same value appears on The Police disc in the 2026-10-21 bundles, so this drive, or libcdio's `mmc_get_disctype`, never reports a CD profile. On this rig the line cannot answer the question.
- The other evidence points to a pressed CD: AccurateRip confidence 24-28, CTDB entries that match, and MusicBrainz's format "CD".

## 2. Every failed step

No failed step comes from a fork defect: `.26` did what its contract says on every path the runs reached. The counts in `REP` are R1 pass 480, fail 4, unreachable 1, info 12; and R2 pass 481, fail 2, blocked 1, unreachable 1, info 12.

R2's MANIFEST says "3 FAILURE(S)" (R2:MANIFEST.txt:37), which counts the blocked step as a failure. Its own verdict line keeps them apart (R2:MANIFEST.txt:39).

| Run | Step | What failed | Cause | Owner | Both runs? | Tracked? |
|---|---|---|---|---|---|---|
| R1 | L726 `expect-album-audit` (section F) | "completion warned: … 1 ripping errors" (R1:TR:457-458; R1:REP:2042) | **Disc and script.** Track 16 has a real paranoia skip at LSN 248743 (R1:FA1.platterpus.json:1242). Its kept read is unverified, and the chase found no verified read (R1:FA1.platterpus.json:1371-1373). The product's warning is correct. The script asserts a clean self-audit on a disc that will not read clean, although its own comment says read instability is "deliberately not graded" (`fullacceptance.txt:686-689`). `grade_album_audit` excuses only the open-round warning. | Platterpus (script or grader) | No. R2's L726 fails for another reason. | No |
| R1 | L730 `expect-cover-art` (F) | "the report says 0 file(s) took the cover; the files hold 16" (R1:TR:465-466) | **Platterpus defect: a race.** See the note below the table. | Platterpus | No. R2's L730 is blocked and its L910 passes (R2:TR:673). | No |
| R1 | L910 `expect-cover-art` (J) | "…0 file(s)…; the files hold 2" (R1:TR:683-684) | Same race: graded at 12:30:55Z (R1:APP:18410), result recorded at 12:31:55Z (R1:APP:18501-18502). | Platterpus | Failed in R1 only. In R2 the cover result landed about 50 s after post-rip began, before grading. | No |
| R1 | L1274 `expect-album-audit` (N) | "completion warned: … 2 ripping errors" (R1:TR:1116; R1:REP:4889) | **Platterpus defect.** The chase replaced track 16 with a read AccurateRip verifies (R1:SR1.platterpus-addendum.txt:20-25), and the verdict is "Bit-perfect: all 16 tracks" (R1:SR1.platterpus.json:269). Yet `health_status` stays "2 ripping errors" (R1:SR1.platterpus.json:657), counted from the superseded `-Z` read. `rip_audit.py:425-429` warns on any `health_status` other than "No errors occurred". The EAC-layout log likewise prints "All tracks accurately ripped" over "2 ripping errors" (R1:SR1 (EAC-compatible).log:292,294). | Platterpus | No. R2's L1274 fails for another reason. | No |
| R2 | L726 and L1274 `expect-album-audit` | "cue_integrity warned: … track 10: cue USZO10001709 vs sent USZ010001709" (R2:TR:450-451, 1103-1104) | **Platterpus defect.** See the note below the table. | Platterpus | Yes, both steps in R2. R1's disc carries no ISRCs, so it cannot show this. | No |
| R2 | L730 `expect-cover-art`, **blocked** | "none was fetched: network HTTP 500" (R2:TR:458-459) | **Rig/network.** The Cover Art Archive returned HTTP 500 for the front cover (R2:APP:27591; R2:FA2.platterpus.json:2466-2472). Booklet images from the same archive did save 54 s later (R2:APP:27603), so the message "could not reach the Cover Art Archive" (R2:APP:27604) overstates it. | External | No | The class is recorded in TASKS R17 (CAA HTTP 500 on 2026-10-14) |
| Both | L571 `expect-offset-refusal`, unreachable, not a failure | The drive is in AccurateRip's list (R1:TR:387, R2:TR:381) | Rig | n/a | Yes | Yes: TASKS, "Permutations the acceptance test still does not run, (a)" |

**The cover-art race (R1 L730 and L910).** The FLACs already carry the front cover when the grader reads them.

- The report's `cover_art` block, with `embedded_count`, is written only after Platterpus downloads this release's 23-25 booklet scans. That takes 60-120 s here.
- The step graded at 12:18:09Z (R1:APP:17625). The result was recorded as "late" at 12:19:40Z (R1:APP:17718-17719), and the report now says 16 (R1:FA1.platterpus.json:2660).
- `settle_state()` (`uiscript/artifact_grading.py`) waits for `outcome` and `verification.gates`, not for `cover_art`.
- The defect is latent. It shows on a release with many CAA images, and The Police release does not have them.

**The cue ISRC check under `--prefer-disc-isrc` (R2 L726 and L1274).**

- `--prefer-disc-isrc` was sent (R2:FA2.platterpus.json:472), so the files and the cue carry the disc's code `USZO10001709` (R2:FA2.log:792; R2:FA2.cue:77).
- MusicBrainz has `USZ010001709`, with a digit zero where the disc has a letter O.
- `cue_validate._check_isrcs` compares the cue with the ISRCs **sent**, not with those **written**. The report already knows the difference: `agreement: "differ"`, `written: USZO10001709` (R2:FA2.platterpus.json:568-572), and the `isrc_disc_differs` info issue (:313).
- The fork's behaviour is correct.

TASKS R20 covers ISRC provenance, not this check.

### Defects that failed no step

1. **The derived-file verify runs before the transcode writes its files.** It gives up after about 60 s while the transcode waits behind the cover-art and booklet fetch.
   - R1: MP3, WavPack and WAV all report "not run — no … files found to verify". For example, the verify was skipped at 12:38:35Z (R1:APP:18991) and the transcode wrote its files at 12:39:26Z (R1:APP:18999). WavPack and WAV: R1:APP:19336/19342 and 19679/19686.
   - R2: MP3 is the same (R2:APP:29047). WavPack and WAV ran and passed, because their transcode finished first (R2:APP:29373-29384).
   - So no derived file was verified in R1, and no MP3 in either run. `expect-verification` passed every time, because the gate honestly says "not run". This is Platterpus's, and it is untracked.
2. **The verified-read chase's `-j` records are missing from the bundle.** The chase's 10 cyanrip invocations in R1 each passed `--diagnostics` (for example `cyanrip-diagnostics-20261022T121023Z.json`; R1:FA1.platterpus-verified-read.txt:2). None is in `ripperdiagnostics/`, and the MANIFEST says "missing none" (R1:MANIFEST.txt:33-34).
   - The positions of the skips in chase reads 1, 3 and 4 of SR1 and in read 1 of FA1 are therefore lost.
   - TASKS R9 fixed this for the securing pass only. The chase path is untracked.
3. **SR1's track 16 mixes two reads.** Its CRC, 3EACDE74, and its AccurateRip result come from chase read 5, but its speed (0.55x), elapsed time (362.25 s) and paranoia counters (`SKIP: 1`) come from the superseded `-Z` read (R1:SR1.platterpus.json:2596-2636; R1:SR1.log:1424-1430). The kept read ran at 4.8x in 41.53 s with no skip (R1:SR1.platterpus-verified-read.txt:822-823, 840-901). The EAC-layout log repeats the mix: "Extraction speed 0.6 X … 0:06:02 … Copy CRC 3EACDE74" (R1:SR1 (EAC-compatible).log:282-286).
4. **`expect-pregaps-agree` (P4) misses two kinds of log.** It runs before the P5 timing rips, so in R2 it reported "11 logs … identical" (R2:TR:1971-1974) without seeing the `.25` logs that omit track 5's pregap (section 3b). It also sets aside any log whose `Gaps:` block holds an `unknown` line (R1:TR:1970-1974, three logs).
5. **Minor.** `distinct_reads_seen: 4` counts only the `Repeating ripping` values, but each securing pass read five distinct values (R1:SR1.platterpus.json:1594; R1:FA1.platterpus-securing-pass.txt:60-68,108). `expect-accuraterip` labels track 16's one-frame (frame 450) match `offset-variant` (R1:TR:459-460).

## 3. Consistency

### 3a. Per-track checksums and AccurateRip, within each run

**R1, disc 3.** Every read was parsed: album logs, both securing passes, all 10 chase reads, and both `.25` and `.26`.

- **Tracks 1-15:** one CRC per track across every read (track 1 has 15 reads, track 2 has 11, track 3 has 6, tracks 4-15 have 2 each). Every read is AccurateRip v1 and v2 accurate, at the same values. Examples: track 1 `C2691C02`, v2 `E03D140D` at confidence 24 (R1:FA1.log:95-101); track 15 `3ECA7369`, v2 `0AA80B51`.
- **Track 16:** 14 reads produced **14 different CRCs**. Thirteen are unverified and match only on frame 450 (`F81ED370`, confidence 24). One, chase read 5 of SR1 (`3EACDE74`, v2 `B337E973` at confidence 24), is verified (R1:SR1.platterpus-verified-read.txt:831-835). The other 13 reads and where they appear:
  - FA1: `8B597546` (R1:FA1.log:1275), `60CB92F8` (R1:FA1.platterpus-securing-pass.txt:108), and five chase reads, none verified (R1:FA1.platterpus-verified-read.txt:101,284,465,646,827).
  - SR1: `0FC7769D` (R1:SR1.log:1390), `808A9514` (R1:SR1.platterpus-securing-pass.txt:108), and chase reads 1-4.
- Each of the three `-Z` passes on track 16 hit the repeat limit with every read different: "at most 1 read agreed" (R1:SR1.log:1350; both securing passes at :68). Track 16 is physically marginal on this disc.

**R2, disc 4.** All 16 tracks have one CRC each across every read (track 1 has 15 reads, track 2 has 11, track 3 has 6, the rest 2), all AccurateRip accurate, with no securing pass and no chase. "Tracks ripped accurately: 16/16" (R2:FA2.log:1348); "Ripping errors: 0" (R2:FA2.log:1355).

### 3b. Pregaps

`.26`'s two-search clause ("two searches read %i and %i frames", `cyanrip_log.c:439-440`) printed **nowhere**: every `Pregap source:` line is `lead-in` (30) or `sub-channel (not signalled by TOC)` (98). Wherever both searches ran, they agreed.

**R1** has 27 cyanrip invocations: 25 by `.26` and 2 by `.25`.

- All 27 `Gaps:` lists agree on 75, 110, 157, 132, 140, 110, 140, 178, 183 and 108 frames for tracks 3, 4, 5, 6, 8, 9, 10, 13, 14 and 15 (R1:FA1.log:46-56).
- In 3 of the 25 `.26` invocations, track 16's search **failed**, and the list says so: "pregap of track 16 unknown (sub-channel CRC mismatches)". This is in `cancel me … CD3.log:57`, `derived wavpack … CD3.log:57` and `r16deemphon/Unknown disc (BKYF).log:54`.
- The other 22 list no pregap for track 16. All 14 of track 16's own blocks print 0 frames.
- No track's measured value varied.

**R2** has 15 invocations: 13 by `.26` and 2 by `.25`.

- All 13 `.26` lists are identical and include `175 frame pregap in track 5` (R2:FA2.log:49; track block R2:FA2.log:411).
- **Both `.25` lists omit track 5** (R2:TA1_2:44-47, R2:TA2_2:44-47). Same disc, same run.

### 3c. The disc's ISRCs (`Disc ISRC:` lines)

**R1, disc 3.** Every `.26` read of every track says "none (libcdio returned none, also after reading 200 Q frames of the track, none an ISRC frame)" (R1:FA1.log:79 and the other blocks). The two `.25` timing logs say "none (libcdio returned none)". So the drive's Q frames carry no ISRC on this disc. The files carry MusicBrainz's codes for 9 tracks.

**R2, disc 4.**

- `.26` read codes for tracks 1-3, 5-7, 9-14 and 16 (R2:FA2.log:83, 162, 241, 398, 477, 556, 713, 792, 871, 950, 1029, 1108, 1266) and "none … 200 Q frames" for tracks 4, 8 and 15 (R2:FA2.log:320, 635, 1187).
- The codes are consistent across every read of each track. For example, track 1 has `USRO28102801` in all 13 `.26` reads.
- **`.25`, in the same run, read none for tracks 1-3** (R2:TA1_2:80,159; the same in A2).
- Disc against MusicBrainz:
  - Track 10: disc `USZO10001709` (letter O), MusicBrainz `USZ010001709` (digit zero).
  - Track 15: the disc has none and MusicBrainz has `CAW119901677`, which the files carry.
  - All other tracks agree.

### 3d. Error positions (`-j` `error_positions`)

**R1.** Every position is a skip, and every one is on track 16, whose range is 245135-260089:

| Read | Positions (LSN) | Evidence |
|---|---|---|
| FA1 album pass | 248743 | R1:ripperdiagnostics/cyanrip-diagnostics-20261022T114605Z.json:55 |
| FA1 securing pass | 250438, 250364 | …120418Z-securingpass.json:55 |
| SR1 album pass | 250715, 251158 | …124948Z.json:55 |
| SR1 securing pass | 250401 | …134436Z-securingpass.json:55 |

- The positions vary from read to read but stay within LSN 248743-251158, about 48-80 s into the track.
- The report repeats the album-pass positions (R1:FA1.platterpus.json:406, 1242).
- Every other track and record is empty. The cancelled rip has `ripping_errors: 1` with no skip.

**R2.** Every record is empty, which is consistent with no errors.

### 3e. CTDB per track

| Rip | Whole disc | Per track |
|---|---|---|
| R1 FA1 | `no_match` "at any alignment within ±5,879 samples" | Tracks 1-15 match (confidence 54-56); track 16 `differs` (CRC 26521651). R1:FA1.platterpus.json:2440-2459, 2627-2628 |
| R1 SR1, after the chase | `match`, confidence 52, offset 0 | All 16 match; track 16 at confidence 53 (CRC 0DF70A39). R1:SR1.platterpus.json:2657-2664 |
| R2 FA2 and SR2 | `match`, confidence 65, offset 0 | All 16 match at 67-68, with identical per-track CRCs in both rips. R2:FA2.platterpus.json:2248-2435 |

### Every difference between the two runs

- **Caused by the medium:**
  - The disc itself: DiscID, TOC, length, AccurateRip ID, titles and ISRCs.
  - Every CRC and AccurateRip value.
  - AccurateRip confidence: 23-24 against 25-28.
  - CTDB: 5 entries at 52 against 4 entries at 65.
  - Pregap sets.
  - ISRCs: none against 13 of 16.
  - Track 16's damage, which only disc 3 has. It caused R1's securing passes, chases, skips and error positions, while R2 had none of these.
- **Caused by the run:**
  - Cover-art fetch: R1 succeeded but late; R2 hit HTTP 500 on F and was on time on J. This gives L730 fail against blocked, and L910 fail against pass.
  - Derived verify: 0 of 3 ran in R1, 2 of 3 in R2.
  - Cache probe: 140 sectors against 137 (R1:TR:1477; R2:TR:1475).
  - P5 timing ratios: 0.354 and 0.354 in R1 (R1:TR:2180-2182), against 0.197 and 0.193 in R2 (R2:TR:2180-2182). `.25` took about 698 s for tracks 1-3 on both discs, at roughly 1x; `.26` read at 2.5-6x.
  - Bundle size: 17 `-j` records and 136 files in R1, against 15 and 129 in R2 (MANIFEST:33, :48).

## 4. The known fixes

| # | Fix | Verdict | Evidence |
|---|---|---|---|
| 1 | Second read on a disc AccurateRip doesn't know | **NOT EXERCISED** | Both discs are in AccurateRip (R1:FA1.log:35; R2:FA2.log:35) and `accuraterip_standing` is `in_database` (R1:FA1.platterpus.json:1433). The retries that did happen were triggered by `accuraterip` and `instability`, never by `second_read`. |
| 2 | Keep the read AccurateRip verifies at the repeat limit | **PROVEN** on Platterpus's chase (R7). The fork's `--prefer-accuraterip-match` is `.27` and **NOT EXERCISED**. | SR1 track 16: two `-Z` passes at the limit, then chase read 5 verified at v2 confidence 24 and was kept (R1:SR1.platterpus.json:1590-1642; addendum :20-25; EAC log :285-287; CTDB track 16 match). FA1: five chase reads, none verified, the first read kept and nothing falsely replaced (R1:FA1.platterpus.json:1371-1373). Faults beside it: L1274 (section 2) and defects 2 and 3. |
| 3 | No "No errors occurred" over an unclean read | **PROVEN** for a counted skip. The uncounted case is **NOT EXERCISED**. | FA1: `health_status` "1 ripping errors" (R1:FA1.platterpus.json:440); EAC log "Copy NOT confirmed … 1 ripping errors" (R1:FA1 (EAC-compatible).log:270-280); `unverified_paranoia_skips` issue (:431). The phrase is printed only on clean rips. The trigger the fix adds, a skip under `Ripping errors: 0`, did not occur: every skip was counted. EAC's "There were errors" wording is not built (lap 3 S11). |
| 4 | An Enhanced CD's data track | **NOT EXERCISED** | No data track on either disc. |
| 5 | The record says which checks ran | **PROVEN** | The gates read from results: `ctdb: "ran"` or "not run — CTDB verifies whole discs…", and `derived: "not run — no mp3 files found to verify"` (R1:DM1:1271). The gates are honest, and that honesty is what exposed defect 1. A check cut short was not exercised. |
| 6 | Error positions | **PROVEN** in R1; empty in R2, which is correct | Section 3d. The `-j` positions, the report's `disc.error_positions` and the issue text agree (R1:FA1.platterpus.json:406, 1242). Gaps: the chase reads' positions are lost (defect 2), and the EAC-layout wording is not built (S10). |
| 7 | CTDB per track and over offsets | **PROVEN** per track. The offset sweep is PROVEN for a no-match at every alignment. A **non-zero pressing offset is NOT EXERCISED**. | Section 3e. FA1 names track 16 alone as differing, and every match was at offset 0. |
| 8 | The disc's ISRCs | **PROVEN** | Disc 4: `.26` read 13 of 16 codes where `.25`, in the same run on the same drive, read none for tracks 1-3 (section 3c). Disc 3: "none … 200 Q frames" on all 16 tracks, which is the STATUS close's other branch. The Police disc, where EAC shows codes, was not re-read. |
| 10 | Pregap stability | **PROVEN on disc 4**, but its **close condition is unmet** | Track 5's 175 frames appear in 13 of 13 `.26` logs and 0 of 2 `.25` logs (section 3b). Disc 3 agrees everywhere. STATUS closes the item only on The Police disc reading 94 and 158 frames, and that disc was not run. Also first seen on a drive: `gaps-undetermined-pregap`'s `unknown` line, in 3 R1 logs (STATUS:12). |
| 11 | The log says whether the offset is AccurateRip's for the drive | **The report proves it; the log does not say it** | `read_offset_check: matches`, "+667, matches the AccurateRip drive database for PIONEER BD-RW BDR-209D", reconfirmed by AccurateRip on 15 of 16 and 16 of 16 tracks (R1:FA1.platterpus.json:1289-1294; R1:SR1.platterpus.json:1510-1515). The EAC-layout line is still bare "Read offset correction : 667" (R1:FA1 (EAC-compatible).log:22), awaiting lap 3 S12. |
| 12 | No "not in the database" for a disc AccurateRip holds | **PROVEN** | FA1's headline names the one-frame match (R1:FA1.platterpus.json:267). No report or EAC log in either run contains "not in the database". |
| — | `Accurate stream:` and `Recordable:` lines | **PROVEN** printed and parsed; `Recordable:` is uninformative | Both lines are in all 38 `.26` logs and absent from the 4 `.25` logs, which report `not_present`. The values are parsed (R1:FA1.platterpus.json:1306-1309). `Recordable:` is `0xffff` on every disc this rig has run, so it never answers CD-R. The EAC-layout line still says "Utilize accurate stream : (not reported by the ripper)" (R1:FA1 (EAC-compatible).log:18). |
| — | The derived MP3's ReplayGain, measured on the MP3 | **PROVEN, on the record only** | `measured_on: "the MP3 itself (ffmpeg ebur128, true peak)"`, 2 of 2 tracks and the album tagged, in both runs (R1:DM1:1289). The MP3s are not in the bundle and the app log prints no gain values, so the values cannot be checked independently. The MP3 decode check did not run in either run (defect 1). |

### Fork STATUS items these runs bear on (for the fork's reading)

- `disc-isrc-read` (STATUS:15) meets its close condition: codes on disc 4, and "the drive's Q frames carry none" on disc 3.
- `gaps-undetermined-pregap` (STATUS:12) printed on a drive for the first time.
- `error-positions` (STATUS:21) is non-empty on a drive for the first time.
- `hardware-unverified` (STATUS:27): "a paranoia skip on a drive" now has evidence. There are 8 skips across 4 `-j` records.
- `repeat-limit-last-read` (STATUS:11): the limit was hit 3 times, each time with 5 distinct reads. The newest read was kept, so the clause correctly stayed silent.
- `subchannel-pregap-varies` (STATUS:20): supported on disc 4, but its stated close condition, The Police disc, is unmet.
- `recordable-medium-line` (STATUS:24): reads `0xffff` on three discs. Whether that comes from the drive or from libcdio's `mmc_get_disctype` parsing is not determinable from this evidence.
