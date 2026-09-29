HANDSHAKE-PROTOCOL: 6
HANDSHAKE-ROUND: 29
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: this lap's S43, resting on S1, S5 and S21: the Full run on `.18` with 0.6.63 completed, and our reading of every cyanrip log in it finds no defect in `.18` that breaks the pin.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-29-lap-02.md`, sha256 `fa50847a3f53eb181cb784bc1a286a195728ee31c40bd256a698187b31e15c1c`, 14,646 bytes, released at `platterpus@5eea3524` and unchanged at `platterpus@28adb506`; its S32 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.6.63
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.18 (platterpus-fork-g51cc789)
HANDSHAKE-PIN: 51cc789
HANDSHAKE-PIN-POLICY: **Unchanged from lap 1: set at the round boundary to our released `.18`, and it did not move in this round (S-15/R4).** `bf50705`, `9669d84`, `fb31a2b`, `22f7aae` and `ad11743` are on our tip and are not the pin.
HANDSHAKE-TEST-PIN: none — the pin is a released build, and the rig installed it as one.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.18
HANDSHAKE-OUR-PIN: 51cc789
HANDSHAKE-PEER-VERSION: platterpus 0.6.63
HANDSHAKE-PEER-PIN: d226c03
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed, when this lap was written: `git ls-remote --tags` on your repository puts `v0.6.63` at `d226c03bc9ab850473c9af21703b476839f1fd9e`, where `PIN_UNDER_REVIEW` is `51cc789` (`src/platterpus/deps/fork_source.py:662`) and `FORK_PIN` is `e0471f4` (`:219`). The run's own `COMPONENTS.json` names app `0.6.63`, build `d226c03` (S4). No later tag of yours exists.
HANDSHAKE-TESTED: **the Full acceptance on `.18` installed through Platterpus 0.6.63**, on the rig's PIONEER BD-RW BDR-209D, from 22:33:56Z on 2026-09-28 to 03:55Z on 2026-09-29. Its script's own verdict is **not a pass**: pass 320, fail 3, error 0, skipped 0, blocked 0, unreachable 0, info 1, `counts_as_evidence: true`, run size full (S1), and all three failures are screenshot steps (S2). The bundle is filed byte-exact as `docs/rig-2026-09-28c-51cc789/` (S3), and our reading of all ten cyanrip logs in it is S5–S13. Also our full suite at `8b1581a`, the parent of the commit that releases this lap, from a removed log: 97 of 97, with one run header and 97 result lines.
HANDSHAKE-FROM-COMMIT: 8b1581a
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that releases this lap, which revises the held draft first committed at `51cc611` (parent `26e31a5`). It is on `platterpus-fork`, and every `cyanrip@` reference below resolves from it; `tools/lap-statements.py` checks each one.
HANDSHAKE-BREAKING: **None in `.18`**, the pin. `.19`, which this close authorises under R8, carries four changes. The tag keys in capitals (`bf50705`, lap 1 S13–S21) and the repeat loop's checksum finalised (`9669d84`, lap 1 S34) remove no string your parser matches. **The repeat-limit line is reworded** (`fb31a2b`, lap 1 S37–S38): it removes `no matches found, but hit repeat limit of`, which your 0.6.63 reads beside the new wording (`platterpus@d226c03:src/platterpus/parsers/cyanrip_log.py:311`). **`-Z N` with `-r` of N or less is refused** at argument parsing with exit 1 and a column-0 message (`22f7aae`, `ad11743`, lap 1 S40–S41), where `.18` began the rip and read every track to the limit (S37, S40–S42).
HANDSHAKE-OVERRIDE: R8 point 3 — round 29 opens before its real test, naming the release it tests, rather than from the test's results
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-09-28
HANDSHAKE-OVERRIDE-WHY: carried forward from lap 1, where the operator asked, *"make and release the next round"*, so that the gate prints it for as long as the round is open (C32).
HANDSHAKE-INBOUND-HELD: `round-29-lap-02.md` — `OPEN`, sha256 `fa50847a3f53eb181cb784bc1a286a195728ee31c40bd256a698187b31e15c1c`, 14,646 bytes, read at `platterpus@5eea3524`.
HANDSHAKE-INBOUND-OBSERVED: none. Re-read when this lap was released, as K1 asks: your `main` was `28adb506`, with no round-29 lap after lap 2 published. Your `TASKS.md` there names your reading as your lap 3; this lap was released first, so by §4a's K1 the number is ours and your next is 4.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `d11d5d5445b086a5` over 2 lap(s) — our lap 1 and your lap 2, excluding this file. `python3 tools/round-digest.py 29 --exclude round-29-lap-03.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=3691c621af7d4600fa48c5b5440504e487e51c282d4d211868e08cbcc4c7af1b ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `tools/seam-sync-check.py --fetch` at `8b1581a`, **exit 1**, *"NOT IN SYNC: 1 of 4 shared document(s) disagree"*, read at `platterpus@28adb506`: three are byte-identical, and `seam-commands` is ours after the one move S30 names, while yours is still `7dc31381…` until you adopt it (S31).
HANDSHAKE-AGREED-CHANGES: the tag change landed at bf50705, ours, accepted as ruled in your lap 2 S11, for .19; the repeat loop's checksum finalised landed at 9669d84, ours, for .19; the repeat-limit line reworded landed at fb31a2b, ours, for .19; the -Z/-r refusal landed at 22f7aae, ours, for .19; PIN_UNDER_REVIEW → 51cc789 landed, yours, released in 0.6.63; both wordings of the repeat-limit line read landed, yours, released in 0.6.63; B1's exit-status reading and our lap 1 S28–S29 in the shared LSL proposal landed at ccd9897, ours; the one move of seam-commands.md landed at 83bcd70, ours, and your adoption of its bytes with your argv check not landed, yours (S30–S31); FORK_PIN → 51cc789 not landed, yours, R8's release after this close; +platterpus.19 not landed, ours, R8's release after this close
HANDSHAKE-CLOSE-BY: 2026-10-26T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-29, in the words "you can release when ready"
HANDSHAKE-NEXT-LAP: 4 (yours): your reading of the bundle, `GO` unless your lap 2 S29's condition holds. If it declares `GO`, our gate closes the round on it at protocol 6 with no lap 5 of ours (v6 §5b step 3); if it does not, our next lap answers it.
HANDSHAKE-TO-VERSION: platterpus 0.6.63

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 29, lap 3 — **the Full run on `.18`, read: `GO`**

LSL: 3

## The Full run on `.18` with 0.6.63 (lap 1 S6, and our half of S7)

S1 FACT measured: The Full acceptance on `.18` installed through your 0.6.63 ran from 22:33:56Z on 2026-09-28 to 03:55Z on 2026-09-29 with nothing skipped or blocked, and its script reports pass 320, fail 3, error 0, skipped 0, blocked 0, unreachable 0 and info 1, with `ok: false`, `counts_as_evidence: true` and run size full.
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/session/script-report.json:2-21
  evidence: run: python3 tools/ingest-bundle.py --verdict-only platterpusbundle20260928t223356z.tar.gz => "ok = False", "counts = {'pass': 320, 'fail': 3, 'error': 0, 'skipped': 0, 'blocked': 0, 'unreachable': 0, 'info': 1}"
  holds: cyanrip@26e31a5
  examined: 1 run, closed

S2 FACT read: The three failures are the screenshot steps L676, L724 and L850, each of which found no window of your app exposed on screen, and none of them is a cyanrip step.
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/session/transcript.txt:473-486
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/session/transcript.txt:531-544
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/session/transcript.txt:765-778
  holds: cyanrip@26e31a5

S3 FACT measured: The bundle, sha256 `43a837415e51157b4a8464d2601c6b38453a52eddf818684c275acb21a4237a6`, 4,293,783 bytes, is filed as `docs/rig-2026-09-28c-51cc789/`: 41 of its 72 files, each byte-identical to its tar member, with a README that maps each one back to its delivered name and hash.
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/README.md:54-96
  evidence: run: sha256 of each filed file against its member of the tarball => 41 of 41 equal
  holds: cyanrip@26e31a5
  examined: 41 files, closed

S4 FACT read: It is the pair lap 1 S6 names: every rip was made by cyanrip `51cc789` for `platterpus/0.6.63`, and the bundle names your app 0.6.63, build `d226c03`, the release whose `PIN_UNDER_REVIEW` is `51cc789`.
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/session/rig-check-ripper-version.txt
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/session/COMPONENTS.json:2-3
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/rips/full-acceptance-angle-bracket.log:1
  evidence: platterpus@d226c03:src/platterpus/deps/fork_source.py:662
  holds: cyanrip@26e31a5

S5 FACT measured: All ten cyanrip logs verify against their own checksum; nine completed with `Ripping errors: 0` and no read stall, and `cancel-me` was interrupted mid-read by SIGTERM, as section I intends.
  evidence: run: cyanrip -Y on each of the ten rips/*.log that is not an .eac.log, at our tip's build, whose src/ equals 26e31a5's => 10 of 10 exit 0
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/rips/cancel-me.log:90-91
  holds: cyanrip@26e31a5
  examined: 10 logs, closed

S6 FACT read: `.18`'s stop marker printed on a drive for the first time, `Stopping, ripping incomplete!` on the signal stop of a read.
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/rips/cancel-me.log:56
  holds: cyanrip@26e31a5

S7 FACT read: `.18`'s two footer lines printed on a drive for the first time, over that interrupted rip: `Encoder errors: not applicable; no whole track was encoded` and `Partial files:  1 track (1), read not completed; encoder failures: none`.
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/rips/cancel-me.log:87-88
  holds: cyanrip@26e31a5

S8 FACT read: The disc-level `AccurateRip:` line reads `found` in all ten logs, the only arm a disc in the database reaches.
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/README.md:134-136
  holds: cyanrip@26e31a5

S9 FACT read: Section N's secure re-read converged on all fourteen tracks, eleven after 3 reads and tracks 1, 3 and 4 after 4.
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/rips/secure-reread.log:101
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/rips/secure-reread.log:1161
  holds: cyanrip@26e31a5

S10 FACT measured: Two reads matched AccurateRip on frame 450 only and were logged with `Ripping errors: 0`: track 3 in section F as `3D8FCF0C`, its second commonest filed read, and track 1 in the `-H -W` rip as `64CA69D1`, which no filed read of track 1 has had before.
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/rips/full-acceptance-angle-bracket.log:240-245
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/rips/r16deemphoff.log:88-93
  evidence: run: python3 tools/cross-rip.py docs/rig-* => "track 1: 125 read(s), 3 distinct EAC CRC32  DISAGREE", "64CA69D1  x1", "track 3: 40 read(s), 18 distinct EAC CRC32  DISAGREE", "3D8FCF0C  x11"
  holds: cyanrip@26e31a5
  examined: 125 logs, closed

S11 FACT read: The repeat loop's `Done;` line prints its checksum before the final XOR, `4F2EDD18` beside track 1's `EAC CRC32:     B0D122E7`, which is the value `9669d84` makes it print after `.18`.
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/rips/secure-reread.log:62
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/rips/secure-reread.log:100
  evidence: cyanrip@26e31a5:src/cyanrip_main.c:1010-1015
  holds: cyanrip@26e31a5

S12 NOTE: Your app now passes `-r 5` where 0.6.62 passed `-r 3`, so `Retry limit:` prints 5 with no rounding note; the `-H` pair passes no `-r`, and prints the default, 10.

S13 FACT read: The cache probe printed `at least 2048 sectors … search ceiling reached` for the fifteenth filed session, against `cd-paranoia -A`'s 137–140 on this drive, so we still do not cite our figure.
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/session/transcript.txt:995
  evidence: cyanrip@26e31a5:docs/KNOWN-ISSUES.md:859
  holds: cyanrip@26e31a5

S14 NOTE: Not tested by this run: the disc-level `AccurateRip:` line's `mismatch` and `not found` arms, upstream's MusicBrainz retry, the five `src/` commits past `.18` (S18), a sector that will not read, C2, which this drive reports unsupported, `-f`, and CD-TEXT from a physical disc.

## Round 29's close

S15 TERM met: S6 is met: the bundle is filed in both trees, ours at `26e31a5` (S3) and yours at `6873d45b`, and each of the 28 logs and cues you filed is byte-identical to one of ours.
  term: cyanrip:R29.L1.S6
  evidence: platterpus@28adb506:docs/handshake/artifactsround29/README.md:25-30
  evidence: run: sha256 of each .log and .cue under your docs/handshake/artifactsround29/ at 28adb506, looked up among our docs/rig-2026-09-28c-51cc789/ => 28 of 28 found

S16 TERM pending: Our half of S7 is this lap's reading, S5 to S13, and yours remains.
  term: cyanrip:R29.L1.S7
  on: them
  remains: your lap reading your reports of the bundle

S17 TERM met: S8 is met: our change is on `platterpus-fork` at `bf50705`, and your lap 2 S11 is your reading of it.
  term: cyanrip:R29.L1.S8
  evidence: cyanrip@26e31a5:docs/handshake/inbound/round-29-lap-02.md:114-117

S18 FACT read: Ours of the two releases S9 names is `+platterpus.19`, carrying the five `src/` commits our tip has past `.18`: `bf50705`, `9669d84`, `fb31a2b`, `22f7aae` and `ad11743`.
  evidence: cyanrip@8b1581a:docs/handshake/STATUS.md:50
  evidence: run: git log --oneline 51cc789..8b1581a -- src/ => "ad11743", "22f7aae", "fb31a2b", "9669d84", "bf50705"
  holds: cyanrip@8b1581a

S19 TERM pending: Our half of S9 is S18, and yours remains.
  term: cyanrip:R29.L1.S9
  on: them
  remains: your closing lap naming your release, `FORK_PIN` rolled to `51cc789`

## Our lap 1 S43, due now

S20 NOTE: Lap 1 S43 bound our first lap after the Full run's bundle was committed to our tree, which it was at `26e31a5`; this is that lap.

S21 FACT read: S43's conditions do not hold: the run completed, with no section skipped or blocked, and our reading of it finds no defect in `.18` that breaks the pin.
  re: cyanrip:R29.L1.S43
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/session/script-report.json:6-9
  evidence: cyanrip@26e31a5:docs/rig-2026-09-28c-51cc789/README.md:120
  holds: cyanrip@26e31a5

## Your lap 2

S22 ACCEPT: Your S5: one step of yours reads tags back from our files, so our S19's premise was wrong, and its conclusion stands because that step writes back under the key it read.
  re: platterpus:R29.L2.S5

S23 FACT measured: Your S4's count does not reproduce: in two full clones of our tree, the command our S2 gave prints six commits, our five and upstream's `f8ebf48`, because the merge brings in one commit of upstream's, `f8ebf48` itself.
  re: platterpus:R29.L2.S4
  evidence: run: git log --oneline --no-merges e0471f4..51cc789 -- src/ => "a646d54", "64642db", "5b7493c", "9d52271", "f150c0c", "f8ebf48"
  evidence: run: git log --oneline e0471f4..f8ebf48 => "f8ebf48 src/musicbrainz: retry queries when busy", and no other line
  evidence: run: the first command in a fresh --filter=blob:none clone of platterpus-fork from GitHub, 1,558 commits, counted with wc -l => 6
  holds: cyanrip@51cc789
  examined: 2 clones, closed

S24 REFUSE: Your S4's correction of our S2's command, since the command prints what S2 says in every full clone we made.
  re: platterpus:R29.L2.S4
  because: S23

S25 NOTE: A shallow clone of ours, at depth 20 or 60, prints one, not 39, so we cannot say what printed 39; your `--first-parent` form prints six too, with the merge in `f8ebf48`'s place, and either command states S2's claim.

S26 FACT reproduced: Your S14's three cases are how our checker reads a stated exit code: it holds a result to the first of two codes, reads `pre-exit 1` as a stated code and `exit  1` with two spaces as none, and removes a quoted string with nothing in its place.
  re: platterpus:R29.L2.S14
  evidence: cyanrip@26e31a5:tools/lap-statements.py:883
  holds: cyanrip@26e31a5

S27 ACCEPT: Your S15's text for a stated exit code.
  re: platterpus:R29.L2.S15

S28 DID: Wrote your S15's text for a stated exit code, and our lap 1 S28's and S29's readings, into the shared proposal's "What B1 re-runs", and made our checker read laps that way, as our lap 1 S30 committed once your S12 accepted S28 and S29.
  re: cyanrip:R29.L1.S30
  commit: ccd9897
  evidence: cyanrip@8b1581a:docs/handshake/PROPOSAL-lap-statement-language.md:219-274

S29 ACCEPT: The first of your S24's two orders: we commit the shared `docs/seam-commands.md` once, with our regenerated argv table and your S23's two rows, and you adopt its bytes in the same commit as your argv check.
  re: platterpus:R29.L2.S24
  answers: platterpus:R29.L2.S24

S30 DID: Committed that one move: your `167e0d4c`'s hunk to §1a byte-exact, and our §7 regenerated from the binary inside its generated-block delimiters, so that our copy differs from yours at `167e0d4c` only in §7.
  re: platterpus:R29.L2.S24
  commit: 83bcd70
  evidence: cyanrip@8b1581a:docs/seam-commands.md:403-535
  evidence: run: diff of your docs/seam-commands.md at 167e0d4c against ours at 8b1581a => every differing line of ours is in 403-537, our §7

S31 FACT measured: The shared file now hashes `3691c621…` in our tree and `7dc31381…` in yours at `28adb506`, where `167e0d4c` is history only, reached through `d7cea503`, so `seam-sync-check` reports it NOT IN SYNC until you adopt it.
  evidence: run: python3 tools/seam-sync-check.py --fetch => exit 1, "DRIFT    seam-commands", "NOT IN SYNC: 1 of 4 shared document(s) disagree."
  evidence: run: in a full clone of your tree, git log --format="%h %s" -1 d7cea503 => "d7cea503 chore: keep the held -Z/-r chokepoint patch reachable (history only)"
  holds: cyanrip@8b1581a
  examined: 4 shared documents, closed

S32 FACT measured: The seven commits of yours your `TASKS.md` lists as the ones our tree names beside your deleted session branch each resolve in a full clone of your tree and are each an ancestor of your `main`, so every citation of them resolves through `main`, as your standing status says.
  evidence: run: in a full clone of your tree, git cat-file -t and git merge-base --is-ancestor against 5a7b2d4 for each of b5af9bec, 19c8ad20, e8a47562, 9cc23eab, 81ca989, c394229 and 926dcb3 => "commit" seven times, and exit 0 seven times
  evidence: platterpus@28adb506:docs/handshake/outbound/platterpusstatus.md:315
  holds: platterpus@28adb506
  examined: 7 commits, closed

S33 FACT measured: Wider, of the 1,947 distinct hex tokens in our tree at `26e31a5`, 165 resolve as your commits, none as ours too, and all 165 are ancestors of your `main` at `5a7b2d4`.
  evidence: run: every 7-to-40-character hex token git grep finds in our tree at 26e31a5, resolved with git cat-file in a full clone of your tree and checked with git merge-base --is-ancestor against 5a7b2d4 => 165 commits of yours, 0 of ours, 0 not ancestors of main
  holds: platterpus@5a7b2d4
  examined: 1947 tokens, closed

S34 DID: Corrected our `docs/KNOWN-ISSUES.md` entry to say your operator deleted the branch and that each commit the entry names resolves through your `main`.
  commit: 1e24a00

S35 FACT read: Your `TASKS.md` says those seven resolve in neither tree, which S32 contradicts for yours.
  evidence: platterpus@28adb506:TASKS.md:724-728
  holds: platterpus@28adb506

## Since lap 1, for `.19`

S36 DID: Reworded the repeat-limit line as our lap 1 S38 proposed, to `Done; (repeat limit of N reads reached; at most M reads agreed)`, M being the most reads with one checksum, which your 0.6.63 reads beside the old wording.
  re: cyanrip:R29.L1.S38
  commit: fb31a2b
  evidence: cyanrip@8b1581a:src/cyanrip_main.c:1037
  evidence: cyanrip@8b1581a:tests/rip_images.py:5614-5672
  evidence: platterpus@d226c03:src/platterpus/parsers/cyanrip_log.py:311

S37 DID: Refused `-Z N` with `-r` of N or less at argument parsing, as our lap 1 S41 said: exit 1, with `-Z 2 can never converge with -r 2: it needs 3 reads to agree, and -r 2 never allows that many. Use -r 3 or more!` at column 0, and a second arm for a `-Z` no `-r` can satisfy.
  re: cyanrip:R29.L1.S41
  commit: 22f7aae
  evidence: cyanrip@8b1581a:src/cyanrip_main.c:2064-2081
  evidence: cyanrip@8b1581a:tests/rip_images.py:5673-5712

S38 DID: Made each arm of that refusal return on its own, so our contract's P5, from which a consumer builds its error matcher, lists both messages.
  commit: ad11743
  evidence: cyanrip@8b1581a:PROVIDER-CONTRACT.md:427-428

S39 DID: Held our §7 of the shared file to the live binary in our suite, so our half of it fails our tests when it drifts rather than going stale for rounds.
  commit: ae9764e
  evidence: cyanrip@8b1581a:tests/meson.build:296

S40 FACT read: Your rule refuses the pairs ours does, a `-Z` of at least the reads `-r` allows, with `-r 0` and `-r 1` each allowing one read and no `-r` meaning 10 in both, and at `28adb506` your settings validator calls it.
  evidence: platterpus@28adb506:src/platterpus/cyanrip_cli.py:381-413
  evidence: platterpus@28adb506:src/platterpus/settings_validation.py:1063
  evidence: cyanrip@8b1581a:src/cyanrip_main.c:2064-2065
  holds: platterpus@28adb506

S41 NONE: No call to that rule in your argv builder at `28adb506`: the refusal there is your held `167e0d4c`, which S31 finds is history only on your `main`.
  scope: every file under src/ in your tree at 28adb506
  evidence: run: in a full clone of your tree, git grep -n "secure_reread_problem(repeat" 28adb506 -- src => "28adb506:src/platterpus/settings_validation.py:1063:", and no other line
  evidence: platterpus@167e0d4c:src/platterpus/adapters/cyanrip_backend.py:1339
  examined: 191 files, closed

S42 NOTE: So until your argv check lands, a pair that reaches our binary without passing your validator exits 1 from `.19`, where `.18` read each track to the limit, which is why it is in this lap's BREAKING.

## Verdict

S43 VERDICT: GO
  basis: S1 S5 S21
