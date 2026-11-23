"""A CTDB-only disagreement is shown as a note, never as WRONG (0.7.119).

**The decision.** AccurateRip is the one source of "WRONG"
(``verdict.track_accuraterip_contradiction``; every surface that says WRONG asks
it, ``tests/test_wrong_track_on_every_surface.py``). CTDB answers per track too,
and before this change a track CTDB *differs* on, or agrees with only a
*minority* on (``outvoted``), showed the ripper's clean "ripped successfully" in
the results table with nothing beside it: the disagreement reached only the
Details tab's CTDB sentence and the report. Now the track's Status cell and
tooltip, and the reconciled verdict line under the banner, carry an ``ⓘ`` note
naming the track and saying that AccurateRip is the verdict, all through one
predicate (``ctdb_disagreement.ctdb_disagreements``).

**Where the note lives since R181** (UX review of 0.7.127, V2): the note used to
be its own line under the status line, and the Status cell was in the rip pane's
results table. The one track table's Status cell now carries it (the pane hands
the table its cells, ``RipProgress.track_results``), and the note is part of the
one reconciled verdict line, word for word. These tests drive the pane with the
real F1 log and assert the note reaches that line: R181's own check.

The rip log is the owner's 2026-11-03 Full run, section F (the evidence fixture
for ``round37full1103awholedisc.log``): track 5 matched AccurateRip on frame 450
only, which AccurateRip calls WRONG. The relation test uses the same log with
every track made AccurateRip-verified, so the only disagreement is CTDB's, and
asserts it the way a user meets it: every surface shows the note on the tracks
CTDB names, and no surface says WRONG.
"""

from __future__ import annotations

import re
from dataclasses import replace

import pytest
from evidence_paths import evidence
from PySide6.QtWidgets import QApplication

from platterpus.ctdb.matching import CtdbTrackResult, TrackVerdict
from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
from platterpus.ctdb_disagreement import (
    CTDB_DISAGREES_DIFFERS,
    CTDB_DISAGREES_OUTVOTED,
    NOTE_MARKER,
    ctdb_disagreements,
    ctdb_note_sentence,
    track_ctdb_disagreement,
)
from platterpus.eac_log_export import (
    CONTRADICTED_VERDICT,
    DISC_HAD_ERRORS,
    render_eac_style_log,
)
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog
from platterpus.rip_health import effective_health_status
from platterpus.ui.disc_info_panel import DiscInfoPanel
from platterpus.ui.main_window_helpers import fidelity_summary
from platterpus.ui.rip_progress import RipProgress

_F1_LOG: str = "docs/handshake/artifactsround37/round37full1103awholedisc.log"

#: The tracks the relation test's CTDB answer questions: 2 differs, 9 outvoted.
_CTDB_QUESTIONED: dict[int, str] = {
    2: CTDB_DISAGREES_DIFFERS,
    9: CTDB_DISAGREES_OUTVOTED,
}


def _f1_log() -> RipLog:
    return parse_cyanrip_log(evidence(_F1_LOG).read_text(encoding="utf-8"))


def _all_verified(rip_log: RipLog) -> RipLog:
    """The F1 log with every track carrying track 1's exact AccurateRip match."""
    one = next(t for t in rip_log.tracks if t.number == 1)
    return replace(
        rip_log,
        tracks=tuple(
            replace(
                t,
                accuraterip_v1=one.accuraterip_v1,
                accuraterip_v2=one.accuraterip_v2,
                accuraterip_offset=None,
            )
            for t in rip_log.tracks
        ),
    )


def _row(number: int, kind: str | None) -> CtdbTrackResult:
    """A CTDB per-track row: agrees, differs, or agrees only with a minority."""
    if kind == CTDB_DISAGREES_DIFFERS:
        return CtdbTrackResult(
            number, TrackVerdict.DIFFERS, disagreeing_confidence=1405
        )
    if kind == CTDB_DISAGREES_OUTVOTED:
        return CtdbTrackResult(
            number,
            TrackVerdict.MATCH,
            confidence=1,
            disagreeing_confidence=1405,
            strongest_disagreeing=1405,
        )
    return CtdbTrackResult(number, TrackVerdict.MATCH, confidence=1406)


def _ctdb_result(questioned: dict[int, str], count: int = 14) -> CtdbVerifyResult:
    return CtdbVerifyResult(
        Verdict.NO_MATCH,
        message="no entry matches the whole disc",
        best_confidence=1405,
        total_confidence=1406,
        tracks=tuple(_row(n, questioned.get(n)) for n in range(1, count + 1)),
    )


def _named(text: str) -> set[int]:
    """The track numbers a note sentence names, as a set."""
    found: set[int] = set()
    for group in re.findall(r"tracks? ([\d, ]+) \(", text):
        found |= {int(n) for n in re.findall(r"\d+", group)}
    return found


# --- The predicate ----------------------------------------------------------


#: A spec naming an in-memory ``CtdbTrackResult`` to build, so the parametrize
#: list stays literal (``tests/test_dynamic_sweeps_declare_a_floor.py``).
_RESULT: str = "result"


def _built(spec: object) -> object:
    """The row a spec names: ``(_RESULT, kind)`` builds a result; else as given."""
    if isinstance(spec, tuple) and spec[:1] == (_RESULT,):
        if spec[1] == "not_determined":
            return CtdbTrackResult(1, TrackVerdict.NOT_DETERMINED, reason="no CRCs")
        return _row(1, spec[1])
    return spec


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ((_RESULT, CTDB_DISAGREES_DIFFERS), CTDB_DISAGREES_DIFFERS),
        ((_RESULT, CTDB_DISAGREES_OUTVOTED), CTDB_DISAGREES_OUTVOTED),
        ((_RESULT, None), None),
        ((_RESULT, "not_determined"), None),
        # The report's `ctdb.tracks[]` rows, as `rip_report._ctdb_tracks` writes them.
        ({"track": 1, "verdict": "differs", "outvoted": False}, CTDB_DISAGREES_DIFFERS),
        ({"track": 1, "verdict": "match", "outvoted": True}, CTDB_DISAGREES_OUTVOTED),
        ({"track": 1, "verdict": "match", "outvoted": False}, None),
        ({"track": 1, "verdict": "not_determined", "outvoted": False}, None),
        (None, None),
        ("garbage", None),
    ],
    ids=[
        "differs",
        "outvoted",
        "agrees",
        "not-determined",
        "report-differs",
        "report-outvoted",
        "report-agrees",
        "report-not-determined",
        "none",
        "garbage",
    ],
)
def test_one_track_predicate(row: object, expected: str | None) -> None:
    assert track_ctdb_disagreement(_built(row)) == expected


def test_a_track_accuraterip_calls_wrong_gets_no_ctdb_note() -> None:
    """F1's track 5 is AccurateRip-WRONG: its ⚠ is already there, so CTDB's
    disagreement adds no note to it. Track 2, which AccurateRip verifies, does."""
    rip_log = _f1_log()
    result = _ctdb_result({2: CTDB_DISAGREES_DIFFERS, 5: CTDB_DISAGREES_DIFFERS})
    assert ctdb_disagreements(result.tracks, rip_log) == [(2, CTDB_DISAGREES_DIFFERS)]
    # Floor: without the log, nothing says track 5 is contradicted, so both count.
    assert [n for n, _ in ctdb_disagreements(result.tracks, None)] == [2, 5]
    # The same answer from the report's rows as from the result's.
    report_rows = [
        {"track": r.track, "verdict": r.verdict.value, "outvoted": r.outvoted}
        for r in result.tracks
    ]
    assert ctdb_disagreements(report_rows, rip_log) == ctdb_disagreements(
        result.tracks, rip_log
    )
    assert ctdb_disagreements("not rows", rip_log) == []


def test_the_note_sentence() -> None:
    assert ctdb_note_sentence([]) == ""
    assert ctdb_note_sentence([(3, CTDB_DISAGREES_DIFFERS)]) == (
        "ⓘ CTDB disagrees on track 3 (differs); AccurateRip is the verdict"
    )
    assert ctdb_note_sentence(
        [
            (1, CTDB_DISAGREES_DIFFERS),
            (7, CTDB_DISAGREES_OUTVOTED),
            (4, CTDB_DISAGREES_DIFFERS),
        ]
    ) == (
        "ⓘ CTDB disagrees on tracks 1, 4 (differs) and track 7 (outvoted); "
        "AccurateRip is the verdict"
    )
    assert "WRONG" not in ctdb_note_sentence([(1, CTDB_DISAGREES_DIFFERS)]).upper()


# --- The relation: every surface shows the note, none says WRONG -------------


@pytest.mark.parametrize("ctdb_first", [False, True], ids=["log-first", "ctdb-first"])
def test_every_surface_notes_a_ctdb_only_disagreement_and_none_says_wrong(
    qapp: QApplication, ctdb_first: bool
) -> None:
    rip_log = _all_verified(_f1_log())
    result = _ctdb_result(_CTDB_QUESTIONED)
    # Floor: AccurateRip contradicts nothing, and CTDB questions exactly the two.
    assert dict(ctdb_disagreements(result.tracks, rip_log)) == _CTDB_QUESTIONED

    progress = RipProgress()
    if ctdb_first:
        progress.set_ctdb_result(result)
        progress.set_rip_log(rip_log, disc_track_total=14)
    else:
        progress.set_rip_log(rip_log, disc_track_total=14)
        progress.set_ctdb_result(result)
    status_line = fidelity_summary(rip_log, expected_track_total=14)
    progress.set_status(status_line)

    # The track table's Status cells: the clean word stays ("✓ Done", the one
    # status word the table uses), the note follows it, and the tooltip carries
    # the sentence and the ripper's own word. Never a ⚠ or a "Wrong".
    cells = progress.track_results()
    assert sorted(cells) == list(range(1, 15))
    noted: set[int] = set()
    for number, track_cells in cells.items():
        cell = track_cells.status
        assert not cell.text.startswith("⚠"), cell.text
        assert "wrong" not in (cell.text + cell.tip).lower(), cell.tip
        if NOTE_MARKER in cell.text:
            noted.add(number)
            assert cell.text == "✓ Done · ⓘ CTDB disagrees"
            assert f"track {number} (" in cell.tip
            assert "AccurateRip is the verdict" in cell.tip
            assert "ripped successfully" in cell.tip
        else:
            assert cell.text == "✓ Done"

    # The reconciled verdict line carries the note, with real data (R181).
    note = progress._reconciled_label
    assert not note.isHidden()
    assert note.text().startswith(NOTE_MARKER)
    assert "AccurateRip is the verdict" in note.text()
    assert progress.reconciled_text() == note.text()

    # The surfaces that say WRONG are AccurateRip's, and none of them does.
    banner = progress._verdict_banner.text()
    panel = DiscInfoPanel()
    panel.set_accuraterip_result(rip_log, disc_track_total=14)
    eac = render_eac_style_log(rip_log, disc_track_total=14, ctdb_result=result)
    for surface in (status_line, banner, panel._accuraterip_value.text(), eac):
        assert "WRONG" not in surface, surface
    assert CONTRADICTED_VERDICT not in eac and DISC_HAD_ERRORS not in eac
    assert effective_health_status(rip_log) == "No errors occurred"

    # The relation: the table and the note name the same tracks, CTDB's two.
    assert noted == _named(note.text()) == set(_CTDB_QUESTIONED), (noted, note.text())


def test_the_note_goes_when_ctdb_agrees_and_on_clear(qapp: QApplication) -> None:
    """A CTDB answer that questions nothing shows no note; a new rip clears one."""
    rip_log = _all_verified(_f1_log())
    progress = RipProgress()
    progress.set_rip_log(rip_log, disc_track_total=14)
    progress.set_ctdb_result(_ctdb_result({}))
    assert "CTDB disagrees" not in progress.reconciled_text()
    assert all(
        NOTE_MARKER not in cells.status.text
        for cells in progress.track_results().values()
    )
    progress.set_ctdb_result(_ctdb_result(_CTDB_QUESTIONED))
    assert "CTDB disagrees" in progress.reconciled_text()  # floor: it was shown
    progress.clear()
    assert progress._reconciled_label.isHidden()
    assert progress._reconciled_label.text() == ""
    assert progress.track_results() == {}
    progress.set_rip_log(rip_log, disc_track_total=14)
    assert progress._reconciled_label.isHidden(), "a cleared CTDB answer came back"


def test_the_wrong_track_keeps_its_warning_beside_a_ctdb_note(
    qapp: QApplication,
) -> None:
    """On F1 as recorded, track 5 stays "⚠ Wrong (AccurateRip)" and gets no note,
    while a track AccurateRip verifies gets the note."""
    progress = RipProgress()
    progress.set_rip_log(_f1_log(), disc_track_total=14)
    progress.set_ctdb_result(
        _ctdb_result({2: CTDB_DISAGREES_DIFFERS, 5: CTDB_DISAGREES_DIFFERS})
    )
    cells = {n: c.status.text for n, c in progress.track_results().items()}
    assert cells[5] == "⚠ Wrong (AccurateRip)"
    assert cells[2] == "✓ Done · ⓘ CTDB disagrees"
    # The line leads with AccurateRip's ⚠ for track 5, and the note about track
    # 2 keeps its own ⓘ beside it, word for word.
    line = progress.reconciled_text()
    assert line.startswith("⚠ AccurateRip decides track 5:")
    assert (
        "ⓘ CTDB disagrees on track 2 (differs); AccurateRip is the verdict, "
        "because AccurateRip, the per-track check, found nothing wrong with this "
        "track."
    ) in line
