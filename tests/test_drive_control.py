"""Tests for whipper_gui.drive_control.

The runner is injected so we never touch a real drive or container — we just
assert the right host/container commands are issued and the return logic.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

from whipper_gui import drive_control


class _Recorder:
    """Fake runner: records argv calls, returns a chosen exit code."""

    def __init__(self, returncode: int = 0) -> None:
        self.calls: list[list[str]] = []
        self.returncode = returncode

    def __call__(self, argv: list[str]) -> SimpleNamespace:
        self.calls.append(argv)
        return SimpleNamespace(returncode=self.returncode)


def _base(argv: list[str]) -> list[str]:
    """argv with the executable reduced to its basename, so assertions don't
    depend on whether eject/distrobox resolved to an absolute path."""
    return [os.path.basename(argv[0]), *argv[1:]]


# --- eject_drive ---------------------------------------------------------


def test_eject_success() -> None:
    rec = _Recorder(returncode=0)
    assert drive_control.eject_drive("/dev/sr0", runner=rec) is True
    assert _base(rec.calls[0]) == ["eject", "/dev/sr0"]


def test_eject_busy_returns_false() -> None:
    rec = _Recorder(returncode=1)  # "device busy" mid-rip
    assert drive_control.eject_drive("/dev/sr0", runner=rec) is False


def test_eject_without_device_omits_arg() -> None:
    rec = _Recorder()
    drive_control.eject_drive("", runner=rec)
    assert _base(rec.calls[0]) == ["eject"]


def test_eject_swallows_exceptions() -> None:
    def boom(argv: list[str]) -> SimpleNamespace:
        raise OSError("no eject binary")

    assert drive_control.eject_drive("/dev/sr0", runner=boom) is False


# --- force_stop_in_container (the Rule #3 exception) ---------------------


def test_in_container_kill_issues_distrobox_sigkill() -> None:
    rec = _Recorder(returncode=0)
    assert drive_control.force_stop_in_container("ripping", runner=rec) is True
    assert _base(rec.calls[0]) == [
        "distrobox", "enter", "ripping", "--",
        "pkill", "-KILL", "-f", "cdparanoia|cd-paranoia|whipper|cdrdao",
    ]


def test_in_container_kill_rc1_means_nothing_to_kill_ok() -> None:
    rec = _Recorder(returncode=1)
    assert drive_control.force_stop_in_container(runner=rec) is True


def test_in_container_kill_real_error_false() -> None:
    rec = _Recorder(returncode=2)
    assert drive_control.force_stop_in_container(runner=rec) is False


# --- force_stop_drive (both levers) --------------------------------------


def test_force_stop_attempts_both_levers() -> None:
    rec = _Recorder(returncode=1)  # eject busy → False; pkill rc1 → killed
    msg = drive_control.force_stop_drive("/dev/sr0", runner=rec)
    cmds = [os.path.basename(c[0]) for c in rec.calls]
    assert "eject" in cmds and "distrobox" in cmds
    assert "reader" in msg.lower()


def test_force_stop_kills_before_ejecting() -> None:
    # The kill must come first so the device is free for the eject.
    rec = _Recorder(returncode=0)
    drive_control.force_stop_drive("/dev/sr0", runner=rec)
    order = [os.path.basename(c[0]) for c in rec.calls]
    assert order.index("distrobox") < order.index("eject")


def test_force_stop_both_succeed_message() -> None:
    rec = _Recorder(returncode=0)
    msg = drive_control.force_stop_drive("/dev/sr0", runner=rec)
    assert "eject" in msg.lower()
