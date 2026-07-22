"""Tests for platterpus.ui.disc_info_panel."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from platterpus.adapters.musicbrainz_client import ReleaseSummary
from platterpus.parsers.cd_info import DiscInfo
from platterpus.parsers.drive_list import DriveDescriptor
from platterpus.parsers.rip_log import AccurateRipResult, RipLog, TrackResult
from platterpus.ui.disc_info_panel import DiscInfoPanel, format_drive_summary


def _track(number: int, *, matched: bool) -> TrackResult:
    """A TrackResult whose AccurateRip v1 either matched or wasn't in the DB.

    A real match always carries a confidence ≥ 1 (how many submitted rips
    share the CRC); a "not present" track has no confidence — mirror that so
    the fixture exercises the real confidence-based verification rule.
    """
    if matched:
        ar = AccurateRipResult(version=1, result="Found, exact match", confidence=12)
    else:
        ar = AccurateRipResult(
            version=1, result="Track not present in AccurateRip database"
        )
    return TrackResult(number=number, accuraterip_v1=ar)


def _release(
    mbid: str = "x",
    title: str = "Album",
    artist: str = "Artist",
) -> ReleaseSummary:
    return ReleaseSummary(mbid=mbid, title=title, artist_credit=artist)


# --- Initial state -------------------------------------------------------


def test_default_state_shows_placeholders(qapp: QApplication) -> None:
    panel = DiscInfoPanel()

    assert panel._drive_value.text() == "(no drive)"
    assert panel._mb_id_value.text() == "—"
    assert panel._cddb_id_value.text() == "—"
    assert panel._mb_match_value.text() == "—"
    # AccurateRip is a post-rip fact — blank until a rip log lands, never a
    # premature "verified".
    assert panel._accuraterip_value.text() == "—"


def test_value_labels_have_accessible_names(qapp: QApplication) -> None:
    # Each value sits beside a cosmetic QFormLayout label that a screen reader
    # can't tie to the value, so every value carries its own accessible name
    # (a11y, principle #10).
    panel = DiscInfoPanel()
    assert panel._drive_value.accessibleName()
    assert panel._mb_id_value.accessibleName()
    assert panel._cddb_id_value.accessibleName()
    assert panel._mb_match_value.accessibleName()
    assert panel._accuraterip_value.accessibleName()
    assert panel._offset_value.accessibleName()


# --- Drive selection -----------------------------------------------------


def test_set_drive_updates_label(qapp: QApplication) -> None:
    panel = DiscInfoPanel()
    panel.set_drive("/dev/sr0")
    assert panel._drive_value.text() == "/dev/sr0"


def test_set_drive_shows_make_model_firmware(qapp: QApplication) -> None:
    """With the full descriptor, the panel identifies the exact drive —
    make, model, firmware, and device — not just the /dev node."""
    panel = DiscInfoPanel()
    panel.set_drive(
        "/dev/sr0",
        DriveDescriptor(
            device="/dev/sr0",
            vendor="PIONEER",
            model="BD-RW  BDR-209D",  # sysfs double-spacing is collapsed
            release="1.51",
        ),
    )
    assert (
        panel._drive_value.text() == "PIONEER BD-RW BDR-209D · firmware 1.51 · /dev/sr0"
    )


def test_format_drive_summary_variants() -> None:
    """The pure formatter: full record, missing firmware, and no record."""
    full = DriveDescriptor(
        device="/dev/sr1", vendor="HL-DT-ST", model="BD-RE WH16NS40", release="1.05"
    )
    assert (
        format_drive_summary(full)
        == "HL-DT-ST BD-RE WH16NS40 · firmware 1.05 · /dev/sr1"
    )
    # A drive whose firmware sysfs node was unreadable ("" release) just omits it.
    no_fw = DriveDescriptor(
        device="/dev/sr0", vendor="PIONEER", model="BDR-209D", release=""
    )
    assert format_drive_summary(no_fw) == "PIONEER BDR-209D · /dev/sr0"
    # No descriptor at all → bare device, then the placeholder.
    assert format_drive_summary(None, "/dev/sr0") == "/dev/sr0"
    assert format_drive_summary(None, None) == "(no drive)"


def test_set_drive_none_shows_placeholder(qapp: QApplication) -> None:
    panel = DiscInfoPanel()
    panel.set_drive("/dev/sr0")
    panel.set_drive(None)
    assert panel._drive_value.text() == "(no drive)"


def test_set_drive_clears_disc_fields(qapp: QApplication) -> None:
    """Switching drives must wipe the previously-loaded disc's info."""
    panel = DiscInfoPanel()
    panel.set_disc_info(
        DiscInfo(
            cddb_disc_id="abc",
            musicbrainz_disc_id="mb-id",
            musicbrainz_submit_url="",
        )
    )
    panel.set_mb_matches([_release()])

    panel.set_drive("/dev/sr1")

    assert panel._mb_id_value.text() == "—"
    assert panel._cddb_id_value.text() == "—"
    assert panel._mb_match_value.text() == "—"


# --- Disc info -----------------------------------------------------------


def test_set_disc_info_loading_shows_status(qapp: QApplication) -> None:
    panel = DiscInfoPanel()
    panel.set_disc_info_loading()

    assert panel._mb_id_value.text() == "…"
    assert panel._cddb_id_value.text() == "…"
    assert panel._mb_match_value.text() == "reading disc…"


def test_set_disc_info_populates_ids(qapp: QApplication) -> None:
    panel = DiscInfoPanel()
    info = DiscInfo(
        cddb_disc_id="940A6A0B",
        musicbrainz_disc_id="wzr8h2ssXg4F2.x8L3KqB9PHevc-",
        musicbrainz_submit_url="https://example",
    )
    panel.set_disc_info(info)

    assert panel._mb_id_value.text() == "wzr8h2ssXg4F2.x8L3KqB9PHevc-"
    assert panel._cddb_id_value.text() == "940A6A0B"


def test_set_disc_info_empty_ids_show_placeholder(
    qapp: QApplication,
) -> None:
    panel = DiscInfoPanel()
    info = DiscInfo()
    panel.set_disc_info(info)

    assert panel._mb_id_value.text() == "—"
    assert panel._cddb_id_value.text() == "—"


def test_set_disc_info_error_shows_message(qapp: QApplication) -> None:
    panel = DiscInfoPanel()
    panel.set_disc_info_error("disc not present")
    assert "disc not present" in panel._mb_match_value.text()


# --- MusicBrainz match ---------------------------------------------------


def test_set_mb_loading_shows_status(qapp: QApplication) -> None:
    panel = DiscInfoPanel()
    panel.set_mb_loading()
    assert panel._mb_match_value.text() == "querying MusicBrainz…"


def test_set_mb_matches_empty_shows_not_in_database(
    qapp: QApplication,
) -> None:
    panel = DiscInfoPanel()
    panel.set_mb_matches([])
    assert panel._mb_match_value.text() == "not in MusicBrainz"


def test_set_mb_matches_single_shows_release_name(
    qapp: QApplication,
) -> None:
    panel = DiscInfoPanel()
    panel.set_mb_matches([_release(artist="Pink Floyd", title="Dark Side")])

    text = panel._mb_match_value.text()
    assert "1 match" in text
    assert "Pink Floyd" in text
    assert "Dark Side" in text


def test_set_mb_matches_multiple_shows_count_and_hint(
    qapp: QApplication,
) -> None:
    panel = DiscInfoPanel()
    panel.set_mb_matches([_release(), _release(mbid="y"), _release(mbid="z")])
    text = panel._mb_match_value.text()
    assert "3 matches" in text
    assert "pick" in text.lower()


def test_set_mb_matches_handles_missing_metadata(
    qapp: QApplication,
) -> None:
    panel = DiscInfoPanel()
    panel.set_mb_matches([_release(title="", artist="")])
    text = panel._mb_match_value.text()
    assert "Unknown Title" in text
    assert "Unknown Artist" in text


def test_set_mb_error_shows_message(qapp: QApplication) -> None:
    panel = DiscInfoPanel()
    panel.set_mb_error("network down")
    text = panel._mb_match_value.text()
    assert "network down" in text


# --- AccurateRip outcome -------------------------------------------------


def test_accuraterip_none_matched_reports_not_in_database(
    qapp: QApplication,
) -> None:
    """A CD-R (nothing in the DB) must NOT read as 'verified'."""
    panel = DiscInfoPanel()
    rip_log = RipLog(tracks=tuple(_track(n, matched=False) for n in range(1, 17)))
    panel.set_accuraterip_result(rip_log)
    assert panel._accuraterip_value.text() == "not in database"


def test_accuraterip_all_matched_reports_verified(qapp: QApplication) -> None:
    panel = DiscInfoPanel()
    rip_log = RipLog(tracks=tuple(_track(n, matched=True) for n in range(1, 4)))
    panel.set_accuraterip_result(rip_log)
    text = panel._accuraterip_value.text()
    assert "verified" in text
    assert "3" in text


def test_accuraterip_partial_match_reports_fraction(
    qapp: QApplication,
) -> None:
    panel = DiscInfoPanel()
    rip_log = RipLog(
        tracks=(
            _track(1, matched=True),
            _track(2, matched=False),
            _track(3, matched=True),
        )
    )
    panel.set_accuraterip_result(rip_log)
    assert panel._accuraterip_value.text() == "2 of 3 tracks matched"


def test_accuraterip_no_tracks_stays_placeholder(qapp: QApplication) -> None:
    panel = DiscInfoPanel()
    panel.set_accuraterip_result(RipLog(tracks=()))
    assert panel._accuraterip_value.text() == "—"


def test_accuraterip_confidence_zero_exact_match_is_not_verified(
    qapp: QApplication,
) -> None:
    """Regression: a confidence-0 'exact match' must NOT read as verified.

    The old string-only check ("exact match" in result) counted this as a
    match while the results-pane banner did not — two surfaces disagreeing on
    the same screen. Both now share the confidence ≥ 1 rule.
    """
    panel = DiscInfoPanel()
    rip_log = RipLog(
        tracks=(
            TrackResult(
                number=1,
                copy_crc="ABCD1234",
                accuraterip_v1=AccurateRipResult(
                    version=1, result="Found, exact match", confidence=0
                ),
            ),
        )
    )
    panel.set_accuraterip_result(rip_log)
    assert panel._accuraterip_value.text() == "not in database"


def test_accuraterip_counts_cyanrip_style_match(qapp: QApplication) -> None:
    """Regression: cyanrip writes 'accurately ripped, confidence N' — no
    'exact match' substring — so the old string check missed EVERY cyanrip
    verification. The confidence-based rule counts it correctly."""
    panel = DiscInfoPanel()
    rip_log = RipLog(
        tracks=(
            TrackResult(
                number=1,
                accuraterip_v1=AccurateRipResult(
                    version=1, result="accurately ripped, confidence 3", confidence=3
                ),
            ),
        )
    )
    panel.set_accuraterip_result(rip_log)
    assert "verified" in panel._accuraterip_value.text()


def test_set_drive_clears_accuraterip_result(qapp: QApplication) -> None:
    """A new disc means the old AccurateRip verdict no longer applies."""
    panel = DiscInfoPanel()
    panel.set_accuraterip_result(RipLog(tracks=(_track(1, matched=True),)))
    panel.set_drive("/dev/sr1")
    assert panel._accuraterip_value.text() == "—"


# --- Lifecycle: drive change after data ----------------------------------


def test_set_drive_called_twice_resets_in_between(
    qapp: QApplication,
) -> None:
    """A user changing drives mid-flow must always see a clean panel."""
    panel = DiscInfoPanel()
    panel.set_drive("/dev/sr0")
    panel.set_disc_info(DiscInfo(cddb_disc_id="aaa", musicbrainz_disc_id="bbb"))
    panel.set_drive("/dev/sr1")
    panel.set_disc_info_loading()

    # The previous disc's IDs must not leak.
    assert "aaa" not in panel._cddb_id_value.text()
    assert "bbb" not in panel._mb_id_value.text()


# --- Read-offset provenance row (UX gap #6) ------------------------------


def test_offset_provenance_row_starts_blank(qapp: QApplication) -> None:
    panel = DiscInfoPanel()
    assert panel._offset_value.text() == "—"


def test_set_drive_offset_provenance_renders(qapp: QApplication) -> None:
    panel = DiscInfoPanel()
    panel.set_drive_offset_provenance("+667 — from the AccurateRip list (medium)")
    assert "+667" in panel._offset_value.text()
    # Accessible name is set so screen readers announce the row (principle #10).
    assert panel._offset_value.accessibleName() == "Read offset provenance"


def test_set_drive_clears_offset_provenance(qapp: QApplication) -> None:
    panel = DiscInfoPanel()
    panel.set_drive_offset_provenance("+667 — measured on this drive (high)")
    panel.set_drive("/dev/sr1")  # picking a new drive clears the stale line
    assert panel._offset_value.text() == "—"


# --- Keyboard reachability + announcements (a11y gap #4) ---------------------


def test_value_labels_are_tab_reachable(qapp: QApplication) -> None:
    """Qt gives keyboard-selectable labels only ClickFocus, so without an
    explicit StrongFocus a keyboard-only user could never Tab to a disc ID to
    copy it — the flag would be dead. Regression for the gap-#4 sweep fix."""
    from PySide6.QtCore import Qt

    panel = DiscInfoPanel()
    for label in (
        panel._drive_value,
        panel._mb_id_value,
        panel._cddb_id_value,
        panel._mb_match_value,
        panel._accuraterip_value,
        panel._offset_value,
    ):
        assert label.focusPolicy() & Qt.FocusPolicy.TabFocus
        assert (
            label.textInteractionFlags()
            & Qt.TextInteractionFlag.TextSelectableByKeyboard
        )


def _capture_announcements(monkeypatch) -> list[str]:
    heard: list[str] = []
    monkeypatch.setattr(
        "platterpus.ui.disc_info_panel.announce",
        lambda _source, message: heard.append(message) or True,
    )
    return heard


def test_mb_outcomes_are_announced(qapp: QApplication, monkeypatch) -> None:
    """Disc identification is the async status the user is waiting on after
    inserting a disc — its outcomes must be audible without focus (gap #4)."""
    heard = _capture_announcements(monkeypatch)
    panel = DiscInfoPanel()

    panel.set_mb_loading()  # transient — deliberately NOT announced
    panel.set_mb_matches([])
    panel.set_mb_error("rate limited")
    panel.set_disc_info_error("no disc")

    assert heard == [
        "MusicBrainz: not in MusicBrainz",
        "MusicBrainz error: rate limited",
        "error: no disc",
    ]


def test_offset_guard_warning_is_announced(qapp: QApplication, monkeypatch) -> None:
    """The wrong-offset guard line is trust-critical; the plain provenance
    line is routine and stays silent."""
    heard = _capture_announcements(monkeypatch)
    panel = DiscInfoPanel()

    panel.set_drive_offset_provenance("+667 — AccurateRip list (medium)")
    panel.set_drive_offset_provenance("⚠ two identical drives share this profile")

    assert heard == ["⚠ two identical drives share this profile"]
