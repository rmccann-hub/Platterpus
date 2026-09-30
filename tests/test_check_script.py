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
import os
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


def test_the_gates_run_at_the_same_time(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every gate is started before any has to finish (2026-09-26).

    Each stand-in waits at a barrier sized to the number of gates. Run one after
    another, the first would wait alone until the barrier timed out; run together,
    all of them reach it. The report must still come out in the fixed gate order,
    with every gate's own exit code.
    """
    import threading

    fakes = [
        check.Gate(name, [sys.executable, "-c", "pass"])
        for name in ("lint (x)", "format (x)", "types (x)")
    ]
    barrier = threading.Barrier(len(fakes), timeout=10)

    def fake_run(gate: object) -> None:
        barrier.wait()
        gate.code = 0  # type: ignore[attr-defined]

    monkeypatch.setattr(check, "_build_gates", lambda only, coverage: fakes)
    monkeypatch.setattr(check, "_run", fake_run)
    assert check.main(["--log-dir", str(tmp_path)]) == 0
    printed = capsys.readouterr().out
    order = [printed.index(f"==> {gate.name}") for gate in fakes]
    assert order == sorted(order), "the report is not in the fixed gate order"
    assert all(gate.code == 0 for gate in fakes)


# --- The stale-clone preflight (2026-09-29 configuration re-check, A21) ---------
#
# A fresh cloud session starts shallow, with an origin/main hundreds of commits
# old. Ten tests that read origin/main then failed on laps that were fine, and
# their messages offered the exemption list as the remedy. The preflight says
# which it is before the suite runs. It warns and never changes a verdict.


def _state(**overrides: object) -> check.CloneState:
    """A CloneState that is fresh unless told otherwise."""
    fields: dict[str, object] = {
        "in_git": True,
        "shallow": False,
        "local_main": "a" * 40,
        "local_main_missing": False,
        "remote_main": "a" * 40,
        "remote_error": None,
    }
    fields.update(overrides)
    return check.CloneState(**fields)


def test_a_fresh_full_clone_gets_no_warning() -> None:
    assert check.clone_warnings(_state()) == []


def test_outside_git_there_is_nothing_to_say() -> None:
    """An unpacked sdist has no origin/main, and no reachability test can run."""
    assert (
        check.clone_warnings(_state(in_git=False, shallow=None, local_main=None)) == []
    )


def test_a_git_that_could_not_be_asked_is_said_not_taken_as_no_checkout() -> None:
    """Tri-state: "git did not answer" is not "there is no clone to check"."""
    [line] = check.clone_warnings(_state(in_git=None, shallow=None, local_main=None))
    assert "could not ask git" in line


def test_a_shallow_clone_is_named_with_its_fix() -> None:
    [line] = check.clone_warnings(_state(shallow=True))
    assert "shallow" in line and "git fetch --unshallow origin" in line


def test_an_origin_main_that_differs_from_the_remote_is_named_with_both() -> None:
    [line] = check.clone_warnings(_state(local_main="1" * 40, remote_main="2" * 40))
    assert "1" * 9 in line and "2" * 9 in line
    assert "git fetch origin main" in line


def test_no_origin_main_at_all_is_named() -> None:
    [line] = check.clone_warnings(_state(local_main=None, local_main_missing=True))
    assert "no origin/main" in line


def test_an_unreadable_origin_main_is_said_not_taken_as_missing() -> None:
    """Tri-state: a git that timed out has not said the ref is absent."""
    [line] = check.clone_warnings(_state(local_main=None, local_main_missing=False))
    assert "could not read this clone's origin/main" in line


def test_an_unreadable_remote_is_said_not_taken_as_fresh() -> None:
    """Tri-state: "could not compare" is never read as "up to date"."""
    [line] = check.clone_warnings(_state(remote_main=None, remote_error="exit 128"))
    assert "could not compare" in line and "exit 128" in line


def test_an_unknown_shallow_flag_is_said_not_taken_as_full() -> None:
    [line] = check.clone_warnings(_state(shallow=None))
    assert "could not tell" in line


def _repo_git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout.strip()


def _upstream_with_two_commits(tmp_path: Path) -> tuple[Path, str]:
    """A throwaway remote whose main has two commits; returns it and the first."""
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    _repo_git(upstream, "init", "-q", "-b", "main")
    _repo_git(upstream, "config", "user.email", "test@example.invalid")
    _repo_git(upstream, "config", "user.name", "test")
    for name in ("base", "tip"):
        (upstream / name).write_text(name, encoding="utf-8")
        _repo_git(upstream, "add", name)
        _repo_git(upstream, "commit", "-q", "-m", name)
    return upstream, _repo_git(upstream, "rev-parse", "HEAD~1")


def test_a_clone_whose_origin_main_is_held_back_is_caught(tmp_path: Path) -> None:
    """The real reader against a real clone: fresh first, then held back."""
    upstream, base = _upstream_with_two_commits(tmp_path)
    clone = tmp_path / "clone"
    _repo_git(tmp_path, "clone", "-q", str(upstream), str(clone))
    fresh = check.read_clone_state(clone, ask_remote=True)
    assert fresh.shallow is False and fresh.local_main == fresh.remote_main
    assert check.clone_warnings(fresh) == []

    _repo_git(clone, "update-ref", "refs/remotes/origin/main", base)
    held_back = check.read_clone_state(clone, ask_remote=True)
    [line] = check.clone_warnings(held_back)
    assert base[:9] in line and "git fetch origin main" in line


def test_a_clone_with_no_origin_main_is_told_apart_from_an_unreadable_one(
    tmp_path: Path,
) -> None:
    upstream, _ = _upstream_with_two_commits(tmp_path)
    clone = tmp_path / "clone"
    _repo_git(tmp_path, "clone", "-q", str(upstream), str(clone))
    _repo_git(clone, "update-ref", "-d", "refs/remotes/origin/main")
    state = check.read_clone_state(clone, ask_remote=False)
    assert state.local_main is None and state.local_main_missing is True


def test_a_shallow_clone_is_caught(tmp_path: Path) -> None:
    upstream, _ = _upstream_with_two_commits(tmp_path)
    clone = tmp_path / "shallow"
    _repo_git(tmp_path, "clone", "-q", "--depth", "1", f"file://{upstream}", str(clone))
    state = check.read_clone_state(clone, ask_remote=True)
    assert state.shallow is True
    assert any("--unshallow" in line for line in check.clone_warnings(state))


def test_a_remote_that_cannot_be_reached_is_reported(tmp_path: Path) -> None:
    upstream, _ = _upstream_with_two_commits(tmp_path)
    clone = tmp_path / "clone"
    _repo_git(tmp_path, "clone", "-q", str(upstream), str(clone))
    _repo_git(clone, "remote", "set-url", "origin", str(tmp_path / "gone"))
    state = check.read_clone_state(clone, ask_remote=True)
    assert state.remote_main is None and state.remote_error is not None
    assert any("could not compare" in line for line in check.clone_warnings(state))


def test_git_output_that_is_not_utf8_does_not_raise(tmp_path: Path) -> None:
    """Review finding B2 (2026-09-29): strict decoding raised UnicodeDecodeError.

    An origin whose path holds bytes that are not UTF-8 makes `git ls-remote`
    echo them in its error. The reader must still return, with the error said.
    """
    upstream, _ = _upstream_with_two_commits(tmp_path)
    clone = tmp_path / "clone"
    _repo_git(tmp_path, "clone", "-q", str(upstream), str(clone))
    odd = os.fsdecode(os.fsencode(str(tmp_path)) + b"/gone-\xff\xfe")
    _repo_git(clone, "remote", "set-url", "origin", odd)
    state = check.read_clone_state(clone, ask_remote=True)
    assert state.remote_main is None and state.remote_error is not None


def _proc_state(pid: int) -> str:
    """The process's state letter from ``/proc``, or ``"gone"`` once it has no entry.

    Both errors mean gone. ``FileNotFoundError`` is the entry already removed;
    ``ProcessLookupError`` (ESRCH) is the process reaped between the open and the
    read, which failed the py3.11 leg of PR #282's CI (2026-09-30) on exactly the
    outcome the test below waits for. A live process always reads.
    """
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except (FileNotFoundError, ProcessLookupError):
        return "gone"


def test_a_process_reaped_mid_read_counts_as_gone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The race, made deterministic: the read raises ESRCH, the answer is gone."""
    assert _proc_state(os.getpid()) in ("R", "S"), "the floor: a live process reads"

    def _reaped(self: Path, *args: object, **kwargs: object) -> str:
        raise ProcessLookupError(3, "No such process")

    monkeypatch.setattr(Path, "read_text", _reaped)
    assert _proc_state(os.getpid()) == "gone"


def test_a_git_that_hangs_is_cut_off_with_everything_it_started(
    tmp_path: Path,
) -> None:
    """Bounded, and the whole group goes: git here runs `sleep` as its child.

    Killing only the direct child would leave the sleep running, the case where
    git has started ssh. So the test reads the sleep's own pid and requires it
    gone (or a zombie, dead and awaiting its reaper). A bound on elapsed time
    alone would not catch this: an orphaned sleep only lengthens the wait.
    """
    import time

    pid_file = tmp_path / "nap.pid"
    started = time.monotonic()
    answer = check._git(
        tmp_path,
        "-c",
        f"alias.nap=!echo $$ > '{pid_file}'; exec sleep 30",
        "nap",
        timeout=1.0,
    )
    assert answer.code is None and "no answer" in answer.err
    assert time.monotonic() - started < 15, "the timeout did not bound the wait"
    pid = int(pid_file.read_text(encoding="utf-8").strip())
    deadline = time.monotonic() + 5
    state = "?"
    while time.monotonic() < deadline:
        state = _proc_state(pid)
        if state in ("gone", "Z", "X"):
            break
        time.sleep(0.1)
    assert state in ("gone", "Z", "X"), f"the sleep git started is still {state!r}"


def test_git_is_run_so_it_cannot_wait_on_a_person(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review finding: `git ls-remote` could prompt for credentials on the tty.

    No stdin, no terminal prompts, and its own session (no controlling terminal,
    so ssh cannot ask for a passphrase either).
    """
    seen: dict[str, object] = {}
    real_popen = subprocess.Popen

    def spy(*args: object, **kwargs: object) -> object:
        seen.update(kwargs)
        return real_popen(*args, **kwargs)  # type: ignore[call-overload]  # a pass-through spy

    # The environment this runs in may already say 0 (a cloud container does), and
    # then the check would pass without the code setting anything. Say 1 here.
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "1")
    monkeypatch.setattr(check.subprocess, "Popen", spy)
    check._git(tmp_path, "--version", timeout=10.0)
    assert seen["stdin"] is subprocess.DEVNULL
    assert seen["start_new_session"] is True
    env = seen["env"]
    assert isinstance(env, dict) and env["GIT_TERMINAL_PROMPT"] == "0"


def test_the_clone_state_is_read_before_any_gate_runs_and_changes_no_verdict(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Review finding: printing first is not running first.

    The `==>` headers are printed after every gate has finished, so output order
    alone would pass even if the read moved after the gates. The order of the
    calls is what is asserted here.
    """
    sentinel = tmp_path / ".pytest-session-complete"
    fake = check.Gate("tests (x)", [sys.executable, "-c", "pass"])
    order: list[str] = []

    def fake_read(repo: object, ask_remote: bool) -> check.CloneState:
        order.append("read clone")
        return _state(shallow=True)

    def fake_run(gate: object) -> None:
        order.append("run gate")
        gate.code = 0  # type: ignore[attr-defined]  # the fake stands in for a Gate
        sentinel.write_text("0", encoding="utf-8")

    monkeypatch.setattr(check, "SENTINEL", sentinel)
    monkeypatch.setattr(check, "_build_gates", lambda only, coverage: [fake])
    monkeypatch.setattr(check, "_run", fake_run)
    monkeypatch.setattr(check, "read_clone_state", fake_read)
    assert check.main(["--log-dir", str(tmp_path)]) == 0, "a warning is not a failure"
    assert order == ["read clone", "run gate"]
    printed = capsys.readouterr().out
    assert printed.index("! clone: this clone is shallow") < printed.index("==> tests")


def test_a_preflight_that_raises_does_not_stop_the_gates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Review finding B2: the preflight is a warning, so it may not end the run."""
    sentinel = tmp_path / ".pytest-session-complete"
    fake = check.Gate("tests (x)", [sys.executable, "-c", "pass"])

    def fake_run(gate: object) -> None:
        gate.code = 0  # type: ignore[attr-defined]  # the fake stands in for a Gate
        sentinel.write_text("0", encoding="utf-8")

    def broken(repo: object, ask_remote: bool) -> object:
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    monkeypatch.setattr(check, "SENTINEL", sentinel)
    monkeypatch.setattr(check, "_build_gates", lambda only, coverage: [fake])
    monkeypatch.setattr(check, "_run", fake_run)
    monkeypatch.setattr(check, "read_clone_state", broken)
    assert check.main(["--log-dir", str(tmp_path)]) == 0
    assert "could not read the clone's state" in capsys.readouterr().out


def test_no_clone_check_runs_when_the_suite_does_not(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Lint alone reads no origin/main, so it pays for no remote call."""
    fake = check.Gate("lint (x)", [sys.executable, "-c", "pass"])

    def refuse(repo: object, ask_remote: bool) -> object:
        raise AssertionError("read_clone_state ran for a run with no suite")

    monkeypatch.setattr(check, "_build_gates", lambda only, coverage: [fake])
    monkeypatch.setattr(check, "_run", lambda gate: setattr(gate, "code", 0))
    monkeypatch.setattr(check, "read_clone_state", refuse)
    assert check.main(["--log-dir", str(tmp_path)]) == 0
