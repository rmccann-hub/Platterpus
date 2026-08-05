# `cyanrip_fork_flac/` — the rip that reached **full 14/14 EAC parity**

A real rip of the EAC baseline disc, **same disc, same drive**, captured on the
Bazzite + Pioneer BDR-209D rig on **2026-08-04**.

```
Platterpus  0.6.4b3 (build 1671c21)
cyanrip     0.9.4-rc1+platterpus.5-beta.1  (platterpus-fork-g9003e6f)
drive       PIONEER  BD-RW   BDR-209D 1.51   |   read offset  +667
disc        The Police — Every Breath You Take: The Classics  (14 tracks)
```

## What it proves

**14 of 14 tracks are bit-identical to EAC** — every `Copy CRC` equal, track for
track, against `../EAC_flac/eac_baseline_police_classics.log`. That closes the
parity goal stated in `../README.md`.

**All ten of EAC's `Pre-gap length` rows match ours to the hundredth of a second,
in order.** cyanrip 0.9.3 reported "None signalled" and found none; the fork reads
them from the sub-channel and finds exactly EAC's ten. The KDD-32 / `INDEX 00`
capability gap that `eac_log_export._gap_handling` documented as *our one
measurable archival shortfall against EAC* is **closed for the fork**. It remains
open for stock 0.9.3, which is why `../cyanrip_flac/` (a 0.9.3 rip) is still here
and still cited by tests.

**Track 5 got there via the auto-fix.** Its first read pass produced `6902BCF0`,
which does **not** match EAC; only the `+450` offset-variant matched AccurateRip.
The secure re-rip produced `E0036697` — EAC's value — and swapped it in. The
whole-disc log records the first pass; the `[Platterpus auto-fix addendum]` records
the shipped file. So this artifact is also the proof that the re-rip feature does
the thing it exists for.

All of the above is asserted by `tests/test_fork_rip_eac_parity.py`, which **reads
these files** rather than restating their numbers — a remembered measurement has no
provenance you can re-check.

## What it caught

Reading this artifact found three defects that every green test had missed:

1. **The `Gap handling` row was broken on every real disc.** The fork prints
   `merging into track N`; our matcher looked for `merged`. One word ending, and
   the row read "(not reported by the ripper)" where EAC says "Appended to previous
   track". The fork had published `merging into track %i` in **round 5** — the
   evidence was in a committed file in this repo for two rounds. Two separate tests
   pinned the invented word.
2. **`artifacts.ripper_stdout` was empty on every completed rip.** The report is
   re-written by each post-rip step, and the writer read the *live worker*, which
   `_on_rip_finished` clears in between — behind a guard whose only effect was to
   emit `""`. The block's own `source` string still promised "complete even when the
   ripper was killed": accurate about the mechanism, false about the file.
3. **`self_check` was an undeclared top-level key.** It is added by `write_report`
   after `_build`, so the completeness sweep — which inspected the *builder* —
   could not see it. The sweep now reads a written file.

## Files

| file | what it is |
|---|---|
| `cyanrip_fork_police_classics.log` | the ripper's whole-disc log, verbatim, **including the auto-fix addendum** |
| `cyanrip_fork_police_classics_EACcompatible.log` | our EAC-layout render of the same rip — the file compared against EAC's |
| `cyanrip_fork_police_classics.cue` | the gap-appended cue sheet, with `INDEX 00` pre-gap markers |
| `cyanrip_fork_police_classics.platterpus.json` | the machine-readable report (schema **v15** — this rip predates the v16 `diagnostics` block). 82% of its bulk is the embedded session DEBUG log, kept because it is the artifact rather than a summary of one |

**No audio, here or anywhere** (CLAUDE.md critical rule #8). The CRCs prove
bit-perfection without it — that is the entire reason this directory is text.

---

*Last updated for Platterpus v0.6.4b8.*
