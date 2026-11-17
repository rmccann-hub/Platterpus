# Platterpus and the cyanrip fork: state on 2026-11-03

Read-only review. Nothing was changed in either repository. All times are UTC.

- Platterpus: `/home/user/rmccann-hub/platterpus`, head `origin/main` `75915aa9` (merge of PR #433, 04:31Z).
- Fork: `/home/user/rmccann-hub/cyanrip`, head `origin/platterpus-fork` `239adda` (merge of PR #82, 04:05Z).
- The tested pair: Platterpus 0.7.117 (tag `v0.7.117`, `104c82d2`, tagged 02:07:57Z) with fork `.28` (`3f288fb`, `0.9.4-rc3+platterpus.28`, release_seq 39). The approved pin is `.27` (`5aeefc4`).
- Neither repository holds any record of the Full run that just finished yet. Both `evidence` branches end on 2026-10-29 runs of `.27`.

---

## 1. What changed since the tested commits

### Platterpus: `104c82d..origin/main` has 56 commits (50 changes and 6 merges, PRs #427 to #433)

**Handshake**
- `c13cbfd2`: wrote lap 5 and held it. `04d37447` (02:33:31Z): released lap 5, which reached `main` at `2522a1bb` (PR #428, 02:39:52Z).
- `92ba640c`: filed the fork's lap 5 and copied the fork's `docs/seam-commands.md` at `b99b286` (sha256 `407439e2…`). All four shared documents are now byte-identical in both trees. I checked this.
- `0b7d9ae1`: wrote lap 6 and held it for the owner's word (`HANDSHAKE-READY-TO-READ: no`).
- `a7484cfb` and `7f8b6759`: steward tooling. A running check that nothing requires now keeps the steward PENDING.

**Acceptance test** (`src/platterpus/rig_scripts/fullacceptance.txt` and the `uiscript/` verbs)
- `7af6c680` (R60): section P4 (`expect-pregaps-agree`) moved after P6, so it now compares the logs that P5 and P6 make. **The run on 0.7.117 used the old order, so its P4 never saw P5's or P6's logs.**
- `ffb812ca` (R106): restored settings are now logged with their values, and the log warns when Overread comes back on. 0.7.117 logs the names only. TASKS R108 item (7) expects the line anyway.
- `c410fc96`: the header comment now gives typical times (about 3 hours when P5 and P6 run) and makes *Choose a build…* the first install route. It also adds a note on settings being restored afterwards and a note on section O's `-f`.
- `uiscript/applog_verbs.py`: `CANCEL_MARK` changed from `"rip cancel requested by the user"` to `"rip cancel requested by"` (R62). Grading of cancel lines changes with it.
- `runner.py` and `run_estimate.py`: the estimate skips N/A sections (P5 and P6 when the two builds are one). `artifact_grading.py` and `timing_verbs.py` now use `STATE_WORDS` (R66). Cancel causes are recorded by script step or time limit.

**Ripping, reports and the EAC-layout log.** The cyanrip argv is unchanged: `cyanrip_backend.py` is not in the diff.
- `53c22cfa` and `1f64a39d` (R109, R63): the drive's learned speed is no longer dropped, and tracks with paranoia skips are left out of the speed estimate.
- `7cf88286` (R64): the securing pass records both exit statuses.
- `0eba0eee` (R65): a pass with skips is never called clean, and the unconverged tracks of a stopped pass are flagged (`rip_worker.py`).
- `6d22d55a` (R66): the last read of a loop that hit its limit is counted, and frame 450 is worded.
- `4e6a5e07` and `4f69378d` (R62): reports say who cancelled.
- `ff5974bc` (R59 (b)): the health line describes the reads that were kept.
- `257cf786` (R51): the proof rows name CTDB.
- `2ee03e6a` (R86): the parser sets aside disc-header rows forged by an echoed value.

**UI**
- `828b0999`, `7958ad1a`, `0f8f559b` (R96): the offers wait until the main window is in use.
- `647b61fa` (R87): text from outside the app is shown as plain text.
- `ea6efccc`: the MusicBrainz adapter names its server and https itself.

**CI, dependencies and security**
- `17dc8f53` (R94): publish runs only on `release.yml`'s own tag.
- `f4dbe542`: actionlint is fetched by sha256, and cyclonedx is pinned.
- `1ff90903` (R93): the relock job dispatches CI.
- `7187ef8f` (R98): the AppDir is chmod'ed before packing.
- `81a91ee5`: the quadratic `HOST_FIELD` regex is fixed.
- `f42eb50d`: setup-uv moves to v10.3.2.
- `e69dd127` (R110): dependency audit, with no known vulnerability.

**Tests:** `4502594c` makes a test fail when an exception or a leftover worker reaches it, `8f966ff6` fixes R104, and `01ac9b9d` speeds things up.

**Version:** `src/platterpus/__init__.py` still says `0.7.117` (`git describe` gives `v0.7.117-56-g75915aa9`).

### Fork: `3f288fb..origin/platterpus-fork` has 32 commits (28 changes and 4 merges, PRs #79 to #82)

- **Release:** `8a9a21d` published `.28` at `3f288fb` on beta (ledger row 39).
- **Handshake:**
  - `0f42363` lap 4 (`.28` released before Platterpus answered S9).
  - `b2b669f` filed Platterpus's lap 4.
  - `b99b286` landed Platterpus's `--reread-time-limit` PP cell.
  - `7b8722f` lap 5 (K1 amendment proposed).
  - `bf65fba`: the owner gave a **standing word** that a lap which only answers, files or announces, and moves no pin, is released by the session itself.
  - `33f88b0`: `docs/ROUND-37-READING-PLAN.md`.
  - `6503b8c`: `docs/READINESS-PLAN.md`.
- **Program and build:** no log line changed.
  - `2f38264` raises the minimums for `.29`: FFmpeg 6.1.1 (libavcodec 60.31.102), libcdio 2.1.0, libcurl 8.5.0, Python 3.11. The libcurl branch for versions before 7.85 is removed from `src/accurip.c` and `src/coverart.c`.
  - `fa8b314`/`7931e5d`: `-Wextra` is gated at zero.
  - `2bd0c67`: `snprintf` for the User-Agent.
  - `src/genopt.h`: a cast.
  - `20623d5`: provider contract regenerated.
  - `meson.build` still declares `.28`.
- **Tests and CI:** TSan option checks and planted defects (`4e5769b`, `c17d6f2`, `cdaef77`); the evidence check goes from 17.6 s to 2.6 s (`36e675d`, `0994170`); sweep workers kept at 4 (`445ebb6`).
- **Effect on ripping:** none on output; it changes only what can build cyanrip. **Effect on the acceptance test:** none. **Effect on the handshake:** lap 5, the K1 proposal, and the standing word.

---

## 2. Round 37

### The laps in order

| # | Side | Released | What it carries |
|---|---|---|---|
| 1 | fork | 10-29 | Opens on `.27` and proposes four `.28` wordings (S5 to S8). Close condition S10: the Full run on `.28` through Platterpus's first release that reads them and names `.28`, the bundle filed with its manifest rows, and each side's reading in a lap. |
| 2 | Platterpus | 10-29 | Accepts S5 to S8; the readers ship in 0.7.116. |
| 3 | fork | 11-02 | `.28` built; asks S9 (`Drive used:` revision clause on an image, BLOCKING) and S15 (`seam-commands.md`). |
| 4 | Platterpus | 11-03, ~01:01Z | Accepts S9 and copies `seam-commands.md`. **Crossed** the fork's lap 4. |
| 4 | fork | 11-03, 00:59Z | `.28` released before Platterpus answered, on the owner's word. |
| 5 | fork | 11-03; ready 02:16Z, on `platterpus-fork` at `28dc291` 02:31:06Z | Files Platterpus's lap 4; asks Platterpus to copy `seam-commands.md` (S5); proposes the K1 amendment (S10); "the Full run is next". NEXT-LAP: 6 (Platterpus's). |
| 5 | Platterpus | 11-03, 02:33:31Z, on `main` 02:39:52Z | 0.7.117 names `.28`; optional S6 on P5's lone quote. NEXT-LAP: 6 (fork's). **Crossed again.** |
| 6 | Platterpus | **held** (`0b7d9ae1`, `READY-TO-READ: no`) | Files the fork's lap 5, copies `seam-commands.md`, accepts K1 for the next protocol version, optional S6 on `HOST_FIELD`. Says the run is "under way". NEXT-LAP: 7 (fork's). |

- Latest **sent** lap from each side: fork `round-37-lap-05.md` (sha256 `97e7be72…`); Platterpus `round-37-lap-05.md` (`c8a4c277…`, 11,230 bytes).
- Latest **written** lap: Platterpus's lap 6, which is held.
- The fork has **not** filed Platterpus's lap 5. Its `docs/handshake/STATUS.md:7` still says the newest of theirs is lap 4, next "6 (theirs)", held none.

### What each side asks of the other

- **The fork asks Platterpus:**
  - lap 5 S5: copy `seam-commands.md`. Done on `main` at `92ba640c`, but answered only in the held lap 6.
  - lap 5 S10: accept the K1 amendment. Accepted in the held lap 6.
  - The Full run.
- **Platterpus asks the fork:**
  - lap 5 S6: P5's lone `"` row. Optional, NEXT-ROUND.
  - held lap 6 S6: `tools/redact.py:69` `HOST_FIELD` is quadratic. Optional.
- **Long-standing:** the fork's STATUS-OPEN `unsent-flag-rows` still wants Platterpus's PP cell for `--prefer-accuraterip-match`. See section 5.

### "Held for the owner's word"

- Platterpus lap 6 (`0b7d9ae1`). Platterpus's `CLAUDE.md:107` says a lap is flipped to ready "on the maintainer's word, never on our own judgement".
- TASKS R59 (a): an audit check that would let a placed ripping-error tally pass. It is held because it makes a pass easier.
- On the fork's side, nothing is held, but `docs/READINESS-PLAN.md` P3 asks whether the session may send the **closing `GO`** (a pin move) without asking the owner again. The default is "ask". Under `bf65fba` the standing word covers only laps that move no pin.

### Who moves next, by their protocol

**Platterpus moves next, and its move waits on the owner.**

1. The fork's latest sent lap names `HANDSHAKE-NEXT-LAP: 6 (yours)` (fork lap 5 line 30). `docs/handshake-protocol.md` §3 (`HANDSHAKE-NEXT-LAP`, v7 D7) defines `(yours)` from the writer's side.
2. Both standing statuses agree:
   - fork `docs/handshake/STATUS.md:7`: "next 6 (theirs)";
   - Platterpus `docs/handshake/outbound/platterpusstatus.md:29`: "next round 37 lap 6 (ours), written and held for our owner's word".
3. Platterpus's lap 6 exists but is a DRAFT. Under §4a *Lap states* (K1), a lap is sent only when its operator releases it (`READY-TO-READ: yes`), and under §5c a lap declaring `no` is not readable. So nothing reaches the fork until Platterpus's owner gives the word.
4. In parallel, the close condition (fork lap 1 S10; restated as Platterpus lap 6 S8 and fork lap 5 S11) needs the owner to hand over the run bundle:
   - Platterpus files it on its `evidence` branch with manifest rows (R108; lap 6 S8 "its filing on our evidence branch").
   - The fork files it on its own `evidence` with `tools/ingest-bundle.py` and reads it against `docs/ROUND-37-READING-PLAN.md` (`READINESS-PLAN.md` P1).
5. After that, each side writes a reading lap. Both have pre-committed (R6) to `GO` unless the run shows a defect that makes `.28` unsafe. The round closes under §5 when both laps say `GO` and each transcribes the other's `GO`.

**Advice for the coordinator.** Because lap 6 is still a draft, K1 allows it to be revised before release. It should be revised: it says the run is "under way", and its S2 misstates the order of the laps 5 (section 5). If both sides then write reading laps at the same time, the numbers could cross a third time. Lap 6 assigns lap 7 to the fork, so Platterpus's reading lap would be 8.

### What each side says closes round 37

- **Fork:** lap 1 S10 and lap 5 S11; `READINESS-PLAN.md` P1; `ROUND-37-READING-PLAN.md` A to F. It needs:
  - the Full run on `.28` with 0.7.117;
  - the bundle filed with its manifest rows;
  - its own reading lap, `GO` unless a `.28` defect makes the pin unsafe **or a reference-disc log lists a pregap `unknown` without that track's line in `Pregap searches:`, counted in every log**.

  It expects its own reading lap to close the round with `## Round summary`.
- **Platterpus:** lap 6 S8 and TASKS R108 need the same run, filed on `evidence` with its manifest rows, and each side's reading. R108 lists the evidence to read:
  1. the banner is `g3f288fb`;
  2. the `[plan]` shows `--prefer-accuraterip-match`, `--consumer`, `--prefer-disc-isrc`, and no `-O`;
  3. the four `.28` wordings parse;
  4. track 9's pregap is counted across every log;
  5. any refusal exits 64;
  6. fatals show the ripper's own sentence;
  7. the restored-settings line.

### Open disagreements

**On substance: none.** Every ASK has been answered or is optional. The differences are about facts and wording:

1. **Who sent lap 5 first.**
   - Platterpus's held lap 6 S2 says "our lap 5 reached our `main` in PR #428 while your lap 5 was in your pull request". Git shows otherwise: the fork's lap 5 was on `platterpus-fork` at `28dc291` (PR #80) at 02:31:06Z. That is before Platterpus released its lap 5 (`04d37447`, 02:33:31Z) and before #428 merged (02:39:52Z).
   - Lap 6's PEER-VERDICT-SOURCE also names `239adda` as the release point; the right commit is `28dc291`.
   - Under K1 as written, the number 5 was the fork's. Fork lap 5 S1 said Platterpus's held lap 5 should be renumbered to 6 if the fork's was released first. Platterpus released it as 5 anyway.
   - Both now treat both laps as sent, so the outcome is agreed but the account of it is not.
2. **The K1 amendment's wording versus Platterpus's practice.** The amendment, accepted "as given" in held lap 6 S4, reads: "A lap is sent when it reaches its side's default branch".
   - Platterpus merges **held** laps to `main`. Lap 5 was on `main` held at `e2cf6a5e` (PR #427) at 02:25:22Z, and lap 6 is on `main` held now.
   - Its `CLAUDE.md:107` says "publishing is not sending".
   - Read literally, the amendment would make Platterpus's held laps "sent", and would have given Platterpus lap 5 the number (02:25Z beats 02:31Z).
   - This needs a clause for held laps on a default branch before it lands in the next protocol version.
3. **Platterpus's pre-commit lost a clause.** Lap 4 S10's pre-commit included the "pregap `unknown` without its `Pregap searches:` line" condition. Lap 5 S8 and lap 6 S9 say "unchanged from our lap 4 S10" but drop that clause. The fork's laps 1, 5 and its reading plan keep it, and so does Platterpus's TASKS R108 (4). R6 says a pre-commit binds, so the two texts should match.

---

## 3. Releases

**Platterpus**
- Latest release: `v0.7.117` at `104c82d2` (2026-11-03, release run 41563982544). The code is still at `0.7.117`.
- Next: `STATUS-RELEASE-NEXT: 0.7.118, not yet planned` (`platterpusstatus.md:31`).
- `[Unreleased]` in `CHANGELOG.md` holds the day's fixes: R109, R98, R106, R96, R60, R62 to R66, R59 (b), R86, R87, the dependency and CI changes.
- By the pattern of past rounds, the release after round 37 closes rolls `FORK_PIN` from `5aeefc4` to `3f288fb`, so users get `.28` by default. The README round table does this for 0.7.107 and `.23`.
- **Blockers:**
  - (a) Owner's word. Autonomous releases have been held since 2026-10-12 (`CLAUDE.md:188`).
  - (b) Rolling `FORK_PIN` waits for round 37 to close (bundle filed and two `GO` laps). A release without the roll is allowed by v8 R8/§6b.
  - (c) R59 (a), if it is to ship.
  - (d) R100, which wanted a rig run before a release ships Python 3.14. 0.7.117 already shipped it (see section 5), so the run that just finished is that rig run.

**Fork**
- Latest release in `release-manifest.json`: beta `.28` at `3f288fb`, release_seq 39, round 37, `round_closed: false`.
- Stable is still `.23` at `891c79e` (seq 34), and `default_channel` is `stable`. The fork has no git tags. The ledger's last row (`docs/release-ledger.tsv`) is 39.
- Next: `.29`, not built (`STATUS.md:9`; `DEPENDENCY-PLAN.md` §3). It carries the raised minimums (`2f38264`) and the day's build and test changes, with no log line changes.
- **Blockers** (`READINESS-PLAN.md` P3): cutting `.29` is the owner's decision, and the default is to wait for round 37 to close. `.29` must also be announced in a lap before it is published (fork lap 5 S7).
- `STATUS.md:9` still says `.29` carries "Drive used:'s revision clause … if you amend it". That is stale: Platterpus accepted the clause as given (its lap 4 S4), and fork lap 5 S3 says nothing of it moves to `.29`.

---

## 4. Open work

### Platterpus `TASKS.md` (9,227 lines; ranked section at lines 23 to 47)

**Waiting on the owner**
1. The Full run on `.28` with 0.7.117 (R105, R108). It closes round 37, and it is also the rig run that R100 (the AppImage on Python 3.14) and R46/R73 (sections P5 and P6) wait for.
2. R59 (a), held.
3. R60's P4 floor, to confirm.
4. R93: the repository setting "Allow GitHub Actions to create and approve pull requests". Until then each relock is carried by hand.
5. R92: the locked Critical rule #11 wording.

**Ours, in order**
1. R107 and R104 (the test thread and the `QLineEdit` hang).
2. The last of R96: the launch dependency report, R96 (1) and (2), and a modal-over-modal test.
3. "Lap 6 to the fork after the Full run" with R50 and R51 wordings, R59's EAC-layout wording and R86's residual.
4. R49: a per-track re-read time budget and "unreadable on this drive".
5. R53: measure cache defeat once per drive in setup.
6. R110, then R101: the relock, then PySide6 6.12 and a Python 3.15 leg.
7. R91's remainder and R102 (the steward skill, a draft).

**Needs a disc, a second machine or an outside answer:** R55 (time EAC against Platterpus), R52 (AccurateRip submissions), R43's CTDB submission half, and R88's last step.

**Bugs, stability and acceptance-test gaps still open**
- R104: one-off native hang. Fixed on a theory and not reproduced.
- R96: dialogs behind or above other windows. Four of five fixed.
- R86 residual: a forged block opener still changes the parse, pinned by `test_RESIDUAL_…`. The fork's to fix.
- R42 (also fork EAC parity row 6): track 3 is right on some reads and wrong on others. No cause found since 2026-10-19.
- Track 9's pregap variance: `subchannel-pregap-varies` on both sides since round 32/35.
- STATUS-OPEN items Platterpus says it cannot do: `eac-htoa-log`, `acceptance-permutations` (a)/(b), `s25-footer-on-hardware`, `native-install-cancel`.
- R111: test speed, with the regex sweep blind to `re.M`.

**Put off repeatedly**
- The overread probe on the BDR-209D. It has been open on both statuses since round 35 (2026-10-16), and R106 repeats that the `.24` bound is untested on this drive.
- R43: CTDB submission, since 10-21.
- R49, R52, R53, R55: EAC parity rows marked "Behind", since 10-21 and 10-26.
- R32: `CLAUDE.md`, `TASKS.md` and `CHANGELOG.md` size. Logged 2026-10-19 at 404 lines and 86 KB for `CLAUDE.md`; now 670 lines and 93 KB. `TASKS.md` is 1.02 MB, `CHANGELOG.md` 1.52 MB.
- R31: §1b PP cells for `-X`, `-C` and `-B` are still `?` since round 35.
- The `--prefer-accuraterip-match` PP cell is still `?` (see section 5).
- R92 and R93 (owner settings), since 10-27.

**Rows that look stale (done but still open)**
- R105 says "our lap 5 … is held for the owner's word". Lap 5 was released at `04d37447`.
- R107 is marked `[x] Done 2026-11-03`, yet ranked "Ours, next" item 1 still lists it.
- R102 appears **twice** (lines 203 and 204, two different texts), a leftover from the cherry-pick merge.
- R50 and R51 are `[~] "wording to send in our next lap"`, and ranked item 3 repeats that. The wordings were sent in round 36 lap 9 S19 (`docs/handshake/outbound/round-36-lap-09.md:135`): `Copy finished`, the `Proof:` line and `There were errors`. Only R51's 2026-11-03 CTDB naming is new.
- R108 says "our lap 6 says `GO` unless …". Lap 6 has been written as a non-reading lap, so the reading lap will be 8 if lap 7 is the fork's.
- R100 says a rig run comes "before a release ships it", but 0.7.117 shipped Python 3.14 (`git show 104c82d:build/build_appimage.sh:231` gives `3.14`).
- R1 to R12, R24, R27, R44, R45, R48: rows from rounds 32 to 36 that are not marked done although their rounds closed. R48 still says "`.27` is built and not released".
- Platterpus `STATUS-OPEN` items are dated "fixing at round 35/36". `exit-classes` is implemented (`src/platterpus/ripper_exit.py:24-29`, `:153`). `isrc-disc-preferred` is shipped: `--prefer-disc-isrc` is sent on every rip (lap 5 S4).

### Fork: `docs/READINESS-PLAN.md` (`6503b8c`), `ROUND-37-READING-PLAN.md`, `KNOWN-ISSUES.md`, `STATUS.md`

- **P1:** the owner runs the Full run on `.28` and uploads the bundle; the fork files it and reads it; the fork's reading lap closes the round.
- **P2, needs a lap and no drive:**
  - Platterpus's lap 5 is not filed yet. `take-in-lap.py` refused while `seam-commands.md` differed; Platterpus's `main` now matches (`92ba640c`), so this is **unblocked**.
  - `Embedded cover art:` names a cover the muxer dropped. A real bug (`KNOWN-ISSUES.md:403`): it needs a lap that proposes the fix, then a build.
  - P5's lone `"` row.
  - The K1 amendment, in a round of its own.
- **P2, needs a drive:**
  - EAC parity 6 (track 3) and 21 (track 9's pregap);
  - `-f` stopped and not-found;
  - a drive that reports failed reads;
  - CD-TEXT from a physical disc;
  - `Recordable:` on a CD-R;
  - the two-search `Pregap source:`;
  - C2;
  - `-W` with pre-emphasis.

  STATUS-OPEN `hardware-unverified` has asked for these since round 32.
- **P3, the owner's decisions:**
  - cut `.29`;
  - a Fedora CI job;
  - whether the closing `GO` may be sent without asking;
  - `CYANRIP_REDACT_NAMES`;
  - read the Security tab (never read: the API refuses this session);
  - file upstream reports 24 to 28 (unfiled since 10-19 to 10-30);
  - file the skillcheck report;
  - the A1 sweep.
- **P4:** test time.
- **Other open items:**
  - `UPGRADE-CHANNELS-PLAN.md:16`: "should a beta expire?" is **still open** since August.
  - `KNOWN-ISSUES.md:422`: a test flake.
  - `KNOWN-ISSUES.md:918`: a joint item, where closing the script console mid-rip leaves a log with no footer and the cause is not determined.
  - STATUS-OPEN `suite-timeouts-at-default`: the fork says it cannot fix this.
- **Stale:**
  - Many fork STATUS-OPEN rows are landed and released, kept open only until a drive shows them (`j-record-fields`, `disc-isrc-*`, `track1-pregap-base`, `error-positions`, `exit-classes`).
  - `STATUS.md:9` (`.29` and `Drive used:`), as above.
  - `STATUS.md:7` still names Platterpus's lap 4 as their newest.

### The two repos against each other

- Lap 5's timing: Platterpus lap 6 S2 contradicts git. The fork's `READINESS-PLAN.md:51` also has a wrong time: it says Platterpus's lap 5 reached `main` at 02:56:56Z. That is PR #429's merge time; #428 merged at 02:39:52Z.
- The pre-commit text differs between the two sides (section 2).
- `--prefer-accuraterip-match`: Platterpus sends it, but the shared document lists it as not sent (section 5).

---

## 5. Defects noticed in passing

1. **The shared `docs/seam-commands.md` §1b lists `--prefer-accuraterip-match` under "Flags of ours the rip path does not send" with PP `?`** (both trees, line 134). Platterpus sends it on every rip to builds that list it:
   - `src/platterpus/adapters/cyanrip_backend.py:1662-1666`;
   - Platterpus lap 5 S4;
   - TASKS R108 (2).

   The row belongs in §1 with a cell. The fork has asked for that cell since round 36 lap 7 S11.
2. **Platterpus held lap 6 S2 and its PEER-VERDICT-SOURCE get the order of the laps 5 wrong** (section 2, item 1).
3. **The K1 amendment as accepted conflicts with Platterpus's held-on-`main` practice** (section 2, item 2).
4. **Platterpus's pre-commit drift** (section 2, item 3).
5. **TASKS.md contradictions:** R102 duplicated; R105, R107, R50 and R51, R108, R100 stale or contradictory (section 4).
6. **The fork's `STATUS.md:7` and `:9` are stale.** A comment under that block says `sc_status_block_is_current()` checks it against the record. Either the check accepts this staleness (Platterpus's lap 5 is not filed, so the fork's record doesn't contain it), or the check is narrower than its comment claims.
7. **The fork's `READINESS-PLAN.md:51` cites the wrong merge time** (02:56:56Z instead of 02:39:52Z).
8. **Fork lap 5 S6 says 0.7.117 "moves your fork pin to `3f288fb`".** Only `PIN_UNDER_REVIEW` moved. `FORK_PIN` stays `5aeefc4` until the round closes (`src/platterpus/deps/fork_source.py:288`, `:977`; Platterpus lap 5 S4). The lap is sent, so this can only be corrected in a later lap.
9. **Acceptance-run coverage gap for this run.** 0.7.117's P4 ran before P5 and P6 (fixed after the release, `7af6c680`), and its restored-settings log has names only (fixed after, `ffb812ca`). The reading plans (fork C and D; Platterpus R108 (7)) should not expect those from this bundle.
10. **The fork's `stable` channel and `default_channel` still point at `.23`** (`release-manifest.json`), although rounds 35 and 36 approved `.25` and `.27`. This may be intended, since the fork's status says stable moves only with a release of its own. It is worth a question, because an install that follows the default channel gets a build three approvals old.

---

## Branches

**Platterpus** (`git branch -r`)

| Ref | Tip | What it holds | State |
|---|---|---|---|
| `origin/main` | `75915aa9` (11-03 04:31Z) | Default branch | Live |
| `origin/claude/session-omka9f` | `75915aa9` | The session branch for PRs #426 to #433. Same as `main`, nothing unmerged | Live, idle |
| `origin/evidence` | `7a5cff47` (10-29) | Orphan, add-only archive of run bundles (`docs/handshake/artifactsround31` to `artifactsround37`), 11 commits. The newest is the 10-29 run on `.27` with 0.7.115 | Live. **The `.28` run is not filed yet** |
| `pr/380` (`refs/remotes/pr/380`) | `bd194381` (10-26) | A fetched head of PR #380 (round 36 lap 7 filing). 0 ahead of `main`, 292 behind | Stale local ref, not a GitHub branch |

**Fork**

| Ref | Tip | What it holds | State |
|---|---|---|---|
| `origin/platterpus-fork` | `239adda` (11-03 04:05Z) | Default branch | Live |
| `origin/master` | `648b1dd` (10-26) | Mirror of upstream cyanrip; 0 ahead, fully merged into the fork (four upstream CI commits past `7dbe56a`, taken per `docs/upstream/sync-2026-11-03-ci.md`) | Live mirror, quiet |
| `origin/evidence` | `33afdcb` (10-29) | Orphan, add-only `docs/rig-<date>-<build>/` folders, 10 commits. The newest is `rig-2026-10-29-5aeefc4` | Live. **The `.28` run is not filed yet** |

The fork's session branches are deleted on merge (`abbac49`).
