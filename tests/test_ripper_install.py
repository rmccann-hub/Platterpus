"""`deps/ripper_install.py`: the one function behind `--install-ripper` and the
`install-ripper` script verb.

Three properties, each one a way the two callers could drift apart or a script
could install the wrong thing:

* **What a script may install** is a closed set: a numbered fork release our
  record holds, the approved pin, or the build under review, by keyword or by a
  hex commit that names exactly one of them. Anything else is refused with a
  reason, because an unattended batch that could build any sha would install
  whatever a typo named.
* **The install is the step engine's**, run once, with its verdict read as "is
  the ripper usable" (an optional step's failure does not make it unusable) and a
  cancel that stops the engine between steps.
* **There is one implementation**: both callers delegate to `run_install`, and
  neither constructs `HostSetup` itself (read from their source, the artifact).

**What the stand-in does that the real thing does not** (`CLAUDE.md`): the fake
`HostSetup` runs no command and polls `cancelled()` exactly where the real
engine does (before each step) but has two steps, not eight; the fake runner's
output is canned. Nothing here proves a real build succeeds — that is the rig's,
and the engine's own tests (`tests/test_deps_host_setup.py`).
"""

from __future__ import annotations

import ast
import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import supply_round_state

from platterpus.deps import fork_source, ripper_install
from platterpus.deps import host_setup as host_setup_module
from platterpus.deps.step_engine import StepResult, StepStatus

SRC = Path(__file__).resolve().parents[1] / "src" / "platterpus"


# --- what a script may install --------------------------------------------------


def test_each_keyword_resolves_through_the_record() -> None:
    assert ripper_install.resolve_script_commit("(fork-pin)") == (
        fork_source.FORK_PIN,
        "",
    )
    assert ripper_install.resolve_script_commit("(under-review)") == (
        fork_source.PIN_UNDER_REVIEW,
        "",
    )
    assert ripper_install.resolve_script_commit("(pin)") == (
        fork_source.pin_the_rig_should_install(),
        "",
    )


def test_the_keywords_follow_the_record_when_it_moves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A committed script names a ROLE, so a round opening moves what it installs."""
    supply_round_state(monkeypatch, "round-open")
    assert ripper_install.resolve_script_commit("(under-review)") == ("abc1234", "")
    assert ripper_install.resolve_script_commit("(fork-pin)")[0] == fork_source.FORK_PIN
    assert ripper_install.resolve_script_commit("(pin)") == ("abc1234", "")


def test_a_known_release_resolves_to_its_recorded_spelling() -> None:
    """A full sha of a known release resolves to the seven characters the build
    tag carries, which is what the verify step compares against."""
    commit, refusal = ripper_install.resolve_script_commit("93afa15" + "0" * 33)
    assert (commit, refusal) == ("93afa15", "")
    assert ripper_install.resolve_script_commit("93AFA15") == ("93afa15", "")


def test_an_unknown_commit_is_refused_with_the_known_list() -> None:
    commit, refusal = ripper_install.resolve_script_commit("deadbee")
    assert commit == ""
    assert "not a build this Platterpus knows" in refusal
    assert fork_source.FORK_PIN in refusal, "the refusal should say what IS allowed"


@pytest.mark.parametrize(
    "spec", ["", "latest", "abc", "93afa1", "93afa15; rm", "(newest)", "g93afa15"]
)
def test_anything_but_a_hex_commit_or_a_keyword_is_refused(spec: str) -> None:
    commit, refusal = ripper_install.resolve_script_commit(spec)
    assert commit == "" and refusal, spec


def test_the_build_under_review_is_installable_before_the_fork_numbers_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`.26` may be a round's subject before a manifest row exists for it."""
    supply_round_state(monkeypatch, "round-open")
    assert "abc1234" not in fork_source.FORK_RELEASE_SEQ_BY_PIN
    assert ripper_install.resolve_script_commit("abc1234") == ("abc1234", "")


# --- the run itself -------------------------------------------------------------


class _Engine:
    """A `HostSetup` stand-in: two steps, `cancelled()` polled before each."""

    instances: list[_Engine] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.ready = True
        self.fail_step = ""
        self.raise_on_run = False
        self.ran_steps: list[str] = []
        self.before_step: Callable[[str], None] = lambda _sid: None
        _Engine.instances.append(self)

    def run(
        self,
        progress: Callable[[StepResult], None] | None = None,
        dry_run: bool = False,
        cancelled: Callable[[], bool] | None = None,
    ) -> list[StepResult]:
        del dry_run
        if self.raise_on_run:
            raise RuntimeError("engine fault")
        results: list[StepResult] = []
        for sid in ("container", "cyanrip_fork"):
            self.before_step(sid)
            if cancelled is not None and cancelled():
                results.append(StepResult(sid, sid, StepStatus.CANCELLED))
                continue
            self.ran_steps.append(sid)
            status = StepStatus.FAILED if sid == self.fail_step else StepStatus.RAN
            result = StepResult(sid, sid.title(), status, "detail")
            results.append(result)
            if progress is not None:
                progress(result)
        return results

    def is_ready(self) -> bool:
        return self.ready


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> type[_Engine]:
    _Engine.instances = []
    monkeypatch.setattr(host_setup_module, "HostSetup", _Engine)
    return _Engine


def test_run_install_builds_the_target_it_was_given(engine: type[_Engine]) -> None:
    target = fork_source.target_for_commit("93afa15")
    seen: list[str] = []
    outcome = ripper_install.run_install(
        target, progress=lambda r: seen.append(r.title)
    )
    assert outcome.ready and outcome.exit_code == 0
    assert engine.instances[0].kwargs["fork_target"] is target
    assert seen == ["Container", "Cyanrip_Fork"], "progress was not wired"
    assert "Ripping stack is ready" in ripper_install.outcome_text(outcome)


def test_an_optional_failure_leaves_the_ripper_usable(
    engine: type[_Engine], monkeypatch: pytest.MonkeyPatch
) -> None:
    """KDD-29: the verdict is the engine's `is_ready`, not "every step passed"."""

    def factory(**kwargs: Any) -> _Engine:
        made = _Engine(**kwargs)
        made.fail_step = "cyanrip_fork"
        return made

    monkeypatch.setattr(host_setup_module, "HostSetup", factory)
    outcome = ripper_install.run_install(fork_source.PRODUCTION_TARGET)
    assert outcome.ready and outcome.failed == ("Cyanrip_Fork",)
    assert "Optional step(s) did not complete: Cyanrip_Fork" in (
        ripper_install.outcome_text(outcome)
    )


def test_a_cancel_stops_the_engine_between_steps(
    engine: type[_Engine], monkeypatch: pytest.MonkeyPatch
) -> None:
    flag = {"stop": False}

    def factory(**kwargs: Any) -> _Engine:
        made = _Engine(**kwargs)
        made.before_step = lambda sid: flag.update(stop=sid == "cyanrip_fork")
        return made

    monkeypatch.setattr(host_setup_module, "HostSetup", factory)
    outcome = ripper_install.run_install(
        fork_source.PRODUCTION_TARGET, cancelled=lambda: flag["stop"]
    )
    assert outcome.cancelled and not outcome.ready
    assert outcome.results[-1].status is StepStatus.CANCELLED
    assert "cancelled before a step started" in ripper_install.outcome_text(outcome)


def test_an_engine_that_raises_is_reported_not_raised(
    engine: type[_Engine], monkeypatch: pytest.MonkeyPatch
) -> None:
    def factory(**kwargs: Any) -> _Engine:
        made = _Engine(**kwargs)
        made.raise_on_run = True
        return made

    monkeypatch.setattr(host_setup_module, "HostSetup", factory)
    outcome = ripper_install.run_install(fork_source.PRODUCTION_TARGET)
    assert not outcome.ready and "engine fault" in outcome.crash
    assert outcome.exit_code == 1


class _Runner:
    """A `CommandRunner` with canned answers, recording what it was asked."""

    def __init__(self, output: str, code: int = 0) -> None:
        self.output, self.code = output, code
        self.asked: list[list[str]] = []

    def which(self, name: str) -> bool:
        return name == "distrobox"

    def exists(self, path: Path) -> bool:
        return path.name == "cyanrip"

    def run(self, argv: list[str]) -> tuple[int, str]:
        self.asked.append(argv)
        return self.code, self.output


def test_the_recording_runner_delegates_and_keeps_head_and_tail() -> None:
    long_output = "\n".join(f"line {n}" for n in range(200)) + "\nfatal: the end\n"
    inner = _Runner(long_output, code=2)
    recorder = ripper_install.RecordingRunner(inner)
    assert recorder.which("distrobox") and recorder.exists(Path("/x/cyanrip"))
    argv = ["sh", "-c", "echo one\necho two", "build-cyanrip-fork"]
    assert recorder.run(argv) == (2, long_output)
    assert inner.asked == [argv], "the call did not reach the wrapped runner"
    (record,) = recorder.commands
    assert record.exit_code == 2
    assert record.argv == "sh -c echo one\\necho two build-cyanrip-fork"
    assert "fatal: the end" in record.output, "the tail, where the failure is, was cut"
    assert "line 0" in record.output and "line(s) omitted" in record.output


# --- one implementation, two callers ---------------------------------------------


def _constructs_host_setup(source: str) -> bool:
    tree = ast.parse(source)
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "HostSetup"
        for node in ast.walk(tree)
    )


def test_both_callers_delegate_and_neither_builds_the_engine_itself() -> None:
    """`CLAUDE.md`: a verb and a flag doing one job are two thin callers of ONE
    function. Read off the source, so a second implementation fails here."""
    import textwrap

    from platterpus.uiscript import install_verbs

    cli = (SRC / "app.py").read_text(encoding="utf-8")
    block = cli.split("if args.install_ripper is not None:", 1)[1].split(
        "# Rig-session mode", 1
    )[0]
    verb = textwrap.dedent(
        inspect.getsource(install_verbs.InstallVerbsMixin._do_install_ripper)
    )
    assert "ripper_install.run_install(" in block
    assert "ripper_install.run_install(" in verb
    assert not _constructs_host_setup(textwrap.dedent("if True:\n" + block))
    assert not _constructs_host_setup(verb)
