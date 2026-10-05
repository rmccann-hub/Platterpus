"""Section J2's verbs: a library move, and a rip with no `-r` and no `-Z`.

TASKS *"Permutations the acceptance test still does not run"* (2026-09-30)
named paths no acceptance rip had taken. Section J2 takes them in one short rip,
and these tests run its verbs, and its lines as the shipped script spells them,
against the same stand-in window the other uiscript tests use.

**The graders are tested against committed rip reports** (round 29's), because
the argv a report records is the product's own record of what it sent. Where a
J2-shaped report is needed (no `-r`), it is the committed one with exactly that
flag removed, so every other field is still a real rip's.

**What the stand-in does that the product does not** (`CLAUDE.md`): the window
does not move anything. Where a test needs the album filed, it runs the REAL
`library_move.move_album_folder` and then repoints `_last_rip_log_file`, which is
what `MainWindow._on_library_moved` does on success. That repoint is pinned on
the real window by `tests/test_ui_main_window.py::
test_library_move_success_repoints_the_view_log_button`.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QTimer
from test_uiscript_rip_verbs import _step_outcome, _window

from platterpus import library_move
from platterpus.config import Config
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.uiscript import artifact_verbs, permutation_verbs
from platterpus.uiscript import permutation_grading as grading
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner
from platterpus.uiscript.script import parse

pytest.importorskip("PySide6.QtWidgets")

_REPO = Path(__file__).resolve().parent.parent
_ROUND29 = _REPO / "docs/handshake/artifactsround29"
_ACCEPTANCE = _REPO / "src/platterpus/rig_scripts/fullacceptance.txt"


@pytest.fixture(autouse=True)
def _short_waits(monkeypatch: pytest.MonkeyPatch) -> None:
    """The product waits 600 s for a record or a move; a test cannot."""
    monkeypatch.setattr(artifact_verbs, "ARTIFACT_WAIT_S", 2.0)
    monkeypatch.setattr(permutation_verbs, "LIBRARY_MOVE_WAIT_S", 2.0)


def _load(name: str) -> dict[str, Any]:
    loaded = json.loads((_ROUND29 / f"round29full{name}report.json").read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _without_retries(report: dict[str, Any]) -> dict[str, Any]:
    """The committed report as J2's rip would leave it: no `-r`, sent or received.

    Removed from all four places a report records the argv, so the sent and the
    received halves still agree, as they do on a real rip.
    """
    edited = copy.deepcopy(report)
    outcome = edited["outcome"]
    for key in ("ripper_argv", "ripper_argv_first_pass"):
        argv = outcome[key]
        at = argv.index("-r")
        outcome[key] = argv[:at] + argv[at + 2 :]
    edited["rip"]["invoked_as"] = edited["rip"]["invoked_as"].replace(" -r 5 ", " ")
    log = edited["artifacts"]["rip_log"]
    log["text"] = re.sub(
        r"^(Invoked as:.*?) -r 5 ", r"\1 ", log["text"], count=1, flags=re.MULTILINE
    )
    assert "-r" not in outcome["ripper_argv"], "the edit did not land"
    assert " -r 5 " not in log["text"].split("Invoked as:", 1)[1].splitlines()[0]
    return edited


def _album(root: Path, report: dict[str, Any]) -> Path:
    """An album folder as a finished rip leaves it under ``root``; returns its log."""
    folder = root / "Platterpus Acceptance" / "permutations"
    folder.mkdir(parents=True)
    log_file = folder / "permutations.log"
    log_file.write_text(report["artifacts"]["rip_log"]["text"], encoding="utf-8")
    (folder / "permutations.platterpus.json").write_text(json.dumps(report), "utf-8")
    return log_file


def _window_after(log_file: Path, *, library: Path | None) -> Any:
    """A stand-in window whose last rip wrote ``log_file``."""
    config = Config(
        output_dir=str(log_file.parents[2]),
        library_dir=str(library) if library is not None else "",
    )
    return _window(
        last_rip_log=parse_cyanrip_log(log_file.read_text(encoding="utf-8")),
        last_rip_log_file=log_file,
        config=config,
    )


def _file_in_library(win: Any, library: Path) -> None:
    """What the product does once the post-rip checks settle: move, then repoint."""
    log_file: Path = win._last_rip_log_file
    result = library_move.move_album_folder(log_file.parent, library)
    assert result.ok and result.destination is not None, result.message
    win._last_rip_log_file = result.destination / log_file.name


def _run(win: Any, qapp: Any, process_until: Any, source: str) -> Any:
    return _step_outcome(ScriptRunner(win), qapp, process_until, source)


# --- permutation_grading: the pure answers -----------------------------------


def test_the_scratch_library_is_inside_the_rips_folder() -> None:
    path, problem = grading.scratch_library_dir("/rig/session/rips")
    assert problem == ""
    assert path == Path("/rig/session/rips") / grading.SCRATCH_LIBRARY_NAME


@pytest.mark.parametrize("output_dir", ["", "   ", "relative/rips"])
def test_no_scratch_library_is_derived_from_an_unusable_output_folder(
    output_dir: str,
) -> None:
    path, problem = grading.scratch_library_dir(output_dir)
    assert path is None and problem, (output_dir, problem)


def test_the_argv_grader_reads_r_off_a_real_rip() -> None:
    """Round 29's overwrite rip sent `-r 5`: `with` holds and `without` fails."""
    report = _load("overwrite")
    held = grading.grade_rip_argv(report, "-r", present=True)
    assert held.passed and "`-r 5`" in held.detail, held.detail
    refused = grading.grade_rip_argv(report, "-r", present=False)
    assert not refused.passed, refused.detail


def test_the_argv_grader_passes_a_rip_that_sent_no_r() -> None:
    graded = grading.grade_rip_argv(
        _without_retries(_load("overwrite")), "-r", present=False
    )
    assert graded.passed and "no `-r`" in graded.detail, graded.detail


def test_the_argv_grader_tells_a_uniform_z_from_none() -> None:
    """The uniform secure re-read sends `-Z` on its whole-disc pass (section N)."""
    uniform = _load("securereread")
    assert grading.grade_rip_argv(uniform, "-Z", present=True).passed
    assert not grading.grade_rip_argv(uniform, "-Z", present=False).passed


def test_a_later_pass_is_reported_and_not_graded() -> None:
    """Round 29's whole-disc rip: no `-Z` on pass 1 (dynamic), `-Z` on the re-read."""
    graded = grading.grade_rip_argv(_load("wholedisc"), "-Z", present=False)
    assert graded.passed, graded.detail
    assert "later pass" in graded.detail and "carries -Z" in graded.detail, (
        graded.detail
    )


@pytest.mark.parametrize(
    ("report", "flag", "said"),
    [
        ({}, "-r", "no outcome"),
        ({"outcome": {"ripper_argv": None}}, "-r", "no argv"),
        ({"outcome": {"ripper_argv": ["cyanrip", "-d", "/dev/sr0"]}}, "-r", "-N"),
        ({"outcome": {"ripper_argv": ["cyanrip", "-N"]}}, "r", "not a flag"),
    ],
)
def test_the_argv_grader_cannot_pass_by_finding_nothing(
    report: dict[str, Any], flag: str, said: str
) -> None:
    """`without -r` is true of an empty argv, a non-rip argv and a misspelt flag,
    and none of them is a rip that left `-r` out."""
    graded = grading.grade_rip_argv(report, flag, present=False)
    assert not graded.passed and said in graded.detail, graded.detail


def test_a_moved_album_passes_and_a_waiting_one_is_not_yet_graded(
    tmp_path: Path,
) -> None:
    log_file = _album(tmp_path / "rips", _load("overwrite"))
    library = tmp_path / "rips" / grading.SCRATCH_LIBRARY_NAME
    before = log_file.parent
    assert grading.grade_library_move(log_file, library, before) is None
    moved = library_move.move_album_folder(before, library)
    assert moved.destination is not None
    graded = grading.grade_library_move(
        moved.destination / log_file.name, library, before
    )
    assert graded is not None and graded.passed, graded
    assert f"nothing is left at {before}" in graded.detail


def test_a_copy_is_not_a_move(tmp_path: Path) -> None:
    import shutil

    log_file = _album(tmp_path / "rips", _load("overwrite"))
    library = tmp_path / "library"
    copied = library / log_file.parent.name
    shutil.copytree(log_file.parent, copied)
    graded = grading.grade_library_move(
        copied / log_file.name, library, log_file.parent
    )
    assert graded is not None and not graded.passed
    assert "copied, not moved" in graded.detail


def test_a_folder_filed_without_its_report_fails(tmp_path: Path) -> None:
    log_file = _album(tmp_path / "rips", _load("overwrite"))
    (log_file.parent / "permutations.platterpus.json").unlink()
    library = tmp_path / "library"
    moved = library_move.move_album_folder(log_file.parent, library)
    assert moved.destination is not None
    graded = grading.grade_library_move(
        moved.destination / log_file.name, library, log_file.parent
    )
    assert graded is not None and not graded.passed
    assert "no rip report travelled" in graded.detail


def test_a_window_that_lost_the_log_path_fails() -> None:
    graded = grading.grade_library_move(None, Path("/lib"), Path("/out/a"))
    assert graded is not None and not graded.passed


# --- the verbs, through the real runner ---------------------------------------


def test_set_library_scratch_sets_it_through_the_real_set(
    qapp, process_until, tmp_path
) -> None:
    rips = tmp_path / "rips"
    win = _window(config=Config(output_dir=str(rips)))
    step = _run(win, qapp, process_until, "set-library-scratch")
    assert step.outcome is Outcome.PASS, step.detail
    scratch = str(rips / grading.SCRATCH_LIBRARY_NAME)
    assert win._config.library_dir == scratch
    # `set`'s own side effects, which a restatement would have to remember: the
    # config is pushed to the rip controls and saved.
    assert win._rip_controls.config_pushed.library_dir == scratch
    assert win.saved and win.saved[-1].library_dir == scratch


def test_set_library_scratch_refuses_an_output_folder_it_cannot_use(
    qapp, process_until
) -> None:
    win = _window(config=Config(output_dir="relative/rips"))
    step = _run(win, qapp, process_until, "set-library-scratch")
    assert step.outcome is Outcome.FAIL, step.detail
    assert win._config.library_dir == "", "a refused scratch library was written"


def test_expect_library_move_refuses_at_once_when_the_library_is_off(
    qapp, process_until, tmp_path
) -> None:
    win = _window_after(_album(tmp_path / "rips", _load("overwrite")), library=None)
    step = _run(win, qapp, process_until, "expect-library-move")
    assert step.outcome is Outcome.FAIL and "library_dir is off" in step.detail


def test_expect_library_move_waits_for_the_window_to_file_the_rip(
    qapp, process_until, tmp_path
) -> None:
    """The move lands AFTER the step starts waiting, as it does on a real rip."""
    library = tmp_path / "rips" / grading.SCRATCH_LIBRARY_NAME
    win = _window_after(_album(tmp_path / "rips", _load("overwrite")), library=library)
    QTimer.singleShot(300, lambda: _file_in_library(win, library))
    step = _run(win, qapp, process_until, "expect-library-move")
    assert step.outcome is Outcome.PASS, step.detail
    assert step.elapsed_s >= 0.2, "it graded before the move it is waiting for"


def test_expect_library_move_fails_when_nothing_is_filed(
    qapp, process_until, tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(permutation_verbs, "LIBRARY_MOVE_WAIT_S", 0.3)
    library = tmp_path / "rips" / grading.SCRATCH_LIBRARY_NAME
    win = _window_after(_album(tmp_path / "rips", _load("overwrite")), library=library)
    step = _run(win, qapp, process_until, "expect-library-move")
    assert step.outcome is Outcome.FAIL
    assert "was not filed" in step.detail, step.detail


@pytest.mark.parametrize(
    "source", ["expect-rip-argv sideways -r", "expect-rip-argv without r"]
)
def test_a_malformed_argv_step_is_a_script_error_not_a_finding(
    qapp, process_until, tmp_path, source: str
) -> None:
    win = _window_after(_album(tmp_path / "rips", _load("overwrite")), library=None)
    step = _run(win, qapp, process_until, source)
    assert step.outcome is Outcome.ERROR, step.detail


def test_expect_rip_argv_reads_the_report_on_disk(
    qapp, process_until, tmp_path
) -> None:
    win = _window_after(
        _album(tmp_path / "rips", _without_retries(_load("overwrite"))), library=None
    )
    assert _run(win, qapp, process_until, "expect-rip-argv without -r").outcome is (
        Outcome.PASS
    )
    real = _window_after(_album(tmp_path / "real", _load("overwrite")), library=None)
    step = _run(real, qapp, process_until, "expect-rip-argv without -r")
    assert step.outcome is Outcome.FAIL, step.detail


# --- section J2's own lines, as the shipped script spells them -----------------


def _section(letter: str) -> list[str]:
    """The executable lines of one acceptance section, read from the shipped file."""
    lines: list[str] = []
    inside = False
    for raw in _ACCEPTANCE.read_text(encoding="utf-8").splitlines():
        header = re.match(r"^log --- ([A-Z][0-9]*)\.\s", raw)
        if header:
            inside = header.group(1) == letter
            continue
        stripped = raw.strip()
        if inside and stripped and not stripped.startswith("#"):
            lines.append(stripped)
    assert lines, f"section {letter} is not in the shipped script"
    return lines


def _lines_between(lines: list[str], first: str, last: str) -> list[str]:
    return lines[lines.index(first) : lines.index(last) + 1]


def test_j2_s_settings_lines_change_what_it_says_and_put_it_all_back(
    qapp, process_until, tmp_path
) -> None:
    """Every settings line of J2, in order, through the real `set` and `expect`.

    The rip and its graders are left out (the stand-in does not rip); what is
    left is the claim that J2 leaves the rig as it found it, so K1 rips on the
    shipped settings, and that mid-section the settings were the permutation.
    """
    settings_verbs = {"set", "expect", "expect-contains", "set-library-scratch"}
    lines = [line for line in _section("J2") if line.split()[0] in settings_verbs]
    assert len(lines) >= 20, f"J2's settings lines shrank: {lines}"
    start = Config(output_dir=str(tmp_path / "rips"))
    win = _window(config=start)
    emitted: list[Any] = []
    runner = ScriptRunner(win)
    runner.finished.connect(emitted.append)
    source = "\n".join(lines)
    runner.start(parse(source), source=source)
    assert process_until(lambda: bool(emitted)), "the run never finished"
    steps = emitted[0].steps
    assert all(s.outcome is Outcome.PASS for s in steps), [
        (s.source, s.outcome, s.detail) for s in steps if s.outcome is not Outcome.PASS
    ]
    scratch = [s for s in steps if s.source == "set-library-scratch"]
    assert scratch and grading.SCRATCH_LIBRARY_NAME in scratch[0].detail
    for name in (
        "library_dir",
        "max_retries",
        "secure_rerip_matches",
        "secure_rerip_dynamic",
        "read_speed_mode",
        "read_speed",
    ):
        assert getattr(win._config, name) == getattr(start, name), (
            f"J2 leaves {name} at {getattr(win._config, name)!r}, not "
            f"{getattr(start, name)!r}"
        )


def test_j2_rips_on_settings_its_without_lines_can_fail_over(
    qapp, process_until, tmp_path
) -> None:
    """J2's distinguishing property, asserted at the section (`docs/testing.md`
    §5.bj): the settings in force at its `rip` are ones that would SEND the flags
    its `without` lines refuse, had the permutation not taken.

    The trap is `-Z`. In the default dynamic mode the first pass never carries
    `-Z`, so `expect-rip-argv without -Z` would hold whatever `secure_rerip_
    matches` said. Only in uniform mode does a non-zero setting reach pass 1, so
    J2 must be in uniform mode when it rips. The settings are replayed through the
    real runner up to the `rip`, and the flags are predicted with the builder's
    own mapping (`cyanrip_cli.retries_flag_value`) and the worker's pass-1 rule.
    """
    from platterpus.cyanrip_cli import retries_flag_value

    settings_verbs = {"set", "expect", "expect-contains", "set-library-scratch"}
    section = _section("J2")
    before_rip = section[: section.index("rip")]
    lines = [line for line in before_rip if line.split()[0] in settings_verbs]
    win = _window(config=Config(output_dir=str(tmp_path / "rips")))
    emitted: list[Any] = []
    runner = ScriptRunner(win)
    runner.finished.connect(emitted.append)
    source = "\n".join(lines)
    runner.start(parse(source), source=source)
    assert process_until(lambda: bool(emitted)), "the run never finished"
    at_rip = win._config
    assert at_rip.secure_rerip_dynamic is False, (
        "J2 rips in dynamic mode, where pass 1 never carries -Z, so its "
        "`without -Z` line holds whatever the secure re-read setting says"
    )
    assert at_rip.secure_rerip_matches == 0, "J2 does not rip with the -Z 0 it tests"
    assert retries_flag_value(at_rip.max_retries) is None, "J2 would send -r"
    assert at_rip.read_speed_mode == "fixed" and at_rip.read_speed == 0
    assert grading.SCRATCH_LIBRARY_NAME in at_rip.library_dir
    # Non-triviality: with the shipped values in uniform mode, both flags WOULD
    # be sent, so the two `without` lines are each able to fail.
    shipped = Config()
    assert retries_flag_value(shipped.max_retries) is not None
    assert shipped.secure_rerip_matches > 0


def _run_j2_grading(
    win: Any, qapp: Any, process_until: Any, library: Path
) -> list[Any]:
    lines = _lines_between(
        _section("J2"), "expect-library-move", "expect-album-audit argv_agreement"
    )
    assert len(lines) >= 6, f"J2's grading lines shrank: {lines}"
    QTimer.singleShot(300, lambda: _file_in_library(win, library))
    emitted: list[Any] = []
    runner = ScriptRunner(win)
    runner.finished.connect(emitted.append)
    source = "\n".join(lines)
    runner.start(parse(source), source=source)
    assert process_until(lambda: bool(emitted), timeout=30), "the run never finished"
    steps: list[Any] = emitted[0].steps
    return steps


def test_j2_s_grading_lines_pass_over_a_rip_that_did_what_j2_asks(
    qapp, process_until, tmp_path
) -> None:
    """J2's lines from `expect-library-move` on, verbatim, over a J2-shaped rip:
    filed into the scratch library, its argv carrying no `-r`, `-Z` or `-S`."""
    library = tmp_path / "rips" / grading.SCRATCH_LIBRARY_NAME
    report = _without_retries(_load("overwrite"))
    win = _window_after(_album(tmp_path / "rips", report), library=library)
    steps = _run_j2_grading(win, qapp, process_until, library)
    assert all(s.outcome is Outcome.PASS for s in steps), [
        (s.source, s.outcome, s.detail) for s in steps if s.outcome is not Outcome.PASS
    ]
    # Every grader after the move read the album where it ended up.
    assert win._last_rip_log_file.parent.parent == library


def test_j2_s_grading_lines_fail_over_a_rip_that_sent_r(
    qapp, process_until, tmp_path
) -> None:
    """The same lines over the unedited round-29 rip, which sent `-r 5`: the
    `without -r` line must fail, or the section could not see the setting lost."""
    library = tmp_path / "rips" / grading.SCRATCH_LIBRARY_NAME
    win = _window_after(_album(tmp_path / "rips", _load("overwrite")), library=library)
    steps = _run_j2_grading(win, qapp, process_until, library)
    by_source = {s.source: s for s in steps}
    assert by_source["expect-rip-argv without -r"].outcome is Outcome.FAIL
    assert by_source["expect-library-move"].outcome is Outcome.PASS
