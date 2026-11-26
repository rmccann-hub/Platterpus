"""The window offers to rebuild an approved cyanrip built without the release option.

TASKS R249 / PLANNING KDD-49: 0.7.130's setup wizard compiled the approved pin
without `-Ddeclare_released=true`, so its logs say `NOT a released build` while
we score it approved (the owner's two Full runs of 2026-11-25 and 26). Updating
Platterpus does not rebuild it, so the window offers to, after a rip shows it.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from platterpus import handshake_approval
from platterpus.deps import fork_source

_UNDECLARED = "round 41 lap 5 OPEN, verdict GO -- NOT a released build"
_DECLARED = "round 41 lap 5 OPEN, verdict GO -- released build"


def _log(note: str, *, pin: str = fork_source.FORK_PIN) -> SimpleNamespace:
    return SimpleNamespace(
        log_creator=f"cyanrip {fork_source.FORK_EXPECTED_VERSION}",
        ripper_build=f"platterpus-fork-g{pin}",
        handshake_note=note,
    )


def test_only_an_approved_build_that_is_not_declared_released_is_offered() -> None:
    assert handshake_approval.approve_rip_log(_log(_UNDECLARED)).verdict == (
        handshake_approval.APPROVED
    ), "floor: the stand-in must read as the approved build"
    assert handshake_approval.rebuild_offer(_log(_UNDECLARED)).startswith("ⓘ")
    assert handshake_approval.rebuild_offer(_log(_DECLARED)) == ""
    assert handshake_approval.rebuild_offer(_log("")) == ""
    assert handshake_approval.rebuild_offer(_log(_UNDECLARED, pin="abc1234")) == ""
    assert handshake_approval.rebuild_offer(object()) == ""


@pytest.fixture()
def window(qapp: Any) -> Any:
    from conftest import stop_window_threads
    from test_ui_main_window import _make_window

    win = _make_window(qapp)
    yield win
    stop_window_threads(win)
    win.deleteLater()


def test_the_window_offers_once_and_rebuilds_the_approved_pin(
    window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    installs: list[tuple[object, str]] = []
    monkeypatch.setattr(
        window,
        "_begin_ripper_install",
        lambda offer, commit: installs.append((offer, commit)),
    )
    window._offer_ripper_rebuild(_log(_DECLARED))
    assert window._ripper_rebuild_note is None, "a declared build needs nothing"

    window._offer_ripper_rebuild(_log(_UNDECLARED))
    note = window._ripper_rebuild_note
    assert note is not None and not note.isHidden()
    window._offer_ripper_rebuild(_log(_UNDECLARED))
    assert window._ripper_rebuild_note is note, "offered once per launch"

    # Never during a rip.
    monkeypatch.setattr(window, "_rip_thread", object(), raising=False)
    window._on_rebuild_ripper_clicked()
    assert installs == []
    assert "rip is running" in window.statusBar().currentMessage()

    monkeypatch.setattr(window, "_rip_thread", None, raising=False)
    window._on_rebuild_ripper_clicked()
    assert installs == [(None, fork_source.FORK_PIN)]
    assert note.isHidden()
