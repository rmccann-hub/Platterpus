# Artifacts our laps carried (round 15 lap 13) and the LSL amendments

Files our own laps carried rather than filed from a bundle: round 15 lap 13's cancelled-rip log, rig-check manifest, run report, run transcript, and secure re-read logs (`g978f9b0`); and `lsl-amendments-1.md`, a specification the lap-language checker implements.

**Where the files are (HR-2, protocol v9 §17).** From HR-2's move these files are
on this repository's `evidence` branch, not on `main`; this README stays on both,
as the folder's index (HR-2 point 5a and HR-2.1 a). Each one's evidence commit is
its row in `docs/evidence-manifest.tsv`, and a
lap cites one as `platterpus@<evidence commit>:<path>` with its SHA-256. A tool reads
one by fetching that commit by hash into a temporary repository
(`scripts/laplang/evidence.py`), never into a working clone.

`lsl-amendments-1.md` is a specification, so it stays on `main` as well (HR-2 point 1).

| file | bytes | sha256 | on |
|---|---:|---|---|
| `lsl-amendments-1.md` | 17,666 | `72a4c65afde184f20f65ef32addbf93711d7e0e6669e711785b23de0bebb7592` | both branches |
| `round-15-lap-13-cancelled-rip-g978f9b0.log` | 11,903 | `acdf80b44ba4d62eb41cbd2f306e8ea34bdf863b61f76bf0d015ae32350af69d` | `evidence` |
| `round-15-lap-13-rig-check-manifest.txt` | 14,751 | `30388e7f887fc93b7a98860ee2916efa35a9aaad0dd110e23ce41afecef1a563` | `evidence` |
| `round-15-lap-13-run-report.json` | 134,930 | `7075f857ee75f992bd444da1c114513139c7e3909d8792bbd781bba8a4dfb388` | `evidence` |
| `round-15-lap-13-run-transcript.txt` | 94,926 | `1d4bb7aeb800308d815563164d52fe4c1f20fe6235c51aa1a390d2f0e5d30453` | `evidence` |
| `round-15-lap-13-secure-reread-eac-g978f9b0.log` | 10,415 | `0bf24a6e0a763af6ca3d1d1c60d8c04d57aab91234edd88597051c90376b592f` | `evidence` |
| `round-15-lap-13-secure-reread-g978f9b0.log` | 42,734 | `6e857f025f699c721e36c367098fc9f0bbdcb6d8028808d5cefe4bf5aec32aae` | `evidence` |
