# EAC "WAV" — reference (actually WavPack; imperfect, replaceable)

Holds an EAC rip of the baseline disc (*The Police — Every Breath You Take: The
Classics*, BDR-209D, offset +667). **Text only — no audio** (Critical Rule #8).

- `eac_wav_police_classics.log` / `.cue` — the EAC rip (2026-06-25).

## ⚠️ This rip is **WavPack**, not plain PCM WAV

EAC's "User Defined Encoder" for this rip is **`wavpack.exe -h -m`** — so the
output was **WavPack (`.wv`)**, a *lossless-compressed* format with APEv2-style
tags (EAC wrote `-w "Artist=…"` etc.), **not** the plain uncompressed PCM WAV our
planned WAV path produces (`ffmpeg … -c:a pcm_s16le`). Why it still belongs here:

- **For parity it's equivalent.** WavPack is lossless → decodes to identical PCM
  → identical per-track Copy CRC, so it compares against the FLAC baseline exactly
  like a plain-WAV rip would.
- **As a format reference it's different.** If you want this to document *plain
  WAV* (uncompressed, no tags — RIFF limitation), re-rip with EAC pointed at a WAV
  output, or accept that this documents the WavPack option instead. WavPack is a
  legitimate tagged-lossless choice (cyanrip lists `wavpack` under `-o`), but it's
  out of our current flac/wav/mp3 scope — flag for a product decision if wanted.

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
until all 14 match (and, if you want a *plain-WAV* reference, set EAC's encoder to
WAV rather than WavPack), then overwrite these files.

## On format & encoding

The shared **extraction CRCs** (identical to `../EAC_flac/`) are what compare;
the container/encoder differs. EAC's native log encoding is **UTF-16**; this copy
was converted to UTF-8 for readability (like the FLAC baseline). The parity
checker reads either (`whipper_gui.parity.decode_log_bytes`). Cue nit: this
session's cue dropped track 10's ISRC. No audio is committed — see
[`../README.md`](../README.md).
