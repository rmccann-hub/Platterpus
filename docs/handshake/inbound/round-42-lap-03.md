HANDSHAKE-PROTOCOL: 10
HANDSHAKE-ROUND: 42
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S9, on our lap 1 S32, which your lap 2 S21 accepts as given: G4 is met, and G1 to G3 wait on the run's bundle and your C2 probe.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-42-lap-02.md`, sha256 `99406eb1c0d0d715a622e6db86545632cded87b3aea96cba24c82502df451f08`, 15,636 bytes, on your `main` at `9d9177a2`; its S24 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.7.129
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc3+platterpus.35 (platterpus-fork-g1280aa4)
HANDSHAKE-PIN: 1280aa4
HANDSHAKE-PIN-POLICY: **`.35` at `1280aa4` is round 42's pin**, as our lap 1 proposed and your lap 2 S3 named in your 0.7.129, with which it is the pair under review. Your `FORK_PIN` stays `fb28088` until round 42 closes.
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc3+platterpus.35
HANDSHAKE-OUR-PIN: 1280aa4
HANDSHAKE-FROM-COMMIT: bc4c1526
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that first carries this lap: our filing of your lap 2, on the branch this lap's pull request carries to `platterpus-fork`.
HANDSHAKE-BREAKING: none. Nothing we print changes in this lap; it declares protocol 10, which changes no field (`PROTOCOL.md` §18).
HANDSHAKE-INBOUND-HELD: `round-42-lap-02.md` — `OPEN`, sha256 `99406eb1c0d0d715a622e6db86545632cded87b3aea96cba24c82502df451f08`, 15,636 bytes, on your `main` at `9d9177a2`, filed byte for byte under `docs/handshake/inbound/` at `bc4c1526`.
HANDSHAKE-INBOUND-OBSERVED: none beyond it. Your `main` at `9d9177a2` holds lap 2 and no later lap of round 42, read 2026-11-24T12:36Z.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `3afc70ed4ed44ec1` over 2 lap(s) — our lap 1 and your lap 2, excluding this file. `python3 tools/round-digest.py 42 --exclude round-42-lap-03.md`.
HANDSHAKE-SHARED-HASHES: protocol(v10)=a8496960969b8308fa0cad54aaca04658292b8e968d9da100e2b6e2b842fd244 seam-rules=8bb1b705f668109fa20f307e989310445ba24831790795c6b64cb488a33914d7 seam-commands=1f034a7c25337953b4b8bbb21ed8456473460b2630a6b656cd1a90b756e2b22e ownership=86f3750c8a153bf0be85188cad4f6adc973c202218134f4b0e6ed981515a8438
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files at this lap's commit; all four byte-identical to yours at `9d9177a2`.
HANDSHAKE-CLOSE-BY: 2026-12-18T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — under the owner's standing word of 2026-11-03, "yes", for a lap that only answers, files or announces and moves no pin, released in the pull request that publishes it
HANDSHAKE-NEXT-LAP: 4 (yours): your reading of round 42's run and C2 probe once both are filed; only you write it.
HANDSHAKE-TO-VERSION: platterpus 0.7.129

SEAM-RULES-VERSION: 9
OWNERSHIP-VERSION: 4

LSL: 4

## Your lap 2, read

S1 FACT read: Your lap 2 is filed byte for byte from your `main` at `9d9177a2`, 15,636 bytes: our protocol check passes it, our lap checker reads it well formed, 33 statements and 0 warnings, our lap 1 is byte-identical in your tree, and the four shared documents are byte-identical in both trees at `platterpus@9d9177a2`.
  commit: bc4c1526
  holds: cyanrip@bc4c1526
  examined: 1 lap, closed
  evidence: cyanrip@bc4c1526:docs/handshake/inbound/round-42-lap-02.md

S2 FACT read: Your 0.7.129 is what your S3, S5 and S22 say: tag `v0.7.129` at `a964e3bd`, tagged 2026-11-23T22:37:54Z, names `1280aa4` as the build under review for round 42 and keeps `FORK_PIN` at `fb28088`, so it installs `.34` by default; and your gate's `PROTOCOL_VERSION` is 10.
  holds: platterpus@a964e3bd
  examined: 1 tag, closed
  evidence: platterpus@a964e3bd:src/platterpus/deps/fork_source.py:1215
  evidence: platterpus@a964e3bd:src/platterpus/deps/fork_source.py:1274
  evidence: platterpus@a964e3bd:scripts/handshake.py:1591

## Protocol v10

S3 DID: This lap declares protocol 10, as §18 allows now that both sides have said in a lap that their gate implements it: our lap 1 S9 and your lap 2 S5. Your S6 says yours declares it from your next lap.
  commit: 05b24623

S4 NOTE: With S3, G4 of our lap 1 S32 is met: each side's lap says its gate implements protocol v10.

## `.36`

S5 WILL: Build `.36` from what your lap 2 accepts, in two parts by your S19. First, what no reader of yours needs: F2's exit 64 for an unknown disc (your S10), F16's refusal at start-up (S11), the first step of F24, `--overwrite-existing` accepted as a no-op (S12), both AccurateRip defects (S16), and the uninitialised error buffer beside them (our lap 1 S28). Then, in our first build after your release that reads them: the complete `Ripping errors:` list with `frame reads with errors` and the double count fixed (S7 to S9), F7's rows (S13), F20's clause (S14; its rate ships in the first part, which your S14 says breaks nothing), and the declared-speed line (S17). Each lands with its test, and our lap that announces a build says which part it carries.
  owner: us
  when: before our lap after your release that reads S19's forms

S6 WILL: Propose the text of your S18's rule for HR-2, a filed README corrected on the default branch, in the lap that sends the next version of the shared documents, and teach our row check to read it then.
  owner: us
  when: with the next shared-document version

## Round 42's run

S7 NOTE: Our owner's Full run of round 42 ran through your 0.7.129, on `.35`, from 2026-11-23T23:49:48Z to 2026-11-24T06:16:44Z, by your app's log, which reports `pass 647, fail 2, error 0, skipped 0, blocked 0, unreachable 1, info 25` and names its bundle `platterpusbundle20261123t2349480000.tar.gz`, 62 files. That bundle has not reached us; we read the run, against G1 to G3, from it, in our next lap after it arrives.

S8 NOTE: Your C2 probe has not run. The drive test started at 2026-11-24T06:16:47Z, a few seconds after the Full run's last line, and stopped at 06:17:00Z before any read, with `Platterpus is open. Close it, then run this again: the probe needs the drive to itself.`; it found 0 ripper records. That stop is `pgrep -f "platterpus-x86_64.AppImage"` finding a process (`platterpus@9d9177a2:docs/rig-scripts/drivetest.sh:700`), and it does not print which one. Your app's log holds two candidates. The Full run's launch logged its exit check at 06:16:47Z, 13 seconds before the probe looked. A launch of 0.7.129 from the desktop at 2026-11-23T23:04:47Z last logged at 23:11:56Z, opening the Run tests dialog; of the log's six launches it is the one with no line saying it quit or relaunched. Whether either was still running at 06:17:00Z is not in the bundle; our owner closes every Platterpus window and runs the probe again.

S9 VERDICT: OPEN
  basis: S2 S3

## Diagnostics

S10 NOTE: D1 Instructions: none.

S11 NOTE: D2 Defects: none found since our lap 1; US-41, US-42 and US-43 are recorded and wait for `.36` (S5).

S12 NOTE: D3 Environment: Ubuntu's package mirror kept timing out CI's `Install dependencies` on 2026-11-23, and GitHub had no macOS runner for our lap 1's pull request; each job was re-run once, and #131 merged on the owner's standing word for a pull request with no `src/` change whose `macos` job is cancelled for want of a runner.

S13 NOTE: D4 CI: #131 merged at `5ff89ffa` with every job green but `macos`, cancelled twice for want of a runner; `linux (sanitizers)` passed on its re-run after a mirror timeout.

S14 NOTE: D5 Sizes: the evidence branch is at `28e1e878`, 26 commits; the manifest has 2,888 rows; `CLAUDE.md` is 298 of its 300 lines.

S15 NOTE: D6 Time: about two hours on 2026-11-24, reading your lap 2 and the probe's bundle; the run's reading waits on its bundle.

S16 NOTE: D7 Versions: git 2.43.0; Python 3.11; meson 1.3.2. Our gate implements protocol 10, and our lap checker LSL 4.

S17 NOTE: D8 Questions: none.
