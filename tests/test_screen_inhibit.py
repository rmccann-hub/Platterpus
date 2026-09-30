"""The screen hold the acceptance run takes beside its sleep lock.

The round 29 Full run's three screenshot failures found every window unexposed; the
hypothesis is a blanked screen (`TASKS.md`, round 29). These tests pin the hold's
tri-state outcome on every arm, and drive the real QtDBus path against a private
``dbus-daemon`` with a stand-in ``org.freedesktop.ScreenSaver``, so the calls are the
ones a desktop receives: ``Inhibit(app, reason)`` answered with a cookie, and
``UnInhibit(cookie)`` on release.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtDBus import QDBusConnection, QDBusMessage, QDBusVirtualObject
from PySide6.QtWidgets import QApplication

from platterpus import screen_inhibit
from platterpus.screen_inhibit import ScreenInhibitor, outcome_from_reply
from platterpus.sleep_inhibit import (
    STATE_HELD,
    STATE_NOT_INSTALLED,
    STATE_UNAVAILABLE,
    InhibitOutcome,
)


def test_a_cookie_is_a_held_screen() -> None:
    outcome, cookie = outcome_from_reply(False, "", "", [7])
    assert outcome.state == STATE_HELD and cookie == 7
    assert outcome.what == screen_inhibit.SCREEN_WHAT


def test_no_screensaver_service_is_not_installed_and_says_what_to_do() -> None:
    outcome, cookie = outcome_from_reply(
        True, screen_inhibit.SERVICE_UNKNOWN, "The name was not provided", []
    )
    assert outcome.state == STATE_NOT_INSTALLED and cookie is None
    assert "never turn off" in outcome.detail


def test_any_other_error_is_unavailable_with_the_buss_own_words() -> None:
    outcome, cookie = outcome_from_reply(
        True, "org.freedesktop.DBus.Error.AccessDenied", "nope", []
    )
    assert outcome.state == STATE_UNAVAILABLE and cookie is None
    assert "AccessDenied: nope" in outcome.detail


@pytest.mark.parametrize("arguments", [[], ["7"], [True], [None]])
def test_a_reply_without_a_releasable_cookie_is_not_claimed(
    arguments: list[object],
) -> None:
    outcome, cookie = outcome_from_reply(False, "", "", arguments)
    assert outcome.state == STATE_UNAVAILABLE and cookie is None


def test_with_no_session_bus_the_answer_is_immediate_and_not_held(
    qapp: QApplication,
) -> None:
    """The CI shape: no bus at all. The callback still fires, so the window has one path."""
    dead = QDBusConnection.connectToBus("unix:path=/nonexistent/bus", "no-bus")
    assert not dead.isConnected(), "the floor: this connection must be dead"
    got: list[InhibitOutcome] = []
    inhibitor = ScreenInhibitor(reason="test", connection=dead)
    inhibitor.acquire(got.append)
    assert len(got) == 1 and got[0].state == STATE_UNAVAILABLE, got
    assert not inhibitor.held
    inhibitor.release()  # safe with nothing held
    QDBusConnection.disconnectFromBus("no-bus")


# -- a real bus, with a stand-in screen saver ------------------------------------


@dataclass
class _Desktop:
    client: QDBusConnection
    calls: list[tuple[str, list[object]]] = field(default_factory=list)


class _FakeScreenSaver(QDBusVirtualObject):
    """Answers Inhibit with cookie 7 and records every call."""

    def __init__(self, calls: list[tuple[str, list[object]]]) -> None:
        super().__init__()
        self._calls = calls

    def introspect(self, path: str) -> str:
        return ""

    def handleMessage(self, message: QDBusMessage, connection: QDBusConnection) -> bool:
        self._calls.append((message.member(), list(message.arguments())))
        reply = message.createReply(7) if message.member() == "Inhibit" else None
        connection.send(reply if reply is not None else message.createReply())
        return True


@pytest.fixture
def desktop(qapp: QApplication) -> Iterator[_Desktop]:
    if shutil.which("dbus-daemon") is None:
        pytest.skip("dbus-daemon is not installed, so no private session bus")
    daemon = subprocess.Popen(
        ["dbus-daemon", "--session", "--print-address=1", "--nofork", "--nopidfile"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        assert daemon.stdout is not None
        address = daemon.stdout.readline().strip()
        server = QDBusConnection.connectToBus(address, "fake-desktop")
        client = QDBusConnection.connectToBus(address, "fake-client")
        assert server.isConnected() and client.isConnected(), "the floor"
        state = _Desktop(client=client)
        fake = _FakeScreenSaver(state.calls)
        assert server.registerVirtualObject(screen_inhibit.SCREENSAVER_PATH, fake)
        assert server.registerService(screen_inhibit.SCREENSAVER_SERVICE)
        yield state
    finally:
        QDBusConnection.disconnectFromBus("fake-client")
        QDBusConnection.disconnectFromBus("fake-desktop")
        daemon.terminate()
        daemon.wait(5)


def _pump_until(predicate: object, seconds: float = 5.0) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and not predicate():  # type: ignore[operator]  # a callable
        QCoreApplication.processEvents()
        time.sleep(0.01)


def test_a_desktop_holds_the_screen_and_gets_it_back(desktop: _Desktop) -> None:
    got: list[InhibitOutcome] = []
    inhibitor = ScreenInhibitor(reason="acceptance run", connection=desktop.client)
    inhibitor.acquire(got.append)
    assert not got, "acquire must return before the desktop answers"
    _pump_until(lambda: bool(got))
    assert got and got[0].state == STATE_HELD, got
    assert inhibitor.held
    assert desktop.calls[0] == (
        "Inhibit",
        [screen_inhibit.APP_NAME, "acceptance run"],
    )
    inhibitor.release()
    _pump_until(lambda: len(desktop.calls) >= 2)
    assert desktop.calls[1] == ("UnInhibit", [7]), desktop.calls
    assert not inhibitor.held
    inhibitor.release()  # twice is fine, and sends nothing more
    _pump_until(lambda: False, seconds=0.2)
    assert len(desktop.calls) == 2


def test_a_release_before_the_answer_gives_the_cookie_straight_back(
    desktop: _Desktop,
) -> None:
    got: list[InhibitOutcome] = []
    inhibitor = ScreenInhibitor(reason="acceptance run", connection=desktop.client)
    inhibitor.acquire(got.append)
    inhibitor.release()  # the run ended before the desktop replied
    _pump_until(lambda: bool(got) and len(desktop.calls) >= 2)
    assert got and got[0].state == STATE_UNAVAILABLE, got
    assert ("UnInhibit", [7]) in desktop.calls, desktop.calls
    assert not inhibitor.held


def test_a_bus_without_a_screen_saver_is_not_installed(qapp: QApplication) -> None:
    if shutil.which("dbus-daemon") is None:
        pytest.skip("dbus-daemon is not installed, so no private session bus")
    daemon = subprocess.Popen(
        ["dbus-daemon", "--session", "--print-address=1", "--nofork", "--nopidfile"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        assert daemon.stdout is not None
        client = QDBusConnection.connectToBus(daemon.stdout.readline().strip(), "bare")
        assert client.isConnected(), "the floor"
        got: list[InhibitOutcome] = []
        # Held by a name, as the window holds it: an inhibitor nobody references is
        # collected with its watcher, and its answer never arrives.
        inhibitor = ScreenInhibitor(reason="t", connection=client)
        inhibitor.acquire(got.append)
        _pump_until(lambda: bool(got))
        assert got and got[0].state == STATE_NOT_INSTALLED, got
    finally:
        QDBusConnection.disconnectFromBus("bare")
        daemon.terminate()
        daemon.wait(5)
