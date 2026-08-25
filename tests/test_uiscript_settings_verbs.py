"""The two script capabilities the acceptance suite needed and did not have.

**`expect-refused`.** `CLAUDE.md` makes input validation institutional — every
value entering from outside the code is validated at its boundary, the pure
validator is the source of truth, and *"a GUI widget's own constraint is a
convenience, not the validation"*. None of it was reachable from a script: `set`
records FAIL when the validator refuses, which is the right report for an
accidental bad value and the wrong one for a deliberate probe, so a script could
not tell *"the guard fired"* from *"the run broke"*. The acceptance suite
therefore exercised **none** of the validation subsystem.

**`set rip_goal`.** A goal is not a setting; it is a name for a set of them. In
Settings, choosing one calls `apply_preset`. Writing the field alone produced a
config no dialog could ever create — `rip_goal="archival"` beside fast-verified
values — which `detect_goal` then reports as `custom`. A script could "select the
archival goal" and rip with exactly the settings it was avoiding.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from platterpus.config import Config
from platterpus.goal_presets import GOAL_ARCHIVAL, GOAL_FAST, detect_goal
from platterpus.uiscript import runner as runner_mod
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.script import parse


@pytest.fixture
def window(qapp: QApplication) -> QWidget:
    """A bare top-level carrying a config, which is all these verbs touch."""
    del qapp
    widget = QWidget()
    widget._config = Config()  # type: ignore[attr-defined]
    return widget


def _steps(text: str) -> list[Any]:
    parsed = parse(text)
    assert all(step.ok for step in parsed), [s.error for s in parsed]
    return parsed


def _run(window: QWidget, text: str) -> list[Any]:
    run = runner_mod.ScriptRunner(window)
    run.start(_steps(text))
    deadline = time.monotonic() + 5.0
    while run.running and time.monotonic() < deadline:
        run._tick()
        time.sleep(0.005)
    assert not run.running, "the runner never finished"
    return list(run._report.steps)


# --- expect-refused ----------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("read_offset", "99999"),  # OFFSET_MAX is 5000
        ("read_offset", "-99999"),
        ("max_retries", "101"),  # MAX_RETRIES_MAX is 100
        ("secure_rerip_matches", "11"),  # SECURE_REREP_MAX is 10
        ("mp3_vbr_quality", "10"),  # MP3_QUALITY_MAX is 9
    ],
)
def test_a_value_outside_the_validated_range_is_refused(
    window: QWidget, field: str, bad: str
) -> None:
    """Each of these reaches cyanrip's argv, which is why the range is enforced.

    Parametrised over the numeric settings the validator bounds rather than one
    example, because a range check that holds for one field says nothing about
    the next — and `read_offset` in particular *"rips the next disc wrong with a
    clean-looking log"* when nudged.
    """
    before = getattr(window._config, field)  # type: ignore[attr-defined]
    steps = _run(window, f"expect-refused {field} {bad}")
    assert len(steps) == 1
    assert steps[0].outcome is Outcome.PASS, steps[0].detail
    assert getattr(window._config, field) == before  # type: ignore[attr-defined]


def test_a_value_inside_the_range_makes_expect_refused_FAIL(window: QWidget) -> None:
    """**The floor, and without it the verb passes on everything.**

    A verb whose pass condition is "something went wrong" is trivially satisfiable
    if it never checks that the something was the *right* thing. 667 is a legal
    read offset — this rig's real one — so asserting it is refused must fail.
    """
    steps = _run(window, "expect-refused read_offset 667")
    assert steps[0].outcome is Outcome.FAIL, steps[0].detail
    assert "ACCEPTED" in steps[0].detail


def test_a_refusal_that_wrote_the_value_anyway_is_a_FAILURE(
    window: QWidget, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both halves, because only the pair is a check.

    A guard that reports a refusal and stores the value is worse than no guard:
    the log says the input was rejected while the setting still reaches the rip.
    Simulated by making the validator refuse while something else moves the field,
    which is the only way to reach a branch the real code does not currently take
    — the point is that the assertion would *catch* it if it ever did.
    """
    import dataclasses

    from platterpus.uiscript import runner as mod

    def refuse_and_write(*_a: object, **_k: object) -> str:
        # The stub IS the defect: it reports a refusal and stores the value, which
        # is the exact pair the verb has to be able to tell apart. Reaching the
        # branch requires the write to land BETWEEN the handler reading `before`
        # and reading it back — a `before`-time edit is a different scenario and
        # passes, which is how the first version of this test was vacuous.
        window._config = dataclasses.replace(  # type: ignore[attr-defined]
            window._config,  # type: ignore[attr-defined]
            read_offset=4999,
        )
        return "nope"

    monkeypatch.setattr(mod, "_validation_error_for", refuse_and_write)

    steps = _run(window, "expect-refused read_offset 4999")
    assert steps[0].outcome is Outcome.FAIL, steps[0].detail
    assert "CHANGED" in steps[0].detail
    assert window._config.read_offset == 4999, (  # type: ignore[attr-defined]
        "the stub did not actually write the value, so this test would pass "
        "against a verb that never checks the second half"
    )


def test_an_unknown_setting_is_an_error_not_a_pass(window: QWidget) -> None:
    """A typo must not read as "the validator refused it", which would be a pass
    for a field that does not exist — the "satisfied by the wrong thing" shape in
    the verb whose whole job is asserting a refusal."""
    steps = _run(window, "expect-refused not_a_setting 1")
    assert steps[0].outcome is Outcome.ERROR, steps[0].detail
    assert "no setting called" in steps[0].detail


# --- set rip_goal applies the preset -----------------------------------------


def test_setting_the_goal_applies_the_whole_preset(window: QWidget) -> None:
    """Selecting a goal in a script must mean what selecting it in Settings means.

    Archival differs from fast-verified by EFFORT: uniform secure re-read
    (`secure_rerip_dynamic=False`) and offset-variant matches re-read. Writing
    only `rip_goal` left both at the fast-verified values under an archival label.
    """
    assert window._config.secure_rerip_dynamic is True  # type: ignore[attr-defined]
    steps = _run(window, f"set rip_goal {GOAL_ARCHIVAL}")
    assert steps[0].outcome is Outcome.PASS, steps[0].detail
    config = window._config  # type: ignore[attr-defined]
    assert config.rip_goal == GOAL_ARCHIVAL
    assert config.secure_rerip_dynamic is False, (
        "the goal was written but its preset was not applied — the label and the "
        "settings disagree, which is the config no dialog can produce"
    )
    assert config.rerip_offset_variant is True


def test_the_goal_round_trips_through_the_real_detector(window: QWidget) -> None:
    """`detect_goal` must agree, since that is what the dialog's combo renders.

    Asserted through the detector rather than field by field: it is the function
    that decides whether the GUI shows the goal or "Custom", so agreement with it
    is the property, and it cannot be satisfied by copying a preset's fields into
    the test.
    """
    _run(window, f"set rip_goal {GOAL_ARCHIVAL}")
    assert detect_goal(window._config) == GOAL_ARCHIVAL  # type: ignore[attr-defined]
    _run(window, f"set rip_goal {GOAL_FAST}")
    assert detect_goal(window._config) == GOAL_FAST  # type: ignore[attr-defined]


def test_setting_an_ordinary_field_still_writes_only_that_field(
    window: QWidget,
) -> None:
    """The preset hook must not leak into every `set`.

    The narrow scoping is the point: `rip_goal` is the one field that names a
    group, and a `set` of anything else changing a second setting would be a far
    worse surprise than the bug this fixes.
    """
    before = window._config  # type: ignore[attr-defined]
    _run(window, "set max_retries 7")
    after = window._config  # type: ignore[attr-defined]
    changed = {
        name
        for name in vars(before)
        if getattr(before, name) != getattr(after, name, None)
    }
    assert changed == {"max_retries"}, changed


# --- The 2026-08-24 rig run: a bound too generous became no bound -------------


def test_an_over_cap_rip_wait_WAITS_THE_CAP_instead_of_skipping(
    window: QWidget, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**The regression test for the defect that destroyed a night's disc pass.**

    `wait-for-rip 21600` against a 3-hour cap used to record FAIL and return
    *immediately*, so no wait happened at all. The next step then graded a rip
    that had started 0.4 s earlier, a cache probe opened the same drive 1.2 s
    later, and the unattended-quit helper declared the batch finished and killed
    the reader at 1.48% of track 1.

    Asserted as the PROPERTY — a deadline is armed for the cap — rather than as
    "the step did not fail", because the step may still legitimately report the
    clamp. What must never happen again is *not waiting*.
    """
    window._rip_worker = object()  # type: ignore[attr-defined]
    run = runner_mod.ScriptRunner(window)
    run.start(_steps("wait-for-rip 21600"))
    run._tick()
    assert run._deadline is not None, (
        "no deadline was armed — the over-cap request was refused rather than "
        "clamped, which is the defect: the script carries on against a live rip"
    )
    armed_for = run._deadline - run._deadline_started
    assert armed_for == pytest.approx(runner_mod.MAX_RIP_WAIT_S, abs=1.0), armed_for
    assert "CLAMPED" in run._deadline_detail, run._deadline_detail
    run.stop("test over")


def test_an_over_cap_plain_wait_also_waits_the_cap(window: QWidget) -> None:
    """Same defect, same file, one verb over. A `wait` exists to let something
    settle; skipping it entirely makes the next step measure the wrong moment."""
    run = runner_mod.ScriptRunner(window)
    run.start(_steps("wait 99999"))
    run._tick()
    assert run._deadline is not None, "the over-cap wait was refused, not clamped"
    armed_for = run._deadline - run._deadline_started
    assert armed_for == pytest.approx(runner_mod.MAX_WAIT_S, abs=1.0), armed_for
    assert "CLAMPED" in run._deadline_detail, run._deadline_detail
    run.stop("test over")


def test_a_wait_within_the_cap_is_not_labelled_clamped(window: QWidget) -> None:
    """The floor. Without it, a verb that clamped *everything* would pass above."""
    run = runner_mod.ScriptRunner(window)
    run.start(_steps("wait 1"))
    run._tick()
    assert "CLAMPED" not in run._deadline_detail, run._deadline_detail
    run.stop("test over")


def test_the_ripper_verb_refuses_to_open_the_drive_during_a_rip(
    window: QWidget,
) -> None:
    """Two ripper processes on one drive, measured 1.2 s apart on the rig.

    A cache probe is the worst thing to do to a drive mid-read — defeating the
    readback cache is its entire purpose. The guard lives on the verb that knows
    it touches the drive rather than only in the wait, because two independent
    defects had to line up to produce it and neither ordering assumption held.
    """
    window._rip_worker = object()  # type: ignore[attr-defined]
    steps = _run(window, "cyanrip -N -x -I")
    assert steps[0].outcome is Outcome.FAIL, steps[0].detail
    assert "READING THE DISC" in steps[0].detail, steps[0].detail


def test_a_version_probe_is_still_allowed_during_a_rip(window: QWidget) -> None:
    """**The floor, and it is not hypothetical.**

    Section A of the acceptance script runs `cyanrip --version` deliberately. A
    guard that refused every invocation would break the identity check the whole
    run is attributable through — so the exemption is asserted, not assumed.
    Probe flags print and exit without opening the device.
    """
    window._rip_worker = object()  # type: ignore[attr-defined]
    steps = _run(window, "cyanrip --version")
    detail = steps[0].detail
    assert "READING THE DISC" not in detail, (
        f"a --version probe was refused during a rip: {detail}"
    )
