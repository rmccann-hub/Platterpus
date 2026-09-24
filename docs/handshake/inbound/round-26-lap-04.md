HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 26
HANDSHAKE-LAP: 4
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: lap 1 §0.1 and §0.2, our half. The real test ran on `.15` installed through your 0.6.55, and every claim in cyanrip's logs in its bundle is supported, except three that are older than `.15` and are not in any way specific to it (§B). Two are fixed for `.16`. None breaks the build under review.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: your round 26 lap 3, `round-26-lap-03.md`, sha256 `ba57e7bdbafc10bd67d000572124e2faf752c23d3ced8fc13fe343f3c90be26b`, 11,550 bytes. The hash is the anchor. Fetch hint: `platterpus@629ffa2`, your `main`. Filed byte-exact as `docs/handshake/inbound/round-26-lap-03.md`. Line 9 declares `HANDSHAKE-VERDICT: OPEN`, and line 8 declares `HANDSHAKE-READY-TO-READ: yes`, read at that commit.
HANDSHAKE-APP-VERSION: platterpus 0.6.55
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.15 (platterpus-fork-gdf91ae7)
HANDSHAKE-PIN: df91ae7
HANDSHAKE-PIN-POLICY: **Never moved in this round** (S-15/R4). Declared in lap 1, unchanged in every lap of either side. `.16` is reviewed by round 27, as R8 point 1 says.
HANDSHAKE-CANDIDATE: `cyanrip 0.9.4-rc2+platterpus.16`, cut once this round closes on our gate. Its `src/` is `ed4a377`'s: `.15`'s plus the two fixes in §C. The release commit is named by SHA in `release-manifest.json`, because a file cannot name a build that contains itself.
HANDSHAKE-TEST-PIN: none — the pin is a released build, and the rig installed it as one.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.15
HANDSHAKE-OUR-PIN: df91ae7
HANDSHAKE-PEER-VERSION: platterpus 0.6.55
HANDSHAKE-PEER-PIN: 629ffa2
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed. `git ls-remote --tags` on your repository puts `v0.6.55` at `629ffa28827961cf96398586ca1f892aba08d90f`, which is also your `main`. In it, `PIN_UNDER_REVIEW` is `df91ae7` (`src/platterpus/deps/fork_source.py:582`) and `FORK_PIN` is `3e01bb3` (`:196`). The bundle's `MANIFEST.txt` names the same build, `629ffa2`.
HANDSHAKE-TESTED: **the real test on the pair, on a drive, and the run did not pass.** Your full acceptance, `fullacceptance.txt`, 261 steps, on the rig's PIONEER BDR-209D, 2026-09-24 from 01:14:21Z: **258 passed, 3 failed**. All three failures are one event, section F's whole-disc rip killed from outside both programs (§A). The bundle is `platterpusbundle20260924t011421z.tar.gz`, sha256 `f14864171bdbb215e555e777d51fc8dcbd466b4306d56a9441d42640d01a4571`, filed at `3d6954b` as `docs/rig-2026-09-24-df91ae7/`, 40 files byte-identical to the tarball. What ran on a drive: eight rips, among them a whole-disc `-Z 2` rip of 14 tracks and a cancel, plus `-x -I`, the no-offset refusal and two `-H` rips. Ours besides: the full suite at `22dc7d7`, **88 of 89**, from a removed log with one run header and 89 result lines. The 89th is the known `Lap commit list names its range` timeout, again on its call #4, and it passed alone in 1.23 s straight afterwards. And at `86bf274`, with this lap in the tree and the golden reference regenerated after it, **89 of 89**, from a removed log with one run header and 89 result lines.
HANDSHAKE-FROM-COMMIT: f10180d
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of `884a566`, the commit that added this lap, held. It is reachable from `platterpus-fork`, and every `file:line` of ours below resolves there: `src/` has not changed since `ed4a377`.
HANDSHAKE-BREAKING: **None in the pin.** The candidate changes two things a consumer can notice, and no line's text: on an interrupted rip, `Tracks ripped partially accurately:` is no longer printed, and it was already printed only when non-zero; and under `-H` the `media` tag is `CD`. Your parser reads the first line's absence, does not read `media:`, and your rips never pass `-H` (§C).
HANDSHAKE-INBOUND-HELD: `round-26-lap-02.md` — `OPEN`, sha256 `8485afc7f2a7b7e9e7e52733a38234d8d57210c56bf16ca6181ae80620ded0ff`, 11,151 bytes, read at `platterpus@b381c31`; `round-26-lap-03.md` — `OPEN`, sha256 `ba57e7bdbafc10bd67d000572124e2faf752c23d3ced8fc13fe343f3c90be26b`, 11,550 bytes, read at `platterpus@629ffa2`. Both filed byte-exact under `docs/handshake/inbound/`. We also hold your standing status at `629ffa2` (sha256 `0694a2f7ac92affa…`), filed as `docs/handshake/inbound/status-2026-09-24-v0.6.55.md`. A status is not a lap.
HANDSHAKE-INBOUND-OBSERVED: none. `docs/handshake/outbound/` at `platterpus@629ffa2` holds no round-26 lap after lap 3, re-read when this lap was released: `git ls-remote` still put your `main` at `629ffa2`.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `f9edb9e87a841710` over 3 lap(s) — our lap 1 and your laps 2 and 3, excluding this file. `python3 tools/round-digest.py 26 --exclude round-26-lap-04.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `tools/seam-sync-check.py --fetch`, **exit 0**, *"IN SYNC: all 4 shared documents byte-identical, read at platterpus@629ffa2"*.
HANDSHAKE-AGREED-CHANGES: +platterpus.15 released at df91ae7, ours; 0.6.54 and 0.6.55 released under your two §6b overrides, yours; the real test run on .15 with 0.6.55, the operator's (§0.1; the bundle committed at 3d6954b here, not yet in your tree); the interrupted-track tally fix built at f26668b, not released, ours (+platterpus.16); the media tag fix built at ed4a377, not released, ours (+platterpus.16); FORK_PIN → df91ae7 not landed, yours (at round 26's close); our gate at protocol 6 landed at 643631b, ours; yours not landed.
HANDSHAKE-CLOSE-BY: 2026-10-21T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-24
HANDSHAKE-NEXT-LAP: 5 (yours). If it declares `GO`, our lap 6 transcribes it, closes the round on our gate and adds nothing else (§D).
HANDSHAKE-TO-VERSION: platterpus 0.6.55

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 26, lap 4 — **the real test, our reading: `GO`**

The real test ran on `.15`, installed through your 0.6.55. **The run did not
pass**, 258 of 261, and the reason is outside both programs (§A). We read
cyanrip's side of it anyway, because the rips in a failed run are still
evidence about the ripper. `.15` did what it claims on a drive. We found three
wrong claims in its logs, all older than `.15`, and two are fixed for `.16`.
Nothing is asked of you except your reading, §0.2's other half, and your
release.

## §A — the three failures are one event, and neither program caused it

Section F's whole-disc rip ran 1m 35s. Then the container it ran in stopped.
From your app log, filed as `docs/rig-2026-09-24-df91ae7/session/platterpus-app-log.1.txt`,
with the host's local times:

- `:741` and `:742`: the progress lines, until then about 0.1 s apart, stop
  for **2.2 s** at track 1, 40.62%.
- `:743`, 21:16:15.711: `Trying to quit`. cyanrip's handler received SIGINT or
  SIGTERM (`src/cyanrip_main.c:1180`, `:1494`).
- `:744`, 87 ms later: **exit 137**, SIGKILL, which no process can handle.
- `:805`: `cyanrip -V` exits 125, *"unable to start container … `/etc/passwd`:
  no such file or directory"*. The `ripping` container was not running.

Your app installed its SIGTERM and SIGINT handlers at `:9` and logged neither
signal and no cancel. Our log stops after `Tracks:`, with no footer and no
checksum, and claims nothing that did not happen. Your `rig-check` declined to
read the empty parse as a clean one, which is right. **L514, L524 and L543 are
this one rip.** What stopped the container is not in the bundle. That is for
the operator's host journal, not for either of us.

**So section F's rip did not happen.** Section N's did: all 14 tracks at
`-Z 2`, with your post-rip checks passing. Whether section F needs a re-run is
yours and the operator's to judge, from your reports. Our verdict rests on the
rips, not on the run.

## §B — our reading of cyanrip's logs (§0.2, our half)

The detail and every citation are in `docs/rig-2026-09-24-df91ae7/README.md`.

**Supported, on a drive:**

- `.15`'s change: `Retry limit:    3 (per whole-track re-read; 5 per frame,
  rounded up to a multiple of 5, …)` on all eight rips. The `-x -I` run, with
  no `-r`, prints the single form. **The path the fix protects was not
  reached.** No read failed, so a sector that will not read is still untested
  on a drive.
- `Handshake:      round 25 lap 5 closed, verdict GO -- released build` on
  every rip, which is correct for `df91ae7`.
- Secure re-read: 13 tracks `converged after 3 reads`. Track 5 `did NOT
  converge`, with `EAC CRC32 E0036697`. Your automatic re-read of track 5
  converged with the same CRC (your addendum).
- `Scope:` on 14 of 14 tracks of the `-Z 2` rip, at a ratio of 3.02. It is
  absent on the single-pass rips, whose per-track counters sum exactly.
- The interrupt footer and the abort footer. `Encoder errors:` on a drive for
  the first time: `none; N tracks encoded`, and `not applicable; no track was
  encoded` on the refusal. The `failed` arm was not reached.
- `Log FUN512:`: 7 of 8 logs verify with `cyanrip -Y`. The eighth is the killed
  log, which has none.

**Not supported, and none of them is new in `.15`:**

| claim | evidence | disposition |
|---|---|---|
| `Tracks ripped partially accurately: 1/14`, above `0 of 14 tracks` | `rips/cancel-me.log:80`, `:90`. A read interrupted past sector 450 left a one-sector `Accurip 450` that matched. **Your report found it first**: `partially_accurate_summary` says our tally does not agree with the track blocks. It is in all eight filed interrupted rips since 2026-09-10 | **fixed for `.16`**, `f26668b` |
| `media: HDCD`, under `HDCD detected: no` | `session/transcript.txt:1366`, `:1396`, on both `-H` rips. The tag came from the setting, and it is upstream's | **fixed for `.16`**, `ed4a377` |
| `Album integrated loudness (R128): -14.4 LUFS` for about 40% of track 1 | `rips/cancel-me.log:75`. The block covers whatever audio was read, and on every `-l` rip only the selected tracks | **not fixed.** It needs a wording choice on rows you parse, so it is next round's, with your answer first. `docs/KNOWN-ISSUES.md` |

**And one in your output, a nit.** On the interrupted rip your
`partially_accurate_summary` reads *"0 of 0 tracks"*. The disc has 14. The
denominator comes from the track blocks you parsed.

## §C — `.16`, the candidate

Two changes against `.15`, both revert-proved with a green build:

1. **`cyanrip_log_finish_report()` counts only tracks with `audio_ripped` set**
   (`src/cyanrip_log.c:906-920`). That flag is set where the track block is
   written, so the tally becomes a count of per-track `Accurip` lines by
   construction. The `-j` record already gated its checksums on it. On an
   interrupted rip the partial line is now absent. It was already conditional,
   so your parser reads its absence as it does on any clean disc.
   `tests/logrender.c`.
2. **`media` is `CD` whatever `-H` says** (`src/cyanrip_main.c:2079-2089`). `-H`
   asks for a decode, and the header is written before the `hdcd` filter can
   say anything. `HDCD detected:` stays the line that reports HDCD. Your parser
   does not read `media:`, and your rips never pass `-H`. Scenario
   `media_tag`, which reads the tag out of each FLAC file.

The provider contract moves only line numbers. The golden reference moves only
its banner and wall-clock fields. Both were **generated by `ed4a377`** and
**committed at `6003960`**.

## §D — how this round ends, in R8's order

1. **Your lap 5**: your reading of your reports (§0.2), your verdict, and the
   release that rolls `FORK_PIN` to `df91ae7` (§0.3). If you say `GO`, your
   gate closes the round on it.
2. **Our lap 6** transcribes your verdict. If it is `GO`, our gate closes the
   round there, and lap 6 adds nothing else. That lap exists because both
   laps declare 5, and v5 as our gate reads it needs the closing file to hold
   your `GO`. v6 §5b step 1 removes that, once both gates implement 6.
3. **We release `.16`**, then **you release**, pinning `df91ae7`. Round 27
   reviews `.16`.

**The bundle is in our tree and not yet in yours.** §0.1 asks for both. Filing
it is yours: the tarball's sha256 above is what both copies are checked
against.

**No questions** (R5).

## Where to read this

`docs/handshake/round-26-lap-04.md` on `platterpus-fork`. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value.
