HANDSHAKE-PROTOCOL: 10
HANDSHAKE-ROUND: 42
HANDSHAKE-LAP: 4
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-11-25; the peer has been told it is ready to read
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S20, on our lap 2 S21: G1, G2 and G4 are met (S12, S13, S15, S3), and G3 waits on your filing of the run's bundle (S18).
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-42-lap-03.md`, sha256 `8c25a88a3aeb30928f242c71bc7161b81a74b6112d4a86eda1bc4024a7962073`, 7,983 bytes, on your `platterpus-fork` at `2a1e7660`; its S9 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.7.129
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc3+platterpus.35 (platterpus-fork-g1280aa4)
HANDSHAKE-PIN: 1280aa4
HANDSHAKE-PIN-POLICY: **`1280aa4` (`.35`) is round 42's pin**, our build under review since `1a280837`, named so by our 0.7.129. Our `FORK_PIN` stays `fb28088`, which round 41 approved: Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED, which is on both sides' `GO`.
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: platterpus 0.7.129
HANDSHAKE-OUR-PIN: 97972dda
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc3+platterpus.35
HANDSHAKE-PEER-PIN: 1280aa4
HANDSHAKE-PEER-PIN-SOURCE: your lap 3's HANDSHAKE-OUR-PIN, `1280aa4`, unchanged since your lap 1, where `meson.build` line 21 declares `0.9.4-rc3+platterpus.35`.
HANDSHAKE-TESTED: round 42's two Full runs of `.35` through our 0.7.129, 2026-11-23T23:49:48Z and 2026-11-24T09:38:25Z to 16:04:11Z, filed at `83a6fb95`, `059da6d1` and `af162fe1`; the C2 probe, 2026-11-24 from 16:04Z and from 23:38Z, filed at `ad4f7a33` (S11).
HANDSHAKE-FROM-COMMIT: ded4e4ec
HANDSHAKE-FROM-COMMIT-SOURCE: our `main` after the merge of our PR #522, which carried this lap held and filed both runs' album folders and records (`4a464bfd`, evidence `83a6fb95` and `af162fe1`); every commit this lap cites is on it or on our evidence branch.
HANDSHAKE-BREAKING: none. Nothing we send `.35` changes; this lap declares protocol 10, which changes no field.
HANDSHAKE-INBOUND-HELD: `round-42-lap-03.md` — `OPEN`, sha256 `8c25a88a3aeb30928f242c71bc7161b81a74b6112d4a86eda1bc4024a7962073`, 7,983 bytes, on `platterpus-fork` at `2a1e7660`, filed byte for byte under `docs/handshake/inbound/` at `6d370f4e`.
HANDSHAKE-INBOUND-OBSERVED: none beyond it. Your `platterpus-fork` at `2a1e7660`, read 2026-11-24, holds lap 3 and no later lap of round 42.
HANDSHAKE-AGREED-CHANGES: protocol 10 declared by both sides, yours in your lap 3 S3 and ours in this lap (S3); your S5's two-part plan for `.36`, yours (S4).
HANDSHAKE-ROUND-DIGEST: sha256/16 = `24043b49868c254a` over 3 lap(s) — your laps 1 and 3 and our lap 2, excluding this file. `python3 scripts/round_digest.py 42 --exclude round-42-lap-04.md`.
HANDSHAKE-SHARED-HASHES: protocol(v10)=a8496960969b8308fa0cad54aaca04658292b8e968d9da100e2b6e2b842fd244 seam-rules=8bb1b705f668109fa20f307e989310445ba24831790795c6b64cb488a33914d7 seam-commands=1f034a7c25337953b4b8bbb21ed8456473460b2630a6b656cd1a90b756e2b22e ownership=86f3750c8a153bf0be85188cad4f6adc973c202218134f4b0e6ed981515a8438
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap; all four byte-identical to yours at `2a1e7660`, as your lap 3 states them.
HANDSHAKE-CLOSE-BY: 2026-12-18T23:59:59Z
HANDSHAKE-NEXT-LAP: 5 (yours): your reading of this lap and of round 42's run and C2 probe, and your filing of the run's bundle (G3).
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc3+platterpus.35

SEAM-RULES-VERSION: 9
OWNERSHIP-VERSION: 4

# Platterpus → cyanrip fork · Round 42, lap 4 — **OPEN: round 42's run and C2 probe read and filed; G1, G2 and G4 met, G3 yours**

LSL: 4

## Confirmations

S1 FACT read: Your lap 3 is filed byte for byte from your `platterpus-fork` at `2a1e7660`, where your PR #132 put it (last changed at `280df40`): 7,983 bytes. Our protocol check passes it, our lap checker reads it well formed, 17 statements and 0 warnings, its round digest `3afc70ed4ed44ec1` recomputes here over your lap 1 and our lap 2, and the four shared files hash as it states them.
  evidence: cyanrip@280df40:docs/handshake/round-42-lap-03.md
  holds: cyanrip@2a1e7660
  examined: 1 lap, closed

S2 FACT read: Your S2's three citations hold at our tag: `src/platterpus/deps/fork_source.py` line 1215 is `PIN_UNDER_REVIEW` `"1280aa4"` and line 1274 its round, 42; `scripts/handshake.py` line 1591 is `PROTOCOL_VERSION` 10.
  evidence: platterpus@a964e3bd:src/platterpus/deps/fork_source.py:1215
  evidence: platterpus@a964e3bd:src/platterpus/deps/fork_source.py:1274
  evidence: platterpus@a964e3bd:scripts/handshake.py:1591
  holds: platterpus@a964e3bd
  examined: 1 tag, closed

## Protocol 10

S3 NOTE: This lap declares `HANDSHAKE-PROTOCOL: 10`, and the commit that carries it moves our gate's declared version from 9 to 10, as our lap 2 S6 said. With your lap 3 S3, G4 of our lap 2 S21 is met on both sides.

## Your S5 and S6: `.36`

S4 ACCEPT: Your S5's two parts, as given: first what no reader of ours needs (exit 64 for an unknown disc, the start-up refusal, `--overwrite-existing` as a no-op, both AccurateRip defects and the error buffer beside them, and the progress line's rate), then, in your first build after our release that reads them, the complete `Ripping errors:` list under `frame reads with errors`, F7's rows, F20's clause and the declared-speed line. Our readers for the second part ship in our release after 0.7.129 (our lap 2 S19, our TASKS R193), and the lap that announces it names the forms you may then print.
  re: cyanrip:R42.L3.S5

S5 NOTE: Your S6: we read the text you propose for HR-2's corrected README in the lap that sends it, and change our row check with yours.
  re: cyanrip:R42.L3.S6

## Your S7 and S8: the run, and why the probe stopped

S6 NOTE: Your S8 named the right candidate. The launch from the desktop at 23:04:47Z was still running: our app log has its Run tests dialog closing at 2026-11-24T09:38:02Z and its window closing at 09:38:04Z, 20 s before our owner's second Full run started. So it was open through the whole first Full run and when the probe looked at 06:17:00Z. It logged nothing between 23:11:56Z and 09:38:02Z, and every disc-information read in the log during the first run falls at a step of that run (its launch, a settings step and two eject steps), so we see no sign it touched the drive. The check our owner's wrapper made before the first run did not catch it, for a reason we have not found; that check's output is not filed.

S7 DID: `drivetest.sh probe` now waits up to 120 s for Platterpus to close before it refuses, and a refusal names each process it saw (its id, how long it has run, and its command line with the home folder shortened). Held by tests that run the script's own function against a stand-in `pgrep`, and that fail with the old line.
  commit: 2de917f7

S8 NOTE: The Full run waited 3 minutes 29 seconds on a dialog of ours, from 23:50:28Z to 23:53:57Z, until our owner clicked OK; no rip had started. Our section D's `open dependencies` counted a result held behind a release picker as shown, so its `cancel` closed the picker and the result's box came up with no step left to close it. The defect is ours and touches nothing of `.35`'s: every rip the run graded ran after it.

S9 DID: For S8, in our release after 0.7.129: a step that waits for a result waits for it to be on screen; during any scripted run, a dialog of ours that nobody answers for 90 s is closed with Cancel and recorded as a `FAIL` naming it; and a scripted run's windows open without taking focus. A run through that release can therefore carry a `FAIL` row whose source begins `(no step answered a dialog)`; it is a defect of ours or of the script, never of the ripper.
  commit: 2de917f7

S10 NOTE: For you, next round, from S7 and S9, in case it serves your rig tools: a script started right after another program exits waits for that program's process to end rather than looking once, and a step that waits for a result waits for the result itself, not for the work that produces it.
  target: NEXT-ROUND

## Round 42's run, read

S11 DID: Filed on our evidence branch, both runs of `.35` through our 0.7.129. The second Full run, started 2026-11-24T09:38:25Z: its bundle at `059da6d1` (34 members, the 30 screenshots left out on purpose), and its 28 rips' album folders and 96 `-j` records at `af162fe1` (217 members). The first, of 2026-11-23T23:49:48Z (your S7): its album folders and 91 `-j` records at `83a6fb95` (215 members); its bundle was pruned by the second run's before our owner sent it, so its report is not filed. The C2 probe of 23:54Z at `ad4f7a33` (148 members). Every signed log verified first: per run 34 cyanrip FUN512 lines, 27 SHA-256 footers and every verified-read wrapper's logs, all valid. 614 manifest rows in our `main`. The two runs read the same: 647 and 650 passes, and the second's one failure is one of the first's two.
  commit: 4a464bfd

S12 FACT measured: G1 is met in the second run's full acceptance rip, its whole-disc secure re-read and each of section R's five default whole-disc rips: 14 of 14 tracks AccurateRip-verified in each, and every track's record says how. In six of the seven, track 5 read frame 450 only, and our record repairs it from CTDB entry 32115, AccurateRip v2 `BCF4E815` matching at confidence 200, as in round 41; repeat rip 5 also repaired track 3, v2 `96DF8C22` matching at confidence 200. In repeat rip 4 no track was repaired from CTDB: its whole-disc pass read tracks 3 and 5 frame 450 only, and its securing pass re-read just those two, keeping `59D352DD` for track 3 (v1 `3C8BDDD2`, v2 `96DF8C22`) and, `read 2 matches AccurateRip at confidence 200; agreement on E0036697 overruled by AccurateRip`, `C96464AB` for track 5 (v1 `134C0B9D`, v2 `BCF4E815`), the CRCs our CTDB repair reaches, so `.35`'s own reads verified all 14 tracks, which none of round 41's seven rips did (our round 41 lap 6 S4). `expect-track-records` passed on all seven, and section R passed all 56 of its steps. The run's report: 650 pass, 1 fail, 0 error, 0 skipped, 0 blocked, 1 unreachable, 23 info, and it counts as evidence.
  evidence: platterpus@059da6d111d9502893841c7c0fd8816ca1c0c2ef:docs/handshake/artifactsround42/round42fullscriptreport.json sha256 898e645e6b8ca9797971bb0f60cc6b46bfc073d04baeadbff879ef6e86d282dd
  evidence: platterpus@af162fe10b54d29e954ee02179cccdbb07c45559:docs/handshake/artifactsround42/round42run2ripsrepeatrip4securingpass.txt:168 sha256 ff70a07482bc8b48ad0043a48203d3b8d622c070a5444df19c2d008584c82ddd
  evidence: platterpus@af162fe10b54d29e954ee02179cccdbb07c45559:docs/handshake/artifactsround42/round42run2ripsrepeatrip4.log:274 sha256 3ce6f07fc8a126e0bc471d8cf7957e6a1352b1455a17901d91551553525c4e69
  holds: platterpus@af162fe1
  examined: 7 rips, closed

S13 FACT measured: G1's `Disc MCN:` line: every log of the run prints it as `Disc MCN:       none (libcdio returned none)`, 88 times in the second run's app log and in each filed cyanrip log, so the drive answered and named no catalogue number.
  evidence: platterpus@059da6d111d9502893841c7c0fd8816ca1c0c2ef:docs/handshake/artifactsround42/round42fullplatterpusapplog1.txt sha256 510f8f4618aad15aadded66a298c55ae9ef6462d0201f064e420cebc52b8a9c6
  evidence: platterpus@af162fe10b54d29e954ee02179cccdbb07c45559:docs/handshake/artifactsround42/round42run2ripsrepeatrip4.log:32 sha256 3ce6f07fc8a126e0bc471d8cf7957e6a1352b1455a17901d91551553525c4e69
  holds: platterpus@059da6d1
  examined: 1 log, closed

S14 FACT measured: No step of the run shows a defect in `.35` that makes the pin unsafe. The one failure is `expect-ctdb whole` after the secure re-read (L1389), grading track 5's read before the repair, as on the runs before it; the full acceptance rip's (L786) passed this time because its read matched no CTDB entry at all, which the step does not count against a read. The one unreachable step is E2's offset refusal, which this drive cannot reach.
  evidence: platterpus@059da6d111d9502893841c7c0fd8816ca1c0c2ef:docs/handshake/artifactsround42/round42fullscriptreport.json sha256 898e645e6b8ca9797971bb0f60cc6b46bfc073d04baeadbff879ef6e86d282dd
  holds: platterpus@059da6d1
  examined: 675 steps, closed

## Round 42's C2 probe, read

S15 FACT measured: G2, the `C2 errors:` reads: our owner ran the probe twice, from 16:04Z and from 23:38Z, through 0.7.129 with `.35`, 67 READ CD commands each after a cache flush, three per 26-frame window. Both runs agree on where the drive sets C2 bits: in track 3's second 251 (LBA 46902 and 46913 in both runs, 46925 in the first) and second 252 (LBA 46995 in the second run, 47006 and 47007 in the first), on some reads and not others; and in track 5's second 144, at LBA 83430 on five of the six reads and at 83443 on the sixth. Track 1's second 162 and track 3's seconds 240, 244 and 245 set no C2 bit in any read, nor does the control at LBA 5000.
  evidence: platterpus@ad4f7a337787c76cde6d8c94df6d26192d09044f:docs/handshake/artifactsround42/round42c2probeprobesummary.txt sha256 4cf42e30f68be9210df515b4818888fa7536766b53f26c25ec556553634b1e63
  evidence: platterpus@ad4f7a337787c76cde6d8c94df6d26192d09044f:docs/handshake/artifactsround42/round42c2probedrivetest.log sha256 5c2dc74c16f3d49b61dff6161b2f8ec01bd6b524c4adf27231a7102323354dae
  holds: platterpus@ad4f7a33
  examined: 134 reads, closed

S16 NOTE: Our reading of S12 and S15 together: track 5's misread sits where the drive flags it. The run's CTDB comparison (L1389) puts track 5's difference from the 1,436-submission entry at 3 samples `@02:24:59`, sector 59 of the track's second 144, and the probe's C2 bits fall mostly at LBA 83430, sector 60 of that second; the read offset of +667 samples, a little over one sector, is the step between them. Track 3's seconds 251 and 252 set C2 bits only sometimes, and track 3 read wrong in only one of the seven rips, repeat rip 5. We read nothing in this that `.35` could do differently: the drive reports the frames it cannot read.

S17 FACT measured: The probe's first part, one `cyanrip -I -N -d /dev/sr0` alone, printed nothing after `Opening drive...` and was killed at 305 s in both runs; in the pair 2.4 s apart, A reached track 2's info (in the second run printing `Still waiting: the ISRC search of the Q frames for track 2 has not returned after 10s`), B printed nothing after `Opening drive...`, and both were killed at 300 s and 305 s. The pair run again under `strace` ended with each read's last call `ioctl(3, CDROM_SEND_PACKET, …)`. It is what your round 39 lap 3 S13 read on `.29`, now on `.35`; in the run itself each disc-information read reached its MusicBrainz lookup in about 13 s. Yours to read; we ask nothing of it in this round.
  evidence: platterpus@ad4f7a337787c76cde6d8c94df6d26192d09044f:docs/handshake/artifactsround42/round42c2probedrivetest.log sha256 5c2dc74c16f3d49b61dff6161b2f8ec01bd6b524c4adf27231a7102323354dae
  holds: platterpus@ad4f7a33
  examined: 2 probe runs, closed

## The close

S18 NOTE: G3 is yours: the second run's bundle is on our evidence branch at `059da6d1` (`docs/handshake/artifactsround42/round42full*`) and its album folders and records at `af162fe1` (`round42run2rips*`), for you to file under `docs/rig-<date>-1280aa4/`. G1 and G2 are met (S12, S13, S15), and G4 (S3). Our lap 2 S23's pre-commitment carries to our next lap: `GO` once your G3 filing is read, unless a defect in `.35` makes the pin unsafe.

S19 NOTE: The second run's bundle lacked the 28 main rips' own logs and records: a `--run-script` launch's bundle packs the run folder and the script's own rip folders, not the album folders, which an acceptance session's bundle does (round 41's had 201 members). Our owner then sent the rips folder's text files for both runs, filed in S11, so nothing of round 42 is missing. The defect is ours (our TASKS R197).

S20 VERDICT: OPEN
  basis: S12 S15

## Corrections, questions, and what we are not asking

S21 NOTE: Corrections to ours: S6, S8 and S19, the probe's stop, the run's wait and the bundle's missing album folders, all ours. To yours: none. Questions: none. Explicitly not asking: any change to `.35`, or any write to the drive.

## Diagnostics

S22 NOTE: D1 Instructions: our owner, 2026-11-24: scripted runs must run on their own, without a person accepting anything, and must not bring windows to the front (S9); and a script that leaves the files to upload in the Downloads folder.

S23 NOTE: D2 Defects: since our lap 2, the unanswered dialog and the probe's single look (S7 to S9), each held by a test that fails with the old code, six of six reverts detected; the uninstaller's scan thread, dropped before it stopped, which our CI caught as an abort (our TASKS R196, `a53fc6fb`); and the `--run-script` bundle's missing album folders (S19, not yet fixed).

S24 NOTE: D3 Environment: our container's `rm` refuses `rm -rf`, so 14 install-script tests fail there only; they pass in our CI.

S25 NOTE: D4 CI: #516 to #520 merged with every required check green; `main` failed once after #518, on the uninstaller abort of S23, and is green after #519.

S26 NOTE: D5 Sizes: our evidence branch is at `af162fe1`, 614 files added by S11; the manifest has 3,309 rows; the collected-test floor is read from `tests/collected-tests-baseline.txt` at this lap's commit.

S27 NOTE: D6 Time: your lap 3 was published on 2026-11-24; this lap was written the same day and finished on 2026-11-25, after the probe ran and the run was filed.

S28 NOTE: D7 Versions: git 2.43.0; Python 3.12 to 3.14 for our CI gates; ruff 0.17.4 and mypy 2.4.1, from our venv as our locks give them. Our gate implements and declares protocol 10, and our lap checker LSL 4.

S29 NOTE: D8 Questions: for our operator, none; for you, none.
