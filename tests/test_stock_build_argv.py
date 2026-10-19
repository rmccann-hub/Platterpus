"""A stock cyanrip is sent no option it would refuse (TASKS R30).

Stock cyanrip 0.9.3 parses its options with ``getopt``, has no long options, and
exits 1 on one it does not know (``cyanrip@063d848:src/cyanrip_main.c:1797-1798``).
The setup wizard installs that build from the COPR before it builds the fork, so
an install where the fork's build failed is left on it. Until 2026-10-19 our argv
builder sent ``--diagnostics`` to every build, ``--consumer`` and
``--prefer-disc-isrc`` being the only two it gated, so on that install every rip
was refused before it read a sector.

The stock banner here is read from a real stock rip's log in ``output_reference/``,
not typed, so the test holds the build tag stock cyanrip actually prints.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from platterpus.adapters.cyanrip_backend import (
    DIAGNOSTICS_FLAG,
    PREFER_DISC_ISRC_FLAG,
    CyanripImpl,
    diagnostics_args_for_build,
)
from platterpus.deps import fork_source
from platterpus.ripper_identity import identify_from_banner
from platterpus.uiscript.script import DIAGNOSTICS_PLACEHOLDER, expand_identity

REPO_ROOT: Path = Path(__file__).resolve().parents[1]

#: A real stock cyanrip 0.9.3 rip of the reference disc, captured 2026-06-27.
STOCK_LOG: Path = (
    REPO_ROOT / "output_reference/cyanrip_flac/cyanrip_flac_police_classics.log"
)

#: Every long option our argv builder can send that stock cyanrip lacks.
LONG_OPTIONS: tuple[str, ...] = ("--consumer", PREFER_DISC_ISRC_FLAG, DIAGNOSTICS_FLAG)


def _stock_build_tag() -> str:
    banner = next(
        line
        for line in STOCK_LOG.read_text(encoding="utf-8").splitlines()
        if line.startswith("cyanrip ")
    )
    identity = identify_from_banner(banner)
    # Non-triviality: the artifact really is a stock banner and we read its tag.
    assert identity.kind == "stock", banner
    assert identity.build_tag, banner
    return identity.build_tag


def _rip_argv(build_tag: str) -> list[str]:
    return CyanripImpl(binary_path="cyanrip")._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=667,
        prefer_disc_isrc=True,
        ripper_build_tag=build_tag,
    )


def test_a_stock_builds_rip_argv_carries_no_long_option() -> None:
    argv = _rip_argv(_stock_build_tag())
    assert [word for word in argv if word in LONG_OPTIONS] == []
    # And it is still a rip: the chokepoint's own flag is there.
    assert "-N" in argv


def test_the_fork_under_review_still_gets_the_diagnostics_record() -> None:
    tag = f"platterpus-fork-g{fork_source.PIN_UNDER_REVIEW}"
    assert DIAGNOSTICS_FLAG in _rip_argv(tag)


def test_a_fork_build_no_table_lists_still_gets_it() -> None:
    """Keyed on the fork's ID, not the commit list ``--consumer`` uses, so a fork
    build agreed after this release keeps its record."""
    tag = "platterpus-fork-g0000000"
    assert not fork_source.accepts_consumer_flag(tag)
    assert DIAGNOSTICS_FLAG in _rip_argv(tag)


@pytest.mark.parametrize(
    ("tag", "sent"),
    [
        ("release", False),
        ("g1a2b3c4", False),  # a banner we read and do not recognise
        ("platterpus-fork-g93afa15-dirty", True),
        ("", True),  # no banner read: the record is kept, see the docstring
    ],
)
def test_which_builds_get_the_flag(tag: str, sent: bool) -> None:
    assert bool(diagnostics_args_for_build(tag)) is sent


def test_a_scripts_placeholder_sends_nothing_to_stock_and_says_so() -> None:
    out, notes = expand_identity([DIAGNOSTICS_PLACEHOLDER], build_tag="release")
    assert out == []
    assert len(notes) == 1 and DIAGNOSTICS_PLACEHOLDER in notes[0]


def test_a_scripts_placeholder_still_reaches_the_fork() -> None:
    tag = f"platterpus-fork-g{fork_source.PIN_UNDER_REVIEW}"
    out, notes = expand_identity([DIAGNOSTICS_PLACEHOLDER], build_tag=tag)
    assert out[:1] == [DIAGNOSTICS_FLAG]
    assert notes == []
