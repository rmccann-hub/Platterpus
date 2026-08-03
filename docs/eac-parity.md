# EAC parity — how close we are, and what is left

The single home for *"can Platterpus output stand in for an EAC rip?"*. Four investigations that each answered one part of that question, kept whole and put in one place: what deviates and why, whether a tracker would accept our log, how the two log formats compare field by field, and what the actual logcheckers deduct for.

**Read §1 first.** It carries the framing the other three assume — that *bit-identical audio* and *tracker-accepted log* are different goals with different answers, and conflating them is how this subject goes wrong.

## Where this came from

Consolidated from four separate documents so the subject has one home. Content is unchanged — each part below is the original file, whole, with its headings demoted one level.

**Parts are lettered, not numbered, on purpose:** the originals number their own sections from 0, so a numbered wrapper would make a reference like *§2.1* ambiguous. `Part A §8` reads exactly one way.

| Part | Was | Written |
|---|---|---|
| A | `docs/eac-parity.md` | 2026-06-27 |
| B | `docs/eac-parity.md` | 2026-06-30 |
| C | `docs/eac-parity.md` | 2026-06-28 |
| D | `docs/eac-parity.md` | 2026-07-29 |

---

## Part A — Can our output be bit-identical to EAC?

## EAC parity investigation — can Platterpus output be bit-identical to EAC?

**Status:** research + plan (2026-06-27). Triggered by the maintainer's goal:
*"this program needs to essentially output the exact same files, bit by bit, as
EAC."* This document marks every axis where our output can deviate from EAC,
says whether closing the gap is **possible**, and lays out a prioritized plan.

Evidence base: a real hardware rip of **The Police — *Every Breath You Take: The
Classics*** (cyanrip 0.9.3, Pioneer BDR-209D, +667 offset) compared against the
EAC V1.8 baseline of the same disc. Logs/cues live in
[`output_reference/`](../output_reference/) (`EAC_flac/` vs `cyanrip_flac/`).

### TL;DR — two very different goals

1. **Bit-identical *audio* (the PCM samples) — ACHIEVABLE, and ~90% there.**
   This is the real meaning of "archival/EAC-quality": the *samples* equal the
   AccurateRip consensus, proven by the per-track CRC. Our cyanrip rip already
   matched EAC **byte-for-byte on 12 of 14 tracks**, with an identical TOC and
   AccurateRip confidence 200. This is the goal worth chasing, and it's nearly
   met.

   > **Outcome (2026-07, added after later hardware runs):** the v0.4.13
   > re-rip reached **13/14** — Track 3 converged partial→exact on a re-read,
   > confirming P2(c)'s transient-near-miss prediction (see
   > `output_reference/cyanrip_mp3/README.md` and the v0.4.13 session-log
   > entry); Track 5 remains the disc's own defect. A still-later re-rip
   > regressed Track 3 again, refining the story to *read-instability on that
   > track* — now auto-detected by the v0.4.24 re-rip comparison. The `-Z`
   > hardware gate below is **answered** (a real `-Z` run produced per-track
   > convergence data, session-log 0.4.7), and P1 is **✅ done**
   > (`scripts/eac_parity.py` golden-tested; `tests/test_parity.py` pins the
   > committed 12/14 baseline; procedure + CRC table in `docs/test-plan.md`).
   > The committed-baseline analysis below is kept as the dated record.

2. **Bit-identical *files* (the `.flac`/`.cue`/`.log` byte-for-byte) — NOT
   ACHIEVABLE, and not the right target.** A FLAC file's bytes are *encoder-
   determined*: EAC pipes PCM to `flac.exe -8`; we use FFmpeg/libavcodec. Even
   with **identical PCM**, the two encoders choose different block sizes,
   prediction, stereo decorrelation, padding, seektable, and vendor string, so
   the `.flac` files never hash-match (Xiph FLAC format overview; Xiph FAQ). The
   `.cue`/`.log` are different tools' formats entirely. **This is expected and
   fine** — lossless means *same audio*, and the durable proof is the decoded-PCM
   CRC, never the file hash (exactly why Critical Rule #8 / `output_reference/`
   commit CRCs, not audio).

So we reframe the maintainer's goal to the one that is both meaningful and
attainable: **match EAC's extracted PCM (AccurateRip-verified), not EAC's file
bytes.**

### Deviation matrix (EAC ↔ our cyanrip output)

| Axis | EAC | Our cyanrip | Same? | Possible to close? |
|---|---|---|---|---|
| Read offset | +667 | +667 (`-s 667`) | ✅ identical | n/a |
| Drive / disc | BDR-209D | BDR-209D | ✅ | n/a |
| TOC (track sectors) | — | — | ✅ identical (all 14) | n/a |
| Secure / re-read | Secure | paranoia max | ✅ equivalent | n/a |
| Gap handling **audio** | append-to-previous | default merge-to-previous | ✅ (12/14 prove it) | n/a |
| Per-track **PCM** | baseline | 12/14 byte-identical | ⚠️ mostly | **Yes** — see T3/T5 |
| Overread lead-in/out | No | +2 frames, silence-fill | ⚠️ config differs | harmless here (T1/T14 matched); alignable |
| **Pre-gap markers in cue** (`INDEX 00`) | Yes (10/14) | **No** | ❌ deviates | **Hard** — see §Pregaps |
| FLAC **file bytes** | flac.exe `-8` | libavcodec | ❌ differ | **No** (encoder-determined) — and unnecessary |
| Tag **values** | EAC set | cyanrip set + colon-restore | ✅ matchable | minor work if needed |
| Tag/file **byte layout** | EAC | FFmpeg | ❌ differ | **No** — unnecessary |
| `.log` / `.cue` format | EAC | cyanrip | ❌ differ | **No** — different tools |
| Single-file disc image+cue | optional | **unsupported** | ❌ | needs another tool |

### The two audio tracks that differ (the only real audio gap)

- **Track 5 — a defect on this physical disc, not a ripper fault.** EAC *also*
  could not verify track 5 ("1 track could not be verified"); its CTDB pass says
  "differs in 3 samples @02:24:59." cyanrip rates it partially-accurate (offset-
  450). Both tools hit the same ~3 samples. **A tie; nothing to fix in software.**
- **Track 3 — a genuine near-miss.** EAC matched the main AccurateRip DB;
  cyanrip matched only the offset-450 *pressing-detector* CRC ("partially
  accurate") and applied 58 `FIXUP_ATOM` corrections. Per AccurateRip semantics,
  matching only the 450 variant means **a small number of differing samples** vs
  the consensus — a near-miss, not a quality grade. **Fixable** by (a) a re-rip
  (may be transient) or (b) CUETools/CTDB **Repair**, which uses whole-disc
  parity to correct small errors back to the consensus (needs the full disc).

### Pre-gaps in the cue (the "Detect Gaps" question) — why it's hard

EAC runs a **Detect Gaps** pass that reads the disc **subchannel** to find
index-00 pre-gaps, and records them as `INDEX 00` in its cue (10 of 14 tracks
here). Our cyanrip cue has none — every track is plain `INDEX 01 00:00:00`.

Findings:
- cyanrip's cue writer (`cue_writer.c`) **can** emit `INDEX 00`, but only when a
  track has a *merged pregap* recorded, and our rip's log says **"Gaps: None
  signalled"** / per-track **"Pregap LSN: none"** — i.e. cyanrip did **not detect
  the pre-gaps EAC found**. There is no evidence cyanrip reads the P-W subchannel
  for index detection the way EAC does (cyanrip issue #117 confirms INDEX-00
  emission exists but is pre-gap-gated; nothing about subchannel index scanning).
- Crucially, this is a **cue-metadata** gap, **not an audio** gap: both tools use
  append/merge-to-previous, so the pre-gap audio is already in the previous
  track's file the same way (that's *why* 12/14 PCM match). EAC merely *documents*
  the index points; cyanrip doesn't.
- It only matters for a **single-file disc image** or a **gapless re-burn** — not
  for tagged per-track FLACs, where the audio is already equivalent.

So writing EAC-style `INDEX 00` pre-gaps is **blocked on pre-gap detection**,
which cyanrip doesn't currently do on this path. Options are in the plan.

### Extraction-vector scorecard (vs. the 2026 landscape doc)

The maintainer's 2026 ripper-landscape research doc scores extraction tools
against a fuller list of vectors than the EAC-guide audit (KDD-13) covers.
Scoring Platterpus/cyanrip against that full list, one row per vector:

| Vector | Status | Rationale |
|---|---|---|
| Read offset | **Present + auto-confirmed (KDD-31)** | Per-drive offset applied via cyanrip `-s`; correct on the BDR-209D (+667), confirmed byte-identical on 12/14 tracks. A rip that matches the AccurateRip global consensus now records the offset as `ACCURATERIP_CONFIRMED` and promotes its provenance to CONFIRMED/HIGH on the user's own unit — the equal-or-stronger analogue of EAC's Key-Disc check (re-confirms every matching rip). A from-scratch finder for drives *absent* from the AR list is deferred to the soft-fork roadmap. |
| Cache defeat | **Measured (KDD-29)** | libcdio-paranoia attempts cache defeat every rip; cyanrip emits no verdict, so we **measure** it with `cd-paranoia -A` (libcdio's copy of that same engine) via Set up drive → Analyse cache, recorded per drive and folded into the EAC-compatible log. Still `(unknown)` (never forged) when the probe is inconclusive — the KDD-25 honesty rule holds. Hardware-tuned on the BDR-209D. |
| Overread (into lead-in/lead-out) | **Present (opt-in)** | Surfaced 2026-07-21 as the Settings "Overread" toggle → cyanrip `-O`, off by default (EAC's baseline setting is "overread: No", and that's how the 12/14 parity proof matched). Flag-letter corrected the same day: this row previously said `-x`, which does not exist in cyanrip — `-O` verified against 0.9.3.1 + master. |
| Subcode / pre-gap / `INDEX 00` | **Absent** | cyanrip performs no subchannel pre-gap detection on this path, so no `INDEX 00` cue metadata is emitted. The underlying *audio* is unaffected (append/merge-to-previous matches EAC) — this is a cue-metadata gap only. See "Pre-gaps" above. |
| HTOA (hidden track one audio) | **Absent — explicit scope note** | Not pursued: HTOA discs are rare in practice, and neither backend gives us a clean, low-effort path to it. Out of scope rather than a tracked gap; see `TASKS.md` "Out of scope." |
| Pre-emphasis | **Flag-only, intentionally unused** | cyanrip's `-E` (de-emphasis) flag exists but is deliberately not passed — Platterpus preserves pre-emphasis-encoded discs as-is (an archival choice: don't alter samples) rather than actively de-emphasizing. See `docs/dependency-contracts.md`. |
| AccurateRip v1/v2 | **Present** | Queried every rip; v1+v2 confidence parsed and rendered (KDD-12). |
| CTDB (whole-disc verify) | **Present, validated** | `ctdb/` clean-room client (KDD-16); GUI-wired; `crc.CRC_VALIDATED=True` since 2026-07-07 (a real disc's CRC reproduced at offset 0 on hardware), so a match reads "verified". |
| Log layout (side-by-side comparable) | **Present (2026-07-27)** | Checked against a genuine EAC V1.8 log of the same disc: the TOC table is byte-identical, and the archival header, output-format block and end-of-rip status report use EAC's rows and wording. Unreportable rows are labelled `(not reported by the ripper)`. Attribution + checksum stay deliberately distinct — layout is parity, provenance would be forgery. |
| Accuracy comparison from logs alone | **Present (2026-07-27)** | `parity.compare_logs` pairs all 14 tracks across a real EAC log and ours with no other input. The reference rip matches EAC on **13/14** tracks once the shipped (auto-fixed) read is reported. |
| Test & Copy (two full passes) | **Present via `-Z` convergence (KDD-30)** | No literal two-labeled-pass mode, but `-Z N` (re-rip until N reads' checksums agree) is the same two-reads-agree guarantee. A converged track renders as an EAC-style **Test CRC == Copy CRC** pair in the EAC-compatible log; the Settings toggle "Verify every track with a second read" runs it whole-disc. Single-read tracks show only a Copy CRC — never a fabricated test read. Includes tracks the per-track auto-fix re-read *after* the whole-disc log was written: the swapped-in read's own record — CRC, AccurateRip results, convergence — is folded over the first pass (`_apply_auto_fix_results`), so the pair describes the file on disk and not the discarded read, and convergence is claimed only when the converged copy was actually swapped in (both hardware-found 2026-07-26). |
| EAC log + checksum | **Present — our own checksum, not EAC's** | We render an EAC-*layout* log (`eac_log_export.py`) attributed to Platterpus/cyanrip, explicitly marked "not a genuine EAC log", and now footered with **our own integrity checksum: a plain SHA-256 of the text above it, equal-or-stronger than EAC's and openly verifiable** (`head -n -1 … \| sha256sum`) — never EAC's obfuscated *provenance* signature (KDD-28, refining KDD-11; open-trust choice KDD-24). |
| Gap handling | **Audio matches; no `INDEX 00`** | Same entry as "Subcode / pre-gap" above — audio placement is EAC-equivalent, cue metadata isn't. |

**Reading this table:** "present"/"partial" rows are real capability; "absent"
and "out-of-scope" rows are **deliberate**, not oversights discovered too
late — each links back to the KDD or doc that made the call. The one
genuinely load-bearing absence for *tracker* purposes (not audio purposes) is
covered separately in PLANNING.md **KDD-24**: none of the rows above matter
for tracker acceptance anyway, because that gate is ripper-identity, not
vector coverage.

### Plan (prioritized)

**P0 — Reframe + lock the achievable bar (docs only).**
Adopt "**AccurateRip/CRC-identical PCM**" as the parity definition (this doc).
Stop implying byte-identical files are a goal — they're impossible across
encoders and unnecessary. (No code.)

**P1 — Make parity measurable and routine.**
We already have `platterpus.parity` + `scripts/eac_parity.py` (compares per-track
Copy CRC, format-agnostic). Wire a documented step / optional check that runs the
candidate rip's log against the committed EAC baseline and reports the match
count — so "did this rip match EAC?" is one command. (Small; mostly done.)

**P2 — Close Track-3-class near-misses (the real audio gap).**
- (a) Add cyanrip **`-Z N`** ("re-rip until checksums match N times") as a
  secure-rip option for marginal discs — strengthens reads so a near-miss track
  converges to the consensus. **✅ Code landed 2026-06-28** (as the Settings
  control now named "Max reads to confirm a shaky track",
  `config.secure_rerip_matches` → cyanrip `-Z N`; dynamic secure re-rip is
  **on by default since v0.4.9** — no opt-in checkbox; the whipper grey-out
  clause is history, whipper was removed 2026-06-30, KDD-18). **⚠ HARDWARE-GATED:** confirmed
  to build the right argv and pass through the stack in tests, but its *effect*
  on a marginal disc — does a `-Z 2` rip actually converge Track-3-class
  near-misses to the AccurateRip consensus? — can only be proven on the
  BDR-209D rig with the real disc. Re-rip the Police disc with it on and re-run
  `scripts/eac_parity.py` against the EAC baseline to measure.
- (b) Document the **CUETools Repair** workflow as the authoritative fix for a
  "partially accurate (450)" track, and evaluate a future in-app CTDB-repair
  step (large; CTDB verify already exists, repair does not). Evaluated in
  [docs/eac-parity.md](eac-parity.md)
  (repair deferred; its CRC-validation gate cleared 2026-07-07). **✅ The
  manual workflow is written: [`manual-ctdb-repair.md`](manual-ctdb-repair.md)
  (2026-07-21).**
- (c) First, simply **re-rip track 3** to see if the near-miss was transient.

**P3 — Pre-gaps / `INDEX 00` in the cue (decision-gated).**
- (a) Hardware-test cyanrip's **`-p`** modes to see if any makes it record
  `INDEX 00` for this disc; if so, pass it and we get EAC-style pre-gap markers
  for free. **Syntax note (verified upstream):** `-p` is *per-track* —
  `-p track_number=action`, repeated for each track (actions:
  `default`/`merge`/`drop`/`track`); there is no global `-p default`, and a bare
  `-p default` aborts the rip (parsed as track 0). This is a **cue-metadata**
  experiment only: the *audio* placement already matches EAC under the default
  (§"Gap handling audio" above), so no `-p` mode changes audio parity — the
  question is purely whether one triggers `INDEX 00` emission.
- (b) If cyanrip won't detect subchannel pre-gaps, the only routes are a cyanrip
  feature request, the whipper/cdrdao path (cdrdao reads full TOC incl. gaps —
  but whipper is offset->587-buggy and cdrdao stalls on this BD drive), or
  generating the cue ourselves from a subchannel read we don't currently do.
  *(Superseded 2026-07-07: the researched answer lives in
  [docs/cyanrip-upstream.md](cyanrip-upstream.md) — support cyanrip
  **PR #115**, with a Platterpus-side `cdrdao read-toc` as the documented
  fallback; the whipper route no longer exists — KDD-18.)*
- (c) **Decision gate:** is `INDEX 00` worth it given the audio is already
  equivalent and per-track FLACs don't use it? Likely **only** pursue if we add a
  single-file-image output mode.

**P4 — Config alignment (minor).**
Optionally align overread to EAC's setting; expose it. Low value (audio matched).

**P5 — Single-file image + cue (future, large).**
EAC's image+cue mode isn't supported by cyanrip (one FILE per track, no image
mode). Would need a different tool or post-assembly. Only justified if users want
a burnable disc image; revisit with KDD-18 (ripper-engine strategy).

### Bottom line

- **Audio parity with EAC is achievable and 12/14 already met** — the path to
  14/14 is re-rip + CUETools-repair-class tooling for the marginal tracks (P2),
  not a format change.
- **File-byte identity with EAC is impossible across encoders and is the wrong
  goal** — lossless audio + AccurateRip CRC is the archival standard, and we meet
  it where the disc allows.
- **EAC-style pre-gap cue markers are a metadata nicety, currently blocked on
  cyanrip pre-gap detection**, and only matter for disc-image use (P3/P5).

---

## Part B — Log format, field by field: cyanrip vs EAC

## Rip log format: cyanrip vs EAC

The brief promises "EAC-equivalent archival quality" — so the rip log should be a reasonable archival substitute for EAC's. This document compares the two formats field-by-field, identifies what each captures, and notes the small gaps.

**History:** this document originally compared *whipper* vs EAC. whipper was removed as a backend on 2026-06-30 (KDD-18) in favour of **cyanrip**, which is now the sole ripper. It was refreshed to cyanrip vs EAC in the post-0.4.5 session. The whipper comparison is preserved in git history if ever needed.

### Where the reference material lives

- `rip_log_eac_reference.log` (`tests/fixtures/`) — a representative EAC v1.6 log. Hand-authored to match the format documented on the Hydrogenaudio and CueTools wikis. **Not** used by the parser; stored for reference.
- cyanrip's exact format strings are pinned in the parser docstring and regexes at `src/platterpus/parsers/cyanrip_log.py`, verified against cyanrip master `src/cyanrip_log.c` (cyanrip 0.9.3.x). The parser tests (`tests/test_parsers_cyanrip_log.py`, plus the never-raises property test in `tests/test_parsers_property.py`) carry inline cyanrip log samples.

### Field-by-field comparison

#### Archival header (drive + settings)

| Field | EAC | cyanrip | Notes |
|---|---|---|---|
| Tool version | `Exact Audio Copy V1.6 from 23. November 2020` | `cyanrip 0.9.3.1 (...)` | Both clearly identify the ripping tool + version. |
| Date | `EAC extraction logfile from 16. October 2023, 14:30` | `Ripping finished at 2026-06-09 12:34:56` | Both stamp the rip; cyanrip records the *finish* time (Platterpus adds the real elapsed + a realtime multiplier in the JSON report — cyanrip logs neither its own run time nor an ETA). |
| Drive identification | `Used drive  : PIONEER BD-RW BDR-209D   Adapter: 1  ID: 0` | `Device model:   PIONEER BD-RW   BDR-209D (revision 1.10)` | EAC includes adapter/ID; cyanrip includes firmware revision. **Roughly equivalent.** (cyanrip 0.9.3 prints `Device model:`; older builds printed `Drive used:` — the parser accepts both.) |
| Extraction engine | (implicit in EAC binary) | (implicit — cyanrip drives libcdio-paranoia) | cyanrip is built on FFmpeg + libcdio-paranoia; it doesn't print the engine versions in the log. Minor parity gap vs whipper (which named them). |
| Read mode | `Read mode : Secure` | (implicit — cyanrip always reads with paranoia) | EAC offers Burst mode; cyanrip doesn't. Not a gap for archival. |
| Read offset correction | `Read offset correction : 667` | `Offset:         +667 samples` | Equivalent. cyanrip applies the offset itself (no whipper >587 cd-paranoia bug), and prints the sign explicitly. |
| C2 pointers | `Make use of C2 pointers : No` | `C2 errors: <text> by drive` | **Parsed since v0.5.12** (`_C2` → `RippingInfo.c2_pointers`). Note the two lines ask different questions: cyanrip reports what the *drive can do*, EAC's row what the *rip did* — so `unsupported`/`disabled` renders a truthful `No` and an affirmative capability renders as unknown rather than a fabricated `Yes`. Per-sector C2 *counts* remain unexposed — see `docs/cyanrip-fork.md Part A §8`. |
| Gap detection | (not in EAC log) | `Gaps:` block | **cyanrip extra**, parsed to `RippingInfo.gap_detection`. |
| Per-track pre-gap | `Pre-gap length  0:00:02.00` | `Pregap LSN: N` | Parsed to `TrackResult.pregap_sectors` and rendered in the EAC-layout export. |
| Per-track sector range | (implicit in the TOC table) | `Start LSN:` / `End LSN:` | Parsed to `TrackResult.start_sector`/`end_sector`; they build the EAC-layout TOC table. |
| Cache defeat | `Defeat audio cache : Yes/No` | (no equivalent line) | **No cyanrip equivalent.** cyanrip prints no cache line at all; libcdio-paranoia *attempts* cache defeat (readahead exhaustion + FUA where supported) but never asserts success. Our EAC-style log export therefore renders `(unknown)` rather than a fabricated `Yes` — but the field is no longer *usually* unknown: **KDD-29** measures the drive's real cache-defeat behaviour with `cd-paranoia -A` and folds that verdict in, so a probed drive renders a measured `Yes`/`No` (hardware-confirmed `Yes` on the BDR-209D, 2026-07-26). KDD-25's "always unknown" position is superseded; the never-fabricate rule it was protecting is not. |
| Paranoia status counts | (not in EAC log) | `Paranoia status counts:` block (`SKIP: N`, `READ_ERROR: N`, …) | **cyanrip extra.** A per-status tally of how hard paranoia had to work — a useful marginal-disc signal EAC doesn't surface. |
| Disc audio duration | (implicit) | `Total time:     00:59:42.354` | cyanrip records the disc's audio length; Platterpus uses it for the honest realtime multiplier. |

#### Per-track block

| Field | EAC | cyanrip | Notes |
|---|---|---|---|
| Track header | `Track  1` | `Track 5 ripped and encoded successfully!` | cyanrip opens the block with the outcome line. |
| Pre-emphasis flag | (not in EAC log) | `Preemphasis:   none detected` | cyanrip extra. Useful for archival pre-emphasis-encoded discs. |
| Duration | `... (per-track)` | `Duration:    03:51.44` | Both capture. |
| CRC | `Test CRC 0025D726` / `Copy CRC 0025D726` (two reads) | `EAC CRC32:     A1B2C3D4 (after 2 rips)` | **Different verification models.** EAC does a test read then a copy read and compares. cyanrip computes ONE EAC-style CRC32 per track and, with `-Z`, re-rips until N reads agree — it records how many rips it took. Platterpus stores cyanrip's single CRC in `copy_crc` and leaves `test_crc` empty, so the fidelity summary can tell the two models apart. **In the EAC-compatible export** (KDD-30) a track whose reads *converged* is rendered as an EAC-style `Test CRC` == `Copy CRC` pair — convergence is the same two-reads-agree proof — while a track whose re-reads **disagreed** carries an explicit "not confirmed reproducible" caveat and a whole-disc `Read stability :` line. A never-re-read track keeps a lone `Copy CRC`: we neither fabricate a test read nor imply doubt we didn't measure. Note the CRC is always the **shipped** file's: cyanrip's whole-disc log records the first pass, so when the auto-fix swaps in a re-read, that track's record is replaced with the re-rip's own (matching the swap addendum cyanrip's log carries — hardware-found 2026-07-26). |
| AccurateRip v1 result | `Accurately ripped (confidence 14)  [95E6A189]  (AR v1)` | `Accurip v1:  12345678 (accurately ripped, confidence 3)` | Both capture the CRC + confidence; the primary bit-perfection proof on both tools. |
| AccurateRip v2 result | `Accurately ripped (confidence 11)  [113FA733]  (AR v2)` | `Accurip v2:  9ABCDEF0 (not found, ...)` | Same structure as v1. |
| Offset-variant (450) match | (not distinctly labelled) | `Accurip 450: BF62B1DA (..., track is partially accurately ripped)` | **cyanrip extra.** The +450-frame offset-pressing variant — surfaced as an honest "partially accurate" match, not counted as a plain verified match. |
| Per-track loudness (ReplayGain / R128) | (not in EAC log) | `REPLAYGAIN_TRACK_GAIN: -4.10 dB` / `R128_TRACK_GAIN: 229` | **cyanrip extra**, written into the FLAC tags and captured in the report. |

#### Summary / status report

| Field | EAC | cyanrip | Notes |
|---|---|---|---|
| Overall AccurateRip outcome | `All tracks accurately ripped` | `Tracks ripped accurately: 15/16` | cyanrip gives an explicit count; a partial-accurate line (`Tracks ripped partially accurately: N/M`) is separate. |
| Error summary | `No errors occurred` | `Ripping errors: 0` | Platterpus normalises cyanrip's "0 errors" to EAC's "No errors occurred" phrasing so downstream checks behave the same. |
| Album loudness | (not in EAC log) | `Album Loudness Summary:` block (`I: … LUFS`, `LRA: … LU`, `Peak: … dBFS`) | **cyanrip extra.** Whole-disc integrated loudness / range / true peak — a genuine archival bonus EAC has no equivalent for. |

#### Log integrity

| Aspect | EAC | cyanrip | Notes |
|---|---|---|---|
| Footer | `==== Log checksum <HEX> ====` | `Log FUN512: <base64>` | Both tools sign their own log. EAC's checksum is a widely-recognised forensic signal in the archival community (its log-verify tool + CTDB accept "EAC-verified logs"); cyanrip's `Log FUN512:` is its own analogue but is **not** recognised by those third parties. Platterpus captures `Log FUN512:` in the report so the signature is preserved, but the third-party-recognition gap is real and **not actionable from the GUI side**. |

### What Platterpus adds beside the log

Platterpus never *rewrites* cyanrip's `.log`/`.cue` — those stay the EAC-parity, human-facing archival record, named after the album. It writes exactly **one** companion next to them by default (a second, optional `<Album> (EAC-compatible).log` appears when the Settings toggle `write_eac_log_after_rip` is on — off by default; `eac_log_export.py`):

- **`<Album>.platterpus.json`** — the single machine-readable / LLM-oriented rip report: the parsed verdict, per-track AccurateRip, the full post-rip verification suite (AccurateRip + CTDB + FLAC-integrity, plus derived-file verification for MP3/WavPack/WAV), per-file SHA256 digests, timing + realtime multiplier, album loudness, the read-speed-ladder history, **and this rip's embedded session log** (`debug.lines`, scoped to this album).

The album folder therefore holds: the audio, the front cover, cyanrip's EAC-style `<Album>.log`/`<Album>.cue` (for humans), the `<Album>.platterpus.json` (for machines/LLMs/debugging), and — only when the toggle above is on — the optional `<Album> (EAC-compatible).log`. The *rationale* for this split — two audiences, two artifacts; why there is deliberately **no** plain-text `.platterpus.log` sidecar; how the global `~/.local/share/platterpus/log.txt` divides the work with the JSON's embedded log — is owned by [`architecture.md` §3.7](architecture.md) ("Two audiences, two artifacts"); this doc records only *what* sits beside the rip.

### Verdict on EAC-equivalence

**Archival content: equivalent, and richer in places.** Every field EAC captures that bears on whether the rip is bit-perfect (drive, offset, per-track CRC, AccurateRip confidence v1+v2) is captured by cyanrip too. cyanrip *additionally* records paranoia status counts, pre-emphasis, per-track + album loudness (ReplayGain/R128), and the offset-variant match — none of which EAC logs.

**Log integrity: EAC is still stronger by reputation.** Both tools sign their logs, but EAC's checksum is a trusted forensic signal to third parties (CTDB, the audiophile community) in a way cyanrip's `Log FUN512:` is not. This is a real gap but not closable from the GUI side.

### Implications for the GUI

1. **The `RippingInfo` block on `RipLog` mirrors EAC's archival header** (drive/offset/etc.), so the GUI can surface it in a "Rip details" panel that gives the user EAC-level archival confidence — regardless of which tool wrote the log.
2. **The per-track display** renders cyanrip's AR v1 / v2 confidence the same way EAC does, and the results pane now also surfaces the album loudness + partial-accurate count that cyanrip uniquely provides.
3. **We offer an optional EAC-*layout* companion log (v0.4.16)** — the Settings toggle `write_eac_log_after_rip` (off by default) writes `<Album> (EAC-compatible).log` beside the rip, rendered by `eac_log_export.py`: conspicuously attributed and **never signed** as EAC (signing would forge provenance — KDD-11/KDD-24, `docs/eac-parity.md`). Linux still can't submit to AccurateRip (the brief's confirmed gap).

### How this was verified

- cyanrip format: pinned against cyanrip master `src/cyanrip_log.c` in the parser (`src/platterpus/parsers/cyanrip_log.py`); several fields (`Device model:`, the loudness block, `Log FUN512:`) were corrected from **real Pioneer BDR-209D rip logs** captured during 0.4.5 testing.
- EAC format: cross-referenced against the Hydrogenaudio Knowledgebase EAC article and CueTools' AccurateRip log parser documentation, both stable public references.

If a future cyanrip version changes its log format, update both this document and the cyanrip parser tests together.

---

## Part C — Tracker acceptance, and in-app CTDB repair

## Feasibility: EAC-log tracker-acceptance & in-app CTDB repair

**Status:** research (2026-06-28) — **decided**: Part A resolved per **KDD-24**
(tracker acceptance out of scope by design; option 1 is the standing path,
option 2 shipped v0.4.16, option 3 documented-not-pursued; the signing path is
permanently closed — TASKS.md closed the signed-checksum item). Part B (repair)
remains deferred pending maintainer appetite for the .NET dependency; its CRC
gate cleared 2026-07-07 (KDD-16). Originally: research / decision-gated, no
code written. This is
the write-up the EAC-parity brief asked for ("investigate the LOG-trust path"
and "scope/evaluate an in-app CUETools/CTDB *repair*") so the maintainer can
decide before any implementation. It pairs with
[`eac-parity.md`](eac-parity.md) (the audio-parity
plan) and answers the two questions that investigation deferred.

---

### Part A — Can we make our rips *tracker-accepted* by emitting an EAC log?

#### The decisive finding (added 2026-07, research session): the block is ripper identity, above the audio layer

Before any of the checksum discussion below, there's a harder wall: the
gazelle logcheckers (OPSnet's/orpheusnet's PHP logchecker; RED's EAC/XLD +
Python `eac_logchecker` for the checksum) score a log by **which program
produced it**, not by whether the underlying audio is bit-perfect. Their
ripper allow-list is **EAC, XLD, and whipper ≥ 0.7.3** — full stop. An
unrecognized ripper, including **cyanrip**, is hard-set to score **0 /
rejected** before the checker ever looks at read quality, AccurateRip
confidence, or anything audio-related.

That matters for how to read everything below: there is **no honest partial
ceiling** to aim for. A cyanrip log with perfect AccurateRip confidence and a
flawless extraction still scores exactly the same as a garbage rip — zero —
because the gate is identity, not quality. "Get closer to tracker-accepted" is
not a spectrum we can climb by improving the rip; it's a binary allow-list we
are not on. This reframes Part A from "how close can we get" to "this is
categorically out of scope by design" — see PLANNING.md **KDD-24** for the
full record.

**Two corrections to the maintainer's 2026 ripper-landscape research doc**
surfaced while researching this — (1) whipper + `whipper-plugin-eaclogger`
does **not** genuinely satisfy RED (the plugin hits the same EAC-checksum
wall described below), and (2) the "logchecker-go (pure Go)" characterization
is unverified and not load-bearing (the verifiable fact is the scoring
mechanics). The full text of both corrections lives in PLANNING.md
**KDD-24** — the designated record.

#### The constraint

Gazelle trackers (RED/OPS) accept **only EAC or XLD logs** — plus whipper
≥ 0.7.3 at OPS. A cyanrip log — even with a valid AccurateRip result and
cyanrip's own FUN512 checksum — is **not** accepted.

> **Correction (2026-07-29):** an earlier version of this paragraph said whipper
> "still cannot clear RED's checksum requirement." That is wrong. OPS's checker
> validates whipper's checksum, which is a **plain SHA-256 of every line but the
> last** (`OPSnet/Logchecker`, `src/Check/Checksum/Whipper.php`) — the same scheme
> Platterpus's own footer uses. The checksum wall is cleared there; what excludes
> cyanrip is *identity*, checked before any quality line is read, and Redacted's
> rules listing only EAC and XLD is a policy limit rather than a technical one.
> Details and the full requirement-by-requirement comparison:
> [`eac-parity.md`](eac-parity.md). So "make the CD-archiving community fully trust our rips"
splits into two very different audiences:

- **AccurateRip + CTDB** = the *open*, tool-agnostic trust system. Anyone can
  verify our rip against the shared databases. We already meet this (and now
  surface it prominently — the verdict banner).
- **Gazelle log acceptance** = a *private, EAC-shaped* gate. It does not check
  "is the audio bit-perfect"; it checks "did **EAC/XLD** produce this log,
  ripping securely". That is a different claim entirely.

#### Is emitting a checksum-valid EAC log technically possible? **Yes.**

The EAC log checksum was reverse-engineered and is public and documented:

- **`puddly/eac_logsigner`** — MIT-licensed, **Python 3.7+** (fits our stack),
  verifies *and signs* EAC logs. ([github.com/puddly/eac_logsigner](https://github.com/puddly/eac_logsigner))
- **`OPSnet/eac_logchecker.py`** — a fork **maintained by the OPS tracker
  itself**, tuned to match the real EAC Logchecker.
  ([github.com/OPSnet/eac_logchecker.py](https://github.com/OPSnet/eac_logchecker.py),
  on PyPI as `eac-logchecker`)

The algorithm (from the signer's source): strip newlines + BOM, cut off any
existing signature block, re-encode the log text to **little-endian UTF-16**,
encrypt with **Rijndael-256** (variable block size, via `pprp`), and **XOR all
the 256-bit ciphertext blocks** together. The result is the signature appended
as `==== Log checksum <hex> ====`. So we *could* render an EAC-format log from a
real cyanrip rip and produce a checksum that the public logchecker accepts.

#### So why this is **NOT** the path — the honesty wall

**A signed "EAC" log is an attestation about the *tool and process*, not just
the audio.** The checksum is EAC's authenticity mark: it says "Exact Audio Copy
produced this log on this rip." Emitting that from cyanrip is **misrepresenting
which program did the rip** — i.e. a **forged log**, regardless of whether the
underlying audio is genuinely bit-perfect. Gazelle communities treat
third-party-signed EAC logs as **faked logs, and faking a log is a bannable
offence**. (The long-running debate at
[whipper-plugin-eaclogger#7](https://github.com/whipper-team/whipper-plugin-eaclogger/issues/7)
is exactly this: whipper *can* render EAC-shaped logs, but signing them to pass
as EAC is the line nobody legitimate crosses.)

That `eac_logsigner`'s README carries no ethics warning is irrelevant — the
**tracker rules**, not the tool, define the offence. And it collides head-on
with two of our own hard constraints:

- The brief: *"it must reflect REAL results — never fake a log/checksum."* An
  EAC-signed cyanrip log fakes the **provenance** even when the audio is real.
- The project ethos (see the honesty rules in `docs/ux-design-principles.md`
  and the verdict code in `ui/rip_progress.py`): *"never claim a check that
  didn't run."* We never ran EAC.

**Recommendation: do not forge EAC logs.** It is technically a few hundred lines
of Python and ethically a non-starter.

#### The honest options (for the maintainer to pick)

1. **(Recommended) Don't chase gazelle acceptance; double down on open trust.**
   AccurateRip v1/v2 + CTDB whole-disc verification + an honest, complete,
   *attributed* log (which we already produce) is the real, tamper-evident
   archival standard. This is "good everything" without pretending to be EAC.
2. **Emit an EAC-*format* log that is clearly attributed to Platterpus /
   cyanrip and *unsigned* (or signed with our own visible marker).** Useful for
   humans and for our own EAC-parity diffing (`scripts/eac_parity.py`), honest
   about its origin, and it simply *won't* be tracker-accepted — which is
   correct, because it isn't an EAC rip. Low effort, no forgery.
   **✅ The building block is now implemented** (`src/platterpus/eac_log_export.py`
   `render_eac_style_log()` + the `scripts/render_eac_log.py` CLI, 2026-06-28):
   it renders our real `RipLog` into EAC's layout with a conspicuous
   "generated by Platterpus — NOT a genuine EAC log / not signed" header and
   footer, never a fabricated checksum. The GUI wiring shipped in
   v0.4.16: the opt-in Settings toggle (*EAC-style log*,
   `write_eac_log_after_rip`, off by default) writes the attributed EAC-layout
   log beside each rip — option 2 is fully implemented.
3. **If tracker acceptance is genuinely required**, the only legitimate route is
   the *tracker* choosing to accept whipper/cyanrip (advocate upstream; OPS
   already maintains tooling in this space). We do not manufacture acceptance by
   signing. This is out of our hands by design.

**Decision gate — RESOLVED (KDD-24, 2026-07):** option **1** is the standing
path, option **2** shipped (v0.4.16 toggle), option **3** is documented, not
pursued. No code ever proceeds on the signing path.

---

### Part B — In-app CUETools / CTDB *repair*

#### What "repair" buys us

CTDB stores whole-disc **parity**, so for a rip that's a near-miss (a handful of
bad samples — the Track-3-class gap), CTDB can **reconstruct the correct
samples** and bring the track back to the consensus. We already do CTDB
**verify** (`src/platterpus/ctdb/`); **repair does not exist** in our code.

#### Is headless repair on Linux possible? **Yes, but heavy.**

- **`Masterisk-F/ctdb-cli`** — a **Linux-only** CLI that does CTDB parity calc,
  verify, **repair**, and upload from a CUE + WAV/FLAC. Repair writes
  `<cue>_repaired.wav`. **Needs the .NET 10.0 runtime** plus patched
  cuetools.net libs (Freedb, TagLib#, UTF.Unknown).
  ([github.com/Masterisk-F/ctdb-cli](https://github.com/Masterisk-F/ctdb-cli))
- **CUETools under Mono** — the GUI/`CUETools.exe` run on Linux via Mono and can
  read/write FLAC via its C# codec; repair is a GUI action.
  ([cue.tools wiki](http://cue.tools/wiki/Command-line_Tools))

#### Why it's deferred (not "no", but "not yet")

1. **New heavyweight runtime dependency** (.NET 10.0 or Mono + cuetools.net).
   That's a big addition for a single-file-AppImage app, routed through the dep
   self-management subsystem + a new adapter (Critical rules #1, #6). Must-ask
   territory (it's a new dependency) — the maintainer signs off first.
2. **Output shape mismatch.** `ctdb-cli` repair emits **one WAV** — no per-track
   split, no tags, no cover art. Folding that back into our per-track tagged
   FLAC master means re-split + re-tag + re-embed + re-transcode. Real work, and
   it touches the archival master, so it must be provably lossless.
3. **Repair rewrites audio — it is far higher-stakes than verify.** Our own CTDB
   verify CRC is now hardware-validated (KDD-16, `crc.CRC_VALIDATED` is True since
   2026-07-07); verify fails *safe* (can only under-claim), but **repair cannot** —
   a wrong alignment would corrupt the master, and repair exercises the *parity*
   path (`CUETools.Parity`), not just this verify CRC, so it still needs its own
   validation regardless of the dependency question.

#### Recommendation

- **Now:** ship the lighter first line of defence — **cyanrip `-Z N` re-rip**
  (done this session) converges most marginal tracks without any new dependency.
- **Document the manual CUETools/ctdb-cli repair workflow** as the authoritative
  fix for a stubborn "partially accurate (450)" track (a power-user escape
  hatch), pointing at the tools above. **✅ Written 2026-07-21:
  [`manual-ctdb-repair.md`](manual-ctdb-repair.md)** (assembled strictly from
  this doc + the investigation record; unexecuted steps marked unverified).
- **Gate an in-app repair** behind: (a) ~~the CTDB CRC hardware-validation~~
  **cleared 2026-07-07 (KDD-16)**, (b) explicit maintainer appetite for the
  .NET/Mono dependency, and (c) repair-specific validation of the
  CUETools.Parity path. Revisit alongside `docs/cyanrip-fork.md`
  (the living engine-options doc that revisits KDD-18) — if we ever bundle a
  richer engine, repair rides along more cheaply.

---

### Bottom line

- **EAC-log tracker acceptance:** technically trivial to *forge*, ethically and
  per-the-brief a hard **no** — and, per the ripper-identity finding above, not
  even reachable by degrees since the gate is binary allow-list, not audio
  quality. Trust the open path (AccurateRip + CTDB + honest attributed logs);
  optionally emit an *unsigned, attributed* EAC-format log for humans.
  **Decided per KDD-24 (option 1; 2 shipped; 3 not pursued).** This conclusion is **unchanged** by the
  ripper-identity finding — it's the same "don't forge, invest in open trust"
  answer, now with a sharper reason why closing the gap by degrees was never
  on the table.
- **Why we ship no two-pass Test&Copy, and why our log is unsigned — both are
  the open-trust choice, not gaps.** A literal EAC-style Test&Copy (two full
  disc passes, compared) and a signed EAC checksum are both *provenance/process
  attestations* — "this ran the way EAC runs" — not audio-correctness
  mechanisms. Given tracker acceptance is out of scope by design (KDD-24), we
  spend the equivalent effort on the open-trust primitives instead: `-Z N`
  secure-re-read convergence (a cheaper, single-engine analogue of Test&Copy's
  purpose) plus AccurateRip/CTDB consensus for correctness, and an honest
  **unsigned** attributed log for humans instead of a **signed** one that would
  misrepresent which tool ran. Building Test&Copy or a real signature would
  buy tracker-shaped credibility we've deliberately decided not to chase.
- **In-app CTDB repair:** feasible on Linux (`ctdb-cli`/.NET or CUETools/Mono)
  but a heavy dependency that rewrites the master. The CRC-validation blocker
  **cleared 2026-07-07 (v0.4.20, KDD-16)**; the remaining gates are maintainer
  appetite for the .NET dependency and validation of the repair path itself.
  `-Z N` shipped; the manual workflow is documented
  ([`manual-ctdb-repair.md`](manual-ctdb-repair.md), 2026-07-21); gate the
  integration behind maintainer sign-off + validation.

---

## Part D — Measured against the real logcheckers

## EAC vs. Platterpus, measured against tracker logcheckers (2026-07-29)

**The question asked:** how does Platterpus compare to EAC, to EAC rips, and to what
music trackers require of a rip log?

**The short answer, and it is not the flattering one:** a Platterpus/cyanrip log will
**never** pass a tracker logchecker, and no amount of work on this codebase changes
that. The gate is *which program ripped the disc*, checked before a single quality
line is read. That is a hard architectural fact, not a gap to close — and the one way
to "close" it is forgery, which KDD-24 already rules out.

What *is* worth doing is the rest of this document: the requirements EAC's settings
encode are mostly about read correctness, and several are things Platterpus already
does but does not *say*, or could measure and currently leaves as "unknown". Those are
real archival-quality wins, and they are ranked at the end.

---

### 1. Who checks, and what they actually run

Trackers score logs with two open-source implementations. Both do a **ripper
allow-list first**, quality second:

| Checker | Accepts | Everything else |
|---|---|---|
| [OPSnet/Logchecker](https://github.com/OPSnet/Logchecker) (PHP; what OPS runs) | EAC, XLD, whipper ≥0.7.3 | `UnknownRipperException` → score **0**, "Unrecognized log file" |
| [ligh7s/hey-bro-check-log](https://github.com/ligh7s/hey-bro-check-log) (Python; "aligned with Redacted standards") | EAC ≥0.99, EAC95, XLD | `UnrecognizedException` — and the version string must be in a hardcoded table |

Redacted's own rules name only EAC and XLD, and treat a log from any other tool as
trumpable ([rules](https://interviewfor.red/en/rules.html),
[ripping](https://interviewfor.red/en/ripping.html)).

**So: cyanrip, morituri, dBpoweramp, Rubyripper, CUERipper — not accepted.** whipper is
the sole non-EAC/XLD exception, and only at OPS.

#### Checksums are not the barrier — identity is

Worth being precise, because it is easy to assume the opposite. EAC's footer is an
obfuscated Rijndael-256 fold under a reverse-engineered key
([eac_logchecker.py](https://github.com/OPSnet/eac_logchecker.py),
[eac_logsigner](https://github.com/puddly/eac_logsigner)). But **whipper's checksum is a
plain SHA-256 of every line but the last, and OPS validates it**
(`src/Check/Checksum/Whipper.php`).

Platterpus's own footer is *structurally the same scheme* a real tracker already
accepts. The only thing between them is the ripper's name — which is exactly the right
place for the wall to be.

---

### 2. What the checkers deduct for

Recorded because these are the *quality* criteria worth caring about even when the
score is unreachable. From `heybrochecklog/resources/eac/english.json` +
`resources/__init__.py`, cross-checked against the PHP:

| Log line | Required | Deduction |
|---|---|---|
| `Read mode` | Secure | −20 |
| `Utilize accurate stream` | Yes | −20 |
| `Defeat audio cache` | Yes | −10 |
| `Make use of C2 pointers` | No | −20 |
| `Read offset correction` | matches the drive's AccurateRip value | −5 |
| `Fill up missing offset samples with silence` | Yes | −5 |
| `Delete leading and trailing silent blocks` | No | −5 |
| `Null samples used in CRC calculations` | Yes | −1 |
| `Gap handling` | Appended to previous track | −10 |
| `Add ID3 tag` | No | −1 |
| per-track `Test CRC` on every track | present | −20 |
| `Test CRC` ≠ `Copy CRC` | — | −30 per track |
| AccurateRip results | present | −5 |
| `==== Log checksum … ====` | present | −15 |

**Automatic zero:** unrecognised ripper; `Copy aborted`; `Normalize to`; `Use
compression offset`; a virtual/fake drive.

**Unscoreable rather than deducted** (thrown out): any of the settings lines *missing*;
a track missing filename/peak/copy-CRC; track count ≠ TOC count; an unknown version
string; a non-English log.

**Not scored at all:** overread into lead-in/lead-out. It is a recommendation.

---

### 3. Where Platterpus stands, row by row

cyanrip flags from `_build_rip_argv`: `-d`, `-s <offset>`, `-o flac`, `-r <retries>`,
`-Z <matches>`, `-O` (only when force-overread is on), `-S <speed>`, `-l <tracks>`,
`-N`, `-a`/`-t`, `-D`/`-F`, `-G`. Notably **no `-p`** — cyanrip's default already merges
pregaps into the previous track.

| Requirement | Platterpus equivalent | Status |
|---|---|---|
| Secure read | libcdio-paranoia always; `paranoia_level` allow-listed | **met** |
| Defeat audio cache | *measured* via `cd-paranoia -A` (KDD-29), not asserted | **met when probed** |
| Delete silent blocks: No | asserted for cyanrip (it writes what it reads) | **met** |
| Null samples in CRC: Yes | asserted for cyanrip (CRCs matched a real EAC log, 12/14 tracks) | **met** |
| Gap handling | wording **actually** fixed 2026-07-30 (see below) — says "Not detected, thus appended to previous track" | **wording met, detection is not** |
| Test & Copy | `-Z` convergence rendered as a Test/Copy pair | **partial** |
| AccurateRip | parsed and rendered; `verdict.py` is the single predicate | **met** |
| No ID3 on FLAC | Vorbis comments only | **met** |
| Individual tracks (not a range rip) | cyanrip is always per-track | **met** |
| No normalization / compression offset | never emitted | **met** |
| Read offset correction | `-s` applied; value printed but never asserted *correct* | **partial** |
| Fill missing offset samples with silence | derived from overread text, else unknown | **partial** |
| `Make use of C2 pointers` | **`No`, measured** on a drive that reports C2 unsupported; "(not reported)" otherwise (see below) | **met on the rig; open in general** |
| `Utilize accurate stream` | no equivalent | **open** |
| Signed EAC log footer | plain SHA-256, self-labelled *not* EAC's | **by design** |
| Recognised ripper name | never emitted (KDD-11/24/28) | **by design → score 0** |

#### The C2 row — earned by the ripper, not by the survey (settled 2026-07-30)

The survey says libcdio-paranoia never uses C2 error pointers, which would let this
row be asserted `No` and remove EAC's most heavily-weighted unknown. **I changed it on
that basis, a test stopped me, and the test was right.**
`test_does_not_fabricate_read_mode_or_c2_pointers` exists precisely to stop a value
being printed into an archival log without evidence, and a secondary source summarising
libcdio is not the standard the silent-blocks and null-samples rows are held to.

**Then the rig answered it directly.** cyanrip's own header on the BDR-209D prints
`C2 errors: unsupported by drive`, the parser maps that to `False`, and the exported log
reads `Make use of C2 pointers : No`. That is first-party evidence from the tool doing
the read — the standard the test was defending — so the row is now filled on this drive.

The distinction the parser keeps, and that matters: cyanrip's line reports what the
**drive can do**, not what the rip did. "unsupported" *proves* C2 was not used; a
"supported" line would prove only that it was available, and EAC's row asks whether C2
was *used*. So a C2-capable drive still yields "(not reported)" rather than a guess in
either direction. The row is met where the hardware settles it, open where it doesn't.

---

#### Pregap detection — a real archival gap, now visible in the log (found 2026-07-30)

Comparing the committed real EAC 1.8 log against the cyanrip log **of the same disc in
the same drive** shows something neither log's wording had made obvious:

| | EAC 1.8 | cyanrip 0.9.3 |
|---|---|---|
| `Gap handling` | `Appended to previous track` | `Gaps: None signalled` |
| Per-track `Pre-gap length` | present for **10 of 14** tracks (1, 2, 4, 5, 7, 8, 9, 10, 13, 14) | none |

**EAC detects pregaps that cyanrip does not.** (Ten of the fourteen; tracks 3, 6, 11 and 12 have none in EAC's log either. The committed baseline is **two concatenated EAC runs**, so a whole-file `grep -c` doubles every count — 20 pregap lines, not 20 pregaps.) EAC runs its own gap-detection pass;
cyanrip reports what the disc's TOC signalled, and on this disc the TOC signalled
nothing. Both tools then *append* the gap to the previous track, so **the audio is
unaffected** — this is a completeness gap in the archival record, not a correctness one.

It is the same capability gap as KDD-32 / the `INDEX 00` work, and it is the reason the
run sheet's cyanrip-`master` build step exists.

Until 2026-07-30 our exported row echoed cyanrip's "None signalled", which hid the
comparison entirely. It now reads EAC's own phrase for the not-detected case, so a
side-by-side diff against a real EAC log shows the difference instead of burying it —
and `test_gap_row_vocabulary_comes_from_a_real_eac_log_not_from_us` pins the
disagreement so nobody later "fixes" it by making the string match.

---

### 4. Ranked next steps, cheapest first

1. **Earn the C2 row** — read libcdio-paranoia's source for C2 handling, or measure it,
   then assert `No` with the evidence recorded next to the assertion. ~10 lines once the
   evidence exists; the point is the evidence, not the lines.
2. **`Fill up missing offset samples with silence`** — plumb `force_overread` into the
   renderer, which currently only sees parsed log text. ~30 lines.
3. **Assert the offset is *correct*, not merely applied** — the AccurateRip drive table
   is already in `adapters/accuraterip_offsets_data.py`, so the log can say
   `+667 (matches the AccurateRip database for PIONEER BD-RW BDR-209D)`. Genuine
   archival value: it turns a number into a checkable claim. ~40 lines.
4. **Investigate accurate-stream** — check whether `cd-paranoia -A` output carries a
   usable signal. May be a dead end; investigation before code.
5. **Do NOT build a whipper-format emitter.** It is the only technically-passing route,
   and it is the same forgery as EAC-signing: whipper did not do the rip.

---

### 5. The honest framing

A 100% logchecker score certifies **process and provenance** — that a known program,
configured a known way, produced this log. It explicitly does not certify bit-perfect
audio; OPS's own README concedes that a sub-100% log can still be a perfect rip.

Platterpus makes a *different and narrower* claim, and it is a stronger one about the
audio itself: **provably bit-perfect, verified openly** via AccurateRip v1/v2 + CTDB
CRCs and per-track Copy-CRC parity against the committed EAC baseline in
`output_reference/EAC_flac/` (currently 12/14 for cyanrip FLAC, with the two
mismatches attributable to the disc, tracked in the hardware runs).

That is the goal to keep. "Tracker-acceptable" is not reachable and should not be
chased.

#### One correction to our own docs

`docs/eac-parity.md` says whipper "still cannot clear RED's
checksum requirement." OPS's checker **does** validate whipper's plain SHA-256, so the
checksum wall is cleared there. The accurate statement is that *Redacted's rules* list
only EAC and XLD — a policy limit, not a technical one.

---

*Sources:* [OPSnet/Logchecker](https://github.com/OPSnet/Logchecker) ·
[ligh7s/hey-bro-check-log](https://github.com/ligh7s/hey-bro-check-log) ·
[OPSnet/eac_logchecker.py](https://github.com/OPSnet/eac_logchecker.py) ·
[puddly/eac_logsigner](https://github.com/puddly/eac_logsigner) ·
[interviewfor.red rules](https://interviewfor.red/en/rules.html) ·
[interviewfor.red ripping](https://interviewfor.red/en/ripping.html) ·
[eacguide.github.io](https://eacguide.github.io/) ·
[arg274/cambia](https://github.com/arg274/cambia)

---

*Last updated for Platterpus v0.6.3.*
