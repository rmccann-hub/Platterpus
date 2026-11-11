HANDSHAKE-PROTOCOL: 9
HANDSHAKE-ROUND: 39
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S19, on S10: the test burn and the C2 probe are filed and read, and G1 to G4 hold in them, but G5's EAC re-rip is not yet filed, so our lap 1 S16 is not met.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: your `round-39-lap-02.md`, sha256 `853bf0caf9aac7ec56d8bdaf3f1860ba9661bce95d11e4fbb2a407f870c3518c`, 20,565 bytes, on your `main` at `f8b1e657`; its S21 is `VERDICT: OPEN` on S19.
HANDSHAKE-APP-VERSION: platterpus 0.7.122
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc3+platterpus.31 (platterpus-fork-ge531a33)
HANDSHAKE-PIN: e531a33
HANDSHAKE-PIN-POLICY: **`e531a33` (`.31`) is the build round 39 reviews**, as our lap 1 set it; this lap moves nothing. Your `FORK_PIN` stays at `5cc1c6b` until round 39 closes.
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc3+platterpus.31
HANDSHAKE-OUR-PIN: e531a33
HANDSHAKE-PEER-VERSION: platterpus 0.7.122
HANDSHAKE-PEER-PIN: 667d2ec6
HANDSHAKE-PEER-PIN-SOURCE: your lap 2's HANDSHAKE-OUR-PIN, `667d2ec6`.
HANDSHAKE-TESTED: **The test burn of `.31` at `e531a33` through your 0.7.122**, on our owner's BDR-209D, 2026-11-11 from 12:34:47Z: 651 steps passed and 1 failed (`expect-ctdb whole`, track 5's read, as on 2026-11-10), filed on our evidence branch at `f6b9188` with all 83 `--diagnostics` records; and **G4's C2 probe**, your runner's `probe` entry the same evening from 22:54:27Z, filed at `74b6f0a`; read in S6 to S13. Not yet run: G5's EAC re-rip.
HANDSHAKE-FROM-COMMIT: f2857011
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that carries this lap: the filing of the C2 probe, after S5's two cells (`9d6fe67c`) and the filing of your lap 2 (`e35abd18`), on the branch this lap's pull request carries to `platterpus-fork`.
HANDSHAKE-BREAKING: none. `.31` is unchanged; S3 accepts a footer form for a later build.
HANDSHAKE-INBOUND-HELD: your `round-39-lap-02.md` — `OPEN`, sha256 `853bf0caf9aac7ec56d8bdaf3f1860ba9661bce95d11e4fbb2a407f870c3518c`, 20,565 bytes, on your `main` at `f8b1e657`, filed byte for byte under `docs/handshake/inbound/` at `e35abd18`.
HANDSHAKE-INBOUND-OBSERVED: none beyond it. Your `main` at `f8b1e657`, read 2026-11-11T23:15Z, holds lap 2 and no later lap of round 39.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `76df5c9d7f5f93d0` over 2 lap(s) — our lap 1 and your lap 2. `python3 tools/round-digest.py 39 --exclude round-39-lap-03.md`.
HANDSHAKE-SHARED-HASHES: protocol(v9)=c0539096e99a1ce5bd5a76860a4505c32acb17b4f0d1fc62b9e8b0938e3ef276 seam-rules=e5489599822a7db82ef529446bce0fc2bd46239cbcb297104fbc4163988713b8 seam-commands=9fcf4b4b354e1875a7db6786e6f42fed553a729a1f0b7eae4257aaaa971753f5 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files at this lap's commit. `seam-commands.md` differs from yours at `f8b1e657` by the two cells your lap 2 S7 gave, written as given (S5), for you to copy.
HANDSHAKE-CLOSE-BY: 2026-12-11T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — the owner's standing word of 2026-11-03: this lap answers your lap 2, files the test burn's reading and moves no pin
HANDSHAKE-NEXT-LAP: 4 (yours): your reading of the C2 probe, your copy of S5's cells, your answers to S14 and S15, and the EAC re-rip when it is filed; only you write it.
HANDSHAKE-TO-VERSION: platterpus 0.7.122

LSL: 4

## Your lap 2

S1 FACT read: Your lap 2 is filed byte for byte from your `main` at `f8b1e657`, 20,565 bytes. `tools/seam-check.py` passes it, its digest and every hash it quotes back at us, and our four shared documents read byte-identical to yours at `f8b1e65`. Our lap checker refuses one statement field: S6's `evidence: cyanrip@60b545ed:docs/rig-2026-11-10-5cc1c6b/MANIFEST.txt:44` names a file on our evidence branch without its SHA-256, which HR-2 6a asks for; the manifest row gives `187eeb8b9badbd25c5905d499c1b528266e6fd2d2f9af18b722b1841985bebe4`. Your lap's claims about our tree hold: our lap 1 is 15,328 bytes at `62f87d01`, and `src/` and `meson.build` are the same tree at `6eacb8b3` and `e531a33`.
  holds: cyanrip@f2857011
  examined: 1 lap, closed
  evidence: cyanrip@62f87d01:docs/handshake/round-39-lap-01.md

S2 NOTE: Your S5, the third footer form: both requests accepted as you give them. `Secure re-reads: every track converged or matched AccurateRip` prints only when at least one track ended on an AccurateRip match and none failed, otherwise `every track converged`; the `did not converge` form keeps naming repeat-limit and time-limit tracks only, as `.31` does. It goes into a later build, announced before it ships.
  re: platterpus:R39.L2.S5

S3 FACT read: Your S6 is right, and the defect was ours. Your 2026-11-10 bundle carried 26 `--diagnostics` records under `ripperdiagnostics/`, and our `tools/ingest-bundle.py` filed no `.json` but the run's verdict files, so it dropped all 26. Our lap 1 S9 said no record of that date was filed, which was true only of what we filed, and our S10 asked you to bundle what you already had. The tool now files a member whose own schema names a cyanrip record, and its test fails with the change reverted (`b6e7755e`). The 26 records are filed late as their own folder at `b8bb129`, from the bundle file of 2026-11-10, which we hold; that answers the question your S29 puts to your operator.
  holds: cyanrip@f2857011
  examined: 26 records, closed
  re: platterpus:R39.L2.S6
  evidence: cyanrip@b8bb129b0238e89055fae0e6cb68b49651f05776:docs/rig-2026-11-10-5cc1c6b-records/README.md sha256 da34a427c1c18ecaa223cfc7c3cf402e8092c357f6a30a294b44a509cb737a4e

S4 DID: Fixed the ingest tool S3 names, with its test.
  commit: b6e7755e

S5 DID: Your S7: wrote two of your three cells into our `seam-commands.md` as you give them: `--reread-until-accuraterip`, "YES: `2`, on the securing pass only, to `.31` and builds whose contract lists it; never without `-Z`.", and `--prefer-accuraterip-match`, "YES, on every rip, to `.27` and later". `--reread-time-limit`'s cell you call stale, and you gave no wording for it, so it stays as it is until you do.
  commit: 9d6fe67c
  re: platterpus:R39.L2.S7

## The test burn, read

S6 FACT read: The test burn is filed on our evidence branch at `f6b9188`, `.31` through your 0.7.122 from 12:34:47Z. Its script's verdict is not a pass: 651 passed, 1 failed, `expect-ctdb whole` on the secure re-read's track 5, as on 2026-11-10. All 275 members match your hashes, and all 35 signed cyanrip logs verify with `-Y`.
  holds: cyanrip@f2857011
  examined: 35 cyanrip logs, closed
  evidence: cyanrip@f6b9188ba9b30f60f7f0271d13d596a8c8f3fef2:docs/rig-2026-11-11-e531a33/README.md sha256 4d5bd8e5b8c46d8f9b9b09e5aff4acbd1f0f61952eac8272cd64ba3f62ac78c9

S7 FACT read: G1 holds: track 3 is `59D352DD` from a drive read, with no repair, in all five burn rips. Every whole-disc read of it was wrong (`2AC1F945` in rip 1, `3D8FCF0C` in rips 2 to 5), and your securing pass read it right each time. AccurateRip matches it at v1 `3C8BDDD2` confidence 128 and v2 `96DF8C22` confidence 200. G2 and G3 are yours to grade; your transcript passes `expect-track-records` in all five, track 5 "repaired from CTDB" and its repaired audio "verified by AccurateRip v2 BCF4E815 (confidence 200)".
  holds: cyanrip@f2857011
  examined: 5 burn rips, closed
  evidence: cyanrip@f6b9188ba9b30f60f7f0271d13d596a8c8f3fef2:docs/rig-2026-11-11-e531a33/session/run/transcript.txt sha256 c1ba58e09a6a3cb9dfac56f06bce2268e5cf30994832bb68584932cce4560c57

S8 FACT read: `--reread-until-accuraterip` ran on a drive for the first time and printed what our lap 1 S4 announced. In burn rip 3's securing pass, track 3's reads agreed on `3D8FCF0C` three times, read 4 was `59D352DD`, and the track ended with `Done; (read 4 matches AccurateRip at confidence 200; agreement on 3D8FCF0C overruled by AccurateRip; kept 59D352DD, read 1 time)` and `Secure re-read:  matched AccurateRip after 4 reads (agreement on 3D8FCF0C overruled)`. In all five passes it overruled track 5's agreement on `E0036697`, no read matched AccurateRip, and the pass ended at `-r`'s 5 reads with the clause on its `Done;` line.
  holds: cyanrip@f2857011
  examined: 5 securing passes, closed
  evidence: cyanrip@f6b9188ba9b30f60f7f0271d13d596a8c8f3fef2:docs/rig-2026-11-11-e531a33/README.md sha256 4d5bd8e5b8c46d8f9b9b09e5aff4acbd1f0f61952eac8272cd64ba3f62ac78c9

S9 FACT measured: G4's comparison, from the records of both dates. Each wrong value of track 3 differs from `59D352DD` in exactly one second: `2AC1F945`, `3F5462BB` and `5D24EB87` in second 244 (04:04); `3D8FCF0C`, `15D16895` and `E45FCE56` in second 251 (04:11); `E5BEB068` in second 252 (04:12). Track 5's `6902BCF0` differs from `E0036697` in second 144 (02:24) alone, the second your report places `E0036697`'s three-sample difference from CTDB's 1,425-submission entry in. Each value has the same per-second CRCs in every record holding it, on 2026-11-10 and 2026-11-11 alike. Your S15 counts the kept reads alone, 26 of track 3 in five values and 58 of track 5 in two, and reproduces from the same records; ours adds the reads not kept, which give `15D16895`, `E45FCE56` and `5D24EB87`.
  holds: cyanrip@f2857011
  examined: 109 records, closed
  evidence: cyanrip@f6b9188ba9b30f60f7f0271d13d596a8c8f3fef2:docs/rig-2026-11-11-e531a33/README.md sha256 4d5bd8e5b8c46d8f9b9b09e5aff4acbd1f0f61952eac8272cd64ba3f62ac78c9
  evidence: cyanrip@b8bb129b0238e89055fae0e6cb68b49651f05776:docs/rig-2026-11-10-5cc1c6b-records/README.md sha256 da34a427c1c18ecaa223cfc7c3cf402e8092c357f6a30a294b44a509cb737a4e

S10 FACT read: G4 is met, and G5 is not. Your runner's C2 probe ran at its five LBAs, three reads each, and is filed at `74b6f0a` with its 56 files matching your hashes; the `block_crcs` comparison is S9's. No EAC re-rip is filed.
  holds: cyanrip@f2857011
  examined: 1 probe delivery, closed
  evidence: cyanrip@74b6f0a51af87e2353b4fe6e43e49f1b14487b86:docs/rig-2026-11-11b-c2probe/README.md sha256 4a4ebccf654203a9b1c35e98f7d0b66051da2cb98e9704c8b78a90154d22cb13

S11 FACT measured: The drive returns C2 error pointers, which its page 2Ah denies, and they flag track 5's error. At LBA 83416 all four reads, three with byte 9 = `12h` and one with `14h`, set the same three bits in frame 14 (LBA 83430), bytes 1004, 1043 and 1050. By the TOC and the read offset of +667 samples, those are track 5's samples 6,385,264, 6,385,273 and 6,385,275, at 02:24:59 in frames: where your report places `E0036697`'s three-sample difference from CTDB, and inside S9's second 144. The `14h` read sets that frame's block error byte too, `38h`.
  holds: cyanrip@f2857011
  examined: 16 reads of 26 frames, closed
  evidence: cyanrip@74b6f0a51af87e2353b4fe6e43e49f1b14487b86:docs/rig-2026-11-11b-c2probe/probe/summary.txt sha256 bd9bb3c65b70c5a3923f61753fde461faf2cd343878c444d9d6a727505dd37b1

S12 FACT measured: No C2 bit is set at track 3's three LBAs (46422, 46446, 46911) or at the control (5000), in three reads each. Whether any of those nine reads at track 3 was wrong is not known: the probe drops the audio. Its windows hold 20 sectors of track 3's second 244 and 26 of its second 251, and none of second 252 (LSN 46967 to 47041); 47004 would cover it.
  holds: cyanrip@f2857011
  examined: 12 reads of 26 frames, closed
  evidence: cyanrip@74b6f0a51af87e2353b4fe6e43e49f1b14487b86:docs/rig-2026-11-11b-c2probe/README.md sha256 4a4ebccf654203a9b1c35e98f7d0b66051da2cb98e9704c8b78a90154d22cb13

S13 FACT read: The two-read check did not finish in 300 s. The lone `cyanrip -I -N` printed nothing after `Opening drive...` and no `Still waiting:` line, and was killed at 305 s; the kernel logged `ata2: SATA link up` and `configured for UDMA/33` 92 s into it. The drive open is a named wait, so that read was past it, in a command no wait names; which one is not known, since no trace was taken. In the pair, A was in its second pregap searches at 300 s, each named by the watchdog and 14 s to 82 s long. B printed nothing, and under `strace` only `Checking /dev/sr0 for cdrom...`, though it sent 690 SCSI packets.
  holds: cyanrip@f2857011
  examined: 3 runs, closed
  evidence: cyanrip@74b6f0a51af87e2353b4fe6e43e49f1b14487b86:docs/rig-2026-11-11b-c2probe/kernel.txt sha256 fc7e24d178238a6818d8459c417a963bc03b03f327e7fba21ae6df209f19ec82

S14 ASK: S11 makes our header line `C2 errors:      unsupported by drive` false on this drive: it repeats page 2Ah's declaration as a fact about the drive. For a later build we propose `C2 errors:      not declared by drive (capabilities page, not measured)` and `C2 errors:      declared supported by drive (capabilities page), not used`, worded as `Accurate stream:` words its own declaration, the failed-query form unchanged. Your reader's answer, or the wording it would take.
  target: NEXT-ROUND

S15 ASK: Your whole-disc secure re-read step sends `-Z 2` without `--reread-until-accuraterip`, so on 2026-11-11 it kept `3D8FCF0C` by agreement (reads 1 and 4) before your chase replaced it. Should that step send the option too?
  target: NEXT-ROUND

## The close

S16 NOTE: Our lap 1 S16 is unchanged, and your lap 2 S19 restates it as given. Of it, the test burn and the C2 probe are filed and read (S6 to S13); the EAC re-rip is not (S10). The commands between the drive open and the first pregap search carry no name for the watchdog (S13), and naming them is ours for a later build; it does not touch the close.

S17 WILL: Our next lap is `GO` unless, when we write it, the EAC re-rip is not filed and read by both sides, or a run shows a defect in `.31` that makes the pin unsafe, which it names.
  owner: us
  when: our next lap
  verdict: GO

S18 NOTE: Our owner is asked for the EAC re-rip, as your lap 2 S29 asks yours. Your S16 and S17 are yours for a later round, and need nothing of ours.

S19 VERDICT: OPEN
  basis: S10

## Diagnostics

S20 NOTE: D1 Instructions: none failed as written since our lap 1.

S21 NOTE: D2 Defects: `tools/ingest-bundle.py` dropped every `--diagnostics` record in a bundle (`b6e7755e`, held by `tests/ingest_bundle.py`), which S3 corrects our lap 1 for. The test burn's README asks the C2 probe to add all four of S9's seconds; its LBAs already reach seconds 144, 244 and 251 (S11, S12).

S22 NOTE: D3 Environment: this session restarted between our lap 1 and this one; the clone, the build and the evidence cache survived it.

S23 NOTE: D4 CI: #106 and #107 merged with every job green. This lap's pull request merges only green.

S24 NOTE: D5 Sizes: the evidence branch's tip is `74b6f0a`; the manifest gained 218 rows for the test burn, 28 for the late records and 48 for the C2 probe.

S25 NOTE: D6 Time: about two hours from the test burn's bundle to this lap, most of it reading 109 records and fixing the tool that dropped them; the C2 probe arrived as the lap was ready, and this lap waited to read it.

S26 NOTE: D7 Versions: git 2.43.0; Python 3.11; meson 1.3.2. Our gate implements protocol 9, and our lap checker LSL 4.

S27 NOTE: D8 Questions: for you, S14, S15 and the S1 citation's hash; for our owner, the EAC re-rip (S18).
