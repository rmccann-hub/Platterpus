# cyanrip beta — `0.9.4-rc1+platterpus.5-beta.1`

*Information only. This file describes the beta and nothing else.*

---

## Identifiers

```
version   0.9.4-rc1+platterpus.5-beta.1
repo      rmccann-hub/cyanrip
branch    platterpus-fork
commit    9003e6f
banner    cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)
tests     24/24
anchor    sha256/16 = c109971e81cbba95   (over src/*.c and src/*.h)
contract  PROVIDER-CONTRACT.md @ 9003e6f
```

**The commit is the identifier.** There is no git tag and no GitHub release: the
git proxy in the build environment refuses tag pushes (`HTTP 403`, re-probed for
this build) and no release-creation API is reachable from it.

**This is a pre-release.** It claims no joint verification, and says so in every
logfile it writes.

## Build and verify

```sh
git clone <repo> && cd cyanrip
git checkout 9003e6f
meson setup build && ninja -C build
meson test -C build --print-errorlogs
./build/src/cyanrip --version
```

Expected:

```
24/24 tests passing
cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)
```

A banner ending `-dirty` means the tree had uncommitted changes and the commit
does not describe the binary.

## What every logfile from this build contains

```
cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)
Invoked as:     …
Handshake:      round 7 lap 7 OPEN, verdict HOLD -- NOT a released build
Consumer:       <whatever --consumer was given>
                (reported by the caller, not verified by cyanrip)
```

`Handshake:` is derived at build time from this tree's handshake record. It reads
`lap 7` rather than `lap 8` because a commit cannot contain the hash of a file
added after it.

## What is in this beta and was not in `0.9.4-rc1+platterpus.4`

**Fixed**

- **A diagnosed abort no longer exits 0.** The exit code tracked read errors, so
  a refusal to start or a rip that failed outright printed its reason and
  returned success. Still within `{0, 1}`. *Not covered by any automated test —
  the affected paths need real hardware.*
- **`-x` can no longer hang without reporting it.** The cache probe ran before
  the stall watchdog started, so the one read most likely to wedge on a real
  drive had no liveness reporting. The watchdog now starts first and the probe
  brackets its own reads, printing
  `Still reading track 0 - the read for LSN N has not returned after Ts`.
  Track `0` means "not ripping a track".
- **The golden reference was regenerated from a clean tree.** The previous one
  carried a `-dirty` banner.

**Added**

- **Sample-peak cross-check.** The peak is measured a second way — max |sample|
  over the same frames the ebur128 filter sees — and a line appears **only when
  the two disagree**:
  `Sample peak disagreement: ebur128 X dBFS, direct scan Y dBFS (Z dB apart)`.
  Silent on agreement.
- **`--prerelease`** on `tools/release-gate.py`: a stable release stays refused
  while a handshake round is open; a pre-release is permitted after printing
  every open round.

## Flags relevant to this build

| flag | |
|---|---|
| `-u` / `--consumer <string>` | recorded verbatim in the log, explicitly not verified |
| `-k <seconds>` | stall threshold before liveness is reported (default 10, `0` disables) |
| `-x` / `--cache-probe` | measure the drive's readback cache before ripping; refuses on a disc image. **Never executed on real hardware** |

Flag count: 40. Full generated interface in `PROVIDER-CONTRACT.md @ 9003e6f`.

## Known limits of this build

- **`-x` has never produced a measurement on a real drive.** Any number it
  prints is unverified.
- **The exit-code fix is untested.** Its paths are not reachable from a disc
  image.
- **Seven refusal paths print to stdout only.** They fire before the logfile is
  opened, so their diagnostics do not appear in any log.
- **No hardware path is verified by the test suite**: the MMC sub-channel read,
  C2 reporting, `-f` offset autodetection, damaged media, and CD-TEXT from a
  physical disc are all outside what disc images can exercise.
