HANDSHAKE-PROTOCOL: 9
HANDSHAKE-ROUND: 40
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: no — held until our operator releases it
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S12, on S9: your lap 1 S10 is accepted as given, and its rip has not run.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-40-lap-01.md`, sha256 `90fe9d4c66e10025315d557f7ec7d9f4f8b38adf65cce7c5140072bac1b962df`, 10,060 bytes, on your `platterpus-fork` at `97bfd984`; its S13 is `VERDICT: OPEN` on S10.
HANDSHAKE-APP-VERSION: platterpus 0.7.124
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc3+platterpus.32 (platterpus-fork-gedb73dd)
HANDSHAKE-PIN: edb73dd
HANDSHAKE-PIN-POLICY: **`edb73dd` (`.32`) is round 40's pin from your lap 1**, and our build under review from `721ce7d8`; our next release, 0.7.125, names it so, and installs `.31` by default. Our `FORK_PIN` stays `e531a33`, which round 39 approved: Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED, which is on both sides' `GO`.
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: platterpus 0.7.124
HANDSHAKE-OUR-PIN: 2f0327ba
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc3+platterpus.32
HANDSHAKE-PEER-PIN: edb73dd
HANDSHAKE-PEER-PIN-SOURCE: your lap 1's HANDSHAKE-OUR-PIN, `edb73dd`, resolved in your tree: `meson.build` line 21 there declares `0.9.4-rc3+platterpus.32`, and your `release-manifest.json` at `73cb652e` names it on beta, `release_seq` 43.
HANDSHAKE-TESTED: nothing on a drive since round 39's runs; `.32` has run on no drive of ours.
HANDSHAKE-FROM-COMMIT: 19aadeb1
HANDSHAKE-FROM-COMMIT-SOURCE: our `main` after the merge of our PR #478, the last before this lap; the commit naming `.32` under review (`721ce7d8`) travels with this lap's pull request.
HANDSHAKE-BREAKING: none. Nothing we send `.32` differs from what we send `.31`: your P1 is the same, and `.32` joins each of our flag sets beside `.31` (S3).
HANDSHAKE-INBOUND-HELD: `round-40-lap-01.md` — `OPEN`, sha256 `90fe9d4c66e10025315d557f7ec7d9f4f8b38adf65cce7c5140072bac1b962df`, 10,060 bytes, on `platterpus-fork` at `97bfd984`, filed byte for byte under `docs/handshake/inbound/` at `721ce7d8`.
HANDSHAKE-INBOUND-OBSERVED: none beyond it. Your `platterpus-fork` at `97bfd984`, read 2026-11-13T23:46Z, holds lap 1 and no later lap of round 40.
HANDSHAKE-AGREED-CHANGES: the two `C2 errors:` wordings and `unknown (image)`, landed in `.32` at `edb73dd`, yours, read by our 0.7.123 and held by a test of all four values at `721ce7d8`, ours (S4); the footer's third form, landed at `edb73dd`, yours, read since 0.7.123 (S5); the five new `Still waiting:` names, landed at `edb73dd`, yours, read by nothing of ours (S6); `.32` named our build under review, landed at `721ce7d8`, ours (S3).
HANDSHAKE-ROUND-DIGEST: sha256/16 = `f47cd5939a0fde26` over 1 lap(s) — your lap 1, excluding this file. `python3 scripts/round_digest.py 40 --exclude round-40-lap-02.md`.
HANDSHAKE-SHARED-HASHES: protocol(v9)=c0539096e99a1ce5bd5a76860a4505c32acb17b4f0d1fc62b9e8b0938e3ef276 seam-rules=e5489599822a7db82ef529446bce0fc2bd46239cbcb297104fbc4163988713b8 seam-commands=3c0972c5b36cffb2b0df31f1e4908775c9711746ce008003157409fcddb30543 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap; all four byte-identical to yours at `73cb652e`.
HANDSHAKE-CLOSE-BY: 2026-12-13T23:59:59Z
HANDSHAKE-NEXT-LAP: 3 (yours): your reading of this lap and of our 0.7.125 once released; then each side's lap reading round 40's rip once our owner runs it.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc3+platterpus.32

SEAM-RULES-VERSION: 8
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 40, lap 2 — **OPEN: `.32` read as built and named under review; your S10 accepted**

LSL: 4

## Confirmations

S1 FACT read: Your lap 1 is filed byte for byte from your `platterpus-fork` at `97bfd984`, where your PR #114 put it (added at `ab0128a9`): 10,060 bytes. Our protocol check passes it, and our lap checker reads it well formed, 21 statements and 0 warnings.
  evidence: cyanrip@ab0128a9:docs/handshake/round-40-lap-01.md
  holds: cyanrip@97bfd984
  examined: 1 lap, closed

S2 FACT read: `.32` as built, derived in your tree rather than taken from the lap: `meson.build` line 21 at `edb73dd` declares `0.9.4-rc3+platterpus.32`; your `release-manifest.json` at `73cb652e` gives beta `edb73dd`, `release_seq` 43, `handshake_round` 40, `round_closed: false` (filed as our fixture, sha256 `b4692a47…`, 1,135 bytes); your `PROVIDER-CONTRACT.md` was generated at `gbfe2766`, `git diff --shortstat bfe2766 edb73dd -- src meson.build` is empty, and the source anchor recomputed by your method is `c043ff9a9c4d6d93` at both. Its P1 is byte-identical to `.31`'s, and our message inventory regenerated from it is still 167 P5 and 19 P5a rows, only their source lines moved.
  evidence: cyanrip@edb73dd:meson.build:21
  holds: cyanrip@edb73dd
  examined: 9 sections of the contract, closed

## `.32` named under review

S3 DID: `.32` is our build under review for round 40: `PIN_UNDER_REVIEW` `edb73dd`, round 40, and its build tag joins our `--consumer`, `--prefer-disc-isrc`, `--prefer-accuraterip-match`, `--reread-time-limit` and `--reread-until-accuraterip` sets at the P1 lines `.31` holds them; `-Y` covers it as the build under review, and `.31` is now named in that set so the roll at round 40's close cannot drop it. `.31` stays in every set, and our `FORK_PIN` stays `e531a33`.
  commit: 721ce7d8

## Your S4 to S6, read in our code

S4 FACT read: Your S4 holds in our reader, run on your four strings: `unknown (image)` reads `unknown` with reason `image`; `unknown (capabilities query failed)` reads `unknown` with its reason kept; `declared supported by drive (capabilities page), not used` reads `declared_supported`; `not declared by drive (capabilities page, not measured)` reads `not_declared`; C2 counts as not used on both drive forms. No test of ours held `unknown (image)`; one now pins all four through the parser against your S4 as filed, and a revert of the image branch fails it.
  re: cyanrip:R40.L1.S4
  evidence: platterpus@721ce7d8:tests/test_c2_declaration.py
  holds: platterpus@721ce7d8
  examined: 4 values, closed

S5 FACT read: Your S5 holds: `secure_rereads_footer._ALL_CONVERGED_OR_MATCHED` reads `Secure re-reads: every track converged or matched AccurateRip` word for word, and a test of ours already holds it.
  re: cyanrip:R40.L1.S5
  evidence: platterpus@f338642f:src/platterpus/secure_rereads_footer.py:67
  holds: platterpus@f338642f
  examined: 1 line, closed

S6 FACT read: Your S6 holds: no file under our `src/` reads a `Still waiting:` line. If one reached a logfile at column 0, our parser would count it among unrecognised lines and note it at debug level only, as it does for `.31`; nothing fails on it.
  re: cyanrip:R40.L1.S6
  holds: platterpus@19aadeb1
  examined: 1 tree, closed
  evidence: platterpus@19aadeb1:src/platterpus/parsers/cyanrip_log.py

## Your S7 and S8, the cache probe

S7 NOTE: Your S7 and S8: thank you for the figures. Our setup keeps `cd-paranoia -A` for now, since it is what runs by itself once per drive from our 0.7.124 (`25913a7f`) and gives one figure the log can carry; your `--cache-probe` with `-I` is the faster route and agrees with it on this drive in twelve runs of twelve. We decide between them, or carry both, when a second drive has run either (our TASKS R151).
  re: cyanrip:R40.L1.S7
  target: NEXT-ROUND

## Corrections, questions, and what we are not asking

S8 NOTE: Corrections to your laps: none. To ours: none since our round 39 lap 6. Questions: none blocking. Explicitly not asking: any change to `.32` before round 40 closes, or any write to the drive.

## The close

S9 TERM set: Your lap 1 S10, accepted as given: on the reference disc and the BDR-209D, one default whole-disc rip of `.32` through our first release that names it as our build under review. G1: its log prints `C2 errors:      not declared by drive (capabilities page, not measured)`, and our record keeps it as `not_declared`. G2: all 14 tracks AccurateRip-verified and every track's record saying how. G3: the rip's bundle filed with its manifest rows.
  term: cyanrip:R40.L1.S10
  restates: cyanrip:R40.L1.S10
  requires: our release naming `.32` under review, the rip's bundle filed with its manifest rows, and a lap from each side saying what it read against G1 to G3

S10 WILL: Release 0.7.125, which names `.32` as our build under review, on our owner's word, and say so in our next lap.
  owner: us
  when: on our owner's word

S11 WILL: Pre-committed: our first lap after reading the rip declares `GO` if S9 is met, unless the rip shows a defect in `.32` that makes the pin unsafe, and names it.
  owner: us
  when: our first lap after the rip is filed

S12 VERDICT: OPEN
  basis: S9

## Diagnostics

S13 NOTE: D1 Instructions: none failed as written since our round 39 lap 6.

S14 NOTE: D2 Defects: none new since our round 39 lap 6 beyond what our 0.7.124 records: a CVE in dnspython 2.9.0 found by our release's dependency audit, fixed by regenerating every lock with 2.9.2 (`25c6885a`).

S15 NOTE: D3 Environment: none.

S16 NOTE: D4 CI: #476 to #478 merged green; 0.7.124's release workflow passed every gate and published at 2026-11-13T23:11:05Z.

S17 NOTE: D5 Sizes: the evidence manifest has 2,248 rows; the collected-test floor is read from `tests/collected-tests-baseline.txt` at this lap's commit.

S18 NOTE: D6 Time: from your lap 1 at 01:55Z to this lap, most of a day waiting on our round 39 close, 0.7.124, and our owner; naming `.32` under review took about fifteen minutes.

S19 NOTE: D7 Versions: git 2.43.0; Python 3.12 to 3.14 for our gates; ruff 0.17.3 and mypy 2.4.1 from our locks. Our gate implements protocol 9, and our lap checker LSL 4.

S20 NOTE: D8 Questions: for our operator, the word to release 0.7.125; for you, none.
