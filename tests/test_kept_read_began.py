"""`.27`'s `Kept read began:` line, read into the parse and the report (schema 40).

The fork's round 36 lap 7 S5 says the line is built (`5062bd5`): one per audio
track, directly below `Elapsed:`, the UTC instant the read the track's files carry
began, in ISO 8601 (`cyanrip@709337a:src/cyanrip_log.c:670-679`, formatted by
`crip_iso8601_utc`, `cyanrip@709337a:src/utils.h:278-284`). A data track prints
none, and neither does a track whose time could not be converted.

**Where the lines come from.** `cyanrip_fork_golden_reference_r36l7.log` is
`cyanrip@ed540ff:docs/golden-reference.log` byte for byte (sha256
`bc9b98c4…75e3`), the reference the fork regenerated for lap 7 from their build
`platterpus-fork-g9c27d31`, which carries the line on each of its three tracks.
`cyanrip_fork_golden_reference_r36.log` is `.26`'s, which carries none.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus import kept_read
from platterpus.parsers import cyanrip_log
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.rip_report import build_report

_FIXTURES = Path(__file__).parent / "fixtures"
_R36L7_LOG = _FIXTURES / "cyanrip_fork_golden_reference_r36l7.log"
_R36_LOG = _FIXTURES / "cyanrip_fork_golden_reference_r36.log"
_R36L7_SHA256 = "bc9b98c426e9a7bc688a357fdabe5dc062d45347a824848bbc958909c50c75e3"

#: The P2 row of the fork's regenerated contract
#: (`cyanrip@302dba8:PROVIDER-CONTRACT.md:331`), copied rather than built from our
#: pattern, so a test that fills it in checks our reader against their text. The
#: four-space indent is the source's (`cyanrip_log.c:679`); P2 records the format
#: string without it.
_P2_KEPT = "    Kept read began:    %s"

_INSTANT = "2026-10-21T09:41:04Z"


def _golden() -> str:
    text = _R36L7_LOG.read_text(encoding="utf-8")
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == _R36L7_SHA256
    return text


def _with_value(value: str) -> str:
    """The `.27` reference with track 1's value replaced by ``value``."""
    text = _golden()
    line = _P2_KEPT % _INSTANT
    assert text.count(line + "\n") == 3  # floor: the anchor is there, three times
    return text.replace(line + "\n", (_P2_KEPT % value) + "\n", 1)


# --- the reference as published --------------------------------------------------


def test_the_line_sits_directly_below_elapsed_on_every_audio_track() -> None:
    """Where the fork puts it (their lap 7 S5), read off their artifact."""
    lines = _golden().splitlines()
    kept = [
        i for i, line in enumerate(lines) if line.startswith("    Kept read began:")
    ]
    assert len(kept) == 3  # floor: one per audio track of the three-track disc
    for index in kept:
        assert lines[index - 1].startswith("    Elapsed:"), lines[index - 1]


def test_the_reference_parses_to_one_instant_per_track() -> None:
    log = parse_cyanrip_log(_golden())

    assert len(log.tracks) == 3  # floor: the whole log was read
    assert [t.kept_read_began for t in log.tracks] == [_INSTANT] * 3
    assert {t.kept_read_began_state for t in log.tracks} == {kept_read.READ}


def test_the_line_is_claimed_by_a_listed_pattern_and_nothing_else() -> None:
    """The enumeration the generated consumer contract publishes lists it."""
    patterns = dict(cyanrip_log._INDENTED_LINE_PATTERNS)
    line = _P2_KEPT % _INSTANT
    assert patterns["track_kept_read_began"].match(line)
    others = [
        name
        for name, pattern in cyanrip_log._INDENTED_LINE_PATTERNS
        if name not in {"track_kept_read_began", "gaps_value"} and pattern.match(line)
    ]
    assert others == []


def test_a_build_without_the_line_reads_not_present_never_a_negative() -> None:
    log = parse_cyanrip_log(_R36_LOG.read_text(encoding="utf-8"))
    assert len(log.tracks) == 3
    assert [(t.kept_read_began, t.kept_read_began_state) for t in log.tracks] == [
        ("", "")
    ] * 3
    rows = build_report(log)["tracks"]
    assert [(r["kept_read_began"], r["kept_read_began_state"]) for r in rows] == [
        (None, kept_read.NOT_PRESENT)
    ] * 3


def test_the_report_carries_the_instant_per_track() -> None:
    rows = build_report(parse_cyanrip_log(_golden()))["tracks"]
    assert len(rows) == 3
    assert [(r["kept_read_began"], r["kept_read_began_state"]) for r in rows] == [
        (_INSTANT, kept_read.READ)
    ] * 3


# --- values we cannot read ----------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "2026-13-45T25:61:00Z",  # the shape of an instant, not an instant
        "2026-10-21T09:23:27+00:00",  # an offset: not the form the log prints
        "2026-10-21 09:23:27Z",
        "yesterday",
        "9" * 4400,
    ],
    ids=["impossible-date", "offset", "space", "words", "long-number"],
)
def test_a_value_that_is_not_an_instant_is_unrecognised_not_a_time(value: str) -> None:
    log = parse_cyanrip_log(_with_value(value))
    track = log.tracks[0]
    assert (track.kept_read_began, track.kept_read_began_state) == (
        "",
        kept_read.UNRECOGNISED,
    )
    # The other two tracks still read: one bad line spoils nothing else.
    assert [t.kept_read_began for t in log.tracks[1:]] == [_INSTANT] * 2
    row = build_report(log)["tracks"][0]
    assert (row["kept_read_began"], row["kept_read_began_state"]) == (
        None,
        kept_read.UNRECOGNISED,
    )


def test_the_record_form_takes_an_offset_and_converts_it_to_utc() -> None:
    """The record's reader shares this function, and its instants carry offsets."""
    assert (
        kept_read.began_instant("2026-10-21T05:23:27-04:00", offset_allowed=True)
        == "2026-10-21T09:23:27Z"
    )
    assert kept_read.began_instant("2026-10-21T05:23:27-04:00") is None
    assert kept_read.began_instant(_INSTANT, offset_allowed=True) == _INSTANT


@given(st.text(max_size=200))
def test_the_line_never_raises(value: str) -> None:
    parse_cyanrip_log(_with_value(value.replace("\n", " ").replace("\r", " ")))


@given(st.one_of(st.text(max_size=80), st.integers(), st.none(), st.floats()))
def test_the_instant_reader_never_raises_and_only_returns_an_instant(
    value: object,
) -> None:
    for offset_allowed in (False, True):
        state, instant = kept_read.instant_state(value, offset_allowed=offset_allowed)
        assert state in kept_read.STATES
        if state == kept_read.READ:
            assert kept_read.LOG_INSTANT.fullmatch(instant), instant
        else:
            assert instant == ""
