# Round 33 — the Full run, 2026-10-14 11:07 UTC, `200530e` (`+platterpus.22`) on Platterpus 0.7.105

**The pair.** The Full run our round 33 lap 2 S11 names: `.22` at `200530e` with our
0.7.105. Every rip log here opens `cyanrip 0.9.4-rc2+platterpus.22 (platterpus-fork-g200530e)`
(11 of 11 logs). The app is 0.7.105 at `b33b90d`, which pins `200530e`
(`round33fullrigcheckmanifest.txt:5`). The operator held the run until HR-2's move was
done and handed it over on 2026-10-15.

**Where it lives.** This is the first run filed straight to our `evidence` branch under
HR-2 point 10 (protocol v9 §17). The whole folder, this README included, is on
`evidence`; the default branch keeps only this README, as the folder's index (point 1),
and `docs/evidence-manifest.tsv` gives every file's size and SHA-256 with an empty
`last_default_commit`, because none of them was ever on the default branch.

**The bundle.** `platterpusbundle20261014t110756z.tar.gz`: sha256
`a99addc6d99e8f45bf58057082c492831b869d8158a278de120924503cad8c73`, 7,529,505 bytes, 108
members. 78 of its 82 text members are filed here byte for byte, each with a `round33full`
prefix and the same names as round 32's run (`../artifactsround32/`). 77 of them hash as
the bundle's own MANIFEST lists them; the 78th is that MANIFEST
(`round33fullmanifest.txt`). The tarball is not committed.

Not filed:
- the 26 screenshots;
- `session/transcript.txt`, which is byte-identical to `round33fulltranscript.txt`;
- the app-log rotations `.3` to `.5`, which end before the run (`.3` ends at 11:46 local
  on 2026-10-13).

There is no audio. The app log's times are local, UTC−4 on this rig.

## Point 9: what was replaced before filing

- **Home folders**, replaced with `~` by the app's own export as it wrote the bundle
  (`src/platterpus/export_redaction.py`): 2,267 replacements in 26 members and 12 in the
  MANIFEST's own text, each member's count and its SHA-256 before replacement listed in
  `round33fullmanifest.txt` under *HOME FOLDERS REPLACED WITH ~*. No signed log needed a
  replacement (*kept as written: 0 member(s), 0 home path(s) left in them*).
- **The hostname**: 0 replacements. The export does not replace hostnames (its MANIFEST
  says so), so all 78 files were searched for one before filing: no hostname, no
  `user@host` prompt, no `HOSTNAME=`/`USER=`/`LOGNAME=` and no `.local`/`.localdomain`
  name appears.
- **The owner's real name**: 0 replacements; it does not appear. The project's public
  repository address (`github.com/rmccann-hub/...`, in `round33fullplatterpusapplog2.txt` and the nine album reports)
  is the project's published URL, not a personal detail, and is left as written.
- No other byte was changed: every filed file is the bundle's member, byte for byte.

## Point 9: the self-verifying logs, verified before filing

All 20 signed logs verify, so each hash below is both the hash before and the hash after
filing: nothing in them was replaced. The 11 cyanrip logs were checked against their
`Log FUN512:` line with a port of cyanrip's own `-Y` check (`cyanrip@5c564042:src/fun512.c`,
`crip_log_fun512` and `cyanrip_verify_log`); the 9 EAC-compatible logs against our SHA-256
footer (`platterpus.eac_log_export.verify_eac_style_log_checksum`). Changing one byte of a
copy of each kind made it report a mismatch, so the check can fail.

| File | Check | SHA-256 (before = after) |
|---|---|---|
| `round33fullaftercancel.log` | cyanrip FUN512 (`-Y`): valid | `a8629735055d8479ae66c4061eb4b860d1935b1cc8179ef7ae47188215c8f81e` |
| `round33fullaftercanceleac.log` | our SHA-256 footer: valid | `c5349af61f5a029d42b81bb179a73ccd2c4c0d8bbad071d446cceb3a6531034c` |
| `round33fullcancelme.log` | cyanrip FUN512 (`-Y`): valid | `af31e4befe5e036dbfda1889e8b57699ea8a4211d23d3e3060b1c5c5f95a1188` |
| `round33fullcancelmeeac.log` | our SHA-256 footer: valid | `345643eb492da4d5ae2bc5774ce08c0c2735bf2b40c16af052a6c6f6f50157df` |
| `round33fulldeemphoff.log` | cyanrip FUN512 (`-Y`): valid | `407a346cea4a35367b081aa5b266e12e29c812e398453eec86876a69a48d85b3` |
| `round33fulldeemphon.log` | cyanrip FUN512 (`-Y`): valid | `b2f85e8e0286dedc59885b4cf6156149a8417326e7db37d63833e1ddfa0ba65f` |
| `round33fullderivedmp3.log` | cyanrip FUN512 (`-Y`): valid | `fa72b84d69a194cd26318de133199edfa949b116455787183700cd028384b823` |
| `round33fullderivedmp3eac.log` | our SHA-256 footer: valid | `df6cd8ef860d91bbc7d118ed0134f18de15071bff14cb80c6368fb279b91e405` |
| `round33fullderivedwav.log` | cyanrip FUN512 (`-Y`): valid | `90c280d57d0d60db4c49e104b28921473436d7ce2f024e23bff75eefc8111a48` |
| `round33fullderivedwaveac.log` | our SHA-256 footer: valid | `9b7e1b32c943a31e17918fbb91858d98420a83004546e2bd48a1cfb9cec4dbb1` |
| `round33fullderivedwavpack.log` | cyanrip FUN512 (`-Y`): valid | `47b435d70b5b91ae38446e1a5fa0af2b3f38c2688ce886d1dd63bf8adfa9a261` |
| `round33fullderivedwavpackeac.log` | our SHA-256 footer: valid | `2ca69e54a1b2a1acb0f81eee4b083617af7744247b653e8c66c0db6aae9ac33e` |
| `round33fulloverwrite.log` | cyanrip FUN512 (`-Y`): valid | `245226340d40bd09c5a7db269e47473d21f65f75edf88739049d969bf41764f9` |
| `round33fulloverwriteeac.log` | our SHA-256 footer: valid | `376c98aa834e49ae706bbbddfece3c7f2352c498bbd5236470d3603272d30fe2` |
| `round33fullpermutations.log` | cyanrip FUN512 (`-Y`): valid | `82c8353fdc08f69523b9fb21ed11a1cb7eaebeafb377a7317587b89b2d3b687b` |
| `round33fullpermutationseac.log` | our SHA-256 footer: valid | `67f2709a25e55a2637713932ea003e00d4453d45395f91c78460c0c36e725944` |
| `round33fullsecurereread.log` | cyanrip FUN512 (`-Y`): valid | `bdc8b91c8bc803654a7879365f62bdbef9d18c7d7b80648ed3ccd95d236aff0f` |
| `round33fullsecurerereadeac.log` | our SHA-256 footer: valid | `dae28fd4b1846dd82ce835b9866e530bc74a9c6ebb9a02aec1282bae02952a4c` |
| `round33fullwholedisc.log` | cyanrip FUN512 (`-Y`): valid | `e47acb1dd45178305cf8d57409e34d5dafcf3b442cbfe163f47aaea521edf3e8` |
| `round33fullwholedisceac.log` | our SHA-256 footer: valid | `b93cff8c4bb94d06a7d1d0b3bcf6b17bc33b43e16f5f2ee837780c5f74594469` |

## What it shows

- **425 pass, 0 fail, 0 error, 1 blocked, 1 unreachable, 6 info**, 433 step results
  (`round33fullscriptreport.json` `counts`; the transcript's last lines). The report
  says `run_size: full` and `counts_as_evidence: true`.
- **The unreachable step is E2** (line 566, `expect-offset-refusal`): the BDR-209D is
  on the AccurateRip drive list, so the refusal it checks cannot be reached, as on every
  Full run since 2026-10-07.
- **The blocked step is line 1071, `expect-cover-art`**: cover art was asked for and
  none was fetched, `network HTTP 500` from the Cover Art Archive
  (`round33fulldiagnostics.txt`, `coverart.fetch_failed` at 13:07:15 UTC;
  `round33fullplatterpusapplog1.txt:14925`, 09:07:15 local). An HTTP 500 is the
  server's own error; the rip is unaffected.
- **The run** began 11:07:56 UTC (the transcript's header) and ended when the app
  restored the operator's settings at 12:45:19 local, 16:45:19 UTC
  (`round33fullplatterpusapplog.txt:47832`).
- **13 `-j` records**, the two securing passes' included
  (`round33fulljrecord20261014t115837zsecuringpass.json`,
  `round33fulljrecord20261014t155837zsecuringpass.json`), where round 32 had 9 and named
  neither absence.
- **Not graded here.** Its row in the evidence ledger (`docs/testing.md` §5B) is a
  separate step.
