"""Tests for the cyanrip rip-log parser (parsers/cyanrip_log.py).

Sample shapes reconstructed from cyanrip master's format strings
(`cyanrip_log.c::cyanrip_log_track_end` / `cyanrip_log_finish_report`).
A real hardware log (test-plan Test 8 step 6) should be added as a golden
fixture when available. Cases follow docs/testing.md's taxonomy.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path

import pytest

from platterpus.parsers import cyanrip_log
from platterpus.parsers.cyanrip_log import looks_like_cyanrip_log, parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog

# The committed real-hardware logs the accountability tests at the bottom read.
_REPO = Path(__file__).resolve().parents[1]

_FULL_LOG = """\
cyanrip 0.9.3.1 (master)
Drive used:     PIONEER BD-RW   BDR-209D (revision 1.10)
System device:  /dev/sr0
Offset:         +667 samples
Paranoia level: full
Frame retries:  10
Outputs:        flac
Disc tracks:    2
DiscID:         xA2hjkk0Jl0gKKtIdYuTje4JTXY-
Album:          Greatest Hits
Album artist:   The Police

Track 1 ripped and encoded successfully!
  Preemphasis:   none detected
    Data bytes:  40841920 (38.95 Mib)
    Frames:      17369
    Duration:    03:51.44
    Samples:     10210480
  EAC CRC32:     A1B2C3D4
  Accurip:       found in database (max confidence: 3)
    Accurip v1:  12345678 (accurately ripped, confidence 3)
    Accurip v2:  9ABCDEF0 (accurately ripped, confidence 2)
  File(s):
    The Police/Greatest Hits/01 - Roxanne.flac

Track 2 ripped and encoded with errors.
  Preemphasis:   present (subcode) (deemphasis applied)
  EAC CRC32:     00FF00FF (after 5 rips)
    Accurip v1:  DEADBEEF (not found, either a new pressing, or bad rip)

Tracks ripped accurately: 1/2
Ripping errors: 3
Ripping finished at 2026-06-09 12:34:56
"""


# --- Easy: full log ---------------------------------------------------------


def test_parses_device_model_as_drive() -> None:
    # cyanrip 0.9.3 prints "Device model:", not "Drive used:" — a real rip's
    # drive came out null because the regex only matched the latter (0.4.5 bug).
    log = parse_cyanrip_log(
        "cyanrip 0.9.3 (release)\n"
        "Device model:   PIONEER  BD-RW   BDR-209D 1.51 SCSI CD-ROM\n"
        "Offset:         +667 samples\n"
    )
    assert log.ripping_info.drive == "PIONEER  BD-RW   BDR-209D 1.51 SCSI CD-ROM"
    assert log.ripping_info.read_offset_correction == 667


def test_parses_replaygain_filename_loudness_and_checksum() -> None:
    # From the real rip: per-track ReplayGain + filename, album loudness, and
    # cyanrip's own "Log FUN512" signature must all reach the RipLog.
    log = parse_cyanrip_log(
        "cyanrip 0.9.3 (release)\n"
        "Track 1 ripped and encoded successfully!\n"
        "Summary:\n"
        "  EAC CRC32:     B0D122E7 (after 3 rips)\n"
        "  Metadata:\n"
        "    REPLAYGAIN_TRACK_GAIN:         -4.10 dB\n"
        "    R128_TRACK_GAIN:               229\n"
        "    REPLAYGAIN_TRACK_PEAK:         1.029445\n"
        "  File(s):\n"
        "    The Police/Album/01 - Roxanne.flac\n"
        "\n"
        "Album Loudness Summary:\n"
        "  Integrated loudness:\n"
        "    I:         -13.9 LUFS\n"
        "  Loudness range:\n"
        "    LRA:         8.9 LU\n"
        "  True peak:\n"
        "    Peak:        0.8 dBFS\n"
        "Log FUN512: SMUmY2sgZFoiL_8iSXnp\n"
    )
    (track,) = log.tracks
    assert track.filename == "The Police/Album/01 - Roxanne.flac"
    assert track.replaygain["REPLAYGAIN_TRACK_GAIN"] == "-4.10 dB"
    assert track.replaygain["R128_TRACK_GAIN"] == "229"
    assert track.replaygain["REPLAYGAIN_TRACK_PEAK"] == "1.029445"
    assert log.album_loudness == {
        "integrated_lufs": "-13.9",
        "lra_lu": "8.9",
        "true_peak_dbfs": "0.8",
    }
    assert log.log_checksum == "SMUmY2sgZFoiL_8iSXnp"


def test_full_log_parses_header_and_finish() -> None:
    log = parse_cyanrip_log(_FULL_LOG)
    assert log.log_creator == "cyanrip 0.9.3.1"
    assert log.creation_date == "2026-06-09 12:34:56"
    assert log.ripping_info.drive.startswith("PIONEER")
    assert log.ripping_info.read_offset_correction == 667
    assert log.accuraterip_summary == "1/2 tracks ripped accurately (AccurateRip)"
    assert log.health_status == "3 ripping errors"


def test_full_log_parses_tracks() -> None:
    log = parse_cyanrip_log(_FULL_LOG)
    assert len(log.tracks) == 2

    one = log.tracks[0]
    assert one.number == 1
    assert one.status == "ripped successfully"
    assert one.copy_crc == "A1B2C3D4"
    assert one.test_crc == ""  # cyanrip has no test+copy dual read
    assert one.pre_emphasis is False
    assert one.accuraterip_v1 is not None
    assert one.accuraterip_v1.confidence == 3
    assert one.accuraterip_v1.local_crc == "12345678"
    assert one.accuraterip_v2 is not None
    assert one.accuraterip_v2.confidence == 2

    # A clean single-pass track records no explicit rip count.
    assert one.rip_count is None
    assert one.accuraterip_offset is None

    two = log.tracks[1]
    assert two.status == "ripped with errors"
    assert two.copy_crc == "00FF00FF"  # "(after N rips)" suffix tolerated
    assert two.rip_count == 5  # ...and the count is captured from that suffix
    assert two.pre_emphasis is True
    assert two.accuraterip_v1 is not None
    assert two.accuraterip_v1.confidence is None  # not found → no confidence
    assert two.accuraterip_v2 is None


# --- The -Z secure-rerip extras (offset variant, partial summary, …) ---------

# A marginal-disc shape: a track that only matched the +450-frame offset
# variant after several re-reads, plus the finish-report extras cyanrip writes
# under -Z. Mirrors the real Police "Classics" rip (tracks 3 & 5).
_MARGINAL_LOG = """\
cyanrip 0.9.3 (release)
Offset:         +667 samples
Total time:     00:59:42.354

Track 3 ripped and encoded successfully!
  Preemphasis:   none detected
  EAC CRC32:     7E50D2FA (after 5 rips)
  Accurip:       found in database
    Accurip 450: BF62B1DA (matches Accurip DB, confidence 200, track is partially accurately ripped)

Tracks ripped accurately: 12/14
Tracks ripped partially accurately: 2/2

Paranoia status counts:
  READ:          71948
  VERIFY:        11098
  FIXUP_ATOM:    193
  OVERLAP:       1677

Ripping errors: 0
Ripping finished at 2026-06-29T21:36:39
"""


def test_disc_duration_captured_from_start_report() -> None:
    log = parse_cyanrip_log(_MARGINAL_LOG)
    # The disc's AUDIO length — not the rip wall-clock (that lives in the JSON
    # report's timing section, measured by the GUI).
    assert log.disc_duration == "00:59:42.354"


def test_rip_count_captured_from_after_n_rips() -> None:
    log = parse_cyanrip_log(_MARGINAL_LOG)
    assert log.tracks[0].rip_count == 5


def test_offset_variant_match_is_captured_but_not_a_plain_match() -> None:
    log = parse_cyanrip_log(_MARGINAL_LOG)
    track = log.tracks[0]
    # The "Accurip 450" offset-pressing variant is recorded as data...
    assert track.accuraterip_offset is not None
    assert track.accuraterip_offset.version == 450
    assert track.accuraterip_offset.confidence == 200
    assert track.accuraterip_offset.local_crc == "BF62B1DA"
    # ...but it is NOT a plain v1/v2 match, so the shared "verified" rule
    # (confidence>=1 on v1/v2) does not over-claim it as accurately ripped.
    from platterpus.parsers.rip_log import track_accuraterip_verified

    assert track.accuraterip_v1 is None
    assert track.accuraterip_v2 is None
    assert track_accuraterip_verified(track) is False


def test_partial_accurate_summary_and_paranoia_counts() -> None:
    log = parse_cyanrip_log(_MARGINAL_LOG)
    assert "2/2" in log.partially_accurate_summary
    assert log.paranoia_counts == {
        "READ": 71948,
        "VERIFY": 11098,
        "FIXUP_ATOM": 193,
        "OVERLAP": 1677,
    }


def test_paranoia_block_tolerates_a_malformed_line() -> None:
    """A non-integer count in the Paranoia block must degrade gracefully — the
    parser captures the well-formed counts and never raises (parser discipline).
    """
    text = (
        "cyanrip 0.9.3 (release)\n"
        "Paranoia status counts:\n"
        "  READ:          100\n"
        "  VERIFY:        not-a-number\n"
        "  OVERLAP:       7\n"
        "Ripping errors: 0\n"
    )
    log = parse_cyanrip_log(text)  # must not raise
    # The malformed VERIFY line closes the block; READ (before it) is captured.
    assert log.paranoia_counts.get("READ") == 100
    assert "VERIFY" not in log.paranoia_counts
    assert log.health_status == "No errors occurred"


def test_paranoia_block_ends_cleanly_before_finish_lines() -> None:
    # The block must not swallow the "Ripping errors:" / "finished at" lines
    # that follow it (they don't match the indented KEY: N shape, so the block
    # closes). Health + date still parse.
    log = parse_cyanrip_log(_MARGINAL_LOG)
    assert log.health_status == "No errors occurred"
    assert log.creation_date == "2026-06-29T21:36:39"


# --- Secure re-read (-Z) convergence: the per-track read-instability signal ---

# cyanrip prints each track's -Z verdict on the line JUST BEFORE that track's
# "Track N ripped…" opener. Four shapes, mirroring the real Police "Classics"
# rip (2026-07-01) where cyanrip reported 0 whole-disc errors yet one track never
# read the same twice:
#   1 — converged (2 of 2 reads agreed), AccurateRip-verified   → stable
#   2 — hit the repeat limit with NO two reads agreeing, offset → UNSTABLE
#   3 — converged (2 of 2), but only an offset-variant match    → stable pressing
#   4 — no verdict line at all (e.g. -Z off / a later track)    → unknown (None)
# The 2-vs-3 contrast is the whole point: an offset-variant match is a PRESSING
# difference, not instability, so a *converged* one (track 3) must NOT be flagged.
_SECURE_REREP_LOG = """\
cyanrip 0.9.3 (release)
Offset:         +667 samples
Disc tracks:    4

Repeating ripping (0 out of 2 matches for current checksum 4F2EDD18)
Repeating ripping (1 out of 2 matches for current checksum 4F2EDD18)
Done; (2 out of 2 matches for current checksum 4F2EDD18)
Track 1 ripped and encoded successfully!
  EAC CRC32:     B0D122E7 (after 3 rips)
    Accurip v1:  5D3C90CB (accurately ripped, confidence 129)
  File(s):
    Album/01 - Stable.flac

Repeating ripping (0 out of 2 matches for current checksum 24B44721)
Repeating ripping (0 out of 2 matches for current checksum 6A0DC832)
Repeating ripping (0 out of 2 matches for current checksum 962AD3C6)
Repeating ripping (0 out of 2 matches for current checksum ECA31204)
Done; (no matches found, but hit repeat limit of 5)
Track 2 ripped and encoded successfully!
  EAC CRC32:     329DC760 (after 5 rips)
    Accurip 450: BF62B1DA (matches Accurip DB, confidence 200, track is partially accurately ripped)
  File(s):
    Album/02 - Unstable.flac

Repeating ripping (0 out of 2 matches for current checksum 1FFC9968)
Repeating ripping (1 out of 2 matches for current checksum 1FFC9968)
Done; (2 out of 2 matches for current checksum 1FFC9968)
Track 3 ripped and encoded successfully!
  EAC CRC32:     E0036697 (after 5 rips)
    Accurip 450: 4CCBCF89 (matches Accurip DB, confidence 200, track is partially accurately ripped)
  File(s):
    Album/03 - StableOffsetVariant.flac

Track 4 ripped and encoded successfully!
  EAC CRC32:     ABCDEF01
  File(s):
    Album/04 - NoSecureRerip.flac

Tracks ripped accurately: 2/4
Tracks ripped partially accurately: 2/2
Ripping errors: 0
Ripping finished at 2026-07-01T03:10:58
"""


def test_secure_rerip_convergence_recorded_per_track() -> None:
    log = parse_cyanrip_log(_SECURE_REREP_LOG)
    numbers = [t.number for t in log.tracks]
    assert numbers == [1, 2, 3, 4]
    by_number = {t.number: t for t in log.tracks}
    # 1: converged.  2: hit the repeat limit → did NOT converge (unstable).
    assert by_number[1].secure_rerip_converged is True
    assert by_number[2].secure_rerip_converged is False
    # 3: converged (stable read) even though it matched only the offset variant —
    #    a pressing difference, NOT instability.
    assert by_number[3].secure_rerip_converged is True
    # 4: no verdict line preceded it → unknown; and crucially it did NOT inherit
    #    track 3's verdict (the buffer must reset after each track opens).
    assert by_number[4].secure_rerip_converged is None


def test_secure_rerip_verdict_never_raises_when_dangling() -> None:
    # A "Done; …" line with no following track (a crash right after) must not
    # raise and must simply be dropped (parser discipline).
    log = parse_cyanrip_log(
        "cyanrip 0.9.3 (release)\nDone; (no matches found, but hit repeat limit of 5)\n"
    )
    assert log.tracks == ()


def test_unstable_tracks_picks_only_the_non_converged_track() -> None:
    # The read-speed ladder's unstable_tracks() must flag track 2 only — not the
    # offset-variant-but-converged track 3 (the real-disc track-3-vs-5 lesson).
    from platterpus.read_speed_ladder import unstable_tracks

    log = parse_cyanrip_log(_SECURE_REREP_LOG)
    assert unstable_tracks(log) == [2]


# --- Medium: negative offset, zero errors normalize like whipper ------------


def test_speed_changeable_parsed_from_banner() -> None:
    # "unchangeable" contains "changeable" — the parser must not misread it.
    unchangeable = parse_cyanrip_log(
        "cyanrip 0.9.3 (release)\nSpeed:          default (unchangeable)\n"
    )
    assert unchangeable.ripping_info.speed_changeable is False

    changeable = parse_cyanrip_log(
        "cyanrip 0.9.3 (release)\nSpeed:          default (changeable)\n"
    )
    assert changeable.ripping_info.speed_changeable is True

    a_set_speed = parse_cyanrip_log("cyanrip 0.9.3 (release)\nSpeed:          8x\n")
    assert a_set_speed.ripping_info.speed_changeable is True

    # Absent Speed line (or a whipper log) → unknown, not a false negative.
    absent = parse_cyanrip_log("cyanrip 0.9.3 (release)\nOffset:  +667 samples\n")
    assert absent.ripping_info.speed_changeable is None


def test_negative_offset_and_clean_finish() -> None:
    log = parse_cyanrip_log(
        "cyanrip 0.9.3.1 (master)\nOffset:         -12 samples\nRipping errors: 0\n"
    )
    assert log.ripping_info.read_offset_correction == -12
    # Normalized to whipper's phrasing so downstream checks are shared.
    assert log.health_status == "No errors occurred"


def test_data_track_recorded_not_crashed() -> None:
    log = parse_cyanrip_log("cyanrip 0.9.3.1 (x)\nTrack 9 is data:\n  Frames: 1\n")
    assert log.tracks[0].number == 9
    assert log.tracks[0].status == "data track (skipped)"


# --- Hard: truncated log (crash mid-rip) -------------------------------------


def test_truncated_log_keeps_completed_tracks() -> None:
    truncated = _FULL_LOG.split("Track 2")[0]  # ends after track 1's block
    log = parse_cyanrip_log(truncated)
    assert len(log.tracks) == 1
    assert log.tracks[0].copy_crc == "A1B2C3D4"
    assert log.health_status == ""  # finish report never written


# --- Edge / unexpected -------------------------------------------------------


def test_empty_and_garbage_inputs_degrade_to_empty() -> None:
    assert parse_cyanrip_log("") == RipLog()
    garbage = parse_cyanrip_log("::::\nTrack x ripped\nEAC CRC32 nope\n")
    assert garbage.tracks == ()


def test_whipper_log_is_not_detected_as_cyanrip() -> None:
    whipper_text = "Log created by: whipper 0.10.0\nRipping phase information:\n"
    assert looks_like_cyanrip_log(whipper_text) is False
    assert looks_like_cyanrip_log(_FULL_LOG) is True
    assert looks_like_cyanrip_log("") is False
    assert looks_like_cyanrip_log("\n\n  \n") is False


# --- v9 (0.4.24): TOC-derived disc IDs ---------------------------------------


def test_parses_disc_id_and_cddb_id() -> None:
    log = parse_cyanrip_log(
        "cyanrip 0.9.3 (release)\n"
        "Device model:   PIONEER  BD-RW   BDR-209D 1.51 SCSI CD-ROM\n"
        "Offset:         +667 samples\n"
        "DiscID:         pNtImOkdBm9RMBIalzx0w9cfsYY-\n"
        "CDDB ID:        E20DFE0E\n"
    )
    assert log.disc_id == "pNtImOkdBm9RMBIalzx0w9cfsYY-"
    assert log.cddb_id == "E20DFE0E"


def test_disc_ids_default_empty_when_absent() -> None:
    log = parse_cyanrip_log("cyanrip 0.9.3 (release)\nOffset:  +0 samples\n")
    assert log.disc_id == ""
    assert log.cddb_id == ""


# --- Overread mode (real-hardware regression, 2026-07-26) --------------------


def test_parses_overread_mode_read_as_yes() -> None:
    """REGRESSION: the parser never read cyanrip's "Overread mode:" line, so
    RippingInfo.overread_lead_out stayed None and the EAC-compatible log rendered
    "(unknown)" even though cyanrip had stated it outright. Confirmed against the
    2026-07-26 BDR-209D rip, where `-O` was ON (and hung the drive)."""
    text = (
        "cyanrip 0.9.3 (release)\n"
        "Offset:         +667 samples\n"
        "Overread:       +2 frames\n"
        "Overread mode:  read in lead-in/lead-out\n"
    )
    assert parse_cyanrip_log(text).ripping_info.overread_lead_out is True


def test_parses_overread_mode_silence_fill_as_no() -> None:
    """cyanrip's conservative default (no `-O`) pads instead of reading, which is
    EAC's "Overread into Lead-In and Lead-Out: No". Wording confirmed against the
    committed overread-OFF reference log in output_reference/cyanrip_flac/."""
    text = (
        "cyanrip 0.9.3 (release)\n"
        "Overread:       +2 frames\n"
        "Overread mode:  fill with silence in lead-in/lead-out\n"
    )
    assert parse_cyanrip_log(text).ripping_info.overread_lead_out is False


def test_overread_frame_count_alone_is_not_a_verdict() -> None:
    """The frame COUNT is printed identically in both modes (+2 frames in the
    overread-ON and overread-OFF reference logs alike), so keying on it would
    report Yes for every rip. Only the mode line decides; absent it, stay unknown."""
    text = "cyanrip 0.9.3 (release)\nOverread:       +2 frames\n"
    assert parse_cyanrip_log(text).ripping_info.overread_lead_out is None


def test_unrecognised_overread_mode_stays_unknown() -> None:
    text = "cyanrip 0.9.3 (release)\nOverread mode:  something we have never seen\n"
    assert parse_cyanrip_log(text).ripping_info.overread_lead_out is None


def test_parses_underread_mode_for_negative_offset_drives() -> None:
    """cyanrip switches the label to "Underread mode:" whenever the frame count is
    negative, and that sign comes from the READ OFFSET — so a drive with a negative
    offset prints "Underread". An `^Overread mode:`-only pattern silently missed
    those drives, sending the field back to "(unknown)" for exactly them. The mode
    VALUES are identical in both cases, so the mapping is unchanged."""
    for label in ("Overread", "Underread"):
        read = f"cyanrip 0.9.3 (release)\n{label} mode:  read in lead-in/lead-out\n"
        silence = f"cyanrip 0.9.3 (release)\n{label} mode:  fill with silence in lead-in/lead-out\n"
        assert parse_cyanrip_log(read).ripping_info.overread_lead_out is True, label
        assert parse_cyanrip_log(silence).ripping_info.overread_lead_out is False, label


# --- The recognised-line enumeration, checked against the REAL logs ----------
# Every bug this parser ever shipped was one shape: cyanrip prints a line and we
# silently ignore it (overread mode twice, the gap section, "Accurip 450", the
# per-track rip count). The tables in the parser make the recognised set data;
# these tests are the payoff — they walk the committed real logs and fail when a
# TOP-LEVEL line matches neither the tables nor the written-down ignore list, so
# a row a future cyanrip adds cannot slip past unnoticed the way those did.
#
# Scope, decided deliberately: only column-0 lines are a hard failure. Those are
# cyanrip's structural rows (settings, section headers, the finish report) and
# there are ~58 of them per log. The ~1,300 INDENTED lines are per-track detail
# and tag dumps — mostly things we correctly skim — so requiring an allow-list
# entry for each would be busywork that trains people to rubber-stamp it. They
# get the reporting test below instead, which has its own floors.


def _corpus_logs() -> list[Path]:
    """The committed real cyanrip logs (`output_reference/cyanrip_*/`)."""
    return sorted((_REPO / "output_reference").glob("cyanrip_*/*.log"))


def _classify_top_level(line: str) -> str | None:
    """Name of whatever recognises this top-level line, or None if nothing does."""
    for rule in cyanrip_log._ALL_LINE_RULES:
        if rule.pattern.match(line):
            return rule.name
    for name, pattern in cyanrip_log._SECTION_LINE_PATTERNS:
        if pattern.match(line):
            return name
    if cyanrip_log._is_ignored_disc_line(line):
        return "ignored"
    return None


def test_rule_tables_are_a_complete_enumeration_of_this_module() -> None:
    """No line pattern may hide outside the enumerable groups.

    The tables are only worth having if they are exhaustive: a pattern added to
    the loop but not listed would make the accountability test below report a
    recognised line as unhandled (or worse, lull a reader into thinking the list
    is the whole story). So this walks the module's own regex constants and
    requires each to appear in a table, in the section list, or in the indented
    list. `_ACCURIP_CONFIDENCE` is the one exception and is named explicitly: it
    is searched inside an already-captured fragment, not matched against a line.
    """
    listed = (
        {rule.pattern for rule in cyanrip_log._ALL_LINE_RULES}
        | {pattern for _name, pattern in cyanrip_log._SECTION_LINE_PATTERNS}
        | {pattern for _name, pattern in cyanrip_log._INDENTED_LINE_PATTERNS}
        | {cyanrip_log._ACCURIP_CONFIDENCE}
    )
    module_patterns = {
        name: value
        for name, value in vars(cyanrip_log).items()
        if isinstance(value, re.Pattern)
    }
    # Floor: if the introspection found nothing, the test proves nothing.
    assert len(module_patterns) >= 25, module_patterns
    missing = sorted(
        name for name, pattern in module_patterns.items() if pattern not in listed
    )
    assert not missing, (
        "these compiled patterns are not listed in any enumerable group, so the "
        f"'what do we recognise' listing is incomplete: {missing}"
    )
    names = [rule.name for rule in cyanrip_log._ALL_LINE_RULES]
    assert len(names) >= 19, names
    assert len(set(names)) == len(names), f"duplicate rule names: {names}"
    for rule in cyanrip_log._ALL_LINE_RULES:
        # Anchored matching only — a floating pattern would claim a line because
        # of something in its middle (and `.match` already implies the anchor,
        # so an unanchored pattern here is a sign someone meant `.search`).
        assert rule.pattern.pattern.startswith("^"), rule.name


def test_every_top_level_line_of_the_real_cyanrip_logs_is_accounted_for() -> None:
    """THE regression guard for this file's whole bug history.

    Fails if a column-0 line in a committed real log is matched by no rule, no
    section header, and no `_IGNORED_DISC_LINES` entry. Silencing a new upstream
    row therefore requires writing down the decision — which is the step that
    never happened for the overread mode, the gaps section or "Accurip 450".
    """
    logs = _corpus_logs()
    assert len(logs) >= 2, f"expected the committed cyanrip logs, found {logs}"
    total_examined = 0
    for path in logs:
        lines = path.read_text(encoding="utf-8").splitlines()
        top_level = [line for line in lines if line and not line[0].isspace()]
        # Floor per log: a truncated or mis-globbed file must not pass by being
        # nearly empty. The real logs carry 58 top-level lines each.
        assert len(top_level) >= 40, f"{path.name}: only {len(top_level)} top-level"
        unaccounted = [line for line in top_level if _classify_top_level(line) is None]
        assert not unaccounted, (
            f"{path.name}: cyanrip printed {len(unaccounted)} top-level line(s) this "
            "parser recognises nothing for. Either parse them (a table rule) or "
            "record the decision in _IGNORED_DISC_LINES with a reason:\n  "
            + "\n  ".join(repr(line) for line in unaccounted[:20])
        )
        total_examined += len(top_level)
    assert total_examined >= 100, total_examined


def test_ignore_list_is_evidence_based_and_cannot_hide_a_parsed_row() -> None:
    """The allow-list must stay specific, and stay honest.

    Two ways an allow-list rots: it grows entries for lines nobody has ever seen
    (speculation), or an entry gets broad enough to swallow a row we DO parse, at
    which point the accountability test above still passes while the parse
    quietly regresses. So: most entries must match a real committed line, and no
    entry may match a line that a rule or section pattern claims.
    """
    corpus = [
        line
        for path in _corpus_logs()
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(corpus) >= 1000, len(corpus)
    observed = sum(
        1
        for pattern, _reason in cyanrip_log._IGNORED_DISC_LINES
        if any(pattern.match(line) for line in corpus)
    )
    assert observed >= 8, (
        f"only {observed} of {len(cyanrip_log._IGNORED_DISC_LINES)} ignore entries "
        "match anything in the real logs — the list is drifting into speculation"
    )
    for pattern, reason in cyanrip_log._IGNORED_DISC_LINES:
        assert reason, f"{pattern.pattern}: an ignore entry needs a stated reason"
        for rule in cyanrip_log._ALL_LINE_RULES:
            overlap = [
                line
                for line in corpus
                if pattern.match(line) and rule.pattern.match(line)
            ]
            assert not overlap, (
                f"ignore entry {pattern.pattern!r} also matches lines that rule "
                f"{rule.name!r} parses, so it can mask a real regression: "
                f"{overlap[:3]}"
            )


def test_indented_lines_report_what_the_parser_reads_and_what_it_skims() -> None:
    """Informational counterpart: what do we read INSIDE the blocks, and what not?

    Deliberately not a hard failure. A rip log's indented body is per-track
    detail and a full tag dump — hundreds of lines we are right to skim — so
    failing on an unrecognised one would fail the build for progress spam. It
    still needs teeth, or it would pass by finding nothing: it asserts a floor on
    lines examined and that every load-bearing per-track row is recognised. The
    residue is printed, so `pytest -s` (or any failure here) shows exactly which
    lines the parser has no opinion about.

    `gaps_value` is excluded from the classifier on purpose: its pattern is "any
    indented line", meaningful only on the line after "Gaps:", so counting it
    would mark all 1,300 indented lines as recognised and prove nothing. Track
    FILENAME lines are likewise invisible here — they are claimed by the
    "File(s):" lookahead in the loop, not by a pattern.
    """
    classifiers = [
        (name, pattern)
        for name, pattern in cyanrip_log._INDENTED_LINE_PATTERNS
        if name != "gaps_value"
    ]
    classifiers += [(rule.name, rule.pattern) for rule in cyanrip_log._ALL_LINE_RULES]
    recognised: Counter[str] = Counter()
    skimmed: Counter[str] = Counter()
    examined = 0
    for path in _corpus_logs():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or not line[0].isspace():
                continue
            examined += 1
            for name, pattern in classifiers:
                if pattern.match(line):
                    recognised[name] += 1
                    break
            else:
                label = line.strip().split(":")[0][:40]
                skimmed[label] += 1
    print(
        f"\nindented lines examined: {examined}; recognised: {sum(recognised.values())}"
        f" across {len(recognised)} row types; skimmed: {sum(skimmed.values())}"
        f" across {len(skimmed)} labels"
    )
    for label, count in skimmed.most_common():
        print(f"  skimmed x{count:<4} {label}")
    assert examined >= 1200, examined
    # Every row that carries a trust claim or a disc fact must be recognised —
    # this is the part that cannot be satisfied by finding nothing.
    must_read = {
        "track_eac_crc",
        "track_accurip",
        "track_accurip_offset",
        "track_start_lsn",
        "track_end_lsn",
        "track_pregap_lsn",
        "track_preemphasis",
        "track_replaygain",
        "track_files_header",
        "paranoia_count",
        "loudness_integrated",
        "loudness_range",
        "loudness_true_peak",
    }
    assert must_read <= set(recognised), sorted(must_read - set(recognised))
    assert sum(recognised.values()) >= 400, dict(recognised)


def test_an_unrecognised_top_level_line_is_reported_to_the_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The runtime half of the same idea: a strange row leaves evidence.

    A user's bug report carries the log file, so when a future cyanrip prints a
    row we do not understand, the fact should be IN that file rather than
    inferred. Debug level, not warning: a stray line is not a rip failure, and
    the parser must stay quiet in normal use.
    """
    with caplog.at_level(logging.DEBUG, logger="platterpus.parsers.cyanrip_log"):
        parse_cyanrip_log(
            "cyanrip 0.9.3 (release)\n"
            "Offset:         +667 samples\n"
            "Quantum entanglement mode: enabled\n"  # the row from the future
            "    indented detail we correctly skim: 5\n"
            "Ripping errors: 0\n"
        )
    messages = [record.getMessage() for record in caplog.records]
    assert any("unrecognised top-level line" in m for m in messages), messages
    assert any("Quantum entanglement mode" in m for m in messages), messages
    # The indented line is per-track detail: reporting it would be noise.
    assert not any("indented detail" in m for m in messages), messages


def test_a_known_ignored_row_is_not_reported_as_unrecognised(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The allow-list silences the debug report too, so the report stays useful.

    Same list, one meaning: entries in `_IGNORED_DISC_LINES` are decisions, and a
    decision should not keep costing a log line on every parse.
    """
    with caplog.at_level(logging.DEBUG, logger="platterpus.parsers.cyanrip_log"):
        parse_cyanrip_log(
            "cyanrip 0.9.3 (release)\n"
            "System device:  /dev/sr0\n"
            "HDCD decoding:  disabled\n"
            "Tracks to rip:  all\n"
        )
    assert not [
        record.getMessage()
        for record in caplog.records
        if "unrecognised" in record.getMessage()
    ]


# --- The table's own new failure modes ---------------------------------------
# The table introduced two things the if-chain didn't have: a handler that can
# DECLINE a line it matched, and a "disc-level rows only" flag. Both are state,
# so both get a test (docs/testing.md §5.t — "what new state does this create?").


def test_a_second_version_banner_does_not_overwrite_the_first() -> None:
    """First banner wins — and a later one keeps travelling down the chain.

    cyanrip stamps its version into each track's Metadata block ("comment:
    cyanrip 0.9.3"), and a concatenated or re-ripped log can carry two banners.
    The rule declines rather than claims, which is what the old
    `if match and not log_creator:` did.
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.3 (release)\n"
        "Offset:         +667 samples\n"
        "cyanrip 9.9.9 (from the future)\n"
    )
    assert log.log_creator == "cyanrip 0.9.3"
    assert log.ripping_info.extraction_engine == "cyanrip 0.9.3"


def test_album_rows_inside_a_track_block_do_not_overwrite_the_disc_album() -> None:
    """`disc_level_only` rows: the per-track tag dump must not win.

    cyanrip prints "album:" / "album_artist:" inside every track's Metadata
    block. Those are indented, but a log whose indentation is lost (a copy-paste,
    a mangled encoding) would otherwise let the last track's tags redefine the
    disc — and `Outputs:` the same way.
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.3 (release)\n"
        "Album:          The Real Album\n"
        "Album artist:   The Real Artist\n"
        "Outputs:        flac\n"
        "Track 1 ripped and encoded successfully!\n"
        "Album:          Not The Disc\n"
        "Album artist:   Not The Artist\n"
        "Outputs:        mp3\n"
        "  EAC CRC32:     B0D122E7\n"
    )
    assert log.ripping_info.album == "The Real Album"
    assert log.ripping_info.album_artist == "The Real Artist"
    assert log.ripping_info.output_formats == "flac"
    # And the track itself still parsed normally around those lines.
    assert log.tracks[0].copy_crc == "B0D122E7"
