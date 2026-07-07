"""Build the text for the rip-completion desktop notification.

The *sending* is a one-liner on the GUI side (a ``QSystemTrayIcon.showMessage``
— pure PySide6, no external tool, so there's no ad-hoc dependency check to make,
per Critical rule #6). The interesting, testable part is turning a finished
rip's outcome into a short (title, body) pair, so that lives here as a pure
function with no Qt import — unit-tested without a desktop, a tray, or a bus.

Kept deliberately tiny and Qt-free: a completion notification is a courtesy for
an unattended rip, never load-bearing, so nothing here raises and the caller
treats a failure to send as a no-op.
"""

from __future__ import annotations

# Shown as the notification's title; the body carries the specifics.
_TITLE_SUCCESS: str = "Platterpus — rip complete"
_TITLE_FAILED: str = "Platterpus — rip didn't finish"
_TITLE_CANCELLED: str = "Platterpus — rip cancelled"


def build_completion_message(
    success: bool, cancelled: bool, detail: str
) -> tuple[str, str]:
    """Return the ``(title, body)`` for a finished rip's notification.

    `detail` is the same human-readable status the results pane shows (the
    fidelity summary on success, or the failure hint), reused so the two
    surfaces never disagree. `cancelled` distinguishes a user cancel from a real
    failure (both arrive as ``success=False``). Pure; never raises. The caller
    decides whether to actually send it (a cancel is typically not announced).
    """
    text = (detail or "").strip()
    if cancelled:
        return _TITLE_CANCELLED, (text or "The rip was cancelled by you.")
    if success:
        return _TITLE_SUCCESS, (text or "Your rip finished successfully.")
    return _TITLE_FAILED, (text or "The rip did not finish — see the log for details.")
