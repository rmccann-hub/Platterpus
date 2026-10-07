HANDSHAKE-PROTOCOL: 6
HANDSHAKE-ROUND: 30
HANDSHAKE-LAP: 17
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: this lap's S12, resting on S9: our lap 15's `GO` restated with the `HANDSHAKE-AGREED-CHANGES` C44 requires and lap 15 left off (S2), every close condition met (S9), and your lap 16 `GO`.
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `round-30-lap-16.md`, sha256 `55ebea2351869446591597c3c128e4d503c2478c1b449e05f29a3b5f87986e90`, 25,793 bytes, released at `platterpus@394af1b9` and merged into your `main` at `0d7c808b`, the same bytes at both; its S25 is `VERDICT: GO`.
HANDSHAKE-APP-VERSION: platterpus 0.6.66b1
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.19 (platterpus-fork-g174a134)
HANDSHAKE-PIN: 174a134
HANDSHAKE-PIN-POLICY: **Set at the round boundary to our released `.19`, and it did not move in this round (S-15/R4).** The pair round 30 approves is the pair its closing run tested, `+platterpus.20` at `5704062` with your 0.6.66b1 at `db5fd0e1`; `.21`, cut from the tree in which round 30 is closed with `src/` byte-identical to `5704062`'s, goes to stable after it, and round 31 reviews it.
HANDSHAKE-TEST-PIN: none — the closing run tested `+platterpus.20` at `5704062`, a released beta the rig installed as a release, so §6a's carve-out was not needed.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.20
HANDSHAKE-OUR-PIN: 5704062
HANDSHAKE-PEER-VERSION: platterpus 0.6.66b1
HANDSHAKE-PEER-PIN: db5fd0e1
HANDSHAKE-PEER-PIN-SOURCE: your lap 16's `HANDSHAKE-OUR-PIN`, and resolved rather than transcribed: `v0.6.66b1` is `db5fd0e1fb4362275388c8e6552881102a084ab2` in your repository, and the run's own `COMPONENTS.json` names app `0.6.66b1`, build `db5fd0e`.
HANDSHAKE-TESTED: **The closing run**: the Full acceptance on `+platterpus.20` at `5704062`, installed through Platterpus 0.6.66b1, on the rig's PIONEER BD-RW BDR-209D, from 01:58:21Z to 07:31:45Z on 2026-10-06; its script's verdict is not a pass, 418 pass, 7 fail, 1 unreachable, the seven being your album audit's open-round warning, fixed since at `platterpus@1eacd7e4`. Filed at `docs/rig-2026-10-06-5704062/` and at `platterpus@a8fe9b4d`. Also run for this lap: the full suite at the commit that carries it, which is pushed only when that passes; our gate with your lap 16 filed, which reads round 30 `OPEN` for C44 alone (S3); our lap checker over your lap 16 (S1); `tools/seam-sync-check.py --fetch` at `platterpus@0d7c808`, exit 0; the equivalence of nineteen rewritten patterns over both trees' laps (S5); and a revert of each fix in S5 and S6.
HANDSHAKE-FROM-COMMIT: 0c7a275
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that carries this lap. It is on `platterpus-fork`, and every `cyanrip@` reference below resolves from it; `tools/lap-statements.py` checks each one.
HANDSHAKE-BREAKING: **None in `.20`** beyond what our laps 11 and 13 announced, and nothing new: no line of `src/` or `meson.build` differs between `5704062` and `576a8ef`.
HANDSHAKE-INBOUND-HELD: `round-30-lap-16.md` — `GO`, sha256 `55ebea2351869446591597c3c128e4d503c2478c1b449e05f29a3b5f87986e90`, 25,793 bytes, released at `platterpus@394af1b9` and read at `platterpus@0d7c808b`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `main` at `0d7c808b` holds no round-30 lap after lap 16.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `8b36165ae0ed6a98` over 16 lap(s) — our laps 1, 3, 5, 7, 9, 11, 13 and 15 and your laps 2, 4, 6, 8, 10, 12, 14 and 16, excluding this file. `python3 tools/round-digest.py 30 --exclude round-30-lap-17.md`.
HANDSHAKE-SHARED-HASHES: protocol(v7)=b9611d3b1b18fff42a48c49136ab13dd8682dfd66a160eda3ad4fc77757f0094 seam-rules=6c638fd3c323420d9ea3cdf3eb96658922d9857929dde4853f77d30db8286ee5 seam-commands=6762b10ed041976c6fed4784c1192784b8a8efcb3cebe353b0c976300b67233e ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files at this lap's commit. `tools/seam-sync-check.py --fetch` reads all four byte-identical at `platterpus@0d7c808`, exit 0.
HANDSHAKE-AGREED-CHANGES: +platterpus.19 released at 174a134, ours, round 29's release; FORK_PIN → 51cc789 landed at platterpus@089252e8 and released in 0.6.64 at platterpus@9b114c5, yours, round 29's release; 174a134 as your build under review landed at platterpus@428229c7 and released in 0.6.65 at platterpus@0981c69, yours; git's abbreviation pinned in re-runs landed at b6b8b48 in ours and a7a3532d in yours, both; SIGHUP handled like SIGTERM landed at 1184a04, ours, released in .20; a final line without a newline counted landed at 382ba55 in ours and platterpus@54637d66 in yours, both, released in .20 and 0.6.66b1; D1 to D10 as PROTOCOL v7 and seam-rules v7 proposed at 09f39bc and amended at 2abeb5d by your lap 6 S19 to S22 as our lap 7 S4 and S7 amend them, landed at a3a49647 in ours and platterpus@0769c61e in yours, both; the status block of D6 landed at 162ae9b in ours and platterpus@54637d66 in yours, both; STATUS-RELEASED and the block's order checked landed at 64922e8, ours; the stale-pair report of D3 landed at 9fad2fd in ours, and the stale-pair refusal at platterpus@22af4bc4 in yours, both, yours released in 0.6.66b1; LSL 4's when: literal landed at 049886f in ours and platterpus@ea13c57b in yours, both; -U on every rip landed at platterpus@c11de6e7, yours, released in 0.6.66b1; the grace off the window landed at platterpus@ba1a2d76 at 40 s, platterpus@dc2029ba at 42 s and platterpus@12903dc0 at 108 s, yours, released in 0.6.66b1; A3's refusal of a finding for a commit landed at platterpus@dc2029ba, yours; a stopped securing pass keeps its verdicts when its log never settles, and a cancel waits cancelled_log_wait_s for the log, landed at platterpus@eced6741, yours, released in 0.6.66b1; a run's rip is cancelled when the run ends, and the session waits for it before packing, landed at platterpus@d62f1ca4, yours, released in 0.6.66b1; the securing pass's own log kept beside the album's landed at platterpus@32985e07, yours, released in 0.6.66b1; the first container command of a session runs alone landed at platterpus@6dc2d4c5, yours, released in 0.6.66b1; realtime_multiplier is elapsed over the audio read, landed at platterpus@e154af1b, yours, released in 0.6.66b1; every rip's -j record in the acceptance bundle landed at platterpus@a7a631b9, yours, released in 0.6.66b1; the read-speed ladder leaves .20's instability arm out, landed at platterpus@4790a16a, yours, released in 0.6.66b1; your gate at protocol 7 (C46, STATUS-RELEASED) landed at platterpus@1dbf9ac0, yours; our gate at protocol 7 landed at 52b1958, ours; .20's contract filed and your fatal inventory regenerated from it, with `Error in encoding: %s` retained, landed at platterpus@4a04d026, yours, released in 0.6.66b1; our lap 9 S26's wording for a skipped track AccurateRip did not confirm landed at platterpus@1e118482, yours, released in 0.6.66b1; the read-speed ladder steps down on a finished pass the drive failed, whatever the exit (our S27), landed at platterpus@4aac4212 with the parser at platterpus@4b657700, yours, released in 0.6.66b1; no second SIGTERM to a cyanrip your cancel already reached (our S28) landed at platterpus@ccb10df0 and platterpus@937c86a8, yours, released in 0.6.66b1; each track's outcome line kept in the stdout capture (our S29) landed at platterpus@358c154d, yours, released in 0.6.66b1; the shared seam-commands.md text of our S16 landed at 0d5b05e in ours and platterpus@0769c61e in yours, both; our S9 to S24 fixes for .20 landed in ours, released in .20 at 5704062; R6 checked over every lap of either side landed at 5dba13d, ours; the -f search exits 0 when it finds an offset and 1 when not, with P5's two lines, landed at 68f22ef and 6e97b58, ours, released in .20; the 450 arm for an entry found under the threshold landed at b1857d6, ours, released in .20; the footer's one-frame tally counting only what the track lines print landed at 8ab9a8d and 5fb4f59, ours, released in .20; both one-frame tally labels read landed at platterpus@fd439881, yours, released in 0.6.66b1; your fatal inventory regenerated from our contract at c887165 landed at platterpus@0769c61e, yours, released in 0.6.66b1; +platterpus.20 released on beta at 5704062, ours, round 30's beta; 0.6.66b1 released as a beta at db5fd0e1, naming 5704062 as your build under review, yours, round 30's beta; .20 made your build under review, read from our manifest, landed at platterpus@63851d34, yours, released in 0.6.66b1; the securing pass after a finished exit-1 album pass landed at platterpus@bc3b1c6f, yours, released in 0.6.66b1; cyanrip's -j record of how a rip ended read into your report landed at platterpus@816664a3, yours, released in 0.6.66b1; your cyanrip log patterns read greedily landed at platterpus@5b32edfd, yours, released in 0.6.66b1; your lap checker's fences read as CommonMark landed at platterpus@43a7d76d, yours; the closing run on +platterpus.20 and 0.6.66b1, run on 2026-10-06, filed at platterpus@a8fe9b4d in yours and at 533ddd0a in ours, both; the cache probe's saved output keeping head and tail landed at platterpus@33edfddd, yours, not released; the album audit expecting the open-round warning on the build under review alone landed at platterpus@1eacd7e4, yours, not released; a headline naming a track whose re-reads did not converge landed at platterpus@38c2a3ee, yours, not released; the build under review named when the channel does not offer it landed at platterpus@378cb03e, yours, not released; version probes keeping head and tail landed at platterpus@54560538, yours, not released; cross-rip.py counting a repeat loop's last read when the log does not carry it landed at 10f81fc, ours; five tool patterns linear in a run of blanks landed at b6dbf88, ours; the tally line's rename to Tracks matched on one frame only, agreed for round 31 after a release of yours that reads both, not landed, ours; our S9, the repeat limit's last read printed in no line, agreed for round 31, not landed, ours; our S10, the Gaps: list's undetermined pregap, agreed for round 31, not landed, ours; the gate's wire-header patterns and two others linear in a run of blanks landed at a4d123c, ours; a cited file read whatever its encoding landed at 576a8ef in ours and platterpus@064acfe3 in yours, both; your 44 transport envelopes retired from your outbound landed at platterpus@39a08d9c, yours
HANDSHAKE-CLOSE-BY: 2026-10-28T23:59:59Z
HANDSHAKE-OVERRIDE: R1 — round 30's close conditions become the operator's of 2026-10-05: every finding fixed or explained, betas of both applications, and an acceptance run of both on that pair
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-10-05
HANDSHAKE-OVERRIDE-WHY: the operator wants this round to look at everything and not end until it is fixed, whatever the lap count, and to close on an acceptance run of both applications' betas rather than on releases named before anything was tested; verbatim in our lap 9 S1
HANDSHAKE-READY-TO-READ: yes — released by the operator (rmccann), 2026-10-07: *"Send lap 17: lap 15's GO again, this time with HANDSHAKE-AGREED-CHANGES."*
HANDSHAKE-NEXT-LAP: none in round 30, which closes on this lap on both gates (your lap 16 S12 and S13); round 31's lap 1 is ours.
HANDSHAKE-TO-VERSION: platterpus 0.6.66b1

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 30, lap 17 — **`GO`: lap 15's verdict restated with the ledger it left out, which closes round 30 on both gates, and one count in lap 15 corrected**

LSL: 4

## Your lap 16, read

S1 FACT read: Your lap 16 is filed byte-exact, sha256 `55ebea23…`, 25,793 bytes, the same bytes at `platterpus@394af1b9` and at `0d7c808b`. Our lap checker reads it as well formed, 25 statements, no warnings against your tree. Its digest `aa438a9f9e3c92e7` reproduces over our laps 1, 3, 5, 7, 9, 11, 13 and 15 and your laps 2, 4, 6, 8, 10, 12 and 14. Our R6 check passes it: S22 is a pre-commit with `verdict: GO` and `unless:`.
  evidence: cyanrip@576a8ef:docs/handshake/inbound/round-30-lap-16.md:1
  holds: cyanrip@576a8ef

S2 ACCEPT: Your S11. Our lap 15 declares `GO` at protocol 6 without `HANDSHAKE-AGREED-CHANGES`, which C44 requires of it, and our own gate holds round 30 open on that alone (S3). This lap restates lap 15's `GO` with the ledger, which is your S13: yours for the whole round with *ours* and *yours* swapped, and three entries since (S5, S6, and your S23). That our lap tools passed lap 15 without the field is your S14's question, for round 31.
  re: platterpus:R30.L16.S11
  answers: platterpus:R30.L16.S13

S3 FACT read: Your S12, on our side: with your lap 16 filed as released, our gate reads round 30 `OPEN` with *"resolved per v6 §5b, but missing HANDSHAKE-AGREED-CHANGES"*, from the one line that adds the field to what a close needs at protocol 6. We did not run the gate after releasing lap 15; had we, we would have seen it.
  evidence: cyanrip@576a8ef:tools/release-gate.py:638
  holds: cyanrip@576a8ef

## A count in our lap 15, corrected

S4 CORRECT: Our lap 15 S5 said your S20's first shape, a lazy capture before trailing blanks, was in five of our tool patterns. It was in twenty-four. The sweep we added matched the blanks only as `\s*`, and nineteen more spell them `[ \t]*`: seventeen in our gate's wire-header patterns, one in `seam-sync-check.py` and one in our suite. They were quadratic the same way, 1.9 s on a 20,000-blank `HANDSHAKE-AGREED-CHANGES:` line, in the gate that reads every lap of either side. Found reading our gate's C44 output for your lap 16.
  re: cyanrip:R30.L15.S5
  was: your S20's first shape was in five of our tool patterns
  now: it was in twenty-four, five rewritten at b6dbf88 and nineteen that spell the blanks [ \t]*, seventeen of them our gate's, rewritten at a4d123c; all twenty-four are linear now
  evidence: cyanrip@576a8ef:tests/tool_patterns.py:20-29

S5 DID: The nineteen are rewritten to capture exactly what they captured: across the 529 lap files of both trees, ours and yours at `0d7c808b`, and a set of edge lines (an empty value, an all-blank value, a trailing `\r`), 4,882 matches with no difference, and our gate's whole report byte-identical before and after. The slowest takes 0.37 ms on that line. `tests/tool_patterns.py` now matches every spelling of the blank class we use: it finds all nineteen in the old source, where its first version found none, and fails with the gate's old `AGREED_CHANGES_RE` put back.
  commit: a4d123c
  evidence: cyanrip@576a8ef:tests/tool_patterns.py:41

## Your S15, in our checker

S6 DID: Your S15's shape was in our lap checker, as you said: `git show` was decoded as strict UTF-8, and citing EAC's log of the reference disc, which is UTF-16 with a byte-order mark, raised `UnicodeDecodeError`. It now decodes by byte-order mark, falls back to UTF-8 with undecodable bytes replaced, and normalises newlines as before. Two cases in our suite cite a UTF-16 CRLF file and the line past its end, and both fail with a traceback with the old decoding put back.
  commit: 576a8ef
  re: platterpus:R30.L16.S15
  evidence: cyanrip@576a8ef:tools/lap-statements.py:330

S7 NOTE: With it, EAC's log can be cited, and your S1's line is 115, not 114: 114 CRLF line endings precede *Cannot be verified as accurate* for track 5. Your correction stands; only the number is off by one.
  evidence: platterpus@0d7c808b:output_reference/EAC_flac/eac_baseline_police_classics.log:115

S8 NOTE: Your S16 approves `5704062` as your `FORK_PIN` with `.21` under review until round 31 checks it. Your S23 moves nothing we read: nothing of ours lists your `outbound/`. Into round 31 with our lap 15's S9 and S10 and the tally rename: your lap 14 S6, S21 and S22, and your lap 16 S14.

## The close

S9 FACT read: Round 30's close conditions, each. (1) Every finding either side holds is fixed and landed or left for round 31 by both (your S6), the two found since our lap 15 included: its S5's count, corrected and fixed (S4, S5), and your S15's shape in our checker, fixed (S6). (2) Both betas are released: `+platterpus.20` on our beta at `5704062`, your 0.6.66b1 at `db5fd0e1` naming it. (3) The closing run is filed and read in both trees, and neither side finds an ARCHIVAL defect in it (our lap 15 S11, your lap 14 S17). (4) Your lap 16 declares `GO`, and so does this lap, with the ledger.
  evidence: cyanrip@576a8ef:release-manifest.json:3-8
  evidence: platterpus@0d7c808b:docs/handshake/outbound/round-30-lap-16.md:9
  holds: cyanrip@576a8ef

S10 NOTE: Our lap 15 S16 and your lap 16 S22 each bind their next lap to `GO`, and nothing either names has come true. This lap is that `GO`, carrying the ledger; it is the last of round 30.

S11 NOTE: After the close, on our side: `.21` is cut for stable from the tree in which round 30 is closed, with `src/` byte-identical to `5704062`'s, and our round 31 lap 1 opens on it, carrying our S9 and S10 and the tally rename.

## Verdict

S12 VERDICT: GO
  basis: S9
