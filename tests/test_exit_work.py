"""Work the process finishes after the window has gone (`exit_work`).

Round 30's S17: quitting mid-rip hands the stop of the ripper to a helper thread,
so the window closes at once, and `app.main` joins that thread before the process
exits. These tests pin the three properties that rests on: the join really
waits, it is bounded, and a failure inside the work does not escape.
"""

from __future__ import annotations

import inspect
import threading
from collections.abc import Iterator

import pytest

from platterpus import exit_work


@pytest.fixture(autouse=True)
def _no_leftover_jobs() -> Iterator[None]:
    """Each test starts, and ends, with no exit work pending."""
    assert exit_work.wait(margin_s=5.0)
    yield
    assert exit_work.wait(margin_s=5.0)


def test_wait_joins_the_work_before_returning() -> None:
    done = threading.Event()
    release = threading.Event()

    def work() -> None:
        release.wait(5)
        done.set()

    exit_work.start(work, name="test", budget_s=5.0)
    assert exit_work.pending() == 1
    release.set()
    assert exit_work.wait() is True
    assert done.is_set(), "wait() returned before the work had finished"
    assert exit_work.pending() == 0


def test_wait_is_bounded_and_says_the_work_did_not_finish(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A job past its budget is left, and the log says what is not known done."""
    release = threading.Event()
    exit_work.start(lambda: release.wait(10), name="stuck", budget_s=0.0)
    try:
        assert exit_work.wait(margin_s=0.2) is False
        assert "did not finish within its budget" in caplog.text
        assert "'stuck'" in caplog.text
    finally:
        release.set()


def test_a_failure_inside_the_work_is_logged_and_not_raised(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def work() -> None:
        raise OSError("fuser is not installed")

    exit_work.start(work, name="boom", budget_s=5.0)
    assert exit_work.wait() is True
    assert "exit work 'boom' failed" in caplog.text
    assert "fuser is not installed" in caplog.text


def test_the_work_runs_off_the_calling_thread() -> None:
    seen: list[int] = []
    exit_work.start(lambda: seen.append(threading.get_ident()), name="x", budget_s=5)
    assert exit_work.wait()
    assert seen and seen[0] != threading.get_ident()


def test_app_main_joins_exit_work_before_it_decides_how_to_exit() -> None:
    """The join is the whole point: without it, the interpreter's exit kills the
    helper part-way through stopping the reader, and cyanrip keeps the drive
    after the app has gone (the 2026-07-01 report). It must come after the event
    loop ends and before `hard_exit`, which may leave with `os._exit`."""
    from platterpus import app

    source = inspect.getsource(app.main)
    loop = source.index("app.exec()")
    join = source.index("exit_work.wait()")
    exit_check = source.index("hard_exit.exit_now_if_threads_abandoned(status)")
    assert loop < join < exit_check, (
        "app.main must run the event loop, then join exit work, then decide how to exit"
    )


# --- The exit check (`exit_work.audit`), asked for 2026-10-05 -----------------


class _Proc:
    """What `subprocess.run` returns, as far as `drive_control` reads it."""

    def __init__(self, returncode: int | None, stdout: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


def _host(fuser_rc: int | None, pgrep_rc: int | None, pgrep_out: str = ""):  # type: ignore[no-untyped-def]  # a runner stand-in
    """A runner answering `fuser` and `pgrep` the way the host would."""
    calls: list[list[str]] = []

    def run(argv: list[str]) -> _Proc:
        calls.append(argv)
        tool = argv[0].rsplit("/", 1)[-1]
        if tool == "fuser":
            return _Proc(fuser_rc)
        if tool == "pgrep":
            return _Proc(pgrep_rc, pgrep_out)
        raise AssertionError(f"the exit check ran something unexpected: {argv}")

    run.calls = calls  # type: ignore[attr-defined]  # inspected by the tests
    return run


def test_the_exit_check_says_nothing_was_left_behind_only_when_both_probes_agree(
    caplog: pytest.LogCaptureFixture,
) -> None:
    run = _host(fuser_rc=1, pgrep_rc=1)
    with caplog.at_level("INFO", logger="platterpus.exit_work"):
        result = exit_work.audit("/dev/sr0", runner=run)
    assert result.clean is True
    assert [argv[0].rsplit("/", 1)[-1] for argv in run.calls] == ["fuser", "pgrep"]
    assert "nothing holds /dev/sr0" in caplog.text
    assert "no ripper process is running" in caplog.text
    assert "left nothing behind" in caplog.text


def test_the_exit_check_names_a_ripper_left_running_and_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    run = _host(fuser_rc=0, pgrep_rc=0, pgrep_out="4242 cyanrip\n")
    with caplog.at_level("WARNING", logger="platterpus.exit_work"):
        result = exit_work.audit("/dev/sr0", runner=run)
    assert result.clean is False
    assert result.readers == ("4242 cyanrip",)
    assert "/dev/sr0 is STILL HELD" in caplog.text
    assert "4242 cyanrip" in caplog.text
    assert any(r.levelname == "WARNING" for r in caplog.records)


def test_no_answer_is_never_read_as_all_clear(caplog: pytest.LogCaptureFixture) -> None:
    """A probe that could not run is `None`, and the line says it does not know."""
    run = _host(fuser_rc=None, pgrep_rc=None)
    with caplog.at_level("WARNING", logger="platterpus.exit_work"):
        result = exit_work.audit("/dev/sr0", runner=run)
    assert result.clean is None
    assert "not known" in caplog.text
    assert "left nothing behind" not in caplog.text


def test_with_no_drive_in_use_the_check_still_looks_for_a_ripper() -> None:
    run = _host(fuser_rc=0, pgrep_rc=0, pgrep_out="77 cyanrip\n")
    result = exit_work.audit("", runner=run)
    assert result.device_held is None
    assert result.clean is False, (
        "a running ripper is left behind with or without a drive"
    )
    assert [argv[0].rsplit("/", 1)[-1] for argv in run.calls] == ["pgrep"]


def test_app_main_runs_the_exit_check_after_the_exit_work() -> None:
    """After the join, so it sees what the stop left; before `hard_exit`, which may
    leave with `os._exit` and skip anything after it."""
    from platterpus import app

    source = inspect.getsource(app.main)
    join = source.index("exit_work.wait()")
    check = source.index("exit_work.audit(audit_device)")
    assert source.index("window.exit_audit_device()") < check
    leave = source.index("hard_exit.exit_now_if_threads_abandoned(status)")
    assert join < check < leave


# --- Freeing the drive after a cancelled ripper child (2026-11-05) -------------
#
# `drive_frees` (tests/conftest.py, autouse) records each drive_control step in
# place of running it, so these read which stop was chosen for which drive.


def test_a_cancelled_rip_gets_the_graceful_stop_and_a_probe_the_sigkill(
    drive_frees: list[tuple[str, str]],
) -> None:
    """The kind of stop follows what the child writes: a rip's log needs its footer."""
    assert exit_work.free_drive_after_cancel("/dev/sr5", writes_log=True, why="t")
    assert exit_work.free_drive_after_cancel("/dev/sr6", writes_log=False, why="t")
    assert exit_work.wait()
    assert sorted(drive_frees) == [("probe", "/dev/sr6"), ("rip", "/dev/sr5")]


def test_a_second_cancel_of_the_same_drive_does_not_start_a_competing_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A SIGKILL racing a graceful stop's grace would cost the rip its footer.

    The first stop is held open; a second request for the same drive while it
    runs starts nothing, and once it has finished a new request starts again.
    """
    release = threading.Event()
    started: list[str] = []

    def held_stop(device: str, _run: object) -> None:
        started.append(device)
        release.wait(10.0)

    monkeypatch.setattr(exit_work, "rip_reader_stop", held_stop)
    monkeypatch.setattr(exit_work, "probe_reader_stop", held_stop)
    try:
        assert exit_work.free_drive_after_cancel("/dev/sr5", writes_log=True, why="a")
        assert exit_work.freeing("/dev/sr5")
        assert not exit_work.free_drive_after_cancel(
            "/dev/sr5", writes_log=False, why="b"
        ), "a second stop of a drive already being freed was started"
    finally:
        release.set()
    assert exit_work.wait()
    assert started == ["/dev/sr5"]
    assert not exit_work.freeing("/dev/sr5")
    assert exit_work.free_drive_after_cancel("/dev/sr5", writes_log=True, why="c")
    assert exit_work.wait()
    assert started == ["/dev/sr5", "/dev/sr5"]


def test_no_device_frees_nothing_and_says_so(
    drive_frees: list[tuple[str, str]], caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("WARNING", logger="platterpus.exit_work"):
        assert not exit_work.free_drive_after_cancel("", writes_log=True, why="t")
    assert drive_frees == []
    assert "NOT DETERMINED" in caplog.text


def test_the_real_steps_are_the_drive_control_ones() -> None:
    """What the recorders stand in for: device-scoped SIGKILL for a probe (never
    `free_drive`'s broad pkill), `stop_reader_gracefully` for a rip. Read off the
    source, because running them would signal a real drive."""
    probe = inspect.getsource(exit_work._sigkill_probe_reader)
    rip = inspect.getsource(exit_work._stop_rip_reader)
    assert "drive_control.free_device_holders(" in probe
    assert "free_drive(" not in probe.replace("free_drive(s)", "")
    assert "drive_control.stop_reader_gracefully(" in rip
