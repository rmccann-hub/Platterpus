"""Tests for the post-rip FLAC encode-verify adapter + worker.

The `flac` subprocess is injected (a fake runner), so these run with no real
binary. The contract: never raise; distinguish "couldn't run" (error) from
"a file failed" (failures).
"""

from __future__ import annotations

import logging
import subprocess
import threading
from pathlib import Path

import pytest

from platterpus.adapters import flac_verify as fv
from platterpus.adapters.flac_verify import FlacVerifyResult, verify_flac_files
from platterpus.workers.flac_verify_worker import verify_rip_dir

# --- adapter: verify_flac_files -------------------------------------------


def test_default_runner_logs_stderr_tail_on_failure(
    monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    """Regression: the real runner must not swallow flac's stderr — a failed
    `flac --test` (corruption) has to be diagnosable from the log file."""

    class _Proc:
        returncode = 1
        stderr = "some warning\nERROR: got error while decoding\n"

    monkeypatch.setattr(fv.subprocess, "run", lambda *a, **k: _Proc())
    with caplog.at_level(logging.WARNING):
        rc = fv._default_runner(["flac", "--test", "x.flac"])

    assert rc == 1
    assert "flac --test failed (rc=1)" in caplog.text
    assert "got error while decoding" in caplog.text  # the stderr tail landed


def test_all_pass() -> None:
    seen: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        seen.append(argv)
        return 0

    paths = [Path("01.flac"), Path("02.flac")]
    result = verify_flac_files(paths, binary="flac", runner=runner)

    assert result.ok and result.ran
    assert result.checked == 2
    assert result.failures == ()
    # Each call is `flac --test --silent <path>`.
    assert seen[0] == ["flac", "--test", "--silent", "01.flac"]


def test_one_file_fails() -> None:
    def runner(argv: list[str]) -> int:
        return 1 if argv[-1].endswith("02.flac") else 0

    result = verify_flac_files([Path("01.flac"), Path("02.flac")], runner=runner)

    assert not result.ok and result.ran
    assert result.checked == 2
    assert result.failures == (Path("02.flac"),)


def test_missing_binary_is_an_error_not_a_failure() -> None:
    def runner(argv: list[str]) -> int:
        raise FileNotFoundError("flac")

    result = verify_flac_files([Path("01.flac")], runner=runner)

    assert not result.ran  # couldn't even run → error, not a "corrupt file"
    assert not result.ok
    assert result.failures == ()
    assert "not found" in result.error


def test_timeout_marks_the_file_failed() -> None:
    def runner(argv: list[str]) -> int:
        raise subprocess.TimeoutExpired(cmd="flac", timeout=120)

    result = verify_flac_files([Path("01.flac")], runner=runner)

    assert result.ran  # it ran, the file just didn't finish → a failure
    assert result.failures == (Path("01.flac"),)


def test_oserror_aborts_with_error() -> None:
    def runner(argv: list[str]) -> int:
        raise OSError("permission denied")

    result = verify_flac_files([Path("01.flac")], runner=runner)

    assert not result.ran
    assert "could not run" in result.error


def test_empty_input() -> None:
    result = verify_flac_files([], runner=lambda argv: 0)
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
