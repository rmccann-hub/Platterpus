"""The block-framing verbs: ``expect-kept`` (TASKS R189), ``run-block`` and
``expect-repeats`` (TASKS R188).

Each is driven through the real :class:`ScriptRunner` against a stand-in window
that carries only what the verbs read (``_config``), so a step's outcome is the
runner's own verdict and not this file's reading of it.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Final

import pytest

from platterpus.config import Config
from platterpus.uiscript import blocks, run_block
from platterpus.uiscript.accuracy_grading import AccuracyRecord, TrackAccuracy
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.script import parse
from platterpus.verdict import AR_STATE_NO_MATCH, AR_STATE_VERIFIED

_RIG: Final[Path] = (
    Path(__file__).resolve().parents[1] / "src" / "platterpus" / "rig_scripts"
)


class _Window:
    """What `keep`, `set`, `expect-kept` and `log` read: the running settings."""

    def __init__(self, config: Config) -> None:
        self._config: Config = config


def _run(qapp: object, window: _Window, text: str) -> list[tuple[str, Outcome, str]]:
    """Run ``text`` to the end; ``[(source, outcome, detail)]`` per step."""
    del qapp  # the runner's timer needs the application
    from platterpus.uiscript.runner import ScriptRunner

    runner = ScriptRunner(window)  # type: ignore[arg-type]  # a stand-in: these verbs read only _config
    runner.start(parse(text))
    for _ in range(500):  # bounded: one step per tick
        if not runner.running:
            break
        runner._tick()
    assert not runner.running
    return [(s.source, s.outcome, s.detail) for s in runner._report.steps]


# --- expect-kept (TASKS R189) ------------------------------------------------


@pytest.mark.parametrize("value", [True, False])
def test_expect_kept_passes_on_the_value_it_found_whatever_it_was(
    qapp: object, value: bool
) -> None:
    """The defect: `expect force_overread off` failed an owner whose Overread
    was ON before the run. `expect-kept` grades the probe, not their choice."""
    window = _Window(dataclasses.replace(Config(), force_overread=value))
    rows = _run(qapp, window, "keep force_overread\nexpect-kept force_overread")
    assert [r[1] for r in rows] == [Outcome.PASS, Outcome.PASS], rows


def test_expect_kept_fails_when_the_setting_changed_and_names_both_values(
    qapp: object,
) -> None:
    window = _Window(dataclasses.replace(Config(), force_overread=False))
    rows = _run(
        qapp,
        window,
        "keep force_overread\nset force_overread on\nexpect-kept force_overread",
    )
    source, outcome, detail = rows[-1]
    assert outcome is Outcome.FAIL, rows
    assert "False" in detail and "True" in detail, detail


def test_expect_kept_with_no_keep_is_an_error_never_a_pass(qapp: object) -> None:
    window = _Window(Config())
    rows = _run(qapp, window, "expect-kept force_overread\nexpect-kept no_such")
    assert [r[1] for r in rows] == [Outcome.ERROR, Outcome.ERROR], rows
    assert "no `keep force_overread`" in rows[0][2]


def test_a_new_run_forgets_what_the_last_one_kept(qapp: object) -> None:
    window = _Window(Config())
    assert _run(qapp, window, "keep force_overread")[0][1] is Outcome.PASS
    rows = _run(qapp, window, "expect-kept force_overread")
    assert rows[0][1] is Outcome.ERROR, rows


def test_the_overread_probe_keeps_the_setting_before_its_first_read() -> None:
    """R189: keep before the first `-O` read, expect-kept as the last step, and
    the header says where the two logs are, not 'the bundle the run ends with'."""
    text = (_RIG / "overreadprobe.txt").read_text(encoding="utf-8")
    steps = parse(text)
    first_read = next(
        i for i, s in enumerate(steps) if s.verb == "cyanrip" and "-O" in s.args
    )
    kept = [i for i, s in enumerate(steps) if s.verb == "keep"]
    assert kept and kept[0] < first_read
    assert steps[kept[0]].args == ("force_overread",)
    assert (steps[-1].verb, steps[-1].args) == ("expect-kept", ("force_overread",))
    assert not any(s.verb == "expect" and s.args[0] == "force_overread" for s in steps)
    assert "the bundle the run ends with" not in text.lower()
    header = text.split("\nlog ", 1)[0]
    assert "overreadleadout" in header and "overreadleadin" in header
    assert "rips folder" in header and "whole output" in header


# --- run-block: expanded when the run starts (TASKS R188) ----------------------


def _expand(text: str) -> run_block.Expansion:
    return run_block.expand_run_blocks(parse(text))


def test_run_block_expands_each_run_under_its_own_label() -> None:
    expansion = _expand("log before\nrun-block repeatrip ×3 as r\nlog after")
    assert expansion.runs == {"r": 3}
    assert expansion.blocks == ("repeatrip",)
    steps = expansion.steps
    assert steps[0].source == "log before" and steps[-1].source == "log after"
    body = steps[1:-1]
    text, _ = blocks.block_text("repeatrip")
    assert text is not None
    per_run = len(parse(text))
    assert len(body) == 3 * (per_run + 1)  # each run: its log line, then its steps
    assert all(step.ok for step in body)
    assert all(step.line_no == 2 for step in body), "a run keeps its run-block line"
    records = [s.args[0] for s in body if s.verb == "record-accuracy"]
    assert records == ["r1", "r2", "r3"]
    albums = [s.joined() for s in body if s.verb == "album"]
    assert albums == [f"repeat rip r{i} (run) (ripper)" for i in (1, 2, 3)]
    assert not any("(label)" in s.source for s in body)


@pytest.mark.parametrize("count", ["×5", "x5", "X5"])
def test_the_count_may_be_typed_with_a_letter(count: str) -> None:
    assert _expand(f"run-block repeatrip {count} as r").runs == {"r": 5}


@pytest.mark.parametrize(
    ("line", "said"),
    [
        ("run-block nosuchblock ×2 as r", "no block called"),
        ("run-block repeatrip 5 as r", "not a count"),
        ("run-block repeatrip ×0 as r", "1 to 20"),
        ("run-block repeatrip ×21 as r", "1 to 20"),
        ("run-block repeatrip ×2 for r", "write it as"),
        ("run-block repeatrip ×2 as bad/label", "label"),
    ],
)
def test_a_line_that_cannot_expand_stays_one_step_carrying_its_error(
    line: str, said: str
) -> None:
    expansion = _expand(line)
    assert expansion.runs == {}
    [step] = expansion.steps
    assert not step.ok and said in step.error, step.error


def test_a_label_names_one_run_block_only() -> None:
    expansion = _expand("run-block repeatrip ×1 as r\nrun-block repeatrip ×1 as r")
    assert expansion.runs == {"r": 1}
    assert not expansion.steps[-1].ok
    assert "earlier run-block" in expansion.steps[-1].error


def test_no_block_runs_another_block() -> None:
    """A block is a list, not a subroutine library: no nesting, so no loops."""
    for block in blocks.BLOCKS:
        text, _ = blocks.block_text(block.name)
        assert text is not None
        assert not any(s.verb == "run-block" for s in parse(text)), block.name


def test_the_runner_expands_before_the_preflight_and_the_estimate(
    qapp: object,
) -> None:
    del qapp
    from platterpus.uiscript.runner import ScriptRunner

    runner = ScriptRunner(_Window(Config()))  # type: ignore[arg-type]  # a stand-in: start reads only _config
    runner.name_test("repeatrips", ("needripper", "repeatrip"))
    runner.start(parse("run-block repeatrip ×2 as r"))
    runner.stop("the test only needed the start")
    assert len(runner._steps) > 10
    assert runner._repeat_runs == {"r": 2}
    assert runner._report.test_name == "repeatrips"
    assert runner._report.blocks == ("needripper", "repeatrip", "repeatrip")
    assert not runner._report.counts_as_evidence
    assert runner._report.as_dict()["test"] == "repeatrips"


def test_an_unexpanded_run_block_is_an_error_never_a_pass(qapp: object) -> None:
    """The handler exists for the verb sweep; reaching it means expansion failed."""
    del qapp
    from platterpus.uiscript.runner import ScriptRunner

    runner = ScriptRunner(_Window(Config()))  # type: ignore[arg-type]  # a stand-in
    [step] = parse("run-block repeatrip ×2 as r")
    runner._do_run_block(step)
    assert runner._report.steps[-1].outcome is Outcome.ERROR


# --- expect-repeats ------------------------------------------------------------


def _record(label: str, *tracks: tuple[int, str, str]) -> AccuracyRecord:
    return AccuracyRecord(
        label,
        "platterpus-fork-g0000000",
        tuple(TrackAccuracy(n, state, crc32=crc) for n, state, crc in tracks),
    )


_V = AR_STATE_VERIFIED
_M = AR_STATE_NO_MATCH


def _five(track3: list[tuple[str, str]]) -> dict[str, AccuracyRecord]:
    """Runs of track 1 verified at AAAA every time, and track 3 as given."""
    return {
        f"r{i}": _record(f"r{i}", (1, _V, "AAAA"), (3, state, crc))
        for i, (state, crc) in enumerate(track3, start=1)
    }


def _grade(
    words: str, records: dict[str, AccuracyRecord], runs: int | None = 5
) -> run_block.RepeatVerdict:
    rule, problem = run_block.parse_rule(words.split())
    assert rule is not None, problem
    return run_block.grade_repeats("r", rule, runs, records)


def test_verified_passes_when_every_track_verifies_in_every_run() -> None:
    verdict = _grade("verified", _five([(_V, "BBBB")] * 5))
    assert verdict.verdict == run_block.PASS, verdict.detail


def test_verified_fails_naming_the_run_and_the_track() -> None:
    track3 = [(_V, "BBBB")] * 5
    track3[3] = (_M, "CCCC")
    verdict = _grade("verified", _five(track3))
    assert verdict.verdict == run_block.FAIL
    assert "track 3" in verdict.detail and "r4 (mismatch)" in verdict.detail


def test_same_crc_fails_naming_each_run_s_crc() -> None:
    track3 = [(_V, "BBBB")] * 5
    track3[1] = (_V, "CCCC")
    verdict = _grade("same-crc", _five(track3))
    assert verdict.verdict == run_block.FAIL
    assert "track 3" in verdict.detail and "r2 CCCC" in verdict.detail
    assert _grade("same-crc", _five([(_M, "BBBB")] * 5)).verdict == run_block.PASS


def test_at_least_counts_the_verified_runs_per_track() -> None:
    track3 = [(_V, "B"), (_M, "C"), (_V, "B"), (_V, "B"), (_V, "B")]
    assert _grade("at-least 4 of 5", _five(track3)).verdict == run_block.PASS
    verdict = _grade("at-least 5 of 5", _five(track3))
    assert verdict.verdict == run_block.FAIL
    assert "verified in 4 of 5" in verdict.detail and "r2" in verdict.detail


def test_a_missing_run_is_not_determined_unless_the_rest_already_broke_it() -> None:
    records = _five([(_V, "B")] * 5)
    del records["r5"]
    verdict = _grade("verified", records)
    assert verdict.verdict == run_block.NOT_DETERMINED
    assert "r5" in verdict.detail
    assert _grade("at-least 5 of 5", records).verdict == run_block.NOT_DETERMINED
    records["r2"] = _record("r2", (1, _V, "AAAA"), (3, _M, "C"))
    assert _grade("verified", records).verdict == run_block.FAIL


def test_with_no_run_block_there_is_nothing_to_compare() -> None:
    assert _grade("verified", {}, runs=None).verdict == run_block.NOT_DETERMINED
    assert _grade("at-least 2 of 3", {}, runs=5).verdict == run_block.NOT_DETERMINED


@pytest.mark.parametrize(
    "words", ["", "same", "at-least 6 of 5", "at-least 0 of 5", "at-least x of y"]
)
def test_a_rule_it_does_not_know_is_refused(words: str) -> None:
    rule, problem = run_block.parse_rule(words.split())
    assert rule is None and problem


def test_expect_repeats_records_each_verdict_as_its_outcome(qapp: object) -> None:
    del qapp
    from platterpus.uiscript.runner import ScriptRunner

    runner = ScriptRunner(_Window(Config()))  # type: ignore[arg-type]  # a stand-in
    runner._repeat_runs = {"r": 5}
    runner._accuracies = _five([(_V, "B")] * 5)
    steps = parse(
        "expect-repeats r verified\nexpect-repeats r same-crc\n"
        "expect-repeats q verified\nexpect-repeats r sometimes"
    )
    for step in steps:
        runner._do_expect_repeats(step)
    outcomes = [s.outcome for s in runner._report.steps]
    assert outcomes == [Outcome.PASS, Outcome.PASS, Outcome.ERROR, Outcome.ERROR]
