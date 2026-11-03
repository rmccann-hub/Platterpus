"""A first pass that hit the re-read limit keeps that fact after a securing pass (R114).

Finding 2 of the 2026-11-03 Full run, section N: track 3's first pass read four
different checksums and stopped at the repeat limit (``did NOT converge after 5
reads (repeat limit hit)``), the securing pass re-ripped it and converged after 3,
and the merge replaced the first pass's verdict with the securing pass's. The
report's ``heavy_reread`` then named track 5 only, and the EAC-layout log said
``confirmed across 3 secure re-reads``.

The run's own two logs are the input: the album pass's
(``round37full1103asecurereread.log``) and the securing pass's
(``round37full1103asecurerereadsecuringpass.txt``), filed on ``evidence`` at
``1bb98a2c`` and copied byte for byte by ``scripts/evidence_fixtures.py``. The
merge is driven the way the window drives it, through
``RipMixin._apply_auto_fix_results`` with the worker's record of that rip
(``read_speed.retried_tracks`` in its report).
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest
from evidence_paths import evidence

from platterpus.eac_log_export import render_eac_style_log
from platterpus.first_pass_reread import (
    FirstPassReread,
    clause,
    did_not_converge,
    sentences,
    snapshot,
)
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog, TrackResult, tracks_needing_heavy_reread
from platterpus.reread_limit import RereadLimitStop
from platterpus.rip_report import build_report
from platterpus.ui.main_window_rip import RipMixin, _merge_shipped_track

_RUN = "docs/handshake/artifactsround37/round37full1103a"

#: The worker's record of what it re-ripped, from that rip's report
#: (`read_speed.retried_tracks`), verbatim.
_RETRIED: list[dict[str, object]] = [
    {
        "track": 3,
        "trigger": "instability",
        "reripped_z": 2,
        "converged": True,
        "replaced": True,
        "replaced_because": "converged",
        "kept_read": "securing_pass",
        "verified_read_chase": None,
        "pass_unfinished": False,
        "not_replaced_because": None,
    }
]


def _parsed(name: str) -> RipLog:
    path = evidence(f"{_RUN}{name}")
    return parse_cyanrip_log(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def merged() -> RipLog:
    """The album pass with the securing pass's track 3 merged in, as the window does."""
    album = _parsed("securereread.log")
    securing = _parsed("securerereadsecuringpass.txt")
    shipped = {t.number: t for t in securing.tracks}
    assert list(shipped) == [3]  # the securing pass ripped track 3 alone
    window = SimpleNamespace(
        _last_retried_tracks=_RETRIED, _last_swapped_tracks=shipped
    )
    out = RipMixin._apply_auto_fix_results(window, album)
    assert isinstance(out, RipLog)
    return out


def _track(log: RipLog, number: int) -> TrackResult:
    return next(t for t in log.tracks if t.number == number)


def test_the_album_pass_is_what_the_finding_says() -> None:
    """Non-triviality: the input has the non-converged first pass the fix keeps."""
    first = _track(_parsed("securereread.log"), 3)
    assert first.secure_rerip_converged is False
    assert first.rip_count == 5
    assert tracks_needing_heavy_reread(_parsed("securereread.log")) == [3, 5]


def test_the_shipped_read_stays_the_shipped_reads(merged: RipLog) -> None:
    track = _track(merged, 3)
    assert track.secure_rerip_converged is True
    assert track.rip_count == 3
    assert track.secure_rerip_limit_stop is None


def test_the_first_pass_verdict_is_kept_in_its_own_slot(merged: RipLog) -> None:
    first = _track(merged, 3).first_pass_reread
    assert isinstance(first, FirstPassReread)
    assert first.converged is False
    assert first.rip_count == 5
    assert first.agreement is not None and first.agreement.most_reads_agreed == 2
    assert first.limit_stop is not None and first.limit_stop.kind == "repeat_limit"
    # Tracks nothing replaced carry no snapshot.
    assert _track(merged, 5).first_pass_reread is None


def test_heavy_reread_names_the_track_whose_first_pass_did_not_converge(
    merged: RipLog,
) -> None:
    assert tracks_needing_heavy_reread(merged) == [3, 5]
    report = build_report(merged)
    issue = next(i for i in report["issues"] if i["code"] == "heavy_reread")
    assert issue["message"].startswith("track(s) 3, 5 needed"), issue["message"]
    assert (
        "track 3: the first pass did not converge after 5 reads (repeat limit hit; "
        "at most 2 of 5 reads agreed); the read that replaced it converged after "
        "3 reads"
    ) in issue["message"], issue["message"]


def test_the_report_carries_both_passes(merged: RipLog) -> None:
    row = next(t for t in build_report(merged)["tracks"] if t["number"] == 3)
    assert row["rip_count"] == 3
    assert row["secure_rerip_converged"] is True
    assert row["first_pass_reread"] == {
        "rip_count": 5,
        "secure_rerip_converged": False,
        "most_reads_agreed": 2,
        "most_reads_agreed_exact": True,
        "secure_rerip_kept_read": {
            "crc": "59D352DD",
            "reads": 2,
            "accuraterip_confidence": 200,
            "last_read_crc": None,
        },
        "secure_rerip_limit_stop": {
            "stopped_by": "repeat_limit",
            "time_limit_seconds": None,
            "repeat_limit_reads": 5,
            "reads": 5,
        },
    }
    other = next(t for t in build_report(merged)["tracks"] if t["number"] == 1)
    assert other["first_pass_reread"] is None


def test_the_eac_layout_line_states_the_first_pass(merged: RipLog) -> None:
    text = render_eac_style_log(merged)
    line = next(
        row for row in text.splitlines() if row.startswith("     Copy CRC 59D352DD")
    )
    assert line == (
        "     Copy CRC 59D352DD  (Test and Copy CRC identical — confirmed across 3 "
        "secure re-reads; the first pass did not converge after 5 reads (repeat "
        "limit hit; at most 2 of 5 reads agreed))"
    ), line
    # Track 1 converged on its first pass and was never replaced: unchanged.
    assert (
        "     Copy CRC B0D122E7  (Test and Copy CRC identical — confirmed across 3 "
        "secure re-reads)"
    ) in text.splitlines()


def test_a_second_merge_keeps_the_album_pass_not_the_securing_pass() -> None:
    """A snapshot already on the track wins, so a later merge cannot overwrite it."""
    album = TrackResult(3, copy_crc="AA", rip_count=5, secure_rerip_converged=False)
    once = _merge_shipped_track(
        album, TrackResult(3, copy_crc="AA", rip_count=3), {3: True}
    )
    twice = _merge_shipped_track(
        once, TrackResult(3, copy_crc="AA", rip_count=4), {3: True}
    )
    assert twice.first_pass_reread == once.first_pass_reread
    assert twice.first_pass_reread is not None
    assert twice.first_pass_reread.rip_count == 5


def test_our_time_limit_is_never_worded_as_reads_that_disagreed() -> None:
    track = replace(
        TrackResult(4, rip_count=3, secure_rerip_converged=True),
        first_pass_reread=FirstPassReread(
            rip_count=2,
            converged=False,
            limit_stop=RereadLimitStop(kind="time_limit", time_limit_seconds=600),
        ),
    )
    said = clause(track)
    assert said == (
        "the first pass did not converge after 2 reads (stopped at our time limit "
        "of 600 s)"
    )
    assert sentences(RipLog(tracks=(track,))) == [
        f"track 4: {said}; the read that replaced it converged after 3 reads"
    ]


def test_nothing_is_said_without_a_measured_non_convergence() -> None:
    """No record, a converged first pass, and an empty one each say nothing.

    A plain loop over a literal list rather than a parametrize: the dynamic-sweep
    guard reads a constructor call in a parametrize list as a computed population.
    """
    cases: list[FirstPassReread | None] = [
        None,
        FirstPassReread(rip_count=3, converged=True),
        FirstPassReread(),
    ]
    for first in cases:
        track = TrackResult(2, rip_count=3, first_pass_reread=first)
        assert not did_not_converge(track), first
        assert clause(track) == "", first
        assert sentences(RipLog(tracks=(track,))) == [], first


def test_snapshot_of_a_track_never_re_read_is_none() -> None:
    assert snapshot(TrackResult(1, copy_crc="AA")) is None
    assert snapshot(object()) is None
