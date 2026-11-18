"""Cancelled, empty and stuck: three states the window now words for the user.

The UX review of 0.7.127 (TASKS R182, wave 1, the owner's plan of 2026-11-17):

* **E2, cancelled** — "Rip cancelled by user. Partial files may remain." said
  nothing about where. The line now names the folder, and an **Open folder**
  button beside the banner opens that same folder. (No "Delete partial files":
  deleting a user's files waits for its own design.)
* **E3, empty** — with no drive the window showed "(no drives found)" over
  seven rows of "—" that read as data. While a listing is empty the disc panel
  is hidden and one line says what to do, naming the real Refresh button; it
  stays out of the way of the setup strip, which already explains a missing
  ripper.
* **M4, Force stop** — sat beside Cancel at equal weight for the whole rip. It
  is now shown during a rip only once a cancel has been asked for, and for the
  whole of a disc scan, which has no Cancel and where it is the only way out.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import stop_window_threads
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
from test_ui_main_window import _make_window

from platterpus.config import Config
from platterpus.finish_wording import (
    cancelled_folder,
    cancelled_status,
    stall_next_step,
)
from platterpus.parsers.drive_list import DriveDescriptor
from platterpus.ui.no_drive_notice import NOTICE_TEXT
from platterpus.ui.rip_controls import RipControls
from platterpus.ui.rip_progress import RipProgress
from platterpus.workers.rip_worker import RipParameters

_DRIVE: DriveDescriptor = DriveDescriptor(
    device="/dev/sr0", vendor="ACME", model="Frobnicator", release="1"
)


@pytest.fixture()
def make_window(qapp: QApplication) -> Iterator[Callable[..., Any]]:
    """A real MainWindow, its threads stopped afterwards."""
    created: list[Any] = []

    def factory(**kwargs: Any) -> Any:
        window = _make_window(qapp, **kwargs)
        created.append(window)
        return window

    yield factory
    for window in created:
        stop_window_threads(window)
        window.deleteLater()


# --- M4: Force stop only where it is the next step ------------------------


def _offered(controls: RipControls) -> bool:
    button = controls._force_stop_button
    # Hidden and enabled must agree: a hidden but enabled button still answers
    # its Alt+O, and a shown but disabled one is a dead end.
    assert button.isHidden() is (not button.isEnabled())
    return not button.isHidden()


def test_force_stop_appears_during_a_rip_only_once_a_cancel_is_asked_for(
    qapp: QApplication,
) -> None:
    controls = RipControls(Config(output_dir="/music"))
    assert _offered(controls) is False  # idle
    controls.set_rip_active(True)
    assert _offered(controls) is False, "beside Cancel at equal weight again"
    assert controls._cancel_button.isEnabled()  # the ordinary way out is there
    controls.set_cancel_requested(True)
    assert _offered(controls) is True
    controls.set_rip_active(False)
    assert _offered(controls) is False
    # The next rip starts without the last one's cancel.
    controls.set_rip_active(True)
    assert _offered(controls) is False


def test_force_stop_stays_for_the_whole_scan_which_has_no_cancel(
    qapp: QApplication,
) -> None:
    controls = RipControls(Config(output_dir="/music"))
    controls.set_scan_active(True)
    assert controls._cancel_button.isEnabled() is False
    assert _offered(controls) is True, "a stuck scan has no other way out"
    controls.set_scan_active(False)
    assert _offered(controls) is False


def test_every_cancel_route_reveals_force_stop(
    make_window: Callable[..., Any],
) -> None:
    """Through the window's `_on_rip_cancel`, which every route calls."""
    window = make_window()
    controls = window._rip_controls
    controls.set_rip_active(True)
    window._rip_worker = SimpleNamespace(
        cancel=lambda: None,
        abandon_log_wait=lambda: None,
        stop_signal_reach=lambda: None,
    )
    try:
        assert _offered(controls) is False
        window._on_rip_cancel()
        assert _offered(controls) is True
        assert "Force stop" in window._rip_progress.current_status()
    finally:
        window._force_stop_timer.stop()


def test_the_stall_notice_sends_the_user_to_the_button_that_is_there() -> None:
    before = stall_next_step(False)
    after = stall_next_step(True)
    assert before.startswith("Press Cancel"), before
    assert "Force stop" in after and "Cancel" not in after, after


# --- E2: cancelled, and where the files are ---------------------------------


def test_the_cancelled_line_names_the_folder_the_button_opens() -> None:
    album = "/music/The Police/Synchronicity"
    with_log = cancelled_status(f"{album}/Synchronicity.log", "/music")
    assert "cancelled" in with_log  # the rig scripts' `expect-status cancelled`
    assert album in with_log, with_log
    assert cancelled_folder(f"{album}/Synchronicity.log", "/music") == Path(album)

    no_log = cancelled_status("", Path("/music"))
    assert "/music" in no_log and "album's folder" in no_log, no_log
    assert cancelled_folder("", Path("/music")) == Path("/music")

    # Nothing names a folder: say so, and offer nothing.
    assert cancelled_folder("", None) is None
    assert "cancelled" in cancelled_status("", None)


def test_open_folder_opens_the_cancelled_folder_and_clears_with_the_next_rip(
    qapp: QApplication, tmp_path: Path
) -> None:
    opened: list[QUrl] = []

    def open_url(url: QUrl) -> bool:
        opened.append(url)
        return True

    progress = RipProgress(open_url=open_url)
    button = progress._open_cancelled_folder_button
    assert button.isHidden()
    progress.offer_cancelled_folder(tmp_path)
    assert not button.isHidden()
    assert "&" in button.text() and button.accessibleName()
    button.click()
    assert [u.toLocalFile() for u in opened] == [str(tmp_path)]
    progress.clear()
    assert button.isHidden()


def test_a_cancelled_rip_says_where_and_offers_the_folder(
    make_window: Callable[..., Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    window = make_window()
    window._rip_worker = SimpleNamespace(failure_hint="")
    window._active_rip_params = RipParameters(
        drive="/dev/sr0",
        release_id="",
        output_dir=tmp_path,
        track_template="t",
        disc_template="d",
        unknown=True,
    )
    window._rip_cancelled = True
    statuses: list[str] = []
    real_set_status = window._rip_progress.set_status

    def record(text: str) -> None:
        statuses.append(text)
        real_set_status(text)

    monkeypatch.setattr(window._rip_progress, "set_status", record)
    window._finish_rip(success=False, log_path="")
    assert statuses, "floor: the finish set no status"
    assert any("cancelled" in s and str(tmp_path) in s for s in statuses), statuses
    assert not window._rip_progress._open_cancelled_folder_button.isHidden()
    assert window._rip_progress._cancelled_folder == tmp_path


# --- E3: no drive, and what to do -----------------------------------------


def test_an_empty_listing_replaces_the_dashes_with_one_line(
    make_window: Callable[..., Any],
) -> None:
    window = make_window()
    picker = window._drive_picker
    panel = window._disc_info_panel
    assert not panel.isHidden()

    picker.populate([])
    notice = window._no_drive_notice
    assert notice is not None, "no empty state was built"
    assert not notice.isHidden()
    assert panel.isHidden(), "the rows of dashes are still there"
    # The sentence names the button that is really there.
    refresh = picker._refresh_button.text().replace("&", "")
    assert f"press {refresh}." in notice.text() and notice.text() == NOTICE_TEXT
    # Directly under the picker, in the page.
    layout = picker.parentWidget().layout()
    assert layout.indexOf(notice) == layout.indexOf(picker) + 1

    picker.populate([_DRIVE])
    assert notice.isHidden() and not panel.isHidden()

    picker.populate([])
    picker.show_error("the container did not answer")
    assert notice.isHidden() and not panel.isHidden(), "a failure is not 'no drive'"


def test_the_empty_state_does_not_repeat_the_setup_strip(
    make_window: Callable[..., Any],
) -> None:
    window = make_window()
    window._drive_picker.populate([])
    notice = window._no_drive_notice
    assert notice is not None and not notice.isHidden()

    window._show_setup_needed_notice()
    assert notice.isHidden(), "two notices for one cause"
    assert window._disc_info_panel.isHidden(), "the dashes are no truer now"

    window._hide_setup_needed_notice()
    assert not notice.isHidden()
