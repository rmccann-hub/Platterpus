"""The acceptance run's overall estimate (TASKS D6, "The acceptance run's overall
estimate").

**Held against the filed runs, not against numbers typed here.** The committed
2026-10-05 and 2026-09-30 Full runs carry their script, every step's time and the
whole-disc rip's sector spans (``docs/handshake/artifactsround30/``). The
estimate of each run's own script, from those track lengths and the rig's
measured speed, must contain what the run actually took; the per-section table
is re-derived from the 2026-10-05 report.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from test_uiscript_rip_verbs import _run_one, _window

from platterpus import rip_estimate
from platterpus.config import Config
from platterpus.uiscript import run_estimate as est
from platterpus.uiscript.report import Outcome, render
from platterpus.uiscript.runner import _STRUCTURAL_VERBS, MAX_WAIT_S, TICK_MS
from platterpus.uiscript.script import parse

_REPO = Path(__file__).resolve().parent.parent
_FILED = _REPO / "docs/handshake/artifactsround30"
_ACCEPTANCE = _REPO / "src/platterpus/rig_scripts/fullacceptance.txt"
_RIG = rip_estimate.seed_for("PIONEER BD-RW BDR-209D")
_TICK = TICK_MS / 1000


def _load(name: str) -> dict[str, Any]:
    loaded = json.loads((_FILED / name).read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _lengths(report: dict[str, Any]) -> dict[int, float]:
    """Track seconds from a filed rip report's sector spans (75 sectors a second)."""
    return {
        t["number"]: (t["end_sector"] - t["start_sector"] + 1) / 75
        for t in report["tracks"]
    }


def _estimate(source: str, size: str = "full", **kw: Any) -> est.RunEstimate:
    args: dict[str, Any] = {
        "run_size": size,
        "config": Config(),
        "track_lengths": {n: 240.0 for n in range(1, 15)},
        "rate": _RIG,
        "tick_s": _TICK,
        "wait_cap_s": MAX_WAIT_S,
    }
    args.update(kw)
    return est.estimate_run(parse(source), **args)


def test_the_measured_table_is_the_filed_runs() -> None:
    """Re-derived from the committed report: each section's steps other than
    `rip`, `wait-for-rip` and `wait`, in whole seconds."""
    report = _load("round30oct05fullscriptreport.json")
    assert est.MEASURED_FROM.endswith("round30oct05fullscriptreport.json")
    derived: dict[str, float] = {}
    section = ""
    for step in report["steps"]:
        source = step["source"].strip()
        if source.startswith("log --- "):
            section = source[len("log --- ") :].split(".", 1)[0]
        derived.setdefault(section, 0.0)
        if source.split(maxsplit=1)[0] in {"rip", "wait-for-rip", "wait"}:
            continue
        derived[section] += step["elapsed_s"]
    assert len(derived) >= 20, "floor: the report's sections were not read"
    assert {k: float(round(v)) for k, v in derived.items()} == est.MEASURED_OTHER_S


@pytest.mark.parametrize(
    ("script_report", "disc_report"),
    [
        ("round30oct05fullscriptreport.json", "round30oct05fullwholediscreport.json"),
        ("round30fullscriptreport.json", "round30fullwholediscreport.json"),
    ],
)
def test_each_filed_full_run_took_what_its_own_script_was_estimated_at(
    script_report: str, disc_report: str
) -> None:
    """The estimate of the filed run's OWN script, at the rig's speed, contains
    the wall time the run took (every step's time plus the runner's pause between
    steps), and its main figure is within 10 % of it."""
    report = _load(script_report)
    assert report["run_size"] == "full" and not report["ended_reason"]
    actual = sum(s["elapsed_s"] for s in report["steps"]) + _TICK * len(report["steps"])
    figure = _estimate(
        report["script_source"], track_lengths=_lengths(_load(disc_report))
    )
    assert figure.rips == figure.rips_estimated == 8
    assert figure.low_s <= actual * 1.1 and figure.low_s >= actual * 0.9, (
        figure.low_s,
        actual,
    )
    assert actual <= figure.high_s, (actual, figure.high_s)


def test_a_rip_with_no_track_lengths_is_unknown_not_zero() -> None:
    source = "run-size quick\nselect-tracks 1-2\nrip\nwait-for-rip 600\nwait 5"
    figure = _estimate(source, track_lengths={})
    assert figure.rips == 1 and figure.rips_estimated == 0
    text = est.describe(figure)
    assert "no total yet" in text and "not identified" in text
    assert "about" not in text.split(":", 1)[1].split(".")[0], text


def test_a_drive_with_no_measured_speed_is_unknown_not_zero() -> None:
    figure = _estimate("select-tracks 1\nrip", rate=None)
    assert figure.rips_estimated == 0
    assert "reading speed is not known" in est.describe(figure)


def test_a_section_no_filed_run_had_makes_the_figure_a_floor_and_is_named() -> None:
    source = (
        "log --- Z9. a section nobody measured ---\nrun-size quick\nexpect-tracks 2+"
    )
    figure = _estimate(source)
    assert figure.unmeasured == ("Z9",) and not figure.complete
    text = est.describe(figure)
    assert "at least" in text and "Z9" in text and "floor" in text


def test_a_smaller_run_counts_only_the_rips_it_runs_and_their_settings() -> None:
    """A declined section does nothing, its `set` lines included, as in the runner."""
    source = "\n".join(
        [
            "log --- A. quick ---",
            "run-size quick",
            "select-tracks 1",
            "rip",
            "log --- B. full only ---",
            "run-size full",
            "set secure_rerip_dynamic off",
            "select-tracks all",
            "rip",
            "log --- C. quick again ---",
            "run-size quick",
            "select-tracks 1",
            "rip",
        ]
    )
    quick = _estimate(source, size="quick")
    full = _estimate(source, size="full")
    assert (quick.rips, full.rips) == (2, 3)
    # In the quick run B's `set` never ran, so C's rip is dynamic: no uniform
    # re-reads in its low figure, unlike the full run's C.
    assert quick.rips_low_s < full.rips_low_s


def test_waits_come_from_the_script_and_are_capped_as_the_runner_caps_them() -> None:
    figure = _estimate("wait 90\nwait 100000")
    assert figure.waits_s == 90 + MAX_WAIT_S


def test_the_high_bound_in_dynamic_mode_re_reads_every_track_at_the_ceiling() -> None:
    """Dynamic mode cannot know which tracks AccurateRip will not confirm, so the
    bound assumes all of them, each re-read at the retry ceiling (`rip_estimate`'s
    per-track cost, applied to the whole selection)."""
    figure = _estimate("select-tracks 1\nrip", track_lengths={1: 240.0})
    single = rip_estimate.estimate_rip(
        240.0, _RIG, secure_rerip_matches=2, dynamic=True, max_retries=5
    )
    assert single is not None and single.reread_high is not None
    assert figure.rips_low_s == pytest.approx(single.seconds)
    assert figure.rips_high_s == pytest.approx(
        single.seconds + single.reread_high * 240
    )
    assert figure.rips_high_s > figure.rips_low_s


def test_the_structural_verbs_are_the_runners() -> None:
    assert est.STRUCTURAL_VERBS == _STRUCTURAL_VERBS


def test_the_shipped_script_is_estimated_after_the_disc_is_identified() -> None:
    lines = [ln.strip() for ln in _ACCEPTANCE.read_text(encoding="utf-8").splitlines()]
    at = lines.index("run-estimate")
    assert lines.index("expect-identified") < at < lines.index("rip")


# --- The runner and the verb ------------------------------------------------------


class _Track:
    def __init__(self, number: int, length_ms: int | None) -> None:
        self.number = number
        self.length_ms = length_ms


class _Table:
    def __init__(self, tracks: list[_Track]) -> None:
        self._tracks = tracks

    def tracks(self) -> list[_Track]:
        return list(self._tracks)


def test_a_run_states_its_estimate_before_step_one_in_the_record(
    qapp: Any, process_until: Any
) -> None:
    from platterpus.uiscript.runner import ScriptRunner

    win = _window(track_table=_Table([_Track(1, 200_000), _Track(2, 180_000)]))
    win._read_rate_for_current_drive = lambda: _RIG
    runner = ScriptRunner(win)
    finished: list[Any] = []
    runner.finished.connect(finished.append)
    runner.start(parse("select-tracks 1-2\nwait 0.1"), source="x")
    assert runner.estimate.startswith("Run estimate (full): about"), runner.estimate
    assert process_until(lambda: bool(finished))
    report = finished[0]
    assert report.as_dict()["estimate"] == runner.estimate
    assert runner.estimate in render(report)


def test_run_estimate_records_the_rest_of_the_run_as_info(qapp: Any) -> None:
    win = _window(track_table=_Table([_Track(1, None)]))  # a placeholder row
    win._read_rate_for_current_drive = lambda: _RIG
    record, _runner = _run_one(win, "run-estimate")
    assert record.outcome is Outcome.INFO
    assert record.detail.startswith("for the rest of this run: Run estimate")


def test_the_window_reader_never_raises(qapp: Any) -> None:
    from platterpus.uiscript.estimate_verbs import estimate_for_window

    win = _window()

    def broken() -> object:
        raise RuntimeError("no profile store")

    win._read_rate_for_current_drive = broken
    text = estimate_for_window(
        win, parse("rip"), run_size="full", tick_s=_TICK, wait_cap_s=MAX_WAIT_S
    )
    assert text.startswith("Run estimate: none") and "no profile store" in text
