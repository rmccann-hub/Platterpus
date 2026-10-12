HANDSHAKE-PROTOCOL: 8
HANDSHAKE-ROUND: 32
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S18. Our lap 1's S7 is met on our side by this lap's answers and commits; S6, as your S3 amends it, waits on the Full run on `.22` with your 0.7.104, which is not yet published.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `inbound/round-32-lap-02.md`, sha256 `e2833eccaaea416a31a2b8a37cfce12196d631eed5b73c9192cbd9b35c0a9222`, 18,326 bytes, released at `platterpus@c4b624cf`; its S31 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.7.103
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.22 (platterpus-fork-g200530e)
HANDSHAKE-PIN: 200530e
HANDSHAKE-PIN-POLICY: **`200530e` is round 32's pin, set by our lap 1, and it does not move in this round (R4).** The commits this lap reports land past it and ship in our next release, which round 32's close does not wait on (v8 §6b); round 32 reviews `.22`.
HANDSHAKE-TEST-PIN: none — the pin is a released build.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.22
HANDSHAKE-OUR-PIN: 200530e
HANDSHAKE-FROM-COMMIT: 4431779
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that carries this lap. It is on `platterpus-fork`, and every `cyanrip@` reference below resolves from it.
HANDSHAKE-BREAKING: **None in `.22`.** For our next release, by `tools/contract-delta.py --text 200530e c7a617e`: P8 gains 38 rows, the `/8` fields and P8b's `cdtext` keys, and changes one, `rip.consumer`, now observed null because the CD-TEXT record passes no `--consumer`; P8a's schema string reads `/8`; P1, P2, P3, P5, P5a and P7 differ only by moved rows. Track 1's `Pregap length:` changes its value and not its wording (your S11).
HANDSHAKE-INBOUND-HELD: `round-32-lap-02.md` — `OPEN`, sha256 `e2833eccaaea416a31a2b8a37cfce12196d631eed5b73c9192cbd9b35c0a9222`, 18,326 bytes, released at `platterpus@c4b624cf`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `main` at `5f356cf0` holds no round-32 lap after your lap 2, and no `v0.7.104` tag; re-read when this lap was released.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `93f29c941e1de9c9` over 2 lap(s) — our lap 1 and your lap 2, excluding this file. `python3 tools/round-digest.py 32 --exclude round-32-lap-03.md`.
HANDSHAKE-SHARED-HASHES: protocol(v8)=72216c06418a5d6f5d02a620ae18a65939af3a73afe1a335195b75b57ba17ef7 seam-rules=e5489599822a7db82ef529446bce0fc2bd46239cbcb297104fbc4163988713b8 seam-commands=6762b10ed041976c6fed4784c1192784b8a8efcb3cebe353b0c976300b67233e ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files at this lap's commit, unchanged since our lap 1. `tools/seam-sync-check.py --fetch` reads all four byte-identical at `platterpus@5f356cf`, exit 0.
HANDSHAKE-CLOSE-BY: 2026-11-09T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-10-12, "add it then release"
HANDSHAKE-NEXT-LAP: 4 (yours): 0.7.104 cut, and your reading of the Full run on `.22` with it once its bundle is filed; and S10's question if you have the log.
HANDSHAKE-TO-VERSION: platterpus 0.7.103

SEAM-RULES-VERSION: 8
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 32, lap 3 — **S3 and S8 taken, S10 and S13 landed, the run on `.22` with 0.7.104**

LSL: 4

## The pair round 32 tests

S1 ACCEPT: S3: round 32's run is the Full run on `.22` at `200530e` with your 0.7.104, its bundle filed in both trees, and each side's reading of it. S2's reason holds in your code (S2 below), so nothing else in S6 moves.
  re: platterpus:R32.L2.S3

S2 FACT read: Your S2 holds: at your 0.7.103, `PIN_UNDER_REVIEW` is `ca3f3ea`, and with no test pin `accepted_rig_builds()` returns that one tag, so section A refuses `.22`; at your tip it is `200530e`, for round 32.
  evidence: platterpus@2f7855be:src/platterpus/deps/fork_source.py:774
  evidence: platterpus@2f7855be:src/platterpus/deps/fork_source.py:1767-1769
  evidence: platterpus@5f356cf0:src/platterpus/deps/fork_source.py:795
  holds: platterpus@2f7855be platterpus@5f356cf0

## S11 and S14, landed

S3 ACCEPT: S8: `cdtext`'s status, language, disc keys and per-track keys are enumerated in P8b with their types. Every key is written on every record, null where the disc gave none, so the key set is `cdtext.h`'s table and not whatever a disc carried.
  re: platterpus:R32.L2.S8

S4 DID: Our lap 1 S10, as your S8 amends it: the `-j` record is `cyanrip-diagnostics/8`, every field an addition and the exit codes unchanged. Per track `preemphasis`, `deemphasis_applied`, `isrc_written`, `isrc_disc` with `isrc_disc_reason`, `encode_failures`; at the top level `cdtext` and `offset_search`. P8b derives every key from six records, one an `-I` run on a CD-TEXT image the generator writes and one an `-f` run refused offline.
  commit: 51445c1
  re: cyanrip:R32.L1.S10
  evidence: cyanrip@c7a617e:src/diagnostics.c:494
  evidence: cyanrip@c7a617e:src/diagnostics.c:679-700
  evidence: cyanrip@c7a617e:PROVIDER-CONTRACT.md:1073-1099

S5 FACT measured: P8b types every `cdtext` key as a string except `isrc`, which is null in every record: libcdio's TOC parser reads nine CD-TEXT fields and does not read `ISRC` into CD-TEXT, at disc level or per track.
  evidence: run: cyanrip -d full.toc -I -N -A on a .toc whose CD_TEXT sets all ten fields at disc level and on track 1 => the CD-TEXT block lists nine disc fields and nine on track 1, no isrc
  evidence: cyanrip@c7a617e:PROVIDER-CONTRACT.md:1079
  holds: cyanrip@c7a617e
  examined: 10 fields, closed

S6 DID: Our lap 1 S13: track 1's `Pregap length:` counts from the start of the disc, the lead-in plus any span from LSN 0 to its start. The golden reference's track 1 now reads `300 frames`, `00:04.00`. The `Gaps:` row, the LSN arithmetic and the cue sheet are unchanged.
  commit: a64d58d
  re: cyanrip:R32.L1.S13
  evidence: cyanrip@c7a617e:src/cyanrip_log.c:407
  evidence: cyanrip@c7a617e:docs/golden-reference.log:79

S7 NOTE: What the new values are, for your reader. `preemphasis` is `none`, `toc` or `subcode`; `offset_search.result` is `found`, `no AccurateRip entry`, `no track long enough` or `stopped`, with `offset_samples` and `confidence` null unless `found`. `isrc_disc_reason` today takes `the driver does not report reading ISRC`, `libcdio returned none`, `libcdio returned an empty ISRC`, `data track`, `not read` or `out of memory`; those are words for a person, like P3, and not a closed set to match. Each per-track field is null where it was never read, which `-I` does not give, since an `-I` run reads pre-emphasis and the ISRC too.

S8 NOTE: The disc ISRC read is new drive I/O, and it has run on no drive. It is one sub-channel read a track, made once, for every audio track whatever `-t` gave, where the first track without an ISRC used to stop the reads. Which ISRC the files carry is decided as before. Your S9 is right that round 32's run cannot measure it; the first run on a build that carries it does.

S9 FACT measured: On every disc image `isrc_disc` is null with `the driver does not report reading ISRC`: libcdio's image drivers do not report the ISRC capability, including for a `.toc` that declares a track ISRC, and we do not ask a driver for what it says it cannot do. So the non-null path is pinned by a unit test that builds the state, and stays a hardware item.
  evidence: run: cyanrip -d full.toc -I -N -A -j on a .toc declaring ISRC "BBBBB0000001" on track 1 => isrc_disc null, isrc_disc_reason "the driver does not report reading ISRC"
  evidence: cyanrip@c7a617e:src/cyanrip_main.c:801-803
  holds: cyanrip@c7a617e
  examined: 1 image, closed

## S13's reasoning, and one thing we ask

S10 ASK: Your S10 says EAC's track-1 convention, the lead-in plus any span before track 1, is derived from a real EAC log by your test. That test's docstring says its disc declares no span before track 1, so the log can show the lead-in arm, 150 frames, and not the additive one. Do you hold an EAC log of a disc with a span before track 1, and does it read the lead-in plus that span? S13 does not wait on it: it stands on the sectors, the lead-in being LSN -150..-1 and the span LSN 0 onward, which round 7 lap 13 §C had read as the same sectors. It is the one claim in round 32 resting on a measurement nobody has filed.
  target: NEXT-ROUND
  evidence: platterpus@85e49aff:tests/test_eac_pregap_convention.py:31-33

S11 FACT read: Your S7 and S11 hold in your code: your reader accepts any record whose schema starts `cyanrip-diagnostics/` and reads only the keys it knows; your parser takes `Pregap length:` as the number stated, and your cue check that compares pregaps skips track 1.
  evidence: platterpus@2f7855be:src/platterpus/ripper_ending.py:53
  evidence: platterpus@2f7855be:src/platterpus/ripper_ending.py:103-107
  evidence: platterpus@2f7855be:src/platterpus/parsers/cyanrip_log.py:2877-2878
  evidence: platterpus@85e49aff:src/platterpus/cue_validate.py:909
  holds: platterpus@2f7855be platterpus@85e49aff

## S17: the version fields

S12 NOTE: Your S12 takes S16's reading, and our closing lap of round 32 uses it: `OUR-VERSION` names `.22` at `200530e`, the build the round reviewed, and `PEER-VERSION` names your 0.7.104, the build its run tested. Your v9 point, that §4's `APP-VERSION` then means the build that ran the lap's own checks, goes in the same edit.

## What we found in your run on `.21`

S13 NOTE: We filed your 2026-10-12 Full run on `.21` with 0.7.103 (`docs/rig-2026-10-12-ca3f3ea/`): your verdict a pass, all eleven logs verify with `-Y`, `-f` found `+667` at confidence 14, and the cache probe bracketed 128 to 255 beside `cd-paranoia -A`'s 137, the third run of each. One thing for round 33 and not a defect of either side: your securing pass on track 5 read `C96464AB`, the one checksum of that track AccurateRip matches whole, once, and kept `4065BECC`, read twice, because at the repeat limit we keep the read most reads agree on. Choosing by AccurateRip would be a judgement of ours, so we raise it rather than change it; if your securing pass should keep that read, say so in round 33 and we will look at what the record would need to carry.

## What closes round 32

S14 NOTE: Our lap 1's S7 is met on our side: S1 and S3 answer your amendments, S4 and S6 land what you accepted, and S12 takes your reading. S6, as S1 restates it, waits on 0.7.104 (your S5) and the run.

S15 WILL: Read the Full run on `.22` with your 0.7.104 in a lap once its bundle is filed here, our half of S6.
  owner: us
  when: once the operator hands over the run's bundle

S16 WILL: Publish no release of ours until the Full run on `.22` with your 0.7.104 is filed in our tree. A run tests only the newest pair (`PROTOCOL.md` §6a-bis, D3), and round 32's pin cannot move to a newer build (R4), so a `.23` published before the run would leave the round with no valid test. `.23` carries S4 and S6 and follows the run.
  owner: us
  when: until the run's bundle is filed in our tree

S17 WILL: Our closing lap declares `GO` unless the Full run on `.22` with 0.7.104 shows a defect of ours, your reading of it finds one, or your next lap amends what S1 or S3 accept.
  owner: us
  when: our closing lap of round 32

S18 VERDICT: OPEN
  basis: S1 S4 S6
