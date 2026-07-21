# Manual CTDB repair — the power-user escape hatch (CUETools / `ctdb-cli`)

**Status:** how-to (2026-07-21). This is the manual repair workflow that
[`eac-log-and-repair-feasibility.md`](eac-log-and-repair-feasibility.md) (Part B)
and [`eac-parity-investigation.md`](eac-parity-investigation.md) (P2b) have
recommended documenting since 2026-06-28. It is assembled **strictly from the
project's research record** — those two docs plus the archived
[`archive/upstream-modification-investigation.md`](archive/upstream-modification-investigation.md)
— and **none of it has been executed on project hardware yet**: every claim we
have not proven ourselves is marked *(unverified)*. In-app repair remains
parked (KDD-14 Phase 2 — blocked on maintainer appetite for the .NET dependency
and on repair-path validation); this page exists so a power user with a
stubborn disc isn't stuck waiting on that decision.

## When to reach for this

Repair is the *last* resort, after the in-app remedies:

1. **Re-rip first.** A Track-3-class near-miss is often transient — the
   project's own baseline disc converged partial→exact on one re-read and
   regressed on another (read instability, now auto-detected by the re-rip
   comparison banner).
2. **Let `-Z` secure re-reads work.** Dynamic secure re-rip is on by default
   (Settings → "Max reads to confirm a shaky track"); it re-reads
   AccurateRip-failing tracks until N reads agree.
3. **Check the verdict.** If a track *still* ends "partially accurate (450)"
   or AccurateRip-inaccurate across rips — and CTDB reports the disc with
   parity available — CTDB repair is the one mechanism that can *reconstruct*
   the bad samples instead of re-reading and hoping.

Matching only the offset-450 pressing variant means a **small number of
samples differ from the AccurateRip consensus** — exactly the case whole-disc
parity can correct. A disc that is simply not in CTDB (the verify verdict says
so) cannot be repaired this way at all.

## What repair does

CTDB stores whole-disc **parity** (~180 KB per disc). For a rip that is a
near-miss — a handful of wrong samples — the parity record can reconstruct the
correct samples and bring the rip back to the community consensus,
mathematically, without re-reading the disc. It operates on the **whole disc**
(cue + all tracks), not a single file.

## The tools (both external, both unverified by this project)

- **Route A — [`Masterisk-F/ctdb-cli`](https://github.com/Masterisk-F/ctdb-cli),
  headless.** A Linux-only CLI that does CTDB parity calculation, verify,
  **repair**, and upload from a CUE + WAV/FLAC. Requires the **.NET 10
  runtime** plus patched cuetools.net libraries (Freedb, TagLib#, UTF.Unknown);
  it builds with `./configure && make` but is C#/.NET underneath. Per its
  documentation the command shape is `ctdb-cli verify|repair <cue>` with
  `--xml` for parseable output, and repair writes its result as
  **`<cue>_repaired.wav`** *(all unverified — we have never built or run it)*.
- **Route B — CUETools under Mono, GUI.** The CUETools GUI (`CUETools.exe`)
  runs on Linux via Mono, reads/writes FLAC via its C# codec, and repair is a
  GUI action there *(unverified on our rigs; see the
  [cue.tools wiki](http://cue.tools/wiki/Command-line_Tools))*.

## The workflow

1. **Work on a copy.** Copy the whole album folder (audio + `.cue` + logs)
   somewhere else and run everything there. The originals — the FLAC archival
   master — stay untouched until the very end.
2. **Point the tool at the rip's cue sheet.** cyanrip writes `<Album>.cue`
   beside the tracks; both routes take the cue + audio as input. Run verify
   first (`ctdb-cli verify <cue>` *(unverified)*, or CUETools' verify) to
   confirm the disc is in CTDB, parity is available, and the tool sees the
   same near-miss Platterpus reported.
3. **Run repair.** `ctdb-cli repair <cue>` *(unverified)* or the CUETools GUI
   repair action. Route A's output is **one whole-disc WAV**
   (`<cue>_repaired.wav`) — no per-track split, no tags, no cover art.
4. **Fold the repaired audio back — the careful part.** The repaired WAV must
   be re-split by the cue sheet into per-track files, re-tagged, and have the
   cover art re-embedded (and any derived MP3/WavPack/WAV outputs
   re-transcoded from the repaired master). CUETools' conversion modes can
   reportedly split a cue+image into per-track files *(unverified)*; the
   exact mechanics are outside what this project has verified — whichever
   tool you use, the split must be sample-exact against the cue.
5. **Verify before you keep anything.** Re-check the repaired, re-split audio
   against CTDB before replacing the originals. Once the repaired tracks sit
   in an album folder as FLACs, `platterpus --ctdb-calibrate "<folder>"`
   recomputes the whole-disc CTDB CRC from the files and reports whether it
   matches a stored entry — that CRC path *is* hardware-validated (KDD-16).
   The external tools' own verify serves the same purpose *(unverified)*.
   Only after a clean verify do the repaired files replace the originals —
   and keeping the pre-repair originals anyway costs little.

## Safety rules (non-negotiable)

- **Repair rewrites audio — it is far higher-stakes than verify.** Verify can
  only under-claim; a repair gone wrong (a misalignment, a bad split) corrupts
  the master. Never run it in place, never delete the originals unverified.
- **Never trust the repaired output without a fresh verification pass** (step
  5). "The tool said repaired" is not the proof; the recomputed CRC matching
  the database is.
- These tools are **not** Platterpus dependencies: nothing in the app
  installs, invokes, or depends on them, and this page confers no support
  promise. If in-app repair ever ships (KDD-14 Phase 2), it will route through
  the dependency subsystem and its own validation first.

---

*Last updated for Platterpus v0.5.0.*
