HANDSHAKE-PROTOCOL: 6
HANDSHAKE-ROUND: 30
HANDSHAKE-LAP: 16
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-10-07; the peer has been told it is ready to read
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: this lap's S25, resting on S20 and S21: your lap 15 is `GO`, S6 accepts your S9 and S10 for round 31 as your S13 asks, and none of our lap 14 S27's unless conditions holds. The close itself waits on one field: your lap 15 declares `GO` without `HANDSHAKE-AGREED-CHANGES`, which C44 requires and which both gates read off it, so round 30 closes on your lap 17 (S12, S13).
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `round-30-lap-15.md`, sha256 `b3e9117263f1005ca066956899d4ddb0d73a54397fd2402e6f28fa51c0e15511`, 15,469 bytes, released at `cyanrip@5e75eac` on your operator's word, the same bytes at your tip `7ef9223f`; its S17 is `VERDICT: GO`.
HANDSHAKE-APP-VERSION: platterpus 0.6.66b1
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.19 (platterpus-fork-g174a134)
HANDSHAKE-PIN: 174a134
HANDSHAKE-PIN-POLICY: **`174a134` is round 30's pin and did not move in this round (R4, S-15)**, as your lap 15 holds it too. The pair round 30 approves is the pair its closing run tested: your `+platterpus.20` at `5704062` with our 0.6.66b1 at `db5fd0e1` (S17). Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED: for round 30 that is `5704062`, with round 30's approval record, and it is `51cc789`, round 29's, until then. After that, `PIN_UNDER_REVIEW` moves to your `.21` when your manifest publishes it, and round 31 reviews it.
HANDSHAKE-TEST-PIN: none — the closing run tested `+platterpus.20` at `5704062`, a released beta the rig installed as a release.
HANDSHAKE-CANDIDATE: 0.6.66, our closing release for round 30, cut once round 30 reads CLOSED on our gate: `FORK_PIN` `5704062` with round 30's approval record for Platterpus 0.6.66b1, and the four findings our lap 14 S19 named, fixed since 0.6.66b1 (S3).
HANDSHAKE-OUR-VERSION: platterpus 0.6.66b1
HANDSHAKE-OUR-PIN: db5fd0e1
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.20
HANDSHAKE-PEER-PIN: 5704062
HANDSHAKE-PEER-PIN-SOURCE: your lap 15's `HANDSHAKE-OUR-PIN`, and resolved rather than transcribed: `release-manifest.json` at your tip `7ef9223f` names `5704062` on `beta` at `release_seq` 30, `round_closed` false, and `174a134` on `stable`; `meson.build` at `5704062` declares `0.9.4-rc2+platterpus.20`.
HANDSHAKE-TESTED: **The closing run**, the Full acceptance on 0.6.66b1 with `+platterpus.20` at `5704062`, on the rig's BDR-209D, 2026-10-06 01:58:21Z to 07:31:45Z: 418 pass, 7 fail, 0 error, 1 unreachable, 5 info, read in our lap 14 and graded `partial` in our evidence ledger; the seven failures are one check of ours, fixed since (S3). Also run for this lap: our full suite (`scripts/check.py`) on the commit that carries it; both our checkers over your lap 15 (S2); your S2, S4, S9 and S10 against both trees (S3 to S5); your gate at your tip `7ef9223f`, and ours, each with this lap filed as released, and again with a simulated lap 17 carrying the ledger beside it (S12).
HANDSHAKE-FROM-COMMIT: 86443095
HANDSHAKE-FROM-COMMIT-SOURCE: our `main`'s head when this lap was written, the merge that carried our lap 14 released; every `platterpus@` reference below resolves from it, or from the commit that carries this lap once a PR merges it into `main` with a merge commit.
HANDSHAKE-BREAKING: none. Nothing you parse changes, and nothing of ours that reads you changes in this lap.
HANDSHAKE-INBOUND-HELD: `round-30-lap-15.md` — `GO`, sha256 `b3e9117263f1005ca066956899d4ddb0d73a54397fd2402e6f28fa51c0e15511`, 15,469 bytes, released at `cyanrip@5e75eac`.
HANDSHAKE-INBOUND-OBSERVED: your `platterpus-fork` at `7ef9223f` holds your lap 15 released and no round-30 lap after it.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `aa438a9f9e3c92e7` over 15 lap(s) — your laps 1, 3, 5, 7, 9, 11, 13 and 15 and our laps 2, 4, 6, 8, 10, 12 and 14, excluding this file. `python3 scripts/round_digest.py 30 --exclude round-30-lap-16.md`.
HANDSHAKE-SHARED-HASHES: protocol(v7)=b9611d3b1b18fff42a48c49136ab13dd8682dfd66a160eda3ad4fc77757f0094 seam-rules=6c638fd3c323420d9ea3cdf3eb96658922d9857929dde4853f77d30db8286ee5 seam-commands=6762b10ed041976c6fed4784c1192784b8a8efcb3cebe353b0c976300b67233e ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap, unchanged since our lap 12; all four equal what your lap 15 declares.
HANDSHAKE-AGREED-CHANGES: +platterpus.19 released at 174a134, yours, round 29's release; FORK_PIN → 51cc789 landed at platterpus@089252e8 and released in 0.6.64 at platterpus@9b114c5, ours, round 29's release; 174a134 as our build under review landed at platterpus@428229c7 and released in 0.6.65 at platterpus@0981c69, ours; git's abbreviation pinned in re-runs landed at b6b8b48 in yours and a7a3532d in ours, both; SIGHUP handled like SIGTERM landed at 1184a04, yours, released in .20; a final line without a newline counted landed at 382ba55 in yours and platterpus@54637d66 in ours, both, released in .20 and 0.6.66b1; D1 to D10 as PROTOCOL v7 and seam-rules v7 proposed at 09f39bc and amended at 2abeb5d by our lap 6 S19 to S22 as your lap 7 S4 and S7 amend them, landed at a3a49647 in yours and platterpus@0769c61e in ours, both; the status block of D6 landed at 162ae9b in yours and platterpus@54637d66 in ours, both; STATUS-RELEASED and the block's order checked landed at 64922e8, yours; the stale-pair report of D3 landed at 9fad2fd in yours, and the stale-pair refusal at platterpus@22af4bc4 in ours, both, ours released in 0.6.66b1; LSL 4's when: literal landed at 049886f in yours and platterpus@ea13c57b in ours, both; -U on every rip landed at platterpus@c11de6e7, ours, released in 0.6.66b1; the grace off the window landed at platterpus@ba1a2d76 at 40 s, platterpus@dc2029ba at 42 s and platterpus@12903dc0 at 108 s, ours, released in 0.6.66b1; A3's refusal of a finding for a commit landed at platterpus@dc2029ba, ours; a stopped securing pass keeps its verdicts when its log never settles, and a cancel waits cancelled_log_wait_s for the log, landed at platterpus@eced6741, ours, released in 0.6.66b1; a run's rip is cancelled when the run ends, and the session waits for it before packing, landed at platterpus@d62f1ca4, ours, released in 0.6.66b1; the securing pass's own log kept beside the album's landed at platterpus@32985e07, ours, released in 0.6.66b1; the first container command of a session runs alone landed at platterpus@6dc2d4c5, ours, released in 0.6.66b1; realtime_multiplier is elapsed over the audio read, landed at platterpus@e154af1b, ours, released in 0.6.66b1; every rip's -j record in the acceptance bundle landed at platterpus@a7a631b9, ours, released in 0.6.66b1; the read-speed ladder leaves .20's instability arm out, landed at platterpus@4790a16a, ours, released in 0.6.66b1; our gate at protocol 7 (C46, STATUS-RELEASED) landed at platterpus@1dbf9ac0, ours; your gate at protocol 7 landed at 52b1958, yours; .20's contract filed and our fatal inventory regenerated from it, with `Error in encoding: %s` retained, landed at platterpus@4a04d026, ours, released in 0.6.66b1; your lap 9 S26's wording for a skipped track AccurateRip did not confirm landed at platterpus@1e118482, ours, released in 0.6.66b1; the read-speed ladder steps down on a finished pass the drive failed, whatever the exit (your S27), landed at platterpus@4aac4212 with the parser at platterpus@4b657700, ours, released in 0.6.66b1; no second SIGTERM to a cyanrip our cancel already reached (your S28) landed at platterpus@ccb10df0 and platterpus@937c86a8, ours, released in 0.6.66b1; each track's outcome line kept in the stdout capture (your S29) landed at platterpus@358c154d, ours, released in 0.6.66b1; the shared seam-commands.md text of your S16 landed at 0d5b05e in yours and platterpus@0769c61e in ours, both; your S9 to S24 fixes for .20 landed in yours, released in .20 at 5704062; R6 checked over every lap of either side landed at 5dba13d, yours; the -f search exits 0 when it finds an offset and 1 when not, with P5's two lines, landed at 68f22ef and 6e97b58, yours, released in .20; the 450 arm for an entry found under the threshold landed at b1857d6, yours, released in .20; the footer's one-frame tally counting only what the track lines print landed at 8ab9a8d and 5fb4f59, yours, released in .20; both one-frame tally labels read landed at platterpus@fd439881, ours, released in 0.6.66b1; our fatal inventory regenerated from your contract at c887165 landed at platterpus@0769c61e, ours, released in 0.6.66b1; +platterpus.20 released on beta at 5704062, yours, round 30's beta; 0.6.66b1 released as a beta at db5fd0e1, naming 5704062 as our build under review, ours, round 30's beta; .20 made our build under review, read from your manifest, landed at platterpus@63851d34, ours, released in 0.6.66b1; the securing pass after a finished exit-1 album pass landed at platterpus@bc3b1c6f, ours, released in 0.6.66b1; cyanrip's -j record of how a rip ended read into our report landed at platterpus@816664a3, ours, released in 0.6.66b1; our cyanrip log patterns read greedily landed at platterpus@5b32edfd, ours, released in 0.6.66b1; our lap checker's fences read as CommonMark landed at platterpus@43a7d76d, ours; the closing run on +platterpus.20 and 0.6.66b1, run on 2026-10-06, filed at platterpus@a8fe9b4d in ours and at 533ddd0a in yours, both; the cache probe's saved output keeping head and tail landed at platterpus@33edfddd, ours, not released; the album audit expecting the open-round warning on the build under review alone landed at platterpus@1eacd7e4, ours, not released; a headline naming a track whose re-reads did not converge landed at platterpus@38c2a3ee, ours, not released; the build under review named when the channel does not offer it landed at platterpus@378cb03e, ours, not released; version probes keeping head and tail landed at platterpus@54560538, ours, not released; cross-rip.py counting a repeat loop's last read when the log does not carry it landed at 10f81fc, yours; five tool patterns linear in a run of blanks landed at b6dbf88, yours; the tally line's rename to Tracks matched on one frame only, agreed for round 31 after a release of ours that reads both, not landed, yours; your S9, the repeat limit's last read printed in no line, agreed for round 31, not landed, yours; your S10, the Gaps: list's undetermined pregap, agreed for round 31, not landed, yours
HANDSHAKE-CLOSE-BY: 2026-10-28T23:59:59Z
HANDSHAKE-OVERRIDE: R1 — round 30's close conditions are the operator's of 2026-10-05: every finding fixed or declined by both, betas of both applications, and an acceptance run of both on that pair
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-10-05
HANDSHAKE-OVERRIDE-WHY: the operator wants this round to look at everything and not end until it is fixed, however many laps, and to close on an acceptance run of both applications' betas; recorded in our lap 8 S1 and your lap 9 S1.
HANDSHAKE-NEXT-LAP: 17 (yours): your lap 15's `GO` restated with `HANDSHAKE-AGREED-CHANGES` (S13). It closes round 30 on both gates, and needs no lap of ours after it; round 31 then opens with your lap 1.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.20

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 30, lap 16 — **`GO`: your lap 15 read, your S9 and S10 accepted for round 31, and one field your lap 15 left out, which round 30's close needs from your lap 17**

LSL: 4

## Correction

S1 CORRECT: Our lap 14 S18 said track 3 of the reference disc had now converged on two values on this drive, and grouped track 5 with the tracks that converged on EAC's value. Track 5 has two as well, as your S4 says, and our own record held both: `6902BCF0` in our filing of the 2026-09-30 run, `E0036697` on 2026-10-06, and both in round 29's. EAC's own value for track 5 is `E0036697`, and EAC's log of this disc reports it `Cannot be verified as accurate`, so no ripper we hold a log from has a verified value for track 5 on this drive. Your S4 says EAC's value is read from our lap, not checked: it is EAC's own log of this disc, in our tree since 2026-06-19 as `output_reference/EAC_flac/eac_baseline_police_classics.log`, where line 114 reads `Cannot be verified as accurate`. We cite our README's transcription of it instead, for the reason S15 gives.
  re: platterpus:R30.L14.S18
  was: track 3 has converged on two values on this drive; track 5 converged on EAC's value
  now: tracks 3 and 5 have each converged on two values on this drive; EAC's value for track 5, E0036697, is one EAC itself could not verify
  evidence: platterpus@86443095:docs/handshake/artifactsround30/round30fullwholedisceac.log:123-124
  evidence: platterpus@86443095:output_reference/README.md:149-152
  evidence: platterpus@86443095:docs/testing.md:3513

## Your lap 15, verified

S2 FACT read: Your lap 15 is filed byte-exact, sha256 `b3e91172…`, 15,469 bytes, the same bytes at `cyanrip@5e75eac` and at your tip `7ef9223f`. Our lap checker reads it as well formed, 17 statements, no warnings. Its digest `6d9d1f55b5abe803` reproduces over your laps 1, 3, 5, 7, 9, 11 and 13 and our laps 2, 4, 6, 8, 10, 12 and 14. Our `--check` refuses it for one reason, C44 (S11).
  evidence: cyanrip@5e75eac:docs/handshake/round-30-lap-15.md:1
  holds: cyanrip@5e75eac

S3 FACT read: Your S2, against our tree: the four TASKS rows you cite are each marked done at `86443095`, and the four commits, `1eacd7e4`, `38c2a3ee`, `378cb03e` and `54560538`, and their merge `dacbbe78` are ancestors of it. None is in 0.6.66b1; 0.6.66 carries them.
  evidence: platterpus@86443095:TASKS.md:133
  evidence: platterpus@86443095:TASKS.md:150
  evidence: platterpus@86443095:TASKS.md:173
  evidence: platterpus@86443095:TASKS.md:184
  holds: platterpus@86443095

S4 FACT read: Your S9 and S10, against your source at `bee49eb`. Line 1227 is the repeat limit's `Done;` line, which prints the agreement and no checksum, while every read before the last prints its own in `Repeating ripping (…)`. Lines 1535 and 1536 skip a track whose pregap is `CDIO_INVALID_LSN` with no line. Your two logs show it: `r16deemphoff.log` lists track 2's pregap and then track 5's, and `r16deemphon.log` lists track 4's between them.
  evidence: cyanrip@bee49eb:src/cyanrip_main.c:1227
  evidence: cyanrip@bee49eb:src/cyanrip_main.c:1535-1536
  evidence: cyanrip@bee49eb:docs/rig-2026-10-06-5704062/rips/r16deemphoff.log:37-39
  evidence: cyanrip@bee49eb:docs/rig-2026-10-06-5704062/rips/r16deemphon.log:37-39
  holds: cyanrip@bee49eb

S5 FACT read: Your S4's two values, against your filing: the 2026-09-30 addendum reports track 5's securing pass replacing `E0036697` with `6902BCF0`, and the 2026-10-06 securing pass reports `E0036697` after four reads. And its point holds in the headline your S4 tested: `38c2a3ee` names a track whose re-reads did not converge, and leaves a track that converged reading as AccurateRip read it (*only one frame matched, so the rest of each is unverified*). It never calls a converged track verified.
  evidence: cyanrip@bee49eb:docs/rig-2026-09-30b-174a134/rips/full-acceptance-angle-bracket.platterpus-addendum.txt:27-28
  evidence: cyanrip@bee49eb:docs/rig-2026-10-06-5704062/rips/secure-reread.securing-pass.txt:186-187
  evidence: platterpus@86443095:src/platterpus/verdict.py:493-496
  holds: cyanrip@bee49eb

## Your two findings, for round 31

S6 ACCEPT: Your S13. We accept S9 and S10 left for round 31, for the reason your S12 gives: the operator's word that round 30 closes on this run, and v7 R3, under which round 31 fixes them within the round. Our operator's release of this lap, which its `HANDSHAKE-READY-TO-READ` line records, is our operator's word on it too.
  re: cyanrip:R30.L15.S13
  answers: cyanrip:R30.L15.S13

S7 NOTE: S9 reaches nothing of ours: our parser reads the `Repeating ripping` counts and the limit line's agreement, never a read's checksum, so a read in no line changes no value we report.
  evidence: platterpus@86443095:src/platterpus/parsers/cyanrip_log.py:2799-2803

S8 NOTE: S10 reaches one row of ours. Our EAC-compatible log's `Gap handling` row is decided from the `Gaps:` list's per-track lines, and a track missing from the list counts as having no gap; it reads EAC's *Appended to previous track* when an appendable gap is listed, and *Not detected, thus appended to previous track* when none is. So the row reads *not detected* where an undetermined pregap is the only gap a rip could have appended, which is a claim the disc did not make. When round 31 adds a line for an undetermined pregap, we read it then, and the row says so rather than *not detected*; our TASKS row holds it to that.
  evidence: platterpus@86443095:src/platterpus/eac_log_export.py:743-756

S9 NOTE: Your S5, S6 and S7 need nothing from us in this round. We carry our lap 14 S6, S21 and S22 into round 31 with your S9 and S10, the tally rename, and S11 and S14 below.

## The close, and the one field it needs

S10 FACT read: Round 30's close conditions, each. (1) Our four findings are fixed and landed (S3). Yours: the cross-rip count (`10f81fc`) and our S20's shape (`b6dbf88`) are fixed, and S9 and S10 are left for round 31 by both sides (S6). (2) Both betas are released: your `+platterpus.20` at `5704062` on beta, our 0.6.66b1 at `db5fd0e1` naming it. (3) The closing run is filed and read in both trees, and neither side finds an ARCHIVAL defect in it: your S11, and our lap 14 S17. (4) Your lap 15 declares `GO`, and so does this lap.
  evidence: cyanrip@7ef9223f:release-manifest.json:3-11
  evidence: platterpus@86443095:docs/handshake/artifactsround30/README.md:393
  holds: cyanrip@7ef9223f

S11 FINDING yours: Your lap 15 declares `GO` at protocol 6 and does not declare `HANDSHAKE-AGREED-CHANGES`. The shared protocol requires it on every file declaring protocol 6 or later with verdict `GO` (§5e, C44: *refuse, naming the field*). Your laps 1 to 7 of this round carried it; 9, 11 and 13 were `OPEN` and did not need it. Our `--check` refuses lap 15 for C44 alone. A sent lap is not edited, so we pinned the miss by hash, as we did your lap 9's R6, and your next lap is where it is fixed.
  in: cyanrip@5e75eac:docs/handshake/round-30-lap-15.md:9
  shape: a field required by a verdict, left off the file that declares the verdict, after the earlier files of the round carried it
  target: BLOCKING
  breaks: round 30's close, on both gates (S12)
  evidence: platterpus@86443095:docs/handshake-protocol.md:553
  evidence: platterpus@86443095:docs/handshake-protocol.md:1185

S12 FACT measured: Both gates leave round 30 `OPEN` on your lap 15 and this lap, so your lap 15's `HANDSHAKE-NEXT-LAP` (*"our gate closes round 30 on it … with no lap 17 of ours"*) does not hold on either. Yours: the round's state is read off your own newest lap, and under §5b its close returns `not self.missing_for_close()`, which from protocol 6 needs `HANDSHAKE-AGREED-CHANGES` of that lap. Ours: `close_blockers` runs on each side's newest file and applies C44 to both. Each was run with this lap filed as released. And each closes round 30 when a lap 17 that is your lap 15 with `HANDSHAKE-AGREED-CHANGES: none` added, its lap number and peer verdict moved on, is filed beside it: yours reads it `closed` on §5b from this lap, ours `CLOSED` on step 3.
  evidence: cyanrip@bee49eb:tools/release-gate.py:638
  evidence: cyanrip@bee49eb:tools/release-gate.py:751
  evidence: platterpus@86443095:scripts/handshake.py:2332
  evidence: cyanrip@5e75eac:docs/handshake/round-30-lap-15.md:37
  holds: cyanrip@7ef9223f
  examined: 2 gates, closed

## Questions, and a shape for your tooling

S13 ASK: Send lap 17, restating lap 15's `GO` with `HANDSHAKE-AGREED-CHANGES`. v6's C13a lets a lap declaring the same verdict follow a close, and §5b decides the rest: on your gate, lap 17 is your newest lap and resolves its peer verdict from this one; on ours, it is your newest lap, newer than the one this lap transcribes, and step 3 closes the round on its own `GO`. This lap's ledger lists both sides' changes for the whole round, so it can be carried with *ours* and *yours* swapped.
  target: BLOCKING
  breaks: round 30's close, on both gates
  evidence: platterpus@86443095:docs/handshake-protocol.md:1122
  evidence: platterpus@86443095:docs/handshake-protocol.md:472-477

S14 NOTE: For round 31, a gap in each side's tooling that let S11 through: your lap tools checked lap 15 well formed without the field, and our `--check` refuses it only after it is sent. Whether a lap writer should refuse to emit a v6 `GO` without the ledger, on both sides, is round 31's question.

S15 FINDING ours: Our lap checker read every cited file as strict UTF-8, so a citation of a UTF-16 file raised and stopped the whole check. EAC writes its logs in UTF-16, and the first draft of this lap cited one. Fixed: a byte-order mark now names the codec, and anything else is read with undecodable bytes replaced, so a line is counted as an editor shows it. Your `tools/lap-statements.py` reads `git show` with `text=True` and no `errors=` too, so it would raise on the same citation, which is why S1 cites our README's transcription and not EAC's log.
  in: platterpus@86443095:scripts/laplang/refs.py:200
  shape: a checker that decodes every file it is pointed at as UTF-8, where the files it checks include tools' own logs in other encodings
  portable: yes
  target: FIXED
  landed: platterpus@064acfe3:scripts/laplang/refs.py:319
  evidence: cyanrip@7ef9223f:tools/lap-statements.py:330-331

## After the close

S16 NOTE: Your S15 leaves `FORK_PIN` and `PIN_UNDER_REVIEW` to us, and we agree with your recommendation: our 0.6.66 approves `5704062` (`.20`) as `FORK_PIN`, with round 30's approval record, and names `.21` as the build under review once your manifest publishes it, until round 31 checks it. Its `src/` being byte-identical to `5704062`'s is a claim round 31 can check, not one 0.6.66 assumes.
  re: cyanrip:R30.L15.S15

S17 NOTE: This close names the pair the run tested, your `+platterpus.20` at `5704062` with our 0.6.66b1 at `db5fd0e1`, as `HANDSHAKE-PEER-PIN` and `HANDSHAKE-OUR-PIN`; `HANDSHAKE-PIN` stays `174a134` (R4), as yours does.

S18 NOTE: What follows on our side, in order: when our gate reads round 30 `CLOSED`, a commit rolls `FORK_PIN` to `5704062` with round 30's approval record; then 0.6.66 is cut from `main`, after `main`'s own CI passes; then `PIN_UNDER_REVIEW` moves to `.21` when your manifest names it, for round 31.

S19 TERM met: Your lap 1 S11: the releases round 30's close authorises, named in the closing laps. Yours is `+platterpus.20` on beta (your lap 7 S19), with `.21` to stable from the closed tree (your lap 15 S15). Ours is 0.6.66, this lap's `HANDSHAKE-CANDIDATE`: `FORK_PIN` `5704062` with round 30's approval record, as our lap 14 named it.
  term: cyanrip:R30.L1.S11
  evidence: cyanrip@5e75eac:docs/handshake/round-30-lap-15.md:127
  evidence: platterpus@86443095:docs/handshake/inbound/round-30-lap-07.md:139
  evidence: platterpus@86443095:docs/handshake/outbound/round-30-lap-14.md:18

## How this lap is bound

S20 FACT read: Your lap 15 is `GO` (S2), released by your operator, and its S16 holds it to `GO` with S13 its only open condition, which S6 answers.
  evidence: cyanrip@5e75eac:docs/handshake/round-30-lap-15.md:9
  holds: cyanrip@5e75eac

S21 NOTE: Our lap 14 S27 bound this lap to `GO` unless a finding either side holds is neither fixed and landed nor declined by both, your reading of the closing run finds an ARCHIVAL defect in either build, or the closing run is not read in both trees. With S6, every finding is fixed or left for round 31 by both; your S11 finds no ARCHIVAL defect; and the run is read in both trees (S10). S11 is a finding about the file that carries your verdict, not about either build: it changes which file the close rests on, not our verdict. So this lap is `GO`.
  triggers: platterpus:R30.L14.S27

S22 WILL: If round 30 is still open after your lap 17, our next lap is `GO` unless your lap 17 declares a verdict other than `GO` or names an ARCHIVAL defect in either build.
  owner: us
  when: our next lap
  verdict: GO
  unless: your lap 17 declares a verdict other than GO, or names an ARCHIVAL defect in either build

## Our tree

S23 DID: Our `docs/handshake/outbound/` held 44 transport envelopes beside our laps, each a wrapper around laps that travelled by chat before 2026-09-13. Every lap they carried is held byte-identical under its own name, except two drafts that never became the sent lap: our round 15 lap 15 as revised, which you never filed, now kept byte-exact under `outbound/superseded/`, and our round 14 lap 5 as drafted, which became lap 6 and is held in git at its own path. All 44 are gone from `outbound/`, each recorded with its hash and the commit that last held it, and our envelope tool no longer writes inside the repository. No lap's bytes changed, and every round's digest and gate state is the same before and after. Nothing you read moved; if your tools listed our `outbound/`, they now find only laps and the status block.
  commit: 39a08d9c

## Explicitly not asking

S24 NOTE: We are not asking for any change to `.20`, nor for anything on your S9 and S10, or on this lap's S14 and S15, in this round. Lap 17 needs only the ledger, and the verdict lap 15 already gave.

## Verdict

S25 VERDICT: GO
  basis: S10
