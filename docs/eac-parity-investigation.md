# EAC parity investigation — can Platterpus output be bit-identical to EAC?

**Status:** research + plan (2026-06-27). Triggered by the maintainer's goal:
*"this program needs to essentially output the exact same files, bit by bit, as
EAC."* This document marks every axis where our output can deviate from EAC,
says whether closing the gap is **possible**, and lays out a prioritized plan.

Evidence base: a real hardware rip of **The Police — *Every Breath You Take: The
Classics*** (cyanrip 0.9.3, Pioneer BDR-209D, +667 offset) compared against the
EAC V1.8 baseline of the same disc. Logs/cues live in
[`output_reference/`](../output_reference/) (`EAC_flac/` vs `cyanrip_flac/`).

## TL;DR — two very different goals

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

## Deviation matrix (EAC ↔ our cyanrip output)

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

## The two audio tracks that differ (the only real audio gap)

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

## Pre-gaps in the cue (the "Detect Gaps" question) — why it's hard

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

## Extraction-vector scorecard (vs. the 2026 landscape doc)

The maintainer's 2026 ripper-landscape research doc scores extraction tools
against a fuller list of vectors than the EAC-guide audit (KDD-13) covers.
Scoring Platterpus/cyanrip against that full list, one row per vector:

| Vector | Status | Rationale |
|---|---|---|
| Read offset | **Present** | Per-drive offset applied via cyanrip `-s`; correct on the BDR-209D (+667), confirmed byte-identical on 12/14 tracks. |
| Cache defeat | **Attempted, not measured** | libcdio-paranoia attempts cache defeat (readahead exhaustion + FUA where supported); cyanrip emits no verdict. Reported `(unknown)` by design, never forged. See PLANNING.md KDD-25. |
| Overread (into lead-in/lead-out) | **Exists upstream, not surfaced** | cyanrip's `-x` flag exists but Platterpus never passes it (dropped as a Settings toggle when whipper was removed, KDD-18); re-openable as a fresh cyanrip-native task. |
| Subcode / pre-gap / `INDEX 00` | **Absent** | cyanrip performs no subchannel pre-gap detection on this path, so no `INDEX 00` cue metadata is emitted. The underlying *audio* is unaffected (append/merge-to-previous matches EAC) — this is a cue-metadata gap only. See "Pre-gaps" above. |
| HTOA (hidden track one audio) | **Absent — explicit scope note** | Not pursued: HTOA discs are rare in practice, and neither backend gives us a clean, low-effort path to it. Out of scope rather than a tracked gap; see `TASKS.md` "Out of scope." |
| Pre-emphasis | **Flag-only, intentionally unused** | cyanrip's `-E` (de-emphasis) flag exists but is deliberately not passed — Platterpus preserves pre-emphasis-encoded discs as-is (an archival choice: don't alter samples) rather than actively de-emphasizing. See `docs/dependency-contracts.md`. |
| AccurateRip v1/v2 | **Present** | Queried every rip; v1+v2 confidence parsed and rendered (KDD-12). |
| CTDB (whole-disc verify) | **Present, validated** | `ctdb/` clean-room client (KDD-16); GUI-wired; `crc.CRC_VALIDATED=True` since 2026-07-07 (a real disc's CRC reproduced at offset 0 on hardware), so a match reads "verified". |
| Test & Copy (two full passes) | **Absent** | No literal two-pass Test&Copy. Single secure read strengthened by `-Z N` re-read convergence instead — a different, cheaper mechanism aimed at the same correctness goal, not a gap we're trying to close by adding a second pass. |
| EAC log + checksum | **Unsigned, by design** | We render an EAC-*layout* log (`eac_log_export.py`) attributed to Platterpus/cyanrip and explicitly marked "not a genuine EAC log" — never a forged checksum. This is the deliberate open-trust choice (KDD-24), not a missing feature. |
| Gap handling | **Audio matches; no `INDEX 00`** | Same entry as "Subcode / pre-gap" above — audio placement is EAC-equivalent, cue metadata isn't. |

**Reading this table:** "present"/"partial" rows are real capability; "absent"
and "out-of-scope" rows are **deliberate**, not oversights discovered too
late — each links back to the KDD or doc that made the call. The one
genuinely load-bearing absence for *tracker* purposes (not audio purposes) is
covered separately in PLANNING.md **KDD-24**: none of the rows above matter
for tracker acceptance anyway, because that gate is ripper-identity, not
vector coverage.

## Plan (prioritized)

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
  [docs/eac-log-and-repair-feasibility.md](eac-log-and-repair-feasibility.md)
  (repair deferred; its CRC-validation gate cleared 2026-07-07). **✅ The
  manual workflow is written: [`manual-ctdb-repair.md`](manual-ctdb-repair.md)
  (2026-07-21).**
- (c) First, simply **re-rip track 3** to see if the near-miss was transient.

**P3 — Pre-gaps / `INDEX 00` in the cue (decision-gated).**
- (a) Hardware-test cyanrip's **`-p`** modes (`-p default`/`merge`) to see if any
  makes it record `INDEX 00` for this disc; if so, pass it and we get EAC-style
  pre-gap markers for free.
- (b) If cyanrip won't detect subchannel pre-gaps, the only routes are a cyanrip
  feature request, the whipper/cdrdao path (cdrdao reads full TOC incl. gaps —
  but whipper is offset->587-buggy and cdrdao stalls on this BD drive), or
  generating the cue ourselves from a subchannel read we don't currently do.
  *(Superseded 2026-07-07: the researched answer lives in
  [docs/upstream-pr-roadmap.md](upstream-pr-roadmap.md) — support cyanrip
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

## Bottom line

- **Audio parity with EAC is achievable and 12/14 already met** — the path to
  14/14 is re-rip + CUETools-repair-class tooling for the marginal tracks (P2),
  not a format change.
- **File-byte identity with EAC is impossible across encoders and is the wrong
  goal** — lossless audio + AccurateRip CRC is the archival standard, and we meet
  it where the disc allows.
- **EAC-style pre-gap cue markers are a metadata nicety, currently blocked on
  cyanrip pre-gap detection**, and only matter for disc-image use (P3/P5).

---

*Last updated for Platterpus v0.4.24.*
