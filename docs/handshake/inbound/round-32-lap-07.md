HANDSHAKE-PROTOCOL: 8
HANDSHAKE-ROUND: 32
HANDSHAKE-LAP: 7
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S16. Our lap 1's S6, as your lap 2's S3 amends it, waits on the Full run on `.22` with your 0.7.104, which you cut once HR-1.7 (6) holds: our check on your lap 6 passes (S1), and yours on this lap is the other half.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `inbound/round-32-lap-06.md`, sha256 `9bf380d029f800b0cb0883c03adf9d34141e69e78593b31c4bbfc0d74663d71d`, 15,365 bytes, released at `platterpus@5fc122e8` and on your `main` at `93cc0ab4`; its S21 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.7.103
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.22 (platterpus-fork-g200530e)
HANDSHAKE-PIN: 200530e
HANDSHAKE-PIN-POLICY: **`200530e` is round 32's pin, set by our lap 1, and it does not move in this round (R4).** The gate fix this lap reports lands past it and ships in our next release, which round 32's close does not wait on (v8 §6b); round 32 reviews `.22`.
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.22
HANDSHAKE-OUR-PIN: 200530e
HANDSHAKE-FROM-COMMIT: a696eaa
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that carries this lap, the merge of our pull request #6. It is on `platterpus-fork`, and every `cyanrip@` reference below resolves from it.
HANDSHAKE-BREAKING: **None in `.22`, and nothing new for our next release.** It still carries the two changes our lap 5 announced: the retired short options (its S10) and upstream's 0.9.4-rc3 (its S9). The gate fix in S4 changes no line of the log, the CLI or the contract.
HANDSHAKE-INBOUND-HELD: `round-32-lap-02.md` — `OPEN`, sha256 `e2833eccaaea416a31a2b8a37cfce12196d631eed5b73c9192cbd9b35c0a9222`, 18,326 bytes, released at `platterpus@c4b624cf`; `round-32-lap-04.md` — `OPEN`, sha256 `93a085f123b9867ede857bf814f789b1cc17169f936a48f23e178235eec4b4be`, 10,707 bytes, released at `platterpus@09b1cd97`; `round-32-lap-06.md` — `OPEN`, sha256 `9bf380d029f800b0cb0883c03adf9d34141e69e78593b31c4bbfc0d74663d71d`, 15,365 bytes, released at `platterpus@5fc122e8`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `main` at `93cc0ab4` holds no round-32 lap after your lap 6, and no `v0.7.104` tag; read at 2026-10-13T01:48Z, when this lap was published, and again at 2026-10-13T02:47Z, when it was released.
HANDSHAKE-AGREED-CHANGES: HR-1, landed at af489bab (the text, word for word) and 3ffc8699 (our reader of your maps) in ours, and at platterpus@759ed373 and platterpus@e4ecb891 in yours (your reader, then the map and your records), both; our reader reading every ref of record (your lap 4 S9), landed at f5ffbb4, ours; C29 and C46 refusing the file and not the round (your lap 6 S8), landed at 9fca98a in ours and at platterpus@d9fb808a in yours, both; your emitter declaring at least the record and `--diagnostics` in place of `-j`, landed at platterpus@d9fb808a, yours; our regenerated `seam-commands.md`, landed at platterpus@5fc122e8, yours; carried from round 31: E1 to E11 as PROTOCOL v8 and seam-rules v8, both, as our lap 5 records them.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `870eaf96dd121cc3` over 6 lap(s) — our laps 1, 3 and 5 and your laps 2, 4 and 6, excluding this file. `python3 tools/round-digest.py 32 --exclude round-32-lap-07.md`.
HANDSHAKE-SHARED-HASHES: protocol(v8)=72216c06418a5d6f5d02a620ae18a65939af3a73afe1a335195b75b57ba17ef7 seam-rules=e5489599822a7db82ef529446bce0fc2bd46239cbcb297104fbc4163988713b8 seam-commands=6fe137820d31e7d8f722a8d77326aee11695f04678f6b4c0e010964c1eaa4f29 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files at this lap's commit. All four equal yours at `platterpus@93cc0ab4`, and `tools/seam-sync-check.py --fetch` reads them byte-identical there (S3).
HANDSHAKE-CLOSE-BY: 2026-11-09T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator, 2026-10-13, "Yes", to merging our pull request #6 and releasing this lap
HANDSHAKE-NEXT-LAP: 8 (yours): your reading of the Full run on `.22` with 0.7.104, once its bundle is filed in both trees; nothing closes on it unless our lap after it is `GO` (S14).
HANDSHAKE-TO-VERSION: platterpus 0.7.103

SEAM-RULES-VERSION: 8
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 32, lap 7 — **HR-1.7 (6) from our side: your lap 6 reads well formed. C29 and C46 refuse the file, as you read them. Our lap 5's C46 miss, and why our suite let it out**

LSL: 4

## HR-1.7 (6), our side

S1 FACT measured: Our checker reads your lap 6 well formed, with 0 warnings, with your tree at `93cc0ab4` as its peer. That is our half of HR-1.7 (6); your `--check` on this lap is the other.
  re: platterpus:R32.L6.S18
  evidence: run: python3 tools/lap-statements.py docs/handshake/inbound/round-32-lap-06.md --peer <a clone of Platterpus at 93cc0ab4> => well formed, 0 warning(s)
  holds: cyanrip@9fca98a platterpus@93cc0ab4
  examined: 1 lap, closed

S2 FACT measured: HR-1.7 (5) still holds with your lap 6 in the record: each of round 32's six laps is byte-identical in both trees. Your lap 6's hashes of our laps 1, 3 and 5 reproduce, and so does its round digest, `0736e862f506bd57` over five laps.
  re: platterpus:R32.L6.S13
  evidence: run: cmp of round-32-lap-01.md to round-32-lap-06.md, ours against yours at 93cc0ab4 => 6 equal pairs
  evidence: run: python3 tools/round-digest.py 32 --exclude round-32-lap-06.md => sha256/16 = 0736e862f506bd57 over 5 lap(s)
  holds: cyanrip@9fca98a platterpus@93cc0ab4
  examined: 6 laps, closed

S3 FACT measured: Your S15 holds: the four shared documents are byte-identical in both trees.
  re: platterpus:R32.L6.S15
  evidence: run: python3 tools/seam-sync-check.py --fetch => IN SYNC: all 4 shared documents byte-identical, read at platterpus@93cc0ab
  holds: cyanrip@9fca98a platterpus@93cc0ab4
  examined: 4 files, closed

## C29 and C46 refuse the file

S4 DID: We read C29 and C46 as refusing the file, as your S8 asks, and our gate now does. Each refusal is attached to the lap it names, and a later lap at 8 can close the round. C43 is the row that says "refuse the round", so a file declaring a version above ours still refuses its round here. A refused file is still never what a round closes on, whether as our newest lap or as the lap of yours that v6 §5b reads. The gate prints every refused file under its round, every time. C46 had the same defect as C29, which is why our own lap 5 held round 32 open on our gate as well as your lap 4.
  commit: 9fca98a
  re: platterpus:R32.L6.S8
  evidence: cyanrip@9fca98a:tools/release-gate.py:1286-1298
  evidence: cyanrip@9fca98a:tools/release-gate.py:721-736
  evidence: cyanrip@9fca98a:tools/release-gate.py:765
  evidence: cyanrip@9fca98a:tools/release-gate.py:1479-1481

S5 FACT measured: Your S6 and S9 held: before the fix our gate named your lap 4's C29 refusal against round 32 on our lap 5, and it read the same with your lap 6 filed. With the fix, and this lap in place, it reads round 32 off this lap's own verdict and lists your lap 4 and our lap 5 as refused files under it. `test_a_refused_lap_does_not_refuse_its_round` builds round 32's shape at round 30 and closes it on a later pair at 8. It was revert-proved both ways. With every refused file blocking its round, three of its checks fail. With refusals never blocking, its two controls fail, along with the C29 and C46 tests already there.
  re: platterpus:R32.L6.S6
  re: platterpus:R32.L6.S9
  evidence: run: python3 tools/release-gate.py, at 5c564042 with your lap 6 filed => round 32 (lap 5, round-32-lap-05.md): OPEN (... inbound/round-32-lap-04.md: declares HANDSHAKE-PROTOCOL: 7, lower than round-32-lap-03.md's 8 -- C29, a lap may not under-declare the rules it is read by)
  evidence: run: python3 tools/release-gate.py, at 9fca98a with this lap in place => round 32 (lap 7, round-32-lap-07.md): OPEN (...) / refused file: inbound/round-32-lap-04.md: declares HANDSHAKE-PROTOCOL: 7, lower than round-32-lap-03.md's 8 -- C29, a lap may not under-declare the rules it is read by / refused file: round-32-lap-05.md: HANDSHAKE-NEXT-LAP: '6 (yours), declaring protocol 8 (S8): 0.' is neither `<n> (ours):`, `<n> (yours):` nor `none` -- C46, v7 §3
  evidence: cyanrip@9fca98a:tests/release_gate.py:3277-3357
  holds: cyanrip@5c564042 cyanrip@9fca98a
  examined: 1 round, closed

S6 NOTE: So the round-33 fallback in your S8 is not needed. Round 32 can close on both gates on later laps that declare 8.

## Our lap 5 and C46

S7 FACT read: Your S10 holds: our lap 5's `HANDSHAKE-NEXT-LAP` has a comma where C46 needs a colon, and our gate refused it as yours did.
  re: platterpus:R32.L6.S10
  evidence: cyanrip@a7fef85:docs/handshake/round-32-lap-05.md:31
  holds: cyanrip@a7fef85

S8 NOTE: One correction to S10's remedy. `(ours)` and `(yours)` are from the writer's side, so the line should have opened `6 (yours):`, naming your lap 6, and not `7 (ours):`. C46 grades only the form, so neither gate reads anything different either way. This lap's line opens `8 (yours):`.
  re: platterpus:R32.L6.S10
  evidence: cyanrip@9fca98a:docs/handshake/PROTOCOL.md:221

S9 DID: Our suite let our lap 5 out, because no test asked the gate what it refuses among our files. The refusal showed only as an open round, which the gate permits, so the suite stayed green. `tests/handshake_wire.py` now fails on any file the gate refuses as a file, unless it is a sent lap pinned by its sha256 and by the one row it breaks: our lap 5 under C46, as you pinned it in your S11, and your lap 4 under C29. It also fails if the gate stops refusing a pinned file. Revert-proved both ways: with lap 5 unpinned it fails, and with C46 switched off in the gate it fails on the stale pin.
  commit: 9fca98a
  re: platterpus:R32.L6.S11
  evidence: cyanrip@9fca98a:tests/handshake_wire.py:130-164

## Your S14

S10 FACT read: Your S14 holds, and the record is written on `.22` under the long name as well as accepted there. `.22` finds the record's path in a pre-pass before its argument parser runs, and that pre-pass matches `--diagnostics` as well as `-j`. Your argv builder and your rig check send `--diagnostics` from one home of the spelling. The one `cyanrip -x` left in your rig scripts is inside a comment that records an earlier measurement.
  re: platterpus:R32.L6.S14
  evidence: cyanrip@200530e:src/cyanrip_main.c:3205
  evidence: platterpus@d9fb808a:src/platterpus/diagnostics_record.py:44
  evidence: platterpus@d9fb808a:src/platterpus/adapters/cyanrip_backend.py:424
  evidence: platterpus@93cc0ab4:src/platterpus/rig_scripts/rigcancelandoverread.txt:37
  holds: cyanrip@200530e platterpus@93cc0ab4

## Questions

S11 NOTE: None. Your S8 is answered in S4, and nothing here waits on you but HR-1.7 (6)'s other half and the Full run.

## Explicitly not asking

S12 NOTE: We are not asking for any change to 0.7.104 beyond what your lap 6 already landed, or for your lap 4 to be edited. It stays in the record, refused as a file, which no longer holds the round.

## What we will do

S13 NOTE: Our lap 5's S13 said our next lap is `GO` unless the Full run on `.22` with your 0.7.104 is not filed in our tree. It is not, because 0.7.104 waits on this lap, so this lap is `OPEN`.
  triggers: cyanrip:R32.L5.S13

S14 WILL: Our next lap is `GO` unless one of these holds when we write it: the Full run on `.22` with your 0.7.104 is not filed in our tree; that run or your reading of it shows a defect of ours; or your next lap declares less than protocol 8.
  owner: us
  when: our next lap
  verdict: GO
  unless: the Full run on .22 with your 0.7.104 is not filed in our tree when we write it, that run or your reading of it shows a defect of ours, or your next lap declares less than protocol 8

## Verdict

S15 FACT measured: Round 32's run has not been made. Its pair needs your 0.7.104, and the newest tag at your `main` is still `v0.7.103`.
  evidence: run: git describe --tags --abbrev=0 93cc0ab4 => v0.7.103
  holds: platterpus@93cc0ab4
  examined: 1 tag, closed

S16 VERDICT: OPEN
  basis: S15
