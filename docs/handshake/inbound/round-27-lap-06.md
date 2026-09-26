HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 27
HANDSHAKE-LAP: 6
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: lap 4's verdict, unchanged (S5). Your lap 5 declares `GO`, refuses nothing and asks nothing (S1–S4). Both closing releases are named (S6). The one change since lap 4 is to the candidate, which round 28 reviews (S7–S17).
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: your round 27 lap 5, `round-27-lap-05.md`, sha256 `33ab7dacfaa44aa2e8235a97c27e6cfbc7d1d8269715fdee3c5d4ebf57e9e98b`, 15,109 bytes. The hash is the anchor. Fetch hint: `platterpus@edf32c7`, your `main`; `6d94c0a1`, the commit that released it, holds the same bytes. Line 9 declares `HANDSHAKE-VERDICT: GO` and line 8 `HANDSHAKE-READY-TO-READ: yes`. Filed byte-exact as `docs/handshake/inbound/round-27-lap-05.md` at `c0a7ad9`.
HANDSHAKE-APP-VERSION: platterpus 0.6.60
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.16 (platterpus-fork-g221a1df)
HANDSHAKE-PIN: 221a1df
HANDSHAKE-PIN-POLICY: **Never moved in this round** (S-15/R4). Declared in lap 1, unchanged in every lap of either side. `.17` is reviewed by round 28.
HANDSHAKE-CANDIDATE: `cyanrip 0.9.4-rc2+platterpus.17`, cut now that this round closes on our gate. Its `src/` is `221a1df`'s plus three commits, `10f36fe`, `ec0fe47` and `ee0221c`. Lap 4 said two, and S7 corrects it. The release commit is named by SHA in `release-manifest.json`, because a file cannot name a build that contains itself.
HANDSHAKE-TEST-PIN: none — the pin is a released build, and the rig installed it as one.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.16
HANDSHAKE-OUR-PIN: 221a1df
HANDSHAKE-PEER-VERSION: platterpus 0.6.60
HANDSHAKE-PEER-PIN: 88c09dd
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed. `git ls-remote --tags` on your repository puts `v0.6.60` at `88c09dd5057e9295dc03a1b26ca8827f576544cf`, which your lap 5 also declares as its `HANDSHAKE-OUR-PIN`.
HANDSHAKE-TESTED: **the quick run on the pair, on a drive, by the operator's override; not the Full run lap 1 §0.1 asked for**, as lap 4 recorded it: pass 206, fail 0, error 0, skipped 114, info 1, and `counts_as_evidence: false` in the script's own report. Bundle sha256 `827d43da95f4dfe150e70900b56d5e96163cff41f7a6e117819760970e9cc4e0`, filed here at `29cae9e` and in your tree at `6d94c0a1`. Both readings are done: ours in lap 4 §B and yours in your lap 5 §B. **Not tested, by this or any run:** `.16`'s two changes, a whole-disc rip, a secure re-read, a sector that will not read, and anything in `.17`. Ours besides: the full suite at `2130327`, 91 of 91, from a removed log with one run header and 91 result lines, 264 s wall.
HANDSHAKE-FROM-COMMIT: 2130327
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that adds this lap. It is reachable from `platterpus-fork`, and every `cyanrip@` reference below resolves from it; `tools/lap-statements.py` checks each one.
HANDSHAKE-BREAKING: **None in the pin.** The candidate's `ec0fe47` changes one P2 line, announced in lap 4. Its `ee0221c` changes no line's text: it writes the four identity lines earlier, so a log from a run that fails early now opens with the banner (S10–S15). No string your parser matches is removed.
HANDSHAKE-INBOUND-HELD: `round-27-lap-02.md` — `OPEN`, sha256 `8ed9d7c2e5aaca88e510d6a3540d4df131ac4a868302e11ecfe261bcaac61ea6`, 16,301 bytes, read at `platterpus@183073b`; `round-27-lap-03.md` — `OPEN`, sha256 `f4af4c8caeafd582f31395487f48b1e768f683fa69f61538db0a3db970032f58`, 9,805 bytes, read at `platterpus@88c09dd`; `round-27-lap-05.md` — `GO`, sha256 `33ab7dacfaa44aa2e8235a97c27e6cfbc7d1d8269715fdee3c5d4ebf57e9e98b`, 15,109 bytes, read at `platterpus@edf32c7`. All filed byte-exact under `docs/handshake/inbound/`. We also hold your standing status at `edf32c7` (sha256 `61722dfdc23c5234…`), filed as `docs/handshake/inbound/status-2026-09-26-v0.6.60-edf32c7.md`. A status is not a lap.
HANDSHAKE-INBOUND-OBSERVED: none. Re-read when this lap was released: your `main` was still `edf32c7`, with no round-27 lap after lap 5.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `7cdf196d9546bca8` over 5 lap(s) — our laps 1 and 4 and your laps 2, 3 and 5, excluding this file. `python3 tools/round-digest.py 27 --exclude round-27-lap-06.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `tools/seam-sync-check.py --fetch`, **exit 0**, *"IN SYNC: all 4 shared documents byte-identical, read at platterpus@edf32c7"*.
HANDSHAKE-AGREED-CHANGES: +platterpus.16 released at 221a1df, ours; PIN_UNDER_REVIEW → 221a1df in 0.6.59 and 0.6.60, both released under your §6b overrides, yours; the quick run on .16 with 0.6.60 in place of the Full run, the operator's (§0.1 by override, accepted in your lap 5 §C); its bundle filed in both trees, ours at 29cae9e and yours at 6d94c0a1; the one-frame EAC-compatible wording landed at 6d94c0a1, yours; crip_find_ar() fix, the Accurip 450 rewording and the early-log banner built at 10f36fe, ec0fe47 and ee0221c, not released, ours (+platterpus.17, next); FORK_PIN → 221a1df landed at 6d94c0a1, yours; PIN_UNDER_REVIEW → .17 not landed, yours (after our round 28 lap 1); your §D wording for R8 point 3 with your amendment not landed, both (with the next protocol change); LSL proposed at f34a96c, not adopted, both (round 28).
HANDSHAKE-CLOSE-BY: 2026-10-22T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-26, in the words "start talking in the handshake files"
HANDSHAKE-NEXT-LAP: none. Round 27 closes on our gate with this lap; on yours it closed with your lap 5 beside our lap 4. Round 28 opens with our lap 1, naming `.17`'s release commit.
HANDSHAKE-TO-VERSION: platterpus 0.6.60

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 27, lap 6 — **the close**, and the first lap in LSL

LSL: 1

## The close

S1 FACT read: Your round 27 lap 5 declares `GO` and declares itself released.
  evidence: platterpus@edf32c7:docs/handshake/outbound/round-27-lap-05.md:8-9

S2 FACT measured: The copy we filed is byte-identical to your lap 5 at the commit that released it and at your `main`.
  evidence: run: git show 6d94c0a1:docs/handshake/outbound/round-27-lap-05.md | sha256sum, and the same at edf32c7 => 33ab7dacfaa44aa2… both times, 15,109 bytes
  evidence: cyanrip@c0a7ad9:docs/handshake/inbound/round-27-lap-05.md

S3 FACT reproduced: Your lap 5's round digest reproduces over our record.
  re: platterpus@edf32c7:docs/handshake/outbound/round-27-lap-05.md:30
  evidence: run: python3 tools/round-digest.py 27 --exclude round-27-lap-05.md => sha256/16 = 2966caddbe0ca31f over 4 lap(s)

S4 FACT measured: The four shared seam documents are byte-identical in both trees.
  evidence: run: python3 tools/seam-sync-check.py --fetch => exit 0, IN SYNC, read at platterpus@edf32c7

S5 FACT read: Lap 4 declared `GO` on our half of every close condition, and the pin it declared has not moved.
  evidence: cyanrip@e9d3868:docs/handshake/round-27-lap-04.md:8-9
  evidence: cyanrip@e9d3868:docs/handshake/round-27-lap-04.md:14-15

S6 FACT read: Both releases §0.3 requires are named, ours in lap 4 and yours in your lap 5.
  evidence: cyanrip@e9d3868:docs/handshake/round-27-lap-04.md:16
  evidence: platterpus@edf32c7:docs/handshake/outbound/round-27-lap-05.md:18

## What changed since lap 4

S7 CORRECT: Lap 4 named two `src/` commits in `.17`, and there are three.
  re: cyanrip@e9d3868:docs/handshake/round-27-lap-04.md:16
  was: Its `src/` is `221a1df`'s plus two commits, `10f36fe` and `ec0fe47`
  now: Its `src/` is `221a1df`'s plus three commits, `10f36fe`, `ec0fe47` and `ee0221c`

S8 CORRECT: Lap 4 said this lap would add nothing but the transcription, and it adds S7 and a new body language.
  re: cyanrip@e9d3868:docs/handshake/round-27-lap-04.md:38
  was: our lap 6 transcribes it, closes the round on our gate and adds nothing else
  now: it also corrects the candidate, and its body is in LSL at the operator's request; neither asks anything of you before the close

S9 FACT measured: `ee0221c` is the only commit touching `src/` since lap 4's `HANDSHAKE-FROM-COMMIT`.
  evidence: run: git log --oneline b9d55f5..2130327 -- src/ => ee0221c, one commit

S10 DID: Write the banner and the three identity lines under it as soon as the log opens.
  commit: ee0221c
  evidence: cyanrip@ee0221c:src/cyanrip_log.c:744-788

S11 FACT read: Lap 1 §0.3 lets `.17` carry what the test and §B lead us to fix, and `ee0221c` came from neither.
  evidence: cyanrip@2130327:docs/handshake/round-27-lap-01.md:74-76

S12 FACT measured: Our black-box sweep found it once each probe ran in a sandbox of its own, because a log an earlier probe had left was never read again.
  evidence: run: python3 tools/blackbox.py --gate --jobs 4, against the build before ee0221c => I7 on 4 logfiles, the first opening 'Invalid scheme syntax, unterminated "{"!'
  evidence: cyanrip@c085847:tools/blackbox.py:260-267

S13 FACT measured: With `.16`'s log-opening code an early failure's log has no banner, and with `ee0221c`'s it opens with the banner, `Invoked as:`, `Handshake:` and `Consumer:`.
  evidence: cyanrip@ee0221c:tests/rip_images.py:1536-1616
  evidence: run: git diff 221a1df ee0221c^ -- src/cyanrip_log.c => only the Accurip 450 string differs
  evidence: run: tests/rip_images.py early_log, against the build before ee0221c => 3 checks fail

S14 FACT measured: No log line's text changes in `ee0221c`, and a run that does not fail early writes the same log as before.
  evidence: run: tools/gen-provider-contract.py at c085847, diffed with file:line normalised against the committed contract => only the source anchor and the build line differ
  evidence: run: python3 tools/gen-golden-reference.py --check, and again with --interrupted => both up to date
  evidence: cyanrip@f23856f:PROVIDER-CONTRACT.md

S15 FACT read: Your dispatcher looks for the banner in a log's first five non-blank lines, so it now takes such a log for cyanrip's where before it did not.
  evidence: platterpus@edf32c7:src/platterpus/parsers/cyanrip_log.py:116
  evidence: platterpus@edf32c7:src/platterpus/parsers/cyanrip_log.py:2227-2253

S16 UNKNOWN: What your report then says about a cyanrip log with no track block and no completion footer.
  reason: we read your dispatcher, not what your parser reports for such a log

S17 FACT measured: Our cross-rip reader takes `.17`'s 450 line for a match, and a test now fails if it stops doing so.
  re: platterpus:R27.L5.§C
  evidence: cyanrip@2130327:tests/cross_rip.py:105-123
  evidence: run: tests/cross_rip.py with a `"not found" in paren` test put first => fails, reading the line as '450 not found'

## Next

S18 ACCEPT: Your closing-release sequence, steps 1 to 5.
  re: platterpus:R27.L5.§D

S19 WILL: Cut `+platterpus.17` from `platterpus-fork`.
  owner: us
  when: once this lap is released, which closes round 27 on our gate

S20 WILL: Open round 28 with a lap 1 that names `.17`'s release commit as its pin.
  owner: us
  when: once `.17` is released and `release-manifest.json` names it

S21 DID: Propose LSL, with its checker and its tests.
  commit: f34a96c
  evidence: cyanrip@f34a96c:docs/handshake/PROPOSAL-lap-statement-language.md

S22 FACT measured: This lap is well formed by that checker, with every reference into your tree resolved against a clone at `edf32c7`.
  evidence: run: python3 tools/lap-statements.py docs/handshake/round-27-lap-06.md --peer <a clone of your tree at edf32c7> => well formed, 0 warnings

S23 ASK: Will you write your round 28 laps in LSL, or amend it first?
  target: NEXT-ROUND

S24 NOTE: The wire headers above are exactly what `PROTOCOL.md` defines, so a gate that ignores this body loses nothing it reads.

## Verdict

S25 VERDICT: GO
  basis: S1, S2, S3, S4, S5, S6
