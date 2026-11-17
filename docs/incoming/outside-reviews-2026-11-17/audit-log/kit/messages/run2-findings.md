# Run 2 findings: Full acceptance run of 2026-10-21 21:45 UTC (bundle 20261021t214509z)

Read-only analysis. Platterpus 0.7.112 (build 9bf0cd3) with cyanrip `0.9.4-rc3+platterpus.26` (ca0f097).
Source read against: `platterpus@bba81563` and `cyanrip@ca0f097` (the build that ran; the fork tip
`fc73b4d` is cited where it differs). All times are UTC. The app log and the cyanrip logs are written in
local time (UTC-04:00), and every time below has been converted.

Path prefixes used below:

- `B/` = `/tmp/claude-0/-home-user-claude-code-skills/46cfbc1a-d1c5-5a09-bbbb-4b2444266d0f/scratchpad/bundles/20261021t214509z/`
- `ALB/` = `B/album/full acceptance∶ angle‹bracket 20261021t214510 platterpus-fork-gca0f097 CD1`, followed by
  `.log` (the album pass's cyanrip log), `.platterpus-securing-pass.txt`, `.platterpus.json` (the rip
  report) or ` (EAC-compatible).log`
- `APP` = `B/session/artifacts/02platterpus/log.txt` (the live app log; this run is lines 5825 to 14558)
- `DIAG1` = `B/ripperdiagnostics/cyanrip-diagnostics-20261021T214611Z.json` (the album pass's `-j` record)
- `DIAG2` = `B/ripperdiagnostics/cyanrip-diagnostics-20261022T001928Z-securingpass.json`

The seven bundled rotations, `B/session/zz-applog-rotations/*/log.txt.1` to `.7`, cover 2026-10-12 to
2026-10-21 11:50 UTC, which is all before this run. They hold nothing about it. Rotations `.8` to `.10`
were left out for the size budget (`B/MANIFEST.txt:93-95`), and they are older still.

## 0. Which disc it was: confirmed

The disc is *Roots Music: An American Journey*, disc 1 of 4 (Rounder 11661-0501-2, release
`53d0f596-95a3-4e60-b4aa-09f5f7532b1e`). It has 18 tracks, MusicBrainz disc ID
`zxtbw2JgJ.kZBiyIcKOQvn2ZTUM-` and AccurateRip ID `00244e5e-01e6a7bd-000dac12`.

- Evidence in this run: `ALB/.log:2,27-35`, and `B/session/run/transcript.txt:356-369`, where the step
  identified the disc unambiguously with 18 tracks.
- Evidence that it is the same damaged disc as the 2026-10-04 run: the same disc ID appears in
  `platterpus@bba81563:tests/fixtures/evidence/docs/handshake/artifactsround30/round30oct04fullreport.json`.
  `platterpus@bba81563:docs/testing.md:4253-4262` describes that run: track 18 had 2,586 skips and
  section F's six-hour wait ran out with the securing pass still on track 18. **This run repeats that
  failure.**

## 1. Why the rip ran past 6 hours

### Summary

**Track 18's damaged area, read through a drive that cannot be slowed, accounts for 5 h 17 m 50 s of the
rip's 6 h 00 m 10 s (88 %).** The securing pass's `-Z 2 -r 5` is what multiplies it: it re-reads track 18
up to five times, and each read takes about 1.75 to 2.4 hours.

- Pass 1, the album pass, read track 18 once in 2 h 22 m 28 s.
- Pass 2, the securing pass, re-read tracks 11 to 18 and reached track 18's second of up to five reads.
  The harness then stopped it.

**0.7.112's new rule, "re-read singly until one read AccurateRip verifies" (the verified-read chase),
never ran.** It runs only after a securing pass that finished (`rip_worker.py:3137-3149` returns first;
the chase is called at `:3231`). No `[verified read]` line appears anywhere in `APP`, and every
`retried_tracks[].verified_read_chase` is `null` (`ALB/.platterpus.json:5615-5675`).

### The album pass

The album pass ran from 21:46:11 to 00:19:28. It was invoked with `-r 5` and no `-Z` (dynamic mode), as
`ALB/.log:2` and `APP:6000` show.

| Trk | Start (UTC) | Read time | AccurateRip | Paranoia | Source |
|---|---|---|---|---|---|
| 1-10 | 21:46:28-21:50:30 | 17-34 s each, 6.0-8.3x | verified (v2 conf 28-29) | clean | `ALB/.log:64-841` |
| 11 | 21:50:50 | 24.8 s | frame 450 only | FIXUP_ATOM 1012 | `ALB/.log:846-921` |
| 12 | 21:51:16 | 23.6 s | frame 450 only | FIXUP_ATOM 26166 | `:926-1001` |
| 13 | 21:51:41 | 33.9 s | frame 450 only | **1 skip**, LSN 158236 | `:1006-1082` |
| 14 | 21:52:16 | 55.7 s | frame 450 only | — | `:1087-1162` |
| 15 | 21:53:14 | 61.2 s | frame 450 only | **1 skip**, LSN 208410 | `:1167-1244` |
| 16 | 21:54:16 | 22.2 s | frame 450 only | — | `:1249-1324` |
| 17 | 21:54:39 | 139.4 s, 1.4x | frame 450 only | **28 skips** | `:1329-1405` |
| 18 | 21:56:59 | **8548.5 s (2 h 22 m 28 s), 0.031x** | frame 450 only | **2076 skips**, 703 FIXUP_EDGE | `:1410-1488` |

On track 18, 259 reads took 10 s or more. They add up to 7,087 s of the 8,548 s, and the longest was
77 s at LSN 253113 (`DIAG1` messages; `ALB/.log:1528`). The app logged 17 "rip stalled" warnings on the
album pass's track 18 between 22:26 and 00:11 (`APP:8064` onward). The footer reads
`Ripping errors: 2106 (including 2106 paranoia skips)`, `Rip completed: yes`
(`ALB/.log:1515-1530`).

### The read-speed ladder did not step

The ladder logged "no step after pass 1: the drive reported no read errors" (`APP:10226`). Two things
stopped it, and both are by design:

- The drive cannot change speed: `Speed: default (unchangeable)` (`ALB/.log:13`), and
  `rip.speed_changeable: false` in the report.
- The ladder does not count paranoia skips as read errors
  (`platterpus@bba81563:src/platterpus/ladder_trigger.py:26-31,98-99`).

So read speed was not a lever on this drive, though the wording "no read errors" sits badly beside 2,106
skips.

### The securing pass

**The plan.** `plan_securing_pass` re-reads the tracks that fail AccurateRip on a disc AccurateRip holds,
and that includes the tracks that matched on one frame only (`rerip_offset_variant`)
(`platterpus@bba81563:src/platterpus/securing_pass.py:222-235`). That gives `-Z 2 -r 5 -l 11..18`, run
as **one** cyanrip invocation (`ALB/.platterpus-securing-pass.txt:2`, `APP:10228`).

**The bound.** cyanrip's loop for each track stops when 2 reads match the current one
(`cyanrip@ca0f097:src/cyanrip_main.c:1778`), or when it reaches `-r` = 5 reads (`:1790`). At the limit it
keeps the read that most reads agreed on, and the newest on a tie (`:1244-1253`, `:1809`). Within each
read, paranoia's per-frame retries are capped at 5 (`cyanrip@ca0f097:src/cyanrip_main.h:732-739`, used at
`src/cyanrip_main.c:762-763`).

**The timeline.** Each read's start comes from the "being re-read (pass k)" lines in `APP:10303-13280`.

| Trk | Reads (UTC) | Read durations | Outcome | Source |
|---|---|---|---|---|
| 11 | 00:19:46-00:21:58 | 23, 28, 29, 26, 25 s | 5 distinct CRCs. **The kept 5th read `10248071` is AccurateRip-verified: v1 conf 12, v2 `F90C8B07` conf 29.** | `ALB/.platterpus-securing-pass.txt:65-116` |
| 12 | 00:21:59-00:24:14 | 34, 29, 22, 21, 28 s | 5 distinct; frame 450 only; 1 skip, LSN 151669 | `:155-207`; `DIAG2` track_state |
| 13 | 00:24:16-00:27:40 | 46, 39, 32, 50, 37 s | 5 distinct; frame 450 only | `:246-298` |
| 14 | 00:27:42-00:32:24 | 59, 58, 58, 53, 54 s | 5 distinct; frame 450 only | `:337-389` |
| 15 | 00:32:27-00:36:57 | 53, 54, 53, 57, 53 s | 5 distinct; frame 450 only | `:428-480` |
| 16 | 00:36:59-00:38:56 | 25, 23, 23, 24, 22 s | 5 distinct; frame 450 only | `:520-572` |
| 17 | 00:38:57-00:50:46 | **600 s** (17 stalls, 352 s), then 27, 28, 27, 27 s | 5 distinct; 142 skips over all reads | `:611-663`; `APP:11330-11453` |
| 18 | read 1: 00:50:49-02:34:38 | **1 h 43 m 49 s** (193 stalls of 10 s or more, 4,110 s, longest 59 s) | CRC `AB84C427`, "0 out of 2 matches" | `:702`; `APP:13280` |
| 18 | read 2: 02:34:38-03:46:11 | **1 h 11 m 33 s and unfinished** (137 stalls, 2,632 s) | Reached about LSN 253132 of 242462-262524, about 53 %. SIGTERM. | `:704,739-745`; `DIAG2` |

The securing pass ran 3 h 26 m 51 s. Tracks 11 to 17 took 31 m; track 18 took 2 h 55 m 22 s
(`DIAG2` `rip_time_us` 10,533 s). Every finished track hit the repeat limit with "at most 1 read agreed"
(`B/DIAGNOSTICS.txt:27-67`). On tracks 11 to 17, no two of the five reads ever returned the same
audio.

**Run-out projection.** At this pace, read 2 needed about another hour, and reads 3 to 5 about 1.75 to
2.25 h each. The securing pass would have ended about 10 to 11 hours after the rip began. After that, the
0.7.112 chase would have run, because tracks 12 to 18 each showed more than one value
(`verified_read_chase.py:36-43,186-198`). It allows up to `min(-r, 5)` = 5 single reads per track
(`:85,183`). For track 18 alone that is about 9 to 12 more hours. **The end-to-end worst case is
roughly 20 to 24 hours.** The script's own estimate said "up to 16h 20m" (`transcript.txt:4`), while
section F waits 6 hours.

### The questions asked

**Does the new rule loop on a damaged disc where no read can ever verify?**

It cannot loop without end: each track gets at most 5 attempts
(`platterpus@bba81563:src/platterpus/verified_read_chase.py:85,183`;
`src/platterpus/workers/verified_read_run.py:138`). But it has **no time bound**, and its gate admits
exactly the tracks where no read can verify. The gate asks that "the drive returned more than one
value" (`verified_read_chase.py:36-43,194-198`), and a damaged track returns a new value on every read.
On this disc the chase would spend up to 5 more whole reads on each of tracks 12 to 18, with no prospect
of verifying track 18. **It did not run in this run.**

**Is it the securing pass, the `-Z` repeat count, read speed, or the drive?**

- **Drive and disc:** they are the root cause. 2,076 skips and 259 stalls on track 18, at 0.031x.
- **Securing pass:** it is why the rip went past 6 hours. It started at 2 h 33 m and spent 2 h 55 m on
  track 18.
- **`-Z`/`-r`:** the multiplier, at up to 5 reads × about 2 h.
- **Read speed:** not a factor. The drive's speed is fixed, and the ladder by policy ignores skips.

**Was any bound supposed to stop it?**

The bounds are counts only:

- `-r 5` on frame retries and on whole-track reads (`cyanrip@ca0f097:src/cyanrip_main.c:1790`;
  `src/cyanrip_main.h:732-739`);
- the chase ceiling of 5.

Nothing bounds time:

- The fork's stall watchdog only reports liveness: "Seconds a frame read must stall before reporting
  liveness" (`cyanrip@ca0f097:src/cyanrip_main.c:2537-2538`).
- Platterpus's stall detection only decorates the status line
  (`platterpus@bba81563:src/platterpus/workers/rip_worker.py:1246-1258`).
- `_REFIX_ETA_MAX_S` = 6 h (`rip_worker.py:549,1478-1492`) only suppresses the ETA (`APP:10291-10297`).
- The only time limit was the test script's own: `wait-for-rip 21600`
  (`platterpus@bba81563:src/platterpus/rig_scripts/fullacceptance.txt:601-618,664`). Its comment sizes F
  by "section N's workload" on a clean disc and does not consider a damaged one.

Neither repository has a time limit, the fork's tip `fc73b4d` included.

## 2. The one failed step

**`L664 wait-for-rip 21600` expected** the rip that `L663 rip` started at 21:46:11 to finish within
21,600 s, so that F's later steps could grade a finished rip: `expect-rip-complete`,
`expect-verification`, the AccurateRip and CTDB checks, and the rest.

**What happened:** at 03:46:11 it recorded `fail: still not finished after 21600s`
(`B/session/run/report.json` step `line_no 664`, `elapsed_s 21600.025`; `transcript.txt:421-424`;
`APP:14524`).

- The rip was in the securing pass, on track 18's second read.
- The runner cancelled it with SIGTERM (`APP:14527`). The ripper's log gained its footer 9.5 s later
  (`APP:14535`).
- The run ended, with 348 steps BLOCKED and the verdict pass 144, fail 1, blocked 348, unreachable 1,
  info 4 (`transcript.txt:773-776`).

`B/MANIFEST.txt:28` words the same counts as "349 failed", which conflates BLOCK with FAIL.

**This is a budget overrun on the known damaged disc, not a new defect in F's checks.** The same thing
happened on 2026-10-04.

## 3. Was the app's behaviour right for a user?

### What the user was told

The user was told that something was slow. They were not told what it would cost, and they were not
given a choice.

- **Right:** the status line carries "· stalled Xm — the drive is stuck on a hard-to-read spot (a
  scratch or smudge)" (`rip_worker.py:1255-1258`), and 34 stall episodes were logged (`APP:8064-14466`).
  The securing pass announces "Re-ripping track(s) 11, …, 18 (didn't match AccurateRip) to secure them…"
  (`rip_worker.py:3111`).
- **Wrong:**
  - The pre-rip estimate was "about 1h" (`APP:5998`), and the actual time was 6 h 0 m 10 s and still
    running (`APP:14539`).
  - During the securing pass the ETA is withheld ("showing no estimate", `APP:10291-10297`), so a user
    sees no number at all.
  - Nothing says "track 18 alone may take another 10+ hours, and further reads are unlikely to verify
    it".
  - There is no way to stop re-reading one track and keep the rest.

### Cancel

Cancel works: SIGTERM, the footer written, the drive released in about 10 s (`APP:14527-14547`). But it
is all or nothing:

- **Cancelling the securing pass discards every re-read it finished.** That includes track 11's
  AccurateRip-verified read (v2 conf 29). Nothing is swapped from a pass that did not finish
  (`rip_worker.py:3137-3149`). `_record_unfinished_refix` keeps only each track's converged flag and
  never asks `reread_supersedes` (`rip_worker.py:3462-3480`), although that rule would have kept the read
  (`platterpus@bba81563:src/platterpus/verdict.py:916-921`). The report says track 11 is
  `replaced: false, kept_read: first_read` (`ALB/.platterpus.json:5608-5615`). The EAC-layout log says
  "Copy NOT confirmed — re-reads did not converge" (`ALB/ (EAC-compatible).log:212-214`). **A verified
  copy was produced and thrown away, and no structured field or sentence mentions it.** The evidence
  survives only in the embedded securing-pass log text.
- The cancel is attributed to the user. The runner did it ("ui script run ended … cancelling it",
  `APP:14524-14527`), yet the log line reads "rip cancel requested by the user". The EAC-layout log says
  "INTERRUPTED (you cancelled the rip)" (`ALB/ (EAC-compatible).log:11,325`).

### What it did with the bad tracks

The labelling is honest and conservative.

- All 18 FLACs are the album pass's reads (`B/MANIFEST.txt:75-92` lists them).
- Tracks 11 to 17 are flagged as never converging, and 13, 15, 17 and 18 as unverified skips. Track 18
  carries 2 frames of appended silence (`ALB/ (EAC-compatible).log:313-326`).
- The verdict is `warn`, naming the 8 frame-450-only tracks and the 7 that did not converge
  (`ALB/.platterpus.json:291`). `outcome.status` is `cancelled` (`:128`).
- `read_speed.unstable_tracks` is `[]` and `unresolved` is `false` (`:5604-5605`), even though tracks 11
  to 17 never converged. The verdict covers this, but the field is inconsistent.

### Side effects worth noting

- **The drive's estimate is now wrong.** The app learned the drive's speed from this rip, "3500 s of
  audio in 9162 s; folded over 1 rip(s), 0.38x" (`APP:14545`;
  `platterpus@bba81563:src/platterpus/ui/main_window_drive.py:347-363` does not exclude a rip with stalls
  or skips). The next estimate for this drive will be about 2.6 times too long.
- **The bundled report predates the post-rip checks.** CTDB and FLAC verification were launched at
  03:46:21 (`APP`, just after 14547). The report was generated at 03:46:22 with `gates.ctdb: "ran"`,
  `gates.flac_integrity: "ran"` and both in `without_result` (`ALB/.platterpus.json:304,6860-6862`,
  with two `verification_result_missing` warnings at `:467-476`), and the bundle was packed straight
  after.
- **The exit codes disagree.** The report's `securing_pass_exit_code` is 1 (`:138`), while `DIAG2` says
  `exit_code: 143` (SIGTERM). One is the wrapper's and the other the reader's.
- **The fork reports a misleading speed.** In the securing pass, "Extraction speed" and "Elapsed" span
  all 5 reads but divide by one track's length. Track 11 reads "1.4x" when each read ran at about 7x
  (`ALB/.platterpus-securing-pass.txt:104-105`).

## 4. The known fixes this disc exercises

### (6) Error positions in the report: **PROVEN** in the report, **NOT EXERCISED** in the EAC-layout log (by design)

**In the report.** `disc.error_positions` (`ALB/.platterpus.json:811` onward) carries, per track:

- the positions;
- `error_positions_dropped`;
- `count_agrees_with_counters: true` for all 18 tracks.

Its values match the cyanrip log and `DIAG1`:

| Track | Skips | Positions |
|---|---|---|
| 13 | 1 | LSN 158236 |
| 15 | 1 | LSN 208410 |
| 17 | 28 | (listed) |
| 18 | 1000 listed + 1076 dropped = 2076 | (first 1000 listed) |

The `error_positions_reported` warnings name the tracks, the counts and the first sectors
(`:432-450`).

**Defects:**

- **(a) The count states the list, not the counter.** Track 18's `skips` is 1000 (`:5491`) and its
  message says "cdparanoia reported … 1000 skip(s)". paranoia reported 2,076; the remaining 1,076 are only
  mentioned afterwards as "did not list".
- **(b) Positions repeat.** Track 17's 28 entries cover 16 sectors, and track 18's 1000 cover 287. The
  message prints "238003, 238003".
- **(c) The securing pass's positions never reach the structured report.** For example, track 12's skip
  at LSN 151669, which the album pass did not have. The block "describes album pass" (`:812`).
- **(d) The EAC-layout log shows no positions.** This is deliberate until the handshake agrees a wording
  (`CHANGELOG.md:94-95`).

### (3) "No errors occurred" over an unclean read: **NOT EXERCISED** for its trigger, **PROVEN** for the skip half

**The trigger did not occur.** The fix fires when an error line sits above `Ripping errors: 0`
(`ripper_error_lines_under_zero_summary`), and no pass here summarised 0 errors: the album pass's footer
reads 2106 (`ALB/.log:1526`) and the securing pass's reads 3390 (`.platterpus-securing-pass.txt:739`).

**The skip half is proven.** The fix's companion, `unverified_paranoia_skips`, fired for tracks 13, 15,
17 and 18 (`ALB/.platterpus.json:462-465`). The EAC-layout "Read stability" line names them
(`(EAC-compatible).log:323`). Nowhere reads clean: `health_status` is "2106 ripping errors"
(`.platterpus.json:481`), and the EAC disc line says "2106 ripping errors" and "Some tracks could not be
verified" (`(EAC-compatible).log:316-318`).

**The 2026-10-04 regression is also fixed.** "Copy OK" no longer appears over a stopped securing pass's
tracks; they now read "Copy NOT confirmed" (`(EAC-compatible).log:214-296`).

### Paranoia counters: **PROVEN**

- **The album pass.** Its per-track `paranoia_all_reads` sum to the disc totals exactly: READ 554629,
  VERIFY 1025708, FIXUP_ATOM 56958786, SKIP 2106 (`DIAG1`; `ALB/.log:1518-1524`;
  `.platterpus.json` `paranoia_counts`).
- **The securing pass under `-Z`.** Its per-track blocks say "Scope: the last of 5 reads; the disc totals
  below sum all of them" (`.platterpus-securing-pass.txt:145`). Summing `DIAG2`'s per-track
  `paranoia_all_reads`, partial track 18 included, gives the footer exactly: READ 933705, SKIP 3389,
  FIXUP_DROPPED 4 (`:730-737`).

**Not exercised:** Platterpus does not read the `-Z` all-reads counters into the report. No securing read
was kept, so the report describes only the album pass.

### The damaged disc's error and skip reporting: **PROVEN**, with wording defects

**Consistent across the ripper's surfaces:**

- the cyanrip log, "Track N read with errors" for 13, 15, 17 and 18, the footer, and "Read stalls: 261 …
  longest 77s";
- the `-j` record;
- the report's issues `ripper_read_stalls`, `error_positions_reported`, `unverified_paranoia_skips` and
  `heavy_reread`;
- the EAC-layout status block.

`READERR` is 0 everywhere: the drive never returned a hard error, and every error was a paranoia skip.

**The defects:**

- (6)(a) and (6)(b) above;
- the ladder's "the drive reported no read errors" (`APP:10226`);
- "you cancelled";
- track 11's verified re-read, which goes unreported.

## 5. Proposed fix

### The bound (Platterpus owns it: the policy, the UI, the swap)

**1. Run the securing pass one track at a time.** Use `-l N` per invocation, or else swap each track a
stopped pass finished. The fork's footer already names the only partial file: "Partial files: 1 track
(18)" (`.platterpus-securing-pass.txt:741`). Then:

- run `reread_supersedes` on every finished track;
- extend `_record_unfinished_refix` (`rip_worker.py:3428-3496`) to swap through the same path as
  `rip_worker.py:3193-3212`.

A stop on track 18 then keeps track 11's verified read.

**2. Give each track a time budget for re-reading.** Derive it from that track's album-pass read: for
example, stop re-reading track N once its re-reads have used `max(5 × track length, 2 × its album-pass
read time)`, and spend at most a rip-level total above the pre-rip ceiling. On reaching the budget, keep
the best read so far, record `stopped_reason: "time_budget"`, and move to the next track. Apply the same
budget to the chase loop (`verified_read_run.py:138-177` has the `cancelled` hook; add a clock check
beside it).

**3. Skip the chase when no read can be verified.** Add a gate before `plan_chase` returns `run=True`.
When the album read and every securing read of the track carry paranoia skips, it is an unreadable area,
not a near miss. Record `CHASE_SKIPPED_UNREADABLE` instead of spending 5 reads. Tracks 13, 15, 17 and 18
would be skipped. Tracks 12, 14 and 16 stay eligible: they had no skips, and track 11 shows that kind of
track can verify.

**4. Ask the user.** Once a track exceeds its budget, the status line offers "Track 18 has taken 2 h 22 m
and has 2,076 unreadable spots; more reads are unlikely to help: [Stop re-reading this track] [Keep
trying]". Attribute cancels properly: the user, the test run, or the time limit.

### The fork's side (optional)

- **`--prefer-accuraterip-match`** is already on the fork's tip (`cyanrip@6e2ca21`, not in `.26`). It
  keeps an AccurateRip-matching read at the repeat limit. Send it once a released build carries it.
- **A track-level deadline flag**, which the fork could add. It would end the `-Z` loop at a read
  boundary with a distinct line, such as "Done; (time limit of N s reached; …)", and a distinct
  `secure_rip_state`. That would let Platterpus stop without SIGTERM, and the log would never blame the
  disc for the operator's limit (the same concern as `src/cyanrip_main.c:1722-1738`).

Neither is required for the bound above: SIGTERM between per-track invocations is already clean.

### What the report should say when no read can be verified

Per track: **"Not verified: unreadable on this drive."**

- Reads made, each with its duration and CRC. For track 18: one album read of 2 h 22 m, then the
  securing reads.
- "No two reads agreed".
- AccurateRip: matched on frame 450 only, confidence 28.
- paranoia skips: 2,076, at sectors 242,828 to 259,798, given as times within the track, and the count
  from the counter, not the list.
- Why re-reading stopped: the time budget, the repeat limit, "you stopped it", or "the test run stopped
  it".
- Which read the file holds.
- Whether any read was verified, so that track 11 would read "a re-read matched AccurateRip (confidence
  29) and was kept".

Disc level: "Track 18 cannot be read reliably by this drive; another drive or cleaning the disc may
help", and no "about 1h" estimate left standing.

### Tests that need no drive

**Platterpus** (the suites exist: `tests/test_verified_read_chase.py`,
`tests/test_rip_worker_verified_read.py`, `tests/test_securing_pass.py`,
`tests/test_auto_fix_convergence.py`):

1. Commit this bundle's `ALB/.log` and `.platterpus-securing-pass.txt` as fixtures.
2. With a fake `_rip_once` returning `success=False` and a temporary folder holding track 11's FLAC,
   assert that track 11 is `replaced`, `replaced_because=accuraterip`, and that tracks 12 to 17 are
   recorded unswapped.
3. With `plan_chase` over the fixtures, assert that tracks 13, 15, 17 and 18 are skipped as unreadable
   and that 12, 14 and 16 are eligible.
4. With `run_chase`, a `read_once` that never verifies, and an injected clock advancing 2 h per read,
   assert it stops at the budget with `stopped_reason: "time_budget"`.
5. Write golden tests of the report sentences and the EAC-layout lines, built from these fixtures.

**Fork:** extend `tests/stall.c` or `tests/badsector.c` with a fake slow reader, and assert that the
deadline ends the `-Z` loop at a read boundary with the new line and state.

**Acceptance script:** section F's wait should take the run estimate's ceiling, or the rig should run F
on the reference disc and test the damaged disc in its own section, with the bound above as the thing
graded.
