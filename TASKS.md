# TASKS.md — Platterpus Active Task Checklist

Single source of truth for what's being worked on next. Update status as work progresses:

- `[ ]` / ⬜ not started
- `[~]` / 🟡 in progress
- `[x]` / ✅ complete
- `[?]` / ⛔ blocked (add a one-line note about what's blocking)

The **bullet** task lists below use `[ ]`/`[x]` (GitHub renders these as real
checkboxes). The **numbered** sections ("Current plan & priorities", "Ranked
execution order") use the emoji equivalents instead — GitHub only renders
checkboxes in bullet lists, so a numbered `1. [x]` would show as literal text;
the emoji means the same status and keeps the rank numbers (referenced elsewhere
as "item N" / "TASKS #N") intact.

Execute tasks in priority order. P0 shipped 2026-06-01 as v0.1.0; the P1 backlog has been the active queue since.

When a task changes status, update it here in the same commit as the code change. When a task uncovers a new sub-task, add it to this file; don't let it live only in chat.

**This file holds live work only.** On 2026-11-16 every section with no open row moved,
unchanged, to [`docs/archive/tasks-closed-to-2026-11-16.md`](docs/archive/tasks-closed-to-2026-11-16.md);
where a section still held an open row, its closed rows moved there under a copy of its
heading and the open rows stayed here. A row or section this file names and does not
hold is in that archive, and so is every closed item that comments and docs cite by an
old list's number or letter: *TASKS P1 #1* and *P2 #4* to *#8* (the 2026-10-12
ranking); the A to E items of the 2026-10-05 ranking (*A4*, *C4*, *D2*, *D6* among them);
*D1* to *D19* (the maintainer decisions); the closed lettered rows of the round-25
agenda (*C1* to *C8*, *E1*, *E12* among them; its open ones, such as *C10* and *G12*,
are below); the gate-audit IDs that closed (`stateful:…`, `conv.…`, `rule-…`,
`fuzz:…`); and closed rows cited by title. Where a letter names two lists, both are
in the archive.

---

## 2026-11-16 — every open row triaged, ranked (after round 40's close)

Every `[ ]`, `[~]` and `[?]` row in this file was checked against the tree on
2026-11-16, and each carries a dated `Triaged 2026-11-16` note saying what is true
and citing where. 39 rows closed as done, superseded or moved; R157 to R170 were
added for open items that had no row. State then: 0.7.125 released; round 40 closed,
`FORK_PIN` `edb73dd` (`.32`); round 41 is the fork's to open (protocol §1a), and our
list for its lap 1 is in `docs/handshake/outbound/platterpusstatus.md` → *What we need
from you*. Order follows the owner's rule of 2026-11-04: EAC parity first, then wins.

### Waiting on the owner (nothing else moves these)

1. **0.7.126**: the first release to install `.32` by default; carries R155 and R156 once fixed.
2. **R59 (a)**: whether `expect-album-audit` may pass a placed ripping-error tally.
3. **R93**: the repository setting that lets Actions open pull requests; **R92**: Critical rule #11's locked wording; **R142**: whether the EAC-layout log may be rewritten after a CTDB repair (KDD-47); **R32**: `CLAUDE.md` at 678 lines.
4. **Rig time**: R24 (the over-read probe, never filed), R123 (`track3abba.txt`), R53 and R96 (rig confirmation only), the C2 probe's whole seconds, and a second drive for R150 and R151.
5. **R157**: a protocol v10 carrying K1 and the deferred list, on both operators' words.

### Ours, next, in this order

1. **Record correctness, before 0.7.126:** R155 and R156 (the fork's round 40 lap 3 S13, S14), then R131 and R141, the same family.
2. **EAC parity:** R88 (retire the 255-byte refusal now that `.32` is the pin); R152 and R151 (read the drive's declarations at setup and choose the cache probe; the fork has answered both); R150 (offset from a disc for drives AccurateRip does not list); R44 (error positions in the log, Part F row 10); the disc-level *There were errors* for unverified skips (row triaged at line 1424 of `34d20333`); R137 parts (2) and (3).
3. **Wins:** R134 (rebuild a disputed second; its hold lifted with round 39's close); R43's CTDB submission; R49's *unreadable on this drive* verdict.
4. **Cheap:** R86 (send the escape ask in our next lap), R73, add second 245 to the C2 probe.
5. **The rest of the R-table**, R157 to R170 among them, as each row orders itself.

### Needs a disc, a second machine or an outside answer

R55 (one EAC rip timed against ours), R52 (AccurateRip submissions from an unlisted program), R6 (an EAC hidden-track rip), and a second machine and distro for 0.8.1's gate.

## 2026-10-12 — every open row, ranked: close now, close soon, fine open, and what goes to the fork

The maintainer, 2026-10-12, asking both repositories the same question: *"compile all open
tasks in a priority order, and present them to the other as needed and in priority? leave
the remaining as open tasks to either be OK as open or need to close in another priority
list? if needed, include in the lap/round."*

**This section replaces the 2026-10-05 ranking below**, which was written for the 0.6.66
beta and is now history: every A, C and D item in it is done, B went into laps 13 to 16,
and E is re-ranked here. It is an order, not a second copy of each row. Each item names
its row by title (line numbers move), and the row carries the status.

**How it was built, and the count.** Every open row was read against the tree on
2026-10-12, not from memory. Open means a `[ ]` or `[~]` row in either bullet form, or a
🟡/⬜ item in the old numbered lists. That was **173 rows**: 164 checkbox rows and
9 numbered items. The first extraction stopped at the old ranked-order sections
and missed 42 of them. A count that claims "all" was the trap the 2026-10-05 note
recorded, so those rows went through a fifth read before any number here was written.
**22 closed in this change**, each with a dated note on its row giving the commit,
file or test: 11 were done (one of them the 0.7.103 release, cut during this change), 11 superseded (mostly by protocol 8). The
**151 that stay open** are ranked below. P1 means an archival risk to a user's library,
or blocking a release now. P2 means close soon: a real defect, or a cheap gap with a
trust cost. P3 means fine to stay open: features, hardware-gated work, large refactors
and gate ideas.

### What the fork's own 2026-10-12 list needs from us

The fork compiled theirs the same day (`cyanrip@cbce64d:docs/handshake/STATUS.md:6-25`, read
from their tree; their round 32 lap 1 is held and unread by us, as the seam requires). Of
their items, these are ours to do. They join the order here, between P1 and P2:

**Round 32 CLOSED on both gates 2026-10-14** (their lap 9 `GO` after our lap 8 `GO`): it
approves `.22` (`200530e`) with 0.7.104, and `FORK_PIN` rolled to `200530e` the same day,
with the approval record moved to round 32. 0.7.105 is the first release that installs
`.22` by default: **released 2026-10-14** (tag at `b33b90d4`, PR #326, release run
38508995393, PyPI published). Rows still open below carry to round 33.

| # | What | Ours to | Their item |
|---|---|---|---|
| R1 | **[x] Triaged 2026-11-16: done: the run was graded `full-green` and round 32 closed GO/GO (`docs/testing.md` §5B; `scripts/handshake.py --status`).** *Was:* **Round 32's test: the Full run on `.22` with 0.7.104**, not 0.7.103 as this row first said: 0.7.103's section A accepts `.21` alone (`accepted_rig_builds()` returns `PIN_UNDER_REVIEW`, `ca3f3ea` in that release). Corrected in our round 32 lap 2 S2, which amends their S6's pair (S3). `PIN_UNDER_REVIEW` is `200530e` from `497d4dbb` | **0.7.104 released 2026-10-13** (tag at `3577be65`, PR #320, pre-release), once HR-1.7 (6) held (their lap 7). **Run 2026-10-13** (11:29 to 16:49 UTC): 424 pass, 0 fail, E2 N/A, graded `full-green` on the maintainer's ruling; filed as `docs/handshake/artifactsround32/round32full*`, read in our lap 8 | `STATUS-RUN-NEXT` |
| R2 | **[x] Triaged 2026-11-16: done: the `-j` record's fields are read into the report (`record_track_v11.py`; `rip_report.py:1406`, `ripper_record`), and round 32 closed GO/GO.** *Was:* Their `-j` field names for pre-emphasis, subcode ISRC, CD-TEXT and the `-f` result. **Answered 2026-10-12** in our round 32 lap 2: accepted as named (S7), with one amendment, `cdtext`'s keys enumerated in their P8b (S8) | Wait for their lap 3's word on S8 and their commits; then parse the fields (P2 #9 first, so they land in the archived record) | `j-record-fields` |
| R3 | **[x] Triaged 2026-11-16: done: nothing of ours was owed, and round 32 closed GO/GO (`scripts/handshake.py --status`).** *Was:* Track 1's pregap length from LBA 0 (their S13). **Answered 2026-10-12** in our round 32 lap 2: accepted (S10), and no release of ours needed first (S11), because our reader takes `Pregap length:` as stated and EAC's convention is the lead-in plus any span | Nothing more of ours; their commit lands it | `track1-pregap-base` |
| R4 | **[x] Triaged 2026-11-16: done: answered in round 32, which closed GO/GO (`scripts/handshake.py --status`).** *Was:* Which build a closing lap's version fields name. **Answered 2026-10-12** in our round 32 lap 2 S12: their S16's reading, the reviewed build in `OUR-VERSION`/`PEER-VERSION`, which is how our approval record already reads theirs | Our closing lap names 0.7.104 there, and `--emit` says so (lap 2 S26) | `version-field-meaning` |
| R5 | **Triaged 2026-11-16 (STALE-BUT-OPEN): the bounded `-O` shipped in `.24` and its one hardware read is still owed (R24; `docs/handshake/outbound/platterpusstatus.md:36`); `accurate-stream-declared` became `.26`'s `Accurate stream:` line, read since 0.7.111 (R45), and reading it at drive setup is now R152; the other items stay parked.** Four drive-gated proposals and four parked joint items. **Answered 2026-10-12** in our round 32 lap 2: S19 orders the four (bounded `-O` first), S20 orders the four disc runs for our script, S21 keeps two parked items for round 33 and folds two into v9 | For round 33; the operator's disc list decides S20. *2026-10-19:* round 33's task was HR-2, so these carried; the bounded `-O` (S19's first) came in `.24` (round 35), and its one read is `overreadprobe.txt` (R24) | `overread-bounded`, `accurate-stream-declared`, `subchannel-pregap-varies`, `superseded-read-marker`, `files-listed-from-request` |
| R6 | **Triaged 2026-11-16 (OWNER, HARDWARE): unchanged: only an EAC rip of a hidden-track disc settles it, and none is filed under `output_reference/`.** Their round 32 lap 3 S10: our lap 2 S10 said EAC's additive track-1 convention (lead-in plus a span before track 1) is derived from a real EAC log. Only the lead-in arm is: our one EAC log has no such span. The test docstring and the parser comment now say so (2026-10-12) | Answer S10 in our lap 4 (no such log; the additive arm is sector arithmetic). Ripping a hidden-track disc with EAC would settle it, and only the operator can do that | `eac-htoa-log` |
| R7 | **[x] Triaged 2026-11-16: done for the pinned builds: every `-Z` pass sends `--reread-until-accuraterip` to `.31` and `.32` (`workers/rip_worker.py:2312`, R146), the chase covers older builds, and a stopped pass keeps its verified re-reads (`ba8a2e77`, `unfinished_refix.py:127`).** *Was:* Their round 32 lap 3 S13, for round 33: on the 2026-10-12 run our securing pass on track 5 read `C96464AB` once (the one checksum AccurateRip matches whole) and kept `4065BECC`, read twice, because at the repeat limit they keep the majority read | Decide in round 33 whether our securing pass should prefer an AccurateRip-matching read, and what the record would need to carry. *2026-10-19:* not decided in round 33 (its task was HR-2) or since; still open. **[~] 2026-10-21: built on our side, hardware-gated.** cyanrip's `-Z` cannot be told which read to keep, and within one pass we cannot tell which read AccurateRip would verify (cyanrip computes AccurateRip only for the read it keeps). So after the securing pass, a track whose kept read AccurateRip did not verify, on a disc it holds, whose reads showed more than one value, is read singly (`-l N`, no `-Z`) up to `-r` times (at most 5); the first read AccurateRip verifies (confidence >= 1, the one definition of verified, through `verdict.reread_supersedes`) replaces the album's file, and otherwise nothing changes (`verified_read_chase.py`, `workers/verified_read_run.py`). Report schema 39: `retried_tracks[].kept_read` and `verified_read_chase` (each read's EAC CRC32, AccurateRip confidence, exit status), `secure_rerip.verified_rereads`; the EAC-layout log prints the chase read as one read (Copy CRC only) and our own `Verified re-read` status line. **This is the path for builds without the fork's proposed `--prefer-accuraterip-match`** (their round 36 lap 4 S11, for the release after `.26`): that option keeps the AccurateRip-matching read at the limit for no extra reads, where ours costs up to `-r` reads. We already read its proposed limit-line clause (`kept X, read N times, which AccurateRip matches at confidence C[; last read Y, not kept]`, `cyanrip_log.secure_rerip_limit_kept_read`, per-track report key `secure_rerip_kept_read`), and do not send the flag: no released build accepts it, and sending it needs the build-tag gate. *2026-10-26 (R48):* the gate is built (`prefer_accuraterip_match_args_for_build`, `fork_source.BUILD_TAGS_ACCEPTING_PREFER_ACCURATERIP_MATCH`), sending the option on every rip to a listed build; the set is empty until `.27` (`6e2ca21`) is released. Open: a hardware run that exercises the chase (the reference disc's track 5); keeping each chase read's own `-j` record, which goes with its temp folder; `.27`'s tag into the set on its release, after its contract's P1 is checked. **2026-10-26 (Part F row 2 of `docs/eac-parity.md`, Behind; the EAC parity plan of record):** the chase ran on hardware and worked: disc 3's secure re-read replaced track 16 with a single read AccurateRip verifies (v2 confidence 24; `round36full1022asecurerereadaddendum.txt`, evidence `fc48882f`). Two paths still lose a right read. The archival secure re-read runs no chase, and shipped track 3's converged `3D8FCF0C` after reading the verified `59D352DD` first (`round36full1021asecurereread.log:225-231`, evidence `ab3b1395`). And a cancelled securing pass swaps nothing it finished, so disc 1's verified track-11 read `10248071` was thrown away (`round36full1021bwholediscsecuringpass.txt:112-116`, evidence `08de9851`; `_record_unfinished_refix` never asks `reread_supersedes`). **[~] The second, swapping each track an unfinished securing pass finished, is in progress on the session branch on 2026-10-26, not committed at `bd194381`.** Still open: a chase, or the fork's `--prefer-accuraterip-match`, on the archival path | *(round 33)*; ours |
| R8 | Their round 32 lap 5: C29 (our lap 4 declared 7 after their 8), C46 (their lap 5's `HANDSHAKE-NEXT-LAP`), and S11/S12 (`--diagnostics`, `seam-commands.md`). **Answered 2026-10-13** in our round 32 lap 6: our gate checks C29 and our emitter declares at least the record (`d9fb808a`, merged at `9156e878`); S8 asks them to refuse the file, not the round, with round 33 on the same pin as the fallback; S10 gives C46's fix; S11 and S12 landed | **Done 2026-10-13:** their lap 7 (`cyanrip@afe5ca7a`) passes our `--check` and lap checker, completing HR-1.7 (6); their gate now refuses the file under C29 and C46 (`cyanrip@9fca98a`), so no round 33 is needed. Their S8 corrects our S10's remedy: it should have read `6 (yours):`, from the writer's side; our lap 8 says so under Corrections. Cut 0.7.104 | *(done)* |
| R9 | **Triaged 2026-11-16 (STALE-BUT-OPEN): the chase half is done: each chase read's record is kept (`chase_record_keep.py`, R147) and the five-rip run's bundle carried 47 chase records (evidence `ac0a5133`); the packing-order half (a bundle packed before CTDB and FLAC verification land) was not re-verified in this triage.** Found in the 2026-10-13 Full run: a securing pass's own `--diagnostics` record is never kept, because the pass runs in a temporary folder deleted afterwards (`rip_worker.py`, above `record_path_from_argv`), and the session bundle's MANIFEST does not name the absence. Two of the run's 11 invocations (`-l 3,5`, `-l 3`) left no record. W6 recorded the gap as "not done" in a closed row; this is the open one | **[x] Done 2026-10-14, both halves**: the worker copies the securing pass's record into the rips root as `<name>-securingpass.json` before its temp folder is deleted, on every way the pass ends, and names it for the rip's bundle (`record_fate.keep_securing_record`); when it cannot, the reason (no record named, not written, the rip cancelled, the copy failed) goes into the report as `outcome.securing_pass_record` (schema v34) with a `securing_pass_record_missing` info issue, and the session MANIFEST's `ripper -j records missing` line names every pass whose record is missing, with that reason, cross-checked against the scan. Read over the filed round-32 reports it says the two securing passes are not determined (schema v33). Not covered: an earlier album pass of a speed-ladder retry (only the last is in a report), and a cancelled pass's record that cyanrip writes after the folder is cleared, which is named missing rather than kept. Was: either keep the securing pass's record beside the album pass's in the rips root, or name each missing record in the bundle's MANIFEST with the reason. Ours; nothing of the fork's. **2026-10-26, [~] bundle packing, in progress on the session branch on 2026-10-26, not committed at `bd194381`:** the same gap on the verified-read chase. Each of its cyanrip invocations passes `--diagnostics`, and none of their records reaches the session bundle, while its MANIFEST says `missing none` (disc 3, 2026-10-22, ten chase reads; the positions of their skips are lost). And a bundle can be packed before the post-rip checks land: disc 1's report (2026-10-21) was written a second after CTDB and FLAC verification were launched, both gates `ran` and `without_result`. From the EAC parity plan of record's Appendices H and I (`docs/eac-parity.md` Part F) | *(round 33)* |
| R10 | Their round 32 lap 9 S4 (round 32 closed GO on it, 2026-10-14): in the 2026-10-13 run's secure re-read, cyanrip's sub-channel search read track 4's 158-frame pregap as none (`Gaps:` omits track 4, its block reads `Pregap length: 0 frames`, the cue has no `INDEX 00` for it), where the whole-disc rip lists it. Verified in our filing (`round32fullsecurereread.log:42-50`, `.cue`, against `round32fullwholedisc.log:44`). **The defect is theirs and old** (first on 2026-09-05, `978f9b0`); **the miss is ours**: our lap 8 read the run and did not name it, and nothing in our grader compares the `Gaps:` lists of two rips of one disc in one run | **[x] Done 2026-10-14**: `expect-pregaps-agree`, run by the acceptance script's new section P4 (`uiscript/pregap_grading.py`, `pregap_verbs.py`). It compares the `Gaps:` lists of every cyanrip log the run wrote (album logs, P3's, each securing pass's own) disc by disc, keyed on the Disc ID, and names each track that differs with which logs said what. On the filed round-32 logs it names exactly tracks 4 and 9 (`tests/test_uiscript_pregap_verbs.py`). `info` either way and `blocked` below the floor of two comparable logs of one disc; the severity argument is P4's row in `docs/testing.md` → *Acceptance severity*. Was: round 33: a grader check that the pregap lists of rips of the same disc in one session agree, naming each track that differs (track 9's 94 vs 95 frames is the same run's second instance, their `subchannel-pregap-varies`). Nothing to fix in cyanrip from our side. **Added 2026-10-20 (P5 of the claude-code-skills check of the EAC audit, for the fork too):** across all 26 shipped rips of the reference disc, track 9's pre-gap reads 95 frames (`0:00:01.26`) in three (`round30oct05fullsecurereread`, `round32fullwholedisc`, `round33fullwholedisc`, the last at evidence commit `f57cdc2b`) and 94 (`0:00:01.25`, EAC's in all three of its sessions) in the other 23; the cue's track-9 `INDEX 00` then sits one frame early (`03:44:10` in `round32fullwholedisc.cue:69` against EAC's `03:44:11`). `docs/eac-parity.md` Part E §E4 now grades pre-gaps on 23 of 26. Whether the Q sub-channel read varies or a rounding step does is the fork's question; ours is to keep P4 naming it | `subchannel-pregap-varies` |
| R11 | **[x] Triaged 2026-11-16: done: S8 to S10 landed 2026-10-14 and round 33 closed GO/GO (`scripts/handshake.py --status`).** *Was:* Their round 32 lap 9 S8 to S10, for round 33 (their data register's X7 to X9): **S8** a sha256 for every member of a session bundle, from our side, so a filing is checked against our hashes and not only the archive as it arrived (`MANIFEST.txt` gives sizes only); **S9** `--consumer` and `--diagnostics` on section R16's pre-emphasis rips, which call cyanrip directly; **S10** home paths replaced at export, so a bundle never carries them (they replaced them in nine files of this run). **S8 landed 2026-10-14**: `MANIFEST.txt` gives every included member's SHA-256, of the bytes written, in `sha256sum` format (`evidence_bundle._sha256_section`); the fork's `tools/ingest-bundle.py` and `tools/read-run.py` do not parse the manifest, so neither is affected. **S10 landed 2026-10-14**: every text member is written with home-folder paths replaced by `~` (`export_redaction.py`, the fork's `tools/redact.py` pattern), counted in the manifest with each member's hash before the change; S8's hashes are taken after it. **S9 landed 2026-10-14**: R16's two rips carry `(consumer) (diagnostics)`, script placeholders that expand to the words the rip argv builder sends (`consumer_args_for_build`, `diagnostics_args`, now the builder's own calls), gated on the build `cyanrip --version` latched; the line still passes `sanitise_cyanrip_args` → `assert_metadata_lookup_disabled`. `.22` accepts both (`cyanrip@200530e:src/cyanrip_main.c:1927-1930`); only the next Full run shows the two logs naming their caller. **Narrowed, and the narrowing is the ask's to accept or refuse in our round-33 lap:** a signed cyanrip log and our checksummed EAC-compatible log are written byte for byte, because a replaced path makes a genuine log fail `--verify-log` or its footer; any home path in one stays. Measured over our filing of the 2026-10-13 run, the 22 signed members of its 76 files (11 cyanrip logs, 2 securing-pass logs, 9 EAC-compatible logs) carry none, because cyanrip is handed relative paths, so today the exception costs nothing; the other members held 1,985 replacements. Hostnames and names are not replaced | Round 33: answer each in our lap and land what we accept | X7, X8, X9 |
| R12 | **Triaged 2026-11-16 (STALE-BUT-OPEN): still neither flag is sent (no `-X` or `-B` argv in `src/platterpus`); R13 handles a data track on our side, and the `-X`/`-B` decision is now R31's (`docs/seam-commands.md:145,153` still read `?`).** **`.23` copies data tracks by default** (upstream rc3; `cyanrip@aa45b975:src/cyanrip_main.c:1294-1296`). On an Enhanced CD that puts a `.bin` in the album folder, and data-sector errors count in `Ripping errors:` (`:1217`, `:1227`), so our report reads "N ripping errors" and our read-speed ladder re-rips the whole disc slower over audio that was fine. Sending `-X` (`--no-data-tracks`) avoids all three, but our argv check refuses it until a round files `.23`'s flag table. Also ask whether their container build links libchromaprint: if it does, every file gains an `ACOUSTID_FINGERPRINT` tag unless we send `-B`. Found 2026-10-14 by the rc3 readiness work | Maintainer's call on `-X` and `-B`; ask the fork in our first round-33 lap; then send the agreed flags through the argv chokepoint. *2026-10-26:* `docs/eac-parity.md` Part F row 25 (Behind): HTOA, image + cue and data tracks; HTOA and image + cue stay low (E7). This row's open question is unchanged | round 33 |
| R13 | **Done 2026-10-21** (branch `r13-data-track`). One predicate and one key, `src/platterpus/data_tracks.py` (`is_data_track`, `audio_track_totals`), now asked by the verdict, the JSON verdict, the EAC-layout log, the status line, the disc-info panel, the read-speed ladder, the artifact grading and the CTDB refusal. The verdict names the data track it leaves out; the EAC-layout log gives a data track no AccurateRip line (EAC never extracts one, so it has no sentence to borrow); CTDB says its TOC cannot hold the data track instead of calling the rip partial. Held by `tests/test_cyanrip_rc3_readiness.py` section 2b (ten tests, among them `test_a_mixed_disc_whose_every_audio_track_verified_is_bit_perfect`, `test_the_eac_layout_log_gives_a_data_track_no_accuraterip_line`, `test_every_surface_counts_the_same_two_audio_tracks_on_a_mixed_disc` and `test_is_data_track_is_the_one_predicate_and_nothing_restates_it`). Residue: a data track a stopped rip never reached still counts as never ripped, because the log is the only record of which tracks are data. Was: **A data track is counted as an audio track with no result.** `verdict.accuraterip_verdict` counts its block, so a mixed disc whose every audio track verified reads "⚠ 2 of 3 tracks verified … 1 track produced no result", and the EAC-layout log prints "Track not present in AccurateRip database" for it. Older than `.23`; the disc total passed in is cyanrip's `Disc tracks:`, which counts data tracks, though the docstring says audio only. Found 2026-10-14 | Count audio tracks only in the verdict and the EAC layout, with a test on a mixed-disc log | ours |
| R14 | **[x] Landed 2026-10-16:** the app log (and so the report's `debug.lines`) writes each run of redraws as its first line, one checkpoint at most every 10 s (so a freeze still shows where the drive stopped), and its last line, as the ripper wrote them (the error count kept), with a `progress redraws elided here` marker counting every redraw between; until now the redraws between the ten a second were dropped with no count. `redraw_run.LoggedRun`, a property test that every redraw is written or counted exactly once, worker tests for the order and for a stream that ends mid-read; three revert probes detected. Replaying the newest app log file of the 2026-10-16 run through it: 5.9 MB and 53,908 lines down to about 0.3 MB and 2,267 lines (a replay of the already-throttled lines, so an estimate). **85% of our filed evidence is cyanrip's progress line, recorded verbatim.** Measured 2026-10-14 over every `docs/handshake/artifacts*` folder: 231 MB of 240 MB of app logs and 132 MB of 142 MB of report `debug.lines` are `Ripping track N, progress - X%` at ten a second. The same block sits in every rip's `.platterpus.json` in a user's library (about 6 MB for a whole-disc rip), and the app log's 10 x 8 MiB rotation holds only about 2.5 hours of ripping. Collapsing repeats to first and last per track with a counted elision marker keeps CLAUDE.md's capture rule. **Checked 2026-10-14: no reader of timing uses them.** `rip_estimate` folds each track's `Elapsed:` line from the ripper's own log (`parsers/cyanrip_log.py`), and the live ETA works from the in-memory stream. The stored capture is already thinned to first, count, last (`redraw_run.py`, 2026-10-05); what still keeps every throttled redraw, at up to ten a second, is the DEBUG copy in `rip_worker.py`'s log path, which feeds the app log and the report's `debug.lines` | Collapse progress lines in the app log and the report's debug block, with counts; tests for the marker and for any reader of the timing | ours |
| R15 | **[x] Triaged 2026-11-16: done: HR-2 is in force (rounds 33 to 40 filed on `evidence`, `docs/evidence-manifest.tsv`). `--emit` still numbers from our outbound laps alone; `--announce` refuses a number the peer has claimed (`scripts/handshake.py:2178-2200`), the backstop.** *Was:* **HR-2: run evidence moves to an `evidence` branch** (round 33's first task, agreed 2026-10-14; text in `docs/cyanrip-handshake.md` §7.4b). **Step 1 [x] merged 2026-10-14 (PR #328, `5139c5d3`; PR and push CI both green, §8c)**: the lap checker reads evidence citations (§6), `scripts/evidence_manifest.py` (§3–§5, §8a), the reader sweep with its 38-file allowlist (§2), the session-start refspec (§7), and CI fetching by refspec with `gitleaks` as the one evidence job (§8). **Step 2 [x] on the session branch 2026-10-14**: 394 fixtures (47 MB); a run-time guard fails a test that opens an original; the simulated move passes the suite (one stale-ref test in the scratch clone aside). **Order B [x] 2026-10-14 (HR-2.1 a and b, and the fork's v9 `PROTOCOL.md` copied byte for byte from `cyanrip@8f847271`, sha256 `c0539096…`)**. **Order C [x] gate side, 2026-10-14**: our gate implements 9 (`bc3f7162`), after the fork's round 33 lap 1 (filed, `cyanrip@b20eb2de`, instant `2026-10-14T20:00:00Z`); our lap 2 says so (held). Our three run folders that had no README gained one before the build, as the fork's four did. **Order D [x] 2026-10-14**: evidence commit `c737fb6b…` from `25db8bd5` at the instant, 756 files, 425,738,049 bytes, pushed to `evidence` (749 objects, 33.14 MiB, 58 s); the removal PR deletes 744 files and adds the 756-row manifest, its first commit `9439bfec` on `25db8bd5`; merged as `f82392bb` (PR #336). The fork's move verified by our checker (round 33 lap 4 S8 to S10), after `7981b961` taught our move check to read paths with `-z`. **Step E [x]**: the 2026-10-14 Full run is filed straight to `evidence` (HR-2 point 10a, 2026-10-15): `f57cdc2b…`, parent `c737fb6b`, 79 files and 38,250,562 bytes under `docs/handshake/artifactsround33/`; the manifest-rows pull request is point 10b, landed as `7b2319a0` (PR #340, merged at `37ed04b9`; `docs/evidence-manifest.tsv` holds the 79 rows, each naming `f57cdc2b`). Our point-12 lap citing one of its files is lap 6, on the operator's word of 2026-10-15: it cites `round33fullwholedisc.log` on `f57cdc2b` and declares `GO`; the fork's lap 5 S5 passes our checker after `7ac8b5fc` taught it to read the SHA-256 a lap writes. **Round 33 CLOSED 2026-10-15** on both gates (their lap 7 `GO`, `cyanrip@9aee54a`); the approval record moved to round 33 for `.22` with 0.7.105, `FORK_PIN` unchanged. the fork's `0f9375ad…` rebuilt here to their ID. **Open, ours:** `handshake.py --emit 33` emitted a lap 1 while the fork's lap 1 was filed (it numbers from our outbound laps alone); lap 2 was written by hand (lap 2 D1 (c)). **Step 3 [x]** (order D): build and push the evidence commit (§5b–§5d, dated by round 33 lap 1), then the removal PR with the manifest; done as Order D above (corrected 2026-10-19: this said `[ ]` after Order D was recorded done). **Step 4** is R14, landed 2026-10-16 | Orders C–E and step 4; the operator's answers of 2026-10-14 settled what did not match (the fork's v9 file wins, lap 1 fixes the instant, GitHub secret scanning counts, fixtures accepted) | ours; theirs mirrors it |
| R16 | **[x] Landed 2026-10-16:** `scripts/evidence_file.py stage` copies a bundle's members under HR-2 names (`scripts/evidence_names.py`, refusing a member it cannot name), verifies each signed log first (`fun512.py`, a port pinned to the three signed logs in `tests/fixtures`, and our SHA-256 footer) and keeps it byte for byte, and replaces home folders, hostnames (`host`) and the owner's names (`the owner`, only from a list outside the repository; without one it says *not checked*), counting each in `<out>-FILING.tsv` with both hashes; `commit` builds the evidence commit (identity `evidence <evidence@invalid>`) and writes the manifest rows; it never pushes. The app's export replaces hostnames and names the same way (`export_identity.py`), counted in the bundle MANIFEST. Run over the 2026-10-16 bundle: 81 filed, 27 skipped (screenshots), 13 cyanrip logs FUN512-valid and 8 EAC-layout footers valid, nothing left to replace. **HR-2 point 9 is done by hand where it should be done by our filing tool.** Point 9 says each side replaces home folders, the hostname and the owner's real name "through its filing tool, counting each replacement", and verifies self-verifying logs first, recording the result and both hashes. Filing the 2026-10-14 run (2026-10-15) showed three gaps: (a) the app's export (`export_redaction.py`) replaces home folders only and says "Hostnames and names are NOT replaced", so the hostname and name were checked by a search, not by the tool, and counted 0 in the folder's README rather than in the bundle's MANIFEST; (b) we have no Python FUN512 verifier, so the 11 cyanrip logs were checked by a scratch port of `cyanrip@5c564042:src/fun512.c`; (c) the staging, renaming and evidence-commit steps were scripted in the session scratchpad, not committed. | A committed filing tool (`scripts/evidence_file.py` or a mode of `evidence_move.py`): stage with round names, verify FUN512 and our SHA-256 footer, replace and count hostname and owner name as well as home folders, build the commit, emit the rows; a FUN512 port with tests pinned to a filed log; the export gains the hostname | ours |
| R17 | **[x] Graded 2026-10-16** (`docs/testing.md` §5B, both rows cited in HR-2 6a's form): 2026-10-16 `full-green` on the maintainer's standing E2 reading; 2026-10-14 `partial`, because K2's `expect-cover-art` (ARCHIVAL) was `blocked` by the Cover Art Archive's HTTP 500 and so never reached its subject, unlike E2, which no day on this rig can reach. **Two Full runs had no row in the evidence ledger**: the 2026-10-16 run (round 34: 0.7.106 with `.23`, 426 pass, 0 fail, 1 unreachable; filed on `evidence` at `fe13de0c`, `docs/handshake/artifactsround34/`) as well as **the 2026-10-14 Full run** (`docs/testing.md` §5B). It is filed on `evidence` at `f57cdc2b` (`docs/handshake/artifactsround33/`): 0.7.105 with `.22`, 425 pass, 0 fail, 1 blocked (the Cover Art Archive's HTTP 500), 1 unreachable (E2). Not graded when filed. | Grade it and add the row, citing the filed run in HR-2 6a's form; say whether the blocked step changes the grade under the severity rules. *2026-10-26:* the class recurred on disc 4's Full run (2026-10-22 21:57 UTC): `expect-cover-art` L730 blocked by the Cover Art Archive's HTTP 500 for the front cover, while booklet images from the same archive saved 54 s later, so our message "could not reach the Cover Art Archive" overstates it (R57). The four round 36 runs are not graded in the ledger yet | ours, round 34 |
| R18 | **[x] Fixed 2026-10-16:** `repo_markdown_files` (`tests/conftest.py`) walks with `os.walk`, which skips a directory gone by the time it descends and still raises any other error, and prunes the tool caches (`TOOL_CACHE_DIRS`); `tests/test_doc_links.py` removes a directory mid-walk and fails on the old `rglob` walker with the reported `FileNotFoundError`. The walk's population lost one file, `.pytest_cache/README.md`. **`tests/test_doc_index_completeness.py::test_every_handshake_citation_in_prose_resolves_in_THIS_tree` races Hypothesis.** Its tree walk met `.hypothesis/tmp` as a parallel xdist worker removed it (`FileNotFoundError`, one local `scripts/check.py` run, 2026-10-15; the re-run passed). | Skip `.hypothesis/` (and other tool caches) in the walk, or tolerate a directory vanishing mid-walk; a test that removes the directory during the walk | ours, round 34 |
| R19 | **[x] Round 34 CLOSED 2026-10-16** on both gates (their lap 3 `GO`, `cyanrip@68f56fa`); `FORK_PIN` rolled to `891c79e` and the approval record moved to round 34 for `.23` with 0.7.106; 0.7.107 is the first release that installs `.23` by default. Their lap 3 corrects our lap 2 twice, both checked against the filed logs and to be acknowledged in our round 35 lap: S26, the log's `ISRC:` lines are the values our app passed, not the disc's (R20); S27, track 5 converged after 3 reads, not 2. **Round 34: `.23` at `891c79e` with our 0.7.106.** Their lap 1 (`cyanrip@fa8e7e4`) filed and verified 2026-10-16; the Full run (426 pass, 0 fail) filed on `evidence` at `fe13de0c` with its manifest rows (PR #346, `97b1d7ab`); our lap 2 (`GO`) written and held. Their held "lap 2" at `cyanrip@d38e28d` renumbers by K1 | On their next lap's `GO`: roll `FORK_PIN` to `891c79e`, move the approval record to round 34 (our lap 2 S15), then release the version that installs `.23` by default | their reading of the run |
| R20 | **[x] Triaged 2026-11-16: done: the cue audit expects the disc's ISRC under `--prefer-disc-isrc` (`2904e732`), and `.25` onward carry the fork's check (round 35 closed).** *Was:* **The disc's ISRC is read and then overridden by ours.** `.23` reads each track's ISRC from the disc's sub-channel and keeps it only in the `--diagnostics` record (`isrc_disc`); the tag and the log's `ISRC:` line take the value our app passes (`cyanrip@891c79e:src/cyanrip_main.c:886-888`), and our app passes the MusicBrainz ISRC for every track (`src/platterpus/adapters/cyanrip_backend.py:1152-1153`). A MusicBrainz ISRC names a recording, which can carry several; a disc ISRC is a measurement of this pressing. Found by the fork's round 34 lap 3 S26, which corrected our lap 2 S6. **The operator chose the fork's route on 2026-10-16, for round 35:** (1) a cyanrip log line per track for the disc read, separate from the metadata as CD-TEXT is, giving the code or `none reported by libcdio`; (2) a cyanrip option our app sets to prefer the disc's ISRC over the one it passes; where both exist and differ, both are recorded and the judgement is ours | **[~] Ours, done 2026-10-16 without the fork:** the report records both values per track from the `-j` record the album pass already writes (`disc.isrc_provenance`, schema v35, `isrc_provenance.py`), with `isrc_disc_differs` and `isrc_disc_malformed` as info issues. **Part 2 done 2026-10-16 for round 35, against `.24` (`93afa15`):** the `Disc ISRC:` line is parsed per track (`code` / `none` / `unknown` with its reason) into the report; `--prefer-disc-isrc` goes through the argv chokepoint only to a build tag in `BUILD_TAGS_ACCEPTING_PREFER_DISC_ISRC`, behind the `Disc ISRC` setting (default on); the report records what we passed, the disc's value and the files', compares the disc with what we passed, and records whether the option was sent (`tests/test_disc_isrc.py`). The Full run sends it in F and leaves it out in J2. Shipped in 0.7.108; our round 35 lap 2 accepts the wording with (a) and (b). **The check inside cyanrip landed for `.25` at `cyanrip@72a7a8b`** (their laps 4 and 5, ISO 3901 by our report's pattern, both modes); 0.7.109 reads its `<code> (not an ISO 3901 code, so not used)` line, and our report now checks a code as written, so the two agree. Still open: `.25` itself, which waits for 0.7.109's publication; until then our report flags a malformed disc code (`isrc_disc_malformed`). **2026-10-26 (`docs/eac-parity.md` Part F row 22; [~] in progress on the session branch on 2026-10-26, not committed at `bd194381`):** `.26` reads the disc's ISRCs, 14 of 14 matching EAC's cue on the reference disc, and our own cue audit then warns: `cue_validate._check_isrcs` compares the cue with the codes we *sent*, with no case for `--prefer-disc-isrc`, so the disc's own code reads as `cue_isrc_mismatch`. It failed L726, L1109 and L1274 on the reference disc (2026-10-21, `round36full1021ascriptreport.json`, evidence `ab3b1395`) and L726 and L1274 on disc 4 (2026-10-22), where the disc's `USZO10001709` and MusicBrainz's `USZ010001709` differ by a letter O. Fix: compare with the code written, which `disc.isrc_provenance` already records. The fork's lap 8 S10 (held) names it too | theirs: (c) in the release after `.24` |
| R21 | **[x] Done 2026-10-19 (operator: a prompt must never open as a window of its own or inside Settings).** The release picker was already parented to the main window and centred over it (`ui/main_window.py`, `ReleasePickerDialog(releases, self)`). The one loose prompt was the fatal-error box (`app.py`), built with no parent, so a desktop could place it anywhere, give it its own taskbar entry or put it behind the app; it now takes the active window. `tests/test_dialogs_have_a_parent.py` reads every dialog construction in `src/platterpus` (a floor of 25) and refuses one with no parent; the uninstaller is the one exception, because `--uninstall` runs without the main window | If the operator still sees a prompt open apart from the window, a screenshot or the run's bundle names which one | ours |
| R22 | **[x] Done 2026-10-19:** `src/platterpus/rig_scripts/quickcheck.txt`, run with `--run-script quickcheck`: ripper, offset and disc checks, one track (2) ripped with overread off and graded, then the bundle; held by three tests in `tests/test_rig_scripts.py`. Not yet run on the rig. Was: **A short custom run the operator can start as one file.** The Quick and Standard runs are sections of the acceptance script; the operator asked (2026-10-18) for a script of their own for a quick check before a Full run. Decided for round 35: run the Full run. Still worth having: one packaged rig script, run with `--run-script`, that rips one track, checks its AccurateRip and CTDB verdicts and the report, and bundles, in under ten minutes | A packaged `quickcheck.txt` under `src/platterpus/rig_scripts/` with its test in `tests/test_rig_scripts.py` | ours |
| R23 | **[x] Released 2026-10-19:** 0.7.109 published (0.7.110 follows on the owner's word "When you are both ready do a new release", reviewing `.25`) at 22:52 UTC from `fe557e80` (release run 39337620305), on the operator's word ("When complete make the new release new lap etc. I want to do a new test run"); our round 35 lap 14 tells the fork, whose `.25` waited on it. The release hold of 2026-10-12 in `CLAUDE.md` is unchanged: the word covered this release, and the line is the operator's to change (the claude-code-skills review of 2026-10-19 asks for it to be restated) | Nothing more for 0.7.109 | done |
| R24 | **Triaged 2026-11-16 (HARDWARE): the Full-run half is done (R39, evidence `37482669`; round 35 closed GO/GO); the `overreadprobe` run was never filed (no row in `docs/evidence-manifest.tsv`) and stays the owner's, at the drive.** **File and read round 35's bundles.** The Full run on 0.7.108 with `.24`, then `--run-script overreadprobe` (the bounded `-O` read, last track at +667 and track 1 at -667) | File both on `evidence` with manifest rows (`scripts/evidence_file.py`), grade the Full run in `docs/testing.md` §5B, write our next lap with the readings, close round 35 | ours, on the uploads |
| R25 | **[x] Triaged 2026-11-16: done: all four rows are in `docs/seam-commands.md:113-116`, HAVE on both sides.** *Was:* **The four `docs/seam-commands.md` §1 rows** (`-T`, `-U`, `-W`, `--diagnostics`) and the count sentence, proposed in our lap 6 S17 | Land them in both trees in the same round, byte-identical, once the fork accepts | both, on their acceptance |
| R26 | **[x] Done 2026-10-19:** parsed per track into the report (schema v37) with the `beyond_disc_frames_refused` info issue, `tests/test_beyond_disc.py`; not yet seen from a drive. Was: **`Beyond disc:` per track into the report** (our round 35 lap 2 S9 WILL). `.24` prints `Beyond disc: N of M frames refused (written as silence)` per track (`cyanrip@93afa15:src/cyanrip_log.c:481`); our parser does not read it yet | Parse it with a named-group regex and a never-raises property test; record it per track in the report; a refused frame written as silence is an info issue on an overread rip | ours |
| R27 | **Triaged 2026-11-16 (STALE-BUT-OPEN): the tags are in (`deps/fork_source.py:1935-1943`, through `edb73dd`); the ISO 3901 clause is still not in the shared row (`docs/seam-commands.md:112`), which moves only in a lap.** **When `.25` is cut:** add its tag to the build-tag sets (`BUILD_TAGS_ACCEPTING_PREFER_DISC_ISRC` and the rest), regenerate the ripper inventory from `.25`'s provider contract (`scripts/emit_ripper_inventory.py`), and add the ISO 3901 clause to the seam row's meaning cell | In the round that puts `.25` under review | ours, on `.25` |
| R28 | **[x] Done 2026-10-19:** `tests/test_no_whole_repo_rglob.py`; four walks converted to `repo_files`, two allowlisted. Was: **A ratchet against new whole-repo `rglob` walks in tests.** Two races with tool caches (R18, and the conflict scan this session) came from tests walking the tree with `rglob`; `tests/conftest.py::repo_files` is the shared walker that tolerates a vanishing directory and prunes the caches | A test that refuses a new `Path(...).rglob` over the repository root outside `conftest.py`, with an allowlist that may shrink, never grow | ours |
| R29 | **Triaged 2026-11-16 (OWNER): unchanged: the operator watches upstream issue 167.** **Upstream issue 167 (https://github.com/cyanreg/cyanrip/issues/167) has no maintainer reply as of 2026-10-19.** Corrected by the operator's review of 2026-10-19 (item 2), read from the public page at 18:40 UTC: no comments, labels or assignees, and the one entry after the body is GitHub's automatic note that a fork commit referenced it. This row said the issue "has a maintainer reply we cannot read from here", which was not so. Also from that review: a commit message or pull request that writes the owner/repo#number form posts a notice on upstream's issue, so ours name it as "upstream issue 167" with the URL | The operator checks the page from time to time and posts reports 24 and 25 there; we answer any reply in the next lap if it bears on our use of the flags | operator |
| R30 | **[x] Fixed 2026-10-19:** `diagnostics_args_for_build` (`adapters/cyanrip_backend.py`) sends `--diagnostics` only when the banner names the fork, or when no banner was read, and both routes (the rip argv builder and a script's `(diagnostics)` placeholder, which now notes the omission) call it. A stock build, whose banner reads `(release)`, and any tag we read but do not recognise get none of our three long options. Keyed on the fork's ID rather than `--consumer`'s commit list, so a fork build agreed after a release keeps its record. Held by `tests/test_stock_build_argv.py`, which reads the stock tag from a real stock 0.9.3 log in `output_reference/`; both routes revert-probed. Was: **a stock cyanrip would refuse every rip on `--diagnostics`**, found by the 2026-10-19 docs audit from source: stock cyanrip 0.9.3.x, which the setup wizard installs from the COPR before building the fork, parses options with `getopt`, has no long options and returns 1 on an unknown one (`cyanrip@063d848:src/cyanrip_main.c:1797-1798`) | Shown by running: one rip, or one `-I` probe, against a real stock 0.9.3 binary, which this container does not have; the operator's review of 2026-10-19 (item 1) asks for it in CI or a container | ours |
| R31 | **Triaged 2026-11-16 (OPEN-OURS): the exit-code part is done; `-X`, `-C` and `-B` still read `?` in our column (`docs/seam-commands.md:145,151,153`).** **Three §1b cells we left `?` in our round 35 lap 8 S5:** `-X` (whether a data track's raw binary belongs in an archive), `-C` (our cover art goes in after the rip; whether `-C` should replace that) and `-B` (whether a rip under `-N` fingerprints at all). And the fork's builds our lap 8 accepted or named: error positions and all-reads counters (read into the report 2026-10-21, R44; the EAC-layout wording is still open), `--encoder-option`, exit codes 64/74/128+N (ours to map in `ripper_exit.py` once built; **mapped 2026-10-20** for `.25`: `ripper_exit_class.py`, the status line and `outcome.ripper_exit_class`) | Settle each cell with `NO: <reason>` or a change, in a lap; ~~map the exit codes when a build carries them~~ (done) | ours |
| R32 | **Triaged 2026-11-16 (OWNER): larger since: `CLAUDE.md` is 678 lines and 98,907 bytes, `TASKS.md` 9,272 lines, `CHANGELOG.md` 20,050 lines (`wc`, 2026-11-16); the move waits on the owner's confirmation for the locked sections.** **`CLAUDE.md`, `TASKS.md` and `CHANGELOG.md` are far past a workable size** (the operator's review of 2026-10-19, item 3): 404 lines and 86,027 bytes, 9,015 lines and 895,531 bytes, and 19,105 lines and 1,373,241 bytes, against a standard of 300 lines and 32 KiB for `CLAUDE.md`. Stale rules there have already cost round trips (the release hold, R23) | After round 35 closes, as a change of its own: keep in `CLAUDE.md` only what a session needs on every task, each rule with what fails without it; MOVE the rest (history to `PLANNING.md` or `docs/archive/`, procedures to the documents they describe, finished rows to a dated archive, old CHANGELOG sections to an archive file), never summarise it away (rule #7), and add a test that holds `CLAUDE.md` under the cap. Rule #7 itself and the CLAUDE.md lock need the maintainer's confirmation | ours, maintainer confirms |
| R33 | **[x] Done 2026-10-19:** our round 35 lap 13 answers the fork's lap 12 (released at `cyanrip@820c0c55`): their `seam-commands.md` copied at `f8d42052` (sha256 `d4dcd5ec…`), their S3 count correction taken (our lap 11 S3's "37 and 7 lines" is 37 and 8; the sites hold), their S4 noted (the run goes through 0.7.108), and our lap 11's ruff version corrected. First held back under the operator's review of 2026-10-19 (item 5); our two shared-file checks (`tests/test_handshake_tooling.py`) then failed, ours against our tree and theirs against our copy, because a copy of a jointly owned file has to travel with the lap that declares its hash | Nothing more; the next lap of ours reads the Full run | ours |
| R34 | **[x] Fixed 2026-10-19 (P1 of the claude-code-skills audit check):** a CTDB match is green only when its entry is the plurality for the TOC and AccurateRip rejects no track. `CtdbVerifyResult` records `best_confidence` and `total_confidence`; `outvoted` makes a match untrustworthy; `minority_match_sentence` is the one wording ("matched 1 of N CTDB submissions; K disagree"); `ctdb_verdict_level` takes the rip log and turns amber beside a track AccurateRip compared and did not verify (`verdict.accuraterip_rejected_count`). Report schema 38. Held by `tests/test_ctdb_outvoted_match.py`, built from the real round-32 report and log; both conditions revert-probed. Was: 8 of 26 shipped rips of the reference disc showed a green "verified (confidence 1)" while the strongest entry had about 1,405 submissions | Ships in the next release. Still open beside it: per-track CTDB, the offset-shifted sweep and localisation (R43, the audit's own CTDB row). *2026-10-26:* `docs/eac-parity.md` Part F row 11 (CTDB check, Behind on naming samples) cites this row and R43 | ours |
| R35 | **[x] Fixed 2026-10-19 (P4 of the claude-code-skills audit check):** the report's `accuraterip_summary` and the window's fallback quoted cyanrip's first-pass "N/M tracks ripped accurately" after a securing pass had fixed a track (`round27fullwholediscreport.json` and `round30fullwholediscreport.json` say 12/14 beside a verdict of 13 of 14). The auto-fix merge now recounts N from the shipped tracks (`verdict.recount_accuraterip_summary`); held by `tests/test_auto_fix_convergence.py`, revert-probed | Nothing more | ours |
| R36 | **[x] Triaged 2026-11-16: done: ruff `>=0.17.2,<0.18` and mypy `>=2.4,<2.5` (`pyproject.toml:123-124`), every job on `ubuntu-22.04`, the AppImage on Python 3.14 (`build/build_appimage.sh:278`, R100), and both action comments name exact releases; PySide6 6.12 and a 3.15 leg are R101.** *Was:* **Every dependency on its newest release, checked weekly** (the owner's word of 2026-10-19, *"are all repos using the most up to date of all dependcies, they should. And we need a way to make sure they are. Like a weekly repo check"*; P10 and S2 of the claude-code-skills report). **Done 2026-10-19:** `.github/workflows/dependencies.yml` runs `skillcheck --outdated` every Monday and keeps one issue open while anything is behind; `actions/upload-artifact` 7.0.1 to 7.0.2 (`cf430e03`, tag verified by `git ls-remote`). **Open, each its own commit because each moves a gate or the runtime (rule #11):** `ruff` to `>=0.17.1,<0.18` (may reformat; re-run the gate); `mypy` to `>=2.4.0,<2.5` (strict flags are version-dependent); `PySide6` 6.12 (Dependabot #332; the minor pin exists because a patch removed two shortcuts, so the shortcut and conformance tests decide); Python 3.15 in the CI matrix, then the single-version jobs; the AppImage's Python 3.12 (`build/build_appimage.sh`), which users run; every job's runner image (named, not `-latest`); exact releases in the comments of `attest-build-provenance` and `gh-action-pypi-publish` | One per pull request, each with its gate re-run | ours |
| R37 | **[x] Released 2026-10-20:** 0.7.110 published at 00:22 UTC from `e4b0115d` (release run 39346990446; PyPI 0.7.110), on the owner's word "When you are both ready do a new release. Then let me know so I can do a full acceptance test." It reviews `.25` (`5f1d036`, `PIN_UNDER_REVIEW`) and still pins `.23` (`891c79e`, `FORK_PIN`); it carries R34 (CTDB minority match), R35 (recounted AccurateRip summary), R30 (no long options to stock cyanrip) and the weekly dependency check. The release hold of 2026-10-12 is otherwise unchanged | The operator's Full run on `.25` with 0.7.110, then the `overreadprobe` script; we file the bundle and write the reading lap | operator, then ours |
| R38 | **[x] Built 2026-10-20 (P2; *First-rip proof* items 1 and 2):** a disc AccurateRip can't vouch for is read twice by default, on the owner's word *"yes, read twice by default"*. The parser now reads cyanrip's disc-level `AccurateRip:` line, because the per-track `Accurip:` row says `not found` both for a failed lookup and for a disc the database lacks (`cyanrip@3861b266:src/cyanrip_log.c:669-671` and `:1037-1041`). `accuraterip_standing.py` sorts a disc into in the database, not in it, lookup failed, or not determined. The securing pass re-reads every track of the last three with `-Z` (trigger `second_read`). A disc in the database whose every track failed now re-reads the failing tracks toward its entry; until today it was skipped as "not in AccurateRip". The verdict is the named **"Reads agree … not verified by AccurateRip"** (`verdict.basis` = `reads_agree`, report schema 39), amber when a track's reads disagree. The estimate and the plan say an unknown disc reads twice. The opt-out is Settings → *Read every track twice when AccurateRip can't vouch for the disc*, with each skip reason recorded. Held by `tests/test_second_read_default.py`, `tests/test_securing_pass.py` and `tests/test_rip_worker.py`; five reverts probed | Ships in the next release the owner gives the word for; reported to the fork in our next lap. Open: whether `-Z 1` would do (P2 item 5, for the fork and us), and the timed rip with and without upstream `7dbe56a` (the owner's, at the drive) | ours |
| R39 | **[x] Filed 2026-10-20:** the operator's Full run on `.25` (`5f1d036`) with 0.7.110. Evidence commit `374826695ec2233ae685be7f797d75e6aa326db5` (80 files, `docs/handshake/artifactsround35/`), manifest rows added, ledger row `partial` (`docs/testing.md` §5B): 434 pass, 1 fail, E2 unreachable, 6 info. Fixed from it, each with a regression test: P2's `expect-exit 1` met `.25`'s agreed exit class 64 (`expect-exit refused`, `ripper_exit.refusal_exit_code`); a CTDB no-match dropped its entries' weights (`ctdb/verify.py`); the export's redaction kept a username after a JSON `\n` escape (`export_redaction.ESCAPE_AWARE_START`, also in `export_identity`). Lap 17 is the fork's, decided 2026-10-20 on the operator's word that only one side writes it | Our lap 18 reads the run after their lap 17: tracks 3 and 5 converged on values AccurateRip rejects, the round08joint SECTION C refusals that still expect 1, their `tools/redact.py` sharing the escape gap, and the `overreadprobe` run still to do | ours, after the fork's lap 17 |
| R40 | **[x] Fixed 2026-10-20 (the fork's round 35 lap 17 S10, first in their round 34 lap 3 S22):** the acceptance runner latched `no read exceeded 10s` from a refused rip's summary as the ripper's build tag, so the deemphasis rip after it sent no `--consumer` or `--diagnostics`. The latch now reads only a banner-shaped line (`ripper_identity.version_banner_in`, `813ecfd4`); held by `tests/test_uiscript_cyanrip_verb.py`, revert-probed | Nothing more | ours |
| R41 | **[x] Round 35 closed 2026-10-20:** the fork's lap 17 (`GO`, `cyanrip@8885ed23`) filed at `43809a1f`; our lap 18 (`GO`) released on the standing word, with `FORK_PIN` rolled to `5f1d036` and the approval record to round 35 with 0.7.110, after PR #369 (`bccf8d7a`) put the run's manifest rows on `main` (HR-2 §6b). **Open for 0.7.111** (the owner's word of 2026-10-20): as many fixes as are ready, so the next Full run tests them; `.26` with upstream `7dbe56a` as the build under review if it is out; the timed `.25`-vs-`.26` rip in the Full run until both sides agree the result is clear (threshold in round 36 lap 1). Candidates: the report's reading of exit 64, 74 and 128 + N; the flaky `test (py3.13)` leg; the EAC audit branch (`ccr-3c66e173-5708ow`, Part E), taken over and merged with its rows renumbered R42 to R44 and the report's P3, P5 to P8 applied; error positions in the report; the R36 bumps; the claude-code-skills pin in the weekly workflow (0.1.18, `9c545d6`) | Round 36 lap 1 is the fork's | ours |
| R42 | **[x] Triaged 2026-11-16: done: the owner's EAC re-rip of 2026-11-12 is filed (`00a3592b`, `output_reference/EAC_wav/`), and EAC also failed to verify tracks 3 and 5 (12 of 14; `docs/eac-parity.md` G.7), so by this row's own test the misreads point at the disc or drive, not at a change on our side.** *Was:* **Is the reference disc wearing out, or have our reads of track 3 got worse?** Found by the 2026-10-19 EAC audit (`docs/eac-parity.md` Part E §E2): we read track 3 right (`59D352DD`) in 9 of the first 11 rips and in none of the last 15 (since 2026-09-30); EAC's last session was 2026-06-25, and two of its three sessions also misread track 3. Nothing on record separates a worn disc from a change on our side | One EAC rip of the reference disc now, on the BDR-209D (Windows, or EAC under Wine), with its log committed beside the others in `output_reference/`; if EAC also reads track 3 wrong, it is the disc. Untick EAC's CTDB submission for that rip: a third EAC entry carrying the same misreads would add weight to exactly the entry R34 learned to distrust (the claude-code-skills check of the audit, §7) | maintainer, on hardware |
| R43 | **Triaged 2026-11-16 (STALE-BUT-OPEN): repair is built and proven on hardware: the 2026-11-10 Full run met the pre-registered values, `C96464AB` and `5092E94B` (our round 38 lap 17 S3). Left: CTDB submission (`docs/eac-parity.md` Part F row 13) and the by-hand track-3 localisation on EAC's wav session.** **[~] CTDB per track and over every offset, built 2026-10-21; localisation built 2026-10-26; repair built 2026-11-04, and run automatically after a rip from 2026-11-05 (R133, no button); submission not built.** *Per track:* each track is compared with every entry's `trackcrcs` the way CUETools' `GenerateLog` does, at that entry's offset (read from where most of its tracks agree with ours, `ctdb/matching.py:136`) or within ±2939 (`:165`); tri-state per track with the summed confidence, in the verdict message, the results pane, `--ctdb-calibrate` and the report's `ctdb.tracks`. *Offset sweep:* the whole-disc CRC is compared at every alignment in ±5879 in the same streamed pass (`ctdb/sweep.py`, `ctdb/verify.py`); a match names `matched_offset`, a no-match says our audio differs from every entry over `offset_range`. Held against the real CTDB answer for the reference disc (`tests/fixtures/ctdb_lookup_police_classics.xml`) and EAC's three logs (`tests/test_ctdb_per_track.py`), by `tests/test_ctdb_sweep.py` and by `tests/test_ctdb_offset_sweep.py`. *Localisation* ("track 3 differs in 16 samples @04:04:68,04:05:17,04:11:32 from the 1,416-submission entry"), **built 2026-10-26 on the owner's word on numpy** (*"numpy; record what it adds to the download"*, 02:19 UTC; DEPENDENCIES.md has the measured cost): CUETools' `CDRepairEncode.VerifyParity`, clean-room (KDD-16). The entry's parity record is fetched from its `hasparity` URL (`adapters/ctdb_parity.py`; its layout, rows of 11,760 little-endian syndrome words, checked against the real record for entry 32115, whose row heads equal the lookup's `syndrome` attribute); our syndromes over GF(2^16) (`ctdb/gf16.py`) come from one streamed numpy pass (`ctdb/syndromes.py`, 0.64 ms a row, about 17 s for the reference disc's 26,866 rows on the 2026-10-26 session box) and shift to any alignment in ±5879 without another pass; a clean-room Berlekamp-Massey, Chien and Forney decoder (`ctdb/rs_decode.py`) names each differing column's rows; and the corrections must reproduce the entry's CRC (`ctdb/verify_parity.py`) or nothing is located. It runs against at most the three strongest entries with parity that our disc does not match and that outweigh the one it does (`ctdb/localise.py`), in a second, lazy decode pass on the CTDB worker, bounded to 300 s; every failure reads "not determined" with the reason (numpy not installed, record unavailable or mismatched, time bound, too many differences). It reaches the verdict message, the results pane, `--ctdb-calibrate` (a `Localisation:` line and EAC's `(1,416/1,441) differs in ...` per track) and the report (schema 40: `ctdb.localisation`, `ctdb.tracks[].differences`). Held by `tests/test_ctdb_syndromes.py` (an independent reference encoder, every alignment, and CUETools' systematic-parity form converting to our definition), `tests/test_ctdb_rs_decode.py` (injected errors decode exactly; a never-raises property whose every answer reproduces its syndromes), `tests/test_ctdb_localise.py` (synthetic discs at offsets 0, +667 and -1500 locate exactly the injected samples; our wording equals EAC's committed track-3 and track-5 lines; random parity never raises) and `tests/test_ctdb_parity.py`. **Run on hardware 2026-10-28, on EAC's FLAC session:** the owner's `--ctdb-calibrate` on EAC's FLACs of the reference disc (0.7.114, `95691b5`) located track 5's difference exactly as EAC's own log does: ours *"track 5 differs in 3 samples @02:24:59 from the 1,419-submission entry"*, entry 32115 located at offset -7, against EAC's *"(1339/1441) Differs in 3 samples @02:24:59"* (`output_reference/EAC_flac/eac_baseline_police_classics.log:264`); the other 13 tracks agree with 1,485 to 1,512 of 1,521 submissions at offset -7, and the whole disc matched one minority entry at +0, reported as not corroborating. **Still hardware-gated, and not claimed:** that EAC's own wav session of the reference disc (`output_reference/EAC_wav/`) locates track 3's 16 samples at `04:04:68,04:05:17,04:11:32` here; that needs the owner's audio. *Repair*, **built 2026-11-04 on the owner's word** (*"Start building CTDB repair now? yes"*; KDD-14 amended): CUETools' `CDRepairFix.Write` natively, the step after the localisation, with `neheb/cdverify`'s `src/repair.rs` as the safety reference. The localisation now keeps each correction's XOR value (`EntryLocalisation.values`) and each track's whole-PCM CRC-32 (`CtdbLocalisation.track_crc32s`). `ctdb/repair_plan.py` maps every corrected word to (track, frame, channel) toward the single strongest entry, and refuses, each with its sentence: a minority or tied entry, a rip already matching the strongest, a track AccurateRip verified, a word in a guard band or outside the audio, a pregap or a track not whole sectors, more corrections in one column than npar 8 (4) or 16 (8) carries. `ctdb/repair.py` then requires each affected file to be the audio localised (length and CRC-32), XORs the words, encodes a hidden new file with `flac -8` and copies every metadata block with `metaflac --list --data-format=binary` / `--append` (`adapters/flac_rewrite.py`, refused unless the new file's blocks equal the original's), decodes it back and requires the corrected PCM byte for byte, and measures the whole repaired disc: the entry's whole-disc CRC and the repaired track's CRC at the entry's offset, or nothing is replaced. AccurateRip v1/v2 of each repaired track are recomputed before and after (`accuraterip_crc.py`, ours, checked against Leo Bogert's C `accuraterip-checksum`; there was no AccurateRip CRC code of ours before). `ctdb/repair_commit.py` keeps the original as `<name>.flac.before-ctdb-repair` (hard link, or a compared copy on FAT/exFAT), refuses to overwrite an earlier one, renames the new file in, and undoes everything on a failure part-way. The logs are never edited (KDD-24). `ctdb/repair_run.py` is the thin caller from a `CtdbVerifyResult`; the record is the report's `ctdb.repair` (schema 44). Held by `tests/test_ctdb_repair.py` (synthetic discs at 0, +667 and -1500 restored byte for byte, an npar-8 entry, every refusal with the album unchanged, the commit's link-less and part-way paths, the real `flac`/`metaflac` chain where installed), `tests/test_ctdb_repair_plan.py`, `tests/test_accuraterip_crc.py` and `tests/test_flac_rewrite.py`. **Pre-registered prediction for the owner's disc** (EAC's FLAC session, entry 32115 at offset -7, `tests/fixtures/ctdb_lookup_police_classics.xml`): after repair the whole-disc CTDB CRC at -7 is `5092E94B` and track 5's at -7 is `1CB564CC` (the entry's own, which the proof requires); track 5's Copy CRC becomes `C96464AB`, AccurateRip v1 `134C0B9D` and v2 `BCF4E815`, the values of the one secure re-read AccurateRip verified (`tests/fixtures/evidence/docs/handshake/artifactsround31/round31fullsecurereread.log:437-441`; v2 is also what EAC's log says AccurateRip returned, `output_reference/EAC_wav/eac_wav_police_classics.log:115`), and the value 48 offset-0 CTDB entries hold for track 5. Not algebraic: the three XOR values are not in any committed artifact. *Submission* is out of scope. Found by the 2026-10-19 EAC audit (Part E §E5). Weighing a match against the entries that disagree is R34, done | *Repair, next:* **done 2026-11-05 as R133** (no button, on the owner's word: the repair runs on its own after a rip, on a worker with a real `cancel()` through `killable.KillableJob`, fed AccurateRip's per-track answer from the rip log, recorded with a fresh verify beside the read's verdict, and the derived copies made again from the repaired FLAC); no `ctdb-repair` script verb, since the scripted rips reach it through the app's own pipeline. Left: the owner's hardware proof on a copy of EAC's FLAC session against the prediction in this row. The owner's run: `--ctdb-calibrate` on a FLAC copy of EAC's wav session (`flac *.wav` in that folder), whose `Track | CTDB per-track result` table must read `differs in 16 samples @04:04:68,04:05:17,04:11:32` for track 3 against the dominant entry; the first AppImage built with numpy gives its real size; then submission. *2026-10-26:* `docs/eac-parity.md` Part F row 11 (Behind on naming samples: the syndrome pass, on the owner's word) and row 13 (CTDB submission, Behind: build it, and never submit a rip with a track AccurateRip rejects, as EAC's plugin did with track 5, `output_reference/EAC_flac/eac_baseline_police_classics.log:258`). Per track and the offset sweep ran on hardware in the four Full runs of 2026-10-21 and 22 (the plan of record's Appendices G and I); a match at a nonzero offset has not occurred yet | ours; the run is the owner's |
| R44 | **Triaged 2026-11-16 (OPEN-OURS, parity): unchanged: Part F row 10 still reads Behind (`docs/eac-parity.md`), and the three damaged-disc defects were not found fixed.** **Error positions, once a released fork build prints them.** EAC logs where a track was doubtful; the build users get (`.23`) prints only counts. The fork's tip records positions (`cyanrip@820c0c5:src/cyanrip_main.c:643-645`), accepted in our round 35 lap 8. Found again by the 2026-10-19 EAC audit (Part E §E4). **Parse and report done 2026-10-21** for `.25` (`cyanrip-diagnostics/10`): `error_positions.py` reads `error_positions`, `error_positions_dropped` and `paranoia_all_reads` per track through the one `track_state` reader, tri-state and bounded, with a never-raises property test, into the report's `disc.error_positions` and the `error_positions_reported` warning | ~~Parse them with a never-raises property test, put them in the report~~ (done); agree their EAC-layout wording through the handshake (the fork diffs that log). *2026-10-26:* `docs/eac-parity.md` Part F row 10 (Behind; both sides). On the damaged disc (2026-10-21) the report carried positions, with three defects (the plan of record's Appendix H §4): track 18's `skips` states the list's 1,000, not paranoia's 2,076; positions repeat (track 17's 28 entries cover 16 sectors); and the securing pass's positions never reach the report (track 12's skip at LSN 151669) | ours, on the build that carries them |
| R45 | **[x] Triaged 2026-11-16: done: round 36 closed GO/GO (`scripts/handshake.py --status`).** *Was:* **Round 36** (opened by the fork's lap 1, `cyanrip@088557c`, 2026-10-21): it reviews `.26` (upstream `7dbe56a`, `Accurate stream:`, `Recordable:`, the two-search `Pregap source:`) and closes on the Full run on `.26` through our first release that reads the three lines, with a timed `.25`-vs-`.26` rip in it. **Done:** lap 1 filed (`c3d49341`), the opener floor taught the `TERM set` form (`e7b8ab0d`), the three lines parsed and reported (`7a3817a3`), SECTION C's six exit classes (`c3d49341`); our lap 2 released 2026-10-21 on the owner's standing word (`cb82d620`); 0.7.111 published 2026-10-21 04:50 UTC from `cb82d620` with `.25` by default, reading the three lines (the claude-code-skills note asked for it now rather than with `.26`); the timed-rip script support built (R46). The fork released `.26` at `ca0f097` with its lap 4 (`cyanrip@32d17db`). **The owner's word of 2026-10-21:** *"Yes: once .26 is released, move round 36's pin to .26."* Their lap 4 and `.26`'s provider contract (built at `ge2b52b1`) filed, `PIN_UNDER_REVIEW` moved to `ca0f097` (`release_seq` 37, read off their manifest at `a085d19`), the ripper inventory regenerated, `.26`'s tag added to the `--consumer` and `--prefer-disc-isrc` sets, and the three `.26` rows retired from `_FORK_ONLY_WITHOUT_A_PUBLISHED_LITERAL` now that its contract publishes them. | Done: lap 3 released (PR #377); 0.7.112 published 2026-10-21 06:51 UTC from `9bf0cd34`, naming `.26`. Next: the owner's Full run on `.26` through 0.7.112 with the timed rip, filed with manifest rows, and our reading in a lap | ours |
| R46 | **[x] Triaged 2026-11-16: done: the ratios were measured in all four round-36 Full runs (this row's 2026-10-26 note), and `.25` and `.26` are both retired; P5 still runs whenever two builds differ.** *Was:* **[~] The timed `.25`-vs-`.26` rip, scripted (2026-10-21; the owner's ask, the fork's round 36 lap 1 S15).** Section P5 of the Full run installs the approved build and the build under review in turn (`install-ripper`, the same `deps/ripper_install.run_install` as `--install-ripper`), rips tracks 1-3 four times (approved, review, approved, review) with no securing pass and a fixed read speed, records each rip's `Elapsed:` seconds (`record-timing`), and prints both pairs' ratios and whether they agree within 0.05 (`compare-timings`); all `info`. Between rounds it says `nothing to compare` and marks its steps N/A (`skip-if-same-build`). Held by `tests/test_uiscript_timing_verbs.py` and `tests/test_ripper_install.py` | The first Full run once `.26` is `PIN_UNDER_REVIEW`: its two ratios, and P5's real duration recorded in its header. *2026-10-26:* ran in all four round 36 Full runs: `.26` took 0.348 and 0.346 of `.25`'s time on the reference disc, 0.354 and 0.354 on disc 3, and 0.197 and 0.193 on disc 4, each pair within 0.05 (the fork's lap 8 S8, held). Against EAC: R55 | ours; the run is the maintainer's, on hardware |
| R48 | **[x] Triaged 2026-11-16: done: `.27` was released and named by 0.7.114 (R80), and its tag is in the capability sets (`deps/fork_source.py:1938`).** *Was:* **[~] Reading the fork's `.27` (their round 36 lap 7, `cyanrip@fc73b4d`; S3 to S6, S9, S15), built 2026-10-26 on our side.** `.27` is built and not released, and is cut once a release of ours reads its two new lines (their S9). **Done:** `Kept read began:` per track into `TrackResult` and the report (schema 40, `kept_read.py`); the `/11` record's `kept_read_began` and `isrc_disc_read` (`record_track_v11.py`), a `/10` record reading as before; the footer's `not written whole:` paths into the report, one warning per file and the status line (`written_whole.py`); `--prefer-accuraterip-match` through the argv chokepoint behind an empty build-tag set (R7); `.27`'s audio-track tally checked against the report and the verdict (no change needed, a test pins it). | Name the release that reads the lines and `/11` in our next lap (their S9); add `.27`'s tag to the capability sets on its release, after checking its contract | ours |
| R47 | **[x] Filed 2026-10-26:** the owner's four Full runs on 0.7.112 with `.26` under review (2026-10-21 11:35 and 21:45 UTC, 2026-10-22 11:45 and 21:57 UTC), on `evidence` at `ab3b1395`, `08de9851`, `fc48882f` and `6b31795c` (308 files, `docs/handshake/artifactsround36/`, prefixes `round36full1021a` to `round36full1022b`), with manifest rows. The filing tool learned the timed rips' folders, `install-ripper`'s records, a rip's loose files, and the verified-read chase's wrapper (each embedded log verified, the argv lines' home folder redacted: 10 replacements) | Read the four runs (findings, ledger grade, our lap) | ours |
| R49 | **Triaged 2026-11-16 (STALE-BUT-OPEN): the time budget is built, in the chase (`chase_budget.py`; `chase_record.STOPPED_TIME_BUDGET`) and on the securing pass (`securing_time_limit.py`, `--reread-time-limit`); left: the "unreadable on this drive" verdict and a stop-this-track control, neither found in `src/`.** **[ ] A per-track time budget for re-reading, and "unreadable on this drive" (`docs/eac-parity.md` Part F row 5, Behind).** On *Roots Music* disc 1, 2026-10-21, the album pass read track 18 in 8,548 s with 2,076 paranoia skips (`round36full1021bwholedisc.log:1441`, evidence `08de9851`), the securing pass's `-Z 2 -r 5` began reading it again, and the Full run's 6-hour wait stopped the rip in its second re-read; the plan of record projects 20 to 24 hours to the end. Every bound is a count (`-r`, the chase's 5), none a time. The plan's proposal (Appendix H §5): run the securing pass one track at a time, or swap what a stopped pass finished (R7); give each track a re-read budget, for example the larger of 5 × its length and 2 × its album-pass read time, keeping the best read with `stopped_reason: "time_budget"`, in the chase loop too; skip the chase for a track whose every read carries skips; offer "stop re-reading this track"; and report "Not verified: unreadable on this drive" with each read's time and CRC and the skip count from the counter. Its drive-free tests are listed there. Section F of the Full run waits 6 hours, sized for a clean disc | Build the budget and the unreadable verdict, with the drive-free tests. **The owner, 2026-11-03: pass `.28`'s `--reread-time-limit` after 0.7.118, with a default they choose (R125)** | ours; what `-r 5` means beside EAC's 82 reads is the fork's |
| R50 | **[x] Built 2026-10-26; sent in our round 36 lap 9 S19 (released 2026-10-26) (row 8): never a clean word over a track AccurateRip contradicts.** The 2026-10-21 Full run's secure re-read shipped track 3 as `3D8FCF0C`, matched on frame 450 only, under "confirmed across 4 secure re-reads … Copy OK" and "No errors occurred". One predicate, `verdict.track_accuraterip_contradiction` (`wrong`: frame 450 matched and the whole track did not; `differs`: compared, nothing matched), now asked by the EAC-layout log (Copy CRC note, a `Proof: none — WRONG: …` row, EAC's `Copy finished`, and EAC's `There were errors` with the ripper's count on a labelled line), the report (`tracks[].accuraterip_contradiction`, schema 40) and the results table's Status cell (`⚠ Wrong (AccurateRip)`). `tests/test_wrong_track_never_reads_clean.py`. Not changed: the report's `health_status`, which `rip_audit` grades | Sent: round 36 lap 9 S19 (`58659497`); the fork has not objected. The report's `health_status` is R112, from the 2026-11-03 run | ours; `read successfully!` over such a track is the fork's |
| R51 | **[x] Built 2026-10-26; sent with R50 in our round 36 lap 9 S19 (row 9): one line per track naming which proof its copy has.** `track_proof.track_proof` reads the verdict's predicates and words the strongest proof: AccurateRip v1/v2 at a confidence, a single re-read AccurateRip verifies (the chase), CTDB per track, reads that agreed with no database behind them, or `none` with the reason. The EAC-layout log prints it as a `Proof:` row in every track block; the report carries `tracks[].proof` (`kind`, `line`, schema 40) with CTDB's per-track answer. `tests/test_track_proof.py` **2026-11-03: the log names CTDB.** It is written at the rip's end and again when CTDB answers, from the inputs the first write kept on the album's record (`post_rip_record.EacLogRender`, `_rewrite_eac_log_with_ctdb`), before the report write, so the embedded copy names CTDB too; only over a log the first write made, in the album's own folder, and only when the text changed (`tests/test_track_proof.py`, `tests/test_ui_main_window.py`) | Sent with R50. Keeping Fast Verified as the default with this line printed waits on the owner's word | ours |
| R52 | **Triaged 2026-11-16 (OPEN-OURS): unchanged: KDD-12's 2026-10-26 correction still names no primary source (`PLANNING.md:1225`).** **[ ] Does AccurateRip accept submissions from a program it has not listed? (`docs/eac-parity.md` Part F row 14, Behind, may be not possible).** "Impossible from Linux" had no source (PLANNING.md KDD-12's dated correction, 2026-10-26). AccurateRip's list of compatible programs names five, none for Linux, and does not say whether it refuses others | Find a primary source and record the answer in KDD-12 and Part E §E5; writing to AccurateRip is the owner's call. If it refuses, close as not ours to change | ours |
| R53 | **Triaged 2026-11-16 (HARDWARE): unchanged: no filed run shows the probe starting on open and dying on *Skip check*.** **[~] Measure cache defeat once per drive in setup (`docs/eac-parity.md` Part F row 17, Behind on the default). Built 2026-11-12; a hardware run is left.** `cd-paranoia -A` ran only when the user pressed *Analyze cache* (KDD-29), so a drive never analysed logged no verdict, where EAC logs the setting on every rip. Now Set up drive starts the same worker by itself when it opens for a drive with no saved verdict and an audio CD in (`cache_check_plan.decide_auto_check`), with *Skip check* killing the probe; with no disc it says it will start when one is read, and does; a firmware change since the measurement makes it due again (`cache_defeat_release`, beside the verdict in the drive profile); a rip on a drive with no verdict goes ahead with a dismissible status-bar note, and never starts the probe. Held by `tests/test_cache_check_auto.py`. *Left:* the rig confirming `cd-paranoia -A` starts on open and dies on *Skip check* and on Close (the acceptance scripts' `open drive` then `cancel` exercises the second on a drive with no verdict) | Hardware confirmation on the rig | ours |
| R54 | **[x] Fixed 2026-10-26 (`9d2db6fd`, graders `34c72c69`); whether the drive still flickers needs the rig.** **Confirm a drive removal before acting on it (`docs/eac-parity.md` Part F row 33, Behind).** At 12:02:39 UTC on 2026-10-21, after the reference disc's rip had finished, one status poll read the tray open. `MediaWatcher` treats a single OPEN reading as a removal, so the app cleared its disc view, and the auto-rescan's release picker then stood in the run's way: 57 steps failed behind it, L729 to L1086 (`round36full1021ascriptreport.json`, evidence `ab3b1395`). The plan of record (Appendix G §1 B) finds the same 2.4 s open, unavailable, disc pattern while idle in earlier app logs. Its second defect: the tag and cover graders compare the files with the live window, which the blip had emptied, not with the rip's own record. In progress on the session branch on 2026-10-26, not committed at `bd194381` | Land it with a test fed the recorded sequence; the graders read the rip's report | ours |
| R55 | **Triaged 2026-11-16 (HARDWARE, OWNER): unchanged: no timed EAC rip is filed.** **[ ] Time one EAC rip against one Platterpus rip of the same disc (`docs/eac-parity.md` Part F row 34, no data against EAC).** EAC's three sessions ran at 1.6× to 9.1× with Test & Copy; `.26` is 2.8× to 5.1× faster than `.25` (R46). EAC set up as Part F §F4 says | EAC rips of the damaged disc and disc 3, timed | the owner's, at the drive |
| R56 | **[x] Fixed 2026-10-26 (`c6f11f41`).** **The acceptance script's rip and picker races (the plan of record, Appendix G §1 C and D; `docs/eac-parity.md` Part F).** `rip` fails at once while a disc scan is still running instead of waiting a bounded time, and `pick-release` answers any open picker, including one an earlier scan opened: on 2026-10-21 L893 answered the blip's stale picker, and the rips at L897, L965, L1045 and L1073 found Start disabled, 39 steps in all. No step fails fast on a picker it did not expect, so 16 more timed out behind one. In progress on the session branch on 2026-10-26, not committed at `bd194381` | Land it with tests | ours |
| R57 | **[x] Fixed 2026-10-26 (`007ae42a`); the HTTP 500 wording is still open.** **`expect-cover-art` grades before the cover-art result is recorded (the plan of record, Appendix I §2).** The report's `cover_art` block is written only after the release's booklet scans download, 60 to 120 s for a release with 23 to 25 images; `settle_state()` waits for `outcome` and `verification.gates`, not `cover_art`. Disc 3 (2026-10-22) failed L730 and L910 with the files already holding the cover. Latent on The Police release, which has no such images. With it: a Cover Art Archive HTTP 500 for the front cover is worded "could not reach the Cover Art Archive" (R17). The race is in progress on the session branch on 2026-10-26, not committed at `bd194381` | Land it with a test; reword the HTTP 500 message | ours |
| R58 | **[x] Fixed 2026-10-26 (`16413c1d`, R68).** **The derived-file check runs before the transcode writes the files (the plan of record, Appendix I §2, defect 1).** It gives up after about 60 s while the transcode waits behind the cover-art and booklet fetch, so on disc 3 (2026-10-22) no MP3, WavPack or WAV file was verified, and no MP3 in either run of that day. The gate said `not run` honestly, so no step failed. The derived-verify timeout is in progress on the session branch on 2026-10-26, not committed at `bd194381` | Land it with a test | ours |
| R59 | **Triaged 2026-11-16 (OWNER): (b) is done; (a) still waits on the owner's word, because it makes a pass easier.** **[~] (b) fixed 2026-11-03: the audit's grade on 2026-10-26 (`df181a84`, R70), and now `health_status`, the EAC-layout line and the window's status line, by one placement (`replaced_read_errors.py`): "No errors occurred in the reads kept; the ripper's 2 ripping error(s) were all in the first read of track(s) 16, replaced by a read AccurateRip verified", the ripper's own sentence kept as `ripper_health_status` (schema 42), and clean only where each replacement printed no READERR or SKIP. Replayed on run C's secure re-read log and chase read 5. The EAC-layout wording (`No errors occurred` with `Ripper's own count  : Ripping errors: 2 — all in the first read of track(s) 16, replaced by …`) is a line the fork diffs: send it in our next lap. A 0.7.112 report such as run C's own now warns again in the audit, because its track 16 carries the superseded read's `SKIP: 1` (R61's defect), which the narrowing reads. (a) is open.** **(a) is written and HELD for the owner's word** (on a local branch of the 2026-11-03 session only, so if it is lost it is redone from this row: a check `expected_warnings.expected_ripping_error_warning` and the constant `rip_audit.RIPPING_ERRORS_WARNING`, with slim extracts of run C's two filed reports as fixtures): it would let `expect-album-audit` pass a rip whose only completion finding is a ripping-error tally the record places on named tracks, instead of failing it. That makes a pass easier, and a re-grade that makes a version easier to reach waits for the owner (CLAUDE.md, *A version number is a claim about the field*). **The completion audit on a damaged disc, and a replaced read's errors (the plan of record, Appendix I §2).** (a) `expect-album-audit` asserts a clean self-audit on disc 3, whose track 16 has a real skip, though the script's own comment says read instability is not graded (L726, 2026-10-22). (b) After the chase replaced track 16 with a verified read and the verdict said `Bit-perfect: all 16 tracks`, `health_status` stayed "2 ripping errors", counted from the superseded read, and the EAC-layout log printed "All tracks accurately ripped" beside it (L1274). The completion-audit fix is in progress on the session branch on 2026-10-26, not committed at `bd194381` | Land it with tests on the filed reports | ours |
| R60 | **[x] Done 2026-11-03: P4 now runs after P6, so it compares P5's and P6's logs too, and a test holds every `rip` and `cyanrip` step before it; the `unknown` half was already fixed by `4b532452` (commit `7af6c680`).** **`expect-pregaps-agree` misses two kinds of log (the plan of record, Appendix I §2, defect 4).** It runs before section P5's timing rips, so it never sees `.25`'s logs (on disc 4 both omit track 5's 175-frame pregap that all 13 `.26` logs list), and it sets aside any log whose `Gaps:` block holds an `unknown` line (three on disc 3) | Run it after P5; grade an `unknown` line rather than drop the log | ours |
| R61 | **[x] Fixed 2026-10-26 (the owner's plan of record, Appendix I defect 3):** a track whose file is a chase read or a securing re-read reported the superseded read's speed, elapsed time and paranoia counters (run C's track 16: 0.55x, 362.25 s, `SKIP: 1` beside chase read 5's CRC, which ran at 4.8x in 41.53 s with none). `ui/main_window_rip._merge_shipped_track` now takes all four from the shipped read, with no fallback; reproduced from the bundle's album log and verified-read record. `tests/test_auto_fix_convergence.py`. Not in scope: the same rip's `health_status` "2 ripping errors" is still counted from the superseded read (the plan's L1274 finding; `rip_audit`'s side) | The disc-level health count over a replaced track (R59) | ours |
| R62 | **[x] Done 2026-11-03: every caller of the window's Cancel names itself (`cancel_cause.py`: user, script step, run ended, time limit; `not_recorded` otherwise), and the app log, `outcome.cancelled_by` (schema 42), the `rip_cancelled` issue and the EAC-layout log say who (commit `4e6a5e07`).** **Say who cancelled a rip (the plan of record, Appendix H §3).** On disc 1 (2026-10-21) the acceptance runner cancelled at its 6-hour limit, and the app log says "rip cancel requested by the user" and the EAC-layout log "INTERRUPTED (you cancelled the rip)" (`round36full1021bwholedisceac.log:325`, evidence `08de9851`) | Name the user, the test run, or a time limit (R49) | ours |
| R63 | **[x] Done 2026-11-03: a track paranoia skipped on is left out of the drive's learned speed (`rip_estimate.struggled`), and the app log counts them (commit `1f64a39d`).** **The drive's speed estimate learns from a stalled rip (the plan of record, Appendix H §3).** After disc 1 the app folded "3500 s of audio in 9162 s … 0.38x" into the drive's estimate (`ui/main_window_drive.py` does not exclude a rip with stalls or skips), so the next estimate for this drive is about 2.6 times too long | Leave out, or weight down, a rip with stalls or skips | ours |
| R64 | **[x] Done 2026-11-03: `outcome.securing_pass_exit_codes` (schema 42, `securing_exit.py`) records the wrapper's reaped status and cyanrip's own from the kept record, each named, with `agree` (commit `7cf88286`).** **The securing pass's exit code disagrees with the reader's (the plan of record, Appendix H §3).** Disc 1's report has `securing_pass_exit_code` 1 and its `--diagnostics` record `exit_code: 143` (SIGTERM): one is the wrapper's, the other the reader's, and neither field says which | Record both, each named | ours |
| R65 | **[x] Done 2026-11-03: the ladder's no-step line names the skips and unconverged tracks (`ladder_trigger._no_read_errors_reason`), and a stopped securing pass adds its finished unconverged tracks to `unstable_tracks` (commit `0eba0eee`).** **"No read errors" beside 2,106 skips, and an empty `unstable_tracks` beside seven tracks that never converged (the plan of record, Appendix H §1 and §3).** On disc 1 the read-speed ladder logged "no step after pass 1: the drive reported no read errors", which is right by its rule (skips are not read errors) and reads as a clean disc; and `read_speed.unstable_tracks` is `[]` with `unresolved: false` though tracks 11 to 17 never converged (the verdict says so) | Reword the ladder's line; make the field agree with the verdict | ours |
| R66 | **[x] Done 2026-11-03: `plan_chase` counts the unprinted last read from the `at most M reads agreed` line, and `expect-accuraterip` words states through `accuracy_grading.STATE_WORDS` (commit `6d22d55a`).** **Two small record defects (the plan of record, Appendix I §2, defect 5).** `distinct_reads_seen` counts only the `Repeating ripping` values (4) where each securing pass read five; and `expect-accuraterip` labels a frame-450-only match `offset-variant`, a cause our screens stopped naming on 2026-09-24 | Fix both, each with a test | ours |
| R67 | **[x] Fixed 2026-10-26 (run B of the four 0.7.112 Full runs, ARCHIVAL):** a securing pass that was stopped threw away re-reads AccurateRip had verified. Run B's pass (`-Z 2 -l 11…18`) was cancelled by the script's six-hour wait during track 18; its log shows track 11's re-read `Accurip v1: 9FCC4FB0 (accurately ripped, confidence 12)`, v2 confidence 29, yet the report kept the unverified first read (`kept_read: first_read`). Now each track the stopped pass finished is decided on its own (`unfinished_refix.py`): block complete, AccurateRip verifying it by `verdict.reread_supersedes`, and its FLAC closed by its encoder with the read's sample count (`checksums.flac_total_samples`); such a read is swapped in as a finished pass's is. Every track records `pass_unfinished` and `not_replaced_because` (report schema 40). Tests: `tests/test_unfinished_refix.py`, `tests/test_rip_worker.py::test_a_stopped_securing_pass_*` | Confirm on the next damaged-disc Full run | ours |
| R68 | **[x] Fixed 2026-10-26 (run C of the four 0.7.112 Full runs, ARCHIVAL, silent):** the derived-file verify waited a fixed 60 s for the post-rip thread. Run C's MP3, WavPack and WAV transcodes took 86 to 121 s (they wait for cover art), so each verify found nothing and recorded "not run — no mp3 files found to verify" (app log lines 18991, 19336, 19679), and `expect-derived-output` and `expect-verification` both passed. The verify now waits for the post-rip thread to end (its last step is the transcode) under a one-hour deadline, polling for a newer rip; a deadline that passes is recorded as `timed out waiting for the transcode to finish` with `verification.derived.timed_out_waiting_for_transcode` (schema 40). Both verbs FAIL a derived verification that did not run (`artifact_grading.derived_verification_refusal`). Not changed: the CTDB and FLAC verifiers keep their own 60 s settle | Confirm on the next Full run's K sections | ours |
| R69 | **[x] Fixed 2026-10-26 (run B of the four 0.7.112 Full runs):** the acceptance session packed its bundle before the last rip's post-rip checks finished. The rip stopped at 23:46:21, the session packed from 23:46:22 (written 23:46:48, app log line 14560), and the CTDB and FLAC results landed at 23:47:34 and 23:47:29, so the bundled report carried `verification_result_missing`. The session now waits for `_album_folder_settled` (the predicate the per-rip bundle already waits on), bounded by `test_session.post_rip_wait_s` (600 s), before restoring settings and packing; the bundle's facts say `post-rip checks at packing`: finished, waited N s, or STILL RUNNING with the steps named | Confirm on the next Full run whose last rip is cut off | ours |
| R70 | **[x] Fixed 2026-10-26 (run C of the four 0.7.112 Full runs, section N):** the completion audit counted errors in a read the album had replaced. The album pass counted 2 ripping errors, both paranoia skips in track 16 (its `-j` record, LSN 250715 and 251158); the verified-read chase kept attempt 5, AccurateRip v1 confidence 11 and v2 24 (16/16 AR); the audit still warned "the ripper reports the rip completed with 2 ripping errors". The warning is now scoped to the reads the album keeps (`rip_health.errors_in_replaced_reads`): errors are placed per track by `disc.error_positions`, and a first read counts as replaced only when `retried_tracks` keeps another read on AccurateRip's word and the track's row says AccurateRip verified it. Not determined (the warning stands) unless the per-track counts are complete and sum to the tally. Not changed: `health_status` still reads the album pass's tally | none | ours |
| R71 | **[x] Fixed 2026-10-26 (runs A and D of the four 0.7.112 Full runs):** the cue's ISRC check ignored `--prefer-disc-isrc`. With the flag sent the ripper writes the disc's own ISRC, and both cues carried the disc's codes (A: all 14 equal to EAC's cue, `output_reference/EAC_flac/eac_baseline_police_classics.cue`; D track 10: disc `USZO10001709` where MusicBrainz has `USZ010001709`, an MB typo), yet `cue_integrity` warned "ISRC(s) differ from what we sent". When the first-pass argv carries the flag and a track's `Disc ISRC:` row gives a code (`tracks[].disc_isrc_state: code`), that code is now what the cue must carry (`ExpectedCue.disc_isrcs`); a difference from MusicBrainz is a note naming both (`cue_isrc_disc_differs_from_musicbrainz`), and a cue that lost the disc's code still warns | Correct D's track 10 ISRC on MusicBrainz (the owner's call) | ours |
| R72 | **[x] Fixed 2026-10-26 (run C of the four 0.7.112 Full runs):** the verified-read chase's record wrote each attempt's argv with the absolute home folder (`/home/<user>/.local/bin/cyanrip`, five times per record), and only the export's redaction around the signed logs (commit 3abb38eb) kept it out of the bundle. `verified_read_chase.chase_log_section` now writes that line with `~` at creation, through `export_redaction.redact_text`, the function the export uses, so the two spell it alike; the embedded cyanrip logs stay byte for byte | none | ours |
| R73 | **Triaged 2026-11-16 (STALE-BUT-OPEN): the `.25`/`.26` comparison is history; left: `artifact_grading._track_ar_state` still calls `verdict.accuraterip_state` itself (`uiscript/artifact_grading.py:255-263`) rather than delegating to `verdict.track_accuraterip_state`.** **[~] Paired rips of track 3, scripted (2026-10-26; the owner's word *"add paired .25/.26 rips of track 3 to the Full run"*, after the fork's round 36 lap 8 S8).** Section P6 of the Full run rips track 3 alone eight times in ABBA order (approved, review, review, approved, twice), with P5's fixed settings and five `install-ripper` switches, records each rip's per-track AccurateRip state, CRC32, speed and build (`record-accuracy`), and tallies per build "right in N of M rips" with every distinct CRC32 read (`compare-accuracy`); all `info`, and a comparison that cannot be made is refused as not determined. "Verified" is `verdict.track_accuraterip_state`, new beside `accuraterip_state`; `uiscript/artifact_grading._track_ar_state` ranks the same states and a property test holds the two equal. Held by `tests/test_uiscript_accuracy_verbs.py` | The first Full run with `.26` still under review: P6's tally, and its real duration recorded in its header (estimated about 30 minutes from P5's measured rips). Then make `artifact_grading._track_ar_state` delegate to `verdict.track_accuraterip_state` (it was being edited on another branch when P6 landed) | ours; the run is the maintainer's, on hardware |
| R76 | **[x] Done 2026-10-26 (the fork's round 36 lap 8 S26):** the reader takes `Track N read with no error reported.`, their proposed rename of `read successfully!`, beside the old wording, which stays for good. One predicate, `cyanrip_log.read_reported_no_error`, replaced the five `endswith("successfully!")` sites (the block loop and `finished_track`, through which the rip worker, the progress row and the verified-read chase read); held by `tests/test_read_outcome_wording.py`, including a sweep that no module keys on the wording's ending | Name the release that reads it (0.7.113) in our lap 9, so the rename lands in their build after it | ours |
| R77 | **[x] Done 2026-10-26 (the fork's round 36 lap 8 S21, their S5):** `.27`'s `Pregap search:` line is read by `pregap_search.py` (a bounded named-group pattern into a frozen `PregapSearch`; a variant wording kept, bounded and screened, as `unrecognised`, never dropped) into `TrackResult.pregap_search` and the report's per-track `pregap_search` (schema 40); the rip audit names the counts beside an `unknown` pre-gap. Held by `tests/test_pregap_search.py` on their lap-8 golden reference (`cyanrip@22af58e`), every top-level and track-block line of it accounted for | Answer their S23 (accept the wording) in our lap 9; read the four runs' `unknown`s through it on the Full run on `.27` | ours |
| R78 | **[x] Fixed 2026-10-26 (the fork's round 36 lap 8 S11):** `expect-pregaps-agree` set aside every log whose `Gaps:` block said `pregap of track N unknown (reason)`, so on their reference-disc runs it compared three logs and called them identical while three said track 9 was unknown. `uiscript/pregap_grading.py` now reads an unknown pregap as a reading (`None`), which differs from any frame count, and its detail names each log's reason and, from `.27`, its `Pregap search:` counts. Held by `tests/test_uiscript_pregap_verbs.py` on the fork's `.27` golden reference beside the same log with a value (no filed log of those runs is a fixture here) | Read the four runs' `unknown`s through it when they are next graded | ours |
| R79 | **[x] Done 2026-10-26 (the fork's round 36 lap 10, `cyanrip@52501ed`; the owner's word of 2026-10-26, *"Round 36: .27 with the Recordable: fix and the track 9 pregap record, then a Full run of the reference disc"*): `.27` (`5aeefc4`) is the build under review.** Their lap 10 filed byte for byte (sha256 `920e8bda…`, 16,212 bytes; its INBOUND-HELD holds our lap 9, `df688e56…`, filed at their `056e468`); `PIN_UNDER_REVIEW` `ca0f097` -> `5aeefc4`, `release_seq` 38 read off their manifest at `a3f7043` (`tests/fixtures/fork_release_manifest_a3f7043.json`), `meson.build` line 21 declaring `0.9.4-rc3+platterpus.27`; `.27`'s provider contract (built at `g580c46c`, `src/` and `meson.build` equal to `5aeefc4`'s) filed and the message inventory regenerated (142 P5, 11 P5a, sites only); `.27`'s tag joins the `--consumer`, `--prefer-disc-isrc` and `--prefer-accuraterip-match` sets (P1 lines 58, 60, 61), so every rip to `.27` sends `--prefer-accuraterip-match` (R48's second open item, R7), and `.26` is named in the `--verify-log` set; the three `.27` rows leave `_FORK_ONLY_WITHOUT_A_PUBLISHED_LITERAL`. `FORK_PIN` stays `5f1d036` until round 36 closes | Nothing more here; the run is R80 | ours |
| R80 | **[x] Done 2026-10-28: 0.7.114 named `.27` (`5aeefc4`); the owner's Full run on it passed (553, 0 fail, evidence `4e3830ca`); round 36 closed on our lap 17 and the fork's lap 18, both `GO`, and `FORK_PIN` is `5aeefc4`.** *Was:* 0.7.114, naming `.27` (`5aeefc4`) as the build under review, is cut on the owner's word of 2026-10-28; the Full run on `.27` is the owner's, tonight. **The Full run on `.27` needs a release of ours naming it.** The fork's lap 10 S13 names the run *"on `.27` through your 0.7.113"*, but 0.7.113's `PIN_UNDER_REVIEW` is `ca0f097` (`git show v0.7.113:src/platterpus/deps/fork_source.py`, line 899), so its section A (`expect-ripper-under-review`) refuses `.27` and its P5 and P6 install `.26` as the build under review; `tests/test_standing_status_is_current.py` refuses `5aeefc4 with 0.7.113` for the same reason. Our lap 11 also answers their S11 (the `-Z` time limit, `--reread-time-limit SECONDS`) and S12 (`disc image` as an image's `isrc_disc_read`) | Cut 0.7.114 naming `5aeefc4` once a word of the owner's covers it (the release hold); say so in lap 11 with S11 and S12 answered; then the owner's Full run of the reference disc on `.27`, filed with manifest rows, and our reading in a lap | ours; the run is the owner's, on hardware |
| R81 | **[x] Reader built 2026-10-26 (the fork's round 36 lap 10 S11, `cyanrip@52501ed`):** their PROPOSED `-Z` time limit, `--reread-time-limit SECONDS`, is read before any build prints it (round 20's order). The `Done; (time limit of 600 s reached after 4 reads; …)` line is a third arm of `_SECURE_DONE_FAIL`, so it reads as NOT converged and never falls through unrecognised, with the repeat limit's count and kept-read clauses read on it as they are; which limit stopped the track (repeat or time, with the seconds) is `TrackResult.secure_rerip_limit_stop`, from that line and the block's `Secure re-read: … (time limit of 600 s reached)` (`reread_limit.py`); the `Re-read limit:` header into `RippingInfo`. Report schema 41 (`tracks[].secure_rerip_limit_stop`, `rip.reread_time_limit_*`); the EAC-layout log says `stopped at our time limit` and a `Read stability` line of its own, never "did NOT agree". Held by `tests/test_reread_time_limit.py` on the fork's `.27` reference with S11's lines put in, and two never-raises properties | Accept S11 in our next lap, naming the release that reads it and the EAC-layout wording (they diff that log); we do not send the option, so it stays a reader until we decide to | ours |
| R82 | **[x] Reader built 2026-10-26 (the fork's round 36 lap 10 S12, `cyanrip@52501ed`):** `disc image` is a known fourth word for the `/11` record's `isrc_disc_read` (the code came from the image's own file through libcdio; no command reached a drive), read before any build writes it. Each word has its meaning in `record_track_v11.ISRC_DISC_READ_MEANINGS`, carried into the report as `disc.isrc_provenance.tracks[].disc_read_meaning` (schema 41); an unknown word stays `unrecognised`, with no meaning. Held by `tests/test_record_track_v11.py` (the word, its meaning, near misses) and the never-raises property | Accept S12 in our next lap, naming the release that reads it, so `/11` can be built with both keys | ours |
| R83 | **[x] Fixed 2026-10-26 (the claude-code-skills review of 2026-10-26, item 2.1):** the ripper build script checked out a 7-character pin, warned on a dirty tree and built it, and its pre-install guard matched the tag as a substring, so `(<tag>-dirty)` passed. Now each named pin carries its full commit (`FORK_PIN_FULL`, `PIN_UNDER_REVIEW_FULL`, `FORK_TEST_PIN_FULL`, resolved in the fork's clone; the short pins stay the build tag every consumer reads), passed as `$7`; the script checks it out, exits non-zero unless HEAD equals it (a prefix check, said as such, for an unrecorded commit), exits non-zero on `git status --porcelain` output, and requires the banner's parenthetical to be exactly the tag. Held by `tests/test_fork_build_head_and_dirt.py`, which runs the script with real git: a wrong HEAD, a dirty tree, a ref-shadowed short pin and a `-dirty` banner each exit non-zero, beside a clean positive control | Add the full commit beside each pin move (the test refuses a named pin without one) | ours |
| R84 | **[x] Fixed 2026-10-26 (the claude-code-skills review of 2026-10-26, item 2.2):** the rip verdict already read a `-dirty` tag as `unapproved` (`handshake_approval._tag_is_approved` compares the whole tag), but `same_commit`'s prefix match made `<pin>-dirty` the approved pin in the update offer ("newest published", nothing offered), the build under review in `is_the_build_under_review` (kept by the offer, the wizard and the status), and installed in `HostSetup.fork_installed` (a substring test). One predicate, `fork_source.is_dirty_build`; ordering keeps the tolerance (`release_seq_for_commit`, the flag sets), while keeping, offering and installing refuse it: `_dirty_build_offer` offers the clean build, and the build script refuses a `-dirty` banner (R83). Held by `tests/test_dirty_build_is_unapproved.py` (verdict `== UNAPPROVED` with its reason, the tri-state for a tagless banner, offers, status, the manifest boundary) and two `tests/test_deps_host_setup.py` cases | None | ours |
| R85 | **[x] Fixed 2026-10-26 (the claude-code-skills review of 2026-10-26, item 2.3):** `update_install.download_and_install` installed any version it was handed; only the OFFER was kept from being a downgrade (`update_check.is_newer`), and the attestation does not name a version. Now `update_version_guard` refuses a version below `__version__` before any request, and after the attestation verifies reads the version the file was BUILT as from `src/platterpus/__init__.py` at the attested `resolvedDependencies[0]` commit (by full SHA, 64 KiB cap), refusing one below the running version or different from the asked one; fail closed. Held by `tests/test_update_install.py` (a correctly attested 0.6.60 build offered as newer is refused; the same build declaring the asked version installs) and `tests/test_update_version_guard.py` (with a never-raises property for the parser) | Release-time: a history rewrite that drops a release's commit would make that release uninstallable by the updater (the version file 404s, fail closed); say so if history is ever rewritten again | ours |
| R86 | **Triaged 2026-11-16 (OPEN-OURS): the escape ask has not been sent: no outbound lap of rounds 37 to 40 carries it, and `tests/test_echoed_field_forgery.py:489` still pins the residual.** **[~] Ours done 2026-11-03 (`2ee03e6a`); the residual is the fork's. The disc-header rows are closed in our parser** (`parsers/cyanrip_echo_guard.py`): the eight rows cyanrip prints above the disc `CD-TEXT:` row (`Invoked as:`, `Drive used:`, `Offset:`, `Overread mode:`, `Speed:`, `C2 errors:`, `Accurate stream:`, `Recordable:`) are not read once that row or a track block is reached, so cyanrip's value stays; the five printed between that block and `Album:` (`Paranoia level:`, `Outputs:`, `Tracks to rip:`, `DiscID:`, `CDDB ID:`) are read once, and a second copy makes the row not determined, never the forger's value; forged copies are counted and logged. Both rest on a print order every committed log agrees on (130 header logs, each guarded row in at least 3), read by `tests/test_echoed_field_forgery.py::test_the_disc_header_order_the_guards_rest_on_holds_in_every_committed_log`; the three routes (the `Album:` line, the disc CD-TEXT block, a track echo) and a non-triviality floor per row are tested there, revert-probed. **Still open, the fork's to close, and pinned by `test_RESIDUAL_a_forged_block_opener_still_changes_the_parse`:** a forged block opener (`Track N read successfully!`) or `Done;` line; a `once` row on a build that prints none of its own; and a forgery can make a `once` row not determined (a refusal, not a forgery). **Proposed item for the fork (theirs, NEXT-ROUND):** their `.28` carries *"every value the log writes escaped"* (`cyanrip@46cec2a:src/cyanrip_log.c`, their round 37 lap 1 S3, accepted in our round 36 lap 13 S3). Ask them to state, with file and line, that the escape covers a line break (and every character `str.splitlines` breaks at, `\x85` and U+2028 included) in each echo: the per-track `Metadata:` and `CD-TEXT:` blocks, the disc `CD-TEXT:` block, the `Album:` line, the `.cue` and the `Invoked as:` line; and to publish a `.28` reference log ripped from an image whose CD-TEXT title holds a line break, so our test can assert the escaped form reads as one row. Then the residual test stays for logs from builds before `.28` (they are already filed) and gains its `.28` counterpart. *Was:* **An echoed value can forge a line in cyanrip's log (peer review 2.4, the claude-code-skills session, 2026-10-26).** cyanrip prints metadata and CD-TEXT values with a bare `"%s\n"` (`cyanrip@eca33dc:src/cyanrip_log.c:58-62`, `:770-776`, `:785-788`), so a value holding a line break puts text at column 0 of a line of its own. **Our values cannot:** the argv chokepoint refuses a control character in the four path-bearing fields and replaces it in the seven tag-only ones (D14), held end to end (argv, echo, parse, verdict) by `tests/test_echoed_field_forgery.py`. **The disc's own CD-TEXT can**, whatever we send (`cyanrip@eca33dc:src/cdtext.c:110-131` fills empty tags from it and the log echoes it verbatim). Closed in the parser for every per-track verdict row (`EAC CRC32`, `Secure re-read`, `Accurip:` and its `v1`/`v2`/`450` rows): each prints before the block's `Metadata:` header in every build, so one after it is counted and not read (`_TRACK_ECHO_HEADER`). **Still open, and pinned by `test_RESIDUAL_a_forged_block_opener_still_changes_the_parse`:** a forged block opener (`Track N read successfully!`), a `Done;` line, and a disc-level header row (`Offset:`, `Drive used:`, `Paranoia level:`, measured) through the `Album:` line or the disc `CD-TEXT:` block. Our parser cannot tell those from cyanrip's own | Send the shape to the fork as a NEXT-ROUND item in our next lap, with these citations: escape (or refuse) a control character in every value they echo into the log, the `.cue` and the `Invoked as:` line, as we do at our argv chokepoint; then retire the residual test against a build that does | ours to send; theirs to fix |
| R87 | **[x] Done 2026-11-03: the last two surfaces (`647b61fa`; `ad4d6196` kept `ui/help_dialogs.py` within 300 lines).** (1) The rip-complete notification's title and body pass through `notify.notification_text`, which maps `<`, `>` and `&` to look-alikes (‹ › ＆): the same text on a server that reads `body-markup` and one that does not, so no capability check is needed (Qt does not expose one); held where it is sent by `tests/test_ui_main_window.py::test_completion_notification_carries_no_markup_to_the_server`, and by `tests/test_notify.py` (four markup shapes with a floor, and a `hypothesis` property). (2) About escapes the build stamp, the Python, Qt, PySide6 and platform strings and a tool's parsed version with `_markdown_literal`; `tests/test_component_inventory.py::test_about_shows_every_outside_value_as_written` renders six hostile values and finds each as written, with no link target or image made from them. All three fixes revert-probed `detected`. *Was:* **Outside text on screen as plain text: two surfaces fixed, two left (peer review 2.6, 2026-10-26).** Fixed: the seven tooltips built from a value (`ui/rip_progress.py` results table x4, `ui/main_window_deps.py` status label, `ui/rip_controls.py` Start, `ui/settings_dialog.py` logging) go through `ui.plain_text.plain_tooltip`, and the update dialog's `QProgressDialog` (`ui/main_window_update.py`, showing the server's version and the worker's status) is built by `plain_progress_dialog` with a PlainText label; swept by `tests/test_tooltips_and_progress_labels_are_plaintext.py`, with floors. **Left:** (1) the rip-complete desktop notification (`ui/main_window_rip.py:1526`, `QSystemTrayIcon.showMessage`) carries the failure hint, which can quote the ripper; a notification server that advertises `body-markup` reads it as markup, and escaping it would show `&lt;` on one that does not, so the fix needs the server's capability, which Qt does not expose; (2) About's Markdown (`ui/help_dialogs.py:240-260`) puts `inventory['build']` and a dependency's parsed `version` in unescaped, where the version text and location already go in code spans | (1) decide whether to send the body through `notify-send`-free D-Bus with a capability check, or strip `<` and `&` from it; (2) put both values through `_markdown_literal` | ours |
| R88 | **Triaged 2026-11-16 (STALE-BUT-OPEN): the gate is met: `FORK_PIN` is `.32` (`deps/fork_source.py:327`), which descends from `.28`'s shortening (`cyanrip@edb73dd:src/cyanrip_main.c:2773`, `Names shortened:`), so retiring the before-Start refusal is now ours (keeping the case a title cannot shorten); `adapters/cyanrip_name_lengths.py` still refuses on every build.** **[~] Ours done, checked 2026-11-03; what is left waits on a round, not on code.** The ask went (our round 36 lap 13 S4); the fork proposed `Names shortened:` (their round 37 lap 1 S7), we accepted it and our reader is built (our round 37 lap 2 S5, `d06aed37`, `parsers/cyanrip_disc_blocks.py`, shipped in 0.7.116); the fork built the shortening in `.28` (their round 37 lap 3 S6, `cyanrip@ed50558`), which 0.7.117 names as the build under review. **Left, and gated:** retire the before-Start refusal once a build that shortens is the DEFAULT (`FORK_PIN` moves only when a round closes, so this follows the round that approves `.28` or later, and is not ours to start). When it is retired, keep refusing the case their S6 says still fails: a component the track number, extension and the scheme's own text alone keep over 255 bytes, which `.28` leaves whole and cannot open. Nothing is proposed to the fork; no fork change is outstanding. *Was:* **Filenames built from titles (peer review 2.7, 2026-10-26).** **Fixed:** the album year could leave the library: `%y` is cyanrip's `{date}`, rendered from the Year box verbatim, and the year was checked by neither the argv chokepoint nor the track table, so a year of `..` with a template `%y/%A/…` wrote one folder above the output directory. Now refused at both (`settings_validation.path_reference_issue`; `tests/test_title_filenames.py`). **Held, with tests:** `/`, `../`, `\`, absolute paths and look-alike characters land as one segment (cyanrip's table, `cyanrip@eca33dc:src/naming.c:132-218`, mirrored by our preview); `.`/`..`/control characters are refused in the four path-bearing fields; the unknown-album path is ours and capped at 255 bytes. **Left, by decision not oversight:** a leading dot is a hidden folder inside the library; Windows-reserved names are legal on Linux and only a template's literal text is warned about; **Interim built (the owner's choice, 2026-10-26): a name over 255 UTF-8 bytes is refused before Start.** An identified-disc title of 90 CJK characters passed every check and failed at file creation in cyanrip, which does not shorten it, after the track had been read. `adapters/cyanrip_name_lengths.py` now renders each album-folder level, the `<album>.log`/`.cue` and every ticked track's file (`.flac` and any derived extension) from the `-D`/`-F` schemes and tags the argv sends, through `naming.render_scheme`, counts bytes as cyanrip writes them (`naming.name_bytes_on_disk`), and refuses in the track table (*"Track 7’s file name would be 280 bytes; the limit is 255 — shorten its title."*, the rest counted and logged) and at the argv chokepoint. The pin flipped: `test_an_overlong_identified_title_IS_refused_before_start`, with the 255/256 boundary, 3-byte characters, the folder and log, the unknown disc's capped folder, and `hypothesis` never-raises and agrees-with-the-renderer properties (`tests/test_title_filenames.py`). It shortens the TAG with the name | **The owner chose this on 2026-10-26:** *"Long term, option 3: ask the fork to shorten an over-long file or folder name to 255 bytes at a character boundary, keeping the track number and extension, and to print the shortened name in its log. That fits the escaping work they're already doing for .28."* Ask the fork in our next lap (held until the owner releases it); our reader takes the shortened-name log line before any build prints it; retire the refusal once a build that shortens is the default | ours (the interim); the fork (the shortening) |
| R89 | **[x] Done 2026-11-03 (`ea6efccc`, `01e507ae`): the MusicBrainz body is accepted unbounded, as a recorded decision.** musicbrainzngs reads it with `f.read()` and offers no hook short of monkey-patching (forbidden), so `docs/dependency-contracts.md` → *musicbrainzngs* states why it is accepted (only MusicBrainz, over verified HTTPS, can answer; expat refuses entity expansion; the call is on the worker thread) and what is NOT bounded (size in memory; total time, since the 30 s timeout is per read and the library retries 8 times). The premise our code can enforce is now enforced: the adapter calls `set_hostname(MB_HOST, use_https=True)` itself instead of inheriting the library default; held by `tests/test_server_answers_never_raise.py::test_every_lookup_goes_to_musicbrainz_over_https_whatever_the_library_held` (reads the URL the library opens and the timeout in force, starting from a wrong host; revert-probed `detected` for the host call and for the timeout) and `test_a_musicbrainz_entity_expansion_bomb_is_the_documented_error`. If size or total time ever matters, the exit is a second `MusicBrainzClient` with a capped read, named in the doc. *Was:* **Server answers are external input (peer review 2.8, 2026-10-26).** Now held by `tests/test_server_answers_never_raise.py` (hypothesis over any JSON shape, and pinned cases): **MusicBrainz** raised `AttributeError`/`TypeError` out of the adapter on a wrongly shaped answer and passed a non-string title on as one; now every value is coerced and bounded (`MAX_TEXT_CHARS`, the cut marked and logged) and a wrong shape is the documented `MusicBrainzQueryError`. **Cover Art Archive:** the manifest `save_additional_covers` reads raised out of a never-raises function (non-list `images`, deep nesting), fetched any URL it named (`file://`, any host), and had no bound on images; now only the archive's http(s) hosts are fetched, at most `MAX_EXTRA_IMAGES`. **Update check:** a tag with surrounding whitespace survived into the version, and the page URL opened in the browser came from the answer unchecked; now stripped, and only a page under our releases URL is taken. **CTDB** held already (size cap, host-checked parity URL, bad XML is `CtdbLookupError`); now a property and the entity-expansion bomb pin it. **AccurateRip** reaches us only through cyanrip's log, whose parser has its properties. **Left:** the MusicBrainz body itself is read by `musicbrainzngs`, with no size cap we can set (the other four fetchers cap theirs) | Decide whether to wrap `musicbrainzngs`' opener with a bounded read, or accept its timeout as the bound and say so in `docs/dependency-contracts.md` | ours |
| R90 | **[x] Fixed 2026-11-02: a suspect is confirmed only when every one of up to three larger-scale measurements grows past the line, and the lowest ratio is the verdict, as each timing already takes the lowest of three rounds; `test_a_suspect_is_confirmed_only_when_every_attempt_grows` holds it with fixed readings. It failed PR #424's py3.13 leg that day over `scripts/handshake.py:2824` (8.6x, then 8.3x, at 0.34 ms).** The regex timing test flakes on a shared runner (2026-10-27). *2026-10-28: it failed again, on 0.7.114's pull request (#405, py3.11), over `_PREEMPHASIS` (`cyanrip_log.py:938`), at about 0.05 ms, which the owner judged noise (locally that regex timed linear up to 128,000 characters). The owner had that one regex replaced with string operations (`cyanrip_preemphasis.preemphasis_text`) for the release. **The test itself still needs a larger input or a minimum-time floor, so that a ratio built from tens of microseconds stops failing on noise** (the owner's word of 2026-10-28; not for 0.7.114). The pattern it names next will be as linear as this one was.* `tests/test_regex_bounded_time.py::test_every_compiled_regex_in_src_is_roughly_linear` failed `test (py3.11)` on PR #396 over `cue_validate.py:256` (`_RE_FILE`, 8.4x then 8.5x for a 4x run of tabs, at 0.05 ms), and passed on the re-run; earlier the same day it failed once locally over `scripts/laplang/refs.py:38` and passed on the rerun. Measured here, `_RE_FILE` is linear (0.019, 0.077, 0.295 ms at 2,000, 8,000 and 32,000 tabs). So the detector, not the pattern, is what fails. Find out why its noise floor and second confirmation let a 0.05 ms reading through on a busy runner, and fix the measurement, not the patterns; a failure must stay reproducible on re-run before it counts. |
| R91 | **Triaged 2026-11-16 (OPEN-OURS): unchanged: python-appimage's base image, appimagetool's runtime and `scripts/bommap` reading the locks are still open.** **[~] Hash every install that is still a range (the follow-up review of 2026-10-27, after items 1, 4 and 6; item 5).** The jobs that publish, attest and gate install from `build/locks/` with `--require-hashes` (`708aba97`, `fe6e7e56`). **Covered since item 5:** the required `sbom` job (`build/locks/sbom.lock`: the runtime dependencies, pyproject's new `sbom` extra and the backend, then the project offline; its `pip install --upgrade pip` is gone), the `shellcheck` job and zizmor and ShellCheck in `workflow-lint` (`build/locks/ci-lint.lock`), and `mutation.yml` (`build/locks/ci.lock`). `commit-subjects` installs nothing: `scripts/check_commit_subjects.py` is standard library only. **Still ranges:** actionlint-py in `workflow-lint` (`>=1.7.12,<1.8`): it publishes only an sdist, whose build downloads the actionlint binary from GitHub and checks it against checksums the sdist carries, so a wheel-only lock cannot hold it; the way through is either a lock that admits that one sdist and installs it with `--no-build-isolation` beside its build dependencies (setuptools, wheel, requests, semver), or the actionlint release binary fetched with a pinned sha256, as the `gitleaks` job fetches its CLI. cyclonedx-bom's own range is `>=7,<8`, a major range: pinning it to the minor (amendment A5) would also add it to `.github/dependabot.yml`'s ignore list (it is a CI tool) and to the weekly group's `exclude-patterns`; `tests/test_dependabot_holds_the_pins.py` derives both from `pyproject.toml`, so it would say so. (The `pinned-minor` group this sentence once named was removed on 2026-10-27.) python-appimage's own downloads of the base image and appimagetool are not pip installs and are not locked. And `scripts/bommap` does not read the locks, so `bom.cdx.json` lists ranges where the jobs install exact versions. **2026-11-03, two of these closed.** (1) actionlint: `workflow-lint` now fetches `actionlint_1.7.12_linux_amd64.tar.gz` from rhysd/actionlint's release, checks sha256 `8aca8db9…` (the release's own checksums file and actionlint-py 1.7.12.25's `_custom_build/checksums.cfg` agree; the extracted binary is byte-identical to the one actionlint-py installed), checks `-version`, and runs that file; the job's only pip install is now the hashed lock, so it joins `HASHED_JOBS`, and `bom.cdx.json` maps the binary as `ci:actionlint`. pyproject's `actionlint-py` line stays for local installs, and `tests/test_dependency_locks.py::test_workflow_lint_fetches_actionlint_pinned_and_in_pyprojects_range` holds CI's version inside its range. (2) cyclonedx-bom is `>=7.5,<7.6`, the minor sbom.lock already resolves (no lock moved), in dependabot.yml's ignore list and weekly `exclude-patterns`, held by `tests/test_gating_tools_are_pinned.py::test_the_sbom_generator_is_pinned_to_a_minor`. **Still open:** python-appimage's base-image download (a rolling release asset per CPython minor, so a sha256 pin would break whenever upstream rebuilds it; the way through is fetching a named patch build by URL and sha256 and passing `PLATTERPUS_BASE_IMAGE`, proved by an `appimage.yml` build), appimagetool's own type-2 runtime download, and `scripts/bommap` reading the locks. |
| R92 | **Triaged 2026-11-16 (OWNER): unchanged: rule #11 in `CLAUDE.md` still says the workflow derives its specs from `pyproject.toml`.** **[ ] Critical rule #11's wording predates the locks (the owner's call: the rules section is locked).** It says *"the workflow derives its specs from `pyproject.toml`"*. Since `fe6e7e56` the workflows install a hashed lock that `build/lock-requirements.sh` derives from `pyproject.toml`, and `tests/test_dependency_locks.py` holds the lock inside pyproject's ranges, so the rule still binds, one step removed. Proposed wording, for the owner: *"the workflow installs a hashed lock derived from `pyproject.toml`, and `tests/test_dependency_locks.py` refuses a lock outside its ranges"*. |
| R93 | **Triaged 2026-11-16 (OWNER): still the repository setting: the scheduled runs of 2026-11-02 (41478401331) and 2026-11-09 (42655573534) both ended in failure (`gh run list --workflow=dependencies.yml`); the second's cause was not read here.** **[~] Relock pull requests get no CI (the third follow-up review of 2026-10-27).** A pull request opened with `GITHUB_TOKEN` starts no workflow, so `dependencies.yml`'s `relock` job's pull requests arrive with no checks. Give that job `actions: write` and dispatch `ci.yml` on its branch after the push, then delete each relock branch once it merges (GitHub's auto-delete covers branches merged through a pull request; check that it reaches these). First confirm the repository lets Actions open pull requests at all (Settings, Actions, General); the job has not yet run. **Ours, done 2026-11-03:** the job holds `actions: write` and runs `gh workflow run ci.yml --ref <branch>` right after the push and before the pull request (a `workflow_dispatch` made with `GITHUB_TOKEN` is the exception GitHub's recursion guard makes, so the checks land on the branch's commit and its pull request shows them); and each run deletes every other `relock/` branch, because the KDD-43 path closes a relock pull request rather than merging it, and auto-delete only reaches merged ones. A pull request it cannot open still fails the job red, after the dispatch and the cleanup. Held by `tests/test_dependency_locks.py::test_a_weekly_job_regenerates_the_locks_and_proposes_them`. Not yet run on GitHub. **Needs the owner:** the job did run, on 2026-11-02 (run 41478401331), and `gh pr create` failed with *"GitHub Actions is not permitted to create or approve pull requests (createPullRequest)"*. The session's proxy refuses the API path that reads the setting. Steps: (1) github.com/rmccann-hub/Platterpus, Settings, Actions, General; (2) under *Workflow permissions*, tick *Allow GitHub Actions to create and approve pull requests* and Save (the default `GITHUB_TOKEN` permission can stay *read*: the job grants its own writes); (3) dispatch *Dependencies* from the Actions tab, or wait for Monday's run, and check that the relock pull request opens and shows CI checks. Without step 2 the job still pushes the branch and runs CI on it, then fails red with the compare link to open the pull request by hand. |
| R94 | **[x] Done 2026-11-03 (`17dc8f53`): `publish-pypi.yml`'s new tag gate, after the ref gate and before the build, publishes only release.yml's annotated tag (tagger `github-actions[bot]`, read with `git for-each-ref`) on the commit being built, or a tag on `main`'s tip, and refuses a tag it cannot read or one that names another commit; held by `tests/test_release_git_steps.py`'s seven tag-gate tests against real repositories, revert-probed. Not stopped, and said in the step: someone with push rights writing that tagger line into a tag of their own.** *Was:* The publish gate accepts a hand-pushed `v*` tag on an older `main` commit (the third follow-up review of 2026-10-27). Since `fdb07e3c` its comment says a publish retry needs an older commit, and that PyPI refuses a version it already has. Left open: a tag on an older commit whose version was never released would publish. Require the tag's commit to be the one `release.yml` tagged (an annotated tag by `github-actions[bot]`, readable with `git cat-file -p`), or `main`'s tip. |
| R95 | **[x] Done 2026-10-29:** `rip_worker` locks the speed unless the log says it can change (`is not True`), and `Speed:          default (setting 8x failed)` from `.28` reads as unchangeable; held by `tests/test_rip_worker.py::test_the_speed_lock_engages_unless_the_log_says_the_speed_can_change`, which fails on the old lock for the three wordings read as not determined. When a fork build reads a refused `-S` at the drive's own speed (`.28`, round 37 lap 1 S8) is our default, the lock can relax for it. **Was:** Lock the read speed when the drive's answer is unknown (round 36 lap 15 S5, owed to the fork). `rip_worker.py:1892` locks only on `speed_changeable is False`; our lap 13 S5 said we would lock on None too, and the fork's lap 14 S5 found we had not. Lock on None as well, until a fork build reads a refused `-S` at the drive's own speed; hold it with a test that fails if the lock goes back to False alone. Why: their build after `.27` prints a wording our reader gives as None, so without this we would send it `-S`. When: before the fork publishes that build. |
| R96 | **Triaged 2026-11-16 (HARDWARE): every part is built and held (`tests/test_hold_for_user.py`, `tests/test_modal_stacking.py`); left: the owner's KWin desktop confirming the stacking. Qt's own file dialog is not covered.** **[~] Dialogs that hide behind other windows, or stay in front of the wrong ones (the owner, 2026-10-28; for the next round, not this one).** Two reports: (1) a dialog or yes/no question can end up behind a window that cannot be closed until the question is answered, which locks the app; (2) the disc-identity screen for the reference disc's album stayed in front of other option windows and of the update window. Sweep every `QDialog`, `QMessageBox` and `exec()` for its parent and modality: each question should be parented to the window it is about, raised above whatever blocks it, and never left behind a modal window it is waiting on; a dialog that is not a question should not stay above unrelated windows. Hold it with a test that opens each modal path over another modal window and checks the newest is on top and answerable. **(3), the owner, 2026-10-29, on 0.7.114:** the album picker (`ReleasePickerDialog`, opened at `main_window.py:1640` when a disc's lookup returns more than one release) popped up while they were in Tools → Setup & Updates…, asking them to choose or cancel there. A question the user did not start should wait until the main window is the one in use: no other dialog open, and the window active. The update offer already defers this way (`main_window_update.py:342`, Qt's `activeModalWidget()`); the album picker does not. Sweep every dialog that opens without a click and **sort each into one of two kinds, the owner's word of 2026-10-29: *"if they need to pop up, sure, but if they can hold, then hold them"***. *Can hold*: nothing is waiting on the answer and nothing is lost by a delay (the album picker for a disc just inserted, the first-run setup offer, the update offers, Picard's prompt, the drive and dependency notices); these wait for the main window, through one shared predicate rather than one check per dialog. *Must show now*: something is stopped on the answer or is lost without it (a rip that failed, a drive removed mid-rip, a question a running rip is blocked on, a confirmation before data is overwritten); these still open at once, raised above whatever is open so they are never hidden behind it. Record each dialog's kind beside it, and test both: a held dialog stays closed while Setup & Updates is open and appears when it closes, and an urgent one opens on top of it. For the next round or release, not this one. **Status, 2026-10-29 (on the owner's word, *"while we are waiting for the new fork release, yes, you have my permission to do those"*):** (3) is done for the album picker. The shared predicate is `ui/hold_for_user.py` (`busy_reason`: a modal dialog is open, or another window of ours is active and visible, the script console excepted; `hold_until_free` asks again every 500 ms and asks the caller whether the dialog is still wanted before each try). The picker moved into `ui/main_window_picker.py` and waits through it, one held picker per disc (`_mb_picker_held_for`); `tests/test_hold_for_user.py` drives the real Setup & Updates window, and each of its five guards was reverted with `scripts/revert_probe.py` and caught. Learned on the way: Qt can name a dialog that has just closed as the active window, so a hidden window counts as not in use. **2026-11-03:** the unknown-album offer (`_handle_no_mb_match`, the picker's sibling for no match) waits the same way, through `_hold_unknown_album_offer` in `ui/main_window_picker.py`, keyed on the disc scan (`_disc_retries.request`) because a disc with no MusicBrainz ID comes there too: one offer per scan, waiting or open (the key clears when the dialog closes, so a duplicate result during the modal does not ask again), and a newer scan drops it; five tests in `tests/test_hold_for_user.py`, four guards reverted with `scripts/revert_probe.py` and caught, the control unaffected. The first-run offers wait the same way (the settings-reset notice, the AppImage menu offer, the host setup offer and the drive setup offer, which run in sequence from `_maybe_offer_first_run_setup`, now through `hold_until_free` as one group, the unattended check asked again where they open); three tests in `tests/test_hold_for_user.py`, two guards revert-probed and caught, the control and the unattended test unaffected. The automatic ripper update offer waits too (`_hold_automatic_ripper_offer` in `ui/main_window_update.py`): only the automatic path holds, so `_interruption_blocker` did not gain the other-window test and a check the user starts from Setup & Updates is still answered at once; `_interruption_blocker` is split into `_no_one_to_ask` (drop: window hidden, acceptance session), `_rip_blocker` and `_modal_floor_blocker` (wait), and `hold_until_free` takes an `also_busy` for a caller's own wait reasons; a newer check or an install clears `_held_ripper_offer`; arming no longer skips the check for an open dialog. Six tests in `tests/test_hold_for_user.py`, seven guards revert-probed and caught. **The launch dependency report waits too (2026-11-03, `c753ad77`)**, the fifth *can hold* dialog, answering the two facts read that day: (a) a launch-only marker, `run_dependency_check_async(launch=True)`, passed by `app.main` and nowhere else (`test_only_the_launch_passes_the_launch_marker` reads the source), cleared when anyone asks for a check while the launch one is running, so About's Check again, the re-check after host setup and Check dependencies are answered at once; only the launch report also waits for `hold_for_user.busy_reason` (another window of ours in use), inside `_defer_if_floor_is_busy`; (b) a report that resolves a MISSING REQUIRED dependency, of any check, no longer has the 30 s bound: it waits as long as it must, logs on its first hold and then every 40 attempts rather than each one, and is dropped only when a newer check has started (`_dep_check_generation`); a report that only summarises keeps the bound. Retries now carry the window as their timer's context. Six tests in `tests/test_hold_for_user.py` and one in `tests/test_ui_main_window.py`; eight reverts probed with `scripts/revert_probe.py`, seven caught and the control unaffected. *Not ours to hold:* Picard opens as its own program after a rip, from a choice made in the post-rip dialog. *Must show now:* unchanged. **(1) and (2), 2026-11-03, what is ours (`ff14c134`):** the lock in (1) was the stacking: an application-modal question blocks every other window of ours, but Qt makes it the transient of its PARENT, which is what the desktop stacks by, so a question parented to the main window could sit under the window it had locked (measured, PySide6 6.11 offscreen: a box shown over an open modal dialog was the main window's transient). `ui/dialogs/stacking.py` now makes every application-modal dialog, on every show, the transient of the window it blocks (the newest modal, else the active window of ours), from `CenteredDialog.showEvent` and the app-wide `DialogCenterFilter`; its parent, which owns and centres it, is unchanged, and window-modal and modeless dialogs are left alone (moving a window-modal one would change what it blocks, and it cannot lock the app). For (2), the picker that stayed in front was a question opening by itself, which the holds above now keep from opening over another window, and the automatic offers wait while it is open; no window of ours sets a stays-on-top or bypass flag, which `tests/test_modal_stacking.py` now holds by a source sweep. Seven tests there; seven reverts probed with `scripts/revert_probe.py`, six caught and the control unaffected. What a real desktop (KWin on the owner's Bazzite) does with the transient is for a hardware run to confirm. **The test that opens each modal path over another modal window, 2026-11-03 (`8eec7b6b`):** `test_every_modal_path_opens_on_top_of_another_window` in `tests/test_modal_stacking.py`, over the conformance matrix's populations (every `CenteredDialog` subclass, every routed message box, every scenario that drives a box through its real code path), each opened over an application-modal dialog and over a modeless window in use, with floors from the measured counts (16, 40, 53; 74 application-modal, 33 window-modal, 2 modeless); `exec()` and `open()` are replaced by the check, and conftest's non-blocking message-box answers are put back to the module's own functions for it. Revert-probed: the filter's stacking, the window-modal exemption and the active-window fallback each caught; CenteredDialog's own stacking is not, because the filter it runs under stacks every dialog too (that path is held by `test_a_centered_dialog_is_stacked_without_the_app_filter`). Not covered: Qt's own file dialog. |
| R97 | **[x] Fixed 2026-10-29:** the probe runs in a folder of its own under the app's data folder (`adapters/cache_probe_folder.py`), returns the tool's log as `analysis_log`, and the `cache-probe` script verb saves it beside its output as `cacheprobeNNNNlog.txt`, so a bundle carries it; held by `tests/test_cache_probe_folder.py`, which runs the real probe path with a stand-in that writes `cdparanoia.log` to its working folder and fails when the probe is started in the launch folder again. **Was:** The drive-cache check leaves `cdparanoia.log` in the user's home folder (the owner, 2026-10-28). `cd-paranoia -A` always writes its detailed timing log to `cdparanoia.log` in its working folder, and `adapters/cache_probe.py` spawns it without setting one, so it lands wherever Platterpus was started, the home folder on the owner's rig (325 KB from the 2026-10-28 Full run; the run's bundle kept only the 18 KB of stdout, `cacheprobe1364.txt`). Run the probe in a folder of its own (a temporary one, or the test session's folder when a script runs it), move the log beside the probe's output so a bundle carries it, and leave nothing in the user's folders; hold it with a test that runs the probe with a stand-in that writes `cdparanoia.log` to its working folder and fails if the file appears outside the probe's own folder. Also: our instructions must never tell the owner to write output to the home folder itself; use `~/platterpus-rig/`. |
| R98 | **[x] Done 2026-11-03: the AppDir is made readable by everyone before packing, and `appimage.yml` run 41570912574 built the AppImage through that step with the pinned 1.9.1 on the session branch. 1.9.1 is appimagetool's newest fixed release (only `continuous` is newer), so no pin move is due; when a new release appears, move the pin and dispatch `appimage.yml` on the branch first.** *Was:* **Make python-appimage's AppDir readable by everyone, so appimagetool's pin can move past 1.9.1 (found 2026-11-02).** appimagetool's continuous build of 2026-11-01 (commit `b082d2e`, *Check AppDir permissions and validate .DirIcon before packaging*) refuses an AppDir whose folders are mode 0700, and python-appimage 1.4.6 makes its AppDir that way: the AppDir itself, `usr`, and the bundled CPython's folders, 177 in all on the #421 merge's run. Every AppImage build from the #420 merge on failed. The build now pins appimagetool to 1.9.1 by sha256 (`build/build_appimage.sh`), which predates the check, so builds pass, and the AppImage's own folders still carry those modes. To move the pin, the AppDir needs `chmod -R a+rX` between python-appimage making it and appimagetool packing it, which python-appimage gives no hook for; the options are a wrapper at the cached `AppRun` path that does it and then runs the real tool, or building the AppDir with python-appimage's own steps and packing it ourselves. Then move `APPIMAGETOOL_TAG` and `APPIMAGETOOL_SHA256` together. **Done (2026-11-03): the wrapper.** `install_appdir_mode_wrapper` in `build/build_appimage.sh` moves the pinned tool's `AppRun` to `AppRun.pinned` in the same folder and writes a wrapper in its place that runs `chmod -R a+rX` on every directory argument, refuses (an `Error` line, which python-appimage turns into a failed build) if any folder is still not `a+rx`, then `exec`s the real tool with the arguments unchanged; the zsync re-pack runs the same file. `tests/test_build_harness.py::test_appdir_is_made_readable_by_everyone_before_appimagetool_packs_it` runs the wrapper's own text against a fake tool that records the modes it is handed (revert-probed: removing the `chmod`, the `chmod` and the check, or the install call each turns it red). **Still open: the pin.** It stays at 1.9.1: the session that wrote the wrapper could not run a downloaded binary, so no real appimagetool has packed through it yet, 1.9.1 included. The next `appimage.yml` run on `main` proves the wrapper does not break 1.9.1; to move the pin, change both values on a branch, dispatch `appimage.yml` for that branch (`gh workflow run appimage.yml --ref <branch>`), and move it only once that build passes and its smoke test runs. |
| R99 | **[x] Done 2026-11-02, on the owner's answer that day ("Drop 3.11"; `PLANNING.md` KDD-46): Python 3.12 is the floor and numpy is 2.5.4.** Drop Python 3.11 for pip and pipx installs, and move numpy to 2.5. numpy 2.5 requires Python 3.12 or later (PyPI `requires_python`, read 2026-11-02), so while `requires-python` is `>=3.11` we stay on numpy 2.4, whose last release is 2.4.6 of 2026-05-18: no fix has reached that line since 2.5.0 on 2026-06-21, and the AppImage bundles the same `~=2.4.6`, so every user carries it. Python 3.11 itself has had security fixes only since 2024 and ends in October 2027. Who 3.11 serves: a pip or pipx install on a system whose Python is 3.11, chiefly Debian 12; the AppImage, the main channel, brings its own Python and is unaffected, and our primary targets (Bazzite and Fedora, Arch) ship 3.13 or newer. Ubuntu 24.04 LTS ships 3.12, so 3.12 stays supported. The work: `requires-python = ">=3.12"` and ruff's `target-version`, the CI matrix without its 3.11 leg, `numpy>=2.5.4,<2.6` in pyproject and `~=2.5.4` in the AppImage recipe, relocked, the CTDB localisation tests re-run against 2.5 (the reason numpy is minor-pinned), and README and SECURITY saying so. |
| R100 | **[x] Done 2026-11-03: 0.7.117 shipped the AppImage on Python 3.14, and the owner's Full run on it was green** (553 pass; its `DIAGNOSTICS.txt` reads `python: 3.14.9`, filed at evidence `1bb98a2c`). *Was:* built 2026-11-02, on the owner's answer that day ("3.14, after a rig run"); what remained was a Full run on a build with it. Bundle Python 3.14 in the AppImage instead of 3.12 (planned for the next release, after its hardware run). The AppImage's interpreter is the one every AppImage user runs, and 3.12 has had security fixes only since April 2025; 3.14 gets bug fixes as well, CI already runs the whole suite and the coverage gate on 3.14, and PySide6 6.11 and numpy support it. The work: `PLATTERPUS_PYTHON_VERSION` in `build/build_appimage.sh`, `build/python-appimage/requirements.lock` resolved for 3.14 (`build/lock-requirements.sh`), the AppImage smoke test, and a Full run on the owner's rig before a release ships it, since what changes is what the user runs. |
| R101 | **Triaged 2026-11-16 (OPEN-OURS): unchanged: `pyproject.toml:57` still pins `PySide6>=6.11.1,<6.12`.** **[ ] Move to PySide6 6.12 and add a Python 3.15 leg (after R99 and R100, not urgent).** PySide6 6.12.0 (2026-10-08) is outside our minor pin `>=6.11.1,<6.12`; 6.11 is still patched (6.11.3, 2026-10-26), so nothing is unpatched yet. Every PySide6 6.11 wheel declares `Requires-Python <3.15`, so a 3.15 leg needs 6.12 first (`ci.yml`'s matrix comment). The pin exists because a patch release once removed two menu shortcuts (Critical rule #11), so 6.12 is its own deliberate change: the suite on both, the UI conformance matrix, `main_window.standard_shortcut`'s checks, the AppImage recipe's `~=` changed with pyproject, and a hardware run. |
| R102 | **Triaged 2026-11-16 (OPEN-OURS, outside answer): still DRAFT (`.claude/skills/steward/SKILL.md`); the claude-code-skills checker's framework has not answered.** **[~] A `steward` skill, DRAFT (the owner, 2026-11-03: *"Add it as a draft. Be clear that you should own it, but the skill checker should give a framework for you. Make sure that YOU are thorough with it."*).** Built: `.claude/skills/steward/SKILL.md`, the loop and the rules, and `scripts/pr_steward.py`, which judges a commit's checks from the ruleset and the API (`GREEN`, `FAILED`, `PENDING`, `BLOCKED`, `CANCELLED`) and prints every failure line of a failed job; `tests/test_pr_steward.py` holds each rule, each revert-probed, and holds the skill's verdict table to the script. Run on live data the day it was written: PR #425 `BLOCKED` on `test (py3.11)`, and #421's merge commit `FAILED` on the AppImage build, the two things it exists to see. **Learned on 0.7.117's day:** it read GREEN while `appimage.yml`, which nothing requires, was still building; fixed at `a7484cfb` (a running check of any kind is PENDING), with a test. And twice a merge was sent with a guessed `expectedHeadSha`; GitHub refused both (409), but the rule is now in the skill: read the SHA from `git rev-parse`, never type it. **What keeps it a draft:** the claude-code-skills checker's framework (where a skill lives, its frontmatter, the draft marker, how a skill's script is checked), asked in the skill's last section; and a session's use of it from start to merge, which it has not yet had. |
| R104 | **Triaged 2026-11-16 (OPEN-OURS, watch): no recurrence is recorded in TASKS or the session log since 2026-11-03; by its own rule it closes if none appears, which a search of CI logs would confirm.** **[~] A native hang constructing a `QLineEdit` on CI's py3.14 leg (2026-11-03, once). A mechanism that fits the dump is fixed; the hang was not reproduced, so this closes if it does not recur.** *Found 2026-11-03:* the `uiscript-bundle` thread's frame, `threading.py:1028`, is the `del self._target, self._args, self._kwargs` that ends `Thread.run()` (Python 3.14.6; line 1082 of the dump matches the same file). The bundle closure in `ScriptRunner._write_run_bundle` captured `self`, and the accused test makes its runner as a temporary (`_run(win, ...)` in `tests/test_uiscript_permutation_verbs.py`), so that `del` dropped the LAST reference to a `QObject` and ran its destructor on the bundle thread, while the GUI thread built the next stand-in window's `QLineEdit`: destroying a `QObject` off its own thread is undefined in Qt. *Fixed:* the closure takes plain values read on the GUI thread (`src/platterpus/uiscript/runner.py`), held by `tests/test_uiscript_rip_verbs.py::test_the_bundle_thread_does_not_keep_the_runner_alive` (revert probe: detected). *Tried to reproduce:* a stress script of the same shape (a `QObject` with a child `QTimer`, its last reference dropped on a thread while the GUI thread builds `QLineEdit`s), 3,000 iterations on Python 3.14 with PySide6 6.11: no hang. *Was:* PR #425's run 41557841640, job 125660971230, at `e75a3d13`: `test_uiscript_permutation_verbs.py::test_expect_rip_argv_reads_the_report_on_disk` hit the 300 s `faulthandler_timeout` with the main thread at `tests/test_uiscript_rip_verbs.py:68` (`QLineEdit()` in the `_TrackTable` stub), below it `File "__init__", line ???` and `<invalid frame>`, so inside PySide6's C++ constructor; the other Python threads were a `uiscript-bundle` daemon thread (`runner.py:4358`, building a tar of the log folder, which touches no Qt) in native code with no Python frame, and execnet's reader. The same test passed on the run before at `da3d1d98` (one commit earlier, a footer the only change). Not reproduced locally: those three uiscript test files, five runs with `-n 4` on Python 3.12, all passed. `docs/testing.md` §5.ar's lesson applies: the accused test may be innocent, armed by an earlier test on the same worker. Next: if it recurs, compare the tests that ran on that worker before it (from the run's `-v` order), and check whether a test leaves a Qt thread or the bundle thread running into the next; a 3.14 venv locally to rerun the whole file order. |
| R105 | **[x] Done 2026-11-03: 0.7.117 is published (`104c82d2`, release run 41563982544) naming `.28` (`3f288fb`) as the build under review; our lap 5 was released that day; the Full run on it ran (R108).** *Was:* 0.7.117 names `.28` (`3f288fb`) as the build under review (the owner's word of 2026-11-03: *"release 0.7.117 naming .28 as the build under review, as your STATUS-RELEASE-NEXT says. That's my word."*).** Done in the code: `PIN_UNDER_REVIEW` `3f288fb` (round 37), `release_seq` 39 from their manifest at `8a9a21d` (filed byte-exact), `.28` in the `--consumer`, `--prefer-disc-isrc` and `--prefer-accuraterip-match` sets, exit class 64, and its provider contract (built at `gef413b1`, same `src/` and `meson.build`) filed with the inventory regenerated from it. **What closes it:** 0.7.117 published, then the owner's Full run on `.28` with 0.7.117 (round 37's close condition, the fork's lap 1 S10), filed on `evidence` and read by each side. `FORK_PIN` stays `5aeefc4` until round 37 closes. **Round 37 closed 2026-11-03** on the fork's lap 7 `GO` (their PR #85, `cyanrip@1b22ed96`) beside our lap 6: `FORK_PIN` rolls to `3f288fb` and the approval record to round 37 with 0.7.117; the first release installing `.28` by default is 0.7.119, on the owner's word. |
| R106 | **[x] The acceptance run's restored settings are logged by NAME only, and a risky one comes back silently (2026-11-03).** The owner's Settings before the 0.7.117 Full run had Overread ticked. The Full script sets `force_overread off` and asserts it at the end (`rig_scripts/fullacceptance.txt:223`, `:1858`), so the run is safe. But `_restore_settings_after_acceptance` (`ui/main_window_provision.py:1698`) then puts Overread back, and logs only `restored your settings (the run had changed force_overread, …)`, with no values. -O hung this BDR-209D for about 23 minutes before `.24` bounded it, and the bound is still unverified on this drive (status block's overread-bounded item). **Plan:** (1) log each restored field with its run value and restored value, and put the same list in the bundle's manifest, so a reader of the run knows the user's own settings; (2) when Overread is among the restored settings, say so in the closing dialog and the log, citing the open item, without changing the user's choice. **Done, 2026-11-03:** (1) the restore logs one line per field, `restored force_overread: the run had False, yours is True` (`user_settings.RestoredSetting`, `restored_settings`), and the bundle's `your settings` fact, which the manifest renders, carries the same list; `evidence_bundle.py` needed no change, and `SETTINGS.json` already held both snapshots. (2) when the restore puts Overread back on, `OVERREAD_RESTORED_NOTE` is logged as a warning, appended to both closing dialogs (the bundle's and the nothing-to-send one), and the manifest gains an `overread after the run` fact (on, off, or put back on); the setting itself is left as the user had it. Eight guards reverted with `scripts/revert_probe.py`, each caught by `tests/test_ui_acceptance_session.py` or `tests/test_user_settings.py`, the no-Overread control unaffected. |
| R108 | **[x] Read 2026-11-03: filed at evidence `1bb98a2c`, `full-green`; (4) holds in 19 of 19 signed `.28` logs; our round 37 lap 6 says `GO`; what the reading found is R112 to R120.** *Was:* what to read in the 0.7.117 Full run's bundle (round 37's close), listed before the bundle arrives so the reading cannot shrink to what is easy.** For each log of the run, not one: (1) the banner names `platterpus-fork-g3f288fb`, and every rip report records its ripper as under review, unapproved; (2) the `[plan]` block shows `--prefer-accuraterip-match`, `--consumer`, `--prefer-disc-isrc` where set, and **no `-O`**; (3) `.28`'s four new wordings parse (`Pregap searches:`, `Names shortened:`, the unknown pregap's reason, `Speed:` when a speed was not applied) and `Drive used:` reads whole; (4) track 9's pregap: every log where it is `unknown` has track 9 in `Pregap searches:` (our lap 4 S10's pre-commit, counted across every log); (5) any refusal exits 64 and is surfaced by name; (6) any fatal shows the ripper's own sentence, including the five `.27` wordings retained and the new `cdio: "` line; (7) the restored-settings line in the app log (R106). File the bundle on `evidence` with its manifest rows, then our lap 6 says `GO` unless (4) or a defect in `.28` fails. |
| R109 | **[x] Done 2026-11-03: two causes found and fixed, each held by a test.** (1) `_record_drive_fact`, run on every drive sighting, rebuilt the drive's profile from scratch and dropped `read_rate`, so the speed a rip learned was gone by the next rescan (the rig's app log: "folded over 1 rip(s)" on every rip) and every estimate fell back to the 1.05 seed measured on older, slower builds; it now builds from the existing profile. (2) The estimate counted P5's and P6's twelve rips when `skip-if-same-build` will mark them N/A; it now asks the verb's own predicate (`timing_verbs.section_will_skip`). *Was:* **The acceptance run's own estimate is more than twice the real time (found 2026-11-03).** Both Full runs of 2026-10-28 and 2026-10-29 opened with *"Run estimate (full): at least 6h 40m, up to 17h 40m … 21 rip(s) about 6h 30m at 1.0x (the speed the project's rig measured for this drive model)"*; their script reports' step times sum to 2h 54m and 1h 37m (evidence `4e3830ca`, `7a5cff47`, `round36full1028ascriptreport.json` and `round37full1029ascriptreport.json`). Two causes to check in `uiscript/run_estimate.py`: the 1.0x drive speed (the rig reads several times faster), and P5 and P6 counted when `skip-if-same-build` will mark them N/A (the 10-29 run). **Plan:** take the drive speed from this drive's own measured rips where the app has them, leave out sections the run will skip, and test both against those two reports. |
| R110 | **Triaged 2026-11-16 (STALE-BUT-OPEN): the relock to `--exclude-newer 2026-11-04` took the in-range moves (PySide6 6.11.3, ruff 0.17.3, mypy 2.4.1; `build/locks/`) and dnspython 2.9.2 (`25c6885a`); left: cyclonedx-bom 7.6, zizmor 1.32, gitleaks 8.24.3 (`.github/workflows/ci.yml:586`), uv 0.13.5 in every lock header, and PySide6 6.12 (R101).** **[ ] Dependency audit of 2026-11-03: no known vulnerability; the moves that are due, none urgent.** `pip-audit` 2.10.1 over all eight locks (`--disable-pip --require-hashes`, as `ci.yml`'s job runs it): *No known vulnerabilities found*; its floor held (`uv==0.8.5` reports four advisories). OSV (`api.osv.dev/v1/query`) reports none for uv 0.13.5, python-appimage 1.4.6, actionlint 1.7.12, gitleaks 8.24.3 (Go module) or any of our six actions at their pinned versions; its floor held (uv 0.8.5 and `pypa/gh-action-pypi-publish` 1.14.1 each report theirs). Newest releases read from PyPI's JSON and `git ls-remote --tags` the same day; the cooldown cut-off is 2026-10-27, and every lock is at `--exclude-newer 2026-10-26`. **Within our ranges, for the next relock** (no lock moved here, none is a security fix): PySide6/shiboken6 6.11.2 to 6.11.3 (2026-10-26), hypothesis 6.170.10 to 6.170.12, jsonpointer 3.5 to 3.6, msgpack 1.2.3 to 1.2.4; and, once each clears its seven days, mypy 2.4.1 (2026-10-28), ruff 0.17.3 (2026-10-27), pytest 9.2.0 (2026-10-27), dnspython 2.9.1, pydantic 2.14.2 / pydantic-core 2.50.2, tzdata 2026.6, platformdirs 4.14.3, filelock 4.2.7, pip 26.3, sigstore-models 0.0.7, and python-dateutil 4.0.0 (a major, transitive through the sbom and CI locks). The weekly relock (`dependencies.yml`) regenerates these, but its pull request cannot open until the owner's step in R93, so a session carries the locks meanwhile. **Outside a minor pin, each a deliberate commit that re-runs its gate (Critical rule #11):** cyclonedx-bom 7.5 to 7.6.0 (2026-10-28, clear on 2026-11-04); zizmor 1.31 to 1.32.0 (2026-11-02, clear on 2026-11-09); PySide6 6.12, which is R101. **Pinned binaries and actions:** gitleaks 8.24.3 against 8.30.1 (the gating `gitleaks` job; release dates not read, since GitHub's API and release feeds are refused through this session's proxy); uv 0.13.5 against 0.13.7 (2026-11-03; 0.13.6 2026-10-27), which every lock header names, so moving it is a regenerate-and-`--check` change; `astral-sh/setup-uv` v10.3.1 against v10.3.3, which Dependabot's weekly action update carries; appimagetool 1.9.1 is the newest fixed release, and moving off it is R98. Current: actionlint 1.7.12, actions/checkout v7.0.1, setup-python v7.1.0, upload-artifact v7.0.2, attest-build-provenance v4.2.2, gh-action-pypi-publish v1.14.3, and every other direct dependency (build, twine, python-appimage, pip-audit, cyclonedx-python-lib, cryptography, sigstore, numpy, tomli-w, musicbrainzngs, pytest-cov, pytest-xdist, setuptools, wheel, shellcheck-py). |
| R107 | **[x] Done 2026-11-03: an exception that reaches `sys.excepthook` fails the test it happened in, and a test's queued MusicBrainz calls run before its window is torn down.** *Found:* after a passing local run, tracebacks from `workers/mb_worker.py:127` (`fetch_release`) ending in `_FakeMb.release_by_mbid`'s `assert self.mbid_result is not None`; reproduced with `tests/test_ui_main_window.py` alone, `-n 0` (three tracebacks in one run). Not a thread outliving its test: four tests made the window settle on a release (one candidate, or a picker answered) with the default fake, so the real queued fetch asserted on `_mb_thread`, and PySide hands an exception in a slot to `sys.excepthook` and carries on (measured, PySide6 6.11.2), which pytest's `threadexception` plugin never sees. Whether the fetch ran before `stop_window_threads` quit the thread was a race, so the tracebacks came and went. *Fixed:* `tests/conftest.py` owns `sys.excepthook` for the session and fails the test an exception reached (after the thread joins, so a joined worker is charged to its own test); `stop_window_threads` waits for a marker queued behind every MusicBrainz call (`drain_mb_queue`); `pyproject.toml` makes `PytestUnhandledThreadExceptionWarning` an error; the four tests give the fake an answer and assert the fetch. The check found two PRODUCT defects on its first full run: the first-run offer, scheduled with a bare `QTimer.singleShot`, ran in a later test on a torn-down window, and its config write raised `OSError` into Qt (a crash dialog on first launch with a read-only config folder). Six bare config writes now go through `_save_config_or_report`, and the offer is a child timer of the window (the context form of `singleShot` leaks the window in PySide6 6.11.2 when the posted call is dropped, measured). Held by `tests/test_harness_fidelity.py` (three tests), `tests/test_ui_setting_writes.py` (two) and the four window tests; ten reverts probed, all detected. **And a worker that outlives its test fails it:** the join backstops now FAIL a test whose `threading.Thread` is still alive 5 s after it, or whose `QThread` is still running 3 s after `quit()` (they only warned); a thread that stops when asked is still a warning. The day's full run at `-n 4` had no warning of either kind, so neither can fire on today's suite; the `threading` half is held by a harness test, the `QThread` half by none (it needs a worker that ignores `quit()`). *Found in passing, at `2522a1bb` before any of this:* `test_a_new_scan_closes_a_release_picker_an_older_scan_left_open` hung 300 s once in `open_unknown_album_dialog` (a modal `exec()` nobody answers) when run with the window test files at `-n 4`; not investigated. |
| R111 | **Triaged 2026-11-16 (STALE-BUT-OPEN): the `HOST_FIELD` shape went to the fork in our round 37 lap 6 S6; left: the regex sweep's `\n` fill and the pattern it flags (`scripts/bommap/runtime_entries.py:30`).** **[~] Test-suite speed, and a quadratic regex found while measuring it (2026-11-03).** *Measured once:* the whole suite at `-n 4` on Python 3.12, 8 min 55 s wall (02:52:39 to 03:01:34 UTC, on a machine shared with other sessions), with `--durations=40`. The largest single item is the UI conformance matrix's module fixture (250 s of setup; its own CI job since 2026-11-02, so not in the test legs). *Found:* `export_identity.HOST_FIELD` (the fork's pattern) was quadratic in a run of blank lines under `re.M` (`^\s*` crossed line breaks from every line start); fixed with `[^\S\n]*`, same captures (a Hypothesis equivalence test against the old pattern), held by the prefixed-offender table in `tests/test_regex_bounded_time.py` (revert probe: detected). **NEXT ROUND for the fork:** their `HOST_FIELD` has the same shape; send it with our citation (seam rule: a fix that could help them is sent). **The regex sweep could not see it:** `test_regex_bounded_time.py` compiles each literal WITHOUT its flags, so `^` under `re.M` is never tried mid-string, and its fills have no `\n`. Adding a `\n` fill flagged one more pattern (`scripts/bommap/runtime_entries.py:30`, lead-in sweep) and tripped a meta-test; not done here, open. *Faster, nothing weakened (before and after, one test, `-n 0`):* `test_the_rewritten_wire_field_pattern_reads_what_the_old_one_read` 15.3 s to 2.1 s and `test_the_rewritten_requirement_pattern_reads_what_the_old_one_read` 2.5 s to 1.0 s (the pattern read from source once per process, not once per Hypothesis example); `test_the_status_block_check_can_fail` 12.7 s to 1.5 s (the handshake record read once per process, not once per mutation). *Left as they are, and why:* the `test_evidence_bundle.py` budget tests (16 s and 7 s) spend their time redacting 64 MiB, the real cap, and shrinking the cap would be lowering a bound; the `test_lap_language.py` checks are bound by subprocess calls to the version-control tool (93 in one test), which only a cache in `scripts/laplang` itself would cut; Hypothesis tests stay at their example counts. |
| R112 | **[x] Done 2026-11-03 (`7021f2cb`, `1eb5cc6f`): `fidelity_summary` asks `verdict.accuraterip_contradictions`, so the status line and the notification name a contradicted track ("13/14 tracks ripped cleanly. ⚠ AccurateRip says track 5 is WRONG"); `tests/test_wrong_track_on_every_surface.py` drives the run's own whole-disc log through the finish handler and holds seven surfaces to the EAC-layout log's verdict.** *Was:* the status line and the desktop notification say "all N tracks ripped cleanly" over a track AccurateRip says is WRONG (the 2026-11-03 Full run, finding 1; archival-adjacent).** App log lines 6764 (F), 12208 (N) and the four P5 rips: "Done — all 14 tracks ripped cleanly, no read errors. AccurateRip: 13/14 verified…", while the EAC-layout log says `Proof: none — WRONG: frame 450 matches…` and `There were errors`, and the report carries `accuraterip_contradiction: "wrong"`. `ui/main_window_helpers.py:527-535` counts clean from `status` and skips only and never asks `verdict.track_accuraterip_contradiction`, the one predicate `verdict.py:179-195` says every surface asks. Fix: ask it, and word a contradicted track as not clean. |
| R113 | **[x] Done 2026-11-03: the subset rip's AccurateRip row (`9c159aa2`), the row cleared when a rip starts (`1eb5cc6f`), "1 track" and "1 ripping error" (`b9cc4bec`), a stopped track shown as stopped (`045ab84e`); the Settings example's `:` is U+2236 `∶` already, not a defect (`tests/test_naming.py:47`). Open: the Tracks table's height (it shows 3.4 rows offscreen at 1000×860; the fix is a design choice, the table's 64 px minimum or the default pane split) and the CTDB `match` label beside `outvoted: true` (the report's own word; changing it changes the report format).** *Was:* small surface defects from the 2026-11-03 run (findings 10, 11).** The disc panel's AccurateRip row shows the last rip's subset as the disc's status ("verified — all 1 tracks matched" on a disc whose track 5 fails); "1 tracks" and "1 ripping errors"; after a cancel, the track being read still shows "⟳ Ripping"; the lower Tracks table shows about 1.5 rows in every after-rip screenshot; Settings' example name shows a raw `:` where the file gets `∶`; CTDB's label says `match` at confidence 2 against 1,523 disagreeing (the message corrects it, the label does not). |
| R114 | **[x] Done 2026-11-03 (`324c0d09`): the merge keeps the album pass's `-Z` facts in their own slot, `TrackResult.first_pass_reread` (`first_pass_reread.py`), before it replaces them with the securing read's; `heavy_reread` flags a first pass that did not converge and names what replaced it, the report carries `tracks[].first_pass_reread` (schema 42), and the EAC-layout Copy CRC note keeps the first pass beside the securing pass's count. Held by `tests/test_first_pass_reread.py` on the run's own two logs (fixtures copied from evidence `1bb98a2c`); revert probe: 5 of 5 reverts detected.** *Was:* a track that hit the re-read limit in the first pass loses that from its record when the securing pass converges (finding 2). Section N's track 3: "did NOT converge after 5 reads (repeat limit hit)", four distinct CRCs, then the securing pass converged; the report keeps the securing pass's `rip_count 3`, `secure_rerip_converged true`, so `heavy_reread` names track 5 only and the EAC log says "confirmed across 3 secure re-reads". `parsers/rip_log.py:913-926` reads the per-track fields after the securing pass overwrote them. The addendum and diagnostics keep the first pass. |
| R115 | **[x] Done 2026-11-03 (`c8b78e15`): each timing record carries its tracks' AccurateRip results (`TimingRecord.accuraterip`, the verdict's own states), `record-timing` prints each beside its time, and `compare-timings` adds `NOTE: timed reads AccurateRip did not verify: A1 track 3 frame 450 only, …` to any ratio over such a read, as information (the step stays INFO; P5 is a measurement). Held by four tests in `tests/test_uiscript_timing_verbs.py` on the run's own A1 and B1 logs (fixtures copied from evidence `1bb98a2c`); revert probe: 3 of 3 reverts detected.** *Was:* P5's timing comparison is measured on wrong reads and does not say so (finding 3). In all four P5 rips (tracks 1-3) track 3 read wrong (four different CRCs, frame 450 only); ripped alone in P6 it read right eight times of eight. `compare-timings` reports only speed ratios. It should state each rip's AccurateRip result beside its time, so a ratio over a misread is labelled. |
| R116 | **[x] Done 2026-11-03 (`73f554f3`, the review's B7): `safe_int.present_int_or_none` logs nothing for an absent optional clause and still warns on a present, unusable value; on the run's `accuracy A3` log, 2 warnings before and 0 after.** *Was:* 1,942 false WARNING lines a run, 96% of all warnings (finding 4).** "unusable integer for Pregap search undecided from: None" and "… to: None", 971 each: `pregap_search.py:167-172` hands an optional clause's absent value to `int_or_none`, which warns. Predates `.28`. A log that is 96% noise hides the warning that matters. |
| R117 | **[x] Done 2026-11-03 (`49eb96f9`), four parts.** (1) The `[plan]` block names `--prefer-accuraterip-match` and `--consumer <tag>` (and `--diagnostics` by its name), held by a sweep that builds the argv for `.28` and requires every long option it sends to appear in the plan (`tests/test_rip_plan.py`). (2) `Pregap searches:` and `Names shortened:` reach the report as `rip.pregap_searches` and `rip.names_shortened` (schema 42); not the EAC-layout log, which has no such lines (`docs/eac-parity.md`, cyanrip extras). (3) A failed probe's `deps.command_failed` reads `cyanrip exited 64: Offset is unset! To continue with an offset of 0, run with -s 0!`, the sentence picked by the parser's `is_ripper_error_line` (`rip_backend.ripper_sentence`). (4) A report's `diagnostics` holds what was recorded from its rip's `timing.started_at` on and counts the session's earlier ones once in `earlier_in_session` (`diagnostics_scope.py`); no upper bound, since post-rip checks record after the rip ends. Held by `tests/test_records_reach_their_reader.py` (the run's secure re-read log, copied from evidence `1bb98a2c`, and the probe output that run's report recorded); revert probe: 7 of 7 reverts detected. *Was:* records that do not reach their reader (findings 6, 7, 9). The `[plan]` block never names `--prefer-accuraterip-match` or `--consumer` (it names `-O` and `--prefer-disc-isrc`); the disc-wide `Pregap searches:` and `Names shortened:` blocks are parsed into `RippingInfo` and read by nothing (report, EAC export, UI); a dependency diagnostic says "cyanrip exited 64" while the ripper's own sentence sits only in its detail (CLAUDE.md: show the dependency's own sentence), and process-session diagnostics repeat in every later report. |
| R118 | **[x] Done 2026-11-03: a shutdown that crashed (finding 15; the log's banner says 0.7.115, build de2420d, not 0.7.114; 2026-10-28 23:20:26).** *Found, by reproduction:* (a) **not a recursion.** `auto_center.py:201` is `event.type() == …` and calls nothing that re-enters. A Python override of a Qt virtual that raises leaves the exception pending while Qt finishes the close, and every Python event filter Qt calls meanwhile fails on its first call into Qt with it, one traceback frame each (the `scroll_guards.py:86` frame in the middle is the same thing). Measured on PySide6 6.11.2: a raising `closeEvent` under the filter gave 17 such frames and a nesting depth of one. (b) **not a circular import and not interpreter shutdown**: `report_writer` imports nothing from `platterpus`, and the close ran inside `app.exec()`. It was the module's first import of that session (no rip had run), attempted after SIGTERM, and the file was not found. A logout sends SIGTERM to the whole session, the AppImage runtime that serves the package's mount included; refusing every new import during a close reproduces the field's sentence word for word. That the runtime died first is the one link no log shows. *Fixed:* `report_writer` is imported when `main_window_rip` loads (stdlib-only, no cycle possible), and `closeEvent` logs a failed flush with its traceback instead of raising it, so Qt's close still runs; the flush keeps its own 5 s bound. Held by `tests/test_close_never_raises.py`: a fresh interpreter closes a window while every new import is refused (no import, no ERROR line, with a floor that the refusal works), and a flush that raises is logged while the app-wide filter sees no exception and is never nested. Four reverts probed: the file restored to HEAD and the import line alone (detected), the guard (detected), and the guard against the import test (unaffected). *Left open:* the flush's 5 s bound is its own, not the close's shared `ShutdownDeadline`; and no sweep proves the rest of the close path imports nothing on a close mid-rip (the test closes an idle window). |
| R120 | **[x] Sent 2026-11-03 in our round 37 lap 6 S11, with the review's A7 (keep `INDEX 00` at the earlier bound of an undecided pregap) (finding 12).** The cue sheet gives track 9 no `INDEX 00` while cyanrip says its pregap is unknown (`F1.cue:65-70`), which reads as a confirmed zero. Send as a next-round item with the citation. |
| R121 | **[x] Done 2026-11-03: the skills session's review of the 2026-11-03 run, sections A and B: ours.** One verdict on every surface for a track AccurateRip or CTDB contradicts (A1 `health_status` "No errors occurred", A2 "offset-variant" / "13 of 14 matched" / the addendum's "CONFIRMED", with R112); a CTDB match outvoted by its own database passing `expect-ctdb whole` (A3); the AccurateRip line not reset at a rip's start and "1 tracks" (B1, with R113); a hidden modal leaked per cyanrip update offer, no `WA_DeleteOnClose` in `_offer_ripper_install` (B2, with R96); the learned speed across rescans and "at least" on a figure runs beat by 2.8x (B3; R109 fixed the first half at `a49873ff`); rig-check and the report's paranoia counts leaving out the securing pass (B4); 1,942 false warnings (B7, with R116); the bundle's `SOURCES.txt` against its `MANIFEST`, its size budget, and 20 per-rip bundles where one file is promised (B8); cancel's device-wide `fuser -k TERM` (B9). Done: A1 for AccurateRip (`1eb5cc6f`; a CTDB-only contradiction waits on the owner, since it would change the EAC-layout log's verdict), A2 (`1eb5cc6f`), B1 (`1eb5cc6f`, `9c159aa2`), B2 (`40eb719f`), B3 (`8b4cf843`: the learned speed survives a reload, held by a test; the estimate says "about"), B4 (`e65ac578`, `paranoia_scope.py`), B7 (`73f554f3`), B8 (`cebdd57c`: one account of the bundle; the per-rip bundles are the design, and the closing text now says so), B9 (`ff7fedbd`: the device-wide signal kept and its reach recorded, and the drive poll held off while a force stop runs, which could have signalled Platterpus itself). A3 (`eb550dd6`: `expect-ctdb whole` fails a match its own report marks outvoted or untrustworthy, and a match without its weight is not determined) | Fix each with a regression test, for 0.7.118 | ours; A5's EAC-log half ("Copy OK … confirmed across 3 secure re-reads" beside the main pass's errors) with R114 **The owner's word of 2026-11-03, "do 1 - 4 as recommended":** (1) a CTDB-only disagreement is a note, `ⓘ CTDB disagrees on track N`, in the Tracks table's status cell and a line under the status line, and AccurateRip stays the one source of WRONG (`22f92fa8`, `ctdb_disagreement.py`); (2) the rip pane's default share 0.30/0.50, so its Tracks table opens with 4 rows and the track list keeps 4 (`9b121ccb`); (3) an output folder that cannot be written is refused before the rip with a message naming it (`b4020717`, `output_writable.py`); (4) the WAV warning names what a WAV keeps (title, artist, album, track number, year, genre) and loses, measured through our own transcode (`643e2b40`). CLAUDE.md's Critical rule 4 still says WAV has "no tags/art": a locked rule, the owner's to edit. |
| R122 | **[x] Done 2026-11-03; its last finding, `FLAGS PRE`, done 2026-11-04 (`d8b18aee`: the cue carries `FLAGS PRE` on exactly the tracks the `Preemphasis:` row flags when every pass sent `-W` without `-E`, on none otherwise, not determined without argv; the planted fault's strict xfail now passes; the WAV wording is fixed, R121): the review's section C: acceptance steps that pass without checking.** `expect-verification` passing a gate that ran and failed (C1); no step that can fail on accuracy: add *every track AccurateRip or CTDB contradicts is shown as wrong on every surface* (C2, after R121's A1 and A2 merge, since it fails on them today); nothing reading `rip.read_offset_check` (C3); K1 to K3 grading the FLAC masters, not the derived files, and K3's WAV warning unasserted (C4); P3 decidable as "CRCs equal, R128 apart" (C5; the fork asked to confirm `measure_frame` in our round 37 lap 6 S12 (d)); P3's result lost to 898 KB of carriage-return progress (C6); O, P, P2 and P3 passing no `-d` (C7); `record-timing` without each track's AccurateRip state (C8); six one-drive gaps unscripted (C9); no free-space check before a rip (C10) | Done: C2 (`1eb5cc6f`, `tests/test_wrong_track_on_every_surface.py`, seven surfaces held to the EAC-layout log's verdict on the run's own log), C5 (`ca48fa94`, `91f4ba24`, `expect-deemphasis-pair`; the fork's lap 7 S4 confirms the measurement point), C6 (`00edc577`), C7 (`bfb49de5`), C8 (`c8b78e15`, with R115), C9 (`74c36cfe`: Settings OK, the overwrite prompt's Cancel and Replace, and a cancel in the securing pass; Force stop, eject and re-insert, and an unwritable folder are not scripted, each with its reason in H2), C10 (`a205cbba`, `disk_space.py`). C1 (`eb550dd6`: a gate that ran and failed fails `expect-verification` and `expect-derived-output`), C3 (`01ac180c`, `2c5fcc8c`: `expect-read-offset` after F and N, every pass's `-s`), C4 (`c5371f51`: `expect-derived-files` opens the MP3, WavPack and WAV files, with the encoder's argv as run; K3's title now promises only what is checked). Open from it: a cue missing `FLAGS PRE` on a pre-emphasised track passes `cue_integrity` (held as a strict expected failure in `tests/test_uiscript_planted_faults.py`; a rule needs to know whether de-emphasis was applied, which neither the report nor the cue states); and Settings says WAV "can't store tags or cover art", but ffmpeg 6.1 writes title, artist, album and track number into the RIFF INFO chunk, losing album artist and cover only | ours |
| R123 | **Triaged 2026-11-16 (HARDWARE): no `track3abba` run is filed (`docs/evidence-manifest.tsv`); round 39's five-rip run has since read track 3 as `59D352DD` in all five rips (evidence `ac0a5133`), so the question is worth less now.** **[~] Script built 2026-11-04 (`13c1df4b`, `--run-script track3abba`: 12 rips, ABBA pair against alone, then `-S 4` and `-P 0`, with `compare-conditions` and `cyanrip-timeout`); the run is the owner's, on the rig.** A controlled test of track 3 (the review's D, with A4 and R42), on the rig, about 25 minutes.** P5's four rips read track 3 wrong (four CRCs, `2363932F`, `28D42AE3`, `3D8FCF0C`, `AD24D3ED`, the same in the 2026-10-21 bundle); P6's track-3-alone rips were right 8 of 8 (`59D352DD`) on both builds. Alternate four rips of tracks 2 and 3 together with four of track 3 alone, same build and settings, ABBA order; then the cache probe and `cd-paranoia -A`. If "after track 2" is wrong and "alone" right again, the cause is the read path between tracks, not the build | Script it as a P6b section or a one-off; ask the fork what to vary next | the owner's rig; ours to script |
| R124 | **Triaged 2026-11-16 (OPEN-OURS, HARDWARE): (1) and (2) are done; (3) to (6) are not started, and (3), (4) and (6) need the rig.** **[~] Finding what we do not know we are missing (the review's E).** (1) plant one fault each in filed-shape reports and replay every grader (done, `2c5fcc8c`, `tests/test_uiscript_planted_faults.py`: every planted fault fails its grader but `FLAGS PRE`, R122); (2) an inventory guard generated from the source: every verb used by a rig script or allowlisted with its reason and unit test (done, `6a1d2953`: of the review's 8, five are used by other rig scripts or now by D2, and `abort`, `tier` and `needs` are the allowlist); (3) one Standard run under coverage.py against CI's coverage; (4) differential rips with the ripper older versions used and the owner's EAC log of the same pressing; (5) mine the filed runs for steps whose pass text never varies; (6) a disc corpus: damaged, HTOA, pre-emphasis, Enhanced CD, CD-Text, CD-R, a disc AccurateRip does not know, an unlisted drive | (1) and (2) for 0.7.118; (3) to (6) after it | ours; (3), (4) and (6) need the owner's rig and discs |
| R125 | **Triaged 2026-11-16 (STALE-BUT-OPEN): CTDB repair (R133) and the per-track time limit (R49, `securing_time_limit.py`) are done, and the parity-plan corrections are in `docs/eac-parity.md` (AcoustID, line 1648); the other features are unplanned.** **[ ] Features after 0.7.118 is out and a Full run on it is green (the review's F, and the owner's word of 2026-11-03).** Correctness first: CTDB repair; C2 pointers as evidence after a per-drive trust test; a per-track re-read limit as a multiple of real time, which is `.28`'s `--reread-time-limit` (the owner: *"Do 1 and 3"*, 3 being "add it after this release", with a default they choose; R49); the tray lock during a rip; HTOA; lead-in and lead-out overread per drive; the sub-channel as a second source for pre-emphasis; data tracks and Enhanced CD, image + cue, CTDB submission, CD-Text, re-verifying a library. And three corrections to the EAC parity plan of record: reading changed after 1.0 beta 3 (run EAC 1.8, the newest, 2024-07-15); EAC's log checksum is public (OPS's logchecker); EAC 1.x submits AcoustID fingerprints by default | Plan them after 0.7.118; correct `docs/eac-parity.md` now | ours |
| R126 | **[x] Done 2026-11-04 but for (e), the owner's: carried from the audits of 2026-10-27 and 28 (the skills session's list, 2026-11-03).** (a) pull requests that relock dependencies run no CI; (b) the publish gate accepts an older `main` commit; (c) stale comments in the AppImage requirements; (d) the bounded-time test judges noise below a floor: give it a minimum size or time first; (e) the `pypi` environment's branch rule, which no session can read: the owner to confirm it; (f) whether to adopt GitHub's workflow lockfiles, generally available since 2026-10-28. Already: #425 merged at `cfbe39c7` (Python 3.12 floor, numpy 2.5, the AppImage on 3.14; shipped in 0.7.117); R96 dialogs in progress | (a) already `1ff90903`, and the trigger it dispatches now held (`6cd7e2e8`); (b) not a defect: an older `main` commit can release only the version it names, once, by the changelog, version, tag and publish gates, now each run as a test (`4d5381f3`); (c) stale comments corrected (`941c5b84`, the locks reproduced byte for byte); (d) growth judged only above 10 µs, with floors on what each sweep judged (`6f00a931`); (f) not adopted: seven days old, a new dependency, and it does not follow the publish job's runtime action; additive path if wanted: keep the SHA pins, onboard `dependencies.yml`, a non-gating `--verify` job. Issue #385's setup-python and uv entries were already current (`53850354`, `a74cbf3d`) | ours; (e) the owner's |
| R127 | **[x] Triaged 2026-11-16: done for its own items: the seam row moved (`docs/seam-commands.md:134`, YES to `.27` and later); `CLAUDE.md`'s size is R32, and the upstream notes stay held on the owner's word of 2026-11-03.** *Was:* **[ ] Housekeeping the same review found.** The shared `docs/seam-commands.md` lists `--prefer-accuraterip-match` in §1b, flags we do not send, though we send it to `.27` and `.28` (`adapters/cyanrip_backend.py:1662`): asked of the fork in our round 37 lap 6 S12 (e), our cell to follow in the lap that carries the move. `CLAUDE.md` is 670 lines against a standard of about 30 with the rest in rule files (R32). The next upstream notes are held until upstream takes #167's items (the owner, 2026-11-03), ready in `docs/cyanrip-fork.md` Part D with three candidates for the fork to confirm on upstream's code. Done 2026-11-03: the duplicate R102 row removed; R50, R51, R100, R105, R108 and R120 brought up to date; no stale `pr/380` ref exists in this clone | Move the seam row when the fork's lap carries it; R32 | ours; the seam file is the fork's |
| R128 | **[x] Done 2026-11-04: (a) the fatal box attached to a hidden dialog, fixed `ca9e158c`/`414358d5` (17 of 20 failing to 0 of 20 in the failing order); (b) the close's report flush draws on the shared deadline, `bd72c2cf`/`57fe56b9` (5.52 s to inside a 1.5 s budget); (c) the optional-group sweep, `d06bac1f`/`e2d03202`, one hit (`Rip completed:`'s track count). Each held by a test a revert probe detects.** Found while fixing R118 and R116 (2026-11-03). (a) The fatal-dialog tests in `tests/test_app.py` fail about one run in three at `-n 4` beside `tests/test_ui_main_window.py`, on `main`'s own conftest too: "Internal C++ object (QTimer) already deleted" at `app.py:342`. (b) The close's report flush keeps its own 5 s bound outside the shared `ShutdownDeadline`, and the no-late-import test closes an idle window, so a close during a rip is unproven. (c) R116's sweep covered `pregap_search`'s two optional groups; the other `int_or_none` callers were not swept for optional groups (none fired in the run's bundle) | Fix (a) at its cause; (b) and (c) with tests | ours |
| R129 | **Triaged 2026-11-16 (STALE-BUT-OPEN, OWNER): the drive came back (the 2026-11-04 Full run on 0.7.120 is in the ledger, `docs/testing.md` §5B); this 0.7.119 bundle is not filed (no `round37full1103b` rows in `docs/evidence-manifest.tsv`), which needs the owner's upload if it is still wanted.** **[~] The owner's Full run on 0.7.119 with `.28` (2026-11-03 23:05 UTC): the drive dropped out mid-run.** 462 pass, 16 fail, 1 blocked, 128 unreachable. Every failure is at or after section N: on the secure re-read's track 10 the drive stalled 17 s on LSN 170803, returned 6,720 unreadable sectors, and cyanrip stopped on `Drive media change query failed` (exit 74) at 00:34 UTC; from then on `/dev/sr0` did not exist in the container (`Can't get file status for /dev/sr0`), so O, P, P2, P3 and the rest failed with exit 74. Nothing of ours touched the drive then: no force stop, eject or signal in the app log. Before N, every step passed, the new ones included (D2 Settings OK, H2's Cancel and Replace, `expect-read-offset` 12 of 14 AccurateRip matches, K1 to K3 on the derived files). The 128 unreachable are E2 and P5/P6, which skip by design now that the default and the build under review are both `.28`. N's 9 tracks read track 3 WRONG again in a sequential rip (R123). Found and fixed: the ladder's sentence calling exit 74 a code cyanrip never returns. | The owner: check the drive (power, cable, a reboot), then rerun the Full run on 0.7.119; file this bundle on `evidence` beside it | the owner's rig; ours to read and file |
| R130 | **[x] `.30` (`5cc1c6b`) is the build under review from 2026-11-05 (the fork's round 38 lap 12: published on beta and round 38's pin moved to it on their owner's word, *"ya, i think it makes sense to do our testing with the new release and everything it has already improved"*, and ours the same day).** Done in the code: `PIN_UNDER_REVIEW` `5cc1c6b` (round 38), `release_seq` 41 from their manifest at `1c8099c3` (filed byte-exact), `.30` in the `--consumer`, `--prefer-disc-isrc` and `--prefer-accuraterip-match` sets and in `-Y`'s as the pin under review (`.29` named there by commit, which it reached only as the pin under review), exit class 64, and its provider contract (built at `g0c276fc`, same `src/` and `meson.build`, anchor `ea7e371fa0b470b1`) filed with the inventory regenerated from it (166 P5, 14 P5a). **What closes it:** 0.7.121 naming `.30` (no standing word covers the release), then the owner's drive test on `.30` through it, filed on `evidence` and read by each side (the fork's lap 12 S10). `FORK_PIN` stays `3f288fb` until round 38 closes. **Before, `.29` (`8d2ca72`), from 2026-11-04 (the fork's round 38 lap 5: published on beta and round 38's pin moved to it on their operator's word, *"Yes to all"*).** Done in the code: `PIN_UNDER_REVIEW` `8d2ca72` (round 38), `release_seq` 40 from their manifest at `1d7a1a4` (filed byte-exact), `.29` in the `--consumer`, `--prefer-disc-isrc` and `--prefer-accuraterip-match` sets and in `-Y`'s as the pin under review, exit class 64, and its provider contract (built at `g2a06e064`, same `src/` and `meson.build`, anchor `70549c5b81227f06`) filed with the inventory regenerated from it. **What closes it:** our release naming `.29` as the build under review (0.7.120, on the owner's word; no standing word covers it), then the owner's Full run on `.29` with it (round 38's close condition, the fork's lap 1 S14), filed on `evidence` and read by each side. `FORK_PIN` stays `3f288fb` until round 38 closes. **2026-11-04:** 0.7.120 released (`f8e2b17a`, lap 6 sent at `c0cb43a3`); the owner's install of `.29` was refused on a longer short hash and fixed (`7fdc33a1`, R132), then the Full run ran from 12:53:46 UTC: 591 pass, 2 fail (`expect-ctdb whole` in F and N, track 5, the disc: see the tracks 3 and 5 row), filed on `evidence` at `78cff7e8`. Left: our lap 7 reading it, and the fork's lap reading it; then round 38 closes and `FORK_PIN` rolls. Done 2026-11-11: round 38 closed on both laps' `GO` (R143), and `.31` takes the review over (R144). |
| R131 | **Triaged 2026-11-16 (OPEN-OURS): unchanged; the same family as R155.** **[ ] Say, on the error-positions row of a track a later pass re-ripped, that its block CRCs describe the album pass and not the shipped read.** Found reading the 2026-11-04 run: in the whole-disc rip the block CRCs of tracks 3 and 5 combine to `3D8FCF0C` and `6902BCF0`, the album pass's reads, beside copy CRCs `59D352DD` and `E0036697` from the app's later pass. The block says `describes: album pass`, so nothing is false, but a reader comparing a row's block CRCs with its copy CRC is comparing two reads. Add the per-track fact (re-ripped by a later pass, or not) beside the row, with a test on that run's report. |
| R132 | **[x] Triaged 2026-11-16: done: ours shipped in 0.7.121 (`deps/fork_source.py:3048`, `core.abbrev 7`), and the fork asks for seven characters (`cyanrip@6b5b9dc7:src/meson.build:214-215`), recorded in our round 38 lap 7 S10.** *Was:* **[~] The fork's build tag grows with the clone; ours is pinned (`7fdc33a1`, PR #449), theirs is not.** Their `src/meson.build` `vcs_tag` prints `git rev-parse --short HEAD` (`cyanrip@8d2ca726:src/meson.build:200-210`), which git lengthens as a repository grows; their repository passed eight characters with `.29`. Our installer now pins `core.abbrev 7` in its clone and names a longer hash when it refuses. Left: ship it (0.7.121, on the owner's word), and send the shape to the fork in our lap 7 as a NEXT-ROUND item, since a build of theirs from a large clone names itself in a form their own manifest and ours do not list. |
| R133 | **[x] Triaged 2026-11-16: done: the hardware proof ran in the 2026-11-10 Full run, committed twice toward entry 32115, track 5 `E0036697` to `C96464AB`, disc `5092E94B`, AccurateRip v2 `BCF4E815` at 200 (our round 38 lap 17 S3), the pre-registered values. The re-verify abandoned on close stays a stated limit.** *Was:* **[~] WIN. No button (the owner, 2026-11-05, KDD-47 amended): the repair runs on its own after a rip when every proof passes, on a worker with a real `cancel()`, re-verifies and says what it did; when it refuses or fails, the rip's result says why in plain words and what the user can do; a Settings switch, on by default; derived copies made from the repaired FLAC.** **Built 2026-11-05; the hardware proof is left.** *Trigger:* `ctdb/repair_run.differs_from_strongest` (a MATCH or NO_MATCH whose strongest entry our audio does not equal at any measured offset, an outvoted match included); armed on the CTDB check's own daemon before it emits (`_arm_ctdb_repair`), so the library move cannot settle in the gap before the slot. *Worker:* `workers/ctdb_repair_worker.py`, a `QThread` worker stopped in `closeEvent`; every child (`metaflac` lengths, `flac` decodes and encode, `metaflac` metadata copy, the re-verify's decodes) runs through one `killable.KillableJob`, whose `cancel()` SIGKILLs the one in flight and refuses every later run (new: `KillableCommand.run_bytes` for binary pipes, `flac_rewrite.killable_runner`, `decode.killable_runner`/`killable_probe_runner`). It waits for the album's other readers, feeds AccurateRip's per-track answer from the rip's log (`repair_run.accuraterip_answers`; refuses outright when the log and files cannot be lined up), passes each track's offset-0 CTDB CRC as `ctdb_crc_before`, and after a REPAIRED outcome runs a fresh verify, kept as `CtdbVerifyResult.after_repair`. *Window:* `ui/main_window_ctdb_repair.py` (`CtdbRepairMixin`): the CTDB gate stays pending during the repair; on landing the read's verdict is recorded with `repair` and `after_repair` beside it (report schema 44, unreleased: `ctdb.after_repair`, `settings.ctdb_repair_after_rip`), the derived copies are made again from the repaired FLAC (whole album, same transcode) and the derived verify, checksums and FLAC integrity re-run with their stale results cleared. The EAC-layout log is rendered from the read's verdict only (KDD-24). *Told:* `ctdb/repair_wording.py`, a line under the CTDB verdict and in the log view: ✓/⚠/ⓘ, the track, samples, entry and submissions, the proof, the fresh check, AccurateRip *not determined* with our v1/v2 stated (no AccurateRip lookup of our own; the rip's log prints no database value for a track that did not match), where the original is kept; a refusal or failure says why, what to do, and `failure_text.LOG_POINTER`. Diagnostics `ctdb_repair.repaired`/`refused`/`failed` (and the tool codes `ctdb_repair.flac`/`metaflac`, used since 2026-11-04 and unlisted until now). *Setting:* `ctdb_repair_after_rip` (default on; Settings → *Repair from CTDB after a rip*; validated as a bool; frozen at Start on the record, which is what the decision reads). *Acceptance:* `expect-ctdb` grades the READ (`ctdb.verdict`/`outvoted`/`trustworthy`, unchanged fields), and names the repair as information only, so an archival grade the read failed cannot be satisfied by a repair; no severity changed. Held by `tests/test_ctdb_repair_auto.py` (revert-probed: switch off, refusal, cancel, the read's verdict kept, the move held). **Left:** the owner's hardware run on the reference disc against R43's pre-registered prediction; a closing window abandons a re-verify blocked in its CTDB HTTP lookup (bounded by the client's timeout). Was: (beyond EAC alone; parity with EAC plus CUETools). Native CTDB repair (KDD-47; `docs/eac-parity.md` Part G.4 item 1), on the owner's word of 2026-11-04. Build on R43's localiser: keep each correction's value; a pure repair plan mapping each word to track, frame and channel, refusing guard bands, out-of-audio words and unplaceable pregaps; patch only the damaged track's FLAC, re-encoded with the host `flac` and every metadata block copied; prove before replacing (re-decode equals original XOR plan, whole-disc CTDB CRC and the entry's track CRC match, AccurateRip v1 and v2 recomputed); keep the original; record it in the report; never edit the EAC-compatible log. Strongest entry only. In progress. Then: the GUI and script-verb wiring, and the hardware proof on the reference disc, pre-registered: entry 32115 at offset -7 (`tests/fixtures/ctdb_lookup_police_classics.xml`). |
| R134 | **Triaged 2026-11-16 (STALE-BUT-OPEN, WIN): the hold is lifted: round 39 closed GO/GO on 2026-11-13 (R153) with G1 met, so by this row's own words it is a WIN, not a parity gap; EAC's 2026-11-12 re-rip did not verify track 3 either (`docs/eac-parity.md` G.7).** **[ ] HELD (2026-11-11, our round 39 lap 2 S11) until the five-rip run is read by both sides: the seconds where track 3's reads differ come from G4's `block_crcs` comparison, whose records now come only from the five-rip run (the owner removed the rips of 2026-11-09 and 2026-11-10), and if the chase and `.31`'s rule give `59D352DD` from a drive read in all five rips (G1), this row is a WIN, not a parity gap.** PARITY for track 3 (EAC reads it right on this drive; we do not reliably), and a WIN beyond it. Rebuild a disputed second from several reads, accepted only on AccurateRip v1 and v2** (Part G.4 item 2). Keep each read (the fork asked, in our round 38 lap 8, to keep every `-Z` read's audio and block CRCs); find the differing seconds by block CRC; candidates from per-sample majority and each observed variant, every sample one the drive returned; accept only on AccurateRip v1 and v2 (and the CTDB track CRC where present); cap and record the number of candidates tried. No ripper found automates this; two open requests on the ripper older versions used (its issues #667 and #679) ask for it. **2026-11-11:** the five-rip run ran (the owner's Full run on 0.7.122 with `.31`, from 12:34:47 UTC) and is filed on `evidence` at `ac0a5133`: in section R's five rips track 3 was `59D352DD` from a drive read, AccurateRip v1 128 and v2 200 (rip 3 by `.31`'s AccurateRip-guided rule). Still held until both sides have read it. |
| R135 | **[x] Triaged 2026-11-16: answered: both sides' dispositions are in our round 38 lap 17 S5 (seating refuted; speed and Pioneer's utility unsettleable on this drive), G1 was met in round 39, and EAC's 2026-11-12 re-rip on the same drive missed track 3 too (`00a3592b`, G.7), so the premise that EAC reads it reliably here no longer holds. The PureRead byte is `.30`'s vendor read (R137).** *Was:* **[~] PARITY: why our read of track 3 is less reliable than EAC's on the same drive. The owner's drive-mode and session experiment** (Part G.4 items 3 and 4): `rig_scripts/drivemode.txt` (`b1adb92f`), run with the disc left in, then wiped and reinserted, then after setting PureRead to Perfect (and Master) in Pioneer's utility on Windows 11 on the same machine. Never by interrupting a run: a Full acceptance run stays unattended. Read each bundle against Part G.2's two hypotheses. **First, a read-only check of whether the drive has PureRead at all** (READ BUFFER `0x3C`, ID `0xF4`, byte 9; Part G.4 item 3): the 209DBK at firmware 1.51 most likely reports *not supported*, which makes the Windows step moot and leaves Runs A and B (disc left in; wiped and reinserted) as the whole experiment. Pioneer's help also names a speed policy (*Advanced Quiet Drive*: the default spins slowly after insertion, then adjusts "depending on the situation"), a session factor for track 3 the same settings read reports (Part G.2), and testable from Linux with `rig_scripts/drivespeed.txt` (`-S 4` and `-S 24` against the drive's own choice; upstream `0be45a36` tries a set speed on a drive that does not advertise it). Bazzite runs first, and **the Windows step stays in the plan** whatever the settings read says: what this drive can do (PureRead, its speed policy, whether it honours `-S`) is *not determined* until the drive itself answers each, and a third party's reading of a settings byte is checked against the drive, not trusted (the owner, 2026-11-05: *"keep them open"*). The procedure: `docs/rig-scripts/README.md` → *Round 38's drive test*. |
| R137 | **Triaged 2026-11-16 (STALE-BUT-OPEN, parity): part (1) shipped in `.30` (`--read-vendor-settings` and `drive_declared`, read by `record_vendor_settings.py` and `record_drive_declared.py`); left: (2) the report in `--doctor` and an any-drive rig script, and (3) *Report this drive*, neither found in `src/`.** **[ ] PARITY (EAC's *Detect Read Features* measures a drive's cache, accurate stream and C2 for any drive). A drive report for ANY drive, and an opt-in way for a user to send it back** (the owner, 2026-11-05: *"shouldn't we keep testing, reporting, etc open to as many drives as we can? In case a user is testing our app with a way different drive and needs to report or add something? We want to give them the choice and also allow that, but also, see a report back on what it is saying for our bug testing"*). Three parts. **(1) Theirs, asked in our standing status:** a read-only drive report from cyanrip (INQUIRY and firmware; the MMC capabilities page and feature list: C2, speed selection, accurate stream, cache; and, only for a vendor that documents one, its settings read, such as Pioneer's buffer `0xF4`), since drive I/O is the ripper's under `docs/OWNERSHIP.md`; **the owner's word of 2026-11-05 on the vendor read: "Yes do this"**, opt-in, read-only, sent only to a drive whose INQUIRY names the vendor, each row citing its source (relayed in our round 38 lap 11); tri-state throughout, a capability the drive does not report is *not determined*, never *no*. **(2) Ours:** run it in `--doctor` and carry it in every bundle; a generic rig script that measures any drive on any disc (cache, speed honoured, repeat reads of every track against AccurateRip), not the reference disc's tracks 3 and 5 alone. **(3) Ours, the choice:** nothing leaves the user's machine on its own; a *Report this drive* action builds the bundle (no serial numbers, no home paths, no hostnames) and opens a prefilled GitHub issue for the user to read and send, so reports from other drives reach our testing. | (1) the fork's wording, read before they build it; (2) and (3) after it | ours, theirs |
| R138 | **[x] WIN (round 39 G2): an AccurateRip witness for repaired audio** — done 2026-11-11 (`adapters/accuraterip_db.py`, the dBAR parser, `ctdb/repair_accuraterip.py`, G2 in `expect-track-records`); hardware proof pending: the next Full run's track 5 record must read `v2 BCF4E815 matched (confidence 200)`. Was: The record built at `c1d2dcb1` says AccurateRip v1 and v2 of a CTDB-repaired track are *not determined*, because Platterpus has no AccurateRip lookup of its own and cyanrip's answer describes the read. G2 grades track 5 on AccurateRip v2 verifying the repaired track. Fetch the disc's `dBAR-<n>-<id1>-<id2>-<cddb>.bin` (path from id1's three lowest hex digits; verified by hand on 2026-11-11, our lap 17 S3: the repaired track's v2 `BCF4E815` is the top entry at confidence 200) and compare the repair's `accuraterip_v1_after` / `v2_after` | An adapter under `adapters/`, a parser with a never-raises property test, the record wired to it | ours |
| R139 | **[x] Add `expect-track-records` to `fullacceptance.txt`** (done 2026-11-11) sections F and N after `expect-ctdb whole` (round 39 G3), remove its `UNUSED_BY_ANY_RIG_SCRIPT` entry and put that ceiling back to 3 | With the five-rip run's script update | ours |
| R140 | **Triaged 2026-11-16 (OPEN-OURS, low): exact on `.30` and later; with `FORK_PIN` at `.32` the floor reaches only logs from older builds.** **[~] The record's "n agreeing of m" is a floor before `.30`**: keep the ripper's converged `-Z` match count in the parser so the count is exact on older builds. **2026-11-12, our round 39 lap 2 S16:** on `.30` and `.31`, which print an `Other read:` line for every `-Z` read not kept, a converged track with none now reads the exact count (`3 agreeing of 3`, round 39's track 3, was `at least 2 agreeing of 3`): `track_record_sources.OTHER_READS_COMPLETE_BUILDS`, `tests/test_track_record_exact_agreement.py`. Left: the older builds, which still say the floor | Parser change with property test | ours |
| R141 | **Triaged 2026-11-16 (OPEN-OURS): unchanged at `ui/rip_progress.py:1689`.** **[ ] UX: the results-table EAC cell's tooltip** still says "✓ = AccurateRip-verified and copy OK" for a chase read whose reads disagreed; match the record (`c1d2dcb1`) | Wording and its test | ours |
| R142 | **Triaged 2026-11-16 (OWNER): unchanged.** **[ ] Owner to confirm: the EAC-layout log is rewritten after a CTDB repair** (`c1d2dcb1`). KDD-47 says "never edit the EAC-compatible log"; the change keeps every row of the read and adds the `Record:` line and a status naming the repair, reading KDD-47's intent as protecting the record of the read (`docs/eac-parity.md` Part B). The ripper's own log is never touched | The owner's word, then KDD-47 amended or the rewrite reverted | owner |
| R143 | **[x] Round 38 closed, 2026-11-11**: the fork's lap 18 (`GO`, released on their owner's word) filed byte for byte; `FORK_PIN` `3f288fb` -> `5cc1c6b` (`.30`), approval record round 38 with 0.7.121; `.28` kept in the `--verify-log` set. Round 39 opens with the fork's lap 1 on `.31` | Filed lap, pin roll, generators | ours |
| R153 | **[x] Round 39 closed, 2026-11-13**: the fork's lap 7 (`GO`, released on their owner's word *"Release on their GO"*, `cyanrip@2a49776a`) filed byte for byte; with our lap 6 `GO` both gates read it CLOSED. `FORK_PIN` `5cc1c6b` -> `e531a33` (`.31`), the approval record to round 39 with 0.7.123, the dependency map and contract regenerated. The next release installs `.31` by default, on the owner's word | Done | ours |
| R154 | **[x] `.32` (`edb73dd`) is the build under review for round 40** (the fork's round 40 lap 1, released 2026-11-13 on their owner's word *"do your own thing if you can without their input"*; `release_seq` 43 at `cyanrip@73cb652e`). Filed: the lap, `.32`'s provider contract (built at `gbfe2766`, anchor `c043ff9a9c4d6d93`, P1 byte-identical to `.31`'s), the manifest fixture; `PIN_UNDER_REVIEW` `edb73dd`, round 40, every gated set `.31` is in (`.31` named in the `--verify-log` set), the inventory (sites only) and the generators. Their S4 to S6 checked against ours: `c2_declaration.py` maps all four `C2 errors:` values as they say (now pinned by a test), the footer's third form is `secure_rereads_footer.py`'s, and no file of ours reads `Still waiting:`. Done since: our lap 2 (released 2026-11-14, `01c291e9`) and 0.7.125 naming it (`553a2d8c`). **2026-11-14:** the owner ran a Full run of 0.7.125 with `.32` from 02:12:01 UTC (650 pass, 2 fail: sections F's and N's `expect-ctdb whole` on track 5's read, repaired after), filed on `evidence` at `7faf1b9f`; G1 holds in all 23 `.32` rip logs and their 21 reports (counted 24 on first reading; corrected 2026-11-16), and G2 in the whole-disc rip, the secure re-read and all five of section R's rips (track 5 by the labelled CTDB repair, AccurateRip v1 and v2 matching). **2026-11-16:** the fork's lap 3 (`GO`, `cyanrip@8fc88cc2`) filed byte for byte; our lap 4 (`GO`, answering their S13 and S14 with R155 and R156) written and held. **Round 40 closed 2026-11-16**: our lap 4 released on the owner's word *"release lap 4 when ready"*; both gates read the round CLOSED; `FORK_PIN` `e531a33` -> `edb73dd` (`.32`), the approval record to round 40 with 0.7.125. Left: our next release installs `.32` by default, on the owner's word | Release | the owner's word |
| R155 | **Triaged 2026-11-16 (OPEN-OURS): verified at `parsers/cyanrip_log.py:4526-4527` and `record_track_v11.py:128`.** **[ ] `kept_read_began` describes the album pass's read, not the read the file carries** (the fork's round 40 lap 3 S13). In all seven whole-disc rips of the 2026-11-14 run, tracks 3 and 5 give the whole-disc read's start (rip 1 track 3: `05:02:54Z`, a read of `2E36401F`) while the file holds a later read (the securing pass's `59D352DD`, begun `05:21:02Z`; in rip 2 the chase's ninth read, `06:36:53Z`). The field is read from the album pass's log line (`parsers/cyanrip_log.py:4526-4527`) and its `-j` record (`record_track_v11.py:128`), and nothing replaces it when a later pass's read is kept. Same family as R131. Fix: take it from the read the file carries, or say which pass it describes, with a test on that run's report (evidence `7faf1b9f`) | Record field and its test | ours |
| R156 | **Triaged 2026-11-16 (OPEN-OURS): verified at `track_record.py:144-148`.** **[ ] A CTDB repair's record names the securing pass's reads, not the read it repaired** (the fork's round 40 lap 3 S14). Rip 1's track 5 says `after the read (re-read, at most 5 agreeing): Copy CRC 6902BCF0 before`; `6902BCF0` is the whole-disc read, a single read, which the file held, and the five agreeing reads were the securing pass's `E0036697`. `track_record._repaired_line` (`track_record.py:146`) takes its parenthetical from `track_record_reads.read_path`, which reads the securing pass's counts whatever read was kept. Fix: name the read the repair started from, with a test on that rip's report (evidence `7faf1b9f`) | Record wording and its test | ours |
| R157 | **[ ] JOINT. Retire or define the protocol's deferred list** (old A6, A10 to A13, lines 3412 to 3442; `docs/handshake-protocol.md:1573-1578`): five header fields, the transport retirement, `CONCURRENT-WITH`, `SEAM-COMMANDS` and the semantic-change marker, carried since v6 and taken by neither v8 nor v9. With K1 (round 41 list item 5), a v10 on both operators' words (triaged 2026-11-16 from the old sections; the line is TASKS.md's at `34d20333`) | Protocol v10 | both |
| R158 | **[ ] The 14 untested conformance rows C21 to C36** (line 3978): the shared protocol's §8 table is run, not read, and these rows have no case in `tests/test_handshake_conformance.py` (triaged 2026-11-16 from the old sections; the line is TASKS.md's at `34d20333`) | Test cases | ours |
| R159 | **[ ] Bring the challenge ledger up to date** (old C10, line 3539; `docs/cyanrip-handshake.md` §9 stops at round 29): rounds 22 to 24 and 30 to 40, including the fork's round 40 lap 3 S4, S13 and S14, which they won (triaged 2026-11-16 from the old sections; the line is TASKS.md's at `34d20333`) | Ledger rows | ours |
| R160 | **[ ] Embed the whole `-j` record in `.platterpus.json`, and read `encode_failures`** (line 5096 with old E5, line 3655; the fork's `diagnostics.c:647`): the record still lands in the rips root; our status row `j-record-embedded` (triaged 2026-11-16 from the old sections; the line is TASKS.md's at `34d20333`) | Report and parser | ours |
| R161 | **[ ] Read `--consumer` support from `cyanrip -h`, not a hand list** (line 5410, D5 B) (triaged 2026-11-16 from the old sections; the line is TASKS.md's at `34d20333`) | Probe | ours |
| R162 | **[ ] Derive `a_round_is_reviewing_a_build` from the round record, not by comparing pins** (old F3, line 3741) (triaged 2026-11-16 from the old sections; the line is TASKS.md's at `34d20333`) | Gate | ours |
| R163 | **[ ] A provenance field for `defeat_audio_cache`** (line 5435): which probe and when, per drive (triaged 2026-11-16 from the old sections; the line is TASKS.md's at `34d20333`) | Record field | ours |
| R164 | **[ ] A never-raises property test for `build_report`** (line 6280) (triaged 2026-11-16 from the old sections; the line is TASKS.md's at `34d20333`) | Test | ours |
| R165 | **[ ] Acceptance-run grading** (lines 5879, 5076, 5941, 5930): `rig-check` told its subject; a device-held verb for section J; a warning when the app is newer than the script; grouping by section and severity (triaged 2026-11-16 from the old sections; the line is TASKS.md's at `34d20333`) | Grader | ours |
| R166 | **[ ] Our laps carry the leaving-beta objective** (old G12, line 3894): absent from rounds 36 to 40 (triaged 2026-11-16 from the old sections; the line is TASKS.md's at `34d20333`) | Lap content | ours |
| R167 | **[ ] UX: the Finish-setup dialog, and D6 C's line for state no preset owns** (lines 4269, 7264) (triaged 2026-11-16 from the old sections; the line is TASKS.md's at `34d20333`) | UI | ours |
| R168 | **[ ] A UTC offset on app-log timestamps** (line 4794) (triaged 2026-11-16 from the old sections; the line is TASKS.md's at `34d20333`) | Logging | ours |
| R169 | **[ ] Mutation coverage** (lines 6214, 6221, 6228, 5692): legs for `fork_source` and `rip_report`, `--min-score`, and the 77 survivors (triaged 2026-11-16 from the old sections; the line is TASKS.md's at `34d20333`) | CI | ours |
| R170 | **[ ] Rewrite the hardware checklist against today's Full script** (line 4057); with the docs consolidation of 2026-11-16, which merges it with the test plan (triaged 2026-11-16 from the old sections; the line is TASKS.md's at `34d20333`) | Doc | ours |
| R144 | **[x] Round 39 closed on it 2026-11-13 (R153).** *Was:* **[~] `.31` (`e531a33`) is the build under review for round 39** (the fork's round 39 lap 1, released 2026-11-11 on their owner's word; `release_seq` 42 at `cyanrip@73f65d7f`). Filed: the lap, `.31`'s provider contract (built at `g6eacb8b`), the manifest fixture, the shared `seam-commands.md` with its new row; `PIN_UNDER_REVIEW` `e531a33`, round 39, every gated set, the inventory and the generators. Left: our lap 2 (our cell for `--reread-until-accuraterip`, answers to S7 and S10), 0.7.122, and the five-rip run. **2026-11-11:** the five-rip run ran from 12:34:47 UTC (651 pass, 1 fail: section N's `expect-ctdb whole` on track 5) and is filed on `evidence` at `ac0a5133` | Pin move, generators | ours |
| R145 | **[x] Read `.31`'s `--reread-until-accuraterip` lines** (done 2026-11-11; the fork's round 39 lap 1 S3 to S6): the early end (`cyanrip@e531a33:src/cyanrip_main.c:2140`) as a `-Z` verdict, not converged; the overrule clause in the eight limit lines (`:2183-2242`); the `Secure re-read:` row (`src/cyanrip_log.c:852`); the footer printing neither form after an AccurateRip-ended track (`:339`) and its proposed third form (S7). `reread_ar_overrule.py`, the per-track record's `.31` seam wired, the merge carrying the fact; `tests/test_cyanrip_dot31_reread_until_accuraterip.py` | Parser and record | ours |
| R146 | **[x] Send `--reread-until-accuraterip 2` on the securing pass to `.31`** (done 2026-11-11; our round 38 lap 17 S8's commitment): `adapters/reread_until_accuraterip_args.py` (range, `-Z` rule, gate `fork_source.BUILD_TAGS_ACCEPTING_REREAD_UNTIL_ACCURATERIP`, `.31` only), threaded through the ABC, the backend and the worker's securing pass; the consumer contract regenerated; `tests/test_reread_until_accuraterip_flag.py`. Left: our cell for the shared `seam-commands.md` row, in our lap 2; the five-rip run shows it on hardware. **2026-11-12, the fork's round 39 lap 3 S15:** every `-Z` pass asks, the album pass too when it reads with `-Z` (section N's whole-disc pass sent `-Z 2` alone), never a pass without `-Z` (`confidence_for_pass`; `tests/test_reread_until_accuraterip_passes.py`); `--reread-time-limit` stays on the securing pass. Left: the shared `seam-commands.md` row's PP cell still reads "on the securing pass only", to change with the fork in a lap, since its bytes must equal theirs | Argv | ours |
| R147 | **[x] Triaged 2026-11-16: done: the five-rip run's bundle carries 83 records (evidence `ac0a5133`) and round 39 closed, so the owner's re-send is no longer needed.** *Was:* **[~] Every rip's `--diagnostics` record in the bundle** (the fork's round 39 lap 1 S10, BLOCKING). Found: the app's Full-run bundle already carried every album and securing pass record (26 under `ripperdiagnostics/` on 2026-11-10, `cyanrip@60b545ed:docs/rig-2026-11-10-5cc1c6b/MANIFEST.txt:156-181`), but the fork's filing of it kept none; chase reads' records were deleted with their temp folders; `drivetest.sh` never collected any. Done 2026-11-11: `chase_record_keep.py` keeps each chase read's record, the scan cap is 400, every `drivetest.sh` upload carries the records since its test began, and `drivetest.sh records` packs those since 2026-11-09. Left: the owner runs `bash ~/platterpus-rig/drivetest.sh records` (or re-sends the 2026-11-10 bundle, whose `ripperdiagnostics/` holds 26) for the track 3 comparison before the five-rip run. **2026-11-11:** the five-rip run's bundle carries 83 records under `ripperdiagnostics/`, 36 album and securing passes and 47 chase reads' (45 `-chase-t05`, 2 `-chase-t03`), filed on `evidence` at `ac0a5133` | Bundle, rig script | ours, then the owner |
| R148 | **[x] Done 2026-11-13: a citation that resolves as evidence must carry its full 40-character commit (`refs.Trees._evidence`) and its SHA-256 (`check._evidence_form`); three tests, revert probe detected both, and our sent lap 2 S6 now reads refused, as the fork's checker read it. *Was:* Our lap checker passed an evidence citation without its SHA-256** (the fork's round 39 lap 3 S1): our round 39 lap 2 S6 cited `cyanrip@60b545ed:docs/rig-2026-11-10-5cc1c6b/MANIFEST.txt:44`, a file on their evidence branch, with no hash, which HR-2 6a asks for; their checker refused it and ours did not. Find why (`scripts/laplang/refs.py` `_evidence` on a peer citation) and make ours refuse it, with a test | Checker fix with test | ours |
| R149 | **[x] Done before we sent it: the fork adopted it from their own owner's word, `cyanrip@f1c5d935`, their round 39 lap 5 S12; our lap 6 S4 acknowledges it. *Was:* Send the owner's first question to the fork in our next lap** (2026-11-12): "who released the last lap, and who is holding the next", asked first in every session on both sides; ours answers it with `scripts/lap_turn.py` and the session-start hook. Ask them to add the same to their `CLAUDE.md` (transport, so it lives in both) | Our round 39 lap 6 | ours |
| R150 | **Triaged 2026-11-16 (OPEN-OURS, parity): unchanged: `supports_offset_detection` still returns False (`adapters/rip_backend.py:735-748`).** **[ ] PARITY (EAC's key-disc calibration): measure the read offset from a disc for a drive AccurateRip does not list.** The audit of 2026-11-12 against the owner's EAC guide found cyanrip's `-f` offset finder wrapped but not wired in (`adapters/rip_backend.py:735-748`, graded against +667). Needs a disc AccurateRip knows; run at drive setup, saved per drive, under the owner's rule *test the drive once, up front* (CLAUDE.md) | Wire `-f` into the drive-setup dialog on a worker, with its result recorded as the drive's offset provenance | ours |
| R151 | **Triaged 2026-11-16 (STALE-BUT-OPEN): the fork answered: both probes agreed in 17 runs on this drive, and which one setup keeps is ours (their round 40 lap 1 S7 and S8, lap 3 S5); left: our decision and the log row naming its source.** **[ ] Two cache-defeat sources, reconciled.** Our *Analyze cache* runs `cd-paranoia -A` (`cache_probe.py:13-15`, which calls it the rip's own engine), and the fork's `--cache-probe` with `-I` is a second, different probe (their provider contract, "costs seconds"). Say which one the log's `Defeat audio cache` row reports, and whether setup should use the fork's (asked in our round 39 lap 6) | A decision and one source of record | both |
| R152 | **Triaged 2026-11-16 (STALE-BUT-OPEN, parity): the fork answered yes: `-I` prints both lines without ripping, from the same capability queries a rip runs (their round 39 lap 7 S6, `cyanrip@e501a060:src/cyanrip_main.c:435-466`); left: our setup probe on a worker, saved per drive.** **[ ] PARITY: read the drive's declarations (accurate stream, C2) once at drive setup and save them per drive** (the owner's rule of 2026-11-12; part of R137). Today they are read only during a rip. Asked of the fork in our round 39 lap 6: does `-I` with an audio disc print `Accurate stream:` and `C2 errors:`, and does their read path depend on accurate stream (`docs/eac-parity.md` Part F row 16) | Their answer, then a setup probe on a worker | both |
| R136 | **[x] CUETools is GPL-2.0-or-later, not LGPL: correct the wording where it still says LGPL** (done 2026-11-11: every current statement corrected; KDD-14's and KDD-16's original words kept as the record, under a dated correction; the session log left as written) (Part G.6). Found building the CTDB repair (2026-11-04): CUETools' own `License.txt` (`gchudov/cuetools.net` at `f2ec334`) grants GPL version 2 "or (at your option) any later version". Corrected where the repair touched it (`ctdb/differences.py`, `ctdb/verify_parity.py`, `ctdb/localise.py`, PLANNING KDD-14's amendment). Still saying LGPL about CUETools: `src/platterpus/adapters/ctdb_client.py` (2), `adapters/ctdb_parity.py`, `ctdb/calibrate.py`, `ctdb/crc.py`, `ctdb/gf16.py`, `ctdb/matching.py`, `ctdb/rs_decode.py`, `ctdb/sweep.py`, `ctdb/syndromes.py`, `ctdb/toc.py`, `PLANNING.md` KDD-14 and KDD-16, `docs/ctdb-crc-algorithm.md`, `docs/architecture.md`, `docs/README.md`, `docs/test-plan.md`, `DEPENDENCIES.md`, and dated entries in `docs/session-log.md` (left as written: a log records what was believed then). Not every LGPL in `docs/cyanrip-fork.md` (which since 2026-11-16 also holds the former `cyanrip-upstream.md`, as Parts C and D) is about CUETools: cyanrip itself is LGPL, so read each. The clean-room choice of KDD-16 does not depend on the answer (GPL-2.0-or-later code may be ported into GPL-3.0-only) | Correct each in one commit, with this row's source | ours |
| R119 | **[x] Done 2026-11-03 (`0c5e9881`): the comment says the lock engages on an undetermined answer, and a test holds it to the worker's condition (`tests/test_cyanrip_rc3_readiness.py::test_the_speed_line_comment_states_the_lock_the_worker_applies`; revert probe: detected).** *Was:* a stale comment (finding 8). `parsers/cyanrip_log.py:365-370` says an undetermined speed answer leaves the speed lock off; the code locks on anything but an explicit yes (`workers/rip_worker.py:1891-1896`), which is right. |

## The getting-started walkthrough (planned 2026-10-06, framework 2026-10-07, `PLANNING.md` KDD-42)

An archival (EAC-parity) rip of an average disc, step by step, for a first-time user:
a written step list with still screenshots and three short GIFs, shot by a script on
the rig. **In the app by default** (Help → Getting started, offline) **and on GitHub**
(the README's *Getting started* section, generated from the same source). Every
ruling is KDD-42 (W1 to W7). The framework shipped in 0.7.101; the pictures are the
shoot below.

**The shoot (the plan; KDD-42 W7).** One sitting on the rig, about an hour and a half,
most of it the rip:
1. **In a fresh `demo` account**, download the AppImage and allow it to run. Spectacle:
   `01-allow-to-run.png`, its Properties → Permissions.
2. **Double-click it** and Spectacle the *Set up Platterpus* question:
   `02-first-run-setup.png`. Then answer **Yes** and let setup finish.
3. **Insert the disc** and run `./platterpus-x86_64.AppImage --run-script walkthrough`.
   It photographs steps 3 to 8 and rips the disc once.
4. **Upload** the run folder it names at the end, with the two Spectacle PNGs.

Then, here:
- `scripts/build_walkthrough_media.py` builds the files;
- the guide gains an image line for each picture;
- the size budget is set from the real total;
- `SHOOT_STATUS` becomes `shot`;
- the README regenerates;
- it ships in the next release.

**Decide on the day** (KDD-42, *Not decided here*): the disc, which must be one that
AccurateRip and CTDB both know; the window size; and the budget. One look throughout:
Breeze light, 100 % scaling.

**Open:**
- [ ] **Triaged 2026-11-16 (HARDWARE): unchanged: `getting_started.SHOOT_STATUS` is still `pending` (`getting_started.py:67`).** **The shoot**, above. Needs the rig, the `demo` account and the disc.
- [ ] **Triaged 2026-11-16 (OPEN-OURS): unchanged: `uiscript/run_sizes.py:85` still decides by run size alone.** **`counts_as_evidence` is decided by the run size alone**, so any script run at
  Full says `true`: the walkthrough, `securereread.txt`, `police-rerip.txt`. The ledger
  grades only `fullacceptance.txt` runs by hand, so nothing was miscounted. But the
  field claims what it does not know; it should require the acceptance script. Found
  building the walkthrough, 2026-10-07; not changed on release day.
- [ ] **Triaged 2026-11-16 (HARDWARE): unchanged; waits on the shoot.** **A callout can name a label on a Settings tab that is not showing**; if the shoot
  shows it, the script opens that tab first. Only the rig can say.

## 2026-10-05 window size and readability audit

The maintainer: *"double check window sizes and readability, especially on obscure
windows like the beta or odd cyanrip upgrades"*. Every window, message box and Qt
dialog the app can show was built with its real worst-case text and measured
headless (offscreen, Fusion, DejaVu Sans) from 853 × 533 to 1920 × 1080 logical,
at 100 % and 150 % text, and the screenshots were looked at.

- [ ] **Triaged 2026-11-16 (HARDWARE): unchanged; a by-hand check at 150 % on the rig.** **Confirm on the rig what headless cannot show.** Real KWin decorations and
  placement, Noto Sans metrics (DejaVu Sans, used here, is wider), and native
  Wayland, where a client cannot place its own window. At 150 % text, open Help →
  Check for cyanrip updates and the test console's script reference, and confirm
  the buttons are on screen.
  - *2026-10-06 (A4, cec0a55b): not a step, and why.* The text scale is a desktop setting a
    script can neither set nor put the run into, so a run cannot place itself at
    150 %. The two windows the row names are outside the script surface: *Check for
    cyanrip updates* reads the fork's manifest and can offer an install, which no
    verb may answer, and the script reference belongs to the console that runs the
    script. And on native Wayland the compositor places windows, which the app
    cannot read back to grade. It stays a by-hand check at 150 % on the rig.
- [ ] **Triaged 2026-11-16 (OPEN-OURS, low): unchanged; fine to stay open.** **Qt's own file dialog and tooltips are not measured.** On the desktop the
  file dialog is usually the desktop's own, not ours to size.

## 2026-10-04 hardware runs — two discs MusicBrainz does not know, then a damaged one

Four acceptance runs on 0.6.65 + `.19`, graded `partial` (`docs/testing.md` §5B, and
`docs/handshake/artifactsround30/README.md` → *The 2026-10-04 runs*). Fixed after the
runs, each with a regression test:

Open:

- [~] **Triaged 2026-11-16 (STALE-BUT-OPEN, parity): the EAC-layout log now prints EAC's `There were errors` with our count line when AccurateRip contradicts a track or a replaced read held the errors (`eac_log_export.py:1411-1430`); for the two triggers proposed here, unverified skips and an error line under a zero summary, it still appears to print cyanrip's sentence.** **The EAC-layout log and the report for a track with unverified skips.** Track 18
  still renders "Copy OK" and the status report "No errors occurred". The EAC-layout
  log is a surface the fork diffs against, so its wording goes through the handshake:
  proposed for round 31 in our round 30 lap 8. The report could carry an `issues` code
  sooner; it changes the report's vocabulary, so it waits for the same round.
  - *2026-10-05: the EAC-layout half is done* (`1e118482`; the row *"A skipped track
    AccurateRip did not confirm gets its own EAC-layout verdict"*): track 18 renders
    "Copy NOT confirmed". Still open, for round 31: the disc-level "No errors
    occurred" for such a disc, and the report's `issues` code.
  - *2026-10-21 (the owner's known-fixes list, items 3 and 12): our side is done.*
    The report raises `unverified_paranoia_skips` (warning) and, for an error line
    the ripper printed under `Ripping errors: 0`, `ripper_error_lines_under_zero_summary`
    (warning); its `health_status` and the window's status line stop reading clean
    over the second (`rip_health.py`). The EAC-layout `Read stability` line now names
    skipped tracks: `Read stability      : track(s) 18 had reads paranoia could not
    verify (skips) and AccurateRip did not confirm the audio — not confirmed`. Held by
    `tests/test_verdict_honesty.py`.
  - **Still open, PROPOSED FOR OUR ROUND 36 LAP: the disc-level sentence.** The
    EAC-layout log still prints cyanrip's "No errors occurred" verbatim
    (`eac_log_export._status_report`), because the fork diffs that line. Proposed
    replacement, exactly. When a track has unverified skips, or the ripper printed
    an error line under `Ripping errors: 0`, print EAC's own sentence for a rip with
    errors in place of "No errors occurred", followed by one line of ours naming
    what the ripper's count left out:

        There were errors
        Ripper's own count  : Ripping errors: 0 — not counted: paranoia skips on track(s) 18 that AccurateRip did not confirm

    and, for an error line (each quoted line verbatim, the first three, then
    "and N more"):

        There were errors
        Ripper's own count  : Ripping errors: 0 — not counted: 1 error line the ripper printed ("Error writing trailer: File too large!")

    When both apply, one `Ripper's own count` line names both, joined by `; `. A
    disc with neither keeps "No errors occurred" unchanged. "There were errors" is
    EAC's wording, not ours, so a log checker reads it as EAC means it; the second
    line is ours and says so by its label.

## Round 30 — CLOSED on both gates 2026-10-07 at seventeen laps (opened on `174a134`, `+platterpus.19`): the Full run on 0.6.65 with `.19`, and the operator's release-cycle question

Their lap 1 (`cyanrip@171bcf9`, platterpus-fork tip `0ae873c`, sha256 `6db0ed0d…`, 15,546
bytes, `OPEN`, LSL 3) opens round 30 on `.19`, `release_seq` 29 on both channels,
released by their operator on 2026-09-30 before the run, by a recorded override of R8
point 3 (*"update all, include my override if needed. we are getting this started."*).
The operator had first chosen to hold it until the run existed; the fork then measured
that our section A could not accept `.19` until a lap named it (their S22–S24), so the
lap went first, as in rounds 26 to 29. Its close conditions (S9–S11): the proposal's D1
to D10 settled by both sides with the text in both trees; the Full run on `.19` from our
first release naming `174a134` as its build under review, its bundle in both trees and
each side's reading; and the closing releases named.

- [ ] **Triaged 2026-11-16 (HARDWARE): unchanged; a by-hand close mid-rip on the rig.** **S25 on hardware: close the window mid-rip on the rig, then `cyanrip -Y` on that
  rip's log must exit 0.** The hardware half of the fix above (split out 2026-09-30, so
  the code fix can stay `[x]`): only a drive run shows cyanrip writes its footer and
  `Log FUN512:` inside `drive_control.READER_TERM_GRACE_S` (8 s) on the container path.
  - *2026-09-30: the grace is 40 s* (the fork's round 30 lap 5 S17: 8 s is shorter than
    one read). The rig's drive has done a single read of 20 s
    (`docs/handshake/outbound/artifacts/round-15-lap-13-cancelled-rip-g978f9b0.log:311`),
    so the grace is twice that, derived by a test from the filed logs. It no longer holds
    the window: the stop runs as exit work (`exit_work`), joined by `app.main` before the
    process exits. The hardware half stays open.
  - *2026-09-30: 42 s.* The fork's round 30 lap 7 S16 found this test read only our tree;
    theirs, searched whole, has two reads of 21 s on the same drive. One is filed here
    (`docs/handshake/inbound/artifacts/round-30-lap-07-accurip-gddc1e8c.log`), and the floor
    follows it.
  - *2026-10-05: 108 s.* The 2026-10-04 rig run's damaged disc took 54 s over one read
    (`docs/handshake/artifactsround30/round30oct04full.log:1501`); filed, and the floor
    follows it again.
  - *2026-10-06 (A4, cec0a55b): the cancel half is in the closing run; the close
    trigger cannot be a step.* Section I now names this row beside its
    `expect-log-well-formed` and `expect-album-audit ripper_log_integrity` (cyanrip
    `-Y` on the kept log), which grade a cancelled rip's footer on the container
    path. The post-cancel rescue and the window-close stop both reach the ripper
    through `drive_control.term_unsignalled_holders` with `READER_TERM_GRACE_S`, so
    that is the same signal and the same grace. What it cannot show is the close
    trigger: closing the main window ends the app and the script with it, so no
    later step can run `-Y` on what it left. That half stays a by-hand check on the
    rig (close mid-rip, then `cyanrip -Y` on the log).
- [~] **Triaged 2026-11-16 (HARDWARE): (a) to (d) are in the scripts and (e) stays by design; (a) needs a drive the AccurateRip list does not carry (E2 is N/A on the rig) and (b) a disc MusicBrainz does not know.** **Permutations the acceptance test still does not run** (found 2026-09-30,
  with the row above). (a) **Offset override off**: a drive in AccurateRip's list
  auto-applies the list offset and rips, an unknown drive is refused with a
  dialog, so no one script line holds on every drive, and on the rig the
  auto-apply could move the offset mid-run; it needs the script to branch on the
  drive, or a drive-independent verb. (b) The **unknown-album** path (section E
  aborts the run before any unidentified rip). (c) A **library move**
  (`library_dir` is kept, never set). (d) **`max_retries 0`** (no `-r` sent) and
  **`-Z 0`**. (e) `read_speed_mode fixed`, `update_channel beta`, auto-eject and
  Picard on. Each is a real path with no hardware evidence.
  - *2026-10-05: (c) and (d) DONE in script lines, (e) in part; no hardware
    evidence yet.* New section **J2** (Standard size, one track) rips with
    `max_retries 0`, `secure_rerip_matches 0` in UNIFORM mode, `read_speed_mode
    fixed` at speed 0, and `library_dir` set by the new verb `set-library-scratch`
    to `<rips folder>/libraryscratch` (inside the session folder, so the bundle
    still collects the album). Uniform, because dynamic mode's first pass never
    sends `-Z`, so "no `-Z`" there would hold whatever the setting said. It then
    grades `expect-library-move` (the window's own pointer moved into the library,
    log and report with it, nothing left behind), `expect-rip-argv without
    -r|-Z|-S` (the argv as spawned) and `expect-album-audit argv_agreement` (as
    received), and puts every setting back before K1 (`set library_dir ""` turns
    the move off). Section B round-trips `update_channel beta`, auto-eject on and
    Picard on, each straight back. Tested against the stand-in window and round
    29's committed reports, with J2's own lines run from the shipped file; 14
    reverts were each caught (`scripts/revert_probe.py`). The next Standard or
    Full run is the first on hardware.
  - *(a) still needs a design decision.* A drive in AccurateRip's list
    auto-applies the list offset (`_auto_apply_known_offset`, behind an
    information modal) and rips; a drive not in it is refused with a dialog. So
    one line passes on one rig and fails on another, and on the rig the
    auto-apply rewrites the offset `set-drive-offset` set, for every later
    section. It needs a verb that branches on whether the drive is in the list,
    or a way to exercise the path that does not depend on the drive. Which one is
    the maintainer's call.
  - *(b) still needs a design decision.* Section E stops the run when the disc is
    not identified, because every later rip would be evidence about a release
    nobody chose, so no unidentified rip is reached by design. Exercising the path
    needs either a disc MusicBrainz does not know (the run promises "any ordinary
    audio CD", so that is media-dependent), or ripping a known disc as unknown
    (File → Rip as Unknown Album), which the script cannot drive yet: that dialog
    is not in `open`'s table, and accepting it puts the rip controls in unknown
    mode for every rip after it. Which route, and where it can sit without
    affecting the rips after it, is a design decision.
  - *2026-10-06: (a) DONE in script lines, as ruled (KDD-41 C4); Done in
    688f0cee; no hardware evidence yet.* New section **E2** (Quick size, after E, before F) runs the
    new verb `expect-offset-refusal`: on a drive the AccurateRip list carries it
    records **`unreachable`** (N/A) and changes nothing; on any other it turns the
    override off, presses Start, answers the real *"Set up your drive first"*
    refusal with No, checks no rip started and puts the override back on every
    path (answered, a rip that started, the wait running out, the run stopped).
    `expect-drive-offset` and `expect override_read_offset on` follow it. The
    rig's BDR-209D is listed, so **on the rig this step records N/A**: only a run
    on a drive the list does not carry can grade the refusal. `RunReport.ok`
    forgives `unreachable` as it forgives a size's declines, and the RESULT line,
    `unreachable_lines` and the closing dialog name it, so it neither fails the
    run nor reads as a pass. Tested against the real gate
    (`RipMixin._on_rip_requested` with its real blocking box); 6 reverts each
    caught (`scripts/revert_probe.py`).
  - *2026-10-06: (b) DONE as a second script, as ruled (KDD-41 C4); Done in
    61f92ef8; no hardware evidence yet.* `rig_scripts/unknowndiscacceptance.txt`, run by the new menu
    item **Tools → Advanced → Run acceptance test with an unknown disc…** through
    the same session as the full run (no size question), and by `--run-script
    unknowndiscacceptance`. Its header says which disc it needs: one MusicBrainz
    does not know, with at least two tracks (a CD-R of your own recordings). It
    starts from the full run's baseline line for line (a test holds the two
    equal), checks the ripper and the offset, rescans, accepts *Rip as unknown
    album* with Picard unticked, asserts **`expect-unidentified`** (no release id,
    placeholder rows, unknown mode on, Picard not set to launch, no picker open),
    aborts on a disc MusicBrainz knows, rips tracks 1-2 and grades them with the
    full run's verbs plus **`expect-unknown-record`** (the report's `disc` block
    says `unknown: true` with no release id, and no `tagging_failed`). Its five
    sections are classified in advance in `docs/testing.md` (a second severity
    table, swept). 5 reverts each caught. **Needs a run with such a disc**, which
    the rig's usual disc is not.
  - *(e), what stays open and why.* A NON-ZERO fixed read speed sends `-S`, and a
    drive that reports its speed unchangeable makes cyanrip abort the rip on it
    (the BDR-209D, 2026-07-01): the same shape as (a). Fixed at 0 cannot tell
    fixed from the ladder on a healthy disc, whose first rung sends no `-S` either;
    only read errors show the difference. `update_channel` acts only on Check for
    updates, which no verb runs and whose answer is a modal (section A's
    `expect-newest-pair` reads the beta channel itself on every run). Auto-eject
    would eject the disc every later section needs, nothing records whether the
    tray opened, and the vocabulary excludes ejecting (`uiscript/verbs.py`).
    Picard on acts only on the unknown-album path, which is (b), and launching
    Picard is an external program the vocabulary excludes. So B's round-trips
    prove each value is accepted and stored, and nothing about what it does.
  - *Ruled 2026-10-05, "Do all recommendations" (`PLANNING.md` KDD-41):* (a) a verb that turns the offset override off and skips, saying why, on a
    drive AccurateRip lists; (b) a second acceptance script for a disc MusicBrainz does not
    know. In progress.
- [ ] **Triaged 2026-11-16 (HARDWARE): unchanged; needs a drive the list does not carry.** **E2 on a drive the AccurateRip list does not carry**: owed before 0.9.1, which
  also needs a second machine and distro.
- [ ] **Triaged 2026-11-16 (OPEN-OURS): the offset from a disc is now R150; CD-Text fallback tags, a MusicBrainz attach link (parsed as `cd_info.musicbrainz_submit_url`, `parsers/cd_info.py:60`, with no caller outside the parser) and rip-on-insert are not built.** **What other rippers have that we lack, our side** (the maintainer, 2026-10-07:
  *"anything in the instructions framework that seems like we are missing something
  that other rippers have or makes the workflow easier?"*). Checked against the code
  before listing; the parts that need the fork are asked in our round 31 lap 3 S5, S8
  to S12. Ours, most useful first:
  - **Find the offset from a disc** in Set up drive, for a drive AccurateRip's list
    does not carry (EAC, dBpoweramp and XLD all have it). The fork's `-f`
    found +667 on the rig (`round31fulltranscript.txt:1132-1160`); waits on S8 for a
    stable result to read. The guide's step 3 then gains a second route.
  - **CD-Text as fallback tags** when MusicBrainz has no match: the fork's header
    already prints the fields, and our `-I` info run already happens before the rip;
    the parser lists `CD-TEXT:` as a candidate only (`parsers/cyanrip_log.py:2574`).
  - **A link to add an unknown disc's ID to MusicBrainz** from the no-match flow, the
    way other rippers and Picard offer it; today we offer Rip as Unknown Album and Picard.
  - **Rip on insert** (optional, off by default), as dBpoweramp and EAC can.
  - Already present, so not gaps: a desktop notification when a rip ends
    (`notify_on_completion`, on by default), auto-eject, Test & Copy, CTDB verify.
- [ ] **Triaged 2026-11-16 (OPEN-OURS): not found built: `announce_lap` (`scripts/handshake.py:2058`) checks the lap number and a held body, not the ledger; both gates still refuse at close.** **Round 31: a lap writer that refuses a v6 `GO` without the ledger, on both
  sides** (our lap 16 S14). Both gates refuse it once sent; neither side's writer stops
  it being sent.
- [ ] **Triaged 2026-11-16 (OPEN-OURS): still no row in `docs/handshake/inbound/superseded/README.md`.** **`inbound/superseded/README.md` has no row for `round-07-lap-25-as-second-sent.md`**
  (noticed by the envelope helper, 2026-10-06).

## Round 29 — CLOSED on both gates on `51cc789` (`+platterpus.18`), 2026-09-29: the Full run on 0.6.63 + `.18`, and the tag change

Their lap 1 (`cyanrip@566d3fa`, sha256 `2e275d2f…`, 19,353 bytes, `OPEN`, LSL 3, released
by their operator 2026-09-28) opens on `.18`, `release_seq` 28 on both channels. Its
close conditions (S6–S9): our **Full** acceptance run with `.18` installed through our
app from a release whose `PIN_UNDER_REVIEW` is `51cc789`, with the bundle in both repos;
each side's reading of it; the tag change our operator ruled, and our reading of it; and
both closing releases (ours rolls `FORK_PIN` to `51cc789`, theirs is `+platterpus.19`).
Their gate reads round 28 closed on our lap 9, so round 28 is closed on both gates.

- [~] **Triaged 2026-11-16 (OPEN-OURS, low): (4a)'s lead-in debt still holds three patterns (`tests/test_regex_bounded_time.py:836`) and (6) `tests/` is still outside the size ratchet; neither blocks anything.** **Found while integrating, for later.** None of these blocks round 29.
  - *2026-10-05: re-sorted.* Merging the agents' branches had left (1)'s and (3)'s
    done notes under (2) and (6), and (2) written twice. Each note is now under its
    own item, and the only text removed is the second copy of (2). Open: (4), (5)
    and (6). (4) and (5) are in the 2026-10-05 ranked list at the top of this file.
  - (1) ~~The EAC-compatible log still says "re-reads did NOT agree" for a track whose
    re-reads hit the limit (`eac_log_export.py`). That overstates it for a track like
    round 28's track 5, where two reads agreed. Changing rendered EAC text has parity
    consequences, so this needs its own change.~~
    - [x] *Done in ce04e1fe:* the caveat follows what the log proves. "did NOT agree"
      stays only where no two reads agreed (the fork's `at most 1 read agreed`; round
      30's 10-05 track 3); an exact count reads "re-reads did not converge; at most 2
      of 3 reads agreed" (round 28 and round 26, track 5); a floor reads "at least";
      a log that does not say reads "re-reads did not converge" (round 27, track 3).
      The verdict line says "re-reads did not converge" for all of them. The count is
      parsed from the fork's line or from the `Repeating ripping` lines, now off the
      ignore list (consumer contract regenerated), and travels with the verdict through
      the auto-fix merge. Parity reasoning: `docs/eac-parity.md`, Part B, *The
      repeat-limit caveat*. **Still owed:** a NOTE in our next lap. Our round 29 lap 2
      S18 told the fork we skip the `Repeating ripping` line entirely; we now read its
      match count (not its checksum), and the rendered sentence changed (round 7 H4).
      *Sent 2026-10-05:* our round 30 lap 10 S20 says we read the count from your
      `Done;` line, or from the `Repeating ripping` lines before it.
  - (2) ~~The size ratchet, the regex-time sweep and the mypy gate cover
    `src/platterpus` only, not `scripts/`. `scripts/laplang/lsl3.py` is 428 lines, and
    `mypy --strict scripts/laplang` reports 3 errors in `scratch.py`.~~
    (`scripts-outside-gates`)
    - *Done in 4bd6d23c, 408981d2, 16838ec0, f8692ca1, 1beff95d, d5b489dc:* all three
      gates read `scripts/**/*.py` and `build/*.py`, one population defined once in
      `tests/conftest.py` (`maintained_tooling_modules`; `build/` not recursive,
      because `build/lib/` holds a package copy after a wheel build). Size: 19 tooling
      modules ledgered at their real counts (`lsl3.py` was 433 by then), floors of 40
      tooling and 35 `scripts/` modules, and the population checked against
      `git ls-files`. Regex: 88 literal patterns timed, all linear; the 15 computed
      ones (2 in `src/`, 13 in the tooling) ledgered per file. mypy: `files` is
      `src/platterpus`, `scripts`, `build/*.py`, with no opt-out; `scratch.py` was
      already clean, and the 12 errors found (9 in 5 scripts, 3 in `make_icon.py`)
      were fixed, one of them a crash in `scripts/check.py`. Two quadratic patterns
      the sweep could not see were fixed by hand (`bommap._REQUIREMENT`,
      `handshake._WIRE_FIELD`); see (4).
  - (3) ~~Nothing yet acts on `eac_log_producer`. The parity tool does not warn when its
    "baseline" is one of our own exports.~~
    - *Done in 67a86d06 (its tests' parametrize made literal in c369cfb9):*
      `scripts/eac_parity.py` names the baseline's producer and
      quotes its first line before any table. One of our exports (either banner) is
      refused, exit 2, with that line on stderr and in the log, and no table is
      printed. Before the fix, the committed export against its own rip printed
      "14/14 PARITY ✓" and exited 0. Refused rather than warned: a false pass gets
      cited, and a false refusal would need a real EAC log to begin with one of our
      banners. A baseline it cannot attribute is compared, but the output says the
      match is not parity with EAC. `parity.ParityReport.ok` now refuses a baseline
      that is ours, and rip_audit's `eac_log_agreement` (the other caller of
      `compare_logs`) gives that case a "not determined" WARN naming the line. Both
      read `identify_baseline`, which delegates to `eac_log_producer` and to the new
      `eac_log_producer_line`. revert_probe: 10 of 10 reverts behaved as expected.
      Not changed: `verify_log_surface.py::_is_ours_by_text` still uses its own,
      broader head-of-file rule. It is not a baseline consumer.
  - (4) **The regex-time sweep cannot see a pattern that only backtracks behind a
    literal prefix**, because it feeds runs of one character. Found 2026-10-05 while
    extending it to `scripts/`. The two in the tooling are fixed; the same shape, a
    lazy capture before trailing whitespace (`\S.*?\s*$`), is in eight
    `parsers/cyanrip_log.py` patterns (`_GAPS_VALUE`, `_READ_STALLS`,
    `_TRACK_ACCURIP_STATUS`, `_ENCODER_ERRORS`, `_INTERRUPTED_AT`, `_TRACKS_TO_RIP`,
    `_TRACK_PARANOIA_SCOPE`, `_TRACK_SECURE_VERDICT`). Measured on one line with
    8,000 spaces inside the value: `_READ_STALLS` 344 ms, `_GAPS_VALUE` 393 ms,
    quadratic. `inbound_text.MAX_LINE_CHARS` lets a line reach 65,536 characters,
    which would be tens of seconds per line. Two parts: rewrite them greedily, as
    `\S(?:.*\S)?`, with an equivalence test against the old form (they are published
    in `docs/cyanrip-consumer-contract.md`, so this regenerates it); and give the
    sweep inputs that pass a pattern's literal prefix, so it can find the next one.
    - [x] *Part one done 2026-10-06 in 5b32edfd:* the eight, and thirteen more of the same
      shape in the same file, rewritten greedily. The thirteen are eleven
      `(?P<v>.+?)\s*$` (`_DRIVE`, `_OVERREAD_MODE`, `_ALBUM`, `_ALBUM_ARTIST`, `_C2`,
      `_PARANOIA_LEVEL`, `_OUTPUTS`, `_SPEED_CAP`, `_PREEMPHASIS`, `_FINISHED_AT`,
      `_REPLAYGAIN`), which the lead-in inputs of part two measured equally
      quadratic, and the two bounded ones, `_INVOKED_AS` (`\S.{0,4000}?`, quadratic
      up to its bound) and `_PREGAP_SOURCE` (`\S.{0,63}?`, linear, rewritten so the
      file has one shape). `\S.*?` became `\S(?:.*\S)?`; `.+?` became
      `\S(?:.*\S)?|[^\S\n]`, whose second branch keeps `.+?`'s answer for a value
      that is all blanks (one blank); a bound `{0,N}?` became `{0,N-1}` between two
      `\S`. `tests/test_cyanrip_log_reads_values_greedily.py` keeps the 21 old
      forms and holds each rewrite to them with Hypothesis over generated lines
      (blank runs inside and after the value, every Unicode blank class, and a
      newline): same match, span and groups by `match`, `search` and `fullmatch`.
      Also hand-written lines with a match floor, the two bounds at N-1..N+2, and a
      timing pin per pattern on a 20,000-space line (not `_PREGAP_SOURCE`, whose
      old form was linear). The property was shown to catch four wrong rewrites
      (`|\s`, no blank branch, `.*\S`, `\S.*`). Contract regenerated.
    - [x] *Part two done 2026-10-06 in a408ca79:* `tests/test_regex_bounded_time.py` also times every
      literal pattern on runs that start INSIDE it. For each repeat that can hold a
      run (count varies, maximum at least 500), the shortest text in front of it,
      alone and plus one character the repeat accepts, then a run of each fill the
      repeat accepts, then no tail or `x`; derived by `re._parser` from the pattern,
      with every group opened and every alternative laid out. Two new sweeps (3,248
      inputs over 133 package patterns, 2,174 over 67 tooling ones; floors 66 and
      33), one timing round in the screen and the full three to confirm. A proof
      test pins the blind spot both ways (the old `_READ_STALLS` linear to the old
      inputs, quadratic to the new). Besides the cyanrip_log patterns (part one)
      it found nine more; six are fixed, each held to its old form by Hypothesis in
      `tests/test_regex_rewrites_read_the_same.py` and pinned by name:
      `cue_validate._RE_REM`, `_RE_TITLE`, `_RE_PERFORMER` (`.*\S` → `\S(?:.*\S)?`),
      `rip_log._FIELD` (lazy value → `(?:\S(?:.*\S)?)?`),
      `rip_worker._CYANRIP_ETA_VALUE` (the blanks after `m` inside its group), and
      `handshake._SOURCE_NAMED_LAP` (`round-0*\d+-` → `round-\d+-`). Three are
      ledgered in `_LEAD_IN_DEBT`, item (4a). revert_probe: 9 of 9 as expected,
      including reverting `_READ_STALLS` to its lazy form (the lead-in sweep fails;
      the old sweep passes, which is the blind spot, now asserted).
  - (4a) **The lead-in debt** (`tests/test_regex_bounded_time.py::_LEAD_IN_DEBT`, may
    shrink, never grow): three patterns the lead-in sweep finds super-linear and
    that are not fixed. `drive_list._DRIVE_LINE` (the legacy drive list; no caller
    outside tests; 320 ms on 2,000 spaces), `emit_ripper_inventory._ROW` (hand-run
    over the fork's provider-contract rows; cubic, 3.7 s on one 2,000-character
    row), and `round_digest._LAP_NAME` (file names only, NAME_MAX-bounded: 0.3 ms
    at 255). Each needs its own equivalence proof; a fixed one's entry goes stale
    and `test_every_lead_in_debt_entry_still_names_a_real_pattern` asks for it.
  - (5) ~~`lint` (`ruff check`, `ruff format --check`) still reads `src tests` only.
    `scripts/` and `build/` were clean under both on 2026-10-05 (0 findings, 51 files
    formatted), so adding them is a CI and `scripts/check.py` change with no fixes.~~
    - *Done 2026-10-05 (this commit), C3 lifted for it by KDD-41:* CI and `scripts/check.py`
      lint and format-check `src tests scripts build`, and
      `tests/test_check_script.py::test_the_local_lint_paths_match_ci` holds the two to the
      same paths (two reverts probed, both detected).
  - (6) `tests/` is outside the size ratchet: 139 of its 280 modules are over 300 lines
    (2026-10-05). Whether a test module should be split is its own question.

## Round 25 — the complete known-issue agenda (compiled 2026-09-23)

**Maintainer ruling, 2026-09-23:** *"if round 24 is closed … fix the problem, and if
[it] needs to keep closed how we fix this for the next round … include everything,
the next round needs to fix everything known."* So this is not a wish list. It is the
round's scope, and its close conditions should be chosen from it in lap 1 (S-13).
**Round 25 cannot close on all of it** — 80-odd items would reproduce round 7 — so lap
1 should name the subset that closes the round and move the rest to NEXT-ROUND by name
(S-14). What this section guarantees is that **nothing known is missing** from the
table the fork and we choose from.

**How it was compiled.** Every open `[ ]`/`[~]` row in this file; every NEXT-ROUND
item, question and correction in rounds 22–24 from both sides; `platterpusstatus.md`;
the challenge ledger; the fork's `KNOWN-ISSUES.md` (`KI:`), `handshake/STATUS.md` and round plans
(all under their `docs/`, at `origin/platterpus-fork@c884c4e`); and a field-by-field grep of the
four shared documents. Rows marked *derived* were found by that compilation and were
never recorded before; the four spot-checked (A6, C9, D6, G12) held. Line numbers
`@b8f89a2` are this file at that commit. **Owner**: ours / theirs / both / shared.
**v6**: whether it needs a protocol bump.

### A — Protocol v6 (shared docs; needs the bump)

- [~] **A6. Eight wire fields every current lap carries and no shared doc defines** —
  `INBOUND-OBSERVED`, `NEXT-LAP`, `VERDICT-SOURCE`, `PEER-PIN-SOURCE`,
  `FROM-COMMIT-SOURCE`, `PIN-POLICY`, `BREAKING`, `SHARED-HASHES`/`-SOURCE`: 0
  occurrences each in `handshake-protocol.md`, `seam-rules.md`, `seam-commands.md`
  (re-counted 2026-09-23). *Derived.*
  - *Audit 2026-09-25: partly done.* INBOUND-OBSERVED and FROM-COMMIT-SOURCE are defined in v6. NEXT-LAP, VERDICT-SOURCE, PEER-PIN-SOURCE, PIN-POLICY, BREAKING and SHARED-HASHES are deferred to v7.
  - **Triaged 2026-11-16 (open, joint):** `HANDSHAKE-NEXT-LAP` was defined in v7 (`docs/handshake-protocol.md:212`) and `HANDSHAKE-INBOUND-OBSERVED` made required in v8 (E11). The other five fields are still on the shared deferred list (`docs/handshake-protocol.md:1573-1578`), which v8 and v9 took nothing from; fork list F7 of 2026-10-12.
- [ ] **A10. The evidence-transport proposal** — adopt or formally retire 5b.1–5b.8
  (ours: 5b.2/4/5/6 as written, 5b.1 as an end-state obligation, 5b.3 gating both
  sides); pull transport with `main` as ref of record, practised but unwritten; the
  filename convention as a §5c; the envelope (§4b "exactly once", and whether it is
  needed now that laps travel by git — we still emit one). Cite: fork
  `PROTOCOL-v5-PROPOSAL-evidence-transport.md`; TASKS@b8f89a2:581, 1705–1729.
  - **Triaged 2026-11-16 (open, joint):** still on the shared deferred list (`docs/handshake-protocol.md:1577`). HR-2 (v9 §17) now governs evidence on the `evidence` branch, so what is left is formally retiring 5b.1 to 5b.8 and the envelope (`scripts/emit_envelope.py` still exists); fork list F7.
- [ ] **A11. `HANDSHAKE-CONCURRENT-WITH`** — proposed round 7 laps 32–33, never built;
  adopt or retire (K1 may subsume it). TASKS@b8f89a2:2928.
  - **Triaged 2026-11-16 (open, joint):** still deferred and never built (`docs/handshake-protocol.md:1577`); retiring it jointly is the fork list's F4 of 2026-10-12, not yet done.
- [ ] **A12. A `SEAM-COMMANDS: audited @ N` close field** — prototyped, reverted for
  want of the shared file; the round-8 bump never happened. TASKS@b8f89a2:3734.
  - *Merged 2026-09-30, verbatim, from the duplicate row "Propose the protocol version bump in round 8" (P0, 2026-08-06) (it was `[ ]`):* **Propose the protocol version bump in round 8**, with the four-row table above as the specified behavior, and land the gate change **in the round where both sides adopt it** — not before.
  - **Triaged 2026-11-16 (open, joint):** still deferred (`docs/handshake-protocol.md:1578`); fork list F7.
- [ ] **A13. A semantic-change marker** — a derived contract diff cannot see a change
  of meaning (round 21's `Ripping errors:` recount changed no format string); pairs with
  defining `BREAKING`. KI:1364.
  - **Triaged 2026-11-16 (open, joint):** still deferred beside a definition of `HANDSHAKE-BREAKING` (`docs/handshake-protocol.md:1578`); fork list F7.

### B — Shared-doc defects that bump only that doc's own version

- [ ] **B3. `seam-commands.md` — five known-wrong statements**: §7's summary (48 of 68
  "accepted" rows never observed to take effect); line 504 `-p '99=drop'` published as
  accepted, refused by the binary; line 97 `-D` is `folder_scheme`, not an output dir;
  §1's provenance warning (0 of 17 rows are `?`); §4 NEED 4 vs §1's `-a` row (our
  `_COLON_SUBSTITUTE` is safety-net only). Plus stale §6. Needs their D5 first. KI:763.
  - **Triaged 2026-11-16 (stale but open):** the five statements are fixed (`docs/seam-commands.md:98` names `-D` `folder_scheme`, `:578` shows `-p '99=drop'` refused, §4 NEED 4 is answered). Still stale in the shared file: §6 *What we owe next* (`:331-339`) describes the round-8 outbound, and §7's exit-code grading (`:622-632`) says every refusal exits `1` while the generated table above it shows `64`. Fits R127's housekeeping.
- [ ] **B4. (Optional) name one shape as a seam rule** — *"a key whose lifetime does not
  change when the thing it suppresses does"*, four instances in round 22; offered as a
  round-23 item, never raised. Our r22 lap 4 §H.
  - **Triaged 2026-11-16 (open, ours, optional):** never raised with the fork; the shape lives on our side as the §5.aq question in `CLAUDE.md` (*What else WRITES to the field I'm reading*).

### C — Our gate and tooling

- [ ] **C10. The challenge ledger stops at round 21 lap 4** — unrecorded: r22 C1 (our
  circular `GO`, they were right), r22 lap 5 (our withdrawn `handshake_round` claim),
  r22 lap 3 §H1, r23 §A (tracks 3 and 5, we were right), r23 lap 1 §H6, r24 §B3 (the
  §5b reading, we were right). `docs/cyanrip-handshake.md` §9. *Derived.*
  - **Triaged 2026-11-16 (open, ours):** still missing. The ledger (`docs/cyanrip-handshake.md` §9) goes from row 19 (round 21) to row 20 (round 26 lap 4) and ends at row 22 (round 29), so rounds 22 to 24 and 30 to 40 are unrecorded.
- [~] **C11. Handshake-gate test quality** — the vacuity and rule rows at
  TASKS@b8f89a2:1882, 1883, 1895, 1913, 1923, 1951; and the weekly mutation sweep omits
  `handshake_approval.py`, `deps/fork_source.py`, `ripper_identity.py`,
  `adapters/cyanrip_backend.py`, `rig_check.py` (:1970–1980).
  - *Audit 2026-09-30: partly done.* `.github/workflows/mutation.yml` now has legs for
    `handshake_approval.py`, `ripper_identity.py`, `adapters/cyanrip_backend.py` and
    `rig_check.py`; `deps/fork_source.py` still has none. The vacuity and rule rows were
    not re-checked here.
  - **Triaged 2026-11-16 (open, ours):** `deps/fork_source.py` still has no leg (`.github/workflows/mutation.yml:80-145` lists 15 targets), and the vacuity rows it names are still open below.
- [ ] **C12. Two meta-sweeps never run** — "a check that agrees for the wrong reason",
  and status questions #5 (a bound reached every run) and #8 (right direction, wrong
  magnitude). TASKS@b8f89a2:1429.
  - **Triaged 2026-11-16 (open, ours):** no such sweep in `tests/`; unchanged.

### D — Their gate and tooling (theirs; listed so nothing is lost)

- [ ] **D9. Their tools hygiene (low)** — `tools/mutate.py` `EXCLUDED_TESTS` premise
  (KI:97); "lap commit list names its range" timeout (KI:244); flaky "interrupted sample
  freshness" (KI:153).
  - *Audit 2026-09-25: not ours to verify.* The fork's; still open.
  - **Triaged 2026-11-16 (open, fork):** the `EXCLUDED_TESTS` premise is now derived and named (`cyanrip@6b5b9dc7:docs/KNOWN-ISSUES.md:60-69`); the *lap commit list names its range* timeout is still open there (`:487`); no freshness entry was found in that file.

### E — Contract, argv and log surface

- [ ] **E2. `File(s):` lists what was requested, not what was written.** Theirs. KI:1213.
  - *Audit 2026-09-25: not ours to verify.* The fork's; their KNOWN-ISSUES says STILL OPEN.
  - **Triaged 2026-11-16 (open, fork):** still marked STILL OPEN at `cyanrip@6b5b9dc7:docs/KNOWN-ISSUES.md:1259`. `.27` added a `not written whole: <path>` footer line under a failing `Encoder errors:`, but `File(s):` stays the request; fork list F8.
- [ ] **E5.** ~~**The `-j` diagnostics record goes nowhere** — lands in the rips root, nothing
  reads it, the auto-bundle does not collect it;~~ and **`Encoder errors:` has no `-j`
  field in P8 at `3e01bb3`** (*derived*), leaving half of TASKS@b8f89a2:805 open. Both.
  - *2026-09-30:* the struck `-j` half is merged into **Embed the `-j` record in
    `.platterpus.json`**, where its stale clause is corrected (`09636001` collects the
    record into each rip's bundle). The `Encoder errors:` half stays open here.
  - **Triaged 2026-11-16 (stale but open, ours now):** the fork's record carries a per-track `encode_failures` (`cyanrip@6b5b9dc7:src/diagnostics.c:647`) and nothing in `src/` reads it, so this half belongs beside *Embed the `-j` record in `.platterpus.json`*.
- [~] **E11. The inbound half of the seam is unguarded** — no return-path sanitiser; 13
  `QLabel(<non-literal>)` sites outside the PlainText sweep; no test that what reaches
  the user is what cyanrip said. TASKS@b8f89a2:3818–3821.
  - *2026-09-25:* **Sanitiser done** (`inbound_text`, and `errors="replace"` on every text-mode read). ~~The 13 `QLabel(<non-literal>)` sites are still unswept.~~
  - *Audit 2026-09-30:* the `QLabel(<non-literal>)` sites are swept: `98b3a8c3` added
    `tests/test_labels_state_their_text_format.py` (it found 17, not 13). **Still open:**
    labels given their value later by `setText(...)`, which that sweep does not cover, and
    a two-way test that what reaches the user is what cyanrip said.
  - *2026-10-05:* the `setText(...)` half is done in adc04a08
    (`tests/test_labels_given_text_later_state_their_format.py`; 14 labels pinned, see
    the row *"Labels given their text by `setText` after they are built"*). **Still
    open:** a two-way test that what reaches the user is what cyanrip said.
  - **Triaged 2026-11-16 (open, ours):** the two-way test that what reaches the user is what cyanrip said is still absent from `tests/`.
- [ ] **E13. `seam-commands` structural work** — rows for all 41 flags, generated types
  and ranges, string/path probes, reasons for the `-I`/`-J` and `-F` exclusions,
  NEED 1–3 / WANT 1–3. TASKS@b8f89a2:3704–3709, 3766.
  - *Merged 2026-09-30, verbatim, from the duplicate row "Rows for all 41 of their flags" (P0, 2026-08-06) (it was `[ ]`):* **Rows for all 41 of their flags, not our 17.** For every flag we do not send, the row must say `NO: <reason>` or `?`. Today nothing distinguishes *"we decline it"* from *"we never noticed it"* — and those are different facts about the same blank cell.
  - *Merged 2026-09-30, verbatim, from the duplicate row "Extend the emitter to carry types + ranges" (P0, 2026-08-06) (it was `[~]`):* **Extend the emitter to carry types + ranges; build the merge; add the both-sides-audited gate; propose the shared file in the round-8 outbound alongside `docs/seam-rules.md`.**
    - *Audit 2026-09-25: partly done.* docs/seam-commands.md is byte-identical in both repos, but the emitter carries no types, and there is no merge tool or audited gate.
  - **Triaged 2026-11-16 (stale but open):** rows for every flag landed in round 35 (`docs/seam-commands.md` §1b, `:118-127`, held by the fork's `probe-argv-surface.py --check`). Still open: the emitter does not generate the type and range columns, there is no merge or both-sides-audited gate, and `-F` and `-I` still say *needs confirming* (`:109-110`) although §7 records the `-I -J` refusal (`:604`).
- [ ] **E14. Fork lines we do not consume** — the progress line's `, errors - %i`;
  `Cache model:`; per-track paranoia counts in the read-effort flag; `Duration:` vs
  `Samples:` (T14(c)). TASKS@b8f89a2:4483, 4479, 4461, 4502, 4371.
  - **Triaged 2026-11-16 (open, ours):** none of the four is consumed yet; each keeps its own open row below (*T14(c)*, *per-track paranoia counts*, *`Cache model:`*, *`, errors - %i`*).
- [~] **E15. A cancelled-rip log addendum (J2) and the tag-casing ruling (J7).**
  - *2026-09-25:* **Decided:** D13 A (a cancelled rip's kept tracks and their checksums go in the JSON report only; cyanrip's log is untouched and no sidecar is written; ready to build) and D2 B (the fork writes every tag key in capitals, plus both `DISCTOTAL` and `TOTALDISCS`; asked in our next lap).
  - *Audit 2026-09-30: the tag-casing half landed in round 29.* The fork's tag change
    (`bf50705`) writes every key in capitals plus both `DISCTOTAL` and `TOTALDISCS`, our
    operator accepted the key set as landed (round 29's S8 row), and it ships in `.19`
    (round 30 lap 1's `HANDSHAKE-BREAKING`). The D13 A half (a cancelled rip's kept
    tracks in the JSON report) is not built.
  - **Triaged 2026-11-16 (undecided):** could not settle whether D13 A is already met: a report is written for a cancelled rip whenever its log parses (`ui/main_window_rip.py:2221`, success or not), but no code names a cancelled rip's kept tracks. Needs a filed cancelled-rip report read against D13 A.
- [x] **E16. AccurateRip skip discrimination** (round 8 J13) — ours to answer; the
  track-3 CRC puzzle is related. KI:1388.
  - *Done 2026-10-12, found already answered*: our round 28 lap 6 S7 (`docs/handshake/outbound/round-28-lap-06.md`) says we compute no AccurateRip checksum and read theirs from the log. Their `KNOWN-ISSUES` still calls it open; that is in the fork list of the 2026-10-12 ranking.
- [x] **E17. Does cyanrip emit `Accurip` lines under `-l`?** — gates the AR-carryover
  finding; derive from their source. TASKS@b8f89a2:4523.
  - *Closed 2026-09-27, answered from hardware:* yes. The maintainer's subset rip under `-l` (`Tracks to rip: 3, 4, …, 16`) carried `Accurip:` and all three local CRCs per track (`docs/cyanrip-fork.md` Part C §3.3). A drive log is stronger evidence than a reading of their source, so no source derivation is owed.
- [ ] **E18. Long-standing optional asks** — a severity column on the message inventory
  (:1842); the C2-pointers row (:4674); their H3 sanitiser question (:2966); `-f` in the
  wizard (:3545); upstream PR asks (:3918–3921); their eight unfiled upstream defect
  reports; the cache-probe calibration (KI:516).
  - *Merged 2026-09-30, verbatim, from the duplicate row "Answer the fork's H3 question" (it was `[ ]`):* **Answer the fork's H3 question about a Platterpus-side sanitiser blind spot.** They
    found ASAN and UBSAN both blind to their argv overread. Our nearest equivalent of that false
    comfort is *"the parsers have a `hypothesis` never-raises property test, so malformed input is
    covered"* — which proves survival, not correctness of the value returned. Worth a real audit
    rather than the one example we volunteered.
  - **Triaged 2026-11-16 (stale but open):** the cache-probe calibration is fixed for `.20` (`cyanrip@6b5b9dc7:docs/KNOWN-ISSUES.md:735`); C2 pointers as evidence is in R125; `-f` in the wizard is R150. The H3 sanitiser audit and the fork's unfiled upstream reports remain.

### F — Pin, approval and release ordering

- [ ] **F3. `a_round_is_reviewing_a_build()` answers from pin coincidence, not from the
  round record** — after our roll it returns False while round 24 is still OPEN on their
  gate (round 21 showed the same fault). One predicate derived from the record.
  - **Triaged 2026-11-16 (open, ours):** unchanged: `deps/fork_source.py:2260-2276` still answers `not same_commit(PIN_UNDER_REVIEW, FORK_PIN)`.
- [ ] **F5. The approval's app half is never the build that carries the roll** (0.6.53
  approves; 0.6.54 ships). By design, but the stale-claim guard re-arms on every bump;
  make the provenance chain a structure. TASKS@b8f89a2:2055.
  - *Merged 2026-09-30, verbatim, from the duplicate row "handshake_approval.py's provenance chain wants to be a structure" (it was `[ ]`):* **`handshake_approval.py`'s provenance chain wants to be a structure, not
    consecutive comment blocks.** It has grown by ~8 lines on each of the last three
    round closes (547 → 563 → 571) and will do so again every round, because what it
    stores is a *table* — `(round, pin, app version, why)` — written as prose. The
    module is ~40% provenance by line count. Making it iterable would let the tests
    assert the chain rather than the endpoint, and would let a rip report cite the
    round that approved its pin without a constant per round. **Deliberately not
    done during a round close** — the constants are load-bearing at exactly the
    moment a round closes — so this is queued for a quiet commit between rounds.
    Promoted from a comment in `tests/test_critical_rules_are_enforced.py` after the
    same note was written three times.
  - **Triaged 2026-11-16 (open, ours):** still prose: `handshake_approval.py` is 865 lines, and the chain is constants (`APPROVED_BY_ROUND` at `:390`).
- [~] **F6. The ripper install surface** — the wizard silently rebuilds the production pin
  over a test pin (:2669); verify the binary before installing (:2795);
  `--install-ripper` prints its shell scripts (:2810); `latest`/`latest-beta` (:2857);
  `target_for_commit` version lookup (:917); the launch-time notice gap (:812).
  - *Audit 2026-09-25: partly done.* The wizard/offer over the build under review was fixed in c36efa4 (is_the_build_under_review). Binary verification, script printing, latest/latest-beta, target_for_commit and the notice gap are not evidenced.
  - *Merged 2026-09-30, verbatim, from the duplicate row "The setup wizard silently rebuilds the production pin" (round 8) (it was `[~]`):* **The setup wizard silently rebuilds the production pin over a test pin.**
    Found while answering the fork's J10 (*"what reverts our binary?"*) from source
    rather than from memory: nothing reverts it at launch, and the only code running
    `git checkout --force --detach <pin>` is the setup wizard and `--install-ripper`,
    both explicit. But the wizard builds `WIZARD_TARGET` (= `PRODUCTION_TARGET`), so
    an operator running a test pin who opens the wizard for any other reason —
    a missing encoder, a drive question — gets it **downgraded with no warning**,
    which is exactly the shape of every revert in their reflog landing on `ddf7ac3`.
    The wizard should say *"this will replace cyanrip <test pin> with <production
    pin>"* and let the operator decline. Deliberately **not** fixed mid-round
    (S-14: a real defect that does not break the artifact under review).
    - *Audit 2026-09-25: partly done.* c36efa4: the default target keeps the build under review. Other installed test builds are still replaced with no "will replace X with Y" prompt.
  - *Merged 2026-09-30, verbatim, from the duplicate row "The launch-time notice gap" (round 16) (it was `[ ]`):* **The launch-time notice gap.** The app knew the wrong cyanrip build was
        installed and said nothing: the deferred automatic ripper check is a bare
        `return` with no retry, so a condition that refuses at arming time is never
        re-asked. Same shape as the *"did I check the preconditions where the thing
        HAPPENS"* rule — make the guards a named function that reports **which** one
        refused, and call it at every point that can interrupt.
  - **Triaged 2026-11-16 (open, ours):** `latest` and `latest-beta` exist (`app.py:908`), and the launch check's guards return a named reason (`ui/main_window_update.py:232-266`, R96). Still missing: a *will replace X with Y* prompt, a check of the binary before install, and a retry for a check skipped during a rip (it waits for the next launch).
- [~] **F8. Their two channel questions** — "should a beta expire?" (asked of us, never
  answered) and `release/*` markers (planned, relates to A5). Fork `CLAUDE.md:2076-2104`.
  - *2026-09-25:* **Decided (D15 B):** a beta stops being offered when its round closes or a newer beta appears. The answer goes to the fork in our next lap. The `release/*` half stays open.
  - *Audit 2026-09-30:* the D15 answer was sent, in our round 28 lap 6 S34. The `release/*` half is still open.
  - **Triaged 2026-11-16 (open, fork):** the `release/*` half is theirs (fork list F8 of 2026-10-12); not re-read in their tree for this triage.

### G — Evidence, rig and acceptance the seam depends on

- [ ] **G7. Two verification-leg gaps** — the dependency dialog is screenshotted, never
  asserted; an absent checker graded `ran` is untested (r23 lap 1 §H2/§H3).
  - *2026-10-21:* the second half is done: an absent `flac` now grades the gate
    `not run — <reason>`, tested through the real runner
    (`tests/test_verification_gates.py`). The dependency-dialog half stays open.
  - **Triaged 2026-11-16 (open, ours):** the dependency dialog is still screenshotted only (`rig_scripts/fullacceptance.txt:497-498`).
- [ ] **G9. Rig hygiene** — an unattended run blocks on its first fatal dialog (:2397);
  ~~the rig is left on `max_retries 3` and beta (:230);~~ exact-match script paths (:2681);
  ~~rewrite `hardware-test-checklist.md` (:126, 2358);~~ the colon safety net on
  hardware (:2325).
  - *2026-09-30:* the `max_retries`/beta item is closed, superseded (the app restores the
    user's settings when an acceptance session ends; its row is `[x]`). The checklist
    rewrite is a duplicate of **Rewrite `hardware-test-checklist.md` rather than
    patch it again**, merged 2026-09-30.
  - *Merged 2026-09-30, verbatim, from the duplicate row "A filesystem path inside a script is still an exact-match string" (round 8) (it was `[ ]`):* **A filesystem path inside a script is still an exact-match string.** Fixed
    for `--run-script` itself (`uiscript/find_script.py` matches names with case and
    ASCII separators removed), and *not* for paths the script hands to a tool. C6 of
    the round-8 joint script named the EAC log as
    `…Every Breath You Take-The Classics.log`; the file on disk is
    `…Every Breath You Take- The Classics.log`. One space. `--verify-log` would have
    exited non-zero because the file could not be **opened**, and `expect-exit 1`
    would have **passed** — on the one test whose entire purpose is telling that
    apart from "the log was refused". Satisfied by the wrong thing, again, and it
    survived because the path was checked by eye rather than against the filesystem.
    The fix is a glob or a normalising resolve for `takes_paths` arguments, plus a
    parse-time warning when a literal path does not exist. **Not done mid-round
    (S-14):** the corrected literal works and does not make the reviewed pin unsafe.
    Found 2026-08-13 by asking the operator to `ls` the path before the run — which
    is the cheap check that should have existed the first time the path was written.
  - **Triaged 2026-11-16 (open, ours):** `takes_paths` arguments get only `~` expanded (`uiscript/script.py:211-216`), with no normalising resolve and no warning for a missing path. The fatal-dialog block and the colon check on hardware were not re-checked.
- [ ] **G10. Our never-exercised list is stale** — the fork retired the diagnosed abort and
  a non-zero `Read stalls:` (KI:829-848); still open: `-x` correctness (wrong in all ten
  sessions), C2 (unreachable here), `-f` at another offset, damaged media, physical
  CD-TEXT, the forced-error corpus, H9, H10.
  - *Merged 2026-09-30, verbatim, from the duplicate row "The never-exercised list, which is joint with the fork" (what v1.0.0 needs) (it was `[ ]`):* **The never-exercised list, which is joint with the fork and has not moved
    in four rounds:** `-x` on a real drive, C2 error reporting, `-f`, damaged media,
    CD-TEXT from a physical disc, a diagnosed abort, a non-zero `Read stalls:`.
    Nobody on either project has touched any of them, on any build.
    - *Audit 2026-09-25: not ours to verify.* Hardware, joint with the fork (-x is blocked on the BDR-209D).
  - *Merged 2026-09-30, verbatim, from the duplicate row "Run the rig session: H9, H10, H12, T9, T12, T13" (round 7) (it was `[ ]`):* **Run the rig session: H9, H10, H12, T9, T12, T13.** Capture **stdout for every
        invocation** — seven of the ripper's refusal paths fire before its logfile exists,
        so nothing in the archived log can show them, and its heartbeat lines are
        stdout-only too. Send the artifacts to **both** repositories. Their lap 8 adds one
        cheap step worth taking: run `-x` on a rip you can afford to lose first, since it
        is the least-exercised code in the binary.
    - *Audit 2026-09-25: not ours to verify.* The maintainer's hardware run; H9 open and H10 blocked (the BDR-209D rejects -O).
    - *Reconciled 2026-09-30 with the v0.6.4 plan's blocker 1, which is `[x]`:* that
      tick means superseded as a v0.6.4 blocker, not run in full. The session did run
      on 2026-08-04 (`c5fb909`), and its results table
      (`platterpus@4b793199:docs/handshake/artifacts-round-07/rig-session-results-c5fb909.md`) records H10/`-O`,
      the `-x` probe, `-j` and the mid-rip cancel as NOT RUN; what is still owed is
      listed in this row.
  - *Merged 2026-09-30, verbatim, from the duplicate row "Send the A7/G2/H12 forced-error corpus" (round 7) (it was `[ ]`):* **Send the A7/G2/H12 forced-error corpus.** Hardware-gated and deliberately not
        hand-assembled: a corpus built from my reading of their control flow is a fixture
        carrying my assumptions about their control flow. **Now runnable without re-derivation:
        `hardware-test-checklist.md` §F3** gives the five states as five one-line commands
        with exactly what to record for each. Case 1 needs no disc and nothing is written.
  - **Triaged 2026-11-16 (hardware, joint):** partly carried elsewhere: the bounded `-O` read is R24's `overreadprobe`, the C2 and accurate-stream declarations R152, `-f` R150; a damaged disc was read once (*Roots Music* disc 1, 2026-10-21, R49). `-x` correctness, physical CD-TEXT and the forced-error corpus remain.
- [ ] **G11. Version-gate evidence** — zero full-green rows; a second drive, machine and
  distro missing. `docs/testing.md` §5B.
  - *Audit 2026-09-25: not ours to verify.* Needs hardware runs and the maintainer: every ledger row so far is partial, none full-green.
  - *2026-10-12:* the premise is out of date. The ledger has two `full-green` rows (2026-10-07 on 0.6.66, 2026-10-12 on 0.7.103), both on the BDR-209D on Bazzite with the maintainer.
  - *2026-10-13:* a third `full-green` row (0.7.104 with `.22`), on the same rig, so nothing changes for 0.8.1. What 0.9.1 still needs: a second machine and distro, and E2 on a drive the AccurateRip list does not carry.
  - *2026-10-19:* a fourth `full-green` row (2026-10-16, 0.7.106 with `.23`), on the same rig again; the 2026-10-14 run is `partial`. 0.8.1 still needs a `full-green` row from a second machine and distro (`docs/testing.md` §5B, whose table is the authority).
  - *Merged 2026-09-30, verbatim, from the duplicate row "Run fullacceptance.txt overnight" (round 14) (it was `[~]`):* **Run `fullacceptance.txt` overnight** — now **0.6.30** against `d9c058c`.
    No longer a round-14 close condition (the round closed on T1); it is the
    **0.7.100 gate** run: zero failures in the ARCHIVAL sections, UX failures
    recorded and non-blocking (`docs/testing.md` → *Acceptance severity*). The
    2026-08-27 attempt aborted correctly in two seconds on a wrong-ripper
    precondition — see the round-state fix below.
    - *Audit 2026-09-25: not ours to verify.* The maintainer's hardware run. The 0.6.30 pairing is stale; the ledger has only `partial` rows, so the 0.7.100 gate run is still owed.
  - *Merged 2026-09-30, verbatim, from the duplicate row "More than one drive" (what v1.0.0 needs) (it was `[ ]`):* **More than one drive.** Every hardware result this project has is from one
    Pioneer BDR-209D 1.51 at offset +667. A read-offset bug, a speed-lock quirk or
    a cache behavior that is drive-specific is invisible in a sample of one, and
    the offset path is the single most correctness-critical thing we do.
    - *Audit 2026-09-25: not ours to verify.* Hardware coverage: every ledger row is the BDR-209D.
  - *Merged 2026-09-30, verbatim, from the duplicate row "More than one machine" (what v1.0.0 needs) (it was `[ ]`):* **More than one machine.** Bazzite + KDE Plasma 6 is the primary target and
    the only one anyone has run. Fedora/Arch/Ubuntu are claimed in the README and
    unverified by a person.
    - *Audit 2026-09-25: not ours to verify.* Hardware coverage: every ledger row is one machine (Bazzite).
  - **Triaged 2026-11-16 (hardware, owner):** eight `full-green` rows now (`docs/testing.md:4118-4131`), every one the maintainer's BDR-209D on Bazzite; 0.8.1 still needs a second machine and distro.
- [~] **G12. The leaving-beta objective has dropped out of our laps** — the rule says it
  *"must appear in every lap we write"*; round 20–24 outbound laps mention it once
  (round 23 lap 4). *Derived; rule text re-read 2026-09-23.* Carry it in our round-25 lap.
  - *2026-09-27:* `scripts/handshake.py` `LEAVING_BETA_WORDS` / `LEAVING_BETA_OBJECTIVE`,
    stated in `--emit`'s skeleton under *The objective*, and checked word for word against
    `docs/handshake/verified/round-08-lap-10.md` §A by
    `tests/test_handshake_tooling.py::test_the_skeleton_states_the_maintainers_objective_in_their_words`
    (revert-probed 2 of 2). ~~Our round 28 lap 5 carries it. Closes when that lap is released.~~
  - *Corrected 2026-09-30:* it was our round 28 **lap 6** (S38) that carried it; lap 5 is
    the fork's. And the objective has appeared in none of our laps since: round 28 laps 7
    and 9, round 29 laps 2 and 4 and round 30 lap 2 do not state it, so the skeleton's
    text is not reaching the released laps. Still open.
  - **Triaged 2026-11-16 (open, ours):** still not reaching laps: the newest outbound lap that states it is round 35 lap 14; none of our round 38 to 40 laps does (grep of `docs/handshake/outbound/`).
- [ ] **G13. The audit we owe ourselves** — *"a file you declined to file is a file you
  will reason about without opening"*; we said we had not audited our side. r23 lap 4 §A.
  - **Triaged 2026-11-16 (open, ours):** no record of the audit since; unchanged.

## 2026-09-22 pre-round-24 document audit — what it found that a doc edit cannot fix

The audit's doc corrections landed in one change (see `CHANGELOG.md`). These four
did not, because they are code or need a judgement, and the first two are the
most important thing on this page before round 24's lap 1 arrives.

- [~] **Sixteen binding conformance rows have never had a named test: C21–C36.**
  Found while bumping to v5. `test_every_conformance_row_has_a_test_here`
  exempted every row after the v3 heading **unconditionally**, against §8's own
  instruction that *"bumping `PROTOCOL_VERSION` turns them on with no second
  edit"* — so when both gates reached 4 in round 9, the v3/v4 rows stayed exempt
  for thirteen rounds. The split now follows `PROTOCOL_VERSION`, C37–C42 have
  tests, and C21–C36 are counted in `_BINDING_ROWS_WITHOUT_A_NAMED_TEST` (may
  only shrink). Some behaviors are covered under other names (the digest,
  overrides, the lap limit); the work is one `test_C<nn>_…` per row, and any row
  whose test fails is a divergence to report, not to fix quietly.
  - *Audit 2026-09-25: partly done.* C23/C24 got test_C23_/test_C24_ on 2026-09-25 (f93bd59). The other 14 rows (C21, C22, C25–C36) are still counted in _BINDING_ROWS_WITHOUT_A_NAMED_TEST.
  - *Merged 2026-09-30, verbatim, from the duplicate row "14 of 37 shared-protocol conformance rows have no test" (round 18) (it was `[~]`):* **14 of 37 shared-protocol conformance rows have no test — C21–C30 and
        C33–C36, contiguous — and the file
        claiming "one test per row" was written when the table had 14.**
        `tests/test_handshake_conformance.py`'s docstring says *"`PROTOCOL.md` §8 is
        a 14-row table… one test per row, in the table's order"*. The jointly-owned
        table now defines **C1–C36 plus C13a — 37 rows**; nine are named by a test
        here, and three of those only inside an assertion message, so nine is an
        upper bound. **The fork found the miscount in their round-18 lap 3 §4a, one
        day after this row was written**: our id pattern was `C\d+`, which cannot
        match `C13a` — and a row the denominator cannot include can never be
        reported as uncovered, so the check would have printed full coverage while
        one row had none. Their own counter has the identical blind spot
        (`\bC[0-9]+\b`); same defect, both projects, independently. Fixed here by
        widening to `C\d+[a-z]?` and pinning `C13a` by id. The
        table grew 2.5× and the completeness claim did not — `CLAUDE.md`'s
        *a map is only ever wrong by omission*, in the file whose job is proving we
        conform to a spec neither project owns alone.
        **The cyanrip fork found the symptom before we found the disease.** Their
        round-18 status ran their own checks against our public tree and reported
        `HANDSHAKE-OVERRIDE` in `docs/handshake-protocol.md` and **zero** `.py`
        files. Verified: 0 references in any `.py`, `scripts/handshake.py` included.
        So **C31** (refuse an override missing `-BY`/`-WHY`) and **C32** (honour it,
        and print it whenever the round's state is printed) are unimplemented. C32 is
        the one that bites — an override our gate cannot see is, in that row's own
        words, indistinguishable from the rule never existing. With their gate
        honouring overrides and ours ignoring them, an operator override makes the
        two gates reach **opposite conclusions about whether a round can close**.
        *Counted, not fixed:* `test_the_conformance_table_has_not_outgrown_this_file_any_further`
        derives the row set from the protocol, floors it at 30, and ratchets coverage
        so it cannot shrink. Full coverage is not asserted because that fails today
        and a red suite is not a record.
        *Do first:* C31 and C32 — they are the two a peer is already relying on.
    - *Audit 2026-09-25: partly done.* C31/C32 are implemented for §6b overrides (release_overrides), but only on --release-gate, so --status does not print overrides. 14 rows still have no named test.
  - *Merged 2026-09-30, verbatim, from the duplicate row "We claim 'one test per conformance row'" (round 15) (it was `[~]`):* **We claim "one test per conformance row" and it is not true: 37 rows, 24
    tests.** Measured 2026-08-27: `docs/handshake-protocol.md` §8 carries `C1`–`C36`
    plus `C13a` (37 rows); `tests/test_handshake_conformance.py` defines 24
    `test_C*` functions. `docs/cyanrip-handshake.md` said *"one test per §8 row"* and
    `docs/README.md` said *"20-row … one test per ID, with the ID set derived from the
    file"* — both were written when the table had 20 rows and neither noticed it grow.
    Both sentences are now softened to point at the table, which stops the claim being
    false but does **not** close the gap. Two things needed, in order: **(1)** fix the
    ID-derivation regex to `(C\d+[a-z]?)` so `C13a` is visible at all — a derived set
    that silently skips a row is the "satisfied by finding nothing" shape in the file
    that exists to prevent it; **(2)** write the 13 missing tests, or record per
    missing row why it is untestable here. Do not re-assert "one test per row" until
    the numbers agree.
    - *Audit 2026-09-25: partly done.* The row-id regex is fixed (_ROW_ID `C\d+[a-z]?`). 14 binding rows still have no named test, counted by _BINDING_ROWS_WITHOUT_A_NAMED_TEST.
  - **Triaged 2026-11-16 (open, ours):** still 14 rows (`tests/test_handshake_conformance.py:1800-1802`).

- [x] **ANSWERED in their round 24 lap 1 §B3: they read it literally, agree ours is the reading under which §5b works, keep the literal one until v6, and propose v6 text** (step 1 and C37: *held, and enumerated by the gate when it decides*). Carried to round 25. Original:
- [x] ~~**Ask the fork, in round 24: does their gate read §5b's "enumerated" the way
  ours does?**~~ We derived it rather than chose it: C40 allows a candidate *newer*
  than the transcription's source, and the source is the newest peer lap the
  writer held, so that candidate cannot be in the writer's own `INBOUND-HELD`.
  Our gate therefore enumerates at decision time (`resolve_peer_verdict`). If
  theirs reads it as the closing lap's field, the two gates would disagree about
  exactly the close v5 exists to allow.

- [x] **Say it in our first round-24 lap: a Platterpus pre-release counts for the
  round-22 ordering.** Answered to the fork by hand on 2026-09-22; it belongs in the
  record as a stated term. Every `v0.*` tag carries GitHub's pre-release flag
  (`release.yml:343`), our updater deliberately ignores that flag and offers
  0.6.53 on the stable channel (`update_check.py:99-117`), round 20 already set the
  precedent (the `Retry limit:` arm first shipped in v0.6.50, also flagged), and the
  both-wordings parser first ships in **v0.6.53** — no earlier tag carries the
  `read successfully!` arm. So our half of the ordering is met and `+platterpus.14`
  is theirs to ship; our `FORK_PIN` stays `2cce60d` until a round reviews `.14`.
  - *Audit 2026-09-25: done.* Said in docs/handshake/outbound/round-24-lap-02.md ("a Platterpus pre-release counts"), released 2026-09-23.

- [~] **Rewrite `hardware-test-checklist.md` rather than patch it again.** Its
- [~] **Rewrite `docs/hardware-test-checklist.md` rather than patch it again.** Its
  intro is the v0.6.0 sheet's ("v0.6.0 (this sheet)", releases listed to v0.5.21);
  the audit added a dated banner and corrected the tools row, but deciding which
  §A–§D cases the acceptance run has absorbed is a per-case call against hardware
  results.
  - *Merged 2026-09-30, verbatim, from the duplicate row "hardware-test-checklist.md is titled v0.6.0" (doc drift, 2026-08-20) (it was `[~]`):* **`hardware-test-checklist.md` is titled "v0.6.0" and stamped "v0.6.19".**
    Both facts are true and together they are the failure `CLAUDE.md` names exactly: *a
    stamp records when a doc was edited, and a doc nobody rewrites keeps an accurate
    stamp while its prose quietly expires.* Its narrative still opens on the v0.6.0
    one-file-upload change and "four releases since your last completed run", which is
    now nineteen minors stale. The stamp gate cannot see this, and neither can the
    version-claims gate — they check the footer and the CHANGELOG, not whether the
    document still describes the release it is for.
    **Deliberately not rewritten inside this release**: it is a ~700-line run sheet and
    the release window is the wrong place for it. It is also partly superseded — the
    *reference* half now lives in `docs/test-plan.md` Part E, so the rewrite should
    reduce this sheet to the fillable per-release instance Part E describes rather than
    restate it. Do that before the next hardware pass, and consider whether the
    promise-of-completeness sweep (§5.af) can be extended to catch a title/stamp
    mismatch mechanically — the check that would have caught this is "does the version
    in the H1 match the version in the footer", which is two lines of test.
    - *Audit 2026-09-25: partly done.* H1 no longer says v0.6.0 and a current note was added (9986868). The rewrite to a per-release sheet is not done, and there is no H1/footer check.
  - **Triaged 2026-11-16 (open, ours):** not rewritten; `hardware-test-checklist.md:3-16` still carries the v0.6.0 intro under a banner saying a rewrite is due.
  - *2026-11-16, moved, not rewritten:* the file is folded into `docs/test-plan.md` → *Hardware test checklist* (Critical rule #7, one home), unchanged but for heading levels, cross-references and two statements that document already made (the CRC baseline is Part B's table; the no-audio rule is §0's). The former `hardware-test-checklist.md` path in this row and in the rows that cite it means that section. The rewrite this row asks for is still open and now applies to the section.

## 2026-09-21 UX audit — the post-update prompt chain, and the menu (real-user report)

*Maintainer, after updating: "when i went to check for updates it kept asking me,
repeatedy or this that or the other, and other dependanciessn, other
applications, other whatever, this was too much. also audit the menu and what is
needed. can they be in sub menues? are some thing not needed or can be put into
other things. we dont need 20 menues when 5 will do."*

### The prompt chain — MEASURED, not estimated

One update-and-relaunch can present **five sequential modals**, each its own
decision, with no shared OK:

| # | Prompt | Where |
|---|---|---|
| 1 | *"Update available … Update now?"* | `main_window_update.py:778` |
| 2 | *"Update installed. Restart Platterpus now?"* | `main_window_update.py:943` |
| 3 | *"Add Platterpus to your applications menu?"* | `main_window_provision.py:161` |
| 4 | *"Set up Platterpus…"* (dependencies) | `main_window_provision.py:163` |
| 5 | *"Set up drive…"* | `main_window_provision.py:165` |

…plus **6.** the cyanrip-build offer, armed separately on a timer
(`main_window.py:759`, `_maybe_check_ripper_updates`).

3, 4 and 5 are called **one after another inside
`_maybe_offer_first_run_setup`** — a straight-line sequence, which is why it
reads as "this, that, or the other". The maintainer's three nouns map exactly:
*applications* → 3, *dependencies* → 4, *whatever* → 5/6.

- [ ] **Fold 3-6 into ONE post-launch "Finish setting up" dialog** — a checklist
      of what is outstanding, with one confirm, instead of a modal chain. Each
      item keeps its own skip. Anything already satisfied is simply absent, so a
      fully-provisioned launch shows nothing at all.
      **Name the tension honestly: the menu-entry fix in this same change makes
      the chain WORSE before it gets better.** Declining used to be permanent
      (the bug), so prompt 3 had stopped appearing; keying it on path+version
      restores it once per release — which is what the maintainer asked for in
      the same session, and they answer Yes. So the consolidation is the thing
      that makes both asks true at once, not a nice-to-have on top of it.
      **Do not "fix" this by making prompts permanent-dismiss again** — that is
      the bug we just removed, and it is how prompt 3 disappeared for several
      releases without anyone choosing that.
  - **Triaged 2026-11-16 (open, ours):** still one modal after another (`ui/main_window_provision.py:228-245`).

## 2026-09-09 hardware run — 237/238, and the one failure was ours (2026-09-10)

Full run on `platterpus 0.6.45` + `platterpus-fork-gddc1e8c`: 237 passed, 0
errors, 0 skipped, reached the last step. `-H` with de-emphasis executed for the
first time ever (both P3 arms ok). The 0.6.42 cancel fix is proven on hardware —
cyanrip's log carries `Rip completed:  no (interrupted by SIGTERM, 0 of 14
tracks)`, `Interrupted at: track 1, mid-read` and a valid `Log FUN512:`.

- [ ] **Filed out of the fork's reading of our bundle (all ours).** The raw
      `cyanrip` invocations live only in `transcript.txt`, so the eight `.log`
      files a reader greps do not contain them — which is how their lap 9 §1
      concluded four flags never ran when all four did. **And their output does
      not travel at all**: `r16deemphon` / `r16deemphoff` are 0 occurrences in
      `MANIFEST.txt` and 0 files on disk, because the bundler collects album
      folders and a raw `cyanrip` verb produces none — so the run's strongest
      clause-2 evidence survives only as a banner quoted in a transcript. Plus:
      `zz-applog-rotations/` sorts and reads as an appendix, and the decisive
      file for the run's only failure was in it; and our application log's
      timestamps carry no UTC offset while every other artifact in the bundle
      does.
  - **Triaged 2026-11-16 (stale but open):** raw `cyanrip` verb rips now travel (`dda325e9`, each scripted rip's folder in the bundle). Still open: the app log's timestamps carry no UTC offset (`logging_setup.py:54`, plain `asctime`), and the rotations folder is still `zz-applog-rotations` (`test_session.py:363`).

## Round 16 — CLOSED `GO`/`GO` 2026-09-12 (written 2026-09-07 as *"ROUND 16 IS OPEN — their lap 1 filed, runbook run, everything verified"*)

> **Header corrected by the 2026-09-22 document audit**, which found it still announcing an open round ten days and seven rounds after the close. Items below that are still `[ ]` carry forward as ordinary backlog; the three plainly overtaken by later rounds are now marked.

**Their lap 1 arrived and the rehearsed runbook was run end to end.** Filed at
`docs/handshake/inbound/round-16-lap-01.md`, byte-identical to their committed
copy at `origin/platterpus-fork` (checked, not assumed). `CURRENT_ROUND` → 16,
`PIN_UNDER_REVIEW` → `a9aedf0`, the round-16 row is in `docs/handshake/README.md`,
and round 15's row — which still read OPEN — now reads its real verdict.

**What was verified rather than accepted, all of it derived here:**

- **All four shared-artifact hashes match byte for byte** — protocol v4,
  `seam-rules.md`, `seam-commands.md`, `OWNERSHIP.md`.
- **Both round digests re-derive exactly.** Our lap 16's declared
  `696b8ada8b203d21 over 15` and their round-16 `01ba4719c80b6fe9 over 0`, from
  our own implementation, which was built from their written spec rather than
  their code. Tenth consecutive agreement.
- **Their §D2 footer parses clean, and I nearly reported a defect against a line
  they do not print.** Their lap says the new path reads ``no (aborted…)``; I
  expanded the ellipsis myself, fed `no (aborted before any track was ripped)` to
  the parser, and watched it drop the reason and log two `unusable integer`
  warnings. **Their source says otherwise**: `src/cyanrip_log.c:907` at `a9aedf0`
  is `"Rip completed:  no (aborted, %i of %i tracks)\n"` — counts present, comma
  present, which is exactly the shape `_RIP_COMPLETED` expects. Measured:
  `completed=False reason='aborted' tracks=0/0`, no warnings. **An ellipsis in a
  peer's prose is not their output**; the rule is the one this repo keeps paying
  for — answer from the artifact.
- **Their §D1 timestamp is RFC 3339 at the pin**, `src/utils.h:213`
  (`%Y-%m-%dT%H:%M:%S%z` with `+HHMM` rewritten to `+HH:MM`). The empty-`%z` case
  degrades to a naive stamp, which our `_eac_date` already handles by omitting the
  `(UTC±HH:MM)` marker rather than inventing one.
- **§D3 is unreachable for us** — `-H` only, and we never pass it.

- [ ] **§J's drive-open proof is satisfiable by the wrong thing, and the 2026-09-07
      rig run proved it.** §J rips again after a cancel, on the reasoning quoted in
      `main_window_rip.py`: *"the only honest test of 'did cancelling release the
      drive?' is ripping again afterwards"*. It **passed** on a run where the drive
      was never released at all — the cancelled reader kept it for another 15 minutes
      and the second rip simply ran concurrently. A check that passes both when the
      drive was freed AND when it was never taken away is measuring nothing;
      `CLAUDE.md`'s *can it be satisfied by the wrong thing?* asked of the very check
      written to answer this question.
      **What it needs:** an assertion that nothing holds the device at that point —
      `fuser -s <device>` with no `-k`, tri-state, where "could not check" is not a
      pass. That is a new non-destructive probe in `drive_control` plus a script verb,
      so it is a change to the rig surface rather than a comment fix.
      NEXT-ROUND: the cancel defect itself is fixed, so §J is no longer *actively*
      misleading; it is still not evidence.
  - *2026-09-30: the probe half exists.* `drive_control.device_is_held` (`b9ac0974`) is
    `fuser -s <device>` with no signal, tri-state (`None` when fuser cannot answer, never
    read as "released"). What is missing is the script verb that asks it at §J's
    point, and §J's assertion on it.
  - **Triaged 2026-11-16 (open, ours):** still no verb: `device_is_held` is called only at `drive_control.py:787` and `exit_work.py:324`, and §J (`rig_scripts/fullacceptance.txt:983`) asserts nothing about the device.

- [ ] **Embed the `-j` record in `.platterpus.json`.** *(Retitled 2026-09-30 from
      ~~**Move the `-j` diagnostics record into the album folder after the rip.**~~,
      which the maintainer ruled out on 2026-09-27: the album folder holds only `.log`,
      `.cue` and `.platterpus.json`, per the `DIAGNOSTICS_RECORD_PREFIX` comment in
      `adapters/cyanrip_backend.py`.)* Its
      name is now per-rip (2026-09-07), which fixes the overwrite and the concurrency
      race, but it still lands in `output_dir` — the rips root — so the evidence
      bundle does not collect it and it litters the user's music library one file per
      rip. The album folder is only knowable AFTER the rip (cyanrip derives it from
      `-D`), and predicting it is what cost a finished 14-track rip over one
      character, so the fix is a post-rip move from the known log path's parent, not a
      cleverer argv. Small, and deliberately not done in the same change as the cancel
      fix: that one touches a destructive path and wanted its own commit.
  - *2026-09-27: not done, deferred, the maintainer's choice that day:* a move into the album
    folder was built and withdrawn, because a rip leaves only its `.log`, `.cue` and
    `.platterpus.json` there (the one-debug-file rule). The record is to be EMBEDDED in
    `.platterpus.json` instead, which moves the report schema, so it waits for the next
    round and is announced to the fork in a lap first. Until then the record stays in the
    rips root, one file per rip, and the row above sends it in each rip's bundle.
  - *Merged 2026-09-30, from row E5 (its `-j` half):* "The `-j` diagnostics record goes
    nowhere — lands in the rips root, nothing reads it, the auto-bundle does not collect
    it". The last clause is stale: `09636001` (2026-09-28) collects each album pass's
    record into that rip's report bundle, by name from the rips root. The rest holds:
    it still lands in the rips root and nothing parses it. E5's other half (`Encoder
    errors:` has no `-j` field) stays in E5.
  - **Triaged 2026-11-16 (stale but open):** the record is read into the report in parts (`outcome.ripper_record` v32, `disc.isrc_provenance` v35, `disc.error_positions` v39) but not embedded whole, and it still lands in the rips root (`adapters/cyanrip_backend.py:840-843`: *embedding it in the report is next*).

## Round 22 (CLOSED `GO`/`GO` 2026-09-21) — the queue, and why none of it was built before lap 4 was released (2026-09-18)

> **Round 22 is closed**, so the release-ordering constraint in this header no longer binds; the open items below are ordinary backlog now. (Header tense corrected by the 2026-09-22 document audit.)

**Read this heading before touching any row below it.** Round 21 lap 4 states, in
a file we are about to send, that two of these are *"not fixed, and reported
rather than quietly widened"*. Fixing one before the operator announces the lap
would make our own sent lap false — which is **§A of that same lap**: *a claim can
outlive the fix that invalidates it, because nothing re-runs what produced it*.
The order is: release lap 4 → the fork closes on their lap 5 → then build. Any row
here that lands early must also edit the lap, and the lap is the harder thing to
get right twice.

- [ ] **A capability gate keyed on the peer's identity, whose table of known peers
      ships inside a release, cannot recognise a peer newer than that release.**
      §H2 of lap 4, found in the round-21 artifact itself: line 4 of the citable
      log reads `Consumer: not identified (no --consumer given)`, because
      `accepts_consumer_flag` is deliberately `False` for an unrecognised build
      and the operator's released 0.6.50 AppImage (`4bedb45`, the v0.6.50 release
      commit) carries **zero** occurrences of `3952c03` — the pin was agreed after
      that release. **Nothing is broken; the gate did what it was built to do.**
      The consequence had never been written down: *for the whole life of a round,
      every rip on the agreed test pin from a released app records a
      half-identified pair* — the precise thing that accept-set exists to prevent,
      arriving from the direction it was not written for. It was designed against
      *their build being too old for the flag*; this is *our app being too old to
      know their build*, and the fail-closed default is identical in both cases
      while only one of them is a real risk.
      **Two candidate remedies, and the choice is NOT made — do not pick one
      silently.** (a) The `--install-ripper` move: give the accept-set a route to
      it that does not ship inside a release, same family as *"a moving pin needs a
      route to it that does not ship inside a release"*, which we already solved
      once. (b) Stop it being a table: derive acceptance from something the binary
      itself answers — probing the flag is the obvious candidate and the obvious
      hazard, since a rejected flag exits non-zero and reads to every probe as
      *"the tool is not installed"*, which is the `-V` failure exactly.
      Declared `NEXT-ROUND` in lap 4.
  - *2026-09-25:* **Decided (D5 B): ask the binary.** Read `cyanrip -h`, look for `--consumer`, and cache the answer per build. When the help text cannot be read, send no flag (today's behavior). This replaces the shipped accept-set, so a build newer than the app is recognised. Ready to build, as a probe through the dependency subsystem.
  - **Triaged 2026-11-16 (open, ours):** still a shipped table (`deps/fork_source.py:1906-1917`); D5 B waits on the fork's word that the `-h` line is contracted (fork list F2).
- [ ] **`defeat_audio_cache` carries its provenance in the EAC export and NOT in
      the report JSON — the fork's round-21 §H, accepted, and it is ours.** The EAC
      row says *"(measured for this drive with `cd-paranoia -A`, not asserted from
      the ripper's log)"*; `/rip/defeat_audio_cache` says nothing, and it sits
      beside `ripper_build`, `read_stalls` and `invoked_as`, **all three of which
      DO come from the ripper's log**, while cyanrip's own `Cache model:` line says
      the drive was not probed. A reader of the JSON has every reason to attribute
      our measurement to them. **We fixed the instance and not the class:** the
      sentence the fork quoted back at us — *"a reader could not tell any of that
      from the row"* — is our own, written about the EAC row in round 7 §6b and
      fixed only there. Third instance of that shape in one lap (§H2, §A, this).
      **Deliberately NOT fixed in round 21:** a provenance field on a report key
      moves `REPORT_SCHEMA_VERSION`, and lap 4 line 29 declares
      `HANDSHAKE-BREAKING: **None from us.** REPORT_SCHEMA_VERSION unchanged`.
      Landing it early makes a sent lap false about its own header.
  - **Triaged 2026-11-16 (open, ours):** still no provenance beside the field (`rip_report.py:2330`).

## Mutation sweep — give the weekly audit a SCORE floor (2026-09-06)

- [ ] **Add `--min-score` per leg to `.github/workflows/mutation.yml`.** The sweep
      today has `--min-checked` only, which stops it reading green on a run that
      measured nothing — but nothing stops the *score* eroding. The gains are only
      as durable as the ratchet under them, and there is none.
      **The three legs measured on 2026-09-06 (`--seed 0 --limit 40`, so CI samples
      the identical population)** — record them here so the next session sets the
      floors from a measurement rather than inventing one:
      `verdict` **94.9%** (37/39 killed, 66 generated), `rip-log` **100.0%**
      (40/40, 64 generated), `cyanrip-log` **77.5%** (31/40, 199 generated).
      **The other three legs were not measured in that change** — `ctdb-crc`,
      `eac-log`, `eac-log-export` — so measure before setting theirs; a floor
      invented rather than measured is the shape this workflow's own comments
      refuse. Then extend
      `tests/test_mutation_audit_can_report_its_own_absence.py` the same way it
      already handles `floor:`: every leg must **declare** one, and it may rise,
      never fall.
  - **Triaged 2026-11-16 (open, ours):** `--min-score` exists (`scripts/mutation_sweep.py:453`) and no leg passes it (`.github/workflows/mutation.yml:189-196`).

## Left open by the 0.6.38 archival-check fixes (2026-09-05)

- [ ] **Split `uiscript/runner.py` (3898 lines).** The oversize ratchet was raised
      rather than split for the same reason — refactoring the script engine on the
      night of the run it drives is the risk this project keeps paying for. The
      raised numbers are the debt marker, not a settlement. Mixins, per the
      `MainWindow` precedent in `docs/architecture.md`.
  - *Audit 2026-09-25: confirmed open.* Not split, and runner.py has grown to 4305 lines.
  - *2026-10-05: 4,787 lines.* E2 of the 2026-10-05 ranked list: after the beta.
  - **Triaged 2026-11-16 (open, ours):** not split; 5,068 lines.
- [~] **Split the post-rip chain out of `ui/main_window_rip.py` (4458 lines).**
      **Raised for the third time in a month** (2026-08-18, 2026-09-08,
      2026-09-15), which is the signal the ratchet exists to produce rather than a
      number to keep nudging. The seam is obvious and the 2026-09-15 defect is the
      argument for it: tagging → cover art → re-compress → transcode → the three
      verify daemons is a *pipeline with its own lifetime*, and it lives inside the
      window, which is why its results have nowhere to go once "the current rip"
      moves on. A `PostRipChain` owning `(rip_dir, rip_log, settings snapshot,
      report handle)` would make the superseded case a state of that object instead
      of a hole in the window's, and would close the TASKS row above it about
      routing a late result back into the album it belongs to. Deliberately NOT
      done in 0.6.49: a hardware re-run is waiting on the fix, and a structural move
      shipped under a release is how a correct fix arrives broken.
  - *Audit 2026-09-25: partly done.* ui/post_rip_record.py (the per-album record) landed. The chain itself (tagging → transcode → verify) is still in main_window_rip.py, now 4715 lines.
  - *2026-10-05: 4,977 lines,* the largest module in `src/`. E2 of the 2026-10-05 ranked list: after the beta.
  - **Triaged 2026-11-16 (open, ours):** not split; `ui/main_window_rip.py` is 5,391 lines.

---

## Acceptance-path review, 2026-09-04 — what an eight-lens sweep left open

**Provenance of this list.** Eight parallel reviewers over the acceptance path,
738 sites examined, 65 raw findings, then two adversarial verifiers per
`BLOCKING` claim. **The verification is PARTIAL: 10 of the verifier agents died
on an org spend limit**, so the `BLOCKING`/`NEXT-ROUND` split below is confirmed
for some rows and merely claimed for others. Rows are marked. Nothing here is
graded from an unverified claim.

Fixed in the same session: the two `expect-status Done` sites, the five ARCHIVAL
rips that asserted nothing about completion, the same two defects across the
other four committed scripts, `securereread.txt`'s 10800 budget, `rig-check`'s
SKIP-passes-as-zero, and `abort-if-failed`'s scope.

- [ ] **`rig-check` has no subject identity — it grades the newest rip on the
  MACHINE, not the rip its section made.** `[CONFIRMED BLOCKING]` The other half
  of the finding whose floor was fixed. Discovery is newest-`.platterpus.json`
  by mtime (`rip_compare`), and a rip that never started writes no report — so
  §I's `rig-check` can grade §H's completed two-track rip as the *cancel*
  evidence, and §N's can grade §K3's WAV rip as T1's. Seven ARCHIVAL sites.
  Largely mitigated as a side effect of this session's work — `expect-rip-complete`
  now precedes five of the seven, so a section whose rip did not happen fails
  before `rig-check` runs — but mitigation is not the guarantee, and the two
  uncovered sites are §G (whose subject is §F's rip, legitimately) and §I (whose
  rip is *cancelled*, so completion is the wrong claim). The real fix is for
  `rig-check` to be told which rip it is grading.
  - **Triaged 2026-11-16 (open, ours):** unchanged: `fullacceptance.txt` still calls `rig-check` bare seven times (`:812`, `:980`, `:1015`, `:1171`, `:1199`, `:1227`, `:1396`).
- [ ] **Nothing in the run's artifacts groups steps by section or carries the
  severity classification the release bar is defined in terms of** — so grading
  a run against `docs/testing.md`'s table is a manual join. `[CLAIMED]`
  - **Triaged 2026-11-16 (open, ours):** unchanged: `uiscript/report.py` has no section or severity field.

## From the 2026-09-03 acceptance bundle (2026-09-04)

Three fixed in 0.6.35/0.6.36 (section-F budget, the EAC `Copy OK` over
unreproducible tracks, the two operator pages that said to refuse the required
build, the false-fatal re-read verdict, the diagnostics header naming the
approved build). These are what the same reading left open.

- [ ] **The acceptance run asserts the RIPPER build and never the APP version.**
  Section A stops the night in four seconds if the wrong cyanrip is installed —
  correct, and it has now earned its keep twice. Nothing does the same for
  Platterpus itself, and the script ships *inside* the app, so an operator on a
  stale build runs that build's stale script and gets its stale budgets. The
  2026-09-03 run is the case: `0.6.34`'s script waited `10800`s on section F
  because that is what `0.6.34` shipped, and nothing on screen said a newer
  release existed. **The script cannot fix this** — a version assertion baked into
  a shipped file can only ever compare the app to itself. The check belongs at
  *Tools → Run acceptance test…*: if the update check already knows a newer
  release exists, say so **before** six hours of drive time, not after. Same
  reasoning as section A, one axis over.
  - **Triaged 2026-11-16 (open, ours):** unchanged; no newer-app check before an acceptance run in `ui/`.
- [ ] **Track 3's copy CRC was identical across two whole-disc rips hours apart
  while its own within-rip re-reads disagreed** — and track 5's differed between
  rips while its AccurateRip CRC was identical in both. Recorded in round 15 lap 6
  §D5 as `[UNVERIFIED]`. There is a candidate explanation involving the sample
  range AR skips at track boundaries; it has not been tested, so it is not being
  offered as one.
  - **Triaged 2026-11-16 (hardware):** unverified still. The track 3 investigation is R134 and R135; this puzzle's AccurateRip-skip explanation has not been tested there.

## Split the acceptance session out of `main_window_provision.py` (2026-09-01)

- [ ] **`ui/main_window_provision.py` is 1,212 lines doing four jobs** — host
  provisioning, AppImage integration, the uninstaller, and now ~550 lines of
  acceptance session. `CLAUDE.md` says split a Qt god-object via **mixins** the
  concrete class inherits, so methods stay reachable as `window._x`. The module
  docstring still names only the first three. Deliberately **not** done at
  release time with a real hardware run in flight: a 550-line move earns no
  functional gain and risks the thing being tested. The size ratchet in
  `tests/test_critical_rules_are_enforced.py` records the number so it cannot
  grow further unnoticed.
  - *Audit 2026-09-25: confirmed open.* Not split, and now 1607 lines.
  - **Triaged 2026-11-16 (open, ours):** not split; 1,936 lines.

## The lesson→gate audit backlog (2026-08-28)

**130 gaps, from the 187-item audit written up in `docs/testing.md` §5C.**
Every row carries a concrete breaking change and a proposed gate in the audit
data; the one-liners here are the index. Effort: **72 small, 51 medium, 7
large**. Two were fixed on the day (`from __future__ import annotations`,
`Signal(object)` payloads) and are not listed.

**Read the shape before the list:** 52 of the *existing* gates can be satisfied
by finding nothing — present, green, passing on an empty population. That is
more than the 54 that genuinely work, so section 5 below outranks the rest.

### 5. Existing gates satisfiable by finding nothing (20)

- [ ] **`vacuity:tests/test_handshake_protocol.py::test_the_cyanrip_return_spec_enumerates_every_section`** (partial, medium) — Nine markers checked anywhere in a 29 KB doc, none tied to the return spec
  - **Triaged 2026-11-16 (open, ours):** still nine substrings anywhere in the doc (`tests/test_handshake_protocol.py:80-96`).
- [ ] **`vacuity:tests/test_report_writer.py::test_close_waits_for_the_pending_write`** (partial, medium) — The final-report-survives-close guard is a substring match on closeEvent's text
  - **Triaged 2026-11-16 (open, ours):** still a substring match on `closeEvent`'s source (`tests/test_report_writer.py:181-193`).
- [ ] **`vacuity:tests/test_scroll_guards.py::test_every_module_with_a_value_widget_installs_the_guard`** (partial, medium) — The wheel-guard sweep tests for a name in the file, not a call in the constructor
  - **Triaged 2026-11-16 (open, ours):** still a name search (`tests/test_scroll_guards.py:237-260`).
- [ ] **`vacuity:tests/test_scroll_guards.py::test_the_settings_dialog_installs_the_wheel_guard`** (partial, medium) — A class literally named TestItIsActuallyWiredIn verifies a MENTION, not a call
  - **Triaged 2026-11-16 (open, ours):** still a source search (`tests/test_scroll_guards.py:317-329`).
- [ ] **`vacuity:tests/test_dynamic_sweeps_declare_a_floor.py::test_every_computed_parametrize_is_registered`** (partial, large) — The anti-vacuity meta-gate polices parametrize only — plain rglob loops are unpoliced
  - **Triaged 2026-11-16 (open, ours):** unchanged; the plain `glob` loops (`tests/test_dynamic_sweeps_declare_a_floor.py:370`, `:454`) are not policed.

### 1. Critical rules with no gate (16)

- [~] **`rule-10.no-bare-any`** (partial, medium) — Critical rule #10 — no bare Any, and no bare `# type: ignore`
  - *Audit 2026-09-25: partly done.* A bare `# type: ignore` is refused by mypy's ignore-without-code. A bare Any is not (disallow_any_explicit is off), and the required `# reason` suffix is not checked.
  - **Triaged 2026-11-16 (open, ours):** unchanged: `disallow_any_explicit` is still off (`pyproject.toml:372`).
- [~] **`rule-4.one-transcode-adapter`** (partial, medium) — Critical rule #4 — one transcode adapter, no bespoke per-encoder install code
  - *Audit 2026-09-25: partly done.* test_deps_registry::test_ffmpeg_spec_is_registered_and_optional and the spawn-site classification. No sweep that encoders are invoked or installed only via adapters/transcode.py and deps/.
  - **Triaged 2026-11-16 (open, ours):** no general gate found in `tests/`; stays a P3 gate idea under the 2026-10-12 ranking.
- [ ] **`rule-6.one-subsystem`** (ungated, medium) — Critical rule #6 — dependency self-management is one subsystem, not scattered checks
  - **Triaged 2026-11-16 (open, ours):** no general gate found in `tests/`; stays a P3 gate idea under the 2026-10-12 ranking.
- [ ] **`rule-7.session-log`** (ungated, medium) — Critical rule #7 obligation 2 — a session-log entry before ending a session
  - **Triaged 2026-11-16 (open, ours):** no general gate found in `tests/`; stays a P3 gate idea under the 2026-10-12 ranking.

### 2. §5 cases with no gate (14)

- [~] **`§5.x`** (partial, small) — Test the wiring, at the call site
  - *Audit 2026-09-25: partly done.* test_dead_attribute_reads (b96922d) plus per-site wiring tests. No sweep for getattr-with-default, or for wiring tests going through the entry point.
  - *2026-09-27:* the getattr-with-default half is covered: `tests/test_dead_attribute_reads.py` reads string attribute names, which is how the `getattr` defect was spelled. Still open: no sweep that wiring tests go through the entry point.
  - **Triaged 2026-11-16 (open, ours):** no general gate found in `tests/`; stays a P3 gate idea under the 2026-10-12 ranking.
- [~] **`§5.an`** (partial, medium) — A gate that picks its subject by chance is not a gate
  - *Audit 2026-09-25: partly done.* Instance: test_fork_source::test_the_pin_check_reads_a_closed_round_not_whatever_sorts_last. No sweep for non-total sort keys.
  - **Triaged 2026-11-16 (open, ours):** no general gate found in `tests/`; stays a P3 gate idea under the 2026-10-12 ranking.
- [ ] **`§5.ao`** (ungated, medium) — A number read from a run still in flight is the fast tail, not the range
  - **Triaged 2026-11-16 (open, ours):** no general gate found in `tests/`; stays a P3 gate idea under the 2026-10-12 ranking.
- [~] **`§5.at`** (partial, medium) — The advice a failure prints is code, and it can carry the bug
  - *Audit 2026-09-25: partly done.* Instances in test_dialog_lifecycle_logging. No gate that executes printed advice.
  - **Triaged 2026-11-16 (open, ours):** no general gate found in `tests/`; stays a P3 gate idea under the 2026-10-12 ranking.
- [~] **`§5.p`** (partial, medium) — A documented capability is not a capability
  - *Audit 2026-09-25: partly done.* Instances: the qthread flag-only-cancel allowlist, and the `is not RipBackend.x` checks. No general ABC-no-op sweep.
  - **Triaged 2026-11-16 (open, ours):** no general gate found in `tests/`; stays a P3 gate idea under the 2026-10-12 ranking.
- [ ] **`§5.s`** (ungated, medium) — A fix is a change, and changes have their own failure modes
  - **Triaged 2026-11-16 (open, ours):** no general gate found in `tests/`; stays a P3 gate idea under the 2026-10-12 ranking.
- [~] **`§5.t`** (partial, medium) — Harness fidelity — a stand-in must not be better than the real thing
  - *Audit 2026-09-25: partly done.* test_harness_fidelity covers thread teardown only. Stand-ins and stubbing the method under test are not gated.
  - **Triaged 2026-11-16 (open, ours):** no general gate found in `tests/`; stays a P3 gate idea under the 2026-10-12 ranking.

### 3. "Stop shipping the next one" bullets (15)

- [~] **`checklist-18`** (partial, small) — Is the user's symptom gone, or just the mechanism I named?
  - *Audit 2026-09-25: partly done.* test_no_stale_version_claims gates version bumps on hardware passes. Nothing ties a single fix to hardware confirmation.
  - **Triaged 2026-11-16 (open, ours):** no general gate found in `tests/`; stays a P3 gate idea under the 2026-10-12 ranking.
- [~] **`checklist-23`** (partial, medium) — Did a correction get less scrutiny than a claim?
  - *Audit 2026-09-25: partly done.* handshake.py --check requires a Confirmations section in outbound laps. Nothing checks that a correction was independently verified.
  - **Triaged 2026-11-16 (open, ours):** no general gate found in `tests/`; stays a P3 gate idea under the 2026-10-12 ranking.
- [ ] **`checklist-24`** (ungated, medium) — Never state a mechanism in the other side's code without citing where you read it
  - **Triaged 2026-11-16 (open, ours):** no general gate found in `tests/`; stays a P3 gate idea under the 2026-10-12 ranking.
- [ ] **`checklist-4`** (ungated, large) — Would this test fail if I reverted the fix? (and did the revert actually land?)
  - **Triaged 2026-11-16 (open, ours):** no general gate found in `tests/`; stays a P3 gate idea under the 2026-10-12 ranking. `scripts/revert_probe.py` exists and nothing requires it per fix.

### 4. Code conventions (8)

- [~] **`conv.a11y-colour`** (partial, medium) — Code convention / WCAG 1.4.1 — status is never colour alone
  - *Audit 2026-09-25: partly done.* TestUseOfColour covers verdict.accuraterip_verdict only, plus per-widget asserts. No sweep over the other status surfaces.
  - **Triaged 2026-11-16 (open, ours):** unchanged: `TestUseOfColour` still checks the verdict levels only (`tests/test_accessibility_standards.py:77`).

### 6. Mutation-testing scope (22)

- [ ] **`mutation:_survivors-20260925`** (ungated, medium) — The nine new legs' first sweep left 77 survivors of 241 checked; read them and kill the real ones
  - *2026-09-25:* Measured in a separate worktree at 24755e1 (`--limit 40 --seed 0`). By leg: cyanrip-backend 14, rig-check 14, settings-validation 14, ripper-identity 11, ctdb-diagnose 9, ctdb-decode 5, handshake-approval 4, naming 4, ctdb-toc 2. **Not all are test gaps:** several are `@dataclass(frozen=True)` flipped to `False` (naming.py:130, ripper_identity.py:63, ctdb/toc.py:40, handshake_approval.py:257), which only says no test asserts immutability. Triage each as *equivalent*, *immutability only*, or *a real missed behavior*, and write a test for the last kind. The weekly run's artifact lists them all.
  - **Triaged 2026-11-16 (open, ours):** not triaged since; P2 #28 of 2026-10-12.
- [ ] **`mutation:deps/fork_source.py`** (ungated, medium) — Ripper build offers and pins — 6 fix commits, pure, and the two-surfaces-one-key defect lives here
  - **Triaged 2026-11-16 (open, ours):** still no leg (`.github/workflows/mutation.yml:80-145`).
- [~] **`mutation:parsers/cyanrip_log.py`** (partial, medium) — In scope on paper, 6 fix commits, 1,357 mutants — none checked
  - *Audit 2026-09-25: partly done.* Now a leg with a floor of 30, but --limit 40 with a fixed --seed 0 checks the same 40 of 193 mutants every week; about 150 are never checked.
  - **Triaged 2026-11-16 (open, ours):** unchanged: no `--seed` in the workflow, so the sweep's default seed 0 (`scripts/mutation_sweep.py:444`) samples the same 40 every week.
- [ ] **`mutation:rip_audit.py+evidence_bundle.py+checksums.py+parity.py`** (ungated, medium) — Four small pure archival modules, 3 fix commits between them, none in scope
  - **Triaged 2026-11-16 (open, ours):** still no legs (`.github/workflows/mutation.yml:80-145`).
- [ ] **`mutation:rip_compare.py`** (ungated, medium) — 1,404 pure lines comparing two rips — 2 fix commits, outside scope
  - **Triaged 2026-11-16 (open, ours):** still no leg.
- [ ] **`mutation:rip_report.py`** (ungated, medium) — The JSON report of record — 5 fix commits, pure, 2,302 lines, largest single addition
  - **Triaged 2026-11-16 (open, ours):** still no leg.
- [~] **`mutation:verdict.py`** (partial, medium) — In scope, 348 mutants, 0 checked — and the thinnest test selection in the config
  - *Audit 2026-09-25: partly done.* Now a leg with a floor of 30 (66 generated, capped at 40); the test selection is still tests/test_verdict.py only.
  - **Triaged 2026-11-16 (open, ours):** the leg still runs `tests/test_verdict.py` alone (`.github/workflows/mutation.yml:82`).
- [ ] **`mutation:app.py`** (ungated, large) — 6 fix commits, second-highest count — and not a mutmut candidate *(2026-09-30: the audit is `scripts/mutation_sweep.py`, not mutmut, so the open question is a sweep leg for it)*
  - **Triaged 2026-11-16 (open, ours):** still no leg.
- [ ] **`mutation:ui/main_window*.py`** (ungated, large) — 16 fix-commit touches across the main-window mixins — outside scope and outside mutmut's reach *(2026-09-30: the audit is `scripts/mutation_sweep.py`, not mutmut, so the open question is a sweep leg for them)*
  - **Triaged 2026-11-16 (open, ours):** still no leg.
- [ ] **`mutation:uiscript/runner.py`** (ungated, large) — Top shipped-bug module in the window (11 fix commits) and the worst mutmut candidate *(2026-09-30: the audit is `scripts/mutation_sweep.py`, not mutmut, so the open question is a sweep leg for it)*
  - **Triaged 2026-11-16 (open, ours):** still no leg.

### 7. Boundary functions with no property test (23)

- [ ] **`fuzz:rip_report.build_report`** (ungated, medium) — The JSON rip report has no never-raises property test over parser output
  - **Triaged 2026-11-16 (open, ours):** still none; the `@given` tests that call `build_report` check single fields, not the whole builder.

### 8. Event-ordering / stateful testing (12)

- [~] **`stateful:no-modal-during-rip`** (ungated, small) — A spontaneous modal must not open over a running rip
  - *Audit 2026-09-25: partly done.* Only the ripper-update offer is covered (test_the_automatic_check_stands_down_during_a_rip, test_a_rip_that_starts_MID_CHECK_still_stops_the_modal); no sweep over other spontaneous modals.
  - *2026-09-25:* **Partly done.** The two MusicBrainz modals (the release picker and the unknown-album dialog) no longer open over a running rip; same test as `stateful:table-immutable-during-rip`. Still open: a sweep over every other spontaneous modal.
  - **Triaged 2026-11-16 (open, ours):** no sweep over every spontaneous modal yet.
- [ ] **`stateful:missed-swap`** (partial, medium) — A disc swap the poller does not observe leaves the whole app describing the wrong disc
  - **Triaged 2026-11-16 (open, ours):** still open; the rip itself is now caught after the fact by `disc_identity` (`166635ea`), which does not correct what the window shows.
- [ ] **`stateful:staleness-key-is-a-value`** (ungated, medium) — The disc/MB pipeline keys staleness on a mutable value; the rip pipeline uses a monotonic generation, and only one of them has …
  - **Triaged 2026-11-16 (open, ours):** unchanged: the disc and MusicBrainz path still keys on the disc ID string (`_mb_release_chosen_for`, `ui/main_window.py:411`), with no generation like the rip path's.
- [ ] **`stateful:harness`** (ungated, large) — No test anywhere explores event ORDERING; every fixture starts in an end state
  - **Triaged 2026-11-16 (open, ours):** unchanged.

---

## Bring the overnight run inside the app (maintainer, 2026-08-26)

Standing instruction, given while the shell version was being written: *"we should
plan for getting some of this internal, such as the compressed single file and
keeping the sleep mode off ability."* `platterpusovernight.sh` ships now because
tonight's run needs it, and every line of it is a line the app should own — the
project's own rule is that a procedure handed back in prose is a symptom, and a
shell wrapper is one step better than prose, not the destination.

- [~] **Inhibit sleep from inside a script run, for its duration.** Same
      mechanism, different owner: take the systemd inhibitor lock when
      `--run-script` starts and release it when the run ends, including on a
      crash or a cancel. **The lock must not outlive the run** — that is the whole
      reason `systemd-inhibit`'s child-lifetime model was chosen over a settings
      change, and an in-process implementation has to reproduce it deliberately
      rather than inherit it. Reach it as a **script verb** if it should be
      per-script (`inhibit-sleep`), not a flag — `CLAUDE.md`'s *a new testing
      capability is a SCRIPT VERB* — unless the right answer is that every
      unattended run wants it, in which case it belongs to `--run-script` itself
      and needs no surface at all. Decide which before writing it.
  - *Audit 2026-09-25: partly done.* sleep_inhibit.SleepInhibitor is held by Tools → Run acceptance test. A plain --run-script takes no lock, and there is no inhibit-sleep verb.
  - **Triaged 2026-11-16 (open, ours):** a plain `--run-script` still takes no lock; only *Run acceptance test* holds `SleepInhibitor` (`ui/main_window_provision.py:810-812`).
- [~] **Make the run's own bundle the ONE file.** The auto-bundle already exists
      and already prints *"SEND THIS ONE FILE"*; it calls
      `evidence_bundle.build_bundle()` **without `album_dir`**, which is the
      parameter that admits a rip folder's files — so it carries the app log and
      the script-run folder and **not one rip log, cue sheet, EAC log or `-j`
      record**. That single omission ~~is~~ was the entire reason
      `platterpusmorning.sh` existed (deleted 2026-09-27 in `1b2f7007`). Passing the run's rip folders would collapse
      three collectors into the one the app already builds. **Every text artifact
      from every rip folder, not the newest** — the acceptance run performs seven
      rips and the one the handshake round is waiting on is not the last of them.
      Audio never enters the bundle (Critical rule #8); the suffix allowlist and
      the post-stage sweep in the shell collector are the behavior to port.
  - *Audit 2026-09-25: partly done.* The acceptance-session bundle passes album_dirs from session_album_dirs. The --run-script auto-bundle (runner.py) still has none.
  - **Triaged 2026-11-16 (open, ours):** the `--run-script` bundle now carries raw `cyanrip` rips' folders (`dda325e9`; `uiscript/runner.py:4477`), but not the folders of rips the window makes (`_scripted_rip_dirs` is filled only at `:1980`).
- [x] **Write it to `~/Downloads`.** The folder a browser upload dialog opens in.
      Fall back rather than `mkdir`: inventing the directory puts the file
      somewhere the operator has no habit of looking.
  - *Audit 2026-09-25: superseded.* The maintainer's 2026-09-24 ruling put everything in one session folder (test_session.plan_session); downloads_dir now only suggests where to save a transcript.
- [x] **Ship `docs/rig-scripts/*` INSIDE the AppImage, so an acceptance run needs
      zero downloads.** Measured cost of not doing it, 2026-08-27: handing over
      tonight's run took **three** raw-file fetches (`platterpusovernight.sh`,
      `platterpusmorning.sh`, `fullacceptance.txt`) plus one command — and the
      three-file shape is precisely the *"never hand back an instruction file"*
      symptom, one indirection removed. With the scripts packaged,
      `--run-script fullacceptance` resolves against the bundle and the handover
      is one command with no fetch at all. `uiscript/find_script.py` already
      searches `~/Downloads`, `~/Desktop` and `.`; a **packaged** directory joins
      that list as a *last* fallback, never a first — an operator who downloaded
      a newer script must still win over the one baked into their build, and
      silently preferring the packaged copy is the "ran a different script
      without saying so" defect that module exists to end. Print which copy was
      resolved, always.
  - *Audit 2026-09-25: partly done.* The scripts ship in src/platterpus/rig_scripts/ and the menu uses builtin_acceptance_script, but find_script.FALLBACK_DIRS has no packaged fallback, so `--run-script fullacceptance` does not resolve to it.
  - *Done 2026-09-27:* `uiscript/find_script.py` appends `packaged_scripts_dir()` LAST, and
    `_which_copy` labels every answer (packaged, or yours, and whether yours differs from a
    shipped copy of the same name). A bare name widens to `.txt`/`.pscript` in every folder,
    so a download still beats the packaged copy. Tests: `tests/test_script_console.py`
    (including a `main()`-driven one) and `tests/test_test_session.py` (menu and CLI name one
    folder).
- [x] **Retire `platterpusovernight.sh` and `platterpusmorning.sh` in the same
      commit that lands the above** — including their rows in
      `docs/rig-scripts/README.md`. Two routes to one bundle is two answers to
      *"which file do I upload"*, which is the question this work exists to make
      unambiguous.
  - *Done 2026-09-27, in the same commit as the row above:* both scripts deleted, their
    README section replaced by "Which collector gathers what", `securereread.txt` points at
    `--rig-session`, and live comments name them as labels. `platterpuscollect.sh` stays.
    Guarded by `tests/test_rig_scripts.py` (no live instruction to run a retired wrapper,
    and the files cannot come back).

## Round 14 lap 12, 2026-08-25 — a header that promised a stop it could not perform

- [x] **`fullacceptance.txt` §A claimed it "stops you in the first four seconds"
  on the wrong ripper build, and it did not.** New `abort-if-failed` verb, used
  once after the identity assertions. Preconditions abort; findings do not.
- [x] **The rig harness printed a false conclusion as a finding** — exit 137
  "means the reader was wedged". cyanrip has caught SIGTERM since
  `+platterpus.7`, so SIGKILL is the expected terminator and 137 says nothing
  about the drive.
- [x] **An empty stdout capture beside a populated `-j` record** now reports the
  disagreement as its own finding. The ripper path is a Distrobox wrapper, so a
  container runtime sits between cyanrip's fd 1 and our redirect; `-j` bypasses
  it. Why the forwarding lost the bytes is NOT DETERMINED and is not guessed at.
- [x] **Our handshake gate read `HANDSHAKE-TEST-PIN: none.` as a build** (the
  fork's §F2 — they found it in theirs and asked). Fixed at the reader; only an
  exact `none` reads as an absence.
- [x] Fork's **C1 detector added as section P2**; **J6 answered** (the verb is
  bounded — 300 s + kill + 20 s, then an unreapable-child report).
- Duplicate of **G11. Version-gate evidence** — merged 2026-09-30.
- [x] Run the fork's `rig-c1-probe.sh` **only if section P2 hangs**.
  - *Audit 2026-09-25: not ours to verify.* A conditional operator action; nothing in the record says P2 hung.
  - *2026-09-25:* **Closed as a duplicate, not done.** The work is tracked in the row *"Run fullacceptance.txt overnight — now 0.6.30 against d9c058c."* (merged 2026-09-30 into **G11. Version-gate evidence**, which stays open).

## Round 14 lap 10, 2026-08-25 — the cancel that destroyed its own log

- [x] **We sent cyanrip TWO SIGTERMs per cancel, 0.445 ms apart** — the second
  taking its `_exit(1)` branch, which runs no `atexit` and so writes neither the
  completion footer nor the FUN512. Three call sites each sent their own, the
  third commented *"free and idempotent"* (true of `Popen.terminate()`, false of
  the handler receiving it). One chokepoint now, at most one per subprocess, keyed
  on the handle's identity. Answers the fork's J1; measured on the real path.
- [x] **The cancel `break` discarded the ripper's dying line**, silently, every
  time — the line that is its answer to being cancelled. Why the fork found zero
  `"Trying to quit"` in 51,492 captured lines and concluded their handler never
  ran. Both lines of the `\r\n`+message shape now retained and revert-probed.
- [x] **`test_qthread_ownership.py` now follows one level of same-class
  delegation**, so extracting a kill into a chokepoint stops reporting the cancel
  as flag-only. Fixed by teaching the sweep, not by an allowlist entry — the
  convenient repair would have asserted something false in the file that exists
  to prevent that.
- [x] Fork's **J3 answered** — no objection to a sixth `--verify-log` exit code
  for *"checksum valid, record incomplete"*; one ask, that the provider contract
  name **which builds** emit it (else it is indistinguishable from a rejected
  flag, the `-V` shape again). Filed for round 15 by them, not blocking.
- [x] **T1 PASSED and round 14 CLOSED (GO/GO on `d9c058c`), 2026-08-27.**
  `securereread.txt` on the rig: `-Z 2 -r 3`, **14/14 tracks** reporting
  `Done; (2 out of 2 matches)`, `Ripping errors: 0`, and the `Log FUN512:`
  footer present — which is itself the proof `atexit` ran. Declared in
  `docs/handshake/outbound/round-14-lap-18.md`; their GO is lap 17 line 6, their
  acknowledgement lap 19.
- [x] **Verify §A4's prediction on the next cancel artifact** (any build after
  these fixes): `Trying to quit` present in the capture, completion footer
  present, valid FUN512 so `--verify-log` exits 0, exit code 1. Any of those
  still missing means our fix was not the whole cause.
  - *Audit 2026-09-25: done.* artifactsround26/round26cancelmereport.json: "Trying to quit" present, footer interrupted by SIGTERM, verify-log exit 0, ripper exit 1 (outbound/round-26-lap-05.md).
- [x] Still owed by the operator, neither blocking: the T3 acceptance bundle
  (`platterpusbundle20260825t0217020000.tar.gz`) and the `cancel me
  platterpus-fork-gd9c058c.log` from the 2026-08-24 run. §A no longer depends on
  either — J1 is answered from code and measurement.
  - *Audit 2026-09-25: not ours to verify.* The operator's artifacts (the 2026-08-24 bundle and cancel log); neither is filed.
  - *2026-09-25:* **Withdrawn.** Neither artifact blocks anything, and the pairing they were for (d9c058c) is long superseded.

## Audit findings, 2026-08-20 — and one measurement limit worth knowing

- [x] **Updater followed an https→http redirect.** Fixed; see CHANGELOG Security.
- [x] **The tag escape had examples but no injection property.** Fixed with three
  hypothesis properties, sabotage-verified.
- [x] **The `-N` chokepoint was enforced at its two call sites and nowhere else.**
  Fixed with an AST-derived, two-way ratchet.
- [x] **A swallow-test that asserted nothing** (shutdown drive-free) now records
  the attempt.
- [x] **RETRACTED: "coverage cannot be measured in this dev container" was
  FALSE, and so was the sharpened version of it.** It can. Disproved by
  measurement 2026-08-20; both wrong versions are kept below because the way
  this entry was wrong is more instructive than the fact.
  **What is actually true**, all four measured in a fresh container:
  - `.coverage` **is** written (1,167,360 bytes), and `python3 -m coverage
    report` prints the whole table on demand. Current tree: **TOTAL 91.51%**
    branch coverage against the floor of 91 — so it passes, with 0.51 points of
    room.
  - `--cov-fail-under` **is** enforced locally, through the exit code. Proved the
    only way it can be proved — by making it fail on purpose:
    `pytest tests/test_app.py --cov=platterpus --cov-fail-under=100` exits **1**
    and prints `ERROR: Coverage failure: total of 20 is less than fail-under=100`.
  - pytest's own summary line prints (`4335 passed, 16 skipped … in 320.06s`),
    because `pytest_sessionfinish` deliberately calls `summary_stats()` itself.
  - the **only** thing skipped is pytest-cov's printed terminal table **on a
    passing run**, because `os._exit` fires in the sessionfinish post-yield
    before pytest-cov prints. The `conftest.py` comment says exactly this, in
    those words, and has said so all along.
  - separately and mundanely: `addopts = "-q --strict-markers"` carries no
    `--cov`, so a bare `pytest` measures no coverage at all. That is not a broken
    gate, it is an ungated invocation.
  **How the false version was reached, which is the part worth keeping.** The
  observation was *no coverage table, exit 0*. The proposed mechanism — `os._exit`
  skips the epilogue, so the floor is never evaluated — accounts for that
  observation completely. It is also wrong. **A passing gate and an absent gate
  produce the identical signature: exit 0 and nothing to look at.** So the
  observation could not distinguish them, and the inference was never evidence.
  This is `CLAUDE.md`'s first *"how to stop shipping the next one"* question —
  *did I reproduce the symptom, or only explain it?* — with the twist that the
  symptom was never reproduced because it did not exist. Two commands settled
  what a paragraph of reasoning got backwards.
  **What it cost, stated so the cost is not hidden:** the false limitation was
  written into this file, cited in a commit message, and used to retract two
  earlier commit messages that said *"green with the CI coverage gate"* — a
  retraction of a claim that, for any run actually invoked with
  `--cov-fail-under`, was true. Retracting a correct statement for a wrong reason
  is not a cheaper error than the reverse; it puts a false correction into the
  permanent record, where the retraction reads as the more careful of the two
  statements.
  **Graduated** to `docs/testing.md` as the general rule (an inference from a
  passing check cannot distinguish *passed* from *absent* — to claim a check is
  inert, make it fail on purpose). What remains actionable is only the small
  diagnosability fix, tracked in its own item below.

- [x] **Print the coverage table before the hard exit, for the same reason the
  test summary is already printed there.** Not a correctness fix — the gate works
  — a *diagnosability* one, and it has a measured cost: the missing table is what
  produced two successive wrong entries above. `pytest_sessionfinish` already
  reaches into the terminal reporter and calls `summary_stats()` itself, with the
  comment *"Diagnosability is the whole point of a test run"*; the coverage plugin
  can be asked to render in the same place. Then a local run shows its own
  coverage number and nobody has to infer one.
  - *Audit 2026-09-25: done.* 8b495a4: tests/conftest.py print_coverage_report, called before the hard exit; tested in tests/test_harness_fidelity.py.
- [x] **The colon safety net still awaits its hardware confirmation** — now
  obtainable, because section E's album title carries a colon deliberately. Look
  for a real `:` in the written tag, not `∶`.
  - *Audit 2026-09-25: done.* Observed on hardware: artifactsround26/round26fullacceptanceanglebracket.log shows `Album: full acceptance: angle<bracket`; CHANGELOG records the colon surviving into tags.

## Rig run 2026-08-20 (v0.6.19) — pass=58 fail=2, and the drive-open question ANSWERED

- [x] **Task #53's core question is answered: the cancel released the drive.**
  After the cancel, section E's `rescan` succeeded, MusicBrainz returned the disc,
  and 14 track rows loaded (`pick-release` in 10.8 s). That is the drive-open
  proof — a held reader cannot be re-read — and it is the first clean evidence for
  it in four attempts. What is still unproven is the *second rip completing*,
  because the run stopped on an unanswered modal before it started; the tray also
  stayed closed, which is the v0.6.16 rescue-timer behavior holding.
- [x] Both failures descended from one unanswered "Album already ripped" dialog.
  Fixed by the `answer-dialog` verb + the script's section E + the corrected
  advice `wait-for-rip` prints. Third consecutive run with a single-cause failure
  set, which is exactly what `docs/test-plan.md` Part E predicts.
- [x] The cancelled rip's FUN512 "rejection" and `rig-check`'s zero-track FAIL
  were both reports that were accurate word-by-word and wrong in kind. Fixed.
- [x] **NOT a defect, recorded so it is not re-investigated:** `worker thread
  DiscInfoWorker did not stop within 0ms — abandoning it` on every rescan is
  deliberate and heavily commented (`main_window.py`, the `wait_ms=0` call) — the
  old 2 s wait was a dead stutter on the GUI thread and `quit()` cannot interrupt
  a mid-read subprocess, so the probe is cancelled and abandoned by design. Only
  the log line reads like a fault. Consider phrasing it as an INFO that says
  "superseded by a newer probe" so a rig transcript does not carry a WARNING for
  normal operation.
  - *Done 2026-09-27:* `stop_thread(…, superseded_by=…)` logs a planned supersession at
    INFO (`workers/__init__.py`), and the rescan passes it (`ui/main_window.py`). All other
    abandonments stay WARNING. Tests: `tests/test_workers_init.py`,
    `tests/test_ui_main_window.py`. Revert-probed.
- [x] **Still unproven, and it needs the next run:** a *completed* second rip
  after a cancel, which is what exercises `rig-check`'s parser path against a real
  subject and what closes Task #53 outright.
  - *Audit 2026-09-25: done.* artifactsround26/round26aftercancelreport.json: success, exit 0, 2/2 tracks after the cancelled rip.

## Doc drift found 2026-08-20 — a stamp can be current while the prose is not

- Duplicate of **Rewrite `hardware-test-checklist.md` rather than patch it again** — merged 2026-09-30.

## Found in CI, 2026-08-20 — the crash handler was the crash — **FIXED in 0.6.19**

- [x] **The fatal-error dialog stacked on itself without limit.** `box.exec()` runs
  a nested event loop, so an exception escaping any callback while the dialog is up
  re-enters the excepthook and opens a second dialog inside the first one's loop.
  Nothing raises, so the handler's own `except` never saw it. Found from a
  faulthandler stack dump after three wrong hypotheses were each killed by
  measurement (PySide6 6.11.2: green locally; random ordering: `pytest-randomly` is
  not installed; a leaked test timer: fixed on merit, CI failed again identically).
  Reverting the guard makes the regression test die with `RecursionError`.
  `docs/testing.md` §5.ar.
- [x] **The unattended-quit timer could raise after its window was destroyed** — a
  PySide6 wrapper whose C++ side is gone raises on attribute access, from a timer
  callback, i.e. into the dialog above. This is what SUPPLIED the exception. The
  checklist question *what new state does this fix create* asked one day late.
- [x] **Seven tests left the product's excepthook installed** for the rest of the
  session (four the `--run-script` path through `main()`); three restored
  `sys.excepthook` and not `threading.excepthook`. `conftest.py` restores both now.
- [x] **A hang names itself.** `faulthandler_timeout = 300` +
  `faulthandler_exit_on_timeout`, bounded against a measured 275 s suite so it
  cannot fire on a slow-but-working test.

- [x] **An unattended `--run-script` run still blocks on its FIRST fatal dialog.**
  The re-entrancy guard stops the recursion, not the one dialog. On the rig that
  means a single uncaught exception parks the batch waiting for somebody to click
  OK — the same *"an unattended run needs no attendant"* principle as the quit
  timer, which the maintainer raised on 2026-08-19. Deliberately **not** fixed
  inside a release: it is a behavior change (when may the app suppress its own
  crash dialog?) and it deserves its own decision rather than being wedged in.
  Shape when it is done: the fatal dialog is non-modal — or auto-dismissed after a
  bounded wait with the reason logged — when the process was started with
  `--run-script`, and never when a person is driving.
  - *Done 2026-09-28, the maintainer's ruling that day ("auto-dismiss under --run-script"):*
    `app.py` `_arm_fatal_dialog_auto_dismiss` and `_show_fatal_dialog(..., unattended=)`,
    constant `UNATTENDED_FATAL_DIALOG_TIMEOUT_S` = 60, wired from `args.run_script`. Two
    QTimers on the box (no sleep), the reason and traceback logged and flushed before it
    closes, the re-entrancy guard held through the countdown, timers disconnected so the
    box is freed. Tests in `tests/test_app.py` through the real nested `exec()`;
    revert-probed 10 of 10. Open: a launch by the saved config's autorun also runs a script
    unattended and still waits for a click (the hook is installed before the config is read).

## Found on the rig, 2026-08-19 — the v0.6.17 pass — **FIXED in 0.6.18**

Every item here was found by **reading the maintainer's uploaded artifacts** (three
report bundles and the terminal transcript), not by the suite. Three of the five are
defects in the bundle feature 0.6.17 shipped the day before — the bundle's own
manifest is what proved the bundle wrong.

- [x] **The bundle sealed before the verification it exists to carry had landed.**
  0.6.17 joined one post-rip handle of six and then asserted *"post-rip processing
  finished first"* in the manifest. Measured off the upload: sealed `22:20:02.314`,
  FLAC verify `22:20:02.680`, CTDB `22:20:03.106`; the archived report carried
  `checksums: null, ctdb: null, audio_md5: null`. Now a GUI-thread settlement poll
  gated on `_post_rip_work_settled` — the predicate the library move already used.
- [x] **A deliberate 1-track rip was archived as `partial`**, because the denominator
  was the disc's 14 rather than `RipParameters.only_tracks`. The same rip's banner
  read *"all 1 tracks verified against AccurateRip"*.
- [x] **`(ripper)` stopped expanding after any later `cyanrip` step**, because it read
  `_last_cyanrip_output` — a field `expect-cyanrip`/`expect-exit` invalidate on
  purpose. The cache probe's timeout wiped the banner, both `album … (ripper)` steps
  failed, the rips fell back to the default album title, and a cancelled rip's FLACs
  landed in the disc's real album folder. **That is the overwrite prompt the
  maintainer flagged — the dialog was correct.** The tag is now latched in its own
  field. `CLAUDE.md` + `docs/testing.md` §5.aq.
- [x] **The script `rip` verb could start a second rip behind an open modal** — both
  its guards pass while the overwrite confirmation is up, and Qt ticks the runner
  inside the modal's nested loop. It now refuses and names the dialog;
  `wait-for-rip` names the blocking modal too.
- [x] **`expect-tracks 3` / `1` failed every run against the 14-track disc.** The
  script promises to need no editing on any disc, so no exact number could work. Added
  an at-least form: `expect-tracks 3+`.
- [x] **The bundle was unbounded in memory and on disk** — six log rotations each
  permitted 16 MiB, all held at once, and nothing ever pruned the folder. Now
  streamed one file at a time, 64 MiB payload cap with every over-budget file named
  in the manifest, newest 20 bundles kept.

**And the headline hardware finding, which is an ask on the fork rather than a fix
here:** `cyanrip -x` printed `Cache probe: 32 sectors, 73.5 KiB, uncached read
362.6 ms` **and then ripped the whole disc** (ETA 1h 3m). Killed at 300 s, child
unreapable, drive held for the two rips that follow — the most likely reason round 1's
evidence came back unusable. The step is removed from the script until `-x` exits
after measuring. This also corrects the script's own 2026-08-18 claim that the probe
"costs SECONDS".

- [x] **`--rig-session` ran the same `-x` call, and that is a second call site of one
  fix.** `rig_session.sh` step 5a is what a person runs *after* a rig pass, so it spent
  five minutes re-ripping the disc into its own scratch directory and left the drive
  held for every step after it. Fixing the rig script alone would have left the harness
  doing the damage — `docs/testing.md` §5.o, *enforce a rule across the codebase, not at
  the place it was learned*. Found by grepping for the call.

- [x] **SENT and ANSWERED.** Carried in `outbound/round-13-lap-02.md`; the fork
  answered in their round-13 lap 1 §B6 — *"`-x` — ANSWERED ALREADY, and the answer
  is a second flag"*: `-x` is a modifier that proceeds into a rip, `-x -I` is the
  probe-only form, and they declined to change `-x` alone. Original wording kept
  below as the record.
  ~~Send the `-x` finding to the fork as round 12 lap 1 — NOT before pass 2's~~
  bundle exists.** The finding is real and theirs to fix, and it is tempting to open a
  round on it today. Don't: opening round 12 now closes the release door (deviation
  policy) *and* creates a round whose close condition cannot be met without hardware
  evidence we do not have — the S-13 failure that ran round 7 to 37 laps. The
  measurement is recorded in `docs/dependency-contracts.md` (single home), the rig
  script and `docs/rig-scripts/README.md`; it travels when the round opens. All eleven
  rounds are CLOSED as of this commit, so the release gate itself is clear.

- [x] **The 13 `QLabel(<non-literal>)` sites are outside the PlainText sweep.**
  `tests/test_message_boxes_are_plaintext.py` covers `QMessageBox`: the functions
  that construct one (10 sites, all pinned) and, since 2026-09-28, Qt's static
  helpers too, which it refuses outright (the 38 calls it had never seen now go
  through `ui/message_boxes.py`, which pins PlainText). These are not covered, and the reason is honest rather than principled:
  most build their text from our own constants, so a blanket rule would need a long
  allowlist, and an allowlist that fills up enforces nothing. Assess them
  individually and pin the ones that carry external text:
  `ui/dialogs/manual_install.py:70,75,76,77,92`, `ui/disc_info_panel.py:290`,
  `ui/drive_setup_dialog.py:173,177,193`, `ui/help_dialogs.py:72`,
  `ui/host_setup_dialog.py:140`, `ui/release_picker.py:67`,
  `ui/settings_dialog.py:248`. **`release_picker.py:67` first** — a release picker
  renders MusicBrainz artist/title directly, which is the exact case Critical rule
  #12 names.
  - *Done 2026-09-28, in the commit `fix(ui): make every label built from data state
    its text format`:* no allowlist. Every `QLabel(<non-literal>)` now STATES its
    format right after it is built, and `tests/test_labels_state_their_text_format.py`
    refuses one that does not (floor 15; it found 17, not 13). **PlainText (14):**
    `ui/dialogs/manual_install.py` Required, Currently, Why manual and the search-field
    caption; `ui/drive_setup_dialog.py` intro and device path; `ui/help_dialogs.py`
    logo (a picture, stated anyway); `ui/release_picker.py` intro; and six already
    pinned (`ui/dialogs/setup_center.py` x3, `ui/disc_info_panel.py::_value_label`,
    `ui/ripper_picker.py` `choice.why`, `ui/settings_dialog.py` offset status).
    **RichText with escaping (3), kept rich because each renders a `<b>` of ours:**
    the manual-install intro (`html.escape` on the dependency's display name), the
    drive wizard's known-offset line (the drive's vendor/model), and the setup
    wizard's intro, whose markup `SetupCopy.intro` is written by its callers: the
    ripper update escapes the build pin, and the test checks every builder. Rendered
    output was compared before and after on 546 labels across those dialogs: no
    change on ordinary input. The release picker's MusicBrainz fields were never in
    a label: they are table cells, which draw text as written (measured: a
    `<b>WWWW</b>` cell is 113 px wide against 54 px for `WWWW`). **Not covered, and
    still open:** labels built empty or from a literal and given a value later by
    `setText` — 13 counted, 8 of them in `ui/rip_progress.py`. Also found: the setup
    wizard's intro renders as markup, so its bullet list has always shown as one
    paragraph; kept as it was here, since this change was not to alter output.
  - *Tightened 2026-09-28, after a second-round review:* the escaping test used to
    pass a RichText site whose function called `html.escape` once, on anything. It
    now judges each value in the markup (an `html.escape(...)` call, a number with
    a numeric format, a literal of ours, or a name bound only to those, traced
    through assignments and into the helper that builds the markup), and the
    `SetupCopy` builders the same way. The three sites already passed. The same
    review found a LITERAL label showing its own tags: the uninstall dialog's intro
    held `<b>Never touched:</b>` below a first line with no tag, so AutoText showed
    it as plain text. Fixed (RichText, `<br>` for its line breaks), and the sweep now
    also holds a literal label whose markup Qt would not see to stating its format.

- [x] **Labels given their text by `setText` after they are built are outside both
  format sweeps.** `tests/test_labels_state_their_text_format.py` holds every
  `QLabel(<non-literal>)` to stating its format, but a label built empty or from a
  literal and filled later with `setText(<value>)` is not seen: 13 counted on
  2026-09-28, 8 of them in `ui/rip_progress.py`, which shows rip status built partly
  from cyanrip's output. The count is an approximation and may be low. Also found
  the same day: the setup wizard's intro is markup, so its bullet list has always
  rendered as one paragraph.
  - *Done in adc04a08:* `tests/test_labels_given_text_later_state_their_format.py`
    traces every `setText` / `setInformativeText` (and a `setText` passed as a slot)
    back to where its widget is built, with `ast`: through `self.<attr>` across a
    mixin family, a helper that returns the label, a dict of labels, `isinstance`,
    and a Qt accessor by its return type in PySide6's own stubs. Measured: 115
    setters, closed by a second count with `tokenize`; 55 give a label a value, from
    20 construction sites, of which **14** stated no format (the row's 13 was one
    low): the 8 in `ui/rip_progress.py`, the setup, uninstall and drive wizards'
    status lines, each Pending-installs row, and Settings' validation banner and
    filename preview. All 14 now state PlainText. The 2 receivers the resolver
    cannot trace are listed in `_UNRESOLVED`, a ratchet capped at 2. The setup
    wizard's intro list, and the update wizard's paragraphs, break with `<br>` since
    aa3c9ee6. **Still not swept, and said so in the file:** `setToolTip` and wizard
    page titles, which guess their format too. **Waiting on the maintainer:**
    CLAUDE.md Critical rule #12 still says a label filled later by `setText` is
    outside both sweeps; that sentence is in the locked rules section, so its
    replacement is proposed, not made.

- [x] **DELIVERED in round 12 itself** — `inbound/round-12-lap-01.md` §B2,
  *"`--verify-log` should separate absent from mismatched — [MEASURED], done"*.
  ~~A second round-12 ask, rides with the `-x` one: `--verify-log` should separate~~
  *absent* from *mismatched*, and the discriminator should be an exit code.** Target
  **NEXT-ROUND** per S-16 — it breaks nothing in any artifact under review, so under
  S-14 it is not grounds to hold anything. What v0.6.20 had to do: a killed or cancelled
  rip leaves a log with **no** `Log FUN512:` footer at all, while an altered archival
  record leaves one that does not match, and *"the ripper was killed mid-write"* and
  *"this file was modified"* are different findings — only the second is a tamper claim.
  Their tooling today reports both through message text, and their own lap-12 J4 asked us
  **not** to key on genopt's `"No FUN512 checksum found"` string because one upstream sync
  can change it. That left us correct but unaided: we derived the distinction from our own
  read of the log (`parsers/cyanrip_log.has_log_checksum`), which works and is the right
  local fix, but means two projects now answer the same question by separate routes — the
  *"do two surfaces answer this question, and do they use the same key?"* shape. The ask
  is a **machine-readable discriminator** — distinct exit codes for absent vs mismatched —
  plus the null case (no footer) stated explicitly in their provider contract, since a
  null case left silent is one of the two failures `--check` is written to catch.

- [x] **SUPERSEDED.** The compromised-evidence fact stands as the record — two rips
  mixed in one folder, `--verify-log` rejecting the album log — and it is *why* the
  `(ripper)` album-title expansion exists. But the re-run it asks for is against
  0.6.18, twelve minors behind; the live acceptance queue supersedes it.
  ~~Round 1's evidence is compromised; pass 2 has not been started.~~
  `cyanrip --verify-log` rejected the album log (*"checksum mismatch, the file has
  been modified!"*) and `rig-check` FAILed *"parsed … to ZERO tracks"* — the folder
  mixes two rips. Task #53 still has no clean cancel/drive-open proof. Re-run on
  0.6.18.

---

## Found on the rig, 2026-08-18 — the run that failed 8 steps to one line — **FIXED in 0.6.17**

The run (`20260819T000808+0000`, app 0.6.16, pin `platterpus-fork-gddf7ac3`) finished
`pass=50 fail=8`. All eight descend from one defect; the rest of the script was fine.
`rig-check` passed on both halves it can answer: `OK ripper/handshake approved` and
`OK argv/integrity — -Z, -l, -N, -s present in the binary's own record of 26 composed
args`.

- [x] **`pick-release` passed 124 ms before the tracks existed.** `_fetch_release_detail`
  emits to the MusicBrainz worker thread, so accepting the dialog is when the work is
  *requested*. The verb now waits for the track table. `docs/testing.md` §5.ap.
- [x] **The disc panel never stopped saying "N matches found — pick one"** after the
  user picked one. Cosmetic, and it is what made the first diagnosis of the above
  wrong — it reads exactly like a release choice that never applied.
- [x] **The cache probe ran with no `-s`**, so cyanrip refused to open the drive and
  the flag's first-ever hardware run measured nothing, twice. Now `-s 0`.
- [x] **The AppImage integration dialog opened four seconds into an unattended run**,
  failed the step in flight, and was answered by the script's next click — relocating
  the running AppImage out of `~/Downloads` mid-batch. No first-run offers on a
  scripted launch.
- [x] **`hardware-test-checklist.md` H10 told the operator to enable overread**
  on the BDR-209D, calling the flag `-x` and saying the drive was *"expected to be
  fine"*. It is measured to hang that drive for ~23 minutes. Now ⛔ BLOCKED, needs a
  different drive.
- [x] **The `-x`/overread doc gate derives its file list from disk** (4 files → 60).
  It could not see `PLANNING.md`, which carried the sentence it was written to stop.

- [x] **The two-pass album-name collision — FIXED in 0.6.17, and it was the one step
  that had resisted automation.** Both rip sections used fixed album names
  (`cancel me`, `after cancel`), so running the script twice — once on `ddf7ac3`,
  once on `c4d1a00` — wrote both passes into the same two folders and pass 2 landed
  on top of pass 1. The workaround was telling the operator to `mv` the pass-1
  folders aside, which is work handed back and exactly what `CLAUDE.md` forbids.
  **Fixed as a script capability, not a flag** (maintainer directive, 2026-08-11):
  `album` / `album-artist` expand **`(ripper)`** to the installed ripper's build tag,
  read from the `cyanrip --version` banner section A already captures. Pass 1 writes
  `cancel me platterpus-fork-gddf7ac3`, pass 2 `cancel me platterpus-fork-gc4d1a00`.
  An unresolvable placeholder FAILS the step rather than writing the literal text,
  because a silent non-expansion restores the collision while looking like it worked.
  Spelled to match the `(track) - (title)` placeholders we already hand cyanrip.

**Not fixed by this, and it is why the rig has to run again:** the race killed sections
D and E before they ripped anything, so **task #53 has no cancel/drive-open evidence
yet**. The 0.6.17 re-run did not close it either — see the 2026-08-19 section above,
where `-x` held the drive for the rest of the pass. Re-run on 0.6.18.

- [x] **Provenance labels disagree across three surfaces — next round, not blocking
  (S-14).** Our manifest says the build was approved by *"round 8 … for Platterpus
  0.6.12b6"*; the binary's own `argvprobe.json` says *"round 7 lap 39 closed, verdict
  GO"*; `--install-ripper` says *"the round-7 release … see round-07-lap-40"*. All
  three are defensible — `ddf7ac3` was approved in round 7 and carried into 8 — but
  three answers to one question is the shape `CLAUDE.md` warns about, and the recorded
  approval names app **0.6.12b6** while the rig runs **0.6.16**, which rule #12's
  obligation (3) makes a real (if minor) scope gap.
  - *Audit 2026-09-25: superseded.* Concerned ddf7ac3; the pin is df91ae7, no round-07-lap-40 string remains in src, and round/app version come from the record.

---

## Queued for the rig, 2026-08-18 — two passes, and a gap the plan exposed

**v0.6.15 is published**, so the hardware round (item 3 / task #53) is unblocked.
The plan is **two passes of the same script on two ripper builds**, because the two
open questions are different questions:

- [x] **SUPERSEDED — `ddf7ac3` has not been `FORK_PIN` since round 14 closed
  (GO/GO on `d9c058c`, 2026-08-27; hardware evidence 2026-08-26).** The pin is now
  `d9c058c` = `0.9.4-rc2+platterpus.10`, approved for Platterpus 0.6.28.
  ~~Pass 1 — `ddf7ac3` (our `FORK_PIN`, `0.9.4-rc1+platterpus.5`). Closes the two~~
  `[NOT PROVEN]` items — `-x` on a real drive, and the drive-open fix on cancel — for
  the build **we ship**. Reports must say `approved`. This is what unblocks `v1.0.0`.
- [x] **Pass 2 — `c4d1a00`** (the fork's current published stable, seq 16,
  `0.9.4-rc1+platterpus.6`). Becomes **round 12's lap-1 evidence**, which is what a
  pin move needs and what round 11 explicitly did not have: its own header records
  *"NOT tested: an actual build or install of +platterpus.6 — that needs the container
  and the rig."* Reports will say `unapproved`, which is **correct** — our record
  approves `ddf7ac3`, and a build it has not approved must be stamped as such.
  - *Audit 2026-09-25: superseded.* The pin has moved through rounds 12–26 to df91ae7.
- [x] **Restore `ddf7ac3`** afterwards, so the rig is left on the shipping build.
  - *Audit 2026-09-25: superseded.* ddf7ac3 is no longer the shipping build; FORK_PIN is df91ae7.

**No handshake round is opened until pass 2's bundle exists.** Opening round 12 first
would close the release door (deviation policy) *and* create a round whose close
condition cannot be met — the S-13 failure that made round 7 run 37 laps.

### The gap this exposed: the rig script cannot say which pass it is

- [x] **`rigcancelandoverread.txt` wrote to fixed album names — FIXED in 0.6.17.**
  A second pass landed **on top of** the first pass's rip folders. The mitigation was
  ordering rather than code (`--rig-session` bundles the newest report by mtime, so it
  always caught the *right* pass — but pass 1's raw artifacts were gone once pass 2
  ran), which is a procedure holding a correctness property: the shape this project
  keeps paying for.

  Closed by the `(ripper)` placeholder above — the installed build tag lands in the
  album name automatically, which is exactly what distinguishes the two passes. Per
  `CLAUDE.md` this went in as a **script capability, not a flag**. The sibling
  `police-rerip.txt` still makes the operator hand-edit its `album` line and can adopt
  the same placeholder whenever it is next touched.

---

## Found on the rig, 2026-08-12 — the round-8 script run that never reached the rip

Three defects, all ours, all found by a real hardware run of
`src/platterpus/rig_scripts/round08joint.txt` on the Bazzite + BDR-209D rig. The run
scored 62 pass / 10 fail and **the rip never started**, so it produced no round-8
evidence — but it produced these.

**All three are fixed and shipped in v0.6.12b2** (2026-08-13), together with a
fourth the fork reported separately (`expect-cyanrip` could not express a string
containing a double quote). Boxes ticked below with what each turned out to be —
kept rather than deleted, because the *diagnosis* of the first one is the part
worth re-reading and it is not what the symptom said.

- [x] **BLOCKER — the disc scan is killed by a 0 ms grace, so no disc identifies
  and no rip can start.** *Fixed in 0.6.12b2 — and the 0 ms was innocent.*
  `DrivePicker.set_drives` re-emitted `drive_changed` when a repopulate restored
  the **same** device, which is a no-op by definition; the second emission four
  seconds into launch superseded a healthy scan for no reason. Superseding really
  does need to be immediate (a probe blocked in `subprocess.communicate()` cannot
  be asked politely to stop), so the wait is unchanged. **When a mechanism is
  correctly violent, audit its trigger, not its force** — the second of the two
  questions below was the wrong one to fix, and fixing it would have left the
  scan still cancelled and restarted, just more slowly. Original notes: `drive changed: /dev/sr0` fires **twice** during
  startup (02.978 and 06.823 in the rig log); the second cancels the in-flight
  `DiscInfoWorker`, which is then abandoned with *"did not stop within 0ms"* and
  its cyanrip child is SIGKILLed mid-TOC-read — surfacing as
  `cyanrip failed (exit -9) with no output`. Start rip stays disabled, so
  `rip` fails with *"the Start button is not enabled"* and the whole unattended
  run is lost. A **zero**-length wait is the same family as `CLAUDE.md` rule #9's
  *never hand `QThread.wait()` a negative number*: no grace at all is not a
  bounded wait, it is a kill. Two questions to answer together — *why does the
  drive-changed signal fire twice from one startup*, and *why is the cancel
  budget 0 ms*. Fixing only the second leaves a scan that is still cancelled and
  restarted for no reason. Present in 0.6.11 and 0.6.12b1 alike.

- [x] **A refused `cyanrip` step leaves the PREVIOUS invocation as the comparison
  subject.** *Fixed in 0.6.12b2: a refusal now clears `_last_cyanrip_*`, so the
  following assertion reports "no cyanrip command has run yet".* On the rig, `L260` was refused (the `-t 1` guard) and `L261`'s
  `expect-cyanrip` then compared against the output of `-p ==`, two commands
  earlier; same at L283/L284 and L315/L316. It failed loudly this time, which is
  luck — the stale command could just as easily have contained the expected
  string and reported a **pass for a step that never ran**. That is the
  *satisfied by the wrong thing* shape, inside the surface this project's tests
  are written in. A refusal must invalidate `_last_cyanrip_*` so the following
  assertion fails as *"no cyanrip ran"*.

- [x] **`expect secure_rerip_dynamic True` measures the operator's config, not
  the behavior.** *Fixed in the script, not the code: B2 now `set`s both fields
  before asserting them. Still to correct to the fork in lap 10.* Failed on the rig (`got False`) because that install has it
  off. Round 8 lap 8 §J9 told the fork "both defaults are what B2 asserts, so B2
  passes on a default install" — accurate about a *default* install and useless
  about this one. A test that asserts a setting it did not set is testing the
  machine. Either `set` it first, or asserting it is the point and the script
  should say which. Correct this to the fork in lap 10.

- Duplicate of **F6. The ripper install surface** — merged 2026-09-30.

- Duplicate of **G9. Rig hygiene** — merged 2026-09-30.

## Leaving beta — the standing objective for every round from here (set 2026-08-15)

**The maintainer's words, both halves, because only the pair is the instruction:**

> *"our goal is to get us out of beta and into a user release testable release,
> if possible, as soon as we can, make sure that is clear in all handshakes and
> objectives."*
>
> *"but not at the expense of quality, functionality, or reducing bugs."*

This is not a licence to lower the bar and it is not a date. It is the
correction round 7 already diagnosed and neither project has yet applied to
itself: **release-grade rigour was being attached to the *round* rather than to
the *release*.** The rigour stays. What ends is a round that cannot terminate
because every finding it makes is a reason to extend it.

Named in `docs/handshake/verified/round-08-lap-10.md` §A so the fork holds the
same objective; it must appear in every lap we write from here. *(2026-09-30: it has
not appeared in any of our laps since round 28 lap 6 S38; tracked in row G12.)*

- [x] **Round 8: declare `GO` on `ddf7ac3`.** Done — lap 10, 2026-08-15. Our half
  only: the round stays OPEN until their lap 11 declares `GO`, and `handshake.py
  --status` enforces that.
- [x] **Name what `v0.6.x` final needs, and keep the list closed.** Same
  discipline as S-13: fix the conditions once, do not let them grow. This is a
  *different and much shorter list* than the `v1.0.0` one below — 1.0 claims
  stability across drives and machines nobody has tested; leaving beta claims the
  build is good enough for a user who is not the maintainer to run on the
  hardware we do support.
  - *Audit 2026-09-25: superseded.* The maintainer's ruling set the gate: 0.7.100 needs a full pass with zero ARCHIVAL failures (docs/testing.md → Acceptance severity).
- [x] **Every defect from here is triaged against the release, not the round.**
  S-14 applied inward: a finding blocks the beta exit only if it names what it
  breaks for a user of the build. Everything else ships in the release after.
  - *Audit 2026-09-25: superseded.* Replaced by the per-test severity classification declared in advance (docs/testing.md, swept by tests/test_rig_scripts.py).

## When their lap 9 arrives — everything our lap 10 must carry (staged 2026-08-15) — **DONE, lap 10 sent**

**Kept, not deleted.** Every row below was written before the lap and is ticked
with what it turned out to be; the staging notes are the part worth re-reading if
round 9 needs the same preparation. The gate that mattered — *do not write lap 10
before their move* — was satisfied by their round-8 state document, which
explicitly asks for our lap 10 and reports their laps through 13.

- [x] **Settle the expired close-by date FIRST.** *Their lap 13 ruled it spent
  and not extended, citing our own S-13 against their lap 9's extension. Lap 10
  §D accepts without amendment.* Our lap 8 §J1 accepted
  `HANDSHAKE-CLOSE-BY: 2026-08-14` *"Accepted, unchanged"*. That date passed with
  the round open. Under S-13 a close condition fixed at lap 1 cannot be
  *extended*, which is exactly the rule written after round 7's 37 laps — so
  this needs a joint decision, not a unilateral reading by either side. It is the
  first thing lap 10 addresses.

- [x] **Hold the pre-commit exactly as written.** *Held. None of the three
  escape conditions fired, so lap 10 is `GO`.* Lap 8 §E: *"Our lap 10 is GO on
  `ddf7ac3` unless"* (1) their lap 9 moves the pin, (2) they raise a finding that
  makes `ddf7ac3` **itself** unsafe (S-14 — name what it breaks in the artifact
  under review), or (3) they would rather we made the two SECTION C edits.
  **Nothing else.** §C2, §C3 and §C5 were pre-committed to round 9 precisely so
  they could not quietly become blockers; honour that even if lap 9 revisits them.

- [x] **Carry hardware evidence on `ddf7ac3` — the gap that would otherwise make
  lap 10 dishonest.** We pre-commit to GO on `ddf7ac3` and our only rig rip is on
  `g2ce8993` (`docs/handshake/artifactsround08/`, which says so in its README).
  Signing off a build nobody ripped with is what Critical rule #12 exists to
  prevent. The rig is now on `ddf7ac3` and reporting `OK ripper/handshake
  approved`, so this is one disc. **Rip AFTER their lap 9 confirms the pin**, not
  before — a rip on a pin they are about to move is wasted.

- [x] **Report the loss of `~/rigsession/` (2026-08-14) plainly in lap 10.**
  *Lap 10 §G, unhedged.* Their
  round-8 state document §10.4 asked for it to be kept regardless — *"it is the
  only evidence of the drive-open hang and cannot be re-taken."* It is gone from
  the operator's machine, confirmed by a `find` across `$HOME` on 2026-08-15, and
  no copy was ever uploaded to us: the bundle we hold contains the ui-script run,
  not the rig-session artifacts. **It was not our archive command** — that moved
  nothing (its target directory is empty) and never named `rigsession` at all.
  Say so without hedging: an artifact the other side asked us to preserve was
  lost on our side. It does not block the round — the drive-open hang is their
  finding, fixed on their side at `5869977`, and its status was already *"needs
  your rig"* — but a quiet omission here is exactly the failure both projects
  keep writing rules against.

- [x] **Answer their reply to our two §F questions** (both `NEXT-ROUND`): whether
  their `HANDSHAKE-PROTOCOL: 2` proposal changes the field set we are already
  emitting, and whether they hold round 8 laps 3–7 for us to commit as inbound.

- [x] **Report what shipped since lap 8**, with the pin unchanged: v0.6.12b6;
  the pre-install build-tag guard (a wrong build is now refused *before* `sudo
  install` and `distrobox-export`, so a failed check no longer leaves the wrong
  ripper exported); our own argv now logged at startup; `--install-ripper list`.
  None of it touches SECTION C or the pin.

- [x] **Hand over the former `cyanrip-known-issues.md`** (now `docs/cyanrip-fork.md` Part E) — ten verified findings, and
  §10b's three questions about listing their builds. It is deliberately not a lap
  and must not be counted as one; say so when sending.

## Found on the rig, 2026-08-15 — two `--install-ripper` observations

Both surfaced while an operator moved the rig between pins during round 8.
Neither made a build unsafe, so both are **NEXT-ROUND under S-14**.

- [x] **Verify the built binary *before* installing it, not after.** The build
  script's order is build → install → export → verify, so
  `sudo install -Dm0755 …` overwrites `/usr/local/bin/cyanrip` and
  `distrobox-export` rewrites the host wrapper *before* `verify-cyanrip-fork`
  compares the banner's build tag. A failing verify therefore reports the
  problem correctly and leaves the wrong ripper installed and exported, with no
  rollback — the guard meant to be the last word runs after the irreversible
  step. **Not demonstrated on the rig**: the 2026-08-15 pin change was an
  explicit `--install-ripper 2ce8993`, not a failed verify, and every verify
  observed has passed. Filed as a latent ordering hazard, not a sighting. The
  fix is nearly free because the build step *already* reads the banner off the
  binary it just produced (`platterpus: built banner=…`) — the comparison can
  move there, leaving the post-install verify as a second, cheaper check that
  what landed is what was checked.
  - *Audit 2026-09-25: done.* 2180e85: the build script refuses a wrong banner before installing (deps/fork_source.py).

- [x] **`--install-ripper` prints its own shell scripts to the terminal.** The
  step engine logs each container command at INFO, and the fork build/install/
  verify steps *are* multi-line `sh -c` scripts, so a routine install dumps
  roughly a hundred lines of shell source between the progress rows. It is
  excellent diagnostics and poor terminal UX, and the two are separable: keep
  the full script in the log file, print a one-line summary to the terminal.
  The maintainer's standing bar — *"at the end of the day people need to use
  it"* — applies to a command an end user is told to run during setup.
  - *Audit 2026-09-25: partly done.* 2180e85: one_line_argv collapses the script to one escaped line for the step view, but the console log still gets the whole script.
  - *Done 2026-09-27:* `deps/step_engine.py` `console_argv` for the start, timeout and
    failure lines, and `logging_setup.console_summary` + `_ConsoleFormatter`, which formats
    a COPY so the file and the session buffer keep the full command. Tests: end to end
    through the real handlers in `tests/test_logging_setup.py`.

## Ripper install: find the newest build automatically, and let the user pick its channel (2026-08-07)

**The maintainer's ask, verbatim:** *"in the future it should be automatic that it
looks for the most recent version, and give an option between a full release and a
beta/alpha."*

Prompted by having to hand-correct the pin twice in one day — `9048082` → `422d12a`
→ `ddf7ac3` — each time by editing a constant and cutting a release. The pattern is
real and the ask is right.

**The constraint that shapes the design, stated first because it is the whole
difficulty:** the pin is not a convenience, it is the handshake's subject. A round
approves a *named commit* for a *named app version*, `handshake_approval.py`
verifies every rip against it, and the deviation policy forbids moving it while a
round is open. **An installer that silently fetched "the newest" would defeat the
protocol both projects spent 41 laps building.** So the automation cannot be "keep
up to date"; it has to be "notice, and offer."

- [x] **Detect that a newer fork build exists, and say so.** Done via the fork's
  published `release-manifest.json` rather than the GitHub API + `meson.build` read
  sketched here — they publish the sequence, the channel and the round state as
  facts, so nothing has to be inferred. (`deps/ripper_manifest.py`, 2026-08-07.)
- [x] **A channel choice that mirrors the app's own.** `config.ripper_channel` =
  `stable`|`beta`, Settings → Updates, same vocabulary as the app's own.
- [x] **Every non-approved install must be visible in the artifact.** Still holds
  for an automatically-resolved build — that path is now taken and tested.
- [x] **Install it, on one click, when it costs nothing** *(2026-08-18, and it goes
  further than this section asked)*. The maintainer's later instruction was
  explicit: *"the autoupdate on platterpus should take the next viable candidate
  without the user needing to pick … it shouldnt need to be explicity callled out by
  eitether rop unless very impartant"*, and *"assume last most stable is good, then
  if beta flags are checked, look for those, but it should still be an autoupdate."*
  **The constraint above is not weakened, it is what draws the line:**
  `RipperOffer.auto_installable` is true only for a build **our own record**
  approves, so the one-click path can never move a user onto an unverified build —
  which is exactly what *"do not make any of this the default"* was protecting. A
  build no round here has verified keeps the old treatment: consequence stated,
  never the default action, `--install-ripper <commit>` handed over.
- [x] **`--install-ripper latest` / `latest-beta`**, resolving the newest commit
  from the manifest instead of requiring a sha. **Still open, and now lower
  priority**: the GUI covers the case a person hits, so this is for a *script* that
  wants "whatever the channel says" without pinning. A resolver in front of
  `target_for_commit`, not a new install path.
  - *Done 2026-09-27:* `deps/ripper_latest.py` `resolve_latest` / `resolve_keyword`, a
    resolver in front of `target_for_commit`, called from `app.py`. The default is
    unchanged (a bare `--install-ripper` builds the approved target and touches no
    network), and an unreadable manifest refuses with exit 1 rather than falling back.
    Tests: `tests/test_ripper_latest.py` (including agreement with the GUI's offer) and
    `tests/test_app.py`.

**Do not** make any of this the default. The default stays: install what a closed
round approved. The automation's job is to stop the *maintainer* hand-editing a
constant, not to move users onto unverified builds.

## What v1.0.0 needs, named before anyone is tempted to declare it (2026-08-07)

**S-17 applied to our own versioning.** Round 7 took 38 laps because its evidence
was *"a rip"* — not a thing anyone can be finished with. The maintainer declined
1.0 for a precise reason and it should not be left in a chat log:

> *"we've only had my hardware and a small amount of albums yet."*

`v0.6.4` is honest about what it is. `v1.0.0` is a claim of stability, and the
evidence for it does not exist yet. Naming it now means nobody has to argue about
the finish line later — and if any row turns out to be the wrong bar, that is a
decision to take deliberately rather than by drift.

- [ ] **A disc sample with the awkward cases in it, not just more of the same.**
  Currently: a handful of pressed, AccurateRip-listed, single-disc albums. Missing
  and each one exercises different code: a **CD-R** or an obscure pressing (not in
  AccurateRip — the "no consensus to converge toward" path), a **multi-disc set**
  (`-c`, DISCNUMBER/totaldiscs), a **various-artists compilation** (per-track
  artist naming), a **genuinely damaged disc** (the read-speed ladder and the
  unresolved-track flagging, never once exercised), a disc with **CD-TEXT**, and a
  **pre-emphasis** disc.
  - *Audit 2026-09-25: not ours to verify.* Disc coverage: no CD-R, multi-disc, VA, damaged, CD-TEXT or pre-emphasis evidence in the record.
  - **Triaged 2026-11-16 (hardware):** R124 item (6), the disc corpus, carries most of it (damaged, pre-emphasis, CD-Text, CD-R, a disc AccurateRip does not know); a multi-disc set and a various-artists compilation are not in it. One damaged disc has been read (R49).

## Open, from the b15 reachability sweep (2026-08-06)

- [ ] **Sweep the rest of `src/` for unreachable subsystems.** Two were found in one
  afternoon by asking *"does anything outside this package import it?"* — `uiscript/`
  (no menu item, no flag) and `rig_session.sh` (in `scripts/`, so absent from every
  built artifact). Neither was caught by a green suite, because a subsystem's own
  tests import it directly. Run the same question over every package and data file:
  `grep -rn '<pkg>' src/ --exclude-dir=<pkg>`, and for data, check
  `[tool.setuptools.package-data]` rather than the filesystem. Rule: `docs/testing.md`
  §5.ag.
  - **Triaged 2026-11-16 (open, ours):** no gate yet; the 2026-10-12 ad-hoc sweep found none.

- [ ] **Build D6 C: descriptive preset names, and a separate line for state no preset
  owns.** Rename the Goal presets in the Settings label to say what they produce (e.g.
  "FLAC – lossless archival master"), and add one line under the Goal row naming state
  outside every preset, e.g. "Debug logging is on" or "A test script runs at start".
  Keep the stored goal IDs unchanged, so old configs and past reports still read; only
  the labels change. The label must stay true to the preset alone: a sweep that no
  label names a field the preset does not set. Update the in-app guide and the docs
  that quote the old names in the same change. *Decided 2026-09-25 (D6 C).*
  - **Triaged 2026-11-16 (stale but open):** the labels have been descriptive since `5f16b997` (0.6.4b11; `goal_presets.py:138-148`). Still missing: the line under the Goal row for state no preset owns, and the sweep.

- [ ] **Consider surfacing the `[plan]` block in the UI, not only the log.** It goes to
  the live log pane today, which is right during a rip but is not where someone decides
  whether to *start* one. A one-line summary beside the Start button ("Test & Copy: off
  — only AccurateRip misses re-read") would put it at the decision point. Deferred, not
  dropped: it needs a place in the layout that does not push the track grid around.
  - **Triaged 2026-11-16 (open, ours):** not built; nothing in `ui/` shows the `[plan]` block outside the log.

## P1 — backlog (do not start until P0 ships)

P0 shipped 2026-06-01 (v0.1.0), so this backlog is now the active queue; the fence below is kept for the record of how the sections were ordered.

The sub-sections below are ordered by current priority for picking up work:

1. **P1.1 — Install / uninstall ease** is the **highest priority subset** of P1. Items here unblock new contributors at the install step; finish before anything else P1.
2. **P1 — Release milestones** — gating actions for v0.1.0. Merging to main, flipping the repo public, tagging the first release, publishing to PyPI. Most other P1 items remove caveats from the README once these are done.
3. **P1 — EAC bit-perfect parity gaps — ✅ closed in v0.5.8 except INDEX 00.** The old whipper-flag widgets were retired with whipper (KDD-18); the fresh cyanrip overread toggle shipped 2026-07-21 (`-O` — the doc-claimed `-x` never existed), and the gap-handling investigation closed the same day as already-satisfied (cyanrip's default = EAC's, verified upstream). **v0.5.8 closed the remaining four** on the maintainer's "equal-or-stronger rigor, honestly labelled as ours — never forge EAC" principle: an openly-verifiable SHA-256 **log checksum** (KDD-28), a **measured cache-defeat verdict** via `cd-paranoia -A` (KDD-29), **Test & Copy** CRC pairs from `-Z` convergence + a verify-every-track mode (KDD-30), and **read-offset auto-confirmation** by AccurateRip (KDD-31). The one remaining difference is the cue-metadata **`INDEX 00`** question, whose *mechanism is now decided* — build cyanrip from the soft-fork integration branch (KDD-32; `master` already emits it, and it carries PR #115). Not a blocker for the public AppImage. *Closed on the fork (recorded 2026-10-07):* its rip of 2026-08-04 matches all ten of EAC's pre-gap rows to the hundredth of a second (`tests/test_fork_rip_eac_parity.py`), and the 2026-10-07 run's cue marks the same nine tracks as EAC's. HTOA stays out of scope.
4. **P1 — UX gaps from real-user testing** — issues surfaced on Bazzite that aren't urgent but make the GUI feel less polished.
5. **P1 — Install automation** — pre-clone host bootstrap script. Blocked on the repo flipping public.
6. **P1 — Documentation backlog** — items that need real-system output from T32 to write authoritatively.

### ⭐ Current plan & priorities (re-ranked 2026-07-21 — HISTORICAL since 2026-09-30)

> **Historical, not the live queue** (2026-09-30 audit). This was START HERE in July
> 2026; the live queue is the newest dated section at the top of this file. Kept for
> its numbering, which other text cites.

The live, ordered work queue — what to pick up next. Difficulty: **S** = a focused session, **M** = 1–2 sessions (may need upstream-source research), **L** = multi-session. **HW** = hardware-gated (needs the user's machine/drive/disc — code-side prep can still be done first). Each entry is deliberately just the queue line; the linked section carries the full context. *(Originally set 2026-06-09; re-ranked 2026-07-21 per the docs-audit consolidation plan, because 11 of the original 15 items were ✅ and the genuinely live workstreams sat in later sections a START-HERE reader never reached. The original numbered list — still cited elsewhere as "current-plan item N" — is preserved with its numbering as ranked history just below.)*

1. **✅ Trust & supply-chain hardening — open audit follow-ups (M; maintainer-gated in part).** The **verify** half of update authenticity **shipped 2026-07-21** (KDD-26): the `cryptography` dep was approved and is a hard runtime requirement, `update_signing.py` exists, and `update_install.py` is wired fail-closed — dormant until a key exists. **Remaining, maintainer-only:** ~~generate the keypair, bake in the public key, sign the first release (see [docs/architecture.md §6.2](docs/architecture.md)).~~ ✅ **Superseded (2026-09-30 audit):** KDD-37 D9 (2026-09-25) rules that signing is never armed; an update is protected instead by the build attestation, checked fail-closed in the app (`update_attestation.py`). Separately, full-AppImage byte-reproducibility still needs validating on a real release build (the *Reproducible AppImage build* row, still `[~]`). See *P1 — Trust & supply-chain hardening* below.
   - *Superseded 2026-10-12*: the signing half was retired by KDD-37 D9 (`update_signing.PUBLIC_KEY_B64` stays empty on purpose; the fail-closed `update_attestation.py` protects an update instead). The reproducibility half is the open row *Reproducible AppImage build*.
2. **✅ cyanrip soft-fork upstream PRs — prepared, env-gated (M).** *(2026-09-30 audit: only the encoder-args contribution remains; the colon fix is done — an escape-aware pre-splitter is in upstream `master` and the fork, per the colon row's 2026-09-25 audit under "cyanrip upstream contributions".)* Both contributions (the `-a`/`-t` colon-parsing fix; full libavcodec encoder args) are researched, patched, and paste-ready in `scripts/cyanrip/` + [docs/cyanrip-fork.md](docs/cyanrip-fork.md); execution (fork → build in the container → issue → PR) needs an environment with cyanrip repo access (local, or a cyanrip-seeded session — this cloud session is scoped to Platterpus only). See the *cyanrip upstream contributions* block below.
   - *Superseded 2026-10-12*: only the encoder-options half is left, and the open row *Full FLAC (libavcodec) encoder arguments* carries it.
3. **🟡 Hardware-gated proof queue — HW (user), S each.** *(2026-09-30 audit: the hardware runs this queue waited for have happened — the in-app acceptance run, rounds 26–29 — and the current run sheet is [`docs/rig-session.md`](docs/rig-session.md); `hardware-test-checklist.md` is kept as the full reference (since 2026-11-16 the *Hardware test checklist* section of `docs/test-plan.md`). The "Still open" items below were not re-checked one by one.)* Everything only the Bazzite + BDR-209D rig can prove, consolidated. **The run sheet is the former `hardware-test-checklist.md`, now [`docs/test-plan.md`](docs/test-plan.md) → *Hardware test checklist*** — as of 2026-07-30 it is *consolidated*: it carries **every** outstanding hardware test rather than only the newest release's, grouped by why each is still open, with stable test IDs that are retired once they pass. Work that sheet first; it, not this bullet, is the live list. **First run done 2026-07-26 (partial):** the log checksum verified end-to-end (test 3 ✅, recomputed independently from the real artifact + tamper detected), force-stop/post-cancel recovery held (test 15 ✅), the wizard's `dnf install /usr/bin/cd-paranoia` provides-install + export **succeeded on a real Fedora container** (previously flagged unverified — now proven), and the real `cd-paranoia -A` output was captured and committed as a fixture (the KDD-29 gate is CLOSED). That run also surfaced **five defects, all fixed** (see CHANGELOG `[Unreleased]`): the 90 s probe timeout, the undiagnosable unknown verdict, "Finished with issues." on a successful cache-only run, the EAC log calling offset-variant tracks absent from AccurateRip, and overread rendering "(unknown)". **Second run done 2026-07-26 (v0.5.9, Overread OFF — a complete 14-track rip):** all eight v0.5.9 fixes confirmed on the rig — the cache probe finishes and reaches both the panel and the log as a measured `Yes`, the wizard reports "Done.", the offset trust line reached **"confirmed — two independent sources agree"** (KDD-31 earned on hardware), overread renders `No`, and offset-variant tracks are described correctly — so **tests 2, 5, 14 are ✅**. **⭐ Test 17 is ANSWERED:** the `.cue` carried 14 × `INDEX 01`, no `PREGAP` — the pre-gap gap is real on the deployed cyanrip 0.9.3, so KDD-32's build-cyanrip-from-source step is now **required** and is the run sheet's final part. That run also surfaced **two new honesty defects, both fixed in v0.5.10**: a re-read track's Test & Copy proof never reached the log, and a track whose re-reads *disagreed* rendered as clean. **Third run done 2026-07-26 (v0.5.10, step 1 only):** the Test & Copy rendering fired but paired the convergence proof with the **first pass's** CRC on both swapped tracks (log `52DFDF7D`/`6902BCF0`; files `3D8FCF0C`/`E0036697`) — the swapped-in read's own record now replaces the first pass's (fixed in v0.5.11, regression-pinned). Both problem tracks converged for the first time (`unresolved: false`). **Still open** — the run sheet's own §A–§E are authoritative and the old flat test numbers below were superseded by them on 2026-07-30; everything *not* on the sheet: the `-Z` convergence re-rip (history item 14); the from-scratch wizard/`setup-host.sh` run + drive-setup success screens + README screenshots + Picard UX (history item 10; test-plan Tests 3/5/6); cyanrip WAV parity (proof matrix below); the new test-plan Tests 12–14; a real in-app uninstall run (history item 4); UX gap #3 (timestamp-localized anomalies — needs real anomaly-bearing output); and a live screen-reader (e.g. Orca) session over the announced surfaces (UX gap #4's last fraction, 2026-07-21). *(The EAC gap-handling check was removed from this queue 2026-07-21 — closed as already-satisfied; cyanrip's default matches EAC, verified upstream, no hardware run needed.)*
4. **✅ Documentation backlog — the 2026-07-21 docs-audit consolidation plan (S–M).** In execution; per-item status under *P1 — Documentation backlog* below.
   - *Done 2026-10-12, found already finished*: the *P1 — Documentation backlog* parent and every sub-item are `[x]` (`docs/archive/audit-2026-07-21.md`, `docs/manual-ctdb-repair.md`, `scripts/cyanrip/verify-meta-colon.c`). The two README rows left (screenshots, Picard) are their own open rows.
5. **✅ UX gap backlog remainder (S–M).** Gap #4 is ✅ complete (the keyboard-reachability sweep + focus-safe live announcements shipped 2026-07-21; only the live screen-reader confirmation rides queue item 3); gap #3 is hardware-gated (queue item 3 above). Canonical ranked table: [docs/ux-design-principles.md](docs/ux-design-principles.md); tracking checklist: history item 15 below.
   - *Superseded 2026-10-12*: a pointer only. The canonical table is `docs/ux-design-principles.md` (gaps 1, 2, 4, 5, 6 done), and gap 3, the one left, is item 15's checklist.
6. Duplicate of **CTDB parity repair** — merged 2026-09-30.

8. **[x] ✅ The fork is installed by the app, and "which build" is visible — DONE 2026-08-03 (v0.6.3, KDD-33).** The container switch to the fork was a manual step in a test plan, and it never ran: **every rip through v0.6.2 used the stock COPR `cyanrip 0.9.3`**, including the AccurateRip-verified hardware runs. The maintainer found out by reading the dependency dialog. Fixed at both ends — the setup wizard now builds/installs/**verifies** the pinned fork (`deps/fork_source.py`, `cyanrip_fork` step, additive so a failed build leaves a working ripper), and the dependency check names the build next to the version because the fork keeps upstream's version string on purpose. See KDD-33.

10. **[x] ✅ Two contract-verification gaps closed — DONE 2026-08-03 (v0.6.3).** Both were ours and both were invisible to a green suite. (a) **The input half of the seam was never checked.** We diffed the fork's published log lines against our parser and never their published *flag table* against our argv — and that table had said `-v`/`--version` with no `-V` row for a full round, while all four of our version probes sent `-V`. A rejected version flag exits non-zero, which every probe here reads as "the tool is absent", so installing the fork would have reported the ripper **missing** right after the wizard built it. `tests/test_argv_surface_agreement.py` now does the diff mechanically and fails against round 4's own table with the old flag set. (b) **Our fatal-message fixture inherited the fork's filter.** Their generator ran candidates through a 21-word prefix allowlist; their control-flow re-derivation took the inventory 88 → 104, and our pattern missed all 13 matchable strings it had hidden — two of them ordinary hardware failures reaching the user as a bare "Rip failed." The matcher is now compiled from their published `printf` formats. See `docs/testing.md` §5.ab.
3. **🟡 Hardware-gated proof queue — HW (user), S each.** *(2026-09-30 audit: the hardware runs this queue waited for have happened — the in-app acceptance run, rounds 26–29 — and the current run sheet is [`docs/rig-session.md`](docs/rig-session.md); `docs/hardware-test-checklist.md` is kept as the full reference. The "Still open" items below were not re-checked one by one.)* Everything only the Bazzite + BDR-209D rig can prove, consolidated. **The run sheet is [`docs/hardware-test-checklist.md`](docs/hardware-test-checklist.md)** — as of 2026-07-30 it is *consolidated*: it carries **every** outstanding hardware test rather than only the newest release's, grouped by why each is still open, with stable test IDs that are retired once they pass. Work that sheet first; it, not this bullet, is the live list. **First run done 2026-07-26 (partial):** the log checksum verified end-to-end (test 3 ✅, recomputed independently from the real artifact + tamper detected), force-stop/post-cancel recovery held (test 15 ✅), the wizard's `dnf install /usr/bin/cd-paranoia` provides-install + export **succeeded on a real Fedora container** (previously flagged unverified — now proven), and the real `cd-paranoia -A` output was captured and committed as a fixture (the KDD-29 gate is CLOSED). That run also surfaced **five defects, all fixed** (see CHANGELOG `[Unreleased]`): the 90 s probe timeout, the undiagnosable unknown verdict, "Finished with issues." on a successful cache-only run, the EAC log calling offset-variant tracks absent from AccurateRip, and overread rendering "(unknown)". **Second run done 2026-07-26 (v0.5.9, Overread OFF — a complete 14-track rip):** all eight v0.5.9 fixes confirmed on the rig — the cache probe finishes and reaches both the panel and the log as a measured `Yes`, the wizard reports "Done.", the offset trust line reached **"confirmed — two independent sources agree"** (KDD-31 earned on hardware), overread renders `No`, and offset-variant tracks are described correctly — so **tests 2, 5, 14 are ✅**. **⭐ Test 17 is ANSWERED:** the `.cue` carried 14 × `INDEX 01`, no `PREGAP` — the pre-gap gap is real on the deployed cyanrip 0.9.3, so KDD-32's build-cyanrip-from-source step is now **required** and is the run sheet's final part. That run also surfaced **two new honesty defects, both fixed in v0.5.10**: a re-read track's Test & Copy proof never reached the log, and a track whose re-reads *disagreed* rendered as clean. **Third run done 2026-07-26 (v0.5.10, step 1 only):** the Test & Copy rendering fired but paired the convergence proof with the **first pass's** CRC on both swapped tracks (log `52DFDF7D`/`6902BCF0`; files `3D8FCF0C`/`E0036697`) — the swapped-in read's own record now replaces the first pass's (fixed in v0.5.11, regression-pinned). Both problem tracks converged for the first time (`unresolved: false`). **Still open** — the run sheet's own §A–§E are authoritative and the old flat test numbers below were superseded by them on 2026-07-30; everything *not* on the sheet: the `-Z` convergence re-rip (history item 14); the from-scratch wizard/`setup-host.sh` run + drive-setup success screens + README screenshots + Picard UX (history item 10; test-plan Tests 3/5/6); cyanrip WAV parity (proof matrix below); the new test-plan Tests 12–14; a real in-app uninstall run (history item 4); UX gap #3 (timestamp-localized anomalies — needs real anomaly-bearing output); and a live screen-reader (e.g. Orca) session over the announced surfaces (UX gap #4's last fraction, 2026-07-21). *(The EAC gap-handling check was removed from this queue 2026-07-21 — closed as already-satisfied; cyanrip's default matches EAC, verified upstream, no hardware run needed.)*

11. **⬜ Round-5 follow-ups the verification surfaced (S–M each, not blocking the round).** Ranked:
   - **RESOLVED — not a defect, a decision.** The line was RENAMED in round 6 and is
     now `Cache model:`, carried deliberately on the parser's ignore-list
     (`parsers/cyanrip_log.py`); an honest `(unknown)` in an unprobed EAC-style
     export is the correct rendering, not a dropped fact. Original text:
   - ~~**HIGH — `Cache defeat:` is captured and discarded.**~~ The fork now prints it; our parser drops it, so the EAC-style log renders `Defeat audio cache : (unknown)` for a fact stated on the line above. A diagnostic-completeness violation in the archival artifact.
   - **HIGH — keep BOTH golden references.** The round-5 log *narrows* coverage vs the round-4 one already committed: no `-Z` secure-read path (so the F1 `Done;`-misattribution class stops being exercised), no over-full-scale `REPLAYGAIN_TRACK_PEAK` > 1.0 (the case the whole sample-peak trap comment exists for), and no custom `-D/-F/-L/-M/-P`. Commit round 5 as a *second* fixture, and ask them to generate future references with `-Z` and a clipping track.
   - **MEDIUM — `Encoder:` and `CD-TEXT:` fall through unrecognised.** `Encoder:` names which libavformat/libavcodec actually encoded the archival FLAC, which is squarely under the say-which-build-produced-an-artifact rule.
   - **MEDIUM — per-track paranoia counters: we asked for W1, they built it, we read none of it.** `TrackResult` has no field. Either graduate it or record the decision.
   - **DONE 2026-08-03** — `rip_timing.py:72` parses `MM:SS.FF`, alias at `:126`.
     Already recorded as done later in this same file, which is why this row is a
     duplicate rather than a gap. Original text:
   - ~~**MEDIUM — `Total time:` / `Duration:` are `MM:SS.FF` in CD frames.**~~ `rip_timing.parse_hms_to_seconds` requires `HH:MM:SS`, so it returns `None` for every fork value and `_enrich_timing_with_disc_duration` is a silent no-op on every fork log. No wrong number is produced; the fact is dropped.
   - **LOW — the status report says "3 track(s) could not be verified as accurate" on a disc where AccurateRip was never queried**, while the per-track rows correctly say "Not checked against the AccurateRip database". The summary is less honest than the rows it summarises.
   - **LOW — `True peak level:` has no field** and falls through silently.
   - **HIGH — the auto-fix addendum invalidates cyanrip's own log checksum, and the naive fix is worse.** We append the supersession block to the ripper's `.log`, after its `Log FUN512:` line; cyanrip has a dedicated `CRIP_LOG_TRAILING_DATA` state, so `cyanrip -Y` reports the file as modified and exits 1 (fork round 5 Q5, measured). But simply moving it to a sidecar **regresses bug #19**: `parse_cyanrip_log` reads `shipped_crcs` *from that appended text* and its own comment calls it "the only statement in the file about which bytes actually shipped", so the EAC-style log would go back to printing the **discarded** first-pass CRC. Attempted and reverted rather than shipped half-done. The real fix is to apply the supersession structurally from the worker's `retried_tracks` (which already reaches the report) *before* rendering, keep the parser's addendum rule for legacy logs, and only then write the sidecar. Needs the whole chain re-verified end to end.
   - **[x] MEDIUM — the album-loudness block is gated on FFmpeg's wording — FIXED 2026-08-21.** Two halves, fixed in two steps. The *header* half was done earlier: `cyanrip_log.py` keyed on `^Album Loudness Summary:$` when the fork's stable string is only `Album Loudness` (their P2), so one FFmpeg rewording emptied `album_loudness` entirely — the pattern is now `^Album Loudness\b`. The *values* half was the one this entry said had "**no** stable provider source at all", and that stopped being true at round 8 without anyone here noticing: the fork now prints four column-0 rows it owns — `Album integrated loudness (R128):`, `Album loudness range (R128):`, `Album sample peak level:`, `Album true peak level:` (their P2, `cyanrip_encode.c:847-853`) — and we were **silently dropping all four** while still scraping the `I:` / `LRA:` / `Peak:` lines their P3 disclaims. Measured on the round-12 artifacts: 4 of the 8-9 unclaimed column-0 lines per log were these rows, with no `_IGNORED_DISC_LINES` entry either. Now: the owned rows are the source, the `ebur128` scrape is a documented fallback for the deployed stock 0.9.3 and every pre-round-8 fork build (both cases are committed logs), precedence is recorded rather than positional, and the report's "say the source is libavfilter and unpinned" alternative is moot for a build that prints the owned rows. Pinned by `tests/test_fork_album_loudness_r12.py` against both committed round-12 artifacts. **Not yet done, and named so it is not mistaken for closed:** the same migration at the **per-track** level (task #80 — `True peak level:` / `Integrated loudness (R128):` / `Loudness range (R128):` per track still come off the sub-header block), and `_FORK_ONLY_RULES` in `scripts/emit_dependency_contract.py` does not yet list the four new rule names, so the generated contract's fork-only count under-reports by 4.

### 2026-06-09 plan — ranked history (numbering preserved; cited elsewhere as "current-plan item N")

The queue as set 2026-06-09 and worked down through 2026-07 — 11 of its 15 items shipped. Kept with its original numbering as the historical record (same pattern as the 2026-05-30 "Ranked execution order" further down) because other text cites "current-plan item N"; the still-open fractions of items 10/14/15 are ranked in the live queue above.

10. **⬜ Remaining hardware-gated doc items — HW (user), S each.** Real-run confirmations: `setup-host.sh` / host wizard from scratch, the drive-setup wizard's "what success looks like" screens (the previous backend's `drive analyze`/`offset find` strings are gone — test-plan Tests 3–4 need re-scoping, see the Documentation backlog), README screenshots (Test 5), Picard UX (Test 6). *(PyPI Trusted-Publisher setup — Test 7 — is **DONE**: the package publishes automatically on every tagged release.)*

14. **🟡 EAC-parity follow-up (audio-trust focus) — code SHIPPED 2026-06-28; convergence HW-gated.** Continuing the EAC-parity brief ([docs/eac-parity.md](docs/eac-parity.md), [docs/eac-parity.md](docs/eac-parity.md)). **(a) ✅ cyanrip `-Z N` "re-rip until reads match"** — `Config.secure_rerip_matches` (0=off) → `RipParameters` → backend ABC → cyanrip argv; whipper ignores it; Settings spin box greyed for whipper. The lighter, no-new-dep answer to a Track-3-class near-miss. *HW-gated:* convergence effect needs a real marginal-disc run on the BDR-209D (re-rip with it on, re-run `scripts/eac_parity.py` vs the EAC baseline). **(b) ✅ Verification verdict banner** — colour-coded at-a-glance trust headline above the results table, plus one shared `confidence ≥ 1` rule (`parsers/rip_log.track_accuraterip_verified`) across the banner, disc panel, status line, and EAC renderer (fixed a real bug: the disc panel string-matched "exact match" and under-counted cyanrip rips). **(c) ✅ Parity made routine** — `tests/test_parity.py` pins the committed cyanrip-vs-EAC result (12/14, T3+T5) as a no-hardware regression guard. **(d) ✅ Honest EAC-layout log renderer** — `eac_log_export.py` + `scripts/render_eac_log.py` render our rip into EAC's layout, clearly attributed and **never signed** (an EAC-signed log = provenance forgery; not pursued). **Decisions for the maintainer (in the feasibility doc):** tracker-accepted EAC logs (recommend no — forgery), in-app CTDB repair (defer — heavy .NET/Mono dep + blocked on CRC hardware-validation).

15. **🟡 UX trust-first improvements (from the EAC-UX deep-research, 2026-06-28).** The ranked gap table — each gap's rationale, size, and shipped detail — lives **canonically in [docs/ux-design-principles.md](docs/ux-design-principles.md)** (code comments cite its gap numbering; this entry drifted from it once, which is why it is now only the tracking checklist):
    - [x] Gap 1 — Goal presets (shipped 2026-06-28, 0.4.0)
    - [x] Gap 2 — Machine-readable `.platterpus.json` log (shipped 2026-06-28)
    - [ ] Gap 3 — Timestamp-localized anomalies + one-click playback (hardware-gated)
      - **Triaged 2026-11-16 (stale but open):** positions now reach the report from `.25` (R44, `disc.error_positions`); there is no UI for them and no playback (no player in `src/`).
    - [x] Gap 4 — Accessibility (names pass 0.4.4; keyboard-reachability sweep + focus-safe live announcements DONE 2026-07-21; a live screen-reader session on the rig is the one hardware-gated confirmation still owed — queued in live item 3)
    - [x] Gap 5 — Outcome-oriented wording (shipped 2026-06-29)
    - [x] Gap 6 — Drive profiles keyed by stable fingerprint (record/display/guard ledger shipped 2026-06-29; per-drive offset *application* shipped 2026-11-13, each drive's own record deciding its `-s`, KDD-23 as amended; proven in the suite with two simulated drives, and still to be seen on a real two-drive rig)

- **[ ]** Multi-disc queue
  - **Triaged 2026-11-16 (owner):** not built; the maintainer's feature call.
- **[ ]** Multi-drive support
  - **Triaged 2026-11-16 (owner):** not built as concurrent rips; each drive's own offset shipped 2026-11-13 (Gap 6), which this would build on.
- **[x]** ~~udev-driven auto-detect on disc insert~~ — **closed as satisfied 2026-07-21 (audited):** the outcome (a freshly-inserted disc is picked up with no manual Rescan) has been delivered since 0.4.x by `drive_media.MediaWatcher` — a 2.5s `CDROM_DRIVE_STATUS` poll (never spins the disc) + a transition-detecting state machine that auto-rescans while idle. A udev/DBus listener would only shave the ≤2.5s poll latency at the cost of a new integration surface; not worth it unless a real case surfaces that polling misses. (Live-hardware confirmation of the watcher itself is already tracked in the test plan.)
- **[x]** ~~ReplayGain calculation~~ — **closed as satisfied 2026-07-21 (audited against upstream master):** cyanrip computes EBU R128 loudness on every rip and writes the full tag set by default (`REPLAYGAIN_TRACK_GAIN/RANGE/PEAK`, `REPLAYGAIN_ALBUM_GAIN/RANGE/PEAK`, `R128_TRACK_GAIN`, `R128_ALBUM_GAIN`, reference loudness — gated only by `-K`, which Platterpus never passes), and the results-pane/JSON already surface album loudness. Derived MP3/WavPack copies carry the tags via the transcode's `-map_metadata 0` (WAV can't hold tags — already warned in Settings); that carriage is worth an eyeball on the next hardware session, but nothing needs building.
- **[x]** Auto-move completed rips to a library folder — **DONE 2026-07-21:** Settings → "Move finished rips to" (`Config.library_dir`, empty = off). The album folder moves only after **every** post-rip worker settles (tag/cover/transcode, the verification suite, checksums, the comparison scan, the debounced report write) — a 500ms settlement poll gates it, the rip generation abandons a superseded move, and the actual move runs on the shared generation-guarded daemon (`library_move.move_album_folder`: never overwrites — collisions get a "(N)" sibling; refuses self-nesting/workspace-root moves). The post-rip buttons repoint to the new home; the re-rip comparison now also scans the library (`find_prior_report` extra_roots).
- **[x] Additional encoding outputs: WavPack, MP3, and WAV — SHIPPED 2026-06-26** (maintainer sign-off; flipped Critical Rule #4 to "FLAC is the default/master, others derived"). **Design → [docs/archive/mp3-wav-support-2026-06.md](docs/archive/mp3-wav-support-2026-06.md) (archived 2026-08-06).** Built: `adapters/transcode.py` now does FLAC→**WavPack** (`-c:a wavpack`, lossless, APEv2 tags) in addition to MP3 (`-q:a 0` VBR + ID3/APIC cover) and WAV (`pcm_s16le`); the **Settings → Output format** selector (FLAC/WavPack/MP3/WAV) + a live WAV no-tags/art warning; the transcode folded into the post-rip daemon thread (after tag→cover→re-compress, reading the final FLACs) via a `transcode_done` signal; `to_config()` now round-trips `output_format` (+ preserves `mp3_vbr_quality`, which had been silently reset). **Transcode-always model** (§4(b)): both backends rip FLAC, then derive — so MP3 is best-practice VBR on *both* (cyanrip's native MP3 is only CBR) and the FLAC master always exists. `ffmpeg` is the single encoder dep (already registered in the subsystem — no bespoke install code, Critical Rule #6). +11 tests. **Known limitation:** embedding cover art *inside* `.wv` needs the standalone `wavpack` tool (ffmpeg's muxer is audio-only) — deferred; the folder `cover.<ext>` is the universal image. **Backend rip parity proofs (P2 below) stay open** — those await real-hardware rips, not code.
  - **Verified findings (2026-06-23, replacing the earlier "verify-before-relying" bank):**
    - **whipper is FLAC-only** (profiles removed in v0.5.0) → MP3/WAV for the whipper path is a **post-rip re-encode**, not native. **cyanrip is natively multi-format** via `-o` (incl. `wav`, `mp3`; lossy bitrate `-b`, default 256).
    - **MP3/LAME `noise_shaping_amp` bug (#516)** is real + still open (LAME 3.100.1 is the last release) **but CBR/ABR-only — NOT VBR.** Use **VBR `-V0`**, joint-stereo ON; the `-q 4` workaround only matters if we ever ship CBR. Via FFmpeg/libmp3lame (cyanrip + a whipper re-encode) `-q:a 0` = `-V0`; the standalone-`-q` bug is a different code path → non-issue for VBR.
    - **WAV:** no RF64 needed at CD scope (~800 MB ≪ 4 GiB); **WAV carries no rich tags or cover art** (RIFF INFO only) → must warn the user (collides with the "good everything" north star). MP3 is *transparent*, not archival — keep FLAC the master.
  - See the design doc for the routing (Config `output_format`, a `native_output_formats()` capability flag, a post-rip `transcode.py` adapter modelled on `flac_recompress.py`, and `ffmpeg` as the single transcode dep).

### ⭐ EAC output-parity proof matrix (`output_reference/`)

Prove each backend reproduces EAC bit-for-bit, and **commit the proof**. The EAC
baseline (log + cue, *The Police — …: The Classics*, BDR-209D, offset +667) is
banked at `output_reference/EAC_flac/`, and the checker is built:
`scripts/eac_parity.py` (logic in `platterpus.parity`) diffs per-track `Copy CRC`
across EAC, cyanrip and legacy-format logs and exits non-zero unless every track matches.

**Each task = HW (user):** rip the baseline disc with cyanrip (the sole backend since 2026-06-30 — KDD-18) in that format,
run `python3 scripts/eac_parity.py output_reference/EAC_flac/eac_baseline_police_classics.log <the rip's .log>`,
and when it passes, commit the backend's `.log` (+ `.cue`) into the matching
`output_reference/` dir as the durable proof. **Do NOT commit audio** (public
repo + copyright; the CRCs are the proof). Ordered by format priority:

*Priority 1 — FLAC (v1 archival format):*
- **[x]** ~~whipper FLAC parity~~ — **retired: whipper removed 2026-06-30 (KDD-18)**; row kept as the record (the >587-offset question was settled by the cyanrip run below)
  - *Audit 2026-09-25: superseded.* The previous ripper was removed (KDD-18).
- **[x]** cyanrip FLAC parity → `output_reference/cyanrip_flac/` — **proof committed 2026-06-27: 12/14 byte-identical vs EAC** (T3 divergence + T5 disc spot — documented near-parity; pinned by `tests/test_parity.py`)
  - *Audit 2026-09-25: partly done.* 12 of 14 near-parity committed in output_reference/cyanrip_flac/, pinned by tests/test_parity.py; 2 tracks still differ.
  - *2026-09-25:* **Withdrawn.** Superseded by the 14/14 fork rip in output_reference/cyanrip_fork_flac/ (tests/test_fork_rip_eac_parity.py).

*Priority 2 — WAV (lossless → same Copy CRCs as FLAC):*
- **[x]** EAC "WAV" reference stored → `output_reference/EAC_wav/` (2026-06-25, **13/14** vs the FLAC baseline — track 3 read error this session; best run so far). ⚠️ **It's actually WavPack** (`wavpack -h -m`), not plain PCM WAV — equivalent for extraction parity (lossless) but a different format/encoder; see its README. Re-rip with a plain-WAV encoder to replace if a true WAV reference is wanted.
  - *Audit 2026-09-25: partly done.* Stored (13 of 14), but it is WavPack, not plain WAV; a true-WAV re-rip is owed.
  - *2026-09-25:* **Withdrawn.** Parity for WAV reuses the FLAC baseline (tests/test_parity.py), so a true-WAV EAC re-rip proves nothing new. The folder is WavPack and should just be labelled so.
- **[x]** ~~whipper WAV parity~~ — **retired: whipper removed 2026-06-30 (KDD-18)**
  - *Audit 2026-09-25: superseded.* The previous ripper was removed (KDD-18).
- **[x]** cyanrip WAV parity → `output_reference/cyanrip_wav/`
  - *2026-09-25:* **Closed as a duplicate, not done.** The work is tracked in the row *"MP3 / WAV parity rows — the matrix's other formats are unchanged and still"*, which stays open.

*Priority 3 — MP3 (P1; lossy → "parity" = same extraction CRCs + correct encoder/tags, not bit-identical audio):*
- **[x]** EAC MP3 reference stored → `output_reference/EAC_mp3/` (2026-06-25, **imperfect**: 12/14 vs the FLAC baseline — tracks 3/4 read errors this session; kept for the encoder-config reference `lame -V 0` + ID3. Re-rip clean to replace; see its README).
  - *Audit 2026-09-25: partly done.* Stored but imperfect (12 of 14); a clean EAC re-rip (the maintainer's) is owed.
  - *2026-09-25:* **Withdrawn.** MP3 parity is the extraction CRC, already proven by the 14/14 FLAC baseline; the stored copy still serves as the lame -V 0/ID3 reference.
- **[x]** ~~whipper MP3 parity~~ — **retired: whipper removed 2026-06-30 (KDD-18)**
  - *Audit 2026-09-25: superseded.* The previous ripper was removed (KDD-18).
- **[x]** cyanrip MP3 parity → `output_reference/cyanrip_mp3/` — **proof committed 2026-06-27: 13/14 extraction parity vs EAC**
  - *Audit 2026-09-25: partly done.* The log and cue are committed, 13 of 14 parity, not 14 of 14.
  - *2026-09-25:* **Closed as a duplicate, not done.** The work is tracked in the row *"MP3 / WAV parity rows — the matrix's other formats are unchanged and still"*, which stays open.

Done so far: **[x]** EAC baseline committed; **[x]** parity checker + tests
(`scripts/eac_parity.py`, `parsers/eac_log.py`, `platterpus.parity`); **[x]**
WAV/MP3 parity *semantics* pinned (WAV reuses the FLAC baseline; MP3 = extraction
CRC only) — `tests/test_parity.py`, [docs/archive/mp3-wav-support-2026-06.md](docs/archive/mp3-wav-support-2026-06.md) §1;
**[x]** checker reads EAC's native UTF-16 logs (was UTF-8-only → false 0/N).
So the one open row (cyanrip WAV) only awaits a real rip — the checker is ready.

### P1 — EAC bit-perfect parity gaps

The following whipper CLI options exist but aren't currently surfaced in our Settings dialog. Each is a small addition: a Config field, a Settings widget, a `RipParameters` field, and a flag in `WhipperHostExportedImpl.rip()`. The reference for what "should" be exposed is the EAC bit-perfect guide audit in [PLANNING.md KDD-13](PLANNING.md).

- **[x] Cover art (embed + save).** Done 2026-05-30. Whipper's `-C/--cover-art` — **actual choices are `file|embed|complete`** (the earlier `none/embedded/file` guess was wrong; confirmed against `whipper/command/cd.py`). Settings dropdown maps "Don't fetch"→`""` (flag omitted), "Embed in FLAC"→`embed`, "Save as file"→`file`, "Embed and save file"→`complete`. **Behavior change:** `Config.cover_art` defaults to `embed` for EAC parity, so a rip now fetches art over the network by default (best-effort; an unidentified disc just gets none). `RipParameters.cover_art`; flag passthrough.
- **[x] Force overread into lead-in/lead-out — REBUILT cyanrip-native, DONE 2026-07-21.** The whipper-era `-x/--force-overread` plumbing was removed with whipper (KDD-18); the fresh task shipped as the Settings "Overread" toggle → `Config.force_overread` → `RipParameters` → cyanrip **`-O`**, off by default (EAC's baseline setting, and how the 12/14 parity proof matched). **Flag-letter correction (same day):** this row and `docs/dependency-contracts.md` previously claimed cyanrip has "its own `-x` flag" — **`-x` does not exist in cyanrip's getopt at all** (verified against the deployed 0.9.3.1 *and* master); wiring the documented letter would have aborted every overread rip. The whipper flag really was `-x`, which is likely the mix-up's origin. Upstream's own caveat ("may freeze if unsupported by drive") is surfaced in the tooltip; effect confirmed only by a future hardware run (like every rip flag).
- **[x] Max retries.** Done 2026-05-30. `-r/--max-retries N`, default 5 (whipper's own). `Config.max_retries` + Settings spinbox (0–100) + `RipParameters.max_retries`; always passed (no-op at 5). Still current: cyanrip has its own `-r` and this Settings widget is live.
- **[x] Keep going on track failure — superseded, cyanrip-native.** Was done 2026-05-30 as whipper's `-k/--keep-going` (`Config.keep_going` + Settings toggle + `RipParameters.keep_going` + flag); removed with whipper (KDD-18). cyanrip needs no equivalent flag — its rip loop is cyanrip-native and there is no Settings toggle for this today.
  - *Audit 2026-09-25: superseded.* Removed with the previous ripper (KDD-18); cyanrip does it natively.
- **[x] Continue on CD-R — superseded, cyanrip-native.** Was done 2026-05-29 (pulled forward during T32) as whipper's `--cdr` flag (`Config.continue_on_cdr`, a "CD-R discs" Settings toggle, `RipParameters.cdr`, passthrough in `WhipperHostExportedImpl.rip()`); removed with whipper (KDD-18). cyanrip is cyanrip-native here too — no equivalent flag, no Settings toggle exists today.
  - *Audit 2026-09-25: superseded.* Removed with the previous ripper (KDD-18).

- **[x] EAC gap-handling parity — CLOSED as already-satisfied (verified upstream 2026-07-21).** EAC's reference rip used **"Gap handling: Appended to previous track"**, and this was flagged (2026-06-14) as a possible parity lever because "we set no gap mode." Re-checked against cyanrip's own source and README (0.9.3.1 **and** master): cyanrip's default *is* EAC's — README §"Pregap handling": *"By default, track 1 pregap is ignored, while any other track's pregap is merged into the previous track. **This is identical to EAC's default behaviour.**"* We pass **no `-p`**, so the rip uses that default (exactly how the committed 12/14 audio-parity proof matched). So there is **no audio-parity gap here and no knob to add**: cyanrip's `-p` is a *per-track* override (`-p track_number=action`; `default`/`merge`/`drop`/`track`), not a global switch, and its only archival-safe value is the default we already use (`drop` deletes pregap audio and breaks cyanrip's no-discontinuities guarantee; `track` renumbers tracks and would desync our per-track `-t`/`-l`/progress/AR alignment). The **one** remaining EAC-gap difference is *cue-metadata only* — EAC's subchannel-detected `INDEX 00` pre-gap markers — which is **not** an audio-parity gap and is tracked separately (parity doc §Pregaps P3 + the cyanrip **PR #115** route in [docs/cyanrip-fork.md](docs/cyanrip-fork.md) Part C §2.2 and Part D, Order 1). Same disposition as the udev/ReplayGain backlog closures: the feature was already delivered by cyanrip's default; the checkbox just hadn't been flipped.

Each is independent; do them in any order. They should land before the AppImage's first public release so the GUI matches what EAC users expect.

**Archival-quality follow-ups (from the 2026-06-23 EAC-guide gap analysis; see [docs/session-log.md](docs/session-log.md) + [docs/archive/archival-extraction-guide-2026-06.md](docs/archive/archival-extraction-guide-2026-06.md)):**

- **[x] cyanrip metadata richness (current-scope, "good everything"). Done 2026-06-23.** The MB lookup now also extracts **genre** (top folksonomy tag — musicbrainzngs 0.7.1 has no `genres` include), **disc number / total discs** (medium position/count), and **per-track ISRC** (`isrcs` include), and feeds them to cyanrip's `-a`/`-t` (FFmpeg `genre`/`disc`/`isrc`). Silent passthroughs (read from the stored MB `ReleaseDetail`, guarded by matching MBID; not editable). `RipMetadata.tracks` is now `TrackTag(number,title,artist,isrc)`; `ReleaseSummary`/`TrackSummary` gained the fields. whipper unaffected. **Composer deferred** (per-recording work→artist relationship queries = rabbit hole; revisit if a classical-heavy user asks).
- **[x] cyanrip FLAC encode-verify (archival integrity) — SHIPPED.** cyanrip encodes FLAC via FFmpeg with no decode-verify pass (unlike whipper's `flac --verify`). Closed by `adapters/flac_verify.py`: a best-effort, never-raising post-rip `flac --test` (decodes each FLAC and checks its embedded STREAMINFO MD5 against the decoded audio), run on the cyanrip output via the `verify_flac_after_rip` Setting (default on), wired in `main_window_rip._start_flac_verify` off the GUI thread. Result surfaced in the rip report + UI. (Doing this *inside* cyanrip is a separate, lower-priority upstream idea — see the cyanrip upstream-contribution list below.)
- **[x] FLAC compression level `-8` — whipper-only, shipped as an opt-in post-rip re-encode (2026-06-23).** whipper hardcodes flac `-5` (not exposable — KDD-13); `-8` is lossless and just smaller. **cyanrip is a no-op:** it encodes FLAC at *maximum* compression (upstream README "always uses maximum compression"; it sets libavcodec `compression_level` explicitly per format, not FFmpeg's default 5) and exposes no level flag — so there is nothing to expose or change there. Closed for whipper with an **optional post-rip re-encode** to `-8 --verify` (`adapters/flac_recompress.py`), gated on the new `WhipperBackend.produces_max_compression_flac()` capability (False=whipper→runs, True=cyanrip→skipped), surfaced as the "Re-compress FLACs" Settings toggle (off by default). Lossless + verified, atomic per-file swap-in, tags/art preserved; folded into the post-rip tag/cover thread so it runs after those. Flags (`-8 -e -p --verify --silent -f -o`) verified current against the xiph spec (2026-06-23). `-e` (exhaustive model search) and `-p` (exhaustive `qlp_coeff_precision` search) cost only *encode* time — never decode time, the one thing that mattered to the maintainer (mobile playback) — so they were added 2026-06-23 ("always fine to add encoding time if it helps") for the last fraction of a percent at zero playback cost. **Hardware validation gated:** test-plan **Test 10** (decoded-PCM MD5 identical before/after, cover art + tags survive, files smaller).
  - *Removed 2026-10-07* (the maintainer: *"fix or remove this … it is inert and disabled with cyanrip and does nothing"*). With cyanrip the sole backend (KDD-18) the step could never run, so the setting, the Settings row, the `flac_recompress.py` adapter, the `produces_max_compression_flac()` capability and the report's re-compress keys (schema v33) went together. An old config carrying the key loads quietly (`config.RETIRED_CONFIG_KEYS`).

> **CTDB verify + repair are tracked elsewhere, not here.** They are archival-verification *features*, not parity-gap Settings widgets, so they live in the **Ranked execution order** above (items 5–6) with full rationale and decisions in the [Upstream open-source modification](#p1p2--upstream-open-source-modification-for-eac-parity-investigation-2026-06-02) section and [docs/archive/upstream-modification-investigation.md](docs/archive/upstream-modification-investigation.md). See also [PLANNING.md KDD-12 / KDD-14 / KDD-16](PLANNING.md).

### P1 — Release milestones

These remove most of the README's "until X happens" caveats. Done in order, they collapse Method C's friction substantially.

- **[x] Merge `claude/lucid-babbage-JYI8c` into `main`.** Done 2026-05-30 (`--allow-unrelated-histories`; main previously held only `.gitattributes`). Fresh `git clone` now lands on a working state. Removed the README dev-branch/authenticate steps and the `dev-setup.sh` branch-guard.
- **[x] Flip the GitHub repo to Public.** Done 2026-05-30 by the user. Plain `git clone https://...` now works without `gh auth login` / SSH key setup. The LICENSE decision it was gated on is also resolved: **GPL-3.0-only** (KDD-10) — `LICENSE` committed, `pyproject.toml` classifier set, README updated. Follow-up: drop the README Method-C "private repo, authenticate first" blockquote (see Documentation backlog).
- **[x] Tag `v0.1.0` and publish the AppImage as a release asset. Done 2026-06-01.** The first public release is live: [v0.1.0](https://github.com/rmccann-hub/Platterpus/releases/tag/v0.1.0) with `platterpus-x86_64.AppImage` (+ `.sha256`), `install.sh`, and `install-appimage.sh` all attached by `release.yml`. Both CI workflows (`ci.yml`, the new `appimage.yml`) and the release workflow are confirmed green on real Actions runs. Method A (AppImage) is now the recommended path. **Note:** the GitHub release got marked as a *full* release rather than a pre-release (UI default; `release.yml` only sets `--prerelease` when it *creates* the release, and this one was created in the UI). Cosmetic — flip it in the UI if a pre-release badge is wanted; future `git tag`-driven `v0.*` releases will auto-mark correctly.
      Earlier prep notes (2026-05-31): README rewritten for a published-AppImage world, `CHANGELOG.md` added, real app icon committed, release/CI workflows authored and YAML-validated.
- **[x] Publish the wheel to PyPI — DONE.** Method B is live: `pipx install platterpus` works. `.github/workflows/publish-pypi.yml` builds wheel+sdist, `twine check`s them, and publishes via **Trusted Publishing (OIDC, no stored token)** on each release, separate from `release.yml` so it can't block the AppImage. The one-time PyPI Trusted-Publisher config is in place and the publish run has gone green on every tagged release.

### P1 — The `FORK_PIN` gap: gated on hardware, not on code (assessed 2026-08-18)

**SUPERSEDED 2026-08-27 — this section described the gap as it stood before round 14.**
**Re-read 2026-09-30:** our pin is `51cc789` = `0.9.4-rc2+platterpus.18`, approved by
round 29; the fork's newest published build is `174a134` = `+platterpus.19`,
`release_seq` 29, under review in round 30 (`deps/fork_source.py`). The 2026-08-27
statement, as the record: ~~Our pin is `d9c058c` = `0.9.4-rc2+platterpus.10`, approved by round 14; the fork's
newest published build is `978f9b0` = `platterpus.11`, `release_seq` 21, which no
round has reviewed.~~ The gap is real again, deliberately, and for the same reason.
The original text, as the record: ~~Our pin is `ddf7ac3` = fork release **11**; the
fork's published stable is `c4d1a00` = release **16**.~~ **This is a decision, not drift** — round 11's `HANDSHAKE-PIN-POLICY` reads *"Reviewed and approved, not installed. FORK_PIN stays ddf7ac3"*, and its §5 gives the reason: `ddf7ac3` has BDR-209D evidence behind it and nothing published since has been near a drive. *"We do not ship a ripper to users on the strength of a suite."*

- **[x] Stop the gap being described wrongly (2026-08-18).** The release sequence of an installed build came only from `FORK_RELEASE_SEQ_BY_PIN`, a map maintained by hand here — so a release published *after* this app was built could not be placed, and a user on the fork's current stable was told their ripper had no story. It now also resolves from the fork's own manifest, so **the gap widening no longer degrades the message**. Since the gap is the normal steady state between hardware rounds, that mattered more than the gap itself.
- **[x] Move `FORK_PIN` — blocked, and deliberately so.** Two preconditions, in this order:
  1. **Hardware evidence for the newer build** — the rig run in the *Hardware-gated* item below. Code-side prep is already done: `meson_options` is wired, so the move is a constant plus a rig session, not a build change.
  2. **A handshake round that approves it.** That means **opening round 12**, which is not free: `scripts/handshake.py --status` shows all eleven rounds CLOSED today, so nothing blocks a release *right now*, and opening a round closes that door until both sides declare GO. Per **S-13** a round's close conditions are fixed at its lap 1, so a round cannot be opened cheaply just to move a constant.
  - *Audit 2026-09-25: superseded.* FORK_PIN has moved through later rounds and is now df91ae7.
- **Do not "tidy" the pin forward.** Every mechanism that would let it drift silently is deliberate: `FORK_PIN_RELEASE_SEQ` is `None` if the pin moves without its sequence being recorded (the suite refuses that state), and `test_the_pin_is_the_one_the_newest_closed_handshake_round_verified` derives the pin from `docs/handshake/verified/` rather than trusting the constant.

### P1 — Install automation

The host-side setup (Distrobox, container, whipper, exports) currently lives only in the README's prose. A reproducible script would catch the same pitfalls we hit walking the user through (`python3-setuptools` dep, `:latest` image pull confirmation, distrobox-export needs container entry). The post-clone side is already covered by `dev-setup.sh`.

- **[x] `setup-host.sh`.** Done 2026-05-30. Automates README Steps 1-4 (ensure Distrobox per-distro, create the `ripping` container with `--yes`, `dnf install whipper flac python3-setuptools` in-container, `distrobox-export` both binaries) **plus** clone + `dev-setup.sh` (Step 7). Idempotent (each step checks state first), with `--dry-run` (prints every command, changes nothing), `--yes`, `--no-gui`, `--container`, `--image`. Detects whether it's running inside a checkout (uses it) or piped from `curl` (clones to `~/Platterpus`). 7 smoke tests (`tests/test_setup_host_script.py`). **Untested against a real Distrobox host** — verified only via `--dry-run` + smoke tests in CI; needs a real-hardware run to confirm. Deliberately excludes drive calibration (GUI wizard) and Picard (GUI dependency manager).
- **[x] Document the curl-pipe-bash pattern** in the README as the "fast path" — done. The README quickstart leads with `curl -fsSL …/install.sh | bash` (and a download-then-run alternative); the manual Steps 1-4 are kept underneath as the source of truth.

### P1.1 — Install / uninstall ease (real-user testing)

Highest-priority subset of P1, focused specifically on the friction the first-time user hits between "no GUI installed" and "GUI running with a successful rip in hand." Items here unblock new contributors and reduce abandonment at the install step.

- **[x] ⭐ Zero-CLI distribution (PLANNING.md [KDD-17](PLANNING.md); user-approved 2026-06-04; ranked-order item 7). ALL THREE SLICES SHIPPED.** The headline install-ease goal: download one file, double-click, no terminal ever:
  - **[x] (a) Self-integrating AppImage — SHIPPED 2026-06-05** (`appimage_integration.py`; details in ranked-order item 7).
  - **[x] (b) Self-updating AppImage — SHIPPED 2026-06-09** (zsync update-information embedded at build; `.zsync` shipped per release; Help → Check for updates… delegates to AppImageUpdate or the release page; details in current-plan item 6).
  - **[x] (c) GUI first-run host wizard — SHIPPED 2026-06-05** (`deps/host_setup.py` + dialog + worker; cyanrip step added 2026-06-09; details in ranked-order item 7). Done since: the wizard exports `flac` (+ `metaflac`) from the container as of v0.3.5 (2026-06-27), needed by `flac --test` verification and the CTDB audio decode; CTDB verify was GUI-wired 2026-06-17.
  - **Rejected (see KDD-17):** Flatpak (sandbox can't reach host `~/.local/bin/whipper` — Critical Rule #3); a bespoke remote-config download stub (AppImage update-info already does it); a downloaded `.desktop`/script installer (Linux desktop trust model blocks it).

- **[x] Drive setup wizard (write-enabled) — top first-run priority.** Done 2026-05-30. Replaces the manual hand-edit of `whipper.conf` with a guided "Detect my drive" flow. `DriveSetupDialog` (Tools → "Set up drive…", and the Settings "Re-detect…" button) runs whipper's OWN `drive analyze` (cache) + `offset find` (offset) through the host-exported `~/.local/bin/whipper` on a worker thread (`DriveSetupWorker`), so they persist to `whipper.conf` themselves; we `back_up_whipper_config()` to `whipper.conf.bak` first. New adapter methods `analyze_drive()`/`find_offset()` (optional ABC capability — `NotImplementedError` default so non-whipper backends and test fakes still construct). Per-step failure is tolerated (a failed offset-find still reports the cache verdict). Also **fixed the "misleading read-offset field"**: it's read-only with the "Re-detect…" button beside it. Design: PLANNING.md **KDD-15**. 17 new tests.
  **Follow-ups:**
  - **[x] Manual-offset fallback — done 2026-05-31.** Real-user testing showed a fresh install with only CD-Rs is hard-blocked (whipper errors "drive offset unconfigured" and `offset find` needs an AccurateRip disc). The wizard now has a manual-entry spinbox + "Save offset" (linked to AccurateRip's offset list). It does **not** hand-author `whipper.conf` (still honouring KDD-15) — it persists via the GUI's existing `--offset` override (`Config.read_offset` + `override_read_offset`), emitted as `DriveSetupDialog.manual_offset_saved` and saved by the main window.
  - **[x] First-run auto-offer — done 2026-05-31.** On launch, if no offset is configured (new `offset_config.is_offset_configured()` checks `whipper.conf` *and* the override), the GUI offers the wizard once (dismissible; `Config.drive_setup_prompted` guards against re-nagging). Reversed the earlier "discoverable entry only" call after the CD-R block proved it's needed.
  - *Live streaming output during detection* — v1 shows a busy indicator + phase status; streaming the whipper output (like the rip view) is a polish item. Still deferred.

- **[x] Drive-access permission diagnostics.** Done 2026-05-30. New pure-stdlib `drive_access.diagnose_drive_access()` (injectable probes for testing) classifies the "no drive" state on the host: `no_device` (nothing connected), `permission` (a `/dev/sr*` node exists but isn't readable — owned by a group the user isn't in → fix command `sudo usermod -aG <group> $USER`), or `ok` (node readable, so the cause is elsewhere — container/whipper). `DrivePicker` now emits `drives_unavailable` on an empty refresh; MainWindow auto-shows the diagnosis **once per session and only when it's actionable** (a permission fix) — "no device" stays quiet (nothing to do). Always available via **Tools → Diagnose drive access…**. The dialog text is selectable so the fix command can be copied. Checking the host is correct because the AppImage runs as the host user and distrobox passes `/dev` through as the same user. (This was the one transferable lesson from the EAC-successor doc's Flatpak/Snap sandboxing section — the rest is N/A since we ship AppImage + pipx to reach host whipper.) 10 new tests.

- **[x] Auto-prompt the Unknown Album dialog when MB returns 0 matches.** Done 2026-05-28. Previously the user had to find File → Rip as Unknown Album in the menu after seeing "not in MusicBrainz"; now the dialog opens automatically the first time the GUI detects an unknown disc on a given drive selection. Guarded so it doesn't re-prompt if the user already accepted in this session.

- **[x] One-command uninstall script** (`uninstall.sh`). Done 2026-05-29. Default-removes the safe stuff (`.venv/`, `~/.config/platterpus`, `~/.local/share/platterpus`). Interactive prompts (or `--full`) for the broader cleanup: Picard Flatpak, the ripping Distrobox container, whipper.conf, host-exported binaries. `--dry-run` shows planned actions without executing. Music files at `~/Music/rips` are never touched without an explicit `--remove-rips` flag plus a typed `DELETE` confirmation in interactive mode. 6 smoke tests verify the script's help, error handling, and dry-run safety.

- **[x] One-command host bootstrap script** (`setup-host.sh`). Done 2026-05-30 — see the "P1 — Install automation" entry above for details. Remaining: a real-hardware run to confirm it (only `--dry-run`-tested so far).

- **[x] Surface install failures in the GUI summary popup** (verified done 2026-06-02), not only the log file. `MainWindow._show_dep_summary` appends an "Install failures:" block listing each failed dep + `InstallResult.message` (which `AutoInstaller` fills with the failing command's last stderr/stdout line), then points at the full log. Declines are excluded (the user already saw that dialog). Covered by `test_dep_summary_does_not_show_user_declines_as_failures`.

- **[x] Stop cascading the install dialogs when the user *declines*.** Done (verified 2026-06-02). `resolve_missing` skips cascade for `InstallResult.user_declined=True` (manager.py) — only real install *failures* cascade to the next tier. Both `AutoInstaller` (consent=No) and `QueuedInstaller` (empty selection) set `user_declined`. Covered by `test_resolve_missing_does_not_cascade_when_user_declines`, `test_resolve_missing_still_cascades_on_non_decline_failure`, and `test_dep_summary_does_not_show_user_declines_as_failures`.

- **[x] Version-stamp dependencies in the dep-report. Done 2026-06-02.** The probe already reads each dep's version; `DependencyReport` now carries `ok_versions` (dep_id → detected version), `check_all` populates it, and the summary popup lists an "Installed: whipper 0.10.0, FLAC 1.4.3, …" line (a version-less-but-present probe renders as "unknown"). New `version.format_version()` helper. Tests across `test_deps_version`, `test_deps_manager`, `test_ui_main_window`. *(Not done: pinning the Picard `.flatpakref` to a fixed version — that always tracks latest by URL; left as a separate question since pinning a Flatpak ref is non-trivial and the version is now at least visible to the user.)*

### P1 — UX gaps from real-user testing

Items that surfaced when an actual user walked through the GUI on Bazzite. Each is small but each makes the first-run experience noticeably worse.

- **[x] Show placeholder track rows for an unknown disc.** Done 2026-05-29 (T32). Previously the track table stayed empty when MusicBrainz had no match, so the user couldn't see what was on the disc before an unknown-album rip. whipper reports the track count even for an unidentified disc, so the adapter salvages it from `cd info`'s partial output (`DiscInfo.num_tracks`) and the main window renders that many rows via `TrackTable.set_placeholder_tracks()` — pre-filled with `Track 01`…`Track NN` titles + `Unknown Artist`, and album fields set to `Unknown Artist` / `Unknown Album` to mirror the tags the rip writes. The no-match handler is shared by the empty-disc-ID path and the 0-result-lookup path. **Follow-up is P2 (below):** edits to those rows don't yet feed the unknown rip.

- **[x] Live status during the pre-track disc scan.** Done 2026-05-29 (T32). The status label sat on "Starting rip…" for the whole initial TOC/table read (a minute-plus) because those whipper lines carry no track number, so the GUI looked frozen. `RipWorker` now emits a `status(str)` phase signal (`_describe_activity`) recognizing the disc-scan, per-track read/verify, encode, tag, and length phases; `RipProgress.set_progress` drives the bar only while `set_status` owns the label.

- **[x] Default path template → Artist/Album folders + per-mode templates.** Done 2026-05-29 (T32). Replaced the flat v1 `Artist - Album/` layout with two template pairs, picked per rip in `ui/rip_controls`:
  - **Known disc:** `%A/%d/%t - %n - %d - %A - %y` + disc `%A/%d/%d` → `Artist/Album/01 - Title - Album - Artist - Year.flac`.
  - **Unknown disc:** literal `Unknown Artist/Unknown Album/%t - Track %t` + disc `Unknown Artist/Unknown Album/Unknown Album` → clean `Unknown Artist/Unknown Album/01 - Track 01.flac`. This is what made the "Unknown Album now" choice safe — whipper never sees `%d` (the disc-ID hash) for unknown discs, so no post-rip renaming and no broken `.cue`/`.log` references.
  - All four templates are editable in Settings. Config schema bumped to v2 with a migration that upgrades the known templates only if they still hold the v1 defaults (hand-edited templates preserved); the unknown templates fill from defaults when absent.
  - **Flat-template caveats (documented in config.py):** a known disc with no year leaves a trailing " - " (whipper can't conditionally omit an empty field); disc-number/volume (`%N`) is always present so it's left out of the default — add `/%N` for multi-disc sets.

- **[x] Highlight the current track row during a rip. Done 2026-06-02.** The track table now follows whipper track by track. Note the mechanism changed: `RipWorker.progress` was reworked to `(overall, task)` percentages and no longer carries the track number, so this added a dedicated `RipWorker.current_track(int)` signal (emitted once per new track, derived from the `"track N of M"` lines the worker already parses) wired to `TrackTable.highlight_track()` (selects + scrolls the row; out-of-range numbers ignored). Tests: `test_emits_current_track_once_per_new_track`, `test_highlight_track_selects_matching_row`, `test_highlight_track_ignores_out_of_range`.
- **[x] Read offset field in Settings is misleading.** Resolved 2026-05-30 by the drive setup wizard (P1.1 / KDD-15): the field is read-only and now sits beside a "Re-detect…" button that launches the wizard — the supported way to (re)calibrate and write the offset to `whipper.conf`. (Still open as polish: parse `whipper.conf` to *display* the live per-drive offset rather than our config's stored copy.)
- **[x] PendingInstallsDialog visual feedback during install. Done 2026-06-02** (chose option 1: the dialog drives the install loop itself). `PendingInstallsDialog` now takes an optional `install_one` callable; when supplied, clicking "Install Selected" installs each ticked item in turn, updating that row live (`installing…` → `OK`/`FAILED`) then swapping in a Close button, with `results()` exposing one `InstallResult` per item (unticked → `user_declined`, so the manager won't cascade them). A new GUI resolver `main_window._DialogQueuedResolver` replaces `QueuedInstaller` in the GUI path (QueuedInstaller installs *after* its callback returns, which closed the dialog); `QueuedInstaller` itself is untouched and still used elsewhere. Row repaint uses `widget.repaint()`, NOT `QApplication.processEvents()` — the loop runs as a slot inside the modal `exec()`, and processEvents would re-enter that loop / pump unrelated timers+threads (a crash hazard caught in testing). Passive (no-`install_one`) mode preserved for existing callers/tests. Tests in `test_ui_pending_installs_dialog` + `test_ui_main_window`.
- **[x] Declined dependencies should not cascade to the next tier.** Done (verified 2026-06-02) — see the identical item under P1.1 above. `resolve_missing` skips cascade for `user_declined`; three tests cover it.
- **[x] Picard auto-install failure mode — resolved.** Both halves are done: (1) **root cause** — the registry now installs Picard via the **`.flatpakref` URL** (`https://dl.flathub.org/repo/appstream/org.musicbrainz.Picard.flatpakref`) instead of `flathub <ref>`; the `.flatpakref` carries the remote URL so flatpak adds flathub at *user* level on first install, fixing the Bazzite "No remote refs found for 'flathub'" error (Atomic distros configure flathub as a *system* remote). See `deps/registry.py`. (2) **diagnostics** — `AutoInstaller` captures the failed command's last stderr/stdout line into `InstallResult.message`, and `_show_dep_summary` surfaces it in an "Install failures:" block (no longer debug-only). Picard is also `optional=True`, so a failure doesn't nag.

### P0 — Exhaustive argument documentation + black-box limit testing, our half (2026-08-06)

Maintainer, and it is now `docs/seam-rules.md` **S-8/S-9/S-10** (version 2): *"i want it exhaustive on you side and on thiers. even if you dont use the argument or variabe or setting, i want i documented and with the limits and errors. we may have to use or fix in the future."* Plus the division of labour: *"i dont expect you to test cyanrip, its on them, just like its on you."*

- **[~] Black-box limit probes for every argument we DO send**, run against the real binary rather than read out of the builder: the **real** accepted min/max (the declared type is not the range — `int` says nothing about whether `-1` is taken); behavior at min, at max and **one past each**; and on a bad value the exit code, the message, and **whether the operation dies or the flag is silently ignored**. That last distinction is the difference between a bad tag and a lost rip: `-t 17=` on a 16-track disc killed a rip in two seconds and the *type* was fine.
  - *Audit 2026-09-25: partly done.* scripts/probe_argv_surface.py probes the builder for -r/-S/-Z/-s and tag shapes, not the real binary; -d/-c/-l/-t are not probed.
  - **Triaged 2026-11-16 (open):** the fork's black-box table has 133 probes over 19 flags, `-d`, `-c`, `-l` and `-t` among them (`docs/seam-commands.md:462-600`). Not probed: `-D`, `-F`, `-U`, `-W`, `--prefer-disc-isrc`, `--prefer-accuraterip-match`, `--reread-time-limit`, `--reread-until-accuraterip`.
- **[ ] The same for our own surface** — every `Config` field and every CLI flag, including ones the GUI cannot set. Same columns, same rule.
  - **Triaged 2026-11-16 (open, ours):** partly: §1a measures eight `Config` fields through the builder (`docs/seam-commands.md:169-243`); the other fields and the CLI flags are not measured.
- **[~] Interactions**: `-I` must never appear with `-J` in our builder and **neither of us has recorded why**; `-F` is in the builder with no recorded reason at all. Probe both, document both, or delete them — carrying a flag we cannot explain is worse than not having it.
  - *Audit 2026-09-25: partly done.* The fork's §7 records the -I/-J refusal and -F semantics; our §1 rows still say the semantics need confirming.
  - **Triaged 2026-11-16 (open, ours):** the fork's §7 records `-I -J` refused with exit 64 (`docs/seam-commands.md:604`) and calls `-F` the track naming scheme; our §1 cells still say *needs confirming* (`:109-110`). Cheap, but the file is shared, so it rides a lap.

### P0 — `set`/`expect` must key on Config field names, NOT row labels (audit, 2026-08-06)

**FIXED — `verbs.VERBS['set'].help` now reads *"set `<config-field>` `<value>` —
change a setting (validated, then saved); booleans take on/off"*.** The trap list
below stays as the record of why. Original: ~~`verbs.py` currently says *"set
`<field>` `<value>` — set a Settings field by its row label."* That is the wrong
design and the audit gives three in-repo proofs:**

1. **Seven form rows have the label `""`, five of them interactive** — `override_read_offset`, `notify_on_completion`, `save_additional_art`, `rerip_offset_variant`, `secure_rerip_dynamic`. There is no label to address them by, so a label-keyed namespace cannot reach five real switches.
2. **Labels are prose and they get renamed.** `option_labels.py` exists *because* every option string was renamed in b11 — a script pinned to `"Fixed speed (advanced)"` broke silently at that commit.
3. **A registry already exists, half-built:** `settings_dialog.py:700`'s `_validated_widgets: dict[str, QWidget]` already maps **config field name → widget**, for 8 of them. Generalising it gives `set`, `expect`, the validation renderer and the completeness test **one** source.

So: **canonical key = the `Config` field name; row label = an alias**, matched by equality after normalisation (never `startswith`/`in`), with ambiguous or empty aliases **refused at parse time** rather than guessed.

- **[~] Traps the audit found that any resolver must handle**, each of which would otherwise be a silent wrong answer:
  - `secure_rerip_dynamic` is **INVERTED** relative to its checkbox; `update_channel` is a **bool view of a string**.
  - `Read offset (samples):` names **two** widgets (the spin box and `Re-&detect…`) — the input must win or the resolver must refuse.
  - Substring collisions: `Track template:` ⊂ `Track template (unknown):`; `Verify FLACs:` and `Re-compress FLACs:` share `FLACs:`.
  - Unicode that will not survive a copy-paste: `×` is **U+00D7** (not ASCII `x`) in `Fixed speed (×):`; `…` is **U+2026**.
  - Mnemonic ampersands survive `.text()` — `Chec&k dependencies`, and `&&` renders as one `&`.
  - `metaflac path:` is the only lowercase-initial label; an over-eager `.title()` normaliser eats it.
  - `recompress_flac_after_rip` is **permanently disabled**; `mp3_vbr_quality` and `read_speed` are **gated** — setting a disabled widget must FAIL loudly, not no-op silently.
  - *Audit 2026-09-25: partly done.* `set` keys on Config field names (uiscript/runner.py), so the label traps no longer apply. A disabled field is not refused: recompress is disabled in Settings but settable.
  - *2026-10-07:* `recompress_flac_after_rip` is gone (maintainer: remove the inert setting), so the permanently-disabled case no longer exists; `mp3_vbr_quality` and `read_speed` are still gated and still settable while greyed.
  - **Triaged 2026-11-16 (open, ours):** a greyed `mp3_vbr_quality` or `read_speed` is still settable; nothing in the `set` handler checks a widget's enabled state (`uiscript/runner.py`).
- **[ ] The completeness test:** derive the editable set from the dialog and assert every one is addressable, so this audit cannot silently expire.
  - **Triaged 2026-11-16 (open, ours):** no such test in `tests/`.

### P0 — The RETURN path from cyanrip is unsanitised, and Qt's default renders it as HTML (found 2026-08-06)

The maintainer asked the mirror of the argv question: *"do all logs and commands pass back to platterpus from cyanrip before user facing? same deal, they probably should and get sanitized and checked ... this should be a check in both directions, and full."*

**Measured answer: the output half has no sanitiser at all.** Two greps settle it:
- ~~`grep -rn "setTextFormat|Qt.RichText|Qt.PlainText" src/platterpus/ui/` → **zero
  hits.**~~ **STALE — re-run 2026-08-27 returns seven hits.** Widgets carrying
  dependency output now pin `PlainText`; `tests/test_message_boxes_are_plaintext.py`
  sweeps the `QMessageBox` sites. The 13 `QLabel(<non-literal>)` sites remain
  outside that sweep and are still tracked.
- No sanitiser function exists on the return path (`ripper_messages.py`'s `re.escape` calls are regex construction, not output cleaning).

**Why that is a live defect, not a theoretical one.** Qt's default is `Qt::AutoText`, which **auto-detects HTML and renders it as rich text**. cyanrip's `captured_stdout` and `failure_hint` reach user-facing surfaces (`main_window_rip.py:1368`, `:1456`). So any captured line that *looks* like markup is interpreted rather than shown.

**The realistic failure is silent text loss, not an exploit.** cyanrip is a local trusted binary — but the *content* it echoes is not ours: album and track titles come from **MusicBrainz**, i.e. from outside. A title containing `<` — `Track <Remix>`, `A > B`, `<untitled>` — is swallowed as an unknown tag in a user-facing error dialog, and **the user never learns text went missing**. That is exactly CLAUDE.md's *validate every dependency output* category and exactly the silent-truncation shape the diagnostic-completeness rule exists to forbid.

- **[x] Pin every user-facing widget that can carry dependency output to `PlainText`**, and add a sweep test asserting no `QLabel`/`QMessageBox` receiving tool output is left on `AutoText`. The sweep matters more than the individual fixes — this is a rule to enforce across the codebase, not at the one place it was found (`docs/testing.md` §5.o).
  - *Audit 2026-09-25: partly done.* The QMessageBox sweep exists (tests/test_message_boxes_are_plaintext.py); the 13 QLabel(<non-literal>) sites are not swept.
  - *2026-09-25:* **Closed as a duplicate, not done.** The work is tracked in the row *"The 13 QLabel(<non-literal>) sites are outside the PlainText sweep."*, which is now done (2026-09-30 audit).
- **[x] Add the return-path sanitiser as the mirror of `sanitise_cyanrip_args`**: strip/flag control characters and NULs, bound absurd line lengths (a 10 MB single line will freeze the GUI thread rendering it), and preserve everything else verbatim. It must **never silently drop** — an elision is counted and marked, same rule as the argv side.
  - *Audit 2026-09-25: confirmed open.* Confirmed: no control-character/NUL flagging or per-line length cap on ripper output, only head-and-tail line-count elision (rip_worker.py).
  - *2026-09-25:* **Done** as `inbound_text` (see the `rule-12.inbound-sanitising` row). The QLabel half of rule #12's plain-text pinning is still open, in its own rows.
- **[x] Institutionalised in both repos.** The clause is now a bullet of Critical rule #12 in `CLAUDE.md` (which is the bidirectional-seam rule and already carries the "this rule lives in both repos" obligation), and the fork's half is drafted ready to send as [`docs/handshake/verified/round-07-lap-29.md`](docs/handshake/verified/round-07-lap-29.md) §S. That file describes **our own two defects** rather than proposing a clause from a clean position, asks which of their routes reach the ripping core, and asks for confirmation the clause landed on their side so the next round can cite it instead of re-arguing it.
- **[x] Make it a two-way contract test.** The input half is `tests/test_argv_surface_agreement.py`. The output half has parser tests but nothing asserting *what reaches the user* is what cyanrip said. That asymmetry is the same one that let the `-V` blocker ship for a full round.
  - *Superseded 2026-10-12*: the output half is asserted by `tests/test_ripper_error_surfacing.py::test_every_string_the_ripper_can_print_is_surfaced` and `::test_every_other_inventory_row_still_reaches_the_user` (the fatal inventory reaching the user), with `tests/test_provider_contract_agreement.py` checking the parser against their provider contract.

### ✅ DONE — Handshake lap 28: our sent verdict was wrong on both halves (2026-08-06)

**Acted on in `verified/round-07-lap-29.md`**, which withdrew the stale HOLD reason.
Round 7 later closed GO/GO at lap 41. Kept as the record:

**Our lap 27 is sitting in the fork's inbox making two false statements**, both verified against committed artifacts rather than remembered:

- **[x] The HOLD's only stated reason has evaporated.** Lap 27 line 20 declares `**HOLD on f5e11ba**` because *"the P1 flag table still has not arrived"*, and line 297 says our argv check is *"diffing our argv against **round 6b's** table"*. Both false today: `docs/handshake/inbound/artifacts/round-07-lap-25-provider-contract-g9048082.md` exists (738 lines, 45 KB, 2026-08-05 18:51), and `tests/test_argv_surface_agreement.py` has `_MAX_TABLE_LAG = 0` and passes — it reads round 7's own table.
  - *Audit 2026-09-25: done.* verified/round-07-lap-29.md §D.1 withdraws the lap-27 HOLD.

- **[x] Lap 27 recommends a pin our own product has retired.** Line 285: *"**No pin change requested.** `f5e11ba` remains our test pin and our recommendation."* Meanwhile `deps/fork_source.py:200` has `FORK_TEST_PIN = "9048082"` and line 252 lists `"f5e11ba"` in `SUPERSEDED_TEST_PINS`. The wizard installs `9048082`; the handshake file recommends `f5e11ba`. **The code and the contract disagree about which binary we want**, which is exactly the class of drift rule #12 exists to prevent.
  - *Audit 2026-09-25: done.* round-07-lap-29.md §D.2 names that lap 27 held on the superseded f5e11ba.

- **[x] Root cause, and it is theirs: lap 25 was sent THREE times under one lap number.** Protocol §2 is unambiguous — *"Each lap is a new file. Never edit a file already sent."* On disk: `superseded/round-07-lap-25-as-first-sent.md` and `…-as-second-sent.md` both carry `HANDSHAKE-TEST-PIN: f5e11ba`; the live `inbound/round-07-lap-25.md` carries `HANDSHAKE-TEST-PIN: 9048082` and attaches the contract. **Our lap 27 was written against the second send.** So it is a faithful reading of a document that was replaced under the same name — which is the precise failure §2 forbids, and it needs raising as an ask, not as a complaint.
  - *Audit 2026-09-25: done.* round-07-lap-29.md raises lap 25 sent three times as Ask D-1.

- **[x] Second-order finding worth more than the first:** the table arrived and *our own check still could not see it* for a further lap, because `_group_by_round` globbed only lap files and the shared round parser returns `None` for an artifact filename (fixed in `8a045ab`). **A contract sitting in a directory nothing reads is not a contract received.** Already graduated; restate in lap 28 because it is the transferable half.
  - *Audit 2026-09-25: superseded.* The fix landed (tests/test_argv_surface_agreement.py globs the artifacts); round 7 closed at lap 41.

- **[x] Also stale in lap 27, by construction:** `HANDSHAKE-APP-VERSION: platterpus 0.6.4b8` (now b11), and §F cross-references §G ("Revert-proof") for the flag-table blocker that actually lives in §K — a reader following the pointer lands in the wrong section.
  - *Audit 2026-09-25: superseded.* Lap 27 was replaced by lap 29; round 7 closed GO/GO at lap 41.

**Still true in lap 27 and to be re-asserted rather than re-derived:** the consumer-contract counts (55 parsed / 17 ignored / 18 flags) survive regeneration at b11; the drive-proven A1/A2/`--verify-log` rows stay citable *scoped to `f5e11ba` + b6/b7/b8*; and the standing caveat that nothing here exercises a *stock* cyanrip.

**Lap 28 must not claim** anything needing rig data we do not hold — in particular it cannot approve `9048082` on evidence, because no disc has been ripped on it yet. Their own §E1 says they are not asking us to approve it untested.

### P1 — Rig-session findings, 2026-08-05 (b10 + cyanrip `9048082`) — SHIPPED in v0.6.4b11

Raised by the maintainer while walking through the b10 build on the Bazzite rig, recorded first and acted on after his go-ahead (*"only options, roll a new version if needed after ingesting all this data"*). Every claim below was verified against the code *before* being written down, because two of the five turned out not to be what the screenshots suggested — and those two are marked as **refuted**, not fixed.

- **[x] The naming ask — DONE for the option labels; the `[Debugging]`-on-the-Goal-row half is still a decision for the maintainer.** Shipped in v0.6.4b11: `option_labels.py` defines the one convention (`Name — Descriptor In Title Case [Qualifier]`) with a pure `check_option_label()`, and `tests/test_option_labels.py` sweeps every item of every combo in the *constructed dialog* — not a table of the labels we know about — so a sixth dropdown is covered without anyone remembering. Pinned non-vacuous by a test asserting all 19 pre-rename labels fail the checker, and by one asserting every combo still carries the same item data. `naming.CUSTOM_LABEL` is now the shared constant. **What is deliberately NOT done:** annotating the *Goal* row with state no preset owns (his `[Debugging]` example). That needs a decision on which fields a label may speak for, and `docs/rig-session.md` §1 asks him for it.
  - *Audit 2026-09-25: partly done.* option_labels.check_option_label and tests/test_option_labels.py exist; the Goal-row [Debugging] suffix awaits the maintainer.
  - *2026-09-25:* **Closed as a duplicate, not done.** The work is tracked in the row *"Decide the [Debugging]-on-the-Goal-row question. Still the maintainer's"*, which is now decided (D6 C, 2026-09-30 audit); the build is the row *"Build D6 C: descriptive preset names, and a separate line for state no preset"*, which stays open.

  Original ask: Maintainer's words: *"These settings should be called something like Flack - Lossless Archival Master [Debugging] or similar, and other settings should reflect similar naming syntax."*

  **The "auto-change to Custom" half of the request already works, and that is verified rather than assumed** (`goal_presets.py:85-89`, `settings_dialog.py:67-70`, `_on_dependent_changed` at `:940-946`; run offscreen against the real dialog: all six preset-driven controls flip the combo to `Custom (hand-tuned below)` immediately, `to_config().rip_goal == "custom"` persists it, and a config matching no preset re-opens showing Custom. Pinned by `test_editing_a_control_flips_goal_to_custom` and `test_every_goal_preset_field_has_a_wired_control`).

  **So what he is actually asking for is different from what it looks like.** His screenshot shows `Archival exact` while **Debug logging is on** — and debug logging is *not* a goal-driven field, so nothing is wrong. He wants the label to describe state the preset does not cover. That is a design question, not a bug: decide which fields a label may mention, and whether a `[Debugging]`-style suffix is a *label* or a separate status line. Scope for a rename: `GOAL_LABELS` is the single source for the three presets, but `"Custom (hand-tuned below)"` is a **hardcoded literal** at `settings_dialog.py:70` that duplicates `naming.CUSTOM_LABEL` (used by the unrelated naming-scheme combo — renaming naively renames both), and the labels are restated by hand in `help_content.py:169-173`, `README.md:11`/`:548`, `PLANNING.md:151`/`:310`, `docs/ux-design-principles.md:46`/`:110`, `docs/test-plan.md:725`.

- **[x] One genuine defect found while checking the above: the Goal combo ignores the persisted `rip_goal`.** **FIXED in v0.6.4b11** — resolved in favour of *the fields are authoritative, the label is a view of them*, which is `detect_goal`'s documented semantics. `rip_report.build_settings` now derives `settings.rip_goal` through the same function the dialog uses, and keeps the stored value as `settings.rip_goal_stored` **only when the two disagree** (report schema v23) — discarding a disagreement silently would be the same class of bug in a smaller place. Five regression tests, and the revert was applied-and-proved before believing the run. `_wire_goal_presets` re-derives from the field values via `detect_goal` and never reads `config.rip_goal`, so a saved goal can disagree with what the dialog shows (measured: `Config(rip_goal="custom")` with default fields re-opens as `fast_verified`). Harmless today because the derived answer is the truthful one — but the report writes `settings.rip_goal` into every rip's JSON, so the *record* can name a goal the settings never matched. Decide which is authoritative and make the other follow.

- **[x] The dependency dialog truncates the ripper version and names no commit. CONFIRMED, and it is captured-and-discarded.** **FIXED in v0.6.4b11** — `BuildNote` gained `version_text` and `build_tag` (both read off the `RipperIdentity` the dialog already receives) plus an `identity_line()` renderer, so the row now reads `cyanrip 0.9.4-rc1+platterpus.5-beta.5 (the Platterpus fork; build tag "platterpus-fork-g9048082")`. The `; build tag "…"` shape rather than `, build …` because the unknown-build summary is literally the words "build not identified", and a comma there produced "build not identified, build g1a2b3c4". It shows `cyanrip 0.9.4 (the Platterpus fork)` where the binary's own banner is `cyanrip 0.9.4-rc1+platterpus.5-beta.5 (platterpus-fork-g9048082)`. Two independent losses: `deps/version.py:33-35` reduces the version to an int triple, so `-rc1+platterpus.5-beta.5` is structurally unrepresentable, and `build_notes.py:100-107` collapses the build to the four-word phrase `"the Platterpus fork"`. **Both the full banner and the build tag are live in the object the dialog receives** (`probe.raw_output`, and `identify_from_banner().build_tag`) — so this is the exact shape `CLAUDE.md` names: *"our dependency dialog reading `cyanrip 0.9.3` / `0 missing`: every word accurate, the message wrong."* It is also rule #12's *say which build* obligation unmet on the surface a user actually reads.

- **[x] The setup-wizard rows name no build either. CONFIRMED.** **FIXED in v0.6.4b11** — `_title_for` / `_done_detail` / `_ran_detail` on `HostSetup`; the row reads `… — commit 9048082` with `already present — the installed banner names commit 9048082`. Worded to match what `_fork_installed` actually checks (the tag *contains* the pin) rather than claiming an equality nobody tested. The fork row renders exactly `✓ Platterpus fork of cyanrip (build + export) — already present` (or `— installed`); `host_setup.py:451-463` titles, `:514`/`:591` details. **The `ForkTarget` is already read inside the very probe that produces that row** (`host_setup.py:294-295` reads `self._target.pin` to decide "already present"), and it exposes ready-made `build_tag` / `banner` / `why` strings that no UI consumes. So the row can say which commit it checked for at no new cost.

- **[x] The release picker logs nothing at all, so a wait for input is indistinguishable from a hang.** **FIXED in v0.6.4b11, and fixed on the shared base rather than at this one call site** (`docs/testing.md` §5.o). `CenteredDialog` now logs `dialog presented:` from `showEvent` — which makes the line *evidence Qt mapped the window*, a stronger claim than a line before `exec()` — and `dialog closed: … — accepted / rejected or closed` from `done()`, the single funnel accept/reject/Esc/WM-close all route through. The picker additionally logs the candidate count, the words "this is not a hang", the elapsed wait, and the chosen mbid; the accepted-with-no-selection branch is a WARNING rather than a silent return, because a silent return there reads exactly like a cancel. Nine tests across two files, including a floor asserting the single-match path emits *none* of these lines — otherwise the others would be satisfied by one `log.info` at the top of the method. The maintainer closed the app because it *"looked hung"*; the log has a **96-second silence** (19:36:41 → 19:38:17) and the main window was showing `MusicBrainz match: 4 matches found — pick one`.

  **The mechanism I first suspected is refuted:** a modal wizard/message box cannot swallow the picker, because the MB result arrives as a queued cross-thread signal and nested Qt event loops still deliver those. But `main_window.py:1090-1099` calls `dialog.exec()` with **no log line on any branch** — not opened, not waiting, not accepted, not cancelled — and `disc_info_panel.py` does not import `logging` at all. **So a 96-second silent gap is exactly what this path produces whether or not the dialog was visible, and the artifact cannot tell us which happened.** That is the finding: not "the picker was hidden" (undetermined), but "we cannot answer the question from the log". Log the picker's lifecycle first; only then is a hidden-dialog claim checkable.

- **[x] My own instruction was wrong: `./platterpus-x86_64.AppImage --install-ripper 9048082` fails after the app relocates itself.** **DONE in v0.6.4b11** — `README.md` → *Command-line usage* now opens by saying where the file actually is and that a `./` command from the download folder will report *No such file or directory*; the `--install-ripper` example uses the `~/Applications/` path; the same note is in `docs/test-plan.md` §A3 and `hardware-test-checklist.md`. The AppImage is **moved** (`shutil.move`, `appimage_integration.py:93`) to `~/Applications/` — but only after an explicit Yes, and the app *does* name the new absolute path in a follow-up dialog (`main_window_provision.py:192-199`). So the app behaved correctly and the docs did not: sweep every bare `./platterpus-x86_64.AppImage …` command in `README.md` and `docs/` and make them relocation-safe. Also worth noting for the record: the b10 wizard built `9048082` on its own, so the manual step was never needed.

### P1 — Trust & supply-chain hardening (2026-07-08 audit follow-ups)

- **[~] Reproducible AppImage build.** **`SOURCE_DATE_EPOCH` — DONE (2026-07-08):** `build_appimage.sh` pins every embedded timestamp to the HEAD commit time; verified the *wheel* is byte-identical across rebuilds (same sha256). **`pip --require-hashes` dependency byte-pinning — PLUMBING SHIPPED (2026-07-21, Option A, maintainer-chosen):** the python-appimage-compatible design is a **hash-verified wheelhouse** — `build/lock-requirements.sh` resolves the third-party closure and writes a hash-pinned `requirements.lock` (run in the release env when a dep changes); `build_appimage.sh`, *when the lock exists*, `pip download --require-hashes`-es the closure into a local wheelhouse (aborts on any byte mismatch) and installs python-appimage's per-line deps **offline** from it, with the local `platterpus` wheel served alongside. It's **opt-in and additive** — no lock ⇒ the previous version-pinned online install, unchanged. Parsing logic unit-verified; scripts `bash -n`-clean. **Still gated on a real build (only place it can be validated):** generate the lock in CI/the release env, commit it, and confirm the *full* AppImage is byte-identical across rebuilds (the sandbox can only verify the wheel half).
  - *Audit 2026-09-25: partly done.* SOURCE_DATE_EPOCH and --require-hashes plumbing are in build_appimage.sh; no requirements.lock is committed, and full AppImage byte-identity is unproven.
  - *2026-10-27 (the review's follow-up to items 2.1 and 2.3): the lock is committed and REQUIRED.* `build/lock-requirements.sh` now resolves it with uv for the bundled target (CPython 3.12, manylinux_2_34_x86_64) rather than the host's Python, which the pip-report version could not do; the build refuses to run without it, refuses a lock for another CPython, and downloads for that target. Replayed offline on CPython 3.12.3 it installs exactly the 36 locked versions; the full build in this sandbox stopped at the base-image lookup (GitHub API 403), so `appimage.yml` on the branch is the whole-build proof. **Still open:** full-AppImage byte-identity across two rebuilds, which needs two real builds.
  - **Triaged 2026-11-16 (open, ours):** hashed locks are committed (`build/locks/release.lock`, R91); two builds are still never compared (no such step in `appimage.yml` or `release.yml`).

### P1 — Documentation backlog

- **[ ] Add a screenshot or two** of the GUI to the top of the README once T32 confirms it looks right on Bazzite KDE Plasma 6. *(Needs a real GUI screenshot — hardware/display; [docs/test-plan.md](docs/test-plan.md) Test 5.)*
  - *2026-09-25:* **Decided (D10 A):** take two of the screenshots the next Full run saves in its bundle. I pick, the maintainer approves. ~~Waits for that run.~~
  - *2026-09-30: unblocked.* The acceptance runs of rounds 27–29 have happened (Full on
    rounds 28 and 29), and their session bundles hold the screenshots. The pick is owed,
    not the run.
  - **Triaged 2026-11-16 (owner):** still none (`README.md:2` is the icon); D10 A, the maintainer picks from filed bundles.
- **[ ] Document Picard's actual auto-launch behavior** under Step 6 once T32 verifies it. The README currently says it works "if you enable the toggle"; T32 will confirm what the toggle UX actually feels like end-to-end. *([docs/test-plan.md](docs/test-plan.md) Test 6.)*
  - **Triaged 2026-11-16 (hardware):** README Step 6 (`README.md:400-415`) no longer mentions the toggle; the auto-launch on an unknown disc is undocumented there and still waits on Test 6.

### ⭐ P1 — EAC parity: **CLOSED at 14/14 on real hardware (2026-08-04)**

The rig rip of the baseline disc — b3 + `platterpus-fork-g9003e6f`, same drive, offset
+667 — is **bit-identical to EAC on all 14 tracks**, and its ten `Pre-gap length` rows
match EAC's to the hundredth of a second in order. Artifacts committed to
`output_reference/cyanrip_fork_flac/`; proven by `tests/test_fork_rip_eac_parity.py`,
which reads them.

- **[ ] MP3 / WAV parity rows** — the matrix's other formats are unchanged and still
      pending; only FLAC is proven.
  - **Triaged 2026-11-16 (owner):** unchanged; each derived file is checked per rip by `adapters/derived_verify.py`, so this may close on the maintainer's word (the 2026-10-12 reading).

### P1 — Carried over from cyanrip handshake round 7 (2026-08-04; the round CLOSED GO/GO at lap 41)

Four files so far: our `outbound/round-7.md`, their `inbound/round-7.md` (lap 1), our
`verified/round-7.md` (lap 2), their `inbound/round-07-lap-02.md` (their lap 2), and our
`verified/round-07-lap-03.md` (lap 3). **Both sides declare HOLD.** The round is OPEN and
**neither project releases** — now enforced bilaterally rather than remembered.

The pin stays `2f950c8` (r2). **Four SHAs in one open round** — `ad65a24` → `d5d12ec`
→ `345241b` → `5bc654d` (r4, `0.9.4-rc1+platterpus.4`) — recorded as
`NEXT_PIN_UNDER_REVIEW`, **not installed**. The gate is what has kept us on r2
through all four.

**Protocol v2 adopted.** `docs/handshake-protocol.md` is the SHARED spec, verbatim
from the fork; our own §8 points at it instead of restating it. Conformance is
`tests/test_handshake_conformance.py`, one test per §8 row (T15 — **done**, and it
found row 12 failing on our side: an empty record allowed a release).

**We had not sent them `outbound/round-7.md`.** They asked three times; Q8, which we
cited three times as blocking our addendum fix, was in it. Delivered with lap 3. Our
process failure, not their oversight: the protocol says two files per round and we sent
one.

**The deadlock, and the two betas.** The fork found that our shared rules are
unsatisfiable as written (their lap 6 §1): a round cannot close without
`HANDSHAKE-TESTED`; that evidence needs the reviewed build on the rig; installing it
is forbidden while the round is open. Their fix is `HANDSHAKE-TEST-PIN` — a build for
gathering evidence, which never closes a round and never moves the production pin.
Adopted. Ours is a **pre-release**, because our artifact is an AppImage a user
downloads rather than a tree they build: `--release-gate --prerelease` permits it
loudly, `--release-gate` still refuses a stable release.

**Both betas are cut and both are named in writing (their lap 8, our lap 9).**

```
Platterpus  v0.6.4b1                        GitHub pre-release, assets attached
cyanrip     0.9.4-rc1+platterpus.5-beta.2   commit c5fb909 on platterpus-fork
                                            (was beta.1 / 9003e6f — moved in lap 21)
```

**`beta.1` was worn by four commits, which is why the *tag* is the pin and the version
never is.** Laps 8–20 all declare `0.9.4-rc1+platterpus.5-beta.1`, across `9003e6f`,
`ceca8bc`, `f00cb2b` and `486dce3`, while `HANDSHAKE-SOURCE-ANCHOR` moved twice
underneath it — and one of the changes it spans is a **log value we parse** (track 1's
`Pregap length:`, the lead-in counted twice). Our classifiers key on the build tag, so
nothing here broke; a human reading a report's `ripper_version` could not have told which
behavior they had. Raised as lap 22 §D1/I2.

- **[ ] T14(c) — `Duration:` must agree with `Samples:` in both passes' logs.** Their
      three-part restatement of T14; (a) is done, (b) is blocked on Q8, (c) needs a
      `Duration:` field we do not yet parse. Queued behind that field rather than
      half-landed.
  - **Triaged 2026-11-16 (open, ours):** per-track `Duration:` is still not parsed (`parsers/cyanrip_log.py` keeps `disc_duration` only, `:1995`).

### P1 — Open from cyanrip handshake round 6 (2026-08-03, closed on pin `2f950c8`)

Each item is either queued with the reason it is queued, or hardware-gated. Nothing
here blocks the v0.6.3 release; round 6 is CLOSED both directions.

- **[~] Assert the read offset is CORRECT, not merely applied.** Already ranked #3 in
      `docs/eac-parity.md` Part D §4 and still open; the audit of the previous backend re-surfaced it as
      the second-highest-value gap. We have the drive table
      (`adapters/accuraterip_offsets_data.py`); the log can say `+667 (matches the
      AccurateRip database for PIONEER BD-RW BDR-209D)`. Worth −5 on the real rubric, so
      it is a genuine quality row rather than cosmetics, and a wrong offset silently
      corrupts every rip. Borrow the previous backend's *consensus* discipline
      (its `command/offset.py:168` — confirm across tracks 2..n−1, require agreement), **not**
      its disc-based probe, which its own README calls "quite primitive" and which our
      adapter records failing on the BDR-209D with an in-database disc (KDD-31 stands).
      **Report and results pane DONE 2026-10-21** (the owner's known-fixes list of
      2026-10-21, item 11). `read_offset_check.py` looks the drive the rip's own log
      names (`Drive used:` / `Device model:`, revision and interface words dropped) up
      in the AccurateRip list by `OffsetDatabase.lookup_entry`, the one rule the app
      also applies offsets with. `rip.read_offset_check` (schema 39, an addition)
      records `matches` / `differs` / `drive_not_listed` / `not_determined`, the
      list's row and value, and KDD-31's evidence beside it (`accuraterip_reconfirms`:
      `confirmed` / `not_confirmed` / `not_determined`). `differs` raises the
      `read_offset_differs_from_accuraterip` warning, `drive_not_listed` an info
      issue; the results pane prints the same sentence with a `✓`/`⚠`/`ⓘ` marker.
      Held by `tests/test_read_offset_check.py`. The consensus discipline above is
      not built: KDD-31's re-confirmation counts matching tracks, it does not
      require agreement across tracks 2..n−1.
      **Still open: the EAC-layout log**, which the fork diffs, so its wording is not
      changed here. **PROPOSAL for our next round-36 lap.** EAC's own log prints only
      the number and says nothing about the database, in its header or anywhere else
      (all three `output_reference/EAC_*/*.log`, line 14: `Read offset correction                      : 667`; line 7:
      `Used drive  : PIONEER BD-RW   BDR-209D   Adapter: 1  ID: 0`). So we do not
      forge an EAC line. We keep EAC's row and value exactly and add our own
      parenthetical after two spaces, as the `Defeat audio cache` row already does
      (`eac_log_export.py`, "(measured for this drive with cd-paranoia -A, …)"). The
      exact lines, one per state:

      ```
      Read offset correction                      : 667  (matches the AccurateRip drive offset database for PIONEER BD-RW BDR-209D)
      Read offset correction                      : 48  (the AccurateRip drive offset database gives +667 for PIONEER BD-RW BDR-209D)
      Read offset correction                      : 667  (this drive is not in the AccurateRip drive offset database)
      Read offset correction                      : 667
      ```

      The last is `not_determined`: unchanged from today. To settle before the lap
      (from the logchecker source `docs/eac-parity.md` Part D already reads): whether a
      logchecker reading `Read offset correction                      :` takes the whole rest of the line as the
      value (it would then misread the suffix); if so, the fallback is the same
      sentence on a line of its own after `Gap handling`, outside EAC's rows.
  - **Triaged 2026-11-16 (open, ours):** the EAC-layout wording was proposed in our round 36 lap 3 S12 (`docs/handshake/outbound/round-36-lap-03.md:100`) and is not built (no such text in `eac_log_export.py`).
- **[ ] Use the per-track paranoia counts to strengthen `track_read_effort_flag`.**
      The data landed 2026-08-24 (`TrackResult.paranoia_counts`); the *use* did not,
      deliberately. `rip_log.py`'s note says the flag cannot catch a disc whose
      paranoia settles on one wrong answer per pass — `rip_count` 1, `converged`
      None — and per-track READ/VERIFY/OVERLAP is exactly the missing signal. It
      needs a threshold, a threshold needs evidence from more than one disc, and
      inventing one would swap a documented gap for an undocumented guess. Gate on
      a hardware round with a marginal disc.
  - **Triaged 2026-11-16 (hardware):** unchanged: `track_read_effort_flag` (`parsers/rip_log.py:931-951`) does not read `paranoia_counts`.
- **[ ] Parse `Encoder:` and `CD-TEXT:` into the report schema, then off the ignore list.**
      Both are real archival facts the fork added for us, both currently on
      `_IGNORED_DISC_LINES` with a recorded reason. Queued rather than half-landed because
      a regex with no rendered home is dead code that reads as coverage. `Encoder:` is
      encoder provenance (which ffmpeg built the files); `CD-TEXT:` is tri-state
      (present / absent / unreadable-by-this-driver) and closes an EAC parity row. The
      fork's method for `Encoder:` — assert it against `ffprobe` output rather than
      against the line itself — is the one to copy. Note the populated disc-level form is
      richer than our golden reference shows (`present (English, 5 disc fields, 2 of 2
      tracks tagged)`), and there is now a per-track indented `CD-TEXT:` block too.
  - **Triaged 2026-11-16 (open, ours):** both still on the ignore list (`parsers/cyanrip_log.py:3539`, `:3548`).
- **[ ] Surface `Cache model:` as a *modelled* figure, distinct from our measured verdict.**
      Deliberately NOT wired to `defeat_audio_cache` (KDD-25/29 — see the recorded reason
      on the ignore-list entry). If shown at all it needs its own row, labelled as
      paranoia's model with the drive unprobed.
  - **Triaged 2026-11-16 (open, ours):** still ignored (`parsers/cyanrip_log.py:3505`).
- **[ ] Consume the progress line's `, errors - %i` segment.** Their P2a declares it and
      we ignore it, so we learn the error count only from the finished log. Surfacing it
      would let rip-progress say "reading, 3 errors so far" instead of looking healthy
      until the end. Note it resets per `-Z` pass, like the paranoia counters.
  - **Triaged 2026-11-16 (open, ours):** still not consumed; `redraw_run.py` only folds the redraws.
- **[~] Migrate `I:` / `LRA:` off libavfilter's wording onto the fork's `(R128)` rows.**
      Their A5 delivery: `Integrated loudness (R128):` and `Loudness range (R128):` are
      fork-owned and stable, where the unqualified headings we currently read are
      libavfilter's and move when FFmpeg does. **The `(R128)` qualifier is required** —
      libavfilter prints the unqualified spellings in the same track block, so an
      unqualified pattern matches two different lines. Needs report-schema fields first,
      same reason as `Encoder:`.
  - *Audit 2026-09-25: partly done.* Album-level (R128) rows are parsed with precedence; per-track (R128) rows are still unparsed.
  - **Triaged 2026-11-16 (open, ours):** album-level `(R128)` rows are parsed (`parsers/cyanrip_log.py:1333`, `:1340`); per-track ones are not.
- **[ ] The cancelled-rip log addendum, properly.** Their J2 is right that appending after
      `Log FUN512:` breaks `cyanrip -Y`, and the naive sidecar regresses bug #19 (the
      shipped-CRC statement lives in that text). Needs the real fix, not the sidecar.
  - *2026-09-25:* **Decided (D13 A):** Platterpus's part (which tracks were kept, and their checksums) goes in the JSON report only. cyanrip's log stays exact, so `cyanrip -Y` still verifies it, and no sidecar is written. Ready to build.
  - **Triaged 2026-11-16 (undecided):** see E15's note of the same date: whether the report a cancelled rip already gets (`ui/main_window_rip.py:2221`) meets D13 A needs a filed cancelled-rip report read.

### P1 — Thread-cancellation follow-ups (opened 2026-07-29, from the v0.5.17 audit)

- **[~] Give `run_capture` a killable child so the remaining no-cancel workers can actually cancel.** **Two** workers block and expose **no `cancel()` at all**: `MusicBrainzWorker` and `UpdateCheckWorker`. (Count corrected 2026-07-31 — this entry said "the five" and named `DependencyCheckWorker` and `DiscInfoWorker`, both of which gained real cancels on 2026-07-29, the same day the entry was written; `DriveListWorker` is the third name still on the ratchet but does **not** block — it only globs `/dev` and reads sysfs, so it is permanent-by-nature rather than debt. Re-derive the roster from `tests/test_qthread_ownership.py::_WORKERS_WITHOUT_CANCEL` before starting.) With no `cancel()`, `stop_thread` has nothing to call: `quit()` never reaches a thread blocked in a subprocess or socket read, and closing the window waits out its share of the shutdown budget and then **abandons** the thread. That is bounded and non-fatal — abandonment retains the reference and makes exit bypass interpreter teardown (`platterpus.hard_exit`) — but it is not cancellation, and a stalled network or cold container is exactly when a user closes the window.
      The fix is one change in the shared helper, not one per worker: port `run_capture` from `subprocess.run` (which hides the child, so there is nothing to signal) to `Popen` with **`start_new_session=True`** — load-bearing, because without it the child shares the GUI's process group and a `killpg` would signal the GUI itself — exactly as `adapters/cache_probe.py` now does, then thread a cancel through the workers. Note both remaining workers are **network**, not subprocess (urllib/musicbrainzngs), so `run_capture` alone does not reach them: there is no child process, and interrupting means closing the socket out from under the request. Different mechanism, same acceptance.
      **Acceptance:** each gains a `cancel()` that actually interrupts its block; the `_WORKERS_WITHOUT_CANCEL` ratchet in `tests/test_qthread_ownership.py` shrinks by one per worker and its upper bound comes down with it (the list may only shrink — CLAUDE.md rule 10's discipline). Deliberately its own cycle: it touches the helper every backend probe goes through, and this is the kind of change that has historically introduced the next bug when bolted onto the end of another one (`docs/testing.md` §5.s).
  - *Audit 2026-09-25: partly done.* run_capture is now a killable Popen (rip_backend.py). MusicBrainzWorker and UpdateCheckWorker still have no cancel() (the ratchet in test_qthread_ownership.py).
  - **Triaged 2026-11-16 (open, ours):** `MusicBrainzWorker` and `UpdateCheckWorker` are still on the ratchet (`tests/test_qthread_ownership.py:497-499`).

- **[ ] Hardware round for the v0.5.17 cancellation work.** The suite proves the mechanisms fire; only the Bazzite + BDR-209D rig with a real disc proves the **drive stops**. Watch specifically: (1) **Cancel, then quit within five seconds** — does the reader stop and does the eject button work? (2) **Force stop** mid-rip — recorded as *cancelled*, not *failed*, in the report and the signed log? (3) **"Set up drive"** at a small window size — any clipped text? (4) **Close the window mid-rip** — no abort. Flagged honestly as hardware-gated rather than implied by a green suite.
  - *Audit 2026-09-25: not ours to verify.* The maintainer's hardware run.
  - **Triaged 2026-11-16 (hardware):** still the maintainer's rig run.

---

## P2 — future enhancements (post-P1)

Items that are technically achievable but represent significant effort, double the rip time, or otherwise belong after the P1 backlog has settled. Pull from here when there's a concrete user request.

- **Test & Copy dual-pass rip — DOWNGRADED (largely already delivered).** Re-evaluated 2026-05-30 during the EAC-successor research review: **whipper already performs a test read and a copy read per track and records both CRCs** (your T32 log shows `Test CRC == Copy CRC` for all 16 tracks, and `(try 2)` re-reads on mismatch). We already surface this as the fidelity summary ("all N tracks verified, Test/Copy CRCs match"). So the core guarantee EAC's Test&Copy provides is already in hand. The only delta would be EAC's literal *two separate full passes* of the whole disc — marginal extra assurance at 2× rip time. Not worth building unless a user specifically asks for the two-full-passes behavior; keep parked here.

**From the 2026-06-23 EAC-guide gap analysis (P2 ideas; [docs/archive/archival-extraction-guide-2026-06.md](docs/archive/archival-extraction-guide-2026-06.md)):**

- **[ ] AcoustID fingerprint fallback.** Identify discs that MusicBrainz can't match by disc ID via audio fingerprinting (needs a personal AcoustID API key + `chromaprint`/`fpcalc`). Would route through the dependency subsystem; honors Critical Rule #5 (GUI resolves, not the ripper).
  - **Triaged 2026-11-16 (owner):** not built as an identification fallback; cyanrip prints its own `AcoustID:` line since upstream rc3 (`parsers/cyanrip_log.py:3559-3566`), and whether a rip under `-N` fingerprints is R31's `-B` cell.
- **[ ] Lyrics fetch + embed.** The guide tags `LYRICS=` from a file; we fetch none. A lyrics source behind a small adapter → embed via metaflac. Niche.
  - **Triaged 2026-11-16 (owner):** not built.
- **[ ] Embed the cuesheet in FLAC metadata.** cyanrip writes a sidecar `.cue`; FLAC can hold the cuesheet in a metadata block (`--cuesheet`). Nice-to-have for single-image rips.
  - **Triaged 2026-11-16 (owner):** not built.

**Graduated out of the multi-format design-of-record when it was archived (2026-08-06):**

- **[ ] Embed the cover art *inside* the `.wv` (the one open item from the WavPack ship).** WavPack carries art as a **binary APEv2 tag** (`Cover Art (Front)`), and **ffmpeg's WavPack muxer accepts only a single audio stream**, so the shipped transcode path physically cannot embed it. Today's behavior is a deliberate, working fallback, not a silent gap: whenever a non-embedding format is selected, art is wanted and the disc was identified, the GUI **force-writes the front cover to the album folder as `cover.<ext>`** — even in the default "embed" cover-art mode, which normally embeds in the FLAC and deletes the folder copy. So a WavPack rip *always* has a visible cover; it is folder-level, not embedded. Closing it means registering the standalone **`wavpack`** encoder through the dependency subsystem (Critical rule #6 — no bespoke install code) and routing `.wv` through it instead of ffmpeg, which also needs hardware validation that the resulting `.wv` shows its art in real players. **Deferred, not lost** — this row exists because [`docs/archive/mp3-wav-support-2026-06.md`](docs/archive/mp3-wav-support-2026-06.md) was archived and an open item inside an archived doc is an item nobody will read again. WAV is *not* part of this: RIFF cannot hold art at all, and the UI warns rather than pretending.
  - **Triaged 2026-11-16 (owner):** unchanged: only MP3 embeds art (`adapters/transcode.py:85`).

---

## Out of scope (not in P0, P1, or P2)

Listed here for clarity so they don't sneak in:

- Writing a ripper from scratch. *(Maintaining our own engine is what the Platterpus fork of cyanrip is — see [docs/cyanrip-fork.md](docs/cyanrip-fork.md) and KDD-18. "Build our own from scratch" stays rejected.)*
- **AccurateRip submission.** Policy-restricted, not technically impossible. AccurateRip's operators accept submissions only from EAC and dBpoweramp; any Linux tool implementing the upload protocol would have its submissions rejected. **AccurateRip *verification* IS in scope and already works** — cyanrip queries AccurateRip during every rip, the parser captures the v1/v2 confidence values, and the rip-progress widget renders them.
- **CTDB submission.** Likely subject to the same trust-gate as AccurateRip submission.
- **Tracker (RED/OPS/Orpheus) log acceptance — out of scope by design, not a gap.** Researched 2026-07: the gazelle logcheckers score by ripper identity (allow-list: EAC, XLD, and the ripper Platterpus used before cyanrip at ≥ 0.7.3) before ever looking at audio quality, so an unrecognized ripper (cyanrip) scores 0 regardless of how clean the rip is — there is no honest partial score to chase. RED additionally requires a valid EAC checksum we refuse to forge. The alternative we invest in instead is the open-trust path (AccurateRip + CTDB + an honest unsigned log). See PLANNING.md **KDD-24** and `docs/eac-parity.md`. Only legitimate reopen routes: re-add the previous backend as an optional secondary one for its tracker-recognized log (reverses KDD-18, needs sign-off), or upstream advocacy to add cyanrip to a logchecker's allow-list — neither is being built.
- **HTOA (hidden track one audio) — explicit scope note.** Not pursued. HTOA discs are rare in practice and neither backend gives a clean, low-effort extraction path today (the previous backend's HTOA edge cases are moot since its removal, KDD-18). Revisit only on a concrete user request with a disc in hand.
- Network features (NAS, Plex, Jellyfin, cloud)
- Library/catalog database
- DVD/Blu-ray support
- Windows or macOS support

---

*Last updated for Platterpus v0.7.125.*
