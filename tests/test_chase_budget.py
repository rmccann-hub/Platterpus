"""Tests for how far the verified-read chase may go (`chase_budget.py`, round 39 G1).

Rule 1 (the attempt limit), rule 2 (the time budget, TASKS R49) and rule 3 (the
drive cache between chase reads), each at its boundary, and all three read off
the committed reference log of the disc G1 is about (track 3 of *Every Breath You
Take: The Classics*), so the arithmetic is checked against the artifact rather
than against numbers copied into the test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from platterpus.chase_budget import (
    CACHE_DEFEAT_NOT_ASSURED,
    CACHE_DEFEAT_NOT_DETERMINED,
    CACHE_DEFEATED_BY_WHOLE_TRACK_READ,
    CACHE_SELF_DEFEATING_SECTORS,
    CHASE_ATTEMPTS_CEILING,
    CHASE_HIGH_CONFIDENCE_ATTEMPTS_CEILING,
    CHASE_HIGH_CONFIDENCE_MIN,
    LIMIT_FROM_HIGH_CONFIDENCE,
    LIMIT_FROM_REPEAT_LIMIT,
    attempt_limit,
    cache_defeat,
    plan_budget,
    time_budget_seconds,
    top_confidence,
    track_sectors,
)
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import TrackResult

#: The reference disc's fork log, committed (text only, rule 8).
_REFERENCE_LOG = (
    Path(__file__).resolve().parent.parent
    / "output_reference"
    / "cyanrip_fork_flac"
    / "cyanrip_fork_police_classics.log"
)


def _reference_track(number: int) -> TrackResult:
    tracks = parse_cyanrip_log(_REFERENCE_LOG.read_text(encoding="utf-8")).tracks
    return {t.number: t for t in tracks}[number]


# --- Rule 1: the attempt limit -----------------------------------------------


def test_the_numbers_are_the_ones_the_module_justifies() -> None:
    """Pinned so a change to any of them is a decision the docstring must follow."""
    assert CHASE_ATTEMPTS_CEILING == 5
    assert CHASE_HIGH_CONFIDENCE_MIN == 10
    assert CHASE_HIGH_CONFIDENCE_ATTEMPTS_CEILING == 16


def test_sixteen_is_the_smallest_limit_giving_g1_at_99_percent_at_one_in_three() -> (
    None
):
    """The docstring's arithmetic, recomputed: (1 - (2/3)^N)^5 >= 0.99 first at 16."""

    def g1(n: int) -> float:
        return float((1 - (2 / 3) ** n) ** 5)

    assert g1(CHASE_HIGH_CONFIDENCE_ATTEMPTS_CEILING) >= 0.99
    assert g1(CHASE_HIGH_CONFIDENCE_ATTEMPTS_CEILING - 1) < 0.99
    assert g1(CHASE_ATTEMPTS_CEILING) < 0.5, "the old limit failed G1 one time in two"


@pytest.mark.parametrize(
    ("confidence", "budget_known", "expected"),
    [
        (200, True, (16, LIMIT_FROM_HIGH_CONFIDENCE)),
        (10, True, (16, LIMIT_FROM_HIGH_CONFIDENCE)),
        (9, True, (5, LIMIT_FROM_REPEAT_LIMIT)),
        (None, True, (5, LIMIT_FROM_REPEAT_LIMIT)),
        # No time budget, no high limit: 16 reads of a damaged track are days.
        (200, False, (5, LIMIT_FROM_REPEAT_LIMIT)),
    ],
)
def test_the_high_limit_needs_a_high_confidence_entry_and_a_time_budget(
    confidence: int | None, budget_known: bool, expected: tuple[int, str]
) -> None:
    assert attempt_limit(5, confidence, budget_known=budget_known) == expected


@pytest.mark.parametrize(("max_retries", "limit"), [(1, 1), (3, 3), (20, 5), (0, 1)])
def test_the_ordinary_limit_is_still_the_users_r_capped(
    max_retries: int, limit: int
) -> None:
    assert attempt_limit(max_retries, None, budget_known=True) == (
        limit,
        LIMIT_FROM_REPEAT_LIMIT,
    )


def test_the_top_entry_is_read_from_the_accurip_row_by_the_one_reader() -> None:
    stated = TrackResult(
        number=3, accuraterip_lookup="disc found in database (max confidence: 24)"
    )
    unstated = TrackResult(number=3, accuraterip_lookup="disc not found in database")
    assert top_confidence(unstated, stated) == 24
    assert top_confidence(None, unstated) is None


# --- Rule 2: the time budget -------------------------------------------------


def test_the_budget_is_five_times_the_length_when_the_read_was_quick() -> None:
    assert time_budget_seconds(300.0, 60.0) == 1500.0


def test_the_budget_is_twice_the_read_time_when_the_read_was_slow() -> None:
    """Disc 1's track 18, 2026-10-21 (TASKS R49): read once in 8,548 s."""
    assert time_budget_seconds(300.0, 8548.0) == 17096.0


def test_without_a_length_there_is_no_budget_even_with_a_read_time() -> None:
    """The length is the floor; a read time alone never makes a budget."""
    assert time_budget_seconds(None, 303.06) is None
    assert time_budget_seconds(0.0, 303.06) is None


def test_track_3_of_the_reference_disc_gets_the_high_limit_and_its_budget() -> None:
    """Read off the committed log: LSN 28067 to 49919 (21,853 sectors, 291.37 s),
    Elapsed 303.06 s, top entry 200. So 16 reads, within max(5 x 291.37,
    2 x 303.06) = 1456.87 s, and each read flushes the cache itself."""
    track = _reference_track(3)
    assert track_sectors(track) == 21853, "floor: the fixture still states its LSNs"
    budget = plan_budget(kept=track, album_pass=track, max_retries=5)
    assert budget.attempt_limit == CHASE_HIGH_CONFIDENCE_ATTEMPTS_CEILING
    assert budget.limit_reason == LIMIT_FROM_HIGH_CONFIDENCE
    assert budget.accuraterip_top_confidence == 200
    assert budget.album_read_seconds == pytest.approx(303.06)
    assert budget.time_budget_seconds == pytest.approx(5 * 21853 / 75)
    assert budget.cache_defeat == CACHE_DEFEATED_BY_WHOLE_TRACK_READ


def test_a_stock_log_without_lsns_keeps_the_old_behaviour() -> None:
    """Stock cyanrip states no LSN or Elapsed: the chase is as before round 39."""
    track = TrackResult(
        number=5, accuraterip_lookup="disc found in database (max confidence: 200)"
    )
    budget = plan_budget(kept=track, album_pass=None, max_retries=5)
    assert (budget.attempt_limit, budget.limit_reason) == (5, LIMIT_FROM_REPEAT_LIMIT)
    assert budget.time_budget_seconds is None
    assert budget.cache_defeat == CACHE_DEFEAT_NOT_DETERMINED


# --- Rule 3: the drive cache between chase reads -----------------------------


@pytest.mark.parametrize(
    ("sectors", "expected"),
    [
        (CACHE_SELF_DEFEATING_SECTORS, CACHE_DEFEATED_BY_WHOLE_TRACK_READ),
        (CACHE_SELF_DEFEATING_SECTORS - 1, CACHE_DEFEAT_NOT_ASSURED),
        (None, CACHE_DEFEAT_NOT_DETERMINED),
    ],
)
def test_a_track_flushes_the_cache_itself_from_567_sectors(
    sectors: int | None, expected: str
) -> None:
    """255 (the cache's ceiling) + 312 (the fork's flush) = 567 sectors."""
    assert CACHE_SELF_DEFEATING_SECTORS == 567
    assert cache_defeat(sectors) == expected


def test_a_backwards_or_partial_lsn_pair_is_not_a_length() -> None:
    assert track_sectors(TrackResult(number=1, start_sector=10, end_sector=5)) is None
    assert track_sectors(TrackResult(number=1, start_sector=10)) is None
