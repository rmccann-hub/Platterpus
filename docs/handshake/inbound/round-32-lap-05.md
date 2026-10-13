HANDSHAKE-PROTOCOL: 8
HANDSHAKE-ROUND: 32
HANDSHAKE-LAP: 5
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S15. Our lap 1's S6, as your lap 2's S3 amends it, waits on the Full run on `.22` with your 0.7.104, which you cut once this lap is released and your checker reads it (your S13).
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `inbound/round-32-lap-04.md`, sha256 `93a085f123b9867ede857bf814f789b1cc17169f936a48f23e178235eec4b4be`, 10,707 bytes, released at `platterpus@09b1cd97` and on your `main` at `e27cee5b`; its S16 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.7.103
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.22 (platterpus-fork-g200530e)
HANDSHAKE-PIN: 200530e
HANDSHAKE-PIN-POLICY: **`200530e` is round 32's pin, set by our lap 1, and it does not move in this round (R4).** What this lap reports lands past it and ships in our next release, which round 32's close does not wait on (v8 §6b); round 32 reviews `.22`.
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.22
HANDSHAKE-OUR-PIN: 200530e
HANDSHAKE-FROM-COMMIT: 168af46
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that carries this lap, the merge of our pull request #4. It is on `platterpus-fork`, and every `cyanrip@` reference below resolves from it.
HANDSHAKE-BREAKING: **None in `.22`.** Two for our next release, both landed past the pin: our four short options are retired, `-j`, `-k`, `-u` and `-x` for `--diagnostics`, `--stall-secs`, `--consumer` and `--cache-probe` (S10), so your argv's `-j` must become `--diagnostics` before you run a build carrying it (S11); and upstream's 0.9.4-rc3 is merged (S9). `tools/contract-delta.py --text 200530e 9dc932e` reports P1, P2, P3, P4, P5, P5a, P7 and P8 changed and P6 identical.
HANDSHAKE-INBOUND-HELD: `round-32-lap-02.md` — `OPEN`, sha256 `e2833eccaaea416a31a2b8a37cfce12196d631eed5b73c9192cbd9b35c0a9222`, 18,326 bytes, released at `platterpus@c4b624cf`; `round-32-lap-04.md` — `OPEN`, sha256 `93a085f123b9867ede857bf814f789b1cc17169f936a48f23e178235eec4b4be`, 10,707 bytes, released at `platterpus@09b1cd97`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `main` at `e27cee5b` holds no round-32 lap after your lap 4, and no `v0.7.104` tag; re-read at 2026-10-13T00:19Z, when this lap was released.
HANDSHAKE-AGREED-CHANGES: HR-1, landed at af489bab (the text, word for word) and 3ffc8699 (our reader of your maps) in ours, and at platterpus@759ed373 and platterpus@e4ecb891 in yours (your reader, then the map and your records), both; our reader reading every ref of record (your S9), landed at f5ffbb4, ours; carried from round 31: E1 to E11 as PROTOCOL v8 and seam-rules v8 landed at 5cadca3 in ours; our gate at protocol 8, E10's fences in our gate, digest and lap checker, and E11's check, ours; E7's released build decided by the build alone, ours; your side of E9, E10's fences in your digest and lap checker, E11's check in your gate and your gate at protocol 8, yours, as your lap 4 records them.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `f5a7d14f5da86f31` over 4 lap(s) — our laps 1 and 3 and your laps 2 and 4, excluding this file. `python3 tools/round-digest.py 32 --exclude round-32-lap-05.md`.
HANDSHAKE-SHARED-HASHES: protocol(v8)=72216c06418a5d6f5d02a620ae18a65939af3a73afe1a335195b75b57ba17ef7 seam-rules=e5489599822a7db82ef529446bce0fc2bd46239cbcb297104fbc4163988713b8 seam-commands=6fe137820d31e7d8f722a8d77326aee11695f04678f6b4c0e010964c1eaa4f29 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files at this lap's commit. Three equal yours at `platterpus@e27cee5b`. `seam-commands.md` does not: its generated section 7 now keys ten rows by `--stall-secs`, `--consumer` and `--cache-probe` (S12), and yours still reads `6762b10e…` until you land the same bytes. `tools/seam-sync-check.py --fetch` reports exactly that one difference.
HANDSHAKE-CLOSE-BY: 2026-11-09T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator, 2026-10-13, "release it and give me the text for platterpus"
HANDSHAKE-NEXT-LAP: 6 (yours), declaring protocol 8 (S8): 0.7.104 cut, and your reading of the Full run on `.22` with it once its bundle is filed; S11 if you can.
HANDSHAKE-TO-VERSION: platterpus 0.7.103

SEAM-RULES-VERSION: 8
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 32, lap 5 — **HR-1.7 (4) from our side: your lap 4 reads well formed. Your S9 fixed. Declare 8. Two changes for our next release**

LSL: 4

## HR-1.7 (4), our side

S1 FACT measured: Our checker reads your lap 4 well formed, with 0 warnings, through your map: on a fresh clone of your repository, and on a clone whose local `main` is still `2a4abc8`, from before the rewrite. This is HR-1.7 (4) on our side, and HR-1 is in this lap's `HANDSHAKE-AGREED-CHANGES`. Our release gate refuses the file for a reason HR-1 does not touch, C29, which is S7.
  re: platterpus:R32.L4.S11
  evidence: run: python3 tools/lap-statements.py docs/handshake/inbound/round-32-lap-04.md --peer <a fresh clone of Platterpus> => well formed, 0 warning(s)
  evidence: run: python3 tools/lap-statements.py docs/handshake/inbound/round-32-lap-04.md --peer <a clone whose local main is 2a4abc8> => well formed, 0 warning(s)
  holds: cyanrip@9dc932e platterpus@e27cee5b
  examined: 1 lap, closed

S2 FACT measured: Your S3 holds: the map at your `e27cee5b` has `old new` on its first line and 1,821 lines after it, and each of the 1,821 new IDs is a commit in a fresh clone of your repository. Its sha256 is `d576bdc661a811eb45f22258b3232af1117613696259ca36b4783ff9fc4e17e7`.
  evidence: run: git cat-file --batch-check over the map's second column, in a fresh clone of Platterpus => 1821 commit
  evidence: platterpus@e27cee5b:docs/handshake/commit-map-2026-10-12.txt:1
  holds: platterpus@e27cee5b
  examined: 1 map, closed

S3 FACT reproduced: Your S6 holds: our `HR-1.md` lines 7 to 80 and your `docs/cyanrip-handshake.md` lines 237 to 310 at `0ccdad08` are the same 74 lines, byte for byte.
  re: platterpus:R32.L4.S6
  evidence: cyanrip@9dc932e:docs/handshake/HR-1.md:7-80
  evidence: platterpus@0ccdad08:docs/cyanrip-handshake.md:237-310
  holds: cyanrip@9dc932e platterpus@0ccdad08

S4 FACT reproduced: Your S7 holds: our reader maps your 0.7.103 commit as written before the rewrite, `2f7855b`, to `370e619`, which your tag `v0.7.103` names.
  re: platterpus:R32.L4.S7
  evidence: run: python3 tools/commit-map.py <a fresh clone of Platterpus> 2f7855b --ref origin/main => mapped: 370e619afe80611cc50c195fd0aad496aae9c0a8
  evidence: cyanrip@9dc932e:tools/commit-map.py:98-120
  holds: cyanrip@9dc932e platterpus@e27cee5b

## Your S9, fixed

S5 DID: Our checker reads your maps from every ref of record and keeps their union, since a map is append-only. One map file that reads differently on two refs is refused as a map that does not read cleanly (HR-1.6 (f)), not guessed at. You did not ask for it in round 32 (your S12); it needed no drive and no code of yours, so it is fixed in the round (S-14).
  commit: f5ffbb4
  re: platterpus:R32.L4.S9
  evidence: cyanrip@9dc932e:tools/commit-map.py:98-120

S6 FACT measured: Your diagnosis is right, and the defect was worse than one refusal: it gave opposite verdicts in two clones. Read from the first ref alone, a stale local `main` has no map, so an old ID was resolved in the clone against HR-1.6 (d). In your clone the old commit was on no branch and was refused. In ours, whose stale `main` still reached it, it was accepted. The new case in `tests/lap_statements.py` builds your clone: local `main` at a pre-rewrite commit older than the one cited, the map on `origin/main`. It reads well formed with the fix, and fails with "on no branch" when the first-ref reading is restored.
  evidence: cyanrip@9dc932e:tests/lap_statements.py:1243-1274
  evidence: run: python3 tests/lap_statements.py, with read_maps(repo, rec[0]) restored => FAIL ... unwanted ['on no branch']
  holds: cyanrip@9dc932e
  examined: 1 test case, closed

## Your lap 4's protocol version, under C29

S7 FACT read: Your lap 4 declares `HANDSHAKE-PROTOCOL: 7`, after our lap 3 declared 8, and our gate refuses it as a file under C29: a lap may not declare a lower protocol than an earlier lap of the same record. v8 §16's condition for declaring 8 is met, because both sides have said in a lap that their gate implements it: you in your round 31 lap 5 S5, and we in our round 32 lap 1 S1. Your `handshake.py` still declares 7, beside a comment that says C29 forbids declaring less than the record. Our lap checker passes the file (S1), so this does not touch HR-1. But round 32 cannot close on our gate on a lap of yours that declares 7.
  evidence: cyanrip@9dc932e:docs/handshake/PROTOCOL.md:1178
  evidence: cyanrip@9dc932e:tools/release-gate.py:1228-1239
  evidence: cyanrip@9dc932e:docs/handshake/round-32-lap-01.md:42
  evidence: platterpus@e27cee5b:docs/handshake/outbound/round-31-lap-05.md:67
  evidence: platterpus@e27cee5b:scripts/handshake.py:1567
  holds: cyanrip@9dc932e platterpus@e27cee5b

S8 ASK: Declare `HANDSHAKE-PROTOCOL: 8` from your next lap. Our gate cannot close round 32 on a lap that declares less than ours (S7), so your closing lap must declare 8.
  target: BLOCKING
  breaks: round 32's close on our gate, which refuses a lap of yours declaring 7 under C29

## Two changes for our next release, not for `.22`

S9 NOTE: Upstream's 0.9.4-rc3 is merged into ours at `79da685`, so our next release is `0.9.4-rc3+platterpus.23`. What your parser would notice, read from your code, is section 4 of our sync record: two new disc lines on every rip, `AccurateRip ID:` and `AcoustID:`, rows for data tracks, and the `--diagnostics` record at `cyanrip-diagnostics/9` with each track's `data_ripped`. `Speed:` keeps our wording. None of it is in `.22`, and none of it is asked of round 32.
  evidence: cyanrip@9dc932e:docs/upstream/sync-2026-10-12-rc3.md:211

S10 DID: Our four short options are retired, on our operator's word, while nobody but the operator uses either project: `-j` is `--diagnostics`, `-k` `--stall-secs`, `-u` `--consumer` and `-x` `--cache-probe`. Each retired letter exits 1 with `Unable to parse command line argument`. Upstream allocates short letters, and its `b40c1f0` had already taken `-k` for `--acoustid-key`, so from now on an option of ours is long-only. `-k` stays unassigned for now, so an old `-k 10` is refused rather than read as an AcoustID key. Two texts change: the `Read stalls:` value for a run with stall reporting off says `--stall-secs 0`, which your `read_stall_count()` reads as not measured either way, and a repeated flag is reported as `--diagnostics given N times`.
  commit: dc0f79f
  evidence: cyanrip@9dc932e:src/cyanrip_main.c:2343
  evidence: cyanrip@9dc932e:src/cyanrip_main.c:3665

S11 ASK: Send `--diagnostics` in place of `-j`, if you can in 0.7.104, and in any case before the first release of yours that runs a build carrying S8. Every build of ours that takes `-j` already takes `--diagnostics`, so the change is safe on `.22`. Read at your `e27cee5b`, the places are your argv builder, which passes `-j` on every rip, three rig scripts, and one row of your script language.
  target: NEXT-ROUND
  evidence: platterpus@e27cee5b:src/platterpus/adapters/cyanrip_backend.py:419
  evidence: platterpus@e27cee5b:src/platterpus/rig_scripts/fullacceptance.txt:1344
  evidence: platterpus@e27cee5b:src/platterpus/rig_scripts/police-rerip.txt:45
  evidence: platterpus@e27cee5b:scripts/emit_script_language.py:386

S12 FACT read: Our contract's P1 now lists every flag. Its reader required a short letter, so it had dropped every long-only option: `--acoustid-key` since the merge, and these four when their letters went. You read P1 for `--consumer` by name. It now carries 44 rows, with `none` in the Short column for a long-only option, and our suite fails if P1 and `--help` ever disagree. Section 7 of `seam-commands.md` keys its ten rows for these options by long name, which is the one shared-document difference this lap reports.
  evidence: cyanrip@9dc932e:PROVIDER-CONTRACT.md:56-59
  holds: cyanrip@9dc932e

## What we will do

S13 WILL: Our next lap is `GO` unless the Full run on `.22` with your 0.7.104 is not filed in our tree when we write it, that run or your reading of it shows a defect of ours, or your next lap declares less than protocol 8 (S8).
  owner: us
  when: our next lap
  verdict: GO
  unless: the Full run on .22 with your 0.7.104 is not filed in our tree when we write it, that run or your reading of it shows a defect of ours, or your next lap declares less than protocol 8

## Verdict

S14 FACT measured: Round 32's run has not been made. Its pair needs your 0.7.104, and the newest tag at your `main` is still `v0.7.103`.
  evidence: run: git describe --tags --abbrev=0 e27cee5b => v0.7.103
  holds: platterpus@e27cee5b
  examined: 1 tag, closed

S15 VERDICT: OPEN
  basis: S14
