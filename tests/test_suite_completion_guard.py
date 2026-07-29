"""Prove the suite cannot report green after dying mid-run.

The bug this file guards, stated exactly: `tests/conftest.py` deliberately ends
the session with `os._exit(status)` to dodge a PySide teardown abort. That makes
**any** `os._exit(0)` reached from product code indistinguishable from success —
status 0, no summary line, no coverage report, `--cov-fail-under` never
evaluated. On 2026-07-29 a test drove the update-relaunch path into the real
`os._exit` and the suite stopped at 76% of the way through: ~500 tests never ran,
and CI marked the job ✅.

Two independent things must hold, and each gets a test below:

1. **No test may reach the real `os._exit`.** The autouse `hard_exit_calls`
   fixture swaps in a stand-in that raises. (The seam it patches already existed
   and was documented as the way to test this — it had simply never been used,
   which is why the hazard was live in every test for five releases.)
2. **A run that dies anyway must not look green.** `pytest_sessionfinish` writes
   `.pytest-session-complete` as its last act; CI fails the job when that file is
   missing. This is deliberately an *external* check, because a truncated run
   cannot detect itself — the process is gone.

Test 2 runs a real child `pytest` because that is the only honest way to observe
a process dying: doing it in-process would kill this run too.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from conftest import SESSION_COMPLETE_SENTINEL, HardExitCalled

from platterpus import hard_exit

REPO_ROOT: Path = Path(__file__).resolve().parents[1]


def test_the_real_os_exit_is_not_reachable_from_a_test() -> None:
    """The autouse fixture is installed, and it does not merely record.

    A recording stub that *returns* would be a stand-in kinder than the real
    thing: `os._exit` never returns, so falling through lets a test execute code
    production can never reach. This asserts the stand-in is in place **and** that
    it stops the caller.
    """
    assert hard_exit._exit_fn is not __import__("os")._exit, (
        "the autouse hard_exit_calls fixture is not installed — the real os._exit "
        "is live in this test, and any product path that reaches it will end the "
        "whole session with status 0 while CI reads that as success."
    )

    with pytest.raises(HardExitCalled) as info:
        hard_exit.exit_without_teardown(3, "unit test")
    assert info.value.code == 3


def test_the_stand_in_records_every_requested_exit(hard_exit_calls: list[int]) -> None:
    """The fixture's list is usable for assertions, and survives being caught."""
    for code in (0, 7):
        with pytest.raises(HardExitCalled):
            hard_exit.exit_without_teardown(code, "unit test")
    assert hard_exit_calls == [0, 7]


def test_a_run_that_calls_os_exit_midway_leaves_no_completion_sentinel(
    tmp_path: Path,
) -> None:
    """The external check that would have caught the false green.

    Builds a two-test child suite whose *first* test calls the real `os._exit(0)`,
    exactly as the update-relaunch path did, and asserts three things about the
    child: it exits **0** (this is the trap — the status is a lie), it never
    reports the second test, and it leaves **no completion sentinel**.

    The sentinel absence is the whole point: it is the only one of those three
    signals a CI job can check cheaply and unambiguously.
    """
    suite = tmp_path / "tests"
    suite.mkdir()
    # A minimal conftest carrying just the sentinel protocol from the real one —
    # importing the project's conftest would drag in Qt and its own hard exit.
    (suite / "conftest.py").write_text(
        textwrap.dedent(
            f"""
            import os, sys, pytest
            from pathlib import Path

            SENTINEL = Path(r"{tmp_path}") / ".pytest-session-complete"

            def pytest_sessionstart(session):
                SENTINEL.unlink(missing_ok=True)

            @pytest.hookimpl(hookwrapper=True)
            def pytest_sessionfinish(session, exitstatus):
                yield
                status = int(session.exitstatus)
                sys.stdout.flush()
                SENTINEL.write_text(str(status))
                os._exit(status)
            """
        ),
        encoding="utf-8",
    )
    (suite / "test_a_dies.py").write_text(
        textwrap.dedent(
            """
            import os

            def test_this_one_ends_the_process():
                os._exit(0)   # what the un-stubbed relaunch path did
            """
        ),
        encoding="utf-8",
    )
    (suite / "test_b_never_runs.py").write_text(
        textwrap.dedent(
            """
            def test_this_one_should_never_be_reported():
                assert True
            """
        ),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, "-u", "-m", "pytest", "-p", "no:cacheprovider", str(suite)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=180,
    )

    # The trap, demonstrated: the status is 0. Anything that trusts the exit code
    # alone — GitHub Actions, a shell `&&` chain, a human reading a green tick —
    # concludes the suite passed.
    assert proc.returncode == 0, (
        "expected the child to exit 0 (that IS the bug). Got "
        f"{proc.returncode}; stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    # And it plainly did not finish.
    combined = proc.stdout + proc.stderr
    assert "2 passed" not in combined, (
        "the child suite reported both tests, so it did not actually die midway — "
        f"this probe is not exercising the failure any more. Output:\n{combined}"
    )
    assert not (tmp_path / ".pytest-session-complete").exists(), (
        "the truncated child left a completion sentinel behind, so the CI guard "
        "('Confirm the suite actually finished' in ci.yml) would pass for a run "
        "that never finished. The guard is worthless if this fires."
    )


def test_a_run_that_finishes_does_leave_a_completion_sentinel() -> None:
    """The floor under the test above: the sentinel must be *achievable*.

    "No sentinel" is a useless signal if a healthy run doesn't produce one either
    — the check would fail every build and get deleted. This session is itself a
    finishing run, so the file cannot exist *yet* (it is written at session
    finish), but `pytest_sessionstart` must have cleared any stale copy and the
    path must be somewhere writable.

    Asserting on a *previous* run's file would be worse than nothing: a stale
    sentinel is exactly what `pytest_sessionstart` deletes, because a leftover
    from yesterday would vouch for today.
    """
    assert SESSION_COMPLETE_SENTINEL.parent == REPO_ROOT, (
        "the sentinel moved out of the repo root; ci.yml looks for it there."
    )
    assert not SESSION_COMPLETE_SENTINEL.exists(), (
        "a completion sentinel exists while the session is still running, so "
        "pytest_sessionstart did not clear it — a stale file from an earlier run "
        "would vouch for this one."
    )
    assert SESSION_COMPLETE_SENTINEL.parent.is_dir()
