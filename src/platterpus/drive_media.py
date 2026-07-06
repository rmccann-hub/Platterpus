"""Detect optical-media presence changes so a freshly-inserted disc is picked
up automatically — including after a rip is cancelled (which force-stops and
*ejects* the drive), the exact "put a new CD in and nothing happens" gap a real
session hit.

Two pieces, kept apart so the decision logic is testable without a drive:

  * :func:`probe_disc_status` — a thin, best-effort read of the drive's media
    state via the Linux ``CDROM_DRIVE_STATUS`` ioctl. It never spins the disc up
    (that's what this ioctl is for) and **never raises** — any problem (no such
    device, a busy drive, a non-Linux host) degrades to ``"unavailable"``, i.e.
    "don't know", so the caller simply doesn't auto-rescan (no regression).
  * :class:`MediaWatcher` — a pure state machine that turns a stream of statuses
    into "should I rescan now?" decisions: fire only on a genuine *transition*
    into "a disc is present" from a known empty/open/not-ready tray, so a disc
    that was already in at startup (the initial scan covers it) or a drive that
    briefly reads "unavailable" never triggers a spurious re-scan.

⚠️ HARDWARE-GATED: the ioctl path can't be exercised in the cloud (no drive).
It's isolated here, best-effort, and degrades to a no-op; validate the live
auto-detect on the Bazzite + BDR-209D rig (docs/test-plan.md).
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# Linux <linux/cdrom.h>. CDROM_DRIVE_STATUS reports tray/media state WITHOUT
# spinning the disc up; its return codes are CDS_* below.
_CDROM_DRIVE_STATUS: int = 0x5326
_CDS_NO_DISC: int = 1
_CDS_TRAY_OPEN: int = 2
_CDS_DRIVE_NOT_READY: int = 3
_CDS_DISC_OK: int = 4

# Our normalized statuses (kept as plain strings so the report/logs are readable
# and tests are obvious). "unavailable" = couldn't tell (treat as "no signal").
DISC: str = "disc"
EMPTY: str = "empty"
OPEN: str = "open"
NOT_READY: str = "not_ready"
UNAVAILABLE: str = "unavailable"

_CODE_TO_STATUS: dict[int, str] = {
    _CDS_NO_DISC: EMPTY,
    _CDS_TRAY_OPEN: OPEN,
    _CDS_DRIVE_NOT_READY: NOT_READY,
    _CDS_DISC_OK: DISC,
}


def status_from_code(code: int) -> str:
    """Map a raw CDROM_DRIVE_STATUS return code to one of our statuses (unknown
    codes → UNAVAILABLE). Split out so the mapping is unit-tested without a
    drive; :func:`probe_disc_status` calls it."""
    return _CODE_TO_STATUS.get(code, UNAVAILABLE)


# A disc "appeared" only when the tray was in one of these KNOWN empty states
# just before — so we never re-scan off an "unavailable"/unknown blip (a busy
# drive mid-teardown), only off a real empty→loaded transition. The same set is
# the "disc left" target for removal (disc→known-empty).
_EMPTY_STATES: frozenset[str] = frozenset({EMPTY, OPEN, NOT_READY})

# The three outcomes of one observation, returned by MediaWatcher.observe_event.
INSERTED: str = "inserted"  # known-empty → disc: a new disc to scan
REMOVED: str = "removed"  # disc → known-empty: the disc left; clear the stale view
NO_CHANGE: str = "none"  # steady state, a baseline observation, or an unknown blip


def probe_disc_status(device: str) -> str:
    """Best-effort media state of `device` (e.g. ``/dev/sr0``). Never raises.

    Returns one of DISC / EMPTY / OPEN / NOT_READY / UNAVAILABLE. Uses a
    non-blocking open + the CDROM_DRIVE_STATUS ioctl, so it returns promptly even
    with no media and doesn't spin the disc. Any error (missing device, busy
    drive, non-Linux host without the ioctl) → UNAVAILABLE.
    """
    if not device:
        return UNAVAILABLE
    try:
        import fcntl
        import os
    except Exception:  # noqa: BLE001 — non-Linux / restricted host
        return UNAVAILABLE
    fd: int | None = None
    try:
        # O_NONBLOCK: opening an optical device with no media otherwise blocks;
        # this returns a usable fd immediately just for the status ioctl.
        fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
        code = fcntl.ioctl(fd, _CDROM_DRIVE_STATUS)
    except (OSError, ValueError, AttributeError):
        return UNAVAILABLE
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
    return status_from_code(code)


class MediaWatcher:
    """Turn a stream of drive statuses into "a new disc appeared — rescan now"
    decisions. Pure and deterministic (no I/O); the caller feeds it statuses.

    Rules:
      * the FIRST observation only records the baseline — a disc already in the
        drive at startup is handled by the normal startup scan, not us;
      * thereafter, fire :data:`INSERTED` exactly once on a transition INTO
        :data:`DISC` from a known-empty tray (:data:`EMPTY`/:data:`OPEN`/
        :data:`NOT_READY`) — the "inserted a new disc" (or "re-inserted after the
        cancel/eject") event;
      * fire :data:`REMOVED` exactly once on the reverse transition, :data:`DISC`
        → a known-empty tray — the "disc left the drive" event, so the GUI can
        clear the now-stale disc view (an eject or a physical removal);
      * an ``UNAVAILABLE`` blip (drive busy mid-teardown) is remembered but never
        itself a trigger in either direction, so it can't manufacture a spurious
        rescan or a spurious clear.
    """

    def __init__(self) -> None:
        self._prev: str | None = None

    def reset(self) -> None:
        """Forget the baseline (e.g. after switching drives) so the next
        observation re-establishes it without firing."""
        self._prev = None

    def observe_event(self, status: str) -> str:
        """Record `status`; return :data:`INSERTED`, :data:`REMOVED`, or
        :data:`NO_CHANGE`.

        This is the richer form; :meth:`observe` is the insert-only bool wrapper
        kept for existing callers. Exactly one event can fire per observation
        (insert and removal are opposite transitions).
        """
        prev = self._prev
        self._prev = status
        if prev in _EMPTY_STATES and status == DISC:
            return INSERTED
        if prev == DISC and status in _EMPTY_STATES:
            return REMOVED
        return NO_CHANGE

    def observe(self, status: str) -> bool:
        """Record `status`; return True iff it means "a new disc appeared —
        rescan now". Back-compat wrapper over :meth:`observe_event`; prefer that
        method, which also reports removal."""
        return self.observe_event(status) == INSERTED
