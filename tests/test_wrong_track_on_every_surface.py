"""No surface calls a track clean that another calls WRONG (TASKS R112).

**The measured case.** The owner's Full run of 2026-11-03 (0.7.117 with the
fork's ``.28``), section F: track 5 matched AccurateRip on frame 450 only (v1 and
v2 "not found"). The EAC-layout log said ``Proof: none — WRONG: …`` and
``There were errors``, the report said ``accuraterip_contradiction: "wrong"``,
and the status line and the desktop notification both said::

    Done — all 14 tracks ripped cleanly, no read errors. AccurateRip: 13/14 verified.

(app log line 6764 of that run). The status line counted clean from the
ripper's ``status`` and the paranoia skips, and never asked
``verdict.track_accuraterip_contradiction``, the one predicate every other
surface asks. The report's own self-check, embedded in the same JSON, graded
"rip completed (14 of 14 tracks, no errors)" OK beside it.

The log here is that rip's whole-disc log, byte for byte (the evidence fixture
for ``round37full1103awholedisc.log``). It is driven through the window's finish
handler, so every surface the finish writes is read as the user would meet it:
the status line, the notification, the results table, the banner, the
EAC-layout log and the report. The relation is asserted, not each side alone:
the tracks each surface marks as not clean are the same set.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import stop_window_threads
from evidence_paths import evidence
from PySide6.QtWidgets import QApplication

from platterpus import report_writer
from platterpus.config import Config
from platterpus.eac_log_export import CONTRADICTED_VERDICT, DISC_HAD_ERRORS
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.track_proof import contradicted_tracks_sentence
from platterpus.ui.main_window import MainWindow
from platterpus.ui.main_window_helpers import fidelity_summary
from platterpus.verdict import (
    AR_CONTRADICTION_DIFFERS,
    AR_CONTRADICTION_WRONG,
    track_accuraterip_contradiction,
)

_F1_LOG: str = "docs/handshake/artifactsround37/round37full1103awholedisc.log"

#: Words that call a rip or a track clean. None may sit over a contradicted track.
_CLEAN_WORDS: tuple[str, ...] = (
    "all 14 tracks ripped cleanly",
    "14/14 tracks ripped cleanly",
    "no read errors",
    "No errors occurred",
    "All tracks accurately ripped",
)


def _f1_text() -> str:
    return evidence(_F1_LOG).read_text(encoding="utf-8")


def test_the_fixture_holds_the_measured_shape() -> None:
    """Floor: track 5 alone is contradicted, as WRONG, and nothing else is."""
    rip_log = parse_cyanrip_log(_f1_text())
    assert len(rip_log.tracks) == 14
    found = {t.number: track_accuraterip_contradiction(t) for t in rip_log.tracks}
    assert found[5] == AR_CONTRADICTION_WRONG
    assert [n for n, kind in found.items() if kind] == [5]
    # The ripper's own word is the clean one: the defect needs it to be.
    assert all(t.status == "ripped successfully" for t in rip_log.tracks)


def test_the_status_line_does_not_call_the_wrong_track_clean() -> None:
    summary = fidelity_summary(parse_cyanrip_log(_f1_text()), expected_track_total=14)
    for word in _CLEAN_WORDS:
        assert word not in summary, summary
    assert summary.startswith("Done — 13/14 tracks ripped cleanly. ⚠ "), summary
    assert "AccurateRip says track 5 is WRONG (only frame 450 matched" in summary


@pytest.mark.parametrize(
    ("found", "expected"),
    [
        ([], ""),
        ([(1, None), (2, None)], ""),
        (
            [(5, AR_CONTRADICTION_WRONG)],
            "AccurateRip says track 5 is WRONG (only frame 450 matched, so the "
            "audio differs from the pressing)",
        ),
        (
            [(3, AR_CONTRADICTION_WRONG), (5, AR_CONTRADICTION_WRONG), (7, None)],
            "AccurateRip says tracks 3, 5 are WRONG (only frame 450 matched, so the "
            "audio differs from the pressing)",
        ),
        (
            [(5, AR_CONTRADICTION_WRONG), (9, AR_CONTRADICTION_DIFFERS)],
            "AccurateRip says track 5 is WRONG (only frame 450 matched, so the "
            "audio differs from the pressing) and track 9 is different (nothing "
            "matched, most likely a misread)",
        ),
    ],
    ids=["none", "no-contradiction", "one-wrong", "two-wrong", "wrong-and-differs"],
)
def test_the_shared_sentence(
    found: list[tuple[int, str | None]], expected: str
) -> None:
    assert contradicted_tracks_sentence(found) == expected


@pytest.fixture()
def window(qapp: QApplication) -> Iterator[MainWindow]:
    """A real window with fakes for the backend, MusicBrainz and the tray."""
    from test_ui_main_window import _make_window

    made = _make_window(
        qapp,
        config=Config(
            host_setup_prompted=True,
            drive_setup_prompted=True,
            ctdb_verify_after_rip=False,
            verify_flac_after_rip=False,
            write_eac_log_after_rip=True,
            notify_on_completion=True,
        ),
    )
    yield made
    stop_window_threads(made)
    made.deleteLater()


class _Tray:
    """Stands in for the system tray: records what the notification would show."""

    def __init__(self) -> None:
        self.shown: list[tuple[str, str]] = []

    def showMessage(self, title: str, body: str, *_args: Any) -> None:  # Qt's name
        self.shown.append((title, body))


def test_every_surface_the_finish_writes_agrees_track_5_is_not_clean(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    window._rip_worker = SimpleNamespace(  # type: ignore[assignment]
        needs_unknown_retry=False, failure_hint=""
    )
    window._active_rip_params = None
    window._rip_cancelled = False
    window._auto_retry_done = True
    window._current_num_tracks = 14
    tray = _Tray()
    monkeypatch.setattr(window, "_ensure_tray_icon", lambda: tray)
    statuses: list[str] = []
    real_set_status = window._rip_progress.set_status

    def record_status(text: str) -> None:
        statuses.append(text)
        real_set_status(text)

    monkeypatch.setattr(window._rip_progress, "set_status", record_status)
    log_file = tmp_path / "Album.log"
    log_file.write_text(_f1_text(), encoding="utf-8")

    window._on_rip_finished(True, str(log_file))
    report_writer.writer().flush()
    if window._post_rip_thread is not None:
        window._post_rip_thread.join(timeout=10)
    report_writer.writer().flush()

    # The status line, and the notification, which sends what the window shows.
    fidelity = [s for s in statuses if s.startswith("Done — ")]
    assert fidelity, statuses  # floor: the status line was composed
    assert tray.shown, "floor: the notification was posted"
    _title, body = tray.shown[-1]
    for text in (fidelity[-1], body):
        for word in _CLEAN_WORDS:
            assert word not in text, text
        assert "track 5 is WRONG" in text, text

    # The results table and the banner.
    progress = window._rip_progress
    table = progress._ar_table
    cells = {table.item(r, 0).text(): table.item(r, 2).text() for r in range(14)}
    marked_in_table = {int(n) for n, cell in cells.items() if cell.startswith("⚠")}
    assert not progress._verdict_banner.text().startswith("✓")

    # The EAC-layout log.
    eac = (tmp_path / "Album (EAC-compatible).log").read_text(encoding="utf-8")
    assert f"\n{DISC_HAD_ERRORS}\n" in eac
    for word in _CLEAN_WORDS:
        assert word not in eac
    blocks = eac.split("\nTrack ")[1:]
    marked_in_eac = {
        int(block.split("\n", 1)[0])
        for block in blocks
        if CONTRADICTED_VERDICT in block
    }

    # The report: its per-track field, and the self-check it carries.
    report = json.loads((tmp_path / "Album.platterpus.json").read_text("utf-8"))
    marked_in_report = {
        t["number"] for t in report["tracks"] if t.get("accuraterip_contradiction")
    }
    findings = report["self_check"]["findings"]
    completed = [f for f in findings if f["text"].startswith("rip completed")]
    assert completed, findings  # floor: the completion grade ran
    assert all(f["level"] != "ok" for f in completed), completed
    assert any("track 5 is WRONG" in f["text"] for f in completed), completed

    # The relation: every surface marks the same tracks, and it is track 5.
    named = re.search(r"tracks? (?P<n>[\d, ]+) (?:is|are) WRONG", fidelity[-1])
    marked_in_status = (
        {int(n) for n in named.group("n").split(",")} if named is not None else set()
    )
    assert (
        marked_in_status == marked_in_table == marked_in_eac == marked_in_report == {5}
    ), (marked_in_status, marked_in_table, marked_in_eac, marked_in_report)
