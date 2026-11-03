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

from typing import Final

from platterpus.paths import LOG_PATH

# Shown as the notification's title; the body carries the specifics.
_TITLE_SUCCESS: str = "Platterpus — rip complete"
_TITLE_FAILED: str = "Platterpus — rip didn't finish"
_TITLE_CANCELLED: str = "Platterpus — rip cancelled"


#: The three characters a notification server that advertises ``body-markup``
#: reads as markup (``<b>``, ``<a href>``, ``<img>``, ``&amp;``), each mapped to a
#: look-alike that no server reads as anything but text. TASKS R87 item 1.
#:
#: **Why replace rather than escape.** The freedesktop notification spec lets a
#: server choose: one that advertises ``body-markup`` reads the body as a small
#: subset of HTML, one that does not shows it literally. Escaping ``<`` as
#: ``&lt;`` is right on the first and shows ``&lt;`` on the second, and which one
#: we are talking to is a capability Qt's ``QSystemTrayIcon.showMessage`` does
#: not expose. A look-alike reads the same on both, so the body can quote a
#: dependency's sentence (the failure hint often does) without that sentence
#: being able to style the toast, insert a link or fetch an image.
_NOTIFICATION_LOOKALIKES: Final[dict[int, str]] = {
    ord("<"): "‹",  # SINGLE LEFT-POINTING ANGLE QUOTATION MARK
    ord(">"): "›",  # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
    ord("&"): "＆",  # FULLWIDTH AMPERSAND
}


def notification_text(text: str) -> str:
    """``text`` with nothing a notification server could read as markup.

    Pure; never raises. See `_NOTIFICATION_LOOKALIKES` for why the three
    characters are replaced by look-alikes rather than escaped.
    """
    return str(text).translate(_NOTIFICATION_LOOKALIKES)


def build_completion_message(
    success: bool, cancelled: bool, detail: str
) -> tuple[str, str]:
    """Return the ``(title, body)`` for a finished rip's notification.

    `detail` is the same human-readable status the results pane shows (the
    fidelity summary on success, or the failure hint), reused so the two
    surfaces never disagree. `cancelled` distinguishes a user cancel from a real
    failure (both arrive as ``success=False``). Pure; never raises. The caller
    decides whether to actually send it (a cancel is typically not announced).

    The body passes through :func:`notification_text`: ``detail`` can quote the
    ripper, so its ``<``, ``>`` and ``&`` arrive as look-alikes, the one way the
    toast differs from the results pane (TASKS R87).
    """
    title, body = _completion_text(success, cancelled, (detail or "").strip())
    return notification_text(title), notification_text(body)


def _completion_text(success: bool, cancelled: bool, text: str) -> tuple[str, str]:
    """The ``(title, body)`` before :func:`notification_text`; pure."""
    if cancelled:
        return _TITLE_CANCELLED, (text or "The rip was cancelled by you.")
    if success:
        return _TITLE_SUCCESS, (text or "Your rip finished successfully.")
    # Name the file. "see the log for details" in a desktop toast is the least
    # actionable sentence in the app: the notification vanishes, and it never said
    # where to look. A path fits fine in a notification body.
    return _TITLE_FAILED, (text or f"The rip did not finish. Details are in {LOG_PATH}")
