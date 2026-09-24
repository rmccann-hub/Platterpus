"""The album loudness rows are labelled by what they were measured over.

cyanrip's "Album integrated loudness" and its three sibling rows cover whatever
audio the rip read. The fork found one over 40% of a single track, on a rip
interrupted in track 1 (round 26 lap 4, `cancel-me.log:75`). The subjects here are
the three real logs of the 2026-09-24 run that show all three states, so what is
tested is the line cyanrip actually wrote.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from platterpus import album_loudness
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog
from platterpus.rip_report import build_report
from platterpus.ui.rip_progress import loudness_summary_line

_ARTIFACTS: Path = (
    Path(__file__).resolve().parents[1] / "docs/handshake/artifactsround26"
)


def _parse(name: str) -> RipLog:
    return parse_cyanrip_log((_ARTIFACTS / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("log_name", "state", "finished", "total"),
    [
        # Interrupted in track 1: the fork's case.
        ("round26cancelme.log", album_loudness.PART_OF_DISC, 0, 14),
        # A clean `-l 1,2` rip: two of fourteen tracks.
        ("round26aftercancel.log", album_loudness.PART_OF_DISC, 2, 14),
        # The whole disc: the one case the rows are the album's.
        ("round26securereread.log", album_loudness.WHOLE_DISC, 14, 14),
    ],
)
def test_coverage_is_read_off_the_logs_own_footer(
    log_name: str, state: str, finished: int, total: int
) -> None:
    parsed = _parse(log_name)
    assert parsed.album_loudness, "floor: the log must carry album loudness rows"
    covers = album_loudness.coverage(parsed)
    assert covers is not None
    assert covers["state"] == state
    assert covers["tracks_finished"] == finished
    assert covers["disc_tracks"] == total


def test_an_interrupted_rip_is_not_called_album_loudness_on_screen() -> None:
    """The results-pane line, which is the claim a user reads."""
    line = loudness_summary_line(_parse("round26cancelme.log"))
    assert "-14.4 LUFS integrated" in line, line
    assert line.startswith(
        "Loudness of what was read (0 of 14 tracks finished, then stopped at track "
        "1, mid-read), not the whole album: "
    ), line
    assert "Album loudness" not in line


def test_a_whole_disc_rip_keeps_the_album_label() -> None:
    """The non-triviality half: the relabel must not fire on the album itself."""
    line = loudness_summary_line(_parse("round26securereread.log"))
    assert line.startswith("Album loudness: -13.9 LUFS integrated"), line


def test_the_report_records_what_the_figures_cover() -> None:
    report = build_report(_parse("round26aftercancel.log"))
    assert report["album_loudness"] is not None
    assert report["album_loudness_covers"] == {
        "state": album_loudness.PART_OF_DISC,
        "tracks_finished": 2,
        "disc_tracks": 14,
        "interrupted_at": None,
    }


def test_no_footer_is_not_determined_and_keeps_the_rippers_name() -> None:
    """Tri-state: a log that does not say how much was read is not called partial."""
    parsed = RipLog(album_loudness={"integrated_lufs": "-9.0"})
    covers = album_loudness.coverage(parsed)
    assert covers is not None and covers["state"] == album_loudness.NOT_DETERMINED
    assert album_loudness.label(covers) == album_loudness.ALBUM_LABEL


def test_no_loudness_rows_means_no_coverage_claim() -> None:
    assert album_loudness.coverage(RipLog()) is None
    assert build_report(RipLog())["album_loudness_covers"] is None
