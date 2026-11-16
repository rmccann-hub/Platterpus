"""TASKS R24: `overreadprobe.txt` runs on every build that bounds `-O`, and only those.

**The defect** (2026-11-16). The probe's first step was
``expect-cyanrip platterpus-fork-g93afa15``: `.24`'s build tag, typed into the
script. The owner's rig runs `.31` (0.7.124/0.7.125's default) or `.32` (now
`FORK_PIN`), both of which bound `-O` exactly as `.24` does, so the one hardware
read R24 still owes could not start on any build the owner could install. Which
builds bound `-O` is now one fact, `fork_source.BUILD_TAGS_BOUNDING_OVERREAD`,
read from each build's source, and the script asks it through the
`expect-ripper-bounds-overread` verb.

**What must stay true:** `.23` and earlier are refused, because on them `-O`
hung the BDR-209D for about 23 minutes (2026-07-22), and a build Platterpus
cannot place stops the run as *not determined*, never as a pass.

The same script's offset check moved from ``expect read_offset 667`` (the global
config field, which no longer decides a rip's offset from 0.7.124) to
``expect-drive-offset 667`` (the selected drive's own answer).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from platterpus.deps import fork_source
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner
from platterpus.uiscript.script import parse
from platterpus.uiscript.script_values import parse_offset

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "platterpus"
    / "rig_scripts"
    / "overreadprobe.txt"
)

#: Banners as each build prints them on `--version` (version, then the build tag).
_BANNER_23 = "cyanrip 0.9.4-rc3+platterpus.23 (platterpus-fork-g891c79e)"
_BANNER_31 = "cyanrip 0.9.4-rc3+platterpus.31 (platterpus-fork-ge531a33)"
_BANNER_32 = "cyanrip 0.9.4-rc3+platterpus.32 (platterpus-fork-gedb73dd)"


def _runner() -> tuple[ScriptRunner, list[tuple[Outcome, str]]]:
    """A bare runner whose `_record` keeps what each step recorded."""
    runner = ScriptRunner.__new__(ScriptRunner)
    runner._ripper_build_tag = ""
    recorded: list[tuple[Outcome, str]] = []
    runner._record = (  # type: ignore[method-assign]
        lambda step, outcome, detail="", **_: recorded.append((outcome, detail))
    )
    return runner, recorded


def _gate_on(banner: str) -> tuple[Outcome, str]:
    """Run the SCRIPT's own step 1 gate against the build ``banner`` names.

    The step is the one parsed out of the committed file, and the build tag is
    latched from the banner by the runner's own `_latch_ripper_identity`, as the
    `cyanrip --version` step above it does in a real run.
    """
    steps = parse(_SCRIPT.read_text(encoding="utf-8"))
    [gate] = [s for s in steps if s.verb == "expect-ripper-bounds-overread"]
    runner, recorded = _runner()
    runner._latch_ripper_identity(banner)
    runner._do_expect_ripper_bounds_overread(gate)
    assert len(recorded) == 1, recorded
    return recorded[0]


@pytest.mark.parametrize("banner", [_BANNER_31, _BANNER_32])
def test_the_probe_runs_on_31_and_32(banner: str) -> None:
    outcome, detail = _gate_on(banner)
    assert outcome is Outcome.PASS, detail
    assert "bounds -O" in detail


def test_the_probe_refuses_23_whose_o_hung_the_drive() -> None:
    outcome, detail = _gate_on(_BANNER_23)
    assert outcome is Outcome.FAIL
    assert "does NOT bound -O" in detail
    # The remedy names a build the gate passes, so following it works.
    assert f"--install-ripper {fork_source.FORK_PIN}" in detail
    assert fork_source.bounds_overread(
        f"{fork_source.FORK_BRANCH}-g{fork_source.FORK_PIN}"
    )


def test_a_build_nobody_can_place_stops_the_probe_as_not_determined() -> None:
    for banner in (
        "cyanrip 0.9.4-rc3+platterpus.99 (platterpus-fork-g0000000)",
        "",
    ):
        outcome, detail = _gate_on(banner)
        assert outcome is Outcome.ERROR, (banner, detail)
        assert "not determined" in detail


def test_the_gate_stops_the_run_before_any_o_read() -> None:
    """The gate and its `abort-if-failed` come before the first `-O` read, and
    no build tag is typed into the script (the second copy that went stale)."""
    steps = parse(_SCRIPT.read_text(encoding="utf-8"))
    verbs = [s.verb for s in steps]
    first_read = next(
        i for i, s in enumerate(steps) if s.verb == "cyanrip" and "-O" in s.args
    )
    gate = verbs.index("expect-ripper-bounds-overread")
    assert gate < first_read
    assert verbs[gate + 1] == "abort-if-failed"
    assert verbs[: verbs.index("expect-ripper-bounds-overread")].count("cyanrip") == 1
    assert not any("platterpus-fork-g" in s.raw_tail for s in steps)


def test_bounds_overread_is_tri_state() -> None:
    """True for each build whose source was read, False for releases before `.24`,
    None for anything not placed. Non-trivial: both sides are populated."""
    for tag in fork_source.BUILD_TAGS_BOUNDING_OVERREAD:
        assert fork_source.bounds_overread(tag) is True
        assert fork_source.bounds_overread(tag + "-dirty") is True
        assert fork_source.bounds_overread(tag.upper()) is True
    assert len(fork_source.BUILD_TAGS_BOUNDING_OVERREAD) >= 9
    known_unbounded = [
        commit
        for commit, seq in fork_source.FORK_RELEASE_SEQ_BY_PIN.items()
        if seq < fork_source.FIRST_RELEASE_BOUNDING_OVERREAD
    ]
    assert "891c79e" in known_unbounded  # `.23`
    for commit in known_unbounded:
        assert fork_source.bounds_overread(f"platterpus-fork-g{commit}") is False
    for tag in ("", "  ", "g1a2b3c4", "platterpus-fork-g0000000", "cyanrip 0.9.3"):
        assert fork_source.bounds_overread(tag) is None


def test_every_bounding_build_is_a_placed_release_from_24() -> None:
    """The set and the release sequence agree: each listed build is a numbered
    release at or after `.24`'s, and `.24` is the first."""
    seqs = []
    for tag in fork_source.BUILD_TAGS_BOUNDING_OVERREAD:
        commit = tag.removeprefix(f"{fork_source.FORK_BRANCH}-g")
        seq = fork_source.release_seq_for_commit(commit)
        assert seq is not None, tag
        seqs.append(seq)
    assert min(seqs) == fork_source.FIRST_RELEASE_BOUNDING_OVERREAD
    assert fork_source.release_seq_for_commit("93afa15") == min(seqs)


def _offset_runner(
    set_by_script: int | None, drive_value: int | None
) -> tuple[ScriptRunner, list[tuple[Outcome, str]]]:
    runner, recorded = _runner()
    runner._drive_offset = set_by_script
    decision = SimpleNamespace(value=drive_value, reason="applied")
    runner._window = SimpleNamespace(_selected_drive_offset=lambda: decision)  # type: ignore[assignment]
    return runner, recorded


@pytest.mark.parametrize(
    ("line", "set_by_script", "drive_value", "expected"),
    [
        ("expect-drive-offset 667", 667, 667, Outcome.PASS),
        ("expect-drive-offset +667", 667, 667, Outcome.PASS),
        # Another drive's offset: the script is for the BDR-209D, so it stops.
        ("expect-drive-offset 667", 6, 6, Outcome.FAIL),
        # The drive changed under the run.
        ("expect-drive-offset 667", 667, 6, Outcome.FAIL),
        ("expect-drive-offset", 6, 6, Outcome.PASS),
        ("expect-drive-offset", 667, 6, Outcome.FAIL),
        ("expect-drive-offset six", 667, 667, Outcome.ERROR),
        ("expect-drive-offset 99999", 667, 667, Outcome.ERROR),
    ],
)
def test_expect_drive_offset_with_a_value_asks_the_drive(
    line: str, set_by_script: int, drive_value: int, expected: Outcome
) -> None:
    runner, recorded = _offset_runner(set_by_script, drive_value)
    [step] = parse(line)
    assert not step.error
    runner._do_expect_drive_offset(step)
    assert recorded[0][0] is expected, recorded


def test_parse_offset_reads_a_whole_number_in_range() -> None:
    assert parse_offset("667") == 667
    assert parse_offset("+667") == 667
    assert parse_offset("-667") == -667
    assert parse_offset("0") == 0
    for bad in ("", "six", "6.5", "5001", "-5001", "0x29b"):
        assert parse_offset(bad) is None
