# cyanrip beta — `0.9.4-rc1+platterpus.5-beta.4`

*Information only. This file describes the beta and what to test in it, and
nothing else.*

---

## Identifiers

```
version   0.9.4-rc1+platterpus.5-beta.4
repo      rmccann-hub/cyanrip
branch    platterpus-fork
commit    f5e11ba
banner    cyanrip 0.9.4-rc1+platterpus.5-beta.4 (platterpus-fork-gf5e11ba)
tests     28/28
anchor    sha256/16 = da96b1223b0e182b   (over src/*.c and src/*.h)
contract  PROVIDER-CONTRACT.md @ f5e11ba
```

**The commit is the identifier.** There is no git tag and no GitHub release: the
git proxy in the build environment refuses tag pushes (`HTTP 403`,
`git ls-remote --tags origin` returns nothing) and no release-creation API is
reachable from it.

**This is a pre-release.** It claims no joint verification, and says so in every
logfile it writes. Round 7 is open and both projects declare HOLD.

**It supersedes `…-beta.3` (`e61e75a`) and `…-beta.2` (`c5fb909`) as the build
to install — but read the next section before assuming the rig evidence carries
over. Unlike `beta.3`, this build is *not* observably identical to the one the
rig tested.**

## Build and verify

```sh
git clone <repo> && cd cyanrip
git checkout f5e11ba
meson setup build && ninja -C build
meson test -C build --print-errorlogs
./build/src/cyanrip --version
```

Expected:

```
28/28 tests passing
cyanrip 0.9.4-rc1+platterpus.5-beta.4 (platterpus-fork-gf5e11ba)
```

A banner ending `-dirty` means the tree had uncommitted changes and the commit
does not describe the binary.

**If you ran the previous beta's suite and saw 27/28, that was a defect in our
test harness and not in your setup.** `version_matrix` resolved upstream
`master` as a local branch, and `git clone` creates a local branch only for the
remote's HEAD — which is `platterpus-fork` — so a fresh clone had
`origin/master` and no `master`, and the check failed with *"master is
unreachable"*. It passed in our working tree, which happens to carry the
branch, so `beta.3`'s note claimed 28/28 from a clean checkout and that was not
true for anyone who cloned. Fixed here, and this beta's 28/28 was verified in a
fresh clone rather than in the tree that built it.

## What changed, and it is exactly two log lines

Both were raised as non-blocking notes and both were carried as known
imprecision. They are **proposals shipped in a beta so they can be run**, and
either can be withdrawn.

`git diff e61e75a..f5e11ba -- src/` touches two files and nothing else.

### 1. Cover art — the line now names which release ID, and when

```diff
- Release ID unavailable, cannot search Cover Art DB!
+ No MusicBrainz release ID at cover art lookup, cannot search Cover Art DB!
```

The old line sits in the replayed pre-log block, two blocks above a header that
prints `Release ID: <uuid>`. Both were always true — `-R` and a user
`-a musicbrainz_albumid=` are merged into the metadata **after** the cover-art
lookup runs, so cyanrip genuinely had no ID of its own at that moment — but the
pair reads as a contradiction. The new line states what was observed rather
than the stronger claim that the release has no ID.

**The trailing `cannot search Cover Art DB!` is unchanged**, so a substring
match on the tail still works. An exact-string match does not.

### 2. AccurateRip — both tally lines now divide by the disc

```diff
  Tracks ripped accurately: 13/14
- Tracks ripped partially accurately: 1/1
+ Tracks ripped partially accurately: 1/14
```

The partial line divided by *tracks not fully verified* while the line above it
divides by the disc's track count, so `1/1` was a denominator derived from the
first line's result and the pair read as one tally over-reports. Both now
divide by the track count.

**The numerators are unchanged, and so is which track falls in which bucket.**
Same disc, same verdict, different denominator.

**This one changes a number, not only text.** A stored `1/1` from the
2026-08-04 run becomes `1/14` on the same disc.

## What to test

### Highest value, cheapest, and specific to this beta

**Re-rip the 2026-08-04 baseline disc (DiscID `E20DFE0E`) on `f5e11ba` and diff
the log against the one you already have.**

Everything must be byte-identical except:

| expected to differ | |
|---|---|
| the version banner | `beta.4`, `gf5e11ba` |
| `Handshake:` | reads `round 7 lap 24` |
| timing fields | `Elapsed:`, `Extraction speed:`, `Ripping finished at` |
| `Log FUN512:` | follows from all of the above |
| the two lines above | §1 and §2 |

**If anything else moves, that is a finding.**

The second line is the one that matters most: **it has never executed
anywhere.** The block needs an AccurateRip database hit, the lookup fetches over
the network with no local-file input, and the synthetic test discs are not in
the database — measured, a fixture rip with lookups enabled reports
`AccurateRip:    not found` and prints no tally at all. Your baseline disc is
the only place this can be verified.

### Everything else, unchanged from the previous beta

Nothing else in this build is new, so the standing list still stands, in
priority order:

1. **`-x` — never executed on a real drive, anywhere, ever.** Still the largest
   gap in the project. One throwaway rip closes it. It now reports a stall if
   it wedges rather than hanging silently, which is why asking is reasonable.
   **A hang is also a result.**
2. **A non-zero `Read stalls:` count — never produced anywhere.** `none` is
   hardware-confirmed as of 2026-08-04; the populated forms are unit-tested
   against the formatter and no drive has ever emitted one. Needs marginal
   media; `-k 1` is the cheapest provocation.
3. **The diagnosed-abort exit code** — the rig rip had `Ripping errors: 0`, so
   nothing has ever aborted. Needs a rip that genuinely fails.
4. **`-j` from a physical drive** — the diagnostics record has only ever been
   written by image rips. Add `-j <path>` to one rig invocation; it is off by
   default and changes nothing else. Worth cross-checking `read_stalls` and
   `rip.track_state` against the same facts in the log.
5. **`-f` offset autodetection**, and **CD-TEXT from a disc that has some** —
   both unrun. A physical disc's CD-TEXT goes through `mmc_read_cdtext`, a
   different code path from the `.toc` image parser the suite uses.

### One thing to know before relying on `PROVIDER-CONTRACT.md`

**The contract did not change when change §2 did.** P2 derives each entry from
the *format string* at the call site, and §2 changed an argument, so the row is
byte-identical before and after and `--check` exits 0 across it.

**The contract derives the shape of a line, not the meaning of its numbers.**
Deliberately not patched on the way out — a half-working argument extractor
would put wrong text into a document that presents itself as derived. It is
proposed as round 8 work with the cost stated.

## What every logfile from this build contains

```
cyanrip 0.9.4-rc1+platterpus.5-beta.4 (platterpus-fork-gf5e11ba)
Invoked as:     …
Handshake:      round 7 lap 24 OPEN, verdict HOLD -- NOT a released build
Consumer:       <whatever --consumer was given>
                (reported by the caller, not verified by cyanrip)
```

`Handshake:` reads `lap 24` rather than lap 25 because a commit cannot contain
the hash of a file added after it, and lap 24 is the newest lap file this
commit contains.

## Flags relevant to this build

| flag | |
|---|---|
| `-u` / `--consumer <string>` | recorded verbatim in the log, explicitly not verified |
| `-j` / `--diagnostics <path>` | machine-readable JSON record; off unless given |
| `-k <seconds>` | stall threshold before liveness is reported (default 10, `0` disables) |
| `-x` / `--cache-probe` | measure the drive's readback cache before ripping; refuses on a disc image. **Never executed on real hardware** |

Flag count: 41. Full generated interface in `PROVIDER-CONTRACT.md @ f5e11ba`.

## What this build still cannot claim

Full list with the cost to close each: `docs/AUDIT-2026-08-05.md` §3.

- **The two changed lines have not run on a drive**, and §2 has not run
  anywhere at all.
- **`-x` has never produced a measurement on a real drive.**
- **A non-zero `Read stalls:` count has never been produced anywhere.** A silent
  watchdog is not a working watchdog — zero heartbeats on healthy media is the
  expected result and is not evidence either way.
- **The diagnosed-abort exit code has never fired on hardware.**
- **`-j` has never been written by a rip from a physical drive.**
- **`-f` and CD-TEXT from a disc that has some** remain unrun.
- **The track-1 pre-gap fix is hardware-unprovable on the current collection** —
  40+ `Pregap source:` lines across three days of rips and **zero** say `TOC`.
  A disc image whose TOC declares a track-1 HTOA is the cheapest route left,
  and needs no drive.
