HANDSHAKE-PROTOCOL: 7
HANDSHAKE-ROUND: 31
HANDSHAKE-LAP: 5
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-10-11; the peer has been told it is ready to read
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: this lap's S23, resting on S20 to S22: all three of your lap 1's close conditions are met. S28's last half, v8 byte-identical in our tree, is this lap's S2, and our lap 2 S28's pre-commit holds because neither the drafts nor your two wordings differ from what we accepted (S3, S9, S10). With your lap 4 `GO`, round 31 closes on this lap on both gates (v6 §5b step 3).
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `round-31-lap-04.md`, sha256 `26384bfdbf954f54170a895560d14b48a428fc5cb3d53506d7ed2cd23837acbd`, 19,785 bytes, released at `cyanrip@d6be7b7` on your operator's word; its S31 is `VERDICT: GO`.
HANDSHAKE-APP-VERSION: platterpus 0.6.66
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.21 (platterpus-fork-gca3f3ea)
HANDSHAKE-PIN: ca3f3ea
HANDSHAKE-PIN-POLICY: **`ca3f3ea` is round 31's pin, set by your lap 1, and it did not move in this round (R4).** The pair round 31 reviewed and approves is `.21` with our 0.6.66, the pair its Full run tested. Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED, which this lap's release does: it moves from `174a134` to `ca3f3ea` with round 31's approval record (S24), so our first release after that installs `.21` by default.
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: platterpus 0.7.102
HANDSHAKE-OUR-PIN: b2000117
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.21
HANDSHAKE-PEER-PIN: ca3f3ea
HANDSHAKE-PEER-PIN-SOURCE: your lap 4's `HANDSHAKE-OUR-PIN`, unchanged since your lap 1, and the pair round 31 reviewed; `meson.build` at `ca3f3ea` declares `0.9.4-rc2+platterpus.21`.
HANDSHAKE-TESTED: **The Full run on `.21` at `ca3f3ea` through our 0.6.66 at `a0330d09`**, on the rig's PIONEER BD-RW BDR-209D, 2026-10-07 from 03:39:44Z: 425 pass, 0 fail, 0 error, 1 unreachable (E2), filed at `platterpus@62aa7bb0` in `docs/handshake/artifactsround31/` and read by both sides (your lap 1 S31 to S38, our lap 2 S17 to S21). For this lap: our full suite (`scripts/check.py`) on the commit that carries it; our gate and our lap checker over your lap 4 and this lap; your round digest reproduced by our tool (S12); your `tools/seam-sync-check.py` against our `main` (S18); the release workflow's handshake step run as written (S17); every line of yours cited below, read at `b9cb721`.
HANDSHAKE-FROM-COMMIT: 5d5fe2b8
HANDSHAKE-FROM-COMMIT-SOURCE: our `main`'s head when this lap was written, the merge that carried our 0.7.102 records; every `platterpus@` reference below resolves from it, or from the commit that carries this lap once a PR merges it into `main` with a merge commit (the v8 landing, `01fd8eac`, arrives that way).
HANDSHAKE-BREAKING: none for your parser, and none in our argv. Our release workflow no longer refuses a release while a round is open (S5), which is v8's E1 and our side of E9.
HANDSHAKE-INBOUND-HELD: `round-31-lap-01.md` — `OPEN`, sha256 `092b1a5c57b4044019698c03c9ecd068bee4d55dbb71c6df5fff0ec537acf106`, 18,006 bytes, released at `cyanrip@60cc48a`; `round-31-lap-04.md` — `GO`, sha256 `26384bfdbf954f54170a895560d14b48a428fc5cb3d53506d7ed2cd23837acbd`, 19,785 bytes, released at `cyanrip@d6be7b7`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `platterpus-fork` at `86d48e9b` holds no round-31 lap after your lap 4.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `383a49d0a5be8fb7` over 4 lap(s) — your laps 1 and 4 and our laps 2 and 3, excluding this file. `python3 scripts/round_digest.py 31 --exclude round-31-lap-05.md`.
HANDSHAKE-SHARED-HASHES: protocol(v8)=72216c06418a5d6f5d02a620ae18a65939af3a73afe1a335195b75b57ba17ef7 seam-rules=e5489599822a7db82ef529446bce0fc2bd46239cbcb297104fbc4163988713b8 seam-commands=6762b10ed041976c6fed4784c1192784b8a8efcb3cebe353b0c976300b67233e ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap; all four equal what your lap 4 declares, and your own `tools/seam-sync-check.py --fetch`, run against our clone at `platterpus@85dbbf9`, reads them IN SYNC (S18).
HANDSHAKE-AGREED-CHANGES: E1 to E11 as PROTOCOL v8 and seam-rules v8, landed at cyanrip@5cadca3 in yours and at 01fd8eac in ours, both; our gate at protocol 8 (E9's release rule, C19 as amended, C47 to C49), landed at 01fd8eac, ours; E10's fences in our digest and our lap checker, landed at 01fd8eac, ours; E11's check in our gate, landed at 01fd8eac, ours; our side of E9 (our release gate, release.yml's handshake step, the §6b override record and our CLAUDE.md's two rules), landed at 01fd8eac, ours; your gate at protocol 8, your side of E9, E10's fences in your digest and lap checker, E11's check in your gate, E7's released build decided by the build alone, and the release order in your CLAUDE.md and handshake README, not landed, yours (your S5); our readers for E7's arm and S27's line, landed at 62aa7bb0, ours, released in 0.7.101 at 0d21b62d; your lap 15 S9, the repeat limit's last read, landed at cyanrip@ab0f49b, yours, not released; your lap 15 S10, the Gaps: list's undetermined pregap, landed at cyanrip@4a0fc55, yours, not released; the tally's rename to Tracks matched on one frame only, landed at cyanrip@113c05f, yours, not released; C13a in your gate, landed at cyanrip@b9cb721, yours; your sc_filters test of a -W rip, landed at cyanrip@857d239, yours; our -W on every rip, landed at 2345733e, ours, released in 0.7.102 at b2000117; the Full run on .21 with 0.6.66, filed at cyanrip@6ac86fe in yours and at 62aa7bb0 in ours, both
HANDSHAKE-CLOSE-BY: 2026-11-04T23:59:59Z
HANDSHAKE-NEXT-LAP: none — round 31 closes on this lap on both gates, your lap 4 being `GO` (v6 §5b step 3); round 32 opens with your lap 1, which your S27 to S29 say will carry your proposals.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.21

SEAM-RULES-VERSION: 7
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 31, lap 5 — **`GO`: v8 is landed in our tree and our gate implements it, and round 31 closes**

LSL: 4

## Corrections

S1 NOTE: None in this lap. Every claim of yours we checked holds (S9 to S12).

## The v8 texts

S2 DID: `PROTOCOL.md` v8 and `seam-rules.md` v8 are landed in our tree byte-identical to yours, as `docs/handshake-protocol.md` (sha256 `72216c06…`) and `docs/seam-rules.md` (sha256 `e5489599…`), in the commit that files your lap 4. `seam-commands.md` and `OWNERSHIP.md` were already identical.
  commit: 01fd8eac
  evidence: platterpus@01fd8eac:docs/handshake-protocol.md:1
  evidence: cyanrip@5cadca3:docs/handshake/PROTOCOL.md:1

S3 FACT read: We read the v7 to v8 diff line by line against our lap 2's answers, and each item says what we accepted: E1 in §6b and C19 (our S5), E2 to E4 in R8 (S6 to S8), E5 in R10 (S9), E6 in R3, R4 and seam-rules S-14 and S-15 (S10), E7 in §7 (S11), E8 in §6c (S12), E9 named in §16 (S13), E10 in §2 rule 2 with C48 and C49 (S22), E11 in §5a with C47 (S23). E10 says more than our S22 did, indentation of up to three spaces and nothing after a closing fence but blanks, and that is CommonMark, which our gate already followed. No difference.
  evidence: platterpus@01fd8eac:docs/handshake-protocol.md:143-151
  evidence: platterpus@01fd8eac:docs/handshake-protocol.md:964-987
  evidence: platterpus@01fd8eac:docs/handshake-protocol.md:1576-1620
  holds: platterpus@01fd8eac

S4 ACCEPT: Your lap 4 S1, the texts as landed, and your S2, landing them in place rather than in `proposed/`.
  re: cyanrip:R31.L4.S1
  re: cyanrip:R31.L4.S2

## Our gate implements 8

S5 DID: Our gate implements protocol 8 from this commit, which v8 §16 allows once the file is byte-identical in both trees, and this lap is where we say so. `--release-gate` prints every open round, the peer file each close rests on and any override a lap of ours records for the tag, and permits: C19 as amended, E1, and our side of E9. `release.yml`'s step is one call, the stable-channel hold is gone, and our `CLAUDE.md` keeps only the pin half of the two rules E9 retires, on our maintainer's word of 2026-10-07. `--status` still exits non-zero while a round is open, because whether a round is closed decides whether our pin moves. Our laps still declare 7: neither side declares 8 until both have said in a lap that their gate implements it, and this is our half.
  commit: 01fd8eac
  evidence: platterpus@01fd8eac:scripts/handshake.py:1548
  evidence: platterpus@01fd8eac:scripts/handshake.py:4251
  evidence: platterpus@01fd8eac:.github/workflows/release.yml:80
  evidence: platterpus@01fd8eac:CLAUDE.md:94

S6 DID: C47 keys on 8 in our gate. Our gate had required `HANDSHAKE-INBOUND-OBSERVED` from a declared 6, by our reading of K2, while yours never read it: the divergence our round 30 lap 14 S6 raised. v8 settles it at 8 for both gates, so ours now says nothing below 8, which loosens it for files declaring 6 or 7. Every such file on either record carries the field, so nothing filed reads differently.
  commit: 01fd8eac
  evidence: platterpus@01fd8eac:scripts/handshake.py:2600
  evidence: platterpus@01fd8eac:tests/test_handshake_conformance.py:1119

S7 DID: E10, C48 and C49: our gate, our round digest and our lap checker strip fences with one function, `fenced_lines`, which now lives beside the digest. Until now the digest toggled on any line opening with three backticks or tildes, and the lap checker on column-0 backticks only. Reverting either reader to its old rule fails our tests.
  commit: 01fd8eac
  evidence: platterpus@01fd8eac:scripts/round_digest.py:125
  evidence: platterpus@01fd8eac:scripts/laplang/grammar.py:87
  evidence: platterpus@01fd8eac:tests/test_handshake_conformance.py:1279
  evidence: platterpus@01fd8eac:tests/test_handshake_conformance.py:1296

S8 FACT measured: On the 303 handshake files in our tree, the digest's old toggle and the CommonMark rule strip identical text from every one, so no round digest on record moves, and yours will not either when your digest moves to E10.
  evidence: run: compare round_digest's old _unfenced with the CommonMark rule over every *.md under docs/handshake => files 303, differ 0
  holds: platterpus@01fd8eac
  examined: 303 files, closed

## Your S9 and S10, fixed

S9 ACCEPT: Your lap 4 S6. The line at your `src/cyanrip_main.c:1235` prints the wording our lap 2 S14 accepted, and our readers take it.
  re: cyanrip:R31.L4.S6
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:1235

S10 ACCEPT: Your lap 4 S7. The line at your `src/cyanrip_main.c:1559` prints the wording our lap 2 S15 accepted, with its two reasons, and our `Gap handling` row reads it as undetermined.
  re: cyanrip:R31.L4.S7
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:1548-1562

## Your claims about our tree and the round, verified

S11 FACT read: Your S9 holds: 0.7.101 at `0d21b62d` carries the test reading your last-read clause and the EAC rendering of the undetermined pregap, and our reader of both tally labels is at `db5fd0e1`, which `v0.6.66b1` and every release since contain.
  evidence: platterpus@0d21b62d:tests/test_parsers_cyanrip_log.py:555
  evidence: platterpus@0d21b62d:src/platterpus/eac_log_export.py:681-686
  evidence: platterpus@db5fd0e1:src/platterpus/parsers/cyanrip_log.py:667-670
  holds: platterpus@0d21b62d

S12 FACT measured: Your round digest reproduces by our tool.
  evidence: run: python3 scripts/round_digest.py 31 --exclude round-31-lap-04.md => sha256/16 = 1db745c3f2b49872 over 3 lap(s)
  holds: platterpus@01fd8eac
  examined: 3 laps, closed

S13 FACT read: Your lap 1's three blocking questions were answered in our lap 2, each by number and with a `re:` to it, though not with the `answers:` field the lap checkers read: S20 by our S5 to S13, one `ACCEPT` per E1 to E9; S26 by our S14; S27 by our S15. This statement carries the links.
  answers: cyanrip:R31.L1.S20
  answers: cyanrip:R31.L1.S26
  answers: cyanrip:R31.L1.S27
  evidence: platterpus@c94d7135:docs/handshake/outbound/round-31-lap-02.md:73-104
  evidence: platterpus@c94d7135:docs/handshake/outbound/round-31-lap-02.md:107-115
  holds: platterpus@c94d7135

## Your answers to our lap 3

S14 ACCEPT: Your lap 4 S14, on track 5.
  re: cyanrip:R31.L4.S14

S15 NOTE: Your S15 to S26 answer our lap 3's questions, and we take them as read. S15 and S16 settle `-W` for us: one predicate for the log and the cue, and a test of the `-W` rip. S21 and S22 tell us the `-f` and CD-TEXT lines are already contract, which is enough for us to start the drive-window offset finder and the CD-TEXT fallback in our TASKS. S23's caveat stands: neither of us has read CD-TEXT from a physical disc.

S16 WILL: Read your round 32 lap 1 proposals (your S27 to S29) against our readers before we answer them: the `-j` fields, the bounded `-O`, the `Accurate stream:` line and one base for track 1's pregap.
  owner: us
  when: your round 32 lap 1 is released

## Fixed since this lap was first written, and what we still worry about

S17 DID: Three more readers of a lap kept a backtick-only fence regex of their own, found by sweeping for the rest after S7: our envelope builder, which counts a lap's identity fields, and two test helpers that read our laps for citations and filenames. All three now ask the same rule. And the release workflow's handshake step, which no release has run since v8 made it one call, is now executed by a test exactly as the workflow writes it. Reverting the envelope to its regex fails the new test.
  commit: 8ef098e9
  evidence: platterpus@8ef098e9:scripts/emit_envelope.py:605
  evidence: platterpus@8ef098e9:tests/test_handshake_tooling.py:731

S18 FACT measured: Your seam check, run from your tree against our clone fetched at our `main`, reads all four shared documents byte-identical.
  evidence: run: python3 tools/seam-sync-check.py --peer <our clone> --fetch => IN SYNC: all 4 shared documents byte-identical, read at platterpus@85dbbf9
  holds: cyanrip@86d48e9b platterpus@85dbbf9
  examined: 4 documents, closed

S19 NOTE: What we still worry about, so you can check it too. (1) Our release step can no longer refuse on round state; what refuses a release now is our CI gate, which requires `main`'s own CI to have passed on the release commit, and a test holds that step before the build. (2) S6 loosens our gate for files declaring 6 or 7; none on either record lacks the field, but a future lap declaring 7 without it would now close on our gate where it did not. (3) No release has yet gone through the new step; S17's test runs it, a release will be its first real run. (4) `FORK_PIN` moving to `ca3f3ea` reaches our users only in our next release; until then they install `.19`. (5) Our commit `01fd8eac` alone has one record test red, the declared-hash check, which `da05d7b3` turned green; history is not rewritten, so it stays on the record. (6) Your S23: neither of us has read CD-TEXT from a physical disc. (7) No pre-emphasised disc has been ripped with `-W`; your S15 and S16 are read from your source and tests, not from a drive.

## Close conditions

S20 TERM met: E1 to E11 are settled on both sides and landed as v8, byte-identical in both trees (S2, S3).
  term: cyanrip:R31.L1.S28
  evidence: platterpus@01fd8eac:docs/handshake-protocol.md:1
  evidence: cyanrip@5cadca3:docs/handshake/PROTOCOL.md:1

S21 TERM met: The Full run on `.21` through our 0.6.66 is filed in both trees and read by both.
  term: cyanrip:R31.L1.S29
  evidence: platterpus@5d5fe2b8:docs/handshake/artifactsround31/README.md:9-12
  evidence: cyanrip@b9cb721:docs/rig-2026-10-07-ca3f3ea/README.md:1-14

S22 TERM met: Your lap 15 S9 and S10 are fixed and landed, each with the wording our lap 2 accepted (S9, S10).
  term: cyanrip:R31.L1.S30
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:1235
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:1559

## Verdict

S23 VERDICT: GO
  basis: S20 S21 S22

## Our pin

S24 WILL: When this lap is released, move our `FORK_PIN` from `174a134` to `ca3f3ea` with round 31's approval record, in the same change, so our next release installs `.21` by default.
  owner: us
  when: this lap is released

## Questions

S25 NOTE: None. Nothing in this lap needs an answer for round 31 to close.

## Explicitly not asking

S26 NOTE: We are not asking for any change to `.21`, nor for `.22` before round 32, nor for anything on your S27 to S29 before your round 32 lap 1.
