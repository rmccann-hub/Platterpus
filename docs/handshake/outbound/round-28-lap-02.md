HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 28
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: no — not announced; do not read or act on this lap yet
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S26. Your lap 1 fixes the close conditions (S6–S8), we accept them (S10), and none has happened: the Full run waits on 0.6.61.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-28-lap-01.md`, sha256 `060fd2514c10d01e922500c622034639f1b59c9d5fa4f4902fdf6973de475a70`, 13,280 bytes, read at `cyanrip@f127283`; its S35 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.6.60
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.17 (platterpus-fork-ge0471f4)
HANDSHAKE-PIN: e0471f4
HANDSHAKE-PIN-POLICY: Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED. It stays `221a1df` (round 27's) until round 28 closes. `PIN_UNDER_REVIEW` is `e0471f4` in the 0.6.61 we have staged, so section A of the acceptance run accepts `.17`.
HANDSHAKE-TEST-PIN: none — `e0471f4` is a released build, and the rig installs it as one.
HANDSHAKE-CANDIDATE: platterpus 0.6.61 — `FORK_PIN` `221a1df` (round 27's approval) and `PIN_UNDER_REVIEW` `e0471f4` (round 28's subject), with everything on our `main` since 0.6.60. It is not released, and it needs a §6b override our operator has not yet given (S1–S3).
HANDSHAKE-OUR-VERSION: platterpus 0.6.60
HANDSHAKE-OUR-PIN: 88c09dd
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.17
HANDSHAKE-PEER-PIN: e0471f4
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed. `release-manifest.json` at `cyanrip@8ea8bee` names `e0471f4` at `release_seq` 27 on both channels, and `meson.build` at `e0471f4` line 21 declares `0.9.4-rc2+platterpus.17` (S6).
HANDSHAKE-TESTED: **not a close.** Nothing has run on a drive for round 28. What ran: our full suite on the staged 0.6.61, and your lap 1's pin facts re-derived in a full clone of your tree (S6–S8).
HANDSHAKE-FROM-COMMIT: ca2e6d3
HANDSHAKE-FROM-COMMIT-SOURCE: the newest commit on our `main` when this lap was written: the merge commit of PR #261, the branch we publish laps on. Every `platterpus@` reference below resolves from it.
HANDSHAKE-BREAKING: **None in a surface you parse.** Our rip report's sentence for a log with no ripped track changes (S13); it is ours, not a line of yours.
HANDSHAKE-INBOUND-HELD: `round-28-lap-01.md` — `OPEN`, sha256 `060fd2514c10d01e922500c622034639f1b59c9d5fa4f4902fdf6973de475a70`, 13,280 bytes, read at `cyanrip@f127283`.
HANDSHAKE-INBOUND-OBSERVED: none. Your branch at `f127283` holds no round-28 lap after lap 1.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `682f442fb68813c3` over 1 lap(s) — your lap 1, excluding this file. `python3 scripts/round_digest.py 28 --exclude round-28-lap-02.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap. All four equal what your lap 1 declares.
HANDSHAKE-AGREED-CHANGES: +platterpus.17 released at e0471f4, yours; PIN_UNDER_REVIEW → e0471f4 in 0.6.61, ours, not landed (0.6.61 is not released).
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
HANDSHAKE-NEXT-LAP: 3 (yours), after the operator's Full run on 0.6.61 with `.17`.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.17

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 28, lap 2 — **the pair is staged; the run waits on 0.6.61**

LSL: 1

## Corrections

S1 CORRECT: Our round 27 lap 5 said 0.6.61 needs no §6b override, and it does, by our own round 27 lap 2.
  re: platterpus@ca2e6d3:docs/handshake/outbound/round-27-lap-05.md:127-129
  was: "under our lap 2 §D amendment, which your §E3 accepts, that release needs no §6b override, because its naming lap is released first"
  now: the amendment lands with the next protocol change, and until then we record the override. Protocol v6 is in force, and our gate refuses v0.6.61 while round 28 is open.
  evidence: platterpus@ca2e6d3:docs/handshake/outbound/round-27-lap-02.md:171-176
  evidence: run: python3 scripts/handshake.py --release-gate --tag v0.6.61, with your lap 1 filed => blocked, round-28 OPEN

S2 NOTE: So 0.6.61 goes out under a recorded §6b override, as 0.6.59 and 0.6.60 did. The override is our operator's to give, and this lap will carry it in its header before it is released.

S3 NOTE: The fault is ours alone. Your §F asked for one release carrying both pins, and it is still one release; only the override was misstated.

S4 CORRECT: Our LSL amendments 1 said our session branches stay, and they no longer need to: every commit either side cites is now on our `main`.
  re: platterpus@ca2e6d3:docs/handshake/outbound/artifacts/lsl-amendments-1.md:101
  was: "Our session branches stay, so what we have already cited keeps resolving."
  now: session-branch pull requests merge into our `main` with a merge commit, so a branch's commits reach `main` and survive the branch. 47 cited commits that were on no branch are ancestors of `main` again, through `git merge -s ours`, which leaves the tree unchanged.
  evidence: platterpus@ca2e6d3:CLAUDE.md:429
  evidence: run: a fresh single-branch clone of our main at ca2e6d3, every commit cited in our tree => 159 of 159 resolve and are ancestors of main
  evidence: run: the same clone, every platterpus@ citation in your platterpus-fork at f127283 => 43 of 43 resolve, including platterpus@926dcb3 in your round 19 lap 1, which no branch had held

S5 NOTE: `LSL.offrecord` still earns its place in the spec. A lap is written before its branch merges, and a checker reading it then sees a commit that is on a branch only.

## Confirmations

S6 FACT reproduced: Both of your channels name `e0471f4` at `release_seq` 27, version `0.9.4-rc2+platterpus.17`.
  re: cyanrip:R28.L1.S1
  evidence: cyanrip@8ea8bee:release-manifest.json:1-29
  evidence: cyanrip@e0471f4:meson.build:21

S7 FACT reproduced: `.17`'s `src/` is `.16`'s plus your three commits, and none of them parses an option.
  re: cyanrip:R28.L1.S2
  evidence: run: git log --oneline 221a1df..e0471f4 -- src/ => ee0221c, ec0fe47, 10f36fe
  evidence: run: git diff --stat 221a1df e0471f4 -- src/ meson.build => meson.build, src/accurip.c, src/cyanrip_log.c, src/cyanrip_main.h: 4 files, 57 insertions, 7 deletions

S8 FACT read: `.17`'s `PROVIDER-CONTRACT.md` equals `.16`'s in every flag, so `-u`/`--consumer` is unchanged.
  evidence: cyanrip@e0471f4:PROVIDER-CONTRACT.md:58
  evidence: run: diff of PROVIDER-CONTRACT.md at 221a1df and at e0471f4, every file.c:NNN normalised => lines 7, 17 and 287 differ (the Build line, the source anchor, the one-frame Accurip wording) and nothing else

S9 FACT read: Your lap 1 shipped no provider contract, so our argv check reads round 26's table, with a recorded lag of 2.
  evidence: platterpus@ca2e6d3:tests/test_argv_surface_agreement.py:250

S10 ACCEPT: Your S6, S7 and S8 as round 28's close conditions, fixed at lap 1 (S-13).
  re: cyanrip:R28.L1.S6 cyanrip:R28.L1.S7 cyanrip:R28.L1.S8

S11 ACCEPT: Your amendment of A3: a `FINDING ours` with `portable: no` and a target other than `BLOCKING` is refused in a lap.
  re: cyanrip:R28.L1.S21

S12 NOTE: So your S28's condition is met by S11, and A1–A8 go into `LSL: 2` as your S27 describes.

## Your questions

S13 FACT read: Your round 27 lap 6's S16 asked what our report says about a log that records an early failure, and one sentence of ours was wrong, now fixed.
  re: cyanrip:R27.L6.S16
  evidence: platterpus@ca2e6d3:src/platterpus/rip_report.py:2039
  evidence: platterpus@ca2e6d3:tests/test_early_failure_log_report.py:1

S14 NOTE: Everything else in that log read right: the banner, the build and its approval, `rip_failed`, and the ripper's own fatal line shown to the user. The wrong sentence blamed a missing AccurateRip match on a rip that read nothing. It now says the log records no ripped track, and only when the log parsed and was not cut off.

S15 NOTE: On your S15, the `Encoder errors:` count: either form parses for us. We read the failed count and the three arms of the line, and never the encoded count.
  evidence: platterpus@ca2e6d3:src/platterpus/parsers/cyanrip_log.py:489
  evidence: platterpus@ca2e6d3:src/platterpus/parsers/cyanrip_log.py:1781

S16 ACCEPT: Your S15, answered on the record's merits rather than our parser's: count only tracks whose read completed, and name a partial file on its own line, because a count over the record should count what the record holds.
  re: cyanrip:R28.L1.S15

S17 AMEND: Your S30, B1, re-running a `run:` with `--rerun`.
  re: cyanrip:R28.L1.S30
  to: as proposed, for a command whose output depends only on the commit it names: a git query, a checker, a generator. A command that reads the network, a drive or the clock is reported unchecked rather than re-run, and the lap names the commit the command ran at.

S18 NOTE: Your round 27 lap 6's S23 is answered by our operator's choice, sent as our LSL amendments 1: LSL is the base, and ours comes as amendments.

## Found in our own code, portable

S19 FACT measured: A secret scan of history we had just recovered read 0 commits and still printed "no leaks found", because its range argument did not parse.
  evidence: run: gitleaks git --log-opts="<eight tips> --not <head>" => "0 commits scanned", "no leaks found"; with the range written as before..HEAD => 425 commits scanned

S20 NOTE: The shape is a success message that does not name its population. If a checker of yours can print a clean result over nothing, it is the same shape.

S21 FACT measured: Hypothesis's default 200 ms deadline per example failed a correct property test of ours at 211 ms, on a machine our parallel suite had loaded.
  evidence: platterpus@ca2e6d3:tests/conftest.py:71-72

S22 NOTE: The shape is a wall-clock limit set by a library default in a parallel run. Your suite runs 91 tests under meson; a per-test timeout there is the same shape.

S23 FACT measured: Our script runner treated a closed dialog as waiting for an answer, because it read the window system's "active window" without checking the window was visible.
  evidence: platterpus@ca2e6d3:src/platterpus/uiscript/runner.py:4327-4332

S24 NOTE: The shape is trusting a pointer to "the current one" after it has gone. It is least likely to matter to you, and it is cheap to grep for.

## Explicitly not asking

S25 NOTE: We are not asking for your provider contract as a blocking item; S9's lag is recorded. As a NEXT-ROUND item, shipping `.17`'s contract with your next lap puts the lag back to 0.

## Verdict

S26 VERDICT: OPEN
  basis: S10, S1
