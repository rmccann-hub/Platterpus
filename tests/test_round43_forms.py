"""Two `.36` forms from the fork's round 43 lap 1, read before any build prints them.

S13 proposes, for a pregap cyanrip cannot decide, a cue line in the track's block
before `INDEX 00`: ``    REM PREGAP_UNDECIDED "94 or 95 frames"``. S14 proposes
six `Preemphasis:` forms that say what the TOC and the sub-code each said. Both
are claimed to need no reader of ours; these tests are the check, so our lap 2
answers from the code rather than from the claim.
"""

from __future__ import annotations

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
