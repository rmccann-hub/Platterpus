"""The sleep inhibitor: tri-state honesty, a probe that cannot drift, a bounded release.

**The test this file exists for is the first one.** The shell version of this lock
(`docs/rig-scripts/platterpusovernight.sh`) shipped a probe that asked for
`--what=idle` while the real lock asked for `--what=idle:sleep:handle-lid-switch`,
so it tested a *weaker* capability than the one that mattered: on a machine whose
session could inhibit `idle` and not `sleep`, the probe passed, the lock failed,
and the whole run was consumed by the inhibitor with the real work never executed.
CI caught it within the hour.

So the regression test reads the ``--what`` entry out of **both recorded argvs**
and requires them to be byte-identical. Reading the module constant twice would
prove nothing — the constant was never the thing that drifted; the *call sites*
were. A second test hands in a non-default ``what`` so that a hard-coded literal
in either builder fails, and a third parses the module and requires the value to
appear exactly once outside the prose.

Nothing here spawns a process, opens a socket or sleeps. Every OS interaction goes
through the injected :class:`~platterpus.sleep_inhibit.InhibitRunner`, including
the group kill — a fake pid handed to a real ``os.killpg`` would be a live grenade
in a test suite.
"""

from __future__ import annotations

import ast
import logging
import math
import subprocess
from pathlib import Path

import pytest

from platterpus import sleep_inhibit
from platterpus.sleep_inhibit import (
    INHIBIT_BINARY,
    INHIBIT_STATES,
    INHIBIT_WHAT,
    LOCK_HOLD_SECONDS,
    OUTPUT_HEAD_CHARS,
    OUTPUT_TAIL_CHARS,
    PROBE_TIMEOUT_S,
    STATE_HELD,
    STATE_NOT_INSTALLED,
    STATE_UNAVAILABLE,
    InhibitOutcome,
    ProbeResult,
    SleepInhibitor,
    SubprocessInhibitRunner,
)

# --------------------------------------------------------------------------
# Doubles
# --------------------------------------------------------------------------


class FakeProcess:
    """Exactly the part of ``subprocess.Popen`` the release path touches.

    ``dies_on_terminate`` / ``dies_on_kill`` are how the two escalation paths are
    reached: a child that ignores SIGTERM, and a child that ignores SIGKILL too
    (the unreapable case — a reader wedged in an uninterruptible drive ioctl).
    """

    def __init__(
        self,
        *,
        pid: int = 4242,
        alive: bool = True,
        returncode: int = 0,
        dies_on_terminate: bool = True,
        dies_on_kill: bool = True,
    ) -> None:
        self._pid: int = pid
        self._alive: bool = alive
        self._returncode: int = returncode
        self._dies_on_terminate: bool = dies_on_terminate
        self._dies_on_kill: bool = dies_on_kill
        self.terminate_calls: int = 0
        self.kill_calls: int = 0
        self.poll_calls: int = 0
        self.wait_timeouts: list[float | None] = []

    @property
    def pid(self) -> int:
        return self._pid

    def die(self) -> None:
        """Make the child look exited, without any signal having been sent."""
        self._alive = False

    def poll(self) -> int | None:
        self.poll_calls += 1
        return None if self._alive else self._returncode

    def terminate(self) -> None:
        self.terminate_calls += 1
        if self._dies_on_terminate:
            self._alive = False

    def kill(self) -> None:
        self.kill_calls += 1
        if self._dies_on_kill:
            self._alive = False

    def wait(self, timeout: float | None = None) -> int:
        self.wait_timeouts.append(timeout)
        if self._alive:
            raise subprocess.TimeoutExpired(cmd=INHIBIT_BINARY, timeout=timeout or 0.0)
        return self._returncode


class FakeRunner:
    """Records every argv and flag that crosses the seam."""

    def __init__(
        self,
        *,
        probe_result: ProbeResult | None = None,
        probe_error: BaseException | None = None,
        spawn_error: BaseException | None = None,
        process: FakeProcess | None = None,
    ) -> None:
        self._probe_result: ProbeResult = probe_result or ProbeResult(0, "")
        self._probe_error: BaseException | None = probe_error
        self._spawn_error: BaseException | None = spawn_error
        self.process: FakeProcess = process or FakeProcess()
        self.probe_argvs: list[list[str]] = []
        self.probe_timeouts: list[float] = []
        self.spawn_argvs: list[list[str]] = []
        self.spawn_sessions: list[bool] = []
        self.kill_group_calls: list[object] = []
        #: Hook fired inside ``spawn``, used to reproduce a release that lands
        #: between the sequence number being taken and the child being registered.
        self.on_spawn: object = None

    def probe(self, argv: list[str], *, timeout: float) -> ProbeResult:
        self.probe_argvs.append(list(argv))
        self.probe_timeouts.append(timeout)
        if self._probe_error is not None:
            raise self._probe_error
        return self._probe_result

    def spawn(self, argv: list[str], *, start_new_session: bool) -> FakeProcess:
        self.spawn_argvs.append(list(argv))
        self.spawn_sessions.append(start_new_session)
        if self._spawn_error is not None:
            raise self._spawn_error
        if callable(self.on_spawn):
            self.on_spawn()
        return self.process

    def kill_group(self, process: object) -> None:
        self.kill_group_calls.append(process)
        # A group SIGKILL reaches this child too; whether it *dies* is the fake
        # process's business, which is how the unreapable case is expressed.
        if isinstance(process, FakeProcess):
            process.kill()


def _what_args(argv: list[str]) -> list[str]:
    return [arg for arg in argv if arg.startswith("--what=")]


def _is_finite_positive(timeout: float | None) -> bool:
    return timeout is not None and math.isfinite(timeout) and timeout > 0


# --------------------------------------------------------------------------
# Parametrize populations
#
# Written out as literal lists of names, with the exception objects looked up in
# `_ERRORS` inside the test body. That indirection is deliberate:
# `tests/test_dynamic_sweeps_declare_a_floor.py` classifies any `argvalues`
# containing a *call* as a discovered population — one that can shrink to nothing
# with no diff, generating zero cases while pytest still exits 0. A written-out
# list cannot empty itself without an edit somebody reviews. The floor tests below
# then pin the two halves together, so a name that loses its error is a failure
# rather than a silently skipped case.
# --------------------------------------------------------------------------

#: Every failure shape the OS or `subprocess` can hand us, by name.
_ERRORS: dict[str, BaseException] = {
    "oserror": OSError("boom"),
    "permission-denied": PermissionError("denied"),
    "missing-binary": FileNotFoundError(2, "No such file or directory"),
    "would-block": BlockingIOError("would block"),
    "subprocess-error": subprocess.SubprocessError("something went wrong"),
    "timeout": subprocess.TimeoutExpired(cmd="systemd-inhibit", timeout=1.0),
}

_PROBE_ERROR_NAMES: list[str] = [
    "oserror",
    "permission-denied",
    "missing-binary",
    "would-block",
    "subprocess-error",
    "timeout",
]

#: The spawn cases exclude `missing-binary`, which has its own test: it is the one
#: error that must NOT be reported as `unavailable`.
_SPAWN_ERROR_NAMES: list[str] = [
    "oserror",
    "permission-denied",
    "would-block",
    "subprocess-error",
]

#: `(expected state, probe exit code, probe output)`.
_OUTCOME_CASES: list[tuple[str, int, str]] = [
    (STATE_UNAVAILABLE, 1, "Failed to inhibit: Access denied"),
    (STATE_HELD, 0, ""),
]


def test_the_parametrize_populations_are_floored() -> None:
    """Neither list may empty itself, and every name must resolve to an error.

    Without this, dropping an entry from `_ERRORS` would turn its case into a
    `KeyError`… but dropping an entry from a *names* list would silently examine
    one shape fewer, which is the failure the suite's dynamic-sweep rule is about.
    """
    assert len(_PROBE_ERROR_NAMES) >= 5
    assert len(_SPAWN_ERROR_NAMES) >= 3
    assert len(_OUTCOME_CASES) >= 2
    assert set(_PROBE_ERROR_NAMES) == set(_ERRORS), (
        "every known error shape must be exercised against the probe"
    )
    assert set(_SPAWN_ERROR_NAMES) <= set(_ERRORS)
    assert {state for state, _, _ in _OUTCOME_CASES} == {STATE_HELD, STATE_UNAVAILABLE}


# --------------------------------------------------------------------------
# THE REGRESSION TEST: the probe must ask for exactly what the run asks for
# --------------------------------------------------------------------------


def test_the_probe_asks_for_byte_identical_what_to_the_real_lock() -> None:
    """The 2026-08 CI failure, pinned.

    Read from the **recorded argvs of both calls** — not from the constant, which
    was never what drifted. If a future edit spells the probe's capability set
    anywhere but :func:`SleepInhibitor._what_arg`, this fails.
    """
    runner = FakeRunner()
    SleepInhibitor(runner=runner).acquire()

    assert len(runner.probe_argvs) == 1, "the probe must run exactly once"
    assert len(runner.spawn_argvs) == 1, "the lock must be taken exactly once"

    probe_what = _what_args(runner.probe_argvs[0])
    lock_what = _what_args(runner.spawn_argvs[0])
    # Floor: a check that can be satisfied by finding nothing is decoration.
    assert len(probe_what) == 1, f"no --what in the probe argv: {runner.probe_argvs[0]}"
    assert len(lock_what) == 1, f"no --what in the lock argv: {runner.spawn_argvs[0]}"

    assert probe_what[0] == lock_what[0]
    assert probe_what[0] == f"--what={INHIBIT_WHAT}"


def test_a_non_default_what_reaches_both_argvs() -> None:
    """Kills a hard-coded literal in *either* builder.

    The previous test would still pass if both builders hard-coded the same
    default. This one cannot: the value only reaches the argv if both sites read
    the instance's ``what``.
    """
    runner = FakeRunner()
    SleepInhibitor(runner=runner, what="idle:sleep").acquire()

    assert _what_args(runner.probe_argvs[0]) == ["--what=idle:sleep"]
    assert _what_args(runner.spawn_argvs[0]) == ["--what=idle:sleep"]


def test_the_capability_set_is_spelled_exactly_once_in_code() -> None:
    """One definition, enforced against the source rather than asked for in prose.

    Docstrings are excluded — the module docstring quotes the value while
    explaining why it may only be spelled once, and a format's own documentation
    is the likeliest place to trip its own checker.
    """
    source = Path(sleep_inhibit.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    docstring_ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                docstring_ids.add(id(first.value))

    literals = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value == INHIBIT_WHAT
        and id(node) not in docstring_ids
    ]
    assert len(literals) == 1, (
        f"{INHIBIT_WHAT!r} appears {len(literals)} time(s) in code. It must be "
        "defined once (INHIBIT_WHAT) and reached through _what_arg(), so the probe "
        "cannot drift from the lock."
    )


def test_the_outcome_records_the_capability_that_was_actually_asked_for() -> None:
    """A report must be able to *prove* the probe matched the run, not assert it."""
    runner = FakeRunner()
    outcome = SleepInhibitor(runner=runner, what="idle:sleep").acquire()
    assert outcome.what == "idle:sleep"
    assert f"--what={outcome.what}" in runner.probe_argvs[0]
    assert f"--what={outcome.what}" in runner.spawn_argvs[0]


# --------------------------------------------------------------------------
# Present is not the same as working: the three failure shapes
# --------------------------------------------------------------------------


def test_no_session_bus_is_unavailable_and_spawns_no_lock_child() -> None:
    """`systemd-inhibit` is installed and cannot work. Adopting it would consume
    the whole run with the real work never executed."""
    stderr = "Failed to connect to bus: No such file or directory"
    runner = FakeRunner(probe_result=ProbeResult(1, stderr))
    inhibitor = SleepInhibitor(runner=runner)

    outcome = inhibitor.acquire()

    assert outcome.state == STATE_UNAVAILABLE
    assert stderr in outcome.detail, "the tool's own words must reach the user"
    assert runner.spawn_argvs == [], "no lock child may be spawned after a failed probe"
    assert inhibitor.held is False


def test_access_denied_is_unavailable_and_spawns_no_lock_child() -> None:
    """The awkward middle case: a session bus exists, polkit refuses sleep/lid.

    This is what a GitHub runner looks like, and it is the case a weaker probe
    (`--what=idle` alone) passes.
    """
    runner = FakeRunner(probe_result=ProbeResult(1, "Failed to inhibit: Access denied"))
    inhibitor = SleepInhibitor(runner=runner)

    outcome = inhibitor.acquire()

    assert outcome.state == STATE_UNAVAILABLE
    assert "Access denied" in outcome.detail
    assert runner.spawn_argvs == []
    assert inhibitor.held is False


def test_a_missing_binary_is_not_installed_not_unavailable() -> None:
    """Tri-state, never a bool: the two failures need different advice."""
    runner = FakeRunner(probe_error=FileNotFoundError(2, "No such file or directory"))
    inhibitor = SleepInhibitor(runner=runner)

    outcome = inhibitor.acquire()

    assert outcome.state == STATE_NOT_INSTALLED
    assert INHIBIT_BINARY in outcome.detail
    assert runner.spawn_argvs == []
    assert inhibitor.held is False


def test_the_binary_vanishing_between_probe_and_lock_is_not_installed() -> None:
    runner = FakeRunner(spawn_error=FileNotFoundError(2, "No such file or directory"))
    inhibitor = SleepInhibitor(runner=runner)

    outcome = inhibitor.acquire()

    assert outcome.state == STATE_NOT_INSTALLED
    assert inhibitor.held is False


def test_a_probe_timeout_is_a_refusal_never_a_pass() -> None:
    """A hung D-Bus is not a working lock, and must not be reported as one."""
    runner = FakeRunner(
        probe_error=subprocess.TimeoutExpired(cmd=INHIBIT_BINARY, timeout=10.0)
    )
    outcome = SleepInhibitor(runner=runner).acquire()

    assert outcome.state == STATE_UNAVAILABLE
    assert runner.spawn_argvs == []


def test_the_probe_is_bounded_by_a_finite_positive_timeout() -> None:
    runner = FakeRunner()
    SleepInhibitor(runner=runner).acquire()
    assert runner.probe_timeouts == [PROBE_TIMEOUT_S]
    assert _is_finite_positive(runner.probe_timeouts[0])


@pytest.mark.parametrize("state, returncode, output", _OUTCOME_CASES)
def test_every_outcome_is_tri_state_with_a_non_empty_detail(
    state: str, returncode: int, output: str
) -> None:
    probe = ProbeResult(returncode, output)
    outcome = SleepInhibitor(runner=FakeRunner(probe_result=probe)).acquire()
    assert outcome.state == state
    assert outcome.state in INHIBIT_STATES
    assert outcome.detail.strip(), "a silent downgrade is the failure mode"
    assert outcome.is_held is (state == STATE_HELD)


def test_an_outcome_cannot_be_built_without_a_reason() -> None:
    """The tripwire on the dataclass: a blank explanation is not an outcome."""
    with pytest.raises(ValueError):
        InhibitOutcome(state=STATE_UNAVAILABLE, detail="   ", what=INHIBIT_WHAT)
    with pytest.raises(ValueError):
        InhibitOutcome(state="probably", detail="something", what=INHIBIT_WHAT)


# --------------------------------------------------------------------------
# The happy path
# --------------------------------------------------------------------------


def test_the_happy_path_holds_exactly_one_child_in_a_new_session() -> None:
    runner = FakeRunner()
    inhibitor = SleepInhibitor(runner=runner)

    outcome = inhibitor.acquire()

    assert outcome.state == STATE_HELD
    assert len(runner.spawn_argvs) == 1
    assert runner.spawn_sessions == [True], (
        "start_new_session is load-bearing: without it a killpg on release would "
        "signal our own process group"
    )
    argv = runner.spawn_argvs[0]
    assert argv[0] == INHIBIT_BINARY
    assert "--mode=block" in argv
    assert argv[-2:] == ["sleep", str(LOCK_HOLD_SECONDS)]
    assert inhibitor.held is True


def test_the_lock_horizon_is_finite() -> None:
    """A leaked `sleep infinity` would hold the machine awake until reboot with
    nothing left to explain why."""
    assert 0 < LOCK_HOLD_SECONDS < math.inf
    assert LOCK_HOLD_SECONDS >= 12 * 60 * 60, "must comfortably outlast a night"


def test_acquiring_twice_while_held_does_not_spawn_a_second_child() -> None:
    runner = FakeRunner()
    inhibitor = SleepInhibitor(runner=runner)

    first = inhibitor.acquire()
    second = inhibitor.acquire()

    assert first == second
    assert len(runner.spawn_argvs) == 1
    assert len(runner.probe_argvs) == 1


def test_held_reflects_the_child_not_our_bookkeeping() -> None:
    """A stored flag would keep claiming the machine is protected after the lock
    child died — the silent downgrade arriving by the one route the outcome
    cannot see."""
    process = FakeProcess()
    inhibitor = SleepInhibitor(runner=FakeRunner(process=process))
    assert inhibitor.acquire().state == STATE_HELD
    assert inhibitor.held is True

    process.die()  # the child exits on its own; nobody told us

    assert inhibitor.held is False


# --------------------------------------------------------------------------
# Release: terminate, escalate, bound, and say so
# --------------------------------------------------------------------------


def test_release_terminates_the_child() -> None:
    process = FakeProcess(dies_on_terminate=True)
    runner = FakeRunner(process=process)
    inhibitor = SleepInhibitor(runner=runner)
    inhibitor.acquire()

    inhibitor.release()

    assert process.terminate_calls == 1
    assert runner.kill_group_calls == [], "no escalation was needed"
    assert inhibitor.held is False


def test_release_escalates_to_a_group_kill_with_a_bounded_wait() -> None:
    process = FakeProcess(dies_on_terminate=False, dies_on_kill=True)
    runner = FakeRunner(process=process)
    inhibitor = SleepInhibitor(runner=runner)
    inhibitor.acquire()

    inhibitor.release()

    assert process.terminate_calls == 1
    assert runner.kill_group_calls == [process], (
        "a SIGTERM the child ignores must escalate to a GROUP kill — signalling "
        "only the direct child leaves the inhibitor held"
    )
    assert process.wait_timeouts, "the release must actually wait for the child"
    assert all(_is_finite_positive(t) for t in process.wait_timeouts), (
        f"every wait must be bounded; got {process.wait_timeouts!r} "
        "(None means wait forever, which freezes a teardown)"
    )
    assert inhibitor.held is False


def test_an_unreapable_child_is_reported_rather_than_waited_on_forever(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """SIGKILL does not land on a process in uninterruptible sleep. Say so and
    return — a shutdown that blocks forever is worse than a leaked child."""
    process = FakeProcess(dies_on_terminate=False, dies_on_kill=False)
    runner = FakeRunner(process=process)
    inhibitor = SleepInhibitor(runner=runner)
    inhibitor.acquire()

    with caplog.at_level(logging.ERROR, logger=sleep_inhibit.__name__):
        inhibitor.release()

    assert len(process.wait_timeouts) == 2, "one bounded wait per escalation step"
    assert all(_is_finite_positive(t) for t in process.wait_timeouts)
    assert "UNREAPABLE" in caplog.text.upper()
    assert inhibitor.held is False

    inhibitor.release()  # and the state is still consistent afterwards
    assert process.terminate_calls == 1


def test_release_with_nothing_held_is_a_no_op() -> None:
    runner = FakeRunner()
    inhibitor = SleepInhibitor(runner=runner)

    inhibitor.release()  # never acquired

    assert runner.kill_group_calls == []
    assert runner.spawn_argvs == []
    assert inhibitor.held is False


def test_release_twice_is_a_no_op() -> None:
    process = FakeProcess()
    inhibitor = SleepInhibitor(runner=FakeRunner(process=process))
    inhibitor.acquire()

    inhibitor.release()
    inhibitor.release()

    assert process.terminate_calls == 1, "the second release must not re-signal"
    assert inhibitor.held is False


def test_a_child_that_already_exited_is_not_signalled() -> None:
    process = FakeProcess()
    inhibitor = SleepInhibitor(runner=FakeRunner(process=process))
    inhibitor.acquire()
    process.die()

    inhibitor.release()

    assert process.terminate_calls == 0
    assert process.kill_calls == 0


def test_release_survives_a_handle_that_has_become_unusable() -> None:
    """A broken handle is not a reason to break a caller's teardown."""

    class _BrokenProcess(FakeProcess):
        def terminate(self) -> None:
            raise OSError("no such process")

    process = _BrokenProcess()
    inhibitor = SleepInhibitor(runner=FakeRunner(process=process))
    inhibitor.acquire()

    inhibitor.release()  # must not raise

    assert inhibitor.held is False


def test_a_release_that_lands_during_acquire_is_not_lost() -> None:
    """The startup race: a teardown arriving while the child is being spawned.

    Without the watermark the release finds nothing registered, returns, and the
    lock child then registers itself and outlives the run that asked for it —
    holding the machine awake with nobody left to drop it.
    """
    process = FakeProcess()
    runner = FakeRunner(process=process)
    inhibitor = SleepInhibitor(runner=runner)
    runner.on_spawn = inhibitor.release  # lands mid-acquire, before registration

    outcome = inhibitor.acquire()

    assert outcome.state == STATE_UNAVAILABLE
    assert runner.kill_group_calls == [process], (
        "a child spawned after its release must be killed, not adopted"
    )
    assert inhibitor.held is False


# --------------------------------------------------------------------------
# Never raises
# --------------------------------------------------------------------------


@pytest.mark.parametrize("error_name", _PROBE_ERROR_NAMES)
def test_acquire_never_raises_when_the_probe_raises(error_name: str) -> None:
    inhibitor = SleepInhibitor(runner=FakeRunner(probe_error=_ERRORS[error_name]))

    outcome = inhibitor.acquire()

    assert outcome.state in INHIBIT_STATES
    assert outcome.detail.strip()
    assert inhibitor.held is False


@pytest.mark.parametrize("error_name", _SPAWN_ERROR_NAMES)
def test_acquire_never_raises_when_the_spawn_raises(error_name: str) -> None:
    error = _ERRORS[error_name]
    runner = FakeRunner(spawn_error=error)
    inhibitor = SleepInhibitor(runner=runner)

    outcome = inhibitor.acquire()

    assert outcome.state == STATE_UNAVAILABLE
    assert outcome.detail.strip()
    assert inhibitor.held is False
    # The failure the user is shown must carry the tool's own failure, not a
    # generic "could not take the lock".
    assert type(error).__name__ in outcome.detail


# --------------------------------------------------------------------------
# Capture: the dependency's own words, bounded, with every elision counted
# --------------------------------------------------------------------------


def test_a_long_message_is_elided_with_a_count_and_keeps_its_tail() -> None:
    """A silent truncation reads as completeness — and a *head-only* cap drops
    exactly the line that explains the failure, because a tool's fatal message is
    the last thing it prints."""
    head = "systemd-inhibit: begin-of-message"
    filler = "x" * 4000
    tail = "Failed to inhibit: Access denied"
    output = f"{head} {filler} {tail}"
    expected_omitted = len(output) - OUTPUT_HEAD_CHARS - OUTPUT_TAIL_CHARS

    outcome = SleepInhibitor(
        runner=FakeRunner(probe_result=ProbeResult(1, output))
    ).acquire()

    assert f"[{expected_omitted} character(s) omitted]" in outcome.detail
    assert head in outcome.detail, "the head must survive"
    assert tail in outcome.detail, "the TAIL must survive — it carries the diagnosis"
    assert filler not in outcome.detail, "the bound must actually bind"


def test_a_short_message_is_passed_through_verbatim() -> None:
    """The converse: nothing is elided or annotated when nothing needs to be."""
    output = "Failed to inhibit: Access denied"
    outcome = SleepInhibitor(
        runner=FakeRunner(probe_result=ProbeResult(1, output))
    ).acquire()

    assert output in outcome.detail
    assert "omitted" not in outcome.detail
    assert "replaced" not in outcome.detail


def test_control_characters_are_replaced_and_the_substitution_is_counted() -> None:
    """External bytes going into a message a person reads. Replacing them without
    saying so is the same silent-drop defect in a different coat."""
    outcome = SleepInhibitor(
        runner=FakeRunner(probe_result=ProbeResult(1, "Failed\x00to\x1binhibit"))
    ).acquire()

    assert "[2 control character(s) replaced]" in outcome.detail
    assert "\x00" not in outcome.detail
    assert "\x1b" not in outcome.detail


def test_a_silent_tool_is_reported_as_silent_not_as_an_empty_quote() -> None:
    outcome = SleepInhibitor(
        runner=FakeRunner(probe_result=ProbeResult(1, "   \n  "))
    ).acquire()

    assert outcome.state == STATE_UNAVAILABLE
    assert "printed nothing" in outcome.detail
    assert "It said:" not in outcome.detail


def test_the_probe_exit_code_reaches_the_user() -> None:
    """Exit code, argv and complete output: the diagnostic-completeness trio. The
    argv is provable from `outcome.what`; the code and the output are here."""
    outcome = SleepInhibitor(
        runner=FakeRunner(probe_result=ProbeResult(77, "weird"))
    ).acquire()
    assert "77" in outcome.detail


def test_the_failure_is_logged_as_a_warning_not_printed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A downgrade is what a morning post-mortem needs to find in the log file."""
    with caplog.at_level(logging.WARNING, logger=sleep_inhibit.__name__):
        SleepInhibitor(
            runner=FakeRunner(probe_result=ProbeResult(1, "Access denied"))
        ).acquire()

    assert "Access denied" in caplog.text


# --------------------------------------------------------------------------
# The production runner: the seam must forward what the fake records
# --------------------------------------------------------------------------


def test_the_production_lock_uses_popen_with_a_new_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Closes the gap where a test only ever asserts against its own fake.

    ``subprocess.run`` is monkeypatched to fail loudly: it constructs the child
    internally and never hands it out, so a lock held that way could never be
    signalled by ``release()`` (`CLAUDE.md` rule 9).
    """
    recorded: dict[str, object] = {}

    class _FakePopen:
        def __init__(self, argv: list[str], **kwargs: object) -> None:
            recorded["argv"] = argv
            recorded.update(kwargs)

    def _forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("subprocess.run must never hold the lock")

    monkeypatch.setattr(subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(subprocess, "run", _forbidden)

    SubprocessInhibitRunner().spawn(
        [INHIBIT_BINARY, "sleep", "1"], start_new_session=True
    )

    assert recorded["argv"] == [INHIBIT_BINARY, "sleep", "1"]
    assert recorded["start_new_session"] is True
    # Never a pipe nobody drains: ~64 KiB in and the child blocks in write() for
    # the rest of the night.
    assert recorded["stdout"] is subprocess.DEVNULL
    assert recorded["stderr"] is subprocess.DEVNULL
    assert recorded["stdin"] is subprocess.DEVNULL


def test_the_production_probe_merges_stderr_and_is_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: dict[str, object] = {}

    def _fake_run(
        argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        recorded["argv"] = argv
        recorded.update(kwargs)
        return subprocess.CompletedProcess(argv, 1, "Failed to inhibit: Access denied")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = SubprocessInhibitRunner().probe([INHIBIT_BINARY, "true"], timeout=3.0)

    assert result == ProbeResult(1, "Failed to inhibit: Access denied")
    assert recorded["timeout"] == 3.0
    assert recorded["check"] is False
    assert recorded["stderr"] is subprocess.STDOUT, "stderr must be merged, not dropped"
    assert recorded["stdin"] is subprocess.DEVNULL


def test_the_production_probe_reports_a_silent_tool_without_crashing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``CompletedProcess.stdout`` can be ``None``; the caller must still get a str."""

    def _fake_run(
        argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, None)  # type: ignore[arg-type]

    monkeypatch.setattr(subprocess, "run", _fake_run)

    assert SubprocessInhibitRunner().probe([INHIBIT_BINARY], timeout=1.0).output == ""
