# Round 27 — the quick run, 2026-09-26, `221a1df` (`+platterpus.16`) on Platterpus 0.6.60

**Read the build, not the date.** The one rip log here opens
`cyanrip 0.9.4-rc2+platterpus.16 (platterpus-fork-g221a1df)`: the build round 27
reviews, installed through our 0.6.60 (`88c09dd`). This is the run that stands in for
round 27 lap 1 §0.1's Full acceptance, **by the operator's override of R1** (the fork's
round 27 lap 4 records it as `HANDSHAKE-OVERRIDE`). It is a **quick** run and says so
itself: its script report carries `counts_as_evidence: false`, and it is not evidence
for a version (KDD-35).

**The bundle:** `platterpusbundle20260926t000413z.tar.gz`, sha256
`827d43da95f4dfe150e70900b56d5e96163cff41f7a6e117819760970e9cc4e0`, 1,656,589 bytes,
handed over by the operator. The tarball itself is not committed. Its text members
are, **byte for byte**, and the table below names the member behind every file,
so each one can be checked with `sha256sum`.

**The fork filed the same set** at `cyanrip@29cae9e:docs/rig-2026-09-26-221a1df-quick/`.
Its 15 files have the **same git blob ids** as our copies, 15 of 15, so the two trees
hold identical bytes under different names. Ours use this directory's naming convention
(`docs/handshake/README.md` → *Artifacts*). Unlike round 26, the fork filed our rip
report too, so nothing here is ours alone.

**Not filed:** the 13 screenshots, pictures of our own windows that neither side's
reading rests on, and `session/transcript.txt`, which is byte-identical to
`session/run/transcript.txt` (filed as `round27transcript.txt`). **No EAC-compatible log
exists for this rip:** the script turns that export off for section K1 (step L223).
**No audio can be here**: the bundle's own allowlist refused every audio file, and
`MANIFEST` lists each refusal.

**What happened on this run** is in our round 27 lap 5 and `docs/session-log.md`
(2026-09-26). In short: 206 passed, 0 failed, 114 declined by the run size, one `info`.
The only rip, section K1, took tracks 1–2 and both are exact AccurateRip v1 and v2
matches. The run found three defects, all ours, all fixed before `main` saw them.
One of them is the run's own manifest line calling this complete run incomplete,
which the fork found independently in their lap 4 §E.

| our file | tarball member | fork's file (`cyanrip@29cae9e`) | sha256/16 |
|---|---|---|---|
| `round27derivedmp3.cue` | `album/derived mp3 20260926t000413 platterpus-fork-g221a1df.cue` | `rips/derived-mp3.cue` | `424befb1cd88a2eb` |
| `round27derivedmp3.log` | `album/derived mp3 20260926t000413 platterpus-fork-g221a1df.log` | `rips/derived-mp3.log` | `49f4b6ef41b1e1df` |
| `round27derivedmp3report.json` | `album/derived mp3 20260926t000413 platterpus-fork-g221a1df.platterpus.json` | `rips/derived-mp3.platterpus.json` | `be2cfa5db0bef61e` |
| `round27components.json` | `COMPONENTS.json` | `session/COMPONENTS.json` | `6d4c4dd66afa50fc` |
| `round27diagnostics.txt` | `DIAGNOSTICS.txt` | `session/DIAGNOSTICS.txt` | `66781958ada452cd` |
| `round27manifest.txt` | `MANIFEST.txt` | `session/MANIFEST.txt` | `82fdd94760d25c77` |
| `round27settings.json` | `SETTINGS.json` | `session/SETTINGS.json` | `c370dd3f5555dcb8` |
| `round27sources.txt` | `SOURCES.txt` | `session/SOURCES.txt` | `4dd4b28124a6981c` |
| `round27config.toml` | `session/artifacts/03platterpus/config.toml` | `session/config.toml` | `8d816eea558fa8c8` |
| `round27scriptreport.json` | `session/run/report.json` | `session/report.json` | `354ca837d0e6a1d7` |
| `round27rigcheckmanifest.txt` | `session/run/rig-check/MANIFEST.txt` | `session/rig-check-MANIFEST.txt` | `283f43dba4e69989` |
| `round27rigcheckargvprobeoutput.txt` | `session/run/rig-check/argv-probe-output.txt` | `session/rig-check-argv-probe-output.txt` | `dae8e715b1a6664c` |
| `round27rigcheckargvprobe.json` | `session/run/rig-check/argv-probe.json` | `session/rig-check-argv-probe.json` | `e7dc0ffbdb5cd222` |
| `round27rigcheckripperversion.txt` | `session/run/rig-check/ripper-version.txt` | `session/rig-check-ripper-version.txt` | `5f3153bbf48a5103` |
| `round27transcript.txt` | `session/run/transcript.txt` | `session/transcript.txt` | `c2525b537e13e0a7` |
