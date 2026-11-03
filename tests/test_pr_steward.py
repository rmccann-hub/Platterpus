"""`scripts/pr_steward.py`: the verdict on a commit's checks, decided by rule.

Each case is one of the three ways hand-written waits went wrong on 2026-11-02,
or a guard around them (`.claude/skills/pr-steward/SKILL.md`). The classifier
and the log reader are pure, so these run without the network; the fetching
half is exercised through `main` with the fetchers replaced.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / ".claude" / "skills" / "pr-steward" / "SKILL.md"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "pr_steward", REPO / "scripts" / "pr_steward.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pr_steward"] = module
    spec.loader.exec_module(module)
    return module


steward = _load()
Run = steward.CheckRun


def _run(
    name: str, conclusion: str = "success", status: str = "completed", rid: int = 1
) -> object:
    return Run(name=name, status=status, conclusion=conclusion, run_id=rid)


REQUIRED = ["lint", "test (py3.12)", "ui-conformance"]


def _all_green() -> list[object]:
    return [_run(n, rid=i) for i, n in enumerate(REQUIRED, 1)]


def test_every_required_check_passing_is_green() -> None:
    report = steward.classify(REQUIRED, _all_green(), workflows_finished=True)
    assert report.verdict == steward.GREEN
    assert sorted(report.passed) == sorted(REQUIRED)


def test_a_cancelled_run_is_not_a_failure() -> None:
    """The first trap: a run superseded by a newer push reads `cancelled`."""
    runs = _all_green()[:2] + [_run("ui-conformance", "cancelled", rid=3)]
    report = steward.classify(REQUIRED, runs, workflows_finished=True)
    assert report.verdict == steward.CANCELLED
    assert not report.failed


def test_a_re_run_supersedes_the_run_before_it() -> None:
    runs = _all_green() + [_run("lint", "failure", rid=0)]  # an OLDER failure
    assert steward.classify(REQUIRED, runs, True).verdict == steward.GREEN
    runs = _all_green() + [_run("lint", "failure", rid=99)]  # a NEWER failure
    assert steward.classify(REQUIRED, runs, True).verdict == steward.FAILED


def test_a_required_check_no_workflow_will_report_is_blocked() -> None:
    """The third trap: `test (py3.11)` after the leg left the matrix."""
    required = REQUIRED + ["test (py3.11)"]
    report = steward.classify(required, _all_green(), workflows_finished=True)
    assert report.verdict == steward.BLOCKED
    assert report.never_reported == ("test (py3.11)",)


def test_an_unreported_check_is_only_pending_while_workflows_run() -> None:
    required = REQUIRED + ["test (py3.11)"]
    report = steward.classify(required, _all_green(), workflows_finished=False)
    assert report.verdict == steward.PENDING
    assert report.pending == ("test (py3.11)",)


def test_the_required_list_is_read_not_counted() -> None:
    """The second trap: a fixed count of checks to wait for. Adding a required
    job the commit has not run makes the verdict PENDING, whatever the count."""
    required = REQUIRED + ["lock-check"]
    report = steward.classify(required, _all_green(), workflows_finished=False)
    assert report.verdict == steward.PENDING
    assert "lock-check" in report.pending


def test_a_failing_check_nobody_requires_still_fails_main() -> None:
    """appimage.yml's `build` is not required, and it was main's red on 2026-11-02."""
    runs = _all_green() + [_run("build", "failure", rid=7)]
    report = steward.classify(REQUIRED, runs, workflows_finished=True)
    assert report.verdict == steward.FAILED
    assert [r.name for r in report.failed] == ["build"]


def test_a_failure_is_never_hidden_behind_something_pending() -> None:
    runs = [_run("lint", "failure", rid=1), _run("test (py3.12)", "", "in_progress", 2)]
    report = steward.classify(REQUIRED, runs, workflows_finished=False)
    assert report.verdict == steward.FAILED


def test_severity_order_and_exit_codes_agree() -> None:
    assert (
        steward.SEVERITY[0] == steward.FAILED and steward.SEVERITY[-1] == steward.GREEN
    )
    assert set(steward.SEVERITY) == set(steward.EXIT_CODES)
    assert steward.EXIT_CODES[steward.GREEN] == 0
    codes = list(steward.EXIT_CODES.values()) + [steward.EXIT_UNREAD]
    assert len(set(codes)) == len(codes), "two outcomes share an exit code"


def test_failure_lines_names_every_failure_not_the_last() -> None:
    """`tail -1` hid two failing tests on 2026-11-02; every one is kept."""
    log = "\n".join(
        [
            "2026-11-02T23:58:01.1Z ............ [ 90%]",
            "2026-11-02T23:58:02.2Z FAILED tests/a.py::one - AssertionError",
            "2026-11-02T23:58:02.3Z E       assert 1 == 2",
            "2026-11-02T23:58:02.4Z FAILED tests/b.py::two - AssertionError",
            "2026-11-02T23:58:02.5Z FAILED tests/c.py::three - KeyError",
            "2026-11-02T23:58:02.6Z 3 failed, 9500 passed, 20 skipped in 301.10s",
            "2026-11-02T23:58:02.7Z ##[error]Process completed with exit code 1.",
        ]
    )
    lines = steward.failure_lines(log)
    assert [line for line in lines if line.startswith("FAILED")] == [
        "FAILED tests/a.py::one - AssertionError",
        "FAILED tests/b.py::two - AssertionError",
        "FAILED tests/c.py::three - KeyError",
    ]
    assert "3 failed, 9500 passed, 20 skipped in 301.10s" in lines
    assert "##[error]Process completed with exit code 1." in lines
    assert "E       assert 1 == 2" in lines
    assert not any("[ 90%]" in line for line in lines)


@settings(max_examples=200, deadline=None)
@given(st.text())
def test_failure_lines_never_raises(log: str) -> None:
    """A job log is external output: the reader takes anything."""
    assert isinstance(steward.failure_lines(log), list)


def test_main_gives_no_verdict_when_the_api_cannot_be_read(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def broken(*_args: object) -> object:
        raise steward.ApiError("network down")

    monkeypatch.setattr(steward, "full_sha", broken)
    assert steward.main(["--sha", "abc"]) == steward.EXIT_UNREAD
    assert "no verdict" in capsys.readouterr().err


def test_main_returns_the_verdicts_exit_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    sha = "a" * 40
    monkeypatch.setattr(steward, "full_sha", lambda repo, ref: sha)
    monkeypatch.setattr(
        steward, "required_checks", lambda repo, branch: REQUIRED + ["test (py3.11)"]
    )
    monkeypatch.setattr(steward, "check_runs", lambda repo, s: _all_green())
    monkeypatch.setattr(steward, "workflows_finished", lambda repo, s: True)
    assert steward.main(["--sha", "abc"]) == steward.EXIT_CODES[steward.BLOCKED]
    out = capsys.readouterr().out
    assert out.startswith("BLOCKED") and "test (py3.11)" in out and "owner" in out


def test_only_the_api_host_is_ever_opened() -> None:
    with pytest.raises(steward.ApiError, match="refusing"):
        steward._get("file:///etc/passwd")


def test_the_skill_states_what_the_script_decides() -> None:
    """The skill and the script describe one tool; a verdict or exit code the
    script has and the skill does not name is a drift, caught here."""
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\nname: pr-steward\n"), "frontmatter first, named"
    assert "scripts/pr_steward.py" in text
    for verdict, code in steward.EXIT_CODES.items():
        assert f"`{verdict}`" in text and f"| {code} |" in text, (verdict, code)
    assert f"| {steward.EXIT_UNREAD} |" in text
    assert "DRAFT" in text
