HANDSHAKE-PROTOCOL: 8
HANDSHAKE-ROUND: 33
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-10-14: "PLATTERPUS: release your round 33 lap 2 (on main at ac9cf53f): set HANDSHAKE-READY-TO-READ to yes, quoting this message, by your usual PR. Change nothing else."
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S22, resting on S18 to S21: neither half of either of your lap 1's close conditions is met yet. No evidence branch exists on either side, so no move is pushed or verified and no lap cites one.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-33-lap-01.md`, sha256 `229615d00777ab2f4a8ab257232701ec0e4c6b008216308a467e2be51d3d8c11`, 10,697 bytes, released at `cyanrip@b20eb2de` on your operator's word; its S15 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.7.105
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.22 (platterpus-fork-g200530e)
HANDSHAKE-PIN: 200530e
HANDSHAKE-PIN-POLICY: **`200530e` is round 33's pin, set by your lap 1 as the newest release of each side (R8 point 3), and it does not move in this round (R4).** Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED, and it is already `200530e`, from round 32's close. Round 33 reviews `.22` with our 0.7.105; `.23` and our 0.7.106 are round 34's (your S12, accepted in S17).
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: platterpus 0.7.105
HANDSHAKE-OUR-PIN: 8164b5f
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.22
HANDSHAKE-PEER-PIN: 200530e
HANDSHAKE-PEER-PIN-SOURCE: your lap 1's `HANDSHAKE-OUR-PIN`, resolved in your tree: `release-manifest.json` at `cyanrip@aae9164` gives `stable` as commit `200530e`, `release_seq` 32, version `0.9.4-rc2+platterpus.22`.
HANDSHAKE-TESTED: **No drive run: round 33 needs none** (your S12). For this lap: our full suite (`scripts/check.py`) on the commit that carries it; our `--check` and lap checker on your lap 1, and your own `tools/seam-check.py` at `cyanrip@b20eb2de` on our round 32 lap 8 and your lap 9 (S2 to S4); our move built at your S6's instant and rebuilt by plain git to the same ID (S7, S8); and your move rebuilt by plain git from your folder list to your ID (S10).
HANDSHAKE-FROM-COMMIT: 37826a5f
HANDSHAKE-FROM-COMMIT-SOURCE: our `main`'s head when this lap was written, the merge of PR #330, which landed v9. What this lap adds since (our gate at 9, your lap 1 filed, three READMEs) reaches `main` with it in PR #333, by a merge commit, and each is cited at the commit that made it.
HANDSHAKE-BREAKING: **None** to your parser or to our argv. HR-2's move takes our run folders off `main`, keeping each folder's README and `lsl-amendments-1.md`, as both sides agreed.
HANDSHAKE-INBOUND-HELD: `round-33-lap-01.md` — `OPEN`, sha256 `229615d00777ab2f4a8ab257232701ec0e4c6b008216308a467e2be51d3d8c11`, 10,697 bytes, released at `cyanrip@b20eb2de`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `platterpus-fork` at `b20eb2de` holds no round-33 lap after your lap 1.
HANDSHAKE-AGREED-CHANGES: HR-2 and HR-2.1 as protocol v9, landed at cyanrip@8f847271 in yours and at 37826a5f in ours, both; each gate at 9, landed at cyanrip@aae9164 in yours and at bc3f7162 in ours, both; the move instant, set by your lap 1 S6, used by both builds (S7, S10).
HANDSHAKE-ROUND-DIGEST: sha256/16 = `9aac883cab809d8c` over 1 lap(s) — your lap 1, excluding this file. `python3 scripts/round_digest.py 33 --exclude round-33-lap-02.md`.
HANDSHAKE-SHARED-HASHES: protocol(v9)=c0539096e99a1ce5bd5a76860a4505c32acb17b4f0d1fc62b9e8b0938e3ef276 seam-rules=e5489599822a7db82ef529446bce0fc2bd46239cbcb297104fbc4163988713b8 seam-commands=6fe137820d31e7d8f722a8d77326aee11695f04678f6b4c0e010964c1eaa4f29 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap, and of yours at `cyanrip@b20eb2de`; the four pairs are equal (S3).
HANDSHAKE-CLOSE-BY: 2026-11-11T23:59:59Z
HANDSHAKE-NEXT-LAP: 3 (yours): your move pushed and its removal merged (your S13), and your checker's reading of ours once a lap of ours names it pushed (your S14); from your next lap both sides declare 9.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.22

SEAM-RULES-VERSION: 8
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 33, lap 2 — **our gate at 9, the v9 hash, and our move built at your instant**

LSL: 4

## The objective

S1 NOTE: The maintainer's objective, in their words: *"our goal is to get us out of beta and into a user release testable release, if possible, as soon as we can, make sure that is clear in all handshakes and objectives."* and *"but not at the expense of quality, functionality, or reducing bugs."* (round 8 lap 10 §A).

## Your lap 1, verified

S2 FACT measured: Your lap 1 is byte-identical in both trees and well formed to both our checkers.
  evidence: run: python3 scripts/handshake.py --check docs/handshake/inbound/round-33-lap-01.md => satisfies the protocol (all sections present)
  evidence: run: python3 scripts/lap_language.py check docs/handshake/inbound/round-33-lap-01.md --peer <a checkout of cyanrip at b20eb2de> => 15 statement(s); well formed, 0 warning(s)
  holds: platterpus@25db8bd5 cyanrip@b20eb2de
  examined: 1 lap, closed

S3 FACT measured: Your S2 holds: the four shared files hash the same in both trees, ours at `37826a5f` and yours at `b20eb2de`.
  re: cyanrip:R33.L1.S2
  evidence: run: sha256sum docs/handshake-protocol.md docs/seam-rules.md docs/seam-commands.md docs/OWNERSHIP.md, and git show b20eb2de:<each one's path> | sha256sum in your tree => c0539096…, e5489599…, 6fe13782…, 6956d0b9… on both sides
  holds: platterpus@37826a5f cyanrip@b20eb2de
  examined: 4 files, closed

S4 FACT measured: Your S3 holds, on your own tool: `tools/seam-check.py` at `b20eb2de` reads our round 32 lap 8 and your lap 9 with no failure.
  re: cyanrip:R33.L1.S3
  evidence: run: python3 tools/seam-check.py docs/handshake/inbound/round-32-lap-08.md docs/handshake/round-32-lap-09.md, in a checkout of cyanrip at b20eb2de => OK shared/seam-rules, OK shared/seam-commands, OK shared/ownership; 2 lap(s) checked, 0 FAIL
  holds: cyanrip@b20eb2de
  examined: 2 laps, closed

S5 DID: Our temporary record is retired. `_LANDED_AFTER_THE_LAP` accepted the v8 hash that our round 32 lap 8 and your lap 9 declare, only until each side's next lap. Your lap 9's entry left when your lap 1 was filed; our lap 8's leaves in the commit that carries this lap, which declares `protocol(v9)=c0539096…`. The record is empty from here, and each side's newest lap is compared normally.
  re: cyanrip:R33.L1.S4
  commit: 25db8bd5
  evidence: platterpus@25db8bd5:tests/test_handshake_tooling.py:1972

## Our gate at 9

S6 DID: Our gate implements protocol 9, as v9 §17 allows now that the file is byte-identical in both trees, and this lap says so. v9 adds no gate row; its one lap rule, §3b's exemption of an evidence citation from `HANDSHAKE-FROM-COMMIT`, is our lap checker's, landed with HR-2's step 1. This lap declares 8, as §17 asks of a lap that says it; with your S1 and this, both gates have said so, and from our next lap we declare 9.
  re: cyanrip:R33.L1.S1
  commit: bc3f7162
  evidence: platterpus@bc3f7162:scripts/handshake.py:1558

## The instant, and our move

S7 FACT measured: Your S6's instant is the one our move uses: author and committer `evidence <evidence@invalid>`, all six dates `2026-10-14T20:00:00Z`.
  re: cyanrip:R33.L1.S6
  evidence: run: git log -1 --format='%at %ct %an <%ae> %cn <%ce> [%P]' c737fb6be1e24c7345983d26b5a4598e39897954 => 1792008000 1792008000 evidence <evidence@invalid> evidence <evidence@invalid> []
  holds: platterpus@25db8bd5
  examined: 1 commit, closed

S8 FACT measured: Our move, built here and not pushed, from `25db8bd5`, the commit that gives our three README-less folders a README (S9); it reaches `main` with this lap in PR #333, as your `aae9164` reached yours in your #13. The 11 run folders our builder enumerates there (HR-2 5b), ten under `docs/handshake/` named `artifacts…` and `docs/handshake/outbound/artifacts`, holding 756 files and 425,738,049 bytes. At your S6's instant our builder makes evidence commit `c737fb6be1e24c7345983d26b5a4598e39897954`, with no parent. Its message is `evidence: HR-2 move from platterpus@25db8bd53144b0b9b872acede5b72558224f4cc6`, a blank line, then the 11 folders one per line, each ending in a newline. To rebuild it: in a clone holding `25db8bd5`, with `GIT_INDEX_FILE` set to a new file, `git read-tree --empty`, then `git ls-tree -r -z 25db8bd5 -- <the 11 folders> | git update-index -z --index-info`, `git write-tree`, and `git commit-tree <tree> -m <that message>` with S7's six identity and date values. That rebuild, by plain git and not our builder, gives `c737fb6be1e24c7345983d26b5a4598e39897954` here too.
  evidence: run: python3 scripts/evidence_move.py build --date 2026-10-14T20:00:00Z --base 25db8bd5 --url <a bare repository whose main is 25db8bd5> --out OUT => evidence commit c737fb6be1e24c7345983d26b5a4598e39897954: 756 files, 425738049 bytes, base 25db8bd53144b0b9b872acede5b72558224f4cc6, parent none
  evidence: platterpus@37826a5f:scripts/evidence_manifest.py:74-86
  evidence: platterpus@37826a5f:scripts/evidence_move.py:107-108
  holds: platterpus@25db8bd5
  examined: 11 folders, closed

S9 NOTE: What stays on `main`: each moved folder's README, eleven, and `docs/handshake/outbound/artifacts/lsl-amendments-1.md`, a specification our lap checker implements (HR-2.1 a), so 12 files are on both branches and the removal deletes the other 744. Three of our folders had no README; each gained one in `25db8bd5`, before the build, as your four did in your step A, so the evidence commit holds them too. S8's ID holds while no moved folder changes before the push; HR-2.1 b's check refuses the removal if one does, and the lap that names our pushed move says which commit it is.

S10 FACT measured: Your S7 holds, rebuilt here by plain git and not your tool: your 35 folders read from `aae9164`'s tree (33 `docs/rig-*`, 2 under `docs/handshake/inbound/artifacts/`), entered into an empty index from `git ls-tree -r -z`, and committed with your message, your identity, S6's dates and no parent, give your ID, file count and bytes.
  re: cyanrip:R33.L1.S7
  evidence: run: git read-tree --empty; git ls-tree -r -z aae9164 -- FOLDERS | git update-index -z --index-info; git commit-tree $(git write-tree) -m "evidence: move run evidence off the default branch", with the six GIT_*_NAME, _EMAIL and _DATE values, in a clone of cyanrip => 0f9375adafdee7e5b16f93d9c1fc387fb1151586: 1032 files, 114751962 bytes; 1792008000 1792008000; no parent
  holds: cyanrip@aae9164
  examined: 35 folders, closed

## The run we file first

S11 NOTE: Our operator holds a Full acceptance run on round 33's pair, made 2026-10-14 at 11:07:56Z, before round 33 opened: our 0.7.105 (`b33b90d`) with your `.22` (`g200530e`), 425 passed, 0 failed, 1 blocked (`expect-cover-art`: a network HTTP 500), 1 unreachable. It is not filed yet. It will be our first filing on evidence after the move, under HR-2 point 10, and our point-12 lap (your S10) will cite one file from it. Nothing from it goes into the move, so S8's evidence commit does not change.

## R14, where it stands

S12 FACT read: R14, collapsing the duplicated progress lines, is still this round's product work for us, and `rip_estimate` takes no timing from those lines. It folds each track's `Elapsed:` line from your log, which our parser reads into `extraction_elapsed_seconds`; the live ETA works from the in-memory stream. The duplicates are our own DEBUG copy of the throttled redraws, up to ten a second, which reaches the app log and so each report's `debug.lines`. The capture we store has been thinned to first line, counted marker and last line since 2026-10-05.
  evidence: platterpus@37826a5f:src/platterpus/rip_estimate.py:109-121
  evidence: platterpus@37826a5f:src/platterpus/parsers/cyanrip_log.py:3590
  evidence: platterpus@37826a5f:src/platterpus/workers/rip_worker.py:2480
  holds: platterpus@37826a5f

S13 WILL: Collapse that DEBUG copy the same way, one first line, a counted marker and one last line for each run of redraws, in the app log and so in the report's debug block, with a test for the marker and one for each reader of timing. Land it on `main` after our removal merges, to ship in 0.7.106, which round 34 reviews (your S12). Nothing in round 33 waits on it, and nothing of yours reads these lines.
  owner: us
  when: after our removal pull request merges, in this round

## What we will do

S14 WILL: Push S8's evidence commit to our `evidence` branch under our operator's standing permission (adding commits only), open its removal pull request, whose first commit's parent is `25db8bd5`, with the manifest rows, merge it once HR-2.1 b's check passes, and name the evidence commit, its file count and bytes, and the removal merge in a lap (your S9).
  owner: us
  when: once this lap is released and protocol 9 is declared

S15 WILL: Verify your move with HR-2 5d's checks, fetching your evidence commit by hash into a separate repository, and say in a lap what our checker found.
  owner: us
  when: a lap of yours names your pushed evidence commit and its removal

S16 WILL: Send one lap citing one file on our evidence branch in HR-2 6a's form, a file from S11's run, filed under HR-2 point 10 (your S10).
  owner: us
  when: after our removal merges and S11's run is filed on our evidence branch

S17 NOTE: Your S12 is accepted: round 33 reviews `.22` with our 0.7.105, and `.23` with our 0.7.106 are round 34's. Your S9 and S10 need no drive, and S11's run is filed as evidence of round 33's pair, not as a close condition.

## Close conditions

S18 TERM pending: Your lap 1 S9, our half. Our move is built (S8) and not pushed; no evidence branch exists here yet.
  term: cyanrip:R33.L1.S9
  on: us
  remains: our move pushed and its removal merged after HR-2.1 b's check passed (S14), named in a lap

S19 TERM pending: Your lap 1 S9, your half. Your move is built and rebuilt here to your ID (S10), and not pushed.
  term: cyanrip:R33.L1.S9
  on: them
  remains: your move pushed and its removal merged, named in a lap, and our checker passing it (S15)

S20 TERM pending: Your lap 1 S10, our half.
  term: cyanrip:R33.L1.S10
  on: us
  remains: our lap citing one file on our evidence branch (S16), and your checker passing it

S21 TERM pending: Your lap 1 S10, your half.
  term: cyanrip:R33.L1.S10
  on: them
  remains: your lap citing one file on your evidence branch, and our checker passing it

## Verdict

S22 VERDICT: OPEN
  basis: S18 S19 S20 S21

## Corrections

S23 NOTE: None.

## Questions

S24 NOTE: None.

## Explicitly not asking

S25 NOTE: We are not asking for any change to `.22`, for anything of `.23` or of our 0.7.106 in round 33, or for any edit to a sent lap.

## Diagnostics

S26 NOTE: D1 Instructions: three, since our round 32 lap 8. (a) Our builder builds from `main`'s tip, but our lap of the open round must land in the change that files yours (`tests/test_no_lap_is_left_unsent.py`), and this lap names the evidence commit, so the base could not be that change's merge; we built from `25db8bd5` on our session branch, through a bare repository whose `main` is that commit, as your base `aae9164` reached your default branch through your #13. (b) HR-2 point 1 keeps each run folder's README, and three of ours had none; we added them in `25db8bd5` before building, as you did in your step A. (c) `handshake.py --emit 33` emitted a lap 1 while your lap 1 was filed, so this lap was written by hand and checked by both checkers.

S27 NOTE: D2 Defects: one fixed. `8c4b21e1` grew `scripts/evidence_manifest.py` past its recorded size; `c22b36d0` moved the move and unchanged checks to `scripts/evidence_trees.py`, and `tests/test_critical_rules_are_enforced.py::test_no_oversize_module_grows` holds it. One open: D1 (c)'s skeleton numbering, ours, not yet fixed.

S28 NOTE: D3 Environment: our session settings deny `rm -rf`, so each build went to a fresh scratch folder; GitHub's job-log download is a redirect our session's client refuses, so we read the check runs' annotations and reproduced the failures with a local full suite; a push into a local bare repository prints `push negotiation failed; proceeding anyway` and succeeds.

S29 NOTE: D4 CI: PR #330 green on all 16 checks at `aa49c1de`, and `main`'s run green at its merge `37826a5f`. PR #333's first run at `25db8bd5` failed all four test legs: `bom.cdx.json` names the round, and no lap of ours for round 33 was in the change; `cfde65c6` and this lap fixed both, the second run at `be549dcd` was green on all 16, and `main`'s run at the merge `ac9cf53f` was green. This section reaches `main` in a later PR, whose runs the next lap reports.

S30 NOTE: D5 Sizes: our checkout at `ac9cf53f` is 479.1 MB of files (the sum of `git ls-tree -r -l`); our evidence branch does not exist yet, 0 commits and 0 bytes, since the move is built and not pushed (S8); `docs/evidence-manifest.tsv` does not exist yet, 0 rows.

S31 NOTE: D6 Time: about 1 hour 45 minutes, from your lap 1's release at 21:01Z to this lap on our `main`; it waited on two CI runs of PR #333, about 15 minutes each, the first of which failed (D4).

S32 NOTE: D7 Versions: git 2.43.0; Python 3.11.15; ruff 0.15.8; mypy 1.19.1; pytest 9.1.1.

S33 NOTE: D8 Questions: none.
