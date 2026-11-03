# SPDX-License-Identifier: GPL-3.0-only
"""The ``(device)`` placeholder in a ``cyanrip`` step: the drive the run selected.

**Why it exists** (the review of the 2026-11-03 Full run, C7). Sections O, P, P2
and P3 of the acceptance script call cyanrip directly and passed no ``-d``, so
cyanrip opened its default drive. On a machine with two drives that need not be
the drive section B set the offset for, nor the one the app's own rips use
(``cyanrip_backend._build_rip_argv`` passes ``-d`` whenever a drive is known,
``docs/dependency-contracts.md``). ``(device)`` expands to the drive picker's
selection when the step runs, and a step with no drive selected is refused
rather than run against whatever cyanrip would pick.

The expanded argv still passes the one sanitiser every scripted cyanrip line
passes (``sanitise_cyanrip_args``, which delegates to
``assert_metadata_lookup_disabled``): the expansion happens before it, so the
device is judged by the same chokepoint as the rest of the line.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QWidget
from test_uiscript_cyanrip_verb import _FakeCapture, _pump, _steps

from platterpus.config import Config
from platterpus.uiscript import runner as runner_mod
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.script import (
    DEVICE_PLACEHOLDER,
    args_as_preflight_sees_them,
    device_problem,
    expand_device,
    sanitise_cyanrip_args,
)

_RIG_SCRIPTS = (
    Path(__file__).resolve().parents[1] / "src" / "platterpus" / "rig_scripts"
)


class _Picker:
    """The one method of `DrivePicker` the placeholder reads."""

    def __init__(self, device: str | None) -> None:
        self._device = device

    def current_device(self) -> str | None:
        return self._device


def _window(rips: Path, device: str | None) -> QWidget:
    widget = QWidget()
    widget._config = Config(output_dir=str(rips))  # type: ignore[attr-defined]  # the window's settings slot
    widget._drive_picker = _Picker(device)  # type: ignore[attr-defined]  # the window's drive picker slot
    return widget


@pytest.fixture
def fake_capture(monkeypatch: pytest.MonkeyPatch) -> _FakeCapture:
    fake = _FakeCapture()
    fake.released.set()
    monkeypatch.setattr("platterpus.adapters.rip_backend.run_capture", fake)
    return fake


def _run(window: QWidget, line: str) -> runner_mod.ScriptRunner:
    run = runner_mod.ScriptRunner(window)
    run.start(_steps(line))
    _pump(run)
    return run


def test_the_selected_drive_reaches_the_argv_as_d(
    qapp: QApplication, tmp_path: Path, fake_capture: _FakeCapture
) -> None:
    del qapp
    run = _run(_window(tmp_path, "/dev/sr1"), "cyanrip -N -d (device) -f")
    assert run._report.steps[0].outcome is Outcome.PASS
    assert fake_capture.calls[0][1:] == ["-N", "-d", "/dev/sr1", "-f"]


def test_no_drive_selected_refuses_the_step_and_runs_nothing(
    qapp: QApplication, tmp_path: Path, fake_capture: _FakeCapture
) -> None:
    """Refused, not guessed: cyanrip's default drive may be the other one."""
    del qapp
    run = _run(_window(tmp_path, None), "cyanrip -N -d (device) -f")
    record = run._report.steps[0]
    assert record.outcome is Outcome.FAIL
    assert "no drive is selected" in record.detail
    assert fake_capture.calls == []


def test_a_device_that_reads_as_a_flag_is_refused(
    qapp: QApplication, tmp_path: Path, fake_capture: _FakeCapture
) -> None:
    del qapp
    run = _run(_window(tmp_path, "-N"), "cyanrip -N -d (device) -f")
    record = run._report.steps[0]
    assert record.outcome is Outcome.FAIL
    assert "not an absolute path" in record.detail
    assert fake_capture.calls == []


def test_a_refused_device_step_leaves_no_result_for_expect_exit(
    qapp: QApplication, tmp_path: Path, fake_capture: _FakeCapture
) -> None:
    """The refusal is an early return; the next `expect-exit` must have no subject."""
    del qapp
    run = _run(_window(tmp_path, None), "cyanrip -N -d (device) -f\nexpect-exit 0")
    assert [s.outcome for s in run._report.steps] == [Outcome.FAIL, Outcome.ERROR]


def test_the_expanded_argv_still_passes_the_chokepoint() -> None:
    """Delegated, not restated: without -N the expanded line is still refused."""
    assert (
        sanitise_cyanrip_args(
            expand_device(["-d", DEVICE_PLACEHOLDER, "-f"], "/dev/sr0")
        )
        is not None
    )
    assert (
        sanitise_cyanrip_args(
            expand_device(["-N", "-d", DEVICE_PLACEHOLDER], "/dev/sr0")
        )
        is None
    )


@pytest.mark.parametrize(
    ("device", "refused"),
    [
        ("/dev/sr0", False),
        ("/dev/cdrom", False),
        ("/dev/disk/by-id/ata-PIONEER_BD-RW_BDR-209D", False),
        ("sr0", True),
        ("-f", True),
        ("/dev/sr 0", True),
        ("", True),
    ],
)
def test_device_problem(device: str, refused: bool) -> None:
    assert bool(device_problem(device)) is refused


def test_the_preflight_view_expands_the_device_so_the_line_is_judged() -> None:
    seen = args_as_preflight_sees_them(["-N", "-d", DEVICE_PLACEHOLDER, "-f"])
    assert seen == ["-N", "-d", "/dev/sr0", "-f"]


def test_sections_o_p_p2_and_p3_pass_the_selected_drive() -> None:
    """Every direct cyanrip call that opens the drive names it (C7).

    Read from the committed script, not from this test's belief about it. A
    probe (`--version`) and a file-only read (`--verify-log`) open no drive.
    """
    text = (_RIG_SCRIPTS / "fullacceptance.txt").read_text(encoding="utf-8")
    drive_lines = [
        line.strip()
        for line in text.splitlines()
        if line.startswith("cyanrip ")
        and "--version" not in line
        and "--verify-log" not in line
    ]
    assert len(drive_lines) >= 5, drive_lines  # O, P, P2 and P3's two arms
    for line in drive_lines:
        assert f"-d {DEVICE_PLACEHOLDER}" in line, line
