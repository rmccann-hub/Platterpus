# Rip log format: cyanrip vs EAC

The brief promises "EAC-equivalent archival quality" — so the rip log should be a reasonable archival substitute for EAC's. This document compares the two formats field-by-field, identifies what each captures, and notes the small gaps.

**History:** this document originally compared *whipper* vs EAC. whipper was removed as a backend on 2026-06-30 (KDD-18) in favour of **cyanrip**, which is now the sole ripper. It was refreshed to cyanrip vs EAC in the post-0.4.5 session. The whipper comparison is preserved in git history if ever needed.

## Where the reference material lives

- `rip_log_eac_reference.log` (`tests/fixtures/`) — a representative EAC v1.6 log. Hand-authored to match the format documented on the Hydrogenaudio and CueTools wikis. **Not** used by the parser; stored for reference.
- cyanrip's exact format strings are pinned in the parser docstring and regexes at `src/platterpus/parsers/cyanrip_log.py`, verified against cyanrip master `src/cyanrip_log.c` (cyanrip 0.9.3.x). The parser tests (`tests/test_cyanrip_log*.py`) carry inline cyanrip log samples.

## Field-by-field comparison

### Archival header (drive + settings)

| Field | EAC | cyanrip | Notes |
|---|---|---|---|
| Tool version | `Exact Audio Copy V1.6 from 23. November 2020` | `cyanrip 0.9.3.1 (...)` | Both clearly identify the ripping tool + version. |
| Date | `EAC extraction logfile from 16. October 2023, 14:30` | `Ripping finished at 2026-06-09 12:34:56` | Both stamp the rip; cyanrip records the *finish* time (Platterpus adds the real elapsed + a realtime multiplier in the JSON report — cyanrip logs neither its own run time nor an ETA). |
| Drive identification | `Used drive  : PIONEER BD-RW BDR-209D   Adapter: 1  ID: 0` | `Device model:   PIONEER BD-RW   BDR-209D (revision 1.10)` | EAC includes adapter/ID; cyanrip includes firmware revision. **Roughly equivalent.** (cyanrip 0.9.3 prints `Device model:`; older builds printed `Drive used:` — the parser accepts both.) |
| Extraction engine | (implicit in EAC binary) | (implicit — cyanrip drives libcdio-paranoia) | cyanrip is built on FFmpeg + libcdio-paranoia; it doesn't print the engine versions in the log. Minor parity gap vs whipper (which named them). |
| Read mode | `Read mode : Secure` | (implicit — cyanrip always reads with paranoia) | EAC offers Burst mode; cyanrip doesn't. Not a gap for archival. |
| Read offset correction | `Read offset correction : 667` | `Offset:         +667 samples` | Equivalent. cyanrip applies the offset itself (no whipper >587 cd-paranoia bug), and prints the sign explicitly. |
| C2 pointers | `Make use of C2 pointers : No` | (not exposed) | Neither the Linux libcdio-paranoia stack nor the tested BDR-209D uses C2 — see `docs/ripper-engine-strategy.md §8`. Not actionable here. |
| Cache defeat | `Defeat audio cache : Yes/No` | (no equivalent line) | **No cyanrip equivalent.** cyanrip prints no cache line at all; libcdio-paranoia *attempts* cache defeat (readahead exhaustion + FUA where supported) but never asserts success. By design, our EAC-style log export renders this field `(unknown)` rather than a fabricated `Yes` — see PLANNING.md KDD-25. |
| Paranoia status counts | (not in EAC log) | `Paranoia status counts:` block (`SKIP: N`, `READ_ERROR: N`, …) | **cyanrip extra.** A per-status tally of how hard paranoia had to work — a useful marginal-disc signal EAC doesn't surface. |
| Disc audio duration | (implicit) | `Total time:     00:59:42.354` | cyanrip records the disc's audio length; Platterpus uses it for the honest realtime multiplier. |

### Per-track block

| Field | EAC | cyanrip | Notes |
|---|---|---|---|
| Track header | `Track  1` | `Track 5 ripped and encoded successfully!` | cyanrip opens the block with the outcome line. |
| Pre-emphasis flag | (not in EAC log) | `Preemphasis:   none detected` | cyanrip extra. Useful for archival pre-emphasis-encoded discs. |
| Duration | `... (per-track)` | `Duration:    03:51.44` | Both capture. |
| CRC | `Test CRC 0025D726` / `Copy CRC 0025D726` (two reads) | `EAC CRC32:     A1B2C3D4 (after 2 rips)` | **Different verification models.** EAC does a test read then a copy read and compares. cyanrip computes ONE EAC-style CRC32 per track and, with `-Z`, re-rips until N reads agree — it records how many rips it took. Platterpus stores cyanrip's single CRC in `copy_crc` and leaves `test_crc` empty, so the fidelity summary can tell the two models apart. |
| AccurateRip v1 result | `Accurately ripped (confidence 14)  [95E6A189]  (AR v1)` | `Accurip v1:  12345678 (accurately ripped, confidence 3)` | Both capture the CRC + confidence; the primary bit-perfection proof on both tools. |
| AccurateRip v2 result | `Accurately ripped (confidence 11)  [113FA733]  (AR v2)` | `Accurip v2:  9ABCDEF0 (not found, ...)` | Same structure as v1. |
| Offset-variant (450) match | (not distinctly labelled) | `Accurip 450: BF62B1DA (..., track is partially accurately ripped)` | **cyanrip extra.** The +450-frame offset-pressing variant — surfaced as an honest "partially accurate" match, not counted as a plain verified match. |
| Per-track loudness (ReplayGain / R128) | (not in EAC log) | `REPLAYGAIN_TRACK_GAIN: -4.10 dB` / `R128_TRACK_GAIN: 229` | **cyanrip extra**, written into the FLAC tags and captured in the report. |

### Summary / status report

| Field | EAC | cyanrip | Notes |
|---|---|---|---|
| Overall AccurateRip outcome | `All tracks accurately ripped` | `Tracks ripped accurately: 15/16` | cyanrip gives an explicit count; a partial-accurate line (`Tracks ripped partially accurately: N/M`) is separate. |
| Error summary | `No errors occurred` | `Ripping errors: 0` | Platterpus normalises cyanrip's "0 errors" to EAC's "No errors occurred" phrasing so downstream checks behave the same. |
| Album loudness | (not in EAC log) | `Album Loudness Summary:` block (`I: … LUFS`, `LRA: … LU`, `Peak: … dBFS`) | **cyanrip extra.** Whole-disc integrated loudness / range / true peak — a genuine archival bonus EAC has no equivalent for. |

### Log integrity

| Aspect | EAC | cyanrip | Notes |
|---|---|---|---|
| Footer | `==== Log checksum <HEX> ====` | `Log FUN512: <base64>` | Both tools sign their own log. EAC's checksum is a widely-recognised forensic signal in the archival community (its log-verify tool + CTDB accept "EAC-verified logs"); cyanrip's `Log FUN512:` is its own analogue but is **not** recognised by those third parties. Platterpus captures `Log FUN512:` in the report so the signature is preserved, but the third-party-recognition gap is real and **not actionable from the GUI side**. |

## What Platterpus adds beside the log

Platterpus never *rewrites* cyanrip's `.log`/`.cue` — those stay the EAC-parity, human-facing archival record, named after the album. It writes exactly **one** companion next to them:

- **`<Album>.platterpus.json`** — the single machine-readable / LLM-oriented rip report: the parsed verdict, per-track AccurateRip, the full post-rip verification suite (AccurateRip + CTDB + FLAC-integrity, plus derived-file verification for MP3/WavPack/WAV), per-file SHA256 digests, timing + realtime multiplier, album loudness, the read-speed-ladder history, **and this rip's embedded session log** (`debug.lines`, scoped to this album). It is the self-contained debug artifact — everything the application generated for this album's rip, in one file, re-verifiable later.

The album folder therefore holds only: the audio, the front cover, cyanrip's EAC-style `<Album>.log`/`<Album>.cue` (for humans), and the `<Album>.platterpus.json` (for machines/LLMs/debugging). There is **no** separate plain-text `.platterpus.log` sidecar — it would only duplicate cyanrip's human `.log` and the JSON's embedded `debug` block. The always-on global `~/.local/share/platterpus/log.txt` lives *outside* the album folder and is the cross-session catch-all for **program-level failures** (see `docs/architecture.md §3.7`).

## Verdict on EAC-equivalence

**Archival content: equivalent, and richer in places.** Every field EAC captures that bears on whether the rip is bit-perfect (drive, offset, per-track CRC, AccurateRip confidence v1+v2) is captured by cyanrip too. cyanrip *additionally* records paranoia status counts, pre-emphasis, per-track + album loudness (ReplayGain/R128), and the offset-variant match — none of which EAC logs.

**Log integrity: EAC is still stronger by reputation.** Both tools sign their logs, but EAC's checksum is a trusted forensic signal to third parties (CTDB, the audiophile community) in a way cyanrip's `Log FUN512:` is not. This is a real gap but not closable from the GUI side.

## Implications for the GUI

1. **The `RippingInfo` block on `RipLog` mirrors EAC's archival header** (drive/offset/etc.), so the GUI can surface it in a "Rip details" panel that gives the user EAC-level archival confidence — regardless of which tool wrote the log.
2. **The per-track display** renders cyanrip's AR v1 / v2 confidence the same way EAC does, and the results pane now also surfaces the album loudness + partial-accurate count that cyanrip uniquely provides.
3. **We don't export EAC-format logs.** No P0/P1 feature requires it, and Linux can't submit to AccurateRip anyway (the brief's confirmed quality gap). If ever needed it's a separate feature.

## How this was verified

- cyanrip format: pinned against cyanrip master `src/cyanrip_log.c` in the parser (`src/platterpus/parsers/cyanrip_log.py`); several fields (`Device model:`, the loudness block, `Log FUN512:`) were corrected from **real Pioneer BDR-209D rip logs** captured during 0.4.5 testing.
- EAC format: cross-referenced against the Hydrogenaudio Knowledgebase EAC article and CueTools' AccurateRip log parser documentation, both stable public references.

If a future cyanrip version changes its log format, update both this document and the cyanrip parser tests together.

---

*Last updated for Platterpus v0.4.17.*
