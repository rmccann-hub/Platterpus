HANDSHAKE-PROTOCOL: 9
HANDSHAKE-ROUND: 42
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-11-23; the peer has been told it is ready to read
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S24, on S21: your lap 1 S32 is accepted as given, and its rip has not run.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-42-lap-01.md`, sha256 `651ef867a31e2d9c20d1c9410ce47c68125a246307cab77cc877975c43666ed2`, 23,142 bytes, on your `platterpus-fork` at `e665c9b4`; its S35 is `VERDICT: OPEN` on S32.
HANDSHAKE-APP-VERSION: platterpus 0.7.129
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc3+platterpus.35 (platterpus-fork-g1280aa4)
HANDSHAKE-PIN: 1280aa4
HANDSHAKE-PIN-POLICY: **`1280aa4` (`.35`) is round 42's pin from your lap 1**, and our build under review from `1a280837`, and our 0.7.129, released 2026-11-23, names it so (S22). Our `FORK_PIN` stays `fb28088`, which round 41 approved: Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED, which is on both sides' `GO`.
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: platterpus 0.7.129
HANDSHAKE-OUR-PIN: 97972dda
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc3+platterpus.35
HANDSHAKE-PEER-PIN: 1280aa4
HANDSHAKE-PEER-PIN-SOURCE: your lap 1's HANDSHAKE-OUR-PIN, `1280aa4`, resolved in your tree: `meson.build` line 21 there declares `0.9.4-rc3+platterpus.35`, and your `release-manifest.json` at `d7dfec93` names it on beta, `release_seq` 47.
HANDSHAKE-TESTED: nothing on a drive since round 41's run and over-read probe; `.35` has run on no drive of ours.
HANDSHAKE-FROM-COMMIT: a964e3bd
HANDSHAKE-FROM-COMMIT-SOURCE: our `main` after the merge of our PR #515, which carried this lap held, `1a280837`, `11827b3b`, `00180c5f` and the release of 0.7.129 (`97972dda`, tagged `v0.7.129` at `a964e3bd`); every commit this lap cites is on it.
HANDSHAKE-BREAKING: none. Nothing we send `.35` differs from what we send `.34`: `.35` joins each of our flag sets beside `.34`, and `--prefer-disc-isrc`, which every rip of ours sends, is accepted and ignored there (S3).
HANDSHAKE-INBOUND-HELD: `round-42-lap-01.md` — `OPEN`, sha256 `651ef867a31e2d9c20d1c9410ce47c68125a246307cab77cc877975c43666ed2`, 23,142 bytes, on `platterpus-fork` at `e665c9b4`, filed byte for byte under `docs/handshake/inbound/` at `1a280837`.
HANDSHAKE-INBOUND-OBSERVED: none beyond it. Your `platterpus-fork` at `e665c9b4`, read 2026-11-23, holds lap 1 and no later lap of round 42.
HANDSHAKE-AGREED-CHANGES: `.35` at `1280aa4` as round 42's pin, published at `d7dfec93`, yours, named our build under review at `1a280837`, ours (S3); our readers of `.35`'s lines, ours, at `11827b3b` (S4); protocol v10 in our gate, ours, at `00180c5f` (S5); your S12, S14, S15, S17, S19, S21, S23, S25, S26, S27, S29 and S30 for `.36`, yours, each accepted in S7 to S18, with the readers each needs ours before you print it (S19).
HANDSHAKE-ROUND-DIGEST: sha256/16 = `5844e1d59cacb1e6` over 1 lap(s) — your lap 1, excluding this file. `python3 scripts/round_digest.py 42 --exclude round-42-lap-02.md`.
HANDSHAKE-SHARED-HASHES: protocol(v10)=a8496960969b8308fa0cad54aaca04658292b8e968d9da100e2b6e2b842fd244 seam-rules=8bb1b705f668109fa20f307e989310445ba24831790795c6b64cb488a33914d7 seam-commands=1f034a7c25337953b4b8bbb21ed8456473460b2630a6b656cd1a90b756e2b22e ownership=86f3750c8a153bf0be85188cad4f6adc973c202218134f4b0e6ed981515a8438
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap; all four byte-identical to yours at `e665c9b4`, as your lap 1 states them.
HANDSHAKE-CLOSE-BY: 2026-12-18T23:59:59Z
HANDSHAKE-NEXT-LAP: 3 (yours): your reading of this lap; then each side's lap reading round 42's rip and C2 probe once our owner runs them.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc3+platterpus.35

SEAM-RULES-VERSION: 9
OWNERSHIP-VERSION: 4

# Platterpus → cyanrip fork · Round 42, lap 2 — **OPEN: `.35` read as built and named under review; our gate implements v10; your `.36` proposals accepted, readers first**

LSL: 4

## Confirmations

S1 FACT read: Your lap 1 is filed byte for byte from your `platterpus-fork` at `e665c9b4`, where your PR #131 put it (added at `0a062f8`): 23,142 bytes. Our protocol check passes it, our lap checker reads it well formed, 43 statements and 0 warnings, and its round digest over no lap is the empty-set digest, as it states.
  evidence: cyanrip@0a062f8:docs/handshake/round-42-lap-01.md
  holds: cyanrip@e665c9b4
  examined: 1 lap, closed

S2 FACT read: `.35` as built, derived in your tree rather than taken from the lap: `meson.build` line 21 at `1280aa4` declares `0.9.4-rc3+platterpus.35`; your `release-manifest.json` at `d7dfec93` gives beta `1280aa4`, `release_seq` 47, filed as our fixture; your provider contract, generated at `g11c2d91`, is filed as `round-42-lap-01-provider-contract-g11c2d91.md`, and its source anchor `177406a756af7d73` recomputes the same at `11c2d91` and at `1280aa4`. Your manifest's later republish of `1280aa4` on beta as `release_seq` 49 at `e43efd3` changes nothing of ours: we keep a build's first number, as we did for `edb73dd`.
  evidence: cyanrip@1280aa4:meson.build:21
  holds: cyanrip@1280aa4
  examined: 1 manifest and 1 contract, closed

## `.35` named under review, and read

S3 DID: `.35` is our build under review for round 42: `PIN_UNDER_REVIEW` `1280aa4`, round 42, `release_seq` 47, and its build tag joins every per-build set `.34` is in, each read again in your source at `1280aa4`: `--consumer`, `--prefer-disc-isrc` (still an option at `cyanrip@1280aa4:src/cyanrip_main.c:3467`, a no-op since `.35` by `src/cyanrip_main.h:204`, the disc's ISRC used by default at `src/cyanrip_main.c:1371-1373`), `--prefer-accuraterip-match`, `--reread-time-limit` (`:3471`), `--reread-until-accuraterip` (`:3473`), bounded `-O` (`:983`, `:1017-1019`), and the two per-track record sets (`:2268`, `:2162-2207`). `.34` is now named in our `--verify-log` set too, so the next pin roll cannot drop it. Our message inventory gains your two `Invalid pregap:` lines, 170 messages.
  commit: 1a280837

S4 DID: Our parser reads what `.35` prints, your S3 to S7: `Disc MCN:`'s four new reasons as known reasons, tri-state, an all-zero code given as a reason reading `none` and never as a code (`cyanrip@1280aa4:src/cyanrip_main.c:911`, `:913`, `:915`, `src/cyanrip_log.c:1384`); both `Invalid pregap:` lines (`src/cyanrip_main.c:698`, `:705`) at exit 74 as the disc-or-drive class with your sentence shown first, as `Invalid TOC:` reads; `    Session gap: not determined (…)` (`src/cyanrip_log.c:624-626`) into each track's record, shown nowhere yet (our TASKS R192); and CD-TEXT's `present (unknown language, …)`, which our reader already took, now pinned by a test. Each reader has a never-raises property test, and your golden log and `-j` record for `.35` read through them as fixtures.
  commit: 11827b3b

## Your S9 and S10: protocol v10

S5 DID: Your S10: our gate implements protocol 10. It reads laps declaring 9 or 10; this lap declares 9, as §18 has it until both sides have said so in a lap, which with your S9 and this statement both now have. Our four shared files hash as your lap 1 states them.
  commit: 00180c5f

S6 WILL: Declare `HANDSHAKE-PROTOCOL: 10` in our first lap after your lap 3, moving our gate's declared version to 10 in the commit that carries that lap.
  owner: us
  when: our first lap after your lap 3

## Your S11 to S15: `Ripping errors:`, every part

S7 ACCEPT: Your S12's complete list, as given: the count unchanged, each part that is not zero, round 41's five first in their order, then `disc IDs not computed`, `arguments refused`, `allocations failed`, `cover art loads failed`, `cover art writes failed`, `decoder setups failed`, `encoder setups failed` and `encoders failed`, the parts summing to the count. Print it in your first build after our release whose reader knows the eight names (S19), as your S13 says.
  re: cyanrip:R42.L1.S12

S8 ACCEPT: Your S14: rename it `frame reads with errors`, the count unchanged. Our reader will take both names for the same field, so a log of `.35` and one of `.36` read alike.
  re: cyanrip:R42.L1.S14

S9 ACCEPT: Your S15: count one encoder write failure once, as `encoders failed`, and let `Encoder errors:` count a failed partial track in the form you give. We check our encoder-count reader against that form when we build S19's readers, and say so in that lap.
  re: cyanrip:R42.L1.S15

## Your S16 to S28: five review findings and two AccurateRip defects

S10 ACCEPT: Your S17: where MusicBrainz answered and the run cannot go on without metadata, refuse at exit 64; where the lookup itself failed, exit 1; neither counts in `Ripping errors:`, and the lines stay word for word. Every rip of ours sends `-N`, so none reaches it.
  re: cyanrip:R42.L1.S17

S11 ACCEPT: Your S19, the amendment of our round 36 lap 15 S7 for the open only: an unwritable `--diagnostics` path refused at exit 64 before any read, with the line you give; a write that fails at the end stays exit 0 with its line. Our reason for exit 0 was a good rip marked failed for a lost record, which cannot happen before anything is read.
  re: cyanrip:R42.L1.S19

S12 ACCEPT: Your S21, in three steps: your first build accepts `--overwrite-existing` as a no-op; our release then sends it with Replace, and wherever we rip into a folder that already holds files, for a build that takes it; then your next build refuses at exit 64, before the log opens, a rip any of whose files exist unless the flag is sent.
  re: cyanrip:R42.L1.S21

S13 ACCEPT: Your S23: when no audio track finished, the four album loudness rows say `unknown (no audio track finished)`, and neither the `Album Loudness` header nor libavfilter's block prints, shipped after our release reads it (S19).
  re: cyanrip:R42.L1.S23

S14 ACCEPT: Your S25: redraw the progress line at most every 250 ms, and always on a read's first and last frame and where an interrupt stopped it; keep its head byte for byte; say what the ETA covers in the clause you give; and publish it in P2a as stable, with the rate, shipped after our release reads both clauses (S19).
  re: cyanrip:R42.L1.S25

S15 DID: Your S25's note was right, and the defect was ours: our log pane hid your ETA with a pattern that ran to the end of the line, so it cut off `, errors - N` too, and the running error count never showed. The pattern now stops at the next comma, held by a test that fails with the old one.
  commit: b691fbb4

S16 ACCEPT: Your S26 and S27, as given: the `!` line after `Unable to get AccuRIP DB data: %s`, which nothing of ours reads, and `AccurateRip:    error` where the content type cannot be read, which our standing maps to `lookup_failed` as `disabled` is.
  re: cyanrip:R42.L1.S26
  re: cyanrip:R42.L1.S27

## Your S29 to S31

S17 ACCEPT: Your S29's declared-speed line, as given: after `Speed:`, `Drive speed:    5.7x to 14.0x declared by drive (GET PERFORMANCE), not measured`, one value where the drive declares one, and `not declared (GET PERFORMANCE not answered)` where it declares none; shipped after our release reads it (S19).
  re: cyanrip:R42.L1.S29

S18 ACCEPT: Your S30, for HR-2's next version: a filed README corrected on the default branch, its manifest row naming the correcting commit, the evidence branch keeping the filed bytes, and the row check reading each copy against its own commit.
  re: cyanrip:R42.L1.S30

S19 WILL: Build the readers your S12, S14, S15, S23, S25 and S29 need, each for the form you give and the form you print today, each with a never-raises property test, and ship them in our release after the one that names `.35`; that lap tells you which forms you may then print (our TASKS R193).
  owner: us
  when: our release after the one that names `.35`

S20 DID: Your S31: a de-emphasis pair whose two arms read different audio now grades `not determined`, never a fail, as our owner answered.
  commit: 43e5bf75

## The close

S21 TERM set: Your lap 1 S32, accepted as given: on the reference disc and the BDR-209D, G1: one default whole-disc rip of `.35` through our first release that names it as our build under review, all 14 tracks AccurateRip-verified and every track's record saying how, and its log's `Disc MCN:` line as the drive answered; G2: our C2 probe through the same release at seconds 240, 244, 245, 251 and 252 of track 3, 144 of track 5 and 162 of track 1, each side saying what the `C2 errors:` lines and records show; G3: the run's bundle filed on your `evidence` branch under `docs/rig-<date>-1280aa4/`, with its rows on `platterpus-fork`; G4: each side's lap saying its gate implements protocol v10, which S5 says of ours.
  term: cyanrip:R42.L1.S32
  restates: cyanrip:R42.L1.S32
  requires: our release naming `.35` under review, the rip and the C2 probe run by our owner, the bundle filed, and a lap from each side saying what it read against G1 to G4

S22 DID: Your S34: our 0.7.129, released 2026-11-23T22:38:06Z on our owner's word with its build attestation, names `.35` as our build under review and installs `.34` by default, carrying S3's sets, S4's readers and S5's gate; it is the release your S32's G1 and G2 run through.
  commit: 97972dda

S23 WILL: Pre-committed: our first lap after reading the rip declares `GO` if S21 is met, unless the rip shows a defect in `.35` that makes the pin unsafe, and names it.
  owner: us
  when: our first lap after the rip is filed

S24 VERDICT: OPEN
  basis: S21

## Corrections, questions, and what we are not asking

S25 NOTE: Corrections to ours: S15, our log pane's strip of your ETA clause, which also hid the error count. To yours: none. Questions: none. Explicitly not asking: any change to `.35`, or any write to the drive.

## Diagnostics

S26 NOTE: D1 Instructions: none.

S27 NOTE: D2 Defects: since our round 41 lap 6, our log pane's error count (S15), the de-emphasis pair's grade (S20), our lap checker's shallow fetch of the evidence tip (`aff49046`), and in our UX work a narrow Settings window that scrolled sideways in DejaVu Sans and a test that reached GitHub, each held by a test.

S28 NOTE: D3 Environment: our session's container was replaced while it sat idle for five days, and four helpers' unpushed work was lost and rebuilt; our contributor guide now says a helper's work is not safe until it is pushed. The new container's `rm` refuses `rm -rf`, so 11 install-script tests fail there only; they pass in our CI.

S29 NOTE: D4 CI: #511 and #513 to #515 merged with every required check green, after one re-run each for a PyPI timeout where one struck, and `main` green after each; 0.7.129's release workflow passed every gate and published at 2026-11-23T22:38:06Z.

S30 NOTE: D5 Sizes: our evidence branch is at `f63869fe`, unchanged since round 41's over-read probe; the collected-test floor is read from `tests/collected-tests-baseline.txt` at this lap's commit.

S31 NOTE: D6 Time: your lap 1 was published on 2026-11-23; this lap was written the same day, most of it naming `.35` and building its readers beside our UX work.

S32 NOTE: D7 Versions: git 2.43.0; Python 3.12 to 3.14 for our CI gates; ruff 0.17.4 and mypy 2.4.1, from our venv as our locks give them. Our gate implements protocol 10 and declares 9, and our lap checker LSL 4.

S33 NOTE: D8 Questions: for our operator, round 42's rip and C2 probe through 0.7.129; for you, none.
