# Platterpus full acceptance run: coverage audit

- Repository: `rmccann-hub/platterpus` at `origin/main`, `75915aa9` (merge of PR #433). Read only; nothing changed.
- Subject: `src/platterpus/rig_scripts/fullacceptance.txt` (1,911 lines). Every line number below is from that file at that commit.
- Method: both inventories come from the source, not the docs. Inventory A is built from `ui/main_window.py::_build_menus`, `ui/dialogs/setup_center.py`, every `QPushButton`/`addAction` label under `ui/`, `config.Config`, `settings_validation.py` (ranges and `_ALLOWED_*` sets), `goal_presets.PRESETS`, `app.py`'s argparse, every `message_boxes.*` call under `ui/`, and the outcome vocabularies in `verdict.py`, `ripper_exit_class.py`, `cancel_cause.py`, `verification_gates.py`, `read_offset_check.py` and `accuraterip_standing.py`. Inventory B is built from the script, the verb table (`uiscript/verbs.py`, 70 verbs) and the handlers that grade (`uiscript/runner.py`, `artifact_grading.py`, `tag_grading.py`, `permutation_grading.py`, `unknown_disc_verbs.py`).
- Legend: **C** = covered and asserted (a step can go red over it). **E** = exercised but not asserted (it runs, or is set, and nothing grades the result). **N** = not exercised. **N/A-rig** = the verb records `unreachable` on the reference rig.

---

## 0. Headline findings

1. **A failed verification passes the run.** `expect-verification` (runner.py:2851) passes when every gate "left a result". Per its own docstring, a gate reading `"ran — failed"` counts as having run. `expect-derived-output` (runner.py:2706) rejects only `not run — …` and `cut short`, through `artifact_grading.derived_verification_refusal`. None of the 13 `rip_audit.CHECKS` reads `flac_integrity` or the derived block. So a FLAC that fails `flac --test`, or a WavPack or WAV whose decoded PCM differs from its master (`verification_gates._from_pass_fail_block` gives `"ran — failed"`), passes F, H, J, K2, K3 and N. Neither failure depends on the disc; both are always our defect. This is the §5.bi shape again: the step cannot fail over the thing it is named for. No unit test in `tests/test_uiscript_rip_verbs.py` covers a `"ran — failed"` gate; the existing tests cover only "did not run".
2. **Nothing grades the read offset a rip actually applied.** The report computes `rip.read_offset_check` (`matches` / `differs` / …) and files `read_offset_differs_from_accuraterip`, but no verb reads it. `expect-drive-offset` and `expect override_read_offset on` read the config, not the rip. Because `expect-accuraterip` and `expect-ctdb` pass on a mismatch by design, a wrong offset in the argv builder (a sign flip, say) would produce a run that stays green.
3. **The derived files themselves are never opened for metadata.** `expect-tags` and `expect-cover-art` read the FLAC masters only (`tag_grading.py`). The severity table's reason for K1 is that the MP3 "*is* their library entry … with its tags and art", and the script's K header (line 1017) claims "WavPack — Tags and art survive". Neither claim is checked. `mp3_vbr_quality 2` (lines 1058–1059) is round-tripped as a setting. The report records the config value (`rip_report.py:1345`), not the ffmpeg argv, so nothing shows that `-q:a 2` reached the encoder.
4. **The Settings dialog's save path never runs on the rig.** `set` writes `window._config` directly (runner.py:3763–3842, "the same push the Settings dialog does on Accept"), which is a parallel path. Section D only opens Settings and presses Cancel (lines 489–491). The WAV warning K3's title promises ("the UI must say so", line 1106) is `settings_dialog._wav_warning_label`, which is visible only while that dialog's combo box shows WAV. It is never shown and never asserted.
5. **The direct `cyanrip` steps pass no `-d`.** O (1318), P (1376), P2 (1431) and P3 (1562, 1568) carry no device. The verb has `(offset)`, `(lasttrack)`, `(consumer)` and `(diagnostics)` placeholders but no `(device)` one (`uiscript/script.py:235–260`). `docs/dependency-contracts.md:51` says `-d` is passed "always, when a device is known". On a two-drive machine each step reads whatever cyanrip opens by default. P's `cache-probe` beside it uses the *selected* drive (`probe_verbs.py:195`), so P can compare two different drives.
6. **No inventory guard exists.** `test_rig_scripts.py` holds the settings baseline (`test_the_baseline_sets_or_keeps_every_user_setting`) and checks that every *named* verb exists, but nothing checks that every verb, every `OPENABLE` dialog or every menu action is *used*. Full acceptance leaves 8 of 70 verbs unused and 1 of 8 openable dialogs (`getting-started`) unopened. `open setup` maps to the host-setup wizard (`OPENABLE["setup"] = "open_host_setup_dialog"`), not to Tools → Setup & Updates… (`open_setup_center`), which is the user's real path and is unreachable by `open`.
7. **P4's order is no longer a gap.** At this commit P4 runs after P6 (line 1822), and `tests/test_uiscript_pregap_verbs.py::test_the_pregap_comparison_comes_after_every_rip_the_script_makes` pins it by asserting no `rip` or `cyanrip` step follows `expect-pregaps-agree`. Residual: P4 is `run-size standard` while P5 and P6 are `full` and are N/A whenever the build under review is the approved pin, so most runs compare only the F/H/I/J/J2/K/N/P3 logs. That is correct, but it means the cross-build pregap comparison happens only during an open round.

---

## A. Inventory of what a user can reach (from source)

### A1. Menu actions (`ui/main_window.py::_build_menus`, lines 1086–1243)

| # | Path | Slot |
|---|---|---|
| M1 | File → Rip as Unknown Album… | `_on_rip_as_unknown` |
| M2 | File → Quit (Ctrl+Q) | `_on_quit_requested`, which asks "Quit Platterpus?" mid-rip |
| M3 | Tools → Settings… (Ctrl+,) | `_on_open_settings` |
| M4 | Tools → Setup & Updates… | `open_setup_center` |
| M5 | Tools → Advanced → Run test script… | `open_script_console` |
| M6 | Tools → Advanced → Run acceptance test… | `_on_run_acceptance_action` |
| M7 | Tools → Advanced → Run acceptance test with an unknown disc… | `_on_run_unknown_disc_acceptance_action` |
| M8 | Tools → Uninstall Platterpus… | `open_uninstall_dialog` |
| M9 | Help → Getting started… | `_on_show_getting_started` |
| M10 | Help → User Guide… (F1) | `_on_show_help` |
| M11 | Help → Open logs folder… | `_on_open_logs_folder` |
| M12 | Help → Copy diagnostics… | `_on_show_diagnostics` |
| M13 | Help → About Platterpus… | `_on_show_about` |
| M14 | Album right-click → Copy / Select All / Set cover art from file… | `album_menu.py`, `_on_set_cover_art_from_file` |
| M15 | Track table right-click → Rip only these / Include / Exclude / Select all / Select none | `track_table.py:835–844` |

### A2. Setup & Updates sections (`setup_center.py`, actions wired at `main_window_provision.py:541–551`)

| # | Button / control | Action key |
|---|---|---|
| S1 | Check for updates | `app_update` → `_on_check_updates` (download, verify, install and restart path in `main_window_update.py`) |
| S2 | Check for cyanrip updates | `ripper_update` (offers "Install it now" or "Install it anyway") |
| S3 | Choose a build… | `ripper_pick` → `_on_pick_ripper_build` (`ripper_picker.py`) |
| S4 | Check dependencies | `dep_check` |
| S5 | Set up drive… | `drive_setup` (`drive_setup_dialog.py`: Detect / Analyze cache, Save offset) |
| S6 | Diagnose drive access… | `drive_diagnose` |
| S7 | Run setup… | `host_setup` (`host_setup_dialog.py`) |
| S8 | Add app shortcut | `shortcut` |
| S9 | Tick-boxes: beta app updates, beta cyanrip builds | save `update_channel` and `ripper_channel` at once |

### A3. Main-window buttons with an effect

| # | Button | Where |
|---|---|---|
| B1 | Start rip / Cancel / Force stop | `rip_controls.py:55–62` |
| B2 | Refresh (drive list) / Rescan disc / Eject | `drive_picker.py:85–105` |
| B3 | View log / View report / View cue / Open rip folder / Report bundle | `rip_progress.py:610–639`. Each handler returns silently when its path is `None` |
| B4 | Tracks / Details / Live log tabs | `rip_progress.py:178–180` |
| B5 | Overwrite prompt: Replace / Rip to a new numbered folder / Cancel, plus the variant that does not offer Replace | `main_window_rip.py:871–917` |
| B6 | Release picker (row or MBID) | `release_picker.py` |
| B7 | Unknown-album dialog, and Picard launch | `unknown_album.py` |
| B8 | File viewer: Open externally… | `file_viewer.py:101` |
| B9 | Diagnostics: Copy to clipboard | `diagnostics_dialog.py:264` |
| B10 | Script console: Run / Stop / Load… / Save transcript… / Commands / Close | `script_console.py:217–240` |
| B11 | Uninstall… | `uninstall_dialog.py:121` |

### A4. Settings (`config.Config` and `settings_validation.py`)

| Setting | Allowed values | Shipped default |
|---|---|---|
| rip_goal | fast_verified, archival, portable, custom | fast_verified |
| output_format | flac, wavpack, mp3, wav | flac |
| mp3_vbr_quality | 0–9 | 0 |
| cover_art | "" (off), embed, file, complete | embed |
| save_additional_art | bool | on |
| max_retries | 0–100, refused as a pair with matches (validator line 1065) | 5 |
| secure_rerip_matches | 0–10 | 2 |
| secure_rerip_dynamic | bool | on |
| rerip_offset_variant | bool | on |
| second_read_without_accuraterip | bool | on |
| read_speed_mode | auto_ladder, fixed | auto_ladder |
| read_speed | 0–72 | 0 |
| read_offset | −5000…5000 | 0 |
| override_read_offset | bool | off |
| force_overread | bool | off |
| prefer_disc_isrc | bool | on |
| ctdb_verify_after_rip / verify_flac_after_rip | bool | on / on |
| write_eac_log_after_rip | bool | off |
| track_template / disc_template | tokens `AadntyYNM`; no absolute paths; no `..`; Windows-reserved characters warn | `%A/%d/%t - %n`, `%A/%d/%d` |
| track_template_unknown / disc_template_unknown | same rules | Unknown Artist/… |
| output_dir / library_dir / metaflac_path | path | — |
| auto_launch_picard / auto_eject_after_rip / notify_on_completion | bool | off / off / on |
| update_channel / ripper_channel | stable, beta | stable |
| debug_logging | bool | off |
| test_script_path / test_script_autorun | — | — |
| internal flags (`*_prompted`, `integration_declined_*`, `schema_version`) | not user-set | — |

### A5. Command-line flags (`app.py:829–960`, 13 flags)

`--version`, `--uninstall`, `--doctor`, `--install-ripper [list|<commit>]`, `--run-script FILE`, `--rig-session [DIR]`, `--rig-check DIR`, `--rig-check-album`, `--rig-check-device`, `--ctdb-calibrate`, `--audit-rips FOLDER`, `--compare A B`, `--assemble-best-of A B DEST`.

### A6. Rip outcomes the UI can show

- **Status line** (`main_window_rip.py:2053–2085`, `main_window_helpers.py:500–514`): "Done — …" (clean, or with the read-stability warning); "Done." with no audio track logged (data only); "Rip cancelled by user. Partial files may remain."; "Rip cancelled after the read finished; …" (cancel during the securing pass); the failure hint or "Rip failed — no diagnosis was captured"; a pass-exit phrase when a securing pass followed a failed album pass.
- **Per-track AccurateRip state** (`verdict.py:237–247`): verified, offset-variant (a one-frame match), no-match, absent (not in the database), no-data, not-checked. AccurateRip standing: in_database, not_in_database, lookup_failed, not_determined.
- **CTDB verdict**: match, no_match, not_in_db, declined for a partial rip, or a lookup error. Verification gates: `ran — passed`, `ran — failed`, `not run — <reason>`, `cut short`, `superseded`.
- **Derived-format verify**: bit-identical (WavPack, WAV), decode-clean plus complete (MP3), mismatch, or failures ("⚠ {fmt} verify FAILED", `main_window_rip.py:5226`).
- **Ripper exit class** (`ripper_exit_class.py`): ok, refused, disc_or_drive (74), signal, container_tool, failure, unclassified, not_determined.
- **Cancel cause** (`cancel_cause.py`): user, time_limit, run_ended, script_step, not_recorded.
- **Read offset check**: matches, differs, drive_not_listed, not_determined.
- **Desktop notification**: success, or "rip didn't finish" (`notify.py`).

### A7. Error paths and prompts a user can hit

From the `message_boxes` titles and the handlers:

- **Drive and offset**: "Set up your drive first" (no offset and the drive is not listed); "Read offset disagreement"; "Read offset out of range"; "Read offset set automatically"; "Set up drive: Select a drive first"; "Cannot rip: Select a drive first".
- **Start refusals**: "Cannot start rip" (track-table validation, including names over 255 bytes, `..` segments and control characters); the overwrite prompt.
- **Disc**: disc-probe failure with bounded retry (`_handle_disc_probe_failure`, `_on_disc_retry_due`); scan force-stopped; probe timed out, which frees the drive; drives unavailable; drive-list failed; no disc (`set_no_disc`); disc removed and returned (`main_window_disc_return`); disc swapped under the tags (`disc_identity`); data-only disc; Enhanced CD (`data_tracks.is_data_track`); CD-R (not in AccurateRip).
- **MusicBrainz**: lookup error, which falls back to placeholder rows; release fetch failed; no match, which offers the unknown-album rip; several candidates, which opens the picker; a stale or duplicate answer.
- **Lookups after the rip**: AccurateRip lookup failed; CTDB error; cover art not found or not readable ("Cover art" dialogs at `main_window_rip.py:1646–1649`).
- **Output**: preflight "Output location not writable" (`preflight.py:191–221`). Disk full has no check of its own: no `statvfs` or `disk_usage` anywhere in `src/`, only a pass-through of cyanrip's and metaflac's "No space left on device".
- **Settings**: "Couldn't save settings"; "Some settings were reset" (a bad config on load).
- **Dependencies and container**: "Couldn't check dependencies"; "Dependency check incomplete"; ripper missing or wrong build (`ripper_standing`); container not running or cold start (`container_gate`).
- **Updates**: "Check for updates: couldn't check (no connection…)"; Update available / failed / installed.
- **Other**: shortcut and menu-integration prompts; uninstall prompts; script console "no script was run" and "Could not save".

---

## B. What the script exercises, per section

| § | Lines | Size | Exercises | Asserts |
|---|---|---|---|---|
| baseline | 227–272 | all | sets 26 settings to their defaults, keeps 7, turns debug on | `expect debug_logging on` |
| A | 306–348 | quick | `cyanrip --version`, `app-log`, `probe-ripper-wrapper` | exit 0, banner, build under review, newest pair (needs network), abort |
| B | 398–443 | quick | `set-drive-offset`; round-trips max_retries, output_format, force_overread, prefer_disc_isrc, auto_eject, picard, update_channel, ripper_channel | each `expect`; abort on an unknown offset. **`ripper_channel` is left on beta until Q** |
| C | 459–472 | quick | validator refusals: read_offset ±99999, max_retries 101, matches 11, mp3 10, retries 2 as a pair | `expect-refused` (refused and value unchanged); floor checks |
| D | 486–503 | quick | opens and cancels drive, settings, dependencies, about, diagnostics, guide, setup (the wizard) | nothing beyond the dialog closing; screenshots are for a person |
| E | 526–564 | quick | `rescan`, `pick-release 1` | picker gone, at least 2 tracks, `expect-identified` (MBID held), abort; `run-estimate` is info |
| E2 | 588–590 | quick | `expect-offset-refusal` | N/A-rig on a listed drive (the BDR-209D is listed) |
| F | 662–747 | standard | whole disc, fast_verified, every post-rip check, the `:` and `<` title | rip complete, verification left a result, `--prefer-disc-isrc` in argv, audit, AccurateRip answered, CTDB whole, FLAC tags, cover embedded |
| G | 767 | standard | `rig-check` | SKIP/PASS/FAIL rows (its INFO rows are not graded) |
| H | 799–822 | standard | collision; track title with `= : ' \`; `click=new` | complete, verification, audit, CTDB partial, FLAC tags |
| I | 842–893 | standard | cancel 90 s into tracks 1–3 (pass 1 of a dynamic rip) | status reads cancelled, log well formed, audit (2 checks); `sigterm-world` info; rig-check |
| J | 909–928 | standard | rescan and rip after the cancel | the F set at partial scope |
| J2 | 967–1004 | standard | no `-r`, no `-Z` (uniform), fixed speed 0, isrc off, library move | library move, `without -r/-Z/-S/--prefer-disc-isrc`, argv_agreement. **Note: no tags, cover, AccurateRip or CTDB grading** |
| K1 | 1056–1077 | quick | MP3 at q2 | `expect-derived-output mp3` (count, and that verification was not skipped) plus the FLAC set |
| K2 | 1081–1104 | full | WavPack, cover `file` | same; cover graded on the FLACs |
| K3 | 1108–1131 | full | WAV, cover `complete` | same; **the WAV warning is not asserted** |
| K4 | 1152–1157 | quick | restores the format and cover mode | `expect` |
| L | 1171–1188 | quick | goal presets archival, portable, fast | preset fields (`ctdb_verify_after_rip` and `verify_flac_after_rip` are never asserted per preset) |
| M | 1198–1201 | quick | default track and disc templates | round-trip only |
| N | 1243–1296 | full | whole-disc uniform `-Z 2` | the F set plus `expect-secure-rerip` |
| O | 1318–1320 | standard | `cyanrip -N -f` with **no `-d`** | exit 0, offset found equals B's offset |
| P | 1376–1379 | standard | `cyanrip -N --cache-probe -I` with **no `-d`**; `cache-probe` on the selected drive | exit 0, "Cache probe" field; cd-paranoia is info |
| P2 | 1431–1433 | standard | `cyanrip -N -l 1` with **no `-d`** | exit refused, "Offset is unset" |
| P3 | 1562–1569 | full | `-H -E` and `-H -W`, **no `-d`** | exit 0 only; the clause is stated as unprobed |
| P5 | 1610–1661 | full | 4 installs, 4 timed rips (N/A between rounds) | complete, verification; timings are info |
| P6 | 1716–1792 | full | 8 rips of track 3, ABBA order (N/A between rounds) | same; accuracy tally is info |
| P4 | 1822 | standard | `expect-pregaps-agree` over every log | blocked if fewer than 2 logs; disagreement is info |
| Q | 1866–1889 | quick | restores defaults | `expect` lines, `expect-dialog none` |

Verbs never used by full acceptance: `abort`, `callout`, `needs`, `ok`, `record`, `tier`, `expect-unidentified`, `expect-unknown-record`. The last two are in `unknowndiscacceptance.txt`; `callout` and `record` are in `walkthrough.txt`; `abort`, `needs`, `ok` and `tier` appear in **no** rig script.

---

## C. Coverage matrix

### C1. Menus, dialogs and buttons

| Item | Status | Script line | Note / what would cover it |
|---|---|---|---|
| M1 Rip as Unknown Album | N | — | `unknowndiscacceptance.txt` covers the automatic no-match route, not the menu item. Use a `menu` verb, or `open unknown-album`, on the identified disc |
| M2 Quit (and Quit mid-rip) | N | — | Cannot be scripted: it ends the run. Unit test with a fake worker; `closeEvent` flush is in `test_ui_main_window` |
| M3 Settings dialog | E | 489–491 | Opened and cancelled only. **Accept never runs; `set` bypasses the dialog** |
| M4 Setup & Updates | N | — | Not in `OPENABLE` |
| M5/M6 test console, acceptance | E | (the run itself) | Self-hosting |
| M7 unknown-disc acceptance | N | — | Separate script; needs a second disc |
| M8 Uninstall dialog | N | — | Open and cancel is safe; add to `OPENABLE` |
| M9 Getting started | N | — | In `OPENABLE` but unused |
| M10 User Guide | E | 500–501 | open/cancel |
| M11 Open logs folder | N | — | Externally opened; assert the path exists |
| M12 Copy diagnostics | E | 497–499 | Copy to clipboard (B9) not pressed |
| M13 About | E | 495–496 | "Installed" and "Build under test" lines unasserted (A checks the same fact another way) |
| M14 Set cover art from file… | N | — | Scriptable with a bundled test image |
| M15 Track context actions | N | — | `select-tracks` calls `set_all_selected` and per-row setters, not the menu |
| S1 Check for updates (download, verify, install, restart) | N | — | `expect-newest-pair` reads releases itself. Integration test against a local fake release server; signing is unit-tested (`test_update_signing`) |
| S2 Check for cyanrip updates | N | — | As S1 |
| S3 Choose a build… dialog | N (dialog); E (function) | 1624ff, 1730ff | `install-ripper` calls the step engine and **runs only while a round is open** |
| S4 Check dependencies | E | 492–494 | The result box is not asserted |
| S5 Set up drive (Detect / Analyze cache / Save offset) | E (opened) | 486–488 | Detect never pressed. `cache-probe` (1379) calls the same adapter |
| S6 Diagnose drive access | N | — | Read only; easy to add |
| S7 Run setup… wizard | E | 502–503 | open/cancel |
| S8 Add app shortcut | N | — | Writes outside the session; unit test only |
| S9 channel tick-boxes | E (as settings) | 438–443 | Only through `set`; the box's own save is never clicked |
| B1 Start / Cancel | C | rips; 848 | Cancel through `_on_rip_cancel` with cause `script_step`, not `user` |
| B1 Force stop | N | — | Fault path; scriptable (add a `force-stop` verb) |
| B2 Rescan | C | 526, 909, 1258 | |
| B2 Refresh drive list / drive switch | N | — | Needs a second drive |
| B2 Eject; auto-eject | N (set only) | 430–433 | A tray drive can close itself (`eject -t`); slot loaders cannot |
| B3 View log/report/cue, Open folder, Report bundle | N | — | Add `expect-post-rip-buttons`: each enabled, and its path exists. Do not launch an external viewer |
| B5 Overwrite: new folder | C | 810 | |
| B5 Overwrite: Replace / Cancel / the variant without Replace | N | — | Replace destroys a master: worth one 1-track rip onto a scratch album |
| B6 Release picker | C | 527, 910, 1259 | By row 1, which the verb's own help calls unstable (verbs.py:249–252). A non-first choice is never made |
| B7 Unknown-album dialog, Picard | N | — | The other script answers the confirmation only. Picard is validated only (434–437) |

### C2. Settings

| Setting | Values the run's rips use | Status | Line |
|---|---|---|---|
| rip_goal | fast_verified (F), archival (N); portable as a setting only | C for the presets' fields (L, 1171–1188). `custom` is never set | 662, 1243 |
| output_format | flac C; mp3, wavpack, wav: existence C, content partly E (see §D) | C/E | 1056, 1081, 1108 |
| mp3_vbr_quality | 0, 2 | **E** (no proof it reached ffmpeg) | 1058 |
| cover_art | embed, file, complete: C on FLACs. `""` (off) never; on MP3/WV never | C/N | 665, 1086, 1111 |
| save_additional_art | on | **E** (never graded) | 667 |
| max_retries | 5 C (argv tests); 0 C (J2 `without -r`); 3 round-trip only | C | 414, 971, 987 |
| secure_rerip_matches | 2 C (N secure-rerip); 0 C (J2) | C | 969, 1256 |
| secure_rerip_dynamic | on (F), off (N, J2, P5/P6) | C at N; F's dynamic re-read **fires only on a disc AccurateRip does not confirm** | 664, 1244 |
| rerip_offset_variant | on everywhere | E: fires only on a one-frame (offset-variant) pressing; off is never ripped | 1174 |
| second_read_without_accuraterip | on (most), off (P5/P6) | E: fires only on a disc unknown to AccurateRip | 1616 |
| read_speed_mode / read_speed | auto_ladder; fixed 0 | C for "no `-S`" (J2). The ladder's step-down needs read errors; a non-zero fixed speed is deliberately excluded (aborts on the BDR-209D) | 973, 989 |
| read_offset / override | the drive's | C for config; **N for the applied value** (`rip.read_offset_check` is ungraded) | 398–400 |
| force_overread | off | C (guard) | 418, 1882 |
| prefer_disc_isrc | on C (`with --prefer-disc-isrc`), off C | C | 722, 990 |
| ctdb_verify / verify_flac | on | C that they ran; **N that they passed** (see §0.1) | 668–669, 717 |
| write_eac_log_after_rip | on (F) | C through the audit's `our_log_integrity` and `eac_log_agreement` | 670 |
| track/disc templates | defaults | E: round-trip only; the landing path is never compared with the prediction | 1198–1201 |
| *_unknown templates | defaults | N in full; E in the unknown-disc script (no path check) | 230–231 |
| output_dir | kept | E | 254 |
| library_dir | scratch | C (`expect-library-move`) | 978–984 |
| auto_launch_picard / auto_eject | round-trip | E (setting only) | 430–437 |
| notify_on_completion | on | **E** (the notification is never observed) | 234 |
| update_channel / ripper_channel | round-trip | E: no offer is ever made | 438–443 |
| debug_logging | on | C | 270 |

### C3. Command-line flags

None is run by the acceptance script. Same function, different entry point: `rig-check` ↔ `--rig-check`; `install-ripper` ↔ `--install-ripper`; the acceptance session ↔ `--run-script`. Every flag is referenced in unit tests (`test_app.py`, `test_rig_check.py`, `test_rip_audit.py`, `test_cli_compare.py`, `test_script_surface_is_the_default.py`). **Gap with real value:** `--audit-rips`, `--compare` and `--assemble-best-of` are user tools that operate on real rips, and the run already produces two whole-disc rips of one disc (F and N), the exact input `--compare` exists for. Running them over the session's own rips costs seconds and no drive time.

### C4. Outcomes the UI can show

| Outcome | Status | Note |
|---|---|---|
| Done, clean | C (`expect-rip-complete` on the log, not the label) | 707 |
| Done with the read-instability warning | E | Disc-dependent; counted, not graded (by design) |
| Cancelled during pass 1 | C | 858, 877 |
| Cancelled after the read finished (securing pass) | **N** | A regression on 2026-10-04 lived here (`main_window_helpers.py:466–470`). Scriptable: cancel N as soon as the status reads "Re-ripping…", on a disc that triggers a re-read, or in uniform mode where every track is re-read |
| Failed, with a hint / failed, no diagnosis | N | Fake ripper (`test_multi_pass_rip_end_to_end` has the seam) |
| AccurateRip verified | E | `expect-accuraterip` accepts any answer |
| Offset-variant, no-match, absent | E | Accepted as answers; whether each appears is down to the disc |
| AccurateRip lookup failed | N | Needs a network fault |
| CTDB match / no_match / not_in_db | E | All pass. Partial-scope decline: C |
| CTDB repair (parity) | N | `docs/manual-ctdb-repair.md`, `ctdb/rs_decode.py`; damaged disc or synthetic damage |
| FLAC integrity failed | **N, and it would pass** | §0.1 |
| Derived verify mismatch or decode failure | **N, and it would pass** | §0.1 |
| Exit classes refused / ok | C (P2, A) | |
| Exit classes disc_or_drive / signal / container_tool / failure | N | Fake ripper; fault injection |
| Read offset differs / drive not listed | **N** (computed, never graded) | §0.2 |
| Notification success / failure | N | |
| Data-only "Done." / Enhanced CD audio tally | N | Corpus |

### C5. Error paths

| Path | Status | What would cover it |
|---|---|---|
| No disc | N | One drive, scriptable: `eject`, then `rescan`, expect the no-disc state, then `eject -t` (tray drives) |
| Unknown disc | separate script | Second disc (a CD-R of own recordings) |
| Data-only disc, Enhanced CD | N | Corpus. Note the script header (line 211): "exercised by nothing, anywhere" |
| CD-R | N | Corpus (the same CD-R serves the unknown-disc run) |
| Disc ejected mid-rip | N | Fault injection (fake ripper exiting with the disc-gone text). On hardware the tray is usually locked; a USB drive pulled is a manual test |
| Disc swapped between scan and Start | N | `disc_identity` unit tests; on the rig, two discs and a human |
| Output unwritable | N | **Scriptable on one drive**: set `output_dir` to a `chmod 555` folder inside the session, expect the Start refusal or the preflight row, then restore |
| Output full | N, **and the app has no free-space check** | A small loop or tmpfs mount set up by the operator, or `LD_PRELOAD`/seccomp fault injection; unit tests pass messages through only |
| Network down, or MB/AR/CTDB/cover art failing or slow | N (the run requires the network at A, line 312) | A fault proxy (toxiproxy) in front of each host in a CI integration test with recorded responses; on the rig, a "lookup host override" seam |
| Ripper missing or wrong build | C for wrong build (A aborts); N for missing | Dependency-check unit tests |
| Container not running or cold | E (A4 `app-log` info, 321–322) | `container_gate` unit tests; a cold-start rig run is an operator step |
| Offset unknown, refused at Start | N/A-rig (588) | Second drive not in the AccurateRip list, or a fake drive descriptor |
| Offset disagreement prompt | N | Set `read_offset` to listed+1 with the override on, then answer No/Yes. Scriptable, but it must be restored |
| Track name over 255 bytes; `..` title; control characters | N on the rig | Scriptable: `track-title 1 ..` then `rip`, expect a "Cannot start rip" dialog, then `answer-dialog ok` |
| Bad config on load ("Some settings were reset") | N | Unit test; on the rig, corrupting config.toml is invasive |

---

## D. Specific checks requested

### D1. K1–K3 derived formats

- **Tags and cover art in the derived files:** not checked. `expect-tags` and `expect-cover-art` read the FLAC masters only (`tag_grading.py`: "these open the audio files themselves, through `read_flac_metadata`"). MP3 ID3v2 tags, the MP3's embedded APIC, WavPack APEv2 tags and MP3 ReplayGain (`adapters/mp3_replaygain.py`) are never read. K1's severity reason and line 1017 both claim them.
- **Duration and sample count:** WavPack and WAV are hashed against the master's PCM by `derived_verify.py`, which would prove sample equality. **But a mismatch reaches the report as `"ran — failed"`, which both `expect-derived-output` and `expect-verification` accept** (§0.1). The MP3 is decoded clean and counted, with no duration check. Expected length is the master's samples plus the encoder delay and padding, which the LAME tag records.
- **`mp3_vbr_quality 2` reaching the encoder:** no. `transcode._build_argv` passes `-q:a N` (line 191), but the report records only `settings.mp3_vbr_quality` from config (`rip_report.py:1345`), and the transcode block has no argv. Fixes, cheapest first: (a) record the ffmpeg argv in the report's transcode block and grade it with an `expect-transcode-argv` verb; (b) read the LAME/Xing tag's quality byte from one MP3; (c) differential: average bitrate at q2 is below q0 on the same track (K1 against a q0 rip).
- **The WAV warning:** not asserted. It exists only as `settings_dialog._wav_warning_label`, shown while the combo box shows WAV (`settings_dialog.py:317–325, 1102–1104`). The script sets `output_format wav` through `set` and never opens Settings with WAV selected. Covering it needs a step that opens Settings after `set output_format wav` and asserts the label is visible, or an `expect-widget` verb.

### D2. M naming templates

- Only the defaults are round-tripped (1198–1201). That is a validator check; nothing rips with them changed.
- **No non-default template is ever ripped.** No rip checks that files landed where the template predicts. The graders find the folder from wherever the log landed (`_rip_album_dir`: `Path(log_file).parent`), so a template the ripper ignored would still be graded in the right place. Critical rule #3, the preview against reality, is never compared on hardware.
- **Unknown-album templates:** set to the defaults in the baseline (230–231). They are never used in the full run, and the unknown-disc run does not check the path (`grade_unknown_record` reads only the report's `disc` block).
- **Illegal and path-traversing characters:** on the rig, only H's track title (`E=MC2: Rock 'n' Roll \ Part 2`, line 808) and F's album title (`:` and `<`). Never on the rig: `/` in a title; a `..` title (refused at Start by `path_segment_issue`); a year of `..` with `%y` (peer review 2.7, `settings_validation.py:567–575`); names over 255 bytes; Windows-reserved characters in a *template* (warn, never block). All of these have unit tests (`test_settings_validation.py:598, 645, 763–835`; `test_title_filenames.py`), but none of the cyanrip-side behaviour (what `-T unicode` actually writes) is checked anywhere except F's colon.
- Proposal: one J2-style one-track rip with a non-default template that uses every token (`%y/%A/%a - %d [%M]/%N %t - %n`), a title carrying `/`, `..`-like text and a 200-byte UTF-8 run. Assert the predicted relative path exists (`naming.render_preview` against the disk), then restore. Add a refusal step for a literal `..` title.

### D3. Direct `cyanrip` steps and `-d`

None of O (1318), P (1376), P2 (1431) or P3 (1562, 1568) passes `-d`. The verb adds no device (runner.py:1759–1922), and there is no `(device)` placeholder. On a two-drive machine:

- **O** grades the default drive's `-f` answer against the selected drive's offset, so it could pass or fail about the wrong drive.
- **P** compares cyanrip's probe of the default drive with `cd-paranoia -A` on the selected one.
- **P2** could refuse on the other drive and pass. If that drive is empty, it fails with the wrong diagnosis.
- **P3** reads the other drive using this drive's `-s`.

The older `round08joint.txt` hard-coded `-d /dev/sr0` (lines 231–338), which is also wrong on a second machine. Fix: a `(device)` placeholder that expands to `_drive_picker.current_device()`. The sanitiser should also refuse a non-probe invocation without `-d`, enforced by `test_every_scripted_cyanrip_invocation_survives_the_sanitiser`. This matters to the 0.8.1 gate, which needs two machines.

### D4. P4 before P5/P6

Fixed at this commit, as described in §0.7.

### D5. An inventory-driven guard for verbs and dialogs

There is none. What exists:

- `test_every_step_names_a_verb_that_exists_and_is_built`: a direction check (script → table).
- `test_every_openable_dialog_names_a_real_method`: `OPENABLE` → a window method.
- `test_the_baseline_sets_or_keeps_every_user_setting`: settings only.
- `test_help_documents_the_menu`: help text → menus.

Nothing checks table → used, `OPENABLE` → opened, menu → openable, or setup-center action → reached. A proposed `tests/test_acceptance_inventory.py` would:

1. Enumerate the verbs from `_VERB_LIST`, the dialogs from `OPENABLE`, the menu actions by parsing `_build_menus` (or by building the window under `qapp` and walking `menuBar().actions()`), the setup-center actions from the `actions={…}` dict, the `QPushButton` labels and the flags from `build_parser()`.
2. Require each one to be used in a named rig script, or to sit in an explicit ledger (`acceptance-not-scripted.toml`) with a reason and the name of the unit test that covers it.
3. Fail on a ledger entry whose covering test does not exist.

This turns "what is missing" from a reading exercise into a CI failure, the same move the baseline test made for settings.

---

## E. Gaps ranked by risk to an existing feature working for a user

| Rank | Gap | Why the risk is high | Cheapest cover |
|---|---|---|---|
| 1 | **Failed FLAC-integrity or derived verification passes** (`"ran — failed"` accepted by `expect-verification` and `expect-derived-output`; the audit has no such check) | A corrupt master, or a WavPack/WAV that is not bit-identical, ships under a green ARCHIVAL section. Disc-independent, so always our defect | Grade `gates.flac_integrity` and `gates.derived` as `ran — passed` (keep CTDB and AccurateRip disc-agnostic). Add a unit test with a `ran — failed` report |
| 2 | **The applied read offset is ungraded** (`rip.read_offset_check` is never read; `-s` value never asserted) | Every rip's accuracy rests on it, and AccurateRip and CTDB pass on mismatch, so a sign or offset regression stays green | `expect-rip-argv with -s (offset)` (needs a value form), plus grading `read_offset_check == matches` on a listed drive |
| 3 | **The derived files' own tags, art and ReplayGain are never read; `-q:a` is unproven** | The MP3 is the user's library entry (K1's own severity reason) | `expect-tags <fmt>` / `expect-cover-art <fmt>` through mutagen or ffprobe; record the transcode argv in the report |
| 4 | **The Settings dialog's Accept path never runs on the rig** (`set` writes config directly) | Every user changes settings through the dialog; a widget-to-field mapping bug is invisible | A `settings-dialog` verb that sets widgets and presses OK, for at least goal, format, cover, templates and offset; read back with `expect` |
| 5 | **Naming: no non-default or unknown template is ripped; the landing path is never compared with the prediction; illegal titles are not refused on the rig** | Library-wide misfiling. Critical rule #3 is untested on hardware | One one-track rip with an every-token template; a `..`-title refusal step |
| 6 | **Overwrite prompt: Replace and Cancel never taken** | Replace destroys a finished master, the defect the prompt exists for | A one-track scratch album, Replace, then assert the old folder is gone and the new rip is complete |
| 7 | **Cancel during the securing pass, and Force stop, never exercised** | A known regression lived here (2026-10-04); Force stop is the user's escape from a wedged drive | A cancel step gated on the status reading "Re-ripping…" (uniform mode guarantees a re-read); a `force-stop` verb |
| 8 | **Direct `cyanrip` steps without `-d`** | Evidence about the wrong drive on the second machine the 0.8.1 gate requires | A `(device)` placeholder and a sanitiser rule |
| 9 | **Setup & Updates and the update paths are never opened** (S1–S3, S6, S9); `open setup` reaches only the wizard | A broken updater strands users on old builds; Choose a build is the documented route (header line 61) | Add `setup-center` to `OPENABLE`; an integration test for S1/S2 against a local fake manifest |
| 10 | **Eject, insert, swap and no-disc cycle never exercised** | Every user ejects; the media watcher and disc-return logic have rig history (`main_window_disc_return.py`) | On tray drives: `eject`, `expect` the no-disc state, `eject -t`, `rescan`, and expect the same disc ID |
| 11 | **Offset refusal and disagreement prompts are unreachable on the reference rig** (E2 N/A) | Every user with an unlisted drive hits the refusal | A second drive not in the AccurateRip list; or a disagreement step (listed+1, answer Yes) |
| 12 | **Network and lookup failure paths are unscriptable** (A requires the network) | MB, AccurateRip and CTDB outages are common; the fallbacks (placeholder rows, "lookup failed") are unit-only | CI integration with a fault proxy; a host-override seam for one rig section after A |
| 13 | **Disk full and unwritable output** (no free-space precheck exists; unwritable never exercised) | A whole-disc rip failing at hour two | A `chmod 555` output step on the rig (one drive, scriptable); disk full through an operator-made small mount or fault injection |
| 14 | **Post-rip buttons are never checked** (View log/report/cue, Open folder, Report bundle silently no-op on `None`) | The user's way into the evidence | An `expect-post-rip-buttons` verb asserting each is enabled and its path exists |
| 15 | **WAV warning, `save_additional_art`, notification, `cover_art ""` (off) never asserted** | Small individually; K3's title promises the warning | Settings-dialog widget check; grade extra art files; observe the notification through the D-Bus session monitor or a notifier seam |

Lower: `pick-release 1` instead of an MBID (stable within one run); the getting-started, uninstall and logs-folder items; the 8 unused verbs; CLI tools not run over the session's own rips.

---

## F. What one healthy disc and one drive cannot cover, and what would

| Item | Why not | What would cover it |
|---|---|---|
| Paranoia error correction, read errors, the speed ladder stepping down, a non-zero `Read stalls:`, C2 | Healthy media has no errors | Damaged-disc corpus (scratched pressings, a deliberately marked CD-R); fake ripper replaying captured damaged-disc logs; CTDB parity repair on synthetic damage (`ctdb/rs_decode` unit tests already exist) |
| Offset-variant re-read (`rerip_offset_variant`) | Needs a one-frame-match pressing | Corpus: a pressing known to match AccurateRip only offset-shifted |
| `second_read_without_accuraterip`; F's dynamic re-read | Needs a disc unknown to AccurateRip | Corpus: a CD-R of own recordings (also the unknown-MusicBrainz disc) |
| HTOA (audio in track 1 index 00) | Disc property | Corpus; parser fixtures exist in `test_parsers_cyanrip_log` and `test_rip_worker` |
| Pre-emphasis (`FLAGS PRE`, P3 plain `-H`) | Disc property | A pre-emphasised pressing (early-1980s CDs); P3 is unprobed by design |
| Data track, Enhanced CD, mixed mode | Disc property (T5) | Corpus |
| CD-Text, disc ISRCs | Disc property (`isrcdisc.txt` exists) | Corpus |
| Unknown to MusicBrainz | Disc property | The unknown-disc run with its own disc |
| Several MusicBrainz candidates, choosing a non-first one | Disc property | A multi-release disc; `pick-release <mbid-prefix>` |
| Offset refusal (unlisted drive); drive switching; per-drive offsets; `-d` correctness | One drive | Second drive (ideally unlisted), or a fake drive list |
| Overread (`-O`) | Hangs the BDR-209D | A different drive model; TASKS R106 |
| Disc removed mid-rip | Tray locked; destructive | Fake ripper; a USB drive unplugged by hand |
| Quit or window close mid-rip | Ends the run | Unit test (`closeEvent`); a separate one-step script whose result is read on the next launch |
| Network down, slow lookups | The run requires the network | Fault proxy in CI; recorded HTTP fixtures |
| Disk full | Needs a full filesystem | Small loop or tmpfs mount; an `ENOSPC` injection shim |
| App self-update, install and restart | Needs a newer release | A local signed fake release in an integration test |

---

## G. Methods to find what the team does not know it is missing (ranked by value per effort)

1. **Artifact and grader mutation ("plant a defect, does a step fail?").** Highest value per effort. The graders are pure and Qt-free (`artifact_grading.py`, `tag_grading.py`, `permutation_grading.py`, `accuracy_grading.py`, `pregap_grading.py`). The repository already stores real Full-run reports as fixtures (`tests/fixtures/evidence/.../round29full*report.json`, round 31–32). Build a matrix of planted defects and replay every grader against each:
   - set `gates.derived` or `flac_integrity` to `ran — failed`;
   - remove an ALBUM tag, swap `:` for `∶`, strip the picture;
   - truncate a FLAC;
   - change `-s` in the argv;
   - delete the cue's `FLAGS PRE`;
   - set `read_offset_check: differs`.
   
   Every surviving defect is a §5.bi hole. It would have found §0.1 and §0.2 in an afternoon. Extend the existing `scripts/mutation_sweep.py` targets to `uiscript/*_grading.py` as a second layer; its current 15 targets include no grader.
2. **A source-generated inventory guard** (§D5). Cheap, permanent and drift-proof. It makes every new menu item, button, verb, dialog, setting value or flag either scripted or explicitly ledgered with its covering test.
3. **coverage.py over a Full run, diffed against the inventory and against CI coverage.** Run the app from source on the rig under coverage, with `concurrency = ["thread"]` for the Qt workers and `COVERAGE_CORE=sysmon` on 3.12 for low overhead on a multi-hour, I/O-bound run. Partition the executed lines three ways: (a) run by hardware only (highest value: these are what CI cannot see); (b) run by neither; (c) run by CI only. Intersect (b) with the outcome and error-path modules (`ripper_exit_class`, `cancel_cause`, `main_window_disc_return`, `disc_identity`, `update_*`) to get a measured list of unreached branches rather than a remembered one. Medium effort: one instrumented Standard run.
4. **Mining the filed run history for decoration.** The bundles and script reports kept as evidence fixtures record each step's outcome, detail and elapsed time. Flag every step whose PASS detail is byte-identical across runs on different builds or discs: it is probably not reading its subject. Also flag every INFO row that never varied (a candidate for promotion to an assertion), and every grader that passed in under 10 ms over an artifact it claims to open. Cheap, and specific to this repository's long run ledger.
5. **Differential rips against another ripper.** whipper runs on Linux and can share the container. Rip the reference disc and compare per-track AccurateRip v1/v2 and EAC CRC32, and also what AccurateRip cannot judge: pregap lengths (P4's subject), ISRCs, the cue layout, HTOA, and the pre-emphasis flag. EAC, XLD, dBpoweramp and CUERipper need Windows or macOS; use filed logs of the same pressing where they exist (the EAC baseline used for +667). Medium effort. Highest value for the accuracy claims nothing else can check.
6. **Fault injection at the worker boundaries.** The fake-ripper seam exists (`tests/test_multi_pass_rip_end_to_end.py`); `test_fault_injection.py` covers the evidence bundle only. Extend it to: ripper exit 74, signals and unreapable children; `ENOSPC` mid-track; disc-gone text; MusicBrainz, AccurateRip, CTDB and cover-art hosts timing out or returning 503 through a proxy; a cold container. Add two on-rig steps that need no root: an unwritable output folder, and an offset-disagreement prompt.
7. **Pairwise settings combinations in CI.** Generate the allowed values from the validator's constants and the `_ALLOWED_*` sets; allpairs gives about 30 configurations. For each, build the argv and plan with the fake ripper and assert the invariants: `-r` ceiling against `-Z`, no `-S` on fixed 0, `-s` present when the override is on, the transcode argv carries `-q:a N`, and cover actions match `plan_actions`. Hardware is too costly for this; the argv builder is not.
8. **Round-trip and metamorphic property tests for the cue, log and EAC-export parsers.** Hypothesis "never raises" properties already exist (`test_parsers_property.py`, `test_parsers_structure_fuzz.py`). What is missing are round trips (render an EAC log, parse it, get the same CRCs; render a cue, parse it, get the same pregaps and ISRCs) and metamorphic ones (shifting every index by k frames shifts every pregap by k). Lower marginal value because the base exists.
