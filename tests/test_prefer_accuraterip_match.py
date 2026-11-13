"""`--prefer-accuraterip-match` (the fork's `.27`): sent only to a build that lists it.

The fork built the option in `.27` (`6e2ca21`; their round 36 lap 7 S3, which our
round 36 lap 3 S4 accepted): at the `-Z` repeat limit it keeps first a read
AccurateRip matches, at confidence 1 or more, the higher winning
(`cyanrip@709337a:src/cyanrip_main.c:1809-1834`).

**`.27` is released (2026-10-26, `5aeefc4`, their round 36 lap 10 S4)** and P1 of its
filed contract lists the option
(`round-36-lap-10-provider-contract-g580c46c.md:61`), so its tag,
`platterpus-fork-g5aeefc4`, joined the set. **`.28` joined on 2026-11-03** (`3f288fb`,
their round 37 lap 4 S2), P1 of ITS filed contract listing the option
(`round-37-lap-04-provider-contract-gef413b1.md:61`). **`.29` joined on 2026-11-04**
(`8d2ca72`, their round 38 lap 5 S5), P1 of ITS filed contract listing the option
(`round-38-lap-05-provider-contract-g2a06e064.md:61`). **`.30` joined on 2026-11-05**
(`5cc1c6b`, their round 38 lap 12 S4), P1 of ITS filed contract listing the option
(`round-38-lap-12-provider-contract-g0c276fc.md:61`). **`.31` joined on 2026-11-11**
(`e531a33`, their round 39 lap 1 S2), P1 of ITS filed contract listing the option
(`round-39-lap-01-provider-contract-g6eacb8b.md:61`). cyanrip refuses an option it
does not know, and every availability probe reads a refused run as a missing ripper,
so the gate is the whole safety of the flag: these tests hold that `.27`, `.28`,
`.29`, `.30` and `.31` get it on every rip and that no other build does, including `.26`,
`.25` and the fork's unreleased lap-7 build of the same option.
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

#: `.28`'s build tag: `meson.build` line 21 at `3f288fb` declares
#: `0.9.4-rc3+platterpus.28`, and their round 37 lap 4's RIPPER-VERSION names
#: `platterpus-fork-g3f288fb`.
_TAG_28 = "platterpus-fork-g3f288fb"

#: `.29`'s build tag: `meson.build` line 21 at `8d2ca72` declares
#: `0.9.4-rc3+platterpus.29`, and their round 38 lap 5's RIPPER-VERSION names
#: `platterpus-fork-g8d2ca72`.
_TAG_29 = "platterpus-fork-g8d2ca72"

#: `.30`'s build tag: `meson.build` line 21 at `5cc1c6b` declares
#: `0.9.4-rc3+platterpus.30`, and their round 38 lap 12's RIPPER-VERSION names
#: `platterpus-fork-g5cc1c6b`.
_TAG_30 = "platterpus-fork-g5cc1c6b"

#: `.31`'s build tag: `meson.build` line 21 at `e531a33` declares
#: `0.9.4-rc3+platterpus.31`, and their round 39 lap 1's RIPPER-VERSION names
#: `platterpus-fork-ge531a33`.
_TAG_31 = "platterpus-fork-ge531a33"

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


@pytest.fixture(
    params=[_TAG_27, _TAG_28, _TAG_29, _TAG_30, _TAG_31],
    ids=[".27", ".28", ".29", ".30", ".31"],
)
def listed(request: pytest.FixtureRequest) -> str:
    """Each listed tag, asserted to be in the real set, not patched in."""
    tag: str = request.param
    assert tag in fork_source.BUILD_TAGS_ACCEPTING_PREFER_ACCURATERIP_MATCH
    return tag


# --- today: `.27` to `.31` accept it --------------------------------------------------


def test_only_27_to_31_are_listed() -> None:
    assert fork_source.BUILD_TAGS_ACCEPTING_PREFER_ACCURATERIP_MATCH == frozenset(
        {_TAG_27, _TAG_28, _TAG_29, _TAG_30, _TAG_31}
    )
    # Non-triviality: the production pin IS `.31` from round 39's close
    # (2026-11-13), and it is still the build under review until round 40 names
    # the next, so a rig on it sends the flag; `.27`, `.28` and `.30`, the pins
    # before it, and `.29`, under review before `.30`, still run on rigs that
    # installed them and still take the flag.
    assert f"{fork_source.FORK_BRANCH}-g{fork_source.FORK_PIN}" == _TAG_31
    assert f"{fork_source.FORK_BRANCH}-g{fork_source.PIN_UNDER_REVIEW}" == _TAG_31
    assert fork_source.accepts_prefer_accuraterip_match(_TAG_27)
    assert fork_source.accepts_prefer_accuraterip_match(_TAG_28)
    assert fork_source.accepts_prefer_accuraterip_match(_TAG_29)
    assert fork_source.accepts_prefer_accuraterip_match(_TAG_30)


def test_no_other_build_is_sent_it() -> None:
    for tag in (
        # `.25`, named by its commit: until round 36 closed it was FORK_PIN, and
        # `.27`, which takes the flag, is FORK_PIN from 2026-10-28.
        "platterpus-fork-g5f1d036",
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
