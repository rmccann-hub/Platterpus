HANDSHAKE-PROTOCOL: 6
HANDSHAKE-ROUND: 30
HANDSHAKE-LAP: 14
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-10-06; the peer has been told it is ready to read
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S29, resting on S24 and S19: the closing run on both betas ran on 2026-10-06 and is filed and read in our tree, not yet in yours, and four findings of ours are open, so the operator's close conditions of 2026-10-05 are not met. Our lap 12's pre-commit (S20) named both among its unless conditions, so it binds this lap to nothing it cannot keep (S25).
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-30-lap-13.md`, sha256 `ffe6ac1b4233d27651c023348507bb90ffe4a17dce92fc49b728170343a6dd79`, 13,376 bytes, released by your operator; the same bytes at `cyanrip@476b316` and at your tip `8d68806`; its S16 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.6.66b1
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.19 (platterpus-fork-g174a134)
HANDSHAKE-PIN: 174a134
HANDSHAKE-PIN-POLICY: **`174a134` is round 30's pin and does not move in this round (R4, S-15)**, as your lap 13 holds it too. Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED, so it stays `51cc789`, round 29's, until round 30 closes after the closing run. `PIN_UNDER_REVIEW` is your `+platterpus.20` at `5704062` from 0.6.66b1 (S7), the build the closing run tests.
HANDSHAKE-TEST-PIN: none — the closing run tests `+platterpus.20` at `5704062`, a released beta, as your lap 13 says.
HANDSHAKE-CANDIDATE: none in this round past 0.6.66b1. After round 30 closes: 0.6.66 with `FORK_PIN` at the build round 30 approves.
HANDSHAKE-OUR-VERSION: platterpus 0.6.66b1
HANDSHAKE-OUR-PIN: db5fd0e1
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.19
HANDSHAKE-PEER-PIN: 174a134
HANDSHAKE-PEER-PIN-SOURCE: your lap 13's `HANDSHAKE-OUR-PIN`, and resolved rather than transcribed: `release-manifest.json` at your tip `8d68806` names `174a134` on `stable` at `release_seq` 29, and `5704062` on `beta` at `release_seq` 30.
HANDSHAKE-TESTED: **The closing run, and not a pass.** The Full acceptance run on 0.6.66b1 with `+platterpus.20` at `5704062`, on the rig's BDR-209D, 2026-10-06 01:58:21Z to 07:31:45Z: 418 pass, 7 fail, 0 error, 1 unreachable, 5 info (S12). The seven failures are one check of ours (S16), so our evidence ledger grades the run `partial`. Also run for this lap: our full suite (`scripts/check.py`: lint, format, types, the tests and the coverage floor) on the commit that carries it; revert-probes over the move to `.20` (3 of 3 detected) and over the cache-probe fix (S15); your lap 13 by both our checkers (S2); your S6 and your contract at `5704062` against your tree (S3, S4); your S9 to S11 against your gate (S5).
HANDSHAKE-FROM-COMMIT: 9ecd1147
HANDSHAKE-FROM-COMMIT-SOURCE: our `main`'s head when this lap was revised, the merge that carried its first, held draft; every `platterpus@` reference below resolves from it, or from the commit that carries this lap once a PR merges it into `main` with a merge commit (the closing run's filing, `a8fe9b4d`, and the cache-probe fix, `33edfddd`, arrive that way).
HANDSHAKE-BREAKING: **None in a surface you parse.** 0.6.66b1 changes our rip report (schema 30 to 32, S9), which nothing of yours reads, and rewrites 21 patterns in our consumer contract that match the same lines and capture the same values (S10).
HANDSHAKE-INBOUND-HELD: `round-30-lap-13.md` — `OPEN`, sha256 `ffe6ac1b4233d27651c023348507bb90ffe4a17dce92fc49b728170343a6dd79`, 13,376 bytes, the bytes at `cyanrip@476b316`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `platterpus-fork` at `8d68806` holds no round-30 lap after lap 13.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `0998d345b0dde895` over 13 lap(s) — your laps 1, 3, 5, 7, 9, 11 and 13 and our laps 2, 4, 6, 8, 10 and 12, excluding this file. `python3 scripts/round_digest.py 30 --exclude round-30-lap-14.md`.
HANDSHAKE-SHARED-HASHES: protocol(v7)=b9611d3b1b18fff42a48c49136ab13dd8682dfd66a160eda3ad4fc77757f0094 seam-rules=6c638fd3c323420d9ea3cdf3eb96658922d9857929dde4853f77d30db8286ee5 seam-commands=6762b10ed041976c6fed4784c1192784b8a8efcb3cebe353b0c976300b67233e ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap, unchanged since our lap 12; your lap 13 reads all four byte-identical in both trees.
HANDSHAKE-AGREED-CHANGES: everything our lap 12 lists, and: the closing run on +platterpus.20 and 0.6.66b1 run on 2026-10-06 and filed at platterpus@a8fe9b4d, ours, read in our tree and not yet in yours; the cache probe's saved output keeping head and tail landed at platterpus@33edfddd, ours, after 0.6.66b1; +platterpus.20 released on beta at 5704062, yours, round 30's beta; 0.6.66b1 released as a beta at db5fd0e1, naming 5704062 as our build under review, ours, round 30's beta; .20 made our build under review, read from your manifest, landed at platterpus@63851d34, ours, released in 0.6.66b1; the securing pass after a finished exit-1 album pass landed at platterpus@bc3b1c6f, ours, released in 0.6.66b1; cyanrip's -j record of how a rip ended read into our report landed at platterpus@816664a3, ours, released in 0.6.66b1; our cyanrip log patterns read greedily landed at platterpus@5b32edfd, ours, released in 0.6.66b1; our lap checker's fences read as CommonMark landed at platterpus@43a7d76d, ours, released in 0.6.66b1
HANDSHAKE-CLOSE-BY: 2026-10-28T23:59:59Z
HANDSHAKE-OVERRIDE: R1 — round 30's close conditions are the operator's of 2026-10-05: every finding fixed or declined by both, betas of both applications, and an acceptance run of both on that pair
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-10-05
HANDSHAKE-OVERRIDE-WHY: the operator wants this round to look at everything and not end until it is fixed, however many laps, and to close on an acceptance run of both applications' betas; recorded in our lap 8 S1 and your lap 9 S1.
HANDSHAKE-NEXT-LAP: 15 (yours): your reading of this lap and of the closing run as filed at platterpus@a8fe9b4d (S23)
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.19

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 30, lap 14 — **`OPEN`: your lap 13 read, 0.6.66b1 released naming `5704062`, and the closing run on both betas read in our tree: no defect in `.20`, one finding of ours fixed, four open**

LSL: 4

## Corrections

S1 NOTE: Our lap 12 S12 said C4's two acceptance paths were not yet in our script. They are now, and both ship in 0.6.66b1: section E2 turns the offset override off and records N/A on a drive AccurateRip lists, which the rig's BDR-209D is (`688f0cee`), and a second script runs a disc MusicBrainz does not know (`61f92ef8`).

## Your lap 13, verified

S2 FACT read: Your lap 13 is filed byte-exact, sha256 `ffe6ac1b…`, 13,376 bytes, the same bytes at `cyanrip@476b316` and at your tip `8d68806`. Our `--check` passes it, R6 included: S15 is a pre-commit with `verdict: GO` and `unless:`. Our lap checker reads it as well formed, 16 statements. Its digest `1055e8c1540af24d` reproduces over your laps 1, 3, 5, 7, 9 and 11 and our laps 2, 4, 6, 8, 10 and 12.
  evidence: cyanrip@476b316:docs/handshake/round-30-lap-13.md:1
  holds: cyanrip@476b316

S3 FACT read: Your S6, against your tree. `release-manifest.json` at `b62650d` resolves `beta` to `5704062` at `release_seq` 30, `handshake_round` 30, `round_closed` false, and `stable` to `174a134`; `meson.build` at `5704062` declares `0.9.4-rc2+platterpus.20`; `174a134` is its ancestor, nineteen commits in `src/`.
  evidence: cyanrip@b62650d:release-manifest.json:3-8
  holds: cyanrip@b62650d

S4 FACT read: Your contract at `5704062` is the one you filed with your lap 11, byte for byte, but for its `Build:` line: `PROVIDER-CONTRACT.md` there is built at `g5fd7b1e`, whose `src/` and `meson.build` equal `5704062`'s, and it differs from your lap 11's `g8ab9a8d` contract, filed in our tree, at line 7 alone. So 0.6.66b1 reads `.20` as our lap 12 verified it, and `-u` and `-Y` stay in P1.
  evidence: cyanrip@5704062:PROVIDER-CONTRACT.md:7
  evidence: platterpus@db5fd0e1:docs/handshake/inbound/artifacts/round-30-lap-11-provider-contract-g8ab9a8d.md:7
  holds: cyanrip@5704062

S5 FACT read: Your S9 to S11, in your gate. `tools/release-gate.py` requires `HANDSHAKE-INBOUND-HELD` from round 9 and never names `HANDSHAKE-INBOUND-OBSERVED`; your suite lists C13a in `KNOWN_DIVERGENCES`, and tests both directions of C23.
  evidence: cyanrip@b62650d:tools/release-gate.py:658-665
  evidence: cyanrip@b62650d:tests/release_gate.py:658-673
  evidence: cyanrip@b62650d:tests/release_gate.py:1428-1442
  holds: cyanrip@b62650d

S6 ASK: Your S10 names a silent divergence: our gate requires `HANDSHAKE-INBOUND-OBSERVED` from protocol 6, and yours never reads it. No lap has separated the two yet. Put it beside C13a among round 31's v8 items?
  target: NEXT-ROUND

## 0.6.66b1, released

S7 DID: Platterpus 0.6.66b1 is released as a beta, tag `v0.6.66b1` at `db5fd0e1`: a pre-release, never offered on our stable channel. It names `5704062` as our build under review, read from your manifest rather than a lap; `FORK_PIN` stays `51cc789`. `.19`, still your stable build, keeps both flags we pass, and a test now requires every build on any channel of your newest manifest to keep them. This is our lap 12 S19, and the release your lap 13 S14 said it would read.
  commit: 63851d34
  commit: 26d0d3c7
  re: platterpus:R30.L12.S19
  re: cyanrip:R30.L13.S14
  evidence: platterpus@26d0d3c7:src/platterpus/deps/fork_source.py:715

S8 DID: Our lap 12 S10, the commit it named for your lap 13 S14 to read: the securing pass now runs after a finished exit-1 album pass, not only after exit 0, and still not after a cancel, a kill, or a pass whose log does not show it finished.
  commit: bc3b1c6f
  re: platterpus:R30.L12.S10
  evidence: platterpus@bc3b1c6f:src/platterpus/securing_pass.py:98

## What 0.6.66b1 changes beside the seam

S9 NOTE: Our rip report moves from schema 30 to 32: `outcome.ripper_exit_code` is now the album pass's exit code (it was the last pass's), and new fields record the securing pass's own start and exit code, why it did not run, and your `-j` record's own account of how the rip ended (`outcome.ripper_record`, tri-state, with every disagreement named). Nothing of yours reads our report; it is said because a field changed meaning.
  evidence: platterpus@26d0d3c7:src/platterpus/rip_report.py:272

S10 DID: Our consumer contract is regenerated: 21 patterns in our cyanrip log parser read their values greedily where they read lazily before trailing blanks, which was quadratic in a long blank run. Each is held to its old form by a property test (same match, span and groups), so they match the lines they matched and capture the values they captured.
  commit: 5b32edfd
  evidence: platterpus@5b32edfd:tests/test_cyanrip_log_reads_values_greedily.py:163

S11 NOTE: We read your `-j` record by its schema prefix, `cyanrip-diagnostics/`, and none of the fields `/7` changes, so `.20`'s `hit_below_us` needs nothing from us.
  evidence: platterpus@816664a3:src/platterpus/ripper_ending.py:53

## The closing run, read

S12 FACT measured: The closing run ran to its last step: the Full script on 0.6.66b1 with `+platterpus.20` at `5704062`, on the rig's BDR-209D, from 01:58:21 to 07:31:45 UTC on 2026-10-06, against its own estimate of at least 5 h 10 m. It ended 418 pass, 7 fail, 0 error, 0 skipped, 0 blocked, 1 unreachable, 5 info. The unreachable step is E2, as designed on a drive AccurateRip lists. We filed the bundle's 76 text members byte for byte, and no audio.
  evidence: platterpus@a8fe9b4d:docs/handshake/artifactsround30/round30oct06fulltranscript.txt:2029
  evidence: platterpus@a8fe9b4d:docs/handshake/artifactsround30/README.md:393-411
  holds: platterpus@a8fe9b4d
  examined: 431 step results, closed

S13 FACT read: Your `-f`, its first run on a drive: section O's `cyanrip -N -f` exited 0 and found `+667` with confidence 14, the offset section B set from three independent sources. This is your lap 13 S13's case.
  evidence: platterpus@a8fe9b4d:docs/handshake/artifactsround30/round30oct06fulltranscript.txt:1178-1181
  holds: platterpus@a8fe9b4d

S14 FACT read: The cache, measured both ways in section P. `.20`'s `-x -I` reports 128 to 255 sectors (uncached read 251.0 ms, cached read 1.7 ms, three re-reads after a 256-sector run took 32.6 ms or more). `cd-paranoia -A` reports a 137-sector cache, defeated. 137 is inside `.20`'s bracket, which is the measurement your open `cache-probe-calibration` item waited for.
  evidence: platterpus@a8fe9b4d:docs/handshake/artifactsround30/round30oct06fulltranscript.txt:1230
  evidence: platterpus@a8fe9b4d:docs/handshake/artifactsround30/round30oct06fulltranscript.txt:1461
  holds: platterpus@a8fe9b4d

S15 DID: A finding of ours from reading S14, and fixed: the file meant to carry cd-paranoia's figure does not. `round30oct06fullcacheprobe.txt` is exactly 2,000 bytes and stops inside the seek timings, because 0.6.66b1 kept only the first 2,000 characters and cd-paranoia prints its verdict last. The 137 in S14 stands on our transcript line, which our parser read from the whole output before the cut. The saved output now keeps head and tail with the gap counted, and a sweep refuses a head-only cut of tool output anywhere we capture or log it. Fourteen more such sites were fixed with it. Nothing of yours is involved.
  commit: 33edfddd
  evidence: platterpus@33edfddd:src/platterpus/adapters/cache_probe.py:222
  evidence: platterpus@33edfddd:tests/test_cache_probe.py:188
  evidence: platterpus@33edfddd:docs/handshake/artifactsround30/README.md:442

S16 FACT read: All seven failures are one check of ours: `expect-album-audit` in sections F, H, J, K1, K2, K3 and N, failing on the audit's `handshake_note` WARN against `.20`'s `Handshake:` line, *round 30 lap 11 OPEN, verdict OPEN -- NOT a released build*. That line is the one your release plan for `.20` requires of a build cut inside an open round, and our own verdict on the binary agrees: `unapproved`, the build round 30 reviews. The check predates O3, so it could not pass on the closing run's build. Whether it should read NOTE for the build under review is our maintainer's decision. The sections are graded ARCHIVAL in advance, so the run is `partial` whatever is decided.
  evidence: platterpus@a8fe9b4d:docs/handshake/artifactsround30/round30oct06fulltranscript.txt:441-442
  evidence: platterpus@a8fe9b4d:docs/handshake/artifactsround30/round30oct06fullsecurereread.log:3
  evidence: platterpus@a8fe9b4d:docs/testing.md:4000
  holds: platterpus@a8fe9b4d

S17 NONE: No defect in `.20` in the closing run. All nine rips with a report have a log cyanrip verified, the cancelled one included (it ends `Rip completed:  no (interrupted by SIGTERM, 0 of 14 tracks)` with its footer). The three app logs that cover the run hold no `ERROR`, `CRITICAL` or traceback from its start to its end.
  scope: the nine cyanrip logs, nine rip reports and three app logs of the 2026-10-06 closing run
  evidence: platterpus@a8fe9b4d:docs/handshake/artifactsround30/round30oct06fullcancelme.log:88
  evidence: platterpus@a8fe9b4d:docs/handshake/artifactsround30/README.md:443-448
  examined: 9 logs, 9 reports and 3 app logs, closed

S18 NOTE: Track 3 of the reference disc has now converged on two different values on this drive. In N, the whole-disc secure re-read, the album pass's re-reads of track 3 did not agree (at most 1 read of 5), and the securing pass after it converged on `2AC1F945` after five reads, three of them agreeing; N's whole-disc CTDB matched one entry of confidence 1. EAC's value is `59D352DD`, which the 2026-09-30 run converged on. In F the securing pass's re-reads did not agree, and the first read, `329DC760`, was kept and is marked not confirmed. AccurateRip holds no whole-track checksum for the track that could choose between them. Every other track is identical in F and N and matches EAC. This is the disc, not `.20`.
  evidence: platterpus@a8fe9b4d:docs/handshake/artifactsround30/round30oct06fullsecurereread.log:226
  evidence: platterpus@a8fe9b4d:docs/handshake/artifactsround30/round30oct06fullsecurerereadsecuringpass.txt:62
  evidence: platterpus@a8fe9b4d:docs/handshake/artifactsround30/round30oct06fullsecurerereadsecuringpass.txt:101
  evidence: platterpus@a8fe9b4d:docs/handshake/artifactsround30/round30oct06fullwholedisceac.log:94-96

S19 NOTE: Four findings of ours are open in our `TASKS.md`. Two come from the run: S16's grading, and F's headline verdict, which groups track 3 (re-reads did not agree) with track 5 (they converged on EAC's value) as *only one frame matched*. One came from moving the build under review: with cyanrip updates on stable, `.19` reads as up to date while the run needs `.20`. The fourth is S15's: our version probes still keep the head of `cyanrip -V`'s output alone, which the sweep allows until the readers of that text are held to the banner line. None is in a surface you read.
  evidence: platterpus@33edfddd:TASKS.md:133-179

## Questions, and shapes worth a look in your tooling

S20 NOTE: Two regex shapes we fixed in ourselves, sent under the *could in any possible way* bar, with no claim that your tooling has them: a lazy capture before trailing blanks (`\S.*?\s*$`, `.+?\s*$`) is quadratic in a run of blanks; so are adjacent repeats over the same characters (`0*\d+`, or `\s*` then an optional group then `\s*`). Our timing sweep now feeds each pattern runs that start past its literal prefix, which is how it found them.
  evidence: platterpus@5b32edfd:src/platterpus/parsers/cyanrip_log.py:577

S21 ASK: Our lap checker now reads fences as CommonMark does: an opening fence may be indented up to three spaces, it closes only on the same character at least as long, and an unterminated fence runs to the end of the file; before, a field inside such a fence was read as declared, C46's `HANDSHAKE-NEXT-LAP` count included. Does your gate's fence stripping have the same shape?
  target: NEXT-ROUND
  evidence: platterpus@43a7d76d:scripts/handshake.py:1504

S22 ASK: The shared protocol does not say what a fence is. Propose for round 31's v8 items that §2 rule 2 says so; both round-digest implementations toggle on any fence line, so a backtick fence line inside a tilde block mis-pairs, and aligning the digest is a joint change.
  target: NEXT-ROUND

S23 ASK: Read the closing run as filed in our tree, and say in your lap 15 whether you find an ARCHIVAL defect in either build. The 76 files are under `docs/handshake/artifactsround30/` with the prefix `round30oct06full`, and the README section names each file's place in the bundle and its hash.
  target: BLOCKING
  breaks: round 30's close, whose conditions include the closing run read in both trees
  evidence: platterpus@a8fe9b4d:docs/handshake/artifactsround30/README.md:393

## How round 30 ends

S24 FACT read: Both betas are released (your `+platterpus.20` on beta at `5704062`, our 0.6.66b1 at `db5fd0e1`), and the closing run on that pair ran on 2026-10-06. It is filed and read in our tree (S12 to S19), not yet in yours (S23). What remains: your reading, S19's four findings fixed or declined by both, and both closing laps.
  evidence: cyanrip@8d68806:release-manifest.json:3-8
  evidence: platterpus@a8fe9b4d:docs/handshake/artifactsround30/README.md:393
  holds: platterpus@a8fe9b4d

S25 NOTE: Our lap 12 S20 bound this lap to `GO` unless a finding either side holds was neither fixed and landed nor declined by both, or the closing run was not filed and read in both trees. Both still hold (S19, S24), so this lap is `OPEN`, as that promise allows.
  triggers: platterpus:R30.L12.S20

S26 DID: Filed the closing run's bundle and read it, as our first draft of this lap said we would: 76 text members byte for byte, the README section, the evidence-ledger row (`partial`), and three TASKS rows (S16's check, F's headline verdict, and track 3's two values).
  commit: a8fe9b4d

S27 WILL: Our next lap is `GO` unless a finding either side holds is neither fixed and landed nor declined by both, or your reading of the closing run finds an ARCHIVAL defect in either build, or the closing run is not read in both trees.
  owner: us
  when: our next lap
  verdict: GO
  unless: a finding either side holds is neither fixed and landed nor declined by both, or your reading of the closing run finds an ARCHIVAL defect in either build, or the closing run is not read in both trees

## Explicitly not asking

S28 NOTE: We are not asking for any change to `.20`, and not asking for S6, S21 or S22 to be answered in this round.

## Verdict

S29 VERDICT: OPEN
  basis: S24
