"""`--reread-time-limit` (the fork's `.28`) on the securing pass (round 39, TASKS R49).

The securing pass reads with `-Z`, so the fork's time limit carries the chase
budget's rule 2 there: each track's re-reads stop starting once they have taken
the larger of 5 x its length and 2 x its album-pass read time. These tests hold
the three things that make the flag safe to send: the build gate (cyanrip refuses
an option it does not know, and a refused rip reads as a missing ripper), the
range the option's own table states (1 to INT32_MAX, every listed build), and the
refusal without `-Z`, which cyanrip refuses too. Then the value the worker
computes, and that a chase read, which has no `-Z`, never carries it.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from platterpus.adapters.cyanrip_backend import CyanripImpl
from platterpus.adapters.reread_time_limit_args import (
    REREAD_TIME_LIMIT_FLAG,
    REREAD_TIME_LIMIT_MAX_SECONDS,
    reread_time_limit_args_for_build,
)
from platterpus.adapters.rip_backend import RipError
from platterpus.deps import fork_source
from platterpus.parsers.rip_log import TrackResult
from platterpus.securing_time_limit import securing_pass_time_limit

_TAG_27 = "platterpus-fork-g5aeefc4"
_TAG_28 = "platterpus-fork-g3f288fb"
_TAG_29 = "platterpus-fork-g8d2ca72"
_TAG_30 = "platterpus-fork-g5cc1c6b"


def _argv(tag: str, **options: object) -> list[str]:
    return CyanripImpl(binary_path="cyanrip")._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="",
        max_retries=5,
        read_offset_override=667,
        ripper_build_tag=tag,
        **options,  # type: ignore[arg-type]  # keyword options of the builder, typed there
    )


# --- the gate --------------------------------------------------------------------


def test_only_28_29_and_30_are_listed_each_on_its_own_contracts_p1() -> None:
    assert fork_source.BUILD_TAGS_ACCEPTING_REREAD_TIME_LIMIT == frozenset(
        {_TAG_28, _TAG_29, _TAG_30}
    )
    root = Path(__file__).resolve().parent.parent / "docs/handshake/inbound/artifacts"
    row = f"| none | `{REREAD_TIME_LIMIT_FLAG}` |"
    for name in (
        "round-37-lap-04-provider-contract-gef413b1.md",  # .28
        "round-38-lap-05-provider-contract-g2a06e064.md",  # .29
        "round-38-lap-12-provider-contract-g0c276fc.md",  # .30
    ):
        assert row in (root / name).read_text(encoding="utf-8"), name
    # `.27`'s contract does not list it, which is why `.27` is not in the set.
    assert row not in (
        root / "round-36-lap-10-provider-contract-g580c46c.md"
    ).read_text(encoding="utf-8")


@pytest.mark.parametrize("tag", [_TAG_28, _TAG_29, _TAG_30, _TAG_30 + "-dirty"])
def test_a_listed_build_is_sent_the_seconds_right_after_the_flag(tag: str) -> None:
    argv = _argv(tag, secure_rerip_matches=2, reread_time_limit_s=1457)
    index = argv.index(REREAD_TIME_LIMIT_FLAG)
    assert argv[index + 1] == "1457"
    assert argv.count(REREAD_TIME_LIMIT_FLAG) == 1


@pytest.mark.parametrize("tag", [_TAG_27, "platterpus-fork-gca0f097", "release", ""])
def test_no_other_build_is_sent_it(tag: str) -> None:
    assert REREAD_TIME_LIMIT_FLAG not in _argv(
        tag, secure_rerip_matches=2, reread_time_limit_s=1457
    )
    assert reread_time_limit_args_for_build(tag, 1457) == []


def test_no_limit_asked_sends_nothing_even_to_a_listed_build() -> None:
    assert REREAD_TIME_LIMIT_FLAG not in _argv(_TAG_30, secure_rerip_matches=2)


# --- the chokepoint's range and the -Z rule ---------------------------------------


@pytest.mark.parametrize("seconds", [1, REREAD_TIME_LIMIT_MAX_SECONDS])
def test_the_ends_of_the_options_range_are_sent(seconds: int) -> None:
    argv = _argv(_TAG_30, secure_rerip_matches=2, reread_time_limit_s=seconds)
    assert argv[argv.index(REREAD_TIME_LIMIT_FLAG) + 1] == str(seconds)


@pytest.mark.parametrize(
    "seconds", [0, -1, REREAD_TIME_LIMIT_MAX_SECONDS + 1, True, 1.5, "600"]
)
def test_a_value_outside_the_range_is_refused_not_dropped(seconds: object) -> None:
    """Refused for every build, listed or not: a caller error is a caller error,
    and a silent drop would read as a limit that was set."""
    for tag in (_TAG_30, ""):
        with pytest.raises(RipError, match="reread_time_limit_s"):
            _argv(tag, secure_rerip_matches=2, reread_time_limit_s=seconds)


def test_the_limit_without_z_is_refused_as_cyanrip_refuses_it() -> None:
    """`cyanrip@5cc1c6b:src/cyanrip_main.c:3414-3417`: exit 64 without -Z."""
    with pytest.raises(RipError, match="without -Z"):
        _argv(_TAG_30, secure_rerip_matches=0, reread_time_limit_s=600)


def test_the_range_is_the_options_own_int32() -> None:
    assert REREAD_TIME_LIMIT_MAX_SECONDS == 2**31 - 1


# --- the value -----------------------------------------------------------------


def _album(number: int, sectors: int | None, read: float | None) -> TrackResult:
    return TrackResult(
        number=number,
        start_sector=None if sectors is None else 1000,
        end_sector=None if sectors is None else 1000 + sectors - 1,
        extraction_elapsed_seconds=read,
    )


def test_one_value_for_the_pass_is_its_largest_track_budget_rounded_up() -> None:
    """Track 3 of the reference disc (21,853 sectors, read in 303.06 s) beside a
    track read slowly (75 s long, read in 900 s): max(1456.87, 1800) -> 1800, and
    track 3 alone -> ceil(1456.87) = 1457. No track is cut below its own budget."""
    albums = {3: _album(3, 21853, 303.06), 5: _album(5, 75 * 75, 900.0)}
    assert securing_pass_time_limit([3, 5], albums) == 1800
    assert securing_pass_time_limit([3], albums) == math.ceil(5 * 21853 / 75)


def test_a_track_without_a_stated_length_means_no_limit_for_the_pass() -> None:
    albums = {3: _album(3, 21853, 303.06), 5: _album(5, None, 900.0)}
    assert securing_pass_time_limit([3, 5], albums) is None
    assert securing_pass_time_limit([], albums) is None
