# CTDB: the audio CRC (KDD-16) and manual repair

Two parts, one subject. **Part 1** is the reference for the CTDB per-disc audio CRC as
Platterpus computes it, cited from code (`ctdb/crc.py`). **Part 2** is the power-user
how-to for repairing a rip by hand with CUETools or `ctdb-cli`. Part 2 was
`manual-ctdb-repair.md` until 2026-11-16, when the owner asked for the documents to be
combined (*"Do all 5"*); its text moved here unchanged, its headings one level down.

## Part 1 — The CTDB audio CRC (KDD-16)


Reference for the CUETools Database (CTDB) per-disc audio CRC as Platterpus
computes it. Reconstructed clean-room from the **GPL-2.0-or-later** `CUETools.AccurateRip` /
`CUETools.Codecs` source (github.com/gchudov/cuetools.net) — the algorithm is a
*fact*, reimplemented here, not ported from the GPL `python-cuetoolsdb`.

> ✅ **Hardware-validation gate — PASSED (2026-07-07).** The algorithm below is
> source-grounded, reproduced in Python, and now **confirmed end-to-end on real
> hardware**: `platterpus --ctdb-calibrate` on an in-database disc reproduced a
> stored CTDB CRC at aligned `offset=+0` (see *Confirming on hardware* below), so
> `ctdb/crc.py::CRC_VALIDATED` is **True** — a CTDB `MATCH` now reads as
> *verified* and a `NO_MATCH` legitimately means the rip differs. The confirmed
> vector is baked as a regression fixture (`crc.CONFIRMED_VECTOR` +
> `tests/test_ctdb_verify.py::test_kdd16_confirmed_vector_trim`).

### The algorithm

`CTDBCRC(offset)` is a **standard IEEE / zlib CRC-32** (polynomial `0x04c11db7`,
reflected in/out, init/xor `0xffffffff` — exactly `zlib.crc32`) over the
**whole-disc little-endian 16-bit stereo PCM**, with a guard band trimmed off
each end so the value survives a small pressing/drive offset:

```
stride       = 10 * 588 * 2            # = 11760  (16-bit words; CUEToolsDB.Init)
laststride   = stride + (2 * total_frames) mod stride
front_frames = stride / 2              # = 5880   (fixed for every disc = 10 sectors)
back_frames  = laststride / 2          # length-dependent

CTDBCRC(offset) = zlib.crc32( pcm[ (front+offset)*4 : len - (back-offset)*4 ] )
```

- `total_frames` is the whole-disc audio length in stereo frames =
  `(leadout - 150) * 588` (lead-in removed), which for a real CD equals the
  concatenated decoded-FLAC frame count (tracks are sector-aligned).
- `offset` slides a **constant-length window** across the guard band
  (`front += offset; back -= offset`), tolerance **`±(stride/2 − 1) = ±5879`
  frames** — CueTools `CDRepair.FindOffset` sweeps `1 − stride/2 … stride/2`.
  This is DELIBERATELY WIDER than AccurateRip's ±2939 (`5·588 − 1`); real
  pressing offsets routinely exceed the AR window. `offset = 0` is the value
  stored in the database; a correctly-offset rip matches there.

#### Why the earlier attempts failed

Two separate off-by-a-constant bugs, both since fixed (verified against the
CueTools C# source):

1. **Trim (v0.4.16 placeholder).** It computed a plain `zlib.crc32` of the
   **untrimmed** disc (trim `(0,0)`). The CRC polynomial was always right — the
   trim was wrong. The real trim is asymmetric: `front=5880` fixed, back length-dependent
   (`laststride/2` — 9996 for the Police disc's 157,999,716 frames); v0.4.17 fixed this.
2. **Offset range (v0.4.17).** The trim was now correct, but calibration swept
   only AccurateRip's **±2939**. CTDB matches over **±5879**; a pressing aligned
   in (2939, 5879] was never reached, so a genuinely-good in-database disc still
   reported `NO_MATCH`. v0.4.18 widened the sweep to the CTDB range. The
   CRC/trim/combine were confirmed bit-for-bit correct.

### How Platterpus uses it

- **Verify** (`ctdb/verify.py`, since 2026-10-21 through `ctdb/sweep.py`):
  one pass over the decoded tracks, one track resident at a time (#39), measures
  `CTDBCRC(o)` for every `o` in ±5879 and every track's CRC over the same range,
  with the windows read from the TOC. `CTDBCRC(0)` from that pass equals
  `crc.ctdb_crc_offset0_streaming` (`tests/test_ctdb_sweep.py`). An entry matched
  at any offset is a match, and the result names the offset (TASKS R43).

#### The per-track CRC (`trackcrcs`)

Each entry also carries one CRC per track. CUETools computes it as
`AccurateRipVerify.CTDBCRC(iTrack, oi, stride/2, laststride/2)` (GPL-2.0-or-later,
`CUETools.AccurateRip/AccurateRip.cs`, called from `CDRepairEncode.TrackCRC`
in `CDRepair.cs`): the same zlib CRC-32 over the track's PCM, where **track 1
starts `stride/2` frames in and the last track stops `laststride/2` frames
before the lead-out**, the whole-disc trims, and every other track is whole. So a
middle track's value is the plain CRC-32 of the track, EAC's "Copy CRC" with null
samples counted. That half is measured, not only read: the live CTDB answer for
the reference disc (`tests/fixtures/ctdb_lookup_police_classics.xml`) holds EAC's
Copy CRCs for its middle tracks (`tests/test_ctdb_per_track.py`). The first and
last track's trims rest on the source and on the whole-disc vector below, which
uses the same two trims.

How the per-track values are compared (an entry's offset, ±2939, the summed
confidence) is CUETools' `CUEToolsDB.GenerateLog`, implemented in
`ctdb/matching.py`; its docstring says where ours differs (the entry's offset
for per-track matching comes from the consensus of its tracks). Where a track
differs, the entry's parity locates the samples (`ctdb/localise.py`, TASKS R43),
and the corrections must reproduce the entry's whole-disc CRC above, with the
same window, or nothing is located.
- **Calibrate** (`ctdb/calibrate.py`, `platterpus --ctdb-calibrate`): sweeps the
  full ±5879 offset window and reports which offset reproduces a DB CRC. Uses the
  zlib `crc32_combine` (GF(2) "append N zero bytes") operator so the whole sweep
  is a few big CRC passes plus cheap algebra, not ~11 759 re-CRCs of a ~600 MB disc.
  A match at `offset 0` means the rip's read offset aligns with that pressing; a
  match at `±k` means it differs by `k` samples (still a valid verify).

### Confirming on hardware — done

Confirmed 2026-07-07 (Platterpus build `f50258c`). Running
`platterpus --ctdb-calibrate "<album folder>"` on *The Police — Every Breath You
Take: The Classics* (14 tracks, Pioneer BDR-209D, read offset +667) reported:

```
Decoded whole-disc PCM: 631998864 bytes = 157999716 stereo frames.
Trim (offset 0): front=5880 back=9996 frames.
✅ MATCH — the CTDB-CRC algorithm is confirmed:
   offset=+0 → CRC 5da89fcd (confidence 1) (aligned — read offset matches this pressing)
```

Our offset-0 CRC reproduced a CTDB-stored value bit-exactly — an aligned
`offset=+0` match — which confirms the trim + polynomial + offset window against
the database. (It matched a confidence-1 pressing rather than the dominant
confidence-1350 one; that only means this physical disc is a less-common
pressing — it doesn't affect *algorithm* correctness, which is all the gate
tests.) The vector `(total_frames, front, back, offset, crc) =
(157_999_716, 5880, 9996, 0, 0x5DA89FCD)` is recorded as `crc.CONFIRMED_VECTOR`
and pinned by `tests/test_ctdb_verify.py::test_kdd16_confirmed_vector_trim`.

To re-confirm (e.g. after any change to the trim/offset math), re-run the same
command on any in-CTDB disc and expect a `✅ MATCH` at `offset=+0`.

## Part 2 — Manual CTDB repair — the power-user escape hatch (CUETools / `ctdb-cli`)

**Status:** how-to (2026-07-21). This is the manual repair workflow that
[`eac-parity.md`](eac-parity.md) has recommended documenting since
2026-06-28 — in Part C §2 (*In-app CUETools / CTDB repair*) and in
Part A's *P2(b)*. It is assembled **strictly from the
project's research record** — that doc plus the archived
[`archive/upstream-modification-investigation.md`](archive/upstream-modification-investigation.md)
— and **none of it has been executed on project hardware yet**: every claim we
have not proven ourselves is marked *(unverified)*. In-app repair remains
parked (KDD-14 Phase 2, decided 2026-07-21 as "D → B": nothing ships until a user
needs repair, and then `ctdb-cli` arrives as an optional user-installed tool,
never a bundled .NET; the repair path itself is still unvalidated); this page exists so a power user with a
stubborn disc isn't stuck waiting on that decision.

> **2026-11-04: Platterpus now repairs natively, in its core** (KDD-14 amended,
> TASKS R43): toward the strongest CTDB entry only, proved against the entry's
> CRCs before any file is replaced, with the original kept beside the repaired
> file. It has no button or script verb yet, so until it does this page remains
> the way for a user to repair a disc by hand.

### When to reach for this

Repair is the *last* resort, after the in-app remedies:

1. **Re-rip first.** A Track-3-class near-miss is often transient — the
   project's own baseline disc converged partial→exact on one re-read and
   regressed on another (read instability, now auto-detected by the re-rip
   comparison banner).
2. **Let `-Z` secure re-reads work.** Dynamic secure re-rip is on by default
   (Settings → "Extra matching reads to trust a track"); it re-reads
   AccurateRip-failing tracks until N+1 reads are identical.
3. **Check the verdict.** If a track *still* ends "partially accurate (450)"
   or AccurateRip-inaccurate across rips — and CTDB reports the disc with
   parity available — CTDB repair is the one mechanism that can *reconstruct*
   the bad samples instead of re-reading and hoping.

Matching only the offset-450 pressing variant means a **small number of
samples differ from the AccurateRip consensus** — exactly the case whole-disc
parity can correct. A disc that is simply not in CTDB (the verify verdict says
so) cannot be repaired this way at all.

### What repair does

CTDB stores whole-disc **parity** (~180 KB per disc). For a rip that is a
near-miss — a handful of wrong samples — the parity record can reconstruct the
correct samples and bring the rip back to the community consensus,
mathematically, without re-reading the disc. It operates on the **whole disc**
(cue + all tracks), not a single file.

### The tools (both external, both unverified by this project)

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

### The workflow

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

### Safety rules (non-negotiable)

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

*Last updated for Platterpus v0.7.126.*
