"""`--prefer-accuraterip-match` (the fork's `.27`): sent only to a build that lists it.

The fork built the option in `.27` (`6e2ca21`; their round 36 lap 7 S3, which our
round 36 lap 3 S4 accepted): at the `-Z` repeat limit it keeps first a read
AccurateRip matches, at confidence 1 or more, the higher winning
(`cyanrip@709337a:src/cyanrip_main.c:1809-1834`).

**`.27` is released (2026-10-26, `5aeefc4`, their round 36 lap 10 S4)** and P1 of its
filed contract lists the option
(`round-36-lap-10-provider-contract-g580c46c.md:61`), so its tag,
`platterpus-fork-g5aeefc4`, is the one tag in the set. cyanrip refuses an option it
does not know, and every availability probe reads a refused run as a missing ripper,
so the gate is the whole safety of the flag: these tests hold that `.27` gets it on
every rip and that no other build does, including `.26`, `.25` and the fork's
unreleased lap-7 build of the same option.
"""

from __future__ import annotations

import pytest

from platterpus.adapters.cyanrip_backend import (
    PREFER_ACCURATERIP_MATCH_FLAG,
    CyanripImpl,
    prefer_accuraterip_match_args_for_build,
)
from platterpus.deps import fork_source

#: `.27`'s build tag: `meson.build` line 21 at `5aeefc4` declares
#: `0.9.4-rc3+platterpus.27`, and their lap 10's RIPPER-VERSION names
#: `platterpus-fork-g5aeefc4`.
_TAG_27 = "platterpus-fork-g5aeefc4"

#: The fork's lap-7 build (`platterpus-fork-g709337a`), which carries the option and
#: was never released. Unlisted: a build joins on its own filed contract, not on
#: having the code.
_TAG_27_UNRELEASED_BUILD = "platterpus-fork-g709337a"


def _argv(tag: str, **options: object) -> list[str]:
    return CyanripImpl(binary_path="cyanrip")._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=667,
        ripper_build_tag=tag,
        **options,  # type: ignore[arg-type]  # keyword options of the builder, typed there
    )


@pytest.fixture
def listed() -> str:
    """`.27`'s tag, asserted to be in the real set, not patched in."""
    assert _TAG_27 in fork_source.BUILD_TAGS_ACCEPTING_PREFER_ACCURATERIP_MATCH
    return _TAG_27


# --- today: `.27` alone accepts it ----------------------------------------------------


def test_only_27_is_listed() -> None:
    assert fork_source.BUILD_TAGS_ACCEPTING_PREFER_ACCURATERIP_MATCH == frozenset(
        {_TAG_27}
    )
    # Non-triviality: the build under review IS `.27`, so a rig on it sends the flag.
    assert f"{fork_source.FORK_BRANCH}-g{fork_source.PIN_UNDER_REVIEW}" == _TAG_27


def test_no_other_build_is_sent_it() -> None:
    for tag in (
        f"{fork_source.FORK_BRANCH}-g{fork_source.FORK_PIN}",  # `.25`
        "platterpus-fork-gca0f097",  # `.26`
        _TAG_27_UNRELEASED_BUILD,
        "release",  # stock cyanrip
        "",
    ):
        assert not fork_source.accepts_prefer_accuraterip_match(tag), tag
        assert PREFER_ACCURATERIP_MATCH_FLAG not in _argv(tag), tag


def test_the_flag_is_spelled_as_27s_p1_spells_it() -> None:
    """`round-36-lap-10-provider-contract-g580c46c.md:61`:
    `| none | `--prefer-accuraterip-match` |`."""
    assert PREFER_ACCURATERIP_MATCH_FLAG == "--prefer-accuraterip-match"


def test_a_filed_contract_listing_the_option_forces_the_question() -> None:
    """The tripwire for the set's one obligation: when a filed provider contract's P1
    lists the option, that build is released, and the set must have been asked about
    it. The newest filed contract is `.27`'s, which lists it, so the branch below is
    taken (asserted, so the tripwire cannot pass by finding nothing)."""
    from test_argv_surface_agreement import newest_provider_contract

    contract = newest_provider_contract().read_text(encoding="utf-8")
    assert "| none | `--prefer-disc-isrc` |" in contract  # floor: P1 was read
    assert f"| none | `{PREFER_ACCURATERIP_MATCH_FLAG}` |" in contract
    assert fork_source.BUILD_TAGS_ACCEPTING_PREFER_ACCURATERIP_MATCH, (
        "the newest filed provider contract lists --prefer-accuraterip-match in "
        "P1 and no build tag is in BUILD_TAGS_ACCEPTING_PREFER_ACCURATERIP_MATCH; "
        "add the released build's tag (fork_source.py says how)"
    )


# --- the listed build ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("suffix", "other", "sent"),
    [("", "", True), ("-dirty", "", True), ("", "platterpus-fork-gca0f097", False)],
)
def test_the_option_goes_only_to_a_listed_tag(
    listed: str, suffix: str, other: str, sent: bool
) -> None:
    tag = other or f"{listed}{suffix}"
    assert fork_source.accepts_prefer_accuraterip_match(tag) is sent
    assert prefer_accuraterip_match_args_for_build(tag) == (
        [PREFER_ACCURATERIP_MATCH_FLAG] if sent else []
    )


@pytest.mark.parametrize(
    "options",
    [{}, {"secure_rerip_matches": 2}, {"prefer_disc_isrc": True}],
    ids=["plain", "with -Z", "with --prefer-disc-isrc"],
)
def test_every_rip_to_a_listed_build_sends_it_once(
    listed: str, options: dict[str, object]
) -> None:
    """No setting: it acts only at the `-Z` limit, so it goes on every rip."""
    argv = _argv(listed, **options)
    assert argv.count(PREFER_ACCURATERIP_MATCH_FLAG) == 1
    assert PREFER_ACCURATERIP_MATCH_FLAG not in _argv("", **options)


def test_the_generated_contract_publishes_it_for_the_listed_build(
    listed: str,
) -> None:
    """The input half of the seam is derived from a real call to the builder, so
    the listed build's flag reaches §3 and `tests/test_argv_surface_agreement.py`
    without anyone editing a doc."""
    argv = _argv(listed, secure_rerip_matches=2)
    assert PREFER_ACCURATERIP_MATCH_FLAG in argv
    assert "-N" in argv  # the metadata-lookup guard still holds beside it
