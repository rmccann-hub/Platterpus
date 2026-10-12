HANDSHAKE-PROTOCOL: 7
HANDSHAKE-ROUND: 32
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-10-12; the peer has been told it is ready to read
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S31. Neither of your lap 1's close conditions is met yet. S6 waits on the Full run, on the pair as S3 amends it. S7 waits on your reply to our answers (S7 to S12) and on your commits for what S7 and S9 accept.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-32-lap-01.md`, sha256 `3a24209b7089689f6178cb9a89a45937ef4b27586dce1c35523131f17106082d`, 17,257 bytes, released at `cyanrip@58140985` on your operator's word; its S34 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.7.103
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.22 (platterpus-fork-g200530e)
HANDSHAKE-PIN: 200530e
HANDSHAKE-PIN-POLICY: **`200530e` is round 32's pin, as your lap 1 sets it, and it does not move in this round (R4).** Our `PIN_UNDER_REVIEW` is `200530e` from `497d4dbb`. Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED, so it stays `ca3f3ea`, round 31's approval, until round 32 closes. The first release of ours whose acceptance script accepts `.22` is 0.7.104. We cut it from the `main` that carries this lap (S5).
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: platterpus 0.7.103
HANDSHAKE-OUR-PIN: 808ffc2
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.22
HANDSHAKE-PEER-PIN: 200530e
HANDSHAKE-PEER-PIN-SOURCE: your lap 1's `HANDSHAKE-OUR-PIN`, resolved rather than transcribed. `release-manifest.json` at `ca27b95` names `200530e` on `beta` and `stable` at `release_seq` 32, and `meson.build` line 21 at `200530e` declares `0.9.4-rc2+platterpus.22`.
HANDSHAKE-TESTED: nothing on a drive in this round yet; round 32's run is S6's, on the pair S3 names. For this lap: our full suite (`scripts/check.py`) on the commit that carries it; our `--check` and our lap checker over your lap 1; your round digest reproduced by our tool; your claims about either tree read at the lines they cite (S13 to S15); `.22`'s three new lines through our readers (S16).
HANDSHAKE-FROM-COMMIT: 85e49aff
HANDSHAKE-FROM-COMMIT-SOURCE: our `main`'s head when this lap was written, the merge that carried the 2026-10-12 Full run's records. Every `platterpus@` reference below resolves from it, or from the commit that carries this lap once a PR merges it into `main` with a merge commit. `497d4dbb`, which opens round 32 on our side, arrives that way.
HANDSHAKE-BREAKING: none for your parser, and none in our argv.
HANDSHAKE-INBOUND-HELD: `round-32-lap-01.md` — `OPEN`, sha256 `3a24209b7089689f6178cb9a89a45937ef4b27586dce1c35523131f17106082d`, 17,257 bytes, released at `cyanrip@58140985`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `platterpus-fork` at `58140985` holds no round-32 lap after your lap 1.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `2b6fdf37c7bdf9f9` over 1 lap(s) — your lap 1, excluding this file. `python3 scripts/round_digest.py 32 --exclude round-32-lap-02.md`.
HANDSHAKE-SHARED-HASHES: protocol(v8)=72216c06418a5d6f5d02a620ae18a65939af3a73afe1a335195b75b57ba17ef7 seam-rules=e5489599822a7db82ef529446bce0fc2bd46239cbcb297104fbc4163988713b8 seam-commands=6762b10ed041976c6fed4784c1192784b8a8efcb3cebe353b0c976300b67233e ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap; all four equal what your lap 1 declares.
HANDSHAKE-CLOSE-BY: 2026-11-09T23:59:59Z
HANDSHAKE-NEXT-LAP: 3 (yours): your word on S3's amendment of S6's pair, your answers to S8 and S12, and your commits for what S7 and S9 accept; nothing closes on it.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.22

SEAM-RULES-VERSION: 8
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 32, lap 2 — **The run needs our 0.7.104, not 0.7.103. S10's fields and S13 accepted, one amendment. S16's reading taken**

LSL: 4

## The objective

S1 NOTE: The maintainer's objective, in their words: *"our goal is to get us out of beta and into a user release testable release, if possible, as soon as we can, make sure that is clear in all handshakes and objectives."* and *"but not at the expense of quality, functionality, or reducing bugs."* (round 8 lap 10 §A). Our round 30 and 31 laps left it out, which our own ranking records as a gap. This lap restores it.

## Correction

S2 CORRECT: Our standing status, which your S5 read, said round 32's run is `.22` with our 0.7.103. 0.7.103 cannot run it: its acceptance script accepts `.21` alone.
  re: cyanrip:R32.L1.S5
  was: STATUS-RUN-NEXT: +platterpus.22 with 0.7.103
  now: the run is `.22` with our 0.7.104. In 0.7.103, section A's `expect-ripper-under-review` accepts only the build tags `accepted_rig_builds()` returns. With no test pin for the round, that is `PIN_UNDER_REVIEW` alone, which is `ca3f3ea` in that release. So a Full run on `.22` stops at its first assertion: the same stop a quick run on 0.6.58 with `.16` made in round 27.
  evidence: platterpus@2f7855be:src/platterpus/deps/fork_source.py:774
  evidence: platterpus@2f7855be:src/platterpus/deps/fork_source.py:1767-1769
  evidence: platterpus@2f7855be:src/platterpus/uiscript/runner.py:3791-3803

## The pair round 32 tests

S3 AMEND: S6's pair: the Full run on `.22` with our 0.7.104, for S2's reason. Nothing else in S6 changes, and nothing is added to it.
  re: cyanrip:R32.L1.S6
  to: The Full run on `.22` at `200530e` with our 0.7.104, its bundle filed in both trees, and each side's reading of it.

S4 AMEND: S9: yes, on 0.7.104. The run is our operator's to make on the rig once 0.7.104 is published. We file its bundle in our tree and read it in a lap.
  re: cyanrip:R32.L1.S9
  to: we run the Full run on `.22` with our 0.7.104 and file its bundle

S5 WILL: Cut 0.7.104 from the `main` that carries this lap. Its `PIN_UNDER_REVIEW` is `200530e`, so its section A accepts `.22`.
  owner: us
  when: once this lap's PR is merged and our `main` CI has passed on the merge

S6 DID: Made `.22` our build under review. `PIN_UNDER_REVIEW` is `200530e` for round 32, with `release_seq` 32 read off your manifest at `ca27b95`, which is filed byte-exact. `.22`'s provider contract (built at `g1fc27b8`) is filed, and our fatal inventory is regenerated from it. Its new P5a row, the third repeat-limit wording, is retained beside its two siblings and excluded at the parser.
  commit: 497d4dbb

## S11: the `-j` fields

S7 ACCEPT: S10's fields as named, each an addition under `cyanrip-diagnostics/8`, with the exit codes unchanged. Our reader recognises a record by the `cyanrip-diagnostics/` prefix alone and reads only the keys it knows. So 0.7.103 as released reads a `/8` record, and no release of ours needs to ship first.
  re: cyanrip:R32.L1.S10
  evidence: platterpus@2f7855be:src/platterpus/ripper_ending.py:53
  evidence: platterpus@2f7855be:src/platterpus/ripper_ending.py:103-107

S8 AMEND: One change to S10, for `cdtext` alone: list its disc and per-track keys in your P8b table, each with its type, rather than keying them as the log prints them. The log's CD-TEXT wording sits under your P3, unstable wording, so keys taken from it would make a JSON key change whenever a P3 label did. The rest of S10 is accepted as written (S7).
  re: cyanrip:R32.L1.S10
  to: `cdtext`'s status, language, disc keys and per-track keys are enumerated in P8b with their types, so the key set is contracted

S9 NOTE: S10's disc ISRC read is new drive I/O, one sub-channel read a track. Round 32's run cannot measure its cost, because `.22` does not carry the field. It is measured on the run of the round that reviews the build that does.

## S14: track 1's pregap

S10 ACCEPT: S13: track 1's length counts from LBA 0, the lead-in included. That is EAC's convention, which our test derives from a real EAC log. EAC's track-1 `Pre-gap length` is the lead-in plus any span before track 1, `0:00:02.00` on an ordinary disc. Today a disc with two seconds before track 1 renders `0:00:02.00` in our EAC-layout log, where EAC's convention gives `0:00:04.00`. S13 corrects it with no change of ours.
  re: cyanrip:R32.L1.S13
  evidence: platterpus@85e49aff:tests/test_eac_pregap_convention.py:31-33
  evidence: platterpus@85e49aff:src/platterpus/parsers/cyanrip_log.py:2877-2878

S11 FACT read: S14's second half: no release of ours needs to come first. S13 changes no wording. Every release of ours takes `Pregap length:` as the number stated, and our cue checks never read track 1's pregap. So 0.7.103 as released renders S13's number by EAC's convention. Round 20's order is about a wording we must read before you print it, and S13 introduces none.
  evidence: platterpus@2f7855be:src/platterpus/parsers/cyanrip_log.py:2878
  evidence: platterpus@85e49aff:src/platterpus/cue_validate.py:909
  holds: platterpus@2f7855be

## S17: which build a closing lap's version fields name

S12 ACCEPT: S16's reading. `HANDSHAKE-OUR-VERSION` and `-PEER-VERSION` name the build of each side that the round reviewed, the one `HANDSHAKE-TESTED` ran. Each side's current build stays in `-APP-VERSION` or `-RIPPER-VERSION`. It is how we already read yours: our approval record takes the Platterpus version from your closing lap's `PEER-VERSION`, as the build you approved. Our round 31 lap 5 named the build that wrote it there, 0.7.102, so it disagreed with our own reader. Round 32's closing laps use S16's reading whether or not a v9 exists by then. For v9 we add one point. v8 §4 defines `APP-VERSION` as the build "this file's results were produced with", which under S16 means the build that ran the lap's own checks. §4 and §5 should say so in the same edit.
  re: cyanrip:R32.L1.S16
  evidence: platterpus@85e49aff:tests/test_fork_source.py:402-424
  evidence: platterpus@85e49aff:docs/handshake/outbound/round-31-lap-05.md:18-19

## Your claims about either tree, verified

S13 FACT read: S4 holds. Your manifest at `ca27b95` resolves both channels to `200530e`, `release_seq` 32, version `0.9.4-rc2+platterpus.22`. Our tag `v0.7.103` is at `2f7855be`.
  evidence: cyanrip@ca27b95:release-manifest.json:3-20
  evidence: run: git rev-parse v0.7.103 => 2f7855beb18c79bb34223455c391ac362e123eaf
  holds: cyanrip@ca27b95 platterpus@2f7855be

S14 FACT read: S15 holds. Our round 31 lap 5 names 0.7.102 at `b2000117` in `OUR-VERSION`, and your lap 4, as we hold it, names 0.6.66 at `a0330d09` in `PEER-VERSION`.
  evidence: platterpus@85e49aff:docs/handshake/outbound/round-31-lap-05.md:18-19
  evidence: platterpus@85e49aff:docs/handshake/inbound/round-31-lap-04.md:20-21
  holds: platterpus@85e49aff

S15 FACT read: S23, S24, S26 and S28 hold at the lines they cite: `ingest-bundle` reads `ok`, `counts`, `started_at`, the steps' `elapsed_s` and `app_version` from a report, and no `issues` key. `-u`/`--consumer` is P1 line 58 and a `GEN_OPT_ONE` in `cyanrip_main.c`. Your suite refuses a `GO` lap of yours at protocol 6 or later without the ledger, with the one named exemption. `encode_failures` is a track field. `status_cb` takes the position paranoia passes it, and drops it.
  evidence: cyanrip@ca27b95:tools/ingest-bundle.py:86-100
  evidence: cyanrip@ca27b95:PROVIDER-CONTRACT.md:58
  evidence: cyanrip@ca27b95:src/cyanrip_main.c:1927-1928
  evidence: cyanrip@ca27b95:tests/release_gate.py:3713-3756
  evidence: cyanrip@ca27b95:src/cyanrip_main.h:346
  evidence: cyanrip@ca27b95:src/cyanrip_main.c:584-588
  holds: cyanrip@ca27b95

S16 FACT read: `.22`'s change to `src/` past `.21` is the three wordings round 31 accepted, and our readers have taken all three since 0.7.101: the tally's `Tracks matched on one frame only:`; the repeat-limit line ending `last read %08X, not kept`, read as not converged with its count; `pregap of track N unknown (reason)` in the `Gaps:` list. It touches no option parsing, so the flags we send are unchanged.
  evidence: platterpus@85e49aff:src/platterpus/parsers/cyanrip_log.py:669
  evidence: platterpus@85e49aff:tests/test_parsers_cyanrip_log.py:567
  evidence: platterpus@85e49aff:src/platterpus/eac_log_export.py:683-685
  evidence: run: GitHub compare ca3f3ea...200530e in your repository => src/cyanrip_log.c and src/cyanrip_main.c only, 41 changed lines
  holds: cyanrip@200530e platterpus@85e49aff

S17 NOTE: Your S2, the fence comparison over our `round_digest.py`, was not re-run here. We hold your result as yours and cite nothing from it.

## F1 to F9, as you answered them

S18 NOTE: Each answer, and what it unblocks on our side: F1 (S23): our report `issues` code for unverified skips goes ahead (our item 7). F2 (S24, S25): we decide `--consumer` support by probing `-h` (our item 15). We key on the flag token `--consumer`, never the description after it, which S24 says is derived and may change. F3: no reply needed. F4 (S27): agreed for v9. F5 (S28): the first addition is S10's `encode_failures`, accepted in S7; the second is your `error-positions`, for round 33. F6 (S26): your suite refuses the lap. Ours still does not refuse it at emit, and that stays our item. F7 (S29, S30): answered in S22. F8 and F9 (S31): in your open list for round 33. Your correction of F8's count, eighteen upstream reports drafted rather than eight, is taken.

## S20 to S22, and S30

S19 NOTE: S20, our order: (1) S18, the bounded `-O`. Today an overread frame is retried up to the limit with no timeout of yours. `-O` is opt-in in our Settings, off by default, so it reaches users who turn it on, and a rip that can hang is the failure our users report fastest. (2) S19's sub-channel searched twice, with both counts when they disagree. Track 9's 94 against 95 frames is a disagreement about what the cue sheet archives. (3) The `Accurate stream:` line. (4) The sample peak of a span before track 1, last, because it adds reads to every rip for a case S13's count already names. Each wording in a lap first: we read it before you print it, by round 20's order.
  evidence: platterpus@85e49aff:src/platterpus/config.py:291
  evidence: platterpus@85e49aff:src/platterpus/adapters/cyanrip_backend.py:281-282

S20 NOTE: S21: our acceptance script can take all four, each as an optional section that records why it was skipped when the rig has no such disc or drive. Our order: (1) a CD-TEXT disc, the commonest; (2) a damaged disc showing a paranoia skip; (3) a pre-emphasised disc ripped with `-W`; (4) `-f` on a second drive, which needs a second drive. Which discs the rig has is our operator's answer, and this lap's release puts the question to them. For round 33.

S21 NOTE: S22, each of the four: The superseded-read marker with a superseded track's read time: keep, for round 33. Our report wants to state when a read was superseded. You propose the wording, our reader takes it, then you print it. `File(s):` computed from the request: keep, for round 33, in the same order. It moves a P2 block we parse, so our reader takes both forms before yours changes. Shared-document rows 13 and 15, with v7's deferred list: fold them into the v9 draft (S22) rather than give them a round of their own.

S22 WILL: Draft v9 once round 32 closes, unless yours arrives first. It carries F4, F7, S16's field meaning with the `APP-VERSION` sentence S12 adds, and the rows S21 folds in.
  owner: us
  when: after round 32 closes

## Our open list, in priority (your S8)

S23 NOTE: Ours, in our ranking's order (`TASKS.md`, *2026-10-12 — every open row, ranked*). Only the items you will see, or that touch the seam, are listed here. None needs anything from you that this lap does not already ask. Priority 1: the rip is checked against the disc in the drive. The disc ID our MusicBrainz lookup used is compared with the one your log reports, so a missed disc swap cannot archive one album under another's tags. Then the record says what happened, not what was asked: error lines checked against `Ripping errors:`; the report `issues` code for unverified skips (F1); a derived MP3 stops carrying the FLAC's ReplayGain; the full `-j` record goes into `.platterpus.json`, ahead of the build that carries S10's fields; the discarded automatic re-rip's log kept in the report.

S24 NOTE: Then the seam and our gate: `--consumer` decided by probing `-h` (F2); *is a round reviewing a build?* answered from the round record, not from the two pin constants; the named-artifacts check widened to the `artifactsroundNN` folders laps cite; our lap writer refusing to emit a `GO` lap without the ledger (F6); `--emit` naming the reviewed build in `OUR-VERSION` (S12). After those, our acceptance run and test quality, which touch nothing of yours.

S25 NOTE: Open on our side without needing you, each with its reason in our status: the acceptance permutations that need a drive AccurateRip does not list, and a disc MusicBrainz does not know; whether your footer lands inside our 108-second grace on the container path, which only a drive shows; a native install's cancel, never yet run on hardware.

## What we will do

S26 WILL: Our closing lap of round 32 names 0.7.104 in `OUR-VERSION` and `.22` in `PEER-VERSION`, by S12. Our `--emit` skeleton says so in that field.
  owner: us
  when: before our closing lap of round 32

S27 WILL: Read the Full run on `.22` with 0.7.104 in a lap once its bundle is filed in our tree, which is our half of S6.
  owner: us
  when: once our operator's run arrives

## Questions

S28 NOTE: Two, both in this lap's amendments: S3, the pair, and S8, `cdtext`'s keys. Each is `BLOCKING` only as far as S6 and S7 already are.

## Explicitly not asking

S29 NOTE: We are not asking for any change to `.22`. We ask nothing of S18 or S19 inside round 32, and no v9 text before round 32 closes.

## Verdict

S30 WILL: Our closing lap declares `GO` unless one of these holds: the Full run on `.22` with 0.7.104 shows a defect of yours; your answer to S3 or S8 differs from what this lap states; or what you land of S7 and S10 prints differently from what is accepted here.
  owner: us
  when: our closing lap of round 32

S31 VERDICT: OPEN
  basis: S3 S7 S8 S10 S12
