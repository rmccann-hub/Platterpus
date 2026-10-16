"""TASKS R20 part 2: the fork's `Disc ISRC:` line and `--prefer-disc-isrc` (round 35).

Their round 35 lap 1 S4 gives the line's three shapes and S5 the option; `.24`'s
provider contract lists the option in P1 at line 60 and the line in P2 at lines
309-310 (`docs/handshake/inbound/artifacts/round-35-lap-01-provider-contract-
g16b9469.md`). The real `.24` log here is the fork's golden reference as their
tree held it at `cyanrip@e1adf47` (`docs/golden-reference.log`), whose three
tracks give the `unknown` shape; the `code` and `none` shapes are built to S4.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus import fun512
from platterpus import isrc_provenance as ip
from platterpus.adapters.cyanrip_backend import (
    PREFER_DISC_ISRC_FLAG,
    CyanripImpl,
    prefer_disc_isrc_args_for_build,
)
from platterpus.deps import fork_source
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.rip_report import build_report

_FIXTURES = Path(__file__).parent / "fixtures"
_R35_LOG = _FIXTURES / "cyanrip_fork_golden_reference_r35.log"
_R6B_LOG = _FIXTURES / "cyanrip_fork_golden_reference_r6b.log"
_CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "docs/handshake/inbound/artifacts/round-35-lap-01-provider-contract-g16b9469.md"
)
_TAG_24 = "platterpus-fork-g93afa15"


def _with_line(line: str) -> str:
    """The `.24` golden reference with track 1's `Disc ISRC:` line replaced."""
    text = _R35_LOG.read_text(encoding="utf-8")
    old = "  Disc ISRC:     unknown (the driver does not report reading ISRC)\n"
    assert old in text
    return text.replace(old, line, 1)


# --- the line -------------------------------------------------------------------


def test_the_24_golden_reference_is_cyanrips_own_signed_log() -> None:
    assert fun512.verify(_R35_LOG.read_bytes()) == fun512.VALID


def test_every_track_of_the_24_log_states_the_unknown_shape_and_its_reason() -> None:
    tracks = parse_cyanrip_log(_R35_LOG.read_text(encoding="utf-8")).tracks

    assert len(tracks) == 3  # floor: the line is read on every track it is on
    for track in tracks:
        assert (track.disc_isrc, track.disc_isrc_state, track.disc_isrc_reason) == (
            "",
            "unknown",
            "the driver does not report reading ISRC",
        )


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("  Disc ISRC:     USRC17607839\n", ("USRC17607839", "code", "")),
        (
            "  Disc ISRC:     none (libcdio returned none)\n",
            ("", "none", "libcdio returned none"),
        ),
        (
            "  Disc ISRC:     none (libcdio returned an all-zero ISRC)\n",
            ("", "none", "libcdio returned an all-zero ISRC"),
        ),
        ("  Disc ISRC:     unknown (not read)\n", ("", "unknown", "not read")),
    ],
)
def test_each_shape_s4_gives_is_read(line: str, expected: tuple[str, str, str]) -> None:
    track = parse_cyanrip_log(_with_line(line)).tracks[0]
    assert (track.disc_isrc, track.disc_isrc_state, track.disc_isrc_reason) == expected


def test_a_build_without_the_line_states_nothing_not_none() -> None:
    track = parse_cyanrip_log(_R6B_LOG.read_text(encoding="utf-8")).tracks[0]
    assert (track.disc_isrc, track.disc_isrc_state, track.disc_isrc_reason) == (
        "",
        "",
        "",
    )


def test_the_report_carries_the_line_per_track() -> None:
    log = parse_cyanrip_log(_with_line("  Disc ISRC:     USRC17607839\n"))
    row = build_report(log)["tracks"][0]

    assert (row["disc_isrc"], row["disc_isrc_state"], row["disc_isrc_reason"]) == (
        "USRC17607839",
        "code",
        None,
    )


# --- the option -----------------------------------------------------------------


def test_the_flag_we_send_is_the_one_24s_contract_lists() -> None:
    row = next(
        line
        for line in _CONTRACT.read_text(encoding="utf-8").splitlines()
        if "prefer-disc-isrc" in line
    )
    assert row.startswith(f"| none | `{PREFER_DISC_ISRC_FLAG}` |"), row


@pytest.mark.parametrize(
    ("tag", "sent"),
    [
        (_TAG_24, True),
        (f"{_TAG_24}-dirty", True),
        ("platterpus-fork-g891c79e", False),  # .23 has no such option
        ("", False),  # an unknown build gets no capability-gated flag
    ],
)
def test_the_option_goes_only_to_a_build_whose_contract_lists_it(
    tag: str, sent: bool
) -> None:
    assert fork_source.accepts_prefer_disc_isrc(tag) is sent
    assert prefer_disc_isrc_args_for_build(tag) == (
        [PREFER_DISC_ISRC_FLAG] if sent else []
    )


@pytest.mark.parametrize(
    ("setting", "tag", "sent"),
    [
        (True, _TAG_24, True),
        (False, _TAG_24, False),
        (True, "platterpus-fork-g891c79e", False),
    ],
)
def test_the_rip_argv_sends_it_when_asked_and_supported(
    setting: bool, tag: str, sent: bool
) -> None:
    argv = CyanripImpl(binary_path="cyanrip")._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=667,
        prefer_disc_isrc=setting,
        ripper_build_tag=tag,
    )
    assert (PREFER_DISC_ISRC_FLAG in argv) is sent


def test_the_setting_defaults_on() -> None:
    from platterpus.config import Config

    assert Config().prefer_disc_isrc is True


# --- the report block: the disc against what WE passed ---------------------------


def _reading(written: str | None, disc: str | None) -> ip.IsrcReading:
    return ip.IsrcReading(
        ip.STATE_READ,
        tracks=(ip.TrackIsrc(1, written, disc, None, ripped=True),),
    )


def test_under_the_option_the_disc_is_still_compared_with_musicbrainz() -> None:
    """With `--prefer-disc-isrc` the files carry the disc's code, so comparing the
    files with the disc always agrees. The comparison is with what we passed."""
    reading = _reading(written="USRC17607839", disc="USRC17607839")
    block = ip.report_block(
        reading,
        passed={1: "AAAAA0000001"},
        argv=("cyanrip", "--prefer-disc-isrc", "-N"),
    )
    row = block["tracks"][0]  # type: ignore[index]  # a list of row dicts

    assert row["agreement"] == ip.DIFFER  # type: ignore[index]  # row is a dict
    assert block["prefer_disc_isrc_sent"] is True
    [(code, sentence)] = ip.findings(block)
    assert code == "isrc_disc_differs"
    assert "USRC17607839" in sentence and "AAAAA0000001" in sentence


def test_a_track_we_passed_nothing_for_is_disc_only_even_when_the_files_carry_it() -> (
    None
):
    block = ip.report_block(_reading("USRC17607839", "USRC17607839"), passed={})
    assert block["tracks"][0]["agreement"] == ip.DISC_ONLY  # type: ignore[index]  # rows are dicts


def test_without_an_argv_whether_the_option_went_is_not_determined() -> None:
    assert ip.report_block(_reading(None, None))["prefer_disc_isrc_sent"] is None
    sent = ip.report_block(_reading(None, None), argv=("cyanrip", "-N"))
    assert sent["prefer_disc_isrc_sent"] is False


@given(st.text(max_size=200))
def test_the_line_parser_never_raises(tail: str) -> None:
    parse_cyanrip_log(_with_line(f"  Disc ISRC:     {tail}\n"))


def test_the_pin_under_review_has_been_asked_about_the_option() -> None:
    """The consumer-flag guard's shape (`test_rig_scripts`), for this option: the
    Full run's `expect-rip-argv with --prefer-disc-isrc` holds only on a build in
    the set, so the next pin move must answer the question, not skip it. A build
    that genuinely lacks the option is a real state: say so here and change this."""
    tag = f"{fork_source.FORK_BRANCH}-g{fork_source.PIN_UNDER_REVIEW}"
    assert fork_source.BUILD_TAGS_ACCEPTING_PREFER_DISC_ISRC  # floor
    assert fork_source.accepts_prefer_disc_isrc(tag), (
        f"{tag} is the build the acceptance run installs and it is not in "
        "BUILD_TAGS_ACCEPTING_PREFER_DISC_ISRC; add it if its provider contract "
        "lists --prefer-disc-isrc in P1"
    )
