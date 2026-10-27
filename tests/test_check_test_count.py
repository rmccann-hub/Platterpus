"""`scripts/check_test_count.py` and the count `tests/conftest.py` writes for it.

The 2026-10-27 external review, item 2.12: CI checked that the suite FINISHED
(the session sentinel) but not how much of it ran. These tests hold the three
parts of the fix: the pure comparison, the conftest writer that feeds it, and
the ratchet that keeps the committed baseline from drifting down.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest
from conftest import TEST_COUNT_FILE_ENV, write_collected_count

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]


def _load_gate():  # noqa: ANN202 — a module object
    """Import the script by path (scripts/ is deliberately not a package)."""
    path = REPO_ROOT / "scripts" / "check_test_count.py"
    spec = importlib.util.spec_from_file_location("_check_test_count", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate()

BASELINE: Final[Path] = REPO_ROOT / "tests" / "collected-tests-baseline.txt"


def test_below_the_baseline_fails() -> None:
    verdict = gate.judge(9000, 9327)
    assert not verdict.ok
    assert "327 fewer" in verdict.message, verdict.message


def test_equal_passes_without_asking_for_a_raise() -> None:
    verdict = gate.judge(9327, 9327)
    assert verdict.ok and verdict.raise_to is None


def test_above_passes_and_names_the_number_to_raise_to() -> None:
    """The ratchet's upward half: the run says what the new floor is."""
    verdict = gate.judge(9400, 9327)
    assert verdict.ok and verdict.raise_to == 9400
    assert "9400" in verdict.message


def test_a_missing_count_refuses() -> None:
    """Not determined is not a pass: a run that wrote no count is refused."""
    assert not gate.judge(None, 9327).ok


@pytest.mark.parametrize("baseline", [None, 0])
def test_a_missing_or_zero_baseline_refuses(baseline: int | None) -> None:
    """A floor of zero would be satisfied by a run that collected nothing."""
    assert not gate.judge(9327, baseline).ok
    assert not gate.judge(0, baseline).ok


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("9327\n", 9327),
        ("  42 ", 42),
        ("", None),
        ("9327 tests\n", None),
        ("1\n2\n", None),
        ("-5", None),
        ("٣", None),  # an Arabic-Indic digit: isdigit() says yes, int() would too
    ],
)
def test_parse_count_is_strict(text: str, expected: int | None) -> None:
    assert gate.parse_count(text) == expected


def test_main_reads_both_files_and_exits_by_the_verdict(tmp_path: Path) -> None:
    count = tmp_path / "count"
    baseline = tmp_path / "baseline"
    baseline.write_text("100\n", encoding="utf-8")
    count.write_text("99\n", encoding="utf-8")
    argv = ["--count-file", str(count), "--baseline-file", str(baseline)]
    assert gate.main(argv) == 1
    count.write_text("100\n", encoding="utf-8")
    assert gate.main(argv) == 0
    count.unlink()
    assert gate.main(argv) == 1, "a missing count file must refuse"


def test_the_committed_baseline_is_a_plausible_count() -> None:
    """One positive integer, and not a token value a broken run could meet.

    9,313 tests were collected on main at 27755380 (CI run 40425541839, py3.11
    and py3.12 alike), so a baseline far below that is no floor at all.
    """
    value = gate.parse_count(BASELINE.read_text(encoding="utf-8"))
    assert value is not None and value >= 9313, value
    assert BASELINE.read_text(encoding="utf-8").endswith("\n")


class _FakeSession:
    """The one attribute `write_collected_count` reads off a pytest session."""

    def __init__(self, collected: int) -> None:
        self.testscollected: int = collected


def test_the_conftest_writer_writes_only_when_asked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "count"
    monkeypatch.delenv(TEST_COUNT_FILE_ENV, raising=False)
    assert write_collected_count(_FakeSession(5)) is None  # type: ignore[arg-type]  # a stand-in carrying the one attribute read
    assert not target.exists(), "a local run must leave no count behind"

    monkeypatch.setenv(TEST_COUNT_FILE_ENV, str(target))
    assert write_collected_count(_FakeSession(5)) == target  # type: ignore[arg-type]  # as above
    assert gate.parse_count(target.read_text(encoding="utf-8")) == 5


def test_the_writer_and_the_script_name_one_variable() -> None:
    """Two spellings of one environment variable would write where nobody reads."""
    assert TEST_COUNT_FILE_ENV == gate.COUNT_FILE_ENV
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert ci.count(f"{TEST_COUNT_FILE_ENV}:") >= 2, (
        "ci.yml must set the variable on the test step AND on the check step"
    )
    assert "scripts/check_test_count.py" in ci


def _git(*args: str) -> str | None:
    """Run git in the repo root; None on any failure (no git, no tag, no file)."""
    try:
        result = subprocess.run(  # noqa: S603 — fixed argv, no shell
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except OSError:
        return None
    return result.stdout if result.returncode == 0 else None


def test_the_baseline_never_ratchets_down() -> None:
    """The baseline may only drop in a release cycle that says why.

    A committed number is not a ratchet by itself: whoever lowers it edits it in
    the same commit. The value at the newest release tag cannot be edited after
    the fact, so it is the comparison, as for the coverage floor
    (`tests/test_check_script.py::test_the_coverage_floor_never_ratchets_down`).
    Skips, visibly, when no tag is reachable or the tag predates the baseline.
    """
    tag = (_git("describe", "--tags", "--abbrev=0", "--match", "v*") or "").strip()
    if not tag:
        pytest.skip("no release tag reachable (shallow clone?) — cannot compare")
    previous_text = _git("show", f"{tag}:tests/collected-tests-baseline.txt")
    if previous_text is None:
        pytest.skip(f"{tag} predates the baseline file; the ratchet starts there")
    previous = gate.parse_count(previous_text)
    current = gate.parse_count(BASELINE.read_text(encoding="utf-8"))
    assert previous is not None and current is not None, (previous, current)
    assert current >= previous, (
        f"the collected-test baseline went DOWN: {previous} at {tag} -> {current} "
        "now. If tests were removed or merged on purpose, say why in the commit."
    )
