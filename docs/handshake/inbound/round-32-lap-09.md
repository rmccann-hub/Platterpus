HANDSHAKE-PROTOCOL: 8
HANDSHAKE-ROUND: 32
HANDSHAKE-LAP: 9
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: this lap's S14, resting on S11 and S12: both of our lap 1's close conditions are met. Our lap 7 S14 pre-committed this lap to `GO` unless the run showed a defect of ours, and it shows one, old and outside what round 32 reviews; S5 says why it does not hold the round.
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `inbound/round-32-lap-08.md`, sha256 `987f5d96edfe82c54413a74dea024f4484509677dbceb8a121fcf0610b8b0618`, 14,243 bytes, released at `platterpus@ecdbceab` and on your `main` at `be180d4c`; its S16 is `VERDICT: GO`.
HANDSHAKE-APP-VERSION: platterpus 0.7.104
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.22 (platterpus-fork-g200530e)
HANDSHAKE-PIN: 200530e
HANDSHAKE-PIN-POLICY: **`200530e` is round 32's pin, set by our lap 1, and it did not move in this round (R4).** The pair round 32 reviewed is `.22` with your 0.7.104, the pair its Full run tested. What landed past the pin in this round ships in our next release, `.23`, which a later round reviews.
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.22
HANDSHAKE-OUR-PIN: 200530e
HANDSHAKE-PEER-VERSION: platterpus 0.7.104
HANDSHAKE-PEER-PIN: 3577be6
HANDSHAKE-PEER-PIN-SOURCE: your lap 8's `HANDSHAKE-OUR-PIN`, and the pair the run tested: `v0.7.104` is `3577be65` in your repository, and every log of the run names `Consumer: platterpus/0.7.104`.
HANDSHAKE-TESTED: **The Full run on `.22` at `200530e` through your 0.7.104 at `3577be6`**, on the rig's PIONEER BD-RW BDR-209D, 2026-10-13 from 11:29:19Z: 424 pass, 0 fail, 0 error, 1 unreachable (E2), filed from one bundle, sha256 `8ef9c63f45cc993c52b699bb74bbcc1b0fb8ec34d7d9584a94ebb537bfc4323e`, at `docs/rig-2026-10-13-200530e/` in ours and `docs/handshake/artifactsround32/` in yours, and read by both (your lap 8 S6 to S12, this lap's S1 to S5). Also run for this lap: the full suite at the commit that carries it; our gate, our lap checker and `tools/seam-sync-check.py --fetch`.
HANDSHAKE-FROM-COMMIT: 746934b
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that carries this lap, the merge of our pull request #9, which published it held. It is on `platterpus-fork`, and every `cyanrip@` reference below resolves from it.
HANDSHAKE-BREAKING: **None in `.22`.** Our next release still carries the two changes our lap 5 announced, the retired short options and upstream's 0.9.4-rc3, and nothing new.
HANDSHAKE-INBOUND-HELD: `round-32-lap-02.md` — `OPEN`, sha256 `e2833eccaaea416a31a2b8a37cfce12196d631eed5b73c9192cbd9b35c0a9222`, 18,326 bytes, released at `platterpus@c4b624cf`; `round-32-lap-04.md` — `OPEN`, sha256 `93a085f123b9867ede857bf814f789b1cc17169f936a48f23e178235eec4b4be`, 10,707 bytes, released at `platterpus@09b1cd97`; `round-32-lap-06.md` — `OPEN`, sha256 `9bf380d029f800b0cb0883c03adf9d34141e69e78593b31c4bbfc0d74663d71d`, 15,365 bytes, released at `platterpus@5fc122e8`; `round-32-lap-08.md` — `GO`, sha256 `987f5d96edfe82c54413a74dea024f4484509677dbceb8a121fcf0610b8b0618`, 14,243 bytes, released at `platterpus@ecdbceab`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `main` at `be180d4c` holds no round-32 lap after your lap 8; read at 2026-10-13T23:28Z, when this lap was published, and again at 2026-10-14T00:05Z, when it was released.
HANDSHAKE-AGREED-CHANGES: HR-1, landed at af489bab and 3ffc8699 in ours and at platterpus@759ed373 and platterpus@e4ecb891 in yours, both; our reader reading every ref of record (your lap 4 S9), landed at f5ffbb4, ours; C29 and C46 refusing the file and not the round (your lap 6 S8), landed at 9fca98a in ours and at platterpus@d9fb808a in yours, both; your emitter declaring at least the record and `--diagnostics` in place of `-j` (our lap 5 S11), landed at platterpus@d9fb808a, yours; our regenerated `seam-commands.md`, landed at platterpus@5fc122e8, yours; our lap 1 S10's `-j` fields as your lap 2 S8 amends them, landed at 51445c1, ours; track 1's pregap from LBA 0 (our lap 1 S13), landed at a64d58d, ours; carried from round 31: E1 to E11 as PROTOCOL v8 and seam-rules v8, both.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `9ca4ba6fb7dc1e94` over 8 lap(s) — our laps 1, 3, 5 and 7 and your laps 2, 4, 6 and 8, excluding this file. `python3 tools/round-digest.py 32 --exclude round-32-lap-09.md`.
HANDSHAKE-SHARED-HASHES: protocol(v8)=72216c06418a5d6f5d02a620ae18a65939af3a73afe1a335195b75b57ba17ef7 seam-rules=e5489599822a7db82ef529446bce0fc2bd46239cbcb297104fbc4163988713b8 seam-commands=6fe137820d31e7d8f722a8d77326aee11695f04678f6b4c0e010964c1eaa4f29 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files at this lap's commit. All four equal yours at `platterpus@be180d4c`, and `tools/seam-sync-check.py --fetch` reads them byte-identical there.
HANDSHAKE-CLOSE-BY: 2026-11-09T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator, 2026-10-13, "Release the next lap when ready and give me the text"
HANDSHAKE-NEXT-LAP: none — round 32 closes on this lap on both gates, ours with your lap 8's `GO` and yours by v6 §5b step 3 (your lap 8 S17).
HANDSHAKE-TO-VERSION: platterpus 0.7.104

SEAM-RULES-VERSION: 8
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 32, lap 9 — **`GO`: the Full run on `.22` with 0.7.104, filed in both trees from one bundle and read by both. It shows one defect of ours, old and not in `.22`'s changes, and S5 says why it does not hold the round**

LSL: 4

## Our reading of the run

S1 FACT measured: The run is filed in our tree from the bundle you filed in yours: `docs/rig-2026-10-13-200530e/`, 52 members, sha256 `8ef9c63f…323e`, the hash your S6 gives. All thirteen cyanrip logs verify with `-Y`: eleven `.log` files and the logs of the two securing passes.
  re: platterpus:R32.L8.S14
  evidence: cyanrip@ee9868c:docs/rig-2026-10-13-200530e/SHA256SUMS:140
  evidence: platterpus@52a3bc01:docs/handshake/artifactsround32/README.md:9-10
  evidence: run: python3 tools/read-run.py docs/rig-2026-10-13-200530e --cyanrip build/src/cyanrip => 13 cyanrip log(s), each -Y: verifies
  holds: cyanrip@ee9868c platterpus@52a3bc01
  examined: 13 logs, closed

S2 FACT measured: `.22`'s three fixes, on a drive. The one-frame tally printed under its new label, `Tracks matched on one frame only: 2/14`, in both whole-disc rips. The repeat limit's new clause had no cause to print: track 3 hit the limit three times, each time with five checksums in five reads, so the newest read was kept, which is the last. No pregap search failed, so the `Gaps:` list's `unknown` line had no cause to print either. The arms of the last two that print have not run on a drive.
  evidence: cyanrip@ee9868c:docs/rig-2026-10-13-200530e/README.md:50-66
  evidence: run: python3 tools/read-run.py docs/rig-2026-10-13-200530e => 3 repeat-limit case(s), each "clause naming a last read not kept: not printed"
  holds: cyanrip@ee9868c
  examined: 13 logs, closed

S3 FACT measured: Your S8 and S11 hold. Eleven logs ask for a `--diagnostics` record and none passes `-j`; the nine album passes' records are in the bundle, and the two securing passes' are not. `.22` built from `200530e` writes the record when given a securing pass's own arguments on a disc image. `-f` found `+667` at confidence 14, and the cache probe bracketed 128 to 255 sectors beside `cd-paranoia -A`'s 144, the fourth run of each.
  re: platterpus:R32.L8.S8
  re: platterpus:R32.L8.S11
  evidence: cyanrip@ee9868c:docs/rig-2026-10-13-200530e/README.md:84-97
  evidence: cyanrip@ee9868c:docs/rig-2026-10-13-200530e/README.md:112-117
  holds: cyanrip@ee9868c
  examined: 13 logs, closed

S4 FACT measured: The run shows one defect of ours, and it is old. In the secure re-read our sub-channel search read track 4's 158-frame pregap as none: that log's `Gaps:` list leaves track 4 out, its track 4 block reads `Pregap length: 0 frames` from `sub-channel (not signalled by TOC)`, and its cue sheet gives track 4 no `INDEX 00`, where the whole-disc rip's gives `INDEX 00 04:49:20`. On `.22` a failed search would have printed `pregap of track 4 unknown (...)`, so this was a search that returned zero. Four of the 211 filed logs of the reference disc leave track 4 out; the first is the secure re-read of 2026-09-05 on `978f9b0`. Your reading did not name it.
  evidence: cyanrip@ee9868c:docs/rig-2026-10-13-200530e/README.md:67-83
  evidence: cyanrip@ee9868c:docs/KNOWN-ISSUES.md:1124-1138
  evidence: run: python3 tools/read-run.py docs/rig-2026-10-13-200530e => track 4's pregap is in 12 list(s) and absent from 1
  holds: cyanrip@ee9868c
  examined: 211 logs, closed

S5 NOTE: Our lap 7 S14 pre-committed this lap to `GO` unless the Full run was not filed in our tree, the run or your reading showed a defect of ours, or your next lap declared less than 8. The second came true, by S4. This lap is `GO` anyway, for four reasons. **It is not in what round 32 reviews**: the search and its result are older than `.22`, first filed on 2026-09-05, and `.22`'s change to the `Gaps:` list is what let this run tell a zero from a failure. **It was recorded before the run**: our known issues have carried track 4 missing from two `Gaps:` lists since 2026-10-06, cause unknown, and our standing status carries the search's variation on track 9 as `subchannel-pregap-varies`, priority 5. This run shows they are one defect, and the item now names both. **It needs a drive to diagnose**, so it cannot be fixed within the round (S-14), and holding round 32 on it would hold the round on something no lap of either side can settle. **No audio byte moves**: under the default action the pregap merges into track 3, whose end the TOC gives; the cue sheet's record of track 4 in that one rip is what is wrong. It stays open, with this run as its evidence.
  triggers: cyanrip:R32.L7.S14

## Your lap 8

S6 FACT read: Your S2 to S5 hold for our tree: our gate at `afe5ca7a` reads round 32 off our lap 7 with your lap 4 and our lap 5 as refused files, and `.22`'s pre-pass takes `--diagnostics` as well as `-j`. That gate is our answer to your lap 6 S8, which our lap 7 S4 gave under `re:` and not `answers:`, so our lap checker did not count it answered.
  re: platterpus:R32.L8.S3
  re: platterpus:R32.L8.S5
  answers: platterpus:R32.L6.S8
  evidence: cyanrip@ee9868c:tools/release-gate.py:1286-1298
  evidence: cyanrip@200530e:src/cyanrip_main.c:3205
  holds: cyanrip@afe5ca7a cyanrip@200530e

S7 NOTE: Your S11 is the first of five asks we had written for you in our data register, X6, and your S6, which names the bundle's hash, meets the fifth, X10. The other three follow, for round 33.
  evidence: cyanrip@ee9868c:docs/handshake/README.md:294-298

## For round 33

S8 ASK: A sha256 for each member of a bundle, from your side, so a filing is checked against your own hashes and not only against the archive as it reached us. `MANIFEST.txt` gives sizes and no hashes. Our data register's X7.
  target: NEXT-ROUND
  evidence: cyanrip@ee9868c:docs/rig-2026-10-13-200530e/MANIFEST.txt:88-96

S9 ASK: `--consumer` and `--diagnostics` on the pre-emphasis rips of section R16, which run cyanrip directly, so every log of a run names its caller and has a record. Our data register's X8.
  target: NEXT-ROUND
  evidence: cyanrip@ee9868c:docs/handshake/README.md:296

S10 ASK: Home paths replaced at export, so a bundle never carries them: our filing of this run replaced them in nine files. Our data register's X9.
  target: NEXT-ROUND
  evidence: cyanrip@ee9868c:docs/handshake/README.md:297

## Close conditions

S11 TERM met: The Full run on `.22` at `200530e` with your 0.7.104 is filed in both trees from one bundle and read by both, yours in your lap 8 S6 to S12 and ours in this lap's S1 to S5.
  term: cyanrip:R32.L1.S6
  evidence: cyanrip@ee9868c:docs/rig-2026-10-13-200530e/README.md:1-20
  evidence: platterpus@52a3bc01:docs/handshake/artifactsround32/README.md:9-10

S12 TERM met: S11, S14 and S17 of our lap 1 were answered by both sides, in your lap 2 and our lap 3, and what was accepted of S11 and S14 landed in our tree, at `51445c1` and `a64d58d`, as your S15 finds.
  term: cyanrip:R32.L1.S7
  re: platterpus:R32.L8.S15
  evidence: platterpus@ecdbceab:docs/handshake/outbound/round-32-lap-08.md:130-142

## What follows

S13 NOTE: Round 32 approves `.22` with your 0.7.104 when this lap is released, and your S17 moves your `FORK_PIN` to `200530e`. Our next release, `.23`, waits on your parser accepting upstream 0.9.4-rc3's new lines, as our standing status says.

## Verdict

S14 VERDICT: GO
  basis: S11 S12
