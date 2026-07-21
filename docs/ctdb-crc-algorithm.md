# The CTDB audio CRC (KDD-16)

Reference for the CUETools Database (CTDB) per-disc audio CRC as Platterpus
computes it. Reconstructed clean-room from the **LGPL** `CUETools.AccurateRip` /
`CUETools.Codecs` source (github.com/gchudov/cuetools.net) — the algorithm is a
*fact*, reimplemented here, not ported from the GPL `python-cuetoolsdb`.

> ✅ **Hardware-validation gate — PASSED (2026-07-07).** The algorithm below is
> source-grounded, reproduced in Python, and now **confirmed end-to-end on real
> hardware**: `platterpus --ctdb-calibrate` on an in-database disc reproduced a
> stored CTDB CRC at aligned `offset=+0` (see *Confirming on hardware* below), so
> `ctdb/crc.py::CRC_VALIDATED` is **True** — a CTDB `MATCH` now reads as
> *verified* and a `NO_MATCH` legitimately means the rip differs. The confirmed
> vector is baked as a regression fixture (`crc.CONFIRMED_VECTOR` +
> `tests/test_ctdb_verify.py::test_kdd16_confirmed_vector_trim`).

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
   trim was wrong. The real trim is asymmetric: `front=5880` fixed, back length-dependent
   (`laststride/2` — 9996 for the Police disc's 157,999,716 frames); v0.4.17 fixed this.
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
  is a few big CRC passes plus cheap algebra, not ~11 759 re-CRCs of a ~600 MB disc.
  A match at `offset 0` means the rip's read offset aligns with that pressing; a
  match at `±k` means it differs by `k` samples (still a valid verify).

## Confirming on hardware — done

Confirmed 2026-07-07 (Platterpus build `f50258c`). Running
`platterpus --ctdb-calibrate "<album folder>"` on *The Police — Every Breath You
Take: The Classics* (14 tracks, Pioneer BDR-209D, read offset +667) reported:

```
Decoded whole-disc PCM: 631998864 bytes = 157999716 stereo frames.
Trim (offset 0): front=5880 back=9996 frames.
✅ MATCH — the CTDB-CRC algorithm is confirmed:
   offset=+0 → CRC 5da89fcd (confidence 1) (aligned — read offset matches this pressing)
```

Our offset-0 CRC reproduced a CTDB-stored value bit-exactly — an aligned
`offset=+0` match — which confirms the trim + polynomial + offset window against
the database. (It matched a confidence-1 pressing rather than the dominant
confidence-1350 one; that only means this physical disc is a less-common
pressing — it doesn't affect *algorithm* correctness, which is all the gate
tests.) The vector `(total_frames, front, back, offset, crc) =
(157_999_716, 5880, 9996, 0, 0x5DA89FCD)` is recorded as `crc.CONFIRMED_VECTOR`
and pinned by `tests/test_ctdb_verify.py::test_kdd16_confirmed_vector_trim`.

To re-confirm (e.g. after any change to the trim/offset math), re-run the same
command on any in-CTDB disc and expect a `✅ MATCH` at `offset=+0`.

---

*Last updated for Platterpus v0.4.24.*
