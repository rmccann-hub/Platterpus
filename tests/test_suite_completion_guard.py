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
from conftest import SESSION_COMPLETE_SENTINEL, HardExitCalled, pytest_sessionstart

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


def test_session_start_clears_a_stale_sentinel() -> None:
    """The floor under the test above: the sentinel must be *achievable*, and a
    leftover from an earlier run must never vouch for this one.

    This asserts the MECHANISM (`pytest_sessionstart` unlinks the file) rather than
    the ambient fact "no sentinel exists right now". The first draft did the
    latter, and it was wrong in a way worth recording: the sentinel path is a
    single fixed file in the repo root, so *anything else* that finishes a pytest
    session in the same checkout — a parallel agent, a second terminal, a child
    run — creates it and the assertion fires for a reason that has nothing to do
    with the property. It failed exactly that way during a concurrent session.

    A test that can go red for an unrelated reason is a test that eventually gets
    deleted, and this one guards the check that stops a truncated suite reporting
    green. So it is now hermetic: create a stale file, run the hook, assert it is
    gone, and put it back the way it was.
    """
    assert SESSION_COMPLETE_SENTINEL.parent == REPO_ROOT, (
        "the sentinel moved out of the repo root; ci.yml looks for it there."
    )
    assert SESSION_COMPLETE_SENTINEL.parent.is_dir()

    # Preserve whatever is really there, so this test cannot disturb the run it is
    # part of (its own session-finish will rewrite the file afterwards).
    existed = SESSION_COMPLETE_SENTINEL.exists()
    previous = SESSION_COMPLETE_SENTINEL.read_text() if existed else None
    try:
        SESSION_COMPLETE_SENTINEL.write_text("stale from an earlier run\n")
        assert SESSION_COMPLETE_SENTINEL.exists(), (
            "the sentinel path must be writable, or the guard can never fire"
        )
        # The real hook, called directly. `session` is unused by it, so None is
        # honest here rather than a fake that pretends to be a pytest.Session.
        pytest_sessionstart(None)  # type: ignore[arg-type]  # hook ignores it
        assert not SESSION_COMPLETE_SENTINEL.exists(), (
            "pytest_sessionstart left a stale sentinel in place — a leftover from "
            "an earlier run would then vouch for this one, and CI's 'did the suite "
            "finish' guard would pass for a run that died midway"
        )
    finally:
        if previous is not None:
            SESSION_COMPLETE_SENTINEL.write_text(previous)
