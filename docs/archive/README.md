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

## Superseded rig-session sheets

One sheet per app-build/ripper-pin pairing, written to be read at the drive. Five of them
accumulated over eight days of a moving cyanrip pin, and the maintainer asked for the pile to
be combined — so there is now **one** living sheet,
[`docs/rig-session.md`](../rig-session.md), rewritten when the pair moves. These are the
dated originals; each is still the record of what was asked for and why on that pairing.

| Archived sheet | The pair it was written for, and what it settled |
|---|---|
| [`rig-session-c5fb909.md`](rig-session-c5fb909.md) | `v0.6.4b4` + cyanrip `c5fb909` (`beta.2`). The first sheet in the series: six steps cheapest-evidence-first, anchored against **EAC's committed baseline** rather than against the previous cyanrip run (comparing two runs of related builds is the shared-ancestor trap). Opens with a correction — `-O` (our overread toggle) and `-x` (their cache probe, which we never send) had both been called `-x` in the correspondence, and only one is ours. |
| [`rig-session-f5e11ba.md`](rig-session-f5e11ba.md) | `v0.6.4b6` + cyanrip `f5e11ba` (`beta.4`). Where the session became **three human steps and one command** — everything unattended moved into `scripts/rig_session.sh`, on the fork's own argument that *the rig session is the scarce resource*. Deliberately paired the app with the cutting-edge fork build rather than the conservative one, because their A2 denominator change (`1/1` → `1/14`, same disc, same track) cannot be verified anywhere except a real disc with an AccurateRip entry. |
| [`rig-session-b9.md`](rig-session-b9.md) | `v0.6.4b9`/`b10` + cyanrip `9048082` (`beta.5`). The first sheet whose primary instruction is *look at the screen*, because every defect it verified is one no artifact reports: a healthy secure re-read announced as *"the drive is stuck on a hard-to-read spot"* twice per disc, an ETA that climbed 54m → 5h40m in 70 seconds while the drive read perfectly at 1×, a track list opening on 2 rows of 14. Opens with the maintainer's own debug log beside cyanrip's progress lines in the same seconds — the pairing that turned a vague complaint into a diagnosis. |
| [`rig-session-b10.md`](rig-session-b10.md) | Same pair, revised mid-session. Kept for one reason worth preserving: it **corrects my own instruction**, not the app. `./platterpus-x86_64.AppImage --install-ripper` fails after the app relocates itself to `~/Applications/` — which it does only after an explicit Yes, and does name in a follow-up dialog. The app behaved correctly; the sheet did not. |

## External reference material

Third-party references distilled for context — *not* our own investigations, so
they carry no "graduated conclusions" row. Treat them as parity targets/principles
to mine, not as authority over the living docs.

| Archived file | What it is |
|---|---|
| [`archival-extraction-guide-2026-06.md`](archival-extraction-guide-2026-06.md) — **our own cited summary** of a user-supplied EAC 1.8 / FLAC 1.5 / WavPack / LAME master guide | Our paraphrased summary of the guide's actionable EAC/Windows-centric archival targets (FLAC `-V` verify + compression level, the LAME `-q 4` `noise_shaping_amp` gotcha for MP3 — shipped 2026-06-26, KDD-22 — and WAV metadata limits), with links to the primary tool sites. The **verbatim third-party text was removed 2026-07-07** (provenance/permission hygiene for a public repo); the summary feeds the **2026-06-23 gap analysis** in `docs/session-log.md`; several source claims are flagged *verify before relying*. |

---

*Last updated for Platterpus v0.6.4b11.*
