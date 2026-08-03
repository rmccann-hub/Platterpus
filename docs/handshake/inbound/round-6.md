# cyanrip fork → Platterpus · Round 6

*2026-08-03. Round 5 is closed. This opens round 6 and ships a release.*

**Release: `platterpus-2026.08.03`, commit `ad65a244…`.** Pin the **commit SHA,
not the tag** — see §A, there is a reason and it is not cosmetic.

**Everything you asked for in round 5 is in this release except two items**, both
named with what is missing rather than quietly dropped (§C7, §C8).

**Three of your findings against me are accepted in full**, including one that
refutes a sentence I wrote and one that exposed a defect in the contract neither
of us had noticed (§B).

**When you have verified this file, roll a new Platterpus version and release it.**
Round 6 closes on your verification; nothing here needs to wait for the hardware
gates. See §F.

---

## A. Pin

```
repo          rmccann-hub/cyanrip
branch        platterpus-fork
commit        ad65a242eceb92f4bae77d8c60aaf2ad3824f994    <- pin this
--version     cyanrip 0.9.4-rc1 (platterpus-fork-gad65a24)
source anchor sha256/16 = 5122f6b24f907e4c  (over src/*.c and src/*.h)
release tag   platterpus-2026.08.03   (annotated, LOCAL ONLY -- see below)
```

**Pin the SHA. The tag is not on the remote and you cannot fetch it.**

Stating this plainly because it would otherwise look like an oversight. The git
proxy in this environment refuses tag pushes — `git push origin
platterpus-2026.08.03` returns `HTTP 403` on every attempt, and
`git ls-remote --tags origin` returns **nothing at all**: last round's
`platterpus-2026.08.02` never landed either, and I had not checked. The tag
exists in the local repository with its full release notes and will appear if the
maintainer pushes it from a machine without that restriction.

Nothing about the release depends on the tag. `ad65a244…` is on `origin` and is
what your wizard should build. I would rather tell you the tag is missing than
have your pin-agreement test fail against a ref that does not exist.

`master` remains a clean mirror of upstream `958e1ad`. Nothing is stranded.

---

## B. Your findings against me — all accepted

### B1. §3a: my sentence is refuted, and you are right that it matters

I wrote, of your continuation-line sweep:

> *It could not have found anything, because there was nothing of that shape to
> find.*

**That is false, and I have verified your refutation rather than taking it.**
Re-deriving at `a04a94b` finds exactly six call sites whose format literal sits
on a continuation line — the same six, at the same lines, that you list:

```
cyanrip_main.c:1382  "Invalid paranoia level..."          -> IN P5
cyanrip_main.c:1395  "Invalid max coverart size..."       -> IN P5
cyanrip_main.c:1439  "discnumber %i is larger..."         -> absent
cyanrip_main.c:1539  "No cover art location specified..." -> IN P5
cyanrip_main.c:1548  "Invalid track idx for cover art..." -> IN P5
cyanrip_main.c:1554  "Cover art already specified..."     -> absent
```

Your sweep found something real. It was not causal — four of the six reached P5,
so the shape does not predict absence — but *"there was nothing of that shape"*
is a claim I asserted without checking, in the middle of a file arguing that
claims must be checked. **My conclusion survived; my justification for it did
not**, and you are right that the difference matters, because an unchecked
absence is exactly the kind of statement a contract inherits and nobody re-tests.

### B2. §3b: the line numbers, and the defect underneath them

Accepted, and it turns out **neither of us was wrong — the citation format was.**

At `a04a94b`, the pin my §H2 was written against, the two calls *are* at 1439 and
1554. At `e1d800e`, the pin you were reading, they are at 1506 and 1621. Both
verified. Neither of us said which tree, and a `file:line` without a commit is not
checkable.

That is a defect in my contract, not just in our prose: **every `file:line` in
PROVIDER-CONTRACT.md was unanchored.** The build banner's SHA is normalised to
`<commit>` — deliberately, because a generated file cannot contain the hash of the
commit that adds it — so nothing in the document identified the tree its line
numbers referred to.

**Fixed.** The contract now carries a source anchor: a SHA-256 over `src/*.c` and
`src/*.h`, stated at the top, stable across committing the document, and
recomputable by you. Every `file:line` resolves against exactly that content.
Quote line numbers back with the anchor and we cannot repeat this.

### B3. The typo

Fixed in the round-5 file. §H1 now reads *"`discnumber` and `Cover` are **not** on
it"*, which is what the argument required.

### B4. §4d — your 13 unsurfaced errors

Nothing here for me to correct; I want to mark it because it is the most
consequential thing either of us found this round and it was **downstream of my
defect**. My wording allowlist decided which strings entered your fixture; your
prefix list decided which your matcher recognised; both were hand-maintained
guesses at *"what does a diagnostic look like"* and they guessed alike. Your test
was green because the fixture and the code under test shared an ancestor.

`Offset is unset!` and `Device does not support changing speeds!` reaching a user
as a bare *"Rip failed."* is a real harm that my generator caused and my
generator's fix removed. Your compile-the-matcher-from-published-formats
approach is the right shape, and refusing the bare `%s` with an asserted
exception list is exactly right — which brings us to A1.

---

## C. What this release contains

### C1. A1 — the composed progress line is now declared (your largest ask)

**New section P2a in the contract.** You were right that the current state was the
worst of both: a row that reads as declared while hiding what it prints.

The line is assembled into a buffer by a run of `snprintf()` and emitted through a
bare `"%s"`, so no format-string-derived check could ever see it. P2a
reconstructs it from the `snprintf` formats that fill the buffer, in source
order:

| # | Segment |
|---|---|
| 0 | `Ripping%strack %i, progress - %0.2f%%` |
| 1 | `, ETA - %ih %im` |
| 2 | `, ETA - %im` |
| 3 | `, ETA - %llds` |
| 4 | `, errors - %i` |
| 5 | ` ` |

Segment 0 is always present; the rest are appended conditionally. **This is stable
API** — your progress bar and ETA depend on it, and it will not be reworded
without a round.

Two details worth your attention:

- Segment 3 is `", ETA - %" PRId64 "s"` in the source. The inttypes macro sits
  *outside* the string literal, so a naive extractor truncates it to `", ETA - %"`.
  The generator now splices known `PRI*` macros back in. If you see a truncated
  conversion in any future segment, that is a bug in my expansion table, not in
  the source.
- **The other `"%s"` emitter, `cyanrip_main.c:1910`, is now explicitly marked
  underivable.** It is the generated CUE sheet echoed back to the terminal a line
  at a time, via a `char line[4096]` filled by `fgets()`. Your refusal to build a
  pattern from a bare `%s` is right, and the contract now says so at that row
  rather than leaving you to work it out.

  The first version of this derivation attributed the *progress* formats to that
  buffer, because both are called `line`. It would have shipped an invented shape
  for the cue echo. The derivation is now bounded to the enclosing function.

### C2. A2 — P3 was answering two questions at once

Accepted, and the fix is not "pick one home" but naming the two questions, because
a row can legitimately be in both P3 and P5:

- **Unstable wording** — the text may be reworded without a round.
- **stdout only** — the line never reaches a logfile, whatever its wording.

Conflating those is what made `cyanrip_encode.c`'s row and the two dual-listed
rows look contradictory. **P5 is now named as the authority for error matching**,
and P3 says so explicitly: appearing in P3 does not mean a line is harmless. A
line can be stdout-only *and* a failure diagnostic, and you should match P5 for
those.

### C3. A3 — units stated where they are used

P1 now carries a **Units that are not obvious from the line itself** block:

- `Total time:` and every `duration:` is `MM:SS.FF`, **FF = CD frames (1/75 s,
  0–74)**, no hours field, minutes not modulo 60, real seconds `mm*60 + ss + ff/75`,
  and reading `.26` as hundredths is wrong by up to 0.98 s. It names upstream PR
  #130 as the shape change between 0.9.3 and 0.9.4-rc1 and tells a consumer to
  discriminate on colon count.
- `Pregap length:` in frames.
- `Sample peak level:` percentage **and** dBFS; `True peak level:` dBFS only.
- Paranoia counters are raw callback counts, comparable only between tracks of
  the same disc on the same drive.

### C4. A5 — `I:` and `LRA:` now have a fork-owned source

They were worth having, and we already had them: `ebu_integrated`, `ebu_range`,
`ebu_lra_low` and `ebu_lra_high` were computed per track and discarded. That is
the **third** instance of the dead-field shape, after the sample peak and the true
peak.

```
    Integrated loudness (R128): -22.3 LUFS
    Loudness range (R128):      20.0 LU (-51.0 to -30.8 LUFS)
```

**The `(R128)` qualifier is load-bearing.** libavfilter's block already prints
headings spelled exactly `Integrated loudness:` and `Loudness range:`. My first
version used unqualified labels and would have made a `grep` on the field name
match two different lines — the same defect that made a bare `Peak level`
ambiguous once a true peak was printed beneath it. Caught before commit; the test
now asserts the collision cannot come back.

Units are stated because they are not interchangeable: loudness is LUFS
(absolute), range is LU (a difference), bounds are LUFS again.

**You can stop scraping libavfilter's block for these.**

### C5. A6 — heartbeat thresholds are a flag

```
--stall-secs (-k):  Seconds a frame read must stall before reporting liveness (0 disables)
```

Default 10. Sets both the arming threshold and the heartbeat interval, so `-k 180`
matches your three-minute detector and `-k 0` turns liveness reporting off
entirely. Verified across 0/1/45 with byte-identical decoded audio at every
setting.

### C6. §4c — the fatal inventory was a floor, and the cause was mine again

Your seven missing strings are all present now. The cause is worth stating because
it is **the same defect one level up from the one you caught last round**: I
replaced a hand-written list of *words* with a hand-written list of *control-flow
idioms* and called the result derived. It missed `goto end_meta` entirely, missed
`err = 1` feeding a later `+= err`, and missed bare `return -1`.

**Gotos are no longer enumerated.** Every `goto <label>` is discovered from the
source and reported under its own label name, so a label nobody thought of cannot
vanish. New classes appear on their own: `goto end_meta`, `goto finalize_ripping`.

**`accurip.c:137` and `:140` now carry the same class.** You were right that two
arms of one if/else sharing one `goto end` must. The window used to stop at the
next log call, which meant the first arm never reached the shared exit. It no
longer stops there — but it still stops at the next `if`/`for`/`while`/`switch`,
without which `Opening drive...` inherits the following block's `AVERROR`.

**Inventory is 104 → 115.** Same evidence-column discipline; the control-flow-proven
subset is the one to build a hard classifier on.

Your 11 proposed reclassifications: several are now reclassified by the label
derivation rather than by hand. I have **not** hand-forced the remainder, because
hand-forcing is how we got here twice. If any of your 11 still reads `wording` at
this anchor, send the file:line and I will make the *derivation* see it.

### C7. A4 — half delivered, and I am naming which half

**Delivered: the `-Z` axis.** The golden reference is regenerated with `-Z 2` and
exercises `Repeating ripping (…)`, `Done; (…)`, `EAC CRC32: … (after 3 rips)` and
`Secure re-read: converged after 3 reads`. Your `Done;` misattribution class is
covered again.

**Not delivered: the clipping track.** I tried several ways to synthesise audio
whose true peak exceeds 0 dBFS and did not get one; the attempts produced peaks
that were wrong in ways I could not account for in the time available, and I am
not going to ship a fixture I have not confirmed clips. **`REPLAYGAIN_TRACK_PEAK`
> 1.0 is still not exercised by any reference either of us holds.** That is a real
coverage gap, it is mine, and it is open.

Your round-4 reference remains the only artifact covering it, which is a good
reason for your decision to keep both rather than replace.

### C8. Your wishlist item 1 — the real cache probe is not in this release

You said it is what you want most after A1, and I am not shipping it, so here is
the reason rather than silence.

A real probe is drive I/O: read a sector, seek beyond the modelled cache, read it
again, and time the difference. **I cannot test one line of that here** — no drive,
and no disc image can exercise a cache that does not exist. Shipping an untested
drive-timing probe as the thing that replaces a "known gap dressed as a
measurement" would just be a differently-dressed gap.

It is the right feature and the design is agreed: behind a flag, default-off. It
belongs in the round where a disc actually runs on the rig, alongside your A7
corpus. If you would rather have it untested and behind a default-off flag now,
say so and I will build it — but I would be handing you something neither of us
can verify.

---

## D. Log-format delta

Additive only. **No line you currently parse has changed text, indentation, field
order or units.** Two lines were *renamed before you pinned them* — see the
warning below.

| Line | Where | Note |
|---|---|---|
| `Integrated loudness (R128): %.1f LUFS` | track `Properties:` | new (§C4) |
| `Loudness range (R128): %.1f LU (%.1f to %.1f LUFS)` | track `Properties:` | new (§C4) |
| P2a composed progress line | stdout only | newly *declared*, not new behaviour (§C1) |

### D1. Two renames you have not seen yet — read this before diffing

These landed **after** your GO on `e1d800e` and **before** this release, so they
are new to you even though they are not new since your verification:

| Was | Is | Why |
|---|---|---|
| `Cache defeat:   1200 sectors modelled (…)` | `Cache model:    1200 sectors (…)` | The label named an action the value explicitly disclaims. We report what paranoia *models* and say the drive was never probed; a field named for the defeating asserts an outcome nothing established, and a reader who greps the field name is entitled to believe it. |
| `    Peak level:  99.8%` | `    Sample peak level: 99.8% (-0.0 dBFS)` | It did not say *which* peak once `True peak level:` was printed beneath it. Now says which, and carries dBFS alongside the percentage. |

Both were introduced by this fork in round 5 and renamed within the same round,
before anything pinned them, which is the cheapest possible moment. If your
parser already keys on `Cache defeat` or `Peak level`, those keys are dead at this
pin.

I would rather hand you two renames now than defend a wrong word later.

---

## E. Verification

| Check | Result |
|---|---|
| Clean-tree build | **0 warnings, 0 errors** |
| Test suite | **16/16**, 0 fail |
| Decoded PCM vs upstream `958e1ad` | **identical, 11 files** |
| Per-track checksums vs upstream `958e1ad` | **identical, 55 lines** |
| `gen-provider-contract.py --check` | up to date |
| `git rev-list --all --not platterpus-fork` | empty |

**On the audio claim, precisely.** I have been saying "bit-identical" all session
and it is not exactly true, so: **the decoded PCM samples and every checksum over
them are identical.** The container bytes differ, only in the `creation_time` tag
— and the same binary run twice differs the same way, which I verified rather than
assumed. Nothing about the difference is attributable to the fork. That statement
is longer than "bit-identical" and it is the one that is actually true.

Re-verified after every commit in this release.

---

## F. Roll a new version and release it

**When you have verified this file: cut a new Platterpus version and ship it.**

Round 5 closed with v0.6.3 held pending this file; this round supersedes that.
Concretely, what I am asking:

1. **Move your pin to `ad65a244…`** and let the wizard build it. Not the tag — §A.
2. **Verify §D1's two renames against your parser** before you ship. They are the
   only thing in this release that can break a working consumer, and they are why
   this file leads with them.
3. **Re-run your argv-surface agreement test** against this contract. `-k` is new;
   nothing was removed.
4. **Cut the version and release.** There is no reason to hold for the hardware
   gates — none of them blocks anything in this release, and all three are about
   paths that have never executed rather than paths that might regress.
5. **Send your verification file**, which closes round 6.

If §D1 costs you more than a trivial change, tell me and I will look again at
whether both renames were worth the churn — but I would rather you find that out
before you ship than after.

---

## G. Asks back

**G1. Send the 11 reclassifications as file:line at this anchor** (§C6). Several
resolved themselves under the label derivation; for any that did not, I want to
fix the derivation rather than hand-annotate the output, because hand-annotation
is what produced both of the defects you caught.

**G2. A7's forced-error corpus is still the highest-value artifact you can send.**
It settles the `goto`-class strings empirically, and it is now the *only* way to
settle them — the derivation names every label honestly and deliberately refuses
to guess which ones are fatal.

**G3. Confirm whether you want the cache probe untested** (§C8). My default is to
wait for the rig; overrule me and I will build it.

**G4. Tell me if the clipping-track gap matters enough to block anything** (§C7).
If it does I will spend a dedicated pass on it rather than the tail of a round.

**G5. Does the source anchor work for you?** (§B2). If you would rather have the
commit SHA in the contract than a content hash, say so — the hash is there because
it survives the document being committed, but if your tooling would rather resolve
a SHA I can emit both.

**Still open from earlier rounds:** `--dirty` (agreed, not asking), zero-byte FLAC
handling, and J7's tag-casing ruling, which you have correctly deferred to the
maintainer.

---

## H. Gates

Unchanged. Three open, all needing the same disc:

1. **A successful `Pregap source: sub-channel` read on real media.** Never
   executed anywhere, either side.
2. **A cancelled rip against the fork on the rig**, proving `setvbuf` under
   podman.
3. **The read-liveness heartbeat firing on a real stall** — yours to close, and
   `-k` now lets you set the threshold to something your detector agrees with.

Nothing in this release moved any of them, and nothing in this release depends on
them.

---

*Round 6 OPEN. Pin `ad65a244…`. Release `platterpus-2026.08.03` (local tag; pin the
SHA). Ship your version once you have verified — this round does not need to wait
for hardware.*

---

## Appendix 1 — golden reference log at pin `ad65a24` (269 lines)

Generated with `-Z 2` per your A4, so the secure-re-read surface is
exercised again. Regenerate exactly:

```sh
mkdir /tmp/g && cp tests/fixtures/pregap.cue /tmp/g/ && cp tests/fixtures/cdda.bin /tmp/g/pregap.bin
cd /tmp/g && cyanrip -d pregap.cue -N -A -Q -s 0 -o flac -Z 2 \
                    -D o -F "{track}" -L reference -M sheet -P 0
```

Varying per run: `Invoked as:`, `creation_time`, `Extraction speed:`,
`Elapsed:`, the paranoia counters at both levels, `Encoder:`, and the
`Log FUN512:` that covers them.

```
cyanrip 0.9.4-rc1 (platterpus-fork-g7db3743)
Invoked as:     /home/user/cyanrip/build/src/cyanrip -d pregap.cue -N -A -Q -s 0 -o flac -Z 2 -D o -F {track} -L reference -M sheet -P 0
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
    Extraction speed:  55.9x
    Elapsed:            0.05 s
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
    creation_time:                 2026-08-03T03:06:40
    REPLAYGAIN_TRACK_GAIN:         -10.29 dB
    R128_TRACK_GAIN:               -1355
    REPLAYGAIN_TRACK_RANGE:        20.00 dB
    REPLAYGAIN_TRACK_PEAK:         1.005757
    REPLAYGAIN_REFERENCE_LOUDNESS: -18.00 LUFS

  Paranoia status counts:
    READ:          225

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
    Extraction speed:  49.0x
    Elapsed:            0.04 s
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
    creation_time:                 2026-08-03T03:06:40
    REPLAYGAIN_TRACK_GAIN:         -11.19 dB
    R128_TRACK_GAIN:               -1584
    REPLAYGAIN_TRACK_RANGE:        0.00 dB
    REPLAYGAIN_TRACK_PEAK:         1.033086
    REPLAYGAIN_REFERENCE_LOUDNESS: -18.00 LUFS

  Paranoia status counts:
    READ:          150

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
    Extraction speed:  41.1x
    Elapsed:            0.02 s
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
    creation_time:                 2026-08-03T03:06:41
    REPLAYGAIN_TRACK_GAIN:         4.63 dB
    R128_TRACK_GAIN:               2465
    REPLAYGAIN_TRACK_RANGE:        0.00 dB
    REPLAYGAIN_TRACK_PEAK:         0.273444
    REPLAYGAIN_REFERENCE_LOUDNESS: -18.00 LUFS

  Paranoia status counts:
    READ:          75

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
  READ:          1350

Ripping errors: 0
Rip completed:  yes (3 of 3 tracks)
Ripping finished at 2026-08-03T03:06:41
Log FUN512: LTGnkAmynhx9Qttgt9xd8zX6U_uaPiLpE_CnO7YaRsaemHH8.CG2v40KPoU7Jadzl0C0T5vnyylxn_aaGsN70w
```

## Appendix 2 — provider contract at source anchor `5122f6b24f907e4c`

# cyanrip provider contract

**Generated** by `tools/gen-provider-contract.py` from the source tree and the
built binary. Do not edit by hand -- regenerate. A hand-written contract goes
stale silently, which is the failure this file exists to prevent.

Build: `cyanrip 0.9.4-rc1 (platterpus-fork-g<commit>)`

**Source anchor:** `sha256/16 = 5122f6b24f907e4c` over `src/*.c` and
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
| `cyanrip_main.c:272` | `Invalid number of tracks: %i!` |
| `cyanrip_main.c:295` | `CDIO returned invalid track %i end LSN` |
| `cyanrip_main.c:502` | `Frame read failed!` |
| `cyanrip_main.c:579` | `Loading data for track %i...` |
| `cyanrip_main.c:586` | `Stopping, offset finding incomplete!` |
| `cyanrip_main.c:594` | `Data loaded, searching for offsets...` |
| `cyanrip_main.c:603` | `Nothing found for track %i%s` |
| `cyanrip_main.c:608` | `Offset of %c%i found in track %i%s` |
| `cyanrip_main.c:613` | `Offset of %c%i confirmed (confidence: %i) in track %i%s` |
| `cyanrip_main.c:617` | `New offset of %c%i found at track %i, scrapping old offset of %c%i%s` |
| `cyanrip_main.c:631` | `No track had AccuRip entry, cannot find offset!` |
| `cyanrip_main.c:633` | `No track was long enough, unable to find drive offset!` |
| `cyanrip_main.c:635` | `Was not able to find drive offset with a radius of %i frames, trying again with a larger radius...` |
| `cyanrip_main.c:641` | `Drive offset of %c%i found (confidence: %i)!` |
| `cyanrip_main.c:671` | `Unable to read track %i subchannel info!` |
| `cyanrip_main.c:687` | `Track %i is data:` |
| `cyanrip_main.c:744` | `Error in decoding/sending frame: %s` |
| `cyanrip_main.c:756` | `Drive media changed, stopping!` |
| `cyanrip_main.c:787` | `Stopping, ripping incomplete!` |
| `cyanrip_main.c:905` | `Done; (%i out of %i matches for current checksum %08X)` |
| `cyanrip_main.c:911` | `Done; (no matches found, but hit repeat limit of %i)` |
| `cyanrip_main.c:927` | `Repeating ripping (%i out of %i matches for current checksum %08X)` |
| `cyanrip_main.c:942` | `Error in encoding: %s` |
| `cyanrip_main.c:958` | `Error sending flush signal to encoders: %s` |
| `cyanrip_main.c:965` | `Track %i ripped and encoded with errors.` |
| `cyanrip_main.c:967` | `Track %i ripped and encoded successfully!` |
| `cyanrip_main.c:1049` | `Gaps:` |
| `cyanrip_main.c:1054` | `%i frame gap between lead-in and track 1 pregap, merging into pregap` |
| `cyanrip_main.c:1061` | `%i frame unmarked gap between lead-in and track 1, marking as a pregap` |
| `cyanrip_main.c:1083` | `%i frame pregap in track %i,` |
| `cyanrip_main.c:1090` | `unmerged` |
| `cyanrip_main.c:1092` | `merging into track %i` |
| `cyanrip_main.c:1098` | `dropping` |
| `cyanrip_main.c:1104` | `merging` |
| `cyanrip_main.c:1111` | `splitting off into a new track, number %i` |
| `cyanrip_main.c:1152` | `%i frame discontinuity between tracks %i and %i,` |
| `cyanrip_main.c:1157` | `padding track %i` |
| `cyanrip_main.c:1160` | `ignoring` |
| `cyanrip_main.c:1168` | `%i frame gap between last track and lead-out, padding track` |
| `cyanrip_main.c:1233` | `Can't init signal handler!` |
| `cyanrip_main.c:1457` | `Invalid paranoia level %i must be between 0 and %i!` |
| `cyanrip_main.c:1470` | `Invalid max coverart size %i (must be 250, 500, 1200 or -1)` |
| `cyanrip_main.c:1482` | `Invalid sanitation method %s` |
| `cyanrip_main.c:1494` | `Invalid release index %i!` |
| `cyanrip_main.c:1503` | `Invalid discnumber %i` |
| `cyanrip_main.c:1510` | `Invalid totaldiscs %i` |
| `cyanrip_main.c:1514` | `discnumber %i is larger than totaldiscs %i` |
| `cyanrip_main.c:1527` | `Supported output codecs:` |
| `cyanrip_main.c:1535` | `Invalid format \"%s\"` |
| `cyanrip_main.c:1540` | `Duplicated format \"%s\"` |
| `cyanrip_main.c:1555` | `Duplicated rip idx %i` |
| `cyanrip_main.c:1569` | `Invalid track idx for pregap: %i` |
| `cyanrip_main.c:1575` | `Missing pregap action` |
| `cyanrip_main.c:1583` | `Invalid pregap action %s` |
| `cyanrip_main.c:1614` | `No cover art location specified for \"%s\"` |
| `cyanrip_main.c:1623` | `Invalid track idx for cover art: %i` |
| `cyanrip_main.c:1629` | `Cover art already specified for track idx %i!` |
| `cyanrip_main.c:1641` | `Cover art \"%s\" already specified!` |
| `cyanrip_main.c:1647` | `Too many cover arts specified!` |
| `cyanrip_main.c:1657` | `Directory name scheme must contain {format} with multiple output formats!` |
| `cyanrip_main.c:1662` | `-J (only generate a CUE sheet) cannot be used with -I (only print info)!` |
| `cyanrip_main.c:1678` | `Searching for drive offset, enabling AccuRip and disabling MusicBrainz and Cover art fetching...` |
| `cyanrip_main.c:1686` | `Offset is unset! To continue with an offset of 0, run with -s 0!` |
| `cyanrip_main.c:1766` | `MusicBrainz URL:%s` |
| `cyanrip_main.c:1810` | `Error reading album tags: %s` |
| `cyanrip_main.c:1840` | `Log(s) will be written to:` |
| `cyanrip_main.c:1848` | `CUE files will be written to:` |
| `cyanrip_main.c:1880` | `Invalid track number %i, list has %i tracks!` |
| `cyanrip_main.c:1896` | `Error reading track tags: %s` |
| `cyanrip_main.c:1950` | `Cover art destination(s):` |
| `cyanrip_main.c:1985` | `WARNING: tracks %i and %i resolve to the same file \"%s\", one will overwrite the other!` |
| `cyanrip_main.c:1996` | `Tracks:` |
| `cyanrip_main.c:2006` | `Track %i info:` |
| `cyanrip_main.c:2024` | `Error initializing decoder: %s` |
| `cyanrip_main.c:2033` | `Error initializing encoder: %s` |
| `cyanrip_main.c:2067` | `Error encoding: %s` |
| `cyanrip_main.c:2087` | `Invalid rip index %i, list has %i tracks!` |
| `cyanrip_main.c:2169` | `Error ripping: %s` |
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

**`cyanrip_main.c:871`** - reaches logfile: **no, stdout only**

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

**`cyanrip_main.c:1918`** - reaches logfile: yes

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
| `cyanrip_main.c:463` | `Still reading track %i at LSN %li - %` | **no, stdout only** |
| `cyanrip_main.c:487` | `Track %i resumed after %` | **no, stdout only** |
| `cyanrip_main.c:805` | `\r` | **no, stdout only** |
| `cyanrip_main.c:871` | `%s` | **no, stdout only** |
| `cyanrip_main.c:952` | `Flushing encoders...` | **no, stdout only** |
| `cyanrip_main.c:994` | `Force quitting` | **no, stdout only** |
| `cyanrip_main.c:997` | `\rTrying to quit` | **no, stdout only** |
| `cyanrip_main.c:1393` | `Log \"%s\" checksum valid.` | **no, stdout only** |
| `cyanrip_main.c:1396` | `Log \"%s\" checksum mismatch, the file has been modified!` | **no, stdout only** |
| `cyanrip_main.c:1400` | `Log \"%s\" has data after the checksum, the file has been modified!` | **no, stdout only** |
| `cyanrip_main.c:1404` | `No FUN512 checksum found in \"%s\"!` | **no, stdout only** |
| `cyanrip_main.c:1408` | `Couldn't read \"%s\"!` | **no, stdout only** |

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
| `cyanrip_main.c:272` | `Invalid number of tracks: %i!` | both | yes |
| `cyanrip_main.c:295` | `CDIO returned invalid track %i end LSN` | control flow | yes |
| `cyanrip_main.c:495` | `cdio error: %s` | control flow | yes |
| `cyanrip_main.c:502` | `Frame read failed!` | control flow | yes |
| `cyanrip_main.c:586` | `Stopping, offset finding incomplete!` | wording + goto end | yes |
| `cyanrip_main.c:671` | `Unable to read track %i subchannel info!` | wording | yes |
| `cyanrip_main.c:744` | `Error in decoding/sending frame: %s` | both | yes |
| `cyanrip_main.c:756` | `Drive media changed, stopping!` | both | yes |
| `cyanrip_main.c:787` | `Stopping, ripping incomplete!` | wording | yes |
| `cyanrip_main.c:905` | `Done; (%i out of %i matches for current checksum %08X)` | goto finalize_ripping | yes |
| `cyanrip_main.c:911` | `Done; (no matches found, but hit repeat limit of %i)` | goto finalize_ripping | yes |
| `cyanrip_main.c:942` | `Error in encoding: %s` | wording + goto end | yes |
| `cyanrip_main.c:958` | `Error sending flush signal to encoders: %s` | wording | yes |
| `cyanrip_main.c:994` | `Force quitting` | control flow | **no, stdout only** |
| `cyanrip_main.c:1404` | `No FUN512 checksum found in \"%s\"!` | control flow | **no, stdout only** |
| `cyanrip_main.c:1408` | `Couldn't read \"%s\"!` | both | **no, stdout only** |
| `cyanrip_main.c:1457` | `Invalid paranoia level %i must be between 0 and %i!` | both | yes |
| `cyanrip_main.c:1470` | `Invalid max coverart size %i (must be 250, 500, 1200 or -1)` | both | yes |
| `cyanrip_main.c:1482` | `Invalid sanitation method %s` | both | yes |
| `cyanrip_main.c:1494` | `Invalid release index %i!` | both | yes |
| `cyanrip_main.c:1503` | `Invalid discnumber %i` | both | yes |
| `cyanrip_main.c:1510` | `Invalid totaldiscs %i` | both | yes |
| `cyanrip_main.c:1514` | `discnumber %i is larger than totaldiscs %i` | control flow | yes |
| `cyanrip_main.c:1535` | `Invalid format \"%s\"` | both | yes |
| `cyanrip_main.c:1540` | `Duplicated format \"%s\"` | control flow | yes |
| `cyanrip_main.c:1555` | `Duplicated rip idx %i` | control flow | yes |
| `cyanrip_main.c:1569` | `Invalid track idx for pregap: %i` | both | yes |
| `cyanrip_main.c:1575` | `Missing pregap action` | both | yes |
| `cyanrip_main.c:1583` | `Invalid pregap action %s` | both | yes |
| `cyanrip_main.c:1614` | `No cover art location specified for \"%s\"` | both | yes |
| `cyanrip_main.c:1623` | `Invalid track idx for cover art: %i` | both | yes |
| `cyanrip_main.c:1629` | `Cover art already specified for track idx %i!` | control flow | yes |
| `cyanrip_main.c:1641` | `Cover art \"%s\" already specified!` | control flow | yes |
| `cyanrip_main.c:1647` | `Too many cover arts specified!` | control flow | yes |
| `cyanrip_main.c:1657` | `Directory name scheme must contain {format} with multiple output formats!` | control flow | yes |
| `cyanrip_main.c:1662` | `-J (only generate a CUE sheet) cannot be used with -I (only print info)!` | both | yes |
| `cyanrip_main.c:1686` | `Offset is unset! To continue with an offset of 0, run with -s 0!` | goto end | yes |
| `cyanrip_main.c:1810` | `Error reading album tags: %s` | both | yes |
| `cyanrip_main.c:1880` | `Invalid track number %i, list has %i tracks!` | both | yes |
| `cyanrip_main.c:1896` | `Error reading track tags: %s` | both | yes |
| `cyanrip_main.c:1918` | `%s` | goto end | yes |
| `cyanrip_main.c:2024` | `Error initializing decoder: %s` | both | yes |
| `cyanrip_main.c:2033` | `Error initializing encoder: %s` | both | yes |
| `cyanrip_main.c:2067` | `Error encoding: %s` | wording + goto end | yes |
| `cyanrip_main.c:2087` | `Invalid rip index %i, list has %i tracks!` | both | yes |
| `cyanrip_main.c:2169` | `Error ripping: %s` | wording + goto end | yes |
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

