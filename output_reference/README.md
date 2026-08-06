# `output_reference/` — rip-output baselines for EAC parity

This directory holds **reference rip outputs** used to prove Platterpus's rips
are correct by comparing them against a known-good baseline.

**EAC is the baseline.** Exact Audio Copy is the gold standard this project is
measured against (see [`../docs/test-plan.md`](../docs/test-plan.md) → *EAC
output-parity check*). The EAC reference is committed here now. cyanrip (the sole backend since
2026-06-30, KDD-18) rips are committed once there is a **hardware run worth
documenting** — imperfections stated honestly in the dir README (the
"store the text, document the imperfection" practice); full 14/14 parity is
the goal that closes the TASKS.md checkbox.

## What "parity" means here (and why there's no audio)

A rip is bit-perfect when its **per-track CRC matches EAC's**. EAC's log records,
for every track, a `Test CRC` and a `Copy CRC` (e.g. `Copy CRC B0D122E7`); when
those two match each other the rip is internally consistent, and when a ripper's
`Copy CRC` equals EAC's for the same track the two rips are **bit-identical**.
AccurateRip / CTDB confidence values in the log corroborate this against the
wider community database.

> **Log encoding:** EAC writes its `.log` as **UTF-16** — the logs here are stored
> verbatim in that native encoding (the authentic artifact), and the parity
> checker + tests decode them via `platterpus.parity.decode_log_bytes`.
> `.gitattributes` marks `output_reference/**/*.log` `-text` so line-ending
> normalization can't corrupt the UTF-16. (`.cue` sheets are ASCII text.) Don't
> "fix" a log to UTF-8 — that silently broke the checker once; the decoder, not a
> conversion, is the right layer.

So the comparison is **log-to-log (CRCs)**, not audio-to-audio. That's why this
directory stores **logs and cue sheets, never the decoded audio**:

- **Copyright (project-wide rule — `CLAUDE.md` Critical rule #8).** This
  repository is public. The reference disc (*The Police — Every Breath You Take:
  The Classics*) is a commercial recording; committing its FLAC/WAV/MP3 audio
  here would publicly redistribute copyrighted material. Owning the disc does not
  grant that right. This applies to **any** copyrighted media **anywhere in the
  repo, even a temporary test file** — never `git add` one. `.gitignore` denies
  audio extensions as a backstop.
- **It isn't needed.** The CRCs in the log already prove bit-perfection.
- **Repo bloat.** Full-album audio is hundreds of MB and would live in git
  history forever.

If a test ever genuinely needs real PCM to exercise the decode/CRC path, use a
**short, freely-licensed or self-generated** sample (CC0 / public-domain / a
synthetic tone with a known CRC), and keep it tiny (kilobytes,
not megabytes) — never a commercial track. (The pre-commit hook blocks audio
extensions; a verified CC0 sample goes in via `git commit --no-verify`.)

## Layout — backend × format

EAC is the baseline for each format; the backend dirs hold a documented
hardware rip's **log** (+ `.cue`) with its result stated honestly. **Priority order: FLAC (1) → WAV (2) →
MP3 (3)** — FLAC is the archival master and the first parity target; the
WavPack/MP3/WAV *output formats* now ship (KDD-22), but their per-backend parity
*proofs* still await real-hardware rips (see `TASKS.md`).

| | FLAC (priority 1) | WAV (priority 2) | MP3 (priority 3) |
|---|---|---|---|
| **EAC** (baseline) | `EAC_flac/` ✅ committed | `EAC_wav/` 🟡 13/14; **WavPack not plain WAV** (see below) | `EAC_mp3/` 🟡 imperfect (12/14; see its README) |
| **whipper** *(removed 2026-06-30, KDD-18 — historical row; no proof will be added)* | `whipper_flac/` — | `whipper_wav/` — | `whipper_mp3/` — |
| **cyanrip** | `cyanrip_flac/` 🟡 12/14 (T3+T5; see its README) | `cyanrip_wav/` ⬜ | `cyanrip_mp3/` 🟡 13/14 (T5 only; see its README) |

The committed EAC baseline (`EAC_flac/eac_baseline_police_classics.log`) is the
canonical extraction reference. Its per-track **Copy CRC** is the CRC of the
ripped PCM, so it's the bit-perfect target for **both FLAC and WAV** (both are
lossless → decode to identical PCM → identical CRC). **MP3 is lossy**, so an MP3
encode is *not* bit-comparable; "MP3 parity" means the same extraction CRCs +
correct encoder/tag behaviour, not identical audio. `EAC_wav/` and `EAC_mp3/`
therefore reuse this same extraction baseline rather than duplicating it.

## What is in each directory

Consolidated here from nine per-directory READMEs, because nine files describing
one 3×3 matrix meant the shared rules (no audio, UTF-16, how to replace a rip)
were restated nine times and could drift nine ways. The per-rip findings below
are unchanged.

### `EAC_flac/` — the canonical baseline ✅

`eac_baseline_police_classics.log` / `.cue` — a real **EAC V1.8** secure rip
(Test & Copy) of the reference disc on the Pioneer BDR-209D, read offset **+667**.
This is the extraction baseline every parity check measures against
(`scripts/eac_parity.py`, `tests/test_parity.py`, `docs/test-plan.md` Part B).

⚠️ **The `.log` is UTF-16 — do not re-encode or "fix" it.** See the log-encoding
note above; converting it to UTF-8 silently broke the parity checker once.

### `EAC_mp3/` — 12/14. Kept for EAC's *encoder configuration* 🟡

`eac_mp3_police_classics.log` / `.cue` (2026-06-25). **Not a clean baseline** —
12/14 extraction CRCs match `EAC_flac/`. Tracks 3 and 4 took read errors this
session (the disc's known marginal zone, not an MP3 problem; on track 4 EAC's
*Test* CRC matched the baseline while the *Copy* pass picked up a transient
error). Track 5 differs from AccurateRip but matches our baseline — the
consistent pressing quirk.

**Why it is still valuable:** it documents EAC's own MP3 settings — encoder
`lame3.100.1`, options **`-V 0`** (VBR, ~245 kbps), ID3 tags on. That *confirms
our design* (`docs/archive/mp3-wav-support-2026-06.md` §3): our FLAC→MP3 transcode
(`adapters/transcode.py`, `ffmpeg -q:a 0`, equivalent to lame `-V0`) matches what
EAC does.

### `EAC_wav/` — 13/14, and it is **WavPack**, deliberately 🟡

`eac_wav_police_classics.log` / `.cue` (2026-06-25). EAC's User Defined Encoder
here was **`wavpack.exe -h -m`**, so the output is WavPack (`.wv`) — lossless
compressed with APEv2-style tags, not plain PCM WAV. The maintainer confirmed
keeping it (2026-06-25), and it is **equivalent for parity**: WavPack is lossless,
decodes to identical PCM, so identical per-track Copy CRC. WavPack has since
shipped as a real output format (KDD-22), which makes this reference doubly
useful.

**13/14 Copy CRCs match `EAC_flac/`** — the best run of the three sessions. Track
3 differs (`329DC760` vs baseline `59D352DD`) — the persistent marginal spot.
Track 4 came back **clean** here having errored in the MP3 session, which is what
establishes the trouble as transient disc surface rather than systematic. Cue nit:
this session's cue dropped track 10's ISRC.

### `cyanrip_flac/` — 12/14 🟡

Real cyanrip 0.9.3 rip, same disc/drive/offset, captured 2026-06-27. The
comparison matches EAC's per-track **Copy CRC** against cyanrip's **EAC CRC32**
(cyanrip computes the EAC-style CRC, so they are directly comparable). **TOC is
identical** — every start/end sector matches EAC exactly. Both rips report
AccurateRip confidence 200 where they verify.

Two tracks differ:

- **Track 5 — the disc, not the ripper, and a tie.** EAC *also* could not verify
  track 5, and its CTDB pass shows track 5 "Differs in 3 samples @02:24:59".
  cyanrip rates it partially accurate via the AccurateRip offset-450 check. Both
  rippers hit the same ~3-sample spot and resolved it differently.
- **Track 3 — a genuine cyanrip ↔ EAC divergence** at the time: EAC matched the
  main AccurateRip database at confidence 200, cyanrip matched only offset-450.
  Superseded by `cyanrip_mp3/` below, which got track 3 right.

### `cyanrip_mp3/` — 13/14, better than the FLAC reference 🟡

Real MP3-output rip, same disc/drive/offset, 2026-06-27. **Note the log says
`Outputs: flac` and the cue references `.flac`** — that is the transcode-always
model (KDD-22): cyanrip always extracts to FLAC and the GUI derives MP3 from it,
so this log *is* the FLAC extraction record and the MP3s are a lossy derivative of
the same verified samples. The extraction CRCs are the proof.

- **Track 3 matches EAC exactly (`59D352DD`)**, where the earlier cyanrip FLAC run
  missed it — **confirming that divergence was transient and a re-rip resolves
  it.**
- **Track 5 is genuinely unstable:** three rips, three different CRCs (EAC
  `E0036697`, cyanrip-FLAC `4065BECC`, cyanrip-MP3 `6902BCF0`), and EAC could not
  verify it either. Repair-class tooling (CUETools/CTDB) or a cleaner disc is the
  only path to a verified track 5.

### `cyanrip_wav/` — pending ⬜

Empty until a cyanrip WAV rip matches the baseline (WAV is lossless, so the target
is the same per-track `Copy CRC`). Priority 2, after FLAC.

### `whipper_flac/`, `whipper_wav/`, `whipper_mp3/` — historical, permanently empty

whipper was removed as a backend on **2026-06-30 (KDD-18)** before reaching any
parity proof, so these will stay empty. Retained as the record of the
originally-planned backend×format matrix.

### Replacing an imperfect rip

Clean the disc around the failing tracks, re-rip with EAC in **Test & Copy** mode
until all 14 match, then overwrite that directory's `.log` and `.cue`. Keeping
WavPack for the WAV slot is fine — the maintainer's call.

## How to add a parity proof (when a backend reaches it)

1. Rip the **same disc** (*The Police — …: The Classics*, AccurateRip offset
   +667 on the BDR-209D) with the backend, in the format you're proving.
2. Run the parity checker against the EAC baseline:
   ```
   python3 scripts/eac_parity.py \
       output_reference/EAC_flac/eac_baseline_police_classics.log \
       path/to/the/backend/Album.log
   ```
   It prints a per-track PASS/FAIL table and exits 0 only on full parity. (It
   auto-detects EAC / whipper / cyanrip log formats; the comparison logic is
   `platterpus.parity`.)
3. When it passes, drop the backend's `.log` (and `.cue`) into the matching
   directory above, and tick the task in `TASKS.md` with the date + result
   ("14/14 Copy CRCs match EAC").

That commit is the durable evidence the backend is bit-perfect against EAC.

> A second, unrelated EAC sample log (*Shark Tale* soundtrack) lives in
> `../tests/fixtures/rip_log_eac_reference.log`; it's a format-reference sample for `docs/eac-parity.md`
> (not parsed by any test), not a parity baseline.

---

*Last updated for Platterpus v0.6.4b13.*
