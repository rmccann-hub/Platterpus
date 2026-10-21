"""The three log lines the fork's `.26` adds, read into the parse and the report.

The fork proposes them in its round 36 lap 1 (S4 to S6), and `.26` is released only
once our reader takes them. This file is read against their draft, at
`cyanrip@cef0f629` (their branch `claude/pending-task-vg2afd`), and is to be
confirmed against the lap as released:

* `Accurate stream:`, a disc-header line below `C2 errors:`
  (`cyanrip@cef0f629:src/cyanrip_log.c:967`), worded by
  `cyanrip@cef0f629:src/drive_caps.c:85-97`;
* `Recordable:`, below it (`cyanrip@cef0f629:src/cyanrip_log.c:969-970`), worded by
  `cyanrip@cef0f629:src/drive_caps.c:59-83`;
* the two-search form of `Pregap source:`
  (`cyanrip@cef0f629:src/cyanrip_log.c:432-440`).

**Where the lines come from.** The fixture `cyanrip_fork_golden_reference_r36.log`
is `cyanrip@cef0f629:docs/golden-reference.log` byte for byte (sha256
`9f4cad75…99f5`), which carries the two header lines in their image wording. No
image reaches a drive's arm, so every other wording is the golden reference with
its value replaced by the string the fork's source prints, cited beside each case,
and the pre-gap form is the line their `tests/logrender.c` pins, put into a track
block of the same log.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus.parsers import cyanrip_log
from platterpus.parsers.cyanrip_log import (
    PREGAP_SOURCE_SUB_CHANNEL,
    accurate_stream_state,
    parse_cyanrip_log,
    recordable_state,
)
from platterpus.parsers.rip_log import (
    ACCURATE_STREAM_STATES,
    DRIVE_FACT_NOT_PRESENT,
    DRIVE_FACT_UNRECOGNISED,
    RECORDABLE_STATES,
)
from platterpus.rip_report import build_report

_FIXTURES = Path(__file__).parent / "fixtures"
# cyanrip@cef0f629:docs/golden-reference.log, verbatim.
_R36_LOG = _FIXTURES / "cyanrip_fork_golden_reference_r36.log"
# The `.24` golden reference: a build that prints none of the three lines.
_R35_LOG = _FIXTURES / "cyanrip_fork_golden_reference_r35.log"

# cyanrip@cef0f629:docs/golden-reference.log:13-14, the two lines as an image rip
# prints them.
_ACCURATE_LINE = "Accurate stream: unknown (image)\n"
_RECORDABLE_LINE = "Recordable:     unknown (image)\n"

# The three P2 format strings as the fork's regenerated provider contract lists
# them (`cyanrip@cef0f629:PROVIDER-CONTRACT.md:294`, `:372` and `:373`, generated
# by their `1d1f0ab`). Copied here, not built from our patterns, so a test that
# fills them in checks our reader against their text.
_P2_ACCURATE = "Accurate stream: %s"
_P2_RECORDABLE = "Recordable:     %s"
_P2_TWO_SEARCHES = (
    "Pregap source: sub-channel (not signalled by TOC; two searches read %i and "
    "%i frames, the first is used)"
)

# Track 2's pre-gap rows in the golden reference (lines 159-160); the two-search
# line replaces its `Pregap source:` row.
_TRACK2_PREGAP = "    Pregap length: 75 frames\n    Pregap source: TOC\n"


def _golden() -> str:
    return _R36_LOG.read_text(encoding="utf-8")


def _with_header(accurate: str | None = None, recordable: str | None = None) -> str:
    """The golden reference with either header line's VALUE replaced."""
    text = _golden()
    # Floors: each anchor is there, once, so a replacement cannot silently miss.
    assert text.count(_ACCURATE_LINE) == 1
    assert text.count(_RECORDABLE_LINE) == 1
    if accurate is not None:
        text = text.replace(_ACCURATE_LINE, (_P2_ACCURATE % accurate) + "\n", 1)
    if recordable is not None:
        text = text.replace(_RECORDABLE_LINE, (_P2_RECORDABLE % recordable) + "\n", 1)
    return text


def _with_pregap_line(line: str) -> str:
    """The golden reference with track 2's `Pregap source:` row replaced by `line`."""
    text = _golden()
    assert text.count(_TRACK2_PREGAP) == 1  # floor: lands, and once
    return text.replace(_TRACK2_PREGAP, "    Pregap length: 75 frames\n" + line, 1)


# --- the golden reference as published ------------------------------------------


def test_the_golden_reference_carries_both_header_lines_below_c2_errors() -> None:
    """Where the fork puts them (round 36 lap 1 S4, S5): the two lines directly
    below `C2 errors:`, in that order (cyanrip@cef0f629:docs/golden-reference.log:12-14)."""
    lines = _golden().splitlines()
    c2 = lines.index("C2 errors:      unsupported by drive")
    assert lines[c2 + 1 : c2 + 3] == [_ACCURATE_LINE[:-1], _RECORDABLE_LINE[:-1]]


def test_the_golden_reference_parses_to_the_image_states() -> None:
    log = parse_cyanrip_log(_golden())
    info = log.ripping_info

    assert len(log.tracks) == 3  # floor: the whole log was read
    assert (info.accurate_stream, info.accurate_stream_reason) == ("unknown", "image")
    assert (info.recordable, info.recordable_reason) == ("unknown", "image")
    # No track of the image rip printed two searches.
    assert [t.pregap_search_frames for t in log.tracks] == [None, None, None]


def test_every_top_level_line_of_the_golden_reference_is_accounted_for() -> None:
    """The completeness sweep's question, asked of the `.26` golden reference: the
    two header lines must be claimed, or `.26` trips every rip's sweep (their S2)."""
    top_level = [
        line for line in _golden().splitlines() if line and not line[0].isspace()
    ]
    assert len(top_level) >= 40  # floor
    claimed_by_new_rules = [
        line
        for line in top_level
        if any(
            rule.pattern.match(line)
            for rule in cyanrip_log._ALL_LINE_RULES
            if rule.name in {"accurate_stream", "recordable"}
        )
    ]
    assert claimed_by_new_rules == [_ACCURATE_LINE[:-1], _RECORDABLE_LINE[:-1]]


# --- Accurate stream: -----------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # cyanrip@cef0f629:src/drive_caps.c:89
        (
            "declared supported by drive (capabilities page, not measured)",
            ("declared_supported", "capabilities page, not measured"),
        ),
        # cyanrip@cef0f629:src/drive_caps.c:91
        ("declared unsupported by drive", ("declared_unsupported", "")),
        # cyanrip@cef0f629:src/drive_caps.c:93
        ("unknown (image)", ("unknown", "image")),
        # cyanrip@cef0f629:src/drive_caps.c:97
        (
            "unknown (capabilities page not readable)",
            ("unknown", "capabilities page not readable"),
        ),
    ],
)
def test_each_accurate_stream_wording_is_read(
    value: str, expected: tuple[str, str]
) -> None:
    info = parse_cyanrip_log(_with_header(accurate=value)).ripping_info
    assert (info.accurate_stream, info.accurate_stream_reason) == expected
    # The other line is untouched by this one.
    assert (info.recordable, info.recordable_reason) == ("unknown", "image")


def test_an_unrecognised_accurate_stream_wording_is_kept_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A reworded value claims its line but is not squeezed into a known state:
    `measured accurate` is not `declared_supported`, whatever it resembles."""
    with caplog.at_level("WARNING", logger="platterpus.parsers.cyanrip_log"):
        info = parse_cyanrip_log(
            _with_header(accurate="measured accurate by drive")
        ).ripping_info
    assert info.accurate_stream == DRIVE_FACT_UNRECOGNISED
    assert info.accurate_stream_reason == "measured accurate by drive"
    assert any("Accurate stream:" in r.getMessage() for r in caplog.records)


# --- Recordable: ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # cyanrip@cef0f629:src/drive_caps.c:69
        ("no, CD-ROM (drive's current profile)", ("cdrom", "drive's current profile")),
        # cyanrip@cef0f629:src/drive_caps.c:72
        ("yes, CD-R (drive's current profile)", ("cdr", "drive's current profile")),
        # cyanrip@cef0f629:src/drive_caps.c:75
        ("yes, CD-RW (drive's current profile)", ("cdrw", "drive's current profile")),
        # cyanrip@cef0f629:src/drive_caps.c:63
        ("unknown (image)", ("unknown", "image")),
        # cyanrip@cef0f629:src/drive_caps.c:66
        ("unknown (profile not readable)", ("unknown", "profile not readable")),
        # cyanrip@cef0f629:src/drive_caps.c:78, `0x%04x` filled as their
        # tests/drivecaps.c:156 fills it.
        (
            "unknown (profile 0x0010 is not a CD profile)",
            ("unknown", "profile 0x0010 is not a CD profile"),
        ),
    ],
)
def test_each_recordable_wording_is_read(value: str, expected: tuple[str, str]) -> None:
    info = parse_cyanrip_log(_with_header(recordable=value)).ripping_info
    assert (info.recordable, info.recordable_reason) == expected
    assert (info.accurate_stream, info.accurate_stream_reason) == ("unknown", "image")


@pytest.mark.parametrize(
    "value",
    [
        # An answer word that contradicts its profile: not resolved either way.
        "yes, CD-ROM (drive's current profile)",
        "no, CD-R (drive's current profile)",
        # A profile the fork does not name.
        "yes, DVD-R (drive's current profile)",
        # A bare answer with nothing to say what it answers.
        "yes",
    ],
)
def test_an_unrecognised_or_contradictory_recordable_is_kept_and_logged(
    value: str, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("WARNING", logger="platterpus.parsers.cyanrip_log"):
        info = parse_cyanrip_log(_with_header(recordable=value)).ripping_info
    assert (info.recordable, info.recordable_reason) == (DRIVE_FACT_UNRECOGNISED, value)
    assert any("Recordable:" in r.getMessage() for r in caplog.records)


# --- an older build ---------------------------------------------------------------


def test_a_build_without_the_lines_is_not_present_never_a_negative() -> None:
    """`.24` prints neither header line: `not_present`, which says nothing about
    the drive. Not `declared_unsupported`, not `cdrom`."""
    log = parse_cyanrip_log(_R35_LOG.read_text(encoding="utf-8"))
    info = log.ripping_info

    assert len(log.tracks) == 3  # floor
    assert (info.accurate_stream, info.accurate_stream_reason) == (
        DRIVE_FACT_NOT_PRESENT,
        "",
    )
    assert (info.recordable, info.recordable_reason) == (DRIVE_FACT_NOT_PRESENT, "")
    assert [t.pregap_search_frames for t in log.tracks] == [None, None, None]


# --- Pregap source: two searches ----------------------------------------------------


@pytest.mark.parametrize(
    ("first", "second"),
    [
        # The reference disc's track 9 (cyanrip@cef0f629:tests/logrender.c:885).
        (94, 95),
        # Track 4's 158 read as 0 by one search (tests/logrender.c:889).
        (0, 158),
    ],
)
def test_two_disagreeing_searches_are_read_as_a_pair(first: int, second: int) -> None:
    log = parse_cyanrip_log(
        _with_pregap_line("    " + _P2_TWO_SEARCHES % (first, second) + "\n")
    )
    assert len(log.tracks) == 3  # floor: the other tracks were read, so None is a read
    track = log.tracks[1]
    assert track.pregap_search_frames == (first, second)
    # The provenance is the same as the agreeing form's; the counts are the
    # second fact, in their own field.
    assert track.pregap_source == PREGAP_SOURCE_SUB_CHANNEL
    assert track.pregap_source == "sub-channel (not signalled by TOC)"
    # The pre-gap length is still the one `Pregap length:` stated.
    assert track.pregap_length_frames == 75
    assert [t.pregap_search_frames for t in (log.tracks[0], log.tracks[2])] == [
        None,
        None,
    ]


def test_the_lines_verbatim_text_from_their_test_is_read() -> None:
    """The line exactly as `cyanrip@cef0f629:tests/logrender.c:885` pins it, typed
    out rather than filled from a format string."""
    line = (
        "    Pregap source: sub-channel (not signalled by TOC; two searches read 94 "
        "and 95 frames, the first is used)\n"
    )
    assert parse_cyanrip_log(_with_pregap_line(line)).tracks[
        1
    ].pregap_search_frames == (
        94,
        95,
    )


def test_the_agreeing_form_still_reads_as_before() -> None:
    """`cyanrip@cef0f629:src/cyanrip_log.c:443`: no pair, the source verbatim."""
    track = parse_cyanrip_log(
        _with_pregap_line("    Pregap source: sub-channel (not signalled by TOC)\n")
    ).tracks[1]
    assert track.pregap_source == "sub-channel (not signalled by TOC)"
    assert track.pregap_search_frames is None


def test_a_reworded_trailer_is_kept_verbatim_not_read_as_the_first_used() -> None:
    """A build that ripped the SECOND search would not be saying "the first is
    used": the line is kept whole as the source, and no pair is claimed."""
    value = (
        "sub-channel (not signalled by TOC; two searches read 94 and 95 frames, "
        "the second is used)"
    )
    track = parse_cyanrip_log(
        _with_pregap_line(f"    Pregap source: {value}\n")
    ).tracks[1]
    assert track.pregap_source == value
    assert track.pregap_search_frames is None


# --- never raises -------------------------------------------------------------------


@given(st.text(max_size=300))
def test_accurate_stream_state_never_raises(value: str) -> None:
    state, reason = accurate_stream_state(value)
    assert state in ACCURATE_STREAM_STATES - {DRIVE_FACT_NOT_PRESENT}
    assert isinstance(reason, str)


@given(st.text(max_size=300))
def test_recordable_state_never_raises(value: str) -> None:
    state, reason = recordable_state(value)
    assert state in RECORDABLE_STATES - {DRIVE_FACT_NOT_PRESENT}
    assert isinstance(reason, str)


@given(st.text(max_size=200), st.text(max_size=200), st.text(max_size=200))
def test_the_parser_never_raises_on_any_of_the_three_lines(
    accurate: str, recordable: str, pregap: str
) -> None:
    text = _with_header(accurate=accurate, recordable=recordable)
    text = text.replace(
        _TRACK2_PREGAP, f"    Pregap length: 75 frames\n    Pregap source: {pregap}\n"
    )
    parse_cyanrip_log(text)


@given(st.integers(-(10**9) + 1, 10**9 - 1), st.integers(-(10**9) + 1, 10**9 - 1))
def test_any_pair_the_ripper_can_print_is_read_exactly(first: int, second: int) -> None:
    line = "    " + _P2_TWO_SEARCHES % (first, second) + "\n"
    assert parse_cyanrip_log(_with_pregap_line(line)).tracks[
        1
    ].pregap_search_frames == (
        first,
        second,
    )


# --- the report ---------------------------------------------------------------------


def _codes(report: dict) -> set[str]:
    return {issue["code"] for issue in report["issues"]}


@pytest.mark.parametrize(
    ("value", "state", "name"),
    [
        ("yes, CD-R (drive's current profile)", "cdr", "CD-R"),
        ("yes, CD-RW (drive's current profile)", "cdrw", "CD-RW"),
    ],
)
def test_a_recordable_disc_is_visible_in_the_report(
    value: str, state: str, name: str
) -> None:
    report = build_report(parse_cyanrip_log(_with_header(recordable=value)))

    assert report["rip"]["recordable"] == state
    assert report["rip"]["recordable_reason"] == "drive's current profile"
    found = [i for i in report["issues"] if i["code"] == "recordable_disc"]
    assert len(found) == 1
    assert found[0]["severity"] == "info"
    assert f"({name}," in found[0]["message"]


@pytest.mark.parametrize(
    "value",
    [
        "no, CD-ROM (drive's current profile)",
        "unknown (profile not readable)",
        "yes, CD-ROM (drive's current profile)",  # unrecognised: says nothing
    ],
)
def test_a_pressed_unknown_or_unreadable_disc_raises_no_recordable_issue(
    value: str,
) -> None:
    report = build_report(parse_cyanrip_log(_with_header(recordable=value)))
    assert "recordable_disc" not in _codes(report)


def test_the_report_carries_the_accurate_stream_state_and_reason() -> None:
    report = build_report(
        parse_cyanrip_log(
            _with_header(
                accurate="declared supported by drive (capabilities page, not measured)"
            )
        )
    )
    assert report["rip"]["accurate_stream"] == "declared_supported"
    assert report["rip"]["accurate_stream_reason"] == "capabilities page, not measured"


def test_an_older_build_reports_not_present_and_raises_nothing() -> None:
    report = build_report(parse_cyanrip_log(_R35_LOG.read_text(encoding="utf-8")))

    assert report["rip"]["accurate_stream"] == "not_present"
    assert report["rip"]["accurate_stream_reason"] is None
    assert report["rip"]["recordable"] == "not_present"
    assert report["rip"]["recordable_reason"] is None
    assert len(report["tracks"]) == 3  # floor
    assert [row["pregap_search_frames"] for row in report["tracks"]] == [
        None,
        None,
        None,
    ]
    assert not {"recordable_disc", "pregap_searches_disagree"} & _codes(report)


def test_a_disagreeing_pregap_is_visible_in_the_report() -> None:
    report = build_report(
        parse_cyanrip_log(
            _with_pregap_line("    " + _P2_TWO_SEARCHES % (94, 95) + "\n")
        )
    )
    rows = report["tracks"]

    assert len(rows) == 3  # floor
    assert rows[1]["pregap_search_frames"] == [94, 95]
    assert rows[1]["pregap_source"] == "sub-channel (not signalled by TOC)"
    assert rows[0]["pregap_search_frames"] is None
    found = [i for i in report["issues"] if i["code"] == "pregap_searches_disagree"]
    assert len(found) == 1
    assert found[0]["severity"] == "info"
    assert "track 2" in found[0]["message"]
    assert "94 and 95 frames" in found[0]["message"]


def test_the_image_golden_reference_raises_neither_new_issue() -> None:
    report = build_report(parse_cyanrip_log(_golden()))
    assert report["rip"]["recordable"] == "unknown"
    assert report["rip"]["accurate_stream"] == "unknown"
    assert not {"recordable_disc", "pregap_searches_disagree"} & _codes(report)
