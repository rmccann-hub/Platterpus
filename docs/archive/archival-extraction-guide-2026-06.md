# EAC-archival parity targets (our summary)

> **What this is.** Our own condensed summary of the *actionable* archival
> extraction/compression targets from a user-supplied master guide,
> *"Archival-Grade Digital Audio Extraction and Compression"* (added 2026-06-23,
> EAC 1.8 / FLAC 1.5 / WavPack 5.9 / LAME 3.100.1, Windows-centric).
>
> **The verbatim third-party text was removed (2026-07-07)** — reproducing a
> full external document in a public repo is a provenance/permission risk we
> don't need to carry. This is a paraphrased summary of the parts we actually
> use as *parity targets*, in our own words. Treat it as **targets and
> principles, not literal config**: it describes EAC on Windows; Platterpus
> drives cyanrip on Linux, and the concrete mapping lives in the README
> "Capability & EAC-parity matrix" + [`../ripper-engine-strategy.md`](../ripper-engine-strategy.md).
> A couple of the source's claims are the author's assertions flagged
> **verify-before-relying** (notably the LAME 3.100.1 `noise_shaping_amp` / `-q 4`
> r6147 claim and some exact version/date numbers).

---

## The principle

Red Book audio CDs lack the sync/error-correction layer of data CDs, so a naive
OS read yields jitter and dropped samples. Archival extraction means forcing
**bit-parity** with the original PCM: re-read until the reads agree, correct for
the drive's read offset, and verify the result against independent databases
(AccurateRip, CTDB). FLAC is the lossless master; WAV is the raw baseline;
WavPack and MP3 are derived.

## EAC drive / extraction settings the guide calls out (parity checklist)

- **Secure Mode** — re-read sectors until statistical parity; never trust a
  single read.
- **Accurate Stream** — assume the drive has it (nearly all modern drives do).
- **Drive caches audio data → defeat the cache** — enable so EAC flushes the
  cache between re-reads, forcing genuinely independent reads.
- **C2 error pointers — leave DISABLED**, *even if the drive reports support*.
  Many drives falsely report clean reads while dropping C2 internally, so the
  guide relies on software re-reading, not C2. (So "no C2" is best practice, not
  a deficiency.)
- **Read sample offset correction** — set from the AccurateRip drive database
  (auto via a "Key Disc", or entered manually as a signed integer).
- **Overread into Lead-In/Lead-Out** — leave OFF unless the drive's firmware is
  verified to support it without errors.
- **Allow speed reduction during extraction** — on, so the drive slows over
  scratches instead of erroring.
- **Gap/Index retrieval — Detection Method A, "Secure" accuracy** (fall back to
  B/C only if A can't read the gaps).
- **AccurateRip + CTDB** — use both for verification/metadata; freedb is dead.

## Encoder targets (best-practice command intent)

- **FLAC 1.5** — max compression + verify + multithread: `-8 -V -j <N>`, tags as
  native Vorbis comments. `-V` decodes the result and compares it to the source
  (guards disk-write corruption).
- **WAV** — uncompressed PCM baseline; no standardized tagging (RIFF), so it's a
  staging/comparison format, not the archive.
- **WavPack 5.9** — hybrid lossless (`-c` writes the `.wv` lossy base + a `.wvc`
  correction file that recombines to bit-exact), plus `-m` (store MD5) and `-v`
  (verify pass).
- **LAME 3.100.1 MP3** — best-practice VBR (`-V 0`), with the author's
  **verify-before-relying** claim that `-q 4` sidesteps an `noise_shaping_amp`
  regression (SVN r6147) that degrades `-q 0..3`. Keep Joint Stereo (Mid/Side)
  on. *N.B.:* Platterpus encodes MP3 with **ffmpeg**, not `lame.exe -q 0..3`, so
  this specific LAME command-line footgun isn't in our path.

## How Platterpus maps to these

See the README's **"Capability & EAC-parity matrix"** and **"Point-by-point vs.
the EAC 'perfect rip' checklist"** for the line-by-line mapping (Secure Mode →
cyanrip paranoia + `-Z`, C2 correctly off, offset via AccurateRip, gaps via TOC
+ cyanrip PR #115, FLAC `-8 -V`, etc.), and `../ripper-engine-strategy.md` for
the deferred gaps.

## Sources referenced

The source guide is a user-supplied document (not a public URL we can cite), but
the authoritative tool/reference websites it points to are kept here so a reader
can go to the primary source rather than trusting a paraphrase:

- **Exact Audio Copy** — <https://www.exactaudiocopy.de/> (the reference ripper;
  our parity target)
- **FLAC** — <https://xiph.org/flac/> (encoder + format spec)
- **WavPack** — <https://www.wavpack.com/> (hybrid-lossless encoder)
- **LAME** — <https://lame.sourceforge.io/> (the MP3 encoder the guide's
  `-q 4`/`noise_shaping_amp` claim concerns; *verify before relying* — and note
  Platterpus encodes MP3 via ffmpeg, not LAME directly)
- **AccurateRip** — <https://www.accuraterip.com/> and **CueTools DB (CTDB)** —
  <http://cue.tools/> (the two verification databases)

---

*Last updated for Platterpus v0.4.18.*
