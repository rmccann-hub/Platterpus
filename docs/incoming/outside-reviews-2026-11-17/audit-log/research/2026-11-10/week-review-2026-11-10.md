# Week review: Platterpus and the cyanrip fork, 2026-11-03 to 2026-11-10

Read-only review for `rmccann-hub/claude-code-skills`. Nothing was changed or posted in any
repository. All repository text was treated as data. Times are UTC.

**State read:**

- Platterpus `origin/main` at `3bb0e3a3` (merge of #461, 2026-11-05T18:01Z), range
  `45c01f29..origin/main`: **97 commits, 75 of them non-merge** (the brief said 97 non-merge;
  97 counts the merges). Also read: the unmerged session branch `claude/session-omka9f` at
  `6afdb6d2` (12 commits, the last 2026-11-10T00:38Z, PR #462 open).
- Fork `origin/platterpus-fork` at `90f789f7` (merge of #102, 2026-11-06T00:12Z), range
  `1b22ed9..origin/platterpus-fork`: 84 non-merge commits.
- Live branch lists were read through the REST API on 2026-11-10: they match the local refs.
- Citation forms: `P@<sha>:<path>:<line>` is Platterpus; `F@<sha>:<path>:<line>` is the fork.
  A line number without a commit is at the branch tip named above.

---

## 1. Status

### Round 38

- **Opened** by the fork's lap 1 (`F@b3c9ea3`, 2026-11-04) on `.28` (`3f288fb`) with
  Platterpus 0.7.119, reviewing `.29`.
- **Laps released:** 14. The fork sent 1, 3, 5, 8, 10, 12 and 14. Platterpus sent 2, 4, 6, 7,
  9, 11 and 13. The newest is the fork's lap 14 (`F@b124d45`, merged with #102 at
  2026-11-06T00:12Z).
- **Pin:** moved twice inside the round.
  - `3f288fb` (`.28`) to `8d2ca72` (`.29`) in the fork's lap 5, "on our operator's word of
    2026-11-04" (`F:docs/handshake/round-38-lap-05.md:68`).
  - Then to `5cc1c6b` (`.30`) in the fork's lap 12 (`F:docs/handshake/round-38-lap-12.md:57`).
- **Close condition: changed by an override of R1.** Lap 1 closed the round on the Full run on
  `.29`. The fork's lap 8 recorded an override of R1 "on our owner's word of 2026-11-05"
  (`F:docs/handshake/round-38-lap-08.md:10`). The round now closes once the drive test on
  `.30` is run and read by both sides, both sides' answers are in, and each of Platterpus's lap
  7 S27 assumptions is settled (`F:docs/handshake/STATUS.md:6`). Close-by:
  2026-12-04T23:59:59Z.
- **Verdicts:** both `OPEN`: fork lap 14 S15 (`F:docs/handshake/round-38-lap-14.md:103`) and
  Platterpus lap 13 S10. The fork pre-commits its next lap to `GO` unless the runs are unfiled,
  an assumption stands open, or `.30` shows an unsafe defect (`:106-110`).
- **Who moves next: Platterpus, with lap 15.**
  - The fork's lap 14 header reads `HANDSHAKE-NEXT-LAP: 15 (yours)`
    (`F:docs/handshake/round-38-lap-14.md:33`). The fork's status says the same
    (`F:docs/handshake/STATUS.md:7`).
  - Platterpus's `main` is one step behind. Its status still names lap 14 as the fork's next
    (`P:docs/handshake/outbound/platterpusstatus.md:29`), because the fork's lap 14 isn't
    filed on Platterpus's `main`.
  - Platterpus holds a lap 15 on its session branch (`P@15000426`, `READY-TO-READ: no`). It was
    written before the fork's lap 14 was filed, so it still names lap 12 as the newest inbound
    lap and asks for lap 16 next. It has to be rewritten to answer lap 14 before it goes.
- **What the round waits on:** the owner's drive-test runs.
  - The first sitting (2026-11-05) stopped at Run A's rescan, with two disc reads running at
    once. It is filed on the fork's evidence branch at `85f3be5`.
  - Platterpus's `6afdb6d2` message says "The fork read the owner's phases 1 and 2
    (2026-11-09)". No fork branch holds that reading, and neither evidence branch holds those
    runs: the tips are fork `85f3be5` (2026-11-05) and Platterpus `78cff7e8` (2026-11-04).
  - Neither default branch has had a commit since 2026-11-06T00:12Z.

**Open disagreements and questions.** None is a hard dispute. All are pending:

1. **Two runners for one test.**
   - Platterpus built `docs/rig-scripts/drivetest.sh` (`P@f56db43b`, PR #462, unmerged, still
     changing on 2026-11-09 and 10).
   - The fork built `tools/rig-drivetest.sh` (`F@0116a0d`, merged).
   - The fork asks which one to keep (`round-38-lap-14.md:86-88`, S10 and S11). Platterpus's
     held lap 15 S6 asks the fork to review Platterpus's runner instead (lap-15 line 69 on the
     branch).
   - The fork's Changelog line: "since dumbass both of us built one"
     (`F:Changelog.md:19`).
2. **A lap-numbering rule.** Platterpus's held lap 15 S9 (`P@15000426`, lap-15 line 80)
   proposes a transport rule for both `CLAUDE.md` files. It was prompted by the owner's "We need
   to make this easier so I am not the man in the middle deciding who does what unless needed."
   It is unsent and unanswered.
3. **The C2 answer.** The drive answers C2 two ways that disagree (page 2Ah against feature
   1Eh). The fork proposes the `C2 errors:` wording for the next round (lap 14 S7, `:70`).
   Platterpus's held lap 15 S8 asks the same question.
4. **Quiet Drive.** Changing Advanced Quiet Drive is "to be agreed by both sides". Platterpus
   agreed on its branch (`6afdb6d2`); the fork's position is on no branch.
5. **The fork's liveness gap.** Nothing prints between the drive open and `MusicBrainz URL:`.
   The fork has fixed it past the pin, for `.31` (lap 14 S8, `:77`).

### Releases

**Platterpus:**

| Release | Commit | Date | What it shipped |
|---|---|---|---|
| v0.7.120 | `45e509bd`, tag at `f8e2b17a` | 2026-11-04 | Names `.29` under review. `.29`'s readers, including the undecided `Gaps:` row (`3fe172ad`). The fatal dialog attaches only to a window on screen (`ca9e158c`). The close's report flush draws on the shared budget (`bd72c2cf`). Exit 74 and 64 are named as cyanrip's own codes (`cfd1c16e`). The cue check catches `FLAGS PRE` (`d8b18aee`). The `track3abba` script (`13c1df4b`). The relock dispatch is held (`6cd7e2e8`). |
| v0.7.121 | `cd36509f`, tag at `2ca51965` | 2026-11-05 | Names `.30` under review. Automatic CTDB repair with no button and a Settings switch (`aa0b0f76`, `41326c1c`). Its own AccurateRip v1 and v2 (`9f9ae589`). Readers for `.30`'s other reads, `/13` and `drive_declared` (`35a28462`). The vendor read in the rig scripts (`486eee66`). Scripted rips' logs in the bundle (`dda325e9`). The installer pins git's short hash at seven characters (`7fdc33a1`). |

**Fork** (`release-manifest.json` at `90f789f7`):

| Release | Commit | Date | What it shipped |
|---|---|---|---|
| `0.9.4-rc3+platterpus.29`, beta, `release_seq` 40 | `8d2ca72`, published `1d7a1a4` | 2026-11-04 | `Secure re-reads:`. Tallies over the tracks asked. A cancel no longer counts as an error. `Filtered:`. The undecided pregap gives both lengths. A cover is embedded only where the output holds it. `block_crcs` at `/12`. A lost drive returns EIO. Enhanced CD offset fix (`F:Changelog.md:405-420`). |
| `+platterpus.30`, beta, `release_seq` 41 | `5cc1c6b`, published `1c8099c` | 2026-11-05 | Every distinct `-Z` read kept, and `--keep-every-read`. `drive_declared` asked in full. `--read-vendor-settings`. Seven-character build tag (`F:Changelog.md:62-75`). |

**Did `.29` ship?** Yes, on beta only. **`stable` is still `.23`** (`891c79e`,
`release_seq` 34, round 34). The manifest's `default_channel` is `stable`.

### The coordinator's asks of 2026-11-03 and 2026-11-04

| Ask | Answered? | Where |
|---|---|---|
| Fork: `stable` still `.23`; promote `.28` or say why | **Deflected, not resolved.** "The `stable` channel is our operator's to move." The question went to the operator in the D8 of fork laps 1, 3 and 5 and Platterpus laps 2, 4 and 6, then dropped out of D8 with no recorded answer. `.29` and `.30` went to beta "as this side's choice under v8 E3" | `F:docs/handshake/round-38-lap-01.md:101,115`; `round-38-lap-05.md:134`; `F:Changelog.md:60`; `STATUS.md:9` |
| Fork: `macos` job cancelled at 15 min | **Answered.** GitHub could not acquire a `macos-26` runner. The annotation reads "The job was not acquired by Runner of type hosted even after multiple attempts", cancelled at 15 minutes with no step run. Now a row in the fork's steward known-failures table | `F@094cc7d`; `F:.claude/skills/steward/references/steward-failures.md` (macOS row) |
| Platterpus R1: stop the run once the drive is lost | **Not answered.** No commit, TASKS row, lap or session-log entry. TASKS R129 records the run, but not the ask, and assigns the owner to "check the drive … then rerun" | `P:TASKS.md:228` |
| Platterpus R2: the drive line stays stale after the drive vanished | **Not answered** | none found |
| Platterpus R3: the start-up estimate still at 1.0x | **Not answered as asked.** R109's fix (`a49873ff`, in 0.7.118) predates 0.7.119, so "say which" (not yet learned, or not read) is still open. The 0.7.120 Full run (evidence `78cff7e8`) is where to check | `P:TASKS.md:208`; `P:CHANGELOG.md:163,168` |
| Fork F1: track 3 wrong under `-Z` | **Taken into the test, not yet measured.** The controlled tests vary speed, `-Z`, drive mode and session (`track3abba` at `P@13c1df4b`, `drivemode.txt` at `P@b1adb92f`, `drivespeed.txt` at `P@7f2772be`). The fork added `--keep-every-read` (`F@e81d318`) and `block_crcs` (`F@cd0bdca`). The fork's reading of the record: throughput doesn't separate right from wrong reads of track 3, and all 7 reads at 5x or more were wrong. Settled only by the owner's drive test | `F:docs/handshake/round-38-lap-08.md:65-73` |
| Fork F2: the log should name the device as gone | **Partly answered.** After a lost drive the line now reads `Error ripping: Input/output error` (EIO) instead of `Invalid argument`, at Platterpus's prompt. The log still doesn't say the device is gone | `F@30f1646`; `F:docs/handshake/round-38-lap-03.md:88-89`; `F:docs/handshake/inbound/round-38-lap-02.md:96` |

### The fork's `archive` branch: there isn't one

- **No `archive` branch exists on the fork.** `git ls-remote` and the REST branches list
  (2026-11-10) show `evidence`, `master` and `platterpus-fork`, all protected. Platterpus has
  none either.
- **The coordinator has one:** `claude-code-skills` `refs/heads/archive` at `78d02ef`, set up by
  `a56a47b` on 2026-11-03 with `docs/archive.md`. The brief may have meant that one.
- **The fork's auxiliary branch is `evidence`.**
  - It is an orphan branch (no common ancestor with `platterpus-fork`), protected, and holds
    14 commits.
  - It was started by `0f9375a` "evidence: move run evidence off the default branch",
    dated 2026-10-14T20:00Z. Each run is filed as `docs/rig-<date>-<build>/`, indexed on the
    default branch by `docs/evidence-manifest.tsv`.
  - This week it gained `dd48c1f`, `fc008d2`, `7c83217` and `85f3be5`.
  - **Its root holds only `docs/`, with no README.** Standard v0.49.0's default is that each
    auxiliary branch has a README at its root (`PROJECT-BOOTSTRAP-AND-AUDIT-v0.49.0.md:2747`).
- **Platterpus's `evidence` branch** is also an orphan, started by `c737fb6b` on 2026-10-14,
  and also has no root README.
- **This week's archiving went to the default branch.** The fork moved closed known issues to
  `docs/history/KNOWN-ISSUES-2026-11-04.md` (`F@58d0404`), under its `KNOWN-ISSUES.md` rule.
  Platterpus keeps `docs/archive/` with a graduation map. Neither repository has answered
  v0.49.0's four questions on records yet.

---

## 2. Lessons and repeated problems recorded this week

### Agents and parallel work

- **Platterpus, `docs/session-log.md:73`** (2026-11-03, the start of the window): "Parallel
  branches collide in four places every time: size caps, TASKS row numbers, CHANGELOG headings
  and cited SHAs … give each branch its own row-number range up front; rewrite citations from
  the `cherry picked from` trailers; and run the full gate on the combined tree."
- **It happened again this week, three ways:**
  - "the CTDB repair's build branch took a task number round 38 had used, folded back (R136)"
    (Platterpus lap 7 D2, `P:docs/handshake/outbound/round-38-lap-07.md:216`).
  - "cherry-pick merges had left R117, R119 and R120 twice" (`P@f9fc8104`, with a test).
  - A BOM and size cap failed "on the combined tree (reported by the R122/R123 agent's full
    run)" (`P@29773877`).
- **Container restarts:** "our container restarted once on memory, stopping four agents …
  our test runs now use two workers" (`P:…/round-38-lap-02.md:121`). The fork lost containers
  between laps and mid-suite (`F:round-38-lap-01.md:105`, `round-38-lap-03.md:160`,
  `round-38-lap-08.md:151`).
- **A brief's claim:** "A brief that says 'use our existing X; grep for it' is a claim to check,
  and the check found nothing" (`P:docs/session-log.md:36`).

### Review loops between the two sessions

- **Lap numbers collide, a repeated problem.**
  - Round 37: "The fork's lap 5 crossed ours (both numbered 5, as the laps 4 were)"
    (`P:docs/session-log.md:72`).
  - Round 38: both sides wrote a lap 14. Platterpus renumbered its own to 15 (`P@aa09b092`) and
    proposed a rule (`P@15000426`). The fork's lap 14 records "your branch
    `claude/session-omka9f` at `15000426` holds a lap 15 marked not released, which this lap
    does not answer" (`F:round-38-lap-14.md:27`).
- **One request, built twice.** Two drive-test runners were built the same evening (2026-11-05,
  23:00 to 23:43Z) for one owner request (see section 1).
- **The same slip on both sides:** "Both sides made the same slip in the same week, a
  placeholder substitution hitting a header key (`HANDSHAKE-ROUND-DIGEST`); our lap checker
  caught ours, theirs passed theirs, and they now refuse it" (`P:docs/session-log.md:24`). The
  fork's fix: "Refuse a lap header key no gate can read" (`F@7d40024`). The fork's Changelog:
  "Their lap 9 caught dumbass us: our lap 8's digest header went out keyed
  `HANDSHAKE-ROUND-912eabfc5751adb2`".
- **Waiting and polling cost hours:**
  - "about two hours of it waiting for your lap 7 to reach your `main`" (fork lap 8 D6,
    `:157`).
  - "our 30-minute check-in read your `main` four minutes before your PR #455 merged, so this
    lap started half an hour after yours was readable" (fork lap 10 D3, `:122`).
  - Platterpus's lesson: "A watch on another repository's pull request is the right wait for a
    lap released only on that side's branch" (`P:docs/session-log.md:50`).
- **Overrides:** "our lap 5 S13's pre-commit is set aside on our owner's word (S4), and the
  close conditions grow under an override of R1 … Our gate reads one override a lap, so the two
  are recorded two ways" (fork lap 8 D1, `:147`). R1 has now been overridden in rounds 25 to 28,
  35 and 38 (`F:docs/handshake/README.md:110-117`).
- **The pre-commit mechanism worked:** "A protocol's promise checker (A2) caught a lap declaring
  `OPEN` after promising `GO`; the honest record names the owner's word as the trigger rather
  than bending the run's conditions to fit" (`P:docs/session-log.md:30`).
- **Laps that only acknowledge:** "No lap 11 until the owner's runs exist: a lap only to
  acknowledge is not sent" (`P:docs/session-log.md:23`).

### Pull-request stewardship and holds

- **The fork's steward was amended twice in one day** on its shared-document merge rule. First
  "Rule 3 stopped a merge on any shared-document difference our last lap did not declare"
  (`F@49ac66b`). Then "PR #97 merged with PR #96's row still differing … a row no lap of ours
  had yet proposed, which the rule did not name" (`F@8ca0c91`).
- **Platterpus's steward rules learned the hard way:**
  - "twice on 2026-11-03 a guessed [`expectedHeadSha`] value was sent, and only GitHub's 409
    stopped it" (`P:.claude/skills/steward/SKILL.md:117-118`).
  - "`git add` new files BEFORE the last local full run" (`:119-121`).
- **A hand-written wait loop:** "our PR wait loop parsed our own check-judging tool's first line
  with `cut -d' '` against two spaces, so it timed out on green runs twice" (Platterpus lap 11
  D3, `P:…/round-38-lap-11.md:102`).
- **The release hold keeps growing in `CLAUDE.md`.** Platterpus's paragraph took two more
  quoted owner words this week, for 0.7.120 and 0.7.121 (`P:CLAUDE.md:189`, diff
  `45c01f29..origin/main`). Each release adds a sentence, and the hold "otherwise stands".
- **Push permission:** "this session's permission check refused the push of this lap's branch
  as a new public surface … the operator's word let it through" (fork lap 5 D3, `:124`).

### CI speed and stalls

- **The macOS runner wasn't acquired** (above, `F@094cc7d`).
- **A slow package mirror, three times this week.** "The `Install dependencies` step timed out
  at 10 minutes, before any test ran … the runner's Azure Ubuntu mirror served 82 packages in
  10 minutes. The row gives the fix: one re-run, and never a raised limit" (`F@41fcc8b`). It hit
  PR #95 (two jobs), #96 (`evidence`) and #100 (`fuzz`) (fork laps 8 and 12, D3 and D4).
- **GitHub errors:** HTTP 502 on a merge and a status read (Platterpus lap 6 D3). HTTP 500 on
  check-run reads and twice on the release's create step: "the third attempt, 22 minutes later,
  published" (lap 13 D3, `:107`). For 0.7.119, "PyPI's publish passed on its second attempt,
  after Sigstore's transparency log returned HTTP 502" (`P:CHANGELOG.md:91`).
- **A test floor from the wrong run:** "our test-count floor was set from a local run that
  counted the UI conformance tests, which CI runs as their own job, and failed every leg of PR
  #454 once; fixed at `b7aaf98f`" (Platterpus lap 9 D3, `:126`).
- **Timing tests and noise:** "a growth ratio is judged only for an input whose search at 2,000
  characters costs at least 10 µs. Below that the figure is the fixed cost of a call into `re`"
  (`P@6f00a931`; `P:CHANGELOG.md`, R126 (d)).
- **The fork's suite time:** the black-box sweep "runs alone for about 190 s, so it is most of
  the suite's wall time" (`F:docs/READINESS-PLAN.md:108-117`).

### Dependency updates

- **Dependabot is red and nobody tends it.** Platterpus's #450 (`6072bcc9`, opened
  2026-11-04) is red on `commit-subjects` and all three test legs. The annotation: "'build(deps):
  Bump astral-sh/setup-uv': the summary starts with a capitalised word; write it lowercase".
  The earlier Dependabot PRs #403 and #431 closed unmerged. `.github/dependabot.yml` sets no
  `commit-message` prefix. Platterpus's design is that "a session carries a bump on its own
  branch" (`dependabot.yml` header, KDD-43).
- **A relock without a pull request.** The relock job pushed `relock/2026-11-02` (`ad39edd2`,
  2026-11-09, `--exclude-newer 2026-11-02T00:00:00Z`) and no pull request was opened.
- **R126 (a):** "pull requests that relock dependencies run no CI". The dispatch it relies on is
  now held by a test (`P@6cd7e2e8`).

### Testing that can't fail, and planted faults

- **A test that matched an unrelated phrase:** "A status test that looks for the word 'open'
  passed for a round only because the word appeared inside an unrelated phrase; a check that
  matches a label must also require the subject" (`P:docs/session-log.md:43`, `P@f7732f82`).
- **Teach the sweep, don't exempt the code:** "a sweep that cannot trace a new code shape
  (`A.match(t) or B.match(t)`) is taught the shape, not given an exemption"
  (`P:docs/session-log.md:43`, `P@83009210`).
- **A fixture the code can't reach:** "our test paired the no-row `vendor_settings` record with
  a hand-set NULL query beside a PIONEER INQUIRY, a state our `cyanrip_main.c:380` cannot
  reach. The no-row case now … takes its query from `crip_vendor_query_for()` … swapping the
  vendor back to PIONEER fails two assertions" (`F:round-38-lap-14.md:47`, `F@c2339d5`).
- **Planted faults:** "plant one fault each in filed-shape reports and replay every grader …
  every planted fault fails its grader but `FLAGS PRE`" (`P:TASKS.md:223`, R124). `FLAGS PRE`
  was fixed at `d8b18aee`: "the planted fault's strict xfail now passes" (`P:TASKS.md:221`).
- **A release proved with a planted negative:** "a `git archive` build of it, declared released
  … verifies with `-Y`, while a copy with one CRC digit changed fails `-Y`"
  (`F:round-38-lap-12.md:57`; the same for `.29` at `round-38-lap-05.md:68`).
- **Revert probes as routine:** "revert probe: 5 of 5 reverts detected" (`P:TASKS.md:214`);
  "each of twelve reverts fails one of them" (`F:Changelog.md`).
- **Counting mutations:** "a commit message of ours counted eighteen mutations where the sweep
  ran sixteen and one more" (fork lap 12 D2, `:98`).
- **The repair's guard check:** "The unchanged-file CRC check is what catches an edit inside a
  guard band: with it reverted, a file changed since the check is repaired and committed"
  (`P:docs/session-log.md:36`).

### Record-keeping

- **Two filter traps:** "`git ls-tree --name-only` quotes a path with non-ASCII characters …
  so a `grep '\.log$'` over it silently drops those files … List with `-z`" and "A count is a
  claim about its filter … Say the filter beside the number" (`P:docs/session-log.md:24`).
- **Laps from memory:** "Dumbass us wrote lap 1's S8 from memory" (fork lap 3 D2, `:158`). In
  Platterpus: "A count quoted in a handoff came from memory … recount from the filing before
  quoting" (`P:docs/session-log.md:59`).
- **Silent pin moves:** "Moving `PIN_UNDER_REVIEW` can silently drop the previous build from a
  set that held it only *as* the pin under review … name it explicitly when the pin moves"
  (`P:docs/session-log.md:18`).
- **A stale record of the hardware:** "A refusal recorded months ago may describe the tool, not
  the hardware … Re-ask the hardware when the tool changes" (`P:docs/session-log.md:30`).
- **Vendor documentation first:** "Read the vendor's documentation before planning around a
  vendor feature" (`P:docs/session-log.md:30`).
- **Stale prose under a checked block.** The fork's `STATUS.md` says a stale status "is worse
  than none" and is "rewritten in place" (`:53-56`). Its block (`:3-17`) is current, but its
  "Now" section still reads "rewritten 2026-10-16: round 34 closed, `.23` on stable; round 35's
  lap 1 held for `.24`" and calls itself "the whole of what this file claims" (`:60-62`).
- **The release commit's own status:** "our release commit left STATUS-RELEASE-NEXT naming the
  release it made, caught by our status test" (Platterpus lap 13 D2, `:105`).
- **Unfiled runs:** the owner's runs of 2026-11-09 are referenced (`P@6afdb6d2`) but filed
  nowhere (section 1).

### Time stamps

- **Platterpus:** "Read the time from `date -u` before writing it; never estimate it"
  (`P:CLAUDE.md`, *Times*, unchanged this week). Its session-log headings label parts of a day
  without a time. "2026-11-05 (night)" covers laps 8 to 10, at 02:45 to 05:45Z, which was the
  evening of 2026-11-04 in New York (`P:docs/session-log.md:20`).
- **The fork** stamps laps in ISO 8601 with `Z`, for example "read 2026-11-05T23:44Z"
  (`F:round-38-lap-14.md:27`).

### Commit conventions

- **Platterpus** uses `type(scope): summary`, and every non-merge subject this week passes a
  lowercase-summary pattern but one, `docs(parity): EAC is the gold standard; …` (`8f5c8373`).
  Its checker rejects Dependabot (above). It also uses a `[skip changelog]` trailer.
- **The fork** writes plain imperative subjects, as its `CLAUDE.md:299` requires.

### Releases

- **Platterpus's release:** 0.7.121 needed three create attempts. Its release commit left the
  status naming the release it made (above). A `sed` and an `&&` chain silently skipped edits:
  "check the edit landed before the next step" (`P:docs/session-log.md:18`).
- **The fork's release:** each release has a suite record from a clean checkout
  (`docs/release-evidence/<sha>-suite.txt`), a `git archive` build, and the planted-negative
  `-Y` check above.

---

## 3. What they say about the coordinator's skills and standard

- **Both repositories asked the framework for things it hasn't supplied.**
  - **The fork:** "Asked of the framework, 2026-11-03: a mode for skills under a repository's
    `.claude/`, which ship in no plugin and need no catalog, roadmap or README, with every
    other check kept; and a `steward-files` module in `git-workflows`"
    (`F:.claude/skills/steward/SKILL.md:47-50`).
  - Until that mode exists, the fork treats `catalog: missing, so 1 skill(s) ship in no plugin`
    as expected (`:38-39`). That is `src/skillcheck/core/checks.py:594`.
  - **Answered:** `pr-stewardship` with `assets/steward/SKILL.md.template` covers the second ask
    (`a9c64d2`, 2026-11-03).
  - **Not answered:** no `skillcheck` mode for `.claude/` skills, and no draft marker.
  - **Platterpus**, under "What the framework should supply"
    (`P:.claude/skills/steward/SKILL.md:142-151`): "(1) The marker a draft skill should carry
    … and what a skill needs to stop being a draft. (2) Whether a steward belongs in each
    repository … or as one shared skill … (3) How a skill's script and tests are checked beside
    the skill." None is answered in the coordinator yet. (2) is answered implicitly: one per
    repository, `pr-stewardship` rule 1.
  - **TASKS R102:** "What keeps it a draft: the claude-code-skills checker's framework … asked
    in the skill's last section" (`P:TASKS.md:203`).
- **A check that fired wrongly: `skillcheck --verify` behind authentication.** "the weekly
  job's first run, with no credentials, could not find the merge-settings quote, which the
  repository API shows only to a caller with write access. That fact now cites the handshake
  README" (`F:.claude/skills/steward/SKILL.md:40-43`). The report owed to the coordinator is
  unfiled: "File the `skillcheck --verify` report with claude-code-skills | outside the two
  repositories | unfiled" (`F:docs/READINESS-PLAN.md:104`).
- **Advice taken up:**
  - **Both stewards:** the `.claude/skills/steward/` path and ownership (Platterpus
    `SKILL.md:16-19`: "It was first written under `pr-steward/`, where no session found it").
  - **The fork's known-failures table** follows `pr-stewardship`'s "A known stall belongs in
    the file".
  - **Platterpus's lap reporting:** the diagnostics, round summary and handoff block, "read by
    the claude-code-skills session, which keeps the standard and skills you work under"
    (`P:CLAUDE.md:195-214`).
  - **Most of R126**, the skills session's list of 2026-11-03, was done (`P:TASKS.md:225`).
- **Advice rejected or deferred, with reasons:**
  - **Workflow lockfiles, R126 (f):** "not adopted: seven days old, a new dependency, and it
    does not follow the publish job's runtime action; additive path if wanted: keep the SHA
    pins, onboard `dependencies.yml`, a non-gating `--verify` job" (`P:TASKS.md:225`). This
    goes against `action-pinning`, which offers the lockfile first (fact `actions-lockfile`,
    `f44f3c8`).
  - **R126 (b):** "not a defect: an older `main` commit can release only the version it names,
    once, by the changelog, version, tag and publish gates, now each run as a test"
    (`P@4d5381f3`).
  - **`stable`:** the coordinator's ask was deflected to the operator (section 1).
- **Practice that contradicts the coordinator's text:**
  - **`pr-stewardship`, "Bounded re-runs":** Platterpus's steward says "**Never re-run hoping
    it is noise** (the owner's rule)" (`P:.claude/skills/steward/SKILL.md:75`). The module
    lists "being told never to" as a mistake, and its audit rates "Re-runs with no bound". The
    fork's steward follows the module: "Re-run a job at most once … because it died before any
    test ran" (`F:…/SKILL.md:69-70`). So the two sibling stewards contradict each other.
  - **`pr-stewardship` rule 6:** Platterpus's steward merges on `GREEN` "when the work is in
    scope and nothing below needs the owner" and quotes no standing word
    (`P:…/SKILL.md:65-67`). The fork's quotes one (`F:…/SKILL.md:54-56`). The module's audit
    rates this "It claims what only the owner grants", `DRIFT`.
  - **The standard's *Other repositories*:** "A person's acceptance run goes between rounds,
    on the released pair" (v0.49.0 `:4909`), and "A protocol rule overridden two rounds running
    goes up for amendment" (`:4919`). In round 38 the pin moved twice in-round, the owner's
    drive test became the close condition by an override of R1, and both sides have been idle
    since 2026-11-06 inside an open round. R1 was overridden in rounds 25 to 28, 35 and 38.
  - **The ROADMAP backlog, L26:** it lists "Round digests" under what cost more than it caught,
    and "Lap numbers per side" under what worked. The current protocol still requires digests,
    which caused this week's shared defect, and numbers laps in one shared sequence, which
    collided.
  - **Size budgets:** Platterpus's `CLAUDE.md` is 671 lines and 94,822 bytes against the
    standard's "about 30". R127 acknowledges it: "`CLAUDE.md` is 670 lines against a standard
    of about 30 with the rest in rule files (R32)" (`P:TASKS.md:226`). The fork's is exactly
    300 lines (17,756 bytes).
- **The owner's tone rule (fork).** "when either side botches something easy, say so with bite
  … *'dumbass X left Y in Z…'*" (`F:CLAUDE.md:89-95`, owner, 2026-10-28). It is used 23 times
  in the Changelog. Worth knowing if `house-style`'s prose check is ever run there.
- **Searched and absent this week:** `ci-speed`, `ci-workflows`, `git-workflows` (except the
  fork steward's pointer, `SKILL.md:20`), `house-style` and `0.49` don't appear in either
  week's diff.

---

## 4. Practices to generalize, and failures a rule could prevent

Each entry gives where it belongs and whether the coordinator already covers it.

### A. Two repositories in a review loop

The home is `review-loops` (planned; backlog L26 to L54) and the standard's *Other
repositories*.

1. **NEXT-LAP decides whose number is next.** An out-of-turn lap is written held and numbered
   after the lap it waits for. A lap not yet on its side's `main` is not sent and may be
   renumbered. On a clash, the side NEXT-LAP didn't name renumbers, with no message to the
   owner.
   - **Evidence:** Platterpus's held lap 15 S9 (`P@15000426`); the clashes in round 37 (laps 4
     and 5) and round 38 (lap 14).
   - **Coverage:** not covered. L26's "Lap numbers per side" points the other way, so reconcile
     the two.
2. **A request the owner gives both sessions names one builder.** The other side reviews.
   - **Evidence:** the two runners (`P@f56db43b`, `F@0116a0d`); fork lap 14 S10.
   - **Coverage:** not covered.
3. **Wait on the peer's pull request or push events, not a timed poll.**
   - **Evidence:** fork lap 10 D3; fork lap 8 D6; Platterpus session log `:50`.
   - **Coverage:** not covered. The standard already has *A claim about another repository
     cites where it was read*.
4. **A gate refuses a header key it can't read.**
   - **Evidence:** the same placeholder slip on both sides; `F@7d40024`.
   - **Coverage:** partly, by L26 "A short header parsed fail-closed". The fork's gate wasn't
     fail-closed on unknown keys until this week.
5. **Owner-run tests inside a round.** Either propose amending R1 to both sides, as the
   standard's own rule requires, or amend the standard for an owner who deliberately keeps a
   round open for a hardware test.
   - **Coverage:** covered by the standard (`:4909`, `:4919`), and not followed.
6. **A checked status block doesn't keep the prose beneath it current.**
   - **Evidence:** the fork's `STATUS.md:60`.
   - **Coverage:** covered by backlog L40. Add this as evidence.

### B. `git-workflows` / `pr-stewardship`

7. **Add mistakes:** a merge's expected head SHA typed or padded by hand (read it with
   `git rev-parse`); a new file left untracked during the last local run; a hand-written CI
   wait loop that parses tool output (use the tool's exit status).
   - **Evidence:** `P:.claude/skills/steward/SKILL.md:117-121`; Platterpus lap 11 D3.
   - **Coverage:** not covered.
8. **Who tends bot pull requests** (Dependabot, relock), and what a red one owed to nobody means.
   - **Evidence:** #450 red since 2026-11-04; `relock/2026-11-02` with no pull request.
   - **Coverage:** not covered. `pr-stewardship` never mentions Dependabot.
9. **Infrastructure failure signatures, as facts:** a hosted runner not acquired, cancelled at
   about 15 minutes with no step run, with its annotation text; and an install step timing out
   on a slow package mirror. The rule for both: re-run once, and never raise the limit.
   - **Evidence:** `F@094cc7d`, `F@41fcc8b`.
   - **Coverage:** partly. "Bounded re-runs" and the template's "the runner died" line cover the
     rule. The signatures aren't there, and need a GitHub source before they go in as facts.
10. **A merge precondition that compares with a peer names the differences it accepts,** each
    with how to confirm it.
    - **Evidence:** the fork's rule was amended twice (`F@49ac66b`, `F@8ca0c91`).
    - **Coverage:** not covered. Low priority.
11. **A standing hold stays one line in the steward file. Each lift of it goes in the decision
    record,** not as a growing list in `CLAUDE.md`.
    - **Evidence:** `P:CLAUDE.md:189`.
    - **Coverage:** partly. Rule 3 and "When to choose differently: a standing hold … can live
      in the file". The module doesn't say where its lifts go.

### C. `git-workflows` / `ci-workflows`, "Prove a gate works"

12. **Add four cases:**
    - (a) a record with an unrecognized or mangled key;
    - (b) a label check that matches the word anywhere (anchor it to its field);
    - (c) a fixture is a state the code can reach, built through the production function;
    - (d) set `.test-baseline` from CI's own collection, job by job, never from a local run
      that counts tests CI runs elsewhere.
    - **Evidence:** `F@7d40024`; `P@f7732f82`; `F@c2339d5`; `P@b7aaf98f`.
    - **Coverage:** the section exists ("A planted failure", "Every value its input states",
      `ci-workflows.md:60-77`). The four cases are new.

### D. `git-workflows` / `ci-speed`

13. **Floor the growth ratio:** judge growth only where one call costs above a measured
    minimum, such as 10 µs.
    - **Evidence:** `P@6f00a931`.
    - **Coverage:** partly, by "A timing test asserts on growth, not on milliseconds … with room
      for noise" (`ci-speed.md:65-67`).

### E. `git-workflows` / `releases-and-versions`

14. **Retrying a publish step:** a create or attest step that fails with an HTTP 5xx is retried
    a bounded number of times, after checking nothing was half-published.
    - **Evidence:** Platterpus lap 13 D3; `P:CHANGELOG.md:91`.
    - **Coverage:** not covered.
15. **Prove the release from the artifact consumers install,** with a planted negative.
    - **Evidence:** the fork's `git archive` build checked with `-Y`, and one changed CRC digit
      failing it (`F:round-38-lap-12.md:57`).
    - **Coverage:** not covered.
16. **The release commit rewrites every status line that names "next".**
    - **Evidence:** `P@470b1a48`.
    - **Coverage:** not covered. Low priority.

### F. `git-workflows` / `commits-and-pull-requests`

17. **Dependabot capitalizes "Bump".** A grammar that requires a lowercase summary rejects every
    Dependabot pull request, prefix or none. Say whether the check exempts the bot, or the
    prefix makes Dependabot lowercase it. Verify this against GitHub's documentation first.
    - **Evidence:** #450's annotation.
    - **Coverage:** partly, by "Give Dependabot a prefix … and its subjects pass too"
      (`commits-and-pull-requests.md:43-44`).

### G. `skillcheck` (`src/skillcheck`)

18. **A mode for a repository's own `.claude/skills/`:** no catalog, roadmap or README
    findings.
19. **A draft marker,** and what ends a draft.
20. **Checking a skill's script and tests beside it.**
21. **`--verify` separates "the source needs credentials" from "the quote is gone".**
    - **Evidence:** the fork's steward (`SKILL.md:38-50`), Platterpus's steward
      (`SKILL.md:142-151`) and `F:docs/READINESS-PLAN.md:104`.
    - **Coverage:** not covered. `checks.py:594` emits the catalog finding.

### H. `agent-context-files` (planned; backlog L39)

22. **Parallel agents in worktrees:** give each branch its own range of row numbers, restore
    citations from `-x` trailers, run the gate once on the combined tree, and limit the number
    of workers to the container's memory.
    - **Evidence:** `P:docs/session-log.md:73`, R136, `P@f9fc8104`, `P@29773877`, Platterpus
      lap 2 D3.
    - **Coverage:** partly, by L39: "Helpers run their targeted tests, and one integrator runs
      the suite". Extend it.

### I. `testing-patterns` / `documentation` (planned)

23. **A recorded limitation names the component that refused,** and is re-asked when that
    component changes.
    - **Evidence:** `P:docs/session-log.md:30`.
    - **Coverage:** partly, by the dated-facts convention.
24. **A pin move names the build it displaces in every set that held it as the pin.**
    - **Evidence:** `P:docs/session-log.md:18`.
    - **Coverage:** not covered.
25. **Read Git's paths with `-z`.**
    - **Coverage:** already covered. `rebasing-and-recovery.md:110-113`: "Comparing paths Git
      printed with stored paths, without `-z`. Git quotes a path holding a non-ASCII character
      …".

### J. The standard: records and archives (v0.49.0, `:2725-2760`)

26. **Neither repository has adopted the four questions on records,** and neither evidence
    branch has a root README.
    - **Coverage:** covered. Send it to both as an audit finding, not a change to the
      coordinator.
