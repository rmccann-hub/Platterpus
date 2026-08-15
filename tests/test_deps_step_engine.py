# SPDX-License-Identifier: GPL-3.0-only
"""Tests for the shared host step-engine vocabulary (deps/step_engine).

Most of the module is types + a Protocol the engines inject a *fake* runner
against, so the production :class:`SubprocessRunner` — the only code that
actually shells out — is otherwise unexercised. These tests pin its contract,
especially the two error sentinels the setup/teardown pipelines branch on:
a missing command → 127, a timeout → 124 (never an exception that would crash
the worker mid-pipeline)."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import pytest

from platterpus.deps.step_engine import (
    StepResult,
    StepStatus,
    SubprocessRunner,
    one_line_argv,
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


# --- Diagnostic capture: the output must reach the log ----------------------


def test_a_failing_command_logs_its_exit_code_and_output(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """REGRESSION (2026-08-04). The runner logged the argv and DISCARDED the output.

    `HostSetup._run_commands` then reduced that output to its last line for the UI,
    so a failed `git`/`meson`/`ninja` inside the container left exactly one line of
    evidence anywhere in the system — and the log file a user is asked to attach to
    a bug report contained none of it. Found while trying to diagnose a real fork
    build failure with nothing to go on.

    Captured-and-discarded is worse than never captured: the report still looks
    complete (CLAUDE.md, diagnostic completeness).
    """
    with caplog.at_level(logging.ERROR, logger="platterpus.deps.step_engine"):
        rc, out = SubprocessRunner().run(
            [
                sys.executable,
                "-c",
                "import sys; print('stdout marker'); "
                "print('fatal: the explaining line', file=sys.stderr); "
                "sys.exit(3)",
            ]
        )

    assert rc == 3
    logged = caplog.text
    assert "exit 3" in logged, "the exit code is not in the log"
    assert "stdout marker" in logged, "stdout was swallowed"
    assert "fatal: the explaining line" in logged, "stderr was swallowed"
    # And the caller still receives it, so the UI can show the last line.
    assert "fatal: the explaining line" in out


def test_a_successful_command_does_not_shout_but_is_still_recoverable(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Success logs at DEBUG: a normal run stays readable, `debug_logging` gets all."""
    with caplog.at_level(logging.ERROR, logger="platterpus.deps.step_engine"):
        SubprocessRunner().run([sys.executable, "-c", "print('quiet success')"])
    assert "quiet success" not in caplog.text, "a success should not log at ERROR"

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="platterpus.deps.step_engine"):
        SubprocessRunner().run([sys.executable, "-c", "print('quiet success')"])
    assert "quiet success" in caplog.text, "debug logging must capture the transcript"


def test_bounded_output_keeps_the_tail_and_counts_the_gap() -> None:
    """The TAIL is the half that must survive — a fatal message is printed last.

    A head-only cap drops precisely the line that explains the failure while still
    looking like a complete capture, and an *unmarked* gap reads as a command that
    fell silent rather than one that was elided.
    """
    from platterpus.deps.step_engine import (
        _OUTPUT_HEAD_LINES,
        _OUTPUT_TAIL_LINES,
        _bounded_output,
    )

    short = "\n".join(f"line{i}" for i in range(5))
    assert _bounded_output(short) == short, "short output must pass through verbatim"

    total = _OUTPUT_HEAD_LINES + _OUTPUT_TAIL_LINES + 400
    kept = _bounded_output("\n".join(f"line{i}" for i in range(total))).splitlines()
    assert kept[0] == "line0"
    assert kept[-1] == f"line{total - 1}", "the tail was dropped"
    marker = kept[_OUTPUT_HEAD_LINES]
    assert "omitted" in marker and "400" in marker, f"gap not counted: {marker!r}"


class TestArgvIsLoggedOnOneLine:
    """A multi-line `sh -c` script must not become 100 log lines.

    Reported from real use, 2026-08-15: `--install-ripper` printed its own shell
    scripts at the operator between progress rows, because the step engine logs
    each command at INFO and several commands *are* multi-line scripts. The log
    goes to the terminal as well as the file, so good diagnostics produced
    unusable output.

    The fix must not lose anything: recording the exact argv is the obligation
    that makes a run diagnosable, and the same day proved what its absence
    costs. So this pins both halves — one line, and nothing dropped.
    """

    SCRIPT = "set -eu\necho one\necho two\n"

    def test_a_multiline_script_becomes_a_single_line(self) -> None:
        rendered = one_line_argv(["sh", "-c", self.SCRIPT, "label"])
        assert "\n" not in rendered, (
            f"the argv still spans multiple lines: {rendered!r}"
        )
        assert rendered.count("\\n") == 3, "the newlines were dropped, not escaped"

    def test_nothing_is_lost(self) -> None:
        """The non-triviality floor, and the one that matters: a truncating
        'fix' would satisfy the single-line test while destroying the record."""
        rendered = one_line_argv(["sh", "-c", self.SCRIPT])
        for token in ("set -eu", "echo one", "echo two"):
            assert token in rendered, f"{token!r} vanished from the logged argv"

    @staticmethod
    def _unescape(text: str) -> str:
        """A correct inverse: parse left to right, one escape at a time.

        Chained `str.replace` calls are NOT a valid inverse of backslash
        escaping, and the first version of this test used them and failed on
        `back\\nslash` — a literal backslash followed by the letter n. Escaping
        gives `back\\\\nslash`; replacing `\\n` first then matches the *second*
        backslash and turns it into a newline. The encoding is unambiguous; a
        naive decoder is not, which is exactly the sort of "looks equivalent"
        shortcut this project keeps finding in its own checks.
        """
        out: list[str] = []
        i = 0
        while i < len(text):
            if text[i] == "\\" and i + 1 < len(text):
                nxt = text[i + 1]
                mapped = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\"}.get(nxt)
                if mapped is not None:
                    out.append(mapped)
                    i += 2
                    continue
            out.append(text[i])
            i += 1
        return "".join(out)

    def test_the_escaping_is_reversible(self) -> None:
        """A log line you cannot turn back into the command is a summary, not a
        record. Tested per-argument: splitting the joined line on spaces would be
        meaningless, since arguments legitimately contain spaces."""
        for original in (
            "set -eu\nrm -rf /\n",
            "a\tb",
            "carriage\rreturn",
            "back\\slash",
            "back\\nslash-that-looks-escaped",
            "trailing-backslash\\",
            "",
            "plain",
        ):
            rendered = one_line_argv([original])
            assert "\n" not in rendered and "\r" not in rendered
            restored = self._unescape(rendered)
            assert restored == original, (
                f"{original!r} did not survive the round trip: "
                f"rendered={rendered!r} restored={restored!r}"
            )

    def test_an_ordinary_command_is_unchanged(self) -> None:
        """Most commands have no newlines and must read exactly as before."""
        assert one_line_argv(["distrobox", "list"]) == "distrobox list"

    def test_the_runner_uses_it(self) -> None:
        """A helper nothing calls is the shape this project has shipped before."""
        import inspect

        src = inspect.getsource(SubprocessRunner.run)
        assert "one_line_argv" in src, "the runner still joins argv raw"
        assert '" ".join(argv)' not in src
