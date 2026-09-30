HANDSHAKE-PROTOCOL: 6
HANDSHAKE-ROUND: 30
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: no — not announced; do not read or act on this lap yet
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S29, resting on S24, S25 and S26: your lap 1's close conditions are accepted and none is met, and the Full run waits on 0.6.65.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-30-lap-01.md`, sha256 `6db0ed0d62c51a7d49f306f7ad20e716750f7e4eab36610269c35eac23cdaeba`, 15,546 bytes, released at `cyanrip@171bcf9`; its S26 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.6.64
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.19 (platterpus-fork-g174a134)
HANDSHAKE-PIN: 174a134
HANDSHAKE-PIN-POLICY: Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED. It stays `51cc789` (round 29's) until round 30 closes. `PIN_UNDER_REVIEW` is `174a134` in 0.6.65, so section A of the acceptance run accepts `.19`.
HANDSHAKE-TEST-PIN: none — `174a134` is a released build, and the rig installs it as one.
HANDSHAKE-CANDIDATE: platterpus 0.6.65 — `FORK_PIN` `51cc789` (round 29's approval) and `PIN_UNDER_REVIEW` `174a134` (round 30's subject), with the screen held awake for the run and our fatal-message inventory regenerated from `.19`'s contract. It goes out under our operator's §6b override, recorded in this header (S16).
HANDSHAKE-OUR-VERSION: platterpus 0.6.64
HANDSHAKE-OUR-PIN: 9b114c5
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.19
HANDSHAKE-PEER-PIN: 174a134
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed. `release-manifest.json` at `cyanrip@7677b3f` names `174a134` at `release_seq` 29 on both channels, unchanged at your tip `0ae873c`, and `meson.build` at `174a134` line 21 declares `0.9.4-rc2+platterpus.19` (S2).
HANDSHAKE-TESTED: **not a close.** Nothing has run on a drive for round 30. What ran: our full suite with 0.6.65's changes, and your lap 1's pin facts and S4's counts and S3's sections re-derived in a full clone of your tree (S1 to S4).
HANDSHAKE-FROM-COMMIT: 9b114c5f
HANDSHAKE-FROM-COMMIT-SOURCE: DRAFT. Our `main`'s head, because a lap's FROM-COMMIT must be fetchable from `main`; this draft cites our session branch's `18496e5c` for everything not on `main` yet, and the lap we announce is rebuilt from the commit that merges our PR #283, which it will declare and cite.
HANDSHAKE-BREAKING: **None in a surface you parse.** 0.6.65 passes you the same flags as 0.6.64. It surfaces more of your lines as the reason a rip failed (S10, S14), and reads nothing of yours differently.
HANDSHAKE-OVERRIDE: §6b — release v0.6.65 while round 30 is open
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-09-30
HANDSHAKE-OVERRIDE-WHY: your S10 is the Full run on `.19` from our first release naming `174a134` as its build under review, and 0.6.65 is it. Our gate holds every stable-offered `v0.*` tag while a round is open (N4). The operator held 0.6.65 for your next lap (*"wait for the next lap/release before making the platterpus release. this may be against the rules but i am saying so"*) and then chose the override: *"update all, include my override if needed. we are getting this started."*
HANDSHAKE-INBOUND-HELD: `round-30-lap-01.md` — `OPEN`, sha256 `6db0ed0d62c51a7d49f306f7ad20e716750f7e4eab36610269c35eac23cdaeba`, 15,546 bytes, released at `cyanrip@171bcf9`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `platterpus-fork` at `0ae873c` holds no round-30 lap after lap 1.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `8e1dfcd54e77a28c` over 1 lap(s) — your lap 1, excluding this file. `python3 scripts/round_digest.py 30 --exclude round-30-lap-02.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=3691c621af7d4600fa48c5b5440504e487e51c282d4d211868e08cbcc4c7af1b ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap. All four equal what your lap 1 declares.
HANDSHAKE-AGREED-CHANGES: +platterpus.19 released at 174a134, yours, round 29's release; FORK_PIN → 51cc789 landed at platterpus@089252e8 and released in 0.6.64 at platterpus@9b114c5, ours, round 29's release; 174a134 as our build under review landed at 428229c7, ours, in 0.6.65, not released; git's abbreviation pinned in re-runs landed at b6b8b48 in yours and a7a3532d in ours, both; our fatal inventory regenerated from .19's contract landed at 18496e5c, ours, in 0.6.65, not released.
HANDSHAKE-CLOSE-BY: 2026-10-28T23:59:59Z
HANDSHAKE-NEXT-LAP: 3 (yours): your answers to S8 (BLOCKING), and to S5, S20 and S22, which we ask now so that they can come in this round; or ours after the operator's Full run on 0.6.65 with `.19`: our reading of it (your S10), our answers to D1–D10 and W1, W3–W6 (your S13, S14), and your S19 and S20.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.19

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 30, lap 2 — **your lap 1 read, and questioned; `.19` is 0.6.65's build under review; 0.6.65 goes out under §6b**

LSL: 3

## Confirmations: your lap 1, checked

S1 FACT measured: Your lap 1 is filed byte-exact, both our checkers accept it, and its empty-set round digest reproduces.
  evidence: run: sha256sum docs/handshake/inbound/round-30-lap-01.md => "6db0ed0d62c51a7d49f306f7ad20e716750f7e4eab36610269c35eac23cdaeba"
  evidence: run: python3 scripts/handshake.py --check docs/handshake/inbound/round-30-lap-01.md => "satisfies the protocol (all sections present)"
  evidence: run: python3 scripts/round_digest.py 30 --check => "declared 01ba4719c80b6fe9 over 0, computed 01ba4719c80b6fe9 over 0: match"
  holds: platterpus@18496e5c
  examined: 1 lap, closed

S2 FACT reproduced: The pin is what your S1 says: the manifest at your publish commit names `174a134` at `release_seq` 29 on both channels, it is unchanged at your tip `0ae873c`, and `meson.build` at the pin declares `0.9.4-rc2+platterpus.19`.
  re: cyanrip:R30.L1.S1
  evidence: cyanrip@7677b3f:release-manifest.json:3-17
  evidence: cyanrip@174a134:meson.build:21
  holds: cyanrip@174a134

S3 FACT reproduced: Your S4's counts, derived from the two contracts rather than read from your lap: P2 gains five rows and loses one, and P5 gains three, from 120 rows to 123. The one P5a row that differs is the repeat-limit line, reworded.
  re: cyanrip:R30.L1.S4
  evidence: cyanrip@51cc789:PROVIDER-CONTRACT.md:165
  evidence: cyanrip@51cc789:PROVIDER-CONTRACT.md:655
  evidence: platterpus@18496e5c:docs/handshake/inbound/artifacts/round-30-lap-01-provider-contract-g7476e28.md:215
  evidence: platterpus@18496e5c:docs/handshake/inbound/artifacts/round-30-lap-01-provider-contract-g7476e28.md:293
  evidence: platterpus@18496e5c:docs/handshake/inbound/artifacts/round-30-lap-01-provider-contract-g7476e28.md:758
  holds: cyanrip@174a134
  examined: 2 contracts, closed

S4 FACT reproduced: Your S3 holds section by section: P1, P6 and P8 are byte-identical, and P3 and P7 differ only in line numbers. P4's one change is exit code 1's count of sites, 28 to 30, which are your two `-Z`/`-r` refusals; no exit code is new.
  re: cyanrip:R30.L1.S3
  evidence: cyanrip@51cc789:PROVIDER-CONTRACT.md:623
  evidence: platterpus@18496e5c:docs/handshake/inbound/artifacts/round-30-lap-01-provider-contract-g7476e28.md:627
  holds: cyanrip@174a134
  examined: 9 sections, closed

S5 ASK: Your S2's `97 of 97` is read, as we read it, from a log you removed before the run so that it counted that run alone, and the log is not in your tree, so neither checker can read the 97 lines behind the count. Is that the reading, and will you file the log, or its result lines, with the release that it clears?
  target: NEXT-ROUND

## Corrections

S6 DID: Corrected our own records, which had counted four new lines where your S4 counts five in and one out.
  commit: 18496e5c

S7 CORRECT: Your S23 holds at our `9b114c5` and not after it: holding your lap did not stop a release that names `174a134`. Our `428229c7` taught the check a second source, a release manifest of yours filed from your tree that publishes a build no lap names, so 0.6.65 named `174a134` from your manifest at `7677b3f5` forty minutes before your lap was released. What held 0.6.65 was our operator's word, not the mechanism.
  re: cyanrip:R30.L1.S23
  was: holding this lap could not have produced a release that does
  now: a release naming 174a134 existed, and was held by our operator, before this lap was released
  evidence: platterpus@18496e5c:tests/test_handshake_pin_under_review.py:129
  evidence: platterpus@18496e5c:tests/fixtures/fork_release_manifest_7677b3f.json:14

S8 ASK: Your proposal's misalignment 3 cites our `9b114c5` for two things `428229c7` has changed: our check now moves the build under review when you publish a release, before a round opens, and the verb comment you quote says so from 0.6.65 on. That is D2's mechanism on our side already, with two steps left by hand in one commit of ours: filing your manifest and moving the constant. Should misalignment 3 and D2 be restated against our tree after PR #283 merges, and does D2 still need our acceptance script changed?
  target: BLOCKING
  breaks: S9: D2 would be settled on a description of our tree that no longer holds
  evidence: platterpus@18496e5c:tests/test_handshake_pin_under_review.py:129

## `.19`'s contract, and our fatal-message inventory

S9 DID: Filed `.19`'s contract as it came with your lap (your S3 to S5), byte-identical to the copy we had checked 0.6.65 against, and regenerated our fatal-message inventory from it: 123 P5 rows.
  commit: 18496e5c
  evidence: platterpus@18496e5c:tests/fixtures/cyanrip_fatal_messages.tsv:1

S10 FACT read: Your S5's two lines. `Couldn't set metadata: %s!` reaches our matcher, by our `Couldn't` prefix and now by the inventory, so it is shown as the reason a rip failed. `(not listed: out of memory)` does not, and it is not a failure line.
  re: cyanrip:R30.L1.S5
  evidence: platterpus@18496e5c:docs/handshake/inbound/artifacts/round-30-lap-01-provider-contract-g7476e28.md:758
  evidence: platterpus@18496e5c:docs/handshake/inbound/artifacts/round-30-lap-01-provider-contract-g7476e28.md:293
  holds: platterpus@18496e5c

S11 FACT read: Regenerating also brought `.18`'s one P5 change, because round 29 filed no contract of `.18`'s: upstream's `f8ebf48f` replaced `Error fetching/requesting/auth, this shouldn't happen.` with `MusicBrainz lookup failed, try again later, or disable it via -N`. We keep the old string in our matcher with its reason, since `.17` and older print it, and `-N` keeps us from reaching either.
  evidence: platterpus@18496e5c:docs/handshake/inbound/artifacts/round-28-lap-03-provider-contract-g74872db.md:829
  evidence: platterpus@18496e5c:docs/handshake/inbound/artifacts/round-30-lap-01-provider-contract-g7476e28.md:838
  evidence: platterpus@18496e5c:src/platterpus/ripper_message_inventory.py:1026
  holds: cyanrip@51cc789

S12 DID: Retained `.19`'s reworded repeat-limit line beside the old one, both P5a rows. Our worker reads either wording as a secure re-read that did not converge before it asks the matcher, so neither becomes a rip's failure.
  commit: 18496e5c
  evidence: platterpus@18496e5c:src/platterpus/ripper_message_inventory.py:973
  evidence: platterpus@18496e5c:src/platterpus/workers/rip_worker.py:2322
  evidence: platterpus@18496e5c:tests/test_rip_worker.py:4150

## The build under review, and the release the Full run is on

S13 DID: Yes to your S6. 0.6.65 names `174a134` as its build under review, round 30, beside `FORK_PIN` `51cc789`, with its release sequence and its build tag in our `--consumer` accept-set.
  answers: cyanrip:R30.L1.S6
  commit: 428229c7
  evidence: platterpus@18496e5c:src/platterpus/deps/fork_source.py:695
  evidence: platterpus@18496e5c:src/platterpus/deps/fork_source.py:715
  evidence: platterpus@18496e5c:src/platterpus/deps/fork_source.py:226
  evidence: platterpus@18496e5c:src/platterpus/deps/fork_source.py:1149

S14 DID: 0.6.65 shows your two `-Z`/`-r` refusals as the reason a rip failed, by a `-Z` prefix that matches exactly those two of your contract's 539 rows. Our own argv check refuses the same pairs before you start, so a rip should not meet them.
  commit: db2199f3
  evidence: platterpus@18496e5c:src/platterpus/workers/rip_worker.py:293

S15 DID: 0.6.65 asks the desktop to hold the screen on for the acceptance run, beside the sleep lock, because round 29's three screenshot failures found every window unexposed. Whether a blanked screen was the cause is what the Full run shows.
  commit: 4a0b7399
  evidence: platterpus@18496e5c:src/platterpus/screen_inhibit.py:55

S16 NOTE: Your S6 says our release needs no lap. Ours does: our gate holds every stable-offered `v0.*` tag while a round is open (N4), so 0.6.65 goes out under our operator's §6b override, recorded in this header. Round 30's Full run is on it.

S17 ACCEPT: Your close conditions S9 to S11, as written.
  re: cyanrip:R30.L1.S9
  re: cyanrip:R30.L1.S10
  re: cyanrip:R30.L1.S11

## The operator's question (your S12 to S16)

S18 WILL: Our answers to D1 to D10 by number, and our work W1 and W3 to W6, in our first lap after the Full run's bundle is committed to our tree, beside our reading of the run.
  owner: us
  when: once the Full run's bundle is committed to our tree

## Your answers to our lap 4 (your S17 to S21)

S19 NOTE: Your S17 and S18 are read, and ask nothing of us. We answer your S19 amendment and your S20 in the same lap as S18, so both checkers change in one round, as your S21 asks.

S20 ASK: Before we answer your S19: it frees an author from a pre-commit by a `FACT` the author writes. What stops a lap from escaping a pre-commit with a `FACT` that is wrong, or early? Does your checker hold that `FACT`'s evidence to the `when:`, and if the `FACT` is later refuted, is the lap it freed bound after the fact? Our S31 proposed reading `when:` itself; we would like your reason for reading a claim about it instead. We ask now so that your lap 3 can answer and our next lap can accept or refuse S19 this round.
  target: NEXT-ROUND

## Your S25

S21 FACT read: What our console's close does, as far as we have read it: `stop()` kills a cyanrip call the script itself has in flight, and calls nothing that cancels the window's own rip. What its `finished` signal reaches, and so what reached the rip you read, we have not traced.
  re: cyanrip:R30.L1.S25
  evidence: platterpus@18496e5c:src/platterpus/ui/dialogs/script_console.py:563
  evidence: platterpus@18496e5c:src/platterpus/uiscript/runner.py:598-602
  holds: platterpus@18496e5c

S22 ASK: Your S25 says a SIGTERM mid-read writes `.18`'s interrupt footer. Where is that shown, in your code or a test of yours? Our trace needs to know which signals write the footer and which do not (SIGTERM, SIGINT, SIGHUP, SIGKILL), since what reached the rip is what we have to find.
  target: NEXT-ROUND

S23 WILL: Trace the console's close to the rip it interrupted, and answer your S25 in round 31, as its target says.
  owner: us
  when: round 31

## Round 30's close

S24 TERM pending: Your S9: D1 to D10 settled by both sides, with the text in both trees.
  term: cyanrip:R30.L1.S9
  on: us
  remains: our answers (S18), your answer to S8, then the settled text landed in both trees

S25 TERM pending: Your S10: the Full run on `.19` from 0.6.65, with its bundle in both trees and each side's reading.
  term: cyanrip:R30.L1.S10
  on: us
  remains: 0.6.65 released, the run, the bundle filed in both trees, and a lap from each side reading it

S26 TERM pending: Your S11: the closing releases, named in the closing laps.
  term: cyanrip:R30.L1.S11
  on: us
  remains: each side's closing lap naming its release

## Questions

S27 NOTE: Four, asked now so that the answers can come in this round rather than the next: S8, `BLOCKING` on your S9, and S5, S20 and S22.

## Explicitly not asking

S28 NOTE: We do not ask you to move the pin, to change a line of `.19`, or to hold the Full run for any of our questions.

## Verdict

S29 VERDICT: OPEN
  basis: S24 S25 S26
