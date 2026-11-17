"""The finished and failed rip's words: the status line's lead, the next step, the failure banner.

UX review of 0.7.127, finding V1 (fixed on the owner's word of 2026-11-17): after
a rip AccurateRip called WRONG on some tracks, the status line read "Done" over
an amber banner, and the banner never said what to do. These tests hold three
things:

* the pure wording (``finish_wording``): which lead each verdict level gets, and
  that no lead ever carries a pass mark the verdict did not give;
* the window, driven through the real finish handler on a real cyanrip log
  (round 37's 13-of-14 run, track 5 WRONG): the status line and the banner carry
  the same mark, the banner ends with a next step naming track 5, and the
  technical detail moved to the banner's tooltip without leaving the report;
* that the next step names controls the window really has, read off the widgets.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import stop_window_threads
from evidence_paths import evidence
from PySide6.QtWidgets import QApplication, QMenu

from platterpus import report_writer
from platterpus.config import Config
from platterpus.finish_wording import (
    RIP_ONLY_THESE,
    START_RIP,
    finished_line,
    next_step_sentence,
    tracks_phrase,
)
from platterpus.parsers.rip_log import AccurateRipResult, RipLog, TrackResult
from platterpus.ui.main_window import MainWindow
from platterpus.ui.main_window_helpers import fidelity_summary
from platterpus.ui.rip_progress import RipProgress

#: Round 37's whole-disc log of 2026-11-03: 14 tracks, track 5 matched frame 450
#: only, so AccurateRip calls it WRONG (`test_wrong_track_on_every_surface.py`
#: pins that shape).
_F1_LOG: str = "docs/handshake/artifactsround37/round37full1103awholedisc.log"

_MARKS: tuple[str, ...] = ("✓", "⚠", "ⓘ", "✖")


# --- The pure wording ---------------------------------------------------------


def test_tracks_are_listed_in_english() -> None:
    assert tracks_phrase(()) == ""
    assert tracks_phrase((5,)) == "track 5"
    assert tracks_phrase((3, 5)) == "tracks 3 and 5"
    assert tracks_phrase((3, 5, 7)) == "tracks 3, 5 and 7"


def test_the_next_step_names_the_tracks_and_the_controls() -> None:
    assert next_step_sentence(()) == ""
    one = next_step_sentence((5,))
    assert one.startswith("Next: clean the disc, then re-rip track 5: select it ")
    two = next_step_sentence((3, 5))
    assert "re-rip tracks 3 and 5: select them" in two
    for sentence in (one, two):
        assert f"“{RIP_ONLY_THESE}”" in sentence and START_RIP in sentence


@pytest.mark.parametrize(
    ("level", "clean", "lead"),
    [
        ("ok", True, "✓ Finished — "),
        ("neutral", True, "ⓘ Finished, not verified by AccurateRip — "),
        ("warn", True, "⚠ Finished with warnings — "),
        ("error", True, "✖ Finished with errors — "),
        # The verdict says verified but the line's own tally is not clean (an
        # error line the ripper's count left out): never a tick over it.
        ("ok", False, "⚠ Finished with warnings — "),
        ("neutral", False, "⚠ Finished with warnings — "),
        # No verdict: not determined, so no mark of any kind, least of all ✓.
        (None, True, "Finished — "),
        (None, False, "⚠ Finished with warnings — "),
    ],
)
def test_each_verdict_level_gets_its_own_lead(
    level: str | None, clean: bool, lead: str
) -> None:
    line = finished_line("the body.", verdict_level=level, body_clean=clean)
    assert line == f"{lead}the body.", line
    assert "Done" not in line


def test_contradicted_tracks_lead_with_a_warning_whatever_the_level() -> None:
    """A one-frame match is never "verified": the tracks AccurateRip contradicts
    lead the line, and no level the caller passes can put a tick in front."""
    for level in ("ok", "neutral", "warn", None):
        line = finished_line(
            "12/14 tracks ripped cleanly.",
            verdict_level=level,
            body_clean=True,
            attention=(3, 5),
        )
        assert line == (
            "⚠ Finished — 2 tracks need attention (3 and 5). "
            "12/14 tracks ripped cleanly."
        ), line
    single = finished_line("x", verdict_level="warn", body_clean=False, attention=(5,))
    assert single.startswith("⚠ Finished — 1 track needs attention (5). X"), single


def test_a_partial_rip_never_leads_with_a_tick(qapp: QApplication) -> None:
    """Twelve of fourteen tracks ripped, both verified: the verdict is warn (the
    shortfall), and the line must not claim the rip finished clean."""
    track = TrackResult(
        number=1,
        copy_crc="AAAA1111",
        status="ripped successfully",
        accuraterip_v2=AccurateRipResult(
            version=2, result="accurately ripped", confidence=200
        ),
    )
    from dataclasses import replace

    rip_log = RipLog(
        log_creator="cyanrip 0.9.4",
        tracks=(track, replace(track, number=2)),
        health_status="No errors occurred",
    )
    widget = RipProgress()
    widget.set_rip_log(rip_log, disc_track_total=14, outcome_status="success")
    level = widget.verdict_level()
    assert level == "warn", widget._verdict_banner.text()
    line = fidelity_summary(rip_log, expected_track_total=14, verdict_level=level)
    assert line.startswith("⚠ Finished with warnings — "), line
    assert "✓" not in line


# --- The window, through the real finish handler -----------------------------


@pytest.fixture()
def window(qapp: QApplication) -> Iterator[MainWindow]:
    from test_ui_main_window import _make_window

    made = _make_window(
        qapp,
        config=Config(
            host_setup_prompted=True,
            drive_setup_prompted=True,
            ctdb_verify_after_rip=False,
            verify_flac_after_rip=False,
            write_eac_log_after_rip=False,
        ),
    )
    yield made
    stop_window_threads(made)
    made.deleteLater()


def _finish(
    window: MainWindow, log_file: Path, monkeypatch: pytest.MonkeyPatch
) -> list[str]:
    """Run the real finish handler on ``log_file``; return every status set."""
    window._rip_worker = SimpleNamespace(  # type: ignore[assignment]
        needs_unknown_retry=False, failure_hint=""
    )
    window._active_rip_params = None
    window._rip_cancelled = False
    window._auto_retry_done = True
    window._current_num_tracks = 14
    statuses: list[str] = []
    real_set_status = window._rip_progress.set_status

    def record(text: str) -> None:
        statuses.append(text)
        real_set_status(text)

    monkeypatch.setattr(window._rip_progress, "set_status", record)
    window._on_rip_finished(True, str(log_file))
    report_writer.writer().flush()
    if window._post_rip_thread is not None:
        window._post_rip_thread.join(timeout=10)
    report_writer.writer().flush()
    return statuses


def test_a_warning_rip_never_says_done_and_ends_with_a_next_step(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """V1, reproduced on the real log: "Done — 13/14 …" over an amber banner."""
    import json

    log_file = tmp_path / "Album.log"
    log_file.write_text(evidence(_F1_LOG).read_text(encoding="utf-8"), encoding="utf-8")
    statuses = _finish(window, log_file, monkeypatch)
    progress = window._rip_progress

    status = progress.current_status()
    assert statuses, "floor: the finish handler set a status"
    assert not any(s.startswith("Done") for s in statuses), statuses
    # The status line carries the banner's level and mark.
    assert progress.verdict_level() == "warn"
    assert status.startswith("⚠ Finished — 1 track needs attention (5). "), status

    banner = progress._verdict_banner.text()
    assert banner.startswith("⚠"), banner
    assert banner.endswith(next_step_sentence((5,))), banner
    # The technical detail is in the tooltip, word for word the status line's.
    tip = progress._verdict_banner.toolTip()
    assert "track 5 is WRONG (only frame 450 matched" in tip, tip
    # ...and never left the report: the next step is the window's advice only.
    report = json.loads((tmp_path / "Album.platterpus.json").read_text("utf-8"))
    assert "Next:" not in report["verdict"]["message"]
    assert "only one frame matched" in report["verdict"]["message"]


def test_a_verified_rip_leads_with_the_tick_the_banner_has(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The twin: ✓ on the status line when, and because, the banner says ✓."""
    tracks = tuple(
        TrackResult(
            number=n,
            copy_crc=f"{n:08X}",
            status="ripped successfully",
            accuraterip_v2=AccurateRipResult(
                version=2, result="accurately ripped", confidence=200
            ),
        )
        for n in range(1, 15)
    )
    rip_log = RipLog(
        log_creator="cyanrip 0.9.4", tracks=tracks, health_status="No errors occurred"
    )
    monkeypatch.setattr(window, "parse_rip_log_from_disk", lambda _path: rip_log)
    log_file = tmp_path / "Album.log"
    log_file.write_text("cyanrip 0.9.4\n", encoding="utf-8")

    _finish(window, log_file, monkeypatch)
    progress = window._rip_progress
    assert progress.verdict_level() == "ok", progress._verdict_banner.text()
    assert progress._verdict_banner.text().startswith("✓")
    status = progress.current_status()
    assert status.startswith("✓ Finished — all 14 tracks ripped cleanly"), status
    # No next step over a clean rip: there is nothing to do.
    assert "Next:" not in progress._verdict_banner.text()


def test_the_next_step_names_controls_the_window_has(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read off the widgets, not off the constants: the Start button's text, and
    the track list's right-click menu as it is built."""
    from platterpus.adapters.musicbrainz_client import TrackSummary

    start = window._rip_controls._start_button.text().replace("&", "")
    assert start == START_RIP

    table = window._track_table
    table._model.set_tracks(
        [TrackSummary(number=n, title=f"T{n}", length_ms=1000) for n in (1, 2)]
    )
    table._view.selectRow(0)
    shown: list[str] = []

    import platterpus.ui.track_table as track_table_module

    class _RecordingMenu(QMenu):
        """The real menu, built by the real code; only showing it is skipped."""

        def exec(self, *_args: object) -> None:  # type: ignore[override]
            shown.extend(a.text() for a in self.actions())

    monkeypatch.setattr(track_table_module, "QMenu", _RecordingMenu)
    table._show_track_menu(table._view.rect().center())
    assert RIP_ONLY_THESE in shown, shown
