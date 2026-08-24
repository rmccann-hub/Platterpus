# cyanrip provider contract

**Generated** by `tools/gen-provider-contract.py` from the source tree and the
built binary. Do not edit by hand -- regenerate. A hand-written contract goes
stale silently, which is the failure this file exists to prevent.

Build: `cyanrip 0.9.4-rc2+platterpus.7 (platterpus-fork-ga494aa7)`

That is the build that GENERATED this file, which is always the commit
*before* the one containing it -- a generated artifact cannot carry the hash
of a commit that adds it. `--check` normalises this field for exactly that
reason; everything else in the file is compared byte for byte. **It is the
weaker provenance handle**: a build tag names a commit, not what was built.
The source anchor below is content-derived, survives committing this file,
and is the one to recompute.

**Source anchor:** `sha256/16 = 94f2b1f625e2f63d` over `src/*.c` and
`src/*.h`. **Every `file:line` below refers to exactly that source.** Line
numbers move between commits, so a citation without an anchor is not
checkable -- recompute this hash before quoting one back.

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
| `-k` | `--stall-secs` | Seconds a frame read must stall before reporting liveness (0 disables) (default: 10) |
| `-x` | `--cache-probe` | Measure the drive's readback cache before ripping (costs seconds; with -I to measure without ripping) (default: false) |
| `-u` | `--consumer` | Identify the calling program in the log (recorded verbatim, not verified) |
| `-j` | `--diagnostics` | Write a machine-readable diagnostics record to this path (JSON) |
| `-p` | `--pregap` | Track pregap handling: N=default|drop|merge|track (repeatable) |
| `-P` | `--paranoia` | Paranoia level (0..max, or 'none'/'max') |
| `-O` | `--overread` | Enable overreading into lead-in and lead-out (default: false) |
| `-H` | `--hdcd` | Enable HDCD decoding (default: false) |
| `-E` | `--force-deemphasis` | Force CD deemphasis (default: false) |
| `-W` | `--no-deemphasis` | Disable automatic CD deemphasis (default: false) |
| `-K` | `--no-replaygain` | Disable ReplayGain tagging (default: false) |

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
| `-U` | `--no-coverart-db` | Disable Cover art DB query and retrieval (default: false) |
| `-m` | `--cover-size` | Cover art max size: 250, 500, 1200, or -1 for original (default: -1) |
| `-G` | `--no-coverart-embed` | Disable embedding of cover art images (default: false) |

### Misc. options

| Short | Long | Meaning |
|---|---|---|
| `-Q` | `--eject` | Eject tray once successfully done (default: false) |
| `-f` | `--find-offset` | Find drive offset (requires a disc with an AccuRip entry) (default: false) |
| `-Y` | `--verify-log` | Verify a rip log's FUN512 checksum |

**41 flags total.** Notes that are not derivable from `--help`:

- `-O` is **overread**, not an options passthrough. Never repurpose it.
- `-v`, `-V` and `--version` all print the version banner and exit 0 **on
  this fork**. Across the stock line they are not interchangeable and there
  is no single spelling that works everywhere -- see P6.
- `-J` and `-I` are mutually exclusive; combining them exits 1.
- `-d` accepts a device path **or** a TOC/CUE/NRG image file.
- `-a`/`-t` values are `:`-separated; a literal colon must be escaped `\:`.
- `-t N=` and `-l N` are 1-based and validated against the disc's real track
  count; out of range exits 1 with a message naming both numbers.
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
- `Pregap length:` is in **frames**, stated in the line.
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
  posed are each answered above.

## P2 - Outputs: stable log lines (the API)

Every line below reaches **both stdout and the logfile**. Changing the text,
indentation, field order or units of any of them is a breaking change and
requires a handshake round.

| File:line | Line |
|---|---|
| `accurip.c:97` | `Unable to get AccuRIP DB data: missing CDDB ID!` |
| `accurip.c:129` | `Unable to get AccuRIP DB data: missing entry!` |
| `accurip.c:137` | `Unable to get AccuRIP DB data: %s%s` |
| `accurip.c:140` | `Unable to get AccuRIP DB data: %s!` |
| `accurip.c:176` | `AccuRIP DB data error, got unexpected number of bytes!` |
| `cache_probe.c:232` | `Cache probe:    %s` |
| `coverart.c:34` | `Cover art has no packet!` |
| `coverart.c:51` | `Unable to init lavf context: %s!` |
| `coverart.c:57` | `Unable to alloc stream!` |
| `coverart.c:70` | `Couldn't open %s for writing: %s!` |
| `coverart.c:82` | `Couldn't write header: %s!` |
| `coverart.c:92` | `Error writing picture packet: %s!` |
| `coverart.c:97` | `Error writing trailer: %s!` |
| `coverart.c:169` | `Downloading %s cover art...` |
| `coverart.c:177` | `Unable to get cover art \"%s\": not found!` |
| `coverart.c:186` | `Unable to get cover art \"%s\": %s%s!` |
| `coverart.c:189` | `Unable to get cover art \"%s\": %s!` |
| `coverart.c:262` | `Unable to open \"%s\": %s!` |
| `coverart.c:269` | `Unable to get cover image info: %s!` |
| `coverart.c:299` | `Error demuxing cover image: %s!` |
| `coverart.c:368` | `No MusicBrainz release ID at cover art lookup, cannot search Cover Art DB!` |
| `cue_writer.c:39` | `Couldn't open path \"%s\" for writing: %s!Invalid folder name? Try -D <folder>.` |
| `cue_writer.c:106` | `Refusing an INDEX 00 of %i frames into a %i frame file for track %i, writing none` |
| `cyanrip_encode.c:364` | `Error creating filter source: %s!` |
| `cyanrip_encode.c:375` | `Error creating filter sink: %s!` |
| `cyanrip_encode.c:389` | `Error setting filter sample format: %s!` |
| `cyanrip_encode.c:397` | `Error setting filter channel layout: %s!` |
| `cyanrip_encode.c:406` | `Error setting filter sample rate: %s!` |
| `cyanrip_encode.c:440` | `Error initializing filter sink: %s!` |
| `cyanrip_encode.c:474` | `Error parsing filter graph: %s!` |
| `cyanrip_encode.c:480` | `Error configuring filter graph: %s!` |
| `cyanrip_encode.c:541` | `Error pushing frame to FIFO: %s!` |
| `cyanrip_encode.c:614` | `Error filtering frame: %s!` |
| `cyanrip_encode.c:692` | `Error allocating frame!` |
| `cyanrip_encode.c:704` | `Error allocating frame: %s!` |
| `cyanrip_encode.c:820` | `Album Loudness` |
| `cyanrip_encode.c:847` | `Album integrated loudness (R128): %.1f LUFS` |
| `cyanrip_encode.c:849` | `Album loudness range (R128):      %.1f LU (%.1f to %.1f LUFS)` |
| `cyanrip_encode.c:851` | `Album sample peak level:          %.1f dBFS` |
| `cyanrip_encode.c:853` | `Album true peak level:            %.1f dBFS` |
| `cyanrip_encode.c:868` | `Could not alloc swr context!` |
| `cyanrip_encode.c:886` | `Could not init swr context!` |
| `cyanrip_encode.c:1061` | `Error while encoding: %s!` |
| `cyanrip_encode.c:1083` | `Error encoding: %s!` |
| `cyanrip_encode.c:1114` | `Error pushing packet to FIFO: %s!` |
| `cyanrip_encode.c:1121` | `Error writing packet: %s!` |
| `cyanrip_encode.c:1151` | `Error writing to file: %s!` |
| `cyanrip_encode.c:1274` | `Codec not found (not compiled in lavc?)!` |
| `cyanrip_encode.c:1283` | `Unable to init output avctx!` |
| `cyanrip_encode.c:1294` | `Could not open output codec context!` |
| `cyanrip_encode.c:1301` | `Couldn't copy codec params!` |
| `cyanrip_encode.c:1308` | `Couldn't open %s: %s! Invalid folder name? Try -D <folder>.` |
| `cyanrip_log.c:941` | `Log FUN512: %s` |
| `cyanrip_log.c:1019` | `--- %zu earlier message(s) dropped: buffer full ---` |
| `cyanrip_log.c:58` | `%s%s:` |
| `cyanrip_log.c:61` | `%s` |
| `cyanrip_log.c:71` | `CD-TEXT:        none reported by libcdio (absent, or unreadable by this driver)` |
| `cyanrip_log.c:76` | `CD-TEXT:        present (%s, %i disc %s, %i of %i tracks tagged)` |
| `cyanrip_log.c:97` | `Cache model:    not in use (paranoia disabled)` |
| `cyanrip_log.c:108` | `Cache model:    %i sector%s (disc image, no drive cache)` |
| `cyanrip_log.c:113` | `Cache model:    %i sector%s (drive cache size not probed)` |
| `cyanrip_log.c:147` | `%sSample peak disagreement: ebur128 %.2f dBFS, direct scan %.2f dBFS (%.2f dB apart)` |
| `cyanrip_log.c:185` | `%sRead-path peak disagreement: direct scan %.2f dBFS, read-buffer scan %.2f dBFS (%.2f dB apart)` |
| `cyanrip_log.c:211` | `Read stalls:    %s` |
| `cyanrip_log.c:222` | `%s%s` |
| `cyanrip_log.c:226` | `%lu` |
| `cyanrip_log.c:285` | `Pregap LSN:  %i (duration: %s)` |
| `cyanrip_log.c:287` | `Pregap length: %i frames` |
| `cyanrip_log.c:289` | `Pregap LSN:  unknown (sub-channel unreadable)` |
| `cyanrip_log.c:291` | `Pregap LSN:  unknown (sub-channel CRC mismatches)` |
| `cyanrip_log.c:293` | `Pregap LSN:  none` |
| `cyanrip_log.c:299` | `Pregap source: sub-channel (not signalled by TOC)` |
| `cyanrip_log.c:301` | `Pregap source: lead-in` |
| `cyanrip_log.c:303` | `Pregap source: TOC` |
| `cyanrip_log.c:306` | `Prepended:   %i frames of silence` |
| `cyanrip_log.c:307` | `Start LSN:   %i` |
| `cyanrip_log.c:309` | `(with offset: %i)` |
| `cyanrip_log.c:330` | `End LSN:     %i` |
| `cyanrip_log.c:334` | `(less %i frame CD-Extra session gap, read to: %i)` |
| `cyanrip_log.c:340` | `Appended:    %i frames of silence` |
| `cyanrip_log.c:371` | `Preemphasis:` |
| `cyanrip_log.c:373` | `none detected` |
| `cyanrip_log.c:376` | `(deemphasis forced)` |
| `cyanrip_log.c:381` | `present (subcode)` |
| `cyanrip_log.c:383` | `present (TOC)` |
| `cyanrip_log.c:386` | `(deemphasis applied)` |
| `cyanrip_log.c:391` | `Properties:` |
| `cyanrip_log.c:394` | `Data bytes:  %i (%.2f Mib)` |
| `cyanrip_log.c:397` | `Frames:      %u` |
| `cyanrip_log.c:403` | `Duration:    %s` |
| `cyanrip_log.c:404` | `Samples:     %zu` |
| `cyanrip_log.c:412` | `Sample peak level: %.1f%% (%.1f dBFS)` |
| `cyanrip_log.c:415` | `True peak level:   %.1f dBFS` |
| `cyanrip_log.c:436` | `Integrated loudness (R128): %.1f LUFS` |
| `cyanrip_log.c:438` | `Loudness range (R128):      %.1f LU (%.1f to %.1f LUFS)` |
| `cyanrip_log.c:442` | `Extraction speed:  %.1fx` |
| `cyanrip_log.c:444` | `Elapsed:            %.2f s` |
| `cyanrip_log.c:452` | `EAC CRC32:     %08X` |
| `cyanrip_log.c:454` | `(after %i rips)` |
| `cyanrip_log.c:461` | `Secure re-read:  converged after %i reads` |
| `cyanrip_log.c:464` | `Secure re-read:  did NOT converge after %i reads (repeat limit hit)` |
| `cyanrip_log.c:469` | `Secure re-read:  not attempted` |
| `cyanrip_log.c:473` | `Accurip:       %s` |
| `cyanrip_log.c:477` | `(max confidence: %i)` |
| `cyanrip_log.c:485` | `Accurip v1:  %08X` |
| `cyanrip_log.c:487` | `(accurately ripped, confidence %i)` |
| `cyanrip_log.c:489` | `(not found, either a new pressing, or bad rip)` |
| `cyanrip_log.c:493` | `Accurip v2:  %08X` |
| `cyanrip_log.c:504` | `Accurip 450: %08X` |
| `cyanrip_log.c:522` | `(no comparison possible, a checksum of 0 is meaningless)` |
| `cyanrip_log.c:524` | `(matches Accurip DB, confidence %i, track is partially accurately ripped)` |
| `cyanrip_log.c:527` | `(not found)` |
| `cyanrip_log.c:534` | `Metadata:` |
| `cyanrip_log.c:544` | `%s:` |
| `cyanrip_log.c:556` | `CD-TEXT:` |
| `cyanrip_log.c:581` | `Paranoia status counts:` |
| `cyanrip_log.c:583` | `Scope:         the last of %i reads; the disc totals below sum all of them` |
| `cyanrip_log.c:587` | `none` |
| `cyanrip_log.c:610` | `Embedded cover art:    %s: %s` |
| `cyanrip_log.c:613` | `Embedded cover art:    %s: %ix%i %s` |
| `cyanrip_log.c:617` | `File(s):` |
| `cyanrip_log.c:631` | `cyanrip %s (%s-g%s)` |
| `cyanrip_log.c:634` | `Invoked as:     %s` |
| `cyanrip_log.c:655` | `Handshake:      %s%s` |
| `cyanrip_log.c:659` | `(declared at build time, not verified by cyanrip)` |
| `cyanrip_log.c:664` | `Consumer:       %s` |
| `cyanrip_log.c:668` | `(reported by the caller, not verified by cyanrip)` |
| `cyanrip_log.c:672` | `Drive used:     error retrieving drive info` |
| `cyanrip_log.c:674` | `Drive used:     %s %s (revision %s)` |
| `cyanrip_log.c:675` | `System device:  %s` |
| `cyanrip_log.c:677` | `Device model:   %s` |
| `cyanrip_log.c:686` | `Offset:         %c%u %s` |
| `cyanrip_log.c:689` | `Underread:      %c%i %s` |
| `cyanrip_log.c:689` | `Overread:       %c%i %s` |
| `cyanrip_log.c:694` | `Underread mode: %s` |
| `cyanrip_log.c:694` | `Overread mode:  %s` |
| `cyanrip_log.c:698` | `Speed:          %ix` |
| `cyanrip_log.c:700` | `Speed:          default (%s)` |
| `cyanrip_log.c:702` | `C2 errors:      %s` |
| `cyanrip_log.c:711` | `Encoder:        libavformat %i.%i.%i, libavcodec %i.%i.%i (%s)` |
| `cyanrip_log.c:716` | `Paranoia level: %s` |
| `cyanrip_log.c:720` | `Paranoia level: %i` |
| `cyanrip_log.c:721` | `Frame retries:  %i` |
| `cyanrip_log.c:723` | `HDCD decoding:  %s` |
| `cyanrip_log.c:725` | `Album Art:      %s` |
| `cyanrip_log.c:729` | `%s%s%s%s%s` |
| `cyanrip_log.c:737` | `Outputs:` |
| `cyanrip_log.c:743` | `Disc tracks:    %i` |
| `cyanrip_log.c:744` | `Tracks to rip:  %s` |
| `cyanrip_log.c:747` | `%i%s` |
| `cyanrip_log.c:761` | `AccurateRip:    %s` |
| `cyanrip_log.c:767` | `Total time:     %s` |
| `cyanrip_log.c:812` | `Tracks ripped accurately: %i/%i` |
| `cyanrip_log.c:814` | `Tracks ripped partially accurately: %i/%i` |
| `cyanrip_log.c:824` | `Ripping errors: %i` |
| `cyanrip_log.c:847` | `Rip completed:  no (interrupted by %s, %i of %i tracks)` |
| `cyanrip_log.c:850` | `Rip completed:  no (interrupted by signal %i, %i of %i tracks)` |
| `cyanrip_log.c:868` | `Interrupted at: track %i, mid-read` |
| `cyanrip_log.c:871` | `Interrupted at: between tracks, no read in progress` |
| `cyanrip_log.c:873` | `Rip completed:  yes (%i of %i tracks)` |
| `cyanrip_log.c:876` | `Ripping finished at %s` |
| `cyanrip_log.c:741` | `Disc number:    %s` |
| `cyanrip_log.c:742` | `Total discs:    %s` |
| `cyanrip_log.c:754` | `DiscID:         %s` |
| `cyanrip_log.c:755` | `Release ID:     %s` |
| `cyanrip_log.c:756` | `CDDB ID:        %s` |
| `cyanrip_log.c:757` | `Disc MCN:       %s` |
| `cyanrip_log.c:758` | `Album:          %s` |
| `cyanrip_log.c:759` | `Album artist:   %s` |
| `cyanrip_main.c:224` | `No device specified and unable to get default device!` |
| `cyanrip_main.c:232` | `Unable to open device: %s` |
| `cyanrip_main.c:241` | `Unable to init cddap context!` |
| `cyanrip_main.c:243` | `cdio: \"%s\"` |
| `cyanrip_main.c:254` | `Opening drive...` |
| `cyanrip_main.c:266` | `Unable to open device!` |
| `cyanrip_main.c:275` | `Device does not support changing speeds!` |
| `cyanrip_main.c:283` | `cdio error: %s` |
| `cyanrip_main.c:292` | `Unable to init paranoia!` |
| `cyanrip_main.c:337` | `Invalid number of tracks: %i!` |
| `cyanrip_main.c:360` | `CDIO returned invalid track %i end LSN` |
| `cyanrip_main.c:397` | `Track %i is data and last, but track %i is %i frames and the %i frame CD-Extra session gap does not fit; TOC left unadjusted` |
| `cyanrip_main.c:549` | `Frame read failed!` |
| `cyanrip_main.c:626` | `Loading data for track %i...` |
| `cyanrip_main.c:636` | `Stopping, offset finding incomplete!` |
| `cyanrip_main.c:644` | `Data loaded, searching for offsets...` |
| `cyanrip_main.c:653` | `Nothing found for track %i%s` |
| `cyanrip_main.c:658` | `Offset of %c%i found in track %i%s` |
| `cyanrip_main.c:663` | `Offset of %c%i confirmed (confidence: %i) in track %i%s` |
| `cyanrip_main.c:667` | `New offset of %c%i found at track %i, scrapping old offset of %c%i%s` |
| `cyanrip_main.c:681` | `No track had AccuRip entry, cannot find offset!` |
| `cyanrip_main.c:683` | `No track was long enough, unable to find drive offset!` |
| `cyanrip_main.c:685` | `Was not able to find drive offset with a radius of %i frames, trying again with a larger radius...` |
| `cyanrip_main.c:691` | `Drive offset of %c%i found (confidence: %i)!` |
| `cyanrip_main.c:721` | `Unable to read track %i subchannel info!` |
| `cyanrip_main.c:751` | `Track %i is data:` |
| `cyanrip_main.c:826` | `Error in decoding/sending frame: %s` |
| `cyanrip_main.c:838` | `Drive media changed, stopping!` |
| `cyanrip_main.c:869` | `Stopping, ripping incomplete!` |
| `cyanrip_main.c:1008` | `Done; (%i out of %i matches for current checksum %08X)` |
| `cyanrip_main.c:1014` | `Done; (no matches found, but hit repeat limit of %i)` |
| `cyanrip_main.c:1030` | `Repeating ripping (%i out of %i matches for current checksum %08X)` |
| `cyanrip_main.c:1045` | `Error in encoding: %s` |
| `cyanrip_main.c:1061` | `Error sending flush signal to encoders: %s` |
| `cyanrip_main.c:1068` | `Track %i ripped and encoded with errors.` |
| `cyanrip_main.c:1070` | `Track %i ripped and encoded successfully!` |
| `cyanrip_main.c:1214` | `Gaps:` |
| `cyanrip_main.c:1219` | `%i frame gap between lead-in and track 1 pregap, merging into pregap` |
| `cyanrip_main.c:1226` | `%i frame unmarked gap between lead-in and track 1, marking as a pregap` |
| `cyanrip_main.c:1248` | `%i frame pregap in track %i,` |
| `cyanrip_main.c:1255` | `unmerged` |
| `cyanrip_main.c:1257` | `merging into track %i` |
| `cyanrip_main.c:1263` | `dropping` |
| `cyanrip_main.c:1269` | `merging` |
| `cyanrip_main.c:1276` | `splitting off into a new track, number %i` |
| `cyanrip_main.c:1317` | `%i frame discontinuity between tracks %i and %i,` |
| `cyanrip_main.c:1322` | `padding track %i` |
| `cyanrip_main.c:1325` | `ignoring` |
| `cyanrip_main.c:1333` | `%i frame gap between last track and lead-out, padding track` |
| `cyanrip_main.c:1359` | `` |
| `cyanrip_main.c:1359` | `    None signalled\n` |
| `cyanrip_main.c:1478` | `Can't init %s handler!` |
| `cyanrip_main.c:1755` | `Invalid paranoia level %i must be between 0 and %i!` |
| `cyanrip_main.c:1768` | `Invalid max coverart size %i (must be 250, 500, 1200 or -1)` |
| `cyanrip_main.c:1780` | `Invalid sanitation method %s` |
| `cyanrip_main.c:1792` | `Invalid release index %i!` |
| `cyanrip_main.c:1803` | `Missing discnumber` |
| `cyanrip_main.c:1808` | `Invalid discnumber %i` |
| `cyanrip_main.c:1815` | `Invalid totaldiscs %i` |
| `cyanrip_main.c:1819` | `discnumber %i is larger than totaldiscs %i` |
| `cyanrip_main.c:1832` | `Supported output codecs:` |
| `cyanrip_main.c:1840` | `Invalid format \"%s\"` |
| `cyanrip_main.c:1845` | `Duplicated format \"%s\"` |
| `cyanrip_main.c:1860` | `Duplicated rip idx %i` |
| `cyanrip_main.c:1894` | `Missing track idx for pregap` |
| `cyanrip_main.c:1899` | `Invalid track idx for pregap: %i` |
| `cyanrip_main.c:1905` | `Missing pregap action` |
| `cyanrip_main.c:1913` | `Invalid pregap action %s` |
| `cyanrip_main.c:1945` | `No cover art location specified for \"%s\"` |
| `cyanrip_main.c:1954` | `Invalid track idx for cover art: %i` |
| `cyanrip_main.c:1960` | `Cover art already specified for track idx %i!` |
| `cyanrip_main.c:1972` | `Cover art \"%s\" already specified!` |
| `cyanrip_main.c:1978` | `Too many cover arts specified!` |
| `cyanrip_main.c:1988` | `Directory name scheme must contain {format} with multiple output formats!` |
| `cyanrip_main.c:1993` | `-J (only generate a CUE sheet) cannot be used with -I (only print info)!` |
| `cyanrip_main.c:2009` | `Searching for drive offset, enabling AccuRip and disabling MusicBrainz and Cover art fetching...` |
| `cyanrip_main.c:2031` | `Offset is unset! To continue with an offset of 0, run with -s 0!` |
| `cyanrip_main.c:2112` | `MusicBrainz URL:%s` |
| `cyanrip_main.c:2158` | `Error reading album tags: %s` |
| `cyanrip_main.c:2188` | `Log(s) will be written to:` |
| `cyanrip_main.c:2196` | `CUE files will be written to:` |
| `cyanrip_main.c:2255` | `Invalid track number %i for pregap, list has %i tracks!` |
| `cyanrip_main.c:2276` | `Invalid track number %i, list has %i tracks!` |
| `cyanrip_main.c:2289` | `Missing \"=\" in track metadata \"%s\"` |
| `cyanrip_main.c:2305` | `Error reading track tags: %s` |
| `cyanrip_main.c:2359` | `Cover art destination(s):` |
| `cyanrip_main.c:2394` | `WARNING: tracks %i and %i resolve to the same file \"%s\", one will overwrite the other!` |
| `cyanrip_main.c:2405` | `Tracks:` |
| `cyanrip_main.c:2415` | `Track %i info:` |
| `cyanrip_main.c:2433` | `Error initializing decoder: %s` |
| `cyanrip_main.c:2442` | `Error initializing encoder: %s` |
| `cyanrip_main.c:2478` | `Error encoding: %s` |
| `cyanrip_main.c:2498` | `Invalid rip index %i, list has %i tracks!` |
| `cyanrip_main.c:2580` | `Error ripping: %s` |
| `discid.c:31` | `Unable to init SHA for DiscID: %s!` |
| `genopt.h:265` | `Error parsing \"%s\" as a <type> for argument \"%s\"` |
| `genopt.h:272` | `Error parsing %f for argument \"%s\": not in [%f:%f] range!` |
| `genopt.h:292` | `Error parsing %lli for argument \"%s\": not in [%lli:%lli] range!` |
| `genopt.h:312` | `Error parsing %llu for argument \"%s\": not in [%llu:%llu] range!` |
| `genopt.h:356` | `Error parsing value for argument \"%s\"` |
| `genopt.h:376` | `Error parsing %f for argument \"%s\": range [%f:%f]!` |
| `genopt.h:558` | `Unable to parse command line argument: %s` |
| `genopt.h:564` | `Programming error, incorrect type for: %s` |
| `genopt.h:575` | `Missing value for argument \"%s\"` |
| `genopt.h:598` | `Too many values for argument \"%s\" (at most %i)` |
| `musicbrainz.c:117` | `Invalid disc number %i, release only has %i CDs` |
| `musicbrainz.c:122` | `Got empty medium list.` |
| `musicbrainz.c:128` | `No mediums match DiscID!` |
| `musicbrainz.c:156` | `Medium has no track list.` |
| `musicbrainz.c:197` | `Could not connect to MusicBrainz.` |
| `musicbrainz.c:205` | `Missing DiscID!` |
| `musicbrainz.c:216` | `MusicBrainz query failed: %s` |
| `musicbrainz.c:223` | `Connection failed, try again? Or disable via -N` |
| `musicbrainz.c:228` | `Error fetching/requesting/auth, this shouldn't happen.` |
| `musicbrainz.c:251` | `MusicBrainz lookup failed: DiscID has no associated releases.` |
| `musicbrainz.c:259` | `MusicBrainz lookup failed: no releases found for DiscID.` |
| `musicbrainz.c:263` | `Multiple releases found in database for DiscID %s:` |
| `musicbrainz.c:284` | `%i (ID: %s): %s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s` |
| `musicbrainz.c:298` | `Please specify which release to use by adding the -R argument with an index or ID.` |
| `musicbrainz.c:303` | `Invalid release index %i specified, only have %i releases!` |
| `musicbrainz.c:321` | `Release ID %s not found in release list for DiscID %s!` |
| `musicbrainz.c:352` | `Found MusicBrainz release: %s - %s` |
| `musicbrainz.c:366` | `MusicBrainz lookup failed, but DiscID has a matching stub, consider verifying the data and creating a release here:` |
| `musicbrainz.c:370` | `Unable to find release info for this CD, and metadata hasn't been manually added!` |
| `musicbrainz.c:374` | `Unable to find metadata for this CD, but metadata has been manually specified, continuing.` |
| `musicbrainz.c:380` | `Please help improve the MusicBrainz DB by submitting the disc info via the following URL:` |
| `musicbrainz.c:387` | `To continue add metadata via -a or -t, or ignore via -N!` |
| `naming.c:123` | `Error parsing string: %s!` |
| `naming.c:215` | `Invalid scheme syntax, unterminated \"{\"!` |
| `naming.c:229` | `Invalid scheme syntax, no \"#\"!` |
| `naming.c:243` | `Invalid scheme syntax, no terminating \"#\"!` |
| `naming.c:259` | `Invalid condition syntax!` |

**301 distinct stable lines.**

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

**`cyanrip_main.c:956`** - reaches logfile: **not directly** - see legend

| # | Segment |
|---|---|
| 0 | `Ripping%strack %i, progress - %0.2f%%` |
| 1 | `, ETA - %ih %im` |
| 2 | `, ETA - %im` |
| 3 | `, ETA - %llds` |
| 4 | `, errors - %i` |
| 5 | ` ` |

Segment 0 is always present; the rest are appended conditionally.

**`cyanrip_main.c:2327`** - reaches logfile: yes

Not derivable: the buffer is built neither by `snprintf` in this
function nor by a `helper(buf, sizeof(buf), ...)` call in it. It
emits arbitrary text - here, the generated CUE sheet echoed back to
the terminal a line at a time. **Do not pattern-match this row**; a
pattern built from its `"%s"` would match every line in the log.

**`cache_probe.c:232`** - reaches logfile: yes

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

Segment 0 is always present; the rest are appended conditionally.

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
| `cyanrip_encode.c:108` | `%s folder: [%s] extension: %s%s` | **not directly** - see legend |
| `cyanrip_encode.c:128` | `Encoder for %s not compiled in ffmpeg!` | **not directly** - see legend |
| `cyanrip_main.c:890` | `\r` | **not directly** - see legend |
| `cyanrip_main.c:956` | `%s` | **not directly** - see legend |
| `cyanrip_main.c:1055` | `Flushing encoders...` | **not directly** - see legend |
| `cyanrip_main.c:1415` | `libcdio %s: %s` | **not directly** - see legend |
| `cyanrip_main.c:1684` | `Log \"%s\" checksum valid.` | **not directly** - see legend |
| `cyanrip_main.c:1687` | `Log \"%s\" checksum mismatch, the file has been modified!` | **not directly** - see legend |
| `cyanrip_main.c:1692` | `Log \"%s\" has data after the checksum, the file has been modified!` | **not directly** - see legend |
| `cyanrip_main.c:1697` | `No FUN512 checksum found in \"%s\"!` | **not directly** - see legend |
| `cyanrip_main.c:1702` | `Couldn't read \"%s\"!` | **not directly** - see legend |
| `genopt.h:399` | `(default: %f)` | yes |
| `genopt.h:409` | `(default: %hi)` | yes |
| `genopt.h:414` | `(default: %i)` | yes |
| `genopt.h:419` | `(default: %lli)` | yes |
| `genopt.h:424` | `(default: %hu)` | yes |
| `genopt.h:429` | `(default: %u)` | yes |
| `genopt.h:434` | `(default: %llu)` | yes |
| `genopt.h:439` | `(default: %s)` | yes |
| `genopt.h:445` | `(default: %i/%i)` | yes |
| `genopt.h:531` | `%s:` | yes |
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
| `1` | 30 | *(the source annotates none)* |
| `2` | 1 | `CRIP_LOG_EXIT_MISMATCH` -- footer present, does not match: modified |
| `3` | 1 | `CRIP_LOG_EXIT_NO_CHECKSUM` -- no footer: incomplete, NOT a tamper claim |
| `4` | 1 | `CRIP_LOG_EXIT_TRAILING_DATA` -- footer present, content after it: modified |
| `5` | 1 | `CRIP_LOG_EXIT_IO_ERROR` -- unreadable: no verdict was reached |

**Values resolved: `0`, `1`, `2`, `3`, `4`, `5`.** Exit paths that could not be resolved: **none**.

Followed from the entry point, one hop at a time, so the scope is checkable
rather than asserted: `main()` -> `cyanrip_run()`.
Comments and string literals are blanked before scanning, because this file's
own comments discuss returns and exits and the first version of this
derivation reported three of them as real paths.

**`1` is the generic failure and carries no class.** For everything except
`--verify-log`, classification must come from the text, which is why P5
exists. `--verify-log` is the one surface that discriminates, and its five
values are wire format: the enum's ORDER is an implementation detail, the
numbers are not, and they are mapped explicitly for that reason.

No non-zero exit is silent: argument parse failures print before returning,
and every other `return 1` reachable from the entry point is preceded by a
`cyanrip_log()` call.

Argument validation runs **before the logfile is opened**. Those diagnostics are
buffered and replayed into the logfile if one is later opened, so a consumer
reading the log does see them. **But a run that refuses during argument
validation opens no logfile at all**, and for that class the only artifact is
the `-j` diagnostics record, which is written for those runs and is off unless
asked for. Without `-j`, a refused run leaves its reason on stdout and nowhere
else.

## P5 - Fatal and error message inventory

Every string reachable on a failure path. Use this to derive error matching
rather than guessing prefixes.

**Evidence** says why each string is here, and is reported rather than folded
into a bare verdict so you can see which entries rest on the weaker test:

- `control flow` - the call is followed by `return 1`, a non-zero `exit()`,
  `return AVERROR(...)`, `total_error_count++`, or `goto fail`. Does not
  depend on how the message is worded.
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
| `accurip.c:97` | `Unable to get AccuRIP DB data: missing CDDB ID!` | wording + goto end | yes |
| `accurip.c:129` | `Unable to get AccuRIP DB data: missing entry!` | wording + goto end | yes |
| `accurip.c:137` | `Unable to get AccuRIP DB data: %s%s` | wording + goto end | yes |
| `accurip.c:140` | `Unable to get AccuRIP DB data: %s!` | wording + goto end | yes |
| `accurip.c:176` | `AccuRIP DB data error, got unexpected number of bytes!` | goto end | yes |
| `coverart.c:51` | `Unable to init lavf context: %s!` | both | yes |
| `coverart.c:57` | `Unable to alloc stream!` | both | yes |
| `coverart.c:70` | `Couldn't open %s for writing: %s!` | both | yes |
| `coverart.c:82` | `Couldn't write header: %s!` | both | yes |
| `coverart.c:92` | `Error writing picture packet: %s!` | both | yes |
| `coverart.c:97` | `Error writing trailer: %s!` | both | yes |
| `coverart.c:177` | `Unable to get cover art \"%s\": not found!` | wording + goto end | yes |
| `coverart.c:186` | `Unable to get cover art \"%s\": %s%s!` | wording + goto end | yes |
| `coverart.c:189` | `Unable to get cover art \"%s\": %s!` | wording + goto end | yes |
| `coverart.c:262` | `Unable to open \"%s\": %s!` | wording + goto end | yes |
| `coverart.c:269` | `Unable to get cover image info: %s!` | wording + goto end | yes |
| `coverart.c:299` | `Error demuxing cover image: %s!` | wording + goto end | yes |
| `cue_writer.c:39` | `Couldn't open path \"%s\" for writing: %s!Invalid folder name? Try -D <folder>.` | both | yes |
| `cyanrip_encode.c:128` | `Encoder for %s not compiled in ffmpeg!` | control flow | **not directly** - see legend |
| `cyanrip_encode.c:364` | `Error creating filter source: %s!` | both | yes |
| `cyanrip_encode.c:375` | `Error creating filter sink: %s!` | both | yes |
| `cyanrip_encode.c:389` | `Error setting filter sample format: %s!` | both | yes |
| `cyanrip_encode.c:397` | `Error setting filter channel layout: %s!` | both | yes |
| `cyanrip_encode.c:406` | `Error setting filter sample rate: %s!` | both | yes |
| `cyanrip_encode.c:440` | `Error initializing filter sink: %s!` | both | yes |
| `cyanrip_encode.c:474` | `Error parsing filter graph: %s!` | both | yes |
| `cyanrip_encode.c:480` | `Error configuring filter graph: %s!` | both | yes |
| `cyanrip_encode.c:541` | `Error pushing frame to FIFO: %s!` | wording | yes |
| `cyanrip_encode.c:614` | `Error filtering frame: %s!` | both | yes |
| `cyanrip_encode.c:692` | `Error allocating frame!` | both | yes |
| `cyanrip_encode.c:704` | `Error allocating frame: %s!` | both | yes |
| `cyanrip_encode.c:868` | `Could not alloc swr context!` | wording | yes |
| `cyanrip_encode.c:886` | `Could not init swr context!` | wording | yes |
| `cyanrip_encode.c:1061` | `Error while encoding: %s!` | both | yes |
| `cyanrip_encode.c:1083` | `Error encoding: %s!` | both | yes |
| `cyanrip_encode.c:1114` | `Error pushing packet to FIFO: %s!` | both | yes |
| `cyanrip_encode.c:1121` | `Error writing packet: %s!` | both | yes |
| `cyanrip_encode.c:1151` | `Error writing to file: %s!` | both | yes |
| `cyanrip_encode.c:1274` | `Codec not found (not compiled in lavc?)!` | control flow | yes |
| `cyanrip_encode.c:1283` | `Unable to init output avctx!` | both | yes |
| `cyanrip_encode.c:1294` | `Could not open output codec context!` | both | yes |
| `cyanrip_encode.c:1301` | `Couldn't copy codec params!` | both | yes |
| `cyanrip_encode.c:1308` | `Couldn't open %s: %s! Invalid folder name? Try -D <folder>.` | both | yes |
| `cyanrip_main.c:224` | `No device specified and unable to get default device!` | both | yes |
| `cyanrip_main.c:232` | `Unable to open device: %s` | both | yes |
| `cyanrip_main.c:241` | `Unable to init cddap context!` | wording | yes |
| `cyanrip_main.c:243` | `cdio: \"%s\"` | control flow | yes |
| `cyanrip_main.c:266` | `Unable to open device!` | both | yes |
| `cyanrip_main.c:275` | `Device does not support changing speeds!` | control flow | yes |
| `cyanrip_main.c:292` | `Unable to init paranoia!` | both | yes |
| `cyanrip_main.c:337` | `Invalid number of tracks: %i!` | both | yes |
| `cyanrip_main.c:360` | `CDIO returned invalid track %i end LSN` | control flow | yes |
| `cyanrip_main.c:542` | `cdio error: %s` | control flow | yes |
| `cyanrip_main.c:549` | `Frame read failed!` | control flow | yes |
| `cyanrip_main.c:636` | `Stopping, offset finding incomplete!` | wording + goto end | yes |
| `cyanrip_main.c:721` | `Unable to read track %i subchannel info!` | wording | yes |
| `cyanrip_main.c:826` | `Error in decoding/sending frame: %s` | both | yes |
| `cyanrip_main.c:838` | `Drive media changed, stopping!` | both | yes |
| `cyanrip_main.c:869` | `Stopping, ripping incomplete!` | wording | yes |
| `cyanrip_main.c:1008` | `Done; (%i out of %i matches for current checksum %08X)` | goto finalize_ripping | yes |
| `cyanrip_main.c:1014` | `Done; (no matches found, but hit repeat limit of %i)` | goto finalize_ripping | yes |
| `cyanrip_main.c:1045` | `Error in encoding: %s` | wording + goto end | yes |
| `cyanrip_main.c:1061` | `Error sending flush signal to encoders: %s` | wording | yes |
| `cyanrip_main.c:1702` | `Couldn't read \"%s\"!` | wording | **not directly** - see legend |
| `cyanrip_main.c:1755` | `Invalid paranoia level %i must be between 0 and %i!` | both | yes |
| `cyanrip_main.c:1768` | `Invalid max coverart size %i (must be 250, 500, 1200 or -1)` | both | yes |
| `cyanrip_main.c:1780` | `Invalid sanitation method %s` | both | yes |
| `cyanrip_main.c:1792` | `Invalid release index %i!` | both | yes |
| `cyanrip_main.c:1803` | `Missing discnumber` | both | yes |
| `cyanrip_main.c:1808` | `Invalid discnumber %i` | both | yes |
| `cyanrip_main.c:1815` | `Invalid totaldiscs %i` | both | yes |
| `cyanrip_main.c:1819` | `discnumber %i is larger than totaldiscs %i` | control flow | yes |
| `cyanrip_main.c:1840` | `Invalid format \"%s\"` | both | yes |
| `cyanrip_main.c:1845` | `Duplicated format \"%s\"` | control flow | yes |
| `cyanrip_main.c:1860` | `Duplicated rip idx %i` | control flow | yes |
| `cyanrip_main.c:1894` | `Missing track idx for pregap` | both | yes |
| `cyanrip_main.c:1899` | `Invalid track idx for pregap: %i` | both | yes |
| `cyanrip_main.c:1905` | `Missing pregap action` | both | yes |
| `cyanrip_main.c:1913` | `Invalid pregap action %s` | both | yes |
| `cyanrip_main.c:1945` | `No cover art location specified for \"%s\"` | both | yes |
| `cyanrip_main.c:1954` | `Invalid track idx for cover art: %i` | both | yes |
| `cyanrip_main.c:1960` | `Cover art already specified for track idx %i!` | control flow | yes |
| `cyanrip_main.c:1972` | `Cover art \"%s\" already specified!` | control flow | yes |
| `cyanrip_main.c:1978` | `Too many cover arts specified!` | control flow | yes |
| `cyanrip_main.c:1988` | `Directory name scheme must contain {format} with multiple output formats!` | control flow | yes |
| `cyanrip_main.c:1993` | `-J (only generate a CUE sheet) cannot be used with -I (only print info)!` | both | yes |
| `cyanrip_main.c:2031` | `Offset is unset! To continue with an offset of 0, run with -s 0!` | goto end | yes |
| `cyanrip_main.c:2158` | `Error reading album tags: %s` | both | yes |
| `cyanrip_main.c:2255` | `Invalid track number %i for pregap, list has %i tracks!` | both | yes |
| `cyanrip_main.c:2276` | `Invalid track number %i, list has %i tracks!` | both | yes |
| `cyanrip_main.c:2289` | `Missing \"=\" in track metadata \"%s\"` | both | yes |
| `cyanrip_main.c:2305` | `Error reading track tags: %s` | both | yes |
| `cyanrip_main.c:2327` | `%s` | goto end | yes |
| `cyanrip_main.c:2433` | `Error initializing decoder: %s` | both | yes |
| `cyanrip_main.c:2442` | `Error initializing encoder: %s` | both | yes |
| `cyanrip_main.c:2478` | `Error encoding: %s` | wording + goto end | yes |
| `cyanrip_main.c:2498` | `Invalid rip index %i, list has %i tracks!` | both | yes |
| `cyanrip_main.c:2580` | `Error ripping: %s` | wording + goto end | yes |
| `diagnostics.c:526` | `Couldn't open diagnostics path \"%s\" for writing!` | wording | **not directly** - see legend |
| `discid.c:31` | `Unable to init SHA for DiscID: %s!` | wording | yes |
| `genopt.h:265` | `Error parsing \"%s\" as a <type> for argument \"%s\"` | genopt | yes |
| `genopt.h:272` | `Error parsing %f for argument \"%s\": not in [%f:%f] range!` | genopt | yes |
| `genopt.h:292` | `Error parsing %lli for argument \"%s\": not in [%lli:%lli] range!` | genopt | yes |
| `genopt.h:312` | `Error parsing %llu for argument \"%s\": not in [%llu:%llu] range!` | genopt | yes |
| `genopt.h:356` | `Error parsing value for argument \"%s\"` | genopt | yes |
| `genopt.h:376` | `Error parsing %f for argument \"%s\": range [%f:%f]!` | genopt | yes |
| `genopt.h:558` | `Unable to parse command line argument: %s` | genopt | yes |
| `genopt.h:564` | `Programming error, incorrect type for: %s` | genopt | yes |
| `genopt.h:575` | `Missing value for argument \"%s\"` | genopt | yes |
| `genopt.h:598` | `Too many values for argument \"%s\" (at most %i)` | genopt | yes |
| `musicbrainz.c:117` | `Invalid disc number %i, release only has %i CDs` | both | yes |
| `musicbrainz.c:122` | `Got empty medium list.` | control flow | yes |
| `musicbrainz.c:197` | `Could not connect to MusicBrainz.` | both | yes |
| `musicbrainz.c:205` | `Missing DiscID!` | wording | yes |
| `musicbrainz.c:228` | `Error fetching/requesting/auth, this shouldn't happen.` | both | yes |
| `musicbrainz.c:251` | `MusicBrainz lookup failed: DiscID has no associated releases.` | goto end_meta | yes |
| `musicbrainz.c:259` | `MusicBrainz lookup failed: no releases found for DiscID.` | goto end_meta | yes |
| `musicbrainz.c:298` | `Please specify which release to use by adding the -R argument with an index or ID.` | control flow | yes |
| `musicbrainz.c:303` | `Invalid release index %i specified, only have %i releases!` | both | yes |
| `musicbrainz.c:321` | `Release ID %s not found in release list for DiscID %s!` | control flow | yes |
| `musicbrainz.c:366` | `MusicBrainz lookup failed, but DiscID has a matching stub, consider verifying the data and creating a release here:` | control flow | yes |
| `musicbrainz.c:370` | `Unable to find release info for this CD, and metadata hasn't been manually added!` | both | yes |
| `musicbrainz.c:374` | `Unable to find metadata for this CD, but metadata has been manually specified, continuing.` | wording | yes |
| `naming.c:123` | `Error parsing string: %s!` | wording | yes |
| `naming.c:215` | `Invalid scheme syntax, unterminated \"{\"!` | both | yes |
| `naming.c:229` | `Invalid scheme syntax, no \"#\"!` | both | yes |
| `naming.c:243` | `Invalid scheme syntax, no terminating \"#\"!` | both | yes |
| `naming.c:259` | `Invalid condition syntax!` | both | yes |

**128 distinct strings.** By evidence: 66 both, 18 control flow, 13 wording, 3 goto end, 14 wording + goto end.

The `control flow` and `both` rows total 84 strings proven reachable on a
failure path without reference to their wording. That subset is the one to
build a hard failure classifier on.

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
| stock, genopt onward (`master` = `958e1ad`, 0.9.4-rc1) | exit 0 | **exit 1** | exit 0 |
| **this fork** (`e1d800e` onward) | exit 0 | exit 0 | exit 0 |

- Pre-genopt uses plain `getopt()` -- `#include <getopt.h>`, a short-only
  optstring containing `V`, **no long options at all** -- so `--version` is
  rejected by getopt before cyanrip sees it, on stderr, prefixed with the
  binary's own path.
- `442de2a` *"Replace getopt option parsing with genopt"* moved the flag to
  `-v`/`--version` and dropped `-V`.
- `e1d800e` restores `-V` as an alias **on this fork only**; it is not
  upstream.

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

## P8 - The `-j` diagnostics record

**DERIVED, from two sources that must agree.** The key names come from
`diagnostics.c`'s emitter, where they are spelled into the format
strings; the types and nullability come from real records. Neither half
is sufficient alone, and the failure mode each one covers is the other's
blind spot: a record-only derivation lists whatever the samples happened
to exercise and calls it a schema, and a source-only derivation cannot
say which fields are ever null. Anything the two disagree about is
reported below rather than reconciled.

Platterpus asked for this in round 12 §F1 and carried it into round 13.

### P8a - The schema string, and what a consumer should do with it

This build emits `"schema": "cyanrip-diagnostics/3"` (`diagnostics.c:327`).

The number after the slash is not a version to compare, it is an
identity to recognise. A field ADDED to this record is harmless to a
reader that ignores unknown keys, and every change so far has been an
addition -- so a consumer that rejects an unrecognised schema string
rejects records it could have read. Gate on the prefix, and widen the
accepted set rather than pinning one value.

### P8b - Every field

Derived from 4 records, named rather than globbed so that
a shape which stops being covered is a visible act:

- **a completed rip** -- `docs/golden-reference.diagnostics.json`
- **a rip stopped by a signal** -- `docs/sample-interrupted.diagnostics.json`
- **a run refused during argument validation** -- produced by -J -I -j
- **a run with stall reporting off (-k 0)** -- produced by -J -I -k 0 -j

`null` in the table means **observed null in at least one record**, which
is a stronger claim than "the type allows it" and a weaker one than
"it is the only way it can be null". A field marked `--` was never
observed null by any record here; that is not a guarantee it cannot be.

| field | type | observed null | in every record |
|---|---|---|---|
| `cyanrip` | object | -- | yes |
| `cyanrip.fork_id` | string | -- | yes |
| `cyanrip.handshake` | string | -- | yes |
| `cyanrip.released_build_declared` | bool | -- | yes |
| `cyanrip.vcs` | string | -- | yes |
| `cyanrip.version` | string | -- | yes |
| `exit_code` | int | -- | yes |
| `invocation` | string | -- | yes |
| `messages` | array | -- | yes |
| `messages[]` | string | -- | yes |
| `messages_are_classified` | bool | -- | yes |
| `messages_complete_within_scope` | bool | -- | yes |
| `messages_dropped` | int | -- | yes |
| `messages_note` | string | -- | yes |
| `messages_scope` | string | -- | yes |
| `messages_tail` | array | -- | yes |
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
| `rip.consumer` | string | -- | **no** |
| `rip.consumer_verified` | bool | -- | **no** |
| `rip.device` | string | -- | **no** |
| `rip.frame_retries` | int | -- | **no** |
| `rip.interrupted` | bool | -- | **no** |
| `rip.interrupted_by` | string | **yes** | **no** |
| `rip.offset_samples` | int | -- | **no** |
| `rip.paranoia_level` | int | -- | **no** |
| `rip.rip_repeats` | int | -- | **no** |
| `rip.ripping_errors` | int | -- | **no** |
| `rip.track_state` | array | -- | **no** |
| `rip.track_state[]` | object | -- | **no** |
| `rip.track_state[].audio_ripped` | bool | -- | **no** |
| `rip.track_state[].cd_track` | int | -- | **no** |
| `rip.track_state[].crcs_computed` | bool | -- | **no** |
| `rip.track_state[].eac_crc` | string | **yes** | **no** |
| `rip.track_state[].number` | int | -- | **no** |
| `rip.track_state[].repeats` | int | -- | **no** |
| `rip.track_state[].rip_time_us` | int | -- | **no** |
| `rip.tracks` | int | -- | **no** |
| `rip.tracks_completed` | int | -- | **no** |
| `schema` | string | -- | yes |

The two derivations agree: every key in the source scan appears in a
record, and every key in a record appears in the source scan.

### P8c - Two absences that are deliberate

Both would be easy to add and both would be wrong, so they are stated
here rather than left to look like oversights.

- **No severity on any message.** `cyanrip_log()` carries none, so
  attaching one here would be this program guessing at its own output.
  The record says so in its own `messages_note` field rather than only
  in this document.
- **No `success` flag.** A record is written for runs that produce no
  logfile at all, which is the reason `-j` exists; a boolean verdict
  would be cyanrip making a judgement, and judgements are the
  consumer's. `exit_code`, `ripping_errors`, `interrupted` and the
  per-track `audio_ripped` are the measurements a verdict would be
  built from, and they are all present.

`exit_code` is **tri-state and `null` is not `0`.** A record written from
`atexit` before the exit status is known reports `null`, and a consumer
that coerces that to zero reports a crashed run as a clean one.

On **this fork** the genopt message is routed through `cyanrip_log()`, so
it reaches stdout, the logfile if one is open, and the `-j` record. That
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

**The default is `unicode`.** `cyanrip_main.c:1488` assigns `CRIP_SANITIZE_UNICODE`, and it
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
| `naming.c:142` | `av_bprint_append_data` | the input, verbatim |
| `naming.c:147` | `av_bprint_chars` | the `simple` glyph, from the table |
| `naming.c:150` | `av_bprint_append_data` | the `unicode` glyph, from the table |

### P7c - What each mode does to each character

The two `os_` modes substitute a character **only when it is unavailable
on the build's OS**. Note which way that runs: a character being *legal*
on the target filesystem is why an `os_` mode leaves it **alone**. On any
given build an `os_` mode is therefore the **least** substituting of the
four, never the most, and `-T os_unicode` is not a way to ask for the
unicode glyphs -- it is a way to ask for fewer of them.

Availability is a **compile-time** property (P7e). Two columns cover it,
because `os_compat.h` has exactly two states for these macros: the
`HAVE_WMAIN` build and everything else. `HAVE_WMAIN` is set by
`src/meson.build:150` when the compiler links `wmain` with `-municode`,
so in practice it means a Windows/MinGW build. The build that generated
this document is named in the banner at the top; which branch **your**
build took is a property of your build, not of this file.

| character | `simple` | `unicode` | `os_simple` non-`HAVE_WMAIN` | `os_unicode` non-`HAVE_WMAIN` | `os_simple` `HAVE_WMAIN` | `os_unicode` `HAVE_WMAIN` |
|---|---|---|---|---|---|---|
| `<` | `_` | `‹` | unchanged | unchanged | `_` | `‹` |
| `>` | `_` | `›` | unchanged | unchanged | `_` | `›` |
| `:` | `_` | `∶` | unchanged | unchanged | `_` | `∶` |
| `\|` | `_` | `│` | unchanged | unchanged | `_` | `│` |
| `?` | `_` | `？` | unchanged | unchanged | `_` | `？` |
| `*` | `_` | `∗` | unchanged | unchanged | `_` | `∗` |
| `/` † | `_` | `∕` | `_` | `∕` | `_` | `∕` |
| `\` | `_` | `⧹` | unchanged | unchanged | `_` | `⧹` |
| `"` | `'` | `“` | unchanged | unchanged | `'` | `“` |
| `"` | `'` | `”` | unchanged | unchanged | `'` | `”` |

Read the two `non-HAVE_WMAIN` columns before treating an `os_` mode as
a safe substitute for a plain one. On such a build **8 of the 9 distinct
characters** are left unchanged by both `os_` modes: `<`, `>`, `:`, `\|`, `?`, `*`, `\`, `"`.

Which leaves `os_simple` and `os_unicode` differing, on such a
build, on `/` and nothing else.

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
| `naming.c:205` | `0` | literal text, never a tag value -- `/` is a directory separator here |
| `naming.c:315` | `origin_is_tag` | `origin_is_tag`: 1 when the token resolved to a metadata tag, 0 when it fell back to literal scheme text |
| `naming.c:335` | `origin_is_tag` | `origin_is_tag`: 1 when the token resolved to a metadata tag, 0 when it fell back to literal scheme text |
| `naming.c:401` | `0` | literal text, never a tag value -- `/` is a directory separator here |

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
| `HAS_CH_COLUMN` | `1` (`os_compat.h:115`) | `HAVE_WMAIN` | `0` (`os_compat.h:99`) |
| `HAS_CH_OR` | `1` (`os_compat.h:118`) | `HAVE_WMAIN` | `0` (`os_compat.h:100`) |
| `HAS_CH_Q` | `1` (`os_compat.h:121`) | `HAVE_WMAIN` | `0` (`os_compat.h:101`) |
| `HAS_CH_ANY` | `1` (`os_compat.h:124`) | `HAVE_WMAIN` | `0` (`os_compat.h:102`) |
| `HAS_CH_FWDSLASH` | `0` (`os_compat.h:127`, *default should be 0 here*) | `HAVE_WMAIN` | `0` (`os_compat.h:103`) |
| `HAS_CH_BWDSLASH` | `1` (`os_compat.h:130`) | `HAVE_WMAIN` | `0` (`os_compat.h:104`) |
| `HAS_CH_QUOTES` | `1` (`os_compat.h:133`) | `HAVE_WMAIN` | `0` (`os_compat.h:105`) |

A macro appears once per row of P7b, so `HAS_CH_QUOTES` governs both
quote rows together.

**Defined here and read by nothing.** Derived, not noted: this
paragraph disappears by itself when the macro is wired up, which a
prose remark could not do.

- **`HAS_COLUMN`** -- `os_compat.h:93` defines it as
  `0` under `__MACH__`. No file in `src/` reads
  that name.

Stated as an observation and not as an intent: this generator can see
that the name is never read, and cannot see what was meant. The
consequence a consumer can act on is in the table above -- the macro
the substitution table actually reads has no override under that
condition, so those builds follow the default column.

