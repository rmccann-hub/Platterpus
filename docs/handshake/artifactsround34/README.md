# Round 34 — the Full run, 2026-10-16 00:20 UTC, `891c79e` (`+platterpus.23`) on Platterpus 0.7.106

**The pair.** Round 34's subject: `.23` at `891c79e` (upstream cyanrip 0.9.4-rc3) with our
0.7.106, the release that made `.23` our build under review. Every rip log here opens
`cyanrip 0.9.4-rc3+platterpus.23 (platterpus-fork-g891c79e)` (11 of 11 logs). The app is
0.7.106 at `dd200af` (`round34fullcomponents.json`), which pins `200530e` and accepts
`891c79e` as the build under review (`round34fulltranscript.txt`, the `ripper/pin` lines).

**Where it lives.** Filed straight to our `evidence` branch under HR-2 point 10 (protocol
v9 §17), as round 33's run was. The whole folder, this README included, is on `evidence`;
the default branch keeps only this README, as the folder's index (point 1), and
`docs/evidence-manifest.tsv` gives every file's size and SHA-256 with an empty
`last_default_commit`.

**The bundle.** `platterpusbundle20261016t002045z.tar.gz`: sha256
`cfb2fab2eb68ef12aeee90dcfdbeb28c837b09ce0bcba11e677565fb1f815016`, 6,720,084 bytes, 108
members. 79 of its text members are filed here byte for byte, each with a `round34full`
prefix and the same names as round 33's run (`../artifactsround33/`), plus one new kind:
`round34fullwholediscaddendum.txt`, the whole-disc rip's `.platterpus-addendum.txt`. 78
of them hash as the bundle's own MANIFEST lists them; the 79th is that MANIFEST
(`round34fullmanifest.txt`). The tarball is not committed.

Not filed:
- the 26 screenshots;
- `session/transcript.txt`, which is byte-identical to `round34fulltranscript.txt`;
- the app-log rotations `.3` and `.4`, which end before the run (`.3` ends at 11:05 local
  on 2026-10-14; the run began at 20:20 local on 2026-10-15).

There is no audio. The app log's times are local, UTC−4 on this rig.

## Point 9: what was replaced before filing

- **Home folders**, replaced with `~` by the app's own export as it wrote the bundle
  (`src/platterpus/export_redaction.py`): 2,218 replacements in 25 members and 12 in the
  MANIFEST's own text, each member's count and its SHA-256 before replacement listed in
  `round34fullmanifest.txt` under *HOME FOLDERS REPLACED WITH ~*. No signed log needed a
  replacement (*kept as written: 0 member(s), 0 home path(s) left in them*).
- **The hostname**: 0 replacements. The export does not replace hostnames (its MANIFEST
  says so), so all 79 files were searched for one before filing: no hostname, no
  `user@host` prompt, no `HOSTNAME=`/`USER=`/`LOGNAME=` and no `.local`/`.lan`/`.home`
  name appears.
- **The owner's real name**: 0 replacements; it does not appear. The project's public
  repository address (`github.com/rmccann-hub/...`) and the app's desktop ID are the
  project's published names, not personal details, and are left as written.
- No other byte was changed: every filed file is the bundle's member, byte for byte.

## Point 9: the self-verifying logs, verified before filing

All 20 signed logs verify, so each hash below is both the hash before and the hash after
filing. The 11 cyanrip logs were checked against their `Log FUN512:` line with a port of
cyanrip's own `-Y` check (`cyanrip@5c564042:src/fun512.c`, `crip_log_fun512` and
`cyanrip_verify_log`); the 9 EAC-compatible logs against our SHA-256 footer
(`platterpus.eac_log_export.verify_eac_style_log_checksum`). Changing one byte in the
middle of a copy of each kind made it report a mismatch, so the check can fail.

| File | Check | SHA-256 (before = after) |
|---|---|---|
| `round34fullaftercancel.log` | cyanrip FUN512 (`-Y`): valid | `41ac7f851d5b1676b296e7e6eb80263b411fd8eb2b304477dd45148670991de4` |
| `round34fullaftercanceleac.log` | our SHA-256 footer: valid | `57058836421042ddc2ed140e1c5fb0f5dcf4954760c3b51f33ea669d8fe32a33` |
| `round34fullcancelme.log` | cyanrip FUN512 (`-Y`): valid | `c9e32692725d47a07cab62d6c23f07c5a1d456476cab851fd32875ca419c055a` |
| `round34fullcancelmeeac.log` | our SHA-256 footer: valid | `4cd1e8a6e3fc5db8d0013fa3e636bc8d634b8409b26423120f724361436c8ff4` |
| `round34fulldeemphoff.log` | cyanrip FUN512 (`-Y`): valid | `4ec02450c3c39868d1b6636c6b49152b490094840b87bf9a7792a8f329986d06` |
| `round34fulldeemphon.log` | cyanrip FUN512 (`-Y`): valid | `c6ae0bda9dce4a1581c629a69677919fc81d0f47d18dbb781a8a281b8a2f7e13` |
| `round34fullderivedmp3.log` | cyanrip FUN512 (`-Y`): valid | `5513dd82fe148f1bdf546ba74b27c4a88f9720c917c128e97f26b8cadd13c33e` |
| `round34fullderivedmp3eac.log` | our SHA-256 footer: valid | `87cf8512eed87c4d703deaedb532488cbbd5d68c9425b98b538e4d1acb170649` |
| `round34fullderivedwav.log` | cyanrip FUN512 (`-Y`): valid | `097d274fca3f1551779c64539a4f16a17e55763bef9d74e36d8a6eabd6f03387` |
| `round34fullderivedwaveac.log` | our SHA-256 footer: valid | `fde11c5d77b685070589af60f7d45fa15df6ebb27615a325eaf225cf0aa65532` |
| `round34fullderivedwavpack.log` | cyanrip FUN512 (`-Y`): valid | `a44471d5b94cb129d15cc948fdff5de773880dfc93b5b7a7754d7f0339df6f3d` |
| `round34fullderivedwavpackeac.log` | our SHA-256 footer: valid | `1799617c0aaf251a191cb26be3e3741524d132d63a07c51a8fae7d6a97614edb` |
| `round34fulloverwrite.log` | cyanrip FUN512 (`-Y`): valid | `b09eee63a8ebcdb9958b527ad1ea08bac9442355d62305b50e9cc2f5b96262a1` |
| `round34fulloverwriteeac.log` | our SHA-256 footer: valid | `96e9d2737521df2db5c5fad6ce767c345246f51dc28594c30e88220ef31e6905` |
| `round34fullpermutations.log` | cyanrip FUN512 (`-Y`): valid | `1dcd62d407064abb2cf308bc80d2f72172a58520a0141d3fcb5fbd03883d2d64` |
| `round34fullpermutationseac.log` | our SHA-256 footer: valid | `a7f5ca27f8165d8210c05f4f9dfd3166b314aefa033e87d89757df3a45819cf4` |
| `round34fullsecurereread.log` | cyanrip FUN512 (`-Y`): valid | `84401e072faf2398a9d284d6fae0946b569565eebd0deda6c80efd352604e0cf` |
| `round34fullsecurerereadeac.log` | our SHA-256 footer: valid | `b033e17180af59911052080337b8eb0ee5e47ee1ce8ad453b02a3f92af20d376` |
| `round34fullwholedisc.log` | cyanrip FUN512 (`-Y`): valid | `4387ba88e0073dfa3dfc953b184ab83661b3c0bc96bfaeca83aa525a623fe2fe` |
| `round34fullwholedisceac.log` | our SHA-256 footer: valid | `cc36c57c32e3e0ad6f943047ab98324c3fb0ae4701858e96fb019d65c1afd35c` |

## What it shows

- **426 pass, 0 fail, 0 error, 0 skipped, 0 blocked, 1 unreachable, 6 info**, 433 step
  results (`round34fullscriptreport.json` `counts`; the transcript's last lines). The
  report says `run_size: full` and `counts_as_evidence: true`.
- **The unreachable step is E2** (line 566, `expect-offset-refusal`): the BDR-209D is on
  the AccurateRip drive list, so the refusal it checks cannot be reached, as on every Full
  run since 2026-10-07.
- **The run** began 00:20:45 UTC (the transcript's header) and ended when the app
  restored the operator's settings at 01:31:18 local, 05:31:18 UTC
  (`round34fullplatterpusapplog.txt:53908`).
- **The whole-disc rip**: 12 of 14 tracks accurately ripped, `Ripping errors: 0`, as on
  the 2026-10-14 run on `.22`. Tracks 3 and 5 match AccurateRip on one frame only
  (`Accurip 450`), track 3 on `BF62B1DA`, the same frame as on `.22`.
- **The secure re-read**: track 3 did not converge in 5 reads, as on `.22`; track 5
  agreed on the first two reads (`E0036697`), where on `.22` at most 2 of 5 agreed.
- **`.23`'s own lines**: `AcoustID:       unsupported (built without libchromaprint)` in
  every log, so no fingerprint tag was written; track 1's pregap reads `150 frames` from
  the lead-in; the `-j` records carry `cdtext` and `offset_search`.
- **13 `-j` records**, the two securing passes' included.
- **Pregaps** differ between rips at tracks 4 and 9 (section P4, gathered, not graded):
  the fork's known `subchannel-pregap-varies`.
- **Not graded here.** Its row in the evidence ledger (`docs/testing.md` §5B) is a
  separate step.
