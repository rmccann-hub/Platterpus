# EAC "WAV" slot — WavPack reference (imperfect, replaceable)

Holds an EAC rip of the baseline disc (*The Police — Every Breath You Take: The
Classics*, BDR-209D, offset +667). **Text only — no audio** (Critical Rule #8).

- `eac_wav_police_classics.log` / `.cue` — the EAC rip (2026-06-25).

## This rip is **WavPack** (intentional — kept as-is)

EAC's "User Defined Encoder" for this rip is **`wavpack.exe -h -m`** — so the
output is **WavPack (`.wv`)**: a *lossless-compressed* format with APEv2-style
tags (EAC wrote `-w "Artist=…"` etc.), not plain uncompressed PCM WAV. The
maintainer confirmed this is fine — use the WavPack rip as the WAV-slot reference
(2026-06-25). Notes:

- **For parity it's equivalent to WAV.** WavPack is lossless → decodes to
  identical PCM → identical per-track Copy CRC, so it compares against the FLAC
  baseline exactly like a plain-WAV rip would. (Our own plain-WAV output, when
  built, also proves parity against the **FLAC** baseline — not against this log
  specifically — so the format difference doesn't matter to the matrix.)
- **WavPack is a legitimate tagged-lossless format** and a candidate output of its
  own (cyanrip lists `wavpack` under `-o`). WavPack has since **shipped** as a GUI
  output format (2026-06-26, KDD-22; decisions locked in
  `docs/mp3-wav-support.md` §5) — which makes this WavPack reference doubly
  useful.

## Extraction quality: 13/14 (best of the three sessions)

- **13/14 Copy CRCs match** `../EAC_flac/` (the clean baseline) — the best run so
  far.
- **Track 3** differs (Copy `329DC760` ≠ baseline `59D352DD`) — the disc's
  persistent marginal spot; a read error this session, not a format issue.
- **Track 5** differs from AccurateRip but matches our baseline — the known,
  consistent disc/pressing quirk, not an error.
- Track 4 came back **clean** this time (it had errored in the MP3 session),
  confirming the trouble is transient/disc-surface, not systematic.

```
python3 scripts/eac_parity.py \
    output_reference/EAC_flac/eac_baseline_police_classics.log \
    output_reference/EAC_wav/eac_wav_police_classics.log
# → 13/14 tracks match — NOT parity (track 3)
```

**To replace it:** clean the disc around track 3 and re-rip in Test & Copy mode
until all 14 match, then overwrite these files. (Keeping WavPack is fine — the
maintainer's call.)

## On format & encoding

The shared **extraction CRCs** (identical to `../EAC_flac/`) are what compare;
the container/encoder differs. The log is stored **verbatim in EAC's native
UTF-16**; the parity checker and tests decode it via
`platterpus.parity.decode_log_bytes` (`.gitattributes` marks
`output_reference/**/*.log` `-text` so the UTF-16 isn't corrupted). Cue nit: this
session's cue dropped track 10's ISRC. No audio is committed — see
[`../README.md`](../README.md).

---

*Last updated for Platterpus v0.5.0.*
