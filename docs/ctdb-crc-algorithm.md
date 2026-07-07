# The CTDB audio CRC (KDD-16)

Reference for the CUETools Database (CTDB) per-disc audio CRC as Platterpus
computes it. Reconstructed clean-room from the **LGPL** `CUETools.AccurateRip` /
`CUETools.Codecs` source (github.com/gchudov/cuetools.net) — the algorithm is a
*fact*, reimplemented here, not ported from the GPL `python-cuetoolsdb`.

> ⚠️ **Hardware-validation gate.** The algorithm below is source-grounded and
> reproduced in Python, but `ctdb/crc.py::CRC_VALIDATED` stays **False** until a
> real, in-database disc confirms it end-to-end (`platterpus --ctdb-calibrate`).
> Until then a CTDB `MATCH` is shown as *experimental* and a `NO_MATCH` says
> nothing about the rip (the fail-safe direction). Flipping the flag is a
> one-line change plus baking the confirmed vector as a regression fixture.

## The algorithm

`CTDBCRC(offset)` is a **standard IEEE / zlib CRC-32** (polynomial `0x04c11db7`,
reflected in/out, init/xor `0xffffffff` — exactly `zlib.crc32`) over the
**whole-disc little-endian 16-bit stereo PCM**, with a guard band trimmed off
each end so the value survives a small pressing/drive offset:

```
stride       = 10 * 588 * 2            # = 11760  (16-bit words; CUEToolsDB.Init)
laststride   = stride + (2 * total_frames) mod stride
front_frames = stride / 2              # = 5880   (fixed for every disc = 10 sectors)
back_frames  = laststride / 2          # length-dependent

CTDBCRC(offset) = zlib.crc32( pcm[ (front+offset)*4 : len - (back-offset)*4 ] )
```

- `total_frames` is the whole-disc audio length in stereo frames =
  `(leadout - 150) * 588` (lead-in removed), which for a real CD equals the
  concatenated decoded-FLAC frame count (tracks are sector-aligned).
- `offset` slides a **constant-length window** across the guard band
  (`front += offset; back -= offset`), tolerance **`±(stride/2 − 1) = ±5879`
  frames** — CueTools `CDRepair.FindOffset` sweeps `1 − stride/2 … stride/2`.
  This is DELIBERATELY WIDER than AccurateRip's ±2939 (`5·588 − 1`); real
  pressing offsets routinely exceed the AR window. `offset = 0` is the value
  stored in the database; a correctly-offset rip matches there.

### Why the earlier attempts failed

Two separate off-by-a-constant bugs, both since fixed (verified against the
CueTools C# source):

1. **Trim (v0.4.16 placeholder).** It computed a plain `zlib.crc32` of the
   **untrimmed** disc (trim `(0,0)`). The CRC polynomial was always right — the
   trim was wrong. The real trim is `front=5880`, `back=9996` frames
   (asymmetric); v0.4.17 fixed this.
2. **Offset range (v0.4.17).** The trim was now correct, but calibration swept
   only AccurateRip's **±2939**. CTDB matches over **±5879**; a pressing aligned
   in (2939, 5879] was never reached, so a genuinely-good in-database disc still
   reported `NO_MATCH`. v0.4.18 widened the sweep to the CTDB range. The
   CRC/trim/combine were confirmed bit-for-bit correct.

## How Platterpus uses it

- **Verify** (`ctdb/verify.py`): computes `CTDBCRC(0)` streamed track-by-track
  (`crc.ctdb_crc_offset0_streaming`, one track resident at a time — #39 memory
  fix) using `total_frames` from the TOC, and compares to the DB entries.
- **Calibrate** (`ctdb/calibrate.py`, `platterpus --ctdb-calibrate`): sweeps the
  full ±5879 offset window and reports which offset reproduces a DB CRC. Uses the
  zlib `crc32_combine` (GF(2) "append N zero bytes") operator so the whole sweep
  is a few big CRC passes plus cheap algebra, not 5 879 re-CRCs of a ~600 MB disc.
  A match at `offset 0` means the rip's read offset aligns with that pressing; a
  match at `±k` means it differs by `k` samples (still a valid verify).

## Confirming on hardware

Run `platterpus --ctdb-calibrate "<album folder>"` on a disc that is in CTDB.
Expect a `✅ MATCH` at (ideally) `offset=+0` against the highest-confidence
entry. Paste the offset + CRC + trim back; then `CRC_VALIDATED` flips to `True`
with that vector as the KDD-16 regression fixture, and CTDB `MATCH` becomes a
plain "verified" instead of "experimental".
