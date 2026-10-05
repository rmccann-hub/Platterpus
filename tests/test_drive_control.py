"""Tests for platterpus.drive_control.

The runner is injected so we never touch a real drive or container. We assert
the right commands are issued and — crucially — the safety property earlier
attempts got wrong: no kill pattern may use `-f`, because a full-command-line
match can hit the GUI's own command line ("platterpus") or the pkill's own.
"""

from __future__ import annotations

import os
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


def test_no_kill_pattern_matches_the_full_command_line() -> None:
    """Every pkill here matches a process NAME; none uses `-f`.

    The old ripper's orchestrator pattern was the one `-f` match, anchored
    carefully so it could not hit the GUI or itself. It was removed on
    2026-09-24 with nothing left for it to kill; this pins that no `-f` pattern
    comes back without someone reading why it was dangerous.
    """
    patterns = drive_control._pkill_arglists()
    assert patterns, "no kill patterns at all"
    assert all("-f" not in args for args in patterns), patterns
    assert any("cyanrip" in arg for args in patterns for arg in args)


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


def test_fuser_sends_the_NAMED_signal_and_SIGKILL_only_by_default() -> None:
    """The other half of the post-cancel rescue, and it was missing.

    `tests/test_ui_main_window.py` asserts the rescue *requests* `signal="TERM"`.
    That is a claim about the call site. Nothing asserted the signal reached
    fuser's argv, and `revert_probe.py` proved it: disabling the append here left
    every test green. `CLAUDE.md` — *am I asserting that a thing HAPPENED, or
    that it was REQUESTED?*

    WHY THE SIGNAL IS ARCHIVAL. SIGKILL cannot be caught, so cyanrip runs no
    `atexit`, and `atexit` is where the log's completion footer and `Log FUN512:`
    signature are written. A rescue that stops the drive with SIGKILL turns every
    cancelled rip's log into an unverifiable fragment — the exact loss §I of the
    acceptance run exists to detect.

    Both directions, because the default must stay SIGKILL: the stuck-scan path
    frees a *wedged* reader with no log to protect, and quietly softening it to
    SIGTERM would leave a reader that ignores it holding the drive. (The shutdown
    path used to share that default, and cost a log its footer; it now goes
    through `stop_reader_gracefully`, tested below.)
    """
    rec = _Recorder(returncode=0)
    assert (
        drive_control.free_device_holders("/dev/sr0", runner=rec, signal="TERM") is True
    )
    assert _base(rec.calls[0]) == ["fuser", "-s", "-k", "-TERM", "/dev/sr0"], (
        f"the named signal did not reach fuser's argv: {_base(rec.calls[0])}"
    )

    # Default: fuser's own default, which is SIGKILL. No signal flag at all.
    rec2 = _Recorder(returncode=0)
    assert drive_control.free_device_holders("/dev/sr0", runner=rec2) is True
    assert _base(rec2.calls[0]) == ["fuser", "-s", "-k", "/dev/sr0"], (
        f"the default gained a signal flag: {_base(rec2.calls[0])}"
    )


def test_fuser_noop_without_device() -> None:
    rec = _Recorder(returncode=0)
    assert drive_control.free_device_holders("", runner=rec) is False
    assert rec.calls == []


# --- host kill -----------------------------------------------------------


def test_host_kill_targets_the_readers_by_name() -> None:
    rec = _Recorder(returncode=0)
    assert drive_control.kill_reader_on_host(runner=rec) is True
    assert len(rec.calls) == 1
    only = _base(rec.calls[0])
    # The reader/ripper by name (NO -f). Includes cyanrip, which is its own
    # reader (so cancelling a cyanrip rip actually stops it).
    assert only == ["pkill", "-KILL", "cdparanoia|cd-paranoia|cdrdao|cyanrip"]
    assert "-f" not in rec.calls[0]


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
        "cdparanoia|cd-paranoia|cdrdao|cyanrip",
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
    # rc 1 everywhere → fuser catches nothing → broad host pkill → distrobox.
    rec = _Recorder(returncode=1)
    drive_control.force_stop_drive("/dev/sr0", runner=rec)
    cmds = [os.path.basename(c[0]) for c in rec.calls]
    assert cmds == ["fuser", "pkill", "distrobox", "eject"]


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
    # rc 1 everywhere → fuser catches nothing → broad host pkill → distrobox
    # fallback, still without any eject.
    rec = _Recorder(returncode=1)
    drive_control.free_drive("/dev/sr0", runner=rec)
    cmds = [os.path.basename(c[0]) for c in rec.calls]
    assert cmds == ["fuser", "pkill", "distrobox"]
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


# --- shutdown: SIGTERM, a grace, then SIGKILL (the fork's round 30 S25) ---------


class _Scripted:
    """Fake runner: answers each argv by its shape, and records every call.

    `fuser -s -k -TERM <dev>` and `fuser -s <dev>` are told apart by argv, so a
    test states what the device holder does over time: `held` is consumed one
    answer per `fuser -s` probe (its last value repeats).
    """

    def __init__(
        self, *, term_rc: int = 0, kill_rc: int = 0, held: list[int | None]
    ) -> None:
        self.calls: list[list[str]] = []
        self.term_rc = term_rc
        self.kill_rc = kill_rc
        self.held = held

    def __call__(self, argv: list[str]) -> SimpleNamespace:
        self.calls.append(argv)
        base = _base(argv)
        if base == ["fuser", "-s", "-k", "-TERM", "/dev/sr0"]:
            return SimpleNamespace(returncode=self.term_rc)
        if base == ["fuser", "-s", "/dev/sr0"]:
            rc = self.held[0] if len(self.held) == 1 else self.held.pop(0)
            if rc is None:
                raise OSError("fuser could not start")
            return SimpleNamespace(returncode=rc)
        if base == ["fuser", "-s", "-k", "/dev/sr0"]:
            return SimpleNamespace(returncode=self.kill_rc)
        return SimpleNamespace(returncode=0)  # pkill / distrobox "kill"

    def sigkills(self) -> list[list[str]]:
        """Every call that kills without a TERM flag: fuser -k, pkill, distrobox."""
        return [
            _base(c)
            for c in self.calls
            if (_base(c)[:3] == ["fuser", "-s", "-k"] and "-TERM" not in c)
            or _base(c)[0] in ("pkill", "distrobox")
        ]


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def _stop(run: _Scripted, clock: _Clock, **kw: object) -> str:
    return drive_control.stop_reader_gracefully(
        "/dev/sr0",
        runner=run,
        sleep=clock.sleep,
        clock=clock,
        **kw,  # type: ignore[arg-type]  # test kwargs
    )


def test_shutdown_sends_SIGTERM_first_and_no_SIGKILL_once_the_reader_lets_go() -> None:
    """The round-29 rip was SIGKILLed 191 ms after a SIGTERM and lost its footer.
    Here the reader lets go on the third probe, inside the grace: no SIGKILL at all."""
    run, clock = _Scripted(held=[0, 0, 1]), _Clock()
    message = _stop(run, clock)
    assert _base(run.calls[0]) == ["fuser", "-s", "-k", "-TERM", "/dev/sr0"]
    assert run.sigkills() == [], run.calls
    assert "allowed to finish" in message
    assert clock.now < drive_control.READER_TERM_GRACE_S


def test_shutdown_escalates_to_SIGKILL_only_after_the_whole_grace() -> None:
    run, clock = _Scripted(held=[0]), _Clock()
    _stop(run, clock)
    assert _base(run.calls[0])[-2:] == ["-TERM", "/dev/sr0"]
    assert run.sigkills(), "a reader still holding the drive must be killed"
    assert clock.now >= drive_control.READER_TERM_GRACE_S, (
        f"escalated after {clock.now}s, before the grace was out"
    )
    first_kill = next(i for i, c in enumerate(run.calls) if _base(c) in run.sigkills())
    assert all(_base(c) != ["fuser", "-s", "/dev/sr0"] for c in run.calls[first_kill:])


def test_shutdown_escalates_when_fuser_cannot_say_whether_the_drive_is_held() -> None:
    """Fail-safe direction: "not determined" is never read as "released", or a
    reader could be left ripping after the app has gone (2026-07-01)."""
    for held in ([None], [124]):
        run, clock = _Scripted(held=list(held)), _Clock()
        _stop(run, clock)
        assert run.sigkills(), f"{held}: no escalation on an undeterminable answer"


def test_a_reader_already_signalled_is_not_signalled_again() -> None:
    """cyanrip's second SIGTERM force-exits without the footer."""
    run, clock = _Scripted(held=[0, 1]), _Clock()
    _stop(run, clock, already_signalled=True)
    assert not any("-TERM" in c for c in run.calls), run.calls
    assert run.sigkills() == []


def test_nothing_on_the_host_to_SIGTERM_falls_back_to_the_broad_stop() -> None:
    """If the host sees no holder, the in-container fallback is all that is left."""
    run, clock = _Scripted(term_rc=1, kill_rc=1, held=[1]), _Clock()
    _stop(run, clock)
    assert [os.path.basename(c[0]) for c in run.calls][:1] == ["fuser"]
    assert any(os.path.basename(c[0]) in ("pkill", "distrobox") for c in run.calls)


def test_device_is_held_is_tri_state() -> None:
    assert drive_control.device_is_held("/dev/sr0", runner=_Recorder(0)) is True
    assert drive_control.device_is_held("/dev/sr0", runner=_Recorder(1)) is False
    assert drive_control.device_is_held("/dev/sr0", runner=_Recorder(124)) is None
    assert drive_control.device_is_held("", runner=_Recorder(0)) is None


def test_the_shutdown_grace_is_twice_the_longest_read_on_record() -> None:
    """The fork's round 30 lap 5 S17: a grace shorter than one read loses the log.

    cyanrip acts on SIGTERM only once the read in hand returns, so a grace shorter
    than a read SIGKILLs the reader before it writes its footer. The fork cited
    reads of 11 s; our own filed log from the same drive has one of 20 s, and
    their tree, searched whole, two of 21 s (their round 30 lap 7 S16, which
    found this test read only our tree). So the floor is read from the logs FILED
    IN THIS TREE (cyanrip's own `Read stalls:` summary line), not from a number in
    a comment, and the fork's longest is filed here too
    (`docs/handshake/inbound/artifacts/round-30-lap-07-accurip-gddc1e8c.log`), so
    the population is both trees'. The next longer read filed raises it.

    Only `.log` files count: the `.md` laps quote the line's FORMAT with
    invented values (`longest 187s`) taken from the fork's tests.
    """
    import re
    from pathlib import Path

    docs = Path(__file__).resolve().parents[1] / "docs"
    stall = re.compile(r"^Read stalls:\s.*?longest (?P<s>\d{1,5})s\b", re.M)
    longest: list[tuple[int, str]] = []
    for path in sorted(docs.rglob("*.log")):
        for match in stall.finditer(path.read_text(encoding="utf-8", errors="replace")):
            longest.append((int(match.group("s")), path.name))
    assert longest, (
        "no filed ripper log has a `Read stalls: … longest Ns` line, so this "
        "floor is checking nothing; if the line's wording moved, follow it"
    )
    worst, where = max(longest)
    assert worst >= 21, (
        f"the 21 s read in the fork's filed round 30 lap 7 artifact is gone: {longest}"
    )
    assert drive_control.READER_TERM_GRACE_S >= 2 * worst, (
        f"the SIGTERM grace is {drive_control.READER_TERM_GRACE_S:.0f}s and {where} "
        f"records a single read of {worst}s: a quit during such a read loses the "
        "log's footer"
    )
