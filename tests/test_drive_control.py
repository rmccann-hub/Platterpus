"""Tests for whipper_gui.drive_control.

The runner is injected so we never touch a real drive or container — we just
assert the right host/container commands are issued and the stop logic. We
match the reader by process *name* (not `-f`), so the force-stop can never hit
the GUI ("whipper-gui") or self-match.
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
    depend on whether a tool resolved to an absolute path."""
    return [os.path.basename(argv[0]), *argv[1:]]


# --- eject_drive ---------------------------------------------------------


def test_eject_success() -> None:
    rec = _Recorder(returncode=0)
    assert drive_control.eject_drive("/dev/sr0", runner=rec) is True
    assert _base(rec.calls[0]) == ["eject", "/dev/sr0"]


def test_eject_busy_returns_false() -> None:
    rec = _Recorder(returncode=1)  # "device busy"
    assert drive_control.eject_drive("/dev/sr0", runner=rec) is False


def test_eject_without_device_omits_arg() -> None:
    rec = _Recorder()
    drive_control.eject_drive("", runner=rec)
    assert _base(rec.calls[0]) == ["eject"]


def test_eject_swallows_exceptions() -> None:
    def boom(argv: list[str]) -> SimpleNamespace:
        raise OSError("no eject binary")

    assert drive_control.eject_drive("/dev/sr0", runner=boom) is False


# --- kill_reader_on_host -------------------------------------------------


def test_host_kill_matches_reader_names_only() -> None:
    rec = _Recorder(returncode=0)
    assert drive_control.kill_reader_on_host(runner=rec) == 0
    # No -f: pattern is matched against the process name, and "whipper" is NOT
    # in it, so the GUI ("whipper-gui") can never be hit.
    assert _base(rec.calls[0]) == ["pkill", "-KILL", "cdparanoia|cd-paranoia|cdrdao"]
    assert "-f" not in rec.calls[0]
    assert "whipper" not in rec.calls[0][-1]


def test_host_kill_returns_none_on_failure() -> None:
    def boom(argv: list[str]) -> SimpleNamespace:
        raise FileNotFoundError("no pkill")

    assert drive_control.kill_reader_on_host(runner=boom) is None


# --- force_stop_in_container (the Rule #3 fallback) ----------------------


def test_in_container_kill_issues_distrobox_pkill() -> None:
    rec = _Recorder(returncode=0)
    assert drive_control.force_stop_in_container("ripping", runner=rec) == 0
    assert _base(rec.calls[0]) == [
        "distrobox", "enter", "ripping", "--",
        "pkill", "-KILL", "cdparanoia|cd-paranoia|cdrdao",
    ]
    # Must not use -f, or the `distrobox enter … pkill …` session self-matches.
    assert "-f" not in rec.calls[0]


# --- force_stop_drive ----------------------------------------------------


def test_force_stop_host_kill_then_eject_no_container_call() -> None:
    # Host pkill kills the reader (rc 0) → no distrobox fallback, then eject.
    rec = _Recorder(returncode=0)
    msg = drive_control.force_stop_drive("/dev/sr0", runner=rec)
    cmds = [os.path.basename(c[0]) for c in rec.calls]
    assert cmds == ["pkill", "eject"]  # no "distrobox"
    assert "reader" in msg.lower()


def test_force_stop_falls_back_to_container_when_host_misses() -> None:
    # rc 1 everywhere: host pkill matches nothing → distrobox fallback → eject.
    rec = _Recorder(returncode=1)
    drive_control.force_stop_drive("/dev/sr0", runner=rec)
    cmds = [os.path.basename(c[0]) for c in rec.calls]
    assert cmds == ["pkill", "distrobox", "eject"]


def test_force_stop_kills_before_ejecting() -> None:
    rec = _Recorder(returncode=0)
    drive_control.force_stop_drive("/dev/sr0", runner=rec)
    order = [os.path.basename(c[0]) for c in rec.calls]
    assert order.index("pkill") < order.index("eject")
