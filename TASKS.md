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

**This file holds live work only.** On 2026-11-25 (R233) the R table's 142 closed rows, the 2026-11-16 and 2026-10-12 rankings and seven sections the audit left with no open row moved to the same archive, under *Moved 2026-11-25*. On 2026-11-16 every section with no open row moved,
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

## 2026-11-25 — the audit: EAC parity, every open task, other rippers; what's next

The owner, 2026-11-25: *"another EAC parity audit, and open tasks audit ... expand beyond just
EAC, look for other flagship, common, open sourced, and community liked/preferred CD rippers
... see what is feasible ... keep all as a record even if we decide not to do it ... move
forward things we have planned but not yet done so we can see what is next."*

**State.** 0.7.130 released 2026-11-25, the first to install `.35`; round 42 closed GO/GO the
same day and `FORK_PIN` is `1280aa4`. Round 43 is the fork's to open, on `.36` part 1.

**What the audit did.** Every open row here and in the fork's lists was read against both
trees; 8 R rows closed as done or stale (R5, R12, R24, R31, R93, R129, R177, R191), 31 older
rows closed as duplicates of the R157 to R170 rows that carry them or as stale (each says
which), and R201 to R243 added (R232 to R243 from the review of the file layout). EAC parity was re-read against round 42's logs, and 17 other
rippers were surveyed; every feature found, done, planned or skipped, is recorded with its
reason and sources in `docs/eac-parity.md` Part H. What we ask of the fork is in
`docs/cyanrip-fork.md` → *Asks from the 2026-11-25 audit*. The 2026-11-16 lists this order
replaced are in the archive (R233).

### Waiting on the owner

*Answered 2026-11-25 (PLANNING KDD-48): R217 yes, more derived formats; R215 no, one drive at
a time; R52 stays deferred.*

*R236 and R239, answered 2026-11-25: "do it" to both; both done.*

1. **Rig time, one short session**: the fork's HW-20 (a trace of the lone `cyanrip -I -N` read
   that hangs after `Opening drive...`), R53 (the automatic cache check), R96 (KWin dialog
   stacking); later, a drive AccurateRip does not list for R150 and R151, and a second
   machine and distro for 0.8.1's gate.

### Ours, next, in this order (parity first, then wins, then convenience)

1. **Evidence the next round depends on:** R200 (keep the run's named bundle), R197 (album
   folders and records in a `--run-script` bundle).
2. **Gates the fork's `.36` part 2:** R193 (the readers, each with a never-raises test).
3. **Record and log correctness:** R219 (`Gap handling` names the undecided track), R220 (the
   encoder the header names), R141 (the EAC cell's tooltip), R131 (a re-ripped track's block
   CRCs), R226 (the addendum's time), R227 (`Pregap sample peak:`).
4. **Trust:** R194 with R172 (one estimate from one source).
5. **A convention the code breaks:** R224 (44 px commit buttons).
6. **Parity, small:** R206 (CD-TEXT fallback), R211 (submit the disc ID), R208 (MCN ranks
   the picker), R207 (search by hand), R218 (M3U), R216 (several formats in one rip) with R217 (more derived formats, approved).
7. **Parity, larger:** R152 with R188's drive setup verbs; R150 (offset from a disc); R49's
   remainder (an *unreadable on this drive* verdict); R44 (error positions in the log, a
   proposal in round 43's first lap); R201 (image plus single-file cue); R43's CTDB
   submission (parity: EAC's plugin submits; it was listed as a win before, and Part H
   settles the label).
8. **Housekeeping:** R199 (the outbound check on held laps), R231 (carry #512 and #529),
   round 43's lap items (R86, R166, R27's clause, R228, R229, the beta-expiry owner).
9. **Wins:** R134 (rebuild a disputed second), R204 (check and fix an
   old rip), R202 (say HDCD), R203 (a de-emphasised playback copy), R205 (hear the unsure
   positions).
10. **File organization (the 2026-11-25 review):** R243 next; R233, R234, R235, R237, R238,
    R240, R241, R232 planned, smallest first; R236 and R239 done on the owner's word; R242 only if
    touched anyway. Safe fixes already made: the index's stale facts, the KDD-47 banners, a
    duplicated list here, `build/.gitkeep` removed, `tests/data/` folded into `tests/fixtures/`,
    the layer table in `docs/architecture.md` §2.
11. **Planned, later:** R209, R210, R212, R213, R214, R221, R222, R223, R225; and the
    rest of the R table as each row orders itself.

## Every open numbered row (the R table)

Every open row, in number order; the order of work is the 2026-11-25 section above. On 2026-11-25 (R233) the 142 closed rows and the 2026-11-16 and 2026-10-12 rankings moved unchanged to `docs/archive/tasks-closed-to-2026-11-16.md` → *Moved 2026-11-25*; a row number is never reused, and `tests/test_tasks_rows_are_unique.py` reads both files.

| # | What | Ours to | Their item |
|---|---|---|---|
| R6 | **Triaged 2026-11-16 (OWNER, HARDWARE): unchanged: only an EAC rip of a hidden-track disc settles it, and none is filed under `output_reference/`.** Their round 32 lap 3 S10: our lap 2 S10 said EAC's additive track-1 convention (lead-in plus a span before track 1) is derived from a real EAC log. Only the lead-in arm is: our one EAC log has no such span. The test docstring and the parser comment now say so (2026-10-12) | Answer S10 in our lap 4 (no such log; the additive arm is sector arithmetic). Ripping a hidden-track disc with EAC would settle it, and only the operator can do that | `eac-htoa-log` |
| R8 | Their round 32 lap 5: C29 (our lap 4 declared 7 after their 8), C46 (their lap 5's `HANDSHAKE-NEXT-LAP`), and S11/S12 (`--diagnostics`, `seam-commands.md`). **Answered 2026-10-13** in our round 32 lap 6: our gate checks C29 and our emitter declares at least the record (`d9fb808a`, merged at `9156e878`); S8 asks them to refuse the file, not the round, with round 33 on the same pin as the fallback; S10 gives C46's fix; S11 and S12 landed | **Done 2026-10-13:** their lap 7 (`cyanrip@afe5ca7a`) passes our `--check` and lap checker, completing HR-1.7 (6); their gate now refuses the file under C29 and C46 (`cyanrip@9fca98a`), so no round 33 is needed. Their S8 corrects our S10's remedy: it should have read `6 (yours):`, from the writer's side; our lap 8 says so under Corrections. Cut 0.7.104 | *(done)* |
| R9 | **Triaged 2026-11-16 (STALE-BUT-OPEN): the chase half is done: each chase read's record is kept (`chase_record_keep.py`, R147) and the five-rip run's bundle carried 47 chase records (evidence `ac0a5133`); the packing-order half (a bundle packed before CTDB and FLAC verification land) was not re-verified in this triage.** Found in the 2026-10-13 Full run: a securing pass's own `--diagnostics` record is never kept, because the pass runs in a temporary folder deleted afterwards (`rip_worker.py`, above `record_path_from_argv`), and the session bundle's MANIFEST does not name the absence. Two of the run's 11 invocations (`-l 3,5`, `-l 3`) left no record. W6 recorded the gap as "not done" in a closed row; this is the open one | **[x] Done 2026-10-14, both halves**: the worker copies the securing pass's record into the rips root as `<name>-securingpass.json` before its temp folder is deleted, on every way the pass ends, and names it for the rip's bundle (`record_fate.keep_securing_record`); when it cannot, the reason (no record named, not written, the rip cancelled, the copy failed) goes into the report as `outcome.securing_pass_record` (schema v34) with a `securing_pass_record_missing` info issue, and the session MANIFEST's `ripper -j records missing` line names every pass whose record is missing, with that reason, cross-checked against the scan. Read over the filed round-32 reports it says the two securing passes are not determined (schema v33). Not covered: an earlier album pass of a speed-ladder retry (only the last is in a report), and a cancelled pass's record that cyanrip writes after the folder is cleared, which is named missing rather than kept. Was: either keep the securing pass's record beside the album pass's in the rips root, or name each missing record in the bundle's MANIFEST with the reason. Ours; nothing of the fork's. **2026-10-26, [~] bundle packing, in progress on the session branch on 2026-10-26, not committed at `bd194381`:** the same gap on the verified-read chase. Each of its cyanrip invocations passes `--diagnostics`, and none of their records reaches the session bundle, while its MANIFEST says `missing none` (disc 3, 2026-10-22, ten chase reads; the positions of their skips are lost). And a bundle can be packed before the post-rip checks land: disc 1's report (2026-10-21) was written a second after CTDB and FLAC verification were launched, both gates `ran` and `without_result`. From the EAC parity plan of record's Appendices H and I (`docs/eac-parity.md` Part F) | *(round 33)* |
| R10 | Their round 32 lap 9 S4 (round 32 closed GO on it, 2026-10-14): in the 2026-10-13 run's secure re-read, cyanrip's sub-channel search read track 4's 158-frame pregap as none (`Gaps:` omits track 4, its block reads `Pregap length: 0 frames`, the cue has no `INDEX 00` for it), where the whole-disc rip lists it. Verified in our filing (`round32fullsecurereread.log:42-50`, `.cue`, against `round32fullwholedisc.log:44`). **The defect is theirs and old** (first on 2026-09-05, `978f9b0`); **the miss is ours**: our lap 8 read the run and did not name it, and nothing in our grader compares the `Gaps:` lists of two rips of one disc in one run | **[x] Done 2026-10-14**: `expect-pregaps-agree`, run by the acceptance script's new section P4 (`uiscript/pregap_grading.py`, `pregap_verbs.py`). It compares the `Gaps:` lists of every cyanrip log the run wrote (album logs, P3's, each securing pass's own) disc by disc, keyed on the Disc ID, and names each track that differs with which logs said what. On the filed round-32 logs it names exactly tracks 4 and 9 (`tests/test_uiscript_pregap_verbs.py`). `info` either way and `blocked` below the floor of two comparable logs of one disc; the severity argument is P4's row in `docs/testing.md` → *Acceptance severity*. Was: round 33: a grader check that the pregap lists of rips of the same disc in one session agree, naming each track that differs (track 9's 94 vs 95 frames is the same run's second instance, their `subchannel-pregap-varies`). Nothing to fix in cyanrip from our side. **Added 2026-10-20 (P5 of the claude-code-skills check of the EAC audit, for the fork too):** across all 26 shipped rips of the reference disc, track 9's pre-gap reads 95 frames (`0:00:01.26`) in three (`round30oct05fullsecurereread`, `round32fullwholedisc`, `round33fullwholedisc`, the last at evidence commit `f57cdc2b`) and 94 (`0:00:01.25`, EAC's in all three of its sessions) in the other 23; the cue's track-9 `INDEX 00` then sits one frame early (`03:44:10` in `round32fullwholedisc.cue:69` against EAC's `03:44:11`). `docs/eac-parity.md` Part E §E4 now grades pre-gaps on 23 of 26. Whether the Q sub-channel read varies or a rounding step does is the fork's question; ours is to keep P4 naming it | `subchannel-pregap-varies` |
| R27 | **Audit 2026-11-25: tags are in through `.35`; left is the ISO 3901 clause, with the next shared-document version.** **Triaged 2026-11-16 (STALE-BUT-OPEN): the tags are in (`deps/fork_source.py:1935-1943`, through `edb73dd`); the ISO 3901 clause is still not in the shared row (`docs/seam-commands.md:112`), which moves only in a lap.** **When `.25` is cut:** add its tag to the build-tag sets (`BUILD_TAGS_ACCEPTING_PREFER_DISC_ISRC` and the rest), regenerate the ripper inventory from `.25`'s provider contract (`scripts/emit_ripper_inventory.py`), and add the ISO 3901 clause to the seam row's meaning cell | In the round that puts `.25` under review | ours, on `.25` |
| R29 | **Triaged 2026-11-16 (OWNER): unchanged: the operator watches upstream issue 167.** **Upstream issue 167 (https://github.com/cyanreg/cyanrip/issues/167) has no maintainer reply as of 2026-10-19.** Corrected by the operator's review of 2026-10-19 (item 2), read from the public page at 18:40 UTC: no comments, labels or assignees, and the one entry after the body is GitHub's automatic note that a fork commit referenced it. This row said the issue "has a maintainer reply we cannot read from here", which was not so. Also from that review: a commit message or pull request that writes the owner/repo#number form posts a notice on upstream's issue, so ours name it as "upstream issue 167" with the URL | The operator checks the page from time to time and posts reports 24 and 25 there; we answer any reply in the next lap if it bears on our use of the flags | operator |
| R32 | **[~] Trimmed 2026-11-16 on the owner's word ("7. a"), in its own pull request for the owner to review: `CLAUDE.md` 676 lines / 99,225 bytes → 311 lines / 42,126 bytes (`wc -lc`), every removed sentence moved word for word to an existing home (CHANGELOG names each), and `tests/test_claude_md_size.py` holds the new size as a ratchet. The line standard is met; the 32 KiB byte standard is not, because what remains is the rules' operative sentences, and the next cut would drop one. `TASKS.md` and `CHANGELOG.md` are untouched by this change.** *Was:* **Triaged 2026-11-16 (OWNER): larger since: `CLAUDE.md` is 678 lines and 98,907 bytes, `TASKS.md` 9,272 lines, `CHANGELOG.md` 20,050 lines (`wc`, 2026-11-16); the move waits on the owner's confirmation for the locked sections.** **`CLAUDE.md`, `TASKS.md` and `CHANGELOG.md` are far past a workable size** (the operator's review of 2026-10-19, item 3): 404 lines and 86,027 bytes, 9,015 lines and 895,531 bytes, and 19,105 lines and 1,373,241 bytes, against a standard of 300 lines and 32 KiB for `CLAUDE.md`. Stale rules there have already cost round trips (the release hold, R23) | After round 35 closes, as a change of its own: keep in `CLAUDE.md` only what a session needs on every task, each rule with what fails without it; MOVE the rest (history to `PLANNING.md` or `docs/archive/`, procedures to the documents they describe, finished rows to a dated archive, old CHANGELOG sections to an archive file), never summarise it away (rule #7), and add a test that holds `CLAUDE.md` under the cap. Rule #7 itself and the CLAUDE.md lock need the maintainer's confirmation | ours, maintainer confirms |
| R43 | **Triaged 2026-11-16 (STALE-BUT-OPEN): repair is built and proven on hardware: the 2026-11-10 Full run met the pre-registered values, `C96464AB` and `5092E94B` (our round 38 lap 17 S3). Left: CTDB submission (`docs/eac-parity.md` Part F row 13) and the by-hand track-3 localisation on EAC's wav session.** **[~] CTDB per track and over every offset, built 2026-10-21; localisation built 2026-10-26; repair built 2026-11-04, and run automatically after a rip from 2026-11-05 (R133, no button); submission not built.** *Per track:* each track is compared with every entry's `trackcrcs` the way CUETools' `GenerateLog` does, at that entry's offset (read from where most of its tracks agree with ours, `ctdb/matching.py:136`) or within ±2939 (`:165`); tri-state per track with the summed confidence, in the verdict message, the results pane, `--ctdb-calibrate` and the report's `ctdb.tracks`. *Offset sweep:* the whole-disc CRC is compared at every alignment in ±5879 in the same streamed pass (`ctdb/sweep.py`, `ctdb/verify.py`); a match names `matched_offset`, a no-match says our audio differs from every entry over `offset_range`. Held against the real CTDB answer for the reference disc (`tests/fixtures/ctdb_lookup_police_classics.xml`) and EAC's three logs (`tests/test_ctdb_per_track.py`), by `tests/test_ctdb_sweep.py` and by `tests/test_ctdb_offset_sweep.py`. *Localisation* ("track 3 differs in 16 samples @04:04:68,04:05:17,04:11:32 from the 1,416-submission entry"), **built 2026-10-26 on the owner's word on numpy** (*"numpy; record what it adds to the download"*, 02:19 UTC; DEPENDENCIES.md has the measured cost): CUETools' `CDRepairEncode.VerifyParity`, clean-room (KDD-16). The entry's parity record is fetched from its `hasparity` URL (`adapters/ctdb_parity.py`; its layout, rows of 11,760 little-endian syndrome words, checked against the real record for entry 32115, whose row heads equal the lookup's `syndrome` attribute); our syndromes over GF(2^16) (`ctdb/gf16.py`) come from one streamed numpy pass (`ctdb/syndromes.py`, 0.64 ms a row, about 17 s for the reference disc's 26,866 rows on the 2026-10-26 session box) and shift to any alignment in ±5879 without another pass; a clean-room Berlekamp-Massey, Chien and Forney decoder (`ctdb/rs_decode.py`) names each differing column's rows; and the corrections must reproduce the entry's CRC (`ctdb/verify_parity.py`) or nothing is located. It runs against at most the three strongest entries with parity that our disc does not match and that outweigh the one it does (`ctdb/localise.py`), in a second, lazy decode pass on the CTDB worker, bounded to 300 s; every failure reads "not determined" with the reason (numpy not installed, record unavailable or mismatched, time bound, too many differences). It reaches the verdict message, the results pane, `--ctdb-calibrate` (a `Localisation:` line and EAC's `(1,416/1,441) differs in ...` per track) and the report (schema 40: `ctdb.localisation`, `ctdb.tracks[].differences`). Held by `tests/test_ctdb_syndromes.py` (an independent reference encoder, every alignment, and CUETools' systematic-parity form converting to our definition), `tests/test_ctdb_rs_decode.py` (injected errors decode exactly; a never-raises property whose every answer reproduces its syndromes), `tests/test_ctdb_localise.py` (synthetic discs at offsets 0, +667 and -1500 locate exactly the injected samples; our wording equals EAC's committed track-3 and track-5 lines; random parity never raises) and `tests/test_ctdb_parity.py`. **Run on hardware 2026-10-28, on EAC's FLAC session:** the owner's `--ctdb-calibrate` on EAC's FLACs of the reference disc (0.7.114, `95691b5`) located track 5's difference exactly as EAC's own log does: ours *"track 5 differs in 3 samples @02:24:59 from the 1,419-submission entry"*, entry 32115 located at offset -7, against EAC's *"(1339/1441) Differs in 3 samples @02:24:59"* (`output_reference/EAC_flac/eac_baseline_police_classics.log:264`); the other 13 tracks agree with 1,485 to 1,512 of 1,521 submissions at offset -7, and the whole disc matched one minority entry at +0, reported as not corroborating. **Still hardware-gated, and not claimed:** that EAC's own wav session of the reference disc (`output_reference/EAC_wav/`) locates track 3's 16 samples at `04:04:68,04:05:17,04:11:32` here; that needs the owner's audio. *Repair*, **built 2026-11-04 on the owner's word** (*"Start building CTDB repair now? yes"*; KDD-14 amended): CUETools' `CDRepairFix.Write` natively, the step after the localisation, with `neheb/cdverify`'s `src/repair.rs` as the safety reference. The localisation now keeps each correction's XOR value (`EntryLocalisation.values`) and each track's whole-PCM CRC-32 (`CtdbLocalisation.track_crc32s`). `ctdb/repair_plan.py` maps every corrected word to (track, frame, channel) toward the single strongest entry, and refuses, each with its sentence: a minority or tied entry, a rip already matching the strongest, a track AccurateRip verified, a word in a guard band or outside the audio, a pregap or a track not whole sectors, more corrections in one column than npar 8 (4) or 16 (8) carries. `ctdb/repair.py` then requires each affected file to be the audio localised (length and CRC-32), XORs the words, encodes a hidden new file with `flac -8` and copies every metadata block with `metaflac --list --data-format=binary` / `--append` (`adapters/flac_rewrite.py`, refused unless the new file's blocks equal the original's), decodes it back and requires the corrected PCM byte for byte, and measures the whole repaired disc: the entry's whole-disc CRC and the repaired track's CRC at the entry's offset, or nothing is replaced. AccurateRip v1/v2 of each repaired track are recomputed before and after (`accuraterip_crc.py`, ours, checked against Leo Bogert's C `accuraterip-checksum`; there was no AccurateRip CRC code of ours before). `ctdb/repair_commit.py` keeps the original as `<name>.flac.before-ctdb-repair` (hard link, or a compared copy on FAT/exFAT), refuses to overwrite an earlier one, renames the new file in, and undoes everything on a failure part-way. The logs are never edited (KDD-24). `ctdb/repair_run.py` is the thin caller from a `CtdbVerifyResult`; the record is the report's `ctdb.repair` (schema 44). Held by `tests/test_ctdb_repair.py` (synthetic discs at 0, +667 and -1500 restored byte for byte, an npar-8 entry, every refusal with the album unchanged, the commit's link-less and part-way paths, the real `flac`/`metaflac` chain where installed), `tests/test_ctdb_repair_plan.py`, `tests/test_accuraterip_crc.py` and `tests/test_flac_rewrite.py`. **Pre-registered prediction for the owner's disc** (EAC's FLAC session, entry 32115 at offset -7, `tests/fixtures/ctdb_lookup_police_classics.xml`): after repair the whole-disc CTDB CRC at -7 is `5092E94B` and track 5's at -7 is `1CB564CC` (the entry's own, which the proof requires); track 5's Copy CRC becomes `C96464AB`, AccurateRip v1 `134C0B9D` and v2 `BCF4E815`, the values of the one secure re-read AccurateRip verified (`tests/fixtures/evidence/docs/handshake/artifactsround31/round31fullsecurereread.log:437-441`; v2 is also what EAC's log says AccurateRip returned, `output_reference/EAC_wav/eac_wav_police_classics.log:115`), and the value 48 offset-0 CTDB entries hold for track 5. Not algebraic: the three XOR values are not in any committed artifact. *Submission* is out of scope. Found by the 2026-10-19 EAC audit (Part E §E5). Weighing a match against the entries that disagree is R34, done | *Repair, next:* **done 2026-11-05 as R133** (no button, on the owner's word: the repair runs on its own after a rip, on a worker with a real `cancel()` through `killable.KillableJob`, fed AccurateRip's per-track answer from the rip log, recorded with a fresh verify beside the read's verdict, and the derived copies made again from the repaired FLAC); no `ctdb-repair` script verb, since the scripted rips reach it through the app's own pipeline. Left: the owner's hardware proof on a copy of EAC's FLAC session against the prediction in this row. The owner's run: `--ctdb-calibrate` on a FLAC copy of EAC's wav session (`flac *.wav` in that folder), whose `Track | CTDB per-track result` table must read `differs in 16 samples @04:04:68,04:05:17,04:11:32` for track 3 against the dominant entry; the first AppImage built with numpy gives its real size; then submission. *2026-10-26:* `docs/eac-parity.md` Part F row 11 (Behind on naming samples: the syndrome pass, on the owner's word) and row 13 (CTDB submission, Behind: build it, and never submit a rip with a track AccurateRip rejects, as EAC's plugin did with track 5, `output_reference/EAC_flac/eac_baseline_police_classics.log:258`). Per track and the offset sweep ran on hardware in the four Full runs of 2026-10-21 and 22 (the plan of record's Appendices G and I); a match at a nonzero offset has not occurred yet | ours; the run is the owner's |
| R44 | **Triaged 2026-11-16 (OPEN-OURS, parity): unchanged: Part F row 10 still reads Behind (`docs/eac-parity.md`), and the three damaged-disc defects were not found fixed.** **Error positions, once a released fork build prints them.** EAC logs where a track was doubtful; the build users get (`.23`) prints only counts. The fork's tip records positions (`cyanrip@820c0c5:src/cyanrip_main.c:643-645`), accepted in our round 35 lap 8. Found again by the 2026-10-19 EAC audit (Part E §E4). **Parse and report done 2026-10-21** for `.25` (`cyanrip-diagnostics/10`): `error_positions.py` reads `error_positions`, `error_positions_dropped` and `paranoia_all_reads` per track through the one `track_state` reader, tri-state and bounded, with a never-raises property test, into the report's `disc.error_positions` and the `error_positions_reported` warning | ~~Parse them with a never-raises property test, put them in the report~~ (done); agree their EAC-layout wording through the handshake (the fork diffs that log). *2026-10-26:* `docs/eac-parity.md` Part F row 10 (Behind; both sides). On the damaged disc (2026-10-21) the report carried positions, with three defects (the plan of record's Appendix H §4): track 18's `skips` states the list's 1,000, not paranoia's 2,076; positions repeat (track 17's 28 entries cover 16 sectors); and the securing pass's positions never reach the report (track 12's skip at LSN 151669) | ours, on the build that carries them |
| R49 | **Triaged 2026-11-16 (STALE-BUT-OPEN): the time budget is built, in the chase (`chase_budget.py`; `chase_record.STOPPED_TIME_BUDGET`) and on the securing pass (`securing_time_limit.py`, `--reread-time-limit`); left: the "unreadable on this drive" verdict and a stop-this-track control, neither found in `src/`.** **[ ] A per-track time budget for re-reading, and "unreadable on this drive" (`docs/eac-parity.md` Part F row 5, Behind).** On *Roots Music* disc 1, 2026-10-21, the album pass read track 18 in 8,548 s with 2,076 paranoia skips (`round36full1021bwholedisc.log:1441`, evidence `08de9851`), the securing pass's `-Z 2 -r 5` began reading it again, and the Full run's 6-hour wait stopped the rip in its second re-read; the plan of record projects 20 to 24 hours to the end. Every bound is a count (`-r`, the chase's 5), none a time. The plan's proposal (Appendix H §5): run the securing pass one track at a time, or swap what a stopped pass finished (R7); give each track a re-read budget, for example the larger of 5 × its length and 2 × its album-pass read time, keeping the best read with `stopped_reason: "time_budget"`, in the chase loop too; skip the chase for a track whose every read carries skips; offer "stop re-reading this track"; and report "Not verified: unreadable on this drive" with each read's time and CRC and the skip count from the counter. Its drive-free tests are listed there. Section F of the Full run waits 6 hours, sized for a clean disc | Build the budget and the unreadable verdict, with the drive-free tests. **The owner, 2026-11-03: pass `.28`'s `--reread-time-limit` after 0.7.118, with a default they choose (R125)** | ours; what `-r 5` means beside EAC's 82 reads is the fork's |
| R52 | **Kept deferred 2026-11-25 on the owner's word ("keep it deferred", PLANNING KDD-48).** **Deferred 2026-11-16 on the owner's word ("11. not right now").** **Triaged 2026-11-16 (OPEN-OURS): unchanged: KDD-12's 2026-10-26 correction still names no primary source (`PLANNING.md:1225`).** **[ ] Does AccurateRip accept submissions from a program it has not listed? (`docs/eac-parity.md` Part F row 14, Behind, may be not possible).** "Impossible from Linux" had no source (PLANNING.md KDD-12's dated correction, 2026-10-26). AccurateRip's list of compatible programs names five, none for Linux, and does not say whether it refuses others | Find a primary source and record the answer in KDD-12 and Part E §E5; writing to AccurateRip is the owner's call. If it refuses, close as not ours to change | ours |
| R53 | **Triaged 2026-11-16 (HARDWARE): unchanged: no filed run shows the probe starting on open and dying on *Skip check*.** **[~] Measure cache defeat once per drive in setup (`docs/eac-parity.md` Part F row 17, Behind on the default). Built 2026-11-12; a hardware run is left.** `cd-paranoia -A` ran only when the user pressed *Analyze cache* (KDD-29), so a drive never analysed logged no verdict, where EAC logs the setting on every rip. Now Set up drive starts the same worker by itself when it opens for a drive with no saved verdict and an audio CD in (`cache_check_plan.decide_auto_check`), with *Skip check* killing the probe; with no disc it says it will start when one is read, and does; a firmware change since the measurement makes it due again (`cache_defeat_release`, beside the verdict in the drive profile); a rip on a drive with no verdict goes ahead with a dismissible status-bar note, and never starts the probe. Held by `tests/test_cache_check_auto.py`. *Left:* the rig confirming `cd-paranoia -A` starts on open and dies on *Skip check* and on Close (the acceptance scripts' `open drive` then `cancel` exercises the second on a drive with no verdict) | Hardware confirmation on the rig | ours |
| R55 | **Triaged 2026-11-16 (HARDWARE, OWNER): unchanged: no timed EAC rip is filed.** **[ ] Time one EAC rip against one Platterpus rip of the same disc (`docs/eac-parity.md` Part F row 34, no data against EAC).** EAC's three sessions ran at 1.6× to 9.1× with Test & Copy; `.26` is 2.8× to 5.1× faster than `.25` (R46). EAC set up as Part F §F4 says | EAC rips of the damaged disc and disc 3, timed | the owner's, at the drive |
| R73 | **Triaged 2026-11-16 (STALE-BUT-OPEN): the `.25`/`.26` comparison is history; left: `artifact_grading._track_ar_state` still calls `verdict.accuraterip_state` itself (`uiscript/artifact_grading.py:255-263`) rather than delegating to `verdict.track_accuraterip_state`.** **[~] Paired rips of track 3, scripted (2026-10-26; the owner's word *"add paired .25/.26 rips of track 3 to the Full run"*, after the fork's round 36 lap 8 S8).** Section P6 of the Full run rips track 3 alone eight times in ABBA order (approved, review, review, approved, twice), with P5's fixed settings and five `install-ripper` switches, records each rip's per-track AccurateRip state, CRC32, speed and build (`record-accuracy`), and tallies per build "right in N of M rips" with every distinct CRC32 read (`compare-accuracy`); all `info`, and a comparison that cannot be made is refused as not determined. "Verified" is `verdict.track_accuraterip_state`, new beside `accuraterip_state`; `uiscript/artifact_grading._track_ar_state` ranks the same states and a property test holds the two equal. Held by `tests/test_uiscript_accuracy_verbs.py` | The first Full run with `.26` still under review: P6's tally, and its real duration recorded in its header (estimated about 30 minutes from P5's measured rips). Then make `artifact_grading._track_ar_state` delegate to `verdict.track_accuraterip_state` (it was being edited on another branch when P6 landed) | ours; the run is the maintainer's, on hardware |
| R86 | **Audit 2026-11-25: the fork's KNOWN-ISSUES says `.28`'s escape is held by `tests/logescape.c` and `log_values_cannot_forge_a_line`, and only paranoia's identify message is left (their US-1); the ask shrinks to citing those tests beside our counterpart test, in round 43's first lap.** **Triaged 2026-11-16 (OPEN-OURS): the escape ask has not been sent: no outbound lap of rounds 37 to 40 carries it, and `tests/test_echoed_field_forgery.py:489` still pins the residual.** **[~] Ours done 2026-11-03 (`2ee03e6a`); the residual is the fork's. The disc-header rows are closed in our parser** (`parsers/cyanrip_echo_guard.py`): the eight rows cyanrip prints above the disc `CD-TEXT:` row (`Invoked as:`, `Drive used:`, `Offset:`, `Overread mode:`, `Speed:`, `C2 errors:`, `Accurate stream:`, `Recordable:`) are not read once that row or a track block is reached, so cyanrip's value stays; the five printed between that block and `Album:` (`Paranoia level:`, `Outputs:`, `Tracks to rip:`, `DiscID:`, `CDDB ID:`) are read once, and a second copy makes the row not determined, never the forger's value; forged copies are counted and logged. Both rest on a print order every committed log agrees on (130 header logs, each guarded row in at least 3), read by `tests/test_echoed_field_forgery.py::test_the_disc_header_order_the_guards_rest_on_holds_in_every_committed_log`; the three routes (the `Album:` line, the disc CD-TEXT block, a track echo) and a non-triviality floor per row are tested there, revert-probed. **Still open, the fork's to close, and pinned by `test_RESIDUAL_a_forged_block_opener_still_changes_the_parse`:** a forged block opener (`Track N read successfully!`) or `Done;` line; a `once` row on a build that prints none of its own; and a forgery can make a `once` row not determined (a refusal, not a forgery). **Proposed item for the fork (theirs, NEXT-ROUND):** their `.28` carries *"every value the log writes escaped"* (`cyanrip@46cec2a:src/cyanrip_log.c`, their round 37 lap 1 S3, accepted in our round 36 lap 13 S3). Ask them to state, with file and line, that the escape covers a line break (and every character `str.splitlines` breaks at, `\x85` and U+2028 included) in each echo: the per-track `Metadata:` and `CD-TEXT:` blocks, the disc `CD-TEXT:` block, the `Album:` line, the `.cue` and the `Invoked as:` line; and to publish a `.28` reference log ripped from an image whose CD-TEXT title holds a line break, so our test can assert the escaped form reads as one row. Then the residual test stays for logs from builds before `.28` (they are already filed) and gains its `.28` counterpart. *Was:* **An echoed value can forge a line in cyanrip's log (peer review 2.4, the claude-code-skills session, 2026-10-26).** cyanrip prints metadata and CD-TEXT values with a bare `"%s\n"` (`cyanrip@eca33dc:src/cyanrip_log.c:58-62`, `:770-776`, `:785-788`), so a value holding a line break puts text at column 0 of a line of its own. **Our values cannot:** the argv chokepoint refuses a control character in the four path-bearing fields and replaces it in the seven tag-only ones (D14), held end to end (argv, echo, parse, verdict) by `tests/test_echoed_field_forgery.py`. **The disc's own CD-TEXT can**, whatever we send (`cyanrip@eca33dc:src/cdtext.c:110-131` fills empty tags from it and the log echoes it verbatim). Closed in the parser for every per-track verdict row (`EAC CRC32`, `Secure re-read`, `Accurip:` and its `v1`/`v2`/`450` rows): each prints before the block's `Metadata:` header in every build, so one after it is counted and not read (`_TRACK_ECHO_HEADER`). **Still open, and pinned by `test_RESIDUAL_a_forged_block_opener_still_changes_the_parse`:** a forged block opener (`Track N read successfully!`), a `Done;` line, and a disc-level header row (`Offset:`, `Drive used:`, `Paranoia level:`, measured) through the `Album:` line or the disc `CD-TEXT:` block. Our parser cannot tell those from cyanrip's own | Send the shape to the fork as a NEXT-ROUND item in our next lap, with these citations: escape (or refuse) a control character in every value they echo into the log, the `.cue` and the `Invoked as:` line, as we do at our argv chokepoint; then retire the residual test against a build that does | ours to send; theirs to fix |
| R88 | **Audit 2026-11-25: the pin is now `.35` (`1280aa4`), not `.32`.** **Not retired, 2026-11-16: retiring the refusal would move the failure from before Start to after the rip, into files of ours.** `.32` cuts an over-long name to exactly 255 bytes (`cyanrip@edb73dd:src/naming.c:741-765`, `CRIP_NAME_MAX`; logged at `src/cyanrip_main.c:2773`), and we write siblings named from cyanrip's names with longer endings: `<flac>.platterpus-refix.tmp` (`workers/rip_worker.py:3845`), `<stem>.<ext>.transcode.tmp` (`adapters/transcode.py:266`), `<log stem> (EAC-compatible).log` (`ui/main_window_rip.py:3594`), `<log stem>.platterpus.json` (`rip_report.py:3867`) and `.platterpus-addendum.txt` (`rip_addendum.py:178`). Measured on this container's filesystem beside a 255-byte `.flac`: all five fail with `ENAMETOOLONG` (266 to 276 bytes). The overwrite guard also predicts the album folder unshortened (`cyanrip_backend.predicted_album_folder`), so a shortened folder would not be found and a re-rip would write into it without the prompt. **Before the refusal can go:** bound our own sibling and temp names (or budget the refusal for the longest of them), and teach the folder prediction the cut, or keep refusing the folder. **The gap the same arithmetic left is closed (2026-11-16, the commit that adds `src/platterpus/sibling_names.py`):** the refusal now holds each name to 255 less the longest ending we add to it (234 for a track's FLAC, 230 for the rip log), derived from the endings in `sibling_names.py`, through which every writer now builds its names (`tests/test_sibling_names.py`, real files at the limit and one byte over). Retiring the refusal stays open, for the overwrite-guard reason above. *Was:* **Triaged 2026-11-16 (STALE-BUT-OPEN): the gate is met: `FORK_PIN` is `.32` (`deps/fork_source.py:327`), which descends from `.28`'s shortening (`cyanrip@edb73dd:src/cyanrip_main.c:2773`, `Names shortened:`), so retiring the before-Start refusal is now ours (keeping the case a title cannot shorten); `adapters/cyanrip_name_lengths.py` still refuses on every build.** **[~] Ours done, checked 2026-11-03; what is left waits on a round, not on code.** The ask went (our round 36 lap 13 S4); the fork proposed `Names shortened:` (their round 37 lap 1 S7), we accepted it and our reader is built (our round 37 lap 2 S5, `d06aed37`, `parsers/cyanrip_disc_blocks.py`, shipped in 0.7.116); the fork built the shortening in `.28` (their round 37 lap 3 S6, `cyanrip@ed50558`), which 0.7.117 names as the build under review. **Left, and gated:** retire the before-Start refusal once a build that shortens is the DEFAULT (`FORK_PIN` moves only when a round closes, so this follows the round that approves `.28` or later, and is not ours to start). When it is retired, keep refusing the case their S6 says still fails: a component the track number, extension and the scheme's own text alone keep over 255 bytes, which `.28` leaves whole and cannot open. Nothing is proposed to the fork; no fork change is outstanding. *Was:* **Filenames built from titles (peer review 2.7, 2026-10-26).** **Fixed:** the album year could leave the library: `%y` is cyanrip's `{date}`, rendered from the Year box verbatim, and the year was checked by neither the argv chokepoint nor the track table, so a year of `..` with a template `%y/%A/…` wrote one folder above the output directory. Now refused at both (`settings_validation.path_reference_issue`; `tests/test_title_filenames.py`). **Held, with tests:** `/`, `../`, `\`, absolute paths and look-alike characters land as one segment (cyanrip's table, `cyanrip@eca33dc:src/naming.c:132-218`, mirrored by our preview); `.`/`..`/control characters are refused in the four path-bearing fields; the unknown-album path is ours and capped at 255 bytes. **Left, by decision not oversight:** a leading dot is a hidden folder inside the library; Windows-reserved names are legal on Linux and only a template's literal text is warned about; **Interim built (the owner's choice, 2026-10-26): a name over 255 UTF-8 bytes is refused before Start.** An identified-disc title of 90 CJK characters passed every check and failed at file creation in cyanrip, which does not shorten it, after the track had been read. `adapters/cyanrip_name_lengths.py` now renders each album-folder level, the `<album>.log`/`.cue` and every ticked track's file (`.flac` and any derived extension) from the `-D`/`-F` schemes and tags the argv sends, through `naming.render_scheme`, counts bytes as cyanrip writes them (`naming.name_bytes_on_disk`), and refuses in the track table (*"Track 7’s file name would be 280 bytes; the limit is 255 — shorten its title."*, the rest counted and logged) and at the argv chokepoint. The pin flipped: `test_an_overlong_identified_title_IS_refused_before_start`, with the 255/256 boundary, 3-byte characters, the folder and log, the unknown disc's capped folder, and `hypothesis` never-raises and agrees-with-the-renderer properties (`tests/test_title_filenames.py`). It shortens the TAG with the name | **The owner chose this on 2026-10-26:** *"Long term, option 3: ask the fork to shorten an over-long file or folder name to 255 bytes at a character boundary, keeping the track number and extension, and to print the shortened name in its log. That fits the escaping work they're already doing for .28."* Ask the fork in our next lap (held until the owner releases it); our reader takes the shortened-name log line before any build prints it; retire the refusal once a build that shortens is the default | ours (the interim); the fork (the shortening) |
| R91 | **Triaged 2026-11-16 (OPEN-OURS): unchanged: python-appimage's base image, appimagetool's runtime and `scripts/bommap` reading the locks are still open.** **[~] Hash every install that is still a range (the follow-up review of 2026-10-27, after items 1, 4 and 6; item 5).** The jobs that publish, attest and gate install from `build/locks/` with `--require-hashes` (`708aba97`, `fe6e7e56`). **Covered since item 5:** the required `sbom` job (`build/locks/sbom.lock`: the runtime dependencies, pyproject's new `sbom` extra and the backend, then the project offline; its `pip install --upgrade pip` is gone), the `shellcheck` job and zizmor and ShellCheck in `workflow-lint` (`build/locks/ci-lint.lock`), and `mutation.yml` (`build/locks/ci.lock`). `commit-subjects` installs nothing: `scripts/check_commit_subjects.py` is standard library only. **Still ranges:** actionlint-py in `workflow-lint` (`>=1.7.12,<1.8`): it publishes only an sdist, whose build downloads the actionlint binary from GitHub and checks it against checksums the sdist carries, so a wheel-only lock cannot hold it; the way through is either a lock that admits that one sdist and installs it with `--no-build-isolation` beside its build dependencies (setuptools, wheel, requests, semver), or the actionlint release binary fetched with a pinned sha256, as the `gitleaks` job fetches its CLI. cyclonedx-bom's own range is `>=7,<8`, a major range: pinning it to the minor (amendment A5) would also add it to `.github/dependabot.yml`'s ignore list (it is a CI tool) and to the weekly group's `exclude-patterns`; `tests/test_dependabot_holds_the_pins.py` derives both from `pyproject.toml`, so it would say so. (The `pinned-minor` group this sentence once named was removed on 2026-10-27.) python-appimage's own downloads of the base image and appimagetool are not pip installs and are not locked. And `scripts/bommap` does not read the locks, so `bom.cdx.json` lists ranges where the jobs install exact versions. **2026-11-03, two of these closed.** (1) actionlint: `workflow-lint` now fetches `actionlint_1.7.12_linux_amd64.tar.gz` from rhysd/actionlint's release, checks sha256 `8aca8db9…` (the release's own checksums file and actionlint-py 1.7.12.25's `_custom_build/checksums.cfg` agree; the extracted binary is byte-identical to the one actionlint-py installed), checks `-version`, and runs that file; the job's only pip install is now the hashed lock, so it joins `HASHED_JOBS`, and `bom.cdx.json` maps the binary as `ci:actionlint`. pyproject's `actionlint-py` line stays for local installs, and `tests/test_dependency_locks.py::test_workflow_lint_fetches_actionlint_pinned_and_in_pyprojects_range` holds CI's version inside its range. (2) cyclonedx-bom is `>=7.5,<7.6`, the minor sbom.lock already resolves (no lock moved), in dependabot.yml's ignore list and weekly `exclude-patterns`, held by `tests/test_gating_tools_are_pinned.py::test_the_sbom_generator_is_pinned_to_a_minor`. **Still open:** python-appimage's base-image download (a rolling release asset per CPython minor, so a sha256 pin would break whenever upstream rebuilds it; the way through is fetching a named patch build by URL and sha256 and passing `PLATTERPUS_BASE_IMAGE`, proved by an `appimage.yml` build), appimagetool's own type-2 runtime download, and `scripts/bommap` reading the locks. |
| R96 | **Triaged 2026-11-16 (HARDWARE): every part is built and held (`tests/test_hold_for_user.py`, `tests/test_modal_stacking.py`); left: the owner's KWin desktop confirming the stacking. Qt's own file dialog is not covered.** **[~] Dialogs that hide behind other windows, or stay in front of the wrong ones (the owner, 2026-10-28; for the next round, not this one).** Two reports: (1) a dialog or yes/no question can end up behind a window that cannot be closed until the question is answered, which locks the app; (2) the disc-identity screen for the reference disc's album stayed in front of other option windows and of the update window. Sweep every `QDialog`, `QMessageBox` and `exec()` for its parent and modality: each question should be parented to the window it is about, raised above whatever blocks it, and never left behind a modal window it is waiting on; a dialog that is not a question should not stay above unrelated windows. Hold it with a test that opens each modal path over another modal window and checks the newest is on top and answerable. **(3), the owner, 2026-10-29, on 0.7.114:** the album picker (`ReleasePickerDialog`, opened at `main_window.py:1640` when a disc's lookup returns more than one release) popped up while they were in Tools → Setup & Updates…, asking them to choose or cancel there. A question the user did not start should wait until the main window is the one in use: no other dialog open, and the window active. The update offer already defers this way (`main_window_update.py:342`, Qt's `activeModalWidget()`); the album picker does not. Sweep every dialog that opens without a click and **sort each into one of two kinds, the owner's word of 2026-10-29: *"if they need to pop up, sure, but if they can hold, then hold them"***. *Can hold*: nothing is waiting on the answer and nothing is lost by a delay (the album picker for a disc just inserted, the first-run setup offer, the update offers, Picard's prompt, the drive and dependency notices); these wait for the main window, through one shared predicate rather than one check per dialog. *Must show now*: something is stopped on the answer or is lost without it (a rip that failed, a drive removed mid-rip, a question a running rip is blocked on, a confirmation before data is overwritten); these still open at once, raised above whatever is open so they are never hidden behind it. Record each dialog's kind beside it, and test both: a held dialog stays closed while Setup & Updates is open and appears when it closes, and an urgent one opens on top of it. For the next round or release, not this one. **Status, 2026-10-29 (on the owner's word, *"while we are waiting for the new fork release, yes, you have my permission to do those"*):** (3) is done for the album picker. The shared predicate is `ui/hold_for_user.py` (`busy_reason`: a modal dialog is open, or another window of ours is active and visible, the script console excepted; `hold_until_free` asks again every 500 ms and asks the caller whether the dialog is still wanted before each try). The picker moved into `ui/main_window_picker.py` and waits through it, one held picker per disc (`_mb_picker_held_for`); `tests/test_hold_for_user.py` drives the real Setup & Updates window, and each of its five guards was reverted with `scripts/revert_probe.py` and caught. Learned on the way: Qt can name a dialog that has just closed as the active window, so a hidden window counts as not in use. **2026-11-03:** the unknown-album offer (`_handle_no_mb_match`, the picker's sibling for no match) waits the same way, through `_hold_unknown_album_offer` in `ui/main_window_picker.py`, keyed on the disc scan (`_disc_retries.request`) because a disc with no MusicBrainz ID comes there too: one offer per scan, waiting or open (the key clears when the dialog closes, so a duplicate result during the modal does not ask again), and a newer scan drops it; five tests in `tests/test_hold_for_user.py`, four guards reverted with `scripts/revert_probe.py` and caught, the control unaffected. The first-run offers wait the same way (the settings-reset notice, the AppImage menu offer, the host setup offer and the drive setup offer, which run in sequence from `_maybe_offer_first_run_setup`, now through `hold_until_free` as one group, the unattended check asked again where they open); three tests in `tests/test_hold_for_user.py`, two guards revert-probed and caught, the control and the unattended test unaffected. The automatic ripper update offer waits too (`_hold_automatic_ripper_offer` in `ui/main_window_update.py`): only the automatic path holds, so `_interruption_blocker` did not gain the other-window test and a check the user starts from Setup & Updates is still answered at once; `_interruption_blocker` is split into `_no_one_to_ask` (drop: window hidden, acceptance session), `_rip_blocker` and `_modal_floor_blocker` (wait), and `hold_until_free` takes an `also_busy` for a caller's own wait reasons; a newer check or an install clears `_held_ripper_offer`; arming no longer skips the check for an open dialog. Six tests in `tests/test_hold_for_user.py`, seven guards revert-probed and caught. **The launch dependency report waits too (2026-11-03, `c753ad77`)**, the fifth *can hold* dialog, answering the two facts read that day: (a) a launch-only marker, `run_dependency_check_async(launch=True)`, passed by `app.main` and nowhere else (`test_only_the_launch_passes_the_launch_marker` reads the source), cleared when anyone asks for a check while the launch one is running, so About's Check again, the re-check after host setup and Check dependencies are answered at once; only the launch report also waits for `hold_for_user.busy_reason` (another window of ours in use), inside `_defer_if_floor_is_busy`; (b) a report that resolves a MISSING REQUIRED dependency, of any check, no longer has the 30 s bound: it waits as long as it must, logs on its first hold and then every 40 attempts rather than each one, and is dropped only when a newer check has started (`_dep_check_generation`); a report that only summarises keeps the bound. Retries now carry the window as their timer's context. Six tests in `tests/test_hold_for_user.py` and one in `tests/test_ui_main_window.py`; eight reverts probed with `scripts/revert_probe.py`, seven caught and the control unaffected. *Not ours to hold:* Picard opens as its own program after a rip, from a choice made in the post-rip dialog. *Must show now:* unchanged. **(1) and (2), 2026-11-03, what is ours (`ff14c134`):** the lock in (1) was the stacking: an application-modal question blocks every other window of ours, but Qt makes it the transient of its PARENT, which is what the desktop stacks by, so a question parented to the main window could sit under the window it had locked (measured, PySide6 6.11 offscreen: a box shown over an open modal dialog was the main window's transient). `ui/dialogs/stacking.py` now makes every application-modal dialog, on every show, the transient of the window it blocks (the newest modal, else the active window of ours), from `CenteredDialog.showEvent` and the app-wide `DialogCenterFilter`; its parent, which owns and centres it, is unchanged, and window-modal and modeless dialogs are left alone (moving a window-modal one would change what it blocks, and it cannot lock the app). For (2), the picker that stayed in front was a question opening by itself, which the holds above now keep from opening over another window, and the automatic offers wait while it is open; no window of ours sets a stays-on-top or bypass flag, which `tests/test_modal_stacking.py` now holds by a source sweep. Seven tests there; seven reverts probed with `scripts/revert_probe.py`, six caught and the control unaffected. What a real desktop (KWin on the owner's Bazzite) does with the transient is for a hardware run to confirm. **The test that opens each modal path over another modal window, 2026-11-03 (`8eec7b6b`):** `test_every_modal_path_opens_on_top_of_another_window` in `tests/test_modal_stacking.py`, over the conformance matrix's populations (every `CenteredDialog` subclass, every routed message box, every scenario that drives a box through its real code path), each opened over an application-modal dialog and over a modeless window in use, with floors from the measured counts (16, 40, 53; 74 application-modal, 33 window-modal, 2 modeless); `exec()` and `open()` are replaced by the check, and conftest's non-blocking message-box answers are put back to the module's own functions for it. Revert-probed: the filter's stacking, the window-modal exemption and the active-window fallback each caught; CenteredDialog's own stacking is not, because the filter it runs under stacks every dialog too (that path is held by `test_a_centered_dialog_is_stacked_without_the_app_filter`). Not covered: Qt's own file dialog. |
| R101 | **Triaged 2026-11-16 (OPEN-OURS): unchanged: `pyproject.toml:57` still pins `PySide6>=6.11.1,<6.12`.** **[ ] Move to PySide6 6.12 and add a Python 3.15 leg (after R99 and R100, not urgent).** PySide6 6.12.0 (2026-10-08) is outside our minor pin `>=6.11.1,<6.12`; 6.11 is still patched (6.11.3, 2026-10-26), so nothing is unpatched yet. Every PySide6 6.11 wheel declares `Requires-Python <3.15`, so a 3.15 leg needs 6.12 first (`ci.yml`'s matrix comment). The pin exists because a patch release once removed two menu shortcuts (Critical rule #11), so 6.12 is its own deliberate change: the suite on both, the UI conformance matrix, `main_window.standard_shortcut`'s checks, the AppImage recipe's `~=` changed with pyproject, and a hardware run. |
| R102 | **Triaged 2026-11-16 (OPEN-OURS, outside answer): still DRAFT (`.claude/skills/steward/SKILL.md`); the claude-code-skills checker's framework has not answered.** **[~] A `steward` skill, DRAFT (the owner, 2026-11-03: *"Add it as a draft. Be clear that you should own it, but the skill checker should give a framework for you. Make sure that YOU are thorough with it."*).** Built: `.claude/skills/steward/SKILL.md`, the loop and the rules, and `scripts/pr_steward.py`, which judges a commit's checks from the ruleset and the API (`GREEN`, `FAILED`, `PENDING`, `BLOCKED`, `CANCELLED`) and prints every failure line of a failed job; `tests/test_pr_steward.py` holds each rule, each revert-probed, and holds the skill's verdict table to the script. Run on live data the day it was written: PR #425 `BLOCKED` on `test (py3.11)`, and #421's merge commit `FAILED` on the AppImage build, the two things it exists to see. **Learned on 0.7.117's day:** it read GREEN while `appimage.yml`, which nothing requires, was still building; fixed at `a7484cfb` (a running check of any kind is PENDING), with a test. And twice a merge was sent with a guessed `expectedHeadSha`; GitHub refused both (409), but the rule is now in the skill: read the SHA from `git rev-parse`, never type it. **What keeps it a draft:** the claude-code-skills checker's framework (where a skill lives, its frontmatter, the draft marker, how a skill's script is checked), asked in the skill's last section; and a session's use of it from start to merge, which it has not yet had. |
| R104 | **Triaged 2026-11-16 (OPEN-OURS, watch): no recurrence is recorded in TASKS or the session log since 2026-11-03; by its own rule it closes if none appears, which a search of CI logs would confirm.** **[~] A native hang constructing a `QLineEdit` on CI's py3.14 leg (2026-11-03, once). A mechanism that fits the dump is fixed; the hang was not reproduced, so this closes if it does not recur.** *Found 2026-11-03:* the `uiscript-bundle` thread's frame, `threading.py:1028`, is the `del self._target, self._args, self._kwargs` that ends `Thread.run()` (Python 3.14.6; line 1082 of the dump matches the same file). The bundle closure in `ScriptRunner._write_run_bundle` captured `self`, and the accused test makes its runner as a temporary (`_run(win, ...)` in `tests/test_uiscript_permutation_verbs.py`), so that `del` dropped the LAST reference to a `QObject` and ran its destructor on the bundle thread, while the GUI thread built the next stand-in window's `QLineEdit`: destroying a `QObject` off its own thread is undefined in Qt. *Fixed:* the closure takes plain values read on the GUI thread (`src/platterpus/uiscript/runner.py`), held by `tests/test_uiscript_rip_verbs.py::test_the_bundle_thread_does_not_keep_the_runner_alive` (revert probe: detected). *Tried to reproduce:* a stress script of the same shape (a `QObject` with a child `QTimer`, its last reference dropped on a thread while the GUI thread builds `QLineEdit`s), 3,000 iterations on Python 3.14 with PySide6 6.11: no hang. *Was:* PR #425's run 41557841640, job 125660971230, at `e75a3d13`: `test_uiscript_permutation_verbs.py::test_expect_rip_argv_reads_the_report_on_disk` hit the 300 s `faulthandler_timeout` with the main thread at `tests/test_uiscript_rip_verbs.py:68` (`QLineEdit()` in the `_TrackTable` stub), below it `File "__init__", line ???` and `<invalid frame>`, so inside PySide6's C++ constructor; the other Python threads were a `uiscript-bundle` daemon thread (`runner.py:4358`, building a tar of the log folder, which touches no Qt) in native code with no Python frame, and execnet's reader. The same test passed on the run before at `da3d1d98` (one commit earlier, a footer the only change). Not reproduced locally: those three uiscript test files, five runs with `-n 4` on Python 3.12, all passed. `docs/testing.md` §5.ar's lesson applies: the accused test may be innocent, armed by an earlier test on the same worker. Next: if it recurs, compare the tests that ran on that worker before it (from the run's `-v` order), and check whether a test leaves a Qt thread or the bundle thread running into the next; a 3.14 venv locally to rerun the whole file order. |
| R110 | **Triaged 2026-11-16 (STALE-BUT-OPEN): the relock to `--exclude-newer 2026-11-04` took the in-range moves (PySide6 6.11.3, ruff 0.17.3, mypy 2.4.1; `build/locks/`) and dnspython 2.9.2 (`25c6885a`); left: cyclonedx-bom 7.6, zizmor 1.32, gitleaks 8.24.3 (`.github/workflows/ci.yml:586`), uv 0.13.5 in every lock header, and PySide6 6.12 (R101).** **[ ] Dependency audit of 2026-11-03: no known vulnerability; the moves that are due, none urgent.** `pip-audit` 2.10.1 over all eight locks (`--disable-pip --require-hashes`, as `ci.yml`'s job runs it): *No known vulnerabilities found*; its floor held (`uv==0.8.5` reports four advisories). OSV (`api.osv.dev/v1/query`) reports none for uv 0.13.5, python-appimage 1.4.6, actionlint 1.7.12, gitleaks 8.24.3 (Go module) or any of our six actions at their pinned versions; its floor held (uv 0.8.5 and `pypa/gh-action-pypi-publish` 1.14.1 each report theirs). Newest releases read from PyPI's JSON and `git ls-remote --tags` the same day; the cooldown cut-off is 2026-10-27, and every lock is at `--exclude-newer 2026-10-26`. **Within our ranges, for the next relock** (no lock moved here, none is a security fix): PySide6/shiboken6 6.11.2 to 6.11.3 (2026-10-26), hypothesis 6.170.10 to 6.170.12, jsonpointer 3.5 to 3.6, msgpack 1.2.3 to 1.2.4; and, once each clears its seven days, mypy 2.4.1 (2026-10-28), ruff 0.17.3 (2026-10-27), pytest 9.2.0 (2026-10-27), dnspython 2.9.1, pydantic 2.14.2 / pydantic-core 2.50.2, tzdata 2026.6, platformdirs 4.14.3, filelock 4.2.7, pip 26.3, sigstore-models 0.0.7, and python-dateutil 4.0.0 (a major, transitive through the sbom and CI locks). The weekly relock (`dependencies.yml`) regenerates these, but its pull request cannot open until the owner's step in R93, so a session carries the locks meanwhile. **Outside a minor pin, each a deliberate commit that re-runs its gate (Critical rule #11):** cyclonedx-bom 7.5 to 7.6.0 (2026-10-28, clear on 2026-11-04); zizmor 1.31 to 1.32.0 (2026-11-02, clear on 2026-11-09); PySide6 6.12, which is R101. **Pinned binaries and actions:** gitleaks 8.24.3 against 8.30.1 (the gating `gitleaks` job; release dates not read, since GitHub's API and release feeds are refused through this session's proxy); uv 0.13.5 against 0.13.7 (2026-11-03; 0.13.6 2026-10-27), which every lock header names, so moving it is a regenerate-and-`--check` change; `astral-sh/setup-uv` v10.3.1 against v10.3.3, which Dependabot's weekly action update carries; appimagetool 1.9.1 is the newest fixed release, and moving off it is R98. Current: actionlint 1.7.12, actions/checkout v7.0.1, setup-python v7.1.0, upload-artifact v7.0.2, attest-build-provenance v4.2.2, gh-action-pypi-publish v1.14.3, and every other direct dependency (build, twine, python-appimage, pip-audit, cyclonedx-python-lib, cryptography, sigstore, numpy, tomli-w, musicbrainzngs, pytest-cov, pytest-xdist, setuptools, wheel, shellcheck-py). |
| R111 | **Triaged 2026-11-16 (STALE-BUT-OPEN): the `HOST_FIELD` shape went to the fork in our round 37 lap 6 S6; left: the regex sweep's `\n` fill and the pattern it flags (`scripts/bommap/runtime_entries.py:30`).** **[~] Test-suite speed, and a quadratic regex found while measuring it (2026-11-03).** *Measured once:* the whole suite at `-n 4` on Python 3.12, 8 min 55 s wall (02:52:39 to 03:01:34 UTC, on a machine shared with other sessions), with `--durations=40`. The largest single item is the UI conformance matrix's module fixture (250 s of setup; its own CI job since 2026-11-02, so not in the test legs). *Found:* `export_identity.HOST_FIELD` (the fork's pattern) was quadratic in a run of blank lines under `re.M` (`^\s*` crossed line breaks from every line start); fixed with `[^\S\n]*`, same captures (a Hypothesis equivalence test against the old pattern), held by the prefixed-offender table in `tests/test_regex_bounded_time.py` (revert probe: detected). **NEXT ROUND for the fork:** their `HOST_FIELD` has the same shape; send it with our citation (seam rule: a fix that could help them is sent). **The regex sweep could not see it:** `test_regex_bounded_time.py` compiles each literal WITHOUT its flags, so `^` under `re.M` is never tried mid-string, and its fills have no `\n`. Adding a `\n` fill flagged one more pattern (`scripts/bommap/runtime_entries.py:30`, lead-in sweep) and tripped a meta-test; not done here, open. *Faster, nothing weakened (before and after, one test, `-n 0`):* `test_the_rewritten_wire_field_pattern_reads_what_the_old_one_read` 15.3 s to 2.1 s and `test_the_rewritten_requirement_pattern_reads_what_the_old_one_read` 2.5 s to 1.0 s (the pattern read from source once per process, not once per Hypothesis example); `test_the_status_block_check_can_fail` 12.7 s to 1.5 s (the handshake record read once per process, not once per mutation). *Left as they are, and why:* the `test_evidence_bundle.py` budget tests (16 s and 7 s) spend their time redacting 64 MiB, the real cap, and shrinking the cap would be lowering a bound; the `test_lap_language.py` checks are bound by subprocess calls to the version-control tool (93 in one test), which only a cache in `scripts/laplang` itself would cut; Hypothesis tests stay at their example counts. |
| R124 | **Triaged 2026-11-16 (OPEN-OURS, HARDWARE): (1) and (2) are done; (3) to (6) are not started, and (3), (4) and (6) need the rig.** **[~] Finding what we do not know we are missing (the review's E).** (1) plant one fault each in filed-shape reports and replay every grader (done, `2c5fcc8c`, `tests/test_uiscript_planted_faults.py`: every planted fault fails its grader but `FLAGS PRE`, R122); (2) an inventory guard generated from the source: every verb used by a rig script or allowlisted with its reason and unit test (done, `6a1d2953`: of the review's 8, five are used by other rig scripts or now by D2, and `abort`, `tier` and `needs` are the allowlist); (3) one Standard run under coverage.py against CI's coverage; (4) differential rips with the ripper older versions used and the owner's EAC log of the same pressing; (5) mine the filed runs for steps whose pass text never varies; (6) a disc corpus: damaged, HTOA, pre-emphasis, Enhanced CD, CD-Text, CD-R, a disc AccurateRip does not know, an unlisted drive | (1) and (2) for 0.7.118; (3) to (6) after it | ours; (3), (4) and (6) need the owner's rig and discs |
| R125 | **Audit 2026-11-25: retired as an umbrella: its items are R49, R134, R137 and R43, and the other rippers' features are R201 to R223.** **Triaged 2026-11-16 (STALE-BUT-OPEN): CTDB repair (R133) and the per-track time limit (R49, `securing_time_limit.py`) are done, and the parity-plan corrections are in `docs/eac-parity.md` (AcoustID, line 1648); the other features are unplanned.** **[ ] Features after 0.7.118 is out and a Full run on it is green (the review's F, and the owner's word of 2026-11-03).** Correctness first: CTDB repair; C2 pointers as evidence after a per-drive trust test; a per-track re-read limit as a multiple of real time, which is `.28`'s `--reread-time-limit` (the owner: *"Do 1 and 3"*, 3 being "add it after this release", with a default they choose; R49); the tray lock during a rip; HTOA; lead-in and lead-out overread per drive; the sub-channel as a second source for pre-emphasis; data tracks and Enhanced CD, image + cue, CTDB submission, CD-Text, re-verifying a library. And three corrections to the EAC parity plan of record: reading changed after 1.0 beta 3 (run EAC 1.8, the newest, 2024-07-15); EAC's log checksum is public (OPS's logchecker); EAC 1.x submits AcoustID fingerprints by default | Plan them after 0.7.118; correct `docs/eac-parity.md` now | ours |
| R131 | **Triaged 2026-11-16 (OPEN-OURS): unchanged; the same family as R155.** **[ ] Say, on the error-positions row of a track a later pass re-ripped, that its block CRCs describe the album pass and not the shipped read.** Found reading the 2026-11-04 run: in the whole-disc rip the block CRCs of tracks 3 and 5 combine to `3D8FCF0C` and `6902BCF0`, the album pass's reads, beside copy CRCs `59D352DD` and `E0036697` from the app's later pass. The block says `describes: album pass`, so nothing is false, but a reader comparing a row's block CRCs with its copy CRC is comparing two reads. Add the per-track fact (re-ripped by a later pass, or not) beside the row, with a test on that run's report. |
| R134 | **Triaged 2026-11-16 (STALE-BUT-OPEN, WIN): the hold is lifted: round 39 closed GO/GO on 2026-11-13 (R153) with G1 met, so by this row's own words it is a WIN, not a parity gap; EAC's 2026-11-12 re-rip did not verify track 3 either (`docs/eac-parity.md` G.7).** **[ ] HELD (2026-11-11, our round 39 lap 2 S11) until the five-rip run is read by both sides: the seconds where track 3's reads differ come from G4's `block_crcs` comparison, whose records now come only from the five-rip run (the owner removed the rips of 2026-11-09 and 2026-11-10), and if the chase and `.31`'s rule give `59D352DD` from a drive read in all five rips (G1), this row is a WIN, not a parity gap.** PARITY for track 3 (EAC reads it right on this drive; we do not reliably), and a WIN beyond it. Rebuild a disputed second from several reads, accepted only on AccurateRip v1 and v2** (Part G.4 item 2). Keep each read (the fork asked, in our round 38 lap 8, to keep every `-Z` read's audio and block CRCs); find the differing seconds by block CRC; candidates from per-sample majority and each observed variant, every sample one the drive returned; accept only on AccurateRip v1 and v2 (and the CTDB track CRC where present); cap and record the number of candidates tried. No ripper found automates this; two open requests on the ripper older versions used (its issues #667 and #679) ask for it. **2026-11-11:** the five-rip run ran (the owner's Full run on 0.7.122 with `.31`, from 12:34:47 UTC) and is filed on `evidence` at `ac0a5133`: in section R's five rips track 3 was `59D352DD` from a drive read, AccurateRip v1 128 and v2 200 (rip 3 by `.31`'s AccurateRip-guided rule). Still held until both sides have read it. |
| R137 | **Triaged 2026-11-16 (STALE-BUT-OPEN, parity): part (1) shipped in `.30` (`--read-vendor-settings` and `drive_declared`, read by `record_vendor_settings.py` and `record_drive_declared.py`); left: (2) the report in `--doctor` and an any-drive rig script, and (3) *Report this drive*, neither found in `src/`.** **[ ] PARITY (EAC's *Detect Read Features* measures a drive's cache, accurate stream and C2 for any drive). A drive report for ANY drive, and an opt-in way for a user to send it back** (the owner, 2026-11-05: *"shouldn't we keep testing, reporting, etc open to as many drives as we can? In case a user is testing our app with a way different drive and needs to report or add something? We want to give them the choice and also allow that, but also, see a report back on what it is saying for our bug testing"*). Three parts. **(1) Theirs, asked in our standing status:** a read-only drive report from cyanrip (INQUIRY and firmware; the MMC capabilities page and feature list: C2, speed selection, accurate stream, cache; and, only for a vendor that documents one, its settings read, such as Pioneer's buffer `0xF4`), since drive I/O is the ripper's under `docs/OWNERSHIP.md`; **the owner's word of 2026-11-05 on the vendor read: "Yes do this"**, opt-in, read-only, sent only to a drive whose INQUIRY names the vendor, each row citing its source (relayed in our round 38 lap 11); tri-state throughout, a capability the drive does not report is *not determined*, never *no*. **(2) Ours:** run it in `--doctor` and carry it in every bundle; a generic rig script that measures any drive on any disc (cache, speed honoured, repeat reads of every track against AccurateRip), not the reference disc's tracks 3 and 5 alone. **(3) Ours, the choice:** nothing leaves the user's machine on its own; a *Report this drive* action builds the bundle (no serial numbers, no home paths, no hostnames) and opens a prefilled GitHub issue for the user to read and send, so reports from other drives reach our testing. | (1) the fork's wording, read before they build it; (2) and (3) after it | ours, theirs |
| R140 | **Audit 2026-11-25: `FORK_PIN` is `.35`, past `.30`, so only old logs are affected; a won't-fix candidate.** **Triaged 2026-11-16 (OPEN-OURS, low): exact on `.30` and later; with `FORK_PIN` at `.32` the floor reaches only logs from older builds.** **[~] The record's "n agreeing of m" is a floor before `.30`**: keep the ripper's converged `-Z` match count in the parser so the count is exact on older builds. **2026-11-12, our round 39 lap 2 S16:** on `.30` and `.31`, which print an `Other read:` line for every `-Z` read not kept, a converged track with none now reads the exact count (`3 agreeing of 3`, round 39's track 3, was `at least 2 agreeing of 3`): `track_record_sources.OTHER_READS_COMPLETE_BUILDS`, `tests/test_track_record_exact_agreement.py`. Left: the older builds, which still say the floor | Parser change with property test | ours |
| R141 | **Audit 2026-11-25: the tooltip moved to `ui/track_results.py:173`.** **Triaged 2026-11-16 (OPEN-OURS): unchanged at `ui/rip_progress.py:1689`.** **[ ] UX: the results-table EAC cell's tooltip** still says "✓ = AccurateRip-verified and copy OK" for a chase read whose reads disagreed; match the record (`c1d2dcb1`) | Wording and its test | ours |
| R150 | **Triaged 2026-11-16 (OPEN-OURS, parity): unchanged: `supports_offset_detection` still returns False (`adapters/rip_backend.py:735-748`).** **[ ] PARITY (EAC's key-disc calibration): measure the read offset from a disc for a drive AccurateRip does not list.** The audit of 2026-11-12 against the owner's EAC guide found cyanrip's `-f` offset finder wrapped but not wired in (`adapters/rip_backend.py:735-748`, graded against +667). Needs a disc AccurateRip knows; run at drive setup, saved per drive, under the owner's rule *test the drive once, up front* (CLAUDE.md) | Wire `-f` into the drive-setup dialog on a worker, with its result recorded as the drive's offset provenance | ours |
| R151 | **Triaged 2026-11-16 (STALE-BUT-OPEN): the fork answered: both probes agreed in 17 runs on this drive, and which one setup keeps is ours (their round 40 lap 1 S7 and S8, lap 3 S5); left: our decision and the log row naming its source.** **[ ] Two cache-defeat sources, reconciled.** Our *Analyze cache* runs `cd-paranoia -A` (`cache_probe.py:13-15`, which calls it the rip's own engine), and the fork's `--cache-probe` with `-I` is a second, different probe (their provider contract, "costs seconds"). Say which one the log's `Defeat audio cache` row reports, and whether setup should use the fork's (asked in our round 39 lap 6) | A decision and one source of record | both |
| R152 | **Triaged 2026-11-16 (STALE-BUT-OPEN, parity): the fork answered yes: `-I` prints both lines without ripping, from the same capability queries a rip runs (their round 39 lap 7 S6, `cyanrip@e501a060:src/cyanrip_main.c:435-466`); left: our setup probe on a worker, saved per drive.** **[ ] PARITY: read the drive's declarations (accurate stream, C2) once at drive setup and save them per drive** (the owner's rule of 2026-11-12; part of R137). Today they are read only during a rip. Asked of the fork in our round 39 lap 6: does `-I` with an audio disc print `Accurate stream:` and `C2 errors:`, and does their read path depend on accurate stream (`docs/eac-parity.md` Part F row 16) | Their answer, then a setup probe on a worker | both |
| R157 | **Owner, 2026-11-16 ("8. a"): propose protocol v10 inside round 41; it still needs the fork owner's word.** **[ ] JOINT. Retire or define the protocol's deferred list** (old A6, A10 to A13, lines 3412 to 3442; `docs/handshake-protocol.md:1573-1578`): five header fields, the transport retirement, `CONCURRENT-WITH`, `SEAM-COMMANDS` and the semantic-change marker, carried since v6 and taken by neither v8 nor v9. With K1 (round 41 list item 5), a v10 on both operators' words (triaged 2026-11-16 from the old sections; the line is TASKS.md's at `34d20333`) | Protocol v10 | both |
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
| R172 | **[ ] The rip time estimate is one disc's: run C's disc 3 finishes well under its floor** (2026-11-16, found when TASKS R59 (a) filed run C's two reports as fixtures). `rip_estimate.MODEL_SEEDS` seeds the BDR-209D at 1.05 s of reading per second of audio, the reference disc's; run C's album pass on *Roots Music* disc 3, same drive, read at about 0.31 (1,070 s for 3,468 s of audio), so the whole-disc rip took 1,849 s against a floor of 3,851 s and the uniform secure re-read 4,015 s against 9,840 s. `tests/test_rip_estimate.py` names both in `_BELOW_THE_MODEL` and asserts they stay below, so the entry fails once the model learns the disc. The estimate only informs the user (the drive's own first rip replaces the seed), so no record is wrong **The same finding from a second filing** (merged here 2026-11-16, both agents named it R172): **[ ] Re-measure the rig's time-model seed against the `.31`/`.32` rips** (2026-11-16, found filing round 40's reports as test fixtures for R155 and R156): `rip_estimate.MODEL_SEEDS` holds the BDR-209D at 1.05 x audio time, the median of the filed first passes, but rip 1 of the 2026-11-14 Full run read 3,583 s of audio in 1,221 s (0.34 x) and took 2,928 s in all, below the model's low bound of 4,904 s for a dynamic rip with two re-read tracks. `tests/test_rip_estimate.py::test_every_filed_dynamic_rip_with_re_reads_falls_inside_the_model` leaves round 40's two rips out by name and counts them, naming this row. Settle whether the drive now reads faster (the cache check once per drive, `.31`'s reads) and the seed should move, or the model needs a second regime; then drop the exclusion | Decide whether the seed should reflect more than one disc, or the estimate say it is the reference disc's | ours |
| R176 | **Audit 2026-11-25: `.35` prints `Disc MCN:` in every log, `none (libcdio returned none)` on the reference disc (the fork's HW-19), so the line is always there to show.** **[~] Read cyanrip's `Disc MCN:` row in every proposed form: done 2026-11-16; showing it is open** (the fork's round 38 lap 3 S17, `docs/handshake/inbound/round-38-lap-03.md:130`, accepted in our round 38 lap 4 S11, *"We build the reader before your build"*, and asked after in their round 41 lap 1 S18). Today the row is `Disc MCN:       %s`, printed only when set (`cyanrip@13bec0a:src/cyanrip_log.c:1367`; the fork sets it only for a drive declaring it reads MCN and a code not all zeroes, `cyanrip@13bec0a:src/cyanrip_main.c:819-838`). `disc_mcn.py` reads the code (13 ASCII digits), upstream's `0000000000000` (`all_zero`), `none (libcdio returned none)`, `unknown (the driver does not report reading MCN)`, `unknown (capabilities query failed)` and no row (`not_present`) into `RipLog.disc_mcn` and `DiscInfo.disc_mcn` (one reader, both parsers); any other shape is `unrecognised`, kept bounded and screened, and logged; a second copy is not determined (the ONCE echo guard, and the same rule in the `-I` parser). The report carries `rip.disc_mcn` (schema 47). `tests/test_disc_mcn.py`, the forgery sweep and a never-raises property test hold it, each revert probed. **Left open**: no screen shows the MCN (the disc panel from `-I`, or the EAC-layout log, which has no MCN row in EAC's own format), and the echo sweep's corpus floor exempts the row until three committed logs print it | Say in our round 41 lap 2, answering S18, that the reader is built and which release carries it | ours |
| R186 | **[~] The filing tool replaced the FILING machine's hostname, `vm`, which is also the app's drive-profile prefix** (2026-11-17, filing round 41's run). `scripts/evidence_file.py stage` replaces `socket.gethostname()` in every unsigned member; in this cloud session that name is `vm`, and the app writes `vm:<vendor model>` as each drive profile's key (`drive_profiles.py`), so `vm:PIONEER BD-RW BDR-209D` became `host:PIONEER …` in a filed app log. Fixed for this filing with `--skip-host` (`filing_hosts`, two tests), and round 41 filed with `--skip-host vm`, 0 hostnames replaced. Open: round 40's filing (evidence `7faf1b9f`) reports "replaced the hostname in 28 unsigned files", most likely the same `vm:` rewrite; check its FILING record and say so in the ledger, since the evidence branch is never rewritten. Better still, the stage step should not replace the filing machine's name when the bundle was exported elsewhere, which the bundle's own `SOURCES.txt` could tell it. |
| R187 | **[ ] `tests/test_app_smoke.py::test_app_main_starts_up_clean_on_the_gui_thread` sometimes errors with "left a main window on screen" when it runs after `tests/test_accessibility_standards.py`** (seen 2026-11-17 by the wave-1 agent: 1 run in 3 on a clean copy of `c7ad4e40`, so not caused by wave 1). Find which test leaves the window and close it there; never re-run hoping it is noise. |
| R188 | **[~] The script console cannot open a built-in script except the full acceptance test** (the owner, 2026-11-17, looking for `overreadprobe`). **Load…** is a file picker on the home folder and cannot reach the scripts packed inside the AppImage; **Choose…** sets the startup script; **Use built-in** offers only `fullacceptance`. The terminal route works (`--run-script <name>`, resolved by `uiscript/find_script.py` from `rig_scripts/`), and our own rig sheet and our instructions to the owner named the console. Give the console a list of the built-in scripts, from the same `packaged_scripts_dir()` the terminal route reads, so a name we tell the owner is a name they can pick. **Design, the owner's of 2026-11-17** (replacing the smaller fix above): one **Run tests…** screen in place of *Run acceptance test…* and the console's pickers. Choose a pre-built test (Full, the evidence run; Quick or Standard, setup checks), a hand-picked combination of built-in tests, or a custom script file (any extension, checked by content: plain UTF-8, a size cap, every line valid before Run enables), with *Run this at start-up* and *Edit script…* for power use; a scripts folder of the owner's (`~/.config/platterpus/scripts/`, scanned at start) adds its scripts to the list, marked as theirs. **Built from blocks:** Full and Quick are broken into individual tests, and every pre-built test is an ordered list of them, so each test exists once. Blocks to have: each Full section (identity, settings and dialogs, disc, the whole-disc rip and its checks, overwrite, cancel and recovery, permutations, output formats, presets and naming, secure re-read, `-f`, cache probe, the no-offset refusal, de-emphasis pair, build comparison P5 and P6, repeat rips R, pregap agreement P4, leave on defaults Q) and Quick's; the existing over-read probe, disc ISRC, drive mode, drive speed, unknown disc, walkthrough; and new: a drive setup check (offset, cache, declared features, read performance; once per drive), a first-run check (a throwaway profile, No then Yes), and the C2 probe at the known seconds brought in from `drivetest.sh`. `round08joint`, `police-rerip` and `track3abba` leave the list. **Rules:** a block states what it needs (a disc identified, a build installed) and the runner sets it up once, and each block restores what it changes; order lives in the pre-built list (P4 after every rip); a run records its preset and every block, and counts as evidence only when the whole Full list ran in order; and before anything changes, a test proves the new Full and Quick lists expand to exactly today's `fullacceptance.txt` and `quickcheck.txt` steps. **Repeats and comparisons** (the owner, 2026-11-17): in a pre-built test, each entry is a block, a count and the comparison that must hold across the runs (e.g. the repeat rips ×5, every track verified in every run, pregaps agreeing), fixed in the pre-built definition with each comparison's severity declared in advance. In a custom script, two verbs: `run-block <name> ×<N> as <label>` (the block as a subroutine, runs labelled `<label>1` to `<label>N`) and `expect-repeats <label> <rule>` (`same-crc`, `verified`, `at-least K of N`, naming the run and track that broke it); the existing compare verbs work on those labels. No general loops or variables: a script stays a list read top to bottom, and every pass or fail is a named check. Built with wave 2, after round 41 closes, a screenshot of the screen to the owner before it merges. **The owner, 2026-11-23:** the screen's screenshots are approved ("both ok"); the C2 probe stays a rig script the owner runs by hand (`docs/rig-scripts/drivetest.sh`, which reads raw sectors inside the container), not a block the app runs, and the Run tests screen points to it; Full's five repeat rips stay one fixed block, not a counted entry, so Full's steps do not change. **Built 2026-11-23 (wave 2, rebuilt to the approved design):** `rig_scripts/blocks/` (Full in 19 blocks, Quick in 8, setup `needripper`/`needoffset`/`needdisc`, `drivesetup`, `repeatrip`), `fullacceptance.txt` and `quickcheck.txt` generated from them by `scripts/emit_rig_scripts.py` and pinned byte for byte to origin/main (675 and 78 steps, `tests/test_prebuilt_tests.py`); `uiscript/blocks.py`, `prebuilt.py` (Repeat rips ×5 new), `run_block.py`, `block_verbs.py`; the verbs `run-block` and `expect-repeats`; Tools → Advanced → **Run tests…** with its three tabs, the box under the choice (titles, estimate, evidence), Edit script…, Run this at start-up, and the C2 line; evidence unchanged. **Left:** the first-run check (needs a throwaway-profile verb); the drive setup check's declared features, read performance and over-read answer (each needs a verb); the packaged scripts (over-read probe, disc ISRC, drive mode, drive speed, unknown disc, walkthrough, secure re-read, cancel and over-read) are offered whole, not yet cut into blocks; and the headers of `fullacceptance.txt` and `quickcheck.txt` still name *Run acceptance test…* and the console's Load, because their bytes are pinned: a header edit in `fullstart`/`quickstart` that re-pins both hashes is a change of its own. |
| R189 | **Audit 2026-11-25: its remainder is R188's drive setup check verb.** **[~] `overreadprobe.txt`'s last check and its header** (the over-read probe of 2026-11-17, filed at `977d78fa`; our round 41 lap 6 S11). Its step `expect force_overread off` read the owner's own Overread setting, which was on before the run, and failed the probe for a thing it neither set nor changed: it should read the setting before the first `-O` step and check the same value after the last. Its header says "the bundle the run ends with carries both" logs, but a console run makes no bundle; say where the logs are (the two folders in the rips folder) and that the transcript carries each read's whole output. Then the drive setup check of R188 records the answer the probe gave on this drive, *beyond-disc frames refused at both edges*, so `-O` is offered only on a drive that returns them. **Done 2026-11-23:** `keep force_overread` before the first `-O` read and the new verb `expect-kept force_overread` as the last step; the header says the two logs are in `overreadleadout` and `overreadleadin` in the rips folder and the transcript carries each read's whole output. **Left:** the drive setup check recording the probe's answer, which needs a verb (R188's drive setup item). |
| R192 | **[ ] Show `.35`'s `Session gap: not determined (…)` where a track's end is shown** (the fork's round 42 lap 1 S7; read and kept on the track as `TrackResult.session_gap` since 2026-11-23, `session_gap.py`). Nothing renders it: the report's per-track rows, the EAC-layout log's status lines and the track record still present that track's `End LSN:` as measured. Needs a report field (a schema bump) and a sentence saying the session layout was not determined and how many frames were cut by assumption. Only an image or a drive that fails the last-session query prints it; no drive has yet | Report field, EAC-log sentence | ours |
| R193 | **[ ] Read what `.36` will print, before it prints it** (our round 42 lap 2 S19, answering the fork's lap 1): the complete `Ripping errors:` list with its eight new part names (S12) and `frame reads with errors` beside `frame reads failed` (S14); `Encoder errors:` counting a failed partial track (S15, check `_ENCODER_FAILED_COUNT` reads `1 track failed (1), read not completed; no whole track was encoded`); the album loudness rows' `unknown (no audio track finished)` with no `Album Loudness` block (S23, and the completeness sweep must not flag it); the progress line's `rest of rip read once - …` clause beside `ETA - …` (S25); and `Drive speed:` after `Speed:` (S29). Each for the form the fork gives and the form it prints today, each with a never-raises property test; then the lap carrying that release tells the fork which forms it may print. Also, for S21: send `--overwrite-existing` with Replace, and wherever a rip goes into a folder that already holds files, for a build that takes it, once the fork's first build accepts it. |
| R194 | **Audit 2026-11-25: the same root as R172: the seed is 1.05 s of reading per second of audio (`rip_estimate.py:60`), shown as "1.0x" (`uiscript/run_estimate.py:290`); also find why the drive's learned speed is not used.** **[ ] The Run tests screen's Full estimate contradicts its own label** (the owner's screenshot of 2026-11-23): the list says *Full acceptance — 4 to 6 hours* and the box under it *about 12h 5m, up to 49h 55m … 29 rip(s) about 11h 50m at 1.0x (the speed the project's rig measured for this drive model)*. Filed Full runs on the BDR-209D took about five hours (round 41's from 01:14Z, about 5 h), and its rips read at about 4.7x (the over-read probe's track 14, `Extraction speed:  4.7x`), so a 1.0x seed for this drive model is wrong, or is read from the wrong record. Find where the per-model speed seed comes from (the drive profile's learned speed, R109) and why it is 1.0x here; make the label and the estimate one number from one source. |
| R197 | **[ ] A `--run-script` launch's bundle leaves out the album folders** (found filing round 42's second Full run, 2026-11-25): the runner's own bundle (`uiscript/runner.py`, `evidence_bundle.build_bundle`) packs the run folder (`scriptrun/`), the script's own rip folders (`scriptrips/`) and the app log, but not the album folders of the rips it made, nor their `-j` records; an acceptance session's bundle (`test_session.py`) packs them, so round 41's had 201 members and round 42's 63, with 2 of its 28 rips' cyanrip logs. The rips' output survived only because the app log carries it at DEBUG. Fix: give the `--run-script` bundle the session's album and record channels (strict allowlist, `album_dirs=`), with a test that a script's `rip` lands its album folder's logs in the bundle. |
| R198 | **[ ] The round 42 wrapper's check for an open Platterpus missed one** (2026-11-25): `round42run.sh` ran `pgrep -f 'platterpus.*AppImage'` before the first Full run and found nothing, while the app log shows a window launched from the desktop at 23:04:47Z open until 09:38:04Z; `drivetest.sh`'s `pgrep -f "platterpus-x86_64.AppImage"` then found a process at 06:17:00Z. Why the first missed it is not known: no process list was taken. Before the next rig script relies on such a check, find what an AppImage launch of Platterpus looks like in the process table (relaunch after an update, desktop launch, terminal launch) and check for it by one shared rule; `drivetest.sh` now names what it sees (R195). |
| R199 | **[ ] Nothing ran `handshake.py --check` on our own held lap until the release** (2026-11-25): our round 42 lap 4 merged to `main` held three times (#518, #522, #523) without its `Confirmations` heading or the pin-policy roll sentence, and `--check` found both only after the announce; it was fixed before the lap reached `main` released, so the fork never saw it. Make a test run the outbound check on every lap under `docs/handshake/outbound/`, held or sent, so a held lap is held to the protocol from its first commit. |
| R200 | **[ ] Keep the bundle a run names until it is sent** (the fork's round 42 lap 5 S6, accepted in our lap 6 S6): `evidence_bundle.prune_bundles` keeps the newest 20 bundles by modification time and protects only the one just written (`evidence_bundle.py:1118`, `:1135` at `a964e3bd`), so the bundle a run names in `SEND THIS ONE FILE` is deleted once 20 more are written; every rip writes one, so the first round 42 Full run's bundle was gone before the second run ended. Fix: never prune the newest run's named bundle (a run's session bundle) by count; prune it only when the next run's replaces it. Test: a run bundle followed by 25 rip bundles is still there. |
| R201 | [ ] **A whole-disc image with a single-file cue, and a choice of cue style** (parity: EAC, CUERipper, dBpoweramp, XLD, EZ CD, fre:ac, K3b, Rubyripper, abcde). Build it from the verified per-track FLACs (contiguous, gaps appended) through the transcode adapter, write a single-file cue with every gap, index, ISRC and flag, and check the image against AccurateRip and CTDB. No second read of the disc. Medium. Planned (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R202 | [ ] **Say when a disc carries HDCD, never decode it into the master** (dBpoweramp, EZ CD, fre:ac, CUETools, cyanrip `-H`). Run ffmpeg's `hdcd` filter over the finished FLAC and record the result as a flag in the report and the log; `-H` is never sent, since a decode changes samples. Ask the fork whether cyanrip can report HDCD without decoding (our asks file of 2026-11-25). Easy to medium. Planned (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R203 | [ ] **A de-emphasised playback copy of a pre-emphasised disc** (dBpoweramp, EZ CD, Rubyripper, cyanrip by default). A derived output through the transcode adapter (ffmpeg `aemphasis`); the master stays flagged and untouched (Critical rule #4). Easy to medium. Planned (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R204 | [ ] **Check and fix an old rip: AccurateRip and CTDB on files already on disk, and correct a wrong offset** (CUETools, XLD, and a Linux ripper's `image verify`; Part H item 13). `--ctdb-calibrate` already sweeps offsets with CTDB; add the AccurateRip pass (`accuraterip_crc.py`) and apply a found offset through the FLAC rewrite path. Medium; a win for users with old libraries. Planned (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R205 | [ ] **Show the positions a rip was unsure of, and let the user hear them** (EAC lists and plays them, dBpoweramp marks them, EZ CD logs them). Positions are in the report since `.25`; this needs R44's log wording first, then the UI (QtMultimedia on the FLAC). Medium. Planned (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R206 | [ ] **CD-TEXT as fallback tags when MusicBrainz has no match** (parity: EAC, abcde, dBpoweramp, EZ CD, fre:ac, foobar2000, K3b). The fork prints `CD-TEXT:` and the `-I` run already happens; our parser leaves it unparsed (`parsers/cyanrip_log.py:3577-3585`). Offer it in the unknown-disc path before Picard. Easy. Next (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R207 | [ ] **Find the release by hand: MusicBrainz text search, a pasted release URL, or a barcode** (dBpoweramp, XLD, Sound Juicer). Through the existing `MusicBrainzClient` adapter (musicbrainzngs search); Discogs would need a new dependency and the owner's word, so not now. Easy to medium. Next (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R208 | [ ] **Use the disc's MCN to rank the release picker's candidates** (Sound Juicer). Compare the MCN `disc_mcn.py` reads with each candidate's barcode and put a match first, saying why. Easy. Next (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R209 | [ ] **A second metadata and cover source from CTDB's answer** (CUERipper takes MusicBrainz and Discogs data through CTDB). We already call CTDB; find the request parameter in CUETools' `CUETools.CTDB` source and show its metadata as a second opinion. Easy to medium. Planned (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R210 | [ ] **Cover art: a size limit or resize on embed, and more than one source later** (dBpoweramp, EZ CD). The size limit is easy; more sources follow R209. Planned (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R211 | [ ] **Offer "Submit this disc ID to MusicBrainz" for an unknown disc** (Sound Juicer, Picard). `cd_info.musicbrainz_submit_url` is parsed and nothing calls it (`parsers/cd_info.py:61`, `parsers/cyanrip_info.py:133`). Easy. Next (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R212 | [ ] **Can Picard read our EAC-layout log, or should we hand it the disc ID?** (Picard reads EAC, XLD and one Linux ripper's logs; Part H item 21). Test it on a filed log; if not, pass the TOC or disc ID when we launch Picard. Small investigation. Planned (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R213 | [ ] **Classical work and movement tags from MusicBrainz work relationships** (dBpoweramp). Check what we write today first. Medium, low priority. Planned (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R214 | [ ] **Rip on insert, off by default** (fre:ac, Sound Juicer, dBpoweramp Batch Ripper). A media-change signal on a worker starts the chosen rip when a known disc goes in. Easy. Planned (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R216 | [ ] **Several output formats in one rip** (dBpoweramp, cyanrip `-o`, Rubyripper, abcde, Asunder). The transcode adapter loops over the chosen formats, each checked against the FLAC master. Easy. Next (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R217 | [ ] **More derived formats: ALAC, Opus, Vorbis, AIFF; AAC later** (dBpoweramp, XLD, EZ CD, fre:ac, cyanrip). **Approved 2026-11-25 on the owner's word** (*"we can do this"*, PLANNING KDD-48). ffmpeg's built-in encoders, through the one transcode adapter and the one dependency subsystem, each with tags, art and a decode-and-compare check against the FLAC master; Critical rule #4's list of formats is amended in the change that ships the first one. Pairs with R216 (several formats in one rip). Medium. Next (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R218 | [ ] **An M3U playlist beside the rip** (parity: EAC, Rubyripper, Asunder, K3b and others; Part H item 29). Easy. Next (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R219 | [ ] **The EAC-layout log's `Gap handling` row names the undecided track instead of reading undetermined for the whole disc.** Round 42: 50 of 54 logs print `(undetermined: the ripper could not measure a pregap)` because track 9 is `94 or 95 frames (undecided)` (`eac_log_export.py:805`, `:897-915`), while the cue cyanrip writes commits to 95 frames (`INDEX 00 03:44:10`) where EAC reads 94 in 4 of 4 sessions. Ours: say `Appended to previous track (track 9's pregap undecided: 94 or 95 frames)`; theirs (the asks file): the cue says which value it chose and why. Small; log honesty. Next (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R220 | [ ] **The EAC-layout header names the encoder that ran.** It prints `FLAC encoder: flac 1.5.0, metaflac 1.5.0` (`eac_log_export.py:1844`), but cyanrip's libavcodec encodes every track; host `flac` encodes only a CTDB-repaired one (`adapters/flac_rewrite.py:10`). The comment at `:1049-1054` says otherwise. Small; record correctness. Next (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R221 | [ ] **EAC's `Track quality` row: a substitute from paranoia's counts, or keep `(not reported by the ripper)`** (EAC's 99.8 % flagged its own wrong track 3 on 2026-11-12). Decide, then render. Small, low. Planned (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R222 | [ ] **Detect a manipulated TOC (copy-protected discs)** (EAC). Say so before the rip. Medium, low. Planned (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R223 | [ ] **Lock the tray during a rip** (EAC). Ours or the fork's, whichever is cheaper; the asks file asks. Small, low. Planned (the 2026-11-25 audit; decisions and sources in `docs/eac-parity.md` Part H) |
| R224 | [ ] **WCAG 2.2: Start rip, Cancel and Force stop are 44 px tall** (CLAUDE.md accessibility rule 3: 44 px for anything that commits). `ui/rip_controls.py:84-92` sets no height; `_COMMIT_HEIGHT` exists only in `ripper_picker.py` and `dialogs/setup_center.py`. Small; a convention the code breaks. Next (the audit; `docs/ux-design-principles.md`, WCAG item 4) |
| R225 | [ ] **WCAG 2.2, the rest of the open list:** contrast measured from pixels, a greyscale and colour-blindness pass on the track table, and forced colours for the validation border (`docs/ux-design-principles.md`, WCAG items 1 to 3). Medium. Planned (the audit) |
| R226 | [ ] **The rip addendum carries a time** (the fork's PP-14). Since `.27`, `Kept read began:` gives one to stand on; `rip_addendum.py` writes none. Small. Next (the audit) |
| R227 | [ ] **Read `Pregap sample peak:`**, the line our round 41 lap 2 S14 told the fork we still want (their US-21 still lists it as unanswered). A reader with a never-raises property test, shown in the report. Small. Next (the audit) |
| R228 | [ ] **Fill our `?` cell at `docs/seam-commands.md:261`** (the fork's PP-12), with the next shared-document version. Small. Round 43 (the audit) |
| R229 | [ ] **Write the two proposed seam rules:** a close condition that names a filing names its repository and path, and a test or rig script names no round, release or build it does not read from the run (STATUS-OPEN `rules-proposed`; adopted in our round 40 lap 4 S21(b)). Into `docs/seam-rules.md` on both sides, with the next version. Small. Round 43 (the audit) |
| R230 | [?] **The native install's rescue refuses a second signal** (`ccb10df0`, `937c86a8`; STATUS-OPEN `native-install-cancel`). **Blocked:** only a native install on hardware shows it, and none has been tested (the audit) |
| R231 | [ ] **Carry the green relock pull request #512 and Dependabot #529 onto a session branch, with the regenerated files, and close both** (the Commit & PR hygiene rule for Dependabot; R93's follow-on; covers part of R110). Small. Next (the audit) |
| R232 | [ ] **Packages for the flat top level, one per commit, then the overdue splits.** `src/platterpus/` has 148 flat modules. In order: the Qt-free modules that each read one cyanrip line (`safe_int`, `disc_mcn`, `pregap_search`, `session_gap`, `ripping_error_parts`, …) into `parsers/`; then `update/`, `record/`; rename `test_session.py`; the rest judged one at a time. Then split `ui/main_window_rip.py` (5,486 lines) into further mixins, `parsers/cyanrip_log.py` (4,911, no monkeypatch targets, the safest) and `deps/fork_source.py` (3,872, patched by 52 `setattr(fork_source, …)` calls). Every step moves with its string monkeypatch targets, `_OVERSIZE_MODULES` keys, mypy opt-outs, `mutation.yml` targets, PLANNING §1 and §2 and logger names, as a `git mv` commit then an import-fix commit. Large; risk low per step. Planned (the 2026-11-25 organization review) |
| R233 | [~] **Most of it done 2026-11-25 on the owner's word ("clean up all you can").** Moved unchanged to `docs/archive/tasks-closed-to-2026-11-16.md` → *Moved 2026-11-25*: the R table's 142 closed rows (the open 103 stay, sorted by number), the 2026-11-16 and 2026-10-12 rankings, and seven sections with no open row; `tests/test_tasks_rows_are_unique.py` now reads both files, so a retired number is never reused. **Left:** the closed bullet rows inside the 16 sections that still hold an open row (round 25's agenda, P1's backlog, the gate-audit backlog and others), and the archive's name, which now undersells it (`tasks-closed.md`, a commit of its own that retires its inbound links). |
| R234 | [ ] **`PLANNING.md`: a KDD status table at the head of §8, and §1 compressed.** The table names each KDD's superseder (KDD-02, 07, 15 by KDD-18; KDD-26 by KDD-37 D9; KDD-14 by KDD-47; the rest from each body). §1's 574-line per-file tree becomes a folder-level tree with each package's modules as one list; the per-module text stays in §2, and `tests/test_planning_module_map.py` checks basenames only. Medium, low risk. Planned (the 2026-11-25 organization review) |
| R235 | [ ] **`docs/cyanrip-fork.md`: archive Part E, banner Part A; one heading per Part in it and in `docs/eac-parity.md`.** Part E (about 990 lines) closed 2026-08-15 by its own heading: move it to `docs/archive/` under a dated name with a two-line stub under `## Part E` (tests and records cite "Part E"); banner Part A as overtaken by KDD-32 and KDD-33; point Part B §0 and §1 at the fork's live patch list. Collapse the doubled H2 at the head of each Part in both files, keeping the `## Part X` heading the scoping test keys on. Medium. Planned (the 2026-11-25 organization review) |
| R237 | [ ] **Split `CHANGELOG.md`** (20,208 lines, 1.7 MB): 0.7.x stays, 0.1 to 0.6 move to `docs/archive/` with their compare links, as the fork did. Check every test and script that reads it for history (`test_no_stale_version_claims.py`, `test_no_previous_ripper_in_live_text.py`, the disc-writing word test, `test_documented_ripper_flags_are_real.py`, `test_handshake_tooling.py`, `scripts/handshake.py`); `release.yml` reads only `[Unreleased]` and the new version. Medium. Planned (the 2026-11-25 organization review) |
| R238 | [ ] **`docs/testing.md` §5 in label order with an index table at its head; §5C to the archive.** About 3,600 lines of cases in no order, cited 321 times by label and spelled two ways (`§5.x` in 45 of 63); citations are by label, so reordering breaks none. §5C, the 2026-08-28 lesson-to-gate audit, moves to `docs/archive/` with a graduation-map row. Medium, text only. Planned (the 2026-11-25 organization review) |
| R239 | **[x] Done 2026-11-25 on the owner's word** (*"R239 ... do it"*, with the code left to our call; held for some hours on the owner's choice, *"hold until tests grow"*, because removing its tests took CI below the collected-test floor, and landed once that day's new tests had lifted the count): §6.2's ritual moved unchanged to `docs/archive/release-signing-ritual-2026-11-25.md`, §6.2 now says what protects an update; `update_signing.py`, the updater's dormant gate and their tests removed (one test kept: the updater never requests a `.minisig`); `cryptography` kept as a pinned constraint because `sigstore` runs on it (DEPENDENCIES.md log, 2026-11-25); KDD-26 and KDD-37 D9 amended. *Was:* [?] Archive §6.2, the release-signing ritual, for signing that is never armed (KDD-37 D9) (the 2026-11-25 organization review) |
| R240 | [ ] **Decide `data/`**: its AppStream metainfo file is used by no build or test. Either move it beside the `.desktop` in `build/python-appimage/`, wire it into the AppImage and validate it with `appstreamcli validate` (build and inspect first: whether python-appimage picks it up on its own is unknown), or retire it. Small. Planned (the 2026-11-25 organization review) |
| R241 | [ ] **Retire the superseded colon kit in `scripts/cyanrip/`** (`setup-fork.sh`, `apply-colon-fix.py`, `issue-colon.md`, `pr-colon.md`, `verify-meta-colon.c`; `build.sh` if the wizard replaced it). First move `UPSTREAM_URL`'s source out of `setup-fork.sh` (`scripts/bommap/ripper_entries.py:40` reads it) and rerun `scripts/emit_bom.py`; then `tests/test_cyanrip_colon_patcher.py`, `tests/test_audit_regressions.py`, the `docs/cyanrip-fork.md` Part B links, `docs/README.md` and `PLANNING.md`. Medium. Planned (the 2026-11-25 organization review) |
| R242 | [ ] **Only if touched anyway:** `docs/rig-scripts/*.sh` to `scripts/rig/` (the operator's documented path changes, so announce it in a lap); split `tests/test_ui_main_window.py` (15,493 lines) along the mixins; `docs/test-plan.md` Part B links to `output_reference/README.md` for the per-track CRC table instead of restating it (check no test reads it there first). Low value. Planned (the 2026-11-25 organization review) |
| R243 | [ ] **`docs/handshake/README.md` says why `verified/` has held nothing since round 21**, after reading protocol v3's history for the reason, and what became of `PROPOSAL-operator-seam-automation.md` (its bytes stay identical in both repos; the fork is asked whether both sides archive it unchanged). Small. Next (the 2026-11-25 organization review) |
| R245 | [ ] **A timed-out disc read frees the drive by killing every process on it, our own included.** `drive_control.free_drive` runs `fuser -k` on the device, so a cache check the setup window is running dies with the read that timed out (R244 closes only the press-during-a-read path). The other path is open: a disc inserted while the setup window's automatic check runs starts a scan beside it. Make a disc read wait while the setup window's check holds the drive, and have freeing the drive spare a reader Platterpus started on purpose, or say which it killed. Also evidence for the fork's HW-20: in the same log the lone `cyanrip -I -N` read did not hang after `Opening drive...`; it was progressing (pregap searches of 12 to 41 s, an ISRC search) when the 300 s limit stopped it, with `cd-paranoia -A` reading the same drive. Next (the owner's log of 2026-11-25) |
| R248 | [ ] **Setup and drive setup say when there is nothing to redo** (the owner, 2026-11-25, after reinstalling: *"we should keep settings on those and let users know if the hardware is the same as the last setup not need to run (and check if it is)"*). Drive facts already persist per drive fingerprint and firmware (offset, cache verdict; the automatic check skips a measured drive), and setup already finds every tool present in seconds, but neither tells the user so before they run it. Show on Setup & Updates, per row, what was last done and whether it still holds, checked now: *Drive setup: done for PIONEER BDR-209D, firmware 1.51, on <date>; this is the same drive and firmware, nothing to do* (or *firmware changed, run it again*); *Setup: the ripping container and the approved ripper build are in place*. Keep the button for anyone who wants to run it anyway. Next (the owner's word) |

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
- [x] **Closed 2026-11-25 (audit): duplicate of the permutations row above it (E2 (a), a drive the AccurateRip list does not carry); tracked there.** **Triaged 2026-11-16 (HARDWARE): unchanged; needs a drive the list does not carry.** **E2 on a drive the AccurateRip list does not carry**: owed before 0.9.1, which
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

- [x] **Closed 2026-11-25 (audit): duplicate of R157; tracked there.** **A6. Eight wire fields every current lap carries and no shared doc defines** —
  `INBOUND-OBSERVED`, `NEXT-LAP`, `VERDICT-SOURCE`, `PEER-PIN-SOURCE`,
  `FROM-COMMIT-SOURCE`, `PIN-POLICY`, `BREAKING`, `SHARED-HASHES`/`-SOURCE`: 0
  occurrences each in `handshake-protocol.md`, `seam-rules.md`, `seam-commands.md`
  (re-counted 2026-09-23). *Derived.*
  - *Audit 2026-09-25: partly done.* INBOUND-OBSERVED and FROM-COMMIT-SOURCE are defined in v6. NEXT-LAP, VERDICT-SOURCE, PEER-PIN-SOURCE, PIN-POLICY, BREAKING and SHARED-HASHES are deferred to v7.
  - **Triaged 2026-11-16 (open, joint):** `HANDSHAKE-NEXT-LAP` was defined in v7 (`docs/handshake-protocol.md:212`) and `HANDSHAKE-INBOUND-OBSERVED` made required in v8 (E11). The other five fields are still on the shared deferred list (`docs/handshake-protocol.md:1573-1578`), which v8 and v9 took nothing from; fork list F7 of 2026-10-12.
- [x] **Closed 2026-11-25 (audit): duplicate of R157; tracked there.** **A10. The evidence-transport proposal** — adopt or formally retire 5b.1–5b.8
  (ours: 5b.2/4/5/6 as written, 5b.1 as an end-state obligation, 5b.3 gating both
  sides); pull transport with `main` as ref of record, practised but unwritten; the
  filename convention as a §5c; the envelope (§4b "exactly once", and whether it is
  needed now that laps travel by git — we still emit one). Cite: fork
  `PROTOCOL-v5-PROPOSAL-evidence-transport.md`; TASKS@b8f89a2:581, 1705–1729.
  - **Triaged 2026-11-16 (open, joint):** still on the shared deferred list (`docs/handshake-protocol.md:1577`). HR-2 (v9 §17) now governs evidence on the `evidence` branch, so what is left is formally retiring 5b.1 to 5b.8 and the envelope (`scripts/emit_envelope.py` still exists); fork list F7.
- [x] **Closed 2026-11-25 (audit): duplicate of R157; tracked there.** **A11. `HANDSHAKE-CONCURRENT-WITH`** — proposed round 7 laps 32–33, never built;
  adopt or retire (K1 may subsume it). TASKS@b8f89a2:2928.
  - **Triaged 2026-11-16 (open, joint):** still deferred and never built (`docs/handshake-protocol.md:1577`); retiring it jointly is the fork list's F4 of 2026-10-12, not yet done.
- [x] **Closed 2026-11-25 (audit): duplicate of R157; tracked there.** **A12. A `SEAM-COMMANDS: audited @ N` close field** — prototyped, reverted for
  want of the shared file; the round-8 bump never happened. TASKS@b8f89a2:3734.
  - *Merged 2026-09-30, verbatim, from the duplicate row "Propose the protocol version bump in round 8" (P0, 2026-08-06) (it was `[ ]`):* **Propose the protocol version bump in round 8**, with the four-row table above as the specified behavior, and land the gate change **in the round where both sides adopt it** — not before.
  - **Triaged 2026-11-16 (open, joint):** still deferred (`docs/handshake-protocol.md:1578`); fork list F7.
- [x] **Closed 2026-11-25 (audit): duplicate of R157; tracked there.** **A13. A semantic-change marker** — a derived contract diff cannot see a change
  of meaning (round 21's `Ripping errors:` recount changed no format string); pairs with
  defining `BREAKING`. KI:1364.
  - **Triaged 2026-11-16 (open, joint):** still deferred beside a definition of `HANDSHAKE-BREAKING` (`docs/handshake-protocol.md:1578`); fork list F7.

### B — Shared-doc defects that bump only that doc's own version

- [x] **Closed 2026-11-25 (audit): stale: fixed by its own triage; the rest is the fork's US-10 and US-11.** **B3. `seam-commands.md` — five known-wrong statements**: §7's summary (48 of 68
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

- [x] **Closed 2026-11-25 (audit): duplicate of R159; tracked there.** **C10. The challenge ledger stops at round 21 lap 4** — unrecorded: r22 C1 (our
  circular `GO`, they were right), r22 lap 5 (our withdrawn `handshake_round` claim),
  r22 lap 3 §H1, r23 §A (tracks 3 and 5, we were right), r23 lap 1 §H6, r24 §B3 (the
  §5b reading, we were right). `docs/cyanrip-handshake.md` §9. *Derived.*
  - **Triaged 2026-11-16 (open, ours):** still missing. The ledger (`docs/cyanrip-handshake.md` §9) goes from row 19 (round 21) to row 20 (round 26 lap 4) and ends at row 22 (round 29), so rounds 22 to 24 and 30 to 40 are unrecorded.
- [x] **Closed 2026-11-25 (audit): duplicate of R169; tracked there.** **C11. Handshake-gate test quality** — the vacuity and rule rows at
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

- [x] **Closed 2026-11-25 (audit): stale for us: it is the fork's US-4.** **D9. Their tools hygiene (low)** — `tools/mutate.py` `EXCLUDED_TESTS` premise
  (KI:97); "lap commit list names its range" timeout (KI:244); flaky "interrupted sample
  freshness" (KI:153).
  - *Audit 2026-09-25: not ours to verify.* The fork's; still open.
  - **Triaged 2026-11-16 (open, fork):** the `EXCLUDED_TESTS` premise is now derived and named (`cyanrip@6b5b9dc7:docs/KNOWN-ISSUES.md:60-69`); the *lap commit list names its range* timeout is still open there (`:487`); no freshness entry was found in that file.

### E — Contract, argv and log surface

- [x] **Closed 2026-11-25 (audit): stale: `File(s):` stays the request by agreement (the fork's ROUND-22-PLAN banner), and `.27` prints a `not written whole:` line for the rest.** **E2. `File(s):` lists what was requested, not what was written.** Theirs. KI:1213.
  - *Audit 2026-09-25: not ours to verify.* The fork's; their KNOWN-ISSUES says STILL OPEN.
  - **Triaged 2026-11-16 (open, fork):** still marked STILL OPEN at `cyanrip@6b5b9dc7:docs/KNOWN-ISSUES.md:1259`. `.27` added a `not written whole: <path>` footer line under a failing `Encoder errors:`, but `File(s):` stays the request; fork list F8.
- [x] **Closed 2026-11-25 (audit): duplicate of R160; tracked there.** **E5.** ~~**The `-j` diagnostics record goes nowhere** — lands in the rips root, nothing
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

- [x] **Closed 2026-11-25 (audit): duplicate of R162; tracked there.** **F3. `a_round_is_reviewing_a_build()` answers from pin coincidence, not from the
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
- [x] **Closed 2026-11-25 (audit): duplicate of R166; tracked there.** **G12. The leaving-beta objective has dropped out of our laps** — the rule says it
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

- [x] **Closed 2026-11-25 (audit): duplicate of R160; tracked there.** **Embed the `-j` record in `.platterpus.json`.** *(Retitled 2026-09-30 from
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

- [x] **Closed 2026-11-25 (audit): duplicate of R169; tracked there.** **`mutation:_survivors-20260925`** (ungated, medium) — The nine new legs' first sweep left 77 survivors of 241 checked; read them and kill the real ones
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

- [x] **Closed 2026-11-25 (audit): duplicate of R164; tracked there.** **`fuzz:rip_report.build_report`** (ungated, medium) — The JSON rip report has no never-raises property test over parser output
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
- [x] **Closed 2026-11-25 (audit): duplicate of R197; tracked there.** **Make the run's own bundle the ONE file.** The auto-bundle already exists
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

- [x] **Closed 2026-11-25 (audit): duplicate of R167; tracked there.** **Build D6 C: descriptive preset names, and a separate line for state no preset
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

3. **🟡 Hardware-gated proof queue — HW (user), S each.** *(2026-09-30 audit: the hardware runs this queue waited for have happened — the in-app acceptance run, rounds 26–29 — and the current run sheet is [`docs/rig-session.md`](docs/rig-session.md); `hardware-test-checklist.md` is kept as the full reference. The "Still open" items below were not re-checked one by one.)* Everything only the Bazzite + BDR-209D rig can prove, consolidated. **The run sheet is `hardware-test-checklist.md` (the former `hardware-test-checklist.md`, now [`docs/test-plan.md` → *Hardware test checklist*](docs/test-plan.md))** — as of 2026-07-30 it is *consolidated*: it carries **every** outstanding hardware test rather than only the newest release's, grouped by why each is still open, with stable test IDs that are retired once they pass. Work that sheet first; it, not this bullet, is the live list. **First run done 2026-07-26 (partial):** the log checksum verified end-to-end (test 3 ✅, recomputed independently from the real artifact + tamper detected), force-stop/post-cancel recovery held (test 15 ✅), the wizard's `dnf install /usr/bin/cd-paranoia` provides-install + export **succeeded on a real Fedora container** (previously flagged unverified — now proven), and the real `cd-paranoia -A` output was captured and committed as a fixture (the KDD-29 gate is CLOSED). That run also surfaced **five defects, all fixed** (see CHANGELOG `[Unreleased]`): the 90 s probe timeout, the undiagnosable unknown verdict, "Finished with issues." on a successful cache-only run, the EAC log calling offset-variant tracks absent from AccurateRip, and overread rendering "(unknown)". **Second run done 2026-07-26 (v0.5.9, Overread OFF — a complete 14-track rip):** all eight v0.5.9 fixes confirmed on the rig — the cache probe finishes and reaches both the panel and the log as a measured `Yes`, the wizard reports "Done.", the offset trust line reached **"confirmed — two independent sources agree"** (KDD-31 earned on hardware), overread renders `No`, and offset-variant tracks are described correctly — so **tests 2, 5, 14 are ✅**. **⭐ Test 17 is ANSWERED:** the `.cue` carried 14 × `INDEX 01`, no `PREGAP` — the pre-gap gap is real on the deployed cyanrip 0.9.3, so KDD-32's build-cyanrip-from-source step is now **required** and is the run sheet's final part. That run also surfaced **two new honesty defects, both fixed in v0.5.10**: a re-read track's Test & Copy proof never reached the log, and a track whose re-reads *disagreed* rendered as clean. **Third run done 2026-07-26 (v0.5.10, step 1 only):** the Test & Copy rendering fired but paired the convergence proof with the **first pass's** CRC on both swapped tracks (log `52DFDF7D`/`6902BCF0`; files `3D8FCF0C`/`E0036697`) — the swapped-in read's own record now replaces the first pass's (fixed in v0.5.11, regression-pinned). Both problem tracks converged for the first time (`unresolved: false`). **Still open** — the run sheet's own §A–§E are authoritative and the old flat test numbers below were superseded by them on 2026-07-30; everything *not* on the sheet: the `-Z` convergence re-rip (history item 14); the from-scratch wizard/`setup-host.sh` run + drive-setup success screens + README screenshots + Picard UX (history item 10; test-plan Tests 3/5/6); cyanrip WAV parity (proof matrix below); the new test-plan Tests 12–14; a real in-app uninstall run (history item 4); UX gap #3 (timestamp-localized anomalies — needs real anomaly-bearing output); and a live screen-reader (e.g. Orca) session over the announced surfaces (UX gap #4's last fraction, 2026-07-21). *(The EAC gap-handling check was removed from this queue 2026-07-21 — closed as already-satisfied; cyanrip's default matches EAC, verified upstream, no hardware run needed.)*

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
- **[x] Closed 2026-11-25 (audit): duplicate of the cancelled-rip addendum row E15; tracked there.** The cancelled-rip log addendum, properly.** Their J2 is right that appending after
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

*Last updated for Platterpus v0.7.130.*
