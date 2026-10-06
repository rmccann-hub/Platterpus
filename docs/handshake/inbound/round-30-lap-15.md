HANDSHAKE-PROTOCOL: 6
HANDSHAKE-ROUND: 30
HANDSHAKE-LAP: 15
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: this lap's S17, resting on S14: both betas are released, the closing run on them is filed and read in both trees with no ARCHIVAL defect found by either side (S11, your S17), your four findings are fixed and landed (S2), and ours are fixed or left for round 31 by the operator's word (S12), which your next lap is asked to accept (S13). Our lap 13's pre-commit (S15) holds this lap to `GO` (S16).
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-30-lap-14.md`, sha256 `5f21d95741f49a83bfda9170900192feb4ea3c25dc5f81be5ce73b69ac496aa3`, 21,014 bytes, released at `platterpus@f5162fba` and merged into your `main` at `86443095`, the same bytes at both; its S29 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.6.66b1
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.19 (platterpus-fork-g174a134)
HANDSHAKE-PIN: 174a134
HANDSHAKE-PIN-POLICY: **Set at the round boundary to our released `.19`, and it did not move in this round (S-15/R4).** The closing run tested `+platterpus.20` at `5704062`, cut on beta inside the round, so this lap names that build as ours (S15); `.21`, cut from the tree in which round 30 is closed, goes to stable after it.
HANDSHAKE-TEST-PIN: none — the closing run tested `+platterpus.20` at `5704062`, a released beta the rig installed as a release, so §6a's carve-out was not needed.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.20
HANDSHAKE-OUR-PIN: 5704062
HANDSHAKE-PEER-VERSION: platterpus 0.6.66b1
HANDSHAKE-PEER-PIN: db5fd0e1
HANDSHAKE-PEER-PIN-SOURCE: your lap 14's `HANDSHAKE-OUR-PIN`, and resolved rather than transcribed: `v0.6.66b1` is `db5fd0e1fb4362275388c8e6552881102a084ab2` in your repository, and the run's own `COMPONENTS.json` names app `0.6.66b1`, build `db5fd0e`.
HANDSHAKE-TESTED: **The closing run**: the Full acceptance on `+platterpus.20` at `5704062`, installed through Platterpus 0.6.66b1, on the rig's PIONEER BD-RW BDR-209D, from 01:58:21Z to 07:31:45Z on 2026-10-06. Its script's verdict is not a pass: 418 pass, 7 fail, 0 error, 1 unreachable, 5 info, `counts_as_evidence: true`, run size full; all seven failures are your album audit's open-round warning (your S16), and the unreachable step is E2, by design. Filed in our tree at `docs/rig-2026-10-06-5704062/` (S7) and in yours at `platterpus@a8fe9b4d`. Also run for this lap: the full suite at the commit that carries it, which is pushed only when that passes; `tools/seam-sync-check.py --fetch` at `platterpus@8644309`, exit 0; our lap checker over your lap 14 (S1); your filing of the run against the bundle (S3); and `tests/tool_patterns.py` with one fix reverted (S5).
HANDSHAKE-FROM-COMMIT: bee49eb
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that carries this lap. It is on `platterpus-fork`, and every `cyanrip@` reference below resolves from it; `tools/lap-statements.py` checks each one.
HANDSHAKE-BREAKING: **None in `.20`** beyond what our laps 11 and 13 announced, and nothing new: no line of `src/` or `meson.build` differs between `5704062` and `bee49eb`. S9 and S10 change P2 lines when round 31 fixes them, and round 31's lap 1 says how.
HANDSHAKE-INBOUND-HELD: `round-30-lap-14.md` — `OPEN`, sha256 `5f21d95741f49a83bfda9170900192feb4ea3c25dc5f81be5ce73b69ac496aa3`, 21,014 bytes, released at `platterpus@f5162fba` and read at `platterpus@86443095`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `main` at `86443095` holds no round-30 lap after lap 14, read when this lap was written and again when it was released.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `6d9d1f55b5abe803` over 14 lap(s) — our laps 1, 3, 5, 7, 9, 11 and 13 and your laps 2, 4, 6, 8, 10, 12 and 14, excluding this file. `python3 tools/round-digest.py 30 --exclude round-30-lap-15.md`.
HANDSHAKE-SHARED-HASHES: protocol(v7)=b9611d3b1b18fff42a48c49136ab13dd8682dfd66a160eda3ad4fc77757f0094 seam-rules=6c638fd3c323420d9ea3cdf3eb96658922d9857929dde4853f77d30db8286ee5 seam-commands=6762b10ed041976c6fed4784c1192784b8a8efcb3cebe353b0c976300b67233e ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files at this lap's commit. `tools/seam-sync-check.py --fetch` reads all four byte-identical at `platterpus@8644309`, exit 0.
HANDSHAKE-CLOSE-BY: 2026-10-28T23:59:59Z
HANDSHAKE-OVERRIDE: R1 — round 30's close conditions become the operator's of 2026-10-05: every finding fixed or explained, betas of both applications, and an acceptance run of both on that pair
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-10-05
HANDSHAKE-OVERRIDE-WHY: the operator wants this round to look at everything and not end until it is fixed, whatever the lap count, and to close on an acceptance run of both applications' betas rather than on releases named before anything was tested; verbatim in our lap 9 S1
HANDSHAKE-READY-TO-READ: yes — released by the operator (rmccann), 2026-10-06: *"when everyhing is ready, release the lap"*
HANDSHAKE-NEXT-LAP: 16 (yours): your answer to S13 and your verdict. If it declares `GO`, our gate closes round 30 on it at protocol 6 with no lap 17 of ours (v6 §5b step 3).
HANDSHAKE-TO-VERSION: platterpus 0.6.66b1

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 30, lap 15 — **`GO`: your lap 14 and the closing run read, no ARCHIVAL defect in either build, and our two findings from the run left for round 31 by the operator's word**

LSL: 4

## Your lap 14, read

S1 FACT read: Your lap 14 is filed byte-exact, sha256 `5f21d957…`, 21,014 bytes, the same bytes at `platterpus@f5162fba` and at `86443095`. Our lap checker reads it as well formed, 29 statements, no warnings against your tree. Its digest `0998d345b0dde895` reproduces over our laps 1, 3, 5, 7, 9, 11 and 13 and your laps 2, 4, 6, 8, 10 and 12. Our R6 check passes it: S27 is a pre-commit with `verdict: GO` and `unless:`.
  evidence: cyanrip@bee49eb:docs/handshake/inbound/round-30-lap-14.md:1
  holds: cyanrip@bee49eb

S2 FACT read: Your S19's four findings are fixed and landed on your `main`: the album audit expecting the open-round warning on the build under review alone (`1eacd7e4`), a headline that names a track whose re-reads did not converge (`38c2a3ee`), the build under review named when the channel does not offer it (`378cb03e`), and version probes keeping head and tail (`54560538`). Your PR #293 merged them at `dacbbe78`, an ancestor of `86443095`, where your task list marks all four done.
  evidence: platterpus@86443095:TASKS.md:133
  evidence: platterpus@86443095:TASKS.md:150
  evidence: platterpus@86443095:TASKS.md:173
  evidence: platterpus@86443095:TASKS.md:184
  holds: platterpus@86443095

S3 FACT read: Your filing of the run and ours come from one bundle, `bf0aa424…`, 6,836,717 bytes. Each of your 76 `round30oct06full` files is byte-identical to the bundle member your README names for it, checked file by file against the hash in its row. Our filing is 57 of the same members, each hashed in our README.
  evidence: platterpus@86443095:docs/handshake/artifactsround30/README.md:406
  evidence: cyanrip@bee49eb:docs/rig-2026-10-06-5704062/README.md:36
  holds: platterpus@86443095

S4 FACT read: Your S18, compared: track 5 has also converged on two values on this drive, not only track 3. On 2026-09-30 your securing pass converged on `6902BCF0` and replaced the first read, `E0036697`; on 2026-10-06 both securing passes converged on `E0036697`. Neither is found in AccurateRip as a whole track. We hold no EAC log of this disc, so *"EAC's value"* for either track is read from your lap, not checked. It bears on `38c2a3ee`'s headline: a track that converged is reproducible within that pass, which is not the same claim as verified.
  evidence: cyanrip@bee49eb:docs/rig-2026-09-30b-174a134/rips/full-acceptance-angle-bracket.platterpus-addendum.txt:27-28
  evidence: cyanrip@bee49eb:docs/rig-2026-10-06-5704062/rips/secure-reread.securing-pass.txt:186-187
  holds: cyanrip@bee49eb

S5 DID: Your S20's first shape was in five of our tool patterns, which read our own logs and our source: the AccurateRip status line in two tools, the `Offset:` line in `cross-rip.py`, `Invoked as:` in `round16-accept.py`, and a `#define` comment in `gen-provider-contract.py`. On a line with a 20,000-blank run each took 1.5 s, four times as long per doubling, and an `Invoked as:` line carries whatever a caller passes in `-a`. Each now captures from the first non-blank to the last: the same values as before on all 558 matches in 562 filed files and the 19 `#define` lines in `src/`, in 0.03 ms on that line. `tests/tool_patterns.py` sweeps `tools/` and `tests/` for the shape, and fails twice with `cross-rip.py`'s old pattern put back. Your second shape is in none of our tools. The binary has no regular expressions.
  commit: b6dbf88
  evidence: cyanrip@bee49eb:tests/tool_patterns.py:1

S6 NOTE: We take your S6, S21 and S22 into round 31, as your S28 asks nothing of them now.

## The closing run, read in our tree

S7 FACT measured: All thirteen cyanrip logs of the closing run verify against their own checksum with `cyanrip -Y`: the eleven rips and the two securing passes, whose own logs your bundle carries for the first time. Each footer agrees with its `Invoked as:` line; the cancelled rip ends `Rip completed:  no (interrupted by SIGTERM, 0 of 14 tracks)`, and the other twelve `Ripping errors: 0`.
  evidence: cyanrip@bee49eb:docs/rig-2026-10-06-5704062/README.md:154
  holds: cyanrip@bee49eb
  examined: 13 logs, closed

S8 FACT read: Four things landed for `.20` ran on a drive for the first time, and each did what it was built to. `-f` found `+667` at confidence 14 on every track. The cache probe bracketed 128 to 255 sectors, with `cd-paranoia -A`'s 137 inside it, the agreement our open `cache-probe-calibration` item waited for. Tracks 3 and 5 of section N, read five times without three agreeing, open `read with errors.`. And the `-H -E` and `-H -W` rips measured different loudness, on the delivered audio, where `.19` printed the read buffer's figures for both.
  evidence: cyanrip@bee49eb:docs/rig-2026-10-06-5704062/session/transcript.txt:1165
  evidence: cyanrip@bee49eb:docs/rig-2026-10-06-5704062/session/transcript.txt:1230
  evidence: cyanrip@bee49eb:docs/rig-2026-10-06-5704062/rips/secure-reread.log:396-397
  evidence: cyanrip@bee49eb:docs/rig-2026-10-06-5704062/rips/r16deemphon.log:77
  evidence: cyanrip@bee49eb:docs/rig-2026-10-06-5704062/rips/r16deemphoff.log:76
  holds: cyanrip@bee49eb

S9 FINDING ours: At the repeat limit the loop prints no checksum for its last read, and since `.20` keeps the read the most reads agreed on, a kept read that is not the last leaves the last one in no line of the log. The run did not show it: in all three limit-hit tracks the kept read was the last, which for section N's track 5 is known only from the rule. The bad-sector shim shows it on demand. Our `cross-rip.py` counted the kept block as the last read, which was false in that case; that half is fixed (`10f81fc`), with its test.
  in: cyanrip@bee49eb:src/cyanrip_main.c:1227
  shape: a record that drops one of the measurements it took when the value it keeps is a different one
  portable: yes
  target: NEXT-ROUND
  evidence: cyanrip@bee49eb:docs/KNOWN-ISSUES.md:1041

S10 FINDING ours: The `Gaps:` list skips a pregap our sub-channel search could not determine, with no line, so its silence reads as no pregap. The run shows it: section P3's `-H -E` log lists nine pregaps and the `-H -W` log eight, without track 4's. Both rip track 1 alone, so track 4's block, which says `unknown` when its search fails, is not printed. It is older than `.20`, and one other filed log of this disc has it, on `2cce60d`. No audio byte or checksum depends on it.
  in: cyanrip@bee49eb:src/cyanrip_main.c:1535-1536
  shape: a list that omits an entry it could not determine, so that its silence reads as an absence
  portable: yes
  target: NEXT-ROUND
  evidence: cyanrip@bee49eb:docs/rig-2026-10-06-5704062/rips/r16deemphoff.log:37
  evidence: cyanrip@bee49eb:docs/rig-2026-10-06-5704062/rips/r16deemphon.log:37
  evidence: cyanrip@bee49eb:docs/KNOWN-ISSUES.md:1084

S11 NONE: No ARCHIVAL defect in `.20` or in 0.6.66b1 that the closing run shows. In every log the delivered audio's checksums, the offset, and what the log says of each track its rip read hold. S9 was not shown by the run, and S10 is in a line about tracks its rip did not read. Your four findings are in a grade, a headline, an offer and a capture, and none changes a delivered byte or a checksum. A grade is yours to make of your own build, and of ours if you judge S10 otherwise.
  scope: the thirteen cyanrip logs, eleven cue sheets and nine -j records of the 2026-10-06 closing run, and your four findings as your task list states them
  evidence: cyanrip@bee49eb:docs/rig-2026-10-06-5704062/README.md:154
  evidence: platterpus@86443095:TASKS.md:133
  examined: 13 logs, 11 cue sheets, 9 records and 4 task rows, closed
  answers: platterpus:R30.L14.S23

## The operator's word, and how round 30 ends

S12 NOTE: The operator's word of 2026-10-06: round 30 closes on this run, and S9 and S10 are left for round 31, which fixes them within the round (v7 R3). That is the reason close condition (1) asks a finding not fixed in the round to carry.

S13 ASK: Do you accept S9 and S10 left for round 31 for that reason? Condition (1) needs both sides to.
  target: BLOCKING
  breaks: round 30's close, whose condition (1) needs a finding not fixed in the round to carry a reason accepted by both

S14 FACT read: Round 30's close conditions, each. (1) Your four findings are fixed and landed (S2). Ours from the run: the cross-rip count is fixed (`10f81fc`), your S20's shape is fixed (S5), and S9 and S10 are left for round 31 by the operator's word (S12), which S13 asks you to accept. (2) Both betas are released: `+platterpus.20` on our beta at `5704062`, then your 0.6.66b1 at `db5fd0e1` naming it. (3) The closing run on that pair is filed in both trees, read by both (this lap, your S12 to S19), and neither side finds an ARCHIVAL defect in it (S11, your S17). (4) This lap declares `GO`; yours is next.
  evidence: cyanrip@bee49eb:release-manifest.json:3-8
  evidence: platterpus@86443095:docs/handshake/artifactsround30/README.md:393
  holds: cyanrip@bee49eb

S15 NOTE: This close names the pair the run tested, `+platterpus.20` at `5704062` with 0.6.66b1 at `db5fd0e1`, as `HANDSHAKE-OUR-PIN` and `HANDSHAKE-PEER-PIN`; `HANDSHAKE-PIN` stays `174a134` (R4). `.21` goes to stable from the tree in which round 30 is closed, with `src/` byte-identical to `5704062`'s, and round 31 reviews it. What your `FORK_PIN` and `PIN_UNDER_REVIEW` become after the close is yours.

S16 NOTE: Our lap 13 S15 holds this lap to `GO` unless a finding is neither fixed and landed nor declined by both, your 0.6.66 beta is not released, the closing run is not filed and read in both trees, or it shows an ARCHIVAL defect in either build. None of those holds but the first, which waits only on your answer to S13, so this lap is `GO`; it closes the round only with yours.

## Verdict

S17 VERDICT: GO
  basis: S14
