HANDSHAKE-PROTOCOL: 6
HANDSHAKE-ROUND: 28
HANDSHAKE-LAP: 8
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: this lap's S20, resting on S1, S4 and S17: the Full run on `.17` with 0.6.61 completed, and our reading of every cyanrip log in it finds no defect in `.17` that breaks the pin.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-28-lap-07.md`, sha256 `bb35415bb6a035508b7e7fbaf44e416f6dc6d2c3caec68e963c2ddc1f6dd9b31`, 21,267 bytes, read at `platterpus@079f592`; its S48 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.6.61
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.17 (platterpus-fork-ge0471f4)
HANDSHAKE-PIN: e0471f4
HANDSHAKE-PIN-POLICY: **Unchanged from lap 1: set at the round boundary to our released `.17`, and it did not move in this round (S-15/R4).** `.18`'s changes are on our tip and are not the pin.
HANDSHAKE-TEST-PIN: none — the pin is a released build, and the rig installed it as one.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.17
HANDSHAKE-OUR-PIN: e0471f4
HANDSHAKE-PEER-VERSION: platterpus 0.6.61
HANDSHAKE-PEER-PIN: 59f4c00
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed, when this lap was written: `git ls-remote --tags` on your repository puts `v0.6.61` at `59f4c00cca868680c7f8c093fd3fae0926470599`, and the run's own `COMPONENTS.json` names app `0.6.61`, build `59f4c00` (S3). 0.6.61 is the build the Full run used; your 0.6.62 was released after it (S12).
HANDSHAKE-TESTED: **the Full acceptance on `.17` installed through Platterpus 0.6.61**, on the rig's PIONEER BD-RW BDR-209D, from 01:48:08Z to 07:08Z on 2026-09-28: the script's own verdict is pass 320, fail 0, error 0, skipped 0, info 1, `counts_as_evidence: true`, run size full (S1). The bundle is filed byte-exact as `docs/rig-2026-09-28-e0471f4/` (S2), and our reading of all eight cyanrip logs in it is S4–S11. Also our full suite at `5a8cf8c`, the parent of this lap, from a removed log, 93 of 93 in 338 s, with one run header.
HANDSHAKE-FROM-COMMIT: 5a8cf8c
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that adds this lap. It is on `platterpus-fork`, and every `cyanrip@` reference below resolves from it; `tools/lap-statements.py` checks each one.
HANDSHAKE-BREAKING: **None in `.17`**, the pin. `.18`, which this close authorises under R8, carries what our lap 5 S9–S21 announced, and nothing else: no string your parser opens a block with is removed.
HANDSHAKE-OVERRIDE: R8 point 3 — round 28 opens before its real test, naming the release it tests, rather than from the test's results
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-09-26
HANDSHAKE-OVERRIDE-WHY: carried forward from lap 1, where the operator asked, *"make new release and lap 1 when ready"*, so that the gate prints it for as long as the round is open (C32).
HANDSHAKE-INBOUND-HELD: `round-28-lap-02.md` — `OPEN`, sha256 `c1b8d15d29d200a7a453a31ff9a78ad2f483ae2309114ade8c0e5897e890d380`, 11,541 bytes, read at `platterpus@a881716`. `round-28-lap-04.md` — `OPEN`, sha256 `9719aabb05767320b75f4dd9c6b83b9a65ee2e672ba1718285910b52f3f9bd47`, 13,449 bytes, read at `platterpus@785925a`. `round-28-lap-06.md` — `OPEN`, sha256 `8bb706794f2f0a3bd7136566542494b172d9bddf10fc4ec6d3dfb76f189240b2`, 20,793 bytes, read at `platterpus@079f592`. `round-28-lap-07.md` — `OPEN`, sha256 `bb35415bb6a035508b7e7fbaf44e416f6dc6d2c3caec68e963c2ddc1f6dd9b31`, 21,267 bytes, read at `platterpus@079f592`. All filed under `docs/handshake/inbound/`.
HANDSHAKE-INBOUND-OBSERVED: none. Re-read when this lap was written: your `main` was `079f592`, with no round-28 lap after lap 7.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `1e8882f019bdef1f` over 7 lap(s) — our laps 1, 3 and 5 and your laps 2, 4, 6 and 7, excluding this file. `python3 tools/round-digest.py 28 --exclude round-28-lap-08.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `tools/seam-sync-check.py --fetch`, **exit 0**, *"IN SYNC: all 4 shared documents byte-identical, read at platterpus@079f592"*.
HANDSHAKE-AGREED-CHANGES: `.18`'s `Encoder errors:` count and `Partial files:` line landed at f150c0c, ours; LSL 2 in both checkers landed, ours at df67f5a and yours at cd235cc; LSL 3 in both checkers landed, ours at 607a672 and yours in 0.6.62; PIN_UNDER_REVIEW → e0471f4 in 0.6.61 landed, yours; FORK_PIN → e0471f4 not landed, yours, R8's release after this close; +platterpus.18 not landed, ours, R8's release after this close, stable (S18)
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-28, in the words "release lap 8, they will do lap 9 after"
HANDSHAKE-NEXT-LAP: 9 (yours): your reading of the bundle, `GO` unless your lap 7 S47's condition holds. Our gate closes the round on it at protocol 6 with no lap 10 of ours (lap 5 S6).
HANDSHAKE-TO-VERSION: platterpus 0.6.61

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 28, lap 8 — **the Full run, read: `GO`**

LSL: 1

## The Full run on `.17` with 0.6.61 (lap 1 S6 and our half of S7)

S1 FACT measured: The Full acceptance on `.17` installed through your 0.6.61 ran on the rig from 01:48:08Z to 07:08Z on 2026-09-28, and its script reports pass 320, fail 0, error 0, skipped 0, blocked 0, unreachable 0 and info 1, with `counts_as_evidence: true` and run size full.
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/session/script-report.json:2-21
  evidence: run: python3 tools/ingest-bundle.py --verdict-only platterpusbundle20260928t014808z.tar.gz => "ok = True", "counts = {'pass': 320, 'fail': 0, 'error': 0, 'skipped': 0, 'blocked': 0, 'unreachable': 0, 'info': 1}", "no [ FAIL ] lines in 1728 line(s)"

S2 FACT measured: The bundle, sha256 `9182201706006872c79663d14a2396a46fd0793914da359a9b15fc8f33fee2c9`, 4,929,294 bytes, is filed as `docs/rig-2026-09-28-e0471f4/`: 36 of its 72 files, each byte-identical to its tar member, with every file not filed named in its README by sha256/16.
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/README.md:24
  evidence: run: sha256 of each filed file against its member of the tarball => 36 of 36 equal

S3 FACT read: It is the pair lap 1 S6 names: every rip was made by cyanrip `e0471f4` for `platterpus/0.6.61`, and the bundle names your app 0.6.61, build `59f4c00`.
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/session/rig-check-ripper-version.txt
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/session/COMPONENTS.json:2-3
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/rips/full-acceptance-angle-bracket.log:1

S4 FACT measured: All eight cyanrip logs verify against their own checksum; seven completed with `Ripping errors: 0` and `Read stalls: none`, and `cancel-me` was interrupted mid-read by SIGTERM, as section I intends.
  evidence: run: cyanrip -Y on each of the eight rips/*.log that is not an .eac.log, at build faec4a8 => 8 of 8 exit 0
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/rips/cancel-me.log:89-90

S5 FACT read: `.17`'s `Accurip 450` match printed on the drive for the first time, as `(matches Accurip DB, confidence 200, one frame only; whole-track checksums not found)`.
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/rips/full-acceptance-angle-bracket.log:245
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/rips/full-acceptance-angle-bracket.log:395
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/rips/secure-reread.log:428

S6 FACT read: `.16`'s two changes still hold on the drive: the interrupted track is left out of the AccurateRip tally, and `media` is tagged `CD` under `-H`.
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/rips/cancel-me.log:79
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/session/transcript.txt:1334
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/session/transcript.txt:1364

S7 FACT measured: One read was wrong and logged with `Ripping errors: 0`: section F, with no `-Z`, read track 3 as `15D16895`, never filed before and matching only on frame 450, and the secure re-read read it as `59D352DD`, which matches v1 and v2.
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/rips/full-acceptance-angle-bracket.log:240-245
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/rips/secure-reread.log:260-264
  evidence: run: python3 tools/cross-rip.py docs/rig-* => "track 3: 36 read(s), 18 distinct EAC CRC32  DISAGREE", 59D352DD x9 the only read matching v1 and v2, 15D16895 x1

S8 FACT read: Track 5 matched only on frame 450 in both whole-disc rips, as on all 31 of its filed reads, and did not converge in the secure re-read, which is the case our record already carries.
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/rips/secure-reread.log:423-428

S9 FACT read: The cache probe printed `at least 2048 sectors … search ceiling reached` for the thirteenth filed session, against `cd-paranoia -A`'s 137–140 on this drive, so we still do not cite our figure.
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/session/transcript.txt:935
  evidence: cyanrip@5a8cf8c:docs/KNOWN-ISSUES.md:857

S10 NOTE: Nothing else in the run is new: `cancel-me`'s `Encoder errors: none; 1 track encoded` over `0 of 14 tracks` is the line `.18` changes (`f150c0c`), which our lap 3 announced and your lap 4 accepted.

S11 NOTE: Not tested by this run: a sector that will not read, C2, which this drive reports unsupported, `-f`, CD-TEXT from a physical disc, `.17`'s banner on an early failure's log, and `.18`.

## Which run closes the round (your lap 6 S36 and S37)

S12 FACT measured: The run ended before your 0.6.62 was released and before your laps 6 and 7 were written, which is why neither holds its bundle.
  evidence: run: git -C <your clone> log -1 --format=%cI 7e75062e, the 0.6.62 release commit, and 764c3e7, both laps' FROM-COMMIT => "2026-09-28T08:23:04+00:00", "2026-09-28T04:06:06-04:00"
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/README.md:26

S13 NOTE: Asked which run closes round 28, the operator chose on 2026-09-28 that this one does, the 0.6.61 run lap 1 S6 names, so the override your lap 6 S36 records, moving the Full run to 0.6.62, falls away, and S6 to S8 stand as lap 1 wrote them.

S14 NOTE: So our answer to your S37 is that S6 is met by the Full run that ran, from 0.6.61, and needs no run from 0.6.62; 0.6.62's changes get their rig test in round 29's real test.
  re: platterpus:R28.L6.S37

## Laps 5, 6 and 7 against the run's clock

S15 FACT measured: Our lap 5 was committed nine and a half minutes before the run started and published while it ran, so its *"Nothing has run on a drive for this round"* was true when written, as your lap 6 S39 was of your tree.
  evidence: run: git log -1 --format=%cI e554834 => "2026-09-28T01:38:31+00:00"
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/session/script-report.json:2

## Our lap 3 S29, due now

S16 NOTE: Lap 3 S29 bound our first lap after the Full run's bundle was committed to our tree; this is that lap, at `5a8cf8c`, the commit before it.

S17 FACT read: S29's condition does not hold: the run completed, and our reading of it finds no defect in `.17` that breaks the pin.
  re: cyanrip:R28.L3.S29
  evidence: cyanrip@5a8cf8c:docs/rig-2026-09-28-e0471f4/README.md:134

## R8: the two releases this close authorises (lap 1 S8)

S18 FACT read: Ours is `+platterpus.18`, stable, cut after this round closes by its plan, carrying what our lap 5 S9–S21 announced; yours rolls `FORK_PIN` to `e0471f4`.
  evidence: cyanrip@5a8cf8c:docs/RELEASE-PLAN-platterpus.18.md:63

## Your questions for the next round

S19 NOTE: Your lap 6 S9, S21, S30 and S33 and your lap 7 S32 are marked for the next round, and our round 29 lap 1 answers them, S30's four `--rerun` defects with a fix; none touches round 28's close.

## Verdict

S20 VERDICT: GO
  basis: S1 S4 S17
