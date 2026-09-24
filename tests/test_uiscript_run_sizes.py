"""Run sizes: Quick, Standard and Full, cut from one acceptance script.

What has to hold, and why each matters:

* **Nesting is structural.** A section names the smallest size it runs in, so
  Quick is inside Standard is inside Full whatever a script says.
* **A step the size leaves out is DECLINED and recorded**, never dropped, and it is
  the ONLY kind of skip `ok` forgives: any other skip still fails the run.
* **Only Full is evidence**, and the transcript says so at the top of any other.
* **The committed script declares a size at EVERY section**, rather than inheriting
  one (`docs/testing.md` §5.bj), and each size adds something the smaller does not.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from platterpus.uiscript import run_sizes
from platterpus.uiscript.report import Outcome, RunReport, StepRecord, render
from platterpus.uiscript.runner import ScriptRunner
from platterpus.uiscript.script import parse
from platterpus.uiscript.verbs import VERBS

_ACCEPTANCE: Path = (
    Path(__file__).resolve().parents[1]
    / "src/platterpus/rig_scripts/fullacceptance.txt"
)

_SCRIPT: str = "\n".join(
    [
        "log set-up that every size runs",
        "log --- A. quick section ---",
        "run-size quick",
        "log in quick",
        "log --- B. standard section ---",
        "run-size standard",
        "log in standard",
        "log --- C. full section ---",
        "run-size full",
        "log in full",
    ]
)


class _NoWindow:
    """`log` and `run-size` touch no window; a verb that did would fail loudly."""


def _run(script: str, size: str) -> RunReport:
    runner = ScriptRunner(_NoWindow())
    runner.set_run_size(size)
    runner._report = RunReport(
        started_at="t", app_version="test", run_size=runner._run_size
    )
    for step in parse(script):
        runner._execute(step)
    return runner._report


def _by_source(report: RunReport) -> dict[str, StepRecord]:
    return {step.source: step for step in report.steps}


# --- The pure half ----------------------------------------------------------


def test_the_sizes_nest_smallest_first() -> None:
    for chosen in run_sizes.ORDER:
        for declared in run_sizes.ORDER:
            expected = run_sizes.ORDER.index(declared) <= run_sizes.ORDER.index(chosen)
            assert run_sizes.includes(chosen, declared) is expected, (chosen, declared)
    # A step before any declaration is set-up: every size runs it.
    assert all(run_sizes.includes(size, None) for size in run_sizes.ORDER)


def test_only_full_counts_as_evidence() -> None:
    assert [run_sizes.counts_as_evidence(s) for s in run_sizes.ORDER] == [
        False,
        False,
        True,
    ]


def test_the_chooser_lists_every_size_in_order() -> None:
    assert tuple(size for size, _label in run_sizes.CHOICES) == run_sizes.ORDER


def test_the_verb_is_in_the_language() -> None:
    assert "run-size" in VERBS


# --- The runner -------------------------------------------------------------


def test_a_quick_run_declines_the_larger_sections_and_records_them() -> None:
    report = _run(_SCRIPT, "quick")
    steps = _by_source(report)
    assert steps["log set-up that every size runs"].outcome is Outcome.PASS
    assert steps["log in quick"].outcome is Outcome.PASS
    for source in ("log in standard", "log in full"):
        declined = steps[source]
        assert declined.outcome is Outcome.SKIPPED, source
        assert declined.declined_by_size is True
        assert "declined" in declined.detail and "quick run" in declined.detail
    # Section headers still run, so the transcript keeps its boundaries.
    assert steps["log --- C. full section ---"].outcome is Outcome.PASS
    # Declined by the size is not a failure.
    assert report.ok is True


def test_a_standard_run_includes_quick_and_standard() -> None:
    steps = _by_source(_run(_SCRIPT, "standard"))
    assert steps["log in quick"].outcome is Outcome.PASS
    assert steps["log in standard"].outcome is Outcome.PASS
    assert steps["log in full"].outcome is Outcome.SKIPPED


def test_a_full_run_declines_nothing() -> None:
    """The floor: a Full run of the same script runs every step."""
    report = _run(_SCRIPT, "full")
    assert all(step.outcome is Outcome.PASS for step in report.steps)
    assert not any(step.declined_by_size for step in report.steps)


def test_any_OTHER_skip_still_fails_the_run() -> None:
    """Only a step the chosen size declined is forgiven by `ok`.

    An ordinary skip is a decision about the run (an unsafe verb refused, say),
    not about its size, so the run is not ok. Asserted on the report's own rule,
    with the only difference between the two runs being that one flag.
    """

    def report_with(declined_by_size: bool) -> RunReport:
        step = StepRecord(1, "log x", Outcome.SKIPPED, "skipped")
        step.declined_by_size = declined_by_size
        return RunReport(started_at="t", app_version="test", steps=[step])

    assert report_with(declined_by_size=True).ok is True
    assert report_with(declined_by_size=False).ok is False


def test_an_unknown_run_size_is_an_error_against_its_line() -> None:
    report = _run("run-size medium\nlog after", "full")
    assert report.steps[0].outcome is Outcome.ERROR
    assert "not a run size" in report.steps[0].detail


def test_set_run_size_refuses_a_size_it_does_not_know() -> None:
    with pytest.raises(ValueError, match="unknown run size"):
        ScriptRunner(_NoWindow()).set_run_size("medium")


def test_a_smaller_run_says_at_the_top_that_it_is_not_evidence() -> None:
    quick = render(_run(_SCRIPT, "quick"))
    assert "run size: quick" in quick
    assert "NOT evidence toward a version or a handshake close" in quick
    assert "every step this quick run ran passed" in quick
    assert "all checks passed" not in quick
    full = render(_run(_SCRIPT, "full"))
    assert "NOT evidence" not in full
    assert "all checks passed" in full


def test_the_json_says_which_size_ran_and_whether_it_counts() -> None:
    data = _run(_SCRIPT, "standard").as_dict()
    assert data["run_size"] == "standard"
    assert data["counts_as_evidence"] is False
    assert _run(_SCRIPT, "full").as_dict()["counts_as_evidence"] is True


# --- The committed acceptance script ---------------------------------------


def _sections() -> list[tuple[str, list[str]]]:
    """``(letter, command lines)`` for each ``log --- X. … ---`` section."""
    sections: list[tuple[str, list[str]]] = []
    for raw in _ACCEPTANCE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        header = re.match(r"^log --- ([A-Z][0-9]?)\. ", line)
        if header:
            sections.append((header.group(1), []))
        elif sections:
            sections[-1][1].append(line)
    return sections


def _size_of(commands: list[str]) -> str:
    assert commands and commands[0].startswith("run-size "), commands[:1]
    return commands[0].split()[1]


def test_every_section_declares_its_own_size_first() -> None:
    """At the section, never inherited from the one before (§5.bj)."""
    sections = _sections()
    assert len(sections) >= 20, "floor: the script has lost its sections"
    for letter, commands in sections:
        assert commands and commands[0].startswith("run-size "), (
            f"section {letter} does not declare its run size as its first command"
        )
        assert run_sizes.parse_size(_size_of(commands)) is not None, letter


def test_each_size_adds_something_the_smaller_one_does_not() -> None:
    """Non-triviality: three sizes that ran the same sections would be one size."""
    sizes = {_size_of(commands) for _letter, commands in _sections()}
    assert sizes == set(run_sizes.ORDER)


def test_every_size_starts_with_identity_and_ends_on_the_shipped_defaults() -> None:
    """Section A refuses the wrong ripper; section Q leaves the rig as shipped."""
    by_letter = {letter: _size_of(commands) for letter, commands in _sections()}
    assert by_letter["A"] == run_sizes.QUICK
    assert by_letter["Q"] == run_sizes.QUICK


def _commands_in(size: str) -> list[str]:
    return [
        command
        for _letter, commands in _sections()
        if run_sizes.includes(size, _size_of(commands))
        for command in commands
    ]


def test_quick_keeps_its_promise_a_short_rip_its_transcode_and_its_check() -> None:
    quick = _commands_in(run_sizes.QUICK)
    assert "rip" in quick
    assert any(c.startswith("expect-derived-output") for c in quick)
    assert "rig-check" in quick
    assert "select-tracks all" not in quick, "a whole-disc rip is not Quick"


def test_standard_keeps_its_promise_the_whole_disc_rip_overwrite_and_cancel() -> None:
    standard = _commands_in(run_sizes.STANDARD)
    assert "select-tracks all" in standard
    assert "cancel-rip" in standard
    assert any(c.startswith("answer-dialog click=new") for c in standard)
    # The uniform secure re-read (section N) is Full's alone.
    assert "expect-secure-rerip" not in standard


def test_full_runs_every_command_in_the_script() -> None:
    full = _commands_in(run_sizes.FULL)
    everything = [command for _l, commands in _sections() for command in commands]
    assert full == everything
    assert "expect-secure-rerip" in full
