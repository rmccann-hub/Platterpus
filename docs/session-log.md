# Session log

Chronological record of what each Claude Code session built, decided, and learned on Platterpus — **newest first**. This is the project's institutional memory; it was split out of `CLAUDE.md` (2026-06-13) so the always-loaded project context stays lean. It *complements*, does not replace, the durable distillations:

- **Coding standards / critical rules** → [`CLAUDE.md`](../CLAUDE.md)
- **Architectural decisions** → [`PLANNING.md`](../PLANNING.md) (KDD-NN)
- **Engineering patterns & lessons** → [`architecture.md`](architecture.md), [`testing.md`](testing.md)
- **User-facing changes** → [`CHANGELOG.md`](../CHANGELOG.md)

**Graduation rule:** when an entry below carries a *durable* lesson (a coding standard, an architectural invariant, a hard-won gotcha), promote it to the relevant doc above; the entry stays here as the dated record of how it arose.

---

## 2026-11-13 to 2026-11-16 — round 40 closes on `.32`; every open task triaged; the documents consolidated

- **Built.** Released 0.7.125 naming `.32` under review; released our lap 2 on the owner's word. Filed the owner's Full run of 2026-11-14 on 0.7.125 with `.32` (evidence `7faf1b9f`, 239 files, 650 pass, 2 fail on track 5's read before the repair) and read it against round 40's G1 to G3, all met. Named section R's rips without a round (`57de20cb`). Filed the fork's lap 3 (`GO`), wrote and released our lap 4 (`GO`, on the owner's word), and rolled `FORK_PIN` to `edb73dd` with the approval record (#484). Triaged every open row of `TASKS.md` against the tree (39 closed, R157 to R170 added, a new ranked list), audited the documents for present-tense drift, and, on the owner's word (*"Do all 5"*), consolidated: the closed TASKS sections and the session log before 2026-10-16 to `docs/archive/`, the hardware checklist into the test plan, the upstream ask list and the known-issues record into `cyanrip-fork.md`, the manual CTDB repair into `ctdb-crc-algorithm.md`, and rounds 38's and 39's rig sections to the archive. `TASKS.md` went from 9,445 lines to 1,938 and this log from 11,108 to under 400.
- **Decided.** The owner: release lap 4 when ready; triage and audit before the next lap, documentation only; consolidate all five. `docs/rig-session.md` stays one file, by Critical rule #7's wording.
- **Learned.** (1) Our lap 4 said either side may open round 41; protocol §1a says the provider opens. A sent lap stays as written, so the correction went to the status block's LIVE CORRECTIONS and our next lap repeats it; the triage agent caught it, not our lap checker, which reads no NEXT-LAP prose. (2) Git can merge one branch that moved text away with another that edited the same text in place and report no conflict: about a thousand moved lines came back. After merging a move, compare the moved file's line count with the mover's. (3) A count read off a screen listing is not a count (24 `.32` logs for 23): count the filed list. (4) All four background agents stopped together at the account's five-hour limit; each resumed from its own transcript when the limit reset, and a worktree can vanish while an agent waits, so an agent should commit early.

## 2026-11-12 to 2026-11-13 — G5 filed; drive setup tested up front; lap 6 GO

- **Built.** Filed the owner's EAC re-rip of 2026-11-12 beside the June logs, folder hidden at their choice with the original's sha256 recorded (#472, `07cd1d94`); read it: EAC 12 of 14, missing tracks 3 and 5 with values this drive also gave us, so both are wins on this rig (`docs/eac-parity.md` G.7). An audit of every setup and per-disc step against the owner's EAC guide found the read offset was one global value (a second unlisted drive ripped at the first's offset), the cache check waited on a button, and the EAC-compatible log was off by default; three agents fixed them (#473: `2a7c3c43`, `25913a7f`, `bb371569`), and the first-run offer stopped promising an offset auto-detect (`12eedddc`). `lap_turn.py` gained the turn line (`c2cbd54a`). Lap 6, GO, with the round summary (#474). TASKS R148 fixed: the lap checker now refuses an evidence citation without its full commit and SHA-256.
- **Decided.** The owner: test the drive once, up front, per drive; only what depends on the disc runs per disc (`CLAUDE.md`). Every handoff opens with `MY TURN TO SEND` or `MY TURN TO WAIT`, the lap that goes to which repository and the lap expected back (`CLAUDE.md`; the fork adopted it at `cyanrip@bd593350`). Moving CTDB ahead of the transcode was not done: it reverses R133 and risks never making the derived copies. An existing config keeps a saved `false` for the EAC log.
- **Learned.** (1) A container restart stops background agents but keeps their worktrees: uncommitted work survives and an agent can be pointed back at it. (2) A merge of two agents' work can break what neither saw: a size ledger both raised, and a sweep's class pattern that a new mixin no longer matched; the full suite on the merged tree is the check, not either agent's run. (3) A handoff time must be read from `date -u`: one reply this session stamped 00:52 UTC at 00:43 UTC, written from no clock.

## 2026-11-11 to 2026-11-12 — round 39: the five-rip run read, G1 to G4 met; 0.7.123 answers lap 3

- **Built.** Filed the owner's Full run on 0.7.122 with `.31` (evidence `ac0a5133`, 246 files) and read it: G1 to G3 met in all five repeat rips, G4's per-second comparison from its 83 records. Fixed `expect-track-records` grading the report alone (`4ee8871d`). Answered the fork's lap 3: every `-Z` pass asks `.31` for `--reread-until-accuraterip` (`3e841e40`), the exact agreeing count on `.30`/`.31` (`048356b0`), the `C2 errors:` line read as a declaration (`6739f51d`), the probe reads each wrong second whole (`fa2a8f85`). Released lap 2 and 0.7.123.
- **Decided.** The owner: "burn" means writing a disc, on both sides (`CLAUDE.md`, `tests/test_burn_means_writing_a_disc.py`). The C2 probe shows the BDR-209D returns C2 pointers and flags track 5's three wrong samples in every read; its capabilities page says it cannot.
- **Learned.** (1) HR-2 §6b: a lap may cite an evidence file only once its manifest row is on `main`, so the rows and the lap go in two pull requests, and the lap's FROM-COMMIT is where the manifest is read. (2) A runner that hands a grader a file where the grader expects a folder fails silent: the glob finds nothing and the check reads as narrower, never as failing. (3) A borrowed word (burn-in) that means the opposite of the program's job (reading) misleads the owner; say what the drive did.

## 2026-11-06 to 2026-11-11 — round 38 closes on `.30`; 0.7.122 names `.31` for round 39's test burn

- **Built.** The one-script drive test (`docs/rig-scripts/drivetest.sh`, phases, probe, records, uploads that keep no audio), run by the owner on 2026-11-09 and the Full run on 0.7.121 with `.30` on 2026-11-10 (592 pass, 2 fail on track 5's read, which the automatic CTDB repair fixed). The per-track record (G3, `c1d2dcb1`), the verified-read chase (G1, `4cba7e11`..`512e052a`), AccurateRip's own database read for a repaired track (G2, `b2ad84ec`), `.31` read and sent `--reread-until-accuraterip 2` (`d94e1388`..`d970b4c6`), every chase read's record kept for the bundle, and the Full run's section R, five default whole-disc rips. Round 38 closed on our lap 17 and the fork's lap 18 (`5190dc1e`); round 39 lap 2 written and held.
- **Decided.** The owner's word of 2026-11-11 released 0.7.122 with the fork's latest release under test; `.30` is the default, `.31` under review. The reference release is picked by its MusicBrainz id, after the owner reported the picker's order differs.
- **Learned.** (1) A parse limit the project's own acceptance script outgrows cuts off its last section silently; the restore sweep caught it, not the limit (`MAX_LINES` 2000 -> 4000). (2) Opening a file for write before reading it truncated CHANGELOG once; read first. (3) A `cd` into an agent's worktree moves the session's working directory; use absolute paths. (4) `head -3` of `cyanrip --version` read a cold container's start-up lines, not the banner; read all of it.

## 2026-11-05 (day) — 0.7.121 names `.30`; the drive test moves to it

- **Built.** The readers for everything `.30` adds (`other_reads.py`, `record_reads.py`, `record_drive_declared.py`, `record_vendor_settings.py`; PR #458 and this release), the vendor read in the two drive-test scripts, `.30` (`5cc1c6b`) under review, and 0.7.121 (the automatic CTDB repair, the `.30` readers, scripted rips' logs in bundles, the installer's seven-character short hash). Our lap 11 relayed the owner's yes to the vendor read; the fork's lap 12 published `.30` and moved round 38's pin to it on both owners' word.
- **Decided.** The drive test runs on 0.7.121 with `.30`, and its Full run doubles as the release's test (the owner, 2026-11-05). The scripts' vendor read needs `.30`, so they landed with the release naming it, not before.
- **Learned.** (1) Moving `PIN_UNDER_REVIEW` can silently drop the previous build from a set that held it only *as* the pin under review (the `-Y` set; the 2026-08-25 defect); name it explicitly when the pin moves. (2) A shell `sed` on `__version__ = ` missed the annotated `__version__: str = `, and an `&&` chain then skipped every edit after it without a word; check the edit landed before the next step.

## 2026-11-05 (night) — round 38 laps 8 to 10: the drive test agreed

- **Built.** The automatic CTDB repair merged (PR #454, no button, KDD-47); the drive test folded the fork's corrections (PR #455) and their timing refinement; our lap 9 released; the fork's laps 8 and 10 filed and verified (digests reproduced).
- **Decided.** A1 refuted by both sides: track 5 is read six ways and gave the AccurateRip-verified read in three sessions, so a keep-until-verified rule can reach it without repair (their round 39 R1). No lap 11 until the owner's runs exist: a lap only to acknowledge is not sent.
- **Learned.** (1) **`git ls-tree --name-only` quotes a path with non-ASCII characters** (`"…\342\210\266…"`, closing quote and all), so a `grep '\.log$'` over it silently drops those files; our lap 9 S3 undercounted two runs that way, and the fork's lap 10 S2 caught it. List with `-z` or `-c core.quotepath=off`. (2) A count is a claim about its filter: our 10-06 denominator counted `.eac.log` files as cyanrip logs. Say the filter beside the number. (3) Both sides made the same slip in the same week, a placeholder substitution hitting a header key (`HANDSHAKE-ROUND-DIGEST`); our lap checker caught ours, theirs passed theirs, and they now refuse it.

## 2026-11-05 — round 38 lap 7: the run read, a test plan for tracks 3 and 5, Pioneer's documentation

- **Built.** `rig_scripts/drivemode.txt` (twelve rips, early and late) and `rig_scripts/drivespeed.txt` (sixteen rips at the drive's own speed, `-S 4` and `-S 24`); a script run's bundle now carries every scripted rip's folder (`uiscript/scripted_rip_dirs.py`); the installer pins git's short hash at seven characters; the CTDB repair core merged (PR #453). Our round 38 lap 7 (`OPEN`) reads the Full run on `.29`, reports the repair, and proposes the owner's test plan for the fork's agreement before it runs.
- **Decided.** On the owner's words of 2026-11-04: the round stays open until tracks 3 and 5 are resolved (KDD-47); EAC is the gold standard, matching it is success and beating it a win, so track 3 is parity and track 5 a win (`CLAUDE.md`, `docs/eac-parity.md`); a rig run stays unattended and a disc is touched only between runs.
- **Learned.** (1) **Read the vendor's documentation before planning around a vendor feature.** The test plan began with a Windows step to change PureRead; Pioneer's own utility list, the drive's brochure and a published firmware census all said this drive most likely has no PureRead, and Pioneer's help (read as text from the utility's archive, nothing run) named a second setting, *Quiet Mode*'s self-chosen speed, that fits track 3's per-session behaviour better than the one we planned around. (2) **A refusal recorded months ago may describe the tool, not the hardware.** Our 2026-07 note said this drive refuses `-S`; it was cyanrip refusing because the drive does not advertise speed selection, and upstream `0be45a36` (2026-10-10) now tries it. Re-ask the hardware when the tool changes. (3) A protocol's promise checker (A2) caught a lap declaring `OPEN` after promising `GO`; the honest record names the owner's word as the trigger rather than bending the run's conditions to fit.

## 2026-11-04 (late) — CTDB repair built natively (TASKS R43, KDD-14 amended)

- **Built on the owner's word** (*"Start building CTDB repair now? yes"*): the step after the 2026-10-26 localisation, CUETools' `CDRepairFix.Write`, in `ctdb/repair*.py` with `adapters/flac_rewrite.py` and our own `accuraterip_crc.py`. The localisation now keeps each correction's XOR value and each track's audio CRC. The plan refuses a minority or tied entry, an AccurateRip-verified track, a guard band, a pregap, a column past npar/2; the core proves the new file and the whole repaired disc before keeping the original and renaming the new file in. Report schema 44 (`ctdb.repair`). No GUI action or script verb yet (R43 says what remains and why a verb needs an argued exception).
- **Pre-registered for the owner's disc** (R43): track 5 after repair, Copy CRC `C96464AB`, AccurateRip v1 `134C0B9D` / v2 `BCF4E815`; CTDB at offset -7 `5092E94B` (disc) and `1CB564CC` (track 5).
- **Learned.** (1) There was no AccurateRip CRC code of ours to reuse: every AR number came from the ripper's log. A brief that says "use our existing X; grep for it" is a claim to check, and the check found nothing. (2) A repair's guard bands are a real limit, not a formality: damage in CTDB's first or last ~5,880 frames is outside the parity and the CRC, so a repair can "succeed" and leave it (held by `test_damage_in_a_guard_band_is_beyond_ctdb`, and said in every record). (3) The unchanged-file CRC check is what catches an edit inside a guard band: with it reverted, a file changed since the check is repaired and committed, because neither CTDB CRC covers the changed byte (revert probe). (4) CUETools is GPL-2.0-or-later, not LGPL as our modules said (R136; filed as R133 on the build branch, which round 38 had already taken). (5) `metaflac --append` (FLAC 1.4.0+) copies every block whole, and a fresh `flac` encode already holds a VORBIS_COMMENT that `--append` refuses to duplicate, so it must be removed first; measured with FLAC 1.4.3.

## 2026-11-04 — round 38 laps 2 and 4; `.29` under review; 0.7.120

- **Round 38, our side.** Laps 2 and 4 released on the owner's word: the fork's six `.29` wordings read before the build (14ec9bb9), four questions on their exact form, and the owner's directive that each side clear its own task, issue and bug lists (R126, R128, R122's last finding and R123's rig script closed or built). The fork's laps 3 and 5 filed and verified: their digests reproduce, `.29`'s `src/` equals what we read, and their `block_crcs` combine by zlib's `crc32_combine` to each track's `eac_crc`.
- **A defect their lap 3 exposed** (3fe172ad): `.29`'s undecided `Gaps:` row was missed by both our readers of that block; the EAC-layout log would have claimed *Appended to previous track*. The fork found the same hole in two of their own tools after our lap 4 said so.
- **`.29` (`8d2ca72`) named under review** (#446), and **0.7.120 cut** on the owner's word ("Do the next release so we can do a test run") for round 38's Full run.
- **Learned.** A status test that looks for the word "open" passed for a round only because the word appeared inside an unrelated phrase; a check that matches a label must also require the subject (CLAUDE.md, *can it be satisfied by the wrong thing?*). And a sweep that cannot trace a new code shape (`A.match(t) or B.match(t)`) is taught the shape, not given an exemption.

## 2026-11-03 (evening) — round 37 closed; `.28` the default; 0.7.119

- **The owner's four decisions** ("do 1 - 4 as recommended", #438): a CTDB-only disagreement is a note and never "WRONG"; the Tracks table opens with four rows; an unwritable output folder is refused before the rip; the WAV warning names what a WAV keeps, measured through our own transcode. Critical rule 4 amended to match, on the owner's word ("update rule 4", #439).
- **Round 37 closed** when the fork's PR #85 brought their lap 7 (`GO`) to `platterpus-fork` at 19:42 UTC; `FORK_PIN` rolled to `3f288fb` with the approval record at round 37 (#440). The roll would have dropped `.27` from the `--verify-log` set, which a test caught; `.27` is now named in it.
- **0.7.119 cut** on the owner's word ("release 0.7.119"), the first release installing `.28` by default.
- **Learned.** A watch on another repository's pull request is the right wait for a lap released only on that side's branch: under the K1 amendment both sides accepted, a lap is sent when it reaches the default branch, so the branch flip alone is not yet the send.

## 2026-11-03 (later) — the Full run read; lap 6 `GO`; the review's fixes; 0.7.118

- **The owner's Full run on 0.7.117 with `.28`** (02:38 to 05:00 UTC, 553 pass, 0 fail) filed on `evidence` at `1bb98a2c` and graded `full-green`, the ledger's eighth. Filing it found two tool faults of ours: no filed name for the cache probe's own log, and no local test of the manifest's order (CI's `gitleaks` caught it). Both fixed with tests (#434).
- **Our round 37 lap 6, `GO` on `.28`**, released on the owner's word (*"Do 1 and 3"*) and merged at `8aca65d3` (#435). Revised before release on the claude-code-skills session's review: the crossed laps 5's order (theirs reached `platterpus-fork` first, 02:31:06 UTC), the pre-commit's dropped second clause, and a held-lap clause for the K1 amendment, which the fork's lap 7 accepts. The fork's lap 7 is `GO`, and held on their side for the owner's word; round 37 closes when it is released.
- **Seven agents, one integration branch.** R112 to R119 from the run and the review's A to C and E1, E2: one verdict for a contradicted track on every surface, an outvoted CTDB match failing its step, the learned speed surviving a reload, a free-space check before a rip, the shutdown that failed after a logout (not a recursion, as R118 had it: each filter added one frame while Qt finished the close), 1,942 false warnings, the hidden update dialog, and acceptance steps that can now fail on their subjects (the read offset, the derived files, the pre-emphasis pair, planted faults). Recorded in TASKS R112 to R128.
- **The next upstream notes are held** until upstream takes #167's 23 items (the owner); the fork's items 24 to 28 and three candidates are written down in `docs/cyanrip-upstream.md` Part B.
- **0.7.118 cut** on the owner's word (*"Release all when ready"*, *"don't wait for the fork"*), with `.27` the default and `.28` under review.
- **Learned.** (a) A count quoted in a handoff came from memory of reading the files (20 of 20) and the files said 19 of 19: recount from the filing before quoting. (b) A checker that counts `answers:` does not read `re:`; our lap 2 and 4 answers needed naming again in lap 6. (c) Switching branches in the tree a background gate is reading invalidates the gate; run gates in their own worktree. (d) A cherry-pick of a branch's commits in `git log` order, not `git rev-list --reverse` order, conflicts where the branch did not.

## 2026-11-03 — the steward skill; lap 4; #425 merged; `.28` under review; 0.7.117

- **A draft steward skill** (R102): `scripts/pr_steward.py` judges a commit's checks from the ruleset and the API, and the skill says what to do about each verdict. On the owner's word it moved to `.claude/skills/steward/`, the folder sessions look in, as the fork's is.
- **Our round 37 lap 4**, released on the owner's word, accepts the fork's `Drive used:` wording for an image and gives `--reread-time-limit`'s cell. It crossed the fork's lap 4, which released `.28` at `3f288fb` before our answer, on their owner's word. The two laps' round digests agree.
- **#425 merged** (`cfbe39c7`): Python 3.12 floor and numpy 2.5 (R99), the AppImage on Python 3.14 (R100), appimagetool pinned (R98), and the picker hold (R96).
- **`.28` named under review** (R105), and 0.7.117 cut on the owner's word of 2026-11-03. Filing `.28`'s contract found two real faults. A check had been backed by the wrong line, because the renderer skipped `%.*f`. And a "never printed" exclusion would have hidden a message `.28` really prints.
- **Learned.** When a dependency's change trips a check, ask whether the check had been passing on the line that moved. Here it had been, and only the move showed it.
- **0.7.117 published** (02:08 UTC, `104c82d2`, release run 41563982544; PyPI too), and **our lap 5 released** on the owner's word (*"might as well release then"*), on `main` at `2522a1bb`. The owner started the Full run on `.28` at about 02:36 UTC, About box confirming `3f288fb` installed and under test.
- **Open after the day** (TASKS): Overread restored silently after an acceptance run (R106); a worker thread that outlived its test (R107); the reading list for the run, written before the bundle (R108); the native `QLineEdit` hang (R104).
- **Learned, twice.** A merge's expected head was typed from a short SHA and padded by guess, twice; GitHub's 409 caught both. Read it from git. And a local full run was skipped before a push, and CI found the 303-line file: run the gate before pushing, not after.
- **Twenty open rows closed in one PR (#430, `a49873ff`)** on the owner's word (*"fix everything else you can without my input"*): six agents in separate worktrees (reports R60 and R62 to R66; security R86 to R89 and R94; dialogs R96 and R106; tests R104, R107 and speed; dependencies R91, R93, R98 and an audit with no known vulnerability; EAC parity R51 and R59 (b)), merged by cherry-pick here. R109 was found while updating the Full run's description: the drive profile's one writer dropped the learned reading speed on every drive sighting, so estimates used a stale seed. The harness now fails a test an exception reached, which found two product defects at once. R59 (a), which would make an audit pass easier, is held for the owner. TASKS opens with the remaining rows ranked.
- **The fork's lap 5 crossed ours** (both numbered 5, as the laps 4 were). Our lap 6 files it, copies their `seam-commands.md` and accepts their amendment that a lap is sent when it reaches its side's default branch; written and held for the owner's word.
- **Learned from the merge.** Parallel branches collide in four places every time: size caps, TASKS row numbers, CHANGELOG headings and cited SHAs (a cherry-pick rewrites them). Resolve caps to the module's real length with both reasons kept; give each branch its own row-number range up front; rewrite citations from the `cherry picked from` trailers; and run the full gate on the combined tree, because each branch's own tests passed and the combination did not.

## 2026-10-29 to 2026-11-02 — R96 and R97; dependencies carried; CI from 9 minutes to 6; the AppImage builds again

- **R97** (#420): the drive-cache check runs `cd-paranoia -A` in a folder of its own under the app's data folder, keeps its `cdparanoia.log` with the run, and removes the folder; nothing is left in the folder Platterpus was started from.
- **R96, the album picker** (#420): it waits until the main window is the one in use (`ui/hold_for_user.py`, a modal dialog or another visible window of ours counts as busy, the script console excepted), then opens if the disc is the same; one held picker per disc. The other dialogs that open on their own are sorted in TASKS R96, still to do.
- **`main` went red after #420, and it was ours**: the new picker tests left the real window on screen, and a later `callout` test on the same CI worker read its labels. Fixed in the tests, and conftest's leftover check now fails a test that leaves a `QMainWindow` up, not only a dialog (#421).
- **Dependencies carried** (#421): the weekly relock, whose job pushed its branch but could not open a pull request, and Dependabot's #403, four actions, `pypa/gh-action-pypi-publish` 1.14.3 among them. Branches cleaned: the remote holds `main`, `evidence` and the session branch.
- **CI from 9 to 10 minutes to 5.8** (#422, the owner's *"yes, do it"*): the UI conformance matrix, 246 s of one worker's setup, runs once in `ui-conformance` instead of in all four `test` legs; coverage unchanged at 93.27%. The owner made it a required check (15 in all).
- **The AppImage builds again** (#422): python-appimage fetches appimagetool's floating `continuous` release, whose build of 2026-11-01 refuses mode-0700 AppDir folders, so every build from the #420 merge failed. Pinned to 1.9.1 by sha256; proved by a dispatched build and by `main`'s. The modes are TASKS R98.
- **Dependencies brought current** (#424, #425; issue #385): mypy 2.4 and ruff 0.17 (ruff now leaves Markdown alone; it would have edited a byte-exact lap fixture). On the owner's answers of 2026-11-02: Python 3.12 is the floor and numpy is 2.5 (KDD-46, R99), and the AppImage bundles Python 3.14 (R100, built and proved by an AppImage build; a Full run before it ships). PySide6 6.12 with a 3.15 leg is R101. Releases under a week old wait out the cooldown. `release.yml`'s required list, which never gained `ui-conformance`, is now held to CI's matrix by a test.
- **The regex timing test** (R90) confirms a suspect on every one of three attempts, taking the lowest ratio, after it failed #424 on one noisy reading.
- **Round 37 lap 4 written and held**: the fork's lap 3 announced `.28` built and waiting on one answer, `Drive used:` on a disc image; accepted as given, their `seam-commands.md` copied.
- **Learned.** A test that shows a real window must put it away, and the check that catches a leak must cover every kind of top-level window, or the leak fails a stranger. A tool fetched from a floating release gates the build as surely as a pinned one, so it is pinned the same way (Critical rule #11). Measure before answering "can CI be faster": one fixture was most of every leg. mypy 2.3.1's incremental cache twice reported `platterpus.paths` missing locally where a fresh cache and CI did not.

## 2026-10-28 (evening) — the Full run on `.27`; laps 16 to 18; round 36 closed; `.27` approved

- **The owner's Full run on 0.7.114 with `.27`** (03:07 UTC): 553 pass, 0 fail, graded `full-green` and filed on `evidence` at `4e3830ca` (#409). `Recordable:` answers; track 3 right in 2 of 6 on each build.
- **The fork's lap 16 held** on track 9's pregap, unexplained in 21 of 23 `.27` logs. Our reading had said GO from one log; lap 17 corrected that in the full-sentence form, on the owner's approval of `.27` on this run (*"1. approve it"*), and said `GO` (#410). Their lap 18 said `GO` with their track 9 record fixed, and round 36 closed; `FORK_PIN` moved to `5aeefc4`.
- **CTDB localisation on real audio**: the owner's `--ctdb-calibrate` on EAC's FLACs located track 5's 3 samples at 02:24:59, as EAC's log does (R43); its stale "paste this back" line fixed.
- **Recorded for next round:** dialogs stacking behind other windows (R96) and the `cdparanoia.log` the cache check leaves at home (R97).
- **Round 37 opened** by the fork's lap 1, proposing `.28`'s four wordings before building it; our readers and the speed lock (R95) landed (#415), our lap 2 accepted all four, and **0.7.116** shipped them on the owner's word (*"any downside to releasing both? if not, do it"*).
- **0.7.115** on the owner's word of 2026-10-29 (*"then release it and let me know when done"*): the first release that installs `.27` by default.
- **Learned.** Count every log of a run before writing a verdict on it; one log is a sample. A command handed to the owner names the full path of the program and writes to `~/platterpus-rig/`, never to the home folder or the current one.

## 2026-10-27/28 — lap 13; three reviews answered; hashed locks; 0.7.114

- **Our lap 13** answered the fork's lap 12 (track 3's count corrected, log escaping accepted, the 255-byte shortening asked for on the owner's word, a refused `-S` to fall back to the drive's own speed), held, then released on the owner's word of 2026-10-27 (#392, #393).
- **The review of 2026-10-27** (`rmccann-hub/audit-reports`): 37 of its items fixed in #393, the rest answered; actionlint, zizmor and ShellCheck added on the owner's word. Two follow-up checks by the claude-code-skills session followed (#396, #398, #400, #401, #402, #404): every job that publishes, attests or gates installs exact versions from hashed locks; the locks keep a seven-day wait, are regenerated weekly, and are checked and installed on every pull request (`lock-check` and `lock-install`, required since 2026-10-28); Dependabot ignores the pinned tools by name.
- **0.7.114**, on the owner's word of 2026-10-28, names `.27` (`5aeefc4`) as the build under review for tonight's Full run, with the paired `.25` and `.27` rips of track 3.
- **Two CI failures on the way, each fixed rather than re-run, on the owner's word** (*"don't re-run hoping it's noise"*): the regex timing test flagged `_PREEMPHASIS`, whose value is now read with string operations, keeping every result the regex gave (#406); and the UI conformance matrix measured the cyanrip upgrade wizard while its run was still changing the status line, now measured once it has settled (#406). 0.7.114 published at 03:00 UTC from `95691b5b` (release run 40623934958), immutable, attested.
- **The fork's lap 14 and our lap 15** (#407): their S5 found our rip worker does not keep the speed lock for an unknown answer that our lap 13 promised (owed as R95); their S8, S10 to S12 accepted, S9 amended (a diagnostics record that cannot be written keeps exit 0); and, on the owner's word, corrections to a sentence now go back corrected in full, both ways.
- **Learned (the release night).** A wait loop keyed on a field that reads the same before a run starts as after it ends stops at once; wait on the end state itself. And a lap sentence in the future tense about code nobody opened is a claim; the fork read the code and we had not.
- **Learned.** Dependabot's `update-types` ignores never matched a pyproject range, because they work from a current version a range does not have (read in dependabot-core's source, not guessed); the fix is to ignore by name. A lock dated the day it was made breaks the wait it exists to keep. A test that runs a slice of a script cannot see a change wrapped around the slice; run the whole script. And taking one side of a conflict in a generated block can drop a hand-kept line in the same file (`docs/architecture.md` §6.3).

## 2026-10-26 (afternoon and evening) — `.27` under review; the review; a full-green run on 0.7.113; lap 11

- **The fork's lap 10** released `.27` (`5aeefc4`) with `Recordable:` from the drive's own reply and the `Pregap search:` record, explained `.26`'s speed (upstream's media-changed query moved from every sector to once a second; checked at their source, and their 9 ms-a-sector saving re-derived from our logs), and proposed a `-Z` time limit and a `disc image` word. `.27` is our build under review (PR #386, `52190cbb`); our readers of both proposals are built (`a0920866`, `97ee5d3b`); `--prefer-accuraterip-match` goes to `.27`.
- **The claude-code-skills review** (PR #387): the weekly check on claude-code-skills 0.1.21 and uv 0.13.5, proven by a run; the ripper build checks out the full commit and refuses a dirty tree; a `-dirty` build is never kept, offered or installed; the updater refuses an older version, read from the attested source; a disc's CD-TEXT can no longer forge a verdict row in our parse; the EAC-layout log is one line per field; tooltips and the update dialog render plain text; a year of `..` cannot write above the library; server answers are coerced, capped and host-checked.
- **The owner's Full run of 0.7.113 with `.26` under review** (12:12 UTC): 553 pass, 0 fail, the fifth `full-green` ledger row, all on one drive and one distro; derived files verified on hardware for the first time. Paired track 3 rips: `.25` right in 1 of 4, `.26` in 0 of 4, no cause named. Filed on `evidence` at `a3503739`; the four 0.7.112 runs entered as `partial`.
- **Our lap 11** released on the owner's word: `.27` under review, the run read, and the `.27` Full run's need for 0.7.114, which waits on the owner.
- **Learned.** Two CodeQL alerts in a week came from tests checking a host as a substring; both now parse the host as the adapter does. And a HANDOFF time was written from no clock a second time, the same day the rule to read `date -u` was added; the rule is right and was not followed, so each time is now read in the same command that precedes the reply.

## 2026-10-25/26 — the four Full runs read; the EAC parity plan of record; 0.7.113

- **The runs.** The owner's four Full runs of 0.7.112 with `.26` (2026-10-21 and 22) are filed on `evidence` at `ab3b1395`, `08de9851`, `fc48882f` and `6b31795c` (PR #380, 308 manifest rows); the filing tool learned the P5 folder names, loose files from a rip that never finished, and the verified-read chase's record (each embedded log verified, the lines between redacted; the export redacted around them too).
- **What they showed of `.26`:** the disc ISRC read works (14 of 14 equal EAC's cue); it reads about 3 to 5 times faster; `Recordable:` never answers (libcdio's placeholder) and track 9's pregap never reads EAC's 94. The fork's lap 8 read it the same way, and the owner's word takes round 36 to `.27` with both fixed, then a Full run of the reference disc with paired `.25`/`.26` rips of track 3.
- **Ours, fixed** (PRs #381, #382): a stopped securing pass threw away a verified re-read; the derived-file check gave up after 60 s; the bundle was packed before the checks finished; the audit counted a replaced read's errors; the cue ISRC check ignored `--prefer-disc-isrc`; a one-reading drive blip cleared the release (57 failed steps); the graders read the window, not the rip's record; the cover-art grade raced its result; `rescan`/`pick-release`/`rip` raced each other.
- **The plan of record** (the claude-code-skills session, 2026-10-26) set the yardstick and 34 regards against EAC; its documentation is `docs/eac-parity.md` Part F and TASKS R49 to R66. Built from it: a wrong track is called wrong (no "Copy OK" over an AccurateRip contradiction), a `Proof:` line per track, CTDB localisation (`differs in N samples @…`, numpy on the owner's word, +13.8 MB estimated in the AppImage), and section P6.
- **Read before they ship:** `.27`'s `Kept read began:`, `not written whole:`, `Pregap search:`, `read with no error reported.` and the `/11` record; `--prefer-accuraterip-match` gated on a build set that is empty until `.27`'s release.
- **Released:** 0.7.113, on the owner's word of 2026-10-26; `.25` stays the default.
- **Learned.** A HANDOFF time written from no clock was four and a half hours off; read `date -u` first (graduated to CLAUDE.md, *Times*). Parallel agents told to number rows "after the last" all took the same numbers (graduated to `docs/architecture.md` §6.3). A test that arms a timer before the step it times passes alone and fails under load: trigger the late event from inside the thing being waited on. And a lap draft claimed the timed rips ran `.25` first; the script alternates them, which the logs confirm, so the draft was read against the script before it was sent.

## 2026-10-21 (small hours) — the known fixes; 0.7.111 and 0.7.112; `.26` under review; lap 3

- **The owner's direction:** *"we need to reach EAC parity or better (better please). and fix know problems and open issues."* The claude-code-skills session ranked the known fixes; eight agents built them in parallel, each integrated by cherry-pick onto `main` (PR #375, `43fb0a16`): R7 (keep a read AccurateRip verifies over a rejected majority, `022c1cb6`), R43 (CTDB per track and over ±5879 offsets, `a5e11284`, `819435d8`), R44 (error positions, `bfedfee7`), R13 (a data track is not a failed one, `08860fae`), items 3 and 12 (verdict honesty, `3581d9e3`), item 5 (gates from results, `d27b2401`), item 11 (the read offset checked against the drive list, `2f902dc5`), and the timed `.25`-vs-`.26` section (`62f321eb`). Item 20, the MP3 ReplayGain, by hand (`1e2bf78f`).
- **Released:** 0.7.111 at 04:50 UTC from `cb82d620` (the second read in users' hands, `.25` by default), on the skills note to ship it before `.26`; lap 2 released on the standing word. The fork released `.26` at `ca0f097` with its lap 4; `.26` is under review (`8db6e666`). Our lap 3 written, held for its PR. 0.7.112 names `.26`.
- **Not built:** CTDB sample localisation needs `numpy` or a native extension, asked of the owner.
- **Learned.** A cherry-pick of a branch cut before a release puts its changelog bullet inside the released section with no conflict; compare the released section with its tag after integrating (graduated to `docs/architecture.md` §6.3). And merges of parallel branches double the size ledger's keys silently; merge each key to one entry at its real count.

## 2026-10-21 (night) — round 36 opens; the reader for `.26`, held lap 2

- **The fork opened round 36** with lap 1 (`cyanrip@088557c`): `.26` carries upstream's `7dbe56a` and three new log lines, and is released once our reader takes them. Our reader takes them (`7a3817a3`, verified word for word against their source), and our lap 2 accepts the wordings and their timed-rip design and names 0.7.111 as the release that reads them. It is held: round 36 has no standing word yet.
- **Our checker refused their lap at first** for "no close condition": it matched the phrase, and they wrote the condition as an LSL `TERM set`. Fixed (`e7b8ab0d`).
- **The owner's word:** *"Yes: once .26 is released, move round 36's pin to .26."*
- **A container restart** dropped the virtual environment, the fork clone and one background agent; each was rebuilt. Three UI measurement tests fail under this container's default font and pass on CI's.
- **Learned.** A checker that reads a structured document by keyword fails the first time the author states the same thing in the structure instead. Match the structure where one exists.

## 2026-10-20 (evening) — the orphaned EAC audit branch taken over and its review applied

- **The branch.** `ccr-3c66e173-5708ow` (one docs commit, `69641172`, Part E of `docs/eac-parity.md`) had no pull request and no longer merged (P7 of the claude-code-skills check of the audit). Taken over as `eac-audit-takeover`: `main` merged in with a merge commit, not a rebase, so `69641172` stays the commit the check cites. Its TASKS rows R32 to R34 collided with `main`'s and are now R42 (disc wear, one fresh EAC rip), R43 (CTDB depth) and R44 (error positions); `main`'s R34 points at R43.
- **The review applied.** P3: E1 and E5 said our log "refuses" `Copy OK` and `No errors occurred` over unverified tracks; `round32fullwholedisceac.log:123-125` and `:253` print both, so the claim is narrowed to where re-reads disagree. P5: re-derived over all 26 rips, rounds 33 and 34 fetched by hash into a scratch bare repository (evidence commits `f57cdc2b`, `fe13de0c`, the round-33 export's SHA-256 matching its manifest row): track 9's pre-gap is EAC's `1.25` in 23 and `1.26` in 3, and a `1.26` rip's cue puts `INDEX 00` one frame early. Noted in R10 (the fork's `subchannel-pregap-varies`), not a new row. P6: `tests/test_fork_rip_eac_parity.py`'s docstrings no longer say it closes the parity question. P8: the oct06 rip's time is given in UTC with the export's own stamp, EAC's session times are marked as zoneless, and E2 quotes the whole 06-25 CTDB row for track 5, whose `(2/1443) Accurately ripped` half is the evidence for R34.
- **Part E caught up with `main`.** E1, E3, E4 and E7 now say the second read is built (R38, next release) and decided from the lookup's own answer (`accuraterip_standing.py`); E5's CTDB row records the minority-match fix (R34, 0.7.110) and its cite moved with the code (`ctdb/verify.py:286-292`). The grades as first written stay visible beside the new ones.
- **Checked, not taken on trust.** The check's citations held where opened: the CTDB submission at `EAC_flac/…log:258` sits under the `CUETools DB Plugin` header (`:255`), not the AcoustID one above it (`:248-252`).
- **Learned.** A takeover of someone else's branch is two jobs: making it merge, and making it true against the `main` it merges into. The second is where the work was: four of Part E's grades had been overtaken by `main` within a day.

## 2026-10-20 (evening) — round 35 closes; the release word, and fixes first

- **The fork's lap 17 (`GO`) and our lap 18 (`GO`) close round 35.** Lap 17 also found a second defect of ours: the acceptance runner took `(no read exceeded 10s)` from a refused rip's summary as the build tag, so the deemphasis rip sent no `--consumer`. Fixed (`813ecfd4`). `FORK_PIN` rolls to `5f1d036` with the approval record (round 35, 0.7.110).
- **Two PRs, not one.** HR-2 §6b reads the manifest at a lap's FROM-COMMIT, and a FROM-COMMIT must be on `main` for the fork to fetch it. The run's manifest rows were on the session branch, so PR #369 merged first (`bccf8d7a`) and lap 18 names that merge.
- **The owner's word for the next release** (*"i can't do number 3 of waiting for me for a little bit, but do 1, and 2 do it as part of a full acceptance test, at least as long as we need to. proceed"*), and then: *"we need to get as many fixes and improvements into the next releases so we can actually do a proper full acceptance test for as much as possible."* So 0.7.111 waits for a batch of fixes and, if it is out, `.26`. Written into `CLAUDE.md`'s hold line.
- **Learned.** A lap that cites evidence filed in the same pull request cannot pass its own checker: file the rows, merge, then write the lap. Order the work that way from the start.

## 2026-10-20 (afternoon) — round 35's Full run filed, and one writer for lap 17

- **The run, on 0.7.110 with `.25`, is filed** on our evidence branch at `374826695ec2233ae685be7f797d75e6aa326db5` and graded `partial` (TASKS R39): 434 pass, one ARCHIVAL failure that was ours. P2 expected exit 1 from a refused flag; `.25` exits 64, as both sides agreed, so the script now asks the build which code a refusal exits with.
- **Two more fixes from the bundle.** A CTDB no-match now carries its entries' weights. The export's redaction left the owner's username in the setup log held inside a JSON string, because `\n` puts a word character right before `/home/<name>`; every name boundary now treats an escape as a start. Caught at filing and replaced before the evidence commit was pushed.
- **Lap 17 is the fork's.** The operator saw both sessions starting a lap 17 and asked for one decision, not a race. Both status blocks already named the fork as lap 17's writer; each also said "or the other side first", which was the race. Ours now says only the fork writes 17, and ours is 18. The fork's operator relay confirmed the same.
- **Learned.** "Claimed at release" (K1) settles a collision after it happens; it does not prevent two sessions doing the work. When both status blocks say "or yours first", neither has said who. Name one writer.

## 2026-10-20 (morning) — the second read by default, and the hourly check stopped

- **The owner's answer to P2: *"yes, read twice by default"*.** It came through the claude-code-skills session at 9:14 AM EDT (13:14 UTC). Built the same morning as TASKS R38: a disc AccurateRip can't vouch for is read twice, with the named "Reads agree" verdict and an opt-out. Not released: the hold in `CLAUDE.md` still stands, and round 35's Full run, on 0.7.110 with `.25`, is unaffected.
- **Found while building it.** The report suggested using each track's `accuraterip_lookup`, but cyanrip writes `not found` on that row both when the lookup failed and when the disc is not in the database (`cyanrip@3861b266:src/cyanrip_log.c:669-671`). Only the disc-level `AccurateRip:` line separates them, and our parser had skipped it on purpose since round 28. It is read now. A second finding: a disc in the database whose every track failed was being skipped as "not in AccurateRip", because "no track matched" was the only test.
- **The hourly handshake Routine is off** on the owner's word, *"stop the hourly check"*. It is disabled, not deleted.
- **Learned.** A field named after a question does not always answer it. `accuraterip_lookup` holds the lookup's per-track row, which cannot tell "the database has nothing" from "we never heard back", so read the row's source before building on it.

## 2026-10-20 — 0.7.110 out for the Full run on `.25`

- **Released.** 0.7.110 at 00:22 UTC (8:22 PM EDT on 10-19) from `e4b0115d`, on the owner's word *"When you are both ready do a new release"*, with `.25` (`5f1d036`) under review. PR #366 carried P1, P4, the weekly dependency workflow, the move to `.25` and our round 35 lap 16; merging it released the lap. The full check found one more thing before the merge: the size ratchet, because keeping `.24`'s wordings and its verify-log entry beside `.25` grew two files. Both numbers were raised with the reason beside each (`dd0d7430`).
- **Learned.** A release built against the build under review has to be re-read against the fork's newest lap just before merging. 0.7.110 was first built against `.24`, and only reading their lap 15 showed the round had moved to `.25`.

## 2026-10-19 (evening) — 0.7.109 out, the sessions to read each other directly, and CTDB's minority match

- **Talking without the operator in the middle.** The owner's word, relayed by the claude-code-skills session: *"make it so they will talk to each other about this in the next round/lap. We need them to communicate without us in the middle."* This session now has an hourly Routine (`trig_01EPieBQES8fMQkPqKutjn8Z`, at 14 minutes past) that reads the fork's `platterpus-fork` and answers a released lap addressed to us under the standing word; the HANDOFF block stays as the operator's copy. Our lap 16 accepts the rule once the fork's lap 15 proposes it.
- **CTDB's green over a minority entry (P1, TASKS R34).** 8 of 26 reference-disc rips showed "CTDB: verified ✓ (confidence 1)": the matched entry had one submission, the strongest about 1,405, and each rip had a track AccurateRip rejected. A match now records the strongest entry's confidence and the total; an outvoted match is not `trustworthy`, its line says "matched 1 of N submissions; K disagree", and a match beside a track AccurateRip rejected is amber (report schema 38). The 2026-07-28 entry's "independent whole-disc corroboration" is corrected in place.
- **Round 35 moved to `.25`, and 0.7.110 reviews it.** The fork's lap 15 (7:30 PM EDT, 23:30 UTC) moved the round's pin from `.24` to `.25` (`5f1d036`) on the operator's override of R4 and the run with it; 0.7.110 had been built against `.24` and was caught before merging by reading that lap. `PIN_UNDER_REVIEW` moved, `.25`'s contract filed and the inventory regenerated; our lap 16 accepts the direct-reading rule and the fork's time format (both now in `CLAUDE.md`).
- **Learned.** A database match is evidence in proportion to the weight behind the entry and the independence of whoever submitted it; a count of one, from the same drive and disc, is our own read echoed back.

## 2026-10-19 (late afternoon) — an independent audit against EAC

**Asked:** a complete third-party audit of Platterpus against EAC, better or worse with reasons
and evidence. **Built:** `docs/eac-parity.md` Part E, two inline corrections to Part A, TASKS
rows R42 to R44 (first numbered R32 to R34 on the branch; renumbered when it merged `main`, which had taken those numbers), and a measured note on the *First-rip proof* item. No code changed.

**Method, so the numbers can be re-derived.** The 262 `.log` files under
`docs/handshake/artifactsround26/` to `artifactsround34/` were fetched blobless into a
separate bare repository (evidence commits `c737fb6b`, `f57cdc2b`, `fe13de0c`). Each
14-track EAC-layout export (`*eac.log`, plus `output_reference/cyanrip_fork_flac/`) was
split at `^Track N$`, and its `Copy CRC` and AccurateRip line were read per track: 26
rips. First-pass values came from each raw `*wholedisc.log` (`EAC CRC32:`, `Paranoia
status counts:`, `Ripping errors:`). EAC's three sessions were read the same way from
`output_reference/EAC_*/` (UTF-16). Every Part A TL;DR number re-derived exactly.

**Learned.** (1) EAC's own logs disagree with each other on this disc. Two of its three
sessions misread track 3, and two of its wrong values match values our ripper read, so
comparing against one EAC session overstated what EAC achieves. (2) The exports show
what *shipped*, after the securing pass. The raw first pass is much worse on track 3:
1 of 12 right, all with `Ripping errors: 0`. That is the evidence for the gap the
maintainer named on 2026-07-30: a disc AccurateRip does not know gets one read.
(3) The four audit helpers stopped on the session's usage limit; the audit was finished
by hand from their partial evidence fetch.

## 2026-10-19 (afternoon) — the fork's lap 12, the operator's review, and stock cyanrip's argv

- **The fork's lap 12** (released at `cyanrip@820c0c55`, 2:46 pm New York time, EDT) is filed byte for byte (sha256 `773d1133…`) and passes `--check`. Their round digest `c04e79ac0268a00c` over 11 reproduces, and their S3, that our lap 11 counted 7 `CRIP_EXIT_IOERR` lines where there are 8, is right (re-derived from their source). Our lap 11 is now pinned as sent, with lap 12's INBOUND-HELD as the evidence.
- **Our lap 13 answers it**, with their `seam-commands.md` copied (sha256 `d4dcd5ec…`), their count taken, and our lap 11's ruff version corrected (0.15.8 is a stray copy on PATH; the gate runs 0.15.22). The operator's review (item 5) asks for no lap before the run unless it changes what a side does; I first held this one, and our two shared-file checks failed: a copy of a jointly owned file must travel with the lap that declares its hash, so it went.
- **The review's item 1, fixed (TASKS R30):** `--diagnostics` went to every ripper build, and stock cyanrip refuses any long option, so an install left on stock cyanrip could not rip. It now goes to a build whose banner names the fork, or whose banner was not read; held by `tests/test_stock_build_argv.py`, revert-probed on both routes. Not yet shown against a real stock binary, which this container lacks.
- **Item 7:** the PyPI publish ran on `ubuntu-latest`, which moves to Ubuntu 26 from today; pinned, and a test refuses a moving runner label. **Item 2:** R29 said upstream issue 167 had a reply we could not read; it has none. **Item 3:** the size of `CLAUDE.md`, `TASKS.md` and `CHANGELOG.md` is R32, after the round. **Item 4** (the release hold) is the operator's.
- **0.7.109 released** at 6:52 pm New York time (EDT), 22:52 GMT, on the operator's word, from `fe557e80`, after two tests that failed `main`'s CI on one Python version each were fixed (a thread-order assumption, PR #362; a test writing into our own handshake folder under xdist, PR #364). Our lap 14 tells the fork.
- **Learned.** Our status-block test allowed only our version and the next release as the one a run goes through, so it could not state the true case of a run on the release before a staged bump; it now allows the newest released version, which its frozen-script check already guarded.

## 2026-10-19 — prompts attached to the window, a documentation audit, and round 35 lap 8

- **Prompts.** The operator asked that no prompt open as a window of its own. The album picker was already parented; the crash dialog was not, and is now. `tests/test_dialogs_have_a_parent.py` refuses a parentless dialog anywhere in the package (PR #357).
- **Open rows done:** D2 (five `disallow_any_generics` opt-outs retired; typing found the report dropping `retried_tracks[].trigger` since v0.6.19, schema v36, and `rip_compare` raising on a non-list `tracks`), R22 (`quickcheck`), R26 (`Beyond disc:` parsed, schema v37), R28 (a ratchet on whole-repo `rglob` walks).
- **Documentation audit.** Four read-only auditors checked every document against the code, the fork's source and git, and corrected what was stale; findings outside their scope were fixed by hand, including `police-rerip.txt`'s probe steps, which carried no `-I` and would have ripped the whole disc, and the harness missing one of the window's eight threads. One probable code defect is recorded, not fixed: a stock cyanrip would refuse every rip on `--diagnostics` (TASKS R30).
- **Round 35 lap 8** answers the fork's lap 7: their `seam-commands.md` copied, the §1b reasons, the four decisions, the exit codes.
- **Learned.** Seven full suites at once on four cores push `test_ui_conformance.py` past its five-minute limit, so parallel helpers should run only their targeted tests and the integrator runs the suite once. And a session's model allowance can run out mid-work: helpers stopped by it resume from their transcript with a message, and their uncommitted work survives in the worktree.

## 2026-10-17 — round 35 lap 6, and 0.7.109 reads `.25`'s refused-code line

**Asked:** file the fork's laps 3 to 5, answer their lap 4 S6 and lap 5 S8 and S13 in lap 6,
copy their `seam-commands.md` line 112, and release a parser for `Disc ISRC: <code>
(<reason>)` before they cut `.25`. Their lap 3 asked for a shorter run and our view of it.

**Built:** the parser's fourth shape (`not_used`); an as-written ISO 3901 check, equal to the
fork's by a property test against a port of their C; the consumer contract's flag list taken
over both builds we may drive, which exposed a flag it had omitted; one shared walker for
every whole-repository test walk; `overreadprobe`'s lead-in step and the `isrcdisc` script;
0.7.109 committed and held for the operator's word; lap 6 held for its pull request.

**Decided:** the shorter run is Standard plus the two scripts, enough to close round 35 on
the operator's override of R1, not a full-green ledger row and not round 36's opening run.
Release 0.7.109 waits for the operator's word, since this message relayed the fork's request
rather than asking for a release.

**Learned:** a document derived from "a maximal parameter set" is maximal only over the
inputs it was given; ours took one build tag and so could not see a flag gated on another.
This is `CLAUDE.md`'s "is the population I measured closed?" (`docs/testing.md` §5.ao)
arriving through a capability gate, so it graduates no new rule; the emitter now iterates
the builds it can drive, and a test holds the option in the list. And a value written from
memory of a prefix is a fabricated value: lap 6's draft carried lap 5's hash with the first
16 characters right and the rest invented, caught only because the checker compared it.
The rule that applies is "answering from the artifact, not from memory of it" (`CLAUDE.md`);
every hash in a lap is pasted from a command's output.

## 2026-10-16 (late) — round 35 lap 2, and 0.7.108 reads the disc's ISRC

**Asked:** answer the fork's round 35 lap 1 (S13 to S15), make the release that parses
`Disc ISRC:` and sends `--prefer-disc-isrc`, propose the option's `seam-commands.md` row,
put the run's checklist in the release's announcement, and give a by-hand command for the
one bounded `-O` read that cannot be run without its time limit.

**Built:** the parser for the line's three shapes, the `Disc ISRC` setting (default on) and
the option sent through the argv chokepoint only to a build tag whose contract lists it; the
report's ISRC block now records what we passed and whether the option went; the Full run
sends it in F and not in J2; `overreadprobe`, a packaged rig script whose `-O` step stops
unless the ripper is `.24` and the offset +667 and runs under the `cyanrip` step's fixed
limit; `(lasttrack)`, a script token. Lap 2 held for its pull request; 0.7.108 committed.

**Decided:** S13 (a) and (b) accepted, (c) asked of the fork's release after `.24`, because
only cyanrip can choose before the files are written and the round's pin does not move; our
report's `isrc_disc_malformed` keeps a malformed winner visible meanwhile. The `-O` read is
not a Full-run section: a first draft added one, and the operator's word moved it to a
script run by hand.

**Learned:** under an option that replaces a value, comparing the disc's code with the
files' compares the option with itself, so it always agrees; the comparison has to be with
what we asked for. This is the existing question "what else writes to the field I'm
reading" (`docs/testing.md` §5.aq) arriving through a new writer, so it graduates no new
rule; `test_under_the_option_the_disc_is_still_compared_with_musicbrainz` holds it.

## 2026-10-16 (evening) — round 35 kickoff: the disc's ISRC reaches the report

**Asked:** start round 35 by asking the fork which open items need both of us, and start
on the most important or easiest. Round 35 opens with the fork's lap 1 (the repository that
produces the build opens), so the ask travels in our standing status block and the handoff,
not in a lap of ours.

**Built:** R20's half that needs nothing from the fork. `.23` already writes each track's
`isrc_written` and `isrc_disc` into the `-j` record, and nothing read them. New
`isrc_provenance.py` (pure, never raises, tri-state) reads them on the worker beside
`ripper_ending`, and the report's `disc.isrc_provenance` (schema 35) states both per track,
ISO 3901 well-formedness, and the comparison; `isrc_disc_differs` / `isrc_disc_malformed`
are info issues naming both values.

**Learned, from the round 34 records rather than the contract:** a limited pass (`-l`, the
securing pass, a cancel) lists every track, and the unripped ones carry `isrc_written: null`
with reason `not read`. Read naively that is "MusicBrainz gave no ISRC", so `audio_ripped`
is read too and those tracks say `not_ripped`. A `cyanrip-diagnostics/7` record has no ISRC
fields, so its tracks say `not_determined`, never `neither`. Every whole-disc record of the
2026-10-16 run reads `written_only` with `libcdio returned none`: the reference disc carries
no sub-channel ISRC on that drive, so the `differ` path has never been exercised by hardware.

**Status block:** `rip-identity` and `securing-record-kept` retired (shipped in 0.7.105),
`j-record-fields` retired (released in `.23`, and now read); the rest moved to round 35, our
halves of the fork's `subchannel-pregap-varies` and `exit-classes` added, and
`isrc-disc-preferred` names the fork's pull request #31 (`cyanrip@dd60143`: the log line
`Disc ISRC:` and `--prefer-disc-isrc`), which the operator's round 35 message pointed to.
That message also put R18, R17, R14 and R16 into round 35, in that order.

**Then all four landed, in the operator's order** (each with revert probes, all detected):
R18 the doc-sweep walker survives a directory vanishing mid-walk (`os.walk`, caches pruned);
R17 the ledger grades 2026-10-16 `full-green` and 2026-10-14 `partial` (K2's cover-art
check blocked by the Cover Art Archive's HTTP 500 is an ARCHIVAL step that never ran,
unlike E2, which this rig can never reach), and the ledger-count check now reads
"twenty-one" instead of skipping it; R14 the app log collapses each run of progress
redraws to first, a 10 s checkpoint and last, with every other redraw counted (the
newest 2026-10-16 app log replays from 5.9 MB to about 0.3 MB); R16 the filing tool and
the export replace hostnames and names by the fork's rules, counted, with a FUN512 port.
**Learned:** a probe found two tests that could not fail (the final flush of a run, and
FUN512's index, which every signed log in the tree has at 0), each fixed with a test that
reaches it. And the ETA strip on progress lines also removed their error count, which is
why the app log now keeps redraws as the ripper wrote them.

## 2026-10-16 (later) — round 34 closes; `FORK_PIN` to `.23`; 0.7.107

**What was done.** Our lap 2 was released on the operator's word ("release lap 2"), after the
fork's own checker read it well formed against a clone of our `main` alone. Their lap 3 (`GO`,
`cyanrip@68f56fa`) was filed and our gate reads round 34 CLOSED. `FORK_PIN` rolled to
`891c79e` with the approval record for `.23` with 0.7.106. The operator's word of 2026-10-16
releases 0.7.107, the first that installs `.23` by default, while the fork moves `.23` to its
stable channel. The disc-ISRC preference is planned for round 35 (TASKS R20).

**Released.** PR #350 merged as `a657b698`; `main`'s own CI passed on it; `release.yml`
(run 38943509534) published v0.7.107 at 2026-10-16T17:59:10Z as an immutable pre-release with
all six assets.

**Learned.** Their lap 3 corrected our lap 2 twice, and both corrections held against the
filed logs: the log's `ISRC:` lines are what our app passed, and track 5 needed 3 reads. Both
were readings of a log line's meaning that the line itself does not state; a line that does
not say where its value came from invites exactly this.

## 2026-10-16 — round 34's Full run filed; the fork's lap 1 filed; our lap 2, GO, held

**What was done.** The operator's Full run on 0.7.106 with `.23` (426 pass, 0 fail, 1
unreachable) was analysed and filed: evidence commit `fe13de0c` (parent `f57cdc2b`, 80
files), manifest rows in PR #346 (`97b1d7ab`). The fork's round 34 lap 1 (`cyanrip@fa8e7e4`)
was filed byte for byte and passes both our checkers; our gate counts round 34. Our lap 2
reads the run, cites its whole-disc and secure re-read logs on `evidence`, and declares `GO`.

**Learned.** (1) `docs/evidence-manifest.tsv` is sorted as a whole: new rows are merged into
place in byte order, not appended, and a locale sort puts `README.md` in the wrong place; the
`format` check caught both. (2) A tamper probe must change a byte the check covers: the first
probe searched for a word the EAC-style log does not contain and so flipped the file's last
byte, and the check passed it. Flipping a byte in the middle was refused. (3) Track 3 of the
reference disc never converges and matches AccurateRip on one frame only on `.22` and `.23`
alike, so it is the disc.

Entries dated before 2026-10-16 are in [`archive/session-log-to-2026-10-15.md`](archive/session-log-to-2026-10-15.md), moved there unchanged on 2026-11-16.

---

*Last updated for Platterpus v0.7.125.*
