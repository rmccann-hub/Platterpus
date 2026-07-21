"""Screen-reader announcements for live status surfaces (UX gap #4).

A sighted user watches the status line / verdict banner change; a screen-reader
user hears nothing unless the widget takes keyboard focus — and stealing focus
mid-rip is exactly what an accessible app must never do. Qt 6.8+ has the right
primitive for this: ``QAccessibleAnnouncementEvent``, the desktop analogue of a
web ``aria-live`` region — assistive technology speaks the message while focus
stays wherever the user left it.

One shared helper so every announcing surface behaves identically:

- **feature-detects** the event class at call time (our PySide6 pin allows
  Qt < 6.8, where the class doesn't exist — announcements just turn off);
- **never raises** (an accessibility decoration must never break a rip) —
  the one blanket ``except`` is the GUI-boundary case Code conventions allow;
- returns whether the event was actually dispatched, so tests can assert on
  behaviour instead of poking Qt internals.

Politeness: every announcement here is **polite** (queued after whatever the
reader is currently saying). No rip status is so urgent that it should cut the
user off mid-sentence — even an error stays on screen for as long as they need.

Callers throttle themselves: announce state *changes*, never every repaint of
the same state (see ``RipProgress.set_status``'s phase-key dedup for the
pattern). Under ``QT_QPA_PLATFORM=offscreen`` (the test environment) dispatch
succeeds and is a no-op, so the calls are cheap and safe everywhere.
"""

from __future__ import annotations

import logging

from PySide6 import QtGui
from PySide6.QtCore import QObject

log = logging.getLogger(__name__)

# Log the missing-API case once per process, not once per status line — a
# pre-6.8 Qt would otherwise write the same debug line thousands of times a rip.
_warned_unavailable: bool = False


def announce(source: QObject, message: str) -> bool:
    """Politely announce ``message`` to assistive technology, focus-safe.

    ``source`` is the widget the announcement belongs to (the status label,
    the verdict banner, …) — screen readers may attribute the message to it.
    Returns True when the event was dispatched, False when there was nothing
    to say (empty message), the running Qt lacks the announcement API, or
    dispatch failed. Never raises and never moves keyboard focus.
    """
    global _warned_unavailable
    if not message:
        return False
    event_cls = getattr(QtGui, "QAccessibleAnnouncementEvent", None)
    accessible = getattr(QtGui, "QAccessible", None)
    if event_cls is None or accessible is None:
        if not _warned_unavailable:
            _warned_unavailable = True
            log.debug(
                "QAccessibleAnnouncementEvent not available in this Qt; "
                "screen-reader announcements are disabled"
            )
        return False
    try:
        event = event_cls(source, message)
        # Polite = queued behind current speech (aria-live="polite"). The
        # enum exists wherever the event class does; getattr is belt only.
        politeness = getattr(accessible, "AnnouncementPoliteness", None)
        if politeness is not None:
            event.setPoliteness(politeness.Polite)
        accessible.updateAccessibility(event)
    except Exception:  # noqa: BLE001 — GUI-boundary guard: a broken a11y
        # bridge must degrade to silence, never crash a rip in progress.
        log.exception("accessibility announcement failed; continuing silently")
        return False
    return True
