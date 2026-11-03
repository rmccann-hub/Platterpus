# SPDX-License-Identifier: GPL-3.0-only
"""``expect-deemphasis-pair``: section P3 decides round 16's clause 2.

**Why this exists** (the review of the 2026-11-03 Full run, C5). P3 rips one
track twice, de-emphasis forced (``-H -E``) and disabled (``-H -W``), and its
comment said nothing in the script language could decide the clause, so the two
arms were captured and nobody graded them. Since the fork's ``.20`` the loudness
cyanrip prints is measured on the delivered audio, after the filter, while its
checksums stay on the read. The run printed ``B0D122E7`` for both arms and
-20.7 against -19.9 LUFS: the filter acted on audio both arms read alike. The
verb grades exactly that, and is tri-state where a value is missing.

The logs below are synthetic, in the shape of the run's two logs (no evidence
file is read: `tests/test_no_new_evidence_readers.py`).
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus.config import Config
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.uiscript import deemphasis_grading as grading
from platterpus.uiscript import deemphasis_verbs
from platterpus.uiscript.report import Outcome

_RIG_SCRIPTS = (
    Path(__file__).resolve().parents[1] / "src" / "platterpus" / "rig_scripts"
)

#: `.28`, a release from `.20` on (measures the delivered audio).
_BUILD_28 = "platterpus-fork-g3f288fb"
#: `.19`, the last release that measured before the filter.
_BUILD_19 = "platterpus-fork-g174a134"


def _log(
    *,
    folder: str = "r16deemphon",
    build: str = _BUILD_28,
    crc: str = "B0D122E7",
    lufs: str | None = "-20.7",
) -> str:
    """A one-track cyanrip log in the shape the Full run's P3 arms wrote."""
    loudness = (
        f"\nAlbum integrated loudness (R128): {lufs} LUFS\n"
        if lufs is not None
        else "\n"
    )
    return (
        f"cyanrip 0.9.4-rc3+platterpus.28 ({build})\n"
        f"Invoked as:     /usr/local/bin/cyanrip -N -s 667 -l 1 -H -E -D {folder}\n"
        "Offset:         +667 samples\n"
        "Disc tracks:    14\n"
        "Tracks to rip:  1\n\n"
        "Tracks:\n"
        "Track 1 read with no error reported.\n"
        "Summary:\n\n"
        f"  EAC CRC32:     {crc}\n\n"
        "  File(s):\n"
        f"    {folder}/01 - Unknown track.flac\n"
        f"{loudness}"
        "Tracks ripped accurately: 1/14\n\n"
        "Ripping errors: 0\n"
        "Rip completed:  yes (1 of 14 tracks)\n"
    )


def _arm(name: str = "r16deemphon", **kwargs: Any) -> grading.Arm:
    return grading.arm_from_log(
        name, f"{name}/x.log", parse_cyanrip_log(_log(**kwargs))
    )


# --- The pure grade -----------------------------------------------------------


def test_the_2026_11_03_pair_passes() -> None:
    verdict = grading.grade_pair(_arm(lufs="-20.7"), _arm("r16deemphoff", lufs="-19.9"))
    assert verdict.state == grading.PASS, verdict.detail
    assert "-0.8 LU" in verdict.detail
    assert "S12 (d)" in verdict.detail, "the answer says what the grade rests on"


def test_equal_loudness_is_the_cascade_defects_signature() -> None:
    """The defect P3 probes: the filter never reached, so nothing moved."""
    verdict = grading.grade_pair(_arm(), _arm("r16deemphoff"))
    assert verdict.state == grading.FAIL
    assert "changed nothing measurable" in verdict.detail


def test_a_difference_below_the_floor_fails() -> None:
    verdict = grading.grade_pair(_arm(lufs="-20.1"), _arm("r16deemphoff", lufs="-19.9"))
    assert verdict.state == grading.FAIL


def test_a_difference_at_the_floor_passes_despite_float_arithmetic() -> None:
    """-19.9 - -20.2 is 0.2999… in binary; the log prints tenths, so it is 0.3."""
    verdict = grading.grade_pair(_arm(lufs="-20.2"), _arm("r16deemphoff", lufs="-19.9"))
    assert verdict.state == grading.PASS, verdict.detail


def test_arms_that_read_different_audio_fail() -> None:
    verdict = grading.grade_pair(
        _arm(lufs="-20.7"), _arm("r16deemphoff", crc="DEADBEEF", lufs="-19.9")
    )
    assert verdict.state == grading.FAIL
    assert "READ different audio" in verdict.detail


@pytest.mark.parametrize(
    ("forced", "disabled", "why"),
    [
        ({"lufs": None}, {"lufs": "-19.9"}, "no integrated loudness"),
        ({"crc": ""}, {}, "no EAC CRC32"),
        ({"build": _BUILD_19}, {"build": _BUILD_19}, "on the read, before"),
        ({"build": "release"}, {"build": "release"}, "on the read, before"),
        (
            {"build": "platterpus-fork-g0000000"},
            {"build": "platterpus-fork-g0000000"},
            "cannot be placed",
        ),
        (
            {"build": _BUILD_28},
            {"build": "platterpus-fork-g5aeefc4"},
            "different builds",
        ),
    ],
)
def test_a_missing_value_or_an_unplaceable_build_is_not_determined(
    forced: dict[str, Any], disabled: dict[str, Any], why: str
) -> None:
    """Tri-state: none of these is a pass, and none is a fail either."""
    verdict = grading.grade_pair(
        _arm(**{"lufs": "-20.7", **forced}),
        _arm("r16deemphoff", **{"lufs": "-19.9", **disabled}),
    )
    assert verdict.state == grading.NOT_DETERMINED, verdict.detail
    assert why in verdict.detail


def test_an_unreadable_arm_is_not_determined() -> None:
    verdict = grading.grade_pair(
        grading.Arm(name="r16deemphon", problem="holds 0 cyanrip log(s)"),
        _arm("r16deemphoff"),
    )
    assert verdict.state == grading.NOT_DETERMINED
    assert "holds 0 cyanrip log(s)" in verdict.detail


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("platterpus-fork-g5704062", True),  # .20, the first after the filter
        ("platterpus-fork-g3f288fb-dirty", True),
        ("platterpus-fork-g174a134", False),  # .19
        ("release", False),
        ("platterpus-fork-g0000000", None),
        ("", None),
    ],
)
def test_where_a_build_measures_loudness(tag: str, expected: bool | None) -> None:
    assert grading.measures_delivered_audio(tag) is expected


@given(st.text(), st.text())
def test_grading_never_raises_on_any_log_text(forced: str, disabled: str) -> None:
    """The logs are the ripper's output, external input (Critical rule #12)."""
    verdict = grading.grade_pair(
        grading.arm_from_log("a", "", parse_cyanrip_log(forced)),
        grading.arm_from_log("b", "", parse_cyanrip_log(disabled)),
    )
    assert verdict.state in {grading.PASS, grading.FAIL, grading.NOT_DETERMINED}


# --- Finding each arm's log -----------------------------------------------------


def _write(root: Path, folder: str, text: str, *, name: str = "disc.log") -> Path:
    path = root / folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_an_arm_reads_its_one_log_from_this_run(tmp_path: Path) -> None:
    _write(tmp_path, "r16deemphon", _log())
    arm = deemphasis_verbs.read_arm(tmp_path, "r16deemphon", since=0.0)
    assert not arm.problem, arm.problem
    assert arm.crcs == ((1, "B0D122E7"),)
    assert arm.integrated_lufs == pytest.approx(-20.7)


def test_a_log_from_before_the_run_is_not_graded(tmp_path: Path) -> None:
    old = _write(tmp_path, "r16deemphon", _log())
    os.utime(old, (1_000_000.0, 1_000_000.0))
    arm = deemphasis_verbs.read_arm(tmp_path, "r16deemphon", since=2_000_000.0)
    assert "holds 0 cyanrip log(s)" in arm.problem


def test_two_logs_in_one_folder_are_not_guessed_between(tmp_path: Path) -> None:
    _write(tmp_path, "r16deemphon", _log())
    _write(tmp_path, "r16deemphon", _log(), name="other.log")
    arm = deemphasis_verbs.read_arm(tmp_path, "r16deemphon", since=0.0)
    assert "holds 2 cyanrip log(s)" in arm.problem


def test_a_log_cyanrip_did_not_write_is_not_counted(tmp_path: Path) -> None:
    _write(tmp_path, "r16deemphon", _log())
    _write(tmp_path, "r16deemphon", "Exact Audio Copy V1.6\n", name="eac.log")
    arm = deemphasis_verbs.read_arm(tmp_path, "r16deemphon", since=0.0)
    assert not arm.problem, arm.problem


@pytest.mark.parametrize("name", ["../r16", "a/b", ".hidden", "", "x" * 65])
def test_a_folder_name_that_could_leave_the_rips_folder_is_refused(name: str) -> None:
    assert deemphasis_verbs.folder_problem(name)


# --- The verb, through the runner -------------------------------------------------


def _run_verb(tmp_path: Path, qapp: Any, process_until: Any) -> Any:
    from test_uiscript_rip_verbs import _step_outcome, _window

    from platterpus.uiscript.runner import ScriptRunner

    win = _window(config=Config(output_dir=str(tmp_path)))
    return _step_outcome(
        ScriptRunner(win),
        qapp,
        process_until,
        "expect-deemphasis-pair r16deemphon r16deemphoff",
    )


def _dated_after_the_run_starts(root: Path) -> None:
    """A real run's rips are written after it starts; date the fixtures so too."""
    ahead = time.time() + 60.0
    for path in root.rglob("*"):
        if path.is_file():
            os.utime(path, (ahead, ahead))


def test_the_verb_passes_the_2026_11_03_pair(
    tmp_path: Path, qapp: Any, process_until: Any
) -> None:
    _write(tmp_path, "r16deemphon", _log(lufs="-20.7"))
    _write(tmp_path, "r16deemphoff", _log(folder="r16deemphoff", lufs="-19.9"))
    _dated_after_the_run_starts(tmp_path)
    step = _run_verb(tmp_path, qapp, process_until)
    assert step.outcome is Outcome.PASS, step.detail


def test_the_verb_fails_when_forcing_changed_nothing(
    tmp_path: Path, qapp: Any, process_until: Any
) -> None:
    _write(tmp_path, "r16deemphon", _log())
    _write(tmp_path, "r16deemphoff", _log(folder="r16deemphoff"))
    _dated_after_the_run_starts(tmp_path)
    step = _run_verb(tmp_path, qapp, process_until)
    assert step.outcome is Outcome.FAIL, step.detail


def test_the_verb_is_blocked_when_an_arm_left_no_log(
    tmp_path: Path, qapp: Any, process_until: Any
) -> None:
    _write(tmp_path, "r16deemphon", _log())
    _dated_after_the_run_starts(tmp_path)
    step = _run_verb(tmp_path, qapp, process_until)
    assert step.outcome is Outcome.BLOCKED, step.detail
    assert "r16deemphoff" in step.detail


def test_p3_grades_its_two_arms_right_after_them() -> None:
    """The grade follows both arms in P3, names their -D folders, forced first."""
    from platterpus.uiscript.script import parse

    text = (_RIG_SCRIPTS / "fullacceptance.txt").read_text(encoding="utf-8")
    body = text.split("log --- P3. ", 1)[1].split("\n# --- P5.", 1)[0]
    steps = [s for s in parse("log --- P3. " + body) if s.verb]
    verbs = [s.verb for s in steps]
    assert verbs.count("cyanrip") == 2, verbs
    assert verbs[-1] == "expect-deemphasis-pair", verbs
    forced, disabled = (s for s in steps if s.verb == "cyanrip")
    assert "-E" in forced.args and "-D" in forced.args
    assert "-W" in disabled.args
    folder = forced.args[forced.args.index("-D") + 1]
    control = disabled.args[disabled.args.index("-D") + 1]
    assert steps[-1].args == (folder, control)
