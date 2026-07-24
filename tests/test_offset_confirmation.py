"""Unit tests for the AccurateRip-confirmed read offset (KDD-31).

The RipMixin helper `_confirm_offset_from_accuraterip` is exercised against a
tiny fake `self` (no full MainWindow), the same lightweight pattern as the
cache-defeat wiring tests. The rule under test: a rip that matched AccurateRip
records the applied offset as an independent ACCURATERIP_CONFIRMED fact, and
only then — never for a no-match rip, and never when no offset override applies.
"""

from __future__ import annotations

from types import SimpleNamespace

from platterpus.drive_profiles import OffsetSource
from platterpus.parsers.rip_log import AccurateRipResult, RipLog, TrackResult
from platterpus.ui.main_window_rip import RipMixin


def _verified_track() -> TrackResult:
    return TrackResult(
        number=1,
        accuraterip_v2=AccurateRipResult(
            version=2, result="accurately ripped, confidence 5", confidence=5
        ),
    )


def _unmatched_track() -> TrackResult:
    return TrackResult(
        number=1,
        accuraterip_v1=AccurateRipResult(
            version=1, result="not found", confidence=None
        ),
    )


def _fake_window(*, override: bool, offset: int = 667):
    recorded: list[dict] = []
    drive = SimpleNamespace(vendor="PIONEER", model="BDR-209D", device="/dev/sr0")

    def record(d, *, offset_value=None, source=None, cache_defeat=None):  # type: ignore[no-untyped-def]
        recorded.append({"offset_value": offset_value, "source": source})

    window = SimpleNamespace(
        _config=SimpleNamespace(override_read_offset=override, read_offset=offset),
        _drive_picker=SimpleNamespace(current_drive=lambda: drive),
        _record_drive_fact=record,
        _refresh_drive_profile_display=lambda: None,
        _recorded=recorded,
    )
    return window


def test_records_confirmation_when_a_track_matched() -> None:
    window = _fake_window(override=True, offset=667)
    RipMixin._confirm_offset_from_accuraterip(
        window, RipLog(tracks=(_verified_track(),))
    )
    assert window._recorded == [
        {"offset_value": 667, "source": OffsetSource.ACCURATERIP_CONFIRMED}
    ]


def test_no_confirmation_when_nothing_matched() -> None:
    window = _fake_window(override=True)
    RipMixin._confirm_offset_from_accuraterip(
        window, RipLog(tracks=(_unmatched_track(),))
    )
    assert window._recorded == []  # a CD-R / unlisted disc confirms nothing


def test_no_confirmation_without_an_offset_override() -> None:
    # No explicit offset applied → nothing to attribute to this drive.
    window = _fake_window(override=False)
    RipMixin._confirm_offset_from_accuraterip(
        window, RipLog(tracks=(_verified_track(),))
    )
    assert window._recorded == []


def test_never_raises_on_a_garbage_log() -> None:
    window = _fake_window(override=True)
    RipMixin._confirm_offset_from_accuraterip(window, object())
    assert window._recorded == []
