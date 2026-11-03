"""Tests for platterpus.notify — the rip-completion notification text builder.

Only the pure (title, body) builder is tested here; the actual send is a
best-effort QSystemTrayIcon call on the GUI side that degrades to a no-op with
no tray/daemon (exercised by the main-window tests, not this Qt-free module)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from platterpus.notify import build_completion_message, notification_text


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


# --- no markup reaches the notification server (TASKS R87 item 1) -------------

#: Shapes a server advertising `body-markup` would act on: a link, an image
#: fetch, styling, and an entity.
_MARKUP: tuple[str, ...] = (
    '<a href="https://example.invalid">click</a>',
    "<img src='file:///etc/passwd'>",
    "<b>bold</b> <i>it</i> <u>under</u>",
    "Tom &amp; Jerry &lt;3",
)


def test_every_markup_shape_reaches_the_body_as_plain_lookalikes() -> None:
    assert len(_MARKUP) >= 4  # the floor: the loop below cannot pass empty
    for detail in _MARKUP:
        for success in (True, False):
            title, body = build_completion_message(success, False, detail)
            assert not set("<>&") & set(title + body), (detail, body)
            # Every other character survives, in order: only the three move.
            assert body.translate({0x2039: "<", 0x203A: ">", 0xFF06: "&"}) == detail


def test_the_lookalikes_are_the_ones_named() -> None:
    assert notification_text("a<b>c&d") == "a‹b›c＆d"


@given(st.text())
def test_notification_text_never_raises_and_never_carries_markup(text: str) -> None:
    out = notification_text(text)
    assert not set("<>&") & set(out)
    assert len(out) == len(text)
    _, body = build_completion_message(False, False, text)
    assert not set("<>&") & set(body)
