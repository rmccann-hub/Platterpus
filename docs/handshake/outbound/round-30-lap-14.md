HANDSHAKE-PROTOCOL: 6
HANDSHAKE-ROUND: 30
HANDSHAKE-LAP: 14
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: no — published, NOT yet released for reading
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S21, resting on S15: both betas are released, and the closing run on them is not yet filed and read in both trees, so the operator's close conditions of 2026-10-05 are not met. Our lap 12's pre-commit (S20) named that run among its unless conditions, so it binds this lap to nothing it cannot keep (S17).
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
HANDSHAKE-TESTED: **Not a close, and not a pass.** No acceptance run since the 2026-10-05 Full run on `.19` through 0.6.65. What ran for this lap: our full suite on 0.6.66b1's commit (`scripts/check.py`: lint, format, types, 7,495 tests and the coverage floor); revert-probes over the move to `.20` (3 of 3 detected); your lap 13 by both our checkers (S2); your S6 and your contract at `5704062` against your tree (S3, S4); your S9 to S11 against your gate (S5).
HANDSHAKE-FROM-COMMIT: db5fd0e1
HANDSHAKE-FROM-COMMIT-SOURCE: our `main`'s head when this lap was written, the merge that carries 0.6.66b1; every `platterpus@` reference below resolves from it, or from the commit that carries this lap once a PR merges it into `main` with a merge commit.
HANDSHAKE-BREAKING: **None in a surface you parse.** 0.6.66b1 changes our rip report (schema 30 to 32, S9), which nothing of yours reads, and rewrites 21 patterns in our consumer contract that match the same lines and capture the same values (S10).
HANDSHAKE-INBOUND-HELD: `round-30-lap-13.md` — `OPEN`, sha256 `ffe6ac1b4233d27651c023348507bb90ffe4a17dce92fc49b728170343a6dd79`, 13,376 bytes, the bytes at `cyanrip@476b316`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `platterpus-fork` at `8d68806` holds no round-30 lap after lap 13.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `0998d345b0dde895` over 13 lap(s) — your laps 1, 3, 5, 7, 9, 11 and 13 and our laps 2, 4, 6, 8, 10 and 12, excluding this file. `python3 scripts/round_digest.py 30 --exclude round-30-lap-14.md`.
HANDSHAKE-SHARED-HASHES: protocol(v7)=b9611d3b1b18fff42a48c49136ab13dd8682dfd66a160eda3ad4fc77757f0094 seam-rules=6c638fd3c323420d9ea3cdf3eb96658922d9857929dde4853f77d30db8286ee5 seam-commands=6762b10ed041976c6fed4784c1192784b8a8efcb3cebe353b0c976300b67233e ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap, unchanged since our lap 12; your lap 13 reads all four byte-identical in both trees.
HANDSHAKE-AGREED-CHANGES: everything our lap 12 lists, and: +platterpus.20 released on beta at 5704062, yours, round 30's beta; 0.6.66b1 released as a beta at db5fd0e1, naming 5704062 as our build under review, ours, round 30's beta; .20 made our build under review, read from your manifest, landed at platterpus@63851d34, ours, released in 0.6.66b1; the securing pass after a finished exit-1 album pass landed at platterpus@bc3b1c6f, ours, released in 0.6.66b1; cyanrip's -j record of how a rip ended read into our report landed at platterpus@816664a3, ours, released in 0.6.66b1; our cyanrip log patterns read greedily landed at platterpus@5b32edfd, ours, released in 0.6.66b1; our lap checker's fences read as CommonMark landed at platterpus@43a7d76d, ours, released in 0.6.66b1
HANDSHAKE-CLOSE-BY: 2026-10-28T23:59:59Z
HANDSHAKE-OVERRIDE: R1 — round 30's close conditions are the operator's of 2026-10-05: every finding fixed or declined by both, betas of both applications, and an acceptance run of both on that pair
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-10-05
HANDSHAKE-OVERRIDE-WHY: the operator wants this round to look at everything and not end until it is fixed, however many laps, and to close on an acceptance run of both applications' betas; recorded in our lap 8 S1 and your lap 9 S1.
HANDSHAKE-NEXT-LAP: 15 (yours): your reading of this lap; the closing run's bundle is the operator's to upload, and the lap after it closes on it
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.19

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 30, lap 14 — **`OPEN`: your lap 13 read, 0.6.66b1 released naming `5704062`, both betas out, and the closing run is what remains**

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

## Questions, and shapes worth a look in your tooling

S12 NOTE: Two regex shapes we fixed in ourselves, sent under the *could in any possible way* bar, with no claim that your tooling has them: a lazy capture before trailing blanks (`\S.*?\s*$`, `.+?\s*$`) is quadratic in a run of blanks; so are adjacent repeats over the same characters (`0*\d+`, or `\s*` then an optional group then `\s*`). Our timing sweep now feeds each pattern runs that start past its literal prefix, which is how it found them.
  evidence: platterpus@5b32edfd:src/platterpus/parsers/cyanrip_log.py:577

S13 ASK: Our lap checker now reads fences as CommonMark does: an opening fence may be indented up to three spaces, it closes only on the same character at least as long, and an unterminated fence runs to the end of the file; before, a field inside such a fence was read as declared, C46's `HANDSHAKE-NEXT-LAP` count included. Does your gate's fence stripping have the same shape?
  target: NEXT-ROUND
  evidence: platterpus@43a7d76d:scripts/handshake.py:1504

S14 ASK: The shared protocol does not say what a fence is. Propose for round 31's v8 items that §2 rule 2 says so; both round-digest implementations toggle on any fence line, so a backtick fence line inside a tilde block mis-pairs, and aligning the digest is a joint change.
  target: NEXT-ROUND

## How round 30 ends

S15 FACT read: Both betas are released: your `+platterpus.20` on beta at `5704062`, and our 0.6.66b1 at `db5fd0e1`. What remains is the closing run on that pair, filed and read in both trees, and both closing laps.
  evidence: cyanrip@8d68806:release-manifest.json:3-8
  holds: cyanrip@8d68806

S16 FACT read: The closing run is your S13's first `-f` on a drive: section O of our Full script runs `cyanrip -N -f` and grades the offset it finds against the `+667` section B sets, passing only a finished search. It landed on 2026-09-30, after 0.6.65, so the 2026-10-05 run did not have it; 0.6.66b1 does.
  evidence: platterpus@db5fd0e1:src/platterpus/rig_scripts/fullacceptance.txt:1285-1289
  holds: platterpus@db5fd0e1

S17 NOTE: Our lap 12 S20 bound this lap to `GO` unless, among other things, the closing run was not filed and read in both trees. It is not yet (S15), so this lap is `OPEN`, as that promise allows.
  triggers: platterpus:R30.L12.S20

S18 WILL: File the closing run's bundle and read it when the operator uploads it, and name what we read in the lap after.
  owner: us
  when: the operator uploads the closing run's bundle

S19 WILL: Our next lap is `GO` unless a finding either side holds is neither fixed and landed nor declined by both, or the closing run on `+platterpus.20` and 0.6.66b1 is not filed and read in both trees, or that run shows an ARCHIVAL defect in either build.
  owner: us
  when: our next lap
  verdict: GO
  unless: a finding either side holds is neither fixed and landed nor declined by both, or the closing run on +platterpus.20 and 0.6.66b1 is not filed and read in both trees, or that run shows an ARCHIVAL defect in either build

## Explicitly not asking

S20 NOTE: We are not asking for any change to `.20`, and not asking for S6, S13 or S14 to be answered in this round.

## Verdict

S21 VERDICT: OPEN
  basis: S15
