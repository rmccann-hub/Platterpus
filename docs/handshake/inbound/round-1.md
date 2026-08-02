# Platterpus: Cancelled-Rip Data Loss — Fix Plan

Fixes for the defect where a fully-ripped, AccurateRip-verified track disappeared from every report Platterpus emitted.

Reference session: The Police, *Every Breath You Take: The Classics*, Platterpus 0.5.21 (build 57462f8), cyanrip 0.9.3, cancelled during track 4.

## Scope and confidence

I had the four output files from that session, not the Platterpus or cyanrip repositories. That splits this document into two confidence tiers.

**Grounded in evidence:**

- The root cause, proven against the real artifacts
- The parser and guard modules, which run and pass 27 tests against fixtures taken from the session
- Call-site module names, read from `debug.lines` in the JSON sidecar

**Needs confirming against your tree:**

- Exact function names and line numbers at each call site
- Everything in the cyanrip fork section, including whether a fork is warranted at all
- Your existing test layout and fixture conventions

## Root cause

cyanrip writes its logfile through a block-buffered stdio handle. The buffer is only flushed when the process exits cleanly. Platterpus reads that logfile *before* the process has exited, and then kills it.

From `debug.lines`:

```text
19:01:32.612  track 3 Summary emitted (CRC 59D352DD, AccurateRip v2 conf 200)
19:02:08.215  rip cancel requested; arming the 5s force-stop rescue
19:02:08.220  rip finished: success=False
19:02:08.230  wrote EAC-layout companion log        <-- reads the file here
19:02:12.571  fuser -k /dev/sr0  ->  killed=True    <-- cyanrip dies here
```

The read happens 4.3 seconds before the writer exits. The on-disk log is exactly 4096 bytes and ends mid-token at `REPLAYGAIN_TRACK_GA` — one unflushed stdio block.

Consequences, all from this single cause:

- Track 3 absent from `tracks[]`, from the EAC-compatible log, and from the verdict
- `tracks[1].filename` null
- `tracks[1].replaygain` null
- Verdict claims 12 tracks were never ripped when the true figure is 11

The information was never actually lost. Platterpus captured all 982 stdout lines, including track 3's complete summary. It just wasn't the source the report was built from.

## Fix 1 — Parse captured stdout, not the logfile (P1)

**Module:** `platterpus/adapters/cyanrip_stdout.py`

The captured stdout stream is complete even when the ripper is killed. Prefer it unconditionally; read the logfile only to detect truncation and to fall back when no stdout was captured.

```python
source = resolve_log_source(stdout_text, logfile_path)
tracks = parse_track_summaries(source.text)

if source.recovered_tracks:
    LOGGER.warning(
        "recovered %d track(s) missing from the ripper logfile: %s",
        len(source.recovered_tracks), source.recovered_tracks,
    )
```

One format difference matters. The logfile marks tracks with `Track N ripped and encoded successfully!`; stdout does not — it goes `Flushing encoders...` then straight to `Summary:`. The parser therefore keys track identity off the `track:` field inside the Metadata block, which both formats carry. A parser written against the logfile header will silently find zero tracks in stdout.

Surface `source.logfile_truncated` and `source.recovered_tracks` in the JSON sidecar. A rip that needed recovery should say so.

## Fix 2 — Terminate the ripper gracefully (P1)

`fuser -k` sends **SIGKILL** by default, which cannot be caught. This has a consequence worth stating plainly: **no signal handler inside cyanrip can ever fix this defect.** A fork that installs a SIGTERM flush handler will not help while Platterpus is issuing SIGKILL.

Replace the single force-kill with a graduated stop:

1. Send SIGTERM to the ripper process directly, by PID, rather than by device.
2. Wait up to about 3 seconds for exit.
3. Only then escalate to `fuser -k` as the drive-release rescue.
4. Read the logfile after the process has exited, not before.

Confirm the default signal on your system with `fuser --help`. Even with Fix 1 in place this is worth doing, because it is what lets the ripper finish writing its own artifacts, including the CUE sheet.

## Fix 3 — Discard empty sidecars (P1)

**Module:** `platterpus/report_integrity.py`, `discard_empty_sidecars()`

The session left a zero-byte `.cue`. That is worse than no file: consumers see it, assume it describes the rip, and fail on parse. Call this on the output directory after any non-successful rip.

## Fix 4 — Do not claim "All tracks accurately ripped" on a partial rip (P2)

**Module:** `platterpus/report_integrity.py`, `format_accuraterip_footer()`

The current log opens with a prominent incomplete-rip banner and closes with an unqualified all-clear. EAC's wording means "all tracks in this session", but under that banner it reads as a verdict over tracks that were never extracted.

Complete rips keep EAC's exact wording, so genuine logs stay comparable. Partial rips get scoped wording instead:

```text
 2 track(s) accurately ripped
All 2 ripped track(s) accurately ripped (12 disc track(s) never extracted)
```

## Fix 5 — Null the cancel-invalid derived metrics (P3)

**Module:** `platterpus/report_integrity.py`, `compute_timing()` and `eta_trace_is_scorable()`

Two fields are computed as though every rip completes, so a cancelled rip yields a plausible wrong number instead of an honest null.

`realtime_multiplier` reported `0.21`, which is `755 / 3582` — elapsed over disc length. That is only a rate if the whole disc was ripped. Actual throughput was about 0.93x.

`actual_remaining_seconds` in `eta_trace` is `finish - sample_time`, where `finish` is the cancellation moment. On a cancelled rip it measures time-until-the-user-pressed-stop, not time remaining.

That second one is worth care, because the obvious reading of the trace is wrong. The final sample shows `our_eta_seconds: 3120` against `actual_remaining_seconds: 1`, which looks like a catastrophic estimator failure. It is not. Tracks 1 through 3 are 49,920 sectors, or 666 seconds of audio, plus roughly 35 seconds of track 4 — about 700 seconds ripped in 754 seconds of wall clock, or 1.08x realtime at paranoia max. Extrapolated across the full 3,582-second disc that is about 3,860 seconds, or 64 minutes. The steady-state estimate of 3,900 seconds was accurate to within a minute.

**The ETA is working.** Gate the comparison columns behind `completed` so the trace cannot mislead a future debugging session into fixing an estimator that is already correct.

## Wiring

Call sites, named from your own debug output. Line numbers need confirming.

| Module | Change |
|--------|--------|
| `platterpus.ui.main_window_rip` | Build reports from `resolve_log_source()`; move the log read to after process exit; call `discard_empty_sidecars()` on cancel |
| `platterpus.workers.rip_worker` | Ensure the full stdout capture is handed to the report builder, not just streamed to the debug log |
| `platterpus.adapters.cyanrip_backend` | Graduated SIGTERM before the `fuser -k` rescue |
| `platterpus.drive_control` | Accept a signal parameter on `force_stop_drive()`; keep SIGKILL as escalation only |
| EAC log writer | Use `format_accuraterip_footer()` |
| JSON sidecar builder | Use `compute_timing()`; add `log_source` and `recovered_tracks`; bump `schema_version` to 12 |

Adding `log_source: {origin, logfile_truncated, recovered_tracks}` to the sidecar is the change I would prioritise after Fix 1. It makes this class of defect self-reporting rather than silent.

## The cyanrip fork

**Start here: you probably do not need one.**

Fix 1 removes Platterpus's dependence on the logfile entirely. Once reports are built from captured stdout, cyanrip's buffering stops mattering to you. A fork is defense-in-depth for *other* consumers of those logfiles, and a reasonable upstream contribution, but it is not on the critical path.

Two further reasons to be cautious:

- SIGKILL is uncatchable, so the fork cannot fix the defect on its own. Fix 2 is a prerequisite for any cyanrip-side change to have effect.
- `stdbuf -oL` will **not** work here. It adjusts stdout and stderr only; the logfile is a separate `FILE*` opened inside cyanrip, so `stdbuf` never touches it. Skip that shortcut.

### What the patch needs to do

Upstream is `cyanreg/cyanrip` — C, meson build, LGPL 2.1+, logging in `src/cyanrip_log.c` and `src/cyanrip_log.h` with a `cyanrip_log(ctx, level, fmt, ...)` entry point. You are on 0.9.3; 0.9.3.1 is the current tag and is worth rebasing onto first.

Either approach works; the first is smaller.

**Option A — line-buffer the logfile.** Immediately after the logfile is opened, before anything is written:

```c
/* Line-buffer the logfile so a killed process cannot lose completed track
   records. CD ripping is I/O-bound on the drive; the extra write syscalls
   are irrelevant next to a 1x-speed read. */
setvbuf(ctx->logfile, NULL, _IOLBF, 0);
```

**Option B — flush at each track boundary.** After the per-track summary is written:

```c
fflush(ctx->logfile);
```

Option A is one line and covers every write path. Option B bounds loss to at most one track but leaves partial records possible mid-block. I would take A.

The exact `FILE*` member name is the part I cannot confirm without the source. Find it with:

```bash
git clone https://github.com/cyanreg/cyanrip.git
cd cyanrip
grep -rn "fopen\|logfile\|log_file" src/cyanrip_log.c src/cyanrip_log.h
```

### Build and install

```bash
git checkout -b fix/logfile-line-buffering v0.9.3.1
# apply the setvbuf change
meson setup build --prefix="$HOME/.local"
ninja -C build
ninja -C build install          # lands in ~/.local/bin/cyanrip
cyanrip --version
```

That path matches the binary Platterpus already probes.

### Pointing Platterpus at the branch

Platterpus resolves cyanrip via a dependency probe and reported `/home/rmccann/.local/bin/cyanrip` with `min_version_met: true`. Installing to the same prefix means the probe picks up the fork with no config change — which is convenient but makes it invisible which build is in use.

Make it explicit instead:

- Add a `rip_backend.cyanrip_path` setting so the binary is chosen deliberately rather than by `PATH` order.
- Record the resolved path and `cyanrip --version` output in the JSON sidecar, which you already do under `environment.dependencies.cyanrip`.
- If the fork reports a version string identical to upstream, add a build marker so logs distinguish them. A fork that is indistinguishable from upstream in the provenance record undercuts the point of the tool.
- Note that `install_channel` was `appimage` for this session. If the AppImage bundles its own cyanrip, a `~/.local/bin` install may not be what actually runs. Verify before concluding the fork is active.

## Test plan

### Automated

`tests/test_cyanrip_stdout.py` — 27 tests, passing. Fixtures are the real artifacts from the cancelled session, so the suite reproduces the actual defect rather than a synthetic approximation.

| Group | Covers |
|-------|--------|
| `TestTruncationDetection` | 4096-byte boundary heuristic; complete and empty files not flagged |
| `TestParsing` | All 3 tracks from stdout; only 2 from the truncated log; track 3 CRC, filename, and AccurateRip confidence; track 2 filename and ReplayGain recovery; partial blocks skipped rather than half-populated |
| `TestSourceResolution` | stdout preferred; `recovered_tracks == (3,)`; logfile fallback; raises when nothing is available |
| `TestAccurateRipFooter` | No all-clear on partial rips; EAC wording preserved on complete rips; rejects impossible counts |
| `TestTiming` | Cancelled rips yield no rate; partial rips use audio actually ripped; ETA trace unscorable on cancel |
| `TestEmptySidecars` | Zero-byte cue removed; populated cue kept; other empty files untouched |

The load-bearing assertion is `test_truncated_logfile_loses_a_track`. It asserts the *old* broken behaviour against the real 4096-byte artifact, so if a future change makes the fixture stop reproducing the defect, the suite says so instead of passing vacuously.

Run:

```bash
python -m pytest tests/test_cyanrip_stdout.py -v
```

### Manual

Regression check, roughly 3 minutes:

1. Start a rip of any 10+ track disc.
2. Cancel during track 4, once tracks 1 through 3 have completed.
3. Confirm the EAC log lists **3** tracks and the banner reads "3 of N".
4. Confirm `tracks[]` has 3 entries, each with a non-null `filename` and `replaygain`.
5. Confirm no zero-byte `.cue` remains in the output directory.
6. Confirm the footer does not read "All tracks accurately ripped".
7. Confirm `realtime_multiplier` is null or plausible, never the disc fraction.

Then the cases the fixtures cannot cover:

- **Cancel during track 1**, before any summary exists. Expect zero tracks, a clean report, no crash, no empty cue.
- **Complete a full rip.** Confirm the EAC footer still reads exactly "All tracks accurately ripped" so genuine logs remain comparable.
- **Cancel with the drive already ejected**, to exercise the termination path when the process is already gone.
- **A disc with a pregap or a data track**, since the parser's LSN handling was only exercised against a clean audio disc.
- **A title containing a colon**, which is what produced the `∶` (U+2236) substitution in paths. Confirm the display title and the path stay distinct.

### Unrelated finding

Track 2's title is `Can't Stand Losing You test`. The trailing ` test` reached the cyanrip command line, the FLAC tags, and the filename on disk. Presumably your own edit, but nothing in the pipeline questioned it. Worth checking your rips directory for a stray partial `04 - *.flac` from this session too.

## What I could not verify

- Exact call sites and line numbers in either repository
- Whether your fork of cyanrip already exists, and what it diverges on
- Your existing test layout, fixture conventions, and CI configuration
- The `FILE*` member name in cyanrip's logging context
- Whether the AppImage bundles its own cyanrip binary
- `fuser` default signal on your system, stated from psmisc documentation
