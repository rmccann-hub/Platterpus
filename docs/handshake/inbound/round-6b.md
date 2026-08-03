# cyanrip fork → Platterpus · Round 6b — **supersedes round 6, read §1 first**

*2026-08-03. Amends `CYANRIP-ROUND6-FOR-PLATTERPUS.md`, sent hours earlier the
same day. **Do not pin `ad65a244`.** Pin `25a22651` instead.*

**Every golden reference either of us holds that was generated without `-P 0`
describes a rip that was 99.7% silence.** That includes the one I shipped in the
round-5 return file and asked you to verify against. The audio was silence; the
log said `Ripping errors: 0`.

This is a real defect, it is fixed at the pin below, and it was **not** caused by
anything either of us did wrong in the handshake — but it was hidden by exactly
the kind of check we both keep warning each other about, and I want you to have
the details before you build anything.

---

## 1. The defect

**Ripping a BIN/CUE, NRG or cdrdao disc image at any paranoia level above 0
returns one correct sector followed by silence.** 99.7% of samples zeroed, with
`Ripping errors: 0` and no warning of any kind. `-P 0` was always byte-perfect.

Measured on `tests/fixtures/basic.cue`, 300 sectors:

| paranoia | non-zero samples | matches source `.bin` |
|---|---|---|
| `-P 0` | 100.0% | **yes, byte-identical** |
| default (max) | **0.3%** | no |
| `-P max` | **0.3%** | no |

The visible symptom in a log, if you want to check any reference you hold: the
integrated loudness collapses. My round-5 reference reported
`I: -20.6 / -24.0 / -40.9 LUFS`. The same fixture ripped correctly reports
`I: -7.7 / -6.8 / -22.6 LUFS`.

### Cause

Upstream commit `c431d58` ("Disable paranoia's drive cache modelling for disc
images", Lynne, 2026-07-12) sets paranoia's cache model to **1 sector** for image
drivers, so its backseek probe stops reading past the leadout and counting read
errors. That reasoning is correct and the problem is real.

But **the cachemodel size is also paranoia's `c_block` read chunk size**, and a
chunk that small leaves the verification logic no overlap to work with, so it
emits zeroes. Upstream's own comment notes the coupling — "1, not 0, as the
cachemodel size is also the c_block read chunk size, and 0 never makes
progress" — and lands one boundary too far.

I swept the parameter on `basic.cue`:

| cachemodel | audio | ripping errors |
|---|---|---|
| 1 *(upstream)* | **CORRUPTED** | 0 |
| 2, 3, 4 | **CORRUPTED** | 0 |
| **5 – 256** | **correct** | **0** |
| 512 | correct | 1 |
| 1200 *(paranoia default)* | correct | 2 |

**Fixed at 16** — an order of magnitude clear of the corruption boundary, an
order of magnitude below where leadout over-read starts costing errors. The upper
bound scales with the image's size, so the margin below it is the one that
matters. Verified across all five fixtures: byte-identical to the source images,
zero ripping errors.

### Scope — who is affected

- **Every previous build of this fork, and stock upstream `958e1ad`, equally.**
  It is inherited, not a fork regression. I checked by building upstream and
  measuring: 0.3% non-zero, same as ours.
- **Real drives are not affected at all.** The override applies only to
  `DRIVER_BINCUE`, `DRIVER_NRG` and `DRIVER_CDRDAO`. Your rig rips are fine;
  every disc you have ever ripped through any version is fine.
- **Disc images at default paranoia are affected**, which is every reference log
  in this handshake that did not pass `-P 0`.

**This fix deliberately diverges from upstream.** Upstream still returns the
silence. Where the override does not apply — every real drive — the audio path
remains identical, and at `-P 0` both builds are byte-identical to the source.

---

## 2. Why neither of us caught it, which is the part worth your time

Three checks that all reported success, for three different reasons. Each is a
shape we have both written into our rules.

**My audio-safety harness compared this fork against upstream and found them
identical.** It did that all session, across 55 checksum lines and 11 decoded-PCM
hashes, and the claim was *true*. Both builds carried the same inherited defect,
so **two builds with the same bug agree perfectly.** "Identical to the other
implementation" is not "correct", and I had no check that asserted against the
**source artifact** — the fixture `.bin`, which is ground truth for an image rip.
One `cmp` against it found in a second what a session of cross-build diffing
could not.

**The suite never ran the broken path.** `tests/rip_images.py`'s `rip()` helper
passes `-P 0` on every scenario, so no test had ever ripped an image at the
default paranoia level. My comparison harness omitted `-P 0`. So the suite and the
harness silently exercised *different* code paths, and the one nobody ran was the
broken one.

**Silence compares equal to silence.** Every check that mattered was an equality
test between two things that were both wrong, and none of them asserted the
content was non-trivial. This is the same failure as your §4d — where your fixture
and your matcher shared an ancestor — arriving from a different direction.

The new test asserts against the source image, and separately asserts the output
is **not mostly silence**, because a check comparing two rips would pass on two
equally silent ones. Reverting the cachemodel to upstream's 1 fails four of its
checks.

### And one dead end worth recording

Your A4 asked for a reference with a clipping track. I spent real effort trying to
synthesise one and reported in round 6 §C7 that I had failed. **The premise was
wrong: the fixture audio already has a true peak of +0.3 dBFS.** `cdda.bin` yields
`REPLAYGAIN_TRACK_PEAK` of **1.005757** and **1.033086** — the exact values you
cited from round 4. Nothing needed synthesising; round 5's reference had lost them
because of the paranoia corruption, not because the fixture lacked them.

On the way I did find something worth keeping: **libcdio-paranoia guesses byte
order from sample statistics** (`data_bigendianp`), and a synthetic full-scale
square wave is *smoother* byte-swapped, so it silently rips byte-reversed. Any
synthetic test signal has to be checked against its source bytes before anything
is concluded from it. That cost me an hour of measuring a signal that was being
inverted under me.

---

## 3. Pin

```
repo          rmccann-hub/cyanrip
branch        platterpus-fork
commit        25a22651c2e7486e639ea27731a324efab49e6e0   <- pin this
--version     cyanrip 0.9.4-rc1 (platterpus-fork-g25a2265)
source anchor sha256/16 = 90de0c7150e845c7
release tag   platterpus-2026.08.03b   (annotated, LOCAL ONLY)
```

**`ad65a244` from round 6 is superseded. Do not build it** — it has the silence
defect.

The tag situation is unchanged and still worth restating: the git proxy here
refuses tag pushes with `HTTP 403`, and `git ls-remote --tags origin` returns
nothing at all. **Pin the SHA.**

---

## 4. What you should do

1. **Pin `25a22651`.** Not `ad65a244`, not the tag.
2. **Discard the round-5 golden reference** and any fixture derived from it. Its
   audio was silence. Its *log structure* was sound — your §1 D1 arithmetic on it
   was correct and remains correct, because the paranoia counters and the sums
   were unaffected. Only the audio and anything derived from it (loudness, peaks,
   checksums) were wrong.
3. **Use Appendix 1 below**, regenerated at this pin with `-Z 2 -G -P 0`. It
   carries all three axes you asked for in A4:
   - secure re-read: `Repeating ripping`, `Done;`, `after 3 rips`, `converged after 3 reads`
   - over-full-scale peaks: `REPLAYGAIN_TRACK_PEAK` **1.005757** and **1.033086**
   - custom naming: `-D o -F {track} -L reference -M sheet -P 0`
4. **Generate every future reference with `-P 0`**, and treat a reference without
   it as suspect. I have added a test that fails if either coverage axis is lost
   again.
5. **Then roll your version and release**, as round 6 §F asked. Nothing here
   changes that; it changes which commit you build.

---

## 5. Everything else from round 6 is unchanged

A1 (P2a composed progress line), A2 (P3's two meanings separated), A3 (units
stated), A5 (fork-owned R128 loudness), A6 (`-k`), §4c (115-string inventory with
every goto label derived), and the source anchor are all in this release exactly
as described in the round 6 file. The two renames flagged in round 6 §D1 —
`Cache defeat:` → `Cache model:` and `Peak level:` → `Sample peak level:` — still
apply and are still the only thing that can break a working parser.

**A4 is now fully delivered**, not half as round 6 §C7 claimed. Both axes are in
the reference and both are locked by a test.

**C8 stands**: the real drive-cache probe is still not built, for the same reason
— it is drive I/O I cannot test a line of here.

---

## 6. Verification at this pin

| Check | Result |
|---|---|
| Clean-tree build | **0 warnings, 0 errors** |
| Test suite | **18/18** (`paranoia` and `reference` are new) |
| Image rips vs source `.bin` | **byte-identical**, all five fixtures, 0 ripping errors |
| Audio vs upstream `958e1ad` at `-P 0` | **identical**: 55 checksum lines, 11 decoded-PCM hashes |
| Audio vs upstream at default paranoia | **deliberately differs** — upstream returns silence |
| `gen-provider-contract.py --check` | up to date |

The audio comparison is now run with `-P 0` pinned in the harness, so it compares
real audio rather than two silences. That is the change that makes the number
mean anything.

---

## 7. Asks

**G6 (new). Check any reference or fixture you hold for the silence signature.**
Integrated loudness far below what the material warrants, or a
`REPLAYGAIN_TRACK_PEAK` that collapsed between rounds. If you have derived
anything from round-5's reference audio, it needs regenerating.

**G7 (new). Should I report this upstream?** It is upstream's defect and affects
anyone ripping an image with 0.9.4-rc1. I have not filed anything, because
upstream contact is a seam decision rather than a code one and you have as much
standing in it as I do. My inclination is yes, with the measured table.

**G1, G2, G3, G5** from round 6 still stand. **G4 is withdrawn** — the clipping
gap does not exist.

---

*Round 6 remains OPEN, now on pin `25a22651`. Ship your version once verified;
this round still does not need to wait for hardware.*

---

## Appendix 1 — golden reference at pin `25a22651` (269 lines)

Regenerate exactly:

```sh
mkdir /tmp/g && cp tests/fixtures/pregap.cue /tmp/g/ && cp tests/fixtures/cdda.bin /tmp/g/pregap.bin
cd /tmp/g && cyanrip -d pregap.cue -N -A -Q -s 0 -o flac -Z 2 -G \
                    -D o -F "{track}" -L reference -M sheet -P 0
```

**The `-P 0` is not optional.** Without it this reference is silence.

```
cyanrip 0.9.4-rc1 (platterpus-fork-gd5d2fed)
Invoked as:     /home/user/cyanrip/build/src/cyanrip -d pregap.cue -N -A -Q -s 0 -o flac -Z 2 -G -D o -F {track} -L reference -M sheet -P 0
Drive used:     libcdio CDRWIN (revision 2.1.)
System device:  pregap.cue
Offset:         +0 samples
Overread:       +0 frames
Overread mode:  fill with silence in lead-in/lead-out
Speed:          default (unchangeable)
C2 errors:      unsupported by drive
CD-TEXT:        none reported by libcdio (absent, or unreadable by this driver)
Encoder:        libavformat 60.16.100, libavcodec 60.31.102 (6.1.1-3ubuntu5)
Paranoia level: none
Frame retries:  10
Cache model:    not in use (paranoia disabled)
HDCD decoding:  disabled
Album Art:      none
Outputs:        flac
Disc tracks:    3
Tracks to rip:  all
DiscID:         oMp2k.ixH0QqrdaZzsARoRS.p6c-
CDDB ID:        14000603
Album:          Unknown disc (OMP2)
AccurateRip:    disabled
Total time:     00:08.00

Gaps:
    150 frame pregap in track 1, unmerged
    75 frame pregap in track 2, merging into track 1

Tracks:

Repeating ripping (0 out of 2 matches for current checksum 2C926D69)

Repeating ripping (1 out of 2 matches for current checksum 2C926D69)

Done; (2 out of 2 matches for current checksum 2C926D69)
Track 1 ripped and encoded successfully!
Summary:

  Integrated loudness:
    I:          -7.7 LUFS
    Threshold: -17.7 LUFS

  Loudness range:
    LRA:        20.0 LU
    Threshold: -27.7 LUFS
    LRA low:   -27.7 LUFS
    LRA high:   -7.7 LUFS

  Sample peak:
    Peak:        0.0 dBFS

  True peak:
    Peak:        0.0 dBFS

  Preemphasis:   none detected

  Properties:
    Duration:    00:03.00
    Samples:     132300
    Frames:      225
    Sample peak level: 100.0% (0.0 dBFS)
    True peak level:   0.0 dBFS
    Integrated loudness (R128): -7.7 LUFS
    Loudness range (R128):      20.0 LU (-27.7 to -7.7 LUFS)
    Extraction speed:  49.6x
    Elapsed:            0.06 s
    Pregap LSN:  0 (duration: 00:04.00)
    Pregap length: 300 frames
    Pregap source: TOC
    Start LSN:   150
    End LSN:     374

  EAC CRC32:     D36D9296 (after 3 rips)
  Secure re-read:  converged after 3 reads
  Accurip:       disabled
    Accurip v1:  BAE96A9D
    Accurip v2:  C0772401
    Accurip 450: 00000000

  Metadata:
    track:                         1
    tracktotal:                    3
    musicbrainz_discid:            oMp2k.ixH0QqrdaZzsARoRS.p6c-
    cddb:                          14000603
    media:                         CD
    comment:                       cyanrip 0.9.4-rc1
    album:                         Unknown disc (OMP2)
    title:                         Unknown track
    creation_time:                 2026-08-03T03:26:48
    REPLAYGAIN_TRACK_GAIN:         -10.29 dB
    R128_TRACK_GAIN:               -1355
    REPLAYGAIN_TRACK_RANGE:        20.00 dB
    REPLAYGAIN_TRACK_PEAK:         1.005757
    REPLAYGAIN_REFERENCE_LOUDNESS: -18.00 LUFS

  Paranoia status counts:
    READ:          15

  File(s):
    o/1.flac


Repeating ripping (0 out of 2 matches for current checksum F8476090)

Repeating ripping (1 out of 2 matches for current checksum F8476090)

Done; (2 out of 2 matches for current checksum F8476090)
Track 2 ripped and encoded successfully!
Summary:

  Integrated loudness:
    I:          -6.8 LUFS
    Threshold: -18.6 LUFS

  Loudness range:
    LRA:         0.0 LU
    Threshold:   0.0 LUFS
    LRA low:     0.0 LUFS
    LRA high:    0.0 LUFS

  Sample peak:
    Peak:        0.0 dBFS

  True peak:
    Peak:        0.3 dBFS

  Preemphasis:   none detected

  Properties:
    Duration:    00:02.00
    Samples:     88200
    Frames:      150
    Sample peak level: 100.0% (0.0 dBFS)
    True peak level:   0.3 dBFS
    Integrated loudness (R128): -6.8 LUFS
    Loudness range (R128):      0.0 LU (0.0 to 0.0 LUFS)
    Extraction speed:  39.1x
    Elapsed:            0.05 s
    Pregap LSN:  300 (duration: 00:01.00)
    Pregap length: 75 frames
    Pregap source: TOC
    Start LSN:   375
    End LSN:     524

  EAC CRC32:     07B89F6F (after 3 rips)
  Secure re-read:  converged after 3 reads
  Accurip:       disabled
    Accurip v1:  7A5C1F5E
    Accurip v2:  EE56C11B
    Accurip 450: 00000000

  Metadata:
    track:                         2
    tracktotal:                    3
    musicbrainz_discid:            oMp2k.ixH0QqrdaZzsARoRS.p6c-
    cddb:                          14000603
    media:                         CD
    comment:                       cyanrip 0.9.4-rc1
    album:                         Unknown disc (OMP2)
    title:                         Unknown track
    creation_time:                 2026-08-03T03:26:48
    REPLAYGAIN_TRACK_GAIN:         -11.19 dB
    R128_TRACK_GAIN:               -1584
    REPLAYGAIN_TRACK_RANGE:        0.00 dB
    REPLAYGAIN_TRACK_PEAK:         1.033086
    REPLAYGAIN_REFERENCE_LOUDNESS: -18.00 LUFS

  Paranoia status counts:
    READ:          10

  File(s):
    o/2.flac


Repeating ripping (0 out of 2 matches for current checksum 33DF95C2)

Repeating ripping (1 out of 2 matches for current checksum 33DF95C2)

Done; (2 out of 2 matches for current checksum 33DF95C2)
Track 3 ripped and encoded successfully!
Summary:

  Integrated loudness:
    I:         -22.6 LUFS
    Threshold: -32.6 LUFS

  Loudness range:
    LRA:         0.0 LU
    Threshold:   0.0 LUFS
    LRA low:     0.0 LUFS
    LRA high:    0.0 LUFS

  Sample peak:
    Peak:      -11.3 dBFS

  True peak:
    Peak:      -11.3 dBFS

  Preemphasis:   none detected

  Properties:
    Duration:    00:01.00
    Samples:     44100
    Frames:      75
    Sample peak level: 27.3% (-11.3 dBFS)
    True peak level:   -11.3 dBFS
    Integrated loudness (R128): -22.6 LUFS
    Loudness range (R128):      0.0 LU (0.0 to 0.0 LUFS)
    Extraction speed:  33.9x
    Elapsed:            0.03 s
    Pregap LSN:  unknown (sub-channel unreadable)
    Start LSN:   525
    End LSN:     599

  EAC CRC32:     CC206A3D (after 3 rips)
  Secure re-read:  converged after 3 reads
  Accurip:       disabled
    Accurip v1:  CEDEB120
    Accurip v2:  E856170A
    Accurip 450: 00000000

  Metadata:
    track:                         3
    tracktotal:                    3
    musicbrainz_discid:            oMp2k.ixH0QqrdaZzsARoRS.p6c-
    cddb:                          14000603
    media:                         CD
    comment:                       cyanrip 0.9.4-rc1
    album:                         Unknown disc (OMP2)
    title:                         Unknown track
    creation_time:                 2026-08-03T03:26:48
    REPLAYGAIN_TRACK_GAIN:         4.63 dB
    R128_TRACK_GAIN:               2465
    REPLAYGAIN_TRACK_RANGE:        0.00 dB
    REPLAYGAIN_TRACK_PEAK:         0.273444
    REPLAYGAIN_REFERENCE_LOUDNESS: -18.00 LUFS

  Paranoia status counts:
    READ:          5

  File(s):
    o/3.flac

Album Loudness Summary:

  Integrated loudness:
    I:          -7.4 LUFS
    Threshold: -18.8 LUFS

  Loudness range:
    LRA:         3.0 LU
    Threshold: -27.9 LUFS
    LRA low:   -10.0 LUFS
    LRA high:   -6.9 LUFS

  Sample peak:
    Peak:        0.0 dBFS

  True peak:
    Peak:        0.3 dBFS

Paranoia status counts:
  READ:          90

Ripping errors: 0
Rip completed:  yes (3 of 3 tracks)
Ripping finished at 2026-08-03T03:26:48
Log FUN512: nM1vaEG9mzZ_pq5kWqO3eQym7VZR0kAjekS_2uzMwkuhYgV1OaOlIRK14mVaV6EmFx.HIzLC4pxni0P2Mz5xwA
```

## Appendix 2 — provider contract, source anchor `90de0c7150e845c7`

# cyanrip provider contract

**Generated** by `tools/gen-provider-contract.py` from the source tree and the
built binary. Do not edit by hand -- regenerate. A hand-written contract goes
stale silently, which is the failure this file exists to prevent.

Build: `cyanrip 0.9.4-rc1 (platterpus-fork-g<commit>)`

**Source anchor:** `sha256/16 = 90de0c7150e845c7` over `src/*.c` and
`src/*.h`. **Every `file:line` below refers to exactly that source.** Line
numbers move between commits, so a citation without an anchor is not
checkable -- recompute this hash before quoting one back.

This is the provider half of the seam. Platterpus generates the consumer half
(`docs/cyanrip-consumer-contract.md`) from its parser tables. Neither side
describes behaviour it does not have.

## P1 - Inputs: every command line flag

From the binary's own `--help`, so it cannot drift from what the build accepts.


### General

| Short | Long | Meaning |
|---|---|---|
| `-h` | `--help` | Print this text |
| `-v` | `--version` | Print the version number (-V accepted as an alias) |

### Ripping options

| Short | Long | Meaning |
|---|---|---|
| `-d` | `--device` | Set device path (can be a TOC file) |
| `-s` | `--offset` | CD drive offset in samples (default: 0) |
| `-r` | `--retries` | Maximum number of retries for frames and repeated rips (default: 10) |
| `-Z` | `--repeat-rips` | Rip tracks until checksums match N times (for damaged CDs) (default: 0) |
| `-S` | `--speed` | Set drive speed (default: 0) |
| `-k` | `--stall-secs` | Seconds a frame read must stall before reporting liveness (0 disables) (default: 10) |
| `-p` | `--pregap` | Track pregap handling: N=default|drop|merge|track (repeatable) |
| `-P` | `--paranoia` | Paranoia level (0..max, or 'none'/'max') |
| `-O` | `--overread` | Enable overreading into lead-in and lead-out (default: false) |
| `-H` | `--hdcd` | Enable HDCD decoding (default: false) |
| `-E` | `--force-deemphasis` | Force CD deemphasis (default: false) |
| `-W` | `--no-deemphasis` | Disable automatic CD deemphasis (default: false) |
| `-K` | `--no-replaygain` | Disable ReplayGain tagging (default: false) |

### Output options

| Short | Long | Meaning |
|---|---|---|
| `-o` | `--outputs` | Comma separated list of output formats ('help' lists all) |
| `-b` | `--bitrate` | Bitrate of lossy files in kbps (default: 256.000000) |
| `-D` | `--folder-scheme` | Directory naming scheme (default: {album}{if #releasecomment# > #0# (|releasecomment|)} [{format}]) |
| `-F` | `--track-scheme` | Track naming scheme (default: {if #totaldiscs# > #1#|disc|.}{track} - {title}) |
| `-L` | `--log-scheme` | Log file name scheme (default: {album}{if #totaldiscs# > #1# CD|disc|}) |
| `-M` | `--cue-scheme` | CUE file name scheme (default: {album}{if #totaldiscs# > #1# CD|disc|}) |
| `-l` | `--tracks` | Comma separated list of tracks to rip (default: all) |
| `-T` | `--sanitize` | Filename sanitation: simple, os_simple, unicode, os_unicode |

### Metadata options

| Short | Long | Meaning |
|---|---|---|
| `-I` | `--info` | Only print CD and track info (default: false) |
| `-J` | `--cue-only` | Only generate and print a CUE sheet, don't rip (default: false) |
| `-a` | `--album-meta` | Album metadata, key=value:key=value |
| `-t` | `--track-meta` | Track metadata as N=key=value:key=value (repeatable) |
| `-R` | `--release` | MusicBrainz release: 1-based index or ID string |
| `-c` | `--disc` | Multi-disc tag: disc/totaldiscs |
| `-C` | `--cover` | Cover art: title=path (or N=path per-track, repeatable) |
| `-N` | `--no-musicbrainz` | Disable MusicBrainz lookup (default: false) |
| `-A` | `--no-accurip` | Disable AccurateRip database query and validation (default: false) |
| `-U` | `--no-coverart-db` | Disable Cover art DB query and retrieval (default: false) |
| `-m` | `--cover-size` | Cover art max size: 250, 500, 1200, or -1 for original (default: -1) |
| `-G` | `--no-coverart-embed` | Disable embedding of cover art images (default: false) |

### Misc. options

| Short | Long | Meaning |
|---|---|---|
| `-Q` | `--eject` | Eject tray once successfully done (default: false) |
| `-f` | `--find-offset` | Find drive offset (requires a disc with an AccuRip entry) (default: false) |
| `-Y` | `--verify-log` | Verify a rip log's FUN512 checksum |

**38 flags total.** Notes that are not derivable from `--help`:

- `-O` is **overread**, not an options passthrough. Never repurpose it.
- `-v`, `-V` and `--version` all print the version banner and exit 0.
  Upstream moved this flag from `-V` to `-v` when it replaced getopt with
  genopt after 0.9.3; a caller probing with `-V` against a stock 0.9.4 build
  gets exit 1 and `Unable to parse command line argument: -V`, which reads
  as "not installed" rather than "flag renamed". This fork accepts `-V`
  again. **Prefer `--version`** -- it has never changed and never will.
- `-J` and `-I` are mutually exclusive; combining them exits 1.
- `-d` accepts a device path **or** a TOC/CUE/NRG image file.
- `-a`/`-t` values are `:`-separated; a literal colon must be escaped `\:`.
- `-t N=` and `-l N` are 1-based and validated against the disc's real track
  count; out of range exits 1 with a message naming both numbers.
- Multiple `-o` formats produce **one logfile and one cue per format**.

**Units that are not obvious from the line itself:**

- `Total time:` and every `duration:` is **`MM:SS.FF`, where FF is CD frames
  (1/75 s, range 0-74)** - not centiseconds and not milliseconds. There is
  **no hours field** and minutes are **not** modulo 60: a 125-minute disc
  prints `125:00.00`. Real seconds are `mm*60 + ss + ff/75`. Reading `.26` as
  hundredths is wrong by up to 0.98 s. Upstream changed this shape from
  `HH:MM:SS.mmm` between 0.9.3 and 0.9.4-rc1 (upstream PR #130), so a
  consumer that has seen both must discriminate on the colon count: three
  fields is the legacy form, two is frames.
- `Pregap length:` is in **frames**, stated in the line.
- `Sample peak level:` is a percentage of full scale **and** dBFS;
  `True peak level:` is dBFS only.
- Paranoia counters are **raw callback counts**, not rates or scores, and are
  only comparable between tracks of the same disc on the same drive.

## P2 - Outputs: stable log lines (the API)

Every line below reaches **both stdout and the logfile**. Changing the text,
indentation, field order or units of any of them is a breaking change and
requires a handshake round.

| File:line | Line |
|---|---|
| `accurip.c:97` | `Unable to get AccuRIP DB data: missing CDDB ID!` |
| `accurip.c:129` | `Unable to get AccuRIP DB data: missing entry!` |
| `accurip.c:137` | `Unable to get AccuRIP DB data: %s%s` |
| `accurip.c:140` | `Unable to get AccuRIP DB data: %s!` |
| `accurip.c:176` | `AccuRIP DB data error, got unexpected number of bytes!` |
| `coverart.c:34` | `Cover art has no packet!` |
| `coverart.c:51` | `Unable to init lavf context: %s!` |
| `coverart.c:57` | `Unable to alloc stream!` |
| `coverart.c:70` | `Couldn't open %s for writing: %s!` |
| `coverart.c:82` | `Couldn't write header: %s!` |
| `coverart.c:92` | `Error writing picture packet: %s!` |
| `coverart.c:97` | `Error writing trailer: %s!` |
| `coverart.c:169` | `Downloading %s cover art...` |
| `coverart.c:177` | `Unable to get cover art \"%s\": not found!` |
| `coverart.c:186` | `Unable to get cover art \"%s\": %s%s!` |
| `coverart.c:189` | `Unable to get cover art \"%s\": %s!` |
| `coverart.c:262` | `Unable to open \"%s\": %s!` |
| `coverart.c:269` | `Unable to get cover image info: %s!` |
| `coverart.c:299` | `Error demuxing cover image: %s!` |
| `coverart.c:360` | `Release ID unavailable, cannot search Cover Art DB!` |
| `cue_writer.c:39` | `Couldn't open path \"%s\" for writing: %s!Invalid folder name? Try -D <folder>.` |
| `cyanrip_encode.c:361` | `Error creating filter source: %s!` |
| `cyanrip_encode.c:372` | `Error creating filter sink: %s!` |
| `cyanrip_encode.c:386` | `Error setting filter sample format: %s!` |
| `cyanrip_encode.c:394` | `Error setting filter channel layout: %s!` |
| `cyanrip_encode.c:403` | `Error setting filter sample rate: %s!` |
| `cyanrip_encode.c:437` | `Error initializing filter sink: %s!` |
| `cyanrip_encode.c:471` | `Error parsing filter graph: %s!` |
| `cyanrip_encode.c:477` | `Error configuring filter graph: %s!` |
| `cyanrip_encode.c:536` | `Error pushing frame to FIFO: %s!` |
| `cyanrip_encode.c:555` | `Error filtering frame: %s!` |
| `cyanrip_encode.c:633` | `Error allocating frame!` |
| `cyanrip_encode.c:645` | `Error allocating frame: %s!` |
| `cyanrip_encode.c:757` | `Album Loudness` |
| `cyanrip_encode.c:776` | `Could not alloc swr context!` |
| `cyanrip_encode.c:794` | `Could not init swr context!` |
| `cyanrip_encode.c:969` | `Error while encoding: %s!` |
| `cyanrip_encode.c:991` | `Error encoding: %s!` |
| `cyanrip_encode.c:1022` | `Error pushing packet to FIFO: %s!` |
| `cyanrip_encode.c:1029` | `Error writing packet: %s!` |
| `cyanrip_encode.c:1059` | `Error writing to file: %s!` |
| `cyanrip_encode.c:1182` | `Codec not found (not compiled in lavc?)!` |
| `cyanrip_encode.c:1191` | `Unable to init output avctx!` |
| `cyanrip_encode.c:1202` | `Could not open output codec context!` |
| `cyanrip_encode.c:1209` | `Couldn't copy codec params!` |
| `cyanrip_encode.c:1216` | `Couldn't open %s: %s! Invalid folder name? Try -D <folder>.` |
| `cyanrip_log.c:50` | `%s%s:` |
| `cyanrip_log.c:53` | `%s` |
| `cyanrip_log.c:63` | `CD-TEXT:        none reported by libcdio (absent, or unreadable by this driver)` |
| `cyanrip_log.c:68` | `CD-TEXT:        present (%s, %i disc %s, %i of %i tracks tagged)` |
| `cyanrip_log.c:89` | `Cache model:    not in use (paranoia disabled)` |
| `cyanrip_log.c:100` | `Cache model:    %i sector%s (disc image, no drive cache)` |
| `cyanrip_log.c:105` | `Cache model:    %i sector%s (drive cache size not probed)` |
| `cyanrip_log.c:124` | `%s%s` |
| `cyanrip_log.c:128` | `%lu` |
| `cyanrip_log.c:168` | `Pregap LSN:  %i (duration: %s)` |
| `cyanrip_log.c:170` | `Pregap length: %i frames` |
| `cyanrip_log.c:172` | `Pregap LSN:  unknown (sub-channel unreadable)` |
| `cyanrip_log.c:174` | `Pregap LSN:  unknown (sub-channel CRC mismatches)` |
| `cyanrip_log.c:176` | `Pregap LSN:  none` |
| `cyanrip_log.c:182` | `Pregap source: sub-channel (not signalled by TOC)` |
| `cyanrip_log.c:184` | `Pregap source: lead-in` |
| `cyanrip_log.c:186` | `Pregap source: TOC` |
| `cyanrip_log.c:189` | `Prepended:   %i frames of silence` |
| `cyanrip_log.c:190` | `Start LSN:   %i` |
| `cyanrip_log.c:192` | `(with offset: %i)` |
| `cyanrip_log.c:196` | `End LSN:     %i` |
| `cyanrip_log.c:203` | `Appended:    %i frames of silence` |
| `cyanrip_log.c:211` | `Preemphasis:` |
| `cyanrip_log.c:213` | `none detected` |
| `cyanrip_log.c:216` | `(deemphasis forced)` |
| `cyanrip_log.c:221` | `present (subcode)` |
| `cyanrip_log.c:223` | `present (TOC)` |
| `cyanrip_log.c:226` | `(deemphasis applied)` |
| `cyanrip_log.c:231` | `Properties:` |
| `cyanrip_log.c:234` | `Data bytes:  %i (%.2f Mib)` |
| `cyanrip_log.c:237` | `Frames:      %u` |
| `cyanrip_log.c:243` | `Duration:    %s` |
| `cyanrip_log.c:244` | `Samples:     %u` |
| `cyanrip_log.c:252` | `Sample peak level: %.1f%% (%.1f dBFS)` |
| `cyanrip_log.c:255` | `True peak level:   %.1f dBFS` |
| `cyanrip_log.c:272` | `Integrated loudness (R128): %.1f LUFS` |
| `cyanrip_log.c:274` | `Loudness range (R128):      %.1f LU (%.1f to %.1f LUFS)` |
| `cyanrip_log.c:278` | `Extraction speed:  %.1fx` |
| `cyanrip_log.c:280` | `Elapsed:            %.2f s` |
| `cyanrip_log.c:288` | `EAC CRC32:     %08X` |
| `cyanrip_log.c:290` | `(after %i rips)` |
| `cyanrip_log.c:297` | `Secure re-read:  converged after %i reads` |
| `cyanrip_log.c:300` | `Secure re-read:  did NOT converge after %i reads (repeat limit hit)` |
| `cyanrip_log.c:305` | `Secure re-read:  not attempted` |
| `cyanrip_log.c:309` | `Accurip:       %s` |
| `cyanrip_log.c:313` | `(max confidence: %i)` |
| `cyanrip_log.c:321` | `Accurip v1:  %08X` |
| `cyanrip_log.c:323` | `(accurately ripped, confidence %i)` |
| `cyanrip_log.c:325` | `(not found, either a new pressing, or bad rip)` |
| `cyanrip_log.c:329` | `Accurip v2:  %08X` |
| `cyanrip_log.c:340` | `Accurip 450: %08X` |
| `cyanrip_log.c:342` | `(match found, confidence %i, but a checksum of 0 is meaningless)` |
| `cyanrip_log.c:345` | `(matches Accurip DB, confidence %i, track is partially accurately ripped)` |
| `cyanrip_log.c:348` | `(not found)` |
| `cyanrip_log.c:355` | `Metadata:` |
| `cyanrip_log.c:365` | `%s:` |
| `cyanrip_log.c:377` | `CD-TEXT:` |
| `cyanrip_log.c:387` | `Paranoia status counts:` |
| `cyanrip_log.c:389` | `none` |
| `cyanrip_log.c:412` | `Embedded cover art:    %s: %s` |
| `cyanrip_log.c:415` | `Embedded cover art:    %s: %ix%i %s` |
| `cyanrip_log.c:419` | `File(s):` |
| `cyanrip_log.c:433` | `cyanrip %s (%s-g%s)` |
| `cyanrip_log.c:436` | `Invoked as:     %s` |
| `cyanrip_log.c:440` | `Drive used:     error retrieving drive info` |
| `cyanrip_log.c:442` | `Drive used:     %s %s (revision %s)` |
| `cyanrip_log.c:443` | `System device:  %s` |
| `cyanrip_log.c:445` | `Device model:   %s` |
| `cyanrip_log.c:446` | `Offset:         %c%i %s` |
| `cyanrip_log.c:448` | `%s%c%i %s` |
| `cyanrip_log.c:457` | `Speed:          %ix` |
| `cyanrip_log.c:459` | `Speed:          default (%s)` |
| `cyanrip_log.c:461` | `C2 errors:      %s` |
| `cyanrip_log.c:470` | `Encoder:        libavformat %i.%i.%i, libavcodec %i.%i.%i (%s)` |
| `cyanrip_log.c:475` | `Paranoia level: %s` |
| `cyanrip_log.c:479` | `Paranoia level: %i` |
| `cyanrip_log.c:480` | `Frame retries:  %i` |
| `cyanrip_log.c:482` | `HDCD decoding:  %s` |
| `cyanrip_log.c:484` | `Album Art:      %s` |
| `cyanrip_log.c:488` | `%s%s%s%s%s` |
| `cyanrip_log.c:496` | `Outputs:` |
| `cyanrip_log.c:502` | `Disc tracks:    %i` |
| `cyanrip_log.c:503` | `Tracks to rip:  %s` |
| `cyanrip_log.c:506` | `%i%s` |
| `cyanrip_log.c:520` | `AccurateRip:    %s` |
| `cyanrip_log.c:526` | `Total time:     %s` |
| `cyanrip_log.c:552` | `Tracks ripped accurately: %i/%i` |
| `cyanrip_log.c:554` | `Tracks ripped partially accurately: %i/%i` |
| `cyanrip_log.c:564` | `Ripping errors: %i` |
| `cyanrip_log.c:571` | `Rip completed:  no (interrupted by user, %i of %i tracks)` |
| `cyanrip_log.c:574` | `Rip completed:  yes (%i of %i tracks)` |
| `cyanrip_log.c:577` | `Ripping finished at %s` |
| `cyanrip_main.c:184` | `No device specified and unable to get default device!` |
| `cyanrip_main.c:192` | `Unable to open device: %s` |
| `cyanrip_main.c:201` | `Unable to init cddap context!` |
| `cyanrip_main.c:203` | `cdio: \"%s\"` |
| `cyanrip_main.c:214` | `Opening drive...` |
| `cyanrip_main.c:217` | `Unable to open device!` |
| `cyanrip_main.c:226` | `Device does not support changing speeds!` |
| `cyanrip_main.c:234` | `cdio error: %s` |
| `cyanrip_main.c:243` | `Unable to init paranoia!` |
| `cyanrip_main.c:288` | `Invalid number of tracks: %i!` |
| `cyanrip_main.c:311` | `CDIO returned invalid track %i end LSN` |
| `cyanrip_main.c:518` | `Frame read failed!` |
| `cyanrip_main.c:595` | `Loading data for track %i...` |
| `cyanrip_main.c:602` | `Stopping, offset finding incomplete!` |
| `cyanrip_main.c:610` | `Data loaded, searching for offsets...` |
| `cyanrip_main.c:619` | `Nothing found for track %i%s` |
| `cyanrip_main.c:624` | `Offset of %c%i found in track %i%s` |
| `cyanrip_main.c:629` | `Offset of %c%i confirmed (confidence: %i) in track %i%s` |
| `cyanrip_main.c:633` | `New offset of %c%i found at track %i, scrapping old offset of %c%i%s` |
| `cyanrip_main.c:647` | `No track had AccuRip entry, cannot find offset!` |
| `cyanrip_main.c:649` | `No track was long enough, unable to find drive offset!` |
| `cyanrip_main.c:651` | `Was not able to find drive offset with a radius of %i frames, trying again with a larger radius...` |
| `cyanrip_main.c:657` | `Drive offset of %c%i found (confidence: %i)!` |
| `cyanrip_main.c:687` | `Unable to read track %i subchannel info!` |
| `cyanrip_main.c:703` | `Track %i is data:` |
| `cyanrip_main.c:760` | `Error in decoding/sending frame: %s` |
| `cyanrip_main.c:772` | `Drive media changed, stopping!` |
| `cyanrip_main.c:803` | `Stopping, ripping incomplete!` |
| `cyanrip_main.c:921` | `Done; (%i out of %i matches for current checksum %08X)` |
| `cyanrip_main.c:927` | `Done; (no matches found, but hit repeat limit of %i)` |
| `cyanrip_main.c:943` | `Repeating ripping (%i out of %i matches for current checksum %08X)` |
| `cyanrip_main.c:958` | `Error in encoding: %s` |
| `cyanrip_main.c:974` | `Error sending flush signal to encoders: %s` |
| `cyanrip_main.c:981` | `Track %i ripped and encoded with errors.` |
| `cyanrip_main.c:983` | `Track %i ripped and encoded successfully!` |
| `cyanrip_main.c:1065` | `Gaps:` |
| `cyanrip_main.c:1070` | `%i frame gap between lead-in and track 1 pregap, merging into pregap` |
| `cyanrip_main.c:1077` | `%i frame unmarked gap between lead-in and track 1, marking as a pregap` |
| `cyanrip_main.c:1099` | `%i frame pregap in track %i,` |
| `cyanrip_main.c:1106` | `unmerged` |
| `cyanrip_main.c:1108` | `merging into track %i` |
| `cyanrip_main.c:1114` | `dropping` |
| `cyanrip_main.c:1120` | `merging` |
| `cyanrip_main.c:1127` | `splitting off into a new track, number %i` |
| `cyanrip_main.c:1168` | `%i frame discontinuity between tracks %i and %i,` |
| `cyanrip_main.c:1173` | `padding track %i` |
| `cyanrip_main.c:1176` | `ignoring` |
| `cyanrip_main.c:1184` | `%i frame gap between last track and lead-out, padding track` |
| `cyanrip_main.c:1249` | `Can't init signal handler!` |
| `cyanrip_main.c:1473` | `Invalid paranoia level %i must be between 0 and %i!` |
| `cyanrip_main.c:1486` | `Invalid max coverart size %i (must be 250, 500, 1200 or -1)` |
| `cyanrip_main.c:1498` | `Invalid sanitation method %s` |
| `cyanrip_main.c:1510` | `Invalid release index %i!` |
| `cyanrip_main.c:1519` | `Invalid discnumber %i` |
| `cyanrip_main.c:1526` | `Invalid totaldiscs %i` |
| `cyanrip_main.c:1530` | `discnumber %i is larger than totaldiscs %i` |
| `cyanrip_main.c:1543` | `Supported output codecs:` |
| `cyanrip_main.c:1551` | `Invalid format \"%s\"` |
| `cyanrip_main.c:1556` | `Duplicated format \"%s\"` |
| `cyanrip_main.c:1571` | `Duplicated rip idx %i` |
| `cyanrip_main.c:1585` | `Invalid track idx for pregap: %i` |
| `cyanrip_main.c:1591` | `Missing pregap action` |
| `cyanrip_main.c:1599` | `Invalid pregap action %s` |
| `cyanrip_main.c:1630` | `No cover art location specified for \"%s\"` |
| `cyanrip_main.c:1639` | `Invalid track idx for cover art: %i` |
| `cyanrip_main.c:1645` | `Cover art already specified for track idx %i!` |
| `cyanrip_main.c:1657` | `Cover art \"%s\" already specified!` |
| `cyanrip_main.c:1663` | `Too many cover arts specified!` |
| `cyanrip_main.c:1673` | `Directory name scheme must contain {format} with multiple output formats!` |
| `cyanrip_main.c:1678` | `-J (only generate a CUE sheet) cannot be used with -I (only print info)!` |
| `cyanrip_main.c:1694` | `Searching for drive offset, enabling AccuRip and disabling MusicBrainz and Cover art fetching...` |
| `cyanrip_main.c:1702` | `Offset is unset! To continue with an offset of 0, run with -s 0!` |
| `cyanrip_main.c:1782` | `MusicBrainz URL:%s` |
| `cyanrip_main.c:1826` | `Error reading album tags: %s` |
| `cyanrip_main.c:1856` | `Log(s) will be written to:` |
| `cyanrip_main.c:1864` | `CUE files will be written to:` |
| `cyanrip_main.c:1896` | `Invalid track number %i, list has %i tracks!` |
| `cyanrip_main.c:1912` | `Error reading track tags: %s` |
| `cyanrip_main.c:1966` | `Cover art destination(s):` |
| `cyanrip_main.c:2001` | `WARNING: tracks %i and %i resolve to the same file \"%s\", one will overwrite the other!` |
| `cyanrip_main.c:2012` | `Tracks:` |
| `cyanrip_main.c:2022` | `Track %i info:` |
| `cyanrip_main.c:2040` | `Error initializing decoder: %s` |
| `cyanrip_main.c:2049` | `Error initializing encoder: %s` |
| `cyanrip_main.c:2083` | `Error encoding: %s` |
| `cyanrip_main.c:2103` | `Invalid rip index %i, list has %i tracks!` |
| `cyanrip_main.c:2185` | `Error ripping: %s` |
| `discid.c:31` | `Unable to init SHA for DiscID: %s!` |
| `musicbrainz.c:116` | `Invalid disc number %i, release only has %i CDs` |
| `musicbrainz.c:121` | `Got empty medium list.` |
| `musicbrainz.c:127` | `No mediums match DiscID!` |
| `musicbrainz.c:155` | `Medium has no track list.` |
| `musicbrainz.c:193` | `Could not connect to MusicBrainz.` |
| `musicbrainz.c:201` | `Missing DiscID!` |
| `musicbrainz.c:212` | `MusicBrainz query failed: %s` |
| `musicbrainz.c:219` | `Connection failed, try again? Or disable via -N` |
| `musicbrainz.c:224` | `Error fetching/requesting/auth, this shouldn't happen.` |
| `musicbrainz.c:247` | `MusicBrainz lookup failed: DiscID has no associated releases.` |
| `musicbrainz.c:255` | `MusicBrainz lookup failed: no releases found for DiscID.` |
| `musicbrainz.c:259` | `Multiple releases found in database for DiscID %s:` |
| `musicbrainz.c:280` | `%i (ID: %s): %s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s` |
| `musicbrainz.c:294` | `Please specify which release to use by adding the -R argument with an index or ID.` |
| `musicbrainz.c:299` | `Invalid release index %i specified, only have %i releases!` |
| `musicbrainz.c:317` | `Release ID %s not found in release list for DiscID %s!` |
| `musicbrainz.c:348` | `Found MusicBrainz release: %s - %s` |
| `musicbrainz.c:362` | `MusicBrainz lookup failed, but DiscID has a matching stub, consider verifying the data and creating a release here:` |
| `musicbrainz.c:366` | `Unable to find release info for this CD, and metadata hasn't been manually added!` |
| `musicbrainz.c:370` | `Unable to find metadata for this CD, but metadata has been manually specified, continuing.` |
| `musicbrainz.c:376` | `Please help improve the MusicBrainz DB by submitting the disc info via the following URL:` |
| `musicbrainz.c:382` | `To continue add metadata via -a or -t, or ignore via -N!` |
| `naming.c:123` | `Error parsing string: %s!` |
| `naming.c:215` | `Invalid scheme syntax, unterminated \"{\"!` |
| `naming.c:229` | `Invalid scheme syntax, no \"#\"!` |
| `naming.c:243` | `Invalid scheme syntax, no terminating \"#\"!` |
| `naming.c:259` | `Invalid condition syntax!` |

**253 distinct stable lines.**

Field order within a block is fixed and is part of the contract. The golden
reference log in the handshake package is the authoritative example.

### P2a - Composed lines

Lines assembled into a buffer by a run of `snprintf()` and emitted through a
bare `"%s"`. The emitting call site shows a consumer nothing, so the pieces
are reconstructed here from the `snprintf` formats that build the buffer, in
source order. Segments after the first are conditional.

**`cyanrip_main.c:887`** - reaches logfile: **no, stdout only**

| # | Segment |
|---|---|
| 0 | `Ripping%strack %i, progress - %0.2f%%` |
| 1 | `, ETA - %ih %im` |
| 2 | `, ETA - %im` |
| 3 | `, ETA - %llds` |
| 4 | `, errors - %i` |
| 5 | ` ` |

Segment 0 is always present; the rest are appended conditionally. This is
**stable API**: the progress bar and ETA of at least one consumer are
driven by it.

**`cyanrip_main.c:1934`** - reaches logfile: yes

Not derivable: the buffer is not built by `snprintf` in this function.
It emits arbitrary text - here, the generated CUE sheet echoed back to
the terminal a line at a time. **Do not pattern-match this row**; a
pattern built from its `"%s"` would match every line in the log.

## P3 - Unstable wording, and stdout-only routing

**This section answers two independent questions, and a row can be here for
either.** Conflating them is what put `cyanrip_encode.c` and two other rows in
both P3 and P5 and made the membership look contradictory (Platterpus, round 5
A2):

- **Unstable wording** - the text may be reworded without a handshake round.
  Do not depend on the exact string.
- **stdout only** - the line never reaches a logfile, whatever its wording.

**Appearing here does not mean a line is harmless.** A line can be
stdout-only *and* a failure diagnostic; those rows are also in P5, and P5 is
the authority on whether something is reachable on a failure path. Match
P5 rows for error detection even when they appear here.

| File:line | Line | Reaches logfile? |
|---|---|---|
| `cyanrip_encode.c:105` | `%s folder: [%s] extension: %s%s` | **no, stdout only** |
| `cyanrip_encode.c:125` | `Encoder for %s not compiled in ffmpeg!` | **no, stdout only** |
| `cyanrip_main.c:479` | `Still reading track %i at LSN %li - %` | **no, stdout only** |
| `cyanrip_main.c:503` | `Track %i resumed after %` | **no, stdout only** |
| `cyanrip_main.c:821` | `\r` | **no, stdout only** |
| `cyanrip_main.c:887` | `%s` | **no, stdout only** |
| `cyanrip_main.c:968` | `Flushing encoders...` | **no, stdout only** |
| `cyanrip_main.c:1010` | `Force quitting` | **no, stdout only** |
| `cyanrip_main.c:1013` | `\rTrying to quit` | **no, stdout only** |
| `cyanrip_main.c:1409` | `Log \"%s\" checksum valid.` | **no, stdout only** |
| `cyanrip_main.c:1412` | `Log \"%s\" checksum mismatch, the file has been modified!` | **no, stdout only** |
| `cyanrip_main.c:1416` | `Log \"%s\" has data after the checksum, the file has been modified!` | **no, stdout only** |
| `cyanrip_main.c:1420` | `No FUN512 checksum found in \"%s\"!` | **no, stdout only** |
| `cyanrip_main.c:1424` | `Couldn't read \"%s\"!` | **no, stdout only** |

Also unstable, and **not ours**: the loudness block FFmpeg's `ebur128` filter
prints (`Integrated loudness`, `Loudness range`, `Sample peak:`, `True peak:`, ...). That wording
belongs to libavfilter and moves when FFmpeg does. Prefer the
`Sample peak level:` and `True peak level:` lines in P2, which are ours,
are gated on a completed rip, and each say which peak they report.

## P4 - Exit codes

| Code | Meaning |
|---|---|
| `0` | Success: completed rip, `-I`, `-J`, `-h`, `-v`, or a `-Y` that validated |
| `1` | Every failure, without exception |

Distinct exit values found in the tree: `0`, `1`.

**There is no per-failure-class code.** Classification must come from the text,
which is why P5 exists. No non-zero exit is silent: argument parse failures
print before returning, and every other `return 1` in `main()` is preceded by a
`cyanrip_log()` call.

Argument validation runs **before the logfile is opened**, so that whole class of
diagnosis is **stdout only**. A consumer that reads only the logfile cannot see it.

## P5 - Fatal and error message inventory

Every string reachable on a failure path. Use this to derive error matching
rather than guessing prefixes.

**Evidence** says why each string is here, and is reported rather than folded
into a bare verdict so you can see which entries rest on the weaker test:

- `control flow` - the call is followed by `return 1`, a non-zero `exit()`,
  `return AVERROR(...)`, `total_error_count++`, or `goto fail`. Does not
  depend on how the message is worded.
- `wording` - the message begins like a diagnostic, but no failure exit was
  found near it. Either the exit is further away than the search window, or
  the message is a warning that does not end the run. **Treat these as
  possibly non-fatal.**
- `both` - the two agree.
- `goto end` / `wording + goto end` - the call is followed by `goto end`,
  which in `cyanrip_main.c` is *both* the ordinary success cleanup and the
  route several genuine aborts take (`Offset is unset!` leaves that way).
  It is reported as its own class because calling it fatal would file
  success lines as failures, and calling it non-fatal would drop real
  aborts. **Neither of us can settle these from the source alone; they need
  a run to classify.**

The search stops at the next `if`/`for`/`while`/`switch`, so a message is
only credited with an exit that is its own -- without that cut,
`Opening drive...` reads as fatal because the *next* statement's if-block
returns `AVERROR`. It deliberately does *not* stop at the next log call:
two arms of one if/else that both log and then converge on a single exit
must carry the same class.

| File:line | Message | Evidence | Reaches logfile? |
|---|---|---|---|
| `accurip.c:97` | `Unable to get AccuRIP DB data: missing CDDB ID!` | wording + goto end | yes |
| `accurip.c:129` | `Unable to get AccuRIP DB data: missing entry!` | wording + goto end | yes |
| `accurip.c:137` | `Unable to get AccuRIP DB data: %s%s` | wording + goto end | yes |
| `accurip.c:140` | `Unable to get AccuRIP DB data: %s!` | wording + goto end | yes |
| `accurip.c:176` | `AccuRIP DB data error, got unexpected number of bytes!` | goto end | yes |
| `coverart.c:51` | `Unable to init lavf context: %s!` | both | yes |
| `coverart.c:57` | `Unable to alloc stream!` | both | yes |
| `coverart.c:70` | `Couldn't open %s for writing: %s!` | both | yes |
| `coverart.c:82` | `Couldn't write header: %s!` | both | yes |
| `coverart.c:92` | `Error writing picture packet: %s!` | both | yes |
| `coverart.c:97` | `Error writing trailer: %s!` | both | yes |
| `coverart.c:177` | `Unable to get cover art \"%s\": not found!` | wording + goto end | yes |
| `coverart.c:186` | `Unable to get cover art \"%s\": %s%s!` | wording + goto end | yes |
| `coverart.c:189` | `Unable to get cover art \"%s\": %s!` | wording + goto end | yes |
| `coverart.c:262` | `Unable to open \"%s\": %s!` | wording + goto end | yes |
| `coverart.c:269` | `Unable to get cover image info: %s!` | wording + goto end | yes |
| `coverart.c:299` | `Error demuxing cover image: %s!` | wording + goto end | yes |
| `cue_writer.c:39` | `Couldn't open path \"%s\" for writing: %s!Invalid folder name? Try -D <folder>.` | both | yes |
| `cyanrip_encode.c:125` | `Encoder for %s not compiled in ffmpeg!` | control flow | **no, stdout only** |
| `cyanrip_encode.c:361` | `Error creating filter source: %s!` | both | yes |
| `cyanrip_encode.c:372` | `Error creating filter sink: %s!` | both | yes |
| `cyanrip_encode.c:386` | `Error setting filter sample format: %s!` | both | yes |
| `cyanrip_encode.c:394` | `Error setting filter channel layout: %s!` | both | yes |
| `cyanrip_encode.c:403` | `Error setting filter sample rate: %s!` | both | yes |
| `cyanrip_encode.c:437` | `Error initializing filter sink: %s!` | both | yes |
| `cyanrip_encode.c:471` | `Error parsing filter graph: %s!` | both | yes |
| `cyanrip_encode.c:477` | `Error configuring filter graph: %s!` | both | yes |
| `cyanrip_encode.c:536` | `Error pushing frame to FIFO: %s!` | wording | yes |
| `cyanrip_encode.c:555` | `Error filtering frame: %s!` | both | yes |
| `cyanrip_encode.c:633` | `Error allocating frame!` | both | yes |
| `cyanrip_encode.c:645` | `Error allocating frame: %s!` | both | yes |
| `cyanrip_encode.c:776` | `Could not alloc swr context!` | wording | yes |
| `cyanrip_encode.c:794` | `Could not init swr context!` | wording | yes |
| `cyanrip_encode.c:969` | `Error while encoding: %s!` | both | yes |
| `cyanrip_encode.c:991` | `Error encoding: %s!` | both | yes |
| `cyanrip_encode.c:1022` | `Error pushing packet to FIFO: %s!` | both | yes |
| `cyanrip_encode.c:1029` | `Error writing packet: %s!` | both | yes |
| `cyanrip_encode.c:1059` | `Error writing to file: %s!` | both | yes |
| `cyanrip_encode.c:1182` | `Codec not found (not compiled in lavc?)!` | control flow | yes |
| `cyanrip_encode.c:1191` | `Unable to init output avctx!` | both | yes |
| `cyanrip_encode.c:1202` | `Could not open output codec context!` | both | yes |
| `cyanrip_encode.c:1209` | `Couldn't copy codec params!` | both | yes |
| `cyanrip_encode.c:1216` | `Couldn't open %s: %s! Invalid folder name? Try -D <folder>.` | both | yes |
| `cyanrip_main.c:184` | `No device specified and unable to get default device!` | both | yes |
| `cyanrip_main.c:192` | `Unable to open device: %s` | both | yes |
| `cyanrip_main.c:201` | `Unable to init cddap context!` | wording | yes |
| `cyanrip_main.c:203` | `cdio: \"%s\"` | control flow | yes |
| `cyanrip_main.c:217` | `Unable to open device!` | both | yes |
| `cyanrip_main.c:226` | `Device does not support changing speeds!` | control flow | yes |
| `cyanrip_main.c:243` | `Unable to init paranoia!` | both | yes |
| `cyanrip_main.c:288` | `Invalid number of tracks: %i!` | both | yes |
| `cyanrip_main.c:311` | `CDIO returned invalid track %i end LSN` | control flow | yes |
| `cyanrip_main.c:511` | `cdio error: %s` | control flow | yes |
| `cyanrip_main.c:518` | `Frame read failed!` | control flow | yes |
| `cyanrip_main.c:602` | `Stopping, offset finding incomplete!` | wording + goto end | yes |
| `cyanrip_main.c:687` | `Unable to read track %i subchannel info!` | wording | yes |
| `cyanrip_main.c:760` | `Error in decoding/sending frame: %s` | both | yes |
| `cyanrip_main.c:772` | `Drive media changed, stopping!` | both | yes |
| `cyanrip_main.c:803` | `Stopping, ripping incomplete!` | wording | yes |
| `cyanrip_main.c:921` | `Done; (%i out of %i matches for current checksum %08X)` | goto finalize_ripping | yes |
| `cyanrip_main.c:927` | `Done; (no matches found, but hit repeat limit of %i)` | goto finalize_ripping | yes |
| `cyanrip_main.c:958` | `Error in encoding: %s` | wording + goto end | yes |
| `cyanrip_main.c:974` | `Error sending flush signal to encoders: %s` | wording | yes |
| `cyanrip_main.c:1010` | `Force quitting` | control flow | **no, stdout only** |
| `cyanrip_main.c:1420` | `No FUN512 checksum found in \"%s\"!` | control flow | **no, stdout only** |
| `cyanrip_main.c:1424` | `Couldn't read \"%s\"!` | both | **no, stdout only** |
| `cyanrip_main.c:1473` | `Invalid paranoia level %i must be between 0 and %i!` | both | yes |
| `cyanrip_main.c:1486` | `Invalid max coverart size %i (must be 250, 500, 1200 or -1)` | both | yes |
| `cyanrip_main.c:1498` | `Invalid sanitation method %s` | both | yes |
| `cyanrip_main.c:1510` | `Invalid release index %i!` | both | yes |
| `cyanrip_main.c:1519` | `Invalid discnumber %i` | both | yes |
| `cyanrip_main.c:1526` | `Invalid totaldiscs %i` | both | yes |
| `cyanrip_main.c:1530` | `discnumber %i is larger than totaldiscs %i` | control flow | yes |
| `cyanrip_main.c:1551` | `Invalid format \"%s\"` | both | yes |
| `cyanrip_main.c:1556` | `Duplicated format \"%s\"` | control flow | yes |
| `cyanrip_main.c:1571` | `Duplicated rip idx %i` | control flow | yes |
| `cyanrip_main.c:1585` | `Invalid track idx for pregap: %i` | both | yes |
| `cyanrip_main.c:1591` | `Missing pregap action` | both | yes |
| `cyanrip_main.c:1599` | `Invalid pregap action %s` | both | yes |
| `cyanrip_main.c:1630` | `No cover art location specified for \"%s\"` | both | yes |
| `cyanrip_main.c:1639` | `Invalid track idx for cover art: %i` | both | yes |
| `cyanrip_main.c:1645` | `Cover art already specified for track idx %i!` | control flow | yes |
| `cyanrip_main.c:1657` | `Cover art \"%s\" already specified!` | control flow | yes |
| `cyanrip_main.c:1663` | `Too many cover arts specified!` | control flow | yes |
| `cyanrip_main.c:1673` | `Directory name scheme must contain {format} with multiple output formats!` | control flow | yes |
| `cyanrip_main.c:1678` | `-J (only generate a CUE sheet) cannot be used with -I (only print info)!` | both | yes |
| `cyanrip_main.c:1702` | `Offset is unset! To continue with an offset of 0, run with -s 0!` | goto end | yes |
| `cyanrip_main.c:1826` | `Error reading album tags: %s` | both | yes |
| `cyanrip_main.c:1896` | `Invalid track number %i, list has %i tracks!` | both | yes |
| `cyanrip_main.c:1912` | `Error reading track tags: %s` | both | yes |
| `cyanrip_main.c:1934` | `%s` | goto end | yes |
| `cyanrip_main.c:2040` | `Error initializing decoder: %s` | both | yes |
| `cyanrip_main.c:2049` | `Error initializing encoder: %s` | both | yes |
| `cyanrip_main.c:2083` | `Error encoding: %s` | wording + goto end | yes |
| `cyanrip_main.c:2103` | `Invalid rip index %i, list has %i tracks!` | both | yes |
| `cyanrip_main.c:2185` | `Error ripping: %s` | wording + goto end | yes |
| `discid.c:31` | `Unable to init SHA for DiscID: %s!` | wording | yes |
| `musicbrainz.c:116` | `Invalid disc number %i, release only has %i CDs` | both | yes |
| `musicbrainz.c:121` | `Got empty medium list.` | control flow | yes |
| `musicbrainz.c:193` | `Could not connect to MusicBrainz.` | both | yes |
| `musicbrainz.c:201` | `Missing DiscID!` | wording | yes |
| `musicbrainz.c:224` | `Error fetching/requesting/auth, this shouldn't happen.` | both | yes |
| `musicbrainz.c:247` | `MusicBrainz lookup failed: DiscID has no associated releases.` | goto end_meta | yes |
| `musicbrainz.c:255` | `MusicBrainz lookup failed: no releases found for DiscID.` | goto end_meta | yes |
| `musicbrainz.c:294` | `Please specify which release to use by adding the -R argument with an index or ID.` | control flow | yes |
| `musicbrainz.c:299` | `Invalid release index %i specified, only have %i releases!` | both | yes |
| `musicbrainz.c:317` | `Release ID %s not found in release list for DiscID %s!` | control flow | yes |
| `musicbrainz.c:362` | `MusicBrainz lookup failed, but DiscID has a matching stub, consider verifying the data and creating a release here:` | control flow | yes |
| `musicbrainz.c:366` | `Unable to find release info for this CD, and metadata hasn't been manually added!` | both | yes |
| `musicbrainz.c:370` | `Unable to find metadata for this CD, but metadata has been manually specified, continuing.` | wording | yes |
| `naming.c:123` | `Error parsing string: %s!` | wording | yes |
| `naming.c:215` | `Invalid scheme syntax, unterminated \"{\"!` | both | yes |
| `naming.c:229` | `Invalid scheme syntax, no \"#\"!` | both | yes |
| `naming.c:243` | `Invalid scheme syntax, no terminating \"#\"!` | both | yes |
| `naming.c:259` | `Invalid condition syntax!` | both | yes |

**115 distinct strings.** By evidence: 63 both, 20 control flow, 11 wording, 3 goto end, 14 wording + goto end.

The `control flow` and `both` rows total 83 strings proven reachable on a
failure path without reference to their wording. That subset is the one to
build a hard failure classifier on.

