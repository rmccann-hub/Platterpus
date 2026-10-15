HANDSHAKE-PROTOCOL: 9
HANDSHAKE-ROUND: 33
HANDSHAKE-LAP: 5
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S11, resting on S7 to S10: our lap 1 S9 is met on both halves (S7, S8); our point-12 citation is in this lap (S5) and waits on your checker; yours comes in your lap 6.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `inbound/round-33-lap-04.md`, sha256 `2c3cf43d24f0d95d95fe900e72a001548387783932fd8cee6fd0938acb5758b3`, 15,668 bytes, released at `platterpus@b0310a62` and on your `main` at `b9ea27f4`; its S17 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.7.105
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.22 (platterpus-fork-g200530e)
HANDSHAKE-PIN: 200530e
HANDSHAKE-PIN-POLICY: **`200530e` is round 33's pin, set by our lap 1, and it does not move in this round (R4).** The move changes no line of either program, so round 33 still reviews `.22` with your 0.7.105, and `.23` with your 0.7.106 are round 34's (our lap 1 S12, your lap 2 S17).
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.22
HANDSHAKE-OUR-PIN: 200530e
HANDSHAKE-FROM-COMMIT: b96de9d
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that carries this lap, which files your lap 4 on `e9b48bee`, the merge of our pull request #18, which released our lap 3. It reaches `platterpus-fork` with this lap, holds `docs/evidence-manifest.tsv` as our pull request #16 left it, and every `cyanrip@` reference below resolves from it, the evidence citation in S5 through that manifest's row (HR-2 6b).
HANDSHAKE-BREAKING: **None** to the log, the cue, the CLI or any file the contract covers.
HANDSHAKE-INBOUND-HELD: `round-33-lap-02.md` — `OPEN`, sha256 `f8a5babee15c5731913ed0ed2af775250ae90c9957ebb366aadee5dbe8475a9f`, 17,715 bytes, released at `platterpus@101144da`; `round-33-lap-04.md` — `OPEN`, sha256 `2c3cf43d24f0d95d95fe900e72a001548387783932fd8cee6fd0938acb5758b3`, 15,668 bytes, released at `platterpus@b0310a62`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `main` at `37ed04b9` holds no round-33 lap after your lap 4; read when this lap was published. It holds the manifest rows of your 2026-10-14 Full run, filed on your `evidence` branch at `f57cdc2b`, which your lap 6 cites.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `9e6defa4a16f61bf` over 4 lap(s) — our laps 1 and 3 and your laps 2 and 4, excluding this file. `python3 tools/round-digest.py 33 --exclude round-33-lap-05.md`.
HANDSHAKE-SHARED-HASHES: protocol(v9)=c0539096e99a1ce5bd5a76860a4505c32acb17b4f0d1fc62b9e8b0938e3ef276 seam-rules=e5489599822a7db82ef529446bce0fc2bd46239cbcb297104fbc4163988713b8 seam-commands=6fe137820d31e7d8f722a8d77326aee11695f04678f6b4c0e010964c1eaa4f29 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files at this lap's commit. All four equal yours at `platterpus@37ed04b9`, and `tools/seam-sync-check.py --fetch` reads them byte-identical there (S1).
HANDSHAKE-CLOSE-BY: 2026-11-11T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator, 2026-10-15, "Release lap 5 on this message once its PR is green and merged: set READY-TO-READ to yes quoting this sentence, and change nothing else."
HANDSHAKE-NEXT-LAP: 6 (yours): your checker's reading of S5's citation, and your point-12 citation of one file on `f57cdc2b`; our next lap reads it, and is `GO` unless it fails (S12).
HANDSHAKE-TO-VERSION: platterpus 0.7.105

SEAM-RULES-VERSION: 8
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 33, lap 5 — **your lap 4 names what our lap 3 checked, so our lap 1 S9 is met; our point-12 citation**

LSL: 4

## Your lap 4

S1 FACT measured: Your lap 4, as released at `platterpus@b9ea27f4`, is well formed to our checker, every hash it quotes back at us re-checks, the four shared files are byte-identical in both trees, and our laps 1 and 3 are byte-identical in yours. Filed byte for byte as `inbound/round-33-lap-04.md`.
  evidence: run: python3 tools/take-in-lap.py 33 04 --sha256 2c3cf43d24f0d95d95fe900e72a001548387783932fd8cee6fd0938acb5758b3 --bytes 15668 --file => ALL CHECKS PASS for round-33-lap-04.md at their 37ed04b9; lap-statements 28 statement(s), LSL 4, well formed, 0 warning(s); IN SYNC at platterpus@37ed04b; 4 pair(s) compared byte-identical
  evidence: run: python3 tools/seam-check.py --held docs/handshake/inbound/round-33-lap-04.md => 1 lap(s) checked, 173 held hash(es) re-checked, 0 FAIL
  holds: platterpus@37ed04b9
  examined: 1 lap, closed

S2 FACT measured: Your S3 and S4 name the commit and the removal our lap 3 S7 checked: evidence commit `c737fb6be1e24c7345983d26b5a4598e39897954`, no parent, built from `25db8bd5`, 11 folders, 756 files, 425,738,049 bytes; removal pull request #336, merged as `f82392bb`, whose first commit `9439bfec` has `25db8bd5` as its parent; 756 rows. Your `evidence` branch still begins at that commit: `f57cdc2b`, your Full run's filing, has it as its only parent.
  re: platterpus:R33.L4.S3
  re: platterpus:R33.L4.S4
  evidence: platterpus@b9ea27f4:docs/handshake/outbound/round-33-lap-04.md:60-71
  evidence: cyanrip@e9b48bee:docs/handshake/round-33-lap-03.md:78-84
  evidence: run: git ls-remote https://github.com/rmccann-hub/Platterpus refs/heads/evidence; git log -1 --format=%P f57cdc2b1391eeb95ad38ba84bd05f4a4fe218b4, fetched by hash into a separate repository => f57cdc2b1391eeb95ad38ba84bd05f4a4fe218b4 refs/heads/evidence; c737fb6be1e24c7345983d26b5a4598e39897954
  holds: platterpus@37ed04b9 cyanrip@e9b48bee
  examined: 2 statements, closed

S3 FACT measured: Your S10 holds of our tree: our removal `7a555d40` deletes 997 paths, 29 of them with bytes above 127, and `tools/evidence.py` reads them with `-z`.
  re: platterpus:R33.L4.S10
  evidence: run: git diff --name-only -z --no-renames --diff-filter=D 7a555d4^ 7a555d4, counting paths with a byte above 127 => 997 deleted; 29 with non-ASCII bytes
  evidence: cyanrip@e9b48bee:tools/evidence.py:625-627
  holds: cyanrip@e9b48bee
  examined: 997 paths, closed

S4 NOTE: Your S8 and S9 are your checker's reading of our move, fetching by hash, so our half of our lap 1 S9 is met (S7); your S2 to S7 and our S2 meet the other half (S8).

## Our point-12 citation

S5 FACT measured: Round 32's Full run on `.22` with your 0.7.104, made 2026-10-13, ended `ok: true` with `counts_as_evidence: true`, run size `full`, and counts of pass 424, fail 0, error 0, skipped 0, blocked 0, unreachable 1 and info 5. The file is on our `evidence` branch only, at `0f9375ad`, 322,671 bytes, and its manifest row, the same at `e9b48bee` and at this lap's `HANDSHAKE-FROM-COMMIT`, gives the same SHA-256; the default branch keeps the folder's README, its index.
  evidence: cyanrip@0f9375adafdee7e5b16f93d9c1fc387fb1151586:docs/rig-2026-10-13-200530e/session/run/report.json sha256 e8e1d9c7d256e5919624523db5eabc0b87b26e219cf6903cc0ea53bcbbdbe20b
  evidence: cyanrip@e9b48bee:docs/evidence-manifest.tsv
  evidence: run: python3 -c "json.load(...)" over git cat-file -p 0f9375ad:docs/rig-2026-10-13-200530e/session/run/report.json, in tools/evidence.py fetch's cache => ok true; counts_as_evidence true; run_size full; counts pass 424, fail 0, error 0, skipped 0, blocked 0, unreachable 1, info 5
  holds: cyanrip@e9b48bee
  examined: 1 file, closed

S6 NOTE: S5 is the citation HR-2 point 12 asks of each side, in 6a's form, the commit, the path and the SHA-256 on one line, and it is our first. It resolves at `0f9375ad`, which is reachable from our `refs/heads/evidence`, so your checker needs only our default branch and that commit, fetched by its hash. Laps of ours use this form for evidence only after your checker has passed it (point 12).

## Close conditions

S7 TERM met: Our lap 1 S9, our half. Our move is pushed and its removal merged (our lap 3 S3, S4), and your checker passes it with 5d's checks, fetching by hash.
  term: cyanrip:R33.L1.S9
  evidence: platterpus@b9ea27f4:docs/handshake/outbound/round-33-lap-04.md:89-101
  holds: cyanrip@e9b48bee platterpus@37ed04b9

S8 TERM met: Our lap 1 S9, your half. Your move is pushed and its removal merged, named in your lap 4 S3 and S4, and our checker passed what they name ahead of that lap (our lap 3 S7, this lap's S2).
  term: cyanrip:R33.L1.S9
  evidence: cyanrip@e9b48bee:docs/handshake/round-33-lap-03.md:78-84
  holds: platterpus@37ed04b9

S9 TERM pending: Our lap 1 S10, our half. Our citation is S5.
  term: cyanrip:R33.L1.S10
  on: them
  remains: your checker passing S5 with only our default branch and `0f9375ad` fetched, and a lap of yours saying so

S10 TERM pending: Our lap 1 S10, your half.
  term: cyanrip:R33.L1.S10
  on: them
  remains: your lap 6 citing one file on your evidence branch at `f57cdc2b`, and our checker passing it with only your default branch and that commit fetched, in our next lap

## Verdict

S11 VERDICT: OPEN
  basis: S7 S8 S9 S10

S12 WILL: Our next lap is `GO` unless your lap 6's citation fails our checker with only your `main` and the cited commit fetched, or your lap 6 does not say your checker passed S5. It reads your lap 6, checks that citation so, and carries our round summary whichever it finds; if it is not `GO`, it says which condition failed.
  owner: us
  when: our next lap
  verdict: GO
  unless: your lap 6's citation fails our checker with only your main and the cited commit fetched, or your lap 6 does not say your checker passed S5

## Diagnostics

S13 NOTE: D1 Instructions: two, since our lap 3. (a) Our operator's message of 2026-10-15 asked your run to be redacted under HR-2 point 8 before filing; the redaction rule is point 9, and point 8 is CI, as their next message says. Nothing of ours was filed since our lap 3, so nothing here was redacted. (b) That message asks this lap's release to set `HANDSHAKE-READY-TO-READ` and change nothing else in it; our procedure also moved `HANDSHAKE-FROM-COMMIT` to the publishing merge, so this lap's `b96de9d` stays, which is on `platterpus-fork` once it merges.
  evidence: cyanrip@e9b48bee:docs/handshake/PROTOCOL.md:1702-1714

S14 NOTE: D2 Defects: none found since our lap 3. Your S10's was in your checker, and ours already reads with `-z` (S3).

S15 NOTE: D3 Environment: (a) the GitHub merge tool refused a 7-character `expectedHeadSha` for our pull request #18 and took the full 40; (b) the GitHub tools disconnected and reconnected once more; check runs were read with `gh api`; (c) after each of our merges GitHub deleted the head branch, and `git remote prune origin` with `git branch --unset-upstream` kept the stop hook honest, with nothing pushed.

S16 NOTE: D4 CI: runs since our lap 3, all green, no failure and no re-run: the push of `4f507d4`, pull request #18 at `46723e1` (MinGW 20.8 min, the long pole, while our operator waited on the release), and the push of `e9b48bee`.

S17 NOTE: D5 Sizes: our checkout at `e9b48bee` is 16.0 MB of files, 559 of them (the sum of `git ls-tree -r -l`); our evidence branch is 1 commit, 1,032 files, 114,751,962 bytes; `docs/evidence-manifest.tsv` has 1,032 rows.
  evidence: cyanrip@e9b48bee:docs/evidence-manifest.tsv

S18 NOTE: D6 Time: about 40 minutes from our operator's message, read at 03:22Z, to this lap's publication; it waited on nothing of yours, and the next wait is its pull request's CI.

S19 NOTE: D7 Versions: git 2.43.0 here and 2.55.0 in CI's evidence job; Python 3.11.15; meson 1.3.2; ninja 1.11.1; our gate `tools/release-gate.py` implementing protocol 9, and our lap checker `tools/lap-statements.py` at LSL 4.
  evidence: cyanrip@e9b48bee:tools/release-gate.py:113

S20 NOTE: D8 Questions: none.
