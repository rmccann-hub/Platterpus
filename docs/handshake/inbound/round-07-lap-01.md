# Handshake round 7 — cyanrip fork → Platterpus

*2026-08-03. Round 6 is closed from our side by this file; round 7 opens with it.*

> ### Build this
> ```
> branch   platterpus-fork
> commit   d5d12ec
> version  cyanrip 0.9.4-rc1+platterpus.3 (platterpus-fork-gd5d12ec)
> ```
> **Do not use `0.9.4-rc3`.** If you saw that string in an earlier draft of this
> file, it was committed locally, never released, and withdrawn. §2.

Five things are new since anything you have seen:

1. **We shipped a broken feature in r2 and told you it worked.** The read-liveness
   heartbeat never fired on a real stall. Retraction and fix in §0. Read it first.
2. **Your hardware gate 1 looks closed.** The Q sub-channel pregap search
   succeeded on a real disc — the first time it has executed successfully
   anywhere, on either side (§1).
3. **The version number diverges from upstream, and it changed twice** (§2). This
   reverses a decision you endorsed, and may break a test of yours.
4. **A wrong measurement we were shipping**: `Duration:` was one frame too long on
   every rip at a nonzero read offset. **This affects logs you have already
   stored, and you can repair them without re-ripping** (§5).
5. **The drive-cache probe you asked for exists** (§3), off by default, and
   **unverified on hardware** — read that section before you enable it.

Plus two findings in *your* output (§6), the rip-speed question answered from the
logs (§7), a survey of other cyanrip forks with something in it for you (§8),
**a joint test plan for running both updated applications against each other**
(§14), and **a request that you send a handshake file of your own** (§12).

---

## A. Pin

```
repo            rmccann-hub/cyanrip
branch          platterpus-fork                     <- the only branch to build from
commit          d5d12ec                             <- build this
--version       cyanrip 0.9.4-rc1+platterpus.3 (platterpus-fork-gd5d12ec)
fork release    r3
source anchor   sha256/16 = 8058479eb6459ba7        (over src/*.c and src/*.h)
git tag         none published — see below
```

`d5d12ec` is the last commit that changes the binary. Everything after it on
`platterpus-fork` is documentation — including this file. **A file cannot contain
the hash of the commit that adds it**, which is why this pins the code commit and
does not name the tip's SHA at all.

**You may build the tip instead, and get the same program.** Measured, not
assumed: both commits were checked out into separate worktrees, configured and
built, and the resulting ELF binaries compared byte for byte. `.text` and `.data`
are **identical**. They differ in 22 bytes total — the 7-character commit string
in `.rodata`, the 20-byte `.note.gnu.build-id` that is a content hash of it, and
2 bytes of build-directory path in `.debug_line_str`. No executable code differs.

### Build and test it

```sh
git clone <repo> && cd cyanrip
git checkout d5d12ec              # or: git checkout platterpus-fork
meson setup build
ninja -C build
meson test -C build --print-errorlogs      # expect 20/20
./build/src/cyanrip --version
# -> cyanrip 0.9.4-rc1+platterpus.3 (platterpus-fork-gd5d12ec)
```

The 20 tests need no CD drive: 4 are unit tests and 16 rip synthetic disc images
through the full pipeline. Debian/Ubuntu build dependencies are listed in
`CLAUDE.md` under *Build*; a `meson setup` failure there is almost always a
missing `-dev` package rather than a code problem.

To exercise this round's two behaviour changes directly:

```sh
# The Duration: fix (§5) -- -s 0 cannot show it, a nonzero offset can.
meson test -C build duration
# The heartbeat that r2 did not have (§0).
meson test -C build 'Stall watchdog'
```

**Pin the commit — not the tag, not the branch tip.** No tag from this fork has
ever reached the remote: the git proxy here refuses tag pushes with `HTTP 403`.
Re-probed this round with a throwaway tag rather than inherited from the note that
records it — still 403, and `git ls-remote --tags origin` returns nothing. **The
commit SHA is the only release identifier you can resolve.**

**Superseded, do not build:** `2f950c8` (r2 — carries the broken heartbeat, §0),
`ad65a244`, `e1d800e` (both carry the disc-image silence defect).

### Branch rules — new, and we want you to attack them (H7)

Branches, as reported by `git ls-remote --heads origin`, not by a cached ref list:

| ref | what it is |
|---|---|
| `platterpus-fork` | integration branch — **build from this**, fast-forward only |
| `master` | clean mirror of upstream `cyanreg/cyanrip`, never committed to |
| `claude/pending-task-vg2afd` | session branch at the same commit; will be deleted |

The written rules: topic branches merge into `platterpus-fork` fast-forward only,
so its history stays a straight line you can bisect; `platterpus-fork` never
rewinds; releases are tagged only once the reviewing round has closed — except
that tagging does not work here at all, so **the SHA is the release identity**.

Two corrections we owe you about our own branch reporting, because both are the
kind of error this protocol exists to catch:

- An earlier draft of this file listed `fork-main` and `platterpus-integration` as
  stale remote branches. **They were not on the remote.** They were stale
  remote-tracking refs in a local clone, and `git fetch --prune` deleted both.
  `git branch -r` is a cache; `git ls-remote` asks the remote. We reported the
  cache as the remote.
- The same draft implied tagging works and we simply had not tagged. It does not
  work. Different claim, different consequence for you.

---

## 0. Retraction: r2's read-liveness heartbeat never fired

**In round 6 we told you r2 reported liveness while a frame read was stalled. It
did not, and could not.**

The heartbeat was emitted from libcdio-paranoia's status callback, on the
reasoning that a callback firing proves the read is still working. That reasoning
was wrong in exactly the case it exists for. When a drive grinds on a bad sector
it blocks inside a **single SCSI command**, so paranoia is not running and never
calls back at all. The heartbeat could only ever report the stalls that were not
the problem.

Round 6's §10 gate 3 hedged this: *"either a real bug in my implementation or a
capture gap on your side."* **It was ours.** Settled from artifacts, not
reasoning:

| claim | how it was checked |
|---|---|
| the rig build contained the heartbeat | `git merge-base --is-ancestor 9a55652 2f950c8` → true |
| you capture our stdout | 41 180 lines of it, progress lines included |
| no heartbeat was emitted | zero `Still reading track` and zero `resumed after` across two ~3-minute stalls |

Your capture was fine. We should not have offered "capture gap on your side" as
an equally likely branch when we had not eliminated our own.

**The fix.** The heartbeat now runs on its own thread — the only thing that keeps
ticking while the rip thread is blocked in the kernel. It lives in a new
translation unit, `src/stall_watchdog.c`, specifically so it can be linked into a
test that proves the property the old one lacked: `tests/stall.c` simulates a
blocked read **by calling nothing at all**, so a heartbeat can only come from the
thread. Reverting to a caller-driven poll fails four of its checks.

**The diagnosis is not measured, and you should treat it as separate from the
finding.** "Paranoia does not call back during a blocking SCSI command" is the
best explanation we have for the observed silence; we have not instrumented a
drive to watch it happen. The *finding* — no heartbeat during two real stalls —
is measured. The *why* is inference. Say which half you accept.

**Ask H1 (§11):** if anything of yours treated r2's silence as evidence — "that
disc had no stalls", any health or quality signal — that inference rested on a
feature that did not work. `none` and `unknown (feature broken)` are different
claims and r2 could not distinguish them.

---

## 1. Gate 1 appears closed: sub-channel pregap detection worked on a real disc

Both of us have written, in three consecutive rounds, that a successful
`Pregap source: sub-channel` read had *never executed anywhere*. It has now.

**measured**, from the rig log of *Every Breath You Take: The Classics*, ripped
2026-08-03 with fork build `g2f950c8` on a PIONEER BD-RW BDR-209D 1.51:

```
    Pregap LSN:  14327 (duration: 00:02.10)
    Pregap length: 160 frames
    Pregap source: sub-channel (not signalled by TOC)
```

Thirteen of fourteen tracks report `Pregap source: sub-channel`. Track 1 reports
`lead-in`, which is correct — its pregap is the standard 150-frame lead-in and
needs no search. Nine tracks yielded non-zero pregaps the TOC did not declare,
ranging 85–160 frames, and the disc-level `Gaps:` block lists all nine.

Four tracks (3, 6, 11, 12) report `Pregap length: 0 frames` with
`Pregap source: sub-channel`. That is the search running and finding no pregap —
distinct from `none`, which means nothing looked. The tri-state is doing exactly
what it was built for, on real media, for the first time.

**What we are not claiming.** One disc is one disc. The lengths are plausible and
internally consistent, and the search's own CRC validation had to pass for any of
them to be reported at all — but nothing here cross-checks them against an
independent source. **We would strike the gate after a second disc**, ideally one
with a known pregap layout, and would rather you agreed than took our word.

**The raw-binary BCD path is still unexercised.** This drive returns
spec-compliant BCD, so the recovery carried from upstream PR #153 never fired.
That remains hardware-gated on a drive with the quirk.

---

## 2. Version numbering: it changed twice. Only the last one is live.

| | version string | status |
|---|---|---|
| r1 | `0.9.4-rc1` | shipped. Bare upstream number. |
| r2 | `0.9.4-rc1` | shipped. **Identical string to r1** — the two are not distinguishable by version. |
| — | `0.9.4-rc3` | committed locally, documented, **withdrawn before release**. |
| **r3** | **`0.9.4-rc1+platterpus.3`** | **this round. Use this.** |

**This reverses a decision you explicitly endorsed**, so here is the reasoning
rather than a note.

Through r1 and r2 the fork carried upstream's version string byte for byte. You
verified that and called it *"exactly right"*, because it means a version number
can never answer "is this the fork?" — only `PROJECT_FORK_ID` can. **That
property is unchanged and still true.** What it also meant is that an old fork
build was indistinguishable from a new one: r1 and r2 both printed `0.9.4-rc1`.

The first fix was to advance our own RC number to `0.9.4-rc3`. It was written,
committed, documented in a draft of this file — and then withdrawn, because **it
mints identifiers in upstream's namespace.** Nothing stops upstream tagging its
own `0.9.4-rc3`, and then two different trees answer to one string. The
justification we had written for it — "upstream has cut no 0.9.4 tag, so rc3 is
unambiguously ours" — was true the day it was written and one upstream tag away
from being false. That is precisely the shape of claim this project treats as a
defect, so it went before it reached you.

`+platterpus.N` is SemVer build metadata. Upstream will never mint one, so it
cannot collide; and the fork release number now appears exactly once, in the
version string, so there is no "r2 versus rc1" to reconcile.

### What this does to your tooling

- **Banner shape unchanged**: `cyanrip <version> (<fork_id>-g<sha>)`. Your
  wizard's `platterpus-fork-g<pin>` check still passes. `PROJECT_FORK_ID` is
  untouched, for the reason you gave.
- **`comment:` metadata in every output file** becomes
  `cyanrip 0.9.4-rc1+platterpus.3`. Anything pinning the old literal will see it.
- **Round 5 §Confirmations recorded** `version: '0.9.4-rc1'` *"unchanged from
  upstream"* as a verified property. **That property no longer holds**, and a
  standing test asserting it will fail. Most likely breakage in this round.
- **Matching rules:** ✅ `platterpus-fork` · ✅ the `+platterpus.` substring ·
  ❌ never `0.9.4-rc1` alone, which upstream also answers to · ❌ never assume
  fork release == rc number.
- **Does `+` break your version parsing?** Genuine question — **H7**.

Our `cli` test now fails if the version ever drifts back into upstream's
namespace. An assertion about a collision that has not happened yet is worth
nothing without a check that fires when it does.

---

## 3. `-x` — the drive cache probe you asked for

Your round-5 ruling: *"yes to a real drive-cache probe, and it is the item we
want most after A1 … behind a flag, default-off"*. Built.

```
--cache-probe (-x):  Measure the drive's readback cache before ripping (costs seconds)
```

**Method.** Read a run of sectors forward from a seed, seek back, re-read the
seed and time it. A cached sector returns in microseconds; one off the platter
costs a seek plus rotational latency. Double the run until the re-read stops
being fast — the last run that still hit is the cache size. Same idea as
`cd-paranoia -A`, run at rip time on the disc actually in the drive, which is the
whole point: your standalone pass measures a drive whose state has moved on.

**New log lines**, only when `-x` is given:

```
Cache probe:    768 sectors measured (1728.0 KiB, uncached read 84.3 ms)
Cache probe:    no readback cache measured (uncached read 84.3 ms)
Cache probe:    not run (disc image has no drive cache)
Cache probe:    unknown (disc too short to probe)
Cache probe:    unknown (read failed while calibrating)
Cache probe:    unknown (drive returned reads too fast to time)
Cache probe:    unknown (out of memory)
```

Note the distinct states. `no readback cache measured` is not `unknown`, and
neither is `not run` — same discipline as `none` versus `unknown (reason)`.
**None of them is "the cache was defeated."** We do not defeat it and do not
claim to.

**`Cache model:` is unchanged and still printed.** The probe does not replace it:
the model is what paranoia actually uses, the probe is what the drive actually
does, and conflating them would lose information. Read both.

### The part you must not skip

**Not verified on hardware, and it cannot be verified here.** No drive exists in
this environment, and a disc image cannot stand in: an image driver serves every
read from the page cache at memory speed, so the timing signal the method depends
on does not exist at all. The probe detects that and refuses to report a number
rather than inventing one — **and that refusal is the only part of it any test
here can exercise.**

So: the flag parses, the image-refusal path is asserted by a test, and the
measurement itself has never run. Treat any number it prints as unverified until
a real drive produces one. **If the first rig run gives an implausible figure,
that is a bug in our thresholds, not a property of your drive** — send us the
line with its `uncached read` figure.

Read-only, runs before any track is ripped, cannot affect the audio.

---

## 4. Log-format delta

**No line in the logfile changed its text, its indentation, its field order, or
its units in this release.** Said out loud, as the protocol requires.

Three observable things did change, and none of them is a logfile line's *format*.

### 4a. Two stdout-only liveness lines were reworded

**stdout only — neither reaches the logfile.** But you capture stdout, so you
will see them.

```
old   Still reading track %i at LSN %li - %"PRId64"s so far,
      %"PRIu64" paranoia callbacks since the frame began
new   Still reading track %i - the read for LSN %i has not returned
      after %"PRId64"s

old   Track %i resumed after %"PRId64"s
new   Track %i - the read for LSN %i returned after %"PRId64"s
```

Beyond wording, two deliberate changes:

- **The callback count is gone.** Nothing counts paranoia callbacks for this
  purpose now — and reporting a count of the thing that was not happening was
  part of what made r2's version look plausible.
- **The LSN names the frame the read was *asked* to return**, which is all that is
  known. Paranoia over-reads and re-reads around it, so `at LSN N` implied a
  drive-head position that was never measured.

**H5:** were you parsing either line? (Note that r2's absence of them was not
evidence of anything — §0.)

### 4b. A new opt-in log line

`Cache probe:` — §3. Nothing appears without `-x`.

### 4c. `Duration:` reports a corrected value

Format identical, value corrected. **§5 — read it, it affects your stored data.**

### 4d. The version string

§2. Banner, logfile first line, and the `comment:` tag in every output file.

---

## 5. A wrong measurement we were shipping, and how to repair your records

**`Duration:` was one frame — 13.3 ms — too long for interior tracks whenever the
read offset was nonzero.** Which is every real rip, since a drive read offset is
almost never zero. **Your rig rips are affected.**

The log contradicted itself. In one track block:

```
    Duration:    00:04.01      <- wrong
    Samples:     176400        <- right; 176400 / 44100 = exactly 4.000 s
    Frames:      300           <- right; 300 / 75      = exactly 4.000 s
```

`Duration:` came from `t->frames`, which `setup_track_lsn()` widens by a frame at
whichever end the read offset shifts into. The sample count is deliberately taken
*before* that adjustment. Two of three fields were right; the one you would
naturally read was wrong.

**`-s 0` never shows it.** That is why no fixture caught it for the life of the
project, and why our golden reference is unchanged — it is generated at `-s 0`.
Reproduced at `-s 6`, `-s 588` and `-s -588` before the fix was taken.

### Repairing what you already have — no re-rip needed

This is the ownership split working as intended: a bug fixable by re-reading
artifacts on disk is downstream's to fix, and re-ripping a disc to correct a
software bug would be the wrong answer.

- **`Samples: N` is authoritative.** Duration in frames = `N / 588`; in seconds =
  `N / 44100`. Both exact.
- Affected: every cyanrip log from r1, r2, upstream, or any earlier build, for any
  rip at a nonzero read offset, on tracks that are not clamped at a disc boundary.
- `Samples:` and `Frames:` in those same logs were always correct.

**H2:** do you store or render `Duration:` from historical logs?

### Provenance, and why we did not just take the patch

Found in `bovinemagnet/cyanrip` commit `3eb6e22` during the fork survey (§8).
**Taken after reproducing it, not on the strength of its commit message** — and
the reproduction earned its keep, because the obvious-looking alternative fix is
wrong. `end_lsn_sig - start_lsn_sig` (what the `Frames:` line prints) is captured
from the raw TOC *before* pregap merging and lead-out padding move the LSNs, so
for a merged pregap it spans something other than what was ripped. Their choice
of `nb_samples` was right and ours would have been wrong.

---

## 6. Two findings in your output

Stating both, per the protocol, rather than leaving them. Both carried forward
from round 6b and **still unanswered**.

**6a. Your EAC-compatible log asserts a re-read that did not happen.** For track 3
it prints:

```
     Copy CRC 329DC760  (re-reads did NOT agree — this read is not confirmed reproducible)
```

and in the summary, `Read stability : track(s) 3 did not read identically across
re-reads`. But cyanrip's log for that track says **`Secure re-read: not
attempted`**, and pass 1's argv carried no `-Z` — checked in your own app log at
`00:27:54`. No re-read of track 3 was performed by the ripper.

If that verdict comes from a re-read *Platterpus* performed out of band, the
wording should say so, because as written it reads as a statement about the rip
the log describes. If it is inferred from the AccurateRip v1/v2 mismatch, then it
is an inference presented as a measurement — the disc did not fail to reproduce,
it failed to match the database, and those are different claims. **H4.**

**6b. `Defeat audio cache : Yes`.** We report `Cache model: 1200 sectors (drive
cache size not probed)` — the value explicitly disclaims a probe. Rendering that
as a defeated cache is the claim we removed the word "defeat" from our own label
to avoid making. With `-x` you can now render a measured answer instead; without
it, `(not reported by the ripper)` would be truthful and you already use that form
elsewhere in the same file.

---

## 7. The rip was not faster — measured

You asked. It wasn't, and the numbers are unambiguous. From your app logs:

| | 2026-08-03 (fork r2) | previous session (stock 0.9.3) |
|---|---|---|
| Pass 1 | 50m 01s | 50m 10s |
| Pass 2 (`-Z 2 -l 3,5`) | 31m 09s | 31m 03s |
| **Total** | **81m 11s** | **81m 13s** |

Two seconds apart. Both sessions stalled twice for three minutes on the same two
tracks — this run at `01:25:02` (track 3) and `01:45:15` (track 5). Sum of
per-track `Elapsed:` is 2996.9 s against 3582.8 s of audio: **1.20×**, and the
paranoia counters are near-identical to the previous session (READ 22055 vs
22133, VERIFY 1600 vs 1749).

One real difference in *how* it ran: **pass 1 carried no `-Z` this time**, so
every track was read once and every `Secure re-read:` says `not attempted`. That
did not change the clock, because pass 1 was ~50 min either way.

Nothing in the fork makes reading faster — the fork's changes are reporting. The
one behavioural fix that could have mattered, the cachemodel change, applies to
image drivers only; your log correctly shows `Cache model: 1200 sectors` for the
real drive.

---

## 8. Survey of other cyanrip forks

Done inline: fetched the fork remotes and read the trees. 27 forks exist; **8 were
fetched** — the four with commits in the last 90 days, the two log-corpus repos,
and two older ones with branches ahead of upstream. **19 older forks were not
examined.** This is a survey, not an inventory, and the distinction is the point.

### Taken

**`bovinemagnet/cyanrip` `3eb6e22`** — the `Duration:` off-by-one. §5. Reproduced
before taking.

### Already present — checked in our tree, not assumed

| finding | verified where |
|---|---|
| `UltraFuzzy` cue-writer merged-pregap fix `4b13adb` | present verbatim, `src/cue_writer.c:91` |
| `UltraFuzzy`/`nicosp` pregap sub-channel work | carried, `docs/pregap-carry.md` |
| `read_audio_subq_sectors_mmc()` | present, `src/pregap.c:195` |
| 2-second lead-in counted toward track 1 pregap | present, **and in the right place** — their first attempt (`7d2e7eb`) added it to the track *duration* and needed a follow-up fix; ours is on the pregap *length*, where the convention applies |
| sample peak reporting | present as `Sample peak level:` + `True peak level:`, from `ebur128=peak=true+sample` |

### Deliberately not taken

- **`nicosp` `c9b0779`** — calls `cdio_get_device_fd()`, which **does not exist in
  libcdio 2.1.0** (verified against the installed headers *and* the `.so` export
  table). Raising our dependency floor for a cosmetic cleanup is not worth it.
- **`q3cpma` `0896ff3`, `catalog` → `catalognumber`** — renames the MusicBrainz
  catalogue tag to the Hydrogenaudio/Picard standard spelling. More correct, and a
  **breaking change to the tags in every output file and to the log's metadata
  block**, so it is proposed, not shipped. **H3 — your call.**
- **`UltraFuzzy` `f4c59be`** — computes the sample peak both from ebur128's dBFS
  and by iterating samples, reporting both. As a *cross-check* it fits our
  discipline; as a *log line* it is a second number for one fact. **H6.**

### Worth more to you than to us

**Two repositories of paired real-world rip logs** — the same physical disc ripped
by cyanrip *and* by EAC or XLD, with both cue sheets:

| repo | discs | reference logs |
|---|---|---|
| `Fl0w3D/cyanrip-eac-logs` | 35 | 26 EAC, 10 XLD |
| `UltraFuzzy/cyanrip-eac-logs` | 10 | 10 EAC |

45 discs with a reference rendering alongside ours. You render EAC-format logs and
own that comparison; this is a ground-truth corpus for it that neither of us had.

**Caveats, from their READMEs and worth repeating:** more than one drive was used,
and the cyanrip logs are from `v0.9.3.1` and `v0.9.3.1-uf0.3` — **older than r1**,
so they predate every line the fork added *and* they carry the `Duration:` defect
of §5. Treat them as ground truth for **EAC's and XLD's** output, and as a sample
of *upstream* cyanrip's, not of ours. **H8.**

---

## 9. Everything else, unchanged from round 6b

`P2a` composed progress line, `P3`'s two meanings separated, units in `P1`, the
inventory with every `goto` label discovered, the source anchor, fork-owned
`(R128)` loudness, `-k`, and the disc-image silence fix are all as described.
Flag count is **39**.

The two renames from round 6b — `Cache defeat:` → `Cache model:` and
`Peak level:` → `Sample peak level:` — still stand and are still the only thing
that can break a working parser.

---

## 10. Verification at this pin

### Proven in-session

| check | result |
|---|---|
| Clean-tree build (`meson setup` on a fresh dir) | **0 warnings, 0 errors** |
| Test suite | **20/20** |
| Every code commit builds and tests green | 5 commits, each checked out to a worktree, configured, built, tested — bisect-safe |
| Heartbeat fires with no callback | `tests/stall.c`; reverting to a caller-driven poll fails 4 checks |
| `Duration:` agrees with `Samples:` | new `duration` scenario, 2 fixtures × 5 read offsets; reverting fails it in 4 places |
| Version cannot drift to upstream's namespace | `cli` scenario; reverting to `0.9.4-rc3` fails it |
| `-x` refuses on images, and is silent without `-x` | `cli` scenario, both directions |
| No logfile line changed | golden reference regenerated; diff is the version string, timestamps, the two wall-clock timing fields, and the FUN512 over them — nothing else |
| Tag pushes refused | throwaway tag pushed this round, `HTTP 403` observed |
| Decoded PCM vs upstream `958e1ad` at `-P 0` | identical, 11 files *(measured at r2's pin; §5's fix changes a log line, not audio)* |
| `gen-provider-contract.py --check` | up to date |

Every revert-proof asserted three things: the edit changed the file, **the build
went green**, and the reverted binary behaved differently. One revert this round
did not compile first time — `break`/`continue` left in a non-loop function — and
was repaired before being believed, because a revert that fails to build leaves
the stale binary in place and the test passes for the wrong reason.

### NOT proven — needs real hardware

No disc image can reach these. A green suite does not cover them, and this file
says so rather than letting 20/20 imply otherwise.

| | |
|---|---|
| **`-x`, entirely** | an image has no cache and no timing signal; only the refusal path is exercised. **Any number it prints is unverified.** |
| **The watchdog against a genuinely stalled drive** | `tests/stall.c` proves the *reporting* works when a read is outstanding. It does not prove a grinding drive is what leaves one outstanding. **That is the exact gap r2 fell into**, so it is named rather than glossed. |
| MMC sub-channel read | a real `Pregap source: sub-channel` success — §1 is the first, on one disc |
| raw-binary-BCD drive quirk end to end | |
| C2 error reporting | |
| `-f` offset autodetection | |
| damaged media / paranoia error correction | |
| CD-TEXT from a physical disc | different code path from the image parser |

---

## 11. Asks

Answers tagged **measured / read-from-source / unverified**, please.

- **H1 — r2's broken heartbeat (§0).** Does any code or stored record of yours
  treat the absence of `Still reading track` lines as evidence about a rip?
- **H2 — the `Duration:` defect (§5).** Do you store or render `Duration:` from
  historical logs? `Samples / 44100` repairs them without re-ripping. Do you want
  us to keep both fields, or is `Samples:` enough?
- **H3 — `catalog` → `catalognumber` (§8).** Standards-correct, breaking. Ship it
  in r4, or remap downstream and we leave it alone?
- **H4 — rule on 6a.** Is the track-3 re-read verdict from your own re-read, or
  inferred from AccurateRip? *(Outstanding since round 6b.)*
- **H5 — the two liveness lines (§4a).** Were you parsing either?
- **H6 — sample peak computed two ways (§8).** Would a *disagreement* between the
  two methods be useful as a reported fact — a line that appears only when they
  differ — or is one number enough? We lean toward reporting only the
  disagreement: agreement is the expected case, and a second always-present number
  is noise.
- **H7 — version and branch rules (§2, §A). Please push back.** Does
  `0.9.4-rc1+platterpus.3` parse in whatever version handling you have, or does
  the `+` break it? Does pinning a SHA rather than a tag cause you a problem? We
  changed this twice in one release and would rather find the third problem now
  than after you have pinned it.
- **H8 — the 45 paired EAC/XLD logs (§8).** Do you want anything from us on those,
  or is that squarely yours? Our reading of the ownership split says yours.
- **H9 — confirm gate 1 with a second disc (§1).** Ideally one whose pregap layout
  you know independently.
- **H10 — run `-x` once on the rig and send the line (§3).** The only way to find
  out whether the thresholds are right. An implausible number is our bug.
- **H11 — should we report the disc-image silence defect upstream?** Still
  unanswered from round 6b. It is upstream's bug and affects anyone ripping an
  image with 0.9.4-rc1. Our inclination is yes, with the measured table.
- **H12 — A7's forced-error corpus** remains the highest-value artifact you can
  send. It is now the only way to settle the `goto`-class strings, since the
  generator names every label honestly and refuses to guess which are fatal.
- **H13 — the upstream escape hatch.** Does "roll back to stock upstream" still
  need to work for you? Several r3 changes correct *upstream* behaviour — the
  `Duration:` defect is upstream's, the disc-image silence defect was upstream's —
  so stock upstream is now measurably worse on those points, not merely different.

Still open and not re-asked: `--dirty`, zero-byte FLAC handling, J7's tag-casing
ruling.

---

## 12. Please send a handshake file of your own

Rounds so far have been asymmetric: we send a full file, you send a verification
of it. That has worked, but it means we only learn about your side through the
lens of our own questions — and twice now that has hidden something.

Your file should carry, at minimum:

- **P1 — your pin.** Which commit of Platterpus verified against which commit of
  ours. Both SHAs.
- **P2 — verification results**, per claim, each tagged measured /
  read-from-source / unverified, **naming the artifact each one touched.** "I
  verified the list you sent me" is not "I verified your inventory"; both sides
  have made that exact substitution.
- **P3 — anything wrong in our output**, or **"nothing found" written out loud.**
- **P4 — what you need from us that we are not providing.** The section we most
  want and have never been given: fields you are inferring, guessing, or
  reconstructing because we do not report them. **If you are deriving anything
  that would require the disc to be in the drive to get right, it belongs on our
  side of the split and we should be measuring it at rip time.**
- **P5 — your instructions and alerts to us.** The reciprocal of this file. What
  must we never change without telling you? What breaks you silently? What would
  you like warning about *before* it ships? We have been the only side stating
  requirements, which cannot be right.
- **P6 — answers to H1–H13**, and **explicit pushback on §2 and §A** (H7). Do not
  simply accept the version scheme and the branch rules; we have changed them
  twice this release and would like them attacked before they set.

**Two protocol reminders, both of which have bitten before:**

- **A correction from us gets the same scrutiny as a claim from us.** Corrections
  arrive with social pressure to accept. Both sides have now applied one that was
  wrong. Reproduce before adopting — as we did with §5, where the obvious-looking
  alternative fix would have been wrong.
- **Separate the finding from the diagnosis; they fail independently.** §0 is a
  finding we are confident in *and* a diagnosis you should check yourself. Say
  plainly which half you accept.

---

## 13. Gates

1. **`Pregap source: sub-channel` on real media** — **provisionally closed**,
   pending H9's second disc.
2. **A cancelled rip on the rig**, proving `setvbuf` under podman.
3. **The read-liveness heartbeat firing on a real stall** — **the r2
   implementation is now known not to have worked (§0), and the diagnosis was
   ours, not a capture gap of yours.** The gate is *not* closed by the fix: it
   reopens against the new thread-based implementation and stays open until a real
   stall on the rig produces a `Still reading track N - the read for LSN L has not
   returned after Ts` line. **Please run the next rig rip with `-k 30` and watch
   stdout.**
4. **`-x` producing a real measurement** — ours, new, unverified.

---

## 14. Joint test plan — both applications updated, tested together

**The thing to avoid: testing cyanrip r3 against an old Platterpus, or a new
Platterpus against r2's logs, and recording either as verification.** Round 7
contains a retraction, a corrected measurement and a changed version string;
every one of those is invisible if only one side is updated.

### Step 0 — both sides state their build, before any test runs

Neither of us records a result until both are pinned. Put these in your file:

```
cyanrip      commit d5d12ec   version 0.9.4-rc1+platterpus.3
Platterpus   commit <yours>   version <yours>
```

If a test was run against anything else, say which — a result from a mismatched
pair is still useful, but it is a different claim and must not be filed as
"verified against r3".

### Step 1 — no drive needed. Do this first; it catches most breakage.

| # | test | what it proves | fails if |
|---|---|---|---|
| T1 | Build r3, `meson test -C build` | the tree you pinned is the tree that passes | not 20/20 |
| T2 | `./build/src/cyanrip --version` through your version detection | §2's `+platterpus.3` parses on your side | your parser chokes on `+`, or a test still asserts `== 0.9.4-rc1` |
| T3 | Feed `docs/golden-reference.log` (regenerated at this pin) to your parser | no logfile line changed — your parser should need **zero** changes | any field moves |
| T4 | Rip a fixture and parse the result end to end: `cyanrip -d tests/fixtures/pregap.cue -N -A -Q -s 0 -o flac -Z 2 -G -D out -F '{track}' -L ref -M sheet -P 0` | the full pipeline, both apps, no hardware | anything |
| T5 | **Repeat T4 with `-s 6`** and parse it | **the §5 `Duration:` fix.** `-s 0` cannot show this — T4 alone will pass on a build that still has the bug | `Duration:` disagrees with `Samples:`/44100 |
| T6 | Point your parser at an *old* r1/r2 log from a nonzero-offset rip | your §5 repair path | you render the stored `Duration:` rather than recomputing from `Samples:` |
| T7 | `cyanrip -d <image> -I -N -A -U -P 0 -x` | `-x` refuses on an image and says so; your renderer handles `Cache probe: not run (…)` | you render it as a measurement, or as a defeated cache |
| T8 | Your EAC-format renderer over T4's log | §6a and §6b | `Defeat audio cache : Yes` still appears from an unprobed `Cache model:` |

T5 and T6 are the two that a "looks fine" pass will miss. Please run them
explicitly rather than assuming T4 covered them.

### Step 2 — on the rig, one disc, both applications updated

| # | test | what it proves |
|---|---|---|
| T9 | Full rip with `-k 30`, capturing stdout | **gate 3.** If a stall occurs, `Still reading track N - the read for LSN L has not returned after Ts` must appear. r2 produced nothing here through two three-minute stalls. |
| T10 | Same rip, second disc with a known pregap layout | **gate 1** (§1, H9). One disc is one observation. |
| T11 | Same rip with `-x` added | **gate 4** (§3, H10). Send us the line *and* its `uncached read` figure. An implausible number is our bug, not your drive's. |
| T12 | Compare T9's `Duration:` against `Samples:`/44100 on a real disc | §5 on real media at the drive's real offset, rather than at a synthetic one |
| T13 | Cancel a rip mid-track | **gate 2** — `setvbuf` under podman, a partial log rather than an empty one |

T9, T11 and T13 can all be the *same rip* if you want one pass. T10 needs a
second disc by definition.

### Step 3 — what a green run does and does not entitle either of us to say

- 20/20 plus T1–T8 green means **the software agrees with itself on synthetic
  media**. It says nothing about `-x`'s numbers, the MMC sub-channel read, C2, `-f`,
  or damaged media. §10's "NOT proven" table is the list, and it does not shrink
  because a suite went green.
- T9 passing proves the heartbeat *reports* a stalled read. It does not prove a
  grinding drive is what leaves one outstanding — that inference is §0's
  diagnosis, which is still inference.
- **T9 not firing is only meaningful if a stall actually occurred.** If the rip
  runs clean, gate 3 stays open; that is "did not happen", not "happened and found
  nothing". Please report it that way.

---

## 15. Releases

**We are not releasing r3 while this round is open, and we ask you to hold too.**

We expect this to take more than one lap. r3 contains a retraction of a feature we
told you worked (§0), a corrected measurement that affects records you have
already stored (§5), a version scheme changed twice (§2), and a branch/tag rule
set you have never reviewed (§A). Any one of those is worth a round on its own.

When you are satisfied, roll your own version and release — and say in your file
which cyanrip pin that release is verified against, so the two are quotable
together. **Release the pair, not the halves:** a Platterpus release verified
only against r2 would ship with the §5 repair untested and the §2 version string
unhandled.

**A "no changes" file is a complete round. Silence is not.**

---

*Round 7 OPEN. Pin `d5d12ec`, version `0.9.4-rc1+platterpus.3`, fork release r3,
source anchor `8058479eb6459ba7`. Round 6's verification file is still
outstanding — send it with this one if it exists.*
