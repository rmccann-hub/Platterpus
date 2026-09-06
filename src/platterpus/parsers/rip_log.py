"""Parse a whipper-FORMAT rip `.log` file into a RipLog dataclass.

This is the legacy whipper log format, kept for old logs and test
fixtures; the current cyanrip backend has its own parser that reuses the
dataclasses defined here. Format verified against a real whipper 0.7.4+
log from whipper-team's own test fixtures
(tests/fixtures/rip_log_real_whipper_0_7.log).

Structure (YAML-style indented mapping):

    Log created by: whipper X.Y.Z (...)
    Log creation date: YYYY-MM-DDThh:mm:ssZ

    Ripping phase information:
      Drive: <vendor> <model> (revision <rev>)
      Extraction engine: ...
      Defeat audio cache: true|false
      Read offset correction: <int>
      Overread into lead-out: true|false
      Gap detection: ...
      CD-R detected: true|false

    CD metadata:
      Release:
        Artist: ...
        Title: ...
      CDDB Disc ID: ...
      MusicBrainz Disc ID: ...
      MusicBrainz lookup URL: ...

    TOC:
      1:
        Start: ...
        Length: ...
        Start sector: ...
        End sector: ...

    Tracks:
      1:
        Filename: <path>
        Peak level: 0.xxxxxx
        Pre-emphasis: <empty>|yes|no
        Extraction speed: N.N X
        Extraction quality: NN.NN %
        Test CRC: XXXXXXXX
        Copy CRC: XXXXXXXX
        AccurateRip v1:
          Result: Found, exact match | Track not present in AccurateRip database | ...
          Confidence: N
          Local CRC: XXXXXXXX
          Remote CRC: XXXXXXXX
        AccurateRip v2:
          (same fields)
        Status: Copy OK

    Conclusive status report:
      AccurateRip summary: ...
      Health status: ...
      EOF: End of status report

    SHA-256 hash: <hex>

We don't pull in a YAML parser — the format is regular enough that a
state-machine with named-group regexes handles it cleanly. Per
CLAUDE.md, the parser degrades gracefully on unexpected input rather
than crashing.

The captured `RippingInfo` block intentionally mirrors what EAC's log
captures (drive, read offset, cache defeat, gap detection) so the GUI
can surface an archival summary comparable to EAC's. See
docs/eac-parity.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from platterpus.safe_int import int_or_none


@dataclass(frozen=True)
class RippingInfo:
    """Drive and rip-engine settings captured at the time of rip.

    Mirrors EAC's "Used drive" / "Read offset correction" / "Defeat
    audio cache" archival block — the fields most relevant to whether
    a rip is bit-perfect and reproducible.
    """

    drive: str = ""
    extraction_engine: str = ""
    defeat_audio_cache: bool | None = None
    read_offset_correction: int | None = None
    overread_lead_out: bool | None = None
    gap_detection: str = ""
    cd_r_detected: bool | None = None
    # Whether the drive can change its read speed (cyanrip's "Speed:" banner
    # line). False = the drive reported speed as "unchangeable", so cyanrip
    # ABORTS the rip if handed `-S` — the read-speed ladder must not send it
    # (real-hardware finding, 2026-07-01: the BDR-209D reports unchangeable).
    # True = a speed was set or reported "changeable"; None = unknown/whipper log.
    speed_changeable: bool | None = None
    # --- fields EAC prints in its archival header, which cyanrip also reports
    # under different names. Captured so the EAC-layout export can fill EAC's
    # own rows from measured data instead of omitting them (2026-07-27).
    #
    # The disc's artist and title, for EAC's "Artist / Album" header line.
    album: str = ""
    album_artist: str = ""
    # cyanrip's "C2 errors:" line → EAC's "Make use of C2 pointers". True only
    # when C2 is actually in use; False when the drive doesn't support it (the
    # BDR-209D reports "unsupported by drive"); None when unreported.
    c2_pointers: bool | None = None
    # cyanrip's "Paranoia level:" → EAC's "Read mode" (Secure vs Burst). Kept as
    # the raw level text so the renderer decides the wording, not the parser.
    paranoia_level: str = ""
    # cyanrip's "Overread mode:" text verbatim (e.g. "fill with silence in
    # lead-in/lead-out"). EAC asks two INDEPENDENT questions — whether it
    # overread, and whether it padded missing offset samples with silence — and
    # this one line answers both. Deriving the second as the complement of the
    # first happened to work for cyanrip and is not generally true, so the text
    # is kept (review finding, 2026-07-28).
    overread_mode: str = ""
    # cyanrip's "Outputs:" row (e.g. "flac", or "flac,mp3"). EAC's "Used output
    # format" was hardcoded to FLAC, which is a false statement in a
    # checksum-attested document for a WavPack/MP3/WAV rip — Platterpus supports
    # all four (review finding, 2026-07-28).
    output_formats: str = ""


@dataclass(frozen=True)
class AccurateRipResult:
    """One of the two AccurateRip checks per track (v1 or v2)."""

    version: int
    result: str = ""  # "Found, exact match" / etc.
    confidence: int | None = None
    local_crc: str | None = None  # uppercase hex
    remote_crc: str | None = None  # uppercase hex


@dataclass(frozen=True)
class TrackResult:
    """One track's results from the rip log."""

    number: int
    filename: str = ""
    peak_level: float | None = None
    pre_emphasis: bool | None = None
    extraction_speed: float | None = None  # in X (drive multiplier)
    extraction_quality: float | None = None  # percentage 0..100
    test_crc: str = ""
    copy_crc: str = ""
    status: str = ""
    accuraterip_v1: AccurateRipResult | None = None
    accuraterip_v2: AccurateRipResult | None = None
    # cyanrip's offset-variant AccurateRip match ("Accurip 450:"). A pressing
    # whose start is shifted by the common +450-frame offset still matches the
    # database here — cyanrip reports the track "partially accurately ripped".
    # It's surfaced as data (not folded into the verified rule) so the verdict
    # never over-claims a plain match; see docs/architecture.md.
    accuraterip_offset: AccurateRipResult | None = None
    # The verbatim text of cyanrip's per-track "Accurip:" status row — e.g.
    # "disc found in database (max confidence: 200)", "disabled", "error". The ONLY
    # thing in the log that says whether a database lookup happened at all; without
    # it, a disc nobody looked up was reported as "in DB, no match" (audit,
    # 2026-07-31). None for whipper logs and any log that omits the row.
    accuraterip_lookup: str | None = None
    #: cyanrip's per-track paranoia status counts (READ / VERIFY / OVERLAP /
    #: FIXUP_ATOM), empty when the log carries none. The fork added these at our
    #: request; our parser dropped them for months because its header pattern was
    #: anchored at column 0 and theirs are indented inside the track block.
    paranoia_counts: dict[str, int] = field(default_factory=dict)
    #: cyanrip's `Scope:` note for those counts, verbatim — it says which reads the
    #: numbers cover when a track was re-read. "" when the log carries none, which
    #: is every rip that converged on its first read.
    paranoia_scope: str = ""
    # How many read passes cyanrip needed for this track (its "(after N rips)"
    # suffix). 1 = clean single pass; higher means secure re-reads (-Z N) were
    # needed — the clearest per-track signal of a marginal read region.
    rip_count: int | None = None
    # cyanrip's secure re-read (-Z N) verdict for this track: True when N reads'
    # checksums agreed ("Done; (N out of N matches)"); False when it hit the
    # repeat limit WITHOUT any two reads agreeing ("no matches found, but hit
    # repeat limit of N"). This is the RELIABLE per-track read-instability signal
    # — cyanrip's whole-disc "Ripping errors" count stays 0 even when a track
    # never converges (real-hardware finding, 2026-07-01). None when -Z was off
    # or the log predates this field. NOTE it is orthogonal to
    # `accuraterip_offset`: a fully-converged (stable) read can still match only
    # the offset-variant pressing — that's a pressing difference, NOT instability
    # — so the two are recorded separately and never conflated.
    secure_rerip_converged: bool | None = None
    # ReplayGain / loudness tags cyanrip computed and wrote into the FLAC (a
    # dict of the raw "REPLAYGAIN_*"/"R128_TRACK_GAIN" values, as strings). The
    # JSON report is the only machine-readable record of what was tagged without
    # re-reading every file. Empty for whipper logs / when not present.
    replaygain: dict[str, str] = field(default_factory=dict)
    # --- absolute disc geometry, for EAC's "TOC of the extracted CD" table.
    # cyanrip prints these per track as "Start LSN:" / "End LSN:" / "Pregap LSN:"
    # (LSN == sector). EAC's Start and Length columns are derived from them
    # exactly — verified against a real EAC log of the same disc (2026-07-27).
    # None when the log didn't report them (whipper, or a partial log).
    start_sector: int | None = None
    end_sector: int | None = None
    # The pre-gap's LENGTH in sectors, for EAC's "Pre-gap length" row. This is a
    # DERIVED value, not a number cyanrip prints: see `pregap_start_lsn` below.
    # 0 means the ripper measured "none"; None means it reported nothing usable.
    pregap_sectors: int | None = None
    # The pre-gap's absolute START position — the number on cyanrip's
    # "Pregap LSN:" row, which is where INDEX 00 begins and is NOT a length.
    # Recorded separately because reading that row's number as a length is a real
    # shipped bug: on the reference pressing, track 2's INDEX 00 sits at LSN 14327
    # against a Start LSN of 14487, so the true gap is 160 sectors (2.13 s) and the
    # EAC-layout log archived 3 m 11 s — an 89x over-claim, and one that scales
    # with the track's position on the disc (audit, 2026-07-31). `pregap_sectors`
    # above is `start_sector - pregap_start_lsn`, which is exactly how cyanrip
    # computes the duration it prints in its own `(duration: …)` suffix.
    pregap_start_lsn: int | None = None
    # Which of the three things the ripper actually said about this track's
    # pre-gap. **`unknown` is not `none`.**
    #
    #   ""        the ripper printed no Pregap row at all
    #   "known"   a position was reported → `pregap_start_lsn` is set
    #   "none"    measured, and there is no pre-gap
    #   "unknown" the ripper TRIED and could not tell (sub-channel unreadable,
    #             or CRC mismatches) — `pregap_unknown_reason` says which
    #
    # Before this existed, `unknown` did not match the LSN pattern at all, so it
    # fell through to `pregap_start_lsn=None, pregap_sectors=None` — byte-identical
    # to a genuine "none". "We could not determine whether this track has a
    # pre-gap" and "this track has no pre-gap" are different archival claims, and
    # collapsing them is the same class of error as `Accurip: disabled` rendering
    # as "in DB, no match". Third instance of that class (2026-08-02).
    pregap_state: str = ""
    pregap_unknown_reason: str = ""
    # The pre-gap length the ripper states OUTRIGHT ("Pregap length: N frames"),
    # as opposed to the one we derive. Fork-only, and **authoritative when
    # present** — it is the only field that can express track 1, whose pre-gap is
    # the 150-frame lead-in PLUS any TOC-declared gap. On the fork's reference
    # disc track 1 reads `Pregap LSN: 0` / `Start LSN: 150` / `Pregap length: 300`,
    # and the `Gaps:` block confirms a 150-frame TOC pre-gap: 150 + 150 = 300. A
    # derivation of `start - lsn` gets 150 there and is simply wrong.
    pregap_length_frames: int | None = None
    # How the ripper found it: "TOC" (declared), "lead-in" (track 1's standard
    # two seconds), or "sub-channel" (a Q-subchannel scan found a gap the TOC does
    # NOT declare — the EAC-parity case, and the whole point of upstream PR #115).
    # Provenance we previously had to infer; empty on stock cyanrip.
    pregap_source: str = ""
    # --- fields that only a FORK of cyanrip fills (see the "fork-only" block in
    # parsers/cyanrip_log.py, and docs/cyanrip-upstream.md Part A §2.1/§2.3).
    # The deployed cyanrip 0.9.3 prints none of these, so they stay None there and
    # every surface must behave exactly as it does today — that is the whole
    # contract: ONE Platterpus build reads both the deployed ripper and the fork.
    #
    # How long the ripper spent extracting this track, in seconds. NOT the same
    # thing as `extraction_speed` (a multiple of 1x read speed): a wall-clock
    # elapsed is what cyanrip is most likely to print, and the speed multiple is
    # what EAC's row wants. We deliberately do NOT derive one from the other —
    # see `_track_block` in eac_log_export for why that would be a guess.
    extraction_elapsed_seconds: float | None = None
    # Frames of SILENCE the ripper appended to this track because it could not
    # read the disc that far ("Appended:    2 frames of silence"). cyanrip 0.9.3
    # DOES print this — on the last track, when overread is off — and we simply
    # discarded it until 2026-07-31. It is an archival-fidelity statement of the
    # first order: those final frames are fabricated, not disc audio. 0 and None
    # are different answers ("measured: none" vs "not reported"), as everywhere
    # else in this dataclass.
    appended_silence_frames: int | None = None


@dataclass(frozen=True)
class RipLog:
    """The full parsed log."""

    log_creator: str = ""
    # cyanrip's build tag from its version banner — "release", "fork", a
    # `git describe` string. Kept out of `log_creator` deliberately: it is the ONLY
    # thing that tells an archival log which BINARY produced the rip, and two logs
    # of the same disc from an official build and a local fork can differ in
    # pre-gap metadata and peak values while both claiming "cyanrip 0.9.3.1"
    # (audit, 2026-07-31). Empty when the banner carries no parenthetical.
    ripper_build: str = ""
    creation_date: str = ""
    ripping_info: RippingInfo = field(default_factory=RippingInfo)
    tracks: tuple[TrackResult, ...] = ()
    accuraterip_summary: str = ""
    health_status: str = ""
    sha256_hash: str = ""
    # cyanrip-only finish-report extras (empty/absent for whipper logs):
    # "Tracks ripped partially accurately: X/Y" — tracks that matched only the
    # offset-variant (see TrackResult.accuraterip_offset). This is OUR sentence,
    # derived from the per-track results rather than paraphrased from the ripper's
    # fraction, because the fraction's denominator changed meaning between fork
    # builds (cyanrip_log.render_partially_accurate_summary).
    partially_accurate_summary: str = ""
    # The ripper's own fraction, verbatim — "1/1" on builds up to e61e75a, "1/14" on
    # f5e11ba and later for the same disc. Kept alongside our sentence because a
    # rendered sentence cannot be turned back into the number the binary printed, and
    # a reader comparing two logs of one disc needs to see the raw values.
    partially_accurate_reported: str = ""
    # "Total time: HH:MM:SS.mmm" from the start report — the disc's AUDIO length,
    # not the rip's wall-clock (which only the GUI measures; see rip_timing).
    disc_duration: str = ""
    # cyanrip fork only: the command line the ripper itself reports receiving.
    # We separately record the argv we spawned it with; when those two disagree
    # something between us mangled an argument, and that gap was previously
    # invisible from either end.
    invoked_as: str = ""
    #: FORK-ONLY provenance, verbatim from the binary: which handshake round it
    #: was BUILT from, derived at its build time from its own round files. A build
    #: from an open-round tree says so permanently. Independent of our
    #: `handshake_approval` check, which compares banners against what *we*
    #: believe was approved — this is what their build system recorded, and it
    #: cannot be stale relative to the binary because it is compiled into it.
    handshake_note: str = ""
    #: FORK-ONLY: who the ripper was TOLD its caller was. Their log states in as
    #: many words that this is reported by the caller and not verified, so it is
    #: provenance, never verification. `not identified (no --consumer given)`
    #: until we ship the flag — itself the fact worth carrying, since a log with
    #: no consumer cannot be attributed to us at all.
    consumer: str = ""
    # The ripper's own "Rip completed:" footer. **Tri-state.** None = the footer
    # is absent, which is exactly what a killed rip's log looks like — never
    # read it as False ("finished, and reported failure"). The fork confirms
    # (handshake round 4, Q10) this footer is the only structural difference
    # between a truncated log and a short one, because the cue cannot tell.
    rip_completed: bool | None = None
    #: Where an interrupted rip stopped, verbatim — e.g. `track 1, mid-read` or
    #: `between tracks, no read in progress`. None when the log carries no such
    #: line, which is every completed rip and every log written before the fork
    #: added it (round 13, answering our round-12 ask).
    interrupted_at: str | None = None
    rip_completed_tracks: int | None = None
    rip_completed_total: int | None = None
    #: Why it did not complete, in the ripper's own words ("interrupted by
    #: user"). Empty on a completed rip and when the footer is absent.
    rip_completed_reason: str = ""
    #: FORK-ONLY. The stall watchdog's disc-level verdict, verbatim — e.g.
    #: ``none (no read exceeded 10s)``. ``""`` means the ripper did not print the
    #: line at all (stock cyanrip never does), which is a THIRD state: "no stalls
    #: measured" and "stalls not measured" are different claims and must not render
    #: the same way.
    #:
    #: Text, not a parsed count, on purpose: we have only ever seen the ``none``
    #: shape, and a regex for the populated one would encode our guess at the fork's
    #: wording. That guess is what put ``merged`` in the gap matcher for two rounds.
    read_stalls: str = ""
    #: FORK-ONLY. How many reads exceeded the stall threshold, parsed out of
    #: :attr:`read_stalls`. **Tri-state**, and all three states are real answers:
    #:
    #: * ``0`` the ripper measured and found none;
    #: * ``N > 0`` that many reads stalled — the disc needed exceptional effort, and
    #:   this is the value that raises an enumerated ``issues[]`` entry;
    #: * ``None`` not measured, not reported, or a shape we did not recognise. Stock
    #:   cyanrip lands here (it prints no line), and so does the fork's own
    #:   ``unknown (stall reporting disabled with -k 0)``.
    #:
    #: The verbatim :attr:`read_stalls` text is the authoritative record and is never
    #: replaced by this. The fork published these shapes derived from the code that
    #: prints them and pinned each with ``strcmp`` (round 7 lap 14, D1), but **no
    #: build has yet printed a populated one anywhere** — so an unrecognised shape
    #: must degrade to ``None`` beside intact text, never to ``0``.
    read_stalls_count: int | None = None
    # cyanrip's "Paranoia status counts" block (READ/VERIFY/FIXUP_ATOM/OVERLAP/…)
    # — error-correction activity. High counts explain a slow, re-read-heavy rip.
    paranoia_counts: dict[str, int] = field(default_factory=dict)
    # cyanrip's "Album Loudness Summary" block (integrated LUFS, LRA, true peak)
    # — the whole-disc loudness, as a dict of strings. Empty when absent.
    album_loudness: dict[str, str] = field(default_factory=dict)
    # cyanrip's own log signature ("Log FUN512: <base64>") — its analogue to
    # EAC's signed log checksum. A different algorithm from `sha256_hash`, so
    # kept as its own field. Empty for whipper logs.
    log_checksum: str = ""
    # The MusicBrainz Disc ID (cyanrip's "DiscID:" line) and the freedb/CDDB
    # Disc ID ("CDDB ID:"). BOTH are computed purely from the disc's Table Of
    # Contents, so they are the truest "is this the SAME physical disc?" key —
    # stable across re-rips and independent of any MusicBrainz *release* edit
    # (which the release id is not). The re-rip comparison (rip_compare) keys on
    # the MB Disc ID first, so these are surfaced into the JSON report's `rip`
    # block. Empty for whipper logs / when cyanrip didn't print them.
    disc_id: str = ""
    cddb_id: str = ""
    # The MusicBrainz RELEASE id the ripper resolved and USED, read off its own
    # header — NOT the id we sent, which is the point. We hand the whole tag set as
    # one colon-delimited `-a` blob, so this is the witness that its parse of that
    # blob put our release id where we meant it to go; `Invoked as:` can only show
    # what it received. A disagreement with `disc.musicbrainz_release_id` is a
    # finding, and the report raises it as one. Empty for whipper logs, and empty
    # whenever no release id reached the ripper (an unknown-disc rip).
    release_id: str = ""
    # True when the log text itself is evidence that the ripper was killed while
    # still writing it — NOT merely that the rip was cancelled.
    #
    # cyanrip opens its logfile block-buffered, so a completed track's record
    # only reaches disk when a 4 KiB stdio block fills or the process exits
    # cleanly. Kill it and the tail of the buffer is lost. On the rig
    # (2026-08-01) that produced a file of exactly 4096 bytes ending mid-token at
    # `REPLAYGAIN_TRACK_GA`: track 3 had completed and verified against
    # AccurateRip at confidence 200, and was absent from every artifact
    # Platterpus wrote. The data was never lost — it was in our captured stdout
    # the whole time — but the report was built from the file.
    #
    # This flag exists because the *silence* was the real defect. A truncated
    # log is indistinguishable, from the parse alone, from a rip that simply
    # stopped earlier: both yield fewer tracks and no finish report. Saying so
    # turns "12 tracks were never ripped" (wrong, and unfalsifiable) into "this
    # log was cut off, so what it does NOT say proves nothing".
    log_truncated: bool = False
    # Set when the LAST track block was the one cut off — its record claims a
    # status and a CRC but never reached its `File(s):` line. That track's data
    # is present but incomplete, which is a different problem from a track that
    # is missing outright, and a consumer counting "verified" tracks should know.
    last_track_incomplete: bool = False


# --- AccurateRip "is this track verified?" — the ONE shared definition -------
#
# Every UI surface that reports trust (the verdict banner, the disc-info panel,
# the status-line fidelity summary) MUST agree on what "verified" means, or two
# panes on the same screen can contradict each other — which destroys the
# "prove it" promise. These two pure, Qt-free helpers are that single source of
# truth; they live here because this module owns the AR dataclasses.


def accuraterip_is_match(ar: object) -> bool:
    """True when one AccurateRip result is a positive database match.

    AccurateRip *confidence* is how many submitted rips share this track's CRC,
    so a genuine match is always ``>= 1``; a "not present"/"no match" track has
    confidence ``None`` (or, in some logs, ``0``). Keying on ``confidence >= 1``
    is therefore **format-agnostic and honest**: it counts whipper's
    "Found, exact match" and cyanrip's "accurately ripped, confidence N" the
    same way (cyanrip's text has no "exact match" substring — a string check
    would silently miss every cyanrip verification), and it can only ever
    under-claim, never fabricate a match. Reads via ``getattr`` so it accepts
    any AR-result shape and never raises.

    **An all-zero local CRC can never be a match, whatever the confidence says.**
    cyanrip prints a caveat on that line and without this guard it parsed as a
    confidence-200 positive. It matters most on the offset-variant row, where a
    silent or absent track yields `Accurip 450: 00000000` and the cell then
    announced a partially-accurate match for audio nothing was compared against.
    Keying on the zero CRC rather than on cyanrip's wording is the stronger
    invariant: it also covers a backend that omits the caveat (audit, 2026-07-31).

    **That choice has now been paid off, and the wording it avoided has already
    moved.** This docstring used to quote the caveat as *"match found, confidence
    200, but a checksum of 0 is meaningless"*; the fork's round-14 acceptance spec
    reports it reworded to *"no comparison possible, a checksum of 0 is
    meaningless"*, because the old text asserted a match it could not have
    established. A string check written in July would have broken in August. The
    example is dropped rather than updated: quoting a producer's exact wording
    inside a function that deliberately does not depend on it is how the next
    reader concludes it does.
    """
    if ar is None:
        return False
    local_crc = getattr(ar, "local_crc", None)
    # All zeros (any width, with or without a `0x` prefix). The `strip()` must be
    # guarded by a non-empty check: `"".strip("0Xx")` is also `""`, and an EMPTY
    # CRC means "not reported" — a whipper log can carry a real match without one,
    # so treating empty as zero would silently discard genuine verifications. This
    # is under-claiming, which is the direction that costs the user trust in a
    # correct rip, so it is as much a bug as the over-claim above.
    if isinstance(local_crc, str) and local_crc and local_crc.strip("0Xx") == "":
        return False
    confidence = getattr(ar, "confidence", None)
    return confidence is not None and confidence >= 1


def track_accuraterip_verified(track: object) -> bool:
    """True when either of a track's AccurateRip checks is a positive match."""
    return accuraterip_is_match(
        getattr(track, "accuraterip_v1", None)
    ) or accuraterip_is_match(getattr(track, "accuraterip_v2", None))


# --- Per-track read-effort ("this track was hard to read") -------------------
#
# A rip can be reported with zero *hard* errors yet still have needed heavy
# re-reading on a marginal region — the earliest in-rip hint that a track's
# audio may not be reproducible. cyanrip exposes two per-track signals we can
# read from the log today:
#
#   * ``rip_count`` — how many passes the drive took ("(after N rips)"). 1 is a
#     clean single pass; a higher number means the paranoia layer had to re-read.
#   * ``secure_rerip_converged`` — for a ``-Z N`` secure re-read, whether N
#     reads' checksums ever agreed. False = it hit the repeat limit WITHOUT any
#     two reads matching — the reliable "this region isn't reading stably" flag
#     (cyanrip's whole-disc "Ripping errors" stays 0 even then).
#
# NOTE this is a *complement* to, not a replacement for, the cross-rip
# comparison (rip_compare): a disc whose paranoia settles on ONE (wrong) answer
# per pass — no re-reads, no -Z — shows rip_count 1 and converged None, so this
# helper won't flag it. Kept honest in the docs so nobody reads a clean
# read-effort result as "provably reproducible".
#
# **CORRECTED 2026-08-24.** This note used to end "...or per-track paranoia
# counts, which cyanrip only emits disc-wide today (a tracked upstream
# JSON-output ask)". That was false, and the artifact refuting it was committed
# in this repository: the fork's own reference log carries **fourteen** per-track
# `Paranoia status counts:` blocks against one disc-level block, because we asked
# for them (W1) and they built them. Our parser dropped all fourteen — its header
# pattern was anchored at column 0 and theirs are indented — so nobody looking at
# a parsed log could see they existed, and this comment then explained the
# absence as an upstream gap. A missing feature and a dropped field read
# identically from inside the parser; only the artifact tells them apart
# (`CLAUDE.md`: am I answering from the artifact, or from my memory of it?).
#
# They are parsed now and land on `TrackResult.paranoia_counts`. Using them to
# strengthen the flag above is deliberately NOT done here: it needs a threshold,
# a threshold needs evidence from more than one disc, and inventing one would
# swap a documented gap for an undocumented guess. `TASKS.md` carries the
# follow-up now that the data is actually available.

# A track needing this many passes (or more) is called out as "unusually heavy
# re-reading". 2 passes (one re-read) is common and benign on real hardware, so
# the floor is 3 to flag genuinely stubborn regions, not ordinary paranoia.
HEAVY_REREAD_THRESHOLD: int = 3


def track_read_effort_flag(track: object) -> bool:
    """True when a track shows a read-effort warning sign.

    Either its secure re-read never converged (``secure_rerip_converged`` is
    False) or it needed ``HEAVY_REREAD_THRESHOLD`` passes or more. Reads via
    ``getattr`` so it accepts any track shape and never raises.
    """
    if getattr(track, "secure_rerip_converged", None) is False:
        return True
    rip_count = getattr(track, "rip_count", None)
    return isinstance(rip_count, int) and rip_count >= HEAVY_REREAD_THRESHOLD


def tracks_needing_heavy_reread(rip_log: object) -> list[int]:
    """Return the 1-based numbers of tracks that showed a read-effort warning.

    The results-pane footnote and the report's ``read_effort`` issue both read
    this, so they can never disagree. Pure; never raises."""
    flagged: list[int] = []
    for track in getattr(rip_log, "tracks", ()) or ():
        if track_read_effort_flag(track):
            number = getattr(track, "number", None)
            if isinstance(number, int):
                flagged.append(number)
    return flagged


# --- Line-level regexes -----------------------------------------------------

# Top-level section line, e.g. "Tracks:" or "Conclusive status report:".
_TOP_LEVEL_SECTION = re.compile(r"^(?P<name>\w[\w\s]*?):\s*$")

# A track header is JUST a number and a colon, indented. The colon must
# be followed by nothing but whitespace — that's how it differs from a
# normal field line.
_TRACK_HEADER = re.compile(r"^\s+(?P<number>\d+):\s*$")

# AccurateRip v1/v2 sub-section header. Same "nothing after the colon"
# discipline.
_AR_HEADER = re.compile(r"^\s+AccurateRip v(?P<version>\d+):\s*$")

# A general "Key: value" line. `value` may be empty (some fields like
# Pre-emphasis are emitted with an empty value).
_FIELD = re.compile(r"^(?P<indent>\s+)(?P<key>[\w][\w\s\-]*?):\s*(?P<value>.*?)\s*$")

_SPEED = re.compile(r"^(?P<value>-?\d+(?:\.\d+)?)\s*X\s*$")
_QUALITY = re.compile(r"^(?P<value>-?\d+(?:\.\d+)?)\s*%\s*$")

# Mapping from section name (as it appears in the log) to internal state.
_SECTION_NAMES: dict[str, str] = {
    "Ripping phase information": "ripping",
    "CD metadata": "metadata",
    "TOC": "toc",
    "Tracks": "tracks",
    "Conclusive status report": "status",
}


def parse_rip_log(text: str) -> RipLog:
    """Parse the full text of a whipper `.log` file.

    Tolerates absent fields and unexpected lines. Returns a RipLog with
    whatever could be extracted; never raises on malformed input.
    """
    log_creator = ""
    creation_date = ""
    sha256 = ""

    ripping_data: dict[str, str] = {}
    status_data: dict[str, str] = {}

    tracks: list[TrackResult] = []
    current_track: _MutableTrack | None = None
    current_ar: int | None = None

    section: str | None = None  # one of _SECTION_NAMES values, or None.

    for line in text.splitlines():
        # Top-of-file metadata: simple "Key: value" lines at column 0.
        if line.startswith("Log created by:"):
            log_creator = line.split(":", 1)[1].strip()
            continue
        if line.startswith("Log creation date:"):
            creation_date = line.split(":", 1)[1].strip()
            continue
        if line.startswith("SHA-256 hash:"):
            sha256 = line.split(":", 1)[1].strip()
            continue

        # Top-level section header switches state. Note: track headers
        # like "  1:" are indented and won't match this column-0 regex.
        top = _TOP_LEVEL_SECTION.match(line)
        if top and not line.startswith(" "):
            name = top.group("name").strip()
            # Flush in-flight track when leaving the tracks section.
            if section == "tracks" and current_track is not None:
                tracks.append(current_track.build())
                current_track = None
            section = _SECTION_NAMES.get(name)
            current_ar = None
            continue

        if section == "ripping":
            field_match = _FIELD.match(line)
            if field_match:
                ripping_data[field_match.group("key").strip()] = field_match.group(
                    "value"
                ).strip()
            continue

        if section == "status":
            field_match = _FIELD.match(line)
            if field_match:
                status_data[field_match.group("key").strip()] = field_match.group(
                    "value"
                ).strip()
            continue

        if section == "tracks":
            # Track header is just "  N:" with nothing after.
            header = _TRACK_HEADER.match(line)
            if header:
                if current_track is not None:
                    tracks.append(current_track.build())
                # An unusable track number drops the block entirely rather than
                # opening one under a guessed number: `TrackResult.number` is the
                # key every consumer joins on (the verdict, the report, the
                # per-track CRC comparison), so a fabricated number would file
                # this track's results against a different track.
                number = int_or_none(header.group("number"), field="rip-log track")
                current_track = None if number is None else _MutableTrack(number=number)
                current_ar = None
                continue

            ar = _AR_HEADER.match(line)
            if ar and current_track is not None:
                # Same reasoning one level down: the version keys this track's AR
                # sub-dict, so an unusable one skips the sub-section instead of
                # merging v1 and v2 results under a made-up key.
                current_ar = int_or_none(
                    ar.group("version"), field="rip-log AccurateRip version"
                )
                if current_ar is None:
                    continue
                current_track.ar[current_ar] = {}
                continue

            field_match = _FIELD.match(line)
            if field_match and current_track is not None:
                key = field_match.group("key").strip()
                value = field_match.group("value").strip()
                indent = len(field_match.group("indent"))
                # AR sub-fields are indented further than track-level
                # ones (6 spaces vs 4). Once we see a 4-indent field
                # after AR fields, we've left the AR block.
                if current_ar is not None and indent >= 6:
                    current_track.ar[current_ar][key] = value
                else:
                    current_track.fields[key] = value
                    current_ar = None
                continue

        # CD metadata and TOC sections are not used by the GUI; ignore.

    # Flush a track that wasn't followed by a status section.
    if current_track is not None:
        tracks.append(current_track.build())

    return RipLog(
        log_creator=log_creator,
        creation_date=creation_date,
        ripping_info=_build_ripping_info(ripping_data),
        tracks=tuple(tracks),
        accuraterip_summary=status_data.get("AccurateRip summary", ""),
        health_status=status_data.get("Health status", ""),
        sha256_hash=sha256,
    )


# --- In-flight track accumulator -------------------------------------------


class _MutableTrack:
    """Mutable scratch struct used while a track section is being parsed.

    Lives only inside parse_rip_log(); the final immutable record is
    produced by .build() at flush time.
    """

    def __init__(self, number: int) -> None:
        self.number: int = number
        self.fields: dict[str, str] = {}
        # ar[version] -> {Result, Confidence, Local CRC, Remote CRC}
        self.ar: dict[int, dict[str, str]] = {}

    def build(self) -> TrackResult:
        return TrackResult(
            number=self.number,
            filename=self.fields.get("Filename", ""),
            peak_level=_parse_float(self.fields.get("Peak level")),
            pre_emphasis=_parse_yes_no(self.fields.get("Pre-emphasis")),
            extraction_speed=_parse_with_pattern(
                self.fields.get("Extraction speed"), _SPEED
            ),
            extraction_quality=_parse_with_pattern(
                self.fields.get("Extraction quality"), _QUALITY
            ),
            test_crc=self.fields.get("Test CRC", ""),
            copy_crc=self.fields.get("Copy CRC", ""),
            status=self.fields.get("Status", ""),
            accuraterip_v1=_build_ar(1, self.ar.get(1)),
            accuraterip_v2=_build_ar(2, self.ar.get(2)),
        )


def _build_ar(version: int, raw: dict[str, str] | None) -> AccurateRipResult | None:
    if raw is None:
        return None
    return AccurateRipResult(
        version=version,
        result=raw.get("Result", ""),
        confidence=_parse_int(raw.get("Confidence")),
        local_crc=raw.get("Local CRC") or None,
        remote_crc=raw.get("Remote CRC") or None,
    )


def _build_ripping_info(data: dict[str, str]) -> RippingInfo:
    return RippingInfo(
        drive=data.get("Drive", ""),
        extraction_engine=data.get("Extraction engine", ""),
        defeat_audio_cache=_parse_yes_no(data.get("Defeat audio cache")),
        read_offset_correction=_parse_int(data.get("Read offset correction")),
        overread_lead_out=_parse_yes_no(data.get("Overread into lead-out")),
        gap_detection=data.get("Gap detection", ""),
        cd_r_detected=_parse_yes_no(data.get("CD-R detected")),
    )


# --- Tiny value parsers -----------------------------------------------------


def _parse_int(s: str | None) -> int | None:
    if s is None or not s.strip():
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _parse_float(s: str | None) -> float | None:
    if s is None or not s.strip():
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_yes_no(s: str | None) -> bool | None:
    """Recognize Yes/No, True/False, true/false. Empty/unknown → None."""
    if s is None:
        return None
    normalized = s.strip().lower()
    if normalized in ("yes", "true"):
        return True
    if normalized in ("no", "false"):
        return False
    return None


def _parse_with_pattern(s: str | None, pattern: re.Pattern[str]) -> float | None:
    """Extract the float `value` named-group from `pattern` applied to `s`."""
    if s is None:
        return None
    match = pattern.match(s.strip())
    if not match:
        return None
    return float(match.group("value"))


def secure_rerip_tracks_scoped(parsed: RipLog) -> int:
    """How many track blocks carry cyanrip's ``Scope:`` line.

    **The single predicate for "was the secure re-read GENUINELY exercised?", and
    it exists because two surfaces were about to answer it with two keys.**
    ``rig_check._report_paranoia_scope`` renders *"secure re-read genuinely
    exercised: YES"* off this count, and section N of the acceptance script
    declares that line to be its pass criterion — but that row is ``INFO``, so
    **nothing graded it**: a rip where ``-Z`` did nothing passed §N (2026-09-05).

    The fix is a graded verb, and the trap in writing one is to re-derive the
    answer from a different field — ``rip_count``, or ``secure_rerip_converged``
    — which is how two surfaces come to disagree about one question while both
    tests pass. `CLAUDE.md`: *one predicate, N callers, where the caller
    delegates rather than restating.* So the report and the assertion read the
    same number from the same place.

    Why ``Scope:`` and not a counter: a paranoia counter can be non-zero on an
    ordinary single-pass read, so it answers *"did the reader retry?"*. The
    ``Scope:`` line is emitted per track when a re-read pass actually ran, which
    is the question ``-Z`` is being tested for.

    Returns a count rather than a bool so a caller can report *how many of how
    many* — "1 of 14" and "14 of 14" are different facts about a disc, and
    collapsing them to ``True`` throws away the one a reader wants.
    """
    return sum(1 for track in parsed.tracks if track.paranoia_scope)
