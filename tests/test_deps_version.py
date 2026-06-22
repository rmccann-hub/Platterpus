"""Tests for whipper_gui.deps.version."""

from __future__ import annotations

import pytest

from whipper_gui.deps.version import format_version, meets_minimum, parse_version

# --- parse_version ---


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("whipper 0.10.0", (0, 10, 0)),
        ("flac version 1.4", (1, 4)),
        ("Version: 2.11.5", (2, 11, 5)),
        ("header\nv 0.7.1 of musicbrainzngs\n", (0, 7, 1)),
        ("no version here", None),
        # The "0.10.0" trap — naive `\d` patterns parse as (0, 1, 0).
        ("whipper 0.10.0", (0, 10, 0)),
    ],
    ids=[
        "basic_semver",
        "two_component_no_patch",
        "label_prefix",
        "multiline_first_match_wins",
        "no_match_returns_none",
        "double_digit_components",
    ],
)
def test_parse_version(text: str, expected: tuple[int, ...] | None) -> None:
    assert parse_version(text) == expected


# --- meets_minimum ---


@pytest.mark.parametrize(
    ("version", "minimum", "expected"),
    [
        ((0, 10, 0), (0, 10, 0), True),  # equal
        ((1, 0, 0), (0, 10, 0), True),  # higher
        ((0, 9, 99), (0, 10, 0), False),  # lower
        ((1, 2), (1, 2, 0), True),  # short version padded → (1, 2, 0)
        ((1, 2, 0), (1, 2), True),  # short minimum padded
        (None, (0, 1, 0), False),  # missing version never satisfies
    ],
    ids=[
        "equal_versions",
        "higher_version",
        "lower_version",
        "pads_short_version",
        "pads_short_minimum",
        "none_version",
    ],
)
def test_meets_minimum(
    version: tuple[int, ...] | None, minimum: tuple[int, ...], expected: bool
) -> None:
    assert meets_minimum(version, minimum) is expected


# --- format_version ---


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ((0, 10, 0), "0.10.0"),
        ((1, 4), "1.4"),
        (None, "unknown"),
        ((), "unknown"),
    ],
    ids=["basic", "two_components", "none_is_unknown", "empty_tuple_is_unknown"],
)
def test_format_version(version: tuple[int, ...] | None, expected: str) -> None:
    assert format_version(version) == expected
