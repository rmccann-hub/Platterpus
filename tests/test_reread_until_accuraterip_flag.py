"""`--reread-until-accuraterip 2` (the fork's `.31`) on every `-Z` pass (round 39, G1).

A `-Z` pass ends a track when its reads agree, so it is where an agreement on the
wrong audio is the question; `.31`'s option lets the ripper refuse such an
agreement (their round 39 lap 1 S4). These tests hold
what makes it safe to send: the build gate (cyanrip refuses an option it does not
know, and a refused rip reads as a missing ripper), the range the option's own
table states (1 to INT32_MAX, ``cyanrip@e531a33:src/cyanrip_main.c:3345``), and
the refusal without `-Z`, which cyanrip refuses too (exit 64,
``cyanrip@e531a33:src/cyanrip_main.c:3553-3556``). Which passes the worker asks
on, every `-Z` pass and no other, is ``tests/test_reread_until_accuraterip_passes.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from platterpus.adapters.cyanrip_backend import CyanripImpl
from platterpus.adapters.reread_until_accuraterip_args import (
    REREAD_ACCURATERIP_CONFIDENCE,
    REREAD_UNTIL_ACCURATERIP_FLAG,
    REREAD_UNTIL_ACCURATERIP_MAX,
    reread_until_accuraterip_args,
)
from platterpus.adapters.rip_backend import RipError
from platterpus.deps import fork_source

_TAG_30 = "platterpus-fork-g5cc1c6b"
_TAG_31 = "platterpus-fork-ge531a33"
_ARTIFACTS = Path(__file__).resolve().parent.parent / "docs/handshake/inbound/artifacts"


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


def test_only_31_is_listed_on_its_own_contracts_p1() -> None:
    assert fork_source.BUILD_TAGS_ACCEPTING_REREAD_UNTIL_ACCURATERIP == frozenset(
        {_TAG_31}
    )
    row = f"| none | `{REREAD_UNTIL_ACCURATERIP_FLAG}` |"
    assert row in (
        _ARTIFACTS / "round-39-lap-01-provider-contract-g6eacb8b.md"
    ).read_text(encoding="utf-8")
    # `.30`'s contract does not list it, which is why `.30`, FORK_PIN, is not in
    # the set: the option would refuse every rip on the default ripper.
    assert row not in (
        _ARTIFACTS / "round-38-lap-12-provider-contract-g0c276fc.md"
    ).read_text(encoding="utf-8")
    assert f"{fork_source.FORK_BRANCH}-g{fork_source.PIN_UNDER_REVIEW}" == _TAG_31


@pytest.mark.parametrize(
    "tag", [_TAG_31, _TAG_31 + "-dirty", "PLATTERPUS-FORK-GE531A33"]
)
def test_the_listed_build_is_sent_the_confidence_right_after_the_flag(tag: str) -> None:
    argv = _argv(tag, secure_rerip_matches=2, reread_until_accuraterip=2)
    index = argv.index(REREAD_UNTIL_ACCURATERIP_FLAG)
    assert argv[index + 1] == "2"
    assert argv.count(REREAD_UNTIL_ACCURATERIP_FLAG) == 1
    assert "-N" in argv  # the metadata-lookup guard still holds beside it


@pytest.mark.parametrize(
    "tag",
    [_TAG_30, "platterpus-fork-g3f288fb", "release", "", "platterpus-fork-g0000000"],
)
def test_no_other_build_is_sent_it(tag: str) -> None:
    assert REREAD_UNTIL_ACCURATERIP_FLAG not in _argv(
        tag, secure_rerip_matches=2, reread_until_accuraterip=2
    )
    assert reread_until_accuraterip_args(tag, 2, 2) == []


def test_nothing_asked_sends_nothing_even_to_the_listed_build() -> None:
    assert REREAD_UNTIL_ACCURATERIP_FLAG not in _argv(_TAG_31, secure_rerip_matches=2)


# --- the chokepoint's range and the -Z rule ---------------------------------------


@pytest.mark.parametrize("confidence", [1, REREAD_UNTIL_ACCURATERIP_MAX])
def test_the_ends_of_the_options_range_are_sent(confidence: int) -> None:
    argv = _argv(_TAG_31, secure_rerip_matches=2, reread_until_accuraterip=confidence)
    assert argv[argv.index(REREAD_UNTIL_ACCURATERIP_FLAG) + 1] == str(confidence)


@pytest.mark.parametrize(
    "confidence", [0, -1, REREAD_UNTIL_ACCURATERIP_MAX + 1, True, 1.5, "2"]
)
def test_a_value_outside_the_range_is_refused_not_dropped(confidence: object) -> None:
    """Refused for every build, listed or not: a silent drop would read, in our
    own record, as a rule that was asked for."""
    for tag in (_TAG_31, _TAG_30, ""):
        with pytest.raises(RipError, match="reread_until_accuraterip"):
            _argv(tag, secure_rerip_matches=2, reread_until_accuraterip=confidence)


def test_the_option_without_z_is_refused_as_cyanrip_refuses_it() -> None:
    """`cyanrip@e531a33:src/cyanrip_main.c:3553-3556`: exit 64 without -Z."""
    for tag in (_TAG_31, ""):
        with pytest.raises(RipError, match="without -Z"):
            _argv(tag, secure_rerip_matches=0, reread_until_accuraterip=2)


def test_the_range_is_the_options_own_int32_and_we_send_2() -> None:
    assert REREAD_UNTIL_ACCURATERIP_MAX == 2**31 - 1
    # Our round 38 lap 17 S8 told the fork "sent as --reread-until-accuraterip 2".
    assert REREAD_ACCURATERIP_CONFIDENCE == 2


def test_it_rides_beside_the_time_limit_on_the_securing_pass() -> None:
    """The two compose (their round 38 lap 16 S13): the time limit is what still
    ends a track AccurateRip holds and no read matches."""
    argv = _argv(
        _TAG_31,
        secure_rerip_matches=2,
        reread_time_limit_s=1457,
        reread_until_accuraterip=2,
    )
    assert "--reread-time-limit" in argv and REREAD_UNTIL_ACCURATERIP_FLAG in argv


def test_the_real_rip_spawns_the_option_it_was_asked_for(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`CyanripImpl.rip` hands the value through to the argv, read off the spawned
    child's own argv (`Popen.args`, which the handle exposes), not off the builder."""
    binary = tmp_path / "cyanrip"
    binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    binary.chmod(0o755)
    impl = CyanripImpl(binary_path=str(binary))
    monkeypatch.setattr(
        impl,
        "version",
        lambda: "cyanrip 0.9.4-rc3+platterpus.31 (platterpus-fork-ge531a33)",
    )
    handle = impl.rip(
        drive="/dev/sr0",
        release_id="",
        output_dir=tmp_path / "out",
        track_template="%t - %n",
        disc_template="",
        secure_rerip_matches=2,
        only_tracks=(3,),
        reread_until_accuraterip=REREAD_ACCURATERIP_CONFIDENCE,
    )
    list(handle.log_lines())
    handle.wait(timeout=10)
    argv = list(handle.argv)
    assert argv[argv.index(REREAD_UNTIL_ACCURATERIP_FLAG) + 1] == "2"
