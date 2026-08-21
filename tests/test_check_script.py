"""Tests for `scripts/check.py` — the local gate runner whose answer must be trusted.

The script exists because reading a gate's status through a pipe reported the
*pipe's* status, four times across two sessions. Its whole value is therefore that
its verdict is correct, so these tests drive it to **FAIL** far more than to pass:
a runner that cannot report a failure is worse than no runner, because its green
gets quoted.

The load-bearing test here is `test_the_local_coverage_floor_matches_ci`. Two
places state one number, and this repo has already been bitten by exactly that —
the release workflow's pre-release tag-shape list and the handshake gate's list
had to be identical, diverged invisibly for the whole v0.x line, and would have
opened at v1.0.0. A local gate that is *easier* than CI's teaches the wrong thing
while looking green.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]


def _load_check():  # noqa: ANN202 — a module object
    """Import `scripts/check.py` by path (scripts/ is deliberately not a package)."""
    path = REPO_ROOT / "scripts" / "check.py"
    spec = importlib.util.spec_from_file_location("_check_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


check = _load_check()


def test_a_nonzero_gate_is_not_a_pass() -> None:
    gate = check.Gate("demo", ["true"], code=1)
    assert gate.passed is False


def test_a_zero_gate_with_no_objection_is_a_pass() -> None:
    gate = check.Gate("demo", ["true"], code=0)
    assert gate.passed is True


def test_no_result_is_not_a_pass() -> None:
    """`code is None` means the gate never produced a verdict.

    Tri-state, the same rule the ripper-approval and handshake gates follow: "not
    determined" is not agreement. A timeout or a child that could not start must
    not read as success just because no failure was recorded.
    """
    gate = check.Gate("demo", ["true"], code=None)
    assert gate.passed is False


def test_a_zero_exit_with_an_objection_is_not_a_pass() -> None:
    """The sentinel check adds a note to an otherwise-green run; it must bite.

    This is the truncated-run case: pytest exits 0 having vanished mid-run, which
    once marked a CI job green at 76%. An exit code alone cannot see it.
    """
    gate = check.Gate("tests (pytest)", ["true"], code=0)
    gate.notes.append("the pytest session never reached session-finish")
    assert gate.passed is False


def test_an_elided_excerpt_keeps_the_head_and_the_tail_and_says_so() -> None:
    """A tool's fatal message is the LAST thing it prints.

    A head-only cap drops precisely the line that explains the failure, and a
    silent truncation reads as completeness — both named rules here. So the
    excerpt must retain both ends and mark the gap with a count.
    """
    body = "HEAD-MARKER" + ("x" * 20_000) + "TAIL-MARKER"
    out = check._excerpt(body)
    assert "HEAD-MARKER" in out, "the head was dropped"
    assert "TAIL-MARKER" in out, "the tail was dropped — the fatal line lives there"
    assert "elided" in out, "the elision was silent"
    assert re.search(r"\d+ characters elided", out), "the elision was not counted"


def test_a_short_output_is_not_elided_at_all() -> None:
    """The floor on the previous test: it must not pass by eliding everything."""
    out = check._excerpt("brief")
    assert out == "brief"


def test_the_local_coverage_floor_matches_ci() -> None:
    """One number, two places — so they are compared rather than trusted.

    `scripts/check.py` applies a floor locally so a local run is not politer than
    CI. That only holds while the numbers agree, and nothing but this test makes
    them agree. Read out of the workflow text rather than hard-coded here, so
    raising the ratchet in CI cannot leave the local runner behind.
    """
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    found = {int(m) for m in re.findall(r"--cov-fail-under=(\d+)", workflow)}
    assert found, (
        "no --cov-fail-under found in ci.yml — either the gate was removed (a "
        "release-blocking change) or this test is now looking in the wrong place. "
        "Either way it must not silently pass."
    )
    assert found == {check.COVERAGE_FLOOR}, (
        f"ci.yml enforces {sorted(found)} but scripts/check.py uses "
        f"{check.COVERAGE_FLOOR}. A local gate that is easier than CI's is worse "
        "than none: it reports green for work CI will reject."
    )


def _git(*args: str) -> str | None:
    """Run git in the repo root; None on any failure (missing git, no repo, no tag)."""
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
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _floor_in(text: str) -> int | None:
    """The `--cov-fail-under` value in a workflow's text, or None if absent."""
    found = {int(m) for m in re.findall(r"--cov-fail-under=(\d+)", text)}
    if len(found) != 1:
        return None
    return found.pop()


def test_the_coverage_floor_never_ratchets_down() -> None:
    """`ci.yml` says the gate "ratchets up, never down". Nothing enforced that.

    A committed high-water constant would not be a ratchet: whoever lowers the
    floor edits it in the same commit, and the check passes. The only value that
    cannot be edited retroactively is the one in the **last release tag**, so that
    is what this compares against.

    Honest about the limit: once a release is cut carrying a lowered floor, the
    ratchet re-bases on it. That is acceptable — cutting a release is a deliberate
    act with its own gates — but it means this guards the *cycle*, not all history.
    Saying so beats implying more.

    Skips rather than passes when there is no reachable tag (a shallow clone), on
    the tri-state rule: no result is not agreement. A skip is visible in the run;
    a silent pass is not.
    """
    tag = _git("describe", "--tags", "--abbrev=0", "--match", "v*")
    if not tag:
        pytest.skip("no release tag reachable (shallow clone?) — cannot compare")

    previous_text = _git("show", f"{tag}:.github/workflows/ci.yml")
    if previous_text is None:
        pytest.skip(f"cannot read ci.yml at {tag} — cannot compare")

    previous = _floor_in(previous_text)
    current = _floor_in(
        (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )
    assert current is not None, (
        "no single --cov-fail-under found in the current ci.yml. Either the gate "
        "was removed — a release-blocking change — or there are now several and "
        "this check needs to say which one is authoritative."
    )
    assert previous is not None, (
        f"no single --cov-fail-under found in ci.yml at {tag}, so there is nothing "
        "to ratchet against. If the gate was introduced after that tag, this test "
        "starts working at the next release."
    )
    assert current >= previous, (
        f"the coverage floor went DOWN: {previous} at {tag} → {current} now. "
        "`ci.yml`'s own comment says the gate ratchets up and is never lowered to "
        "make a red build pass. If the drop is deliberate, say why in the commit "
        "message and expect this test to be the thing that made you say it."
    )


def test_an_unknown_gate_name_is_refused_rather_than_ignored() -> None:
    """A typo must not silently run nothing and report success.

    `--only tets` skipping every gate and printing "0/0 gates passed" would be
    the canonical satisfied-by-finding-nothing failure.
    """
    with pytest.raises(SystemExit, match="unknown gate"):
        check._build_gates({"tets"}, coverage=False)


def test_no_selection_runs_every_gate() -> None:
    """The default must be the whole set, not an empty one."""
    gates = check._build_gates(set(), coverage=True)
    assert len(gates) == 4, [g.name for g in gates]


def test_the_coverage_floor_is_only_applied_when_coverage_is_on() -> None:
    """`--no-coverage` must not silently keep enforcing a floor it cannot measure."""
    with_cov = check._build_gates({"tests"}, coverage=True)[0]
    without = check._build_gates({"tests"}, coverage=False)[0]
    assert any("--cov-fail-under" in arg for arg in with_cov.argv)
    assert not any("--cov-fail-under" in arg for arg in without.argv)
    assert not any("--cov" in arg for arg in without.argv), (
        "--no-coverage still requested coverage, so the run pays for "
        "instrumentation it then does not check"
    )


def test_every_gate_runs_without_a_shell() -> None:
    """No gate may be a shell string — that is where a pipeline could hide.

    The defect this script exists to remove is a status read from a pipeline's
    last stage. An argv list cannot contain a pipe; a shell string can. So the
    property is asserted rather than merely intended.
    """
    for gate in check._build_gates(set(), coverage=True):
        assert isinstance(gate.argv, list), f"{gate.name} is not an argv list"
        joined = " ".join(gate.argv)
        for shell_metachar in ("|", ";", "&&", ">", "<"):
            assert shell_metachar not in joined, (
                f"{gate.name} argv contains {shell_metachar!r}: {gate.argv!r}. "
                "If this ever needs a pipeline, the status must come from the "
                "first stage, not the last."
            )
