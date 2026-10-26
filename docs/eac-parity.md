# EAC parity — how close we are, and what is left

The single home for *"can Platterpus output stand in for an EAC rip?"*. Four investigations that each answered one part of that question, kept whole and put in one place: what deviates and why, whether a tracker would accept our log, how the two log formats compare field by field, and what the actual logcheckers deduct for. A fifth, Part E, is an independent audit of the whole comparison that re-derives its numbers from the raw logs and grades each area better, equal or worse.

**For the verdict, read Part E first; for the framing, Part A**, which carries the framing the other parts assume — that *bit-identical audio* and *tracker-accepted log* are different goals with different answers, and conflating them is how this subject goes wrong.

## Standing direction (KDD-36, 2026-09-21)

**Read this before treating anything below as a target.** The four investigations
in this file measure our output *against EAC's*, because that is the question they
were asked. The project's direction is now the other way round.

* **The EAC-layout export is a compatibility artifact.** Track EAC's format as
  closely as honesty allows and never one step further — it exists for a human
  diff and for readers who expect that layout, not because it is the better
  record. The refusals stand permanently: no Rijndael-256 signature, no
  `Defeat audio cache: Yes` we cannot measure, no field asserted rather than
  observed (KDD-11, KDD-13, KDD-25).
* **Our own log is the goal.** Keep it true, full and current, and weigh work on
  it as work on a candidate reference format.
* **And we are not there yet.** Today our log carries more *diagnostics* than
  EAC's and less *proof of provenance*, because we refuse the one mechanism that
  would supply it. "Better diagnostics" is not "accepted". A gap in it is recorded
  as a gap, never filled with a plausible value.

This does not reverse Part C or Part D: tracker acceptance is still unreachable
and still not chased. What changed is that the open-trust path is now the **route**
to being accepted on merit, rather than the consolation for not being.

## Where this came from

Consolidated from four separate documents so the subject has one home. Each part keeps its original text, with its headings demoted one level. Later changes are dated status notes and corrected rows; git history has the originals.

**Parts are lettered, not numbered, on purpose:** Part D numbers its own sections from 1, so a numbered wrapper would make a reference like *§2* ambiguous. `Part D §3` reads exactly one way. Part C's two halves were called "Part A" and "Part B" in their original file, and are now *Part C §1* and *Part C §2*.

| Part | Was | Written |
|---|---|---|
| A | the former `eac-parity-investigation.md` | 2026-06-27 |
| B | the former `log-format-comparison.md` | 2026-05-28, rewritten for cyanrip 2026-07-01 |
| C | the former `eac-log-and-repair-feasibility.md` | 2026-06-28 |
| D | the former `eac-tracker-requirements-2026-07.md` | 2026-07-29 |
| E | written here: the independent audit against EAC | 2026-10-19 |

---

## Part A — Can our output be bit-identical to EAC?

## EAC parity investigation — can Platterpus output be bit-identical to EAC?

**Status:** research + plan (2026-06-27). *Status 2026-10-07: P0, P1, P2(a) and
(c), P2(b)'s manual workflow and P4 are done; P3 is superseded by the fork; P5 is
open. Tracks 3 and 5 are the open audio gap (item 1).* Triggered by the
maintainer's goal:
*"this program needs to essentially output the exact same files, bit by bit, as
EAC."* This document marks every axis where our output can deviate from EAC,
says whether closing the gap is **possible**, and lays out a prioritized plan.

Evidence base: a real hardware rip of **The Police — *Every Breath You Take: The
Classics*** (cyanrip 0.9.3, Pioneer BDR-209D, +667 offset) compared against the
EAC V1.8 baseline of the same disc. Logs/cues live in
[`output_reference/`](../output_reference/) (`EAC_flac/` vs `cyanrip_flac/`).
Later evidence: the fork's rip (`output_reference/cyanrip_fork_flac/`, 2026-08-04)
and the Full runs under `docs/handshake/artifactsround26/` to `artifactsround34/` (the 2026-10-12 run is `artifactsround31/v07103full*`). Since HR-2 (2026-10-14) those run folders live on the `evidence` branch, each indexed by a row of `docs/evidence-manifest.tsv`; `main` keeps only their READMEs.

### TL;DR — two very different goals

1. **Bit-identical *audio* (the PCM samples) — every track has been read
   verified, but never all fourteen in one rip.** This is the real meaning of
   "archival/EAC-quality": the *samples* equal the AccurateRip consensus, proven by
   the per-track CRC. Matching EAC is the usual proxy, and on this disc it is not
   the same thing, because EAC's own track 5 is not the consensus.
   **Status (2026-10-19), measured over every 14-track log of the reference disc on
   record: 26 rips, 2026-08-04 to 2026-10-16** (`output_reference/
   cyanrip_fork_flac/` and the `*eac.log` files under
   `docs/handshake/artifactsround26/` to `artifactsround34/`, read at evidence
   commit `fe13de0c`):
   - **Twelve tracks match AccurateRip at confidence 200 in all 26**, each with one
     value across all 26.
   - **Track 3.** AccurateRip verifies EAC's value, `59D352DD`. We read it in 9 of
     the 26, and in none of the 15 since the round 30 whole-disc rip of 2026-09-30.
     On 2026-10-12 the whole-disc rip gave `2AC1F945` and the secure re-read a value
     not seen before, `029BB984` (`v07103fullsecurerereadeac.log`). On 2026-10-13, on
     `.22`, the whole-disc rip gave `2AC1F945` again and the secure re-read
     `69D238D2`, first seen in round 30's securing pass of 2026-10-06
     (`round32fullsecurerereadeac.log`). Rounds 33 and 34 gave four values never
     seen before: `0759E037` and `1CA7B917` on 2026-10-14 (`.22`), `A2C798BA` and
     `1AC787A1` on 2026-10-15/16 (`.23`), whole-disc rip then secure re-read
     (`round33full*eac.log`, `round34full*eac.log`): fifteen values in 26 rips.
     This drive reads the track differently from pass to pass: on 2026-10-07 the
     whole-disc rip's first pass gave `1D0B4419`, and its secure re-read's five
     reads gave `149C0991`, `418F6CF8` twice, `34D9A79A` and `418F6CF8` again
     (`round31fullwholediscsecuringpass.txt`).
   - **Track 5.** EAC's value, `E0036697`, is **not** the consensus: EAC's own log
     says *"Cannot be verified as accurate … AccurateRip returned [BCF4E815]"*. The
     2026-10-07 secure re-read converged on `C96464AB`, which AccurateRip verifies
     (v2 `BCF4E815`, confidence 200; v1 confidence 129;
     `round31fullsecurereread.log:437-441`). We read that value once in 26. The
     others gave EAC's `E0036697` (17), `6902BCF0` (7), or once `4065BECC`
     (round 33's whole-disc rip, 2026-10-14, `round33fullwholedisceac.log`).
   - **Equal to EAC on all 14:** 5 rips (2026-08-04, 2026-09-24, 2026-09-26 twice,
     2026-09-28). Each of those carries EAC's unverified track 5.
   - **AccurateRip-verified on all 14 in one rip:** none yet. Track 3's verified
     read and track 5's have never come in the same rip.

   Correction (2026-10-07): earlier text here, and in `TASKS.md`, called track 5
   "the disc" and said no ripper could verify it. The 2026-10-07 secure re-read
   shows otherwise.

   **EAC was not consistent on this disc either** (Part E §E2, 2026-10-19): of its three
   committed sessions, only 2026-06-11 read track 3 correctly. The two 2026-06-25 sessions
   (`output_reference/EAC_mp3/`, `EAC_wav/`) read it wrong, with Test ≠ Copy, and one
   misread track 4 as well. Two of EAC's wrong track-3 values are values our ripper also
   read, so the misread is the drive's.

   The 12/14 below is the dated stock-0.9.3 record that the analysis was written
   against.

   > **Outcome (2026-07, added after later hardware runs):** the v0.4.13
   > re-rip reached **13/14** — Track 3 converged partial→exact on a re-read,
   > confirming P2(c)'s transient-near-miss prediction (see the v0.4.13
   > session-log entry, and `output_reference/README.md` § `cyanrip_mp3/`, an
   > earlier rip of 2026-06-27 with the same track-3 result); Track 5 remains the
   > disc's own defect *(corrected 2026-10-07: it is not; see item 1 above)*. A still-later re-rip
   > regressed Track 3 again, refining the story to *read-instability on that
   > track* — now auto-detected by the v0.4.24 re-rip comparison. The `-Z`
   > hardware gate below is **answered** (a real `-Z` run produced per-track
   > convergence data, session-log 0.4.7), and P1 is **✅ done**
   > (`scripts/eac_parity.py` golden-tested; `tests/test_parity.py` pins the
   > committed 12/14 baseline; procedure + CRC table in `docs/test-plan.md`).
   > The committed-baseline analysis below is kept as the dated record.

2. **Bit-identical *files* (the `.flac`/`.cue`/`.log` byte-for-byte) — NOT
   ACHIEVABLE, and not the right target.** A FLAC file's bytes are *encoder-
   determined*: EAC writes WAV and runs `flac.exe -8 -V` on it; we use FFmpeg/libavcodec. Even
   with **identical PCM**, the two encoders choose different block sizes,
   prediction, stereo decorrelation, padding, seektable, and vendor string, so
   the `.flac` files never hash-match (Xiph FLAC format overview; Xiph FAQ). The
   `.cue`/`.log` are different tools' formats entirely. **This is expected and
   fine** — lossless means *same audio*, and the durable proof is the decoded-PCM
   CRC, never the file hash (exactly why Critical Rule #8 / `output_reference/`
   commit CRCs, not audio).

So we reframe the maintainer's goal to the one that is both meaningful and
attainable: **match the AccurateRip consensus, not EAC's file bytes.** On this
disc that is EAC's extracted PCM on 13 tracks; on track 5 EAC's own read is not
the consensus (item 1).

### Deviation matrix (EAC ↔ our cyanrip output)

| Axis | EAC | Our cyanrip | Same? | Possible to close? |
|---|---|---|---|---|
| Read offset | +667 | +667 (`-s 667`) | ✅ identical | n/a |
| Drive / disc | BDR-209D | BDR-209D | ✅ | n/a |
| TOC (track sectors) | — | — | ✅ identical (all 14) | n/a |
| Secure / re-read | Secure | paranoia max | ✅ equivalent | n/a |
| Gap handling **audio** | append-to-previous | default merge-to-previous | ✅ (14/14 on the fork, 2026-08-04, and the Gap handling row agrees) | n/a |
| Per-track **PCM** | baseline (13 tracks AccurateRip-verified; track 5 not) | equal to EAC on all 14 in 5 of 26 rips; AccurateRip-verified on 12 every time, on track 3 in 9 of 26, on track 5 once | ⚠️ never all 14 verified in one rip | Tracks 3 and 5 (TL;DR, item 1) |
| Overread lead-in/out | No | No: the offset needs 2 frames past the edge, and they are filled with silence, not read (`Overread mode: fill with silence in lead-in/lead-out`) | ✅ same | closed: EAC also fills with silence when overread is off; tracks 1 and 14 match EAC and AccurateRip |
| **Pre-gap markers in cue** (`INDEX 00`) | Yes: 9 in the cue (its log lists 10 pre-gaps, counting track 1's lead-in) | **Yes on the fork**: every pregap EAC finds, to the hundredth of a second | ✅ fork / ❌ stock 0.9.3 | closed on the fork (§Pregaps; the 2026-10-07 cue, `docs/handshake/artifactsround31/round31fullwholedisc.cue`) |
| FLAC **file bytes** | flac.exe `-8` | libavcodec | ❌ differ | **No** (encoder-determined) — and unnecessary |
| Tag **values** | EAC set | cyanrip set + colon-restore | ✅ matchable | minor work if needed |
| Tag/file **byte layout** | EAC | FFmpeg | ❌ differ | **No** — unnecessary |
| `.log` / `.cue` format | EAC | cyanrip, plus our EAC-layout log | ⚠️ partly | Log: our EAC-layout companion has a byte-identical TOC table (`tests/test_eac_layout_parity.py`). Cue: on the fork the FILE/TRACK/INDEX lines equal EAC's (2026-10-07); REM, tag and file-name lines differ |
| Single-file disc image+cue | optional | **unsupported** | ❌ | needs another tool |

### The two audio tracks that differ (the only real audio gap)

> **Status (2026-10-19).** Both tracks are still open, and track 5 is not what the
> analysis below says. Track 5's AccurateRip-verified value is `C96464AB`, read
> once (2026-10-07); EAC's `E0036697` is the unverified read. Track 3's verified
> value is EAC's `59D352DD`, read in 9 of 26 rips and in none since 2026-09-30.
> Full numbers: TL;DR, item 1. The analysis below is the stock-0.9.3 record.

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

### Pre-gaps in the cue (the "Detect Gaps" question) — closed on the fork

> **Status:** closed. The fork carries PR #115's sub-channel reader, and finds
> every pregap EAC finds, in order, to the hundredth of a second, on the reference
> disc (2026-08-04; `tests/test_fork_rip_eac_parity.py` holds all ten of EAC's
> `Pre-gap length` rows). The fork's rips write them into the cue as `INDEX 00`: the
> 2026-10-07 run's cue has nine, on the same nine tracks as EAC's cue (track 1's
> two seconds are the standard lead-in, which neither cue marks). Below is the
> stock-0.9.3 analysis that made it look hard.

EAC runs a **Detect Gaps** pass that reads the disc **subchannel** to find
index-00 pre-gaps, and records them as `INDEX 00` in its cue (9 tracks here; its
log lists 10 pre-gaps, counting track 1's two-second lead-in, which a cue does not
mark). Our cyanrip cue has none — every track is plain `INDEX 01 00:00:00`.

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

So on **stock cyanrip 0.9.3**, writing EAC-style `INDEX 00` pre-gaps is **blocked
on pre-gap detection**, which stock cyanrip doesn't do on this path. The Platterpus
fork — the build the setup wizard installs (KDD-32/KDD-33) — does detect them and
its cue carries `INDEX 00` (the *Subcode / pre-gap / `INDEX 00`* scorecard row
below). The findings above are the stock-0.9.3 record.

### Extraction-vector scorecard (vs. the 2026 landscape doc)

The maintainer's 2026 ripper-landscape research doc scores extraction tools
against a fuller list of vectors than the EAC-guide audit (KDD-13) covers.
Scoring Platterpus/cyanrip against that full list, one row per vector:

| Vector | Status | Rationale |
|---|---|---|
| Read offset | **Present + auto-confirmed (KDD-31)** | Per-drive offset applied via cyanrip `-s`; correct on the BDR-209D (+667), confirmed byte-identical to EAC on 14/14 tracks (the fork, 2026-08-04). A rip that matches the AccurateRip global consensus records the offset as `ACCURATERIP_CONFIRMED` (medium on its own), promoted to CONFIRMED/HIGH when it agrees with the AccurateRip-list value (`drive_profiles.py`) — the equal-or-stronger analogue of EAC's Key-Disc check (re-confirms every matching rip). A from-scratch finder for drives *absent* from the AR list is deferred to the soft-fork roadmap. |
| Cache defeat | **Measured (KDD-29)** | libcdio-paranoia attempts cache defeat every rip; cyanrip emits no verdict, so we **measure** it with `cd-paranoia -A` (libcdio's copy of that same engine) via Set up drive → Analyse cache, recorded per drive and folded into the EAC-compatible log. Still `(unknown)` (never forged) when the probe is inconclusive — the KDD-25 honesty rule holds. Hardware-tuned on the BDR-209D. |
| Overread (into lead-in/lead-out) | **Present (opt-in)** | Surfaced 2026-07-21 as the Settings "Overread" toggle → cyanrip `-O`, off by default (EAC's baseline setting is "overread: No", and that's how the 14/14 fork rip matched). Flag-letter corrected the same day: this row previously said `-x`, which did not exist in cyanrip then — `-O` verified against 0.9.3.1 + master. `-x` later existed on the fork as the cache probe, not overread, and from `.23` the probe is the long-only `--cache-probe`. **On the BDR-209D leave `-O` off:** cyanrip stalled about 23 minutes at the lead-out with it (2026-07-22, stock 0.9.3; `docs/dependency-contracts.md`). |
| Subcode / pre-gap / `INDEX 00` | **Present on the fork; absent on stock 0.9.3** | Stock cyanrip 0.9.3 performs no subchannel pre-gap detection, so it emits no `INDEX 00` cue metadata — that is the `cyanrip_flac/` reference, still cited by tests. The Platterpus fork, which is the build the setup wizard installs (KDD-33), reads them from the sub-channel: the 2026-08-04 rig rip matched **all ten** of EAC's `Pre-gap length` rows to the hundredth of a second, in order (`output_reference/cyanrip_fork_flac/`, asserted by `tests/test_fork_rip_eac_parity.py`). That 2026-08-04 cue predates two fork cue fixes (it has four zero-length `INDEX 00` rows and one ISRC of 14); the 2026-10-07 cue (`docs/handshake/artifactsround31/round31fullwholedisc.cue`) has EAC's nine markers, on the same tracks, and all 14 ISRCs. Those ISRCs are MusicBrainz's, passed in with `-t`, not the disc's: track 1 reads `GBAAM0201086` where EAC's cue has `GBAAM7800003` (Part E §E5, TASKS R20). The underlying *audio* was never affected either way (append/merge-to-previous matches EAC). See "Pre-gaps" above. |
| HTOA (hidden track one audio) | **Absent — explicit scope note** | Not pursued: HTOA discs are rare in practice, and cyanrip (the sole backend since KDD-18) gives us no clean, low-effort path to it. Out of scope rather than a tracked gap; see `TASKS.md` "Out of scope." |
| Pre-emphasis | **Preserved from 0.7.102 (`-W`)** | Up to 0.7.101 a pre-emphasised disc was de-emphasised: cyanrip does that by default (`settings.deemphasis = 1`, cyanrip@ca3f3ea:src/cyanrip_main.c:1816) and Platterpus did not pass `-W`, so the FLAC held altered samples AccurateRip could not verify. From 0.7.102 every rip passes `-W` (the maintainer's call, 2026-10-07): the FLAC holds the disc's samples, as EAC's does, and the cue carries `FLAGS PRE` (cyanrip@ca3f3ea:src/cue_writer.c:187-188) for a player to de-emphasise on playback. `-E` (force de-emphasis) is never passed. Untested on hardware: no pre-emphasised disc has been ripped. |
| AccurateRip v1/v2 | **Present** | Queried every rip; v1+v2 confidence parsed and rendered (KDD-12). |
| CTDB (whole-disc verify) | **Present, validated** | `ctdb/` clean-room client (KDD-16); GUI-wired; `crc.CRC_VALIDATED=True` since 2026-07-07 (a real disc's CRC reproduced at offset 0 on hardware), so a match reads "verified". |
| Log layout (side-by-side comparable) | **Present (2026-07-27)** | Checked against a genuine EAC V1.8 log of the same disc: the TOC table is byte-identical, and the archival header, output-format block and end-of-rip status report use EAC's rows and wording. Unreportable rows are labelled `(not reported by the ripper)`. Attribution + checksum stay deliberately distinct — layout is parity, provenance would be forgery. |
| Accuracy comparison from logs alone | **Present (2026-07-27)** | `parity.compare_logs` pairs all 14 tracks across a real EAC log and ours with no other input. The stock-0.9.3 reference rip matches EAC on **13/14** tracks once its auto-fixed read is reported; the fork's 2026-08-04 rip matches 14/14. |
| Test & Copy (two full passes) | **Present via `-Z` convergence (KDD-30)** | No literal two-labeled-pass mode, but `-Z N` (re-read until N+1 reads are identical, so at least two) gives the same two-reads-agree guarantee. A converged track renders as an EAC-style **Test CRC == Copy CRC** pair in the EAC-compatible log; the Settings toggle "Verify every track with a second read" runs it whole-disc. Single-read tracks show only a Copy CRC — never a fabricated test read. Includes tracks the per-track auto-fix re-read *after* the whole-disc log was written: the swapped-in read's own record — CRC, AccurateRip results, convergence — is folded over the first pass (`_apply_auto_fix_results`), so the pair describes the file on disk and not the discarded read, and convergence is claimed only when the converged copy was actually swapped in (both hardware-found 2026-07-26). |
| EAC log + checksum | **Present — our own checksum, not EAC's** | We render an EAC-*layout* log (`eac_log_export.py`) attributed to Platterpus/cyanrip, explicitly marked "not a genuine EAC log", and now footered with **our own integrity checksum: a plain SHA-256 of the text above it, equal-or-stronger than EAC's and openly verifiable** (`head -n -1 … \| sha256sum`) — never EAC's obfuscated *provenance* signature (KDD-28, refining KDD-11; open-trust choice KDD-24). |
| Gap handling | **Audio matches; `INDEX 00` on the fork** | Same entry as "Subcode / pre-gap" above — audio placement is EAC-equivalent on either build; the cue metadata arrived with the fork. |

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
count — so "did this rip match EAC?" is one command. **✅ Done** (the outcome note above, and the 2026-10-05 note below).

> **Running it, and what it refuses (2026-10-05).** The command is
> `python3 scripts/eac_parity.py <baseline> <candidate.log> [more candidates]`,
> with `output_reference/EAC_flac/eac_baseline_police_classics.log` as the
> baseline for the reference disc. Before any table it prints **who wrote the
> baseline**, quoting the baseline's own first line, as read by
> `parsers/eac_log.eac_log_producer` (the one predicate; the tool does not
> restate it). Three answers, three behaviours:
>
> - **Exact Audio Copy** (its banner, e.g. `Exact Audio Copy V1.8 from 15. July
>   2024`): compared as normal. That is what the log *says*, not proof; EAC's
>   own log checksum is not checked.
> - **One of our own EAC-layout exports** (either banner wording, `Platterpus
>   rip log in EAC's layout, …` or the 0.6.62-and-earlier `Exact Audio
>   Copy-compatible log generated by Platterpus`): **refused, exit 2**, with the
>   line that identified it on screen and in the log, and no table. Every track
>   of a rip matches our own export of that rip by construction. Before this,
>   the committed export against its own rip printed `14/14 — PARITY ✓` and
>   exited 0. Refused rather than warned because a false pass gets committed
>   under `output_reference/` and cited, while a false refusal needs a real EAC
>   log to begin with one of our banners. Our export is still fine as a
>   *candidate*. `platterpus.parity.ParityReport.ok` refuses such a baseline as
>   well, so no other caller of `compare_logs` can be handed the pass
>   (`rip_audit`'s `eac_log_agreement` reports it as not determined).
> - **Not determined** (a cyanrip or legacy-format log, or anything else):
>   compared, because checking two rips against each other is legitimate, but
>   the output, the log and the verdict line all say the match is parity *with
>   that log*, not with EAC.
>
> Exit codes: `0` every candidate at parity, `1` at least one not, `2` an
> unreadable file or a refused baseline.

**P2 — Close Track-3-class near-misses (the real audio gap).**
- (a) Add cyanrip **`-Z N`** ("re-rip until checksums match N times") as a
  secure-rip option for marginal discs — strengthens reads so a near-miss track
  converges to the consensus. **✅ Code landed 2026-06-28** (as the Settings
  control now named "Extra matching reads to trust a track" (renamed twice:
  it was "Max reads to confirm a shaky track", then "Reads that must agree
  to trust a track", which counted one short — `-Z N` needs N+1 identical
  reads),
  `config.secure_rerip_matches` → cyanrip `-Z N`; dynamic secure re-rip is
  **on by default since v0.4.9** — no opt-in checkbox; the grey-out clause for
  the previous backend is history, that backend was removed 2026-06-30, KDD-18). **Answered on
  hardware, with mixed results:** `-Z 2` has converged track 3 to the consensus
  (`docs/handshake/artifactsround26/round26securerereadeac.log`), converged on a
  value AccurateRip does not know (`round31fullwholediscsecuringpass.txt`, 2026-10-07),
  and failed to converge (`round31fullsecurereread.log`, 2026-10-07: repeat limit
  reached). Agreement proves the reads repeat, not that they are right.
- (b) Document the **CUETools Repair** workflow as the authoritative fix for a
  "partially accurate (450)" track, and evaluate a future in-app CTDB-repair
  step (large; CTDB verify already exists, repair does not). Evaluated in
  Part C §2 below (repair deferred; its CRC-validation gate cleared 2026-07-07).
  What did ship for this gap: the per-track auto-fix re-read, and `--compare` /
  `--assemble-best-of` (CHANGELOG 0.4.24). **✅ The
  manual workflow is written: [`manual-ctdb-repair.md`](manual-ctdb-repair.md)
  (2026-07-21).**
- (c) First, simply **re-rip track 3** to see if the near-miss was transient.
  **✅ Done:** transient on some reads and not on others (the outcome note above).

**P3 — Pre-gaps / `INDEX 00` in the cue (decision-gated).**

> **Status: superseded.** The Platterpus fork carries PR #115 and writes `INDEX 00`
> by default; no `-p` mode and no image mode was needed. (a) to (c) are kept as the
> stock-0.9.3 record. One sentence in (a) held only on stock 0.9.3, which detected
> no pregaps: once pregaps are detected, `-p` modes do move pregap audio between
> files (cyanrip@ca3f3ea:src/cyanrip_main.c:1559-1575).
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
  feature request, the previous backend's cdrdao path (cdrdao reads full TOC
  incl. gaps — but that backend is offset->587-buggy and cdrdao stalls on this BD
  drive), or
  generating the cue ourselves from a subchannel read we don't currently do.
  *(Superseded 2026-07-07: the researched answer lives in
  [docs/cyanrip-upstream.md](cyanrip-upstream.md) — support cyanrip
  **PR #115**, with a Platterpus-side `cdrdao read-toc` as the documented
  fallback; the previous backend's route no longer exists — KDD-18.)*
- (c) **Decision gate:** is `INDEX 00` worth it given the audio is already
  equivalent and per-track FLACs don't use it? Likely **only** pursue if we add a
  single-file-image output mode.

**P4 — Config alignment (minor).**
Optionally align overread to EAC's setting; expose it. Low value (audio matched).
**✅ Done 2026-07-21:** Settings → Overread, off by default, which is EAC's setting.

**P5 — Single-file image + cue (future, large).**
EAC's image+cue mode isn't supported by cyanrip (one FILE per track, no image
mode). Would need a different tool or post-assembly. Only justified if users want
a burnable disc image; revisit through the fork (KDD-32). Still open.

### Bottom line

- **Audio parity with EAC has been reached, but it is not yet repeatable, and on
  track 5 it is not the right target** (status 2026-10-07; TL;DR, item 1). 14/14
  equal to EAC first on 2026-08-04 on the fork (`output_reference/
  cyanrip_fork_flac/`, asserted by `tests/test_fork_rip_eac_parity.py`), and in
  four rips since; 13/14 on the latest whole-disc run. EAC's track 5 is not the
  AccurateRip consensus; the verified read, `C96464AB`, was reached once, by the
  2026-10-07 secure re-read. CUETools-class repair (P2(b)) stays the power-user
  escape hatch. The 12/14 figures above are the dated stock-0.9.3 record
  (`cyanrip_flac/`), still pinned by `tests/test_parity.py`.
- **File-byte identity with EAC is impossible across encoders and is the wrong
  goal** — lossless audio + AccurateRip CRC is the archival standard, and we meet
  it where the disc allows.
- **EAC-style pre-gap cue markers are a metadata nicety**, and only matter for
  disc-image use (P3/P5). On **stock cyanrip 0.9.3** they are blocked on pre-gap
  detection; the Platterpus fork detects pre-gaps and emits `INDEX 00`
  (`docs/handshake/artifactsround31/round31fullwholedisc.cue`).

---

## Part B — Log format, field by field: cyanrip vs EAC

## Rip log format: cyanrip vs EAC

The brief promises "EAC-equivalent archival quality" — so the rip log should be a reasonable archival substitute for EAC's. This document compares the two formats field-by-field, identifies what each captures, and notes the small gaps.

**History:** this document originally compared the previous backend (the ripper Platterpus used before cyanrip, whose log is now read as the *legacy log format*) vs EAC. That backend was removed on 2026-06-30 (KDD-18) in favour of **cyanrip**, which is now the sole ripper. It was refreshed to cyanrip vs EAC in the post-0.4.5 session. The earlier comparison is preserved in git history if ever needed.

> **Status (2026-10-07).** The cyanrip column below quotes **stock cyanrip 0.9.3**
> (`output_reference/cyanrip_flac/`). The Platterpus fork's log, the one the app
> installs, prints more (`+platterpus.21`, `docs/handshake/artifactsround31/
> round31fullwholedisc.log`): `Handshake:`, `Consumer:`, `Invoked as:`, `Drive
> used:`, `Encoder:`, `Retry limit:`, `Cache model:`, `CD-TEXT:`, per-track
> `Pregap length:` / `Pregap source:`, `Extraction speed:`, `Elapsed:` and `Secure
> re-read:`, and at the end `Encoder errors:`, `Read stalls:` and `Rip completed:`.
> The rows corrected for the fork say so; the rest describe stock 0.9.3.

### Where the reference material lives

- `output_reference/EAC_flac/eac_baseline_police_classics.log` — a **genuine** EAC V1.8 log of the reference disc (UTF-16, verbatim). The comparison baseline since 2026-06-27.
- `output_reference/cyanrip_fork_flac/` and `docs/handshake/artifactsround*/` — real logs from the Platterpus fork, with our EAC-layout export of each beside it.
- `rip_log_eac_reference.log` (`tests/fixtures/`) — a representative EAC v1.6 log. Hand-authored to match the format documented on the Hydrogenaudio and CueTools wikis. **Not** used by the parser; stored for reference.
- cyanrip's exact format strings are pinned in the parser docstring and regexes at `src/platterpus/parsers/cyanrip_log.py`, verified against cyanrip master `src/cyanrip_log.c` (cyanrip 0.9.3.x). The parser tests (`tests/test_parsers_cyanrip_log.py`, plus the never-raises property test in `tests/test_parsers_property.py`) carry inline cyanrip log samples.

### Field-by-field comparison

#### Archival header (drive + settings)

| Field | EAC | cyanrip | Notes |
|---|---|---|---|
| Tool version | `Exact Audio Copy V1.6 from 23. November 2020` | `cyanrip 0.9.3.1 (...)` | Both clearly identify the ripping tool + version. **Our EAC-compatible export does not copy EAC's first line, not even its first words.** It opens `Platterpus rip log in EAC's layout, not produced by Exact Audio Copy`, then names the cyanrip build on the lines below. Platterpus 0.6.62 and earlier opened `Exact Audio Copy-compatible log generated by Platterpus`, and a tool that sniffs a log's format from its first words, as our own parser did, filed that as an EAC log (handshake round 28 lap 7 S28-S32; the fork accepted the change in round 29 lap 1 S31). Our parser still recognises both wordings as ours (`parsers/eac_log.eac_log_producer`), because users hold logs written with the old one. This is provenance, so it is one of the two places the export stays deliberately un-EAC-like; the other is the checksum footer (KDD-24, KDD-36). |
| Date | `EAC extraction logfile from 16. October 2023, 14:30` | a timestamp line, e.g. `2026-06-27T11:18:26` (stock) or `2026-10-07T00:30:17-04:00` (fork) | Both stamp the rip. Stock cyanrip logs no run time; the fork logs each track's `Extraction speed` and `Elapsed`, which our export renders as `Extraction time`. Platterpus also puts the real elapsed and a realtime multiplier in the JSON report. |
| Drive identification | `Used drive  : PIONEER BD-RW BDR-209D   Adapter: 1  ID: 0` | stock: `Device model:   PIONEER  BD-RW   BDR-209D 1.51 SCSI CD-ROM`; the fork adds `Drive used:     PIONEER  BD-RW   BDR-209D (revision 1.51)` | EAC includes adapter/ID; cyanrip includes firmware revision. **Roughly equivalent.** The parser accepts both lines. |
| Extraction engine | (implicit in EAC binary) | stock: none; the fork: `Encoder: libavformat …, libavcodec … (8.1.2)` | The fork names its FFmpeg libraries; libcdio-paranoia's version is still not printed. We do not render the `Encoder:` line yet (`TASKS.md`). |
| Read mode | `Read mode : Secure` | `Paranoia level: max` | Our export renders `max` as `Secure`, and `none` as `Burst` (`eac_log_export.py`). cyanrip can run with `-P none`; Platterpus never passes `-P`, so it is always `max`. |
| Read offset correction | `Read offset correction : 667` | `Offset:         +667 samples` | Equivalent. cyanrip applies the offset itself (no >587 cd-paranoia bug, which the previous backend had), and prints the sign explicitly. |
| C2 pointers | `Make use of C2 pointers : No` | `C2 errors: <text> by drive` | **Parsed since v0.5.12** (`_C2` → `RippingInfo.c2_pointers`). Note the two lines ask different questions: cyanrip reports what the *drive can do*, EAC's row what the *rip did* — so `unsupported`/`disabled` renders a truthful `No` and an affirmative capability renders as unknown rather than a fabricated `Yes`. Per-sector C2 *counts* remain unexposed — see `docs/cyanrip-fork.md Part A §8`. |
| Gap detection | `Gap handling : Appended to previous track` | `Gaps:` block | Parsed to `RippingInfo.gap_detection`, and our export renders it into EAC's `Gap handling` row. |
| Per-track pre-gap | `Pre-gap length  0:00:02.00` | stock: `Pregap LSN: N`; the fork: `Pregap LSN: 0 (duration: 00:02.00)`, `Pregap length: 150 frames`, `Pregap source: …` | `Pregap LSN` is a position, not a length; the length comes from the fork's `Pregap length:`. Parsed to `TrackResult.pregap_sectors` and rendered in the EAC-layout export. |
| Per-track sector range | (implicit in the TOC table) | `Start LSN:` / `End LSN:` | Parsed to `TrackResult.start_sector`/`end_sector`; they build the EAC-layout TOC table. |
| Cache defeat | `Defeat audio cache : Yes/No` | stock: none; the fork: `Cache model: 1200 sectors (drive cache size not probed)` | **No cyanrip verdict.** The fork's `Cache model:` line is modelled, not probed, and we never fill this row from it; libcdio-paranoia *attempts* cache defeat (readahead exhaustion + FUA where supported) but never asserts success. Our EAC-style log export therefore renders `(unknown)` rather than a fabricated `Yes` — but the field is no longer *usually* unknown: **KDD-29** measures the drive's real cache-defeat behaviour with `cd-paranoia -A` and folds that verdict in, so a probed drive renders a measured `Yes`/`No` (hardware-confirmed `Yes` on the BDR-209D, 2026-07-26). KDD-25's "always unknown" position is superseded; the never-fabricate rule it was protecting is not. |
| Paranoia status counts | (not in EAC log) | `Paranoia status counts:` block (`SKIP: N`, `READ_ERROR: N`, …) | **cyanrip extra.** A per-status tally of how hard paranoia had to work — a useful marginal-disc signal EAC doesn't surface. |
| Disc audio duration | (implicit) | `Total time:     00:59:42.354` | cyanrip records the disc's audio length. The realtime multiplier uses the audio actually extracted when known, and `Total time` only as the fallback (`rip_report.py`). |

#### Per-track block

| Field | EAC | cyanrip | Notes |
|---|---|---|---|
| Track header | `Track  1` | stock: `Track 5 ripped and encoded successfully!`; the fork (from `.14`): `Track 5 read successfully!` | cyanrip opens the block with the outcome line. The fork moved the encode outcome to a disc-level `Encoder errors:` line. |
| Pre-emphasis flag | (not in EAC log) | `Preemphasis:   none detected` | cyanrip extra. Useful for archival pre-emphasis-encoded discs. |
| Duration | `... (per-track)` | `Duration:    03:51.44` | Both capture. |
| CRC | `Test CRC 0025D726` / `Copy CRC 0025D726` (two reads) | `EAC CRC32:     A1B2C3D4 (after 2 rips)` | **Different verification models.** EAC does a test read then a copy read and compares. cyanrip computes ONE EAC-style CRC32 per track and, with `-Z N`, re-reads until N+1 reads are identical — it records how many rips it took. Platterpus stores cyanrip's single CRC in `copy_crc` and leaves `test_crc` empty, so the fidelity summary can tell the two models apart. **In the EAC-compatible export** (KDD-30) a track whose reads *converged* is rendered as an EAC-style `Test CRC` == `Copy CRC` pair — convergence is the same two-reads-agree proof — while a track whose re-reads **hit the repeat limit** carries an explicit "not confirmed reproducible" caveat, worded by what its log proves about how many reads agreed (*The repeat-limit caveat*, below the table), and a whole-disc `Read stability :` line. A never-re-read track keeps a lone `Copy CRC`: we neither fabricate a test read nor imply doubt we didn't measure. Note the CRC is always the **shipped** file's: cyanrip's whole-disc log records the first pass, so when the auto-fix swaps in a re-read, that track's record is replaced with the re-rip's own (matching the auto-fix addendum, a sidecar file `<log stem>.platterpus-addendum.txt` beside cyanrip's log, which is left byte-exact so `cyanrip --verify-log` still passes — hardware-found 2026-07-26). The fork also prints each track's own `Secure re-read:` line. |
| AccurateRip v1 result | `Accurately ripped (confidence 14)  [95E6A189]  (AR v1)` | `Accurip v1:  12345678 (accurately ripped, confidence 3)` | Both capture the CRC + confidence; the primary bit-perfection proof on both tools. |
| AccurateRip v2 result | `Accurately ripped (confidence 11)  [113FA733]  (AR v2)` | `Accurip v2:  9ABCDEF0 (not found, ...)` | Same structure as v1. |
| Frame-450 ("offset-variant") match | (not distinctly labelled) | `Accurip 450: BF62B1DA (..., track is partially accurately ripped)` up to `+platterpus.16`; `(..., one frame only; whole-track checksums not found)` from `.17` (`cyanrip@ec0fe47:src/cyanrip_log.c:625`) | **cyanrip extra.** The checksum of **one frame** (frame 450, six seconds in), printed only after both whole-track checksums missed (`cyanrip@df91ae7:src/checksums.h:74-78`, `src/cyanrip_log.c:594`). It is not a pressing: a shifted pressing moves frame 450 too, and a submitted pressing matches its own whole-track entry. Surfaced as "partially accurate", never as a verified match. Our screens and report say "only one frame matched" since 2026-09-24. Our EAC-compatible log says `Only one frame matched AccurateRip (confidence N); whole-track checksums not found  [CRC]  (AR frame 450)` per track and `N track(s) matched AccurateRip on one frame only` in its summary, the words agreed with the fork in round 27 (round 7 lap 11, H4: neither side rewords this log alone). |
| Per-track loudness (ReplayGain / R128) | (not in EAC log) | `REPLAYGAIN_TRACK_GAIN: -4.10 dB` / `R128_TRACK_GAIN: 229` | **cyanrip extra**, written into the FLAC tags and captured in the report. |

##### The repeat-limit caveat (2026-10-05)

EAC never prints any of these sentences. They are ours, in the two places our
export already words this state itself: a parenthetical on the `Copy CRC` line and
the per-track verdict line that replaces `Copy OK`. Until 2026-10-05 every track
that hit the limit read *"re-reads did NOT agree"*, which was false of the round-28
Full run's track 5: two of its three reads agreed
(`docs/handshake/artifactsround28/round28fullsecurereread.log` lines 381-385, beside
the app's own export of it, `round28fullsecurerereadeac.log` line 126). The limit
means *not enough* reads agreed, never *none did*. So the words now follow what the
log proves (`eac_log_export._reread_shortfall`, from
`TrackResult.secure_rerip_agreement`):

| What the log proves | Copy CRC parenthetical | Committed example |
|---|---|---|
| no two reads agreed (the fork's `at most 1 read agreed`, or `-Z 1`) | `re-reads did NOT agree — this read is not confirmed reproducible` (unchanged) | round 30, 10-05 secure re-read, track 3 |
| the largest group of agreeing reads, exactly | `re-reads did not converge; at most 2 of 3 reads agreed — …` | round 28 track 5, round 26 track 5 |
| only a floor under it (old wording, short of the `-Z` target) | `re-reads did not converge; at least 2 of 4 reads agreed — …` | none committed |
| nothing (old wording, no read matched before the last) | `re-reads did not converge — this read is not confirmed reproducible` | round 27 track 3 |
| **our time limit** stopped the reads (the fork's PROPOSED `--reread-time-limit`, round 36 lap 10 S11; not built, not sent) | `re-reads stopped at our time limit of 600 s before they converged; at most 2 of 4 reads agreed — …`, the count only when two or more agreed | none: no build prints it (`tests/test_reread_time_limit.py` builds the case from S11's text) |

The verdict line reads `Copy NOT confirmed — re-reads did not converge, so this
track is not verified reproducible`, one wording for the first four, since *did not
converge* is the `-Z` verdict itself. A track **our time limit** stopped reads
`Copy NOT confirmed — re-reads stopped at our time limit before they converged, …`
instead, and its own `Read stability` line says *a limit we set, not a finding about
the disc*: the first read always runs and the clock can stop a track after it, so
*did NOT agree* or *did not read identically* would blame the disc for our setting.
The limit is read by `reread_limit.py`; the words go to the fork in our next lap,
since they diff this log. *At most* is the fork's own word for the exact
count, so their line and ours say the same thing about one track.

**The parity reasoning.** (1) Nothing EAC-shaped was added: no new line, no new
field, and none of the strings a logchecker keys on (Part D §2). `Copy OK` (the clean
verdict) and `Copy aborted` (an automatic zero) stay out of the track block.
`tests/test_eac_log_export.py::test_the_repeat_limit_sentences_stay_out_of_eacs_vocabulary`
asserts it on the three committed cases, and asserts that the `Copy CRC` still reads
back through our own EAC-log reader. (2) We deliberately do **not** print a
`Test CRC` from the reads that agreed, although the old-wording log prints their
checksum. A `Test CRC` asserts EAC's two full passes, which never ran. On round 28's
track 5 the kept read is the last one (the fork's round 29 lap 1 S35), and it is not
one of the two that agreed. *(From `+platterpus.20` the fork keeps the read most
reads agreed on (cyanrip@ca3f3ea:src/cyanrip_main.c:835-845), so on current builds
this reason is gone and the refusal rests on reason (1): EAC's two passes never ran.)* So the pair would print EAC's *Test ≠ Copy* state, which
checkers deduct 30 per track for, about a different procedure. And the checksum
cyanrip printed for those reads is the complement of the CRC on builds before
`9669d84` (S34), so the number would be wrong on every older log. (3) The *at least /
at most* split is not cosmetic. Round 27's track 3 shows why a floor of 1 must not be
read as *none agreed*: its last read did match its second (EAC CRC32 `59D352DD` is
the complement of the second read's printed `A62CAD22`), and the old sentence said
otherwise.

##### The skipped-read verdict (2026-10-05)

A track libcdio-paranoia **skipped** on (`SKIP` above zero in its per-track
`Paranoia status counts:` block: paranoia gave up verifying a read and kept what it
had) that AccurateRip did not confirm now reads

> `Copy NOT confirmed — the ripper could not verify every read and AccurateRip did not confirm the audio`

where it read `Copy OK`. Track 18 of the 2026-10-04 rig run is the case: 2,586 skips,
AccurateRip matching one frame only, and `Copy OK` under it
(`docs/handshake/artifactsround30/round30oct04fulleac.log` lines 298-310). cyanrip's
`Ripping errors:` counts only reads that failed outright, so the disc still says
`No errors occurred`. The words are ours, proposed in our round 30 lap 8 S20 and
accepted by the fork in their lap 9 S26: this log is what they diff against, so
neither side rewords it alone (round 7 lap 11, H4). The test is the shared predicate
`verdict.track_has_unverified_skips`, the one the results pane reads, so the two
surfaces cannot disagree about which tracks it names. A skipped track with an exact
AccurateRip match keeps `Copy OK`: the match proves the audio however it was read.
A one-frame match does not.

**When a track was skipped on and also hit the repeat limit, the skip takes the
verdict line.** The re-read shortfall stays on the `Copy CRC` line in its own words,
and the `Read stability` line names the track, so both facts stay in the block. The
other order would say *did not converge* twice and the skip nowhere.

**The parity reasoning.** It is the same move as the re-read verdict: an EAC verdict
we cannot honestly print, replaced by a sentence of ours on the same line. It does
not contain `Copy OK`, so no mechanical reader takes it for EAC's clean verdict, and
it does not contain `Copy aborted`, which checkers score as an automatic zero (Part D
§2). We do not imitate EAC's own per-position way of marking a doubtful read: cyanrip
reports how many skips a track had, not where they were.

#### Summary / status report

| Field | EAC | cyanrip | Notes |
|---|---|---|---|
| Overall AccurateRip outcome | `All tracks accurately ripped` | `Tracks ripped accurately: 15/16` | cyanrip gives an explicit count; a partial-accurate line (`Tracks ripped partially accurately: N/M`) is separate. |
| Error summary | `No errors occurred` | `Ripping errors: 0` | Platterpus normalises cyanrip's "0 errors" to EAC's "No errors occurred" phrasing so downstream checks behave the same. |
| Album loudness | (not in EAC log) | `Album Loudness Summary:` block (`I: … LUFS`, `LRA: … LU`, `Peak: … dBFS`) | **cyanrip extra.** Whole-disc integrated loudness / range / true peak — a genuine archival bonus EAC has no equivalent for. |

#### Log integrity

| Aspect | EAC | cyanrip | Notes |
|---|---|---|---|
| Footer | `==== Log checksum <HEX> ====` | `Log FUN512: <base64>` | Both tools sign their own log. EAC's checksum is a widely-recognised forensic signal in the archival community (its log-verify tool + CTDB accept "EAC-verified logs"); cyanrip's `Log FUN512:` is its own analogue but is **not** recognised by those third parties. Platterpus checks it on every rip by running `cyanrip --verify-log` (`adapters/ripper_log_verify.py`; the report's `ripper_log_verification`), and our EAC-layout log carries its own openly verifiable SHA-256 footer (KDD-28). The third-party-recognition gap is real and **not actionable from the GUI side**. |

### What Platterpus adds beside the log

Platterpus never *rewrites* cyanrip's `.log`/`.cue` — those stay the EAC-parity, human-facing archival record, named after the album. It writes **one** companion next to them by default (a second, optional `<Album> (EAC-compatible).log` appears when the Settings toggle `write_eac_log_after_rip` is on — off by default; `eac_log_export.py`). When the auto-fix replaced a track, `<log stem>.platterpus-addendum.txt` sits beside cyanrip's log too, and a securing pass leaves `<Album>.platterpus-securing-pass.txt` (`rip_addendum.py`), and the verified-read chase leaves each of its single reads' logs in `<Album>.platterpus-verified-read.txt` (`verified_read_chase.py`, TASKS R7):

- **`<Album>.platterpus.json`** — the single machine-readable / LLM-oriented rip report: the parsed verdict, per-track AccurateRip, the full post-rip verification suite (AccurateRip + CTDB + FLAC-integrity, plus derived-file verification for MP3/WavPack/WAV), per-file SHA256 digests, timing + realtime multiplier, album loudness, the read-speed-ladder history, the verbatim text of the artifacts it read (`artifacts`), the `cyanrip --verify-log` result (`ripper_log_verification`), **and this rip's embedded session log** (`debug.lines`, scoped to this album).

The album folder therefore holds: the audio, the front cover, cyanrip's EAC-style `<Album>.log`/`<Album>.cue` (for humans), the `<Album>.platterpus.json` (for machines/LLMs/debugging), and — only when the toggle above is on — the optional `<Album> (EAC-compatible).log`. The *rationale* for this split — two audiences, two artifacts; why there is deliberately **no** plain-text `.platterpus.log` sidecar; how the global `~/.local/share/platterpus/log.txt` divides the work with the JSON's embedded log — is owned by [`architecture.md` §3.7](architecture.md) ("Two audiences, two artifacts"); this doc records only *what* sits beside the rip.

### Verdict on EAC-equivalence

**Archival content: equivalent, and richer in places.** Every field EAC captures that bears on whether the rip is bit-perfect (drive, offset, per-track CRC, AccurateRip confidence v1+v2) is captured by cyanrip too. cyanrip *additionally* records paranoia status counts, pre-emphasis, per-track + album loudness (ReplayGain/R128), and the frame-450 one-frame match — none of which EAC logs.

**Log integrity: EAC is still stronger by reputation.** Both tools sign their logs, but EAC's checksum is a trusted forensic signal to third parties (CTDB, the audiophile community) in a way cyanrip's `Log FUN512:` is not. This is a real gap but not closable from the GUI side.

### Implications for the GUI

1. **The `RippingInfo` block on `RipLog` mirrors EAC's archival header** (drive/offset/etc.), so it can feed the EAC-layout export and the report. *(No "Rip details" panel exists, as of 2026-10-07; the disc-info panel shows drive, offset and cache from the drive profile instead.)*
2. **The per-track display** renders cyanrip's AR v1 / v2 confidence the same way EAC does, and the results pane now also surfaces the album loudness + partial-accurate count that cyanrip uniquely provides.
3. **We offer an optional EAC-*layout* companion log (v0.4.16)** — the Settings toggle `write_eac_log_after_rip` (off by default) writes `<Album> (EAC-compatible).log` beside the rip, rendered by `eac_log_export.py`: conspicuously attributed and **never signed** as EAC (signing would forge provenance — KDD-11/KDD-24, `docs/eac-parity.md`). Linux still can't submit to AccurateRip (the brief's confirmed gap).

### How this was verified

- cyanrip format: pinned against cyanrip master `src/cyanrip_log.c` in the parser (`src/platterpus/parsers/cyanrip_log.py`); several fields (`Device model:`, the loudness block, `Log FUN512:`) were corrected from **real Pioneer BDR-209D rip logs** captured during 0.4.5 testing.
- EAC format: cross-referenced against the Hydrogenaudio Knowledgebase EAC article and CueTools' AccurateRip log parser documentation, both stable public references.

If a future cyanrip version changes its log format, update both this document and the cyanrip parser tests together.

---

## Part C — Tracker acceptance, and in-app CTDB repair

## Feasibility: EAC-log tracker-acceptance & in-app CTDB repair

**Status:** research (2026-06-28) — **decided**: §1 resolved per **KDD-24**
(tracker acceptance out of scope by design; option 1 is the standing path,
option 2 shipped v0.4.16, option 3 documented-not-pursued; the signing path is
permanently closed — TASKS.md closed the signed-checksum item). §2 (repair) was
**decided 2026-07-21 (KDD-14, "D → B")**: no bundled .NET; in-app repair waits for a
user who needs it, and then arrives as an optional user-installed `ctdb-cli` through
the dependency subsystem. Its CRC gate cleared 2026-07-07 (KDD-16). Originally: research / decision-gated, no
code written. This is
the write-up the EAC-parity brief asked for ("investigate the LOG-trust path"
and "scope/evaluate an in-app CUETools/CTDB *repair*") so the maintainer can
decide before any implementation. It pairs with
**Part A — Can our output be bit-identical to EAC?** (the audio-parity
plan) and answers the two questions that investigation deferred.

---

### Part C §1 — Can we make our rips *tracker-accepted* by emitting an EAC log?

#### The decisive finding (added 2026-07, research session): the block is ripper identity, above the audio layer

Before any of the checksum discussion below, there's a harder wall: the
gazelle logcheckers (OPSnet's/orpheusnet's PHP logchecker; RED's EAC/XLD +
Python `eac_logchecker` for the checksum) score a log by **which program
produced it**, not by whether the underlying audio is bit-perfect. Their
ripper allow-list is **EAC, XLD, and the previous backend ≥ 0.7.3** (the ripper
Platterpus used before cyanrip) — full stop. An
unrecognized ripper, including **cyanrip**, is hard-set to score **0 /
rejected** before the checker ever looks at read quality, AccurateRip
confidence, or anything audio-related.

That matters for how to read everything below: there is **no honest partial
ceiling** to aim for. A cyanrip log with perfect AccurateRip confidence and a
flawless extraction still scores exactly the same as a garbage rip — zero —
because the gate is identity, not quality. "Get closer to tracker-accepted" is
not a spectrum we can climb by improving the rip; it's a binary allow-list we
are not on. This reframes §1 from "how close can we get" to "this is
categorically out of scope by design" — see PLANNING.md **KDD-24** for the
full record.

**Two corrections to the maintainer's 2026 ripper-landscape research doc**
surfaced while researching this — (1) the previous backend plus its EAC-logger
plugin does **not** genuinely satisfy RED (the plugin hits the same EAC-checksum
wall described below), and (2) the "logchecker-go (pure Go)" characterization
is unverified and not load-bearing (the verifiable fact is the scoring
mechanics). The full text of both corrections lives in PLANNING.md
**KDD-24** — the designated record.

#### The constraint

Gazelle trackers (RED/OPS) accept **only EAC or XLD logs** — plus the previous
backend ≥ 0.7.3 at OPS. A cyanrip log — even with a valid AccurateRip result and
cyanrip's own FUN512 checksum — is **not** accepted.

> **Correction (2026-07-29):** an earlier version of this paragraph said the
> previous backend "still cannot clear RED's checksum requirement." That is wrong.
> OPS's checker validates that backend's checksum, which is a **plain SHA-256 of
> every line but the last** (`OPSnet/Logchecker`, `src/Check/Checksum/Whipper.php`) — the same
> primitive as Platterpus's own footer (a plain SHA-256 of the text above it), though
> not byte-compatible: OPS joins the lines with no trailing newline, and ours hashes
> every byte. The checksum wall is cleared there; what excludes
> cyanrip is *identity*, checked before any quality line is read, and Redacted's
> rules listing only EAC and XLD is a policy limit rather than a technical one.
> Details and the full requirement-by-requirement comparison: Part D below.

So "make the CD-archiving community fully trust our rips"
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
[the previous backend's EAC-logger plugin, issue #7](https://github.com/whipper-team/whipper-plugin-eaclogger/issues/7)
is exactly this: that backend *can* render EAC-shaped logs, but signing them to pass
as EAC is the line nobody legitimate crosses.)

That `eac_logsigner`'s README carries no ethics warning is irrelevant — the
**tracker rules**, not the tool, define the offence. And it collides head-on
with two of our own hard constraints:

- The brief: *"it must reflect REAL results — never fake a log/checksum."* An
  EAC-signed cyanrip log fakes the **provenance** even when the audio is real.
- The project ethos (see the honesty rules in `docs/ux-design-principles.md`
  and the verdict code in `verdict.py`): *"never claim a check that
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
   it renders our real `RipLog` into EAC's layout with a conspicuous header
   and footer saying EAC did not produce it (since 0.6.63 the first line reads
   `Platterpus rip log in EAC's layout, not produced by Exact Audio Copy`), never
   a fabricated EAC checksum; since KDD-28 it ends with our own SHA-256. The GUI wiring shipped in
   v0.4.16: the opt-in Settings toggle (*EAC-style log*,
   `write_eac_log_after_rip`, off by default) writes the attributed EAC-layout
   log beside each rip — option 2 is fully implemented.
3. **If tracker acceptance is genuinely required**, the only legitimate route is
   the *tracker* choosing to accept cyanrip (advocate upstream; OPS
   already maintains tooling in this space). We do not manufacture acceptance by
   signing. This is out of our hands by design.

**Decision gate — RESOLVED (KDD-24, 2026-07):** option **1** is the standing
path, option **2** shipped (v0.4.16 toggle), option **3** is documented, not
pursued. No code ever proceeds on the signing path.

---

### Part C §2 — In-app CUETools / CTDB *repair*

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
  (shipped 2026-06-28, and driven automatically by the securing pass since,
  `securing_pass.py`) converges most marginal tracks without any new dependency.
- **Document the manual CUETools/ctdb-cli repair workflow** as the authoritative
  fix for a stubborn "partially accurate (450)" track (a power-user escape
  hatch), pointing at the tools above. **✅ Written 2026-07-21:
  [`manual-ctdb-repair.md`](manual-ctdb-repair.md)** (assembled strictly from
  this doc + the investigation record; unexecuted steps marked unverified).
- **Gate an in-app repair** behind: (a) ~~the CTDB CRC hardware-validation~~
  **cleared 2026-07-07 (KDD-16)**, (b) ~~explicit maintainer appetite for the
  .NET/Mono dependency~~ **decided 2026-07-21 (KDD-14): no bundled .NET; an optional
  user-installed `ctdb-cli` when a user needs it**, and (c) repair-specific validation of the
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
  the open-trust choice, not gaps.** *(Status 2026-10-07: still no literal two-pass
  mode, but since KDD-30 a converged `-Z` read renders as a Test/Copy pair, with an
  optional whole-disc pass ("Verify every track with a second read"); and since
  KDD-28 the log carries our own SHA-256, never EAC's.)* A literal EAC-style Test&Copy (two full
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
  **cleared 2026-07-07 (v0.4.20, KDD-16)**; shipping was decided 2026-07-21
  (KDD-14: optional `ctdb-cli`, when a user needs it), and validation of the
  repair path itself remains.
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
| [OPSnet/Logchecker](https://github.com/OPSnet/Logchecker) (PHP; what OPS runs) — read at `ca565479`, 2026-05-31 | EAC, XLD, the previous backend ≥0.7.3 | `UnknownRipperException` → score **0**, "Unknown log file, could not determine ripper." (`src/Logchecker.php:121-124`) |
| [ligh7s/hey-bro-check-log](https://github.com/ligh7s/hey-bro-check-log) (Python; "aligned with Redacted standards" — **unmaintained since 2020-03-31**, read at `d3192ad2`) | EAC ≥0.99, EAC95, XLD | `UnrecognizedException` — and the version string must be in a hardcoded table |

Redacted's own rules name only EAC and XLD, and treat a log from any other tool as
trumpable ([rules](https://interviewfor.red/en/rules.html),
[ripping](https://interviewfor.red/en/ripping.html)).

**So: cyanrip, morituri, dBpoweramp, Rubyripper, CUERipper — not accepted.** The
previous backend is the sole non-EAC/XLD exception, and only at OPS.

**Our EAC-layout log at OPS takes a different path to the same 0** (read from
`ca565479` on 2026-10-07). OPS classes a log as EAC's if the string `Exact Audio
Copy` appears anywhere in it, or its first line contains `EAC`
(`src/Check/Ripper.php:18-26`). Ours does both, on purpose, to say EAC did not
produce it. It then reaches 0, "Unrecognized log file", only because it lacks EAC's
own line `EAC extraction logfile from` (`src/Logchecker.php:517-551`, matched
anywhere). We write `Extraction logfile from`, without the program name, and since
2026-10-07 a title cannot supply the phrase either (D16, widened; pinned by
`tests/test_eac_log_export.py`). **Never add that line**: it is the one thing
between our log and being graded as EAC's.

#### Checksums are not the barrier — identity is

Worth being precise, because it is easy to assume the opposite. EAC's footer is an
obfuscated Rijndael-256 fold under a reverse-engineered key
([eac_logchecker.py](https://github.com/OPSnet/eac_logchecker.py),
[eac_logsigner](https://github.com/puddly/eac_logsigner)). But **the previous backend's
checksum is a plain SHA-256 of every line but the last, and OPS validates it**
(`src/Check/Checksum/Whipper.php`).

Platterpus's own footer is *structurally the same scheme* a real tracker already
accepts. The only thing between them is the ripper's name — which is exactly the right
place for the wall to be.

---

### 2. What the checkers deduct for

Recorded because these are the *quality* criteria worth caring about even when the
score is unreachable. **From OPS's checker, `OPSnet/Logchecker` at `ca56547`
(2026-05-31, the newest commit on 2026-10-26), `src/Logchecker.php`**, each deduction
read at the line given (fetched 2026-10-26, sha256 of the file
`029c8bd8…6514d26`). A score starts at 100. These are the points an EAC log loses,
with the setting a clean rip uses:

| Log line | Required | Points off otherwise |
|---|---|---|
| EAC version | 0.99 or later (1.8 is current) | −30 when the version is 0.95 or older, or unstated (`:480-497`) |
| `Read mode` | Secure | −20 (`:1512`) |
| `Utilize accurate stream` | Yes | −20 (`:1734`); −20 when the line is missing from a secure-mode EAC log (`:639-640`) |
| `Defeat audio cache` | Yes | −10 (`:1757`) |
| `Make use of C2 pointers` | No | −10 (`:1790`) |
| `Read offset correction` | the drive's AccurateRip value | −5 (`:1818`) |
| `Fill up missing offset samples with silence` | Yes | −5 (`:1841`) |
| `Delete leading and trailing silent blocks` | No | −5 (`:1851`) |
| `Null samples used in CRC calculations` | Yes | −5 (`:1865`) |
| `Gap handling` | `Appended to previous track` | −10 for `Not detected` (`:1880-1882`), and −10 for `Appended to next track` or `Left out` (`:1883-1888`) |
| `Add ID3 tag` | No | −1 (`:1918-1923`) |
| Test & Copy (`Test CRC` beside `Copy CRC`) | on | −10 (`:1350-1351`); a further −40 when secure mode was not used either (`:1352-1361`) |
| Range rip | never | −30 (`:990`) |
| Virtual or null drive | never | −20 (`:1554`, `:1558`) |
| `Normalize to` | absent | −100 (`:1873`) |

**Per track:**

| In the log | Points off |
|---|---|
| `Test CRC` ≠ `Copy CRC` | −30 (`:1939`) |
| A suspicious position | −20 (`:1243`) |
| A timing problem | −20 (`:1263`) |
| Missing samples | −20 (`:1273`) |
| `Copy aborted` | −100 (`:1284`) |

**Score set to 0:** an unrecognised ripper (`:121-124`, §1); `Use compression offset`
(`:800-807`); an undecodable log (`:113-115`); a log with no tracks (`:2085`).

**Not deducted:** AccurateRip's results are only coloured (`:885-912`), so a log with
no AccurateRip line loses nothing for it. The log checksum is reported beside the score
as a status (missing, invalid, ok), not taken off it (`:413-433`, `:562`). Overread
into lead-in and lead-out is only coloured (`:705-706`).

**What this replaced (2026-10-26).** This section's table until 2026-10-26 came
mostly from [`ligh7s/hey-bro-check-log`](https://github.com/ligh7s/hey-bro-check-log),
**unmaintained since 2020-03-31** (§1), "cross-checked against the PHP" without line
numbers. Against OPS's own code it was wrong in six rows: C2 is −10, not −20; null
samples −5, not −1; a missing Test & Copy −10, not −20; `Not detected` gap handling
was absent, and is −10; AccurateRip −0, not −5; and the checksum is reported, not
−15. It also listed a virtual drive as an automatic zero, where OPS takes 20. Its
"unscoreable rather than deducted" list (a missing settings line, a track missing its
filename, peak or Copy CRC, a track count unlike the TOC's, an unknown version string,
a non-English log) is hey-bro-check-log's behaviour and has not been re-checked
against OPS. Found by the EAC parity plan of record of 2026-10-26 (§6), and each
line above re-read from the fetched file before it was written.

---

### 3. Where Platterpus stands, row by row

cyanrip flags from `_build_rip_argv`: `-d`, `-s <offset>`, `-o flac`,
`-T <sanitize mode>` (pinned since 0.6.24 — a default is not a contract),
`-r <retries>`, `-Z <matches>`, `-O` (only when force-overread is on),
`-S <speed>`, `-l <tracks>`, `-N`, `-c <disc>/<discs>`, `-a`/`-t`, `-D`/`-F`, `-G`,
`-U`, `-W`, `--diagnostics <record>` (`-j` until 2026-10-13), and `--consumer
<name>/<version>` and `--prefer-disc-isrc` on a build that accepts each (the
generated list: `docs/cyanrip-consumer-contract.md`). Notably **no `-p`** —
cyanrip's default already merges pregaps into the previous track.

| Requirement | Platterpus equivalent | Status |
|---|---|---|
| Secure read | libcdio-paranoia always; `paranoia_level` allow-listed | **met** |
| Defeat audio cache | *measured* via `cd-paranoia -A` (KDD-29), not asserted | **met when probed** |
| Delete silent blocks: No | asserted for cyanrip (it writes what it reads) | **met** |
| Null samples in CRC: Yes | asserted for cyanrip (CRCs matched a real EAC log, 14/14 tracks on the fork, 2026-08-04) | **met** |
| Gap handling | wording **actually** fixed 2026-07-30 (see below) — says "Not detected, thus appended to previous track" when the ripper signals none, and "Appended to previous track" when gaps are signalled (`eac_log_export.py`) | **met on the fork** (it detects pre-gaps); **wording met, detection is not** on stock cyanrip 0.9.3 |
| Test & Copy | `-Z` convergence rendered as a Test/Copy pair; a track at the repeat limit gets no pair, and a caveat saying how many reads agreed (Part B, *The repeat-limit caveat*) | **partial** |
| AccurateRip | parsed and rendered; `verdict.py` is the single predicate | **met** |
| No ID3 on FLAC | Vorbis comments only | **met** |
| Individual tracks (not a range rip) | cyanrip is always per-track | **met** |
| No normalization / compression offset | never emitted | **met** |
| Read offset correction | `-s` applied. Since 2026-10-21 the report (`rip.read_offset_check`) and the results pane assert it against the AccurateRip drive list for the drive the log names, with KDD-31's re-confirmation beside it (`read_offset_check.py`); the EAC-layout log still prints the value only, and its wording is proposed in TASKS P2 #6 | **partial** (report met; EAC-layout log open) |
| Fill missing offset samples with silence | derived from cyanrip's `Overread mode:` line, which stock and fork both always print (cyanrip@ca3f3ea:src/cyanrip_log.c:889-891); reads `No` under `-O` | **met** |
| `Make use of C2 pointers` | **`No`, measured** on a drive that reports C2 unsupported; "(not reported)" otherwise (see below) | **met on the rig; open in general** |
| `Utilize accurate stream` | no equivalent; from `.26` the row carries the drive's own declaration (`Accurate stream:`, MODE SENSE page 2Ah), worded as not determined and never as EAC's `Yes`, since a declaration is not a use (`eac_log_export._accurate_stream_row`, 2026-10-26) | **open** |
| Signed EAC log footer | plain SHA-256, self-labelled *not* EAC's | **by design** |
| Recognised ripper name | never emitted (KDD-11/24/28); our log names EAC only to disclaim it, and OPS refuses it for lacking EAC's first line (§1) | **by design → score 0** |

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
run sheet's cyanrip-`master` build step existed.

> **Status (2026-10-07): closed on the fork, still open on stock 0.9.3.** The fork's
> 2026-08-04 rip matches all ten of EAC's pre-gap rows (`tests/test_fork_rip_eac_parity.py`),
> and the hand-build step was retired: the setup wizard builds the pinned fork (KDD-33).

Until 2026-07-30 our exported row echoed cyanrip's "None signalled", which hid the
comparison entirely. It now reads EAC's own phrase for the not-detected case, so a
side-by-side diff against a real EAC log shows the difference instead of burying it —
and `test_gap_row_vocabulary_comes_from_a_real_eac_log_not_from_us` pins the
disagreement so nobody later "fixes" it by making the string match.

---

### 4. Ranked next steps, cheapest first

1. ~~**Earn the C2 row**~~ — **done 2026-07-30**: earned from cyanrip's own
   `C2 errors: unsupported by drive` header on the rig, not from the survey (*The C2
   row* above). Still "(not reported)" on a C2-capable drive, by design.
2. ~~**`Fill up missing offset samples with silence`** — plumb `force_overread` into the
   renderer~~ — **rejected (review finding, 2026-07-28)**: EAC's overread and
   fill-with-silence checkboxes are independent questions, so the flag cannot answer
   this row. It is read from cyanrip's own overread *mode* line instead, and stays
   "(not reported)" when that line is absent (`eac_log_export._fill_with_silence`).
3. **Assert the offset is *correct*, not merely applied** — the AccurateRip drive table
   is already in `adapters/accuraterip_offsets_data.py`, so the log can say
   `+667 (matches the AccurateRip database for PIONEER BD-RW BDR-209D)`. Genuine
   archival value: it turns a number into a checkable claim. ~40 lines.
4. **Investigate accurate-stream** — check whether `cd-paranoia -A` output carries a
   usable signal. May be a dead end; investigation before code.
5. **Do NOT build a legacy-log-format emitter.** It is the only technically-passing
   route, and it is the same forgery as EAC-signing: the ripper that format names
   did not do the rip.

   **Two additional arguments, added 2026-08-24 after reading the checker's own
   source** (`OPSnet/Logchecker` @ `ca565479`), because the second does not depend
   on ethics at all and is therefore the more durable one:

   * The gate is `if (strpos($log, "Log created by: whipper") !== false)`
     (`src/Check/Ripper.php:18`) — a **23-character substring**, checked before any
     quality rule runs. That it is trivially forgeable is precisely why doing it is
     unambiguous forgery rather than a grey area: there is no craftsmanship in
     which to hide an intention.
   * **The legacy-format rubric is 6 checks; the EAC/XLD rubric is about 30** — and
     the reason is that a legacy-format log does not *contain* the other 24 fields. Its
     ripping-phase block has seven rows: drive, extraction engine, cache defeat,
     read offset, overread, gap detection, CD-R. No read mode, no accurate-stream
     row, no C2 row, no gap-*handling* row, no null-samples row, no silent-blocks
     row, no ID3 row. So a perfect legacy-format log scores 100 having proven **less**
     than our cyanrip log already records. Emitting their format would mean
     **discarding evidence in order to score better on a rubric that checks
     less.** Field-by-field: ours is richer on 14 counts and poorer on 4, and two
     of the four are our own deliberate refusals (extraction-quality %, which
     the previous backend's own source concedes diverges from EAC's at
     `program/cdparanoia.py:150-153`; and the Test/Copy CRC pair, which `-Z`
     convergence supersedes and our export already renders honestly).

---

### 5. The honest framing

A 100% logchecker score certifies **process and provenance** — that a known program,
configured a known way, produced this log. It explicitly does not certify bit-perfect
audio; OPS's own README concedes that a sub-100% log can still be a perfect rip.

Platterpus makes a *different and narrower* claim, and it is a stronger one about the
audio itself: **provably bit-perfect, verified openly** via AccurateRip v1/v2 + CTDB
CRCs and per-track Copy-CRC parity against the committed EAC baseline in
`output_reference/EAC_flac/` (**14/14 on the fork** — `cyanrip_fork_flac/`,
2026-08-04, and in four rips since; 13/14 on the latest run, 2026-10-16, where
track 3 read differently from pass to pass. The dated 12/14 stock-0.9.3 record is
`cyanrip_flac/`. On track 5 EAC's value is not AccurateRip's consensus, so the
stronger claim is AccurateRip's, and that has been met on every track but never on
all fourteen in one rip: Part A, TL;DR item 1).

That is the goal to keep. "Tracker-acceptable" is not reachable and should not be
chased.

#### A correction this part made to Part C

Part C originally said the previous backend "still cannot clear RED's checksum
requirement." That is wrong, and Part C now carries the fix inline — see its
**Correction (2026-07-29)** note. OPS's checker **does** validate that backend's plain SHA-256, so the checksum wall is cleared
there. The accurate statement is that *Redacted's rules* list only EAC and XLD — a
policy limit, not a technical one.

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

## Part E — Independent audit against EAC (2026-10-19)

**Asked by the maintainer, 2026-10-19:** *"you are supposed to be the same or better
than EAC… can you do a complete 3rd party audit and make sure you are at least as good?
… give why you are worse or better, make sure there is evidence."*

**How it was done.** Parts A to D were not taken as evidence. Every number below was
re-derived from a primary artifact: the three genuine EAC 1.8 logs in
`output_reference/EAC_flac/`, `EAC_mp3/` and `EAC_wav/`, the 262 rip logs filed on the
`evidence` branch (fetched blobless from evidence commits `c737fb6b`, `f57cdc2b` and `fe13de0c`, read-only, never into the working clone), the
Platterpus source, and the cyanrip fork's source at the pinned commit `891c79e`
(`src/platterpus/deps/fork_source.py:270`). Where a claim rests only on a document, it
says so.

> **Updated 2026-10-20**, after an independent check of this audit by the
> claude-code-skills session (its report of 2026-10-19 22:10 UTC, findings P1 to P8)
> and the work `main` did the same day. It re-derived every number here and found
> them right. What changed: the serious gap in E3 is built and closed on `main` for
> the next release (TASKS R38); CTDB no longer shows green for a match against a
> minority entry (TASKS R34, in 0.7.110); the verdict-honesty claim in E1 and E5 is
> narrowed to what is true (P3); the pre-gap row in E4 holds for 23 of 26 rips, not
> all (P5); times copied from a log keep their zone (P8). The audit's grades as first
> written stay visible where they changed, so the change can be read.

### E1. The answer, first

**On getting the audio right, we are level with EAC on the one drive and disc where the
two can be compared. We are better at telling the user the truth about a rip, and at
checking the files afterwards. We are worse in five places, none of them in reading the
audio. And "at least as good as EAC" is not proven yet, because every rip on record
comes from one drive and one machine.**

When this audit was written (2026-10-19) it said six places, and one serious: a disc
AccurateRip does not know got one read and no second check. That one is built and
closed on `main` (2026-10-20, TASKS R38) and ships in the next release; 0.7.110 and
every earlier release still read such a disc once (E3).

| Area | Grade | One-line reason |
|---|---|---|
| Reading the audio correctly | **Equal** (one drive) | EAC verified 13, 11 and 12 of 14 tracks in its three sessions; we verified 12 or 13 of 14 in each of 26 (E2) |
| Proof when AccurateRip has the disc | **Better** | A track that fails AccurateRip is re-read automatically until reads agree; EAC leaves the re-rip to the user |
| The proof each track has, shown | **Better** from 2026-10-26 | EAC's one proof is a Test and Copy CRC pair. Ours varies by track, and the plan of record's row 9 asked that each track say which: every EAC-layout block now carries a `Proof:` row (`AccurateRip v1 at confidence 129 and v2 at confidence 200`; `a single re-read that AccurateRip verifies (…), kept in place of a read it did not verify`; `the secure re-reads agreed (converged after 3 reads), and AccurateRip has no entry for this track, so this shows the drive read it the same way each time, not that the audio is right`; or `none — …` with the reason), and the report carries the same line per track with CTDB's per-track answer, which the log is written too early to hold (`track_proof.py`, `tests/test_track_proof.py`) |
| Proof when AccurateRip lacks the disc | **Equal** from the next release; **Worse** in 0.7.110 and earlier | Every track is read again with `-Z` and the result is named "Reads agree … not verified by AccurateRip", as EAC's Test & Copy reads twice; until 2026-10-20 the default read each track once (E3, TASKS R38) |
| Honesty of the verdict | **Better** (from 2026-10-26; before, equal over a stable wrong read) | Where re-reads disagree, our log prints `Copy NOT confirmed` and a read-stability line; EAC printed `Copy OK` over tracks whose Test and Copy CRCs differed. Over a stable read AccurateRip contradicts, EAC prints `Copy OK` and `No errors occurred`; ours did too until 2026-10-26, and now prints `Copy finished`, a `Proof: none — WRONG` row and `There were errors` (the plan of record's row 8; E5) |
| File integrity after tagging | **Better** | `flac --test` on the finished files, SHA-256 per file, derived formats re-verified |
| CTDB | **Worse**, narrower | Per track and over every offset CTDB accepts, from the next release (2026-10-21, TASKS R43); EAC's plugin also locates the bad samples and submits, which we do not. A match against a minority entry is amber, not green, from 0.7.110 (E5, TASKS R34) |
| Error location | **Worse** today | Skip counts per track, no positions, in the build users get; the fork's tip adds positions |
| Cue sheet | **Worse** today | Pregaps match EAC in 23 of 26 rips, track 9 one frame off in 3 (E4); ISRCs are MusicBrainz's, not the disc's (TASKS R20) |
| Odd discs (HTOA, Enhanced CD, image + cue) | **Worse** | HTOA and image mode absent; data tracks copied by default (R12; the verdict's miscount, R13, fixed 2026-10-21) |
| Contributing back (AccurateRip, CTDB) | **Worse** | No AccurateRip submission, and whether one is possible from Linux is unverified (2026-10-26: AccurateRip's own list names five programs and does not say it refuses others; PLANNING.md KDD-12's dated correction); CTDB submission not built (Part F rows 13 and 14) |
| Tracker acceptance | **Worse, by design** | Logcheckers accept EAC and XLD by name (Part D); not chased |
| Diagnostics in the record | **Better** | Paranoia counts, loudness, per-track speed, JSON report, session log |
| Platform, cost, auditability | **Better** | Native Linux, open source, offset and settings chosen for the user |
| Breadth of proof | **Worse** | One drive model, one machine, one distro, two discs, against EAC's twenty years |

> **Updated 2026-10-26.** The EAC parity plan of record of that date grades 34 regards
> against EAC (Part F §F3). Nine of them had no row in this part, and now do: keeping a
> right read once found (F row 2), a damaged disc (5), CD-R detection (23), a drive blip
> mid-rip (33) and the speed of a clean rip (34) in E4; saying a wrong track is wrong
> (8), the proof each track has (9), CTDB submission (13) and AccurateRip submission
> (14) in E5. Accurate stream is re-graded in E4. Those rows use the plan's grades:
> **Better** and **Equal** are the goal reached, **Behind** can be reached and the row
> says how, **Not possible** gives the reason.

### E2. Extraction accuracy — the head-to-head on the reference disc

The reference disc is The Police, *Every Breath You Take: The Classics*, in a Pioneer
BDR-209D at +667. It is the only disc both tools have ripped on the same drive.

**EAC, three sessions** (Test & Copy, secure mode, accurate stream, cache defeat on):

| Session | AccurateRip-verified | Tracks that failed | Test CRC ≠ Copy CRC | Speed |
|---|---|---|---|---|
| 2026-06-11 (`EAC_flac/`) | 13 of 14 | 5 | none | 1.6–3.5× |
| 2026-06-25 18:09 (`EAC_mp3/`) | 11 of 14 | 3, 4, 5 | 3, 4 | 3.3–9.1× |
| 2026-06-25 18:42 (`EAC_wav/`) | 12 of 14 | 3, 5 | 3 | 3.4–9.0× |

`EAC_flac/eac_baseline_police_classics.log` holds the 06-11 session twice, one minute
apart; it is one rip, counted once here. The session times are as EAC printed them
(`EAC extraction logfile from 25. June 2026, 18:09`): EAC's logs carry no time zone, so
none is given. Our exports stamp one (`(UTC-04:00)`), and a time copied from them below
keeps it or gives UTC.

**Platterpus, 26 rips** (2026-08-04 to 2026-10-16; every 14-track EAC-layout export on
`evidence` plus `output_reference/cyanrip_fork_flac/`; one row per shipped album):

| Track | Result over 26 |
|---|---|
| 1, 2, 4, 6–14 | the AccurateRip value at confidence 200, all 26 times |
| 3 | AccurateRip's `59D352DD` 9 times; 15 different values in all; none since 2026-09-30 |
| 5 | AccurateRip's `C96464AB` once (2026-10-07 secure re-read); EAC's unverified `E0036697` 17 times; `6902BCF0` 7; `4065BECC` 1 |

So every rip verified 12 or 13 of 14: 13 in ten rips, 12 in sixteen. **Part A's TL;DR
numbers all re-derive exactly** (the method is in the 2026-10-19 session-log entry).

**What the comparison shows:**

- **Neither tool reads tracks 3 and 5 reliably on this drive.** EAC read track 3
  correctly in 1 of 3 sessions; we did in 9 of 26. EAC never read track 5 correctly; we
  did once.
- **The wrong reads are the drive's, not the ripper's.** EAC's wrong track-3 copies
  `418F6CF8` (`EAC_mp3/…log:86`) and `329DC760` (`EAC_wav/…log:86`) are byte-for-byte
  values our ripper also produced. Our 2026-10-07 securing pass read `418F6CF8` three
  times in a row and accepted it as converged
  (`docs/handshake/artifactsround31/round31fullwholediscsecuringpass.txt:57-63`). Our
  whole-disc rip of 2026-10-06 02:48 UTC (10:48 PM EDT, Mon Oct 5; the export stamps
  `5. October 2026, 22:48 (UTC-04:00)`) shipped `329DC760`
  (`docs/handshake/artifactsround30/round30oct06fullwholedisceac.log`, filed under the
  UTC date). Two different programs got the same wrong bytes, so the drive gives back the
  same wrong data on that track. That is a systematic misread, and no software on this
  drive can beat it except by luck.
- **Track 4 goes our way.** EAC misread it once (`EAC_mp3/…log`, Test `60D796AE`,
  Copy `1D0079A1`). We read it right 26 times out of 26.
- **Agreement is not correctness, for either tool.** EAC's Test and Copy agreed on the
  wrong track-5 value in all three sessions, and its CTDB plugin found that read 3
  samples off at 02:24:59 (`EAC_flac/…log:264`). The two 06-25 sessions give the whole
  row: `(  2/1443) Accurately ripped, or (1341/1443) differs in 3 samples @02:24:59`
  (`EAC_mp3/…log:264`, `EAC_wav/…log:264`). So two CTDB entries carry that misread,
  and EAC's 06-11 log records submitting its rip to CTDB (`EAC_flac/…log:258`). That
  first half of the row is the evidence that a CTDB match of ours on this disc can be
  our own misread echoed back (E5, TASKS R34). Our `-Z` re-reads also "converged" on
  wrong values: track 3 on `3D8FCF0C` after 3 reads
  (`docs/handshake/artifactsround30/round30fullsecurereread.log:263-264`), and track 5 on
  `E0036697` again and again. Our securing pass accepted EAC's own wrong `418F6CF8` after
  three identical reads (above). Only AccurateRip and CTDB catch this, in both tools.
  **Built 2026-10-21, not yet run on hardware (TASKS R7):** when the read we keep
  fails AccurateRip on a disc it holds, and the drive returned more than one value
  for the track, we now read it again singly, up to `-r` times (at most 5), and keep
  the first read AccurateRip verifies; EAC keeps its Test/Copy pair whatever
  AccurateRip says. It would have kept the 2026-10-12 securing pass's one
  `C96464AB` read, had a later single read reproduced it. It cannot help a misread
  the drive returns every time (track 3's `418F6CF8` above), and it does not run then.
  *2026-10-26:* first run on hardware on 2026-10-22, on disc 3 of *Roots Music*: the
  secure re-read's chase replaced track 16 with a single read AccurateRip verifies (v2
  confidence 24; `round36full1022asecurerereadaddendum.txt`, evidence `fc48882f`). It
  does not run on the archival path: the reference disc's secure re-read of 2026-10-21
  read track 3 as `59D352DD` first and shipped `3D8FCF0C` (E4, *Keeping a right read*).
- **One thing to settle: is the disc wearing out?** We read track 3 right in 9 of the
  first 11 rips and in none of the last 15. EAC's last session was 2026-06-25. A fresh
  EAC rip on the same drive (Windows, or EAC under Wine) would show whether the disc
  has worn or our reads have got worse. Logged as TASKS R42.
- **Track 3 since 2026-10-19: marginal on this drive, whatever the build or speed.**
  The fork's round 36 lap 8 S8 (`cyanrip@5af8493:docs/handshake/round-36-lap-08.md`,
  held, not yet released to us) read the timed rips of 2026-10-21: `.25` read track 3
  right in both of its rips at 0.90× to 0.96×, and wrong at 0.96× on 2026-10-20; `.26`
  read it right in the securing pass at 0.99× and wrong in the secure re-read at 0.74×.
  Its words: "Two rips a side cannot separate the build from the disc, and this lap
  names no cause for the speed." So speed is not shown to be the cause, stepping it down
  is not the fix, and this drive takes no speed setting anyway. Pairing `.25` and `.26`
  over more rips is the fork's (Part F row 6); the chase is the fix that works. The
  timed rips' own numbers: `.26` took 0.348 and 0.346 of `.25`'s time on this disc
  (246.96 s against 709.05 s, and 245.90 s against 709.72 s), by the same lap.

**Grade: equal**, with the caveat that it is one disc in one drive. Per rip, EAC
averaged 12.0 of 14 (3 sessions) and we averaged 12.4 (26 rips). Those samples are too
small to call either one better.

### E3. The serious gap: a disc AccurateRip does not know (closed from the next release)

> **Updated 2026-10-20.** Built on `main` on the owner's word *"yes, read twice by
> default"* (TASKS R38), and not yet in a release: 0.7.110 and every earlier release
> behave as the next four paragraphs describe. What was built is at the end of this
> section.

The default rip is *dynamic* (`config.py:314-322`): read the whole disc once at speed,
then re-read only the tracks that miss AccurateRip. When the audit was written
(`69641172`), a disc not in AccurateRip **skipped** the securing pass
(`SKIPPED_DISC_NOT_IN_ACCURATERIP`), so each track was read exactly once. And "not in
AccurateRip" was decided from "no track matched", so a failed lookup, and a disc in the
database whose every track misread, got the same single read (P2 of the check).

How much a single read is worth on this drive, measured: track 3's first-pass read was
wrong in **11 of the 12** whole-disc rips on `evidence` (rounds 27 to 34, and the
0.7.103 run). Each wrong read came with `Ripping errors: 0`, `Track 3 read
successfully!` and no skips; only AccurateRip knew (e.g.
`docs/handshake/artifactsround31/round31fullwholedisc.log:241` and `:1141`). On a disc
AccurateRip does not know, a misread like that would ship with nothing in the rip to
flag it.

EAC configured for Test & Copy reads every track twice whatever the database says, so
it would at least flag the read as unstable when the two reads differ. That is what it
did for track 3 in two of its sessions. (When the misread is systematic, as on track 5,
Test & Copy cannot catch it either.)

This was the maintainer's own *First-rip proof* (TASKS.md, P0, 2026-07-30), unstarted
when the audit was written, waiting on one decision: whether doubling rip time for
unknown discs is acceptable. **The audit recommended yes:** run `-Z` on every track when
the disc is not in AccurateRip, and give the result its own named verdict. Otherwise a
rare pressing, a promo or a CD-R gets the weakest proof, and those are the discs where
no re-rip from a database is possible later.

**What was built (2026-10-20, TASKS R38; the owner said yes the same morning):**

- **The decision comes from the lookup's own answer, not from "nothing matched".**
  `accuraterip_standing.py` reads cyanrip's disc-level `AccurateRip:` line and sorts the
  disc into in the database, not in it, lookup failed, or not determined
  (`accuraterip_standing.py:28-35`, `:51`). The per-track `Accurip:` row says
  `not found` both for a failed lookup and for a disc the database lacks, so it cannot
  tell them apart.
- **A disc not in the database, or whose lookup failed, has every track read again with
  `-Z`** (`securing_pass.py:201-221`, trigger `second_read`). A disc in the database
  whose every track failed re-reads its failing tracks toward the entry, as a partial
  failure always did; until 2026-10-20 it was skipped as "not in AccurateRip".
- **The result is named, and it is not "verified".** "Reads agree … not verified by
  AccurateRip" (`verdict.py:627-634`, `verdict.basis` = `reads_agree`, report schema
  39), amber when a track's reads disagree. Two agreeing reads show the drive gave the
  same bytes twice, not that they are right: on this disc track 5 converged on EAC's
  wrong `E0036697` again and again (E2).
- **The opt-out stays.** Settings → *Read every track twice when AccurateRip can't vouch
  for the disc* (`config.py:333-342`, `second_read_without_accuraterip`); with it off,
  each case records its own skip reason (`securing_pass.py:71-91`).

So on such a disc we now do what EAC's Test & Copy does, and like Test & Copy it cannot
catch a systematic misread. `-Z N` reads until N+1 reads agree, so a troubled disc costs
more than double. No disc AccurateRip lacks has yet been ripped this way on hardware (E6).

### E4. The rest of the extraction path, row by row

| EAC capability | What we do, with the evidence | Grade |
|---|---|---|
| Secure read | libcdio-paranoia at `PARANOIA_MODE_FULL ^ PARANOIA_MODE_NEVERSKIP` (`cyanrip@891c79e:src/cyanrip_main.c:175`, set at `:358`), `-r 5` retries. After retries paranoia may *skip* (keep an unverified read) and counts it; EAC keeps going too, and marks the position | Equal on results (E2); see *error location* |
| Test & Copy | `-Z N` keeps reading until N+1 reads agree and keeps the read most reads agreed on; on by default for AccurateRip-failing tracks, and from the next release for every track of a disc AccurateRip cannot vouch for (E3); a Settings tick makes it every track | Better when AccurateRip has the disc; when not, worse in 0.7.110 and earlier, equal from the next release (E3) |
| Cache defeat | Paranoia tries on every read; the result is measured per drive (KDD-29, measured `Yes` on the BDR-209D) | Equal on the rig; unmeasured elsewhere |
| C2 pointers | Not used; the log states the drive's capability (`cyanrip@891c79e:src/cyanrip_log.c:927-928`). EAC's baseline also had C2 off | Equal |
| Accurate stream | No equivalent, and nothing measures it. From `.26` the drive's declaration is read and shown; every `.26` rip on the BDR-209D (2026-10-21 and -22) read `declared supported by drive (capabilities page, not measured)`, 38 of 38 logs by the fork's count (their lap 8, held). From `59f4e331` (2026-10-26) the EAC-layout row carries that declaration, worded as not determined, never as EAC's `Yes` | **Equal on what can be known** (Part F row 16; *Not determined* until 2026-10-26). Whether paranoia's read path depends on it, and so whether a drive that declares it unsupported should be refused, is the fork's to say |
| Read offset | From AccurateRip's drive list, applied with `-s`, and re-confirmed by every rip that matches AccurateRip (KDD-31). From 2026-10-21 the report checks the applied value against the list's entry for the drive the log names and says `matches`, `differs` (a warning), `drive_not_listed` or `not_determined` (`rip.read_offset_check`); EAC's log prints the number only (`Read offset correction : 667`, `EAC_flac/…log`) | Equal; ahead in that it re-confirms on every rip and names the database entry |
| Overread into lead-in and lead-out | Opt-in `-O`; it stalled for about 23 minutes on the BDR-209D (Part A scorecard) | Equal (EAC's baseline left it off) |
| Read speed | The drive does not advertise speed control (`Speed: default (unchangeable)` in all 135 drive banners on `evidence`), so we never send `-S`, and the read-speed ladder only re-reads. Its slower steps have never run on hardware | Not proven |
| Error location | Pinned `.23`: skip and error **counts** per track only. EAC prints `Suspicious position` times, and its CTDB plugin pinpoints errors (`Differs in 16 samples @04:04:68,04:05:17,04:11:32`, `EAC_wav/…log`). The fork's tip records positions (`cyanrip@820c0c5:src/cyanrip_main.c:643-645`), but no released build does yet | Worse today |
| Pregaps, `INDEX 00` | Matches all ten of EAC's pregap rows in 23 of the 26 rips, the 2026-08-04 one included (`tests/test_fork_rip_eac_parity.py`); the 2026-10-07 cue's `INDEX 00` lines equal EAC's. In three, track 9 reads `0:00:01.26`, one frame longer than the `0:00:01.25` EAC read in all three sessions: `round30oct05fullsecurereread`, `round32fullwholedisc` and `round33fullwholedisc` (the last at evidence commit `f57cdc2b`). The cue follows: track 9's `INDEX 00` is `03:44:10` in `round32fullwholedisc.cue:69` where EAC's is `03:44:11` (`EAC_flac/eac_baseline_police_classics.cue:74`). The sub-channel read varies from rip to rip; it is the fork's `subchannel-pregap-varies` (TASKS R10) | Equal in 23 of 26; one frame off on track 9 in 3 |
| Hidden track one audio (HTOA) | Not supported (out of scope, TASKS.md) | Worse (rare discs) |
| Pre-emphasis | Kept as the disc stores it (`-W`) with `FLAGS PRE` in the cue, from 0.7.102; never ripped on hardware | Equal, but not shown on a real disc |
| Data tracks (Enhanced CD) | `.23` copies them by default (TASKS R12). The verdict counted a data track as a missing audio track until 2026-10-21 (R13): every surface now counts audio tracks only, and the EAC-layout log prints no AccurateRip line for a data track | Worse |
| Single-file image + cue | Not supported (Part A P5) | Worse |
| Keeping a right read once found (Part F row 2) | EAC keeps its Test/Copy pair whatever AccurateRip says. The chase keeps the read AccurateRip verifies (E2), but two paths still lose one. A `-Z` pass shipped a wrong read over a right one: the reference disc's secure re-read of 2026-10-21 read track 3 as AccurateRip's `59D352DD`, then converged on `3D8FCF0C`, a frame-450-only match, and shipped it (`round36full1021asecurereread.log:225-231`, `:270-275`, evidence `ab3b1395`); the archival path runs no chase. And a cancel threw a right read away: on the damaged disc the securing pass's fifth read of track 11, `10248071`, is AccurateRip-verified at v2 confidence 29 (`round36full1021bwholediscsecuringpass.txt:112-116`, evidence `08de9851`), and the cancel kept the album pass's read, because nothing is swapped from a pass that did not finish | **Behind**: ship any read that verifies, whichever path read it, and keep finished tracks through a cancel (TASKS R7) |
| A damaged disc (Part F row 5) | EAC re-reads a bad sector up to 82 times, then flags its position ([Extraction Technology](https://exactaudiocopy.de/extraction-technology/)). We have no time bound. On *Roots Music* disc 1 (2026-10-21) the album pass read track 18 in 8,548 s (`round36full1021bwholedisc.log:1441`) with 2,076 paranoia skips; the securing pass's `-Z 2 -r 5` began re-reading it, and the run's 6-hour limit stopped the rip in track 18's second re-read. Track 18 took 5 h 18 min of the 6 h. Every bound in either repository is a count (`-r`, the chase's 5), none a time | **Behind**: a per-track time budget, and a track whose every read skips recorded as unreadable on this drive, with positions (TASKS R49). What `-r 5` means beside EAC's 82 reads is the fork's |
| CD-R detection (Part F row 23) | No EAC counterpart graded. `.26` prints `Recordable: unknown (profile 0xffff is not a CD profile)` in every log on the BDR-209D, on three discs, so it never answers; libcdio's placeholder is printed as the drive's answer (the fork's lap 8 S4, held) | **Behind**; the fork's fix, proposed for `.27` |
| A drive blip mid-rip (Part F row 33) | No EAC counterpart graded. On 2026-10-21 at 12:02:39 UTC, after the reference disc's rip had finished, one status poll read the tray open; the app cleared its disc view at once, the auto-rescan opened a release picker no step answered, and 57 steps of the Full run failed behind it (the run's transcript, evidence `ab3b1395`). Nothing had asked for an eject | **Behind**: confirm a removal before acting on it (TASKS R54) |
| Speed of a clean rip (Part F row 34) | EAC's three sessions ran at 1.6× to 9.1× with Test & Copy (E2). `.26` read tracks 1 to 3 in 0.348 to 0.354 of `.25`'s time on the reference disc and disc 3, and 0.193 to 0.197 on disc 4 (the fork's lap 8 S8, held): 2.8× to 5.1× faster | **No data against EAC**: time one EAC rip and one Platterpus rip of the same disc (TASKS R55; the owner's, at the drive) |

### E5. Verification, output and record

| EAC (with the CTDB and AcoustID plugins) | Ours, with the evidence | Grade |
|---|---|---|
| AccurateRip v1 and v2, confidence | Same, plus the frame-450 one-frame match reported separately and never counted as verified | Equal, plus a diagnostic EAC lacks |
| Re-reads a failed track automatically | No; the user re-rips by hand | **We do it:** the securing pass and the auto-fix re-read (`securing_pass.py`), and from 2026-10-21 single re-reads until one AccurateRip verifies, when the kept read fails it (`verified_read_chase.py`, TASKS R7, not yet run on hardware) |
| CTDB: per-track status, finds offset-shifted pressings, locates bad samples, submits; CUETools repairs **Per track and over every offset, from the next release** (2026-10-21, TASKS R43): the whole-disc CRC is compared at every alignment in ±5879 (`ctdb/verify.py:235`), so a match names its offset and a no-match says our audio differs from every entry (`:306`); each track is compared with every entry's per-track CRC the way CUETools' `GenerateLog` does (`ctdb/matching.py:180`), and the result names the tracks that differ. Checked against EAC: fed EAC's own Copy CRCs, our counting marks as differing exactly the tracks its CTDB plugin did, in the wav and mp3 sessions (`tests/test_ctdb_per_track.py`). Until then, one whole-disc check at offset 0, and a non-match said nothing. Still no localisation (it needs a Reed-Solomon syndrome pass over the whole disc that pure Python cannot do in reasonable time; TASKS R43 says why), no submission, no repair (repair deferred, KDD-14). **A match is weighed** (fixed 2026-10-19, TASKS R34, shipped in 0.7.110): 8 of the 26 rips here matched an entry of confidence 1, most likely EAC's own 06-11 submission with the same track-5 misread (E2), while about 1,405 submissions disagreed, and the app said "CTDB: verified ✓". A match is now green only when its entry is the strongest for the disc and AccurateRip rejects no track; otherwise it reads "matched 1 of N CTDB submissions; K disagree", in amber (`ctdb/verify.py:101-109`, `:264-265`, `:318`) | **Worse, narrower.** On this disc EAC's CTDB plugin pinpointed track 3's 14 to 16 bad samples; ours now says track 3 differs from every entry, and cannot say where or how many. This audit as first written graded CTDB without seeing that its one match was not independent |
| AccurateRip submission (Part F row 14) | None. This row said "Impossible from Linux", which was written without a source (PLANNING.md KDD-12, 2026-05-28) and is **unverified as of 2026-10-26**: AccurateRip's own list of compatible programs (`http://www.accuraterip.com/software.htm`, read 2026-10-26) names five, none for Linux, and does not say whether a submission from a program not on it is refused | **Behind, may be not possible**: find out whether AccurateRip accepts submissions from programs it has not listed; if it does not, that is not ours to change (TASKS R52) |
| CTDB submission (Part F row 13) | Not built. EAC's CTDB plugin submits (`EAC_flac/…log:258`), and it submitted the track-5 misread AccurateRip rejects (E2) | **Behind**: build it, and never submit a rip with a track AccurateRip rejects (TASKS R43) |
| Saying a wrong track is wrong (Part F row 8) | EAC prints `Copy OK` over a track AccurateRip rejects, and so do we. In the four Full runs of 2026-10-21 and 22, five wrong tracks carried `Copy OK` in the EAC-layout log, three of them beside `Test and Copy CRC identical — confirmed across N secure re-reads`: the reference disc's track 5 in the whole-disc rip, and tracks 3 and 5 in its secure re-read (`round36full1021awholedisceac.log:124-126`; `round36full1021asecurerereadeac.log:97-99`, `:127-129`; evidence `ab3b1395`). On the damaged disc cyanrip's log printed `read successfully!` over tracks 11, 12, 14 and 16, which failed AccurateRip (`round36full1021bwholedisc.log:846`, `:926`, `:1087`, `:1249`, evidence `08de9851`). No wrong track was ever called verified. **Built 2026-10-26** (TASKS R50): a track AccurateRip contradicts (`verdict.track_accuraterip_contradiction`: `wrong` when frame 450 matched and the whole track did not, `differs` when it was compared and nothing matched) gets no clean word on any surface. The secure re-read's track 3 now reads `Copy CRC 3D8FCF0C  (Test and Copy CRC identical — the re-reads agreed on this value, and AccurateRip contradicts it)`, `Proof: none — WRONG: frame 450 matches AccurateRip's entry for this pressing (confidence 200) and the whole track does not, so the audio differs from it`, then EAC's own `Copy finished`; a `differs` track reads `Proof: none — this copy differs from AccurateRip's entry (confidence N): most likely a misread`. The disc level reads EAC's `There were errors`, then `Ripper's own count  : Ripping errors: 0 — not counted: track(s) 3, 5, which AccurateRip contradicts` (the round-36 S11 shape). The report carries `tracks[].accuraterip_contradiction` (schema 40) and the results table's Status cell reads `⚠ Wrong (AccurateRip)` (`tests/test_wrong_track_never_reads_clean.py`). The new lines go to the fork in our next lap | **Better** from 2026-10-26 (was Equal, both bad): EAC prints `Copy OK` over a stable wrong read, ours names it wrong. `read successfully!` is the fork's |
| The proof each track has (Part F row 9) | EAC: the Test & Copy CRC pair. Ours: AccurateRip at confidence N, a single re-read AccurateRip verifies, CTDB per track, or reads that agree. **Shown from 2026-10-26** (TASKS R51): every audio track block of the EAC-layout log carries a `Proof:` row (`AccurateRip v1 at confidence 129 and v2 at confidence 200`; `a single re-read that AccurateRip verifies (…), kept in place of a read it did not verify`; `the secure re-reads agreed (converged after 3 reads), and AccurateRip has no entry for this track, so this shows the drive read it the same way each time, not that the audio is right`; or `none — …` with the reason), and the report carries the same line as `tracks[].proof` with CTDB's per-track answer, which the log is written too early to hold (`track_proof.py`, `tests/test_track_proof.py`) | **Better** from 2026-10-26 (was Better once shown); the log's row cannot yet name CTDB |
| Verdict wording | A skipped or non-converged track reads `Copy NOT confirmed`, never `Copy OK`, and a read-stability line names it (Part B). EAC printed `Copy OK` over tracks whose Test and Copy CRCs differed (`EAC_mp3/…log`, tracks 3 and 4). Both tools print `Copy OK` over a stable read AccurateRip rejects: ours did over track 5 (`round32fullwholedisceac.log:123-125`). And both keep `No errors occurred` beneath such tracks, because in both it means no unrecoverable read errors: ours prints it under a track 3 marked `Copy NOT confirmed` (`round32fullwholedisceac.log:253`), with the read-stability line after it (`eac_log_export.py:1249-1258`). This audit first said our log "refuses to" print either; it prints both | Better where re-reads disagree; equal over a stable wrong read |
| Integrity of finished files | `flac --test` decode of every file after tagging and cover art, SHA-256 per file, derived MP3, WavPack and WAV checked against the FLAC master (`workers/flac_verify_worker.py`, `checksums.py`). EAC's `flac -V` checks the encode only | Better |
| Cue ISRCs | MusicBrainz's ISRC for each track, passed in with `-t`, not the disc's (TASKS R20): track 1 is `GBAAM0201086` in ours (`docs/handshake/artifactsround31/round31fullwholedisc.cue`) and `GBAAM7800003` in EAC's. Two codes for one recording can both be valid; a cue's ISRC should be the disc's. EAC can read cue ISRCs from the disc, but its log does not say where these came from, and `.23`'s own disc read has not been compared with them. `.24`'s `--prefer-disc-isrc` fixes ours; `.23` is still what users install | Worse today |
| Log checksum | Fork `Log FUN512` plus our SHA-256 footer, open and checked on every rip. EAC's is obfuscated and has been reverse-engineered (`eac_logsigner`). Neither stops a determined forger | Equal in strength; only EAC's is recognised by others |
| Tags, cover art | MusicBrainz via the adapter, front art embedded, back and booklet saved, ReplayGain and R128 | Better out of the box |

### E6. How much the evidence covers

**Covered, with evidence:** the extraction path on one Pioneer BDR-209D (firmware
1.51, all 135 drive banners on `evidence`), on one Bazzite machine (every row of the
`docs/testing.md` §5B ledger), with two discs: the 14-track reference disc and an
18-track damaged disc (DiscIDs `pNtImOkd…` and `zxtbw2Jg…`). Four full-green
acceptance runs (2026-10-07, 10-12, 10-13 and 10-16).

**Not covered:** a second drive or chipset; a second machine or distro (the 0.8.1 gate
needs both); a disc AccurateRip does not know, ripped end to end and checked against a
second drive; a pre-emphasised disc; an HTOA disc; an Enhanced CD; a CD-R; a drive that
honours speed changes.

EAC's case rests on two decades of use across thousands of drives. AccurateRip's
drive-offset list was largely built from EAC users. **Our extraction is as good as
EAC's on the one drive we can compare, and nothing yet shows how it does on any
other.**

### E7. What to do, ranked by archival impact

1. **Read every track at least twice when AccurateRip lacks the disc** (E3; the
   maintainer's *First-rip proof*, items 1 and 2). **Built 2026-10-20** on the owner's
   yes (TASKS R38), deciding from the lookup's own answer so a failed lookup is
   covered too; ships in the next release. Still open: rip one such disc end to end on
   hardware.
2. **Prove it on more hardware:** a second drive from another maker, a second machine
   and distro, and the disc types in E6. This is also the 0.8.1 gate.
3. **Find out whether the reference disc is wearing out:** one EAC rip of it now on the
   BDR-209D (TASKS R42).
4. **Deepen CTDB:** per-track results and the offset-shifted sweep are **built
   2026-10-21** (TASKS R43) and ship in the next release. Next: localisation of bad
   samples, which waits on the maintainer's word on `numpy` or a native extension for
   the syndrome pass (R43 says why), then submission. Repair stays deferred under
   KDD-14. Weighing a match against the entries that disagree is done (TASKS R34,
   0.7.110).
5. **Ship disc ISRCs** with `.24` (R20) and **data-track handling** (R12; R13 is done).
6. **Show error positions** once the fork releases them. They need EAC-layout wording
   agreed through the handshake, since the fork diffs that log (TASKS R44).
7. HTOA and image + cue: low, only if users ask.

**Corrections this audit made to Parts A and B:** Part A's scorecard said the 2026-10-07
cue carries "all 14 ISRCs". It does, but they are MusicBrainz's codes, not the disc's.
And Part A compared us with one EAC session; the two other committed EAC sessions read
track 3 wrong and misread track 4 once. Both are fixed inline above, with a pointer here.

**Corrections made to this audit (2026-10-20),** from the claude-code-skills check of it:
E1 and E5 said our log "refuses" `Copy OK` and `No errors occurred` over unverified
tracks, and it prints both (P3); E4 graded pre-gaps "Equal" from one rip, and track 9
differs in 3 of 26 (P5); a time copied from an export dropped its zone (P8); and the CTDB
row missed that its one match was not independent (P1, fixed in the app as TASKS R34).
`tests/test_fork_rip_eac_parity.py` no longer says it closes the parity question (P6).

---

## Part F — The yardstick, and every Full run scored by it (2026-10-26)

**Where this came from.** The owner's *EAC parity plan of record*, written by the
claude-code-skills session on 2026-10-26 02:30 UTC and sent to both sessions, reading
`platterpus@59f4e331` and `cyanrip@5af8493`. The owner's words in it: *"my goal is to be
better or at best equal, to eac, in all regards"*, and *"ripping ir the goal. we need to
report on that accuractly to confirm, that is what we do."* The plan itself is not
committed; this part holds its substance, Part D §2 holds its logchecker table, Part E
its new rows, and TASKS R49 onward its items, each naming its row here. Its corrections
to our records are made where each record lives, with a dated note where the record is
append-only (KDD-12, KDD-30, 0.7.112's notes).

### F1. The yardstick

- **A rip is right** when AccurateRip verifies the track's whole checksum at high
  confidence, or CTDB's strongest entry agrees with it.
- **A rip is wrong** when the frame-450 checksum matches AccurateRip and the whole track
  does not. The frame match proves the pressing, so a whole-track mismatch means the
  audio differs.
- **Every track scores one of three ways:** right; wrong but reported; **wrong and
  reported as fine**. The third is the worst, and the one to drive to zero.
- **A tracker's logchecker is a different test.** It scores how the ripper was set up and
  what the log says, not whether the audio is right (Part D §5: OPS's own README says a
  log below 100 can be a perfect rip).
- **EAC's own words do not decide correctness either.** `Copy OK` means EAC saw no read
  error, and it prints it over tracks AccurateRip rejects: over track 5 in all three
  of our EAC sessions, under `Cannot be verified as accurate`
  (`output_reference/EAC_*/…log:115-116`).

**Each Full run's reading adds a row to F2,** scored this way, so the scoring stays
with the runs.

### F2. The Full runs, scored

**The four of 2026-10-21 and 22,** Platterpus 0.7.112 with `.26` (`ca0f097`) under
review, on the BDR-209D, filed on `evidence` at `ab3b1395`, `08de9851`, `fc48882f` and
`6b31795c` (TASKS R47):

| Run (UTC) | Disc | Right | Wrong | What happened |
|---|---|---|---|---|
| 2026-10-22 21:57 | *Roots Music* disc 4 | all | 0 | Every rip, both builds |
| 2026-10-22 11:45 | *Roots Music* disc 3 | all but 1 | 1 | Track 16 is damaged. The main rip's read was wrong; the secure re-read's chase verified its fifth single read and shipped it (`round36full1022asecurerereadaddendum.txt`). **Final: 16 of 16** |
| 2026-10-21 11:35 | The Police (reference) | 37 | 5 | Track 3 wrong in `.26`'s timed rips and secure re-read; track 5 wrong, its right value never read. **Final main rip: 13 of 14** |
| 2026-10-21 21:45 | *Roots Music* disc 1 (damaged) | 10 | 8 | Tracks 11 to 18. The run hit its 6-hour limit in the securing pass; a re-read of track 11 that verified was thrown away by the cancel (E4) |

**158 of 172 tracks written were right; 14 were wrong.** These counts are the plan's,
from the bundles' `.platterpus.json` reports and EAC-layout logs, and were **not
re-derived here**: the plan does not say which rips make up each count (its own table
for the reference run lists rips writing 44 tracks, and it counts 42). What was re-read for this part, from the
filed copies: the reference disc's secure re-read shipping `3D8FCF0C` for track 3 after
reading `59D352DD` first; the damaged disc's track-11 read `10248071` verified and not
kept; disc 3's track 16 replaced by a verified read; and the 60 failed steps of the
reference run, by line (`round36full1021ascriptreport.json`).

**Did we say so truthfully?** (the plan's reading; the three tracks named in E5's
*Saying a wrong track is wrong* row were re-read here)

- **Every `Bit-perfect` verdict was true.** No wrong track was called verified.
- **But wrong tracks were reported as fine, in the log a user reads:** 5 carried
  `Copy OK`; 3 of those 5 also carried `confirmed across N secure re-reads`; and on the
  damaged disc, tracks 11, 12, 14 and 16 printed `read successfully!` and failed
  AccurateRip (the fork's lap 8 S9, held). This is the worst outcome on F1's scale, and
  EAC does the same (Part E §E5, *Saying a wrong track is wrong*).

**Against EAC, on the one disc both have ripped in the same drive:** EAC 13, 11 and 12
of 14 in its three sessions; we 12 or 13 in 26 rips to 2026-10-16 and 13 on
2026-10-21. Track 3 right in 1 of EAC's 3, and in 9 of our 26; track 5 never right in
EAC's, right once in ours (2026-10-07); track 4 wrong once in EAC's, right 26 of 26 in
ours (E2). **On this disc and drive, we are equal to EAC.**

### F3. Every regard, EAC against us (the plan's section 5)

Grades: **Better** and **Equal** are the goal reached; **Behind** can be reached, and
the last column says how; **Not possible** gives the reason. TASKS rows name these by
number ("Part F row N").

| # | Regard | EAC | Us on 2026-10-26 | Grade | To reach equal or better | Whose |
|---|---|---|---|---|---|---|
| 1 | Reading the audio right | 12.0 of 14 a rip, one disc | 12.4 of 14, one disc | Equal | Rows 2 to 6, then more discs and drives (row 29) | Both |
| 2 | Keeping a right read once found | Keeps its Test/Copy pair whatever AccurateRip says | The chase keeps the read that verifies, but `-Z` shipped a wrong read over a right one, and a cancel threw a right one away (E4) | Behind | Ship any read that verifies, whichever path read it; keep finished tracks through a cancel | Platterpus (R7) |
| 3 | Re-reading a failed track | Leaves it to the user | Automatic, until a read verifies | Better | Keep | — |
| 4 | A disc AccurateRip does not know | Test & Copy on every track | Every track read until reads agree, from 0.7.111 (E3) | Equal | Rip one such disc end to end on the drive | The owner's disc |
| 5 | A damaged disc | Reads a bad sector up to 82 times, then flags it | Track 18 took 5 h 18 min; no time bound (E4) | Behind | A per-track time budget; record a track whose every read skips as unreadable on this drive, with positions. Say what `-r 5` means beside EAC's 82 | Platterpus (R49); the fork for `-r` |
| 6 | Track 3 on this drive | Right 1 in 3 | Right in some rips, both builds (E2) | Equal | Pair `.25` and `.26` over more rips before naming a cause; the chase is the fix that works | The fork |
| 7 | Track 5 on this drive | Never | Once | **Not possible** on this drive | The drive returns the same wrong bytes to every program. Another drive can | — |
| 8 | Saying a wrong track is wrong | `Copy OK` over it | From 2026-10-26, a track AccurateRip contradicts reads `Proof: none — WRONG: …` (or `differs`) and `Copy finished`, never `Copy OK` or "confirmed", and the disc reads `There were errors`; the report and the results table say the same (E5). The fork's `read successfully!` is unchanged | Better (was Equal, both bad) | Send the wording to the fork in our next lap; `read successfully!` over such a track | Platterpus (R50, built); the fork for `read successfully!` |
| 9 | The proof each track has | Test & Copy CRCs | From 2026-10-26, a `Proof:` row per track naming AccurateRip at confidence N, a verified single re-read, reads that agree, or none and why; the report adds CTDB per track (E5) | Better (was Better once shown) | Name CTDB in the log's row too, by re-rendering it when CTDB answers | Platterpus (R51, built) |
| 10 | Where a read was unsure | Suspicious positions | Counts in released builds; positions in `.25`'s record, not yet in the log | Behind | Agree the log wording and print them | Both (R44) |
| 11 | CTDB check | Per track; names the bad samples | Per track and across offsets, matches weighed | Behind on naming samples | The syndrome pass, on the owner's word on `numpy` or a native extension | Platterpus (R43, R34) |
| 12 | CTDB repair | Not in EAC; CUETools does it | Deferred (KDD-14) | Equal | Building it would be better than EAC | Platterpus, later |
| 13 | CTDB submission | Yes | Not built | Behind | Build it. Never submit a track AccurateRip rejects, which EAC did with track 5 | Platterpus (R43) |
| 14 | AccurateRip submission | Yes | None | Behind, may be **not possible** | "Impossible from Linux" had no source and is unverified (KDD-12's correction). Find out whether AccurateRip accepts submissions from programs it has not listed; if not, it is not ours to change | Platterpus (R52) |
| 15 | Secure reading | Secure mode | libcdio-paranoia, full mode | Equal | — | — |
| 16 | Accurate stream | Setting, logged | The drive's declaration read and shown, "not measured" (`59f4e331`) | Equal on what can be known | Say whether paranoia's read path depends on it; if so, refuse a drive that declares it unsupported | The fork |
| 17 | Cache defeat | Setting, logged | Measured when the user runs *Analyse cache* | Behind on the default | Measure once per drive in setup | Platterpus (R53) |
| 18 | C2 | Off by the guides | Not used; logged where the drive reports | Equal | — | — |
| 19 | Read offset | Set by the user | From AccurateRip's list, checked every rip | Better | — | — |
| 20 | Read speed | "Allow speed reduction" | This drive takes no speed setting; the ladder re-reads | Equal on this drive | Test on a drive that takes `-S` | The owner's hardware |
| 21 | Pregaps and gaps | Detect Gaps; appended to the previous track | Matches EAC in 23 of 26 rips; `.26` never reads track 9 as 94 | Behind on `.26` | The fork's lap 8 S5 record, then the fix in `.27` | The fork (R10) |
| 22 | The disc's ISRCs | Read for the cue | `.26` reads them, 14 of 14 matching EAC | Equal | Our cue check compares with the code it sent; compare with the disc's (the fork's lap 8 S10) | Platterpus (R20) |
| 23 | CD-R detection | — | `.26`'s `Recordable:` prints a placeholder | Behind | The fork's lap 8 S4 fix in `.27` | The fork |
| 24 | Pre-emphasis | Kept, flagged | Kept, `FLAGS PRE` | Equal, untested | Rip a pre-emphasised disc | The owner's disc |
| 25 | HTOA, image + cue, data tracks | Supported | Not, or data copied by default | Behind | Build them; HTOA and image + cue low (E7) | Both (R12) |
| 26 | Checking the finished files | `flac -V` at encode | `flac --test` after tagging, SHA-256, derived formats checked | Better | — | — |
| 27 | A tracker accepting the log | Accepted by name | Refused by name, before any setting is read (Part D §1) | **Not possible** by our own work | The checkers allow-list rippers; copying EAC's identity is forgery (KDD-24). The honest route is to ask OPS to add Platterpus, as it added our previous backend's format; that is OPS's decision | — |
| 28 | A log anyone can check | Closed, obfuscated signature | Open SHA-256 over our own log | Better on openness | Keep our own log the goal (KDD-36) | — |
| 29 | Breadth of proof | Twenty years, thousands of drives | One drive, one machine | **Not possible** to equal soon | Narrow it with a second drive, machine and distro (the 0.8.1 gate) | The owner's hardware |
| 30 | Setup | Needs a guide | Settings chosen for the user | Better | — | — |
| 31 | Openness, cost, extras | Closed source, freeware, paid plugin | Open source, free, nothing bundled | Better | — | — |
| 32 | Platform | Windows | Linux | Equal for Linux users | A Windows build is the owner's long-term goal; no work now | Both, later |
| 33 | A drive blip mid-rip | — | One tray-open blip cleared the disc view and cost 57 steps (E4) | Behind | Confirm a removal before acting on it | Platterpus (R54) |
| 34 | Speed of a clean rip | 1.6× to 9.1× with Test & Copy | `.26` is 2.8× to 5.1× faster than `.25` | No data against EAC | Time one EAC rip and one Platterpus rip of the same disc | The owner, at the drive (R55) |

**What waits on the owner** (the plan's §8): how round 36 goes on after the fork's lap
8 S4 and S5; keeping Fast Verified as the default with each track's proof printed (row
9); `numpy` or a native extension (row 11); EAC rips of the damaged disc and disc 3, set
up as F4 says, timed (row 34); and a second drive, a pre-emphasised disc and a disc
AccurateRip does not know (rows 4, 20, 24, 29).

### F4. A clean EAC rip, for the owner's comparison rips

What OPS scores is Part D §2. To rip a disc in EAC for comparison with ours:

1. Run **EAC 1.8, from exactaudiocopy.de only**. Its changelog lists no secure-mode
   change after 1.0 beta 3, and a fix on 2015-04-09 for crashing on a read error, which
   matters on a damaged disc. In the installer keep AccurateRip and the CTDB plugin;
   leave off GD3 (paid after 10 lookups), the other metadata plugins and AcoustID.
2. **Drive options:** secure mode, accurate stream, defeat audio cache, C2 off.
3. **Offset:** from AccurateRip's list (+667 for the BDR-209D); overread off.
4. **Compression:** FLAC `-8 -V`, no ID3 tag, no normalising.
5. **Per disc:** Detect Gaps, then a cue sheet with gaps, then Test & Copy on all tracks.
6. **The log:** save it unedited, in English.

**Our default, Fast Verified, against that bar.** It already meets or beats it on
secure reads, C2, offset, gaps (except `.26`'s track 9), ISRCs, no silent-block
deletion, null samples, no normalising, no ID3 tag, per-track rips, AccurateRip and
CTDB. It meets Test & Copy differently: a track AccurateRip verifies is read once, which
is stronger proof than two reads agreeing, and any other track is read until reads
agree. The plan recommends keeping that default and printing each track's proof (row
9); *Archival Exact* in Settings reads every track twice for anyone who wants EAC's
Test & Copy exactly. That recommendation waits on the owner's word. Behind: rows 10, 16
and 17.

**eacguide.github.io is a setup guide, not an authority.** It is one author's guide for
EAC 1.0 beta 3 (four commits, all 2017-12-26, by the plan's reading), aimed at a log
that passes a logchecker. Its claim that with its settings "the only possible errors
would be with the CD itself" is contradicted by track 3 on this drive (E2), which reads
right in some rips and wrong in others, on both builds, with no read error reported.

---

*Last updated for Platterpus v0.7.113.*
