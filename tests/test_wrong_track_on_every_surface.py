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
from dataclasses import replace
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
from platterpus.rip_addendum import SupersededTrack, addendum_text, render_addendum
from platterpus.rip_health import (
    contradicted_health,
    effective_health_status,
    health_reads_clean,
)
from platterpus.track_proof import contradicted_tracks_sentence
from platterpus.ui.disc_info_panel import DiscInfoPanel
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
    "verified — all",
    "CONFIRMED",
    "the rest of each is unverified",
)


def _named_wrong(text: str) -> set[int]:
    """The track numbers a sentence calls WRONG ("track 5 is WRONG", "tracks 3, 5
    are WRONG"), so a surface's answer is compared as a set, not as a mention."""
    named = re.search(r"tracks? (?P<n>[\d, ]+) (?:is|are) WRONG", text)
    return (
        {int(n) for n in re.findall(r"\d+", named.group("n"))}
        if named is not None
        else set()
    )


def _named_contradicted(text: str) -> set[int]:
    """The track numbers in "AccurateRip contradicts track(s) 5" (``health_status``)."""
    named = re.search(r"AccurateRip contradicts track\(s\) (?P<n>[\d, ]+)", text)
    return (
        {int(n) for n in re.findall(r"\d+", named.group("n"))}
        if named is not None
        else set()
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


def test_health_status_is_never_clean_over_a_contradicted_track() -> None:
    """Review A1: F's report said "No errors occurred" beside track 5's
    `accuraterip_contradiction: "wrong"`. The sentence the report writes (and the
    status line asks) now leads with EAC's own "There were errors" and names the
    track, by the one predicate."""
    rip_log = parse_cyanrip_log(_f1_text())
    assert rip_log.health_status == "No errors occurred"  # floor: the ripper's
    health = effective_health_status(rip_log)
    assert health == (
        "There were errors: AccurateRip contradicts track(s) 5, which the "
        "ripper's count of no errors leaves out"
    )
    assert health_reads_clean(rip_log) is False
    # The mirror: with track 5 verified, the ripper's sentence stands as it was.
    verified = next(t for t in rip_log.tracks if t.number == 1)
    clean = replace(
        rip_log,
        tracks=tuple(
            replace(
                t,
                accuraterip_v1=verified.accuraterip_v1,
                accuraterip_v2=verified.accuraterip_v2,
                accuraterip_offset=None,
            )
            for t in rip_log.tracks
        ),
    )
    assert effective_health_status(clean) == "No errors occurred"
    # Other sentences keep their words and gain the tracks.
    assert contradicted_health("2 ripping errors", [5]) == (
        "2 ripping errors; AccurateRip contradicts track(s) 5"
    )
    assert contradicted_health("", [3, 5]) == "AccurateRip contradicts track(s) 3, 5"
    assert contradicted_health("No errors occurred in the reads kept", [5]) == (
        "There were errors: AccurateRip contradicts track(s) 5. No errors "
        "occurred in the reads kept"
    )


def test_the_disc_panel_names_the_contradicted_track(qapp: QApplication) -> None:
    """Review A2: the panel read "13 of 14 tracks matched", a tally track 5 merely
    missed. It names the track, in the status line's words."""
    panel = DiscInfoPanel()
    panel.set_accuraterip_result(parse_cyanrip_log(_f1_text()), disc_track_total=14)
    assert panel._accuraterip_value.text() == (
        "13 of 14 tracks matched · ⚠ AccurateRip says track 5 is WRONG (only frame "
        "450 matched, so the audio differs from the pressing)"
    )


def test_the_addendum_never_calls_a_contradicted_re_read_confirmed() -> None:
    """Review A2: F's addendum said track 5's re-read "reproduced the first pass
    byte for byte … the original read is CONFIRMED" over a track AccurateRip calls
    WRONG. Two agreeing reads of the wrong audio confirm nothing."""
    track = SupersededTrack(
        number=5, crc="E0036697", previous_crc="E0036697", contradiction="wrong"
    )
    assert track.outcome == "confirmed"  # floor: the CRCs do agree
    text = render_addendum("accuraterip", [track])
    block = text.split("  Track 5 ", 1)[1]
    assert "CONFIRMED" not in block, block
    assert "AccurateRip contradicts that audio, so nothing is confirmed" in block
    assert "AccurateRip verdict:" in block and "track 5 is WRONG" in block
    assert "the same wrong audio twice" in text
    # The mirror: an uncontradicted reproduced read is still CONFIRMED.
    plain = render_addendum("accuraterip", [replace(track, contradiction="")])
    assert "original read is CONFIRMED" in plain
    assert "AccurateRip verdict:" not in plain


def test_the_worker_hands_the_addendum_the_shipped_reads_verdict() -> None:
    """The worker builds each addendum row from the read that shipped; the row
    carries the predicate's answer for that read (review A2)."""
    from platterpus.workers.rip_worker import RipWorker

    track5 = next(t for t in parse_cyanrip_log(_f1_text()).tracks if t.number == 5)
    row = RipWorker._superseded_record(track5, previous_crc=track5.copy_crc)
    assert row.contradiction == AR_CONTRADICTION_WRONG
    track1 = next(t for t in parse_cyanrip_log(_f1_text()).tracks if t.number == 1)
    assert RipWorker._superseded_record(track1).contradiction == ""


def test_the_addendum_rebuilt_from_a_report_carries_the_verdict(tmp_path: Path) -> None:
    """The sidecar-less path rebuilds the addendum from the report; the report's
    per-track `accuraterip_contradiction` must reach it."""
    log_path = tmp_path / "Album.log"
    log_path.write_text("cyanrip\n", encoding="utf-8")
    report = {
        "read_speed": {"retried_tracks": [{"track": 5, "replaced": True}]},
        "tracks": [
            {"number": 5, "copy_crc": "E0036697", "accuraterip_contradiction": "wrong"}
        ],
    }
    (tmp_path / "Album.platterpus.json").write_text(json.dumps(report), "utf-8")
    text = addendum_text(log_path)
    assert "AccurateRip verdict:" in text and "track 5 is WRONG" in text, text


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
    banner = progress._verdict_banner.text()
    assert not banner.startswith("✓")
    for word in _CLEAN_WORDS:
        assert word not in banner, banner
    # The banner counts rather than names: "on the other 1, only one frame
    # matched, so AccurateRip says it is WRONG". Review A2: the EAC log's word.
    assert (
        "on the other 1, only one frame matched, so AccurateRip says it is WRONG"
        in (banner)
    ), banner

    # The disc panel's AccurateRip row (review A2: "13 of 14 tracks matched").
    panel = window._disc_info_panel._accuraterip_value.text()
    for word in _CLEAN_WORDS:
        assert word not in panel, panel
    marked_in_panel = _named_wrong(panel)

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
    # Review A1: `health_status` said "No errors occurred" beside track 5.
    health = report["health_status"]
    assert health.startswith(f"{DISC_HAD_ERRORS}: "), health
    assert report["ripper_health_status"] == "No errors occurred"  # theirs, kept
    marked_in_health = _named_contradicted(health)
    # The self-check grades the completion record OK, with no clean word in it,
    # and says in a NOTE why the rip is not clean. A NOTE, not a WARN, so the
    # acceptance run's `expect-album-audit` is not failed by a disc property.
    findings = report["self_check"]["findings"]
    completed = [f for f in findings if f["text"].startswith("rip completed")]
    assert completed, findings  # floor: the completion grade ran
    for finding in completed:
        for word in (*_CLEAN_WORDS, "no errors"):
            assert word not in finding["text"], finding
    notes = [f for f in findings if "is not a clean rip" in f["text"]]
    assert [f["level"] for f in notes] == ["note"], findings
    marked_in_self_check = _named_wrong(notes[0]["text"])

    # The relation: every surface marks the same tracks, and it is track 5.
    # The EAC-layout log is the reference: every other surface names what it
    # marks, through the one predicate (`verdict.accuraterip_contradictions`).
    surfaces = {
        "status line": _named_wrong(fidelity[-1]),
        "notification": _named_wrong(body),
        "results table": marked_in_table,
        "disc panel": marked_in_panel,
        "report tracks": marked_in_report,
        "report health_status": marked_in_health,
        "self-check": marked_in_self_check,
    }
    assert marked_in_eac == {5}, marked_in_eac  # floor: the reference names it
    disagree = {name: got for name, got in surfaces.items() if got != marked_in_eac}
    assert not disagree, (marked_in_eac, disagree)
