"""The uninstall runner and worker: bounded, logged, and cancel really kills.

CLAUDE.md rule 9: a ``cancel()`` that only sets a flag the blocked call never
reads is a false promise. These run real, harmless children (``sh``, ``sleep``)
so the kill is observed, not assumed.
"""

from __future__ import annotations

import logging
import sys
import threading
import time

import pytest

from platterpus.deps.uninstall_plan import Choices
from platterpus.deps.uninstall_runner import (
    CANCELLED,
    NOT_FOUND,
    TIMED_OUT,
    UninstallRunner,
)
from platterpus.workers.uninstall_worker import UninstallWorker


def test_output_and_exit_code_are_returned_and_a_failure_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    runner = UninstallRunner()
    assert runner.run(["sh", "-c", "echo hello"]) == (0, "hello\n")
    with caplog.at_level(logging.ERROR):
        rc, out = runner.run(["sh", "-c", "echo said-this >&2; exit 3"])
    assert rc == 3 and "said-this" in out
    assert "exit 3 from sh -c" in caplog.text and "said-this" in caplog.text


def test_a_missing_program_and_a_timeout_have_their_own_codes() -> None:
    runner = UninstallRunner()
    rc, out = runner.run(["platterpus-no-such-program-r190"])
    assert rc == NOT_FOUND and "command not found" in out
    rc, out = runner.run(["sleep", "5"], timeout=0.2)
    assert rc == TIMED_OUT and "timed out" in out
    assert runner.which("sh") and not runner.which("platterpus-no-such-program-r190")


def test_cancel_kills_the_command_in_flight_and_refuses_the_next() -> None:
    runner = UninstallRunner()
    started = time.monotonic()
    threading.Timer(0.3, runner.cancel).start()
    rc, _ = runner.run(["sleep", "30"], timeout=60)
    assert rc == CANCELLED
    assert time.monotonic() - started < 10, "cancel did not kill the child"
    assert runner.cancelled
    assert runner.run(["sh", "-c", "echo never"])[0] == CANCELLED


class _Engine:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.choices: Choices | None = None

    def scan(self) -> tuple[()]:
        if self.fail:
            raise RuntimeError("scan blew up")
        return ()

    def run(self, choices, progress=None, cancelled=None):
        self.choices = choices
        if self.fail:
            raise RuntimeError("removal blew up")
        return "report"


class _Killer:
    def __init__(self) -> None:
        self.cancels = 0

    def cancel(self) -> None:
        self.cancels += 1


def test_the_worker_always_finishes_even_when_the_engine_raises(qapp) -> None:
    for fail in (False, True):
        engine = _Engine(fail)
        worker = UninstallWorker(engine, _Killer(), Choices(keep_logs=True))  # type: ignore[arg-type]  # fake
        scanned: list[object] = []
        finished: list[object] = []
        worker.scanned.connect(scanned.append)
        worker.finished.connect(finished.append)
        worker.scan()
        worker.remove()
        assert scanned == [()]
        assert finished == [None, None if fail else "report"]
        assert engine.choices == Choices(keep_logs=True)


def test_worker_cancel_reaches_the_runner(qapp) -> None:
    killer = _Killer()
    worker = UninstallWorker(_Engine(), killer)  # type: ignore[arg-type]  # fake
    worker.cancel()
    assert killer.cancels == 1
    assert worker._cancelled


@pytest.mark.skipif(sys.platform != "linux", reason="process groups")
def test_worker_cancel_ends_a_real_blocked_command(qapp) -> None:
    runner = UninstallRunner()

    class _Blocking:
        def scan(self) -> tuple[()]:
            runner.run(["sleep", "30"], timeout=60)
            return ()

    worker = UninstallWorker(_Blocking(), runner)  # type: ignore[arg-type]  # fake
    thread = threading.Thread(target=worker.scan)
    started = time.monotonic()
    thread.start()
    time.sleep(0.3)
    worker.cancel()
    thread.join(10)
    assert not thread.is_alive(), "the blocked scan was not interrupted"
    assert time.monotonic() - started < 10
