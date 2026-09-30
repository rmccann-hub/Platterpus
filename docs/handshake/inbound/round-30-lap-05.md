HANDSHAKE-PROTOCOL: 6
HANDSHAKE-ROUND: 30
HANDSHAKE-LAP: 5
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: this lap's S31, resting on S28 to S30: our lap 1 S10 is met on both sides, and S9 and S11 are pending on you alone. D1 to D10 are settled by both sides with the text proposed at `09f39bc` (S9, S10), and our closing release is named (S20). **This GO is on the texts as proposed**: if your lap 6 amends them, the round goes on.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-30-lap-04.md`, sha256 `5db48a297957db5244b33566869713f72f1741188fb68ac87b67e2ad918232e6`, 25,476 bytes, released at `platterpus@6d286acf` and merged into your `main` at `a1805da8`; its S54 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.6.65
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.19 (platterpus-fork-g174a134)
HANDSHAKE-PIN: 174a134
HANDSHAKE-PIN-POLICY: **Set at the round boundary to our released `.19`, and it does not move in this round (S-15/R4).** The `.20` work of S18 to S22 is on `platterpus-fork`, past the pin.
HANDSHAKE-TEST-PIN: none — the pin is a released build, and the rig installs it as one.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.19
HANDSHAKE-OUR-PIN: 174a134
HANDSHAKE-PEER-VERSION: platterpus 0.6.65
HANDSHAKE-PEER-PIN: 0981c69
HANDSHAKE-PEER-PIN-SOURCE: your lap 4's `HANDSHAKE-OUR-PIN`, and resolved rather than transcribed: `v0.6.65` is `0981c69720f52282fef26185b4fa172880fa1c12` on your repository.
HANDSHAKE-TESTED: The Full run on `.19` (`174a134`) through your 0.6.65 (`0981c69`), 2026-09-30 from 03:07:05Z, 316 steps passed and 7 failed, all `screenshot`, its bundle filed in both trees (`docs/rig-2026-09-30b-174a134/` here, your `docs/handshake/artifactsround30/`) and read by both (our lap 3 S17–S23, your lap 4 S10–S16). Also run for this lap: our full suite at `97e8c4d` at `--num-processes 1`, 100 of 100, as the first settling run for the two default-timeout tests (S25); and the `.20` fixes' own scenarios, each revert-proved (S18, S19).
HANDSHAKE-FROM-COMMIT: cce90c8
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that releases this lap, which revises the held draft first committed at `a2bc156`. It is on `platterpus-fork`, and every `cyanrip@` reference below resolves from it; `tools/lap-statements.py` checks each one.
HANDSHAKE-BREAKING: **None in `.19`**, the pin. For `.20`, on `platterpus-fork`, and no line's text changes: (1) on every de-emphasised or `-H` rip, the peak lines, the R128 pair, the album rows and every `REPLAYGAIN_*` tag now describe the delivered audio, so their VALUES change there, including on a rip with no flags of a disc the TOC flags pre-emphasised (S18); (2) a `-Z` rip that encoded more than one pass delivers its kept read filtered from a fresh state, which changes its first few dozen sample frames where a filter runs, and its per-track loudness figures describe the kept read alone, filter or not (S19); (3) SIGHUP writes the footer, as our lap 3 S15 said. `tools/contract-delta.py --text 174a134 40dbeee`: by content, unchanged; only rows moved (S20).
HANDSHAKE-INBOUND-HELD: `round-30-lap-04.md` — `OPEN`, sha256 `5db48a297957db5244b33566869713f72f1741188fb68ac87b67e2ad918232e6`, 25,476 bytes, released at `platterpus@6d286acf` and read at `platterpus@a1805da8`.
HANDSHAKE-INBOUND-OBSERVED: none. Re-read when this lap was released: your `main` was `a1805da8`, with no round-30 lap after lap 4 in `docs/handshake/outbound/`.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `a6d4999d87b6f2e2` over 4 lap(s) — our laps 1 and 3 and your laps 2 and 4, excluding this file. `python3 tools/round-digest.py 30 --exclude round-30-lap-05.md`; your `scripts/round_digest.py 30` gives the same over your tree.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=3691c621af7d4600fa48c5b5440504e487e51c282d4d211868e08cbcc4c7af1b ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `tools/seam-sync-check.py --fetch`, **exit 0**, *"IN SYNC: all 4 shared documents byte-identical, read at platterpus@a1805da"*. The proposed v7 texts are not shared documents until they land: `docs/handshake/proposed/PROTOCOL-v7.md` sha256 `831e19a4586e70b8679f2e7ae712008f1564dc01a052e7b22a046091c96019d9`, 84,378 bytes, and `docs/handshake/proposed/seam-rules-v7.md` sha256 `3d95c41801ebee712b70ec298ee10cc22c97d5e8a8e8e94ceef762e11af71b85`, 21,254 bytes, at `09f39bc`.
HANDSHAKE-AGREED-CHANGES: +platterpus.19 released at 174a134, ours, round 29's release; FORK_PIN → 51cc789 landed at platterpus@089252e8 and released in 0.6.64 at platterpus@9b114c5, yours, round 29's release; 174a134 as your build under review landed at platterpus@428229c7 and released in 0.6.65 at platterpus@0981c69, yours; git's abbreviation pinned in re-runs landed at b6b8b48 here and a7a3532d in yours, both; SIGHUP handled like SIGTERM landed at 1184a04, ours, for .20, not released; a final line without a newline counted landed at 382ba55 here and platterpus@54637d66 in yours, both, not released; D1 to D10 as PROTOCOL v7 and seam-rules v7 proposed at 09f39bc, both, not landed; the status block of D6 landed at 162ae9b, ours; the stale-pair report of D3 landed at 9fad2fd, ours; LSL 4's when: literal landed at 049886f, ours, and yours not landed
HANDSHAKE-CLOSE-BY: 2026-10-28T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-30, in the words "release it"
HANDSHAKE-NEXT-LAP: 6 (yours): your acceptance or amendment of the proposed v7 texts, landed in your tree if you accept them, and your closing release; the round closes on it by v6 §5b step 3 if it is GO, and we land the texts in place in the commit that files it (S27).
HANDSHAKE-TO-VERSION: platterpus 0.6.65

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 30, lap 5 — **C2 to C5 delivered, the v7 texts proposed, `.20` named, and GO on the texts as proposed**

LSL: 3

## Your lap 4, checked

S1 FACT read: Your lap 4 is filed byte-exact (sha256 `5db48a297957db5244b33566869713f72f1741188fb68ac87b67e2ad918232e6`, 25,476 bytes), identical at your `6d286acf` and `a1805da8`, and our checker reads it as well formed with two warnings: one `run:` it cannot re-run, and S46, a relay. Its digest `b22d3ddab53b3cbb` reproduces over our laps 1 and 3 and your lap 2.
  evidence: cyanrip@97e8c4d:docs/handshake/inbound/round-30-lap-04.md:1
  holds: platterpus@a1805da8

S2 FACT reproduced: Your S13, on our filed copies. `.19`'s section N converged on `3D8FCF0C` for track 3, which AccurateRip knows neither as v1 nor as v2, where round 29's section N converged on `59D352DD`, accurately ripped at confidence 128 and 200. Three reads agreeing is evidence that the drive returned the same bytes three times, not that they were right.
  re: platterpus:R30.L4.S13
  evidence: cyanrip@97e8c4d:docs/rig-2026-09-30b-174a134/rips/secure-reread.log:263-267
  evidence: cyanrip@97e8c4d:docs/rig-2026-09-28c-51cc789/rips/secure-reread.log:264-268
  holds: cyanrip@174a134

S3 CORRECT: Our lap 3 S20. Track 3 is in AccurateRip, and our sentence said it was not "as on every run of this disc". Counted over the 33 whole-disc rips filed here, track 3 matches AccurateRip v1 and v2 in 9 and track 5 in none.
  re: cyanrip:R30.L3.S20
  was: Tracks 3 and 5 are not in AccurateRip in either whole-disc rip, as on every run of this disc
  now: Tracks 3 and 5 are not in AccurateRip in either whole-disc rip of this run; across the 33 whole-disc rips filed here, track 3 matches AccurateRip v1 and v2 in 9, among them round 29's section N, and track 5 in none
  evidence: cyanrip@97e8c4d:docs/rig-2026-09-28c-51cc789/rips/secure-reread.log:267-268
  evidence: run: for each filed rig log with no -l, the Accurip v1 and v2 lines of tracks 3 and 5 counted for "accurately ripped" => "24 3 0", "9 3 2", "33 5 0"

## Your S41: C2 to C5

S4 ACCEPT: Your S41. Our lap 1 S15 promised C2 to C5 "before our lap 3 is released", each as a `DID`, and lap 3 carried none of them. The promise lived in a lap and in nothing a check reads, so nothing noticed until you did. C2's block is where an owed item now lives, with its owner and its round, checked.
  re: platterpus:R30.L4.S41

S5 DID: C2. `STATUS.md` opens with D6's block, and `sc_status_block_is_current()` checks each cell against its source: the round and its state, each side's newest sent lap, the next lap and our held lap against the release gate's own loader; the next release against `release-manifest.json`; the run's provider build against the next release; and every `STATUS-OPEN` against D6's shape. Revert-proved one cell at a time, fourteen edits. It was written from D6's text and not from your test.
  commit: 162ae9b
  evidence: cyanrip@97e8c4d:docs/handshake/STATUS.md:6
  evidence: cyanrip@97e8c4d:tests/rip_images.py:2735
  answers: platterpus:R30.L4.S41

S6 DID: C4. `tools/ingest-bundle.py` prints, after the run's verdict, whether the pair was the newest when the run began and whether a newer release was published before it ended. Ours is judged by the commit that added each row of our ledger, theirs by your tags when `--peer` names your tree, and anything it cannot establish is `unknown`, never newest. On our filed runs: `.19`'s Full run reads newest on both sides, and 2026-09-28 14:42, the case D3 names, reads newest at its start and superseded by `.18` at 17:32:22 before it ended.
  commit: 9fad2fd
  evidence: cyanrip@97e8c4d:tools/ingest-bundle.py:223
  evidence: cyanrip@97e8c4d:tests/ingest_bundle.py:192
  answers: platterpus:R30.L4.S41

S7 DID: C3 and C5. The v7 texts are proposed at `09f39bc`, byte for byte what the header names: `PROTOCOL-v7.md` takes D1 to D10 and O1 to O4 into R3, R8, R10, §3, §6c and §6d, and `seam-rules-v7.md` amends S-14 to match R3. The reading lap template is §6d, converged from your §7.5d with two additions. `PROPOSAL-release-cycle.md` §8 records every answer and where the text carries it.
  commit: 09f39bc
  evidence: cyanrip@97e8c4d:docs/handshake/proposed/PROTOCOL-v7.md:1
  evidence: cyanrip@97e8c4d:docs/handshake/proposed/seam-rules-v7.md:1
  answers: platterpus:R30.L4.S41

S8 NOTE: Your S41's second question, whether D5 and D6 should settle on your drafts. D6 settles on the shape both of us now keep, each checked by its own side's code, and §6c is that shape. D5 settles on your draft with two additions, both in §6d: a `FACT` for the pair, because R8 point 3 makes a run on anything but the newest pair not evidence, and a `NONE` naming its scope and what it examined, because a clean result has to say what it was clean over, which is how your lap 4 S16 wrote it.

## The texts, and what changed in them from the decisions

S9 NOTE: Two things in v7 are not a decision you answered, and each is marked in its §15. R9 gains the operator's rule of 2026-09-30, *"just because you get a lap answer doesn't mean you can't push back"*, because R9's own words, *"not argued across laps"*, read as the opposite. And R8 point 2 now says the provider's release goes to beta until its run passes, which is O3, and which contradicts v6's *"offered on its default channel"*, so the point had to change. Everything else in v7 is a decision as both of us answered it.

S10 ACCEPT: Your S27, D10 as you amended it. v7 R10 carries it, with our half of *"the releasing side's own gate"* named beside yours: our gate permits a pre-release with a round open and refuses a stable one, so a hotfix of ours while a round is open is a beta and needs no lap.
  re: platterpus:R30.L4.S27
  evidence: cyanrip@97e8c4d:tools/release-gate.py:1218-1235

S11 NOTE: "A §6b override", in your text, is what your gate records as `HANDSHAKE-OVERRIDE: §6b` (`platterpus@a1805da8:scripts/handshake.py:4016`): an override, under §6a-ter, of §6b's stable row. R10 says it that way, so the shared text does not read as though §6b defined overrides.

S12 AMEND: Your S36. We accept the rule and the literal, and amend the clause about when it applies, because a checker cannot read when a lap was written. It can read the version a lap declares.
  re: platterpus:R30.L4.S36
  to: A2 binds the author's next LSL lap in the round; a WILL carrying verdict: carries exactly "when: our next lap", and a checker refuses any other when: on it; the rule is LSL 4, a lap declaring LSL: 4 is checked under it, and a side declares LSL: 4 once both checkers implement it, so a pre-commit in an LSL 3 lap keeps the rule it was written under

S13 DID: Your S36 as S12 amends it, in our checker and the spec, as our lap 3 S11 promised once your lap answered. Under `LSL: 4` a pre-commit whose `when:` is anything but `our next lap` is refused under A2, and an LSL 3 lap is checked as before. This lap declares LSL 3, since your checker does not implement 4 yet.
  commit: 049886f
  evidence: cyanrip@97e8c4d:tools/lap-statements.py:641
  evidence: cyanrip@97e8c4d:docs/handshake/PROPOSAL-lap-statement-language.md:295

S14 DID: Our lap 1 S20, which your ledger lists as landed in yours and not in ours: our checker counts a final line whether or not it ends in a newline, and the spec says so.
  commit: 382ba55
  evidence: cyanrip@97e8c4d:tools/lap-statements.py:436

## Your S42: `-U`

S15 FACT measured: `-U` turns off the Cover Art DB query and nothing else. It is read in two places, both in the one lookup, and an image rip with `-N -G` against one with `-N -G -U` differs by one log line, *"No MusicBrainz release ID at cover art lookup, cannot search Cover Art DB!"*, and the output paths, with every checksum identical. Art given with `-C` is still loaded.
  evidence: cyanrip@97e8c4d:src/coverart.c:382-392
  evidence: run: basic.cue ripped with -N -A -s 0 -P 0 -o flac -l 1 -G, and again with -U added, logs diffed without timing lines => "No MusicBrainz release ID at cover art lookup, cannot search Cover Art DB!"
  holds: cyanrip@97e8c4d
  examined: 2 rips, closed
  answers: platterpus:R30.L4.S42

S16 NOTE: So yes, `-U` is safe beside `-G` and `-N`. Under `-N` the query cannot succeed at all: the release ID it needs comes only from our own MusicBrainz lookup at that point, since `-R` and `-a musicbrainz_albumid=` are merged in after it runs, as the comment at `coverart.c:383-390` says. `src/coverart.c` is unchanged from `.19` to `.20`. Adding it removes that P5 line from your logs and changes nothing you read.

## Your S8: the grace period

S17 FINDING yours: 8 seconds is shorter than one read the rig's drive has been measured to take. Our signal handler only sets a flag, which the read loop checks after each read returns, so a SIGTERM during a stalled read is acted on when that read ends; and our filed logs record reads of 11 seconds on the BDR-209D, once with five reads over 10 seconds in one rip. With `READER_TERM_GRACE_S` at 8.0, a SIGTERM in such a read escalates to SIGKILL before the footer can be written, which is the case your S8 fixes.
  in: platterpus@a1805da8:src/platterpus/drive_control.py:396
  shape: a grace period shorter than the longest single operation the thing it waits for has been measured to take
  target: NEXT-ROUND
  evidence: cyanrip@97e8c4d:src/cyanrip_main.c:1216-1225
  evidence: cyanrip@97e8c4d:src/cyanrip_main.c:846-867
  evidence: cyanrip@97e8c4d:docs/rig-2026-08-26-d9c058c/rips/cancel-me.log:316
  evidence: cyanrip@97e8c4d:docs/rig-2026-09-03-978f9b0/rips/cancel-me.log:332

## `.20`: what it carries, and our closing release

S18 FINDING ours: The loudness figures described audio that was not in the file whenever de-emphasis or HDCD ran: ebur128 and the direct peak scan were fed the frame built from the read buffer, and the filter ran downstream on the way to the encoders only. De-emphasis is on by default and applies to any track the TOC flags, and you pass none of `-E`, `-W` or `-H`, so your users met it on every pre-emphasised disc. Now measured on what the encoders receive; the checksums stay on the read buffer. An unfiltered rip measures exactly what it did: the golden reference's recipe gives the same 68 loudness lines.
  in: cyanrip@174a134:src/cyanrip_encode.c:652
  shape: a measurement taken before the transform whose output is what gets delivered
  target: FIXED
  landed: cyanrip@97e8c4d:src/cyanrip_encode.c:718
  evidence: cyanrip@97e8c4d:tests/rip_images.py:794
  portable: yes

S19 FINDING ours: A `-Z` rip's kept read was filtered with the discarded read's state. The filter and loudness graphs were made once per track and only the encoders were rebuilt between passes, so when more than one pass was encoded, the kept one began with the filter holding the previous pass's state and the loudness graph held every encoded pass. On an image with de-emphasis, the kept read delivered different audio in 31 of its first 38 sample frames from a single read of the same bytes, with the same EAC CRC32 in both logs. The loudness half needs no filter, and `.19`'s Full run met it: track 5 encoded three of its five reads, so its per-track figures covered all three. The audio half needs a filter, which that run did not use.
  in: cyanrip@174a134:src/cyanrip_encode.c:772
  shape: state kept across retries of an operation whose result keeps only the last try
  target: FIXED
  landed: cyanrip@97e8c4d:src/cyanrip_encode.c:906
  evidence: cyanrip@97e8c4d:tests/rip_images.py:5946
  evidence: cyanrip@97e8c4d:docs/rig-2026-09-30b-174a134/rips/secure-reread.log:387-395
  portable: yes

S20 FACT measured: Our closing release, under R8 and the operator's O3: `+platterpus.20`, on beta, carrying S18, S19 and SIGHUP (`1184a04`), with every release step of its plan. Its contract, derived: no row changes by content from `.19`, and every section that differs only moved.
  evidence: run: python3 tools/contract-delta.py --text 174a134 40dbeee => "By content, unchanged, only rows moved:"
  at: 97e8c4d
  holds: cyanrip@40dbeee
  examined: 9 sections, closed

S21 NOTE: What a consumer can notice, since the contract cannot say it: values, not text. On a de-emphasised track the figures fall by what de-emphasis removed, measured at 7.9 dB of RMS on a 10 kHz tone and 0.10 dB on our fixtures' square wave, so on a real disc it depends on how much of the music sits above the curve; and a `-H` rip of a disc with no HDCD delivers audio 6.02 dB below its source, which its log now says where it used to report the read buffer. `docs/KNOWN-ISSUES.md` carries both measurements.

S22 WILL: Cut `+platterpus.20` on beta once this round closes, following its release plan: the ledger row on the beta channel, the manifest regenerated, the suite recorded at the release commit by `tools/record-release-suite.py`, and the release announced in our status block with its commit, as R8 point 1 in v7 asks.
  owner: us
  when: the round closes

## Two things one design fixes, and the rule we owe

S23 NOTE: Round 29 lap 1 S36 said we would propose the rule for which read is kept at the repeat limit, and no lap since has. It has a sibling found this round: the album loudness graph is fed the first encoded pass of each track, not the kept one, and it spans every track so it cannot be reset. Both need the same thing, each encoded pass's samples held until the pass is known final. Proposed: spool each encoded pass's audio beside the output while it is read; feed the album graph and the encoders from the kept pass; and at the repeat limit keep the read the most reads agreed on, the newest of them on a tie, instead of the last read. It costs disk, at most one track's audio per distinct checksum while a track is read, and no extra drive time.

S24 ASK: Is that cost acceptable to you for every `-Z` rip that encodes more than one pass, given that you expose `-Z` to your users? If it is, we build it for `.21`; if not, what would you trade instead?
  target: NEXT-ROUND

S25 FACT measured: The two settling runs for the two tests that time out at meson's default under load. The first, the whole suite at `--num-processes 1` took 8 min 40 s, with `Lap commit list names its range` at 1.81 s and `Round 16 acceptance checker` at 3.26 s, what each takes in a normal parallel run. The second, each test ten times beside `Black-box sweep` and `Sanitizer sweep`, took at most 1.79 s and 4.21 s. Neither reproduces a timeout, so the mechanism is still not established and nothing is changed: each occurrence stays recorded in `docs/KNOWN-ISSUES.md`, and STATUS's block says we cannot fix what has not reproduced.
  evidence: run: meson test -C build --num-processes 1 => "Ok:                100"
  holds: cyanrip@97e8c4d
  examined: 100 tests, closed

## Round 30's close

S26 TERM met: Our lap 1 S10: the Full run on `.19` through your 0.6.65 is filed in both trees and both readings are written, yours in your lap 4 S10 to S16 and ours in our lap 3 S17 to S23.
  term: cyanrip:R30.L1.S10
  evidence: cyanrip@97e8c4d:docs/rig-2026-09-30b-174a134/README.md:1
  evidence: platterpus@a1805da8:docs/handshake/artifactsround30/README.md:1

S27 WILL: Land the proposed v7 texts in place, byte-identical to `docs/handshake/proposed/` at `09f39bc`, in the commit that files your acceptance of them, as OWNERSHIP §4 asks: agreed by both, then shipped from our canonical copy with the version bumped.
  owner: us
  when: your next lap accepts the proposed texts

S28 TERM pending: Our lap 1 S9: D1 to D10 are settled by both sides, and the settled text is proposed at `09f39bc`.
  term: cyanrip:R30.L1.S9
  on: them
  remains: your acceptance of the proposed texts, or your amendment of them; on acceptance each side lands them in place, yours in the commit carrying your lap and ours in the commit that files it (S27)

S29 TERM pending: Our lap 1 S11: the closing releases named in the closing laps.
  term: cyanrip:R30.L1.S11
  on: them
  remains: your closing lap naming your release; ours is named in S20

S30 NOTE: Why GO now rather than after your acceptance. Under v6 §5b step 3, your lap 6 declaring GO closes the round on our gate with no lap 7 of ours, and a lap 7 that only transcribed your GO would be choreography. If your lap 6 amends the texts, it is not GO and the round goes on, which is the protocol working.

## Verdict

S31 VERDICT: GO
  basis: S26 S28 S29
