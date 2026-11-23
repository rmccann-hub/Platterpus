"""One track table, one progress bar, Disc details folded (TASKS R179, R181).

The UX review of 0.7.127 (``docs/archive/ux-review-2026-11-17.md``) found:

* **M1** the disc IDs took seven rows above the editable table, which showed 4 of
  11 tracks at the default window size;
* **M2** the same tracks in two tables with different status words ("✓ Done"
  above, "ripped successfully" below), and two progress bars, one unlabelled;
* **M3** a rip opened on cyanrip's raw console;
* **V3** the results table spoke the databases' internals ("AR v1", "one frame
  only (200)", a hex CRC with "~").

These tests hold the redesign: the rip pane renders each track's cells and the
ONE track table shows them, in its Status column and a Verified column it gains
after a rip; the detail columns are hidden until asked for; one bar names the
track; the disc IDs fold into Disc details, whose toggle carries any ⚠ inside.

The rip log is REAL: the owner's 2026-11-03 Full run, section F, whose track 5
matched AccurateRip on frame 450 only (so AccurateRip calls it WRONG).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from conftest import stop_window_threads
from evidence_paths import evidence
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import (
    QApplication,
    QProgressBar,
    QSplitter,
    QTableView,
    QTableWidget,
    QWidget,
)
from test_ui_main_window import _make_window

from platterpus.adapters.musicbrainz_client import (
    ReleaseDetail,
    ReleaseSummary,
    TrackSummary,
)
from platterpus.config import Config
from platterpus.ctdb.matching import CtdbTrackResult, TrackVerdict
from platterpus.ctdb.repair_types import RepairedTrack, RepairRecord, RepairStatus
from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog
from platterpus.ui.disc_info_panel import DETAILS_TOGGLE_TEXT, DiscInfoPanel
from platterpus.ui.rip_progress import _TAB_DETAILS, _TAB_LOG, RipProgress
from platterpus.ui.track_results import Cell, TrackResultCells
from platterpus.ui.track_table import (
    _COL_AR_V1,
    _COL_CRC,
    _COL_STATUS,
    _COL_VERIFIED,
    DETAIL_COLUMNS,
    TrackTable,
)
from platterpus.uiscript.runner import _panel_fields

_F1_LOG: str = "docs/handshake/artifactsround37/round37full1103awholedisc.log"


@pytest.fixture()
def teardown_threads(qapp: QApplication) -> Any:
    """Windows made by the test, their threads joined before the next test."""
    created: list[Any] = []

    def factory(**kwargs: Any) -> Any:
        window = _make_window(qapp, **kwargs)
        created.append(window)
        return window

    yield factory
    for window in created:
        stop_window_threads(window)
        window.deleteLater()


def _f1() -> RipLog:
    return parse_cyanrip_log(evidence(_F1_LOG).read_text(encoding="utf-8"))


def _release(count: int = 14) -> ReleaseDetail:
    return ReleaseDetail(
        summary=ReleaseSummary(mbid="mbid-14", title="Fourteen", artist_credit="A"),
        tracks=tuple(
            TrackSummary(number=n, title=f"Track {n}", artist_credit="A")
            for n in range(1, count + 1)
        ),
    )


def _wired() -> tuple[RipProgress, TrackTable]:
    """A pane and a table connected as the window connects them."""
    pane = RipProgress()
    table = TrackTable()
    pane.track_results_changed.connect(table.set_results)
    table.set_release(_release())
    return pane, table


def _shown(table: TrackTable, number: int, col: int) -> object:
    model = table._model
    return model.data(model.index(number - 1, col))


# --- M2: one table ---------------------------------------------------------------


def test_the_window_has_one_track_table_and_one_progress_bar(
    qapp: QApplication, teardown_threads: Any
) -> None:
    window = teardown_threads(config=Config(host_setup_prompted=True))
    tables = [
        w
        for w in window.findChildren(QTableView)
        if not isinstance(w.parent(), QTableWidget)
    ]
    assert tables == [window._track_table._view], (
        f"the window lists tracks in {len(tables)} tables (UX review M2)"
    )
    assert not hasattr(window._rip_progress, "_ar_table")
    bars = window._rip_progress.findChildren(QProgressBar)
    assert bars == [window._rip_progress._overall_bar], "one progress bar (M2)"


def test_the_window_hands_the_pane_cells_to_the_track_table(
    qapp: QApplication, teardown_threads: Any
) -> None:
    """The wiring: the window's own connection, not a test's."""
    window = teardown_threads(config=Config(host_setup_prompted=True))
    window._track_table.set_release(_release())
    window._rip_progress.set_rip_log(_f1(), disc_track_total=14)
    assert window._track_table.has_results()
    assert _shown(window._track_table, 5, _COL_STATUS) == "⚠ Wrong (AccurateRip)"
    assert _shown(window._track_table, 5, _COL_VERIFIED) == "⚠ Mismatch"
    window._rip_progress.clear()  # a new rip starts
    assert not window._track_table.has_results()


def test_the_verified_column_appears_with_a_rips_results_and_goes_with_them(
    qapp: QApplication,
) -> None:
    pane, table = _wired()
    view = table._view
    assert view.isColumnHidden(_COL_VERIFIED), "no Verified column before a rip"
    assert _shown(table, 1, _COL_VERIFIED) is None

    pane.set_rip_log(_f1(), disc_track_total=14)
    assert not view.isColumnHidden(_COL_VERIFIED)
    assert _shown(table, 1, _COL_VERIFIED) == "✓ 200 matching rips"
    assert _shown(table, 1, _COL_STATUS) == "✓ Done", "one status word (M2)"
    assert _shown(table, 5, _COL_STATUS) == "⚠ Wrong (AccurateRip)"
    assert _shown(table, 5, _COL_VERIFIED) == "⚠ Mismatch"

    pane.clear()
    assert view.isColumnHidden(_COL_VERIFIED)
    assert _shown(table, 1, _COL_STATUS) == "", "the last rip's status lingered"

    pane.set_rip_log(_f1(), disc_track_total=14)
    table.set_release(_release())  # another disc: its rows carry no result
    assert view.isColumnHidden(_COL_VERIFIED)
    assert not table.has_results()


def test_the_detail_columns_are_hidden_until_asked_for(qapp: QApplication) -> None:
    """V3: the databases' internals are an EAC-style view a person asks for."""
    pane, table = _wired()
    pane.set_rip_log(_f1(), disc_track_total=14)
    view = table._view
    assert all(view.isColumnHidden(c) for c in DETAIL_COLUMNS)
    assert not table.detail_columns_visible()

    table._show_detail_action.trigger()  # the header's right-click switch
    assert table.detail_columns_visible()
    assert not any(view.isColumnHidden(c) for c in DETAIL_COLUMNS)
    assert _shown(table, 5, _COL_AR_V1) == "one frame only (200)"
    assert str(_shown(table, 5, _COL_CRC)).endswith("~")

    # Remembered for the next rip, but shown only while there are results.
    pane.clear()
    assert all(view.isColumnHidden(c) for c in DETAIL_COLUMNS)
    pane.set_rip_log(_f1(), disc_track_total=14)
    assert table.detail_columns_visible()
    table.set_detail_columns_visible(False)
    assert not table._show_detail_action.isChecked()
    assert all(view.isColumnHidden(c) for c in DETAIL_COLUMNS)


def test_a_result_tooltip_shows_every_character_as_written(
    qapp: QApplication,
) -> None:
    """The cells carry the ripper's and the databases' words: PlainText only."""
    table = TrackTable()
    table.set_release(_release(1))
    hostile = "<b>bold</b> & <i>co</i>"
    cell = Cell("✓ Done", hostile)
    table.set_results({1: TrackResultCells(cell, cell, cell, cell, cell)})
    model = table._model
    tip = model.data(model.index(0, _COL_VERIFIED), Qt.ItemDataRole.ToolTipRole)
    doc = QTextDocument()
    doc.setHtml(str(tip))
    assert doc.toPlainText() == hostile


def test_a_confirmed_repair_reaches_the_table_and_the_banners_next_step(
    qapp: QApplication,
) -> None:
    """Track 5 repaired from CTDB, and a fresh check agrees: the table says
    "✓ Repaired" and "✓ CTDB (212)", the reconciled line says CTDB decides it,
    and the banner no longer tells the user to re-rip it."""
    pane, table = _wired()
    pane.set_rip_log(_f1(), disc_track_total=14)
    assert "re-rip track 5" in pane._verdict_banner.text()  # floor: the step is there
    before = CtdbVerifyResult(
        Verdict.NO_MATCH,
        best_confidence=212,
        tracks=tuple(
            CtdbTrackResult(
                n,
                TrackVerdict.DIFFERS if n == 5 else TrackVerdict.MATCH,
                confidence=212,
            )
            for n in range(1, 15)
        ),
    )
    pane.set_ctdb_result(before)
    assert _shown(table, 5, _COL_STATUS) == "⚠ Wrong (AccurateRip)"
    record = RepairRecord(
        status=RepairStatus.REPAIRED,
        confidence=212,
        tracks=(RepairedTrack(5, "/m/05.flac", "/m/05.flac.bak", 12, 1, 2, 3, 3),),
    )
    after = CtdbVerifyResult(Verdict.MATCH, confidence=212, best_confidence=212)
    repaired = replace(before, repair=record, after_repair=after)
    pane.set_ctdb_repair("✓ Repaired from CTDB: track 5 …", "ok", result=repaired)
    assert _shown(table, 5, _COL_STATUS) == "✓ Repaired"
    assert _shown(table, 5, _COL_VERIFIED) == "✓ CTDB (212)"
    assert pane.reconciled_text().startswith("✓ CTDB decides track 5:")
    assert "Next:" not in pane._verdict_banner.text(), (
        "the banner still tells the user to re-rip the track CTDB repaired"
    )


def test_the_banners_next_step_drops_only_a_confirmed_repaired_track(
    qapp: QApplication,
) -> None:
    rip_log = _f1()
    five = next(t for t in rip_log.tracks if t.number == 5)
    two_wrong = replace(
        rip_log,
        tracks=tuple(
            replace(
                t,
                accuraterip_v1=five.accuraterip_v1,
                accuraterip_v2=five.accuraterip_v2,
                accuraterip_offset=five.accuraterip_offset,
            )
            if t.number == 9
            else t
            for t in rip_log.tracks
        ),
    )
    pane = RipProgress()
    pane.set_rip_log(two_wrong, disc_track_total=14)
    assert "re-rip tracks 5 and 9" in pane._verdict_banner.text()  # floor
    before = CtdbVerifyResult(Verdict.NO_MATCH, best_confidence=212)
    record = RepairRecord(
        status=RepairStatus.REPAIRED,
        tracks=(RepairedTrack(9, "/m/09.flac", "/m/09.flac.bak", 12, 1, 2, 3, 3),),
    )
    after = CtdbVerifyResult(Verdict.MATCH, confidence=212, best_confidence=212)
    pane.set_ctdb_result(before)
    pane.set_ctdb_repair(
        "✓ …", "ok", result=replace(before, repair=record, after_repair=after)
    )
    banner = pane._verdict_banner.text()
    assert "re-rip track 5" in banner
    assert "track 9" not in banner.split("Next:")[1]


# --- M2: one progress bar, labelled ------------------------------------------------


def test_the_one_bar_names_the_track_and_says_what_its_percentage_is(
    qapp: QApplication, tmp_path: Path
) -> None:
    pane = RipProgress()
    pane.clear()
    pane.begin_rip(tmp_path, tmp_path / "log.txt", tracks=range(1, 15))
    pane.set_progress(31.0, 62.0)
    assert pane.bar_text() == "31% of the rip", "no track yet: the disc scan"
    pane.set_current_track(5)
    assert pane.bar_text() == "Track 5 of 14 — 31% of the rip"
    # A rip of some tracks: the disc's number, then where it falls in the rip.
    pane.begin_rip(tmp_path, tmp_path / "log.txt", tracks=(3, 5, 9))
    pane.set_current_track(5)
    assert pane.bar_text() == "Track 5 (2 of 3) — 31% of the rip"
    # The rip ends: the bar names no track it is no longer on.
    pane.set_rip_log(_f1(), disc_track_total=14)
    assert pane.bar_text() == "31% of the rip"
    pane.clear()
    assert pane.bar_text() == "0% of the rip"


# --- M3: the console is not the default tab --------------------------------------


def test_a_rip_never_opens_on_the_console(qapp: QApplication, tmp_path: Path) -> None:
    pane = RipProgress()
    pane._tabs.setCurrentIndex(_TAB_LOG)
    pane.begin_rip(tmp_path, tmp_path / "log.txt")
    assert pane._tabs.currentIndex() == _TAB_DETAILS
    assert pane._tabs.count() == 2, "Details and Live log; no Tracks tab (M2)"


# --- R181: the reconciled line ----------------------------------------------------


def test_the_reconciled_line_waits_for_ctdb_and_is_not_bold(
    qapp: QApplication,
) -> None:
    pane = RipProgress()
    pane.set_rip_log(_f1(), disc_track_total=14)
    assert pane._reconciled_label.isHidden(), "no CTDB answer, no line"
    assert pane.reconciled_text() == ""
    pane.set_ctdb_result(
        CtdbVerifyResult(Verdict.MATCH, confidence=212, best_confidence=212)
    )
    assert not pane._reconciled_label.isHidden()
    assert pane.reconciled_text().startswith("⚠ AccurateRip decides track 5:")
    assert "bold" not in pane._reconciled_label.styleSheet(), (
        "the banner is the headline; two bold amber paragraphs separate nothing (A3)"
    )
    assert pane._reconciled_label.textFormat() == Qt.TextFormat.PlainText


def test_the_details_ctdb_line_never_says_verified_in_amber(
    qapp: QApplication,
) -> None:
    """A3: "CTDB: verified ✓" in amber beside AccurateRip's WRONG."""
    pane = RipProgress()
    pane.set_rip_log(_f1(), disc_track_total=14)
    pane.set_ctdb_result(
        CtdbVerifyResult(Verdict.MATCH, confidence=212, best_confidence=212)
    )
    text = pane._ctdb_label.text()
    assert "verified ✓" not in text
    assert text.startswith("CTDB: ⚠ the whole disc matches")


# --- M1: Disc details ---------------------------------------------------------------


def test_the_disc_ids_fold_into_disc_details_closed_by_default(
    qapp: QApplication,
) -> None:
    panel = DiscInfoPanel()
    folded = (
        panel._mb_id_value,
        panel._cddb_id_value,
        panel._accuraterip_value,
        panel._cache_value,
    )
    shown = (panel._drive_value, panel._mb_match_value, panel._offset_value)
    assert not panel.details_expanded()
    assert all(label.isHidden() for label in folded)
    assert not any(label.isHidden() for label in shown)
    panel._details_toggle.click()
    assert panel.details_expanded()
    assert not any(label.isHidden() for label in folded)
    assert panel._details_toggle.arrowType() == Qt.ArrowType.DownArrow
    panel.set_details_expanded(False)
    assert all(label.isHidden() for label in folded)
    assert not panel._details_toggle.isChecked()


def test_a_warning_in_a_folded_row_marks_the_toggle(qapp: QApplication) -> None:
    """A fold is not a place for a warning to hide."""
    panel = DiscInfoPanel()
    assert "⚠" not in panel._details_toggle.text()
    panel.set_accuraterip_result(_f1(), disc_track_total=14)
    assert "⚠" in panel._accuraterip_value.text()  # floor: the row holds one
    assert panel._details_toggle.text() == f"{DETAILS_TOGGLE_TEXT}  ⚠"
    assert "AccurateRip" in panel._details_toggle.toolTip()
    panel.clear_accuraterip_result()
    assert panel._details_toggle.text() == DETAILS_TOGGLE_TEXT


def test_the_snapshot_verb_still_reads_every_folded_field(
    qapp: QApplication, teardown_threads: Any
) -> None:
    """Folding changes what a person sees, never what a script reads."""
    window = teardown_threads(config=Config(host_setup_prompted=True))
    window._disc_info_panel.set_drive_cache_defeat("Yes — measured (cd-paranoia)")
    assert not window._disc_info_panel.details_expanded()
    fields = _panel_fields(window)
    assert fields["cache defeat"] == "Yes — measured (cd-paranoia)"
    assert set(fields) == {
        "drive",
        "musicbrainz",
        "accuraterip",
        "read offset",
        "cache defeat",
    }


@pytest.mark.parametrize("expanded", [True, False])
def test_opening_disc_details_gives_the_panel_its_rows_from_the_track_list(
    qapp: QApplication, teardown_threads: Any, expanded: bool
) -> None:
    window = teardown_threads(config=Config(host_setup_prompted=True))
    window.resize(1000, 860)
    window.show()
    qapp.processEvents()
    window._track_table.set_release(_release())
    qapp.processEvents()
    splitter = window._content_splitter
    closed = splitter.sizes()
    window._disc_info_panel.set_details_expanded(True)
    qapp.processEvents()
    opened = splitter.sizes()
    assert opened[0] > closed[0], f"the panel did not grow: {closed} -> {opened}"
    assert opened[1] < closed[1], "the track list did not pay for it"
    assert opened[2] == closed[2], "the rip pane paid instead of the track list"
    if not expanded:
        window._disc_info_panel.set_details_expanded(False)
        qapp.processEvents()
        assert splitter.sizes()[0] < opened[0], "closing left the gap behind"
    window.close()


def test_the_rip_pane_at_its_own_minimum_never_draws_over_itself(
    qapp: QApplication,
) -> None:
    """The v0.5.15 trap, met again by R179: a wrapped label's minimum is one line.

    With the results table gone the splitter gives the rip pane less room, and
    the banner, the reconciled line and the finished status line run to several
    lines; measured at 1000x860, the reconciled line's last line was drawn under
    the tab strip. `RipProgress._fit_minimum_height` makes the pane's minimum the
    header's height-for-width, so the pane squeezed to its own minimum (what a
    splitter gives it) still draws every header line clear of the tabs.
    """
    from test_ui_rip_progress import _overlapping_sibling_pairs

    # In a splitter, as in the window: a splitter shrinks a pane to its MINIMUM,
    # where a top-level widget would be held at its layout's height-for-width.
    splitter = QSplitter(Qt.Orientation.Vertical)
    filler = QWidget()
    splitter.addWidget(filler)
    pane = RipProgress()
    splitter.addWidget(pane)
    splitter.setChildrenCollapsible(False)
    splitter.resize(990, 700)
    splitter.show()
    pane.set_rip_log(_f1(), disc_track_total=14)
    pane.set_ctdb_result(_no_match_with_track_2_differing())
    pane.set_status("⚠ Finished — 1 track needs attention (5). " * 4)
    qapp.processEvents()
    assert not pane._reconciled_label.isHidden()  # floor: the long line is shown
    splitter.setSizes([10_000, 1])  # give the pane as little as the splitter will
    qapp.processEvents()
    pane.layout().activate()
    qapp.processEvents()
    # Every header line gets the height its wrapped text needs: measured without
    # the fix, the reconciled line got 45 px of the 52 it needs, its last line
    # cut off (the window drew it under the tab strip).
    cut = {
        w.accessibleName(): (w.height(), w.heightForWidth(w.width()))
        for w in (pane._status_label, pane._verdict_banner, pane._reconciled_label)
        if w.height() < w.heightForWidth(w.width())
    }
    assert not cut, f"header lines cut short (height, needed): {cut}"
    clashes, examined = _overlapping_sibling_pairs(pane)
    assert examined >= 8, f"the overlap detector examined only {examined}"
    assert not clashes, f"the rip pane draws over itself at its minimum: {clashes}"
    splitter.hide()
    splitter.deleteLater()


def _no_match_with_track_2_differing() -> CtdbVerifyResult:
    return CtdbVerifyResult(
        Verdict.NO_MATCH,
        best_confidence=212,
        offset_range=5879,
        tracks=tuple(
            CtdbTrackResult(
                n,
                TrackVerdict.DIFFERS if n == 2 else TrackVerdict.MATCH,
                confidence=212,
            )
            for n in range(1, 15)
        ),
    )
