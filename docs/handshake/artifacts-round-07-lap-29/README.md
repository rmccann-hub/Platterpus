# Round 7 lap 29 rig rip (`platterpus-fork-g9048082`)

The rig rip round 7 lap 29 rests on, with the fork build `g9048082`: the ripper's log, its EAC-compatible rendering, the cue sheet, our addendum, our per-rip `.platterpus.json` report, and the rig evidence sheet.

**Where the files are (HR-2, protocol v9 §17).** From HR-2's move these files are
on this repository's `evidence` branch, not on `main`; this README stays on both,
as the folder's index (HR-2 point 5a and HR-2.1 a). Each one's evidence commit is
its row in `docs/evidence-manifest.tsv`, and a
lap cites one as `platterpus@<evidence commit>:<path>` with its SHA-256. A tool reads
one by fetching that commit by hash into a temporary repository
(`scripts/laplang/evidence.py`), never into a working clone.

| file | bytes | sha256 | on |
|---|---:|---|---|
| `round-07-lap-29-rig-rip-g9048082-eac-compatible.log` | 8,573 | `7eb514c2425298a23df76455696269e81ad43f1a6832a18a020775c0e75d50bf` | `evidence` |
| `round-07-lap-29-rig-rip-g9048082-rig-evidence.txt` | 3,755 | `faf3ffa6e0f16866f8fcbcbfb198780d6a6556947934ee07674ffb05737f7603` | `evidence` |
| `round-07-lap-29-rig-rip-g9048082.cue` | 2,810 | `25c5195cf1a3ae3888a2bf833d150fc804b52e525a4be35ee88afd933229cff1` | `evidence` |
| `round-07-lap-29-rig-rip-g9048082.log` | 39,054 | `d71c29c83b1ce133e52f7d74a0477cca6b61f6e707cc2c7b031bb2abec6c7172` | `evidence` |
| `round-07-lap-29-rig-rip-g9048082.platterpus-addendum.txt` | 1,352 | `fa726b7cf16908150a0070f77092e848231770cb3d79d18f3178c85e6a1e5d09` | `evidence` |
| `round-07-lap-29-rig-rip-g9048082.platterpus.json` | 4,446,469 | `ca253112abdc3a86fe18b6a084f4201b1dde6861cae0a7bd589dcfce87cd6524` | `evidence` |
