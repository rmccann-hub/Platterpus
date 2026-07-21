# Archived investigations

Point-in-time investigation write-ups, kept for their audit trail. Their
**durable conclusions have already graduated** into the living docs — read
those first; these are the dated narrative behind them.

| Archived file | Durable conclusions now live in |
|---|---|
| [`ecosystem-audit-2026-06.md`](ecosystem-audit-2026-06.md) — whipper-stalled / cyanrip-successor audit, contribute-vs-fork decision, phased `CyanripImpl` plan | **PLANNING.md KDD-18** (the decision + rationale) and **DEPENDENCIES.md** (whipper/cyanrip rows, the COPR `barsnick/non-fed` packaging detail, the `pkg_resources`/Python-3.14 time-bomb) |
| [`offset-investigation-2026-06.md`](offset-investigation-2026-06.md) — why whipper's `offset find` is unreliable; the AccurateRip offset-by-drive-model refactor | **`adapters/accuraterip_offsets.py`** (the curated +667 entries and the user > curated > bundled layering precedence) **and `scripts/update_drive_offsets.py`** (the `DriveOffsets.bin` 69-byte record format, the +667 validation gate, and the refresh procedure) |
| [`upstream-modification-investigation.md`](upstream-modification-investigation.md) — EAC-parity "modify upstream?" audit; the **CTDB Phase-1 wire-format/CRC spec**; the `ctdb-cli`-is-.NET correction; the "do not revisit" non-feasible list | **PLANNING.md KDD-14 / KDD-16** point here for the original CTDB Phase-1 wire-format/CRC spec (since built as `src/platterpus/ctdb/`, GUI-wired 2026-06-17, and hardware-validated 2026-07-07 — KDD-16); the non-feasible list overlaps the brief's *Out of scope* |
| [`audit-2026-07-02.md`](audit-2026-07-02.md) — the 13-agent full-audit report that drove the 0.4.13–0.4.16 fix batch | Fixes shipped as v0.4.13–v0.4.16 (CHANGELOG); §E's deferred remainders graduated to the **TASKS.md Documentation backlog** (hardware checkboxes, property surfaces, Phase-7/TD-1 items) |
| [`trust-audit-2026-07-08.md`](trust-audit-2026-07-08.md) — the seven-category trust & supply-chain audit behind the v0.4.22 hardening | In-release fixes shipped in v0.4.22/v0.4.23 (CHANGELOG); deferred items graduated to the **TASKS.md trust-hardening section** (release signing + hash-pinning still open there) |

These files are not maintained going forward. If a conclusion here ever
conflicts with a living doc, the living doc wins.

## External reference material

Third-party references distilled for context — *not* our own investigations, so
they carry no "graduated conclusions" row. Treat them as parity targets/principles
to mine, not as authority over the living docs.

| Archived file | What it is |
|---|---|
| [`archival-extraction-guide-2026-06.md`](archival-extraction-guide-2026-06.md) — **our own cited summary** of a user-supplied EAC 1.8 / FLAC 1.5 / WavPack / LAME master guide | Our paraphrased summary of the guide's actionable EAC/Windows-centric archival targets (FLAC `-V` verify + compression level, the LAME `-q 4` `noise_shaping_amp` gotcha for MP3 — shipped 2026-06-26, KDD-22 — and WAV metadata limits), with links to the primary tool sites. The **verbatim third-party text was removed 2026-07-07** (provenance/permission hygiene for a public repo); the summary feeds the **2026-06-23 gap analysis** in `docs/session-log.md`; several source claims are flagged *verify before relying*. |

---

*Last updated for Platterpus v0.5.0.*
