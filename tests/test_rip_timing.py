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
