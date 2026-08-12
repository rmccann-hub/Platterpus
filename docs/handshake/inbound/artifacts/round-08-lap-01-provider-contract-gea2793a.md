# cyanrip provider contract

**Generated** by `tools/gen-provider-contract.py` from the source tree and the
built binary. Do not edit by hand -- regenerate. A hand-written contract goes
stale silently, which is the failure this file exists to prevent.

Build: `cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-g<commit>)`

**Source anchor:** `sha256/16 = 99769a09466b0b57` over `src/*.c` and
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
| `-x` | `--cache-probe` | Measure the drive's readback cache before ripping (costs seconds) (default: false) |
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
| `cache_probe.c:108` | `Cache probe:    not run (disc image has no drive cache)` |
| `cache_probe.c:116` | `Cache probe:    unknown (out of memory)` |
| `cache_probe.c:129` | `Cache probe:    unknown (disc too short to probe)` |
| `cache_probe.c:141` | `Cache probe:    unknown (read failed while calibrating)` |
| `cache_probe.c:158` | `Cache probe:    unknown (drive returned reads too fast to time)` |
| `cache_probe.c:187` | `Cache probe:    no readback cache measured (uncached read %.1f ms)` |
| `cache_probe.c:193` | `Cache probe:    %i sectors measured (%.1f KiB, uncached read %.1f ms)` |
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
| `cyanrip_encode.c:839` | `Could not alloc swr context!` |
| `cyanrip_encode.c:857` | `Could not init swr context!` |
| `cyanrip_encode.c:1032` | `Error while encoding: %s!` |
| `cyanrip_encode.c:1054` | `Error encoding: %s!` |
| `cyanrip_encode.c:1085` | `Error pushing packet to FIFO: %s!` |
| `cyanrip_encode.c:1092` | `Error writing packet: %s!` |
| `cyanrip_encode.c:1122` | `Error writing to file: %s!` |
| `cyanrip_encode.c:1245` | `Codec not found (not compiled in lavc?)!` |
| `cyanrip_encode.c:1254` | `Unable to init output avctx!` |
| `cyanrip_encode.c:1265` | `Could not open output codec context!` |
| `cyanrip_encode.c:1272` | `Couldn't copy codec params!` |
| `cyanrip_encode.c:1279` | `Couldn't open %s: %s! Invalid folder name? Try -D <folder>.` |
| `cyanrip_log.c:58` | `%s%s:` |
| `cyanrip_log.c:61` | `%s` |
| `cyanrip_log.c:71` | `CD-TEXT:        none reported by libcdio (absent, or unreadable by this driver)` |
| `cyanrip_log.c:76` | `CD-TEXT:        present (%s, %i disc %s, %i of %i tracks tagged)` |
| `cyanrip_log.c:97` | `Cache model:    not in use (paranoia disabled)` |
| `cyanrip_log.c:108` | `Cache model:    %i sector%s (disc image, no drive cache)` |
| `cyanrip_log.c:113` | `Cache model:    %i sector%s (drive cache size not probed)` |
| `cyanrip_log.c:147` | `%sSample peak disagreement: ebur128 %.2f dBFS, direct scan %.2f dBFS (%.2f dB apart)` |
| `cyanrip_log.c:173` | `Read stalls:    %s` |
| `cyanrip_log.c:184` | `%s%s` |
| `cyanrip_log.c:188` | `%lu` |
| `cyanrip_log.c:247` | `Pregap LSN:  %i (duration: %s)` |
| `cyanrip_log.c:249` | `Pregap length: %i frames` |
| `cyanrip_log.c:251` | `Pregap LSN:  unknown (sub-channel unreadable)` |
| `cyanrip_log.c:253` | `Pregap LSN:  unknown (sub-channel CRC mismatches)` |
| `cyanrip_log.c:255` | `Pregap LSN:  none` |
| `cyanrip_log.c:261` | `Pregap source: sub-channel (not signalled by TOC)` |
| `cyanrip_log.c:263` | `Pregap source: lead-in` |
| `cyanrip_log.c:265` | `Pregap source: TOC` |
| `cyanrip_log.c:268` | `Prepended:   %i frames of silence` |
| `cyanrip_log.c:269` | `Start LSN:   %i` |
| `cyanrip_log.c:271` | `(with offset: %i)` |
| `cyanrip_log.c:275` | `End LSN:     %i` |
| `cyanrip_log.c:282` | `Appended:    %i frames of silence` |
| `cyanrip_log.c:313` | `Preemphasis:` |
| `cyanrip_log.c:315` | `none detected` |
| `cyanrip_log.c:318` | `(deemphasis forced)` |
| `cyanrip_log.c:323` | `present (subcode)` |
| `cyanrip_log.c:325` | `present (TOC)` |
| `cyanrip_log.c:328` | `(deemphasis applied)` |
| `cyanrip_log.c:333` | `Properties:` |
| `cyanrip_log.c:336` | `Data bytes:  %i (%.2f Mib)` |
| `cyanrip_log.c:339` | `Frames:      %u` |
| `cyanrip_log.c:345` | `Duration:    %s` |
| `cyanrip_log.c:346` | `Samples:     %zu` |
| `cyanrip_log.c:354` | `Sample peak level: %.1f%% (%.1f dBFS)` |
| `cyanrip_log.c:357` | `True peak level:   %.1f dBFS` |
| `cyanrip_log.c:376` | `Integrated loudness (R128): %.1f LUFS` |
| `cyanrip_log.c:378` | `Loudness range (R128):      %.1f LU (%.1f to %.1f LUFS)` |
| `cyanrip_log.c:382` | `Extraction speed:  %.1fx` |
| `cyanrip_log.c:384` | `Elapsed:            %.2f s` |
| `cyanrip_log.c:392` | `EAC CRC32:     %08X` |
| `cyanrip_log.c:394` | `(after %i rips)` |
| `cyanrip_log.c:401` | `Secure re-read:  converged after %i reads` |
| `cyanrip_log.c:404` | `Secure re-read:  did NOT converge after %i reads (repeat limit hit)` |
| `cyanrip_log.c:409` | `Secure re-read:  not attempted` |
| `cyanrip_log.c:413` | `Accurip:       %s` |
| `cyanrip_log.c:417` | `(max confidence: %i)` |
| `cyanrip_log.c:425` | `Accurip v1:  %08X` |
| `cyanrip_log.c:427` | `(accurately ripped, confidence %i)` |
| `cyanrip_log.c:429` | `(not found, either a new pressing, or bad rip)` |
| `cyanrip_log.c:433` | `Accurip v2:  %08X` |
| `cyanrip_log.c:444` | `Accurip 450: %08X` |
| `cyanrip_log.c:446` | `(match found, confidence %i, but a checksum of 0 is meaningless)` |
| `cyanrip_log.c:449` | `(matches Accurip DB, confidence %i, track is partially accurately ripped)` |
| `cyanrip_log.c:452` | `(not found)` |
| `cyanrip_log.c:459` | `Metadata:` |
| `cyanrip_log.c:469` | `%s:` |
| `cyanrip_log.c:481` | `CD-TEXT:` |
| `cyanrip_log.c:491` | `Paranoia status counts:` |
| `cyanrip_log.c:493` | `none` |
| `cyanrip_log.c:516` | `Embedded cover art:    %s: %s` |
| `cyanrip_log.c:519` | `Embedded cover art:    %s: %ix%i %s` |
| `cyanrip_log.c:523` | `File(s):` |
| `cyanrip_log.c:537` | `cyanrip %s (%s-g%s)` |
| `cyanrip_log.c:540` | `Invoked as:     %s` |
| `cyanrip_log.c:548` | `Handshake:      %s%s` |
| `cyanrip_log.c:554` | `Consumer:       %s` |
| `cyanrip_log.c:558` | `(reported by the caller, not verified by cyanrip)` |
| `cyanrip_log.c:562` | `Drive used:     error retrieving drive info` |
| `cyanrip_log.c:564` | `Drive used:     %s %s (revision %s)` |
| `cyanrip_log.c:565` | `System device:  %s` |
| `cyanrip_log.c:567` | `Device model:   %s` |
| `cyanrip_log.c:576` | `Offset:         %c%u %s` |
| `cyanrip_log.c:579` | `%s%c%i %s` |
| `cyanrip_log.c:588` | `Speed:          %ix` |
| `cyanrip_log.c:590` | `Speed:          default (%s)` |
| `cyanrip_log.c:592` | `C2 errors:      %s` |
| `cyanrip_log.c:601` | `Encoder:        libavformat %i.%i.%i, libavcodec %i.%i.%i (%s)` |
| `cyanrip_log.c:606` | `Paranoia level: %s` |
| `cyanrip_log.c:610` | `Paranoia level: %i` |
| `cyanrip_log.c:611` | `Frame retries:  %i` |
| `cyanrip_log.c:613` | `HDCD decoding:  %s` |
| `cyanrip_log.c:615` | `Album Art:      %s` |
| `cyanrip_log.c:619` | `%s%s%s%s%s` |
| `cyanrip_log.c:627` | `Outputs:` |
| `cyanrip_log.c:633` | `Disc tracks:    %i` |
| `cyanrip_log.c:634` | `Tracks to rip:  %s` |
| `cyanrip_log.c:637` | `%i%s` |
| `cyanrip_log.c:651` | `AccurateRip:    %s` |
| `cyanrip_log.c:657` | `Total time:     %s` |
| `cyanrip_log.c:702` | `Tracks ripped accurately: %i/%i` |
| `cyanrip_log.c:704` | `Tracks ripped partially accurately: %i/%i` |
| `cyanrip_log.c:714` | `Ripping errors: %i` |
| `cyanrip_log.c:723` | `Rip completed:  no (interrupted by user, %i of %i tracks)` |
| `cyanrip_log.c:726` | `Rip completed:  yes (%i of %i tracks)` |
| `cyanrip_log.c:729` | `Ripping finished at %s` |
| `cyanrip_main.c:211` | `No device specified and unable to get default device!` |
| `cyanrip_main.c:219` | `Unable to open device: %s` |
| `cyanrip_main.c:228` | `Unable to init cddap context!` |
| `cyanrip_main.c:230` | `cdio: \"%s\"` |
| `cyanrip_main.c:241` | `Opening drive...` |
| `cyanrip_main.c:244` | `Unable to open device!` |
| `cyanrip_main.c:253` | `Device does not support changing speeds!` |
| `cyanrip_main.c:261` | `cdio error: %s` |
| `cyanrip_main.c:270` | `Unable to init paranoia!` |
| `cyanrip_main.c:315` | `Invalid number of tracks: %i!` |
| `cyanrip_main.c:338` | `CDIO returned invalid track %i end LSN` |
| `cyanrip_main.c:498` | `Frame read failed!` |
| `cyanrip_main.c:575` | `Loading data for track %i...` |
| `cyanrip_main.c:585` | `Stopping, offset finding incomplete!` |
| `cyanrip_main.c:593` | `Data loaded, searching for offsets...` |
| `cyanrip_main.c:602` | `Nothing found for track %i%s` |
| `cyanrip_main.c:607` | `Offset of %c%i found in track %i%s` |
| `cyanrip_main.c:612` | `Offset of %c%i confirmed (confidence: %i) in track %i%s` |
| `cyanrip_main.c:616` | `New offset of %c%i found at track %i, scrapping old offset of %c%i%s` |
| `cyanrip_main.c:630` | `No track had AccuRip entry, cannot find offset!` |
| `cyanrip_main.c:632` | `No track was long enough, unable to find drive offset!` |
| `cyanrip_main.c:634` | `Was not able to find drive offset with a radius of %i frames, trying again with a larger radius...` |
| `cyanrip_main.c:640` | `Drive offset of %c%i found (confidence: %i)!` |
| `cyanrip_main.c:670` | `Unable to read track %i subchannel info!` |
| `cyanrip_main.c:686` | `Track %i is data:` |
| `cyanrip_main.c:743` | `Error in decoding/sending frame: %s` |
| `cyanrip_main.c:755` | `Drive media changed, stopping!` |
| `cyanrip_main.c:786` | `Stopping, ripping incomplete!` |
| `cyanrip_main.c:904` | `Done; (%i out of %i matches for current checksum %08X)` |
| `cyanrip_main.c:910` | `Done; (no matches found, but hit repeat limit of %i)` |
| `cyanrip_main.c:926` | `Repeating ripping (%i out of %i matches for current checksum %08X)` |
| `cyanrip_main.c:941` | `Error in encoding: %s` |
| `cyanrip_main.c:957` | `Error sending flush signal to encoders: %s` |
| `cyanrip_main.c:964` | `Track %i ripped and encoded with errors.` |
| `cyanrip_main.c:966` | `Track %i ripped and encoded successfully!` |
| `cyanrip_main.c:1048` | `Gaps:` |
| `cyanrip_main.c:1053` | `%i frame gap between lead-in and track 1 pregap, merging into pregap` |
| `cyanrip_main.c:1060` | `%i frame unmarked gap between lead-in and track 1, marking as a pregap` |
| `cyanrip_main.c:1082` | `%i frame pregap in track %i,` |
| `cyanrip_main.c:1089` | `unmerged` |
| `cyanrip_main.c:1091` | `merging into track %i` |
| `cyanrip_main.c:1097` | `dropping` |
| `cyanrip_main.c:1103` | `merging` |
| `cyanrip_main.c:1110` | `splitting off into a new track, number %i` |
| `cyanrip_main.c:1151` | `%i frame discontinuity between tracks %i and %i,` |
| `cyanrip_main.c:1156` | `padding track %i` |
| `cyanrip_main.c:1159` | `ignoring` |
| `cyanrip_main.c:1167` | `%i frame gap between last track and lead-out, padding track` |
| `cyanrip_main.c:1283` | `Can't init signal handler!` |
| `cyanrip_main.c:1533` | `Invalid paranoia level %i must be between 0 and %i!` |
| `cyanrip_main.c:1546` | `Invalid max coverart size %i (must be 250, 500, 1200 or -1)` |
| `cyanrip_main.c:1558` | `Invalid sanitation method %s` |
| `cyanrip_main.c:1570` | `Invalid release index %i!` |
| `cyanrip_main.c:1581` | `Missing discnumber` |
| `cyanrip_main.c:1586` | `Invalid discnumber %i` |
| `cyanrip_main.c:1593` | `Invalid totaldiscs %i` |
| `cyanrip_main.c:1597` | `discnumber %i is larger than totaldiscs %i` |
| `cyanrip_main.c:1610` | `Supported output codecs:` |
| `cyanrip_main.c:1618` | `Invalid format \"%s\"` |
| `cyanrip_main.c:1623` | `Duplicated format \"%s\"` |
| `cyanrip_main.c:1638` | `Duplicated rip idx %i` |
| `cyanrip_main.c:1652` | `Missing track idx for pregap` |
| `cyanrip_main.c:1657` | `Invalid track idx for pregap: %i` |
| `cyanrip_main.c:1663` | `Missing pregap action` |
| `cyanrip_main.c:1671` | `Invalid pregap action %s` |
| `cyanrip_main.c:1702` | `No cover art location specified for \"%s\"` |
| `cyanrip_main.c:1711` | `Invalid track idx for cover art: %i` |
| `cyanrip_main.c:1717` | `Cover art already specified for track idx %i!` |
| `cyanrip_main.c:1729` | `Cover art \"%s\" already specified!` |
| `cyanrip_main.c:1735` | `Too many cover arts specified!` |
| `cyanrip_main.c:1745` | `Directory name scheme must contain {format} with multiple output formats!` |
| `cyanrip_main.c:1750` | `-J (only generate a CUE sheet) cannot be used with -I (only print info)!` |
| `cyanrip_main.c:1766` | `Searching for drive offset, enabling AccuRip and disabling MusicBrainz and Cover art fetching...` |
| `cyanrip_main.c:1788` | `Offset is unset! To continue with an offset of 0, run with -s 0!` |
| `cyanrip_main.c:1869` | `MusicBrainz URL:%s` |
| `cyanrip_main.c:1913` | `Error reading album tags: %s` |
| `cyanrip_main.c:1943` | `Log(s) will be written to:` |
| `cyanrip_main.c:1951` | `CUE files will be written to:` |
| `cyanrip_main.c:2005` | `Invalid track number %i, list has %i tracks!` |
| `cyanrip_main.c:2018` | `Missing \"=\" in track metadata \"%s\"` |
| `cyanrip_main.c:2034` | `Error reading track tags: %s` |
| `cyanrip_main.c:2088` | `Cover art destination(s):` |
| `cyanrip_main.c:2123` | `WARNING: tracks %i and %i resolve to the same file \"%s\", one will overwrite the other!` |
| `cyanrip_main.c:2134` | `Tracks:` |
| `cyanrip_main.c:2144` | `Track %i info:` |
| `cyanrip_main.c:2162` | `Error initializing decoder: %s` |
| `cyanrip_main.c:2171` | `Error initializing encoder: %s` |
| `cyanrip_main.c:2207` | `Error encoding: %s` |
| `cyanrip_main.c:2227` | `Invalid rip index %i, list has %i tracks!` |
| `cyanrip_main.c:2309` | `Error ripping: %s` |
| `discid.c:31` | `Unable to init SHA for DiscID: %s!` |
| `musicbrainz.c:116` | `Invalid disc number %i, release only has %i CDs` |
| `musicbrainz.c:121` | `Got empty medium list.` |
| `musicbrainz.c:127` | `No mediums match DiscID!` |
| `musicbrainz.c:155` | `Medium has no track list.` |
| `musicbrainz.c:193` | `Could not connect to MusicBrainz.` |
| `musicbrainz.c:201` | `Missing DiscID!` |
| `musicbrainz.c:212` | `MusicBrainz query failed: %s` |
| `musicbrainz.c:219` | `Connection failed, try again? Or disable via -N` |
| `musicbrainz.c:224` | `Error fetching/requesting/auth, this shouldn't happen.` |
| `musicbrainz.c:247` | `MusicBrainz lookup failed: DiscID has no associated releases.` |
| `musicbrainz.c:255` | `MusicBrainz lookup failed: no releases found for DiscID.` |
| `musicbrainz.c:259` | `Multiple releases found in database for DiscID %s:` |
| `musicbrainz.c:280` | `%i (ID: %s): %s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s` |
| `musicbrainz.c:294` | `Please specify which release to use by adding the -R argument with an index or ID.` |
| `musicbrainz.c:299` | `Invalid release index %i specified, only have %i releases!` |
| `musicbrainz.c:317` | `Release ID %s not found in release list for DiscID %s!` |
| `musicbrainz.c:348` | `Found MusicBrainz release: %s - %s` |
| `musicbrainz.c:362` | `MusicBrainz lookup failed, but DiscID has a matching stub, consider verifying the data and creating a release here:` |
| `musicbrainz.c:366` | `Unable to find release info for this CD, and metadata hasn't been manually added!` |
| `musicbrainz.c:370` | `Unable to find metadata for this CD, but metadata has been manually specified, continuing.` |
| `musicbrainz.c:376` | `Please help improve the MusicBrainz DB by submitting the disc info via the following URL:` |
| `musicbrainz.c:382` | `To continue add metadata via -a or -t, or ignore via -N!` |
| `naming.c:123` | `Error parsing string: %s!` |
| `naming.c:215` | `Invalid scheme syntax, unterminated \"{\"!` |
| `naming.c:229` | `Invalid scheme syntax, no \"#\"!` |
| `naming.c:243` | `Invalid scheme syntax, no terminating \"#\"!` |
| `naming.c:259` | `Invalid condition syntax!` |

**268 distinct stable lines.**

Field order within a block is fixed and is part of the contract. The golden
reference log in the handshake package is the authoritative example.

### P2a - Composed lines

Lines assembled into a buffer by a run of `snprintf()` and emitted through a
bare `"%s"`. The emitting call site shows a consumer nothing, so the pieces
are reconstructed here from the `snprintf` formats that build the buffer, in
source order. Segments after the first are conditional.

**`cyanrip_main.c:870`** - reaches logfile: **not directly** - see legend

| # | Segment |
|---|---|
| 0 | `Ripping%strack %i, progress - %0.2f%%` |
| 1 | `, ETA - %ih %im` |
| 2 | `, ETA - %im` |
| 3 | `, ETA - %llds` |
| 4 | `, errors - %i` |
| 5 | ` ` |

Segment 0 is always present; the rest are appended conditionally. This is
**stable API**: the progress bar and ETA of at least one consumer are
driven by it.

**`cyanrip_main.c:2056`** - reaches logfile: yes

Not derivable: the buffer is not built by `snprintf` in this function.
It emits arbitrary text - here, the generated CUE sheet echoed back to
the terminal a line at a time. **Do not pattern-match this row**; a
pattern built from its `"%s"` would match every line in the log.

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
| `cyanrip_main.c:804` | `\r` | **not directly** - see legend |
| `cyanrip_main.c:870` | `%s` | **not directly** - see legend |
| `cyanrip_main.c:951` | `Flushing encoders...` | **not directly** - see legend |
| `cyanrip_main.c:993` | `Force quitting` | **not directly** - see legend |
| `cyanrip_main.c:996` | `\rTrying to quit` | **not directly** - see legend |
| `cyanrip_main.c:1249` | `libcdio %s: %s` | **not directly** - see legend |
| `cyanrip_main.c:1466` | `Log \"%s\" checksum valid.` | **not directly** - see legend |
| `cyanrip_main.c:1469` | `Log \"%s\" checksum mismatch, the file has been modified!` | **not directly** - see legend |
| `cyanrip_main.c:1473` | `Log \"%s\" has data after the checksum, the file has been modified!` | **not directly** - see legend |
| `cyanrip_main.c:1477` | `No FUN512 checksum found in \"%s\"!` | **not directly** - see legend |
| `cyanrip_main.c:1481` | `Couldn't read \"%s\"!` | **not directly** - see legend |
| `stall_watchdog.c:147` | `Still reading track %i - the read for LSN %i has not returned after %llds` | **not directly** - see legend |
| `stall_watchdog.c:221` | `Track %i - the read for LSN %i returned after %llds` | **not directly** - see legend |

Also unstable, and **not ours**: the loudness block FFmpeg's `ebur128` filter
prints (`Integrated loudness`, `Loudness range`, `Sample peak:`, `True peak:`, ...). That wording
belongs to libavfilter and moves when FFmpeg does. Prefer the
`Sample peak level:` and `True peak level:` lines in P2, which are ours,
are gated on a completed rip, and each say which peak they report.

## P4 - Exit codes

| Code | Meaning |
|---|---|
| `0` | Success: completed rip, `-I`, `-J`, `-h`, `-v`, or a `-Y` that validated |
| `1` | Every failure, without exception |

Distinct exit values found in the tree: `1`.

**There is no per-failure-class code.** Classification must come from the text,
which is why P5 exists. No non-zero exit is silent: argument parse failures
print before returning, and every other `return 1` in `main()` is preceded by a
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
| `cache_probe.c:116` | `Cache probe:    unknown (out of memory)` | control flow | yes |
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
| `cyanrip_encode.c:839` | `Could not alloc swr context!` | wording | yes |
| `cyanrip_encode.c:857` | `Could not init swr context!` | wording | yes |
| `cyanrip_encode.c:1032` | `Error while encoding: %s!` | both | yes |
| `cyanrip_encode.c:1054` | `Error encoding: %s!` | both | yes |
| `cyanrip_encode.c:1085` | `Error pushing packet to FIFO: %s!` | both | yes |
| `cyanrip_encode.c:1092` | `Error writing packet: %s!` | both | yes |
| `cyanrip_encode.c:1122` | `Error writing to file: %s!` | both | yes |
| `cyanrip_encode.c:1245` | `Codec not found (not compiled in lavc?)!` | control flow | yes |
| `cyanrip_encode.c:1254` | `Unable to init output avctx!` | both | yes |
| `cyanrip_encode.c:1265` | `Could not open output codec context!` | both | yes |
| `cyanrip_encode.c:1272` | `Couldn't copy codec params!` | both | yes |
| `cyanrip_encode.c:1279` | `Couldn't open %s: %s! Invalid folder name? Try -D <folder>.` | both | yes |
| `cyanrip_main.c:211` | `No device specified and unable to get default device!` | both | yes |
| `cyanrip_main.c:219` | `Unable to open device: %s` | both | yes |
| `cyanrip_main.c:228` | `Unable to init cddap context!` | wording | yes |
| `cyanrip_main.c:230` | `cdio: \"%s\"` | control flow | yes |
| `cyanrip_main.c:244` | `Unable to open device!` | both | yes |
| `cyanrip_main.c:253` | `Device does not support changing speeds!` | control flow | yes |
| `cyanrip_main.c:270` | `Unable to init paranoia!` | both | yes |
| `cyanrip_main.c:315` | `Invalid number of tracks: %i!` | both | yes |
| `cyanrip_main.c:338` | `CDIO returned invalid track %i end LSN` | control flow | yes |
| `cyanrip_main.c:491` | `cdio error: %s` | control flow | yes |
| `cyanrip_main.c:498` | `Frame read failed!` | control flow | yes |
| `cyanrip_main.c:585` | `Stopping, offset finding incomplete!` | wording + goto end | yes |
| `cyanrip_main.c:670` | `Unable to read track %i subchannel info!` | wording | yes |
| `cyanrip_main.c:743` | `Error in decoding/sending frame: %s` | both | yes |
| `cyanrip_main.c:755` | `Drive media changed, stopping!` | both | yes |
| `cyanrip_main.c:786` | `Stopping, ripping incomplete!` | wording | yes |
| `cyanrip_main.c:904` | `Done; (%i out of %i matches for current checksum %08X)` | goto finalize_ripping | yes |
| `cyanrip_main.c:910` | `Done; (no matches found, but hit repeat limit of %i)` | goto finalize_ripping | yes |
| `cyanrip_main.c:941` | `Error in encoding: %s` | wording + goto end | yes |
| `cyanrip_main.c:957` | `Error sending flush signal to encoders: %s` | wording | yes |
| `cyanrip_main.c:993` | `Force quitting` | control flow | **not directly** - see legend |
| `cyanrip_main.c:1477` | `No FUN512 checksum found in \"%s\"!` | control flow | **not directly** - see legend |
| `cyanrip_main.c:1481` | `Couldn't read \"%s\"!` | both | **not directly** - see legend |
| `cyanrip_main.c:1533` | `Invalid paranoia level %i must be between 0 and %i!` | both | yes |
| `cyanrip_main.c:1546` | `Invalid max coverart size %i (must be 250, 500, 1200 or -1)` | both | yes |
| `cyanrip_main.c:1558` | `Invalid sanitation method %s` | both | yes |
| `cyanrip_main.c:1570` | `Invalid release index %i!` | both | yes |
| `cyanrip_main.c:1581` | `Missing discnumber` | both | yes |
| `cyanrip_main.c:1586` | `Invalid discnumber %i` | both | yes |
| `cyanrip_main.c:1593` | `Invalid totaldiscs %i` | both | yes |
| `cyanrip_main.c:1597` | `discnumber %i is larger than totaldiscs %i` | control flow | yes |
| `cyanrip_main.c:1618` | `Invalid format \"%s\"` | both | yes |
| `cyanrip_main.c:1623` | `Duplicated format \"%s\"` | control flow | yes |
| `cyanrip_main.c:1638` | `Duplicated rip idx %i` | control flow | yes |
| `cyanrip_main.c:1652` | `Missing track idx for pregap` | both | yes |
| `cyanrip_main.c:1657` | `Invalid track idx for pregap: %i` | both | yes |
| `cyanrip_main.c:1663` | `Missing pregap action` | both | yes |
| `cyanrip_main.c:1671` | `Invalid pregap action %s` | both | yes |
| `cyanrip_main.c:1702` | `No cover art location specified for \"%s\"` | both | yes |
| `cyanrip_main.c:1711` | `Invalid track idx for cover art: %i` | both | yes |
| `cyanrip_main.c:1717` | `Cover art already specified for track idx %i!` | control flow | yes |
| `cyanrip_main.c:1729` | `Cover art \"%s\" already specified!` | control flow | yes |
| `cyanrip_main.c:1735` | `Too many cover arts specified!` | control flow | yes |
| `cyanrip_main.c:1745` | `Directory name scheme must contain {format} with multiple output formats!` | control flow | yes |
| `cyanrip_main.c:1750` | `-J (only generate a CUE sheet) cannot be used with -I (only print info)!` | both | yes |
| `cyanrip_main.c:1788` | `Offset is unset! To continue with an offset of 0, run with -s 0!` | goto end | yes |
| `cyanrip_main.c:1913` | `Error reading album tags: %s` | both | yes |
| `cyanrip_main.c:2005` | `Invalid track number %i, list has %i tracks!` | both | yes |
| `cyanrip_main.c:2018` | `Missing \"=\" in track metadata \"%s\"` | both | yes |
| `cyanrip_main.c:2034` | `Error reading track tags: %s` | both | yes |
| `cyanrip_main.c:2056` | `%s` | goto end | yes |
| `cyanrip_main.c:2162` | `Error initializing decoder: %s` | both | yes |
| `cyanrip_main.c:2171` | `Error initializing encoder: %s` | both | yes |
| `cyanrip_main.c:2207` | `Error encoding: %s` | wording + goto end | yes |
| `cyanrip_main.c:2227` | `Invalid rip index %i, list has %i tracks!` | both | yes |
| `cyanrip_main.c:2309` | `Error ripping: %s` | wording + goto end | yes |
| `diagnostics.c:437` | `Couldn't open diagnostics path \"%s\" for writing!` | wording | **not directly** - see legend |
| `discid.c:31` | `Unable to init SHA for DiscID: %s!` | wording | yes |
| `musicbrainz.c:116` | `Invalid disc number %i, release only has %i CDs` | both | yes |
| `musicbrainz.c:121` | `Got empty medium list.` | control flow | yes |
| `musicbrainz.c:193` | `Could not connect to MusicBrainz.` | both | yes |
| `musicbrainz.c:201` | `Missing DiscID!` | wording | yes |
| `musicbrainz.c:224` | `Error fetching/requesting/auth, this shouldn't happen.` | both | yes |
| `musicbrainz.c:247` | `MusicBrainz lookup failed: DiscID has no associated releases.` | goto end_meta | yes |
| `musicbrainz.c:255` | `MusicBrainz lookup failed: no releases found for DiscID.` | goto end_meta | yes |
| `musicbrainz.c:294` | `Please specify which release to use by adding the -R argument with an index or ID.` | control flow | yes |
| `musicbrainz.c:299` | `Invalid release index %i specified, only have %i releases!` | both | yes |
| `musicbrainz.c:317` | `Release ID %s not found in release list for DiscID %s!` | control flow | yes |
| `musicbrainz.c:362` | `MusicBrainz lookup failed, but DiscID has a matching stub, consider verifying the data and creating a release here:` | control flow | yes |
| `musicbrainz.c:366` | `Unable to find release info for this CD, and metadata hasn't been manually added!` | both | yes |
| `musicbrainz.c:370` | `Unable to find metadata for this CD, but metadata has been manually specified, continuing.` | wording | yes |
| `naming.c:123` | `Error parsing string: %s!` | wording | yes |
| `naming.c:215` | `Invalid scheme syntax, unterminated \"{\"!` | both | yes |
| `naming.c:229` | `Invalid scheme syntax, no \"#\"!` | both | yes |
| `naming.c:243` | `Invalid scheme syntax, no terminating \"#\"!` | both | yes |
| `naming.c:259` | `Invalid condition syntax!` | both | yes |

**120 distinct strings.** By evidence: 66 both, 21 control flow, 12 wording, 3 goto end, 14 wording + goto end.

The `control flow` and `both` rows total 87 strings proven reachable on a
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

On **this fork** the genopt message is routed through `cyanrip_log()`, so
it reaches stdout, the logfile if one is open, and the `-j` record. That
is a fork property; stock does neither.

