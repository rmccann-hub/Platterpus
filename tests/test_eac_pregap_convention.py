"""What EAC's ``Pre-gap length`` row actually means — derived, not remembered.

This file exists because the convention flipped twice in one day on nothing but
recollection, and the answer was sitting in two committed files the whole time.

The sequence, so the next reader does not repeat it:

1. We stored cyanrip's ``Pregap LSN:`` (a *position*) as a *length* — an 89x
   over-claim on a real track (audit, 2026-07-31). Fixed by subtracting.
2. The fork added ``Pregap length: N frames``. On its reference disc track 1
   reads ``Pregap LSN: 0`` / ``Start LSN: 150`` / ``Pregap length: 300`` — the
   150-frame Red Book lead-in plus a 150-frame declared TOC gap. Subtraction
   gets 150 and is wrong, so we preferred the stated figure.
3. The fork's handshake §H2 argued EAC's row is the *TOC component alone*, so
   300 would be un-EAC-comparable. It was accepted from memory — "EAC reports
   no pre-gap for track 1 on the reference disc" — and step 2 was reverted.
4. That memory was wrong, and it was wrong in a specific, instructive way: it
   was counting ``INDEX 00`` lines in the **cue**, where track 1 *cannot* have
   one (no addressable sector exists before LSN 0). The **log** — a different
   artifact answering a different question — prints a row for track 1. Step 3
   was reverted and step 2 restored.

So the rule below is never restated in prose and asserted; it is **computed
from** ``output_reference/EAC_flac/`` every run. If EAC's convention is not what
we think, these fail, and they fail with the numbers.

The convention, as measured here:

* the fractional field is **hundredths of a second, truncated** — not CD frames
* for track *n* > 1 the value is ``start_sector(n) - absolute(INDEX 00 of n)``
* for track 1 it is the **lead-in plus any declared TOC gap**; on this disc the
  TOC declares none, so the row is the bare 150-frame lead-in, ``0:00:02.00``
* a track with no pre-gap gets **no row at all** — absence is EAC-normal

See also ``docs/testing.md`` §5.u.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from platterpus.eac_log_export import _pregap_line
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import TrackResult

_EAC_DIR = Path(__file__).parents[1] / "output_reference" / "EAC_flac"
_EAC_LOG = _EAC_DIR / "eac_baseline_police_classics.log"
_EAC_CUE = _EAC_DIR / "eac_baseline_police_classics.cue"
_FORK_GOLDEN = Path(__file__).parent / "fixtures" / "cyanrip_fork_golden_reference.log"

# The disc, so a truncated or swapped artifact cannot quietly shrink the sample.
_DISC_TRACKS = 14
_FRAMES_PER_SECOND = 75
_LEAD_IN_FRAMES = 150  # Red Book: LSN -150..-1, two seconds, mandatory.

# EAC's log is UTF-16 with a BOM; the cue it writes beside it is UTF-8. Reading
# either with the other's codec yields mojibake that still *parses*, so the
# encodings are named explicitly rather than sniffed.
_LOG_ENCODING = "utf-16"
_CUE_ENCODING = "utf-8"

_TOC_ROW = re.compile(
    r"^\s*(?P<track>\d{1,3})\s*\|\s*[\d:.]{1,12}\s*\|\s*[\d:.]{1,12}\s*"
    r"\|\s*(?P<start>\d{1,9})\s*\|\s*(?P<end>\d{1,9})\s*$"
)
_TRACK_HEADING = re.compile(r"^Track\s+(?P<track>\d{1,3})$")
_PREGAP_ROW = re.compile(
    r"^Pre-gap length\s+(?P<h>\d{1,3}):(?P<m>\d{2}):(?P<s>\d{2})\.(?P<cs>\d{2})$"
)
_CUE_TRACK = re.compile(r"^TRACK (?P<track>\d{1,3}) AUDIO$")
_CUE_INDEX00 = re.compile(r"^INDEX 00 (?P<mm>\d{2}):(?P<ss>\d{2}):(?P<ff>\d{2})$")


def _msf_to_frames(minutes: str, seconds: str, frames: str) -> int:
    """CD ``MM:SS:FF`` -> frames. Here ``FF`` really *is* frames (0-74)."""
    return (int(minutes) * 60 + int(seconds)) * _FRAMES_PER_SECOND + int(frames)


def _eac_toc() -> dict[int, int]:
    """Track number -> start sector, from EAC's own TOC table."""
    text = _EAC_LOG.read_bytes().decode(_LOG_ENCODING)
    return {
        int(m.group("track")): int(m.group("start"))
        for m in (_TOC_ROW.match(line.strip()) for line in text.splitlines())
        if m
    }


def _eac_pregap_rows() -> dict[int, tuple[str, int]]:
    """Track number -> (row text as EAC wrote it, its value in hundredths).

    EAC's log repeats each per-track block twice (once for the extraction, once
    in the summary), so only the first occurrence of each track is taken.
    """
    text = _EAC_LOG.read_bytes().decode(_LOG_ENCODING)
    rows: dict[int, tuple[str, int]] = {}
    current: int | None = None
    for raw in text.splitlines():
        line = raw.strip()
        heading = _TRACK_HEADING.match(line)
        if heading:
            current = int(heading.group("track"))
            continue
        row = _PREGAP_ROW.match(line)
        if row and current is not None and current not in rows:
            hundredths = (
                int(row.group("h")) * 3600
                + int(row.group("m")) * 60
                + int(row.group("s"))
            ) * 100 + int(row.group("cs"))
            rows[current] = (line, hundredths)
    return rows


def _cue_index00_absolute(toc: dict[int, int]) -> dict[int, int]:
    """Track number -> absolute LSN of its ``INDEX 00``.

    EAC's gaps-appended cue writes one ``FILE`` per track and expresses a
    track's ``INDEX 00`` as an offset into the *previous* track's file, so each
    offset is resolved against that file's TOC start sector.
    """
    absolute: dict[int, int] = {}
    pending: int | None = None
    file_index = 0
    for raw in _EAC_CUE.read_text(encoding=_CUE_ENCODING).splitlines():
        line = raw.strip()
        track = _CUE_TRACK.match(line)
        if track:
            pending = int(track.group("track"))
        if line.startswith("FILE "):
            file_index += 1
        index00 = _CUE_INDEX00.match(line)
        if index00 and pending is not None:
            offset = _msf_to_frames(*index00.group("mm", "ss", "ff"))
            absolute[pending] = toc[file_index] + offset
    return absolute


# --- the sample is real and big enough to conclude from ----------------------


def test_the_committed_baseline_is_the_whole_disc() -> None:
    """A floor, because every assertion below is "for each row EAC printed" and
    an empty or truncated artifact would satisfy all of them vacuously."""
    toc = _eac_toc()
    rows = _eac_pregap_rows()
    assert len(toc) == _DISC_TRACKS, f"TOC table parsed {len(toc)} of {_DISC_TRACKS}"
    assert len(rows) >= 10, f"only {len(rows)} pre-gap rows parsed out of EAC's log"
    # At least two distinct values, or "our formula matches" could be one lucky
    # constant rather than a formula.
    assert len({v for _, v in rows.values()}) >= 5
    # THE COMPLEMENT, and it bounds the opposite direction to the line above.
    #
    # `test_tracks_without_a_row_have_no_gap_to_report` asserts only for tracks
    # WITHOUT a pre-gap row: its body opens with `pytest.skip` when `track in
    # rows`. So the number of cases that actually assert is
    # `_DISC_TRACKS - len(rows)` — 4 today — and `len(rows) >= 10` is the WRONG
    # DIRECTION for it. More rows means fewer asserting cases, so a baseline where
    # every track carries a row satisfies that floor and starves this one to
    # nothing. Measured: rows=10 -> 4 assert; rows=14 -> 13 generated, 13 skipped,
    # `13 skipped`, exit 0, green.
    #
    # Reachable without editing any test: swap the committed reference for a disc
    # whose every track has a pre-gap. On such a swap every other test in this
    # module fails loudly (the TOC equality, the >= 10, the >= 5 distinct values) —
    # and that one would go quietly to "13 skipped". This makes it say so too.
    #
    # Its docstring already claimed the number: "Four tracks of this disc exercise
    # it." A comment where a check belongs is not a check (2026-08-20 audit).
    asserting = _DISC_TRACKS - len(rows)
    assert asserting >= 3, (
        f"only {asserting} track(s) lack a pre-gap row, so "
        "test_tracks_without_a_row_have_no_gap_to_report skips nearly every case "
        "and proves nothing while reporting green. If the baseline was "
        "deliberately swapped, re-measure and lower this floor on purpose."
    )


# --- the finding that overturned §H2 -----------------------------------------


def test_eac_prints_a_pregap_row_for_track_one() -> None:
    """The whole reason this file exists.

    Track 1 has no ``INDEX 00`` and can never have one, yet EAC prints a row for
    it. Anyone concluding "EAC reports no track-1 pre-gap" has read the cue and
    described the log.
    """
    rows = _eac_pregap_rows()
    assert 1 in rows, "EAC's log DOES carry a Pre-gap row for track 1"
    line, hundredths = rows[1]
    assert line == "Pre-gap length  0:00:02.00"
    assert hundredths == 200
    # 2.00 s is exactly the mandatory lead-in, on a disc whose TOC declares no
    # track-1 gap — so EAC's track-1 row is lead-in + declared gap, and a fork
    # that states 150 + 150 = 300 is stating EAC's number, not a rival one.
    assert hundredths * _FRAMES_PER_SECOND // 100 == _LEAD_IN_FRAMES


def test_the_cue_and_the_log_disagree_on_track_one_by_design() -> None:
    """Pins the *specific* trap: the two artifacts genuinely differ, so citing
    one as evidence about the other is always a mistake, not just this once."""
    toc = _eac_toc()
    cue_tracks = set(_cue_index00_absolute(toc))
    log_tracks = set(_eac_pregap_rows())
    assert 1 not in cue_tracks, "no addressable sector exists before LSN 0"
    assert 1 in log_tracks
    assert log_tracks - cue_tracks == {1}, "track 1 is the *only* difference"
    assert cue_tracks < log_tracks


# --- the formula, computed against every row EAC printed ---------------------


def test_every_pregap_row_equals_start_minus_index00_in_truncated_hundredths() -> None:
    """The convention itself, checked on all 10 rows rather than asserted.

    Truncation vs rounding is decided here too: they differ on exactly one row
    (track 4, 158 frames = 2.1067 s -> ``.10`` truncated, ``.11`` rounded), and
    EAC wrote ``.10``.
    """
    toc = _eac_toc()
    index00 = _cue_index00_absolute(toc)
    rows = _eac_pregap_rows()

    checked = 0
    rounding_would_differ = 0
    for track, (line, hundredths) in sorted(rows.items()):
        if track == 1:
            frames = _LEAD_IN_FRAMES
        else:
            assert track in index00, f"track {track} has a row but no INDEX 00"
            frames = toc[track] - index00[track]
        assert frames > 0, f"track {track}: non-positive gap {frames}"
        truncated = frames * 100 // _FRAMES_PER_SECOND
        assert truncated == hundredths, (
            f"track {track}: EAC wrote {line!r} ({hundredths} cs) but "
            f"{frames} frames truncates to {truncated} cs"
        )
        if round(frames * 100 / _FRAMES_PER_SECOND) != truncated:
            rounding_would_differ += 1
        checked += 1

    assert checked >= 10
    assert rounding_would_differ >= 1, (
        "no row distinguishes truncation from rounding, so this run did not "
        "actually decide the question — the baseline may have been replaced"
    )


def test_our_renderer_reproduces_every_real_eac_row_byte_for_byte() -> None:
    """End-to-end: feed our renderer the frame count and demand EAC's own text.

    This is the assertion that would have caught a unit error, an off-by-one, or
    a rounding mode — it compares against strings a real EAC wrote, not against
    our own formatter's idea of itself.
    """
    toc = _eac_toc()
    index00 = _cue_index00_absolute(toc)
    rows = _eac_pregap_rows()

    checked = 0
    for track, (line, _) in sorted(rows.items()):
        frames = _LEAD_IN_FRAMES if track == 1 else toc[track] - index00[track]
        rendered = _pregap_line(TrackResult(number=track, pregap_sectors=frames))
        assert rendered[0].strip() == line, (
            f"track {track}: we render {rendered[0].strip()!r}, EAC wrote {line!r}"
        )
        checked += 1
    assert checked >= 10


def test_the_omission_floor_rejects_a_baseline_that_would_starve_the_sweep() -> None:
    """Prove the floor above can FAIL, since today's artifact satisfies it.

    A floor whose data already passes cannot be revert-proven: deleting the
    assertion breaks nothing *now*, which is exactly what makes this class of
    guard rot unnoticed. So instead of reverting the fix, this drives the floor's
    predicate with the artifact that would starve the sweep — an EAC baseline
    where **every** track carries a pre-gap row.

    Under such a baseline
    `test_tracks_without_a_row_have_no_gap_to_report` generates 13 cases and skips
    all 13, reporting `13 skipped` and exit 0 — green, having asserted nothing.
    Note the old `len(rows) >= 10` floor is *satisfied* by that same baseline,
    which is the point: it bounds rows from below, and this test needs them
    bounded from above.
    """
    every_track_has_a_row = {n: ("row", 100) for n in range(1, _DISC_TRACKS + 1)}
    starved = _DISC_TRACKS - len(every_track_has_a_row)
    assert starved == 0, "the starving case should leave no track asserting"
    assert not starved >= 3, (
        "the omission floor would ACCEPT a baseline in which every track has a "
        "pre-gap row — so it does not actually guard the sweep it was written for"
    )
    # And the converse, so this test is not satisfied by the predicate always
    # being false: today's real artifact must clear the floor.
    real = _DISC_TRACKS - len(_eac_pregap_rows())
    assert real >= 3, (
        f"today's committed baseline leaves only {real} asserting track(s); the "
        "floor in test_the_committed_baseline_is_the_whole_disc should already "
        "have failed, so one of the two is wrong"
    )


@pytest.mark.parametrize("track", sorted(set(range(1, _DISC_TRACKS + 1)) - {1}))
def test_tracks_without_a_row_have_no_gap_to_report(track: int) -> None:
    """The other half of the convention: EAC omits the row rather than printing
    a zero, and so must we. Four tracks of this disc exercise it."""
    rows = _eac_pregap_rows()
    if track in rows:
        pytest.skip(f"track {track} has a pre-gap; covered by the formula test")
    assert _pregap_line(TrackResult(number=track, pregap_sectors=0)) == []
    assert _pregap_line(TrackResult(number=track, pregap_sectors=None)) == []


# --- what the parser must therefore do with the fork's log -------------------


def test_the_parser_keeps_the_stated_length_for_the_eac_row() -> None:
    """The restored behaviour, pinned to the convention proven above.

    Reverting to the derived value makes this fail with 150 — which is the point:
    the fork's 300 is what EAC would print for that disc, and the subtraction is
    not.
    """
    tracks = {t.number: t for t in parse_cyanrip_log(_FORK_GOLDEN.read_text()).tracks}
    t1 = tracks[1]
    assert t1.pregap_start_lsn == 0
    assert t1.start_sector == _LEAD_IN_FRAMES
    assert t1.pregap_length_frames == 300, "the fork states lead-in + declared gap"
    assert t1.pregap_sectors == 300, (
        "the EAC row must carry the stated figure; subtracting gets 150 and EAC "
        "would print 0:00:04.00 for this disc (see the track-1 test above)"
    )
    assert _pregap_line(t1)[0].strip() == "Pre-gap length  0:00:04.00"


def test_the_two_methods_agree_everywhere_except_track_one() -> None:
    """So preferring the stated figure cannot be masking a broader disagreement:
    for every later track the fork's number and our subtraction coincide."""
    parsed = parse_cyanrip_log(_FORK_GOLDEN.read_text())
    tracks = [t for t in parsed.tracks if t.number > 1]
    compared = 0
    for track in tracks:
        if track.pregap_length_frames is None or track.pregap_start_lsn is None:
            continue
        assert track.start_sector is not None
        derived = track.start_sector - track.pregap_start_lsn
        assert derived == track.pregap_length_frames, (
            f"track {track.number}: fork states {track.pregap_length_frames}, "
            f"subtraction gives {derived} — the fixture or the fork has changed"
        )
        compared += 1
    assert compared >= 1, "the golden fixture no longer exercises the agreeing case"
