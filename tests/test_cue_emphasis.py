"""The cue's ``FLAGS PRE`` against the argv and cyanrip's pre-emphasis reading.

``platterpus.cue_emphasis`` holds the rule; ``test_uiscript_planted_faults``
plants each fault in the round-29 report and runs the real audit. This file pins
the pure pieces, the tri-state above all: an unknown fact is *not determined*,
never a pass and never a failure.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus.cue_emphasis import (
    KEPT,
    NOT_DETERMINED,
    REMOVED,
    check_flags_pre,
    emphasis_handling,
    handling_of_passes,
)
from platterpus.cue_validate import (
    LEVEL_NOTE,
    LEVEL_OK,
    LEVEL_WARN,
    CueFinding,
    parse_cue,
)

_CUE = (
    'FILE "01.flac" WAVE\n'
    "  TRACK 01 AUDIO\n"
    "{flags1}"
    "    INDEX 01 00:00:00\n"
    'FILE "02.flac" WAVE\n'
    "  TRACK 02 AUDIO\n"
    "{flags2}"
    "    INDEX 01 00:00:00\n"
)


def _cue(flags1: str = "", flags2: str = "") -> str:
    return _CUE.format(flags1=flags1, flags2=flags2)


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["cyanrip", "-W"], KEPT),
        (["cyanrip", "--no-deemphasis"], KEPT),
        (["cyanrip"], REMOVED),
        (["cyanrip", "-E"], REMOVED),
        (["cyanrip", "--force-deemphasis"], REMOVED),
        (["cyanrip", "-W", "-E"], REMOVED),
        # A tag value carrying the letters is not the flag.
        (["cyanrip", "-t", "1=title=-W"], REMOVED),
        ([], NOT_DETERMINED),
    ],
)
def test_emphasis_handling_reads_the_argv(argv: list[str], expected: str) -> None:
    assert emphasis_handling(argv) == expected


def test_passes_that_disagree_are_not_determined() -> None:
    assert handling_of_passes([["c", "-W"], ["c", "-W"]]) == KEPT
    assert handling_of_passes([["c", "-W"], ["c"]]) == NOT_DETERMINED
    assert handling_of_passes([]) == NOT_DETERMINED
    assert handling_of_passes([[], ["c", "-E"]]) == REMOVED


def test_the_parser_reads_a_flags_line_into_its_track() -> None:
    sheet = parse_cue(_cue(flags1="    FLAGS PRE DCP\n"))
    assert sheet.tracks[0].flags == frozenset({"PRE", "DCP"})
    assert sheet.tracks[1].flags == frozenset()


def _levels(findings: list[CueFinding]) -> set[str]:
    return {f.level for f in findings}


def test_unknown_handling_is_a_note_never_a_verdict() -> None:
    findings = check_flags_pre(parse_cue(_cue()), {1: True, 2: False}, NOT_DETERMINED)
    assert _levels(findings) == {LEVEL_NOTE}


def test_an_unknown_track_reading_is_named_and_the_rest_still_judged() -> None:
    findings = check_flags_pre(
        parse_cue(_cue(flags1="    FLAGS PRE\n")), {1: True, 2: None}, KEPT
    )
    assert _levels(findings) == {LEVEL_NOTE, LEVEL_OK}
    assert any("not determined for track 2" in f.text for f in findings)
    assert any("agrees on 1 track(s) (1 flagged)" in f.text for f in findings)


def test_missing_and_spurious_flags_each_warn_and_name_the_track() -> None:
    sheet = parse_cue(_cue(flags2="    FLAGS PRE\n"))
    findings = check_flags_pre(sheet, {1: True, 2: False}, KEPT)
    warned = [f for f in findings if f.level == LEVEL_WARN]
    assert {f.code for f in warned} == {"flags_pre_missing", "flags_pre_spurious"}
    assert any("missing on track 1" in f.text for f in warned)
    assert any("present on track 2" in f.text for f in warned)


def test_a_removed_emphasis_wants_no_flag_anywhere() -> None:
    clean = check_flags_pre(parse_cue(_cue()), {1: True, 2: True}, REMOVED)
    assert _levels(clean) == {LEVEL_OK}
    flagged = check_flags_pre(
        parse_cue(_cue(flags1="    FLAGS PRE\n")), {1: True, 2: True}, REMOVED
    )
    assert LEVEL_WARN in _levels(flagged)


def test_a_cue_with_no_numbered_track_says_so() -> None:
    findings = check_flags_pre(parse_cue("REM nothing\n"), {1: True}, KEPT)
    assert [f.code for f in findings] == ["flags_pre_no_tracks"]


@given(
    argv=st.lists(st.text(max_size=12), max_size=8),
    handling=st.sampled_from([KEPT, REMOVED, NOT_DETERMINED, "nonsense"]),
    cue=st.text(max_size=200),
)
def test_never_raises_and_always_says_something(
    argv: list[str], handling: str, cue: str
) -> None:
    assert emphasis_handling(argv) in {KEPT, REMOVED, NOT_DETERMINED}
    assert check_flags_pre(parse_cue(cue), {1: True, 2: None}, handling)
