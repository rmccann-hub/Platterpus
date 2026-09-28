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
    that was already in at startup (the initial scan covers it) never triggers a
    spurious re-scan. An "unavailable" reading is neither a trigger nor a state:
    the watcher compares each known reading with the last KNOWN one, so a drive
    that reads "unavailable" while it loads a disc still has the insertion seen.

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


# A disc "appeared" only when the LAST KNOWN state was one of these empty states
# — so we never re-scan off an "unavailable"/unknown blip (a busy drive
# mid-teardown), only off a real empty→loaded transition. The same set is the
# "disc left" target for removal (disc→known-empty).
_EMPTY_STATES: frozenset[str] = frozenset({EMPTY, OPEN, NOT_READY})

# Every reading that says something about the tray. Anything else (UNAVAILABLE,
# or a value this module does not know) is "no information" and is bridged over
# rather than remembered — see MediaWatcher.observe_event.
_KNOWN_STATES: frozenset[str] = _EMPTY_STATES | {DISC}

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
      * an ``UNAVAILABLE`` reading (or any value this module does not know) is
        never a trigger AND never overwrites the last known state. It is
        "no information", so the next known reading is compared with the last
        known one, straight across the gap;
      * a disc the app has just read (:meth:`note_disc_present`) is recorded as
        :data:`DISC` without firing, so the drive saying so afterwards is not
        an insertion.

    **Why the last rule changed (2026-09-28).** An unknown reading used to be
    remembered as the previous state, so ``empty → unavailable → disc`` compared
    ``disc`` with ``unavailable`` and fired nothing: the disc was inserted and
    never read, and closing the tray again or restarting the app were the only
    ways out — which is what the maintainer reported from the rig. The committed
    rig log shows it happening: ``round27fullplatterpusapplog1.txt`` lines 34–35
    record *disc removed* at 20:30:07 and again at 23:25:32 with no *disc
    inserted* and no drive change between them. A second removal needs a disc
    reading in between, and a disc reading straight after an empty one fires
    INSERTED, so the disc's return came through an unknown reading and was
    swallowed. The original intent — never manufacture an event out of a blip —
    is kept: ``disc → unavailable → disc`` is still nothing, and a first reading
    after :meth:`reset` is still only a baseline.
    """

    def __init__(self) -> None:
        # The last reading that said something about the tray (never UNAVAILABLE).
        self._last_known: str | None = None
        # The last reading of any kind, for the caller's "status changed" log line.
        self._last_status: str | None = None
        # Unknown readings since the last known one, and how many the most recent
        # known reading came through (the evidence a log line should carry).
        self._unknown_streak: int = 0
        self._bridged: int = 0

    @property
    def last_status(self) -> str | None:
        """The previous reading as it was taken, UNAVAILABLE included (None at
        start or after :meth:`reset`). For logging a status change; the decision
        logic reads the last KNOWN state instead."""
        return self._last_status

    @property
    def bridged_unknown_readings(self) -> int:
        """How many unknown readings the latest known reading came across. A
        non-zero value beside an INSERTED is the case the 2026-09-28 fix exists
        for, and is worth putting in the log line."""
        return self._bridged

    def bridge_note(self) -> str:
        """A log-line suffix naming the unknown readings the latest known reading
        came across: ``", after 3 unreadable status checks"``, or ``""``."""
        count = self._bridged
        if count <= 0:
            return ""
        return f", after {count} unreadable status check{'' if count == 1 else 's'}"

    def reset(self) -> None:
        """Forget the baseline (e.g. after switching drives) so the next
        observation re-establishes it without firing."""
        self._last_known = None
        self._last_status = None
        self._unknown_streak = 0
        self._bridged = 0

    def note_disc_present(self) -> None:
        """A disc was just READ from the drive: remember that a disc is in, and
        fire nothing.

        **Why (code review, 2026-09-28).** The app reads a disc on its own now (a
        failed read is retried), and a retry can succeed while the last reading
        the watcher took was ``not_ready`` — a disc still spinning up, which the
        watcher counts as an empty tray. Nothing told it the read had worked, so
        the next ``disc`` reading looked like an insertion: a log line for an
        insertion that never happened, a cleared view, and the disc read a third
        time. A successful read is better evidence than any status reading, so it
        becomes the last known state. It is not an event: the caller already has
        the disc on screen. A FAILED read tells the watcher nothing, so a disc
        that becomes ready after every read failed is still an insertion.
        :attr:`last_status` is left alone; it is the stream of readings.
        """
        self._last_known = DISC
        self._unknown_streak = 0
        self._bridged = 0

    def observe_event(self, status: str) -> str:
        """Record `status`; return :data:`INSERTED`, :data:`REMOVED`, or
        :data:`NO_CHANGE`.

        This is the richer form; :meth:`observe` is the insert-only bool wrapper
        kept for existing callers. Exactly one event can fire per observation
        (insert and removal are opposite transitions).
        """
        self._last_status = status
        if status not in _KNOWN_STATES:
            # No information about the tray: not a trigger, and NOT a state. The
            # last known state stands, so the next known reading is compared with
            # it — see the class docstring for the insertion this used to lose.
            self._unknown_streak += 1
            return NO_CHANGE
        prev = self._last_known
        self._last_known = status
        self._bridged = self._unknown_streak
        self._unknown_streak = 0
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
