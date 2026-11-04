"""`.29`'s proposed log wordings, read before the build exists (the fork's round 38 lap 1).

The fork's lap (``cyanrip@f1bcb683:docs/handshake/round-38-lap-01.md``) proposes
six changes for ``.29`` and asks that a release of ours read each first. Five are
log lines, held here; S10, the ``-j`` record's ``block_crcs``, is
``tests/test_record_block_crcs.py``.

**Every ``.29`` line below is HAND-MADE from the lap's wording.** No ``.29`` log
exists yet: the log is the fork's golden reference shape
(``cyanrip@f1bcb683:docs/golden-reference.log``) with the lap's lines put where
the lap says they print, so it pins our reading of the lap, not their build.

* S5: ``Secure re-reads:`` above ``Ripping errors:`` under ``-Z``, never a read
  error for the speed ladder (``secure_rereads_footer``).
* S6: the accuracy tallies divide by the tracks the rip read (``-l 2,3`` prints
  ``/2``); ``-f`` prints neither; a cancelled track no longer adds to
  ``Ripping errors:``.
* S7: ``Filtered:`` after a track's ``Accurip`` rows (``ripper_track_notes``).
* S8: ``Pregap length: A or B frames (undecided)``: a range, never A.
* S9: ``Embedded cover art: none (...)``: never read as a picture embedded.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus import ripper_track_notes as notes
from platterpus import secure_rereads_footer as footer
from platterpus.eac_log_export import render_eac_style_log
from platterpus.ladder_trigger import judge_step_down
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.read_speed_ladder import read_errors_present
from platterpus.rip_audit import LEVEL_WARN, AlbumAudit, _audit_cue_integrity
from platterpus.rip_report import build_report
from platterpus.uiscript import pregap_grading

#: The lap's S7 tail, word for word.
_FILTERED: Final[str] = (
    "  Filtered:      hdcd, de-emphasis; the checksums and AccurateRip verdicts "
    "above are of the read, before the filter"
)

#: S9's line as the lap spells it, with an AV1 cover (the review's B6 case).
_COVER_NONE: Final[str] = (
    "  Embedded cover art: none (the output cannot hold a AV1 (AOMedia Video 1) "
    "picture; saved as o/cover (1).avif)"
)


def _log(
    *,
    secure: str = "Secure re-reads: 1 track did not converge (track 3)",
    errors: str = "Ripping errors: 0",
    completed: str = "Rip completed:  yes (2 of 3 tracks)",
    tallies: str = "Tracks ripped accurately: 1/2\n",
) -> str:
    """A hand-made `.29` log of tracks 2 and 3 of a 3-track disc, under `-Z 2`."""
    return f"""cyanrip 0.9.4-rc3+platterpus.29 (platterpus-fork-g0000000)
Invoked as:     cyanrip -d /dev/sr0 -N -Z 2 -G -U -W -l 2,3
Disc tracks:    3
Tracks to rip:  2,3
DiscID:         oMp2k.ixH0QqrdaZzsARoRS.p6c-
Gaps:
    150 frame pregap in track 1, unmerged
    75 frame pregap in track 2, merging into track 1
    pregap of track 3 unknown (sub-channel search bounds did not meet)

Tracks:

Done; (2 out of 2 matches for current checksum 07B89F6F)
Track 2 read with no error reported.
Summary:

  Properties:
    Pregap LSN:  300 (duration: 00:01.00)
    Pregap length: 75 frames
    Pregap source: TOC
    Start LSN:   375
    End LSN:     524

  EAC CRC32:     07B89F6F (after 3 rips)
  Secure re-read:  converged after 3 reads
  Accurip:       disc found in database (max confidence: 12)
    Accurip v1:  7A5C1F5E (accurately ripped, confidence 12)
    Accurip v2:  EE56C11B
{_FILTERED}

  Metadata:
    TRACK:                         2

  Paranoia status counts:
    READ:          10

{_COVER_NONE}

  File(s):
    o/2.flac

Done; (no matches found)
Track 3 read with errors.
Summary:

  Properties:
    Pregap LSN:  unknown (sub-channel search bounds did not meet)
    Pregap length: 94 or 95 frames (undecided)
    Start LSN:   525
    End LSN:     599

  EAC CRC32:     CC206A3D (after 5 rips)
  Secure re-read:  did NOT converge after 5 reads (repeat limit hit)
  Accurip:       disc found in database (max confidence: 12)
    Accurip v1:  CEDEB120 (not found, either a new pressing, or bad rip)
    Accurip v2:  E856170A (not found, either a new pressing, or bad rip)
    Accurip 450: 00001234 (not found)

  Metadata:
    TRACK:                         3

  File(s):
    o/3.flac

{tallies}
Paranoia status counts:
  READ:          90

{secure}
{errors}
Encoder errors: none; 2 tracks encoded
{completed}
"""


# --- S5: Secure re-reads ------------------------------------------------------------


def test_s5_the_footer_line_is_read_and_agrees_with_the_track_rows() -> None:
    parsed = parse_cyanrip_log(_log())
    assert parsed.secure_rereads is not None
    assert parsed.secure_rereads.state == footer.SOME_DID_NOT_CONVERGE
    assert parsed.secure_rereads.tracks == (3,)
    block = build_report(parsed)["rip"]["secure_rereads"]
    assert block["did_not_converge_tracks"] == [3]
    assert block["agrees_with_track_blocks"] is True


def test_s5_both_arms_and_the_notations_the_lap_leaves_open() -> None:
    def read(value: str) -> footer.SecureRereads:
        return footer.read_value(value)

    assert read("every track converged").state == footer.ALL_CONVERGED
    for value in (
        "2 tracks did not converge (tracks 3, 10)",
        "2 track(s) did not converge (track(s) 3,10)",
        "2 tracks did not converge (tracks 3 and 10)",
    ):
        assert read(value).tracks == (3, 10), value
    cut = read("3 tracks did not converge (tracks 3, 10, list truncated)")
    assert cut.truncated and cut.tracks == (3, 10)
    # A count the list contradicts is the line disagreeing with itself.
    assert read("2 tracks did not converge (tracks 3)").state == footer.UNRECOGNISED
    assert read("1 track did not converge (tracks 3, 4)").state == footer.UNRECOGNISED


def test_s5_a_footer_naming_other_tracks_is_an_info_issue() -> None:
    parsed = parse_cyanrip_log(
        _log(secure="Secure re-reads: 1 track did not converge (track 2)")
    )
    report = build_report(parsed)
    assert report["rip"]["secure_rereads"]["agrees_with_track_blocks"] is False
    found = [i for i in report["issues"] if i["code"] == footer.ISSUE_DISAGREES]
    assert found and found[0]["severity"] == "info"


def test_s5_no_line_is_null_never_all_converged() -> None:
    parsed = parse_cyanrip_log(_log(secure=""))
    assert parsed.secure_rereads is None
    assert build_report(parsed)["rip"]["secure_rereads"] is None


def test_s5_non_convergence_is_never_a_drive_error_for_the_ladder() -> None:
    """`Ripping errors: 0` beside a track that did not converge: no step down."""
    parsed = parse_cyanrip_log(_log())
    assert parsed.drive_read_errors == 0
    assert read_errors_present(parsed) is False
    decision = judge_step_down(
        parsed, exit_code=0, stopped_by_us=False, log_is_this_passes=True
    )
    assert decision.warranted is False


# --- S6: the tallies' denominators, -f, and a cancelled track -------------------------


def test_s6a_a_tally_over_the_tracks_read_reads_and_misreports_nothing() -> None:
    """`-l 2,3` prints `/2`: quoted verbatim, and our own sentences keep the disc."""
    parsed = parse_cyanrip_log(
        _log(
            tallies="Tracks ripped accurately: 1/2\n"
            "Tracks matched on one frame only: 0/2\n"
        )
    )
    assert parsed.accuraterip_summary.startswith("1/2 tracks ripped accurately")
    assert parsed.partially_accurate_reported == "0/2"
    report = build_report(parsed)
    assert report["accuraterip_summary"].startswith("1/2 ")
    # Our sentence counts per track and names the disc's count from `Rip
    # completed:` (3), never the footer's denominator; numerators agree, so no
    # disagreement is invented.
    partial = report["partially_accurate_summary"] or ""
    assert "does not agree" not in partial


def test_s6b_an_offset_search_log_without_either_tally_parses() -> None:
    parsed = parse_cyanrip_log(
        _log(
            tallies="",
            completed="Rip completed:  no (offset search only, 0 of 3 tracks)",
        )
    )
    assert parsed.accuraterip_summary == ""
    assert parsed.partially_accurate_reported == ""
    assert build_report(parsed)["accuraterip_summary"] is None


def test_s6c_a_cancel_with_no_read_error_reads_as_cancelled_not_clean() -> None:
    """`.29` stops adding 1 for the cancelled track; nothing relied on that 1."""
    log = _log(
        errors="Ripping errors: 0",
        completed="Rip completed:  no (interrupted by SIGTERM, 1 of 3 tracks)\n"
        "Interrupted at: track 3, mid-read",
    )
    parsed = parse_cyanrip_log(log)
    assert parsed.ripping_errors == 0
    assert parsed.rip_completed is False
    decision = judge_step_down(
        parsed, exit_code=143, stopped_by_us=True, log_is_this_passes=True
    )
    assert decision.warranted is False
    eac = render_eac_style_log(parsed, outcome_status="cancelled", disc_track_total=3)
    assert "Ripper's own completion record : no (interrupted by SIGTERM" in eac
    assert "Interrupted at : track 3, mid-read" in eac


# --- S7: Filtered -------------------------------------------------------------------


def test_s7_the_filtered_line_is_read_and_said_beside_the_verdict() -> None:
    parsed = parse_cyanrip_log(_log())
    two = next(t for t in parsed.tracks if t.number == 2)
    assert two.filtered is not None
    assert two.filtered.filters == ("hdcd", "de-emphasis")
    report = build_report(parsed)
    row = next(t for t in report["tracks"] if t["number"] == 2)
    assert row["filtered"]["filters"] == ["hdcd", "de-emphasis"]
    codes = [i["code"] for i in report["issues"] if i["severity"] == "warning"]
    assert notes.ISSUE_FILTERED in codes
    eac = render_eac_style_log(parsed, disc_track_total=3)
    assert "Filtered: hdcd and de-emphasis changed the audio written" in eac
    # Track 3 had no line, and nothing claims a filter for it.
    three = next(t for t in report["tracks"] if t["number"] == 3)
    assert three["filtered"] is None
    assert eac.count("Filtered:") == 1


def test_s7_names_and_joins_the_lap_leaves_open() -> None:
    tail = notes.FILTERED_TAIL
    assert notes.read_filtered(f"hdcd{tail}").filters == ("hdcd",)
    assert notes.read_filtered(f"de-emphasis{tail}").filters == ("de-emphasis",)
    for join in (", ", " and ", "+"):
        both = notes.read_filtered(f"de-emphasis{join}hdcd{tail}")
        assert both.filters == ("hdcd", "de-emphasis"), join
    assert notes.read_filtered("hdcd").state == notes.UNRECOGNISED
    assert notes.read_filtered(f"loudnorm{tail}").state == notes.UNRECOGNISED
    assert notes.read_filtered(f"hdcd, hdcd{tail}").state == notes.UNRECOGNISED


def test_s7_a_filtered_line_inside_the_echo_is_refused() -> None:
    """Printed before `Metadata:`; after it, it can only be an echoed CD-TEXT value."""
    moved = _log().replace(
        _FILTERED + "\n\n  Metadata:\n", "\n  Metadata:\n" + _FILTERED + "\n"
    )
    parsed = parse_cyanrip_log(moved)
    assert next(t for t in parsed.tracks if t.number == 2).filtered is None


# --- S8: an undecided pre-gap ---------------------------------------------------------


def test_s8_an_undecided_pregap_is_a_range_and_never_the_first_bound() -> None:
    parsed = parse_cyanrip_log(_log())
    three = next(t for t in parsed.tracks if t.number == 3)
    assert three.pregap_state == "unknown"
    assert three.pregap_undecided_frames == (94, 95)
    assert three.pregap_length_frames is None
    assert three.pregap_sectors is None
    row = next(t for t in build_report(parsed)["tracks"] if t["number"] == 3)
    assert row["pregap_undecided_frames"] == [94, 95]
    assert row["pregap_length_frames"] is None
    eac = render_eac_style_log(parsed, disc_track_total=3)
    assert "not determined by the ripper" in eac
    assert "94 or 95 frames, undecided" in eac
    assert "Pre-gap length  0:00:01.25" not in eac  # 94 frames as a length


def test_s8_without_the_lsn_row_the_range_still_reads_as_not_determined() -> None:
    log = _log().replace(
        "    Pregap LSN:  unknown (sub-channel search bounds did not meet)\n", ""
    )
    three = next(t for t in parse_cyanrip_log(log).tracks if t.number == 3)
    assert three.pregap_state == "unknown"
    assert three.pregap_unknown_reason == "undecided"


def test_s8_an_lsn_row_in_the_range_shape_is_not_read_as_a_known_lsn() -> None:
    log = (
        "cyanrip 0.9.4\nTrack 9 ripped and encoded successfully!\n"
        "    Pregap LSN:  12345 or 12346 (undecided)\n"
    )
    track = parse_cyanrip_log(log).tracks[0]
    assert track.pregap_state != "known"
    assert track.pregap_start_lsn is None


def test_s8_the_pregap_comparison_names_the_range_and_compares_no_number() -> None:
    reading = pregap_grading.read_gap_list(_log(), "a")
    assert reading.pregaps is not None and reading.pregaps[3] is None
    assert "94 or 95 frames, undecided" in reading.unknown_notes[3]


def test_s8_a_cue_marker_at_the_earlier_bound_is_not_called_a_mismatch() -> None:
    """`INDEX 00` B frames before `INDEX 01`, under track 2's file (the lap's S8)."""
    report: dict[str, Any] = build_report(parse_cyanrip_log(_log()))
    # Track 2 is 375..524, 150 frames; 95 frames before its end is 00:00:55.
    report["artifacts"] = {
        "cue": {
            "text": (
                'FILE "2.flac" WAVE\n'
                "  TRACK 02 AUDIO\n"
                "    INDEX 01 00:00:00\n"
                "  TRACK 03 AUDIO\n"
                "    INDEX 00 00:00:55\n"
                'FILE "3.flac" WAVE\n'
                "    INDEX 01 00:00:00\n"
            ),
            "truncated": False,
        }
    }
    report["outcome"] = {**(report.get("outcome") or {}), "ripper_argv": []}
    report["outcome"]["ripper_argv"] = ["cyanrip", "-l", "2,3"]
    album = AlbumAudit(folder=Path("."))
    _audit_cue_integrity(report, album)
    warned = [f.text for f in album.findings if f.level == LEVEL_WARN]
    assert not [text for text in warned if "INDEX 00" in text or "pre-gap" in text]
    # The floor: the marker WAS examined, and placed where the lap says.
    assert any("all 1 INDEX 00 pre-gap marker(s)" in f.text for f in album.findings)


# --- S9: Embedded cover art -----------------------------------------------------------


def test_s9_none_is_read_as_none_and_never_as_embedded() -> None:
    parsed = parse_cyanrip_log(_log())
    two = next(t for t in parsed.tracks if t.number == 2)
    assert two.ripper_cover_art is not None
    assert two.ripper_cover_art.state == notes.COVER_NONE
    assert two.ripper_cover_art.codec == "AV1 (AOMedia Video 1)"
    assert two.ripper_cover_art.saved_as == "o/cover (1).avif"
    report = build_report(parsed)
    row = next(t for t in report["tracks"] if t["number"] == 2)
    assert row["ripper_cover_art"]["state"] == "none"
    # Our own embedding is a separate block, never filled from the ripper's log.
    assert report["cover_art"] is None


def test_s9_the_two_line_form_and_other_values() -> None:
    assert notes.read_cover_art(None).state == notes.COVER_STATED_EMBEDDED
    assert notes.read_cover_art("none").state == notes.COVER_NONE
    assert notes.read_cover_art("none (something else)").codec is None
    assert notes.read_cover_art("Front: 500x500 JPEG").state == notes.UNRECOGNISED


# --- never raises ---------------------------------------------------------------------


@settings(max_examples=400, deadline=None)
@given(st.text(max_size=160))
def test_the_new_readers_never_raise(text: str) -> None:
    footer.read_value(text)
    notes.read_filtered(text)
    notes.read_filtered(text + notes.FILTERED_TAIL)
    notes.read_cover_art(text)
    notes.read_cover_art("none (the output cannot hold a " + text)
    for line in (
        "Secure re-reads: " + text,
        "    Pregap length: " + text,
        "  Filtered:      " + text,
        "  Embedded cover art: " + text,
    ):
        for pattern in (
            footer.LINE,
            notes.PREGAP_LENGTH_UNDECIDED,
            notes.FILTERED_LINE,
            notes.EMBEDDED_COVER_ART_LINE,
        ):
            pattern.match(line)
        match = notes.PREGAP_LENGTH_UNDECIDED.match(line)
        if match:
            notes.read_undecided(match)


@settings(max_examples=150, deadline=None)
@given(st.text(max_size=200))
def test_the_parser_never_raises_on_a_mangled_round38_line(text: str) -> None:
    parse_cyanrip_log(_log(secure="Secure re-reads: " + text))
    parse_cyanrip_log(_log().replace("94 or 95 frames (undecided)", text))
