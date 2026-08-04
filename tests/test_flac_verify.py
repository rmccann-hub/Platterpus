"""Tests for the post-rip FLAC encode-verify adapter + worker.

The `flac` subprocess is injected (a fake runner), so these run with no real
binary. The contract: never raise; distinguish "couldn't run" (error) from
"a file failed" (failures).
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import pytest

from platterpus.adapters import flac_verify as fv
from platterpus.adapters import tool_run
from platterpus.adapters.flac_verify import FlacVerifyResult, verify_flac_files
from platterpus.adapters.tool_run import ToolRun
from platterpus.workers.flac_verify_worker import verify_rip_dir

# --- adapter: verify_flac_files -------------------------------------------


def test_the_real_runner_captures_exit_code_argv_and_complete_output(
    monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    """The real runner must carry flac's own words OUT, not merely log them.

    Was: it logged the last stderr line and returned an `int`, so the reason could
    not reach the result, the report, or the user. Asserts all four facts
    CLAUDE.md's diagnostic-completeness rule names — exit code, exact argv, complete
    output, and a readable sentence — plus that it still reaches the log.
    """

    class _Proc:
        returncode = 1
        args = ["flac", "--test", "x.flac"]
        stdout = "some warning\nERROR: got error while decoding\n"

    monkeypatch.setattr(tool_run.subprocess, "run", lambda *a, **k: _Proc())
    with caplog.at_level(logging.WARNING):
        run = fv._default_runner(["flac", "--test", "x.flac"])

    assert run.exit_code == 1
    assert run.argv == ("flac", "--test", "x.flac")
    # COMPLETE output, not a tail: the earlier warning survives too.
    assert "some warning" in run.output
    assert "got error while decoding" in run.output
    assert "got error while decoding" in run.summary
    # And it still reaches the log file, via the diagnostics collector.
    assert "got error while decoding" in caplog.text
    assert "platterpus-diagnostic" in caplog.text


def test_all_pass() -> None:
    seen: list[list[str]] = []

    def runner(argv: list[str]) -> ToolRun:
        seen.append(argv)
        return ToolRun.of(0)

    paths = [Path("01.flac"), Path("02.flac")]
    result = verify_flac_files(paths, binary="flac", runner=runner)

    assert result.ok and result.ran
    assert result.checked == 2
    assert result.failures == ()
    # `--silent` is deliberately NOT passed: it suppresses the message that explains
    # a failure, which is the one thing this pass exists to be able to quote.
    assert seen[0] == ["flac", "--test", "01.flac"]
    assert "--silent" not in seen[0]


def test_one_file_fails_and_the_result_carries_what_flac_said() -> None:
    def runner(argv: list[str]) -> ToolRun:
        if argv[-1].endswith("02.flac"):
            return ToolRun.of(1, "02.flac: ERROR while decoding data\n", tuple(argv))
        return ToolRun.of(0)

    result = verify_flac_files([Path("01.flac"), Path("02.flac")], runner=runner)

    assert not result.ok and result.ran
    assert result.checked == 2
    assert result.failures == (Path("02.flac"),)
    # THE REGRESSION: the reason must travel with the result, not only to the log.
    assert len(result.failure_details) == 1
    detail = result.failure_details[0]
    assert detail.path == Path("02.flac")
    assert detail.run.exit_code == 1
    assert "ERROR while decoding data" in detail.run.output
    assert "ERROR while decoding data" in detail.reason
    assert result.reasons() == ("02.flac: exit 1: 02.flac: ERROR while decoding data",)


def test_missing_binary_is_an_error_not_a_failure() -> None:
    def runner(argv: list[str]) -> ToolRun:
        return ToolRun.failed_to_run("'flac' not found", tuple(argv))

    result = verify_flac_files([Path("01.flac")], runner=runner)

    assert not result.ran  # couldn't even run → error, not a "corrupt file"
    assert not result.ok
    assert result.failures == ()
    assert "not found" in result.error


def test_timeout_marks_the_file_failed_and_names_the_duration() -> None:
    def runner(argv: list[str]) -> ToolRun:
        return ToolRun.timed_out(
            "timed out after 120s (child killed, never reaped)", argv=tuple(argv)
        )

    result = verify_flac_files([Path("01.flac")], runner=runner)

    # It ran — the tool works and wedged on THIS file — so blame the file, not the
    # pass. `started` is what separates the two; `ran` alone could not.
    assert result.ran
    assert result.failures == (Path("01.flac"),)
    assert "120s" in result.failure_details[0].reason
    # Tri-state: a killed child has NO exit code, and must never read as 0.
    assert result.failure_details[0].run.exit_code is None


def test_a_run_that_never_started_aborts_the_pass() -> None:
    def runner(argv: list[str]) -> ToolRun:
        return ToolRun.failed_to_run("could not run flac: permission denied")

    result = verify_flac_files([Path("01.flac")], runner=runner)

    assert not result.ran
    assert "could not run" in result.error


def test_empty_input() -> None:
    result = verify_flac_files([], runner=lambda argv: ToolRun.of(0))
    assert result.checked == 0
    assert result.failures == ()
    assert result.ran


# --- worker: verify_rip_dir -----------------------------------------------


def test_worker_no_flacs(tmp_path: Path) -> None:
    result = verify_rip_dir(tmp_path)
    assert not result.ran
    assert "no FLAC files" in result.error


def test_worker_passes_sorted_flacs_to_verifier(tmp_path: Path) -> None:
    (tmp_path / "02 - B.flac").write_bytes(b"")
    (tmp_path / "01 - A.flac").write_bytes(b"")
    seen: list[list[Path]] = []

    def verifier(paths: list[Path]) -> FlacVerifyResult:
        seen.append(paths)
        return FlacVerifyResult(checked=len(paths))

    result = verify_rip_dir(tmp_path, verifier=verifier)

    assert result.checked == 2
    assert [p.name for p in seen[0]] == ["01 - A.flac", "02 - B.flac"]  # sorted


def test_worker_joins_wait_for_first(tmp_path: Path) -> None:
    (tmp_path / "01.flac").write_bytes(b"")
    order: list[str] = []
    gate = threading.Event()

    def pre_work() -> None:
        gate.wait(2.0)
        order.append("pre")

    pre = threading.Thread(target=pre_work)
    pre.start()

    def verifier(paths: list[Path]) -> FlacVerifyResult:
        order.append("verify")
        return FlacVerifyResult(checked=len(paths))

    gate.set()  # let the pre-work finish
    verify_rip_dir(tmp_path, wait_for=pre, verifier=verifier)

    assert order == ["pre", "verify"]  # waited for the pre thread before verifying
    assert not pre.is_alive()


def test_worker_never_raises_when_verifier_explodes(tmp_path: Path) -> None:
    (tmp_path / "01.flac").write_bytes(b"")

    def verifier(paths: list[Path]) -> FlacVerifyResult:
        raise RuntimeError("kaboom")

    result = verify_rip_dir(tmp_path, verifier=verifier)
    assert not result.ran
    assert "unexpected error" in result.error
