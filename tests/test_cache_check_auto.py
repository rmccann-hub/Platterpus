"""The drive's audio-cache check runs by itself, once per drive (TASKS R53).

The cache-defeat verdict fills the EAC-compatible log's "Defeat audio cache" line,
and log checkers take points off when it is missing. It used to be measured only
when the user pressed *Analyze cache*; the owner's rule of 2026-11-12 is that drive
properties are tested once, up front, and saved per drive. These tests hold:

* the pure decision (`cache_check_plan`): start with a disc and no verdict; wait
  without a disc or while the drive is busy; never with a saved verdict; again
  after a firmware change;
* the dialog: it really starts the worker on show, and only then; Skip check kills
  the worker's child; closing mid-check stops the thread and the child;
* the window: it hands the dialog the right inputs, wakes a waiting dialog when a
  disc is read, stamps the firmware beside a verdict, and says so (without a box
  and without a probe) when a rip starts on a drive with no verdict.

Hardware is still the proof that ``cd-paranoia -A`` itself starts and is killed
on the rig; here the child is a stand-in Python process run through the same
`KillableCommand` the real probe uses.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable, Generator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from conftest import stop_window_threads
from PySide6.QtWidgets import QApplication, QMessageBox
from test_accessibility_standards import STATUS_MARKERS
from test_ui_main_window import (
    _PIONEER,
    _PIONEER_FP,
    _make_window,
    _params_unknown,
    _pin_pioneer,
)

from platterpus import cache_check_plan
from platterpus.adapters.rip_backend import RipBackend
from platterpus.cache_check_plan import (
    FIRMWARE_CHANGED,
    MEASURED,
    NOT_MEASURED,
    NOTHING,
    START,
    WAIT_FOR_DISC,
    WAIT_FOR_DRIVE,
    decide_auto_check,
    rip_start_note,
    verdict_state,
)
from platterpus.drive_profile_store import DriveProfileStore
from platterpus.drive_profiles import DriveProfile, OffsetSource
from platterpus.killable import KillableCommand
from platterpus.ui import message_boxes
from platterpus.ui.drive_setup_dialog import DriveSetupDialog
from platterpus.workers import abandoned_thread_count
from platterpus.workers.drive_setup_worker import DriveSetupResult

# --- The pure decision ------------------------------------------------------


def _profile(cache: bool | None = None, measured_under: str = "") -> DriveProfile:
    return DriveProfile(
        fingerprint="vm:x",
        vendor="PIONEER",
        model="BDR-209D",
        release="1.0",
        cache_defeat=cache,
        cache_defeat_release=measured_under,
    )


def test_verdict_state_reads_the_profile_and_the_firmware_it_was_measured_under() -> (
    None
):
    assert verdict_state(None, "1.0") == NOT_MEASURED
    assert verdict_state(_profile(None), "1.0") == NOT_MEASURED
    assert verdict_state(_profile(True, "1.0"), "1.0") == MEASURED
    assert verdict_state(_profile(False, "1.0"), "1.0") == MEASURED
    # A firmware update since the measurement re-opens it.
    assert verdict_state(_profile(True, "1.0"), "1.10") == FIRMWARE_CHANGED
    # A verdict saved before the firmware was recorded beside it: kept, because
    # a missing field is not evidence the drive changed.
    assert verdict_state(_profile(True, ""), "1.10") == MEASURED
    # A drive that does not report firmware now: nothing to compare.
    assert verdict_state(_profile(True, "1.0"), "") == MEASURED


def _decide(**overrides: Any) -> cache_check_plan.AutoCheckDecision:
    inputs: dict[str, Any] = {
        "can_analyze": True,
        "verdict": NOT_MEASURED,
        "audio_disc_present": True,
        "drive_busy": False,
        "already_attempted": False,
    }
    inputs.update(overrides)
    return decide_auto_check(**inputs)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, START),
        ({"verdict": FIRMWARE_CHANGED}, START),
        ({"verdict": MEASURED}, NOTHING),
        ({"verdict": None}, NOTHING),
        ({"can_analyze": False}, NOTHING),
        ({"already_attempted": True}, NOTHING),
        ({"audio_disc_present": False}, WAIT_FOR_DISC),
        ({"drive_busy": True}, WAIT_FOR_DRIVE),
        # A saved verdict wins over every disc/drive state.
        ({"verdict": MEASURED, "audio_disc_present": False}, NOTHING),
        ({"verdict": MEASURED, "drive_busy": True}, NOTHING),
    ],
)
def test_decide_auto_check(overrides: dict[str, Any], expected: str) -> None:
    assert _decide(**overrides).action == expected


def test_every_auto_check_message_carries_a_status_marker() -> None:
    """WCAG 1.4.1: the line's meaning is never carried by colour alone."""
    messages = [
        _decide(**overrides).message
        for overrides in (
            {},
            {"verdict": FIRMWARE_CHANGED},
            {"audio_disc_present": False},
            {"drive_busy": True},
        )
    ]
    notes = [
        rip_start_note(can_analyze=True, verdict=v)
        for v in (NOT_MEASURED, FIRMWARE_CHANGED)
    ]
    texts = [m for m in messages + notes if m]
    assert len(texts) == 6, "floor: every non-silent branch produced a sentence"
    for text in texts:
        assert text[0] in STATUS_MARKERS, text
    # The nothing-to-do branches say nothing.
    assert _decide(verdict=MEASURED).message == ""


def test_rip_start_note_only_when_the_user_could_act_on_it() -> None:
    assert rip_start_note(can_analyze=True, verdict=MEASURED) is None
    assert rip_start_note(can_analyze=False, verdict=NOT_MEASURED) is None
    note = rip_start_note(can_analyze=True, verdict=NOT_MEASURED)
    assert note is not None and "Set up drive" in note and "unaffected" in note


def test_the_firmware_beside_a_verdict_survives_the_store(tmp_path: Path) -> None:
    """Round-trips, and a file written before the field existed loads as "" (so
    its verdict still counts as measured, `verdict_state`)."""
    path = tmp_path / "drive_profiles.json"
    store = DriveProfileStore()
    store.upsert(_profile(True, "1.51"))
    store.save(path)
    assert DriveProfileStore.load(path).get("vm:x") == _profile(True, "1.51")

    text = path.read_text(encoding="utf-8")
    assert '"cache_defeat_release": "1.51"' in text
    path.write_text(
        text.replace('"cache_defeat_release": "1.51",', ""), encoding="utf-8"
    )
    old = DriveProfileStore.load(path).get("vm:x")
    assert old is not None and old.cache_defeat is True
    assert old.cache_defeat_release == ""


# --- The dialog ---------------------------------------------------------------


class _CacheBackend(RipBackend):
    """Mirrors cyanrip: measures the cache, has no offset finder. Records every
    analysis it is asked for; answers at once."""

    def __init__(self, verdict: bool | None = True) -> None:
        self.devices: list[str] = []
        self._verdict: bool | None = verdict

    def list_drives(self):  # type: ignore[no-untyped-def,override]
        return []

    def disc_info(self, drive):  # type: ignore[no-untyped-def,override]
        raise NotImplementedError

    def rip(self, *a, **kw):  # type: ignore[no-untyped-def,override]
        raise NotImplementedError

    def version(self) -> str:
        return "fake"

    def supports_offset_detection(self) -> bool:
        return False

    def supports_cache_analysis(self) -> bool:
        return True

    def analyze_drive(self, device: str) -> bool | None:
        self.devices.append(device)
        return self._verdict


class _SlowProbeBackend(_CacheBackend):
    """The real shape of the cancel path: the analysis is a child process run
    through a `KillableCommand` (as `cache_probe` runs ``cd-paranoia -A``), and
    `cancel_setup` cancels that command (as `CyanripBackend.cancel_setup` does).

    The child writes its pid and then sleeps for a minute, so a test that sees it
    gone in seconds has seen it killed, not finish.
    """

    def __init__(self, pid_file: Path) -> None:
        super().__init__(verdict=None)
        self._pid_file: Path = pid_file
        self.command: KillableCommand = KillableCommand("test cache probe")

    def analyze_drive(self, device: str) -> bool | None:
        self.devices.append(device)
        script = (
            "import os, sys, time; "
            "open(sys.argv[1], 'w').write(str(os.getpid())); time.sleep(60)"
        )
        self.command.run(
            [sys.executable, "-c", script, str(self._pid_file)], timeout=90
        )
        return None

    def cancel_setup(self) -> None:
        self.command.cancel()


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # exists, but not ours (a reused pid)
        return True
    return True


@pytest.fixture()
def dialogs(qapp: QApplication) -> Generator[Callable[..., DriveSetupDialog]]:
    """Build dialogs and close every one afterwards (the production close path,
    which cancels and stops the worker thread)."""
    made: list[DriveSetupDialog] = []

    def factory(backend: RipBackend, **kwargs: Any) -> DriveSetupDialog:
        dialog = DriveSetupDialog(backend, "/dev/sr0", **kwargs)
        made.append(dialog)
        return dialog

    yield factory
    for dialog in made:
        dialog.reject()
        dialog.deleteLater()


def test_the_check_starts_by_itself_on_show_with_a_disc_and_no_verdict(
    dialogs: Callable[..., DriveSetupDialog], process_until: Any
) -> None:
    backend = _CacheBackend(verdict=True)
    dialog = dialogs(backend, cache_verdict=NOT_MEASURED, audio_disc_present=True)
    recorded: list[DriveSetupResult] = []
    dialog.detection_recorded.connect(recorded.append)
    assert backend.devices == [], "constructing the window must not read the disc"

    dialog.show()

    assert process_until(lambda: bool(recorded), timeout=5.0), (
        "the cache check did not start by itself on show"
    )
    assert backend.devices == ["/dev/sr0"]
    assert recorded[0].can_defeat_cache is True
    assert process_until(lambda: dialog._thread is None, timeout=5.0)
    # Once per window: a second show starts nothing more.
    dialog.hide()
    dialog.show()
    process_until(lambda: False, timeout=0.2)
    assert backend.devices == ["/dev/sr0"]


@pytest.mark.parametrize(
    ("kwargs", "note_part"),
    [
        ({"cache_verdict": MEASURED, "audio_disc_present": True}, ""),
        ({}, ""),  # a caller that does not say: the old, button-only behaviour
        (
            {"cache_verdict": NOT_MEASURED, "audio_disc_present": False},
            "Insert any audio CD",
        ),
        (
            {
                "cache_verdict": NOT_MEASURED,
                "audio_disc_present": True,
                "drive_busy": True,
            },
            "finished reading the disc",
        ),
    ],
)
def test_the_check_does_not_start_with_a_saved_verdict_no_disc_or_a_busy_drive(
    dialogs: Callable[..., DriveSetupDialog],
    process_until: Any,
    kwargs: dict[str, Any],
    note_part: str,
) -> None:
    backend = _CacheBackend()
    dialog = dialogs(backend, **kwargs)
    dialog.show()
    process_until(lambda: False, timeout=0.2)

    assert backend.devices == []
    assert dialog._thread is None
    if note_part:
        assert not dialog._auto_note_label.isHidden()
        assert note_part in dialog._auto_note_label.text()
    else:
        assert dialog._auto_note_label.isHidden()
    if kwargs.get("cache_verdict") == MEASURED:
        # Re-measuring is the user's choice, and the button says so.
        assert dialog._detect_button is not None
        assert dialog._detect_button.text() == "Re-analy&ze cache"


def test_a_waiting_dialog_starts_when_the_window_reads_a_disc_in_its_drive(
    dialogs: Callable[..., DriveSetupDialog], process_until: Any
) -> None:
    backend = _CacheBackend(verdict=False)
    dialog = dialogs(backend, cache_verdict=NOT_MEASURED, audio_disc_present=False)
    dialog.show()
    assert dialog.notify_disc_ready("/dev/sr1") == NOTHING  # another drive
    assert backend.devices == []

    assert dialog.notify_disc_ready("/dev/sr0") == START
    assert process_until(lambda: dialog._thread is None, timeout=5.0)
    assert backend.devices == ["/dev/sr0"]
    # Measured: nothing more is due, however many discs arrive.
    assert dialog.notify_disc_ready("/dev/sr0") == NOTHING
    assert backend.devices == ["/dev/sr0"]


def test_an_inconclusive_automatic_run_is_not_repeated_in_the_same_window(
    dialogs: Callable[..., DriveSetupDialog], process_until: Any
) -> None:
    backend = _CacheBackend(verdict=None)
    dialog = dialogs(backend, cache_verdict=NOT_MEASURED, audio_disc_present=True)
    dialog.show()
    assert process_until(lambda: bool(backend.devices), timeout=5.0)
    assert process_until(lambda: dialog._thread is None, timeout=5.0)
    assert dialog.notify_disc_ready("/dev/sr0") == NOTHING
    assert backend.devices == ["/dev/sr0"]
    # The button still runs it on request.
    assert dialog._detect_button is not None
    dialog._detect_button.click()
    assert process_until(lambda: len(backend.devices) == 2, timeout=5.0)


def test_the_offset_can_still_be_saved_while_the_cache_check_runs(
    dialogs: Callable[..., DriveSetupDialog], process_until: Any, tmp_path: Path
) -> None:
    """A cache-only run reports no offset, so it locks nothing: the automatic
    check takes minutes and the user may have opened the window for the offset."""
    backend = _SlowProbeBackend(tmp_path / "pid")
    dialog = dialogs(backend, cache_verdict=NOT_MEASURED, audio_disc_present=True)
    dialog.show()
    assert process_until((tmp_path / "pid").exists, timeout=10.0)
    assert dialog._save_offset_button.isEnabled()
    assert dialog._offset_spin.isEnabled()


def test_skip_check_kills_the_workers_child_and_says_so(
    dialogs: Callable[..., DriveSetupDialog], process_until: Any, tmp_path: Path
) -> None:
    pid_file = tmp_path / "pid"
    backend = _SlowProbeBackend(pid_file)
    dialog = dialogs(backend, cache_verdict=NOT_MEASURED, audio_disc_present=True)
    recorded: list[DriveSetupResult] = []
    dialog.detection_recorded.connect(recorded.append)
    dialog.show()
    assert process_until(
        lambda: pid_file.exists() and pid_file.read_text() != "", timeout=10.0
    ), "the stand-in probe never started"
    pid = int(pid_file.read_text())
    assert _alive(pid)
    assert dialog._skip_button is not None and dialog._skip_button.isVisible()

    started = time.monotonic()
    dialog._skip_button.click()

    assert process_until(lambda: dialog._thread is None, timeout=10.0), (
        "Skip check did not end the run"
    )
    # The child sleeps 60 s: gone in well under that means killed.
    assert time.monotonic() - started < 10.0
    assert process_until(lambda: not _alive(pid), timeout=5.0), "the child survived"
    assert not backend.command.is_running()
    assert dialog._status_label.text() == "Check stopped."
    assert "nothing was saved" in dialog._results_label.toPlainText()
    assert recorded == [], "a stopped check must not record a verdict"
    assert not dialog._skip_button.isVisible()


def test_closing_mid_check_stops_the_thread_and_the_child(
    dialogs: Callable[..., DriveSetupDialog],
    process_until: Any,
    thread_has_stopped: Any,
    tmp_path: Path,
) -> None:
    """CLAUDE.md rule 9: a dialog that owns a running QThread must stop it on
    close, and a cancel that only sets a flag is a false promise — so the child
    itself must be gone, not merely asked."""
    pid_file = tmp_path / "pid"
    backend = _SlowProbeBackend(pid_file)
    dialog = dialogs(backend, cache_verdict=NOT_MEASURED, audio_disc_present=True)
    dialog.show()
    assert process_until(
        lambda: pid_file.exists() and pid_file.read_text() != "", timeout=10.0
    )
    pid = int(pid_file.read_text())
    thread = dialog._thread
    assert thread is not None and thread.isRunning()

    dialog.reject()  # the Close button / Esc

    assert dialog._thread is None
    assert process_until(lambda: thread_has_stopped(thread), timeout=5.0)
    assert abandoned_thread_count() == 0, "the thread was abandoned, not stopped"
    assert process_until(lambda: not _alive(pid), timeout=5.0), "the child survived"


# --- The window -------------------------------------------------------------


@pytest.fixture()
def window(qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> Generator[Any]:
    made = _make_window(qapp)
    _pin_pioneer(made, monkeypatch)
    monkeypatch.setattr(made._backend, "supports_cache_analysis", lambda: True)
    yield made
    stop_window_threads(made)
    made.deleteLater()


class _RecordingDialog:
    """Stands in for DriveSetupDialog at the window's call site: records how it
    was built and what it was told, and returns from exec() at once."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.kwargs: dict[str, Any] = kwargs
        self.notified: list[str] = []
        self.open_during_exec: object = None
        for name in (
            "manual_offset_saved",
            "offset_applied_changed",
            "detection_recorded",
        ):
            setattr(self, name, _Signal())

    def exec(self) -> int:
        self.open_during_exec = self.window._drive_setup_dialog
        return 0

    def notify_disc_ready(self, device: str) -> str:
        self.notified.append(device)
        return START


class _Signal:
    def connect(self, _slot: object) -> None:
        return None


def test_the_window_hands_the_dialog_the_drives_state(
    window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    made: list[_RecordingDialog] = []

    def build(*args: Any, **kwargs: Any) -> _RecordingDialog:
        dialog = _RecordingDialog(*args, **kwargs)
        dialog.window = window  # type: ignore[attr-defined]
        made.append(dialog)
        return dialog

    monkeypatch.setattr("platterpus.ui.main_window_drive.DriveSetupDialog", build)
    monkeypatch.setattr(window._drive_picker, "current_device", lambda: "/dev/sr0")

    window._current_num_tracks = 12
    window._on_drive_setup()
    assert made[-1].kwargs["cache_verdict"] == NOT_MEASURED
    assert made[-1].kwargs["audio_disc_present"] is True
    assert made[-1].kwargs["drive_busy"] is False
    # The window knows the dialog while it is open, and forgets it after.
    assert made[-1].open_during_exec is made[-1]
    assert window._drive_setup_dialog is None

    window._record_drive_fact(
        _PIONEER, source=OffsetSource.OFFSET_FIND, cache_defeat=True
    )
    window._current_num_tracks = 0
    window._on_drive_setup()
    assert made[-1].kwargs["cache_verdict"] == MEASURED
    assert made[-1].kwargs["audio_disc_present"] is False


def test_a_disc_read_wakes_an_open_dialog_only_for_an_audio_cd(window: Any) -> None:
    dialog = _RecordingDialog()
    window._drive_setup_dialog = dialog
    try:
        window._tell_drive_setup_disc_ready("/dev/sr0", 0)
        assert dialog.notified == []
        window._tell_drive_setup_disc_ready("/dev/sr0", 12)
        assert dialog.notified == ["/dev/sr0"]
    finally:
        window._drive_setup_dialog = None
    # No dialog open: nothing to tell, and nothing raises.
    window._tell_drive_setup_disc_ready("/dev/sr0", 12)


def test_a_verdict_is_stamped_with_the_firmware_it_was_measured_under(
    window: Any,
) -> None:
    window._record_drive_fact(
        _PIONEER, source=OffsetSource.OFFSET_FIND, cache_defeat=True
    )
    profile = window._drive_profiles.get(_PIONEER_FP)
    assert profile is not None and profile.cache_defeat_release == "1.0"

    # A later sighting under new firmware rewrites `release`, not the stamp, so
    # the change is visible — and the check is due again.
    updated = replace(_PIONEER, release="1.10")
    window._record_drive_fact(updated)
    profile = window._drive_profiles.get(_PIONEER_FP)
    assert profile is not None
    assert profile.release == "1.10"
    assert profile.cache_defeat_release == "1.0"
    assert verdict_state(profile, updated.release) == FIRMWARE_CHANGED


def test_a_rip_on_a_drive_with_no_verdict_starts_and_shows_a_dismissible_note(
    window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Never blocks the rip, never starts the probe: the rip reaches its worker,
    no analysis ran, and the status bar carries a marked, dismissible note."""
    monkeypatch.setattr(
        "platterpus.ui.main_window_rip.is_offset_configured", lambda _o: True
    )
    analyses: list[str] = []
    monkeypatch.setattr(window._backend, "analyze_drive", analyses.append)
    started: list[object] = []
    monkeypatch.setattr(window, "_start_rip_worker", started.append)
    monkeypatch.setattr(message_boxes, "information", lambda *a, **k: None)
    monkeypatch.setattr(
        "platterpus.ui.message_boxes.warning",
        lambda *a, **k: QMessageBox.StandardButton.No,
    )

    window._on_rip_requested(_params_unknown())

    assert started, "floor: the rip never reached the worker"
    assert analyses == [], "a rip must not start the cache probe by itself"
    note = window._cache_check_note
    label = window._cache_check_note_label
    assert note is not None and label is not None
    assert not note.isHidden()
    assert label.text()[0] in STATUS_MARKERS
    assert "Set up drive" in label.text()

    from PySide6.QtWidgets import QPushButton

    buttons = note.findChildren(QPushButton)
    assert len(buttons) == 1
    buttons[0].click()
    assert note.isHidden(), "Dismiss did not dismiss"


def test_no_note_once_the_drive_has_a_verdict_and_a_new_verdict_hides_it(
    window: Any,
) -> None:
    window._note_cache_check_at_rip_start()
    assert window._cache_check_note is not None
    assert not window._cache_check_note.isHidden()

    window._on_detection_recorded(DriveSetupResult(can_defeat_cache=True))
    assert window._cache_check_note.isHidden()

    window._note_cache_check_at_rip_start()
    assert window._cache_check_note.isHidden()


def test_the_disc_read_success_slot_wakes_the_open_dialog(
    window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The wiring, through the slot a real disc read lands in: a dialog that is
    waiting for a CD is told when the window reads one."""
    from platterpus.parsers.cd_info import DiscInfo

    monkeypatch.setattr(window, "open_unknown_album_dialog", lambda: False)
    dialog = _RecordingDialog()
    window._drive_setup_dialog = dialog
    try:
        window._on_disc_info_ready("/dev/sr0", DiscInfo(num_tracks=16))
    finally:
        window._drive_setup_dialog = None
    assert dialog.notified == ["/dev/sr0"]


def test_a_note_that_changes_after_show_keeps_the_dialog_on_a_short_screen(
    dialogs: Callable[..., DriveSetupDialog], process_until: Any, tmp_path: Path
) -> None:
    """The automatic line appears after the base class has fitted the window to
    the screen (on show) and changes again when the check ends. Refitting the
    minimum for it must not outgrow a short screen: the conformance matrix
    caught exactly that (a 586 px dialog on a 533 px screen), from a no-op note
    on show. Here the line really changes, on a 600 px screen."""
    from PySide6.QtCore import QSize

    backend = _SlowProbeBackend(tmp_path / "pid")
    dialog = dialogs(backend, cache_verdict=NOT_MEASURED, audio_disc_present=True)
    dialog.available_screen_size = lambda: QSize(1024, 600)  # type: ignore[method-assign]  # test seam
    dialog.show()
    assert process_until((tmp_path / "pid").exists, timeout=10.0)
    assert not dialog._auto_note_label.isHidden(), "floor: the line is showing"
    limit = 600 - DriveSetupDialog.SCREEN_MARGIN_PX
    assert dialog.minimumHeight() <= limit, dialog.minimumHeight()
    assert dialog.height() <= limit, dialog.height()
