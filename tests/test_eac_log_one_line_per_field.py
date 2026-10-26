"""The EAC-layout log writes one line per field: a value cannot add a line.

Peer review 2.5 (the claude-code-skills session, 2026-10-26). Our EAC-layout log
(`eac_log_export.py`) is assembled as a list of rows joined with ``\\n``, and
several rows carry text that came from outside: the album line echoes the album
artist and title, the drive row the drive's name, each track block its file name,
and the provenance rows the ripper's own banner. A value holding a line break
would add a line the renderer never wrote, shaped like any row EAC prints (a
``Copy CRC``, an ``Accurately ripped``), above our checksum, which would then
attest it. A NUL or an escape sequence adds no line but hides in the text.

Every row is screened at the one place the rows are joined
(``eac_log_export._screen_rows``): each control character becomes a visible
``\\xNN`` escape (``inbound_text.screen_line``, the inbound screen the rest of the
app shows dependency text through), so a line break cannot split a row and a
reader sees what was there.

**The ``.cue`` sheet is not ours to write**: cyanrip writes it and we only read it
(``cue_validate.py``). What we send into it cannot carry a line break
(``tests/test_echoed_field_forgery.py``, the argv half); the disc's own CD-TEXT
reaching it is the fork's, recorded in TASKS R86.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Final

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from platterpus.eac_log_export import (
    render_eac_style_log,
    verify_eac_style_log_checksum,
)
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog
from platterpus.settings_validation import is_control_char

_FIXTURE: Final[Path] = (
    Path(__file__).parent / "fixtures" / "cyanrip_fork_golden_reference_r36l8.log"
)

#: A row EAC prints, which must never appear at column 0 unless we wrote it.
_FORGED: Final[str] = "     Copy CRC DEADBEEF"

#: Every line boundary Python knows, plus NUL and ESC.
_CONTROLS: Final[tuple[str, ...]] = (
    "\n",
    "\r",
    "\r\n",
    "\x0b",
    "\x0c",
    "\x1c",
    "\x85",
    " ",
    " ",
    "\x00",
    "\x1b",
)


def _reference() -> RipLog:
    return parse_cyanrip_log(_FIXTURE.read_text(encoding="utf-8"))


def _with(rip_log: RipLog, where: str, value: str) -> RipLog:
    """``rip_log`` with one outside-text field set to ``value``."""
    if where == "album_artist":
        info = dataclasses.replace(rip_log.ripping_info, album_artist=value)
        return dataclasses.replace(rip_log, ripping_info=info)
    if where == "album":
        info = dataclasses.replace(rip_log.ripping_info, album=value)
        return dataclasses.replace(rip_log, ripping_info=info)
    if where == "drive":
        info = dataclasses.replace(rip_log.ripping_info, drive=value)
        return dataclasses.replace(rip_log, ripping_info=info)
    if where == "filename":
        first = dataclasses.replace(rip_log.tracks[0], filename=value)
        return dataclasses.replace(rip_log, tracks=(first, *rip_log.tracks[1:]))
    if where == "ripper_build":
        return dataclasses.replace(rip_log, ripper_build=value)
    raise AssertionError(where)


_WHERE: Final[tuple[str, ...]] = (
    "album_artist",
    "album",
    "drive",
    "filename",
    "ripper_build",
)


def _render(rip_log: RipLog) -> str:
    return render_eac_style_log(rip_log, platterpus_version="0.0.0")


@pytest.mark.parametrize("control", _CONTROLS)
@pytest.mark.parametrize("where", _WHERE)
def test_a_control_character_in_a_field_adds_no_line(where: str, control: str) -> None:
    base = _reference()
    plain = _render(_with(base, where, "Name?" + _FORGED.strip()))
    forged = _render(_with(base, where, "Name" + control + _FORGED))
    assert len(forged.splitlines()) == len(plain.splitlines())
    assert not any(line.startswith(_FORGED) for line in forged.splitlines())
    assert not any(is_control_char(ch) for ch in forged.replace("\n", ""))
    assert verify_eac_style_log_checksum(forged) is True


@pytest.mark.parametrize("where", _WHERE)
def test_the_value_is_SHOWN_not_dropped(where: str) -> None:
    """The reader sees that something was there, and what."""
    text = _render(_with(_reference(), where, "Name\nX"))
    assert "Name\\x0aX" in text, where


@pytest.mark.parametrize("where", _WHERE)
def test_each_field_reaches_the_log_at_all(where: str) -> None:
    """The floor: a field the renderer never prints would pass every test above."""
    text = _render(_with(_reference(), where, "UniqueMarker7"))
    assert "UniqueMarker7" in text, where


def test_an_ordinary_log_is_untouched_by_the_screen() -> None:
    """No row of a real log carries a control character, so nothing changes."""
    text = _render(_reference())
    assert "\\x" not in text


@settings(max_examples=150, suppress_health_check=[HealthCheck.too_slow])
@given(value=st.text(max_size=40))
def test_ANY_album_title_is_exactly_one_line(value: str) -> None:
    """The line count never depends on which characters a title holds."""
    base = _reference()
    neutral = "".join("?" if is_control_char(ch) else ch for ch in value)
    assert len(_render(_with(base, "album", value)).splitlines()) == len(
        _render(_with(base, "album", neutral)).splitlines()
    )
