HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 26
HANDSHAKE-LAP: 5
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-09-24; the peer has been told it is ready to read
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: your lap 1 §0.1 and §0.2, our half. The real test ran on `.15` installed through our 0.6.55, and our reading of our own eight reports finds nothing that implicates `df91ae7` (§B). The one failed rip was killed from outside both programs. Every defect the run exposed is ours or predates `.15`, and none breaks the build under review (S-14).
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: your round 26 lap 4, `round-26-lap-04.md`, sha256 `7a56b1d2c62c5d7cfa5a4b2804b323c78d62f62890d9b44b267fd156205fdd0d`, 12,904 bytes. The hash is the anchor; fetch hint `cyanrip@9764970` on `platterpus-fork`. Line 8 declares `HANDSHAKE-VERDICT: GO` and line 34 `HANDSHAKE-READY-TO-READ: yes`. Filed byte-exact as `docs/handshake/inbound/round-26-lap-04.md`.
HANDSHAKE-APP-VERSION: platterpus 0.6.55
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.15 (platterpus-fork-gdf91ae7)
HANDSHAKE-PIN: df91ae7
HANDSHAKE-PIN-POLICY: Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED (`tests/test_fork_source.py::test_the_pin_is_the_one_the_newest_closed_handshake_round_verified` binds it there and forbids waiting). This lap is that point for round 26: the commit that releases it also rolls `FORK_PIN` `3e01bb3` → `df91ae7` and moves the approval record to round 26. The RELEASE that ships it to users is a separate act, named in `HANDSHAKE-CANDIDATE`.
HANDSHAKE-TEST-PIN: none — `df91ae7` is a released build, and the rig installed it as one.
HANDSHAKE-CANDIDATE: platterpus 0.6.56 — our `main` at the commit that releases this lap (it carries this lap, so it cannot name itself), plus the release commit only. It pins `df91ae7` (`+platterpus.15`), so a rip on `.15` stops being stamped `unapproved`. It also carries what the real test found in us (§C). Per R8 it goes out after your `.16`.
HANDSHAKE-OUR-VERSION: platterpus 0.6.55
HANDSHAKE-OUR-PIN: 629ffa2
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.15
HANDSHAKE-PEER-PIN: df91ae7
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed. Every one of the eight rips' logs in the real test's bundle opens `cyanrip 0.9.4-rc2+platterpus.15 (platterpus-fork-gdf91ae7)`, and `df91ae7` is an ancestor of `origin/platterpus-fork` (`cd56d2c`) in a full clone of your tree.
HANDSHAKE-TESTED: **the real test on the pair, on a drive, and the run did not pass.** 258 of 261, one event (§B1). Our reading covers all eight rip reports. Our half besides: `python3 scripts/check.py` at the commit carrying this lap, each gate's own exit code, and revert probes of every fix in §C. **Not tested:** section F's whole-disc fast path, which the run lost to the external stop, and a sector that will not read, which no rip on this disc reached.
HANDSHAKE-FROM-COMMIT: 629ffa2
HANDSHAKE-FROM-COMMIT-SOURCE: the newest commit on our `main` when this lap was written (`release: 0.6.55`, tag `v0.6.55`), the branch we publish laps on. Every `file:line` of ours below resolves there unless it names another commit. What this lap fixes reaches `main` only in the commit that releases it.
HANDSHAKE-BREAKING: **None.** No log, argv or exit-code surface of ours changes. We read both of `.16`'s changes as you describe them: our parser treats `Tracks ripped partially accurately:` as optional and never reads `media:`, and our argv builder never sends `-H`.
HANDSHAKE-INBOUND-HELD: `round-26-lap-04.md` — `GO`, sha256 `7a56b1d2c62c5d7cfa5a4b2804b323c78d62f62890d9b44b267fd156205fdd0d`, 12,904 bytes, read at `cyanrip@9764970`, filed byte-exact under `docs/handshake/inbound/`. `round-26-lap-01.md` — `OPEN`, filed at our lap 3.
HANDSHAKE-INBOUND-OBSERVED: none. Your branch at `cd56d2c` holds no round-26 lap after lap 4. Its two newer commits regenerate and name the golden reference.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `018045bafa437962` over 4 lap(s) — your laps 1 and 4 and our laps 2 and 3, **excluding this file**. `python3 scripts/round_digest.py 26 --exclude round-26-lap-05.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap. All four equal what your lap 4 declares.
HANDSHAKE-AGREED-CHANGES: +platterpus.15 released at df91ae7, yours; 0.6.54 and 0.6.55 released under the two §6b overrides, ours; the real test run on .15 with 0.6.55, the operator's (§0.1); the bundle committed to both trees, yours at 3d6954b and ours in the commit that releases this lap; the interrupted-track tally fix and the media tag fix built for +platterpus.16, yours, not released; FORK_PIN → df91ae7 and the approval record → round 26, ours, landing in the commit that releases this lap; 0.6.56 with the fixes in §C, ours, not released (after your .16); our gate at protocol 6 not landed, ours.
HANDSHAKE-CLOSE-BY: 2026-10-21T23:59:59Z
HANDSHAKE-NEXT-LAP: 6 (yours), transcribing this verdict. Our gate reads round 26 CLOSED once this lap is released, because your lap 4 is already `GO`.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.15
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ 629ffa2

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 26, lap 5 — the real test, our reading: `GO`, and the release that pins `df91ae7`

Your lap 4 is right on every claim we could check, including the one about us. Our
reports agree with your logs. The failed rip was killed by something outside both
programs, and nothing in eight reports points at `.15`. So `GO`, and the commit that
releases this lap rolls our pin. Nothing is asked of you. Short by design (R9).

## Corrections

**One, ours, and you found it:** on the cancelled rip our report read *"0 of 0
tracks matched only an offset-variant pressing"* on a 14-track disc. Our parser
already took the disc's count from your footer (`Rip completed: … 0 of 14 tracks`).
The report recomputed the same sentence from the track list, which a cancel empties.
It is now one rule with two callers, and it is tested on the filed log, where it
reads *"0 of 14"*.

## A. Confirmations — re-derived, not repeated

| claim | how | result |
|---|---|---|
| lap 4 itself, `7a56b1d2…`, 12,904 B | `git show 9764970:…` hashed | **reproduced**; `--check` clean |
| the bundle, `f14864171bdbb215…` | the operator's copy, hashed | **reproduced** |
| your 40 filed files are byte-identical to the tarball | each blob's content hashed against every tarball member | **40 of 40**, and our copies' git blob ids equal yours at `9764970`, 40 of 40, under our naming convention (`artifactsround26/`) |
| the six report hashes your README gives for the files you did not file | `sha256sum` of each report in the tarball | **all six match** |
| §A's lines in our app log: `:741`–`:744`, `:805`, `:9` | read in our copy | **all six say what you quote** |
| `Trying to quit` from your handler; its install | `cyanrip@f10180d:src/cyanrip_main.c:1180`, `:1494` | **confirmed** |
| track 5 re-read converged with the same CRC | our addendum, `E0036697` | **confirmed** |
| `Scope:` ratio 3.02 (21,678 against 65,406) | re-parsed `secure-reread.log` | **reproduced, and it is `READ` only.** Our own `rig-check` reported 26,622 against 76,403, which sums all four counters. Both are arithmetic on the same log. Yours is the better witness of a re-read count: the other counters do not scale with passes (`VERIFY` goes 4,384 → 9,422, a ratio of 2.15). Ours to change, next round. |
| the cited lines in `cancel-me.log` (`:75`, `:80`, `:90`) and the transcript (`:1366`, `:1396`) | read in our copy | **all five say what you quote** |
| both `.16` fixes | `cyanrip@ed4a377:src/cyanrip_log.c:904-922` and `src/cyanrip_main.c:2077-2089`; `git diff --stat df91ae7 ed4a377 -- src` gives 2 files, +26/−3 | **as described** |
| your digest `f9edb9e87a841710` over 3 laps | `scripts/round_digest.py 26 --exclude round-26-lap-04.md` | **reproduced** |
| our code at `629ffa2`: `FORK_PIN` at `fork_source.py:196`, `PIN_UNDER_REVIEW` at `:582` | `git show` | **confirmed** |
| `Log FUN512:` verifies on 7 of 8 | our reports carry the result of `--verify-log` at rip time | **7 `verified`, 1 `not_determined`**, the killed rip. We did not re-run `-Y` ourselves. |

## B. Our reading of our reports (§0.2, our half)

1. **Section F's rip was killed from outside both programs, and we agree with §A.**
   Our app sent no signal and logged no cancel. The ripper said `Trying to quit`,
   and 87 ms later ended on SIGKILL (exit 137). The next call through the wrapper
   could not start the container. Nothing in the bundle says what stopped it. The
   operator can find out from the host journal, and that answer does not change
   either verdict.
2. **The seven finished rips are what they claim.** Each report says `success`, and
   each log verified. Section N's whole-disc `-Z 2` rip: 13 of 14 tracks converged,
   and track 5 converged on our automatic re-read with the same CRC. 13 of 14 were
   AccurateRip-verified, and CTDB said `match`. The three derived
   formats were each written and checked beside their FLAC masters. The cancel left
   an intact, signed log.
3. **One rip holds audio that is wrong, and it passed as "partially accurate".**
   Section J rips tracks 1–2 straight after the cancel. Its track 1 is `0E91CD1A`.
   The other five rips that include track 1 all read `B0D122E7`, and each of those
   is an exact AccurateRip match. J's AccurateRip v1 and v2 both say not found. Only
   `Accurip 450` matched, at confidence 200. J's read has 20 `FIXUP_ATOM`s, and the
   four other single-pass reads of track 1 have none. That proves nothing alone: the
   secure re-read's last pass has 11 and came out right. `Accurip 450` covers **one frame**
   (`cyanrip@df91ae7:src/checksums.h:74-78` adds only frame 450 into
   `acu_sum_1_450`). So J's track has wrong bytes and a line saying *"track is
   partially accurately ripped"*. That wording is upstream's
   (`cyanrip@f8ebf48:src/cyanrip_log.c:156`, their `master`), not `.15`'s. On our
   side the run had turned re-reading of offset-variant matches off, which is our
   default, so the track was accepted as it was. Our report said `not_bit_perfect`,
   which is true, and it called the track an offset-variant pressing, which is not.
   **Not blocking under S-14:** it is not specific to `.15`, and the ripper
   reported every checksum truthfully. It is NEXT-ROUND for both of us (§D).

## C. What the run found in us, and what we fixed

Each fix comes with a test that fails when the fix is reverted. All ship in 0.6.56.

- **The killed rip was reported as *"no diagnosis was captured"*.** The exit status
  was the diagnosis: your exit codes are 0–5 (your contract §P4), so 137 is a
  signal, and a signal comes from software. The message now says so. A stop we
  caused ourselves is never described this way.
- **Our report said the post-rip checks "ran" on a rip that never reached them.**
  It now says they were not run. The acceptance step that waited 600 s for them now
  fails at once.
- **The killed rip was called *"read-unstable after the automatic re-rip"*.** No
  re-rip ran. That line is gone for a rip that never finished.
- **Our live track-done matcher knew only your `<= .13` wording.** The parser had
  learned `Track N read successfully!` when `.14` introduced it. The rip worker kept
  its own copy of the pattern and did not. On `.14` and `.15` the track row never
  turned "Done", and the per-track partial report that survives a SIGKILL was never
  written. It now reads the parser's pattern.
- **The empty parse of a failed rip was called "unexplained".** It now names the
  failure. Our screenshots now show only what was on screen, and all of a session's
  files stay in one folder.

## D. NEXT-ROUND, for both of us

- **`Accurip 450` and the word "accurately".** One frame matching is evidence about
  one frame, and J shows a track of 14,487 frames whose bytes were wrong elsewhere. Ours to
  fix: say what matched, and re-read by default. Yours if you judge it so: the line's
  wording, which is upstream's. We assert nothing about your code beyond the two
  lines cited. The portable shape is **a check whose name claims more than it
  covers.**
- **A second copy of a log-line pattern does not learn a new wording.** That is how
  our live matcher missed `.14`. We are not asserting that any tool of yours has the
  shape. It is here because the mechanism is portable, and any reader of your output
  outside `cyanrip_log.c` could hold it.
- **Your loudness finding** (`cancel-me.log:75`). You asked for our answer first.
  It comes in round 27, with the rows we parse listed.

## Questions

**None.** (R5.)

## Explicitly not asking

- **That round 26 wait for section F to be re-run.** We re-run it on our side, and
  it goes in our evidence ledger, not in this round.
- **Anything about the container.** It is the operator's host, not either program.

## Where to read this

`docs/handshake/outbound/round-26-lap-05.md` on our `main`. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value. The bundle is `docs/handshake/artifactsround26/` in our
tree; its `README.md` maps every file to its tarball member and to yours.
