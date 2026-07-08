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
| `-S <int>` | cap read speed (× multiplier) | only when a positive fixed speed is requested. **⚠ ABORTS the rip (`EINVAL`) on a drive that reports speed as "unchangeable"** (the Pioneer BDR-209D does) — so the ladder parses `speed_changeable` and never sends `-S` to a speed-locked drive (real-hardware finding, 2026-07-01) |
| `-l <n,n,…>` | rip only these 1-based track numbers | the per-track auto-fix re-rip (cheap targeted re-read); empty = whole disc |
| `-N` | disable cyanrip's own MusicBrainz lookup | **always** (Critical rule #5 — the GUI feeds tags via `-a`/`-t`, so cyanrip stays offline and never shows its interactive prompt) |
| `-a <k=v:k=v…>` | album-level tags | from the GUI's fetched+edited metadata |
| `-t <n=k=v:…>` | per-track tags (1-based) | from the GUI's metadata |
| `-D <scheme>` / `-F <scheme>` | directory / filename naming scheme | translated from the whipper-style template (`scheme_from_template`) |
| `-G` | disable cover-art embedding | when cover art is not being embedded |

**Tag string syntax (`-a`/`-t`) — a real trap:** the value list is
`key=value:key=value`, parsed by FFmpeg's `av_dict_parse_string`, **but** cyanrip
first runs it through `append_missing_keys()` which splits on `:` *naïvely*
(ignoring backslash/quote escapes). So a literal `:` in a value cannot be escaped
— we substitute the look-alike `∶` (U+2236) and restore the real colon in the
FLAC tags post-rip via metaflac (`_escape_meta_value` / `restore_substituted_colons`).
Other tokenizer-special chars (`\ = '`) are backslash-escaped.

**Filename / path cross-filesystem safety (the `-D`/`-F` output on disk).**
cyanrip builds each folder/file segment from the naming template with the fetched
tag values substituted in, and sanitises the characters illegal in a *path
segment* on the primary Linux target by swapping them for Unicode look-alikes:
`:` → `∶` (U+2236) and a `/` *inside a value* → `∕` (U+2215) (a `/` in the
template itself stays a real separator). On ext4/btrfs — the Bazzite target — the
only truly-illegal filename bytes are `/` and NUL, and both are covered: `/` is
mapped, and NUL can't reach here because MB values are text and the
Settings/config boundary rejects every control character
(`settings_validation._has_control_char`). So on the target filesystem the output
is always writable, and any genuinely-unwritable name (e.g. a component over the
255-**byte** ext4 limit from a very long multibyte title) fails the rip **loudly**
(captured stderr + log), never silently.

**Not sanitised — a documented cross-filesystem limitation, not a silent bug**
(naming audit, 2026-07-08). cyanrip does *not* remap the other
Windows/NTFS/exFAT-reserved characters (`< > " \ | ? *`), the reserved device
names (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`9`, `LPT1`–`9`), or trailing
dots/spaces, and those filesystems are case-insensitive (two titles differing
only in case collide). All of these are legal on Linux, so a rip to the native
library succeeds; they bite only when the output directory is on a mounted
NTFS/exFAT volume or the library is later copied to Windows/macOS. Platterpus
deliberately does **not** re-sanitise the names cyanrip produces — Critical Rule
#3 (the ripper owns naming; overriding it would duplicate cyanrip's logic and
break the Settings naming preview↔reality round-trip). If cross-FS portability is
wanted, the tracked non-overriding options are a *non-blocking* Settings warning
on a cross-FS-unsafe template and/or a user-doc note — a maintainer feature call,
not a unilateral fix.

**Info / probe flags:** `-I -N` (info-only, computes DiscID/CDDB locally, no
network — `disc_info`); `-V` (version). **cyanrip has NO offset-finder** — its
`-f` is *force-overread*, not an AccurateRip offset detector — so `find_offset`
is deliberately unimplemented (inherits `NotImplementedError`). The read offset
comes from the bundled AccurateRip drive-model list (`adapters/accuraterip_offsets.py`)
or manual entry, never from a cyanrip probe. (An earlier build ran `cyanrip -f`
and regex-scraped "offset…N", which read a default 0 and silently overrode the
correct list value — removed.)

**Expected output we parse** (`parsers/cyanrip_log.py`, `parsers/cyanrip_info.py`):
the finish log's banner (`Drive:`, `Disc tracks: N`, `Speed: default
(unchangeable)` → `speed_changeable`, offset → `read_offset`), per-track blocks (`Track N
ripped and encoded …`, `EAC CRC32:`, `Accurip v1/v2: … (accurately ripped,
confidence N)`, `(after N rips)` → `rip_count`, extraction speed/quality,
`Done; (M out of N matches …)` / `(no matches found, but hit repeat limit of N)`
→ `secure_rerip_converged`), the AccurateRip summary, album loudness, and the
`Log FUN512:` signature. cyanrip writes its own `.log` + `.cue` at the end; a
**cancelled** rip writes neither. **Note:** only `read_offset` and
`speed_changeable` are parsed off the banner — cyanrip prints **no cache
line at all**, so there is no `cache` field to parse (see the cache-handling
note below; this corrects an earlier version of this doc that implied one).

**Cache handling — attempted, not asserted.** cyanrip has no cache-defeat
flag and emits no cache-defeat verdict in its log. Its engine,
**libcdio-paranoia**, *attempts* cache defeat on every rip — readahead
cache-exhaustion reads, plus FUA (Force Unit Access) where the drive
advertises support — but this is best-effort and drive-dependent, with no
runtime signal confirming success on a given drive. We report this honestly
as "(unknown)" rather than a measured value (`eac_log_export.py`'s
`Defeat audio cache` line never renders a fabricated `Yes`); the correctness
guarantee instead comes from AccurateRip/CTDB consensus plus `-Z N` secure
re-reads, which would catch a cache-served stale read the same way they catch
any other discrepancy. See PLANNING.md KDD-25.

**Flags that exist upstream but are intentionally not passed:** cyanrip's
`-x` (force overread into the lead-out/lead-in) and `-E` (pre-emphasis
de-emphasis) both exist in cyanrip's own CLI, but Platterpus never passes
either. Emphasis handling is **flag-only preservation** — we deliberately
leave pre-emphasis-encoded discs as cyanrip finds them (an archival choice,
not an oversight) rather than actively de-emphasizing; overread control was a
whipper-era Settings toggle (`-x/--force-overread`) dropped when whipper was
removed (KDD-18) and is currently a re-openable task, not a supported knob.

**Non-zero exit / errors:** streamed stdout+stderr is captured line-by-line
(`RipHandle.log_lines`); a start failure raises `RipError` carrying the output.

## flac — FLAC integrity verify (`adapters/flac_verify.py`)

- **`flac --test --silent <file>`** per output FLAC — decodes and checks the
  stored MD5. Exit 0 = clean. A missing `flac` binary → result with `ran=False`
  (reported, never raised). Bounded by a timeout.

## flac — re-compression (`adapters/flac_recompress.py`, opt-in, off for cyanrip)

- **`flac -8 -e -p --verify [-o tmp] <file>`** — maximum-effort lossless
  re-encode. `-e` (exhaustive model search) + `-p` (qlp-coeff precision search)
  keep LPC order at 12, so they add encode time but **no decode cost**; `--verify`
  re-decodes to confirm bit-identity. cyanrip already maxes compression, so this
  is skipped for it. To revert to a plain `-8`, set `_EXTRA_FLAGS = ()`.

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
- `get_releases_by_discid(discid, includes=[…])` — TOC → candidate releases.
- `get_release_by_id(mbid, includes=[…])` — full release detail (tracks, ISRCs).
- All wrapped so `musicbrainzngs.WebServiceError`/`ResponseError` surface as our
  own error type; the adapter is the seam for this unmaintained dependency
  (Critical rule #1).

## Cover Art Archive (`adapters/cover_art.py`)

- HTTPS GET **`https://coverartarchive.org/release/{mbid}/front`** — the front
  cover image. Best-effort (a missing cover is not an error).

## CTDB — CUETools Database (`adapters/ctdb_client.py`)

- HTTP GET to the CTDB lookup endpoint (plain HTTP — the server serves no valid
  TLS cert; KDD-16) with params `version=3, ctdb=1, fuzzy=0,
  metadata=none, toc=<toc>`; response is MMD XML
  (`<ctdb xmlns="…mmd-1.0#"><entry …/></ctdb>`). A match is labelled
  **experimental** until the audio-CRC is hardware-validated (KDD-16) — it can
  only ever under-claim, never fabricate a "verified".

## System drive/reader control (`drive_control.py`) — force-stop / free

Kill an orphaned rip that podman won't forward a signal into (see the module's
hard-won notes). Tools resolved to absolute paths (minimal PATH under a desktop
launcher):

- **`pkill -KILL -f 'whipper (cd|drive|offset|image|accurip|mblookup|rip)'`** —
  the whipper CLI, anchored so it can never match the GUI or the pkill wrapper.
- **`pkill -KILL 'cdparanoia|cd-paranoia|cdrdao|cyanrip'`** — the readers, by
  process **name** (never `-f` — that would self-match). **cyanrip is its own
  reader** (libcdio, no child), so it must be killed by its own name.
- **`fuser -s -k <device>`** — name-independent catch-all for whatever holds the
  drive node (never the GUI, which doesn't open the device).
- **`eject [<device>]`** — only *after* the holder is killed (a busy device
  ignores eject).
- **In-container fallback** (only if the host pkill matched nothing):
  **`distrobox enter ripping -- pkill …`** — the one user-approved exception to
  Critical rule #3, scoped strictly to force-stopping a cancelled rip.

**Shutdown contract (0.4.9):** closing the app during a rip runs `free_drive`
(kill the reader, no eject) **synchronously** so the in-container reader can't
outlive the window — see `ui/main_window_rip.py::_stop_rip_on_shutdown`.

---

*Last updated for Platterpus v0.4.19.*
