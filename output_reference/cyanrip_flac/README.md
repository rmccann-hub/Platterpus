# cyanrip FLAC — EAC parity comparison

Real cyanrip 0.9.3 rip of the baseline disc (**The Police — *Every Breath You
Take: The Classics***), on the Pioneer BDR-209D (+667 offset), captured
2026-06-27 from a hardware run. Stored here as the **text proof** (log + cue);
the audio is never committed (Critical Rule #8) — parity is proven by the
per-track CRCs, not by the PCM.

Compared against [`../EAC_flac/`](../EAC_flac/) (EAC V1.8, same disc, same drive,
same +667 offset). The comparison matches EAC's per-track **Copy CRC** against
cyanrip's **EAC CRC32** (cyanrip computes the EAC-style CRC, so the two are
directly comparable).

## Result: 12 / 14 tracks byte-identical to EAC

| Track | EAC Copy CRC | cyanrip EAC CRC32 | Match |
|------:|:-------------|:------------------|:-----:|
| 1  | B0D122E7 | B0D122E7 | ✅ |
| 2  | 985AAE32 | 985AAE32 | ✅ |
| 3  | 59D352DD | A8591346 | ❌ |
| 4  | 60D796AE | 60D796AE | ✅ |
| 5  | E0036697 | 4065BECC | ❌ |
| 6  | B32769D6 | B32769D6 | ✅ |
| 7  | CCBFF669 | CCBFF669 | ✅ |
| 8  | D723C1B0 | D723C1B0 | ✅ |
| 9  | 6F6E4A5F | 6F6E4A5F | ✅ |
| 10 | 3A33519F | 3A33519F | ✅ |
| 11 | 56BFC63D | 56BFC63D | ✅ |
| 12 | D78CEAEF | D78CEAEF | ✅ |
| 13 | DA6A4DAF | DA6A4DAF | ✅ |
| 14 | 787BA2D6 | 787BA2D6 | ✅ |

- **TOC is identical** — every track's start/end sector matches EAC exactly
  (same disc geometry, same +667 read offset).
- **Both rips report AccurateRip confidence 200** where they verify.

## The two tracks that differ

- **Track 5 — a marginal spot on this physical disc, not a ripper fault.**
  EAC *also* could not verify track 5 ("1 track could not be verified as
  accurate"), and the EAC log's CTDB pass shows track 5 "Differs in 3 samples
  @02:24:59". cyanrip rates it "partially accurately ripped" via the AccurateRip
  *offset-450* check. So both rippers hit the same ~3-sample trouble spot and
  resolved it slightly differently — this is the disc, and a tie.

- **Track 3 — a genuine cyanrip ↔ EAC divergence.** EAC matched the main
  AccurateRip database (confidence 200); cyanrip matched only the offset-450
  variant ("partially accurately ripped"), and the CRCs differ. cyanrip reported
  **0 read errors** but did 58 `FIXUP_ATOM` corrections, so a few samples on
  track 3 resolved differently from the AccurateRip consensus EAC matched. For
  archival purism this is the one track where EAC's result is the more "standard"
  one; a re-rip or a CUETools repair would likely reconcile it.

## Gap handling (the EAC "Detect Gaps" question)

EAC ran its **Detect Gaps** pass and recorded index-00 **pre-gaps** on 10 of 14
tracks (its cue has `INDEX 00`/`INDEX 01` pairs; "Gap handling: Appended to
previous track"). **cyanrip does not record pre-gaps** — every track in its cue
is a plain `INDEX 01 00:00:00`, one file per track, no `INDEX 00`.

This is a **cue-metadata** difference, not (mostly) an audio one: both rip at the
same TOC track boundaries with append-to-previous semantics, which is why 12/14
tracks are byte-identical. For split-per-track FLACs (what both produced) the
pre-gap audio lands at the end of the previous track either way; EAC's cue just
*documents* where the index points are and cyanrip's doesn't. It would matter for
a single-file image or a gapless re-burn, not for tagged per-track files.

## Status

Documented near-parity (12/14 exact; T5 = a disc spot both rippers fail; T3 = a
real divergence to investigate), kept per the project's "store the text, document
the imperfection" practice — not the originally-hoped *full* bit-perfect parity,
but strong evidence that cyanrip ≈ EAC on this disc/drive. The album name shows
the `∶` (U+2236) look-alike because cyanrip can't take a literal colon on its
command line; Whipper GUI ≥ 0.3.10 restores the real `:` in the FLAC **tags**
after the rip (the folder name and this log keep `∶`).
