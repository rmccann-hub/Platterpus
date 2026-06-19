# `output_reference/` — rip-output baselines for EAC parity

This directory holds **reference rip outputs** used to prove Whipper GUI's rips
are correct by comparing them against a known-good baseline.

**EAC is the baseline.** Exact Audio Copy is the gold standard this project is
measured against (see [`../docs/test-plan.md`](../docs/test-plan.md) → *EAC
output-parity check*). The EAC reference is committed here now. Outputs from the
other backends (whipper, cyanrip) are added **only once they reach parity with
EAC**, as proof — not before.

## What "parity" means here (and why there's no audio)

A rip is bit-perfect when its **per-track CRC matches EAC's**. EAC's log records,
for every track, a `Test CRC` and a `Copy CRC` (e.g. `Copy CRC B0D122E7`); when
those two match each other the rip is internally consistent, and when a ripper's
`Copy CRC` equals EAC's for the same track the two rips are **bit-identical**.
AccurateRip / CTDB confidence values in the log corroborate this against the
wider community database.

So the comparison is **log-to-log (CRCs)**, not audio-to-audio. That's why this
directory stores **logs and cue sheets, never the decoded audio**:

- **Copyright.** This repository is public. The reference disc (*The Police —
  Every Breath You Take: The Classics*) is a commercial recording; committing
  its FLAC/WAV/MP3 audio here would publicly redistribute copyrighted material.
  Owning the disc does not grant that right.
- **It isn't needed.** The CRCs in the log already prove bit-perfection.
- **Repo bloat.** Full-album audio is hundreds of MB and would live in git
  history forever.

If a test ever genuinely needs real PCM to exercise the decode/CRC path, use a
**short, freely-licensed or self-generated** sample (CC0 / public-domain / a
synthetic tone with a known CRC), and **Git LFS** for any binary — never a
commercial track.

## Layout

| Directory | What goes here | Status |
|-----------|----------------|--------|
| `EAC_flac/` | The EAC baseline: extraction **log + cue** (the CRCs are the bit-perfect reference). | ✅ committed (baseline) |
| `EAC_mp3/` | EAC's MP3-reference log/cue, when we baseline lossy output (MP3 is P1; the *extraction* CRCs are shared with `EAC_flac`, the lossy encode is not bit-comparable). | ⬜ not yet |
| `whipper_flac/` | A whipper rip's **log (+ cue)** of the same disc — added **only when its Copy CRCs match `EAC_flac`'s**. | ⬜ pending parity |
| `cyanrip_flac/` | A cyanrip rip's **log** of the same disc — added **only when its CRCs match `EAC_flac`'s** (this also closes the >587 read-offset question, KDD-18). | ⬜ pending parity |

## How to add a parity proof (when a backend reaches it)

1. Rip the **same disc** (`The Police — …: The Classics`, AccurateRip offset
   +667 on the BDR-209D) with the backend.
2. Confirm every track's `Copy CRC` equals the value in
   `EAC_flac/eac_baseline_police_classics.log`.
3. Drop the backend's `.log` (and `.cue`) into its directory, and add a one-line
   note here with the date and the result ("12/12 Copy CRCs match EAC").

That commit is the durable evidence the backend is bit-perfect against EAC.

> A second, unrelated EAC sample log (*Shark Tale* soundtrack) lives in
> `../tests/fixtures/rip_log_eac_reference.log`; it's a parser sample, not a
> parity baseline.
