"""TASKS R123: the controlled track-3 test, its verbs and its committed script.

Track 3 of the reference disc read wrong whenever it was ripped straight after
track 2 and right when ripped alone. ``rig_scripts/track3abba.txt`` varies one
thing at a time (the fork's round 37 lap 7 S11). This file holds the three
pieces it rests on:

* ``record-accuracy <label> <folder>`` reads the one log a scripted
  ``cyanrip … -D <folder>`` rip wrote this run (``folder_logs``), with its
  FIXUP_ATOM and ``Cache probe:`` line;
* ``compare-conditions`` counts one track's rips per condition on one build
  (``condition_grading``), and refuses what cannot be compared;
* ``cyanrip-timeout`` lifts the 300 s kill bound for a two-track rip;

and the script's own shape: ABBA, ``--cache-probe`` on every rip, one variable
per arm. No audio (Critical rule #8): every log here is text.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from test_uiscript_accuracy_verbs import FRAME_450, MISMATCH, VERIFIED, _log_text

from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.uiscript import condition_grading as cg
from platterpus.uiscript.accuracy_grading import (
    AccuracyRecord,
    TrackAccuracy,
    accuracy_from_log,
)
from platterpus.uiscript.folder_logs import read_one_log
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.script import parse
from platterpus.verdict import AR_STATE_ABSENT, AR_STATE_NO_MATCH, AR_STATE_VERIFIED

pytest.importorskip("PySide6.QtWidgets")
# Every runner here builds a widget, which needs the application first.
pytestmark = pytest.mark.usefixtures("qapp")

RIG_SCRIPTS = Path(__file__).resolve().parents[1] / "src" / "platterpus" / "rig_scripts"
SCRIPT = RIG_SCRIPTS / "track3abba.txt"
BUILD = "platterpus-fork-g3f288fb"
CACHE = "2 to 32 sectors (4.6 to 73.5 KiB, uncached read 362.6 ms)"


def _scripted_log(results: tuple[str, str, str], *, fixups: int, crc: str) -> str:
    """A track-3 log as a `--cache-probe` rip writes it: probe line and counters."""
    text = _log_text(BUILD, results, crc=crc)
    text = text.replace("Tracks to rip:", f"Cache probe:    {CACHE}\nTracks to rip:", 1)
    return text + (
        "  Paranoia status counts:\n"
        "    READ:          9000\n"
        f"    FIXUP_ATOM:    {fixups}\n"
    )


# --- the record: FIXUP_ATOM and the cache probe --------------------------------


def test_a_record_carries_the_fixups_and_the_cache_probe_line() -> None:
    text = _scripted_log(MISMATCH, fixups=18, crc="0BADF00D")
    record = accuracy_from_log("pair1", parse_cyanrip_log(text), "x.log", CACHE)
    (track,) = record.tracks
    assert track.state == AR_STATE_NO_MATCH
    assert track.fixups == 18
    assert record.cache == CACHE
    assert "FIXUP_ATOM 18" in record.describe()
    assert f"cache probe: {CACHE}" in record.describe()


def test_the_cache_probe_value_is_read_verbatim_and_bounded() -> None:
    assert cg.cache_probe_value(f"x\nCache probe:    {CACHE}\n") == CACHE
    assert cg.cache_probe_value("Cache model:    1200 sectors\n") == ""
    long = cg.cache_probe_value("Cache probe: " + "y" * 250)
    assert long.startswith("y" * 200) and "(50 more characters)" in long


# --- the comparison -----------------------------------------------------------


def _rec(
    label: str,
    state: str,
    crc: str,
    *,
    build: str = BUILD,
    tracks: tuple[int, ...] = (3,),
) -> AccuracyRecord:
    return AccuracyRecord(
        label=label,
        build=build,
        tracks=tuple(
            TrackAccuracy(number=n, state=state, crc32=crc, fixups=12) for n in tracks
        ),
        cache=CACHE,
    )


def _abba() -> dict[str, AccuracyRecord]:
    """C's eight rips as the Full runs measured them: wrong after 2, right alone."""
    records: dict[str, AccuracyRecord] = {}
    for n in range(1, 5):
        records[f"pair{n}"] = _rec(
            f"pair{n}", AR_STATE_NO_MATCH, "0BADF00D", tracks=(2, 3)
        )
        records[f"alone{n}"] = _rec(f"alone{n}", AR_STATE_VERIFIED, "59D352DD")
    return records


_ORDER = ["pair1", "alone1", "alone2", "pair2", "pair3", "alone3", "alone4", "pair4"]


def test_the_tally_is_per_condition_over_different_track_sets() -> None:
    verdict = cg.compare_conditions(3, _ORDER, _abba())
    assert verdict.determined, verdict.refusal
    assert "track 3, pair: right in 0 of 4 rip(s) (pair1, pair2, pair3, pair4)" in (
        verdict.detail
    )
    assert "track 3, alone: right in 4 of 4 rip(s)" in verdict.detail
    assert "59D352DD x4" in verdict.detail and "0BADF00D x4" in verdict.detail
    assert "FIXUP_ATOM 12" in verdict.detail and CACHE in verdict.detail
    assert "more than one condition: none" in verdict.detail


@pytest.mark.parametrize(
    ("change", "why"),
    [
        ("build", "builds"),
        ("track", "did not rip track 3"),
        ("one-condition", "one condition"),
        ("unanswered", "gave no answer"),
        ("absent", "no accuracy has been recorded"),
        ("repeated", "more than once"),
        ("unnamed", "names no build"),
    ],
)
def test_what_cannot_be_compared_is_not_determined(change: str, why: str) -> None:
    records = _abba()
    labels = list(_ORDER)
    if change == "build":
        records["alone2"] = _rec("alone2", AR_STATE_VERIFIED, "X", build="other")
    elif change == "track":
        records["alone2"] = _rec("alone2", AR_STATE_VERIFIED, "X", tracks=(4,))
    elif change == "one-condition":
        labels = ["pair1", "pair2"]
    elif change == "unanswered":
        records["alone2"] = _rec("alone2", AR_STATE_ABSENT, "X")
    elif change == "absent":
        labels.append("pair9")
    elif change == "repeated":
        labels.append("pair1")
    elif change == "unnamed":
        records["alone2"] = _rec("alone2", AR_STATE_VERIFIED, "X", build="")
    verdict = cg.compare_conditions(3, labels, records)
    assert not verdict.determined
    assert why in verdict.refusal, verdict.refusal


@pytest.mark.parametrize(
    ("label", "condition"),
    [("pair1", "pair"), ("alone12", "alone"), ("pairnofix2", "pairnofix"), ("7", "7")],
)
def test_the_condition_is_the_label_without_its_trailing_digits(
    label: str, condition: str
) -> None:
    assert cg.condition_of(label) == condition


@pytest.mark.parametrize(
    ("text", "ok"),
    [
        ("3", True),
        ("99", True),
        ("0", False),
        ("100", False),
        ("x", False),
        ("-1", False),
    ],
)
def test_the_track_argument_is_validated(text: str, ok: bool) -> None:
    number, problem = cg.track_problem(text)
    assert (number is not None) is ok and bool(problem) is not ok


@given(
    labels=st.lists(st.text(max_size=6), max_size=6),
    number=st.integers(min_value=-5, max_value=120),
)
def test_the_comparison_never_raises(labels: list[str], number: int) -> None:
    assert cg.compare_conditions(number, labels, _abba()).detail is not None


# --- the folder reader ----------------------------------------------------------


def _write(root: Path, folder: str, text: str, name: str = "disc.log") -> Path:
    path = root / folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_the_folder_reader_takes_exactly_one_log_from_this_run(tmp_path: Path) -> None:
    text = _scripted_log(VERIFIED, fixups=2, crc="59D352DD")
    old = _write(tmp_path, "t3alone1", text, "old.log")
    os.utime(old, (1_000_000.0, 1_000_000.0))
    assert (
        "holds 0 cyanrip log(s)"
        in read_one_log(tmp_path, "t3alone1", since=2_000_000.0).problem
    )
    _write(tmp_path, "t3alone1", text)
    found = read_one_log(tmp_path, "t3alone1", since=2_000_000.0)
    assert not found.problem and found.path is not None and "Cache probe:" in found.text
    _write(tmp_path, "t3alone1", text, "two.log")
    assert (
        "holds 2 cyanrip log(s)"
        in read_one_log(tmp_path, "t3alone1", since=2_000_000.0).problem
    )


# --- the verbs, through a real runner -----------------------------------------


def _runner(tmp_path: Path) -> Any:
    from test_uiscript_rip_verbs import _window

    from platterpus.config import Config
    from platterpus.uiscript.runner import ScriptRunner

    return ScriptRunner(_window(config=Config(output_dir=str(tmp_path))))


def _dated_ahead(root: Path) -> None:
    ahead = time.time() + 60.0
    for path in root.rglob("*"):
        if path.is_file():
            os.utime(path, (ahead, ahead))


def test_record_accuracy_reads_a_scripted_rips_folder_then_compares(
    tmp_path: Path, qapp: Any, process_until: Any
) -> None:
    from test_uiscript_rip_verbs import _step_outcome

    _write(tmp_path, "t3pair1", _scripted_log(FRAME_450, fixups=20, crc="0BADF00D"))
    _write(tmp_path, "t3alone1", _scripted_log(VERIFIED, fixups=3, crc="59D352DD"))
    _dated_ahead(tmp_path)
    runner = _runner(tmp_path)
    source = (
        "record-accuracy pair1 t3pair1\n"
        "record-accuracy alone1 t3alone1\n"
        "compare-conditions 3 pair1 alone1"
    )
    step = _step_outcome(runner, qapp, process_until, source)
    steps = runner._report.steps
    assert [s.outcome for s in steps] == [Outcome.INFO] * 3, [s.detail for s in steps]
    assert "FIXUP_ATOM 20" in steps[0].detail and CACHE in steps[0].detail
    assert "track 3, pair: right in 0 of 1 rip(s)" in step.detail
    assert "track 3, alone: right in 1 of 1 rip(s)" in step.detail


def test_record_accuracy_of_an_empty_folder_is_not_determined(
    tmp_path: Path, qapp: Any, process_until: Any
) -> None:
    from test_uiscript_rip_verbs import _step_outcome

    (tmp_path / "t3pair1").mkdir()
    runner = _runner(tmp_path)
    step = _step_outcome(runner, qapp, process_until, "record-accuracy pair1 t3pair1")
    assert step.outcome is Outcome.ERROR and "not determined" in step.detail
    assert "pair1" not in runner._accuracies


def test_a_folder_that_could_leave_the_rips_folder_is_refused(
    tmp_path: Path, qapp: Any, process_until: Any
) -> None:
    from test_uiscript_rip_verbs import _step_outcome

    step = _step_outcome(
        _runner(tmp_path), qapp, process_until, "record-accuracy pair1 ../x"
    )
    assert step.outcome is Outcome.ERROR and "plain folder name" in step.detail


def test_cyanrip_timeout_reaches_the_ripper_call_and_resets_next_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_uiscript_cyanrip_verb import _pump, _window_with_rips_folder

    from platterpus.uiscript import runner as runner_mod

    timeouts: list[float] = []

    def capture(*_a: object, timeout: float, **_k: object) -> tuple[int, str]:
        timeouts.append(timeout)
        return 0, "cyanrip 0.9.4\n"

    monkeypatch.setattr("platterpus.adapters.rip_backend.run_capture", capture)
    run = runner_mod.ScriptRunner(_window_with_rips_folder(str(tmp_path)))
    run.start(parse("cyanrip-timeout 1800\ncyanrip -N --version"))
    _pump(run)
    assert run._report.steps[0].outcome is Outcome.INFO
    assert timeouts == [1800.0]
    run.start(parse("cyanrip -N --version"))
    _pump(run)
    assert timeouts == [1800.0, runner_mod.CYANRIP_VERB_TIMEOUT_S], (
        "a new run must start on the default bound"
    )


@pytest.mark.parametrize(
    ("arg", "outcome", "said"),
    [
        ("0", Outcome.ERROR, "not a number of seconds"),
        ("abc", Outcome.ERROR, "not a number of seconds"),
        ("99999", Outcome.INFO, "CLAMPED"),
    ],
)
def test_cyanrip_timeout_refuses_or_clamps_at_the_boundary(
    tmp_path: Path, arg: str, outcome: Outcome, said: str
) -> None:
    from test_uiscript_cyanrip_verb import _pump, _window_with_rips_folder

    from platterpus.uiscript import runner as runner_mod

    run = runner_mod.ScriptRunner(_window_with_rips_folder(str(tmp_path)))
    run.start(parse(f"cyanrip-timeout {arg}"))
    _pump(run)
    step = run._report.steps[0]
    assert step.outcome is outcome and said in step.detail
    assert run._cyanrip_timeout_s <= runner_mod.MAX_RIP_WAIT_S


# --- the committed script ---------------------------------------------------------


def _steps() -> list[Any]:
    steps = [s for s in parse(SCRIPT.read_text(encoding="utf-8")) if s.verb]
    assert all(s.ok for s in steps), [s.error for s in steps if not s.ok]
    return steps


def _rips() -> list[tuple[str, tuple[str, ...]]]:
    """``(label, cyanrip args)`` for each rip, from the record that follows it."""
    steps = _steps()
    out: list[tuple[str, tuple[str, ...]]] = []
    for index, step in enumerate(steps):
        if step.verb == "cyanrip" and "-l" in step.args:
            follow = steps[index + 1 : index + 3]
            assert [s.verb for s in follow] == ["expect-exit", "record-accuracy"]
            assert follow[0].args == ("0",)
            label, folder = follow[1].args
            assert step.args[step.args.index("-D") + 1] == folder == f"t3{label}"
            out.append((label, step.args))
    return out


def test_the_selection_section_is_abba_four_of_each() -> None:
    rips = _rips()
    assert len(rips) == 12
    selection = [label for label, _ in rips[:8]]
    assert selection == _ORDER
    for label, args in rips[:8]:
        want = "2,3" if label.startswith("pair") else "3"
        assert args[args.index("-l") + 1] == want, label
    assert f"compare-conditions 3 {' '.join(_ORDER)}" in [s.source for s in _steps()]


def test_every_rip_probes_the_cache_and_each_arm_changes_one_thing() -> None:
    rips = _rips()
    base = {label: args for label, args in rips}
    reference = list(base["pair1"])
    for label, args in rips:
        assert "--cache-probe" in args, label
        assert "-Z" not in args and "-O" not in args, label
        extra = [a for a in args if a not in reference]
        if label.startswith("pairslow"):
            assert args[args.index("-S") + 1] == "4" and "-P" not in args
        elif label.startswith("pairnofix"):
            assert args[args.index("-P") + 1] == "0" and "-S" not in args
        else:
            assert "-S" not in args and "-P" not in args, label
        # Beyond its folder and track list, an arm adds only its one flag.
        assert len([a for a in extra if not a.startswith("t3") and a != "3"]) <= 2, (
            label,
            extra,
        )


def test_the_bound_is_lifted_before_the_first_rip_and_the_header_says_how_long() -> (
    None
):
    steps = _steps()
    verbs = [s.verb for s in steps]
    assert verbs.index("cyanrip-timeout") < next(
        i for i, s in enumerate(steps) if s.verb == "cyanrip" and "-l" in s.args
    )
    text = SCRIPT.read_text(encoding="utf-8")
    header = text.split("log ====", 1)[0]
    assert "about 25 to 40 minutes" in header
    for step_no in ("1.", "2.", "3."):
        assert f"  {step_no} " in header
    assert "round 37 lap 7 S11" in header
    # Every folder name crosses machines: ASCII letters and digits only.
    for _, args in _rips():
        folder = args[args.index("-D") + 1]
        assert folder.isascii() and folder.isalnum(), folder
