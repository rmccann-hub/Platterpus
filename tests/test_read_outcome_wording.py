"""`Track N read with no error reported.`, read before the fork prints it.

The fork's round 36 lap 8 S26 proposes renaming `Track N read successfully!`
(printed at `cyanrip@ca0f097:src/cyanrip_main.c:1966`) to `Track N read with no
error reported.`: the line reports the READ alone (no drive error, no paranoia
skip, no `-Z` repeat limit) and is printed before AccurateRip is looked up, and on
their damaged-disc run it printed over four tracks AccurateRip then rejected.
The rename ships only after a release of ours reads both wordings (round 20's
order: no build of theirs may print a line this parser cannot read).

**What would have gone wrong.** Five call sites asked
`what.endswith("successfully!")`. The new wording ends in `reported.`, so every
clean track of a `.28` log would have been filed as `ripped with errors`, and the
live row and the rip worker would have shown every track as read with errors.
They now ask one predicate, `cyanrip_log.read_reported_no_error`. The old wording
stays read for good: every log already filed carries it.

**Where the lines come from.** The `.27` golden reference
(`cyanrip_fork_golden_reference_r36l8.log`, `cyanrip@22af58e:docs/
golden-reference.log`) still prints the old wording; the new one is that log with
its three outcome lines replaced by the wording the lap proposes, character for
character.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.parsers import cyanrip_log
from platterpus.parsers.cyanrip_log import (
    DATA_TRACK_COPIED,
    DATA_TRACK_COPIED_WITH_ERRORS,
    finished_track,
    parse_cyanrip_log,
    read_reported_no_error,
)
from platterpus.rip_report import build_report

_REPO = Path(__file__).resolve().parent.parent
_GOLDEN = _REPO / "tests" / "fixtures" / "cyanrip_fork_golden_reference_r36l8.log"
_GOLDEN_SHA256 = "13e1288cc4447c2ee2d134865b4fa30a1c998150766ddda62a8cef0b9d75c2d1"

#: The two wordings, as the fork's source prints the old one and their lap 8 S26
#: proposes the new one (`%i` the track number).
_OLD = "Track {n} read successfully!"
_NEW = "Track {n} read with no error reported."
_ERRORS = "Track {n} read with errors."


def _golden() -> str:
    text = _GOLDEN.read_text(encoding="utf-8")
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == _GOLDEN_SHA256
    return text


def _with_outcome(wording: str) -> str:
    """The golden reference with every track's outcome line in ``wording``."""
    text = _golden()
    for n in (1, 2, 3):
        old = _OLD.format(n=n) + "\n"
        assert text.count(old) == 1  # floor: the anchor is there, once per track
        text = text.replace(old, wording.format(n=n) + "\n")
    return text


# --- the parse ------------------------------------------------------------------


@pytest.mark.parametrize("wording", [_OLD, _NEW], ids=["old", "renamed"])
def test_both_wordings_parse_to_a_clean_read(wording: str) -> None:
    log = parse_cyanrip_log(_with_outcome(wording))
    assert [t.number for t in log.tracks] == [1, 2, 3]  # floor: the whole log
    assert [t.status for t in log.tracks] == ["ripped successfully"] * 3


def test_the_two_wordings_parse_to_the_same_report() -> None:
    """The rename changes the words and nothing a reader of the report sees."""
    old = build_report(parse_cyanrip_log(_with_outcome(_OLD)))
    new = build_report(parse_cyanrip_log(_with_outcome(_NEW)))
    assert len(old["tracks"]) == 3
    assert old["tracks"] == new["tracks"]
    assert old["verdict"] == new["verdict"]


def test_the_errors_wording_is_still_a_read_with_errors() -> None:
    """Guards the predicate the other way: it must not call everything clean."""
    log = parse_cyanrip_log(_with_outcome(_ERRORS))
    assert [t.status for t in log.tracks] == ["ripped with errors"] * 3


# --- the live reader ------------------------------------------------------------


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Track 4 read successfully!", (4, True)),
        ("Track 4 read with no error reported.", (4, True)),
        ("Track 4 read with errors.", (4, False)),
        ("Track 4 ripped and encoded successfully!", (4, True)),  # <= .13
        ("Track 4 ripped and encoded with errors.", (4, False)),
        ("Track 4 ripped successfully!", (4, True)),  # a data track's copy
        ("Track 4 ripped with errors.", (4, False)),
        ("Track 4 is data:", None),
        # Near misses: no outcome, so no row turns "Done".
        ("Track 4 read with no error reported", None),
        ("Track 4 read with no errors reported.", None),
    ],
)
def test_the_live_reader_reads_both_wordings(
    line: str, expected: tuple[int, bool] | None
) -> None:
    assert finished_track(line) == expected


def test_a_data_track_outcome_in_the_new_wording_is_its_copy() -> None:
    """`read` wording naming the open data track is that track's outcome, as the
    old wording is (see `_DATA_TRACK_OUTCOME`), never a second track."""
    for wording, status in (
        (_NEW, DATA_TRACK_COPIED),
        (_ERRORS, DATA_TRACK_COPIED_WITH_ERRORS),
    ):
        log = parse_cyanrip_log(
            "cyanrip 0.9.4\nTrack 3 is data:\n" + wording.format(n=3) + "\n"
        )
        assert [t.number for t in log.tracks] == [3]
        assert log.tracks[0].status == status


# --- one predicate, every caller -------------------------------------------------


def test_the_predicate_knows_exactly_the_clean_wordings() -> None:
    match = cyanrip_log._TRACK_START.match(_NEW.format(n=1))
    assert match is not None
    assert read_reported_no_error(match.group("what"))
    assert not read_reported_no_error("read with errors.")
    assert not read_reported_no_error("is data:")
    assert not read_reported_no_error("")
    # Every clean wording the pattern can capture is in the set, and nothing else:
    # the set and the pattern describe the same alternatives.
    clean = {
        what
        for what in cyanrip_log._NO_ERROR_REPORTED_OUTCOMES
        if cyanrip_log._TRACK_START.match(f"Track 1 {what}")
        or cyanrip_log._DATA_TRACK_OUTCOME.match(f"Track 1 {what}")
    }
    assert clean == set(cyanrip_log._NO_ERROR_REPORTED_OUTCOMES)
    assert len(clean) == 4


def test_no_code_keys_on_the_wording_but_the_predicate() -> None:
    """The five `endswith("successfully!")` sites are gone, and none is added.

    A sweep of the package for a call that decides an outcome by its suffix: the
    shape the rename would have broken. Floor: the package has modules to sweep.
    """
    sources = sorted((_REPO / "src" / "platterpus").rglob("*.py"))
    assert len(sources) >= 100
    shape = re.compile(r"""\.endswith\(\s*["'](?:successfully!|with errors\.)""")
    offenders = [
        f"{path.relative_to(_REPO)}:{number}"
        for path in sources
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if shape.search(line)
    ]
    assert offenders == []


# --- never raises -----------------------------------------------------------------


@settings(max_examples=150, deadline=None)
@given(
    st.sampled_from([_OLD, _NEW, _ERRORS]),
    st.text(max_size=60).map(lambda s: s.replace("\n", " ").replace("\r", " ")),
)
def test_neither_wording_raises_with_any_tail(wording: str, tail: str) -> None:
    """Both readers, over the wording with anything after it or in place of the
    number."""
    line = wording.format(n=7) + tail
    result = finished_track(line)
    assert result is None or result[0] == 7
    finished_track(wording.format(n=tail))
    parse_cyanrip_log("cyanrip 0.9.4\n" + line + "\n")
