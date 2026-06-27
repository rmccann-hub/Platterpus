# cyanrip MP3 — EAC extraction-parity proof

Real Whipper-GUI **MP3-output** rip of the baseline disc (**The Police — *Every
Breath You Take: The Classics***), cyanrip backend, Pioneer BDR-209D, +667
offset, 2026-06-27. Text proof only (log + cue); no audio committed (Rule #8).

MP3 is **lossy**, so the *encoded* audio is not bit-comparable. "Parity" here
means the **extraction** was accurate: the per-track Copy CRCs (computed by
cyanrip on the read PCM, *before* encoding) match the EAC FLAC baseline. The MP3
files are derived from that exact verified PCM.

**Note — the log says `Outputs: flac` and the cue references `.flac`.** That's the
project's *transcode-always* model (KDD-22): cyanrip always extracts to FLAC, and
the GUI derives MP3 from it with ffmpeg. So this cyanrip log/cue *is* the FLAC
extraction record; the MP3s are a lossy derivative of the same samples. The
extraction CRCs are the proof.

## Result vs EAC baseline: 13 / 14 tracks match

Checked with `scripts/eac_parity.py` against
[`../EAC_flac/eac_baseline_police_classics.log`](../EAC_flac/). 13/14 PASS; only
**Track 5** differs.

- **Track 3 matches EAC exactly (`59D352DD`).** The earlier cyanrip *FLAC* run
  ([`../cyanrip_flac/`](../cyanrip_flac/)) missed track 3 (`A8591346`, offset-450
  partial). This run got it right — **confirming that track-3 divergence was
  transient and a re-rip resolves it** (exactly the §P2 prediction in
  [`../../docs/eac-parity-investigation.md`](../../docs/eac-parity-investigation.md)).
- **Track 5 is a genuinely unstable spot on the disc.** Three rips have produced
  three different track-5 CRCs (EAC `E0036697`, cyanrip-FLAC `4065BECC`,
  cyanrip-MP3 `6902BCF0`), and EAC itself could not verify track 5. This is the
  disc surface, not the ripper — repair-class tooling (CUETools/CTDB) or a
  cleaner disc is the only path to a verified track 5.

So this extraction is **better than the FLAC reference** (13/14 vs 12/14): the
only remaining gap is the disc's own bad spot.
