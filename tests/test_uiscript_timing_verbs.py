"""The timed rip (section P5; the owner's ask, the fork's round 36 lap 1 S15).

Four verbs: `install-ripper`, `skip-if-same-build`, `record-timing`,
`compare-timings`, and the section of `fullacceptance.txt` written in them.

* **The timing reader** reads `TrackResult.extraction_elapsed_seconds`, the field
  the cyanrip parser already fills from each track's `Elapsed:` line, so the tests
  feed it the committed fork golden logs verbatim, through the real parser.
* **The comparison** is a measurement: a ratio and an agreement, or a refusal
  that names why ("not determined") — tested for agree, disagree, missing,
  mismatched tracks, mismatched read counts, and one build against itself.
* **The verbs** are driven through a real `ScriptRunner`. `install-ripper` runs
  with the step engine (`HostSetup`) and the version probe (`run_capture`)
  replaced, because the properties that matter there are the runner's: the work
  is off the GUI thread, a stop cancels it, the banner read afterwards is latched,
  and an unknown commit installs nothing.

**What the stand-ins do that the real things do not** (`CLAUDE.md`): the fake
engine runs no command and finishes in milliseconds; the real one rebuilds the
fork for minutes, and a step in flight is NOT interrupted by a cancel (the
engine polls between steps) — the fake models that by polling at the same place,
so it cannot show a real compile running on after a stop. The fake banner is a
string; the real one comes from the host export through the container.
"""

from __future__ import annotations

import math
import threading
from pathlib import Path
from typing import Any

import pytest
from conftest import supply_round_state
from hypothesis import given, settings
from hypothesis import strategies as st
from test_uiscript_rip_verbs import _step_outcome, _window

from platterpus.deps import fork_source
from platterpus.deps import host_setup as host_setup_module
from platterpus.deps.step_engine import StepResult, StepStatus
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog, TrackResult
from platterpus.uiscript import install_verbs
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner
from platterpus.uiscript.script import parse
from platterpus.uiscript.timing_grading import (
    AGREEMENT_TOLERANCE,
    TimingRecord,
    agreement,
    label_problem,
    ratio,
    timing_from_log,
)

pytest.importorskip("PySide6.QtWidgets")
pytestmark = pytest.mark.usefixtures("qapp")

FIXTURES = Path(__file__).parent / "fixtures"
RIG_SCRIPTS = Path(__file__).resolve().parents[1] / "src" / "platterpus" / "rig_scripts"


def _golden(name: str) -> RipLog:
    """A committed fork log, through the real parser."""
    return parse_cyanrip_log((FIXTURES / name).read_text(encoding="utf-8"))


def _record(
    label: str, build: str, seconds: dict[int, float], **kw: Any
) -> TimingRecord:
    return TimingRecord(label=label, build=build, seconds=seconds, **kw)


# --- the reader, on verbatim fixture lines ------------------------------------


def test_the_reader_takes_each_tracks_elapsed_line_from_a_real_log() -> None:
    """r36's golden log: `Elapsed:            0.06 s` and so on, 3 reads each."""
    record = timing_from_log("A1", _golden("cyanrip_fork_golden_reference_r36.log"))
    assert record.build == "platterpus-fork-g088557c"
    assert record.seconds == {1: 0.06, 2: 0.06, 3: 0.03}
    assert record.reads == {1: 3, 2: 3, 3: 3}
    assert record.complete
    text = record.describe()
    assert "track 1 0.06 s" in text and "summed 0.15 s" in text
    assert "read more than once" in text, "a -Z re-read must be said, not hidden"


def test_a_track_without_an_elapsed_line_is_named_not_counted() -> None:
    log = RipLog(
        ripper_build="platterpus-fork-g5f1d036",
        tracks=(
            TrackResult(number=1, extraction_elapsed_seconds=10.0),
            TrackResult(number=2),
            TrackResult(number=3, extraction_elapsed_seconds=math.inf),
        ),
    )
    record = timing_from_log("A1", log)
    assert record.seconds == {1: 10.0}
    assert record.missing == (2, 3)
    assert not record.complete
    assert "NOT DETERMINED for track(s) 2, 3" in record.describe()


@settings(max_examples=60, deadline=None)
@given(st.text(max_size=600))
def test_the_reader_never_raises_on_any_log_text(text: str) -> None:
    """External text reaches it through the parser; neither may raise."""
    record = timing_from_log("x", parse_cyanrip_log(text))
    record.describe()
    ratio(record, record)


@pytest.mark.parametrize(
    ("label", "ok"),
    [("A1", True), ("b.2-x_y", True), ("", False), ("a b", False), ("x" * 33, False)],
)
def test_labels_are_validated_at_the_boundary(label: str, ok: bool) -> None:
    assert (label_problem(label) == "") is ok


# --- the comparison math --------------------------------------------------------


def test_the_ratio_is_the_candidates_sum_over_the_bases() -> None:
    a = timing_from_log("A1", _golden("cyanrip_fork_golden_reference_r35.log"))
    b = timing_from_log("B1", _golden("cyanrip_fork_golden_reference_r36.log"))
    result = ratio(a, b)
    assert result.value == pytest.approx(0.15 / 0.16)
    assert "B1/A1 = 0.938" in result.detail


def test_two_pairs_that_agree_say_the_comparison_is_done() -> None:
    a1 = _record("A1", "g-a", {1: 100.0, 2: 100.0})
    b1 = _record("B1", "g-b", {1: 90.0, 2: 90.0})
    a2 = _record("A2", "g-a", {1: 100.0, 2: 100.0})
    b2 = _record("B2", "g-b", {1: 94.0, 2: 94.0})
    verdict = agreement(ratio(a1, b1), ratio(a2, b2))
    assert verdict.agree is True
    assert "AGREE" in verdict.detail and "comparison is done" in verdict.detail


def test_two_pairs_further_apart_than_the_tolerance_disagree() -> None:
    first = ratio(_record("A1", "g-a", {1: 100.0}), _record("B1", "g-b", {1: 90.0}))
    second = ratio(_record("A2", "g-a", {1: 100.0}), _record("B2", "g-b", {1: 96.0}))
    assert abs(first.value - second.value) > AGREEMENT_TOLERANCE  # type: ignore[operator]  # both values are set here
    verdict = agreement(first, second)
    assert verdict.agree is False and "DISAGREE" in verdict.detail


def test_exactly_the_tolerance_apart_still_agrees() -> None:
    first = ratio(_record("A1", "g-a", {1: 100.0}), _record("B1", "g-b", {1: 100.0}))
    second = ratio(_record("A2", "g-a", {1: 100.0}), _record("B2", "g-b", {1: 105.0}))
    assert agreement(first, second).agree is True


def test_a_missing_timing_is_not_determined() -> None:
    result = ratio(None, _record("B1", "g-b", {1: 1.0}))
    assert result.value is None and "not determined" in result.refusal
    verdict = agreement(result, result)
    assert verdict.agree is None and "not determined" in verdict.detail


def test_different_track_sets_are_refused() -> None:
    result = ratio(
        _record("A1", "g-a", {1: 1.0, 2: 1.0}), _record("B1", "g-b", {1: 1.0, 3: 1.0})
    )
    assert result.value is None and "track sets differ" in result.refusal


def test_different_read_counts_are_refused() -> None:
    a = timing_from_log("A1", _golden("cyanrip_fork_golden_reference.log"))  # 2 reads
    b = timing_from_log("B1", _golden("cyanrip_fork_golden_reference_r36.log"))  # 3
    result = ratio(a, b)
    assert result.value is None and "different number of times" in result.refusal


def test_one_build_against_itself_is_refused() -> None:
    result = ratio(_record("A1", "g-a", {1: 1.0}), _record("B1", "g-a", {1: 2.0}))
    assert result.value is None and "compared with itself" in result.refusal


def test_an_unnamed_build_is_refused() -> None:
    result = ratio(_record("A1", "", {1: 1.0}), _record("B1", "g-b", {1: 2.0}))
    assert result.value is None and "names no build" in result.refusal


# --- the verbs, through a real runner ----------------------------------------


def _window_after(log: RipLog, tmp_path: Path) -> Any:
    return _window(last_rip_log=log, last_rip_log_file=tmp_path / "rip.log")


def test_record_timing_records_info_and_compare_prints_the_ratio(
    tmp_path: Path,
) -> None:
    runner = ScriptRunner(_window(last_rip_log=None))
    for label, name in (
        ("A1", "cyanrip_fork_golden_reference_r35.log"),
        ("B1", "cyanrip_fork_golden_reference_r36.log"),
    ):
        runner._window = _window_after(_golden(name), tmp_path)
        runner._execute(parse(f"record-timing {label}")[0])
        assert runner._report.steps[-1].outcome is Outcome.INFO, runner._report.steps[
            -1
        ].detail
    runner._execute(parse("compare-timings A1 B1")[0])
    step = runner._report.steps[-1]
    assert step.outcome is Outcome.INFO and "B1/A1 = 0.938" in step.detail


def test_compare_with_four_labels_reports_both_ratios_and_the_agreement() -> None:
    runner = ScriptRunner(_window())
    runner._timings = {
        "A1": _record("A1", "g-a", {1: 100.0}),
        "B1": _record("B1", "g-b", {1: 90.0}),
        "A2": _record("A2", "g-a", {1: 100.0}),
        "B2": _record("B2", "g-b", {1: 92.0}),
    }
    runner._execute(parse("compare-timings A1 B1 A2 B2")[0])
    step = runner._report.steps[-1]
    assert step.outcome is Outcome.INFO
    assert "B1/A1 = 0.900" in step.detail and "B2/A2 = 0.920" in step.detail
    assert "AGREE" in step.detail


def test_compare_refuses_as_an_error_when_a_timing_is_missing() -> None:
    runner = ScriptRunner(_window())
    runner._execute(parse("compare-timings A1 B1 A2 B2")[0])
    step = runner._report.steps[-1]
    assert step.outcome is Outcome.ERROR and "not determined" in step.detail


def test_compare_with_three_labels_is_an_error() -> None:
    runner = ScriptRunner(_window())
    runner._execute(parse("compare-timings A1 B1 A2")[0])
    assert runner._report.steps[-1].outcome is Outcome.ERROR


def test_record_timing_with_no_rip_records_the_readers_failure() -> None:
    runner = ScriptRunner(_window(last_rip_log=None))
    runner._execute(parse("record-timing A1")[0])
    assert runner._report.steps[-1].outcome is Outcome.FAIL
    assert "A1" not in runner._timings


def test_a_new_run_forgets_the_last_runs_timings() -> None:
    runner = ScriptRunner(_window())
    runner._timings = {"A1": _record("A1", "g-a", {1: 1.0})}
    runner._same_build_skip = "stale"
    runner.start(parse("log hi"), source="log hi")
    runner.stop()
    assert runner._timings == {} and runner._same_build_skip == ""


# --- nothing to compare -------------------------------------------------------


_SECTION = (
    "log --- P5. timed ---\n"
    "run-size full\n"
    "skip-if-same-build (fork-pin) (under-review)\n"
    "set read_speed_mode fixed\n"
    "install-ripper (fork-pin)\n"
    "record-timing A1\n"
    "log --- Q. next ---\n"
    "log reached\n"
)


def test_one_build_says_nothing_to_compare_and_runs_nothing(
    qapp: Any, process_until: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    supply_round_state(monkeypatch, "no-round")
    win = _window()
    runner = ScriptRunner(win)
    runner.set_run_size("full")
    emitted: list[Any] = []
    runner.finished.connect(emitted.append)
    runner.start(parse(_SECTION), source=_SECTION)
    assert process_until(lambda: bool(emitted)), "the run never finished"
    rows = {s.source: s for s in emitted[0].steps}
    skip = rows["skip-if-same-build (fork-pin) (under-review)"]
    assert skip.outcome is Outcome.INFO and "nothing to compare" in skip.detail
    for later in (
        "set read_speed_mode fixed",
        "install-ripper (fork-pin)",
        "record-timing A1",
    ):
        assert rows[later].outcome is Outcome.UNREACHABLE, rows[later]
        assert "nothing to compare" in rows[later].detail
    assert win._config.read_speed_mode != "fixed", "a skipped `set` still ran"
    assert rows["log reached"].outcome is Outcome.PASS, (
        "the skip leaked past its section"
    )
    assert emitted[0].ok, "nothing went wrong, so the run must still be ok"


def test_two_builds_set_up_the_comparison(monkeypatch: pytest.MonkeyPatch) -> None:
    supply_round_state(monkeypatch, "round-open")
    runner = ScriptRunner(_window())
    runner._execute(parse("skip-if-same-build (fork-pin) (under-review)")[0])
    step = runner._report.steps[-1]
    assert step.outcome is Outcome.INFO and "comparing" in step.detail
    assert fork_source.FORK_PIN in step.detail and "abc1234" in step.detail
    assert runner._same_build_skip == ""


def test_an_unresolvable_build_is_an_error_and_skips_the_section() -> None:
    runner = ScriptRunner(_window())
    runner._execute(parse("skip-if-same-build (fork-pin) deadbee")[0])
    assert runner._report.steps[-1].outcome is Outcome.ERROR
    assert runner._same_build_skip


# --- install-ripper -------------------------------------------------------------


class _Engine:
    """`HostSetup` stand-in: records its target and thread; polls `cancelled()`
    before each of its two steps, as the real engine does; can be held open."""

    made: list[_Engine] = []
    hold: threading.Event | None = None

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.thread = 0
        self.cancel_seen = False
        _Engine.made.append(self)

    def run(
        self,
        progress: Any = None,
        dry_run: bool = False,
        cancelled: Any = None,
    ) -> list[StepResult]:
        del dry_run
        self.thread = threading.get_ident()
        results: list[StepResult] = []
        for sid in ("container", "cyanrip_fork"):
            if _Engine.hold is not None:
                _Engine.hold.wait(10)
            if cancelled is not None and cancelled():
                self.cancel_seen = True
                results.append(StepResult(sid, sid, StepStatus.CANCELLED))
                continue
            result = StepResult(sid, sid.title(), StepStatus.RAN)
            results.append(result)
            if progress is not None:
                progress(result)
        return results

    def is_ready(self) -> bool:
        return not self.cancel_seen


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> type[_Engine]:
    _Engine.made = []
    _Engine.hold = None
    monkeypatch.setattr(host_setup_module, "HostSetup", _Engine)
    monkeypatch.setattr(
        "platterpus.paths.LOG_PATH", tmp_path / "share" / "log.txt", raising=False
    )
    return _Engine


def _banner(
    monkeypatch: pytest.MonkeyPatch, text: str, code: int = 0
) -> list[list[str]]:
    """Stand in for the info probe the cyanrip adapter's `version()` runs."""
    calls: list[list[str]] = []

    def fake(tool: str, binary: str, args: list[str], **_: Any) -> tuple[int, str]:
        calls.append([binary, *args])
        return code, text

    monkeypatch.setattr("platterpus.adapters.cyanrip_backend.run_capture", fake)
    return calls


def test_install_ripper_installs_off_the_gui_thread_and_latches_the_banner(
    qapp: Any,
    process_until: Any,
    monkeypatch: pytest.MonkeyPatch,
    engine: type[_Engine],
) -> None:
    supply_round_state(monkeypatch, "round-open")
    calls = _banner(monkeypatch, "cyanrip 0.9.4 (platterpus-fork-gabc1234)\n")
    runner = ScriptRunner(_window())
    step = _step_outcome(runner, qapp, process_until, "install-ripper (under-review)")
    assert step.outcome is Outcome.PASS, step.detail
    (made,) = engine.made
    assert made.kwargs["fork_target"].pin == "abc1234"
    assert made.thread != threading.get_ident(), "the install ran on the GUI thread"
    assert calls and calls[0][1:] in (["-V"], ["--version"])
    assert runner._ripper_build_tag == "platterpus-fork-gabc1234"
    assert "installed and verified: platterpus-fork-gabc1234" in step.detail
    assert "[ done ] Container" in step.detail


def test_install_ripper_fails_when_the_export_prints_another_build(
    qapp: Any,
    process_until: Any,
    monkeypatch: pytest.MonkeyPatch,
    engine: type[_Engine],
) -> None:
    _banner(monkeypatch, "cyanrip 0.9.4 (platterpus-fork-g93afa15)\n")
    runner = ScriptRunner(_window())
    step = _step_outcome(runner, qapp, process_until, "install-ripper (fork-pin)")
    assert step.outcome is Outcome.FAIL
    assert "prints platterpus-fork-g93afa15" in step.detail
    # The latch names what IS installed, wrong or not: the next steps must see it.
    assert runner._ripper_build_tag == "platterpus-fork-g93afa15"


def test_install_ripper_refuses_an_unknown_commit_and_installs_nothing(
    engine: type[_Engine],
) -> None:
    runner = ScriptRunner(_window())
    runner._execute(parse("install-ripper deadbee")[0])
    step = runner._report.steps[-1]
    assert step.outcome is Outcome.ERROR and "nothing was installed" in step.detail
    assert engine.made == []


def test_install_ripper_refuses_while_a_rip_is_running(engine: type[_Engine]) -> None:
    runner = ScriptRunner(_window(rip_worker=object()))
    runner._execute(parse("install-ripper (fork-pin)")[0])
    assert runner._report.steps[-1].outcome is Outcome.FAIL
    assert engine.made == []


def test_stopping_the_run_mid_install_cancels_the_engine(
    qapp: Any,
    process_until: Any,
    monkeypatch: pytest.MonkeyPatch,
    engine: type[_Engine],
) -> None:
    """Rule #9: the cancel reaches the engine, which stops before its next step."""
    _banner(monkeypatch, "cyanrip (platterpus-fork-g5f1d036)\n")
    engine.hold = threading.Event()
    runner = ScriptRunner(_window())
    emitted: list[Any] = []
    runner.finished.connect(emitted.append)
    source = "install-ripper (fork-pin)\nlog after"
    runner.start(parse(source), source=source)
    assert process_until(lambda: runner._deadline_step is not None and engine.made)
    runner.stop()
    engine.hold.set()
    assert process_until(lambda: engine.made[0].cancel_seen), (
        "a stopped run left the install going on to its next step"
    )
    rows = {s.source: s.outcome for s in emitted[0].steps}
    assert rows["install-ripper (fork-pin)"] is Outcome.BLOCKED


def test_a_failed_install_is_a_fail_naming_the_log(
    qapp: Any,
    process_until: Any,
    monkeypatch: pytest.MonkeyPatch,
    engine: type[_Engine],
) -> None:
    calls = _banner(monkeypatch, "unused")

    class _Broken(_Engine):
        def is_ready(self) -> bool:
            return False

    monkeypatch.setattr(host_setup_module, "HostSetup", _Broken)
    step = _step_outcome(
        ScriptRunner(_window()), qapp, process_until, "install-ripper (fork-pin)"
    )
    assert step.outcome is Outcome.FAIL and "Setup did not complete" in step.detail
    assert calls == [], "the banner probe ran after an install that did not complete"


def test_the_install_wait_is_bounded() -> None:
    """45 minutes: past any healthy rebuild, and finite."""
    assert 600 < install_verbs.INSTALL_RIPPER_WAIT_S <= 3600


# --- the committed section ------------------------------------------------------


def _p5_lines() -> list[str]:
    text = (RIG_SCRIPTS / "fullacceptance.txt").read_text(encoding="utf-8")
    body = text.split("log --- P5.", 1)[1].split("log --- ", 1)[0]
    return [
        ln.strip()
        for ln in body.splitlines()[1:]
        if ln.strip() and not ln.strip().startswith("#")
    ]


def test_the_committed_section_alternates_the_builds_and_compares_the_pairs() -> None:
    lines = _p5_lines()
    assert lines[0] == "run-size full", "a timed rip is a Full-run section"
    assert lines[1] == "skip-if-same-build (fork-pin) (under-review)"
    installs = [ln.split()[1] for ln in lines if ln.startswith("install-ripper ")]
    assert installs == [
        "(fork-pin)",
        "(under-review)",
        "(fork-pin)",
        "(under-review)",
        "(pin)",
    ], "S15: A, B, A, B, then back to the build section A accepts"
    recorded = [ln.split()[1] for ln in lines if ln.startswith("record-timing ")]
    assert recorded == ["A1", "B1", "A2", "B2"]
    assert "compare-timings A1 B1 A2 B2" in lines
    assert lines.count("rip") == 4
    # Every install sits before a rip, never between a rip and its wait.
    for index, line in enumerate(lines):
        if line == "rip":
            before = lines[:index]
            last_install = max(
                i for i, ln in enumerate(before) if ln.startswith("install-ripper")
            )
            assert all(ln != "rip" for ln in before[last_install + 1 :])
    assert (
        "set secure_rerip_matches 0" in lines and "set read_speed_mode fixed" in lines
    )
    assert "select-tracks 1-3" in lines


def test_every_step_of_the_section_is_a_known_built_verb() -> None:
    from platterpus.uiscript.verbs import VERBS

    steps = parse("\n".join(_p5_lines()))
    assert len(steps) >= 40
    for step in steps:
        assert step.ok, (step.source, step.error)
        assert VERBS[step.verb].implemented
        assert hasattr(ScriptRunner, f"_do_{step.verb.replace('-', '_')}"), step.verb
