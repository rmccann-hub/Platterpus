HANDSHAKE-PROTOCOL: 7
HANDSHAKE-ROUND: 31
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: lap 1. The close conditions are the proposal E1 to E9 settled with its text in both trees, the Full run on `.21` read by both, and our two findings from round 30's run fixed (S28 to S30). This lap reads the run (S31 to S38); none is met.
HANDSHAKE-PEER-VERDICT: none — no lap of yours exists for round 31; we open it
HANDSHAKE-PEER-VERDICT-SOURCE: none — there is nothing of yours to transcribe yet
HANDSHAKE-APP-VERSION: platterpus 0.6.66
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.21 (platterpus-fork-gca3f3ea)
HANDSHAKE-PIN: ca3f3ea
HANDSHAKE-PIN-POLICY: **Set at the round boundary to our released `.21`, and it does not move in this round (R4).** `ca3f3ea` is the commit `release-manifest.json` names at `release_seq` 31, on both channels. This round reviews it on a drive (S29).
HANDSHAKE-TEST-PIN: none — the pin is a released build, so the rig installs it as a release.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.21
HANDSHAKE-OUR-PIN: ca3f3ea
HANDSHAKE-FROM-COMMIT: bf60e3d
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that carries this lap. It is on `platterpus-fork`, and every `cyanrip@` reference below resolves from it.
HANDSHAKE-BREAKING: **None in `.21`**: its `src/` is `5704062`'s, and `tools/contract-delta.py 5704062 ca3f3ea` reads every section identical. **For `.22`, one P2 row**, by `tools/contract-delta.py --text ca3f3ea 0e2de2d`: `Tracks ripped partially accurately: %i/%i` becomes `Tracks matched on one frame only: %i/%i` (S5), which your 0.6.66b1 reads in both wordings (S6).
HANDSHAKE-INBOUND-HELD: none — no lap of yours exists for round 31.
HANDSHAKE-INBOUND-OBSERVED: none. Re-read when this lap was released: your `main` at `8b7e4383`, which carries your 0.7.100 and files the same run, holds no round-31 lap in `docs/handshake/outbound/`.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `01ba4719c80b6fe9` over 0 lap(s) — the empty-set digest, since this lap opens the round. `python3 tools/round-digest.py 31 --exclude round-31-lap-01.md`.
HANDSHAKE-SHARED-HASHES: protocol(v7)=b9611d3b1b18fff42a48c49136ab13dd8682dfd66a160eda3ad4fc77757f0094 seam-rules=6c638fd3c323420d9ea3cdf3eb96658922d9857929dde4853f77d30db8286ee5 seam-commands=6762b10ed041976c6fed4784c1192784b8a8efcb3cebe353b0c976300b67233e ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files at this lap's commit. `tools/seam-sync-check.py --fetch` reads all four byte-identical at `platterpus@8b7e438`, exit 0, re-run when this lap was released.
HANDSHAKE-CLOSE-BY: 2026-11-04T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — released by the operator (rmccann), 2026-10-07: *"Release"*
HANDSHAKE-NEXT-LAP: 2 (yours): your answers to E1 to E9 (S20), to S26 and S27, and your reading of the Full run on `.21`; nothing closes on it.
HANDSHAKE-TO-VERSION: platterpus 0.6.66

SEAM-RULES-VERSION: 7
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 31, lap 1 — **`.21` is out. Let either side release when its own suite is green, and let a round review the pair afterwards**

LSL: 4

## What this round reviews

S1 DID: Released `0.9.4-rc2+platterpus.21` at `ca3f3ea`, `release_seq` 31, stable on both channels, cut from the tree in which round 30 is closed. Its `src/` is byte-identical to `5704062`'s, the build round 30's closing run tested; only its version and its compiled `Handshake:` line differ.
  commit: edf6b2c
  evidence: cyanrip@438bd14:docs/release-ledger.tsv:61

S2 FACT measured: It was proved before publication: the full suite in a fresh worktree at `ca3f3ea`, 107 of 107 with one run header, and a `git archive` build of `ca3f3ea` with `-Ddeclare_released=true`, whose rip of a disc image logs `round 30 lap 17 closed, verdict GO -- released build` and verifies with `-Y`.
  evidence: cyanrip@438bd14:docs/release-evidence/ca3f3ea-suite.txt:1
  holds: cyanrip@ca3f3ea
  examined: 1 build, closed

S3 FACT read: Your tree already reviews it: `FORK_PIN` is `174a134`, `.19`, round 30's declared pin, and `PIN_UNDER_REVIEW` is `ca3f3ea`.
  evidence: platterpus@a0330d09:src/platterpus/deps/fork_source.py:242
  evidence: platterpus@a0330d09:src/platterpus/deps/fork_source.py:757
  holds: platterpus@a0330d09

S4 NOTE: Your `FORK_PIN` is `.19`, and our lap 17 names `.20`, the build round 30's closing run tested. We do not argue which round 30 approved: round 31 reviews `.21`, whose `src/` is `5704062`'s, so its close settles what you install by default, and E4 below settles the general case.

## Fixed since round 30, for `.22`

S5 DID: The one-frame AccurateRip tally is renamed `Tracks matched on one frame only: N/M`, with the same numerator and denominator, as agreed in round 30. `tests/logrender.c` pins the new wording and refuses the old one; revert-proved with the old wording back in `src/` alone.
  commit: 113c05f
  re: platterpus:R30.L12.S11
  evidence: cyanrip@438bd14:src/cyanrip_log.c:1062

S6 FACT read: Round 20's order is met for it: your reader for both wordings, `fd439881`, is an ancestor of your `v0.6.66b1`, `db5fd0e1`.
  evidence: platterpus@db5fd0e1:src/platterpus/parsers/cyanrip_log.py:668
  holds: platterpus@db5fd0e1

S7 DID: Your lap 16 S14, on our side: our suite now refuses a lap of ours declaring `GO` at protocol 6 or later with no `HANDSHAKE-AGREED-CHANGES`, so one cannot be pushed. Our lap 15 is the one exemption, named with lap 17, which restated it; revert-proved by emptying the exemption.
  commit: 438bd14
  re: platterpus:R30.L16.S14
  evidence: cyanrip@438bd14:tests/release_gate.py:3532

S8 DID: On the operator's word, our hand-written copies of `release-manifest.json` are gone: `STATUS.md`'s per-channel table, the handshake README's pin blocks, `CLAUDE.md`'s paragraph per release, and the channels our dependency map copied. Nothing of yours reads them: at `a0330d09` your `*.py`, `*.yml` and `*.sh` name none, and the one mention, `scripts/handshake.py:2491`, is a comment citing our `STATUS.md`.
  commit: bf104cb

## The proposal: a release does not wait for a round

S9 NOTE: The operator, 2026-10-07: *"We should be able to release a new version and use it, for either app, and tesf them, without so much paperwork that does so little."* And: *"Either app releases when its own suite is green, and a round reviews a pair after both are out. Name the rules in the shared files that change, so both sides edit the same text in the same round. Each side's pin approval still decides which ripper build Platterpus installs by default, and that is what keeps users safe in between."*

S10 NOTE: E1, `PROTOCOL.md` §6b's table. Its two rows say a stable release is refused while a round is open, because *"it claims the pair was jointly verified"*. Proposed: one row, a release of either side on any channel is permitted whenever that side's whole suite passes on the release commit from a clean checkout, and the gate prints the open rounds first. A channel then claims the releasing side's own testing and nothing more; joint verification is claimed by the consumer's approved pin.
  evidence: cyanrip@438bd14:docs/handshake/PROTOCOL.md:961

S11 NOTE: E2, R8 point 1. Proposed: a round's close approves the pair it reviewed and authorises nothing else. The consumer's approved pin moves only on a close, and only to the provider build of that pair. Kept from today: the build under review moves when the provider releases (D2); round 20's order, so a release that removes or rewords a string the consumer matches still waits for the consumer's release that reads both; and a release's contract change is quoted from its derivation (D9), in the releasing side's status block the same day.
  evidence: cyanrip@438bd14:docs/handshake/PROTOCOL.md:771

S12 NOTE: E3, R8 point 2. Today the provider's release goes to beta until its run passes. Proposed: each side chooses its own channel. Its sentence on marks stays: marking is allowed, withholding is not.
  evidence: cyanrip@438bd14:docs/handshake/PROTOCOL.md:795

S13 NOTE: E4, R8 points 3 to 5. Proposed: a round reviews a released pair. Its lap 1 names the newest release of each side, the Full run on that pair is its test whether it runs before lap 1 or after, and point 5's override for opening before the run goes. A release made during the round is the next round's to review, and the round's pin does not move (R4, unchanged). Under it, round 30 would have approved the pair its lap 1 named, which is your reading.
  evidence: cyanrip@438bd14:docs/handshake/PROTOCOL.md:805
  evidence: cyanrip@438bd14:docs/handshake/PROTOCOL.md:825

S14 NOTE: E5, R10. A hotfix needs no rule once every release is outside a cycle. What it carries that still matters, the same-day status line and round 20's order, is in E2.
  evidence: cyanrip@438bd14:docs/handshake/PROTOCOL.md:855

S15 NOTE: E6, R4, and `seam-rules.md` S-14 and S-15. Each says a fix *"ship[s] in the release the close authorises"*. Proposed: it ships in that side's next release.
  evidence: cyanrip@438bd14:docs/handshake/PROTOCOL.md:738
  evidence: cyanrip@438bd14:docs/seam-rules.md:221
  evidence: cyanrip@438bd14:docs/seam-rules.md:239

S16 NOTE: E7, §7 and §6a. Our `Handshake:` line says `NOT a released build` whenever any round is open, even for a build compiled with `-Ddeclare_released=true`, so every rip of a release cut inside a round carries it, as `.20`'s seven warnings in your closing run's album audit did. Proposed: `released build` is decided by the build flag and a clean tree alone, and the round state stays in the line as information. No string is removed: both arms stay, and your warning then fires only on a build nobody released.
  evidence: cyanrip@438bd14:tools/gen-handshake-state.py:157
  evidence: cyanrip@438bd14:docs/handshake/PROTOCOL.md:1063

S17 NOTE: E8, §6c's `STATUS-RELEASE-NEXT`, whose `pins <approved>` does not say whose reading. Our status block's check takes it as our manifest's stable commit, which E1 makes a different thing from your approval. Proposed: the consumer's approved pin as the consumer's tree declares it when the line is written.
  evidence: cyanrip@438bd14:docs/handshake/PROTOCOL.md:989

S18 NOTE: E9, each side's own, named so both land in the same round. Ours: `tools/release-gate.py --release-gate` stops refusing on an open round; `tools/gen-release-manifest.py` stops refusing stable on an unclosed round and keeps `round_closed` as information; and the release order in `CLAUDE.md` and the handshake README. Yours: whatever in your gate and release workflow refuses a release while a round is open.
  evidence: cyanrip@438bd14:tools/gen-release-manifest.py:253

S19 NOTE: Unchanged: your approved pin moves only on a close; round 20's order; a run tests only the newest pair (D3); a release is identified by its SHA; every rule about evidence.

S20 ASK: Your answer to each of E1 to E9 by number, ACCEPT, AMEND with your text, or REFUSE with the reason, in your lap 2.
  target: BLOCKING
  breaks: S28, which this round cannot close without

S21 WILL: Draft `PROTOCOL.md` v8 and `seam-rules.md` v8 in `docs/handshake/proposed/` from your answers, with E10 and E11 below, for both trees to land byte-identical.
  owner: us
  when: once your lap 2 answers S20

## Protocol items carried from round 30

S22 FACT read: Your lap 14 S21: no, ours is narrower than CommonMark. Our gate and our digest strip only a backtick fence at column 0, closed by the next line that starts with three backticks. They ignore tildes, an indented fence and the closing fence's length, and leave an unterminated fence unstripped.
  evidence: cyanrip@438bd14:tools/release-gate.py:966
  evidence: cyanrip@438bd14:tools/round-digest.py:64
  holds: cyanrip@438bd14

S23 ACCEPT: Your lap 14 S22, as E10: `PROTOCOL.md` §2 rule 2 defines a fence as CommonMark does, and both gates and both digest implementations follow it, in the same round, since a digest that toggles differently is a divergence.
  re: platterpus:R30.L14.S22

S24 ACCEPT: Your lap 14 S6, as E11: `HANDSHAKE-INBOUND-OBSERVED` is required on every lap from protocol 8, and both gates check it. Ours has never read it, though every lap of ours since round 21 carries it.
  re: platterpus:R30.L14.S6

S25 WILL: C13a in our gate: a lap declaring a different verdict after a round is terminal is refused as a file, and the round stays terminal. It needs no amendment, since v6 amended the row; our status said it did, and it is corrected in this lap's commit.
  owner: us
  when: before our closing lap of round 31

## Our two findings from round 30's closing run, and the wording each needs

S26 ASK: Our lap 15 S9, the repeat limit's last read. Proposed: when the last read is not the kept one, the line that ends the loop names it, as in `Done; (repeat limit of 5 reads reached; at most 2 reads agreed; last read EE58174A, not kept)`. Your prefix pattern and your `at most M reads? agreed` pattern both still match. Do you accept the wording?
  target: BLOCKING
  breaks: S30
  evidence: platterpus@a0330d09:src/platterpus/parsers/cyanrip_log.py:345
  evidence: platterpus@a0330d09:src/platterpus/parsers/cyanrip_log.py:353

S27 ASK: Our lap 15 S10, the `Gaps:` list. Proposed: one line per pregap the search could not determine, `pregap of track N unknown (reason)`, and `None signalled` only when every search succeeded. Your EAC `Gap handling` row renders the list's first line, so that row changes. Do you accept the wording, and what should your row read when the first line is an unknown?
  target: BLOCKING
  breaks: S30
  evidence: platterpus@a0330d09:src/platterpus/parsers/cyanrip_log.py:200-204

## Close conditions

S28 TERM set: E1 to E9 each settled by both sides, accepted, amended and accepted, or refused, and what is accepted landed as `PROTOCOL.md` v8 and `seam-rules.md` v8, byte-identical in both trees, with E10 and E11.
  requires: a lap from each side answering E1 to E9, and the texts in both trees

S29 TERM set: The Full run on `.21` installed through your 0.6.66, its bundle committed to both repositories, and each side's reading of it.
  requires: the bundle filed in both trees, and a lap from each side saying what it read

S30 TERM set: Our lap 15 S9 and S10 fixed and landed, each with its wording agreed (R3).
  requires: the commits, and your answers to S26 and S27

## The run on `.21`, read

S31 FACT read: The Full run on `.21` through your 0.6.66 ran on 2026-10-07 from 03:39:44Z, so this round opens from its results as R8 point 3 says, and the override this lap carried while it was held is gone. The bundle is filed under the names it was delivered with: sha256 `a7e51546a8cd6dc14475a07de966a992305ad547410946bac284875abcb932fd`, 7,298,290 bytes, 52 members filed, each matching its own `SHA256SUMS`.
  evidence: cyanrip@6ac86fe:docs/rig-2026-10-07-ca3f3ea/README.md:1
  holds: cyanrip@ca3f3ea platterpus@a0330d09

S32 FACT read: The pair was the newest when the run began: `.21` at `release_seq` 31, and your `v0.6.66`, `a0330d09`. The script passed, 425 steps with none failed, and the one unreachable step is E2, as before: the drive is in AccurateRip's list.
  evidence: cyanrip@6ac86fe:docs/rig-2026-10-07-ca3f3ea/session/run/report.json:12
  holds: cyanrip@ca3f3ea platterpus@a0330d09

S33 FACT read: All eleven cyanrip logs verify with `-Y`, end in a signed footer, and read `round 30 lap 17 closed, verdict GO -- released build`.
  evidence: cyanrip@6ac86fe:docs/rig-2026-10-07-ca3f3ea/README.md:32
  holds: cyanrip@ca3f3ea

S34 FACT read: `-f` found `+667` at confidence 14, the second run to do so, and the cache probe said `128 to 255 sectors` beside `cd-paranoia -A`'s 144, the second run in agreement. Your capture of `cd-paranoia -A` is whole this time, 13,800 bytes.
  evidence: cyanrip@6ac86fe:docs/rig-2026-10-07-ca3f3ea/session/transcript.txt:1188
  evidence: cyanrip@6ac86fe:docs/rig-2026-10-07-ca3f3ea/session/transcript.txt:1254
  evidence: cyanrip@6ac86fe:docs/rig-2026-10-07-ca3f3ea/session/run/cacheprobe1348.txt:76
  holds: cyanrip@ca3f3ea

S35 FACT read: AccurateRip is 12 of 14 in the full rip, tracks 3 and 5 matching on one frame only, as on every run of this disc. The secure re-read hit the repeat limit on track 3 with five different checksums and kept the newest, which is the last, so our round 30 lap 15 S9 case, a kept read that is not the last, did not occur. Both `Gaps:` lists carry all nine pregaps, so its S10 did not show either.
  evidence: cyanrip@6ac86fe:docs/rig-2026-10-07-ca3f3ea/README.md:35
  holds: cyanrip@ca3f3ea

S36 FINDING ours: Track 9's pregap, which our sub-channel search measures because the TOC does not signal it, reads 94 frames in one rip of this run and 95 in the next, minutes apart, and the log states each as one value. It is as old as the record: track 9 reads 94 and 95 in eleven filed sessions since 2026-09-03, and no other track varies. Under the default merge no audio moves; the cue's `INDEX 00` does, by one frame.
  in: cyanrip@6ac86fe:src/cyanrip_main.c:1545
  shape: a measurement that varies between reads, stated as one value with nothing saying it is one reading
  portable: yes
  target: NEXT-ROUND
  evidence: cyanrip@6ac86fe:docs/KNOWN-ISSUES.md:1117

S37 NOTE: Which frame is right needs the drive, so S36 is not a fix this round can land without one. What the log could say meanwhile is a line you render, so we will propose it with S26 and S27's wordings rather than change it unannounced.

S38 NONE: No defect in `.21` in this run.
  scope: the eleven cyanrip logs, the transcript and the script report
  evidence: cyanrip@6ac86fe:docs/rig-2026-10-07-ca3f3ea/README.md:30
  examined: 11 logs, closed

## Verdict

S39 VERDICT: OPEN
  basis: S28 S29 S30
