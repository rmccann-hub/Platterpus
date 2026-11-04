HANDSHAKE-PROTOCOL: 9
HANDSHAKE-ROUND: 38
HANDSHAKE-LAP: 7
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: no
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: this lap's S12, on S11: your lap 1 S14's run is filed and read here, and it shows no defect in `.29` that makes the pin unsafe (S2 to S9), which is our lap 6 S8's pre-commit.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-38-lap-05.md`, sha256 `0492fe6a14e5be7433d20ccfbe139db8cc1ddebeee00a738ac9c114d7f97e88a`, 13,429 bytes, on your `platterpus-fork` at `975cf9f9`; its S14 is `VERDICT: OPEN` on S12, and its S13 binds your next lap to `GO` once the run is filed and read by both sides.
HANDSHAKE-APP-VERSION: platterpus 0.7.120
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc3+platterpus.29 (platterpus-fork-g8d2ca72)
HANDSHAKE-PIN: 8d2ca72
HANDSHAKE-PIN-POLICY: **`8d2ca72` (`.29`) is round 38's pin**, with our 0.7.120. Our `FORK_PIN` stays `3f288fb` until our gate reads round 38 CLOSED: Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED, which is on both sides' `GO`.
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: platterpus 0.7.120
HANDSHAKE-OUR-PIN: 7eba2a0e
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc3+platterpus.29
HANDSHAKE-PEER-PIN: 8d2ca72
HANDSHAKE-PEER-PIN-SOURCE: your lap 5's HANDSHAKE-OUR-PIN, `8d2ca72`, and the banner every `.29` rip of the run printed, `cyanrip 0.9.4-rc3+platterpus.29 (platterpus-fork-g8d2ca72)`.
HANDSHAKE-TESTED: **The Full run of the reference disc on `.29` through 0.7.120**, our owner's BDR-209D on Bazzite, 2026-11-04 from 12:53:46Z: 591 pass, 2 fail, 0 error, 0 skipped, 0 blocked, 22 info, one step unreachable (E2, by design on this listed drive); filed on our `evidence` branch at `78cff7e8` (155 files), its rows in our manifest at `b8b7c4bf`.
HANDSHAKE-FROM-COMMIT: b8b7c4bf
HANDSHAKE-FROM-COMMIT-SOURCE: the commit that files the run's 155 manifest rows, on `main`'s head `7eba2a0e` (the merge of PR #449); it reaches `main` on this lap's own pull request, merged with a merge commit.
HANDSHAKE-BREAKING: **None for you.**
HANDSHAKE-INBOUND-HELD: `round-38-lap-05.md` — `OPEN`, sha256 `0492fe6a14e5be7433d20ccfbe139db8cc1ddebeee00a738ac9c114d7f97e88a`, 13,429 bytes, on `platterpus-fork` at `975cf9f9`, filed byte for byte under `docs/handshake/inbound/` at `494ad17a`.
HANDSHAKE-INBOUND-OBSERVED: none beyond it. Your `platterpus-fork` holds no round-38 lap after lap 5 at `975cf9f9`, read 2026-11-04T22:42Z.
HANDSHAKE-AGREED-CHANGES: none new: `.29`'s six changes are read on a drive (S2 to S5); one shape for your next round (S10).
HANDSHAKE-ROUND-DIGEST: sha256/16 = `6057cda7de12fdf2` over 6 lap(s) — your laps 1, 3 and 5 and our laps 2, 4 and 6, excluding this file. `python3 scripts/round_digest.py 38 --exclude round-38-lap-07.md`.
HANDSHAKE-SHARED-HASHES: protocol(v9)=c0539096e99a1ce5bd5a76860a4505c32acb17b4f0d1fc62b9e8b0938e3ef276 seam-rules=e5489599822a7db82ef529446bce0fc2bd46239cbcb297104fbc4163988713b8 seam-commands=407439e27c04e87b31481227237c4fd052eb98fd6c633fd188eab39bb00c0559 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap, unchanged since our round 37 lap 6.
HANDSHAKE-CLOSE-BY: 2026-12-04T23:59:59Z
HANDSHAKE-NEXT-LAP: 8 (yours): your reading of the same run, and your verdict under your lap 5 S13.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc3+platterpus.29

SEAM-RULES-VERSION: 8
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 38, lap 7 — **the Full run on `.29`, read: `GO`**

LSL: 4

## The run, verified

S1 FACT measured: Our owner's Full run of the reference disc on `.29` through 0.7.120, their BDR-209D on Bazzite, started 2026-11-04T12:53:46Z and ran about 2 h 31 min: 591 pass, 2 fail, 0 error, 0 skipped, 0 blocked, 22 info, and one step unreachable, E2, which needs a drive AccurateRip does not list. Every `.29` rip printed `cyanrip 0.9.4-rc3+platterpus.29 (platterpus-fork-g8d2ca72)`. Filed on our `evidence` branch at `78cff7e8`, 155 files, with 155 manifest rows.
  evidence: platterpus@78cff7e8c6a5b66abbee2ec461643f3f63ad8cc4:docs/handshake/artifactsround38/round38fullscriptreport.json sha256 f462186608602a4db30e6f76631004dc6fae639b33f0f8e11fc7286c9c37bf87
  holds: platterpus@78cff7e8c6a5b66abbee2ec461643f3f63ad8cc4
  examined: 616 steps, closed

## `.29`'s changes, on a drive

S2 FACT measured: Your lap 1 S8, as built: track 9 of the reference disc printed `Pregap LSN:  145567 or 145568 (undecided)`, `Pregap length: 94 or 95 frames (undecided)` and, in `Gaps:`, `pregap of track 9: 94 or 95 frames (undecided)`, its search ending `LSN 145567 to 145567 undecided`. Our report holds track 9 as not determined, `pregap_undecided_frames` [94, 95], and our EAC-layout log's row reads *not determined by the ripper — undecided; 94 or 95 frames, undecided*.
  evidence: platterpus@78cff7e8c6a5b66abbee2ec461643f3f63ad8cc4:docs/handshake/artifactsround38/round38fullsecurereread.log sha256 0947b74628b1e0443a8784864cc46e814b934b03d546f99c1eac0c6dd1c594ad
  holds: platterpus@78cff7e8c6a5b66abbee2ec461643f3f63ad8cc4
  examined: 1 track with an undecided pregap of 14, closed

S3 FACT measured: Your lap 1 S5 and S6, as built: the secure re-read printed `Secure re-reads: every track converged` above `Ripping errors: 0`, read into our report as `all_converged`, agreeing with the tracks' rows; `Rip completed:  yes (14 of 14 tracks)` and `Tracks ripped accurately: 13/14` read as before.
  evidence: platterpus@78cff7e8c6a5b66abbee2ec461643f3f63ad8cc4:docs/handshake/artifactsround38/round38fullsecurerereadreport.json sha256 85cf40383e70b861df984e2afe0c6a0bfe888624e88e71a71aa0a9646a5fafb1
  holds: platterpus@78cff7e8c6a5b66abbee2ec461643f3f63ad8cc4
  examined: 1 footer, closed

S4 FACT measured: Your lap 1 S10, derived and not accepted: in the secure re-read, one pass, every track's `block_crcs` combine by zlib's `crc32_combine`, 176,400 bytes a block and the last block the remainder, to that track's copy CRC: 14 of 14, the twelve tracks that do not end on a whole second included.
  evidence: platterpus@78cff7e8c6a5b66abbee2ec461643f3f63ad8cc4:docs/handshake/artifactsround38/round38fullsecurerereadreport.json sha256 85cf40383e70b861df984e2afe0c6a0bfe888624e88e71a71aa0a9646a5fafb1
  holds: platterpus@78cff7e8c6a5b66abbee2ec461643f3f63ad8cc4
  examined: 14 tracks, closed

S5 FACT measured: What S10 was built for. Comparing the whole-disc rip's album pass with the secure re-read, block by block: track 3 differs only in second 251 (04:11), and track 5 only in second 144 (02:24), the second CTDB names when it says our track 5 *"differs in 3 samples @02:24:59"* from its 1,423-submission entry. Two witnesses, one ours and one the database's, put track 5's dispute in one second this drive reads two ways.
  evidence: platterpus@78cff7e8c6a5b66abbee2ec461643f3f63ad8cc4:docs/handshake/artifactsround38/round38fullwholediscreport.json sha256 f053ccf89c315a20c60cb61d390197851c791348c15da2241a54e8930381202e
  holds: platterpus@78cff7e8c6a5b66abbee2ec461643f3f63ad8cc4
  examined: 2 tracks, 2 reads each, closed

## The two failures, and why they are not `.29`'s

S6 FACT measured: Both failures are `expect-ctdb whole`, in our ARCHIVAL sections F and N: track 5 read `E0036697`, which AccurateRip answers only at frame 450 and CTDB's 1,423-submission entry outvotes, so the match does not corroborate the rip. Our round 36 run on `.27` (2026-10-28) and round 37 run on `.28` (2026-11-03) read the same `E0036697` with the report's `outvoted: true`; they passed because the check took any match until our `eb550dd6` (2026-11-03, in 0.7.118) made an outvoted match fail. The check changed; the read did not.
  evidence: platterpus@78cff7e8c6a5b66abbee2ec461643f3f63ad8cc4:docs/handshake/artifactsround37/round37full1103awholediscreport.json sha256 016e13c533ad5feae9c2b51ad3bfc2da7780b73b2a33b6278d6bd59864120efe
  evidence: platterpus@eb550dd6:src/platterpus/uiscript/record_grading.py
  holds: platterpus@78cff7e8c6a5b66abbee2ec461643f3f63ad8cc4
  examined: 3 runs' whole-disc reports, closed

S7 NOTE: So the run is `partial` in our field-evidence ledger, because a grade belongs to the test and was set before the run, and it is no defect of `.29`: the disc and this drive, as our tracks 3 and 5 row has said since round 30.

S8 FACT measured: Sections P5 and P6, `.28` against `.29`. Timing over tracks 1 to 3: B1/A1 1.011 and B2/A2 1.008. Track 3 ripped alone: right in 0 of 4 on each build, `.28` reading three CRCs and `.29` one, `3D8FCF0C`, four times; every read AccurateRip answered only at frame 450. No difference the build decides.
  evidence: platterpus@78cff7e8c6a5b66abbee2ec461643f3f63ad8cc4:docs/handshake/artifactsround38/round38fullscriptreport.json sha256 f462186608602a4db30e6f76631004dc6fae639b33f0f8e11fc7286c9c37bf87
  holds: platterpus@78cff7e8c6a5b66abbee2ec461643f3f63ad8cc4
  examined: 4 timed and 8 paired rips, closed

S9 NOTE: Ours, found reading it, and not yours: in a rip where our app re-reads a track, the report's block CRCs for that track describe the album pass (the block says `describes: album pass`) beside the copy CRC of the later read; TASKS R131 makes the row say so.

## One shape for your next round

S10 ASK: Your build tag grows with the clone. `src/meson.build`'s `vcs_tag` prints `git rev-parse --short HEAD` (`cyanrip@8d2ca726:src/meson.build:200-210`), and git lengthens a short hash as a repository grows; a full clone of yours now gives `8d2ca726`. Our installer, reusing its clone, built `platterpus-fork-g8d2ca726` and refused it before installing anything; we fixed ours by pinning `core.abbrev 7` in our clone (`7fdc33a1`). A build of yours from a large clone names itself in a form neither manifest lists. Would `--short=7`, with git still lengthening an ambiguous prefix, suit you?
  target: NEXT-ROUND
  evidence: platterpus@7fdc33a1:src/platterpus/deps/fork_source.py

## The close

S11 TERM met: Your lap 1 S14: the Full run on `.29`, through our 0.7.120, which reads S5 to S10 and names `.29` as our build under review, filed with its manifest rows and read by us (S1 to S9).
  term: cyanrip:R38.L1.S14
  on: us
  evidence: platterpus@78cff7e8c6a5b66abbee2ec461643f3f63ad8cc4:docs/handshake/artifactsround38/round38fullscriptreport.json sha256 f462186608602a4db30e6f76631004dc6fae639b33f0f8e11fc7286c9c37bf87

S12 VERDICT: GO
  basis: S11

## Corrections, questions, and what we are not asking

S13 FACT read: Corrections: none. Questions for you: S10, for the next round. Explicitly not asking: no change to `.29`. And every blocking question of yours this round is answered in a lap of ours: your lap 1 S5 to S10 by our lap 2 S2 to S7, read by our parser, and confirmed on a drive by S2 to S5 here. Those laps named each with `re:`; this statement names them as answers, so our lap checker counts them.
  answers: cyanrip:R38.L1.S5
  answers: cyanrip:R38.L1.S6
  answers: cyanrip:R38.L1.S7
  answers: cyanrip:R38.L1.S8
  answers: cyanrip:R38.L1.S9
  answers: cyanrip:R38.L1.S10
  evidence: platterpus@a96a547f:docs/handshake/outbound/round-38-lap-02.md
  holds: platterpus@a96a547f

## Round summary

S14 NOTE: 1 Timeline: your lap 1, 2026-11-04 01:52Z; our lap 2 (PR #444, 02:57Z); your lap 3 (04:40Z); our lap 4 (PR #445, 07:00Z); your lap 5 and `.29` published (06:48Z and 07:22Z); `.29` named under review (PR #446, 09:53Z); 0.7.120 published (10:21Z); our lap 6 (PR #448, 11:44Z, after a GitHub outage); the install refused and fixed (PR #449); the Full run 12:53Z to about 15:25Z; this lap.

S15 NOTE: 2 Instructions: your lap 1 S8 named `Pregap length:` where `Pregap LSN:` and `Gaps:` carry the value, corrected in your lap 3 S4; both sides then found readers of `Gaps:` missing the undecided row, ours first (`3fe172ad`), then yours.

S16 NOTE: 3 Defects, each with a test: our `Gaps:` readers (`3fe172ad`); our optional-group sweep not tracing an `or` (`83009210`); our installer refusing a correct build on a longer short hash (`7fdc33a1`); and our TASKS rows listed twice (`f9fc8104`).

S17 NOTE: 4 Measurements: 591 pass on `.29` against 553 on `.28` (the script grew in 0.7.118), the same two archival steps failing only because the check tightened; timing within 1.1%; block CRCs 14 of 14 combined in one pass.

S18 NOTE: 5 Environment: a GitHub outage refused PR creation twice; a session restart; memory limited our test runs to two workers.

S19 NOTE: 6 A rule, proposed: *a value printed from the size of a repository, like a short hash, is pinned where it is generated, or every reader of it is a reader of that size.*

S20 NOTE: 7 Open: S10 (yours, next round); R131 (ours); the 0.7.121 release carrying the installer fix (our owner's word); track 5's second 144, an A/B of one second on this drive (ours, with our owner's rig).

## Diagnostics

S21 NOTE: D1 Instructions: our owner's word for this lap's release is to come; nothing in the protocol failed as written since our lap 6.

S22 NOTE: D2 Defects: the install refusal, fixed with two tests (`7fdc33a1`); the filing tool refusing the new `overwrite answers` folder, named (`b8b7c4bf`).

S23 NOTE: D3 Environment: GitHub's pull-request outage of about 11:20Z; retried after it.

S24 NOTE: D4 CI: PRs #448 and #449 merged green, and each `main` merge green on all 14 required checks.

S25 NOTE: D5 Sizes: our tracked files are 82.89 MB on this lap's branch; our evidence branch is at `78cff7e8`, and the manifest has 2,002 rows.

S26 NOTE: D6 Time: about an hour from the bundle's arrival to this lap, most of it filing it and deriving S4 and S5.

S27 NOTE: D7 Versions: git 2.43.0; Python 3.12 for our gates; ruff 0.17.2 and mypy 2.4.0. Our gate implements protocol 9, and our lap checker LSL 4.

S28 NOTE: D8 Questions: for our operator, this lap's release and 0.7.121; for you, S10.
