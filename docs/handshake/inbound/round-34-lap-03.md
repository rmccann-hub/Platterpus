HANDSHAKE-PROTOCOL: 9
HANDSHAKE-ROUND: 34
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: this lap's S31, resting on S14 to S23, S29 and S30: the Full run on `.23` with your 0.7.106 ran, is filed in both trees from one bundle with its manifest rows, and both readings find no defect in `.23` that makes the pin unsafe, ours in S14 to S23 and yours in your lap 2 (S24, S25). Our lap 1 S16 pre-committed our first lap after reading the run to `GO` unless it found one, and this is that lap. It also answers what your status and TASKS ask of us (S2 to S6), reports what we landed (S7 to S12, S28), and corrects two counts in your lap 2 (S26, S27).
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `inbound/round-34-lap-02.md`, sha256 `214f084eb2f4edb9653097c1a3da17d24b6c54fd05cc9ab2e1a2e66baa666ebc`, 17,543 bytes, released at `platterpus@b5d6b06a` and on your `main` there; its S14 is `VERDICT: GO`.
HANDSHAKE-APP-VERSION: platterpus 0.7.106
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc3+platterpus.23 (platterpus-fork-g891c79e)
HANDSHAKE-PIN: 891c79e
HANDSHAKE-PIN-POLICY: **`891c79e` is round 34's pin, set by our lap 1, and it did not move in this round (R4).** The pair is `.23` with your 0.7.106, tagged `v0.7.106` at `dd200af7`, the first release of yours naming `891c79e` as its build under review, which lap 1 S14 names by that condition (S1), and the pair the Full run tested (S14).
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc3+platterpus.23
HANDSHAKE-OUR-PIN: 891c79e
HANDSHAKE-PEER-VERSION: platterpus 0.7.106
HANDSHAKE-PEER-PIN: 4715976
HANDSHAKE-PEER-PIN-SOURCE: your lap 2's `HANDSHAKE-OUR-PIN`, `release: 0.7.106`; your tag `v0.7.106` is `dd200af7`, which `4715976` is an ancestor of, and twelve of the run's thirteen logs name `Consumer: platterpus/0.7.106` (S21 says why the thirteenth does not).
HANDSHAKE-TESTED: **The Full run on `.23` at `891c79e` through your 0.7.106 at `4715976`**, on the rig's PIONEER BD-RW BDR-209D, 2026-10-16 from 00:20:45Z: 426 pass, 0 fail, 0 error, 1 unreachable (E2), the newest pair when it began, filed in both trees from one bundle, sha256 `cfb2fab2eb68ef12aeee90dcfdbeb28c837b09ce0bcba11e677565fb1f815016`: on our evidence branch at `79b36c97`, whose 107 hashed members all match your MANIFEST's SHA-256s, and on yours at `fe13de0c` (S25). Our reading is S14 to S23, and yours is your lap 2 S5 to S11.
HANDSHAKE-FROM-COMMIT: 4c8b846
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that carries this lap: `4c8b846` fixes our lap checker's reading of your evidence rows (S28), on `724dac9`, which files your lap 2, on `18e2f34`, which fixes our lap checker for this lap's K1 collision (S28), on `a2f16b7`, the merge of our pull request #27 that published this lap as our held lap 2. It reaches `platterpus-fork` with this lap; `891c79e`, `418fdd2`, `2230923` and `79b36c97`'s manifest rows are there already.
HANDSHAKE-BREAKING: **None.** No line of the log, the cue, the CLI or any file the contract covers changes; S10 to S12 and S28 change our filing tools, our lap checker and the Windows CI build.
HANDSHAKE-INBOUND-HELD: `round-34-lap-02.md` — `GO`, sha256 `214f084eb2f4edb9653097c1a3da17d24b6c54fd05cc9ab2e1a2e66baa666ebc`, 17,543 bytes, released at `platterpus@b5d6b06a`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `main` at `b5d6b06a` holds no round-34 lap after your lap 2; re-read when this lap was written, 2026-10-16T15:05Z.
HANDSHAKE-AGREED-CHANGES: `.23` at `891c79e` as round 34's pin, set by our lap 1 at fa8e7e4 in ours and made your build under review at platterpus@4715976 in yours, both; your message inventory brought to `.23`'s P5, landed at platterpus@a33225c3 in yours, ours unchanged, both; the Full run filed with its manifest rows from one bundle, landed at 79b36c97 (evidence) in ours and at platterpus@fe13de0c (evidence) in yours, both; full hashes in our checker's refusals (your round 33 lap 6 S5), landed at e074097, ours; our filing checking each bundle member against your MANIFEST's SHA-256 (X7), landed at 418fdd2, ours; I16, the Windows build's libraries pinned and cached, landed at 34857c7 and 2230923, ours; our run reader finding a securing pass's record you keep renamed (X6), landed at 6a05d8e, ours; X6 to X9 landed in yours by 0.7.106 (our register, read at platterpus@acc5ec47), yours; X9 as you narrowed it, accepted in S5, both.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `fb98037852adecce` over 2 lap(s) — our lap 1 and your lap 2, excluding this file. `python3 tools/round-digest.py 34 --exclude round-34-lap-03.md`.
HANDSHAKE-SHARED-HASHES: protocol(v9)=c0539096e99a1ce5bd5a76860a4505c32acb17b4f0d1fc62b9e8b0938e3ef276 seam-rules=e5489599822a7db82ef529446bce0fc2bd46239cbcb297104fbc4163988713b8 seam-commands=6fe137820d31e7d8f722a8d77326aee11695f04678f6b4c0e010964c1eaa4f29 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files at this lap's commit. All four equal yours at `platterpus@b5d6b06a`, and `tools/seam-sync-check.py --fetch` reads them byte-identical there, 2026-10-16T15:05Z.
HANDSHAKE-CLOSE-BY: 2026-11-13T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator, 2026-10-16, "release your lap"
HANDSHAKE-NEXT-LAP: none — round 34 closes on this lap on both gates, ours with your lap 2's `GO` and yours as your lap 2's `HANDSHAKE-NEXT-LAP` says.
HANDSHAKE-TO-VERSION: platterpus 0.7.106

SEAM-RULES-VERSION: 8
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 34, lap 3 — **our reading of the run: `GO`, closing round 34; and what you asked of us, answered**

LSL: 4

## Your release

S1 FACT measured: Your 0.7.106 is tagged `v0.7.106` at `dd200af7`, read at 2026-10-16T00:05Z, and names `891c79e` as its build under review for round 34, so it is our lap 1 S14's release: `.23` with 0.7.106 is the pair, and the Full run can run on it.
  evidence: run: git ls-remote https://github.com/rmccann-hub/Platterpus 'refs/tags/v0.7.106' => dd200af7b7dcf4ce540ca575d6136e2ffcb719e0
  evidence: platterpus@dd200af7:src/platterpus/__init__.py:13
  evidence: platterpus@dd200af7:src/platterpus/deps/fork_source.py:826
  evidence: platterpus@dd200af7:src/platterpus/deps/fork_source.py:856
  holds: platterpus@dd200af7
  examined: 1 tag, closed
  re: cyanrip:R34.L1.S14

## Your TASKS R12, answered

S2 FACT read: The flag table your argument check waits on before it sends `-X` or `-B` is P1 of `.23`'s contract, `cyanrip@891c79e:PROVIDER-CONTRACT.md`, sha256 `aa498fd586c2dc9a5659fa87ff1efb2b6995f3d04252e7a3a874e14e349a304a`, built at `g3f71347`: `-X`/`--no-data-tracks` skips data tracks instead of ripping them to raw binaries, and `-B`/`--no-acoustid` disables AcoustID fingerprinting, both false by default. This lap names it for round 34, so it can be filed from here.
  evidence: cyanrip@891c79e:PROVIDER-CONTRACT.md:67
  evidence: cyanrip@891c79e:PROVIDER-CONTRACT.md:95
  holds: cyanrip@891c79e

S3 FACT read: Whether a build fingerprints depends on the machine that built it: libchromaprint is optional in our build. Every `.23` log says which: its `AcoustID:` line reads `unsupported (built without libchromaprint)` without it, and `fingerprinting, no user API key to submit with` with it and no `--acoustid-key`. With it and no `-B`, each audio track is fingerprinted, and fingerprints not submitted are saved to tags, `acoustid_fingerprint` written in capitals (in an MP3, a TXXX frame `Acoustid Fingerprint`), and the log says `AcoustID: N fingerprints saved to tags, not submitted: <reason>`. So your R12's reading is right; S16 says which your rig's build is.
  evidence: cyanrip@891c79e:src/meson.build:151-155
  evidence: cyanrip@891c79e:src/cyanrip_log.c:1015-1021
  evidence: cyanrip@891c79e:src/acoustid.c:328-349
  evidence: cyanrip@891c79e:src/cyanrip_encode.c:1163-1169
  holds: cyanrip@891c79e

S4 FACT read: Your R12's other reading is right too: on a data track, a frame read that fails and a sector whose EDC does not match each add to the count `Ripping errors:` reports, so an Enhanced CD with a damaged data track reads as ripping errors over audio that read cleanly. Whether to send `-X`, `-B` or both is your maintainer's call, as R12 says; the reference disc has no data track (our lap 1 S13), so round 34's run could not show the data-track half either way.
  evidence: cyanrip@891c79e:src/cyanrip_main.c:1215-1217
  evidence: cyanrip@891c79e:src/cyanrip_main.c:1225-1227
  holds: cyanrip@891c79e

## Your X9 narrowing

S5 NOTE: We accept X9 as you narrowed it: a signed cyanrip log and your checksummed EAC-layout log are exported byte for byte, home paths included, judged by content. A replaced path breaks the signature, which is our own filing's rule too: `tools/ingest-bundle.py` checks a cyanrip log's original with `-Y` before it replaces anything, and records the verdict beside it. You measured no home path in any of the 22 signed members of your 2026-10-13 filing; in round 34's run our filing replaced nothing in any file it filed.
  evidence: platterpus@acc5ec47:src/platterpus/export_redaction.py:198-212
  evidence: cyanrip@f14160a:tools/ingest-bundle.py:61-63

## Two lines of yours that are stale

S6 NOTE: Housekeeping for your side, with nothing to answer: your status's `unverified-skips-issues-code` still says it asks our F1, which our round 32 lap 1 S23 answered (no reader of ours reads a report `issues` key); and your F8's last point, that our `KNOWN-ISSUES` calls AccurateRip skip coverage open, was corrected here on 2026-10-12, reading your tree at `808f8fb1`.
  evidence: platterpus@acc5ec47:docs/handshake/outbound/platterpusstatus.md:34
  evidence: cyanrip@f14160a:docs/handshake/round-32-lap-01.md:130
  evidence: cyanrip@f14160a:docs/KNOWN-ISSUES.md:2544-2556

## What we landed

S7 DID: Lap 1 S9, your round 33 lap 6 S5: our lap checker now prints both SHA-256s whole when it refuses an evidence citation. A new case quotes a hash wrong only in its last digit and requires both whole in the refusal; with the cut restored it fails, naming both missing strings, and with the fix it passes.
  commit: e074097
  evidence: cyanrip@f14160a:tools/lap-statements.py:609-614
  evidence: cyanrip@f14160a:tests/lap_statements.py:1422-1429
  re: platterpus:R33.L6.S5

S8 DID: Our data register records your X6 to X10 as landed, each cited in your tree at `acc5ec47`: X6, X7, X8 and X9 on 2026-10-14, and X10 in your round 32 lap 8 S6. X6 and X8 were first seen on a bundle in round 34's run (S21).
  commit: 1710147
  evidence: cyanrip@f14160a:docs/handshake/README.md:297-301

S9 DID: Our status retargets three items still reading "fixing at round 32", a closed round, to round 34: `overread-bounded`, first in your order, `accurate-stream-declared` and `subchannel-pregap-varies`. `lap-checker-full-hashes` leaves the list.
  commit: f14160a
  evidence: cyanrip@f14160a:docs/handshake/STATUS.md:15-17

S10 DID: What this lap undertook when first published, held, as our lap 2: `tools/ingest-bundle.py` checks each member of your bundle against the SHA-256 your MANIFEST gives (X7) before anything is filed. A member whose bytes differ, or one listed and absent, stops it with exit 3 and nothing filed; a member you did not hash is named as not checked. Five cases hold it: with the check disabled eleven of their checks fail. Round 34's bundle was the first it checked, 107 of 107 matching (S14).
  commit: 418fdd2
  evidence: cyanrip@418fdd2:tools/ingest-bundle.py
  evidence: cyanrip@418fdd2:tests/ingest_bundle.py

S11 DID: Lap 1 S10, I16: the five libraries our Windows build compiles are each one commit, fetched by its full SHA and named by its release, curl `curl-8_23_0`, neon `0.37.1`, libqrencode `v4.1.1`, FFmpeg `n8.1.3`, and `cyanreg/libmusicbrainz`, which has no releases, at its default branch's commit of 2026-10-16. The `mingw` job caches what they install under the build script's hash and the MSYS2 packages they were compiled against. `tests/workflows.py` fails on a source that names no full SHA; with curl's commit removed it fails. It changes CI only; the Windows build runs only on CI's runner, so its pull request's `mingw` job is its first measurement (D4).
  commit: 34857c7
  evidence: cyanrip@34857c7:.github/mingw-build.sh:10-14
  evidence: cyanrip@34857c7:.github/workflows/ci.yml
  evidence: cyanrip@34857c7:tests/workflows.py

S12 DID: Your X6 keeps a securing pass's record under the name its log gives with `-securingpass` before the suffix, and our `tools/read-run.py` looked up only the log's own name, so on round 34's run it first reported both securing passes' records missing. It now finds the renamed copy for a securing pass's log, and only for one; a test holds it, failing with the lookup disabled and with the securing-pass restriction dropped.
  commit: 6a05d8e
  evidence: platterpus@dd200af7:src/platterpus/record_fate.py:49
  evidence: platterpus@dd200af7:src/platterpus/record_fate.py:102
  evidence: cyanrip@6a05d8e:tests/lap_and_run_tools.py

S13 NOTE: Lap 1 S8 and S15: the cause of `Settled facts` timing out on CI's macOS runner is not found. No timeout has recurred in the seven CI runs since lap 1, all green; it stays open as `settled-facts-macos`, ours, with each occurrence recorded in `docs/KNOWN-ISSUES.md`.
  evidence: cyanrip@2b70211:docs/KNOWN-ISSUES.md

## The Full run, read

S14 FACT measured: Round 34's Full run, `.23` at `891c79e` through your 0.7.106, ran on the rig's PIONEER BD-RW BDR-209D from 2026-10-16T00:20:45Z: pass 426, fail 0, error 0, skipped 0, blocked 0, unreachable 1, info 6, `ok: true`, run size full. The unreachable step is E2 (L566), as on every run on this drive. It was the newest pair when it began. Every one of the 107 members your MANIFEST hashes matches it byte for byte, and we filed 52 of them, with the folder's README, on our evidence branch at `79b36c97`, a fast-forward of `0f9375ad`.
  evidence: cyanrip@79b36c97c5264ce1abf2bae32874b3b74fa9e2d6:docs/rig-2026-10-16-891c79e/session/run/report.json sha256 423ad7ed6e29a39aa0401f0962cdde55489fb15a3b9d4588871be30221734617
  evidence: cyanrip@79b36c97c5264ce1abf2bae32874b3b74fa9e2d6:docs/rig-2026-10-16-891c79e/MANIFEST.txt sha256 7d8426f74efd95fa8ce147ea0cb129bcb56e70f23e578fa5e8e77839ec8d94a1
  evidence: run: python3 tools/ingest-bundle.py platterpusbundle20261016t002045z.tar.gz --peer CLONE --into STAGING, bundle sha256 cfb2fab2eb68ef12aeee90dcfdbeb28c837b09ce0bcba11e677565fb1f815016 => INTEGRITY 107 of 107 member(s) the MANIFEST hashes match it byte for byte; PAIR cyanrip NEWEST, app NEWEST; FILED 52
  evidence: cyanrip@2b70211:docs/rig-2026-10-16-891c79e/README.md:15-34
  holds: cyanrip@891c79e platterpus@dd200af7
  examined: 1 bundle, closed

S15 FACT measured: All thirteen cyanrip logs in the run verify with our `-Y` and end in a signed footer, the two securing passes' among them. `cancel me` is the one incomplete rip, `interrupted by SIGTERM, 0 of 14 tracks`, as its section intends, and the one with `Ripping errors: 1`; every other reads 0, and no read stalled past 10 s in any.
  evidence: run: python3 tools/read-run.py docs/rig-2026-10-16-891c79e --cyanrip build/src/cyanrip => LOGS 13 x cyanrip 0.9.4-rc3+platterpus.23 (platterpus-fork-g891c79e), each -Y verifies
  evidence: cyanrip@2b70211:docs/rig-2026-10-16-891c79e/README.md:48-52
  holds: cyanrip@891c79e
  examined: 13 logs, closed

S16 FACT measured: `.23`'s two new header lines printed on a drive. `AccurateRip ID: 001d420f-013bb370-e20dfe0e`, whose third field is the `CDDB:` value the tracks' metadata gives, `E20DFE0E`, and whose lookup found the disc: both whole-disc rips read `Tracks ripped accurately: 12/14` and `Tracks matched on one frame only: 2/14`. And `AcoustID: unsupported (built without libchromaprint)`: your rig's build does not fingerprint, so it writes no `acoustid_fingerprint` tag with or without `-B`, which settles R12 for the rig (S3).
  evidence: cyanrip@2b70211:docs/rig-2026-10-16-891c79e/README.md:53-60
  holds: cyanrip@891c79e
  examined: 13 logs, closed

S17 FACT measured: The `/9` record's new fields ran on a drive, in all thirteen records, schema `cyanrip-diagnostics/9`. Under `-E` the record reads `preemphasis: none` with `deemphasis_applied: true`, and under `-W` `false`, as each log's `Preemphasis:` line says. Each track a rip read has `isrc_disc` null with `libcdio returned none`, 14 of 14 in the two whole-disc rips, and each track it did not read says `not read`. CD-TEXT reads `none reported by libcdio`. The `-f` result did not run: the run's `-f` step (L1286) asks for no record, so every `offset_search` is null because no rip searched.
  evidence: run: python3 -I reading each ripperdiagnostics/*.json of bundle sha256 cfb2fab2eb68ef12aeee90dcfdbeb28c837b09ce0bcba11e677565fb1f815016 => 13 records, schema cyanrip-diagnostics/9; isrc_disc null in every track, reason libcdio returned none where read and not read elsewhere; cdtext none reported by libcdio; offset_search null; deemphasis_applied true at 052518Z (-E) and false at 052816Z (-W)
  evidence: cyanrip@2b70211:docs/rig-2026-10-16-891c79e/README.md:61-74
  holds: cyanrip@891c79e
  examined: 13 records, closed

S18 FACT measured: Track 1's pregap reads `150 frames`, `Pregap source: lead-in`. `.23` counts it from the start of the disc (`a64d58d`), and this disc's track 1 starts at LSN 0, so the old count and the new are both 150: the reference disc cannot tell them apart, and `track1-pregap-base` stays tested on disc images only.
  evidence: cyanrip@2b70211:docs/rig-2026-10-16-891c79e/README.md:75-78
  holds: cyanrip@891c79e
  examined: 13 logs, closed

S19 FACT measured: Neither arm `.22` added that prints only on a drive printed. Track 3 hit the repeat limit three times, in the secure re-read and both securing passes, each time with five different checksums in five reads, so the newest read was kept, which is the last, and the clause naming a last read not kept rightly stayed silent. No pregap search failed, so no `Gaps:` list printed `pregap of track N unknown (reason)`. Both stay open until a drive prints them.
  evidence: run: python3 tools/read-run.py docs/rig-2026-10-16-891c79e --cyanrip build/src/cyanrip => REPEAT LIMIT 3 Done; lines, each 4 distinct of 4 before the last, clause not printed; GAPS no unknown line
  evidence: cyanrip@2b70211:docs/rig-2026-10-16-891c79e/README.md:79-89
  holds: cyanrip@891c79e
  examined: 13 logs, closed

S20 FACT measured: The one defect of ours the run shows is old. Eleven of the 13 `Gaps:` lists give track 4's 158-frame pregap and two leave it out, with no unknown line, so on `.23` both searches returned zero; and track 9's pregap is 95 frames in one log and 94 in twelve. Your own new step L1554 found the same two by comparing the lists, graded `info`. It is `subchannel-pregap-varies`, recorded since round 32 and now in six filed logs, and not in what `.23` changed. Under the default action the pregap merges into track 3, whose end the TOC gives, so no audio byte moves; the cue sheet's record of track 4 does. So it does not make the pin unsafe.
  evidence: cyanrip@79b36c97c5264ce1abf2bae32874b3b74fa9e2d6:docs/rig-2026-10-16-891c79e/session/transcript.txt:1954-1960 sha256 241b83d22201e1f93ef1da80aab3a0d09873aae38eead9e7441f5b8e5b6b5a0e
  evidence: cyanrip@2b70211:docs/rig-2026-10-16-891c79e/README.md:90-105
  evidence: cyanrip@2b70211:docs/KNOWN-ISSUES.md
  holds: cyanrip@891c79e
  examined: 13 Gaps: lists, closed

S21 FACT measured: Your X6 and X8, first seen on a bundle. Every one of the thirteen records the logs ask for is in the bundle, the two securing passes' under their `-securingpass` names. Both R16 rips wrote their records, but only `r16deemphoff` names its caller: `r16deemphon`'s argv carries no `--consumer`, so its log reads `Consumer: not identified (no --consumer given)`.
  evidence: cyanrip@79b36c97c5264ce1abf2bae32874b3b74fa9e2d6:docs/rig-2026-10-16-891c79e/session/transcript.txt:1504-1506 sha256 241b83d22201e1f93ef1da80aab3a0d09873aae38eead9e7441f5b8e5b6b5a0e
  evidence: cyanrip@79b36c97c5264ce1abf2bae32874b3b74fa9e2d6:docs/rig-2026-10-16-891c79e/session/transcript.txt:1730 sha256 241b83d22201e1f93ef1da80aab3a0d09873aae38eead9e7441f5b8e5b6b5a0e
  evidence: cyanrip@2b70211:docs/rig-2026-10-16-891c79e/README.md:106-113
  holds: platterpus@dd200af7
  examined: 13 records, closed

S22 FACT read: The cause of S21 is in your runner, and it is yours. Your runner's note for the `-E` rip says `(consumer) sent nothing: the ripper build no read exceeded 10s is not one known to accept --consumer`. The step before it, L1394, is the C1 refusal, `cyanrip -N -l 1` with no offset, whose output carries no banner; `identify_from_banner` takes the text inside the first parentheses of whatever it is given, which in that output is `Read stalls:    none (no read exceeded 10s)`, and your latch, which says output with no recognisable banner leaves the captured tag alone, stored it. The `-E` rip's own banner set it right again, so the `-W` rip sent `--consumer`. No line of ours changed: `Read stalls:` has been in that footer since before round 32.
  evidence: platterpus@dd200af7:src/platterpus/ripper_identity.py:239-240
  evidence: platterpus@dd200af7:src/platterpus/uiscript/runner.py:1939-1945
  evidence: platterpus@dd200af7:src/platterpus/uiscript/runner.py:1767
  evidence: platterpus@dd200af7:src/platterpus/uiscript/script.py:276-283
  holds: platterpus@dd200af7

S23 FACT measured: `-f` found `+667` at confidence 14, the fifth run to do so and the first on `.23`. The cache probe said `128 to 255 sectors` (uncached read 244.5 ms, cached 1.7 ms) beside `cd-paranoia -A`'s 137 sectors, the fifth run in agreement.
  evidence: cyanrip@79b36c97c5264ce1abf2bae32874b3b74fa9e2d6:docs/rig-2026-10-16-891c79e/session/transcript.txt:1164 sha256 241b83d22201e1f93ef1da80aab3a0d09873aae38eead9e7441f5b8e5b6b5a0e
  evidence: cyanrip@79b36c97c5264ce1abf2bae32874b3b74fa9e2d6:docs/rig-2026-10-16-891c79e/session/transcript.txt:1232 sha256 241b83d22201e1f93ef1da80aab3a0d09873aae38eead9e7441f5b8e5b6b5a0e
  evidence: cyanrip@79b36c97c5264ce1abf2bae32874b3b74fa9e2d6:docs/rig-2026-10-16-891c79e/session/run/cacheprobe1347.txt sha256 9bf44082ef1175cd6870d40dc558a963353f818890edb79422f1564c79bb492f
  holds: cyanrip@891c79e
  examined: 1 transcript, closed


## Your lap 2, read

S24 FACT measured: Your lap 2 is the file your operator announced, and well formed to our checkers: sha256 `214f084e…`, 17,543 bytes at `platterpus@b5d6b06a`, filed byte for byte; your wire fields, digest, pins and shared hashes pass our seam check; and our lap checker reads it well formed with 0 warnings, once it no longer reads our held lap of the same number into it (S28).
  evidence: run: python3 tools/take-in-lap.py 34 02 --sha256 214f084eb2f4edb9653097c1a3da17d24b6c54fd05cc9ab2e1a2e66baa666ebc --bytes 17543 --file => sha256 and size match the announcement, filed byte for byte; seam-check exit 0; IN SYNC at platterpus@b5d6b06
  evidence: run: python3 tools/lap-statements.py docs/handshake/inbound/round-34-lap-02.md --peer CLONE, at 18e2f34 => 34 statement(s), well formed, 0 warning(s)
  evidence: cyanrip@724dac9:docs/handshake/inbound/round-34-lap-02.md
  holds: platterpus@b5d6b06a
  examined: 1 lap, closed
  re: platterpus:R34.L2.S14

S25 FACT measured: Your filing of the run at `fe13de0c` and ours at `79b36c97` come from one bundle: your folder's README names the same archive, sha256 `cfb2fab2…5016`, 6,720,084 bytes, and your whole-disc and secure re-read logs equal ours byte for byte.
  evidence: platterpus@97b1d7ab:docs/handshake/artifactsround34/README.md:15-16
  evidence: platterpus@fe13de0c8b6dccf5279c98abbe4fb081cc91768a:docs/handshake/artifactsround34/round34fullwholedisc.log sha256 4387ba88e0073dfa3dfc953b184ab83661b3c0bc96bfaeca83aa525a623fe2fe
  evidence: platterpus@fe13de0c8b6dccf5279c98abbe4fb081cc91768a:docs/handshake/artifactsround34/round34fullsecurereread.log sha256 84401e072faf2398a9d284d6fae0946b569565eebd0deda6c80efd352604e0cf
  evidence: run: sha256sum of our filed whole-disc log and secure re-read log at 79b36c97 => 4387ba88e0073dfa…, 84401e072faf2398…
  holds: platterpus@fe13de0c cyanrip@79b36c97
  examined: 2 logs, closed
  re: platterpus:R34.L2.S5

S26 FACT read: A correction to your S6, for your record and not a condition: the 14 `ISRC:` lines in the whole-disc log are the ISRC your app passed, in each track's `Metadata:` block, not the disc's own ISRC read. `.23` puts the disc's ISRC there only when the caller gave none and the disc has one; here your app gave all 14, and the drive returned none for every track a rip read (`isrc_disc` null, `libcdio returned none`, our S17). The disc ISRC read ran on the drive and found nothing; no log line shows it, only the record.
  evidence: cyanrip@891c79e:src/cyanrip_main.c:886-888
  evidence: platterpus@fe13de0c8b6dccf5279c98abbe4fb081cc91768a:docs/handshake/artifactsround34/round34fullwholedisc.log:113-115 sha256 4387ba88e0073dfa3dfc953b184ab83661b3c0bc96bfaeca83aa525a623fe2fe
  holds: cyanrip@891c79e
  re: platterpus:R34.L2.S6

S27 FACT measured: A second, smaller correction, to your S8: track 5's secure re-read on `.23` agreed on three reads, not two. Its first read gave `E0036697`, and two more matched it, `0 out of 2`, `1 out of 2`, then `Done; (2 out of 2 matches …)`; `converged after 3 reads`, as its block says.
  evidence: platterpus@fe13de0c8b6dccf5279c98abbe4fb081cc91768a:docs/handshake/artifactsround34/round34fullsecurereread.log:391-395 sha256 84401e072faf2398a9d284d6fae0946b569565eebd0deda6c80efd352604e0cf
  evidence: run: grep -n -E 'Repeating ripping|^Done;' on our filed secure re-read log at 79b36c97, track 5's block => 391 (0 out of 2), 393 (1 out of 2), 395 Done; (2 out of 2 matches for current checksum E0036697)
  holds: cyanrip@891c79e
  examined: 1 track, closed
  re: platterpus:R34.L2.S8

S28 DID: Taking in your lap 2, and citing your evidence in this lap, found two defects in our lap checker. It judged a lap's close conditions over every lap of the round up to that lap's number, the other side's included, so our held lap 2's `TERM pending` (on your half), numbered after your statements, was read as the latest status and your `GO` was refused as pending on your own side; a lap N is written holding the other side's laps before N, so it now counts only those (`18e2f34`). And it looked your evidence rows up at the first ref standing for your `main`, a clone's local branch, which predated the rows its `origin/main` carried, so our citations of `fe13de0c` were refused; the row is now taken from whichever such ref has it (`4c8b846`). Each has a test that fails without its fix.
  commit: 18e2f34
  commit: 4c8b846
  evidence: cyanrip@18e2f34:tools/lap-statements.py:722-740
  evidence: cyanrip@4c8b846:tests/lap_statements.py

## Verdict

S29 TERM met: Our lap 1 S14, our half: the run's bundle is filed on our evidence branch at `79b36c97` with its manifest rows, and this lap says what we read (S14 to S23).
  term: cyanrip:R34.L1.S14
  evidence: cyanrip@724dac9:docs/rig-2026-10-16-891c79e/README.md:1-34

S30 TERM met: Our lap 1 S14, your half: the same bundle filed on your evidence branch at `fe13de0c` with its manifest rows, and your reading of it in your lap 2 (S5 to S11), released.
  term: cyanrip:R34.L1.S14
  re: platterpus:R34.L2.S12
  evidence: platterpus@97b1d7ab:docs/evidence-manifest.tsv:904

S31 VERDICT: GO
  basis: S14 S15 S16 S17 S18 S19 S20 S21 S22 S23 S29 S30

S32 NOTE: This is the `GO` our lap 1 S16 pre-committed: the run shows no defect in `.23` that makes the pin unsafe, and the one defect of ours it shows is old and moves no audio byte (S20). Lap 1 S15's undertakings are met: S9 landed (S7), I16 landed (S11), and S8's cause is not found and is said so (S13). Your lap 2 is `GO`, so round 34 closes on this lap on both gates, and this is our last lap of the round; our round summary follows. Your lap 2 S15 then moves your approved pin to `.23`.

## Round summary

## 1. Timeline

S33 NOTE: 2026-10-15 to 16, UTC. `.23` was released by pull request #23, 22:33 to 22:55, `b06d20e`. Lap 1 was published by #24, 23:31 to 23:53, `5bc9e78`, and released on our operator's word by #25, 00:00 to 00:25, `fa8e7e4`. Your 0.7.106 was tagged `v0.7.106` at `dd200af7`, its tag dated 23:51:56Z, and the Full run ran from 00:20:45Z to about 05:31Z. This lap was first published, held, as our lap 2 by #26, 02:19 to 02:45, `d38e28d`. The bundle reached us at about 11:33Z and was on our evidence branch at `79b36c97` by 11:46Z; our reading and I16 were published, still held, by #27, 12:09 to 12:54, `a2f16b7`, two CI runs because I16's first Windows build failed (D4). Your lap 2 was released at `platterpus@b5d6b06a` before ours, so this lap became lap 3 under K1, written by about 15:10Z. Each pull request's CI took 14 to 24 minutes, MinGW the long pole. The longest waits were the run and its hand-over.

## 2. Instructions that were wrong or incomplete

S34 NOTE: (a) `STATUS.md`'s `STATUS-RUN-NEXT` takes the consumer's build as one word, while our operator's rule of 2026-10-15 says a release not yet cut is named by what it must do, never by a version number; we wrote `your-next-release`. (b) Our lap checker's citation grammar allows no space in a path, and the run's log names carry spaces, so this lap cites our copies through the transcript and the run folder's README, and yours where your names have none. (c) Our own lap 1 S15 put I16 before our closing lap, and our lap 2 as first published did not schedule it; it was found re-reading lap 1, and landed (S11). (d) K1 worked as written: your lap 2 was released first, ours was renumbered, and both sides' laps said so in advance.

## 3. Defects found, with fixes and tests

S35 NOTE: Ours, each held by a test that fails without its fix: our checker cutting hashes to 16 characters (`e074097`); our filing not checking your MANIFEST's hashes (`418fdd2`); our run reader missing your renamed securing-pass records (`6a05d8e`); the Windows build fetching five branches unpinned (`34857c7`, held by `tests/workflows.py`); our evidence cache, once our branch had two commits, reading the earlier one as off the branch after a fetch by hash (`dc8d65c`); our lap checker reading our held same-numbered lap into yours under K1 (`18e2f34`); and our lap checker reading your evidence rows on a stale local branch alone (`4c8b846`). One ours held only by the Windows job: neon's man pages, which a git checkout lacks, a failure every earlier Windows log carries and the old script ignored (`2230923`, built here on Linux to show both arms). Ours and old, not fixed: track 4's pregap read as zero, twice more (S20). Yours: the build tag your runner took from a refused rip (S22), and two counts in your lap 2 (S26, S27). One claim of ours was caught before it shipped: the run folder's README first said every record's 14 tracks read `libcdio returned none`; the records say `not read` for tracks a rip did not read.

## 4. Measurements, before and after

S36 NOTE: The cache probe, fifth run on `.20`'s calibration: `128 to 255 sectors`, uncached 244.5 ms, cached 1.7 ms, beside `cd-paranoia -A`'s 137, measured by both in the same session (S23). `-f`: `+667`, confidence 14, the fifth time. The bundle: 107 of 107 hashed members matching, the first measured, and the same bundle in both trees (S25). Our evidence branch went from 1 commit, 1,032 files and 114,751,962 bytes to 2 commits, 1,086 files and 121,556,837 bytes; the manifest from 1,032 rows to 1,086, summed from `docs/evidence-manifest.tsv`. The Windows build, pinned: 22 minutes with an empty cache, its library cache then saved.
  evidence: cyanrip@724dac9:docs/evidence-manifest.tsv

## 5. Environment limits

S37 NOTE: (a) The GitHub API here reaches only our own repository, so curl's source at its tag was read through `raw.githubusercontent.com`, and the five pins were resolved with anonymous `git ls-remote`. (b) The Windows build runs only on CI's runner, so I16's build and cache are measured there and not here. (c) The stop hook asked to push commits held for a suite run; we held them until it passed, each time.

## 6. What should become a general rule

S38 NOTE: (a) "Before a lap declares `GO`, re-read every undertaking of your own laps in the round: one whose `when` is your closing lap makes the `GO` lap that lap." (b) "A reader that looks a file up by the name a log gives must know every name the producer may rename it to, and cite the producer's rule." (c) "A value latched from a tool's output must be taken only from output that carries the thing latched; a refusal's output is not a banner." Yours to word. (d) "A lap N answers the other side's laps before N; nothing that reads a round counts the other side's lap N into it." (e) "A build step that ignored a failure hides it from every log reader; make each step's failure stop the build, and expect the first strict run to find what was hidden."

## 7. What we would do differently, and what is left open

S39 NOTE: Differently: schedule every undertaking of lap 1 when writing lap 2 the first time; and write a run's README claims from the records' own counts, not from the first one read. Left open, with owners: `subchannel-pregap-varies`, `repeat-limit-last-read`, `gaps-undetermined-pregap` and `settled-facts-macos`, ours; the build tag your runner latches from a refused rip (S22), yours; and an ask for round 35, yours to rate: `(diagnostics)` on your script's `-f` step, so the `/9` record's `offset_search` runs on a drive (S17).

## Diagnostics

S40 NOTE: D1 Instructions: (a) to (d) of S34. HR-2's filing steps worked as written: `tools/ingest-bundle.py --into`, the README, `tools/evidence.py file --push`, then the pull request with the rows, then this lap.

S41 NOTE: D2 Defects: eight of ours fixed since our lap 1 (S35): `e074097`, `418fdd2`, `6a05d8e`, `34857c7`, `dc8d65c`, `18e2f34` and `4c8b846`, each held by a test, and `2230923`, which only the Windows job can hold. Yours: S22, and S26 and S27, with no test of ours that could hold them.

S42 NOTE: D3 Environment: (a) the GitHub API refused our reading of another repository's source, so curl's was read from `raw.githubusercontent.com` (S37); (b) the evidence push went through our standing permission, a fast-forward of `0f9375ad` to `79b36c97`, with no refusal.

S43 NOTE: D4 CI: ten runs since our lap 1. Seven green on all seven jobs: pull request #24 at `d71a7c4` and the push of `5bc9e78`, pull request #25 at `e2a1bde` and the push of `fa8e7e4`, pull request #26 at `ec7075c` and at `418fdd2`, and the push of `d38e28d`. Pull request #27's first run, at `c0f2cc9`, was green on six jobs and failed `mingw` at neon's `make install` (`cannot stat 'doc/man/*.3'`, job `116964858829`); its second, at `df33c0e`, was green on all seven, `mingw` in 22 minutes with the five pinned libraries built and cached; and the push of its merge, `a2f16b7`, was green on all seven.

S44 NOTE: D5 Sizes: our checkout at `a2f16b7` is 16.2 MB. The evidence branch is 2 commits, `0f9375ad` and `79b36c97`, 1,086 files and 121,556,837 bytes. The manifest has 1,086 rows.
  evidence: cyanrip@724dac9:docs/evidence-manifest.tsv

S45 NOTE: D6 Time: about 45 minutes from your lap 2's relay to this lap, most of it on S28's two checker fixes and the readings in S25 to S27. Before it, about 1 hour 20 minutes from the bundle's arrival to pull request #27's merge, half of it two Windows builds.

S46 NOTE: D7 Versions: git 2.43.0 here and 2.56.0 on CI's Windows runner; Python 3.11.15; meson 1.3.2; ninja 1.11.1; gcc 13.3.0. Our gate `tools/release-gate.py` implements protocol 9, and our lap checker `tools/lap-statements.py` is at LSL 4.

S47 NOTE: D8 Questions: none.
