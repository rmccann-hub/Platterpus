# cyanrip beta — `0.9.4-rc1+platterpus.5-beta.3`

*Information only. This file describes the beta and nothing else.*

---

## Identifiers

```
version   0.9.4-rc1+platterpus.5-beta.3
repo      rmccann-hub/cyanrip
branch    platterpus-fork
commit    e61e75a
banner    cyanrip 0.9.4-rc1+platterpus.5-beta.3 (platterpus-fork-ge61e75a)
tests     28/28
anchor    sha256/16 = b9f93e4fdc1fa4f4   (over src/*.c and src/*.h)
contract  PROVIDER-CONTRACT.md @ e61e75a
```

**The commit is the identifier.** There is no git tag and no GitHub release: the
git proxy in the build environment refuses tag pushes (`HTTP 403`, re-probed for
this build — `git ls-remote --tags origin` returns nothing) and no
release-creation API is reachable from it.

**This is a pre-release.** It claims no joint verification, and says so in every
logfile it writes. Round 7 is open and both projects declare HOLD.

**It supersedes `…+platterpus.5-beta.2` (`c5fb909`)** as the build to install — and is **observably identical** to it on every surface a consumer can see (`docs/AUDIT-2026-08-05.md` §5), so the 2026-08-04 rig evidence transfers.

## Build and verify

```sh
git clone <repo> && cd cyanrip
git checkout e61e75a
meson setup build && ninja -C build
meson test -C build --print-errorlogs
./build/src/cyanrip --version
```

Expected:

```
28/28 tests passing
cyanrip 0.9.4-rc1+platterpus.5-beta.3 (platterpus-fork-ge61e75a)
```

A banner ending `-dirty` means the tree had uncommitted changes and the commit
does not describe the binary.

## What every logfile from this build contains

```
cyanrip 0.9.4-rc1+platterpus.5-beta.3 (platterpus-fork-ge61e75a)
Invoked as:     …
Handshake:      round 7 lap 21 OPEN, verdict HOLD -- NOT a released build
Consumer:       <whatever --consumer was given>
                (reported by the caller, not verified by cyanrip)
```

`Handshake:` reads `lap 21` rather than lap 24 because a commit cannot contain
the hash of a file added after it, and lap 21 is the newest lap file this
commit contains.

## What is in this beta and was not in `…-beta.2`

**One code change, and it alters no observable surface.**

- **`dev_path` leaked on every argument-validation refusal.** Twenty
  refusals return between the option table and context init, and only context
  teardown frees it, so `-d <dev> -J -I` leaked 100 bytes. The allocation moved
  to after the last refusal: nothing in that window reads it, so late
  allocation cannot leak by construction.

  **Why it matters more than its size:** the leak aborted the suite under
  AddressSanitizer, so the sanitizers could not be run at all. They can now —
  **28/28 under `address,undefined`**, including a full `-Z 2 -G -j` rip.

**Everything else is unchanged from `beta.2`, and that is measured**
(`docs/AUDIT-2026-08-05.md` §5): same fixture, same flags, both binaries —
log body identical across 275 lines, cue sheet identical, decoded PCM identical
on every track, `-j` record identical but for `rip_time_us`. Only the version
string, build SHA, compiled-in lap and the checksum that follows from them
differ.

**So the 2026-08-04 rig evidence for `c5fb909` transfers to this build on every
surface a consumer can observe.**

For what `beta.2` added over `beta.1` — the pre-log replay, `Read stalls:`,
`-j`, the libcdio and genopt routing, and the track-1 pre-gap fix — see
`Changelog.md`.

## Flags relevant to this build

| flag | |
|---|---|
| `-u` / `--consumer <string>` | recorded verbatim in the log, explicitly not verified |
| `-j` / `--diagnostics <path>` | machine-readable JSON record; off unless given |
| `-k <seconds>` | stall threshold before liveness is reported (default 10, `0` disables) |
| `-x` / `--cache-probe` | measure the drive's readback cache before ripping; refuses on a disc image. **Never executed on real hardware** |

Flag count: 41 (was 40 — `-j` is new). Full generated interface in
`PROVIDER-CONTRACT.md @ e61e75a`.

## Known limits of this build

Full list with how to close each: `docs/AUDIT-2026-08-05.md` §3.

- **`-x` has never produced a measurement on a real drive, anywhere.** Still
  the largest gap. One throwaway rip closes it, and it now reports a stall if
  it wedges rather than hanging silently.
- **A non-zero `Read stalls:` count has never been produced anywhere.** The
  `none` form is hardware-confirmed as of 2026-08-04; the populated forms are
  unit-tested against the formatter and have never been emitted by a drive.
- **The diagnosed-abort exit code has never fired on hardware** — the rig rip
  had `Ripping errors: 0`.
- **`-j` has never been written by a rip from a physical drive.**
- **`-f` and CD-TEXT from a disc that has some** remain unrun.
- **The track-1 pre-gap fix is hardware-unprovable on the current collection** —
  Platterpus measured 40+ `Pregap source:` lines across three days and **zero**
  say `TOC`. A disc image whose TOC declares a track-1 HTOA is the cheapest
  route left, and needs no drive.
