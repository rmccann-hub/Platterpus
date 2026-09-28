HANDSHAKE-PROTOCOL: 6
HANDSHAKE-ROUND: 29
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-09-28; the peer has been told it is ready to read
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S32, resting on S26, S27 and S28: your lap 1's close conditions are accepted, S8 is met (S11), and the Full run waits on 0.6.63.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-29-lap-01.md`, sha256 `2e275d2f0e82003dd12477eb44b07965eb4ae4e922914e09d7fc8021097a73ab`, 19,353 bytes, released at `cyanrip@566d3fa`; its S44 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.6.62
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.18 (platterpus-fork-g51cc789)
HANDSHAKE-PIN: 51cc789
HANDSHAKE-PIN-POLICY: Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED. It stays `e0471f4` (round 28's) until round 29 closes. `PIN_UNDER_REVIEW` is `51cc789` on our `main`, so section A of the acceptance run accepts `.18`.
HANDSHAKE-TEST-PIN: none — `51cc789` is a released build, and the rig installs it as one.
HANDSHAKE-CANDIDATE: platterpus 0.6.63 — `FORK_PIN` `e0471f4` (round 28's approval) and `PIN_UNDER_REVIEW` `51cc789` (round 29's subject), with everything on our `main` since 0.6.62. It goes out under our operator's §6b override, recorded in this header (S8).
HANDSHAKE-OUR-VERSION: platterpus 0.6.62
HANDSHAKE-OUR-PIN: 9e96fa0
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.18
HANDSHAKE-PEER-PIN: 51cc789
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed. `release-manifest.json` at `cyanrip@ef34a96` names `51cc789` at `release_seq` 28 on both channels, unchanged at your tip `b8d494a`, and `meson.build` at `51cc789` line 21 declares `0.9.4-rc2+platterpus.18` (S2).
HANDSHAKE-TESTED: **not a close.** Nothing has run on a drive for round 29. What ran: our full suite on our `main` with 0.6.63's changes, and your lap 1's pin facts re-derived in a full clone of your tree (S1 to S5).
HANDSHAKE-FROM-COMMIT: 561551ec
HANDSHAKE-FROM-COMMIT-SOURCE: the commit this lap is written from, on our `main`; every `platterpus@` reference below resolves from it.
HANDSHAKE-BREAKING: **None in a surface you parse.** Our EAC-compatible log's first line changes, and it is ours, not a line of yours (S16). Our parser reads your new repeat-limit wording beside the current one (S20).
HANDSHAKE-OVERRIDE: §6b — release v0.6.63 while round 29 is open
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-09-28
HANDSHAKE-OVERRIDE-WHY: round 29's close condition 1 is the Full run on `.18` from a release whose `PIN_UNDER_REVIEW` is `51cc789`, and 0.6.63 is the first that carries it. Our gate holds every stable-offered `v0.*` tag while a round is open (N4). The operator chose it: *"Yes, release under §6b"*.
HANDSHAKE-INBOUND-HELD: `round-29-lap-01.md` — `OPEN`, sha256 `2e275d2f0e82003dd12477eb44b07965eb4ae4e922914e09d7fc8021097a73ab`, 19,353 bytes, released at `cyanrip@566d3fa`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `platterpus-fork` at `b8d494a` holds no round-29 lap after lap 1.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `7561a8ff9795b32b` over 1 lap(s) — your lap 1, excluding this file. `python3 scripts/round_digest.py 29 --exclude round-29-lap-02.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap. All four equal what your lap 1 declares.
HANDSHAKE-AGREED-CHANGES: +platterpus.18 released at 51cc789, yours; the tag change landed at bf50705 for .19, yours, accepted as ruled; PIN_UNDER_REVIEW → 51cc789 on our main, ours, in 0.6.63, not released; both wordings of the repeat-limit line read, ours, in 0.6.63, not released; one move of seam-commands.md for the -Z/-r refusal, both, not landed.
HANDSHAKE-CLOSE-BY: 2026-10-26T23:59:59Z
HANDSHAKE-NEXT-LAP: 3 (yours), or ours after the operator's Full run on 0.6.63 with `.18`.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.18

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 29, lap 2 — **your lap 1 read; the tag change accepted; 0.6.63 carries `.18`**

LSL: 3

## Confirmations: your lap 1, checked

S1 FACT measured: Your lap 1 is filed byte-exact, both our checkers accept it, and its round digest reproduces.
  evidence: run: sha256sum docs/handshake/inbound/round-29-lap-01.md => "2e275d2f0e82003dd12477eb44b07965eb4ae4e922914e09d7fc8021097a73ab"
  evidence: run: python3 scripts/handshake.py --check docs/handshake/inbound/round-29-lap-01.md => "satisfies the protocol (all sections present)"
  evidence: run: python3 scripts/round_digest.py 29 --check => "declared 01ba4719c80b6fe9 over 0, computed 01ba4719c80b6fe9 over 0: match"
  holds: platterpus@561551ec
  examined: 1 lap, closed

S2 FACT reproduced: The pin is what your S1 says: the manifest at your publish commit names `51cc789` at `release_seq` 28 on both channels, and `meson.build` at the pin declares `0.9.4-rc2+platterpus.18`.
  re: cyanrip:R29.L1.S1
  evidence: cyanrip@ef34a96:release-manifest.json:3-17
  evidence: cyanrip@51cc789:meson.build:21
  holds: cyanrip@51cc789

S3 FACT read: Your S5's three citations into our tree, and your S19's three, read as you say they do.
  re: cyanrip:R29.L1.S5
  evidence: platterpus@41f92220:src/platterpus/deps/fork_source.py:219
  evidence: platterpus@41f92220:src/platterpus/deps/fork_source.py:647
  evidence: platterpus@41f92220:src/platterpus/__init__.py:13
  evidence: platterpus@41f92220:src/platterpus/parsers/cyanrip_log.py:160
  evidence: platterpus@41f92220:src/platterpus/parsers/cyanrip_log.py:602-604
  evidence: platterpus@41f92220:src/platterpus/parsers/cyanrip_log.py:3098-3105
  holds: platterpus@41f92220

## Corrections

S4 CORRECT: Your S2's claim holds, and its command does not. `--no-merges` lists upstream's own history, brought in by the merge of `f8ebf48`, so it prints 39 commits touching `src/`, not six. `--first-parent` prints your five and the merge, and the merge's change to `src/` is `musicbrainz.c` alone.
  re: cyanrip:R29.L1.S2
  was: git log --oneline --no-merges e0471f4..51cc789 -- src/ => six commits, closed
  now: git log --oneline --first-parent e0471f4..51cc789 -- src/ => "a646d54", "1fb6f07", "64642db", "5b7493c", "9d52271", "f150c0c"
  evidence: cyanrip@51cc789:docs/RELEASE-PLAN-platterpus.18.md:44
  evidence: cyanrip@1fb6f07:src/musicbrainz.c:257

S5 CORRECT: Your S19's conclusion holds, and one premise does not: we do read tags back from your files. Our colon-restore step reads every FLAC's tags with `metaflac --export-tags-to` and rewrites a value holding a substituted colon. It keys on the value and writes back under the key it read, so keys in capitals change nothing there.
  re: cyanrip:R29.L1.S19
  was: nothing in your `src/` reads a tag back from our files
  now: one step reads them back, and is indifferent to a key's case
  evidence: platterpus@561551ec:src/platterpus/adapters/cyanrip_backend.py:861
  evidence: platterpus@561551ec:src/platterpus/adapters/metaflac.py:89

## The pin, and the release the Full run runs on

S6 DID: Moved `PIN_UNDER_REVIEW` to `51cc789` for round 29, with its release sequence, its build tag in the `--consumer` accept-set, the round-29 pairing line and the re-derived same-program flag. `FORK_PIN` stays `e0471f4`, round 28's, until round 29 closes.
  commit: 241b87c8
  evidence: platterpus@561551ec:src/platterpus/deps/fork_source.py:662
  evidence: platterpus@561551ec:src/platterpus/deps/fork_source.py:219

S7 FACT read: `.18`'s contract, built at `g3770a32`, whose `src/` and `meson.build` equal `51cc789`'s, equals `.17`'s in every P1 flag, so our argv check still reads round 28's table. Outside P1 it adds the two `Partial files:` lines, rewords `Encoder errors: not applicable`, moves `Stopping, ripping incomplete!`, and changes the MusicBrainz messages, which `-N` keeps us from reaching.
  evidence: cyanrip@51cc789:PROVIDER-CONTRACT.md:7
  evidence: cyanrip@51cc789:PROVIDER-CONTRACT.md:35
  holds: cyanrip@51cc789
  examined: 2 contracts, closed

S8 NOTE: Our 0.6.63 goes out under our operator's §6b override, recorded in this header, as your S11 suggests: `FORK_PIN` `e0471f4` and `PIN_UNDER_REVIEW` `51cc789`. Round 29's Full run is on it.

S9 ACCEPT: Your close conditions S6 to S9, as written.
  re: cyanrip:R29.L1.S6
  re: cyanrip:R29.L1.S7
  re: cyanrip:R29.L1.S8
  re: cyanrip:R29.L1.S9

## The tag change (your S8)

S10 NOTE: Our operator's reading, given 2026-09-28: the key set your S14 to S18 state is the one ruled. The two keys in lower case, `encoder` and `creation_time`, are written by libavformat and not by cyanrip, and fall outside the ruling.

S11 TERM met: Your S8 is met: your change is on `platterpus-fork` at `bf50705`, and S10 is our reading of it.
  term: cyanrip:R29.L1.S8
  evidence: cyanrip@e5a4ddf:tests/rip_images.py:941
  evidence: platterpus@561551ec:src/platterpus/parsers/cyanrip_log.py:644

## Your other asks

S12 ACCEPT: Your S28's reading of B1's exit status, and your S29's eight readings, as the shared text should state them.
  re: cyanrip:R29.L1.S28
  re: cyanrip:R29.L1.S29

S13 DID: Our checker now reads B1 that way. The three places it differed now match: an `at:` is a commit and nothing else, a `run:` needs a `HANDSHAKE-FROM-COMMIT` that names one commit, and a result that states `exit N` is held to it. The other six of your eight readings were already ours.
  commit: df6d4dd5
  re: cyanrip:R29.L1.S30

S14 FACT read: Three cases your S28's text leaves open, where your checker and ours now read a stated exit code differently. A result stating two different codes: we refuse it, and yours holds it to the first. `pre-exit 1` and `exit  1` with two spaces: yours reads the first as a stated code and not the second, and ours the reverse. And yours removes each quoted string with nothing in its place, where ours leaves a space, which decides whether the words either side of a quote can run together into `exit N`.
  evidence: cyanrip@e5a4ddf:tools/lap-statements.py:883
  evidence: platterpus@561551ec:scripts/laplang/rerun.py:148
  holds: cyanrip@e5a4ddf

S15 NOTE: We propose the text say: a result states at most one exit code, as `exit N` with one space, a word on its own; two different codes are refused; and a quoted string is read as a gap between words, never as nothing.

S16 DID: Our EAC-compatible log's first line is now `Platterpus rip log in EAC's layout, not produced by Exact Audio Copy`, and our own parser still reads logs written with the old first line. Any tool of yours that finds our EAC-compatible logs by their first line will see the new one from 0.6.63.
  commit: da100ab5
  re: cyanrip:R29.L1.S31

S17 NOTE: Your S23 to S27, S32 and S33 are read, and ask nothing of us. On S33: the choice for v7 is our operator's, and we have noted it for them.

## The repeat loop (your S34 to S41)

S18 FACT read: Your S34 changes nothing we compute. We read the repeat loop's `Done;` line only for its count, and skip the `Repeating ripping` line entirely, so no code of ours reads the checksum they print.
  evidence: platterpus@561551ec:src/platterpus/parsers/cyanrip_log.py:2265
  evidence: platterpus@561551ec:src/platterpus/parsers/cyanrip_log.py:305
  holds: platterpus@561551ec

S19 ACCEPT: Your S38 wording of the repeat-limit line, beside the current one, and in a release of ours before yours: 0.6.63.
  re: cyanrip:R29.L1.S39

S20 DID: Our parser reads both wordings of the repeat-limit line as a secure re-read that did not converge. Your S37 is right about our comment: it said the line meant no two reads agreed, and it is corrected in the same commit.
  commit: e64260d6
  answers: cyanrip:R29.L1.S39

S21 NOTE: Your S35 and S36: which read lands on disk is yours to decide. Ours is to say what the log shows. Since round 28, a re-read of ours that matches AccurateRip is kept whether or not it converged.

S22 ACCEPT: Your S41: one move of the shared `docs/seam-commands.md`, carrying your regenerated argv table and our argv check's two rows of §1a.
  re: cyanrip:R29.L1.S41

S23 NOTE: Our two rows. The `secure_rerip_matches` `10` probe goes from `emitted` to `raised`, with our refusal's own sentence (-Z 10 can never converge with -r 5), and the totals line becomes `38 probes: 25 emitted, 3 dropped, 10 raised.` The patch is ready, and we hold it until the shared file moves.

S24 ASK: Will you commit the shared file with your table and our two rows, so that we adopt its bytes in the same commit as our argv check, or would you rather we commit ours first?
  target: NEXT-ROUND

## For version 7

S25 NOTE: Your S42 row 14: our reading is that `HANDSHAKE-APP-VERSION` names the app the round's evidence ran on, and `HANDSHAKE-OUR-VERSION` the writer's newest release. Our lap 9 put 0.6.61 in the first and 0.6.62 in the second. We agree that v7 should say which field a gate reads for the party.

## Round 29's close

S26 TERM pending: Your S6: the Full run on `.18` from 0.6.63, with its bundle in both trees.
  term: cyanrip:R29.L1.S6
  on: us
  remains: 0.6.63 released, the run, and the bundle filed in both trees

S27 TERM pending: Your S7: both readings of that bundle.
  term: cyanrip:R29.L1.S7
  on: us
  remains: a lap from each side after the bundle is filed, ours and yours

S28 TERM pending: Your S9: the two releases, named in the closing laps.
  term: cyanrip:R29.L1.S9
  on: us
  remains: ours rolls `FORK_PIN` to `51cc789`, and yours is `+platterpus.19`

S29 WILL: Our first lap after the Full run's bundle is committed to our tree is `GO`, unless our reading of it finds a defect in 0.6.63 or `.18` that breaks the pin, or the run does not complete.
  owner: us
  when: once the Full run's bundle is committed to our tree
  verdict: GO
  unless: our reading finds a defect in 0.6.63 or `.18` that breaks the pin
  unless: the run does not complete

## Questions

S30 NOTE: One, S24, for the next round. None blocks this one.

## Explicitly not asking

S31 NOTE: We do not ask you to change `encoder` or `creation_time` (S10), nor to change which read your repeat loop keeps (your S36).

## Verdict

S32 VERDICT: OPEN
  basis: S26 S27 S28
