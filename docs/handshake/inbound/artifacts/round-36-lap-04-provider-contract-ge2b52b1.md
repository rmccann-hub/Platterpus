# cyanrip provider contract

**Generated** by `tools/gen-provider-contract.py` from the source tree and the
built binary. Do not edit by hand -- regenerate. A hand-written contract goes
stale silently, which is the failure this file exists to prevent.

Build: `cyanrip 0.9.4-rc3+platterpus.26 (platterpus-fork-ge2b52b1)`

That is the build that GENERATED this file, which is always the commit
*before* the one containing it -- a generated artifact cannot carry the hash
of a commit that adds it. `--check` normalises this field for exactly that
reason; everything else in the file is compared byte for byte. **It is the
weaker provenance handle**: a build tag names a commit, not what was built.
The source anchor below is content-derived, survives committing this file,
and is the one to recompute.

**Source anchor:** `sha256/16 = 986fc5be43e14d9d` over `src/*.c` and
`src/*.h`. **Every `file:line` below refers to exactly that source.** Line
numbers move between commits, so a citation without an anchor is not
checkable -- recompute this hash before quoting one back.

**Fork identifier:** `platterpus-fork`. This is `PROJECT_FORK_ID`, and it is
**the only reliable answer to "is this the fork?"** -- it appears in the
version banner, in the first line of every logfile, and as `cyanrip.fork_id`
in the `--diagnostics` record. **Match on it. Never match on the leading version
number**, which is upstream's string copied verbatim and which upstream can
mint identically; and never on the `-g<tag>` suffix, which names a commit
rather than a build. Derived here from the banner, so it cannot drift from
the binary.

This is the provider half of the seam. Platterpus generates the consumer half
(`docs/cyanrip-consumer-contract.md`) from its parser tables. Neither side
describes behaviour it does not have.

## P1 - Inputs: every command line flag

From the binary's own `--help`, so it cannot drift from what the build accepts.


### General

| Short | Long | Meaning |
|---|---|---|
| `-h` | `--help` | Print this text |
| `-v` | `--version` | Print the version number (-V accepted as an alias) |

### Ripping options

| Short | Long | Meaning |
|---|---|---|
| `-d` | `--device` | Set device path (can be a TOC file) |
| `-s` | `--offset` | CD drive offset in samples (default: 0) |
| `-r` | `--retries` | Maximum number of retries for frames and repeated rips (default: 10) |
| `-Z` | `--repeat-rips` | Rip tracks until checksums match N times (for damaged CDs) (default: 0) |
| `-S` | `--speed` | Set drive speed (default: 0) |
| none | `--stall-secs` | Seconds a frame read must stall before reporting liveness (0 disables) (default: 10) |
| none | `--cache-probe` | Measure the drive's readback cache before ripping (costs seconds; with -I to measure without ripping) (default: false) |
| none | `--consumer` | Identify the calling program in the log (recorded verbatim, not verified) |
| none | `--diagnostics` | Write a machine-readable diagnostics record to this path (JSON) |
| none | `--prefer-disc-isrc` | Tag a track with the ISRC read from the disc, where one is, over one given with -t (default: false) |
| none | `--encoder-option` | Pass key=value to every output's encoder, as FFmpeg names its options (repeatable) |
| `-p` | `--pregap` | Track pregap handling: N=default|drop|merge|track (repeatable) |
| `-P` | `--paranoia` | Paranoia level (0..max, or 'none'/'max') |
| `-O` | `--overread` | Enable overreading into lead-in and lead-out (default: false) |
| `-H` | `--hdcd` | Enable HDCD decoding (default: false) |
| `-E` | `--force-deemphasis` | Force CD deemphasis (default: false) |
| `-W` | `--no-deemphasis` | Disable automatic CD deemphasis (default: false) |
| `-K` | `--no-replaygain` | Disable ReplayGain tagging (default: false) |
| `-X` | `--no-data-tracks` | Skip data tracks instead of ripping them to raw binaries (default: false) |

### Output options

| Short | Long | Meaning |
|---|---|---|
| `-o` | `--outputs` | Comma separated list of output formats ('help' lists all) |
| `-b` | `--bitrate` | Bitrate of lossy files in kbps (default: 256.000000) |
| `-D` | `--folder-scheme` | Directory naming scheme (default: {album}{if #releasecomment# > #0# (|releasecomment|)} [{format}]) |
| `-F` | `--track-scheme` | Track naming scheme (default: {if #totaldiscs# > #1#|disc|.}{track} - {title}) |
| `-L` | `--log-scheme` | Log file name scheme (default: {album}{if #totaldiscs# > #1# CD|disc|}) |
| `-M` | `--cue-scheme` | CUE file name scheme (default: {album}{if #totaldiscs# > #1# CD|disc|}) |
| `-l` | `--tracks` | Comma separated list of tracks to rip (default: all) |
| `-T` | `--sanitize` | Filename sanitation: simple, os_simple, unicode, os_unicode |

### Metadata options

| Short | Long | Meaning |
|---|---|---|
| `-I` | `--info` | Only print CD and track info (default: false) |
| `-J` | `--cue-only` | Only generate and print a CUE sheet, don't rip (default: false) |
| `-a` | `--album-meta` | Album metadata, key=value:key=value |
| `-t` | `--track-meta` | Track metadata as N=key=value:key=value (repeatable) |
| `-R` | `--release` | MusicBrainz release: 1-based index or ID string |
| `-c` | `--disc` | Multi-disc tag: disc/totaldiscs |
| `-C` | `--cover` | Cover art: title=path (or N=path per-track, repeatable) |
| `-N` | `--no-musicbrainz` | Disable MusicBrainz lookup (default: false) |
| `-A` | `--no-accurip` | Disable AccurateRip database query and validation (default: false) |
| `-B` | `--no-acoustid` | Disable AcoustID fingerprinting (default: false) |
| none | `--acoustid-key` | AcoustID user API key, to submit fingerprints of verified rips |
| `-U` | `--no-coverart-db` | Disable Cover art DB query and retrieval (default: false) |
| `-m` | `--cover-size` | Cover art max size: 250, 500, 1200, or -1 for original (default: -1) |
| `-G` | `--no-coverart-embed` | Disable embedding of cover art images (default: false) |

### Misc. options

| Short | Long | Meaning |
|---|---|---|
| `-Q` | `--eject` | Eject tray once successfully done (default: false) |
| `-f` | `--find-offset` | Find drive offset (requires a disc with an AccuRip entry) (default: false) |
| `-Y` | `--verify-log` | Verify a rip log's FUN512 checksum |

**46 flags total.** Notes that are not derivable from `--help`:

- `-O` is **overread**, not an options passthrough. Never repurpose it.
- `-v`, `-V` and `--version` all print the version banner and exit 0 **on
  this fork**. Across the stock line they are not interchangeable and there
  is no single spelling that works everywhere -- see P6.
- `-J` and `-I` are mutually exclusive; combining them exits 64, an argument refused.
- `-d` accepts a device path **or** a TOC/CUE/NRG image file.
- `-a`/`-t` values are `:`-separated; a literal colon must be escaped `\:`.
- `-t N=` and `-l N` are 1-based and validated against the disc's real track
  count; out of range exits 64 with a message naming both numbers.
- Multiple `-o` formats produce **one logfile and one cue per format**.

**Units that are not obvious from the line itself:**

- `Total time:` and every `duration:` is **`MM:SS.FF`, where FF is CD frames
  (1/75 s, range 0-74)** - not centiseconds and not milliseconds. There is
  **no hours field** and minutes are **not** modulo 60: a 125-minute disc
  prints `125:00.00`. Real seconds are `mm*60 + ss + ff/75`. Reading `.26` as
  hundredths is wrong by up to 0.98 s. Upstream changed this shape from
  `HH:MM:SS.mmm` between 0.9.3 and 0.9.4-rc1 (upstream PR #130), so a
  consumer that has seen both must discriminate on the colon count: three
  fields is the legacy form, two is frames.
- `Pregap length:` is in **frames**, stated in the line. For **track 1** it
  counts from the start of the disc: the 150-frame lead-in, LSN -150..-1,
  plus any span from LSN 0 to the track's start, so an ordinary disc reads
  150 and a disc with two seconds before track 1 reads 300 (round 32). The
  `Gaps:` row and the cue sheet state the span alone.
- `Sample peak level:` is a percentage of full scale **and** dBFS;
  `True peak level:` is dBFS only.
- Paranoia counters are **raw callback counts**, not rates or scores, and are
  only comparable between tracks of the same disc on the same drive.
- **Paranoia counter scope (A8).** A per-track `Paranoia status counts:`
  block covers **the final `-Z` pass for that track only**; the disc-level
  block is **cumulative across every pass the invocation performed**. They
  are therefore equal only at `-Z 0`, where there is exactly one pass -
  confirmed on real hardware by Platterpus (round 7: 22055/1600/54/468,
  summing exactly across 14 tracks). Under `-Z N` the per-track figures sum
  to **less** than the disc block by the reads the earlier passes did. A
  consumer cross-checking the two blocks must condition on `-Z`.
- **Paranoia counter denominator under `-l` (Q10).** The disc-level block
  counts only what **this invocation** read, not the whole disc. Under
  `-l 3,5` it covers tracks 3 and 5 and nothing else, and `Rip completed:`
  says `yes (2 of 14 tracks)`. The denominator is the invocation, never the
  TOC.
- **`Elapsed:` and `Extraction speed:` - what the interval covers.** Both
  are fork-only lines, so there is no upstream documentation to fall back
  on, and the interval is not derivable from the number. Read from the
  source rather than described: the clock starts at `cyanrip_main.c`'s
  `track_start_time`, **before** the `repeat_ripping:` label, and is read
  at the `end:` label. Therefore it **includes** the paranoia seek and any
  drive spin-up it triggers, the read, the filter graph, and sending PCM to
  the encoders including the flush signal; it **includes every `-Z` pass**,
  not only the final one; it **excludes** `cyanrip_finalize_encoding()`,
  which joins and muxes after the clock is read; and it **excludes any
  AccurateRip network request** - the only AccurateRip call inside the
  bracket is `crip_find_ar()`, a lookup in an already-populated table.
  `Extraction speed:` is the track's audio duration divided by that same
  `Elapsed:`, so it is **not** a drive-speed multiple and is not directly
  comparable to EAC's row of the same name, which brackets a different
  interval. Asked by Platterpus in round 8; the four sub-questions they
  posed are each answered above. **Its precision varies**: one decimal
  from 1x up, two decimals from 0.1x, three below that, so a slow read
  keeps two significant figures. Below 0.0005x it prints `0.000x`. Before
  round 30 it was one decimal throughout, and 0.033x printed `0.0x`.
- **`Track N read successfully!` / `read with errors.` - what decides the
  arm.** `read with errors.` when, **over the track's last read**, the drive
  reported an error or returned no data, **or** paranoia skipped (`SKIP`
  in that track's block, which the drive does not report), **or** `-Z` hit
  its repeat limit (`Secure re-read:  did NOT converge`), which no count
  records. So the per-track arm can say `with errors` beside `Ripping
  errors: 0`, for a track at the repeat limit. The last two count from
  round 30; before it, `read successfully!` was printed over both.
  `successfully!` does not say the audio is right: that is what
  AccurateRip reports.
- **`Ripping errors:` - what it counts.** Reads the drive failed or
  returned no data for, encoder failures, and operational errors, over
  every read of the run, **and from round 30 paranoia's skips** - the
  disc block's `SKIP:` directly above it, every `-Z` read included. When
  any skip is counted the line says how many of the count they are,
  `Ripping errors: N (including M paranoia skips)`, so **a line with no
  suffix counts no skips, whichever build wrote it**: no earlier build
  counted them. The `--diagnostics` record's `rip.ripping_errors` is the same N and
  `rip.paranoia_skips` is M. **The exit code does not follow the skips**:
  it is `1` when N less M is non-zero or the run aborted, so a rip whose
  only errors are skips prints a non-zero count and exits `0`, which no
  build before round 30 did. The progress line's `errors - N` counts the
  same things for the read in progress.

## P2 - Outputs: stable log lines (the API)

Every line below is written by `cyanrip_log()`: to stdout, and to the logfile
when the run opens one, which replays what was printed before it opened. **A
run that ends before a logfile opens prints them to stdout only**, and every
`-I`, `-J` and `-f` run is one: `-I` and `-J` skip the logfile by design, and
`-f` ends after its search, before the logfile would open
(`sc_probe_runs_open_no_logfile`). Changing the text, indentation, field order
or units of any of them is a breaking change and requires a handshake round.

| File:line | Line |
|---|---|
| `accurip.c:243` | `Disc has no audio tracks, skipping AccuRIP DB!` |
| `accurip.c:297` | `Unable to get AccuRIP DB data: missing entry!` |
| `accurip.c:305` | `Unable to get AccuRIP DB data: %s%s` |
| `accurip.c:308` | `Unable to get AccuRIP DB data: %s\n!` |
| `accurip.c:354` | `AccuRIP DB data error, got unexpected number of bytes!` |
| `acoustid.c:281` | `AcoustID submission failed: %s` |
| `acoustid.c:299` | `AcoustID: submitted %i fingerprint%s, pending import` |
| `acoustid.c:310` | `AcoustID submission failed: unexpected reply (HTTP %li)` |
| `acoustid.c:348` | `AcoustID: %i fingerprint%s saved to tags, not submitted: %s` |
| `cache_probe.c:309` | `Cache probe:    %s` |
| `coverart.c:34` | `Cover art has no packet!` |
| `coverart.c:51` | `Unable to init lavf context: %s!` |
| `coverart.c:57` | `Unable to alloc stream!` |
| `coverart.c:70` | `Couldn't open %s for writing: %s!` |
| `coverart.c:82` | `Couldn't write header: %s!` |
| `coverart.c:92` | `Error writing picture packet: %s!` |
| `coverart.c:97` | `Error writing trailer: %s!` |
| `coverart.c:192` | `Downloading %s cover art...` |
| `coverart.c:200` | `Unable to get cover art \"%s\": not found!` |
| `coverart.c:209` | `Unable to get cover art \"%s\": %s%s!` |
| `coverart.c:212` | `Unable to get cover art \"%s\": %s\n!` |
| `coverart.c:286` | `Unable to open \"%s\": %s!` |
| `coverart.c:293` | `Unable to get cover image info: %s!` |
| `coverart.c:323` | `Error demuxing cover image: %s!` |
| `coverart.c:392` | `No MusicBrainz release ID at cover art lookup, cannot search Cover Art DB!` |
| `cue_writer.c:41` | `Couldn't open path \"%s\" for writing: %s!\nInvalid folder name? Try -D <folder>.` |
| `cue_writer.c:141` | `Refusing an INDEX 00 of %i frames into a %i frame file for track %i, writing none` |
| `cyanrip_encode.c:476` | `Error creating filter source: %s!` |
| `cyanrip_encode.c:487` | `Error creating filter sink: %s!` |
| `cyanrip_encode.c:501` | `Error setting filter sample format: %s!` |
| `cyanrip_encode.c:509` | `Error setting filter channel layout: %s!` |
| `cyanrip_encode.c:518` | `Error setting filter sample rate: %s!` |
| `cyanrip_encode.c:552` | `Error initializing filter sink: %s!` |
| `cyanrip_encode.c:635` | `Error parsing filter graph: %s!` |
| `cyanrip_encode.c:641` | `Error configuring filter graph: %s!` |
| `cyanrip_encode.c:699` | `Error pushing frame to FIFO: %s!` |
| `cyanrip_encode.c:827` | `Error filtering frame: %s!` |
| `cyanrip_encode.c:943` | `Error allocating frame!` |
| `cyanrip_encode.c:955` | `Error allocating frame: %s!` |
| `cyanrip_encode.c:1049` | `Album Loudness` |
| `cyanrip_encode.c:1076` | `Album integrated loudness (R128): %.1f LUFS` |
| `cyanrip_encode.c:1078` | `Album loudness range (R128):      %.1f LU (%.1f to %.1f LUFS)` |
| `cyanrip_encode.c:1080` | `Album sample peak level:          %.1f dBFS` |
| `cyanrip_encode.c:1082` | `Album true peak level:            %.1f dBFS` |
| `cyanrip_encode.c:1097` | `Could not alloc swr context!` |
| `cyanrip_encode.c:1115` | `Could not init swr context!` |
| `cyanrip_encode.c:1259` | `Couldn't set metadata: %s!` |
| `cyanrip_encode.c:1302` | `Error while encoding: %s!` |
| `cyanrip_encode.c:1324` | `Error encoding: %s!` |
| `cyanrip_encode.c:1355` | `Error pushing packet to FIFO: %s!` |
| `cyanrip_encode.c:1362` | `Error writing packet: %s!` |
| `cyanrip_encode.c:1392` | `Error writing to file: %s!` |
| `cyanrip_encode.c:1510` | `Codec not found (not compiled in lavc?)!` |
| `cyanrip_encode.c:1519` | `Unable to init output avctx!` |
| `cyanrip_encode.c:1534` | `Could not open output codec context!` |
| `cyanrip_encode.c:1541` | `Couldn't copy codec params!` |
| `cyanrip_encode.c:1548` | `Couldn't open %s: %s! Invalid folder name? Try -D <folder>.` |
| `cyanrip_log.c:1319` | `Log FUN512: %s` |
| `cyanrip_log.c:1397` | `--- %zu earlier message(s) dropped: buffer full ---` |
| `cyanrip_log.c:59` | `%s%s:` |
| `cyanrip_log.c:62` | `%s` |
| `cyanrip_log.c:72` | `CD-TEXT:        none reported by libcdio (absent, or unreadable by this driver)` |
| `cyanrip_log.c:77` | `CD-TEXT:        present (%s, %i disc %s, %i of %i tracks tagged)` |
| `cyanrip_log.c:98` | `Cache model:    not in use (paranoia disabled)` |
| `cyanrip_log.c:128` | `Cache model:    %i sector%s (disc image, no drive cache)` |
| `cyanrip_log.c:133` | `Cache model:    %i sector%s (drive cache probed separately, see \"Cache probe:\")` |
| `cyanrip_log.c:139` | `Cache model:    %i sector%s (drive cache size not probed)` |
| `cyanrip_log.c:173` | `%sSample peak disagreement: ebur128 %.2f dBFS, direct scan %.2f dBFS (%.2f dB apart)` |
| `cyanrip_log.c:211` | `%sRead-path peak disagreement: direct scan %.2f dBFS, read-buffer scan %.2f dBFS (%.2f dB apart)` |
| `cyanrip_log.c:237` | `Read stalls:    %s` |
| `cyanrip_log.c:316` | `Encoder errors: not applicable; no %strack was encoded` |
| `cyanrip_log.c:319` | `Encoder errors: none; %i track%s encoded` |
| `cyanrip_log.c:322` | `Encoder errors: %i track%s failed (%s%s); %i track%s encoded` |
| `cyanrip_log.c:336` | `Partial files:  %i track%s (%s%s), read not completed; encoder failures: %i` |
| `cyanrip_log.c:341` | `Partial files:  %i track%s (%s%s), read not completed; encoder failures: none` |
| `cyanrip_log.c:355` | `%s%s` |
| `cyanrip_log.c:359` | `%llu` |
| `cyanrip_log.c:419` | `Pregap LSN:  %i (duration: %s)` |
| `cyanrip_log.c:421` | `Pregap length: %i frames` |
| `cyanrip_log.c:423` | `Pregap LSN:  unknown (sub-channel unreadable)` |
| `cyanrip_log.c:425` | `Pregap LSN:  unknown (sub-channel CRC mismatches)` |
| `cyanrip_log.c:427` | `Pregap LSN:  none` |
| `cyanrip_log.c:439` | `Pregap source: sub-channel (not signalled by TOC; two searches read %i and %i frames, the first is used)` |
| `cyanrip_log.c:443` | `Pregap source: sub-channel (not signalled by TOC)` |
| `cyanrip_log.c:445` | `Pregap source: lead-in` |
| `cyanrip_log.c:447` | `Pregap source: TOC` |
| `cyanrip_log.c:450` | `Prepended:   %i frames of silence` |
| `cyanrip_log.c:451` | `Start LSN:   %i` |
| `cyanrip_log.c:453` | `(with offset: %i)` |
| `cyanrip_log.c:474` | `End LSN:     %i` |
| `cyanrip_log.c:478` | `(less %i frame CD-Extra session gap, read to: %i)` |
| `cyanrip_log.c:484` | `Appended:    %i frames of silence` |
| `cyanrip_log.c:491` | `Beyond disc: %i of %i frames refused (written as silence)` |
| `cyanrip_log.c:528` | `Preemphasis:` |
| `cyanrip_log.c:530` | `none detected` |
| `cyanrip_log.c:533` | `(deemphasis forced)` |
| `cyanrip_log.c:538` | `present (subcode)` |
| `cyanrip_log.c:540` | `present (TOC)` |
| `cyanrip_log.c:543` | `(deemphasis applied)` |
| `cyanrip_log.c:559` | `Disc ISRC:     %s` |
| `cyanrip_log.c:561` | `Disc ISRC:     %s (%s)` |
| `cyanrip_log.c:568` | `Properties:` |
| `cyanrip_log.c:571` | `Data bytes:  %i (%.2f Mib)` |
| `cyanrip_log.c:574` | `Frames:      %u` |
| `cyanrip_log.c:578` | `CRC32:         %08X` |
| `cyanrip_log.c:580` | `Sector EDC:    none to check` |
| `cyanrip_log.c:582` | `Sector EDC:    %i of %i sectors mismatched` |
| `cyanrip_log.c:585` | `Sector EDC:    all %i sectors match` |
| `cyanrip_log.c:589` | `File(s):` |
| `cyanrip_log.c:603` | `Duration:    %s` |
| `cyanrip_log.c:604` | `Samples:     %zu` |
| `cyanrip_log.c:612` | `Sample peak level: %.1f%% (%.1f dBFS)` |
| `cyanrip_log.c:615` | `True peak level:   %.1f dBFS` |
| `cyanrip_log.c:636` | `Integrated loudness (R128): %.1f LUFS` |
| `cyanrip_log.c:638` | `Loudness range (R128):      %.1f LU (%.1f to %.1f LUFS)` |
| `cyanrip_log.c:648` | `Extraction speed:  %.*fx` |
| `cyanrip_log.c:650` | `Elapsed:            %.2f s` |
| `cyanrip_log.c:658` | `EAC CRC32:     %08X` |
| `cyanrip_log.c:660` | `(after %i rips)` |
| `cyanrip_log.c:667` | `Secure re-read:  converged after %i reads` |
| `cyanrip_log.c:670` | `Secure re-read:  did NOT converge after %i reads (repeat limit hit)` |
| `cyanrip_log.c:675` | `Secure re-read:  not attempted` |
| `cyanrip_log.c:679` | `Accurip:       %s` |
| `cyanrip_log.c:683` | `(max confidence: %i)` |
| `cyanrip_log.c:691` | `Accurip v1:  %08X` |
| `cyanrip_log.c:693` | `(accurately ripped, confidence %i)` |
| `cyanrip_log.c:695` | `(not found, either a new pressing, or bad rip)` |
| `cyanrip_log.c:699` | `Accurip v2:  %08X` |
| `cyanrip_log.c:711` | `Accurip 450: %08X` |
| `cyanrip_log.c:732` | `(no comparison possible, a checksum of 0 is meaningless)` |
| `cyanrip_log.c:742` | `(matches Accurip DB, confidence %i, one frame only; whole-track checksums not found)` |
| `cyanrip_log.c:754` | `(found in Accurip DB with a confidence of %i, not above %i, the threshold for a one-frame match; whole-track checksums not found)` |
| `cyanrip_log.c:758` | `(not found)` |
| `cyanrip_log.c:765` | `Metadata:` |
| `cyanrip_log.c:772` | `(not listed: out of memory)` |
| `cyanrip_log.c:783` | `%s:` |
| `cyanrip_log.c:796` | `CD-TEXT:` |
| `cyanrip_log.c:821` | `Paranoia status counts:` |
| `cyanrip_log.c:823` | `Scope:         the last of %i reads; the disc totals below sum all of them` |
| `cyanrip_log.c:827` | `none` |
| `cyanrip_log.c:850` | `Embedded cover art:\n    %s: %s` |
| `cyanrip_log.c:853` | `Embedded cover art:\n    %s: %ix%i %s` |
| `cyanrip_log.c:889` | `cyanrip %s (%s-g%s)` |
| `cyanrip_log.c:892` | `Invoked as:     %s` |
| `cyanrip_log.c:913` | `Handshake:      %s%s` |
| `cyanrip_log.c:917` | `(declared at build time, not verified by cyanrip)` |
| `cyanrip_log.c:922` | `Consumer:       %s` |
| `cyanrip_log.c:926` | `(reported by the caller, not verified by cyanrip)` |
| `cyanrip_log.c:935` | `Drive used:     error retrieving drive info` |
| `cyanrip_log.c:937` | `Drive used:     %s %s (revision %s)` |
| `cyanrip_log.c:938` | `System device:  %s` |
| `cyanrip_log.c:940` | `Device model:   %s` |
| `cyanrip_log.c:949` | `Offset:         %c%u %s` |
| `cyanrip_log.c:952` | `Underread:      %c%i %s` |
| `cyanrip_log.c:952` | `Overread:       %c%i %s` |
| `cyanrip_log.c:957` | `Underread mode: %s` |
| `cyanrip_log.c:957` | `Overread mode:  %s` |
| `cyanrip_log.c:961` | `Speed:          %ix` |
| `cyanrip_log.c:963` | `Speed:          default (%s)` |
| `cyanrip_log.c:965` | `C2 errors:      %s` |
| `cyanrip_log.c:967` | `Accurate stream: %s` |
| `cyanrip_log.c:969` | `Recordable:     %s` |
| `cyanrip_log.c:978` | `Encoder:        libavformat %i.%i.%i, libavcodec %i.%i.%i (%s)` |
| `cyanrip_log.c:983` | `Paranoia level: %s` |
| `cyanrip_log.c:987` | `Paranoia level: %i` |
| `cyanrip_log.c:1001` | `Retry limit:    %i (per frame, and per whole-track re-read)` |
| `cyanrip_log.c:1004` | `Retry limit:    %i (per whole-track re-read; %i per frame, rounded up to a multiple of 5, the only values libcdio-paranoia checks)` |
| `cyanrip_log.c:1009` | `HDCD decoding:  %s` |
| `cyanrip_log.c:1011` | `Album Art:      %s` |
| `cyanrip_log.c:1015` | `%s%s%s%s%s` |
| `cyanrip_log.c:1023` | `Outputs:` |
| `cyanrip_log.c:1029` | `Disc tracks:    %i` |
| `cyanrip_log.c:1030` | `Tracks to rip:  %s` |
| `cyanrip_log.c:1033` | `%i%s` |
| `cyanrip_log.c:1049` | `AccurateRip ID: %08x-%08x-%08x` |
| `cyanrip_log.c:1051` | `AccurateRip:    %s` |
| `cyanrip_log.c:1058` | `AcoustID:       %s` |
| `cyanrip_log.c:1062` | `AcoustID:       unsupported (built without libchromaprint)` |
| `cyanrip_log.c:1065` | `Total time:     %s` |
| `cyanrip_log.c:1144` | `Tracks ripped accurately: %i/%i` |
| `cyanrip_log.c:1146` | `Tracks matched on one frame only: %i/%i` |
| `cyanrip_log.c:1165` | `Ripping errors: %llu (including %llu paranoia skip%s)` |
| `cyanrip_log.c:1169` | `Ripping errors: %i` |
| `cyanrip_log.c:1199` | `Rip completed:  no (interrupted by %s, %i of %i tracks)` |
| `cyanrip_log.c:1202` | `Rip completed:  no (interrupted by signal %i, %i of %i tracks)` |
| `cyanrip_log.c:1220` | `Interrupted at: track %i, mid-read` |
| `cyanrip_log.c:1223` | `Interrupted at: between tracks, no read in progress` |
| `cyanrip_log.c:1237` | `Rip completed:  no (cue sheet only, %i of %i tracks)` |
| `cyanrip_log.c:1240` | `Rip completed:  no (offset search only, %i of %i tracks)` |
| `cyanrip_log.c:1243` | `Rip completed:  no (aborted, %i of %i tracks)` |
| `cyanrip_log.c:1246` | `Rip completed:  yes (%i of %i tracks)` |
| `cyanrip_log.c:1249` | `Ripping finished at %s` |
| `cyanrip_log.c:1027` | `Disc number:    %s` |
| `cyanrip_log.c:1028` | `Total discs:    %s` |
| `cyanrip_log.c:1040` | `DiscID:         %s` |
| `cyanrip_log.c:1041` | `Release ID:     %s` |
| `cyanrip_log.c:1042` | `CDDB ID:        %s` |
| `cyanrip_log.c:1043` | `Disc MCN:       %s` |
| `cyanrip_log.c:1044` | `Album:          %s` |
| `cyanrip_log.c:1045` | `Album artist:   %s` |
| `cyanrip_main.c:297` | `No device specified and unable to get default device!` |
| `cyanrip_main.c:305` | `Unable to open device: %s` |
| `cyanrip_main.c:339` | `Unable to init cddap context!` |
| `cyanrip_main.c:341` | `cdio: \"%s\"` |
| `cyanrip_main.c:353` | `Opening drive...` |
| `cyanrip_main.c:365` | `Unable to open device!` |
| `cyanrip_main.c:377` | `cdio error: %s` |
| `cyanrip_main.c:381` | `Device does not support changing speeds!` |
| `cyanrip_main.c:389` | `Unable to init paranoia!` |
| `cyanrip_main.c:441` | `Invalid number of tracks: %i!` |
| `cyanrip_main.c:477` | `CDIO returned invalid track %i end LSN` |
| `cyanrip_main.c:524` | `Track %i is data and last, but track %i is %i frames and the %i frame CD-Extra session gap does not fit; TOC left unadjusted` |
| `cyanrip_main.c:776` | `Frame read failed!` |
| `cyanrip_main.c:859` | `Loading data for track %i...` |
| `cyanrip_main.c:869` | `Stopping, offset finding incomplete!` |
| `cyanrip_main.c:878` | `Data loaded, searching for offsets...` |
| `cyanrip_main.c:887` | `Nothing found for track %i%s` |
| `cyanrip_main.c:892` | `Offset of %c%i found in track %i%s` |
| `cyanrip_main.c:897` | `Offset of %c%i confirmed (confidence: %i) in track %i%s` |
| `cyanrip_main.c:901` | `New offset of %c%i found at track %i, scrapping old offset of %c%i%s` |
| `cyanrip_main.c:935` | `No track had AccuRip entry, cannot find offset!` |
| `cyanrip_main.c:940` | `No track was long enough, unable to find drive offset!` |
| `cyanrip_main.c:943` | `Was not able to find drive offset with a radius of %i frames, trying again with a larger radius...` |
| `cyanrip_main.c:951` | `Drive offset of %c%i found (confidence: %i)!` |
| `cyanrip_main.c:1095` | `Unable to read track %i subchannel info!` |
| `cyanrip_main.c:1240` | `Error writing the -Z spool: %s!` |
| `cyanrip_main.c:1386` | `Drive media changed, stopping!` |
| `cyanrip_main.c:1402` | `Frame read failed at LSN %i!` |
| `cyanrip_main.c:1412` | `Sector EDC mismatch at LSN %i!` |
| `cyanrip_main.c:1420` | `Stopping, ripping incomplete!` |
| `cyanrip_main.c:1430` | `Error writing to \"%s\": %s!` |
| `cyanrip_main.c:1452` | `Track %i ripped with errors.` |
| `cyanrip_main.c:1454` | `Track %i ripped successfully!` |
| `cyanrip_main.c:1481` | `Track %i is data, skipping:` |
| `cyanrip_main.c:1483` | `Track %i is data:` |
| `cyanrip_main.c:1566` | `Error creating the -Z spool: %s!` |
| `cyanrip_main.c:1578` | `Error initializing fingerprinting: %s` |
| `cyanrip_main.c:1605` | `Error in decoding/sending frame: %s` |
| `cyanrip_main.c:1786` | `Done; (%i out of %i matches for current checksum %08X)` |
| `cyanrip_main.c:1818` | `Done; (repeat limit of %i read%s reached; at most %i read%s agreed; last read %08X, not kept)` |
| `cyanrip_main.c:1824` | `Done; (repeat limit of %i read%s reached; at most %i read%s agreed)` |
| `cyanrip_main.c:1831` | `Repeating ripping (%i out of %i matches for current checksum %08X)` |
| `cyanrip_main.c:1880` | `Error reading the -Z spool: %s!` |
| `cyanrip_main.c:1886` | `Error verifying the -Z spool: it does not match the read it was kept for!` |
| `cyanrip_main.c:1900` | `Error sending flush signal to encoders: %s` |
| `cyanrip_main.c:1964` | `Track %i read with errors.` |
| `cyanrip_main.c:1966` | `Track %i read successfully!` |
| `cyanrip_main.c:2119` | `Gaps:` |
| `cyanrip_main.c:2124` | `%i frame gap between lead-in and track 1 pregap, merging into pregap` |
| `cyanrip_main.c:2131` | `%i frame unmarked gap between lead-in and track 1, marking as a pregap` |
| `cyanrip_main.c:2153` | `pregap of track %i unknown (%s)` |
| `cyanrip_main.c:2170` | `%i frame pregap in track %i,` |
| `cyanrip_main.c:2177` | `unmerged` |
| `cyanrip_main.c:2179` | `merging into track %i` |
| `cyanrip_main.c:2185` | `dropping` |
| `cyanrip_main.c:2191` | `merging` |
| `cyanrip_main.c:2198` | `splitting off into a new track, number %i` |
| `cyanrip_main.c:2242` | `%i frame discontinuity between tracks %i and %i,` |
| `cyanrip_main.c:2247` | `padding track %i` |
| `cyanrip_main.c:2250` | `ignoring` |
| `cyanrip_main.c:2258` | `%i frame gap between last track and lead-out, padding track` |
| `cyanrip_main.c:2297` | `` |
| `cyanrip_main.c:2297` | `    None signalled\n` |
| `cyanrip_main.c:2448` | `Can't init %s handler!` |
| `cyanrip_main.c:2751` | `Invalid paranoia level %lli must be between 0 and %i!` |
| `cyanrip_main.c:2765` | `Invalid max coverart size %i (must be 250, 500, 1200 or -1)` |
| `cyanrip_main.c:2777` | `Invalid sanitation method %s` |
| `cyanrip_main.c:2789` | `Invalid release index %lli!` |
| `cyanrip_main.c:2804` | `Missing discnumber` |
| `cyanrip_main.c:2809` | `Invalid discnumber %lli` |
| `cyanrip_main.c:2817` | `Invalid totaldiscs %lli` |
| `cyanrip_main.c:2822` | `discnumber %i is larger than totaldiscs %i` |
| `cyanrip_main.c:2835` | `Supported output codecs:` |
| `cyanrip_main.c:2843` | `Invalid format \"%s\"` |
| `cyanrip_main.c:2848` | `Duplicated format \"%s\"` |
| `cyanrip_main.c:2863` | `Duplicated rip idx %i` |
| `cyanrip_main.c:2897` | `Missing track idx for pregap` |
| `cyanrip_main.c:2902` | `Invalid track idx for pregap: %lli` |
| `cyanrip_main.c:2909` | `Missing pregap action` |
| `cyanrip_main.c:2917` | `Invalid pregap action %s` |
| `cyanrip_main.c:2949` | `No cover art location specified for \"%s\"` |
| `cyanrip_main.c:2958` | `Invalid track idx for cover art: %lli` |
| `cyanrip_main.c:2965` | `Cover art already specified for track idx %i!` |
| `cyanrip_main.c:2977` | `Cover art \"%s\" already specified!` |
| `cyanrip_main.c:2983` | `Too many cover arts specified!` |
| `cyanrip_main.c:2993` | `Directory name scheme must contain {format} with multiple output formats!` |
| `cyanrip_main.c:2998` | `-J (only generate a CUE sheet) cannot be used with -I (only print info)!` |
| `cyanrip_main.c:3015` | `-Z %i can never converge with -r %i: it needs %lli reads to agree, and -r %i never allows that many. Use -r %lli or more!` |
| `cyanrip_main.c:3021` | `-Z %i can never converge with -r %i: it needs %lli reads to agree, more than any -r allows. Use a smaller -Z!` |
| `cyanrip_main.c:3039` | `Searching for drive offset, enabling AccuRip and disabling MusicBrainz and Cover art fetching...` |
| `cyanrip_main.c:3061` | `Invalid encoder option \"%s\", must be key=value!` |
| `cyanrip_main.c:3069` | `Unable to store encoder option \"%s\"!` |
| `cyanrip_main.c:3098` | `Invalid %s naming scheme \"%s\"!` |
| `cyanrip_main.c:3112` | `Offset is unset! To continue with an offset of 0, run with -s 0!` |
| `cyanrip_main.c:3203` | `MusicBrainz URL:\n%s` |
| `cyanrip_main.c:3260` | `Error reading album tags: %s` |
| `cyanrip_main.c:3326` | `Log(s) will be written to:` |
| `cyanrip_main.c:3334` | `CUE files will be written to:` |
| `cyanrip_main.c:3393` | `Invalid track number %i for pregap, list has %i tracks!` |
| `cyanrip_main.c:3415` | `Invalid track number %lli, list has %i tracks!` |
| `cyanrip_main.c:3429` | `Missing \"=\" in track metadata \"%s\"` |
| `cyanrip_main.c:3448` | `Error reading track tags: %s` |
| `cyanrip_main.c:3487` | `Invalid track number %i, list has %i tracks!` |
| `cyanrip_main.c:3505` | `Cover art destination(s):` |
| `cyanrip_main.c:3542` | `WARNING: tracks %i and %i resolve to the same file \"%s\", one will overwrite the other!` |
| `cyanrip_main.c:3553` | `Tracks:` |
| `cyanrip_main.c:3568` | `Track %i info:` |
| `cyanrip_main.c:3587` | `Error initializing decoder: %s` |
| `cyanrip_main.c:3596` | `Error initializing encoder: %s` |
| `cyanrip_main.c:3612` | `Error ripping: %s` |
| `cyanrip_main.c:3643` | `Error encoding: %s` |
| `cyanrip_main.c:3663` | `Invalid rip index %i, list has %i tracks!` |
| `discid.c:52` | `Disc has no audio tracks, skipping DiscID generation!` |
| `discid.c:70` | `Disc TOC is invalid, skipping DiscID generation!` |
| `discid.c:77` | `Unable to init SHA for DiscID: %s!` |
| `genopt.h:268` | `Error parsing \"%s\" as a <type> for argument \"%s\"` |
| `genopt.h:279` | `Error parsing %f for argument \"%s\": not in [%f:%f] range!` |
| `genopt.h:301` | `Error parsing %s for argument \"%s\": not in [%lli:%lli] range!` |
| `genopt.h:324` | `Error parsing %s for argument \"%s\": not in [%llu:%llu] range!` |
| `genopt.h:368` | `Error parsing value for argument \"%s\"` |
| `genopt.h:388` | `Error parsing %f for argument \"%s\": range [%f:%f]!` |
| `genopt.h:573` | `Unable to parse command line argument: %s` |
| `genopt.h:579` | `Programming error, incorrect type for: %s` |
| `genopt.h:590` | `Missing value for argument \"%s\"` |
| `genopt.h:613` | `Too many values for argument \"%s\" (at most %i)` |
| `musicbrainz.c:123` | `Invalid disc number %i, release only has %i CDs` |
| `musicbrainz.c:128` | `Got empty medium list.` |
| `musicbrainz.c:167` | `Several of the release's discs could be this one, pick one via -c!` |
| `musicbrainz.c:176` | `The release lists no discs to take the tracks from!` |
| `musicbrainz.c:179` | `None of the release's discs has %i tracks, pick one via -c!` |
| `musicbrainz.c:186` | `The release's disc has %i tracks, this one %i!` |
| `musicbrainz.c:195` | `Medium has no track list.` |
| `musicbrainz.c:272` | `MusicBrainz query failed: %s` |
| `musicbrainz.c:286` | `Retrying in %i seconds (attempt %i out of %i)...` |
| `musicbrainz.c:322` | `Found MusicBrainz release: %s - %s` |
| `musicbrainz.c:337` | `Release ID %s not found on MusicBrainz!` |
| `musicbrainz.c:344` | `Using release %s as given, its tracks matched to the disc's in order` |
| `musicbrainz.c:359` | `Could not connect to MusicBrainz.` |
| `musicbrainz.c:368` | `Missing DiscID!` |
| `musicbrainz.c:378` | `MusicBrainz lookup failed, try again later, or disable it via -N` |
| `musicbrainz.c:396` | `MusicBrainz lookup failed: DiscID has no associated releases.` |
| `musicbrainz.c:404` | `MusicBrainz lookup failed: no releases found for DiscID.` |
| `musicbrainz.c:408` | `Multiple releases found in database for DiscID %s:` |
| `musicbrainz.c:429` | `%i (ID: %s): %s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s` |
| `musicbrainz.c:443` | `Please specify which release to use by adding the -R argument with an index or ID.` |
| `musicbrainz.c:448` | `Invalid release index %i specified, only have %i releases!` |
| `musicbrainz.c:466` | `Release ID %s not found in release list for DiscID %s, looking it up` |
| `musicbrainz.c:487` | `The disc isn't on MusicBrainz yet, consider attaching it to the release via the following URL%s` |
| `musicbrainz.c:506` | `MusicBrainz lookup failed, but DiscID has a matching stub, consider verifying the data and creating a release here:` |
| `musicbrainz.c:510` | `Unable to find release info for this CD, and metadata hasn't been manually added!` |
| `musicbrainz.c:514` | `Unable to find metadata for this CD, but metadata has been manually specified, continuing.` |
| `musicbrainz.c:520` | `Please help improve the MusicBrainz DB by submitting the disc info via the following URL:` |
| `musicbrainz.c:529` | `To continue add metadata via -a or -t, or ignore via -N!` |
| `naming.c:282` | `Invalid scheme syntax, unterminated \"{\"!` |
| `naming.c:290` | `Invalid scheme syntax, \"{\" inside \"{\", tags in conditions are written as \|tag\|!` |
| `naming.c:302` | `Invalid scheme syntax, no \"#\"!` |
| `naming.c:316` | `Invalid scheme syntax, no terminating \"#\"!` |
| `naming.c:332` | `Invalid condition syntax!` |

**358 distinct stable lines.**

Field order within a block is fixed and is part of the contract. The golden
reference log in the handshake package is the authoritative example.

### P2a - Composed lines

Lines assembled into a buffer and emitted through a trailing `%s`. The
emitting call site shows a consumer nothing, so the pieces are reconstructed
here from the `snprintf` formats that build the buffer, in source order.
Segments after the first are conditional.

The buffer is either filled in the emitting function, or filled by a helper
the emitting function calls as `helper(buf, sizeof(buf), ...)` -- one hop, and
only through the helper's first parameter. `Cache probe:` is the second shape,
and until this generator could follow that hop the contract published it as a
bare `%s` with none of its wordings, in the document whose whole purpose is
that the contract cannot describe behaviour we do not have.

**`cyanrip_main.c:3471`** - reaches logfile: yes

Not derivable: the buffer is built neither by `snprintf` in this
function nor by a `helper(buf, sizeof(buf), ...)` call in it. It
emits arbitrary text - here, the generated CUE sheet echoed back to
the terminal a line at a time. **Do not pattern-match this row**; a
pattern built from its `"%s"` would match every line in the log.

**`cache_probe.c:309`** - reaches logfile: yes

Fixed prefix: `Cache probe:    `

| # | Segment |
|---|---|
| 0 | `not run (disc image has no drive cache)` |
| 1 | `unknown (out of memory)` |
| 2 | `unknown (disc too short to probe)` |
| 3 | `unknown (read failed while calibrating)` |
| 4 | `unknown (drive returned reads too fast to time)` |
| 5 | `unknown (%s at %i sector%s, before any cache hit)` |
| 6 | `no readback cache measured (uncached read %.1f ms%s)` |
| 7 | `%i to %i sectors (%.1f to %.1f KiB, uncached read %.1f ms%s)` |
| 8 | `at least %i sectors, upper bound unknown (%.1f KiB or more, %s, uncached read %.1f ms%s)` |

**These segments ALTERNATE - exactly one is emitted.** Every
write above targets the whole buffer (`snprintf(buf, ...)`),
which writes from the start and NUL-terminates, so each
replaces the last rather than extending it. **Match them as
alternatives, never as a concatenation.**

## P3 - Unstable wording, and stdout-only routing

**This section answers two independent questions, and a row can be here for
either.** Conflating them is what put `cyanrip_encode.c` and two other rows in
both P3 and P5 and made the membership look contradictory (Platterpus, round 5
A2):

- **Unstable wording** - the text may be reworded without a handshake round.
  Do not depend on the exact string.
- **not directly** - the call passes no context, so it never writes to a
  logfile itself. It is still buffered: anything said *before* the logfile is
  opened is replayed into it, delimited by
  `--- output before this log was opened ---` and `--- end of pre-log output ---`,
  after the header block. Anything said *after* it is opened reaches stdout
  only. Which of the two a given row is depends on when it runs, and that is
  not derivable from the call site - **it needs a run to settle**.

**Appearing here does not mean a line is harmless.** A line can be
stdout-only *and* a failure diagnostic; those rows are also in P5, and P5 is
the authority on whether something is reachable on a failure path. Match
P5 rows for error detection even when they appear here.

| File:line | Line | Reaches logfile? |
|---|---|---|
| `cyanrip_encode.c:113` | `%s folder: [%s] extension: %s%s` | **not directly** - see legend |
| `cyanrip_encode.c:164` | `Unable to set up the %s encoder to try encoder options!` | **not directly** - see legend |
| `cyanrip_encode.c:178` | `Encoder option %s refused by %s: %s` | **not directly** - see legend |
| `cyanrip_encode.c:181` | `Encoder option %s refused by %s: it has no option \"%s\"` | **not directly** - see legend |
| `cyanrip_encode.c:230` | `Encoder for %s not compiled in ffmpeg!` | **not directly** - see legend |
| `cyanrip_main.c:1127` | `\r` | **not directly** - see legend |
| `cyanrip_main.c:1187` | `%s` | **not directly** - see legend |
| `cyanrip_main.c:1894` | `Flushing encoders...` | **not directly** - see legend |
| `cyanrip_main.c:2353` | `libcdio %s: %s` | **not directly** - see legend |
| `cyanrip_main.c:2670` | `Log \"%s\" checksum valid.` | **not directly** - see legend |
| `cyanrip_main.c:2673` | `Log \"%s\" checksum mismatch, the file has been modified!` | **not directly** - see legend |
| `cyanrip_main.c:2678` | `Log \"%s\" has data after the checksum, the file has been modified!` | **not directly** - see legend |
| `cyanrip_main.c:2683` | `No FUN512 checksum found in \"%s\"!` | **not directly** - see legend |
| `cyanrip_main.c:2688` | `Couldn't read \"%s\"!` | **not directly** - see legend |
| `cyanrip_main.c:3960` | `--diagnostics given %i times; the diagnostics record goes to the last one: \"%s\"` | **not directly** - see legend |
| `genopt.h:411` | `(default: %f)` | yes |
| `genopt.h:421` | `(default: %hi)` | yes |
| `genopt.h:426` | `(default: %i)` | yes |
| `genopt.h:431` | `(default: %lli)` | yes |
| `genopt.h:436` | `(default: %hu)` | yes |
| `genopt.h:441` | `(default: %u)` | yes |
| `genopt.h:446` | `(default: %llu)` | yes |
| `genopt.h:451` | `(default: %s)` | yes |
| `genopt.h:457` | `(default: %i/%i)` | yes |
| `genopt.h:543` | `%s:` | yes |
| `genopt.h:550` | `%s%s%s%s:%*s%s` | yes |
| `stall_watchdog.c:169` | `Still reading track %i - the read for LSN %i has not returned after %llds` | **not directly** - see legend |
| `stall_watchdog.c:185` | `Still waiting: %s has not returned after %llds` | **not directly** - see legend |
| `stall_watchdog.c:249` | `%s returned after %llds` | **not directly** - see legend |
| `stall_watchdog.c:287` | `Track %i - the read for LSN %i returned after %llds` | **not directly** - see legend |

Also unstable, and **not ours**: the loudness block FFmpeg's `ebur128` filter
prints (`Integrated loudness`, `Loudness range`, `Sample peak:`, `True peak:`, ...). That wording
belongs to libavfilter and moves when FFmpeg does. Prefer the
`Sample peak level:` and `True peak level:` lines in P2, which are ours,
are gated on a completed rip, and each say which peak they report.

## P4 - Exit codes

**Derived, including the table.** Until round 12 the rows here were literal
strings in the generator -- one of them read *"1, Every failure, without
exception"* -- while the line beneath them counted the tree and found
something else. A hand-written claim inside a generated document is the exact
defect this file exists to prevent, and it shipped a contract saying the
opposite of the binary's `--verify-log` codes. Platterpus found it.

| Code | Return/exit sites | Meaning, where the source states one |
|---|---|---|
| `0` | 4 | `CRIP_LOG_EXIT_VALID` -- footer present and matching |
| `1` | 4 | `CRIP_EXIT_FAILURE` -- every failure no class below names |
| `2` | 1 | `CRIP_LOG_EXIT_MISMATCH` -- footer present, does not match: modified |
| `3` | 1 | `CRIP_LOG_EXIT_NO_CHECKSUM` -- no footer: incomplete, NOT a tamper claim |
| `4` | 1 | `CRIP_LOG_EXIT_TRAILING_DATA` -- footer present, content after it: modified |
| `5` | 1 | `CRIP_LOG_EXIT_IO_ERROR` -- unreadable: no verdict was reached |
| `64` | 36 | `CRIP_EXIT_USAGE` -- an argument refused, or a flag this build lacks (EX_USAGE) |
| `74` | 6 | `CRIP_EXIT_IOERR` -- the disc or drive failed: no device, unopenable, TOC unreadable, medium changed (EX_IOERR) |
| `128 + quit_signal` | 1 | `CRIP_EXIT_SIGNAL_BASE` -- plus N: a run stopped by signal N, after its log and footer were written |

**Values resolved: `0`, `1`, `2`, `3`, `4`, `5`, `64`, `74`, `128 + quit_signal`.** Exit paths that could not be resolved: **none**.

Followed from the entry point, one hop at a time, so the scope is checkable
rather than asserted: `main()` -> `cyanrip_run()`.
Comments and string literals are blanked before scanning, because this file's
own comments discuss returns and exits and the first version of this
derivation reported three of them as real paths.

**Classes, from round 35** (our lap 7 S19, Platterpus's lap 8 S9): `64` an
argument refused or a flag this build lacks, `74` the disc or drive failed,
and `128 + N` a run signal N stopped after its footer said so; each meaning
above is the comment beside its enumerator in the source. **`1` is the
generic failure and carries no class**, and within any class the text says
which failure it was, which is why P5 exists. `--verify-log`'s values are
its own, and wire format: the enum's ORDER is an implementation detail, the
numbers are not, and they are mapped explicitly for that reason.

No non-zero exit is silent: argument parse failures print before returning,
and every other non-zero return reachable from the entry point is preceded
by a `cyanrip_log()` call.

Argument validation runs **before the logfile is opened**. Those diagnostics are
buffered and replayed into the logfile if one is later opened, so a consumer
reading the log does see them. **But a run that refuses during argument
validation opens no logfile at all**, and for that class the only artifact is
the `--diagnostics` record, which is written for those runs and is off unless
asked for. Without `--diagnostics`, a refused run leaves its reason on stdout and nowhere
else.

## P5 - Fatal and error message inventory

Every string with evidence of being reachable on a failure path. Use this to
derive error matching rather than guessing prefixes. **P5a below lists strings
this document does NOT claim are failures**; it is not part of this inventory.

**Evidence** says why each string is here, and is reported rather than folded
into a bare verdict so you can see which entries rest on the weaker test:

- `control flow` - the call is followed by one of the constructs below.
  Does not depend on how the message is worded. **They are not equivalent:**
  some end the run and some record an error and continue, and this class
  name alone cannot tell you which fired.

  | construct | reaching it |
  |---|---|
  | `return 1;` | **ends the function** non-zero |
  | `return -N;` | **ends the function** non-zero |
  | `exit(non-zero)` | **ends the process** |
  | `return AVERROR(...)` | **ends the function** with an FFmpeg error |
  | `total_error_count++` | increments a counter; **transfers no control by itself** |
  | `err = N` | sets a local flag; **transfers no control by itself** |
  | `ret = N;` | sets a local flag; **transfers no control by itself** |
  | `return CRIP_EXIT_<class>;` | **ends the function** with a P4 exit class |
  | `exit(CRIP_EXIT_<class>)` | **ends the process** with a P4 exit class |
  | `->exit_class = CRIP_EXIT_<class>;` | sets the run's exit class; **transfers no control by itself** |
  | `goto fail` | see P5a's note -- `fail:` is a label name, not a verdict |

  Derived from `fail_path()` in the generator, so this list cannot describe a
  predicate the tool does not have.

  **A CONSTRUCT IS NOT A SITE, AND THIS COLUMN DESCRIBES THE CONSTRUCT.**
  "Transfers no control by itself" does NOT mean the run continued: at
  most such sites something else in the same window does the transferring,
  and **this class reports only the first mechanism it finds**. Measured on
  this tree:

  - **13** row(s) whose evidence is a bare mechanism ALSO carry a
    `goto end` that this column does not report.
  - **2** row(s) whose evidence is a bare mechanism ALSO carry a
    `goto end_meta` that this column does not report.

  The sharpest case: **every** row whose sole evidence is
  `total_error_count++` is followed immediately by `goto end`, and `end:`
  in `cyanrip_run` is reached past the one assignment that records a
  completed rip. Those rips ABORT. Reading the row as record-and-continue
  is the opposite of what happens, and this paragraph exists because an
  earlier version of this table said exactly that.
- `wording` - the message begins like a diagnostic, but no failure exit was
  found near it. Either the exit is further away than the search window, or
  the message is a warning that does not end the run. **Treat these as
  possibly non-fatal.**
- `both` - the two agree.
- `goto end` / `wording + goto end` - the call is followed by `goto end`,
  which in `cyanrip_main.c` is *both* the ordinary success cleanup and the
  route several genuine aborts take (`Offset is unset!` leaves that way).
  It is reported as its own class because calling it fatal would file
  success lines as failures, and calling it non-fatal would drop real
  aborts. **Neither of us can settle these from the source alone; they need
  a run to classify.**

The search stops at the next `if`/`for`/`while`/`switch`, so a message is
only credited with an exit that is its own -- without that cut,
`Opening drive...` reads as fatal because the *next* statement's if-block
returns `AVERROR`. It deliberately does *not* stop at the next log call:
two arms of one if/else that both log and then converge on a single exit
must carry the same class.

| File:line | Message | Evidence | Reaches logfile? |
|---|---|---|---|
| `accurip.c:297` | `Unable to get AccuRIP DB data: missing entry!` | wording + goto end | yes |
| `accurip.c:305` | `Unable to get AccuRIP DB data: %s%s` | wording + goto end | yes |
| `accurip.c:308` | `Unable to get AccuRIP DB data: %s\n!` | wording + goto end | yes |
| `coverart.c:51` | `Unable to init lavf context: %s!` | both | yes |
| `coverart.c:57` | `Unable to alloc stream!` | both | yes |
| `coverart.c:70` | `Couldn't open %s for writing: %s!` | both | yes |
| `coverart.c:82` | `Couldn't write header: %s!` | both | yes |
| `coverart.c:92` | `Error writing picture packet: %s!` | both | yes |
| `coverart.c:97` | `Error writing trailer: %s!` | both | yes |
| `coverart.c:200` | `Unable to get cover art \"%s\": not found!` | wording + goto end | yes |
| `coverart.c:209` | `Unable to get cover art \"%s\": %s%s!` | wording + goto end | yes |
| `coverart.c:212` | `Unable to get cover art \"%s\": %s\n!` | wording + goto end | yes |
| `coverart.c:286` | `Unable to open \"%s\": %s!` | wording + goto end | yes |
| `coverart.c:293` | `Unable to get cover image info: %s!` | wording + goto end | yes |
| `coverart.c:323` | `Error demuxing cover image: %s!` | wording + goto end | yes |
| `cue_writer.c:41` | `Couldn't open path \"%s\" for writing: %s!\nInvalid folder name? Try -D <folder>.` | both | yes |
| `cyanrip_encode.c:164` | `Unable to set up the %s encoder to try encoder options!` | both | **not directly** - see legend |
| `cyanrip_encode.c:230` | `Encoder for %s not compiled in ffmpeg!` | control flow | **not directly** - see legend |
| `cyanrip_encode.c:476` | `Error creating filter source: %s!` | both | yes |
| `cyanrip_encode.c:487` | `Error creating filter sink: %s!` | both | yes |
| `cyanrip_encode.c:501` | `Error setting filter sample format: %s!` | both | yes |
| `cyanrip_encode.c:509` | `Error setting filter channel layout: %s!` | both | yes |
| `cyanrip_encode.c:518` | `Error setting filter sample rate: %s!` | both | yes |
| `cyanrip_encode.c:552` | `Error initializing filter sink: %s!` | both | yes |
| `cyanrip_encode.c:635` | `Error parsing filter graph: %s!` | both | yes |
| `cyanrip_encode.c:641` | `Error configuring filter graph: %s!` | both | yes |
| `cyanrip_encode.c:699` | `Error pushing frame to FIFO: %s!` | wording | yes |
| `cyanrip_encode.c:827` | `Error filtering frame: %s!` | both | yes |
| `cyanrip_encode.c:943` | `Error allocating frame!` | both | yes |
| `cyanrip_encode.c:955` | `Error allocating frame: %s!` | both | yes |
| `cyanrip_encode.c:1097` | `Could not alloc swr context!` | wording | yes |
| `cyanrip_encode.c:1115` | `Could not init swr context!` | wording | yes |
| `cyanrip_encode.c:1259` | `Couldn't set metadata: %s!` | both | yes |
| `cyanrip_encode.c:1302` | `Error while encoding: %s!` | both | yes |
| `cyanrip_encode.c:1324` | `Error encoding: %s!` | both | yes |
| `cyanrip_encode.c:1355` | `Error pushing packet to FIFO: %s!` | both | yes |
| `cyanrip_encode.c:1362` | `Error writing packet: %s!` | both | yes |
| `cyanrip_encode.c:1392` | `Error writing to file: %s!` | both | yes |
| `cyanrip_encode.c:1510` | `Codec not found (not compiled in lavc?)!` | control flow | yes |
| `cyanrip_encode.c:1519` | `Unable to init output avctx!` | both | yes |
| `cyanrip_encode.c:1534` | `Could not open output codec context!` | both | yes |
| `cyanrip_encode.c:1541` | `Couldn't copy codec params!` | both | yes |
| `cyanrip_encode.c:1548` | `Couldn't open %s: %s! Invalid folder name? Try -D <folder>.` | both | yes |
| `cyanrip_main.c:297` | `No device specified and unable to get default device!` | both | yes |
| `cyanrip_main.c:305` | `Unable to open device: %s` | both | yes |
| `cyanrip_main.c:339` | `Unable to init cddap context!` | wording | yes |
| `cyanrip_main.c:341` | `cdio: \"%s\"` | control flow | yes |
| `cyanrip_main.c:365` | `Unable to open device!` | both | yes |
| `cyanrip_main.c:381` | `Device does not support changing speeds!` | control flow | yes |
| `cyanrip_main.c:389` | `Unable to init paranoia!` | both | yes |
| `cyanrip_main.c:441` | `Invalid number of tracks: %i!` | both | yes |
| `cyanrip_main.c:477` | `CDIO returned invalid track %i end LSN` | control flow | yes |
| `cyanrip_main.c:769` | `cdio error: %s` | control flow | yes |
| `cyanrip_main.c:776` | `Frame read failed!` | control flow | yes |
| `cyanrip_main.c:869` | `Stopping, offset finding incomplete!` | wording + goto end | yes |
| `cyanrip_main.c:935` | `No track had AccuRip entry, cannot find offset!` | control flow | yes |
| `cyanrip_main.c:940` | `No track was long enough, unable to find drive offset!` | control flow | yes |
| `cyanrip_main.c:1095` | `Unable to read track %i subchannel info!` | wording | yes |
| `cyanrip_main.c:1240` | `Error writing the -Z spool: %s!` | wording | yes |
| `cyanrip_main.c:1386` | `Drive media changed, stopping!` | both | yes |
| `cyanrip_main.c:1402` | `Frame read failed at LSN %i!` | control flow | yes |
| `cyanrip_main.c:1412` | `Sector EDC mismatch at LSN %i!` | control flow | yes |
| `cyanrip_main.c:1420` | `Stopping, ripping incomplete!` | both | yes |
| `cyanrip_main.c:1430` | `Error writing to \"%s\": %s!` | wording + goto end | yes |
| `cyanrip_main.c:1566` | `Error creating the -Z spool: %s!` | both | yes |
| `cyanrip_main.c:1578` | `Error initializing fingerprinting: %s` | both | yes |
| `cyanrip_main.c:1605` | `Error in decoding/sending frame: %s` | both | yes |
| `cyanrip_main.c:1880` | `Error reading the -Z spool: %s!` | both | yes |
| `cyanrip_main.c:1886` | `Error verifying the -Z spool: it does not match the read it was kept for!` | both | yes |
| `cyanrip_main.c:1900` | `Error sending flush signal to encoders: %s` | wording | yes |
| `cyanrip_main.c:2688` | `Couldn't read \"%s\"!` | wording | **not directly** - see legend |
| `cyanrip_main.c:2751` | `Invalid paranoia level %lli must be between 0 and %i!` | both | yes |
| `cyanrip_main.c:2765` | `Invalid max coverart size %i (must be 250, 500, 1200 or -1)` | both | yes |
| `cyanrip_main.c:2777` | `Invalid sanitation method %s` | both | yes |
| `cyanrip_main.c:2789` | `Invalid release index %lli!` | both | yes |
| `cyanrip_main.c:2804` | `Missing discnumber` | both | yes |
| `cyanrip_main.c:2809` | `Invalid discnumber %lli` | both | yes |
| `cyanrip_main.c:2817` | `Invalid totaldiscs %lli` | both | yes |
| `cyanrip_main.c:2822` | `discnumber %i is larger than totaldiscs %i` | control flow | yes |
| `cyanrip_main.c:2843` | `Invalid format \"%s\"` | both | yes |
| `cyanrip_main.c:2848` | `Duplicated format \"%s\"` | control flow | yes |
| `cyanrip_main.c:2863` | `Duplicated rip idx %i` | control flow | yes |
| `cyanrip_main.c:2897` | `Missing track idx for pregap` | both | yes |
| `cyanrip_main.c:2902` | `Invalid track idx for pregap: %lli` | both | yes |
| `cyanrip_main.c:2909` | `Missing pregap action` | both | yes |
| `cyanrip_main.c:2917` | `Invalid pregap action %s` | both | yes |
| `cyanrip_main.c:2949` | `No cover art location specified for \"%s\"` | both | yes |
| `cyanrip_main.c:2958` | `Invalid track idx for cover art: %lli` | both | yes |
| `cyanrip_main.c:2965` | `Cover art already specified for track idx %i!` | control flow | yes |
| `cyanrip_main.c:2977` | `Cover art \"%s\" already specified!` | control flow | yes |
| `cyanrip_main.c:2983` | `Too many cover arts specified!` | control flow | yes |
| `cyanrip_main.c:2993` | `Directory name scheme must contain {format} with multiple output formats!` | control flow | yes |
| `cyanrip_main.c:2998` | `-J (only generate a CUE sheet) cannot be used with -I (only print info)!` | both | yes |
| `cyanrip_main.c:3015` | `-Z %i can never converge with -r %i: it needs %lli reads to agree, and -r %i never allows that many. Use -r %lli or more!` | control flow | yes |
| `cyanrip_main.c:3021` | `-Z %i can never converge with -r %i: it needs %lli reads to agree, more than any -r allows. Use a smaller -Z!` | control flow | yes |
| `cyanrip_main.c:3061` | `Invalid encoder option \"%s\", must be key=value!` | both | yes |
| `cyanrip_main.c:3069` | `Unable to store encoder option \"%s\"!` | both | yes |
| `cyanrip_main.c:3098` | `Invalid %s naming scheme \"%s\"!` | wording | yes |
| `cyanrip_main.c:3112` | `Offset is unset! To continue with an offset of 0, run with -s 0!` | control flow | yes |
| `cyanrip_main.c:3260` | `Error reading album tags: %s` | both | yes |
| `cyanrip_main.c:3393` | `Invalid track number %i for pregap, list has %i tracks!` | both | yes |
| `cyanrip_main.c:3415` | `Invalid track number %lli, list has %i tracks!` | both | yes |
| `cyanrip_main.c:3429` | `Missing \"=\" in track metadata \"%s\"` | both | yes |
| `cyanrip_main.c:3448` | `Error reading track tags: %s` | both | yes |
| `cyanrip_main.c:3487` | `Invalid track number %i, list has %i tracks!` | both | yes |
| `cyanrip_main.c:3587` | `Error initializing decoder: %s` | both | yes |
| `cyanrip_main.c:3596` | `Error initializing encoder: %s` | both | yes |
| `cyanrip_main.c:3612` | `Error ripping: %s` | wording + goto end | yes |
| `cyanrip_main.c:3643` | `Error encoding: %s` | wording + goto end | yes |
| `cyanrip_main.c:3663` | `Invalid rip index %i, list has %i tracks!` | both | yes |
| `diagnostics.c:895` | `Couldn't open diagnostics path \"%s\" for writing!` | wording | **not directly** - see legend |
| `discid.c:77` | `Unable to init SHA for DiscID: %s!` | wording | yes |
| `genopt.h:268` | `Error parsing \"%s\" as a <type> for argument \"%s\"` | genopt | yes |
| `genopt.h:279` | `Error parsing %f for argument \"%s\": not in [%f:%f] range!` | genopt | yes |
| `genopt.h:301` | `Error parsing %s for argument \"%s\": not in [%lli:%lli] range!` | genopt | yes |
| `genopt.h:324` | `Error parsing %s for argument \"%s\": not in [%llu:%llu] range!` | genopt | yes |
| `genopt.h:368` | `Error parsing value for argument \"%s\"` | genopt | yes |
| `genopt.h:388` | `Error parsing %f for argument \"%s\": range [%f:%f]!` | genopt | yes |
| `genopt.h:573` | `Unable to parse command line argument: %s` | genopt | yes |
| `genopt.h:579` | `Programming error, incorrect type for: %s` | genopt | yes |
| `genopt.h:590` | `Missing value for argument \"%s\"` | genopt | yes |
| `genopt.h:613` | `Too many values for argument \"%s\" (at most %i)` | genopt | yes |
| `musicbrainz.c:123` | `Invalid disc number %i, release only has %i CDs` | both | yes |
| `musicbrainz.c:128` | `Got empty medium list.` | control flow | yes |
| `musicbrainz.c:167` | `Several of the release's discs could be this one, pick one via -c!` | control flow | yes |
| `musicbrainz.c:176` | `The release lists no discs to take the tracks from!` | control flow | yes |
| `musicbrainz.c:179` | `None of the release's discs has %i tracks, pick one via -c!` | control flow | yes |
| `musicbrainz.c:337` | `Release ID %s not found on MusicBrainz!` | control flow | yes |
| `musicbrainz.c:359` | `Could not connect to MusicBrainz.` | both | yes |
| `musicbrainz.c:368` | `Missing DiscID!` | wording + goto end | yes |
| `musicbrainz.c:378` | `MusicBrainz lookup failed, try again later, or disable it via -N` | control flow | yes |
| `musicbrainz.c:443` | `Please specify which release to use by adding the -R argument with an index or ID.` | control flow | yes |
| `musicbrainz.c:448` | `Invalid release index %i specified, only have %i releases!` | both | yes |
| `musicbrainz.c:491` | `%s` | control flow | yes |
| `musicbrainz.c:506` | `MusicBrainz lookup failed, but DiscID has a matching stub, consider verifying the data and creating a release here:` | control flow | yes |
| `musicbrainz.c:510` | `Unable to find release info for this CD, and metadata hasn't been manually added!` | both | yes |
| `musicbrainz.c:514` | `Unable to find metadata for this CD, but metadata has been manually specified, continuing.` | wording | yes |
| `naming.c:282` | `Invalid scheme syntax, unterminated \"{\"!` | both | yes |
| `naming.c:290` | `Invalid scheme syntax, \"{\" inside \"{\", tags in conditions are written as \|tag\|!` | both | yes |
| `naming.c:302` | `Invalid scheme syntax, no \"#\"!` | both | yes |
| `naming.c:316` | `Invalid scheme syntax, no terminating \"#\"!` | both | yes |
| `naming.c:332` | `Invalid condition syntax!` | both | yes |

**142 distinct strings.** By evidence: 76 both, 30 control flow, 14 wording + goto end, 12 wording, 10 genopt.

The `control flow` and `both` rows total 106 strings proven reachable on a
failure path without reference to their wording. That subset is the one to
build a hard failure classifier on.

## P5a - Strings this document does NOT classify

**Not established in either direction. Do not match these as errors, and do
not treat their absence from P5 as a claim that they are harmless** -- read
them and decide. Neither of the two independent tests fired: no failure exit
within the search window, and no diagnostic wording. All that was found was a
`goto <label>`, which says where control went and nothing about why.

**A jump is not an abort, and this section exists because asserting otherwise
was acted on.** These rows sat in P5 under a heading reading *"Every string
reachable on a failure path"* purely on the strength of a `goto`. One of them
follows a converged/not-converged decision and jumps to `finalize_ripping:`,
which flushes encoders and falls into `Track %i read successfully!` -- so a
consumer classifying by this document recorded errors against a rip that
completed every track with none. (That line read `Track %i ripped and encoded
successfully!` until round 22 split the claim; logs filed before it carry the
old wording, and the point it makes is unchanged.)

**The label is not the discriminator, which is why no label is exempted
here.** `end:`, `end_meta:` and `finalize_ripping:` are all reachable by
fall-through from their function's success path; a rule separating them would
be about their names. Two of the rows below really are failures -- by a flag
set here and read further down than the search window reaches -- and that is
evidence this generator does not have, which is exactly what this section
says.

| File:line | Message | Evidence | Reaches logfile? |
|---|---|---|---|
| `accurip.c:243` | `Disc has no audio tracks, skipping AccuRIP DB!` | goto end | yes |
| `accurip.c:354` | `AccuRIP DB data error, got unexpected number of bytes!` | goto end | yes |
| `acoustid.c:281` | `AcoustID submission failed: %s` | goto end | yes |
| `acoustid.c:299` | `AcoustID: submitted %i fingerprint%s, pending import` | goto end | yes |
| `cyanrip_main.c:1786` | `Done; (%i out of %i matches for current checksum %08X)` | goto spool_encode | yes |
| `cyanrip_main.c:1818` | `Done; (repeat limit of %i read%s reached; at most %i read%s agreed; last read %08X, not kept)` | goto spool_encode | yes |
| `cyanrip_main.c:1824` | `Done; (repeat limit of %i read%s reached; at most %i read%s agreed)` | goto spool_encode | yes |
| `cyanrip_main.c:3471` | `%s` | goto end | yes |
| `musicbrainz.c:396` | `MusicBrainz lookup failed: DiscID has no associated releases.` | goto end_meta | yes |
| `musicbrainz.c:404` | `MusicBrainz lookup failed: no releases found for DiscID.` | goto end_meta | yes |
| `musicbrainz.c:466` | `Release ID %s not found in release list for DiscID %s, looking it up` | goto end_meta | yes |

**11 distinct strings.** By evidence: 5 goto end, 3 goto end_meta, 3 goto spool_encode.

## P6 - Version flags across the stock line

**STATED, NOT DERIVED.** Every other section here comes from this build or
this source tree. This one is about *upstream* builds, which this generator
cannot introspect, so it is measured by hand and cited to commits. It is
here because a consumer probing for cyanrip's version needs it and nowhere
else carries it -- and because the sentence it replaces was wrong.

P1 used to say **"prefer `--version`, it has never changed and never
will"**. That is false: `--version` did not exist before genopt. The claim
was prose, it was cited in a handshake lap as a recommendation, and a
five-minute build disproved it. The `cli` scenario pins all three spellings
**for this fork**, which is a real test whose scope is narrower than the
claim it was cited for.

Measured 2026-08-04 by building each tree and running the binary:

| build | `--version` | `-V` | `-v` |
|---|---|---|---|
| stock, pre-genopt (`442de2a^`, `meson.build` says `0.9.3`) | **exit 1** | exit 0 | **exit 1** |
| stock, genopt onward (`958e1ad`, 0.9.4-rc1) | exit 0 | **exit 1** | exit 0 |
| **this fork** (`e1d800e` onward) | exit 0 | exit 0 | exit 0 |

- Pre-genopt uses plain `getopt()` -- `#include <getopt.h>`, a short-only
  optstring containing `V`, **no long options at all** -- so `--version` is
  rejected by getopt before cyanrip sees it, on stderr, prefixed with the
  binary's own path.
- `442de2a` *"Replace getopt option parsing with genopt"* moved the flag to
  `-v`/`--version` and dropped `-V`.
- `e1d800e` restores `-V` as an alias **on this fork only**; it is not
  upstream.

**The middle row names a COMMIT, not a branch, and that is a repair.** It
used to read `master` = `958e1ad`, which was an equality rather than an
identification -- true on 2026-08-04 and false the moment our mirror of
upstream moved on. Found by asking what would break if `master` were
synced: nothing else does, and this row already had. A measurement is
about the build it ran on, and a branch tip is not a build.

The `version_matrix` scenario checks its claim against whatever `master`
points at **now**, not against `958e1ad`, so it stays meaningful across a
sync and will fail if upstream ever restores `-V`.

**`-V` and `--version` are exactly complementary across the stock line.**
No single spelling answers every stock build, so a probe over stock needs at
least two attempts by construction -- no ordering reduces it to one. Only
this fork accepts all three, and that is a property of ours, not something
to rely on for stock.

The `version_matrix` test scenario re-checks the two upstream claims from
git -- that `442de2a^` parses with `getopt` and no long options, and that
`442de2a` onward has no `-V` in its option table -- so this section fails
when the commits it cites stop saying what it says they say.

### P6a - What a rejection actually prints

**Appendix, deliberately not table cells.** Platterpus asked for the exact
text so nobody has to guess it, and asked for it kept out of the table so
it does not read like something to match on (round 7 lap 19 §C). Both
halves of that are right: **key on the exit code, not on these strings.**
They are upstream's wording, not ours, and one of them is not even
constant.

Measured 2026-08-04 by running each build:

| build, flag | stream | text |
|---|---|---|
| stock pre-genopt, `--version` | **stderr** | `<argv[0]>: invalid option -- '-'` |
| stock pre-genopt, `-v` | **stderr** | `<argv[0]>: invalid option -- 'v'` |
| stock genopt onward, `-V` | **stdout** | `Unable to parse command line argument: -V` |

Three things a consumer would otherwise have to discover the hard way:

- **The two stock builds disagree about which stream carries the**
  **diagnosis.** Pre-genopt writes to stderr, because the message is
  getopt's own; genopt writes to stdout. A probe capturing only one stream
  sees nothing at all from one of the two.
- **The pre-genopt text is not constant.** getopt prefixes `argv[0]`
  verbatim, so the line contains the path the binary was invoked by. Only
  the `: invalid option -- 'X'` suffix is stable.
- **One line each**, no usage block follows.

## P8 - The `--diagnostics` record

**DERIVED, from two sources that must agree.** The key names come from
`diagnostics.c`'s emitter, where they are spelled into the format
strings, and from `cdtext.h`'s key table, which `cdtext` writes in full
on every record; the types and nullability come from real records. Neither half
is sufficient alone, and the failure mode each one covers is the other's
blind spot: a record-only derivation lists whatever the samples happened
to exercise and calls it a schema, and a source-only derivation cannot
say which fields are ever null. Anything the two disagree about is
reported below rather than reconciled.

Platterpus asked for this in round 12 §F1 and carried it into round 13.

### P8a - The schema string, and what a consumer should do with it

This build emits `"schema": "cyanrip-diagnostics/10"` (`diagnostics.c:621`).

The number after the slash is not a version to compare, it is an
identity to recognise. A field ADDED to this record is harmless to a
reader that ignores unknown keys, and most changes have been additions,
`/8` among them; `/5` renamed one key and `/7` replaced one, each said in
`diagnostics.c` where the schema string is. So a consumer that rejects an
unrecognised schema string rejects records it could have read. Gate on
the prefix, read the keys you know, and widen the accepted set rather
than pinning one value.

### P8b - Every field

Derived from 6 records, named rather than globbed so that
a shape which stops being covered is a visible act:

- **a completed rip** -- `docs/golden-reference.diagnostics.json`
- **a rip stopped by a signal** -- `docs/sample-interrupted.diagnostics.json`
- **a run refused during argument validation** -- produced by -J -I --diagnostics
- **a run with stall reporting off (--stall-secs 0)** -- produced by -J -I --stall-secs 0 --diagnostics
- **an -I run on a disc image carrying CD-TEXT** -- produced by -d cdtext.toc -I -N -A --diagnostics
- **an -f run whose AccurateRip lookup is refused offline** -- produced by -d cdtext.toc -f -N --diagnostics

`null` in the table means **observed null in at least one record**, which
is a stronger claim than "the type allows it" and a weaker one than
"it is the only way it can be null". A field marked `--` was never
observed null by any record here; that is not a guarantee it cannot be.

| field | type | observed null | in every record |
|---|---|---|---|
| `cache_probe` | object | -- | yes |
| `cache_probe.ran` | bool | -- | yes |
| `cdtext` | object | **yes** | yes |
| `cdtext.disc` | object | -- | **no** |
| `cdtext.disc.arranger` | string | **yes** | **no** |
| `cdtext.disc.composer` | string | **yes** | **no** |
| `cdtext.disc.discid` | string | **yes** | **no** |
| `cdtext.disc.genre` | string | **yes** | **no** |
| `cdtext.disc.isrc` | *(null in every record here)* | **yes** | **no** |
| `cdtext.disc.message` | string | **yes** | **no** |
| `cdtext.disc.performer` | string | **yes** | **no** |
| `cdtext.disc.songwriter` | string | **yes** | **no** |
| `cdtext.disc.title` | string | **yes** | **no** |
| `cdtext.disc.upc_ean` | string | **yes** | **no** |
| `cdtext.language` | string | **yes** | **no** |
| `cdtext.status` | string | -- | **no** |
| `cdtext.tracks` | array | -- | **no** |
| `cdtext.tracks[]` | object | -- | **no** |
| `cdtext.tracks[].arranger` | string | **yes** | **no** |
| `cdtext.tracks[].composer` | string | **yes** | **no** |
| `cdtext.tracks[].discid` | string | **yes** | **no** |
| `cdtext.tracks[].genre` | string | **yes** | **no** |
| `cdtext.tracks[].isrc` | *(null in every record here)* | **yes** | **no** |
| `cdtext.tracks[].message` | string | **yes** | **no** |
| `cdtext.tracks[].number` | int | -- | **no** |
| `cdtext.tracks[].performer` | string | **yes** | **no** |
| `cdtext.tracks[].songwriter` | string | **yes** | **no** |
| `cdtext.tracks[].title` | string | **yes** | **no** |
| `cdtext.tracks[].upc_ean` | string | **yes** | **no** |
| `cyanrip` | object | -- | yes |
| `cyanrip.fork_id` | string | -- | yes |
| `cyanrip.handshake` | string | -- | yes |
| `cyanrip.released_build_declared` | bool | -- | yes |
| `cyanrip.vcs` | string | -- | yes |
| `cyanrip.version` | string | -- | yes |
| `exit_code` | int | -- | yes |
| `finished_at` | string | -- | yes |
| `invocation` | string | -- | yes |
| `messages` | array | -- | yes |
| `messages[]` | string | -- | yes |
| `messages_are_classified` | bool | -- | yes |
| `messages_complete_within_scope` | bool | -- | yes |
| `messages_dropped` | int | -- | yes |
| `messages_note` | string | -- | yes |
| `messages_scope` | string | -- | yes |
| `messages_tail` | array | -- | yes |
| `offset_search` | object | **yes** | yes |
| `offset_search.confidence` | *(null in every record here)* | **yes** | **no** |
| `offset_search.offset_samples` | *(null in every record here)* | **yes** | **no** |
| `offset_search.result` | string | -- | **no** |
| `read_stalls` | object | -- | yes |
| `read_stalls.count` | int | **yes** | yes |
| `read_stalls.longest_lsn` | *(null in every record here)* | **yes** | yes |
| `read_stalls.longest_seconds` | int | **yes** | yes |
| `read_stalls.longest_track` | *(null in every record here)* | **yes** | yes |
| `read_stalls.reason` | string | -- | **no** |
| `read_stalls.threshold_seconds` | int | -- | **no** |
| `read_stalls.watched` | bool | -- | yes |
| `rip` | object | **yes** | yes |
| `rip.cd_tracks` | int | -- | **no** |
| `rip.consumer` | string | **yes** | **no** |
| `rip.consumer_verified` | bool | -- | **no** |
| `rip.device` | string | -- | **no** |
| `rip.interrupted` | bool | -- | **no** |
| `rip.interrupted_by` | string | **yes** | **no** |
| `rip.offset_samples` | int | -- | **no** |
| `rip.paranoia_level` | int | -- | **no** |
| `rip.paranoia_skips` | int | -- | **no** |
| `rip.retry_limit` | int | -- | **no** |
| `rip.rip_repeats` | int | -- | **no** |
| `rip.ripping_errors` | int | -- | **no** |
| `rip.track_state` | array | -- | **no** |
| `rip.track_state[]` | object | -- | **no** |
| `rip.track_state[].audio_ripped` | bool | -- | **no** |
| `rip.track_state[].cd_track` | int | -- | **no** |
| `rip.track_state[].crcs_computed` | bool | -- | **no** |
| `rip.track_state[].data_ripped` | bool | -- | **no** |
| `rip.track_state[].deemphasis_applied` | bool | **yes** | **no** |
| `rip.track_state[].eac_crc` | string | **yes** | **no** |
| `rip.track_state[].encode_failures` | int | -- | **no** |
| `rip.track_state[].error_positions` | array | **yes** | **no** |
| `rip.track_state[].error_positions_dropped` | int | **yes** | **no** |
| `rip.track_state[].isrc_disc` | *(null in every record here)* | **yes** | **no** |
| `rip.track_state[].isrc_disc_reason` | string | -- | **no** |
| `rip.track_state[].isrc_written` | string | **yes** | **no** |
| `rip.track_state[].number` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads` | object | **yes** | **no** |
| `rip.track_state[].paranoia_all_reads.BACKOFF` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads.CACHEERR` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads.DRIFT` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads.FINISHED` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads.FIXUP_ATOM` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads.FIXUP_DROPPED` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads.FIXUP_DUPED` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads.FIXUP_EDGE` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads.OVERLAP` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads.READ` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads.READERR` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads.REPAIR` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads.SCRATCH` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads.SKIP` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads.VERIFY` | int | -- | **no** |
| `rip.track_state[].paranoia_all_reads.WROTE` | int | -- | **no** |
| `rip.track_state[].preemphasis` | string | **yes** | **no** |
| `rip.track_state[].repeats` | int | -- | **no** |
| `rip.track_state[].rip_time_us` | int | -- | **no** |
| `rip.tracks` | int | -- | **no** |
| `rip.tracks_completed` | int | -- | **no** |
| `schema` | string | -- | yes |
| `started_at` | string | -- | yes |

**Where the two derivations disagree.** Reported rather than
reconciled: a difference here is either a field no record reaches or
a field this generator cannot read out of the source, and those need
different fixes.

Emitted by `diagnostics.c` and absent from every record read here -- so reachable only under conditions none of them met:

- `calibration_us` (`diagnostics.c:696`)
- `hit_below_us` (`diagnostics.c:700`)
- `kind` (`diagnostics.c:304`)
- `lsn` (`diagnostics.c:304`)
- `miss_cost_us` (`diagnostics.c:699`)
- `reread_us` (`diagnostics.c:703`)
- `run_sectors` (`diagnostics.c:703`)
- `scored_hit` (`diagnostics.c:704`)
- `steps` (`diagnostics.c:701`)

Present in a record and not found in the source scan -- this
generator's key extraction is incomplete for these:

- `BACKOFF`
- `CACHEERR`
- `DRIFT`
- `FINISHED`
- `FIXUP_ATOM`
- `FIXUP_DROPPED`
- `FIXUP_DUPED`
- `FIXUP_EDGE`
- `OVERLAP`
- `READ`
- `READERR`
- `REPAIR`
- `SCRATCH`
- `SKIP`
- `VERIFY`
- `WROTE`

### P8c - Two absences that are deliberate

Both would be easy to add and both would be wrong, so they are stated
here rather than left to look like oversights.

- **No severity on any message.** `cyanrip_log()` carries none, so
  attaching one here would be this program guessing at its own output.
  The record says so in its own `messages_note` field rather than only
  in this document.
- **No `success` flag.** A record is written for runs that produce no
  logfile at all, which is the reason `--diagnostics` exists; a boolean verdict
  would be cyanrip making a judgement, and judgements are the
  consumer's. `exit_code`, `ripping_errors`, `interrupted` and the
  per-track `audio_ripped` are the measurements a verdict would be
  built from, and they are all present.

`exit_code` is **tri-state and `null` is not `0`.** A record written from
`atexit` before the exit status is known reports `null`, and a consumer
that coerces that to zero reports a crashed run as a clean one.

On **this fork** the genopt message is routed through `cyanrip_log()`, so
it reaches stdout, the logfile if one is open, and the `--diagnostics` record. That
is a fork property; stock does neither.

## P7 - Filename sanitisation (`-T`)

**DERIVED.** From `src/naming.c`'s substitution table and the branch that
writes each glyph, `src/cyanrip_main.c`'s option handling, and
`src/os_compat.h`'s per-OS availability macros. Nothing here is
transcribed; a hand-copied second copy of the table inside a generated
document is the failure this generator exists to prevent.

**Why it is here.** Platterpus asked for it in round 13 (`[ASK A]`,
BLOCKING). P1 documented the flag and its four spellings and documented
**none of their substitutions**, so the path a rip lands on -- a value
that crosses the seam -- was described by neither contract. The concrete
cost was a completed 14-track rip silently overwritten by a 2-track one,
because a downstream guard predicted the directory name from a two-entry
copy of this table and probed a directory that did not exist.

This section is not advice about which mode to use. It is what the
program does.

### P7a - The default, and the four spellings

**The default is `unicode`.** `cyanrip_main.c:2458` assigns `CRIP_SANITIZE_UNICODE`, and it
is the only assignment to `settings.sanitize_method` that is not
guarded by a `-T` value -- which is how this generator identifies it,
and why a second unguarded one would be reported here as ambiguous
rather than resolved to the first.

| `-T` value | enum constant | glyph field | limited to characters unavailable on the build's OS |
|---|---|---|---|
| `simple` | `CRIP_SANITIZE_SIMPLE` | `to` | no |
| `os_simple` | `CRIP_SANITIZE_OS_SIMPLE` | `to` | **yes** |
| `unicode` *(default)* | `CRIP_SANITIZE_UNICODE` | `to_u` | no |
| `os_unicode` | `CRIP_SANITIZE_OS_UNICODE` | `to_u` | **yes** |

`-T` takes a value; there is no bare form. An unrecognised value is
refused before any disc is touched -- P5 carries the string and the
`return 1` that follows it.

### P7b - The substitution table

`crip_char_replacement[]`, in source order. The order matters for one
thing only, and P7d is about that thing.

| # | character | codepoint | `simple` writes | `unicode` writes | codepoint | availability macro |
|---|---|---|---|---|---|---|
| 0 | `<` | `U+003C` | `_` | `‹` | `U+2039` | `HAS_CH_LESS` |
| 1 | `>` | `U+003E` | `_` | `›` | `U+203A` | `HAS_CH_MORE` |
| 2 | `:` | `U+003A` | `_` | `∶` | `U+2236` | `HAS_CH_COLUMN` |
| 3 | `\|` | `U+007C` | `_` | `│` | `U+2502` | `HAS_CH_OR` |
| 4 | `?` | `U+003F` | `_` | `？` | `U+FF1F` | `HAS_CH_Q` |
| 5 | `*` | `U+002A` | `_` | `∗` | `U+2217` | `HAS_CH_ANY` |
| 6 | `/` | `U+002F` | `_` | `∕` | `U+2215` | `HAS_CH_FWDSLASH` |
| 7 | `\` | `U+005C` | `_` | `⧹` | `U+29F9` | `HAS_CH_BWDSLASH` |
| 8 | `"` | `U+0022` | `'` | `“` | `U+201C` | `HAS_CH_QUOTES` |
| 9 | `"` | `U+0022` | `'` | `”` | `U+201D` | `HAS_CH_QUOTES` |

**Anything not in the `character` column is passed through unchanged**
-- no length limit, no case folding, no whitespace collapsing, no
trailing-dot handling. That is an absence, so here is what it rests on
rather than an assurance: these are every call in
`crip_bprint_sanitize()` that writes to the output buffer, enumerated
from the function body. A transformation this table does not describe
would have to appear as a call here.

| line | call | writes |
|---|---|---|
| `naming.c:187` | `av_bprint_append_data` | the input, verbatim |
| `naming.c:188` | `av_bprint_append_data` | **unclassified** -- `` |
| `naming.c:209` | `av_bprint_append_data` | the input, verbatim |
| `naming.c:214` | `av_bprint_chars` | the `simple` glyph, from the table |
| `naming.c:217` | `av_bprint_append_data` | the `unicode` glyph, from the table |

### P7c - What each mode does to each character

The two `os_` modes substitute a character **only when it is unavailable
on the build's OS**. Note which way that runs: a character being *legal*
on the target filesystem is why an `os_` mode leaves it **alone**. On any
given build an `os_` mode is therefore the **least** substituting of the
four, never the most, and `-T os_unicode` is not a way to ask for the
unicode glyphs -- it is a way to ask for fewer of them.

Availability is a **compile-time** property (P7e). `os_compat.h` has
**3 states** for these macros, so 6 columns cover the
`os_` modes: one per `#if defined()` block that sets any of them -- `HAVE_WMAIN`, `__MACH__` --
and *elsewhere*, a build in none of them. They are exclusive in
practice. `HAVE_WMAIN` is set by `src/meson.build` when the compiler
links `wmain` with `-municode`, so it means a Windows/MinGW build;
`__MACH__` is defined by the compiler on macOS. The build that
generated this document is named in the banner at the top; which
branch **your** build took is a property of your build, not of this
file.

| character | `simple` | `unicode` | `os_simple` elsewhere | `os_unicode` elsewhere | `os_simple` `HAVE_WMAIN` | `os_unicode` `HAVE_WMAIN` | `os_simple` `__MACH__` | `os_unicode` `__MACH__` |
|---|---|---|---|---|---|---|---|---|
| `<` | `_` | `‹` | unchanged | unchanged | `_` | `‹` | unchanged | unchanged |
| `>` | `_` | `›` | unchanged | unchanged | `_` | `›` | unchanged | unchanged |
| `:` | `_` | `∶` | unchanged | unchanged | `_` | `∶` | `_` | `∶` |
| `\|` | `_` | `│` | unchanged | unchanged | `_` | `│` | unchanged | unchanged |
| `?` | `_` | `？` | unchanged | unchanged | `_` | `？` | unchanged | unchanged |
| `*` | `_` | `∗` | unchanged | unchanged | `_` | `∗` | unchanged | unchanged |
| `/` † | `_` | `∕` | `_` | `∕` | `_` | `∕` | `_` | `∕` |
| `\` | `_` | `⧹` | unchanged | unchanged | `_` | `⧹` | unchanged | unchanged |
| `"` | `'` | `“` | unchanged | unchanged | `'` | `“` | unchanged | unchanged |
| `"` | `'` | `”` | unchanged | unchanged | `'` | `”` | unchanged | unchanged |

On a build in none of those blocks, **8 of the 9 distinct characters** are left
unchanged by both `os_` modes: `<`, `>`, `:`, `\|`, `?`, `*`, `\`, `"`.

On a build under `__MACH__`, **7 of the 9 distinct characters** are left
unchanged by both `os_` modes: `<`, `>`, `\|`, `?`, `*`, `\`, `"`.

Read the columns for your build before treating an `os_` mode as a
safe substitute for a plain one.

**† `/` is the exception, and it is not a property of the mode.** See
P7d.

### P7d - Two behaviours the table cannot express

Both are read from the control flow of `crip_bprint_sanitize()`, not from
the table, and both change the resulting filename. A consumer predicting
a path from metadata gets the wrong answer without them.

**1. `/` depends on where the text came from, not on the mode.**
`crip_bprint_sanitize()` takes a `sanitize_fwdslash` argument; when it is
0, a `/` is emitted verbatim -- which is how a naming scheme spells a
subdirectory. Every call site, and what each one passes:

| call site | `sanitize_fwdslash` | meaning |
|---|---|---|
| `naming.c:272` | `0` | literal text, never a tag value -- `/` is a directory separator here |
| `naming.c:393` | `origin_is_tag` | `origin_is_tag`: 1 when the token resolved to a metadata tag, 0 when it fell back to literal scheme text |
| `naming.c:413` | `origin_is_tag` | `origin_is_tag`: 1 when the token resolved to a metadata tag, 0 when it fell back to literal scheme text |
| `naming.c:495` | `0` | literal text, never a tag value -- `/` is a directory separator here |

So a `/` **inside a metadata value** is substituted, and a `/` **in the
scheme itself** creates a directory. The pass-through is checked after
the OS-availability test, so it applies in all four modes.

**2. The two quote glyphs alternate on a counter that every substituted
character advances -- not only quotes.** The table holds two rows for
`"`; which one is used is chosen by a parity flag, and that flag is
toggled by **every** character the table matches, including characters
that are then left unchanged by an `os_` mode or by the `/` pass-through.
The flag is a local, so it resets at every call -- and `process_cond()`
calls once per literal run and once per `{tag}`, which means a `{tag}`
boundary between two quotes resets the parity.

Two consequences, both observable in a filename:

- an odd number of other substitutable characters between two quotes
  flips which glyph the closing quote gets;
- the same rendered text produces different filenames depending on where
  the scheme's `{}` boundaries fall.

The `sanitize_quotes` scenario in `tests/rip_images.py` rips with each
mode and asserts the resulting names, so this section fails when the
behaviour moves.

### P7e - Availability macros, and where they come from

| macro | default | set under | value there |
|---|---|---|---|
| `HAS_CH_LESS` | `1` (`os_compat.h:109`) | `HAVE_WMAIN` | `0` (`os_compat.h:97`) |
| `HAS_CH_MORE` | `1` (`os_compat.h:112`) | `HAVE_WMAIN` | `0` (`os_compat.h:98`) |
| `HAS_CH_COLUMN` | `1` (`os_compat.h:115`) | `HAVE_WMAIN`; `__MACH__` | `0` (`os_compat.h:99`); `0` (`os_compat.h:93`) |
| `HAS_CH_OR` | `1` (`os_compat.h:118`) | `HAVE_WMAIN` | `0` (`os_compat.h:100`) |
| `HAS_CH_Q` | `1` (`os_compat.h:121`) | `HAVE_WMAIN` | `0` (`os_compat.h:101`) |
| `HAS_CH_ANY` | `1` (`os_compat.h:124`) | `HAVE_WMAIN` | `0` (`os_compat.h:102`) |
| `HAS_CH_FWDSLASH` | `0` (`os_compat.h:127`, *default should be 0 here*) | `HAVE_WMAIN` | `0` (`os_compat.h:103`) |
| `HAS_CH_BWDSLASH` | `1` (`os_compat.h:130`) | `HAVE_WMAIN` | `0` (`os_compat.h:104`) |
| `HAS_CH_QUOTES` | `1` (`os_compat.h:133`) | `HAVE_WMAIN` | `0` (`os_compat.h:105`) |

A macro appears once per row of P7b, so `HAS_CH_QUOTES` governs both
quote rows together.

