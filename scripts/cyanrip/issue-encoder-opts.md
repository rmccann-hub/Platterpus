<!-- Ready-to-paste GitHub ISSUE body for cyanreg/cyanrip. Sanity-check the flag
     name with the maintainer (IRC #cyanrip / this issue) BEFORE building the PR,
     since the wiring touches getopt + the settings structs + --help. Design
     detail: docs/cyanrip-soft-fork.md §3. -->

Title: Allow passing arbitrary libavcodec encoder options (e.g. FLAC `compression_level`) instead of only the hardcoded per-format default

`setup_out_avctx()` sets `avctx->compression_level = cfmt->compression_level`
from the format table and `cyanrip_init_track_encoding()` calls
`avcodec_open2(…, NULL)`, so there's no way to change the FLAC compression level
or set any other libavcodec encoder option. For archival vs. speed trade-offs
(and codec tuning generally) it'd help to expose the encoder option surface.

**Proposal:** a repeatable `-O key=value` that builds an `AVDictionary` passed to
`avcodec_open2` (per track, via `av_dict_copy`). Generic across codecs; defaults
unchanged when unused; unknown keys warn rather than abort. Happy to open a PR if
this direction is acceptable — worth a quick sanity-check on the flag
name/behaviour first.
