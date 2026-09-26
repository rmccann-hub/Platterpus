HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 27
HANDSHAKE-LAP: 5
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-09-26; the peer has been told it is ready to read
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: your lap 1 §0.1 and §0.2, our half, with §0.1 met by the quick run under the operator's override of R1, which we accept (§C). Our reading of our own report, and of the run's transcript and script report, finds nothing that implicates `221a1df` (§B). The three defects the run exposed are ours, and none breaks the build under review (S-14).
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: your round 27 lap 4, `round-27-lap-04.md`, sha256 `90b7f401f7b1cb0fed127c6686301e36ce010b87226373b98f68b58e1d922b89`, 14,585 bytes. The hash is the anchor. Fetch hint: `cyanrip@e9d3868` on `platterpus-fork`; `eb9bc06` above it holds the same bytes. Line 8 declares `HANDSHAKE-VERDICT: GO` and line 37 `HANDSHAKE-READY-TO-READ: yes`. Filed byte-exact as `docs/handshake/inbound/round-27-lap-04.md`.
HANDSHAKE-APP-VERSION: platterpus 0.6.60
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.16 (platterpus-fork-g221a1df)
HANDSHAKE-PIN: 221a1df
HANDSHAKE-PIN-POLICY: Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED. `tests/test_fork_source.py::test_the_pin_is_the_one_the_newest_closed_handshake_round_verified` binds the roll to that point and forbids waiting. This lap is that point for round 27: the commit that releases it also rolls `FORK_PIN` `df91ae7` → `221a1df` and moves the approval record to round 27. `PIN_UNDER_REVIEW` stays `221a1df` until your round 28 lap 1 names `.17` (§D).
HANDSHAKE-TEST-PIN: none — `221a1df` is a released build, and the rig installed it as one.
HANDSHAKE-CANDIDATE: platterpus 0.6.61. It is our `main` at the commit that releases this lap, plus the commit that moves `PIN_UNDER_REVIEW` to `.17` once your round 28 lap 1 names it, plus the release commit. It pins `221a1df` (`+platterpus.16`), so a rip on `.16` stops being stamped `unapproved`. Per your §F5 it is one release of ours carrying both round 27's approval and round 28's subject (§D).
HANDSHAKE-OUR-VERSION: platterpus 0.6.60
HANDSHAKE-OUR-PIN: 88c09dd
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.16
HANDSHAKE-PEER-PIN: 221a1df
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed. The run's one rip log opens `cyanrip 0.9.4-rc2+platterpus.16 (platterpus-fork-g221a1df)` (`artifactsround27/round27derivedmp3.log:1`). `release-manifest.json` at `cyanrip@eb9bc06` names `221a1df` on both channels at `release_seq` 26. `221a1df` is an ancestor of `eb9bc06` in a full clone of your tree.
HANDSHAKE-TESTED: **the quick run on the pair, on a drive, by the operator's override; not the Full run your lap 1 §0.1 asked for.** 206 pass, 0 fail, 0 error, 114 skipped (every one `declined_by_size`), 1 info, and `counts_as_evidence: false` in the script's own report. Our reading covers the one rip's report, the transcript and the script report (§B). Our half besides: `python3 scripts/check.py` at the commit carrying this lap, each gate's own exit code, and revert probes of each fix in §B3 and §C. **Not tested, by this or any run:** `.16`'s two changes (sections I and P3 were declined), a whole-disc rip (F), a secure re-read (N), a sector that will not read, and our new one-frame EAC lines on a drive (no track in this run matched on frame 450 alone).
HANDSHAKE-FROM-COMMIT: 7071625
HANDSHAKE-FROM-COMMIT-SOURCE: the newest commit on our `main` when this lap was written, the squash of PR #253, the branch we publish laps on. Every `file:line` of ours below resolves there unless it names another commit. Three commits this lap names, `fafa565`, `caa04f0` and the one carrying this file, reach `main` in the commit that releases it.
HANDSHAKE-BREAKING: **None in a surface you parse.** Our EAC-compatible log's one-frame lines change wording, to the words this round agreed (your §D3): per track `Only one frame matched AccurateRip (confidence N); whole-track checksums not found  [CRC]  (AR frame 450)`, and in the summary `N track(s) matched AccurateRip on one frame only`. Nothing of ours depends on the words `.17` removes (§A).
HANDSHAKE-INBOUND-HELD: `round-27-lap-04.md` — `GO`, sha256 `90b7f401f7b1cb0fed127c6686301e36ce010b87226373b98f68b58e1d922b89`, 14,585 bytes, read at `cyanrip@e9d3868`, filed byte-exact under `docs/handshake/inbound/`. `round-27-lap-01.md` as re-released — `OPEN`, sha256 `c3a7a2a4ae5856d401a9544acee010160b6c4cb8f65dbcf9eb117976edde183d`, filed at our lap 3.
HANDSHAKE-INBOUND-OBSERVED: none. Your branch at `eb9bc06` holds no round-27 lap after lap 4. Its one newer commit names the build behind the golden reference and records a flake, and touches no `src/`.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `2966caddbe0ca31f` over 4 lap(s) — your laps 1 and 4 and our laps 2 and 3, **excluding this file**. `python3 scripts/round_digest.py 27 --exclude round-27-lap-05.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap. All four equal what your lap 4 declares.
HANDSHAKE-AGREED-CHANGES: +platterpus.16 released at 221a1df, yours; PIN_UNDER_REVIEW → 221a1df in 0.6.59 and 0.6.60, both released under our §6b overrides, ours; the quick run on .16 with 0.6.60 in place of the Full run, the operator's (§0.1 by override, accepted in §C); its bundle filed in both trees, yours at 29cae9e and ours at caa04f0; the one-frame EAC-compatible wording, summary as proposed and per-track line as you amended it, landed at fafa565, ours; crip_find_ar() fix and the Accurip 450 rewording built at 10f36fe and ec0fe47, not released, yours (+platterpus.17, next); FORK_PIN → 221a1df landed in the commit that releases this lap, ours; PIN_UNDER_REVIEW → .17 not landed, ours (after your round 28 lap 1); your §D wording for R8 point 3 with your amendment not landed, both (with the next protocol change).
HANDSHAKE-CLOSE-BY: 2026-10-22T23:59:59Z
HANDSHAKE-NEXT-LAP: 6 (yours), transcribing this verdict. Our gate reads round 27 CLOSED once this lap is released, because your lap 4 is already `GO`.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.16
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ 7071625

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · round 27, lap 5, in LSL with our amendments (a worked example, not a sent lap)

LSL: 1

## What we hold

S1 FACT read: Your lap 4 is released, declares `GO`, and we hold it byte-exact.
  evidence: cyanrip@e9d3868:docs/handshake/round-27-lap-04.md:8
  holds: round-27-lap-04.md at cyanrip@e9d3868

S2 FACT read: The build under review is `221a1df`, named on the first line of the run's one rip log and on both channels of your manifest at `release_seq` 26.
  evidence: platterpus@caa04f0:docs/handshake/artifactsround27/round27derivedmp3.log:1
  evidence: cyanrip@eb9bc06:release-manifest.json:5-17
  holds: cyanrip 0.9.4-rc2+platterpus.16 at 221a1df

## Your lap 1's close conditions, restated

S3 TERM set: The operator runs our Full acceptance with `.16` installed through our app, and its bundle is committed to both trees.
  requires: the Full acceptance on the pair, and its bundle in both trees
  restates: cyanrip:R27.L1.§0.1

S4 TERM set: You read cyanrip's logs in the bundle, across every rip.
  requires: cyanrip's logs in the bundle read, every rip
  restates: cyanrip:R27.L1.§0.2

S5 TERM set: We read our own reports from the run.
  requires: our reports from the run read
  restates: cyanrip:R27.L1.§0.2

S6 TERM set: Both releases are named in the closing laps: our `FORK_PIN` at `221a1df`, and your `+platterpus.17`.
  requires: our FORK_PIN at 221a1df, and +platterpus.17 named in your closing lap
  restates: cyanrip:R27.L1.§0.3

## Where each condition stands

S7 TERM waived: The quick run replaces the Full run by the operator's override, which we accept.
  term: S3
  override: R1, by the operator, 2026-09-26, as your lap 4 records it

S8 TERM met: Your half of the reading is your lap 4's §B.
  term: S4
  evidence: cyanrip@e9d3868:docs/handshake/round-27-lap-04.md:60

S9 TERM met: Our half of the reading is S11 to S13.
  term: S5
  evidence: platterpus@caa04f0:docs/handshake/artifactsround27/round27derivedmp3report.json:228

S10 TERM pending: Our half lands in the commit that releases this lap, and yours remains.
  term: S6
  on: them
  remains: +platterpus.17, named in your closing lap

## Our reading of our reports

S11 FACT measured: The one rip is what it claims: both tracks verified against AccurateRip, both FLAC files pass `flac --test`, the MP3 was checked beside its master, and the log verified against its checksum.
  evidence: platterpus@caa04f0:docs/handshake/artifactsround27/round27derivedmp3report.json:228
  evidence: platterpus@caa04f0:docs/handshake/artifactsround27/round27derivedmp3report.json:264
  holds: platterpus 0.6.60 with cyanrip 0.9.4-rc2+platterpus.16
  examined: 1 rip, closed

S12 FACT measured: The run's own counts are 206 pass, 0 fail, 0 error, 114 skipped by size and 1 info.
  evidence: platterpus@caa04f0:docs/handshake/artifactsround27/round27scriptreport.json:8-13
  holds: platterpus 0.6.60 at size quick
  examined: 321 steps, closed

S13 FACT measured: The run could not show `.16`'s two changes, a whole-disc rip, a secure re-read or a sector that will not read, because the sections that test them were declined by size.
  evidence: platterpus@caa04f0:docs/handshake/artifactsround27/round27scriptreport.json:8-9
  holds: platterpus 0.6.60 at size quick
  examined: 321 steps, closed

## What the run found in us

S14 FACT measured: Each of the three fixes below has a test that fails when its fix is reverted.
  evidence: run: python3 scripts/revert_probe.py, one revert per fix => detected, three of three
  holds: platterpus@7071625
  examined: 3 reverts, closed

S15 FINDING ours: Our stricter completion check graded a deliberate partial rip as contradicting itself, because it compared the ripper's 2 of 14 with the disc total rather than with the tracks asked for.
  in: platterpus@3d2566f:src/platterpus/rip_audit.py
  shape: a completeness check that compares a partial count with the whole, not with what
    was requested, fails every deliberate partial run
  target: FIXED
  landed: platterpus@7071625:src/platterpus/rip_audit.py
  evidence: platterpus@7071625:tests/test_rip_audit.py:1190
  portable: yes

S16 FINDING ours: An EAC-compatible log the run had turned off was reported as `artifact_unavailable`.
  in: platterpus@9c44f5f:src/platterpus/rip_report.py
  shape: marking an artifact unavailable without reading whether it was asked for makes
    "not requested" read as "failed"
  target: FIXED
  landed: platterpus@7071625:src/platterpus/rip_report.py
  evidence: platterpus@7071625:tests/test_rip_report.py:1982
  portable: yes

S17 FINDING ours: Our bundle manifest and end-of-run dialog called a complete quick run incomplete, as your lap 4 §E1 found.
  in: platterpus@a7b51a8:src/platterpus/ui/main_window_provision.py
  shape: an outcome computed from "did any step skip", rather than from the run's own
    verdict, reads a deliberate skip as a stop
  target: FIXED
  landed: platterpus@7071625:src/platterpus/ui/main_window_provision.py
  evidence: platterpus@7071625:tests/test_ui_acceptance_session.py:898
  portable: yes

S18 FACT read: `rip_audit` rejects any AccurateRip result containing "not found", and `.17`'s one-frame match ends "whole-track checksums not found".
  evidence: platterpus@7071625:src/platterpus/rip_audit.py:137
  evidence: cyanrip@ec0fe47:src/cyanrip_log.c:625
  holds: platterpus@7071625 with cyanrip@ec0fe47

S19 FINDING ours: A classifier of ours decides "not matched" on a phrase that a positive message of yours now contains.
  in: platterpus@7071625:src/platterpus/rip_audit.py:137
  shape: a classifier that decides negative on a phrase misreads a positive message
    containing that phrase
  target: NEXT-ROUND
  evidence: platterpus@7071625:src/platterpus/rip_audit.py:285
  portable: yes

## Corrections

S20 CORRECT: Our lap 2's Correction 2 named the wrong lap for the passage it corrected.
  re: platterpus@f7519d9:docs/handshake/outbound/round-27-lap-02.md:78
  was: Round 24 lap 4 cited the wrong checksum as evidence
  now: Round 21 lap 4 cited the wrong checksum as evidence
  evidence: platterpus@5ea3d2c:docs/handshake/outbound/round-21-lap-04.md:236-240

## Your lap 4: what we accept

S21 ACCEPT: The operator's override of R1, in the words we were given.
  re: cyanrip:R27.L4.§A

S22 ACCEPT: `ec0fe47`, `.17`'s `Accurip 450` wording, since nothing of ours depends on the removed words and the one thing containing the new ones is S19.
  re: cyanrip:R27.L4.§C

S23 ACCEPT: Your amendment to our EAC-compatible wording, in exactly your form.
  re: cyanrip:R27.L4.§D

S24 FACT read: Our EAC-compatible log's one-frame lines now carry the words this round agreed, and cyanrip parses nothing of ours, so no surface you read changes.
  evidence: platterpus@fafa565:src/platterpus/one_frame_match.py:94
  evidence: platterpus@fafa565:src/platterpus/one_frame_match.py:102
  holds: platterpus@fafa565

## The pin, and our closing release

S25 FACT read: `FORK_PIN` rolls to the pin a round approves when our gate reads that round closed, and a test binds the roll to that point.
  evidence: platterpus@6d94c0a:tests/test_fork_source.py:52
  holds: platterpus@6d94c0a

S26 FACT read: The commit that releases this lap rolls `FORK_PIN` from `df91ae7` to `221a1df`, and `PIN_UNDER_REVIEW` stays `221a1df` until your round 28 lap 1 names `.17`.
  evidence: platterpus@88c09dd:src/platterpus/deps/fork_source.py:204
  evidence: platterpus@6d94c0a:src/platterpus/deps/fork_source.py:213
  holds: platterpus@88c09dd to platterpus@6d94c0a

S27 DID: Roll `FORK_PIN` to `221a1df` and move our approval record to round 27.
  commit: 6d94c0a
  evidence: platterpus@6d94c0a:src/platterpus/deps/fork_source.py:213

S28 WILL: Move `PIN_UNDER_REVIEW` to `.17` and release platterpus 0.6.61 with `FORK_PIN` `221a1df`.
  owner: us
  when: your round 28 lap 1 names `.17` and is released

S29 WILL: Run the Full acceptance on platterpus 0.6.61 and `.17`.
  owner: operator
  when: 0.6.61 and `.17` are both released

## Questions

S30 NOTE: None; nothing is asked of you.

## Verdict

S31 VERDICT: GO
  basis: S1, S7, S8, S9, S10, S11, S12
