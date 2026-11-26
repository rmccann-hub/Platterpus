"""Two `.36` forms from the fork's round 43 lap 1, read before any build prints them.

S13 proposes, for a pregap cyanrip cannot decide, a cue line in the track's block
before `INDEX 00`: ``    REM PREGAP_UNDECIDED "94 or 95 frames"``. S14 proposes
six `Preemphasis:` forms that say what the TOC and the sub-code each said. Both
are claimed to need no reader of ours; these tests are the check, so our lap 2
answers from the code rather than from the claim.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from platterpus.cue_validate import parse_cue
from platterpus.parsers.cyanrip_preemphasis import preemphasis_text

_CUE = """REM GENRE Rock
PERFORMER "Artist"
TITLE "Album"
FILE "08 - Eight.flac" WAVE
  TRACK 08 AUDIO
    TITLE "Eight"
    INDEX 01 00:00:00
FILE "09 - Nine.flac" WAVE
  TRACK 09 AUDIO
    TITLE "Nine"
    REM PREGAP_UNDECIDED "94 or 95 frames"
    INDEX 00 03:58:21
    INDEX 01 00:00:00
"""


def test_the_undecided_pregap_rem_is_kept_as_track_metadata() -> None:
    """S13: kept as the track's own metadata, its INDEX 00 read as before."""
    sheet = parse_cue(_CUE)
    kept = [m for m in sheet.metadata if m.field_name == "REM PREGAP_UNDECIDED"]
    assert len(kept) == 1
    assert kept[0].value == "94 or 95 frames"
    assert kept[0].track_number == 9
    nine = [t for t in sheet.tracks if t.number == 9]
    assert nine and nine[0].index00 == "03:58:21"


@pytest.mark.parametrize(
    ("form", "emphasised"),
    [
        ("present (TOC and subcode)", True),
        ("present (TOC; subcode says none)", True),
        ("present (subcode; TOC says none)", True),
        ("present (TOC; subcode not read)", True),
        ("none detected", False),
        ("none detected (TOC; subcode not read)", False),
        ("present (TOC and subcode) (deemphasis applied)", True),
        ("present (subcode; TOC says none) (deemphasis forced)", True),
    ],
)
def test_each_proposed_preemphasis_form_reads_as_it_should(
    form: str, emphasised: bool
) -> None:
    """S14: the parser's rule, a value that starts `none` is no pre-emphasis
    (`parsers/cyanrip_log.py`), applied to every proposed form."""
    value = preemphasis_text(f"  Preemphasis:   {form}")
    assert value == form
    assert (not value.startswith("none")) is emphasised


# --- `Appended:` in samples (the owner's relay of 2026-11-26, ahead of `.36`) ---

_FIXTURE = (
    Path(__file__).parent / "fixtures" / "cyanrip_fork_golden_reference_r36l7.log"
)


def _with_appended(row: str) -> str:
    """The fixture with ``row`` after the LAST track's `Preemphasis:` row."""
    lines = _FIXTURE.read_text(encoding="utf-8").splitlines()
    anchor = "  Preemphasis:   none detected"
    last = max(i for i, line in enumerate(lines) if line == anchor)
    return "\n".join([*lines[: last + 1], row, *lines[last + 1 :]]) + "\n"


@pytest.mark.parametrize(
    ("row", "frames", "samples", "shown"),
    [
        # Today's form: frames the offset REACHED; the silence is not stated.
        (
            "    Appended:    2 frames of silence",
            2,
            None,
            "(the offset reached 2 frame(s) past the disc's last audio sector)",
        ),
        # `.36`'s form, word for word from the fork's round 43 lap 1 S60.
        (
            "    Appended:    667 samples of silence (2 frames past the last audio "
            "sector, not read)",
            2,
            667,
            "(667 sample(s) of silence; the offset reached 2 frame(s)",
        ),
        ("    Appended:    1 sample of silence", None, 1, "(1 sample(s) of silence)"),
    ],
)
def test_appended_silence_reads_in_frames_and_in_samples(
    row: str, frames: int | None, samples: int | None, shown: str
) -> None:
    from platterpus.eac_log_export import _appended_silence_line
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log
    from platterpus.rip_report import build_report

    log = parse_cyanrip_log(_with_appended(row))
    last = log.tracks[-1]
    assert (last.appended_silence_frames, last.appended_silence_samples) == (
        frames,
        samples,
    )
    assert all(t.appended_silence_frames is None for t in log.tracks[:-1])
    report = build_report(log)
    assert report["tracks"][-1]["appended_silence_samples"] == samples
    assert report["tracks"][-1]["appended_silence_frames"] == frames
    text = "\n".join(_appended_silence_line(log))
    assert shown in text, text
    assert "only the silent samples are not disc audio" in text


def test_prepended_silence_is_read_today_and_in_36_s_form() -> None:
    """`.35` already prints `Prepended:` for a negative offset
    (`cyanrip@52bde2d:src/cyanrip_log.c:586`); it was not read until
    2026-11-26. `.36` gives samples with the frames before LSN 0."""
    from platterpus.eac_log_export import _appended_silence_line
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    lines = _FIXTURE.read_text(encoding="utf-8").splitlines()
    first = lines.index("  Preemphasis:   none detected")
    for row, frames, samples in (
        ("    Prepended:   2 frames of silence", 2, None),
        (
            "    Prepended:   667 samples of silence (2 frames before LSN 0, not read)",
            2,
            667,
        ),
    ):
        text = "\n".join([*lines[: first + 1], row, *lines[first + 1 :]]) + "\n"
        log = parse_cyanrip_log(text)
        one = log.tracks[0]
        assert (one.prepended_silence_frames, one.prepended_silence_samples) == (
            frames,
            samples,
        )
        assert any(
            line.startswith("Prepended silence") for line in _appended_silence_line(log)
        )


def test_app_log_times_carry_their_utc_offset() -> None:
    """TASKS R168: the fork had to infer the owner's log was UTC-5 (its round 43
    lap 1 S37). The offset follows the milliseconds with no space."""
    import logging
    import re

    from platterpus.logging_setup import _LOG_FORMAT, _OffsetFormatter

    record = logging.LogRecord("x", logging.INFO, __file__, 1, "hello", None, None)
    text = _OffsetFormatter(_LOG_FORMAT).format(record)
    assert re.match(
        r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3}[+-]\d{4} INFO x: hello$", text
    ), text
