"""Tests for platterpus.ui.rip_progress."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication

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


def test_ctdb_verdict_line_no_match_validated_can_state_it_differs() -> None:
    # Once the CRC algorithm IS validated, a NO_MATCH legitimately means the rip
    # differs from the database — the honesty guard only muzzles the unvalidated
    # case, it doesn't lose the real signal.
    line = ctdb_verdict_line(CtdbVerifyResult(Verdict.NO_MATCH, crc_validated=True))
    assert "differs" in line


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
