# cyanrip beta — `0.9.4-rc1+platterpus.5-beta.2`

*Information only. This file describes the beta and nothing else.*

---

## Identifiers

```
version   0.9.4-rc1+platterpus.5-beta.2
repo      rmccann-hub/cyanrip
branch    platterpus-fork
commit    c5fb909
banner    cyanrip 0.9.4-rc1+platterpus.5-beta.2 (platterpus-fork-gc5fb909)
tests     28/28
anchor    sha256/16 = 1f09494a9899867b   (over src/*.c and src/*.h)
contract  PROVIDER-CONTRACT.md @ c5fb909
```

**The commit is the identifier.** There is no git tag and no GitHub release: the
git proxy in the build environment refuses tag pushes (`HTTP 403`, re-probed for
this build — `git ls-remote --tags origin` returns nothing) and no
release-creation API is reachable from it.

**This is a pre-release.** It claims no joint verification, and says so in every
logfile it writes. Round 7 is open and both projects declare HOLD.

**It supersedes `…+platterpus.5-beta.1` (`9003e6f`)** as the build to install.

## Build and verify

```sh
git clone <repo> && cd cyanrip
git checkout c5fb909
meson setup build && ninja -C build
meson test -C build --print-errorlogs
./build/src/cyanrip --version
```

Expected:

```
28/28 tests passing
cyanrip 0.9.4-rc1+platterpus.5-beta.2 (platterpus-fork-gc5fb909)
```

A banner ending `-dirty` means the tree had uncommitted changes and the commit
does not describe the binary.

## What every logfile from this build contains

```
cyanrip 0.9.4-rc1+platterpus.5-beta.2 (platterpus-fork-gc5fb909)
Invoked as:     …
Handshake:      round 7 lap 20 OPEN, verdict HOLD -- NOT a released build
Consumer:       <whatever --consumer was given>
                (reported by the caller, not verified by cyanrip)
```

`Handshake:` reads `lap 20` rather than lap 21 because a commit cannot contain
the hash of a file added after it.

## What is in this beta and was not in `…-beta.1`

**Fixed**

- **Track 1's pre-gap length counted the 2-second lead-in twice** on any disc
  whose TOC signals an HTOA. `Pregap length: 300 frames` and `00:04.00` against
  a `Gaps:` block, an LSN subtraction and a cue sheet that all said 150. Now
  150 everywhere. *Only affects discs with a track 1 pre-gap; the 2026-08-04 rig
  disc has none and reported 150 correctly.*
- **Everything said before the logfile existed reached stdout and nowhere
  else** — the drive open, the metadata lookups, and seven refusal paths. It is
  now replayed into the logfile as a delimited block after the header.
- **libcdio's own messages never reached cyanrip.** Its default handler prints
  to stderr and exits the process itself, so a bad `-d` produced a run whose
  exit code could not be reported.
- **genopt's own messages did not either** — every argument-parsing error went
  to the terminal only.
- **The diagnostics record kept only the first 10000 messages**, discarding the
  last — which is the one that explains a failure.

**Added**

- **`Read stalls:`** in the disc summary, in three forms:
  `none (no read exceeded 10s)`, `N reads exceeded 10s; longest Ns (track T,
  LSN L)`, or `unknown (stall reporting disabled with -k 0)`.
- **`-j` / `--diagnostics <path>`** — a JSON record written for every run,
  including runs that open no logfile at all. Off unless asked for.

## Flags relevant to this build

| flag | |
|---|---|
| `-u` / `--consumer <string>` | recorded verbatim in the log, explicitly not verified |
| `-j` / `--diagnostics <path>` | machine-readable JSON record; off unless given |
| `-k <seconds>` | stall threshold before liveness is reported (default 10, `0` disables) |
| `-x` / `--cache-probe` | measure the drive's readback cache before ripping; refuses on a disc image. **Never executed on real hardware** |

Flag count: 41 (was 40 — `-j` is new). Full generated interface in
`PROVIDER-CONTRACT.md @ c5fb909`.

## Known limits of this build

- **`-x` has never produced a measurement on a real drive.** Any number it
  prints is unverified.
- **The exit-code fix is still untested.** Its paths are not reachable from a
  disc image, and the 2026-08-04 rig rip had `Ripping errors: 0`.
- **A non-zero `Read stalls:` count has never been produced anywhere.** The
  accounting is unit-tested on synthetic stalls; no drive has stalled under it.
- **No hardware path is verified by the test suite**: the MMC sub-channel read,
  C2 reporting, `-f` offset autodetection, damaged media, and CD-TEXT from a
  physical disc are outside what disc images can exercise. The 2026-08-04 rig
  session retired the sub-channel pre-gap read and `-Z` convergence **for
  `9003e6f`**; nothing in this beta has been near a disc.
