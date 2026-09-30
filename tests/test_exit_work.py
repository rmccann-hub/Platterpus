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
