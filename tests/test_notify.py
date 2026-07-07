"""Tests for platterpus.notify — the rip-completion notification text builder.

Only the pure (title, body) builder is tested here; the actual send is a
best-effort QSystemTrayIcon call on the GUI side that degrades to a no-op with
no tray/daemon (exercised by the main-window tests, not this Qt-free module)."""

from __future__ import annotations

from platterpus.notify import build_completion_message


def test_success_uses_detail_as_body() -> None:
    title, body = build_completion_message(
        True, False, "All 14 tracks verified against AccurateRip."
    )
    assert title == "Platterpus — rip complete"
    assert body == "All 14 tracks verified against AccurateRip."


def test_failure_uses_detail_and_failed_title() -> None:
    title, body = build_completion_message(False, False, "Track 3 couldn't be read.")
    assert title == "Platterpus — rip didn't finish"
    assert body == "Track 3 couldn't be read."


def test_cancelled_has_its_own_title() -> None:
    title, body = build_completion_message(False, True, "")
    assert title == "Platterpus — rip cancelled"
    assert "cancel" in body.lower()


def test_blank_detail_falls_back_to_a_generic_line() -> None:
    # An empty/whitespace detail must never produce an empty notification body.
    _, body_ok = build_completion_message(True, False, "   ")
    _, body_fail = build_completion_message(False, False, "")
    assert body_ok.strip()
    assert body_fail.strip()
    assert "success" in body_ok.lower()
