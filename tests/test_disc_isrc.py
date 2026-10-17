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
        # `.25` (round 35 lap 5 S2-S3, cyanrip@72a7a8b): a code the disc returned
        # that is not an ISO 3901 code, kept and not used. Their cue's two cases.
        (
            "  Disc ISRC:     1234567890AB (not an ISO 3901 code, so not used)\n",
            ("1234567890AB", "not_used", "not an ISO 3901 code, so not used"),
        ),
        (
            "  Disc ISRC:     usrc17607839 (not an ISO 3901 code, so not used)\n",
            ("usrc17607839", "not_used", "not an ISO 3901 code, so not used"),
        ),
    ],
)
def test_each_shape_s4_gives_is_read(line: str, expected: tuple[str, str, str]) -> None:
    track = parse_cyanrip_log(_with_line(line)).tracks[0]
    assert (track.disc_isrc, track.disc_isrc_state, track.disc_isrc_reason) == expected


def _contract_rows() -> list[str]:
    """`.24`'s P2 rows for the line, as its provider contract publishes them."""
    import re

    rows = re.findall(
        r"^\| `[^`]+` \| `(Disc ISRC:[^`]*)` \|$",
        _CONTRACT.read_text(encoding="utf-8"),
        re.M,
    )
    assert rows == ["Disc ISRC:     %s", "Disc ISRC:     %s (%s)"]  # floor: both
    return rows


@pytest.mark.parametrize(
    ("row", "fill", "expected"),
    [
        (0, ("USRC17607839",), ("USRC17607839", "code", "")),
        (1, ("none", "libcdio returned none"), ("", "none", "libcdio returned none")),
        (
            1,
            ("unknown", "the driver does not report reading ISRC"),
            ("", "unknown", "the driver does not report reading ISRC"),
        ),
        # The same `%s (%s)` row with a code where `none`/`unknown` stood (`.25`).
        (
            1,
            ("1234567890AB", "not an ISO 3901 code, so not used"),
            ("1234567890AB", "not_used", "not an ISO 3901 code, so not used"),
        ),
    ],
)
def test_the_contracts_own_rows_filled_in_are_read(
    row: int, fill: tuple[str, ...], expected: tuple[str, str, str]
) -> None:
    """Built from the contract's format strings, not from our own pattern: the
    `.24` contract's P2 rows (lines 309-310), indented as the track block is."""
    line = "  " + _contract_rows()[row] % fill + "\n"
    track = parse_cyanrip_log(_with_line(line)).tracks[0]
    assert (track.disc_isrc, track.disc_isrc_state, track.disc_isrc_reason) == expected


def test_a_build_without_the_line_states_nothing_not_none() -> None:
    track = parse_cyanrip_log(_R6B_LOG.read_text(encoding="utf-8")).tracks[0]
    assert (track.disc_isrc, track.disc_isrc_state, track.disc_isrc_reason) == (
        "",
        "",
        "",
    )


def test_the_24_log_with_the_line_removed_reads_as_a_build_before_24() -> None:
    """The same track block with no `Disc ISRC:` line at all: nothing is stated,
    which is not the ripper's `none` and not its `unknown`."""
    track = parse_cyanrip_log(_with_line("")).tracks[0]
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


# --- the Full run's bounded -O read (their lap 1 S17 item 3) ----------------------


def test_lasttrack_expands_to_the_loaded_discs_highest_track_number() -> None:
    from types import SimpleNamespace

    from platterpus.uiscript.runner import _last_track_number
    from platterpus.uiscript.script import expand_last_track

    rows = [SimpleNamespace(number=n) for n in (1, 2, 14, 3)]
    window = SimpleNamespace(_track_table=SimpleNamespace(tracks=lambda: rows))
    assert _last_track_number(window) == 14
    assert expand_last_track(["-l", "(lasttrack)"], 14) == ["-l", "14"]
    # No table, or no rows: nothing to name, so the step fails rather than guess.
    assert _last_track_number(SimpleNamespace()) is None
    empty = SimpleNamespace(_track_table=SimpleNamespace(tracks=lambda: []))
    assert _last_track_number(empty) is None


_RIG = Path(__file__).resolve().parents[1] / "src/platterpus/rig_scripts"


def test_the_bounded_o_read_is_the_last_track_only_and_stops_on_the_wrong_rig() -> None:
    """The operator's point 4 (2026-10-16): run by hand, last track only, at
    +667, and impossible without the limit. The limit is the `cyanrip` verb's
    own (no step can pass one); the script stops before the read unless the
    build is `.24` and the offset +667."""
    from platterpus.uiscript.runner import CYANRIP_VERB_TIMEOUT_S
    from platterpus.uiscript.script import (
        args_as_preflight_sees_them,
        parse,
        sanitise_cyanrip_args,
    )

    text = (_RIG / "overreadprobe.txt").read_text(encoding="utf-8")
    steps = parse(text)
    assert all(not s.error for s in steps)
    reads = [s for s in steps if s.verb == "cyanrip" and "-O" in s.args]
    # Two -O reads: the last track at the drive's offset (their lap 3 S9), then
    # the lead-in side at a deliberately wrong -667 (S10), after it.
    assert len(reads) == 2
    leadin = list(reads[1].args)
    assert leadin[leadin.index("-s") + 1] == "-667"
    assert leadin[leadin.index("-l") + 1] == "1"
    args = list(reads[0].args)
    assert args[args.index("-l") + 1] == "(lasttrack)"
    assert args[args.index("-s") + 1] == "(offset)"
    assert sanitise_cyanrip_args(args_as_preflight_sees_them(args)) is None
    # Both preconditions are checked, and stopped on, before the read.
    before = steps[: steps.index(reads[0])]
    assert sum(s.verb == "abort-if-failed" for s in before) == 2
    assert any(
        s.verb == "expect" and tuple(s.args[:2]) == ("read_offset", "667")
        for s in before
    )
    assert any(
        s.verb == "expect-cyanrip" and "platterpus-fork-g93afa15" in s.args
        for s in before
    )
    assert 60 <= CYANRIP_VERB_TIMEOUT_S <= 600  # "a few minutes"


def test_no_other_packaged_script_sends_o() -> None:
    for script in sorted(_RIG.glob("*.txt")):
        if script.name == "overreadprobe.txt":
            continue
        for line in script.read_text(encoding="utf-8").splitlines():
            if line.startswith("cyanrip "):
                assert "-O" not in line.split(), (script.name, line)


def test_a_code_cyanrip_did_not_use_is_flagged_with_its_own_reason() -> None:
    """Our report and `.25`'s check agree in both directions (their lap 5 S5): a
    lower-case code is malformed to both, and the finding quotes the ripper."""
    reading = ip.IsrcReading(
        ip.STATE_READ,
        tracks=(
            ip.TrackIsrc(
                4,
                None,
                "usrc17607839",
                "not an ISO 3901 code, so not used",
                ripped=True,
            ),
        ),
    )
    block = ip.report_block(reading, passed={})
    [(code, sentence)] = ip.findings(block)
    assert code == "isrc_disc_malformed"
    assert sentence.endswith("; cyanrip: not an ISO 3901 code, so not used")


def _cyanrip_iso3901(code: str) -> bool:
    """A port of `crip_isrc_is_iso3901()` (`cyanrip@64bc315:src/cyanrip_main.h:643-653`)."""
    if len(code) != 12:
        return False
    for i, c in enumerate(code):
        letter = "A" <= c <= "Z"
        digit = "0" <= c <= "9"
        if not (letter if i < 2 else (letter or digit) if i < 5 else digit):
            return False
    return True


@given(
    st.one_of(
        st.text(max_size=16),
        st.from_regex(r"[A-Za-z0-9 -]{10,14}", fullmatch=True),
        st.from_regex(r"[A-Z]{2}[A-Z0-9]{3}[0-9]{7}", fullmatch=True),
    )
)
def test_our_well_formed_is_the_rippers_check_in_both_directions(code: str) -> None:
    """Their lap 5 S5: our report normalised before checking and theirs reads the
    bytes, so a lower-case code was fine to us and refused by them. Now equal."""
    assert ip.well_formed(code) is _cyanrip_iso3901(code)


def test_a_refused_code_with_inner_spaces_is_still_read() -> None:
    track = parse_cyanrip_log(
        _with_line("  Disc ISRC:     US RC1 76 (not an ISO 3901 code, so not used)\n")
    ).tracks[0]
    assert (track.disc_isrc, track.disc_isrc_state) == ("US RC1 76", "not_used")


def test_the_consumer_contract_lists_the_option_every_rip_on_24_sends() -> None:
    """Round 35 regression: §3 "Flags we pass you" was derived from a maximal
    argv for the installed pin only, so `--prefer-disc-isrc`, sent to the build
    under review alone, was missing from the contract that claims completeness."""
    contract = (
        Path(__file__).resolve().parents[1] / "docs/cyanrip-consumer-contract.md"
    ).read_text(encoding="utf-8")
    flags_line = contract.split("## 3. Flags we pass you", 1)[1].split("```")[1]
    assert PREFER_DISC_ISRC_FLAG in flags_line.split()
    assert "--consumer" in flags_line.split()  # floor: the other gated flag too


def test_the_isrc_disc_script_rips_with_the_option_then_without() -> None:
    """Their lap 3 S8: one disc that carries ISRCs, ripped with the option and
    without, each rip's argv checked as spawned, and the default put back."""
    from platterpus.uiscript.script import parse

    steps = parse((_RIG / "isrcdisc.txt").read_text(encoding="utf-8"))
    assert all(not s.error for s in steps)
    seen = [
        (s.verb, tuple(s.args))
        for s in steps
        if s.verb in ("rip", "expect-rip-argv")
        or (s.verb == "set" and s.args[0] == "prefer_disc_isrc")
    ]
    assert seen == [
        ("set", ("prefer_disc_isrc", "on")),
        ("rip", ()),
        ("expect-rip-argv", ("with", PREFER_DISC_ISRC_FLAG)),
        ("set", ("prefer_disc_isrc", "off")),
        ("rip", ()),
        ("expect-rip-argv", ("without", PREFER_DISC_ISRC_FLAG)),
        ("set", ("prefer_disc_isrc", "on")),
    ]
