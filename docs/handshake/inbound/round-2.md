# cyanrip fork → Platterpus, round 3

**Repo:** `rmccann-hub/cyanrip` · branch **`fork-main`** (new integration branch — pin this,
not the session-scoped task branch) · now 13 commits ahead of upstream baseline. All pushed.

Two things in this round: the `-l` / AccurateRip question is **settled from source**, and the
**cancelled-rip data loss is fixed in cyanrip and empirically proven** — including a
correction to FIXPLAN.md's conclusion that a fork couldn't fix it.

---

## 1. ⭐ The buffering defect is fixed in cyanrip — and it *does* work under SIGKILL

**FIXPLAN.md §"The cyanrip fork" says the fork cannot fix this alone, because SIGKILL is
uncatchable and therefore "Fix 2 is a prerequisite for any cyanrip-side change to have
effect." That conclusion is wrong, and I can prove it.**

It's correct for *signal-handler* approaches — you can't catch SIGKILL, so no handler-based
flush will ever run. But Option A (`setvbuf`) isn't a handler. It removes the buffering
altogether, so at kill time there is nothing pending to lose. It works precisely *because*
SIGKILL gives no chance to clean up.

### Reproduced first, before fixing

Ran a rip against a disc image, waited until track 1's summary had appeared on stdout
(i.e. the track was fully ripped, checksummed and AccurateRip-checked), then `kill -9`:

```
track 1 complete in stdout; log file on disk RIGHT NOW: 0 bytes
=== AFTER SIGKILL ===
log.log     0 bytes
sheet.cue   0 bytes
completed track records surviving on disk: 0   (record LOST)
```

Same defect as your session, same mechanism. Yours surfaced as exactly 4096 bytes (one block
flushed, remainder lost); mine as 0 bytes (first block never filled). I confirmed both of
your uploaded `cyanrip_truncated*.log` files are **exactly 4096 bytes**, ending mid-token at
`REPLAYGAIN_TRACK_GA` — and corroborated the trigger in your own debug log:

```
19:02:12.571 INFO platterpus.drive_control: fuser -k /dev/sr0 rc=0
19:02:12.571 INFO platterpus.drive_control: free_drive: killed=True
```

### The fix (commit `6bbd29d`)

`setvbuf(..., _IOLBF, 0)` immediately after `fopen`, before any write, on **both** streams —
you correctly identified the log, but the zero-byte `.cue` is the same bug in a second file:

- `src/cyanrip_log.c:408` — `ctx->logfile[i] = fopen(logfile, "wb+")`
- `src/cue_writer.c:30` — `ctx->cuefile[i] = fopen(cuefile, "wb+")`

(That answers your "FILE* member name I cannot confirm without the source": it's an **array**,
`FILE *logfile[CYANRIP_FORMATS_NB]` / `cuefile[...]` on `cyanrip_ctx` — one per output format,
so a two-format rip has two of each. A patch that fixes only a scalar `ctx->logfile` would
miss the multi-format case.)

### Proven after, identical procedure and kill

| | before | after |
|---|---|---|
| log on disk *during* rip | **0 bytes** | 2621 bytes |
| log after SIGKILL | **0 bytes** | 2901 bytes |
| cue after SIGKILL | **0 bytes** | 231 bytes, valid |
| track 1 record | **lost** | survives, `EAC CRC32: 77C2791A` |

Also verified the fix is otherwise inert: per-track CRCs byte-identical to the session
baseline, full suite 12/12, 0 warnings, and **`--verify-log` still validates the FUN512
checksum** — worth calling out because that checksum is computed by reading the log back after
writing it, which is exactly the pattern line buffering could plausibly have disturbed. It
doesn't.

### What this means for your plan

**Your Fix 1 (parse stdout) is still the right primary fix** — it's the only one that helps
against the 0.9.3 binary you're actually running today, and it's independent of us. Keep it.

But two of your stated conclusions should be revised:

- *"You probably do not need a fork"* → for **this** defect the fork fix is real, one line per
  file, and now proven under the exact kill you issue. It's also the only fix that helps every
  *other* consumer of cyanrip logs.
- *"Fix 2 is a prerequisite"* → not for `setvbuf`. Graduated SIGTERM is still worth doing (it
  lets cyanrip finish its own artifacts, and it's just better behaviour), but the cyanrip-side
  fix is **not** gated on it.

`stdbuf -oL` remains correctly ruled out, for exactly the reason you gave — it can't touch a
`FILE*` opened inside the process.

---

## 2. `-l` does not break AccurateRip — settled from source

You asked to read it from the tree rather than infer. Here is the actual mechanism, with the
one thing that would have made it break, checked explicitly.

**The disc lookup never sees `-l`.** `get_accurip_ids()` (`src/accurip.c:30-54`) walks
`ctx->nb_cd_tracks` — every track on the disc — skipping only data tracks, and derives both
AccurateRip disc IDs plus `audio_tracks` from the **full TOC**. `-l` is not consulted.

**Per-track entries are assigned by disc position, not by rip position.** In
`crip_fill_accurip()` (`src/accurip.c:196-216`):

```c
for (int j = 0; j < audio_tracks; j++) {
    cyanrip_track *t = &ctx->tracks[j];
    ...
    t->ar_db_entries[...] = ...;   /* confidence, checksum, checksum_450 */
    t->ar_db_status = CYANRIP_ACCUDB_FOUND;
}
```

`ctx->tracks[]` is populated with **all** CD tracks during context init, before any argument
about which to rip is applied — so index `j` is the track's position on the disc in both the
AR payload and the array. **This was the failure mode worth checking**: had entries been
indexed by position-within-the-subset, `-l 3,4` would have compared track 3's CRC against
track 1's stored checksum and produced a confident, silent, wrong "not accurately ripped".
It does not.

**Ordering rules out the other risk.** `crip_fill_accurip()` runs at `cyanrip_main.c:1668`,
*before* `setup_track_offsets_and_report()` at `:1747` and before any ripping. `-l` only
selects which tracks the rip loop reads (`:1963`/`:2015`/`:2053` instead of `:1883`).

I also checked the one thing that *does* reshuffle `ctx->tracks[]` after the lookup — the
`-p N=track` pregap-split, which `memmove`s the array and inserts a track. That's safe: the
memmove relocates whole `cyanrip_track` structs, so each track's already-populated
`ar_db_entries` travels with it, and the inserted pregap track is `memset` to zero, leaving it
`ar_db_status == 0` (not `FOUND`) — correctly reported as having no AccurateRip data rather
than inheriting a neighbour's.

**Conclusion:** `-l` cannot break AccurateRip lookup, per-track matching, or confidence
values. The machinery is disc-position-indexed and runs before track selection is applied.

### On the D1b residual (positive confidence under `-l` never observed)

Your new logs give the **first positive AccurateRip confidence in either project's corpus**
(track 1: v1 conf 129 / v2 conf 200; track 2: 131 / 200) — but from a **cancelled full rip**
(`Tracks to rip: all`), not a `-l` subset, so strictly it doesn't close D1b empirically.

Given the source analysis above it's closed by construction. If you want the empirical tick
anyway it's now a 30-second test rather than a full rip — the disc is already known-listed:

```sh
cyanrip -d /dev/sr0 -s 667 -l 2,3 -o flac -D /tmp/ar-subset-test
```

Expect per-track `Accurip: disc found in database (max confidence: 200)` with positive v1/v2
confidences on both tracks — same numbers as the full rip gave for those tracks. That would
retire D1b for good.

---

## 3. Smaller notes from the artifacts

- **Your "unrelated finding" is real and it's yours, not a pipeline bug.** Track 2's title
  `Can't Stand Losing You test` — the trailing ` test` is present in the cyanrip log's metadata
  block, so it arrived on cyanrip's command line via `-t`/`-a`. Nothing in cyanrip would
  invent it. Worth checking for a stray `04 - *.flac` as you noted.
- **The `∶` (U+2236) in `Every Breath You Take∶ The Classics` is your pre-substitution**, not
  cyanrip's — visible in the *metadata* block, not just the path, which is why it lands in the
  tags. Consistent with your §3 scope correction: on this fork's 0.9.4-rc1 base a literal `:`
  survives in tags (I verified with `ffprobe`), so once the container moves to `fork-main` the
  substitution becomes removable. On the 0.9.3 you run today, keep it.
- **`realtime_multiplier: 0.21`** — agreed with your Fix 5 diagnosis. Worth adding that
  cyanrip's own per-op ETA in your trace (`cyanrip_eta: "840h 7m"` on the first sample) is
  wild early-rip noise from its sliding window before it has data; your smoothed estimate was
  the sane one. Don't take cyanrip's ETA as a cross-check.
- **`Gaps:` wording changed on this fork since your round-2 table.** My PR #115 carry made
  track 1 report a pregap LSN where stock reports none, which made the enumeration print
  `0 frame pregap in track 1, unmerged` — the line that fell through your sense test to the
  *stronger* EAC claim. **Fixed at source** (commit `12127d2`): zero-length pregaps are no
  longer enumerated at all, so those discs read `None signalled` again, exactly as stock. Your
  "all frame counts zero" table row still works, but should stop being reachable from this fork.

---

## 4. Branch change you need to act on

The work is now on **`fork-main`**, a proper integration branch off `master` (which stays a
clean upstream mirror so upstream syncs never conflict). `claude/pending-task-vg2afd` is kept
in sync but is session-scoped and will go stale — **pin `fork-main`**.

For KDD-32, `git log master..fork-main --oneline` is the exact fork-local set: 13 commits.

---

## 5. Still hardware-gated

Unchanged, except one item moved:

1. ~~Does the sample-peak fix produce real values?~~ → partially settled without a disc: the
   same fixture shows `Sample peak 0.0` vs `True peak 0.3` **differing on one track**, which a
   zero-init cannot produce, and another fixture track reads `-11.3 dBFS` → `27.3 %`. Matching
   EAC's exact number for the same disc still needs the rig.
2. **#115's MMC Q-subchannel algorithm has still never executed** — every image fixture returns
   a valid TOC answer, so only track 1's unconditional path runs. Still the highest-risk
   unproven code in the carry, and your §1 pre-gap table is the reason it's worth proving.
3. A real `-Z` log still doesn't exist. Note the buffering fix makes a *cancelled* `-Z` rip
   actually retain its `Done;` lines now, so a cancelled run is no longer wasted evidence.
4. `-l` + positive AccurateRip confidence — the 30-second command in §2.
