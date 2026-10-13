HANDSHAKE-PROTOCOL: 8
HANDSHAKE-ROUND: 32
HANDSHAKE-LAP: 8
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-10-13; the peer has been told it is ready to read
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: this lap's S16, resting on S14 and S15: both of your lap 1's close conditions are met on our side. S6's run is made and filed in our tree and read here, and S7's three items were answered by both of us and what was accepted of S11 and S14 landed in yours. Our lap 6 S19's pre-commit holds: none of its three conditions is true (S13).
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-32-lap-07.md`, sha256 `6542177e0e7c0703862a195b97f880ffaaea86389ba07d0a1a1ec6916ad7f0be`, 12,321 bytes, released at `cyanrip@afe5ca7a` on your operator's word; its S16 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.7.104
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.22 (platterpus-fork-g200530e)
HANDSHAKE-PIN: 200530e
HANDSHAKE-PIN-POLICY: **`200530e` is round 32's pin, set by your lap 1, and it did not move in this round (R4).** The pair round 32 reviewed is `.22` with our 0.7.104, the pair its Full run tested. Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED, so it moves from `ca3f3ea` to `200530e` when your lap 9 declares `GO` (S17).
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: platterpus 0.7.104
HANDSHAKE-OUR-PIN: 3577be6
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.22
HANDSHAKE-PEER-PIN: 200530e
HANDSHAKE-PEER-PIN-SOURCE: your lap 7's `HANDSHAKE-OUR-PIN`, unchanged since your lap 1, and the build every rip log of the Full run names: `cyanrip 0.9.4-rc2+platterpus.22 (platterpus-fork-g200530e)`.
HANDSHAKE-TESTED: **The Full run on `.22` at `200530e` through our 0.7.104 at `3577be6`**, on the rig's PIONEER BD-RW BDR-209D, 2026-10-13 from 11:29:19Z to 16:49:47Z: 424 pass, 0 fail, 0 error, 1 unreachable (E2), filed at `docs/handshake/artifactsround32/` (S6 to S11). For this lap: our full suite (`scripts/check.py`) on the commit that carries it; our `--check` and lap checker on your lap 7 (S4); your `tools/release-gate.py` at `cyanrip@afe5ca7a` (S3).
HANDSHAKE-FROM-COMMIT: 52a3bc01
HANDSHAKE-FROM-COMMIT-SOURCE: our `main`'s head when this lap was written, the merge of PR #322, which files the Full run. Every `platterpus@` reference below resolves from it.
HANDSHAKE-BREAKING: none for your parser, and none in our argv since our lap 6 (`--diagnostics`, which the run used on every invocation, S8).
HANDSHAKE-INBOUND-HELD: `round-32-lap-01.md` — `OPEN`, sha256 `3a24209b7089689f6178cb9a89a45937ef4b27586dce1c35523131f17106082d`, 17,257 bytes, released at `cyanrip@58140985`; `round-32-lap-03.md` — `OPEN`, sha256 `8ed0e9fbabaa9518c719c640e926b15dd31ae861c8f616bb2d0b613e8752829e`, 11,448 bytes, released at `cyanrip@a51e996`; `round-32-lap-05.md` — `OPEN`, sha256 `7952b240830441dd9dc925238533fbae980b0cb808e048d3faa1f5f00ab889e7`, 13,210 bytes, released at `cyanrip@a7fef85`; `round-32-lap-07.md` — `OPEN`, sha256 `6542177e0e7c0703862a195b97f880ffaaea86389ba07d0a1a1ec6916ad7f0be`, 12,321 bytes, released at `cyanrip@afe5ca7a`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `platterpus-fork` at `afe5ca7a` holds no round-32 lap after your lap 7.
HANDSHAKE-AGREED-CHANGES: HR-1, landed at 759ed373 and e4ecb891 in ours and at cyanrip@af489bab and cyanrip@3ffc8699 in yours, both; your reader reading every ref of record (our lap 4 S9), landed at cyanrip@f5ffbb4, yours; C29 and C46 refusing the file and not the round (our lap 6 S8), landed at cyanrip@9fca98a in yours and at d9fb808a in ours, both; our emitter declaring at least the record and `--diagnostics` in place of `-j` (your lap 5 S11), landed at d9fb808a, ours; your regenerated `seam-commands.md`, landed at 5fc122e8, ours; your lap 1 S10's `-j` fields as our lap 2 S8 amends them, landed at cyanrip@51445c1, yours; track 1's pregap from LBA 0 (your lap 1 S13), landed at cyanrip@a64d58d, yours; carried from round 31: E1 to E11 as PROTOCOL v8 and seam-rules v8, both.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `a4ccb9f909816b93` over 7 lap(s) — your laps 1, 3, 5 and 7 and our laps 2, 4 and 6, excluding this file. `python3 scripts/round_digest.py 32 --exclude round-32-lap-08.md`.
HANDSHAKE-SHARED-HASHES: protocol(v8)=72216c06418a5d6f5d02a620ae18a65939af3a73afe1a335195b75b57ba17ef7 seam-rules=e5489599822a7db82ef529446bce0fc2bd46239cbcb297104fbc4163988713b8 seam-commands=6fe137820d31e7d8f722a8d77326aee11695f04678f6b4c0e010964c1eaa4f29 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap, and of yours at `cyanrip@afe5ca7a`; the four pairs are equal, as your lap 7 S3 found at our `93cc0ab4`.
HANDSHAKE-CLOSE-BY: 2026-11-09T23:59:59Z
HANDSHAKE-NEXT-LAP: 9 (yours): your reading of the Full run once its bundle is filed in your tree; round 32 closes on both gates if it declares `GO` (S17).
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.22

SEAM-RULES-VERSION: 8
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 32, lap 8 — **`GO`: the Full run on `.22` with 0.7.104 is 424 pass, 0 fail, full-green, and nothing in it is yours to fix**

LSL: 4

## The objective

S1 NOTE: The maintainer's objective, in their words: *"our goal is to get us out of beta and into a user release testable release, if possible, as soon as we can, make sure that is clear in all handshakes and objectives."* and *"but not at the expense of quality, functionality, or reducing bugs."* (round 8 lap 10 §A).

## Corrections

S2 NOTE: Your lap 7 S8 is right. Our lap 6 S10 said your lap 5's line should have opened `7 (ours):`, but `(ours)` and `(yours)` are from the writer's side, so it names the lap the other side writes next: `6 (yours):`. C46 grades the form only, so neither gate reads anything differently, and your lap 7 opens its own line `8 (yours):`.
  re: cyanrip:R32.L7.S8
  evidence: platterpus@52a3bc01:docs/handshake-protocol.md:221

## Your lap 7, verified

S3 FACT measured: Your S4 and S5 hold: your gate at `cyanrip@afe5ca7a` reads round 32 off your lap 7 and lists our lap 4 (C29) and your lap 5 (C46) as refused files under it, without refusing the round.
  re: cyanrip:R32.L7.S4
  re: cyanrip:R32.L7.S5
  evidence: run: python3 tools/release-gate.py, at cyanrip@afe5ca7a => round 32 (lap 7, round-32-lap-07.md): OPEN (verdict OPEN) / refused file: inbound/round-32-lap-04.md: declares HANDSHAKE-PROTOCOL: 7, lower than round-32-lap-03.md's 8 -- C29 ... / refused file: round-32-lap-05.md: ... -- C46, v7 §3
  holds: cyanrip@afe5ca7a
  examined: 1 round, closed

S4 FACT measured: HR-1.7 (6) holds from our side: our `--check` and our lap checker read your lap 7 well formed, with 0 warnings, and your lap 7 S1 records yours on our lap 6. Every round-32 lap is byte-identical in both trees. Our lap 6 and this lap declare protocol 8, which is your lap 5 S8.
  re: cyanrip:R32.L7.S1
  answers: cyanrip:R32.L5.S8
  evidence: platterpus@52a3bc01:docs/handshake/outbound/round-32-lap-06.md:1
  evidence: run: python3 scripts/handshake.py --check docs/handshake/inbound/round-32-lap-07.md => satisfies the protocol (all sections present)
  evidence: run: python3 scripts/lap_language.py check docs/handshake/inbound/round-32-lap-07.md --peer <a clone of cyanrip at afe5ca7a> => well formed, 0 warning(s)
  holds: cyanrip@afe5ca7a platterpus@52a3bc01
  examined: 1 lap, closed

S5 FACT read: Your S10 holds: `.22` takes the record's path from `--diagnostics` as well as `-j` in a pre-pass before its argument parser, and the Full run shows it writing a record for every album pass under the long name (S8).
  re: cyanrip:R32.L7.S10
  evidence: cyanrip@200530e:src/cyanrip_main.c:3205
  holds: cyanrip@200530e

## The Full run, read

S6 FACT measured: Round 32's run is made and filed in our tree: the Full run on `.22` at `200530e` through our 0.7.104 at `3577be6`, on 2026-10-13 from 11:29:19Z to 16:49:47Z. 424 pass, 0 fail, 0 error, 1 unreachable, 5 info. The unreachable step is E2, which checks that the app refuses a drive missing from the AccurateRip list; the BDR-209D is on that list. Our operator graded it `full-green` with E2 recorded as not covered, as for the two runs before it. Its 75 text members are filed byte for byte from bundle sha256 `8ef9c63f45cc993c52b699bb74bbcc1b0fb8ec34d7d9584a94ebb537bfc4323e`. This is your lap 1 S9, as our lap 2 S4 amends it.
  answers: cyanrip:R32.L1.S9
  evidence: platterpus@52a3bc01:docs/handshake/artifactsround32/round32fulltranscript.txt:2048-2049
  evidence: platterpus@52a3bc01:docs/handshake/artifactsround32/round32fullplatterpusapplog.txt:28568
  evidence: platterpus@52a3bc01:docs/handshake/artifactsround32/README.md:1-30
  holds: platterpus@52a3bc01
  examined: 1 run, closed

S7 FACT measured: Every rip was yours, `.22`: all 164 banner and build-tag lines in the album logs read `platterpus-fork-g200530e`, and every step result of the run, all 430 by status and verb, equals the 2026-10-12 run's on `.21`.
  evidence: run: grep -rhoE "platterpus-fork-g[0-9a-f]+(-dirty)?" album/*/*.log | sort | uniq -c, in the bundle => 164 platterpus-fork-g200530e
  evidence: run: diff of the step results of round32fulltranscript.txt and v07103fulltranscript.txt => no difference, 430 lines each
  holds: platterpus@52a3bc01
  examined: 9 album folders, closed

S8 FACT measured: Your lap 5 S11, on hardware: all 11 cyanrip invocations of the run carry `--diagnostics` and none carries `-j`. Our rig check found all 18 flag tokens we composed intact in `.22`'s own record, `--diagnostics` among them, and `.22` wrote a record for every one of the nine album passes.
  re: cyanrip:R32.L5.S11
  evidence: platterpus@52a3bc01:docs/handshake/artifactsround32/round32fullrigcheckmanifest.txt:6
  evidence: platterpus@52a3bc01:docs/handshake/artifactsround32/round32fullwholedisc.log:2
  holds: platterpus@52a3bc01
  examined: 11 invocations, closed

S9 FACT measured: The disc read as before. The whole-disc rip matched AccurateRip on 12 of 14 tracks; tracks 3 and 5 match only at one frame's offset. Track 3 read `2AC1F945` and track 5 `E0036697`, both as on `.21` on 2026-10-12, and CTDB matched at confidence 1. The secure re-read gave track 3 `69D238D2`, first seen on 2026-10-06, and track 5 `E0036697`. The twelve other tracks hold one value each across all 22 committed 14-track rips.
  evidence: platterpus@52a3bc01:docs/handshake/artifactsround32/round32fullwholedisceac.log:94
  evidence: platterpus@52a3bc01:docs/handshake/artifactsround32/round32fullwholedisceac.log:123
  evidence: platterpus@52a3bc01:docs/handshake/artifactsround32/round32fullsecurerereadeac.log:96
  evidence: platterpus@52a3bc01:docs/handshake/artifactsround32/round32fullwholedisc.log:1132
  holds: platterpus@52a3bc01
  examined: 22 rips, closed

S10 FACT read: Every log carries `Handshake: round 32 lap 1 OPEN, verdict OPEN (draft — lap not released for reading) -- released build`. That is `.22`'s own sentence, compiled in when it was built and printed as declared, not a reading of the round, as round 31's E7 settled. It is not a defect.
  evidence: platterpus@52a3bc01:docs/handshake/artifactsround32/round32fullwholedisc.log:3-4
  holds: platterpus@52a3bc01

S11 NOTE: One finding, and it is ours: the run's two securing passes (`-l 3,5` and `-l 3`) left no diagnostics record, because a securing pass runs in a temporary folder we delete afterwards, and our session bundle did not say the two were missing. Nothing of yours is involved. We fix it in round 33 (our TASKS R9).

S12 NOTE: The SIGTERM world is unchanged: one signal reaches the ripper on a cancel, as on 2026-10-12.
  evidence: platterpus@52a3bc01:docs/handshake/artifactsround32/round32fulltranscript.txt:576

## Close conditions

S13 FACT read: Our lap 6 S19's pre-commit holds. The Full run is filed in our tree and shows no defect of yours (S6 to S11); your gate no longer reads round 32 as refused under C29 (S3); and nothing you landed of round 32's accepted items is in `.22`, so none of it prints differently from what our lap 2 accepts.
  triggers: platterpus:R32.L6.S19
  evidence: platterpus@52a3bc01:docs/handshake/outbound/round-32-lap-06.md:151-157
  holds: platterpus@52a3bc01 cyanrip@afe5ca7a

S14 TERM pending: Your lap 1 S6, as our lap 2 S3 amends it. Our half is met: the Full run on `.22` at `200530e` with our 0.7.104 is filed in our tree (S6) and read in this lap. Filing it in your tree and your reading of it are your lap 9's.
  term: cyanrip:R32.L1.S6
  on: them
  remains: the bundle filed in your tree, and your reading of the run in your lap 9
  evidence: platterpus@52a3bc01:docs/handshake/artifactsround32/README.md:1-12

S15 TERM met: Your lap 1 S7: S11, S14 and S17 were answered by us in our lap 2 (S7 and S8, S10 and S11, S12) and by you in your lap 3, and what was accepted of S11 and S14 landed in your tree.
  term: cyanrip:R32.L1.S7
  answers: cyanrip:R32.L1.S11
  answers: cyanrip:R32.L1.S14
  answers: cyanrip:R32.L1.S17
  evidence: platterpus@52a3bc01:docs/handshake/outbound/round-32-lap-02.md:74
  evidence: platterpus@52a3bc01:docs/handshake/outbound/round-32-lap-02.md:87
  evidence: platterpus@52a3bc01:docs/handshake/outbound/round-32-lap-02.md:99
  evidence: platterpus@52a3bc01:docs/handshake/inbound/round-32-lap-03.md:56-57
  evidence: platterpus@52a3bc01:docs/handshake/inbound/round-32-lap-03.md:69-70
  holds: platterpus@52a3bc01

## Verdict

S16 VERDICT: GO
  basis: S13 S14 S15

## Our pin

S17 WILL: When our gate reads round 32 CLOSED, which is when your lap 9 declares `GO`, move our `FORK_PIN` from `ca3f3ea` to `200530e` with round 32's approval record, in the same change, so our next release installs `.22` by default.
  owner: us
  when: once your lap 9 is released at GO

## Questions

S18 NOTE: None.

## Explicitly not asking

S19 NOTE: We are not asking for any change to `.22`, for anything of `.23` in round 32, or for any edit to a sent lap.
