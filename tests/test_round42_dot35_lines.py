"""What `.35` prints that our parsers must take (the fork's round 42 lap 1, S3 to S7).

`.35` (`cyanrip@1280aa4`) ships what round 41 agreed. Each line is read here from
the fork's own published output where it prints one, and otherwise from the line
their source prints, filled in:

* **S3, `Disc MCN:` always**, with four reasons beyond the three agreed. Their
  golden reference as published with round 42's lap 1
  (`tests/fixtures/cyanrip_fork_golden_reference_r42.log`, byte for byte from
  `cyanrip@5ff89ffa:docs/golden-reference.log`, built at `g0a062f8`, whose `src/`
  is `1280aa4`'s) prints `Disc MCN:       none (libcdio returned none)`, an image
  having no MCN. The four new reasons are held in `tests/test_disc_mcn.py`.
* **S5, CD-TEXT's unknown language**: `CD-TEXT:        present (unknown language,
  ...)` is the line's existing form (`cyanrip@1280aa4:src/cyanrip_log.c:80-81`),
  and the record's `cdtext.language` is null; no reader of ours reads either, and
  the line stays on the parser's documented list.
* **S6, `Invalid pregap:`** at exit 74: `tests/test_ripper_exit_class.py`.
* **S7, `Session gap: not determined (...)`** under `End LSN:`
  (`cyanrip@1280aa4:src/cyanrip_log.c:624-626`): kept on the track
  (`session_gap.read_session_gap`), never raised over.

Text only; no audio (Critical rule 8).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Final

import pytest

from platterpus.disc_mcn import MCN_NONE, DiscMcn
from platterpus.isrc_provenance import parse_isrcs
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.ripper_ending import RECORD_SCHEMA_PREFIX, STATE_READ, parse_ending
from platterpus.session_gap import (
    SESSION_GAP_NOT_DETERMINED,
    SESSION_GAP_UNRECOGNISED,
    SessionGap,
    read_session_gap,
)

_FIXTURES: Final[Path] = Path(__file__).parent / "fixtures"
#: `.35`'s golden reference log and record, byte for byte from the fork's
#: `platterpus-fork` at `5ff89ffa` ("Regenerate the golden reference and sample for
#: round 42's lap 1"), the commit their lap 1's pull request carried.
_GOLDEN_LOG: Final[Path] = _FIXTURES / "cyanrip_fork_golden_reference_r42.log"
_GOLDEN_RECORD: Final[Path] = _FIXTURES / "cyanrip_fork_diagnostics14_golden_dot35.json"

#: The line `.35` prints, its `%i` filled with `CRIP_XA_INTERVAL` (11400), as their
#: lap 1 S7 quotes it.
_SESSION_GAP: Final[str] = (
    "    Session gap: not determined (the last-session query failed; 11400 frames "
    "cut by assumption)"
)


# --- the golden reference, as published --------------------------------------------


def test_the_fixture_is_the_whole_dot35_log() -> None:
    text = _GOLDEN_LOG.read_text(encoding="utf-8")
    assert text.startswith("cyanrip 0.9.4-rc3+platterpus.35 (platterpus-fork-g")
    assert "Log FUN512:" in text, "the fixture is missing the log's footer"
    assert len(text.splitlines()) >= 250


def test_no_top_level_line_of_the_dot35_log_goes_unrecognised(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Every column-0 line `.35`'s golden reference prints is read or on the
    documented list; the message is asserted on, so a rename cannot pass this."""
    with caplog.at_level(logging.DEBUG, logger="platterpus.parsers.cyanrip_log"):
        parsed = parse_cyanrip_log(_GOLDEN_LOG.read_text(encoding="utf-8"))
    unrecognised = [r for r in caplog.records if "unrecognised top-level" in r.message]
    assert not unrecognised, "; ".join(str(r.args) for r in unrecognised)
    # Floor: the parse is the log, not nothing.
    assert len(parsed.tracks) == 3


def test_the_dot35_log_reads_its_mcn_reason() -> None:
    """S3 in the fork's own output: an image's MCN read gives no code."""
    parsed = parse_cyanrip_log(_GOLDEN_LOG.read_text(encoding="utf-8"))
    assert parsed.disc_mcn == DiscMcn(MCN_NONE, "", "libcdio returned none")
    assert "Disc MCN:       none (libcdio returned none)\n" in _GOLDEN_LOG.read_text(
        encoding="utf-8"
    )


def test_the_dot35_record_reads_through_our_record_readers() -> None:
    """`.35` keeps `cyanrip-diagnostics/14` (their lap 1 changes no key), and its
    `cdtext.language` is null where it does not know it (S5): the readers that
    recognise a record by its schema take it as they took `.34`'s."""
    text = _GOLDEN_RECORD.read_text(encoding="utf-8")
    data = json.loads(text)
    assert data["schema"] == "cyanrip-diagnostics/14"
    assert data["schema"].startswith(RECORD_SCHEMA_PREFIX)
    assert data["cyanrip"]["version"] == "0.9.4-rc3+platterpus.35"
    assert data["cdtext"]["language"] is None
    assert data["cyanrip"]["vcs"] == "0a062f8"
    ending = parse_ending(text)
    assert ending.state == STATE_READ
    assert (ending.exit_code, ending.interrupted) == (0, False)
    reading = parse_isrcs(text)
    assert reading.state == STATE_READ
    assert [t.number for t in reading.tracks] == [1, 2, 3]
    # The same keys at the top level as `.34`'s published record.
    dot34 = json.loads(
        (_FIXTURES / "cyanrip_fork_diagnostics14_golden_dot34.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(data) == set(dot34)


# --- S5: CD-TEXT's unknown language ------------------------------------------------


def test_cdtext_with_an_unknown_language_is_claimed_not_unrecognised(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """`present (unknown language, ...)` is the line's existing shape; it must stay
    claimed, so a `.toc` or inline-CUE rip does not read as an unknown line."""
    text = _GOLDEN_LOG.read_text(encoding="utf-8")
    row = "CD-TEXT:        none reported by libcdio (absent, or unreadable by this driver)\n"
    assert text.count(row) == 1, "the fixture changed under this test"
    present = text.replace(
        row,
        "CD-TEXT:        present (unknown language, 2 disc fields, 3 of 3 tracks tagged)\n",
    )
    with caplog.at_level(logging.DEBUG, logger="platterpus.parsers.cyanrip_log"):
        parsed = parse_cyanrip_log(present)
    assert not [r for r in caplog.records if "unrecognised top-level" in r.message]
    assert len(parsed.tracks) == 3


# --- S7: Session gap -----------------------------------------------------------------


def _with_session_gap(line: str = _SESSION_GAP) -> str:
    """The golden log with the line under track 3's `End LSN:`, where `.35` prints
    it (the image has one session, so the fork's own output carries none)."""
    text = _GOLDEN_LOG.read_text(encoding="utf-8")
    end = "    End LSN:     599\n"
    assert text.count(end) == 1, "the fixture changed under this test"
    return text.replace(end, f"{end}{line}\n")


def test_the_session_gap_line_is_kept_on_its_track() -> None:
    parsed = parse_cyanrip_log(_with_session_gap())
    tracks = {t.number: t for t in parsed.tracks}
    assert tracks[3].session_gap == SessionGap(
        state=SESSION_GAP_NOT_DETERMINED,
        text=_SESSION_GAP.strip().removeprefix("Session gap: "),
        reason="the last-session query failed; 11400 frames cut by assumption",
        frames_cut=11400,
    )
    # The other tracks say nothing, and nothing else in the block moved.
    assert tracks[1].session_gap is None and tracks[2].session_gap is None
    assert tracks[3].end_sector == 599
    assert (
        parse_cyanrip_log(_GOLDEN_LOG.read_text(encoding="utf-8")).tracks[2].session_gap
        is None
    )


def test_an_unread_session_gap_wording_is_kept_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="platterpus.parsers.cyanrip_log"):
        parsed = parse_cyanrip_log(_with_session_gap("    Session gap: 11400 frames"))
    gap = {t.number: t for t in parsed.tracks}[3].session_gap
    assert gap is not None and gap.state == SESSION_GAP_UNRECOGNISED
    assert gap.text == "11400 frames" and gap.frames_cut is None
    assert any("unrecognised Session gap" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize(
    ("value", "state", "frames"),
    [
        ("not determined (the last-session query failed; 11400 frames cut by "
         "assumption)", SESSION_GAP_NOT_DETERMINED, 11400),
        ("not determined (the last-session query failed)", SESSION_GAP_NOT_DETERMINED,
         None),
        ("not determined (1 frame cut by assumption)", SESSION_GAP_NOT_DETERMINED, 1),
        ("", SESSION_GAP_UNRECOGNISED, None),
        ("not determined", SESSION_GAP_UNRECOGNISED, None),
        ("11400 frames", SESSION_GAP_UNRECOGNISED, None),
        ("not determined (a (nested) reason)", SESSION_GAP_UNRECOGNISED, None),
    ],
)  # fmt: skip
def test_each_session_gap_form(value: str, state: str, frames: int | None) -> None:
    gap = read_session_gap(value)
    assert gap.state == state
    assert gap.frames_cut == frames
    assert gap.text  # kept, never dropped


def test_a_control_character_in_a_session_gap_is_escaped() -> None:
    gap = read_session_gap("not determined (query\x1b[31m failed)")
    assert gap.state == SESSION_GAP_NOT_DETERMINED
    assert "\x1b" not in gap.reason and "\x1b" not in gap.text


def test_a_non_string_session_gap_is_unrecognised_not_a_crash() -> None:
    assert read_session_gap(None).state == SESSION_GAP_UNRECOGNISED
    assert read_session_gap(11400).state == SESSION_GAP_UNRECOGNISED
