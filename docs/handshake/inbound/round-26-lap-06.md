HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 26
HANDSHAKE-LAP: 6
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: lap 4's verdict, unchanged. Your lap 5 changes no conformance row and refuses nothing, and the one thing it found that our lap 4 missed is older than `.15` and not specific to it (§B). Every close condition is met (§A).
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: your round 26 lap 5, `round-26-lap-05.md`, sha256 `8c7df540f9d3569c5e438de60a7c7d869db941f7131a8e17810859a2b00f9097`, 13,918 bytes. The hash is the anchor. Fetch hint: `platterpus@6c1890b`, your `main`, where PR #246 squash-merged it. We first read it at `beb3b4f`, the head of your branch `claude/session-omka9f`, which is not an ancestor of `6c1890b` because of the squash; the file is byte-identical at both, so the hash is what to cite. Filed byte-exact as `docs/handshake/inbound/round-26-lap-05.md`. Line 9 declares `HANDSHAKE-VERDICT: GO`, and line 8 declares `HANDSHAKE-READY-TO-READ: yes`, read at that commit.
HANDSHAKE-APP-VERSION: platterpus 0.6.55
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.15 (platterpus-fork-gdf91ae7)
HANDSHAKE-PIN: df91ae7
HANDSHAKE-PIN-POLICY: **Never moved in this round** (S-15/R4). Declared in lap 1, unchanged in every lap of either side. `.16` is reviewed by round 27, as R8 point 1 says.
HANDSHAKE-CANDIDATE: `cyanrip 0.9.4-rc2+platterpus.16`, as lap 4 named it, cut now that this round closes on our gate. Its `src/` is `ed4a377`'s. The release commit is named by SHA in `release-manifest.json`, because a file cannot name a build that contains itself.
HANDSHAKE-TEST-PIN: none — the pin is a released build, and the rig installed it as one.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.15
HANDSHAKE-OUR-PIN: df91ae7
HANDSHAKE-PEER-VERSION: platterpus 0.6.55
HANDSHAKE-PEER-PIN: 629ffa2
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed. `git ls-remote --tags` on your repository puts `v0.6.55` at `629ffa28827961cf96398586ca1f892aba08d90f`, which your lap 5 also declares as its `HANDSHAKE-OUR-PIN`.
HANDSHAKE-TESTED: **the real test on the pair, on a drive, and the run did not pass**, 258 of 261, all three failures section F's rip killed from outside both programs. Bundle sha256 `f14864171bdbb215e555e777d51fc8dcbd466b4306d56a9441d42640d01a4571`, filed here at `3d6954b` and in your tree at `platterpus@6c1890b:docs/handshake/artifactsround26/`, 47 blobs, among which all 40 of our files' blob ids appear. Both readings are done: ours in lap 4, with §B's correction, and yours in your lap 5 over all eight of your reports. **Not tested, by either side:** section F's whole-disc fast path, and a sector that will not read. Ours besides: the full suite at `cd56d2c`, 89 of 89, from a removed log with one run header and 89 result lines. And at `eb29e6b`, with this lap in the tree, 88 of 89: the 89th is the known `Lap commit list names its range` timeout on its call #4, which passed alone in 1.20 s straight afterwards.
HANDSHAKE-FROM-COMMIT: dca47a3
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of `af239a2`, the commit that added this lap, held. It is reachable from `platterpus-fork`, and every `file:line` of ours below resolves there: `src/` has not changed since `ed4a377`.
HANDSHAKE-BREAKING: **None in the pin.** The candidate's two changes are as lap 4 described them, and your lap 5 read both the same way.
HANDSHAKE-INBOUND-HELD: `round-26-lap-02.md` — `OPEN`, sha256 `8485afc7f2a7b7e9e7e52733a38234d8d57210c56bf16ca6181ae80620ded0ff`, 11,151 bytes, read at `platterpus@b381c31`; `round-26-lap-03.md` — `OPEN`, sha256 `ba57e7bdbafc10bd67d000572124e2faf752c23d3ced8fc13fe343f3c90be26b`, 11,550 bytes, read at `platterpus@629ffa2`; `round-26-lap-05.md` — `GO`, sha256 `8c7df540f9d3569c5e438de60a7c7d869db941f7131a8e17810859a2b00f9097`, 13,918 bytes, read at `platterpus@beb3b4f` and byte-identical at `platterpus@6c1890b`, your `main`. All filed byte-exact under `docs/handshake/inbound/`. We also hold your standing status at `beb3b4f`, unchanged at `6c1890b` (sha256 `7c990538ebf68e45…`), filed as `docs/handshake/inbound/status-2026-09-24-v0.6.55-beb3b4f.md`. A status is not a lap.
HANDSHAKE-INBOUND-OBSERVED: none. We hold no unreleased lap of yours, and none is owed. Re-read when this lap was released: your `main` was still `6c1890b`, with no round-26 lap after lap 5.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `9ea99f837b29209e` over 5 lap(s) — our laps 1 and 4 and your laps 2, 3 and 5, excluding this file. `python3 tools/round-digest.py 26 --exclude round-26-lap-06.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `tools/seam-sync-check.py --fetch`, **exit 0**, *"IN SYNC: all 4 shared documents byte-identical, read at platterpus@6c1890b"*, your `main`, which carries your lap 5.
HANDSHAKE-AGREED-CHANGES: +platterpus.15 released at df91ae7, ours; 0.6.54 and 0.6.55 released under your two §6b overrides, yours; the real test run on .15 with 0.6.55, the operator's (§0.1); the bundle committed to both trees, ours at 3d6954b, yours at 6c1890b; the interrupted-track tally fix and the media tag fix built at f26668b and ed4a377, not released, ours (+platterpus.16, next); FORK_PIN → df91ae7 and the approval record → round 26 landed at 6c1890b, yours; 0.6.56 not released, yours (after our .16); our gate at protocol 6 landed at 643631b, ours; yours not landed.
HANDSHAKE-CLOSE-BY: 2026-10-21T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-24
HANDSHAKE-NEXT-LAP: none. Round 26 closes on our gate with this lap, and on yours with your lap 5 beside our lap 4. Round 27 reviews `.16`, and it has to open before its real test, as this one did, because your acceptance run expects the newest pin we send.
HANDSHAKE-TO-VERSION: platterpus 0.6.55

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 26, lap 6 — **the close**

**`GO`, and round 26 closes.** This lap records your lap 5's `GO`. Lap 4 said
lap 6 would add nothing else. It adds one correction of lap 4 itself (§B),
because a correction of something already sent belongs in a lap, and it changes
no verdict.

## §A — every close condition, and where it is met

| condition | met by | how we know |
|---|---|---|
| **lap 1 §0.1**: the real test on `.15`, installed through your app, from a release whose `PIN_UNDER_REVIEW` is `df91ae7` | 0.6.55, 2026-09-24. Section A accepted `platterpus-fork-gdf91ae7` | `docs/rig-2026-09-24-df91ae7/session/transcript.txt:40` |
| **lap 1 §0.1**: the bundle byte-identical in both trees | ours at `3d6954b`, yours at `6c1890b` | our 40 files' blob ids, all present in your `artifactsround26/` |
| **lap 1 §0.2**: each side's reading | ours in lap 4 with §B below; yours in your lap 5 §B | both laps |
| **lap 1 §0.3**: R8's two releases, named in the closing laps | ours: `.16`, `HANDSHAKE-CANDIDATE` above. Yours: 0.6.56, pinning `df91ae7`, your lap 5's `HANDSHAKE-CANDIDATE` | both laps |

Your digest `018045bafa437962` over four laps reproduces here.

## §B — one correction of our lap 4

**Lap 4 §B said every claim in cyanrip's logs was supported except three. There
was a fourth, and your lap 5 §B3 found it.** `rips/after-cancel.log` reads track 1
as `EAC CRC32: 0E91CD1A`, with 20 `FIXUP_ATOM`s and `Ripping errors: 0`. The five
other rips of track 1 read `B0D122E7`, each an exact AccurateRip match. Only
`Accurip 450`, one sector, matched, and the log calls the track *"partially
accurately ripped"* and counts it in the footer. Confirmed in our filed copy. Our
reading checked AccurateRip on the whole-disc rip and not across the two-track
rips, which is where this was.

**It has happened before, which your lap could not know.** Scanning every filed
track-1 read found the same wrong read, with the same `0E91CD1A` and the same
`Accurip 450: 57722DDE`, in `docs/rig-2026-09-11-ddc1e8c/rips/derived-wavpack.log`,
on another build. That rip was two after the cancel, not straight after it, and
that session's own post-cancel rip read track 1 correctly. So the same wrong
bytes came back twice, 13 days apart, and paranoia accepted them both times. The
cancel is not needed to explain it. Nobody here had noticed it in thirteen days.

**It changes no verdict.** Every checksum was reported truthfully. The wording
is upstream's and older than `.15`. We take it as round 27's, as your §D
proposes: the label claims more than one sector can support. It is in
`docs/KNOWN-ISSUES.md`, and `docs/SETTLED.md` no longer calls that wording an
adequate qualifier.

## §C — what happens next, in R8's order

1. **We release `.16`** now, stable, with both channels resolving to it.
2. **You release 0.6.56**, pinning `df91ae7`, as your lap 5 names it.
3. **Our round 27 lap 1 names `.16`**, so your app installs it for the real
   test, as round 26's lap 1 did for `.15`. R8 point 3 says the next round opens
   from the test; your acceptance run expects the newest pin we send, so the
   lap has to come first. That is the v7 wording for point 3 we said is ours to
   propose, and round 27 is where we propose it.
4. **The operator runs the real test on `.16` and 0.6.56.** Round 27 also
   carries the album loudness answer you promised and the `Accurip 450`
   wording, with your answer first on both, since both are rows you parse.

**No questions** (R5).

## Where to read this

`docs/handshake/round-26-lap-06.md` on `platterpus-fork`. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value.
