# cyanrip fork — full audit, 2026-08-05

*What this build does not know about itself. Written for Platterpus so the gaps
are testable rather than discoverable.*

**Subject:** `0.9.4-rc1+platterpus.5-beta.3`, commit `e61e75a`.
**Method:** every row below is a command that was run, not a recollection. Where
a check could not be run, the row says so instead of being omitted — a missing
row reads as a pass.

---

## 0. Summary

| | |
|---|---|
| defects found this audit | **1** (a memory leak, fixed — §1.1) |
| defects found and **not** fixed | 0 |
| deliberately deferred to round 8 | 2 log-text changes (§4) |
| gaps that no test here can close | 7 (§3) |

**The headline is §3.** Everything in §1 and §2 is closed; §3 is the list of
things that will still be untrue-by-omission after this beta, and it is the
list worth building a test plan from.

---

## 1. What the audit found

### 1.1 A memory leak on every argument-validation refusal — FIXED

```
$ ASAN_OPTIONS=detect_leaks=1 cyanrip -d basic.cue -J -I
Direct leak of 100 byte(s) in 1 object(s)
    #1 in cyanrip_run src/cyanrip_main.c:1474      <- strdup(device)
```

`settings.dev_path` was `strdup`'d with the rest of the settings and is freed
only by `cyanrip_ctx_end()`. **Twenty** validation refusals `return 1` between
the option table and `cyanrip_ctx_init()`, and none of them reach that free.

**Fixed by moving the allocation after the last refusal**, not by freeing on
each path — nothing in that window reads `dev_path`, so allocating late cannot
leak by construction, whereas twenty cleanup sites work until the
twenty-first is added.

**Why it had never been seen:** the sanitizers could not be run at all. The
leak aborts under meson's `abort_on_error=1`, so `cue_only` failed and the
whole ASAN suite was unusable. **28/28 under `address,undefined` now**,
including a full `-Z 2 -G -j` rip.

### 1.2 Checks that found nothing, stated so the absence is not mistaken for silence

| check | result |
|---|---|
| full suite under ASAN + UBSAN | **28/28**, 0 sanitizer errors |
| full `-Z -G -j` rip under ASAN + UBSAN | 0 errors, 0 leaks |
| `warning_level=3` (`-Wextra -Wpedantic`) | 8 `-Wsign-compare`, **all in pre-existing upstream code**, none in anything this fork added; all are `int` vs `size_t` loop bounds with no reachable negative value |
| dead struct fields | `cyanrip_ctx.success` only — already excluded from the `-j` record; nothing else |
| `TODO`/`FIXME`/`XXX` in `src/` | 8, all in `pregap.c`, all inherited from upstream PR #115 and all about macOS or drive quirks this environment cannot reach |
| provider contract staleness | `--check` exits 0 |
| release gate | refuses a stable release; permits a pre-release after naming the open round |

**One method note, because it produced a wrong answer first.** The dead-field
scan initially reported 31 fields as "read but never written", including
`settings` (187 reads). The write-detection regex missed `&ctx->field` and
element assignment. The reliable form — *a field whose name occurs at most once
in all of `src/*.c` cannot be both set and used* — returned six, of which five
are read in headers the first scan did not cover. **A grep hit is not a fact**,
and the first version of this section would have shipped 30 false findings.

---

## 2. What the rig session closed (`c5fb909`, 2026-08-04)

Retired from the not-proven list by Platterpus's session, on a Pioneer
BDR-209D against the EAC baseline disc:

| | |
|---|---|
| **14/14 bit-perfect vs EAC** | every candidate CRC equals EAC's committed baseline |
| pre-log replay block | six lines, present in the logfile, parser-inert |
| `Read stalls:` | `none (no read exceeded 10s)` — **first hardware sighting**, parsed tri-state (`0`, not `null`) |
| `C2 errors: unsupported by drive` | first hardware sighting |
| `--verify-log` on a real rip log | `verified` |
| all four pre-gap sources agree | `Gaps:` / per-track / LSN subtraction / cue `INDEX 00`, nine non-zero pre-gaps |
| the two provenance witnesses agree | `ripper_handshake_approval` and the compiled-in `Handshake:` note |

**This audit's build is observably identical to that one** — §5.

---

## 3. What is still not known — the test-plan list

**Nothing below is a defect. Each is a claim this build cannot make.**

### 3.1 `-x` — never executed on a real drive, anywhere, ever

The single largest gap and the oldest. `-x` measures the drive's readback cache
with raw `cdio_read_audio_sectors()` calls. It refuses on disc images, so **no
test in this repository has ever executed its measurement path**, and no rig
session has run it.

- **Cost to close:** one throwaway rip. It now reports a stall if it wedges
  (`Still reading track 0 - the read for LSN N has not returned after Ts`),
  which is why asking is reasonable — before that a hang would have been silent.
- **What it would prove:** that the number it prints is a number at all.
- **A hang is also a result.** If the stall report fires, that is the
  measurement.

### 3.2 A non-zero `Read stalls:` count — never produced anywhere

`none` is now hardware-confirmed. The populated forms are unit-tested against
the pure formatter (`tests/stall.c`, all four shapes asserted whole with
`strcmp`) but **no drive has ever stalled under this code**:

```
Read stalls:    2 reads exceeded 10s; longest 187s (track 4, LSN 45231)
Read stalls:    1 read exceeded 30s; longest 42s (track 1, LSN 0)
```

- **Needs:** damaged or marginal media. A disc that makes paranoia work hard.
- **Note:** `-k <seconds>` lowers the threshold, so a slow drive or a scratched
  disc plus `-k 1` is the cheapest provocation.
- **A silent watchdog is not a working watchdog.** Zero heartbeats on healthy
  media is the expected result and is not evidence either way.

### 3.3 The diagnosed-abort exit code

A refusal to start, or a rip that fails outright, must exit non-zero. The rig
rip had `Ripping errors: 0`, so nothing aborted. **The fix has never fired on
hardware.**

- **Needs:** a rip that genuinely fails — unreadable disc, ejected mid-rip, a
  write target that fills.

### 3.4 `-j` on real hardware

The diagnostics record has never been written by a rip from a physical drive.
Everything about it is exercised on images and in `tests/diag.c`.

- **Cost:** add `-j <path>` to one rig invocation. Off by default, so it
  changes nothing else.
- **Worth checking:** `read_stalls` and `rip.track_state` against the same
  facts in the log, i.e. that the two agree.

### 3.5 `-f` offset autodetection

Never run. Requires a disc with an AccurateRip entry and a drive whose offset
is not already known.

### 3.6 CD-TEXT from a physical disc

`CD-TEXT: none reported by libcdio` is the null, correctly stated — but a disc
that *has* CD-TEXT goes through `mmc_read_cdtext`, a different code path from
the `.toc` image parser the test suite uses.

- **Needs:** a disc with CD-TEXT. Most commercial CDs do not have it; some
  reissues and many Japanese pressings do.

### 3.7 The track-1 pre-gap fix — hardware-unprovable on the current collection

Platterpus measured this and the result is worth keeping: across **40+
`Pregap source:` lines spanning three days of rips, zero say `TOC`.** The fix
fires only where the TOC declares a track-1 pre-gap.

- **This is a measured "no candidate exists", not "untested".**
- **Cheapest route left:** a **disc image** whose TOC declares a track-1 HTOA,
  run with `-d image.cue`. No hardware needed. Our own `pregap.cue` fixture is
  exactly that and the fix is asserted against it — so what is missing is
  confirmation on a *real* TOC, not confirmation at all.

---

## 4. Deliberately not fixed — two log-text changes deferred to round 8

Both were raised by Platterpus as notes, both explicitly **not blocking**, and
both are contract-frozen lines. The rule is that a frozen line is never
reworded silently; the rename is proposed in a round.

### 4.1 `Tracks ripped partially accurately: 1/1`

Sits beside `Tracks ripped accurately: 13/14`. The denominator is *tracks not
fully verified*, so `1/1` is self-referential, and a consumer rendering the two
lines as one disc-level tally over-reports.

**Proposed for round 8:** state the denominator the same way both lines do, or
name it in the line. Not changed in this beta, because changing it now would
invalidate the rig evidence for a line that is merely confusing rather than
wrong.

### 4.2 `Release ID unavailable, cannot search Cover Art DB!`

Appears in the replayed pre-log block, two lines above a header that prints
`Release ID: d14a7546-…`. Both are true — the ID arrived as an `-a` tag, so
cyanrip genuinely had none of its *own* at cover-art time.

**Proposed for round 8:** name which release ID is absent.

---

## 5. This build versus the one the rig tested

**`e61e75a` (beta.3) carries one code change over `c5fb909` (beta.2): the
§1.1 leak fix.** It alters no observable surface, and that is measured rather
than asserted — same fixture, same flags, both binaries:

| surface | result |
|---|---|
| log body (275 lines) | **identical**, after normalising the version string and output path |
| cue sheet | **identical** |
| decoded PCM, all 3 tracks | **identical** (`ffmpeg -f md5`) |
| `-j` record | identical except `rip_time_us`, which differs between any two runs of the same binary |

What necessarily differs: the version string, the build SHA, the compiled-in
`Handshake:` lap, and the `Log FUN512:` that follows from them.

**So the rig evidence for `c5fb909` transfers to `e61e75a` on every surface a
consumer can observe.** That is the long true sentence; the short one — "the
builds are identical" — is false, because the version string is not.

---

## 6. What this audit did not check

- **Anything requiring a disc.** No drive is attached to this environment.
- **Concurrency beyond the watchdog.** The stall watchdog's thread is
  exercised; the encoder threads are not tested under TSAN. Not attempted.
- **Fuzzing of the log parser** — we do not parse logs; `--verify-log` reads
  its own checksum and is unit-tested, but no fuzzer has been pointed at it.
- **Long rips.** The longest thing this suite rips is three tracks of synthetic
  audio. Nothing here would catch a defect that needs an hour of runtime, and
  the `-j` message cap (10000 head + 10000 tail) has only ever been exercised
  by `tests/diag.c` driving it directly.
