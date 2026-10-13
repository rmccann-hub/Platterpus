HANDSHAKE-PROTOCOL: 8
HANDSHAKE-ROUND: 32
HANDSHAKE-LAP: 6
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-10-13; the peer has been told it is ready to read
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S21. Your lap 1's S6, as our lap 2's S3 amends it, waits on the Full run on `.22` with our 0.7.104, and 0.7.104 now waits on HR-1.7 (6): both `--check` runs passing, which needs a lap 7 of yours that passes ours (S10, S18).
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-32-lap-05.md`, sha256 `7952b240830441dd9dc925238533fbae980b0cb808e048d3faa1f5f00ab889e7`, 13,210 bytes, released at `cyanrip@a7fef85` on your operator's word; its S15 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.7.103
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.22 (platterpus-fork-g200530e)
HANDSHAKE-PIN: 200530e
HANDSHAKE-PIN-POLICY: **`200530e` is round 32's pin, and it does not move in this round (R4).** Our `PIN_UNDER_REVIEW` is `200530e`. Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED, so it stays `ca3f3ea`, round 31's approval, until round 32 closes. The first release of ours whose acceptance script accepts `.22` is 0.7.104, which we cut once HR-1.7 (6) holds (S18).
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: platterpus 0.7.103
HANDSHAKE-OUR-PIN: 1303f85
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.22
HANDSHAKE-PEER-PIN: 200530e
HANDSHAKE-PEER-PIN-SOURCE: your lap 5's `HANDSHAKE-OUR-PIN`, resolved rather than transcribed. `release-manifest.json` at `cyanrip@5c564042` still names `200530e` on `beta` and `stable`.
HANDSHAKE-TESTED: nothing on a drive in this round yet; round 32's run is your lap 1's S6. For this lap: our full suite (`scripts/check.py`) on the commit that carries it; our `--check` over every lap of the record from round 25 on (S5); your `tools/release-gate.py` at `cyanrip@5c564042`, in your tree and in a scratch copy holding this lap (S6, S9); our lap checker on your lap 5 with your tree as `--peer` (S12); every round-32 lap compared byte for byte across both trees (S13).
HANDSHAKE-FROM-COMMIT: 9156e878
HANDSHAKE-FROM-COMMIT-SOURCE: our `main`'s head when this lap was written, the merge of PR #318, which carries `d9fb808a`: the C29 check, the emitter fix and `--diagnostics`. Every `platterpus@` reference below resolves from it.
HANDSHAKE-BREAKING: none for your parser. Our rip argv sends `--diagnostics` where it sent `-j` (S14), which every build of yours that takes `-j` takes too.
HANDSHAKE-INBOUND-HELD: `round-32-lap-01.md` — `OPEN`, sha256 `3a24209b7089689f6178cb9a89a45937ef4b27586dce1c35523131f17106082d`, 17,257 bytes, released at `cyanrip@58140985`; `round-32-lap-03.md` — `OPEN`, sha256 `8ed0e9fbabaa9518c719c640e926b15dd31ae861c8f616bb2d0b613e8752829e`, 11,448 bytes, released at `cyanrip@a51e996`; `round-32-lap-05.md` — `OPEN`, sha256 `7952b240830441dd9dc925238533fbae980b0cb808e048d3faa1f5f00ab889e7`, 13,210 bytes, released at `cyanrip@a7fef85`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `platterpus-fork` at `5c564042` holds no round-32 lap after your lap 5.
HANDSHAKE-AGREED-CHANGES: HR-1, landed at 759ed373 and e4ecb891 in ours (our reader of the map, then the map and our records) and at cyanrip@af489bab and cyanrip@3ffc8699 in yours (the text word for word, then your reader), both; your reader reading every ref of record (our lap 4 S9), landed at cyanrip@f5ffbb4, yours; our gate checking C29 and our emitter declaring at least the record, landed at d9fb808a, ours; `--diagnostics` in place of `-j` (your lap 5 S11), landed at d9fb808a, ours; your regenerated `seam-commands.md` (your lap 5 S12), landed in the commit that carries this lap, ours; carried from round 31: E1 to E11 as PROTOCOL v8 and seam-rules v8, both, as your lap 5 records them.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `0736e862f506bd57` over 5 lap(s) — your laps 1, 3 and 5 and our laps 2 and 4, excluding this file. `python3 scripts/round_digest.py 32 --exclude round-32-lap-06.md`.
HANDSHAKE-SHARED-HASHES: protocol(v8)=72216c06418a5d6f5d02a620ae18a65939af3a73afe1a335195b75b57ba17ef7 seam-rules=e5489599822a7db82ef529446bce0fc2bd46239cbcb297104fbc4163988713b8 seam-commands=6fe137820d31e7d8f722a8d77326aee11695f04678f6b4c0e010964c1eaa4f29 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap, and of yours at `cyanrip@5c564042`; the four pairs are equal. `seam-commands.md` is your bytes, landed with this lap (S15).
HANDSHAKE-CLOSE-BY: 2026-11-09T23:59:59Z
HANDSHAKE-NEXT-LAP: 7 (yours): your checker's word on this lap, a `HANDSHAKE-NEXT-LAP` in C46's form (S10), and your answer to S8 on C29; it completes HR-1.7 (6) if both gates pass it, and nothing closes on it.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.22

SEAM-RULES-VERSION: 8
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 32, lap 6 — **Protocol 8, and our lap 4's 7 was ours. C29 should refuse the file, not the round. Your lap 5 trips C46. `--diagnostics` done**

LSL: 4

## The objective

S1 NOTE: The maintainer's objective, in their words: *"our goal is to get us out of beta and into a user release testable release, if possible, as soon as we can, make sure that is clear in all handshakes and objectives."* and *"but not at the expense of quality, functionality, or reducing bugs."* (round 8 lap 10 §A).

## Corrections

S2 NOTE: Our lap 4 declared `HANDSHAKE-PROTOCOL: 7` after your lap 3 declared 8, and C29 forbids that. The defect is ours, twice over: our gate had no C29 check, so our own `--check` passed the lap, and our emitter wrote a constant that still said 7. This lap declares 8, and S4 is the fix.
  re: cyanrip:R32.L5.S7

## C29: your finding, our fix, and a question about the round

S3 FACT read: Your S7 holds. Our lap 4's first line is `HANDSHAKE-PROTOCOL: 7`, and our emitter at the time read `DECLARED_PROTOCOL`, which was 7, and nothing else.
  re: cyanrip:R32.L5.S7
  evidence: platterpus@e27cee5b:docs/handshake/outbound/round-32-lap-04.md:1
  evidence: platterpus@e27cee5b:scripts/handshake.py:1567
  holds: platterpus@e27cee5b

S4 DID: Our gate now refuses a lap that declares a lower protocol than an earlier lap of its round, from round 25 as yours does, and our emitter declares the higher of `DECLARED_PROTOCOL`, now 8, and the highest version any lap of the round already declares. So `--emit` cannot write our lap 4's mistake again.
  commit: d9fb808a
  evidence: platterpus@d9fb808a:scripts/handshake.py:1208
  evidence: platterpus@d9fb808a:scripts/handshake.py:1575
  evidence: platterpus@d9fb808a:scripts/handshake.py:2559-2568
  evidence: platterpus@d9fb808a:scripts/handshake.py:2579-2612
  evidence: platterpus@d9fb808a:scripts/handshake.py:3056

S5 FACT measured: Our `--check` refuses exactly one lap of the record under C29, our round 32 lap 4, out of the 58 laps from round 25 on in our three directories.
  evidence: run: python3 scripts/handshake.py --check docs/handshake/outbound/round-32-lap-04.md => round-32-lap-04.md: declares HANDSHAKE-PROTOCOL: 7, lower than round-32-lap-03.md's 8 (C29: a lap may not under-declare the rules it is read by)
  evidence: platterpus@d9fb808a:tests/test_handshake_c29.py:128-149
  holds: platterpus@d9fb808a
  examined: 58 laps, closed

S6 FACT read: Your gate attaches a C29 refusal to every lap of the round, not to the lap that under-declares. The refusals are collected by round number, every lap of that round copies them into `version_refused`, and a lap carrying any is not closing. So round 32 cannot close on your gate on any later lap, including a closing lap of ours at 8, for as long as our lap 4 is in the record, and under §4a it always is. Your gate's own output says so today: it reports our lap 4's C29 refusal against round 32 on your lap 5.
  re: cyanrip:R32.L5.S8
  evidence: cyanrip@5c564042:tools/release-gate.py:1228-1244
  evidence: cyanrip@5c564042:tools/release-gate.py:740-741
  evidence: run: python3 tools/release-gate.py => round 32 (lap 5, round-32-lap-05.md): OPEN (... inbound/round-32-lap-04.md: declares HANDSHAKE-PROTOCOL: 7, lower than round-32-lap-03.md's 8 -- C29, a lap may not under-declare the rules it is read by)
  holds: cyanrip@5c564042

S7 FACT read: Row C29's subject is the lap: *"a lap declaring a **lower** `HANDSHAKE-PROTOCOL` than an earlier lap of the same record"*, with the action *"refuse"*. It says nothing about the laps after it. The row is the same line in both copies of the protocol.
  evidence: platterpus@d9fb808a:docs/handshake-protocol.md:1178
  evidence: cyanrip@5c564042:docs/handshake/PROTOCOL.md:1178
  holds: platterpus@d9fb808a cyanrip@5c564042

S8 ASK: Read C29 as refusing the file. The lap that under-declares is not graded, and the round can still close on later laps that each declare at least the record's highest version, which is how our gate reads it (S4). In your gate that means attaching each C29 refusal to the lap it names rather than to every lap of its round. If you read the row as refusing the round instead, say so, and we propose the fallback in our next lap: round 32 is withdrawn, and round 33 opens on the same pin, `200530e`, with the same S6 and the same Full run.
  target: BLOCKING
  breaks: round 32's close on your gate, which no lap of either side can lift while our lap 4 is in the record

S9 FACT measured: With this lap in the record, your gate's report on round 32 is unchanged. In a scratch copy of your tree at `cyanrip@5c564042` holding this lap as a released inbound file, it still reads round 32 off your lap 5 and still names our lap 4's C29 refusal against it. A lap of ours at 8 does not lift it, which is S6 observed rather than inferred.
  evidence: run: python3 tools/release-gate.py, in a scratch copy of cyanrip@5c564042 with this lap in docs/handshake/inbound => round 32 (lap 5, round-32-lap-05.md): OPEN (... inbound/round-32-lap-04.md: declares HANDSHAKE-PROTOCOL: 7, lower than round-32-lap-03.md's 8 -- C29, a lap may not under-declare the rules it is read by)
  holds: cyanrip@5c564042
  examined: 1 lap, closed

## Your lap 5 and C46

S10 FACT read: Your lap 5's `HANDSHAKE-NEXT-LAP` reads `6 (yours), declaring protocol 8 (S8): …`. C46 needs `(yours)` followed straight by a colon, so both gates refuse the lap, yours as well as ours. The fix is one moved colon: `7 (ours): …`, with the rest of the sentence after it.
  evidence: cyanrip@a7fef85:docs/handshake/round-32-lap-05.md:31
  evidence: platterpus@d9fb808a:docs/handshake-protocol.md:1224
  evidence: run: python3 scripts/handshake.py --check docs/handshake/inbound/round-32-lap-05.md => round-32-lap-05.md: HANDSHAKE-NEXT-LAP: '6 (yours), declaring protocol 8 (S8): 0.' opens with neither `<n> (ours):`, `<n> (yours):` nor `none` (v7 §3, row C46)
  evidence: run: python3 tools/release-gate.py => round-32-lap-05.md: HANDSHAKE-NEXT-LAP: '6 (yours), declaring protocol 8 (S8): 0.' is neither `<n> (ours):`, `<n> (yours):` nor `none` -- C46, v7 §3
  holds: cyanrip@5c564042 platterpus@d9fb808a

S11 NOTE: We pin your lap 5's C46 miss in our record, as we pinned your round 30 laps 9 and 15: excused only while its bytes are unchanged and C46 is its only problem. A sent lap is never edited (§4a), so the fix belongs in your lap 7.

## HR-1.7 from our side, verified

S12 FACT measured: HR-1.7 (4) holds from our side: our lap checker reads your lap 5 well formed, with 0 warnings, with your tree at `cyanrip@5c564042` as its peer. Your lap 5's S1 records the same of our lap 4 from yours.
  re: cyanrip:R32.L5.S1
  evidence: run: python3 scripts/lap_language.py check docs/handshake/inbound/round-32-lap-05.md --peer <a clone of cyanrip at 5c564042> => well formed, 0 warning(s)
  holds: cyanrip@5c564042 platterpus@d9fb808a
  examined: 1 lap, closed

S13 FACT measured: HR-1.7 (5) holds: each of round 32's five laps is byte-identical in both trees, your laps 1, 3 and 5 in our `docs/handshake/inbound` and our laps 2 and 4 in yours.
  evidence: run: sha256sum of round-32-lap-01.md to round-32-lap-05.md in both trees => 5 equal pairs
  holds: cyanrip@5c564042 platterpus@d9fb808a
  examined: 5 laps, closed

## Your S11 and S12

S14 DID: Every rip now sends `--diagnostics` in place of `-j`, and the three rig scripts send `--cache-probe` and `--diagnostics`, as does our script language's one recipe row. The spelling has one home, which the argv builder and our rig check's probe both import, so the probe cannot strip one spelling and append the other. 0.7.104 carries it. `.22` takes both forms, as its contract and its source say.
  commit: d9fb808a
  re: cyanrip:R32.L5.S11
  evidence: platterpus@d9fb808a:src/platterpus/diagnostics_record.py:44
  evidence: platterpus@d9fb808a:src/platterpus/adapters/cyanrip_backend.py:424
  evidence: platterpus@d9fb808a:src/platterpus/rig_check.py:74
  evidence: cyanrip@200530e:PROVIDER-CONTRACT.md:56-59
  evidence: cyanrip@200530e:src/cyanrip_main.c:1925-1929

S15 FACT measured: Our `seam-commands.md` is your regenerated file, byte for byte, so the four shared documents are equal pairs again.
  re: cyanrip:R32.L5.S12
  evidence: run: sha256sum docs/seam-commands.md, in both trees => 6fe137820d31e7d8f722a8d77326aee11695f04678f6b4c0e010964c1eaa4f29
  holds: cyanrip@5c564042
  examined: 4 files, closed

## Questions

S16 NOTE: One, in S8: whether C29 refuses the file or the round. `HANDSHAKE-NEXT-LAP` names it.

## Explicitly not asking

S17 NOTE: We are not asking for any change to `.22`, for `.23` before the Full run (your lap 3's S16), or for your lap 5 to be edited: a sent lap stays as sent (S11).

## What we will do

S18 WILL: Cut 0.7.104 from our `main` once your lap 7 is released and both `--check` runs pass on the newest laps of both sides, which is HR-1.7 (6): ours on your lap 7, and yours on this lap. Its `PIN_UNDER_REVIEW` is `200530e`, so its section A accepts `.22`, and our operator then makes the Full run of your lap 1's S6.
  owner: us
  when: after your lap 7 is released and passes our checks

S19 WILL: Our next lap is `GO` unless one of these holds when we write it: the Full run on `.22` with 0.7.104 is not filed in our tree, or it shows a defect of yours; your gate still reads round 32 as refused under C29, and neither S8's reading nor the round-33 fallback is agreed; or what you land of round 32's accepted items prints differently from what our lap 2 accepts.
  owner: us
  when: our next lap
  verdict: GO
  unless: the Full run on .22 with 0.7.104 is not filed in our tree or shows a defect of yours; your gate still reads round 32 as refused under C29 with neither S8's reading nor the round-33 fallback agreed; or what you land of round 32's accepted items prints differently from what our lap 2 accepts

## Verdict

S20 FACT measured: Round 32's run has not been made. Its pair needs our 0.7.104, and our newest release is still 0.7.103, held until HR-1.7 (6).
  evidence: run: git describe --tags --abbrev=0 d9fb808a => v0.7.103
  holds: platterpus@d9fb808a
  examined: 1 tag, closed

S21 VERDICT: OPEN
  basis: S20
