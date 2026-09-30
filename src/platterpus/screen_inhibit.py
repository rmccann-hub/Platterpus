"""Hold the screen awake, with no blanking and no lock, for the length of an acceptance run.

**Why this exists (2026-09-30).** The round 29 Full run (`docs/handshake/artifactsround29/`)
failed three screenshot steps, at 94, 96 and 124 minutes, because every window was
``visible=True`` but ``exposed=False``: there was nothing on screen to photograph. The
steps sit in sections graded ARCHIVAL in advance, so the run was ``partial`` whatever the
rips did. Our hypothesis is that the display blanked or locked. The sleep lock
(:mod:`platterpus.sleep_inhibit`) holds ``idle:sleep:handle-lid-switch`` through logind,
which stops the machine sleeping, and says nothing to the desktop's screen saver. That
module's docstring once called a blanked screen "harmless (the session keeps running)",
and for the rips it is; for a step that must photograph a window it is not.

**The fix is the desktop's own interface, not a settings change.**
``org.freedesktop.ScreenSaver.Inhibit`` on the session bus is the freedesktop standard a
video player uses. KDE Plasma honours it for both blanking and locking. It returns a
cookie, and the hold lasts until ``UnInhibit(cookie)`` or until our connection to the bus
goes away. So a crash, a kill or an exit releases it with nothing to undo, for the same
reason the sleep lock uses a child process. It is **not** a new dependency: QtDBus is part
of the Qt we already ship, and the interface belongs to the desktop session.

**Only the hardware run can say the hypothesis was right.** This holds the screen; whether
the screen blanking was what hid the windows is what the next Full run answers.

**Never blocks the GUI thread** (`CLAUDE.md`). The call is asynchronous, with a
:data:`CALL_TIMEOUT_MS` bound, and its answer comes back through a
``QDBusPendingCallWatcher`` on the event loop. :meth:`ScreenInhibitor.release` sends
``UnInhibit`` without waiting for a reply, so it is safe on a teardown path.

**Tri-state, never a bool**, and the outcome is the sleep lock's own
:class:`~platterpus.sleep_inhibit.InhibitOutcome`, so the window reports both the same way:
``held``; ``not_installed`` when the session bus has no screen-saver service at all; and
``unavailable`` for everything else, with the bus's own sentence.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Final

from PySide6.QtCore import QObject
from PySide6.QtDBus import QDBusConnection, QDBusMessage, QDBusPendingCallWatcher

from platterpus.sleep_inhibit import (
    STATE_HELD,
    STATE_NOT_INSTALLED,
    STATE_UNAVAILABLE,
    InhibitOutcome,
    _bounded,
)

log = logging.getLogger(__name__)

#: The freedesktop screen-saver service, object and interface. One spelling each.
SCREENSAVER_SERVICE: Final[str] = "org.freedesktop.ScreenSaver"
SCREENSAVER_PATH: Final[str] = "/org/freedesktop/ScreenSaver"
SCREENSAVER_INTERFACE: Final[str] = "org.freedesktop.ScreenSaver"

#: What an outcome records as the thing held, beside the sleep lock's `--what` set.
SCREEN_WHAT: Final[str] = "screensaver (no blanking, no lock)"

#: The application name the desktop lists as holding the screen awake.
APP_NAME: Final[str] = "Platterpus"

#: How long the Inhibit call may take. A sick session bus must not leave the run
#: waiting: the run starts on the sleep lock's answer, and this one only reports.
CALL_TIMEOUT_MS: Final[int] = 5000

#: The bus's answer when nothing on it provides the screen-saver service.
SERVICE_UNKNOWN: Final[str] = "org.freedesktop.DBus.Error.ServiceUnknown"


def inhibit_message(reason: str) -> QDBusMessage:
    """The ``Inhibit(application, reason)`` call."""
    message = QDBusMessage.createMethodCall(
        SCREENSAVER_SERVICE, SCREENSAVER_PATH, SCREENSAVER_INTERFACE, "Inhibit"
    )
    message.setArguments([APP_NAME, reason])
    return message


def uninhibit_message(cookie: int) -> QDBusMessage:
    """The ``UnInhibit(cookie)`` call that ends the hold."""
    message = QDBusMessage.createMethodCall(
        SCREENSAVER_SERVICE, SCREENSAVER_PATH, SCREENSAVER_INTERFACE, "UnInhibit"
    )
    message.setArguments([cookie])
    return message


def outcome_from_reply(
    is_error: bool, error_name: str, error_message: str, arguments: list[object]
) -> tuple[InhibitOutcome, int | None]:
    """The outcome, and the cookie when the hold was taken. **Never raises.**

    Takes plain values rather than a ``QDBusMessage`` so every arm can be tested
    without a bus. A reply with no integer cookie is ``unavailable``: the service
    answered something we cannot release, and a hold we cannot release is not one
    we claim.
    """
    if is_error:
        said = _bounded(f"{error_name}: {error_message}")
        if error_name == SERVICE_UNKNOWN:
            return (
                InhibitOutcome(
                    state=STATE_NOT_INSTALLED,
                    detail=(
                        "This desktop session has no screen-saver service to ask "
                        f"({said}), so the screen could NOT be held on. Set the screen "
                        "to never turn off for the run, or screenshot steps may find "
                        "no window on screen."
                    ),
                    what=SCREEN_WHAT,
                ),
                None,
            )
        return (
            InhibitOutcome(
                state=STATE_UNAVAILABLE,
                detail=(
                    f"The desktop refused to hold the screen on ({said}). Set the "
                    "screen to never turn off for the run, or screenshot steps may "
                    "find no window on screen."
                ),
                what=SCREEN_WHAT,
            ),
            None,
        )
    cookie = arguments[0] if arguments else None
    if not isinstance(cookie, int) or isinstance(cookie, bool):
        return (
            InhibitOutcome(
                state=STATE_UNAVAILABLE,
                detail=(
                    "The screen-saver service answered without a cookie Platterpus "
                    f"can release ({_bounded(repr(arguments))}), so the hold is not "
                    "claimed. Set the screen to never turn off for the run."
                ),
                what=SCREEN_WHAT,
            ),
            None,
        )
    return (
        InhibitOutcome(
            state=STATE_HELD,
            detail=(
                "The desktop agreed to keep the screen on, with no blanking and no "
                "lock, for this run; that is its promise, not a measurement, and "
                "each screenshot step reports whether the display was showing the "
                "app. It is released when the run ends, or if Platterpus exits."
            ),
            what=SCREEN_WHAT,
        ),
        cookie,
    )


class ScreenInhibitor(QObject):
    """Takes, holds and releases one screen-saver inhibit. Lives on the GUI thread."""

    def __init__(
        self,
        *,
        reason: str,
        connection: QDBusConnection | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._reason: str = reason
        self._connection: QDBusConnection = (
            connection if connection is not None else QDBusConnection.sessionBus()
        )
        self._cookie: int | None = None
        self._released: bool = False
        self._watcher: QDBusPendingCallWatcher | None = None
        self._on_done: Callable[[InhibitOutcome], None] | None = None

    @property
    def held(self) -> bool:
        """Whether a cookie is held that :meth:`release` has not yet given back."""
        return self._cookie is not None

    def acquire(self, on_done: Callable[[InhibitOutcome], None]) -> None:
        """Ask for the hold; ``on_done`` gets the outcome on the event loop.

        Returns at once. With no session bus the answer is immediate, and is still
        delivered through ``on_done`` so the caller has one path.
        """
        self._released = False
        self._on_done = on_done
        if not self._connection.isConnected():
            error = self._connection.lastError()
            said = _bounded(f"{error.name()}: {error.message()}".strip(": "))
            self._finish(
                InhibitOutcome(
                    state=STATE_UNAVAILABLE,
                    detail=(
                        "There is no desktop session bus to ask"
                        + (f" ({said})" if said else "")
                        + ", so the screen could NOT be held on. Set the screen to "
                        "never turn off for the run."
                    ),
                    what=SCREEN_WHAT,
                )
            )
            return
        pending = self._connection.asyncCall(
            inhibit_message(self._reason), CALL_TIMEOUT_MS
        )
        watcher = QDBusPendingCallWatcher(pending, self)
        watcher.finished.connect(self._on_reply)
        self._watcher = watcher

    def _on_reply(self, watcher: QDBusPendingCallWatcher) -> None:
        reply = watcher.reply()
        error = watcher.error()
        outcome, cookie = outcome_from_reply(
            watcher.isError(), error.name(), error.message(), list(reply.arguments())
        )
        watcher.deleteLater()
        self._watcher = None
        if cookie is not None and self._released:
            # Released while the call was in flight: give it straight back, or the
            # screen stays held for a run that has already ended.
            self._connection.send(uninhibit_message(cookie))
            outcome = InhibitOutcome(
                state=STATE_UNAVAILABLE,
                detail=(
                    "The screen hold was released while it was being taken, so it is "
                    "NOT held."
                ),
                what=SCREEN_WHAT,
            )
        elif cookie is not None:
            self._cookie = cookie
        self._finish(outcome)

    def _finish(self, outcome: InhibitOutcome) -> None:
        if outcome.state == STATE_HELD:
            log.info("screen inhibitor: %s — %s", outcome.state, outcome.detail)
        else:
            log.warning("screen inhibitor: %s — %s", outcome.state, outcome.detail)
        callback, self._on_done = self._on_done, None
        if callback is not None:
            callback(outcome)

    def release(self) -> None:
        """Give the hold back. Never waits, never raises, safe to call twice or never."""
        self._released = True
        cookie, self._cookie = self._cookie, None
        if cookie is None:
            return
        if not self._connection.send(uninhibit_message(cookie)):
            log.warning(
                "screen inhibitor: UnInhibit could not be sent; the hold ends when "
                "Platterpus exits"
            )
            return
        log.info("screen inhibitor: the screen hold has been released")
