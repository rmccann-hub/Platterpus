# Full acceptance run 20261021T113505Z: findings

Run: Platterpus 0.7.112 (9bf0cd3) with ripper `.26` (ca0f097), reference disc (The Police,
14 tracks), started 2026-10-21 11:35:05 UTC. Verdict: pass 424, fail 60, unreachable 1, info 12.
Read-only analysis. Sources: Platterpus `origin/main` bba81563 (its acceptance script is
byte-identical to the `script_source` in `session/run/report.json`), and the fork's
`origin/platterpus-fork` fc73b4d.

## Path abbreviations (all bundle-relative)

- `T` = `session/run/transcript.txt`; `RJ` = `session/run/report.json`
- `AL` = `session/artifacts/02platterpus/log.txt` (app log; its times are UTC-04:00, converted to
  UTC below). `AL1` = `session/zz-applog-rotations/03platterpus/log.txt.1`
- `F/` = `album/full acceptance_ angle_bracket 20261021t11__terpus-fork-gca0f097/`. Section F,
  the whole-disc rip in dynamic mode. Files: `F.log` (the ripper log, `…gca0f097.log`), `F.sec`
  (`…platterpus-securing-pass.txt`), `F.add` (`…platterpus-addendum.txt`), `F.json`, `F.cue`,
  and `F.eac` (`… (EAC-compatible).log`)
- `N/` = `album/secure reread 20261021t113505 platterpus-fork-gca0f097/`. Section N, archival,
  with uniform `-Z 2`. Files `N.log`, `N.json`, `N.cue`, `N.eac`, on the same pattern.
- `K3/` = `album/derived wav …gca0f097/`
- `A1/`, `A2/` = `album/timing A1|A2 … platterpus-fork-g5f1d036/` (`.25`); `B1/`, `B2/` =
  `album/timing B1|B2 … platterpus-fork-gca0f097/` (`.26`)
- `R16on/`, `R16off/` = `album/r16deemphon/`, `album/r16deemphoff/` (`Unknown disc (PNTI).log`)
- `P@` = `platterpus@bba81563:`; `C@` = `cyanrip@fc73b4d:`

## 1. The 60 failures: four causes

| Group | Count | Script lines | Root cause | Owner | New? |
|---|---|---|---|---|---|
| A | 3 | L726, L1109, L1274 | Platterpus defect: the cue audit ignores `--prefer-disc-isrc` | Platterpus | New |
| B | 2 | L729, L730 | Rig trigger (a drive-status flap), plus a Platterpus grader defect | Platterpus | New |
| C | 16 | L782–L864 (sections H, I) | Cascade of B: the auto-rescan opened a 4-candidate release picker that no step answered | Platterpus (app plus harness) | New |
| D | 39 | L897–L1086 (sections J, J2, K1, K2) | Platterpus harness race: `pick-release` answered C's stale picker, and `rip` fired while J's own rescan was still running | Platterpus (harness) | New |

3 + 2 + 16 + 39 = 60. One step was unreachable: E2 L571. It was known beforehand (TASKS
"Permutations the acceptance test still does not run", (a); T:389). That makes 48 of the 60
failures B's knock-on effects, and the other 12 (A, B and the 10 in C before the cancel) come
from two defects. **No failure is a fork defect, and none is a defect in the audio.**

### A. The cue ISRC round-trip check counts the disc's own ISRCs as a mismatch (3)

- **Expected:** `expect-album-audit` passes. **Happened:** `cue_integrity warned: cue sheet — 14
  ISRC(s) differ from what we sent: track 1: cue GBAAM7800003 vs sent GBAAM0201086…`
  (T:460-461 for L726, T:971 for L1109, which is K3 and 2 tracks, and T:1130 for L1274, which is
  N; AL:660).
- **What the files hold:** F's argv sends `--prefer-disc-isrc`, along with MusicBrainz ISRCs in
  `-t … isrc=GBAAM0201086` (F.log:2). `.26` reads the disc's codes (`Disc ISRC: GBAAM7800003`,
  F.log:78) and, as `--prefer-disc-isrc` asks, writes them to the tags and the cue
  (F.log:117; F.cue:16-100). The report itself records this correctly as info only:
  `isrc_disc_differs … the files carry GBAAM7800003` (F.json:322-387).
- **Root cause:** a Platterpus defect. `_check_isrcs` compares the cue with the ISRCs Platterpus
  *sent*, with no case for `--prefer-disc-isrc` (P@src/platterpus/cue_validate.py:575-663,
  mismatch at :619-620). It never fired before because `.25` read no disc ISRC on this drive
  (A1.log:76 `Disc ISRC: none (libcdio returned none)`). `.26` fixing item 8 is what exposed it.
- **Fix:** when the argv carries `--prefer-disc-isrc` and the report holds a valid disc ISRC for a
  track, expect the disc's code in the cue. This is Platterpus's fix. TASKS R20 (P@TASKS.md:88)
  covers the report and argv but does not name the cue check.

### B. The tag and cover graders read the live window, which a drive-status flap had cleared (2)

- **Timeline (UTC):** F's rip finished at 12:01:58 (AL:610). Post-rip checks ran, FLAC verify
  passed (AL:647), and CTDB matched (AL:651). At **12:02:39** the drive's status poll read
  `disc -> open` (AL:649), then `disc removed … — clearing the disc view` (AL:650),
  `open -> unavailable` (AL:653) and, 2.5 s later, `unavailable -> disc … auto-rescanning`
  (AL:665-666). Nothing asked for an eject: `auto_eject_after_rip off` (T:31).
- **L729 expect-tags (T:466):** `track 1: ALBUM is ['full acceptance: angle<bracket …'], chosen
  ''; … the window has no row for it`. The FLAC is in fact right
  (`session/run/tags0729.txt:10-17`). The grader takes "chosen" from the window's track table
  (P@src/platterpus/uiscript/artifact_verbs.py:173-182), which the flap had just emptied.
- **L730 expect-cover-art (T:468):** `mode 'embed' embeds nothing, yet track(s) 1…14 carry a
  picture`. The grader takes `release_id` from the window (artifact_verbs.py:216). The flap
  cleared it, and `plan_actions` returns (False, False) for an empty id
  (P@src/platterpus/adapters/cover_art.py:434-454). The files do hold the cover
  (tags0729.txt:30; AL:636 `Cover art: embedded in 14 track(s)`).
- **Root cause:** the trigger is the rig's drive. It reported tray-open for one poll. The same
  2.4 s open→unavailable→disc pattern recurs while the app is idle in earlier logs (AL1:53913,
  63418, 72444, 72454, 72463). Its cause cannot be found from the bundle. The defects it exposed
  are Platterpus's:
  1. `MediaWatcher` treats a single OPEN reading as a removal, with no confirming second read
     (P@src/platterpus/drive_media.py:76, 123, 209-231).
  2. The graders compare the rip's files with mutable window state instead of with the rip's own
     record (its report or argv).
- **Owner:** Platterpus. Neither TASKS nor STATUS names this; TASKS:7792 describes the watcher
  without noting the flap.

### C. Sections H and I: blocked behind the release picker the auto-rescan opened (16)

- At 12:02:57 the auto-rescan's MusicBrainz lookup returned 4 candidates and opened the modal
  picker (AL:681-682). The disc view was still empty, so:
  - L782 and L825: `no tracks are loaded` (T:503, 554)
  - L791: no track 1 (T:507)
  - L792: Start not enabled (T:509)
  - L793: waited 120 s for "Album already ripped" while the picker was open (T:511)
  - L794: nothing to wait for (T:513)
  - L827: refused to press Start behind the picker (T:558)
  - L831: `no rip is running` (T:572)
  - L841: the status line still read F's `Done — all 14 tracks…` (T:577)
  - L798, L802-L805, L860, L864: `no rip has finished since this section asked for one`
    (T:540-548, 581-583)
- **Root cause:** a cascade of B. The script calls `pick-release` only after its own `rescan`
  steps (E, J L893, N L1242), and an unplanned rescan has no step to answer it. **Owner:**
  Platterpus. The direct fix is B's debounce. The harness could also fail fast on a picker it
  didn't expect, instead of letting 16 steps time out behind it. Losses from C: H's overwrite
  prompt (the per-track `-t` escaping, `E=MC2…`) and section I's whole cancel path, including
  `sigterm-world` (T:587: NOT DETERMINED) and S25. None of them was tested.

### D. Sections J, J2, K1 and K2: rips started while J's own rescan was still running (39)

- L892 `rescan` started a new DiscInfoWorker at 12:08:35 (AL:702). L893 `pick-release 1 120`
  passed in 0.6 s (T:643), but it answered **C's stale picker**: `user chose 65282302… after
  338.4s` (AL:704-705). The new scan was still running cyanrip `-I` and its MusicBrainz lookup
  until **12:08:49** (AL:770: `4 candidates … again, but a release was already chosen … not
  re-opening`).
- Within those 14 s the script ran four rips. Each one failed on `Start button is not enabled`:
  L897, L965, L1045, L1073 (T:651, 743, 803, 877; AL:708, 725, 743, 757). All their graders
  failed too (T:653-691, 745-761, 805-843, 879-904). K3's rip was the next one, at 12:08:51
  (AL:795), and it succeeded (T:938-940).
- **Root cause:** a Platterpus harness defect. `rip` fails at once while a scan is active instead
  of waiting a bounded time, and `pick-release` takes any open picker, including one an earlier
  scan opened. On a clean run the fresh picker gates the scan, so this only shows up after C.
  **Owner:** Platterpus (uiscript). New. TASKS:6857 records an older, different "Start not
  enabled" cause, which has been fixed.
- **Untested as a result:** the drive-open proof (J), the J2 permutations (no `-r`/`-Z`, fixed
  speed, library move, **`--prefer-disc-isrc` off**), MP3 (K1) and WavPack (K2).

## 2. The known fixes on this disc

| # | Item | Verdict | Evidence |
|---|---|---|---|
| 2 | Keep the AccurateRip-verified read, not the majority (the 0.7.112 chase) | **NOT EXERCISED as shipped; the goal is CONTRADICTED in N** | F: the chase on track 5 reads `skipped_reads_agreed`, `distinct_reads_seen 1` (F.json:1251-1252), with E0036697 every time (F.log:402, F.sec:143-147). Track 3 was saved by the securing pass, not the chase (F.json:1232-1241; F.add:20-25). No log hits the repeat limit. **N:** track 3's reads were `59D352DD` (the AR-verified value), then `3D8FCF0C` three times (N.log:225-231). The rip shipped `3D8FCF0C`, which matched on frame 450 only (N.log:270-275). N's `retried_tracks` is `[]`, mode `uniform` (N.json:1443-1445), because the chase runs only over the securing pass's retried tracks (P@src/platterpus/workers/rip_worker.py:3226-3238; P@src/platterpus/verified_read_chase.py:14-45). So the archival path has no chase. The fork's `--prefer-accuraterip-match` (`.27`, unreleased; C@docs/handshake/STATUS.md:30) acts only at the repeat limit, and N converged after 4 reads, before it. |
| 3 | No "No errors occurred" over an unclean read | **NOT EXERCISED** | The fix fires on paranoia skips or an error line under `Ripping errors: 0` (P@src/platterpus/rip_health.py:1-20; P@TASKS.md:1290-1320). No log has either: every count is 0, and every `error_positions` entry is empty (F.json:691 onward). Outside its scope: N.json:612 and N.eac:266 still read "No errors occurred", and N.eac:96-99 reads `Test and Copy CRC identical — confirmed across 4 secure re-reads … Copy OK` for track 3, whose first read disagreed. That wording overstates the case (Platterpus). |
| 5 | The record says which checks ran | **PROVEN (pass, fail and not-run arms); cut-short NOT EXERCISED** | K3: `ctdb: not run — CTDB verifies whole discs…`, `flac_integrity: ran — passed`, `derived: ran — passed` (K3 json:1135-1139). F: `flac_integrity: ran — passed`, `ctdb: ran` beside a verdict, by design (P@src/platterpus/verification_gates.py:131-157). No give-up happened. |
| 6 | Error positions in the report | **PROVEN in structure; positions NOT EXERCISED** | `disc.error_positions` is read from `.26`'s `-j`, with `state: read`, positions `[]`, 0 read errors and 0 skips, and `count_agrees_with_counters: true` on every track (F.json:691 onward, N.json:902 onward). The disc gave no error, and the EAC-layout log is unchanged by design. |
| 7 | CTDB per track, over ±5879 | **PROVEN on hardware; a nonzero-offset match NOT EXERCISED** | F: `offset_range 5879`, `matched_offset 0`, `Per track: 13 of 14 agree with CTDB; track 5 agrees only with a minority (2 of 1,518)` (F.json:2151-2157, 2267). N: `no_match … Per track: 12 of 14 agree; tracks 3 and 5 differ from every entry` (N.json:2340-2346, 2456). |
| 8 | The disc's ISRCs | **PROVEN** | `.26` read 14 of 14 codes on every `.26` rip (F.log:78…1068; N.log:84…; B1.log:78; K3; R16on.log:76). The cue matches EAC's cue track for track (F.cue:16-100 against P@output_reference/EAC_flac/eac_baseline_police_classics.cue:13-111; track 1 GBAAM7800003, track 14 GBAAM9500177). `.25` in this same run read none (A1.log:76). The fork's close condition is met (C@docs/handshake/STATUS.md:15). It also exposed group A. |
| 10 | Pregap stability | **Track 4: consistent (158 in 8 of 8 `.26` logs). Track 9: CONTRADICTED** | EAC's value for track 9 is 94: INDEX 00 03:44:11 on a 16,905-frame track 8 (EAC cue:74). `.25` read 94 twice (A1.log:50, A2.log:50). `.26` read **95** in 3 logs (F.sec:52, N.log:52, K3 log:52) and `pregap of track 9 unknown (sub-channel CRC mismatches)` in 5 (F.log:52, B1.log:52, B2.log:52, R16on.log:49, R16off.log:49). It read 94 in **none**. No `two searches read` clause printed anywhere. The fork's stated close condition, "reads 94 and 158 in every log" (C@docs/handshake/STATUS.md:20; C@docs/handshake/round-36-lap-04.md:81), fails. The cue for F has no INDEX 00 for track 9 (F.cue:69-70), and N's says 03:44:10, which is 95 (N.cue:69). Owner: the fork. Side effect: the new "unknown" line printed on a drive for the first time (STATUS.md:12 `gaps-undetermined-pregap`), and Platterpus's `expect-pregaps-agree` set those 3 logs aside as unreadable (T:1997). |
| 11 | Whether the read offset is AccurateRip's | **PROVEN in the report and results pane; the log half not shipped** | `read_offset_check: matches, applied 667, listed 667, AR re-confirms 13 of 14` (F.json:1160 onward; AL:616). The cyanrip log says only `Offset: +667 samples` (F.log:10), and the EAC-layout log says `Read offset correction : 667` (F.eac:22). Both are as planned (P@TASKS.md:125, P2 #6). |
| 12 | No "not in the database" for a disc AccurateRip holds | **PROVEN** | N had the old trigger, 12 of 14 verified. Its verdict reads `…on the other 2, only one frame matched` (N.json:259 onward); F's reads the same way (T:577). The phrase appears nowhere in the bundle outside the script's comments. The "differs from AccurateRip's entry" arm was NOT EXERCISED: every failing track matched frame 450. |
| — | `Accurate stream:` | **PROVEN as printed and parsed; one Platterpus gap** | `Accurate stream: declared supported by drive (capabilities page, not measured)` (F.log:15) maps to `rip.accurate_stream: declared_supported` (F.json:1178). The EAC-layout log still says `Utilize accurate stream : (not reported by the ripper)` (F.eac:18, N.eac:18). That is now false. It may be held back on purpose until the wording is agreed with the fork (unsure). |
| — | `Recordable:` | **Printed, but undetermined on this drive** | `Recordable: unknown (profile 0xffff is not a CD profile)` on every `.26` log (F.log:16), maps to `recordable: unknown` (F.json:1180). The fork's lap 1 S5 expects `no, CD-ROM (drive's current profile)` for a pressed CD (C@docs/handshake/round-36-lap-01.md:59). Owner: the fork, to find out whether the BDR-209D really reports 0xFFFF or the profile is parsed wrongly. |

## 3. Accuracy

Track 3's AccurateRip-verified value is **59D352DD** (v1 3C8BDDD2, confidence 128; v2 96DF8C22,
confidence 200; F.sec:102-106), which matches the repo's records
(P@docs/handshake/inbound/round-35-lap-15.md:78). Track 5's is **C96464AB**, and no read in this
run produced it.

| Rip (build) | Verified | Not verified (frame 450 only) | Shipped CRCs of tracks 3 and 5 |
|---|---|---|---|
| F album pass (`.26`, about 3.5x) | 1, 2, 4, 6-14 | 3 (2363932F), 5 (E0036697) | first pass (F.log:248-253, 402-407) |
| F as shipped, after the securing pass | 1-4, 6-14 (13 of 14) | 5 | 3 = **59D352DD ✓** (re-read, verified); 5 = **E0036697 ✗**: 3 matching reads, the same as the first pass (F.add:20-32) |
| N archival (`.26`) | 1, 2, 4, 6-14 (12 of 14) | 3, 5 | 3 = **3D8FCF0C ✗**, 5 = **6902BCF0 ✗** (N.log:270-275, 438-443) |
| K3 (`.26`, tracks 1-2) | 1, 2 | — | — |
| A1, A2 (`.25`, about 0.9x) | 1, 2, 3 | — | 3 = 59D352DD ✓ in both (A1.log:246, A2.log:246) |
| B1, B2 (`.26`, about 2.7x) | 1, 2 | 3 | 3 = D7314554 ✗, 2363932F ✗ (B1.log:248, B2.log:248) |
| R16on, R16off (`.26`, track 1) | 1 | — | — |

- **Shipped unverified when a verified read was available: yes, track 3 in N.** Its first `-Z`
  read was 59D352DD, the verified value, and cyanrip converged on 3D8FCF0C instead
  (N.log:225-231). The report raises only `heavy_reread` (N.json:603), and the EAC-layout log
  calls the result "confirmed across 4 secure re-reads… Copy OK".
- Track 5 never verified. The values read were E0036697 (4 times in F) and 6902BCF0 (3 times in
  N). Per track, CTDB puts F's E0036697 with a minority of 2 in 1,518 (F.json:2267) and N's
  6902BCF0 with none.
- **Speed observation (correlation only, small sample).** With the same argv, `.26` reads about
  2.9 times faster than `.25` (ratio 0.348 and 0.346, T:2206). The fork attributes that to
  upstream `7dbe56a` (C@docs/handshake/round-36-lap-01.md:48). Track 3 verified in 2 of 2 `.25`
  rips at 0.9-0.96x, and in 0 of 2 `.26` rips at 2.8x, and F's fast first pass misread it too.
  The fork pre-committed to GO "unless … the timed rip show[s]" a defect
  (C@docs/handshake/round-36-lap-07.md:142), so this deserves a look before the round closes.

## Unsure, or not checked

- What makes the drive report tray-open briefly. Whether it's a kernel or drive power-state
  artefact can't be determined from the bundle.
- Per-track CTDB rows show `offset: -7` while the whole-disc `matched_offset` is 0
  (F.json:2271 onward). Not explained.
- Whether the "unknown (sub-channel CRC mismatches)" track 9 result comes from the two searches
  disagreeing or from one search failing. The log doesn't say.
- `SOURCES.txt` says app-log rotations .7 to .10 were archived, but `MANIFEST.txt:196-199`
  excluded them for the size budget. This is a minor wording inconsistency in the bundle.
- The DIAGNOSTICS warning `cyanrip exited 64` (DIAGNOSTICS.txt:123-143) is the expected negative
  test at L1414/L1416 (T:1514-1535), not a defect.
