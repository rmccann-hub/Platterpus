"""Tests for `platterpus.killable` — the one killable-subprocess implementation.

This module exists because the pattern was written twice (the cache probe, then
wanted again by the disc-info probe) and it is fiddly in ways that only show up on
real hardware: the process group, the cancel/startup race, and killing on timeout.
So it is implemented once and tested here once, thoroughly, rather than
re-tested at each call site — those only need to prove they *use* it.

**Several of these drive real child processes.** That is deliberate. The whole
point of the module is signalling a real OS process group, and a fake `Popen`
cannot demonstrate that a `killpg` actually reaches a grandchild — the stand-in
would be exactly the "kinder than reality" harness `docs/testing.md` §5.t warns
about. The children are `sh`/`sleep`, they are killed within milliseconds, and each
test bounds its own wait.
"""

from __future__ import annotations

import subprocess
import threading
import time

import pytest

from platterpus import killable
from platterpus.killable import KillableCommand


def test_a_normal_command_returns_a_completed_process() -> None:
    """The drop-in contract: same shape `subprocess.run` returned."""
    cmd = KillableCommand("test echo")
    result = cmd.run(["sh", "-c", "printf out; printf err >&2; exit 3"], timeout=30)

    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 3
    assert result.stdout == "out"
    assert result.stderr == "err"
    assert result.args == ["sh", "-c", "printf out; printf err >&2; exit 3"]
    assert not cmd.is_running(), "the slot was not cleared after the run finished"


def test_a_missing_binary_still_raises_filenotfounderror() -> None:
    """Callers translate this into their own error type; don't change the type."""
    cmd = KillableCommand("test missing")
    with pytest.raises(FileNotFoundError):
        cmd.run(["/nonexistent/definitely-not-a-real-binary"], timeout=5)
    assert not cmd.is_running()


def test_a_timeout_raises_and_kills_the_child() -> None:
    """`subprocess.run` killed on timeout; `Popen` does not for free.

    Migrating to `Popen` for cancellability would silently LOSE that, leaving a
    timed-out probe running with the disc spinning — the exact bug being fixed. So
    the timeout path kills, and this proves the child is gone rather than merely
    that the exception arrived.
    """
    cmd = KillableCommand("test timeout")
    with pytest.raises(subprocess.TimeoutExpired):
        cmd.run(["sh", "-c", "sleep 30"], timeout=0.3)

    assert not cmd.is_running()
    # The child was reaped by the kill, not left behind. `communicate` in the
    # timeout branch does that; a non-None returncode is the proof.
    assert cmd._proc is None


def test_cancel_from_another_thread_stops_a_running_child() -> None:
    """The real thing: a GUI-thread cancel ends work blocked on a worker thread.

    Times the run. If cancel did nothing, `sh -c 'sleep 30'` would sit there until
    the 30 s timeout and this test would take 30 seconds — so the elapsed-time
    assertion is the actual check, not decoration.
    """
    cmd = KillableCommand("test cancel")
    outcome: list[object] = []

    def _run() -> None:
        try:
            outcome.append(cmd.run(["sh", "-c", "sleep 30"], timeout=30))
        except BaseException as exc:  # noqa: BLE001 — record whatever happened
            outcome.append(exc)

    worker = threading.Thread(target=_run)
    started = time.monotonic()
    worker.start()

    # Wait for the child to actually exist before cancelling, so this exercises the
    # normal path rather than accidentally testing the startup race (which has its
    # own test below).
    deadline = time.monotonic() + 10
    while not cmd.is_running() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert cmd.is_running(), "the child never started"

    cmd.cancel()
    worker.join(15)
    elapsed = time.monotonic() - started

    assert not worker.is_alive(), "the worker never returned after cancel"
    assert elapsed < 10, (
        f"cancel took {elapsed:.1f}s — the child was not actually killed; it ran "
        "until something else stopped it. A cancel that does not interrupt the "
        "blocked call is the false promise CLAUDE.md rule 9 forbids."
    )
    assert outcome, "the run neither returned nor raised"
    assert not cmd.is_running(), "the slot was not cleared"


def test_a_cancel_that_lands_during_startup_is_not_lost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The registration race, which is silent when you get it wrong.

    Between `Popen` returning and the process being registered, a cancel would find
    an empty slot and return quietly — the user presses Cancel and the work runs to
    completion. The sticky flag closes it. Here the cancel is fired from *inside*
    `Popen`, which is precisely that window.

    **The child must still be ALIVE when the cancel lands, and it used not to be.**
    This ran `sh -c "exit 0"`, which can finish before `run` reads the sticky flag —
    and `_kill_group` correctly returns early on an already-exited child, so `killpg`
    is never called and the assertion below fails. That is the product being right and
    the TEST'S PREMISE being unmet: you cannot signal a process that has exited.

    It went red on CI's py3.13 runner on 2026-08-18 and had never failed locally; a
    probe here found the child still alive 200/200 times on this machine, which is
    exactly the shape of a race that only a loaded scheduler loses. Fixed by giving the
    child something to do (`sleep 30`) so the window it is testing genuinely exists.

    The spy now performs the **real** kill as well as recording it, for two reasons:
    the child would otherwise outlive the test and `communicate` would wait out its
    sleep, and asserting that a signal was *delivered* is a stronger claim than
    asserting a function was called. `getpgid` is left unpatched so the process group
    resolved is the real one — the child is a group leader (`start_new_session=True`),
    so the identity patch was only ever masking that.
    """
    cmd = KillableCommand("test startup race")
    killed: list[int] = []
    real_killpg = killable.os.killpg

    def _spy_killpg(pgid: int, sig: int) -> None:
        killed.append(sig)
        real_killpg(pgid, sig)

    monkeypatch.setattr(killable.os, "killpg", _spy_killpg)

    real_popen = killable.subprocess.Popen

    def _popen_then_cancel(*args: object, **kwargs: object) -> object:
        proc = real_popen(*args, **kwargs)  # type: ignore[arg-type]
        cmd.cancel()  # lands after the child exists, before it is registered
        return proc

    monkeypatch.setattr(killable.subprocess, "Popen", _popen_then_cancel)
    # A child that is unambiguously still running when the cancel lands. The timeout is
    # far below the sleep, so if the kill did NOT happen this fails as a timeout rather
    # than hanging the suite.
    cmd.run(["sh", "-c", "sleep 30"], timeout=15)

    assert killed, (
        "a cancel arriving during process startup was dropped — the cancel "
        "watermark is not covering the run that was already issued, so a Cancel "
        "press would silently do nothing."
    )
    # THE PROPERTY, NOT THE MECHANISM. This used to assert
    # `cmd._cancel_requested is False` — "the flag was reset for the next run" —
    # which described the old boolean rather than what a caller depends on. That
    # reset was itself the bug: it made the cancel's lifetime depend on which
    # thread unwound first, so a replacement probe started before it could kill
    # itself at birth. A watermark has nothing to reset, so the assertion is now
    # about the next run's fate, which is what the old one was standing in for.
    # Drop the patch first: it cancels on EVERY spawn, so leaving it installed
    # would cancel the follow-up on its own merits and the assertion would be
    # measuring the fixture rather than the module.
    monkeypatch.undo()
    followup = cmd.run(["sh", "-c", "echo next"], timeout=15)
    assert followup.returncode == 0 and "next" in (followup.stdout or ""), (
        "the run AFTER a cancelled one was killed too — a cancel must not "
        "outlive the run it was aimed at"
    )


def test_the_child_is_its_own_process_group_leader() -> None:
    """`start_new_session=True` is load-bearing, and this measures it.

    Two things depend on it. A `killpg` must reach the whole tree, because these
    commands are host wrappers that spawn podman which spawns the real tool —
    signalling only the direct child leaves the reader running. And *without* it the
    child shares OUR group, so a `killpg` would signal the GUI itself.

    So this asserts the child's process-group id differs from ours. A comment
    claiming the flag is set would not catch someone removing it; this does.
    """
    import os

    cmd = KillableCommand("test pgid")
    result = cmd.run(["sh", "-c", "ps -o pgid= -p $$"], timeout=30)
    child_pgid = int(result.stdout.strip())

    assert child_pgid != os.getpgid(0), (
        f"the child shares our process group ({child_pgid}) — a killpg would "
        "signal the GUI itself. start_new_session=True must not be removed."
    )


def test_cancel_kills_the_whole_group_not_just_the_direct_child() -> None:
    """The reason it is a group kill: a grandchild must die too.

    Models the real shape — host wrapper spawns podman spawns the reader — with a
    shell that spawns a `sleep` and then waits on it. If only the direct child were
    signalled, the grandchild would survive and (in production) keep the disc
    spinning after the user pressed Cancel.

    The sleep duration is deliberately odd so `pgrep` cannot match some other test's
    child and report a false survivor.
    """
    cmd = KillableCommand("test group kill")
    sentinel = "4747"
    argv = ["sh", "-c", f"sleep {sentinel} & wait"]

    outcome: list[object] = []

    def _run() -> None:
        try:
            outcome.append(cmd.run(argv, timeout=60))
        except BaseException as exc:  # noqa: BLE001 — record whatever happened
            outcome.append(exc)

    worker = threading.Thread(target=_run)
    worker.start()
    deadline = time.monotonic() + 10
    while not cmd.is_running() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert cmd.is_running(), "the child never started"

    # Let the grandchild actually exist before killing, else this proves nothing.
    grandchild_deadline = time.monotonic() + 10
    while time.monotonic() < grandchild_deadline:
        found = subprocess.run(
            ["pgrep", "-f", f"sleep {sentinel}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if found.stdout.strip():
            break
        time.sleep(0.05)
    else:  # pragma: no cover — the probe never got going
        pytest.fail("the grandchild never started; this probe would prove nothing")

    cmd.cancel()
    worker.join(20)
    assert not worker.is_alive(), "cancel did not unblock the run"

    # Give the kernel a moment to reap, then assert the grandchild is gone.
    gone_deadline = time.monotonic() + 10
    remaining = "?"
    while time.monotonic() < gone_deadline:
        found = subprocess.run(
            ["pgrep", "-f", f"sleep {sentinel}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        remaining = found.stdout.strip()
        if not remaining:
            break
        time.sleep(0.05)

    assert not remaining, (
        f"a grandchild survived the cancel (pids {remaining!r}). Only the direct "
        "child was signalled, so in production the in-container reader would keep "
        "holding the drive after the user cancelled."
    )


def test_cancel_is_safe_when_nothing_is_running() -> None:
    """Called from a dialog's close path, which may fire with no work in flight."""
    cmd = KillableCommand("test idle cancel")
    cmd.cancel()
    cmd.cancel()  # twice, too
    assert not cmd.is_running()
    # And the sticky flag must not poison the next legitimate run.
    result = cmd.run(["sh", "-c", "exit 0"], timeout=10)
    assert result.returncode in (0, -9), (
        "a stale cancel request killed the NEXT run. The flag is reset when a run "
        "ends, but an idle cancel sets it with no run to consume it."
    )


def test_an_overlapping_run_does_not_deregister_the_newer_child() -> None:
    """The bug this module introduced on day one, found by audit within the hour.

    One `KillableCommand` is shared by every `run_capture` caller, and two runs CAN
    overlap: the GUI supersedes an in-flight disc scan by starting a second one. The
    first version cleared the slot unconditionally in its `finally`, so when the
    *loser* finished it deregistered the *winner* — leaving the live child unkillable
    and `cancel()` a silent no-op from then on.

    That is the pre-flight checklist's "what new state does this fix create, and what
    tests that?" — the fix's own failure mode, which every original test missed
    because each ran a single child at a time.

    What is under test is the **identity check** in the `finally`, so the stand-in
    winner does not need to be alive: an already-exited `Popen` has a distinct object
    identity and keeps this test free of process-cleanup flakiness. No patching.
    """
    cmd = KillableCommand("test overlap")
    winner = subprocess.Popen(
        ["sh", "-c", "exit 0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    winner.communicate(timeout=10)

    outcome: list[object] = []

    def _run() -> None:
        try:
            # Long enough to be superseded from this thread, short enough to be fast.
            outcome.append(cmd.run(["sh", "-c", "sleep 0.6"], timeout=30))
        except BaseException as exc:  # noqa: BLE001
            outcome.append(exc)

    worker = threading.Thread(target=_run)
    worker.start()
    deadline = time.monotonic() + 10
    while not cmd.is_running() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert cmd.is_running(), "the first child never started"

    # A second probe takes the slot mid-run, exactly as "Rescan disc" does.
    with cmd._lock:
        cmd._proc = winner

    worker.join(20)
    assert not worker.is_alive(), "the first run never finished"
    assert outcome and not isinstance(outcome[0], BaseException), (
        f"the superseded run did not complete cleanly: {outcome}"
    )
    assert cmd._proc is winner, (
        "the finishing run deregistered the newer child. The live probe would then "
        "be unkillable and cancel() a no-op, defeating the whole module."
    )
    with cmd._lock:
        cmd._proc = None  # don't hand a later test a stale slot


def test_a_cancel_aimed_at_one_run_does_not_kill_the_next_one() -> None:
    """The rescan defect: a cancel must not reach a run started after it.

    `cancel()` is deliberately sticky so a cancel landing between `Popen` and
    registration is honoured rather than dropped — necessary, and pinned by
    `test_a_cancel_that_lands_during_startup_is_not_lost`. The first version
    implemented that as a boolean on the **slot**, cleared only by the cancelled
    run's own `finally`. That `finally` unwinds on another thread after a SIGKILL,
    and "Rescan disc" cancels the in-flight probe and starts its replacement
    immediately (`MainWindow._start_disc_scan` → `stop_thread(..., wait_ms=0)`),
    so the replacement could register while the flag was still set for its
    predecessor and kill itself at birth.

    **The interleaving is constructed, not raced.** Racing it — cancel, then start
    a thread — lets the cancelled run's `finally` win most of the time, and a test
    that passes against the bug proves nothing. The first attempt at this test did
    exactly that and passed, which is why the state is set up explicitly instead:
    `_proc` still points at the SIGKILLed predecessor, the cancel has been
    recorded, and the replacement then runs. Against the boolean this produced
    `returncode -9` with empty output — the same signature the 2026-08-19 rig run
    recorded for a rescan that never completed.
    """
    cmd = KillableCommand("test cancel scoping")

    # The predecessor: issued, registered, and already killed — but its `finally`
    # has not run yet, which is the whole window under test.
    predecessor = subprocess.Popen(
        ["sh", "-c", "exit 0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    predecessor.communicate(timeout=10)
    with cmd._lock:
        cmd._issued += 1
        cmd._proc = predecessor
    cmd.cancel()

    result = cmd.run(["sh", "-c", "sleep 0.3; echo alive"], timeout=30)

    assert result.returncode == 0, (
        "the replacement probe was killed at birth by the PREVIOUS run's cancel "
        f"(returncode {result.returncode!r}). On the rig this is a rescan whose "
        "scan never completes and which nothing retries."
    )
    assert "alive" in (result.stdout or ""), (
        "the replacement produced no output, so it did not run to completion"
    )


def test_the_cancel_watermark_still_stops_the_run_it_was_aimed_at() -> None:
    """The counter-test, and the reason the fix is a watermark and not a reset.

    Scoping the cancel must not quietly retire it. A run ISSUED before the cancel
    is still cancelled however late it registers — that is the startup race the
    stickiness exists for, and a fix that simply cleared the flag sooner would
    pass the test above while reopening this one.
    """
    cmd = KillableCommand("test cancel still bites")
    with cmd._lock:
        cmd._issued += 1  # a run has been issued and is mid-`Popen`
    cmd.cancel()  # the cancel lands in that window

    # That issued-but-unregistered run is sequence 1; the watermark must cover it.
    with cmd._lock:
        assert cmd._cancel_through >= 1, (
            "the cancel did not cover the run that was already issued — a cancel "
            "landing between Popen and registration would be silently dropped"
        )
