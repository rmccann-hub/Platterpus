"""The scan verbs wait for the scan they started, and answer only its picker.

Run A of the owner's Full test on 0.7.112 (app log of bundle
``platterpusbundle20261021t113505z`` lines 690-710, script lines 892-897):
``rescan`` returned at once, ``pick-release`` answered a picker an earlier scan
had left open, and ``rip`` was refused because the new scan was still reading.
These drive the real runner against the stand-in window, given the two facts
the real window exposes for this: its read-request count and its read thread.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from PySide6.QtCore import QTimer
from test_uiscript_rip_verbs import (
    ReleasePickerDialog,
    _Release,
    _RipControls,
    _step_outcome,
    _window,
    _with_picker,
)

from platterpus.uiscript import scan_verbs
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner

_MBID = "d14a7546-815b-43c6-8af6-35cff6cee1d0"


class _ReadThread:
    """The window's `_disc_info_thread`, as far as the verbs read it."""

    def __init__(self, running: bool = False) -> None:
        self.running = running

    def isRunning(self) -> bool:  # noqa: N802 — Qt spelling
        return self.running


def _scanning_window(**overrides: Any) -> Any:
    """A stand-in window that counts its scans, as `DiscReadRetries` does.

    Its `_on_drive_changed` starts a scan the way the real one does: the
    request number goes up and the read thread runs."""
    win = _window(**overrides)
    win._disc_retries = SimpleNamespace(request=3)
    win._disc_info_thread = _ReadThread()

    def _rescan(device: str) -> None:
        win.rescanned.append(device)
        win._disc_retries.request += 1
        win._disc_info_thread.running = True

    win._on_drive_changed = _rescan
    return win


def test_the_real_window_exposes_what_the_scan_verbs_read() -> None:
    """Floor: the stand-in's two facts exist on the real window, by these names."""
    import inspect

    from platterpus.disc_probe_retry import DiscReadRetries
    from platterpus.ui.main_window import MainWindow

    init = inspect.getsource(MainWindow.__init__)
    assert "self._disc_retries" in init and "self._disc_info_thread" in init
    assert isinstance(DiscReadRetries().request, int)


def test_rescan_waits_for_its_scan_to_identify_the_disc(qapp, process_until) -> None:
    win = _scanning_window()

    def _identified() -> None:
        win._disc_info_thread.running = False
        win._current_release_id = _MBID

    QTimer.singleShot(400, _identified)
    step = _step_outcome(ScriptRunner(win), qapp, process_until, "rescan")
    assert step.outcome is Outcome.PASS, step.detail
    assert win.rescanned == ["/dev/sr0"]
    assert step.elapsed_s >= 0.3, "it returned before its scan finished"
    assert f"release {_MBID}" in step.detail, step.detail


def test_rescan_passes_when_its_own_picker_opens(
    qapp, process_until, monkeypatch
) -> None:
    win = _scanning_window()
    picker = ReleasePickerDialog([_Release(_MBID)] * 4, scan_request=4)
    QTimer.singleShot(300, lambda: _with_picker(monkeypatch, picker))
    step = _step_outcome(ScriptRunner(win), qapp, process_until, "rescan")
    assert step.outcome is Outcome.PASS, step.detail
    assert "release picker is open (4 candidate(s))" in step.detail


def test_rescan_is_not_satisfied_by_an_older_scans_picker(
    qapp, process_until, monkeypatch
) -> None:
    """The picker on screen is scan 3's; the rescan's scan is 4."""
    monkeypatch.setattr(scan_verbs, "RESCAN_WAIT_S", 0.5)
    win = _scanning_window()
    _with_picker(monkeypatch, ReleasePickerDialog([_Release(_MBID)], scan_request=3))
    step = _step_outcome(ScriptRunner(win), qapp, process_until, "rescan")
    assert step.outcome is Outcome.FAIL, step.detail
    assert "had not finished" in step.detail


def test_pick_release_refuses_a_picker_from_a_superseded_scan(
    qapp, process_until, monkeypatch
) -> None:
    """Run A's L893: the picker answered was scan N's, 250 ms into scan N+1."""
    win = _scanning_window()
    win._disc_retries.request = 4
    old = ReleasePickerDialog([_Release(_MBID)], scan_request=3)
    _with_picker(monkeypatch, old)
    step = _step_outcome(ScriptRunner(win), qapp, process_until, "pick-release 1 1")
    assert step.outcome is Outcome.FAIL, step.detail
    assert not old.accepted, "it answered the superseded scan's picker"
    assert "scan 3's" in step.detail and "scan 4" in step.detail, step.detail


def test_pick_release_answers_the_current_scans_picker(
    qapp, process_until, monkeypatch
) -> None:
    win = _scanning_window()
    win._disc_retries.request = 4
    current = ReleasePickerDialog([_Release(_MBID)], scan_request=4)
    _with_picker(monkeypatch, current)
    step = _step_outcome(ScriptRunner(win), qapp, process_until, "pick-release 1 1")
    assert current.accepted, step.detail


def test_rip_waits_for_a_scan_in_flight_then_presses_start(qapp, process_until) -> None:
    """Run A's L897: Start was disabled because the rescan's read was running."""
    controls = _RipControls(startable=False)
    win = _scanning_window(rip_controls=controls)
    win._disc_info_thread.running = True

    def _scan_done() -> None:
        win._disc_info_thread.running = False
        controls._startable = True

    QTimer.singleShot(300, _scan_done)
    step = _step_outcome(ScriptRunner(win), qapp, process_until, "rip")
    assert step.outcome is Outcome.PASS, step.detail
    assert controls.started
    assert "after waiting" in step.detail, step.detail


def test_rip_after_a_scan_still_refuses_a_start_that_stays_disabled(
    qapp, process_until, monkeypatch
) -> None:
    """Waiting is not passing: the same refusal, once the scan and the lookup
    grace are over."""
    monkeypatch.setattr(scan_verbs, "LOOKUP_GRACE_S", 0.2)
    controls = _RipControls(startable=False)
    win = _scanning_window(rip_controls=controls)
    win._disc_info_thread.running = True
    QTimer.singleShot(200, lambda: setattr(win._disc_info_thread, "running", False))
    step = _step_outcome(ScriptRunner(win), qapp, process_until, "rip")
    assert step.outcome is Outcome.FAIL, step.detail
    assert "Start button is not enabled" in step.detail
    assert not controls.started


def test_rip_with_no_scan_in_flight_decides_at_once(qapp, process_until) -> None:
    controls = _RipControls(startable=False)
    win = _scanning_window(rip_controls=controls)
    step = _step_outcome(ScriptRunner(win), qapp, process_until, "rip")
    assert step.outcome is Outcome.FAIL and step.elapsed_s < 0.2, step
