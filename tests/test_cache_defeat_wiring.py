"""Unit tests for the cache-defeat verdict's pure wiring (KDD-29).

The display formatter and the rip-log injection are exercised here WITHOUT a
full MainWindow: the formatter is a module function, and the injection method is
called against a tiny fake `self` carrying only the three attributes it touches.
This keeps the honest-verdict rules under test cheaply (the end-to-end drive-scan
→ probe → record → render path is the hardware-gated part).
"""

from __future__ import annotations

from types import SimpleNamespace

from platterpus.drive_profiles import DriveProfile, OffsetSource
from platterpus.parsers.rip_log import RipLog, RippingInfo
from platterpus.ui.main_window_drive import _format_cache_defeat
from platterpus.ui.main_window_rip import RipMixin

# --- _format_cache_defeat (pure display) ------------------------------------


def test_format_cache_defeat_measured_yes() -> None:
    profile = DriveProfile(
        fingerprint="vm:x",
        vendor="PIONEER",
        model="BDR-209D",
        cache_defeat=True,
        cache_defeat_source=OffsetSource.OFFSET_FIND,
    )
    text = _format_cache_defeat(profile)
    assert text.startswith("Yes")
    assert "measured" in text


def test_format_cache_defeat_measured_no() -> None:
    profile = DriveProfile(
        fingerprint="vm:x", vendor="v", model="m", cache_defeat=False
    )
    assert _format_cache_defeat(profile).startswith("No")


def test_format_cache_defeat_unmeasured() -> None:
    # No profile, or a profile with no verdict → honest "not measured", never Yes.
    assert "not measured" in _format_cache_defeat(None)
    profile = DriveProfile(fingerprint="vm:x", vendor="v", model="m")
    assert "not measured" in _format_cache_defeat(profile)


# --- _inject_measured_cache_defeat (fold the measured verdict into a RipLog) -


def _fake_window(cache_defeat: bool | None) -> SimpleNamespace:
    """A minimal stand-in exposing only what the injector reads."""
    drive = SimpleNamespace(vendor="PIONEER", model="BDR-209D", device="/dev/sr0")
    profile = (
        DriveProfile(
            fingerprint="vm:x", vendor="v", model="m", cache_defeat=cache_defeat
        )
        if cache_defeat is not None
        else DriveProfile(fingerprint="vm:x", vendor="v", model="m")
    )
    return SimpleNamespace(
        _drive_picker=SimpleNamespace(current_drive=lambda: drive),
        _fingerprint_for=lambda d: ("vm:x", "", ""),
        _drive_profiles=SimpleNamespace(get=lambda fp: profile),
    )


def _log_with_cache(value: bool | None) -> RipLog:
    return RipLog(ripping_info=RippingInfo(defeat_audio_cache=value))


def test_injects_measured_verdict_when_log_has_none() -> None:
    window = _fake_window(cache_defeat=True)
    out = RipMixin._inject_measured_cache_defeat(window, _log_with_cache(None))
    assert out.ripping_info.defeat_audio_cache is True


def test_never_overwrites_a_value_the_log_already_carried() -> None:
    # A log that already reported the fact (e.g. a real EAC/whipper log) is left
    # exactly as parsed — we only FILL a missing value, never replace real data.
    window = _fake_window(cache_defeat=True)
    out = RipMixin._inject_measured_cache_defeat(window, _log_with_cache(False))
    assert out.ripping_info.defeat_audio_cache is False


def test_no_measurement_leaves_log_unknown() -> None:
    window = _fake_window(cache_defeat=None)
    out = RipMixin._inject_measured_cache_defeat(window, _log_with_cache(None))
    assert out.ripping_info.defeat_audio_cache is None


def test_injection_never_raises_without_a_drive() -> None:
    # No selected drive → return the log untouched, never crash the finish path.
    window = SimpleNamespace(
        _drive_picker=SimpleNamespace(current_drive=lambda: None),
        _fingerprint_for=lambda d: ("vm:x", "", ""),
        _drive_profiles=SimpleNamespace(get=lambda fp: None),
    )
    log = _log_with_cache(None)
    assert RipMixin._inject_measured_cache_defeat(window, log) is log
