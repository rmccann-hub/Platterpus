"""Tests for platterpus.drive_control.

The runner is injected so we never touch a real drive or container. We assert
the right commands are issued, the kill ordering (whipper before reader), and —
crucially — the regex-safety properties that earlier attempts got wrong:
the whipper pattern must match the whipper CLI but NEVER "platterpus", and the
reader kill must not use `-f`.
"""

from __future__ import annotations

import os
import re
from types import SimpleNamespace

from platterpus import drive_control


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


# --- regex safety (the bugs that bit us in real use) ---------------------


def test_whipper_pattern_matches_the_cli() -> None:
    pat = drive_control._WHIPPER_CLI
    assert re.search(pat, "/usr/bin/python3 /usr/bin/whipper cd rip --cdr")
    assert re.search(pat, "whipper drive analyze")
    assert re.search(pat, "whipper offset find")


def test_whipper_pattern_never_matches_the_gui() -> None:
    pat = drive_control._WHIPPER_CLI
    # The GUI must survive a force-stop.
    assert not re.search(pat, "/usr/bin/platterpus")
    assert not re.search(pat, "python3 -m platterpus")
    assert not re.search(pat, "/opt/platterpus-x86_64.AppImage")
    # ...and the pkill command line that *carries* the pattern must not match
    # itself (the "whipper (" self-match bug).
    assert not re.search(pat, "pkill -KILL -f whipper (cd|drive|offset)")


# --- eject_drive ---------------------------------------------------------


def test_eject_success() -> None:
    rec = _Recorder(returncode=0)
    assert drive_control.eject_drive("/dev/sr0", runner=rec) is True
    assert _base(rec.calls[0]) == ["eject", "/dev/sr0"]


def test_eject_busy_returns_false() -> None:
    rec = _Recorder(returncode=1)
    assert drive_control.eject_drive("/dev/sr0", runner=rec) is False


# --- fuser (device-based kill) -------------------------------------------


def test_fuser_kills_device_holders() -> None:
    rec = _Recorder(returncode=0)
    assert drive_control.free_device_holders("/dev/sr0", runner=rec) is True
    assert _base(rec.calls[0]) == ["fuser", "-s", "-k", "/dev/sr0"]


def test_fuser_noop_without_device() -> None:
    rec = _Recorder(returncode=0)
    assert drive_control.free_device_holders("", runner=rec) is False
    assert rec.calls == []


# --- host kill -----------------------------------------------------------


def test_host_kill_targets_whipper_first_then_reader() -> None:
    rec = _Recorder(returncode=0)
    assert drive_control.kill_reader_on_host(runner=rec) is True
    first, second = _base(rec.calls[0]), _base(rec.calls[1])
    # whipper CLI first (anchored, with -f)...
    assert first == ["pkill", "-KILL", "-f", drive_control._WHIPPER_CLI]
    # ...then the reader/ripper by name (NO -f). Includes cyanrip, which is its
    # own reader (so cancelling a cyanrip rip actually stops it).
    assert second == ["pkill", "-KILL", "cdparanoia|cd-paranoia|cdrdao|cyanrip"]
    assert "-f" not in rec.calls[1]
    assert "cyanrip" in second[-1]


# --- in-container fallback ----------------------------------------------


def test_in_container_uses_distrobox_enter() -> None:
    rec = _Recorder(returncode=0)
    assert drive_control.force_stop_in_container("ripping", runner=rec) is True
    assert _base(rec.calls[0]) == [
        "distrobox",
        "enter",
        "ripping",
        "--",
        "pkill",
        "-KILL",
        "-f",
        drive_control._WHIPPER_CLI,
    ]


# --- force_stop_drive orchestration --------------------------------------


def test_force_stop_host_path_no_container_call() -> None:
    # Device-scoped fuser succeeds (rc 0) → the broad name pkill is skipped, and
    # no distrobox fallback. Precise kill only, then eject.
    rec = _Recorder(returncode=0)
    msg = drive_control.force_stop_drive("/dev/sr0", runner=rec)
    cmds = [os.path.basename(c[0]) for c in rec.calls]
    assert "distrobox" not in cmds
    assert cmds == ["fuser", "eject"]
    assert "spin down" in msg.lower()


def test_force_stop_does_not_broadly_pkill_when_device_scoped_kill_works() -> None:
    """Regression (#23): the old code ran a name-matched `pkill cyanrip` FIRST,
    which would SIGKILL a cyanrip ripping a *different* disc on another drive.
    When the device-scoped `fuser -k <device>` succeeds, the broad pkill must not
    run at all — only the process holding THIS drive is touched."""
    rec = _Recorder(returncode=0)
    drive_control.force_stop_drive("/dev/sr0", runner=rec)
    cmds = [os.path.basename(c[0]) for c in rec.calls]
    assert "pkill" not in cmds  # no by-name kill that could hit an unrelated rip
    assert cmds[0] == "fuser"  # the precise, device-scoped kill went first


def test_force_stop_falls_back_to_broad_pkill_then_container_when_fuser_misses() -> (
    None
):
    # rc 1 everywhere → fuser catches nothing → broad host pkills → distrobox.
    rec = _Recorder(returncode=1)
    drive_control.force_stop_drive("/dev/sr0", runner=rec)
    cmds = [os.path.basename(c[0]) for c in rec.calls]
    assert cmds == ["fuser", "pkill", "pkill", "distrobox", "distrobox", "eject"]


def test_force_stop_kills_before_ejecting() -> None:
    rec = _Recorder(returncode=0)
    drive_control.force_stop_drive("/dev/sr0", runner=rec)
    order = [os.path.basename(c[0]) for c in rec.calls]
    assert order.index("fuser") < order.index("eject")


# --- free_drive (scan-stall recovery: kill the reader, do NOT eject) ------


def test_free_drive_kills_but_never_ejects() -> None:
    """A wedged disc *scan* frees the drive without ejecting, so the disc stays
    in for a Rescan — the (device-scoped) kill runs but `eject` never does."""
    rec = _Recorder(returncode=0)
    msg = drive_control.free_drive("/dev/sr0", runner=rec)
    cmds = [os.path.basename(c[0]) for c in rec.calls]
    assert "eject" not in cmds
    assert cmds == ["fuser"]  # device-scoped kill succeeded; no broad pkill
    assert "free" in msg.lower()


def test_free_drive_falls_back_to_container_when_host_misses() -> None:
    # rc 1 everywhere → fuser catches nothing → broad host pkills → distrobox
    # fallback, still without any eject.
    rec = _Recorder(returncode=1)
    drive_control.free_drive("/dev/sr0", runner=rec)
    cmds = [os.path.basename(c[0]) for c in rec.calls]
    assert cmds == ["fuser", "pkill", "pkill", "distrobox", "distrobox"]
    assert "eject" not in cmds


# --- the bounded shutdown budget (found on the rig, 2026-07-30) -----------


def test_budgeted_runner_skips_remaining_steps_once_the_budget_is_spent() -> None:
    """Window close runs the kill sequence ON the GUI thread by design, so the
    total must be bounded — capping each of its up-to-seven subprocesses at 20 s
    independently let a closing window sit frozen for over a minute.

    `_run_bounded` is stubbed so nothing is really executed, and the clock is ours
    so the test is deterministic and instant. The floor that stops this passing
    vacuously: the FIRST call must be shown to dispatch. A budget that refuses
    everything would also "skip once spent", and would be a different bug.
    """
    dispatched: list[list[str]] = []
    now = [1000.0]
    real_run = drive_control._run_bounded
    real_clock = drive_control.time.monotonic

    def stub(argv: list[str], timeout: float) -> SimpleNamespace:
        dispatched.append(argv)
        return SimpleNamespace(returncode=0)

    drive_control._run_bounded = stub  # type: ignore[assignment]  # test double
    drive_control.time.monotonic = lambda: now[0]  # type: ignore[assignment]  # test clock
    try:
        run = drive_control.budgeted_runner(5.0)

        inside = run(["pkill", "-probe-a"])
        assert dispatched == [["pkill", "-probe-a"]], (
            "a call inside the budget must really be dispatched"
        )
        assert inside.returncode == 0

        now[0] += 6.0  # budget spent
        after = run(["pkill", "-probe-b"])
    finally:
        drive_control._run_bounded = real_run  # type: ignore[assignment]
        drive_control.time.monotonic = real_clock  # type: ignore[assignment]

    assert len(dispatched) == 1, "a step past the budget must NOT be dispatched"
    assert after.returncode == 124, (
        "a skipped step reports the conventional timeout code, which the callers "
        "already read as 'this step killed nothing' — so the sequence degrades "
        "exactly as it would have if the command had run and matched nothing"
    )


def test_budgeted_runner_never_exceeds_the_per_step_ceiling() -> None:
    """A generous total budget must not let one wedged command eat the whole
    thing — later steps still need their share."""
    captured: list[float] = []
    real = drive_control._run_bounded

    def spy(argv: list[str], timeout: float) -> object:
        captured.append(timeout)
        return real(["/bin/true"], timeout)

    drive_control._run_bounded = spy  # type: ignore[assignment]  # test double
    try:
        run = drive_control.budgeted_runner(600.0)
        run(["/bin/true"])
    finally:
        drive_control._run_bounded = real  # type: ignore[assignment]
    assert captured, "the runner must actually have dispatched something"
    assert captured[0] <= drive_control._STEP_TIMEOUT_S


def test_free_drive_accepts_a_budgeted_runner_and_still_kills() -> None:
    """The budget must not change WHAT gets killed on the happy path — only how
    long we are willing to keep trying."""
    rec = _Recorder(returncode=0)
    drive_control.free_drive(device="/dev/sr0", runner=rec)
    assert any("fuser" in _base(c)[0] for c in rec.calls), (
        "the device-scoped kill must still be the first thing tried"
    )
