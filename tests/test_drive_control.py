"""Tests for platterpus.drive_control.

The runner is injected so we never touch a real drive or container. We assert
the right commands are issued and — crucially — the safety property earlier
attempts got wrong: no kill pattern may use `-f`, because a full-command-line
match can hit the GUI's own command line ("platterpus") or the pkill's own.
"""

from __future__ import annotations

import os
import signal
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
    the population is both trees'. The next longer read filed raises it, and one
    did: the 2026-10-04 rig run's damaged disc, a read of 54 s on track 18
    (`docs/handshake/artifactsround30/round30oct04full.log`).

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
    assert worst >= 54, (
        f"the 54 s read in the filed 2026-10-04 rig log is gone: {longest}"
    )
    assert drive_control.READER_TERM_GRACE_S >= 2 * worst, (
        f"the SIGTERM grace is {drive_control.READER_TERM_GRACE_S:.0f}s and {where} "
        f"records a single read of {worst}s: a quit during such a read loses the "
        "log's footer"
    )


# --- One SIGTERM per ripper (the fork's round 30 lap 9 S28) ---------------------
#
# The stand-in below DELIVERS signals instead of recording argv. `_Recorder` and
# `_Scripted` answer `fuser -k` with an exit code, so they cannot show which
# process a signal reached or that it was its second — which is exactly how a
# rescue that gave a native cyanrip a second SIGTERM passed every test here.


class _Proc:
    """A process holding the drive, and every signal it has received."""

    def __init__(self, pid: int, pgid: int, signals: tuple[str, ...] = ()) -> None:
        self.pid = pid
        self.pgid = pgid
        self.signals: list[str] = list(signals)

    @property
    def footer_written(self) -> bool:
        """cyanrip's own rule (`cyanrip@174a134:src/cyanrip_main.c:1216-1221`): the
        first SIGTERM sets `quit_now` and the log is signed on the way out; a second
        one `_exit(1)`s first, and SIGKILL runs nothing at all."""
        return self.signals.count("TERM") == 1 and "KILL" not in self.signals


class _Drive:
    """The host as `fuser` and `kill(2)` see it: who holds /dev/sr0, from one table.

    `run` answers the listing (`fuser <dev>`, in psmisc's merged form), the probe
    (`fuser -s <dev>`) and the kill (`fuser -s -k [-SIG] <dev>`, delivered to every
    holder, as fuser does). After `held_probes` probes have answered "held", the
    drive is let go. Everything else (pkill, distrobox) finds nothing.
    """

    def __init__(self, *procs: _Proc, held_probes: int = 10**9) -> None:
        self.procs = {p.pid: p for p in procs}
        self.held_probes = held_probes
        self.calls: list[list[str]] = []

    def run(self, argv: list[str]) -> SimpleNamespace:
        self.calls.append(argv)
        base = _base(argv)
        holders = list(self.procs.values())
        if base == ["fuser", "/dev/sr0"]:
            out = "/dev/sr0:" + "".join(f" {p.pid:>6}" for p in holders) + "\n"
            return SimpleNamespace(returncode=0 if holders else 1, stdout=out)
        if base[:3] == ["fuser", "-s", "-k"] and base[-1] == "/dev/sr0":
            sig = base[3].lstrip("-") if len(base) == 5 else "KILL"
            for proc in holders:
                proc.signals.append(sig)
            return SimpleNamespace(returncode=0 if holders else 1)
        if base == ["fuser", "-s", "/dev/sr0"]:
            if self.held_probes <= 0:
                self.procs.clear()
            self.held_probes -= 1
            return SimpleNamespace(returncode=0 if self.procs else 1)
        return SimpleNamespace(returncode=1)

    def kill(self, pid: int, sig: int) -> None:
        proc = self.procs.get(pid)
        if proc is None:
            raise ProcessLookupError(pid)
        proc.signals.append(signal.Signals(sig).name.removeprefix("SIG"))

    def pgid_of(self, pid: int) -> int:
        proc = self.procs.get(pid)
        if proc is None:
            raise ProcessLookupError(pid)
        return proc.pgid


#: A native cyanrip is its own process-group leader (started with
#: `start_new_session=True`); so is the wrapper, and the reader in the container
#: is in a group of its own, which the wrapper's killpg never reaches.
_CYANRIP, _WRAPPER, _READER = 700, 500, 900


def _reach(
    pid: int, pgid: int | None, sent_at: float = 0.0
) -> drive_control.SignalledRipper:
    return drive_control.SignalledRipper(pid=pid, pgid=pgid, sent_at=sent_at)


def _rescue(
    drive: _Drive, reached: drive_control.SignalledRipper | None, now: float
) -> str:
    return drive_control.term_unsignalled_holders(
        "/dev/sr0",
        reached,
        drive.run,  # type: ignore[arg-type]  # a fake runner
        clock=lambda: now,
        pgid_of=drive.pgid_of,
        kill=drive.kill,
    )


def test_the_old_rescue_call_gave_a_native_cyanrip_its_second_signal() -> None:
    """The finding, reproduced on the stand-in, which is also its proof it can fail.

    The rescue used to run `fuser -s -k -TERM <dev>` whoever held the drive. A
    native cyanrip that already had the cancel's SIGTERM, still in its read at
    +5 s, got a second one and lost its footer.
    """
    cyanrip = _Proc(_CYANRIP, _CYANRIP, signals=("TERM",))
    drive_control.free_device_holders(
        "/dev/sr0",
        runner=_Drive(cyanrip).run,  # type: ignore[arg-type]  # a fake runner
        signal="TERM",
    )
    assert cyanrip.signals == ["TERM", "TERM"]
    assert not cyanrip.footer_written


def test_native_path_the_rescue_inside_the_grace_sends_no_second_signal() -> None:
    cyanrip = _Proc(_CYANRIP, _CYANRIP, signals=("TERM",))  # the cancel's, at t=100
    drive = _Drive(cyanrip)
    outcome = _rescue(drive, _reach(_CYANRIP, _CYANRIP, sent_at=100.0), now=105.0)
    assert outcome == "refused"
    assert cyanrip.signals == ["TERM"], cyanrip.signals
    assert cyanrip.footer_written
    assert not any(_base(c)[:3] == ["fuser", "-s", "-k"] for c in drive.calls), (
        f"the blind device-scoped kill ran while our ripper was alive: {drive.calls}"
    )


def test_native_path_after_the_grace_the_rescue_signals_and_the_footer_is_lost() -> (
    None
):
    """What happens past the grace, said and pinned: the holder is signalled.

    That is cyanrip's second SIGTERM, so it exits with no footer. It is the point
    at which the rest of the cancel path has also stopped waiting for one (the
    worker's reap SIGKILLs the same process, `RipWorker._reap_ripper`). The rescue
    fires at +5 s, so this branch is reached only if the countdown is ever made
    longer than the grace, or the timer is held up (a suspended laptop).
    """
    grace = drive_control.READER_TERM_GRACE_S
    for now, expected in (
        (100.0 + grace - 0.01, ["TERM"]),
        (100.0 + grace, ["TERM", "TERM"]),
    ):
        cyanrip = _Proc(_CYANRIP, _CYANRIP, signals=("TERM",))
        _rescue(_Drive(cyanrip), _reach(_CYANRIP, _CYANRIP, sent_at=100.0), now)
        assert cyanrip.signals == expected, (now - 100.0, cyanrip.signals)


def test_wrapper_path_the_rescue_is_unchanged_once_the_wrapper_is_reaped() -> None:
    """The rig's path, as the 2026-10-05 cancel shows it: the wrapper exited at the
    cancel, so nothing our cancel signalled is running and the worker hands over
    `None`. The rescue is the same `fuser -s -k -TERM` it always was, and the
    reader in the container gets its first signal."""
    reader = _Proc(_READER, _READER)
    drive = _Drive(reader)
    assert _rescue(drive, None, now=5.0) == "signalled"
    assert reader.signals == ["TERM"] and reader.footer_written
    assert [_base(c) for c in drive.calls] == [
        ["fuser", "-s", "-k", "-TERM", "/dev/sr0"]
    ]


def test_wrapper_path_the_reader_is_signalled_even_while_the_wrapper_lingers() -> None:
    """The rescue's real purpose is kept when the wrapper has NOT been reaped yet:
    the reader in the container is not in the wrapper's process group, so the
    cancel never reached it, and it is signalled."""
    reader = _Proc(_READER, _READER)
    drive = _Drive(reader)
    assert _rescue(drive, _reach(_WRAPPER, _WRAPPER), now=5.0) == "signalled"
    assert reader.signals == ["TERM"] and reader.footer_written


def test_a_native_cyanrip_is_spared_and_any_other_holder_is_not() -> None:
    cyanrip = _Proc(_CYANRIP, _CYANRIP, signals=("TERM",))
    other = _Proc(800, 800)
    outcome = _rescue(_Drive(cyanrip, other), _reach(_CYANRIP, _CYANRIP), now=5.0)
    assert outcome == "signalled"
    assert cyanrip.signals == ["TERM"] and other.signals == ["TERM"]


def test_a_holder_in_the_signalled_process_group_is_spared_too() -> None:
    """The cancel's killpg reached the whole group: a cyanrip a `PATH` shim started
    as its child had the signal even though its PID is not the one we spawned."""
    child = _Proc(_CYANRIP + 1, _CYANRIP, signals=("TERM",))
    assert _rescue(_Drive(child), _reach(_CYANRIP, _CYANRIP), now=5.0) == "refused"
    assert child.signals == ["TERM"]


def test_when_fuser_cannot_name_the_holder_nothing_is_signalled() -> None:
    """Not determined is never guessed at: a guess could be the second signal."""
    cyanrip = _Proc(_CYANRIP, _CYANRIP, signals=("TERM",))
    drive = _Drive(cyanrip)
    calls: list[list[str]] = []

    def held_but_unnamed(argv: list[str]) -> SimpleNamespace:
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout="/dev/sr0:\n")

    outcome = drive_control.term_unsignalled_holders(
        "/dev/sr0",
        _reach(_CYANRIP, _CYANRIP),
        held_but_unnamed,  # type: ignore[arg-type]  # a fake runner
        clock=lambda: 5.0,
        pgid_of=drive.pgid_of,
        kill=drive.kill,
    )
    assert outcome == "not determined"
    assert cyanrip.signals == ["TERM"]
    assert [_base(c) for c in calls] == [["fuser", "/dev/sr0"]]


def test_second_signal_refusal_names_which_condition_refused() -> None:
    pgids = {_CYANRIP: _CYANRIP, _CYANRIP + 1: _CYANRIP, _READER: _READER}

    def pgid_of(pid: int) -> int:
        if pid not in pgids:
            raise ProcessLookupError(pid)
        return pgids[pid]

    grace = drive_control.READER_TERM_GRACE_S
    reached = _reach(_CYANRIP, _CYANRIP, sent_at=10.0)

    def refusal(pid: int, r: drive_control.SignalledRipper | None, now: float) -> str:
        return drive_control.second_signal_refusal(pid, r, now=now, pgid_of=pgid_of)

    refused = drive_control.REFUSED_ALREADY_SIGNALLED
    assert refusal(_CYANRIP, reached, 15.0) == refused
    assert refusal(_CYANRIP + 1, reached, 15.0) == refused  # same group
    assert refusal(_READER, reached, 15.0) == ""  # never reached by our signal
    assert refusal(_CYANRIP, reached, 10.0 + grace) == ""  # the grace is spent
    assert refusal(_CYANRIP, None, 15.0) == ""  # nothing of ours is running
    assert refusal(123, reached, 15.0) == drive_control.REFUSED_GONE
    assert refusal(os.getpid(), reached, 15.0) == drive_control.REFUSED_OWN_PROCESS
    # Only the single process was signalled (the group kill fell back): its group
    # mates had no signal, so only the PID itself is spared.
    single = _reach(_CYANRIP, None, sent_at=10.0)
    assert refusal(_CYANRIP, single, 15.0) == refused
    assert refusal(_CYANRIP + 1, single, 15.0) == ""


def test_parse_fuser_pids_reads_the_pids_and_never_the_devices_digit() -> None:
    parse = drive_control.parse_fuser_pids
    # psmisc 23.7's own merged output, measured 2026-10-05: the name and a colon
    # on stderr, the PIDs on stdout.
    assert parse("/tmp/tmpuqylzkx7:    28377 28380\n", "/tmp/tmpuqylzkx7") == (
        28377,
        28380,
    )
    assert parse("/dev/sr0:   4321m 4321\n", "/dev/sr0") == (4321,)
    assert parse(
        "Cannot stat file /proc/99/fd/3: Permission denied\n/dev/sr0:   4321\n",
        "/dev/sr0",
    ) == (4321,)
    assert parse("/dev/sr0:\n", "/dev/sr0") == ()
    # A path whose last word is a number: only the name's own `:` is removed, so
    # the `2` stays glued to its colon and is never read as PID 2.
    assert parse("/run/media/disc 2:   4321\n", "/run/media/disc 2") == (4321,)
    assert parse("/dev/sr0: " + "9" * 4301, "/dev/sr0") == ()
    assert parse("", "/dev/sr0") == ()


def test_device_holders_is_tri_state() -> None:
    def answering(rc: int | None, out: str = "") -> drive_control.Runner:
        def run(argv: list[str]) -> SimpleNamespace:
            return SimpleNamespace(returncode=rc, stdout=out)

        return run  # type: ignore[return-value]  # a fake runner

    holders = drive_control.device_holders
    assert holders("/dev/sr0", answering(0, "/dev/sr0:  12 34\n")) == (12, 34)
    assert holders("/dev/sr0", answering(1)) == ()
    assert holders("/dev/sr0", answering(124)) is None
    assert holders("/dev/sr0", answering(0, "/dev/sr0:\n")) is None
    assert holders("", answering(0, "/dev/sr0:  12\n")) is None


def _shutdown(
    drive: _Drive, clock: _Clock, reached: drive_control.SignalledRipper | None
) -> str:
    return drive_control.stop_reader_gracefully(
        "/dev/sr0",
        runner=drive.run,  # type: ignore[arg-type]  # a fake runner
        sleep=clock.sleep,
        clock=clock,
        reached=reached,
        pgid_of=drive.pgid_of,
        kill=drive.kill,
    )


def test_native_path_shutdown_lets_the_cyanrip_our_cancel_reached_sign_its_log() -> (
    None
):
    """Closing the window mid-rip cancels first, and on a native install that
    SIGTERM reached cyanrip itself. The graceful stop's own SIGTERM, milliseconds
    later, was its second; now it only waits for the drive to be let go."""
    cyanrip = _Proc(_CYANRIP, _CYANRIP, signals=("TERM",))
    drive = _Drive(cyanrip, held_probes=3)
    _shutdown(drive, _Clock(), _reach(_CYANRIP, _CYANRIP, sent_at=0.0))
    assert cyanrip.signals == ["TERM"] and cyanrip.footer_written, cyanrip.signals


def test_native_path_shutdown_SIGKILLs_only_after_the_whole_grace() -> None:
    cyanrip = _Proc(_CYANRIP, _CYANRIP, signals=("TERM",))
    clock = _Clock()
    _shutdown(_Drive(cyanrip), clock, _reach(_CYANRIP, _CYANRIP, sent_at=0.0))
    assert cyanrip.signals == ["TERM", "KILL"], cyanrip.signals
    assert clock.now >= drive_control.READER_TERM_GRACE_S


def test_wrapper_path_shutdown_still_TERMs_the_reader_its_cancel_never_reached() -> (
    None
):
    """The close's own cancel signalled the wrapper, which is still alive
    milliseconds later; the reader in the container is not in its group and is
    signalled exactly as before."""
    reader = _Proc(_READER, _READER)
    drive = _Drive(reader, held_probes=2)
    message = _shutdown(drive, _Clock(), _reach(_WRAPPER, _WRAPPER, sent_at=0.0))
    assert reader.signals == ["TERM"] and reader.footer_written, reader.signals
    assert "allowed to finish" in message
