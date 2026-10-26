"""`--prefer-accuraterip-match` (the fork's `.27`): sent only to a build that lists it.

The fork built the option in `.27` (`6e2ca21`; their round 36 lap 7 S3, which our
round 36 lap 3 S4 accepted): at the `-Z` repeat limit it keeps first a read
AccurateRip matches, at confidence 1 or more, the higher winning
(`cyanrip@709337a:src/cyanrip_main.c:1809-1834`). Its P1 row is in `.27`'s
regenerated contract (`cyanrip@302dba8:PROVIDER-CONTRACT.md:61`).

`.27` is not released, so no build tag accepts it yet and the capability set is
EMPTY. cyanrip refuses an option it does not know, and every availability probe
reads a refused run as a missing ripper, so the gate is the whole safety of the
flag. These tests hold the gate with a tag patched in, and hold the set empty
until a filed contract lists the option.
"""

from __future__ import annotations

import pytest

from platterpus.adapters.cyanrip_backend import (
    PREFER_ACCURATERIP_MATCH_FLAG,
    CyanripImpl,
    prefer_accuraterip_match_args_for_build,
)
from platterpus.deps import fork_source

#: A tag standing in for `.27`'s, patched into the set: the fork's lap-7 build
#: (`platterpus-fork-g709337a`), which carries the option and is not released.
_TAG_27_BUILD = "platterpus-fork-g709337a"


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
def listed(monkeypatch: pytest.MonkeyPatch) -> str:
    """The set as it will be once `.27` is released: one tag in it."""
    monkeypatch.setattr(
        fork_source,
        "BUILD_TAGS_ACCEPTING_PREFER_ACCURATERIP_MATCH",
        frozenset({_TAG_27_BUILD}),
    )
    return _TAG_27_BUILD


# --- today: no build accepts it ------------------------------------------------------


def test_no_released_build_is_listed_so_no_rip_sends_it() -> None:
    assert fork_source.BUILD_TAGS_ACCEPTING_PREFER_ACCURATERIP_MATCH == frozenset()
    for tag in (
        f"{fork_source.FORK_BRANCH}-g{fork_source.FORK_PIN}",
        f"{fork_source.FORK_BRANCH}-g{fork_source.PIN_UNDER_REVIEW}",
        _TAG_27_BUILD,
        "",
    ):
        assert not fork_source.accepts_prefer_accuraterip_match(tag), tag
        assert PREFER_ACCURATERIP_MATCH_FLAG not in _argv(tag), tag


def test_the_flag_is_spelled_as_27s_p1_spells_it() -> None:
    """`cyanrip@302dba8:PROVIDER-CONTRACT.md:61`: `| none | `--prefer-accuraterip-match` |`."""
    assert PREFER_ACCURATERIP_MATCH_FLAG == "--prefer-accuraterip-match"


def test_a_filed_contract_listing_the_option_forces_the_question() -> None:
    """The tripwire for the set's one obligation: when a filed provider contract's P1
    lists the option, that build is released, and the set must have been asked about
    it. Today the newest filed contract is `.26`'s, which does not list it."""
    from test_argv_surface_agreement import newest_provider_contract

    contract = newest_provider_contract().read_text(encoding="utf-8")
    assert "| none | `--prefer-disc-isrc` |" in contract  # floor: P1 was read
    if f"| none | `{PREFER_ACCURATERIP_MATCH_FLAG}` |" in contract:
        assert fork_source.BUILD_TAGS_ACCEPTING_PREFER_ACCURATERIP_MATCH, (
            "the newest filed provider contract lists --prefer-accuraterip-match in "
            "P1 and no build tag is in BUILD_TAGS_ACCEPTING_PREFER_ACCURATERIP_MATCH; "
            "add the released build's tag (fork_source.py says how)"
        )


# --- once a build is listed ------------------------------------------------------------


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


def test_the_generated_contract_would_publish_it_once_a_build_is_listed(
    listed: str,
) -> None:
    """The input half of the seam is derived from a real call to the builder, so
    a listed build's flag reaches §3 and `tests/test_argv_surface_agreement.py`
    without anyone editing a doc. Shown here with the patched set."""
    argv = _argv(listed, secure_rerip_matches=2)
    assert PREFER_ACCURATERIP_MATCH_FLAG in argv
    assert "-N" in argv  # the metadata-lookup guard still holds beside it
