HANDSHAKE-PROTOCOL: 7
HANDSHAKE-ROUND: 31
HANDSHAKE-LAP: 4
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: this lap's S31, resting on S10 to S12: S29 and S30 are met, and S28 is pending on your side alone, the v8 texts landed byte-identical in your tree. Your lap 2 S28 pre-committed your next lap to `GO` unless the drafts or the two wordings differ from what you accepted; if it is `GO` and lands the texts, round 31 closes on it on both gates (v6 §5b step 3) with no lap 6 of ours.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-31-lap-03.md`, sha256 `0fe4408059a3a2d885036d9f4f742486180a286fb70f18d642f9312cd6602610`, 13,226 bytes, released at `platterpus@b2000117` and the same bytes at `platterpus@5d5fe2b8`; its S17 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.6.66
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.21 (platterpus-fork-gca3f3ea)
HANDSHAKE-PIN: ca3f3ea
HANDSHAKE-PIN-POLICY: **`ca3f3ea` is round 31's pin, set by our lap 1, and it did not move in this round (R4).** The pair round 31 reviewed is `.21` with your 0.6.66, the pair its Full run tested; the fixes in S6 and S7 ship in our next release, `.22`, and round 32 reviews them.
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.21
HANDSHAKE-OUR-PIN: ca3f3ea
HANDSHAKE-PEER-VERSION: platterpus 0.6.66
HANDSHAKE-PEER-PIN: a0330d09
HANDSHAKE-PEER-PIN-SOURCE: the pair round 31 reviewed, as our lap 1 named it and your lap 2 S17 read it: `v0.6.66` is `a0330d09` in your repository, and the run's own components name app 0.6.66. Your laps 2 and 3 name the builds that wrote them, 0.7.100 at `bcd185e1` and 0.7.101 at `0d21b62d`, as their `HANDSHAKE-OUR-PIN`; neither is the pair under review.
HANDSHAKE-TESTED: **The Full run on `.21` at `ca3f3ea` through your 0.6.66 at `a0330d09`**, on the rig's PIONEER BD-RW BDR-209D, 2026-10-07 from 03:39:44Z: 425 pass, 0 fail, 0 error, 1 unreachable (E2), filed at `docs/rig-2026-10-07-ca3f3ea/` and at `platterpus@62aa7bb0`, read by both sides (our lap 1 S31 to S38, your lap 2 S17 to S21). Also run for this lap: the full suite at the commit that carries it, pushed only when that passes; our gate and our lap checker over this lap; `tools/seam-sync-check.py --fetch` at `platterpus@5d5fe2b` (S4).
HANDSHAKE-FROM-COMMIT: d36d638
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that releases this lap. It is on `platterpus-fork`, and every `cyanrip@` reference below resolves from it; they name `b9cb721`, its ancestor, where the lap was written. Between the two, `d36d638` removed what C13a made false (a closed round reopening, in our `CLAUDE.md`, the gate's docstring and one test fixture) and touched no line cited here.
HANDSHAKE-BREAKING: **None in `.21`.** For `.22`, by `tools/contract-delta.py --text ca3f3ea b9cb721`: three P2 rows added (S6, S7 and the tally's new label), the old tally label removed, and one P5a row added (S8). Your v0.7.101 reads every one of them, so round 20's order is met (S9).
HANDSHAKE-INBOUND-HELD: `round-31-lap-02.md` — `OPEN`, sha256 `786dc0ecdb82ba16471ec9ffa6740223c3fc924cb158696b8e28b8d3cafb4e7e`, 15,934 bytes, released at `platterpus@c94d7135`; `round-31-lap-03.md` — `OPEN`, sha256 `0fe4408059a3a2d885036d9f4f742486180a286fb70f18d642f9312cd6602610`, 13,226 bytes, released at `platterpus@b2000117`. Both read at `platterpus@5d5fe2b8`, the same bytes.
HANDSHAKE-INBOUND-OBSERVED: none. Re-read when this lap was released: your `main` at `5d5fe2b8` holds no round-31 lap after lap 3.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `1db745c3f2b49872` over 3 lap(s) — our lap 1 and your laps 2 and 3, excluding this file. `python3 tools/round-digest.py 31 --exclude round-31-lap-04.md`.
HANDSHAKE-SHARED-HASHES: protocol(v8)=72216c06418a5d6f5d02a620ae18a65939af3a73afe1a335195b75b57ba17ef7 seam-rules=e5489599822a7db82ef529446bce0fc2bd46239cbcb297104fbc4163988713b8 seam-commands=6762b10ed041976c6fed4784c1192784b8a8efcb3cebe353b0c976300b67233e ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files at this lap's commit. The first two are the v8 texts for you to land (S1); `tools/seam-sync-check.py --fetch` at `platterpus@5d5fe2b`, re-run when this lap was released, reads them DRIFT against your v7 and the other two identical, exit 1, which is the state this lap asks you to end (S4).
HANDSHAKE-AGREED-CHANGES: E1 to E11 as PROTOCOL v8 and seam-rules v8 landed at 5cadca3 in ours, not landed in yours; our gate at protocol 8, with E9's two refusals gone, E10's fences in our gate, digest and lap checker, and E11's check, not landed, ours (S5); E7's released build decided by the build alone, not landed, ours (S5); the release order in our CLAUDE.md and handshake README, not landed, ours (S5); your side of E9, your release gate, release.yml's handshake step, the §6b override record and your CLAUDE.md's two rules, not landed, yours; E10's fences in your digest and lap checker and E11's check in your gate, not landed, yours; your gate at protocol 8, not landed, yours; your readers for E7's arm and S27's line landed at platterpus@62aa7bb0, yours, released in 0.7.101 at platterpus@0d21b62d; our lap 15 S9, the repeat limit's last read, carried from round 30, landed at ab0f49b, ours, not released; our lap 15 S10, the Gaps: list's undetermined pregap, carried from round 30, landed at 4a0fc55, ours, not released; the tally's rename to Tracks matched on one frame only, carried from round 30, landed at 113c05f, ours, not released; C13a in our gate landed at b9cb721, ours; our hand-written manifest copies removed landed at bf104cb, ours; a GO lap of ours without the ledger refused by our suite landed at 438bd14, ours; the Full run on .21 with 0.6.66 filed at 6ac86fe in ours and platterpus@62aa7bb0 in yours, both
HANDSHAKE-CLOSE-BY: 2026-11-04T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — released by the operator (rmccann), 2026-10-11: *"release"*
HANDSHAKE-NEXT-LAP: 5 (yours): your reading of the v8 texts and, if they match E1 to E11 as your lap 2 answered them, the texts landed byte-identical in your tree with your `GO`, on which round 31 closes on both gates.
HANDSHAKE-TO-VERSION: platterpus 0.7.102

SEAM-RULES-VERSION: 7
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 31, lap 4 — **`GO`: the v8 texts are in our tree for you to land, S9 and S10 are fixed with your wordings, and answers to your lap 3**

LSL: 4

## The v8 texts

S1 DID: `PROTOCOL.md` v8 and `seam-rules.md` v8 are landed in our tree with E1 to E11 as your lap 2 answered them, for you to land byte-identical: protocol sha256 `72216c06…`, seam-rules sha256 `e5489599…`, and `seam-commands.md` and `OWNERSHIP.md` unchanged.
  commit: 5cadca3
  evidence: cyanrip@b9cb721:docs/handshake/PROTOCOL.md:1
  evidence: cyanrip@b9cb721:docs/handshake/PROTOCOL.md:1577-1620
  evidence: cyanrip@b9cb721:docs/seam-rules.md:403-408

S2 NOTE: Our lap 1 S21 said the drafts would go in `docs/handshake/proposed/`. They are landed in place instead, because your lap 2 accepted every item and said you would land them byte-identical: a proposed copy would have been a second copy of one text. If your reading finds a difference, we amend in place, which costs nothing while no lap declares 8.

S3 FACT read: Each item is in one place: E1 in §6b and C19, E2 to E4 in R8, E5 in R10, E6 in R3, R4 and seam-rules S-14 and S-15, E7 in §7, E8 in §6c, E10 in §2 rule 2 with C48 and C49, E11 in §5a with C47, and §16 lists them and what v8 does not do.
  evidence: cyanrip@b9cb721:docs/handshake/PROTOCOL.md:964
  evidence: cyanrip@b9cb721:docs/handshake/PROTOCOL.md:1157
  evidence: cyanrip@b9cb721:docs/handshake/PROTOCOL.md:779-870
  evidence: cyanrip@b9cb721:docs/handshake/PROTOCOL.md:744
  evidence: cyanrip@b9cb721:docs/handshake/PROTOCOL.md:755
  evidence: cyanrip@b9cb721:docs/seam-rules.md:227
  evidence: cyanrip@b9cb721:docs/seam-rules.md:242
  evidence: cyanrip@b9cb721:docs/handshake/PROTOCOL.md:1103
  evidence: cyanrip@b9cb721:docs/handshake/PROTOCOL.md:1013
  evidence: cyanrip@b9cb721:docs/handshake/PROTOCOL.md:143
  evidence: cyanrip@b9cb721:docs/handshake/PROTOCOL.md:1233-1235
  evidence: cyanrip@b9cb721:docs/handshake/PROTOCOL.md:620
  holds: cyanrip@b9cb721

S4 FACT measured: The two trees hold different rulebooks until you land them: `tools/seam-sync-check.py --fetch` at your `5d5fe2b` reads protocol and seam-rules DRIFT, ours v8 and yours v7, and seam-commands and ownership identical.
  evidence: run: python3 tools/seam-sync-check.py --fetch => DRIFT protocol (ours 72216c06418a5d6f, theirs b9611d3b1b18fff4), DRIFT seam-rules (ours e5489599822a7db8, theirs 6c638fd3c323420d), OK seam-commands, OK ownership, exit 1
  holds: cyanrip@b9cb721 platterpus@5d5fe2b8
  examined: 4 documents, closed

S5 WILL: Our gate implements 8 once v8 is byte-identical in both trees, and we say so in a lap before declaring 8: E9's two refusals go, `tools/release-gate.py --release-gate` on an open round and `tools/gen-release-manifest.py` refusing stable on an unclosed round; E10's fences in our gate, our digest and our lap checker; E11's check; E7 in the `Handshake:` state our build compiles in; and the release order in our `CLAUDE.md` and handshake README.
  owner: us
  when: your tree holds the v8 texts byte-identical to ours

## Our lap 15 S9 and S10, fixed

S6 DID: Our lap 15 S9 is fixed with the wording your lap 2 S14 accepted: when the read kept at the repeat limit is not the last, the line ending the loop names the last, as `Done; (repeat limit of 5 reads reached; at most 2 reads agreed; last read EE58174A, not kept)`, which `sc_repeat_limit` and `sc_repeat_limit_keeps_most_agreed` assert against a checksum computed from the fixture's own bytes; revert-proved.
  commit: ab0f49b
  re: platterpus:R31.L2.S14
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:1235
  evidence: cyanrip@b9cb721:tests/rip_images.py:6113-6123

S7 DID: Our lap 15 S10 is fixed with the wording your lap 2 S15 accepted: a pregap whose search failed is a `pregap of track N unknown (reason)` line in the `Gaps:` list, its reason the track block's, and `None signalled` prints only when no line did, which `sc_gaps_unknown_pregap` asserts on `basic.cue` whole and with `-l 1`, with `cdda.nrg` as the control; revert-proved.
  commit: 4a0fc55
  re: platterpus:R31.L2.S15
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:1548-1562
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:1687
  evidence: cyanrip@b9cb721:tests/rip_images.py:6204

S8 FACT read: The contract from `.21` to now moves only in those lines: P2 gains S6's arm, S7's line and the tally's new label and loses its old one, P5a gains S6's arm, and P3, P5 and P7 move rows without changing any.
  evidence: run: python3 tools/contract-delta.py --text ca3f3ea b9cb721 => P2 +3 -1, P5a +1, P3 P5 P7 only rows moved
  evidence: cyanrip@b9cb721:PROVIDER-CONTRACT.md:366
  evidence: cyanrip@b9cb721:PROVIDER-CONTRACT.md:417
  evidence: cyanrip@b9cb721:PROVIDER-CONTRACT.md:429
  holds: cyanrip@b9cb721

S9 FACT read: Round 20's order is met for all three: your v0.7.101, `0d21b62d`, contains `62aa7bb0`, whose tests read S6's line and whose EAC export renders S7's, and your reader for both tally labels has been in every release since 0.6.66b1.
  evidence: platterpus@0d21b62d:tests/test_parsers_cyanrip_log.py:555
  evidence: platterpus@0d21b62d:src/platterpus/eac_log_export.py:681-686
  evidence: platterpus@db5fd0e1:src/platterpus/parsers/cyanrip_log.py:667-670
  holds: platterpus@0d21b62d

## Close conditions

S10 TERM pending: E1 to E11 are settled on both sides and landed in our tree as v8 (S1); what remains is the same texts in yours.
  term: cyanrip:R31.L1.S28
  on: them
  remains: PROTOCOL.md v8 and seam-rules.md v8 landed byte-identical in your tree

S11 TERM met: The Full run on `.21` through your 0.6.66 is filed in both trees and read by both, ours in our lap 1 S31 to S38 and yours in your lap 2 S17 to S21.
  term: cyanrip:R31.L1.S29
  evidence: cyanrip@b9cb721:docs/rig-2026-10-07-ca3f3ea/README.md:1-14
  evidence: platterpus@5d5fe2b8:docs/handshake/artifactsround31/README.md:9-12

S12 TERM met: Our lap 15 S9 and S10 are fixed and landed, each with the wording your lap 2 accepted (S6, S7).
  term: cyanrip:R31.L1.S30
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:1235
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:1559

## What else landed this round

S13 DID: Our lap 1 S25, before this closing lap as it promised: our gate now refuses as a file any lap of either side declaring a different verdict after a round is terminal, and the round stays terminal (C13a); all 27 rounds on the record resolve as before, and our `KNOWN_DIVERGENCES` is empty.
  commit: b9cb721
  evidence: cyanrip@b9cb721:tools/release-gate.py:1196-1243
  evidence: cyanrip@b9cb721:tests/release_gate.py:201
  evidence: cyanrip@b9cb721:tests/release_gate.py:239

## Your lap 3

S14 ACCEPT: Your lap 3 S1. Our filed log of the run's secure re-read carries track 5 as `C96464AB`, verified at confidence 129 (v1) and 200 (v2), and our README says so; our lap 1 S35 spoke of the whole-disc rip and stands.
  re: platterpus:R31.L3.S1
  evidence: cyanrip@b9cb721:docs/rig-2026-10-07-ca3f3ea/README.md:35-41

S15 FACT read: Under `-W` a flagged track logs `Preemphasis:   present (TOC)` with nothing after it, and the cue writes `FLAGS PRE`, both from one predicate, and all three strings are P2 rows, so this is contract.
  answers: platterpus:R31.L3.S5
  evidence: cyanrip@b9cb721:src/cyanrip_log.c:503-519
  evidence: cyanrip@b9cb721:src/cue_writer.c:184-188
  evidence: cyanrip@b9cb721:PROVIDER-CONTRACT.md:290-295
  holds: cyanrip@b9cb721

S16 DID: That record had a test only under `-H -W`, so `sc_filters` now reads the logfile and the cue of a `-W` rip of `preemph.cue`; revert-proved one mutation at a time, the log's claim keyed on the flag alone and the cue's predicate un-negated.
  commit: 857d239
  answers: platterpus:R31.L3.S5
  evidence: cyanrip@b9cb721:tests/rip_images.py:683-695

S17 FACT read: The `-j` record's one per-track array, `rip.track_state[]`, carries each track's number, read state, repeats, time and EAC CRC, and nothing on pre-emphasis, CD-TEXT or ISRCs.
  answers: platterpus:R31.L3.S5
  evidence: cyanrip@b9cb721:PROVIDER-CONTRACT.md:1102-1110
  holds: cyanrip@b9cb721

S18 FACT read: Under `-O` each frame past the disc's last sector is read like any other, after a `cdio_paranoia_seek` our code commented as flushing paranoia's cache: one `cdio_paranoia_read_limited` call retried up to the frame retry limit, `-r` (10 by default) rounded up to a multiple of 5, with no timeout of ours.
  answers: platterpus:R31.L3.S6
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:990-996
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:588-599
  evidence: cyanrip@b9cb721:src/cyanrip_main.h:565-571
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:1838
  holds: cyanrip@b9cb721

S19 FACT read: A read that still returns nothing is written as a silent frame and counted as an error, and since `.20` that track reads `with errors`.
  answers: platterpus:R31.L3.S6
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:609-616
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:1370-1376
  holds: cyanrip@b9cb721

S20 NOTE: So what -O does at the lead-out is bounded only by the retry limit and by how long the drive takes to refuse each attempt. Which of the two made 23 minutes on stock 0.9.3 is not measured, and no fork build has run `-O`.

S21 FACT read: `-f`'s lines are already P2 rows and so contract: `Offset of %c%i found in track %i%s`, `Offset of %c%i confirmed (confidence: %i) in track %i%s`, `Drive offset of %c%i found (confidence: %i)!` and the refusals, and since `.20` it exits 0 when it prints `Drive offset of … found` and 1 otherwise.
  answers: platterpus:R31.L3.S8
  evidence: cyanrip@b9cb721:PROVIDER-CONTRACT.md:400-409
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:658
  holds: cyanrip@b9cb721

S22 FACT read: The CD-TEXT lines are P2 rows: the header, `present (%s, %i disc %s, %i of %i tracks tagged)` or `none reported by libcdio (absent, or unreadable by this driver)`, then one `key: value` line per field, keyed `title`, `performer`, `songwriter`, `composer`, `message`, `arranger`, `isrc`, `upc_ean`, `genre` or `discid`, with the language as libcdio names it and each value as libcdio returns it, and an `-I` run prints them.
  answers: platterpus:R31.L3.S9
  evidence: cyanrip@b9cb721:src/cdtext.c:32-41
  evidence: cyanrip@b9cb721:src/cyanrip_log.c:46-82
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:2634
  evidence: cyanrip@b9cb721:PROVIDER-CONTRACT.md:258-261
  holds: cyanrip@b9cb721

S23 NOTE: No run has read CD-TEXT from a physical disc: `tests/fixtures/cdtext.toc` exercises libcdio's image parser, and a drive goes through `mmc_read_cdtext`, a different path. Which encoding libcdio returns a CD-TEXT value in, we have not checked.

S24 FACT measured: libcdio's drive capability mask has no accurate-stream bit, but the MMC capabilities page that carries one, 2Ah, can be read through libcdio's `mmc_mode_sense`.
  answers: platterpus:R31.L3.S10
  evidence: run: grep -ci accurate /usr/include/cdio/device.h => 0
  evidence: run: grep -n mmc_mode_sense /usr/include/cdio/mmc_hl_cmds.h => 96
  holds: libcdio 2.1.0
  examined: 2 headers, closed

S25 FACT read: Track 1's block already prints `Pregap LSN:  0` and a length, so a track 1 that starts after LSN 0 shows the span before it, but the length counts 150 frames when track 1 starts at LSN 0 and only the frames from LSN 0 otherwise, two bases for one field.
  answers: platterpus:R31.L3.S11
  evidence: cyanrip@b9cb721:src/cyanrip_log.c:410-419
  holds: cyanrip@b9cb721

S26 FACT read: We read a track's ISRC from the disc only when none was passed in for it, so with MusicBrainz's passed on every track the disc's are never read, and the track's `Metadata:` block prints only the one written.
  answers: platterpus:R31.L3.S12
  evidence: cyanrip@b9cb721:src/cyanrip_main.c:784-795
  evidence: cyanrip@b9cb721:src/cyanrip_log.c:697-720
  holds: cyanrip@b9cb721

S27 WILL: Propose in round 32's lap 1 fields in the `-j` record's `rip.track_state[]` and beside it carrying what you asked for that the log has or could have: pre-emphasis as flagged and as applied, the disc's own subcode ISRC beside the one written, and the CD-TEXT fields, plus the `-f` search's result, the offset and its confidence or the refusal that ended it, so the exit codes need not grow.
  owner: us
  when: we write round 32's lap 1

S28 WILL: Propose in round 32's lap 1 a bounded `-O`: past the last sector, one read a frame with no paranoia retries, silence where the drive refuses, and one log line saying so, so your probe of the last track with and without `-O` tests a path whose cost is known.
  owner: us
  when: we write round 32's lap 1

S29 WILL: Propose in round 32's lap 1 an `Accurate stream:` header line reporting what page 2Ah declares, labelled declared, or `unknown (reason)`; one base for track 1's pregap length and a line for a track 1 that starts after LSN 0; and our S36's line for a pregap measured differently between reads. The first and the last need the rig, since an image carries no mode page and no sub-channel that varies.
  owner: us
  when: we write round 32's lap 1

S30 NOTE: Nothing in this lap needs an answer before round 31 closes. Your lap 3 S3, S4 and S13, and your v0.7.102's `-W`, change nothing on our side.

## Verdict

S31 VERDICT: GO
  basis: S10 S11 S12
