"""Tests for platterpus.ui.rip_progress."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
from platterpus.parsers.rip_log import (
    AccurateRipResult,
    RipLog,
    TrackResult,
)
from platterpus.ui.rip_progress import (
    RipProgress,
    _ar_cell,
    _basename,
    _eac_cell,
    accuraterip_verdict,
    ctdb_verdict_level,
    ctdb_verdict_line,
    loudness_summary_line,
)

# --- Helpers --------------------------------------------------------------


class _OpenUrlSpy:
    def __init__(self) -> None:
        self.calls: list[QUrl] = []

    def __call__(self, url: QUrl) -> bool:
        self.calls.append(url)
        return True


def _track(
    number: int = 1,
    filename: str = "Artist/Album/01. Track.flac",
    status: str = "Copy OK",
    v1: AccurateRipResult | None = None,
    v2: AccurateRipResult | None = None,
    offset: AccurateRipResult | None = None,
) -> TrackResult:
    return TrackResult(
        number=number,
        filename=filename,
        status=status,
        accuraterip_v1=v1,
        accuraterip_v2=v2,
        accuraterip_offset=offset,
    )


# --- EAC results column ---------------------------------------------------


def test_eac_cell_verified_shows_crc_and_check() -> None:
    """A verified, Copy-OK track shows its EAC CRC32 + the ✓ archival mark, and
    the tooltip disclaims EAC-checksum equivalence (honesty)."""
    track = TrackResult(
        number=1,
        copy_crc="b0d122e7",
        status="ripped successfully",
        accuraterip_v2=AccurateRipResult(version=2, confidence=200),
    )
    text, tip = _eac_cell(track)
    assert text == "B0D122E7  ✓"
    assert "AccurateRip-verified" in tip
    assert "never signs an EAC log" in tip


def test_eac_cell_offset_variant_is_partial_not_a_check() -> None:
    """An offset-variant-only match is partial (~), never a false ✓."""
    track = TrackResult(
        number=1,
        copy_crc="E0036697",
        status="ripped successfully",
        accuraterip_v1=AccurateRipResult(
            version=1, result="not found", confidence=None
        ),
        accuraterip_offset=AccurateRipResult(version=1, confidence=200),
    )
    text, tip = _eac_cell(track)
    assert text == "E0036697  ~"
    assert "partially accurate" in tip.lower()


def test_eac_cell_not_in_db_shows_value_without_check() -> None:
    """A recorded CRC that can't be externally verified shows the value, no ✓."""
    track = TrackResult(number=1, copy_crc="7A2ED98F", status="ripped successfully")
    text, tip = _eac_cell(track)
    assert text == "7A2ED98F"
    assert "✓" not in text and "~" not in text
    assert "AccurateRip database" in tip
    # Honesty (trust-copy audit, 2026-07-08): this branch fires for BOTH a track
    # that isn't in AccurateRip AND one that IS present but whose CRC didn't match
    # (confidence 0). The tip must not assert the absolute "isn't in the database"
    # — it must acknowledge the didn't-match case too.
    assert "didn't match" in tip
    assert "can't be independently verified" in tip


def test_eac_cell_without_crc_is_dash() -> None:
    text, tip = _eac_cell(TrackResult(number=1))
    assert text == "—"


# --- Initial state -------------------------------------------------------


def test_default_state(qapp: QApplication) -> None:
    widget = RipProgress()
    assert widget._status_label.text() == "Idle."
    assert widget._progress_bar.value() == 0
    assert widget._log_view.toPlainText() == ""
    assert widget._ar_table.rowCount() == 0
    assert widget._view_log_button.isEnabled() is False


def test_scroll_areas_have_small_minimum_height_for_splitter(
    qapp: QApplication,
) -> None:
    # The vertical splitter in the main window can only redistribute space if
    # its panes can shrink. The log view and AccurateRip table are the big
    # scrollable areas; they keep a small (≤120px) minimum so the splitter has
    # drag slack at the default window size (0.4.x resize fix: the handles
    # showed the resize cursor but wouldn't move until the window was maximized).
    widget = RipProgress()
    assert 0 < widget._log_view.minimumHeight() <= 120
    assert 0 < widget._ar_table.minimumHeight() <= 120


def test_status_surfaces_have_accessible_names(qapp: QApplication) -> None:
    # Screen readers need a name on every status surface (a11y, principle #10).
    widget = RipProgress()
    assert widget._overall_bar.accessibleName()
    assert widget._progress_bar.accessibleName()
    assert widget._verdict_banner.accessibleName()
    assert widget._ar_table.accessibleName()
    assert widget._ctdb_label.accessibleName()
    assert widget._loudness_label.accessibleName()


def test_every_verdict_level_has_a_non_color_symbol() -> None:
    # Status must be conveyed by symbol + text, never colour alone — so each
    # level's message starts with a distinct marker (✓ / ⚠ / ⓘ).
    from platterpus.parsers.rip_log import AccurateRipResult, RipLog, TrackResult

    ok, _ = accuraterip_verdict(
        RipLog(
            tracks=(TrackResult(1, accuraterip_v1=AccurateRipResult(1, confidence=9)),)
        )
    )
    warn, _ = accuraterip_verdict(
        RipLog(
            tracks=(
                TrackResult(1, accuraterip_v1=AccurateRipResult(1, confidence=9)),
                TrackResult(2, copy_crc="AAAA", accuraterip_v1=AccurateRipResult(1)),
            )
        )
    )
    neutral, _ = accuraterip_verdict(RipLog(tracks=(TrackResult(1, copy_crc="AAAA"),)))
    assert ok.startswith("✓")
    assert warn.startswith("⚠")
    assert neutral.startswith("ⓘ")


def test_neutral_verdict_is_honest_about_no_verification() -> None:
    """Regression (honesty): a zero-AccurateRip-match verdict must NOT claim the
    Copy CRC proves 'a secure read', and must name the wrong-offset possibility —
    this is the exact headline a wrong-offset rip produces, and the old wording
    falsely reassured on bit-shifted audio.
    """
    from platterpus.parsers.rip_log import RipLog, TrackResult

    message, level = accuraterip_verdict(
        RipLog(tracks=(TrackResult(1, copy_crc="AAAA"),))
    )
    lowered = message.lower()
    assert "secure read" not in lowered
    assert "not independently verified" in lowered
    assert "offset" in lowered  # names the wrong-offset possibility
    assert level == "neutral"


def test_verdict_confidence_floor_ignores_non_matching_zero() -> None:
    # Each track is verified via v2 (conf >= 1) while v1 is "present, no match"
    # at confidence 0. The "(confidence X+)" floor must reflect only the real
    # matches (min of 200, 50 = 50), never the misleading 0.
    log = RipLog(
        tracks=(
            TrackResult(
                1,
                accuraterip_v1=AccurateRipResult(1, confidence=0),
                accuraterip_v2=AccurateRipResult(2, confidence=200),
            ),
            TrackResult(
                2,
                accuraterip_v1=AccurateRipResult(1, confidence=0),
                accuraterip_v2=AccurateRipResult(2, confidence=50),
            ),
        )
    )
    message, level = accuraterip_verdict(log)
    assert level == "ok"
    assert "confidence 50+" in message
    assert "confidence 0+" not in message


def test_verdict_surfaces_offset_variant_partial_matches() -> None:
    # Real disc (tracks 3 & 5): v1/v2 "not found" but the +450 offset-variant
    # pressing matched at confidence 200 ("partially accurate"). The banner must
    # say so — not bury it in "aren't in the database or didn't match" — while
    # staying amber (partial ≠ proven bit-perfect).
    offset = AccurateRipResult(version=450, result="partial", confidence=200)
    # Mirror the real log: the partial track still has v1/v2 lines, but they're
    # "not found" (confidence None), and only the offset variant matched.
    not_found = AccurateRipResult(version=1, result="not found", confidence=None)
    log = RipLog(
        tracks=(
            TrackResult(1, accuraterip_v2=AccurateRipResult(2, confidence=200)),
            TrackResult(2, accuraterip_v2=AccurateRipResult(2, confidence=200)),
            TrackResult(
                3,
                accuraterip_v1=not_found,
                accuraterip_v2=not_found,
                accuraterip_offset=offset,
            ),
        )
    )
    message, level = accuraterip_verdict(log)
    assert level == "warn"
    assert "2 of 3" in message
    assert "offset-variant" in message and "partially accurate" in message
    # Never claims the partial track is bit-perfect / exactly verified.
    assert "3 of 3" not in message


# --- Log streaming -------------------------------------------------------


def test_append_log_line_adds_text(qapp: QApplication) -> None:
    widget = RipProgress()
    widget.append_log_line("first")
    widget.append_log_line("second")

    text = widget._log_view.toPlainText()
    assert "first" in text
    assert "second" in text


# --- Progress updates ----------------------------------------------------


def test_set_progress_updates_both_bars_only(qapp: QApplication) -> None:
    # set_progress drives the overall + task bars; the status label is
    # owned by set_status (fed from the worker's phase signal).
    widget = RipProgress()
    before = widget._status_label.text()
    widget.set_progress(60.0, 42.0)

    assert widget._overall_bar.value() == 60
    assert widget._progress_bar.value() == 42
    assert widget._status_label.text() == before  # unchanged


def test_set_status_updates_label(qapp: QApplication) -> None:
    widget = RipProgress()
    # Fixed clock so the timestamp prefix is deterministic (maintainer's ask:
    # every status carries the wall-clock time it was set).
    from datetime import datetime

    widget._now = lambda: datetime(2026, 7, 5, 15, 20, 11)
    widget.set_status("All done.")
    assert widget._status_label.text() == "15:20:11 · All done."


# --- AccurateRip table ---------------------------------------------------


def test_set_rip_log_populates_table(qapp: QApplication) -> None:
    widget = RipProgress()
    log = RipLog(
        tracks=(
            _track(
                1,
                filename="Pink Floyd/Dark Side/01. Speak to Me.flac",
                v1=AccurateRipResult(
                    version=1, result="Found, exact match", confidence=14
                ),
                v2=AccurateRipResult(
                    version=2, result="Found, exact match", confidence=11
                ),
            ),
            _track(
                2,
                filename="Pink Floyd/Dark Side/02. Breathe.flac",
                v1=AccurateRipResult(
                    version=1,
                    result="Track not present in AccurateRip database",
                    confidence=0,
                ),
                v2=None,
            ),
        )
    )

    widget.set_rip_log(log)

    assert widget._ar_table.rowCount() == 2
    assert widget._ar_table.item(0, 0).text() == "1"
    assert "Speak to Me" in widget._ar_table.item(0, 1).text()
    assert widget._ar_table.item(0, 2).text() == "Copy OK"
    assert widget._ar_table.item(0, 3).text() == "OK (14)"
    assert widget._ar_table.item(0, 4).text() == "OK (11)"
    # Track 2 — v1 not in DB, v2 missing.
    assert widget._ar_table.item(1, 3).text() == "not in DB"
    assert widget._ar_table.item(1, 4).text() == "—"


def test_set_rip_log_empty_tracks_clears_table(qapp: QApplication) -> None:
    widget = RipProgress()
    widget._ar_table.setRowCount(3)  # pretend we had results
    widget.set_rip_log(RipLog())
    assert widget._ar_table.rowCount() == 0


# --- Album loudness + partial-accurate footnote --------------------------


def test_loudness_summary_line_formats_both_facts() -> None:
    log = RipLog(
        tracks=(),
        album_loudness={
            "integrated_lufs": "-9.3",
            "lra_lu": "7.1",
            "true_peak_dbfs": "-1.0",
        },
        partially_accurate_summary="2/2 tracks ripped partially accurately "
        "(offset-variant match)",
    )
    line = loudness_summary_line(log)
    assert "-9.3 LUFS integrated" in line
    assert "range 7.1 LU" in line
    assert "true peak -1.0 dBFS" in line
    assert "2/2 tracks ripped partially accurately" in line
    assert " · " in line  # the two facts are joined


def test_loudness_summary_line_empty_when_no_data() -> None:
    # A whipper-style log has no loudness and no partial matches → nothing to
    # show (the label stays hidden).
    assert loudness_summary_line(RipLog(tracks=())) == ""


def test_loudness_summary_line_partial_only() -> None:
    log = RipLog(tracks=(), partially_accurate_summary="1/3 tracks partial")
    assert loudness_summary_line(log) == "1/3 tracks partial"


def test_loudness_summary_line_never_raises_on_junk() -> None:
    # It backs a results-pane label from a best-effort parse — defend against a
    # wrongly-typed field rather than crashing the finish handler.
    from types import SimpleNamespace

    junk = SimpleNamespace(album_loudness="not-a-dict", partially_accurate_summary=None)
    assert loudness_summary_line(junk) == ""


def test_set_rip_log_shows_loudness_footnote(qapp: QApplication) -> None:
    widget = RipProgress()
    log = RipLog(
        tracks=(_track(),),
        album_loudness={"integrated_lufs": "-9.3"},
        partially_accurate_summary="1/1 tracks ripped partially accurately",
    )
    widget.set_rip_log(log)
    # isHidden() reflects the explicit setVisible() intent without the parent
    # being shown (isVisible() is always False on an unshown widget tree).
    assert widget._loudness_label.isHidden() is False
    assert "-9.3 LUFS" in widget._loudness_label.text()
    assert "1/1 tracks" in widget._loudness_label.text()


def test_set_rip_log_hides_loudness_footnote_when_empty(qapp: QApplication) -> None:
    widget = RipProgress()
    widget._loudness_label.setText("stale")  # pretend a prior rip left text
    widget._loudness_label.setVisible(True)
    widget.set_rip_log(RipLog(tracks=(_track(),)))
    assert widget._loudness_label.isHidden() is True
    assert widget._loudness_label.text() == ""


# --- View log button -----------------------------------------------------


def test_set_log_path_enables_all_three_output_buttons(
    qapp: QApplication, tmp_path: Path
) -> None:
    widget = RipProgress()
    log_file = tmp_path / "rip.log"
    log_file.write_text("dummy")

    widget.set_log_path(log_file)

    assert widget._view_log_button.isEnabled() is True
    assert widget._view_report_button.isEnabled() is True
    assert widget._open_folder_button.isEnabled() is True


def test_set_log_path_none_disables_all_three(qapp: QApplication) -> None:
    widget = RipProgress()
    widget.set_log_path(Path("/tmp/x"))  # enable
    widget.set_log_path(None)
    assert widget._view_log_button.isEnabled() is False
    assert widget._view_report_button.isEnabled() is False
    assert widget._open_folder_button.isEnabled() is False


def test_cue_button_enabled_only_when_a_cue_sits_beside_the_log(
    qapp: QApplication, tmp_path: Path
) -> None:
    # cyanrip writes <stem>.cue beside <stem>.log during the rip, so the button
    # gates on the file actually being present (no dead button when a rip made
    # no cue) — unlike the JSON report, which we write ourselves right after.
    widget = RipProgress()
    log_file = tmp_path / "Album.log"
    log_file.write_text("dummy")

    # No cue on disk yet → button stays disabled…
    widget.set_log_path(log_file)
    assert widget._view_cue_button.isEnabled() is False

    # …present it and re-point → button enables and targets the cue.
    (tmp_path / "Album.cue").write_text('FILE "Album.flac" WAVE\n')
    widget.set_log_path(log_file)
    assert widget._view_cue_button.isEnabled() is True


def test_view_cue_opens_the_cue_beside_the_log(
    qapp: QApplication, tmp_path: Path
) -> None:
    # IMP-1: a .cue has no default app on a fresh KDE → in-app viewer, not openUrl.
    views: list[tuple[Path, str]] = []
    spy = _OpenUrlSpy()
    widget = RipProgress(open_url=spy, view_file=lambda p, t: views.append((p, t)))
    log_file = tmp_path / "Album.log"
    log_file.write_text("dummy")
    (tmp_path / "Album.cue").write_text('FILE "Album.flac" WAVE\n')
    widget.set_log_path(log_file)

    widget._view_cue_button.click()

    assert spy.calls == []  # NOT openUrl → no "Open With" chooser
    assert views == [(tmp_path / "Album.cue", "Cue sheet — Album.cue")]


def test_set_log_path_none_disables_the_cue_button(
    qapp: QApplication, tmp_path: Path
) -> None:
    widget = RipProgress()
    log_file = tmp_path / "Album.log"
    log_file.write_text("dummy")
    (tmp_path / "Album.cue").write_text("x")
    widget.set_log_path(log_file)  # enable
    assert widget._view_cue_button.isEnabled() is True
    widget.set_log_path(None)
    assert widget._view_cue_button.isEnabled() is False


# --- In-progress access (real-time logs + folder during/after the rip) -------


def test_begin_rip_enables_folder_and_log_from_the_start(
    qapp: QApplication, tmp_path: Path
) -> None:
    # A frozen or cancelled rip must never be a dead end: Open rip folder and
    # View log are enabled the moment the rip begins, before any .log exists.
    widget = RipProgress()
    assert widget._open_folder_button.isEnabled() is False
    widget.begin_rip(tmp_path, tmp_path / "log.txt")
    assert widget._open_folder_button.isEnabled() is True
    assert widget._view_log_button.isEnabled() is True
    # Report + cue need the finished .log, so they stay disabled until finish.
    assert widget._view_report_button.isEnabled() is False
    assert widget._view_cue_button.isEnabled() is False


def test_view_log_during_rip_opens_the_live_app_log(
    qapp: QApplication, tmp_path: Path
) -> None:
    # During the rip (no backend .log yet) View log opens the real-time app log.
    views: list[tuple[Path, str]] = []
    widget = RipProgress(view_file=lambda p, t: views.append((p, t)))
    live_log = tmp_path / "log.txt"
    live_log.write_text("live")
    widget.begin_rip(tmp_path, live_log)

    widget._view_log_button.click()

    assert views == [(live_log, f"Rip log — {live_log.name}")]


def test_cancel_keeps_folder_and_log_reachable(
    qapp: QApplication, tmp_path: Path
) -> None:
    # The reported bug: after force-cancel, Open rip folder did nothing. On
    # cancel the finish handler calls set_log_path("") (no .log was written) —
    # which must NOT blank the buttons begin_rip enabled; the partial folder +
    # live log are still the user's way in.
    widget = RipProgress()
    live_log = tmp_path / "log.txt"
    widget.begin_rip(tmp_path, live_log)
    widget.set_log_path(None)  # cancel / no .log
    assert widget._open_folder_button.isEnabled() is True
    assert widget._view_log_button.isEnabled() is True
    # …but the report/cue (which need the finished .log) are unavailable.
    assert widget._view_report_button.isEnabled() is False
    assert widget._view_cue_button.isEnabled() is False


def test_set_log_path_supersedes_the_live_log_at_finish(
    qapp: QApplication, tmp_path: Path
) -> None:
    # After a successful finish, View log opens the backend's own .log, not the
    # live app log.
    views: list[tuple[Path, str]] = []
    widget = RipProgress(view_file=lambda p, t: views.append((p, t)))
    widget.begin_rip(tmp_path, tmp_path / "log.txt")
    rip_log = tmp_path / "Album.log"
    rip_log.write_text("done")
    widget.set_log_path(rip_log)

    widget._view_log_button.click()

    assert views == [(rip_log, f"Rip log — {rip_log.name}")]


# --- Stall notice (liveness watchdog banner) ---------------------------------


def test_stall_notice_shows_and_hides(qapp: QApplication) -> None:
    widget = RipProgress()
    assert widget._stall_label.isVisibleTo(widget) is False
    widget.set_stall_notice("⚠ No progress for 1m — the drive may be stuck.")
    assert widget._stall_label.isVisibleTo(widget) is True
    assert "stuck" in widget._stall_label.text()
    widget.set_stall_notice(None)
    assert widget._stall_label.isVisibleTo(widget) is False


def test_clear_resets_stall_notice_and_live_log(
    qapp: QApplication, tmp_path: Path
) -> None:
    widget = RipProgress()
    widget.begin_rip(tmp_path, tmp_path / "log.txt")
    widget.set_stall_notice("⚠ stuck")
    widget.clear()
    assert widget._stall_label.isVisibleTo(widget) is False
    assert widget._live_log_path is None
    assert widget._view_log_button.isEnabled() is False
    assert widget._open_folder_button.isEnabled() is False


def test_view_report_opens_the_json_beside_the_log(
    qapp: QApplication, tmp_path: Path
) -> None:
    # IMP-1: the report opens in the in-app viewer, not via openUrl (a
    # .platterpus.json has no default app on a fresh KDE → "Open With" chooser).
    views: list[tuple[Path, str]] = []
    spy = _OpenUrlSpy()
    widget = RipProgress(open_url=spy, view_file=lambda p, t: views.append((p, t)))
    log_file = tmp_path / "Album.log"
    widget.set_log_path(log_file)

    widget._view_report_button.click()

    assert spy.calls == []  # NOT openUrl
    assert len(views) == 1
    assert views[0][0] == tmp_path / "Album.platterpus.json"


def test_open_folder_opens_the_album_directory(
    qapp: QApplication, tmp_path: Path
) -> None:
    spy = _OpenUrlSpy()
    widget = RipProgress(open_url=spy)
    log_file = tmp_path / "Album.log"
    widget.set_log_path(log_file)

    widget._open_folder_button.click()

    assert len(spy.calls) == 1
    assert spy.calls[0].toLocalFile() == str(tmp_path)


def test_view_log_opens_in_app_viewer(qapp: QApplication, tmp_path: Path) -> None:
    # IMP-1: the log opens in the in-app read-only viewer, not the OS chooser.
    views: list[tuple[Path, str]] = []
    spy = _OpenUrlSpy()
    widget = RipProgress(open_url=spy, view_file=lambda p, t: views.append((p, t)))
    log_file = tmp_path / "rip.log"
    log_file.write_text("dummy")
    widget.set_log_path(log_file)

    widget._view_log_button.click()

    assert spy.calls == []  # NOT openUrl → no "Open With" chooser
    assert views == [(log_file, f"Rip log — {log_file.name}")]


def test_view_log_no_op_without_path(qapp: QApplication) -> None:
    views: list[tuple[Path, str]] = []
    widget = RipProgress(view_file=lambda p, t: views.append((p, t)))
    widget._on_view_log_clicked()  # call directly; button is disabled
    assert views == []


# --- clear() -------------------------------------------------------------


def test_clear_resets_all_state(qapp: QApplication, tmp_path: Path) -> None:
    widget = RipProgress()
    widget.append_log_line("noise")
    widget.set_progress(70.0, 90.0)
    widget.set_rip_log(RipLog(tracks=(_track(),)))
    widget.set_log_path(tmp_path / "x.log")

    widget.clear()

    assert widget._status_label.text() == "Idle."
    assert widget._overall_bar.value() == 0
    assert widget._progress_bar.value() == 0
    assert widget._log_view.toPlainText() == ""
    assert widget._ar_table.rowCount() == 0
    assert widget._view_log_button.isEnabled() is False


# --- _basename helper ----------------------------------------------------


def test_basename_strips_extension() -> None:
    assert _basename("Artist/Album/01. Title.flac") == "01. Title"


def test_basename_handles_empty() -> None:
    assert _basename("") == ""


# --- _ar_cell helper -----------------------------------------------------


def test_ar_cell_none_renders_placeholder() -> None:
    assert _ar_cell(None) == "—"


def test_ar_cell_exact_match() -> None:
    ar = AccurateRipResult(version=1, result="Found, exact match", confidence=14)
    assert _ar_cell(ar) == "OK (14)"


def test_ar_cell_not_in_db() -> None:
    ar = AccurateRipResult(
        version=2,
        result="Track not present in AccurateRip database",
        confidence=0,
    )
    assert _ar_cell(ar) == "not in DB"


def test_ar_cell_cyanrip_not_found_reads_not_in_db_not_bad_rip() -> None:
    """cyanrip's alarming "not found, either a new pressing, or bad rip" must
    render as the plain, non-alarmist "not in DB" — a track absent from the
    database is not necessarily a bad rip (trust-first wording)."""
    ar = AccurateRipResult(
        version=1,
        result="not found, either a new pressing, or bad rip",
        confidence=None,
    )
    cell = _ar_cell(ar)
    assert cell == "not in DB"
    assert "bad rip" not in cell


def test_ar_cell_offset_variant_match_reads_as_partial_not_bad() -> None:
    """When v1/v2 didn't match but the +450 offset variant did, the cell reads
    "offset-variant match (N)" — a partially-accurate result — instead of the
    standard checksum's scary "…or bad rip". Regression for the Roots rip, where
    tracks 11–17 are legit offset-variant matches that read as "bad rip"."""
    not_found = AccurateRipResult(
        version=1,
        result="not found, either a new pressing, or bad rip",
        confidence=None,
    )
    offset = AccurateRipResult(version=450, result="partial", confidence=28)
    cell = _ar_cell(not_found, offset_result=offset)
    assert cell == "offset-variant match (28)"
    assert "bad rip" not in cell


def test_ar_cell_plain_match_wins_over_offset() -> None:
    """A track that DID match v1/v2 shows the plain OK, even if an offset result
    is also present — a real match is never downgraded to "offset-variant"."""
    ok = AccurateRipResult(version=2, result="accurately ripped", confidence=200)
    offset = AccurateRipResult(version=450, result="partial", confidence=28)
    assert _ar_cell(ok, offset_result=offset) == "OK (200)"


def test_set_rip_log_offset_variant_track_not_shown_as_bad(
    qapp: QApplication,
) -> None:
    """End-to-end: an offset-variant track's AR cells in the table read as a
    partial match, never "bad rip" — the on-screen fix the maintainer asked for."""
    widget = RipProgress()
    log = RipLog(
        tracks=(
            _track(
                11,
                filename="VA/Roots/11 - All the Way.flac",
                v1=AccurateRipResult(version=1, result="not found", confidence=None),
                v2=AccurateRipResult(version=2, result="not found", confidence=None),
                offset=AccurateRipResult(version=450, result="partial", confidence=28),
            ),
        )
    )
    widget.set_rip_log(log)
    assert widget._ar_table.item(0, 3).text() == "offset-variant match (28)"
    assert widget._ar_table.item(0, 4).text() == "offset-variant match (28)"
    assert "bad rip" not in widget._ar_table.item(0, 3).text()


# --- CTDB verdict --------------------------------------------------------


def test_ctdb_verdict_line_match_validated() -> None:
    result = CtdbVerifyResult(Verdict.MATCH, confidence=8, crc_validated=True)
    line = ctdb_verdict_line(result)
    assert "verified" in line
    assert "8" in line
    assert "EXPERIMENTAL" not in line


def test_ctdb_verdict_line_match_unvalidated_is_experimental() -> None:
    # If the gate were ever re-opened (crc_validated=False), a match must be
    # labelled experimental, never a plain "verified". (The shipped default is
    # now True — KDD-16 — so this pins the value explicitly.)
    result = CtdbVerifyResult(Verdict.MATCH, confidence=8, crc_validated=False)
    line = ctdb_verdict_line(result)
    assert "EXPERIMENTAL" in line
    assert "verified ✓" not in line


def test_ctdb_verdict_line_no_match_unvalidated_does_not_blame_the_rip() -> None:
    # Regression (real-disc Police report): with the gate re-opened
    # (crc_validated=False, KDD-16), a NO_MATCH must NOT assert "this rip
    # differs" — an unproven CRC is EXPECTED to disagree. (Shipped default is
    # now True; pin the value explicitly to keep this path covered.)
    line = ctdb_verdict_line(CtdbVerifyResult(Verdict.NO_MATCH, crc_validated=False))
    assert "differs" not in line
    assert "experimental" in line.lower()
    assert "KDD-16" in line


def test_ctdb_verdict_line_no_match_is_scoped_to_the_tested_alignment() -> None:
    # A validated NO_MATCH is a real signal and must still be shown — but the
    # line may only claim what was measured. We test ONE alignment; CTDB also
    # holds offset-shifted pressings (crc.CTDB_OFFSET_RANGE), so "this rip
    # differs from the database" was a conclusion the check cannot support
    # (audit finding, 2026-07-28).
    line = ctdb_verdict_line(CtdbVerifyResult(Verdict.NO_MATCH, crc_validated=True))
    assert "no match at the standard alignment" in line
    assert "AccurateRip is the per-track authority" in line
    assert "differs" not in line


def test_ctdb_verdict_line_other_verdicts() -> None:
    assert "database" in ctdb_verdict_line(CtdbVerifyResult(Verdict.NOT_IN_DATABASE))
    assert "flac" in ctdb_verdict_line(CtdbVerifyResult(Verdict.DECODER_UNAVAILABLE))
    assert "unavailable" in ctdb_verdict_line(CtdbVerifyResult(Verdict.LOOKUP_ERROR))


def test_ctdb_verdict_level_tracks_trust() -> None:
    # A hardware-validated match is green; an experimental match is amber
    # (never green); everything else is neutral grey.
    assert (
        ctdb_verdict_level(
            CtdbVerifyResult(Verdict.MATCH, confidence=8, crc_validated=True)
        )
        == "ok"
    )
    assert (
        ctdb_verdict_level(
            CtdbVerifyResult(Verdict.MATCH, confidence=8, crc_validated=False)
        )
        == "warn"
    )
    assert ctdb_verdict_level(CtdbVerifyResult(Verdict.NO_MATCH)) == "neutral"
    assert ctdb_verdict_level(CtdbVerifyResult(Verdict.NOT_IN_DATABASE)) == "neutral"


# --- AccurateRip verdict banner ------------------------------------------


def _ar(version: int, confidence: int | None, result: str = "Found, exact match"):
    return AccurateRipResult(version=version, result=result, confidence=confidence)


def test_accuraterip_verdict_all_verified_is_ok() -> None:
    log = RipLog(
        tracks=(
            _track(1, v1=_ar(1, 14), v2=_ar(2, 11)),
            _track(2, v1=_ar(1, 5), v2=_ar(2, 3)),
        )
    )
    message, level = accuraterip_verdict(log)
    assert level == "ok"
    assert "all 2 tracks" in message
    # Lowest confidence across all verified tracks is surfaced (the floor).
    assert "confidence 3+" in message


def test_accuraterip_verdict_partial_is_warn() -> None:
    log = RipLog(
        tracks=(
            _track(1, v1=_ar(1, 14)),
            # Not in DB: confidence None on v1, no v2.
            _track(2, v1=_ar(1, None, "Track not present in AccurateRip database")),
        )
    )
    message, level = accuraterip_verdict(log)
    assert level == "warn"
    assert "1 of 2" in message


def test_accuraterip_verdict_confidence_zero_is_not_a_match() -> None:
    # A "not present" track sometimes logs confidence 0 — that is NOT a match,
    # so it must never count toward "verified" (the honesty rule).
    log = RipLog(tracks=(_track(1, v1=_ar(1, 0, "not present")),))
    message, level = accuraterip_verdict(log)
    assert level == "neutral"
    assert "none of these tracks matched" in message


def test_accuraterip_verdict_none_matched_is_neutral() -> None:
    # Audio tracks present (Copy CRC) but none in the DB → neutral, not a
    # failure — this is the normal CD-R case.
    log = RipLog(tracks=(TrackResult(number=1, copy_crc="ABCD1234"),))
    _, level = accuraterip_verdict(log)
    assert level == "neutral"


def test_accuraterip_verdict_empty_is_blank() -> None:
    # No audio tracks parsed → show nothing (empty message).
    message, _ = accuraterip_verdict(RipLog())
    assert message == ""
    # A pure data track (no CRC, no AR) doesn't count as audio either.
    data_only = RipLog(tracks=(TrackResult(number=1, status="data track (skipped)"),))
    assert accuraterip_verdict(data_only)[0] == ""


def test_set_rip_log_shows_verdict_banner(qapp: QApplication) -> None:
    # isHidden() reflects the explicit setVisible() intent without needing the
    # parent shown (isVisible() is always False on an unshown widget tree).
    widget = RipProgress()
    assert widget._verdict_banner.isHidden() is True
    widget.set_rip_log(RipLog(tracks=(_track(1, v1=_ar(1, 9)),)))
    assert widget._verdict_banner.isHidden() is False
    assert "Bit-perfect" in widget._verdict_banner.text()


def test_set_rip_log_hides_banner_when_no_audio(qapp: QApplication) -> None:
    widget = RipProgress()
    widget.set_rip_log(RipLog(tracks=(_track(1, v1=_ar(1, 9)),)))  # show it first
    widget.set_rip_log(RipLog())  # then a log with nothing to assert
    assert widget._verdict_banner.isHidden() is True


def test_set_ctdb_status_shows_label(qapp: QApplication) -> None:
    widget = RipProgress()
    assert widget._ctdb_label.isVisible() is False
    widget.set_ctdb_status("Verifying against CTDB…")
    assert widget._ctdb_label.text() == "Verifying against CTDB…"


def test_set_ctdb_result_renders_verdict(qapp: QApplication) -> None:
    widget = RipProgress()
    widget.set_ctdb_result(CtdbVerifyResult(Verdict.NOT_IN_DATABASE))
    assert "database" in widget._ctdb_label.text()


def test_clear_hides_ctdb_label(qapp: QApplication) -> None:
    widget = RipProgress()
    widget.set_ctdb_result(CtdbVerifyResult(Verdict.NO_MATCH))
    widget.clear()
    assert widget._ctdb_label.text() == ""
    assert widget._ctdb_label.isVisible() is False


# --- Read-effort footnote + AR/CTDB reconciliation + tooltip (0.4.24) --------


def test_read_effort_summary_line_flags_heavy_reread() -> None:
    from platterpus.ui.rip_progress import read_effort_summary_line

    log = RipLog(
        tracks=(
            TrackResult(1, copy_crc="AA", rip_count=1),
            TrackResult(2, copy_crc="BB", secure_rerip_converged=False),
            TrackResult(3, copy_crc="CC", rip_count=5),
        )
    )
    line = read_effort_summary_line(log)
    assert "2" in line and "3" in line
    assert "re-read" in line.lower()


def test_read_effort_summary_line_empty_when_clean() -> None:
    from platterpus.ui.rip_progress import read_effort_summary_line

    log = RipLog(tracks=(TrackResult(1, copy_crc="AA", rip_count=1),))
    assert read_effort_summary_line(log) == ""


def test_read_effort_summary_line_never_raises() -> None:
    from platterpus.ui.rip_progress import read_effort_summary_line

    assert read_effort_summary_line(object()) == ""


def test_set_rip_log_shows_read_effort_label(qapp: QApplication) -> None:
    widget = RipProgress()
    log = RipLog(tracks=(TrackResult(2, copy_crc="BB", secure_rerip_converged=False),))
    widget.set_rip_log(log)
    # isHidden(), not isVisible() — isVisible() is always False on an unshown
    # widget tree (matches the loudness/verdict-banner tests above).
    assert widget._read_effort_label.isHidden() is False
    assert "2" in widget._read_effort_label.text()


def test_set_rip_log_hides_read_effort_label_when_clean(qapp: QApplication) -> None:
    widget = RipProgress()
    widget.set_rip_log(RipLog(tracks=(TrackResult(1, copy_crc="AA", rip_count=1),)))
    assert widget._read_effort_label.isHidden() is True


def test_ctdb_no_match_shows_reconciliation(qapp: QApplication) -> None:
    widget = RipProgress()
    # 12 verified + 2 offset-variant, then a validated CTDB no-match.
    tracks = tuple(
        TrackResult(
            n, copy_crc=f"{n:08X}", accuraterip_v2=AccurateRipResult(2, confidence=200)
        )
        for n in range(1, 13)
    ) + (
        TrackResult(
            13, copy_crc="AA", accuraterip_offset=AccurateRipResult(450, confidence=200)
        ),
        TrackResult(
            14, copy_crc="BB", accuraterip_offset=AccurateRipResult(450, confidence=200)
        ),
    )
    widget.set_rip_log(RipLog(tracks=tracks))
    widget.set_ctdb_result(
        CtdbVerifyResult(verdict=Verdict.NO_MATCH, confidence=100, crc_validated=True)
    )
    assert widget._ctdb_reconcile_label.isHidden() is False
    assert "offset-variant" in widget._ctdb_reconcile_label.text()


def test_ctdb_match_hides_reconciliation(qapp: QApplication) -> None:
    widget = RipProgress()
    widget.set_rip_log(
        RipLog(
            tracks=(
                TrackResult(
                    1, copy_crc="AA", accuraterip_v2=AccurateRipResult(2, confidence=9)
                ),
            )
        )
    )
    widget.set_ctdb_result(
        CtdbVerifyResult(verdict=Verdict.MATCH, confidence=9, crc_validated=True)
    )
    assert widget._ctdb_reconcile_label.isHidden() is True


def test_offset_variant_cells_get_a_tooltip(qapp: QApplication) -> None:
    from platterpus.ui.rip_progress import _AR_COL_V1, OFFSET_VARIANT_TOOLTIP

    widget = RipProgress()
    log = RipLog(
        tracks=(
            TrackResult(
                1,
                copy_crc="AA",
                accuraterip_offset=AccurateRipResult(450, confidence=200),
            ),
        )
    )
    widget.set_rip_log(log)
    item = widget._ar_table.item(0, _AR_COL_V1)
    assert item.toolTip() == OFFSET_VARIANT_TOOLTIP


# --- Re-rip comparison banner (0.4.24) --------------------------------------


def _mk_comparison(differing: int, level: str, summary: str = "summary text"):
    from platterpus.rip_compare import RipComparison

    return RipComparison(
        label_a="A",
        label_b="B",
        disc_key_a="D",
        disc_key_b="D",
        same_disc=True,
        tracks=(),
        identical_count=0,
        differing_count=differing,
        total=0,
        a_better_tracks=(),
        b_better_tracks=(),
        headline_level=level,
        summary=summary,
    )


def test_comparison_banner_text_identical_is_ok() -> None:
    from platterpus.ui.rip_progress import comparison_banner_text

    text, level = comparison_banner_text(_mk_comparison(0, "ok", "All 5 identical."))
    assert level == "ok"
    assert text.startswith("✓")
    assert "All 5 identical." in text
    assert "--compare" not in text  # no CLI hint when nothing differs


def test_comparison_banner_text_differing_adds_cli_hint() -> None:
    from platterpus.ui.rip_progress import comparison_banner_text

    text, level = comparison_banner_text(_mk_comparison(2, "warn", "2 differ."))
    assert level == "warn"
    assert text.startswith("⚠")
    assert "--compare" in text and "--assemble-best-of" in text


def test_comparison_banner_text_empty_on_none() -> None:
    from platterpus.ui.rip_progress import comparison_banner_text

    assert comparison_banner_text(None) == ("", "neutral")
    assert comparison_banner_text(object()) == ("", "neutral")


def test_set_comparison_shows_and_hides(qapp: QApplication) -> None:
    widget = RipProgress()
    widget.set_comparison(_mk_comparison(1, "warn", "1 differs."))
    assert widget._comparison_label.isHidden() is False
    assert "1 differs." in widget._comparison_label.text()
    # None hides it again.
    widget.set_comparison(None)
    assert widget._comparison_label.isHidden() is True


def test_read_effort_summary_line_threshold_boundary() -> None:
    from platterpus.ui.rip_progress import read_effort_summary_line

    # 2 passes → benign (no footnote); 3 → flagged.
    assert (
        read_effort_summary_line(
            RipLog(tracks=(TrackResult(1, copy_crc="AA", rip_count=2),))
        )
        == ""
    )
    assert "1" in read_effort_summary_line(
        RipLog(tracks=(TrackResult(1, copy_crc="AA", rip_count=3),))
    )


# --- Focus-safe live announcements (a11y gap #4) ----------------------------
#
# Every announcement goes through platterpus.ui.accessibility.announce, which
# rip_progress imports by name — so the module attribute is the monkeypatch
# target (the "patch where it's looked up" lesson, docs/architecture.md §5.1).


def _capture_announcements(monkeypatch) -> list[str]:
    heard: list[str] = []
    monkeypatch.setattr(
        "platterpus.ui.rip_progress.announce",
        lambda _source, message: heard.append(message) or True,
    )
    return heard


def test_status_announces_once_per_phase_not_per_percent(
    qapp: QApplication, monkeypatch
) -> None:
    """The status label redraws constantly (percent/ETA); a screen reader must
    hear each PHASE once — new percent silent, new track announced."""
    heard = _capture_announcements(monkeypatch)
    widget = RipProgress()

    widget.set_status("Ripping track 1 of 14… 0%")
    widget.set_status("Ripping track 1 of 14… 50%")
    widget.set_status("Ripping track 1 of 14… 99%")
    widget.set_status("Ripping track 2 of 14… 0%")

    assert heard == ["Ripping track 1 of 14", "Ripping track 2 of 14"]


def test_clear_resets_the_status_announcement_throttle(
    qapp: QApplication, monkeypatch
) -> None:
    """A new rip's first phase must be announced even when it matches the
    previous rip's last announced phase — and clearing itself says nothing."""
    heard = _capture_announcements(monkeypatch)
    widget = RipProgress()

    widget.set_status("Starting rip… ")
    widget.clear()
    widget.set_status("Starting rip… ")

    assert heard == ["Starting rip", "Starting rip"]


def test_verdict_banner_and_read_effort_are_announced(
    qapp: QApplication, monkeypatch
) -> None:
    heard = _capture_announcements(monkeypatch)
    widget = RipProgress()

    widget.set_rip_log(
        RipLog(
            tracks=(
                TrackResult(
                    1,
                    copy_crc="AA",
                    rip_count=5,
                    accuraterip_v1=AccurateRipResult(1, confidence=9),
                ),
            )
        )
    )

    # The trust headline is announced verbatim…
    assert any(m.startswith("✓") for m in heard)
    # …and the heavy-re-read warning too (rip_count 5 trips the footnote).
    assert any("re-read" in m or "re-reading" in m for m in heard)


def test_ctdb_line_is_announced_once_per_distinct_text(
    qapp: QApplication, monkeypatch
) -> None:
    heard = _capture_announcements(monkeypatch)
    widget = RipProgress()

    widget.set_ctdb_status("Verifying against CTDB…")
    widget.set_ctdb_status("Verifying against CTDB…")  # re-render: silent
    widget.set_ctdb_result(
        CtdbVerifyResult(Verdict.MATCH, confidence=8, crc_validated=True)
    )

    assert heard == [
        "Verifying against CTDB…",
        "CTDB: verified ✓ (confidence 8)",
    ]


def test_comparison_banner_is_announced(qapp: QApplication, monkeypatch) -> None:
    heard = _capture_announcements(monkeypatch)
    widget = RipProgress()

    class _Comparison:
        summary = "13 of 14 tracks byte-identical; 1 differs."
        headline_level = "warn"
        differing_count = 1

    widget.set_comparison(_Comparison())

    assert len(heard) == 1
    assert "previous rip" in heard[0]


# --- Layout: a sentence's length must not set the pane's minimum width -------
#
# Real-hardware report, 2026-07-28: "it looked good when the window was
# maximized, but when smaller was all over the place" — the CTDB and album
# loudness lines were drawn on top of the AccurateRip table.
#
# Cause: `_status_label` was the one label in this pane without word wrap, and an
# un-wrapped QLabel's minimum width is the width of its entire single line. That
# minimum propagates up to the window, so the pane refused to be narrower than
# the longest status it had ever displayed (906 px, against 366 px for "Idle.").
# Below that width the layout could not comply and the contents overflowed.
#
# These tests pin the *invariant* rather than a pixel number, so they hold
# regardless of platform font metrics: **making the text longer must not make the
# pane's minimum width larger.**

_LONG_STATUS: str = (
    "00:54:33 · Done — all 14 tracks ripped cleanly, no read errors. "
    "AccurateRip: 13/14 verified. 1 track partially accurate (offset-variant "
    "match). Read stability: track 5 needed heavy re-reading and may not be "
    "reproducible; re-rip to confirm. See the report for the full breakdown."
)

# A wrapped label's minimum width is its longest *word*, which is irreducible.
# So the invariant is that the *number* of words is what must not matter: same
# vocabulary, ten times the sentence.
_STATUS_WORDS: str = "done all tracks ripped cleanly with no read errors at all "


def test_a_long_status_does_not_widen_the_pane(qapp: QApplication) -> None:
    pane = RipProgress()
    pane.set_status(_STATUS_WORDS)
    narrow = pane.minimumSizeHint().width()

    pane.set_status(_STATUS_WORDS * 10)
    wide = pane.minimumSizeHint().width()

    assert wide == narrow, (
        "the status line's length is driving the pane's minimum width "
        f"({narrow} px → {wide} px). An un-wrapped QLabel reports its whole "
        "line as its minimum, which stops the window being resized narrower "
        "and makes the layout overflow onto its neighbours."
    )


def test_every_message_label_in_the_pane_wraps(qapp: QApplication) -> None:
    """The general rule, so a new label can't reintroduce the bug.

    Any label that holds a *sentence* must wrap. Short fixed captions (the
    "Overall" bar label) are exempt — they are a couple of words and never grow.
    """
    pane = RipProgress()
    pane.set_status(_LONG_STATUS)
    unwrapped = [
        label.text()
        for label in pane.findChildren(QLabel)
        if not label.wordWrap() and len(label.text()) > 24
    ]
    assert not unwrapped, (
        f"these labels hold a sentence but do not word-wrap: {unwrapped}. "
        "Call setWordWrap(True) — see the comment on _status_label."
    )


# --- Vertical overflow: the pane must never paint over itself ----------------
# The width tests above fixed a real problem but not the one the user saw. The
# reported symptom — "looked good when the window was maximized, but when
# smaller was all over the place" — is a *vertical* deficit, and it needs its own
# invariant, because a QVBoxLayout with less height than its children's minimums
# does not clip and does not scroll: it overflows, and overflowing means the
# children's rectangles collide and paint over each other.
#
# Measured on the real widgets with the real hardware rip log: this pane
# reported a minimum height of 326 px while the height it actually allocated at
# 940 px wide was ~405 px, because a word-wrapped QLabel's *minimumSizeHint* is
# one line while its *heightForWidth* is two or three. Below 326 px the verdict
# banner was drawn across the live-log box and the CTDB line across the
# AccurateRip table's first row (hardware report, 2026-07-28).


def _overlapping_sibling_pairs(root: QWidget) -> tuple[list[str], int]:
    """Return (descriptions of overlapping sibling pairs, widgets examined).

    Compares only true siblings — a container legitimately contains its
    children, so parent/child intersection is not a defect. The widget count is
    returned so the caller can prove the walk actually looked at something: the
    first version of this detector walked the pane's own layout, which after the
    fix holds a single item (the scroll area), and it therefore reported "no
    overlaps" for a pane that was still broken. A detector that cannot fail is
    worse than no detector.
    """
    by_parent: dict[QWidget, list[QWidget]] = {}
    examined = 0
    for widget in root.findChildren(QWidget):
        if widget.layout() is not None or not widget.isVisibleTo(root):
            continue  # containers position children; invisible ones paint nothing
        examined += 1
        by_parent.setdefault(widget.parentWidget(), []).append(widget)

    clashes: list[str] = []
    for siblings in by_parent.values():
        for i in range(len(siblings)):
            for j in range(i + 1, len(siblings)):
                first, second = siblings[i].geometry(), siblings[j].geometry()
                if first.intersects(second):
                    clashes.append(
                        f"{type(siblings[i]).__name__}"
                        f"({siblings[i].accessibleName() or '?'}) "
                        f"y{first.top()}..{first.bottom()} overlaps "
                        f"{type(siblings[j]).__name__}"
                        f"({siblings[j].accessibleName() or '?'}) "
                        f"y{second.top()}..{second.bottom()}"
                    )
    return clashes, examined


def _populate_like_a_finished_rip(pane: RipProgress) -> None:
    """Drive the pane into the state the hardware screenshot showed.

    Every long string here is one the user actually had on screen — a partially
    accurate disc with an unstable track, which is what makes three separate
    multi-line warnings visible at once.
    """
    pane.set_status(
        "20:04:22 · ⚠ Read stability: track 3 still didn't read identically even "
        "after an automatic re-rip — kept the best read, which may not be "
        "bit-perfect. Clean the disc and try again for a verified copy. See the "
        "report."
    )
    pane.set_progress(100.0, 100.0)
    pane.append_log_line("Cover art: embedded in 14 track(s).")
    pane.append_log_line("FLAC verify: all 14 file(s) decode cleanly.")
    pane._verdict_banner.setText(
        "⚠ 12 of 14 tracks verified exactly against AccurateRip; the other 2 "
        "matched an offset-variant pressing (partially accurate — see the "
        "table) — this rip is very likely a good copy."
    )
    pane._verdict_banner.setVisible(True)
    pane._read_effort_label.setText(
        "⚠ Track(s) 3, 5 needed heavy re-reading; the read may not be "
        "reproducible; re-rip to confirm."
    )
    pane._read_effort_label.setVisible(True)
    pane._ctdb_label.setText(
        "CTDB: no match at the standard alignment — CTDB also holds "
        "offset-shifted pressings and this check only tests the standard one."
    )
    pane._ctdb_label.setVisible(True)
    pane._ctdb_reconcile_label.setText(
        "Why this and AccurateRip seem to disagree: 2 track(s) matched only an "
        "offset-variant pressing, so the whole-disc CTDB CRC won't match the "
        "database's — this is the SAME finding as Accurip 450 above, not a "
        "separate problem."
    )
    pane._ctdb_reconcile_label.setVisible(True)
    pane._loudness_label.setText(
        "Album loudness: -13.9 LUFS integrated, range 8.9 LU, true peak "
        "0.8 dBFS · 2/2 tracks ripped partially accurately"
    )
    pane._loudness_label.setVisible(True)
    pane._ar_table.setRowCount(14)


def test_the_pane_never_paints_its_children_over_each_other(
    qapp: QApplication,
) -> None:
    """The invariant that actually describes the v0.5.15 bug.

    Not "does it look right" — that needs a screen. Two sibling widgets whose
    rectangles intersect is text drawn on top of text, and that is checkable
    with no window shown and no screenshot.

    Every tab is made current in turn, because widgets in a background tab are
    not visible and are therefore (correctly) skipped by the detector — checking
    only the default tab would leave two thirds of the pane unexamined.
    """
    pane = RipProgress()
    _populate_like_a_finished_rip(pane)

    # 200 px is deliberately absurd. The pane must degrade to a scrollbar, not
    # to a collision, at any size a window manager can impose.
    for height in (620, 420, 320, 260, 200):
        pane.resize(940, height)
        pane.show()
        qapp.processEvents()
        for index in range(pane._tabs.count()):
            pane._tabs.setCurrentIndex(index)
            qapp.processEvents()
            pane.layout().activate()
            qapp.processEvents()

            clashes, examined = _overlapping_sibling_pairs(pane)
            tab = pane._tabs.tabText(index)
            assert examined >= 8, (
                f"the overlap detector only examined {examined} widgets on the "
                f"{tab!r} tab, so it cannot see this bug — the pane's structure "
                "changed and this test has gone vacuous. Fix the walk, don't "
                "delete the test."
            )
            assert not clashes, (
                f"at 940x{height} on the {tab!r} tab the pane paints children on "
                "top of each other:\n  " + "\n  ".join(clashes)
            )
    pane.hide()


def test_the_pane_can_be_made_short_without_a_fight(qapp: QApplication) -> None:
    """A tall report must not impose a tall window.

    One rejected fix for the overlap — teaching every wrapped label to report its
    true height-for-width — removed the overlap but drove this pane's minimum
    height to 1418 px, i.e. it demanded a window taller than most screens. So pin
    that the minimum stays modest.

    The bound is 260 px rather than the 200 px of v0.5.15 because the fixed
    header now deliberately holds the trust headline and the read-effort warning:
    those two are the "is this rip good?" answer and they are never scrolled away
    or hidden behind a tab, which costs about 45 px of guaranteed height. That is
    a considered trade, not drift — if this number needs to grow again, check
    that whatever is being added really belongs in the *fixed* band.
    """
    pane = RipProgress()
    _populate_like_a_finished_rip(pane)
    pane.resize(940, 620)
    pane.show()
    qapp.processEvents()

    minimum = pane.minimumSizeHint().height()
    pane.hide()
    assert minimum <= 260, (
        f"the pane demands at least {minimum} px of height. A variable-length "
        "report must scroll, not dictate the window size."
    )


# --- One scroll surface, never nested ----------------------------------------
# The v0.5.15 scroll area fixed the overlap and created a new complaint: "the 2
# scroll bars in the lower right are difficult to use together". Measured on the
# real widget, a 940x400 pane had two vertical scrollbars 15 px apart (x=911 and
# x=926), the inner one nested inside the outer one's scrolled content.
#
# Nesting is the specific defect, not the count: a nested scroll area steals the
# wheel, and — measured — one that has nothing left to scroll does not even pass
# the wheel on to its parent, so "just turn the inner scrollbar off" trades a
# visible bar for a dead wheel zone. These tests pin the structural property that
# rules both out.


def _live_scrollbars(pane: QWidget) -> list[str]:
    """Scrollbars that are visible AND have somewhere to scroll."""
    from PySide6.QtWidgets import QAbstractScrollArea, QScrollBar

    out: list[str] = []
    for bar in pane.findChildren(QScrollBar):
        if not (bar.isVisible() and bar.maximum() > bar.minimum()):
            continue
        owner: QWidget | None = bar.parentWidget()
        while owner is not None and not isinstance(owner, QAbstractScrollArea):
            owner = owner.parentWidget()
        name = type(owner).__name__ if owner is not None else "?"
        out.append(f"{name}@x{bar.mapTo(pane, bar.rect().topLeft()).x()}")
    return out


def _nested_scroll_areas(pane: QWidget) -> list[str]:
    """Scroll areas living inside another scroll area's scrolled content.

    A QHeaderView is a QAbstractScrollArea and is always inside its table; that
    is Qt's own construction, not a nesting mistake, so it is excluded.
    """
    from PySide6.QtWidgets import QAbstractScrollArea, QHeaderView

    out: list[str] = []
    for inner in pane.findChildren(QAbstractScrollArea):
        if isinstance(inner, QHeaderView):
            continue
        parent: QWidget | None = inner.parentWidget()
        while parent is not None:
            if isinstance(parent, QAbstractScrollArea) and parent is not inner:
                if not isinstance(parent, QHeaderView):
                    out.append(f"{type(inner).__name__} inside {type(parent).__name__}")
                break
            parent = parent.parentWidget()
    return out


def test_the_pane_never_shows_two_scrollbars_at_once(qapp: QApplication) -> None:
    """At most one scrollbar, on any tab, at any size.

    This is the maintainer's complaint stated as a checkable property. It is
    measured with a realistic console (hundreds of lines) because a six-line log
    has nothing to scroll and would make the test pass for the wrong reason.
    """
    pane = RipProgress()
    _populate_like_a_finished_rip(pane)
    for i in range(400):
        pane.append_log_line(f"log line {i}: realistic post-rip console volume")

    seen_any = 0
    for width, height in ((1900, 980), (940, 700), (940, 500), (940, 400), (940, 300)):
        pane.resize(width, height)
        pane.show()
        qapp.processEvents()
        for index in range(pane._tabs.count()):
            pane._tabs.setCurrentIndex(index)
            qapp.processEvents()
            pane.layout().activate()
            qapp.processEvents()
            bars = _live_scrollbars(pane)
            seen_any += len(bars)
            assert len(bars) <= 1, (
                f"at {width}x{height} the {pane._tabs.tabText(index)!r} tab shows "
                f"{len(bars)} scrollbars at once: {bars}. Two scroll surfaces in "
                "one view are what the maintainer reported as 'difficult to use "
                "together'."
            )
    pane.hide()
    # Vacuity floor: "at most one" is trivially true if the walk never finds a
    # scrollbar at all. It must find some — the console alone has 400 lines.
    assert seen_any > 0, (
        "the walk found no live scrollbars anywhere, so 'at most one' proves "
        "nothing — either the detector broke or the content stopped scrolling."
    )


def test_no_scroll_surface_is_nested_inside_another(qapp: QApplication) -> None:
    """The structural rule, which is stronger than counting bars.

    A nested scroll area is the real defect: the wheel lands on whichever surface
    the pointer happens to be over, and an inner one with nothing left to scroll
    swallows the wheel entirely instead of passing it outwards (measured). So no
    scroll area in this pane may contain another.
    """
    pane = RipProgress()
    _populate_like_a_finished_rip(pane)
    pane.resize(940, 400)
    pane.show()
    qapp.processEvents()

    nested = _nested_scroll_areas(pane)
    # Guard against the walk finding nothing because the pane stopped having
    # scroll areas at all — then this test would pass vacuously forever.
    from PySide6.QtWidgets import QAbstractScrollArea

    total = [
        w
        for w in pane.findChildren(QAbstractScrollArea)
        if type(w).__name__ != "QHeaderView"
    ]
    pane.hide()
    assert len(total) >= 2, (
        f"only {len(total)} scroll area(s) found, so this test cannot detect "
        "nesting any more — the pane's structure changed. Fix the walk."
    )
    assert not nested, "these scroll surfaces are nested inside another: " + ", ".join(
        nested
    )


def test_the_live_log_is_shown_during_a_rip_and_results_at_the_end(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The tabs must follow the rip, so the user never clicks to see 'now'.

    A tab that has to be found is worse than a cramped column, so the pane
    switches itself: the console while ripping, the per-track results when the
    log lands.
    """
    pane = RipProgress()
    pane.clear()
    pane.begin_rip(tmp_path, tmp_path / "log.txt")
    qapp.processEvents()
    assert pane._tabs.currentWidget() is pane._log_view, (
        "during a rip the live console should be showing, not an empty table"
    )

    pane.set_rip_log(
        RipLog(
            log_creator="cyanrip 0.9.3",
            tracks=(_track(1),),
        )
    )
    qapp.processEvents()
    assert pane._tabs.currentWidget() is pane._ar_table, (
        "when the rip log lands the per-track results should come to the front"
    )


def test_an_empty_result_set_does_not_swap_away_from_the_log(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Don't replace a console that has output with a blank grid.

    If the rip produced no per-track rows, the log is the only thing that can
    explain why — so switching to an empty table would hide the evidence.
    """
    pane = RipProgress()
    pane.clear()
    pane.begin_rip(tmp_path, tmp_path / "log.txt")
    pane.append_log_line("cyanrip: could not read the disc")
    qapp.processEvents()

    pane.set_rip_log(RipLog(log_creator="cyanrip 0.9.3", tracks=()))
    qapp.processEvents()
    assert pane._tabs.currentWidget() is pane._log_view, (
        "with no tracks to show, the pane should stay on the log"
    )


def test_a_caveat_in_the_details_tab_is_marked_on_the_tab_label(
    qapp: QApplication,
) -> None:
    """A tab must not be a place where warnings go to hide.

    The single-column layout showed every caveat whether you wanted it or not.
    Tabs buy one scroll surface at the cost of that, so the tab label carries a
    marker the moment something lands behind it — otherwise the user has to click
    a tab to discover they should have clicked it.
    """
    pane = RipProgress()
    plain = pane._tabs.tabText(1)
    assert "⚠" not in plain, "a fresh pane has no caveats, so no marker"

    pane.set_ctdb_status("Verifying against CTDB…")
    qapp.processEvents()
    marked = pane._tabs.tabText(1)
    assert "⚠" in marked, (
        f"the Details tab holds a CTDB line but its label is {marked!r} — a user "
        "who never opens the tab has no way to know there is something in it"
    )

    pane.clear()
    qapp.processEvents()
    assert "⚠" not in pane._tabs.tabText(1), (
        "clearing the pane must drop the marker, or it points at a caveat that "
        "no longer exists"
    )
