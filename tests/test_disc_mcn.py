"""cyanrip's ``Disc MCN:`` row, in both parsers and the report (TASKS R176).

The fork proposed printing the row always, with a reason when there is no MCN
(their round 38 lap 3 S17), we accepted (our round 38 lap 4 S11), and they print
it from the first build after a release of ours that reads it (their round 41
lap 1 S18). Today's row, ``Disc MCN:       %s``, is cited to their source in
``disc_mcn.py``. Cases follow the five tiers of ``docs/testing.md``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

import pytest

from platterpus import disc_mcn
from platterpus.disc_mcn import (
    MCN_ALL_ZERO,
    MCN_NONE,
    MCN_NOT_PRESENT,
    MCN_READ,
    MCN_UNKNOWN,
    MCN_UNRECOGNISED,
    DiscMcn,
    read_value,
)
from platterpus.parsers.cd_info import parse_cd_info
from platterpus.parsers.cyanrip_info import parse_cyanrip_info
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import DRIVE_FACT_NOT_PRESENT, DRIVE_FACT_UNRECOGNISED
from platterpus.rip_report import build_report

_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
#: The fork's lap that proposes the three reason forms, as filed here.
_LAP: Final[Path] = _ROOT / "docs" / "handshake" / "inbound" / "round-38-lap-03.md"
#: A `.26` image rip, which prints no `Disc MCN:` row (an image has no MCN).
_FIXTURE: Final[Path] = (
    _ROOT / "tests" / "fixtures" / "cyanrip_fork_golden_reference_r36l8.log"
)
_CDDB_ROW: Final[str] = "CDDB ID:        14000603\n"

#: Every form the parsers must take, the value as printed, and what it reads as.
#: The three reason forms are word for word from S17; the code forms are
#: today's `%s` (`cyanrip@13bec0a:src/cyanrip_log.c:1367`).
_FORMS: Final[dict[str, tuple[str, DiscMcn]]] = {
    "code": ("0602547288769", DiscMcn(MCN_READ, "0602547288769", "")),
    "upstream all zeroes": ("0000000000000", DiscMcn(MCN_ALL_ZERO, "0" * 13, "")),
    "none": (
        "none (libcdio returned none)",
        DiscMcn(MCN_NONE, "", "libcdio returned none"),
    ),
    "unknown, driver": (
        "unknown (the driver does not report reading MCN)",
        DiscMcn(MCN_UNKNOWN, "", "the driver does not report reading MCN"),
    ),
    "unknown, capabilities": (
        "unknown (capabilities query failed)",
        DiscMcn(MCN_UNKNOWN, "", "capabilities query failed"),
    ),
}


def _rip_log_with(value: str) -> str:
    """The fixture with a ``Disc MCN:`` row where the source prints it."""
    text = _FIXTURE.read_text(encoding="utf-8")
    assert text.count(_CDDB_ROW) == 1, "the fixture changed under this test"
    assert "Disc MCN:" not in text
    return text.replace(_CDDB_ROW, f"{_CDDB_ROW}Disc MCN:       {value}\n")


# --- Easy: every form, in both parsers ----------------------------------------


def test_the_proposed_reasons_are_the_laps_own_words() -> None:
    """Verify our copy against their text, not our memory of it."""
    s17 = next(
        ln
        for ln in _LAP.read_text(encoding="utf-8").splitlines()
        if ln.startswith("S17 ASK:")
    )
    reasons = [r for rs in disc_mcn.PROPOSED_REASONS.values() for r in rs]
    assert len(reasons) == 3
    for state, listed in disc_mcn.PROPOSED_REASONS.items():
        for reason in listed:
            assert f"`{state} ({reason})`" in s17, (state, reason)
    for name in ("none", "unknown, driver", "unknown, capabilities"):
        assert f"`{_FORMS[name][0]}`" in s17, name


def test_the_form_table_holds_every_form_and_every_state() -> None:
    """The floor under the two sweeps below: five forms, the three S17 reason
    forms among them, and every state but the two no form can give."""
    assert len(_FORMS) == 5
    values = {value for value, _ in _FORMS.values()}
    for state, reasons in disc_mcn.PROPOSED_REASONS.items():
        assert {f"{state} ({r})" for r in reasons} <= values
    states = {expected.state for _, expected in _FORMS.values()}
    assert states == disc_mcn.MCN_STATES - {MCN_UNRECOGNISED, MCN_NOT_PRESENT}


@pytest.mark.parametrize("name", sorted(_FORMS))
def test_each_form_reads_in_the_rip_log(name: str) -> None:
    value, expected = _FORMS[name]
    parsed = parse_cyanrip_log(_rip_log_with(value))
    assert parsed.disc_mcn == expected
    # Nothing else in the header moved: the row is claimed, not swallowed.
    assert parsed.cddb_id == "14000603"
    assert parsed.ripping_info.album == "Unknown disc (OMP2)"


@pytest.mark.parametrize("name", sorted(_FORMS))
def test_each_form_reads_in_the_info_parser_as_in_the_rip_log(name: str) -> None:
    """Two surfaces, one key: `-I` and a rip read one line the same way."""
    value, expected = _FORMS[name]
    report = f"Disc tracks:    3\nCDDB ID:        14000603\nDisc MCN:       {value}\n"
    assert parse_cyanrip_info(report).disc_mcn == expected
    assert parse_cyanrip_info(report).disc_mcn == (
        parse_cyanrip_log(_rip_log_with(value)).disc_mcn
    )


def test_no_row_is_not_present_in_every_parser() -> None:
    assert parse_cyanrip_log(_FIXTURE.read_text(encoding="utf-8")).disc_mcn == (
        DiscMcn()
    )
    assert parse_cyanrip_info("DiscID:         x\n").disc_mcn.state == MCN_NOT_PRESENT
    # The legacy format has no such row at all.
    assert parse_cd_info("CDDB disc id: 940A6A0B\n").disc_mcn == DiscMcn()


def test_the_state_words_are_the_drive_facts_words() -> None:
    """One word means one thing in the report's `rip` block."""
    assert MCN_NOT_PRESENT == DRIVE_FACT_NOT_PRESENT
    assert MCN_UNRECOGNISED == DRIVE_FACT_UNRECOGNISED


# --- Hard: what is NOT an MCN -------------------------------------------------


@pytest.mark.parametrize(
    ("value", "kept"),
    [
        ("060254728876", "060254728876"),  # 12 digits
        ("06025472887690", "06025472887690"),  # 14 digits
        ("060254728876X", "060254728876X"),  # a letter
        ("０６０２５４７２８８７６９", "０６０２５４７２８８７６９"),  # full-width
        ("06025472887²9", "06025472887²9"),  # a superscript two
        ("0602547288769 (from CD-TEXT)", "0602547288769 (from CD-TEXT)"),
        ("none", "none"),  # the word with no reason
        ("absent (not read)", "absent (not read)"),  # a state word not proposed
        ("0602547\x01288769", "0602547\\x01288769"),  # a control character
    ],
)
def test_anything_but_13_ascii_digits_is_kept_screened_and_flagged(
    value: str, kept: str, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="platterpus.disc_mcn"):
        parsed = parse_cyanrip_log(_rip_log_with(value)).disc_mcn
    assert parsed == DiscMcn(MCN_UNRECOGNISED, kept, "")
    assert any("unrecognised" in r.getMessage() for r in caplog.records)


def test_an_empty_value_is_kept_as_saying_so() -> None:
    parsed = parse_cyanrip_info("Disc MCN:       \n").disc_mcn
    assert parsed == DiscMcn(MCN_UNRECOGNISED, "(an empty value)", "")


def test_a_long_value_is_bounded_and_the_cut_counted() -> None:
    parsed = read_value("7" * 5000)
    assert parsed.state == MCN_UNRECOGNISED
    assert len(parsed.value) < 300
    assert "4880 character(s) omitted" in parsed.value


def test_a_reason_the_lap_does_not_list_is_kept_and_noted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A reworded reason is still the ripper's word: kept, never refused."""
    with caplog.at_level(logging.INFO, logger="platterpus.disc_mcn"):
        parsed = read_value("unknown (image)")
    assert parsed == DiscMcn(MCN_UNKNOWN, "", "image")
    assert any("does not list" in r.getMessage() for r in caplog.records)
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="platterpus.disc_mcn"):
        read_value("none (libcdio returned none)")
    assert not caplog.records


def test_a_control_character_in_a_reason_is_escaped() -> None:
    parsed = read_value("none (libcdio\x1b[31m returned none)")
    assert parsed.state == MCN_NONE
    assert parsed.reason == "libcdio\\x1b[31m returned none"


def test_a_non_string_is_unrecognised_not_a_crash() -> None:
    parsed = read_value(None)
    assert parsed.state == MCN_UNRECOGNISED
    assert parsed.value


# --- Unexpected: a forged copy ------------------------------------------------


def test_a_second_copy_in_the_info_output_is_not_determined(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An echoed CD-TEXT value with a line break can print a second row, before
    or after cyanrip's; neither can be preferred (the rip log's ONCE guard)."""
    two = "Disc MCN:       0602547288769\nDisc MCN:       1111111111111\n"
    with caplog.at_level(logging.WARNING, logger="platterpus.parsers.cyanrip_info"):
        assert parse_cyanrip_info(two).disc_mcn == DiscMcn()
    assert any("not determined" in r.getMessage() for r in caplog.records)


def test_a_second_copy_in_the_rip_log_is_not_determined() -> None:
    text = _rip_log_with("0602547288769").replace(
        "Album:          Unknown disc (OMP2)\n",
        "Album:          Unknown disc (OMP2)\nDisc MCN:       1111111111111\n",
    )
    assert parse_cyanrip_log(text).disc_mcn == DiscMcn()


# --- The report ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "block"),
    [
        ("0602547288769", {"state": "read", "value": "0602547288769", "reason": None}),
        (
            "none (libcdio returned none)",
            {"state": "none", "value": None, "reason": "libcdio returned none"},
        ),
        ("12AB", {"state": "unrecognised", "value": "12AB", "reason": None}),
    ],
)
def test_the_report_carries_the_row(value: str, block: dict[str, object]) -> None:
    rip = build_report(parse_cyanrip_log(_rip_log_with(value)))["rip"]
    assert rip["disc_mcn"] == block


def test_the_report_says_not_present_without_a_row() -> None:
    absent = {"state": "not_present", "value": None, "reason": None}
    rip = build_report(parse_cyanrip_log(_FIXTURE.read_text(encoding="utf-8")))["rip"]
    assert rip["disc_mcn"] == absent
    # A stand-in that is not a DiscMcn never reads as a value.
    assert disc_mcn.report_block("0602547288769") == absent
    assert disc_mcn.report_block(DiscMcn("invented", "1", "")) == absent
