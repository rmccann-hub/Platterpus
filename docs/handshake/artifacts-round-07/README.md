# Round 7 lap 23 rig rip (`platterpus-fork-gc5fb909`)

The rig session of round 7 lap 23: one rip on the Bazzite + Pioneer BDR-209D rig with the fork build `gc5fb909`, as our lap 23 cited it. The session's results sheet, the ripper's log, its EAC-compatible rendering, the cue sheet, our addendum, and our per-rip `.platterpus.json` report.

**Where the files are (HR-2, protocol v9 §17).** From HR-2's move these files are
on this repository's `evidence` branch, not on `main`; this README stays on both,
as the folder's index (HR-2 point 5a and HR-2.1 a). Each one's evidence commit is
its row in `docs/evidence-manifest.tsv`, and a
lap cites one as `platterpus@<evidence commit>:<path>` with its SHA-256. A tool reads
one by fetching that commit by hash into a temporary repository
(`scripts/laplang/evidence.py`), never into a working clone.

| file | bytes | sha256 | on |
|---|---:|---|---|
| `rig-session-results-c5fb909.md` | 12,162 | `0d0b963a1b5464e5a650ff6f0e1a40075aad4093a1074b5527747d39e6a2bab8` | `evidence` |
| `round-07-lap-23-rig-rip-gc5fb909-eac-compatible.log` | 8,572 | `cf6cbf97a2ccd4313dd60f67bb1a8325ed5d29b20b5fcec6679116730ab4b046` | `evidence` |
| `round-07-lap-23-rig-rip-gc5fb909.cue` | 2,810 | `9fd2dd93356ec737cf499376fe6f8d31c55711fb7c8a82075e2f2f8b2182ff22` | `evidence` |
| `round-07-lap-23-rig-rip-gc5fb909.log` | 38,975 | `91b33b8c475715ac5b084963f45828ec4f8028a77d6c89cd47305181063e47db` | `evidence` |
| `round-07-lap-23-rig-rip-gc5fb909.platterpus-addendum.txt` | 1,352 | `2c4a552dcd0d8ebeeb633e2d84a9436b4198945c79458e0772b79836b8b4e9c6` | `evidence` |
| `round-07-lap-23-rig-rip-gc5fb909.platterpus.json` | 1,537,831 | `ae8662b310cb5c1c1e448ee5c7ce8be1957440cfa41e142b4a0265ccf9a39c90` | `evidence` |
