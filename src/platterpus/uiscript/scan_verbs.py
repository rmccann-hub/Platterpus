"""The script's disc-scan verbs wait for the scan they started, and only answer it.

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like
:mod:`platterpus.uiscript.offset_verbs`, so the runner file does not grow.

**Why** (the owner's Full run A on 0.7.112, app log of bundle
``platterpusbundle20261021t113505z`` lines 690-710, script lines 892-897).
``rescan`` returned at once, so ``pick-release`` found the picker an EARLIER scan
had left open (one a drive flicker started 338 s before) and answered it 250 ms
into the new scan; ``rip`` then pressed Start while the new scan was still
reading the disc and was refused. Three verbs, one shape: each acted on the state
it found rather than on the scan it was about.

* ``rescan`` waits, bounded, for ITS scan to finish identifying the disc, or for
  ITS picker to open.
* ``pick-release`` refuses a picker that belongs to a superseded scan (the
  picker carries the window's read-request number, ``ReleasePickerDialog.
  scan_request``) and keeps waiting for the current scan's own.
* ``rip`` waits, bounded, for a scan in flight, and then decides exactly as it
  would have without one.

A window that does not count its scans (a test stand-in) reads as "unknown",
and the verbs behave as they did before: nothing here invents a scan to wait for.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Final

from PySide6.QtCore import QTimer

from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript.script import Step

#: How long ``rescan`` waits for its scan. Run A's read and lookup took 15 s
#: (08:02:41.761 to 08:02:57.043); a retried read adds two 4 s delays.
RESCAN_WAIT_S: Final[float] = 120.0
#: How long ``rip`` waits for a scan in flight before pressing Start anyway.
RIP_SCAN_WAIT_S: Final[float] = 120.0
#: After the disc read ends, how long the MusicBrainz lookup (and a single
#: candidate's release fetch) may take to land. Run A's took 0.6 s.
LOOKUP_GRACE_S: Final[float] = 30.0


def scan_request(window: object) -> int | None:
    """The window's disc-read request number (``DiscReadRetries.request``), which
    every Rescan, drive change and insertion advances; None when not counted."""
    value = getattr(getattr(window, "_disc_retries", None), "request", None)
    return value if isinstance(value, int) else None


def scan_running(window: object) -> bool:
    """True while the window's disc read (``DiscInfoWorker``) is in flight."""
    is_running = getattr(getattr(window, "_disc_info_thread", None), "isRunning", None)
    return bool(callable(is_running) and is_running())


def superseded_picker(window: object, dialog: object) -> str:
    """Why ``dialog`` must not be answered, or ``""`` when it may be.

    A picker stamped with an older scan's request than the window's current one
    asks a question nobody is waiting for; its answer was run A's wrong answer.
    """
    asked = getattr(dialog, "scan_request", None)
    current = scan_request(window)
    if not isinstance(asked, int) or current is None or asked >= current:
        return ""
    return (
        f"the release picker open is scan {asked}'s, and scan {current} has started "
        "since (a rescan or a disc read): its answer would be for a scan nobody is "
        "waiting for, so it is not answered, and the current scan's own picker is "
        "waited for instead"
    )


class ScanVerbsMixin:
    """The ``rescan`` handler and the scan waits ``rip``/``pick-release`` share."""

    if TYPE_CHECKING:
        _window: QWidget
        _deadline_outcome: Outcome
        _deadline_detail: str
        _deadline_timeout_detail: str

        def _record(
            self,
            step: Step,
            outcome: Outcome,
            detail: str = "",
            *,
            elapsed: float = 0.0,
            artifact: str = "",
            declined_by_size: bool = False,
        ) -> None: ...

        def _arm_deadline(
            self,
            step: Step,
            seconds: float,
            predicate: Callable[[], bool] | None = None,
        ) -> None: ...

        def _loaded_track_count(self) -> int: ...

    def _do_rescan(self, step: Step) -> None:
        """Re-run the whole disc pipeline (disc info → MusicBrainz) for the drive,
        and wait for it.

        Goes through the window's own `_on_drive_changed`, which is exactly what the
        Rescan button's `drive_changed` signal triggers — rather than poking the
        probe directly, which would skip the wiring the button depends on. Deferred
        like `open`: the scan spawns workers, and returning to the event loop first
        keeps the runner's own tick responsive.
        """
        picker = getattr(self._window, "_drive_picker", None)
        device = picker.current_device() if picker is not None else None
        if not device:
            self._record(
                step,
                Outcome.FAIL,
                "no drive is selected, so there is nothing to rescan",
            )
            return
        handler = getattr(self._window, "_on_drive_changed", None)
        if handler is None:
            self._record(step, Outcome.ERROR, "the window has no _on_drive_changed()")
            return
        before = scan_request(self._window)
        QTimer.singleShot(0, lambda: handler(device))
        if before is None:
            self._record(step, Outcome.PASS, f"rescanning {device}")
            return
        done_at: list[float] = []
        self._arm_deadline(
            step, RESCAN_WAIT_S, lambda: self._rescan_settled(device, before, done_at)
        )
        self._deadline_timeout_detail = (
            f"rescan of {device}: the disc read had not finished after "
            f"{RESCAN_WAIT_S:.0f}s, so later steps would act on a scan in flight"
        )

    def _rescan_settled(self, device: str, before: int, done_at: list[float]) -> bool:
        """One poll of ``rescan``'s wait: True once its scan has an outcome."""
        from platterpus.uiscript import runner as _runner

        current = scan_request(self._window)
        if current is None or current <= before:
            return False  # the deferred handler has not started the scan yet
        dialog = _runner._release_picker()
        if dialog is not None and not superseded_picker(self._window, dialog):
            count = len(getattr(dialog, "_releases", []) or [])
            self._deadline_detail = (
                f"rescanned {device}: its release picker is open ({count} "
                "candidate(s)) for `pick-release` to answer"
            )
            return True
        if scan_running(self._window):
            done_at.clear()  # a retried read: the lookup grace starts again after it
            return False
        if not done_at:
            done_at.append(time.monotonic())
        release = _runner._held_release_id(self._window)
        loaded = self._loaded_track_count()
        if loaded and _runner._MBID_RE.match(release):
            self._deadline_detail = (
                f"rescanned {device}: release {release}, {loaded} track(s) loaded"
            )
            return True
        if _runner._unknown_album_dialog() is not None:
            self._deadline_detail = (
                f"rescanned {device}: MusicBrainz does not know this disc "
                "('Rip as unknown album' is open)"
            )
            return True
        if time.monotonic() - done_at[0] < LOOKUP_GRACE_S:
            return False
        self._deadline_detail = (
            f"rescanned {device}: the disc read finished, and no release was "
            f"identified within {LOOKUP_GRACE_S:.0f}s of it ({loaded} row(s) loaded)"
        )
        return True

    def _wait_for_scan_then(
        self, step: Step, decide: Callable[[], tuple[Outcome, str]]
    ) -> bool:
        """For ``rip``: if a disc scan is in flight, wait for it (bounded), then
        ``decide`` as the verb would have without one. False: no scan; decide now.

        After the read ends, Start stays disabled until the lookup lands, so the
        wait also allows :data:`LOOKUP_GRACE_S` for the controls to say they can
        start. ``decide`` re-checks everything where the press HAPPENS.
        """
        if not scan_running(self._window):
            return False
        done_at: list[float] = []
        waited_from = time.monotonic()

        def ready() -> bool:
            if scan_running(self._window):
                done_at.clear()
                return False
            if not done_at:
                done_at.append(time.monotonic())
            controls = getattr(self._window, "_rip_controls", None)
            can_start = getattr(controls, "can_start", None)
            startable = bool(callable(can_start) and can_start())
            from platterpus.uiscript import runner as _runner

            if (
                not startable
                and _runner._active_dialog() is None
                and time.monotonic() - done_at[0] < LOOKUP_GRACE_S
            ):
                return False
            outcome, detail = decide()
            self._deadline_outcome = outcome
            self._deadline_detail = (
                f"{detail} (after waiting {time.monotonic() - waited_from:.1f}s "
                "for the disc scan in flight)"
            )
            return True

        self._arm_deadline(step, RIP_SCAN_WAIT_S, ready)
        self._deadline_timeout_detail = (
            f"a disc scan was still running after {RIP_SCAN_WAIT_S:.0f}s, so Start "
            "was not pressed"
        )
        return True
