HANDSHAKE-PROTOCOL: 6
HANDSHAKE-LANGUAGE: 1
HANDSHAKE-ROUND: 27
HANDSHAKE-LAP: 5
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-26
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: #T5, #T6, #T7, #T8
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: lap 4 round-27-lap-04.md sha256:90b7f401f7b1cb0fed127c6686301e36ce010b87226373b98f68b58e1d922b89 14585 bytes
HANDSHAKE-APP-VERSION: platterpus 0.6.60
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.16 (platterpus-fork-g221a1df)
HANDSHAKE-PIN: 221a1df
HANDSHAKE-PIN-POLICY: #C9
HANDSHAKE-TEST-PIN: none
HANDSHAKE-CANDIDATE: platterpus 0.6.61
HANDSHAKE-CANDIDATE-SOURCE: #P1
HANDSHAKE-OUR-VERSION: platterpus 0.6.60
HANDSHAKE-OUR-PIN: 88c09dd
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.16
HANDSHAKE-PEER-PIN: 221a1df
HANDSHAKE-PEER-PIN-SOURCE: #C2
HANDSHAKE-TESTED: #C3, #C4, #C5
HANDSHAKE-FROM-COMMIT: 7071625
HANDSHAKE-BREAKING: none
HANDSHAKE-INBOUND-HELD: round-27-lap-01.md (OPEN) sha256:c3a7a2a4ae5856d401a9544acee010160b6c4cb8f65dbcf9eb117976edde183d 11382 bytes, round-27-lap-04.md (GO) sha256:90b7f401f7b1cb0fed127c6686301e36ce010b87226373b98f68b58e1d922b89 14585 bytes
HANDSHAKE-INBOUND-OBSERVED: none
HANDSHAKE-ROUND-DIGEST: sha256/16 = 2966caddbe0ca31f over 4 lap(s)
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-AGREED-CHANGES: #C10, #C11, #C12, #C13, #C14, #C15, #P1, #P2
HANDSHAKE-CLOSE-BY: 2026-10-22T23:59:59Z
HANDSHAKE-NEXT-LAP: 6 cyanrip-fork
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.16
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ 7071625
SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · round 27, lap 5, in lap language 1 (a worked example, not a sent lap)

## What we hold

#### C1 CLAIM cited
Your lap 4 is released, declares `GO`, and we hold it byte-exact. Its §B is your
reading of cyanrip's logs in the quick run.

- holds-for: `round-27-lap-04.md` as released
- anchor: sha256:90b7f401f7b1cb0fed127c6686301e36ce010b87226373b98f68b58e1d922b89 14585 bytes at cyanrip@e9d3868:docs/handshake/round-27-lap-04.md

#### C2 CLAIM derived
The build under review is `221a1df`. The run's one rip log names it on its first
line, and your release manifest names it on both channels at `release_seq` 26.

- holds-for: the quick run of 2026-09-26, and `release-manifest.json` at `eb9bc06`
- from: platterpus@6d94c0a:docs/handshake/artifactsround27/round27derivedmp3.log:1
- from: cyanrip@eb9bc06:release-manifest.json:5-17

## The close conditions, restated from your lap 1

#### T1 TERM set
The operator runs our Full acceptance on the rig, with `.16` installed through
our app, from a release of ours whose `PIN_UNDER_REVIEW` is `221a1df`. The
bundle it produces is committed byte-identical to both repositories.

- requires: the Full acceptance on the pair, and its bundle in both trees
- restates: §0.1 of sha256:c3a7a2a4ae5856d401a9544acee010160b6c4cb8f65dbcf9eb117976edde183d 11382 bytes at cyanrip@3a5cfc0:docs/handshake/round-27-lap-01.md

#### T2 TERM set
Your half of each side's reading: you read cyanrip's logs in the bundle, across
every rip.

- requires: cyanrip's logs in the bundle read, every rip
- restates: §0.2 of sha256:c3a7a2a4ae5856d401a9544acee010160b6c4cb8f65dbcf9eb117976edde183d 11382 bytes at cyanrip@3a5cfc0:docs/handshake/round-27-lap-01.md

#### T3 TERM set
Our half of each side's reading: we read our reports.

- requires: our reports from the run read
- restates: §0.2 of sha256:c3a7a2a4ae5856d401a9544acee010160b6c4cb8f65dbcf9eb117976edde183d 11382 bytes at cyanrip@3a5cfc0:docs/handshake/round-27-lap-01.md

#### T4 TERM set
Both releases, named in the closing laps. Ours rolls `FORK_PIN` to `221a1df`.
Yours is `+platterpus.17`.

- requires: our `FORK_PIN` at `221a1df`, and `+platterpus.17` named in your closing lap
- restates: §0.3 of sha256:c3a7a2a4ae5856d401a9544acee010160b6c4cb8f65dbcf9eb117976edde183d 11382 bytes at cyanrip@3a5cfc0:docs/handshake/round-27-lap-01.md

## Where each condition stands

#### T5 TERM waived
The quick run of 2026-09-26 replaces the Full run, by the operator's override,
which we accept. The Full run moves to round 28, on both projects' next releases.

- term: #T1
- override: R1, by operator (rmccann), 2026-09-26, as your lap 4 records it

#### T6 TERM met
Your half of the reading is your lap 4's §B.

- term: #T2
- witness: #C1

#### T7 TERM met
Our half of the reading is below.

- term: #T3
- witness: #C3, #C4, #C5

#### T8 TERM pending
Our half lands in the commit that releases this lap. Yours remains.

- term: #T4
- on: cyanrip-fork
- remains: `+platterpus.17`, named in your closing lap

## Our reading of our reports

#### C3 CLAIM measured
The one rip is what it claims. Section K1 ripped tracks 1 and 2, both verified
against AccurateRip, both FLAC files pass `flac --test`, the MP3 was written and
checked beside its master, and the log verified against its FUN512 checksum.
CTDB answered `not_in_db`, so CTDB comparison did not run.

- holds-for: platterpus 0.6.60 with cyanrip 0.9.4-rc2+platterpus.16, the quick run of 2026-09-26
- method: read the rip report, transcript and script report filed in `docs/handshake/artifactsround27/`
- tool: none; the filed files, read directly
- result: `✓ Bit-perfect: all 2 tracks verified against AccurateRip (confidence 129+)`; `ripper_log_verification: verified`
- examined: 1 rip, closed

#### C4 CLAIM measured
The run's counts are what they say: 206 pass, 0 fail, 0 error, 114 skipped (each
declined by size) and 1 info. The info is our wrapper probe, whose host export
exited in 0.28 s, so the 2026-08-27 hang did not reproduce.

- holds-for: the quick run of 2026-09-26
- method: the acceptance script's own report in the filed bundle
- tool: the acceptance script at size quick, in platterpus 0.6.60
- result: 206 pass, 0 fail, 0 error, 114 skipped, 1 info; `counts_as_evidence: false`
- examined: 321 steps, closed

#### C5 CLAIM measured
What the run could not show: `.16`'s two changes (sections I and P3 were
declined), a whole-disc rip, a secure re-read, a sector that will not read, and
our new one-frame lines in the EAC-compatible log on a drive, since no track
matched on frame 450 alone.

- holds-for: the quick run of 2026-09-26
- method: the declined sections in the script report, and each track's AccurateRip result in the rip report
- tool: the acceptance script at size quick, in platterpus 0.6.60
- result: sections F, I, N and P3 declined by size; both tracks matched v1 and v2 whole-track checksums
- examined: 321 steps, closed

## What the run found in us

#### C6 CLAIM measured
Each fix below has a test that fails when its fix is reverted.

- holds-for: platterpus@7071625
- method: `scripts/revert_probe.py`, one revert per fix
- tool: scripts/revert_probe.py
- result: detected, three of three
- examined: 3 reverts, closed

#### F1 FINDING ours
Our stricter completion check graded a deliberate partial rip as contradicting
itself: it compared the ripper's `2 of 14` with the disc total, not with the
tracks the rip was asked for. It was unreleased, so no shipped version had it.

- in: platterpus@3d2566f:src/platterpus/rip_audit.py
- shape: a completeness check that compares a partial count with the whole, rather than with what was requested, fails every deliberate partial run
- target: fixed
- landed: platterpus@7071625:src/platterpus/rip_audit.py
- witness: #C6
- portable: yes

#### F2 FINDING ours
An EAC-compatible log the run had turned off was reported as
`artifact_unavailable`. The report now reads the rip's own recorded setting.

- in: platterpus@9c44f5f:src/platterpus/rip_report.py
- shape: marking an artifact unavailable without reading whether it was asked for makes "not requested" read as "failed"
- target: fixed
- landed: platterpus@7071625:src/platterpus/rip_report.py
- witness: #C6
- portable: yes

#### F3 FINDING ours
Our bundle's manifest and end-of-run dialog called a complete quick run
incomplete, as your lap 4 §E1 found. Both treated any skip as a stop; they now ask
the script report's own `ok`, which forgives size-declined skips.

- in: platterpus@a7b51a8:src/platterpus/ui/main_window_provision.py
- shape: an outcome computed from "did any step skip", rather than from the run's own verdict, reads a deliberate skip as a stop
- target: fixed
- landed: platterpus@7071625:src/platterpus/ui/main_window_provision.py
- witness: #C6
- portable: yes

#### C7 CLAIM derived
`rip_audit` rejects any AccurateRip result containing the words "not found", and
`.17`'s one-frame match ends *"whole-track checksums not found"*. It is applied
only to the v1 and v2 lines, whose wording is unchanged, so nothing it reports
changes today.

- holds-for: platterpus@7071625 with cyanrip@ec0fe47
- from: platterpus@7071625:src/platterpus/rip_audit.py:137
- from: platterpus@7071625:src/platterpus/rip_audit.py:285
- from: cyanrip@ec0fe47:src/cyanrip_log.c:625

#### F4 FINDING ours
A classifier of ours decides "not matched" on a phrase that a positive message of
yours now contains. We fix it next round by moving it to the confidence rule
every other reader of ours uses. We assert nothing about your code; any reader of
cyanrip's AccurateRip lines could hold the same shape.

- in: platterpus@7071625:src/platterpus/rip_audit.py:137
- shape: a classifier that decides negative on a phrase misreads a positive message containing that phrase
- target: next-round
- witness: #C7
- portable: yes

## Your lap 4: what we accept

#### A1 ANSWER accept
The operator's override of R1: accepted. The words in your override are the ones
we were given.

- answers: §A of sha256:90b7f401f7b1cb0fed127c6686301e36ce010b87226373b98f68b58e1d922b89 14585 bytes at cyanrip@e9d3868:docs/handshake/round-27-lap-04.md

#### A2 ANSWER accept
`ec0fe47`, `.17`'s `Accurip 450` wording: accepted. Nothing of ours depends on the
removed words; the one thing containing the new ones is F4.

- answers: §C of sha256:90b7f401f7b1cb0fed127c6686301e36ce010b87226373b98f68b58e1d922b89 14585 bytes at cyanrip@e9d3868:docs/handshake/round-27-lap-04.md
- re: #F4

#### A3 ANSWER accept
Your amendment to our EAC-compatible wording: accepted, in exactly your form.

- answers: §D3 of sha256:90b7f401f7b1cb0fed127c6686301e36ce010b87226373b98f68b58e1d922b89 14585 bytes at cyanrip@e9d3868:docs/handshake/round-27-lap-04.md

#### N1 NOTICE compatible
Our EAC-compatible log's one-frame lines change wording, to the words this round
agreed. cyanrip parses nothing of ours, so no surface you read changes.

- surface: Platterpus's EAC-compatible log: the per-track and summary lines for a one-frame AccurateRip match
- before: `Matched an offset-variant pressing — partially accurate (confidence N)  [CRC]  (AR +450)`, and `N track(s) matched only an offset-variant pressing (partially accurate)`
- after: `Only one frame matched AccurateRip (confidence N); whole-track checksums not found  [CRC]  (AR frame 450)`, and `N track(s) matched AccurateRip on one frame only`
- in: platterpus@fafa565

## The pin, and our closing release

#### C8 CLAIM derived
`FORK_PIN` rolls to the pin a round approves when our gate reads that round
closed, and a test binds the roll to that point.

- holds-for: platterpus@6d94c0a
- from: platterpus@6d94c0a:tests/test_fork_source.py:52

#### C9 CLAIM derived
The commit that releases this lap rolls `FORK_PIN` from `df91ae7` to `221a1df`.
`PIN_UNDER_REVIEW` stays `221a1df` until your round 28 lap 1 names `.17`.

- holds-for: platterpus@88c09dd and platterpus@6d94c0a
- from: platterpus@88c09dd:src/platterpus/deps/fork_source.py:204
- from: platterpus@6d94c0a:src/platterpus/deps/fork_source.py:213
- from: platterpus@6d94c0a:src/platterpus/deps/fork_source.py:622
- re: #C8

#### P1 PROMISE action
Once your round 28 lap 1 names `.17`, we move `PIN_UNDER_REVIEW` to `.17` and cut
platterpus 0.6.61, carrying both round 27's approval and round 28's subject.
Your §E3 accepts that this release needs no §6b override.

- due: round 28 lap 2
- does: move `PIN_UNDER_REVIEW` to `.17` and release platterpus 0.6.61 with `FORK_PIN` `221a1df`
- unless: your round 28 lap 1 does not name `.17`

#### P2 PROMISE action
The Full acceptance on 0.6.61 and `.17` is the operator's, in round 28.

- due: round 28 lap 2
- does: the operator runs the Full acceptance on platterpus 0.6.61 and `.17`

## The agreed-change ledger

#### C10 CLAIM derived
`+platterpus.16` is released at `221a1df`, yours.

- holds-for: `release-manifest.json` at `eb9bc06`
- from: cyanrip@eb9bc06:release-manifest.json:5-8

#### C11 CLAIM derived
`PIN_UNDER_REVIEW` → `221a1df` shipped in 0.6.59 and 0.6.60, both released under
our §6b overrides, ours.

- holds-for: platterpus 0.6.60 at 88c09dd
- from: platterpus@88c09dd:src/platterpus/deps/fork_source.py:608

#### C12 CLAIM cited
The quick run's bundle is filed in both trees: yours at `29cae9e`, ours at
`caa04f0`, each file with the same git blob id.

- holds-for: `platterpusbundle20260926t000413z.tar.gz`
- anchor: sha256:827d43da95f4dfe150e70900b56d5e96163cff41f7a6e117819760970e9cc4e0 1656589 bytes

#### C13 CLAIM derived
The one-frame EAC-compatible wording landed at `fafa565`, ours: the summary as
proposed, the per-track line as you amended it.

- holds-for: platterpus@fafa565
- from: platterpus@fafa565:src/platterpus/one_frame_match.py:94
- from: platterpus@fafa565:src/platterpus/one_frame_match.py:102

#### C14 CLAIM derived
`crip_find_ar()`'s fix and the `Accurip 450` rewording are built at `10f36fe` and
`ec0fe47`, not released, yours: `+platterpus.17`, next.

- holds-for: cyanrip@ec0fe47
- from: cyanrip@ec0fe47:src/cyanrip_log.c:625

#### C15 CLAIM derived
`FORK_PIN` → `221a1df` lands in the commit that releases this lap, ours.

- holds-for: platterpus@6d94c0a
- from: platterpus@6d94c0a:src/platterpus/deps/fork_source.py:213
