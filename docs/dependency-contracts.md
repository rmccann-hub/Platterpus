# Dependency contracts — allowable arguments, syntax & expected output

**What this is:** the single reference for *how Platterpus talks to each external
dependency* — the exact arguments/flags we pass, the syntax those tools expect,
and the output shape we rely on. It's the counterpart to the *"validate every
input and every dependency output"* rule in `CLAUDE.md` (Code conventions): input
validation checks what the **user** typed; this doc is the contract the **code**
must satisfy when it hands work to a dependency, and what it must be ready to
parse (and log) back.

**Why it exists:** external CLIs change their flags and output between versions.
When they do, this is the place to confirm what we assumed and what changed —
paired with the never-raises parsers (`docs/testing.md`) that absorb *minor*
drift and the `RipBackend`/adapter seams (Critical rule #1) that isolate a
*major* change. If you're adding a dependency call or a new flag, record it here
in the same change (Critical rule #7 — documentation currency).

**Ground truth:** every entry below is what the code in `src/platterpus/` actually
invokes today (file references given), not a copy of the upstream man page. When
in doubt, the adapter is authoritative; this doc must be kept in step with it.

**Scope note:** parsers of dependency output **never raise** — they return a
best-effort dataclass (`docs/testing.md`). So "expected output" here is the
*happy-path shape we parse*, not a guarantee; a mismatch degrades gracefully and,
for a hard failure, the dependency's stderr is captured to the log.

**Deliberately not covered here** (so the absence isn't read as a gap): the
one-shot *provisioning and integration* command surfaces — the host-setup /
teardown engines and the dependency registry's install commands (`distrobox`,
`dnf`, `flatpak`, `pkexec`, `distrobox-export`, … — see `deps/host_setup.py`,
`deps/host_teardown.py`, and `deps/registry.py`), the AppImage
desktop-integration calls (`kbuildsycoca6`, `gio` — `appimage_integration.py`),
and the GitHub releases API used by the update check/installer
(`update_check.py` / `update_install.py`). Those invocations are owned,
documented, and tested alongside their engines; this doc covers the
**rip/verify/metadata path** — the tools whose arguments and parsed output a
rip's correctness depends on. If one of the excluded surfaces ever grows a
parsed-output contract of its own, it gains a section here like the rest.

---

## cyanrip — the ripping backend (sole backend, KDD-18)

Invoked as the host-exported `~/.local/bin/cyanrip` (Distrobox routing, Critical
rule #3). Argv is built in `adapters/cyanrip_backend.py::_build_rip_argv`.

**Flags we pass (rip):**

| Flag | Meaning | When Platterpus passes it |
|------|---------|---------------------------|
| `-d <dev>` | drive device | always, when a device is known |
| `-s <int>` | read offset (samples, signed) | when `override_read_offset` is on (cyanrip has no config file — it needs the offset every run) |
| `-o flac` | output codec | always (FLAC is the archival master, Critical rule #4) |
| `-r <int>` | max retries per track | when `max_retries > 0` |
| `-Z <int>` | re-rip a track until N reads' checksums agree | only when `secure_rerip_matches > 0`; the user's number is the ceiling (dynamic mode applies it only to AccurateRip-failing tracks) |
| `-O` | overread into the lead-in/lead-out (upstream help: "may freeze if unsupported by drive") | only when the Settings "Overread" toggle (`force_overread`) is on — off by default, matching EAC's baseline "overread: No". **Flag verified against 0.9.3.1 + master (2026-07-21); `-x` did not exist in cyanrip at that date — it does now, in the fork, as the *cache probe* and not overread (see the `-x` block quote below).** **⚠ CONFIRMED to hang the Pioneer BDR-209D (real-hardware finding, 2026-07-22): 13 of 14 tracks ripped perfectly, then the drive hung ~23 min reading the last track's lead-out with the progress bar frozen near 100 %, exactly the upstream-warned failure. Overread should stay OFF on this drive; the GUI default is off.** |
| `-S <int>` | cap read speed (× multiplier) | only when a positive fixed speed is requested. **⚠ ABORTS the rip (`EINVAL`) on a drive that reports speed as "unchangeable"** (the Pioneer BDR-209D does) — so the ladder parses `speed_changeable` and never sends `-S` to a speed-locked drive (real-hardware finding, 2026-07-01) |
| `-l <n,n,…>` | rip only these 1-based track numbers | **two producers:** the user's per-track "Rip?" checkboxes (a deliberate partial rip, since v0.5.7) and the per-track auto-fix re-rip (a cheap targeted re-read). Empty = whole disc, which is also what "every track ticked" sends. |
| `-N` | disable cyanrip's own MusicBrainz lookup | **always** (Critical rule #5 — the GUI feeds tags via `-a`/`-t`, so cyanrip stays offline and never shows its interactive prompt) |
| `-a <k=v:k=v…>` | album-level tags | from the GUI's fetched+edited metadata |
| `-t <n=k=v:…>` | per-track tags (1-based) | from the GUI's metadata |
| `-D <scheme>` / `-F <scheme>` | directory / filename naming scheme | translated from the whipper-style template (`scheme_from_template`) |
| `-G` | disable cover-art embedding | when cover art is not being embedded |
| `-T <mode>` | filename-sanitation scheme applied to tag values before they become path segments | **always, pinned to `unicode`** (`SANITISE_MODE`). Never defaulted: we passed nothing here until 2026-08-23, so every rip inherited whatever default the build shipped while the naming preview and the overwrite guard predicted a two-glyph table — an unpredicted `<` → `‹` silently overwrote a finished 14-track rip. `unicode` is the fork's own default, so the pin is a no-op today and a fence tomorrow; the `os_*` modes substitute *fewer* characters (only those the build's OS forbids), so they are not a way to ask for the look-alikes |
| `-c <n>/<m>` | disc number / total discs | whenever the release carries a usable disc position, including `-c 1/1` on a single disc. Range-checked in `_disc_args` before it becomes argv — cyanrip refuses the whole rip on a bad value |
| `--consumer <name>/<version>` | who drove the rip, recorded verbatim in cyanrip's logfile | only when the ripper build is known to accept it (`consumer_tag_for_build` → `fork_source.accepts_consumer_flag`, keyed on the build tag, not the version). Fork-only; the tag is validated at the argv chokepoint |

**Gap/pregap handling (`-p`) — deliberately never passed.** cyanrip's default
gap behaviour already matches EAC's, so we pass **no `-p`**. Verified against
upstream README §"Pregap handling" (0.9.3.1 + master): *"By default, track 1
pregap is ignored, while any other track's pregap is merged into the previous
track. This is identical to EAC's default behaviour."* The contract, for the
record: `-p` is a **per-track** override — `-p track_number=action`, repeated
separately for each track (track index 1–197) — with actions `default` (merge
into previous, drop on track 1), `merge` (into current track), `drop` (delete
the pregap — **breaks cyanrip's no-discontinuities guarantee; not archival**),
and `track` (split into a new track, which **renumbers all following tracks**
and would desync our per-track `-t`/`-l`/progress/AccurateRip alignment). There
is no global form: a bare `-p default` parses as track 0 and aborts the rip.
Only the default (no flag) is archival-safe, which is why it's the only mode we
use. See `docs/eac-parity.md` Part A (pre-gaps in the cue) for the `INDEX 00`
cue-metadata question (separate, decision-gated).

**Tag string syntax (`-a`/`-t`) — a real trap:** the value list is
`key=value:key=value`, parsed by FFmpeg's `av_dict_parse_string`, **but** cyanrip
first runs it through `append_missing_keys()` which splits on `:` *naïvely*
(ignoring backslash/quote escapes). So a literal `:` in a value cannot be escaped
— we substitute the look-alike `∶` (U+2236) and restore the real colon in the
FLAC tags post-rip via metaflac (`_escape_meta_value` / `restore_substituted_colons`).
Other tokenizer-special chars (`\ = '`) are backslash-escaped.

**Filename / path cross-filesystem safety (the `-D`/`-F` output on disk).**
cyanrip builds each folder/file segment from the naming template with the fetched
tag values substituted in, and sanitises them with the scheme `-T` selects: we
pin `unicode`, which swaps the ten characters of `crip_char_replacement[]` for
Unicode look-alikes (full table in the cross-filesystem paragraph below, and in
`naming._VALUE_SANITISE`). The two that matter most on the primary Linux target:
`:` → `∶` (U+2236) and a `/` *inside a value* → `∕` (U+2215) (a `/` in the
template itself stays a real separator). On ext4/btrfs — the Bazzite target — the
only truly-illegal filename bytes are `/` and NUL, and both are covered: `/` is
mapped, and NUL can't reach here because MB values are text and the
Settings/config boundary rejects every control character
(`settings_validation._has_control_char`). So on the target filesystem the output
is always writable, and any genuinely-unwritable name (e.g. a component over the
255-**byte** ext4 limit from a very long multibyte title) fails the rip **loudly**
(captured stderr + log), never silently.

**`.` and `..` are *ours* to reject, not cyanrip's to map** (audit, 2026-07-31).
"Writable" was doing too much work in the paragraph above: the two segments POSIX
reserves for *this* and *the parent* directory are not illegal **characters**, so
nothing in cyanrip's sanitiser touches them — an album titled `..` made `-D`
resolve one level **above** the output directory and the rip landed outside the
folder the user chose. Identical to the `%Y` escape fixed 2026-07-28, which was
closed only for the one token Platterpus substitutes itself. So the four
path-bearing values we pass — `album_artist`, `album`, per-track `title` and
`artist` — are validated **before** the argv is built:
`settings_validation.path_segment_issue` refuses a value whose stripped form is
`.` or `..` (and any control character), the track table shows that message
before Start, and `cyanrip_backend._reject_path_reference_values` raises
`RipError` rather than build the rip. Deliberately *only* those two names: `...`,
`..and Justice for All` and a trailing dot are ordinary Linux directory names and
are left alone, because re-sanitising cyanrip's naming is exactly what Critical
Rule #3 forbids. Values that only ever become tags (genre, barcode, catalog
number, ISRC, label) are not path-bearing and are not checked.

**Not sanitised — a documented cross-filesystem limitation, not a silent bug**
(naming audit, 2026-07-08; the character half corrected 2026-08-23). cyanrip
*does* remap the other Windows/NTFS/exFAT-reserved characters. Under
`-T unicode` — the mode `cyanrip_backend.SANITISE_MODE` pins —
`crip_char_replacement[]` substitutes `<` → `‹` (U+2039), `>` → `›` (U+203A),
`|` → `│` (U+2502), `?` → `？` (U+FF1F), `*` → `∗` (U+2217), `\` → `⧹` (U+29F9)
and `"` → `“`/`”` (U+201C/U+201D, chosen by a parity flag no lookup table can
express), alongside the `:` and `/` above. That table is read out of the fork's
generated provider contract P7b and mirrored in `naming._VALUE_SANITISE`, never
observed one glyph at a time — the two-entry guess it replaced is what let an
unpredicted `<` → `‹` silently overwrite a finished 14-track rip on 2026-08-23.
What genuinely is *not* remapped: the reserved device
names (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`9`, `LPT1`–`9`), trailing
dots/spaces, and case collisions (two titles differing
only in case collide on those case-insensitive filesystems). All of these are
legal on Linux, so a rip to the native
library succeeds; they bite only when the output directory is on a mounted
NTFS/exFAT volume or the library is later copied to Windows/macOS. Platterpus
deliberately does **not** re-sanitise the names cyanrip produces — Critical Rule
#3 (the ripper owns naming; overriding it would duplicate cyanrip's logic and
break the Settings naming preview↔reality round-trip). The non-overriding
mitigation shipped 2026-07-21 (maintainer-approved): a **non-blocking Settings
warning** (`settings_validation.cross_fs_hazards`) flags a naming template whose
*literal* text is Windows-unsafe (reserved chars/device names, trailing
dots/spaces). Hazards inside tag **values** remain out of reach by design — they
are produced at rip time by cyanrip's own sanitiser — so this paragraph stays
the honest record of that residual limitation.

**Info / probe flags:** `-I -N` (info-only, computes DiscID/CDDB locally, no
network — `disc_info`); `-V` then `--version` (version — `cyanrip_cli.VERSION_FLAGS`,
and the probe table below says why two). **Both probes are strict about the exit
code** (`CyanripImpl._run(strict=True)`): a non-zero exit is logged with
cyanrip's own output *and* raised as `RipError`, never returned as text. A
recognised version flag prints `cyanrip <version> (<vcstag>)` and returns **0**
(0.9.3.1's `case 'V':` logs the banner and returns 0), so a run in which *every*
flag failed points at the host export / container — but a single non-zero exit
does not, because stock builds after 0.9.3 reject `-V` themselves. The
`--doctor` routing check additionally requires a *recognisable version* in that
output (`preflight.version_banner`, which reuses the dependency subsystem's
`parse_version`) — output with no version means the check FAILS, because the
check exists to prove the chain reaches cyanrip and any-string-accepted is not
proof. It scans for the versioned **line** rather than line 1: a cold Distrobox
container prints its own startup chatter first, and stderr is folded into stdout
by `run_capture`. **cyanrip's offset-finder is
deliberately unused** — its `-f` IS a "find drive offset" mode (verified
against 0.9.3.1 + master getopt/help, 2026-07-21: `-f  Find drive offset
(requires a disc with an AccuRip DB entry)`), but an earlier build that ran it
regex-scraped "offset…N", read a default 0, and silently overrode the correct
list value — so it was removed and `find_offset` stays unimplemented (inherits
`NotImplementedError`). The read offset comes from the bundled AccurateRip
drive-model list (`adapters/accuraterip_offsets.py`) or manual entry, never
from a cyanrip probe. *(This corrects an earlier version of this paragraph
that mis-described `-f` as "force-overread" — overread is `-O`, now the
Settings "Overread" toggle. A re-vetted `-f` wizard integration is a tracked
maintainer call — see the TASKS feature backlog.)*

**Expected output we parse** (`parsers/cyanrip_log.py`, `parsers/cyanrip_info.py`):
the finish log's banner (`Drive:`, `Disc tracks: N`, `Speed: default
(unchangeable)` → `speed_changeable`, offset → `read_offset`, `DiscID:` →
`disc_id` and `CDDB ID:` → `cddb_id` — both TOC-derived, used as the "same
physical disc" key by the re-rip comparison), per-track blocks (`Track N
ripped and encoded …`, `EAC CRC32:`, `Accurip v1/v2: … (accurately ripped,
confidence N)`, `Accurip 450:` → the offset-variant match, `(after N rips)` →
`rip_count`, extraction speed/quality,
`Done; (M out of N matches …)` / `(no matches found, but hit repeat limit of N)`
→ `secure_rerip_converged`), the AccurateRip summary, album loudness, and the
`Log FUN512:` signature. cyanrip writes its own `.log` + `.cue` at the end; a
**cancelled** rip writes neither. **Note:** the banner block yields `drive`,
`read_offset`, `disc_id`, `cddb_id`, `speed_changeable`, the disc duration,
and — added with the v0.5.12 EAC-layout work — `album`, `album_artist`,
`c2_pointers` (from `C2 errors:`; a *drive capability*, not a statement that
C2 was used), `paranoia_level`, `overread_mode`, `gap_detection` (the `Gaps:`
block) and `output_formats`. Per-track, the parser also yields `start_sector`
/ `end_sector` (`Start LSN:` / `End LSN:`, which build the EAC-layout TOC
table) and `pregap_sectors` (`Pregap LSN:`). cyanrip prints **two cache lines,
and neither is a cache-defeat verdict** — which is why there is no `cache` field
to parse: `Cache model:` is libcdio-paranoia's *modelled* size, and
`Cache probe:` is the `-x` probe's own measured readback result (fork). Both are
in `parsers/cyanrip_log.py`'s `_IGNORED_DISC_LINES` with a reason (see the
cache-handling note below; this corrects two earlier versions of this doc — one
that implied a `cache` field, one that said cyanrip prints no cache line at all).

Two corrections to the paragraph above, both from the 2026-07-31 pass:

- "extraction speed/quality" described the **whipper** log's fields, not
  cyanrip's. cyanrip 0.9.3 prints **no per-track speed, elapsed time or quality**
  at all (that is the §2.3 gap below), so `extraction_speed` /
  `extraction_quality` are `None` on every track of every committed cyanrip log.
- `Appended:    N frames of silence` **is** parsed now, into
  `TrackResult.appended_silence_frames` (see the graduation note below).

**Lines a FORK of cyanrip will print, which we already parse — *fork-only, NOT in
0.9.3*.** The maintainer is fixing cyanrip in their own fork, and Platterpus reads
the new rows *before* they exist so one build serves both: an AppImage user's
deployed **cyanrip 0.9.3 prints none of these**, and every field below then stays
`None` and every surface behaves exactly as it did. Full specification and evidence
per row: [`cyanrip-upstream.md`](cyanrip-upstream.md).

| Fork-only line (indented, per-track) | → field | EAC row it fills | Ask |
|---|---|---|---|
| `Sample peak:  -0.5 dBFS` — or a `Sample peak:` sub-header followed by `Peak:  -0.5 dBFS`, cyanrip's existing style for `True peak:`. Unit (`dBFS` or `%`) **required**; a value above full scale is refused and logged | `peak_level` (linear fraction) | `Peak level` | §2.1 |
| `Speed:  1.6x` / `Extraction speed: 1.6 X` (indented — the column-0 `Speed:` row is the drive's speed-changeability and is unaffected) | `extraction_speed` | `Extraction speed` | §2.3 |
| `Elapsed:  161.00 s` (also `Elapsed time:`, `Rip time:`, `Extraction time:`, `Time taken:`; unit `s`/`sec`/`secs`/`seconds`) — **a scalar with a unit, not a clock.** The `(HH:)MM:SS` sibling rule was retired 2026-08-21: it matched 0 of 19 committed fork logs and 0 of 11 stock logs, and the fork's pre-split combined line `Elapsed:  %s (%.1fx)` was refused by its end-of-line anchor anyway. The shipped build emits `Elapsed:  %.2f s`, split from that combined form at their `89eb849` | `extraction_elapsed_seconds` | *none* — rendered as an extra `Extraction time` row, never converted into a speed | §2.3 |
| `Secure re-read: converged (2 out of 2 matches)` / `did NOT converge (…)` / `not attempted`; or the existing `Done; (…)` text routed through the log so it arrives **indented** | `secure_rerip_converged` (True / False / left alone) | drives the `Test CRC`/`Copy CRC` pair vs the "re-reads did NOT agree" caveat | §2.4 |
| `C2 errors:  supported by drive, not used` (column 0) | `c2_pointers` = `False` | `Make use of C2 pointers` | §2.5 |

Three properties of that table are load-bearing, not incidental:

- **cyanrip's `True peak:` must never fill `peak_level`.** EAC's `Peak level` is
  the **sample** peak as a percentage of full scale and cannot exceed 100 %; the
  true (4x-oversampled) peak is a different quantity that legitimately does — all
  fourteen reference tracks are 100.8 %–109.7 %. Only a line that says *sample*
  peak is accepted, and any value over full scale is refused.
- **Indentation disambiguates the `-Z` verdict.** A column-0 `Done; (…)` is the
  stdout form and belongs to the **next** track (0.9.3 prints it before the
  `Track N ripped…` opener); an indented one was written by
  `cyanrip_log_track_end()` and belongs to the track already open.
- **A bare `supported by drive` still means unknown.** It states a drive
  *capability*; EAC's row asks what the rip *did*. Only the wording that states
  usage may answer it.

**Album loudness and peaks: two sources for the same four facts, and only one of
them is cyanrip's.** Fixed 2026-08-21; the previous version of this doc said only
"album loudness" and named no line, which is how the wrong source went unnoticed.
cyanrip prints the whole-disc figures **twice**:

| Source | Shape | Owned by | Status |
|---|---|---|---|
| FFmpeg's `ebur128` summary | `Album Loudness Summary:` then indented `Integrated loudness:` / `Loudness range:` / `Sample peak:` / `True peak:` sub-headers, each with an `I:` / `LRA:` / `Peak:` value line | **libavfilter** | Fork's **P3 — unstable wording**: "moves when FFmpeg does. Prefer the … lines in P2, which are ours" |
| cyanrip's own rows, at **column 0** | `Album integrated loudness (R128): %.1f LUFS`, `Album loudness range (R128): %.1f LU (%.1f to %.1f LUFS)`, `Album sample peak level: %.1f dBFS`, `Album true peak level: %.1f dBFS` (`cyanrip_encode.c:847-853`) | **cyanrip (fork, round 8+)** | Fork's **P2 — stable log lines (the API)** |

Both fill the same four `album_loudness` keys — `integrated_lufs`, `lra_lu`,
`sample_peak_dbfs`, `true_peak_dbfs`, all `str`, dBFS for both peaks. Three
properties of how they are read:

- **The P2 rows win, and the precedence is recorded per key rather than
  positional.** Every artifact prints the `ebur128` block first, so an overwrite
  would happen to be right; `_Disc.record_album_loudness(..., stable=)` makes it
  right on purpose, so a build that reordered the two blocks could not invert it.
- **The `ebur128` scrape stays as a fallback and is still load-bearing.** Stock
  `cyanrip 0.9.3` — what a user is left on when the wizard's fork build fails,
  reported as "you are on stock cyanrip"; the successful path builds the fork at
  `FORK_PIN` (`deps/fork_source.py`) — and every
  fork build before round 8 print it and none of the four rows. Both cases are
  committed logs (`output_reference/cyanrip_flac/…` and
  `output_reference/cyanrip_fork_flac/…`), so this is measured, not assumed.
- **The `(R128)` qualifier is not decoration.** An unqualified
  `Album integrated loudness:` would collide with libavfilter's own unqualified
  heading in the same log; the fork added the qualifier for exactly that reason.
- **Range, not snapshot:** the rows exist from the fork's round-8 builds onward.
  `output_reference/cyanrip_fork_flac/cyanrip_fork_police_classics.log` is a fork
  log *without* them, which is why the fallback cannot be deleted.

**Lines cyanrip prints that we knowingly do NOT parse.** Recorded because the
alternative is what actually kept happening: a row went unparsed by accident and
nobody could tell the difference (the overread mode twice, the `Gaps:` block, the
`Accurip 450` variant). The disc-level rows the parser recognises are now an
enumerable table in `parsers/cyanrip_log.py`, and everything at column 0 that the
table does not claim must appear in that module's `_IGNORED_DISC_LINES`
allow-list **with a reason** — `tests/test_parsers_cyanrip_log.py` walks the
committed real logs and fails otherwise, so a row a future cyanrip adds shows up
as a red test rather than a silent omission. Deliberately skipped today:
`System device:` (the device node — the GUI already knows it), `Overread:` /
`Underread:` (the *frame count*, which is derived from the read offset and is
printed identically whether or not the drive read the lead-in/lead-out — only
`Overread mode:` answers EAC's question), `AccurateRip:` (whether the *disc* was
in the database; the per-track lines and the finish summary carry the verdict),
the `Tracks:` / `Summary:` section markers, and — added 2026-08-21 in the same
pass as the album loudness rows above — the two pre-log replay delimiters
(`--- output before this log was opened ---` / `--- end of pre-log output ---`),
`Opening drive...`, libcdio's `Checking <path> for cdrom...` and
`Stopping, ripping incomplete!` (the `Rip completed:` row carries that verdict,
and `ripper_messages` is what surfaces the sentence). Those five were being
dropped **with no allow-list entry** in 16 committed logs, invisible to the sweep
because its corpus was only `output_reference/cyanrip_*/*.log`; the round-12
artifacts under `docs/handshake/inbound/artifacts/` are now swept too.
**Candidates that arguably should
become `RippingInfo` / `TrackResult` fields** (each needs a new field, so it is a
deliberate change, not a silent one): `HDCD decoding:` — an enabled HDCD decode
*alters samples*, so it bears directly on "is this a bit-perfect copy";
`Tracks to rip:` — anything but `all` means the album on disk is incomplete;
`Frame retries:` — the rip-effort setting EAC reports as part of its read mode;
`Album Art:`; and `Disc tracks:` (the disc's track total, so "did we get them
all?" is answerable from the log alone).

**GRADUATED 2026-07-31 — `Appended:    N frames of silence`.** It was listed above
as the strongest of those candidates and is now parsed into
`TrackResult.appended_silence_frames`: printed on the last track of both committed
reference rips, it names the track whose final frames are **fabricated silence
rather than disc audio** — the per-track consequence of overread being off, and an
archival-fidelity statement rather than a rip *setting*. It is surfaced as an
`Appended silence    :` line in the EAC-layout log's **status report**, beside the
read-stability caveat: EAC has no such row, and the per-track blocks are the
section that gets diffed line-by-line against a real EAC log. Note it never
appeared in `_IGNORED_DISC_LINES` — that allow-list is for **column-0** rows, and
this one is indented; graduating an indented row means adding it to
`_INDENTED_LINE_PATTERNS` and to the `must_read` set in
`tests/test_parsers_cyanrip_log.py`. Two enumerations, one habit: write the
decision down.

**Cache handling — attempted by cyanrip, measured by `cd-paranoia -A` (KDD-29).**
cyanrip has no cache-defeat flag and emits no cache-defeat verdict in its log.
Its engine, **libcdio-paranoia**, *attempts* cache defeat on every rip (readahead
cache-exhaustion reads, plus FUA where the drive advertises support) — best-effort
and drive-dependent, with no runtime signal in cyanrip's output. So cyanrip's log
alone yields `(unknown)`. We now obtain a *measured* verdict separately with the
standalone **`cd-paranoia -A`** self-test (see the cd-paranoia contract below) and
fold it into `RippingInfo.defeat_audio_cache`. The honesty rule is unchanged
(PLANNING.md KDD-25): `eac_log_export.py`'s `Defeat audio cache` line renders the
measured `Yes`/`No` when we have one, and `(unknown)` otherwise — **never a
fabricated `Yes`**. The independent correctness guarantee (AccurateRip/CTDB
consensus + `-Z N` secure re-reads) still stands on its own.

### ⚠️ Argument RANGE constraints cyanrip enforces — violating one kills the rip

Not every contract is about syntax. cyanrip **validates some argument values
against the disc** and exits rather than degrading, so an out-of-range value is
not a cosmetic problem — it is a total rip failure before any audio is read.

| Flag | Constraint | What cyanrip does when violated |
|---|---|---|
| `-t N=…` | `1 <= N <= disc tracks` | `Invalid track number N, list has M tracks!` → **exit 1, nothing ripped** |
| `-l N,…` | `1 <= N <= disc tracks` | `Invalid rip index N, list has M tracks!` → exit 1 |
| `-P N` | `0 <= N <= max` | `Invalid paranoia level …` → exit 1 |
| `-m N` | one of `250, 500, 1200, -1` | `Invalid max coverart size …` → exit 1 |
| `-c N/M` | positive ints | `Invalid discnumber` / `Invalid totaldiscs` → exit 1 |
| `-p N=…` | valid track idx + known action | `Invalid track idx for pregap` / `Invalid pregap action` → exit 1 |
| `-J` | never together with `-I` | exit 1 |

**Measured, not read from docs:** the `-t` row cost a real rip on the rig
(2026-08-02). Disc 1 of a 4-disc set has 16 tracks; the MusicBrainz medium we
used listed 18; we passed `-t 17=` and `-t 18=`; cyanrip refused the whole rip
in two seconds. Guarded now in `_metadata_args` and pinned by
`tests/test_dependency_arg_contract.py`.

**The rule this implies for any new flag:** if a value is derived from
*anything other than the disc we are about to rip* — a metadata service, a
config file, a previous disc — it needs a range check against the disc before
it becomes argv. Being right *usually* is what makes this class of bug rare
enough to ship.

### `cd-paranoia` — drive cache-defeat probe (optional; KDD-29)

Adapter: `adapters/cache_probe.py`. Routed like cyanrip — the host-exported
`~/.local/bin/cd-paranoia` (libcdio's build, the same read engine cyanrip links),
run inside the `ripping` container against the mapped device (Critical Rule #3).

| Invocation | Meaning |
|---|---|
| `cd-paranoia -A -d <device>` | **Analyze-drive**: run the drive's cache/timing self-test and print a report; extract no audio. `-d` targets the specific drive (never the wrong one on a multi-drive rig). A blank device omits `-d`. Needs an audio disc in the drive. |
| `cd-paranoia --version` | Presence/version probe (`check_cdparanoia`). |

Output parsing (`parse_cache_analysis`) is **best-effort and never raises**
(parser-grade): it returns `defeat=True` only on a clear "cache managed / no
cache / drive tests OK" signal, `defeat=False` only on an explicit "cannot defeat
cache", and **`None` (unknown) otherwise** — the honesty gate, never a guessed
`Yes`. A reported cache size (sectors) is recorded as evidence. The exact signal
phrases are centralized constants, **hardware-tuned** against the first real `-A`
capture on the BDR-209D (until confirmed, the parser stays conservative). The
probe is timeout-bounded (a wedged drive can't hang the worker) and `cd-paranoia`
is already in the force-stop reader-name list (`drive_control.py`), so a hung
probe is killable via Cancel.

**Flags that exist upstream but are intentionally not passed:** cyanrip's
`-E` (force de-emphasis) exists in its CLI but Platterpus never passes it —
emphasis handling is **flag-only preservation**: we deliberately leave
pre-emphasis-encoded discs as cyanrip finds them (an archival choice, not an
oversight) rather than actively de-emphasizing. *(Overread moved out of this
list 2026-07-21: it's now the opt-in Settings "Overread" toggle → `-O` in the
table above. Note the flag-letter correction made the same day: earlier
versions of this doc called overread `-x` rather than `-O`, but `-x` did not exist in
cyanrip's getopt at all — verified against the deployed 0.9.3.1 and
upstream master **as of 2026-07-21**; the whipper-era flag really was
`-x/--force-overread`, which is likely where the mix-up came from.)*

> **⚠ `-x` EXISTS AGAIN, AND IT IS A DIFFERENT FLAG. Do not read the paragraph
> above as current** (corrected 2026-08-07). The claim *"`-x` does not exist"* was
> true when measured and went stale two weeks later: the **fork** added
> `-x` / `--cache-probe` in round 7 lap 1, at our own round-5 request, and it is
> the **drive cache probe** — it measures readback cache. It is
> **not** overread. Overread is `-O`, and `-O` is the flag **confirmed to hang the
> Pioneer BDR-209D for ~23 minutes** (2026-07-22).
>
> **⚠ And this correction needed a correction of its own (2026-08-19).** Its first
> version said the probe "costs seconds". **Measured false**, on the BDR-209D with
> fork `platterpus-fork-gddf7ac3`: `cyanrip -x -N -s 0` printed
> `Cache probe: 32 sectors, 73.5 KiB, uncached read 362.6 ms` **and then went on to
> rip the entire disc** — ETA 1h 3m, killed by the script verb's ceiling at 300 s,
> and the child could not be reaped (`exit: null`), so the drive stayed held for
> everything that followed in that session. `-s 0` is required to get that far:
> without an offset cyanrip refuses to open the drive and exits 1 in two seconds
> having measured nothing.
>
> So bare `-x` is **not a cheap probe** — it is a whole-disc rip with a measurement
> printed at the front, and treating it as a quick check costs a hardware session.
> **Answered 2026-08-25, and the answer is a flag rather than a fork change:** `-x`
> is a *modifier*, and `cyanrip -N -x -I` is the probe-only invocation — it measures
> and exits without writing audio (the fork states this in round 13 lap 5 and round
> 14 lap 1 §T3; it returned in 15.9 s with the drive alive on the BDR-209D at round
> 14 lap 16). That is §P of `src/platterpus/rig_scripts/fullacceptance.txt`, placed after
> every rip in the file because the fork could not promise the drive comes back.
> No script here runs bare `-x`.
>
> The instructive part is *how* the wrong claim got in: the 2026-08-18 correction was
> right about the flag identity (which it had measured) and guessed about the cost
> (which it had not), and both halves arrived carrying the authority of a correction.
> `CLAUDE.md`'s *did a correction get less scrutiny than a claim?*, second instance
> in two weeks — `docs/testing.md` §5.aq.
>
> Getting these two confused is a hardware hazard rather than a documentation
> nit, which is why this correction is a block quote and not an edit in place:
> anyone who reads "the previously-documented `-x`" and reaches for the overread flag `-O`
> toggle on that drive loses the session.
>
> This is `CLAUDE.md`'s *"state the range a contract claim covers, not the
> snapshot"* rule, caught in our own document rather than theirs. The original
> sentence named its evidence honestly ("verified against 0.9.3.1 and master")
> and still misled, because it was written as a fact about cyanrip rather than a
> fact about **two builds on one date** — and the binary in front of a user today
> is neither of them.
>
> | flag | what it does | who has it |
> |---|---|---|
> | `-x` / `--cache-probe` | measure the drive's readback cache (prints `Cache probe:` lines) **and then rip the whole disc** — measured 2026-08-19; needs `-s 0` or it refuses to open the drive | the **fork**, from round 7 lap 1 |
> | `-O` | overread into lead-in/lead-out | upstream + fork; **hangs the BDR-209D** |
> | `-x` / `--force-overread` | overread | **whipper only** — never cyanrip |
>
> `Cache probe:` states are deliberately distinct, none of them means "the
> cache was defeated", and they are **alternatives — exactly one is emitted**
> (arms of a switch, each `snprintf` writing the whole buffer). Nine of them, from
> the fork's generated provider contract at `cache_probe.c:232`: a range
> `%i to %i sectors (…)`; a bound `at least %i sectors, upper bound unknown (…)`;
> `no readback cache measured (uncached read %.1f ms…)`, a measurement that found
> nothing; five `unknown (<reason>)` forms, a measurement that could not be taken;
> and `not run (disc image has no drive cache)`, whose *absence* is the first sign
> the probe ran on metal. The `N sectors measured (…)` wording was **removed** by
> the fork for claiming a precision the method lacks, so a script asserts the
> field name and never one value. **`-x` first executed on a real drive on
> 2026-08-19** — never having run on any drive by anyone before that — and reported
> `32 sectors measured`. That is one drive, one build, one disc: the other states
> remain unverified, and whether 32 sectors is this drive's true cache is not
> something the probe's own output can settle.

**Non-zero exit / errors:** streamed stdout+stderr is captured line-by-line
(`RipHandle.log_lines`); a start failure raises `RipError` carrying the output.

## flac — FLAC integrity verify (`adapters/flac_verify.py`)

- **`flac --test --silent <file>`** per output FLAC — decodes and checks the
  stored MD5. Exit 0 = clean. A missing `flac` binary → result with `ran=False`
  (reported, never raised). Bounded by a timeout.

## flac — re-compression (`adapters/flac_recompress.py`, opt-in, off for cyanrip)

- **`flac -8 -e -p --verify --silent -f -o <tmp> <file>`** (then an atomic `os.replace`) — maximum-effort lossless
  re-encode. `-e` (exhaustive model search) + `-p` (qlp-coeff precision search)
  keep LPC order at 12, so they add encode time but **no decode cost**; `--verify`
  re-decodes to confirm bit-identity. cyanrip already maxes compression, so this
  is skipped for it. To revert to a plain `-8`, set `_EXTRA_FLAGS = ()`.

## flac / metaflac — CTDB decode path (`ctdb/decode.py`)

- **`flac -d -s --force-raw-format --endian=little --sign=signed -c <file>`** —
  decode a rip's FLAC to raw little-endian signed PCM on stdout for the CTDB
  whole-disc CRC. `flac` missing/failing degrades to `DecoderUnavailable`
  (a verdict, never a raise).
- **`metaflac --show-total-samples <file>`** — the per-file sample-count probe
  used to build the disc TOC from files. Same best-effort degrade.

## metaflac — tag / picture editing (`adapters/metaflac.py`)

- Read tags: **`metaflac --export-tags-to=- <file>`** (stdout `KEY=value` lines).
- Write tags: **`metaflac --remove-tag=KEY --set-tag=KEY=value … <file>`**.
- Cover art: **`metaflac --remove --block-type=PICTURE <file>`** then
  **`metaflac --import-picture-from=<image> <file>`**.
- Non-zero exit → `MetaflacError` carrying the last stderr line + full output.
  Binary is `config.metaflac_path` (default bare `metaflac`, resolved on PATH).

## ffmpeg — transcode FLAC → MP3/WavPack/WAV (`adapters/transcode.py`)

Base: **`ffmpeg -nostdin -y -i <src.flac> … -f <fmt> <tmp>`** (writes to a
`.transcode.tmp`, then atomic `os.replace`). Per format:

- **MP3:** `-map_metadata 0 -id3v2_version 3 -c:v copy -c:a libmp3lame -q:a <N> -f mp3`
  (`-q:a 0` == LAME `-V0`, best VBR; `-c:v copy` carries the embedded cover → APIC).
- **WavPack:** `-map_metadata 0 -map 0:a -c:a wavpack -f wv` — the **muxer is `wv`**,
  not `wavpack` (passing `-f wavpack` aborts ffmpeg); audio-only (its muxer rejects
  a second stream, so no embedded cover).
- **WAV:** `-map 0:a -c:a pcm_s16le -f wav` — 16-bit LE PCM, audio-only (RIFF
  carries neither cover nor tags).

**Output validation:** the runner captures ffmpeg's **stderr** and logs its tail
on any non-zero exit (so a failed transcode is diagnosable from the log file); a
per-file failure leaves the source FLAC untouched (the master is never at risk).

## musicbrainzngs — release lookup (`adapters/musicbrainz_client.py`)

- `set_useragent(app, version, contact)` once (MB requires a UA).
- `get_releases_by_discid(discid, includes=[…], cdstubs=False)` — disc ID →
  candidate releases (CD stubs excluded on every lookup).
- TOC-lookup variant: `get_releases_by_discid("-", toc=<query>, cdstubs=False)`
  — the documented `"-"` placeholder disc ID when only `toc=` is meaningful.
- `get_release_by_id(mbid, includes=[…])` — full release detail (tracks, ISRCs,
  tags for genre).
- All wrapped so `musicbrainzngs.WebServiceError`/`ResponseError` surface as our
  own error type; the adapter is the seam for this unmaintained dependency
  (Critical rule #1).

## ffmpeg — derived-file verification (`adapters/derived_verify.py`)

- **`ffmpeg -nostdin -v error -i <file> -map 0:a -f s16le -`** — decode a
  derived WavPack/WAV (and the FLAC master) to canonical CD PCM (s16le) on
  stdout and hash it, proving the derived file bit-identical to the master;
  MP3 is only checked as cleanly decodable (lossy by design — Critical
  rule #4). Watchdog timeout; never raises.

## Cover Art Archive (`adapters/cover_art.py`)

- HTTPS GET **`https://coverartarchive.org/release/{mbid}/front`** — the front
  cover image. Best-effort (a missing cover is not an error).
- HTTPS GET **`https://coverartarchive.org/release/{mbid}`** — the typed-image
  JSON manifest; Back/Booklet full-size image URLs from it are downloaded and
  saved as `back.<ext>` / `booklet-NN.<ext>`. Best-effort, size-capped, never
  fatal.

## CTDB — CUETools Database (`adapters/ctdb_client.py`)

- HTTP GET to the CTDB lookup endpoint (plain HTTP — the server serves no valid
  TLS cert; KDD-16) with params `version=3, ctdb=1, fuzzy=0,
  metadata=none, toc=<toc>`; response is MMD XML
  (`<ctdb xmlns="…mmd-1.0#"><entry …/></ctdb>`). The audio-CRC is
  **hardware-validated** (KDD-16 gate passed 2026-07-07 via `--ctdb-calibrate`),
  so a MATCH renders as **verified**; the "experimental" labelling survives in
  code only as the defensive fallback if `crc.CRC_VALIDATED` is ever re-opened —
  the verdict can only ever under-claim, never fabricate a "verified".

## Version probes — the "is it installed?" contract (`deps/checks.py`)

Separate from the working invocations above: the *presence/version* probe each
dependency answers at launch (`_run_version_command`, one call per tool). The
contract has three parts.

**1. The flag.** Not uniform, and each one is deliberate:

| Tool | Probe invocation | Notes |
|---|---|---|
| cyanrip | `cyanrip -V`, then `cyanrip --version` | **two flags, in that order** (`cyanrip_cli.VERSION_FLAGS`, the single home both this probe and the wizard's shell snippet read). 0.9.3.x has `case 'V':` and no long options; upstream's genopt replacement after 0.9.3 deleted `-V`; the fork restored it as an alias from pin `e1d800e`. The loop reports absence only when *every* flag fails — on a 0.9.4 build the first failure is expected and is not the reason |
| cd-paranoia | `cd-paranoia --version` | banner goes to **stderr** |
| metaflac | `metaflac --version` | |
| flac | `flac --version` | |
| ffmpeg | `ffmpeg -version` | single dash, unlike the GNU tools |
| Picard | `flatpak info --user org.musicbrainz.Picard` | not a version flag — a record lookup; must contain a `Version:` line |

**2. Both streams are read.** The version banner is not reliably on stdout —
`cd-paranoia` prints its to stderr — so stdout+stderr are concatenated before
parsing.

**3. A zero exit is required, and that is load-bearing.** The version parser
returns the first `N.N` in the text, and *error* text is full of numbers that
belong to other programs (podman's version in a Distrobox start failure;
`libcdio.so.19.0` in a linker error). Accepting any completed run therefore
reported a broken tool as installed *and* as meeting its minimum version — fixed
2026-07-31; a non-zero exit (including a negative one, i.e. a probe we
SIGKILLed on cancel) now means **absent**, and the exit code plus the tool's
captured output is logged.

Each tool's version-flag exit code was checked against upstream source before
that rule was made a hard failure — the evidence, so a future maintainer doesn't
have to re-derive it:

| Tool | Exit on version flag | Source evidence |
|---|---|---|
| cyanrip | **0** on every build, from three different mechanisms — say which | 0.9.3.x: `src/cyanrip_main.c` `case 'V': cyanrip_log(…); return 0;`. Stock after 0.9.3: `genopt.h:497` special-cases `-v`/`--version`, and **`-V` exits 1**. The fork from `e1d800e` — the deployed build, `d9c058c` / `0.9.4-rc2+platterpus.10` — accepts all three spellings and exits 0 |
| cd-paranoia | **0** | libcdio-paranoia `src/cd-paranoia.c`: `case 'V': fprintf(stderr, PARANOIA_VERSION); … exit(0);` |
| flac | **0** | flac `src/flac/main.c` → `do_it()`: `if(option_values.show_version) { show_version(); return 0; }` |
| metaflac | **0** | flac `src/metaflac/operations.c` → `do_operations()` prints the banner and returns success |
| ffmpeg | **0** | FFmpeg `fftools/opt_common.c`: `show_version()` returns 0 |
| flatpak | **0** when the app is installed | non-zero means "not installed", which is exactly the answer we want |

**The near-miss worth knowing about:** libcdio's *other* tools (`cd-info`,
`cd-drive`) print a perfectly good banner and then exit **100** — their shared
`print_version()` ends in `exit(EXIT_INFO)`, and `EXIT_INFO` is 100
(`libcdio/src/util.h`). `cd-paranoia` has its own `main` and does not do this,
but the convention is real, so `_run_version_command` takes an
`accept_exit_codes` allow-list. No caller passes it today. If a tool ever needs
it, allow-list **that tool's** documented code and record the evidence here —
never widen it to "any exit code", which is the bug this section exists for.

## System drive/reader control (`drive_control.py`) — force-stop / free

Kill an orphaned rip that podman won't forward a signal into (see the module's
hard-won notes). Tools resolved to absolute paths (minimal PATH under a desktop
launcher):

Ordered sequence (device-scoped first since 0.4.9 — a multi-drive box must
never have a rip on another drive killed by a broad name match, #23):

1. **`fuser -s -k <device>`** — device-scoped: kill whatever holds the drive
   node (never the GUI, which doesn't open the device).
2. **Only if that caught nothing**, the name-matched host pkills:
   `pkill -KILL -f 'whipper (cd|drive|offset|image|accurip|mblookup|rip)'`
   (an **inert whipper-era seam** — kept anchored so it can never match the
   GUI or the pkill wrapper) and
   `pkill -KILL 'cdparanoia|cd-paranoia|cdrdao|cyanrip'` — the readers, by
   process **name** (never `-f` — that would self-match). **cyanrip is its own
   reader** (libcdio, no child), so it must be killed by its own name.
3. **In-container fallback** (only if the host saw nothing at all):
   **`distrobox enter ripping -- pkill …`** — the one user-approved exception
   to Critical rule #3, scoped strictly to force-stopping a cancelled rip.
4. **`eject [<device>]`** — only *after* the holder is killed (a busy device
   ignores eject).

**Shutdown contract (0.4.9):** closing the app during a rip runs `free_drive`
(kill the reader, no eject) **synchronously** so the in-container reader can't
outlive the window — see `ui/main_window_rip.py::_stop_rip_on_shutdown`.

---

*Last updated for Platterpus v0.6.34.*
