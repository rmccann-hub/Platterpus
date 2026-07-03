# SPDX-License-Identifier: GPL-3.0-only
"""Tests for the shared host step-engine vocabulary (deps/step_engine).

Most of the module is types + a Protocol the engines inject a *fake* runner
against, so the production :class:`SubprocessRunner` — the only code that
actually shells out — is otherwise unexercised. These tests pin its contract,
especially the two error sentinels the setup/teardown pipelines branch on:
a missing command → 127, a timeout → 124 (never an exception that would crash
the worker mid-pipeline)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from platterpus.deps.step_engine import (
    StepResult,
    StepStatus,
    SubprocessRunner,
)

# --- StepResult.ok: which statuses count as success -------------------------


@pytest.mark.parametrize(
    ("status", "ok"),
    [
        (StepStatus.DONE, True),
        (StepStatus.RAN, True),
        (StepStatus.WOULD_RUN, True),
        (StepStatus.FAILED, False),
        (StepStatus.CANCELLED, False),
        (StepStatus.RUNNING, False),
    ],
)
def test_step_result_ok_maps_status(status: StepStatus, ok: bool) -> None:
    assert StepResult("id", "title", status).ok is ok


# --- SubprocessRunner.which / exists ----------------------------------------


def test_which_finds_a_real_command_and_rejects_a_missing_one() -> None:
    runner = SubprocessRunner()
    assert runner.which("sh") is True
    assert runner.which("platterpus-definitely-not-a-real-command") is False


def test_exists_reflects_the_filesystem(tmp_path: Path) -> None:
    runner = SubprocessRunner()
    present = tmp_path / "here"
    present.write_text("x")
    assert runner.exists(present) is True
    assert runner.exists(tmp_path / "absent") is False


# --- SubprocessRunner.run: success + the 127/124 error sentinels ------------


def test_run_returns_rc_and_combined_output() -> None:
    runner = SubprocessRunner()
    rc, out = runner.run(
        [sys.executable, "-c", "import sys; print('hi'); sys.stderr.write('err')"]
    )
    assert rc == 0
    # stdout + stderr are concatenated so a caller sees everything a step said.
    assert "hi" in out and "err" in out


def test_run_missing_command_is_127_not_an_exception() -> None:
    # A step whose binary isn't installed must degrade to the 127 sentinel the
    # pipeline understands — never raise FileNotFoundError into the worker.
    runner = SubprocessRunner()
    rc, out = runner.run(["platterpus-no-such-binary-xyz", "--version"])
    assert rc == 127
    assert "command not found" in out
    assert "platterpus-no-such-binary-xyz" in out


def test_run_timeout_is_124_not_an_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    # A hung install (dnf/image pull wedged) must surface as the 124 sentinel,
    # not a TimeoutExpired that aborts the whole pipeline.
    def fake_run(*_a: object, **_k: object) -> object:
        raise subprocess.TimeoutExpired(cmd="sleep", timeout=1800.0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    rc, out = SubprocessRunner().run(["sleep", "99999"])
    assert rc == 124
    assert "timed out" in out
