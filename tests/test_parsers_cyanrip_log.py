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
from platterpus.parsers.cyanrip_log import (
    looks_like_cyanrip_log,
    parse_cyanrip_log,
    render_partially_accurate_summary,
)
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
    # THIS FIXTURE IS DELIBERATELY SELF-INCONSISTENT: it declares `2/2` while listing
    # one track. A real log does not do that, so it is kept as the mismatch case —
    # when the ripper's numerator and the per-track detail in the same file disagree,
    # the sentence must SAY SO rather than silently render whichever we computed.
    assert log.partially_accurate_reported == "2/2", (
        "the ripper's own fraction must survive verbatim — a rendered sentence "
        "cannot be turned back into the number the binary printed"
    )
    assert "does not agree" in log.partially_accurate_summary, (
        "the ripper said 2 and the per-track list has 1; a summary that hides that "
        "disagreement is the swallowed-diagnosis failure this project keeps finding"
    )
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


#: Where Platterpus's own auto-fix addendum begins in an album log. The writer
#: (`workers/rip_worker`) emits a 72-char `=` rule and *then* the marker, so the rule
#: belongs to our block too — cutting at the marker alone leaves that line looking
#: like a column-0 row cyanrip printed, which is how the first version of this cut
#: still failed by exactly one line.
_ADDENDUM_MARKER = "[Platterpus auto-fix addendum]"
_ADDENDUM_START = "=" * 72 + "\n" + _ADDENDUM_MARKER


def _corpus_logs() -> list[Path]:
    """Every committed real cyanrip log (`output_reference/cyanrip_*/`).

    **Both builds.** Use :func:`_stock_logs` / :func:`_fork_logs` when the assertion
    is build-specific — several sweeps below were written when this glob returned
    only stock 0.9.3 logs, so "the real logs" and "stock output" were the same set.
    Adding a real fork rip separated them.
    """
    logs = sorted((_REPO / "output_reference").glob("cyanrip_*/*.log"))
    # The EAC-layout render is OUR output, not the ripper's; it lives beside the
    # ripper's log and would otherwise be swept as if cyanrip had printed it.
    return [p for p in logs if "EACcompatible" not in p.name]


def _is_fork_log(path: Path) -> bool:
    """Whether this log came from the Platterpus fork.

    Keyed on the build tag in the banner, via the shared classifier — not on the
    filename, which is ours to rename, and not on the version number, which the fork
    deliberately tracks upstream (so a version cannot separate them; CLAUDE.md
    rule 12).
    """
    from platterpus.ripper_identity import identify_from_banner

    first = path.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0]
    return bool(identify_from_banner(first).is_fork)


def _stock_logs() -> list[Path]:
    """Committed real logs from **stock** cyanrip — what AppImage users run."""
    return [p for p in _corpus_logs() if not _is_fork_log(p)]


def _fork_logs() -> list[Path]:
    """Committed real logs from the **fork** — the build the handshake pins."""
    return [p for p in _corpus_logs() if _is_fork_log(p)]


def test_the_corpus_contains_both_builds() -> None:
    """The floor under every build-aware sweep below.

    If this ever finds only one build, those sweeps stop testing the other half and
    would keep passing — the "can this check be satisfied by finding nothing?" trap,
    one level up. A corpus of stock-only logs is exactly the state that let the fork's
    `merging into track N` wording go unmatched for two handshake rounds.
    """
    stock, fork = _stock_logs(), _fork_logs()
    assert stock, "no committed STOCK cyanrip log — the absent-case sweeps are blind"
    assert fork, "no committed FORK cyanrip log — the present-case sweeps are blind"
    assert len(stock) + len(fork) == len(_corpus_logs())


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
    requires each to appear in a table, in the section list, in the indented list,
    or in `_FRAGMENT_PATTERNS`.

    **That last group replaced a test-side allowlist**, and the change is the point:
    this test used to name `_ACCURIP_CONFIDENCE` itself as "the one exception". A
    hand-maintained exemption list living in the checker is the shape that hid 16 of
    the fork's fatal strings behind their generator's prefix filter (round 5), and it
    bit here the moment two more fragment patterns arrived (round 7 lap 15). The
    enumeration now lives in the module, so a new fragment pattern fails this sweep
    instead of quietly requiring the test to be edited.
    """
    listed = (
        {rule.pattern for rule in cyanrip_log._ALL_LINE_RULES}
        | {pattern for _name, pattern in cyanrip_log._SECTION_LINE_PATTERNS}
        | {pattern for _name, pattern in cyanrip_log._INDENTED_LINE_PATTERNS}
        | {pattern for _name, pattern in cyanrip_log._FRAGMENT_PATTERNS}
        | {pattern for _name, pattern in cyanrip_log._PREPROCESS_PATTERNS}
    )
    # The fragment group must not become a dumping ground: it is small, every entry is
    # applied to a captured substring, and it may not swallow a line-level pattern.
    assert len(cyanrip_log._FRAGMENT_PATTERNS) <= 6, (
        "the fragment group is growing; check each entry really is matched against a "
        "captured fragment rather than a whole line"
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
        text = path.read_text(encoding="utf-8")
        # ONLY THE PART CYANRIP WROTE. Platterpus appends its own `[Platterpus
        # auto-fix addendum]` block to the album log after a re-rip swap, and this
        # sweep's whole premise is "a column-0 line *cyanrip printed* that no rule
        # claims". Sweeping our own prose would demand ignore-list entries for our
        # own sentences — and, worse, an entry matching our wording could then mask a
        # future cyanrip row that happened to start the same way.
        text = text.split(_ADDENDUM_START, 1)[0]
        lines = text.splitlines()
        top_level = [line for line in lines if line and not line[0].isspace()]
        # Floor per log: a truncated or mis-globbed file must not pass by being
        # nearly empty. The real logs carry 58+ top-level lines each.
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
        # Graduated out of the skimmed residue on 2026-07-31: this row names the
        # track whose final frames are FABRICATED SILENCE rather than disc audio,
        # which is an archival-fidelity claim, not per-track noise. Listing it here
        # is what stops it sliding back into the residue unnoticed.
        "track_appended_silence",
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


# --- Reading a FUTURE cyanrip: the fork-only rows (2026-07-31) ----------------
# The maintainer is fixing cyanrip in their own fork, and Platterpus must read the
# new lines the moment they appear WITHOUT requiring them: AppImage users run the
# deployed 0.9.3, so one build has to be correct against both. Every case below
# comes in a pair — the line PRESENT, and the line ABSENT — because the absent half
# is the one that ships today and the one a careless "improvement" would break.
#
# Specification: docs/cyanrip-upstream.md Part A §2.1 (sample peak), §2.3
# (per-track speed/elapsed), §2.4 (the -Z verdict in the log file), §2.5 (C2 use
# vs capability). The `Appended:` row is NOT fork-only — 0.9.3 prints it already.

# The per-track loudness block cyanrip 0.9.3 REALLY prints, verbatim in shape from
# `output_reference/cyanrip_flac/`. Note what it contains: a TRUE peak of +0.3 dBFS
# and a ReplayGain track peak of 1.029445 — both ABOVE full scale, which is exactly
# why neither may ever become EAC's `Peak level`.
_TRUE_PEAK_ONLY_LOG = """\
cyanrip 0.9.3 (release)
Offset:         +667 samples

Track 1 ripped and encoded successfully!
Summary:

  Integrated loudness:
    I:         -13.9 LUFS
    Threshold: -24.3 LUFS

  True peak:
    Peak:        0.3 dBFS

  Preemphasis:   none detected

  EAC CRC32:     B0D122E7
  Metadata:
    REPLAYGAIN_TRACK_PEAK:         1.029445

Ripping errors: 0
"""


def test_a_true_peak_line_alone_leaves_the_peak_level_unreported() -> None:
    """THE critical absent-case: cyanrip's true peak must never fill EAC's row.

    EAC's `Peak level` is the SAMPLE peak as a percentage of full scale and cannot
    exceed 100 %. cyanrip 0.9.3 reports only the TRUE (4x-oversampled) peak, a
    different quantity that legitimately goes over full scale — all fourteen tracks
    of the committed reference disc do (`REPLAYGAIN_TRACK_PEAK` 1.008499–1.097464).
    Letting it through would print a wrong number into a checksum-attested archival
    document where today we honestly print "(not reported by the ripper)".

    So: the true-peak line, the ReplayGain peak tag, and both together leave
    `peak_level` at None. This is the test the whole sample-peak feature is built
    around — if it ever goes green while `peak_level` is set, the feature is a bug.
    """
    (track,) = parse_cyanrip_log(_TRUE_PEAK_ONLY_LOG).tracks
    assert track.peak_level is None
    # The true peak IS still readable elsewhere — it just isn't this field.
    assert track.replaygain["REPLAYGAIN_TRACK_PEAK"] == "1.029445"


def test_a_true_peak_below_full_scale_is_still_not_the_sample_peak() -> None:
    """The case the above-full-scale refusal CANNOT catch — so it isolates the guard.

    Found by reverting: the test above still passes with the "which peak is this?"
    guard removed, because the reference disc's true peak (+0.3 dBFS) is over full
    scale and the second guard refuses it anyway. That redundancy is welcome but it
    hides which defence is doing the work — and on a QUIET track the true peak is
    legitimately *below* 0 dBFS, where only the header state can tell the two
    quantities apart. -6 dBFS would sail through as a plausible "50.1 %".
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.3 (release)\n"
        "Track 1 ripped and encoded successfully!\n"
        "  True peak:\n"
        "    Peak:       -6.0 dBFS\n"
        "  EAC CRC32:     B0D122E7\n"
    )
    assert log.tracks[0].peak_level is None


def test_a_bare_peak_line_with_no_header_is_not_a_sample_peak() -> None:
    """No armed "Sample peak:" header → the value line stays skimmed.

    A log whose sub-headers were lost (a copy-paste, a trimmed log) must not have
    its bare `Peak:` line promoted into the sample-peak field by default.
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.3 (release)\n"
        "Track 1 ripped and encoded successfully!\n"
        "    Peak:        0.3 dBFS\n"
        "  EAC CRC32:     B0D122E7\n"
    )
    assert log.tracks[0].peak_level is None


# A fork log: every new line present, in the two shapes each could plausibly take.
# Track 1 uses the sub-header form (how cyanrip already prints `True peak:`);
# track 2 uses the inline form. Both elapsed values are the plain-seconds shape.
#
# Track 1's elapsed was `00:02:41.005` until 2026-08-21 — a CLOCK, which no cyanrip
# build has ever printed for this row. This fixture was the only producer of that
# shape, and it kept `track_elapsed_clock` looking alive for three weeks after the
# fork split the line at their `89eb849`. `CLAUDE.md`: *what does my stand-in do
# that the real thing does not?* — here it emitted a format the real thing does not,
# which is the same defect pointed the other way. Kept at the same numeric value
# (161.005 s) so the assertion below still pins a distinct number per track.
_FORK_LOG = """\
cyanrip 0.9.3.1-fork (platterpus)
Offset:         +667 samples
C2 errors:      supported by drive, not used
Disc tracks:    2

Track 1 ripped and encoded successfully!
Summary:

  True peak:
    Peak:        0.3 dBFS

  Sample peak:
    Peak:       -0.5 dBFS

  Preemphasis:   none detected

  Properties:
    Duration:    00:03:13.180
    Pregap LSN:  none
    Start LSN:   0 (with offset: 1)
    End LSN:     14486

  Elapsed:     161.005 s
  Speed:       1.6x
  EAC CRC32:     B0D122E7 (after 2 rips)
  Secure re-read: converged (2 out of 2 matches for current checksum B0D122E7)
  File(s):
    Album/01 - One.flac

Track 2 ripped and encoded successfully!
  Sample peak:  -1.0 dBFS
  Extraction speed: 2.4 X
  Extraction time: 161.5 s
  Properties:
    Appended:    2 frames of silence
  EAC CRC32:     985AAE32 (after 5 rips)
  Secure re-read: did NOT converge (no matches found, but hit repeat limit of 5)

Ripping errors: 0
Ripping finished at 2026-08-01 10:00:00
"""


def test_a_fork_sample_peak_fills_the_peak_level_as_a_linear_fraction() -> None:
    """Both print shapes, converted to the unit the EAC row actually renders.

    `TrackResult.peak_level` is a linear fraction because
    `eac_log_export._track_block` renders `peak_level * 100:.1f %`. -0.5 dBFS is
    94.4 % of full scale; -1.0 dBFS is 89.1 %.
    """
    by_number = {t.number: t for t in parse_cyanrip_log(_FORK_LOG).tracks}
    assert by_number[1].peak_level == pytest.approx(10 ** (-0.5 / 20))
    assert by_number[2].peak_level == pytest.approx(10 ** (-1.0 / 20))
    # And the sub-header form did NOT let the true peak (+0.3 dBFS, above full
    # scale) win — track 1 has both lines, in cyanrip's own order.
    assert by_number[1].peak_level is not None
    assert by_number[1].peak_level < 1.0


def test_a_sample_peak_above_full_scale_is_refused_not_clamped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A second line of defence, in case a fork wires the wrong number in.

    EAC's row is a percentage of full scale, so >100 % is not a sample peak at all
    — it is almost certainly the true peak arriving under the wrong label. Refusing
    keeps the honest "(not reported)" cell; clamping would print a plausible 100.0 %
    that nothing measured. The refusal is logged, because a dependency's unusable
    output must be diagnosable from a bug report (CLAUDE.md).

    The last case is not decoration: an absurd positive dBFS must be refused
    *before* the 10**(dB/20) conversion, because `10.0 ** (999999 / 20)` raises
    OverflowError — a parser documented "never raises" doing exactly that. The
    range check afterwards would be too late.
    """
    lines = (
        "  Sample peak:  0.3 dBFS",  # cyanrip's real TRUE peak, track 1
        "  Sample peak:  102.9 %",  # its ReplayGain peak, as a percentage
        "  Sample peak:  999999 dBFS",  # would OverflowError if converted
    )
    with caplog.at_level(logging.WARNING, logger="platterpus.parsers.cyanrip_log"):
        for line in lines:
            log = parse_cyanrip_log(
                "cyanrip 0.9.3-fork\nTrack 1 ripped and encoded successfully!\n"
                f"{line}\n  EAC CRC32:     B0D122E7\n"
            )  # must not raise
            assert log.tracks[0].peak_level is None, line
    assert "above full scale" in caplog.text or "outside" in caplog.text, caplog.text


def test_a_sample_peak_with_no_unit_is_refused() -> None:
    """dBFS and a linear fraction are indistinguishable in this range.

    "Sample peak: 0.942" could be 94.2 % (linear) or 111.5 % (dBFS). An archival
    peak read in the wrong unit is worse than a labelled gap, so the unit is
    required rather than assumed.

    The negative case is the one that isolates the rule (found by reverting): a
    bare "0.942" read as dBFS lands above full scale and the refusal above catches
    it anyway, but a bare "-0.5" read as dBFS would quietly become a
    plausible-looking 94.4 % from a number whose unit nobody stated.
    """
    for value in ("0.942", "-0.5"):
        log = parse_cyanrip_log(
            "cyanrip 0.9.3-fork\nTrack 1 ripped and encoded successfully!\n"
            f"  Sample peak:  {value}\n  EAC CRC32:     B0D122E7\n"
        )
        assert log.tracks[0].peak_level is None, value


def test_a_full_scale_sample_peak_is_accepted_at_exactly_100_percent() -> None:
    """0 dBFS is legal (a clipped track), and it is the boundary of the refusal."""
    log = parse_cyanrip_log(
        "cyanrip 0.9.3-fork\nTrack 1 ripped and encoded successfully!\n"
        "  Sample peak:  0.0 dBFS\n  EAC CRC32:     B0D122E7\n"
    )
    assert log.tracks[0].peak_level == pytest.approx(1.0)


def test_an_album_sample_peak_does_not_overwrite_the_album_true_peak() -> None:
    """The disc-level twin of the same trap.

    `album_loudness["true_peak_dbfs"]` is cyanrip's true peak. If a fork adds a
    sample peak to the Album Loudness Summary, capturing it under the same key
    would silently replace one loudness quantity with another.
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.3-fork\n"
        "Album Loudness Summary:\n"
        "\n"
        "  Integrated loudness:\n"
        "    I:         -13.9 LUFS\n"
        "\n"
        "  True peak:\n"
        "    Peak:        0.8 dBFS\n"
        "\n"
        "  Sample peak:\n"
        "    Peak:       -0.6 dBFS\n"
    )
    assert log.album_loudness == {
        "integrated_lufs": "-13.9",
        "true_peak_dbfs": "0.8",
        "sample_peak_dbfs": "-0.6",
    }


def test_a_fork_per_track_speed_and_elapsed_are_parsed() -> None:
    """§2.3's two halves: the speed multiple (EAC's row) and the wall-clock."""
    by_number = {t.number: t for t in parse_cyanrip_log(_FORK_LOG).tracks}
    assert by_number[1].extraction_speed == pytest.approx(1.6)
    assert by_number[1].extraction_elapsed_seconds == pytest.approx(161.005)
    assert by_number[2].extraction_speed == pytest.approx(2.4)
    assert by_number[2].extraction_elapsed_seconds == pytest.approx(161.5)


def test_every_committed_elapsed_line_is_actually_read() -> None:
    """**The gate that made retiring `track_elapsed_clock` safe.**

    A clock-form rule sat in this parser reading `Elapsed: (HH:)MM:SS(.mmm)`. It
    matched 0 of the 19 committed fork logs, 0 of the 11 stock ones, and — measured
    — it did not match the pre-split shape either: the fork's `89eb849` split
    `Elapsed:  %s (%.1fx)` into a speed row plus `Elapsed:  %.2f s`, and that
    combined line's trailing ` (0.9x)` is refused by the retired pattern's
    end-of-line anchor. So it read a shape nothing has ever emitted.

    Deleting it needed a replacement guard, because the indented-residue sweep in
    this file is deliberately *informational* — a clock form reappearing upstream
    would have been skimmed in silence, which is the failure this project calls
    "absent means absent" only when absence is checked.

    So: every indented line in the corpus whose label is in the elapsed family must
    be claimed by `track_elapsed_seconds`. Floored on lines examined, because a
    check that can pass by finding nothing is decoration.

    **Widened past `_corpus_logs()` on purpose.** That helper is three files from
    `output_reference/`, giving 14 elapsed lines; the handshake artifacts add every
    golden reference either side has published, which is where a new ripper's output
    lands FIRST. Measured 2026-08-21: 24 logs, 82 elapsed-family lines. The whole
    point of this gate is to see a shape change on the round it arrives.
    """
    family = re.compile(
        r"^\s+(?:Elapsed(?: time)?|Rip time|Extraction time|Time taken):", re.MULTILINE
    )
    paths = [
        path
        for path in sorted(_REPO.glob("output_reference/**/*.log"))
        + sorted(_REPO.glob("docs/handshake/**/*.log"))
        if "EACcompatible" not in path.name
    ]
    examined = 0
    unread: list[tuple[str, str]] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not family.match(line):
                continue
            examined += 1
            if not cyanrip_log._TRACK_ELAPSED_SECONDS.match(line):
                unread.append((path.name, line.strip()))
    assert len(paths) >= 20, f"only {len(paths)} logs in the widened corpus"
    assert examined >= 60, (
        f"only {examined} elapsed-family lines found in the corpus (82 on "
        f"2026-08-21) — the logs stopped carrying the row, or the family pattern "
        f"stopped recognising it, and either way a pass here proves nothing"
    )
    assert not unread, (
        "these committed log lines are in the elapsed family and no rule reads "
        f"them: {unread[:5]}.\nA new shape means the ripper changed the row — add a "
        "rule for the shape it ACTUALLY prints (and say which build, in the "
        "pattern's comment). Do not resurrect the clock rule on the strength of a "
        "different clock."
    )


def test_a_clock_shaped_elapsed_is_not_silently_read_as_a_duration() -> None:
    """The other half of the retirement: it left nothing behind that half-reads.

    The retired rule shared `extraction_elapsed_seconds` with the seconds rule, so
    the risk of removing it is not a crash — it is a value quietly becoming `None`
    somewhere that reads `None` as "the ripper did not report it". This pins the
    honest answer: a clock is **not** read, and it is not mistaken for a scalar
    number of seconds either (which is what an unanchored seconds pattern would
    have done — `03:51.44` would have yielded 3.0).
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.3-fork\nTrack 1 ripped and encoded successfully!\n"
        "  Elapsed time: 03:51.44\n  EAC CRC32:     B0D122E7\n"
    )
    assert log.tracks[0].extraction_elapsed_seconds is None
    # And the shape that IS emitted still works, in the same test, so this cannot
    # pass by the parser having stopped reading elapsed lines altogether.
    live = parse_cyanrip_log(
        "cyanrip 0.9.3-fork\nTrack 1 ripped and encoded successfully!\n"
        "  Elapsed:            231.44 s\n  EAC CRC32:     B0D122E7\n"
    )
    assert live.tracks[0].extraction_elapsed_seconds == pytest.approx(231.44)


def test_an_indented_per_track_speed_is_not_the_disc_speed_capability() -> None:
    """cyanrip's banner already has a column-0 "Speed:" row; they must not collide.

    The banner row answers "can this drive change read speed?" (`-S` aborts the rip
    when it cannot). A per-track row answers "how fast did this track read?".
    Indentation is the only difference in the text, so it is the discriminator.
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.3-fork\n"
        "Speed:          default (unchangeable)\n"
        "Track 1 ripped and encoded successfully!\n"
        "  Speed:       1.6x\n"
        "  EAC CRC32:     B0D122E7\n"
    )
    assert log.ripping_info.speed_changeable is False  # the banner row, untouched
    assert log.tracks[0].extraction_speed == pytest.approx(1.6)


def test_a_fork_secure_verdict_line_records_all_three_states() -> None:
    """§2.4: converged / did NOT converge / not attempted — three states, not two.

    The middle one is the whole point. Today cyanrip prints "(after 5 rips)" while
    its health line still says "No errors occurred", so a track that never read the
    same way twice is indistinguishable from a clean one in the saved log.
    """
    by_number = {t.number: t for t in parse_cyanrip_log(_FORK_LOG).tracks}
    assert by_number[1].secure_rerip_converged is True
    assert by_number[2].secure_rerip_converged is False
    # "not attempted" is the third state: no verdict, not a False.
    log = parse_cyanrip_log(
        "cyanrip 0.9.3-fork\nTrack 1 ripped and encoded successfully!\n"
        "  Secure re-read: not attempted (-Z was not requested)\n"
        "  EAC CRC32:     B0D122E7\n"
    )
    assert log.tracks[0].secure_rerip_converged is None


def test_an_indented_done_line_still_describes_the_NEXT_track() -> None:
    """The fixture shape this test used to have is one no cyanrip ever emits.

    It asserted that an indented `Done;` belongs to the track already open, and it
    passed — because it placed the line *inside* a track block, which is not where
    cyanrip puts it. cyanrip emits `Done;` from `cyanrip_rip_track()`'s repeat
    loop, which runs BEFORE the "Track N ripped…" opener. The maintainer's fork
    indented the string **in place**, so it is still a pre-opener line; under the
    old `^`-anchored rule every verdict was handed to the PREVIOUS track.

    Three tracks with DIFFERING consecutive verdicts, deliberately: a one-track
    shift is invisible on any fixture where neighbouring verdicts agree, which is
    exactly how the old test managed to vouch for the bug.
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.3.1 (fork)\n"
        "Repeating ripping (0 out of 1 matches for current checksum AAAA1111)\n"
        "  Done; (1 out of 1 matches for current checksum AAAA1111)\n"
        "Track 1 ripped and encoded successfully!\n"
        "  EAC CRC32:     AAAA1111 (after 2 rips)\n"
        "  Done; (no matches found, but hit repeat limit of 5)\n"
        "Track 2 ripped and encoded successfully!\n"
        "  EAC CRC32:     BBBB2222 (after 5 rips)\n"
        "  Done; (3 out of 3 matches for current checksum CCCC3333)\n"
        "Track 3 ripped and encoded successfully!\n"
        "  EAC CRC32:     CCCC3333 (after 3 rips)\n"
    )
    by_number = {t.number: t for t in log.tracks}
    # Floor: the fixture must actually contain differing verdicts, or this test
    # cannot detect a shift and is decoration.
    verdicts = [by_number[n].secure_rerip_converged for n in (1, 2, 3)]
    assert len(set(verdicts)) >= 2, f"fixture cannot detect a shift: {verdicts}"
    assert verdicts == [True, False, True], (
        "each track must keep its OWN verdict; a one-track shift shows up here as "
        f"[None, True, False] or [False, True, None]. Got {verdicts}"
    )


def test_a_zero_numerator_done_line_is_not_convergence() -> None:
    """`0 out of N matches` is a total failure to reproduce, not a clean read.

    No cyanrip is known to print it in the final verdict — the documented failure
    form is "no matches found, but hit repeat limit of N" — but the wording is
    demonstrably in cyanrip's vocabulary (its own `Repeating ripping (0 out of 1
    matches …)` progress line), and a bare digit quantifier read it as verified.
    This is a
    pinned invariant rather than a fix for an observed bug, and is labelled as one.
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.3\n"
        "Done; (0 out of 5 matches for current checksum AAAA1111)\n"
        "Track 1 ripped and encoded successfully!\n"
        "  EAC CRC32:     AAAA1111 (after 5 rips)\n"
    )
    assert log.tracks[0].secure_rerip_converged is False


def test_an_in_block_labelled_verdict_wins_over_the_buffered_one() -> None:
    """The fork emits both, and the labelled row is the authoritative one.

    A `Done;` line's ownership is inferred from position; a labelled row inside the
    track block states it. When the two disagree the row wins — and it must not be
    the case that the row is simply ignored, which is what a naive "first match
    wins" ordering would do.
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.3.1 (fork)\n"
        "  Done; (no matches found, but hit repeat limit of 5)\n"
        "Track 1 ripped and encoded successfully!\n"
        "  EAC CRC32:     AAAA1111 (after 2 rips)\n"
        "  Secure re-read:  converged after 2 reads\n"
    )
    assert log.tracks[0].secure_rerip_converged is True


def test_a_column_zero_done_line_still_buffers_for_the_next_track() -> None:
    """The 0.9.3 stdout behaviour, pinned so the new indented path can't change it.

    `test_secure_rerip_convergence_recorded_per_track` covers this on a four-track
    fixture; this one states the *rule* — column 0 means "the next track" — so a
    future refactor of the indented path names what it broke.
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.3 (release)\n"
        "Track 1 ripped and encoded successfully!\n"
        "  EAC CRC32:     B0D122E7\n"
        "Done; (2 out of 2 matches for current checksum 985AAE32)\n"
        "Track 2 ripped and encoded successfully!\n"
        "  EAC CRC32:     985AAE32\n"
    )
    by_number = {t.number: t for t in log.tracks}
    assert by_number[1].secure_rerip_converged is None
    assert by_number[2].secure_rerip_converged is True


def test_an_unrecognised_secure_verdict_never_erases_a_measured_one() -> None:
    """An unfamiliar future wording must cost nothing, not a verdict.

    The upstream phrasing is unread (§2.4 says so), so the parser matches the
    *sense*. The safe failure for a sense it cannot read is "no opinion" — leaving
    whatever was already measured, including the GUI auto-fix verdict that
    overrides this field later (`_merge_shipped_track`) and must stay the last word.
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.3-fork\n"
        "Done; (2 out of 2 matches for current checksum B0D122E7)\n"
        "Track 1 ripped and encoded successfully!\n"
        "  Secure re-read: quantum superposition\n"
        "  EAC CRC32:     B0D122E7\n"
    )
    assert log.tracks[0].secure_rerip_converged is True


def test_c2_supported_but_not_used_is_a_truthful_no() -> None:
    """§2.5: the new wording states USE, so it can answer EAC's question.

    And the old wording must keep its old meaning: a bare "supported by drive" is a
    drive CAPABILITY, which says nothing about whether the rip used C2 — that
    distinction is the entire reason EAC's row is honest here, and
    `test_c2_capability_is_not_reported_as_c2_use` pins the rendering side.
    """

    def c2_of(line: str) -> bool | None:
        return parse_cyanrip_log(f"cyanrip 0.9.3\n{line}\n").ripping_info.c2_pointers

    assert c2_of("C2 errors:      supported by drive, not used") is False
    assert c2_of("C2 errors:      supported by drive, unused by the reader") is False
    # Unchanged, deliberately:
    assert c2_of("C2 errors:      supported by drive") is None
    assert c2_of("C2 errors:      unsupported by drive") is False


def test_appended_silence_frames_are_read_from_the_real_committed_logs() -> None:
    """Not fork-only: cyanrip 0.9.3 prints this and we discarded it until now.

    It names the track whose FINAL FRAMES ARE FABRICATED SILENCE rather than disc
    audio — the per-track consequence of overread being off. Read from the committed
    real logs rather than a fixture we wrote, because a fixture we wrote is not
    evidence that cyanrip emits the line (docs/testing.md §5.t).
    """
    logs = _corpus_logs()
    assert len(logs) >= 3, logs
    examined = 0
    for path in logs:
        parsed = parse_cyanrip_log(path.read_text(encoding="utf-8", errors="replace"))
        assert len(parsed.tracks) == 14, path.name
        padded = {
            t.number: t.appended_silence_frames
            for t in parsed.tracks
            if t.appended_silence_frames
        }
        # Every log in the corpus is the SAME disc in the SAME drive at the same
        # offset, so the padded-track answer is a property of the disc and must agree
        # across builds. A build that disagreed here would be a real finding — the
        # final frames of track 14 are fabricated silence rather than disc audio.
        assert padded == {14: 2}, f"{path.name}: {padded}"
        examined += len(parsed.tracks)
    assert examined >= 42, examined


def test_todays_real_cyanrip_logs_report_none_of_the_fork_only_fields() -> None:
    """THE absent-case sweep, over the committed real 0.9.3 logs.

    AppImage users run the deployed cyanrip, which prints none of these lines. This
    is the test that says so with the actual bytes: every fork-only per-track field
    is None on every track of every committed log, so one build behaves identically
    against the deployed ripper and the fork.
    """
    logs = _stock_logs()
    assert len(logs) >= 2, logs
    examined = 0
    for path in logs:
        parsed = parse_cyanrip_log(path.read_text(encoding="utf-8", errors="replace"))
        for track in parsed.tracks:
            examined += 1
            assert track.peak_level is None, (path.name, track.number)
            assert track.extraction_speed is None, (path.name, track.number)
            assert track.extraction_elapsed_seconds is None, (path.name, track.number)
            assert track.secure_rerip_converged is None, (path.name, track.number)
        # The album true peak keeps its own key; no sample peak is invented.
        assert "sample_peak_dbfs" not in parsed.album_loudness, path.name
        assert parsed.album_loudness.get("true_peak_dbfs"), path.name
    # Floor: 14 tracks x 2 logs. A check that examined nothing proves nothing.
    assert examined >= 28, examined


# One past CPython's 4300-digit conversion ceiling (see safe_int.py). Hypothesis
# never generates this, so it is pinned — the same reasoning as
# `test_parsers_property.test_an_absurdly_long_number_never_raises`, extended to
# the rows added on 2026-07-31.
_OVER_THE_DIGIT_LIMIT = "9" * 4301


@pytest.mark.parametrize(
    "line",
    [
        f"  Sample peak:  -{_OVER_THE_DIGIT_LIMIT}.0 dBFS",
        f"  Sample peak:  {_OVER_THE_DIGIT_LIMIT} %",
        f"  Speed:       {_OVER_THE_DIGIT_LIMIT}x",
        f"  Elapsed:     {_OVER_THE_DIGIT_LIMIT}:00:00",
        f"  Elapsed:     00:00:{_OVER_THE_DIGIT_LIMIT}",
        f"  Extraction time: {_OVER_THE_DIGIT_LIMIT} s",
        f"    Appended:    {_OVER_THE_DIGIT_LIMIT} frames of silence",
        f"  Secure re-read: {_OVER_THE_DIGIT_LIMIT} out of 2 matches",
    ],
)
def test_an_absurdly_long_number_in_a_new_field_never_raises(line: str) -> None:
    """The new rows uphold the never-raises contract, by being BOUNDED.

    Every new quantifier is `\\d{1,N}`, so an over-limit digit run cannot even
    match — the conversion is never reached and the field stays unknown. That is
    stronger than catching the error afterwards, and it is also what keeps these
    patterns out of `tests/test_regex_bounded_time.py`'s super-linear findings.
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.3-fork\nTrack 1 ripped and encoded successfully!\n"
        f"{line}\n  EAC CRC32:     B0D122E7\n"
    )  # must not raise
    (track,) = log.tracks
    assert track.peak_level is None
    assert track.extraction_speed is None
    assert track.extraction_elapsed_seconds is None
    assert track.appended_silence_frames is None


# --- fork output fidelity (2026-07-31) ---------------------------------------


def test_the_forks_own_peak_percentage_wins_over_the_rounded_dbfs_header() -> None:
    """Two peak statements per track, and the more precise one must win.

    The fork prints BOTH a `Peak level: NN.N%` row (its own, gated behind
    `computed_crcs`) and FFmpeg's `Sample peak:` / `Peak: N.N dBFS` sub-header.
    Converting that 1-decimal dBFS print fabricates *exactly* 100.0% for anything
    peaking 99.43–100%, which in EAC's row means "clipped" — a claim about the
    audio that the ripper never made.

    The reset between tracks is asserted too: a percentage on one track must not
    suppress the next track's reading, which is the bug the flag itself can cause.
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.3.1 (fork)\n"
        "Track 1 ripped and encoded successfully!\n"
        "  Sample peak:\n"
        "    Peak:        -0.0 dBFS\n"
        "  Properties:\n"
        "    Peak level:  99.7%\n"
        "Track 2 ripped and encoded successfully!\n"
        "  Sample peak:\n"
        "    Peak:        -6.0 dBFS\n"
    )
    by_number = {t.number: t for t in log.tracks}
    assert by_number[1].peak_level == pytest.approx(0.997), (
        "the rounded -0.0 dBFS sub-header overwrote the exact 99.7% row, which "
        "renders as a clipped 100.0% in EAC's Peak level"
    )
    assert by_number[2].peak_level == pytest.approx(0.5011872, abs=1e-6), (
        "track 2's own dBFS reading was suppressed by track 1's percentage"
    )


def test_the_ripper_build_tag_is_recorded_without_changing_log_creator() -> None:
    """Which BINARY produced the rip — the only provenance separating a local fork
    build from official 0.9.3.1, which can differ in pre-gap metadata and peaks.

    `log_creator` must stay byte-identical, because both committed reference logs
    and every assertion over them read it.
    """
    for banner, build in (
        ("cyanrip 0.9.3.1 (fork)", "fork"),
        ("cyanrip 0.9.3 (release)", "release"),
        ("cyanrip 0.9.3.1 (git-abcdef1-dirty)", "git-abcdef1-dirty"),
        ("cyanrip 0.9.3", ""),
    ):
        log = parse_cyanrip_log(banner + "\nTracks:\n")
        assert log.ripper_build == build, f"{banner!r} -> {log.ripper_build!r}"
        assert log.log_creator == "cyanrip " + banner.split()[1]
    # Floor: the four cases must not all produce the same answer.
    builds = {
        parse_cyanrip_log(b + "\nTracks:\n").ripper_build
        for b in ("cyanrip 0.9.3.1 (fork)", "cyanrip 0.9.3 (release)", "cyanrip 0.9.3")
    }
    assert len(builds) == 3


def test_a_long_digit_run_in_a_peak_never_fabricates_digital_silence() -> None:
    """`float()` has no 4300-digit ceiling — it returns `-inf`.

    That slipped past the "> 0.0" refusal and computed a concrete peak of exactly
    0.0, i.e. a claim of digital silence, from unparseable input. The never-raises
    contract already held; this is about absent staying absent.
    """
    huge = "9" * 5000
    log = parse_cyanrip_log(
        "cyanrip 0.9.3.1 (fork)\n"
        "Track 1 ripped and encoded successfully!\n"
        "  Sample peak:\n"
        f"    Peak:        -{huge} dBFS\n"
    )
    assert log.tracks[0].peak_level is None, (
        "an unparseable peak produced a concrete value instead of 'not reported'"
    )


# --- H19: `Secure re-read:` is the contract line; `Done;` is stdout progress ----
# Round 7 lap 4 §3e: `Done; (no matches found, but hit repeat limit of N)` is
# progress output, and the purpose-built logfile field is `Secure re-read:`, backed
# by a three-state enum (`NA` / `CONVERGED` / `LIMIT_HIT`) in their source. Only the
# second is a line they undertake not to reword without a round.
#
# We already read both, and the in-block form already wins — but that precedence
# was EMERGENT from line ordering rather than asserted, which is the same shape as
# an invariant that holds by luck. Pinned here.


def test_the_secure_reread_contract_line_wins_over_the_done_progress_line() -> None:
    """When both are present and they disagree, the contract line decides.

    Constructed so the two disagree on purpose: `Done;` says converged, the
    contract line says it did not. A parser preferring the progress line would
    report a track as read-stable when the ripper's own field says otherwise —
    the worst direction for this field to be wrong in.
    """
    log = (
        "cyanrip 0.9.4-rc1+platterpus.4 (platterpus-fork-g5bc654d)\n"
        "Disc tracks:    1\n"
        "  Done; (2 out of 2 matches for current checksum ABCD1234)\n"
        "Track 1 ripped and encoded successfully!\n"
        "  EAC CRC32:     DEADBEEF\n"
        "  Secure re-read:  did NOT converge after 5 reads (repeat limit hit)\n"
        "  File(s):\n"
        "    Artist/Album/01 - A.flac\n"
        "Ripping errors: 0\n"
    )
    parsed = parse_cyanrip_log(log)
    track = next(t for t in parsed.tracks if t.number == 1)
    assert track.secure_rerip_converged is False, (
        "the `Done;` progress line overrode the `Secure re-read:` contract line — "
        "H19: only the second is a line the fork undertakes not to reword"
    )


def test_the_done_line_remains_the_fallback_for_stock_cyanrip() -> None:
    """And `Done;` is not removed, because stock upstream has no contract line.

    Their ask was to *parse* `Secure re-read:`, not to stop reading `Done;` — and
    dropping it would blind us on every stock build, which is the ripper a user has
    before the wizard runs. Keeping a documented fallback is different from
    depending on it.
    """
    log = (
        "cyanrip 0.9.3 (release)\n"
        "Disc tracks:    1\n"
        "  Done; (no matches found, but hit repeat limit of 5)\n"
        "Track 1 ripped and encoded successfully!\n"
        "  EAC CRC32:     DEADBEEF\n"
        "  File(s):\n"
        "    Artist/Album/01 - A.flac\n"
        "Ripping errors: 0\n"
    )
    parsed = parse_cyanrip_log(log)
    track = next(t for t in parsed.tracks if t.number == 1)
    assert track.secure_rerip_converged is False


def test_not_attempted_never_erases_a_measured_verdict() -> None:
    """The third enum state. `NA` means "no verdict here", not "it converged"."""
    log = (
        "cyanrip 0.9.4-rc1+platterpus.4 (platterpus-fork-g5bc654d)\n"
        "Disc tracks:    1\n"
        "  Done; (no matches found, but hit repeat limit of 5)\n"
        "Track 1 ripped and encoded successfully!\n"
        "  EAC CRC32:     DEADBEEF\n"
        "  Secure re-read:  not attempted\n"
        "  File(s):\n"
        "    Artist/Album/01 - A.flac\n"
        "Ripping errors: 0\n"
    )
    track = next(t for t in parse_cyanrip_log(log).tracks if t.number == 1)
    assert track.secure_rerip_converged is False, (
        "'not attempted' erased a measured non-convergence — an absent verdict "
        "must never overwrite a present one"
    )


# --- the offset-variant tally survives a fork-side denominator change -----------
#
# Round 7 lap 25 §A2: from build `f5e11ba` the fork's
# `Tracks ripped partially accurately:` line divides by `nb_tracks` instead of by
# `nb_tracks - accurip_verified`. Same disc, same track, same numerator — the
# DENOMINATOR moves, `1/1` becomes `1/14`.
#
# Our sentence used to paraphrase the old meaning ("N of M track(s) not fully
# verified"), so on a `beta.4` log it would have claimed 14 tracks were not fully
# verified when 13 of them were verified exactly. The fix is to stop paraphrasing
# their fraction and count the offset-variant tracks ourselves.
#
# THE ANCHOR IS A REAL ARTIFACT, not a fixture: the 2026-08-04 rig rip of the EAC
# baseline disc, committed under docs/handshake/artifacts-round-07/. It is the only
# real log in existence carrying this tally, because the block needs an AccurateRip
# database hit and the synthetic discs are not in the database (their §A2, measured).
_RIG_RIP_LOG = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "handshake"
    / "artifacts-round-07"
    / "round-07-lap-23-rig-rip-gc5fb909.log"
)


def test_offset_variant_sentence_is_the_same_on_both_fork_denominators() -> None:
    """`1/1` and `1/14` describe one disc; they must render one sentence."""
    old_shape = render_partially_accurate_summary("1/1", 1, 14)
    new_shape = render_partially_accurate_summary("1/14", 1, 14)
    assert old_shape == new_shape, (
        "the fork's denominator change moved our sentence, so a re-rip of the same "
        "disc on a newer ripper would read as a different result"
    )
    # NON-TRIVIALITY FLOOR: two empty strings are also equal. Assert the sentence
    # actually says something, and specifically that it names the DISC as the
    # population — the whole point of the change.
    assert "1 of 14 tracks" in old_shape, old_shape
    assert "offset-variant" in old_shape, old_shape
    # And the old prose must be gone: it asserted a meaning that is now wrong.
    assert "not fully verified" not in old_shape, (
        "the sentence still claims the denominator counts unverified tracks, which "
        "is false on f5e11ba and later"
    )


def test_the_real_rig_log_renders_the_disc_as_the_population() -> None:
    """Read the committed artifact, not a fixture's idea of one."""
    assert _RIG_RIP_LOG.is_file(), f"missing committed artifact: {_RIG_RIP_LOG}"
    log = parse_cyanrip_log(_RIG_RIP_LOG.read_text(encoding="utf-8", errors="replace"))
    # Floors first: a log that parsed to nothing would satisfy every assertion below.
    assert len(log.tracks) == 14, (
        f"expected the 14-track baseline disc, got {len(log.tracks)}"
    )
    variant = [t.number for t in log.tracks if t.accuraterip_offset is not None]
    assert variant == [5], f"expected exactly track 5 offset-variant, got {variant}"
    # The ripper printed `1/1`; the sentence must describe the disc, and must not
    # flag a disagreement, because there is none — their 1 is our 1.
    assert log.partially_accurate_reported == "1/1"
    assert log.partially_accurate_summary == (
        "1 of 14 tracks matched only an offset-variant pressing (partially accurate)"
    ), log.partially_accurate_summary
    assert "does not agree" not in log.partially_accurate_summary


def test_a_malformed_fraction_is_reported_not_raised() -> None:
    """Parsers never raise. A junk denominator is a mismatch note, not a crash."""
    assert render_partially_accurate_summary("", 1, 14) == "", (
        "an absent tally must render nothing, not a sentence about nothing"
    )
    # Junk where the NUMERATOR should be: we cannot check their count against ours,
    # so the sentence says the two do not agree rather than implying they do.
    for junk in ("x/y", "/", "not-a-fraction", "9/14"):
        out = render_partially_accurate_summary(junk, 1, 14)
        assert "does not agree" in out, (junk, out)
        assert junk in out, "the ripper's own text must appear verbatim in the note"
    # A junk DENOMINATOR is not a disagreement: we never read the denominator, and
    # the numerator still checks out. The raw string is preserved either way.
    assert "does not agree" not in render_partially_accurate_summary("1/", 1, 14)


# --- the fork's parenthetical qualifiers travel with the line they qualify ---------
#
# WHAT HAPPENED (2026-08-17, round 10 lap 3). The fork implemented the shape we chose
# for `HANDSHAKE_RELEASED`: a released build now prints
#
#     Handshake:      round 9 lap 11 closed, verdict GO -- released build
#                     (declared at build time, not verified by cyanrip)
#
# The qualifier IS the fix — it says who declared the claim and that cyanrip did not
# verify it. Every reader here anchored on `^Handshake:`, so we would have captured
# `-- released build` and dropped the disclaimer, surfacing a build's self-assertion as
# though it were verified. Their defect, repaired on their side, re-created on ours by a
# line-oriented parser.


def test_a_released_builds_qualifier_is_not_dropped() -> None:
    """The claim and its disclaimer are one statement, so they parse as one."""
    log = (
        "cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-g3515553)\n"
        "Handshake:      round 9 lap 11 closed, verdict GO -- released build\n"
        "                (declared at build time, not verified by cyanrip)\n"
    )
    note = parse_cyanrip_log(log).handshake_note
    assert "released build" in note
    assert "declared at build time, not verified by cyanrip" in note, (
        "the qualifier was dropped, so the note asserts a verified release when the "
        f"binary explicitly disclaimed one: {note!r}"
    )


def test_the_consumer_qualifier_does_not_migrate_onto_the_handshake_note() -> None:
    """The trap that ruled out a "continuation rule" and forced adjacency-folding.

    `Consumer:` has its own parenthetical two lines later. A rule matching "an
    indented parenthetical after a handshake note" would graft *the caller's*
    disclaimer onto *the build's* claim — two different provenances merged into one
    sentence, which is worse than dropping either.
    """
    log = (
        "cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-g3515553)\n"
        "Handshake:      round 9 lap 11 closed, verdict GO -- released build\n"
        "                (declared at build time, not verified by cyanrip)\n"
        "Consumer:       platterpus/0.6.12b6\n"
        "                (reported by the caller, not verified by cyanrip)\n"
    )
    note = parse_cyanrip_log(log).handshake_note
    assert "reported by the caller" not in note, (
        f"Consumer's qualifier migrated onto the handshake note: {note!r}"
    )
    assert "declared at build time" in note


def test_the_unreleased_rendering_is_unchanged() -> None:
    """Their §D: the unreleased line is byte-identical to before.

    Folding must be invisible to it — a build with no continuation line parses exactly
    as it always did, or the fix has a blast radius it was not supposed to have.
    """
    log = (
        "cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-gb809cfc)\n"
        "Handshake:      round 10 lap 1 OPEN, verdict OPEN -- NOT a released build\n"
    )
    assert (
        parse_cyanrip_log(log).handshake_note
        == "round 10 lap 1 OPEN, verdict OPEN -- NOT a released build"
    )


def test_a_released_note_does_not_read_as_unreleased() -> None:
    """The substring trap, checked against the real token list.

    `"NOT a released build"` contains `"released build"`, so the tokens meaning
    *unreleased* and the new rendering meaning *released* share a substring. Asserted
    against `handshake_approval`'s actual tuple rather than a copy of it, and in both
    directions so the check is discriminating.
    """
    from platterpus.handshake_approval import _NOTE_NOT_RELEASED

    released = (
        "round 9 lap 11 closed, verdict GO -- released build "
        "(declared at build time, not verified by cyanrip)"
    ).casefold()
    unreleased = "round 10 lap 1 OPEN, verdict OPEN -- NOT a released build".casefold()

    assert not [t for t in _NOTE_NOT_RELEASED if t in released], (
        "a released build reads as unreleased — the folded qualifier or a token has "
        "introduced a false match"
    )
    assert [t for t in _NOTE_NOT_RELEASED if t in unreleased], (
        "an unreleased build no longer reads as unreleased, so the tokens have stopped "
        "matching anything and this test proves nothing"
    )


def test_the_per_track_paranoia_counts_are_read_from_the_forks_own_reference() -> None:
    """We asked for these (W1), the fork built them, and we read none of them.

    Their reference log carries **fourteen** indented `Paranoia status counts:`
    blocks — one per track — against a single disc-level block at column 0. Our
    header pattern was anchored at column 0, so all fourteen fell through; and a
    comment in `parsers/rip_log.py` then explained the absence as an upstream gap,
    saying cyanrip *"only emits disc-wide today"*. From inside the parser a missing
    feature and a dropped field look identical. Only the artifact tells them apart,
    and the artifact was committed in this repository the whole time.

    So this test reads the **committed reference**, not a fixture written from a
    belief about it (`CLAUDE.md`: when a committed artifact can settle a question,
    the test should read the artifact).
    """
    from pathlib import Path

    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    reference = (
        Path(__file__).resolve().parents[1]
        / "output_reference"
        / "cyanrip_fork_flac"
        / "cyanrip_fork_police_classics.log"
    )
    assert reference.is_file(), f"the fork's reference log is missing: {reference}"
    rip_log = parse_cyanrip_log(reference.read_text(encoding="utf-8"))

    with_counts = [t for t in rip_log.tracks if t.paranoia_counts]
    assert len(with_counts) == 14, (
        f"{len(with_counts)} of {len(rip_log.tracks)} tracks carry per-track "
        "paranoia counts; the reference has fourteen blocks, so anything less "
        "means the indented header is being missed again"
    )
    assert with_counts[0].paranoia_counts == {
        "READ": 1250,
        "VERIFY": 85,
        "OVERLAP": 17,
    }, with_counts[0].paranoia_counts

    # THE RELATION, which is the whole reason the per-track figures matter: on a
    # rip with no secure re-read the per-track counts must sum to the disc total.
    # (Under `-Z` they deliberately do NOT — the disc total sums every pass while
    # a track's figure is the last pass, which is exactly the over-reporting the
    # disc number alone cannot expose. This reference was ripped without `-Z`.)
    summed: dict[str, int] = {}
    for track in with_counts:
        for key, value in track.paranoia_counts.items():
            summed[key] = summed.get(key, 0) + value
    assert summed == rip_log.paranoia_counts, (
        f"per-track counts sum to {summed} but the disc block says "
        f"{rip_log.paranoia_counts} — on a rip with no secure re-read these must "
        "reconcile exactly"
    )
    # Non-triviality: two empty dicts also compare equal.
    assert summed.get("READ", 0) > 0, (
        "the sum is empty, so it compares equal to anything"
    )


def test_a_log_with_no_per_track_paranoia_block_yields_empty_counts() -> None:
    """Every whipper log, and every cyanrip log before the fork added these, has
    none. The field must be empty rather than absent, so a consumer can tell "this
    log carried no counts" from "this track had none"."""
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    rip_log = parse_cyanrip_log(
        "cyanrip 0.9.3\n\nTracks:\nTrack 1 ripped and encoded successfully!\n"
        "  EAC CRC32:     B0D122E7\n"
    )
    assert rip_log.tracks, "the minimal log parsed no tracks at all"
    assert rip_log.tracks[0].paranoia_counts == {}
