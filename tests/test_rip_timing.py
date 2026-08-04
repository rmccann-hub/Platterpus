"""Tests for platterpus.rip_timing (ETA parsing + duration formatting).

Both helpers feed the post-rip log line and the JSON report, so — like the
parsers — they must never raise on arbitrary input. A property test pins that
contract; the unit tests pin the formats cyanrip actually emits.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from platterpus.rip_timing import (
    format_duration,
    parse_eta_to_seconds,
    parse_hms_to_seconds,
)


class TestParseEtaToSeconds:
    def test_minutes_only(self) -> None:
        assert parse_eta_to_seconds("3m") == 180

    def test_hours_and_minutes(self) -> None:
        assert parse_eta_to_seconds("1h2m") == 3720

    def test_seconds_only(self) -> None:
        assert parse_eta_to_seconds("45s") == 45

    def test_hours_only(self) -> None:
        assert parse_eta_to_seconds("1h") == 3600

    def test_full_h_m_s(self) -> None:
        assert parse_eta_to_seconds("2h3m4s") == 7384

    def test_bare_integer_is_seconds(self) -> None:
        assert parse_eta_to_seconds("90") == 90

    def test_whitespace_between_pieces(self) -> None:
        assert parse_eta_to_seconds("1h 0m 5s") == 3605

    def test_empty_and_none_are_none(self) -> None:
        assert parse_eta_to_seconds("") is None
        assert parse_eta_to_seconds(None) is None

    def test_unparseable_is_none(self) -> None:
        assert parse_eta_to_seconds("soon") is None


class TestFormatDuration:
    def test_hours_minutes_seconds(self) -> None:
        # The real-disc case: 2h44m56s (9896s) — the number that exposed
        # cyanrip's "~35m" ETA as useless.
        assert format_duration(9896) == "2h 44m 56s"

    def test_minutes_and_seconds(self) -> None:
        assert format_duration(65) == "1m 5s"

    def test_seconds_only_drops_leading_units(self) -> None:
        assert format_duration(0) == "0s"
        assert format_duration(9) == "9s"

    def test_minutes_shown_once_past_an_hour(self) -> None:
        assert format_duration(3600) == "1h 0m 0s"

    def test_rounds_fractional_seconds(self) -> None:
        assert format_duration(64.6) == "1m 5s"

    def test_none_and_negative_are_unknown(self) -> None:
        assert format_duration(None) == "unknown"
        assert format_duration(-5) == "unknown"


class TestParseHmsToSeconds:
    def test_cyanrip_total_time(self) -> None:
        # cyanrip's "Total time: 00:59:42.354" → 3582.354s.
        assert parse_hms_to_seconds("00:59:42.354") == 3582.354

    def test_whole_seconds(self) -> None:
        assert parse_hms_to_seconds("01:00:00") == 3600

    def test_empty_and_garbage_are_none(self) -> None:
        assert parse_hms_to_seconds("") is None
        assert parse_hms_to_seconds(None) is None
        assert parse_hms_to_seconds("not a time") is None
        assert parse_hms_to_seconds("3m") is None  # ETA format, not HH:MM:SS


@given(st.text())
def test_parse_hms_never_raises(text: str) -> None:
    parse_hms_to_seconds(text)


@given(st.text())
def test_parse_eta_never_raises(text: str) -> None:
    # Contract: a best-effort parser of external output never raises.
    parse_eta_to_seconds(text)


@given(st.one_of(st.none(), st.floats(), st.integers()))
def test_format_duration_never_raises(value: object) -> None:
    result = format_duration(value)  # type: ignore[arg-type]
    assert isinstance(result, str)


# --- MM:SS.FF is CD FRAMES, not hundredths ------------------------------------
#
# Verified from the fork's source at the pinned commit (`src/utils.h`:
# `snprintf("%02i:%02i.%02i", min, sec, remain)` with `remain = frames % 75`) and
# stated in their published contract's units block. Reading the fraction as
# hundredths is wrong by up to 0.98 s, and it was wrong on every per-track
# `Duration:` row of every disc, silently, because the old pattern demanded
# HH:MM:SS and returned None for this shape instead.

import pytest  # noqa: E402

from platterpus.rip_timing import (  # noqa: E402
    CD_FRAMES_PER_SECOND,
    parse_cd_duration_to_seconds,
)


def test_the_real_discs_total_time_converts_by_frames_not_hundredths() -> None:
    """`Total time:     59:42.57` off a real 14-track rip.

    57 frames is 0.76 s, not 0.57 s. Asserting the *difference* as well as the
    value, because a test that only pinned the right answer would still pass if
    someone reintroduced a /100 divisor and adjusted the expectation to match.
    """
    frames_reading = parse_cd_duration_to_seconds("59:42.57")
    assert frames_reading is not None
    assert frames_reading == pytest.approx(59 * 60 + 42 + 57 / 75)

    hundredths_reading = 59 * 60 + 42 + 0.57
    assert frames_reading != pytest.approx(hundredths_reading)
    assert frames_reading - hundredths_reading == pytest.approx(0.19, abs=0.01)


def test_the_two_shapes_are_discriminated_on_colon_count() -> None:
    """Their contract tells a consumer to key on colon count, and that is the only
    thing that can work: `.34` is a legal value in both shapes, so the fraction's
    magnitude carries no information about which one you are looking at."""
    # Three fields -> the fraction is MILLISECONDS.
    assert parse_cd_duration_to_seconds("00:59:42.354") == pytest.approx(
        59 * 60 + 42.354
    )
    # Two fields -> the fraction is FRAMES. Same digits, different value.
    assert parse_cd_duration_to_seconds("59:42.35") == pytest.approx(
        59 * 60 + 42 + 35 / 75
    )


def test_minutes_are_not_modulo_60() -> None:
    """There is no hours field in the MM:SS.FF shape, so a 90-minute disc prints
    `90:12.34`. A pattern allowing only two digits of minutes would drop it."""
    assert parse_cd_duration_to_seconds("90:12.34") == pytest.approx(
        90 * 60 + 12 + 34 / 75
    )


def test_a_frame_field_out_of_range_is_refused_not_reinterpreted() -> None:
    """74 is the last legal frame. A `.75` or higher is not a frame field, and
    guessing that it must be hundredths would let a duration quietly gain up to a
    second. Refusing says "this does not match either documented shape"."""
    assert parse_cd_duration_to_seconds("00:00.74") == pytest.approx(74 / 75)
    assert parse_cd_duration_to_seconds("00:00.75") is None
    assert parse_cd_duration_to_seconds("00:00.99") is None
    assert CD_FRAMES_PER_SECOND == 75


def test_the_committed_fork_reference_durations_all_parse() -> None:
    """Read the artifact, not a hand-written sample (docs/testing.md §5.u).

    Every `Duration:` and `Total time:` row in the committed golden reference must
    convert. A floor on the count keeps this from passing by finding none.
    """
    import re
    from pathlib import Path

    golden = (
        Path(__file__).parent / "fixtures" / "cyanrip_fork_golden_reference_r6b.log"
    )
    rows = re.findall(
        r"^\s*(?:Total time|Duration):\s+(\S+)\s*$",
        golden.read_text(encoding="utf-8"),
        re.M,
    )
    assert len(rows) >= 4, f"only found {len(rows)} duration rows: {rows}"
    unparsed = [r for r in rows if parse_cd_duration_to_seconds(r) is None]
    assert not unparsed, f"duration rows the converter cannot read: {unparsed}"
