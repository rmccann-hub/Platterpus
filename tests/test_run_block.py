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
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.script import parse

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
